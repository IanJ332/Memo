"""Fail-closed Honcho adapter foundation for Phase 08B-0.

This module contains no Honcho SDK import, transport, endpoint, or live
implementation.  It only fixes the local interface that a separately
authorized Phase 08B-1 implementation must satisfy.
"""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Protocol, TypeVar

from pydantic import Field, model_validator

from memlife.adapters.base import (
    AdapterError,
    CapabilitySupport,
    MemoryProviderAdapter,
    ProviderCapability,
    UnsupportedCapabilityError,
)
from memlife.models.lifecycle import LifecycleState
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


class HonchoLiveConfig(StrictModel):
    """Attempt-scoped, non-secret configuration for an authorized live probe."""

    provider_id: Literal["honcho"] = "honcho"
    phase: Literal["08B-1"] = "08B-1"
    base_url: NonEmptyText
    workspace_id: NonEmptyText
    session_id: NonEmptyText
    peer_id: NonEmptyText
    provider_version: Literal["3.2.1"] = "3.2.1"
    upstream_commit: Literal["79cb31645f4efdef626d1bd9316a648adb5da89b"] = (
        "79cb31645f4efdef626d1bd9316a648adb5da89b"
    )


class NativeHonchoResponse(StrictModel):
    """Unparsed HTTP response; body bytes are captured before JSON decoding."""

    status_code: int = Field(ge=100, le=599)
    body: bytes
    content_type: str | None = None


class HonchoTransport(Protocol):
    def request(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, object] | None = None,
    ) -> NativeHonchoResponse: ...


class HonchoHttpTransport:
    """Small stdlib transport that retains exact response bytes."""

    def __init__(self, base_url: str, *, timeout_seconds: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, object] | None = None,
    ) -> NativeHonchoResponse:
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.base_url + "/" + path.lstrip("/"),
            data=data,
            headers=headers,
            method=method.upper(),
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read()
                return NativeHonchoResponse(
                    status_code=response.status,
                    body=body,
                    content_type=response.headers.get("Content-Type"),
                )
        except urllib.error.HTTPError as exc:
            return NativeHonchoResponse(
                status_code=exc.code,
                body=exc.read(),
                content_type=exc.headers.get("Content-Type"),
            )


class DirectoryRawArtifactCapture:
    """Exclusive, attempt-local native response persistence."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.identities: dict[str, RawArtifactIdentity] = {}

    def capture_raw(
        self, *, probe_name: str, native_bytes: bytes
    ) -> RawArtifactIdentity:
        safe_name = "".join(
            character if character.isalnum() or character in "-_" else "_"
            for character in probe_name
        )
        path = self.root / safe_name / "provider-raw-response.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(native_bytes)
        identity = RawArtifactIdentity(
            artifact_path=path.as_posix(),
            sha256=hashlib.sha256(native_bytes).hexdigest(),
            byte_count=len(native_bytes),
        )
        self.identities[probe_name] = identity
        return identity


class HonchoLiveAdapter(MemoryProviderAdapter):
    """Minimum native message write/list adapter for Phase 08B-1."""

    def __init__(
        self,
        config: HonchoLiveConfig,
        *,
        transport: HonchoTransport,
        capture: RawArtifactCapture,
    ) -> None:
        self.config = config
        self.transport = transport
        self.capture = capture

    @property
    def provider_name(self) -> str:
        return "honcho"

    @property
    def provider_version(self) -> str:
        return self.config.provider_version

    @property
    def capabilities(self) -> Mapping[ProviderCapability, CapabilitySupport]:
        return {
            ProviderCapability.RESET_NAMESPACE: CapabilitySupport.UNSUPPORTED,
            ProviderCapability.WRITE: CapabilitySupport.SUPPORTED,
            ProviderCapability.QUERY: CapabilitySupport.SUPPORTED,
            ProviderCapability.UPDATE_OR_SUPERSEDE: CapabilitySupport.UNSUPPORTED,
            ProviderCapability.DELETE_OR_INVALIDATE: CapabilitySupport.UNSUPPORTED,
            ProviderCapability.LIST_OR_INSPECT: CapabilitySupport.SUPPORTED,
            ProviderCapability.RESTART: CapabilitySupport.UNSUPPORTED,
        }

    def configuration_report(self) -> Mapping[str, object]:
        return self.config.model_dump(mode="json")

    def version_report(self) -> Mapping[str, object]:
        return {
            "provider": "honcho",
            "version": self.config.provider_version,
            "commit": self.config.upstream_commit,
        }

    def _session_path(self, suffix: str = "") -> str:
        base = (
            f"v3/workspaces/{self.config.workspace_id}/sessions/"
            f"{self.config.session_id}/messages"
        )
        return base + suffix

    def _workspace_path(self, suffix: str = "") -> str:
        return f"v3/workspaces/{self.config.workspace_id}" + suffix

    @staticmethod
    def _json(response: NativeHonchoResponse, *, expected: set[int]) -> Any:
        if response.status_code not in expected:
            detail = response.body.decode("utf-8", errors="replace")[-2000:]
            raise AdapterError(
                f"Honcho HTTP {response.status_code}; response={detail}"
            )
        try:
            return json.loads(response.body)
        except json.JSONDecodeError as exc:
            raise AdapterError("Honcho returned non-JSON response bytes") from exc

    def _normalize_message(
        self,
        item: Mapping[str, Any],
        identity: RawArtifactIdentity,
        *,
        rank: int | None = None,
    ) -> MemoryRecord:
        provider_id = str(item.get("id") or "")
        content = str(item.get("content") or "")
        if not provider_id or not content:
            raise AdapterError("Honcho message omitted required native fields")
        return MemoryRecord(
            memory_id=provider_id,
            namespace=self.config.session_id,
            content=content,
            metadata={
                "provider_native_id": provider_id,
                "provider_peer_id": item.get("peer_id"),
                "provider_created_at": item.get("created_at"),
                "retrieval_rank": rank,
                "raw_artifact": identity.model_dump(mode="json"),
            },
            state=LifecycleState.ACTIVE,
            revision=1,
        )

    def reset_namespace(self, namespace: str) -> None:
        raise UnsupportedCapabilityError("Honcho namespace reset is not used in Phase 08B-1")

    def write(self, command: WriteCommand) -> MemoryRecord:
        if command.namespace != self.config.session_id:
            raise AdapterError("write namespace differs from isolated Honcho session")
        response = self.transport.request(
            "POST",
            self._session_path(),
            payload={
                "messages": [
                    {
                        "content": command.content,
                        "peer_id": self.config.peer_id,
                        "metadata": command.metadata,
                    }
                ]
            },
        )

        def normalize(raw: bytes, identity: RawArtifactIdentity) -> MemoryRecord:
            payload = self._json(response, expected={201})
            if not isinstance(payload, list) or len(payload) != 1:
                raise AdapterError("Honcho create response did not contain one message")
            return self._normalize_message(payload[0], identity)

        return capture_before_normalization(
            probe_name="honcho_capability_create_write_v1",
            native_bytes=response.body,
            capture=self.capture,
            normalize=normalize,
        )

    def query(self, command: QueryCommand) -> tuple[MemoryRecord, ...]:
        if command.namespace != self.config.session_id:
            raise AdapterError("query namespace differs from isolated Honcho session")
        if not command.query.strip():
            raise AdapterError("native Honcho retrieval requires a non-empty search query")
        response = self.transport.request(
            "POST",
            self._workspace_path("/search"),
            payload={
                "query": command.query,
                "filters": {"session_id": self.config.session_id},
                "limit": command.limit,
            },
        )

        def normalize(
            raw: bytes, identity: RawArtifactIdentity
        ) -> tuple[MemoryRecord, ...]:
            payload = self._json(response, expected={200})
            if not isinstance(payload, list):
                raise AdapterError("Honcho workspace search response was not a list")
            return tuple(
                self._normalize_message(item, identity, rank=index)
                for index, item in enumerate(payload, start=1)
            )

        return capture_before_normalization(
            probe_name="honcho_capability_retrieval_v1",
            native_bytes=response.body,
            capture=self.capture,
            normalize=normalize,
        )

    def update_or_supersede(self, command: SupersedeCommand) -> MemoryRecord:
        raise UnsupportedCapabilityError("Honcho exposes no native message supersede")

    def delete_or_invalidate(self, command: DeleteCommand) -> MemoryRecord:
        raise UnsupportedCapabilityError(
            "Phase 08B-1 does not conflate hard delete with revoke/invalidate"
        )

    def list_or_inspect(
        self,
        namespace: str,
        *,
        include_non_active: bool = True,
    ) -> tuple[MemoryRecord, ...]:
        if namespace != self.config.session_id:
            raise AdapterError("inspection namespace differs from isolated Honcho session")
        response = self.transport.request(
            "POST",
            self._session_path("/list") + "?page=1&size=100",
            payload={"filters": {}},
        )

        def normalize(
            raw: bytes, identity: RawArtifactIdentity
        ) -> tuple[MemoryRecord, ...]:
            payload = self._json(response, expected={200})
            items = payload.get("items") if isinstance(payload, Mapping) else None
            if not isinstance(items, list):
                raise AdapterError("Honcho message-list response omitted items")
            return tuple(
                self._normalize_message(item, identity)
                for item in items
            )

        return capture_before_normalization(
            probe_name="honcho_capability_raw_inspection_v1",
            native_bytes=response.body,
            capture=self.capture,
            normalize=normalize,
        )

    def restart(self) -> None:
        raise UnsupportedCapabilityError("service restart is owned by the live controller")

    def trigger_native_rederivation(self, namespace: str) -> None:
        raise UnsupportedCapabilityError(
            "Honcho rederivation is probed through its native schedule endpoint"
        )

    def wait_for_quiescence(self, operation_id: str) -> None:
        raise UnsupportedCapabilityError(
            "quiescence is evaluated from bounded queue-status observations"
        )
