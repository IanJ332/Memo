"""Lifecycle-to-retrieval-to-enforcement trace correlation."""

from datetime import datetime, timezone

from memlife.adapters.reference import ReferenceMemoryAdapter
from memlife.enforcement import PassThroughFilter
from memlife.models.provenance import (
    DownstreamExecutionStatus,
    EnforcementAction,
    ProvenanceRelation,
    ProvenanceStatus,
)
from memlife.runner.lifecycle import LifecycleRunner
from memlife.runner.provenance import ProvenanceTraceRunner
from memlife.scenarios import canonical_scenarios

FIXED_TIME = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)


def _scenario(scenario_id: str):
    return next(
        scenario
        for scenario in canonical_scenarios()
        if scenario.scenario_id == scenario_id
    )


def _run_reference_trace():
    adapter = ReferenceMemoryAdapter()
    lifecycle = LifecycleRunner(
        adapter,
        clock=lambda: FIXED_TIME,
        timer=lambda: 1.0,
    )
    return ProvenanceTraceRunner(
        adapter,
        candidate_filter=PassThroughFilter(),
        lifecycle_runner=lifecycle,
    ).run_scenario(_scenario("supersession"), experiment_id="reference-trace-1")


def test_reference_trace_correlates_lifecycle_retrieval_and_delivery() -> None:
    run = _run_reference_trace()
    trace = run.trace
    assert len(run.benchmark_results) == len(_scenario("supersession").lifecycle_steps)

    write = next(event for event in trace.lifecycle_events if event.event_type == "WRITE")
    supersede = next(
        event for event in trace.lifecycle_events if event.event_type == "SUPERSEDE"
    )
    assert write.relation is ProvenanceRelation.CREATED_FROM
    assert supersede.relation is ProvenanceRelation.SUPERSEDES
    assert supersede.parent_event_id == write.event_id
    assert supersede.provenance_status is ProvenanceStatus.KNOWN

    retrieval = next(item for item in trace.retrieval_traces if item.candidates)
    assert len(retrieval.candidates) == 1
    candidate = retrieval.candidates[0]
    assert candidate.sanitized_content is None
    assert candidate.source_event_ids == (supersede.event_id,)
    assert candidate.provenance_status is ProvenanceStatus.KNOWN
    assert retrieval.decisions[0].decision is EnforcementAction.ALLOW
    assert retrieval.delivered_candidate_ids == (candidate.candidate_id,)
    assert retrieval.model_execution is DownstreamExecutionStatus.NOT_RUN
    assert retrieval.tool_execution is DownstreamExecutionStatus.NOT_RUN
    assert retrieval.model_decision is None
    assert retrieval.tool_action is None
    assert trace.failure_attributions == ()


def test_trace_event_ids_are_stable_for_same_explicit_experiment() -> None:
    first = _run_reference_trace().trace
    second = _run_reference_trace().trace
    assert [event.event_id for event in first.lifecycle_events] == [
        event.event_id for event in second.lifecycle_events
    ]
    assert [item.retrieval_event_id for item in first.retrieval_traces] == [
        item.retrieval_event_id for item in second.retrieval_traces
    ]


def test_phase03_benchmark_result_shape_remains_separate() -> None:
    run = _run_reference_trace()
    serialized_fields = run.benchmark_results[0].model_dump(mode="json")
    assert "trace_schema_version" not in serialized_fields
    assert serialized_fields["benchmark_version"] == "0.1"
