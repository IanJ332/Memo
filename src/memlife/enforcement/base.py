"""Stable provider-independent hook for inspecting retrieval candidates."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import Field, field_validator

from memlife.models.memory import NonEmptyText, StrictModel
from memlife.models.provenance import EnforcementDecision, RetrievalCandidate
from memlife.models.safety import reject_sensitive_keys


class EnforcementContext(StrictModel):
    """Explicit identifiers and sanitized context for one filter invocation."""

    experiment_id: NonEmptyText
    scenario_id: NonEmptyText
    retrieval_event_id: NonEmptyText
    enforcement_event_id: NonEmptyText
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def metadata_has_no_sensitive_keys(cls, value: dict[str, Any]) -> dict[str, Any]:
        return reject_sensitive_keys(value, field_name="metadata")


class CandidateFilter(ABC):
    """Pre-LLM enforcement boundary; implementations must be deterministic here."""

    @abstractmethod
    def inspect_candidates(
        self,
        candidates: tuple[RetrievalCandidate, ...],
        context: EnforcementContext,
    ) -> tuple[EnforcementDecision, ...]:
        """Return exactly one decision for each candidate."""
