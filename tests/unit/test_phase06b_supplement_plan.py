from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "validate_phase06b_supplement.py"
PLAN = (
    REPO_ROOT
    / "experiments"
    / "supplements"
    / "phase06b-openviking-missing-runs-v1.json"
)


@pytest.fixture(scope="module")
def validator():
    spec = importlib.util.spec_from_file_location("phase06b_supplement_validator", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _mutated_plan(tmp_path: Path, mutate) -> Path:
    payload = json.loads(PLAN.read_text(encoding="utf-8"))
    mutate(payload)
    output = tmp_path / "plan.json"
    output.write_text(json.dumps(payload), encoding="utf-8")
    return output


def test_canonical_supplement_plan_is_exact_missing_complement(validator) -> None:
    assert validator.validate_supplement_plan(PLAN, repo_root=REPO_ROOT) == []


def test_executed_error_can_never_become_eligible(validator, tmp_path: Path) -> None:
    path = _mutated_plan(
        tmp_path,
        lambda payload: payload["eligible_run_ids"].append(
            "freeze-v1__openviking__S0__r2"
        ),
    )
    errors = validator.validate_supplement_plan(path, repo_root=REPO_ROOT)
    assert any("exact frozen never-executed complement" in error for error in errors)
    assert any("already executed" in error for error in errors)


def test_missing_run_cannot_be_dropped(validator, tmp_path: Path) -> None:
    path = _mutated_plan(tmp_path, lambda payload: payload["eligible_run_ids"].pop())
    errors = validator.validate_supplement_plan(path, repo_root=REPO_ROOT)
    assert any("exact frozen never-executed complement" in error for error in errors)


def test_design_cannot_silently_authorize_live_execution(validator, tmp_path: Path) -> None:
    path = _mutated_plan(
        tmp_path,
        lambda payload: payload["authorization"].update(
            live_execution_authorized=True, jetstream_action="UNSHELVE"
        ),
    )
    errors = validator.validate_supplement_plan(path, repo_root=REPO_ROOT)
    assert any("live/RQ3 unauthorized" in error for error in errors)


def test_instrumentation_cannot_be_reclassified_as_behavior_change(
    validator, tmp_path: Path
) -> None:
    path = _mutated_plan(
        tmp_path,
        lambda payload: payload["instrumentation"].update(
            classification="EXPERIMENTAL_BEHAVIOR"
        ),
    )
    errors = validator.validate_supplement_plan(path, repo_root=REPO_ROOT)
    assert any("instrumentation classification" in error for error in errors)


def test_same_lifecycle_retry_is_rejected(validator, tmp_path: Path) -> None:
    path = _mutated_plan(
        tmp_path,
        lambda payload: payload["stop_rule"].update(retry_same_lifecycle=True),
    )
    errors = validator.validate_supplement_plan(path, repo_root=REPO_ROOT)
    assert any("same-lifecycle retry" in error for error in errors)
