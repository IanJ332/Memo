"""Reusable lifecycle smoke workflow for provider adapters."""

from collections.abc import Callable

from memlife.adapters.base import (
    CapabilitySupport,
    MemoryProviderAdapter,
    ProviderCapability,
)
from memlife.models.lifecycle import LifecycleState
from memlife.models.memory import (
    DeleteCommand,
    QueryCommand,
    SupersedeCommand,
    WriteCommand,
)

AdapterFactory = Callable[[], MemoryProviderAdapter]
SMOKE_CAPABILITIES = frozenset(
    {
        ProviderCapability.RESET_NAMESPACE,
        ProviderCapability.WRITE,
        ProviderCapability.QUERY,
        ProviderCapability.UPDATE_OR_SUPERSEDE,
        ProviderCapability.DELETE_OR_INVALIDATE,
        ProviderCapability.LIST_OR_INSPECT,
    }
)


def assert_complete_capability_declaration(adapter: MemoryProviderAdapter) -> None:
    """Ensure unsupported behavior is declared rather than omitted."""

    assert set(adapter.capabilities) == set(ProviderCapability)
    assert all(
        support in {CapabilitySupport.SUPPORTED, CapabilitySupport.UNSUPPORTED}
        for support in adapter.capabilities.values()
    )


def run_lifecycle_smoke(
    adapter: MemoryProviderAdapter,
    namespace: str = "contract-smoke",
) -> None:
    """Exercise only behavior guaranteed by the normalized smoke profile."""

    assert_complete_capability_declaration(adapter)
    for capability in SMOKE_CAPABILITIES:
        assert adapter.support_for(capability) is CapabilitySupport.SUPPORTED

    adapter.reset_namespace(namespace)
    assert adapter.list_or_inspect(namespace) == ()

    version_one = adapter.write(
        WriteCommand(namespace=namespace, content="phase-one-version-one")
    )
    queried_v1 = adapter.query(
        QueryCommand(namespace=namespace, query="version-one")
    )
    assert tuple(record.memory_id for record in queried_v1) == (
        version_one.memory_id,
    )

    version_two = adapter.update_or_supersede(
        SupersedeCommand(
            namespace=namespace,
            memory_id=version_one.memory_id,
            content="phase-one-version-two",
        )
    )
    queried_current = adapter.query(
        QueryCommand(namespace=namespace, query="phase-one")
    )
    assert tuple(record.memory_id for record in queried_current) == (
        version_two.memory_id,
    )
    assert queried_current[0].state is LifecycleState.ACTIVE

    deleted = adapter.delete_or_invalidate(
        DeleteCommand(namespace=namespace, memory_id=version_two.memory_id)
    )
    assert deleted.state in {LifecycleState.DELETED, LifecycleState.REVOKED}
    assert adapter.query(QueryCommand(namespace=namespace, query="phase-one")) == ()


class ProviderContract:
    """Subclass in each adapter test module to reuse the common smoke path."""

    adapter_factory: AdapterFactory

    def test_capabilities_are_explicit(self) -> None:
        assert_complete_capability_declaration(self.adapter_factory())

    def test_lifecycle_smoke_workflow(self) -> None:
        run_lifecycle_smoke(self.adapter_factory())
