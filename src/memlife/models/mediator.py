"""Strict normalized inputs and outputs for the future RQ4 mediator.

These are evidence-boundary contracts only.  They deliberately do not
implement a mediation policy or any semantic/LLM equivalence judgment.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from enum import Enum
from typing import Iterable, Self

from pydantic import Field, field_validator, model_validator

from memlife.models.lifecycle import LifecycleState
from memlife.models.memory import NonEmptyText, StrictModel
from memlife.models.provenance import MemorySurface

MEDIATOR_CONTRACT_SCHEMA_VERSION = "0.1-draft"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class EvidenceClass(str, Enum):
    """Origin class that prevents synthetic challenges becoming observations."""

    PROVIDER_OBSERVED = "PROVIDER_OBSERVED"
    SYNTHETIC_RQ4_CHALLENGE = "SYNTHETIC_RQ4_CHALLENGE"


class MediatorAction(str, Enum):
    """Possible future authority-firewall outcomes."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    QUARANTINE = "QUARANTINE"


class RelationEdge(StrictModel):
    """One directly represented relationship between provider-visible IDs."""

    source_id: NonEmptyText
    target_id: NonEmptyText
    relation: NonEmptyText

    @model_validator(mode="after")
    def endpoints_are_distinct(self) -> Self:
        if self.source_id == self.target_id:
            raise ValueError("relation edge endpoints must be distinct")
        return self


def _validate_sha256(value: str, *, field_name: str) -> str:
    if not _SHA256.fullmatch(value):
        raise ValueError(f"{field_name} must be lowercase SHA-256")
    return value


def _aware(value: datetime, *, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone")
    return value


class CandidateEnvelope(StrictModel):
    """Provider retrieval evidence normalized before authority mediation."""

    contract_schema_version: str = MEDIATOR_CONTRACT_SCHEMA_VERSION
    provider: NonEmptyText
    namespace: NonEmptyText
    candidate_id: NonEmptyText
    retrieval_rank: int = Field(ge=1)
    surface: MemorySurface
    raw_bytes_sha256: NonEmptyText
    canonical_body_sha256: str | None = None
    canonicalization_id: NonEmptyText | None = None
    logical_fact_id: NonEmptyText | None = None
    source_ids: tuple[NonEmptyText, ...] = ()
    relation_edges: tuple[RelationEdge, ...] = ()
    lifecycle_hint: LifecycleState | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    provider_timestamp: datetime | None = None
    retrieval_timestamp: datetime
    evidence_class: EvidenceClass

    @field_validator("raw_bytes_sha256")
    @classmethod
    def raw_hash_is_sha256(cls, value: str) -> str:
        return _validate_sha256(value, field_name="raw_bytes_sha256")

    @field_validator("canonical_body_sha256")
    @classmethod
    def canonical_hash_is_sha256(cls, value: str | None) -> str | None:
        if value is not None:
            return _validate_sha256(value, field_name="canonical_body_sha256")
        return value

    @field_validator(
        "valid_from", "valid_until", "provider_timestamp", "retrieval_timestamp"
    )
    @classmethod
    def timestamps_are_aware(cls, value: datetime | None, info: object) -> datetime | None:
        if value is not None:
            return _aware(value, field_name=getattr(info, "field_name", "timestamp"))
        return value

    @model_validator(mode="after")
    def validate_identity_and_time(self) -> Self:
        if self.contract_schema_version != MEDIATOR_CONTRACT_SCHEMA_VERSION:
            raise ValueError(
                f"contract_schema_version must be {MEDIATOR_CONTRACT_SCHEMA_VERSION!r}"
            )
        if (self.canonical_body_sha256 is None) != (self.canonicalization_id is None):
            raise ValueError(
                "canonical_body_sha256 and canonicalization_id must be populated together"
            )
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            raise ValueError("valid_until must not precede valid_from")
        if len(self.source_ids) != len(set(self.source_ids)):
            raise ValueError("source_ids must be unique")
        return self


class AuthoritySnapshot(StrictModel):
    """Independent authority evidence for one logical fact version."""

    contract_schema_version: str = MEDIATOR_CONTRACT_SCHEMA_VERSION
    logical_fact_id: NonEmptyText
    version_id: NonEmptyText
    source_event_id: NonEmptyText
    lifecycle_state: LifecycleState
    authoritative: bool
    sequence: int = Field(ge=1)
    supersedes: NonEmptyText | None = None
    superseded_by: NonEmptyText | None = None
    canonical_proposition_sha256: NonEmptyText
    source_record_sha256: NonEmptyText

    @field_validator("canonical_proposition_sha256", "source_record_sha256")
    @classmethod
    def identity_hashes_are_sha256(cls, value: str, info: object) -> str:
        return _validate_sha256(value, field_name=getattr(info, "field_name", "sha256"))

    @model_validator(mode="after")
    def validate_snapshot(self) -> Self:
        if self.contract_schema_version != MEDIATOR_CONTRACT_SCHEMA_VERSION:
            raise ValueError(
                f"contract_schema_version must be {MEDIATOR_CONTRACT_SCHEMA_VERSION!r}"
            )
        if self.authoritative and self.lifecycle_state is not LifecycleState.ACTIVE:
            raise ValueError("only ACTIVE snapshots may be authoritative")
        if self.version_id in {self.supersedes, self.superseded_by}:
            raise ValueError("a version cannot supersede itself")
        return self


class AuthorityDecision(StrictModel):
    """Auditable output shape for a future deterministic mediator."""

    contract_schema_version: str = MEDIATOR_CONTRACT_SCHEMA_VERSION
    decision: MediatorAction
    reason_codes: tuple[NonEmptyText, ...] = Field(min_length=1)
    current_witnesses: tuple[NonEmptyText, ...] = ()
    stale_witnesses: tuple[NonEmptyText, ...] = ()
    unresolved_edges: tuple[RelationEdge, ...] = ()
    input_bundle_sha256: NonEmptyText
    authority_snapshot_sha256: NonEmptyText
    policy_version: NonEmptyText
    decision_timestamp: datetime

    @field_validator("input_bundle_sha256", "authority_snapshot_sha256")
    @classmethod
    def decision_hashes_are_sha256(cls, value: str, info: object) -> str:
        return _validate_sha256(value, field_name=getattr(info, "field_name", "sha256"))

    @field_validator("decision_timestamp")
    @classmethod
    def decision_time_is_aware(cls, value: datetime) -> datetime:
        return _aware(value, field_name="decision_timestamp")

    @model_validator(mode="after")
    def validate_decision_evidence(self) -> Self:
        if self.contract_schema_version != MEDIATOR_CONTRACT_SCHEMA_VERSION:
            raise ValueError(
                f"contract_schema_version must be {MEDIATOR_CONTRACT_SCHEMA_VERSION!r}"
            )
        for name, values in (
            ("reason_codes", self.reason_codes),
            ("current_witnesses", self.current_witnesses),
            ("stale_witnesses", self.stale_witnesses),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"{name} must be unique")
        if set(self.current_witnesses) & set(self.stale_witnesses):
            raise ValueError("current and stale witnesses must be disjoint")
        return self


def canonical_contract_sha256(values: Iterable[StrictModel]) -> str:
    """Hash an ordered bundle without inferring, sorting, or rewriting evidence."""

    payload = [value.model_dump(mode="json") for value in values]
    exact = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(exact).hexdigest()


def count_provider_observations(candidates: Iterable[CandidateEnvelope]) -> int:
    """Count empirical provider observations, excluding synthetic challenges."""

    return sum(
        candidate.evidence_class is EvidenceClass.PROVIDER_OBSERVED
        for candidate in candidates
    )
