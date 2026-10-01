"""Run all three Phase 06A calibration repetitions through local Mem0."""

import pytest

from memlife.adapters.mem0 import Mem0MemoryAdapter
from memlife.runner.calibration import (
    CALIBRATION_REPETITIONS,
    run_calibration_repetition,
)

pytestmark = pytest.mark.mem0_integration


def test_mem0_calibration_runs_three_isolated_repetitions(
    mem0_adapter: Mem0MemoryAdapter,
) -> None:
    runs = tuple(
        run_calibration_repetition(mem0_adapter, repetition)
        for repetition in range(1, CALIBRATION_REPETITIONS + 1)
    )
    assert len(runs) == 3
    assert len({run.namespace for run in runs}) == 3
    assert all(run.operation_status.value == "SUCCESS" for run in runs)
    assert all(run.rq3_decision_calls == 0 for run in runs)
    assert all(
        run.native_provider_operations[1].native_operation
        == "Memory.update(same UUID)"
        for run in runs
    )
    assert all(
        "revoke" not in operation.native_operation.casefold()
        for run in runs
        for operation in run.native_provider_operations
    )
    assert mem0_adapter._phase02a_llm_calls == []  # type: ignore[attr-defined]

