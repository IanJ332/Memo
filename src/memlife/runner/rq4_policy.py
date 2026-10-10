"""Minimal deterministic authority mediation for the offline RQ4 pilot.

The policy consumes exact identities that were established before evaluation.
It never derives proposition identity from candidate text, rank, or similarity.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Mapping, Self

from pydantic import field_validator, model_validator

from memlife.models.lifecycle import LifecycleState
from memlife.models.mediator import (
    AuthorityDecision,
    AuthoritySnapshot,
    CandidateEnvelope,
    MediatorAction,
    RelationEdge,
    canonical_contract_sha256,
)
from memlife.models.memory import NonEmptyText, StrictModel
from memlife.models.provenance import MemorySurface

RQ4_POLICY_VERSION = "rq4-minimal-exact-v2"
CONTEXT_MAGIC = b"MEMLIFE-RQ4-CONTEXT-V1\x00"
_INVALIDATED_STATES = {
    LifecycleState.SUPERSEDED,
    LifecycleState.REVOKED,
    LifecycleState.DELETED,
    LifecycleState.EXPIRED,
}
_SUPPORTED_LINEAGE_RELATIONS = {"CREATED_FROM", "DERIVED_FROM", "RETRIEVED_FROM"}


class ContentIdentityBinding(StrictModel):
    """Independent evidence binding candidate bytes to one proposition."""

    binding_id: NonEmptyText
    raw_bytes_sha256: NonEmptyText
    canonical_proposition_sha256: NonEmptyText
    logical_fact_id: NonEmptyText
    source_event_id: NonEmptyText
    canonicalization_id: NonEmptyText
    evidence_source_id: NonEmptyText
    evidence_source_sha256: NonEmptyText

    @field_validator(
        "raw_bytes_sha256",
        "canonical_proposition_sha256",
        "evidence_source_sha256",
    )
    @classmethod
    def hashes_are_sha256(cls, value: str) -> str:
        if len(value) != 64 or any(
            character not in "0123456789abcdef" for character in value
        ):
            raise ValueError("content identity hashes must be lowercase SHA-256")
        return value


class AuthorityBundle(StrictModel):
    """Versioned authority evidence whose artifact is independent of retrieval."""

    ledger_version: NonEmptyText
    authority_source_id: NonEmptyText
    authority_source_sha256: NonEmptyText
    snapshots: tuple[AuthoritySnapshot, ...] = ()
    content_bindings: tuple[ContentIdentityBinding, ...] = ()

    @field_validator("authority_source_sha256")
    @classmethod
    def source_hash_is_sha256(cls, value: str) -> str:
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError("authority_source_sha256 must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def authority_coordinates_are_unique(self) -> Self:
        version_ids = [snapshot.version_id for snapshot in self.snapshots]
        if len(version_ids) != len(set(version_ids)):
            raise ValueError("authority snapshot version_id values must be unique")
        source_event_ids = [snapshot.source_event_id for snapshot in self.snapshots]
        if len(source_event_ids) != len(set(source_event_ids)):
            raise ValueError("authority snapshot source_event_id values must be unique")
        binding_ids = [binding.binding_id for binding in self.content_bindings]
        if len(binding_ids) != len(set(binding_ids)):
            raise ValueError("content binding IDs must be unique")
        binding_coordinates = [
            (
                binding.raw_bytes_sha256,
                binding.canonical_proposition_sha256,
                binding.logical_fact_id,
                binding.source_event_id,
                binding.canonicalization_id,
            )
            for binding in self.content_bindings
        ]
        if len(binding_coordinates) != len(set(binding_coordinates)):
            raise ValueError("content binding coordinates must be unique")
        return self


@dataclass(frozen=True)
class MediationResult:
    """Deterministic decisions, allow-only context, and separate audit output."""

    decisions: tuple[AuthorityDecision, ...]
    delivered_candidate_ids: tuple[str, ...]
    delivered_context: bytes
    audit_decisions: tuple[AuthorityDecision, ...]


@dataclass(frozen=True)
class BaselineDecision:
    candidate_id: str
    decision: MediatorAction
    reason_code: str


class BaselinePolicy(str, Enum):
    PASS_THROUGH = "PASS_THROUGH"
    NAIVE_ANCESTRY_ONLY = "NAIVE_ANCESTRY_ONLY"


def _canonical_sha256(value: object) -> str:
    exact = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(exact).hexdigest()


def _aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("evaluation_timestamp must include a timezone")


def _input_bundle_sha256(
    candidates: tuple[CandidateEnvelope, ...],
    content_by_candidate_id: Mapping[str, bytes],
) -> str:
    content_hashes = [
        {
            "candidate_id": candidate.candidate_id,
            "supplied_content_sha256": (
                hashlib.sha256(content_by_candidate_id[candidate.candidate_id]).hexdigest()
                if candidate.candidate_id in content_by_candidate_id
                else None
            ),
        }
        for candidate in candidates
    ]
    return _canonical_sha256(
        {
            "candidate_contract_sha256": canonical_contract_sha256(candidates),
            "supplied_content": content_hashes,
        }
    )


def _lineage_edges(candidate: CandidateEnvelope) -> tuple[RelationEdge, ...]:
    expected = set(candidate.source_ids)
    represented = {
        edge.source_id
        for edge in candidate.relation_edges
        if edge.target_id == candidate.candidate_id
    }
    missing = sorted(expected - represented)
    malformed = sorted(
        (
            edge
            for edge in candidate.relation_edges
            if edge.target_id != candidate.candidate_id
            or edge.source_id not in expected
            or edge.relation not in _SUPPORTED_LINEAGE_RELATIONS
        ),
        key=lambda edge: (edge.source_id, edge.target_id, edge.relation),
    )
    return tuple(
        [
            RelationEdge(
                source_id=source_id,
                target_id=candidate.candidate_id,
                relation="UNRESOLVED_SOURCE",
            )
            for source_id in missing
        ]
        + malformed
    )


def _frame_allowed_content(
    candidates: tuple[CandidateEnvelope, ...],
    content_by_candidate_id: Mapping[str, bytes],
    decisions: tuple[AuthorityDecision, ...],
) -> tuple[tuple[str, ...], bytes]:
    actions = {
        candidate.candidate_id: decision.decision
        for candidate, decision in zip(candidates, decisions, strict=True)
    }
    delivered_ids: list[str] = []
    frames = bytearray(CONTEXT_MAGIC)
    for candidate in candidates:
        if actions[candidate.candidate_id] is not MediatorAction.ALLOW:
            continue
        candidate_id = candidate.candidate_id.encode("utf-8")
        content = content_by_candidate_id[candidate.candidate_id]
        frames.extend(len(candidate_id).to_bytes(8, "big"))
        frames.extend(candidate_id)
        frames.extend(len(content).to_bytes(8, "big"))
        frames.extend(content)
        delivered_ids.append(candidate.candidate_id)
    return tuple(delivered_ids), bytes(frames)


def _is_superseded_ancestor(
    candidate_ancestor: AuthoritySnapshot,
    current: AuthoritySnapshot,
    snapshots_by_version: Mapping[str, AuthoritySnapshot],
) -> bool:
    if candidate_ancestor.lifecycle_state is not LifecycleState.SUPERSEDED:
        return False
    cursor = candidate_ancestor
    visited: set[str] = set()
    while cursor.superseded_by is not None and cursor.version_id not in visited:
        visited.add(cursor.version_id)
        if cursor.superseded_by == current.version_id:
            return True
        next_snapshot = snapshots_by_version.get(cursor.superseded_by)
        if next_snapshot is None:
            return False
        cursor = next_snapshot
    return False


def evaluate_candidates(
    candidates: tuple[CandidateEnvelope, ...],
    authority: AuthorityBundle,
    content_by_candidate_id: Mapping[str, bytes],
    *,
    policy_version: str,
    evaluation_timestamp: datetime,
) -> MediationResult:
    """Evaluate exact candidates against an independent authority bundle.

    Missing or contradictory evidence yields ``QUARANTINE``. ``DENY`` is
    reserved for an exact proposition/version match to an invalidated record.
    """

    _aware(evaluation_timestamp)
    if policy_version != RQ4_POLICY_VERSION:
        raise ValueError(f"policy_version must be {RQ4_POLICY_VERSION!r}")
    candidate_ids = [candidate.candidate_id for candidate in candidates]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("candidate_id values must be unique")
    extras = set(content_by_candidate_id) - set(candidate_ids)
    if extras:
        raise ValueError("content mapping contains unknown candidate IDs")
    if any(not isinstance(value, bytes) for value in content_by_candidate_id.values()):
        raise TypeError("candidate content values must be bytes")
    if authority.authority_source_id in set(candidate_ids):
        raise ValueError("authority source must be independent of retrieved candidates")
    if authority.authority_source_sha256 in {
        candidate.raw_bytes_sha256 for candidate in candidates
    }:
        raise ValueError("authority artifact must not be the candidate content artifact")
    candidate_hashes = {candidate.raw_bytes_sha256 for candidate in candidates}
    if any(
        binding.evidence_source_id in set(candidate_ids)
        for binding in authority.content_bindings
    ):
        raise ValueError("content binding evidence must be independent of candidates")
    if any(
        binding.evidence_source_sha256 in candidate_hashes
        for binding in authority.content_bindings
    ):
        raise ValueError(
            "content binding evidence artifact must not be candidate content"
        )

    input_hash = _input_bundle_sha256(candidates, content_by_candidate_id)
    authority_hash = canonical_contract_sha256((authority,))
    snapshots_by_source: dict[str, list[AuthoritySnapshot]] = {}
    snapshots_by_version = {
        snapshot.version_id: snapshot for snapshot in authority.snapshots
    }
    for snapshot in authority.snapshots:
        snapshots_by_source.setdefault(snapshot.source_event_id, []).append(snapshot)

    decisions: list[AuthorityDecision] = []
    for candidate in candidates:
        reasons: list[str] = []
        unresolved: list[RelationEdge] = list(_lineage_edges(candidate))
        supplied = content_by_candidate_id.get(candidate.candidate_id)
        if supplied is None:
            reasons.append("RAW_CONTENT_MISSING")
        elif hashlib.sha256(supplied).hexdigest() != candidate.raw_bytes_sha256:
            reasons.append("RAW_CONTENT_SHA256_MISMATCH")

        if candidate.logical_fact_id is None or candidate.canonical_body_sha256 is None:
            reasons.append("MISSING_PROPOSITION_IDENTITY")
        if not candidate.source_ids:
            reasons.append("MISSING_LINEAGE")
        if (
            candidate.valid_from is not None
            and evaluation_timestamp < candidate.valid_from
        ) or (
            candidate.valid_until is not None
            and evaluation_timestamp > candidate.valid_until
        ):
            reasons.append("CANDIDATE_VALIDITY_CONTRADICTS_AUTHORITY")

        resolved: list[AuthoritySnapshot] = []
        ambiguous_source = False
        for source_id in candidate.source_ids:
            source_snapshots = snapshots_by_source.get(source_id, [])
            if len(source_snapshots) != 1:
                ambiguous_source = ambiguous_source or len(source_snapshots) > 1
                unresolved.append(
                    RelationEdge(
                        source_id=source_id,
                        target_id=candidate.candidate_id,
                        relation=(
                            "AMBIGUOUS_SOURCE"
                            if source_snapshots
                            else "UNRESOLVED_SOURCE"
                        ),
                    )
                )
            else:
                resolved.append(source_snapshots[0])
        if ambiguous_source:
            reasons.append("CONTRADICTORY_AUTHORITY")
        elif unresolved:
            reasons.append("UNRESOLVED_LINEAGE")

        matches = [
            snapshot
            for snapshot in authority.snapshots
            if snapshot.logical_fact_id == candidate.logical_fact_id
            and snapshot.canonical_proposition_sha256
            == candidate.canonical_body_sha256
        ]
        allows = [
            snapshot
            for snapshot in matches
            if snapshot.authoritative
            and snapshot.lifecycle_state is LifecycleState.ACTIVE
        ]
        denies = [
            snapshot
            for snapshot in matches
            if not snapshot.authoritative
            and snapshot.lifecycle_state in _INVALIDATED_STATES
        ]
        indeterminate = [
            snapshot for snapshot in matches if snapshot not in allows and snapshot not in denies
        ]

        if allows and denies or indeterminate or len(allows) > 1 or len(denies) > 1:
            reasons.append("CONTRADICTORY_AUTHORITY")
        elif not matches and candidate.logical_fact_id is not None:
            reasons.append("NO_EXACT_AUTHORITY_MATCH")
        elif matches and not any(
            snapshot.source_event_id in candidate.source_ids for snapshot in matches
        ):
            reasons.append("MATCHING_SOURCE_NOT_IN_LINEAGE")

        content_bindings = [
            binding
            for binding in authority.content_bindings
            if binding.raw_bytes_sha256 == candidate.raw_bytes_sha256
            and binding.canonical_proposition_sha256
            == candidate.canonical_body_sha256
            and binding.logical_fact_id == candidate.logical_fact_id
            and binding.canonicalization_id == candidate.canonicalization_id
        ]
        if (
            candidate.logical_fact_id is not None
            and candidate.canonical_body_sha256 is not None
            and candidate.canonicalization_id is not None
        ):
            if not content_bindings:
                reasons.append("UNRESOLVED_CONTENT_BINDING")
            elif len(content_bindings) > 1:
                reasons.append("AMBIGUOUS_CONTENT_BINDING")
            else:
                binding = content_bindings[0]
                if binding.source_event_id not in candidate.source_ids:
                    reasons.append("CONTENT_BINDING_SOURCE_MISMATCH")
                bound_authority = [
                    snapshot
                    for snapshot in matches
                    if snapshot.source_event_id == binding.source_event_id
                ]
                if len(bound_authority) != 1:
                    reasons.append("CONTENT_BINDING_AUTHORITY_MISMATCH")

        if allows and supplied is not None and candidate.surface is MemorySurface.SOURCE:
            if allows[0].source_record_sha256 != hashlib.sha256(supplied).hexdigest():
                reasons.append("SOURCE_RECORD_SHA256_MISMATCH")
        if allows and any(
            snapshot.lifecycle_state in _INVALIDATED_STATES
            and not _is_superseded_ancestor(
                snapshot,
                allows[0],
                snapshots_by_version,
            )
            for snapshot in resolved
        ):
            reasons.append("MIXED_AUTHORITY_AGGREGATE")

        fail_closed_reasons = {
            "RAW_CONTENT_MISSING",
            "RAW_CONTENT_SHA256_MISMATCH",
            "MISSING_PROPOSITION_IDENTITY",
            "MISSING_LINEAGE",
            "CANDIDATE_VALIDITY_CONTRADICTS_AUTHORITY",
            "UNRESOLVED_LINEAGE",
            "CONTRADICTORY_AUTHORITY",
            "NO_EXACT_AUTHORITY_MATCH",
            "MATCHING_SOURCE_NOT_IN_LINEAGE",
            "SOURCE_RECORD_SHA256_MISMATCH",
            "MIXED_AUTHORITY_AGGREGATE",
            "UNRESOLVED_CONTENT_BINDING",
            "AMBIGUOUS_CONTENT_BINDING",
            "CONTENT_BINDING_SOURCE_MISMATCH",
            "CONTENT_BINDING_AUTHORITY_MISMATCH",
        }
        if fail_closed_reasons.intersection(reasons):
            action = MediatorAction.QUARANTINE
        elif allows:
            action = MediatorAction.ALLOW
            reasons.append("CURRENT_AUTHORITY_EXACT_MATCH")
        elif denies:
            action = MediatorAction.DENY
            reasons.append("EXACT_INVALIDATED_PROPOSITION")
        else:
            action = MediatorAction.QUARANTINE
            reasons.append("INSUFFICIENT_AUTHORITY_EVIDENCE")

        current_witnesses = tuple(
            sorted(
                snapshot.source_event_id
                for snapshot in resolved
                if snapshot.authoritative
                and snapshot.lifecycle_state is LifecycleState.ACTIVE
            )
        )
        stale_witnesses = tuple(
            sorted(
                snapshot.source_event_id
                for snapshot in resolved
                if not snapshot.authoritative
                and snapshot.lifecycle_state in _INVALIDATED_STATES
            )
        )
        decisions.append(
            AuthorityDecision(
                decision=action,
                reason_codes=tuple(dict.fromkeys(reasons)),
                current_witnesses=current_witnesses,
                stale_witnesses=stale_witnesses,
                unresolved_edges=tuple(unresolved),
                input_bundle_sha256=input_hash,
                authority_snapshot_sha256=authority_hash,
                policy_version=policy_version,
                decision_timestamp=evaluation_timestamp,
            )
        )

    decision_tuple = tuple(decisions)
    delivered_ids, delivered_context = _frame_allowed_content(
        candidates,
        content_by_candidate_id,
        decision_tuple,
    )
    return MediationResult(
        decisions=decision_tuple,
        delivered_candidate_ids=delivered_ids,
        delivered_context=delivered_context,
        audit_decisions=tuple(
            decision
            for decision in decision_tuple
            if decision.decision is not MediatorAction.ALLOW
        ),
    )


def evaluate_baseline(
    policy: BaselinePolicy,
    candidates: tuple[CandidateEnvelope, ...],
    authority: AuthorityBundle,
) -> tuple[BaselineDecision, ...]:
    """Apply one deliberately limited baseline to identical candidate inputs."""

    by_source = {
        snapshot.source_event_id: snapshot for snapshot in authority.snapshots
    }
    decisions: list[BaselineDecision] = []
    for candidate in candidates:
        if policy is BaselinePolicy.PASS_THROUGH:
            action = MediatorAction.ALLOW
            reason = "RETRIEVED"
        else:
            sources = [by_source.get(source_id) for source_id in candidate.source_ids]
            if not sources or any(snapshot is None for snapshot in sources):
                action = MediatorAction.QUARANTINE
                reason = "ANCESTRY_UNRESOLVED"
            elif any(
                not snapshot.authoritative
                or snapshot.lifecycle_state is not LifecycleState.ACTIVE
                for snapshot in sources
                if snapshot is not None
            ):
                action = MediatorAction.DENY
                reason = "ANY_NONCURRENT_ANCESTOR"
            else:
                action = MediatorAction.ALLOW
                reason = "ALL_ANCESTORS_CURRENT"
        decisions.append(
            BaselineDecision(
                candidate_id=candidate.candidate_id,
                decision=action,
                reason_code=reason,
            )
        )
    return tuple(decisions)
