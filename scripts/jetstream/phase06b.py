"""Guarded controller callback for the one authorized Phase 06B lifecycle."""

from __future__ import annotations

import base64
import json
import os
import re
import shlex
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
REMOTE_REPO = "/home/exouser/Memo"
BRANCH = "phase-06b-storage-batch"
LIVE_AUTH_ENV = "MEMLIFE_AUTHORIZE_PHASE06B_LIVE"
HARNESS_ENV = "PHASE06B_HARNESS_VENV"
RESULT_PREFIX = "PHASE06B_RESULT_B64="
ATTEMPT_ENV = "PHASE06B_ATTEMPT_ID"
ATTEMPT_PATTERN = re.compile(r"[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}")
LOCAL_RESULT_ROOT = REPO_ROOT / "runtime_reports" / "phase06b" / "attempts"
LOCAL_ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "phase06b" / "attempts"
ARTIFACT_NAMES = (
    "freeze-v1-raw-runs.jsonl",
    "freeze-v1-aggregate.json",
    "freeze-v1-residual-index.json",
    "execution-ledger.json",
)


def require_live_authorization() -> None:
    if os.environ.get(LIVE_AUTH_ENV) != "YES":
        raise RuntimeError(
            f"Phase 06B live execution is disabled; set {LIVE_AUTH_ENV}=YES only "
            "for the explicitly authorized managed lifecycle"
        )


def new_attempt_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{uuid.uuid4().hex[:12]}"


def validate_attempt_id(attempt_id: str) -> str:
    if not ATTEMPT_PATTERN.fullmatch(attempt_id):
        raise ValueError("invalid Phase 06B attempt ID")
    return attempt_id


def attempt_path(root: Path, attempt_id: str) -> Path:
    return root / validate_attempt_id(attempt_id)


def _sync_command(expected_commit: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", expected_commit):
        raise ValueError("expected commit must be a full lowercase Git object ID")
    return f"""set -eu
repo={REMOTE_REPO}
cd "$repo"
if [ -f JETSTREAM2_SERVER_CONTEXT.txt ]; then
    grep -qxF '/JETSTREAM2_SERVER_CONTEXT.txt' .git/info/exclude || printf '%s\\n' '/JETSTREAM2_SERVER_CONTEXT.txt' >> .git/info/exclude
fi
if [ -n "$(git status --porcelain)" ]; then
    printf '%s\\n' 'remote clone has unexplained tracked modifications' >&2
    git status --short >&2
    exit 21
fi
git fetch origin
if git show-ref --verify --quiet refs/heads/{BRANCH}; then
    git switch {BRANCH}
    git merge --ff-only origin/{BRANCH}
else
    git switch --track -c {BRANCH} origin/{BRANCH}
fi
actual="$(git rev-parse HEAD)"
test "$actual" = '{expected_commit}'
test "$(git branch --show-current)" = '{BRANCH}'
printf 'remote_branch=%s\\n' "$(git branch --show-current)"
printf 'remote_head=%s\\n' "$actual"
"""


def _contains_sensitive_key(value: object) -> bool:
    pattern = re.compile(
        r"(?i)(api.?key|authorization|password|private.?key|access.?token|refresh.?token|credential|secret)"
    )
    if isinstance(value, Mapping):
        return any(
            pattern.search(str(key)) or _contains_sensitive_key(child)
            for key, child in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_sensitive_key(item) for item in value)
    return False


def _synced_remote_head(sync_output: str) -> str:
    heads = [
        line.removeprefix("remote_head=")
        for line in sync_output.splitlines()
        if line.startswith("remote_head=")
    ]
    if len(heads) != 1 or not re.fullmatch(r"[0-9a-f]{40}", heads[0]):
        raise RuntimeError("remote sync did not report exactly one valid Git head")
    return heads[0]


def _remote_batch_command(expected_commit: str, attempt_id: str) -> str:
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
        [*assignments, "bash", f"{REMOTE_REPO}/scripts/jetstream/phase06b_remote.sh"]
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
        f"{mount.rstrip('/')}/memlife/runs/phase06b/attempts/"
        f"{attempt_id}"
    )
    LOCAL_ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    local_attempt_root = attempt_path(LOCAL_ARTIFACT_ROOT, attempt_id)
    local_attempt_root.mkdir(exist_ok=False)
    for name in ARTIFACT_NAMES:
        encoded = runner(
            ssh_builder(address, f"base64 -w0 '{remote_root}/{name}'"),
            timeout=600,
        ).stdout.strip()
        data = base64.b64decode(encoded, validate=True)
        with (local_attempt_root / name).open("xb") as stream:
            stream.write(data)
    return local_attempt_root


def _write_local_result(payload: Mapping[str, Any], attempt_id: str) -> Path:
    result_dir = attempt_path(LOCAL_RESULT_ROOT, attempt_id)
    result_dir.parent.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(exist_ok=False)
    result_path = result_dir / "remote-result.json"
    with result_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, indent=2) + "\n")
    return result_path


def run_remote_validation(
    *,
    address: str,
    facts: Mapping[str, str],
    expected_commit: str,
    attempt_id: str,
    ssh_builder: Callable[[str, str], Sequence[str]],
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> Mapping[str, Any]:
    require_live_authorization()
    validate_attempt_id(attempt_id)
    sync = runner(ssh_builder(address, _sync_command(expected_commit)), timeout=240)
    synced_remote_head = _synced_remote_head(sync.stdout)
    if synced_remote_head != expected_commit:
        raise RuntimeError("synchronized remote head did not match prepared live commit")
    validation = runner(
        ssh_builder(
            address,
            _remote_batch_command(expected_commit, attempt_id),
        ),
        timeout=28800,
    )
    encoded = next(
        (
            line[len(RESULT_PREFIX) :]
            for line in reversed(validation.stdout.splitlines())
            if line.startswith(RESULT_PREFIX)
        ),
        None,
    )
    if not encoded:
        raise RuntimeError("remote Phase 06B batch returned no structured result")
    payload = json.loads(base64.b64decode(encoded).decode("utf-8"))
    if _contains_sensitive_key(payload):
        raise RuntimeError("remote Phase 06B result retained a prohibited sensitive key")
    if payload.get("git_commit_tested") != expected_commit:
        raise RuntimeError("remote result commit did not match prepared live commit")
    if payload.get("freeze_sha256") != (
        "0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b"
    ):
        raise RuntimeError("remote result freeze hash mismatch")
    if payload.get("downstream_decision_model_calls") != 0:
        raise RuntimeError("remote result violated the downstream-call hard-zero gate")
    if payload.get("attempt_id") != attempt_id:
        raise RuntimeError("remote result attempt ID did not match the lifecycle attempt")
    payload["initial_remote_head"] = facts.get("repo_head")
    payload["synced_remote_head"] = synced_remote_head
    payload["tested_commit"] = payload["git_commit_tested"]
    _download_artifacts(
        address=address,
        mount=str(facts["resolved_volume_mount"]),
        attempt_id=attempt_id,
        ssh_builder=ssh_builder,
        runner=runner,
    )
    payload["remote_sync"] = sync.stdout.strip().splitlines()
    payload["live_mount_probe"] = facts.get("resolved_volume_mount")
    _write_local_result(payload, attempt_id)
    return payload
