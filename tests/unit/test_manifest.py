"""Environment manifest behavior and secret safeguards."""

import json
from pathlib import Path

import pytest

from memlife.config.paths import DataRootConfig, DataRootMode
from memlife.runner.manifest import build_manifest, hash_configuration, write_manifest


def test_configuration_hash_is_stable_and_rejects_sensitive_keys() -> None:
    left = hash_configuration({"provider": "reference", "limit": 10})
    right = hash_configuration({"limit": 10, "provider": "reference"})
    assert left == right

    with pytest.raises(ValueError, match="sensitive"):
        hash_configuration({"api_key": "must-not-be-hashed"})


def test_manifest_records_real_environment_without_config_values(tmp_path: Path) -> None:
    data_root = DataRootConfig(tmp_path / "runtime", DataRootMode.LOCAL)
    manifest = build_manifest(
        phase="phase-01",
        data_root=data_root,
        repo_root=tmp_path,
        configuration={"provider": "reference"},
        package_names=("pydantic", "package-that-does-not-exist"),
    )
    destination = tmp_path / "manifest.json"
    write_manifest(manifest, destination)
    payload = json.loads(destination.read_text(encoding="utf-8"))

    assert payload["phase"] == "phase-01"
    assert payload["git_commit"] is None
    assert payload["package_versions"]["pydantic"]
    assert payload["package_versions"]["package-that-does-not-exist"] is None
    assert "reference" not in destination.read_text(encoding="utf-8")


def test_manifest_can_record_non_secret_provider_details(tmp_path: Path) -> None:
    data_root = DataRootConfig(tmp_path / "runtime", DataRootMode.LOCAL)
    details = {"provider": "mem0", "infer": False}
    manifest = build_manifest(
        phase="02A",
        data_root=data_root,
        repo_root=tmp_path,
        configuration=details,
        details=details,
    )
    assert manifest.details == details

    with pytest.raises(ValueError, match="sensitive"):
        build_manifest(
            phase="02A",
            data_root=data_root,
            repo_root=tmp_path,
            details={"api_token": "must-not-be-recorded"},
        )
