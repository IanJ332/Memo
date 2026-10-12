"""Focused deterministic offline tests for Phase 08D-4 D2 candidate persistence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from memlife.adapters.hindsight import HindsightMemoryAdapter, UrllibHindsightTransport
from memlife.models.memory import QueryCommand, WriteCommand
from memlife.runner.phase08d3 import (
    AttemptArtifactStore,
    CandidateArtifactSink,
    CaptureFailure,
    HttpExchangeCapture,
    capture_candidates,
    verify_candidate_integrity,
)
from tests.fakes.hindsight import FakeHindsightTransport


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_d2_unicode_whitespace_and_json_escapes(tmp_path: Path) -> None:
    store = AttemptArtifactStore(tmp_path / "attempt")
    capture = HttpExchangeCapture(store, attempt_id="attempt-d2-1")
    sink = CandidateArtifactSink(store)

    raw_text = "  \u00e9clair \t\n \u4e16\u754c \U0001f600 \"quoted\" \r\n  "
    response_payload = {
        "results": [
            {
                "id": "item-unicode",
                "text": raw_text,
                "fact_type": "world",
                "source_memory_ids": ["src-1"],
            }
        ]
    }
    response_bytes = json.dumps(response_payload, ensure_ascii=False).encode("utf-8")
    exchange = capture.capture(
        method="POST",
        path="/v1/default/banks/test/memories/recall",
        request_body=b'{"query":"*"}',
        response_body=response_bytes,
        status_code=200,
        request_id="req-unicode-1",
    )

    evidence = sink.capture_and_persist(
        results=response_payload["results"],
        selected_positions={1},
        limit=10,
        exchange_manifest=exchange,
    )

    assert len(evidence) == 1
    item = evidence[0]
    assert item.position == 1
    assert item.native_id == "item-unicode"
    assert item.included is True
    assert item.selection_reason == "selected"
    assert item.discard_reason is None
    assert item.surface == "world"
    assert item.parent_ids == ("src-1",)
    assert item.source_ids == ("src-1",)
    assert item.provenance_basis == "PROVIDER_NATIVE"
    assert item.delivery == "STORE_PERSISTED"
    assert item.durable_artifact_persisted is True

    # Exact byte parity
    expected_decoded = raw_text.encode("utf-8")
    expected_normalized = raw_text.strip().encode("utf-8")
    assert item.decoded_field_bytes == expected_decoded
    assert item.normalized_bytes == expected_normalized

    decoded_file = tmp_path / "attempt" / "candidates" / exchange["exchange_id"] / "candidate-0001.decoded.bin"
    normalized_file = tmp_path / "attempt" / "candidates" / exchange["exchange_id"] / "candidate-0001.normalized.bin"
    assert decoded_file.read_bytes() == expected_decoded
    assert normalized_file.read_bytes() == expected_normalized
    assert item.decoded_field_artifact.sha256 == _sha256(expected_decoded)
    assert item.normalized_artifact.sha256 == _sha256(expected_normalized)

    # Manifest verification
    assert verify_candidate_integrity(store, exchange["exchange_id"]) is True


def test_d2_duplicate_native_ids_and_truncation(tmp_path: Path) -> None:
    store = AttemptArtifactStore(tmp_path / "attempt")
    capture = HttpExchangeCapture(store, attempt_id="attempt-d2-2")
    sink = CandidateArtifactSink(store)

    response_payload = {
        "results": [
            {"id": "duplicate-id", "text": "first version", "fact_type": "world", "source_memory_ids": ["s1"]},
            {"id": "duplicate-id", "text": "second version", "fact_type": "experience", "source_memory_ids": ["s2"]},
            {"id": "third-id", "text": "third version", "fact_type": "observation", "source_memory_ids": ["s3"]},
        ]
    }
    response_bytes = json.dumps(response_payload).encode("utf-8")
    exchange = capture.capture(
        method="POST",
        path="/v1/default/banks/test/memories/recall",
        request_body=b"{}",
        response_body=response_bytes,
        status_code=200,
        request_id="req-dup-1",
    )

    # Only position 1 is selected; position 2 and 3 are truncated by limit=1
    evidence = sink.capture_and_persist(
        results=response_payload["results"],
        selected_positions={1},
        limit=1,
        exchange_manifest=exchange,
    )

    assert len(evidence) == 3
    assert [e.position for e in evidence] == [1, 2, 3]
    assert [e.native_id for e in evidence] == ["duplicate-id", "duplicate-id", "third-id"]
    assert [e.included for e in evidence] == [True, False, False]
    assert [e.selection_reason for e in evidence] == ["selected", None, None]
    assert [e.discard_reason for e in evidence] == [None, "filtered_or_truncated", "filtered_or_truncated"]

    # Distinct artifact paths preserved for duplicate IDs
    p1_path = evidence[0].decoded_field_artifact.path
    p2_path = evidence[1].decoded_field_artifact.path
    assert p1_path != p2_path
    assert (tmp_path / "attempt" / p1_path).read_bytes() == b"first version"
    assert (tmp_path / "attempt" / p2_path).read_bytes() == b"second version"

    manifest_data = json.loads((tmp_path / "attempt" / f"candidates/{exchange['exchange_id']}.json").read_text())
    assert manifest_data["total_candidates"] == 3
    assert manifest_data["selected_count"] == 1
    assert [c["position"] for c in manifest_data["candidates"]] == [1, 2, 3]
    assert [c["native_id"] for c in manifest_data["candidates"]] == ["duplicate-id", "duplicate-id", "third-id"]
    assert verify_candidate_integrity(store, exchange["exchange_id"]) is True


def test_d2_empty_and_malformed_responses(tmp_path: Path) -> None:
    store = AttemptArtifactStore(tmp_path / "attempt")
    capture = HttpExchangeCapture(store, attempt_id="attempt-d2-3")
    sink = CandidateArtifactSink(store)

    # 1. Complete empty retrieval: {"results": []}
    exchange_empty = capture.capture(
        method="POST", path="/recall", request_body=b"{}",
        response_body=b'{"results": []}', status_code=200, request_id="empty-1",
    )
    evidence_empty = sink.capture_and_persist(
        results=[],
        selected_positions=set(),
        limit=5,
        exchange_manifest=exchange_empty,
    )
    assert evidence_empty == ()
    manifest_empty = json.loads((tmp_path / "attempt" / f"candidates/{exchange_empty['exchange_id']}.json").read_text())
    assert manifest_empty["retrieval_disposition"] == "COMPLETE_EMPTY"
    assert manifest_empty["total_candidates"] == 0
    assert manifest_empty["selected_count"] == 0
    assert verify_candidate_integrity(store, exchange_empty["exchange_id"]) is True

    # 2. Filtered all items: results had entries, but none included
    exchange_filtered = capture.capture(
        method="POST", path="/recall", request_body=b"{}",
        response_body=b'{"results": [{"id": "x", "text": "   "}, "invalid"]}',
        status_code=200, request_id="filtered-1",
    )
    evidence_filtered = sink.capture_and_persist(
        results=[{"id": "x", "text": "   "}, "invalid"],
        selected_positions=set(),
        limit=5,
        exchange_manifest=exchange_filtered,
    )
    assert len(evidence_filtered) == 2
    assert [e.included for e in evidence_filtered] == [False, False]
    manifest_filtered = json.loads((tmp_path / "attempt" / f"candidates/{exchange_filtered['exchange_id']}.json").read_text())
    assert manifest_filtered["retrieval_disposition"] == "FILTERED_ALL"
    assert manifest_filtered["total_candidates"] == 2
    assert manifest_filtered["selected_count"] == 0
    assert verify_candidate_integrity(store, exchange_filtered["exchange_id"]) is True

    # 3. Malformed responses fail closed
    with pytest.raises(CaptureFailure, match="not a list"):
        sink.capture_and_persist(
            results="not-a-list",
            selected_positions=set(),
            limit=5,
            exchange_manifest=exchange_empty,
        )


def test_d2_candidate_to_response_correlation(tmp_path: Path) -> None:
    store = AttemptArtifactStore(tmp_path / "attempt")
    capture = HttpExchangeCapture(store, attempt_id="attempt-d2-4")
    sink = CandidateArtifactSink(store, extraction_rule="test-extractor-v1", extraction_version="test-version-1")

    resp_body = b'{"results":[{"id":"m1","text":"test value","fact_type":"world"}]}'
    exchange = capture.capture(
        method="POST", path="/memories/recall", request_body=b'{"query":"q"}',
        response_body=resp_body, status_code=200, request_id="corr-1",
    )

    sink.capture_and_persist(
        results=[{"id": "m1", "text": "test value", "fact_type": "world"}],
        selected_positions={1},
        limit=5,
        exchange_manifest=exchange,
    )

    manifest = json.loads((tmp_path / "attempt" / f"candidates/{exchange['exchange_id']}.json").read_text())
    assert manifest["http_exchange"]["exchange_id"] == exchange["exchange_id"]
    assert manifest["http_exchange"]["request_id"] == "corr-1"
    assert manifest["http_exchange"]["response"]["path"] == exchange["response"]["path"]
    assert manifest["http_exchange"]["response"]["sha256"] == exchange["response"]["sha256"]
    assert manifest["extraction"]["rule"] == "test-extractor-v1"
    assert manifest["extraction"]["version"] == "test-version-1"
    assert manifest["extraction"]["charset"] == "utf-8"

    cand = manifest["candidates"][0]
    transforms = cand["transformations"]
    assert len(transforms) == 2
    assert transforms[0]["rule"] == "json_pointer_to_utf8_decoded_field"
    assert transforms[0]["input_artifact_path"] == exchange["response"]["path"]
    assert transforms[0]["input_sha256"] == exchange["response"]["sha256"]
    assert transforms[0]["output_sha256"] == cand["decoded_field"]["sha256"]
    assert transforms[0]["lossless"] is True

    assert transforms[1]["rule"] == "utf8_decoded_field_to_strip_normalized"
    assert transforms[1]["input_sha256"] == cand["decoded_field"]["sha256"]
    assert transforms[1]["output_sha256"] == cand["normalized"]["sha256"]
    assert transforms[1]["lossless"] is False


def test_d2_exact_byte_integrity_and_deterministic_hashes(tmp_path: Path) -> None:
    """Negative regression test: candidate results must originate from persisted HTTP response.

    When the HTTP response is {"results": []} but nonempty candidates are passed,
    capture_and_persist must reject the inconsistent evidence, and verify_candidate_integrity
    must fail closed.
    """
    store = AttemptArtifactStore(tmp_path / "attempt")
    capture = HttpExchangeCapture(store, attempt_id="attempt-d2-5")
    sink = CandidateArtifactSink(store)

    text1 = "Alpha \n \t Beta"
    text2 = "Gamma \u221e Delta"
    exchange = capture.capture(
        method="POST", path="/recall", request_body=b"{}",
        response_body=b'{"results": []}', status_code=200, request_id="det-1",
    )

    with pytest.raises(CaptureFailure, match="candidate results do not match persisted HTTP response results"):
        sink.capture_and_persist(
            results=[
                {"id": "c1", "text": text1},
                {"id": "c2", "text": text2},
            ],
            selected_positions={1, 2},
            limit=2,
            exchange_manifest=exchange,
        )

    # Forged or inconsistent evidence must also be rejected by verify_candidate_integrity
    assert verify_candidate_integrity(store, exchange["exchange_id"]) is False


def test_d2_exact_byte_integrity_and_deterministic_hashes_positive(tmp_path: Path) -> None:
    store = AttemptArtifactStore(tmp_path / "attempt")
    capture = HttpExchangeCapture(store, attempt_id="attempt-d2-5-pos")
    sink = CandidateArtifactSink(store)

    text1 = "Alpha \n \t Beta"
    text2 = "Gamma \u221e Delta"
    resp_obj = {
        "results": [
            {"id": "c1", "text": text1, "fact_type": "world", "source_memory_ids": ["s1"]},
            {"id": "c2", "text": text2, "fact_type": "world", "source_memory_ids": ["s2"]},
        ]
    }
    resp_bytes = json.dumps(resp_obj, ensure_ascii=False).encode("utf-8")
    exchange = capture.capture(
        method="POST", path="/recall", request_body=b"{}",
        response_body=resp_bytes, status_code=200, request_id="det-pos-1",
    )

    evidence = sink.capture_and_persist(
        results=resp_obj["results"],
        selected_positions={1, 2},
        limit=2,
        exchange_manifest=exchange,
    )

    for item, raw in zip(evidence, [text1, text2]):
        decoded_path = tmp_path / "attempt" / item.decoded_field_artifact.path
        normalized_path = tmp_path / "attempt" / item.normalized_artifact.path
        assert decoded_path.read_bytes() == raw.encode("utf-8")
        assert normalized_path.read_bytes() == raw.strip().encode("utf-8")
        assert item.decoded_field_artifact.sha256 == hashlib.sha256(raw.encode("utf-8")).hexdigest()
        assert item.normalized_artifact.sha256 == hashlib.sha256(raw.strip().encode("utf-8")).hexdigest()

    assert verify_candidate_integrity(store, exchange["exchange_id"]) is True


def test_d2_missing_or_corrupt_artifacts_fail_closed(tmp_path: Path) -> None:
    store = AttemptArtifactStore(tmp_path / "attempt")
    capture = HttpExchangeCapture(store, attempt_id="attempt-d2-6")
    sink = CandidateArtifactSink(store)

    # 1. Missing exchange manifest fails closed
    with pytest.raises(CaptureFailure, match="missing D1 HTTP response exchange reference"):
        sink.capture_and_persist(results=[], selected_positions=set(), limit=1, exchange_manifest=None)

    # 2. Corrupted D1 HTTP response hash fails closed before candidate writing
    exchange = capture.capture(
        method="POST", path="/recall", request_body=b"{}",
        response_body=b'{"results":[{"id":"1","text":"ok"}]}', status_code=200, request_id="tamper-1",
    )
    # Mutate the response file on disk
    resp_on_disk = tmp_path / "attempt" / exchange["response"]["path"]
    resp_on_disk.write_bytes(b'{"results":[{"id":"1","text":"TAMPERED"}]}')

    with pytest.raises(CaptureFailure, match="hash mismatch"):
        sink.capture_and_persist(
            results=[{"id": "1", "text": "ok"}],
            selected_positions={1},
            limit=1,
            exchange_manifest=exchange,
        )

    # 3. Missing response file on disk fails closed
    resp_on_disk.unlink()
    with pytest.raises(CaptureFailure, match="artifact missing"):
        sink.capture_and_persist(
            results=[{"id": "1", "text": "ok"}],
            selected_positions={1},
            limit=1,
            exchange_manifest=exchange,
        )


def test_d2_write_failures_and_partial_capture_fail_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store = AttemptArtifactStore(tmp_path / "attempt")
    capture = HttpExchangeCapture(store, attempt_id="attempt-d2-7")
    sink = CandidateArtifactSink(store)

    exchange = capture.capture(
        method="POST", path="/recall", request_body=b"{}",
        response_body=b'{"results":[{"id":"1","text":"sample"}]}', status_code=200,
    )

    # Injected write failure during candidate byte writing
    real_write_bytes = store.write_bytes
    call_count = [0]

    def failing_write_bytes(relative_path: str, data: bytes):
        call_count[0] += 1
        if "candidate-0001.normalized.bin" in relative_path:
            raise CaptureFailure("simulated disk full")
        return real_write_bytes(relative_path, data)

    monkeypatch.setattr(store, "write_bytes", failing_write_bytes)

    with pytest.raises(CaptureFailure, match="simulated disk full"):
        sink.capture_and_persist(
            results=[{"id": "1", "text": "sample"}],
            selected_positions={1},
            limit=1,
            exchange_manifest=exchange,
        )

    # Integrity verification fails because the manifest was never committed
    assert verify_candidate_integrity(store, exchange["exchange_id"]) is False


def test_d2_disabled_instrumentation_backward_compatibility() -> None:
    transport = FakeHindsightTransport()
    adapter = HindsightMemoryAdapter(transport)

    # Baseline write and query without any instrumentation
    record1 = adapter.write(WriteCommand(namespace="uninstrumented", content="first"))
    record2 = adapter.write(WriteCommand(namespace="uninstrumented", content="second"))
    query_res = adapter.query(QueryCommand(namespace="uninstrumented", limit=2))

    assert len(query_res) == 2
    assert [r.content for r in query_res] == ["first", "second"]
    assert adapter._candidate_evidence_sink is None
    assert transport.capture is None
    assert transport.last_exchange is None


def test_d2_adapter_query_integration_with_fake_and_urllib_transports(tmp_path: Path) -> None:
    store = AttemptArtifactStore(tmp_path / "attempt")
    capture = HttpExchangeCapture(store, attempt_id="attempt-d2-8")
    sink = CandidateArtifactSink(store)

    # Test with FakeHindsightTransport instrumented with capture
    transport = FakeHindsightTransport(capture=capture)
    adapter = HindsightMemoryAdapter(transport, candidate_evidence_sink=sink)

    adapter.write(WriteCommand(namespace="test_bank", content="Alice Alder"))
    adapter.write(WriteCommand(namespace="test_bank", content="Bob Alder"))

    # Execute query with limit=1: Alice selected, Bob truncated
    result = adapter.query(QueryCommand(namespace="test_bank", limit=1))
    assert [r.content for r in result] == ["Alice Alder"]

    # Verify sink persisted candidates linked to recall exchange
    assert len(sink.persisted_manifests) == 1
    manifest = sink.persisted_manifests[0]
    exchange_id = manifest["exchange_id"]
    assert manifest["retrieval_disposition"] == "COMPLETE_NONEMPTY"
    assert manifest["total_candidates"] == 2
    assert manifest["selected_count"] == 1
    assert verify_candidate_integrity(store, exchange_id) is True

    # Test complete empty query on empty bank
    empty_transport = FakeHindsightTransport(capture=capture)
    empty_adapter = HindsightMemoryAdapter(empty_transport, candidate_evidence_sink=sink)
    empty_result = empty_adapter.query(QueryCommand(namespace="empty_bank", limit=1))
    assert empty_result == ()

    assert len(sink.persisted_manifests) == 2
    empty_manifest = sink.persisted_manifests[1]
    assert empty_manifest["retrieval_disposition"] == "COMPLETE_EMPTY"
    assert empty_manifest["total_candidates"] == 0
    assert verify_candidate_integrity(store, empty_manifest["exchange_id"]) is True


def test_d2_rejects_missing_or_malformed_results(tmp_path: Path) -> None:
    store = AttemptArtifactStore(tmp_path / "attempt")
    capture = HttpExchangeCapture(store, attempt_id="attempt-d2-missing")
    sink = CandidateArtifactSink(store)

    # 1. Missing "results" key in response JSON must NOT be classified as COMPLETE_EMPTY
    ex_missing = capture.capture(
        method="POST", path="/recall", request_body=b"{}",
        response_body=b'{"status": "ok"}', status_code=200, request_id="missing-res",
    )
    with pytest.raises(CaptureFailure, match="missing 'results' field"):
        sink.capture_and_persist(
            results=[],
            selected_positions=set(),
            limit=5,
            exchange_manifest=ex_missing,
        )

    # 2. "results" is not a list
    ex_nonlist = capture.capture(
        method="POST", path="/recall", request_body=b"{}",
        response_body=b'{"results": "not-a-list"}', status_code=200, request_id="nonlist-res",
    )
    with pytest.raises(CaptureFailure, match="'results' field is not a list"):
        sink.capture_and_persist(
            results=[],
            selected_positions=set(),
            limit=5,
            exchange_manifest=ex_nonlist,
        )

    # 3. "results" is null
    ex_null = capture.capture(
        method="POST", path="/recall", request_body=b"{}",
        response_body=b'{"results": null}', status_code=200, request_id="null-res",
    )
    with pytest.raises(CaptureFailure, match="'results' field is not a list"):
        sink.capture_and_persist(
            results=[],
            selected_positions=set(),
            limit=5,
            exchange_manifest=ex_null,
        )


def test_d2_evidence_completeness_and_json_field_paths(tmp_path: Path) -> None:
    store = AttemptArtifactStore(tmp_path / "attempt")
    capture = HttpExchangeCapture(store, attempt_id="attempt-d2-completeness")
    sink = CandidateArtifactSink(store)

    resp_obj = {
        "results": [
            {"id": "m1", "text": "   leading whitespace   ", "fact_type": "world", "source_memory_ids": ["s1"]},
            {"id": "m2", "text": "   ", "fact_type": "experience", "source_memory_ids": ["s2"]},
            {"id": "m3", "text": "valid item", "fact_type": "observation", "source_memory_ids": ["s3"]},
        ]
    }
    resp_bytes = json.dumps(resp_obj).encode("utf-8")
    exchange = capture.capture(
        method="POST", path="/recall", request_body=b"{}",
        response_body=resp_bytes, status_code=200, request_id="comp-1",
    )

    # Invalid selection position 0 rejected
    with pytest.raises(CaptureFailure, match="invalid selection position 0"):
        sink.capture_and_persist(
            results=resp_obj["results"],
            selected_positions={0},
            limit=1,
            exchange_manifest=exchange,
        )

    # Invalid selection position out of bounds (4 > 3) rejected
    with pytest.raises(CaptureFailure, match="invalid selection position 4"):
        sink.capture_and_persist(
            results=resp_obj["results"],
            selected_positions={4},
            limit=1,
            exchange_manifest=exchange,
        )

    # Position 2 is blank after strip; cannot be selected
    with pytest.raises(CaptureFailure, match="position 2 cannot be selected"):
        sink.capture_and_persist(
            results=resp_obj["results"],
            selected_positions={2},
            limit=1,
            exchange_manifest=exchange,
        )

    # Selected count exceeds limit
    with pytest.raises(CaptureFailure, match="selected candidate count exceeds command limit"):
        sink.capture_and_persist(
            results=resp_obj["results"],
            selected_positions={1, 3},
            limit=1,
            exchange_manifest=exchange,
        )

    # Valid selection: position 1 selected with limit 1
    evidence = sink.capture_and_persist(
        results=resp_obj["results"],
        selected_positions={1},
        limit=1,
        exchange_manifest=exchange,
    )
    assert len(evidence) == 3
    assert evidence[0].json_path == "/results/0"
    assert evidence[0].field_path == "/results/0/text"
    assert evidence[1].json_path == "/results/1"
    assert evidence[1].field_path == "/results/1/text"
    assert evidence[2].json_path == "/results/2"
    assert evidence[2].field_path == "/results/2/text"

    # Distinction between original response bytes and decoded UTF-8 field bytes
    raw_response_bytes = (tmp_path / "attempt" / exchange["response"]["path"]).read_bytes()
    decoded_field_bytes = (tmp_path / "attempt" / evidence[0].decoded_field_artifact.path).read_bytes()
    assert decoded_field_bytes == b"   leading whitespace   "
    assert raw_response_bytes != decoded_field_bytes
    assert b'"results"' in raw_response_bytes

    manifest = json.loads((tmp_path / "attempt" / f"candidates/{exchange['exchange_id']}.json").read_text())
    assert manifest["candidates"][0]["json_path"] == "/results/0"
    assert manifest["candidates"][0]["field_path"] == "/results/0/text"
    assert manifest["candidates"][0]["transformations"][0]["json_pointer"] == "/results/0/text"
    assert verify_candidate_integrity(store, exchange["exchange_id"]) is True


def test_d2_exchange_correlation_concurrent_and_failure_paths(tmp_path: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from memlife.adapters.hindsight import HindsightHTTPError

    store = AttemptArtifactStore(tmp_path / "attempt")
    capture = HttpExchangeCapture(store, attempt_id="attempt-d2-concurrency")
    sink = CandidateArtifactSink(store)

    transport = FakeHindsightTransport(capture=capture)
    adapter = HindsightMemoryAdapter(transport, candidate_evidence_sink=sink)

    # Seed data in distinct banks
    adapter.write(WriteCommand(namespace="bank_alpha", content="Alpha Item"))
    adapter.write(WriteCommand(namespace="bank_beta", content="Beta Item"))

    # Test concurrent queries across threads
    results_map: dict[str, list[str]] = {}
    errors: list[Exception] = []

    def run_query(ns: str) -> None:
        try:
            res = adapter.query(QueryCommand(namespace=ns, limit=5))
            results_map[ns] = [r.content for r in res]
        except Exception as exc:
            errors.append(exc)

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(run_query, "bank_alpha")
        f2 = executor.submit(run_query, "bank_beta")
        f1.result()
        f2.result()

    assert not errors
    assert results_map["bank_alpha"] == ["Alpha Item"]
    assert results_map["bank_beta"] == ["Beta Item"]

    # Verify each persisted manifest correctly correlates to its own bank and exchange
    assert len(sink.persisted_manifests) == 2
    for manifest in sink.persisted_manifests:
        assert verify_candidate_integrity(store, manifest["exchange_id"]) is True

    # Test failure path: transport error records failed exchange on thread-local
    with pytest.raises(HindsightHTTPError):
        transport.request("GET", "/v1/default/banks/test/memories/nonexistent-id")
    failed_exchange = transport.last_exchange
    assert failed_exchange is not None
    assert failed_exchange["status_code"] == 404

    # Subsequent query does not reuse stale error exchange
    pop_res = transport.pop_last_exchange()
    assert pop_res["status_code"] == 404
    assert transport.pop_last_exchange() is None


def test_d2_tampered_disposition_filtered_all_with_unchanged_bytes_fails_closed(tmp_path: Path) -> None:
    """Negative test: mutating a valid selected candidate into FILTERED_ALL while

    leaving candidate bytes unchanged on disk must be rejected by
    verify_candidate_integrity.
    """
    store = AttemptArtifactStore(tmp_path / "attempt")
    capture = HttpExchangeCapture(store, attempt_id="attempt-d2-tamper-disp")
    sink = CandidateArtifactSink(store)

    candidate_text = "Persisted authentic memory"
    resp_obj = {
        "results": [
            {
                "id": "cand-1",
                "text": candidate_text,
                "fact_type": "world",
                "source_memory_ids": ["src-1"],
            }
        ]
    }
    resp_bytes = json.dumps(resp_obj).encode("utf-8")
    exchange = capture.capture(
        method="POST",
        path="/v1/default/banks/test/memories/recall",
        request_body=b'{"query":"*"}',
        response_body=resp_bytes,
        status_code=200,
        request_id="req-tamper-disp-1",
    )

    evidence = sink.capture_and_persist(
        results=resp_obj["results"],
        selected_positions={1},
        limit=5,
        exchange_manifest=exchange,
    )
    assert len(evidence) == 1
    assert evidence[0].included is True

    exchange_id = exchange["exchange_id"]
    cand_manifest_path = tmp_path / "attempt" / f"candidates/{exchange_id}.json"
    decoded_bin_path = tmp_path / "attempt" / f"candidates/{exchange_id}/candidate-0001.decoded.bin"
    normalized_bin_path = tmp_path / "attempt" / f"candidates/{exchange_id}/candidate-0001.normalized.bin"

    # Bytes exist and are valid before tampering
    assert decoded_bin_path.read_bytes() == candidate_text.encode("utf-8")
    assert normalized_bin_path.read_bytes() == candidate_text.strip().encode("utf-8")
    assert verify_candidate_integrity(store, exchange_id) is True

    # Mutate candidate manifest on disk: change valid selected candidate to FILTERED_ALL
    manifest_data = json.loads(cand_manifest_path.read_text(encoding="utf-8"))
    manifest_data["retrieval_disposition"] = "FILTERED_ALL"
    manifest_data["selected_count"] = 0
    manifest_data["candidates"][0]["included"] = False
    manifest_data["candidates"][0]["selection_reason"] = None
    manifest_data["candidates"][0]["discard_reason"] = "filtered_or_truncated"

    # Overwrite candidate manifest with tampered disposition; candidate bytes remain unchanged
    cand_manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
    assert decoded_bin_path.read_bytes() == candidate_text.encode("utf-8")
    assert normalized_bin_path.read_bytes() == candidate_text.strip().encode("utf-8")

    # verify_candidate_integrity must recompute from response bytes and reject the tampered disposition
    assert verify_candidate_integrity(store, exchange_id) is False


def test_d2_linked_d1_exchange_manifest_verification_and_mismatch_fails_closed(tmp_path: Path) -> None:
    """Verify that linked D1 HTTP exchange manifest identity and fields are verified fail-closed:

    missing manifest file, SHA-256 mismatch, exchange_id mismatch, attempt_id mismatch,
    method mismatch, path mismatch, status_code mismatch, and response reference mismatch.
    """
    store = AttemptArtifactStore(tmp_path / "attempt")
    capture = HttpExchangeCapture(store, attempt_id="attempt-d2-d1-verify")
    sink = CandidateArtifactSink(store)

    resp_obj = {"results": [{"id": "m1", "text": "Sample memory"}]}
    resp_bytes = json.dumps(resp_obj).encode("utf-8")
    exchange = capture.capture(
        method="POST",
        path="/v1/default/banks/test/memories/recall",
        request_body=b'{"query":"*"}',
        response_body=resp_bytes,
        status_code=200,
        request_id="req-d1-v-1",
    )

    sink.capture_and_persist(
        results=resp_obj["results"],
        selected_positions={1},
        limit=5,
        exchange_manifest=exchange,
    )
    exchange_id = exchange["exchange_id"]
    d1_manifest_path = tmp_path / "attempt" / f"http/{exchange_id}.json"
    cand_manifest_path = tmp_path / "attempt" / f"candidates/{exchange_id}.json"

    # Baseline is valid
    assert verify_candidate_integrity(store, exchange_id) is True

    # 1. Missing D1 exchange manifest file
    d1_orig_bytes = d1_manifest_path.read_bytes()
    d1_manifest_path.unlink()
    assert verify_candidate_integrity(store, exchange_id) is False

    # 2. Corrupted D1 exchange manifest SHA-256
    d1_manifest_path.write_bytes(d1_orig_bytes + b" ")
    assert verify_candidate_integrity(store, exchange_id) is False

    # Helper to re-save d1_manifest with custom fields and update candidate manifest's d1 SHA
    def set_d1_fields_and_update_sha(mutations: dict[str, Any]) -> None:
        data = json.loads(d1_orig_bytes.decode("utf-8"))
        data.update(mutations)
        new_bytes = json.dumps(data, indent=2).encode("utf-8")
        d1_manifest_path.write_bytes(new_bytes)
        c_data = json.loads(cand_manifest_path.read_text(encoding="utf-8"))
        c_data["http_exchange"]["manifest"]["sha256"] = hashlib.sha256(new_bytes).hexdigest()
        c_data["http_exchange"]["manifest"]["byte_count"] = len(new_bytes)
        cand_manifest_path.write_text(json.dumps(c_data, indent=2), encoding="utf-8")

    # 3. Exchange ID mismatch
    set_d1_fields_and_update_sha({"exchange_id": "exchange-mismatch"})
    assert verify_candidate_integrity(store, exchange_id) is False

    # 4. Attempt ID mismatch
    set_d1_fields_and_update_sha({"attempt_id": "attempt-mismatch"})
    assert verify_candidate_integrity(store, exchange_id) is False

    # 5. Method mismatch
    set_d1_fields_and_update_sha({"method": "GET"})
    assert verify_candidate_integrity(store, exchange_id) is False

    # 6. Path mismatch
    set_d1_fields_and_update_sha({"path": "/v1/other/path"})
    assert verify_candidate_integrity(store, exchange_id) is False

    # 7. Status code mismatch
    set_d1_fields_and_update_sha({"status_code": 500})
    assert verify_candidate_integrity(store, exchange_id) is False

    # 8. Response artifact mismatch in D1 manifest
    set_d1_fields_and_update_sha({
        "response": {
            "path": f"http/{exchange_id}.response.bin",
            "sha256": "0" * 64,
            "byte_count": 999,
        }
    })
    assert verify_candidate_integrity(store, exchange_id) is False

    # Restore original D1 manifest
    d1_manifest_path.write_bytes(d1_orig_bytes)
    c_data = json.loads(cand_manifest_path.read_text(encoding="utf-8"))
    c_data["http_exchange"]["manifest"]["sha256"] = hashlib.sha256(d1_orig_bytes).hexdigest()
    c_data["http_exchange"]["manifest"]["byte_count"] = len(d1_orig_bytes)
    cand_manifest_path.write_text(json.dumps(c_data, indent=2), encoding="utf-8")
    assert verify_candidate_integrity(store, exchange_id) is True


def test_d2_tampered_retrieval_limit_fails_closed(tmp_path: Path) -> None:
    """Verify that tampering with persisted limit or extraction limit fails integrity verification."""
    store = AttemptArtifactStore(tmp_path / "attempt")
    capture = HttpExchangeCapture(store, attempt_id="attempt-d2-limit-tamper")
    sink = CandidateArtifactSink(store)

    resp_obj = {
        "results": [
            {"id": "c1", "text": "Item 1"},
            {"id": "c2", "text": "Item 2"},
        ]
    }
    resp_bytes = json.dumps(resp_obj).encode("utf-8")
    exchange = capture.capture(
        method="POST",
        path="/v1/default/banks/test/memories/recall",
        request_body=b"{}",
        response_body=resp_bytes,
        status_code=200,
        request_id="req-limit-1",
    )

    # Persist with limit=1: position 1 selected, position 2 truncated
    sink.capture_and_persist(
        results=resp_obj["results"],
        selected_positions={1},
        limit=1,
        exchange_manifest=exchange,
    )
    exchange_id = exchange["exchange_id"]
    cand_manifest_path = tmp_path / "attempt" / f"candidates/{exchange_id}.json"
    orig_manifest_text = cand_manifest_path.read_text(encoding="utf-8")

    assert verify_candidate_integrity(store, exchange_id) is True

    # Mutate manifest limit to 2 (expecting both items selected)
    manifest = json.loads(orig_manifest_text)
    manifest["limit"] = 2
    manifest["extraction"]["limit"] = 2
    cand_manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    # Fails because stored candidate 2 has included=False, but recomputed limit 2 requires included=True
    assert verify_candidate_integrity(store, exchange_id) is False

    # Mutate manifest limit to 0 (expecting 0 items selected)
    manifest = json.loads(orig_manifest_text)
    manifest["limit"] = 0
    manifest["extraction"]["limit"] = 0
    cand_manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    # Fails because stored candidate 1 has included=True, but recomputed limit 0 requires included=False
    assert verify_candidate_integrity(store, exchange_id) is False

    # Limit mismatch between top-level limit and extraction.limit
    manifest = json.loads(orig_manifest_text)
    manifest["limit"] = 1
    manifest["extraction"]["limit"] = 5
    cand_manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert verify_candidate_integrity(store, exchange_id) is False

