from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "prepare_phase08b1_candidate10_patch.py"


def _module():
    spec = importlib.util.spec_from_file_location(
        "prepare_phase08b1_candidate10_patch", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_candidate10_patch_is_reconstructed_with_frozen_identity(tmp_path: Path) -> None:
    module = _module()
    destination = tmp_path / module.PATCH_PATH.name

    created = module.prepare_patch(destination)
    verified = module.prepare_patch(destination)

    assert created == {
        "path": str(destination.resolve()),
        "sha256": module.PATCH_SHA256,
        "bytes": module.PATCH_BYTES,
        "created": True,
        "base_commit": module.BASE_COMMIT,
        "publication_commit": module.PUBLICATION_COMMIT,
    }
    assert verified == {**created, "created": False}
    assert len(destination.read_bytes()) == 369_953
    assert module.PATCH_SHA256 == (
        "593b18eda51b8d9291b004683b875c06ebed70f4a8424f02108228bf18261ca3"
    )


def test_candidate10_patch_preparation_refuses_to_overwrite(tmp_path: Path) -> None:
    module = _module()
    destination = tmp_path / module.PATCH_PATH.name
    destination.write_bytes(b"not the historical patch\n")

    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        module.prepare_patch(destination)


def test_candidate10_implementation_checkout_is_declared_lf() -> None:
    module = _module()
    result = subprocess.run(
        ["git", "check-attr", "eol", "--", *module.IMPLEMENTATION_FILES],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    declared = {
        line.split(": eol: ", 1)[0]: line.split(": eol: ", 1)[1]
        for line in result.stdout.splitlines()
    }
    assert declared == {relative: "lf" for relative in module.IMPLEMENTATION_FILES}
