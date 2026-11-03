import hashlib
import json
import multiprocessing
import os
import sqlite3
import sys
import time
from pathlib import Path

import pytest
from scripts import nlip_phase2b2_launcher as launcher


def response():
    action = {'outcome': 'PROPOSE_ACTION', 'tool': 'send_report', 'arguments':
              {'project_id': 'pilot-project', 'recipient': 'authorized@example.invalid'}}
    return json.dumps({'model': launcher.MODEL, 'choices': [{'finish_reason': 'stop',
        'message': {'content': json.dumps(action)}}]}).encode()


def invoke(root, index, queue):
    launcher.PROTOCOL_LEDGER = Path(root) / 'ledger.sqlite'
    try:
        row = launcher.first_cell_operator(Path(root) / f'{index}.sqlite', [response()],
            authorization_window=(time.time()-10, time.time()+60), package_digest=launcher.digest(launcher.INVENTORY), protocol='v1')
        queue.put(('ok', row['delivered']))
    except Exception as exc:
        queue.put(('error', str(exc)))


def test_operator_and_process_race(tmp_path):
    ctx = multiprocessing.get_context('fork')
    queue = ctx.Queue()
    processes = [ctx.Process(target=invoke, args=(str(tmp_path), i, queue)) for i in range(2)]
    for process in processes: process.start()
    for process in processes: process.join(20)
    assert all(p.exitcode == 0 for p in processes)
    results = [queue.get(timeout=2) for _ in processes]
    assert sorted(results) == [('error', 'FIRST_CELL_ALREADY_RESERVED'), ('ok', True)]
    with sqlite3.connect(tmp_path / 'ledger.sqlite') as db:
        assert db.execute('select count(*) from reservations').fetchone() == (1,)


def test_operator_reservation_survives_interruption(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, 'PROTOCOL_LEDGER', tmp_path / 'ledger.sqlite')
    class Interrupted:
        def __init__(self, *args, **kwargs): raise KeyboardInterrupt()
    import scripts.nlip_phase2b1_pilot as pilot
    monkeypatch.setattr(pilot, 'Pilot', Interrupted)
    window = (time.time()-1, time.time()+10)
    package = launcher.digest(launcher.INVENTORY)
    with pytest.raises(KeyboardInterrupt):
        launcher.first_cell_operator(tmp_path/'first', [response()], authorization_window=window, package_digest=package, protocol='v1')
    with pytest.raises(launcher.GateError, match='FIRST_CELL_ALREADY_RESERVED'):
        launcher.first_cell_operator(tmp_path/'second', [response()], authorization_window=window, package_digest=package, protocol='v1')


def test_loaded_origin_and_bytes_rejected_before_transport(tmp_path, monkeypatch):
    import memlife.nlip.model_adapter as module
    monkeypatch.setattr(launcher, 'PROTOCOL_LEDGER', tmp_path / 'ledger.sqlite')
    monkeypatch.setattr(module.__spec__, 'origin', str(tmp_path/'shadow.py'))
    monkeypatch.setattr(launcher, 'FakeTransport', lambda *args: pytest.fail('constructed transport'))
    with pytest.raises(launcher.GateError, match='MODULE_ORIGIN_OR_BYTES_MISMATCH'):
        launcher.first_cell_operator(tmp_path/'evidence', [response()], authorization_window=(0, 9999999999),
                                     package_digest=launcher.digest(launcher.INVENTORY), protocol='v1')
    assert not (tmp_path/'ledger.sqlite').exists()


def test_loaded_source_byte_mismatch(monkeypatch):
    import memlife.nlip.model_adapter
    inventory = json.loads(launcher.INVENTORY.read_bytes())
    inventory['files']['src/memlife/nlip/model_adapter.py'] = '0' * 64
    with pytest.raises(launcher.GateError, match='MODULE_ORIGIN_OR_BYTES_MISMATCH'):
        launcher.verify_loaded_sources(inventory)


def interruptible(root, ready):
    launcher.PROTOCOL_LEDGER = Path(root) / 'ledger.sqlite'
    import scripts.nlip_phase2b1_pilot as pilot
    class Blocked:
        def __init__(self, *args, **kwargs):
            ready.set()
            time.sleep(30)
    pilot.Pilot = Blocked
    launcher.first_cell_operator(Path(root)/'interrupted', [response()],
        authorization_window=(time.time()-1, time.time()+60), package_digest=launcher.digest(launcher.INVENTORY), protocol='v1')


def test_terminated_process_consumes_reservation(tmp_path):
    ctx = multiprocessing.get_context('fork')
    ready = ctx.Event()
    process = ctx.Process(target=interruptible, args=(str(tmp_path), ready))
    process.start()
    try:
        assert ready.wait(10)
    finally:
        process.terminate()
        process.join(10)
    queue = ctx.Queue()
    second = ctx.Process(target=invoke, args=(str(tmp_path), 2, queue))
    second.start(); second.join(15)
    assert second.exitcode == 0
    assert queue.get(timeout=2) == ('error', 'FIRST_CELL_ALREADY_RESERVED')


def test_expiry_while_waiting_for_reservation_lock(tmp_path, monkeypatch):
    import threading
    monkeypatch.setattr(launcher, 'PROTOCOL_LEDGER', tmp_path/'ledger.sqlite')
    with sqlite3.connect(launcher.PROTOCOL_LEDGER) as db:
        db.execute('create table reservations (protocol text primary key, cell text not null)')
    ready = threading.Event()
    def hold():
        with sqlite3.connect(launcher.PROTOCOL_LEDGER) as db:
            db.execute('begin immediate'); ready.set(); time.sleep(.3)
    thread = threading.Thread(target=hold); thread.start(); assert ready.wait(2)
    monkeypatch.setattr(launcher, 'FakeTransport', lambda *args: pytest.fail('transport constructed'))
    now = time.time()
    with pytest.raises(launcher.GateError, match='AUTHORIZATION_EXPIRED'):
        launcher.first_cell_operator(tmp_path/'evidence', [response()], authorization_window=(now-1, now+.1),
                                     package_digest=launcher.digest(launcher.INVENTORY), protocol='v1')
    thread.join()
    with sqlite3.connect(launcher.PROTOCOL_LEDGER) as db:
        assert db.execute('select count(*) from reservations').fetchone() == (1,)


def test_synthetic_secret_not_in_output_or_evidence(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(launcher, 'PROTOCOL_LEDGER', tmp_path/'ledger.sqlite')
    monkeypatch.setenv('SYNTHETIC_API_KEY', 'synthetic-secret-r3-91d4')
    launcher.first_cell_operator(tmp_path/'evidence', [response()],
        authorization_window=(time.time()-1, time.time()+10), package_digest=launcher.digest(launcher.INVENTORY), protocol='v1')
    assert 'synthetic-secret-r3-91d4' not in capsys.readouterr().out
    for file in tmp_path.rglob('*'):
        if file.is_file(): assert b'synthetic-secret-r3-91d4' not in file.read_bytes()
