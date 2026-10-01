"""Fail-closed Phase 06B OpenViking supplement selection and derivation.

This module contains no cloud or provider startup behavior.  It constrains a
future executor to the machine-readable supplement plan and keeps diagnostic
evidence separate from scientific rows.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from memlife.runner.storage_batch import FREEZE_SHA256, generate_run_plan

FREEZE_ID = "experiment-freeze-v1"
ORIGINAL_ATTEMPT_ID = "20261001T183940Z-1fc4c4929532"
ORIGINAL_ERROR_RUN_ID = "freeze-v1__openviking__S0__r2"
ORIGINAL_RAW_SHA256 = "fe6f8cca390fa30b714e7635b9e7e56b987bd8303611f625c3258e90eaea2ef4"
DERIVED_RAW_SHA256 = "80b82f177adf4a15659bc583df61c78dafaa034ac931b5592e22a47d01f67a9f"
SUPPLEMENT_PLAN_SHA256 = "2db182047dd2b1bfddcaddaad40ace58385f8bdcf0bb114354d9724ee5d6626a"
EXECUTION_ORIGIN = "SUPPLEMENT"


@dataclass(frozen=True)
class SupplementSelection:
    """Validated, ordered ten-run selection derived from Freeze v1."""

    plan_id: str
    plan_sha256: str
    runs: tuple[dict[str, Any], ...]
    executed_run_ids: frozenset[str]

    @property
    def run_ids(self) -> tuple[str, ...]:
        return tuple(str(run["run_id"]) for run in self.runs)


@dataclass(frozen=True)
class SupplementExecution:
    """One no-retry traversal of the validated supplement selection."""

    rows: tuple[dict[str, Any], ...]
    blocked: tuple[dict[str, Any], ...]
    diagnostics: tuple[dict[str, Any], ...]
    completion: str


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"expected JSON object at {path}:{line_number}")
        rows.append(value)
    return rows


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_supplement_selection(
    *,
    plan_path: Path,
    freeze_path: Path,
    original_rows_path: Path,
    expected_plan_sha256: str | None = SUPPLEMENT_PLAN_SHA256,
) -> tuple[list[str], SupplementSelection | None]:
    """Validate and derive the sole executable set; return every found error."""

    errors: list[str] = []
    try:
        plan = _load_object(plan_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"supplement plan unreadable: {type(exc).__name__}"], None
    plan_sha256 = sha256_file(plan_path)
    if expected_plan_sha256 is not None and plan_sha256 != expected_plan_sha256:
        errors.append("supplement plan SHA-256 mismatch")

    freeze = plan.get("original_freeze")
    if not isinstance(freeze, Mapping):
        freeze = {}
    if freeze.get("id") != FREEZE_ID or freeze.get("sha256") != FREEZE_SHA256:
        errors.append("original freeze identity/hash mismatch")
    if freeze.get("modified") is not False:
        errors.append("plan must declare Freeze v1 unmodified")

    try:
        frozen = generate_run_plan(freeze_path)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        return [*errors, f"frozen plan validation failed: {type(exc).__name__}: {exc}"], None
    if frozen.get("freeze_id") != FREEZE_ID or frozen.get("freeze_sha256") != FREEZE_SHA256:
        errors.append("generated frozen plan identity/hash mismatch")
    frozen_runs = tuple(dict(run) for run in frozen["runs"])
    frozen_by_id = {str(run["run_id"]): run for run in frozen_runs}

    original = plan.get("original_attempt")
    if not isinstance(original, Mapping):
        original = {}
    if original.get("id") != ORIGINAL_ATTEMPT_ID:
        errors.append("original attempt ID mismatch")
    if original.get("original_raw_sha256") != ORIGINAL_RAW_SHA256:
        errors.append("original raw SHA-256 declaration mismatch")
    if original.get("derived_raw_sha256") != DERIVED_RAW_SHA256:
        errors.append("derived raw SHA-256 declaration mismatch")
    if not original_rows_path.is_file():
        errors.append("tracked provenance-repaired original raw artifact is missing")
        original_rows: list[dict[str, Any]] = []
    else:
        if sha256_file(original_rows_path) != DERIVED_RAW_SHA256:
            errors.append("provenance-repaired original raw SHA-256 mismatch")
        try:
            original_rows = _load_rows(original_rows_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"original rows unreadable: {type(exc).__name__}")
            original_rows = []

    executed_ids = [str(row.get("run_id")) for row in original_rows]
    if len(original_rows) != 32 or len(set(executed_ids)) != 32:
        errors.append("original evidence must contain 32 unique executed run IDs")
    if not set(executed_ids).issubset(frozen_by_id):
        errors.append("original evidence contains a non-frozen run ID")
    if any(row.get("attempt_id") != ORIGINAL_ATTEMPT_ID for row in original_rows):
        errors.append("original derived rows do not share the proven attempt ID")
    error_ids = [
        str(row.get("run_id"))
        for row in original_rows
        if row.get("operation_status") == "ERROR"
    ]
    successes = sum(row.get("operation_status") == "SUCCESS" for row in original_rows)
    if successes != 31 or error_ids != [ORIGINAL_ERROR_RUN_ID]:
        errors.append("original success/error evidence mismatch")

    eligible_value = plan.get("eligible_run_ids")
    eligible = list(eligible_value) if isinstance(eligible_value, list) else []
    if not all(isinstance(run_id, str) for run_id in eligible):
        errors.append("eligible run IDs must all be strings")
        eligible = [str(run_id) for run_id in eligible]
    if len(eligible) != 10:
        errors.append("supplement must contain exactly 10 eligible run IDs")
    if len(eligible) != len(set(eligible)):
        errors.append("duplicate eligible run ID")
    complement = [
        str(run["run_id"])
        for run in frozen_runs
        if str(run["run_id"]) not in set(executed_ids)
    ]
    if eligible != complement:
        errors.append("eligible IDs are not the exact frozen never-executed complement")
    overlap = set(eligible).intersection(executed_ids)
    if overlap:
        errors.append("eligible set contains an already executed run")
    if ORIGINAL_ERROR_RUN_ID in eligible:
        errors.append("OpenViking S0 r2 ERROR must remain excluded")
    if any("__r4" in run_id or run_id.endswith("r4") for run_id in eligible):
        errors.append("eligible set contains forbidden r4")
    selected = [frozen_by_id[run_id] for run_id in eligible if run_id in frozen_by_id]
    if len(selected) != len(eligible):
        errors.append("eligible set contains a run absent from Freeze v1")
    if any(run.get("provider") != "openviking" for run in selected):
        errors.append("eligible set contains a non-OpenViking run")
    namespaces = [str(run.get("namespace")) for run in selected]
    if len(namespaces) != len(set(namespaces)):
        errors.append("duplicate eligible namespace")

    supplement = plan.get("supplement_attempt")
    if not isinstance(supplement, Mapping):
        supplement = {}
    if supplement.get("run_count") != 10 or supplement.get("provider") != "openviking":
        errors.append("supplement run-count/provider policy mismatch")
    if supplement.get("attempt_id") is not None:
        errors.append("plan must not contain a reusable supplement attempt ID")
    if supplement.get("artifact_creation") != "EXCLUSIVE_IMMUTABLE_ATTEMPT_SCOPED":
        errors.append("supplement artifact isolation policy mismatch")
    if supplement.get("local_artifact_path_template") != (
        "artifacts/phase06b/supplements/attempts/{attempt_id}/"
    ):
        errors.append("local supplement artifact path mismatch")
    if supplement.get("remote_artifact_path_template") != (
        "<live-mount>/memlife/runs/phase06b/supplements/attempts/{attempt_id}/"
    ):
        errors.append("remote supplement artifact path mismatch")

    authorization = plan.get("authorization")
    if authorization != {
        "jetstream_action": "KEEP_SHELVED",
        "live_execution_authorized": False,
        "rq3_authorized": False,
    }:
        errors.append("design plan must keep Jetstream shelved and live/RQ3 unauthorized")
    stop = plan.get("stop_rule")
    if not isinstance(stop, Mapping):
        stop = {}
    if stop.get("retry_same_lifecycle") is not False:
        errors.append("same-lifecycle retry must be forbidden")
    if stop.get("stop_remaining_runs_on_service_integrity_loss") is not True:
        errors.append("systemic service-loss stop rule is missing")

    if errors:
        return errors, None
    return (
        [],
        SupplementSelection(
            plan_id=str(plan.get("plan_id")),
            plan_sha256=plan_sha256,
            runs=tuple(selected),
            executed_run_ids=frozenset(executed_ids),
        ),
    )


def validate_supplement_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    selection: SupplementSelection,
    attempt_id: str,
    tested_commit: str | None = None,
) -> list[str]:
    """Validate new rows against the controller identity and exact selection."""

    errors: list[str] = []
    materialized = tuple(rows)
    run_ids = [str(row.get("run_id")) for row in materialized]
    namespaces = [str(row.get("namespace")) for row in materialized]
    selected_by_id = {str(run["run_id"]): run for run in selection.runs}
    if len(run_ids) != len(set(run_ids)):
        errors.append("duplicate supplement raw run IDs")
    if len(namespaces) != len(set(namespaces)):
        errors.append("duplicate supplement raw namespaces")
    if not set(run_ids).issubset(selected_by_id):
        errors.append("supplement raw results contain an ineligible run ID")
    for row in materialized:
        expected = selected_by_id.get(str(row.get("run_id")))
        if expected is not None and any(
            row.get(field) != expected.get(field)
            for field in ("provider", "scenario", "repetition", "namespace")
        ):
            errors.append("supplement row identity does not match validated plan")
        if row.get("attempt_id") != attempt_id:
            errors.append("supplement row attempt ID does not match controller attempt ID")
        if row.get("execution_origin") != EXECUTION_ORIGIN:
            errors.append("supplement row execution_origin is not SUPPLEMENT")
        if row.get("freeze_id") != FREEZE_ID or row.get("freeze_sha256") != FREEZE_SHA256:
            errors.append("supplement row freeze identity/hash mismatch")
        if tested_commit is not None and row.get("tested_git_commit") != tested_commit:
            errors.append("supplement row tested commit mismatch")
        if row.get("downstream_decision_model_calls") != 0 or row.get("rq3_calls") != 0:
            errors.append("supplement row downstream/RQ3 call invariant mismatch")
    return list(dict.fromkeys(errors))


def blocked_supplement_records(
    runs: Iterable[Mapping[str, Any]], *, attempt_id: str, reason: str
) -> list[dict[str, Any]]:
    return [
        {
            "attempt_id": attempt_id,
            "execution_origin": EXECUTION_ORIGIN,
            "run_id": str(run["run_id"]),
            "provider": str(run["provider"]),
            "scenario": str(run["scenario"]),
            "repetition": int(run["repetition"]),
            "namespace": str(run["namespace"]),
            "status": "BLOCKED_NOT_EXECUTED",
            "reason": reason,
        }
        for run in runs
    ]


def _diagnostic_event(
    *, attempt_id: str, run_id: str | None, stage: str, payload: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "attempt_id": attempt_id,
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "supplement_observability",
        "stage": stage,
        "capture_status": "SUCCESS",
        "payload": dict(payload),
    }


def _safe_capture(
    capture: Callable[[str, Mapping[str, Any] | None], Mapping[str, Any]],
    *,
    attempt_id: str,
    run: Mapping[str, Any] | None,
    stage: str,
) -> dict[str, Any]:
    run_id = None if run is None else str(run["run_id"])
    try:
        return _diagnostic_event(
            attempt_id=attempt_id,
            run_id=run_id,
            stage=stage,
            payload=capture(stage, run),
        )
    except Exception as exc:  # diagnostics cannot mutate experiment behavior
        return {
            "attempt_id": attempt_id,
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "supplement_observability",
            "stage": stage,
            "capture_status": "FAILURE",
            "error_type": type(exc).__name__,
            "payload": "UNAVAILABLE",
        }


def execute_supplement_runs(
    *,
    selection: SupplementSelection,
    attempt_id: str,
    tested_commit: str,
    run_once: Callable[[Mapping[str, Any]], dict[str, Any]],
    service_integrity: Callable[[], Mapping[str, Any]],
    capture: Callable[[str, Mapping[str, Any] | None], Mapping[str, Any]],
) -> SupplementExecution:
    """Execute each selected ID at most once and stop on systemic service loss."""

    rows: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    diagnostics = [
        _safe_capture(capture, attempt_id=attempt_id, run=None, stage="after_readiness")
    ]
    for index, run in enumerate(selection.runs):
        diagnostics.append(
            _safe_capture(capture, attempt_id=attempt_id, run=run, stage="before_run")
        )
        row = run_once(run)
        row_errors = validate_supplement_rows(
            [row],
            selection=selection,
            attempt_id=attempt_id,
            tested_commit=tested_commit,
        )
        if row_errors:
            raise RuntimeError("; ".join(row_errors))
        rows.append(row)
        diagnostics.append(
            _safe_capture(capture, attempt_id=attempt_id, run=run, stage="after_run")
        )
        try:
            integrity = dict(service_integrity())
        except Exception as exc:
            integrity = {
                "healthy": False,
                "result": "UNAVAILABLE",
                "error_type": type(exc).__name__,
            }
        diagnostics.append(
            _diagnostic_event(
                attempt_id=attempt_id,
                run_id=str(run["run_id"]),
                stage="service_integrity",
                payload=integrity,
            )
        )
        if integrity.get("healthy") is not True:
            reason = f"systemic OpenViking service integrity loss after {run['run_id']}"
            blocked.extend(
                blocked_supplement_records(
                    selection.runs[index + 1 :], attempt_id=attempt_id, reason=reason
                )
            )
            break

    errors = validate_supplement_rows(
        rows,
        selection=selection,
        attempt_id=attempt_id,
        tested_commit=tested_commit,
    )
    if errors:
        raise RuntimeError("; ".join(errors))
    if len(rows) == len(selection.runs):
        completion = "SUPPLEMENT_COMPLETE"
    elif rows:
        completion = "SUPPLEMENT_PARTIAL"
    else:
        completion = "SUPPLEMENT_BLOCKED"
    return SupplementExecution(tuple(rows), tuple(blocked), tuple(diagnostics), completion)


def derive_combined_view(
    *,
    original_path: Path,
    supplement_path: Path,
    output_path: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    """Exclusively create a derived two-attempt view and provenance manifest."""

    if sha256_file(original_path) != DERIVED_RAW_SHA256:
        raise ValueError("original derived artifact SHA-256 mismatch")
    original = _load_rows(original_path)
    supplement = _load_rows(supplement_path)
    combined: list[dict[str, Any]] = []
    for row in original:
        if row.get("attempt_id") != ORIGINAL_ATTEMPT_ID:
            raise ValueError("original row attempt ID mismatch")
        if "execution_origin" in row:
            raise ValueError("canonical original rows must not be rewritten")
        combined.append({**row, "execution_origin": "ORIGINAL"})
    for row in supplement:
        if row.get("execution_origin") != EXECUTION_ORIGIN:
            raise ValueError("supplement row execution_origin mismatch")
        combined.append(dict(row))

    run_ids = [str(row.get("run_id")) for row in combined]
    if len(run_ids) != len(set(run_ids)):
        raise ValueError("combined view contains duplicate run IDs")
    if len(combined) > 42:
        raise ValueError("combined view exceeds the 42-run frozen plan")
    frozen_error = next(
        (row for row in combined if row.get("run_id") == ORIGINAL_ERROR_RUN_ID), None
    )
    if frozen_error is None or frozen_error.get("operation_status") != "ERROR":
        raise ValueError("combined view did not preserve OpenViking S0 r2 ERROR")

    supplement_attempts = sorted({str(row.get("attempt_id")) for row in supplement})
    if supplement and (len(supplement_attempts) != 1 or "None" in supplement_attempts):
        raise ValueError("supplement source must contain one attempt ID")
    sources = []
    for role, path, rows in (
        ("ORIGINAL", original_path, original),
        ("SUPPLEMENT", supplement_path, supplement),
    ):
        sources.append(
            {
                "role": role,
                "path": str(path),
                "sha256": sha256_file(path),
                "attempt_ids": sorted({str(row.get("attempt_id")) for row in rows}),
                "tested_commits": sorted(
                    {str(row.get("tested_git_commit")) for row in rows}
                ),
            }
        )
    manifest = {
        "artifact_kind": "DERIVED_ONLY",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "freeze_id": FREEZE_ID,
        "freeze_sha256": FREEZE_SHA256,
        "sources": sources,
        "transformation_rules": [
            "infer execution_origin=ORIGINAL only in this derived view",
            "retain supplement execution_origin=SUPPLEMENT",
            "preserve source attempt_id and tested_git_commit",
            "reject duplicate run IDs and preserve S0 r2 ERROR",
            "do not majority-vote or replace observations",
        ],
        "row_count": len(combined),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8", newline="\n") as stream:
        for row in combined:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    try:
        with manifest_path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    except Exception:
        output_path.unlink(missing_ok=True)
        raise
    return manifest
