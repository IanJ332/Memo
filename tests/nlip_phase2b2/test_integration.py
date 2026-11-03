import json
import sqlite3
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest
from scripts import nlip_phase2b2_launcher as launcher
from memlife.nlip.model_adapter import ModelError, TransportResponse
from scripts.nlip_phase2b1_pilot import Pilot, PilotError


def response(model=launcher.MODEL):
    data={'id':'chatcmpl_test','choices':[{'finish_reason':'stop','message':{'content':json.dumps({'outcome':'PROPOSE_ACTION','tool':'send_report','arguments':{'project_id':'pilot-project','recipient':'authorized@example.invalid'}})}}]}
    if model is not ...: data['model']=model
    return json.dumps(data).encode()

def claims(path):
    return launcher.AuthorizationBindings('a'*64,launcher.MANIFEST_SHA,launcher.MODEL,'fake-environment',100,200,'FULL_CAMPAIGN',6,Decimal('0.12'),str(path))

@pytest.mark.parametrize('field,value',[
    ('package_digest','b'*64),('manifest_digest','c'*64),('model','other'),
    ('environment','other'),('evidence','/tmp/other'),('scope','FIRST_CELL_ONLY'),
    ('max_attempts',1),('cost_ceiling',Decimal('0.01')),('end_utc',150),
    ('cost_ceiling',Decimal('NaN')),('max_attempts',7)])
def test_claims_mismatch_fails(field,value,tmp_path):
    expected=claims(tmp_path/'evidence'); actual=replace(expected,**{field:value})
    with pytest.raises(launcher.GateError): launcher.check_bindings(actual,expected,125)

def test_claims_missing_and_expired(tmp_path):
    c=claims(tmp_path/'evidence')
    for provided,now in [(None,125),(c,99),(c,200)]:
        with pytest.raises(launcher.GateError): launcher.check_bindings(provided,c,now)
    launcher.check_bindings(c,c,125)

@pytest.mark.parametrize('model',[...,None,{},'other','gpt-4o-mini'])
def test_identity_rejected_before_dispatch(tmp_path,model):
    class RawFake:
        def __init__(self): self.calls=0
        def send(self,*args): self.calls+=1; return response(model)
    f=RawFake();p=Pilot(tmp_path/'evidence.sqlite',f, protocol='v1')
    row=p.run('authorized','ON')
    assert row['error']=='MODEL_IDENTITY_MISMATCH' and row['dispatch_status']=='NOT_STARTED'
    assert row['delivered'] is False and row['commit_status']=='NOT_ATTEMPTED' and f.calls==1
    with pytest.raises(PilotError,match='CAMPAIGN_STOPPED'): p.run('authorized','OFF')
    assert p.observations()==[row] and f.calls==1

def test_identity_valid_and_ids_are_distinct(tmp_path):
    class Fake:
        def send(self,*args): return TransportResponse(response(),'req_http123')
    p=Pilot(tmp_path/'evidence.sqlite',Fake(), protocol='v1');r=p.run('authorized','ON')
    assert r['dispatcher_decision']=='ALLOW' and r['delivered'] is True
    assert r['completion_id']=='chatcmpl_test' and r['http_request_id']=='req_http123' and r['usage'] is None
    assert p.observations()==[r]

def test_synthetic_expiry_stops_between_cells(tmp_path):
    path=tmp_path/'evidence'; c=claims(path); times=iter([125,125,200])
    f=launcher.FakeTransport([response()]*6)
    rows=launcher.fake_campaign(path,'FULL_CAMPAIGN',f,synthetic_claims=c,synthetic_expected=c,clock=lambda:next(times))
    assert len(rows)==f.calls==1

def test_synthetic_first_scope_cannot_be_broadened(tmp_path):
    path=tmp_path/'evidence'; c=replace(claims(path),scope='FIRST_CELL_ONLY',max_attempts=1)
    f=launcher.FakeTransport([response()]*6)
    with pytest.raises(launcher.GateError):
        launcher.fake_campaign(path,'FULL_CAMPAIGN',f,synthetic_claims=c,synthetic_expected=replace(c,scope='FULL_CAMPAIGN',max_attempts=6),clock=lambda:125)
    assert f.calls==0 and not path.exists()

@pytest.mark.parametrize('field,value', [('package_digest','b'*64),('manifest_digest','b'*64),('model','wrong'),('evidence','/tmp/wrong'),('scope','FIRST_CELL_ONLY')])
def test_invalid_claims_block_fake_campaign_before_evidence(tmp_path,field,value):
    path=tmp_path/'evidence'; expected=claims(path); fake=launcher.FakeTransport([response()])
    with pytest.raises(launcher.GateError):
        launcher.fake_campaign(path,'FULL_CAMPAIGN',fake,synthetic_claims=replace(expected,**{field:value}),synthetic_expected=expected,clock=lambda:125)
    assert fake.calls==0 and not path.exists()

def test_authorized_fake_scopes_and_six_cell_limit(tmp_path):
    full_path=tmp_path/'full'; full=claims(full_path); f=launcher.FakeTransport([response()]*7)
    rows=launcher.fake_campaign(full_path,'FULL_CAMPAIGN',f,synthetic_claims=full,synthetic_expected=full,clock=lambda:125)
    assert len(rows)==f.calls==6
    first_path=tmp_path/'first'; first=replace(claims(first_path),scope='FIRST_CELL_ONLY',max_attempts=1)
    f=launcher.FakeTransport([response()]*2)
    rows=launcher.fake_campaign(first_path,'FIRST_CELL_ONLY',f,max_attempts=1,synthetic_claims=first,synthetic_expected=first,clock=lambda:125)
    assert len(rows)==f.calls==1 and rows[0]['scenario_id']=='authorized' and rows[0]['arm']=='ON'

def test_requested_subwindow_also_expires(tmp_path):
    c=claims(tmp_path/'evidence')
    with pytest.raises(launcher.GateError,match='EXPIRED'):
        launcher.check_bindings(c,replace(c,end_utc=150),150)
