from __future__ import annotations

from pathlib import Path

import pytest

from scripts.jetstream.phase04_runtime import EnvironmentCheck
from scripts.jetstream.phase04_runtime import HindsightServiceController
from scripts.jetstream.phase04_runtime import Phase04RuntimePaths
from scripts.jetstream.phase04_runtime import validate_environment_checks


REPO = Path(__file__).resolve().parents[2]
REMOTE_SCRIPT = REPO / "scripts" / "jetstream" / "phase04_remote.sh"


class FakeProcess:
    def __init__(self, pid: int) -> None:
        self.pid = pid
        self.returncode: int | None = None
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = 0

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9

    def wait(self, timeout: int) -> int:
        assert timeout in {15, 45}
        assert self.returncode is not None
        return self.returncode


def test_install_and_launch_commands_preserve_environment_ownership() -> None:
    paths = Phase04RuntimePaths.derive(
        repo="/home/exouser/Memo",
        data_root="/media/volume/live/memlife",
    )
    assert str(paths.harness_python) == "/home/exouser/Memo/.venv/bin/python"
    assert str(paths.hindsight_venv) == (
        "/media/volume/live/memlife/venvs/hindsight-0.10.1"
    )
    assert paths.harness_install_command()[0] == str(paths.harness_python)
    assert paths.harness_install_command()[-1].endswith("requirements/core.txt")
    assert paths.hindsight_install_command()[0] == str(paths.hindsight_python)
    assert paths.hindsight_install_command()[-1].endswith(
        "requirements/providers/hindsight.txt"
    )
    assert paths.service_command() == (str(paths.hindsight_service),)
    assert paths.benchmark_command("benchmark.py")[0] == str(paths.harness_python)
    assert paths.run_root.is_relative_to(paths.data_root)
    assert not paths.run_root.is_relative_to(paths.repo)


def test_remote_script_never_installs_hindsight_into_harness() -> None:
    source = REMOTE_SCRIPT.read_text(encoding="utf-8")
    assert 'HARNESS_PYTHON="$REPO/.venv/bin/python"' in source
    assert 'HINDSIGHT_VENV="$MEMLIFE_DATA_ROOT/venvs/hindsight-0.10.1"' in source
    assert '"$HARNESS_PYTHON" -m pip install -r "$REPO/requirements/core.txt"' in source
    assert (
        '"$HINDSIGHT_PYTHON" -m pip install --no-cache-dir '
        '-r "$REPO/requirements/providers/hindsight.txt"'
    ) in source
    assert (
        '"$HARNESS_PYTHON" scripts/jetstream/phase04_hindsight_validate.py'
        in source
    )
    assert '"$HARNESS_PYTHON" -m pip install --no-cache-dir' not in source
    assert "/.venv/bin/hindsight-api" not in source
    assert "pip install --no-deps" not in source


def test_cross_environment_protobuf_difference_is_valid() -> None:
    validate_environment_checks(
        EnvironmentCheck("harness", True, "6.33.5"),
        EnvironmentCheck("hindsight", True, "7.36.2"),
    )


@pytest.mark.parametrize("failed_environment", ["harness", "hindsight"])
def test_intra_environment_pip_failure_is_rejected(failed_environment: str) -> None:
    checks = [
        EnvironmentCheck("harness", failed_environment != "harness", "6.33.5"),
        EnvironmentCheck("hindsight", failed_environment != "hindsight", "7.36.2"),
    ]
    with pytest.raises(RuntimeError, match=failed_environment):
        validate_environment_checks(*checks)


def test_restart_and_cleanup_manage_only_run_owned_service(tmp_path: Path) -> None:
    service = tmp_path / "venv" / "bin" / "hindsight-api"
    service.parent.mkdir(parents=True)
    service.write_text("service", encoding="utf-8")
    run_root = tmp_path / "persistent-volume" / "runs" / "phase-04-hindsight"
    calls: list[tuple[list[str], dict[str, object]]] = []
    processes: list[FakeProcess] = []

    def fake_popen(command: list[str], **kwargs: object) -> FakeProcess:
        process = FakeProcess(1000 + len(processes))
        calls.append((command, kwargs))
        processes.append(process)
        return process

    controller = HindsightServiceController(
        service_executable=service,
        repo=tmp_path,
        run_root=run_root,
        environment={"BOUNDARY": "http"},
        popen=fake_popen,
    )
    controller.start()
    assert controller.pid_path.read_text(encoding="ascii") == "1000\n"
    controller.restart()
    assert processes[0].terminated is True
    assert controller.pid_path.read_text(encoding="ascii") == "1001\n"
    controller.stop()

    assert processes[1].terminated is True
    assert not controller.pid_path.exists()
    assert controller.hindsight_service_started_by_this_run is False
    assert [command for command, _ in calls] == [[str(service)], [str(service)]]
    assert all(kwargs["cwd"] == tmp_path for _, kwargs in calls)


def test_existing_pid_file_fails_closed_without_killing_process(tmp_path: Path) -> None:
    service = tmp_path / "venv" / "bin" / "hindsight-api"
    service.parent.mkdir(parents=True)
    service.write_text("service", encoding="utf-8")
    run_root = tmp_path / "runtime"
    run_root.mkdir()
    pid_path = run_root / "hindsight-service.pid"
    pid_path.write_text("4242\n", encoding="ascii")

    controller = HindsightServiceController(
        service_executable=service,
        repo=tmp_path,
        run_root=run_root,
        popen=lambda *args, **kwargs: pytest.fail("must not launch a second service"),
    )
    with pytest.raises(RuntimeError, match="refusing to replace"):
        controller.start()
    controller.stop()
    assert pid_path.read_text(encoding="ascii") == "4242\n"
