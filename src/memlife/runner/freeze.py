"""Checkout-independent materialization of the frozen experiment protocol."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FREEZE_GIT_PATH = "experiments/freeze/experiment-freeze-v1.json"
FREEZE_SHA256 = "0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b"


@dataclass(frozen=True)
class FreezeMaterialization:
    """A freeze loaded from Git and rendered into its authoritative bytes."""

    payload: dict[str, Any]
    git_blob: bytes
    canonical_bytes: bytes
    sha256: str


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        separators=(",", ": "),
    ) + "\n"


def canonical_freeze_bytes(git_blob: bytes) -> tuple[dict[str, Any], bytes]:
    """Validate a canonical Git blob and materialize Freeze v1 CRLF bytes."""

    try:
        source_text = git_blob.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("freeze Git blob is not UTF-8") from exc
    if source_text.startswith("\ufeff"):
        raise ValueError("freeze Git blob must not contain a UTF-8 BOM")
    try:
        payload = json.loads(source_text)
    except json.JSONDecodeError as exc:
        raise ValueError("freeze Git blob is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("freeze Git blob must contain a JSON object")

    canonical_lf = canonical_json(payload)
    normalized_source = source_text.replace("\r\n", "\n")
    if "\r" in normalized_source or normalized_source != canonical_lf:
        raise ValueError("freeze Git blob is not canonical sorted UTF-8 JSON")
    canonical_bytes = canonical_lf.replace("\n", "\r\n").encode("utf-8")
    return payload, canonical_bytes


def _repository_root(freeze_path: Path) -> Path:
    probe = freeze_path.resolve().parent
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=probe,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError(f"freeze path is not in a Git repository: {detail}")
    return Path(result.stdout.strip()).resolve()


def load_freeze_from_git(
    freeze_path: Path,
    *,
    revision: str = "HEAD",
) -> FreezeMaterialization:
    """Load Freeze v1 from ``git show``, never from working-tree bytes."""

    repo_root = _repository_root(freeze_path)
    try:
        git_path = freeze_path.resolve().relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise ValueError("freeze path is outside its Git repository") from exc
    if git_path != FREEZE_GIT_PATH:
        raise ValueError(
            f"freeze must use the repository path {FREEZE_GIT_PATH!r}, got {git_path!r}"
        )
    result = subprocess.run(
        ["git", "show", f"{revision}:{FREEZE_GIT_PATH}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"unable to read freeze Git blob: {detail}")
    payload, canonical_bytes = canonical_freeze_bytes(result.stdout)
    return FreezeMaterialization(
        payload=payload,
        git_blob=result.stdout,
        canonical_bytes=canonical_bytes,
        sha256=hashlib.sha256(canonical_bytes).hexdigest(),
    )
