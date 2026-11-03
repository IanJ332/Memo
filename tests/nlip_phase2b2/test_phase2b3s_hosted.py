"""Actual prospective entrypoint with scripted I/O; sockets are prohibited."""
import json
import multiprocessing
import os
import socket
import time
from pathlib import Path
import pytest
from scripts import nlip_phase2b2_launcher as l
from memlife.nlip import model_adapter as a


def response():
    value={'outcome':'PROPOSE_ACTION','tool':'send_report','arguments':{'project_id':'pilot-project','recipient':'authorized@example.invalid'}}
    return json.dumps({'model':l.DEFAULT_MODEL,'choices':[{'finish_reason':'stop','message':{'content':json.dumps(value)}}]}).encode()

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args,**kwargs): raise AssertionError('NETWORK_PROHIBITED')
    monkeypatch.setattr(socket,'socket',denied)
    monkeypatch.setattr(socket,'getaddrinfo',denied)
    monkeypatch.setattr(a.urllib.request,'build_opener',denied)

def invoke(root,io,name='evidence'):
    l.PROTOCOL_LEDGER=Path(root)/'ledger'
    now=time.time()
    return l.hosted_first_cell_operator(Path(root)/name,authorization_window=(now-10,now+60),package_digest=l.digest(l.INVENTORY),offline_io=io)

def test_actual_direct_chain(tmp_path):
    io=a.ScriptedDirectIO([response(),response()]); row=invoke(tmp_path,io)
    assert row['delivered'] and row['manifest_sha256']==l.MANIFEST_V2_SHA
    assert len(io.calls)==1 and io.calls[0][0]==a.JETSTREAM_ENDPOINT
    assert not any(k.lower()=='authorization' for k in io.calls[0][1])
    assert json.loads(io.calls[0][2])['model']==l.DEFAULT_MODEL
    with pytest.raises(l.GateError,match='ALREADY_RESERVED'): invoke(tmp_path,io,'other')

def test_closed_gate_before_reservation(tmp_path):
    with pytest.raises(l.GateError,match='HOSTED_ADMISSION_UNAVAILABLE'): invoke(tmp_path,None)
    assert not (tmp_path/'ledger').exists()

def test_arbitrary_io_rejected(tmp_path):
    with pytest.raises(l.GateError,match='INVALID_OFFLINE_IO'): invoke(tmp_path,object())
    assert not (tmp_path/'ledger').exists()

def worker(root,queue):
    try: queue.put(('ok',invoke(root,a.ScriptedDirectIO([response()]),str(os.getpid()))['delivered']))
    except l.GateError as e: queue.put(('error',str(e)))

def test_direct_process_competition(tmp_path):
    ctx=multiprocessing.get_context('fork'); q=ctx.Queue()
    ps=[ctx.Process(target=worker,args=(str(tmp_path),q)) for _ in range(2)]
    for p in ps: p.start()
    for p in ps: p.join(20)
    assert all(p.exitcode==0 for p in ps)
    assert sorted(q.get(timeout=2) for _ in ps)==[('error','FIRST_CELL_ALREADY_RESERVED'),('ok',True)]

def test_cli_closed(tmp_path):
    assert l.main(['--mode','FIRST_CELL_ONLY','--package-digest',l.digest(l.INVENTORY),'--evidence',str(tmp_path/'evidence')])==1
    assert not (tmp_path/'evidence').exists()
