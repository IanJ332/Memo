"""Safe, cross-platform runtime storage selection for MemLife."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Mapping

DATA_ROOT_ENV = "MEMLIFE_DATA_ROOT"
JETSTREAM_DEVICE = "/dev/sdb"
RUNTIME_DIRECTORIES = (
    "providers",
    "datasets",
    "model_cache",
    "runs",
    "logs",
    "artifacts",
)


class DataRootMode(str, Enum):
    """How the runtime root was selected."""

    CONFIGURED = "configured"
    JETSTREAM = "jetstream"
    LOCAL = "local"


@dataclass(frozen=True)
class DataRootConfig:
    """Resolved data root and the selection mode used for it."""

    root: Path
    mode: DataRootMode


def repository_root() -> Path:
    """Return the repository root based on this module's source location."""

    return Path(__file__).resolve().parents[3]


def resolve_mountpoint(device: str = JETSTREAM_DEVICE) -> Path | None:
    """Return the current mountpoint for a block device, if it is mounted."""

    result = subprocess.run(
        ["findmnt", "-n", "-o", "TARGET", device],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    if not value or not value.startswith("/"):
        return None
    return Path(value)


def resolve_data_root(
    environment: Mapping[str, str] | None = None,
    repo_root: Path | None = None,
    mount_resolver: Callable[[], Path | None] = resolve_mountpoint,
    platform_name: str | None = None,
) -> DataRootConfig:
    """Resolve storage without creating or modifying any filesystem objects.

    An explicit ``MEMLIFE_DATA_ROOT`` wins. On POSIX systems, an existing
    the mounted ``/dev/sdb`` persistent volume selects ``<mount>/memlife``.
    Every other environment safely falls back to ``<repository>/runtime``.
    """

    env = os.environ if environment is None else environment
    root = repository_root() if repo_root is None else Path(repo_root).resolve()
    configured = env.get(DATA_ROOT_ENV, "").strip()

    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            candidate = root / candidate
        return DataRootConfig(candidate.resolve(), DataRootMode.CONFIGURED)

    current_platform = os.name if platform_name is None else platform_name
    if current_platform == "posix":
        jetstream_volume = mount_resolver()
        if jetstream_volume is not None and jetstream_volume.is_dir():
            return DataRootConfig(jetstream_volume / "memlife", DataRootMode.JETSTREAM)

    return DataRootConfig(root / "runtime", DataRootMode.LOCAL)


def prepare_runtime(config: DataRootConfig | None = None) -> tuple[Path, ...]:
    """Idempotently create the non-destructive MemLife runtime layout."""

    selected = resolve_data_root() if config is None else config
    selected.root.mkdir(parents=True, exist_ok=True)
    paths = tuple(selected.root / name for name in RUNTIME_DIRECTORIES)
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
    return paths
