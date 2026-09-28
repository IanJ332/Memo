"""Provider-independent contract for lifecycle experiment adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Mapping

from memlife.models.memory import (
    DeleteCommand,
    MemoryRecord,
    QueryCommand,
    SupersedeCommand,
    WriteCommand,
)


class CapabilitySupport(str, Enum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"


class ProviderCapability(str, Enum):
    RESET_NAMESPACE = "reset_namespace"
    WRITE = "write"
    QUERY = "query"
    UPDATE_OR_SUPERSEDE = "update_or_supersede"
    DELETE_OR_INVALIDATE = "delete_or_invalidate"
    LIST_OR_INSPECT = "list_or_inspect"
    RESTART = "restart"


class AdapterError(RuntimeError):
    """Base class for normalized adapter errors."""


class UnsupportedCapabilityError(AdapterError):
    """Raised instead of silently emulating a provider operation."""


class MemoryNotFoundError(AdapterError):
    """Raised when a normalized memory identifier cannot be found."""


class InvalidLifecycleTransitionError(AdapterError):
    """Raised when an operation cannot apply to the record's current state."""


class MemoryProviderAdapter(ABC):
    """Minimal normalized surface required by lifecycle experiments.

    Implementations must report every capability as supported or unsupported.
    A provider may reject unsupported operations; adapters must not manufacture
    lifecycle behavior the underlying provider does not have.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return a stable, human-readable provider identifier."""

    @property
    def provider_version(self) -> str | None:
        """Return a provider version when one is known."""

        return None

    @property
    @abstractmethod
    def capabilities(self) -> Mapping[ProviderCapability, CapabilitySupport]:
        """Declare support for every normalized operation."""

    def support_for(self, capability: ProviderCapability) -> CapabilitySupport:
        try:
            return self.capabilities[capability]
        except KeyError as exc:
            raise AdapterError(
                f"{self.provider_name} did not declare {capability.value}"
            ) from exc

    def require_supported(self, capability: ProviderCapability) -> None:
        if self.support_for(capability) is CapabilitySupport.UNSUPPORTED:
            raise UnsupportedCapabilityError(
                f"{self.provider_name} does not support {capability.value}"
            )

    def native_operation_for(self, intended_event: str) -> str:
        """Describe the provider-native action used for benchmark intent."""

        return intended_event.casefold()

    def benchmark_metadata(self) -> Mapping[str, Any]:
        """Return a small sanitized provider description for result records."""

        return {}

    def history_for(self, memory_id: str) -> tuple[Mapping[str, Any], ...]:
        """Expose native history when available, without emulation."""

        raise UnsupportedCapabilityError(
            f"{self.provider_name} does not expose native history"
        )

    @abstractmethod
    def reset_namespace(self, namespace: str) -> None:
        """Reset one isolated experiment namespace."""

    @abstractmethod
    def write(self, command: WriteCommand) -> MemoryRecord:
        """Create a memory and return its normalized representation."""

    @abstractmethod
    def query(self, command: QueryCommand) -> tuple[MemoryRecord, ...]:
        """Return normalized records matching a provider query."""

    @abstractmethod
    def update_or_supersede(self, command: SupersedeCommand) -> MemoryRecord:
        """Update or supersede a memory, preserving provider semantics."""

    @abstractmethod
    def delete_or_invalidate(self, command: DeleteCommand) -> MemoryRecord:
        """Delete or invalidate a memory, preserving provider semantics."""

    @abstractmethod
    def list_or_inspect(
        self,
        namespace: str,
        *,
        include_non_active: bool = True,
    ) -> tuple[MemoryRecord, ...]:
        """Inspect records visible through the provider's diagnostic surface."""

    @abstractmethod
    def restart(self) -> None:
        """Exercise provider restart semantics when explicitly supported."""
