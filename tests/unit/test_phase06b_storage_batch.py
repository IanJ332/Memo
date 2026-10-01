"""Frozen Phase 06B plan, execution-record, aggregate, and residual gates."""

from __future__ import annotations

import json
from pathlib import Path

from memlife.adapters.reference import ReferenceMemoryAdapter
from memlife.runner.storage_batch import (
    FREEZE_SHA256,
    aggregate_runs,
    contains_sensitive_key,
    generate_run_plan,
    residual_index,
    run_repetition,
    sanitize_value,
    validate_artifacts,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FREEZE = REPO_ROOT / "experiments" / "freeze" / "experiment-freeze-v1.json"
ATTEMPT_ID = "20261001T183940Z-1fc4c4929532"


class FrozenMem0Fake(ReferenceMemoryAdapter):
    @property
    def provider_name(self) -> str:
        return "mem0-frozen-fake"

    @property
    def provider_version(self) -> str:
        return "2.2.1"


def _run_spec(plan: dict, provider: str, scenario: str, repetition: int = 1) -> dict:
    return next(
        item
        for item in plan["runs"]
        if item["provider"] == provider
        and item["scenario"] == scenario
        and item["repetition"] == repetition
    )


def test_plan_is_generated_in_exact_frozen_order_and_cardinality() -> None:
    plan = generate_run_plan(FREEZE)
    assert plan["freeze_sha256"] == FREEZE_SHA256
    assert plan["expected_executable_count"] == 42
    assert plan["unsupported_cell_count"] == 4
    assert [item["provider"] for item in plan["runs"][:12]] == ["mem0"] * 12
    assert plan["runs"][0]["run_id"] == "freeze-v1__mem0__S0__r1"
    assert plan["runs"][0]["namespace"] == "memlife-freeze-v1-mem0-S0-r1"
    assert plan["runs"][-1]["run_id"] == "freeze-v1__openviking__S4__r3"
    assert [(item["provider"], item["scenario"]) for item in plan["unsupported_cells"]] == [
        ("mem0", "S4"),
        ("mem0", "S5"),
        ("openviking", "S1"),
        ("openviking", "S5"),
    ]
    assert len({item["run_id"] for item in plan["runs"]}) == 42
    assert len({item["namespace"] for item in plan["runs"]}) == 42


def test_supported_repetition_records_independent_metrics_and_zero_calls() -> None:
    plan = generate_run_plan(FREEZE)
    result = run_repetition(
        adapter=FrozenMem0Fake(),
        run=_run_spec(plan, "mem0", "S1"),
        tested_git_commit="a" * 40,
        attempt_id=ATTEMPT_ID,
    )
    assert result["attempt_id"] == ATTEMPT_ID
    assert result["run_id"] == "freeze-v1__mem0__S1__r1"
    assert result["downstream_decision_model_calls"] == 0
    assert result["rq3_calls"] == 0
    assert result["filter_decision"] is None
    assert result["downstream_model"] is None
    assert result["tool_action"] is None
    assert result["authority_ledger"]["entries"][0]["authoritative"] is False
    assert result["authority_ledger"]["entries"][1]["authoritative"] is True
    assert not contains_sensitive_key(result)


def test_aggregate_preserves_inconsistency_and_residual_queue() -> None:
    plan = generate_run_plan(FREEZE)
    rows = []
    for repetition in range(1, 4):
        row = run_repetition(
            adapter=FrozenMem0Fake(),
            run=_run_spec(plan, "mem0", "S0", repetition),
            tested_git_commit="a" * 40,
            attempt_id=ATTEMPT_ID,
        )
        rows.append(row)
    rows[1] = {
        **rows[1],
        "exact_visibility_outcome": "ABSENT",
        "authority_exposure_outcome": "NONE",
    }
    aggregate = aggregate_runs(plan, rows)
    cell = next(
        item
        for item in aggregate["cells"]
        if item["provider"] == "mem0" and item["scenario"] == "S0"
    )
    assert cell["inconsistent"] is True
    assert cell["residual"] is True
    assert cell["exact_outcome_counts"] == {"ABSENT": 1, "CURRENT_ONLY": 2}
    queue = residual_index(plan, rows, aggregate)
    assert queue["residual_run_count"] == 3
    assert queue["candidate_cells"] == [{"provider": "mem0", "scenario": "S0"}]
    assert all(
        "the three frozen repetitions disagree about normalized authority exposure"
        in item["advancement_reasons"]
        for item in queue["candidates"]
    )


def test_unsupported_cells_are_aggregate_facts_not_fake_runs() -> None:
    plan = generate_run_plan(FREEZE)
    aggregate = aggregate_runs(plan, [])
    unsupported = [item for item in aggregate["cells"] if item["capability"] == "UNSUPPORTED"]
    assert len(unsupported) == 4
    assert all(item["executed_repetitions"] == 0 for item in unsupported)
    assert all(item["supported_repetitions"] == 0 for item in unsupported)


def test_sanitization_removes_secret_keys_and_artifact_validation_recomputes() -> None:
    sanitized = sanitize_value(
        {
            "status": "PASS",
            "api_key": "do-not-keep",
            "nested": {"password": "do-not-keep", "endpoint": "127.0.0.1"},
        }
    )
    assert sanitized == {"nested": {"endpoint": "127.0.0.1"}, "status": "PASS"}
    assert not contains_sensitive_key(sanitized)

    plan = generate_run_plan(FREEZE)
    aggregate = aggregate_runs(plan, [])
    residual = residual_index(plan, [], aggregate)
    assert validate_artifacts(
        plan=plan,
        raw_runs=[],
        aggregate=aggregate,
        residual=residual,
        require_complete=False,
    ) == []
    assert json.loads(json.dumps(plan))["expected_executable_count"] == 42


def test_artifact_validation_fails_closed_on_attempt_id_mismatch() -> None:
    plan = generate_run_plan(FREEZE)
    row = run_repetition(
        adapter=FrozenMem0Fake(),
        run=_run_spec(plan, "mem0", "S0"),
        tested_git_commit="a" * 40,
        attempt_id=ATTEMPT_ID,
    )
    aggregate = aggregate_runs(plan, [row])
    residual = residual_index(plan, [row], aggregate)
    errors = validate_artifacts(
        plan=plan,
        raw_runs=[row],
        aggregate=aggregate,
        residual=residual,
        require_complete=False,
        expected_attempt_id="20261001T190000Z-aaaaaaaaaaaa",
        expected_tested_commit="a" * 40,
    )
    assert errors == ["raw result attempt ID does not match controller attempt ID"]
