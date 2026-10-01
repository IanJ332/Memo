"""Create a provenance-retaining derived Phase 06B original+supplement view."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from memlife.runner.phase06b_supplement import derive_combined_view  # noqa: E402

DEFAULT_ORIGINAL = (
    REPO_ROOT
    / "artifacts"
    / "phase06b"
    / "derived"
    / "20261001T183940Z-1fc4c4929532"
    / "freeze-v1-raw-runs.provenance-repaired.jsonl"
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, default=DEFAULT_ORIGINAL)
    parser.add_argument("--supplement", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args(argv)
    manifest = derive_combined_view(
        original_path=args.original,
        supplement_path=args.supplement,
        output_path=args.output,
        manifest_path=args.manifest,
    )
    print(
        "PASS combined-derived "
        f"rows={manifest['row_count']} sources={len(manifest['sources'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
