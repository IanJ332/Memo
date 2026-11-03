"""V2 first-cell qualification, all provider I/O replaced by in-memory fakes."""
import json
import multiprocessing
import os
import sqlite3
import threading
import time
import socket
from types import SimpleNamespace

import pytest
from scripts import nlip_phase2b2_launcher as launcher
from scripts import nlip_phase2b1_pilot as pilot
from memlife.nlip import model_adapter as adapter

@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def denied(*args,**kwargs): raise AssertionError('NETWORK_PROHIBITED')
    monkeypatch.setattr(socket,'socket',denied)
    monkeypatch.setattr(socket,'getaddrinfo',denied)


def envelope(recipient='authorized@example.invalid', *, outcome='PROPOSE_ACTION', model=launcher.DEFAULT_MODEL, usage=None, request_id=None):
    value={'outcome':outcome,'tool':'send_report','arguments':{'project_id':'pilot-project','recipient':recipient}}
    if outcome == 'ABSTAIN': value.update(tool=None,arguments=None)
    data={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(value)}}]}
    if model is not None: data['model']=model
    if usage is not None: data['usage']=usage
    if request_id is not None: data['id']=request_id
    return json.dumps(data).encode()

@pytest.fixture(params=['fake', 'direct'])
def run(tmp_path, monkeypatch, request):
    monkeypatch.setattr(launcher,'PROTOCOL_LEDGER',tmp_path/'ledger.sqlite')
    def invoke(payload=None, name='evidence', fake_transport=None, window=None):
        now=time.time()
        if request.param == 'direct':
            io=adapter.ScriptedDirectIO([])
            source=fake_transport if fake_transport is not None else launcher.FakeTransport([envelope() if payload is None else payload])
            def read(req, timeout, limit):
                result=source.send(req.data,timeout,limit)
                # ScriptedDirectIO models raw bytes, not an HTTP-header envelope.
                return result.body if type(result) is adapter.TransportResponse else result
            io.read=read
            return launcher.hosted_first_cell_operator(tmp_path/name, authorization_window=window or (now-10,now+60),
                package_digest=launcher.digest(launcher.INVENTORY), offline_io=io)
        return launcher.first_cell_operator(tmp_path/name,[envelope() if payload is None else payload],
            authorization_window=window or (now-10,now+60),package_digest=launcher.digest(launcher.INVENTORY),protocol='v2', fake_transport=fake_transport)
    return invoke

def test_01_success(run):
    r=run(); assert (r['scenario_id'],r['arm'],r['model_status'],r['retries'])==('authorized','ON','ACCEPTED',0)

def test_02_invalid_json(run):
    r=run(b'not json'); assert r['error']=='MALFORMED_RESPONSE' and r['dispatch_status']=='NOT_STARTED'

def test_03_unsupported_envelope(run):
    r=run(json.dumps({'model':launcher.DEFAULT_MODEL,'choices':[{'finish_reason':'stop','message':{'tool_calls':[],'content':None}}]}).encode())
    assert r['error']=='MALFORMED_RESPONSE' and r['dispatch_status']=='NOT_STARTED'

def test_03_schema_http_rejection(run,monkeypatch):
    def reject(*args): raise adapter.ModelError('PROVIDER_HTTP_ERROR')
    monkeypatch.setattr(launcher.FakeTransport,'send',reject)
    r=run(); assert r['error']=='PROVIDER_HTTP_ERROR' and r['dispatch_status']=='NOT_STARTED'

def test_04_wrong_model(run):
    r=run(envelope(model='different')); assert r['error']=='MODEL_IDENTITY_MISMATCH' and r['dispatch_status']=='NOT_STARTED'

def test_05_missing_model(run):
    r=run(envelope(model=None)); assert r['error']=='MODEL_IDENTITY_MISMATCH' and r['dispatch_status']=='NOT_STARTED'

def test_06_missing_usage(run):
    r=run(envelope(request_id='chatcmpl_test')); assert r['usage'] is None and r['delivered'] is True

def test_07_missing_id(run):
    r=run(envelope(usage={'total_tokens':10})); assert r['completion_id'] is None and r['http_request_id'] is None and r['delivered'] is True

def test_08_abstention(run):
    r=run(envelope(outcome='ABSTAIN')); assert r['model_outcome']=='ABSTAIN' and r['dispatch_status']=='NOT_STARTED' and r['delivered'] is False

def test_08_refusal_envelope(run):
    raw=json.dumps({'model':launcher.DEFAULT_MODEL,'choices':[{'finish_reason':'stop','message':{'content':None,'refusal':'synthetic refusal'}}]}).encode()
    r=run(raw); assert r['error']=='MALFORMED_RESPONSE' and r['dispatch_status']=='NOT_STARTED'

def test_09_malformed_proposal(run):
    data=json.loads(envelope()); data['choices'][0]['message']['content']='{"outcome":"PROPOSE_ACTION","tool":"send_report","arguments":{}}'
    r=run(json.dumps(data).encode()); assert r['error']=='MALFORMED_RESPONSE' and r['dispatch_status']=='NOT_STARTED'

def test_10_unauthorized_recipient(run):
    r=run(envelope(recipient='attacker@example.invalid')); assert r['oracle']=='UNAUTHORIZED' and r['delivered'] is False and r['dispatcher_decision']=='DENY'

def test_11_dispatcher_rejection(run,monkeypatch):
    original=pilot.Pilot._fixture
    def fixture(self,scenario):
        values=original(self,scenario); values[2].logout(values[3].sid); return values
    monkeypatch.setattr(pilot.Pilot,'_fixture',fixture)
    r=run(); assert r['dispatch_status']=='REJECTED_AT_BOUNDARY' and r['delivered'] is False

def test_12_synthetic_delivery(run,tmp_path):
    r=run(); assert r['dispatcher_decision']=='ALLOW' and r['commit_status']=='COMMITTED' and r['delivered'] is True
    with sqlite3.connect(tmp_path/'evidence') as db: assert json.loads(db.execute('select observation from attempts').fetchone()[0])==r

def test_13_provider_timeout(run,monkeypatch):
    def timeout(*args): raise TimeoutError()
    monkeypatch.setattr(launcher.FakeTransport,'send',timeout)
    r=run(); assert r['error']=='TIMEOUT' and r['dispatch_status']=='NOT_STARTED'

def test_14_late_response(run,monkeypatch,tmp_path):
    original=pilot.Pilot.__init__
    def init(self,*a,**kw): return original(self,*a,request_seconds=.15,**kw)
    monkeypatch.setattr(pilot.Pilot,'__init__',init)
    entered=threading.Event(); release=threading.Event(); returned=threading.Event()
    def send(*args):
        entered.set(); release.wait(5); returned.set(); return envelope()
    monkeypatch.setattr(launcher.FakeTransport,'send',send)
    try:
        r=run(); assert entered.is_set() and r['dispatch_status']=='NOT_STARTED' and r['delivered'] is False
    finally:
        release.set(); assert returned.wait(5)
    with sqlite3.connect(tmp_path/'evidence') as db: assert json.loads(db.execute('select observation from attempts').fetchone()[0])==r

def test_15_utc_expiry(run,monkeypatch):
    original=pilot.Pilot._fixture; calls=[]
    def fixture(self,s):
        values=original(self,s); self.authorization_window=(0,1); return values
    monkeypatch.setattr(pilot.Pilot,'_fixture',fixture)
    monkeypatch.setattr(launcher.FakeTransport,'send',lambda *a: calls.append(1))
    r=run(); assert r['error']=='AUTHORIZATION_EXPIRED' and not calls and r['dispatch_status']=='NOT_STARTED'

def test_16_duplicate_reservation(run):
    run()
    with pytest.raises(launcher.GateError,match='FIRST_CELL_ALREADY_RESERVED'): run(name='other')

def _interrupt(root,ready):
    from pathlib import Path
    launcher.PROTOCOL_LEDGER=Path(root)/'ledger.sqlite'
    class Stop:
        def __init__(self,*a,**kw): ready.set(); time.sleep(30)
    pilot.Pilot=Stop
    now=time.time()
    launcher.hosted_first_cell_operator(Path(root)/'first',offline_io=adapter.ScriptedDirectIO([envelope()]),authorization_window=(now-1,now+60),package_digest=launcher.digest(launcher.INVENTORY))

def test_17_process_death(run,tmp_path):
    ctx=multiprocessing.get_context('fork'); ready=ctx.Event(); process=ctx.Process(target=_interrupt,args=(str(tmp_path),ready)); process.start()
    try: assert ready.wait(10)
    finally: process.terminate(); process.join(10)
    with pytest.raises(launcher.GateError,match='FIRST_CELL_ALREADY_RESERVED'): run(name='other')

def test_18_evidence_failure(run,monkeypatch):
    monkeypatch.setattr(pilot.Pilot,'_save',lambda *a: (_ for _ in ()).throw(OSError('synthetic failure')))
    with pytest.raises(launcher.GateError,match='OPERATOR_FAILED'): run()
    with pytest.raises(launcher.GateError,match='FIRST_CELL_ALREADY_RESERVED'): run(name='other')

def test_19_secret_exclusion(run,tmp_path,monkeypatch,capsys):
    secret='synthetic-secret-3r-413'; monkeypatch.setenv('SYNTHETIC_SECRET',secret)
    r=run(); assert secret not in json.dumps(r) and secret not in str(capsys.readouterr())
    for path in tmp_path.rglob('*'):
        if path.is_file(): assert secret.encode() not in path.read_bytes()

def test_20_commercial_rejected(run,monkeypatch):
    calls=[]; original=launcher.FakeTransport.send
    def send(self,body,*args):
        calls.append(json.loads(body)); return original(self,body,*args)
    monkeypatch.setattr(launcher.FakeTransport,'send',send)
    r=run(); assert r['delivered'] and calls[0]['model']==launcher.DEFAULT_MODEL
    with pytest.raises(ValueError): adapter.JetstreamDirectTransport(provider='openai',model=launcher.DEFAULT_MODEL)
    assert adapter.JETSTREAM_ENDPOINT=='https://llm.jetstream-cloud.org/qwen-3.8-27b/v1/chat/completions'

def test_21_no_model_fallback(run,monkeypatch):
    calls=[]; original=launcher.FakeTransport.send
    def send(self,body,*args): calls.append(json.loads(body)['model']); return original(self,body,*args)
    monkeypatch.setattr(launcher.FakeTransport,'send',send)
    r=run(envelope(model='other')); assert r['error']=='MODEL_IDENTITY_MISMATCH' and calls==[launcher.DEFAULT_MODEL]

def test_22_no_second_cell(run,monkeypatch,tmp_path):
    calls=[]; original=launcher.FakeTransport.send
    def send(self,body,*args): calls.append(1); return original(self,body,*args)
    monkeypatch.setattr(launcher.FakeTransport,'send',send)
    injected=launcher.FakeTransport([envelope(),envelope()])
    r=run(fake_transport=injected); assert r['delivered'] is True and len(calls)==1 and injected.calls==1
    with sqlite3.connect(tmp_path/'evidence') as db: assert db.execute('select scenario,arm from attempts').fetchall()==[('authorized','ON')]
    with pytest.raises(launcher.GateError,match='FIRST_CELL_ALREADY_RESERVED'): run(name='another')
    assert len(calls)==1

def test_v2_dispatch_expiry_and_late_commit(run,monkeypatch):
    now=time.time(); end=now+60; wall=[now]
    monkeypatch.setattr(pilot,'time',SimpleNamespace(time=lambda:wall[0],monotonic=time.monotonic))
    original=pilot.Pilot._fixture
    def fixture(self,scenario):
        values=original(self,scenario); policy=values[4]; connection=policy._connection
        class Late:
            def __init__(self,db): self.db=db
            def __getattr__(self,key): return getattr(self.db,key)
            def commit(self): self.db.commit(); wall[0]=end
        policy._connection=lambda write=False: Late(connection(write)) if write else connection(write)
        return values
    monkeypatch.setattr(pilot.Pilot,'_fixture',fixture)
    # Fix operator window to the same controlled end; do not alter monotonic time.
    monkeypatch.setattr(launcher,'time',SimpleNamespace(time=lambda:now,monotonic=time.monotonic))
    r=run(window=(now-10,end)); assert r['utc_admission'] < end <= r['utc_commit_return']
    assert r['delivered'] is True and r['commit_status']=='COMMITTED'
    assert r['utc_window_status']=='COMMIT_RETURNED_AFTER_WINDOW' and r['deadline_status']=='COMMIT_RETURNED_WITHIN_DEADLINE'

def test_v2_dispatch_expiry_rejects(run,monkeypatch):
    now=time.time(); end=now+60; wall=[now]
    monkeypatch.setattr(pilot,'time',SimpleNamespace(time=lambda:wall[0],monotonic=time.monotonic))
    monkeypatch.setattr(launcher,'time',SimpleNamespace(time=lambda:now,monotonic=time.monotonic))
    original=pilot.Pilot._save
    def save(self,row):
        original(self,row)
        if row['state']=='DISPATCH_IN_PROGRESS': wall[0]=end
    monkeypatch.setattr(pilot.Pilot,'_save',save)
    r=run(window=(now-10,end)); assert r['utc_admission'] is None and r['utc_window_status']=='EXPIRED_BEFORE_ADMISSION'
    assert r['commit_status']=='NOT_COMMITTED' and r['delivered'] is False

def test_v2_commit_uncertainty(run,monkeypatch):
    original=pilot.Pilot._fixture
    def fixture(self,scenario):
        values=original(self,scenario)
        def unavailable(): raise sqlite3.OperationalError('synthetic')
        values[4].audits=unavailable
        return values
    monkeypatch.setattr(pilot.Pilot,'_fixture',fixture)
    r=run(); assert r['commit_status']=='UNKNOWN' and r['delivered'] is None and r['deadline_status']=='UNKNOWN'

def test_v2_pinned_direct_transport_with_fake_opener(run,monkeypatch):
    calls=[]
    class Response:
        status=200
        headers={'content-type':'application/json','x-request-id':'req_matrix_fixture'}
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self,limit): return envelope()
    class Opener:
        def open(self,request,timeout):
            calls.append((request.full_url,request.get_header('Authorization'),json.loads(request.data)))
            return Response()
    monkeypatch.setattr(adapter.urllib.request,'build_opener',lambda *handlers: Opener())
    def send(self,body,timeout,max_bytes):
        return adapter.JetstreamDirectTransport(provider='jetstream2_direct',model=launcher.DEFAULT_MODEL).send(body,timeout,max_bytes)
    monkeypatch.setattr(launcher.FakeTransport,'send',send)
    r=run(); assert r['delivered'] is True and len(calls)==1
    assert calls[0][0]==adapter.JETSTREAM_ENDPOINT and calls[0][1] is None and calls[0][2]['model']==launcher.DEFAULT_MODEL
