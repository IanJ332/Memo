#!/usr/bin/env python3
"""Thin command entrypoint for frozen Phase 06B planning and validation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from memlife.runner.storage_batch import (  # noqa: E402
    aggregate_runs,
    canonical_json,
    generate_run_plan,
    read_jsonl,
    residual_index,
    validate_artifacts,
    write_run_plan,
)

DEFAULT_FREEZE = REPO_ROOT / "experiments" / "freeze" / "experiment-freeze-v1.json"
DEFAULT_ROOT = REPO_ROOT / "artifacts" / "phase06b"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan")
    plan.add_argument("--freeze", type=Path, default=DEFAULT_FREEZE)
    plan.add_argument("--output", type=Path, default=DEFAULT_ROOT / "planned-runs.json")

    aggregate = commands.add_parser("aggregate")
    aggregate.add_argument("--freeze", type=Path, default=DEFAULT_FREEZE)
    aggregate.add_argument("--raw", type=Path, required=True)
    aggregate.add_argument("--aggregate", type=Path, required=True)
    aggregate.add_argument("--residual", type=Path, required=True)

    validate = commands.add_parser("validate")
    validate.add_argument("--freeze", type=Path, default=DEFAULT_FREEZE)
    validate.add_argument("--raw", type=Path, required=True)
    validate.add_argument("--aggregate", type=Path, required=True)
    validate.add_argument("--residual", type=Path, required=True)
    validate.add_argument("--attempt-id")
    validate.add_argument("--tested-commit")
    validate.add_argument("--require-complete", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "plan":
        plan = write_run_plan(args.freeze, args.output)
        print(
            f"PASS plan supported={plan['expected_executable_count']} "
            f"unsupported={plan['unsupported_cell_count']} output={args.output}"
        )
        return 0

    plan = generate_run_plan(args.freeze)
    rows = read_jsonl(args.raw)
    if args.command == "aggregate":
        aggregate = aggregate_runs(plan, rows)
        residual = residual_index(plan, rows, aggregate)
        args.aggregate.parent.mkdir(parents=True, exist_ok=True)
        args.residual.parent.mkdir(parents=True, exist_ok=True)
        args.aggregate.write_text(canonical_json(aggregate), encoding="utf-8")
        args.residual.write_text(canonical_json(residual), encoding="utf-8")
        print(
            f"PASS aggregate runs={len(rows)} residual_runs={residual['residual_run_count']}"
        )
        return 0

    aggregate = json.loads(args.aggregate.read_text(encoding="utf-8"))
    residual = json.loads(args.residual.read_text(encoding="utf-8"))
    errors = validate_artifacts(
        plan=plan,
        raw_runs=rows,
        aggregate=aggregate,
        residual=residual,
        require_complete=args.require_complete,
        expected_attempt_id=args.attempt_id,
        expected_tested_commit=args.tested_commit,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"PASS artifacts runs={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
