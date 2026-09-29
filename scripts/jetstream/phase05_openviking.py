"""Guarded Phase 05 OpenViking orchestrator and remote validator.

Local orchestration intentionally remains stdlib-only.  MemLife runtime imports
are deferred until ``validate_remote`` is executing in the remote harness.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
REMOTE_REPO = "/home/exouser/Memo"
BRANCH = "phase-05-openviking-bringup"
RESULT_PREFIX = "PHASE05_RESULT_B64="
LOCAL_RESULT = (
    REPO_ROOT
    / "runtime_reports"
    / "phase-05-openviking"
    / "result.json"
)
LIVE_AUTH_ENV = "MEMLIFE_AUTHORIZE_PHASE05_LIVE"
LIVE_CONFIG_PATH = f"{REMOTE_REPO}/.local/phase05_openviking.env"
REQUIRED_DISTRIBUTIONS = ("openviking", "llama-cpp-python")
LIVE_CONFIG_VALUES = {
    "PHASE05_OPENVIKING_VLM_PROVIDER": "openai",
    "PHASE05_OPENVIKING_VLM_MODEL": "gpt-oss-120b",
    "PHASE05_OPENVIKING_VLM_API_BASE": (
        "https://llm.jetstream-cloud.org/gpt-oss-120b/v1/"
    ),
    "PHASE05_OPENVIKING_VLM_API_KEY": "empty",
}


class ServiceExitedBeforeReady(RuntimeError):
    """The controller's one owned child exited before HTTP readiness."""

    def __init__(self, exit_code: int | None) -> None:
        rendered = "unknown" if exit_code is None else str(exit_code)
        super().__init__(f"OpenViking service exited before readiness (exit code {rendered})")
        self.exit_code = exit_code


def require_live_authorization() -> None:
    if os.environ.get(LIVE_AUTH_ENV) != "YES":
        raise RuntimeError(
            f"Phase 05 live execution is disabled; set {LIVE_AUTH_ENV}=YES only in "
            "a separately authorized live conversation"
        )


def _sync_command(expected_commit: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", expected_commit):
        raise ValueError("expected commit must be a full lowercase Git object ID")
    return f"""set -eu
repo={REMOTE_REPO}
cd "$repo"
if [ -n "$(git status --porcelain)" ]; then
    printf '%s\n' 'remote clone has unexplained modifications' >&2
    git status --short >&2
    exit 21
fi
git fetch origin
if git show-ref --verify --quiet refs/heads/{BRANCH}; then
    git switch {BRANCH}
    git merge --ff-only origin/{BRANCH}
else
    git switch --track -c {BRANCH} origin/{BRANCH}
fi
actual="$(git rev-parse HEAD)"
test "$actual" = '{expected_commit}'
printf 'remote_branch=%s\n' "$(git branch --show-current)"
printf 'remote_head=%s\n' "$actual"
"""


def _live_config_command() -> str:
    """Return a fixed, non-interactive mode-600 runtime-config provisioner."""

    assignments = "\n".join(
        f"{name}={value}" for name, value in LIVE_CONFIG_VALUES.items()
    )
    encoded = base64.b64encode((assignments + "\n").encode("utf-8")).decode("ascii")
    return f"""set -eu
config_dir={REMOTE_REPO}/.local
config_path={LIVE_CONFIG_PATH}
umask 077
mkdir -p "$config_dir"
printf '%s' '{encoded}' | base64 -d > "$config_path.tmp"
chmod 600 "$config_path.tmp"
mv -f "$config_path.tmp" "$config_path"
test "$(stat -c %a "$config_path")" = 600
test "$(stat -c %U "$config_path")" = exouser
test "$(wc -l < "$config_path" | xargs)" = 4
printf '%s\n' 'phase05_runtime_config=provisioned'
"""


def _contains_sensitive_result_key(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in {
                "api_key",
                "authorization",
                "password",
                "token",
                "secret",
                "access_key",
            }:
                return True
            if _contains_sensitive_result_key(child):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_sensitive_result_key(item) for item in value)
    return False


def canonicalize_distribution_name(name: object) -> str:
    """Return the PEP 503 canonical form used for dependency comparisons."""

    return re.sub(r"[-_.]+", "-", str(name).strip().lower())


def _git_commit_tested() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    ).stdout.strip()


def validate_dependency_plan(report: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and describe a pip ``--report`` plan without losing context."""

    candidates: dict[str, str] = {}
    normalized_names: set[str] = set()
    for item in report.get("install", []):
        metadata = item.get("metadata", {}) if isinstance(item, Mapping) else {}
        name = canonicalize_distribution_name(metadata.get("name", ""))
        if not name:
            continue
        normalized_names.add(name)
        version = str(metadata.get("version", "")).strip()
        if version:
            candidates[name] = version

    observed = sorted(normalized_names)
    forbidden = sorted(
        name for name in normalized_names if name.startswith(("nvidia-", "cuda-"))
    )
    missing = [name for name in REQUIRED_DISTRIBUTIONS if name not in normalized_names]
    result: dict[str, Any] = {
        "status": "PASS",
        "stage": "dependency_plan",
        "git_commit_tested": _git_commit_tested(),
        "normalized_distributions": observed,
        "required_distributions": list(REQUIRED_DISTRIBUTIONS),
        "openviking_version_candidate": candidates.get("openviking"),
        "llama_cpp_python_version_candidate": candidates.get("llama-cpp-python"),
        "forbidden_distributions": forbidden,
    }
    if missing:
        result.update(
            status="BLOCKED",
            blocker_type="MissingRequiredDistribution",
            missing_required_distributions=missing,
            required=missing[0],
            blocker=f"dependency plan omitted required distribution: {missing[0]}",
        )
    elif forbidden:
        result.update(
            status="BLOCKED",
            blocker_type="ForbiddenDistribution",
            blocker="dependency plan contains forbidden CUDA/NVIDIA distributions",
        )
    return result


def run_remote_validation(
    *,
    address: str,
    facts: Mapping[str, str],
    expected_commit: str,
    ssh_builder: Callable[[str, str], Sequence[str]],
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> Mapping[str, Any]:
    """Run only after an explicit future authorization gate."""

    require_live_authorization()
    sync = runner(ssh_builder(address, _sync_command(expected_commit)), timeout=180)
    runner(ssh_builder(address, _live_config_command()), timeout=60)
    validation = runner(
        ssh_builder(
            address,
            f"{LIVE_AUTH_ENV}=YES bash {REMOTE_REPO}/scripts/jetstream/phase05_openviking_remote.sh",
        ),
        timeout=7200,
    )
    encoded = next(
        (
            line[len(RESULT_PREFIX) :]
            for line in reversed(validation.stdout.splitlines())
            if line.startswith(RESULT_PREFIX)
        ),
        None,
    )
    if not encoded:
        raise RuntimeError("remote OpenViking validation returned no sanitized payload")
    payload = json.loads(base64.b64decode(encoded).decode("utf-8"))
    if _contains_sensitive_result_key(payload):
        raise RuntimeError("remote OpenViking result contained a prohibited sensitive field")
    if payload.get("git_commit_tested") != expected_commit:
        raise RuntimeError("remote result commit did not match the local branch commit")
    payload["remote_sync"] = sync.stdout.strip().splitlines()
    payload["live_mount_probe"] = facts.get("resolved_volume_mount")
    LOCAL_RESULT.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_RESULT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def _sanitize_runtime_text(value: object) -> str:
    """Bound and redact provider/service diagnostics before result serialization."""

    text = str(value or "")
    secret = os.environ.get("PHASE05_OPENVIKING_VLM_API_KEY", "")
    if secret and secret != "empty":
        text = text.replace(secret, "[REDACTED]")
    text = re.sub(
        r'''(?i)(["']?(?:api[_-]?key|authorization|password|token|secret|access[_-]?key)["']?\s*[:=]\s*)["']?[^\s,"'}\]]+["']?''',
        r"\1[REDACTED]",
        text,
    )
    text = re.sub(
        r"(?i)(OS_(?:APPLICATION_CREDENTIAL_SECRET|PASSWORD|TOKEN)\s*[:=]\s*)[^\s,}\]]+",
        r"\1[REDACTED]",
        text,
    )
    text = re.sub(
        r"\b(?!127\.0\.0\.1\b)(?:\d{1,3}\.){3}\d{1,3}\b",
        "[REDACTED_IP]",
        text,
    )
    return text[-8000:]


def _sanitize_runtime_value(value: object) -> object:
    """Recursively sanitize provider diagnostics without changing their shape."""

    if isinstance(value, Mapping):
        return {
            str(key): _sanitize_runtime_value(child)
            for key, child in value.items()
            if str(key).lower().replace("-", "_")
            not in {"api_key", "authorization", "password", "token", "secret"}
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize_runtime_value(child) for child in value]
    if isinstance(value, str):
        return _sanitize_runtime_text(value)
    return value


def write_blocked_result(
    output: Path,
    *,
    stage: str,
    blocker_type: str,
    message: object = "",
    diagnostic_file: Path | None = None,
) -> dict[str, Any]:
    """Write a bounded, sanitized result for an expected pre-validator gate."""

    diagnostic = str(message or "")
    if diagnostic_file is not None:
        try:
            diagnostic = diagnostic_file.read_text(
                encoding="utf-8", errors="replace"
            )
        except OSError as exc:
            diagnostic = f"diagnostic unavailable: {type(exc).__name__}"
    result = {
        "status": "BLOCKED",
        "stage": canonicalize_distribution_name(stage).replace("-", "_"),
        "blocker_type": re.sub(r"[^A-Za-z0-9_.-]", "", blocker_type)[:120]
        or "PreflightError",
        "blocker": _sanitize_runtime_text(diagnostic),
        "git_commit_tested": _git_commit_tested(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def _service_log_tail(path: Path, *, lines: int = 40) -> list[str]:
    if not path.is_file():
        return []
    try:
        raw_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return [_sanitize_runtime_text(f"service log unavailable: {type(exc).__name__}")]
    return [_sanitize_runtime_text(line) for line in raw_lines[-lines:]]


class OpenVikingServiceController:
    """Own exactly one service process; never performs broad process cleanup."""

    def __init__(self) -> None:
        self.executable = Path(os.environ["PHASE05_OPENVIKING_SERVICE"])
        self.config = Path(os.environ["PHASE05_OPENVIKING_CONFIG"])
        self.run_root = Path(os.environ["PHASE05_RUN_ROOT"])
        self.pid_path = self.run_root / "openviking.pid"
        self.log_path = self.run_root / "openviking.log"
        self.process: subprocess.Popen[bytes] | None = None
        self._log = None

    def is_running(self) -> bool:
        """Return liveness for this controller's child only."""

        return self.process is not None and self.process.poll() is None

    def exit_code(self) -> int | None:
        """Return this controller's child exit code, or None while it is alive/unstarted."""

        return None if self.process is None else self.process.poll()

    @property
    def service_pid(self) -> int | None:
        """Return the PID of the exact child owned by this controller."""

        return None if self.process is None else self.process.pid

    def log_tail(self, *, lines: int = 40) -> list[str]:
        return _service_log_tail(self.log_path, lines=lines)

    def start(self) -> None:
        if self.pid_path.exists():
            raise RuntimeError(f"refusing to replace existing PID file: {self.pid_path}")
        if not self.executable.is_file():
            raise RuntimeError(f"OpenViking executable is absent: {self.executable}")
        self.run_root.mkdir(parents=True, exist_ok=True)
        self._log = self.log_path.open("ab")
        self.process = subprocess.Popen(
            [
                str(self.executable),
                "--config",
                str(self.config),
                "--host",
                "127.0.0.1",
                "--port",
                "1933",
            ],
            cwd=self.run_root,
            env=os.environ.copy(),
            stdout=self._log,
            stderr=subprocess.STDOUT,
        )
        exit_code = self.process.poll()
        if exit_code is not None:
            raise ServiceExitedBeforeReady(exit_code)
        self.pid_path.write_text(f"{self.process.pid}\n", encoding="ascii")

    def stop(self) -> None:
        process = self.process
        try:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=45)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=15)
            if process is not None and self.pid_path.exists():
                recorded = self.pid_path.read_text(encoding="ascii").strip()
                if recorded != str(process.pid):
                    raise RuntimeError("OpenViking PID ownership changed")
                self.pid_path.unlink()
        finally:
            self.process = None
            if self._log is not None:
                self._log.close()
                self._log = None

    def restart(self) -> None:
        self.stop()
        self.start()


def write_config(output: Path) -> str:
    """Create a private runtime config from future-run environment variables."""

    provider = os.environ["PHASE05_OPENVIKING_VLM_PROVIDER"]
    model = os.environ["PHASE05_OPENVIKING_VLM_MODEL"]
    api_base = os.environ["PHASE05_OPENVIKING_VLM_API_BASE"]
    api_key = os.environ["PHASE05_OPENVIKING_VLM_API_KEY"]
    workspace = os.environ["PHASE05_PROVIDER_STATE"]
    model_cache = os.environ["PHASE05_MODEL_CACHE"]
    payload = {
        "server": {"host": "127.0.0.1", "port": 1933, "auth_mode": "dev"},
        "storage": {
            "workspace": workspace,
            "agfs": {"backend": "local"},
            "vectordb": {"backend": "local"},
        },
        "embedding": {
            "max_concurrent": 1,
            "max_retries": 1,
            "dense": {
                "provider": "local",
                "model": "bge-small-zh-v1.5-f16",
                "dimension": 512,
                "input": "text",
                "cache_dir": str(Path(model_cache) / "embedding"),
            },
        },
        "vlm": {
            "provider": provider,
            "model": model,
            "api_base": api_base,
            "api_key": api_key,
            "temperature": 0.0,
            "max_concurrent": 1,
            "max_retries": 1,
            "thinking": False,
        },
        "memory": {"extraction_enabled": True},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.chmod(output, 0o600)
    (Path(model_cache) / "embedding").mkdir(parents=True, exist_ok=True)
    return hashlib.sha256(output.read_bytes()).hexdigest()


def _runtime_evidence(controller: OpenVikingServiceController) -> dict[str, Any]:
    reused = os.environ.get("PHASE05_PROVIDER_ENV_REUSED")
    if reused not in {"true", "false"}:
        raise RuntimeError("PHASE05_PROVIDER_ENV_REUSED must be true or false")
    config = Path(os.environ["PHASE05_OPENVIKING_CONFIG"])
    return {
        "provider_environment_reused": reused == "true",
        "openviking_version": os.environ["PHASE05_OPENVIKING_VERSION"],
        "llama_cpp_python_version": os.environ["PHASE05_LLAMA_CPP_PYTHON_VERSION"],
        "service_pid": controller.service_pid,
        "config_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
    }


def strict_liveness_passes(readiness: Mapping[str, Any]) -> bool:
    """Require both provider status and provider healthy evidence."""

    return (
        readiness.get("health_status") == "ok"
        and readiness.get("health_healthy") is True
    )


def _canary_result_fields(canary: Mapping[str, Any]) -> dict[str, Any]:
    """Promote completed-write evidence into stable result fields."""

    return {
        "canary_session_id": canary["session_id"],
        "canary_archive_uri": canary["archive_uri"],
        "canary_task_id": canary["task_id"],
        "canary_task_final_status": canary["task_final_status"],
        "canary_task_submitted_at": canary["task_submitted_at"],
        "canary_task_completed_at": canary["task_completed_at"],
        "canary_quiescence_seconds": canary["quiescence_seconds"],
        "canary_provider_memory_uri_count": canary["provider_memory_uri_count"],
        "canary_memory_diff_add_count": canary["memory_diff_add_count"],
        "canary_memory_diff_update_count": canary["memory_diff_update_count"],
        "canary_memory_diff_delete_count": canary["memory_diff_delete_count"],
        "canary_memory_diff_skipped_count": canary["memory_diff_skipped_count"],
    }


def validate_remote(output: Path) -> None:
    require_live_authorization()
    src_root = REPO_ROOT / "src"
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))
    from memlife.adapters.openviking import (
        OpenVikingMemoryAdapter,
        ServiceExitedBeforeReady as AdapterServiceExitedBeforeReady,
    )
    from memlife.models.memory import QueryCommand, WriteCommand
    from memlife.runner.provenance import ProvenanceTraceRunner
    from memlife.scenarios.canonical import canonical_scenarios

    controller = OpenVikingServiceController()
    result: dict[str, Any] = {
        "status": "IN_PROGRESS",
        "stage": "service_startup",
        "git_commit_tested": _git_commit_tested(),
        "model_calls": "provider-internal only; RQ3=0",
        "service_liveness": "NOT_ESTABLISHED",
        "service_readiness": "NOT_ESTABLISHED",
    }
    adapter = None
    try:
        adapter = OpenVikingMemoryAdapter.from_environment(
            restart_callback=controller.restart,
            process_is_running=controller.is_running,
            process_exit_code=controller.exit_code,
        )
        controller.start()
        result.update(_runtime_evidence(controller))
        result["stage"] = "service_readiness"
        adapter.wait_until_ready(timeout_seconds=180)
        readiness = adapter.readiness_diagnostics
        result.update(
            service_liveness=(
                "PASS"
                if strict_liveness_passes(readiness)
                else "NOT_ESTABLISHED"
            ),
            service_readiness="PASS",
            health_status=readiness.get("health_status"),
            health_healthy=readiness.get("health_healthy"),
            health_version=readiness.get("health_version"),
            readiness_status=readiness.get("readiness_status"),
            readiness_checks=_sanitize_runtime_value(readiness.get("readiness_checks")),
        )
        result["stage"] = "semantic_compatibility"
        namespace = "phase-05-live-probe"
        adapter.reset_namespace(namespace)
        source = adapter.write(
            WriteCommand(namespace=namespace, content="Phase 05 persistence canary is amber.")
        )
        canary = adapter.completed_write_metadata(source.memory_id)
        before = adapter.query(QueryCommand(namespace=namespace, query="persistence canary amber"))
        adapter.restart()
        result["service_pid_after_restart"] = controller.service_pid
        after = adapter.query(QueryCommand(namespace=namespace, query="persistence canary amber"))
        if not before or not after:
            raise RuntimeError("OpenViking persistence canary was not retrieved")
        scenarios = canonical_scenarios()
        traced_runs = [
            ProvenanceTraceRunner(adapter).run_scenario(
                scenario, experiment_id=f"phase05-{scenario.scenario_id}"
            )
            for scenario in scenarios
        ]
        result.update(
            status="PASS",
            stage="complete",
            source_event_id=source.memory_id,
            provider_memory_uris=source.metadata["openviking_provider_memory_uris"],
            persistence_before=len(before),
            persistence_after=len(after),
            canonical_results=[
                item.model_dump(mode="json")
                for run in traced_runs
                for item in run.benchmark_results
            ],
            provenance_traces=[
                run.trace.model_dump(mode="json") for run in traced_runs
            ],
        )
        result.update(_canary_result_fields(canary))
    except Exception as exc:
        readiness = getattr(adapter, "readiness_diagnostics", {}) if adapter is not None else {}
        exited = isinstance(exc, (ServiceExitedBeforeReady, AdapterServiceExitedBeforeReady))
        if exited:
            result["stage"] = "service_startup"
        result.update(
            status="BLOCKED",
            blocker_type="ServiceExitedBeforeReady" if exited else type(exc).__name__,
            blocker=_sanitize_runtime_text(exc),
            service_process_alive=controller.is_running(),
            service_exit_code=(
                getattr(exc, "exit_code", None)
                if exited
                else controller.exit_code()
            ),
            health_status=readiness.get("health_status"),
            health_healthy=readiness.get("health_healthy"),
            health_version=readiness.get("health_version"),
            readiness_status=readiness.get("readiness_status"),
            readiness_checks=_sanitize_runtime_value(readiness.get("readiness_checks")),
            readiness_elapsed_seconds=readiness.get("elapsed_seconds"),
            readiness_last_http_status=readiness.get("last_http_status"),
            readiness_request_error_class=readiness.get("request_error_class"),
        )
        if strict_liveness_passes(readiness):
            result["service_liveness"] = "PASS"
    finally:
        result.setdefault("service_process_alive", controller.is_running())
        result.setdefault("service_exit_code", controller.exit_code())
        try:
            controller.stop()
        except Exception as exc:
            result.update(
                status="BLOCKED",
                blocker_type="ServiceCleanupError",
                blocker=_sanitize_runtime_text(exc),
            )
        log_tail = controller.log_tail()
        if log_tail:
            result["service_log_tail"] = log_tail
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    config = subparsers.add_parser("write-config")
    config.add_argument("--output", type=Path, required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--output", type=Path, required=True)
    plan = subparsers.add_parser("dependency-plan")
    plan.add_argument("--report", type=Path, required=True)
    plan.add_argument("--output", type=Path, required=True)
    blocked = subparsers.add_parser("blocked-result")
    blocked.add_argument("--output", type=Path, required=True)
    blocked.add_argument("--stage", required=True)
    blocked.add_argument("--type", dest="blocker_type", required=True)
    blocked.add_argument("--message", default="")
    blocked.add_argument("--diagnostic-file", type=Path)
    args = parser.parse_args(argv)
    if args.command == "write-config":
        require_live_authorization()
        write_config(args.output)
    elif args.command == "validate":
        validate_remote(args.output)
    elif args.command == "dependency-plan":
        report = json.loads(args.report.read_text(encoding="utf-8"))
        result = validate_dependency_plan(report)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    else:
        write_blocked_result(
            args.output,
            stage=args.stage,
            blocker_type=args.blocker_type,
            message=args.message,
            diagnostic_file=args.diagnostic_file,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
