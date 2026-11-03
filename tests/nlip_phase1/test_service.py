import json
import threading
from pathlib import Path
import pytest
from starlette.testclient import TestClient
from memlife.nlip.admission import AdmissionService, SpyAdapter, TypedContext
from memlife.nlip.agent import DeterministicAdapter
from memlife.nlip.app import ReportApplication
from memlife.nlip.custody import Database
from scripts.nlip_phase1_evaluate import load, setup_case

@pytest.fixture
def case(tmp_path):
    cases,oracle,catalog=load(); c=cases['cases'][0];o=oracle['cases'][0]
    return setup_case(c,o,catalog,tmp_path)

def test_real_service_capture_and_gate(case):
    d,n,h,p,sessions,session,policy,dispatcher,message=case
    spy=SpyAdapter(DeterministicAdapter());svc=AdmissionService(d,sessions,policy,dispatcher,spy)
    result,audit,_=svc.execute(session,message)
    assert result.delivered and result.decision.reason=='AUTHORIZED_CURRENT_RECIPIENT'
    assert len(spy.captures)==1 and audit['envelope_sha256']==spy.captures[0][1]
    assert [x['classification'] for x in audit['decisions']]==['REFERENCE','CURRENT']

def test_application_http_path(case):
    d,n,h,p,sessions,session,policy,dispatcher,message=case
    spy=SpyAdapter(DeterministicAdapter());svc=AdmissionService(d,sessions,policy,dispatcher,spy)
    app=ReportApplication(sessions,policy,dispatcher,n,svc,origin='http://localhost')
    client=TestClient(app.app,base_url='http://localhost')
    response=client.post('/nlip',content=json.dumps(message.as_dict()).encode(),headers={'origin':'http://localhost','host':'localhost','x-csrf-token':session.csrf,'cookie':'memlife_session='+session.sid,'content-type':'application/json'})
    assert response.status_code==200 and len(spy.captures)==1 and response.json()['Content']['delivered']

def test_raw_adapter_rejected(case):
    *_,message=case
    with pytest.raises(TypeError,match='TYPED_CONTEXT_REQUIRED'): DeterministicAdapter().propose(message,('raw note',))
    with pytest.raises(TypeError,match='TYPED_CONTEXT_REQUIRED'): SpyAdapter(DeterministicAdapter()).propose(message,('raw note',))

def test_defense_off_rejected(case):
    d,n,h,p,sessions,session,policy,dispatcher,message=case
    from memlife.nlip.dispatcher import ProtectedDispatcher
    off=ProtectedDispatcher(policy,sessions=sessions,engineering_defense_off=True)
    with pytest.raises(ValueError,match='MANDATORY_AUTHORIZATION_REQUIRED'): AdmissionService(d,sessions,policy,off,SpyAdapter(DeterministicAdapter()))

def test_audit_failure_prevents_adapter(case):
    d,n,h,p,sessions,session,policy,dispatcher,message=case
    spy=SpyAdapter(DeterministicAdapter());svc=AdmissionService(d,sessions,policy,dispatcher,spy)
    with d.lease(),d.transaction() as db: db.execute('DROP TABLE audit')
    with pytest.raises(Exception): svc.execute(session,message)
    assert spy.captures==[] and policy.deliveries()==[]

def test_wrong_store_and_conversation(case):
    d,n,h,p,sessions,session,policy,dispatcher,message=case
    foreign=Database(d.path,'foreign')
    with pytest.raises(ValueError,match='INVALID_STORE_IDENTITY'): AdmissionService(foreign,sessions,policy,dispatcher,SpyAdapter(DeterministicAdapter())).execute(session,message)
    sessions.logout(session.sid)
    with pytest.raises(PermissionError,match='INVALID_SESSION'): AdmissionService(d,sessions,policy,dispatcher,SpyAdapter(DeterministicAdapter())).execute(session,message)

def test_publication_waits_through_adapter_handoff(case):
    d,n,h,p,sessions,session,policy,dispatcher,message=case
    rid=n.read(p,'report-project-01')[1].record_id; started=threading.Event();done=threading.Event();workers=[]
    class PausingAdapter(SpyAdapter):
        def propose(self,message,context):
            def revoke(): started.set();h.deactivate(p,'report-project-01',rid,'REVOKED');done.set()
            t=threading.Thread(target=revoke);workers.append(t);t.start();assert started.wait(1);assert not done.wait(.05)
            return super().propose(message,context)
    spy=PausingAdapter(DeterministicAdapter());svc=AdmissionService(d,sessions,policy,dispatcher,spy)
    svc.execute(session,message);workers[0].join(2);assert done.is_set()

def test_logout_waits_through_adapter_handoff(case):
    d,n,h,p,sessions,session,policy,dispatcher,message=case
    started=threading.Event();done=threading.Event();workers=[]
    class PausingAdapter(SpyAdapter):
        def propose(self,message,context):
            def logout(): started.set();sessions.logout(session.sid);done.set()
            t=threading.Thread(target=logout);workers.append(t);t.start();assert started.wait(1);assert not done.wait(.05)
            return super().propose(message,context)
    spy=PausingAdapter(DeterministicAdapter());svc=AdmissionService(d,sessions,policy,dispatcher,spy)
    svc.execute(session,message);workers[0].join(2);assert done.is_set()

def test_phase1_gate_rechecks_recipient_and_rejects_unknown_tool(case):
    d,n,h,p,sessions,session,policy,dispatcher,message=case
    from memlife.nlip.policy import PolicyAdmin
    PolicyAdmin(policy.path).revoke_recipient('report-project-01','reports-alpha@example.invalid')
    result=dispatcher.dispatch(p,session,'send_report',{'project_id':'report-project-01','recipient':'reports-alpha@example.invalid'})
    assert (result.decision.action,result.decision.reason,result.delivered)==('DENY','RECIPIENT_UNAUTHORIZED',False)
    result=dispatcher.dispatch(p,session,'unknown',{'project_id':'report-project-01','recipient':'reports-alpha@example.invalid'})
    assert result.decision.reason=='UNKNOWN_TOOL' and not result.delivered

def test_phase1_gate_rejects_forged_session_and_bad_revision(case):
    d,n,h,p,sessions,session,policy,dispatcher,message=case
    from dataclasses import replace
    args={'project_id':'report-project-01','recipient':'reports-alpha@example.invalid'}
    assert dispatcher.dispatch(p,replace(session), 'send_report',args).decision.reason=='INVALID_SESSION'
    with policy._dispatch_transaction() as db: db.execute('DELETE FROM revision')
    result=dispatcher.dispatch(p,session,'send_report',args)
    assert result.decision.reason=='POLICY_UNAVAILABLE' and not result.delivered

def test_phase1_gate_serializes_policy_change(case):
    d,n,h,p,sessions,session,policy,dispatcher,message=case
    from memlife.nlip.dispatcher import ProtectedDispatcher
    from memlife.nlip.policy import PolicyAdmin
    from memlife.nlip.security import SecurityRegistry, SecurityDecision
    started=threading.Event();finished=threading.Event();workers=[]
    class Extension:
        def authorize_tool_call(self,principal,session,tool,args,snapshot):
            def revoke(): started.set();PolicyAdmin(policy.path).revoke_recipient('report-project-01','reports-alpha@example.invalid');finished.set()
            t=threading.Thread(target=revoke);workers.append(t);t.start();assert started.wait(1);assert not finished.wait(.05)
            return SecurityDecision('ALLOW','OK',snapshot.revision)
    guarded=ProtectedDispatcher(policy,SecurityRegistry([Extension()]),sessions=sessions)
    result=guarded.dispatch(p,session,'send_report',{'project_id':'report-project-01','recipient':'reports-alpha@example.invalid'})
    workers[0].join(2);assert result.delivered and finished.is_set()
    assert dispatcher.dispatch(p,session,'send_report',{'project_id':'report-project-01','recipient':'reports-alpha@example.invalid'}).decision.reason=='RECIPIENT_UNAUTHORIZED'

def test_completion_audit_failure_stops_dispatch(case):
    d,n,h,p,sessions,session,policy,dispatcher,message=case
    with d.lease(),d.transaction() as db:
        db.execute("CREATE TRIGGER reject_second_audit BEFORE INSERT ON audit WHEN (SELECT COUNT(*) FROM audit)>0 BEGIN SELECT RAISE(ABORT,'audit failed'); END")
    spy=SpyAdapter(DeterministicAdapter());svc=AdmissionService(d,sessions,policy,dispatcher,spy)
    with pytest.raises(Exception,match='audit failed'): svc.execute(session,message)
    assert len(spy.captures)==1 and policy.deliveries()==[]
