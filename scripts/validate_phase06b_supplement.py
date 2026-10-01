"""Validate the Phase 06B OpenViking missing-run supplement design.

This tool is local and read-only. It never contacts Jetstream or executes a
provider. It derives eligibility as the complement of the frozen 42-run plan
and the tracked, provenance-repaired original observations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from memlife.runner.storage_batch import generate_run_plan  # noqa: E402
from memlife.runner.tracked_text import materialize_tracked_jsonl  # noqa: E402
from memlife.runner.phase06b_supplement import (  # noqa: E402
    ORIGINAL_RAW_SHA256,
    SUPPLEMENT_PLAN_SHA256,
    validate_supplement_selection,
)

PLAN_PATH = (
    REPO_ROOT
    / "experiments"
    / "supplements"
    / "phase06b-openviking-missing-runs-v1.json"
)
ORIGINAL_ATTEMPT_ID = "20261001T183940Z-1fc4c4929532"
ORIGINAL_ERROR_RUN_ID = "freeze-v1__openviking__S0__r2"
FREEZE_ID = "experiment-freeze-v1"
FREEZE_SHA256 = "0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b"
DERIVED_RAW_SHA256 = "80b82f177adf4a15659bc583df61c78dafaa034ac931b5592e22a47d01f67a9f"
EXPECTED_ELIGIBLE = [
    "freeze-v1__openviking__S0__r3",
    "freeze-v1__openviking__S2__r1",
    "freeze-v1__openviking__S2__r2",
    "freeze-v1__openviking__S2__r3",
    "freeze-v1__openviking__S3__r1",
    "freeze-v1__openviking__S3__r2",
    "freeze-v1__openviking__S3__r3",
    "freeze-v1__openviking__S4__r1",
    "freeze-v1__openviking__S4__r2",
    "freeze-v1__openviking__S4__r3",
]
REQUIRED_DIAGNOSTICS = {
    "process_pid",
    "process_exit_code",
    "process_start_timestamp",
    "process_stop_timestamp",
    "process_alive",
    "stdout_stderr_tail_sanitized",
    "service_log_sha256",
    "system_memory_before_launch",
    "system_memory_before_each_run",
    "system_memory_after_each_run",
    "process_memory_before_each_run",
    "process_memory_after_each_run",
    "kernel_or_cgroup_oom_evidence",
    "service_port_status",
    "readiness_probe_result",
    "http_error_details",
    "task_or_extraction_status",
    "root_free_bytes",
    "volume_free_bytes",
}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"expected object at {path}:{line_number}")
        rows.append(value)
    return rows


def validate_supplement_plan(
    plan_path: Path = PLAN_PATH, *, repo_root: Path = REPO_ROOT
) -> list[str]:
    """Return validation errors without changing repository or runtime state."""

    errors: list[str] = []
    original_rows_path = (
        repo_root
        / "artifacts"
        / "phase06b"
        / "derived"
        / ORIGINAL_ATTEMPT_ID
        / "freeze-v1-raw-runs.provenance-repaired.jsonl"
    )
    selection_errors, _ = validate_supplement_selection(
        plan_path=plan_path,
        freeze_path=repo_root / "experiments" / "freeze" / "experiment-freeze-v1.json",
        original_rows_path=original_rows_path,
        expected_plan_sha256=(SUPPLEMENT_PLAN_SHA256 if plan_path == PLAN_PATH else None),
    )
    errors.extend(selection_errors)
    plan = _load_json(plan_path)
    freeze = plan.get("original_freeze", {})
    if freeze.get("id") != FREEZE_ID or freeze.get("sha256") != FREEZE_SHA256:
        errors.append("original freeze identity/hash mismatch")
    if freeze.get("modified") is not False:
        errors.append("plan must declare Freeze v1 unmodified")

    freeze_path = repo_root / str(freeze.get("path", ""))
    frozen_plan = generate_run_plan(freeze_path)
    frozen_ids = [str(item["run_id"]) for item in frozen_plan["runs"]]

    original = plan.get("original_attempt", {})
    if original.get("id") != ORIGINAL_ATTEMPT_ID:
        errors.append("original attempt ID mismatch")
    raw_path = repo_root / str(original.get("derived_raw_path", ""))
    try:
        materialization = materialize_tracked_jsonl(raw_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(
            "tracked provenance-repaired original raw artifact is unreadable: "
            f"{type(exc).__name__}"
        )
        rows: list[dict[str, Any]] = []
    else:
        digest = materialization.sha256
        if digest != DERIVED_RAW_SHA256 or digest != original.get("derived_raw_sha256"):
            errors.append("provenance-repaired original raw canonical SHA-256 mismatch")
        rows = list(materialization.rows)

    executed_ids = [str(row.get("run_id")) for row in rows]
    if len(rows) != 32 or len(set(executed_ids)) != 32:
        errors.append("original evidence must contain 32 unique executed run IDs")
    if any(row.get("attempt_id") != ORIGINAL_ATTEMPT_ID for row in rows):
        errors.append("original derived rows do not share the proven attempt ID")
    success_ids = [
        str(row.get("run_id")) for row in rows if row.get("operation_status") == "SUCCESS"
    ]
    error_ids = [
        str(row.get("run_id")) for row in rows if row.get("operation_status") == "ERROR"
    ]
    if len(success_ids) != 31 or error_ids != [ORIGINAL_ERROR_RUN_ID]:
        errors.append("original success/error evidence mismatch")

    derived_eligible = [run_id for run_id in frozen_ids if run_id not in set(executed_ids)]
    eligible = plan.get("eligible_run_ids")
    if eligible != EXPECTED_ELIGIBLE or eligible != derived_eligible:
        errors.append("eligible IDs are not the exact frozen never-executed complement")
    if set(eligible or []).intersection(executed_ids):
        errors.append("eligible set contains an already executed run")
    if any("__openviking__" not in run_id or run_id.endswith("__r4") for run_id in eligible or []):
        errors.append("eligible set contains a forbidden provider or repetition")

    supplement = plan.get("supplement_attempt", {})
    if supplement.get("run_count") != 10 or supplement.get("repetitions_added") != 0:
        errors.append("supplement cardinality/repetition policy mismatch")
    if supplement.get("attempt_id") is not None:
        errors.append("design plan must defer creation of a new attempt ID")
    if supplement.get("attempt_id_must_differ_from_original") is not True:
        errors.append("supplement must require a new attempt ID")
    if supplement.get("artifact_creation") != "EXCLUSIVE_IMMUTABLE_ATTEMPT_SCOPED":
        errors.append("supplement artifacts are not declared immutable and attempt-scoped")
    if supplement.get("intervening_changes_manifest_required") is not True:
        errors.append("intervening code/runtime changes must be recorded")
    if supplement.get("tested_commit_required") is not True:
        errors.append("supplement tested commit must be recorded")
    if supplement.get("local_artifact_path_template") != (
        "artifacts/phase06b/supplements/attempts/{attempt_id}/"
    ):
        errors.append("local supplement artifact path is not attempt-scoped")
    if supplement.get("remote_artifact_path_template") != (
        "<live-mount>/memlife/runs/phase06b/supplements/attempts/{attempt_id}/"
    ):
        errors.append("remote supplement artifact path is not attempt-scoped")

    authorization = plan.get("authorization", {})
    if authorization != {
        "jetstream_action": "KEEP_SHELVED",
        "live_execution_authorized": False,
        "rq3_authorized": False,
    }:
        errors.append("design plan must keep Jetstream shelved and live/RQ3 unauthorized")

    changes = plan.get("change_classification", {})
    if changes.get("actual_bug_fix_required") is not False:
        errors.append("unsupported harness/provider bug-fix claim")
    if changes.get("experimental_behavior_change_authorized") is not False:
        errors.append("experimental-behavior change must remain unauthorized")
    if changes.get("required_change") != "OBSERVABILITY_AND_EXECUTION_SCOPING_ONLY":
        errors.append("required change must remain observability/execution-scoping only")

    diagnostics = plan.get("instrumentation", {})
    if diagnostics.get("classification") != "OBSERVABILITY_ONLY":
        errors.append("instrumentation classification mismatch")
    if diagnostics.get("must_not_change_experiment_semantics") is not True:
        errors.append("instrumentation must preserve experiment semantics")
    if set(diagnostics.get("required_fields", [])) != REQUIRED_DIAGNOSTICS:
        errors.append("required crash diagnostic set mismatch")

    provenance = plan.get("provenance", {})
    if provenance.get("combined_artifact_kind") != "DERIVED_ONLY":
        errors.append("combined artifact must be derived only")
    if provenance.get("original_rows_rewritten") is not False:
        errors.append("original rows must not be rewritten")
    if provenance.get("execution_origin_values") != ["ORIGINAL", "SUPPLEMENT"]:
        errors.append("execution-origin values mismatch")
    if set(provenance.get("required_row_fields", [])) != {"attempt_id", "execution_origin"}:
        errors.append("combined row provenance fields mismatch")

    stop = plan.get("stop_rule", {})
    required_true = {
        "cleanup_owned_resources",
        "preserve_current_result_and_diagnostics",
        "shelve_if_opened_by_run",
        "stop_remaining_runs_on_service_integrity_loss",
    }
    if any(stop.get(key) is not True for key in required_true):
        errors.append("supplement stop rule is incomplete")
    if stop.get("retry_same_lifecycle") is not False:
        errors.append("same-lifecycle retry must be forbidden")

    forbidden = plan.get("forbidden", {})
    for key in (
        "additional_repetitions",
        "executed_run_ids",
        "majority_voting",
        "replacement_observations",
        "retry_in_same_lifecycle",
    ):
        if forbidden.get(key) is not True:
            errors.append(f"forbidden policy missing: {key}")
    return list(dict.fromkeys(errors))


def _git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError((completed.stderr or completed.stdout).strip())
    return completed.stdout.strip()


def validate_pre_live_readiness(
    *, repo_root: Path = REPO_ROOT, plan_path: Path = PLAN_PATH
) -> tuple[list[str], dict[str, Any]]:
    """Run local-only pre-live gates without contacting Jetstream or OpenStack."""

    errors = validate_supplement_plan(plan_path, repo_root=repo_root)
    details: dict[str, Any] = {
        "jetstream_contacted": False,
        "openstack_contacted": False,
        "provider_executed": False,
    }
    try:
        branch = _git(repo_root, "branch", "--show-current")
        details["branch"] = branch
        if branch != "phase-06b-storage-batch":
            errors.append("branch is not phase-06b-storage-batch")
        divergence = _git(
            repo_root,
            "rev-list",
            "--left-right",
            "--count",
            "origin/phase-06b-storage-batch...HEAD",
        ).split()
        if len(divergence) != 2:
            errors.append("origin synchronization status is unreadable")
        else:
            behind, ahead = (int(value) for value in divergence)
            details.update(origin_behind=behind, origin_ahead=ahead)
            if behind:
                errors.append("local branch is behind origin")
    except (RuntimeError, ValueError) as exc:
        errors.append(f"branch/origin synchronization check failed: {exc}")

    details["supplement_plan_sha256"] = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    if details["supplement_plan_sha256"] != SUPPLEMENT_PLAN_SHA256:
        errors.append("supplement plan hash/content mismatch")

    original_raw = (
        repo_root
        / "artifacts"
        / "phase06b"
        / "attempts"
        / ORIGINAL_ATTEMPT_ID
        / "freeze-v1-raw-runs.jsonl"
    )
    if not original_raw.is_file():
        errors.append("attempt-scoped original raw artifact is unavailable")
    else:
        observed = hashlib.sha256(original_raw.read_bytes()).hexdigest()
        details["original_raw_sha256"] = observed
        if observed != ORIGINAL_RAW_SHA256:
            errors.append("original raw SHA-256 changed")
    derived = (
        repo_root
        / "artifacts"
        / "phase06b"
        / "derived"
        / ORIGINAL_ATTEMPT_ID
        / "freeze-v1-raw-runs.provenance-repaired.jsonl"
    )
    try:
        derived_materialization = materialize_tracked_jsonl(derived)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(
            f"derived provenance-repaired artifact is unavailable: {type(exc).__name__}"
        )
    else:
        observed = derived_materialization.sha256
        details["derived_raw_sha256"] = observed
        details["derived_raw_git_blob_sha256"] = hashlib.sha256(
            derived_materialization.git_blob
        ).hexdigest()
        details["derived_raw_validation_source"] = "GIT_BLOB_CANONICAL_CRLF"
        if observed != DERIVED_RAW_SHA256:
            errors.append("derived provenance-repaired canonical SHA-256 changed")
        rows = list(derived_materialization.rows)
        if any(
            row.get("downstream_decision_model_calls") != 0
            or row.get("rq3_calls") != 0
            for row in rows
        ):
            errors.append("original downstream decision/RQ3 calls are not zero")

    controller = repo_root / "scripts" / "jetstream" / "phase06b_supplement.py"
    remote = repo_root / "scripts" / "jetstream" / "phase06b_supplement_remote.py"
    shell = repo_root / "scripts" / "jetstream" / "phase06b_supplement_remote.sh"
    for required in (controller, remote, shell):
        if not required.is_file():
            errors.append(f"supplement implementation missing: {required.name}")
    if controller.is_file():
        controller_text = controller.read_text(encoding="utf-8")
        if "LOCAL_ARTIFACT_ROOT" not in controller_text or "mkdir(exist_ok=False)" not in controller_text:
            errors.append("local attempt-isolation exclusive creation hook missing")
        if "run_id" in " ".join(
            line for line in controller_text.splitlines() if "add_argument" in line
        ):
            errors.append("controller exposes arbitrary run-ID injection")
    if shell.is_file():
        shell_text = shell.read_text(encoding="utf-8")
        required_shell = (
            'RUN_PARENT="$MEMLIFE_DATA_ROOT/runs/phase06b/supplements/attempts"',
            'mkdir "$RUN_ROOT"',
            "phase06b_harness.py",
            'test "$HARNESS_VENV" != "$LEGACY_VENV"',
        )
        if any(fragment not in shell_text for fragment in required_shell):
            errors.append("remote attempt-isolation or harness policy hook missing")
        if "pip install" in shell_text:
            errors.append("supplement shell must not install provider dependencies")
    if remote.is_file():
        remote_text = remote.read_text(encoding="utf-8")
        required_hooks = (
            "validate_supplement_selection",
            "execute_supplement_runs",
            "execution_origin=EXECUTION_ORIGIN",
            "supplement-plan.json",
            "supplement-preflight.json",
            "supplement-aggregate.json",
            "supplement-diagnostics.jsonl",
            "same_lifecycle_retries=0",
            "blocked_supplement_records",
        )
        if any(fragment not in remote_text for fragment in required_hooks):
            errors.append("supplement execution/diagnostics/stop-policy hook missing")
    details["attempt_isolation_readiness"] = "PASS" if not any(
        "attempt-isolation" in error for error in errors
    ) else "FAIL"
    details["harness_policy_readiness"] = "PASS" if not any(
        "harness policy" in error for error in errors
    ) else "FAIL"
    details["diagnostics_hooks"] = "PASS" if not any(
        "diagnostics" in error for error in errors
    ) else "FAIL"
    return list(dict.fromkeys(errors)), details


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=PLAN_PATH)
    parser.add_argument(
        "--design-only",
        action="store_true",
        help="validate only the immutable design content, not local pre-live readiness",
    )
    args = parser.parse_args(argv)
    if args.design_only:
        errors = validate_supplement_plan(args.plan)
        details: dict[str, Any] = {}
    else:
        errors, details = validate_pre_live_readiness(plan_path=args.plan)
    if errors:
        for error in errors:
            print(f"ERROR {error}")
        return 1
    suffix = " ".join(f"{key}={value}" for key, value in sorted(details.items()))
    print(
        "PASS supplement-pre-live eligible=10 executed-original=32 "
        f"freeze=experiment-freeze-v1 {suffix}".rstrip()
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
