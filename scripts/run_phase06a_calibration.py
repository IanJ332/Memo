"""Generate the tracked, LLM-free Phase 06A calibration artifact."""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from memlife.adapters.reference import ReferenceMemoryAdapter
from memlife.runner.calibration import (
    CALIBRATION_REPETITIONS,
    calibration_artifact,
    run_calibration_repetition,
)

BASE_COMMIT = "1436b5537abdef35f0bbf60bb144dc5ffd9593fa"
OUTPUT = REPO_ROOT / "artifacts" / "calibration" / "mem0-calibration-v1.json"


def main() -> int:
    reference_runs = tuple(
        run_calibration_repetition(ReferenceMemoryAdapter(), repetition)
        for repetition in range(1, CALIBRATION_REPETITIONS + 1)
    )

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["MEMLIFE_MEM0_PROVIDER_INSTANCE"] = "phase06a-calibration-v1"
    from memlife.adapters.mem0 import Mem0MemoryAdapter

    mem0 = Mem0MemoryAdapter.from_runtime(REPO_ROOT)
    hosted_calls: list[object] = []

    def reject_hosted_call(*args: object, **kwargs: object) -> None:
        hosted_calls.append((args, kwargs))
        raise RuntimeError("Phase 06A calibration forbids hosted model calls")

    mem0.native_memory.llm.generate_response = reject_hosted_call
    try:
        mem0_runs = tuple(
            run_calibration_repetition(mem0, repetition)
            for repetition in range(1, CALIBRATION_REPETITIONS + 1)
        )
    finally:
        mem0.close()
    if hosted_calls:
        raise RuntimeError("Mem0 attempted a hosted model call")

    artifact = calibration_artifact(
        repo_base_commit=BASE_COMMIT,
        runs=reference_runs + mem0_runs,
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(artifact.canonical_json(), encoding="utf-8", newline="")
    print(OUTPUT.relative_to(REPO_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

