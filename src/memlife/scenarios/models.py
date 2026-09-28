"""Provider-independent lifecycle scenario definitions."""

from __future__ import annotations

from enum import Enum
from typing import Self

from pydantic import Field, model_validator

from memlife.models.lifecycle import LifecycleState
from memlife.models.memory import NonEmptyText, StrictModel

BENCHMARK_VERSION = "0.1"


class LifecycleEvent(str, Enum):
    """Benchmark intent; adapters may realize an event differently."""

    WRITE = "WRITE"
    UPDATE = "UPDATE"
    SUPERSEDE = "SUPERSEDE"
    REVOKE = "REVOKE"
    DELETE = "DELETE"
    RESTART = "RESTART"
    QUERY = "QUERY"
    INSPECT = "INSPECT"


class ScenarioQuery(StrictModel):
    """A deterministic query and the facts it is intended to distinguish."""

    query_id: NonEmptyText
    text: NonEmptyText
    current_facts: tuple[NonEmptyText, ...] = ()
    stale_facts: tuple[NonEmptyText, ...] = ()

    @model_validator(mode="after")
    def facts_do_not_overlap(self) -> Self:
        overlap = set(self.current_facts) & set(self.stale_facts)
        if overlap:
            raise ValueError("query current_facts and stale_facts must not overlap")
        return self


class LifecycleStep(StrictModel):
    """One ordered lifecycle intent in a scenario."""

    event: LifecycleEvent
    memory_key: NonEmptyText | None = None
    target_key: NonEmptyText | None = None
    content: NonEmptyText | None = None
    query_id: NonEmptyText | None = None
    disposition: LifecycleState | None = None

    @model_validator(mode="after")
    def fields_match_event(self) -> Self:
        if self.event is LifecycleEvent.WRITE:
            if self.memory_key is None or self.content is None:
                raise ValueError("WRITE requires memory_key and content")
        elif self.event in {LifecycleEvent.UPDATE, LifecycleEvent.SUPERSEDE}:
            if (
                self.memory_key is None
                or self.target_key is None
                or self.content is None
            ):
                raise ValueError(
                    f"{self.event.value} requires memory_key, target_key, and content"
                )
        elif self.event in {LifecycleEvent.REVOKE, LifecycleEvent.DELETE}:
            if self.target_key is None:
                raise ValueError(f"{self.event.value} requires target_key")
            expected = (
                LifecycleState.REVOKED
                if self.event is LifecycleEvent.REVOKE
                else LifecycleState.DELETED
            )
            if self.disposition not in {None, expected}:
                raise ValueError(
                    f"{self.event.value} disposition must be {expected.value}"
                )
        elif self.event is LifecycleEvent.QUERY and self.query_id is None:
            raise ValueError("QUERY requires query_id")
        return self


class LifecycleScenario(StrictModel):
    """Versioned lifecycle intent, independent of provider mechanics."""

    scenario_id: NonEmptyText
    description: NonEmptyText
    namespace: NonEmptyText
    initial_memory: tuple[NonEmptyText, ...] = ()
    lifecycle_steps: tuple[LifecycleStep, ...] = Field(min_length=1)
    queries: tuple[ScenarioQuery, ...] = ()
    expected_authoritative_state: tuple[NonEmptyText, ...]
    tags: frozenset[NonEmptyText] = frozenset()
    benchmark_version: str = BENCHMARK_VERSION

    @model_validator(mode="after")
    def validate_references_and_order(self) -> Self:
        if self.benchmark_version != BENCHMARK_VERSION:
            raise ValueError(
                f"scenario benchmark_version must be {BENCHMARK_VERSION!r}"
            )

        query_ids = [query.query_id for query in self.queries]
        if len(query_ids) != len(set(query_ids)):
            raise ValueError("query_id values must be unique")
        queries = set(query_ids)

        declared: set[str] = set()
        used_queries: set[str] = set()
        for index, step in enumerate(self.lifecycle_steps):
            if step.target_key is not None and step.target_key not in declared:
                raise ValueError(
                    f"step {index} references undeclared target_key "
                    f"{step.target_key!r}"
                )
            if step.memory_key is not None:
                if step.memory_key in declared:
                    raise ValueError(
                        f"step {index} redeclares memory_key {step.memory_key!r}"
                    )
                declared.add(step.memory_key)
            if step.event is LifecycleEvent.QUERY:
                if step.query_id not in queries:
                    raise ValueError(
                        f"step {index} references unknown query_id {step.query_id!r}"
                    )
                used_queries.add(str(step.query_id))

        unused = queries - used_queries
        if unused:
            raise ValueError(f"queries are not used by lifecycle_steps: {sorted(unused)}")
        return self

    def query(self, query_id: str) -> ScenarioQuery:
        """Resolve one already-validated query identifier."""

        return next(query for query in self.queries if query.query_id == query_id)
