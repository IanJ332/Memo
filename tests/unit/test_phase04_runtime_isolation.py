from __future__ import annotations

from pathlib import Path

import pytest

from scripts.jetstream import phase04_runtime
from scripts.jetstream.phase04_runtime import EnvironmentCheck
from scripts.jetstream.phase04_runtime import HindsightServiceController
from scripts.jetstream.phase04_runtime import Phase04RuntimePaths
from scripts.jetstream.phase04_runtime import harness_environment_fingerprint
from scripts.jetstream.phase04_runtime import validate_environment_checks
from scripts.jetstream.phase04_runtime import validate_harness_fingerprint


REPO = Path(__file__).resolve().parents[2]
REMOTE_SCRIPT = REPO / "scripts" / "jetstream" / "phase04_remote.sh"
CORE_REQUIREMENTS = REPO / "requirements" / "core.txt"
MEM0_REQUIREMENTS = REPO / "requirements" / "providers" / "mem0.txt"
INFRA_LLM_REQUIREMENTS = REPO / "requirements" / "infra" / "jetstream-llm.txt"


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
    assert str(paths.legacy_harness_python) == "/home/exouser/Memo/.venv/bin/python"
    assert str(paths.harness_venv) == (
        "/media/volume/live/memlife/venvs/memlife-harness-phase04"
    )
    assert str(paths.harness_python) == (
        "/media/volume/live/memlife/venvs/memlife-harness-phase04/bin/python"
    )
    assert str(paths.hindsight_venv) == (
        "/media/volume/live/memlife/venvs/hindsight-0.10.1"
    )
    assert paths.harness_install_command()[0] == str(paths.harness_python)
    harness_install = " ".join(paths.harness_install_command())
    assert "requirements/core.txt" in harness_install
    assert "requirements/providers/mem0.txt" in harness_install
    assert "requirements/providers/hindsight.txt" not in harness_install
    assert paths.hindsight_install_command()[0] == str(paths.hindsight_python)
    assert paths.hindsight_install_command()[-1].endswith(
        "requirements/providers/hindsight.txt"
    )
    assert paths.service_command() == (str(paths.hindsight_service),)
    assert paths.benchmark_command("benchmark.py")[0] == str(paths.harness_python)
    assert paths.run_root.is_relative_to(paths.data_root)
    assert not paths.run_root.is_relative_to(paths.repo)
    assert paths.harness_venv != paths.hindsight_venv
    assert paths.harness_python != paths.legacy_harness_python


def test_remote_script_builds_and_gates_clean_harness_before_hindsight() -> None:
    source = REMOTE_SCRIPT.read_text(encoding="utf-8")
    assert 'LEGACY_HARNESS_VENV="$REPO/.venv"' in source
    assert 'CLEAN_HARNESS_VENV="$MEMLIFE_DATA_ROOT/venvs/memlife-harness-phase04"' in source
    assert 'HARNESS_PYTHON="$CLEAN_HARNESS_VENV/bin/python"' in source
    assert 'HINDSIGHT_VENV="$MEMLIFE_DATA_ROOT/venvs/hindsight-0.10.1"' in source
    assert '-r "$REPO/requirements/core.txt"' in source
    assert '-r "$REPO/requirements/providers/mem0.txt"' in source
    assert (
        '"$HINDSIGHT_PYTHON" -m pip install --no-cache-dir '
        '-r "$REPO/requirements/providers/hindsight.txt"'
    ) in source
    assert (
        '"$HARNESS_PYTHON" scripts/jetstream/phase04_hindsight_validate.py'
        in source
    )
    assert "/.venv/bin/hindsight-api" not in source
    assert "pip install --no-deps" not in source

    pip_check = source.index("capture_harness_health before-hindsight")
    mem0_gate = source.index("scripts/jetstream/phase04_mem0_regression.py")
    hindsight_setup = source.index(
        "# Hindsight setup begins only after the clean harness and Mem0 regression pass."
    )
    hindsight_creation = source.index('if [ ! -e "$HINDSIGHT_VENV" ]')
    assert pip_check < mem0_gate < hindsight_setup < hindsight_creation


def test_dependency_ownership_keeps_openai_pin_out_of_core() -> None:
    core = CORE_REQUIREMENTS.read_text(encoding="utf-8").casefold()
    mem0 = MEM0_REQUIREMENTS.read_text(encoding="utf-8").casefold()
    infrastructure = INFRA_LLM_REQUIREMENTS.read_text(encoding="utf-8").casefold()
    remote = REMOTE_SCRIPT.read_text(encoding="utf-8").casefold()

    assert "openai" not in core
    assert "openai==3.13.0" in infrastructure
    assert "protobuf==" not in core + mem0 + remote
    assert "openai==" not in core + mem0 + remote


def test_clean_harness_fingerprint_records_required_dependency_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    versions = {
        "mem0ai": "2.2.1",
        "protobuf": "6.33.5",
        "openai": "2.29.0",
        "litellm": None,
        "sentence-transformers": "6.1.0",
        "torch": "2.7.1+cpu",
        "qdrant-client": "1.19.1",
    }
    monkeypatch.setattr(
        phase04_runtime,
        "_optional_distribution_version",
        lambda name: versions[name],
    )
    monkeypatch.setattr(phase04_runtime, "_distribution_version", lambda name: "26.0.1")
    monkeypatch.setattr(phase04_runtime, "_normalized_freeze_sha256", lambda: "a" * 64)

    fingerprint = harness_environment_fingerprint()
    assert fingerprint["mem0ai_version"] == "2.2.1"
    assert fingerprint["protobuf_version"] == "6.33.5"
    assert fingerprint["openai_version"] == "2.29.0"
    assert fingerprint["litellm_version"] is None
    assert fingerprint["sentence_transformers_version"] == "6.1.0"
    assert fingerprint["torch_version"] == "2.7.1+cpu"
    assert fingerprint["qdrant_client_version"] == "1.19.1"
    assert fingerprint["normalized_pip_freeze_sha256"] == "a" * 64


def test_changed_clean_harness_fingerprint_fails_closed() -> None:
    expected = {"mem0ai_version": "2.2.1", "normalized_pip_freeze_sha256": "a"}
    validate_harness_fingerprint(expected, expected.copy())
    with pytest.raises(RuntimeError, match="refusing automatic rebuild"):
        validate_harness_fingerprint(
            expected,
            {"mem0ai_version": "2.2.1", "normalized_pip_freeze_sha256": "b"},
        )


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
