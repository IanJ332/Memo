"""Phase 04 isolated-runtime planning, service control, and fingerprints."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence

HINDSIGHT_VERSION = "0.10.1"


@dataclass(frozen=True)
class Phase04RuntimePaths:
    """The two Python ownership domains and their persistent runtime paths."""

    repo: PurePosixPath
    data_root: PurePosixPath
    harness_python: PurePosixPath
    hindsight_venv: PurePosixPath
    hindsight_python: PurePosixPath
    hindsight_service: PurePosixPath
    run_root: PurePosixPath
    provider_root: PurePosixPath
    model_cache: PurePosixPath

    @classmethod
    def derive(
        cls, repo: str = "/home/exouser/Memo", data_root: str = "/volume/memlife"
    ) -> "Phase04RuntimePaths":
        repo_path = PurePosixPath(repo)
        data_path = PurePosixPath(data_root)
        if data_path == repo_path or repo_path in data_path.parents:
            raise ValueError("MEMLIFE_DATA_ROOT must remain outside the repository")
        hindsight_venv = data_path / "venvs" / f"hindsight-{HINDSIGHT_VERSION}"
        return cls(
            repo=repo_path,
            data_root=data_path,
            harness_python=repo_path / ".venv" / "bin" / "python",
            hindsight_venv=hindsight_venv,
            hindsight_python=hindsight_venv / "bin" / "python",
            hindsight_service=hindsight_venv / "bin" / "hindsight-api",
            run_root=data_path / "runs" / "phase-04-hindsight",
            provider_root=data_path / "providers" / "hindsight",
            model_cache=data_path / "model_cache" / "hindsight",
        )

    def harness_install_command(self) -> tuple[str, ...]:
        return (
            str(self.harness_python),
            "-m",
            "pip",
            "install",
            "-r",
            str(self.repo / "requirements" / "core.txt"),
        )

    def hindsight_install_command(self) -> tuple[str, ...]:
        return (
            str(self.hindsight_python),
            "-m",
            "pip",
            "install",
            "-r",
            str(self.repo / "requirements" / "providers" / "hindsight.txt"),
        )

    def benchmark_command(self, *arguments: str) -> tuple[str, ...]:
        return (str(self.harness_python), *arguments)

    def service_command(self) -> tuple[str, ...]:
        return (str(self.hindsight_service),)


@dataclass(frozen=True)
class EnvironmentCheck:
    """A pip check belongs to one environment, never to a cross-venv merge."""

    environment: str
    pip_check_ok: bool
    protobuf_version: str


def validate_environment_checks(*checks: EnvironmentCheck) -> None:
    """Require internal consistency without comparing cross-venv protobuf pins."""

    failed = [check.environment for check in checks if not check.pip_check_ok]
    if failed:
        raise RuntimeError(
            "pip check failed inside environment(s): " + ", ".join(failed)
        )


def _distribution_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError as exc:
        raise RuntimeError(f"required distribution is missing: {name}") from exc


def provider_environment_fingerprint() -> dict[str, str]:
    """Return a non-secret, stable fingerprint for the active provider venv."""

    freeze = subprocess.run(
        [sys.executable, "-m", "pip", "freeze", "--all"],
        check=True,
        capture_output=True,
        text=True,
        timeout=300,
    ).stdout.splitlines()
    normalized = "\n".join(
        sorted((line.strip() for line in freeze if line.strip()), key=str.casefold)
    ) + "\n"
    return {
        "python_version": sys.version.split()[0],
        "pip_version": _distribution_version("pip"),
        "hindsight_api_slim_version": _distribution_version("hindsight-api-slim"),
        "protobuf_version": _distribution_version("protobuf"),
        "normalized_pip_freeze_sha256": hashlib.sha256(
            normalized.encode("utf-8")
        ).hexdigest(),
    }


class HindsightServiceController:
    """Own exactly one Hindsight process and its PID/log files for this run."""

    def __init__(
        self,
        *,
        service_executable: Path,
        repo: Path,
        run_root: Path,
        environment: Mapping[str, str] | None = None,
        popen: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
    ) -> None:
        self.service_executable = service_executable
        self.repo = repo
        self.run_root = run_root
        self.log_path = run_root / "hindsight-service.log"
        self.pid_path = run_root / "hindsight-service.pid"
        self.environment = dict(environment or os.environ)
        self._popen = popen
        self.process: subprocess.Popen[bytes] | None = None
        self._log: Any | None = None
        self.hindsight_service_started_by_this_run = False

    def start(self) -> None:
        if self.process is not None and self.process.poll() is None:
            raise RuntimeError("Hindsight service is already owned by this run")
        if self.pid_path.exists():
            raise RuntimeError(
                f"refusing to replace existing Hindsight PID file: {self.pid_path}"
            )
        if not self.service_executable.is_file():
            raise RuntimeError(
                "Hindsight service executable is absent from the provider venv: "
                f"{self.service_executable}"
            )
        self.run_root.mkdir(parents=True, exist_ok=True)
        self._log = self.log_path.open("ab")
        try:
            self.process = self._popen(
                [str(self.service_executable)],
                cwd=self.repo,
                env=self.environment.copy(),
                stdout=self._log,
                stderr=subprocess.STDOUT,
            )
            if self.process.poll() is not None:
                raise RuntimeError("Hindsight service exited during startup")
            self.pid_path.write_text(f"{self.process.pid}\n", encoding="ascii")
            self.hindsight_service_started_by_this_run = True
        except Exception:
            if self.process is not None and self.process.poll() is None:
                self.process.terminate()
                self.process.wait(timeout=45)
            if self.pid_path.exists():
                self.pid_path.unlink()
            self.process = None
            self._log.close()
            self._log = None
            raise

    def stop(self) -> None:
        process = self.process
        try:
            if self.hindsight_service_started_by_this_run and process is not None:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=45)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=15)
                if self.pid_path.exists():
                    recorded_pid = self.pid_path.read_text(encoding="ascii").strip()
                    if recorded_pid != str(process.pid):
                        raise RuntimeError(
                            "Hindsight PID ownership changed; refusing broad cleanup"
                        )
                    self.pid_path.unlink()
        finally:
            self.process = None
            self.hindsight_service_started_by_this_run = False
            if self._log is not None:
                self._log.close()
                self._log = None

    def restart(self) -> None:
        """Restart only the service process; preserve venv, database, and caches."""

        self.stop()
        self.start()


def start_hindsight_service(controller: HindsightServiceController) -> None:
    controller.start()


def wait_hindsight_ready(adapter: Any, *, timeout_seconds: float) -> None:
    adapter.wait_until_ready(timeout_seconds=timeout_seconds)


def restart_hindsight_service(controller: HindsightServiceController) -> None:
    controller.restart()


def stop_hindsight_service(controller: HindsightServiceController) -> None:
    controller.stop()


def _write_fingerprint(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(provider_environment_fingerprint(), indent=2) + "\n",
        encoding="utf-8",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    fingerprint = subparsers.add_parser("fingerprint")
    fingerprint.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "fingerprint":
        _write_fingerprint(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
