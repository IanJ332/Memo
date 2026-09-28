"""Runtime storage selection and creation tests."""

from pathlib import Path

from memlife.config.paths import (
    DataRootConfig,
    DataRootMode,
    RUNTIME_DIRECTORIES,
    prepare_runtime,
    resolve_data_root,
)


def test_configured_relative_root_is_repository_relative(tmp_path: Path) -> None:
    config = resolve_data_root(
        environment={"MEMLIFE_DATA_ROOT": "custom-data"},
        repo_root=tmp_path,
        jetstream_volume=tmp_path / "unused-volume",
    )
    assert config == DataRootConfig(
        root=(tmp_path / "custom-data").resolve(),
        mode=DataRootMode.CONFIGURED,
    )


def test_local_fallback_and_idempotent_preparation(tmp_path: Path) -> None:
    config = resolve_data_root(
        environment={},
        repo_root=tmp_path,
        jetstream_volume=tmp_path / "missing-volume",
    )
    assert config.mode is DataRootMode.LOCAL
    assert config.root == tmp_path / "runtime"

    first = prepare_runtime(config)
    second = prepare_runtime(config)

    assert first == second
    assert tuple(path.name for path in first) == RUNTIME_DIRECTORIES
    assert all(path.is_dir() for path in first)
