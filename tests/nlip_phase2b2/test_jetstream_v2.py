"""Offline qualification of the draft v2 path; no provider network calls."""
import json
import time
from pathlib import Path

import pytest
from memlife.nlip import model_adapter as adapter
from scripts import nlip_phase2b2_launcher as launcher
from scripts.nlip_phase2b1_pilot import Pilot


def response(model='qwen-3.8-27b', outcome='PROPOSE_ACTION'):
    value = {'outcome':outcome, 'tool':'send_report', 'arguments':{'project_id':'pilot-project','recipient':'authorized@example.invalid'}}
    if outcome == 'ABSTAIN': value.update(tool=None, arguments=None)
    return json.dumps({'model':model,'choices':[{'finish_reason':'stop','message':{'content':json.dumps(value)}}]}).encode()


def test_direct_transport_is_fixed_and_bounded(monkeypatch):
    calls=[]
    class Response:
        status=200
        headers={'content-type':'application/json','x-request-id':'req_bounded_fixture'}
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self,limit): return b'{}'
    class Opener:
        def open(self, request, timeout):
            calls.append((request,timeout)); return Response()
    def opener(*handlers):
        assert any(isinstance(x, adapter.urllib.request.ProxyHandler) for x in handlers)
        assert any(isinstance(x, adapter.urllib.request.HTTPRedirectHandler) for x in handlers)
        return Opener()
    monkeypatch.setattr(adapter.urllib.request, 'build_opener', opener)
    transport=adapter.JetstreamDirectTransport(provider='jetstream2_direct',model=adapter.JETSTREAM_MODEL)
    body=json.dumps({'model':adapter.JETSTREAM_MODEL,'messages':[{'role':'user','content':'fixture'}]}).encode()
    result=transport.send(body, 1, 100)
    assert type(result) is adapter.TransportResponse and result.body==b'{}'
    assert result.http_status==200 and result.http_request_id=='req_bounded_fixture'
    assert result.body_complete is True
    request,_=calls[0]
    assert request.full_url == adapter.JETSTREAM_ENDPOINT and request.get_header('Authorization') is None
    assert 'api.openai.com' not in request.full_url and len(calls)==1
    for invalid in (body.replace(b'qwen-3.8-27b',b'other'), b'x'*65537, b'{"model":"qwen-3.8-27b","model":"other"}'):
        with pytest.raises(adapter.ModelError): transport.send(invalid,1,100)
    assert len(calls)==1
    with pytest.raises(ValueError): adapter.JetstreamDirectTransport(provider='openai',model=adapter.JETSTREAM_MODEL)


def test_real_operator_v2_reservation_and_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher,'PROTOCOL_LEDGER',tmp_path/'ledger.sqlite')
    now=time.time(); path=tmp_path/'evidence.sqlite'
    row=launcher.first_cell_operator(path,[response()],authorization_window=(now-1,now+60),package_digest=launcher.digest(launcher.INVENTORY))
    assert row['manifest_sha256']==launcher.MANIFEST_V2_SHA and row['model']=='qwen-3.8-27b'
    assert row['dispatcher_decision']=='ALLOW' and row['delivered'] is True and row['commit_status']=='COMMITTED'
    assert row['retries']==0 and row['attempt_count']==1
    with pytest.raises(launcher.GateError,match='ALREADY_RESERVED'):
        launcher.first_cell_operator(tmp_path/'other',[response()],authorization_window=(now-1,now+60),package_digest=launcher.digest(launcher.INVENTORY),protocol='v2')


@pytest.mark.parametrize('payload,error',[(response('wrong'),'MODEL_IDENTITY_MISMATCH'),(b'{}','MODEL_IDENTITY_MISMATCH'),(response(outcome='ABSTAIN'),None)])
def test_v2_outcomes_do_not_dispatch(tmp_path,payload,error):
    p=Pilot(tmp_path/'evidence',launcher.FakeTransport([payload]),protocol='v2')
    row=p.run('authorized','ON')
    assert row['error']==error and row['dispatch_status']=='NOT_STARTED' and row['delivered'] is False


def test_v2_declared_deadline_is_enforced(tmp_path):
    with pytest.raises(ValueError,match='INVALID_DEADLINE'):
        Pilot(tmp_path/'evidence',launcher.FakeTransport([]),protocol='v2',request_seconds=31)


def test_off_diagnostic_bytes_equal_and_private_data_excluded(tmp_path, monkeypatch):
    class Capture:
        def __init__(self): self.bodies=[]
        def send(self,body,timeout,max_bytes): self.bodies.append(body); return response(outcome='ABSTAIN')
    monkeypatch.setenv('SYNTHETIC_API_KEY','credential-sentinel-v2')
    capture=Capture(); pilot=Pilot(tmp_path/'evidence',capture,protocol='v2')
    pilot.run('misleading','OFF'); pilot.run('misleading','DIAGNOSTIC')
    assert capture.bodies[0]==capture.bodies[1]
    for body in capture.bodies:
        for private in (b'fixture-issuer',b'fixture-subject',b'credential-sentinel-v2'):
            assert private not in body
