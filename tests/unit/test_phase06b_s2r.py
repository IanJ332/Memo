"""Phase 06B-S2R portability, closure, and future-evidence regressions."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from memlife.runner.lifecycle_status import normalize_lifecycle_status
from memlife.runner.phase06b_supplement import DERIVED_RAW_SHA256
from memlife.runner.tracked_text import (
    canonical_crlf_bytes,
    materialize_tracked_jsonl,
)

ROOT = Path(__file__).resolve().parents[2]
DERIVED = (
    ROOT
    / "artifacts"
    / "phase06b"
    / "derived"
    / "20261001T183940Z-1fc4c4929532"
    / "freeze-v1-raw-runs.provenance-repaired.jsonl"
)
PLAN = ROOT / "experiments" / "supplements" / "phase06b-openviking-missing-runs-v1.json"
CLOSURE = (
    ROOT
    / "artifacts"
    / "phase06b"
    / "supplements"
    / "derived"
    / "20261001T205742Z-67a4ab301c67"
)
EXPECTED_IDS = [
    "freeze-v1__openviking__S0__r3",
    "freeze-v1__openviking__S2__r1",
    "freeze-v1__openviking__S2__r2",
    "freeze-v1__openviking__S2__r3",
    "freeze-v1__openviking__S3__r1",
    "freeze-v1__openviking__S3__r2",
    "freeze-v1__openviking__S3__r3",
    "freeze-v1__openviking__S4__r1",
    "freeze-v1__openviking__S4__r2",
    "freeze-v1__openviking__S4__r3",
]


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [
            "git",
            "-c",
            "core.autocrlf=false",
            "-c",
            "user.name=S2R Test",
            "-c",
            "user.email=s2r-test@example.invalid",
            *args,
        ],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


def _derived_blob() -> bytes:
    return _git(ROOT, "show", f"HEAD:{DERIVED.relative_to(ROOT).as_posix()}").stdout


def _tracked_fixture(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    artifact = repo / DERIVED.relative_to(ROOT)
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(_derived_blob())
    _git(repo, "init")
    _git(repo, "add", artifact.relative_to(repo).as_posix())
    _git(repo, "commit", "-m", "artifact")
    return artifact


@pytest.mark.parametrize("line_ending", [b"\n", b"\r\n"])
def test_checkout_eol_does_not_affect_canonical_identity(
    tmp_path: Path, line_ending: bytes
) -> None:
    artifact = _tracked_fixture(tmp_path)
    artifact.write_bytes(_derived_blob().replace(b"\n", line_ending))
    materialization = materialize_tracked_jsonl(artifact)
    assert materialization.sha256 == DERIVED_RAW_SHA256
    assert len(materialization.rows) == 32


def test_git_blob_and_both_eol_representations_have_one_identity() -> None:
    blob = _derived_blob()
    assert hashlib.sha256(blob).hexdigest() == (
        "84f0ac4e0b96730a0b59999573fce2c3e00b5e568bc831b6171e29544fbe2b7c"
    )
    assert hashlib.sha256(canonical_crlf_bytes(blob)).hexdigest() == DERIVED_RAW_SHA256
    assert hashlib.sha256(canonical_crlf_bytes(blob.replace(b"\n", b"\r\n"))).hexdigest() == (
        DERIVED_RAW_SHA256
    )
    assert materialize_tracked_jsonl(DERIVED).sha256 == DERIVED_RAW_SHA256


def test_semantic_mutation_changes_canonical_hash() -> None:
    blob = _derived_blob()
    mutated = blob.replace(b'"operation_status":"SUCCESS"', b'"operation_status":"ERROR"', 1)
    assert mutated != blob
    assert hashlib.sha256(canonical_crlf_bytes(mutated)).hexdigest() != DERIVED_RAW_SHA256


def test_existing_checkout_after_fast_forward_uses_git_blob_identity(tmp_path: Path) -> None:
    origin = tmp_path / "origin.git"
    author = tmp_path / "author"
    remote = tmp_path / "remote"
    origin.mkdir()
    author.mkdir()
    _git(origin, "init", "--bare")
    _git(author, "init")
    _git(author, "switch", "-c", "main")
    artifact = author / DERIVED.relative_to(ROOT)
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(_derived_blob())
    _git(author, "add", artifact.relative_to(author).as_posix())
    _git(author, "commit", "-m", "artifact")
    _git(author, "remote", "add", "origin", str(origin))
    _git(author, "push", "-u", "origin", "main")
    _git(origin, "symbolic-ref", "HEAD", "refs/heads/main")
    _git(tmp_path, "clone", str(origin), str(remote))

    (author / ".gitattributes").write_text(
        f"{DERIVED.relative_to(ROOT).as_posix()} text eol=crlf\n", encoding="utf-8"
    )
    _git(author, "add", ".gitattributes")
    _git(author, "commit", "-m", "checkout policy")
    _git(author, "push")
    _git(remote, "pull", "--ff-only")

    remote_artifact = remote / DERIVED.relative_to(ROOT)
    assert b"\r\n" not in remote_artifact.read_bytes()
    assert materialize_tracked_jsonl(remote_artifact).sha256 == DERIVED_RAW_SHA256


def test_derived_closure_is_explicit_and_lists_exact_blocked_set() -> None:
    closure = json.loads((CLOSURE / "post-run-closure.json").read_text(encoding="utf-8"))
    aggregate = json.loads(
        (CLOSURE / "supplement-aggregate.derived.json").read_text(encoding="utf-8")
    )
    ledger = json.loads(
        (CLOSURE / "supplement-execution-ledger.derived.json").read_text(encoding="utf-8")
    )
    assert closure["artifact_kind"] == "POST_RUN_DERIVED_RECONSTRUCTION"
    assert closure["original_attempt_capture"] is False
    assert closure["original_attempt_mutated"] is False
    assert closure["authorized_run_ids"] == EXPECTED_IDS
    assert closure["evidence_availability"]["disk_free_samples"] == "NOT_SERIALIZED"
    assert closure["evidence_availability"]["harness_sys_prefix"] == "NOT_SERIALIZED"
    assert aggregate["executed"] == aggregate["success"] == aggregate["error"] == 0
    assert aggregate["blocked_not_executed"] == 10
    assert [entry["run_id"] for entry in ledger["entries"]] == EXPECTED_IDS
    assert {entry["status"] for entry in ledger["entries"]} == {"BLOCKED_NOT_EXECUTED"}
    assert all(entry["provider_started"] is False for entry in ledger["entries"])


def test_future_preflight_failure_serializes_plan_disk_harness_and_blocked_ids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scripts = ROOT / "scripts" / "jetstream"
    sys.path.insert(0, str(scripts))
    try:
        spec = importlib.util.spec_from_file_location(
            "phase06b_supplement_remote_s2r",
            scripts / "phase06b_supplement_remote.py",
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(scripts))

    attempt = "20261001T230000Z-abcdef123456"
    monkeypatch.setenv("PHASE06B_SUPPLEMENT_ATTEMPT_ID", attempt)
    monkeypatch.setenv("PHASE06B_LIVE_VOLUME_MOUNT", str(tmp_path))
    monkeypatch.setenv("PHASE06B_HARNESS_VENV", str(ROOT / ".venv"))
    monkeypatch.setattr(module, "_git_commit", lambda: "a" * 40)
    monkeypatch.setattr(module, "_disk_free", lambda path: 123456789)

    def blocked_preflight(evidence: dict[str, object]) -> dict[str, object]:
        raise RuntimeError("intentional preflight block")

    monkeypatch.setattr(module, "validate_pre_experiment_environment", blocked_preflight)
    output = tmp_path / "attempt"
    output.mkdir()
    result = module.run(output)
    assert result["status"] == "BLOCKED"
    assert result["supplement_status"] == "SUPPLEMENT_BLOCKED"
    preflight = json.loads((tmp_path / "attempt" / "supplement-preflight.json").read_text())
    ledger = json.loads(
        (tmp_path / "attempt" / "supplement-execution-ledger.json").read_text()
    )
    aggregate = json.loads(
        (tmp_path / "attempt" / "supplement-aggregate.json").read_text()
    )
    plan_snapshot = (tmp_path / "attempt" / "supplement-plan.json").read_bytes()
    assert hashlib.sha256(plan_snapshot).hexdigest() == (
        "2db182047dd2b1bfddcaddaad40ace58385f8bdcf0bb114354d9724ee5d6626a"
    )
    assert preflight["authorized_run_ids"] == EXPECTED_IDS
    assert preflight["root_free_bytes"] == 123456789
    assert preflight["persistent_volume_free_bytes"] == 123456789
    assert preflight["harness_selected_path"] == str((ROOT / ".venv").resolve())
    assert preflight["sys_prefix"] == str(Path(sys.prefix).resolve())
    assert ledger["planned_run_ids"] == EXPECTED_IDS
    assert [item["run_id"] for item in ledger["blocked_not_executed"]] == EXPECTED_IDS
    assert {item["status"] for item in ledger["run_statuses"]} == {
        "BLOCKED_NOT_EXECUTED"
    }
    assert aggregate["planned"] == aggregate["blocked_not_executed"] == 10
    assert aggregate["executed"] == aggregate["success"] == aggregate["error"] == 0


@pytest.mark.parametrize(
    ("historical", "canonical"),
    [
        ("SUPPLEMENT_COMPLETE", "PASS"),
        ("SUPPLEMENT_PARTIAL", "PARTIAL"),
        ("SUPPLEMENT_BLOCKED", "BLOCKED"),
        ("PASS", "PASS"),
    ],
)
def test_lifecycle_status_historical_compatibility(
    historical: str, canonical: str
) -> None:
    assert normalize_lifecycle_status(historical) == canonical
