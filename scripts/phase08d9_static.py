"""Static evidence utilities. Never load, compile or execute upstream/SDK code."""
from __future__ import annotations

import ast
from collections import deque
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tomllib
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "hindsight-api-slim/hindsight_api/"
PIN = "f8950b0c07d9e34c76493dba802bb309f0ce60fd"
IDENTITY = "memlife-hindsight-provider-boundary/0.1.0+upstream.f8950b0c07d9"
MODIFIED = tuple(PREFIX + p for p in (
    "engine/__init__.py", "engine/providers/__init__.py", "worker/__init__.py"))
TREE_HASH = "b23c03c1c9daf42b764988da19b5aa70e7bd710c8b05092f290773acef35ed33"
RECEIPTS = {
    "phase-08d8-adaptive-source-closure.json": "772680fb16cc79b2dd85b8c07ae435a07e56b6329f926e84ed6b3457991f87dd",
    "phase-08d7-sdk-installation-qualification.json": "bd93ebf5b537c0c53a7c9570b6ae4daf810d42891d40b6477855108b05d13aca",
    "phase-08d7-dependency-preparation.json": "b18a7959e756a278aa3c27b28c69c07c93cb31ea35d3dde4062cb28256722b11",
    "phase-08d8-native-preparation.json": "99aea9f5bc42f0d53a3b13ae81b586f3ec92ab25027c3cb99b65c04441afe410",
    "phase-08d7-sdk-acquisition-plan.json": "5543ed2470a56f0a3082ba51a1f81eb56b9ebc879aafaaf17d841365dd2f5b0a",
}
ALIASES = {"worker/main.py": "worker_main.py", "worker/poller.py": "poller.py",
           "engine/providers/__init__.py": "providers_init.py"}
TOOLS = ("materialize_phase08d9_provider_boundary.py", "phase08d9_static.py",
         "inspect_phase08d8_sources.py", "acquire_phase08d8_sources.py", "phase08d8_package_closure.py")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def identities(data):
    return {"bytes": len(data), "sha256": digest(data),
            "git_blob_sha1": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()}


def check(data, row):
    if any(row.get(k) != v for k, v in identities(data).items()):
        raise ValueError("STOP: identity mismatch: " + row.get("path", "artifact"))


def guard():
    owned = any((p / "AGENTS.md").is_file() and (p / ".git").exists() for p in Path(sys.prefix).parents)
    if sys.prefix == sys.base_prefix or ".venv" not in Path(sys.prefix).parts or not owned or not sys.flags.isolated or not sys.dont_write_bytecode:
        raise RuntimeError("STOP: repository .venv with -I -B required")
    banned = {"hindsight", "hindsight_api", "hindsight_client", "openai", "httpx", "httpcore", "aiohttp"}
    if any(name.split(".")[0] in banned for name in sys.modules):
        raise RuntimeError("STOP: upstream/SDK code already loaded before static guard")
    def deny(event, args):
        if event.startswith("socket.") or (event == "import" and args[0].split(".")[0] in banned):
            raise RuntimeError("STOP: upstream/SDK/network execution forbidden")
    sys.addaudithook(deny)
    require_https_git()


def https_url(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("STOP: configured Git remote must use credential-free HTTPS; SSH prohibited")


def require_https_git():
    configured = subprocess.run(["git", "config", "--get-regexp", r"^remote\..*\.(url|pushurl)$"],
                                cwd=ROOT, capture_output=True, text=True)
    if configured.returncode != 0:
        raise ValueError("STOP: Git HTTPS configuration unavailable")
    for line in configured.stdout.splitlines():
        https_url(line.split(" ", 1)[1])
    for remote in subprocess.check_output(["git", "remote"], cwd=ROOT, text=True).splitlines():
        for flags in ([], ["--push"]):
            urls = subprocess.check_output(["git", "remote", "get-url", "--all", *flags, remote], cwd=ROOT, text=True)
            for url in urls.splitlines():
                https_url(url)  # Reject insteadOf/pushInsteadOf rewrite to SSH too.


def evidence():
    result = {}
    for name, sha in RECEIPTS.items():
        data = (ROOT / "manifests" / name).read_bytes()
        if digest(data) != sha:
            raise ValueError("STOP: immutable receipt changed: " + name)
        result[name] = json.loads(data)
    return result


def regular(path):
    if path.is_symlink() or any(p.is_symlink() for p in path.parents) or not path.is_file():
        raise ValueError("STOP: missing/nonregular/symlink input: " + str(path))
    return path.read_bytes()


def load_inputs(cache, frontier, pinned_tree, metadata):
    receipts = evidence()
    raw = regular(pinned_tree)
    if digest(raw) != TREE_HASH:
        raise ValueError("STOP: pinned tree response mismatch")
    tree = json.loads(raw)
    if tree["sha"] != PIN or tree["truncated"] is not False:
        raise ValueError("STOP: wrong/truncated upstream tree")
    indexed = {r["path"]: r for r in tree["tree"]}
    rows = receipts["phase-08d8-adaptive-source-closure.json"]["verified_sources"]
    acquired = {r["path"] for r in receipts["phase-08d8-adaptive-source-closure.json"]["acquisition_evidence"]}
    # Initial 10 frontier files precede the adaptive acquisition. The remaining
    # 20 historical inputs have fixed basename aliases in the original cache.
    baseline = {r["path"] for r in rows if r["path"] not in acquired
                and r["path"] in {PREFIX + p for p in (
                    "api/http.py", "config.py", "engine/consolidation/consolidator.py", "engine/embeddings.py",
                    "engine/llm_interface.py", "engine/llm_trace.py", "engine/llm_transport.py", "engine/llm_wrapper.py",
                    "engine/memory_engine.py", "engine/multi_llm.py", "engine/providers/__init__.py",
                    "engine/providers/openai_compatible_llm.py", "engine/retain/fact_extraction.py",
                    "engine/retain/orchestrator.py", "engine/task_backend.py", "main.py", "server.py",
                    "worker/main.py", "worker/poller.py", "worker/stage.py")}}
    expected_front = {r["path"] for r in rows} - baseline
    actual_front = {p.relative_to(frontier).as_posix() for p in frontier.rglob("*")
                    if p.is_file() and p.suffix == ".py"}
    if actual_front != expected_front:
        raise ValueError("STOP: missing/unexpected frontier source inputs")
    expected_cache = {ALIASES.get(p.removeprefix(PREFIX), Path(p).name) for p in baseline}
    # api_main.py is a historical non-input in this shared cache. It is never
    # read or materialized; no arbitrary additional Python input is accepted.
    if {p.relative_to(cache).as_posix() for p in cache.rglob("*.py")} - {"api_main.py"} != expected_cache:
        raise ValueError("STOP: missing/unexpected cache source inputs")
    sources = {}
    for row in rows:
        path = row["path"]
        if not path.startswith(PREFIX) or Path(path).is_absolute() or ".." in Path(path).parts or path in sources:
            raise ValueError("STOP: invalid/duplicate source path")
        item = indexed[path]
        if item["type"] != "blob" or item["mode"] != "100644" or item["sha"] != row["git_blob_sha1"] or item["size"] != row["bytes"]:
            raise ValueError("STOP: receipt/tree source mismatch")
        location = cache / ALIASES.get(path.removeprefix(PREFIX), Path(path).name) if path in baseline else frontier / path
        data = regular(location)
        check(data, row)
        sources[path] = data
    if len(sources) != 131:
        raise ValueError("STOP: expected 131 verified source identities")
    metadata_rows = receipts["phase-08d8-native-preparation.json"]["metadata"]
    metadata_bytes = {}
    for row in metadata_rows:
        data = regular(metadata / row["path"])
        check(data, row)
        metadata_bytes[row["path"]] = data
    return sources, indexed, metadata_bytes, receipts


def module(path):
    return path.removeprefix("hindsight-api-slim/").removesuffix(".py").replace("/", ".").removesuffix(".__init__")


def original_exports(data):
    tree = ast.parse(data)
    imports = {}
    names = None
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            if node.level != 1 or not node.module:
                raise ValueError("STOP: unreviewed export import")
            for alias in node.names:
                key = alias.asname or alias.name
                if key in imports:
                    raise ValueError("STOP: duplicate export")
                imports[key] = ("." + node.module, alias.name)
        elif isinstance(node, ast.Assign) and [getattr(t, "id", None) for t in node.targets] == ["__all__"]:
            names = ast.literal_eval(node.value)
        elif not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
            raise ValueError("STOP: unexpected original initializer statement")
    if not isinstance(names, list) or len(names) != len(set(names)) or set(names) != set(imports):
        raise ValueError("STOP: exports and __all__ disagree")
    return names, imports


def lazy_exports(data):
    for node in ast.parse(data).body:
        if isinstance(node, ast.Assign) and [getattr(t, "id", None) for t in node.targets] == ["_LAZY_EXPORTS"]:
            return ast.literal_eval(node.value)
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) == "_LAZY_EXPORTS":
            return ast.literal_eval(node.value)
    return {}


def closure(sources, indexed, metadata, receipts):
    # These are repository static analyzers, not imports of the analyzed code.
    from inspect_phase08d8_sources import analyze
    from phase08d8_package_closure import closure as packages
    paths = {module(p): p for p in sources}
    lazy = {module(p): lazy_exports(data) for p, data in sources.items() if p.endswith("/__init__.py")}
    queue = deque(["hindsight_api.engine.providers.openai_compatible_llm", "hindsight_api.tracing"])
    visited, graph, external, activated = set(), {}, set(), []
    while queue:
        name = queue.popleft()
        if name in visited:
            continue
        if name not in paths:
            stem = "hindsight-api-slim/" + name.replace(".", "/")
            if stem + ".py" in indexed or stem + "/__init__.py" in indexed:
                raise ValueError("STOP: missing mandatory source: " + name)
            if any(p.startswith(stem + "/") for p in indexed):
                continue  # Real upstream namespace package, not a stub.
            raise ValueError("STOP: unresolved mandatory source: " + name)
        visited.add(name)
        p = paths[name]
        graph[name] = analyze(sources[p], name, p.endswith("/__init__.py"))
        parts = name.split(".")
        queue.extend(".".join(parts[:n]) for n in range(1, len(parts)) if ".".join(parts[:n]) in paths)
        for edge in graph[name]["imports"]:
            if edge["phase"] != "IMPORT" or edge["conditions"]:
                continue
            target = edge["module"]
            if target.startswith("hindsight_api"):
                queue.append(target)
                for symbol in edge["symbols"]:
                    if target + "." + symbol in paths:
                        queue.append(target + "." + symbol)
                    elif symbol in lazy.get(target, {}):
                        relative, attr = lazy[target][symbol]
                        if not relative.startswith(".") or relative.startswith(".."):
                            raise ValueError("STOP: unsupported lazy target")
                        resolved = target + relative
                        activated.append({"from": name, "package": target, "name": symbol, "target": resolved, "attribute": attr})
                        queue.append(resolved)
            elif target.split(".")[0] not in sys.stdlib_module_names:
                external.add(target)
    excluded = {"hindsight_api.engine.memory_engine", "hindsight_api.engine.embeddings", "hindsight_api.engine.cross_encoder", "hindsight_api.worker.poller"}
    excluded |= {module(p) for p in sources if "/providers/" in p and p.endswith("_llm.py")
                 and not p.endswith("/openai_compatible_llm.py")}
    if visited & excluded:
        raise ValueError("STOP: excluded implementation reached")
    plan = packages(external, tomllib.loads(metadata["uv.lock"].decode()), receipts["phase-08d7-dependency-preparation.json"])
    # Rehash available artifacts as inert bytes; never install/import them.
    wheel_rows = {r["name"]: r for r in receipts["phase-08d8-adaptive-source-closure.json"]["wheel_inventory"]}
    artifacts = []
    wheelhouse = Path(receipts["phase-08d7-sdk-acquisition-plan.json"]["wheelhouse"])
    for name in plan["package_versions"]:
        row = wheel_rows[name]
        sdk = row["sdk_artifact"]
        local = row["existing_wheels"]
        for wheel in local:
            data = regular(Path(wheel["path"]))
            if len(data) != wheel["bytes"] or digest(data) != wheel["sha256"]:
                raise ValueError("STOP: existing dependency artifact changed: " + name)
        if sdk:
            data = regular(wheelhouse / sdk["filename"])
            if len(data) != sdk["bytes"] or digest(data) != sdk["sha256"]:
                raise ValueError("STOP: SDK artifact changed: " + name)
        candidates = row["compatible_locked_candidates"]
        selected = sdk or next((w for w in candidates if any(w["sha256"] == x["sha256"] for x in local)), None)
        selected = selected or next((w for w in candidates if w["filename"].endswith("py3-none-any.whl")), None)
        selected = selected or next(iter(candidates), None)
        if selected is None:
            raise ValueError("STOP: projected package has no compatible locked binary: " + name)
        artifacts.append({**row, "selected_candidate_artifact": selected,
                          "available_artifacts_rehashed_stage1": bool(sdk or local),
                          "metadata_analysis_only_not_installation": True})
    plan["artifact_plan"] = artifacts
    plan["installation_authorized"] = False
    conditional = [{"required_by": name, **edge} for name in sorted(graph) for edge in graph[name]["imports"]
                   if edge["phase"] != "IMPORT" or edge["conditions"]]
    return {"seed_modules": ["hindsight_api.engine.providers.openai_compatible_llm", "hindsight_api.tracing"],
            "visited_modules": sorted(visited), "graph": {n: graph[n] for n in sorted(graph)},
            "mandatory_external_imports": sorted(external), "activated_lazy_exports": activated,
            "conditional_deferred_type_only_edges": conditional,
            "excluded_implementations": sorted(excluded), "packages": plan,
            "claim": "STATIC_LITERAL_PROJECTION_NOT_RUNTIME_SAFETY"}


def tree_identity(sources):
    return digest(canonical({p: identities(data) for p, data in sorted(sources.items())}))


def ignored_output(path):
    path = path.absolute()
    local = ROOT / ".local"
    if ".." in path.parts or not path.is_relative_to(local) or path == local or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("STOP: output must be a new repository-owned ignored .local tree")
    if subprocess.run(["git", "check-ignore", "-q", str(path)], cwd=ROOT).returncode:
        raise ValueError("STOP: output is not ignored")
    if path.exists():
        raise FileExistsError("STOP: exclusive output already exists")
    return path


def arguments(parser):
    parser.add_argument("--source-cache", type=Path, required=True)
    parser.add_argument("--source-frontier", type=Path, required=True)
    parser.add_argument("--pinned-tree", type=Path, required=True)
    parser.add_argument("--metadata-root", type=Path, required=True)


def inputs(args):
    return load_inputs(args.source_cache, args.source_frontier, args.pinned_tree, args.metadata_root)
