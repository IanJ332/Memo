"""Reference calibration is the measurement oracle for Phase 06A."""

from memlife.adapters.reference import ReferenceMemoryAdapter
from memlife.models.authority import AuthorityExposureOutcome
from memlife.models.benchmark import NormalizedOutcome
from memlife.runner.calibration import (
    CALIBRATION_REPETITIONS,
    calibration_artifact,
    run_calibration_repetition,
)


def test_reference_calibration_runs_three_isolated_repetitions() -> None:
    runs = tuple(
        run_calibration_repetition(ReferenceMemoryAdapter(), repetition)
        for repetition in range(1, CALIBRATION_REPETITIONS + 1)
    )
    artifact = calibration_artifact(repo_base_commit="a" * 40, runs=runs + tuple(
        run.model_copy(update={"provider": "mem0", "provider_version": "2.2.1"})
        for run in runs
    ))
    assert len({run.namespace for run in runs}) == 3
    assert all(run.exact_visibility_outcome is NormalizedOutcome.CURRENT_ONLY for run in runs)
    assert all(run.authority_exposure_outcome is AuthorityExposureOutcome.AUTHORITATIVE_ONLY for run in runs)
    assert all(run.authority_ledger.entries[0].authoritative is False for run in runs)
    assert all(run.authority_ledger.entries[1].authoritative is True for run in runs)
    assert all("revoke" not in operation.native_operation.casefold() for run in runs for operation in run.native_provider_operations)
    assert artifact.hosted_model_calls == 0
    assert artifact.rq3_decision_calls == 0

