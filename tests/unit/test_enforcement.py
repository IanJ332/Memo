"""Transparent pre-LLM enforcement hook behavior."""

from memlife.enforcement import (
    EnforcementContext,
    LifecycleStatusFilter,
    PassThroughFilter,
)
from memlife.models.lifecycle import LifecycleState
from memlife.models.provenance import (
    EnforcementAction,
    ProvenanceStatus,
    RetrievalCandidate,
)


def _context() -> EnforcementContext:
    return EnforcementContext(
        experiment_id="filter-test",
        scenario_id="fixture",
        retrieval_event_id="retrieval-1",
        enforcement_event_id="enforcement-1",
    )


def _candidate(candidate_id: str, status: object) -> RetrievalCandidate:
    return RetrievalCandidate.model_validate(
        {
            "candidate_id": candidate_id,
            "provider_memory_id": candidate_id,
            "sanitized_content": "Synthetic content.",
            "lifecycle_status": status,
        }
    )


def test_pass_through_filter_allows_every_candidate() -> None:
    candidates = (
        _candidate("active", LifecycleState.ACTIVE),
        _candidate("deleted", LifecycleState.DELETED),
        _candidate("unknown", ProvenanceStatus.UNKNOWN),
    )
    decisions = PassThroughFilter().inspect_candidates(candidates, _context())
    assert [decision.decision for decision in decisions] == [
        EnforcementAction.ALLOW,
        EnforcementAction.ALLOW,
        EnforcementAction.ALLOW,
    ]
    assert [decision.candidate_id for decision in decisions] == [
        candidate.candidate_id for candidate in candidates
    ]


def test_lifecycle_filter_uses_only_explicit_status() -> None:
    statuses = (
        LifecycleState.ACTIVE,
        LifecycleState.REVOKED,
        LifecycleState.DELETED,
        LifecycleState.EXPIRED,
        LifecycleState.SUPERSEDED,
        ProvenanceStatus.UNKNOWN,
    )
    candidates = tuple(
        _candidate(f"candidate-{index}", status)
        for index, status in enumerate(statuses)
    )
    decisions = LifecycleStatusFilter().inspect_candidates(candidates, _context())
    assert [decision.decision for decision in decisions] == [
        EnforcementAction.ALLOW,
        EnforcementAction.BLOCK,
        EnforcementAction.BLOCK,
        EnforcementAction.BLOCK,
        EnforcementAction.BLOCK,
        EnforcementAction.TAG,
    ]
    assert decisions[-1].reason_code == "LIFECYCLE_STATUS_NOT_AUTHORITATIVE"
    assert decisions[-1].metadata["unknown_status_policy"] == "TAG"


def test_unknown_status_policy_is_explicitly_configurable() -> None:
    candidate = _candidate("unknown", ProvenanceStatus.UNSUPPORTED)
    decision = LifecycleStatusFilter(
        unknown_action=EnforcementAction.BLOCK
    ).inspect_candidates((candidate,), _context())[0]
    assert decision.decision is EnforcementAction.BLOCK
    assert decision.model_dump(mode="json")["decision"] == "BLOCK"


def test_allow_block_and_tag_serialize_by_value() -> None:
    assert {action.value for action in EnforcementAction} == {"ALLOW", "BLOCK", "TAG"}
