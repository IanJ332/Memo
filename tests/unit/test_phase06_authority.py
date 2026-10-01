"""Phase 06 authority is supplementary to unchanged exact visibility."""

from memlife.models.authority import (
    AuthorityExposureOutcome,
    AuthorityLedger,
    AuthorityLedgerEntry,
    content_sha256,
    normalize_authority_exposure,
)
from memlife.models.benchmark import NormalizedOutcome, OperationStatus
from memlife.models.lifecycle import LifecycleState
from memlife.models.memory import MemoryRecord
from memlife.models.provenance import ProvenanceStatus, RetrievalCandidate
from memlife.runner.experiment import (
    AggregationStatus,
    RepetitionObservation,
    ResidualSignals,
    advances_to_root_cause,
    advances_to_rq3,
    aggregate_repetitions,
    experiment_namespace,
    experiment_run_id,
)
from memlife.runner.lifecycle import normalize_query_observation
from memlife.scenarios.models import ScenarioQuery


def _ledger() -> AuthorityLedger:
    return AuthorityLedger(
        entries=(
            AuthorityLedgerEntry(
                experiment_event_id="event-v1",
                logical_fact_id="fact-v1",
                namespace="test-authority",
                sequence=1,
                lifecycle_state=LifecycleState.SUPERSEDED,
                authoritative=False,
                authority_reason="replaced by v2",
                superseded_by="fact-v2",
                source_content_sha256=content_sha256("v1"),
            ),
            AuthorityLedgerEntry(
                experiment_event_id="event-v2",
                logical_fact_id="fact-v2",
                namespace="test-authority",
                sequence=2,
                lifecycle_state=LifecycleState.ACTIVE,
                authoritative=True,
                authority_reason="current experiment authority",
                supersedes="fact-v1",
                source_content_sha256=content_sha256("v2"),
            ),
        )
    )


def _candidate(name: str, *source_events: str) -> RetrievalCandidate:
    return RetrievalCandidate(
        candidate_id=name,
        provider_memory_id=name,
        source_event_ids=source_events,
        lifecycle_status=LifecycleState.ACTIVE,
        provenance_status=(
            ProvenanceStatus.KNOWN if source_events else ProvenanceStatus.UNKNOWN
        ),
    )


def test_exact_visibility_outcomes_remain_phase03_semantics() -> None:
    query = ScenarioQuery(
        query_id="q",
        text="query",
        current_facts=("current",),
        stale_facts=("stale",),
    )

    def records(*contents: str) -> tuple[MemoryRecord, ...]:
        return tuple(
            MemoryRecord(
                memory_id=f"m-{index}",
                namespace="n",
                content=content,
                state=LifecycleState.ACTIVE,
                revision=1,
            )
            for index, content in enumerate(contents)
        )

    assert normalize_query_observation(records("current"), query)[0] is NormalizedOutcome.CURRENT_ONLY
    assert normalize_query_observation(records("stale"), query)[0] is NormalizedOutcome.STALE_ONLY
    assert normalize_query_observation(records("current", "stale"), query)[0] is NormalizedOutcome.CURRENT_AND_STALE
    assert normalize_query_observation(records("different"), query)[0] is NormalizedOutcome.ABSENT


def test_authority_exposure_outcomes_use_only_direct_event_correlation() -> None:
    ledger = _ledger()
    assert normalize_authority_exposure((_candidate("a", "event-v2"),), ledger) is AuthorityExposureOutcome.AUTHORITATIVE_ONLY
    assert normalize_authority_exposure((_candidate("n", "event-v1"),), ledger) is AuthorityExposureOutcome.NONAUTHORITATIVE_ONLY
    assert normalize_authority_exposure((_candidate("a", "event-v2"), _candidate("n", "event-v1")), ledger) is AuthorityExposureOutcome.AUTHORITATIVE_AND_NONAUTHORITATIVE
    assert normalize_authority_exposure((), ledger) is AuthorityExposureOutcome.NONE
    assert normalize_authority_exposure((_candidate("unknown"),), ledger) is AuthorityExposureOutcome.UNKNOWN_PROVENANCE


def test_semantically_changed_correlated_text_does_not_change_exact_metric() -> None:
    derived = MemoryRecord(
        memory_id="derived-1",
        namespace="n",
        content="Only Bob is currently an approved recipient.",
        state=LifecycleState.ACTIVE,
        revision=1,
    )
    query = ScenarioQuery(
        query_id="q",
        text="Alder recipient",
        current_facts=("Project Alder reports may be sent only to Bob.",),
        stale_facts=("Project Alder reports may be sent to Alice.",),
    )
    exact = normalize_query_observation((derived,), query)[0]
    authority = normalize_authority_exposure(
        (_candidate("derived-1", "event-v2"),), _ledger()
    )
    assert exact is NormalizedOutcome.ABSENT
    assert authority is AuthorityExposureOutcome.AUTHORITATIVE_ONLY


def test_run_identity_is_deterministic_and_namespaces_are_isolated() -> None:
    assert experiment_run_id("mem0", "s1", 2) == "freeze-v1__mem0__s1__r2"
    namespaces = {
        experiment_namespace("mem0", "s1", repetition)
        for repetition in range(1, 4)
    }
    assert len(namespaces) == 3


def test_inconsistent_aggregation_is_preserved_and_residual() -> None:
    runs = (
        RepetitionObservation(
            exact_outcome=NormalizedOutcome.CURRENT_ONLY,
            authority_outcome=AuthorityExposureOutcome.AUTHORITATIVE_ONLY,
            operation_status=OperationStatus.SUCCESS,
            latency_ms=10,
            provenance_known=True,
        ),
        RepetitionObservation(
            exact_outcome=NormalizedOutcome.STALE_ONLY,
            authority_outcome=AuthorityExposureOutcome.NONAUTHORITATIVE_ONLY,
            operation_status=OperationStatus.SUCCESS,
            latency_ms=20,
            provenance_known=True,
        ),
        RepetitionObservation(
            exact_outcome=NormalizedOutcome.CURRENT_ONLY,
            authority_outcome=AuthorityExposureOutcome.AUTHORITATIVE_ONLY,
            operation_status=OperationStatus.SUCCESS,
            latency_ms=30,
            provenance_known=True,
        ),
    )
    aggregate = aggregate_repetitions(runs)
    assert aggregate.status is AggregationStatus.INCONSISTENT
    assert aggregate.inconsistent is True
    assert aggregate.residual is True
    assert aggregate.median_latency_ms == 20


def test_residual_and_rq3_advancement_are_explicit() -> None:
    assert advances_to_root_cause(
        ResidualSignals(reappeared_after_restart=True)
    )
    assert not advances_to_root_cause(ResidualSignals())
    assert advances_to_rq3(
        reproducible_nonauthoritative_exposure=True,
        delivered_context_frozen=True,
        authority_known_for_defense=True,
        reaches_model_boundary=True,
    )
    assert not advances_to_rq3(
        reproducible_nonauthoritative_exposure=True,
        delivered_context_frozen=True,
        authority_known_for_defense=True,
        reaches_model_boundary=False,
    )

