"""Validate the Phase 08A non-final Freeze-v2 design contract."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from memlife.runner.phase08a import (  # noqa: E402
    load_phase08a_draft,
    validate_phase08a_draft,
)

DEFAULT_DRAFT = (
    REPO_ROOT / "experiments" / "freeze" / "experiment-freeze-v2.draft.json"
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft", type=Path, default=DEFAULT_DRAFT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = load_phase08a_draft(args.draft)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    errors = validate_phase08a_draft(payload)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS experiment-freeze-v2.draft Phase08A contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
