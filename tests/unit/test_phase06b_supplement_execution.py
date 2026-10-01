"""Supplement provenance, observability isolation, stop, and combination tests."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from memlife.adapters.reference import ReferenceMemoryAdapter
from memlife.runner.phase06b_supplement import (
    DERIVED_RAW_SHA256,
    EXECUTION_ORIGIN,
    ORIGINAL_ATTEMPT_ID,
    derive_combined_view,
    execute_supplement_runs,
    validate_supplement_rows,
    validate_supplement_selection,
)
from memlife.runner.storage_batch import run_repetition

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "experiments" / "supplements" / "phase06b-openviking-missing-runs-v1.json"
FREEZE = ROOT / "experiments" / "freeze" / "experiment-freeze-v1.json"
ORIGINAL = (
    ROOT
    / "artifacts"
    / "phase06b"
    / "derived"
    / ORIGINAL_ATTEMPT_ID
    / "freeze-v1-raw-runs.provenance-repaired.jsonl"
)
ATTEMPT = "20261001T220000Z-abcdef123456"
COMMIT = "a" * 40


def _selection():
    errors, selection = validate_supplement_selection(
        plan_path=PLAN,
        freeze_path=FREEZE,
        original_rows_path=ORIGINAL,
    )
    assert errors == []
    assert selection is not None
    return selection


def _row(run: dict, *, attempt_id: str = ATTEMPT, status: str = "SUCCESS") -> dict:
    return {
        "attempt_id": attempt_id,
        "execution_origin": EXECUTION_ORIGIN,
        "freeze_id": "experiment-freeze-v1",
        "freeze_sha256": "0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b",
        "tested_git_commit": COMMIT,
        "run_id": run["run_id"],
        "provider": run["provider"],
        "scenario": run["scenario"],
        "repetition": run["repetition"],
        "namespace": run["namespace"],
        "operation_status": status,
        "downstream_decision_model_calls": 0,
        "rq3_calls": 0,
    }


def test_selector_returns_exact_ten_unique_openviking_runs() -> None:
    selection = _selection()
    assert len(selection.runs) == 10
    assert len(set(selection.run_ids)) == 10
    assert all(run["provider"] == "openviking" for run in selection.runs)
    assert "freeze-v1__openviking__S0__r2" not in selection.run_ids
    assert not any(run_id.endswith("r4") for run_id in selection.run_ids)


def test_attempt_mismatch_and_duplicate_namespace_fail_closed() -> None:
    selection = _selection()
    one = _row(selection.runs[0], attempt_id="20261001T220001Z-111111111111")
    errors = validate_supplement_rows(
        [one], selection=selection, attempt_id=ATTEMPT, tested_commit=COMMIT
    )
    assert errors == ["supplement row attempt ID does not match controller attempt ID"]
    first = _row(selection.runs[0])
    second = {**_row(selection.runs[1]), "namespace": first["namespace"]}
    errors = validate_supplement_rows(
        [first, second], selection=selection, attempt_id=ATTEMPT, tested_commit=COMMIT
    )
    assert "duplicate supplement raw namespaces" in errors
    assert "supplement row identity does not match validated plan" in errors


class FrozenOpenVikingFake(ReferenceMemoryAdapter):
    @property
    def provider_name(self) -> str:
        return "openviking"

    @property
    def provider_version(self) -> str:
        return "0.4.22"


def test_supplement_row_has_provenance_at_creation() -> None:
    selection = _selection()
    row = run_repetition(
        adapter=FrozenOpenVikingFake(),
        run=selection.runs[0],
        tested_git_commit=COMMIT,
        attempt_id=ATTEMPT,
        execution_origin=EXECUTION_ORIGIN,
    )
    assert row["attempt_id"] == ATTEMPT
    assert row["execution_origin"] == "SUPPLEMENT"


def test_diagnostic_failure_does_not_mutate_scientific_payload_and_service_exit_stops() -> None:
    selection = _selection()
    calls: list[str] = []
    emitted: list[dict] = []

    def run_once(run: dict) -> dict:
        calls.append(run["run_id"])
        row = _row(run, status="ERROR")
        emitted.append(copy.deepcopy(row))
        return row

    def capture(stage: str, run: dict | None) -> dict:
        raise PermissionError("diagnostics unavailable")

    execution = execute_supplement_runs(
        selection=selection,
        attempt_id=ATTEMPT,
        tested_commit=COMMIT,
        run_once=run_once,
        service_integrity=lambda: {
            "healthy": False,
            "process_alive": False,
            "exit_code": 137,
        },
        capture=capture,
    )
    assert calls == [selection.run_ids[0]]
    assert execution.rows[0] == emitted[0]
    assert len(execution.blocked) == 9
    assert all(item["status"] == "BLOCKED_NOT_EXECUTED" for item in execution.blocked)
    assert execution.completion == "SUPPLEMENT_PARTIAL"
    assert any(item["capture_status"] == "FAILURE" for item in execution.diagnostics)


def test_normal_error_continues_while_service_is_healthy_without_retry() -> None:
    selection = _selection()
    counts: dict[str, int] = {}

    def run_once(run: dict) -> dict:
        counts[run["run_id"]] = counts.get(run["run_id"], 0) + 1
        status = "ERROR" if run["run_id"] == selection.run_ids[0] else "SUCCESS"
        return _row(run, status=status)

    execution = execute_supplement_runs(
        selection=selection,
        attempt_id=ATTEMPT,
        tested_commit=COMMIT,
        run_once=run_once,
        service_integrity=lambda: {"healthy": True},
        capture=lambda stage, run: {"stage": stage},
    )
    assert execution.completion == "SUPPLEMENT_COMPLETE"
    assert len(execution.rows) == 10
    assert set(counts.values()) == {1}
    assert execution.blocked == ()


def test_combined_view_is_derived_and_retains_source_provenance(tmp_path: Path) -> None:
    selection = _selection()
    supplement = tmp_path / "supplement.jsonl"
    supplement.write_text(json.dumps(_row(selection.runs[0])) + "\n", encoding="utf-8")
    output = tmp_path / "combined.jsonl"
    manifest_path = tmp_path / "manifest.json"
    original_before = ORIGINAL.read_bytes()
    manifest = derive_combined_view(
        original_path=ORIGINAL,
        supplement_path=supplement,
        output_path=output,
        manifest_path=manifest_path,
    )
    assert ORIGINAL.read_bytes() == original_before
    assert hashlib.sha256(original_before).hexdigest() == DERIVED_RAW_SHA256
    assert manifest["artifact_kind"] == "DERIVED_ONLY"
    assert manifest["row_count"] == 33
    assert manifest["sources"][0]["attempt_ids"] == [ORIGINAL_ATTEMPT_ID]
    assert manifest["sources"][1]["attempt_ids"] == [ATTEMPT]
    combined = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert all(row["execution_origin"] == "ORIGINAL" for row in combined[:32])
    assert combined[-1]["execution_origin"] == "SUPPLEMENT"
    frozen_error = next(
        row for row in combined if row["run_id"] == "freeze-v1__openviking__S0__r2"
    )
    assert frozen_error["operation_status"] == "ERROR"
