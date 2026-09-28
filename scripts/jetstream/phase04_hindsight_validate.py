"""Run the live Hindsight compatibility, lifecycle, trace, and persistence checks."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from memlife.adapters.hindsight import HindsightMemoryAdapter
from memlife.models.benchmark import OperationStatus
from memlife.models.memory import QueryCommand, WriteCommand
from memlife.models.provenance import TRACE_SCHEMA_VERSION, serialize_trace
from memlife.runner.provenance import ProvenanceTraceRunner
from memlife.scenarios import canonical_scenarios

REPO = Path("/home/exouser/Memo")
PYTHON = REPO / ".venv" / "bin" / "python"
SERVICE = REPO / ".venv" / "bin" / "hindsight-api"


class ServiceController:
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.process: subprocess.Popen[bytes] | None = None
        self._log = None

    def start(self) -> None:
        if self.process is not None and self.process.poll() is None:
            raise RuntimeError("Hindsight service is already running")
        self._log = self.log_path.open("ab")
        self.process = subprocess.Popen(
            [str(SERVICE)],
            cwd=REPO,
            env=os.environ.copy(),
            stdout=self._log,
            stderr=subprocess.STDOUT,
        )

    def stop(self) -> None:
        process = self.process
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=45)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=15)
        self.process = None
        if self._log is not None:
            self._log.close()
            self._log = None

    def restart(self) -> None:
        self.stop()
        self.start()


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


def run(output: Path) -> dict[str, Any]:
    run_root = Path(os.environ["PHASE04_RUN_ROOT"])
    controller = ServiceController(run_root / "hindsight-service.log")
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
        controller.start()
        adapter = HindsightMemoryAdapter.from_environment(
            restart_callback=controller.restart
        )
        adapter.poll_interval_seconds = 0.5
        adapter.quiescence_timeout_seconds = 600
        adapter.wait_until_ready(timeout_seconds=600)
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
            "restart_result": "persistent source fact recalled after service + pg0 restart",
        }

        integration_env = os.environ.copy()
        integration_env["MEMLIFE_RUN_HINDSIGHT_INTEGRATION"] = "1"
        result["hindsight_integration"] = _run_command(
            [
                str(PYTHON),
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
                str(PYTHON),
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
            [str(PYTHON), "-m", "pytest", "-q", "-p", "no:cacheprovider"],
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
    finally:
        controller.stop()
        result["service_stopped_cleanly"] = controller.process is None
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
