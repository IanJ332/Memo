"""Provider-independent execution of lifecycle benchmark scenarios."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from memlife.adapters.base import MemoryProviderAdapter, UnsupportedCapabilityError
from memlife.models.benchmark import (
    BenchmarkResult,
    NormalizedOutcome,
    OperationStatus,
)
from memlife.models.lifecycle import LifecycleState
from memlife.models.memory import DeleteCommand, MemoryRecord, QueryCommand
from memlife.models.memory import SupersedeCommand, WriteCommand
from memlife.scenarios.models import (
    LifecycleEvent,
    LifecycleScenario,
    LifecycleStep,
    ScenarioQuery,
)

Clock = Callable[[], datetime]
Timer = Callable[[], float]


def normalize_query_observation(
    records: Iterable[MemoryRecord],
    query: ScenarioQuery,
) -> tuple[NormalizedOutcome, tuple[str, ...], tuple[str, ...], bool]:
    """Classify exact fact visibility without judging security consequences."""

    observed = {record.content for record in records}
    current = tuple(fact for fact in query.current_facts if fact in observed)
    stale = tuple(fact for fact in query.stale_facts if fact in observed)
    if current and stale:
        outcome = NormalizedOutcome.CURRENT_AND_STALE
    elif current:
        outcome = NormalizedOutcome.CURRENT_ONLY
    elif stale:
        outcome = NormalizedOutcome.STALE_ONLY
    else:
        outcome = NormalizedOutcome.ABSENT
    correct = set(current) == set(query.current_facts) and not stale
    return outcome, current, stale, correct


class LifecycleRunner:
    """Execute scenario intent through an already-constructed adapter."""

    def __init__(
        self,
        adapter: MemoryProviderAdapter,
        *,
        clock: Clock | None = None,
        timer: Timer = perf_counter,
    ) -> None:
        self.adapter = adapter
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.timer = timer

    def run_suite(
        self, scenarios: Iterable[LifecycleScenario]
    ) -> tuple[BenchmarkResult, ...]:
        return tuple(
            result
            for scenario in scenarios
            for result in self.run_scenario(scenario)
        )

    def run_scenario(
        self, scenario: LifecycleScenario
    ) -> tuple[BenchmarkResult, ...]:
        self.adapter.reset_namespace(scenario.namespace)
        memory_ids: dict[str, str] = {}
        results: list[BenchmarkResult] = []
        for index, step in enumerate(scenario.lifecycle_steps):
            results.append(
                self._run_step(
                    scenario=scenario,
                    step=step,
                    step_index=index,
                    memory_ids=memory_ids,
                )
            )
        return tuple(results)

    def _inspect_safely(
        self, namespace: str
    ) -> tuple[tuple[MemoryRecord, ...], bool, str | None]:
        try:
            return self.adapter.list_or_inspect(namespace), True, None
        except UnsupportedCapabilityError as exc:
            return (), False, str(exc)
        except Exception as exc:  # provider diagnostics must not hide the step result
            return (), False, f"{type(exc).__name__}: {exc}"

    @staticmethod
    def _record_summary(records: Iterable[MemoryRecord]) -> list[dict[str, Any]]:
        return [
            {
                "memory_id": record.memory_id,
                "state": record.state.value,
                "revision": record.revision,
                "supersedes_id": record.supersedes_id,
                "superseded_by_id": record.superseded_by_id,
            }
            for record in records
        ]

    def _history_summary(
        self,
        memory_ids: Iterable[str],
        *,
        namespace: str,
    ) -> tuple[bool, dict[str, Any]]:
        summaries: dict[str, Any] = {}
        visible = False
        unsupported: list[str] = []
        errors: list[str] = []
        for memory_id in dict.fromkeys(memory_ids):
            try:
                entries = self.adapter.history_for(memory_id, namespace=namespace)
                visible = visible or bool(entries)
                events = []
                for entry in entries:
                    event = entry.get("event", entry.get("state", "record"))
                    events.append(str(event))
                summaries[memory_id] = {
                    "entry_count": len(entries),
                    "events": events,
                }
            except UnsupportedCapabilityError as exc:
                unsupported.append(str(exc))
                break
            except Exception as exc:
                errors.append(f"{type(exc).__name__}: {exc}")
        metadata: dict[str, Any] = {"history": summaries}
        if unsupported:
            metadata["history_unsupported"] = unsupported
        if errors:
            metadata["history_errors"] = errors
        return visible, metadata

    def _run_step(
        self,
        *,
        scenario: LifecycleScenario,
        step: LifecycleStep,
        step_index: int,
        memory_ids: dict[str, str],
    ) -> BenchmarkResult:
        before, before_supported, before_error = self._inspect_safely(
            scenario.namespace
        )
        native_operation = self.adapter.native_operation_for(step.event.value)
        provider_metadata: dict[str, Any] = dict(self.adapter.benchmark_metadata())
        provider_metadata.update(
            {
                "inspection_before_supported": before_supported,
                "records_before": self._record_summary(before),
            }
        )
        if before_error:
            provider_metadata["inspection_before_note"] = before_error

        status = OperationStatus.SUCCESS
        outcome: NormalizedOutcome | None = None
        query_text: str | None = None
        retrieved_current: tuple[str, ...] = ()
        retrieved_stale: tuple[str, ...] = ()
        current_state_correct: bool | None = None
        stale_state_visible: bool | None = None
        history_visible: bool | None = None
        unsupported_reason: str | None = None
        error: str | None = None
        observed: tuple[MemoryRecord, ...] = ()

        start = self.timer()
        try:
            observed, query = self._execute_step(
                scenario=scenario,
                step=step,
                memory_ids=memory_ids,
            )
            if query is not None:
                query_text = query.text
                (
                    outcome,
                    retrieved_current,
                    retrieved_stale,
                    current_state_correct,
                ) = normalize_query_observation(observed, query)
                stale_state_visible = bool(retrieved_stale)
            if step.event is LifecycleEvent.INSPECT:
                targets = (
                    [memory_ids[step.target_key]]
                    if step.target_key is not None
                    else list(memory_ids.values())
                )
                history_visible, history_metadata = self._history_summary(
                    targets,
                    namespace=scenario.namespace,
                )
                provider_metadata.update(history_metadata)
        except UnsupportedCapabilityError as exc:
            status = OperationStatus.UNSUPPORTED
            outcome = NormalizedOutcome.UNSUPPORTED
            unsupported_reason = str(exc)
        except Exception as exc:
            status = OperationStatus.ERROR
            outcome = NormalizedOutcome.ERROR
            error = f"{type(exc).__name__}: {exc}"
        latency_ms = round((self.timer() - start) * 1000, 3)

        after, after_supported, after_error = self._inspect_safely(scenario.namespace)
        provider_metadata.update(
            {
                "inspection_after_supported": after_supported,
                "records_after": self._record_summary(after),
            }
        )
        if after_error:
            provider_metadata["inspection_after_note"] = after_error

        return BenchmarkResult(
            scenario_id=scenario.scenario_id,
            provider=self.adapter.provider_name,
            provider_version=self.adapter.provider_version,
            namespace=scenario.namespace,
            step_index=step_index,
            intended_event=step.event,
            native_operation=native_operation,
            operation_status=status,
            normalized_outcome=outcome,
            memory_ids_before=tuple(record.memory_id for record in before),
            memory_ids_after=tuple(record.memory_id for record in after),
            query_text=query_text,
            retrieved_current=retrieved_current,
            retrieved_stale=retrieved_stale,
            observed_records=tuple(record.content for record in observed),
            expected_authoritative_state=scenario.expected_authoritative_state,
            current_state_correct=current_state_correct,
            stale_state_visible=stale_state_visible,
            history_visible=history_visible,
            provider_metadata=provider_metadata,
            unsupported_reason=unsupported_reason,
            latency_ms=latency_ms,
            error=error,
            timestamp=self.clock(),
        )

    def _execute_step(
        self,
        *,
        scenario: LifecycleScenario,
        step: LifecycleStep,
        memory_ids: dict[str, str],
    ) -> tuple[tuple[MemoryRecord, ...], ScenarioQuery | None]:
        if step.event is LifecycleEvent.WRITE:
            record = self.adapter.write(
                WriteCommand(namespace=scenario.namespace, content=str(step.content))
            )
            memory_ids[str(step.memory_key)] = record.memory_id
            return (record,), None

        if step.event in {LifecycleEvent.UPDATE, LifecycleEvent.SUPERSEDE}:
            record = self.adapter.update_or_supersede(
                SupersedeCommand(
                    namespace=scenario.namespace,
                    memory_id=memory_ids[str(step.target_key)],
                    content=str(step.content),
                )
            )
            memory_ids[str(step.memory_key)] = record.memory_id
            return (record,), None

        if step.event in {LifecycleEvent.REVOKE, LifecycleEvent.DELETE}:
            disposition = (
                LifecycleState.REVOKED
                if step.event is LifecycleEvent.REVOKE
                else LifecycleState.DELETED
            )
            record = self.adapter.delete_or_invalidate(
                DeleteCommand(
                    namespace=scenario.namespace,
                    memory_id=memory_ids[str(step.target_key)],
                    disposition=disposition,
                )
            )
            return (record,), None

        if step.event is LifecycleEvent.RESTART:
            self.adapter.restart()
            return (), None

        if step.event is LifecycleEvent.QUERY:
            query = scenario.query(str(step.query_id))
            records = self.adapter.query(
                QueryCommand(namespace=scenario.namespace, query=query.text)
            )
            return records, query

        if step.event is LifecycleEvent.INSPECT:
            return self.adapter.list_or_inspect(scenario.namespace), None

        raise ValueError(f"unsupported lifecycle event: {step.event.value}")


def run_scenario(
    adapter: MemoryProviderAdapter,
    scenario: LifecycleScenario,
) -> tuple[BenchmarkResult, ...]:
    """Convenience entry point for one scenario."""

    return LifecycleRunner(adapter).run_scenario(scenario)


def run_suite(
    adapter: MemoryProviderAdapter,
    scenarios: Iterable[LifecycleScenario],
) -> tuple[BenchmarkResult, ...]:
    """Convenience entry point for an ordered suite."""

    return LifecycleRunner(adapter).run_suite(scenarios)
