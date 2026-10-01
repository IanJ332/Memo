"""Guarded controller for the exact Phase 06B ten-run supplement only."""

from __future__ import annotations

import base64
import json
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from phase06b import _contains_sensitive_key, _sync_command, _synced_remote_head
from phase06b import attempt_path, new_attempt_id, validate_attempt_id

REPO_ROOT = Path(__file__).resolve().parents[2]
REMOTE_REPO = "/home/exouser/Memo"
LIVE_AUTH_ENV = "MEMLIFE_AUTHORIZE_PHASE06B_SUPPLEMENT_LIVE"
HARNESS_ENV = "PHASE06B_HARNESS_VENV"
ATTEMPT_ENV = "PHASE06B_SUPPLEMENT_ATTEMPT_ID"
RESULT_PREFIX = "PHASE06B_SUPPLEMENT_RESULT_B64="
FREEZE_SHA256 = "0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b"
ORIGINAL_ATTEMPT_ID = "20261001T183940Z-1fc4c4929532"
LOCAL_RESULT_ROOT = REPO_ROOT / "runtime_reports" / "phase06b" / "supplements" / "attempts"
LOCAL_ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "phase06b" / "supplements" / "attempts"
ARTIFACT_NAMES = (
    "supplement-raw-runs.jsonl",
    "supplement-execution-ledger.json",
    "supplement-diagnostics.jsonl",
    "supplement-result.json",
)


def require_live_authorization() -> None:
    if os.environ.get(LIVE_AUTH_ENV) != "YES":
        raise RuntimeError(
            "Phase 06B supplement execution is disabled; a later prompt must "
            f"explicitly authorize it with {LIVE_AUTH_ENV}=YES"
        )


def _remote_supplement_command(expected_commit: str, attempt_id: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", expected_commit):
        raise ValueError("expected commit must be a full lowercase Git object ID")
    validate_attempt_id(attempt_id)
    assignments = [
        f"{LIVE_AUTH_ENV}=YES",
        f"PHASE06B_EXPECTED_COMMIT={expected_commit}",
        f"{ATTEMPT_ENV}={attempt_id}",
    ]
    explicit_harness = os.environ.get(HARNESS_ENV)
    if explicit_harness:
        assignments.append(f"{HARNESS_ENV}={shlex.quote(explicit_harness)}")
    return " ".join(
        [
            *assignments,
            "bash",
            f"{REMOTE_REPO}/scripts/jetstream/phase06b_supplement_remote.sh",
        ]
    )


def _download_artifacts(
    *,
    address: str,
    mount: str,
    attempt_id: str,
    ssh_builder: Callable[[str, str], Sequence[str]],
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> Path:
    if not mount.startswith("/"):
        raise RuntimeError("remote mount is not absolute")
    validate_attempt_id(attempt_id)
    remote_root = (
        f"{mount.rstrip('/')}/memlife/runs/phase06b/supplements/attempts/{attempt_id}"
    )
    LOCAL_ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    local_root = attempt_path(LOCAL_ARTIFACT_ROOT, attempt_id)
    local_root.mkdir(exist_ok=False)
    for name in ARTIFACT_NAMES:
        encoded = runner(
            ssh_builder(address, f"base64 -w0 '{remote_root}/{name}'"), timeout=600
        ).stdout.strip()
        data = base64.b64decode(encoded, validate=True)
        with (local_root / name).open("xb") as stream:
            stream.write(data)
    return local_root


def _write_local_result(payload: Mapping[str, Any], attempt_id: str) -> Path:
    root = attempt_path(LOCAL_RESULT_ROOT, attempt_id)
    root.parent.mkdir(parents=True, exist_ok=True)
    root.mkdir(exist_ok=False)
    path = root / "remote-result.json"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def run_remote_validation(
    *,
    address: str,
    facts: Mapping[str, str],
    expected_commit: str,
    attempt_id: str,
    ssh_builder: Callable[[str, str], Sequence[str]],
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> Mapping[str, Any]:
    """Run only the plan-derived supplement after explicit future authorization."""

    require_live_authorization()
    validate_attempt_id(attempt_id)
    if attempt_id == ORIGINAL_ATTEMPT_ID:
        raise RuntimeError("supplement attempt ID must differ from the original attempt")
    sync = runner(ssh_builder(address, _sync_command(expected_commit)), timeout=240)
    synced_remote_head = _synced_remote_head(sync.stdout)
    if synced_remote_head != expected_commit:
        raise RuntimeError("synchronized remote head did not match prepared commit")
    execution = runner(
        ssh_builder(address, _remote_supplement_command(expected_commit, attempt_id)),
        timeout=28800,
    )
    encoded = next(
        (
            line[len(RESULT_PREFIX) :]
            for line in reversed(execution.stdout.splitlines())
            if line.startswith(RESULT_PREFIX)
        ),
        None,
    )
    if not encoded:
        raise RuntimeError("remote supplement returned no structured result")
    payload = json.loads(base64.b64decode(encoded, validate=True).decode("utf-8"))
    if _contains_sensitive_key(payload):
        raise RuntimeError("remote supplement result retained a prohibited sensitive key")
    required = {
        "attempt_id": attempt_id,
        "git_commit_tested": expected_commit,
        "freeze_sha256": FREEZE_SHA256,
        "eligible_count": 10,
        "downstream_decision_model_calls": 0,
        "rq3_calls": 0,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise RuntimeError(f"remote supplement result mismatch: {key}")
    _download_artifacts(
        address=address,
        mount=str(facts["resolved_volume_mount"]),
        attempt_id=attempt_id,
        ssh_builder=ssh_builder,
        runner=runner,
    )
    payload.update(
        initial_remote_head=facts.get("repo_head"),
        synced_remote_head=synced_remote_head,
        tested_commit=payload["git_commit_tested"],
        remote_sync=sync.stdout.strip().splitlines(),
        live_mount_probe=facts.get("resolved_volume_mount"),
    )
    _write_local_result(payload, attempt_id)
    return payload


__all__ = [
    "new_attempt_id",
    "require_live_authorization",
    "run_remote_validation",
]
