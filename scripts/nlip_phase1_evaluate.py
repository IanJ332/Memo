# SPDX-License-Identifier: MIT
"""Replay frozen synthetic cases through SQLite, admission, spy and dispatcher."""
import base64
import hashlib
import json
import tempfile
import time
from pathlib import Path
from memlife.nlip.admission import AdmissionService, SpyAdapter
from memlife.nlip.agent import DeterministicAdapter
from memlife.nlip.auth import Principal, Session, SessionAuthority
from memlife.nlip.custody import Database, HostAdmin, Notes
from memlife.nlip.dispatcher import ProtectedDispatcher
from memlife.nlip.policy import PolicyAdmin, PolicyStore
from memlife.nlip.wire import parse_message

FREEZE=Path(__file__).resolve().parents[1]/'docs/research/nlip-context-admission-phase0-20261029/evaluation/v2'
PIN='31681cefe95e2d9ba1ac0845c2a270c13797be7dc4b77d2a37b660d3f283f682'
def load():
    raw=(FREEZE/'manifest.json').read_bytes(); assert hashlib.sha256(raw).hexdigest()==PIN
    manifest=json.loads(raw)
    for x in manifest['members']:
        b=(FREEZE/x['path']).read_bytes(); assert len(b)==x['size_bytes'] and hashlib.sha256(b).hexdigest()==x['sha256']
    return [json.loads((FREEZE/f).read_bytes()) for f in ('cases.json','oracle.json','host-source-catalog.json')]

def rename_fixture(d, table, old, new):
    # Assign frozen, application-owned fixture IDs after API issuance. This is
    # trusted harness setup, not a note ingestion interface.
    with d.lease(),d.transaction() as db:
        if table=='reservations': db.execute('UPDATE reservations SET id=? WHERE id=?',(new,old))
        else:
            db.execute('UPDATE notes SET id=? WHERE id=?',(new,old));db.execute('UPDATE routes SET id=? WHERE id=?',(new,old))

def setup_case(case, oracle, catalog, root):
    d=Database.create(root/'notes.sqlite','fixture-notes-store-01');n=Notes(d);h=HostAdmin(d)
    sc=case['effective_notes'][0]['scope']; p=Principal(sc['issuer'],sc['subject']);project=sc['project_id']
    sessions=SessionAuthority(); session=Session('fixture-sid',p,int(time.time())+600,'fixture-conversation-01','fixture-csrf',sessions);sessions._sessions[session.sid]=session
    pa=PolicyAdmin.create(root/'policy.sqlite');pa.set_policy(p,project,['reports-alpha@example.invalid'])
    policy=PolicyStore(root/'policy.sqlite'); dispatcher=ProtectedDispatcher(policy,sessions=sessions)
    sources={s['event_id']:s for s in catalog['sources']}; approved=set()
    def approve(a):
        event=a['event_id']
        if event not in approved:
            src=sources[event];h.approve_source(src['source_id'],event,src['content_utf8'],a['host_revision']);approved.add(event)
    def insert(note):
        body=base64.b64decode(note['content_base64']).decode('utf-8');rid=note['record_id']
        if note['requested_use']=='reference':
            generated=n.append(p,project,body);rename_fixture(d,'notes',generated,rid)
        else:
            generated=h.reserve(p,project);rename_fixture(d,'reservations',generated,rid);h.persist_reserved(p,project,rid,body)
    for note in case['initial_application']['notes']: insert(note)
    for a in case['initial_host']['associations']:
        approve(a)
        actualscope=(a['scope']['issuer'],a['scope']['subject'],a['scope']['project_id'])
        if actualscope==(p.issuer,p.subject,project) and not any(x['record_id']==a['record_id'] for x in case['initial_host']['associations'][:case['initial_host']['associations'].index(a)]):
            c=h.confirm(p,project,a['record_id'],a['event_id']);h.publish(p,project,a['record_id'],a['event_id'],c)
        else:
            # Frozen negative controls deliberately model foreign or conflicting
            # catalog associations, which the legitimate publisher would reject.
            with d.lease(),d.transaction() as db:
                db.execute('INSERT INTO associations(record_id,issuer,subject,project,event,status,confirmation,host_revision) VALUES(?,?,?,?,?,?,?,?)', (a['record_id'],*actualscope,a['event_id'],a['status'],'synthetic-invalid-confirmation',a['host_revision']))
    # Initial Host snapshot is materialized before any application invocation.
    with d.lease(),d.transaction() as db: db.execute('UPDATE metadata SET generation=?',(case['initial_host']['snapshot_generation'],))
    pending={}
    for e in case['lifecycle_events']:
        kind=e['kind']
        if kind=='APPLICATION_RESERVE_RECORD_ROUTE':
            rid=h.reserve(p,project);rename_fixture(d,'reservations',rid,e['record_id']); pending[e['reservation_id']]=e['record_id']
        elif kind=='NOTE_APPEND':
            note=e['note'];h.persist_reserved(p,project,pending[e['reservation_id']],base64.b64decode(note['content_base64']).decode())
        elif kind=='NOTE_REPLACE': h.replace_for_test(p,project,e['record_id'],base64.b64decode(e['note']['content_base64']).decode())
        elif kind=='HOST_CONFIRM_PERSISTED_RECORD':
            ev=e['event_id']; approve({'event_id':ev,'host_revision':e['host_revision']});pending[e['record_id']]=h.confirm(p,project,e['record_id'],ev)
        elif kind=='HOST_REPLACE_SNAPSHOT':
            entries=e['snapshot']['associations']
            replacements=[a for a in entries if a['status']=='CURRENT' and a['record_id'] in pending]
            superseded=[a for a in entries if a['status']=='SUPERSEDED']
            if superseded and replacements:
                assert len(superseded)==len(replacements)==1
                a=replacements[0];h.supersede_and_publish(p,project,superseded[0]['record_id'],a['record_id'],a['event_id'],pending[a['record_id']])
            else:
                for a in entries:
                    if a['status'] in ('REVOKED','SUPERSEDED'): h.deactivate(p,project,a['record_id'],a['status'])
                    elif a['record_id'] in pending: h.publish(p,project,a['record_id'],a['event_id'],pending[a['record_id']])
        else: raise ValueError(kind)
    message=parse_message(json.dumps(oracle['expected_adapter_input']['message'],ensure_ascii=False).encode())
    return d,n,h,p,sessions,session,policy,dispatcher,message

def run(output):
    cases,oracles,catalog=load(); lookup={o['case_id']:o for o in oracles['cases']}; results=[]
    for case in cases['cases']:
        if not case['executable']: continue
        o=lookup[case['case_id']]; arms={}
        for mode in ('OFF','DIAGNOSTIC','ON'):
            with tempfile.TemporaryDirectory() as tmp:
                d,n,h,p,sessions,session,policy,dispatcher,message=setup_case(case,o,catalog,Path(tmp))
                observed=n.read(p,'report-project-01')
                expected_notes=case['effective_notes']
                assert [(r.record_id,r.revision,base64.b64encode(r.content).decode(),r.use) for r in observed]==[(x['record_id'],x['record_revision'],x['content_base64'],x['requested_use']) for x in expected_notes]
                with d.lease(),d.transaction() as db:
                    generation=db.execute('SELECT generation FROM metadata').fetchone()[0]
                    assert generation==case['effective_host']['snapshot_generation'], (case['case_id'],generation)
                    actual=db.execute('SELECT record_id,issuer,subject,project,event,status,host_revision FROM associations ORDER BY seq').fetchall()
                expected_host=[(a['record_id'],a['scope']['issuer'],a['scope']['subject'],a['scope']['project_id'],a['event_id'],a['status'],a['host_revision']) for a in case['effective_host']['associations']]
                current_keys={row[:4] for row in actual if row[5]=='CURRENT'}
                effective=[row for row in actual if not (row[5]=='SUPERSEDED' and row[:4] in current_keys)]
                assert effective==expected_host,(case['case_id'],effective,expected_host)
                spy=SpyAdapter(DeterministicAdapter());service=AdmissionService(d,sessions,policy,dispatcher,spy,mode)
                outcome,audit,elapsed=service.execute(session,message);payload,sha=spy.captures[0]
                decisions=[{k:v for k,v in x.items() if k in ('record_id','classification','reason')} for x in audit['decisions']]
                expected=[{k:v for k,v in x.items() if k in ('record_id','classification','reason')} for x in o['decisions']]
                if mode!='OFF': assert decisions==expected,(case['case_id'],mode,decisions,expected)
                else: assert all(x['classification']=='UNASSESSED' for x in decisions)
                ids=[x['record_id'] for x in audit['context']]
                if mode=='ON':
                    assert payload==base64.b64decode(o['expected_adapter_input_base64']),(case['case_id'],sha,o['expected_adapter_input_sha256'])
                    assert ids==o['expected_delivered_ids']
                else: assert ids==o['expected_input_ids']
                assert (outcome.decision.action,outcome.decision.reason,outcome.delivered) in {('ALLOW','AUTHORIZED_CURRENT_RECIPIENT',True),('DENY','RECIPIENT_UNAUTHORIZED',False)}
                with d.lease(),d.transaction() as db:
                    durable_audit=[json.loads(row[0]) for row in db.execute('SELECT payload FROM audit ORDER BY seq')]
                assert [row['phase'] for row in durable_audit]==['PRE_HANDOFF','ADAPTER_RETURNED']
                assert durable_audit[0]['invocation']==durable_audit[1]['invocation']
                arms[mode]={'host_snapshot':{k:audit[k] for k in ('store_id','generation','snapshot_sha256','associations','sources','confirmations','events')},'durable_audit':durable_audit,'input':audit['decisions'],'context':audit['context'],'adapter_envelope_base64':base64.b64encode(payload).decode(),'adapter_sha256':sha,'tool_gate':outcome.decision.as_dict(),'delivered':outcome.delivered,'service_elapsed_ns':elapsed}
        results.append({'case_id':case['case_id'],'title':case['title'],'arms':arms})
    output.write_text(json.dumps({'manifest_sha256':PIN,'cases':results,'audit_only':['A01','A02']},indent=2)+'\n')
    print('PASS',len(results),'cases,',len(results)*3,'service executions:',output)

if __name__=='__main__':
    import sys
    run(Path(sys.argv[1]))
