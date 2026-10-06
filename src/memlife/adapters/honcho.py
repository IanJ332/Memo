"""Fail-closed Honcho adapter foundation for Phase 08B-0.

This module contains no Honcho SDK import, transport, endpoint, or live
implementation.  It only fixes the local interface that a separately
authorized Phase 08B-1 implementation must satisfy.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from enum import Enum
from typing import Literal, Protocol, TypeVar

from pydantic import Field, model_validator

from memlife.adapters.base import (
    AdapterError,
    CapabilitySupport,
    MemoryProviderAdapter,
    ProviderCapability,
)
from memlife.models.memory import (
    DeleteCommand,
    MemoryRecord,
    NonEmptyText,
    QueryCommand,
    StrictModel,
    SupersedeCommand,
    WriteCommand,
)


class LiveProviderExecutionNotAuthorized(AdapterError):
    """Raised before any Honcho live-facing operation can run."""


class HonchoAdapterConfig(StrictModel):
    """Non-secret Phase 08B-0 configuration; live authorization is impossible."""

    provider_id: Literal["honcho"] = "honcho"
    phase: Literal["08B-0"] = "08B-0"
    live_execution_authorized: Literal[False] = False
    network_access_authorized: Literal[False] = False
    provider_sdk_installed: Literal[False] = False
    configuration_source: Literal["FUTURE_PHASE08B1_MANIFEST"] = (
        "FUTURE_PHASE08B1_MANIFEST"
    )


class RawArtifactIdentity(StrictModel):
    """Identity returned only after exact native bytes have been persisted."""

    artifact_path: NonEmptyText
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    byte_count: int = Field(ge=0)


class RawArtifactCapture(Protocol):
    """Future immutable artifact hook invoked before normalization."""

    def capture_raw(
        self, *, probe_name: str, native_bytes: bytes
    ) -> RawArtifactIdentity: ...


class NormalizedHonchoRecord(StrictModel):
    """Normalized record with deliberately separate identity layers."""

    provider_native_id: NonEmptyText
    canonical_proposition_id: NonEmptyText | None = None
    logical_fact_id: NonEmptyText | None = None
    raw_artifact: RawArtifactIdentity
    retrieval_rank: int | None = Field(default=None, ge=1)


NormalizedT = TypeVar("NormalizedT")


def capture_before_normalization(
    *,
    probe_name: str,
    native_bytes: bytes,
    capture: RawArtifactCapture,
    normalize: Callable[[bytes, RawArtifactIdentity], NormalizedT],
) -> NormalizedT:
    """Persist and verify exact native bytes before calling a normalizer."""

    identity = capture.capture_raw(
        probe_name=probe_name,
        native_bytes=native_bytes,
    )
    expected_sha256 = hashlib.sha256(native_bytes).hexdigest()
    if identity.sha256 != expected_sha256:
        raise ValueError("raw capture SHA-256 does not match native response bytes")
    if identity.byte_count != len(native_bytes):
        raise ValueError("raw capture byte count does not match native response bytes")
    return normalize(native_bytes, identity)


class QuiescenceCriterion(str, Enum):
    PROVIDER_JOB_COMPLETED = "PROVIDER_JOB_COMPLETED"
    STABLE_RETRIEVAL_ACROSS_BOUNDED_CHECKS = (
        "STABLE_RETRIEVAL_ACROSS_BOUNDED_CHECKS"
    )
    EMPTY_PENDING_QUEUE = "EMPTY_PENDING_QUEUE"
    EXPLICIT_PROVIDER_COMPLETION_SIGNAL = "EXPLICIT_PROVIDER_COMPLETION_SIGNAL"


class QuiescenceContract(StrictModel):
    """Observable, bounded completion contract; elapsed sleep is never success."""

    allowed_criteria: tuple[QuiescenceCriterion, ...] = tuple(QuiescenceCriterion)
    maximum_checks: int = Field(default=20, ge=2)
    stable_retrieval_checks_required: int = Field(default=2, ge=2)
    sleep_only_success_allowed: Literal[False] = False

    @model_validator(mode="after")
    def criteria_are_complete_and_unique(self) -> "QuiescenceContract":
        if set(self.allowed_criteria) != set(QuiescenceCriterion):
            raise ValueError("quiescence criteria must match the predeclared set")
        if len(self.allowed_criteria) != len(set(self.allowed_criteria)):
            raise ValueError("quiescence criteria must be unique")
        if self.stable_retrieval_checks_required > self.maximum_checks:
            raise ValueError("stable checks cannot exceed the bounded maximum")
        return self


class HonchoAdapterSkeleton(MemoryProviderAdapter):
    """Phase 08B-0 shape only; every provider-facing path fails closed."""

    def __init__(self, config: HonchoAdapterConfig | None = None) -> None:
        self.config = config or HonchoAdapterConfig()
        self.quiescence_contract = QuiescenceContract()

    @property
    def provider_name(self) -> str:
        return "honcho"

    @property
    def provider_version(self) -> None:
        return None

    @property
    def capabilities(self) -> Mapping[ProviderCapability, CapabilitySupport]:
        self._raise_not_authorized("capability discovery")

    def configuration_report(self) -> Mapping[str, object]:
        """Return only the local, non-secret preflight configuration."""

        return self.config.model_dump(mode="json")

    def version_report(self) -> Mapping[str, object]:
        """Do not invent a version before provider-observed pinning."""

        return {
            "provider": "honcho",
            "version": None,
            "commit": None,
            "status": "UNKNOWN_UNTIL_AUTHORIZED_LIVE_PROBE",
        }

    @staticmethod
    def _raise_not_authorized(operation: str) -> None:
        raise LiveProviderExecutionNotAuthorized(
            f"Honcho {operation} is not authorized in Phase 08B-0"
        )

    def reset_namespace(self, namespace: str) -> None:
        self._raise_not_authorized("namespace reset")

    def write(self, command: WriteCommand) -> MemoryRecord:
        self._raise_not_authorized("create/write")

    def query(self, command: QueryCommand) -> tuple[MemoryRecord, ...]:
        self._raise_not_authorized("retrieval")

    def update_or_supersede(self, command: SupersedeCommand) -> MemoryRecord:
        self._raise_not_authorized("update/supersede")

    def delete_or_invalidate(self, command: DeleteCommand) -> MemoryRecord:
        self._raise_not_authorized("delete/revoke")

    def list_or_inspect(
        self,
        namespace: str,
        *,
        include_non_active: bool = True,
    ) -> tuple[MemoryRecord, ...]:
        self._raise_not_authorized("raw inspection")

    def restart(self) -> None:
        self._raise_not_authorized("restart/reconstruction")

    def trigger_native_rederivation(self, namespace: str) -> None:
        self._raise_not_authorized("native rederivation/consolidation")

    def wait_for_quiescence(self, operation_id: str) -> None:
        self._raise_not_authorized("quiescence observation")
