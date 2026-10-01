"""Experiment Freeze v1 structural and gate tests."""

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

from memlife.runner.storage_batch import generate_run_plan

REPO_ROOT = Path(__file__).resolve().parents[2]
FREEZE_PATH = REPO_ROOT / "experiments" / "freeze" / "experiment-freeze-v1.json"
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_experiment_freeze.py"


def _validator_module():
    spec = importlib.util.spec_from_file_location("freeze_validator", VALIDATOR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _freeze() -> dict[str, object]:
    return json.loads(FREEZE_PATH.read_text(encoding="utf-8"))


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [
            "git",
            "-c",
            "core.autocrlf=false",
            "-c",
            "user.name=Freeze Test",
            "-c",
            "user.email=freeze-test@example.invalid",
            *args,
        ],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


def _freeze_blob() -> bytes:
    return _git(
        REPO_ROOT,
        "show",
        "HEAD:experiments/freeze/experiment-freeze-v1.json",
    ).stdout


def _checkout_fixture(tmp_path: Path, *, line_ending: bytes) -> Path:
    repo = tmp_path / "repo"
    freeze = repo / "experiments" / "freeze" / "experiment-freeze-v1.json"
    freeze.parent.mkdir(parents=True)
    freeze.write_bytes(_freeze_blob())
    _git(repo, "init")
    _git(repo, "add", "experiments/freeze/experiment-freeze-v1.json")
    _git(repo, "commit", "-m", "freeze")
    freeze.write_bytes(_freeze_blob().replace(b"\n", line_ending))
    return freeze


def test_freeze_is_canonical_and_hash_stable() -> None:
    module = _validator_module()
    materialization = module.load_freeze_from_git(FREEZE_PATH)
    assert materialization.payload == _freeze()
    assert hashlib.sha256(materialization.canonical_bytes).hexdigest() == (
        "0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b"
    )


def test_existing_lf_checkout_passes(tmp_path: Path) -> None:
    module = _validator_module()
    freeze = _checkout_fixture(tmp_path, line_ending=b"\n")
    assert b"\r\n" not in freeze.read_bytes()
    assert module.main(
        ["--freeze", str(freeze), "--manifest", str(tmp_path / "absent.json")]
    ) == 0


def test_existing_crlf_checkout_passes(tmp_path: Path) -> None:
    module = _validator_module()
    freeze = _checkout_fixture(tmp_path, line_ending=b"\r\n")
    assert b"\r\n" in freeze.read_bytes()
    assert module.main(
        ["--freeze", str(freeze), "--manifest", str(tmp_path / "absent.json")]
    ) == 0


def test_git_blob_validation_materializes_authoritative_hash() -> None:
    module = _validator_module()
    relative = "experiments/freeze/experiment-freeze-v1.json"
    materialization = module.load_freeze_from_git(FREEZE_PATH)
    assert materialization.git_blob == _git(REPO_ROOT, "show", f"HEAD:{relative}").stdout
    assert b"\r\n" not in materialization.git_blob
    assert b"\r\n" in materialization.canonical_bytes
    assert hashlib.sha256(materialization.git_blob).hexdigest() == (
        "6b41176154070dd8c58db24a5c5adfe5365e39d0c31408c033019e7d6108b3c9"
    )
    assert materialization.sha256 == (
        "0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b"
    )


def test_remote_style_fast_forward_checkout_passes(tmp_path: Path) -> None:
    module = _validator_module()
    origin = tmp_path / "origin.git"
    author = tmp_path / "author"
    remote = tmp_path / "remote"
    origin.mkdir()
    author.mkdir()
    _git(origin, "init", "--bare")
    _git(author, "init")
    _git(author, "switch", "-c", "main")
    author_freeze = author / "experiments" / "freeze" / "experiment-freeze-v1.json"
    author_freeze.parent.mkdir(parents=True)
    author_freeze.write_bytes(_freeze_blob())
    _git(author, "add", "experiments/freeze/experiment-freeze-v1.json")
    _git(author, "commit", "-m", "add freeze")
    _git(author, "remote", "add", "origin", str(origin))
    _git(author, "push", "-u", "origin", "main")
    _git(origin, "symbolic-ref", "HEAD", "refs/heads/main")
    _git(tmp_path, "clone", str(origin), str(remote))

    (author / ".gitattributes").write_text(
        "experiments/freeze/experiment-freeze-v1.json text eol=crlf\n",
        encoding="utf-8",
    )
    _git(author, "add", ".gitattributes")
    _git(author, "commit", "-m", "add checkout policy")
    _git(author, "push")
    _git(remote, "pull", "--ff-only")

    remote_freeze = remote / "experiments" / "freeze" / "experiment-freeze-v1.json"
    assert b"\r\n" not in remote_freeze.read_bytes()
    assert module.main(
        ["--freeze", str(remote_freeze), "--manifest", str(tmp_path / "absent.json")]
    ) == 0
    assert generate_run_plan(remote_freeze)["expected_executable_count"] == 42


def test_freeze_validator_passes_complete_matrix() -> None:
    module = _validator_module()
    assert module.validate_freeze(_freeze()) == []


def test_freeze_rejects_unresolved_and_incomplete_capability_cells() -> None:
    module = _validator_module()
    payload = _freeze()
    payload["capability_matrix"]["mem0"]["S4"] = "NEEDS_FROZEN_MAPPING"  # type: ignore[index]
    errors = module.validate_freeze(payload)
    assert any("unresolved" in error for error in errors)


def test_unsupported_cells_are_explicit_and_valid() -> None:
    payload = _freeze()
    matrix = payload["capability_matrix"]
    assert matrix["mem0"]["S4"] == "UNSUPPORTED"  # type: ignore[index]
    assert matrix["mem0"]["S5"] == "UNSUPPORTED"  # type: ignore[index]
    assert matrix["openviking"]["S1"] == "UNSUPPORTED"  # type: ignore[index]
    assert matrix["openviking"]["S5"] == "UNSUPPORTED"  # type: ignore[index]


def test_phase06b_gate_rejects_runtime_provider_version_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _validator_module()
    payload = _freeze()
    runtime = {
        "providers": {
            item["id"]: {
                "version": item["version"],
                "configuration_hash": item["configuration_hash"],
            }
            for item in payload["providers"]
        },
        "repetitions": 3,
        "downstream_decision_calls": 0,
    }
    runtime["providers"]["mem0"]["version"] = "wrong"

    class Completed:
        def __init__(self, stdout: str) -> None:
            self.stdout = stdout

    answers = iter(("phase-06-experiment-freeze\n", "a" * 40 + "\n"))
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *args, **kwargs: Completed(next(answers)),
    )
    errors = module.validate_phase06b_gate(
        payload,
        expected_repo_commit="a" * 40,
        runtime_evidence=runtime,
    )
    assert "mem0 runtime version mismatch" in errors
