#!/usr/bin/env python3
"""Execute only the validated Phase 06B OpenViking supplement selection."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from memlife.adapters.openviking import (  # noqa: E402
    OpenVikingMemoryAdapter,
    phase05a_manifest_configuration,
)
from memlife.runner.manifest import hash_configuration  # noqa: E402
from memlife.runner.lifecycle_status import normalize_lifecycle_status  # noqa: E402
from memlife.runner.tracked_text import materialize_tracked_jsonl  # noqa: E402
from memlife.runner.phase06b_supplement import (  # noqa: E402
    DERIVED_RAW_SHA256,
    EXECUTION_ORIGIN,
    FREEZE_ID,
    FREEZE_SHA256,
    ORIGINAL_ATTEMPT_ID,
    ORIGINAL_RAW_SHA256,
    SUPPLEMENT_PLAN_SHA256,
    blocked_supplement_records,
    execute_supplement_runs,
    original_persistent_raw_path,
    validate_supplement_rows,
    validate_supplement_selection,
)
from memlife.runner.storage_batch import (  # noqa: E402
    EXPECTED_CONFIGURATION_HASHES,
    canonical_json,
    generate_run_plan,
    run_repetition,
    sanitize_value,
)
from phase05_openviking import OpenVikingServiceController  # noqa: E402
from phase06b import validate_attempt_id  # noqa: E402
from phase06b_harness import select_approved_harness  # noqa: E402
from phase06b_remote import (  # noqa: E402
    _command,
    _disk_free,
    _distribution_version,
    _git_commit,
    _pip_check,
    _validate_openviking_runtime_config,
)

LIVE_AUTH_ENV = "MEMLIFE_AUTHORIZE_PHASE06B_SUPPLEMENT_LIVE"
PLAN_PATH = (
    REPO_ROOT
    / "experiments"
    / "supplements"
    / "phase06b-openviking-missing-runs-v1.json"
)
FREEZE_PATH = REPO_ROOT / "experiments" / "freeze" / "experiment-freeze-v1.json"
ORIGINAL_ROWS_PATH = (
    REPO_ROOT
    / "artifacts"
    / "phase06b"
    / "derived"
    / "20261001T183940Z-1fc4c4929532"
    / "freeze-v1-raw-runs.provenance-repaired.jsonl"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _memory_info() -> Mapping[str, Any]:
    path = Path("/proc/meminfo")
    if not path.is_file():
        return {"status": "UNAVAILABLE"}
    wanted = {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}
    values: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        key, separator, remainder = line.partition(":")
        if separator and key in wanted:
            values[f"{key}_kib"] = int(remainder.strip().split()[0])
    return values or {"status": "UNAVAILABLE"}


def _process_info(controller: OpenVikingServiceController) -> Mapping[str, Any]:
    pid = controller.service_pid
    if pid is None:
        return {
            "pid": "UNAVAILABLE",
            "alive": False,
            "exit_code": controller.exit_code(),
            "command_identity": "UNAVAILABLE",
            "start_timestamp": "UNAVAILABLE",
            "memory": "UNAVAILABLE",
        }
    proc = Path("/proc") / str(pid)
    command: Any = "UNAVAILABLE"
    memory: Any = "UNAVAILABLE"
    started: Any = "UNAVAILABLE"
    try:
        command = (
            (proc / "cmdline")
            .read_bytes()
            .replace(b"\x00", b" ")
            .decode("utf-8", errors="replace")
            .strip()
        )
    except OSError:
        pass
    try:
        fields: dict[str, str] = {}
        for line in (proc / "status").read_text(
            encoding="utf-8", errors="replace"
        ).splitlines():
            key, separator, value = line.partition(":")
            if separator and key in {"VmRSS", "VmSize", "VmSwap"}:
                fields[f"{key}_kib"] = value.strip().split()[0]
        memory = fields or "UNAVAILABLE"
    except OSError:
        pass
    try:
        stat_fields = (proc / "stat").read_text(encoding="ascii").split()
        ticks = int(stat_fields[21])
        boot = next(
            int(line.split()[1])
            for line in Path("/proc/stat").read_text(encoding="ascii").splitlines()
            if line.startswith("btime ")
        )
        epoch = boot + (ticks / os.sysconf("SC_CLK_TCK"))
        started = datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()
    except (OSError, ValueError, StopIteration, IndexError):
        pass
    return {
        "pid": pid,
        "alive": controller.is_running(),
        "exit_code": controller.exit_code(),
        "command_identity": command,
        "start_timestamp": started,
        "memory": memory,
    }


def _port_status(port: int = 1933) -> Mapping[str, Any]:
    checked = _utc_now()
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.25):
            return {"checked_at": checked, "port": port, "connectable": True}
    except OSError as exc:
        return {
            "checked_at": checked,
            "port": port,
            "connectable": False,
            "error_type": type(exc).__name__,
        }


def _oom_evidence(*, process_alive: bool) -> Mapping[str, Any] | str:
    if process_alive:
        return "NOT_APPLICABLE_PROCESS_ALIVE"
    try:
        completed = subprocess.run(
            ["dmesg", "--level=emerg,alert,crit,err"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "UNAVAILABLE", "error_type": type(exc).__name__}
    if completed.returncode:
        return {"status": "UNAVAILABLE", "error_type": "DmesgAccessDenied"}
    pattern = re.compile(r"(?i)(out of memory|oom-kill|killed process|memory cgroup)")
    relevant = [line[-1000:] for line in completed.stdout.splitlines() if pattern.search(line)]
    return {"status": "AVAILABLE", "relevant_lines": relevant[-20:]}


class Observability:
    """Read-only, bounded instrumentation for one owned OpenViking process."""

    def __init__(
        self,
        *,
        attempt_id: str,
        controller: OpenVikingServiceController,
        adapter: OpenVikingMemoryAdapter,
        volume_mount: Path,
    ) -> None:
        self.attempt_id = attempt_id
        self.controller = controller
        self.adapter = adapter
        self.volume_mount = volume_mount
        self.last_health: Mapping[str, Any] = {"result": "NOT_YET_CHECKED"}
        self.process_exit_timestamp: str | None = None

    def service_integrity(self) -> Mapping[str, Any]:
        requested_at = _utc_now()
        if not self.controller.is_running():
            if self.process_exit_timestamp is None:
                self.process_exit_timestamp = requested_at
            self.last_health = {
                "healthy": False,
                "readiness_result": "NOT_ATTEMPTED_PROCESS_EXITED",
                "health_result": "FAILED",
                "request_timestamp": requested_at,
                "response_error_type": "ServiceProcessExited",
                "process_exit_code": self.controller.exit_code(),
            }
            return self.last_health
        try:
            self.adapter.wait_until_ready(timeout_seconds=5)
            readiness = dict(getattr(self.adapter, "readiness_diagnostics", {}))
            healthy = (
                readiness.get("health_status") == "ok"
                and readiness.get("health_healthy") is True
            )
            self.last_health = {
                "healthy": healthy,
                "readiness_result": readiness.get("readiness_status", "PASS"),
                "health_result": readiness.get("health_status", "UNAVAILABLE"),
                "request_timestamp": requested_at,
                "response_error_type": readiness.get("request_error_class"),
            }
        except Exception as exc:
            self.last_health = {
                "healthy": False,
                "readiness_result": "FAIL",
                "health_result": "FAIL",
                "request_timestamp": requested_at,
                "response_error_type": type(exc).__name__,
            }
        return self.last_health

    def capture(
        self, stage: str, run: Mapping[str, Any] | None
    ) -> Mapping[str, Any]:
        process = _process_info(self.controller)
        if process.get("alive") is False and process.get("pid") != "UNAVAILABLE":
            if self.process_exit_timestamp is None:
                self.process_exit_timestamp = _utc_now()
        log_path = self.controller.log_path
        if log_path.is_file():
            log_sha: Any = hashlib.sha256(log_path.read_bytes()).hexdigest()
            stdout_tail: Any = self.controller.log_tail(lines=60)
        else:
            log_sha = "UNAVAILABLE"
            stdout_tail = "UNAVAILABLE"
        try:
            provider_status: Any = sanitize_value(dict(self.adapter.benchmark_metadata()))
        except Exception as exc:
            provider_status = {"status": "UNAVAILABLE", "error_type": type(exc).__name__}
        return dict(
            sanitize_value(
                {
                    "stage": stage,
                    "system_memory": _memory_info(),
                    "swap_state": {
                        key: value
                        for key, value in _memory_info().items()
                        if str(key).startswith("Swap")
                    },
                    "process": {
                        **process,
                        "exit_timestamp": self.process_exit_timestamp or "UNAVAILABLE",
                    },
                    "service": {
                        "readiness_and_health": self.last_health,
                        "port_status": _port_status(),
                        "stdout_tail": stdout_tail,
                        "stderr_tail": "MERGED_WITH_STDOUT",
                        "service_log_sha256": log_sha,
                        "service_log_path_class": "supplement-attempt/openviking/openviking.log",
                    },
                    "resource": {
                        "root_free_bytes": _disk_free(Path("/")),
                        "persistent_volume_free_bytes": _disk_free(self.volume_mount),
                    },
                    "oom_or_kernel": _oom_evidence(
                        process_alive=bool(process.get("alive"))
                    ),
                    "provider": {
                        "task_or_extraction_state": provider_status,
                        "last_provider_native_status": provider_status,
                        "provider_process_state": (
                            "RUNNING" if process.get("alive") else "EXITED"
                        ),
                        "provider_log_tail": stdout_tail,
                    },
                    "scientific_payload": "NOT_CAPTURED_OR_MUTATED",
                }
            )
        )


def _diagnostic_event(
    *, attempt_id: str, stage: str, payload: Mapping[str, Any], run_id: str | None = None
) -> dict[str, Any]:
    return {
        "attempt_id": attempt_id,
        "run_id": run_id,
        "timestamp": _utc_now(),
        "source": "phase06b_supplement_remote",
        "stage": stage,
        "capture_status": "SUCCESS",
        "payload": dict(payload),
    }


def validate_pre_experiment_environment(
    evidence: dict[str, Any] | None = None,
) -> Mapping[str, Any]:
    evidence = {} if evidence is None else evidence
    expected_commit = os.environ["PHASE06B_EXPECTED_COMMIT"]
    if _git_commit() != expected_commit:
        raise RuntimeError("remote tested commit mismatch")
    evidence["tested_commit"] = expected_commit
    evidence["git_commit_gate"] = "PASS"
    if os.environ.get(LIVE_AUTH_ENV) != "YES":
        raise RuntimeError("supplement live authorization is absent")
    evidence["explicit_live_authorization_gate"] = "PASS"
    freeze_output = _command(
        [sys.executable, str(REPO_ROOT / "scripts" / "validate_experiment_freeze.py")]
    )
    if FREEZE_SHA256 not in freeze_output:
        raise RuntimeError("freeze validator did not emit the canonical SHA-256")
    evidence["freeze_gate"] = "PASS"
    harness = select_approved_harness(
        repo=REPO_ROOT,
        data_root=Path(os.environ["MEMLIFE_DATA_ROOT"]),
        explicit_venv=Path(os.environ["PHASE06B_HARNESS_VENV"]),
    )
    evidence["harness_selected_path"] = str(harness.venv)
    evidence["harness_python_path"] = str(harness.python)
    evidence["sys_prefix"] = str(Path(sys.prefix).resolve())
    if Path(sys.prefix).resolve() != harness.venv:
        raise RuntimeError("supplement did not start from the approved harness")
    _pip_check(harness.python)
    evidence["harness_gate"] = "PASS"
    openviking_python = Path(os.environ["PHASE06B_OPENVIKING_PYTHON"])
    openviking_version = _distribution_version(openviking_python, "openviking")
    if openviking_version != "0.4.22":
        raise RuntimeError("OpenViking frozen distribution version mismatch")
    _pip_check(openviking_python)
    installed = json.loads(
        _command([str(openviking_python), "-m", "pip", "list", "--format=json"])
    )
    if any(
        str(item["name"]).casefold().startswith(("nvidia-", "cuda-"))
        for item in installed
    ):
        raise RuntimeError("OpenViking environment contains forbidden GPU packages")
    if hash_configuration(phase05a_manifest_configuration()) != (
        EXPECTED_CONFIGURATION_HASHES["openviking"]
    ):
        raise RuntimeError("OpenViking frozen configuration hash mismatch")
    _validate_openviking_runtime_config(Path(os.environ["PHASE05_OPENVIKING_CONFIG"]))
    evidence["openviking_runtime_gate"] = "PASS"
    if not original_persistent_raw_path().is_file():
        raise RuntimeError("original Phase 06B raw artifact is unavailable")
    original_raw_sha256 = hashlib.sha256(original_persistent_raw_path().read_bytes()).hexdigest()
    evidence["original_raw_sha256"] = original_raw_sha256
    if original_raw_sha256 != ORIGINAL_RAW_SHA256:
        raise RuntimeError("original Phase 06B raw SHA-256 mismatch")
    evidence["original_raw_gate"] = "PASS"
    errors, selection = validate_supplement_selection(
        plan_path=PLAN_PATH,
        freeze_path=FREEZE_PATH,
        original_rows_path=ORIGINAL_ROWS_PATH,
    )
    if errors or selection is None:
        raise RuntimeError("supplement selection invalid: " + "; ".join(errors))
    derived_materialization = materialize_tracked_jsonl(ORIGINAL_ROWS_PATH)
    evidence["derived_original_canonical_sha256"] = derived_materialization.sha256
    evidence["derived_original_git_blob_sha256"] = hashlib.sha256(
        derived_materialization.git_blob
    ).hexdigest()
    evidence["derived_original_validation_source"] = "GIT_BLOB_CANONICAL_CRLF"
    evidence["supplement_selection_gate"] = "PASS"
    return {
        "freeze_validator": "PASS",
        "freeze_id": FREEZE_ID,
        "freeze_sha256": FREEZE_SHA256,
        "supplement_plan_sha256": SUPPLEMENT_PLAN_SHA256,
        "eligible_run_ids": list(selection.run_ids),
        "eligible_count": len(selection.runs),
        "derived_original_sha256": DERIVED_RAW_SHA256,
        "harness_prefix": str(harness.venv),
        "openviking_version": openviking_version,
        "openviking_configuration_hash": EXPECTED_CONFIGURATION_HASHES["openviking"],
        "downstream_decision_model_calls": 0,
        "rq3_calls": 0,
    }


def _write_jsonl_exclusive(path: Path, rows: list[Mapping[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                + "\n"
            )


from memlife.runner.tracked_text import materialize_tracked_text
import hashlib

def _authorized_plan_snapshot() -> tuple[bytes, list[dict[str, Any]]]:
    """Return the exact authorized plan bytes and frozen run specifications."""

    try:
        plan_materialization = materialize_tracked_text(PLAN_PATH)
    except ValueError as exc:
        raise RuntimeError(f"supplement plan not tracked/canonicalizable: {exc}")

    plan_bytes = plan_materialization.git_blob
    if hashlib.sha256(plan_bytes).hexdigest() != SUPPLEMENT_PLAN_SHA256:
        raise RuntimeError("supplement plan SHA-256 mismatch before snapshot")
    plan = json.loads(plan_bytes.decode("utf-8"))
    eligible = plan.get("eligible_run_ids")
    if not isinstance(eligible, list) or len(eligible) != 10:
        raise RuntimeError("supplement plan does not contain exactly ten run IDs")
    frozen = generate_run_plan(FREEZE_PATH)
    by_id = {str(run["run_id"]): dict(run) for run in frozen["runs"]}
    try:
        runs = [by_id[str(run_id)] for run_id in eligible]
    except KeyError as exc:
        raise RuntimeError("supplement plan contains a non-frozen run ID") from exc
    return plan_bytes, runs


def run(output_dir: Path) -> dict[str, Any]:
    attempt_id = validate_attempt_id(os.environ["PHASE06B_SUPPLEMENT_ATTEMPT_ID"])
    if attempt_id == ORIGINAL_ATTEMPT_ID:
        raise RuntimeError("supplement attempt ID must differ from original attempt")
    commit = _git_commit()
    volume_mount = Path(os.environ["PHASE06B_LIVE_VOLUME_MOUNT"])
    raw_path = output_dir / "supplement-raw-runs.jsonl"
    ledger_path = output_dir / "supplement-execution-ledger.json"
    diagnostics_path = output_dir / "supplement-diagnostics.jsonl"
    plan_snapshot_path = output_dir / "supplement-plan.json"
    aggregate_path = output_dir / "supplement-aggregate.json"
    preflight_path = output_dir / "supplement-preflight.json"
    result: dict[str, Any] = {
        "status": "BLOCKED",
        "supplement_status": "SUPPLEMENT_BLOCKED",
        "attempt_id": attempt_id,
        "execution_origin": EXECUTION_ORIGIN,
        "freeze_id": FREEZE_ID,
        "freeze_sha256": FREEZE_SHA256,
        "supplement_plan_sha256": SUPPLEMENT_PLAN_SHA256,
        "git_commit_tested": commit,
        "eligible_count": 10,
        "executed_count": 0,
        "blocked_not_executed_count": 10,
        "downstream_decision_model_calls": 0,
        "rq3_calls": 0,
        "remote_os": platform.platform(),
        "service": "NOT_STARTED",
    }
    controller: OpenVikingServiceController | None = None
    diagnostics: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    authorized_runs: list[dict[str, Any]] = []
    selection = None
    observability: Observability | None = None
    preflight_evidence: dict[str, Any] = {
        "artifact_kind": "ORIGINAL_ATTEMPT_CAPTURE",
        "attempt_id": attempt_id,
        "status": "IN_PROGRESS",
        "lifecycle_status_vocabulary": "PASS|PARTIAL|BLOCKED",
        "harness_selected_path": str(
            Path(os.environ["PHASE06B_HARNESS_VENV"]).resolve()
        ),
        "sys_prefix": str(Path(sys.prefix).resolve()),
        "root_free_bytes": _disk_free(Path("/")),
        "persistent_volume_free_bytes": _disk_free(volume_mount),
        "supplement_plan_path": str(PLAN_PATH.relative_to(REPO_ROOT).as_posix()),
        "supplement_plan_sha256": SUPPLEMENT_PLAN_SHA256,
        "authorized_run_ids": [],
    }
    try:
        plan_bytes, authorized_runs = _authorized_plan_snapshot()
        with plan_snapshot_path.open("xb") as stream:
            stream.write(plan_bytes)
        preflight_evidence["authorized_run_ids"] = [
            str(run["run_id"]) for run in authorized_runs
        ]
        preflight_evidence["plan_snapshot_status"] = "PASS"
        preflight = validate_pre_experiment_environment(preflight_evidence)
        result["pre_experiment_gate"] = preflight
        errors, selection = validate_supplement_selection(
            plan_path=PLAN_PATH,
            freeze_path=FREEZE_PATH,
            original_rows_path=ORIGINAL_ROWS_PATH,
        )
        if errors or selection is None:
            raise RuntimeError("supplement selection invalid: " + "; ".join(errors))

        controller = OpenVikingServiceController()
        adapter = OpenVikingMemoryAdapter.from_environment(
            restart_callback=controller.restart,
            process_is_running=controller.is_running,
            process_exit_code=controller.exit_code,
        )
        adapter.quiescence_timeout_seconds = 300
        observability = Observability(
            attempt_id=attempt_id,
            controller=controller,
            adapter=adapter,
            volume_mount=volume_mount,
        )
        startup_probe = {
            "system_memory_before_provider_startup": _memory_info(),
            "root_free_bytes": _disk_free(Path("/")),
            "persistent_volume_free_bytes": _disk_free(volume_mount),
            "swap_state": {
                key: value
                for key, value in _memory_info().items()
                if str(key).startswith("Swap")
            },
        }
        diagnostics.append(
            _diagnostic_event(
                attempt_id=attempt_id,
                stage="before_provider_startup",
                payload=startup_probe,
            )
        )
        controller.start()
        result["service"] = "STARTED_RUN_OWNED_SERVICE"
        adapter.wait_until_ready(timeout_seconds=180)

        def run_once(run_spec: Mapping[str, Any]) -> dict[str, Any]:
            return run_repetition(
                adapter=adapter,
                run=run_spec,
                tested_git_commit=commit,
                attempt_id=attempt_id,
                execution_origin=EXECUTION_ORIGIN,
            )

        execution = execute_supplement_runs(
            selection=selection,
            attempt_id=attempt_id,
            tested_commit=commit,
            run_once=run_once,
            service_integrity=observability.service_integrity,
            capture=observability.capture,
        )
        rows.extend(execution.rows)
        blocked.extend(execution.blocked)
        diagnostics.extend(execution.diagnostics)
        result["supplement_status"] = execution.completion
        result["status"] = normalize_lifecycle_status(execution.completion)
    except Exception as exc:
        result["blocker_type"] = type(exc).__name__
        result["blocker"] = str(sanitize_value(str(exc)))
        if observability is not None:
            try:
                diagnostics.append(
                    _diagnostic_event(
                        attempt_id=attempt_id,
                        stage="systemic_blocker",
                        payload=observability.capture("systemic_blocker", None),
                    )
                )
            except Exception as capture_exc:
                diagnostics.append(
                    {
                        "attempt_id": attempt_id,
                        "run_id": None,
                        "timestamp": _utc_now(),
                        "source": "phase06b_supplement_remote",
                        "stage": "systemic_blocker",
                        "capture_status": "FAILURE",
                        "error_type": type(capture_exc).__name__,
                        "payload": "UNAVAILABLE",
                    }
                )
        evidence_runs = selection.runs if selection is not None else authorized_runs
        if evidence_runs:
            completed = {str(row["run_id"]) for row in rows}
            remaining = [run for run in evidence_runs if str(run["run_id"]) not in completed]
            blocked.extend(
                blocked_supplement_records(
                    remaining,
                    attempt_id=attempt_id,
                    reason=f"systemic supplement blocker: {type(exc).__name__}",
                )
            )
        result["supplement_status"] = (
            "SUPPLEMENT_PARTIAL" if rows else "SUPPLEMENT_BLOCKED"
        )
        result["status"] = normalize_lifecycle_status(result["supplement_status"])
    finally:
        if controller is not None and controller.process is not None:
            owned_process = controller.process
            owned_pid = owned_process.pid
            try:
                controller.stop()
                result["service"] = "STOPPED_RUN_OWNED_SERVICE"
                diagnostics.append(
                    _diagnostic_event(
                        attempt_id=attempt_id,
                        stage="after_provider_stop",
                        payload={
                            "process_pid": owned_pid,
                            "process_exit_code": owned_process.poll(),
                            "process_exit_timestamp": _utc_now(),
                            "process_alive": owned_process.poll() is None,
                            "stdout_tail": controller.log_tail(lines=60),
                            "stderr_tail": "MERGED_WITH_STDOUT",
                        },
                    )
                )
            except Exception as exc:
                result["service"] = f"CLEANUP_ERROR:{type(exc).__name__}"

    if selection is not None:
        errors = validate_supplement_rows(
            rows,
            selection=selection,
            attempt_id=attempt_id,
            tested_commit=commit,
        )
        if errors:
            raise RuntimeError("supplement artifact validation failed: " + "; ".join(errors))
    planned_runs = selection.runs if selection is not None else tuple(authorized_runs)
    ledger = {
        "attempt_id": attempt_id,
        "execution_origin": EXECUTION_ORIGIN,
        "planned_run_ids": [str(run["run_id"]) for run in planned_runs],
        "completed_run_ids": [row["run_id"] for row in rows],
        "error_run_ids": [
            row["run_id"] for row in rows if row.get("operation_status") == "ERROR"
        ],
        "blocked_not_executed": blocked,
        "run_statuses": [
            {
                "run_id": row["run_id"],
                "status": row.get("operation_status", "ERROR"),
            }
            for row in rows
        ]
        + [
            {"run_id": item["run_id"], "status": "BLOCKED_NOT_EXECUTED"}
            for item in blocked
        ],
        "same_lifecycle_retries": 0,
    }
    aggregate = {
        "artifact_kind": "OPERATIONAL_COVERAGE_METADATA",
        "attempt_id": attempt_id,
        "planned": len(planned_runs),
        "executed": len(rows),
        "success": sum(row.get("operation_status") == "SUCCESS" for row in rows),
        "error": sum(row.get("operation_status") == "ERROR" for row in rows),
        "blocked_not_executed": len(blocked),
        "scientific_observation": False,
    }
    preflight_evidence["status"] = (
        "PASS"
        if preflight_evidence.get("supplement_selection_gate") == "PASS"
        else "BLOCKED"
    )
    _write_jsonl_exclusive(raw_path, rows)
    _write_jsonl_exclusive(diagnostics_path, diagnostics)
    with ledger_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(canonical_json(ledger))
    with aggregate_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(canonical_json(aggregate))
    with preflight_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(canonical_json(preflight_evidence))
    result.update(
        executed_count=len(rows),
        success_status_count=sum(row.get("operation_status") == "SUCCESS" for row in rows),
        error_count=sum(row.get("operation_status") == "ERROR" for row in rows),
        blocked_not_executed_count=len(blocked),
        diagnostic_event_count=len(diagnostics),
        same_lifecycle_retries=0,
    )
    return dict(sanitize_value(result))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output_dir)
    with args.result.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(canonical_json(result))
    print(canonical_json(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

