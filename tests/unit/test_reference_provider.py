"""Reference-only behavior beyond the generic provider contract."""

import pytest

from memlife.adapters.base import (
    InvalidLifecycleTransitionError,
    MemoryNotFoundError,
)
from memlife.adapters.reference import ReferenceMemoryAdapter
from memlife.models.lifecycle import LifecycleState
from memlife.models.memory import DeleteCommand, QueryCommand, SupersedeCommand, WriteCommand


def test_reference_retains_deterministic_history_and_restart_is_noop() -> None:
    adapter = ReferenceMemoryAdapter()
    namespace = "history"
    first = adapter.write(WriteCommand(namespace=namespace, content="v1"))
    second = adapter.update_or_supersede(
        SupersedeCommand(namespace=namespace, memory_id=first.memory_id, content="v2")
    )
    adapter.delete_or_invalidate(
        DeleteCommand(
            namespace=namespace,
            memory_id=second.memory_id,
            disposition=LifecycleState.REVOKED,
        )
    )

    adapter.restart()
    records = adapter.list_or_inspect(namespace)
    assert [record.memory_id for record in records] == ["memory-0001", "memory-0002"]
    assert [record.state for record in records] == [
        LifecycleState.SUPERSEDED,
        LifecycleState.REVOKED,
    ]
    assert adapter.query(QueryCommand(namespace=namespace)) == ()


def test_reset_is_namespace_scoped_and_resets_identifier_sequence() -> None:
    adapter = ReferenceMemoryAdapter()
    adapter.write(WriteCommand(namespace="keep", content="kept"))
    adapter.write(WriteCommand(namespace="reset", content="old"))

    adapter.reset_namespace("reset")
    replacement = adapter.write(WriteCommand(namespace="reset", content="new"))

    assert replacement.memory_id == "memory-0001"
    assert len(adapter.query(QueryCommand(namespace="keep"))) == 1


def test_missing_and_non_active_transitions_are_explicit_errors() -> None:
    adapter = ReferenceMemoryAdapter()
    with pytest.raises(MemoryNotFoundError):
        adapter.delete_or_invalidate(
            DeleteCommand(namespace="missing", memory_id="memory-0001")
        )

    record = adapter.write(WriteCommand(namespace="state", content="v1"))
    adapter.delete_or_invalidate(
        DeleteCommand(namespace="state", memory_id=record.memory_id)
    )
    with pytest.raises(InvalidLifecycleTransitionError):
        adapter.update_or_supersede(
            SupersedeCommand(
                namespace="state",
                memory_id=record.memory_id,
                content="v2",
            )
        )
