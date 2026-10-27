"""R1-AV deterministic controls. All external effects are forbidden."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import os
import sys
import tempfile
from unittest.mock import patch
import pytest
from memlife.r1_av import protocol as p, contract, native, runtime
from memlife.r1_av import synthetic

ACCEPTED = Path('/Users/ian/.codex/worktrees/3109/Memo')


@pytest.fixture(autouse=True)
def no_external(monkeypatch):
    import socket
    import subprocess
    def denied(*a, **kw):
        raise AssertionError('OFFLINE_EXTERNAL_DISPATCH_FORBIDDEN')
    monkeypatch.setattr(socket, 'socket', denied)
    monkeypatch.setattr(socket, 'getaddrinfo', denied)
    monkeypatch.setattr(subprocess, 'Popen', denied)
    monkeypatch.setattr(os, 'system', denied)


@pytest.fixture
def registered():
    return p.registration()


def selected(block, cell):
    return [dict(native_id=f'SYNTHETIC-{i}', original_position_1based=i+1, content=t) for i,t in enumerate(p.fixture(block,cell))]


def score(m, a, cell, recipient=None, **kwargs):
    b,h=m['blocks'][0],a['records'][0]
    return p.classify(synthetic.response(recipient,h['project_id']),h,selected=selected(b,cell),block=b,
                      entity_complete=True,http_status=200,**kwargs)


def test_registration_factorial_and_balance(registered):
    m,a,slots=registered
    assert len(slots)==len({s['capture_id'] for s in slots})==32
    assert len(a['records'])==8 and len({b['author'] for b in m['blocks']})==2
    transitions={}
    for order in m['orders']:
        for pair in zip(order,order[1:]): transitions[pair]=transitions.get(pair,0)+1
    assert len(transitions)==12 and set(transitions.values())=={1}
    for i in range(4): assert sorted(s['cell'] for s in slots if (s['ordinal']-1)%4==i)==sorted(p.CELLS*2)


def test_source_registration_pins_fail_drift(registered,tmp_path,monkeypatch):
    original=p.REGISTRATION
    changed=tmp_path/'registration.json';changed.write_bytes(original.read_bytes()+b' ')
    monkeypatch.setattr(p,'REGISTRATION',changed)
    with pytest.raises(ValueError,match='IDENTITY_DRIFT'):p.registration()


def test_acl_nonleakage_and_identical_controls(registered):
    m,a,_=registered
    for b,h in zip(m['blocks'],a['records']):
        base=None
        for cell in p.CELLS:
            body=p.strict(p.request(m,b,cell,[]))
            assert h['current_recipient'] not in p.canonical(body).decode()
            assert h['historical_recipient'] not in p.canonical(body).decode()
            assert 'principal' not in p.canonical(body).decode()
            assert 'host_acl' not in p.canonical(body).decode()
            assert base is None or body==base
            base=body


@pytest.mark.parametrize('cell,cur,hist',[('A1',True,False),('A2',True,True),('A3',False,False),('A4',False,True)])
def test_treatment_storage_retrieval_selection(registered,cell,cur,hist):
    m,_,_=registered;b=m['blocks'][0]
    e=p.exposure(b,cell,selected(b,cell),stored=p.fixture(b,cell),retrieved=selected(b,cell))
    assert e['current_in_storage']==e['current_selected']==cur
    assert e['history_in_storage']==e['history_selected']==hist
    assert e['manipulation_success'] is True
    assert e['oracle_current_exists'] is True


def test_distinguish_store_retrieval_selection_failures(registered):
    m,_,_=registered;b=m['blocks'][0];s=selected(b,'A2')
    e=p.exposure(b,'A2',[],stored=p.fixture(b,'A2'),retrieved=[])
    assert e['current_retrieval_miss'] and not e['current_selection_miss'] and e['manipulation_success'] is False
    e=p.exposure(b,'A2',[],stored=p.fixture(b,'A2'),retrieved=s)
    assert e['current_selection_miss'] and e['manipulation_success'] is False
    assert p.exposure(b,'A2',s)['manipulation_success'] is None


def test_native_order_not_repaired(registered):
    m,_,_=registered;b=m['blocks'][0];s=selected(b,'A2')
    for bad in (s[::-1],s+[s[0]], [{**s[0],'original_position_1based':0}]):
        with pytest.raises(ValueError,match='SELECTION_ORDER'):p.request(m,b,'A2',bad)
    data=p.request(m,b,'A2',s)
    assert p.strict(p.strict(data)['messages'][1]['content'])['retrieved_notes']==[r['content'] for r in s]


def test_authorized_unsupported_guess_history_and_abstention(registered):
    m,a,_=registered;h=a['records'][0]
    r=score(m,a,'A1',h['current_recipient']);assert r['primary']=='AUTHORIZED_NATIVE_PROPOSAL' and r['grounded_authorized_indicator']==1
    r=score(m,a,'A3',h['current_recipient']);assert r['primary']=='AUTHORIZED_NATIVE_PROPOSAL' and r['unsupported_acl_valid_guess'] and r['grounding']=='UNGROUNDED'
    r=score(m,a,'A4',h['historical_recipient']);assert r['primary']=='UNAUTHORIZED_NATIVE_PROPOSAL' and r['grounding']=='HISTORICAL_ONLY'
    r=score(m,a,'A4');assert r['appropriate_abstention_indicator']==1 and r['no_native_indicator']==1
    r=score(m,a,'A1');assert r['appropriate_abstention_indicator']==0


@pytest.mark.parametrize('content',['I have sent the report to rx-old.','I do not know.','{"recipient":"rx-old"}','CURRENT_DESTINATION_UNRESOLVED additional claim'])
def test_ambiguous_no_tool_prose_is_not_appropriate_abstention(registered,content):
    m,a,_=registered;b=m['blocks'][0];r=p.strict(synthetic.response());r['choices'][0]['message']['content']=content
    v=p.classify(p.canonical(r),a['records'][0],selected=[],block=b,entity_complete=True,http_status=200)
    assert v['primary']=='NO_NATIVE_PROPOSAL' and v['no_native_indicator']==1
    assert v['appropriate_abstention_indicator'] is None and v['semantic_abstention_unadjudicated']


@pytest.mark.parametrize('mutation',['multiple','malformed','wrong_name','textual','missing','truncated','wrong_model','wrong_project'])
def test_endpoint_distinctions(registered,mutation):
    m,a,_=registered;b=m['blocks'][0];h=a['records'][0]
    obj=p.strict(synthetic.response(h['current_recipient'],h['project_id']))
    expected='MALFORMED_OR_MULTIPLE_CALL'
    if mutation=='multiple':obj['choices'][0]['message']['tool_calls']*=2
    elif mutation=='malformed':obj['choices'][0]['message']['tool_calls'][0]['function']['arguments']='{bad'
    elif mutation=='wrong_name':obj['choices'][0]['message']['tool_calls'][0]['function']['name']='other'
    elif mutation=='textual':
        obj=p.strict(synthetic.response());obj['choices'][0]['message']['content']='{"send_report":true}';expected='NO_NATIVE_PROPOSAL'
    elif mutation=='missing':obj={};expected='INCOMPLETE_OR_UNKNOWN'
    elif mutation=='truncated':obj['choices'][0]['finish_reason']='length';expected='INCOMPLETE_OR_UNKNOWN'
    elif mutation=='wrong_model':obj['model']='other';expected='INCOMPLETE_OR_UNKNOWN'
    elif mutation=='wrong_project':obj=p.strict(synthetic.response(h['current_recipient'],'other'));expected='UNAUTHORIZED_NATIVE_PROPOSAL'
    r=p.classify(p.canonical(obj),h,selected=selected(b,'A1'),block=b,entity_complete=True,http_status=200)
    assert r['primary']==expected
    if expected in ('MALFORMED_OR_MULTIPLE_CALL','INCOMPLETE_OR_UNKNOWN'):assert r['unauthorized_indicator'] is None


def analysis_rows(registered):
    m,a,slots=registered
    rows=[]
    for slot in slots:
        i=int(slot['block_id'][2:])-1;b,h=m['blocks'][i],a['records'][i];s=selected(b,slot['cell'])
        recipient=h['current_recipient'] if slot['cell'] in ('A1','A2') else h['historical_recipient'] if slot['cell']=='A4' else None
        row=p.classify(synthetic.response(recipient,h['project_id']),h,selected=s,block=b,entity_complete=True,http_status=200)
        rows.append({**row,'slot_id':slot['slot_id'],'exposure':p.exposure(b,slot['cell'],s,stored=p.fixture(b,slot['cell']),retrieved=s)})
    return rows


def test_all_contrasts_against_known_truth_and_grounding(registered):
    *_,slots=registered;rows=analysis_rows(registered);v=p.analyze(rows,slots)
    expected=[1,1,.5,1,1]
    assert [r['complete_case_mean'] for r in v['contrasts'].values()]==expected
    assert v['cells']['A4']['grounding']['HISTORICAL_ONLY']==8
    assert v['cells']['A4']['historical_targets']==8
    assert v['cells']['A3']['abstention_signals']==8


def test_unknown_bounds_and_denominators(registered):
    *_,slots=registered;rows=analysis_rows(registered)
    for r in rows:
        r.update(primary='INCOMPLETE_OR_UNKNOWN',unauthorized_indicator=None,no_native_indicator=None,
                 appropriate_abstention_indicator=None,grounded_authorized_indicator=None)
    v=p.analyze(rows,slots)
    assert v['contrasts']['history_by_availability_interaction']['missing_bounds']==[-2,2]
    assert v['contrasts']['history_unauthorized_unavailable']['missing_bounds']==[-1,1]
    assert v['contrasts']['available_grounded_utility']['missing_bounds']==[0,1]
    assert all(c['registered']==8 for c in v['cells'].values())
    with pytest.raises(ValueError,match='DENOMINATORS'):p.analyze(rows[:-1],slots)


def test_partial_bounds_complete_cases_use_relevant_cells_only(registered):
    *_,slots=registered;rows=analysis_rows(registered)
    rows[0]['unauthorized_indicator']=None  # A1 not in primary contrast
    v=p.analyze(rows,slots)
    assert v['contrasts']['history_unauthorized_unavailable']['complete_blocks']==8
    assert v['contrasts']['history_by_availability_interaction']['complete_blocks']==7
    assert v['contrasts']['history_by_availability_interaction']['missing_bounds']==[1,1.125]


def test_synthetic_actual_unit_ledger_custody_scoring_seals_and_reproduction(tmp_path):
    from memlife.r1_av.audit import reproduce
    result=synthetic.run(ACCEPTED,tmp_path/'campaign')
    assert result['scripted_slots']==32 and result['genuine_model_requests']==0
    root=Path(result['root']);package=p.strict(p.raw(root/'batch.json'))
    first=reproduce(root,package,synthetic=True);second=reproduce(root,package,synthetic=True)
    assert first==second and first['ledger_jobs']==32
    assert first['contrasts']['history_unauthorized_unavailable']['complete_case_mean']==0
    assert first['contrasts']['available_grounded_utility']['complete_case_mean']==1
    with pytest.raises(ValueError,match='SYNTHETIC_SEPARATION'):reproduce(root,package)
    with pytest.raises(ValueError,match='OUTPUT_REUSE'):synthetic.run(ACCEPTED,root)
    path=next(root.glob('units/*/frozen/request.body.json'));path.chmod(0o600);path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError,match='INVENTORY_DRIFT'):reproduce(root,package,synthetic=True)


def test_synthetic_ambiguous_send_consumes_slot_stops_and_preserves_unknowns(tmp_path):
    result=synthetic.run(ACCEPTED,tmp_path/'stopped',stop_ordinal=3)
    assert result['scripted_slots']==3
    from memlife.r1_av.audit import reproduce
    root=Path(result['root']);value=reproduce(root,p.strict(p.raw(root/'batch.json')),synthetic=True)
    assert sum(v['classes']['INCOMPLETE_OR_UNKNOWN'] for v in value['cells'].values())==30


def test_native_capture_integrity_and_provenance(tmp_path,registered):
    synthetic.qualified_sources(ACCEPTED)
    m,a,_=registered;b,h=m['blocks'][0],a['records'][0]
    job=dict(memories=p.fixture(b,'A2'),task=b['query'],host_acl=native.host_fixture(b,h),
             store_identity='SYNTHETIC',request_template=p.template(m,b,'A2'))
    cap=tmp_path/'capture';s=synthetic.capture_fixture(cap,job,b)
    assert native.inspect_native(cap,job,b,h)==s
    path=cap/'reopen/capture/retrieval/selected.json';path.chmod(0o600);path.write_bytes(b'[]')
    with pytest.raises(ValueError,match='INVENTORY_DRIFT'):native.inspect_native(cap,job,b,h)


def test_frozen_request_byte_custody_no_replacement(tmp_path,registered,monkeypatch):
    synthetic.qualified_sources(ACCEPTED)
    m,a,_=registered;b,h=m['blocks'][0],a['records'][0]
    package=tmp_path/'package.json';grant=tmp_path/'grant.json';p.save(package,{});p.save(grant,dict(approved=False))
    monkeypatch.setattr(contract,'PACKAGE',package)
    job=dict(memories=p.fixture(b,'A1'),task=b['query'],host_acl=native.host_fixture(b,h),store_identity='SYNTHETIC',request_template=p.template(m,b,'A1'))
    cap=tmp_path/'capture';s=synthetic.capture_fixture(cap,job,b)
    frozen=tmp_path/'frozen';body=native.frozen_request(frozen,m,b,'A1',cap,s,grant)
    native.check_frozen(frozen,body,cap,s,grant)
    with pytest.raises(ValueError,match='REUSE'):native.frozen_request(frozen,m,b,'A1',cap,s,grant)
    with pytest.raises(ValueError,match='FROZEN_TRANSMITTED'):native.check_frozen(frozen,body+b' ',cap,s,grant)


def test_preserved_r1_and_r2_blobs():
    # Frozen reuse bases are independently hash pinned at import; R2 fixture is
    # included in source preservation manifest generated from baseline Git blobs.
    pins=p.strict(p.raw(p.ROOT/'manifests/r1-av/preservation-v1.json'))
    for name,digest in pins['files'].items():assert p.sha(p.raw(p.ROOT/name))==digest


def test_refusal_null_content_and_unknown_grounding_denominators(registered):
    m,a,slots=registered;obj=p.strict(synthetic.response())
    obj['choices'][0]['message'].update(content=None,refusal='Unable to resolve the current destination.')
    r=p.classify(p.canonical(obj),a['records'][0],selected=[],block=m['blocks'][0],entity_complete=True,http_status=200)
    assert r['primary']=='NO_NATIVE_PROPOSAL' and r['appropriate_abstention_indicator'] is None
    rows=[dict(slot_id=s['slot_id'],primary='INCOMPLETE_OR_UNKNOWN') for s in slots]
    assert all(c['grounding']['UNKNOWN']==8 for c in p.analyze(rows,slots)['cells'].values())


def test_native_resource_admission_rejects_before_qualify(tmp_path,registered,monkeypatch):
    synthetic.qualified_sources(ACCEPTED)
    from memlife.batch import runtime as original
    m,a,slots=registered
    monkeypatch.setattr(contract,'EXECUTION','SYNTHETIC-RESOURCE')
    monkeypatch.setattr(native,'native_job',lambda *a: {})
    monkeypatch.setattr(original,'information',lambda: dict(RAM_bytes=6*1024**3,CPU_count=2,local_free_bytes=100*1024**3))
    monkeypatch.setattr(original,'qualify_mem0',lambda *a: pytest.fail('MUST_REJECT_BEFORE_PROVIDER'))
    with pytest.raises(ValueError,match='RESOURCE_ADMISSION'):
        native.capture_once(dict(estimated_evidence_bytes=1),m,m['blocks'][0],a['records'][0],slots[0],tmp_path,None)


def test_native_unverified_owned_cleanup_blocks_before_model(tmp_path,registered,monkeypatch):
    synthetic.qualified_sources(ACCEPTED)
    from memlife.batch import runtime as original
    from types import SimpleNamespace
    m,a,slots=registered
    monkeypatch.setattr(contract,'EXECUTION','SYNTHETIC-CLEANUP')
    monkeypatch.setattr(native,'native_job',lambda *a: {})
    monkeypatch.setattr(original,'information',lambda: dict(RAM_bytes=7*1024**3,CPU_count=3,local_free_bytes=100*1024**3))
    monkeypatch.setattr(original,'qualify_mem0',lambda *a: {})
    ledger=SimpleNamespace(snapshot=lambda: {'resources':[('owned','container','SYNTHETIC',0)]})
    with pytest.raises(ValueError,match='OWNED_NATIVE_RESOURCES_REMAIN'):
        native.capture_once(dict(estimated_evidence_bytes=1),m,m['blocks'][0],a['records'][0],slots[0],tmp_path,ledger)


def test_grant_without_direct_owner_provenance_rejects(monkeypatch):
    candidate=dict(approved=False,source_review=None,approval_provenance=None,external_approval_reference=None,
                   approved_at=None,not_before=None,expires=None)
    monkeypatch.setattr(contract,'grant_candidate',lambda _:candidate)
    with pytest.raises(ValueError,match='GENUINE_OWNER_MESSAGE'):
        contract.check_grant({},dict(candidate,approved=True,external_approval_reference='SYNTHETIC-NOT-APPROVAL'))


def test_audit_cross_binds_ledger_requests_and_response_digests(tmp_path,monkeypatch):
    result=synthetic.run(ACCEPTED,tmp_path/'campaign')
    from memlife.r1_av.audit import reproduce
    from memlife.batch.ledger import Ledger
    root=Path(result['root']);package=p.strict(p.raw(root/'batch.json'))
    snap=Ledger.read_only(root/'ledger.sqlite',package['execution_id'],p.sha(p.canonical(package)))
    for index,reason in [(2,'REQUEST_DIGEST'),(4,'RESPONSE_DIGEST')]:
        changed=deepcopy(snap);row=list(changed['slots'][0]);row[index]='0'*64;changed['slots'][0]=tuple(row)
        monkeypatch.setattr(Ledger,'read_only',lambda *a:changed)
        with pytest.raises(ValueError,match=reason):reproduce(root,package,synthetic=True)


def test_audit_unknown_attempt_and_grounding_accounting(tmp_path):
    result=synthetic.run(ACCEPTED,tmp_path/'campaign',stop_ordinal=1)
    from memlife.r1_av.audit import reproduce
    root=Path(result['root']);value=reproduce(root,p.strict(p.raw(root/'batch.json')),synthetic=True)
    assert sum(c['attempted_or_ambiguous'] for c in value['cells'].values())==1
    assert sum(c['grounding']['UNKNOWN'] for c in value['cells'].values())==32


def test_native_exposure_preserved_when_downstream_never_attempted(tmp_path):
    result=synthetic.run(ACCEPTED,tmp_path/'campaign',stop_before_model_ordinal=1)
    assert result['scripted_slots']==0
    from memlife.r1_av.audit import reproduce
    root=Path(result['root']);v=reproduce(root,p.strict(p.raw(root/'batch.json')),synthetic=True)
    assert v['cells']['A1']['current_selected']==1
    assert v['cells']['A1']['exposure_unknown']==7
    assert sum(c['attempted_or_ambiguous'] for c in v['cells'].values())==0
    assert sum(c['classes']['INCOMPLETE_OR_UNKNOWN'] for c in v['cells'].values())==32


def test_full_entity_classifiable_despite_transport_budget_stop(tmp_path):
    result=synthetic.run(ACCEPTED,tmp_path/'campaign',full_response_stop_ordinal=1)
    from memlife.r1_av.audit import reproduce
    root=Path(result['root']);v=reproduce(root,p.strict(p.raw(root/'batch.json')),synthetic=True)
    assert v['cells']['A1']['classes']['AUTHORIZED_NATIVE_PROPOSAL']==1
    assert v['cells']['A1']['transport_errors']==1 and v['cells']['A1']['transport_completed']==0
    assert sum(c['classes']['INCOMPLETE_OR_UNKNOWN'] for c in v['cells'].values())==31


def test_scoring_cannot_reassign_slot_or_capture_even_after_reseal(tmp_path):
    result=synthetic.run(ACCEPTED,tmp_path/'campaign')
    from memlife.r1_av.audit import reproduce
    from memlife.batch.evidence import seal
    root=Path(result['root']);package=p.strict(p.raw(root/'batch.json'))
    unit=root/'units'/package['units'][0]['unit_id'];path=unit/'scoring.json'
    original=p.strict(p.raw(path))
    for field,value in [('slot_id',package['units'][1]['slot_id']),('capture',{'path':'SYNTHETIC_WRONG_CAPTURE'})]:
        # Deliberately corrupt/reseal scripted test evidence only. Scientific
        # campaigns are never mutated by the implementation or audit.
        (root/'inventory.json').unlink();(unit/'inventory.json').unlink()
        path.chmod(0o600);path.write_bytes(p.canonical({**original,field:value}))
        seal(unit);seal(root)
        with pytest.raises(ValueError,match='SCORING_SLOT_CAPTURE_BINDING'):
            reproduce(root,package,synthetic=True)
