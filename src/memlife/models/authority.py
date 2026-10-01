"""Experiment-defined authority and directly evidenced exposure models."""

from __future__ import annotations

import hashlib
import json
import re
from enum import Enum
from typing import Iterable, Self

from pydantic import Field, model_validator

from memlife.models.lifecycle import LifecycleState
from memlife.models.memory import NonEmptyText, StrictModel
from memlife.models.provenance import RetrievalCandidate

AUTHORITY_SCHEMA_VERSION = "1.0"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class AuthorityExposureOutcome(str, Enum):
    """Authority classes exposed through directly correlated retrieval records."""

    AUTHORITATIVE_ONLY = "AUTHORITATIVE_ONLY"
    AUTHORITATIVE_AND_NONAUTHORITATIVE = "AUTHORITATIVE_AND_NONAUTHORITATIVE"
    NONAUTHORITATIVE_ONLY = "NONAUTHORITATIVE_ONLY"
    NONE = "NONE"
    UNKNOWN_PROVENANCE = "UNKNOWN_PROVENANCE"


def content_sha256(content: str) -> str:
    """Return stable UTF-8 content identity; never use process-randomized hash()."""

    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class AuthorityLedgerEntry(StrictModel):
    """Final experiment-intent authority for one logical source version."""

    experiment_event_id: NonEmptyText
    logical_fact_id: NonEmptyText
    namespace: NonEmptyText
    sequence: int = Field(ge=1)
    lifecycle_state: LifecycleState
    authoritative: bool
    authority_reason: NonEmptyText
    supersedes: str | None = None
    superseded_by: str | None = None
    source_content_sha256: NonEmptyText

    @model_validator(mode="after")
    def validate_authority_entry(self) -> Self:
        if not _SHA256.fullmatch(self.source_content_sha256):
            raise ValueError("source_content_sha256 must be lowercase SHA-256")
        if self.authoritative and self.lifecycle_state is not LifecycleState.ACTIVE:
            raise ValueError("only ACTIVE ledger entries may be authoritative")
        return self


class AuthorityLedger(StrictModel):
    """Versioned authority ledger representing experiment intent, not retrieval."""

    authority_schema_version: str = AUTHORITY_SCHEMA_VERSION
    entries: tuple[AuthorityLedgerEntry, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_ledger(self) -> Self:
        if self.authority_schema_version != AUTHORITY_SCHEMA_VERSION:
            raise ValueError(
                f"authority_schema_version must be {AUTHORITY_SCHEMA_VERSION!r}"
            )
        event_ids = [entry.experiment_event_id for entry in self.entries]
        fact_ids = [entry.logical_fact_id for entry in self.entries]
        sequences = [entry.sequence for entry in self.entries]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("experiment_event_id values must be unique")
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError("logical_fact_id values must be unique")
        if len(sequences) != len(set(sequences)):
            raise ValueError("ledger sequence values must be unique")
        known_facts = set(fact_ids)
        for entry in self.entries:
            for related in (entry.supersedes, entry.superseded_by):
                if related is not None and related not in known_facts:
                    raise ValueError("supersession links must reference logical_fact_id")
        return self

    def by_event_id(self) -> dict[str, AuthorityLedgerEntry]:
        return {entry.experiment_event_id: entry for entry in self.entries}

    def canonical_json(self) -> str:
        return json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            separators=(",", ": "),
        ) + "\n"


def normalize_authority_exposure(
    candidates: Iterable[RetrievalCandidate],
    ledger: AuthorityLedger,
) -> AuthorityExposureOutcome:
    """Classify exposure using only candidate-to-event links and ledger authority.

    Any visible candidate without complete, direct event correlation makes the
    observation ``UNKNOWN_PROVENANCE``. Text and scores are deliberately unused.
    """

    observed = tuple(candidates)
    if not observed:
        return AuthorityExposureOutcome.NONE

    entries = ledger.by_event_id()
    authority_classes: set[bool] = set()
    for candidate in observed:
        if not candidate.source_event_ids:
            return AuthorityExposureOutcome.UNKNOWN_PROVENANCE
        candidate_entries = [entries.get(event_id) for event_id in candidate.source_event_ids]
        if any(entry is None for entry in candidate_entries):
            return AuthorityExposureOutcome.UNKNOWN_PROVENANCE
        authority_classes.update(
            entry.authoritative for entry in candidate_entries if entry is not None
        )

    if authority_classes == {True}:
        return AuthorityExposureOutcome.AUTHORITATIVE_ONLY
    if authority_classes == {False}:
        return AuthorityExposureOutcome.NONAUTHORITATIVE_ONLY
    return AuthorityExposureOutcome.AUTHORITATIVE_AND_NONAUTHORITATIVE

