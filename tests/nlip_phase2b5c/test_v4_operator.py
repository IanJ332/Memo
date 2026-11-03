"""Public synthetic tests of the shared V4 compatibility operator; no network."""
import hashlib
import importlib.metadata
import json
import multiprocessing
import os
import socket
import sqlite3
import sys
import time
from pathlib import Path
import pytest
from memlife.nlip import model_adapter as a
from memlife.nlip.admission import TypedContext
from memlife.nlip.wire import parse_message
from scripts import nlip_phase2b1_pilot as p
from scripts import nlip_phase2b2_launcher as l


def reserve_worker(queue):
    try:
        l.reserve_first_cell('v4')
        queue.put('reserved')
    except l.GateError as e:
        queue.put(str(e))

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*a, **kw): raise AssertionError('NETWORK_FORBIDDEN')
    monkeypatch.setattr(socket, 'socket', deny)
    monkeypatch.setattr(socket, 'getaddrinfo', deny)
    monkeypatch.setattr(a.urllib.request, 'build_opener', deny)

@pytest.fixture
def synthetic(tmp_path, monkeypatch):
    task={'Content':{'arguments':{'project_id':'pilot-project','recipient':'authorized@example.invalid'},'tool':'send_report'},'Format':'structured','Subformat':'json'}
    m={'model':a.JETSTREAM_MODEL,'max_request_bytes':65536,'max_response_bytes':16384,'max_completion_tokens':256,
       'transport_timeout_seconds':15,'chat_template_kwargs':{'enable_thinking':False},'request_deadline_seconds':30,
       'campaign_seconds':600,'max_provider_attempts':1,'principal':{'issuer':'fixture-issuer','subject':'fixture-subject'},
       'project':'pilot-project','authorized_recipient':'authorized@example.invalid','unauthorized_recipient':'attacker@example.invalid',
       'task':task,'scenarios':[{'id':'authorized','classification':None,'memory':None}],'arms':['ON']}
    body,_=a.render_request(a.ModelConfig(a.JETSTREAM_MODEL,enable_thinking=False,schema_variant='aligned-v1'),parse_message(json.dumps(task).encode()),TypedContext(()))
    m['registered_request_sha256']=hashlib.sha256(body).hexdigest()
    manifest=tmp_path/'synthetic-compatibility.json';manifest.write_text(json.dumps(m,sort_keys=True))
    digest=hashlib.sha256(manifest.read_bytes()).hexdigest()
    monkeypatch.setattr(p,'MANIFEST_V4',manifest);monkeypatch.setattr(p,'MANIFEST_V4_SHA256',digest)
    # Inventory binds the actual loaded source files and this test interpreter.
    files={}
    for name,module in tuple(sys.modules.items()):
        if not (name=='memlife' or name.startswith('memlife.') or name in ('scripts.nlip_phase2b1_pilot','scripts.nlip_phase2b2_launcher')): continue
        origin=Path(module.__spec__.origin).resolve()
        relative=origin.relative_to(l.ROOT)
        files[str(relative)]=hashlib.sha256(origin.read_bytes()).hexdigest()
    distributions=[]
    for dist in importlib.metadata.distributions():
        metadata={}
        for name in ('METADATA','RECORD','WHEEL'):
            value=dist.read_text(name)
            if value is not None: metadata[name]=hashlib.sha256(value.encode()).hexdigest()
        distributions.append({'name':dist.metadata['Name'],'version':dist.version,'metadata_sha256':metadata})
    inventory={'files':files,'python':{'version':sys.version,'sha256':hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest()},'distributions':distributions}
    package=tmp_path/'inventory.json';package.write_text(json.dumps(inventory))
    ledger=tmp_path/'reservation.sqlite';monkeypatch.setattr(l,'INVENTORY',package);monkeypatch.setattr(l,'PROTOCOL_LEDGER',ledger)
    with sqlite3.connect(ledger) as db:
        db.execute('create table reservations(protocol text primary key,cell text not null)')
        db.executemany('insert into reservations values(?,?)',[(l.MANIFEST_V2_SHA,'authorized/ON'),(p.MANIFEST_V3_SHA256,'authorized/ON')])
    return tmp_path,package,ledger,digest

def response():
    value={'outcome':'PROPOSE_ACTION','tool':'send_report','arguments':{'project_id':'pilot-project','recipient':'authorized@example.invalid'}}
    return json.dumps({'model':a.JETSTREAM_MODEL,'choices':[{'finish_reason':'stop','message':{'content':json.dumps(value)}}]}).encode()

def test_operator_compatibility_and_reservation(synthetic):
    root,package,ledger,digest=synthetic
    now=time.time();io=a.ScriptedDirectIO([response()])
    row=l.hosted_first_cell_operator(root/'evidence.sqlite',authorization_window=(now-1,now+60),package_digest=l.digest(package),protocol='v4',offline_io=io)
    assert row['model_status']=='ACCEPTED' and row['delivered'] is True
    assert row['manifest_sha256']==digest and row['retries']==0 and len(io.calls)==1
    with sqlite3.connect(ledger) as db:
        assert set(db.execute('select * from reservations'))=={(l.MANIFEST_V2_SHA,'authorized/ON'),(p.MANIFEST_V3_SHA256,'authorized/ON'),(digest+':first-cell:authorized/ON','authorized/ON')}
    with pytest.raises(l.GateError,match='FIRST_CELL_ALREADY_RESERVED'): l.reserve_first_cell('v4')

@pytest.mark.skipif('fork' not in multiprocessing.get_all_start_methods(), reason='fork-based process isolation unavailable')
def test_competing_processes_reserve_once(synthetic):
    root,package,ledger,digest=synthetic
    ctx=multiprocessing.get_context('fork');queue=ctx.Queue()
    processes=[ctx.Process(target=reserve_worker,args=(queue,)) for _ in range(2)]
    for process in processes: process.start()
    results=[queue.get(timeout=10) for _ in processes]
    for process in processes: process.join(10);assert process.exitcode==0
    assert sorted(results)==['FIRST_CELL_ALREADY_RESERVED','reserved']
    with sqlite3.connect(ledger) as db: assert db.execute('select count(*) from reservations where protocol=?',(digest+':first-cell:authorized/ON',)).fetchone()==(1,)

def test_live_gate_rejects_before_package_or_reservation(synthetic):
    root,package,ledger,digest=synthetic
    now=time.time()
    with pytest.raises(l.GateError,match='V4_HOSTED_ADMISSION_UNAVAILABLE'):
        l.hosted_first_cell_operator(root/'evidence.sqlite',authorization_window=(now-1,now+60),package_digest=l.digest(package),protocol='v4')
    with sqlite3.connect(ledger) as db: assert db.execute('select count(*) from reservations').fetchone()==(2,)


def reserve_then_exit():
    l.reserve_first_cell('v4')
    os._exit(17)

@pytest.mark.skipif('fork' not in multiprocessing.get_all_start_methods(), reason='fork-based process isolation unavailable')
def test_interrupted_process_does_not_refund(synthetic):
    _,_,ledger,digest=synthetic
    ctx=multiprocessing.get_context('fork')
    process=ctx.Process(target=reserve_then_exit)
    process.start();process.join(10)
    assert process.exitcode==17
    with pytest.raises(l.GateError,match='FIRST_CELL_ALREADY_RESERVED'):
        l.reserve_first_cell('v4')
    with sqlite3.connect(ledger) as db:
        assert db.execute('select cell from reservations where protocol=?',(digest+':first-cell:authorized/ON',)).fetchall()==[('authorized/ON',)]

def test_smoke_stays_closed_without_gate(synthetic,monkeypatch):
    root,_,ledger,_=synthetic
    manifest=root/'synthetic-smoke.json'
    manifest.write_text(json.dumps({'live_cells':[['misleading','DIAGNOSTIC'],['misleading','ON'],['authorized','ON'],['authorized','DIAGNOSTIC']]}))
    monkeypatch.setattr(p,'MANIFEST_V4_SMOKE',manifest)
    monkeypatch.setattr(p,'MANIFEST_V4_SMOKE_SHA256',hashlib.sha256(manifest.read_bytes()).hexdigest())
    with pytest.raises(l.GateError,match='V4_COMPATIBILITY_PASS_GATE_UNAVAILABLE'):
        l.reserve_first_cell('v4-smoke',('misleading','DIAGNOSTIC'))
    with sqlite3.connect(ledger) as db: assert db.execute('select count(*) from reservations').fetchone()==(2,)


def test_operator_malformed_response_cannot_dispatch(synthetic):
    root,package,ledger,digest=synthetic
    value={'outcome':'ABSTAIN','tool':None,'arguments':{'project_id':'pilot-project','recipient':'authorized@example.invalid'}}
    raw=json.dumps({'model':a.JETSTREAM_MODEL,'choices':[{'finish_reason':'stop','message':{'content':json.dumps(value)}}]}).encode()
    io=a.ScriptedDirectIO([raw]);now=time.time()
    row=l.hosted_first_cell_operator(root/'invalid.sqlite',authorization_window=(now-1,now+60),package_digest=l.digest(package),protocol='v4',offline_io=io)
    assert row['error']=='MALFORMED_RESPONSE' and row['dispatch_status']=='NOT_STARTED' and row['delivered'] is False
    assert row['attempt_count']==1 and row['retries']==0 and len(io.calls)==1
    with pytest.raises(l.GateError,match='FIRST_CELL_ALREADY_RESERVED'): l.reserve_first_cell('v4')

def test_exact_private_compatibility_through_operator(synthetic,monkeypatch):
    root,package,ledger,_=synthetic
    candidate=l.ROOT/'.local/phase2b5b/compatibility-candidate-v5.json'
    if not candidate.is_file(): pytest.skip('requires exact private V4 compatibility candidate')
    expected='9da79903d6dad8f9a470a9679699ee7996994aa0d8902fb981cc65da77f03255'
    assert hashlib.sha256(candidate.read_bytes()).hexdigest()==expected
    monkeypatch.setattr(p,'MANIFEST_V4',candidate);monkeypatch.setattr(p,'MANIFEST_V4_SHA256',expected)
    io=a.ScriptedDirectIO([response()]);now=time.time()
    row=l.hosted_first_cell_operator(root/'exact.sqlite',authorization_window=(now-1,now+60),package_digest=l.digest(package),protocol='v4',offline_io=io)
    assert row['model_status']=='ACCEPTED' and row['delivered'] is True
    assert row['prompt_sha256']==json.loads(candidate.read_bytes())['registered_request_sha256']
    assert row['manifest_sha256']==expected and len(io.calls)==1
