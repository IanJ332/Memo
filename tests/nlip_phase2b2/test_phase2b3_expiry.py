"""Offline pre-send UTC admission regression through the first-cell operator."""
import time

from scripts import nlip_phase2b2_launcher as launcher
from scripts.nlip_phase2b1_pilot import Pilot


def test_expiry_during_fixture_setup_never_enters_transport(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, 'PROTOCOL_LEDGER', tmp_path / 'ledger.sqlite')
    original = Pilot._fixture
    calls = []

    def fixture_then_expire(self, scenario):
        result = original(self, scenario)
        self.authorization_window = (0, 1)
        return result

    def unexpected_send(self, body, timeout, max_bytes):
        calls.append(True)
        raise AssertionError('transport entered after expiry')

    monkeypatch.setattr(Pilot, '_fixture', fixture_then_expire)
    monkeypatch.setattr(launcher.FakeTransport, 'send', unexpected_send)
    now = time.time()
    row = launcher.first_cell_operator(tmp_path / 'evidence', [b'{}'],
        authorization_window=(now - 1, now + 60), package_digest=launcher.digest(launcher.INVENTORY))
    assert row['error'] == 'AUTHORIZATION_EXPIRED'
    assert row['dispatch_status'] == 'NOT_STARTED'
    assert calls == []
    assert row['provider_may_have_received'] is True  # conservative durable pre-send marker
