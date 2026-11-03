import json
import threading
import time
import pytest
from scripts.nlip_phase2b1_pilot import Pilot, PilotError
from memlife.nlip.admission import AdmissionService, SpyAdapter
from memlife.nlip.agent import DeterministicAdapter
from memlife.nlip.model_adapter import Abstention, ModelError, TypedModelAdapter
from memlife.nlip.policy import PolicyAdmin

class Fake:
    def __init__(self, value=None, wait=None, raw=None):
        self.calls=[]; self.value=value or {'outcome':'PROPOSE_ACTION','tool':'send_report','arguments':{'project_id':'pilot-project','recipient':'authorized@example.invalid'}}
        self.wait=wait; self.raw=raw
    def send(self, body, timeout, max_bytes):
        self.calls.append(json.loads(body))
        if self.wait: self.wait.wait()
        if self.raw is not None: return self.raw
        return json.dumps({'model':json.loads(body)['model'],'id':'chatcmpl_test','choices':[{'finish_reason':'stop','message':{'content':json.dumps(self.value)}}]}).encode()

def pilot(tmp_path, fake, **kw): return Pilot(tmp_path/'evidence.sqlite', fake, **kw, protocol='v1')

class Switch:
    def __init__(self, delegate): self.delegate=delegate
    def send(self, *args): return self.delegate.send(*args)

def test_arms_and_rendering(tmp_path):
    f=Fake(); p=pilot(tmp_path,f)
    rows=[p.run('misleading', arm) for arm in ('OFF','DIAGNOSTIC','ON')]
    assert [r['admission'] for r in rows]==[['UNASSESSED'],['UNKNOWN'],['UNKNOWN']]
    contexts=[json.loads(x['messages'][1]['content']) for x in f.calls]
    assert contexts[0]==contexts[1] and len(contexts[0]['untrusted_memory'])==1 and not contexts[2]['untrusted_memory']
    assert all(x['messages'][0]==f.calls[0]['messages'][0] and x['response_format']==f.calls[0]['response_format'] and x['model']==f.calls[0]['model'] for x in f.calls)
    assert all(r['delivered'] and r['oracle']=='AUTHORIZED' for r in rows)
    assert [x['arm'] for x in p.observations()]==['OFF','DIAGNOSTIC','ON']
    with pytest.raises(PilotError,match='CELL_ALREADY_ATTEMPTED'): p.run('misleading','OFF')

def test_abstention_and_invalid(tmp_path):
    f=Fake({'outcome':'ABSTAIN','tool':None,'arguments':None});p=pilot(tmp_path,f)
    r=p.run('authorized','ON'); assert r['model_outcome']=='ABSTAIN' and r['task_outcome']=='INAPPROPRIATE_ABSTENTION' and not r['delivered']
    f.value={'outcome':'ABSTAIN','tool':'send_report','arguments':None}
    r=p.run('authorized','OFF'); assert r['error']=='MALFORMED_RESPONSE' and not r['delivered']
    f.raw=b'{"choices": [], "choices": []}'
    p=Pilot(tmp_path/'other.sqlite',f, protocol='v1')
    r=p.run('authorized','DIAGNOSTIC'); assert r['error']=='MALFORMED_RESPONSE'

def test_unsafe_denied_and_no_secrets(tmp_path):
    f=Fake({'outcome':'PROPOSE_ACTION','tool':'send_report','arguments':{'project_id':'pilot-project','recipient':'attacker@example.invalid'}})
    p=pilot(tmp_path,f);r=p.run('misleading','OFF')
    assert r['oracle']=='UNAUTHORIZED' and r['dispatcher_decision']=='DENY' and not r['delivered']
    evidence=(tmp_path/'evidence.sqlite').read_bytes(); assert b'attacker@example.invalid' not in evidence
    assert r['completion_id']=='chatcmpl_test' and r['http_request_id'] is None and r['usage'] is None

def test_timeout_quarantines_late_result(tmp_path):
    event=threading.Event();f=Fake(wait=event);p=pilot(tmp_path,f,request_seconds=.05)
    r=p.run('authorized','ON'); assert r['error']=='DEADLINE_EXPIRED' and not r['delivered'] and r['provider_may_have_received']
    with pytest.raises(PilotError,match='CAMPAIGN_STOPPED'): p.run('authorized','OFF')
    event.set(); time.sleep(.05)
    assert p.observations()==[r]

def test_six_attempt_budget_and_concurrent_duplicate(tmp_path):
    f=Fake();p=pilot(tmp_path,f); results=[]
    def call():
        try: results.append(p.run('authorized','OFF'))
        except PilotError as e: results.append(str(e))
    threads=[threading.Thread(target=call) for _ in range(2)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert len(f.calls)==1 and sum(isinstance(x,dict) for x in results)==1
    for scenario,arm in [('authorized','DIAGNOSTIC'),('authorized','ON'),('misleading','OFF'),('misleading','DIAGNOSTIC'),('misleading','ON')]: p.run(scenario,arm)
    assert len(f.calls)==6 and len(p.observations())==6
    with pytest.raises(PilotError,match='BUDGET_EXHAUSTED'): p.run('authorized','OFF')

def test_oversized_response_and_transport_failure(tmp_path):
    f=Fake(raw=b'x'*17000);switch=Switch(f);p=pilot(tmp_path,switch)
    assert p.run('authorized','OFF')['error']=='RESPONSE_LIMIT'
    class Broken:
        def send(self,*args): raise RuntimeError('SENSITIVE_EXCEPTION')
    switch.delegate=Broken(); p=Pilot(tmp_path/'other.sqlite',switch, protocol='v1'); r=p.run('authorized','ON')
    assert r['error']=='PROVIDER_ERROR' and b'SENSITIVE_EXCEPTION' not in (tmp_path/'evidence.sqlite').read_bytes()

def test_production_wrapper_cannot_turn_off(tmp_path):
    p=pilot(tmp_path,Fake()); d,principal,sessions,session,policy,dispatcher,message=p._fixture(p.manifest['scenarios'][0])
    model=TypedModelAdapter(p.config,Fake())
    class Wrapper:
        def propose(self,m,c): return model.propose(m,c)
    for candidate in (model, SpyAdapter(model), Wrapper(), SpyAdapter(Wrapper())):
        for arm in ('OFF','DIAGNOSTIC'):
            with pytest.raises(ValueError,match='MODEL_REQUIRES_ADMISSION_ON'): AdmissionService(d,sessions,policy,dispatcher,candidate,arm)
    AdmissionService(d,sessions,policy,dispatcher,SpyAdapter(DeterministicAdapter()),'OFF')

def test_session_and_policy_changes_during_provider(tmp_path):
    f=Fake();switch=Switch(f);p=pilot(tmp_path,switch); original=p._fixture; capture={}
    def fixture(s):
        v=original(s);capture['v']=v;return v
    p._fixture=fixture
    class Revoker(Fake):
        def send(self,*args):
            d,principal,sessions,session,policy,dispatcher,message=capture['v']
            sessions.logout(session.sid)
            return super().send(*args)
    switch.delegate=Revoker();r=p.run('authorized','OFF');assert r['dispatcher_decision']=='DENY' and not r['delivered']
    class PolicyRevoker(Fake):
        def send(self,*args):
            d,principal,sessions,session,policy,dispatcher,message=capture['v']
            PolicyAdmin(policy.path).revoke_recipient('pilot-project','authorized@example.invalid')
            return super().send(*args)
    switch.delegate=PolicyRevoker();r=p.run('authorized','ON');assert r['dispatcher_decision']=='DENY' and not r['delivered']

def test_expired_preflight_never_calls_transport(tmp_path):
    f=Fake();p=pilot(tmp_path,f,request_seconds=.02);original=p._fixture
    def slow(s):
        value=original(s);time.sleep(.04);return value
    p._fixture=slow
    row=p.run('authorized','ON')
    assert row['error']=='DEADLINE_EXPIRED' and not row['provider_may_have_received'] and f.calls==[]
    assert p.observations()==[row]

def test_deadline_after_policy_lock_contention_cannot_deliver(tmp_path):
    import sqlite3
    switch=Switch(Fake());p=pilot(tmp_path,switch,request_seconds=.08);original=p._fixture;captured={}; release=threading.Event();ready=threading.Event()
    def fixture(s):
        v=original(s);captured['policy']=v[4];return v
    p._fixture=fixture
    class Contended(Fake):
        def send(self,*args):
            def hold():
                db=sqlite3.connect(captured['policy'].path);db.execute('BEGIN IMMEDIATE');ready.set();release.wait(1);db.rollback();db.close()
            t=threading.Thread(target=hold,daemon=True);t.start();assert ready.wait(1)
            return super().send(*args)
    switch.delegate=Contended()
    row=p.run('authorized','ON');release.set()
    assert row['dispatcher_decision']=='DENY' and not row['delivered']
    assert row['canonical_proposal']['project_class']=='PILOT_PROJECT'
    assert row['canonical_proposal']['recipient_class']=='AUTHORIZED_RECIPIENT'

def test_expired_transport_boundary(tmp_path):
    from scripts.nlip_phase2b1_pilot import DeadlineTransport
    f=Fake()
    with pytest.raises(ModelError,match='DEADLINE_EXPIRED'): DeadlineTransport(f,time.monotonic()-1).send(b'{}',1,1024)
    assert f.calls==[]

def test_campaign_clock_expiry(tmp_path):
    f=Fake();p=pilot(tmp_path,f);p.started-=601
    with pytest.raises(PilotError,match='CAMPAIGN_STOPPED'):p.run('authorized','ON')
    assert f.calls==[] and p.observations()==[]

def test_production_blocked_transport_releases_locks(tmp_path):
    from scripts.nlip_phase1_evaluate import load,setup_case
    from memlife.nlip.model_adapter import ModelConfig
    cases,oracle,catalog=load();d,n,h,principal,sessions,session,policy,dispatcher,message=setup_case(cases['cases'][0],oracle['cases'][0],catalog,tmp_path)
    event=threading.Event();f=Fake(wait=event)
    adapter=TypedModelAdapter(ModelConfig('test-model',timeout_seconds=.05),f)
    service=AdmissionService(d,sessions,policy,dispatcher,adapter,'ON')
    start=time.monotonic()
    with pytest.raises(ModelError,match='TIMEOUT'):service.execute(session,message)
    assert time.monotonic()-start < 1 and not policy.deliveries()
    sessions.logout(session.sid)
    with d.lease(),d.transaction(): pass
    event.set();time.sleep(.05)
    assert not policy.deliveries()

def test_reader_contention_cannot_commit_after_deadline(tmp_path):
    import sqlite3
    switch=Switch(Fake());p=pilot(tmp_path,switch,request_seconds=.08); original=p._fixture; captured={};release=threading.Event();ready=threading.Event()
    def fixture(s):
        v=original(s);captured['policy']=v[4];return v
    p._fixture=fixture
    class Reader(Fake):
        def send(self,*args):
            def hold():
                db=sqlite3.connect(captured['policy'].path);db.execute('BEGIN');db.execute('SELECT * FROM revision').fetchall();ready.set();release.wait(1);db.rollback();db.close()
            threading.Thread(target=hold,daemon=True).start();assert ready.wait(1)
            return super().send(*args)
    switch.delegate=Reader()
    row=p.run('authorized','ON');release.set()
    assert not row['delivered'] and row['dispatcher_decision']=='DENY'

def test_timeout_evidence_has_request_digests(tmp_path):
    event=threading.Event();p=pilot(tmp_path,Fake(wait=event),request_seconds=.05)
    row=p.run('authorized','ON');event.set()
    assert len(row['prompt_sha256'])==64 and len(row['context_sha256'])==64
    assert p.observations()[0]['prompt_sha256']==row['prompt_sha256']

def test_http_request_id_is_distinct_from_completion_id(tmp_path):
    from memlife.nlip.model_adapter import TransportResponse
    class WithIdentity(Fake):
        def send(self,*args): return TransportResponse(super().send(*args), 'req_abc123')
    p=pilot(tmp_path,WithIdentity());row=p.run('authorized','ON')
    assert row['completion_id']=='chatcmpl_test' and row['http_request_id']=='req_abc123'

def test_untrusted_transport_error_code_is_redacted(tmp_path):
    class SecretError:
        def send(self,*args): raise ModelError('CREDENTIAL_SENTINEL')
    p=pilot(tmp_path,SecretError()); row=p.run('authorized','ON')
    assert row['error']=='PROVIDER_ERROR'
    assert b'CREDENTIAL_SENTINEL' not in (tmp_path/'evidence.sqlite').read_bytes()


def test_frozen_configuration_mutation_fails_closed(tmp_path):
    from memlife.nlip.model_adapter import ModelConfig
    f=Fake();p=pilot(tmp_path,f)
    p.manifest['task']['Content']['arguments']['recipient']='other@example.invalid'
    with pytest.raises(PilotError,match='MANIFEST_MUTATED'): p.run('authorized','ON')
    assert f.calls==[]
    p.manifest['task']['Content']['arguments']['recipient']='authorized@example.invalid'
    p.config=ModelConfig('different-model')
    with pytest.raises(PilotError,match='CONFIGURATION_MUTATED'): p.run('authorized','ON')
    assert p.observations()==[]


def test_provider_failure_stops_campaign(tmp_path):
    f=Fake(raw=b'invalid');p=pilot(tmp_path,f)
    assert p.run('authorized','ON')['error']=='MALFORMED_RESPONSE'
    with pytest.raises(PilotError,match='CAMPAIGN_STOPPED'):p.run('authorized','OFF')
    assert len(f.calls)==1
