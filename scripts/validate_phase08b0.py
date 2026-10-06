"""Validate the local-only Phase 08B-0 Honcho acceptance preflight."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from memlife.runner.phase08b0 import (  # noqa: E402
    load_json_object,
    validate_live_manifest,
    validate_probe_plan,
)

PLAN = REPO_ROOT / "experiments" / "acceptance" / "phase08b0-honcho-probe-plan.json"
MANIFEST = REPO_ROOT / "manifests" / "phase-08b1-honcho-live-acceptance.json"


def main() -> int:
    errors: list[str] = []
    for path, validator in (
        (PLAN, validate_probe_plan),
        (MANIFEST, validate_live_manifest),
    ):
        try:
            payload = load_json_object(path)
        except (OSError, ValueError) as exc:
            errors.append(f"{path}: {exc}")
            continue
        errors.extend(validator(payload))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS Phase08B-0 Honcho acceptance preflight contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
