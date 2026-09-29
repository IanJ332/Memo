"""Guarded Phase 05 OpenViking orchestrator and remote validator.

Phase 05A only prepares this module.  The local-only preparation never invokes
``run_remote_validation`` or the ``validate`` command.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from memlife.adapters.openviking import OpenVikingMemoryAdapter
from memlife.models.memory import QueryCommand, WriteCommand
from memlife.runner.provenance import ProvenanceTraceRunner
from memlife.scenarios.canonical import canonical_scenarios

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
    if payload.get("git_commit_tested") != expected_commit:
        raise RuntimeError("remote result commit did not match the local branch commit")
    payload["remote_sync"] = sync.stdout.strip().splitlines()
    payload["live_mount_probe"] = facts.get("resolved_volume_mount")
    LOCAL_RESULT.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_RESULT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


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
        if self.process.poll() is not None:
            raise RuntimeError("OpenViking exited during startup")
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


def write_config(output: Path) -> None:
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
        "vlm": {
            "provider": provider,
            "model": model,
            "api_base": api_base,
            "api_key": api_key,
        },
        "memory": {"extraction_enabled": True},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.chmod(output, 0o600)
    Path(model_cache).mkdir(parents=True, exist_ok=True)


def validate_remote(output: Path) -> None:
    require_live_authorization()
    controller = OpenVikingServiceController()
    adapter = OpenVikingMemoryAdapter.from_environment(
        restart_callback=controller.restart
    )
    result: dict[str, Any] = {
        "status": "IN_PROGRESS",
        "git_commit_tested": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "model_calls": "provider-internal only; RQ3=0",
    }
    try:
        controller.start()
        adapter.wait_until_ready(timeout_seconds=180)
        namespace = "phase-05-live-probe"
        adapter.reset_namespace(namespace)
        source = adapter.write(
            WriteCommand(namespace=namespace, content="Phase 05 persistence canary is amber.")
        )
        before = adapter.query(QueryCommand(namespace=namespace, query="persistence canary amber"))
        adapter.restart()
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
    except Exception as exc:
        result.update(status="FAIL", failure_type=type(exc).__name__)
        raise
    finally:
        controller.stop()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    config = subparsers.add_parser("write-config")
    config.add_argument("--output", type=Path, required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "write-config":
        require_live_authorization()
        write_config(args.output)
    else:
        validate_remote(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
