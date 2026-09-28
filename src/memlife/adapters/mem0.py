"""Mem0 OSS 2.2.1 adapter for the local-only Phase 02A baseline."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Any, Mapping

from memlife.adapters.base import (
    CapabilitySupport,
    MemoryNotFoundError,
    MemoryProviderAdapter,
    ProviderCapability,
    UnsupportedCapabilityError,
)
from memlife.config.paths import DataRootConfig, DataRootMode, prepare_runtime, resolve_data_root
from memlife.models.lifecycle import LifecycleState
from memlife.models.memory import (
    DeleteCommand,
    MemoryRecord,
    QueryCommand,
    SupersedeCommand,
    WriteCommand,
)

MEM0_VERSION = "2.2.1"
EMBEDDING_PROVIDER = "huggingface"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-MiniLM-L3-v2"
EMBEDDING_DIMS = 384
COLLECTION_NAME = "memlife_phase02a"
PROVIDER_INSTANCE_ENV = "MEMLIFE_MEM0_PROVIDER_INSTANCE"
_PLACEHOLDER_LLM_KEY = "unused-phase02a"
_LOOPBACK_LLM_URL = "http://127.0.0.1:9/v1"
_ALL_SUPPORTED = {
    capability: CapabilitySupport.SUPPORTED for capability in ProviderCapability
}


def phase02a_manifest_configuration() -> dict[str, Any]:
    """Return non-secret, path-class-only Phase 02A provider facts."""

    return {
        "phase": "02A",
        "provider": "mem0",
        "provider_version": MEM0_VERSION,
        "embedding_provider": EMBEDDING_PROVIDER,
        "embedding_model": EMBEDDING_MODEL,
        "embedding_dimensions": EMBEDDING_DIMS,
        "vector_store": "qdrant",
        "vector_store_mode": "embedded/local",
        "vector_store_path_class": "runtime/providers/mem0/qdrant",
        "history_store": "sqlite",
        "history_path_class": "runtime/providers/mem0/history/history.db",
        "model_cache_path_class": "runtime/model_cache/huggingface",
        "infer": False,
        "telemetry_enabled": False,
        "llm_network_policy": "loopback-only placeholder; no calls permitted",
    }


@dataclass(frozen=True)
class Mem0LocalPaths:
    """Explicit project-local paths consumed by Mem0 and its dependencies."""

    data_root: Path
    provider_root: Path
    qdrant: Path
    history: Path
    scratch: Path
    model_cache: Path

    @classmethod
    def from_data_root(
        cls,
        config: DataRootConfig,
        *,
        provider_instance: str | None = None,
    ) -> "Mem0LocalPaths":
        """Build paths below an already-resolved MemLife runtime root.

        Phase 02A keeps the historical ``providers/mem0`` layout. Remote
        validations can select one safe child directory so multiple pinned
        runs do not share mutable Qdrant or SQLite files.
        """

        prepare_runtime(config)
        provider_root = config.root / "providers" / "mem0"
        if provider_instance:
            if not re.fullmatch(r"[A-Za-z0-9._-]+", provider_instance):
                raise ValueError("provider_instance must be one safe path component")
            provider_root /= provider_instance
        paths = cls(
            data_root=config.root,
            provider_root=provider_root,
            qdrant=provider_root / "qdrant",
            history=provider_root / "history",
            scratch=provider_root / "scratch",
            model_cache=config.root / "model_cache" / "huggingface",
        )
        for path in (
            paths.provider_root,
            paths.qdrant,
            paths.history,
            paths.scratch,
            paths.model_cache,
        ):
            path.mkdir(parents=True, exist_ok=True)
        return paths


class Mem0MemoryAdapter(MemoryProviderAdapter):
    """Map the Phase 01 contract to native Mem0 OSS operations.

    Mem0's update mutates one memory ID. It is exposed through
    ``update_or_supersede`` without claiming a supersession relationship.
    Deleted records disappear from normal get/search/list operations; the
    normalized deleted record returned by this adapter is an operation result,
    not an emulated tombstone in Mem0.
    """

    def __init__(self, paths: Mem0LocalPaths) -> None:
        self.paths = paths
        self._configure_process_environment()
        self._memory = self._create_memory()

    @classmethod
    def from_local_runtime(cls, repo_root: Path | None = None) -> "Mem0MemoryAdapter":
        config = resolve_data_root(repo_root=repo_root)
        if config.mode is not DataRootMode.LOCAL:
            raise ValueError("local runtime requires repository-local data-root mode")
        return cls(Mem0LocalPaths.from_data_root(config))

    @classmethod
    def from_runtime(cls, repo_root: Path | None = None) -> "Mem0MemoryAdapter":
        """Create an adapter from local, configured, or live Jetstream storage."""

        config = resolve_data_root(repo_root=repo_root)
        provider_instance = os.environ.get(PROVIDER_INSTANCE_ENV, "").strip() or None
        return cls(
            Mem0LocalPaths.from_data_root(
                config,
                provider_instance=provider_instance,
            )
        )

    @property
    def provider_name(self) -> str:
        return "mem0-oss-2.2.1"

    @property
    def capabilities(self) -> Mapping[ProviderCapability, CapabilitySupport]:
        return _ALL_SUPPORTED

    @property
    def native_memory(self) -> Any:
        """Expose the OSS instance for provider-characterization tests only."""

        return self._memory

    def _configure_process_environment(self) -> None:
        os.environ["MEM0_TELEMETRY"] = "false"
        os.environ["MEM0_DIR"] = str(self.paths.scratch)
        os.environ["HF_HOME"] = str(self.paths.model_cache)
        os.environ["SENTENCE_TRANSFORMERS_HOME"] = str(self.paths.model_cache)

    def _mem0_config(self) -> dict[str, Any]:
        return {
            "version": "v1.1",
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "collection_name": COLLECTION_NAME,
                    "embedding_model_dims": EMBEDDING_DIMS,
                    "path": str(self.paths.qdrant),
                    "on_disk": True,
                },
            },
            "embedder": {
                "provider": EMBEDDING_PROVIDER,
                "config": {
                    "model": EMBEDDING_MODEL,
                    "embedding_dims": EMBEDDING_DIMS,
                    "model_kwargs": {"cache_folder": str(self.paths.model_cache)},
                },
            },
            "llm": {
                "provider": "openai",
                "config": {
                    "model": "unused-phase02a",
                    "api_key": _PLACEHOLDER_LLM_KEY,
                    "openai_base_url": _LOOPBACK_LLM_URL,
                },
            },
            "history_db_path": str(self.paths.history / "history.db"),
        }

    def manifest_configuration(self) -> dict[str, Any]:
        """Return the non-secret, path-class-only configuration for hashing."""

        return phase02a_manifest_configuration()

    def _create_memory(self) -> Any:
        installed_version = version("mem0ai")
        if installed_version != MEM0_VERSION:
            raise RuntimeError(
                f"Phase 02A requires mem0ai=={MEM0_VERSION}; found {installed_version}"
            )

        # Import only after MEM0_DIR and MEM0_TELEMETRY are fixed above.
        from mem0 import Memory
        from mem0.memory.telemetry import MEM0_TELEMETRY

        if MEM0_TELEMETRY:
            raise RuntimeError("Mem0 telemetry must be disabled before import")
        return Memory.from_config(self._mem0_config())

    @staticmethod
    def _namespace(value: str) -> str:
        namespace = value.strip()
        if not namespace:
            raise ValueError("namespace must not be blank")
        return namespace

    @staticmethod
    def _native_results(response: Any) -> list[dict[str, Any]]:
        if isinstance(response, dict):
            results = response.get("results", [])
        elif isinstance(response, list):
            results = response
        else:
            results = []
        return [item for item in results if isinstance(item, dict)]

    @staticmethod
    def _normalized_record(
        native: Mapping[str, Any],
        *,
        state: LifecycleState = LifecycleState.ACTIVE,
    ) -> MemoryRecord:
        metadata = dict(native.get("metadata") or {})
        for key in ("score", "created_at", "updated_at", "role", "actor_id"):
            if native.get(key) is not None:
                metadata[f"_mem0_{key}"] = native[key]
        revision = int(metadata.pop("memlife_revision", 1))
        return MemoryRecord(
            memory_id=str(native["id"]),
            namespace=str(native.get("user_id") or metadata.pop("memlife_namespace")),
            content=str(native.get("memory", "")),
            metadata=metadata,
            state=state,
            revision=revision,
        )

    def _get_native(self, namespace: str, memory_id: str) -> dict[str, Any]:
        native = self._memory.get(memory_id)
        if not native or native.get("user_id") != namespace:
            raise MemoryNotFoundError(
                f"memory {memory_id!r} does not exist in namespace {namespace!r}"
            )
        return native

    def reset_namespace(self, namespace: str) -> None:
        self.require_supported(ProviderCapability.RESET_NAMESPACE)
        self._memory.delete_all(user_id=self._namespace(namespace))

    def write(self, command: WriteCommand) -> MemoryRecord:
        self.require_supported(ProviderCapability.WRITE)
        metadata = dict(command.metadata)
        metadata.update(
            {
                "memlife_namespace": command.namespace,
                "memlife_revision": 1,
            }
        )
        response = self._memory.add(
            command.content,
            user_id=command.namespace,
            metadata=metadata,
            infer=False,
        )
        results = self._native_results(response)
        if len(results) != 1 or not results[0].get("id"):
            raise RuntimeError(f"unexpected Mem0 add response: {response!r}")
        native = self._get_native(command.namespace, str(results[0]["id"]))
        return self._normalized_record(native)

    def query(self, command: QueryCommand) -> tuple[MemoryRecord, ...]:
        self.require_supported(ProviderCapability.QUERY)
        if LifecycleState.ACTIVE not in command.include_states:
            return ()
        filters = {"user_id": command.namespace}
        if command.query.strip():
            response = self._memory.search(
                command.query,
                filters=filters,
                top_k=command.limit,
            )
        else:
            response = self._memory.get_all(filters=filters, top_k=command.limit)
        return tuple(
            self._normalized_record(native)
            for native in self._native_results(response)
        )

    def update_or_supersede(self, command: SupersedeCommand) -> MemoryRecord:
        self.require_supported(ProviderCapability.UPDATE_OR_SUPERSEDE)
        current_native = self._get_native(command.namespace, command.memory_id)
        current = self._normalized_record(current_native)
        metadata = dict(command.metadata or {})
        metadata.update(
            {
                "memlife_namespace": command.namespace,
                "memlife_revision": current.revision + 1,
            }
        )
        self._memory.update(command.memory_id, text=command.content, metadata=metadata)
        updated_native = self._get_native(command.namespace, command.memory_id)
        return self._normalized_record(updated_native)

    def delete_or_invalidate(self, command: DeleteCommand) -> MemoryRecord:
        self.require_supported(ProviderCapability.DELETE_OR_INVALIDATE)
        if command.disposition is LifecycleState.REVOKED:
            raise UnsupportedCapabilityError(
                "Mem0 OSS delete is native deletion, not revocation"
            )
        current = self._normalized_record(
            self._get_native(command.namespace, command.memory_id)
        )
        self._memory.delete(command.memory_id)
        return current.model_copy(update={"state": LifecycleState.DELETED})

    def list_or_inspect(
        self,
        namespace: str,
        *,
        include_non_active: bool = True,
    ) -> tuple[MemoryRecord, ...]:
        self.require_supported(ProviderCapability.LIST_OR_INSPECT)
        # Mem0 get_all exposes current records only; include_non_active cannot
        # manufacture deleted/superseded records that this surface omits.
        response = self._memory.get_all(
            filters={"user_id": self._namespace(namespace)},
            top_k=1000,
        )
        return tuple(
            self._normalized_record(native)
            for native in self._native_results(response)
        )

    def native_history(self, memory_id: str) -> tuple[dict[str, Any], ...]:
        """Expose Mem0's native SQLite history without normalizing semantics."""

        return tuple(self._memory.history(memory_id))

    def close(self) -> None:
        vector_store = getattr(self._memory, "vector_store", None)
        client = getattr(vector_store, "client", None)
        if client is not None and hasattr(client, "close"):
            client.close()
        if hasattr(self._memory, "close"):
            self._memory.close()

    def restart(self) -> None:
        self.require_supported(ProviderCapability.RESTART)
        self.close()
        self._memory = self._create_memory()
