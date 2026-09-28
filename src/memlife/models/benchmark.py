"""Structured observations emitted by the lifecycle benchmark."""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Any, Self

from pydantic import Field, field_validator, model_validator

from memlife.models.memory import NonEmptyText, StrictModel
from memlife.models.safety import reject_sensitive_keys
from memlife.scenarios.models import BENCHMARK_VERSION, LifecycleEvent


class OperationStatus(str, Enum):
    SUCCESS = "SUCCESS"
    UNSUPPORTED = "UNSUPPORTED"
    ERROR = "ERROR"


class NormalizedOutcome(str, Enum):
    CURRENT_ONLY = "CURRENT_ONLY"
    CURRENT_AND_STALE = "CURRENT_AND_STALE"
    STALE_ONLY = "STALE_ONLY"
    ABSENT = "ABSENT"
    UNSUPPORTED = "UNSUPPORTED"
    ERROR = "ERROR"


class BenchmarkResult(StrictModel):
    """One provider observation for one ordered scenario step."""

    benchmark_version: str = BENCHMARK_VERSION
    scenario_id: NonEmptyText
    provider: NonEmptyText
    provider_version: str | None = None
    namespace: NonEmptyText
    lifecycle_mode: str = "native"
    step_index: int = Field(ge=0)
    intended_event: LifecycleEvent
    native_operation: NonEmptyText
    operation_status: OperationStatus
    normalized_outcome: NormalizedOutcome | None = None
    memory_ids_before: tuple[str, ...] = ()
    memory_ids_after: tuple[str, ...] = ()
    query_text: str | None = None
    retrieved_current: tuple[str, ...] = ()
    retrieved_stale: tuple[str, ...] = ()
    observed_records: tuple[str, ...] = ()
    expected_authoritative_state: tuple[str, ...] = ()
    current_state_correct: bool | None = None
    stale_state_visible: bool | None = None
    history_visible: bool | None = None
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
    unsupported_reason: str | None = None
    latency_ms: float = Field(ge=0)
    error: str | None = None
    timestamp: datetime

    @field_validator("provider_metadata")
    @classmethod
    def metadata_has_no_sensitive_keys(cls, value: dict[str, Any]) -> dict[str, Any]:
        return reject_sensitive_keys(value, field_name="provider_metadata")

    @model_validator(mode="after")
    def status_fields_agree(self) -> Self:
        if self.benchmark_version != BENCHMARK_VERSION:
            raise ValueError(
                f"result benchmark_version must be {BENCHMARK_VERSION!r}"
            )
        if self.operation_status is OperationStatus.UNSUPPORTED:
            if not self.unsupported_reason:
                raise ValueError("UNSUPPORTED results require unsupported_reason")
            if self.normalized_outcome is not NormalizedOutcome.UNSUPPORTED:
                raise ValueError("UNSUPPORTED status requires UNSUPPORTED outcome")
        if self.operation_status is OperationStatus.ERROR:
            if not self.error:
                raise ValueError("ERROR results require error")
            if self.normalized_outcome is not NormalizedOutcome.ERROR:
                raise ValueError("ERROR status requires ERROR outcome")
        return self


def serialize_results(results: tuple[BenchmarkResult, ...]) -> str:
    """Serialize results as stable, UTF-8-safe JSON text."""

    payload = [result.model_dump(mode="json") for result in results]
    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        separators=(",", ": "),
    ) + "\n"


def deserialize_results(value: str) -> tuple[BenchmarkResult, ...]:
    """Parse lifecycle result JSON back into closed models."""

    payload = json.loads(value)
    if not isinstance(payload, list):
        raise ValueError("benchmark result document must be a JSON array")
    return tuple(BenchmarkResult.model_validate(item) for item in payload)
