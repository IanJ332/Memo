"""Deterministic tests for Phase 08D-3's disabled-by-default primitives."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

from memlife.adapters.hindsight import HindsightHTTPError, HindsightMemoryAdapter, UrllibHindsightTransport
from memlife.models.memory import QueryCommand, WriteCommand
from memlife.runner.phase08d3 import (
    AccountingRejected,
    AttemptArtifactStore,
    CaptureFailure,
    HttpExchangeCapture,
    SendAccounting,
    assess_operation_coverage,
    attempt_outcome,
    capture_candidates,
    freeze_attempt_manifest,
    verify_inventory,
)
from tests.fakes.hindsight import FakeHindsightTransport


class _Response:
    status = 200
    headers = {"X-Request-ID": "r-1"}

    def __init__(self, data: bytes) -> None:
        self.data = data

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.data


def test_http_capture_preserves_exact_unicode_whitespace_and_escapes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store = AttemptArtifactStore(tmp_path / "attempt")
    capture = HttpExchangeCapture(store, attempt_id="attempt-1")
    body = b'{"text":"\\u00e9  \\n"}'
    monkeypatch.setattr("memlife.adapters.hindsight.urlopen", lambda *args, **kwargs: _Response(body))
    value = UrllibHindsightTransport("http://example.test", capture=capture).request("POST", "/x", payload={"text": "é  \n"})
    assert value == {"text": "é  \n"}
    response = (tmp_path / "attempt" / "http" / "exchange-000001.response.bin").read_bytes()
    request = (tmp_path / "attempt" / "http" / "exchange-000001.request.bin").read_bytes()
    assert response == body
    assert request == json.dumps({"text": "é  \n"}).encode("utf-8")
    assert (tmp_path / "attempt" / "http" / "exchange-000001.json").exists()


def test_http_error_body_is_captured_before_error_decode(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    error = HTTPError("http://example.test/x", 400, "bad", {"X-Request-ID": "bad-1"}, io.BytesIO(b'{"detail":"bad \\u00e9"}'))
    monkeypatch.setattr("memlife.adapters.hindsight.urlopen", lambda *args, **kwargs: (_ for _ in ()).throw(error))
    capture = HttpExchangeCapture(AttemptArtifactStore(tmp_path / "attempt"), attempt_id="attempt-1")
    with pytest.raises(HindsightHTTPError, match="bad é"):
        UrllibHindsightTransport("http://example.test", capture=capture).request("GET", "/x")
    assert (tmp_path / "attempt" / "http" / "exchange-000001.response.bin").read_bytes() == b'{"detail":"bad \\u00e9"}'


def test_capture_failure_fails_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    capture = HttpExchangeCapture(AttemptArtifactStore(tmp_path / "attempt"), attempt_id="attempt-1")
    monkeypatch.setattr(capture.store, "write_bytes", lambda *args, **kwargs: (_ for _ in ()).throw(CaptureFailure("disk full")))
    monkeypatch.setattr("memlife.adapters.hindsight.urlopen", lambda *args, **kwargs: _Response(b"{}"))
    with pytest.raises(CaptureFailure, match="disk full"):
        UrllibHindsightTransport("http://example.test", capture=capture).request("GET", "/x")


def test_candidate_capture_preserves_positions_filters_and_original_decoded_bytes() -> None:
    evidence = capture_candidates([
        {"id": "one", "text": "  \u00e9  ", "fact_type": "world", "source_memory_ids": ["s1"]},
        {"id": "two", "text": "   "},
        {"id": "three", "text": "kept only if room"},
        "malformed",
    ], selected_ids={"one"}, limit=1)
    assert [item.position for item in evidence] == [1, 2, 3, 4]
    assert evidence[0].decoded_field_bytes == "  é  ".encode()
    assert evidence[0].normalized_bytes == "é".encode()
    assert evidence[1].discard_reason == "blank_after_existing_strip"
    assert evidence[2].discard_reason == "filtered_or_truncated"
    assert evidence[3].discard_reason == "non_object"


def test_query_capture_is_optional_and_does_not_change_existing_results() -> None:
    transport = FakeHindsightTransport()
    adapter = HindsightMemoryAdapter(transport)
    adapter.write(WriteCommand(namespace="n", content="first"))
    adapter.write(WriteCommand(namespace="n", content="second"))
    assert [record.content for record in adapter.query(QueryCommand(namespace="n", limit=1))] == ["first"]
    assert adapter._candidate_evidence_sink is None


def test_query_capture_records_discarded_results_without_changing_order() -> None:
    transport = FakeHindsightTransport()
    captured = []
    adapter = HindsightMemoryAdapter(transport, candidate_evidence_sink=captured.append)
    adapter.write(WriteCommand(namespace="n", content="first"))
    adapter.write(WriteCommand(namespace="n", content="second"))
    result = adapter.query(QueryCommand(namespace="n", limit=1))
    assert [record.content for record in result] == ["first"]
    assert len(captured) == 1
    assert [item.position for item in captured[0]] == [1, 2]
    assert captured[0][0].included is True
    assert captured[0][1].discard_reason == "filtered_or_truncated"


def test_operation_coverage_requires_explicit_terminal_pagination() -> None:
    assert assess_operation_coverage((( {"id": "old", "status": "completed"},), ({"id": "new", "status": "cancelled"},))) == "COMPLETE"
    assert assess_operation_coverage((( {"id": "new", "status": "processing"},),)) == "UNKNOWN"
    assert assess_operation_coverage(()) == "UNKNOWN"


def test_adapter_operation_pagination_cancellation_and_unknown_coverage() -> None:
    class OperationsTransport:
        def request(self, method: str, path: str, *, query=None, payload=None):
            if path.endswith("/operations"):
                offset = int(query["offset"])
                rows = [
                    {"id": "old", "status": "completed"},
                    {"id": "cancelled", "status": "cancelled"},
                ]
                return {"operations": rows[offset:offset + 1], "total": 2}
            if path.endswith("/operations/cancelled"):
                return {"id": "cancelled", "status": "cancelled"}
            raise AssertionError(path)

    adapter = HindsightMemoryAdapter(OperationsTransport(), quiescence_timeout_seconds=1, poll_interval_seconds=0.001)
    assert [item["id"] for item in adapter._list_operations("n")] == ["old", "cancelled"]
    with pytest.raises(Exception, match="ended as cancelled"):
        adapter._wait_for_operation("n", "cancelled")
    adapter.wait_for_quiescence("n", known_operation_ids={"old", "cancelled"})
    assert adapter.benchmark_metadata()["operation_coverage"] == "UNKNOWN"


def test_concurrent_reservations_and_missing_usage_are_accounted() -> None:
    accounting = SendAccounting(5)
    first = accounting.admit(endpoint="e", model="m", maximum_units=3)
    with pytest.raises(AccountingRejected, match="exhaust"):
        accounting.admit(endpoint="e", model="m", maximum_units=3)
    accounting.receipt(first, actual_units=None, outcome="failed")
    assert accounting.records[-1]["state"] == "USAGE_MISSING"
    second = accounting.admit(endpoint="e", model="m", maximum_units=5)
    accounting.receipt(second, actual_units=4, outcome="success")


def test_uninstrumented_bound_and_evidence_corruption_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(AccountingRejected, match="bound"):
        SendAccounting(1).admit(endpoint="e", model="m", maximum_units=None)
    store = AttemptArtifactStore(tmp_path / "attempt")
    identity = store.write_bytes("raw.bin", b"immutable")
    assert identity.sha256 == hashlib.sha256(b"immutable").hexdigest()
    with pytest.raises(CaptureFailure):
        store.write_bytes("raw.bin", b"replacement")
    manifest = freeze_attempt_manifest(
        store, attempt_id="attempt-1", source_authority_sha256="a" * 64,
        configuration_sha256="b" * 64, resource_gate=True,
    )
    assert verify_inventory(store, (identity, manifest))
    (tmp_path / "attempt" / "raw.bin").write_bytes(b"corrupted")
    assert not verify_inventory(store, (identity, manifest))
    assert attempt_outcome(evidence_integrity=False, resource_gate=True) == "FAILED"
    assert attempt_outcome(evidence_integrity=True, resource_gate=True, prior_outcome="INCOMPLETE") == "INCOMPLETE"
