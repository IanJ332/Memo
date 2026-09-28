"""Local-only Mem0 OSS 2.2.1 characterization and durability checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from memlife.adapters.mem0 import MEM0_VERSION, Mem0MemoryAdapter
from memlife.models.lifecycle import LifecycleState
from memlife.models.memory import DeleteCommand, QueryCommand, SupersedeCommand, WriteCommand
from tests.contract.provider_contract import run_lifecycle_smoke

pytestmark = pytest.mark.mem0_integration


@pytest.fixture
def mem0_adapter(monkeypatch: pytest.MonkeyPatch) -> Mem0MemoryAdapter:
    """Create Mem0 from the pre-fetched cache and forbid LLM inference."""

    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    adapter = Mem0MemoryAdapter.from_local_runtime(Path.cwd())
    llm_calls: list[object] = []

    def fail_on_llm_call(*args: object, **kwargs: object) -> None:
        llm_calls.append((args, kwargs))
        pytest.fail("Mem0 attempted an LLM call during the infer=False baseline")

    adapter.native_memory.llm.generate_response = fail_on_llm_call
    adapter._phase02a_llm_calls = llm_calls  # type: ignore[attr-defined]
    try:
        yield adapter
    finally:
        adapter.close()


def test_mem0_uses_required_oss_mode_and_reusable_contract(
    mem0_adapter: Mem0MemoryAdapter,
) -> None:
    from importlib.metadata import version

    from mem0 import Memory
    from mem0.memory.telemetry import MEM0_TELEMETRY

    assert version("mem0ai") == MEM0_VERSION
    assert isinstance(mem0_adapter.native_memory, Memory)
    assert MEM0_TELEMETRY is False

    run_lifecycle_smoke(
        mem0_adapter,
        namespace="memlife-phase02-reusable-contract",
    )
    assert mem0_adapter._phase02a_llm_calls == []  # type: ignore[attr-defined]


def test_mem0_native_cedar_lifecycle(mem0_adapter: Mem0MemoryAdapter) -> None:
    namespace = "memlife-phase02-cedar-lifecycle"
    version_one_text = "Project Cedar reports may be sent to Alice."
    version_two_text = "Project Cedar reports may be sent only to Bob."
    mem0_adapter.reset_namespace(namespace)

    version_one = mem0_adapter.write(
        WriteCommand(namespace=namespace, content=version_one_text)
    )
    queried_v1 = mem0_adapter.query(
        QueryCommand(namespace=namespace, query=version_one_text)
    )
    assert any(record.memory_id == version_one.memory_id for record in queried_v1)

    version_two = mem0_adapter.update_or_supersede(
        SupersedeCommand(
            namespace=namespace,
            memory_id=version_one.memory_id,
            content=version_two_text,
        )
    )
    assert version_two.memory_id == version_one.memory_id
    assert version_two.revision == 2
    assert version_two.supersedes_id is None

    queried_v2 = mem0_adapter.query(
        QueryCommand(namespace=namespace, query=version_two_text)
    )
    assert any(
        record.memory_id == version_two.memory_id
        and record.content == version_two_text
        for record in queried_v2
    )
    inspected = mem0_adapter.list_or_inspect(namespace)
    assert [(record.memory_id, record.content) for record in inspected] == [
        (version_two.memory_id, version_two_text)
    ]

    history_before_delete = mem0_adapter.native_history(version_two.memory_id)
    assert [entry["event"] for entry in history_before_delete[-2:]] == [
        "ADD",
        "UPDATE",
    ]
    deleted = mem0_adapter.delete_or_invalidate(
        DeleteCommand(namespace=namespace, memory_id=version_two.memory_id)
    )
    assert deleted.state is LifecycleState.DELETED
    assert mem0_adapter.query(
        QueryCommand(namespace=namespace, query=version_two_text)
    ) == ()
    assert mem0_adapter.list_or_inspect(namespace) == ()

    history_after_delete = mem0_adapter.native_history(version_two.memory_id)
    assert len(history_after_delete) > len(history_before_delete)
    assert history_after_delete[-1]["event"] == "DELETE"
    assert history_after_delete[-1]["is_deleted"] is True
    assert mem0_adapter._phase02a_llm_calls == []  # type: ignore[attr-defined]


def test_mem0_restart_write_and_delete_sanity(
    mem0_adapter: Mem0MemoryAdapter,
) -> None:
    namespace = "memlife-phase02-restart-sanity"
    canary_text = "Phase 02A local restart canary."
    mem0_adapter.reset_namespace(namespace)
    canary = mem0_adapter.write(
        WriteCommand(namespace=namespace, content=canary_text)
    )
    assert mem0_adapter.query(
        QueryCommand(namespace=namespace, query=canary_text)
    )

    mem0_adapter.restart()
    after_write_restart = mem0_adapter.query(
        QueryCommand(namespace=namespace, query=canary_text)
    )
    assert any(record.memory_id == canary.memory_id for record in after_write_restart)

    mem0_adapter.delete_or_invalidate(
        DeleteCommand(namespace=namespace, memory_id=canary.memory_id)
    )
    mem0_adapter.restart()
    assert mem0_adapter.query(
        QueryCommand(namespace=namespace, query=canary_text)
    ) == ()
    assert mem0_adapter.native_history(canary.memory_id)[-1]["event"] == "DELETE"
