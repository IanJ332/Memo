"""Checkout-independent materialization of the frozen experiment protocol."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from memlife.runner.tracked_text import read_git_blob

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


def load_freeze_from_git(
    freeze_path: Path,
    *,
    revision: str = "HEAD",
) -> FreezeMaterialization:
    """Load Freeze v1 from ``git show``, never from working-tree bytes."""

    repo_root, git_path, git_blob = read_git_blob(freeze_path, revision=revision)
    if git_path != FREEZE_GIT_PATH:
        raise ValueError(
            f"freeze must use the repository path {FREEZE_GIT_PATH!r}, got {git_path!r}"
        )
    payload, canonical_bytes = canonical_freeze_bytes(git_blob)
    return FreezeMaterialization(
        payload=payload,
        git_blob=git_blob,
        canonical_bytes=canonical_bytes,
        sha256=hashlib.sha256(canonical_bytes).hexdigest(),
    )
