"""Small local CLI for the Phase 03 lifecycle benchmark."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from memlife.adapters.reference import ReferenceMemoryAdapter
from memlife.config.paths import resolve_data_root
from memlife.models.benchmark import serialize_results
from memlife.runner.lifecycle import run_suite
from memlife.scenarios.canonical import canonical_scenarios


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("reference", "mem0"), required=True)
    parser.add_argument("--output", type=Path)
    return parser


def _adapter(provider: str):
    if provider == "reference":
        return ReferenceMemoryAdapter()
    if provider == "mem0":
        from memlife.adapters.mem0 import Mem0MemoryAdapter

        return Mem0MemoryAdapter.from_local_runtime(Path.cwd())
    raise ValueError(f"unknown provider {provider!r}")


def _validated_output(path: Path) -> Path:
    runtime = resolve_data_root(repo_root=Path.cwd()).root.resolve()
    destination = path.resolve()
    try:
        destination.relative_to(runtime)
    except ValueError as exc:
        raise ValueError("benchmark output must be below the local runtime directory") from exc
    return destination


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    adapter = _adapter(args.provider)
    try:
        document = serialize_results(run_suite(adapter, canonical_scenarios()))
    finally:
        close = getattr(adapter, "close", None)
        if callable(close):
            close()

    if args.output is None:
        sys.stdout.write(document)
    else:
        destination = _validated_output(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(document, encoding="utf-8")
        print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
