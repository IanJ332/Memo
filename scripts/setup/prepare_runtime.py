"""Create the safe MemLife runtime directory layout."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from memlife.config.paths import prepare_runtime, resolve_data_root  # noqa: E402


def main() -> int:
    config = resolve_data_root(repo_root=REPO_ROOT)
    created = prepare_runtime(config)
    print(f"MemLife data root: {config.root}")
    print(f"Selection mode: {config.mode.value}")
    for path in created:
        print(f"Ready: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
