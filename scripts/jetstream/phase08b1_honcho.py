"""Local controller for the authorized Phase 08B-1 Honcho live attempt."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import shlex
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_COMMIT = "cb44f639642442b8277bc3cb2f6afb4b96d81307"
REMOTE_REPO = "/home/exouser/Memo"
REMOTE_EXECUTION_BRANCH = "phase-08b1-honcho-live-acceptance"
REMOTE_ATTEMPT_PARENT = "/home/exouser/.local/memlife/phase08b1"
AUTH_ENV = "MEMLIFE_AUTHORIZE_PHASE08B1_LIVE"
RESULT_PREFIX = "PHASE08B1_RESULT_B64="
WORKTREE_CLEANUP_PREFIX = "PHASE08B1_WORKTREE_CLEANUP_"
PATCH_PATH = (
    REPO_ROOT
    / ".local"
    / "review"
    / "phase08b1-honcho-live-acceptance-candidate10.patch"
)
LOCAL_REVIEW_ROOT = REPO_ROOT / ".local" / "review" / "phase08b1-honcho-live-acceptance"
IMPLEMENTATION_FILES = (
    "experiments/acceptance/phase08b1-honcho-v3.2.1-static-audit.json",
    "scripts/jetstream/jetstreamctl.py",
    "scripts/jetstream/phase08b1_honcho.py",
    "scripts/jetstream/phase08b1_honcho_remote.py",
    "src/memlife/adapters/honcho.py",
    "src/memlife/runner/phase08b1.py",
    "tests/unit/test_phase08b0_honcho_preflight.py",
    "tests/unit/test_phase08b1_honcho_live.py",
    "tests/unit/test_project_handoff.py",
)


def require_live_authorization() -> None:
    if os.environ.get(AUTH_ENV) != "YES":
        raise RuntimeError(f"Phase 08B-1 is disabled unless {AUTH_ENV}=YES")


def new_attempt_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    entropy = os.urandom(6).hex()
    return f"{timestamp}-{entropy}"


def _validate_attempt_id(attempt_id: str) -> None:
    if not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}", attempt_id):
        raise ValueError("invalid Phase 08B-1 attempt ID")


def patch_changed_files(patch_bytes: bytes) -> tuple[str, ...]:
    """Return the exact same-path file set declared by a Git patch."""

    try:
        patch_text = patch_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError("implementation patch is not UTF-8") from exc
    changed: list[str] = []
    for line in patch_text.splitlines():
        if not line.startswith("diff --git "):
            continue
        match = re.fullmatch(r"diff --git a/(.+) b/(.+)", line)
        if match is None or match.group(1) != match.group(2):
            raise RuntimeError("implementation patch contains a rename or invalid path")
        relative = match.group(1)
        path = PurePosixPath(relative)
        if path.is_absolute() or ".." in path.parts or "\\" in relative:
            raise RuntimeError("implementation patch path is unsafe")
        if relative in changed:
            raise RuntimeError(f"implementation patch repeats path: {relative}")
        changed.append(relative)
    if not changed:
        raise RuntimeError("implementation patch declares no changed files")
    return tuple(changed)


def _source_manifest() -> dict[str, str]:
    result: dict[str, str] = {}
    for relative in IMPLEMENTATION_FILES:
        data = (REPO_ROOT / relative).read_bytes()
        result[relative] = hashlib.sha256(data).hexdigest()
    return result


def validate_patch_for_transfer(patch_path: Path = PATCH_PATH) -> dict[str, Any]:
    """Prove the exact LF patch applies to BASE_COMMIT and reproduces local bytes."""

    patch_bytes = patch_path.read_bytes()
    if not patch_bytes:
        raise RuntimeError("Phase 08B-1 implementation patch is empty")
    if b"\r" in patch_bytes:
        raise RuntimeError("Phase 08B-1 implementation patch must use LF only")
    if not patch_bytes.endswith(b"\n") or patch_bytes.endswith(b"\n\n"):
        raise RuntimeError("Phase 08B-1 implementation patch must end with exactly one newline")
    changed_files = patch_changed_files(patch_bytes)
    if set(changed_files) != set(IMPLEMENTATION_FILES):
        missing = sorted(set(changed_files) - set(IMPLEMENTATION_FILES))
        extra = sorted(set(IMPLEMENTATION_FILES) - set(changed_files))
        raise RuntimeError(
            "implementation patch/integrity manifest mismatch: "
            f"missing={missing}, extra={extra}"
        )
    for relative in IMPLEMENTATION_FILES:
        source = (REPO_ROOT / relative).read_bytes()
        if b"\r" in source:
            raise RuntimeError(f"implementation source must use LF: {relative}")
        if not source.endswith(b"\n") or source.endswith(b"\n\n"):
            raise RuntimeError(
                f"implementation source must end with exactly one newline: {relative}"
            )
    common_git_dir = Path(
        subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        ).stdout.strip()
    )
    if not common_git_dir.is_absolute():
        common_git_dir = (REPO_ROOT / common_git_dir).resolve()

    with tempfile.TemporaryDirectory(
        prefix="phase08b1-patch-check-", dir=REPO_ROOT / ".local" / "review"
    ) as temporary:
        index_path = Path(temporary) / "index"
        object_directory = Path(temporary) / "objects"
        object_directory.mkdir()
        environment = os.environ.copy()
        environment["GIT_INDEX_FILE"] = str(index_path)
        environment["GIT_OBJECT_DIRECTORY"] = str(object_directory)
        environment["GIT_ALTERNATE_OBJECT_DIRECTORIES"] = str(
            common_git_dir / "objects"
        )

        def git(*arguments: str, text: bool = True) -> subprocess.CompletedProcess[Any]:
            result = subprocess.run(
                ["git", *arguments],
                cwd=REPO_ROOT,
                env=environment,
                capture_output=True,
                text=text,
                encoding="utf-8" if text else None,
                errors="replace" if text else None,
                check=False,
            )
            if result.returncode:
                stderr = result.stderr if text else result.stderr.decode(errors="replace")
                stdout = result.stdout if text else result.stdout.decode(errors="replace")
                raise RuntimeError((stderr or stdout).strip())
            return result

        git("read-tree", BASE_COMMIT)
        plain = git("apply", "--cached", "--check", str(patch_path))
        nowarn = git(
            "apply", "--cached", "--check", "--whitespace=nowarn", str(patch_path)
        )
        git("apply", "--cached", "--whitespace=nowarn", str(patch_path))
        for relative in IMPLEMENTATION_FILES:
            staged = git("show", f":{relative}", text=False).stdout
            local = (REPO_ROOT / relative).read_bytes()
            if staged != local:
                raise RuntimeError(
                    f"clean-base patch output differs from local implementation: {relative}"
                )
    return {
        "sha256": hashlib.sha256(patch_bytes).hexdigest(),
        "bytes": len(patch_bytes),
        "git_apply_check_exit_status": plain.returncode,
        "git_apply_check_stdout": plain.stdout,
        "git_apply_check_stderr": plain.stderr,
        "git_apply_check_nowarn_exit_status": nowarn.returncode,
        "git_apply_check_nowarn_stdout": nowarn.stdout,
        "git_apply_check_nowarn_stderr": nowarn.stderr,
        "byte_identical_files": list(IMPLEMENTATION_FILES),
        "patch_changed_files": list(changed_files),
        "integrity_manifest_files": list(IMPLEMENTATION_FILES),
    }


def _remote_attempt_paths(attempt_id: str) -> dict[str, str]:
    _validate_attempt_id(attempt_id)
    root = f"{REMOTE_ATTEMPT_PARENT}/{attempt_id}"
    return {
        "root": root,
        "worktree": f"{root}/worktree",
        "patch": f"{root}/implementation.patch",
        "patch_applied": f"{root}/patch-applied",
        "canonical_before": f"{root}/canonical-state-before.sha256",
    }


def _canonical_identity_function() -> str:
    return """canonical_identity() {
    {
        git status --porcelain=v2 -z --untracked-files=all
        git diff --binary
        git diff --cached --binary
        git ls-files --others --exclude-standard | git hash-object --stdin-paths --no-filters
    } | sha256sum | cut -d' ' -f1
}"""


def _prepare_remote_command(
    attempt_id: str,
    mount: str,
    patch_sha256: str,
    patch_bytes: int,
    source_manifest: Mapping[str, str],
) -> str:
    _validate_attempt_id(attempt_id)
    if not mount.startswith("/"):
        raise ValueError("remote persistent-volume mount must be absolute")
    paths = _remote_attempt_paths(attempt_id)
    checks = "\n".join(
        f"test \"$(sha256sum {shlex.quote(relative)} | cut -d' ' -f1)\" = {digest}"
        for relative, digest in source_manifest.items()
    )
    return f"""set -eu
cd {shlex.quote(paths['worktree'])}
test "$(git rev-parse HEAD)" = {BASE_COMMIT}
test "$(sha256sum {shlex.quote(paths['patch'])} | cut -d' ' -f1)" = {patch_sha256}
test "$(wc -c < {shlex.quote(paths['patch'])})" = {patch_bytes}
git apply --check {shlex.quote(paths['patch'])}
git apply --check --whitespace=nowarn {shlex.quote(paths['patch'])}
git -c core.autocrlf=false apply --whitespace=nowarn {shlex.quote(paths['patch'])}
: > {shlex.quote(paths['patch_applied'])}
{checks}
harness={shlex.quote(mount.rstrip('/') + '/memlife/venvs/memlife-harness-phase04/bin/python')}
test -x "$harness"
{AUTH_ENV}=YES "$harness" scripts/jetstream/phase08b1_honcho_remote.py --attempt-id {attempt_id} --mount {shlex.quote(mount)} --implementation-patch-sha256 {patch_sha256} --implementation-patch-bytes {patch_bytes}
"""


def _sync_command(attempt_id: str) -> str:
    paths = _remote_attempt_paths(attempt_id)
    return f"""set -eu
cd {shlex.quote(REMOTE_REPO)}
git fetch origin refs/heads/{REMOTE_EXECUTION_BRANCH}:refs/remotes/origin/{REMOTE_EXECUTION_BRANCH}
target="$(git rev-parse --verify refs/remotes/origin/{REMOTE_EXECUTION_BRANCH}^{{commit}})"
test "$target" = {BASE_COMMIT}
{_canonical_identity_function()}
mkdir -p {shlex.quote(REMOTE_ATTEMPT_PARENT)}
mkdir {shlex.quote(paths['root'])}
canonical_before="$(canonical_identity)"
printf '%s\n' "$canonical_before" > {shlex.quote(paths['canonical_before'])}
git worktree add --detach {shlex.quote(paths['worktree'])} {BASE_COMMIT}
test "$(git -C {shlex.quote(paths['worktree'])} rev-parse HEAD)" = {BASE_COMMIT}
"""


def _cleanup_command(attempt_id: str) -> str:
    paths = _remote_attempt_paths(attempt_id)
    return f"""set +e
cd {shlex.quote(REMOTE_REPO)} || exit 0
{_canonical_identity_function()}
cleanup_status=PASS
canonical_preserved=UNKNOWN
cleanup_blockers=
add_blocker() {{
    cleanup_status=BLOCKED
    if test -n "$cleanup_blockers"; then
        cleanup_blockers="$cleanup_blockers,$1"
    else
        cleanup_blockers="$1"
    fi
}}
if test -f {shlex.quote(paths['canonical_before'])}; then
    canonical_before="$(cat {shlex.quote(paths['canonical_before'])})"
else
    canonical_before=
    add_blocker CANONICAL_STATE_BASELINE_MISSING
fi
if test -e {shlex.quote(paths['worktree'])} || git worktree list --porcelain | grep -Fqx 'worktree {paths['worktree']}'; then
    if test -f {shlex.quote(paths['patch_applied'])}; then
        if git -C {shlex.quote(paths['worktree'])} apply --reverse --check {shlex.quote(paths['patch'])}; then
            git -C {shlex.quote(paths['worktree'])} apply --reverse {shlex.quote(paths['patch'])} || add_blocker ATTEMPT_PATCH_REVERSE_FAILED
        else
            add_blocker ATTEMPT_PATCH_REVERSE_CHECK_FAILED
        fi
    fi
    git worktree remove {shlex.quote(paths['worktree'])} || add_blocker ATTEMPT_WORKTREE_REMOVE_FAILED
fi
canonical_after="$(canonical_identity)"
if test -n "$canonical_before" && test "$canonical_before" = "$canonical_after"; then
    canonical_preserved=true
else
    canonical_preserved=false
    add_blocker CANONICAL_STATE_CHANGED
fi
if test "$cleanup_status" = PASS; then
    for owned_file in {shlex.quote(paths['patch_applied'])} {shlex.quote(paths['patch'])} {shlex.quote(paths['canonical_before'])}; do
        if test -f "$owned_file"; then
            unlink "$owned_file" || add_blocker ATTEMPT_FILE_REMOVE_FAILED
        fi
    done
    rmdir {shlex.quote(paths['root'])} || add_blocker ATTEMPT_ROOT_REMOVE_FAILED
fi
printf '{WORKTREE_CLEANUP_PREFIX}STATUS=%s\n' "$cleanup_status"
printf '{WORKTREE_CLEANUP_PREFIX}CANONICAL_STATE_PRESERVED=%s\n' "$canonical_preserved"
printf '{WORKTREE_CLEANUP_PREFIX}BLOCKERS=%s\n' "$cleanup_blockers"
exit 0
"""


def _scp_command(
    address: str,
    source: Path,
    attempt_id: str,
    ssh_builder: Callable[[str, str], Sequence[str]],
) -> list[str]:
    paths = _remote_attempt_paths(attempt_id)
    ssh = list(ssh_builder(address, "true"))
    if len(ssh) < 4 or ssh[0] != "ssh":
        raise RuntimeError("unexpected SSH command shape")
    return [
        "scp",
        *ssh[1:-2],
        str(source),
        f"{ssh[-2]}:{paths['patch']}",
    ]


def _download(
    *,
    address: str,
    remote_root: str,
    local_root: Path,
    ssh_builder: Callable[[str, str], Sequence[str]],
    runner: Callable[..., subprocess.CompletedProcess[str]],
    completion_sha256: str,
) -> dict[str, Any]:
    def safe_artifact_name(value: object) -> str:
        if not isinstance(value, str) or not value:
            raise RuntimeError("completion artifact name is invalid")
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or "\\" in value:
            raise RuntimeError(f"completion artifact path is unsafe: {value!r}")
        return value

    def remote_bytes(name: str) -> bytes:
        encoded = runner(
            ssh_builder(
                address,
                f"base64 -w0 {shlex.quote(remote_root + '/' + name)}",
            ),
            timeout=300,
        ).stdout.strip()
        try:
            return base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise RuntimeError(f"remote artifact is not valid base64: {name}") from exc

    def write_verified(name: str, data: bytes) -> None:
        destination = local_root / PurePosixPath(name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(data)

    local_root.mkdir(parents=True, exist_ok=False)
    completion_data = remote_bytes("completion.json")
    if hashlib.sha256(completion_data).hexdigest() != completion_sha256:
        raise RuntimeError("completion.json SHA-256 mismatch")
    try:
        completion = json.loads(completion_data)
    except json.JSONDecodeError as exc:
        raise RuntimeError("completion.json is not valid JSON") from exc
    artifacts = completion.get("artifacts") if isinstance(completion, Mapping) else None
    if not isinstance(artifacts, Mapping) or not artifacts:
        raise RuntimeError("completion.json artifacts map is absent or empty")
    normalized: dict[str, tuple[str, int]] = {}
    for raw_name, raw_identity in artifacts.items():
        name = safe_artifact_name(raw_name)
        if not isinstance(raw_identity, Mapping):
            raise RuntimeError(f"completion artifact identity is invalid: {name}")
        digest = raw_identity.get("sha256")
        byte_count = raw_identity.get("bytes")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise RuntimeError(f"completion artifact SHA-256 is invalid: {name}")
        if (
            not isinstance(byte_count, int)
            or isinstance(byte_count, bool)
            or byte_count < 0
        ):
            raise RuntimeError(f"completion artifact byte count is invalid: {name}")
        normalized[name] = (digest, byte_count)
    if "runtime-file-lifecycle.json" not in normalized:
        raise RuntimeError("completion omits runtime-file-lifecycle.json")

    write_verified("completion.json", completion_data)
    copied: list[str] = ["completion.json"]
    for name, (expected_sha, expected_bytes) in normalized.items():
        data = remote_bytes(name)
        if len(data) != expected_bytes:
            raise RuntimeError(f"completion artifact byte-count mismatch: {name}")
        if hashlib.sha256(data).hexdigest() != expected_sha:
            raise RuntimeError(f"completion artifact SHA-256 mismatch: {name}")
        write_verified(name, data)
        copied.append(name)

    lifecycle_path = local_root / "runtime-file-lifecycle.json"
    try:
        lifecycle = json.loads(lifecycle_path.read_bytes())
    except json.JSONDecodeError as exc:
        raise RuntimeError("runtime-file-lifecycle.json is not valid JSON") from exc
    preexisting = (
        lifecycle.get("preexisting_residue")
        if isinstance(lifecycle, Mapping)
        else None
    )
    optional_status = "NOT_PRESENT"
    if isinstance(preexisting, Mapping) and preexisting.get("evidence_artifact"):
        optional_name = safe_artifact_name(preexisting["evidence_artifact"])
        optional_sha = preexisting.get("evidence_sha256")
        if not isinstance(optional_sha, str) or not re.fullmatch(
            r"[0-9a-f]{64}", optional_sha
        ):
            raise RuntimeError("preexisting residue evidence SHA-256 is invalid")
        if optional_name not in normalized:
            optional_data = remote_bytes(optional_name)
            if hashlib.sha256(optional_data).hexdigest() != optional_sha:
                raise RuntimeError("preexisting residue evidence SHA-256 mismatch")
            write_verified(optional_name, optional_data)
            copied.append(optional_name)
        elif normalized[optional_name][0] != optional_sha:
            raise RuntimeError("preexisting residue evidence reference mismatch")
        optional_status = "COPIED_AND_VERIFIED"
    return {
        "completion_artifacts": list(normalized),
        "copied_artifacts": copied,
        "optional_preexisting_residue": optional_status,
    }


def _parse_cleanup_result(output: str) -> dict[str, Any]:
    values: dict[str, str] = {}
    for line in output.splitlines():
        if not line.startswith(WORKTREE_CLEANUP_PREFIX):
            continue
        key, separator, value = line[len(WORKTREE_CLEANUP_PREFIX) :].partition("=")
        if separator:
            values[key] = value
    status = values.get("STATUS")
    preserved = values.get("CANONICAL_STATE_PRESERVED")
    if status not in {"PASS", "BLOCKED"} or preserved not in {
        "true",
        "false",
        "UNKNOWN",
    }:
        return {
            "status": "BLOCKED",
            "canonical_state_preserved": False,
            "blockers": ["WORKTREE_CLEANUP_RESULT_INVALID"],
        }
    blockers = [item for item in values.get("BLOCKERS", "").split(",") if item]
    if status == "BLOCKED" and not blockers:
        blockers = ["WORKTREE_CLEANUP_FAILED"]
    return {
        "status": status,
        "canonical_state_preserved": preserved == "true",
        "blockers": blockers,
    }


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
    _validate_attempt_id(attempt_id)
    if expected_commit != BASE_COMMIT:
        raise RuntimeError("local HEAD differs from the authorized Phase 08B-0 base")
    patch_validation = validate_patch_for_transfer()
    patch_bytes = PATCH_PATH.read_bytes()
    mount = str(facts["resolved_volume_mount"])
    patch_sha256 = hashlib.sha256(patch_bytes).hexdigest()
    payload: dict[str, Any] | None = None
    copyback: dict[str, Any] | None = None
    primary_error: Exception | None = None
    cleanup: dict[str, Any]
    try:
        runner(ssh_builder(address, _sync_command(attempt_id)), timeout=240)
        runner(
            _scp_command(address, PATCH_PATH, attempt_id, ssh_builder),
            timeout=300,
        )
        execution = runner(
            ssh_builder(
                address,
                _prepare_remote_command(
                    attempt_id,
                    mount,
                    patch_sha256,
                    len(patch_bytes),
                    _source_manifest(),
                ),
            ),
            timeout=5400,
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
            raise RuntimeError("remote Honcho runner returned no structured result")
        decoded = json.loads(base64.b64decode(encoded, validate=True))
        if not isinstance(decoded, dict):
            raise RuntimeError("remote Honcho result is not an object")
        payload = decoded
        if (
            payload.get("attempt_id") != attempt_id
            or payload.get("base_commit") != BASE_COMMIT
        ):
            raise RuntimeError("remote Honcho result identity mismatch")
        remote_root = str(payload["remote_evidence_root"])
        completion_sha256 = payload.get("completion_manifest_sha256")
        if not isinstance(completion_sha256, str) or not re.fullmatch(
            r"[0-9a-f]{64}", completion_sha256
        ):
            raise RuntimeError("remote completion manifest identity is invalid")
        local_root = LOCAL_REVIEW_ROOT / attempt_id
        copyback = _download(
            address=address,
            remote_root=remote_root,
            local_root=local_root,
            ssh_builder=ssh_builder,
            runner=runner,
            completion_sha256=completion_sha256,
        )
    except Exception as exc:
        primary_error = exc
    finally:
        try:
            cleanup_execution = runner(
                ssh_builder(address, _cleanup_command(attempt_id)), timeout=300
            )
            cleanup = _parse_cleanup_result(cleanup_execution.stdout)
        except Exception as exc:
            cleanup = {
                "status": "BLOCKED",
                "canonical_state_preserved": False,
                "blockers": [
                    f"WORKTREE_CLEANUP_COMMAND_FAILED:{type(exc).__name__}"
                ],
            }
    if primary_error is not None:
        cleanup_detail = ",".join(cleanup["blockers"])
        if cleanup["status"] == "BLOCKED":
            raise RuntimeError(
                f"{type(primary_error).__name__}: {primary_error}; "
                f"cleanup blockers: {cleanup_detail}"
            ) from primary_error
        raise primary_error
    if payload is None or copyback is None:
        raise RuntimeError("remote Honcho execution produced no result")
    local_root = LOCAL_REVIEW_ROOT / attempt_id
    payload.update(
        initial_remote_head=facts.get("repo_head"),
        synced_remote_head=BASE_COMMIT,
        tested_commit=BASE_COMMIT,
        implementation_patch_sha256=hashlib.sha256(patch_bytes).hexdigest(),
        implementation_patch_bytes=len(patch_bytes),
        local_patch_validation=patch_validation,
        local_review_root=str(local_root),
        completion_copyback=copyback,
        controller_worktree_cleanup=cleanup,
    )
    if cleanup["status"] == "BLOCKED":
        payload["status"] = "BLOCKED"
        payload.setdefault("cleanup_blockers", []).extend(cleanup["blockers"])
    return payload


__all__ = ["new_attempt_id", "require_live_authorization", "run_remote_validation"]
