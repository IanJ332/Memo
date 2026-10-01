"""Guarded controller callback for the one authorized Phase 06B lifecycle."""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
REMOTE_REPO = "/home/exouser/Memo"
BRANCH = "phase-06b-storage-batch"
LIVE_AUTH_ENV = "MEMLIFE_AUTHORIZE_PHASE06B_LIVE"
RESULT_PREFIX = "PHASE06B_RESULT_B64="
LOCAL_RESULT = REPO_ROOT / "runtime_reports" / "phase06b" / "remote-result.json"
LOCAL_ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "phase06b"
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


def _download_artifacts(
    *,
    address: str,
    mount: str,
    ssh_builder: Callable[[str, str], Sequence[str]],
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> None:
    if not mount.startswith("/"):
        raise RuntimeError("remote mount is not absolute")
    remote_root = f"{mount.rstrip('/')}/memlife/runs/phase-06b-freeze-v1"
    LOCAL_ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    for name in ARTIFACT_NAMES:
        encoded = runner(
            ssh_builder(address, f"base64 -w0 '{remote_root}/{name}'"),
            timeout=600,
        ).stdout.strip()
        data = base64.b64decode(encoded, validate=True)
        (LOCAL_ARTIFACT_ROOT / name).write_bytes(data)


def run_remote_validation(
    *,
    address: str,
    facts: Mapping[str, str],
    expected_commit: str,
    ssh_builder: Callable[[str, str], Sequence[str]],
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> Mapping[str, Any]:
    require_live_authorization()
    sync = runner(ssh_builder(address, _sync_command(expected_commit)), timeout=240)
    validation = runner(
        ssh_builder(
            address,
            (
                f"{LIVE_AUTH_ENV}=YES PHASE06B_EXPECTED_COMMIT={expected_commit} "
                f"bash {REMOTE_REPO}/scripts/jetstream/phase06b_remote.sh"
            ),
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
    _download_artifacts(
        address=address,
        mount=str(facts["resolved_volume_mount"]),
        ssh_builder=ssh_builder,
        runner=runner,
    )
    payload["remote_sync"] = sync.stdout.strip().splitlines()
    payload["live_mount_probe"] = facts.get("resolved_volume_mount")
    LOCAL_RESULT.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_RESULT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload
