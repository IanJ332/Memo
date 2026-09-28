"""Remote-work callback for the single authorized Phase 04 Jetstream session."""

from __future__ import annotations

import base64
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

REMOTE_REPO = "/home/exouser/Memo"
BRANCH = "phase-04-hindsight-bringup"
RESULT_PREFIX = "PHASE04_RESULT_B64="
LOCAL_RESULT = Path(__file__).resolve().parents[2] / "runtime_reports" / "phase-04-hindsight" / "result.json"


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
    printf '%s\\n' 'remote clone has unexplained modifications after local-context exclusion' >&2
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
printf 'remote_branch=%s\\n' "$(git branch --show-current)"
printf 'remote_head=%s\\n' "$actual"
"""


def run_remote_validation(
    *,
    address: str,
    facts: Mapping[str, str],
    expected_commit: str,
    ssh_builder: Callable[[str, str], Sequence[str]],
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> Mapping[str, Any]:
    """Synchronize, execute the frozen run, and retain a sanitized local copy."""

    sync = runner(ssh_builder(address, _sync_command(expected_commit)), timeout=180)
    validation = runner(
        ssh_builder(
            address,
            f"bash {REMOTE_REPO}/scripts/jetstream/phase04_remote.sh",
        ),
        timeout=7200,
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
        raise RuntimeError("remote validation did not return its sanitized result payload")
    payload = json.loads(base64.b64decode(encoded).decode("utf-8"))
    if payload.get("git_commit_tested") != expected_commit:
        raise RuntimeError("remote result commit did not match the local branch commit")
    payload["remote_sync"] = sync.stdout.strip().splitlines()
    payload["live_mount_probe"] = facts.get("resolved_volume_mount")
    LOCAL_RESULT.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_RESULT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload
