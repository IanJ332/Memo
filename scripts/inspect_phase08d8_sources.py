"""Static-only recomputation from verified source bytes; no upstream execution.

This script neither acquires nor imports Hindsight/SDK/provider modules. The
frontier is a lower bound while bodies are absent; lazy and conditional imports
are recorded separately from the ordinary mandatory package import closure.
"""
from __future__ import annotations

import argparse
import ast
from collections import deque
import hashlib
import json
from pathlib import Path
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from acquire_phase08d8_sources import load_plan, identities, verify, DESTINATION, INITIALIZERS, PIN, PREFIX, MANIFEST_SHA256

ALIASES = {"main.py": "main.py", "worker/main.py": "worker_main.py",
           "worker/poller.py": "poller.py", "engine/providers/__init__.py": "providers_init.py"}


def source_module(path: str) -> str:
    name = path.removeprefix("hindsight-api-slim/").removesuffix(".py").replace("/", ".")
    return name.removesuffix(".__init__")


def analyze(data: bytes, module: str, package: bool) -> dict:
    tree = ast.parse(data, filename=module)
    edges, calls = [], []
    base = module if package else module.rsplit(".", 1)[0]

    def visit(node, phase="IMPORT", conditions=()):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Defaults/decorators execute during definition; function body is deferred.
            for child in node.decorator_list + node.args.defaults + [x for x in node.args.kw_defaults if x]:
                visit(child, phase, conditions)
            for child in node.body:
                visit(child, "DEFERRED_FUNCTION_BODY", conditions)
            return
        if isinstance(node, ast.Lambda):
            return
        if isinstance(node, ast.If):
            test = ast.unparse(node.test)
            if test in ("TYPE_CHECKING", "typing.TYPE_CHECKING"):
                for child in node.body:
                    visit(child, "TYPE_CHECKING_ONLY", conditions)
                for child in node.orelse:
                    visit(child, phase, conditions)
                return
            for child in node.body:
                visit(child, phase, conditions + (test,))
            for child in node.orelse:
                visit(child, phase, conditions + ("else: " + test,))
            return
        if isinstance(node, ast.Try):
            optional = any(h.type is not None and "ImportError" in ast.unparse(h.type) for h in node.handlers)
            for child in node.body:
                visit(child, phase, conditions + (("IMPORTERROR_GUARDED",) if optional else ()))
            for handler in node.handlers:
                for child in handler.body:
                    visit(child, phase, conditions + ("exception handler",))
            for child in node.orelse + node.finalbody:
                visit(child, phase, conditions)
            return
        if isinstance(node, ast.Import):
            for alias in node.names:
                edges.append({"module": alias.name, "line": node.lineno, "phase": phase,
                              "conditions": list(conditions), "symbols": []})
        if isinstance(node, ast.ImportFrom) and node.module != "__future__":
            if node.level:
                components = base.split(".")[:len(base.split(".")) - node.level + 1]
                target = ".".join(components + ([node.module] if node.module else []))
            else:
                target = node.module or ""
            edges.append({"module": target, "line": node.lineno, "phase": phase,
                          "conditions": list(conditions), "symbols": [a.name for a in node.names]})
        if isinstance(node, ast.Call) and phase == "IMPORT":
            calls.append({"line": node.lineno, "call": ast.unparse(node.func),
                          "conditions": list(conditions)})
        for child in ast.iter_child_nodes(node):
            visit(child, phase, conditions)

    visit(tree)
    return {"imports": edges, "import_phase_calls": calls}


def build_closure(sources: dict, indexed: dict) -> dict:
    graph = {source_module(p): analyze(data, source_module(p), p.endswith("/__init__.py"))
             for p, data in sources.items()}

    def resolve(module):
        stem = "hindsight-api-slim/" + module.replace(".", "/")
        for path in (stem + ".py", stem + "/__init__.py"):
            if path in indexed:
                return path
        return None  # Namespace packages may have children but no initializer.

    seed = "hindsight_api.engine.providers.openai_compatible_llm"
    queue = deque([(seed, {"purpose": "native provider import"}),
                   ("hindsight_api.tracing", {"purpose": "successful native method late import"})])
    visited, missing, external, unknown = set(), {}, {}, []
    while queue:
        module, reason = queue.popleft()
        path = resolve(module)
        if path is None:
            stem = "hindsight-api-slim/" + module.replace(".", "/") + "/"
            if not any(p.startswith(stem) for p in indexed):
                unknown.append({"module": module, "reason": reason})
            continue
        if path not in sources:
            missing.setdefault(path, []).append(reason)
        if module in visited:
            continue
        visited.add(module)
        parts = module.split(".")
        for end in range(1, len(parts)):
            parent = ".".join(parts[:end])
            if resolve(parent) is not None:
                queue.append((parent, {"purpose": "Python parent package initialization", "required_by": module}))
        if path not in sources:
            continue
        for edge in graph[module]["imports"]:
            if edge["phase"] != "IMPORT" or edge["conditions"]:
                continue
            target = edge["module"]
            why = {"purpose": "mandatory module import", "required_by": path, "line": edge["line"]}
            if target.startswith("hindsight_api"):
                queue.append((target, why))
                # from package import submodule executes that submodule if present.
                for symbol in edge["symbols"]:
                    child = target + "." + symbol
                    if resolve(child) is not None:
                        queue.append((child, why))
            elif target.split(".")[0] not in sys.stdlib_module_names:
                external.setdefault(target, []).append(why)
    return {"visited_modules": sorted(visited),
            "graph": {n: graph[n] for n in sorted(visited) if n in graph},
            "missing": missing, "mandatory_external_imports": external,
            "unresolved_module_names": unknown}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-cache", type=Path, required=True)
    parser.add_argument("--pinned-tree", type=Path, required=True)
    parser.add_argument("--metadata-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sys.prefix == sys.base_prefix or ".venv" not in Path(sys.prefix).parts or not sys.flags.isolated:
        raise RuntimeError("STOP: use existing repository .venv with -I -B")

    def deny(event, arguments):
        if event.startswith("socket.") or (event == "import" and arguments[0].startswith(("hindsight", "openai", "aiohttp", "httpx"))):
            raise RuntimeError("STOP: networking or native/SDK import during static inspection")
    sys.addaudithook(deny)
    plan = load_plan()
    raw_tree = args.pinned_tree.read_bytes()
    if hashlib.sha256(raw_tree).hexdigest() != "b23c03c1c9daf42b764988da19b5aa70e7bd710c8b05092f290773acef35ed33":
        raise ValueError("STOP: pinned tree identity changed")
    tree = json.loads(raw_tree)
    if tree["sha"] != PIN or tree["truncated"] is not False:
        raise ValueError("STOP: wrong or truncated source tree")
    indexed = {r["path"]: r for r in tree["tree"] if r["type"] == "blob"}
    sources, verified = {}, []
    for row in plan["verified_cached_sources"]:
        relative = row["path"].removeprefix(PREFIX)
        data = (args.source_cache / ALIASES.get(relative, Path(relative).name)).read_bytes()
        identity = verify(data, {**row, "bytes": row["byte_count"]})
        if identity["sha256"] != row["sha256"]:
            raise ValueError("STOP: cached source SHA-256 changed")
        sources[row["path"]] = data
        verified.append({"path": row["path"], **identity, "status": "VERIFIED_EXISTING_SOURCE"})
    entries = [json.loads(line) for line in (DESTINATION / "acquisition.jsonl").read_text().splitlines()]
    if [r["path"] for r in entries] != INITIALIZERS:
        raise ValueError("STOP: expected acquisition stop after three initializers")
    rows = {r["path"]: r for r in plan["missing_source_acquisition_frontier"]}
    for entry in entries:
        data = (DESTINATION / entry["path"]).read_bytes()
        identity = verify(data, rows[entry["path"]])
        if any(entry[k] != value for k, value in identity.items()) or entry["tls_verify_result"] != 0 or entry["redirects"] != 0:
            raise ValueError("STOP: source acquisition log/bytes mismatch")
        ast.parse(data)  # Only after identity verification.
        sources[entry["path"]] = data
    acquired = {r["path"] for r in entries}
    closure = build_closure(sources, indexed)
    frontier = []
    for path, reasons in sorted(closure.pop("missing").items()):
        row = indexed[path]
        frontier.append({"path": path, "git_blob_sha1": row["sha"], "bytes": row["size"],
                         "url": f"https://raw.githubusercontent.com/vectorize-io/hindsight/{PIN}/{path}",
                         "sha256": None, "purposes": reasons,
                         "status": "MISSING_ALLOWLISTED_NOT_ACQUIRED" if path in rows else "MISSING_OUTSIDE_AUTHORIZED_ALLOWLIST"})
    metadata = []
    for expected in plan["metadata"]:
        data = (args.metadata_root / expected["path"]).read_bytes()
        identity = identities(data)
        if any(identity[k] != expected[k] for k in identity):
            raise ValueError("STOP: pinned dependency metadata changed")
        metadata.append({"path": expected["path"], **identity})
    lock = tomllib.loads((args.metadata_root / "uv.lock").read_text())
    inventory = json.loads((ROOT / "manifests/phase-08d7-dependency-preparation.json").read_bytes())
    locked = {p["name"]: p for p in inventory["packages"]}
    direct = set(closure["mandatory_external_imports"])
    import_to_package = {"aiohttp": "aiohttp", "asyncpg": "asyncpg", "dateutil.parser": "python-dateutil",
                         "dotenv": "python-dotenv", "httpx": "httpx", "json_repair": "json-repair",
                         "openai": "openai", "orjson": "orjson", "pydantic": "pydantic",
                         "numpy": "numpy", "croniter": "croniter", "dateparser": "dateparser",
                         "zoneinfo": None}
    unmapped = sorted(direct - set(import_to_package))
    sdk = {r["name"]: r for r in plan["sdk_packages"]}
    sdk_plan_raw = (ROOT / "manifests/phase-08d7-sdk-acquisition-plan.json").read_bytes()
    if hashlib.sha256(sdk_plan_raw).hexdigest() != "5543ed2470a56f0a3082ba51a1f81eb56b9ebc879aafaaf17d841365dd2f5b0a":
        raise ValueError("STOP: SDK artifact plan changed")
    wheelhouse = Path(json.loads(sdk_plan_raw)["wheelhouse"])
    for artifact in sdk.values():
        raw = (wheelhouse / artifact["filename"]).read_bytes()
        if len(raw) != artifact["bytes"] or hashlib.sha256(raw).hexdigest() != artifact["sha256"]:
            raise ValueError("STOP: reusable SDK wheel changed")
    packages = []
    names = set(sdk) | {import_to_package[n] for n in direct if n in import_to_package and import_to_package[n]}
    names |= {r["name"] for r in plan["known_additional_dependency_closure"]}
    # Resolve only the lock dependencies of demonstrated mandatory roots on this
    # pinned Python target. No full-distribution or optional-extra closure.
    environment = {"python_full_version": "3.12.8", "python_version": "3.12",
                   "sys_platform": "darwin", "os_name": "posix", "platform_machine": "x86_64",
                   "platform_system": "Darwin", "implementation_name": "cpython",
                   "platform_python_implementation": "CPython", "extra": ""}

    def active(marker):
        if marker is None:
            return True
        # A small non-executing evaluator for the actual lock marker syntax.
        # Unknown syntax/names reject instead of guessing or executing eval().
        def value(node):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                return node.value
            if isinstance(node, ast.Name) and node.id in environment:
                return environment[node.id]
            raise ValueError("STOP: unresolved marker operand: " + marker)

        def expression(node):
            if isinstance(node, ast.BoolOp):
                values = [expression(x) for x in node.values]
                if isinstance(node.op, ast.And):
                    return all(values)
                if isinstance(node.op, ast.Or):
                    return any(values)
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                left, right = value(node.left), value(node.comparators[0])
                variable = node.left.id if isinstance(node.left, ast.Name) else node.comparators[0].id if isinstance(node.comparators[0], ast.Name) else ""
                operation = node.ops[0]
                if variable in {"python_version", "python_full_version"} and not isinstance(operation, (ast.In, ast.NotIn)):
                    def version(text):
                        parts = tuple(int(n) for n in text.split("."))
                        return parts + (0,) * (8 - len(parts))
                    left, right = version(left), version(right)
                comparisons = {ast.Eq: lambda: left == right, ast.NotEq: lambda: left != right,
                               ast.Lt: lambda: left < right, ast.LtE: lambda: left <= right,
                               ast.Gt: lambda: left > right, ast.GtE: lambda: left >= right,
                               ast.In: lambda: left in right, ast.NotIn: lambda: left not in right}
                if type(operation) in comparisons:
                    return comparisons[type(operation)]()
            raise ValueError("STOP: unresolved marker syntax: " + marker)
        return expression(ast.parse(marker, mode="eval").body)
    todo = deque(sorted(names))
    done = set()
    while todo:
        name = todo.popleft()
        if name in done:
            continue
        done.add(name)
        candidates = [p for p in lock["package"] if p["name"] == name and p["version"] == locked[name]["version"]]
        if len(candidates) != 1:
            raise ValueError("STOP: ambiguous lock package: " + name)
        for edge in candidates[0].get("dependencies", []):
            if active(edge.get("marker")):
                todo.append(edge["name"])
    for name in sorted(done):
        row = locked[name]
        matching = row["local_matching_wheels"]
        for artifact in matching:
            raw = Path(artifact["path"]).read_bytes()
            if len(raw) != artifact["bytes"] or hashlib.sha256(raw).hexdigest() != artifact["sha256"]:
                raise ValueError("STOP: recorded local wheel changed")
        wheels = row["compatible_upstream_wheels"]
        selected = sdk[name] if name in sdk else next(
            (w for w in wheels if w["filename"].endswith("py3-none-any.whl")), None)
        if selected is None:
            selected = next((w for w in wheels if "cp312-cp312" in w["filename"] and "x86_64" in w["filename"]), None)
        if selected is None:
            raise ValueError("STOP: no compatible pinned candidate wheel: " + name)
        packages.append({"name": name, "version": row["version"],
                         "status": "READY_REHASHED_SDK_WHEEL" if name in sdk else "READY_REHASHED_LOCAL_WHEEL" if matching else "MISSING_MATCHING_LOCAL_WHEEL",
                         "installed_runtime_rechecked_this_continuation": False,
                         "local_matching_wheels": matching,
                         "selected_candidate_artifact": selected,
                         "installation_authorized": False})
    receipt = {"phase": "08D-8", "continuation_base": "a452984507e83f029ae25cb5c850aaca390354c4",
               "authorization": "USER_GRANTED_SOURCE_ACQUISITION_STATIC_INSPECTION_ONLY",
               "authorized_manifest_sha256": MANIFEST_SHA256, "upstream_commit": PIN,
               "authorized_file_count": 31, "aggregate_limit_bytes": 586246,
               "acquired_verified_files": entries, "acquired_file_count": len(entries),
               "aggregate_acquired_bytes": sum(r["bytes"] for r in entries),
               "unacquired_authorized_files": [r for r in rows.values() if r["path"] not in acquired],
               "verified_existing_sources": verified, "metadata": metadata,
               "acquisition_stopped": True,
               "stop_reason": "Root initializer imports and invokes _thread_limits outside authorized allowlist; engine initializer expands ordinary import into engine/embedding/database/search modules",
               "import_closure": closure, "missing_source_frontier": frontier,
               "next_source_plan": {"files": len(frontier), "aggregate_bytes": sum(r["bytes"] for r in frontier),
                    "new_outside_previous_allowlist_files": sum(r["status"] == "MISSING_OUTSIDE_AUTHORIZED_ALLOWLIST" for r in frontier),
                    "previously_allowlisted_unacquired_files": len(rows) - len(acquired),
                    "authorization": "REQUIRED_BEFORE_RESUMING_ACQUISITION",
                    "first_file": PREFIX + "_thread_limits.py", "additional_frontier_acquisition": "STOP"},
               "known_package_lower_bound": packages, "unmapped_external_imports": unmapped,
               "complete_minimal_closure": "UNKNOWN_PENDING_MISSING_SOURCE_BODIES",
               "cryptography": {"full_distribution_metadata": "REQUIRED_GE_50.0.0",
                    "qualified_sdk": "NOT_REQUIRED", "ordinary_native_import": "UNKNOWN",
                    "intel_macos_wheels_in_lock": 0, "workaround_proposed": False},
               "source_execution_native_import_constructor_sdk_request": 0,
               "package_download_install_build": 0, "runtime_gate": "BLOCKED_UNCHANGED",
               "D3": "PARTIAL", "D4": "BLOCKED", "D5": "PARTIAL"}
    with args.output.open("x") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"PASS: {len(entries)} acquired + {len(verified)} existing sources verified; "
          f"{len(frontier)} missing source nodes; {len(packages)} known package lower bound; acquisition STOPPED")


if __name__ == "__main__":
    main()
