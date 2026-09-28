"""Build provenance and enforcement traces beside lifecycle benchmark output."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from memlife.adapters.base import MemoryProviderAdapter
from memlife.enforcement import CandidateFilter, EnforcementContext, PassThroughFilter
from memlife.models.benchmark import BenchmarkResult, OperationStatus
from memlife.models.provenance import (
    DownstreamExecutionStatus,
    EnforcementAction,
    ExperimentTrace,
    MemorySurface,
    ProvenanceEvent,
    ProvenanceRelation,
    ProvenanceStatus,
    RetrievalCandidate,
    RetrievalTrace,
    deterministic_trace_id,
)
from memlife.runner.lifecycle import LifecycleRunner, LifecycleStepObservation
from memlife.scenarios.models import LifecycleEvent, LifecycleScenario


@dataclass(frozen=True)
class TracedScenarioRun:
    """Phase 03 results plus their versioned companion trace."""

    benchmark_results: tuple[BenchmarkResult, ...]
    trace: ExperimentTrace


class ProvenanceTraceRunner:
    """Execute lifecycle observations and the pre-LLM trace hook only."""

    def __init__(
        self,
        adapter: MemoryProviderAdapter,
        *,
        candidate_filter: CandidateFilter | None = None,
        lifecycle_runner: LifecycleRunner | None = None,
        content_sanitizer: Callable[[str], str | None] | None = None,
    ) -> None:
        self.adapter = adapter
        self.candidate_filter = candidate_filter or PassThroughFilter()
        self.lifecycle_runner = lifecycle_runner or LifecycleRunner(adapter)
        # Raw provider content is omitted by default. Callers may supply a
        # sanitizer only when their experiment has an explicit logging policy.
        self.content_sanitizer = content_sanitizer
        if self.lifecycle_runner.adapter is not adapter:
            raise ValueError("lifecycle_runner must use the same adapter")

    def run_scenario(
        self,
        scenario: LifecycleScenario,
        *,
        experiment_id: str,
    ) -> TracedScenarioRun:
        """Run lifecycle + retrieval + enforcement with model/tool NOT_RUN."""

        observations = self.lifecycle_runner.run_scenario_observed(scenario)
        events: list[ProvenanceEvent] = []
        retrieval_traces: list[RetrievalTrace] = []
        alias_event_ids: dict[str, str] = {}
        alias_provider_ids: dict[str, str] = {}
        provider_event_ids: dict[str, str] = {}

        for observation in observations:
            step = observation.step
            result = observation.result
            lifecycle_event_id = deterministic_trace_id(
                "lifecycle",
                experiment_id,
                scenario.scenario_id,
                observation.step_index,
                step.event.value,
            )
            parent_event_id = (
                alias_event_ids.get(str(step.target_key))
                if step.target_key is not None
                else None
            )
            source_record_id = (
                alias_provider_ids.get(str(step.target_key))
                if step.target_key is not None
                else (str(step.memory_key) if step.memory_key is not None else None)
            )
            provider_record_id = (
                observation.records[0].memory_id
                if len(observation.records) == 1
                else None
            )
            relation, provenance_status = self._relation_for(observation)
            lifecycle_status = (
                observation.records[0].state
                if len(observation.records) == 1
                else self._missing_lifecycle_status(result.operation_status)
            )
            surface = (
                MemorySurface.RETRIEVAL
                if step.event is LifecycleEvent.QUERY
                else self.adapter.trace_source_surface
            )
            derived_record_id = (
                provider_record_id
                if step.event
                in {LifecycleEvent.WRITE, LifecycleEvent.UPDATE, LifecycleEvent.SUPERSEDE}
                else None
            )
            events.append(
                ProvenanceEvent(
                    event_id=lifecycle_event_id,
                    parent_event_id=parent_event_id,
                    event_type=step.event.value,
                    source_record_id=source_record_id,
                    derived_record_id=derived_record_id,
                    provider_record_id=provider_record_id,
                    relation=relation,
                    lifecycle_status=lifecycle_status,
                    provenance_surface=surface,
                    provenance_status=provenance_status,
                    timestamp=result.timestamp,
                )
            )

            if step.memory_key is not None and provider_record_id is not None:
                alias = str(step.memory_key)
                alias_event_ids[alias] = lifecycle_event_id
                alias_provider_ids[alias] = provider_record_id
                provider_event_ids[provider_record_id] = lifecycle_event_id
            elif (
                step.event in {LifecycleEvent.REVOKE, LifecycleEvent.DELETE}
                and provider_record_id is not None
                and result.operation_status is OperationStatus.SUCCESS
            ):
                provider_event_ids[provider_record_id] = lifecycle_event_id

            if step.event is LifecycleEvent.QUERY:
                retrieval, retrieval_events = self._retrieval_trace(
                    experiment_id=experiment_id,
                    scenario=scenario,
                    observation=observation,
                    lifecycle_event_id=lifecycle_event_id,
                    provider_event_ids=provider_event_ids,
                )
                retrieval_traces.append(retrieval)
                events.extend(retrieval_events)

        trace = ExperimentTrace(
            experiment_id=experiment_id,
            scenario_id=scenario.scenario_id,
            provider=self.adapter.provider_name,
            lifecycle_events=tuple(events),
            retrieval_traces=tuple(retrieval_traces),
            # Phase 03B records no failure claim without deterministic evidence.
            failure_attributions=(),
            created_at=observations[0].result.timestamp,
        )
        return TracedScenarioRun(
            benchmark_results=tuple(item.result for item in observations),
            trace=trace,
        )

    def _relation_for(
        self, observation: LifecycleStepObservation
    ) -> tuple[ProvenanceRelation, ProvenanceStatus]:
        status = observation.result.operation_status
        if status is OperationStatus.UNSUPPORTED:
            return ProvenanceRelation.UNSUPPORTED, ProvenanceStatus.UNSUPPORTED
        if status is OperationStatus.ERROR:
            return ProvenanceRelation.UNKNOWN, ProvenanceStatus.UNKNOWN

        event = observation.step.event
        if event in {LifecycleEvent.QUERY, LifecycleEvent.INSPECT, LifecycleEvent.RESTART}:
            return ProvenanceRelation.NOT_APPLICABLE, ProvenanceStatus.NOT_APPLICABLE
        if self.adapter.trace_provenance_status is not ProvenanceStatus.KNOWN:
            return ProvenanceRelation.UNKNOWN, ProvenanceStatus.UNKNOWN
        if event is LifecycleEvent.WRITE:
            return ProvenanceRelation.CREATED_FROM, ProvenanceStatus.KNOWN
        if event in {LifecycleEvent.UPDATE, LifecycleEvent.SUPERSEDE}:
            return ProvenanceRelation.SUPERSEDES, ProvenanceStatus.KNOWN
        if event in {LifecycleEvent.REVOKE, LifecycleEvent.DELETE}:
            return ProvenanceRelation.INVALIDATES, ProvenanceStatus.KNOWN
        return ProvenanceRelation.UNKNOWN, ProvenanceStatus.UNKNOWN

    @staticmethod
    def _missing_lifecycle_status(
        operation_status: OperationStatus,
    ) -> ProvenanceStatus:
        if operation_status is OperationStatus.UNSUPPORTED:
            return ProvenanceStatus.UNSUPPORTED
        if operation_status is OperationStatus.ERROR:
            return ProvenanceStatus.UNKNOWN
        return ProvenanceStatus.NOT_APPLICABLE

    def _retrieval_trace(
        self,
        *,
        experiment_id: str,
        scenario: LifecycleScenario,
        observation: LifecycleStepObservation,
        lifecycle_event_id: str,
        provider_event_ids: dict[str, str],
    ) -> tuple[RetrievalTrace, tuple[ProvenanceEvent, ...]]:
        retrieval_event_id = deterministic_trace_id(
            "retrieval", lifecycle_event_id
        )
        enforcement_event_id = deterministic_trace_id(
            "enforcement", retrieval_event_id
        )
        candidates = []
        retrieval_events = []
        for index, record in enumerate(observation.records):
            candidate_id = deterministic_trace_id(
                "candidate", retrieval_event_id, record.memory_id, index
            )
            direct_source_event_id = provider_event_ids.get(record.memory_id)
            exposed_source_ids = self.adapter.trace_source_provider_ids_for(record)
            exposed_source_event_ids = tuple(
                provider_event_ids[source_id]
                for source_id in exposed_source_ids
                if source_id in provider_event_ids
            )
            source_event_ids = (
                exposed_source_event_ids
                if exposed_source_ids
                else ((direct_source_event_id,) if direct_source_event_id else ())
            )
            provenance_status = self.adapter.trace_provenance_status_for(record)
            if exposed_source_ids and len(exposed_source_event_ids) != len(
                exposed_source_ids
            ):
                provenance_status = ProvenanceStatus.UNKNOWN
            provider_metadata = dict(self.adapter.trace_metadata_for(record))
            provider_metadata.update(
                {
                    "association_basis": (
                        "provider_exposed_source_ids"
                        if exposed_source_event_ids
                        else (
                            "experiment_provider_id_match"
                            if direct_source_event_id
                            else "no_observable_source_event"
                        )
                    ),
                    "provider_revision": record.revision,
                }
            )
            candidates.append(
                RetrievalCandidate(
                    candidate_id=candidate_id,
                    provider_memory_id=record.memory_id,
                    sanitized_content=(
                        self.content_sanitizer(record.content)
                        if self.content_sanitizer is not None
                        else None
                    ),
                    # The normalized provider contract does not guarantee a score.
                    score=None,
                    surface=self.adapter.trace_surface_for(record),
                    source_event_ids=source_event_ids,
                    lifecycle_status=record.state,
                    provenance_status=provenance_status,
                    metadata=provider_metadata,
                )
            )
            retrieval_events.append(
                ProvenanceEvent(
                    event_id=deterministic_trace_id(
                        "provenance", retrieval_event_id, candidate_id
                    ),
                    parent_event_id=lifecycle_event_id,
                    event_type="RETRIEVAL_CANDIDATE_OBSERVED",
                    source_record_id=record.memory_id,
                    provider_record_id=record.memory_id,
                    relation=ProvenanceRelation.RETRIEVED_AS,
                    lifecycle_status=record.state,
                    provenance_surface=MemorySurface.RETRIEVAL,
                    # Retrieval itself is directly observed even when provider-
                    # internal causal provenance remains unknown.
                    provenance_status=ProvenanceStatus.KNOWN,
                    timestamp=observation.result.timestamp,
                )
            )

        candidate_tuple = tuple(candidates)
        context = EnforcementContext(
            experiment_id=experiment_id,
            scenario_id=scenario.scenario_id,
            retrieval_event_id=retrieval_event_id,
            enforcement_event_id=enforcement_event_id,
            metadata={"provider": self.adapter.provider_name},
        )
        decisions = self.candidate_filter.inspect_candidates(candidate_tuple, context)
        delivered = tuple(
            decision.candidate_id
            for decision in decisions
            if decision.decision is not EnforcementAction.BLOCK
        )
        return (
            RetrievalTrace(
                retrieval_event_id=retrieval_event_id,
                lifecycle_event_id=lifecycle_event_id,
                enforcement_event_id=enforcement_event_id,
                candidates=candidate_tuple,
                decisions=decisions,
                delivered_candidate_ids=delivered,
                model_execution=DownstreamExecutionStatus.NOT_RUN,
                tool_execution=DownstreamExecutionStatus.NOT_RUN,
                model_decision=None,
                tool_action=None,
                timestamp=observation.result.timestamp,
            ),
            tuple(retrieval_events),
        )
