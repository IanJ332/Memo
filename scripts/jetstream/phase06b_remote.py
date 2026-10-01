#!/usr/bin/env python3
"""Execute the one frozen Phase 06B batch inside the retained clean harness."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from memlife.adapters.hindsight import (  # noqa: E402
    HindsightMemoryAdapter,
)
from memlife.adapters.mem0 import Mem0MemoryAdapter  # noqa: E402
from memlife.adapters.openviking import (  # noqa: E402
    OpenVikingMemoryAdapter,
    phase05a_manifest_configuration,
)
from memlife.runner.manifest import hash_configuration  # noqa: E402
from memlife.runner.storage_batch import (  # noqa: E402
    EXPECTED_CONFIGURATION_HASHES,
    FREEZE_SHA256,
    aggregate_runs,
    blocked_run_records,
    canonical_json,
    generate_run_plan,
    residual_index,
    run_repetition,
    sanitize_value,
    validate_artifacts,
    write_jsonl,
)
from phase04_runtime import (  # noqa: E402
    HindsightServiceController,
    restart_hindsight_service,
    start_hindsight_service,
    stop_hindsight_service,
    wait_hindsight_ready,
)
from phase05_openviking import OpenVikingServiceController  # noqa: E402

LIVE_AUTH_ENV = "MEMLIFE_AUTHORIZE_PHASE06B_LIVE"
FREEZE_PATH = REPO_ROOT / "experiments" / "freeze" / "experiment-freeze-v1.json"


def _command(command: list[str], *, timeout: int = 600) -> str:
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout)[-4000:])
    return result.stdout.strip()


def _distribution_version(python: Path, distribution: str) -> str:
    return _command(
        [
            str(python),
            "-c",
            (
                "import importlib.metadata as m; "
                f"print(m.version({distribution!r}))"
            ),
        ]
    ).splitlines()[-1]


def _pip_check(python: Path) -> None:
    _command([str(python), "-m", "pip", "check"], timeout=900)


def _git_commit() -> str:
    return _command(["git", "rev-parse", "HEAD"], timeout=30)


def _os_release() -> str:
    values: dict[str, str] = {}
    for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator:
            values[key] = value.strip().strip('"')
    return values.get("PRETTY_NAME", platform.platform())


def _disk_free(path: Path) -> int:
    stat = os.statvfs(path)
    return stat.f_bavail * stat.f_frsize


def _mem0_configuration_hash(adapter: Mem0MemoryAdapter) -> str | None:
    configuration = adapter.manifest_configuration()
    configuration.update(
        phase="02B",
        vector_store_path_class="<live-volume>/memlife/providers/mem0/phase-02b/qdrant",
        history_path_class="<live-volume>/memlife/providers/mem0/phase-02b/history/history.db",
        model_cache_path_class="<live-volume>/memlife/model_cache/huggingface",
    )
    return hash_configuration(configuration)


def _validate_openviking_runtime_config(config_path: Path) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    expected = {
        "host": "127.0.0.1",
        "port": 1933,
        "embedding_provider": "local",
        "embedding_model": "bge-small-zh-v1.5-f16",
        "embedding_dimension": 512,
        "vlm_provider": "openai",
        "vlm_model": "gpt-oss-120b",
        "vlm_temperature": 0.0,
        "extraction_enabled": True,
    }
    observed = {
        "host": config.get("server", {}).get("host"),
        "port": config.get("server", {}).get("port"),
        "embedding_provider": config.get("embedding", {}).get("dense", {}).get("provider"),
        "embedding_model": config.get("embedding", {}).get("dense", {}).get("model"),
        "embedding_dimension": config.get("embedding", {}).get("dense", {}).get("dimension"),
        "vlm_provider": config.get("vlm", {}).get("provider"),
        "vlm_model": config.get("vlm", {}).get("model"),
        "vlm_temperature": config.get("vlm", {}).get("temperature"),
        "extraction_enabled": config.get("memory", {}).get("extraction_enabled"),
    }
    if observed != expected:
        raise RuntimeError("OpenViking frozen semantic runtime configuration mismatch")
    if not config.get("vlm", {}).get("api_base") or not config.get("vlm", {}).get("api_key"):
        raise RuntimeError("OpenViking protected runtime configuration is incomplete")


def validate_pre_experiment_environment() -> dict[str, Any]:
    """Fail closed before any experimental namespace or provider service starts."""

    expected_commit = os.environ["PHASE06B_EXPECTED_COMMIT"]
    actual_commit = _git_commit()
    if actual_commit != expected_commit:
        raise RuntimeError("remote tested commit mismatch")
    if os.environ.get(LIVE_AUTH_ENV) != "YES":
        raise RuntimeError("Phase 06B live authorization is absent")
    freeze_output = _command(
        [sys.executable, str(REPO_ROOT / "scripts" / "validate_experiment_freeze.py")]
    )
    if FREEZE_SHA256 not in freeze_output:
        raise RuntimeError("remote freeze validator did not emit the frozen SHA-256")

    harness_python = Path(sys.executable).resolve()
    legacy = (REPO_ROOT / ".venv" / "bin" / "python").resolve()
    if harness_python == legacy:
        raise RuntimeError("legacy repository .venv is forbidden for Phase 06B")
    if version("mem0ai") != "2.2.1" or version("sentence-transformers") != "6.1.0":
        raise RuntimeError("Mem0 frozen distribution version mismatch")
    _pip_check(harness_python)

    hindsight_python = Path(os.environ["PHASE06B_HINDSIGHT_PYTHON"])
    openviking_python = Path(os.environ["PHASE06B_OPENVIKING_PYTHON"])
    if _distribution_version(hindsight_python, "hindsight-api-slim") != "0.10.1":
        raise RuntimeError("Hindsight frozen distribution version mismatch")
    _pip_check(hindsight_python)
    if _distribution_version(openviking_python, "openviking") != "0.4.22":
        raise RuntimeError("OpenViking frozen distribution version mismatch")
    llama_version = _distribution_version(openviking_python, "llama-cpp-python")
    _pip_check(openviking_python)
    installed = json.loads(
        _command([str(openviking_python), "-m", "pip", "list", "--format=json"])
    )
    forbidden = [
        item["name"]
        for item in installed
        if str(item["name"]).casefold().startswith(("nvidia-", "cuda-"))
    ]
    if forbidden:
        raise RuntimeError("OpenViking environment contains forbidden CUDA/NVIDIA packages")

    mem0_adapter = Mem0MemoryAdapter.from_runtime(REPO_ROOT)
    try:
        mem0_hash = _mem0_configuration_hash(mem0_adapter)
    finally:
        mem0_adapter.close()
    if mem0_hash != EXPECTED_CONFIGURATION_HASHES["mem0"]:
        raise RuntimeError("Mem0 frozen configuration hash mismatch")
    openviking_hash = hash_configuration(phase05a_manifest_configuration())
    if openviking_hash != EXPECTED_CONFIGURATION_HASHES["openviking"]:
        raise RuntimeError("OpenViking frozen configuration hash mismatch")
    _validate_openviking_runtime_config(Path(os.environ["PHASE05_OPENVIKING_CONFIG"]))

    hindsight_manifest = json.loads(
        (REPO_ROOT / "manifests" / "phase-04-hindsight-bringup.json").read_text(
            encoding="utf-8"
        )
    )
    if hindsight_manifest.get("config_sha256") != EXPECTED_CONFIGURATION_HASHES["hindsight"]:
        raise RuntimeError("Hindsight stored frozen configuration hash mismatch")
    expected_hindsight = {
        "HINDSIGHT_API_HOST": "127.0.0.1",
        "HINDSIGHT_API_PORT": "8888",
        "HINDSIGHT_API_LLM_PROVIDER": "openai",
        "HINDSIGHT_API_LLM_MODEL": "gpt-oss-120b",
        "HINDSIGHT_API_EMBEDDINGS_PROVIDER": "onnx",
        "HINDSIGHT_API_EMBEDDINGS_ONNX_MODEL_ID": "intfloat/multilingual-e5-small",
        "HINDSIGHT_API_EMBEDDINGS_ONNX_DIMENSIONS": "384",
        "HINDSIGHT_API_RERANKER_PROVIDER": "rrf",
        "HINDSIGHT_API_RETAIN_BATCH_ENABLED": "false",
    }
    if any(os.environ.get(key) != value for key, value in expected_hindsight.items()):
        raise RuntimeError("Hindsight frozen semantic runtime configuration mismatch")
    pg0 = Path("/home/exouser/.pg0")
    expected_pg0 = Path(os.environ["PHASE06B_HINDSIGHT_PG0_ROOT"])
    if not pg0.is_symlink() or pg0.resolve() != expected_pg0.resolve():
        raise RuntimeError("Hindsight persistent pg0 path mismatch")

    return {
        "freeze_validator": "PASS",
        "freeze_sha256": FREEZE_SHA256,
        "git_commit": actual_commit,
        "providers": {
            "mem0": {
                "version": "2.2.1",
                "configuration_hash": mem0_hash,
                "pip_check": "PASS",
            },
            "hindsight": {
                "version": "0.10.1",
                "configuration_hash": EXPECTED_CONFIGURATION_HASHES["hindsight"],
                "pip_check": "PASS",
                "pg0_path": "persistent-volume/providers/hindsight/pg0",
            },
            "openviking": {
                "version": "0.4.22",
                "configuration_hash": openviking_hash,
                "llama_cpp_python_version": llama_version,
                "pip_check": "PASS",
                "cuda_nvidia_packages": [],
            },
        },
        "repetitions": 3,
        "downstream_decision_calls": 0,
    }


def _execute_provider(
    *,
    provider: str,
    adapter: Any,
    runs: list[dict[str, Any]],
    tested_commit: str,
    health_check: Callable[[], None] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    results: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for index, run in enumerate(runs):
        result = run_repetition(
            adapter=adapter,
            run=run,
            tested_git_commit=tested_commit,
        )
        results.append(result)
        if result["operation_status"] == "ERROR" and health_check is not None:
            try:
                health_check()
            except Exception as exc:
                blocked.extend(
                    blocked_run_records(
                        runs[index + 1 :],
                        provider=provider,
                        reason=f"systemic provider health failure: {type(exc).__name__}",
                    )
                )
                break
    return results, blocked


def run(output_dir: Path) -> dict[str, Any]:
    plan = generate_run_plan(FREEZE_PATH)
    commit = _git_commit()
    data_root = Path(os.environ["MEMLIFE_DATA_ROOT"])
    volume_mount = Path(os.environ["PHASE06B_LIVE_VOLUME_MOUNT"])
    root_before = _disk_free(Path("/"))
    volume_before = _disk_free(volume_mount)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "freeze-v1-raw-runs.jsonl"
    aggregate_path = output_dir / "freeze-v1-aggregate.json"
    residual_path = output_dir / "freeze-v1-residual-index.json"
    ledger_path = output_dir / "execution-ledger.json"
    plan_path = output_dir / "planned-runs.json"
    plan_path.write_text(canonical_json(plan), encoding="utf-8")

    result: dict[str, Any] = {
        "status": "BLOCKED",
        "cleanup_independent_experimental_status": "BLOCKED",
        "freeze_id": plan["freeze_id"],
        "freeze_sha256": FREEZE_SHA256,
        "git_commit_tested": commit,
        "planned_supported_count": 42,
        "executed_count": 0,
        "success_status_count": 0,
        "error_count": 0,
        "blocked_not_executed_count": 42,
        "unsupported_cell_count": 4,
        "provider_coverage": {},
        "raw_result_path": str(raw_path),
        "aggregate_path": str(aggregate_path),
        "residual_index_path": str(residual_path),
        "execution_ledger_path": str(ledger_path),
        "downstream_decision_model_calls": 0,
        "rq3_calls": 0,
        "provider_internal_models": {
            "hindsight": "gpt-oss-120b (provider_internal)",
            "openviking": "gpt-oss-120b (provider_internal)",
        },
        "remote_os": _os_release(),
        "volume_mount": str(volume_mount),
        "memlife_data_root": str(data_root),
        "root_free_before": root_before,
        "volume_free_before": volume_before,
        "services": {
            "mem0": "NOT_STARTED",
            "hindsight": "NOT_STARTED",
            "openviking": "NOT_STARTED",
        },
    }
    raw_runs: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    preflight: dict[str, Any] | None = None

    hindsight_controller: HindsightServiceController | None = None
    openviking_controller: OpenVikingServiceController | None = None
    try:
        preflight = validate_pre_experiment_environment()
        result["pre_experiment_gate"] = preflight

        os.environ["MEMLIFE_MEM0_PROVIDER_INSTANCE"] = "phase-06b-freeze-v1"
        mem0 = Mem0MemoryAdapter.from_runtime(REPO_ROOT)
        try:
            provider_runs = [item for item in plan["runs"] if item["provider"] == "mem0"]
            completed, provider_blocked = _execute_provider(
                provider="mem0",
                adapter=mem0,
                runs=provider_runs,
                tested_commit=commit,
            )
            raw_runs.extend(completed)
            blocked.extend(provider_blocked)
            result["services"]["mem0"] = "CLOSED_AFTER_BATCH"
        finally:
            mem0.close()

        hindsight_run_root = Path(os.environ["PHASE06B_RUN_ROOT"]) / "hindsight"
        hindsight_controller = HindsightServiceController(
            service_executable=Path(os.environ["PHASE06B_HINDSIGHT_SERVICE"]),
            repo=REPO_ROOT,
            run_root=hindsight_run_root,
            environment=os.environ,
        )
        start_hindsight_service(hindsight_controller)
        hindsight = HindsightMemoryAdapter.from_environment(
            restart_callback=lambda: restart_hindsight_service(hindsight_controller)
        )
        hindsight.poll_interval_seconds = 0.5
        hindsight.quiescence_timeout_seconds = 600
        wait_hindsight_ready(hindsight, timeout_seconds=600)
        provider_runs = [item for item in plan["runs"] if item["provider"] == "hindsight"]
        completed, provider_blocked = _execute_provider(
            provider="hindsight",
            adapter=hindsight,
            runs=provider_runs,
            tested_commit=commit,
            health_check=lambda: hindsight.verify_server(),
        )
        raw_runs.extend(completed)
        blocked.extend(provider_blocked)
        stop_hindsight_service(hindsight_controller)
        result["services"]["hindsight"] = "STOPPED_RUN_OWNED_SERVICE"

        openviking_controller = OpenVikingServiceController()
        openviking = OpenVikingMemoryAdapter.from_environment(
            restart_callback=openviking_controller.restart,
            process_is_running=openviking_controller.is_running,
            process_exit_code=openviking_controller.exit_code,
        )
        openviking.quiescence_timeout_seconds = 300
        openviking_controller.start()
        openviking.wait_until_ready(timeout_seconds=180)
        provider_runs = [item for item in plan["runs"] if item["provider"] == "openviking"]
        completed, provider_blocked = _execute_provider(
            provider="openviking",
            adapter=openviking,
            runs=provider_runs,
            tested_commit=commit,
            health_check=lambda: openviking.wait_until_ready(timeout_seconds=5),
        )
        raw_runs.extend(completed)
        blocked.extend(provider_blocked)
        openviking_controller.stop()
        result["services"]["openviking"] = "STOPPED_RUN_OWNED_SERVICE"
    except Exception as exc:
        result["blocker_type"] = type(exc).__name__
        result["blocker"] = str(sanitize_value(str(exc)))
        already_accounted = {str(item["run_id"]) for item in raw_runs}
        already_accounted.update(str(item["run_id"]) for item in blocked)
        remaining = [
            item for item in plan["runs"] if str(item["run_id"]) not in already_accounted
        ]
        for provider in plan["provider_order"]:
            blocked.extend(
                blocked_run_records(
                    remaining,
                    provider=str(provider),
                    reason=f"batch stopped after systemic blocker: {type(exc).__name__}",
                )
            )
    finally:
        if hindsight_controller is not None and hindsight_controller.process is not None:
            try:
                stop_hindsight_service(hindsight_controller)
                result["services"]["hindsight"] = "STOPPED_RUN_OWNED_SERVICE"
            except Exception as exc:
                result["services"]["hindsight"] = f"CLEANUP_ERROR:{type(exc).__name__}"
        if openviking_controller is not None and openviking_controller.process is not None:
            try:
                openviking_controller.stop()
                result["services"]["openviking"] = "STOPPED_RUN_OWNED_SERVICE"
            except Exception as exc:
                result["services"]["openviking"] = f"CLEANUP_ERROR:{type(exc).__name__}"

    write_jsonl(raw_runs, raw_path)
    aggregate = aggregate_runs(plan, raw_runs)
    residual = residual_index(plan, raw_runs, aggregate)
    aggregate_path.write_text(canonical_json(aggregate), encoding="utf-8")
    residual_path.write_text(canonical_json(residual), encoding="utf-8")
    ledger = {
        "planned_run_ids": [item["run_id"] for item in plan["runs"]],
        "completed_run_ids": [item["run_id"] for item in raw_runs],
        "error_run_ids": [
            item["run_id"] for item in raw_runs if item["operation_status"] == "ERROR"
        ],
        "blocked_not_executed": blocked,
        "unsupported_cells": plan["unsupported_cells"],
    }
    ledger_path.write_text(canonical_json(ledger), encoding="utf-8")
    errors = validate_artifacts(
        plan=plan,
        raw_runs=raw_runs,
        aggregate=aggregate,
        residual=residual,
        require_complete=len(raw_runs) == 42,
    )
    if errors:
        result["artifact_validation_errors"] = errors
    executed = len(raw_runs)
    error_count = sum(item["operation_status"] == "ERROR" for item in raw_runs)
    if executed == 42 and not errors:
        experimental_status = "PASS"
    elif executed > 0 and not errors:
        experimental_status = "PARTIAL"
    else:
        experimental_status = "BLOCKED"
    result.update(
        status=experimental_status,
        cleanup_independent_experimental_status=experimental_status,
        executed_count=executed,
        success_status_count=executed - error_count,
        error_count=error_count,
        blocked_not_executed_count=42 - executed,
        provider_coverage={
            provider: {
                "planned": sum(item["provider"] == provider for item in plan["runs"]),
                "executed": sum(item["provider"] == provider for item in raw_runs),
                "errors": sum(
                    item["provider"] == provider and item["operation_status"] == "ERROR"
                    for item in raw_runs
                ),
            }
            for provider in plan["provider_order"]
        },
        residual_run_count=residual["residual_run_count"],
        residual_cell_count=residual["residual_cell_count"],
        root_free_after=_disk_free(Path("/")),
        volume_free_after=_disk_free(volume_mount),
    )
    return dict(sanitize_value(result))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output_dir)
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(canonical_json(result), encoding="utf-8")
    print(canonical_json(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
