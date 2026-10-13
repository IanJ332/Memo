"""Read cached pinned source and dependency metadata; NEVER initialize a provider.

This receipt is a static audit / availability record, not installed-runtime proof.
No SDK imports, network, upstream patches, or installation are performed.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
PIN = "f8950b0c07d9e34c76493dba802bb309f0ce60fd"
PREFIX = "hindsight-api-slim/hindsight_api/"
DEPENDENCIES = {
    "hindsight_api": "hindsight-api-slim",
    "openai": "openai",
    "httpx": "httpx",
    "httpcore": "httpcore",
    "aiohttp": "aiohttp",
}
ALIASES = {
    "main.py": "main.py",
    "worker/main.py": "worker_main.py",
    "worker/poller.py": "poller.py",
    "engine/providers/__init__.py": "providers_init.py",
}
EXTRA_SOURCES = (
    "engine/llm_interface.py",
    "engine/retain/orchestrator.py",
    "engine/task_backend.py",
)


def dependency_inventory() -> dict:
    """Inspect top-level import availability and distribution metadata only."""
    result = {}
    for module, distribution in DEPENDENCIES.items():
        try:
            version = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            version = None
        result[module] = {
            "import_available": importlib.util.find_spec(module) is not None,
            "distribution": distribution,
            "version": version,
        }
    return result


def verify_source(path: str, data: bytes, expected: dict) -> dict:
    blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    digest = hashlib.sha256(data).hexdigest()
    if (blob != expected["git_blob_sha1"] or len(data) != expected["byte_count"]
            or ("sha256" in expected and digest != expected["sha256"])):
        raise ValueError(f"pinned source identity mismatch: {path}")
    ast.parse(data, filename=path)  # Parse only. Never compile/import upstream.
    return {"path": path, "git_blob_sha1": blob, "sha256": digest,
            "byte_count": len(data)}


def cached_audit(cache: Path, tree_path: Path) -> tuple[list[dict], dict[str, bytes]]:
    baseline = json.loads((ROOT / "manifests/phase-08d5-upstream-source-audit.json").read_bytes())
    tree_bytes = tree_path.read_bytes()
    tree = json.loads(tree_bytes)
    if (baseline["upstream_commit"] != PIN or tree.get("sha") != PIN
            or tree.get("truncated") is not False
            or hashlib.sha256(tree_bytes).hexdigest() != baseline["git_tree_response_sha256"]):
        raise ValueError("pinned non-truncated tree identity mismatch")
    indexed = {item["path"]: item for item in tree["tree"]}
    expected = list(baseline["files"])
    for relative in EXTRA_SOURCES:
        item = indexed[PREFIX + relative]
        expected.append({"path": item["path"], "git_blob_sha1": item["sha"],
                         "byte_count": item["size"]})
    records, sources = [], {}
    for item in expected:
        path = item["path"]
        tree_item = indexed[path]
        if tree_item["type"] != "blob" or tree_item["sha"] != item["git_blob_sha1"]:
            raise ValueError(f"manifest/tree mismatch: {path}")
        relative = path.removeprefix(PREFIX)
        local_name = ALIASES.get(relative, Path(relative).name)
        data = (cache / local_name).read_bytes()
        records.append(verify_source(path, data, item))
        sources[relative] = data
    return records, sources


def static_observations(sources: dict[str, bytes]) -> dict:
    """Enumerate syntactic sites; this is deliberately not a completeness proof."""
    provider = ast.parse(sources["engine/providers/openai_compatible_llm.py"])
    calls = []
    for node in ast.walk(provider):
        if isinstance(node, ast.Call):
            name = ast.unparse(node.func)
            if name.startswith("self._client.") or name == "session.post":
                calls.append({"line": node.lineno, "call": name})
    factory = ast.parse(sources["engine/llm_wrapper.py"])
    function = next(n for n in factory.body if isinstance(n, ast.FunctionDef)
                    and n.name == "create_llm_provider")
    labels = set()
    for node in ast.walk(function):
        if isinstance(node, ast.Compare) and ast.unparse(node.left) == "provider_lower":
            for comparator in node.comparators:
                labels.update(n.value for n in ast.walk(comparator)
                              if isinstance(n, ast.Constant) and isinstance(n.value, str))
    return {"qualification": "STATIC_SYNTAX_ONLY_NOT_RUNTIME_COVERAGE",
            "openai_compatible_client_call_sites": sorted(calls, key=lambda x: x["line"]),
            "factory_provider_labels": sorted(labels)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-cache", type=Path, required=True)
    parser.add_argument("--pinned-tree", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # Only a repository-owned venv; no system/global interpreter fallback.
    if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
        parser.error("use this repository's .venv interpreter")
    records, sources = cached_audit(args.source_cache, args.pinned_tree)
    dependencies = dependency_inventory()
    missing = [module for module, item in dependencies.items()
               if not item["import_available"] or item["version"] is None]
    receipt = {
        "phase": "08D-6", "base_commit": "58ab52dcd8e628400533173eac08ed5b1ea42faa",
        "upstream_commit": PIN, "python_version": sys.version.split()[0],
        "qualification": "STATIC_SOURCE_AND_LOCAL_DEPENDENCY_AVAILABILITY_ONLY",
        "dependencies": dependencies, "missing_runtime_dependencies": missing,
        "installed_runtime_proof": False, "sdk_transport_probes_executed": False,
        "runtime_blocker": ("MISSING_INSTALLED_RUNTIME_AND_SDK_TRANSPORT_DEPENDENCIES"
                            if missing else "RUNTIME_NOT_EXECUTED_BY_STATIC_AUDIT"),
        "readiness": "BLOCKED", "sources": records,
        "observations": static_observations(sources),
    }
    # Engineering audit output, separate from immutable empirical attempts.
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"readiness": "BLOCKED", "verified_source_files": len(records),
                      "missing_runtime_dependencies": missing,
                      "sdk_transport_probes_executed": False}))
    return 0  # Audit completed; readiness is explicitly BLOCKED in the receipt.


if __name__ == "__main__":
    raise SystemExit(main())
