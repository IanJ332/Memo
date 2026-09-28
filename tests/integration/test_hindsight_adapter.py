"""Opt-in tests against a real self-hosted Hindsight 0.10.1 service."""

import os

import pytest

from memlife.adapters.hindsight import HindsightMemoryAdapter
from memlife.models.lifecycle import LifecycleState
from memlife.models.memory import DeleteCommand, QueryCommand, WriteCommand

pytestmark = pytest.mark.hindsight_integration


@pytest.fixture
def hindsight_adapter() -> HindsightMemoryAdapter:
    if os.environ.get("MEMLIFE_RUN_HINDSIGHT_INTEGRATION") != "1":
        pytest.skip("set MEMLIFE_RUN_HINDSIGHT_INTEGRATION=1 for the real service")
    adapter = HindsightMemoryAdapter.from_environment()
    adapter.verify_server()
    return adapter


def test_real_retain_recall_inspect_and_invalidate(
    hindsight_adapter: HindsightMemoryAdapter,
) -> None:
    namespace = "phase-04-pytest-smoke"
    hindsight_adapter.reset_namespace(namespace)
    record = hindsight_adapter.write(
        WriteCommand(
            namespace=namespace,
            content="Project Cedar reports are handled by Alice.",
        )
    )
    assert hindsight_adapter.query(
        QueryCommand(namespace=namespace, query="Who handles Project Cedar reports?")
    )
    assert record.memory_id in {
        item.memory_id for item in hindsight_adapter.list_or_inspect(namespace)
    }
    revoked = hindsight_adapter.delete_or_invalidate(
        DeleteCommand(
            namespace=namespace,
            memory_id=record.memory_id,
            disposition=LifecycleState.REVOKED,
        )
    )
    assert revoked.state is LifecycleState.REVOKED
