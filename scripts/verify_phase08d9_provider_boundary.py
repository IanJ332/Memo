"""Independent static verifier: does not import the materializer or native/SDK code."""
from __future__ import annotations

import argparse
import ast
import difflib
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase08d9_static as static

# Independent reviewed syntax oracle. Only lookup KeyError is translated;
# target import/getattr remain outside the handler. No exec/compile/eval occurs.
EXPECTED_FUNCTIONS = '''
def __getattr__(name: str):
    """Resolve the original public target; propagate its import/getattr errors."""
    try:
        module_name, attribute = _LAZY_EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    from importlib import import_module
    value = getattr(import_module(module_name, __name__), attribute)
    globals()[name] = value
    return value
def __dir__():
    return sorted(set(globals()) | set(__all__))
'''


def require(condition, message):
    if not condition:
        raise ValueError("STOP: " + message)


def syntax(node):
    return ast.dump(node, include_attributes=False)


def verify_initializer(original, derivative):
    before = ast.parse(original)
    after = ast.parse(derivative)
    names, exports = static.original_exports(original)
    require(ast.get_docstring(before, clean=False) == ast.get_docstring(after, clean=False), "public documentation changed")
    # Construct an AST oracle independently from the original export statements.
    doc = before.body[0]
    all_node = next(n for n in before.body if isinstance(n, ast.Assign))
    expected = [doc, ast.parse("from typing import TYPE_CHECKING").body[0],
                ast.parse("_LAZY_EXPORTS = " + repr({name: exports[name] for name in names})).body[0], all_node,
                *ast.parse(EXPECTED_FUNCTIONS).body,
                ast.If(test=ast.Name(id="TYPE_CHECKING", ctx=ast.Load()),
                       body=[n for n in before.body if isinstance(n, ast.ImportFrom)], orelse=[])]
    require(syntax(ast.Module(body=expected, type_ignores=[])) == syntax(after), "unapproved initializer syntax/export/exception change")
    require(static.lazy_exports(derivative) == exports, "changed export targets")
    # AST equality does not preserve comments; verify original doc and all text too.
    old_lines = original.decode().splitlines(keepends=True)
    new_lines = derivative.decode().splitlines(keepends=True)
    new_all = after.body[3]
    require(old_lines[:doc.end_lineno] == new_lines[:after.body[0].end_lineno], "docstring bytes changed")
    require(old_lines[all_node.lineno - 1:all_node.end_lineno] == new_lines[new_all.lineno - 1:new_all.end_lineno], "__all__ bytes/order/comments changed")
    return {"__all__": names, "targets": exports}


def verify_tree(args):
    original, indexed, metadata, receipts = static.inputs(args)
    raw = static.regular(args.manifest)
    manifest = json.loads(raw)
    require(raw == static.canonical(manifest), "noncanonical manifest")
    require(set(manifest) == {"schema_version", "phase", "engineered_runtime_identity", "qualification_label",
            "UNMODIFIED_HINDSIGHT_RUNTIME", "upstream", "evidence_receipt_sha256", "transformation", "patch",
            "canonical_serialization", "original_source_tree_sha256", "derivative_source_tree_sha256", "files",
            "included_source_closure", "metadata", "license_notice", "excluded_features", "projection_comparison", "execution"}, "unapproved manifest schema")
    require(manifest["canonical_serialization"] == "UTF-8 JSON; sorted keys; compact separators; ensure_ascii=false; LF terminator", "serialization contract drift")
    require(static.regular(args.derivative / "receipt.json") == raw, "published/immutable local receipts differ")
    require(manifest["schema_version"] == 1 and manifest["engineered_runtime_identity"] == static.IDENTITY
            and manifest["phase"] == "08D-9_STAGE_1" and manifest["qualification_label"] == "ENGINEERED_PROVIDER_BOUNDARY"
            and manifest["UNMODIFIED_HINDSIGHT_RUNTIME"] is False, "engineered identity/claim drift")
    require(manifest["upstream"] == {"repository": "https://github.com/vectorize-io/hindsight", "version": "0.10.1",
            "commit": static.PIN, "git_tree_response_sha256": static.TREE_HASH, "source_prefix": static.PREFIX}, "wrong upstream")
    require(manifest["evidence_receipt_sha256"] == static.RECEIPTS, "evidence binding drift")
    expected_files = {"source/" + p for p in original} | {"receipt.json", "bootstrap.patch"}
    actual_files = set()
    for p in args.derivative.rglob("*"):
        require(not p.is_symlink(), "symlink substitution in derivative")
        if p.is_file():
            actual_files.add(p.relative_to(args.derivative).as_posix())
    require(actual_files == expected_files, "missing/unexpected derivative files")
    actual_dirs = {p.relative_to(args.derivative).as_posix() for p in args.derivative.rglob("*") if p.is_dir()}
    expected_dirs = {parent.as_posix() for file in expected_files for parent in Path(file).parents if parent != Path(".")}
    require(actual_dirs == expected_dirs, "unexpected derivative directories")
    derivative = {p: static.regular(args.derivative / "source" / p) for p in original}
    modified = {p for p in original if derivative[p] != original[p]}
    require(modified == set(static.MODIFIED), "not exactly the three approved upstream modifications")
    maps = {p: verify_initializer(original[p], derivative[p]) for p in static.MODIFIED}
    require(manifest["transformation"]["specification"] == "pep562-three-initializers/1.0.0"
            and manifest["transformation"]["approved_paths"] == sorted(static.MODIFIED), "transform scope/version drift")
    require(static.canonical(maps) == static.canonical(manifest["transformation"]["export_maps"]), "manifest export-map drift")
    require(manifest["transformation"]["tool_identities"] == {
        "scripts/" + p: static.identities((static.ROOT / "scripts" / p).read_bytes()) for p in static.TOOLS}, "tool identity drift")
    require(set(manifest["transformation"]) == {"specification", "approved_paths", "tool_identities", "export_maps", "exception_contract", "import_timing"}, "unapproved transform schema")
    require(manifest["transformation"]["exception_contract"] == "Only unknown export lookup is wrapped; import and target attribute exceptions propagate"
            and manifest["transformation"]["import_timing"] == "Intentionally changed; no full-package import semantic equivalence claim", "exception/import-timing claim drift")
    require(manifest["original_source_tree_sha256"] == static.tree_identity(original)
            and manifest["derivative_source_tree_sha256"] == static.tree_identity(derivative), "source-tree identity drift")
    projected = static.closure(derivative, indexed, metadata, receipts)
    require(static.canonical(projected) == static.canonical(manifest["included_source_closure"]), "actual lazy graph/dependency plan mismatch")
    require(len(projected["visited_modules"]) == 29 and len(projected["packages"]["package_versions"]) == 41, "ADR projection changed; review required")
    # Removing eager edges and replacing each with precisely the same lazy target
    # introduces no target edge, hence no new potential first-party target cycle.
    # Runtime reentrancy and optional/deferred paths are not certified here.
    require(projected["activated_lazy_exports"] == [], "unexpected lazy export activation on provider path")
    for p in static.MODIFIED:
        edges = projected["graph"][static.module(p)]["imports"]
        require(not any(e["phase"] == "IMPORT" and not e["conditions"] and e["module"].startswith("hindsight_api") for e in edges), "eager implementation edge retained")
    reached = set(projected["visited_modules"])
    expected_rows = [{"original_path": p, "original": static.identities(data), "derivative_path": "source/" + p,
                      "derivative": static.identities(derivative[p]),
                      "classification": "MODIFIED_BOOTSTRAP" if p in static.MODIFIED else "UNCHANGED_NATIVE_SOURCE",
                      "inclusion_reason": "PROVIDER_ONLY_PROJECTED_CLOSURE" if static.module(p) in reached else "VERIFIED_INACTIVE_SOURCE_RETAINED_FOR_EXPORT_TARGETS_AND_AUDIT"}
                     for p, data in sorted(original.items())]
    require(manifest["files"] == expected_rows, "manifest source identities/classifications/substitutions drift")
    diff = "".join("".join(difflib.unified_diff(original[p].decode().splitlines(keepends=True),
                   derivative[p].decode().splitlines(keepends=True), fromfile="a/" + p, tofile="b/" + p, n=3, lineterm="\n"))
                   for p in sorted(static.MODIFIED)).encode()
    require(static.regular(args.derivative / "bootstrap.patch") == diff, "patch does not describe actual source delta")
    static.check(diff, manifest["patch"])
    require(manifest["patch"] == {"path": "bootstrap.patch", **static.identities(diff),
            "format": "difflib.unified_diff UTF-8 LF, sorted paths, context=3, no timestamps"}, "unexpected patch identity/format")
    require(manifest["metadata"] == [{"path": p, **static.identities(data), "copied_or_installed": False}
            for p, data in sorted(metadata.items())], "metadata identity drift")
    require(manifest["projection_comparison"] == {"adr_modules": 29, "adr_packages": 41, "actual_modules": 29, "actual_packages": 41}, "projection comparison drift")
    require(manifest["license_notice"] == {"path": "LICENSE", "bytes": indexed["LICENSE"]["size"],
            "git_blob_sha1": indexed["LICENSE"]["sha"], "sha256": None,
            "status": "PINNED_TREE_IDENTITY_ONLY_BYTES_NOT_AVAILABLE_IN_VERIFIED_SOURCE_RECEIPT",
            "packaging_or_redistribution_authorized": False, "notice_paths": []}, "license evidence claim drift")
    require(manifest["excluded_features"] == ["MemoryEngine", "worker/poller/service", "embedding/cross-encoder/database initialization",
            "sibling providers", "provider factory/multi-LLM", "Google OAuth activation",
            "Ollama/batch/files/responses/streaming runtime paths", "star import/full lazy export resolution",
            "native/SDK import or construction", "empirical/live/model/RQ3 actions"], "exclusion boundary drift")
    require(manifest["execution"] == {"native_or_sdk_imports": 0, "provider_constructions": 0, "package_acquisition_install_build": 0,
            "provider_model_embedding_downstream_rq3_calls": 0, "runtime_safety": "UNKNOWN_UNEXECUTED",
            "semantic_parity": "NOT_EXECUTED", "D3": "PARTIAL", "D4": "BLOCKED", "D5": "PARTIAL"}, "unsupported readiness claim")
    return raw, original, derivative


def rematerialize(args, raw):
    # Fresh exclusive tree; never overwrite the first receipt or failing output.
    static.ignored_output(args.rematerialize_output)
    command = [sys.executable, "-I", "-B", str(static.ROOT / "scripts/materialize_phase08d9_provider_boundary.py"),
               "--source-cache", str(args.source_cache), "--source-frontier", str(args.source_frontier),
               "--pinned-tree", str(args.pinned_tree), "--metadata-root", str(args.metadata_root),
               "--output", str(args.rematerialize_output)]
    result = subprocess.run(command, cwd=static.ROOT, env={"PATH": "/usr/bin:/bin"}, capture_output=True, text=True, timeout=30)
    require(result.returncode == 0, "rematerialization failed: " + result.stderr)
    require(static.regular(args.rematerialize_output / "receipt.json") == raw, "nondeterministic rematerialization receipt")
    original_tree = {p.relative_to(args.derivative).as_posix(): static.digest(static.regular(p))
                     for p in args.derivative.rglob("*") if p.is_file()}
    second_tree = {p.relative_to(args.rematerialize_output).as_posix(): static.digest(static.regular(p))
                   for p in args.rematerialize_output.rglob("*") if p.is_file()}
    require(original_tree == second_tree, "nondeterministic rematerialization bytes")
    before = static.regular(args.rematerialize_output / "receipt.json")
    rejected = subprocess.run(command, cwd=static.ROOT, env={"PATH": "/usr/bin:/bin"}, capture_output=True, text=True, timeout=30)
    require(rejected.returncode != 0 and "exclusive output already exists" in rejected.stderr, "output reuse accepted")
    require(static.regular(args.rematerialize_output / "receipt.json") == before, "existing receipt overwritten")


def main():
    static.guard()
    parser = argparse.ArgumentParser(description=__doc__)
    static.arguments(parser)
    parser.add_argument("--derivative", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--rematerialize-output", type=Path, required=True)
    parser.add_argument("--receipt-output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.receipt_output.exists(), "verification receipt already exists")
    raw, original, derivative = verify_tree(args)
    rematerialize(args, raw)
    # Rehash originals after all writes/subprocesses; source integrity is not
    # inferred from having verified them before transformation.
    require(static.inputs(args)[0] == original, "original inputs changed during verification")
    receipt = {"phase": "08D-9_STAGE_1", "status": "STATIC_PASS_NOT_RUNTIME_QUALIFICATION",
               "manifest_sha256": static.digest(raw), "verifier": static.identities(Path(__file__).read_bytes()),
               "source_files": len(original), "modified_paths": sorted(static.MODIFIED), "unchanged_files": 128,
               "provider_modules": 29, "packages": 41, "deterministic_rematerialization": True,
               "exclusive_output_and_receipt_preservation": True, "original_inputs_unchanged": True,
               "native_sdk_imports_or_calls": 0, "runtime_safety": "UNKNOWN", "semantic_parity": "NOT_EXECUTED"}
    with args.receipt_output.open("xb") as stream:
        stream.write(static.canonical(receipt))
    print("PASS: independent static identities/export/syntax/graph/patch verification; deterministic rematerialization; exclusive receipts")
    print("VERIFICATION_RECEIPT_SHA256=" + static.digest(static.canonical(receipt)))


if __name__ == "__main__":
    main()
