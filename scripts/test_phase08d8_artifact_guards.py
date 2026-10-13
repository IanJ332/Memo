"""Offline negative controls for real cached artifacts, with no provider fakes.

Use the SDK repository .venv with -I -B under the deny-network OS sandbox.
Tamper only temporary copies; original source, metadata and receipts stay intact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-cache", type=Path, required=True)
    parser.add_argument("--pinned-tree", type=Path, required=True)
    parser.add_argument("--metadata-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source_files = list(args.source_cache.glob("*.py"))
    protected = source_files + [args.pinned_tree, args.metadata_root / "pyproject.toml",
                                args.metadata_root / "uv.lock"]
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    results = []
    with tempfile.TemporaryDirectory(prefix="phase08d8-guards-") as directory:
        temporary = Path(directory)

        def reject(name, cache, tree, metadata, expected, existing=False):
            output = temporary / (name + ".json")
            if existing:
                output.write_bytes(b"immutable receipt sentinel\n")
            result = subprocess.run(
                [sys.executable, "-I", "-B", str(ROOT / "scripts/prepare_phase08d8_native.py"),
                 "--source-cache", str(cache), "--pinned-tree", str(tree),
                 "--metadata-root", str(metadata), "--output", str(output)],
                env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0 or expected not in result.stderr:
                raise RuntimeError(f"negative control did not fail as expected: {name}")
            if existing:
                if output.read_bytes() != b"immutable receipt sentinel\n":
                    raise RuntimeError("existing receipt overwritten")
            elif output.exists():
                raise RuntimeError("failed verification published a receipt")
            results.append({"name": name, "status": "PASS", "expected_rejection": expected})

        copied = temporary / "source"
        copied.mkdir()
        for path in source_files:
            shutil.copyfile(path, copied / path.name)
        with (copied / "openai_compatible_llm.py").open("ab") as stream:
            stream.write(b"\n# deliberate temporary identity mismatch\n")
        reject("source_identity_mismatch", copied, args.pinned_tree, args.metadata_root,
               "pinned source identity mismatch")
        tree_copy = temporary / "tree.json"
        tree_copy.write_bytes(args.pinned_tree.read_bytes() + b"\n")
        reject("tree_identity_mismatch", args.source_cache, tree_copy, args.metadata_root,
               "pinned non-truncated tree identity mismatch")
        metadata_copy = temporary / "metadata"
        metadata_copy.mkdir()
        for name in ("pyproject.toml", "uv.lock"):
            shutil.copyfile(args.metadata_root / name, metadata_copy / name)
        with (metadata_copy / "pyproject.toml").open("ab") as stream:
            stream.write(b"\n# deliberate temporary identity mismatch\n")
        reject("metadata_identity_mismatch", args.source_cache, args.pinned_tree, metadata_copy,
               "dependency metadata identity changed")
        reject("existing_receipt_preserved", args.source_cache, args.pinned_tree, args.metadata_root,
               "FileExistsError", existing=True)
    if before != {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}:
        raise RuntimeError("original artifacts changed")
    with args.output.open("x") as stream:
        json.dump({"phase": "08D-8", "tests": results, "original_artifact_hashes_unchanged": True,
                   "native_calls": 0, "runtime_gate": "BLOCKED_UNCHANGED"}, stream,
                  indent=2, sort_keys=True)
        stream.write("\n")
    print("PASS: 4 artifact rejection controls; original artifacts unchanged; native calls 0")


if __name__ == "__main__":
    main()
