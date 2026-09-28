"""Run the Phase 03 benchmark layer through local Mem0 OSS."""

import pytest

from memlife.adapters.mem0 import MEM0_VERSION, Mem0MemoryAdapter
from memlife.models.benchmark import NormalizedOutcome, OperationStatus
from memlife.models.provenance import ProvenanceRelation, ProvenanceStatus
from memlife.runner.lifecycle import LifecycleRunner
from memlife.runner.provenance import ProvenanceTraceRunner
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


def test_mem0_trace_keeps_provider_internal_causality_unknown(
    mem0_adapter: Mem0MemoryAdapter,
) -> None:
    scenario = next(
        item for item in canonical_scenarios() if item.scenario_id == "correction-update"
    )
    run = ProvenanceTraceRunner(mem0_adapter).run_scenario(
        scenario,
        experiment_id="mem0-provenance-reality-check",
    )

    mutations = [
        event
        for event in run.trace.lifecycle_events
        if event.event_type in {"WRITE", "UPDATE"}
    ]
    assert mutations
    assert all(event.relation is ProvenanceRelation.UNKNOWN for event in mutations)
    assert all(
        event.provenance_status is ProvenanceStatus.UNKNOWN for event in mutations
    )
    candidates = [
        candidate
        for retrieval in run.trace.retrieval_traces
        for candidate in retrieval.candidates
    ]
    assert candidates
    assert all(
        candidate.provenance_status is ProvenanceStatus.UNKNOWN
        for candidate in candidates
    )
    assert all(candidate.provider_memory_id for candidate in candidates)
    assert all(
        candidate.metadata["association_basis"] == "experiment_provider_id_match"
        for candidate in candidates
    )
    retrieval_observations = [
        event
        for event in run.trace.lifecycle_events
        if event.event_type == "RETRIEVAL_CANDIDATE_OBSERVED"
    ]
    assert retrieval_observations
    assert all(
        event.relation is ProvenanceRelation.RETRIEVED_AS
        and event.provenance_status is ProvenanceStatus.KNOWN
        for event in retrieval_observations
    )
    assert mem0_adapter._phase02a_llm_calls == []  # type: ignore[attr-defined]
