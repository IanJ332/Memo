"""Runtime storage selection and creation tests."""

import subprocess
from pathlib import Path

from memlife.config.paths import (
    DataRootConfig,
    DataRootMode,
    RUNTIME_DIRECTORIES,
    prepare_runtime,
    resolve_mountpoint,
    resolve_data_root,
)


def test_configured_relative_root_is_repository_relative(tmp_path: Path) -> None:
    config = resolve_data_root(
        environment={"MEMLIFE_DATA_ROOT": "custom-data"},
        repo_root=tmp_path,
        mount_resolver=lambda: tmp_path / "unused-volume",
    )
    assert config == DataRootConfig(
        root=(tmp_path / "custom-data").resolve(),
        mode=DataRootMode.CONFIGURED,
    )


def test_local_fallback_and_idempotent_preparation(tmp_path: Path) -> None:
    config = resolve_data_root(
        environment={},
        repo_root=tmp_path,
        mount_resolver=lambda: tmp_path / "missing-volume",
    )
    assert config.mode is DataRootMode.LOCAL
    assert config.root == tmp_path / "runtime"

    first = prepare_runtime(config)
    second = prepare_runtime(config)

    assert first == second
    assert tuple(path.name for path in first) == RUNTIME_DIRECTORIES
    assert all(path.is_dir() for path in first)


def test_jetstream_root_uses_dynamically_resolved_mount(tmp_path: Path) -> None:
    mount = tmp_path / "current-volume-name"
    mount.mkdir()

    config = resolve_data_root(
        environment={},
        repo_root=tmp_path,
        mount_resolver=lambda: mount,
        platform_name="posix",
    )

    assert config == DataRootConfig(mount / "memlife", DataRootMode.JETSTREAM)


def test_non_absolute_mount_is_rejected(tmp_path: Path) -> None:
    config = resolve_data_root(
        environment={},
        repo_root=tmp_path,
        mount_resolver=lambda: Path("relative-volume"),
        platform_name="posix",
    )
    assert config == DataRootConfig(tmp_path / "runtime", DataRootMode.LOCAL)


def test_mountpoint_parser_uses_findmnt_output(monkeypatch) -> None:
    observed = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        return subprocess.CompletedProcess(command, 0, "/media/volume/current\n", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert resolve_mountpoint("/dev/sdb") == Path("/media/volume/current")
    assert observed["command"] == ["findmnt", "-n", "-o", "TARGET", "/dev/sdb"]
