"""OpenViking 0.4.22 HTTP adapter and audit/provenance normalization."""

from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
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
from memlife.models.safety import reject_sensitive_keys

OPENVIKING_VERSION = "0.4.22"
OPENVIKING_SDK_VERSION = "0.1.12"
OPENVIKING_UPSTREAM_TAG = "v0.4.22"
OPENVIKING_UPSTREAM_COMMIT = "e8716760934d95ef73414484a45bfe475b9296e2"
OPENVIKING_BASE_URL_ENV = "MEMLIFE_OPENVIKING_BASE_URL"
OPENVIKING_API_KEY_ENV = "MEMLIFE_OPENVIKING_API_KEY"
DEFAULT_BASE_URL = "http://127.0.0.1:1933"


def phase05a_manifest_configuration() -> dict[str, Any]:
    """Return the frozen, credential-free Phase 05A provider configuration."""

    return {
        "phase": "05A",
        "provider": "openviking",
        "provider_version": OPENVIKING_VERSION,
        "sdk_version": OPENVIKING_SDK_VERSION,
        "upstream_tag": OPENVIKING_UPSTREAM_TAG,
        "upstream_commit": OPENVIKING_UPSTREAM_COMMIT,
        "python_requirement": ">=3.10",
        "deployment_mode": "isolated self-hosted HTTP service",
        "service_package": f"openviking=={OPENVIKING_VERSION}",
        "client_package": "not installed; urllib.request direct HTTP transport",
        "service_command": "openviking-server",
        "service_host": "127.0.0.1",
        "service_port": 1933,
        "runtime_isolation": "dedicated provider venv over loopback HTTP",
        "storage": "VikingFS over AGFS content plus local vector index",
        "provider_venv_path_class": (
            f"<MEMLIFE_DATA_ROOT>/venvs/openviking-{OPENVIKING_VERSION}"
        ),
        "provider_state_path_class": "<MEMLIFE_DATA_ROOT>/providers/openviking",
        "model_cache_path_class": "<MEMLIFE_DATA_ROOT>/model_cache/openviking",
        "run_path_class": "<MEMLIFE_DATA_ROOT>/runs/phase-05-openviking",
        "vlm_requirement": "required for semantic summaries and memory extraction",
        "embedding_requirement": (
            "required for vector indexing/retrieval; built-in local dense default or "
            "documented OpenAI-compatible endpoint"
        ),
        "reranker_requirement": "optional; vector similarity is used when absent",
        "retrieval_primitive": "POST /api/v1/search/find",
        "async_completion": "GET /api/v1/tasks/{task_id} status=completed",
        "audit_surface": "archive memory_diff.json",
    }


class OpenVikingTransport(Protocol):
    """Small direct-HTTP seam implemented by production and fake transports."""

    def request(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, Any] | None = None,
        payload: Any | None = None,
    ) -> Any: ...


class OpenVikingHTTPError(AdapterError):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"OpenViking HTTP {status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


@dataclass
class UrllibOpenVikingTransport:
    """Dependency-free transport for the isolated OpenViking service."""

    base_url: str = DEFAULT_BASE_URL
    api_key: str | None = None
    timeout_seconds: float = 120.0

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        parsed = urlsplit(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("OpenViking base URL must be an absolute http(s) URL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("OpenViking base URL must not contain credentials/query/fragment")
        if self.timeout_seconds <= 0:
            raise ValueError("OpenViking HTTP timeout must be positive")

    @staticmethod
    def _query_items(query: Mapping[str, Any]) -> list[tuple[str, str]]:
        items: list[tuple[str, str]] = []
        for key, value in query.items():
            if value is None:
                continue
            values = value if isinstance(value, (list, tuple)) else (value,)
            for item in values:
                if isinstance(item, bool):
                    rendered = str(item).lower()
                else:
                    rendered = str(item)
                items.append((str(key), rendered))
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
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = Request(url, data=body, method=method.upper(), headers=headers)
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read()
        except HTTPError as exc:
            raw_error = exc.read().decode("utf-8", errors="replace")
            try:
                parsed_error = json.loads(raw_error)
                error = parsed_error.get("error", parsed_error)
                detail = error.get("message", error) if isinstance(error, Mapping) else error
            except json.JSONDecodeError:
                detail = raw_error or str(exc.reason)
            raise OpenVikingHTTPError(exc.code, str(detail)) from exc
        except (URLError, TimeoutError) as exc:
            raise AdapterError(f"OpenViking service request failed: {exc}") from exc
        if not raw:
            return None
        response = json.loads(raw.decode("utf-8"))
        if isinstance(response, Mapping) and response.get("status") == "error":
            error = response.get("error", {})
            detail = error.get("message", error) if isinstance(error, Mapping) else error
            raise OpenVikingHTTPError(200, str(detail))
        if isinstance(response, Mapping) and response.get("status") == "ok":
            if "result" in response:
                return response.get("result")
            return {key: value for key, value in response.items() if key != "status"}
        return response


@dataclass(frozen=True)
class MemoryDiffOperation:
    operation: str
    uri: str
    memory_type: str
    before: str | None = None
    after: str | None = None
    deleted_content: str | None = None


@dataclass(frozen=True)
class ParsedMemoryDiff:
    archive_uri: str
    extracted_at: str | None
    operations: tuple[MemoryDiffOperation, ...]
    skipped_operations: tuple[Mapping[str, Any], ...]


def parse_memory_diff(value: str | Mapping[str, Any]) -> ParsedMemoryDiff:
    """Validate the documented memory_diff.json audit shape."""

    payload = json.loads(value) if isinstance(value, str) else dict(value)
    archive_uri = str(payload.get("archive_uri") or "")
    if not archive_uri.startswith("viking://"):
        raise AdapterError("OpenViking memory diff lacks a valid archive_uri")
    operations_value = payload.get("operations")
    if not isinstance(operations_value, Mapping):
        raise AdapterError("OpenViking memory diff lacks operations")
    operations: list[MemoryDiffOperation] = []
    for plural, singular in (("adds", "add"), ("updates", "update"), ("deletes", "delete")):
        rows = operations_value.get(plural, [])
        if not isinstance(rows, list):
            raise AdapterError(f"OpenViking memory diff {plural} must be a list")
        for row in rows:
            if not isinstance(row, Mapping) or not row.get("uri"):
                raise AdapterError(f"OpenViking memory diff {plural} contains an invalid row")
            operations.append(
                MemoryDiffOperation(
                    operation=singular,
                    uri=str(row["uri"]),
                    memory_type=str(row.get("memory_type") or "unknown"),
                    before=None if row.get("before") is None else str(row["before"]),
                    after=None if row.get("after") is None else str(row["after"]),
                    deleted_content=(
                        None
                        if row.get("deleted_content") is None
                        else str(row["deleted_content"])
                    ),
                )
            )
    skipped = payload.get("skipped_operations", [])
    if not isinstance(skipped, list) or any(not isinstance(row, Mapping) for row in skipped):
        raise AdapterError("OpenViking memory diff skipped_operations must be a list")
    return ParsedMemoryDiff(
        archive_uri=archive_uri,
        extracted_at=(
            None if payload.get("extracted_at") is None else str(payload["extracted_at"])
        ),
        operations=tuple(operations),
        skipped_operations=tuple(dict(row) for row in skipped),
    )


class OpenVikingMemoryAdapter(MemoryProviderAdapter):
    """Normalize session-driven OpenViking memory without inventing 1:1 identity.

    ``MemoryRecord.memory_id`` returned by ``write`` is a MemLife source-event
    identifier. Provider memory URIs remain a separate one-to-many set in the
    record metadata and internal correlation table.
    """

    def __init__(
        self,
        transport: OpenVikingTransport,
        *,
        restart_callback: Callable[[], None] | None = None,
        quiescence_timeout_seconds: float = 300.0,
        poll_interval_seconds: float = 0.25,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        if quiescence_timeout_seconds <= 0:
            raise ValueError("quiescence timeout must be positive")
        if poll_interval_seconds <= 0:
            raise ValueError("poll interval must be positive")
        self.transport = transport
        self._restart_callback = restart_callback
        self.quiescence_timeout_seconds = quiescence_timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self._sleep = sleeper
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._correlations: dict[str, dict[str, Any]] = {}
        self._namespace_sources: dict[str, list[str]] = {}
        self._last_operation: dict[str, Any] = {}

    @classmethod
    def from_environment(
        cls, *, restart_callback: Callable[[], None] | None = None
    ) -> "OpenVikingMemoryAdapter":
        return cls(
            UrllibOpenVikingTransport(
                os.environ.get(OPENVIKING_BASE_URL_ENV, DEFAULT_BASE_URL),
                api_key=os.environ.get(OPENVIKING_API_KEY_ENV),
            ),
            restart_callback=restart_callback,
        )

    @property
    def provider_name(self) -> str:
        return f"openviking-self-hosted-{OPENVIKING_VERSION}"

    @property
    def provider_version(self) -> str:
        return OPENVIKING_VERSION

    @property
    def capabilities(self) -> Mapping[ProviderCapability, CapabilitySupport]:
        values = {
            ProviderCapability.RESET_NAMESPACE: CapabilitySupport.SUPPORTED,
            ProviderCapability.WRITE: CapabilitySupport.SUPPORTED,
            ProviderCapability.QUERY: CapabilitySupport.SUPPORTED,
            ProviderCapability.UPDATE_OR_SUPERSEDE: CapabilitySupport.UNSUPPORTED,
            ProviderCapability.DELETE_OR_INVALIDATE: CapabilitySupport.SUPPORTED,
            ProviderCapability.LIST_OR_INSPECT: CapabilitySupport.SUPPORTED,
            ProviderCapability.RESTART: CapabilitySupport.SUPPORTED,
        }
        if self._restart_callback is None:
            values[ProviderCapability.RESTART] = CapabilitySupport.UNSUPPORTED
        return values

    def native_operation_for(self, intended_event: str) -> str:
        return {
            "WRITE": "create session -> add user message -> commit -> poll task -> read memory_diff",
            "QUERY": "POST /api/v1/search/find scoped to memory",
            "UPDATE": "UNSUPPORTED: extraction may update internally; no canonical external update mapping",
            "SUPERSEDE": "UNSUPPORTED: no explicit replacement/supersession edge",
            "REVOKE": "UNSUPPORTED: no revoke/invalidate/disable/tombstone primitive",
            "DELETE": "DELETE /api/v1/fs for every correlated provider memory URI",
            "INSPECT": "read correlated provider memory URIs",
            "RESTART": "stop/start run-owned service with the same persistent workspace",
        }.get(intended_event, super().native_operation_for(intended_event))

    def benchmark_metadata(self) -> Mapping[str, Any]:
        return {
            "deployment_mode": "self-hosted HTTP service",
            "retrieval_surface": "find(memory), no query-planner LLM",
            "identity_semantics": "MemLife source event -> zero/one/many provider memory URIs",
            "update_semantics": "unsupported externally; internal diff updates are audit evidence only",
            "revocation_semantics": "unsupported",
            "history_semantics": "memory_diff operations for adapter-observed commits",
            **self._last_operation,
        }

    def manifest_configuration(self) -> dict[str, Any]:
        return phase05a_manifest_configuration()

    @property
    def trace_source_surface(self) -> MemorySurface:
        return MemorySurface.SOURCE

    @property
    def trace_provenance_status(self) -> ProvenanceStatus:
        return ProvenanceStatus.UNKNOWN

    def trace_surface_for(self, record: MemoryRecord) -> MemorySurface:
        value = record.metadata.get("openviking_surface")
        try:
            return MemorySurface(str(value))
        except ValueError:
            return MemorySurface.UNKNOWN

    def trace_provenance_status_for(self, record: MemoryRecord) -> ProvenanceStatus:
        if record.metadata.get("openviking_memory_diff_operation") in {
            "add",
            "update",
            "delete",
        } and record.metadata.get("openviking_source_event_id"):
            return ProvenanceStatus.KNOWN
        return ProvenanceStatus.UNKNOWN

    def trace_source_provider_ids_for(self, record: MemoryRecord) -> tuple[str, ...]:
        source = record.metadata.get("openviking_source_event_id")
        return (str(source),) if source else ()

    def trace_metadata_for(self, record: MemoryRecord) -> Mapping[str, Any]:
        metadata = {
            "provider_surface": record.metadata.get("openviking_surface", "UNKNOWN"),
            "provider_memory_uri": record.metadata.get("openviking_memory_uri"),
            "provider_memory_type": record.metadata.get("openviking_memory_type"),
            "provider_memory_diff_operation": record.metadata.get(
                "openviking_memory_diff_operation"
            ),
            "provider_session_id": record.metadata.get("openviking_session_id"),
            "provider_archive_uri": record.metadata.get("openviking_archive_uri"),
            "provider_task_id": record.metadata.get("openviking_task_id"),
        }
        return reject_sensitive_keys(metadata, field_name="OpenViking trace metadata")

    @staticmethod
    def _namespace_slug(namespace: str) -> str:
        slug = re.sub(r"[^a-z0-9-]+", "-", namespace.casefold()).strip("-")
        return (slug or "namespace")[:48]

    @classmethod
    def _session_prefix(cls, namespace: str) -> str:
        return f"memlife-{cls._namespace_slug(namespace)}-"

    @staticmethod
    def _archive_id(archive_uri: str) -> str:
        return archive_uri.rstrip("/").rsplit("/", 1)[-1]

    @staticmethod
    def _surface(memory_type: str) -> MemorySurface:
        if memory_type == "profile":
            return MemorySurface.PROFILE
        return MemorySurface.DERIVED

    def wait_until_ready(self, *, timeout_seconds: float | None = None) -> Mapping[str, Any]:
        timeout = timeout_seconds or self.quiescence_timeout_seconds
        deadline = time.monotonic() + timeout
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                response = self.transport.request("GET", "/ready")
                if response is True or (
                    isinstance(response, Mapping)
                    and (response.get("ready") is True or response.get("healthy") is True)
                ):
                    return response if isinstance(response, Mapping) else {"ready": True}
            except Exception as exc:  # readiness is retried until the bounded deadline
                last_error = exc
            self._sleep(self.poll_interval_seconds)
        suffix = f": {last_error}" if last_error else ""
        raise TimeoutError(f"OpenViking readiness timed out{suffix}")

    def wait_for_quiescence(self, task_id: str) -> Mapping[str, Any]:
        submitted_at = self._clock()
        started = time.monotonic()
        deadline = started + self.quiescence_timeout_seconds
        last_status = "unknown"
        while time.monotonic() < deadline:
            task = self.transport.request(
                "GET", f"/api/v1/tasks/{quote(task_id, safe='')}"
            )
            if not isinstance(task, Mapping):
                raise AdapterError("OpenViking task response is not an object")
            last_status = str(task.get("status") or "unknown").casefold()
            if last_status == "completed":
                completed_at = self._clock()
                self._last_operation = {
                    "task_id": task_id,
                    "task_status": last_status,
                    "task_submitted_at": submitted_at.isoformat(),
                    "task_completed_at": completed_at.isoformat(),
                    "quiescence_seconds": round(time.monotonic() - started, 6),
                    "quiescence_criterion": "provider task status=completed",
                }
                return task
            if last_status in {"failed", "cancelled"}:
                raise AdapterError(
                    f"OpenViking task {task_id} ended as {last_status}: {task.get('error')}"
                )
            if last_status not in {"pending", "running", "cancelling"}:
                raise AdapterError(
                    f"OpenViking task {task_id} reported unknown status {last_status!r}"
                )
            self._sleep(self.poll_interval_seconds)
        raise TimeoutError(
            f"OpenViking task {task_id} did not complete before timeout "
            f"(last status {last_status})"
        )

    def _read_memory_diff(self, archive_uri: str) -> ParsedMemoryDiff:
        value = self.transport.request(
            "GET",
            "/api/v1/content/read",
            query={"uri": f"{archive_uri.rstrip('/')}/memory_diff.json", "raw": True},
        )
        if not isinstance(value, (str, Mapping)):
            raise AdapterError("OpenViking memory_diff read returned an invalid value")
        return parse_memory_diff(value)

    def reset_namespace(self, namespace: str) -> None:
        self.require_supported(ProviderCapability.RESET_NAMESPACE)
        sessions = self.transport.request("GET", "/api/v1/sessions")
        rows = sessions if isinstance(sessions, list) else []
        prefix = self._session_prefix(namespace)
        for row in rows:
            if isinstance(row, Mapping) and str(row.get("session_id", "")).startswith(prefix):
                self.transport.request(
                    "DELETE",
                    f"/api/v1/sessions/{quote(str(row['session_id']), safe='')}",
                )
        for source_id in self._namespace_sources.pop(namespace, []):
            self._correlations.pop(source_id, None)
        self._last_operation = {
            "reset_semantics": "delete MemLife-prefixed sessions; provider owns associated cleanup"
        }

    def write(self, command: WriteCommand) -> MemoryRecord:
        self.require_supported(ProviderCapability.WRITE)
        source_event_id = str(command.metadata.get("source_event_id") or self._id_factory())
        session_id = f"{self._session_prefix(command.namespace)}{source_event_id}"
        created = self.transport.request(
            "POST", "/api/v1/sessions", payload={"session_id": session_id}
        )
        if not isinstance(created, Mapping) or not created.get("session_id"):
            raise AdapterError("OpenViking session creation returned no session_id")
        session_id = str(created["session_id"])
        added = self.transport.request(
            "POST",
            f"/api/v1/sessions/{quote(session_id, safe='')}/messages",
            payload={"role": "user", "content": command.content},
        )
        if not isinstance(added, Mapping):
            raise AdapterError("OpenViking add-message returned an invalid response")
        commit = self.transport.request(
            "POST", f"/api/v1/sessions/{quote(session_id, safe='')}/commit", payload={}
        )
        if not isinstance(commit, Mapping):
            raise AdapterError("OpenViking commit returned an invalid response")
        if commit.get("status") != "accepted" or not commit.get("task_id"):
            raise AdapterError(
                f"OpenViking write commit was not accepted: {commit.get('status')}"
            )
        task_id = str(commit["task_id"])
        archive_uri = str(commit.get("archive_uri") or "")
        if not archive_uri:
            raise AdapterError("OpenViking accepted commit returned no archive_uri")
        self.wait_for_quiescence(task_id)
        memory_diff = self._read_memory_diff(archive_uri)
        applied = tuple(
            operation
            for operation in memory_diff.operations
            if operation.operation in {"add", "update"}
        )
        correlation = {
            "namespace": command.namespace,
            "source_event_id": source_event_id,
            "source_content": command.content,
            "session_id": session_id,
            "archive_uri": archive_uri,
            "archive_id": self._archive_id(archive_uri),
            "task_id": task_id,
            "task_status": "completed",
            "extracted_at": memory_diff.extracted_at,
            "operations": memory_diff.operations,
            "provider_memory_uris": tuple(operation.uri for operation in applied),
        }
        self._correlations[source_event_id] = correlation
        self._namespace_sources.setdefault(command.namespace, []).append(source_event_id)
        self._last_operation.update(
            {
                "session_id": session_id,
                "archive_uri": archive_uri,
                "memory_diff_operation_count": len(memory_diff.operations),
                "provider_memory_uri_count": len(applied),
                "write_correlation": "one-to-many; no provider URI selected as canonical",
            }
        )
        return MemoryRecord(
            memory_id=source_event_id,
            namespace=command.namespace,
            content=command.content,
            metadata={
                "openviking_surface": MemorySurface.SOURCE.value,
                "openviking_source_event_id": source_event_id,
                "openviking_session_id": session_id,
                "openviking_archive_uri": archive_uri,
                "openviking_task_id": task_id,
                "openviking_task_status": "completed",
                "openviking_provider_memory_uris": list(correlation["provider_memory_uris"]),
                "openviking_extracted_at": memory_diff.extracted_at,
            },
            state=LifecycleState.ACTIVE,
            revision=1,
        )

    def _known_uri_map(self, namespace: str) -> dict[str, tuple[str, MemoryDiffOperation]]:
        known: dict[str, tuple[str, MemoryDiffOperation]] = {}
        for source_id in self._namespace_sources.get(namespace, []):
            correlation = self._correlations.get(source_id, {})
            for operation in correlation.get("operations", ()):
                if isinstance(operation, MemoryDiffOperation) and operation.operation in {
                    "add",
                    "update",
                }:
                    known[operation.uri] = (source_id, operation)
        return known

    def _normalized_memory(
        self,
        namespace: str,
        row: Mapping[str, Any],
        source_id: str,
        operation: MemoryDiffOperation,
    ) -> MemoryRecord:
        uri = str(row.get("uri") or operation.uri)
        content = str(
            row.get("content")
            or row.get("text")
            or operation.after
            or row.get("abstract")
            or uri
        ).strip()
        correlation = self._correlations[source_id]
        return MemoryRecord(
            memory_id=uri,
            namespace=namespace,
            content=content,
            metadata={
                "openviking_surface": self._surface(operation.memory_type).value,
                "openviking_source_event_id": source_id,
                "openviking_memory_uri": uri,
                "openviking_memory_type": operation.memory_type,
                "openviking_memory_diff_operation": operation.operation,
                "openviking_session_id": correlation["session_id"],
                "openviking_archive_uri": correlation["archive_uri"],
                "openviking_task_id": correlation["task_id"],
                "openviking_score": row.get("score"),
            },
            state=LifecycleState.ACTIVE,
            revision=1,
        )

    def query(self, command: QueryCommand) -> tuple[MemoryRecord, ...]:
        self.require_supported(ProviderCapability.QUERY)
        response = self.transport.request(
            "POST",
            "/api/v1/search/find",
            payload={
                "query": command.query,
                "target_uri": "viking://~/memories",
                "context_type": "memory",
                "limit": command.limit,
                "read_content": True,
            },
        )
        if not isinstance(response, Mapping):
            raise AdapterError("OpenViking find response is not an object")
        memories = response.get("memories", [])
        if not isinstance(memories, list):
            raise AdapterError("OpenViking find memories is not a list")
        known = self._known_uri_map(command.namespace)
        records = []
        for row in memories:
            if not isinstance(row, Mapping):
                continue
            uri = str(row.get("uri") or "")
            if uri in known:
                source_id, operation = known[uri]
                records.append(
                    self._normalized_memory(command.namespace, row, source_id, operation)
                )
        return tuple(records)

    def update_or_supersede(self, command: SupersedeCommand) -> MemoryRecord:
        self.require_supported(ProviderCapability.UPDATE_OR_SUPERSEDE)
        raise AssertionError("unreachable")

    def delete_or_invalidate(self, command: DeleteCommand) -> MemoryRecord:
        self.require_supported(ProviderCapability.DELETE_OR_INVALIDATE)
        if command.disposition is LifecycleState.REVOKED:
            raise UnsupportedCapabilityError(
                "OpenViking exposes no native revoke/invalidate/disable/tombstone operation"
            )
        correlation = self._correlations.get(command.memory_id)
        if correlation is None:
            raise MemoryNotFoundError(
                "OpenViking deletion requires a MemLife source-event correlation"
            )
        uris = tuple(correlation["provider_memory_uris"])
        for uri in uris:
            self.transport.request(
                "DELETE", "/api/v1/fs", query={"uri": uri, "recursive": False}
            )
        correlation["deleted"] = True
        self._last_operation = {
            "delete_source_event_id": command.memory_id,
            "deleted_provider_memory_uris": list(uris),
            "delete_semantics": "external URI deletion; not revocation",
        }
        return MemoryRecord(
            memory_id=command.memory_id,
            namespace=command.namespace,
            content=str(correlation["source_content"]),
            metadata={
                "openviking_surface": MemorySurface.SOURCE.value,
                "openviking_source_event_id": command.memory_id,
                "openviking_deleted_provider_memory_uris": list(uris),
            },
            state=LifecycleState.DELETED,
            revision=1,
        )

    def list_or_inspect(
        self, namespace: str, *, include_non_active: bool = True
    ) -> tuple[MemoryRecord, ...]:
        self.require_supported(ProviderCapability.LIST_OR_INSPECT)
        known = self._known_uri_map(namespace)
        records: list[MemoryRecord] = []
        for uri in sorted(known):
            source_id, operation = known[uri]
            correlation = self._correlations[source_id]
            if correlation.get("deleted"):
                continue
            try:
                content = self.transport.request(
                    "GET", "/api/v1/content/read", query={"uri": uri}
                )
            except OpenVikingHTTPError as exc:
                if exc.status_code == 404:
                    continue
                raise
            records.append(
                self._normalized_memory(
                    namespace, {"uri": uri, "content": content}, source_id, operation
                )
            )
        return tuple(records)

    def history_for(
        self, memory_id: str, *, namespace: str | None = None
    ) -> tuple[Mapping[str, Any], ...]:
        correlation = self._correlations.get(memory_id)
        if correlation is None:
            for candidate in self._correlations.values():
                if memory_id in candidate.get("provider_memory_uris", ()):
                    correlation = candidate
                    break
        if correlation is None or (namespace and correlation["namespace"] != namespace):
            raise MemoryNotFoundError("OpenViking correlation history was not observed")
        return tuple(
            {
                "event": operation.operation,
                "uri": operation.uri,
                "memory_type": operation.memory_type,
                "archive_uri": correlation["archive_uri"],
                "task_id": correlation["task_id"],
                "extracted_at": correlation["extracted_at"],
            }
            for operation in correlation["operations"]
        )

    def trigger_derivation(self, session_id: str) -> tuple[Mapping[str, Any], ...]:
        response = self.transport.request(
            "POST", f"/api/v1/sessions/{quote(session_id, safe='')}/extract", payload={}
        )
        if not isinstance(response, list) or any(not isinstance(row, Mapping) for row in response):
            raise AdapterError("OpenViking extraction response is not a result list")
        return tuple(dict(row) for row in response)

    def restart(self) -> None:
        self.require_supported(ProviderCapability.RESTART)
        if self._restart_callback is None:
            raise UnsupportedCapabilityError(
                "OpenViking restart requires a service-controller callback"
            )
        self._restart_callback()
        self.wait_until_ready()
