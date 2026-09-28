"""Reproducibility manifest generation for MemLife experiment phases."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict

from memlife.config.paths import DataRootConfig

DEFAULT_PACKAGES = ("openai", "psutil", "pydantic", "pytest")
SENSITIVE_KEY_PARTS = ("api_key", "credential", "password", "secret", "token")


class EnvironmentManifest(BaseModel):
    """Non-secret environment facts needed to reproduce a phase run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    phase: str
    git_commit: str | None
    python_version: str
    platform: str
    timestamp_utc: datetime
    package_versions: dict[str, str | None]
    data_root_mode: str
    config_hash_sha256: str | None


def _git_commit(repo_root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    commit = completed.stdout.strip()
    return commit or None


def _contains_sensitive_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = str(key).casefold()
            if any(part in normalized for part in SENSITIVE_KEY_PARTS):
                return True
            if _contains_sensitive_key(nested):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_sensitive_key(item) for item in value)
    return False


def hash_configuration(configuration: Mapping[str, Any] | None) -> str | None:
    """Hash non-secret configuration without recording its values."""

    if configuration is None:
        return None
    if _contains_sensitive_key(configuration):
        raise ValueError("configuration contains a potentially sensitive key")
    canonical = json.dumps(
        configuration,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _package_versions(package_names: Sequence[str]) -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for name in package_names:
        try:
            versions[name] = version(name)
        except PackageNotFoundError:
            versions[name] = None
    return versions


def build_manifest(
    phase: str,
    data_root: DataRootConfig,
    repo_root: Path,
    configuration: Mapping[str, Any] | None = None,
    package_names: Sequence[str] = DEFAULT_PACKAGES,
) -> EnvironmentManifest:
    """Capture current environment facts; missing Git/package data stays null."""

    return EnvironmentManifest(
        phase=phase,
        git_commit=_git_commit(repo_root),
        python_version=platform.python_version(),
        platform=platform.platform(),
        timestamp_utc=datetime.now(timezone.utc),
        package_versions=_package_versions(package_names),
        data_root_mode=data_root.mode.value,
        config_hash_sha256=hash_configuration(configuration),
    )


def write_manifest(manifest: EnvironmentManifest, destination: Path) -> None:
    """Write a manifest as stable, human-readable JSON."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        manifest.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
