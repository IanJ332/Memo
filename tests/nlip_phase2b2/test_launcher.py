import json
import os
import socket
import sqlite3
import pytest
from scripts import nlip_phase2b2_launcher as launcher


def response(model=launcher.MODEL, value=None):
    value = value or {'outcome':'PROPOSE_ACTION','tool':'send_report','arguments':{'project_id':'pilot-project','recipient':'authorized@example.invalid'}}
    return json.dumps({'model':model, 'choices':[{'finish_reason':'stop','message':{'content':json.dumps(value)}}]}).encode()

@pytest.fixture
def private(tmp_path):
    os.chmod(tmp_path, 0o700)
    return tmp_path

def test_fake_first_cell_and_durable_evidence(private):
    f=launcher.FakeTransport([response(), response()])
    path=private/'evidence.sqlite'
    rows=launcher.fake_campaign(path,'FIRST_CELL_ONLY',f)
    assert len(rows)==f.calls==1 and rows[0]['arm']=='ON' and rows[0]['scenario_id']=='authorized'
    with sqlite3.connect(path) as db: assert db.execute('select count(*) from attempts').fetchone()[0]==1
    assert (private/rows[0]['policy_evidence']).is_file()
    assert path.stat().st_mode & 0o777 == 0o600

def test_full_fake_and_budget(private):
    f=launcher.FakeTransport([response()]*6)
    assert len(launcher.fake_campaign(private/'a.sqlite','FULL_CAMPAIGN',f,max_attempts=2))==2
    assert f.calls==2

def test_failures_do_not_retry_or_continue(private):
    for n, payload in enumerate((b'invalid',response('wrong-model'),response(value={'outcome':'ABSTAIN','tool':None,'arguments':None}))):
        f=launcher.FakeTransport([payload,response()])
        assert len(launcher.fake_campaign(private/f'{n}.sqlite','FULL_CAMPAIGN',f))==1
        assert f.calls==1

def test_fake_transport_cannot_be_replaced(private):
    with pytest.raises(launcher.GateError): launcher.fake_campaign(private/'a','FULL_CAMPAIGN',object())
    with pytest.raises(launcher.GateError): launcher.fake_campaign(private/'a','OTHER',launcher.FakeTransport([]))
    with pytest.raises(launcher.GateError): launcher.fake_campaign(private/'a','FULL_CAMPAIGN',launcher.FakeTransport([]),max_attempts=7)

def test_existing_destination_and_permissions(private):
    (private/'a').touch()
    with pytest.raises(launcher.GateError,match='DESTINATION_EXISTS'): launcher.validate_destination(private/'a')
    os.chmod(private,0o755)
    with pytest.raises(launcher.GateError,match='DESTINATION_PERMISSIONS'): launcher.validate_destination(private/'b')

def test_dry_run_and_live_hard_block(private, monkeypatch, capsys):
    monkeypatch.setattr(socket.socket,'connect',lambda *a,**k: pytest.fail('network'))
    # Any credential access through the environment is prohibited.
    monkeypatch.setattr(os, 'getenv', lambda *a, **k: pytest.fail('credential access'))
    digest=launcher.digest(launcher.INVENTORY)
    args=['--package-digest',digest,'--evidence',str(private/'a')]
    assert launcher.main(args)==0 and not (private/'a').exists()
    for mode in ('FIRST_CELL_ONLY','FULL_CAMPAIGN'):
        assert launcher.main(args+['--mode',mode])==1
    assert launcher.main(args+['--model','wrong'])==1
    assert launcher.main(['--package-digest','0'*64,'--evidence',str(private/'a')])==1
    assert 'credential' not in capsys.readouterr().err

def test_concurrent_exclusive_creation(private):
    import threading
    barrier=threading.Barrier(2); result=[]
    def run():
        barrier.wait()
        try: launcher.fake_campaign(private/'race.sqlite','FIRST_CELL_ONLY',launcher.FakeTransport([response()])); result.append('ok')
        except (OSError, launcher.GateError): result.append('blocked')
    a=threading.Thread(target=run); b=threading.Thread(target=run)
    a.start();b.start();a.join();b.join()
    assert sorted(result)==['blocked','ok']

def test_subsequent_denial_does_not_stop_fake_campaign(private):
    denied = {'outcome':'PROPOSE_ACTION','tool':'send_report','arguments':{'project_id':'pilot-project','recipient':'attacker@example.invalid'}}
    f=launcher.FakeTransport([response(),response(),response(),response(value=denied),response(),response()])
    rows=launcher.fake_campaign(private/'deny.sqlite','FULL_CAMPAIGN',f)
    assert len(rows)==6 and rows[3]['dispatcher_decision']=='DENY' and not rows[3]['delivered']
