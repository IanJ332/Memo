"""Closed result schema and deterministic JSON serialization."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from memlife.models.benchmark import (
    BenchmarkResult,
    NormalizedOutcome,
    OperationStatus,
    deserialize_results,
    serialize_results,
)
from memlife.scenarios import LifecycleEvent


def _result(**updates: object) -> BenchmarkResult:
    values: dict[str, object] = {
        "scenario_id": "serialization",
        "provider": "reference-in-memory",
        "provider_version": "0.1",
        "namespace": "serialization",
        "step_index": 0,
        "intended_event": LifecycleEvent.QUERY,
        "native_operation": "reference.substring_query",
        "operation_status": OperationStatus.SUCCESS,
        "normalized_outcome": NormalizedOutcome.CURRENT_ONLY,
        "query_text": "Project Cedar",
        "retrieved_current": ("Project Cedar is current.",),
        "observed_records": ("Project Cedar is current.",),
        "expected_authoritative_state": ("Project Cedar is current.",),
        "current_state_correct": True,
        "stale_state_visible": False,
        "provider_metadata": {"zeta": 2, "alpha": 1},
        "latency_ms": 1.25,
        "timestamp": datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc),
    }
    values.update(updates)
    return BenchmarkResult.model_validate(values)


def test_serialization_is_stable_utf8_json_and_round_trips() -> None:
    results = (_result(),)
    first = serialize_results(results)
    second = serialize_results(results)
    assert first == second
    assert '"alpha": 1' in first
    assert first.index('"alpha"') < first.index('"zeta"')
    assert deserialize_results(first) == results


def test_status_requires_matching_reason_or_error() -> None:
    with pytest.raises(ValidationError, match="unsupported_reason"):
        _result(
            operation_status=OperationStatus.UNSUPPORTED,
            normalized_outcome=NormalizedOutcome.UNSUPPORTED,
        )
    with pytest.raises(ValidationError, match="ERROR results require error"):
        _result(
            operation_status=OperationStatus.ERROR,
            normalized_outcome=NormalizedOutcome.ERROR,
        )


def test_result_rejects_sensitive_provider_metadata_keys() -> None:
    with pytest.raises(ValidationError, match="sensitive key"):
        _result(provider_metadata={"nested": {"api_token": "not-allowed"}})
