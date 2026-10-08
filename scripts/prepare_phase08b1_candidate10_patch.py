"""Reconstruct the frozen Candidate10 implementation patch from Git objects."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_COMMIT = "cb44f639642442b8277bc3cb2f6afb4b96d81307"
PUBLICATION_COMMIT = "54c1f7847af582cffc078fbc99aecfaab6b12dc2"
PATCH_SHA256 = "593b18eda51b8d9291b004683b875c06ebed70f4a8424f02108228bf18261ca3"
PATCH_BYTES = 369_953
PATCH_PATH = (
    REPO_ROOT
    / ".local"
    / "review"
    / "phase08b1-honcho-live-acceptance-candidate10.patch"
)
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


def _reconstruct_patch() -> bytes:
    command: Sequence[str] = (
        "git",
        "-c",
        "core.autocrlf=false",
        "-c",
        "core.safecrlf=false",
        "diff",
        "--no-ext-diff",
        "--no-textconv",
        "--no-color",
        "--binary",
        "--full-index",
        "--no-renames",
        "--diff-algorithm=myers",
        "--unified=3",
        "--src-prefix=a/",
        "--dst-prefix=b/",
        BASE_COMMIT,
        PUBLICATION_COMMIT,
        "--",
        *IMPLEMENTATION_FILES,
    )
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Candidate10 patch reconstruction failed: {message}")
    return result.stdout


def _validate_patch(patch: bytes) -> None:
    digest = hashlib.sha256(patch).hexdigest()
    if len(patch) != PATCH_BYTES or digest != PATCH_SHA256:
        raise RuntimeError(
            "reconstructed Candidate10 patch identity mismatch: "
            f"expected {PATCH_SHA256}/{PATCH_BYTES}, observed {digest}/{len(patch)}"
        )
    if b"\r" in patch or not patch.endswith(b"\n") or patch.endswith(b"\n\n"):
        raise RuntimeError("reconstructed Candidate10 patch is not canonical LF text")


def prepare_patch(destination: Path = PATCH_PATH) -> dict[str, object]:
    """Create the ignored fixture without overwriting any existing bytes."""

    patch = _reconstruct_patch()
    _validate_patch(patch)
    destination = destination.resolve()
    if destination.exists():
        existing = destination.read_bytes()
        if existing != patch:
            raise RuntimeError(
                f"refusing to overwrite non-canonical Candidate10 patch: {destination}"
            )
        created = False
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            with destination.open("xb") as stream:
                stream.write(patch)
        except FileExistsError as exc:
            raise RuntimeError(
                f"Candidate10 patch destination appeared concurrently: {destination}"
            ) from exc
        created = True
    return {
        "path": str(destination),
        "sha256": PATCH_SHA256,
        "bytes": PATCH_BYTES,
        "created": created,
        "base_commit": BASE_COMMIT,
        "publication_commit": PUBLICATION_COMMIT,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reconstruct the frozen Candidate10 patch fixture from tracked Git objects."
        )
    )
    parser.add_argument("--output", type=Path, default=PATCH_PATH)
    arguments = parser.parse_args()
    result = prepare_patch(arguments.output)
    state = "created" if result["created"] else "already verified"
    print(
        f"Candidate10 patch {state}: {result['path']} "
        f"sha256={result['sha256']} bytes={result['bytes']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
