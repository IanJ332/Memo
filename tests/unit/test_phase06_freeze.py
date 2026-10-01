"""Experiment Freeze v1 structural and gate tests."""

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

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


def test_freeze_is_canonical_and_hash_stable() -> None:
    payload = _freeze()
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        separators=(",", ": "),
    ) + "\n"
    assert FREEZE_PATH.read_text(encoding="utf-8") == canonical
    assert hashlib.sha256(FREEZE_PATH.read_bytes()).hexdigest() == (
        "0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b"
    )


def test_freeze_checkout_policy_forces_authoritative_crlf_bytes() -> None:
    relative = "experiments/freeze/experiment-freeze-v1.json"
    attributes = subprocess.run(
        ["git", "check-attr", "text", "eol", "--", relative],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert f"{relative}: text: set" in attributes
    assert f"{relative}: eol: crlf" in attributes

    working_bytes = FREEZE_PATH.read_bytes()
    blob_bytes = subprocess.run(
        ["git", "cat-file", "blob", f"HEAD:{relative}"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    ).stdout
    assert b"\r\n" in working_bytes
    assert b"\r\n" not in blob_bytes
    assert hashlib.sha256(blob_bytes).hexdigest() == (
        "6b41176154070dd8c58db24a5c5adfe5365e39d0c31408c033019e7d6108b3c9"
    )


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
