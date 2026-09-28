from memlife.adapters.hindsight import HindsightMemoryAdapter
from memlife.models.benchmark import NormalizedOutcome, OperationStatus
from memlife.models.provenance import DownstreamExecutionStatus, ProvenanceStatus
from memlife.runner.lifecycle import LifecycleRunner
from memlife.runner.provenance import ProvenanceTraceRunner
from memlife.scenarios import LifecycleEvent, canonical_scenarios
from tests.fakes.hindsight import FakeHindsightTransport


class ObservationOnRecallTransport(FakeHindsightTransport):
    """Expose one provider-derived row when the baseline recall executes."""

    def request(self, method, path, *, query=None, payload=None):
        if method.upper() == "POST" and path.endswith("/memories/recall"):
            bank_id, bank, _ = self._bank(path)
            if not any(row["fact_type"] == "observation" for row in bank.values()):
                source = next(
                    row for row in bank.values() if row["fact_type"] == "world"
                )
                self.add_observation(
                    bank_id,
                    text="Alice is associated with Project Cedar reporting.",
                    source_ids=[source["id"]],
                )
        return super().request(method, path, query=query, payload=payload)


def _adapter() -> HindsightMemoryAdapter:
    return HindsightMemoryAdapter(
        FakeHindsightTransport(),
        restart_callback=lambda: None,
        poll_interval_seconds=0.001,
    )


def test_hindsight_runs_canonical_lifecycle_suite_without_errors() -> None:
    results = LifecycleRunner(_adapter()).run_suite(canonical_scenarios())
    assert len(results) == 24
    assert all(result.operation_status is OperationStatus.SUCCESS for result in results)
    revocation_query = next(
        result
        for result in results
        if result.scenario_id == "revocation"
        and result.intended_event is LifecycleEvent.QUERY
    )
    assert revocation_query.normalized_outcome is NormalizedOutcome.ABSENT
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


def test_hindsight_trace_uses_passthrough_and_no_decision_model() -> None:
    scenario = next(
        item for item in canonical_scenarios() if item.scenario_id == "baseline"
    )
    run = ProvenanceTraceRunner(_adapter()).run_scenario(
        scenario, experiment_id="hindsight-phase04-trace"
    )
    assert run.trace.retrieval_traces
    retrieval = run.trace.retrieval_traces[0]
    assert retrieval.model_execution is DownstreamExecutionStatus.NOT_RUN
    assert retrieval.tool_execution is DownstreamExecutionStatus.NOT_RUN
    assert retrieval.delivered_candidate_ids == tuple(
        candidate.candidate_id for candidate in retrieval.candidates
    )
    assert all(
        candidate.provenance_status is ProvenanceStatus.UNKNOWN
        for candidate in retrieval.candidates
    )
    assert all(
        candidate.metadata["provider_fact_type"] == "world"
        for candidate in retrieval.candidates
    )


def test_hindsight_trace_uses_exposed_observation_source_ids() -> None:
    scenario = next(
        item for item in canonical_scenarios() if item.scenario_id == "baseline"
    )
    adapter = HindsightMemoryAdapter(
        ObservationOnRecallTransport(),
        restart_callback=lambda: None,
        poll_interval_seconds=0.001,
    )
    run = ProvenanceTraceRunner(adapter).run_scenario(
        scenario, experiment_id="hindsight-derived-trace"
    )
    candidates = run.trace.retrieval_traces[0].candidates
    source = next(item for item in candidates if item.metadata["provider_fact_type"] == "world")
    observation = next(
        item for item in candidates if item.metadata["provider_fact_type"] == "observation"
    )
    assert source.surface.value == "SOURCE"
    assert observation.surface.value == "DERIVED"
    assert observation.provenance_status is ProvenanceStatus.KNOWN
    assert observation.source_event_ids
    assert observation.metadata["association_basis"] == "provider_exposed_source_ids"
