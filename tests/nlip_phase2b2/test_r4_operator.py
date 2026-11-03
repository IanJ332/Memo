"""Fake-only qualification through first_cell_operator; no network or credentials."""
import json
import os
import sqlite3
import stat
import threading
import time
from types import SimpleNamespace

import pytest
from scripts import nlip_phase2b2_launcher as launcher
from scripts import nlip_phase2b1_pilot as pilot

SECRET = 'synthetic-secret-r4-49c2'


def response(model=launcher.MODEL):
    action = {'outcome': 'PROPOSE_ACTION', 'tool': 'send_report', 'arguments':
              {'project_id': 'pilot-project', 'recipient': 'authorized@example.invalid'}}
    return json.dumps({'model': model, 'choices': [{'finish_reason': 'stop',
        'message': {'content': json.dumps(action)}}]}).encode()


@pytest.fixture
def run_operator(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, 'PROTOCOL_LEDGER', tmp_path / 'reservation.sqlite')
    def run(payload=None, window=None, name='evidence.sqlite'):
        return launcher.first_cell_operator(tmp_path / name, [response() if payload is None else payload],
            authorization_window=window or (time.time()-10, time.time()+60),
            package_digest=launcher.digest(launcher.INVENTORY), protocol='v1')
    return run


def assert_no_secret(root, captured, *, approved_private_response=None):
    assert SECRET not in captured.out and SECRET not in captured.err
    if approved_private_response is not None:
        path,expected=approved_private_response
        assert path.name=='response.body' and not path.is_symlink()
        assert path.resolve().is_relative_to(root.resolve())
        assert path.stat().st_uid==os.geteuid() and stat.S_IMODE(path.stat().st_mode)==0o600
        assert stat.S_IMODE(path.parent.stat().st_mode)==0o700
        assert path.read_bytes()==expected
    for path in root.rglob('*'):
        if path.is_file() and SECRET.encode() in path.read_bytes():
            assert approved_private_response is not None and path==approved_private_response[0],path


def test_window_not_started(run_operator, tmp_path):
    now = time.time()
    with pytest.raises(launcher.GateError, match='AUTHORIZATION_EXPIRED'):
        run_operator(window=(now+10, now+20))
    assert not (tmp_path/'reservation.sqlite').exists()


def test_end_exactly_at_accepted_response(run_operator, monkeypatch):
    # Change only the Pilot wall clock at the worker's completed response boundary.
    wall = [100.0]
    monkeypatch.setattr(pilot, 'time', SimpleNamespace(time=lambda: wall[0], monotonic=time.monotonic))
    original = launcher.FakeTransport.send
    def send(self, *args):
        value = original(self, *args); wall[0] = 200.0; return value
    monkeypatch.setattr(launcher.FakeTransport, 'send', send)
    now = time.time()
    # The operator checks its real clock, the protected boundary uses the controlled clock.
    # Both clocks' window is aligned to the actual instant below.
    wall[0] = now
    end = now + 10
    def exact_send(self, *args):
        value = original(self, *args); wall[0] = end; return value
    monkeypatch.setattr(launcher.FakeTransport, 'send', exact_send)
    row = run_operator(window=(now-10, end))
    assert row['model_status'] == 'ACCEPTED'
    assert row['utc_admission'] is None and row['utc_window_status'] == 'EXPIRED_BEFORE_ADMISSION'
    assert row['commit_status'] == 'NOT_COMMITTED' and row['delivered'] is False


def test_expiry_after_acceptance_before_session_entry(run_operator, monkeypatch):
    now = time.time(); end = now + 10; wall = [now]
    monkeypatch.setattr(pilot, 'time', SimpleNamespace(time=lambda: wall[0], monotonic=time.monotonic))
    original = pilot.Pilot._save
    def save(self, row):
        original(self, row)
        if row['state'] == 'DISPATCH_IN_PROGRESS': wall[0] = end
    monkeypatch.setattr(pilot.Pilot, '_save', save)
    row = run_operator(window=(now-10, end))
    assert row['model_status'] == 'ACCEPTED' and row['utc_admission'] is None
    assert row['utc_window_status'] == 'EXPIRED_BEFORE_ADMISSION'
    assert row['delivered'] is False and row['commit_status'] == 'NOT_COMMITTED'


def test_expiry_waiting_session_lock(run_operator, monkeypatch):
    now = time.time(); end = now + 10; wall = [now]; held = threading.Event()
    monkeypatch.setattr(pilot, 'time', SimpleNamespace(time=lambda: wall[0], monotonic=time.monotonic))
    original = pilot.Pilot._fixture
    def fixture(self, scenario):
        values = original(self, scenario)
        def hold():
            with values[2]._lock:
                held.set(); time.sleep(.08); wall[0] = end
        thread = threading.Thread(target=hold); thread.start(); assert held.wait(2)
        return values
    monkeypatch.setattr(pilot.Pilot, '_fixture', fixture)
    row = run_operator(window=(now-10, end))
    assert row['model_status'] == 'ACCEPTED' and row['utc_admission'] is None
    assert row['utc_window_status'] == 'EXPIRED_BEFORE_ADMISSION' and row['delivered'] is False


def test_entry_before_expiry_late_commit(run_operator, monkeypatch):
    now = time.time(); end = now+10; wall = [now]
    monkeypatch.setattr(pilot, 'time', SimpleNamespace(time=lambda: wall[0], monotonic=time.monotonic))
    original = pilot.Pilot._fixture
    def fixture(self, scenario):
        values = original(self, scenario); policy = values[4]; connection = policy._connection
        class LateCommit:
            def __init__(self, db): self.db = db
            def __getattr__(self, key): return getattr(self.db, key)
            def commit(self): self.db.commit(); wall[0] = end
        policy._connection = lambda write=False: LateCommit(connection(write)) if write else connection(write)
        return values
    monkeypatch.setattr(pilot.Pilot, '_fixture', fixture)
    row = run_operator(window=(now-10, end))
    assert row['model_status'] == 'ACCEPTED' and row['utc_admission'] < end <= row['utc_commit_return']
    assert row['utc_window_status'] == 'COMMIT_RETURNED_AFTER_WINDOW'
    assert row['commit_status'] == 'COMMITTED' and row['delivered'] is True
    assert row['deadline_status'] == 'COMMIT_RETURNED_WITHIN_DEADLINE'


def test_monotonic_deadline_and_late_response(run_operator, monkeypatch, tmp_path):
    original_init = pilot.Pilot.__init__
    def init(self, *args, **kwargs): return original_init(self, *args, request_seconds=.08, **kwargs)
    monkeypatch.setattr(pilot.Pilot, '__init__', init)
    release = threading.Event(); returned = threading.Event()
    original_send = launcher.FakeTransport.send
    def slow(self, *args):
        release.wait(2)
        try: return original_send(self, *args)
        finally: returned.set()
    monkeypatch.setattr(launcher.FakeTransport, 'send', slow)
    row = run_operator()
    release.set(); assert returned.wait(2); time.sleep(.05)
    assert row['model_status'] == 'TIMEOUT' and row['deadline_status'] == 'RESPONSE_NOT_ACCEPTED'
    assert row['dispatch_status'] == 'NOT_STARTED' and row['commit_status'] == 'NOT_ATTEMPTED'
    assert row['delivered'] is False and row['utc_admission'] is None
    with sqlite3.connect(tmp_path/'evidence.sqlite') as db:
        assert json.loads(db.execute('select observation from attempts').fetchone()[0]) == row
    with pytest.raises(launcher.GateError, match='FIRST_CELL_ALREADY_RESERVED'):
        run_operator(name='second.sqlite')


def test_revoked_session(run_operator, monkeypatch):
    original = pilot.Pilot._fixture
    def fixture(self, scenario):
        values = original(self, scenario); values[2].logout(values[3].sid); return values
    monkeypatch.setattr(pilot.Pilot, '_fixture', fixture)
    row = run_operator()
    assert row['model_status'] == 'ACCEPTED' and row['dispatch_status'] == 'REJECTED_AT_BOUNDARY'
    assert row['utc_admission'] is None and row['delivered'] is False


def test_unknown_commit_outcome(run_operator, monkeypatch):
    original = pilot.Pilot._fixture
    def fixture(self, scenario):
        values = original(self, scenario)
        def unavailable(): raise sqlite3.OperationalError(SECRET)
        values[4].audits = unavailable
        return values
    monkeypatch.setattr(pilot.Pilot, '_fixture', fixture)
    row = run_operator()
    assert row['model_status'] == 'ACCEPTED' and row['utc_admission'] is not None
    assert row['commit_status'] == 'UNKNOWN' and row['delivered'] is None
    assert row['deadline_status'] == 'UNKNOWN' and row['task_outcome'] == 'OUTCOME_UNCERTAIN'
    with pytest.raises(launcher.GateError, match='FIRST_CELL_ALREADY_RESERVED'):
        run_operator(name='second.sqlite')


def test_model_mismatch_no_dispatch(run_operator):
    row = run_operator(response('wrong-model'))
    assert row['error'] == 'MODEL_IDENTITY_MISMATCH' and row['dispatch_status'] == 'NOT_STARTED'
    assert row['delivered'] is False


@pytest.mark.parametrize('case', ['success', 'provider_error', 'malformed'])
def test_secret_filtering(run_operator, tmp_path, monkeypatch, capsys, case):
    monkeypatch.setenv('SYNTHETIC_SECRET', SECRET)
    if case == 'provider_error':
        def send(*args): raise RuntimeError(SECRET)
        monkeypatch.setattr(launcher.FakeTransport, 'send', send)
    payload = (json.dumps({'model': launcher.MODEL, 'choices': [], 'error': SECRET}).encode()
               if case == 'malformed' else response())
    row = run_operator(payload)
    if case == 'success': assert row['delivered'] is True
    else:
        assert row['dispatch_status'] == 'NOT_STARTED' and row['delivered'] is False
        if case == 'malformed': assert row['error'] == 'MALFORMED_RESPONSE'
        with pytest.raises(launcher.GateError, match='FIRST_CELL_ALREADY_RESERVED'):
            run_operator(name='second.sqlite')
    assert SECRET not in json.dumps(row)
    approved=(tmp_path/row['response_evidence'],payload) if case=='malformed' else None
    assert_no_secret(tmp_path, capsys.readouterr(),approved_private_response=approved)


@pytest.mark.parametrize('case', ['shadow_import', 'outside_origin', 'wrong_in_tree_origin', 'modified_source'])
def test_real_subprocess_import_rejected_before_capabilities(tmp_path, case):
    import os
    import subprocess
    import sys
    # The child performs genuine imports. The modified-source case adds a temporary
    # first-party probe and synthetic inventory entry; no existing source is edited.
    script = r'''
import importlib, importlib.util, json, hashlib, sys, uuid
from pathlib import Path
from scripts import nlip_phase2b2_launcher as l
import scripts.nlip_phase2b1_pilot
import memlife.nlip as package
root = Path(sys.argv[1]); case = sys.argv[2]
l.PROTOCOL_LEDGER = root/'ledger'
marker = root/'transport-or-credential'
def prohibited(*a, **k):
    marker.write_text('capability invoked')
    raise AssertionError('unexpected capability')
l.FakeTransport = prohibited
probe = None
try:
    if case == 'shadow_import':
        shadow = root/'shadow'; shadow.mkdir()
        (shadow/'model_adapter.py').write_text('MARKER = "real shadow import"\n')
        package.__path__.insert(0, str(shadow))
        sys.modules.pop('memlife.nlip.model_adapter', None)
        module = importlib.import_module('memlife.nlip.model_adapter')
        assert Path(module.__spec__.origin) == shadow/'model_adapter.py'
    elif case in ('outside_origin', 'wrong_in_tree_origin'):
        name = 'memlife.nlip.model_adapter'
        source = root/'outside.py' if case == 'outside_origin' else l.ROOT/'src/memlife/nlip/auth.py'
        if case == 'outside_origin': source.write_text('MARKER = "outside import"\n')
        spec = importlib.util.spec_from_file_location(name, source)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        sys.modules[name] = module
        assert Path(module.__spec__.origin).resolve() == source.resolve()
    else:
        stem = '_r4_temporary_probe_' + uuid.uuid4().hex
        probe = l.ROOT/'src/memlife/nlip'/ (stem + '.py')
        with probe.open('x') as out: out.write('MARKER = "original"\n')
        name = 'memlife.nlip.' + stem
        module = importlib.import_module(name)
        assert module.MARKER == 'original'
        inv = json.loads(l.INVENTORY.read_bytes())
        inv['files']['src/memlife/nlip/' + stem + '.py'] = l.digest(probe)
        synthetic = root/'inventory.json'
        synthetic.write_text(json.dumps(inv, sort_keys=True))
        l.INVENTORY = synthetic
        original_verify = l.verify_package
        def verify_then_modify(digest):
            accepted = original_verify(digest)
            probe.write_text('MARKER = "modified after package verification"\n')
            return accepted
        l.verify_package = verify_then_modify
    try:
        l.first_cell_operator(root/'evidence', [b'{}'], authorization_window=(0, 9999999999),
                              package_digest=l.digest(l.INVENTORY), protocol='v1')
    except l.GateError as exc:
        assert str(exc) in ('MODULE_ORIGIN_OR_BYTES_MISMATCH', 'MODULE_IMPORT_ROOT_MISMATCH'), str(exc)
    else:
        raise AssertionError('unexpected acceptance')
    assert not marker.exists() and not l.PROTOCOL_LEDGER.exists()
    print('REJECTED ' + case)
finally:
    if probe is not None: probe.unlink(missing_ok=True)
'''
    env = {'PYTHONPATH': str(launcher.ROOT/'src') + os.pathsep + str(launcher.ROOT),
           'PYTHONDONTWRITEBYTECODE': '1'}
    result = subprocess.run([sys.executable, '-c', script, str(tmp_path), case], cwd=launcher.ROOT,
                            env=env, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == 'REJECTED ' + case


@pytest.mark.parametrize('failure', ['transport_construction', 'evidence_write'])
def test_injected_exception_is_sanitized(run_operator, monkeypatch, tmp_path, capsys, failure):
    if failure == 'transport_construction':
        def fail(*args): raise RuntimeError(SECRET)
        monkeypatch.setattr(launcher, 'FakeTransport', fail)
    else:
        def fail(*args): raise sqlite3.OperationalError(SECRET)
        monkeypatch.setattr(pilot.Pilot, '_save', fail)
    with pytest.raises(launcher.GateError) as error:
        run_operator()
    assert str(error.value) == 'OPERATOR_FAILED' and error.value.__suppress_context__
    with pytest.raises(launcher.GateError, match='FIRST_CELL_ALREADY_RESERVED'):
        run_operator(name='second.sqlite')
    assert_no_secret(tmp_path, capsys.readouterr())


def test_sqlite_busy_timeout_does_not_duplicate(run_operator, tmp_path):
    db = sqlite3.connect(tmp_path/'reservation.sqlite')
    db.execute('create table reservations (protocol text primary key, cell text not null)')
    db.execute('begin immediate')
    try:
        with pytest.raises(sqlite3.OperationalError, match='locked'):
            run_operator()
    finally:
        db.rollback(); db.close()
    row = run_operator(name='after-lock.sqlite')
    assert row['delivered'] is True
    with pytest.raises(launcher.GateError, match='FIRST_CELL_ALREADY_RESERVED'):
        run_operator(name='duplicate.sqlite')
    with sqlite3.connect(tmp_path/'reservation.sqlite') as db:
        assert db.execute('select count(*) from reservations').fetchone() == (1,)
