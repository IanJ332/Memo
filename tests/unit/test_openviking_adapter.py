from __future__ import annotations

from datetime import datetime, timezone
import json

import pytest

from memlife.adapters.base import AdapterError, CapabilitySupport, ProviderCapability
from memlife.adapters.base import UnsupportedCapabilityError
from memlife.adapters.openviking import (
    OPENVIKING_UPSTREAM_COMMIT,
    OPENVIKING_VERSION,
    OpenVikingHTTPError,
    OpenVikingMemoryAdapter,
    OpenVikingReadinessTimeout,
    ServiceExitedBeforeReady,
    UrllibOpenVikingTransport,
    parse_memory_diff,
    phase05a_manifest_configuration,
)
from memlife.models.lifecycle import LifecycleState
from memlife.models.memory import DeleteCommand, QueryCommand, SupersedeCommand, WriteCommand
from memlife.models.provenance import MemorySurface, ProvenanceStatus
from memlife.models.provenance import RetrievalCandidate
from memlife.models.provenance import serialize_trace
from memlife.runner.lifecycle import LifecycleRunner
from memlife.runner.provenance import ProvenanceTraceRunner
from memlife.scenarios.canonical import canonical_scenarios
from tests.fakes.openviking import FakeOpenVikingTransport


class _SteppingMonotonic:
    def __init__(self, step: float = 0.05) -> None:
        self.value = -step
        self.step = step

    def __call__(self) -> float:
        self.value += self.step
        return self.value


class _ReadinessTransport:
    def __init__(self, ready_responses) -> None:
        self.ready_responses = iter(ready_responses)
        self.requests: list[str] = []

    def request(self, method, path, *, query=None, payload=None):
        self.requests.append(path)
        if path == "/health":
            return {"status": "ok", "healthy": True, "version": "0.4.22"}
        response = next(self.ready_responses)
        if isinstance(response, Exception):
            raise response
        return response


class _JSONResponse:
    def __init__(self, payload) -> None:
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self):
        return self.payload


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"status": "ok", "result": {"x": 1}}, {"x": 1}),
        (
            {"status": "ok", "healthy": True, "version": "0.4.22"},
            {"status": "ok", "healthy": True, "version": "0.4.22"},
        ),
    ],
)
def test_http_ok_response_contract_is_shape_sensitive(
    monkeypatch, payload, expected
) -> None:
    monkeypatch.setattr(
        "memlife.adapters.openviking.urlopen",
        lambda *_args, **_kwargs: _JSONResponse(payload),
    )
    assert UrllibOpenVikingTransport().request("GET", "/health") == expected


def _readiness_adapter(transport, **kwargs) -> OpenVikingMemoryAdapter:
    return OpenVikingMemoryAdapter(
        transport,
        quiescence_timeout_seconds=1,
        poll_interval_seconds=0.01,
        sleeper=lambda _: None,
        monotonic=_SteppingMonotonic(),
        **kwargs,
    )


def _not_ready(checks=None) -> OpenVikingHTTPError:
    payload = {"status": "not_ready", "checks": checks or {"embedding": "not_initialized"}}
    return OpenVikingHTTPError(503, str(payload), payload=payload)


def test_pinned_ready_status_passes_immediately() -> None:
    transport = _ReadinessTransport(
        [{"status": "ready", "checks": {"agfs": "ok", "embedding": "ok"}}]
    )
    adapter = _readiness_adapter(transport)
    assert adapter.wait_until_ready()["status"] == "ready"
    assert transport.requests == ["/health", "/ready"]
    assert adapter.readiness_diagnostics["readiness_status"] == "ready"


def test_pinned_503_not_ready_retries_then_passes() -> None:
    transport = _ReadinessTransport(
        [_not_ready(), {"status": "ready", "checks": {"embedding": "ok"}}]
    )
    adapter = _readiness_adapter(transport)
    assert adapter.wait_until_ready()["status"] == "ready"
    assert transport.requests.count("/ready") == 2


def test_healthy_liveness_never_substitutes_for_readiness() -> None:
    adapter = _readiness_adapter(_ReadinessTransport([_not_ready()] * 20))
    with pytest.raises(OpenVikingReadinessTimeout) as captured:
        adapter.wait_until_ready(timeout_seconds=0.3)
    assert captured.value.diagnostics["health_status"] == "ok"
    assert captured.value.diagnostics["readiness_status"] == "not_ready"


def test_healthy_without_provider_status_does_not_fabricate_liveness() -> None:
    class MissingStatusTransport(_ReadinessTransport):
        def request(self, method, path, *, query=None, payload=None):
            if path == "/health":
                return {"healthy": True, "version": "0.4.22"}
            return super().request(method, path, query=query, payload=payload)

    adapter = _readiness_adapter(
        MissingStatusTransport([{"status": "ready", "checks": {}}])
    )
    adapter.wait_until_ready()
    assert adapter.readiness_diagnostics["health_status"] is None
    assert adapter.readiness_diagnostics["health_healthy"] is True


def test_unknown_ready_payload_is_never_silently_accepted() -> None:
    adapter = _readiness_adapter(_ReadinessTransport([{"status": "mystery"}] * 20))
    with pytest.raises(OpenVikingReadinessTimeout) as captured:
        adapter.wait_until_ready(timeout_seconds=0.3)
    assert captured.value.diagnostics["readiness_status"] == "mystery"


def test_connection_refused_retries_while_owned_process_is_alive() -> None:
    failures = [AdapterError("connection refused")] * 20
    adapter = _readiness_adapter(
        _ReadinessTransport(failures), process_is_running=lambda: True
    )
    with pytest.raises(OpenVikingReadinessTimeout) as captured:
        adapter.wait_until_ready(timeout_seconds=0.3)
    assert captured.value.diagnostics["request_error_class"] == "AdapterError"
    assert captured.value.diagnostics["service_process_alive"] is True


def test_owned_process_exit_stops_readiness_immediately() -> None:
    states = iter([True, False])
    adapter = _readiness_adapter(
        _ReadinessTransport([AdapterError("connection refused")]),
        process_is_running=lambda: next(states),
        process_exit_code=lambda: 17,
    )
    with pytest.raises(ServiceExitedBeforeReady) as captured:
        adapter.wait_until_ready(timeout_seconds=10)
    assert captured.value.exit_code == 17
    assert captured.value.diagnostics["service_process_alive"] is False


def _adapter(
    transport: FakeOpenVikingTransport | None = None,
    *,
    restart=None,
    timeout: float = 1.0,
) -> tuple[OpenVikingMemoryAdapter, FakeOpenVikingTransport]:
    fake = transport or FakeOpenVikingTransport()
    ids = iter(["source-0001", "source-0002", "source-0003"])
    clock = iter(
        [
            datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc),
            datetime(2026, 9, 28, 12, 0, 1, tzinfo=timezone.utc),
        ]
        * 10
    )
    return (
        OpenVikingMemoryAdapter(
            fake,
            restart_callback=restart,
            quiescence_timeout_seconds=timeout,
            poll_interval_seconds=0.0001,
            sleeper=lambda _: None,
            clock=lambda: next(clock),
            id_factory=lambda: next(ids),
        ),
        fake,
    )


@pytest.mark.parametrize(
    "url",
    ["localhost:1933", "ftp://localhost/x", "http://user:pass@localhost:1933", "http://localhost:1933?q=1"],
)
def test_url_validation_rejects_unsafe_or_non_http_values(url: str) -> None:
    with pytest.raises(ValueError):
        UrllibOpenVikingTransport(url)


def test_configuration_is_frozen_and_contains_no_credentials() -> None:
    config = phase05a_manifest_configuration()
    assert config["provider_version"] == OPENVIKING_VERSION == "0.4.22"
    assert config["upstream_commit"] == OPENVIKING_UPSTREAM_COMMIT
    assert config["service_port"] == 1933
    assert not any("key" in key for key in config)


def test_capabilities_are_honest_and_restart_is_conditional() -> None:
    adapter, _ = _adapter(restart=lambda: None)
    assert set(adapter.capabilities) == set(ProviderCapability)
    assert adapter.capabilities[ProviderCapability.UPDATE_OR_SUPERSEDE] is CapabilitySupport.UNSUPPORTED
    assert adapter.capabilities[ProviderCapability.DELETE_OR_INVALIDATE] is CapabilitySupport.SUPPORTED
    no_restart, _ = _adapter()
    assert no_restart.capabilities[ProviderCapability.RESTART] is CapabilitySupport.UNSUPPORTED


def test_session_commit_poll_diff_retrieval_inspection_and_correlation() -> None:
    adapter, fake = _adapter()
    record = adapter.write(
        WriteCommand(namespace="phase05", content="The launch color is amber.")
    )
    assert record.memory_id == "source-0001"
    assert record.metadata["openviking_provider_memory_uris"] == [
        "viking://user/test/memories/events/task-0001-0.md"
    ]
    assert [request[1] for request in fake.requests[:3]] == [
        "/api/v1/sessions",
        "/api/v1/sessions/memlife-phase05-source-0001/messages",
        "/api/v1/sessions/memlife-phase05-source-0001/commit",
    ]
    queried = adapter.query(QueryCommand(namespace="phase05", query="launch color"))
    assert len(queried) == 1
    assert queried[0].content == "The launch color is amber."
    assert queried[0].memory_id.startswith("viking://")
    inspected = adapter.list_or_inspect("phase05")
    assert [(item.memory_id, item.content) for item in inspected] == [
        (queried[0].memory_id, queried[0].content)
    ]
    assert adapter.trace_surface_for(record) is MemorySurface.SOURCE
    assert adapter.trace_surface_for(queried[0]) is MemorySurface.DERIVED
    assert adapter.trace_provenance_status_for(queried[0]) is ProvenanceStatus.KNOWN
    assert adapter.trace_source_provider_ids_for(queried[0]) == ("source-0001",)
    history = adapter.history_for(record.memory_id, namespace="phase05")
    assert history[0]["event"] == "add"


def test_one_source_event_retains_multiple_provider_uris_without_selecting_one() -> None:
    fake = FakeOpenVikingTransport()
    fake.memory_count_per_commit = 2
    adapter, _ = _adapter(fake)
    record = adapter.write(WriteCommand(namespace="many", content="Remember two facts."))
    assert record.memory_id == "source-0001"
    assert len(record.metadata["openviking_provider_memory_uris"]) == 2
    assert adapter.benchmark_metadata()["write_correlation"].startswith("one-to-many")


def test_completed_write_metadata_serializes_quiescence_and_diff_counts() -> None:
    fake = FakeOpenVikingTransport()
    fake.memory_count_per_commit = 2
    adapter, _ = _adapter(fake)
    record = adapter.write(WriteCommand(namespace="evidence", content="Remember two facts."))
    evidence = adapter.completed_write_metadata(record.memory_id)
    assert evidence["session_id"] == record.metadata["openviking_session_id"]
    assert evidence["archive_uri"] == record.metadata["openviking_archive_uri"]
    assert evidence["task_id"] == record.metadata["openviking_task_id"]
    assert evidence["task_final_status"] == "completed"
    assert evidence["task_submitted_at"]
    assert evidence["task_completed_at"]
    assert evidence["quiescence_seconds"] >= 0
    assert evidence["provider_memory_uri_count"] == 2
    assert evidence["memory_diff_add_count"] == 2
    assert evidence["memory_diff_update_count"] == 0
    assert evidence["memory_diff_delete_count"] == 0
    assert evidence["memory_diff_skipped_count"] == 0


def test_delete_removes_all_correlated_uris_but_revocation_is_unsupported() -> None:
    fake = FakeOpenVikingTransport()
    fake.memory_count_per_commit = 2
    adapter, _ = _adapter(fake)
    record = adapter.write(WriteCommand(namespace="delete", content="Remove this."))
    with pytest.raises(UnsupportedCapabilityError, match="revoke"):
        adapter.delete_or_invalidate(
            DeleteCommand(
                namespace="delete",
                memory_id=record.memory_id,
                disposition=LifecycleState.REVOKED,
            )
        )
    deleted = adapter.delete_or_invalidate(
        DeleteCommand(namespace="delete", memory_id=record.memory_id)
    )
    assert deleted.state is LifecycleState.DELETED
    assert adapter.query(QueryCommand(namespace="delete", query="Remove")) == ()
    assert fake.memory == {}


def test_update_and_supersession_are_explicitly_unsupported() -> None:
    adapter, _ = _adapter()
    with pytest.raises(UnsupportedCapabilityError):
        adapter.update_or_supersede(
            SupersedeCommand(namespace="n", memory_id="source", content="new")
        )


def test_failed_task_and_timeout_fail_closed() -> None:
    failed = FakeOpenVikingTransport()
    failed.fail_task = True
    adapter, _ = _adapter(failed)
    with pytest.raises(RuntimeError, match="ended as failed"):
        adapter.write(WriteCommand(namespace="failed", content="fact"))

    pending = FakeOpenVikingTransport()
    pending.task_statuses = ["pending"]
    adapter, _ = _adapter(pending, timeout=0.00001)
    with pytest.raises(TimeoutError, match="did not complete"):
        adapter.write(WriteCommand(namespace="timeout", content="fact"))


def test_memory_diff_parser_preserves_add_update_delete_and_skips() -> None:
    diff = parse_memory_diff(
        {
            "archive_uri": "viking://user/u/sessions/s/history/archive_001",
            "extracted_at": "2026-09-28T12:00:00Z",
            "operations": {
                "adds": [{"uri": "m/a", "memory_type": "events", "after": "a"}],
                "updates": [{"uri": "m/b", "memory_type": "profile", "before": "b1", "after": "b2"}],
                "deletes": [{"uri": "m/c", "memory_type": "entities", "deleted_content": "c"}],
            },
            "skipped_operations": [{"memory_type": "events", "reason_code": "invalid_ranges"}],
        }
    )
    assert [operation.operation for operation in diff.operations] == ["add", "update", "delete"]
    assert diff.skipped_operations[0]["reason_code"] == "invalid_ranges"


def test_restart_callback_trigger_derivation_and_namespace_reset() -> None:
    restarted: list[str] = []
    adapter, fake = _adapter(restart=lambda: restarted.append("restart"))
    record = adapter.write(WriteCommand(namespace="reset", content="fact"))
    session_id = record.metadata["openviking_session_id"]
    assert adapter.trigger_derivation(session_id)[0]["status"] == "extracted"
    adapter.restart()
    assert restarted == ["restart"]
    adapter.reset_namespace("reset")
    assert fake.sessions == {}
    assert adapter.list_or_inspect("reset") == ()


def test_trace_metadata_is_sanitized_and_serializable_deterministically() -> None:
    adapter, _ = _adapter()
    adapter.write(WriteCommand(namespace="trace", content="The flag is green."))
    result = adapter.query(QueryCommand(namespace="trace", query="flag green"))[0]
    metadata = adapter.trace_metadata_for(result)
    RetrievalCandidate(candidate_id="candidate", metadata=dict(metadata))
    assert "api_key" not in repr(metadata).casefold()
    assert list(metadata) == list(adapter.trace_metadata_for(result))


def test_memory_diff_correlation_generates_known_provenance_trace() -> None:
    adapter, _ = _adapter()
    fixed = datetime(2026, 9, 28, 13, 0, tzinfo=timezone.utc)
    lifecycle = LifecycleRunner(adapter, clock=lambda: fixed)
    scenario = canonical_scenarios()[0]
    run = ProvenanceTraceRunner(adapter, lifecycle_runner=lifecycle).run_scenario(
        scenario, experiment_id="phase05-openviking-trace"
    )
    candidate = run.trace.retrieval_traces[0].candidates[0]
    assert candidate.surface is MemorySurface.DERIVED
    assert candidate.provenance_status is ProvenanceStatus.KNOWN
    assert candidate.source_event_ids
    assert serialize_trace(run.trace) == serialize_trace(run.trace)


def test_exact_match_remains_absent_while_direct_correlation_is_visible() -> None:
    class DerivedTextTransport(FakeOpenVikingTransport):
        def request(self, method, path, *, query=None, payload=None):
            response = super().request(method, path, query=query, payload=payload)
            if method.upper() == "POST" and path.endswith("/commit"):
                for uri, content in list(self.memory.items()):
                    self.memory[uri] = f"{content} Provider-derived summary."
            return response

    adapter, _ = _adapter(DerivedTextTransport())
    scenario = canonical_scenarios()[0]
    query_result = LifecycleRunner(adapter).run_scenario(scenario)[1]
    assert query_result.normalized_outcome.value == "ABSENT"
    assert query_result.current_state_correct is False
    assert query_result.provider_metadata["correlated_retrieval_count"] == 1
    assert query_result.provider_metadata["correlated_source_ids"] == ["source-0001"]
    assert query_result.provider_metadata["correlated_provider_record_ids"][0].startswith(
        "viking://"
    )
