"""Provider-independent commands and normalized memory records."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from memlife.models.lifecycle import LifecycleState

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class StrictModel(BaseModel):
    """Immutable, closed input model used at adapter boundaries."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class WriteCommand(StrictModel):
    namespace: NonEmptyText
    content: NonEmptyText
    metadata: dict[str, Any] = Field(default_factory=dict)


class QueryCommand(StrictModel):
    namespace: NonEmptyText
    query: str = ""
    limit: int = Field(default=10, ge=1)
    include_states: frozenset[LifecycleState] = Field(
        default_factory=lambda: frozenset({LifecycleState.ACTIVE})
    )


class SupersedeCommand(StrictModel):
    namespace: NonEmptyText
    memory_id: NonEmptyText
    content: NonEmptyText
    metadata: dict[str, Any] | None = None


class DeleteCommand(StrictModel):
    namespace: NonEmptyText
    memory_id: NonEmptyText
    disposition: LifecycleState = LifecycleState.DELETED

    @field_validator("disposition")
    @classmethod
    def validate_disposition(cls, value: LifecycleState) -> LifecycleState:
        if value not in {LifecycleState.DELETED, LifecycleState.REVOKED}:
            raise ValueError("disposition must be deleted or revoked")
        return value


class MemoryRecord(StrictModel):
    memory_id: NonEmptyText
    namespace: NonEmptyText
    content: NonEmptyText
    metadata: dict[str, Any] = Field(default_factory=dict)
    state: LifecycleState
    revision: int = Field(ge=1)
    supersedes_id: str | None = None
    superseded_by_id: str | None = None
