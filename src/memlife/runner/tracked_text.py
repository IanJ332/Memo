"""Checkout-independent validation for tracked canonical text artifacts."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TrackedTextMaterialization:
    """A tracked text blob and its canonical CRLF representation."""

    repository_root: Path
    git_path: str
    git_blob: bytes
    canonical_bytes: bytes
    sha256: str


@dataclass(frozen=True)
class TrackedJsonlMaterialization(TrackedTextMaterialization):
    """A canonical tracked JSONL artifact with validated logical rows."""

    rows: tuple[dict[str, Any], ...]


def repository_root(path: Path) -> Path:
    """Resolve the containing Git repository without reading artifact bytes."""

    probe = path.resolve().parent
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=probe,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError(f"tracked path is not in a Git repository: {detail}")
    return Path(result.stdout.strip()).resolve()


def read_git_blob(path: Path, *, revision: str = "HEAD") -> tuple[Path, str, bytes]:
    """Read ``path`` from a Git revision, never from the working tree."""

    repo_root = repository_root(path)
    try:
        git_path = path.resolve().relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise ValueError("tracked path is outside its Git repository") from exc
    result = subprocess.run(
        ["git", "show", f"{revision}:{git_path}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"unable to read tracked Git blob {git_path!r}: {detail}")
    return repo_root, git_path, result.stdout


def canonical_crlf_bytes(source: bytes) -> bytes:
    """Normalize only text line endings and materialize canonical CRLF bytes."""

    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("tracked text artifact is not UTF-8") from exc
    if text.startswith("\ufeff"):
        raise ValueError("tracked text artifact must not contain a UTF-8 BOM")
    normalized_lf = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized_lf.replace("\n", "\r\n").encode("utf-8")


def materialize_tracked_text(
    path: Path, *, revision: str = "HEAD"
) -> TrackedTextMaterialization:
    """Materialize one tracked UTF-8 text artifact from repository source."""

    repo_root, git_path, git_blob = read_git_blob(path, revision=revision)
    canonical_bytes = canonical_crlf_bytes(git_blob)
    return TrackedTextMaterialization(
        repository_root=repo_root,
        git_path=git_path,
        git_blob=git_blob,
        canonical_bytes=canonical_bytes,
        sha256=hashlib.sha256(canonical_bytes).hexdigest(),
    )


def materialize_tracked_jsonl(
    path: Path, *, revision: str = "HEAD"
) -> TrackedJsonlMaterialization:
    """Validate JSONL logical lines without reserializing scientific content."""

    materialization = materialize_tracked_text(path, revision=revision)
    normalized_text = (
        materialization.git_blob.decode("utf-8")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(normalized_text.split("\n"), 1):
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"tracked JSONL artifact has invalid JSON at logical line {line_number}"
            ) from exc
        if not isinstance(value, dict):
            raise ValueError(
                f"tracked JSONL artifact must contain an object at logical line {line_number}"
            )
        rows.append(value)
    return TrackedJsonlMaterialization(
        repository_root=materialization.repository_root,
        git_path=materialization.git_path,
        git_blob=materialization.git_blob,
        canonical_bytes=materialization.canonical_bytes,
        sha256=materialization.sha256,
        rows=tuple(rows),
    )
