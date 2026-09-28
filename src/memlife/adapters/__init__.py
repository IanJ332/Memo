"""Memory provider adapter interfaces and implementations."""

from memlife.adapters.base import (
    AdapterError,
    CapabilitySupport,
    InvalidLifecycleTransitionError,
    MemoryNotFoundError,
    MemoryProviderAdapter,
    ProviderCapability,
    UnsupportedCapabilityError,
)
from memlife.adapters.reference import ReferenceMemoryAdapter
from memlife.adapters.hindsight import HindsightMemoryAdapter

__all__ = [
    "AdapterError",
    "CapabilitySupport",
    "InvalidLifecycleTransitionError",
    "MemoryNotFoundError",
    "MemoryProviderAdapter",
    "HindsightMemoryAdapter",
    "ProviderCapability",
    "ReferenceMemoryAdapter",
    "UnsupportedCapabilityError",
]
