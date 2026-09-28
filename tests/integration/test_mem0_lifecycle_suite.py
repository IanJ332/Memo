"""Run the Phase 03 benchmark layer through local Mem0 OSS."""

import pytest

from memlife.adapters.mem0 import MEM0_VERSION, Mem0MemoryAdapter
from memlife.models.benchmark import NormalizedOutcome, OperationStatus
from memlife.runner.lifecycle import LifecycleRunner
from memlife.scenarios import LifecycleEvent, canonical_scenarios

pytestmark = pytest.mark.mem0_integration


def test_mem0_runs_canonical_lifecycle_suite(
    mem0_adapter: Mem0MemoryAdapter,
) -> None:
    results = LifecycleRunner(mem0_adapter).run_suite(canonical_scenarios())

    assert mem0_adapter.provider_version == MEM0_VERSION
    assert len(results) == 24
    assert not [result for result in results if result.operation_status is OperationStatus.ERROR]

    unsupported = [
        result
        for result in results
        if result.operation_status is OperationStatus.UNSUPPORTED
    ]
    assert len(unsupported) == 1
    assert unsupported[0].scenario_id == "revocation"
    assert unsupported[0].intended_event is LifecycleEvent.REVOKE
    assert "not revocation" in str(unsupported[0].unsupported_reason)

    correction = [
        result
        for result in results
        if result.scenario_id == "correction-update"
        and result.intended_event is LifecycleEvent.UPDATE
    ][0]
    supersession = [
        result
        for result in results
        if result.scenario_id == "supersession"
        and result.intended_event is LifecycleEvent.SUPERSEDE
    ][0]
    assert correction.memory_ids_before == correction.memory_ids_after
    assert supersession.memory_ids_before == supersession.memory_ids_after
    assert correction.native_operation == "Memory.update(same UUID)"
    assert supersession.native_operation == "Memory.update(same UUID)"

    revocation_query = [
        result
        for result in results
        if result.scenario_id == "revocation"
        and result.intended_event is LifecycleEvent.QUERY
    ][0]
    assert revocation_query.normalized_outcome is NormalizedOutcome.STALE_ONLY

    delete_queries = [
        result
        for result in results
        if result.scenario_id == "delete-restart"
        and result.intended_event is LifecycleEvent.QUERY
    ]
    assert [result.normalized_outcome for result in delete_queries] == [
        NormalizedOutcome.CURRENT_ONLY,
        NormalizedOutcome.ABSENT,
        NormalizedOutcome.ABSENT,
    ]
    assert results[
        next(
            index
            for index, result in enumerate(results)
            if result.scenario_id == "delete-restart"
            and result.intended_event is LifecycleEvent.INSPECT
        )
    ].history_visible is True
    assert mem0_adapter._phase02a_llm_calls == []  # type: ignore[attr-defined]
