"""Verify existing artifacts and expose the native import frontier; never acquire.

Run with the existing Phase 08D-7 repository SDK .venv, -I -B, and OS network
denial. No Hindsight module is imported, compiled, stubbed, or initialized.
READY describes artifact integrity only; the runtime gate remains BLOCKED.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import importlib
import importlib.metadata
import io
import json
import platform
from pathlib import Path
import sys
import sysconfig
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from phase08d7_offline_guard import activate, verify_denial, DENIED_EVENTS
from qualify_phase08d6_offline import cached_audit, verify_source, PREFIX, PIN
from verify_phase08d7_sdk import IMPORTS, check_rows
from acquire_phase08d7_sdk import PLAN_SHA256, validate_stage

KNOWN = {
    "aiohttp", "aiohappyeyeballs", "aiosignal", "attrs", "frozenlist",
    "multidict", "propcache", "yarl", "python-dotenv", "json-repair",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def imports(data: bytes, module: str) -> list[dict]:
    """Classify syntax by execution phase; missing module bodies stay UNKNOWN."""
    edges = []
    package = module if module.endswith(".__init__") else module.rsplit(".", 1)[0]
    package = package.removesuffix(".__init__")

    def walk(node, phase="IMPORT", guard=None):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            phase = "METHOD_OR_FUNCTION"
        if isinstance(node, ast.If) and ast.unparse(node.test) == "TYPE_CHECKING":
            phase = "TYPE_CHECKING_ONLY"
        if isinstance(node, ast.Try) and any(
            h.type is not None and "ImportError" in ast.unparse(h.type) for h in node.handlers
        ):
            guard = "IMPORTERROR_OPTIONAL"
        if isinstance(node, ast.Import):
            for alias in node.names:
                edges.append({"module": alias.name, "line": node.lineno,
                              "phase": phase, "guard": guard})
        if isinstance(node, ast.ImportFrom) and node.module != "__future__":
            if node.level:
                base = package.split(".")[:len(package.split(".")) - node.level + 1]
                target = ".".join(base + ([node.module] if node.module else []))
            else:
                target = node.module or ""
            # 'from .providers import Classes' requires the real package initializer.
            edges.append({"module": target, "line": node.lineno,
                          "phase": phase, "guard": guard})
        for child in ast.iter_child_nodes(node):
            walk(child, phase, guard)

    walk(ast.parse(data))
    return edges


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-cache", type=Path, required=True)
    parser.add_argument("--pinned-tree", type=Path, required=True)
    parser.add_argument("--metadata-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    activate()
    guard = verify_denial()
    start_events = len(DENIED_EVENTS)
    # D7's installer loader intentionally binds artifacts to its own worktree.
    # Reuse verifies the immutable plan and observed paths without rebinding it.
    plan_data = (ROOT / "manifests/phase-08d7-sdk-acquisition-plan.json").read_bytes()
    if digest(plan_data) != PLAN_SHA256:
        raise RuntimeError("STOP: immutable SDK acquisition plan changed")
    plan = json.loads(plan_data)
    runtime = Path(plan["runtime"])
    if Path(sys.prefix) != runtime or sys.prefix == sys.base_prefix or not sys.flags.isolated:
        raise RuntimeError("STOP: use existing isolated repository SDK .venv with -I")
    if (platform.python_version(), sys.platform, platform.machine()) != ("3.12.8", "darwin", "x86_64"):
        raise RuntimeError("STOP: target differs from the verified SDK artifact target")
    site = Path(sysconfig.get_path("purelib"))
    if (any(site.glob("*.pth")) or
            "include-system-site-packages = false" not in (runtime / "pyvenv.cfg").read_text()):
        raise RuntimeError("STOP: unexpected dependency inheritance")
    d7 = json.loads((ROOT / "manifests/phase-08d7-sdk-installation-qualification.json").read_bytes())
    staged = json.loads((Path(plan["wheelhouse"]).parent / "sdk-staged-wheels.json").read_bytes())
    validate_stage(plan, staged)
    expected = {x["name"]: x["version"] for x in staged["wheels"]}
    recorded = {x["name"]: (x["version"], x["sha256"], x["bytes"])
                for x in d7["packages"]}
    distributions = list(importlib.metadata.distributions())
    installed = {d.metadata["Name"].lower().replace("_", "-"): d for d in distributions}
    if len(distributions) != 16 or len(installed) != 16 or {n: d.version for n, d in installed.items()} != expected:
        raise RuntimeError("STOP: installed SDK inventory changed")
    sdk = []
    for artifact in staged["wheels"]:
        name = artifact["name"]
        if (artifact["version"], artifact["sha256"], artifact["bytes"]) != recorded[name]:
            raise RuntimeError("STOP: stage differs from tracked installation receipt")
        data = (Path(plan["wheelhouse"]) / artifact["filename"]).read_bytes()
        if digest(data) != artifact["sha256"] or len(data) != artifact["bytes"]:
            raise RuntimeError("STOP: SDK wheel changed")
        distribution = installed[name]

        def read_installed(path):
            target = Path(distribution.locate_file(path)).resolve()
            if not target.is_relative_to(runtime):
                raise RuntimeError("STOP: installed RECORD escapes SDK environment")
            return target.read_bytes()

        installed_count = check_rows(csv.reader(io.StringIO(distribution.read_text("RECORD"))),
                                     read_installed, name)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            record_paths = [n for n in archive.namelist()
                            if n.count("/") == 1 and n.endswith(".dist-info/RECORD")]
            if len(record_paths) != 1:
                raise RuntimeError("STOP: ambiguous wheel RECORD")
            record = archive.read(record_paths[0]).decode()
            wheel_count = check_rows(csv.reader(io.StringIO(record)), archive.read, name)
            for path, value, _ in csv.reader(io.StringIO(record)):
                if value and read_installed(path) != archive.read(path):
                    raise RuntimeError("STOP: installed bytes differ from SDK wheel")
        module = importlib.import_module(IMPORTS[name])
        if not Path(module.__file__).resolve().is_relative_to(runtime):
            raise RuntimeError("STOP: SDK import escaped isolated environment")
        sdk.append({**artifact, "status": "READY_VERIFIED_EXISTING_SDK",
                    "requires_dist": distribution.requires or [],
                    "installed_record_files": installed_count, "wheel_record_files": wheel_count})

    records, source = cached_audit(args.source_cache, args.pinned_tree)
    tree = json.loads(args.pinned_tree.read_bytes())
    indexed = {x["path"]: x for x in tree["tree"] if x["type"] == "blob"}
    # Newly inspected stage is required by the provider, not a worker entrypoint.
    item = indexed[PREFIX + "worker/stage.py"]
    data = (args.source_cache / "stage.py").read_bytes()
    records.append(verify_source(item["path"], data,
                                 {"git_blob_sha1": item["sha"], "byte_count": item["size"]}))
    source["worker/stage.py"] = data
    available = {"hindsight_api." + p.removesuffix(".py").replace("/", "."): data
                 for p, data in source.items()}
    graph = {name: imports(data, name) for name, data in available.items()}

    def source_path(module):
        stem = "hindsight-api-slim/" + module.replace(".", "/")
        for p in (stem + ".py", stem + "/__init__.py"):
            if p in indexed:
                return p
        raise RuntimeError(f"STOP: unresolved module in pinned tree: {module}")

    # Bounded frontier: mandatory imports in cached provider/helper bodies,
    # actual package initializers, and tracing needed by successful native calls.
    pending = ["hindsight_api.engine.providers.openai_compatible_llm",
               "hindsight_api.tracing"]
    visited, frontier = set(), {}
    while pending:
        module = pending.pop()
        if module in visited:
            continue
        visited.add(module)
        path = source_path(module)
        key = module + ".__init__" if path.endswith("/__init__.py") else module
        if key not in available:
            frontier[path] = indexed[path]
        else:
            pending.extend(e["module"] for e in graph[key]
                           if e["module"].startswith("hindsight_api")
                           and e["phase"] == "IMPORT" and e["guard"] is None)
        parts = module.split(".")
        for end in range(1, len(parts)):
            parent = ".".join(parts[:end])
            init = "hindsight-api-slim/" + parent.replace(".", "/") + "/__init__.py"
            if init in indexed and parent not in visited:
                pending.append(parent)
    sources_plan = [{"path": p, "git_blob_sha1": x["sha"], "bytes": x["size"],
                     "url": f"https://raw.githubusercontent.com/vectorize-io/hindsight/{PIN}/{p}",
                     "status": "BLOCKED_SOURCE_BYTES_ABSENT", "sha256": None}
                    for p, x in sorted(frontier.items())]
    metadata = []
    for name, blob, size in (("pyproject.toml", "e656821ca96c76b84a1d1cb1c7eb592f7f3b2563", 15638),
                             ("uv.lock", "cd9687ebaa9a749e506ed396fc95c6f48925072a", 999593)):
        data = (args.metadata_root / name).read_bytes()
        if hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() != blob or len(data) != size:
            raise RuntimeError("STOP: dependency metadata identity changed")
        metadata.append({"path": name, "git_blob_sha1": blob, "sha256": digest(data), "bytes": size})
    lock = tomllib.loads((args.metadata_root / "uv.lock").read_text())
    inventory = json.loads((ROOT / "manifests/phase-08d7-dependency-preparation.json").read_bytes())
    package_rows = {x["name"]: x for x in inventory["packages"]}
    gaps = []
    for name in sorted(KNOWN):
        row = package_rows[name]
        local = []
        for artifact in row["local_matching_wheels"]:
            data = Path(artifact["path"]).read_bytes()
            if digest(data) != artifact["sha256"] or len(data) != artifact["bytes"]:
                raise RuntimeError("STOP: local candidate wheel changed")
            local.append(artifact)
        candidates = row["compatible_upstream_wheels"]
        choices = [a for a in candidates if a["filename"].endswith("py3-none-any.whl")]
        if not choices:
            choices = [a for a in candidates if "cp312-cp312" in a["filename"]
                       and a["filename"].endswith("x86_64.whl")]
        if len(choices) != 1:
            raise RuntimeError("STOP: ambiguous restricted wheel candidate")
        gaps.append({"name": name, "version": row["version"],
                     "lock_dependencies": next(x.get("dependencies", []) for x in lock["package"]
                                               if x["name"] == name and x["version"] == row["version"]),
                     "status": "READY_LOCAL_WHEEL_NOT_INSTALLED" if local else "BLOCKED_NO_MATCHING_LOCAL_WHEEL",
                     "local_verified_wheels": local, "candidate_wheel": choices[0],
                     "installation_authorized": False})
    crypto = next(x for x in lock["package"] if x["name"] == "cryptography")
    receipt = {"phase": "08D-8", "base_commit": "e07de9832572a910e7055d2df582b919146c35fd",
               "upstream_commit": PIN, "evidence_class": "VERIFIED_ARTIFACTS_AND_PARTIAL_IMPORT_CLOSURE",
               "guard": guard, "metadata": metadata, "verified_cached_sources": records,
               "cached_import_graph": {n: graph[n] for n in sorted(graph) if n in visited or n.removesuffix(".__init__") in visited},
               "missing_source_acquisition_frontier": sources_plan,
               "source_frontier_total_bytes": sum(x["bytes"] for x in sources_plan),
               "sdk_runtime_observed_path": str(runtime), "sdk_packages": sdk,
               "known_additional_dependency_closure": gaps,
               "closure_complete": False, "uninspected_source_dependencies": "UNKNOWN",
               "cryptography": {"version": crypto["version"],
                    "intel_macos_wheels_in_pinned_lock": len(package_rows["cryptography"]["compatible_upstream_wheels"]),
                    "sdk_required": False, "native_import_required": "UNKNOWN_PENDING_SOURCE_FRONTIER",
                    "workaround_proposed": False},
               "acquisition_installation_or_build_performed": False,
               "native_import_or_construction_executed": False,
               "import_socket_or_dns_attempts": len(DENIED_EVENTS) - start_events,
               "actual_socket_transmissions": 0,
               "D3": "PARTIAL", "D4": "BLOCKED", "D5": "PARTIAL", "runtime_gate": "BLOCKED_UNCHANGED"}
    if len(DENIED_EVENTS) != start_events or any(n.startswith("hindsight") for n in sys.modules):
        raise RuntimeError("STOP: unexpected networking or native import")
    with args.output.open("x") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"PASS: 16 SDK identities/imports; {len(records)} pinned cached sources; "
          f"{len(sources_plan)} missing source files. Native qualification BLOCKED.")


if __name__ == "__main__":
    main()
