import json
import sqlite3
import concurrent.futures
import threading
import time
from types import SimpleNamespace

import pytest

from scripts import nlip_phase2b2_launcher as launcher
from scripts.nlip_phase2b1_pilot import Pilot


def response():
    action = {'outcome': 'PROPOSE_ACTION', 'tool': 'send_report', 'arguments':
              {'project_id': 'pilot-project', 'recipient': 'authorized@example.invalid'}}
    return json.dumps({'model': launcher.MODEL, 'choices': [{'finish_reason': 'stop',
        'message': {'content': json.dumps(action)}}]}).encode()


def test_fake_operator_reservation_survives_evidence_change(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, 'PROTOCOL_LEDGER', tmp_path / 'ledger.sqlite')
    window = (time.time() - 1, time.time() + 10)
    first = launcher.FakeTransport([response()])
    row = launcher.fake_first_cell_operator(tmp_path / 'one.sqlite', first, authorization_window=window)
    assert first.calls == 1 and row['delivered'] is True
    second = launcher.FakeTransport([response()])
    with pytest.raises(launcher.GateError, match='FIRST_CELL_ALREADY_RESERVED'):
        launcher.fake_first_cell_operator(tmp_path / 'two.sqlite', second, authorization_window=window)
    assert second.calls == 0 and not (tmp_path / 'two.sqlite').exists()
    with sqlite3.connect(tmp_path / 'ledger.sqlite') as db:
        assert db.execute('SELECT protocol, cell FROM reservations').fetchall() == [(launcher.MANIFEST_SHA, 'authorized/ON')]


def test_concurrent_fake_operators_reserve_only_once(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, 'PROTOCOL_LEDGER', tmp_path / 'ledger.sqlite')
    window = (time.time() - 1, time.time() + 10)
    transports = [launcher.FakeTransport([response()]) for _ in range(2)]
    def invoke(i):
        try:
            return launcher.fake_first_cell_operator(tmp_path / f'{i}.sqlite', transports[i], authorization_window=window)
        except launcher.GateError as error:
            return str(error)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(invoke, range(2)))
    assert sum(isinstance(x, dict) for x in results) == 1
    assert 'FIRST_CELL_ALREADY_RESERVED' in results
    assert sum(t.calls for t in transports) == 1


def test_reservation_is_not_refunded_after_malformed_output(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, 'PROTOCOL_LEDGER', tmp_path / 'ledger.sqlite')
    window = (time.time() - 1, time.time() + 10)
    row = launcher.fake_first_cell_operator(tmp_path / 'first.sqlite', launcher.FakeTransport([b'{}']), authorization_window=window)
    assert row['delivered'] is False
    with pytest.raises(launcher.GateError, match='FIRST_CELL_ALREADY_RESERVED'):
        launcher.fake_first_cell_operator(tmp_path / 'second.sqlite', launcher.FakeTransport([response()]), authorization_window=window)


def test_utc_expiry_before_dispatch_rejects_transaction(tmp_path):
    end = time.time() + .1
    pilot = Pilot(tmp_path / 'evidence', launcher.FakeTransport([response()]), authorization_window=(end - 1, end), protocol='v1')
    original = pilot._save
    def delay(row):
        original(row)
        if row['state'] == 'DISPATCH_IN_PROGRESS': time.sleep(.15)
    pilot._save = delay
    row = pilot.run('authorized', 'ON')
    assert row['utc_window_status'] == 'EXPIRED_BEFORE_ADMISSION'
    assert row['commit_status'] == 'NOT_COMMITTED' and row['delivered'] is False


def test_utc_expiry_before_model_response_rejects_dispatch(tmp_path):
    end = time.time() + .1
    class SlowFake:
        def send(self, *args): time.sleep(.15); return response()
    pilot = Pilot(tmp_path / 'evidence', SlowFake(), authorization_window=(end - 1, end), protocol='v1')
    row = pilot.run('authorized', 'ON')
    assert row['utc_window_status'] == 'EXPIRED_BEFORE_ADMISSION'
    assert row['delivered'] is False and row['commit_status'] == 'NOT_COMMITTED'


def test_utc_expiry_waiting_for_session_lock(tmp_path):
    end = time.time() + .2
    pilot = Pilot(tmp_path / 'evidence', launcher.FakeTransport([response()]), authorization_window=(end - 1, end), protocol='v1')
    original = pilot._fixture
    def fixture(scenario):
        values = original(scenario)
        held = threading.Event()
        def hold():
            with values[2]._lock:
                held.set()
                time.sleep(.3)
        threading.Thread(target=hold, daemon=True).start()
        assert held.wait(1)
        return values
    pilot._fixture = fixture
    row = pilot.run('authorized', 'ON')
    assert row['utc_window_status'] == 'EXPIRED_BEFORE_ADMISSION'
    assert row['delivered'] is False and row['utc_admission'] is None


def test_revoked_session_prevents_utc_admission(tmp_path):
    end = time.time() + 10
    pilot = Pilot(tmp_path / 'evidence', launcher.FakeTransport([response()]), authorization_window=(end - 20, end), protocol='v1')
    original = pilot._fixture
    def fixture(scenario):
        values = original(scenario)
        values[2].logout(values[3].sid)
        return values
    pilot._fixture = fixture
    row = pilot.run('authorized', 'ON')
    assert row['delivered'] is False and row['utc_admission'] is None
    assert row['dispatch_status'] == 'REJECTED_AT_BOUNDARY'


def test_utc_late_commit_preserves_delivery(tmp_path, monkeypatch):
    from scripts import nlip_phase2b1_pilot as pilot_module
    now = time.time()
    end = now + 10
    wall = [now]
    monkeypatch.setattr(pilot_module, 'time', SimpleNamespace(time=lambda: wall[0], monotonic=time.monotonic))
    pilot = Pilot(tmp_path / 'evidence', launcher.FakeTransport([response()]), authorization_window=(now - 1, end), protocol='v1')
    original = pilot._fixture
    def fixture(scenario):
        values = original(scenario)
        policy = values[4]
        connection = policy._connection
        class DelayedCommit:
            def __init__(self, db): self.db = db
            def __getattr__(self, name): return getattr(self.db, name)
            def commit(self): self.db.commit(); wall[0] = end
        policy._connection = lambda write=False: DelayedCommit(connection(write)) if write else connection(write)
        return values
    pilot._fixture = fixture
    row = pilot.run('authorized', 'ON')
    assert row['utc_admission'] < end <= row['utc_commit_return']
    assert row['utc_window_status'] == 'COMMIT_RETURNED_AFTER_WINDOW'
    assert row['commit_status'] == 'COMMITTED' and row['delivered'] is True
    assert row['deadline_status'] == 'COMMIT_RETURNED_WITHIN_DEADLINE'
