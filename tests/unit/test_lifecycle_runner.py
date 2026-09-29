"""Deterministic reference validation for the lifecycle runner."""

from __future__ import annotations

from datetime import datetime, timezone

from memlife.adapters.base import UnsupportedCapabilityError
from memlife.adapters.reference import ReferenceMemoryAdapter
from memlife.models.benchmark import NormalizedOutcome, OperationStatus
from memlife.models.lifecycle import LifecycleState
from memlife.models.memory import (
    DeleteCommand,
    MemoryRecord,
    QueryCommand,
    SupersedeCommand,
    WriteCommand,
)
from memlife.runner.lifecycle import LifecycleRunner, normalize_query_observation
from memlife.scenarios import LifecycleEvent, canonical_scenarios
from memlife.scenarios.models import ScenarioQuery

FIXED_TIME = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)


def _record(content: str, memory_id: str) -> MemoryRecord:
    return MemoryRecord(
        memory_id=memory_id,
        namespace="normalization",
        content=content,
        state=LifecycleState.ACTIVE,
        revision=1,
    )


def test_normalization_covers_current_stale_and_absent_observations() -> None:
    query = ScenarioQuery(
        query_id="versions",
        text="Project Cedar",
        current_facts=("v2",),
        stale_facts=("v1",),
    )
    current = _record("v2", "current")
    stale = _record("v1", "stale")

    assert normalize_query_observation((current,), query)[0] is NormalizedOutcome.CURRENT_ONLY
    assert normalize_query_observation((current, stale), query)[0] is NormalizedOutcome.CURRENT_AND_STALE
    assert normalize_query_observation((stale,), query)[0] is NormalizedOutcome.STALE_ONLY
    assert normalize_query_observation((), query)[0] is NormalizedOutcome.ABSENT


def test_reference_provider_runs_full_suite_in_scenario_and_step_order() -> None:
    scenarios = canonical_scenarios()
    results = LifecycleRunner(
        ReferenceMemoryAdapter(),
        clock=lambda: FIXED_TIME,
        timer=lambda: 1.0,
    ).run_suite(scenarios)

    assert len(results) == sum(len(s.lifecycle_steps) for s in scenarios) == 24
    assert [result.scenario_id for result in results[:3]] == ["baseline"] * 3
    for scenario in scenarios:
        scenario_results = [r for r in results if r.scenario_id == scenario.scenario_id]
        assert [r.step_index for r in scenario_results] == list(
            range(len(scenario.lifecycle_steps))
        )
    assert all(result.operation_status is OperationStatus.SUCCESS for result in results)
    assert all(result.timestamp == FIXED_TIME for result in results)
    assert all(result.latency_ms == 0 for result in results)


def test_runner_resets_only_scenario_namespace() -> None:
    adapter = ReferenceMemoryAdapter()
    sentinel = adapter.write(WriteCommand(namespace="outside", content="keep me"))
    scenario = canonical_scenarios()[0]
    adapter.write(WriteCommand(namespace=scenario.namespace, content="remove me"))

    LifecycleRunner(adapter).run_scenario(scenario)

    assert adapter.query(QueryCommand(namespace="outside")) == (sentinel,)
    inspected = adapter.list_or_inspect(scenario.namespace)
    assert [record.content for record in inspected] == list(
        scenario.expected_authoritative_state
    )


class UnsupportedRevocationAdapter(ReferenceMemoryAdapter):
    def delete_or_invalidate(self, command: DeleteCommand) -> MemoryRecord:
        if command.disposition is LifecycleState.REVOKED:
            raise UnsupportedCapabilityError("fixture has no native revocation")
        return super().delete_or_invalidate(command)


def test_unsupported_operation_is_recorded_without_emulation() -> None:
    scenario = next(s for s in canonical_scenarios() if s.scenario_id == "revocation")
    results = LifecycleRunner(UnsupportedRevocationAdapter()).run_scenario(scenario)
    revoke = next(r for r in results if r.intended_event is LifecycleEvent.REVOKE)
    query = next(r for r in results if r.intended_event is LifecycleEvent.QUERY)

    assert revoke.operation_status is OperationStatus.UNSUPPORTED
    assert revoke.normalized_outcome is NormalizedOutcome.UNSUPPORTED
    assert revoke.unsupported_reason == "fixture has no native revocation"
    assert query.normalized_outcome is NormalizedOutcome.STALE_ONLY


class QueryErrorAdapter(ReferenceMemoryAdapter):
    def query(self, command: QueryCommand) -> tuple[MemoryRecord, ...]:
        raise RuntimeError("synthetic provider query failure")


def test_provider_error_becomes_a_structured_result_and_suite_continues() -> None:
    results = LifecycleRunner(QueryErrorAdapter()).run_scenario(canonical_scenarios()[0])
    assert [result.operation_status for result in results] == [
        OperationStatus.SUCCESS,
        OperationStatus.ERROR,
        OperationStatus.SUCCESS,
    ]
    assert results[1].normalized_outcome is NormalizedOutcome.ERROR
    assert results[1].error == "RuntimeError: synthetic provider query failure"


class RestartRecordingAdapter(ReferenceMemoryAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.restart_count = 0

    def restart(self) -> None:
        self.restart_count += 1
        super().restart()


def test_restart_step_executes_and_deleted_fact_remains_absent() -> None:
    adapter = RestartRecordingAdapter()
    scenario = next(
        s for s in canonical_scenarios() if s.scenario_id == "delete-restart"
    )
    results = LifecycleRunner(adapter).run_scenario(scenario)
    after_restart = [
        result
        for result in results
        if result.intended_event is LifecycleEvent.QUERY
    ][-1]

    assert adapter.restart_count == 1
    assert after_restart.normalized_outcome is NormalizedOutcome.ABSENT
    inspect = results[-1]
    assert inspect.history_visible is True
    assert inspect.provider_metadata["history"]["memory-0001"]["events"] == [
        "deleted"
    ]


class UnsupportedSupersessionAdapter(ReferenceMemoryAdapter):
    def update_or_supersede(self, command: SupersedeCommand) -> MemoryRecord:
        raise UnsupportedCapabilityError("fixture has no native supersession")


class ErroredSupersessionAdapter(ReferenceMemoryAdapter):
    def update_or_supersede(self, command: SupersedeCommand) -> MemoryRecord:
        raise RuntimeError("synthetic supersession failure")


def _supersession_results(adapter):
    scenario = next(
        item for item in canonical_scenarios() if item.scenario_id == "supersession"
    )
    return LifecycleRunner(adapter).run_scenario(scenario)


def test_supported_producer_materializes_target_for_inspection() -> None:
    inspect = _supersession_results(ReferenceMemoryAdapter())[-1]
    assert inspect.intended_event is LifecycleEvent.INSPECT
    assert inspect.operation_status is OperationStatus.SUCCESS
    assert inspect.error is None


def test_unsupported_producer_propagates_only_to_dependent_target() -> None:
    results = _supersession_results(UnsupportedSupersessionAdapter())
    supersede, old_query, new_query, inspect = results[1:]
    assert supersede.operation_status is OperationStatus.UNSUPPORTED
    assert old_query.operation_status is OperationStatus.SUCCESS
    assert new_query.operation_status is OperationStatus.SUCCESS
    assert inspect.operation_status is OperationStatus.UNSUPPORTED
    assert inspect.unsupported_reason == (
        "target v2 was not materialized because its producer operation was unsupported"
    )
    assert inspect.error is None


def test_errored_producer_propagates_error_not_unsupported() -> None:
    results = _supersession_results(ErroredSupersessionAdapter())
    inspect = results[-1]
    assert results[1].operation_status is OperationStatus.ERROR
    assert inspect.operation_status is OperationStatus.ERROR
    assert inspect.normalized_outcome is NormalizedOutcome.ERROR
    assert inspect.unsupported_reason is None
    assert "target v2 was not materialized" in str(inspect.error)
    assert "KeyError" not in str(inspect.error)
