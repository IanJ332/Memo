"""Run the live Hindsight compatibility, lifecycle, trace, and persistence checks."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from memlife.adapters.hindsight import HindsightMemoryAdapter
from memlife.models.benchmark import OperationStatus
from memlife.models.memory import QueryCommand, WriteCommand
from memlife.models.provenance import TRACE_SCHEMA_VERSION, serialize_trace
from memlife.runner.provenance import ProvenanceTraceRunner
from memlife.scenarios import canonical_scenarios
from phase04_runtime import HindsightServiceController
from phase04_runtime import restart_hindsight_service, start_hindsight_service
from phase04_runtime import stop_hindsight_service, wait_hindsight_ready

REPO = Path(os.environ.get("PHASE04_REPO", "/home/exouser/Memo"))
HARNESS_PYTHON = Path(
    os.environ.get("PHASE04_HARNESS_PYTHON", str(REPO / ".venv" / "bin" / "python"))
)
HINDSIGHT_VENV = Path(
    os.environ.get(
        "PHASE04_HINDSIGHT_VENV", "/volume/memlife/venvs/hindsight-0.10.1"
    )
)
HINDSIGHT_SERVICE = Path(
    os.environ.get(
        "PHASE04_HINDSIGHT_SERVICE", str(HINDSIGHT_VENV / "bin" / "hindsight-api")
    )
)


def _record_summary(record) -> dict[str, Any]:
    return {
        "provider_record_id": record.memory_id,
        "state": record.state.value,
        "surface": record.metadata.get("hindsight_surface", "UNKNOWN"),
        "fact_type": record.metadata.get("hindsight_fact_type", "unknown"),
        "document_id": record.metadata.get("hindsight_document_id"),
        "source_memory_ids": record.metadata.get("hindsight_source_memory_ids", []),
    }


def _run_command(command: list[str], *, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        command,
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=3600,
    )
    if result.returncode:
        raise RuntimeError(result.stderr[-4000:] or result.stdout[-4000:])
    return result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "passed"


def _sanitized_log_tail(path: Path, *, line_limit: int = 80) -> list[str]:
    """Return bounded startup diagnostics without credentials or public IPs."""

    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-line_limit:]
    secrets = [
        value
        for key, value in os.environ.items()
        if value
        and value != "empty"
        and any(marker in key.upper() for marker in ("KEY", "TOKEN", "SECRET", "PASSWORD"))
    ]
    sanitized: list[str] = []
    for line in lines:
        for secret in secrets:
            line = line.replace(secret, "<redacted-secret>")
        line = re.sub(
            r"\b(?!127\.0\.0\.1\b)(?:\d{1,3}\.){3}\d{1,3}\b",
            "<redacted-ip>",
            line,
        )
        sanitized.append(line[-1000:])
    return sanitized


def run(output: Path) -> dict[str, Any]:
    run_root = Path(os.environ["PHASE04_RUN_ROOT"])
    controller = HindsightServiceController(
        service_executable=HINDSIGHT_SERVICE,
        repo=REPO,
        run_root=run_root,
        environment=os.environ,
    )
    fingerprint_path = Path(os.environ["PHASE04_ENVIRONMENT_FINGERPRINT"])
    result: dict[str, Any] = {
        "status": "IN_PROGRESS",
        "phase": "04",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit_tested": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True
        ).stdout.strip(),
        "python": platform.python_version(),
        "os": platform.platform(),
        "live_volume_mount": os.environ["PHASE04_LIVE_VOLUME_MOUNT"],
        "live_volume_source": os.environ["PHASE04_LIVE_VOLUME_SOURCE"],
        "live_volume_fstype": os.environ["PHASE04_LIVE_VOLUME_FSTYPE"],
        "root_free_before": int(os.environ["PHASE04_ROOT_FREE_BEFORE"]),
        "volume_free_before": int(os.environ["PHASE04_VOLUME_FREE_BEFORE"]),
        "dependency_dry_run": json.loads(os.environ["PHASE04_DRY_RUN_SUMMARY"]),
        "unit_contract": os.environ["PHASE04_UNIT_SUMMARY"],
        "runtime_isolation": {
            "harness_python": str(HARNESS_PYTHON),
            "hindsight_python": os.environ["PHASE04_HINDSIGHT_PYTHON"],
            "hindsight_venv": str(HINDSIGHT_VENV),
            "communication_boundary": "loopback HTTP",
            "hindsight_venv_created_by_this_run": (
                os.environ["PHASE04_HINDSIGHT_VENV_CREATED_BY_THIS_RUN"] == "true"
            ),
        },
        "environment_checks": {
            "harness_before_hindsight": os.environ["PHASE04_HARNESS_PIP_CHECK_BEFORE"],
            "hindsight_provider": os.environ["PHASE04_HINDSIGHT_PIP_CHECK"],
            "harness_after_hindsight": os.environ["PHASE04_HARNESS_PIP_CHECK_AFTER"],
            "comparison_rule": "each environment must pass independently; cross-venv protobuf versions may differ",
        },
        "hindsight_environment_fingerprint": json.loads(
            fingerprint_path.read_text(encoding="utf-8")
        ),
        "internal_llm": {
            "provider": "openai",
            "model": "gpt-oss-120b",
            "endpoint_class": "course-authorized OpenAI-compatible hosted endpoint",
            "structured_output": "not yet probed",
            "purpose": "provider-internal fact extraction and consolidation",
            "rq3_decision_model_calls": 0,
        },
    }
    adapter: HindsightMemoryAdapter | None = None
    try:
        start_hindsight_service(controller)
        adapter = HindsightMemoryAdapter.from_environment(
            restart_callback=lambda: restart_hindsight_service(controller)
        )
        adapter.poll_interval_seconds = 0.5
        adapter.quiescence_timeout_seconds = 600
        wait_hindsight_ready(adapter, timeout_seconds=600)
        result["server_version"] = dict(adapter.verify_server())

        # Mandatory first live compatibility probe. No later work runs if this fails.
        probe_namespace = "phase-04-compatibility-probe"
        adapter.reset_namespace(probe_namespace)
        retained = adapter.write(
            WriteCommand(
                namespace=probe_namespace,
                content="Project Cedar reports are handled by Alice.",
            )
        )
        recalled = adapter.query(
            QueryCommand(
                namespace=probe_namespace,
                query="Who handles Project Cedar reports?",
            )
        )
        if not recalled or not any("alice" in item.content.casefold() for item in recalled):
            raise RuntimeError("compatibility recall did not return meaningful provider state")
        result["compatibility_probe"] = {
            "status": "PASS",
            "retained_record_id": retained.memory_id,
            "recall_record_ids": [item.memory_id for item in recalled],
            "structured_output": "PASS (retain fact extraction parsed)",
        }
        result["internal_llm"]["structured_output"] = "PASS"

        # Basic provider smoke and true service restart/persistence check.
        smoke_namespace = "phase-04-provider-smoke"
        adapter.reset_namespace(smoke_namespace)
        smoke = adapter.write(
            WriteCommand(namespace=smoke_namespace, content="Project Birch restart canary is active.")
        )
        before_restart = adapter.query(
            QueryCommand(namespace=smoke_namespace, query="Project Birch restart canary")
        )
        inspected = adapter.list_or_inspect(smoke_namespace)
        adapter.restart()
        after_restart = adapter.query(
            QueryCommand(namespace=smoke_namespace, query="Project Birch restart canary")
        )
        if not before_restart or not inspected or not after_restart:
            raise RuntimeError("provider smoke persistence check failed")
        result["provider_smoke"] = {
            "status": "PASS",
            "record_id": smoke.memory_id,
            "before_restart_count": len(before_restart),
            "inspect_count": len(inspected),
            "after_restart_count": len(after_restart),
            "restart_result": "persistent source fact recalled after run-owned service restart",
        }

        integration_env = os.environ.copy()
        integration_env["MEMLIFE_RUN_HINDSIGHT_INTEGRATION"] = "1"
        result["hindsight_integration"] = _run_command(
            [
                str(HARNESS_PYTHON),
                "-m",
                "pytest",
                "tests/integration/test_hindsight_adapter.py",
                "-q",
                "-p",
                "no:cacheprovider",
            ],
            env=integration_env,
        )

        benchmark_results = []
        traces = []
        for scenario in canonical_scenarios():
            traced = ProvenanceTraceRunner(adapter).run_scenario(
                scenario,
                experiment_id=f"phase-04-hindsight-{scenario.scenario_id}",
            )
            benchmark_results.extend(traced.benchmark_results)
            traces.append(traced.trace)
        errors = [
            item
            for item in benchmark_results
            if item.operation_status is OperationStatus.ERROR
        ]
        if errors:
            raise RuntimeError(
                "canonical benchmark recorded errors: "
                + ", ".join(f"{item.scenario_id}:{item.step_index}" for item in errors)
            )
        benchmark_path = run_root / "canonical-benchmark.json"
        benchmark_path.write_text(
            json.dumps(
                [item.model_dump(mode="json") for item in benchmark_results],
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        trace_path = run_root / "provenance-traces.json"
        trace_path.write_text(
            json.dumps(
                {
                    "trace_schema_version": TRACE_SCHEMA_VERSION,
                    "traces": [json.loads(serialize_trace(trace)) for trace in traces],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        result["canonical_benchmark"] = [
            item.model_dump(mode="json") for item in benchmark_results
        ]
        result["trace"] = {
            "schema_version": TRACE_SCHEMA_VERSION,
            "scenario_count": len(traces),
            "pass_through_only": True,
            "model_execution_values": sorted(
                {
                    retrieval.model_execution.value
                    for trace in traces
                    for retrieval in trace.retrieval_traces
                }
            ),
        }

        # One limited derived-surface observability probe.
        derived_namespace = "phase-04-derived-observability"
        adapter.reset_namespace(derived_namespace)
        first = adapter.write(
            WriteCommand(
                namespace=derived_namespace,
                content="Project Cedar reports are handled by Alice.",
            )
        )
        second = adapter.write(
            WriteCommand(
                namespace=derived_namespace,
                content="Alice reviews Project Cedar reports every Friday.",
            )
        )
        operation = adapter.trigger_derivation(derived_namespace)
        derived_records = adapter.list_or_inspect(derived_namespace)
        result["derived_probe"] = {
            "status": "PASS",
            "source_record_ids": [first.memory_id, second.memory_id],
            "operation_id": operation.get("operation_id", operation.get("id")),
            "records": [_record_summary(record) for record in derived_records],
        }

        result["mem0_regression"] = _run_command(
            [
                str(HARNESS_PYTHON),
                "-m",
                "pytest",
                "tests/integration/test_mem0_adapter.py",
                "tests/integration/test_mem0_lifecycle_suite.py",
                "-q",
                "-m",
                "mem0_integration",
                "-p",
                "no:cacheprovider",
            ]
        )
        result["full_suite"] = _run_command(
            [str(HARNESS_PYTHON), "-m", "pytest", "-q", "-p", "no:cacheprovider"],
            env=integration_env,
        )
        result["root_free_after"] = int(
            subprocess.run(
                ["df", "-B1", "--output=avail", "/"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.splitlines()[-1].strip()
        )
        result["volume_free_after"] = int(
            subprocess.run(
                ["df", "-B1", "--output=avail", os.environ["PHASE04_LIVE_VOLUME_MOUNT"]],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.splitlines()[-1].strip()
        )
        result["status"] = "PASS"
    except Exception as exc:
        result["status"] = "BLOCKED"
        result["blocker_type"] = type(exc).__name__
        result["blocker"] = str(exc)
        result["service_log_tail"] = _sanitized_log_tail(controller.log_path)
    finally:
        result["hindsight_service_started_by_this_run"] = (
            controller.hindsight_service_started_by_this_run
        )
        try:
            stop_hindsight_service(controller)
            result["service_stopped_cleanly"] = (
                controller.process is None and not controller.pid_path.exists()
            )
        except Exception as cleanup_exc:
            result["service_stopped_cleanly"] = False
            result["service_cleanup_error"] = str(cleanup_exc)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
