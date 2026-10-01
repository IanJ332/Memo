from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_DOCS = REPO_ROOT / "docs" / "project"
PLAN = (
    REPO_ROOT
    / "experiments"
    / "supplements"
    / "phase06b-openviking-missing-runs-v1.json"
)


def test_bootstrap_reading_order_exists() -> None:
    agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    ordered = [
        "docs/project/MODEL_HANDOFF.md",
        "docs/project/PROJECT_STATE.md",
        "docs/project/DEBUGGING_LEDGER.md",
    ]
    positions = [agents.index(item) for item in ordered]
    assert positions == sorted(positions)
    for relative in ordered:
        assert (REPO_ROOT / relative).is_file()


def test_cold_agent_can_answer_required_bootstrap_questions() -> None:
    handoff = (PROJECT_DOCS / "MODEL_HANDOFF.md").read_text(encoding="utf-8")
    state = (PROJECT_DOCS / "PROJECT_STATE.md").read_text(encoding="utf-8")
    ledger = (PROJECT_DOCS / "EXPERIMENT_LEDGER.md").read_text(encoding="utf-8")
    debugging = (PROJECT_DOCS / "DEBUGGING_LEDGER.md").read_text(encoding="utf-8")

    assert "cross-provider lifecycle security and authority" in handoff
    assert "Retrieved != Authoritative" in handoff
    assert "phase-06b-storage-batch" in handoff
    assert "42 planned; 32 executed; 31 success; 1 error; 10 never executed" in handoff
    assert "SHELVED" in handoff and "live execution is not authorized" in handoff
    assert "Next authorized action" in handoff and "local Phase 06B-S0" in handoff
    assert "Phase 06B-S0" in state
    assert "experiment-freeze-v1" in ledger
    assert "0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b" in ledger
    assert "freeze-v1__openviking__S0__r2" in ledger
    assert "Never rerun, replace, or relabel it" in ledger
    assert "UNKNOWN" in handoff
    for heading in (
        "Freeze CRLF/LF mismatch",
        "Virtualenv identity false positive",
        "Artifact overwrite risk",
        "Missing attempt_id in raw rows",
        "Initial remote HEAD ambiguity",
        "OpenViking process crash observation",
    ):
        assert heading in debugging


def test_missing_run_ids_agree_across_plan_protocol_and_ledger() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    protocol = (
        REPO_ROOT
        / "docs"
        / "experiments"
        / "PHASE_06B_OPENVIKING_SUPPLEMENT_PROTOCOL.md"
    ).read_text(encoding="utf-8")
    ledger = (PROJECT_DOCS / "EXPERIMENT_LEDGER.md").read_text(encoding="utf-8")
    assert len(plan["eligible_run_ids"]) == 10
    for run_id in plan["eligible_run_ids"]:
        assert protocol.count(run_id) == 1
        assert ledger.count(run_id) == 1
