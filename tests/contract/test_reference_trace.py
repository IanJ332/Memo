"""Reference provider supplies controlled, fully known trace relationships."""

from memlife.adapters.reference import ReferenceMemoryAdapter
from memlife.models.provenance import ProvenanceRelation, ProvenanceStatus
from memlife.runner.provenance import ProvenanceTraceRunner
from memlife.scenarios import canonical_scenarios


def test_reference_write_update_query_filter_trace_is_known() -> None:
    scenario = next(
        item for item in canonical_scenarios() if item.scenario_id == "correction-update"
    )
    run = ProvenanceTraceRunner(ReferenceMemoryAdapter()).run_scenario(
        scenario,
        experiment_id="reference-contract-trace",
    )

    source_events = [
        event
        for event in run.trace.lifecycle_events
        if event.event_type in {"WRITE", "UPDATE"}
    ]
    assert [event.relation for event in source_events] == [
        ProvenanceRelation.CREATED_FROM,
        ProvenanceRelation.SUPERSEDES,
    ]
    assert all(
        event.provenance_status is ProvenanceStatus.KNOWN
        for event in source_events
    )
    assert all(
        retrieval.delivered_candidate_ids
        == tuple(candidate.candidate_id for candidate in retrieval.candidates)
        for retrieval in run.trace.retrieval_traces
    )
