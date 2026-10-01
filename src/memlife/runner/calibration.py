"""LLM-free Phase 06A calibration for reference and local Mem0 adapters."""

from __future__ import annotations

import json
from time import perf_counter
from typing import Any, Iterable

from pydantic import Field, model_validator

from memlife.adapters.base import MemoryProviderAdapter
from memlife.models.authority import (
    AUTHORITY_SCHEMA_VERSION,
    AuthorityExposureOutcome,
    AuthorityLedger,
    AuthorityLedgerEntry,
    content_sha256,
    normalize_authority_exposure,
)
from memlife.models.benchmark import NormalizedOutcome, OperationStatus
from memlife.models.lifecycle import LifecycleState
from memlife.models.memory import NonEmptyText, QueryCommand, StrictModel
from memlife.models.memory import SupersedeCommand, WriteCommand
from memlife.models.provenance import ProvenanceStatus, RetrievalCandidate
from memlife.runner.lifecycle import normalize_query_observation
from memlife.scenarios.models import ScenarioQuery

CALIBRATION_VERSION = "1.0"
CALIBRATION_REPETITIONS = 3
CALIBRATION_SCENARIO = "calibration"
CALIBRATION_RUN_ID_TEMPLATE = "freeze-v1__calibration__{provider}__r{repetition}"
CALIBRATION_NAMESPACE_TEMPLATE = (
    "memlife-freeze-v1-calibration-{provider}-r{repetition}"
)
ALDER_V1 = "Project Alder reports may be sent to Alice."
ALDER_V2 = "Project Alder reports may be sent only to Bob."
ALDER_QUERY = "Project Alder reports"


def calibration_run_id(provider: str, repetition: int) -> str:
    return CALIBRATION_RUN_ID_TEMPLATE.format(
        provider=provider, repetition=repetition
    )


def calibration_namespace(provider: str, repetition: int) -> str:
    return CALIBRATION_NAMESPACE_TEMPLATE.format(
        provider=provider, repetition=repetition
    )


class NativeCalibrationOperation(StrictModel):
    intended_event: NonEmptyText
    native_operation: NonEmptyText
    provider_memory_id: NonEmptyText
    operation_status: OperationStatus


class CalibrationRun(StrictModel):
    calibration_version: str = CALIBRATION_VERSION
    run_id: NonEmptyText
    provider: NonEmptyText
    provider_version: NonEmptyText
    repetition: int = Field(ge=1)
    namespace: NonEmptyText
    source_event_ids: tuple[NonEmptyText, ...]
    logical_fact_ids: tuple[NonEmptyText, ...]
    authority_transitions: tuple[dict[str, Any], ...]
    authority_ledger: AuthorityLedger
    native_provider_operations: tuple[NativeCalibrationOperation, ...]
    exact_visibility_outcome: NormalizedOutcome
    authority_exposure_outcome: AuthorityExposureOutcome
    provenance_status: ProvenanceStatus
    retrieved_provider_ids: tuple[str, ...]
    retrieved_source_event_ids: tuple[str, ...]
    retrieved_content_sha256: tuple[str, ...]
    lifecycle_status: tuple[LifecycleState, ...]
    operation_status: OperationStatus
    latency_ms: float = Field(ge=0)
    error: str | None = None
    rq3_decision_calls: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def calibration_policy(self) -> "CalibrationRun":
        if self.calibration_version != CALIBRATION_VERSION:
            raise ValueError("unexpected calibration version")
        if self.rq3_decision_calls != 0:
            raise ValueError("Phase 06A calibration must not make RQ3 calls")
        return self


class CalibrationArtifact(StrictModel):
    calibration_version: str = CALIBRATION_VERSION
    authority_schema_version: str = AUTHORITY_SCHEMA_VERSION
    repo_base_commit: NonEmptyText
    repetitions_per_provider: int = CALIBRATION_REPETITIONS
    hosted_model_calls: int = Field(default=0, ge=0)
    rq3_decision_calls: int = Field(default=0, ge=0)
    runs: tuple[CalibrationRun, ...]

    @model_validator(mode="after")
    def validate_artifact(self) -> "CalibrationArtifact":
        if self.hosted_model_calls != 0 or self.rq3_decision_calls != 0:
            raise ValueError("calibration artifact must record zero model calls")
        providers: dict[str, list[CalibrationRun]] = {}
        for run in self.runs:
            providers.setdefault(run.provider, []).append(run)
        if set(providers) != {"reference", "mem0"}:
            raise ValueError("calibration requires exactly reference and mem0")
        for provider, runs in providers.items():
            if len(runs) != CALIBRATION_REPETITIONS:
                raise ValueError(f"{provider} must have exactly three repetitions")
            if {run.repetition for run in runs} != {1, 2, 3}:
                raise ValueError(f"{provider} repetition IDs must be 1, 2, 3")
            if len({run.namespace for run in runs}) != CALIBRATION_REPETITIONS:
                raise ValueError(f"{provider} namespaces must be isolated")
        return self

    def canonical_json(self) -> str:
        return json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            separators=(",", ": "),
        ) + "\n"


def _provider_label(adapter: MemoryProviderAdapter) -> str:
    return "reference" if adapter.provider_name == "reference-in-memory" else "mem0"


def _ledger(run_id: str, namespace: str) -> AuthorityLedger:
    v1_event = f"{run_id}__write-v1"
    v2_event = f"{run_id}__update-v2"
    return AuthorityLedger(
        entries=(
            AuthorityLedgerEntry(
                experiment_event_id=v1_event,
                logical_fact_id=f"{run_id}__alder-v1",
                namespace=namespace,
                sequence=1,
                lifecycle_state=LifecycleState.SUPERSEDED,
                authoritative=False,
                authority_reason="experiment authority transition replaced v1 with v2",
                superseded_by=f"{run_id}__alder-v2",
                source_content_sha256=content_sha256(ALDER_V1),
            ),
            AuthorityLedgerEntry(
                experiment_event_id=v2_event,
                logical_fact_id=f"{run_id}__alder-v2",
                namespace=namespace,
                sequence=2,
                lifecycle_state=LifecycleState.ACTIVE,
                authoritative=True,
                authority_reason="v2 is the current experiment-defined authority",
                supersedes=f"{run_id}__alder-v1",
                source_content_sha256=content_sha256(ALDER_V2),
            ),
        )
    )


def run_calibration_repetition(
    adapter: MemoryProviderAdapter,
    repetition: int,
) -> CalibrationRun:
    """Run one isolated authority transition and ordinary retrieval."""

    provider = _provider_label(adapter)
    run_id = calibration_run_id(provider, repetition)
    namespace = calibration_namespace(provider, repetition)
    ledger = _ledger(run_id, namespace)
    v1, v2 = ledger.entries
    adapter.reset_namespace(namespace)

    started = perf_counter()
    written = adapter.write(
        WriteCommand(
            namespace=namespace,
            content=ALDER_V1,
            metadata={
                "experiment_event_id": v1.experiment_event_id,
                "logical_fact_id": v1.logical_fact_id,
            },
        )
    )
    updated = adapter.update_or_supersede(
        SupersedeCommand(
            namespace=namespace,
            memory_id=written.memory_id,
            content=ALDER_V2,
            metadata={
                "experiment_event_id": v2.experiment_event_id,
                "logical_fact_id": v2.logical_fact_id,
            },
        )
    )
    records = adapter.query(
        QueryCommand(namespace=namespace, query=ALDER_QUERY, limit=10)
    )
    latency_ms = round((perf_counter() - started) * 1000, 3)

    exact_outcome, _, _, _ = normalize_query_observation(
        records,
        ScenarioQuery(
            query_id="alder-current-vs-stale",
            text=ALDER_QUERY,
            current_facts=(ALDER_V2,),
            stale_facts=(ALDER_V1,),
        ),
    )
    provider_event_ids = {
        written.memory_id: v1.experiment_event_id,
        updated.memory_id: v2.experiment_event_id,
    }
    candidates: list[RetrievalCandidate] = []
    correlated_event_ids: list[str] = []
    for index, record in enumerate(records):
        metadata_event = record.metadata.get("experiment_event_id")
        source_event_ids: tuple[str, ...]
        if isinstance(metadata_event, str) and metadata_event in ledger.by_event_id():
            source_event_ids = (metadata_event,)
        else:
            provider_sources = adapter.trace_source_provider_ids_for(record)
            mapped = tuple(
                provider_event_ids[source_id]
                for source_id in provider_sources
                if source_id in provider_event_ids
            )
            direct = provider_event_ids.get(record.memory_id)
            source_event_ids = mapped or ((direct,) if direct else ())
        correlated_event_ids.extend(source_event_ids)
        candidates.append(
            RetrievalCandidate(
                candidate_id=f"{run_id}__candidate-{index + 1}",
                provider_memory_id=record.memory_id,
                sanitized_content=None,
                score=None,
                source_event_ids=source_event_ids,
                lifecycle_status=record.state,
                provenance_status=(
                    ProvenanceStatus.KNOWN
                    if source_event_ids
                    else ProvenanceStatus.UNKNOWN
                ),
                metadata={"association_basis": "adapter-observed write correlation"},
            )
        )

    authority_outcome = normalize_authority_exposure(candidates, ledger)
    provenance = (
        ProvenanceStatus.KNOWN
        if all(candidate.source_event_ids for candidate in candidates)
        else ProvenanceStatus.UNKNOWN
    )
    run = CalibrationRun(
        run_id=run_id,
        provider=provider,
        provider_version=str(adapter.provider_version or "unknown"),
        repetition=repetition,
        namespace=namespace,
        source_event_ids=(v1.experiment_event_id, v2.experiment_event_id),
        logical_fact_ids=(v1.logical_fact_id, v2.logical_fact_id),
        authority_transitions=(
            {
                "logical_fact_id": v1.logical_fact_id,
                "from_authoritative": True,
                "to_authoritative": False,
                "reason": "superseded by v2",
            },
            {
                "logical_fact_id": v2.logical_fact_id,
                "from_authoritative": False,
                "to_authoritative": True,
                "reason": "current replacement",
            },
        ),
        authority_ledger=ledger,
        native_provider_operations=(
            NativeCalibrationOperation(
                intended_event="WRITE",
                native_operation=adapter.native_operation_for("WRITE"),
                provider_memory_id=written.memory_id,
                operation_status=OperationStatus.SUCCESS,
            ),
            NativeCalibrationOperation(
                intended_event="UPDATE",
                native_operation=adapter.native_operation_for("UPDATE"),
                provider_memory_id=updated.memory_id,
                operation_status=OperationStatus.SUCCESS,
            ),
        ),
        exact_visibility_outcome=exact_outcome,
        authority_exposure_outcome=authority_outcome,
        provenance_status=provenance,
        retrieved_provider_ids=tuple(record.memory_id for record in records),
        retrieved_source_event_ids=tuple(dict.fromkeys(correlated_event_ids)),
        retrieved_content_sha256=tuple(content_sha256(record.content) for record in records),
        lifecycle_status=tuple(record.state for record in records),
        operation_status=OperationStatus.SUCCESS,
        latency_ms=latency_ms,
        error=None,
        rq3_decision_calls=0,
    )
    if provider == "reference" and (
        run.exact_visibility_outcome is not NormalizedOutcome.CURRENT_ONLY
        or run.authority_exposure_outcome
        is not AuthorityExposureOutcome.AUTHORITATIVE_ONLY
    ):
        raise RuntimeError("reference calibration failed measurement-oracle assertions")
    return run


def calibration_artifact(
    *, repo_base_commit: str, runs: Iterable[CalibrationRun]
) -> CalibrationArtifact:
    return CalibrationArtifact(repo_base_commit=repo_base_commit, runs=tuple(runs))

