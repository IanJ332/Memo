import json
import runpy
import sqlite3
import threading
import time
from pathlib import Path

import pytest

from scripts.nlip_phase2b1_pilot import Pilot, PilotError

class Fake:
    def __init__(self, wait=None): self.wait=wait
    def send(self,*args):
        if self.wait: self.wait.wait()
        proposal={'outcome':'PROPOSE_ACTION','tool':'send_report','arguments':{'project_id':'pilot-project','recipient':'authorized@example.invalid'}}
        return json.dumps({'model':json.loads(args[0])['model'],'choices':[{'finish_reason':'stop','message':{'content':json.dumps(proposal)}}]}).encode()

class CommitProxy:
    def __init__(self, db, mode): self.db,self.mode=db,mode
    def __getattr__(self,key): return getattr(self.db,key)
    def commit(self):
        if self.mode=='delay': time.sleep(.15); return self.db.commit()
        self.db.commit(); raise RuntimeError('post-commit failure')

def configured(tmp_path, mode=None, seconds=.08):
    p=Pilot(tmp_path/'evidence.sqlite',Fake(),request_seconds=seconds, protocol='v1');original=p._fixture
    def fixture(s):
        values=original(s);policy=values[4];connection=policy._connection
        if mode: policy._connection=lambda write=False: CommitProxy(connection(write),mode) if write else connection(write)
        return values
    p._fixture=fixture
    return p

def test_original_delayed_commit_fixture_is_preserved(capsys, monkeypatch):
    # The immutable historical reproducer predates response-model validation.
    # Adapt only its synthetic envelope, preserving its original bytes and assertions.
    import memlife.nlip.model_adapter as adapter
    original = adapter._bounded_send
    def adapt(transport, body, timeout, max_bytes, deadline):
        raw = original(transport, body, timeout, max_bytes, deadline)
        parsed = json.loads(raw)
        parsed['model'] = json.loads(body)['model']
        return json.dumps(parsed).encode()
    monkeypatch.setattr(adapter, '_bounded_send', adapt)
    script=Path(__file__).with_name('reproduce_commit_deadline.py')
    runpy.run_path(str(script),run_name='__main__')
    output=json.loads(capsys.readouterr().out)
    assert output['delivered'] is True and output['dispatcher_decision']=='ALLOW'
    assert output['error']=='DEADLINE_EXPIRED' and output['task_outcome']=='AUTHORIZED_SUCCESS'

def test_delayed_commit_is_authoritatively_recorded(tmp_path):
    p=configured(tmp_path,'delay'); row=p.run('authorized','ON')
    assert row['model_status']=='ACCEPTED' and row['proposal_validity']=='VALID'
    assert row['dispatcher_decision']=='ALLOW' and row['delivered'] is True
    assert row['commit_status']=='COMMITTED' and row['deadline_status']=='COMMIT_RETURNED_AFTER_DEADLINE'
    assert row['dispatch_status']=='COMPLETED' and row['task_outcome']=='AUTHORIZED_SUCCESS'
    assert row['dispatch_entry_offset_ms'] < 80 and row['commit_return_offset_ms'] >= 80
    assert p.observations()==[row]
    policy=tmp_path/row['policy_evidence']; assert policy.exists()
    with sqlite3.connect(policy) as db:
        assert db.execute('select action,delivered from audit').fetchall()==[('ALLOW',1)]
        assert db.execute('select count(*) from deliveries').fetchone()[0]==1
    with pytest.raises(PilotError,match='CAMPAIGN_STOPPED'):p.run('authorized','OFF')

def test_error_after_commit_cannot_hide_delivery(tmp_path):
    p=configured(tmp_path,'raise_after_commit'); row=p.run('authorized','ON')
    assert row['dispatcher_decision']=='ALLOW' and row['delivered'] is True
    assert row['commit_status']=='COMMITTED' and row['deadline_status']=='COMMIT_TIME_UNKNOWN'
    assert row['task_outcome']=='AUTHORIZED_SUCCESS' and row['error']=='COMMIT_TIME_UNKNOWN'
    with pytest.raises(PilotError,match='CAMPAIGN_STOPPED'):p.run('authorized','OFF')

def test_unreadable_commit_evidence_is_uncertain_and_stops(tmp_path):
    p=configured(tmp_path); original=p._fixture
    def fixture(s):
        v=original(s)
        def unavailable(): raise sqlite3.OperationalError('sensitive')
        v[4].audits=unavailable
        return v
    p._fixture=fixture
    row=p.run('authorized','ON')
    assert row['commit_status']=='UNKNOWN' and row['delivered'] is None and row['task_outcome']=='OUTCOME_UNCERTAIN'
    assert p.observations()==[row] and b'sensitive' not in p.path.read_bytes()
    with pytest.raises(PilotError,match='CAMPAIGN_STOPPED'):p.run('authorized','OFF')

def test_expiration_before_entry_prevents_dispatch(tmp_path):
    p=configured(tmp_path,seconds=.05); original=p._save
    def slow_save(row):
        original(row)
        if row['state']=='DISPATCH_IN_PROGRESS':time.sleep(.08)
    p._save=slow_save; row=p.run('authorized','ON')
    assert row['model_status']=='ACCEPTED' and row['dispatch_status']=='REJECTED_EXPIRED'
    assert row['commit_status']=='NOT_ATTEMPTED' and row['delivered'] is False
    with sqlite3.connect(tmp_path/row['policy_evidence']) as db:
        assert db.execute('select count(*) from audit').fetchone()[0]==0

def test_timeout_late_response_cannot_enter_dispatch(tmp_path):
    event=threading.Event();p=Pilot(tmp_path/'evidence.sqlite',Fake(event),request_seconds=.05, protocol='v1')
    row=p.run('authorized','ON');event.set();time.sleep(.06)
    assert row['model_status']=='TIMEOUT' and row['dispatch_status']=='NOT_STARTED'
    assert row['commit_status']=='NOT_ATTEMPTED' and row['delivered'] is False
    assert p.observations()==[row]

def test_interrupted_dispatch_is_durably_uncertain_and_cannot_retry(tmp_path):
    p=configured(tmp_path);original=p._fixture
    def fixture(s):
        v=original(s)
        def crash(*args):raise RuntimeError('simulated interruption')
        v[5].dispatch=crash
        return v
    p._fixture=fixture
    with pytest.raises(RuntimeError,match='simulated interruption'):p.run('authorized','ON')
    row=p.observations()[0]
    assert row['state']=='DISPATCH_IN_PROGRESS' and row['commit_status']=='UNKNOWN' and row['delivered'] is None
    assert (tmp_path/row['policy_evidence']).exists()
    with pytest.raises(PilotError,match='CAMPAIGN_STOPPED'):p.run('authorized','OFF')

def test_expiration_between_admission_check_and_dispatch_boundary(tmp_path):
    p=configured(tmp_path,seconds=.06);original=p._fixture
    def fixture(s):
        v=original(s);dispatch=v[5].dispatch
        def delayed(*args):
            time.sleep(.10)
            return dispatch(*args)
        v[5].dispatch=delayed
        return v
    p._fixture=fixture;row=p.run('authorized','ON')
    assert row['dispatch_status']=='REJECTED_AT_BOUNDARY' and row['dispatch_entry_offset_ms'] is None
    assert row['commit_status']=='NOT_COMMITTED' and row['delivered'] is False
    with sqlite3.connect(tmp_path/row['policy_evidence']) as db:
        assert db.execute('select count(*) from deliveries').fetchone()[0]==0
