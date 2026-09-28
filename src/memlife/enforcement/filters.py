"""Transparent controls for proving Phase 03B enforcement plumbing."""

from __future__ import annotations

from memlife.enforcement.base import CandidateFilter, EnforcementContext
from memlife.models.lifecycle import LifecycleState
from memlife.models.provenance import (
    EnforcementAction,
    EnforcementDecision,
    RetrievalCandidate,
    deterministic_trace_id,
)


class PassThroughFilter(CandidateFilter):
    """D0/control filter: every candidate is allowed without policy inference."""

    RULE_ID = "pass-through-control-v0.1"

    def inspect_candidates(
        self,
        candidates: tuple[RetrievalCandidate, ...],
        context: EnforcementContext,
    ) -> tuple[EnforcementDecision, ...]:
        return tuple(
            EnforcementDecision(
                decision_id=deterministic_trace_id(
                    "decision", context.enforcement_event_id, candidate.candidate_id
                ),
                enforcement_event_id=context.enforcement_event_id,
                candidate_id=candidate.candidate_id,
                decision=EnforcementAction.ALLOW,
                reason_code="PASS_THROUGH_CONTROL",
                authoritative_status=candidate.lifecycle_status,
                rule_id=self.RULE_ID,
                provenance_basis="NOT_EVALUATED_CONTROL",
            )
            for candidate in candidates
        )


class LifecycleStatusFilter(CandidateFilter):
    """Basic metadata-only baseline, not the Memory Authority Gateway.

    Only explicit normalized lifecycle status is consulted. ACTIVE is allowed;
    REVOKED, DELETED, EXPIRED, and SUPERSEDED are blocked. Missing/unknown,
    unsupported, or not-applicable status is tagged and remains delivered by
    default so this primitive does not silently treat ambiguity as safe or
    unsafe. ``unknown_action`` makes that behavior explicit and configurable.
    """

    RULE_ID = "explicit-lifecycle-status-baseline-v0.1"
    _BLOCKED = frozenset(
        {
            LifecycleState.REVOKED,
            LifecycleState.DELETED,
            LifecycleState.EXPIRED,
            LifecycleState.SUPERSEDED,
        }
    )

    def __init__(
        self, unknown_action: EnforcementAction = EnforcementAction.TAG
    ) -> None:
        self.unknown_action = unknown_action

    def inspect_candidates(
        self,
        candidates: tuple[RetrievalCandidate, ...],
        context: EnforcementContext,
    ) -> tuple[EnforcementDecision, ...]:
        decisions = []
        for candidate in candidates:
            status = candidate.lifecycle_status
            if status is LifecycleState.ACTIVE:
                action = EnforcementAction.ALLOW
                reason = "EXPLICIT_ACTIVE_STATUS"
            elif status in self._BLOCKED:
                action = EnforcementAction.BLOCK
                reason = f"EXPLICIT_{status.value.upper()}_STATUS"
            else:
                action = self.unknown_action
                reason = "LIFECYCLE_STATUS_NOT_AUTHORITATIVE"

            basis = (
                "EXPLICIT_NORMALIZED_LIFECYCLE_STATUS"
                if isinstance(status, LifecycleState)
                else f"PROVENANCE_STATUS_{status.value}"
            )
            decisions.append(
                EnforcementDecision(
                    decision_id=deterministic_trace_id(
                        "decision",
                        context.enforcement_event_id,
                        candidate.candidate_id,
                    ),
                    enforcement_event_id=context.enforcement_event_id,
                    candidate_id=candidate.candidate_id,
                    decision=action,
                    reason_code=reason,
                    authoritative_status=status,
                    rule_id=self.RULE_ID,
                    provenance_basis=basis,
                    metadata={
                        "unknown_status_policy": self.unknown_action.value,
                        "policy_scope": "explicit_metadata_only",
                    },
                )
            )
        return tuple(decisions)
