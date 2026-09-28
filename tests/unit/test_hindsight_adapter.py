from __future__ import annotations

from memlife.adapters.base import CapabilitySupport, ProviderCapability
from memlife.adapters.hindsight import HINDSIGHT_VERSION, HindsightMemoryAdapter
from memlife.adapters.hindsight import phase04_manifest_configuration
from memlife.models.lifecycle import LifecycleState
from memlife.models.memory import DeleteCommand, QueryCommand, SupersedeCommand
from memlife.models.memory import WriteCommand
from memlife.models.provenance import MemorySurface, ProvenanceStatus
from tests.contract.provider_contract import run_lifecycle_smoke
from tests.fakes.hindsight import FakeHindsightTransport


def _adapter() -> tuple[HindsightMemoryAdapter, FakeHindsightTransport, list[str]]:
    transport = FakeHindsightTransport()
    restarts: list[str] = []
    adapter = HindsightMemoryAdapter(
        transport,
        restart_callback=lambda: restarts.append("restart"),
        poll_interval_seconds=0.001,
    )
    return adapter, transport, restarts


def test_configuration_is_frozen_and_sanitized() -> None:
    config = phase04_manifest_configuration()
    assert config["provider_version"] == HINDSIGHT_VERSION == "0.10.1"
    assert config["internal_llm_model"] == "gpt-oss-120b"
    assert config["embedding_provider"] == "onnx"
    assert config["reranker_provider"] == "rrf"
    assert "api_key" not in config


def test_capabilities_depend_only_on_real_restart_control() -> None:
    adapter, _, _ = _adapter()
    assert set(adapter.capabilities) == set(ProviderCapability)
    assert all(value is CapabilitySupport.SUPPORTED for value in adapter.capabilities.values())
    no_controller = HindsightMemoryAdapter(FakeHindsightTransport())
    assert (
        no_controller.support_for(ProviderCapability.RESTART)
        is CapabilitySupport.UNSUPPORTED
    )


def test_fake_transport_satisfies_provider_contract() -> None:
    adapter, _, _ = _adapter()
    run_lifecycle_smoke(adapter, namespace="hindsight-contract")


def test_native_edit_invalidation_inspection_and_document_delete() -> None:
    adapter, _, _ = _adapter()
    namespace = "hindsight-unit"
    first = adapter.write(WriteCommand(namespace=namespace, content="version one"))
    edited = adapter.update_or_supersede(
        SupersedeCommand(
            namespace=namespace,
            memory_id=first.memory_id,
            content="version two",
        )
    )
    assert edited.memory_id == first.memory_id
    assert edited.revision == 2
    revoked = adapter.delete_or_invalidate(
        DeleteCommand(
            namespace=namespace,
            memory_id=edited.memory_id,
            disposition=LifecycleState.REVOKED,
        )
    )
    assert revoked.state is LifecycleState.REVOKED
    assert adapter.query(QueryCommand(namespace=namespace, query="version")) == ()
    assert adapter.list_or_inspect(namespace) == (revoked,)

    adapter.reset_namespace(namespace)
    active = adapter.write(WriteCommand(namespace=namespace, content="delete me"))
    deleted = adapter.delete_or_invalidate(
        DeleteCommand(namespace=namespace, memory_id=active.memory_id)
    )
    assert deleted.state is LifecycleState.DELETED
    assert adapter.list_or_inspect(namespace) == ()


def test_observation_surface_and_lineage_are_only_known_when_exposed() -> None:
    adapter, transport, _ = _adapter()
    source = adapter.write(
        WriteCommand(namespace="derived", content="Project Cedar is handled by Alice.")
    )
    native = transport.add_observation(
        "derived", text="Alice handles Project Cedar.", source_ids=[source.memory_id]
    )
    observation = adapter._normalized_record("derived", native)
    assert adapter.trace_surface_for(source) is MemorySurface.SOURCE
    assert adapter.trace_provenance_status_for(source) is ProvenanceStatus.UNKNOWN
    assert adapter.trace_surface_for(observation) is MemorySurface.DERIVED
    assert adapter.trace_provenance_status_for(observation) is ProvenanceStatus.KNOWN
    assert adapter.trace_source_provider_ids_for(observation) == (source.memory_id,)


def test_trigger_derivation_and_restart_use_explicit_completion() -> None:
    adapter, _, restarts = _adapter()
    result = adapter.trigger_derivation("derive")
    assert result["status"] == "completed"
    assert adapter.benchmark_metadata()["quiescence_criterion"] == (
        "provider operation status=completed"
    )
    adapter.restart()
    assert restarts == ["restart"]
