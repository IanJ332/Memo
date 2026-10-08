#!/usr/bin/env python3
"""One-shot, fail-closed Honcho 3.2.1 acceptance runner for Jetstream."""

from __future__ import annotations

import argparse
import hashlib
import http.server
import ipaddress
import math
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import time
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from importlib.metadata import version as package_version

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from memlife.adapters.honcho import (  # noqa: E402
    DirectoryRawArtifactCapture,
    HonchoHttpTransport,
    HonchoLiveAdapter,
    HonchoLiveConfig,
)
from memlife.models.memory import QueryCommand, WriteCommand  # noqa: E402
from memlife.models.provider_acceptance import (  # noqa: E402
    AcceptanceCapability,
    CapabilityClassification,
)
from memlife.runner.phase08b1 import (  # noqa: E402
    ACCEPTANCE_DERIVER_FLUSH_ENABLED,
    ACCEPTANCE_DREAM_ENABLED,
    ACCEPTANCE_DREAM_ENABLED_TYPES,
    ACCEPTANCE_DREAM_MODEL_CONFIG,
    ACCEPTANCE_EMBEDDING_VECTOR_DIMENSIONS,
    BASE_COMMIT,
    CURRENT_EMBEDDING_ASSESSMENT,
    CURRENT_PROVENANCE_ASSESSMENT,
    DREAM_OPERATION_BUDGET,
    DreamOperationGuard,
    PROVENANCE_PROBE_PURPOSE,
    PROVIDER_INTERNAL_MODEL_REQUEST_BUDGET,
    QUIESCENCE_MAX_CHECKS,
    QUIESCENCE_POLL_SECONDS,
    EFFECTIVE_REASONING_EFFORT,
    REASONING_EFFORT_COMPATIBILITY_REASON,
    REASONING_EFFORT_COMPATIBILITY_RESOLUTION,
    REQUESTED_REASONING_EFFORT,
    REQUIRED_ARTIFACTS,
    SENTENCE_TRANSFORMERS_VERSION,
    SUPPORTED_HOSTED_REASONING_EFFORTS,
    UPSTREAM_COMMIT,
    UPSTREAM_TAG,
    acceptance_record,
    bound_runtime_manifest,
    build_capability_assessments,
    build_provider_raw_index,
    build_provider_surface_inventory,
    build_scenario_evidence_matrix,
    canonical_json_bytes,
    classify_native_search_result,
    current_baseline_authority_ledger,
    derive_scenario_classifications,
    evidence_binding,
    evaluate_lineage,
    evaluate_trigger_relative_quiescence,
    index_adapter_raw_captures,
    LiveCalibrationState,
    load_static_api_audit,
    sha256_bytes,
    stage_a_allows_stage_b,
    surface_inventory_classifications,
    validate_model_endpoint_compatibility,
    validate_static_api_audit,
    write_completion,
    write_json_exclusive,
)

UPSTREAM_URL = "https://github.com/plastic-labs/honcho.git"
TEXT_MODEL = "gpt-oss-120b"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-MiniLM-L3-v2"
MODEL_ENDPOINT = "https://llm.jetstream-cloud.org/gpt-oss-120b/v1/"
MAX_MODEL_CALLS = PROVIDER_INTERNAL_MODEL_REQUEST_BUDGET
PROXY_BASE_URL = "http://host.docker.internal:18081/v1/"
EMBEDDING_VECTOR_DIMENSIONS = ACCEPTANCE_EMBEDDING_VECTOR_DIMENSIONS
DREAM_CONFIG_CHANGE_AUTHORIZED = True
DERIVER_FLUSH_CHANGE_AUTHORIZED = True
PREFLIGHT_AUTHORIZATION = "Bearer empty"
DOCKER_BRIDGE_SOURCE_RANGE = ipaddress.ip_network("172.16.0.0/12")
FIXTURE_CONTENT = (
    "Fictional benchmark subject Rowan keeps the amber notebook in cabinet seven."
)
FIXTURE_QUERY = "Where does fictional benchmark subject Rowan keep the amber notebook?"
RETRIEVAL_LIMIT = 10
REQUIRED_COMPOSE_SERVICES = ("database", "redis", "api", "deriver")
EFFECTIVE_CONFIG_ARTIFACTS = {
    "api": "effective-config/api.json",
    "deriver": "effective-config/deriver.json",
}
REDACTED_VALUE = "<REDACTED>"
CANDIDATE8_EMBEDDING_MODEL = "gpt-oss-120b"
CANDIDATE8_EMBEDDING_VECTOR_DIMENSIONS = 1536
RUNTIME_ENV_NAME = ".env"
RUNTIME_COMPOSE_NAME = "docker-compose.phase08b1.yml"
SENSITIVE_SETTING_COMPONENTS = frozenset(
    {
        "api_key",
        "authorization",
        "connection_uri",
        "credential",
        "credentials",
        "dsn",
        "password",
        "private_key",
        "secret",
        "token",
    }
)

# This program runs inside each pinned Honcho container. Redaction occurs before
# the settings JSON crosses the container boundary; the host only receives the
# already-redacted payload and its canonical digest.
EFFECTIVE_SETTINGS_CAPTURE_CODE = r'''
import hashlib
import json
from collections.abc import Mapping
from src.config import settings

REDACTED = "<REDACTED>"
SENSITIVE = {
    "api_key", "authorization", "connection_uri", "credential", "credentials",
    "dsn", "password", "private_key", "secret", "token",
}

def sensitive(component):
    normalized = str(component).strip().lower().replace("-", "_")
    return normalized in SENSITIVE or any(
        normalized.endswith("_" + item) for item in SENSITIVE
    )

def redact(value, path=()):
    if isinstance(value, Mapping):
        result = {}
        paths = []
        for key, child in value.items():
            child_path = path + (str(key),)
            if sensitive(key):
                result[str(key)] = REDACTED
                paths.append(".".join(child_path))
            else:
                result[str(key)], child_paths = redact(child, child_path)
                paths.extend(child_paths)
        return result, paths
    if isinstance(value, list):
        result = []
        paths = []
        for index, child in enumerate(value):
            item, child_paths = redact(child, path + (str(index),))
            result.append(item)
            paths.extend(child_paths)
        return result, paths
    if isinstance(value, str) and "://" in value:
        scheme, remainder = value.split("://", 1)
        authority, separator, suffix = remainder.partition("/")
        if "@" in authority:
            host = authority.rsplit("@", 1)[1]
            sanitized = f"{scheme}://{REDACTED}@{host}"
            if separator:
                sanitized += "/" + suffix
            return sanitized, [".".join(path)]
    return value, []

redacted, redacted_paths = redact(settings.model_dump(mode="json", by_alias=True))
canonical = (json.dumps(redacted, indent=2, sort_keys=True) + "\n").encode("utf-8")
payload = {
    "effective_settings": redacted,
    "redacted_paths": sorted(redacted_paths),
    "effective_settings_sha256": hashlib.sha256(canonical).hexdigest(),
}
print("PHASE08B1_EFFECTIVE_CONFIG=" + json.dumps(payload, sort_keys=True))
'''


def model_proxy_client_allowed(host: str) -> bool:
    """Permit only this host and the expected private Docker bridge range."""

    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return address.is_loopback or (
        isinstance(address, ipaddress.IPv4Address)
        and address in DOCKER_BRIDGE_SOURCE_RANGE
    )


def validate_structured_output_response(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the exact deterministic schema requested by Stage A."""

    choices = payload.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise ValueError("structured-output preflight requires exactly one choice")
    choice = choices[0]
    if not isinstance(choice, Mapping):
        raise ValueError("structured-output choice must be an object")
    message = choice.get("message")
    if not isinstance(message, Mapping) or message.get("role") != "assistant":
        raise ValueError("structured-output preflight requires one assistant message")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("structured-output assistant content must be non-empty text")
    try:
        decoded = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("structured-output assistant content is not valid JSON") from exc
    if not isinstance(decoded, dict) or set(decoded) != {"explicit"}:
        raise ValueError("structured-output JSON must contain only explicit")
    explicit = decoded["explicit"]
    if not isinstance(explicit, list):
        raise ValueError("structured-output explicit must be a list")
    for item in explicit:
        if not isinstance(item, dict) or set(item) != {"content"}:
            raise ValueError("each structured-output item must contain only content")
        if not isinstance(item["content"], str):
            raise ValueError("each structured-output item content must be a string")
    return decoded


def validate_dream_tool_response(payload: Mapping[str, Any]) -> None:
    """Require the exact native function call requested by the Dream preflight."""

    choices = payload.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise ValueError("Dream tool preflight requires exactly one choice")
    choice = choices[0]
    message = choice.get("message") if isinstance(choice, Mapping) else None
    tool_calls = message.get("tool_calls") if isinstance(message, Mapping) else None
    if not isinstance(tool_calls, list) or len(tool_calls) != 1:
        raise ValueError("Dream tool preflight requires exactly one native tool call")
    call = tool_calls[0]
    function = call.get("function") if isinstance(call, Mapping) else None
    if (
        not isinstance(call, Mapping)
        or call.get("type") != "function"
        or not isinstance(function, Mapping)
        or function.get("name") != "finish_preflight"
    ):
        raise ValueError("Dream tool preflight returned the wrong native tool call")
    arguments = function.get("arguments")
    if not isinstance(arguments, str):
        raise ValueError("Dream tool-call arguments must be JSON text")
    try:
        decoded = json.loads(arguments)
    except json.JSONDecodeError as exc:
        raise ValueError("Dream tool-call arguments are invalid JSON") from exc
    if decoded != {}:
        raise ValueError("Dream tool-call arguments must match the empty schema")


class ProviderContactState:
    """Track provider startup, contact attempts, and successful health separately."""

    def __init__(self) -> None:
        self.provider_stack_start_attempted = False
        self.provider_stack_started = False
        self.provider_contact_attempted = False
        self.provider_api_health_passed = False
        self.provider_required_services_passed = False
        self.provider_health_passed = False

    @property
    def contacted(self) -> bool:
        return (
            self.provider_stack_start_attempted
            or self.provider_stack_started
            or self.provider_contact_attempted
        )

    def mark_stack_start_attempted(self) -> None:
        self.provider_stack_start_attempted = True

    def mark_stack_started(self) -> None:
        self.provider_stack_start_attempted = True
        self.provider_stack_started = True

    def mark_health_attempted(self) -> None:
        self.provider_contact_attempted = True

    def begin_required_health_check(self) -> None:
        self.provider_api_health_passed = False
        self.provider_required_services_passed = False
        self.provider_health_passed = False

    def mark_api_health_passed(self) -> None:
        self.provider_contact_attempted = True
        self.provider_api_health_passed = True

    def mark_required_services_passed(self) -> None:
        self.provider_required_services_passed = True
        self.provider_health_passed = self.provider_api_health_passed


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(command: list[str], *, cwd: Path | None = None, timeout: int = 1800) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout)[-8000:]
        raise RuntimeError(f"command failed ({command[0]}): {detail}")
    return result.stdout


def disk(path: Path) -> dict[str, int]:
    usage = shutil.disk_usage(path)
    return {"total_bytes": usage.total, "used_bytes": usage.used, "free_bytes": usage.free}


def memory() -> dict[str, int]:
    values: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        key, value = line.split(":", 1)
        values[key] = int(value.strip().split()[0]) * 1024
    return {
        "total_bytes": values.get("MemTotal", 0),
        "available_bytes": values.get("MemAvailable", 0),
        "swap_total_bytes": values.get("SwapTotal", 0),
        "swap_free_bytes": values.get("SwapFree", 0),
    }


class RawLog:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.entries: list[dict[str, Any]] = []

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: object | None = None,
        expected: set[int] = {200},
        name: str,
    ) -> Any:
        data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode()
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            "http://127.0.0.1:8000/" + path.lstrip("/"),
            data=data,
            headers=headers,
            method=method,
        )
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                status = response.status
                body = response.read()
        except urllib.error.HTTPError as exc:
            status = exc.code
            body = exc.read()
        elapsed = round(time.monotonic() - started, 6)
        target = (
            self.root
            / "provider-raw-responses"
            / f"{len(self.entries) + 1:03d}-{name}.json"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        self.entries.append(
            {
                "name": name,
                "method": method,
                "path": path,
                "status_code": status,
                "artifact": target.relative_to(self.root).as_posix(),
                "sha256": sha256_bytes(body),
                "bytes": len(body),
                "duration_seconds": elapsed,
                "captured_before_normalization": True,
            }
        )
        if status not in expected:
            detail = body.decode("utf-8", errors="replace")[-2000:]
            raise RuntimeError(f"Honcho HTTP {status} for {path}: {detail}")
        if not body:
            return None
        return json.loads(body)


class LocalEmbeddingRequestError(ValueError):
    """The OpenAI-compatible embedding request or model output is invalid."""


class LocalEmbeddingUnavailable(RuntimeError):
    """The exact offline embedding artifact cannot be loaded deterministically."""


class HostedReasoningEffortCompatibilityError(ValueError):
    """A hosted chat reasoning effort cannot be resolved without guessing."""

    def __init__(self, requested: object) -> None:
        self.audit = {
            "requested_reasoning_effort": requested,
            "effective_reasoning_effort": None,
            "compatibility_resolution": "REJECTED_UNSUPPORTED",
            "compatibility_reason": REASONING_EFFORT_COMPATIBILITY_REASON,
        }
        super().__init__(
            f"unsupported hosted reasoning_effort {requested!r}; "
            "accepted values are low, medium, or high"
        )


def resolve_hosted_reasoning_effort(requested: object) -> tuple[str, dict[str, Any]]:
    """Resolve a requested provider effort explicitly or fail closed."""

    if requested == REQUESTED_REASONING_EFFORT:
        return EFFECTIVE_REASONING_EFFORT, {
            "requested_reasoning_effort": REQUESTED_REASONING_EFFORT,
            "effective_reasoning_effort": EFFECTIVE_REASONING_EFFORT,
            "compatibility_resolution": REASONING_EFFORT_COMPATIBILITY_RESOLUTION,
            "compatibility_reason": REASONING_EFFORT_COMPATIBILITY_REASON,
        }
    if isinstance(requested, str) and requested in SUPPORTED_HOSTED_REASONING_EFFORTS:
        return requested, {
            "requested_reasoning_effort": requested,
            "effective_reasoning_effort": requested,
            "compatibility_resolution": "ALREADY_SUPPORTED",
            "compatibility_reason": "Requested reasoning effort is natively supported",
        }
    raise HostedReasoningEffortCompatibilityError(requested)


def normalize_hosted_chat_body(
    path: str, body: bytes
) -> tuple[bytes, dict[str, Any] | None]:
    """Normalize only hosted chat reasoning effort; embeddings bypass this path."""

    request_path = path.partition("?")[0].rstrip("/")
    if not request_path.endswith("/chat/completions"):
        return body, None
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HostedReasoningEffortCompatibilityError("<INVALID_JSON>") from exc
    if not isinstance(payload, Mapping):
        raise HostedReasoningEffortCompatibilityError("<NON_OBJECT_REQUEST>")
    if "reasoning_effort" not in payload:
        return body, None
    effective, audit = resolve_hosted_reasoning_effort(payload["reasoning_effort"])
    normalized = dict(payload)
    normalized["reasoning_effort"] = effective
    return json.dumps(normalized, separators=(",", ":")).encode("utf-8"), audit


def resolve_local_embedding_snapshot(cache_root: Path) -> tuple[Path, str | None]:
    """Resolve one cached Hugging Face snapshot without network-capable APIs."""

    repository = "models--sentence-transformers--paraphrase-MiniLM-L3-v2"
    repositories = [cache_root / "hub" / repository, cache_root / repository]
    for root in repositories:
        snapshots = root / "snapshots"
        if not snapshots.is_dir():
            continue
        ref = root / "refs" / "main"
        if ref.is_file():
            revision = ref.read_text(encoding="utf-8").strip()
            if not re.fullmatch(r"[0-9a-fA-F]{40,64}", revision):
                raise LocalEmbeddingUnavailable(
                    "LOCAL_EMBEDDING_CACHE_INVALID: refs/main is not a revision"
                )
            resolved = snapshots / revision
            if not resolved.is_dir():
                raise LocalEmbeddingUnavailable(
                    "LOCAL_EMBEDDING_CACHE_INVALID: refs/main snapshot is absent"
                )
            return resolved.resolve(), revision.lower()
        candidates = sorted(path for path in snapshots.iterdir() if path.is_dir())
        if len(candidates) == 1:
            name = candidates[0].name
            revision = name.lower() if re.fullmatch(r"[0-9a-fA-F]{40,64}", name) else None
            return candidates[0].resolve(), revision
        if candidates:
            raise LocalEmbeddingUnavailable(
                "LOCAL_EMBEDDING_CACHE_AMBIGUOUS: multiple unpinned snapshots"
            )
    raise LocalEmbeddingUnavailable(
        "LOCAL_EMBEDDING_CACHE_MISSING: expected MiniLM-L3-v2 snapshot is absent"
    )


def fingerprint_local_model_artifacts(
    snapshot: Path, cache_root: Path
) -> tuple[str, int]:
    """Hash the complete resolved artifact set by relative path, size, and bytes."""

    artifacts: list[dict[str, Any]] = []
    for path in sorted(snapshot.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_file():
            try:
                path.resolve().relative_to(cache_root)
            except ValueError as exc:
                raise LocalEmbeddingUnavailable(
                    "LOCAL_EMBEDDING_CACHE_INVALID: model artifact escapes cache"
                ) from exc
            body = path.read_bytes()
            artifacts.append(
                {
                    "path": path.relative_to(snapshot).as_posix(),
                    "bytes": len(body),
                    "sha256": sha256_bytes(body),
                }
            )
    if not artifacts:
        raise LocalEmbeddingUnavailable(
            "LOCAL_EMBEDDING_CACHE_INVALID: resolved snapshot contains no files"
        )
    return sha256_bytes(canonical_json_bytes(artifacts)), len(artifacts)


class LocalSentenceTransformerEmbeddings:
    """Offline-only CPU embedding implementation behind the existing proxy."""

    def __init__(
        self,
        cache_root: Path,
        *,
        snapshot_path: Path | None = None,
        revision: str | None = None,
        model_factory: Any | None = None,
        installed_version: str | None = None,
    ) -> None:
        self.cache_root = cache_root.resolve()
        os.environ["HF_HOME"] = str(self.cache_root)
        os.environ["SENTENCE_TRANSFORMERS_HOME"] = str(self.cache_root)
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        try:
            observed_version = installed_version or package_version(
                "sentence-transformers"
            )
        except Exception as exc:
            raise LocalEmbeddingUnavailable(
                "LOCAL_EMBEDDING_PACKAGE_MISSING: sentence-transformers==6.1.0 required"
            ) from exc
        if observed_version != SENTENCE_TRANSFORMERS_VERSION:
            raise LocalEmbeddingUnavailable(
                "LOCAL_EMBEDDING_PACKAGE_MISMATCH: expected sentence-transformers=="
                + SENTENCE_TRANSFORMERS_VERSION
            )
        if snapshot_path is None:
            snapshot, resolved_revision = resolve_local_embedding_snapshot(
                self.cache_root
            )
        else:
            snapshot = snapshot_path.resolve()
            resolved_revision = revision
        try:
            snapshot.relative_to(self.cache_root)
        except ValueError as exc:
            raise LocalEmbeddingUnavailable(
                "LOCAL_EMBEDDING_CACHE_INVALID: snapshot escapes persistent cache"
            ) from exc
        self.snapshot = snapshot
        self.revision = resolved_revision
        self.artifact_fingerprint, self.artifact_file_count = (
            fingerprint_local_model_artifacts(snapshot, self.cache_root)
        )
        if model_factory is None:
            from sentence_transformers import SentenceTransformer

            model_factory = SentenceTransformer
        try:
            self.model = model_factory(
                str(snapshot),
                cache_folder=str(self.cache_root),
                device="cpu",
                local_files_only=True,
            )
        except Exception as exc:
            raise LocalEmbeddingUnavailable(
                "LOCAL_EMBEDDING_LOAD_FAILED: cached MiniLM-L3-v2 could not be loaded"
            ) from exc

    def provenance(self, *, observed_dimension: int | None = None) -> dict[str, Any]:
        return {
            "backend": "local_sentence_transformer",
            "execution_device": "cpu",
            "model_id": EMBEDDING_MODEL,
            "sentence_transformers_version": SENTENCE_TRANSFORMERS_VERSION,
            "local_snapshot_path": str(self.snapshot),
            "resolved_revision": self.revision,
            "artifact_fingerprint_sha256": self.artifact_fingerprint,
            "artifact_file_count": self.artifact_file_count,
            "offline_cache_only": True,
            "observed_dimension": observed_dimension,
        }

    def embed_request(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        unsupported = set(payload) - {
            "model",
            "input",
            "dimensions",
            "encoding_format",
        }
        if unsupported:
            raise LocalEmbeddingRequestError(
                "unsupported embedding request fields: "
                + ", ".join(sorted(str(item) for item in unsupported))
            )
        if payload.get("model") != EMBEDDING_MODEL:
            raise LocalEmbeddingRequestError("embedding model does not match exact pin")
        dimensions = payload.get("dimensions", EMBEDDING_VECTOR_DIMENSIONS)
        if (
            isinstance(dimensions, bool)
            or not isinstance(dimensions, int)
            or dimensions != EMBEDDING_VECTOR_DIMENSIONS
        ):
            raise LocalEmbeddingRequestError("embedding dimensions must equal 384")
        encoding = payload.get("encoding_format", "float")
        if encoding != "float":
            raise LocalEmbeddingRequestError("only float embedding encoding is supported")
        request_input = payload.get("input")
        if isinstance(request_input, str):
            inputs = [request_input]
        elif isinstance(request_input, list):
            inputs = request_input
        else:
            raise LocalEmbeddingRequestError("embedding input must be a string or list")
        if not inputs or any(not isinstance(item, str) or not item.strip() for item in inputs):
            raise LocalEmbeddingRequestError(
                "embedding input must contain non-empty strings"
            )
        try:
            encoded = self.model.encode(
                inputs,
                convert_to_numpy=True,
                show_progress_bar=False,
                normalize_embeddings=False,
            )
        except Exception as exc:
            raise LocalEmbeddingUnavailable("LOCAL_EMBEDDING_INFERENCE_FAILED") from exc
        rows = encoded.tolist() if hasattr(encoded, "tolist") else encoded
        if not isinstance(rows, list) or len(rows) != len(inputs):
            raise LocalEmbeddingRequestError("embedding model returned malformed output")
        data: list[dict[str, Any]] = []
        for index, row in enumerate(rows):
            if not isinstance(row, list) or len(row) != EMBEDDING_VECTOR_DIMENSIONS:
                raise LocalEmbeddingRequestError(
                    "embedding model returned a vector with the wrong dimension"
                )
            if any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                for value in row
            ):
                raise LocalEmbeddingRequestError(
                    "embedding model returned a non-finite or non-numeric vector"
                )
            data.append(
                {
                    "object": "embedding",
                    "embedding": [float(value) for value in row],
                    "index": index,
                }
            )
        return {"object": "list", "data": data, "model": EMBEDDING_MODEL}


class ModelBudgetProxy:
    """Count, cap, and split-route provider-internal OpenAI-compatible requests."""

    def __init__(
        self,
        embedding_backend: "LocalSentenceTransformerEmbeddings | None" = None,
        *,
        server_address: tuple[str, int] = ("0.0.0.0", 18081),
    ) -> None:
        self.lock = threading.Lock()
        self.calls: list[dict[str, Any]] = []
        self.budget_stop = False
        self.embedding_backend = embedding_backend
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

            def do_POST(self) -> None:  # noqa: N802
                if not model_proxy_client_allowed(self.client_address[0]):
                    self.send_response(403)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"error":{"message":"CLIENT_ORIGIN_REJECTED"}}')
                    return
                with owner.lock:
                    if len(owner.calls) >= MAX_MODEL_CALLS:
                        owner.budget_stop = True
                        self.send_response(429)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(b'{"error":{"message":"BUDGET_STOP"}}')
                        return
                    ordinal = len(owner.calls) + 1
                    request_path = self.path.partition("?")[0].rstrip("/")
                    is_embedding = request_path.endswith("/embeddings")
                    owner.calls.append(
                        {
                            "ordinal": ordinal,
                            "path": self.path,
                            "status_code": None,
                            "duration_seconds": None,
                            "success": False,
                            "role": "embedding" if is_embedding else "text_generation",
                            "backend": (
                                "local_sentence_transformer"
                                if is_embedding
                                else "jetstream_hosted"
                            ),
                            "usage": {},
                            "completed": False,
                        }
                    )
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length)
                started = time.monotonic()
                if is_embedding:
                    status_code, response_body, response_headers = (
                        owner._handle_local_embedding(body)
                    )
                    reasoning_effort_compatibility = None
                else:
                    (
                        status_code,
                        response_body,
                        response_headers,
                        reasoning_effort_compatibility,
                    ) = (
                        owner._forward_hosted(self.path, body, self.headers)
                    )
                usage: dict[str, Any] = {}
                try:
                    decoded = json.loads(response_body)
                    if isinstance(decoded, dict) and isinstance(decoded.get("usage"), dict):
                        usage = decoded["usage"]
                except json.JSONDecodeError:
                    pass
                with owner.lock:
                    call_update = {
                        "status_code": status_code,
                        "duration_seconds": round(time.monotonic() - started, 6),
                        "success": 200 <= status_code < 300,
                        "usage": usage,
                        "completed": True,
                    }
                    if reasoning_effort_compatibility is not None:
                        call_update["reasoning_effort_compatibility"] = (
                            reasoning_effort_compatibility
                        )
                    owner.calls[ordinal - 1].update(
                        call_update
                    )
                self.send_response(status_code)
                for key, value in response_headers.items():
                    if key.lower() not in {"transfer-encoding", "connection", "content-length"}:
                        self.send_header(key, value)
                self.send_header("Content-Length", str(len(response_body)))
                self.end_headers()
                self.wfile.write(response_body)

        self.server = http.server.ThreadingHTTPServer(server_address, Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def _handle_local_embedding(
        self, body: bytes
    ) -> tuple[int, bytes, dict[str, str]]:
        if self.embedding_backend is None:
            payload = {"error": {"message": "LOCAL_EMBEDDING_BACKEND_UNAVAILABLE"}}
            return 503, canonical_json_bytes(payload), {"Content-Type": "application/json"}
        try:
            decoded = json.loads(body)
            if not isinstance(decoded, Mapping):
                raise LocalEmbeddingRequestError("request body must be a JSON object")
            response = self.embedding_backend.embed_request(decoded)
            return 200, canonical_json_bytes(response), {"Content-Type": "application/json"}
        except (json.JSONDecodeError, LocalEmbeddingRequestError) as exc:
            payload = {
                "error": {
                    "message": str(exc),
                    "error_type": "LOCAL_EMBEDDING_REQUEST_REJECTED",
                }
            }
            return 400, canonical_json_bytes(payload), {"Content-Type": "application/json"}
        except LocalEmbeddingUnavailable as exc:
            payload = {
                "error": {
                    "message": str(exc),
                    "error_type": "LOCAL_EMBEDDING_PROVISIONING_BLOCKER",
                }
            }
            return 503, canonical_json_bytes(payload), {"Content-Type": "application/json"}

    @staticmethod
    def _forward_hosted(
        path: str, body: bytes, incoming_headers: Mapping[str, str]
    ) -> tuple[int, bytes, dict[str, str], dict[str, Any] | None]:
        try:
            outbound_body, compatibility = normalize_hosted_chat_body(path, body)
        except HostedReasoningEffortCompatibilityError as exc:
            payload = {
                "error": {
                    "message": str(exc),
                    "error_type": "HOSTED_REASONING_EFFORT_REJECTED",
                }
            }
            return (
                400,
                canonical_json_bytes(payload),
                {"Content-Type": "application/json"},
                exc.audit,
            )
        suffix = path[3:] if path.startswith("/v1") else path
        upstream = MODEL_ENDPOINT.rstrip("/") + suffix
        headers = {
            key: value
            for key, value in incoming_headers.items()
            if key.lower() not in {"host", "content-length", "connection"}
        }
        request = urllib.request.Request(
            upstream, data=outbound_body, headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=600) as response:
                return (
                    response.status,
                    response.read(),
                    dict(response.headers.items()),
                    compatibility,
                )
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(), dict(exc.headers.items()), compatibility
        except Exception as exc:
            payload = {
                "error": {
                    "message": "provider-internal endpoint request failed",
                    "error_type": type(exc).__name__,
                }
            }
            return (
                502,
                canonical_json_bytes(payload),
                {"Content-Type": "application/json"},
                compatibility,
            )

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=10)

    def accounting(self) -> dict[str, Any]:
        def total(*keys: str) -> int | str:
            values = []
            for call in self.calls:
                if call["backend"] != "jetstream_hosted":
                    continue
                usage = call["usage"]
                value = next((usage[key] for key in keys if isinstance(usage.get(key), int)), None)
                if value is None:
                    return "UNKNOWN"
                values.append(value)
            return sum(values)

        return {
            "provider_label": "split-backend-openai-compatible",
            "text_generation_model": TEXT_MODEL,
            "embedding_model": EMBEDDING_MODEL,
            "text_endpoint": "Jetstream gpt-oss endpoint",
            "embedding_endpoint": "local CPU sentence-transformer",
            "maximum_requests": MAX_MODEL_CALLS,
            "call_count": len(self.calls),
            "provider_internal_total_requests": len(self.calls),
            "text_generation_call_count": sum(
                call["role"] == "text_generation" for call in self.calls
            ),
            "hosted_text_generation_call_count": sum(
                call["backend"] == "jetstream_hosted" for call in self.calls
            ),
            "embedding_call_count": sum(
                call["role"] == "embedding" for call in self.calls
            ),
            "local_embedding_call_count": sum(
                call["backend"] == "local_sentence_transformer" for call in self.calls
            ),
            "local_embedding_success_count": sum(
                call["backend"] == "local_sentence_transformer" and call["success"]
                for call in self.calls
            ),
            "local_embedding_failure_count": sum(
                call["backend"] == "local_sentence_transformer" and not call["success"]
                for call in self.calls
            ),
            "input_tokens": total("prompt_tokens", "input_tokens"),
            "output_tokens": total("completion_tokens", "output_tokens"),
            "cache_tokens": "UNKNOWN",
            "budget_stop": self.budget_stop,
            "calls": self.calls,
        }


def transform_pinned_compose(compose_source: str, state: Path) -> str:
    """Rewrite only the exact audited v3.2.1 Compose shape, or fail closed."""

    expected_counts = {
        "      - lancedb-data:/app/lancedb_data": 2,
        "      - pgdata:/var/lib/postgresql/data/": 1,
        "      - redis-data:/data": 1,
        "  api:": 1,
        "  deriver:": 1,
    }
    source_lines = compose_source.splitlines()
    for pattern, expected in expected_counts.items():
        observed = source_lines.count(pattern)
        if observed != expected:
            raise RuntimeError(
                "pinned Honcho Compose shape mismatch for "
                f"{pattern.strip()!r}: expected {expected}, observed {observed}"
            )

    replacements = {
        "      - lancedb-data:/app/lancedb_data": (
            f"      - {state / 'lancedb'}:/app/lancedb_data"
        ),
        "      - pgdata:/var/lib/postgresql/data/": (
            f"      - {state / 'postgres'}:/var/lib/postgresql/data/"
        ),
        "      - redis-data:/data": f"      - {state / 'redis'}:/data",
    }
    transformed = compose_source
    for original, replacement in replacements.items():
        transformed = transformed.replace(original, replacement)
    transformed = transformed.replace(
        "  api:\n",
        '  api:\n    extra_hosts:\n      - "host.docker.internal:host-gateway"\n',
        1,
    ).replace(
        "  deriver:\n",
        '  deriver:\n    extra_hosts:\n      - "host.docker.internal:host-gateway"\n',
        1,
    )

    for original in replacements:
        if original in transformed:
            raise RuntimeError(f"original named-volume mount remains active: {original}")
    expected_transformed_counts = {
        replacements["      - lancedb-data:/app/lancedb_data"]: 2,
        replacements["      - pgdata:/var/lib/postgresql/data/"]: 1,
        replacements["      - redis-data:/data"]: 1,
        '      - "host.docker.internal:host-gateway"': 2,
    }
    transformed_lines = transformed.splitlines()
    for pattern, expected in expected_transformed_counts.items():
        observed = transformed_lines.count(pattern)
        if observed != expected:
            raise RuntimeError(
                "runtime Honcho Compose transform mismatch for "
                f"{pattern!r}: expected {expected}, observed {observed}"
            )
    return transformed


def runtime_environment_content(
    *, embedding_model: str = EMBEDDING_MODEL,
    embedding_vector_dimensions: int = EMBEDDING_VECTOR_DIMENSIONS,
) -> str:
    """Render only the authorized Phase 08B-1 runtime environment."""

    return (
        "\n".join(
            [
                "AUTH_USE_AUTH=false",
                "LLM_OPENAI_API_KEY=empty",
                "DERIVER_MODEL_CONFIG__TRANSPORT=openai",
                f"DERIVER_MODEL_CONFIG__MODEL={TEXT_MODEL}",
                f"DERIVER_MODEL_CONFIG__OVERRIDES__BASE_URL={PROXY_BASE_URL}",
                "DIALECTIC_LEVELS__minimal__MODEL_CONFIG__TRANSPORT=openai",
                f"DIALECTIC_LEVELS__minimal__MODEL_CONFIG__MODEL={TEXT_MODEL}",
                f"DIALECTIC_LEVELS__minimal__MODEL_CONFIG__OVERRIDES__BASE_URL={PROXY_BASE_URL}",
                "EMBEDDING_MODEL_CONFIG__TRANSPORT=openai",
                f"EMBEDDING_MODEL_CONFIG__MODEL={embedding_model}",
                f"EMBEDDING_MODEL_CONFIG__OVERRIDES__BASE_URL={PROXY_BASE_URL}",
                "EMBEDDING_MODEL_CONFIG__ENCODING_FORMAT_MODE=float",
                f"EMBEDDING_VECTOR_DIMENSIONS={embedding_vector_dimensions}",
                "DERIVER_WORKERS=1",
                "DERIVER_FLUSH_ENABLED=true",
                "DREAM_ENABLED=true",
                'DREAM_ENABLED_TYPES=["omni"]',
                "DREAM_DEDUCTION_MODEL_CONFIG__TRANSPORT=openai",
                f"DREAM_DEDUCTION_MODEL_CONFIG__MODEL={TEXT_MODEL}",
                f"DREAM_DEDUCTION_MODEL_CONFIG__OVERRIDES__BASE_URL={PROXY_BASE_URL}",
                "DREAM_DEDUCTION_MODEL_CONFIG__TEMPERATURE=0",
                "DREAM_DEDUCTION_MODEL_CONFIG__THINKING_EFFORT=minimal",
                "DREAM_INDUCTION_MODEL_CONFIG__TRANSPORT=openai",
                f"DREAM_INDUCTION_MODEL_CONFIG__MODEL={TEXT_MODEL}",
                f"DREAM_INDUCTION_MODEL_CONFIG__OVERRIDES__BASE_URL={PROXY_BASE_URL}",
                "DREAM_INDUCTION_MODEL_CONFIG__TEMPERATURE=0",
                "DREAM_INDUCTION_MODEL_CONFIG__THINKING_EFFORT=minimal",
                "METRICS_ENABLED=true",
            ]
        )
        + "\n"
    )


def write_runtime_files(
    provider: Path,
    state: Path,
    *,
    identity_sink: list[dict[str, Any]] | None = None,
) -> tuple[Path, Path]:
    compose_source = (provider / "docker-compose.yml.example").read_text(
        encoding="utf-8"
    )
    compose_source = transform_pinned_compose(compose_source, state)
    compose = provider / RUNTIME_COMPOSE_NAME
    with compose.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(compose_source)
    if identity_sink is not None:
        identity_sink.append(runtime_file_identity(compose))
    env = provider / RUNTIME_ENV_NAME
    env_content = runtime_environment_content()
    with env.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(env_content)
    if identity_sink is not None:
        identity_sink.append(runtime_file_identity(env))
    os.chmod(env, 0o600)
    return compose, env


def runtime_file_identity(path: Path) -> dict[str, Any]:
    """Create a deletion token only for an unambiguous regular file."""

    file_stat = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(file_stat.st_mode):
        raise RuntimeError(
            f"BLOCKED_UNRECOGNIZED_RUNTIME_RESIDUE_TYPE: {path.name}"
        )
    data = path.read_bytes()
    return {
        "path": str(path.resolve()),
        "sha256": sha256_bytes(data),
        "bytes": len(data),
        "mode": oct(stat.S_IMODE(file_stat.st_mode)),
    }


def capture_runtime_file_identities(paths: tuple[Path, ...]) -> list[dict[str, Any]]:
    return [runtime_file_identity(path) for path in paths]


def cleanup_runtime_files(
    identities: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Remove only exact attempt-owned bytes; never broaden the target set."""

    results: list[dict[str, Any]] = []
    blockers: list[str] = []
    for expected in identities:
        path = Path(str(expected["path"]))
        if not path.exists() and not path.is_symlink():
            results.append({"path": str(path), "status": "ALREADY_ABSENT"})
            continue
        try:
            observed = runtime_file_identity(path)
        except (OSError, RuntimeError):
            observed = None
        if (
            observed is None
            or observed["sha256"] != expected.get("sha256")
            or observed["bytes"] != expected.get("bytes")
        ):
            blocker = f"RUNTIME_FILE_IDENTITY_CHANGED: {path.name}"
            blockers.append(blocker)
            results.append(
                {
                    "path": str(path),
                    "status": "PRESERVED_IDENTITY_CHANGED",
                    "blocker": blocker,
                    "observed_identity": observed,
                }
            )
            continue
        path.unlink()
        results.append({"path": str(path), "status": "REMOVED"})
    return {
        "status": "PASS" if not blockers else "BLOCKED",
        "files": results,
        "blockers": blockers,
    }


def _recover_managed_compose_state(
    compose_text: str, *, mount: Path
) -> tuple[Path, str]:
    suffix = ":/var/lib/postgresql/data/"
    prefix = "      - "
    candidates = [
        line[len(prefix) : -len(suffix)]
        for line in compose_text.splitlines()
        if line.startswith(prefix) and line.endswith(suffix)
    ]
    if len(candidates) != 1:
        raise RuntimeError("BLOCKED_UNRECOGNIZED_RUNTIME_COMPOSE_STATE")
    postgres_path = Path(candidates[0]).resolve()
    if postgres_path.name != "postgres":
        raise RuntimeError("BLOCKED_UNRECOGNIZED_RUNTIME_COMPOSE_STATE")
    state = postgres_path.parent
    attempts_root = (
        mount.resolve() / "memlife" / "runs" / "phase08b" / "attempts"
    )
    try:
        relative = state.relative_to(attempts_root)
    except ValueError as exc:
        raise RuntimeError(
            "BLOCKED_UNRECOGNIZED_RUNTIME_COMPOSE_STATE_SCOPE"
        ) from exc
    if len(relative.parts) != 2 or relative.parts[1] != "provider-state":
        raise RuntimeError("BLOCKED_UNRECOGNIZED_RUNTIME_COMPOSE_STATE_SCOPE")
    return state, relative.parts[0]


def classify_managed_runtime_residue(
    provider: Path, *, mount: Path
) -> dict[str, Any]:
    """Recognize only exact Candidate8/Candidate9 runtime-file residue."""

    env = provider / RUNTIME_ENV_NAME
    compose = provider / RUNTIME_COMPOSE_NAME
    present = [
        path for path in (env, compose) if path.exists() or path.is_symlink()
    ]
    if not present:
        return {
            "status": "NO_RESIDUE",
            "files": [],
            "cleanup_tokens": [],
            "prior_state_path": None,
            "prior_attempt_id": None,
            "redacted_parsed_environment": None,
            "compose_sha256": None,
        }

    files: list[dict[str, Any]] = []
    cleanup_tokens: list[dict[str, Any]] = []
    redacted_environment: dict[str, Any] | None = None
    redacted_paths: list[str] = []
    prior_state_path: str | None = None
    prior_attempt_id: str | None = None
    compose_sha256: str | None = None

    if env in present:
        identity = runtime_file_identity(env)
        observed = env.read_bytes()
        authorized = {
            runtime_environment_content(
                embedding_model=CANDIDATE8_EMBEDDING_MODEL,
                embedding_vector_dimensions=CANDIDATE8_EMBEDDING_VECTOR_DIMENSIONS,
            ).encode("utf-8"): "PHASE08B1_CANDIDATE8_RUNTIME_ENV",
            runtime_environment_content().encode("utf-8"): (
                "PHASE08B1_CANDIDATE9_RUNTIME_ENV"
            ),
        }
        classification = authorized.get(observed)
        if classification is None:
            raise RuntimeError("BLOCKED_UNRECOGNIZED_RUNTIME_ENV_RESIDUE")
        redacted_environment, redacted_paths = declared_runtime_environment(env)
        files.append({**identity, "classification": classification})
        cleanup_tokens.append(identity)

    if compose in present:
        identity = runtime_file_identity(compose)
        compose_text = compose.read_text(encoding="utf-8")
        state, attempt_id = _recover_managed_compose_state(
            compose_text, mount=mount
        )
        pinned_source = (provider / "docker-compose.yml.example").read_text(
            encoding="utf-8"
        )
        expected = transform_pinned_compose(pinned_source, state)
        if compose.read_bytes() != expected.encode("utf-8"):
            raise RuntimeError("BLOCKED_UNRECOGNIZED_RUNTIME_COMPOSE_RESIDUE")
        prior_state_path = str(state)
        prior_attempt_id = attempt_id
        compose_sha256 = identity["sha256"]
        files.append(
            {**identity, "classification": "PHASE08B1_RUNTIME_COMPOSE"}
        )
        cleanup_tokens.append(identity)

    return {
        "status": "RECOGNIZED_MANAGED_RESIDUE",
        "files": files,
        "cleanup_tokens": cleanup_tokens,
        "prior_state_path": prior_state_path,
        "prior_attempt_id": prior_attempt_id,
        "redacted_parsed_environment": redacted_environment,
        "redacted_paths": redacted_paths,
        "compose_sha256": compose_sha256,
    }


def preserve_and_remove_managed_runtime_residue(
    provider: Path, *, mount: Path, attempt_root: Path
) -> dict[str, Any]:
    """Write verified secret-safe evidence before exact identity-token cleanup."""

    classified = classify_managed_runtime_residue(provider, mount=mount)
    if classified["status"] == "NO_RESIDUE":
        return {**classified, "evidence_artifact": None, "evidence_sha256": None}
    evidence = {
        "schema_version": "phase08b1-preexisting-runtime-residue-v1",
        "status": classified["status"],
        "files": classified["files"],
        "prior_state_path": classified["prior_state_path"],
        "prior_attempt_id": classified["prior_attempt_id"],
        "redacted_parsed_environment": classified[
            "redacted_parsed_environment"
        ],
        "redacted_paths": classified["redacted_paths"],
        "compose_sha256": classified["compose_sha256"],
    }
    evidence_path = attempt_root / "preexisting-runtime-residue.json"
    evidence_sha = write_json_exclusive(evidence_path, evidence)
    if sha256_bytes(evidence_path.read_bytes()) != evidence_sha:
        raise RuntimeError("preexisting runtime residue evidence verification failed")
    cleanup = cleanup_runtime_files(classified["cleanup_tokens"])
    if cleanup["status"] != "PASS":
        raise RuntimeError("BLOCKED_PREEXISTING_RUNTIME_RESIDUE_IDENTITY_CHANGED")
    return {
        **classified,
        "cleanup": cleanup,
        "evidence_artifact": evidence_path.name,
        "evidence_sha256": evidence_sha,
    }


def validate_provider_source_checkout(
    provider: Path, *, expected_commit: str = UPSTREAM_COMMIT
) -> dict[str, Any]:
    """Fail closed on any source identity or pre-build checkout ambiguity."""

    observed_commit = run(["git", "rev-parse", "HEAD"], cwd=provider).strip()
    if observed_commit != expected_commit:
        raise RuntimeError("BLOCKED_PROVIDER_VERSION_PIN: upstream checkout mismatch")
    try:
        run(["git", "diff", "--quiet", "HEAD", "--"], cwd=provider)
        run(["git", "diff", "--cached", "--quiet"], cwd=provider)
    except RuntimeError as exc:
        raise RuntimeError("BLOCKED_PROVIDER_TRACKED_SOURCE_DIRTY") from exc
    untracked_output = run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=provider,
    )
    untracked = sorted(item for item in untracked_output.split("\0") if item)
    if untracked:
        raise RuntimeError(
            "BLOCKED_PROVIDER_UNTRACKED_BUILD_INPUT: " + ", ".join(untracked)
        )
    tree_id = run(["git", "rev-parse", "HEAD^{tree}"], cwd=provider).strip()
    if len(tree_id) != 40:
        raise RuntimeError("BLOCKED_PROVIDER_TREE_ID_UNAVAILABLE")
    return {
        "observed_commit": observed_commit,
        "git_tree": tree_id,
        "tracked_source_clean": True,
        "cached_source_clean": True,
        "untracked_files": [],
    }


def provider_version_identity_complete(payload: Mapping[str, Any]) -> bool:
    tree_id = payload.get("git_tree")
    images = payload.get("image_digests")
    return (
        payload.get("observed_commit") == UPSTREAM_COMMIT
        and isinstance(tree_id, str)
        and len(tree_id) == 40
        and payload.get("tracked_source_clean") is True
        and payload.get("cached_source_clean") is True
        and payload.get("untracked_files") == []
        and isinstance(images, list)
        and bool(images)
        and all(
            isinstance(image, Mapping)
            and isinstance(image.get("identity"), str)
            and bool(image["identity"])
            for image in images
        )
    )


def parse_compose_image_identities(output: str) -> list[dict[str, Any]]:
    """Normalize Compose JSON while requiring an exact image ID or digest."""

    stripped = output.strip()
    if not stripped:
        raise RuntimeError("executing Honcho image identity was not observable")
    try:
        decoded = json.loads(stripped)
        raw_items = decoded if isinstance(decoded, list) else [decoded]
    except json.JSONDecodeError:
        raw_items = [json.loads(line) for line in stripped.splitlines() if line]
    identities: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, Mapping):
            raise RuntimeError("Compose image identity output was not an object")
        identity = item.get("ID") or item.get("Digest")
        if not isinstance(identity, str) or not identity:
            raise RuntimeError("Compose image identity omitted ID/digest")
        identities.append({"identity": identity, "compose_record": dict(item)})
    if not identities:
        raise RuntimeError("executing Honcho image identity was not observable")
    return identities


def _is_sensitive_setting_component(component: object) -> bool:
    normalized = str(component).strip().lower().replace("-", "_")
    return normalized in SENSITIVE_SETTING_COMPONENTS or any(
        normalized.endswith("_" + item)
        for item in SENSITIVE_SETTING_COMPONENTS
    )


def redact_secret_settings(
    value: Any, *, path: tuple[str, ...] = ()
) -> tuple[Any, list[str]]:
    """Recursively redact credentials without hiding scientific tuning data."""

    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        redacted_paths: list[str] = []
        for key, child in value.items():
            key_text = str(key)
            child_path = (*path, key_text)
            if _is_sensitive_setting_component(key_text):
                redacted[key_text] = REDACTED_VALUE
                redacted_paths.append(".".join(child_path))
            else:
                redacted[key_text], child_paths = redact_secret_settings(
                    child, path=child_path
                )
                redacted_paths.extend(child_paths)
        return redacted, sorted(redacted_paths)
    if isinstance(value, list):
        redacted_items: list[Any] = []
        redacted_paths = []
        for index, child in enumerate(value):
            redacted_child, child_paths = redact_secret_settings(
                child, path=(*path, str(index))
            )
            redacted_items.append(redacted_child)
            redacted_paths.extend(child_paths)
        return redacted_items, sorted(redacted_paths)
    if isinstance(value, str) and "://" in value:
        scheme, remainder = value.split("://", 1)
        authority, separator, suffix = remainder.partition("/")
        if "@" in authority:
            host = authority.rsplit("@", 1)[1]
            sanitized = f"{scheme}://{REDACTED_VALUE}@{host}"
            if separator:
                sanitized += "/" + suffix
            return sanitized, [".".join(path)]
    return value, []


def declared_runtime_environment(env: Path) -> tuple[dict[str, Any], list[str]]:
    """Return every generated env input, redacting secret-designated names."""

    values: dict[str, str] = {}
    for line in env.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not key:
            raise RuntimeError("generated runtime env contains an invalid line")
        values[key] = value
    redacted, paths = redact_secret_settings(values, path=("runtime_environment",))
    if not isinstance(redacted, dict):
        raise RuntimeError("declared runtime environment was not an object")
    return redacted, paths


def initial_provider_configuration() -> dict[str, Any]:
    """Create the write-once artifact state used by incomplete Stage-A runs."""

    return {
        "schema_version": "phase08b1-provider-config-v2",
        "provider": "honcho",
        "version": "3.2.1",
        "declared_configuration": {"status": "NOT_MATERIALIZED"},
        "declared_runtime_env_sha256": None,
        "transformed_compose_sha256": None,
        "effective_api_configuration_artifact": EFFECTIVE_CONFIG_ARTIFACTS["api"],
        "effective_api_configuration_sha256": None,
        "effective_deriver_configuration_artifact": EFFECTIVE_CONFIG_ARTIFACTS[
            "deriver"
        ],
        "effective_deriver_configuration_sha256": None,
        "redacted_paths": {"declared": [], "api": [], "deriver": []},
        "effective_shared_configuration_matches": None,
        "unresolved_configuration_defaults": [
            "effective API AppSettings not observed",
            "effective deriver AppSettings not observed",
        ],
        "effective_configuration_status": "NOT_OBSERVED",
        "runtime_verified": False,
    }


def build_declared_provider_configuration(
    *,
    compose_project: str,
    provider: Path,
    state: Path,
    compose: Path,
    env: Path,
    provider_version: Mapping[str, Any],
) -> dict[str, Any]:
    """Preserve all attempt-owned inputs without calling them effective defaults."""

    runtime_environment, redacted_paths = declared_runtime_environment(env)
    payload = initial_provider_configuration()
    payload.update(
        declared_configuration={
            "status": "PRESERVED",
            "compose_project": compose_project,
            "runtime_environment": runtime_environment,
            "provider_source": {
                "path": str(provider),
                "commit": provider_version.get("observed_commit"),
                "git_tree": provider_version.get("git_tree"),
                "tracked_source_clean": provider_version.get("tracked_source_clean"),
                "cached_source_clean": provider_version.get("cached_source_clean"),
                "untracked_files": provider_version.get("untracked_files"),
            },
            "state_paths": {
                "root": str(state),
                "postgres": str(state / "postgres"),
                "redis": str(state / "redis"),
                "lancedb": str(state / "lancedb"),
            },
            "transformed_compose": {
                "artifact": str(compose),
                "sha256": sha256_bytes(compose.read_bytes()),
            },
            "live_compatibility_evidence": "stage-a-preflight.json",
            "dream_operation_budget": DREAM_OPERATION_BUDGET,
            "dream_purpose": PROVENANCE_PROBE_PURPOSE,
            "provider_internal_request_budget": MAX_MODEL_CALLS,
            "downstream_model_calls": 0,
            "rq3_calls": 0,
        },
        declared_runtime_env_sha256=sha256_bytes(env.read_bytes()),
        transformed_compose_sha256=sha256_bytes(compose.read_bytes()),
        redacted_paths={"declared": redacted_paths, "api": [], "deriver": []},
    )
    return payload


def capture_effective_settings(
    compose_cmd: list[str], provider: Path, service: str
) -> dict[str, Any]:
    """Capture already-redacted AppSettings from one running owned service."""

    if service not in EFFECTIVE_CONFIG_ARTIFACTS:
        raise ValueError(f"unsupported effective-settings service: {service}")
    output = run(
        [
            *compose_cmd,
            "exec",
            "-T",
            service,
            "/app/.venv/bin/python",
            "-c",
            EFFECTIVE_SETTINGS_CAPTURE_CODE,
        ],
        cwd=provider,
        timeout=120,
    )
    prefix = "PHASE08B1_EFFECTIVE_CONFIG="
    encoded = next(
        (
            line[len(prefix) :]
            for line in reversed(output.splitlines())
            if line.startswith(prefix)
        ),
        None,
    )
    if encoded is None:
        raise RuntimeError(f"effective {service} AppSettings marker was absent")
    decoded = json.loads(encoded)
    if not isinstance(decoded, Mapping):
        raise RuntimeError(f"effective {service} AppSettings payload was not an object")
    settings = decoded.get("effective_settings")
    paths = decoded.get("redacted_paths")
    digest = decoded.get("effective_settings_sha256")
    if not isinstance(settings, Mapping) or not isinstance(paths, list):
        raise RuntimeError(f"effective {service} AppSettings payload was incomplete")
    host_redacted, host_paths = redact_secret_settings(settings)
    if host_redacted != settings or sorted(paths) != host_paths:
        raise RuntimeError(f"effective {service} AppSettings was not safely redacted")
    expected_digest = sha256_bytes(canonical_json_bytes(settings))
    if digest != expected_digest:
        raise RuntimeError(f"effective {service} AppSettings digest mismatch")
    return {
        "schema_version": "phase08b1-effective-honcho-settings-v1",
        "service": service,
        "status": "OBSERVED",
        "effective_settings": dict(settings),
        "redacted_paths": host_paths,
        "effective_settings_sha256": expected_digest,
    }


def effective_shared_configuration_matches(
    api_payload: Mapping[str, Any], deriver_payload: Mapping[str, Any]
) -> bool:
    """Require exact equality for AppSettings shared by the Compose/env contract."""

    return (
        api_payload.get("status") == "OBSERVED"
        and deriver_payload.get("status") == "OBSERVED"
        and api_payload.get("effective_settings")
        == deriver_payload.get("effective_settings")
    )


def provider_configuration_support_ready(
    payload: Mapping[str, Any], *, provider_healthy: bool
) -> bool:
    """Return true only after declared and effective configuration evidence closes."""

    declared = payload.get("declared_configuration")
    return (
        provider_healthy
        and isinstance(declared, Mapping)
        and declared.get("status") == "PRESERVED"
        and isinstance(payload.get("declared_runtime_env_sha256"), str)
        and isinstance(payload.get("transformed_compose_sha256"), str)
        and isinstance(payload.get("effective_api_configuration_sha256"), str)
        and isinstance(payload.get("effective_deriver_configuration_sha256"), str)
        and payload.get("effective_shared_configuration_matches") is True
        and payload.get("unresolved_configuration_defaults") == []
        and payload.get("effective_configuration_status") == "VERIFIED"
    )


def native_message_ids(payload: object) -> list[str] | None:
    """Return exact native IDs, or None when the list response is ambiguous."""

    if not isinstance(payload, Mapping) or not isinstance(payload.get("items"), list):
        return None
    ids: list[str] = []
    for item in payload["items"]:
        if not isinstance(item, Mapping) or not isinstance(item.get("id"), str):
            return None
        ids.append(item["id"])
    return ids


def classify_restart_persistence(
    created_native_id: str,
    pre_restart_ids: list[str] | None,
    post_restart_ids: list[str] | None,
    *,
    restart_healthy: bool,
) -> CapabilityClassification:
    """Classify persistence only from the exact written native message ID."""

    if not created_native_id or pre_restart_ids is None:
        return CapabilityClassification.UNKNOWN
    if created_native_id not in pre_restart_ids:
        return CapabilityClassification.UNKNOWN
    if not restart_healthy or post_restart_ids is None:
        return CapabilityClassification.UNKNOWN
    if created_native_id in post_restart_ids:
        return CapabilityClassification.SUPPORTED
    return CapabilityClassification.UNSUPPORTED


def model_endpoint_preflight_plan() -> dict[str, Any]:
    """Exact compatibility calls reserved for a later authorized Stage A."""

    return {
        "counts_as": "provider-internal preflight calls",
        "maximum_requests_including_preflight_and_provider": MAX_MODEL_CALLS,
        "text_generation": {
            "method": "POST",
            "path": "/v1/chat/completions",
            "model": TEXT_MODEL,
            "temperature": "omitted (effective Honcho value is None)",
            "max_tokens": 2500,
            "structured_output_mode": "json_schema",
            "strict_json_schema": True,
            "required_feature": "json_schema structured output for PromptRepresentation",
        },
        "embedding": {
            "method": "POST",
            "path": "/v1/embeddings",
            "model": EMBEDDING_MODEL,
            "backend": "local_sentence_transformer",
            "execution_device": "cpu",
            "offline_cache_only": True,
            "hosted_forwarding": False,
            "required_vector_dimensions": EMBEDDING_VECTOR_DIMENSIONS,
            "required": True,
        },
        "dream_tool_calling": {
            "method": "POST",
            "path": "/v1/chat/completions",
            "model": TEXT_MODEL,
            "temperature": 0,
            "requested_reasoning_effort": REQUESTED_REASONING_EFFORT,
            "effective_reasoning_effort": EFFECTIVE_REASONING_EFFORT,
            "compatibility_resolution": REASONING_EFFORT_COMPATIBILITY_RESOLUTION,
            "compatibility_reason": REASONING_EFFORT_COMPATIBILITY_REASON,
            "max_tokens": 8192,
            "required_feature": "OpenAI-compatible tool calling",
            "required": True,
        },
    }


def _preflight_post(path: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        "http://127.0.0.1:18081" + path,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": PREFLIGHT_AUTHORIZATION,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            status = response.status
            body = response.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = exc.read()
    if not 200 <= status < 300:
        detail = body.decode("utf-8", errors="replace")[-2000:]
        raise RuntimeError(f"model endpoint preflight {path} returned {status}: {detail}")
    decoded = json.loads(body)
    if not isinstance(decoded, dict):
        raise RuntimeError(f"model endpoint preflight {path} returned a non-object")
    return decoded


def run_model_endpoint_preflight(
    embedding_backend: LocalSentenceTransformerEmbeddings | None = None,
) -> dict[str, Any]:
    """Execute only the model features used by the pinned Honcho paths."""

    structured = _preflight_post(
        "/v1/chat/completions",
        {
            "model": TEXT_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": "Return one fictional explicit observation as JSON.",
                }
            ],
            "max_tokens": 2500,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "PromptRepresentation",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "explicit": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {"content": {"type": "string"}},
                                    "required": ["content"],
                                    "additionalProperties": False,
                                },
                            }
                        },
                        "required": ["explicit"],
                        "additionalProperties": False,
                    },
                },
            },
        },
    )
    validate_structured_output_response(structured)

    embedding = _preflight_post(
        "/v1/embeddings",
        {
            "model": EMBEDDING_MODEL,
            "input": ["Fictional Phase 08B-1 embedding compatibility probe."],
            "encoding_format": "float",
            "dimensions": EMBEDDING_VECTOR_DIMENSIONS,
        },
    )
    data = embedding.get("data")
    vector = data[0].get("embedding") if isinstance(data, list) and data else None
    if not isinstance(vector, list) or len(vector) != EMBEDDING_VECTOR_DIMENSIONS:
        raise RuntimeError(
            "embedding preflight did not return the configured 384 dimensions"
        )

    tool_response = _preflight_post(
        "/v1/chat/completions",
        {
            "model": TEXT_MODEL,
            "messages": [{"role": "user", "content": "Call finish_preflight now."}],
            "max_tokens": 8192,
            "temperature": 0,
            "reasoning_effort": REQUESTED_REASONING_EFFORT,
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "finish_preflight",
                        "description": "Finish the compatibility preflight.",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "additionalProperties": False,
                        },
                    },
                }
            ],
            "tool_choice": "required",
        },
    )
    validate_dream_tool_response(tool_response)

    embedding_provenance = (
        embedding_backend.provenance(observed_dimension=len(vector))
        if embedding_backend is not None
        else {
            "backend": "local_sentence_transformer",
            "model_id": EMBEDDING_MODEL,
            "offline_cache_only": True,
            "observed_dimension": len(vector),
        }
    )
    return {
        "status": "PASS",
        "structured_output_supported": True,
        "structured_output_mode": "json_schema",
        "structured_output_strict": True,
        "deriver_temperature_omitted": True,
        "embedding_supported": True,
        "embedding_vector_dimensions": len(vector),
        "text_backend": "jetstream_hosted",
        "text_model": TEXT_MODEL,
        "embedding_backend": "local_sentence_transformer",
        "embedding_model": EMBEDDING_MODEL,
        "embedding_offline_cache_only": True,
        "hosted_embedding_forwarding": False,
        "embedding_provenance": embedding_provenance,
        "dream_tool_calling_supported": True,
        "requested_reasoning_effort": REQUESTED_REASONING_EFFORT,
        "effective_reasoning_effort": EFFECTIVE_REASONING_EFFORT,
        "compatibility_resolution": REASONING_EFFORT_COMPATIBILITY_RESOLUTION,
        "compatibility_reason": REASONING_EFFORT_COMPATIBILITY_REASON,
    }


def static_stage_a_preflight(provider: Path, compose: Path) -> dict[str, Any]:
    """Validate pinned source/config before any provider startup or model call."""

    audit = load_static_api_audit()
    audit_errors = validate_static_api_audit(audit)
    compose_check = run(
        ["docker", "compose", "-f", str(compose), "config", "--quiet"],
        cwd=provider,
        timeout=120,
    )
    blockers = list(audit_errors)
    return {
        "schema_version": "phase08b1-stage-a-preflight-v1",
        "status": "BLOCKED" if blockers else "STATIC_PASS_MODEL_COMPATIBILITY_PENDING",
        "scientific_provider_contact": False,
        "provider_internal_model_calls": 0,
        "downstream_model_calls": 0,
        "rq3_calls": 0,
        "upstream_tag": UPSTREAM_TAG,
        "upstream_commit": UPSTREAM_COMMIT,
        "static_api_audit_sha256": sha256_bytes(canonical_json_bytes(audit)),
        "config_schema_validated": not audit_errors,
        "config_schema_basis": "pinned src/config.py and schemas/config/v1.json",
        "compose_config_parsed": True,
        "embedding_assessment": CURRENT_EMBEDDING_ASSESSMENT,
        "split_backend": {
            "text": {"backend": "jetstream_hosted", "model": TEXT_MODEL},
            "embedding": {
                "backend": "local_sentence_transformer",
                "model": EMBEDDING_MODEL,
                "dimensions": EMBEDDING_VECTOR_DIMENSIONS,
                "execution_device": "cpu",
                "offline_cache_only": True,
                "hosted_forwarding": False,
            },
        },
        "embedding_compatibility_call_executed": False,
        "dream_config_change_authorized": DREAM_CONFIG_CHANGE_AUTHORIZED,
        "deriver_flush_change_authorized": DERIVER_FLUSH_CHANGE_AUTHORIZED,
        "model_endpoint_preflight_plan": model_endpoint_preflight_plan(),
        "blockers": blockers,
    }


def wait_health(raw: RawLog, contact_state: ProviderContactState) -> dict[str, Any]:
    deadline = time.monotonic() + 300
    last = "not contacted"
    while time.monotonic() < deadline:
        try:
            contact_state.mark_health_attempted()
            response = raw.request("GET", "health", name="health", expected={200})
            if isinstance(response, dict) and response.get("status") == "ok":
                contact_state.mark_api_health_passed()
            return response
        except Exception as exc:
            last = str(exc)
            time.sleep(5)
    raise RuntimeError(f"Honcho health did not become ready: {last}")


def observe_required_provider_health(
    compose_cmd: list[str],
    provider: Path,
    *,
    phase: str,
    api_health_payload: object,
    api_health_raw_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind API health to exact run-owned required-service liveness."""

    output = run(
        [*compose_cmd, "ps", "--services", "--status", "running"],
        cwd=provider,
        timeout=120,
    )
    observed = sorted({line.strip() for line in output.splitlines() if line.strip()})
    required = list(REQUIRED_COMPOSE_SERVICES)
    states = {service: service in observed for service in required}
    api_health_passed = (
        isinstance(api_health_payload, Mapping)
        and api_health_payload.get("status") == "ok"
    )
    passed = api_health_passed and all(states.values())
    return {
        "phase": phase,
        "timestamp": now(),
        "required_service_names": required,
        "observed_running_service_names": observed,
        "api_health_passed": api_health_passed,
        "api_health_raw_evidence": dict(api_health_raw_evidence),
        "api_running": states["api"],
        "deriver_running": states["deriver"],
        "database_running": states["database"],
        "redis_running": states["redis"],
        "optional_mcp_running": "mcp" in observed,
        "decision": "PASS" if passed else "FAIL",
        "passed": passed,
    }


def require_required_provider_health(observation: Mapping[str, Any]) -> None:
    """Stop the lifecycle before probes if any required service is not live."""

    if observation.get("passed") is True:
        return
    missing = [
        service
        for service in REQUIRED_COMPOSE_SERVICES
        if observation.get(f"{service}_running") is not True
    ]
    if observation.get("api_health_passed") is not True:
        missing.append("api:/health")
    raise RuntimeError(
        "BLOCKED_PROVIDER_REQUIRED_SERVICE_HEALTH: " + ", ".join(missing)
    )


def prove_fresh_run_owned_provider_state(state: Path, attempt_root: Path) -> dict[str, Any]:
    """Prove the bootstrap target is this new attempt and has no prior state."""

    resolved_state = state.resolve()
    resolved_attempt = attempt_root.resolve()
    if (
        resolved_state != resolved_attempt / "provider-state"
        or resolved_attempt.parent.name != "attempts"
        or not (resolved_attempt / "bound-runtime-manifest.json").is_file()
    ):
        raise RuntimeError("PGVECTOR_BOOTSTRAP_STATE_NOT_RUN_OWNED")
    expected = {"postgres", "redis", "lancedb"}
    observed = {path.name for path in resolved_state.iterdir()}
    if observed != expected:
        raise RuntimeError("PGVECTOR_BOOTSTRAP_STATE_SHAPE_INVALID")
    nonempty = [
        child.name
        for child in resolved_state.iterdir()
        if child.is_file() or any(child.iterdir())
    ]
    if nonempty:
        raise RuntimeError(
            "PGVECTOR_BOOTSTRAP_REFUSES_NONEMPTY_STATE: " + ", ".join(sorted(nonempty))
        )
    return {
        "run_owned_state": True,
        "state_path": str(resolved_state),
        "initial_state_empty": True,
    }


def bootstrap_pgvector_schema(
    compose_cmd: list[str],
    provider: Path,
    state: Path,
    attempt_root: Path,
    *,
    run_command: Any = run,
    sleep_command: Any = time.sleep,
) -> dict[str, Any]:
    """Bootstrap the pinned empty pgvector schema before API/deriver startup."""

    evidence = prove_fresh_run_owned_provider_state(state, attempt_root)
    run_command([*compose_cmd, "up", "-d", "database"], cwd=provider, timeout=1800)
    database_ready = False
    for _ in range(60):
        try:
            run_command(
                [
                    *compose_cmd,
                    "exec",
                    "-T",
                    "database",
                    "pg_isready",
                    "-U",
                    "postgres",
                    "-d",
                    "postgres",
                ],
                cwd=provider,
                timeout=30,
            )
            database_ready = True
            break
        except RuntimeError:
            sleep_command(2)
    if not database_ready:
        raise RuntimeError("PGVECTOR_BOOTSTRAP_DATABASE_NOT_READY")
    run_command([*compose_cmd, "build", "api"], cwd=provider, timeout=3600)
    container_python = "/app/.venv/bin/python"
    run_command(
        [
            *compose_cmd,
            "run",
            "--rm",
            "--no-deps",
            "--entrypoint",
            container_python,
            "api",
            "-m",
            "alembic",
            "upgrade",
            "head",
        ],
        cwd=provider,
        timeout=1800,
    )
    empty_query = (
        "SELECT SUM(n) FROM ("
        "SELECT COUNT(*) n FROM public.workspaces UNION ALL "
        "SELECT COUNT(*) FROM public.peers UNION ALL "
        "SELECT COUNT(*) FROM public.sessions UNION ALL "
        "SELECT COUNT(*) FROM public.session_peers UNION ALL "
        "SELECT COUNT(*) FROM public.messages UNION ALL "
        "SELECT COUNT(*) FROM public.collections UNION ALL "
        "SELECT COUNT(*) FROM public.documents UNION ALL "
        "SELECT COUNT(*) FROM public.document_sources UNION ALL "
        "SELECT COUNT(*) FROM public.message_embeddings UNION ALL "
        "SELECT COUNT(*) FROM public.queue UNION ALL "
        "SELECT COUNT(*) FROM public.active_queue_sessions UNION ALL "
        "SELECT COUNT(*) FROM public.webhook_endpoints"
        ") AS phase08b1_rows;"
    )
    observed_rows = run_command(
        [
            *compose_cmd,
            "exec",
            "-T",
            "database",
            "psql",
            "-U",
            "postgres",
            "-d",
            "postgres",
            "-At",
            "-c",
            empty_query,
        ],
        cwd=provider,
        timeout=120,
    ).strip()
    if observed_rows != "0":
        raise RuntimeError(
            "PGVECTOR_BOOTSTRAP_REFUSES_POPULATED_DATABASE: " + observed_rows
        )
    configure_base = [
        *compose_cmd,
        "run",
        "--rm",
        "--no-deps",
        "--entrypoint",
        container_python,
        "api",
        "scripts/configure_embeddings.py",
    ]
    dry_run_output = run_command(
        [*configure_base, "--dry-run"], cwd=provider, timeout=300
    )
    apply_output = run_command(
        [*configure_base, "--yes"], cwd=provider, timeout=300
    )
    dimension_query = (
        "SELECT c.relname || '|' || a.atttypmod "
        "FROM pg_attribute a JOIN pg_class c ON a.attrelid=c.oid "
        "JOIN pg_namespace n ON c.relnamespace=n.oid "
        "WHERE n.nspname='public' AND c.relname IN "
        "('documents','message_embeddings') AND a.attname='embedding' "
        "ORDER BY c.relname;"
    )
    dimension_output = run_command(
        [
            *compose_cmd,
            "exec",
            "-T",
            "database",
            "psql",
            "-U",
            "postgres",
            "-d",
            "postgres",
            "-At",
            "-c",
            dimension_query,
        ],
        cwd=provider,
        timeout=120,
    )
    dimensions: dict[str, int] = {}
    for line in dimension_output.splitlines():
        table, separator, value = line.strip().partition("|")
        if separator and value.isdigit():
            dimensions[table] = int(value)
    expected_dimensions = {
        "documents": EMBEDDING_VECTOR_DIMENSIONS,
        "message_embeddings": EMBEDDING_VECTOR_DIMENSIONS,
    }
    if dimensions != expected_dimensions:
        raise RuntimeError(
            "PGVECTOR_BOOTSTRAP_DIMENSION_VERIFICATION_FAILED: "
            + json.dumps(dimensions, sort_keys=True)
        )
    return {
        **evidence,
        "status": "PASS",
        "migrations_applied": True,
        "database_row_count_before_configuration": 0,
        "configure_embeddings_script": "scripts/configure_embeddings.py",
        "configure_embeddings_dry_run_completed": dry_run_output is not None,
        "configure_embeddings_apply_completed": apply_output is not None,
        "verified_dimensions": dimensions,
        "api_deriver_start_authorized": True,
    }


def require_effective_settings_capture(
    payloads: Mapping[str, Mapping[str, Any]],
) -> None:
    """Treat run-owned runtime-introspection failure as operational."""

    failed = [
        service
        for service in EFFECTIVE_CONFIG_ARTIFACTS
        if payloads.get(service, {}).get("status") != "OBSERVED"
    ]
    if failed:
        raise RuntimeError(
            "BLOCKED_EFFECTIVE_CONFIG_CAPTURE: " + ", ".join(failed)
        )


def provider_configuration_evidence_is_provider_observed(
    payload: Mapping[str, Any], classification: CapabilityClassification
) -> bool:
    """Avoid calling declared-only config evidence provider-observed."""

    if classification is CapabilityClassification.SUPPORTED:
        return (
            payload.get("runtime_verified") is True
            and payload.get("effective_configuration_status") == "VERIFIED"
        )
    if classification is CapabilityClassification.UNKNOWN:
        return (
            payload.get("effective_configuration_status") == "MISMATCH"
            and payload.get("effective_shared_configuration_matches") is False
            and payload.get("unresolved_configuration_defaults") == []
        )
    return False


def artifact_sha(root: Path, name: str) -> str:
    return sha256_bytes((root / name).read_bytes())


def write_json_once(root: Path, name: str, payload: object) -> str:
    path = root / name
    if path.exists():
        return sha256_bytes(path.read_bytes())
    return write_json_exclusive(path, payload)


def write_jsonl_once(root: Path, name: str, rows: list[Mapping[str, Any]]) -> str:
    path = root / name
    if not path.exists():
        with path.open("xb") as stream:
            for row in rows:
                stream.write(json.dumps(dict(row), sort_keys=True).encode() + b"\n")
    return sha256_bytes(path.read_bytes())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--mount", required=True)
    parser.add_argument("--implementation-patch-sha256", required=True)
    parser.add_argument("--implementation-patch-bytes", required=True, type=int)
    args = parser.parse_args()
    if os.environ.get("MEMLIFE_AUTHORIZE_PHASE08B1_LIVE") != "YES":
        raise RuntimeError("Phase 08B-1 live authorization guard is closed")
    if run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).strip() != BASE_COMMIT:
        raise RuntimeError("remote checkout is not the exact Phase 08B-0 base")

    mount = Path(args.mount).resolve()
    attempt_root = mount / "memlife" / "runs" / "phase08b" / "attempts" / args.attempt_id
    attempt_root.mkdir(parents=True, exist_ok=False)
    state = attempt_root / "provider-state"
    state.mkdir()
    for child in (state / "postgres", state / "redis", state / "lancedb"):
        child.mkdir()
    raw = RawLog(attempt_root)
    started = now()
    compose_project = "memlife08b1" + args.attempt_id[-8:].replace("-", "")
    provider = mount / "memlife" / "providers" / "honcho-v3.2.1"
    compose: Path | None = None
    model_proxy: ModelBudgetProxy | None = None
    embedding_backend: LocalSentenceTransformerEmbeddings | None = None
    contact_state = ProviderContactState()
    health = False
    blocker: str | None = None
    cleanup_blockers: list[str] = []
    calibration = LiveCalibrationState()
    current_runtime_file_identities: list[dict[str, Any]] = []
    runtime_file_lifecycle: dict[str, Any] = {
        "schema_version": "phase08b1-runtime-file-lifecycle-v1",
        "preexisting_residue": {"status": "NOT_INSPECTED"},
        "current_attempt_identities": [],
        "current_attempt_cleanup": {
            "status": "NOT_REQUIRED",
            "files": [],
            "blockers": [],
        },
    }
    provider_version: dict[str, Any] = {
        "provider": "honcho",
        "version": "3.2.1",
        "upstream_tag": UPSTREAM_TAG,
        "upstream_commit": UPSTREAM_COMMIT,
        "source": UPSTREAM_URL,
        "status": "PIN_VERIFICATION_PENDING",
    }
    provider_config = initial_provider_configuration()
    effective_configuration_payloads: dict[str, dict[str, Any]] = {
        service: {
            "schema_version": "phase08b1-effective-honcho-settings-v1",
            "service": service,
            "status": "NOT_OBSERVED",
            "effective_settings": None,
            "redacted_paths": [],
            "effective_settings_sha256": None,
        }
        for service in EFFECTIVE_CONFIG_ARTIFACTS
    }
    baseline = {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "root_disk_pre": disk(Path("/")),
        "persistent_volume_pre": disk(mount),
        "memory_pre": memory(),
        "mount": str(mount),
        "docker_version": run(["docker", "version", "--format", "{{.Server.Version}}"]).strip(),
        "docker_containers_before": run(
            ["docker", "ps", "--format", "{{.Names}}|{{.Status}}"]
        ).splitlines(),
        "git_base": BASE_COMMIT,
        "attempt_id": args.attempt_id,
        "started_at": started,
    }
    source_manifest = json.loads(
        (REPO_ROOT / "manifests" / "phase-08b1-honcho-live-acceptance.json").read_text()
    )
    bound = bound_runtime_manifest(source_manifest, args.attempt_id)
    bound_sha = write_json_exclusive(attempt_root / "bound-runtime-manifest.json", bound)
    classifications = {
        capability: CapabilityClassification.UNKNOWN for capability in AcceptanceCapability
    }
    notes = {capability: "probe not reached" for capability in AcceptanceCapability}
    bindings: dict[AcceptanceCapability, dict[str, Any]] = {}
    terminal_capabilities: set[AcceptanceCapability] = set()
    scenario_status = {f"S{i}": "UNKNOWN" for i in range(6)}
    scenario_calibration_derived = False
    scenario_evidence_materialized = False
    provider_observed_scenarios: set[str] = set()
    retrieval_candidates: list[dict[str, Any]] = []
    lineage: dict[str, Any] = {"status": "NOT_OBSERVED", "edges": []}
    quiescence: dict[str, Any] = {"status": "NOT_OBSERVED", "observations": []}
    provider_stack_health: dict[str, Any] = {
        "schema_version": "phase08b1-provider-stack-health-v1",
        "required_service_names": list(REQUIRED_COMPOSE_SERVICES),
        "requested_start_service_names": list(REQUIRED_COMPOSE_SERVICES),
        "optional_mcp_requested": False,
        "startup_order": [
            "database",
            "migrations",
            "empty-state-proof",
            "configure-embeddings-384",
            "dimension-verification",
            "redis-api-deriver",
        ],
        "pgvector_bootstrap": {"status": "NOT_REACHED"},
        "observations": [],
        "status": "NOT_OBSERVED",
    }
    surface_inventory: dict[str, Any] = {
        "schema_version": "phase08b1-provider-surface-inventory-v1",
        "provider_observed": False,
        "evidence_class": None,
        "status": "NOT_OBSERVED",
    }
    adapter_capture_identities: dict[str, Mapping[str, Any]] = {}
    adapter_capture_index: list[dict[str, Any]] = []
    capability_evidence_payloads: dict[AcceptanceCapability, tuple[str, dict[str, Any]]] = {}
    capabilities = None
    record = None
    workspace: str | None = None
    session: str | None = None
    scenario_evidence_index: dict[str, dict[str, Any]] = {}
    model_accounting: dict[str, Any] = {
        "provider_label": "split-backend-openai-compatible",
        "text_generation_model": TEXT_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "text_endpoint": "Jetstream gpt-oss endpoint",
        "embedding_endpoint": "local CPU sentence-transformer",
        "maximum_requests": MAX_MODEL_CALLS,
        "call_count": 0,
        "text_generation_call_count": 0,
        "hosted_text_generation_call_count": 0,
        "embedding_call_count": 0,
        "local_embedding_call_count": 0,
        "local_embedding_success_count": 0,
        "local_embedding_failure_count": 0,
        "input_tokens": "UNKNOWN",
        "output_tokens": "UNKNOWN",
        "budget_stop": False,
        "limitation": "Token fields remain UNKNOWN if the upstream omits usage.",
    }
    stage_a: dict[str, Any] = {
        "schema_version": "phase08b1-stage-a-preflight-v1",
        "status": "NOT_REACHED",
        "scientific_provider_contact": False,
        "provider_internal_model_calls": 0,
        "downstream_model_calls": 0,
        "rq3_calls": 0,
        "blockers": ["stage A not reached"],
    }
    authority_rows: list[dict[str, Any]] = []

    def materialize_effective_configuration() -> None:
        redacted_paths = dict(provider_config["redacted_paths"])
        for service, artifact in EFFECTIVE_CONFIG_ARTIFACTS.items():
            payload = effective_configuration_payloads[service]
            artifact_digest = write_json_once(attempt_root, artifact, payload)
            provider_config[f"effective_{service}_configuration_sha256"] = (
                artifact_digest
            )
            paths = payload.get("redacted_paths")
            redacted_paths[service] = list(paths) if isinstance(paths, list) else []
        provider_config["redacted_paths"] = redacted_paths

    def materialize_scientific_evidence() -> None:
        nonlocal adapter_capture_index
        materialize_effective_configuration()
        write_json_once(attempt_root, "provider-config.json", provider_config)
        write_json_once(attempt_root, "provider-version.json", provider_version)
        write_json_once(
            attempt_root, "provider-stack-health.json", provider_stack_health
        )
        write_json_once(attempt_root, "retrieval-candidates.json", retrieval_candidates)
        write_json_once(attempt_root, "lineage.json", lineage)
        write_json_once(attempt_root, "quiescence.json", quiescence)
        write_json_once(
            attempt_root,
            "provider-internal-model-accounting.json",
            model_accounting,
        )
        write_json_once(
            attempt_root,
            "provider-surface-inventory.json",
            surface_inventory,
        )
        if adapter_capture_identities:
            adapter_capture_index = index_adapter_raw_captures(
                attempt_root, adapter_capture_identities
            )
        raw_index = build_provider_raw_index(raw.entries, adapter_capture_index)
        write_json_once(attempt_root, "provider-raw-response.json", raw_index)
        write_jsonl_once(attempt_root, "authority-ledger.jsonl", authority_rows)
        write_jsonl_once(
            attempt_root,
            "latency.jsonl",
            [
                {
                    "name": entry["name"],
                    "duration_seconds": entry["duration_seconds"],
                }
                for entry in raw.entries
            ],
        )

        for capability, (artifact, payload) in capability_evidence_payloads.items():
            digest = write_json_once(attempt_root, artifact, payload)
            bindings[capability] = evidence_binding(
                capability,
                artifact=artifact,
                artifact_sha256=digest,
            )

        direct_artifacts = {
            AcceptanceCapability.PROVENANCE_RELATIONSHIP_EDGES: "lineage.json",
            AcceptanceCapability.NATIVE_REDERIVATION_CONSOLIDATION: "lineage.json",
            AcceptanceCapability.QUIESCENCE_ASYNC_COMPLETION_PROOF: "quiescence.json",
            AcceptanceCapability.PROVIDER_CONFIGURATION_PINNING: "provider-config.json",
            AcceptanceCapability.PROVIDER_VERSION_COMMIT_PINNING: "provider-version.json",
        }
        for capability, artifact in direct_artifacts.items():
            conclusive = (
                capability
                is not AcceptanceCapability.PROVIDER_CONFIGURATION_PINNING
                and classifications[capability]
                in {
                    CapabilityClassification.SUPPORTED,
                    CapabilityClassification.UNSUPPORTED,
                }
            )
            observed_config = (
                capability
                is AcceptanceCapability.PROVIDER_CONFIGURATION_PINNING
                and provider_configuration_evidence_is_provider_observed(
                    provider_config, classifications[capability]
                )
            )
            if conclusive or observed_config:
                bindings[capability] = evidence_binding(
                    capability,
                    artifact=artifact,
                    artifact_sha256=artifact_sha(attempt_root, artifact),
                )
        surface_sha = artifact_sha(attempt_root, "provider-surface-inventory.json")
        for capability in (
            AcceptanceCapability.UPDATE_SUPERSEDE,
            AcceptanceCapability.HARD_DELETE,
            AcceptanceCapability.REVOKE_INVALIDATE,
            AcceptanceCapability.SOURCE_VERSION_TRANSITIONS,
            AcceptanceCapability.TEMPORAL_VALIDITY,
        ):
            if classifications[capability] is CapabilityClassification.UNSUPPORTED:
                bindings[capability] = evidence_binding(
                    capability,
                    artifact="provider-surface-inventory.json",
                    artifact_sha256=surface_sha,
                )

    def materialize_scenario_evidence() -> dict[str, dict[str, Any]]:
        nonlocal scenario_evidence_index
        s0_classification = CapabilityClassification(scenario_status["S0"])
        relevant_bindings = {
            capability.value: dict(bindings[capability])
            for capability in (
                AcceptanceCapability.CREATE_WRITE,
                AcceptanceCapability.RETRIEVAL,
            )
            if capability in bindings
        }
        s0_payload = {
            "schema_version": "phase08b1-scenario-S0-evidence-v1",
            "scenario": "S0",
            "provider_observed": (
                scenario_calibration_derived
                and "S0" in provider_observed_scenarios
            ),
            "classification": s0_classification.value,
            "fixture": {
                "content": FIXTURE_CONTENT,
                "content_sha256": sha256_bytes(FIXTURE_CONTENT.encode("utf-8")),
                "retrieval_query": FIXTURE_QUERY,
                "workspace_id": workspace,
                "session_id": session,
            },
            "capability_evidence": relevant_bindings,
            "completion_result": s0_classification.value,
        }
        s0_sha = write_json_once(
            attempt_root, "scenarios/S0/evidence.json", s0_payload
        )
        direct_bindings: dict[str, dict[str, Any]] = {}
        if s0_classification is CapabilityClassification.SUPPORTED:
            if set(relevant_bindings) != {
                AcceptanceCapability.CREATE_WRITE.value,
                AcceptanceCapability.RETRIEVAL.value,
            }:
                raise RuntimeError("S0 support lacks create/write or retrieval evidence")
            direct_bindings["S0"] = {
                "provider_observed": True,
                "artifact": "scenarios/S0/evidence.json",
                "sha256": s0_sha,
            }
        scenario_matrix = build_scenario_evidence_matrix(
            {
                scenario: CapabilityClassification(value)
                for scenario, value in scenario_status.items()
            },
            classifications,
            bindings,
            direct_bindings,
        )
        write_json_once(
            attempt_root, "scenario-capabilities.json", scenario_matrix
        )
        scenario_evidence_index = {
            "S0": {
                "artifact": "scenarios/S0/evidence.json",
                "sha256": s0_sha,
                "classification": s0_classification.value,
            }
        }
        return scenario_matrix

    def materialize_evidence_index() -> None:
        evidence_index = {
            "schema_version": "phase08b1-provider-evidence-index-v1",
            "provider_observed": bool(raw.entries or adapter_capture_index),
            "evidence_class": (
                "PROVIDER_OBSERVED"
                if raw.entries or adapter_capture_index
                else None
            ),
            "raw_response_index": "provider-raw-response.json",
            "adapter_raw_captures": adapter_capture_index,
            "capability_evidence": {
                capability.value: dict(binding)
                for capability, binding in sorted(
                    bindings.items(), key=lambda item: item[0].value
                )
            },
            "scenario_evidence": scenario_evidence_index,
        }
        write_json_once(attempt_root, "provider-evidence-index.json", evidence_index)

    try:
        if not provider.exists():
            provider.parent.mkdir(parents=True, exist_ok=True)
            run(
                ["git", "clone", "--depth", "1", "--branch", UPSTREAM_TAG, UPSTREAM_URL, str(provider)],
                timeout=600,
            )
        try:
            preexisting_residue = preserve_and_remove_managed_runtime_residue(
                provider, mount=mount, attempt_root=attempt_root
            )
        except Exception as exc:
            runtime_file_lifecycle["preexisting_residue"] = {
                "status": "BLOCKED",
                "blocker": f"{type(exc).__name__}: {exc}",
            }
            raise
        runtime_file_lifecycle["preexisting_residue"] = {
            key: value
            for key, value in preexisting_residue.items()
            if key != "cleanup_tokens"
        }
        source_identity = validate_provider_source_checkout(provider)
        provider_version["status"] = "VERIFIED"
        provider_version.update(source_identity)
        provider_version["uv_lock_sha256"] = sha256_bytes((provider / "uv.lock").read_bytes())
        compose, env = write_runtime_files(
            provider,
            state,
            identity_sink=current_runtime_file_identities,
        )
        runtime_file_lifecycle["current_attempt_identities"] = (
            current_runtime_file_identities
        )
        provider_version["compose_sha256"] = sha256_bytes(compose.read_bytes())
        provider_config = build_declared_provider_configuration(
            compose_project=compose_project,
            provider=provider,
            state=state,
            compose=compose,
            env=env,
            provider_version=provider_version,
        )

        stage_a = static_stage_a_preflight(provider, compose)
        stage_a.update(
            base_commit=BASE_COMMIT,
            implementation_patch_sha256=args.implementation_patch_sha256,
            implementation_patch_bytes=args.implementation_patch_bytes,
            patch_apply_check=True,
            patch_apply_check_whitespace_nowarn=True,
            persistent_volume=str(mount),
            root_disk=baseline["root_disk_pre"],
            persistent_volume_disk=baseline["persistent_volume_pre"],
            memory=baseline["memory_pre"],
        )
        if baseline["root_disk_pre"]["free_bytes"] < 3 * 1024**3:
            stage_a["blockers"].append(
                "BLOCKED_ENVIRONMENT_RESOURCE: less than 3 GiB root free"
            )
        if baseline["persistent_volume_pre"]["free_bytes"] < 5 * 1024**3:
            stage_a["blockers"].append(
                "BLOCKED_ENVIRONMENT_RESOURCE: less than 5 GiB persistent-volume free"
            )
        if baseline["memory_pre"]["total_bytes"] < 4 * 1024**3:
            stage_a["blockers"].append(
                "BLOCKED_ENVIRONMENT_RESOURCE: less than 4 GiB total RAM"
            )
        if baseline["memory_pre"]["available_bytes"] < 2 * 1024**3:
            stage_a["blockers"].append(
                "BLOCKED_ENVIRONMENT_RESOURCE: less than 2 GiB available RAM"
            )
        if stage_a["blockers"]:
            stage_a["status"] = "BLOCKED"
            write_json_exclusive(attempt_root / "stage-a-preflight.json", stage_a)
            raise RuntimeError(
                "STAGE_A_BLOCKED_BEFORE_PROVIDER: " + "; ".join(stage_a["blockers"])
            )
        try:
            embedding_backend = LocalSentenceTransformerEmbeddings(
                mount / "memlife" / "model_cache" / "huggingface"
            )
            model_proxy = ModelBudgetProxy(embedding_backend)
            model_proxy.start()
            compatibility = run_model_endpoint_preflight(embedding_backend)
            compatibility_blockers = validate_model_endpoint_compatibility(
                compatibility
            )
            if compatibility_blockers:
                raise RuntimeError("; ".join(compatibility_blockers))
            stage_a.update(
                status="PASS",
                model_endpoint_compatibility=compatibility,
                embedding_compatibility_call_executed=True,
                provider_internal_model_calls=len(model_proxy.calls),
                provider_internal_total_requests=len(model_proxy.calls),
                hosted_text_generation_requests=sum(
                    call["backend"] == "jetstream_hosted" for call in model_proxy.calls
                ),
                local_embedding_requests=sum(
                    call["backend"] == "local_sentence_transformer"
                    for call in model_proxy.calls
                ),
                embedding_model_provenance=embedding_backend.provenance(
                    observed_dimension=EMBEDDING_VECTOR_DIMENSIONS
                ),
                blockers=[],
            )
        except Exception as exc:
            stage_a.update(
                status="BLOCKED",
                model_endpoint_compatibility={
                    "status": "FAIL",
                    "error": type(exc).__name__,
                    "message": str(exc),
                },
                provider_internal_model_calls=(
                    len(model_proxy.calls) if model_proxy is not None else 0
                ),
                provider_internal_total_requests=(
                    len(model_proxy.calls) if model_proxy is not None else 0
                ),
                blockers=[
                    "LOCAL_EMBEDDING_PROVISIONING_BLOCKER"
                    if isinstance(exc, LocalEmbeddingUnavailable)
                    else "MODEL_ENDPOINT_COMPATIBILITY_FAILED"
                ],
            )
            write_json_exclusive(attempt_root / "stage-a-preflight.json", stage_a)
            raise
        write_json_exclusive(attempt_root / "stage-a-preflight.json", stage_a)
        if not stage_a_allows_stage_b(stage_a):
            raise RuntimeError("STAGE_A_DID_NOT_AUTHORIZE_STAGE_B")
        compose_cmd = ["docker", "compose", "-p", compose_project, "-f", str(compose)]
        contact_state.mark_stack_start_attempted()
        bootstrap_evidence = bootstrap_pgvector_schema(
            compose_cmd,
            provider,
            state,
            attempt_root,
        )
        if (
            bootstrap_evidence.get("status") != "PASS"
            or bootstrap_evidence.get("api_deriver_start_authorized") is not True
        ):
            raise RuntimeError("PGVECTOR_BOOTSTRAP_DID_NOT_AUTHORIZE_API_DERIVER")
        provider_stack_health["pgvector_bootstrap"] = bootstrap_evidence
        run(
            [*compose_cmd, "up", "-d", "redis", "api", "deriver"],
            cwd=provider,
            timeout=3600,
        )
        contact_state.mark_stack_started()
        provider_version["image_digests"] = parse_compose_image_identities(
            run([*compose_cmd, "images", "--format", "json"], cwd=provider)
        )
        contact_state.begin_required_health_check()
        health_payload = wait_health(raw, contact_state)
        initial_health = observe_required_provider_health(
            compose_cmd,
            provider,
            phase="initial",
            api_health_payload=health_payload,
            api_health_raw_evidence=raw.entries[-1],
        )
        provider_stack_health["observations"].append(initial_health)
        provider_stack_health["status"] = (
            "PASS" if initial_health["passed"] else "FAIL"
        )
        health = initial_health["passed"]
        if health:
            contact_state.mark_required_services_passed()
        require_required_provider_health(initial_health)
        for service in EFFECTIVE_CONFIG_ARTIFACTS:
            try:
                effective_configuration_payloads[service] = (
                    capture_effective_settings(compose_cmd, provider, service)
                )
            except Exception as exc:
                effective_configuration_payloads[service] = {
                    "schema_version": "phase08b1-effective-honcho-settings-v1",
                    "service": service,
                    "status": "CAPTURE_FAILED",
                    "effective_settings": None,
                    "redacted_paths": [],
                    "effective_settings_sha256": None,
                    "error_type": type(exc).__name__,
                }
        api_effective = effective_configuration_payloads["api"]
        deriver_effective = effective_configuration_payloads["deriver"]
        both_effective_observed = (
            api_effective.get("status") == "OBSERVED"
            and deriver_effective.get("status") == "OBSERVED"
        )
        shared_matches = (
            effective_shared_configuration_matches(api_effective, deriver_effective)
            if both_effective_observed
            else None
        )
        provider_config["effective_shared_configuration_matches"] = shared_matches
        provider_config["unresolved_configuration_defaults"] = (
            []
            if both_effective_observed
            else [
                f"effective {service} AppSettings not observed"
                for service, payload in effective_configuration_payloads.items()
                if payload.get("status") != "OBSERVED"
            ]
        )
        provider_config["effective_configuration_status"] = (
            "VERIFIED"
            if shared_matches is True
            else "MISMATCH"
            if shared_matches is False
            else "CAPTURE_INCOMPLETE"
        )
        materialize_effective_configuration()
        provider_config["runtime_verified"] = provider_configuration_support_ready(
            provider_config, provider_healthy=health
        )
        require_effective_settings_capture(effective_configuration_payloads)
        openapi = raw.request("GET", "openapi.json", name="openapi")
        if not isinstance(openapi, Mapping):
            raise RuntimeError("live Honcho OpenAPI response was not an object")
        openapi_entry = raw.entries[-1]
        surface_inventory = build_provider_surface_inventory(
            openapi,
            raw_artifact=openapi_entry["artifact"],
            raw_sha256=openapi_entry["sha256"],
            raw_bytes=openapi_entry["bytes"],
        )
        write_json_exclusive(
            attempt_root / "provider-surface-inventory.json", surface_inventory
        )
        for capability, classification in surface_inventory_classifications(
            surface_inventory
        ).items():
            classifications[capability] = classification
            notes[capability] = (
                "deterministic rule over live GET /openapi.json surface inventory"
            )
            terminal_capabilities.add(capability)

        workspace = "p08b1-" + args.attempt_id[-12:].replace("-", "")
        session = workspace + "-session"
        peer = workspace + "-peer"
        raw.request("POST", "v3/workspaces", payload={"id": workspace}, expected={201}, name="workspace-create")
        raw.request("POST", f"v3/workspaces/{workspace}/peers", payload={"id": peer}, expected={201}, name="peer-create")
        raw.request(
            "POST",
            f"v3/workspaces/{workspace}/sessions",
            payload={"id": session, "peers": {peer: {}}},
            expected={201},
            name="session-create",
        )
        adapter_capture = DirectoryRawArtifactCapture(attempt_root / "probes")
        adapter = HonchoLiveAdapter(
            HonchoLiveConfig(
                base_url="http://127.0.0.1:8000",
                workspace_id=workspace,
                session_id=session,
                peer_id=peer,
            ),
            transport=HonchoHttpTransport("http://127.0.0.1:8000"),
            capture=adapter_capture,
        )

        def queue_observation(name: str, check: int) -> dict[str, Any]:
            observed = raw.request(
                "GET",
                f"v3/workspaces/{workspace}/queue/status?session_id={session}",
                name=name,
            )
            if not isinstance(observed, Mapping):
                raise RuntimeError("Honcho queue status response was not an object")
            return {
                "check": check,
                "timestamp": now(),
                "raw_evidence": dict(raw.entries[-1]),
                **observed,
            }

        explicit_queue_baseline = queue_observation(
            "explicit-queue-baseline", 0
        )
        written = adapter.write(
            WriteCommand(
                namespace=session,
                content=FIXTURE_CONTENT,
                metadata={"benchmark": "phase08b1", "fictional": True},
            )
        )
        authority_rows.append(
            current_baseline_authority_ledger(
                attempt_id=args.attempt_id,
                namespace=session,
                content=FIXTURE_CONTENT,
            ).model_dump(mode="json")
        )
        explicit_queue_observations = []
        for check in range(1, QUIESCENCE_MAX_CHECKS + 1):
            explicit_queue_observations.append(
                queue_observation(f"explicit-queue-{check:02d}", check)
            )
            current_quiescence = evaluate_trigger_relative_quiescence(
                explicit_queue_baseline,
                explicit_queue_observations,
            )
            if current_quiescence["status"] == "SUPPORTED":
                break
            if check < QUIESCENCE_MAX_CHECKS:
                time.sleep(QUIESCENCE_POLL_SECONDS)
        explicit_quiescence = evaluate_trigger_relative_quiescence(
            explicit_queue_baseline,
            explicit_queue_observations,
        )
        explicit_quiescence.update(
            trigger="native message write",
            baseline=explicit_queue_baseline,
            observations=explicit_queue_observations,
        )

        records = adapter.query(
            QueryCommand(
                namespace=session,
                query=FIXTURE_QUERY,
                limit=RETRIEVAL_LIMIT,
            )
        )
        inspection_records = adapter.list_or_inspect(session)
        adapter_capture_identities = {
            probe_name: identity.model_dump(mode="json")
            for probe_name, identity in adapter_capture.identities.items()
        }
        matched = [record for record in records if record.memory_id == written.memory_id]
        retrieval_candidates = [
            {
                "provider_native_id": record.memory_id,
                "rank": record.metadata.get("retrieval_rank"),
                "content": record.content,
                "raw_artifact": record.metadata.get("raw_artifact"),
            }
            for record in records
        ]
        classifications[AcceptanceCapability.CREATE_WRITE] = CapabilityClassification.SUPPORTED
        classifications[AcceptanceCapability.EXACT_RAW_RESPONSE_CAPTURE] = CapabilityClassification.SUPPORTED
        retrieved_ids = [record.memory_id for record in records]
        recorded_ranks = [item["rank"] for item in retrieval_candidates]
        search_classifications = classify_native_search_result(
            written.memory_id, retrieved_ids, recorded_ranks
        )
        classifications.update(search_classifications)
        ordering_preserved = (
            search_classifications[
                AcceptanceCapability.DETERMINISTIC_OR_RECORDED_ORDERING
            ]
            is CapabilityClassification.SUPPORTED
        )
        classifications[AcceptanceCapability.RAW_INSPECTION] = CapabilityClassification.UNKNOWN
        for capability in (
            AcceptanceCapability.CREATE_WRITE,
            AcceptanceCapability.RETRIEVAL,
            AcceptanceCapability.EXACT_PROVIDER_NATIVE_IDS,
            AcceptanceCapability.EXACT_RAW_RESPONSE_CAPTURE,
            AcceptanceCapability.DETERMINISTIC_OR_RECORDED_ORDERING,
            AcceptanceCapability.RAW_INSPECTION,
        ):
            notes[capability] = "provider-observed Phase 08B-1 probe"
            terminal_capabilities.add(capability)
        notes[AcceptanceCapability.RAW_INSPECTION] = (
            "separate native message list captured, but frozen diagnostic-inspection semantics remain unproven"
        )

        create_raw = written.metadata["raw_artifact"]
        retrieval_raw = adapter_capture_identities[
            "honcho_capability_retrieval_v1"
        ]
        inspection_raw = adapter_capture_identities[
            "honcho_capability_raw_inspection_v1"
        ]
        created_id = written.memory_id
        capability_evidence_payloads.update(
            {
                AcceptanceCapability.CREATE_WRITE: (
                    "probes/create-write/evidence.json",
                    {
                        "probe_name": "honcho_capability_create_write_v1",
                        "native_response": create_raw,
                        "capture_before_normalization": True,
                        "normalized_result": {
                            "provider_native_id": created_id,
                            "namespace": written.namespace,
                            "content": written.content,
                        },
                    },
                ),
                AcceptanceCapability.RETRIEVAL: (
                    "probes/retrieval/evidence.json",
                    {
                        "probe_name": "honcho_capability_retrieval_v1",
                        "native_response": retrieval_raw,
                        "capture_before_normalization": True,
                        "native_surface": (
                            f"POST /v3/workspaces/{workspace}/search"
                        ),
                        "request": {
                            "query": FIXTURE_QUERY,
                            "filters": {"session_id": session},
                            "limit": RETRIEVAL_LIMIT,
                        },
                        "candidates": retrieval_candidates,
                        "provider_returned_ids": retrieved_ids,
                        "fixture_native_id_matched": bool(matched),
                        "non_match_classification": "UNKNOWN",
                    },
                ),
                AcceptanceCapability.EXACT_PROVIDER_NATIVE_IDS: (
                    "probes/exact-native-ids/identity-map.json",
                    {
                        "probe_name": "honcho_capability_exact_provider_native_ids_v1",
                        "create_provider_native_id": created_id,
                        "workspace_search_provider_native_ids": retrieved_ids,
                        "exact_value_match": created_id in retrieved_ids,
                        "deterministic_exact_match": (
                            created_id in retrieved_ids and ordering_preserved
                        ),
                        "identity_scope": "honcho-provider-native-message-id",
                        "canonical_proposition_id": None,
                        "logical_fact_or_version_id": None,
                        "provider_native_id_is_canonical_proposition_id": False,
                        "provider_native_id_is_logical_fact_or_version_id": False,
                    },
                ),
                AcceptanceCapability.EXACT_RAW_RESPONSE_CAPTURE: (
                    "probes/raw-capture/raw-response-identity.json",
                    {
                        "probe_name": "honcho_capability_exact_raw_response_capture_v1",
                        "captures": [create_raw, retrieval_raw],
                        "retrieval_capture_surface": (
                            f"POST /v3/workspaces/{workspace}/search"
                        ),
                        "capture_before_normalization": True,
                    },
                ),
                AcceptanceCapability.DETERMINISTIC_OR_RECORDED_ORDERING: (
                    "probes/retrieval-ordering/evidence.json",
                    {
                        "probe_name": (
                            "honcho_capability_deterministic_or_recorded_ordering_v1"
                        ),
                        "native_response": retrieval_raw,
                        "native_surface": (
                            f"POST /v3/workspaces/{workspace}/search"
                        ),
                        "provider_returned_order": retrieved_ids,
                        "recorded_ranks": recorded_ranks,
                        "raw_order_captured_before_normalization": True,
                        "rank_assignment_rule": (
                            "one-based enumeration of exact native search list order"
                        ),
                        "normalized_order": retrieved_ids,
                        "normalization_preserves_order": ordering_preserved,
                    },
                ),
            }
        )
        capability_evidence_payloads[AcceptanceCapability.RAW_INSPECTION] = (
            "probes/raw-inspection/evidence.json",
            {
                "probe_name": "honcho_capability_raw_inspection_v1",
                "native_response": inspection_raw,
                "native_surface": (
                    f"POST /v3/workspaces/{workspace}/sessions/{session}/messages/list"
                ),
                "provider_native_ids": [
                    record.memory_id for record in inspection_records
                ],
                "independent_from_retrieval_surface": True,
                "classification": "UNKNOWN",
            },
        )
        explicit_snapshot = raw.request(
            "POST",
            f"v3/workspaces/{workspace}/conclusions/list?page=1&size=100",
            payload={"filters": {"session_id": session}},
            name="explicit-conclusions-list",
        )
        explicit_items = explicit_snapshot.get("items", [])
        if any(item.get("level") != "explicit" for item in explicit_items):
            raise RuntimeError("normal deriver produced a non-explicit conclusion")
        if any(item.get("source_ids") for item in explicit_items):
            raise RuntimeError("explicit conclusion unexpectedly carried source_ids")

        dream_queue_baseline = queue_observation("dream-queue-baseline", 0)
        dream_guard = DreamOperationGuard()
        dream_ordinal = dream_guard.authorize(PROVENANCE_PROBE_PURPOSE)
        raw.request(
            "POST",
            f"v3/workspaces/{workspace}/schedule_dream",
            payload={
                "observer": peer,
                "observed": peer,
                "dream_type": "omni",
                "session_id": session,
                "rebuild": False,
            },
            expected={204},
            name=f"schedule-dream-{dream_ordinal}",
        )
        dream_queue_observations = []
        for check in range(1, QUIESCENCE_MAX_CHECKS + 1):
            dream_queue_observations.append(
                queue_observation(f"dream-queue-{check:02d}", check)
            )
            current_quiescence = evaluate_trigger_relative_quiescence(
                dream_queue_baseline,
                dream_queue_observations,
            )
            if current_quiescence["status"] == "SUPPORTED":
                break
            if check < QUIESCENCE_MAX_CHECKS:
                time.sleep(QUIESCENCE_POLL_SECONDS)
        dream_quiescence = evaluate_trigger_relative_quiescence(
            dream_queue_baseline,
            dream_queue_observations,
        )
        dream_quiescence.update(
            trigger="single authorized native schedule_dream",
            baseline=dream_queue_baseline,
            observations=dream_queue_observations,
        )
        quiescence = {
            "status": "SUPPORTED"
            if explicit_quiescence["status"] == "SUPPORTED"
            and dream_quiescence["status"] == "SUPPORTED"
            else "UNKNOWN",
            "normal_deriver_explicit_path": explicit_quiescence,
            "native_dream_derived_path": dream_quiescence,
            "maximum_checks_per_path": QUIESCENCE_MAX_CHECKS,
            "poll_seconds": QUIESCENCE_POLL_SECONDS,
            "maximum_window_seconds_per_path": (
                QUIESCENCE_MAX_CHECKS * QUIESCENCE_POLL_SECONDS
            ),
            "sleep_only_success": False,
        }
        classifications[AcceptanceCapability.QUIESCENCE_ASYNC_COMPLETION_PROOF] = (
            CapabilityClassification.SUPPORTED
            if quiescence["status"] == "SUPPORTED"
            else CapabilityClassification.UNKNOWN
        )
        terminal_capabilities.add(
            AcceptanceCapability.QUIESCENCE_ASYNC_COMPLETION_PROOF
        )
        notes[AcceptanceCapability.QUIESCENCE_ASYNC_COMPLETION_PROOF] = (
            "bounded exact provider queue observations"
        )
        conclusions = raw.request(
            "POST",
            f"v3/workspaces/{workspace}/conclusions/list?page=1&size=100",
            payload={"filters": {"session_id": session}},
            name="post-dream-conclusions-list",
        )
        derived_conclusion_response = dict(raw.entries[-1])
        conclusion_items = conclusions.get("items", [])
        source_ids = {
            source_id
            for item in conclusion_items
            if item.get("level") in {"deductive", "inductive", "contradiction"}
            for source_id in item.get("source_ids", [])
        }
        resolved_sources: dict[str, dict[str, Any]] = {}
        for source_id in sorted(source_ids):
            resolved = raw.request(
                "GET",
                f"v3/workspaces/{workspace}/conclusions/{source_id}",
                expected={200, 404},
                name=f"conclusion-source-{source_id}",
            )
            if isinstance(resolved, dict) and resolved.get("id") == source_id:
                resolved_sources[source_id] = resolved
        lineage = evaluate_lineage(conclusion_items, resolved_sources)
        lineage["normal_deriver_explicit_snapshot"] = explicit_items
        lineage["native_dream_scheduled"] = True
        lineage["native_dream_schedule_attempts"] = dream_guard.scheduled
        lineage["native_dream_operation_budget"] = DREAM_OPERATION_BUDGET
        lineage["native_dream_purpose"] = PROVENANCE_PROBE_PURPOSE
        lineage["automatic_dream_retry_permitted"] = False
        resolution_evidence = {
            entry["name"].removeprefix("conclusion-source-"): entry
            for entry in raw.entries
            if entry["name"].startswith("conclusion-source-")
        }
        lineage["source_resolution_evidence"] = [
            {
                "source_id": source_id,
                "native_surface": (
                    f"GET /v3/workspaces/{workspace}/conclusions/{source_id}"
                ),
                "resolved_native_id": resolved_sources.get(source_id, {}).get("id"),
                "resolved_native_type": "conclusion",
                "raw_artifact": resolution_evidence[source_id]["artifact"],
                "raw_sha256": resolution_evidence[source_id]["sha256"],
                "status_code": resolution_evidence[source_id]["status_code"],
            }
            for source_id in sorted(source_ids)
        ]
        lineage["derived_conclusion_raw_response"] = derived_conclusion_response
        classifications[AcceptanceCapability.PROVENANCE_RELATIONSHIP_EDGES] = (
            CapabilityClassification.SUPPORTED
            if lineage["status"] == "SUPPORTED"
            else CapabilityClassification.UNKNOWN
        )
        terminal_capabilities.add(
            AcceptanceCapability.PROVENANCE_RELATIONSHIP_EDGES
        )
        notes[AcceptanceCapability.PROVENANCE_RELATIONSHIP_EDGES] = (
            "provider-native derived conclusions, source_ids, and exact resolution"
        )
        classifications[AcceptanceCapability.NATIVE_REDERIVATION_CONSOLIDATION] = (
            CapabilityClassification.SUPPORTED
            if lineage["status"] == "SUPPORTED"
            else CapabilityClassification.UNKNOWN
        )
        terminal_capabilities.add(
            AcceptanceCapability.NATIVE_REDERIVATION_CONSOLIDATION
        )
        notes[AcceptanceCapability.NATIVE_REDERIVATION_CONSOLIDATION] = (
            "single authorized native Dream and its exact derived lineage"
        )
        classifications[AcceptanceCapability.RESTART_RECONSTRUCTION] = CapabilityClassification.UNKNOWN
        terminal_capabilities.add(AcceptanceCapability.RESTART_RECONSTRUCTION)
        notes[AcceptanceCapability.RESTART_RECONSTRUCTION] = (
            "owned restart observed, but reconstruction semantics not separately proven"
        )

        pre_restart = raw.request(
            "POST",
            f"v3/workspaces/{workspace}/sessions/{session}/messages/list?page=1&size=100",
            payload={"filters": {}},
            name="pre-restart-messages",
        )
        pre_restart_raw = dict(raw.entries[-1])
        pre_restart_ids = native_message_ids(pre_restart)
        pre_restart_exact_match = (
            pre_restart_ids is not None and created_id in pre_restart_ids
        )
        contact_state.begin_required_health_check()
        run([*compose_cmd, "restart", "api", "deriver"], cwd=provider, timeout=300)
        restart_health_payload = wait_health(raw, contact_state)
        restart_health = observe_required_provider_health(
            compose_cmd,
            provider,
            phase="post-restart",
            api_health_payload=restart_health_payload,
            api_health_raw_evidence=raw.entries[-1],
        )
        provider_stack_health["observations"].append(restart_health)
        provider_stack_health["status"] = (
            "PASS" if restart_health["passed"] else "FAIL"
        )
        restart_healthy = restart_health["passed"]
        health = restart_healthy
        if restart_healthy:
            contact_state.mark_required_services_passed()
        require_required_provider_health(restart_health)
        post_restart = raw.request(
            "POST",
            f"v3/workspaces/{workspace}/sessions/{session}/messages/list?page=1&size=100",
            payload={"filters": {}},
            name="post-restart-messages",
        )
        post_restart_raw = dict(raw.entries[-1])
        post_restart_ids = native_message_ids(post_restart)
        post_restart_exact_match = (
            post_restart_ids is not None and created_id in post_restart_ids
        )
        classifications[AcceptanceCapability.RESTART_PERSISTENCE] = (
            classify_restart_persistence(
                created_id,
                pre_restart_ids,
                post_restart_ids,
                restart_healthy=restart_healthy,
            )
        )
        terminal_capabilities.add(AcceptanceCapability.RESTART_PERSISTENCE)
        notes[AcceptanceCapability.RESTART_PERSISTENCE] = (
            "exact pre/post restart provider-native ID comparison"
        )
        capability_evidence_payloads[AcceptanceCapability.RESTART_PERSISTENCE] = (
            "probes/restart-persistence/evidence.json",
            {
                "probe_name": "honcho_capability_restart_persistence_v1",
                "written_message_provider_native_id": created_id,
                "pre_restart_provider_native_ids": pre_restart_ids,
                "pre_restart_exact_match": pre_restart_exact_match,
                "pre_restart_raw_response": pre_restart_raw,
                "post_restart_provider_native_ids": post_restart_ids,
                "post_restart_exact_match": post_restart_exact_match,
                "post_restart_raw_response": post_restart_raw,
                "owned_restart_services": ["api", "deriver"],
                "owned_restart_healthy": restart_healthy,
                "classification": classifications[
                    AcceptanceCapability.RESTART_PERSISTENCE
                ].value,
            },
        )
        classifications[AcceptanceCapability.PROVIDER_CONFIGURATION_PINNING] = (
            CapabilityClassification.SUPPORTED
            if provider_configuration_support_ready(
                provider_config, provider_healthy=health
            )
            else CapabilityClassification.UNKNOWN
        )
        if not provider_version_identity_complete(provider_version):
            raise RuntimeError("provider version/source/image identity is incomplete")
        classifications[AcceptanceCapability.PROVIDER_VERSION_COMMIT_PINNING] = (
            CapabilityClassification.SUPPORTED
        )
        terminal_capabilities.update(
            {
                AcceptanceCapability.PROVIDER_CONFIGURATION_PINNING,
                AcceptanceCapability.PROVIDER_VERSION_COMMIT_PINNING,
            }
        )
        notes[AcceptanceCapability.PROVIDER_CONFIGURATION_PINNING] = (
            "declared attempt inputs plus redacted effective API/deriver AppSettings"
        )
        notes[AcceptanceCapability.PROVIDER_VERSION_COMMIT_PINNING] = (
            "exact source commit plus executing image identities"
        )
        provider_observed_scenarios.add("S0")
        scenario_status = {
            scenario: classification.value
            for scenario, classification in derive_scenario_classifications(
                classifications,
                provider_observed_scenarios=provider_observed_scenarios,
            ).items()
        }
        scenario_calibration_derived = True
        if terminal_capabilities != set(AcceptanceCapability):
            missing = sorted(
                capability.value
                for capability in set(AcceptanceCapability) - terminal_capabilities
            )
            raise RuntimeError(
                "capability probes did not reach terminal classification: "
                + ", ".join(missing)
            )
        if model_proxy is not None:
            model_accounting = model_proxy.accounting()
            model_proxy.stop()
            model_proxy = None
        materialize_scientific_evidence()
        capabilities = build_capability_assessments(
            attempt_root, classifications, bindings, notes
        )
        materialize_scenario_evidence()
        materialize_evidence_index()
        scenario_evidence_materialized = True
        calibration.complete(
            stage_a_passed=stage_a_allows_stage_b(stage_a),
            health_passed=contact_state.provider_health_passed,
            probes_terminal=terminal_capabilities == set(AcceptanceCapability),
            scenario_derived=scenario_calibration_derived,
            evidence_materialized=scenario_evidence_materialized,
        )
        record = acceptance_record(
            capabilities,
            live_calibration_complete=calibration.live_calibration_complete,
        )
        record_payload = record.model_dump(mode="json")
        record_payload["derived_by"] = "honcho_acceptance_decision"
        record_payload["manual_override"] = False
        write_json_exclusive(
            attempt_root / "acceptance-capabilities.json",
            record_payload["capabilities"],
        )
        write_json_exclusive(
            attempt_root / "provider-acceptance-record.json", record_payload
        )
    except Exception as exc:
        blocker = f"{type(exc).__name__}: {exc}"
        calibration.fail_operationally(blocker)
    finally:
        if compose is not None and contact_state.provider_stack_start_attempted:
            try:
                run(
                    ["docker", "compose", "-p", compose_project, "-f", str(compose), "down"],
                    cwd=provider,
                    timeout=300,
                )
            except Exception as exc:
                cleanup_blocker = f"stack shutdown: {type(exc).__name__}"
                blocker = (blocker + "; " if blocker else "") + cleanup_blocker
                calibration.fail_operationally(cleanup_blocker)
        if model_proxy is not None:
            try:
                model_accounting = model_proxy.accounting()
            except Exception as exc:
                proxy_blocker = (
                    f"model proxy accounting: {type(exc).__name__}"
                )
                cleanup_blockers.append(proxy_blocker)
                calibration.fail_operationally(proxy_blocker)
            try:
                model_proxy.stop()
            except Exception as exc:
                proxy_blocker = f"model proxy stop: {type(exc).__name__}"
                cleanup_blockers.append(proxy_blocker)
                calibration.fail_operationally(proxy_blocker)
        runtime_file_lifecycle["current_attempt_identities"] = (
            current_runtime_file_identities
        )
        try:
            runtime_cleanup = cleanup_runtime_files(
                current_runtime_file_identities
            )
        except Exception as exc:
            runtime_cleanup = {
                "status": "BLOCKED",
                "files": [],
                "blockers": [
                    f"RUNTIME_FILE_CLEANUP_ERROR: {type(exc).__name__}"
                ],
            }
        runtime_file_lifecycle["current_attempt_cleanup"] = runtime_cleanup
        cleanup_blockers.extend(runtime_cleanup["blockers"])
        for cleanup_item in runtime_cleanup["blockers"]:
            calibration.fail_operationally(cleanup_item)

    write_json_exclusive(
        attempt_root / "runtime-file-lifecycle.json", runtime_file_lifecycle
    )

    baseline.update(
        root_disk_post=disk(Path("/")),
        persistent_volume_post=disk(mount),
        memory_post=memory(),
        honcho_health=health,
        honcho_provider_contact=contact_state.contacted,
        provider_stack_start_attempted=contact_state.provider_stack_start_attempted,
        provider_stack_started=contact_state.provider_stack_started,
        provider_contact_attempted=contact_state.provider_contact_attempted,
        provider_api_health_passed=contact_state.provider_api_health_passed,
        provider_required_services_passed=(
            contact_state.provider_required_services_passed
        ),
        provider_health_passed=contact_state.provider_health_passed,
        required_compose_services=list(REQUIRED_COMPOSE_SERVICES),
        requested_start_service_names=list(REQUIRED_COMPOSE_SERVICES),
        initial_observed_running_service_names=(
            provider_stack_health["observations"][0][
                "observed_running_service_names"
            ]
            if provider_stack_health["observations"]
            else []
        ),
        final_observed_running_service_names=(
            provider_stack_health["observations"][-1][
                "observed_running_service_names"
            ]
            if provider_stack_health["observations"]
            else []
        ),
        optional_mcp_requested=False,
        provider_stack_health_artifact="provider-stack-health.json",
        finished_at=now(),
        blocker=blocker,
        cleanup_blockers=cleanup_blockers,
        runtime_file_lifecycle_artifact="runtime-file-lifecycle.json",
    )
    if not (attempt_root / "stage-a-preflight.json").exists():
        stage_a.update(
            status="BLOCKED",
            blockers=[blocker or "stage A did not complete"],
        )
        write_json_exclusive(attempt_root / "stage-a-preflight.json", stage_a)
    write_json_exclusive(attempt_root / "environment-manifest.json", baseline)
    materialize_scientific_evidence()
    if capabilities is None:
        capabilities = build_capability_assessments(
            attempt_root, classifications, bindings, notes
        )
    materialize_scenario_evidence()
    materialize_evidence_index()
    if record is None:
        record = acceptance_record(
            capabilities,
            live_calibration_complete=calibration.live_calibration_complete,
        )
        record_payload = record.model_dump(mode="json")
        record_payload["derived_by"] = "honcho_acceptance_decision"
        record_payload["manual_override"] = False
        write_json_exclusive(
            attempt_root / "acceptance-capabilities.json",
            record_payload["capabilities"],
        )
        write_json_exclusive(
            attempt_root / "provider-acceptance-record.json", record_payload
        )
    run_ledger = {
        "attempt_id": args.attempt_id,
        "status": calibration.operational_status,
        "base_commit": BASE_COMMIT,
        "bound_manifest_sha256": bound_sha,
        "honcho_health": health,
        "honcho_provider_contact": contact_state.contacted,
        "provider_stack_start_attempted": contact_state.provider_stack_start_attempted,
        "provider_stack_started": contact_state.provider_stack_started,
        "provider_contact_attempted": contact_state.provider_contact_attempted,
        "provider_api_health_passed": contact_state.provider_api_health_passed,
        "provider_required_services_passed": (
            contact_state.provider_required_services_passed
        ),
        "provider_health_passed": contact_state.provider_health_passed,
        "required_compose_services": list(REQUIRED_COMPOSE_SERVICES),
        "requested_start_service_names": list(REQUIRED_COMPOSE_SERVICES),
        "initial_observed_running_service_names": (
            provider_stack_health["observations"][0][
                "observed_running_service_names"
            ]
            if provider_stack_health["observations"]
            else []
        ),
        "final_observed_running_service_names": (
            provider_stack_health["observations"][-1][
                "observed_running_service_names"
            ]
            if provider_stack_health["observations"]
            else []
        ),
        "optional_mcp_requested": False,
        "provider_stack_health_artifact": "provider-stack-health.json",
        "live_calibration_complete": calibration.live_calibration_complete,
        "scenario_evidence_materialized_before_completion": (
            scenario_evidence_materialized
        ),
        "provider_acceptance_decision": record.decision.value,
        "downstream_model_calls": 0,
        "rq3_activated": False,
        "rq3_calls": 0,
        "freeze_v2_finalized": False,
        "full_three_repetition_batch_run": False,
        "blocker": blocker,
        "cleanup_blockers": cleanup_blockers,
        "runtime_file_lifecycle_artifact": "runtime-file-lifecycle.json",
    }
    write_json_exclusive(attempt_root / "run-ledger.json", run_ledger)
    completion_sha = write_completion(
        attempt_root,
        {
            "attempt_id": args.attempt_id,
            "status": calibration.operational_status,
            "live_calibration_complete": calibration.live_calibration_complete,
            "provider_acceptance_decision": record.decision.value,
            "completion_time": now(),
        },
    )
    result = {
        **run_ledger,
        "remote_evidence_root": str(attempt_root),
        "completion_manifest_sha256": completion_sha,
        "provider_version": provider_version,
        "required_capabilities": {
            capability.value: classifications[capability].value
            for capability in AcceptanceCapability
            if capability in {
                AcceptanceCapability.CREATE_WRITE,
                AcceptanceCapability.RETRIEVAL,
                AcceptanceCapability.EXACT_PROVIDER_NATIVE_IDS,
                AcceptanceCapability.EXACT_RAW_RESPONSE_CAPTURE,
                AcceptanceCapability.PROVIDER_CONFIGURATION_PINNING,
                AcceptanceCapability.PROVIDER_VERSION_COMMIT_PINNING,
                AcceptanceCapability.DETERMINISTIC_OR_RECORDED_ORDERING,
                AcceptanceCapability.PROVENANCE_RELATIONSHIP_EDGES,
                AcceptanceCapability.QUIESCENCE_ASYNC_COMPLETION_PROOF,
            }
        },
        "all_capabilities": {capability.value: value.value for capability, value in classifications.items()},
        "scenarios": scenario_status,
        "environment": baseline,
        "model_accounting": model_accounting,
    }
    encoded = __import__("base64").b64encode(canonical_json_bytes(result)).decode()
    print("PHASE08B1_RESULT_B64=" + encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
