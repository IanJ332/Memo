"""Scripted HTTP boundary checks; no provider, DNS or socket operation is permitted."""
import hashlib
import http.client
import io
import json
from pathlib import Path
import socket
import stat
import urllib.error
from email.message import Message

import pytest

from memlife.nlip import model_adapter as a
from scripts.nlip_phase2b1_pilot import Pilot


def envelope(model=a.JETSTREAM_MODEL, reason='stop', proposal=None):
    proposal = proposal or {'outcome':'PROPOSE_ACTION', 'tool':'send_report',
        'arguments':{'project_id':'pilot-project', 'recipient':'authorized@example.invalid'}}
    return json.dumps({'model':model, 'id':'completion_test', 'choices':[
        {'finish_reason':reason, 'message':{'content':json.dumps(proposal)}}]}).encode()


@pytest.fixture
def deny_network(monkeypatch):
    def deny(*args, **kwargs): raise AssertionError('NETWORK_PROHIBITED')
    monkeypatch.setattr(socket, 'socket', deny)
    monkeypatch.setattr(socket, 'getaddrinfo', deny)
    monkeypatch.setattr(a.urllib.request, 'build_opener', deny)


@pytest.fixture
def completed_threads(monkeypatch):
    """Execute callbacks inline to exercise the already-completed cutoff branch."""
    class InlineThread:
        def __init__(self, *, target, **kwargs): self.target=target
        def start(self): self.target()
    monkeypatch.setattr(a.threading,'Thread',InlineThread)


def scripted_http(monkeypatch, raw, status=200):
    calls=[]
    headers=Message()
    headers['Content-Type']='application/json'
    headers['X-Request-ID']='req_http_test'
    headers['Set-Cookie']='PRIVATE_COOKIE_NOT_RETAINED'
    class Response(io.BytesIO):
        pass
    class Opener:
        def open(self, request, timeout):
            calls.append((request, timeout))
            if status != 200:
                raise urllib.error.HTTPError(request.full_url, status, 'error', headers, io.BytesIO(raw))
            response=Response(raw); response.status=status; response.headers=headers
            return response
    monkeypatch.setattr(a.urllib.request, 'build_opener', lambda *args:Opener())
    return calls


def run(tmp_path, monkeypatch, raw, status=200):
    calls=scripted_http(monkeypatch, raw, status)
    transport=a.JetstreamDirectTransport(provider='jetstream2_direct', model=a.JETSTREAM_MODEL)
    pilot=Pilot(tmp_path/'evidence.sqlite', transport, protocol='v2')
    return pilot, pilot.run('authorized', 'ON'), calls


def artifact(pilot, row, key):
    path=pilot.path.parent/row[key]
    assert stat.S_IMODE(path.stat().st_mode)==0o600
    assert stat.S_IMODE(path.parent.stat().st_mode)==0o700
    return path.read_bytes()


def test_success_preserves_exact_private_bytes_and_metadata(tmp_path, monkeypatch, deny_network):
    raw=envelope()
    pilot,row,calls=run(tmp_path,monkeypatch,raw)
    assert len(calls)==1 and row['delivered'] and row['retries']==0
    request=artifact(pilot,row,'request_evidence')
    assert request==calls[0][0].data
    assert hashlib.sha256(request).hexdigest()==row['prompt_sha256']
    assert artifact(pilot,row,'response_evidence')==raw
    assert hashlib.sha256(raw).hexdigest()==row['response_sha256']
    assert row['response_body_complete'] is True
    assert row['endpoint']==calls[0][0].full_url==a.JETSTREAM_ENDPOINT
    assert row['model']==row['returned_model']==a.JETSTREAM_MODEL
    assert row['finish_reason']=='stop' and row['http_status']==200
    assert row['schema_validity']=='VALID' and row['http_request_id']=='req_http_test'
    assert set(row['response_headers'])=={'content-type','x-request-id'}
    assert 'PRIVATE_COOKIE_NOT_RETAINED' not in json.dumps(row)
    assert row['application_start_utc']<=row['application_end_utc']
    assert row['application_start_monotonic_ns']<=row['application_end_monotonic_ns']
    assert pilot.observations()==[row]


@pytest.mark.parametrize('status,code',[(400,'PROVIDER_HTTP_ERROR'),(401,'PROVIDER_AUTH'),
                                      (429,'PROVIDER_RATE_LIMIT'),(500,'PROVIDER_HTTP_ERROR')])
def test_http_error_body_private_status_kept_no_retry(tmp_path,monkeypatch,status,code,capsys,deny_network):
    raw=b'{"error":"PRIVATE_PROVIDER_DETAIL"}'
    pilot,row,calls=run(tmp_path,monkeypatch,raw,status)
    assert len(calls)==1 and row['error']==code and row['http_status']==status
    assert not row['delivered'] and row['dispatch_status']=='NOT_STARTED'
    assert artifact(pilot,row,'response_evidence')==raw
    assert row['response_sha256']==hashlib.sha256(raw).hexdigest()
    assert 'PRIVATE_PROVIDER_DETAIL' not in json.dumps(row)
    assert not capsys.readouterr().out
    with pytest.raises(Exception,match='CAMPAIGN_STOPPED'): pilot.run('authorized','DIAGNOSTIC')


@pytest.mark.parametrize('raw,code,model,reason',[
    (envelope(model='wrong-alias'),'MODEL_IDENTITY_MISMATCH','wrong-alias','stop'),
    (envelope(reason='length'),'MALFORMED_RESPONSE',a.JETSTREAM_MODEL,'length'),
    (b'not-json','MALFORMED_RESPONSE',None,None),
])
def test_invalid_provider_result_retains_evidence(tmp_path,monkeypatch,raw,code,model,reason,deny_network):
    pilot,row,calls=run(tmp_path,monkeypatch,raw)
    assert len(calls)==1 and row['error']==code and not row['delivered']
    assert row['returned_model']==model and row['finish_reason']==reason
    assert artifact(pilot,row,'response_evidence')==raw
    assert row['http_status']==200


@pytest.mark.parametrize('status',[200,400])
def test_oversize_response_has_bounded_explicit_prefix(tmp_path,monkeypatch,status,deny_network):
    pilot,row,calls=run(tmp_path,monkeypatch,b'x'*20000,status)
    assert len(calls)==1 and not row['delivered']
    observed=artifact(pilot,row,'response_evidence')
    assert len(observed)==16385 and row['response_body_complete'] is False
    assert row['response_sha256']==hashlib.sha256(observed).hexdigest()
    assert row['error']==('RESPONSE_LIMIT' if status==200 else 'PROVIDER_HTTP_ERROR')


def test_old_bytes_transport_has_unknown_http_metadata(tmp_path,deny_network):
    class Legacy:
        def send(self,*args): return envelope()
    pilot=Pilot(tmp_path/'evidence.sqlite',Legacy(),protocol='v2')
    row=pilot.run('authorized','ON')
    assert row['delivered'] and row['http_status'] is None and row['http_request_id'] is None
    assert artifact(pilot,row,'response_evidence')==envelope()


def test_evidence_capture_failure_prevents_dispatch(tmp_path,monkeypatch,deny_network):
    calls=scripted_http(monkeypatch,envelope())
    pilot=Pilot(tmp_path/'evidence.sqlite',a.JetstreamDirectTransport(
        provider='jetstream2_direct',model=a.JETSTREAM_MODEL),protocol='v2')
    original=pilot._private_artifact
    def fail(directory,name,body):
        if name=='response.body': raise OSError('PRIVATE_FILESYSTEM_DETAIL')
        return original(directory,name,body)
    monkeypatch.setattr(pilot,'_private_artifact',fail)
    row=pilot.run('authorized','ON')
    assert len(calls)==1 and row['error']=='EVIDENCE_WRITE_FAILURE'
    assert not row['delivered'] and row['dispatch_status']=='NOT_STARTED'
    assert 'PRIVATE_FILESYSTEM_DETAIL' not in json.dumps(row)
    with pytest.raises(Exception,match='CAMPAIGN_STOPPED'): pilot.run('authorized','DIAGNOSTIC')


@pytest.mark.parametrize('read_error',[TimeoutError('PRIVATE_TIMEOUT'), OSError('PRIVATE_READ_ERROR'),
                                     http.client.IncompleteRead(b'known partial')])
def test_headers_survive_body_read_failure(tmp_path,monkeypatch,deny_network,read_error):
    headers=Message(); headers['X-Request-ID']='req_headers_observed'
    class Response(io.BytesIO):
        status=200
        def read(self,*args): raise read_error
    class Opener:
        def open(self,*args,**kwargs):
            response=Response(); response.headers=headers; return response
    monkeypatch.setattr(a.urllib.request,'build_opener',lambda *args:Opener())
    pilot=Pilot(tmp_path/'evidence.sqlite',a.JetstreamDirectTransport(
        provider='jetstream2_direct',model=a.JETSTREAM_MODEL),protocol='v2')
    row=pilot.run('authorized','ON')
    assert row['error']==('TIMEOUT' if isinstance(read_error,TimeoutError) else 'PROVIDER_CONNECTION_ERROR')
    assert row['http_status']==200 and row['http_request_id']=='req_headers_observed'
    assert row['response_body_complete'] is False
    assert artifact(pilot,row,'response_evidence')==getattr(read_error,'partial',b'')
    assert row['application_end_utc']>=row['application_start_utc']
    assert 'PRIVATE_' not in json.dumps(row) and not row['delivered']


@pytest.mark.parametrize('error_result',[False,True])
def test_completed_transport_at_deadline_keeps_evidence(monkeypatch,deny_network,error_result,completed_threads):
    clock=[0.0]
    monkeypatch.setattr(a.time,'monotonic',lambda:clock[0])
    response=a.TransportResponse(b'known response',http_status=400 if error_result else 200)
    class Late:
        def send(self,*args):
            clock[0]=2.0
            if error_result: raise a.ModelError('PROVIDER_HTTP_ERROR',response=response)
            return response
    with pytest.raises(a.ModelError,match='TIMEOUT') as caught:
        a._bounded_send(Late(),b'{}',1,1024,1.0)
    assert caught.value.response is response


def test_pilot_retains_completed_late_response_without_dispatch(tmp_path,monkeypatch,deny_network,completed_threads):
    clock=[0.0]
    monkeypatch.setattr(a.time,'monotonic',lambda:clock[0])
    class Late:
        def send(self,*args):
            clock[0]=31.0
            return a.TransportResponse(envelope(),http_status=200)
    pilot=Pilot(tmp_path/'evidence.sqlite',Late(),protocol='v2')
    row=pilot.run('authorized','ON')
    assert row['error']=='DEADLINE_EXPIRED' and row['model_status']=='TIMEOUT'
    assert row['http_status']==200 and row['returned_model']==a.JETSTREAM_MODEL
    assert artifact(pilot,row,'response_evidence')==envelope()
    assert row['provider_evidence_status']=='CAPTURED'
    assert row['dispatch_status']=='NOT_STARTED' and not row['delivered']
