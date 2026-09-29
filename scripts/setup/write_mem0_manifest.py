"""Write the local Phase 02A Mem0 reproducibility manifest."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from memlife.adapters.mem0 import phase02a_manifest_configuration  # noqa: E402
from memlife.config.paths import DataRootMode, resolve_data_root  # noqa: E402
from memlife.runner.manifest import (  # noqa: E402
    DEFAULT_PACKAGES,
    build_manifest,
    write_manifest,
)

PROVIDER_PACKAGES = (
    "mem0ai",
    "openai",
    "protobuf",
    "qdrant-client",
    "sentence-transformers",
    "torch",
)


def main() -> int:
    data_root = resolve_data_root(repo_root=REPO_ROOT)
    if data_root.mode is not DataRootMode.LOCAL:
        raise RuntimeError("Phase 02A manifest must use local data-root mode")
    details = phase02a_manifest_configuration()
    manifest = build_manifest(
        phase="02A",
        data_root=data_root,
        repo_root=REPO_ROOT,
        configuration=details,
        package_names=DEFAULT_PACKAGES + PROVIDER_PACKAGES,
        details=details,
    )
    destination = data_root.root / "artifacts" / "phase-02a-mem0-environment.json"
    write_manifest(manifest, destination)
    print(f"Manifest: {destination}")
    print(f"Git commit: {manifest.git_commit}")
    print(f"Configuration SHA-256: {manifest.config_hash_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
