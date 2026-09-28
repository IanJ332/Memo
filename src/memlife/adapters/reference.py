"""Deterministic in-memory control adapter for contract validation."""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from memlife.adapters.base import (
    CapabilitySupport,
    InvalidLifecycleTransitionError,
    MemoryNotFoundError,
    MemoryProviderAdapter,
    ProviderCapability,
)
from memlife.models.lifecycle import LifecycleState
from memlife.models.memory import (
    DeleteCommand,
    MemoryRecord,
    QueryCommand,
    SupersedeCommand,
    WriteCommand,
)

_ALL_SUPPORTED = MappingProxyType(
    {capability: CapabilitySupport.SUPPORTED for capability in ProviderCapability}
)


class ReferenceMemoryAdapter(MemoryProviderAdapter):
    """Small known-good control with deterministic, namespace-local state.

    ``restart`` is intentionally a logical no-op. The adapter has no external
    process or durable backend, so it retains its in-process records and offers
    only a stable hook for validating runner plumbing.
    """

    def __init__(self) -> None:
        self._records: dict[str, dict[str, MemoryRecord]] = {}
        self._counters: dict[str, int] = {}

    @property
    def provider_name(self) -> str:
        return "reference-in-memory"

    @property
    def capabilities(self) -> Mapping[ProviderCapability, CapabilitySupport]:
        return _ALL_SUPPORTED

    @staticmethod
    def _namespace(value: str) -> str:
        namespace = value.strip()
        if not namespace:
            raise ValueError("namespace must not be blank")
        return namespace

    def _namespace_records(self, namespace: str) -> dict[str, MemoryRecord]:
        return self._records.setdefault(self._namespace(namespace), {})

    def _next_id(self, namespace: str) -> str:
        self._counters[namespace] = self._counters.get(namespace, 0) + 1
        return f"memory-{self._counters[namespace]:04d}"

    def _record(self, namespace: str, memory_id: str) -> MemoryRecord:
        try:
            return self._namespace_records(namespace)[memory_id]
        except KeyError as exc:
            raise MemoryNotFoundError(
                f"memory {memory_id!r} does not exist in namespace {namespace!r}"
            ) from exc

    @staticmethod
    def _require_active(record: MemoryRecord) -> None:
        if record.state is not LifecycleState.ACTIVE:
            raise InvalidLifecycleTransitionError(
                f"memory {record.memory_id!r} is {record.state.value}, not active"
            )

    def reset_namespace(self, namespace: str) -> None:
        self.require_supported(ProviderCapability.RESET_NAMESPACE)
        normalized = self._namespace(namespace)
        self._records[normalized] = {}
        self._counters[normalized] = 0

    def write(self, command: WriteCommand) -> MemoryRecord:
        self.require_supported(ProviderCapability.WRITE)
        records = self._namespace_records(command.namespace)
        memory_id = self._next_id(command.namespace)
        record = MemoryRecord(
            memory_id=memory_id,
            namespace=command.namespace,
            content=command.content,
            metadata=dict(command.metadata),
            state=LifecycleState.ACTIVE,
            revision=1,
        )
        records[memory_id] = record
        return record

    def query(self, command: QueryCommand) -> tuple[MemoryRecord, ...]:
        self.require_supported(ProviderCapability.QUERY)
        needle = command.query.casefold().strip()
        matches = (
            record
            for record in self._namespace_records(command.namespace).values()
            if record.state in command.include_states
            and (not needle or needle in record.content.casefold())
        )
        return tuple(list(matches)[: command.limit])

    def update_or_supersede(self, command: SupersedeCommand) -> MemoryRecord:
        self.require_supported(ProviderCapability.UPDATE_OR_SUPERSEDE)
        records = self._namespace_records(command.namespace)
        current = self._record(command.namespace, command.memory_id)
        self._require_active(current)

        replacement_id = self._next_id(command.namespace)
        replacement = MemoryRecord(
            memory_id=replacement_id,
            namespace=command.namespace,
            content=command.content,
            metadata=(
                dict(current.metadata)
                if command.metadata is None
                else dict(command.metadata)
            ),
            state=LifecycleState.ACTIVE,
            revision=current.revision + 1,
            supersedes_id=current.memory_id,
        )
        records[current.memory_id] = current.model_copy(
            update={
                "state": LifecycleState.SUPERSEDED,
                "superseded_by_id": replacement_id,
            }
        )
        records[replacement_id] = replacement
        return replacement

    def delete_or_invalidate(self, command: DeleteCommand) -> MemoryRecord:
        self.require_supported(ProviderCapability.DELETE_OR_INVALIDATE)
        records = self._namespace_records(command.namespace)
        current = self._record(command.namespace, command.memory_id)
        self._require_active(current)
        updated = current.model_copy(update={"state": command.disposition})
        records[current.memory_id] = updated
        return updated

    def list_or_inspect(
        self,
        namespace: str,
        *,
        include_non_active: bool = True,
    ) -> tuple[MemoryRecord, ...]:
        self.require_supported(ProviderCapability.LIST_OR_INSPECT)
        records = self._namespace_records(namespace).values()
        if not include_non_active:
            records = (
                record
                for record in records
                if record.state is LifecycleState.ACTIVE
            )
        return tuple(records)

    def restart(self) -> None:
        self.require_supported(ProviderCapability.RESTART)
        # Deliberately retain records: there is no external process to restart.
