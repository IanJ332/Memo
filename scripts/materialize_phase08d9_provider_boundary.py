"""Stage 1 exclusive, deterministic source derivative; no native/SDK execution."""
from __future__ import annotations

import argparse
import ast
import difflib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase08d9_static as static

SPEC = "pep562-three-initializers/1.0.0"
RESOLVER = '''
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


def transform(data):
    names, exports = static.original_exports(data)
    tree = ast.parse(data)
    lines = data.decode().splitlines(keepends=True)
    doc = tree.body[0]
    if not isinstance(doc, ast.Expr) or not isinstance(doc.value, ast.Constant):
        raise ValueError("STOP: missing original documentation")
    all_node = next(n for n in tree.body if isinstance(n, ast.Assign))
    imports = [n for n in tree.body if isinstance(n, ast.ImportFrom)]
    # Preserve the docstring and __all__ text, including order and comments.
    prefix = "".join(lines[:doc.end_lineno])
    all_text = "".join(lines[all_node.lineno - 1:all_node.end_lineno])
    type_text = "".join("".join("    " + line for line in lines[n.lineno - 1:n.end_lineno]) for n in imports)
    mapping = "_LAZY_EXPORTS = {\n" + "".join(f"    {name!r}: {exports[name]!r},\n" for name in names) + "}\n"
    return (prefix + "\nfrom typing import TYPE_CHECKING\n\n" + mapping + "\n" + all_text
            + "\n" + RESOLVER + "\n\nif TYPE_CHECKING:\n" + type_text).encode()


def patch(original, derivative):
    return "".join("".join(difflib.unified_diff(original[p].decode().splitlines(keepends=True),
                   derivative[p].decode().splitlines(keepends=True), fromfile="a/" + p, tofile="b/" + p,
                   n=3, lineterm="\n")) for p in sorted(static.MODIFIED)).encode()


def manifest(original, derivative, indexed, metadata, receipts):
    projected = static.closure(derivative, indexed, metadata, receipts)
    reached = set(projected["visited_modules"])
    diff = patch(original, derivative)
    tools = {"scripts/" + p: static.identities((static.ROOT / "scripts" / p).read_bytes()) for p in static.TOOLS}
    return {
        "schema_version": 1, "phase": "08D-9_STAGE_1", "engineered_runtime_identity": static.IDENTITY,
        "qualification_label": "ENGINEERED_PROVIDER_BOUNDARY", "UNMODIFIED_HINDSIGHT_RUNTIME": False,
        "upstream": {"repository": "https://github.com/vectorize-io/hindsight", "version": "0.10.1",
                     "commit": static.PIN, "git_tree_response_sha256": static.TREE_HASH,
                     "source_prefix": static.PREFIX},
        "evidence_receipt_sha256": static.RECEIPTS,
        "transformation": {"specification": SPEC, "approved_paths": sorted(static.MODIFIED),
                           "tool_identities": tools, "export_maps": {
                               p: {"__all__": static.original_exports(original[p])[0],
                                   "targets": static.original_exports(original[p])[1]} for p in static.MODIFIED},
                           "exception_contract": "Only unknown export lookup is wrapped; import and target attribute exceptions propagate",
                           "import_timing": "Intentionally changed; no full-package import semantic equivalence claim"},
        "patch": {"path": "bootstrap.patch", **static.identities(diff), "format": "difflib.unified_diff UTF-8 LF, sorted paths, context=3, no timestamps"},
        "canonical_serialization": "UTF-8 JSON; sorted keys; compact separators; ensure_ascii=false; LF terminator",
        "original_source_tree_sha256": static.tree_identity(original),
        "derivative_source_tree_sha256": static.tree_identity(derivative),
        "files": [{"original_path": p, "original": static.identities(data), "derivative_path": "source/" + p,
                   "derivative": static.identities(derivative[p]),
                   "classification": "MODIFIED_BOOTSTRAP" if p in static.MODIFIED else "UNCHANGED_NATIVE_SOURCE",
                   "inclusion_reason": "PROVIDER_ONLY_PROJECTED_CLOSURE" if static.module(p) in reached else "VERIFIED_INACTIVE_SOURCE_RETAINED_FOR_EXPORT_TARGETS_AND_AUDIT"}
                  for p, data in sorted(original.items())],
        "included_source_closure": projected,
        "metadata": [{"path": p, **static.identities(data), "copied_or_installed": False} for p, data in sorted(metadata.items())],
        "license_notice": {"path": "LICENSE", "bytes": indexed["LICENSE"]["size"],
                           "git_blob_sha1": indexed["LICENSE"]["sha"], "sha256": None,
                           "status": "PINNED_TREE_IDENTITY_ONLY_BYTES_NOT_AVAILABLE_IN_VERIFIED_SOURCE_RECEIPT",
                           "packaging_or_redistribution_authorized": False, "notice_paths": []},
        "excluded_features": ["MemoryEngine", "worker/poller/service", "embedding/cross-encoder/database initialization",
                              "sibling providers", "provider factory/multi-LLM", "Google OAuth activation",
                              "Ollama/batch/files/responses/streaming runtime paths", "star import/full lazy export resolution",
                              "native/SDK import or construction", "empirical/live/model/RQ3 actions"],
        "projection_comparison": {"adr_modules": 29, "adr_packages": 41,
                                  "actual_modules": len(reached), "actual_packages": len(projected["packages"]["package_versions"])},
        "execution": {"native_or_sdk_imports": 0, "provider_constructions": 0, "package_acquisition_install_build": 0,
                      "provider_model_embedding_downstream_rq3_calls": 0, "runtime_safety": "UNKNOWN_UNEXECUTED",
                      "semantic_parity": "NOT_EXECUTED", "D3": "PARTIAL", "D4": "BLOCKED", "D5": "PARTIAL"},
    }


def materialize(args):
    output = static.ignored_output(args.output)
    if args.publish_manifest and args.publish_manifest.exists():
        raise FileExistsError("STOP: immutable published manifest already exists")
    original, indexed, metadata, receipts = static.inputs(args)
    derivative = {p: transform(data) if p in static.MODIFIED else data for p, data in original.items()}
    result = manifest(original, derivative, indexed, metadata, receipts)
    raw = static.canonical(result)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()  # Exclusive: failed partial output is retained, never resumed.
    for p, data in sorted(derivative.items()):
        destination = output / "source" / p
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(data)
    with (output / "bootstrap.patch").open("xb") as stream:
        stream.write(patch(original, derivative))
    with (output / "receipt.json").open("xb") as stream:
        stream.write(raw)
    if args.publish_manifest:
        with args.publish_manifest.open("xb") as stream:
            stream.write(raw)
    return result


def main():
    static.guard()
    parser = argparse.ArgumentParser(description=__doc__)
    static.arguments(parser)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--publish-manifest", type=Path)
    args = parser.parse_args()
    result = materialize(args)
    print("PASS: 131 sources; exactly three modified initializers; " + str(result["projection_comparison"]))
    print("MANIFEST_SHA256=" + static.digest(static.canonical(result)))


if __name__ == "__main__":
    main()
