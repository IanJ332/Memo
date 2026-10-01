#!/usr/bin/env python3
"""Select and verify the approved persistent Phase 06B harness environment."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

DEFAULT_HARNESS_NAME = "memlife-harness-phase04"


class HarnessSelectionError(RuntimeError):
    """The requested Phase 06B harness is absent or outside the approved root."""


@dataclass(frozen=True)
class HarnessSelection:
    venv: Path
    python: Path
    source: str


def _probe_runtime_prefix(python: Path) -> Path:
    result = subprocess.run(
        [
            str(python),
            "-c",
            "import os,sys; print(os.path.realpath(sys.prefix))",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode:
        raise HarnessSelectionError("approved harness interpreter probe failed")
    prefix = result.stdout.strip()
    if not prefix:
        raise HarnessSelectionError("approved harness interpreter returned no prefix")
    return Path(prefix)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def select_approved_harness(
    *,
    repo: Path,
    data_root: Path,
    explicit_venv: Path | None = None,
    prefix_probe: Callable[[Path], Path] = _probe_runtime_prefix,
) -> HarnessSelection:
    """Select an existing venv under the persistent MemLife venv root."""

    repo = repo.resolve()
    data_root = data_root.resolve()
    if data_root == repo or _is_relative_to(data_root, repo):
        raise HarnessSelectionError("MEMLIFE_DATA_ROOT must remain outside the repository")

    approved_root = (data_root / "venvs").resolve()
    legacy_venv = (repo / ".venv").resolve()
    source = "explicit" if explicit_venv is not None else "persistent-default"
    candidate = (
        explicit_venv
        if explicit_venv is not None
        else approved_root / DEFAULT_HARNESS_NAME
    )
    if not candidate.is_absolute():
        raise HarnessSelectionError("Phase 06B harness path must be absolute")
    candidate = candidate.resolve()

    if candidate == legacy_venv or _is_relative_to(candidate, legacy_venv):
        raise HarnessSelectionError("repository .venv is forbidden for Phase 06B")
    if not _is_relative_to(candidate, approved_root):
        raise HarnessSelectionError(
            "Phase 06B harness must be inside the persistent MemLife venv root"
        )
    if not candidate.is_dir():
        raise HarnessSelectionError("approved persistent Phase 06B harness is missing")
    if not (candidate / "pyvenv.cfg").is_file():
        raise HarnessSelectionError("approved Phase 06B harness lacks pyvenv.cfg")

    python = candidate / "bin" / "python"
    if not python.is_file() or not os.access(python, os.X_OK):
        raise HarnessSelectionError("approved Phase 06B harness interpreter is unavailable")

    runtime_prefix = prefix_probe(python).resolve()
    if runtime_prefix != candidate:
        raise HarnessSelectionError(
            "approved Phase 06B harness interpreter has an unexpected runtime prefix"
        )
    return HarnessSelection(venv=candidate, python=python, source=source)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--explicit-venv", type=Path)
    args = parser.parse_args(argv)
    try:
        selection = select_approved_harness(
            repo=args.repo,
            data_root=args.data_root,
            explicit_venv=args.explicit_venv,
        )
    except HarnessSelectionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(selection.venv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
