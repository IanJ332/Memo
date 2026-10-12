"""Hindsight 0.10.1 service adapter for Phase 04 lifecycle experiments."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from memlife.adapters.base import (
    AdapterError,
    CapabilitySupport,
    MemoryNotFoundError,
    MemoryProviderAdapter,
    ProviderCapability,
    UnsupportedCapabilityError,
)
from memlife.models.lifecycle import LifecycleState
from memlife.models.memory import DeleteCommand, MemoryRecord, QueryCommand
from memlife.models.memory import SupersedeCommand, WriteCommand
from memlife.models.provenance import MemorySurface, ProvenanceStatus
from memlife.runner.phase08d3 import CandidateEvidence, HttpExchangeCapture, capture_candidates

HINDSIGHT_VERSION = "0.10.1"
HINDSIGHT_UPSTREAM_COMMIT = "f8950b0c07d9e34c76493dba802bb309f0ce60fd"
HINDSIGHT_BASE_URL_ENV = "MEMLIFE_HINDSIGHT_BASE_URL"
DEFAULT_BASE_URL = "http://127.0.0.1:8888"
INTERNAL_LLM_PROVIDER = "openai"
INTERNAL_LLM_MODEL = "gpt-oss-120b"
EMBEDDINGS_PROVIDER = "onnx"
EMBEDDINGS_MODEL = "intfloat/multilingual-e5-small"
EMBEDDINGS_DIMENSIONS = 384
RERANKER_PROVIDER = "rrf"


def phase04_manifest_configuration() -> dict[str, Any]:
    """Return the frozen, non-secret Phase 04 provider configuration."""

    return {
        "phase": "04",
        "provider": "hindsight",
        "provider_version": HINDSIGHT_VERSION,
        "upstream_commit": HINDSIGHT_UPSTREAM_COMMIT,
        "deployment_mode": "bare-metal self-hosted API service",
        "service_package": "hindsight-api-slim[embedded-db,local-onnx]",
        "client_package": "not installed; urllib.request REST transport",
        "runtime_isolation": "dedicated provider venv over loopback HTTP",
        "storage_backend": "embedded pg0/PostgreSQL with pgvector",
        "storage_path_class": "persistent-volume/providers/hindsight/pg0",
        "internal_llm_provider": INTERNAL_LLM_PROVIDER,
        "internal_llm_model": INTERNAL_LLM_MODEL,
        "internal_llm_endpoint_class": "course-authorized OpenAI-compatible hosted endpoint",
        "internal_llm_api_key_class": "course placeholder",
        "embedding_provider": EMBEDDINGS_PROVIDER,
        "embedding_model": EMBEDDINGS_MODEL,
        "embedding_dimensions": EMBEDDINGS_DIMENSIONS,
        "embedding_cache_path_class": "persistent-volume/model_cache/hindsight",
        "reranker_provider": RERANKER_PROVIDER,
        "retain_mode": "synchronous",
        "derived_processing": "status-polled asynchronous consolidation",
        "retrieval_primitive": "recall(world, experience, observation)",
        "reflect_used": False,
    }


class HindsightTransport(Protocol):
    """Small transport seam used by real HTTP and deterministic unit tests."""

    def request(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, Any] | None = None,
        payload: Any | None = None,
    ) -> Any: ...


class HindsightHTTPError(AdapterError):
    """HTTP response error with the provider status preserved."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"Hindsight HTTP {status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


@dataclass
class UrllibHindsightTransport:
    """Dependency-free JSON transport for the self-hosted REST service."""

    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 120.0
    capture: HttpExchangeCapture | None = None
    last_exchange: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        if not self.base_url.startswith(("http://", "https://")):
            raise ValueError("Hindsight base URL must use http or https")

    @staticmethod
    def _query_items(query: Mapping[str, Any]) -> list[tuple[str, str]]:
        items: list[tuple[str, str]] = []
        for key, value in query.items():
            if value is None:
                continue
            values = value if isinstance(value, (list, tuple)) else (value,)
            items.extend((str(key), str(item)) for item in values)
        return items

    def request(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, Any] | None = None,
        payload: Any | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urlencode(self._query_items(query))}"
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            url,
            data=body,
            method=method.upper(),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        status_code = 0
        headers: Mapping[str, str] | None = None
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read()
                status_code = int(response.status)
                headers = {str(key): str(value) for key, value in response.headers.items()}
        except HTTPError as exc:
            raw = exc.read()
            if self.capture is not None:
                self.last_exchange = self.capture.capture(
                    method=method, path=path, request_body=body, response_body=raw,
                    status_code=exc.code, response_headers={str(key): str(value) for key, value in exc.headers.items()} if exc.headers else None,
                    request_id=exc.headers.get("X-Request-ID") if exc.headers else None,
                )
            decoded = raw.decode("utf-8", errors="replace")
            try:
                parsed = json.loads(decoded)
                detail = str(parsed.get("detail", parsed))
            except json.JSONDecodeError:
                detail = decoded or str(exc.reason)
            raise HindsightHTTPError(exc.code, detail) from exc
        except (URLError, TimeoutError) as exc:
            raise AdapterError(f"Hindsight service request failed: {exc}") from exc
        if self.capture is not None:
            self.last_exchange = self.capture.capture(
                method=method, path=path, request_body=body, response_body=raw,
                status_code=status_code, response_headers=headers,
                request_id=headers.get("X-Request-ID") if headers else None,
            )
        if not raw:
            return None
        return json.loads(raw.decode("utf-8"))


class HindsightMemoryAdapter(MemoryProviderAdapter):
    """Map the MemLife contract to public Hindsight 0.10.1 service APIs.

    Each normalized write is retained as one uniquely identified Hindsight
    document. The adapter returns the single source fact extracted from that
    document. Ambiguous extraction fails instead of manufacturing an identity.
    """

    def __init__(
        self,
        transport: HindsightTransport,
        *,
        restart_callback: Callable[[], None] | None = None,
        quiescence_timeout_seconds: float = 300.0,
        poll_interval_seconds: float = 0.25,
        candidate_evidence_sink: Callable[[tuple[CandidateEvidence, ...]], None] | None = None,
    ) -> None:
        if quiescence_timeout_seconds <= 0:
            raise ValueError("quiescence timeout must be positive")
        if poll_interval_seconds <= 0:
            raise ValueError("poll interval must be positive")
        self.transport = transport
        self._restart_callback = restart_callback
        self.quiescence_timeout_seconds = quiescence_timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self._candidate_evidence_sink = candidate_evidence_sink
        self._last_operation: dict[str, Any] = {}

    @classmethod
    def from_environment(
        cls,
        *,
        restart_callback: Callable[[], None] | None = None,
    ) -> "HindsightMemoryAdapter":
        base_url = os.environ.get(HINDSIGHT_BASE_URL_ENV, DEFAULT_BASE_URL)
        return cls(
            UrllibHindsightTransport(base_url),
            restart_callback=restart_callback,
        )

    @property
    def provider_name(self) -> str:
        return "hindsight-self-hosted-0.10.1"

    @property
    def provider_version(self) -> str:
        return HINDSIGHT_VERSION

    @property
    def capabilities(self) -> Mapping[ProviderCapability, CapabilitySupport]:
        values = {
            capability: CapabilitySupport.SUPPORTED
            for capability in ProviderCapability
        }
        if self._restart_callback is None:
            values[ProviderCapability.RESTART] = CapabilitySupport.UNSUPPORTED
        return values

    def native_operation_for(self, intended_event: str) -> str:
        return {
            "WRITE": "POST /memories (retain, synchronous)",
            "UPDATE": "PATCH /memories/{id} (native curation edit)",
            "SUPERSEDE": "PATCH /memories/{id} (same-ID edit; no supersession edge)",
            "REVOKE": "PATCH /memories/{id} state=invalidated",
            "DELETE": "DELETE /documents/{document_id}",
            "RESTART": "stop/start run-owned API; preserve persistent pg0 state",
            "QUERY": "POST /memories/recall (world + experience only)",
            "INSPECT": "GET /memories/list (valid + invalidated, all fact types)",
        }.get(intended_event, super().native_operation_for(intended_event))

    def benchmark_metadata(self) -> Mapping[str, Any]:
        return {
            "deployment_mode": "self-hosted service",
            "retrieval_surface": "recall world+experience+observation",
            "update_semantics": "native same-ID curation edit",
            "supersession_semantics": "no explicit supersession edge",
            "history_semantics": "observation history only",
            "embedding_provider": EMBEDDINGS_PROVIDER,
            "embedding_model": EMBEDDINGS_MODEL,
            "reranker_provider": RERANKER_PROVIDER,
            **self._last_operation,
        }

    def manifest_configuration(self) -> dict[str, Any]:
        return phase04_manifest_configuration()

    @property
    def trace_provenance_status(self) -> ProvenanceStatus:
        # The generic lifecycle trace must not mistake a same-ID edit for a
        # supersession edge. Observation lineage is handled per record below.
        return ProvenanceStatus.UNKNOWN

    @property
    def trace_source_surface(self) -> MemorySurface:
        return MemorySurface.SOURCE

    def trace_surface_for(self, record: MemoryRecord) -> MemorySurface:
        value = record.metadata.get("hindsight_surface")
        try:
            return MemorySurface(str(value))
        except ValueError:
            return MemorySurface.UNKNOWN

    def trace_provenance_status_for(
        self, record: MemoryRecord
    ) -> ProvenanceStatus:
        sources = record.metadata.get("hindsight_source_memory_ids")
        if (
            record.metadata.get("hindsight_fact_type") == "observation"
            and isinstance(sources, list)
            and bool(sources)
        ):
            return ProvenanceStatus.KNOWN
        return ProvenanceStatus.UNKNOWN

    def trace_source_provider_ids_for(
        self, record: MemoryRecord
    ) -> tuple[str, ...]:
        sources = record.metadata.get("hindsight_source_memory_ids", [])
        if not isinstance(sources, list):
            return ()
        return tuple(str(value) for value in sources)

    def trace_metadata_for(self, record: MemoryRecord) -> Mapping[str, Any]:
        return {
            "provider_fact_type": record.metadata.get(
                "hindsight_fact_type", "unknown"
            ),
            "provider_surface": record.metadata.get(
                "hindsight_surface", MemorySurface.UNKNOWN.value
            ),
            "provider_state": record.metadata.get(
                "hindsight_native_state", "unknown"
            ),
            "provider_document_id": record.metadata.get("hindsight_document_id"),
            "provider_source_count": len(
                record.metadata.get("hindsight_source_memory_ids", [])
            ),
        }

    @staticmethod
    def _bank_path(namespace: str) -> str:
        value = namespace.strip()
        if not value:
            raise ValueError("namespace must not be blank")
        return quote(value, safe="")

    @staticmethod
    def _surface(fact_type: str) -> MemorySurface:
        if fact_type in {"world", "experience"}:
            return MemorySurface.SOURCE
        if fact_type == "observation":
            return MemorySurface.DERIVED
        return MemorySurface.UNKNOWN

    @classmethod
    def _normalized_record(
        cls,
        namespace: str,
        native: Mapping[str, Any],
        *,
        deleted: bool = False,
    ) -> MemoryRecord:
        memory_id = str(native.get("id") or "").strip()
        content = str(native.get("text") or "").strip()
        if not memory_id or not content:
            raise AdapterError(f"unexpected Hindsight memory shape: {native!r}")
        fact_type = str(native.get("fact_type") or native.get("type") or "unknown")
        native_state = str(native.get("state") or "valid")
        if deleted:
            state = LifecycleState.DELETED
        elif native_state == "invalidated":
            state = LifecycleState.REVOKED
        else:
            state = LifecycleState.ACTIVE
        source_ids = native.get("source_memory_ids")
        if source_ids is None:
            source_ids = native.get("source_fact_ids")
        source_ids = [str(value) for value in (source_ids or [])]
        metadata = {
            "hindsight_fact_type": fact_type,
            "hindsight_surface": cls._surface(fact_type).value,
            "hindsight_native_state": native_state,
            "hindsight_document_id": native.get("document_id"),
            "hindsight_chunk_id": native.get("chunk_id"),
            "hindsight_source_memory_ids": source_ids,
            "hindsight_invalidation_reason": native.get("invalidation_reason"),
            "hindsight_invalidated_at": native.get("invalidated_at"),
            "hindsight_edited_at": native.get("edited_at"),
            "hindsight_updated_at": native.get("updated_at"),
        }
        revision = 2 if native.get("edited_at") else 1
        return MemoryRecord(
            memory_id=memory_id,
            namespace=namespace,
            content=content,
            metadata=metadata,
            state=state,
            revision=revision,
        )

    def verify_server(self) -> Mapping[str, Any]:
        response = self.transport.request("GET", "/version")
        if not isinstance(response, Mapping):
            raise AdapterError("Hindsight /version returned a non-object")
        found = str(response.get("api_version") or "")
        if found != HINDSIGHT_VERSION:
            raise AdapterError(
                f"Phase 04 requires Hindsight {HINDSIGHT_VERSION}; server is {found!r}"
            )
        return response

    def wait_until_ready(self, timeout_seconds: float = 120.0) -> None:
        deadline = time.monotonic() + timeout_seconds
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                response = self.transport.request("GET", "/health")
                if isinstance(response, Mapping):
                    self.verify_server()
                    return
            except Exception as exc:  # readiness polling preserves final evidence
                last_error = exc
            time.sleep(self.poll_interval_seconds)
        raise AdapterError(f"Hindsight readiness timed out: {last_error}")

    def _list(
        self,
        namespace: str,
        *,
        state: str,
        document_id: str | None = None,
    ) -> list[dict[str, Any]]:
        path = f"/v1/default/banks/{self._bank_path(namespace)}/memories/list"
        offset = 0
        rows: list[dict[str, Any]] = []
        while True:
            response = self.transport.request(
                "GET",
                path,
                query={
                    "state": state,
                    "document_id": document_id,
                    "limit": 100,
                    "offset": offset,
                },
            )
            if not isinstance(response, Mapping):
                raise AdapterError("Hindsight memory listing returned a non-object")
            items = response.get("items", [])
            if not isinstance(items, list):
                raise AdapterError("Hindsight memory listing omitted items")
            rows.extend(item for item in items if isinstance(item, dict))
            offset += len(items)
            total = int(response.get("total", len(rows)))
            if not items or offset >= total:
                return rows

    def _get_native(self, namespace: str, memory_id: str) -> dict[str, Any]:
        path = (
            f"/v1/default/banks/{self._bank_path(namespace)}/memories/"
            f"{quote(memory_id, safe='')}"
        )
        try:
            response = self.transport.request("GET", path)
        except HindsightHTTPError as exc:
            if exc.status_code == 404:
                raise MemoryNotFoundError(
                    f"memory {memory_id!r} does not exist in {namespace!r}"
                ) from exc
            raise
        if not isinstance(response, dict):
            raise AdapterError("Hindsight get-memory returned a non-object")
        return response

    def _list_operations(self, namespace: str) -> list[dict[str, Any]]:
        path = f"/v1/default/banks/{self._bank_path(namespace)}/operations"
        offset = 0
        rows: list[dict[str, Any]] = []
        while True:
            try:
                response = self.transport.request(
                    "GET", path, query={"limit": 100, "offset": offset}
                )
            except HindsightHTTPError as exc:
                if exc.status_code == 404 and offset == 0:
                    return []
                raise
            if not isinstance(response, Mapping):
                raise AdapterError("Hindsight operations listing returned a non-object")
            operations = response.get("operations", [])
            if not isinstance(operations, list):
                raise AdapterError("Hindsight operations listing omitted operations")
            if any(not isinstance(item, dict) for item in operations):
                raise AdapterError("Hindsight operations listing contained malformed item")
            rows.extend(operations)
            offset += len(operations)
            total = int(response.get("total", len(rows)))
            if not operations or offset >= total:
                return rows

    def _wait_for_operation(
        self, namespace: str, operation_id: str
    ) -> Mapping[str, Any]:
        submitted = datetime.now(timezone.utc)
        path = (
            f"/v1/default/banks/{self._bank_path(namespace)}/operations/"
            f"{quote(operation_id, safe='')}"
        )
        deadline = time.monotonic() + self.quiescence_timeout_seconds
        last: Mapping[str, Any] = {}
        poll_timestamps: list[str] = []
        while time.monotonic() < deadline:
            poll_timestamps.append(datetime.now(timezone.utc).isoformat())
            response = self.transport.request("GET", path)
            if not isinstance(response, Mapping):
                raise AdapterError("Hindsight operation status returned a non-object")
            last = response
            status = str(response.get("status") or "")
            if status == "completed":
                completed = datetime.now(timezone.utc)
                self._last_operation = {
                    "operation_id": operation_id,
                    "operation_submitted_at": submitted.isoformat(),
                    "operation_completed_at": completed.isoformat(),
                    "quiescence_criterion": "provider operation status=completed",
                    "operation_terminal_receipt": dict(response),
                    "operation_poll_timestamps": poll_timestamps,
                    "target_operation_coverage": "COMPLETE",
                    "background_operation_coverage": "UNKNOWN",
                    "operation_coverage": "UNKNOWN",
                }
                return response
            if status in {"failed", "cancelled"}:
                self._last_operation = {
                    "operation_id": operation_id,
                    "operation_terminal_receipt": dict(response),
                    "operation_poll_timestamps": poll_timestamps,
                    "target_operation_coverage": "UNKNOWN",
                    "background_operation_coverage": "UNKNOWN",
                    "operation_coverage": "UNKNOWN",
                }
                raise AdapterError(
                    f"Hindsight operation {operation_id} ended as {status}: "
                    f"{response.get('error_message')}"
                )
            if status != "pending" and status != "processing":
                raise AdapterError(
                    f"Hindsight operation {operation_id} has unknown or malformed status {status!r}"
                )
            time.sleep(self.poll_interval_seconds)
        raise AdapterError(
            f"Hindsight operation {operation_id} did not quiesce within "
            f"{self.quiescence_timeout_seconds}s; last={dict(last)!r}"
        )

    def wait_for_quiescence(
        self,
        namespace: str,
        *,
        known_operation_ids: set[str] | None = None,
    ) -> None:
        """Wait on explicit provider operation states, not an arbitrary delay."""

        deadline = time.monotonic() + self.quiescence_timeout_seconds
        submitted = datetime.now(timezone.utc)
        seen_ids: set[str] = set()
        poll_timestamps: list[str] = []
        while time.monotonic() < deadline:
            poll_timestamps.append(datetime.now(timezone.utc).isoformat())
            all_operations = self._list_operations(namespace)
            preexisting = []
            if known_operation_ids is not None:
                preexisting = [
                    item for item in all_operations
                    if str(item.get("id") or item.get("operation_id") or "") in known_operation_ids
                ]
                operations = [
                    item
                    for item in all_operations
                    if str(item.get("id") or item.get("operation_id") or "")
                    not in known_operation_ids
                ]
            else:
                operations = all_operations
            malformed = [
                item for item in operations
                if not str(item.get("id") or item.get("operation_id") or "")
                or str(item.get("status") or "") not in {"pending", "processing", "completed", "failed", "cancelled"}
            ]
            if malformed:
                raise AdapterError(f"Hindsight operation has malformed or unknown state: {malformed!r}")
            active = [
                item
                for item in operations
                if str(item.get("status")) in {"pending", "processing"}
            ]
            failed = [
                item
                for item in operations
                if str(item.get("status")) == "failed"
            ]
            cancelled = [
                item
                for item in operations
                if str(item.get("status")) == "cancelled"
            ]
            if failed:
                evidence = [
                    {
                        "id": item.get("id"),
                        "task_type": item.get("task_type"),
                        "error_message": item.get("error_message"),
                    }
                    for item in failed
                ]
                self._last_operation = {
                    "operation_ids": sorted(seen_ids),
                    "operation_terminal_receipts": failed,
                    "preexisting_operation_receipts": preexisting,
                    "operation_poll_timestamps": poll_timestamps,
                    "operation_coverage": "UNKNOWN",
                }
                raise AdapterError(f"Hindsight async operation failure: {evidence!r}")
            if cancelled:
                self._last_operation = {
                    "operation_ids": sorted(seen_ids),
                    "operation_terminal_receipts": cancelled,
                    "preexisting_operation_receipts": preexisting,
                    "operation_poll_timestamps": poll_timestamps,
                    "operation_coverage": "UNKNOWN",
                }
                raise AdapterError(
                    f"Hindsight async operation cancelled: {cancelled!r}"
                )
            seen_ids.update(str(item.get("id")) for item in active if item.get("id"))
            if not active:
                completed = datetime.now(timezone.utc)
                self._last_operation = {
                    "operation_ids": sorted(seen_ids),
                    "preexisting_operation_receipts": preexisting,
                    "operation_submitted_at": submitted.isoformat(),
                    "operation_completed_at": completed.isoformat(),
                    "quiescence_criterion": "no provider operations pending or processing",
                    "operation_poll_timestamps": poll_timestamps,
                    "operation_terminal_receipts": [
                        item for item in operations
                        if str(item.get("status")) == "completed"
                    ],
                    "background_operation_coverage": "UNKNOWN",
                    "operation_coverage": "UNKNOWN",
                }
                return
            time.sleep(self.poll_interval_seconds)
        raise AdapterError(
            f"Hindsight bank {namespace!r} did not quiesce within "
            f"{self.quiescence_timeout_seconds}s"
        )

    def reset_namespace(self, namespace: str) -> None:
        self.require_supported(ProviderCapability.RESET_NAMESPACE)
        path = f"/v1/default/banks/{self._bank_path(namespace)}/memories"
        try:
            self.transport.request("DELETE", path)
        except HindsightHTTPError as exc:
            if exc.status_code != 404:
                raise

    def write(self, command: WriteCommand) -> MemoryRecord:
        self.require_supported(ProviderCapability.WRITE)
        known_operations = {
            str(item.get("id") or item.get("operation_id"))
            for item in self._list_operations(command.namespace)
        }
        document_id = f"memlife-{uuid4()}"
        path = f"/v1/default/banks/{self._bank_path(command.namespace)}/memories"
        metadata = {
            str(key): str(value)
            for key, value in command.metadata.items()
            if value is not None
        }
        metadata["memlife_source_text"] = command.content
        response = self.transport.request(
            "POST",
            path,
            payload={
                "items": [
                    {
                        "content": command.content,
                        "document_id": document_id,
                        "metadata": metadata,
                    }
                ],
                "async": False,
            },
        )
        if not isinstance(response, Mapping) or response.get("success") is not True:
            raise AdapterError(f"unexpected Hindsight retain response: {response!r}")
        self.wait_for_quiescence(
            command.namespace, known_operation_ids=known_operations
        )
        rows = [
            item
            for item in self._list(
                command.namespace, state="valid", document_id=document_id
            )
            if str(item.get("fact_type")) in {"world", "experience"}
        ]
        exact = [item for item in rows if str(item.get("text")) == command.content]
        selected = exact if exact else rows
        if len(selected) != 1:
            raise AdapterError(
                "retain did not expose exactly one unambiguous source fact for "
                f"document {document_id!r}; found {len(rows)}"
            )
        return self._normalized_record(command.namespace, selected[0])

    def query(self, command: QueryCommand) -> tuple[MemoryRecord, ...]:
        self.require_supported(ProviderCapability.QUERY)
        if LifecycleState.ACTIVE not in command.include_states:
            return ()
        path = (
            f"/v1/default/banks/{self._bank_path(command.namespace)}"
            "/memories/recall"
        )
        response = self.transport.request(
            "POST",
            path,
            payload={
                "query": command.query or "*",
                "types": ["world", "experience", "observation"],
                "budget": "low",
                "max_tokens": 4096,
                "include": {
                    "entities": None,
                    "source_facts": {},
                },
            },
        )
        if not isinstance(response, Mapping) or not isinstance(
            response.get("results", []), list
        ):
            raise AdapterError("unexpected Hindsight recall response")
        accepted = [
            (position, item)
            for position, item in enumerate(response.get("results", []), start=1)
            if isinstance(item, Mapping) and str(item.get("text") or "").strip()
        ]
        selected_pairs = accepted[: command.limit]
        selected = tuple(
            self._normalized_record(command.namespace, item)
            for _, item in selected_pairs
        )
        if self._candidate_evidence_sink is not None:
            exchange_manifest = getattr(self.transport, "last_exchange", None)
            if hasattr(self._candidate_evidence_sink, "capture_and_persist"):
                self._candidate_evidence_sink.capture_and_persist(
                    results=response.get("results"),
                    selected_positions={position for position, _ in selected_pairs},
                    limit=command.limit,
                    exchange_manifest=exchange_manifest,
                    raw_response=response,
                )
            else:
                self._candidate_evidence_sink(
                    capture_candidates(
                        response.get("results", []),
                        selected_positions={position for position, _ in selected_pairs},
                        limit=command.limit,
                    )
                )
        return selected

    def update_or_supersede(self, command: SupersedeCommand) -> MemoryRecord:
        self.require_supported(ProviderCapability.UPDATE_OR_SUPERSEDE)
        self._get_native(command.namespace, command.memory_id)
        known_operations = {
            str(item.get("id") or item.get("operation_id"))
            for item in self._list_operations(command.namespace)
        }
        path = (
            f"/v1/default/banks/{self._bank_path(command.namespace)}/memories/"
            f"{quote(command.memory_id, safe='')}"
        )
        response = self.transport.request(
            "PATCH", path, payload={"text": command.content}
        )
        if not isinstance(response, Mapping):
            raise AdapterError("unexpected Hindsight curation response")
        self.wait_for_quiescence(
            command.namespace, known_operation_ids=known_operations
        )
        return self._normalized_record(command.namespace, response)

    def delete_or_invalidate(self, command: DeleteCommand) -> MemoryRecord:
        self.require_supported(ProviderCapability.DELETE_OR_INVALIDATE)
        current_native = self._get_native(command.namespace, command.memory_id)
        current = self._normalized_record(command.namespace, current_native)
        known_operations = {
            str(item.get("id") or item.get("operation_id"))
            for item in self._list_operations(command.namespace)
        }
        bank = self._bank_path(command.namespace)
        if command.disposition is LifecycleState.REVOKED:
            path = f"/v1/default/banks/{bank}/memories/{quote(command.memory_id, safe='')}"
            response = self.transport.request(
                "PATCH",
                path,
                payload={
                    "state": "invalidated",
                    "reason": "MemLife lifecycle revocation",
                },
            )
            if not isinstance(response, Mapping):
                raise AdapterError("unexpected Hindsight invalidation response")
            self.wait_for_quiescence(
                command.namespace, known_operation_ids=known_operations
            )
            return self._normalized_record(command.namespace, response)

        document_id = current.metadata.get("hindsight_document_id")
        if not document_id:
            raise UnsupportedCapabilityError(
                "Hindsight hard delete is document-scoped and this fact has no document ID"
            )
        path = f"/v1/default/banks/{bank}/documents/{quote(str(document_id), safe='')}"
        self.transport.request("DELETE", path)
        self.wait_for_quiescence(
            command.namespace, known_operation_ids=known_operations
        )
        return current.model_copy(update={"state": LifecycleState.DELETED})

    def list_or_inspect(
        self,
        namespace: str,
        *,
        include_non_active: bool = True,
    ) -> tuple[MemoryRecord, ...]:
        self.require_supported(ProviderCapability.LIST_OR_INSPECT)
        rows = self._list(namespace, state="valid")
        if include_non_active:
            rows.extend(self._list(namespace, state="invalidated"))
        by_id: dict[str, MemoryRecord] = {}
        for item in rows:
            if str(item.get("text") or "").strip():
                record = self._normalized_record(namespace, item)
                by_id[record.memory_id] = record
        return tuple(by_id[key] for key in sorted(by_id))

    def history_for(
        self,
        memory_id: str,
        *,
        namespace: str | None = None,
    ) -> tuple[Mapping[str, Any], ...]:
        if namespace is None:
            raise ValueError("Hindsight observation history requires a namespace")
        path = (
            f"/v1/default/banks/{self._bank_path(namespace)}/memories/"
            f"{quote(memory_id, safe='')}/history"
        )
        response = self.transport.request("GET", path)
        if not isinstance(response, list):
            raise AdapterError("unexpected Hindsight observation history response")
        return tuple(item for item in response if isinstance(item, Mapping))

    def trigger_derivation(self, namespace: str) -> Mapping[str, Any]:
        """Submit one native consolidation and wait for its explicit status."""

        path = f"/v1/default/banks/{self._bank_path(namespace)}/consolidate"
        response = self.transport.request("POST", path, payload={})
        if not isinstance(response, Mapping) or not response.get("operation_id"):
            raise AdapterError("unexpected Hindsight consolidation response")
        return self._wait_for_operation(namespace, str(response["operation_id"]))

    def restart(self) -> None:
        self.require_supported(ProviderCapability.RESTART)
        if self._restart_callback is None:
            raise UnsupportedCapabilityError(
                "Hindsight restart requires a service-controller callback"
            )
        self._restart_callback()
        self.wait_until_ready()
