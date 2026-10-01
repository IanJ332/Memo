"""Frozen Phase 06B three-provider storage/lifecycle batch.

The module deliberately owns experiment planning, per-repetition recording,
aggregation, and residual selection. Provider lifecycle behavior remains in the
existing adapters; no provider capability is emulated here.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Any, Callable, Iterable, Mapping

from memlife.adapters.base import MemoryProviderAdapter
from memlife.models.authority import (
    AuthorityExposureOutcome,
    AuthorityLedger,
    AuthorityLedgerEntry,
    content_sha256,
    normalize_authority_exposure,
)
from memlife.models.benchmark import NormalizedOutcome, OperationStatus
from memlife.models.lifecycle import LifecycleState
from memlife.models.memory import DeleteCommand, MemoryRecord, QueryCommand
from memlife.models.memory import SupersedeCommand, WriteCommand
from memlife.models.provenance import MemorySurface, ProvenanceStatus, RetrievalCandidate
from memlife.runner.freeze import FREEZE_SHA256, load_freeze_from_git
from memlife.runner.lifecycle import normalize_query_observation
from memlife.scenarios.models import ScenarioQuery

EXPECTED_PROVIDER_VERSIONS = {
    "mem0": "2.2.1",
    "hindsight": "0.10.1",
    "openviking": "0.4.22",
}
EXPECTED_CONFIGURATION_HASHES = {
    "mem0": "23c068e16db7d4bb90aad7755b997d5a4104c433a4a0083ef43b3506680ff2e8",
    "hindsight": "baca300bdce174d8cb2d00fa576df73d0cf5c4f9230aed370d2767bd35f4d73d",
    "openviking": "ad1216520de78aa6dd6fe0c34393e3830b05b035aa7dda367d92725dafe53258",
}
PROVIDER_INTERNAL_MODELS = {
    "mem0": None,
    "hindsight": "gpt-oss-120b",
    "openviking": "gpt-oss-120b",
}
_SENSITIVE_KEY = re.compile(
    r"(?i)(api.?key|authorization|password|private.?key|access.?token|refresh.?token|credential|secret)"
)
_IP_ADDRESS = re.compile(r"\b(?!127\.0\.0\.1\b)(?:\d{1,3}\.){3}\d{1,3}\b")


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        separators=(",", ": "),
    ) + "\n"


def load_frozen_protocol(path: Path) -> dict[str, Any]:
    """Load Freeze v1 from Git and reject any byte or closed-set mismatch."""

    materialization = load_freeze_from_git(path)
    if materialization.sha256 != FREEZE_SHA256:
        raise ValueError(f"freeze SHA-256 mismatch: {materialization.sha256}")
    payload = materialization.payload
    providers = {item["id"]: item["version"] for item in payload["providers"]}
    if providers != EXPECTED_PROVIDER_VERSIONS:
        raise ValueError("frozen provider/version set mismatch")
    if payload.get("repetitions_per_supported_provider_scenario") != 3:
        raise ValueError("frozen repetition count mismatch")
    if payload.get("storage_batch_downstream_decision_calls") != 0:
        raise ValueError("frozen downstream-call policy mismatch")
    return payload


def generate_run_plan(freeze_path: Path) -> dict[str, Any]:
    """Generate the only Phase 06B plan directly from Freeze v1."""

    freeze = load_frozen_protocol(freeze_path)
    repetitions = int(freeze["repetitions_per_supported_provider_scenario"])
    provider_order = list(freeze["run_order"]["providers"])
    scenario_order = list(freeze["run_order"]["scenarios"])
    matrix = freeze["capability_matrix"]
    run_template = str(freeze["run_id_template"])
    namespace_template = str(freeze["namespace_template"])
    runs: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []
    for provider in provider_order:
        for scenario in scenario_order:
            capability = str(matrix[provider][scenario])
            if capability == "UNSUPPORTED":
                unsupported.append(
                    {
                        "provider": provider,
                        "scenario": scenario,
                        "capability": capability,
                        "executed_repetitions": 0,
                    }
                )
                continue
            if capability != "SUPPORTED":
                raise ValueError(f"unresolved capability: {provider}/{scenario}")
            for repetition in range(1, repetitions + 1):
                runs.append(
                    {
                        "provider": provider,
                        "provider_version": EXPECTED_PROVIDER_VERSIONS[provider],
                        "scenario": scenario,
                        "repetition": repetition,
                        "run_id": run_template.format(
                            provider=provider,
                            scenario=scenario,
                            repetition=repetition,
                        ),
                        "namespace": namespace_template.format(
                            provider=provider,
                            scenario=scenario,
                            repetition=repetition,
                        ),
                        "capability": capability,
                    }
                )
    if len(runs) != 42 or len(unsupported) != 4:
        raise ValueError(
            f"frozen plan cardinality mismatch: runs={len(runs)} unsupported={len(unsupported)}"
        )
    return {
        "freeze_id": freeze["freeze_id"],
        "freeze_sha256": FREEZE_SHA256,
        "ordering": freeze["run_order"]["ordering"],
        "provider_order": provider_order,
        "scenario_order": scenario_order,
        "repetitions_per_supported_cell": repetitions,
        "expected_executable_count": len(runs),
        "unsupported_cell_count": len(unsupported),
        "runs": runs,
        "unsupported_cells": unsupported,
        "downstream_decision_model_calls": 0,
    }


def write_run_plan(freeze_path: Path, output: Path) -> dict[str, Any]:
    plan = generate_run_plan(freeze_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(canonical_json(plan), encoding="utf-8")
    return plan


def _sanitize_text(value: object) -> str:
    text = _IP_ADDRESS.sub("[REDACTED_IP]", str(value or ""))
    text = re.sub(
        r'''(?i)((?:api[_-]?key|authorization|password|token|secret|credential)\s*[:=]\s*)[^\s,}\]]+''',
        r"\1[REDACTED]",
        text,
    )
    return text[-4000:]


def sanitize_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            str(key): sanitize_value(child)
            for key, child in value.items()
            if not _SENSITIVE_KEY.search(str(key))
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_value(item) for item in value]
    if isinstance(value, str):
        return _sanitize_text(value)
    return value


def contains_sensitive_key(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(
            _SENSITIVE_KEY.search(str(key)) or contains_sensitive_key(child)
            for key, child in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(contains_sensitive_key(item) for item in value)
    return False


def _scenario_content(run_id: str, scenario: str) -> dict[str, str]:
    if scenario == "S1":
        v1 = f"{run_id}: Project Alder reports may be sent to Alice."
        v2 = f"{run_id}: Project Alder reports may be sent only to Bob."
        return {
            "v1": v1,
            "v2": v2,
            "query": v1,
        }
    if scenario == "S4":
        v1 = f"{run_id}: Project Larch reports may be shared with Analyst-7."
        return {
            "v1": v1,
            "support": f"{run_id}: Analyst-7 reviews Project Larch reports every Friday.",
            "query": v1,
        }
    v1 = f"{run_id}: Project Birch restart canary is active."
    return {
        "v1": v1,
        "query": v1,
    }


def _ledger(
    run: Mapping[str, Any], content: Mapping[str, str]
) -> tuple[AuthorityLedger, list[dict[str, Any]]]:
    run_id = str(run["run_id"])
    namespace = str(run["namespace"])
    scenario = str(run["scenario"])
    v1_state = LifecycleState.ACTIVE
    v1_authoritative = True
    v1_reason = "current experiment-defined authority"
    if scenario == "S1":
        v1_state = LifecycleState.SUPERSEDED
        v1_authoritative = False
        v1_reason = "experiment authority transition replaced v1 with v2"
    elif scenario in {"S2", "S3", "S4"}:
        v1_state = LifecycleState.DELETED
        v1_authoritative = False
        v1_reason = "experiment lifecycle intent hard-deleted this source"
    elif scenario == "S5":
        v1_state = LifecycleState.REVOKED
        v1_authoritative = False
        v1_reason = "experiment lifecycle intent revoked this source"

    entries = [
        AuthorityLedgerEntry(
            experiment_event_id=f"{run_id}__write-v1",
            logical_fact_id=f"{run_id}__fact-v1",
            namespace=namespace,
            sequence=1,
            lifecycle_state=v1_state,
            authoritative=v1_authoritative,
            authority_reason=v1_reason,
            superseded_by=(f"{run_id}__fact-v2" if scenario == "S1" else None),
            source_content_sha256=content_sha256(content["v1"]),
        )
    ]
    transitions: list[dict[str, Any]] = []
    if scenario == "S1":
        entries.append(
            AuthorityLedgerEntry(
                experiment_event_id=f"{run_id}__update-v2",
                logical_fact_id=f"{run_id}__fact-v2",
                namespace=namespace,
                sequence=2,
                lifecycle_state=LifecycleState.ACTIVE,
                authoritative=True,
                authority_reason="v2 is the current experiment-defined authority",
                supersedes=f"{run_id}__fact-v1",
                source_content_sha256=content_sha256(content["v2"]),
            )
        )
        transitions.extend(
            (
                {
                    "logical_fact_id": f"{run_id}__fact-v1",
                    "from_authoritative": True,
                    "to_authoritative": False,
                    "reason": "superseded by v2",
                },
                {
                    "logical_fact_id": f"{run_id}__fact-v2",
                    "from_authoritative": False,
                    "to_authoritative": True,
                    "reason": "current replacement",
                },
            )
        )
    elif scenario == "S4":
        entries.append(
            AuthorityLedgerEntry(
                experiment_event_id=f"{run_id}__write-support",
                logical_fact_id=f"{run_id}__fact-support",
                namespace=namespace,
                sequence=2,
                lifecycle_state=LifecycleState.ACTIVE,
                authoritative=True,
                authority_reason="supporting source remains current experiment authority",
                source_content_sha256=content_sha256(content["support"]),
            )
        )
        transitions.append(
            {
                "logical_fact_id": f"{run_id}__fact-v1",
                "from_authoritative": True,
                "to_authoritative": False,
                "reason": "hard-deleted before frozen re-derivation",
            }
        )
    elif scenario in {"S2", "S3", "S5"}:
        transitions.append(
            {
                "logical_fact_id": f"{run_id}__fact-v1",
                "from_authoritative": True,
                "to_authoritative": False,
                "reason": "revoked" if scenario == "S5" else "hard-deleted",
            }
        )
    return AuthorityLedger(entries=tuple(entries)), transitions


def _record_surface(adapter: MemoryProviderAdapter, record: MemoryRecord) -> MemorySurface:
    return adapter.trace_surface_for(record)


def _provider_score(record: MemoryRecord) -> float | None:
    for key in ("openviking_score", "score", "relevance_score"):
        value = record.metadata.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    return None


def _correlated_event_ids(
    adapter: MemoryProviderAdapter,
    record: MemoryRecord,
    provider_events: Mapping[str, set[str]],
    ledger: AuthorityLedger,
) -> tuple[str, ...]:
    known = ledger.by_event_id()
    direct_metadata = tuple(
        str(record.metadata[key])
        for key in ("experiment_event_id", "source_event_id", "openviking_source_event_id")
        if isinstance(record.metadata.get(key), str)
        and str(record.metadata[key]) in known
    )
    linked: list[str] = list(direct_metadata)
    for provider_id in adapter.trace_source_provider_ids_for(record):
        linked.extend(sorted(provider_events.get(provider_id, set())))
    linked.extend(sorted(provider_events.get(record.memory_id, set())))
    return tuple(dict.fromkeys(linked))


def _retrieval_payload(
    *,
    adapter: MemoryProviderAdapter,
    records: Iterable[MemoryRecord],
    phase: str,
    run_id: str,
    provider_events: Mapping[str, set[str]],
    ledger: AuthorityLedger,
) -> tuple[list[dict[str, Any]], list[RetrievalCandidate]]:
    payload: list[dict[str, Any]] = []
    candidates: list[RetrievalCandidate] = []
    for rank, record in enumerate(records, start=1):
        source_events = _correlated_event_ids(adapter, record, provider_events, ledger)
        provenance = ProvenanceStatus.KNOWN if source_events else ProvenanceStatus.UNKNOWN
        candidate_id = f"{run_id}__{phase}__candidate-{rank}"
        surface = _record_surface(adapter, record)
        score = _provider_score(record)
        candidates.append(
            RetrievalCandidate(
                candidate_id=candidate_id,
                provider_memory_id=record.memory_id,
                score=score,
                surface=surface,
                source_event_ids=source_events,
                lifecycle_status=record.state,
                provenance_status=provenance,
                metadata={"association_basis": "direct provider/adapter identity only"},
            )
        )
        payload.append(
            {
                "retrieval_id": candidate_id,
                "phase": phase,
                "provider_memory_id": record.memory_id,
                "rank": rank,
                "score": score,
                "memory_surface": surface.value,
                "source_event_ids": list(source_events),
                "provider_parent_source_ids": list(
                    adapter.trace_source_provider_ids_for(record)
                ),
                "exact_content_sha256": content_sha256(record.content),
                "lifecycle_state": record.state.value,
                "provenance_status": provenance.value,
            }
        )
    return payload, candidates


def _safe_inspect(adapter: MemoryProviderAdapter, namespace: str) -> tuple[MemoryRecord, ...]:
    try:
        return adapter.list_or_inspect(namespace)
    except Exception:
        return ()


def run_repetition(
    *,
    adapter: MemoryProviderAdapter,
    run: Mapping[str, Any],
    tested_git_commit: str,
    attempt_id: str,
    execution_origin: str | None = None,
) -> dict[str, Any]:
    """Execute one already-supported frozen repetition and preserve all evidence."""

    provider = str(run["provider"])
    scenario = str(run["scenario"])
    run_id = str(run["run_id"])
    namespace = str(run["namespace"])
    if provider not in EXPECTED_PROVIDER_VERSIONS:
        raise ValueError(f"unknown frozen provider: {provider}")
    if str(adapter.provider_version) != EXPECTED_PROVIDER_VERSIONS[provider]:
        raise ValueError(f"{provider} adapter version mismatch")
    content = _scenario_content(run_id, scenario)
    ledger, transitions = _ledger(run, content)
    provider_events: dict[str, set[str]] = {}
    operations: list[dict[str, Any]] = []
    lifecycle_events: list[dict[str, Any]] = []
    final_records: list[MemoryRecord] = []
    after_transition_records: tuple[MemoryRecord, ...] = ()
    all_retrievals: list[dict[str, Any]] = []
    final_candidates: list[RetrievalCandidate] = []
    error: str | None = None
    started = perf_counter()

    def operation(
        intended: str,
        native: str,
        action: Callable[[], Any],
    ) -> Any:
        op_started = perf_counter()
        event_id = f"{run_id}__event-{len(lifecycle_events) + 1:02d}"
        try:
            value = action()
        except Exception as exc:
            elapsed = round((perf_counter() - op_started) * 1000, 3)
            message = _sanitize_text(f"{type(exc).__name__}: {exc}")
            operations.append(
                {
                    "intended_event": intended,
                    "native_operation": native,
                    "operation_status": OperationStatus.ERROR.value,
                    "latency_ms": elapsed,
                    "error": message,
                }
            )
            lifecycle_events.append(
                {
                    "lifecycle_event_id": event_id,
                    "intended_event": intended,
                    "operation_status": OperationStatus.ERROR.value,
                }
            )
            raise
        elapsed = round((perf_counter() - op_started) * 1000, 3)
        metadata = sanitize_value(dict(adapter.benchmark_metadata()))
        operations.append(
            {
                "intended_event": intended,
                "native_operation": native,
                "operation_status": OperationStatus.SUCCESS.value,
                "latency_ms": elapsed,
                "quiescence_evidence": metadata,
            }
        )
        lifecycle_events.append(
            {
                "lifecycle_event_id": event_id,
                "intended_event": intended,
                "operation_status": OperationStatus.SUCCESS.value,
            }
        )
        return value

    def write(label: str, text: str, event_id: str) -> MemoryRecord:
        record = operation(
            "WRITE",
            adapter.native_operation_for("WRITE"),
            lambda: adapter.write(
                WriteCommand(
                    namespace=namespace,
                    content=text,
                    metadata={
                        "experiment_event_id": event_id,
                        "logical_fact_id": event_id.replace("write", "fact"),
                        "source_event_id": event_id,
                    },
                )
            ),
        )
        provider_events.setdefault(record.memory_id, set()).add(event_id)
        return record

    def query(phase: str, query_text: str) -> tuple[MemoryRecord, ...]:
        records = operation(
            "QUERY",
            adapter.native_operation_for("QUERY"),
            lambda: adapter.query(
                QueryCommand(namespace=namespace, query=query_text, limit=10)
            ),
        )
        retrievals, candidates = _retrieval_payload(
            adapter=adapter,
            records=records,
            phase=phase,
            run_id=run_id,
            provider_events=provider_events,
            ledger=ledger,
        )
        all_retrievals.extend(retrievals)
        if phase.startswith("final"):
            final_candidates.extend(candidates)
            final_records.extend(records)
        return records

    try:
        operation(
            "RESET_NAMESPACE",
            adapter.native_operation_for("RESET_NAMESPACE"),
            lambda: adapter.reset_namespace(namespace),
        )
        v1_event = f"{run_id}__write-v1"
        written = write("v1", content["v1"], v1_event)

        if scenario == "S0":
            query("final", content["query"])
        elif scenario == "S1":
            v2_event = f"{run_id}__update-v2"
            updated = operation(
                "UPDATE",
                adapter.native_operation_for("UPDATE"),
                lambda: adapter.update_or_supersede(
                    SupersedeCommand(
                        namespace=namespace,
                        memory_id=written.memory_id,
                        content=content["v2"],
                        metadata={
                            "experiment_event_id": v2_event,
                            "logical_fact_id": f"{run_id}__fact-v2",
                        },
                    )
                ),
            )
            provider_events.setdefault(updated.memory_id, set()).add(v2_event)
            query("final-old", content["v1"])
            query("final-new", content["v2"])
        elif scenario in {"S2", "S3", "S4", "S5"}:
            query("observe-before-transition", content["query"])
            if scenario == "S4":
                support_event = f"{run_id}__write-support"
                write("support", content["support"], support_event)
                if provider == "hindsight":
                    operation(
                        "CREATE_DERIVED_STATE",
                        "POST /consolidate; poll operation status=completed",
                        lambda: getattr(adapter, "trigger_derivation")(namespace),
                    )
                elif provider == "openviking":
                    session_id = str(
                        getattr(adapter, "completed_write_metadata")(written.memory_id)[
                            "session_id"
                        ]
                    )
                    operation(
                        "CREATE_DERIVED_STATE",
                        "POST /sessions/{id}/extract",
                        lambda: getattr(adapter, "trigger_derivation")(session_id),
                    )
            disposition = (
                LifecycleState.REVOKED if scenario == "S5" else LifecycleState.DELETED
            )
            operation(
                "REVOKE" if scenario == "S5" else "DELETE",
                adapter.native_operation_for(
                    "REVOKE" if scenario == "S5" else "DELETE"
                ),
                lambda: adapter.delete_or_invalidate(
                    DeleteCommand(
                        namespace=namespace,
                        memory_id=written.memory_id,
                        disposition=disposition,
                    )
                ),
            )
            after_transition_records = _safe_inspect(adapter, namespace)
            if scenario == "S3":
                operation(
                    "RESTART",
                    adapter.native_operation_for("RESTART"),
                    adapter.restart,
                )
            elif scenario == "S4":
                if provider == "hindsight":
                    operation(
                        "REDERIVE",
                        "POST /consolidate; poll operation status=completed",
                        lambda: getattr(adapter, "trigger_derivation")(namespace),
                    )
                else:
                    session_id = str(
                        getattr(adapter, "completed_write_metadata")(written.memory_id)[
                            "session_id"
                        ]
                    )
                    operation(
                        "REDERIVE",
                        "POST /sessions/{id}/extract",
                        lambda: getattr(adapter, "trigger_derivation")(session_id),
                    )
            query("final", content["query"])
        else:
            raise ValueError(f"unknown frozen scenario: {scenario}")

        operation(
            "INSPECT",
            adapter.native_operation_for("INSPECT"),
            lambda: adapter.list_or_inspect(namespace),
        )
    except Exception as exc:
        error = _sanitize_text(f"{type(exc).__name__}: {exc}")

    elapsed_total = round((perf_counter() - started) * 1000, 3)
    if error is not None:
        exact = NormalizedOutcome.ERROR
        authority = (
            normalize_authority_exposure(final_candidates, ledger)
            if final_candidates
            else AuthorityExposureOutcome.NONE
        )
        overall_status = OperationStatus.ERROR
    else:
        query_spec = ScenarioQuery(
            query_id="final",
            text=content["query"],
            current_facts=((content["v2"],) if scenario == "S1" else ((content["v1"],) if scenario == "S0" else ())),
            stale_facts=((content["v1"],) if scenario != "S0" else ()),
        )
        exact = normalize_query_observation(final_records, query_spec)[0]
        authority = normalize_authority_exposure(final_candidates, ledger)
        overall_status = OperationStatus.SUCCESS

    ledger_by_event = ledger.by_event_id()
    nonauthoritative_candidates = [
        candidate
        for candidate in final_candidates
        if candidate.source_event_ids
        and any(
            event_id in ledger_by_event and not ledger_by_event[event_id].authoritative
            for event_id in candidate.source_event_ids
        )
    ]
    derived_nonauthoritative = [
        candidate
        for candidate in nonauthoritative_candidates
        if candidate.surface is not MemorySurface.SOURCE
    ]
    transition_hash = content_sha256(content["v1"])
    absent_after_transition = not any(
        content_sha256(record.content) == transition_hash
        for record in after_transition_records
    )
    final_exact_visible = any(
        content_sha256(record.content) == transition_hash for record in final_records
    )
    source_classes: set[bool] = set()
    derived_classes: set[bool] = set()
    for candidate in final_candidates:
        classes = {
            ledger_by_event[event_id].authoritative
            for event_id in candidate.source_event_ids
            if event_id in ledger_by_event
        }
        if candidate.surface is MemorySurface.SOURCE:
            source_classes.update(classes)
        else:
            derived_classes.update(classes)
    residual_signals = {
        "nonauthoritative_exact_visible": bool(
            final_exact_visible and scenario != "S0"
        ),
        "nonauthoritative_correlated_derived_visible": bool(derived_nonauthoritative),
        "deleted_or_revoked_descendant_visible": bool(derived_nonauthoritative),
        "reappeared_after_restart": bool(
            scenario == "S3" and absent_after_transition and final_exact_visible
        ),
        "reappeared_after_rederivation": bool(
            scenario == "S4" and absent_after_transition and bool(final_candidates)
        ),
        "source_derived_authority_disagreement": bool(
            source_classes and derived_classes and source_classes != derived_classes
        ),
        "repetition_authority_disagreement": False,
    }
    provenance_values = [candidate.provenance_status for candidate in final_candidates]
    provenance_known = bool(provenance_values) and all(
        value is ProvenanceStatus.KNOWN for value in provenance_values
    )
    derived_ids = [
        item["provider_memory_id"]
        for item in all_retrievals
        if item["memory_surface"] != MemorySurface.SOURCE.value
    ]
    source_ids = [
        item["provider_memory_id"]
        for item in all_retrievals
        if item["source_event_ids"]
        and item["memory_surface"]
        not in {
            MemorySurface.DERIVED.value,
            MemorySurface.SUMMARY.value,
            MemorySurface.PROFILE.value,
            MemorySurface.GRAPH.value,
        }
    ]
    quiescence = [
        operation_item.get("quiescence_evidence", {})
        for operation_item in operations
        if operation_item.get("quiescence_evidence")
    ]
    if execution_origin not in {None, "SUPPLEMENT"}:
        raise ValueError("execution_origin must be SUPPLEMENT when provided")
    result = {
        "attempt_id": attempt_id,
        "freeze_id": "experiment-freeze-v1",
        "freeze_sha256": FREEZE_SHA256,
        "tested_git_commit": tested_git_commit,
        "run_id": run_id,
        "provider": provider,
        "provider_version": EXPECTED_PROVIDER_VERSIONS[provider],
        "provider_configuration_hash": EXPECTED_CONFIGURATION_HASHES[provider],
        "scenario": scenario,
        "repetition": int(run["repetition"]),
        "namespace": namespace,
        "lifecycle_events": lifecycle_events,
        "authority_ledger": ledger.model_dump(mode="json"),
        "authority_ledger_transitions": transitions,
        "provider_native_operations": operations,
        "operation_statuses": [item["operation_status"] for item in operations],
        "operation_status": overall_status.value,
        "exact_visibility_outcome": exact.value,
        "authority_exposure_outcome": authority.value,
        "source_provider_ids": list(dict.fromkeys(source_ids)),
        "provider_derived_ids": list(dict.fromkeys(derived_ids)),
        "provider_parent_source_ids": list(
            dict.fromkeys(
                parent
                for item in all_retrievals
                for parent in item["provider_parent_source_ids"]
            )
        ),
        "memory_surfaces": list(
            dict.fromkeys(item["memory_surface"] for item in all_retrievals)
        ),
        "retrievals": all_retrievals,
        "provenance_status": (
            ProvenanceStatus.KNOWN.value
            if provenance_known
            else (
                ProvenanceStatus.UNKNOWN.value
                if final_candidates
                else ProvenanceStatus.NOT_APPLICABLE.value
            )
        ),
        "provenance_known": provenance_known,
        "quiescence_evidence": quiescence,
        "latencies_ms": {
            "total": elapsed_total,
            "operations": [item["latency_ms"] for item in operations],
        },
        "error": error,
        "provider_internal_model": PROVIDER_INTERNAL_MODELS[provider],
        "provider_internal_model_role": (
            "provider_internal" if PROVIDER_INTERNAL_MODELS[provider] else None
        ),
        "downstream_decision_model_calls": 0,
        "rq3_calls": 0,
        "filter_decision": None,
        "filter_reason": None,
        "delivered_context_sha256": None,
        "downstream_model": None,
        "model_decision": None,
        "tool_action": None,
        "residual_signals": residual_signals,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if execution_origin is not None:
        result["execution_origin"] = execution_origin
    sanitized = sanitize_value(result)
    if contains_sensitive_key(sanitized):
        raise RuntimeError("sanitized result retained a sensitive key")
    if sanitized["downstream_decision_model_calls"] != 0 or sanitized["rq3_calls"] != 0:
        raise RuntimeError("Phase 06B downstream-call invariant violated")
    return dict(sanitized)


def blocked_run_records(
    runs: Iterable[Mapping[str, Any]], *, provider: str, reason: str
) -> list[dict[str, Any]]:
    return [
        {
            "run_id": str(run["run_id"]),
            "provider": provider,
            "scenario": str(run["scenario"]),
            "repetition": int(run["repetition"]),
            "namespace": str(run["namespace"]),
            "status": "BLOCKED_NOT_EXECUTED",
            "reason": _sanitize_text(reason),
        }
        for run in runs
        if run["provider"] == provider
    ]


def aggregate_runs(plan: Mapping[str, Any], raw_runs: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = tuple(raw_runs)
    by_cell: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for row in rows:
        by_cell.setdefault((str(row["provider"]), str(row["scenario"])), []).append(row)
    unsupported = {
        (str(cell["provider"]), str(cell["scenario"]))
        for cell in plan["unsupported_cells"]
    }
    cells: list[dict[str, Any]] = []
    for provider in plan["provider_order"]:
        for scenario in plan["scenario_order"]:
            key = (str(provider), str(scenario))
            if key in unsupported:
                cells.append(
                    {
                        "provider": provider,
                        "scenario": scenario,
                        "capability": "UNSUPPORTED",
                        "supported_repetitions": 0,
                        "executed_repetitions": 0,
                        "exact_outcome_counts": {},
                        "authority_exposure_outcome_counts": {},
                        "residual": False,
                        "inconsistent": False,
                        "operation_error_count": 0,
                        "median_latency_ms": None,
                        "provenance_known_fraction": None,
                    }
                )
                continue
            observations = by_cell.get(key, [])
            exact = Counter(str(item["exact_visibility_outcome"]) for item in observations)
            authority = Counter(
                str(item["authority_exposure_outcome"]) for item in observations
            )
            inconsistent = (
                len(observations) == int(plan["repetitions_per_supported_cell"])
                and (len(exact) > 1 or len(authority) > 1)
            )
            residual = any(
                any(bool(value) for value in item["residual_signals"].values())
                for item in observations
            ) or inconsistent
            cells.append(
                {
                    "provider": provider,
                    "scenario": scenario,
                    "capability": "SUPPORTED",
                    "supported_repetitions": int(
                        plan["repetitions_per_supported_cell"]
                    ),
                    "executed_repetitions": len(observations),
                    "exact_outcome_counts": dict(sorted(exact.items())),
                    "authority_exposure_outcome_counts": dict(sorted(authority.items())),
                    "residual": residual,
                    "inconsistent": inconsistent,
                    "operation_error_count": sum(
                        item["operation_status"] == OperationStatus.ERROR.value
                        for item in observations
                    ),
                    "median_latency_ms": (
                        median(float(item["latencies_ms"]["total"]) for item in observations)
                        if observations
                        else None
                    ),
                    "provenance_known_fraction": (
                        sum(bool(item["provenance_known"]) for item in observations)
                        / len(observations)
                        if observations
                        else None
                    ),
                }
            )
    return {
        "freeze_id": plan["freeze_id"],
        "freeze_sha256": plan["freeze_sha256"],
        "aggregation_unit": "provider x scenario",
        "provider_scenario_cell_count": len(cells),
        "cells": cells,
        "downstream_decision_model_calls": 0,
    }


def residual_index(
    plan: Mapping[str, Any],
    raw_runs: Iterable[Mapping[str, Any]],
    aggregate: Mapping[str, Any],
) -> dict[str, Any]:
    rows = tuple(raw_runs)
    inconsistent_cells = {
        (str(cell["provider"]), str(cell["scenario"]))
        for cell in aggregate["cells"]
        if cell["inconsistent"]
    }
    candidates: list[dict[str, Any]] = []
    reason_names = {
        "nonauthoritative_exact_visible": "non-authoritative exact content remains visible",
        "nonauthoritative_correlated_derived_visible": "provider-correlated non-authoritative derived state remains retrievable",
        "deleted_or_revoked_descendant_visible": "descendants of deleted or revoked state remain visible",
        "reappeared_after_restart": "state disappears and then reappears after restart",
        "reappeared_after_rederivation": "state disappears and then reappears after re-derivation",
        "source_derived_authority_disagreement": "source and derived surfaces disagree about current authority",
        "repetition_authority_disagreement": "the three frozen repetitions disagree about normalized authority exposure",
    }
    for row in rows:
        signals = dict(row["residual_signals"])
        if (str(row["provider"]), str(row["scenario"])) in inconsistent_cells:
            signals["repetition_authority_disagreement"] = True
        reasons = [reason_names[key] for key, value in signals.items() if value]
        if reasons:
            candidates.append(
                {
                    "run_id": row["run_id"],
                    "provider": row["provider"],
                    "scenario": row["scenario"],
                    "repetition": row["repetition"],
                    "advancement_reasons": reasons,
                }
            )
    cells = sorted({(item["provider"], item["scenario"]) for item in candidates})
    return {
        "freeze_id": plan["freeze_id"],
        "freeze_sha256": plan["freeze_sha256"],
        "scope": "queue for residual-only root-cause phase; no probes executed",
        "residual_run_count": len(candidates),
        "residual_cell_count": len(cells),
        "candidate_cells": [
            {"provider": provider, "scenario": scenario}
            for provider, scenario in cells
        ],
        "candidates": candidates,
        "downstream_decision_model_calls": 0,
    }


def write_jsonl(rows: Iterable[Mapping[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    )
    output.write_text(text, encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def validate_artifacts(
    *,
    plan: Mapping[str, Any],
    raw_runs: Iterable[Mapping[str, Any]],
    aggregate: Mapping[str, Any],
    residual: Mapping[str, Any],
    require_complete: bool,
    expected_attempt_id: str | None = None,
    expected_tested_commit: str | None = None,
) -> list[str]:
    errors: list[str] = []
    rows = tuple(raw_runs)
    run_ids = [str(item["run_id"]) for item in rows]
    namespaces = [str(item["namespace"]) for item in rows]
    if len(run_ids) != len(set(run_ids)):
        errors.append("duplicate raw run IDs")
    if len(namespaces) != len(set(namespaces)):
        errors.append("duplicate raw namespaces")
    planned = {str(item["run_id"]) for item in plan["runs"]}
    planned_by_run_id = {str(item["run_id"]): item for item in plan["runs"]}
    if not set(run_ids).issubset(planned):
        errors.append("raw results contain unplanned run IDs")
    if require_complete and set(run_ids) != planned:
        errors.append("complete artifact set does not cover all 42 planned run IDs")
    for item in rows:
        planned_item = planned_by_run_id.get(str(item["run_id"]))
        if planned_item is None:
            continue
        for field in ("provider", "scenario", "repetition", "namespace"):
            if item.get(field) != planned_item.get(field):
                errors.append(f"raw result {field} does not match frozen plan")
                break
    if rows:
        attempt_ids = {item.get("attempt_id") for item in rows}
        if None in attempt_ids or "" in attempt_ids:
            errors.append("raw result attempt ID missing")
        if len(attempt_ids) != 1:
            errors.append("raw result attempt ID inconsistency")
        if expected_attempt_id is not None and attempt_ids != {expected_attempt_id}:
            errors.append("raw result attempt ID does not match controller attempt ID")
        tested_commits = {item.get("tested_git_commit") for item in rows}
        if None in tested_commits or "" in tested_commits:
            errors.append("raw result tested commit missing")
        if len(tested_commits) != 1:
            errors.append("raw result tested commit inconsistency")
        if (
            expected_tested_commit is not None
            and tested_commits != {expected_tested_commit}
        ):
            errors.append("raw result tested commit does not match expected commit")
        if any(item.get("freeze_id") != plan.get("freeze_id") for item in rows):
            errors.append("raw result freeze ID mismatch")
    if any(item.get("freeze_sha256") != FREEZE_SHA256 for item in rows):
        errors.append("raw result freeze hash mismatch")
    if any(item.get("downstream_decision_model_calls") != 0 for item in rows):
        errors.append("raw result downstream-call invariant mismatch")
    if aggregate.get("freeze_sha256") != FREEZE_SHA256:
        errors.append("aggregate freeze hash mismatch")
    if residual.get("freeze_sha256") != FREEZE_SHA256:
        errors.append("residual index freeze hash mismatch")
    recomputed_aggregate = aggregate_runs(plan, rows)
    if recomputed_aggregate != aggregate:
        errors.append("aggregate is inconsistent with raw runs")
    recomputed_residual = residual_index(plan, rows, aggregate)
    if recomputed_residual != residual:
        errors.append("residual index is inconsistent with frozen rules")
    if contains_sensitive_key([*rows, aggregate, residual]):
        errors.append("artifact contains a prohibited sensitive key")
    return errors
