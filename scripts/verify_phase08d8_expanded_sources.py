"""Finalize expanded-source evidence and test the STOP gate offline; no source execution."""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from phase08d8_expanded_sources import (reference, existing_sources, digest, verify, identities,
                                      PLAN_PATH, GROUPS, LOG, DESTINATION, BASE, RECEIPT_SHA256, PIN)
from inspect_phase08d8_sources import build_closure

PLAN_HASH = "f5d1bce8158dad16c6300e18aef04f2d58ed69b80a9c56ac742817df66fafb94"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-cache", type=Path, required=True)
    parser.add_argument("--pinned-tree", type=Path, required=True)
    parser.add_argument("--metadata-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sys.prefix == sys.base_prefix or ".venv" not in Path(sys.prefix).parts or not sys.flags.isolated:
        raise RuntimeError("STOP: repository .venv with -I -B required")
    sys.addaudithook(lambda event, arguments: (_ for _ in ()).throw(RuntimeError("STOP: forbidden static-inspection event"))
                    if event.startswith("socket.") or (event == "import" and arguments[0].startswith(("hindsight", "openai", "httpx", "aiohttp"))) else None)
    previous, indexed = reference(args.pinned_tree)
    sources = existing_sources(previous, args.source_cache)
    plan_bytes = PLAN_PATH.read_bytes()
    if digest(plan_bytes) != PLAN_HASH:
        raise ValueError("STOP: frozen expanded plan changed")
    plan = json.loads(plan_bytes)
    rows = {r["path"]: r for r in plan["files"]}
    assert len(rows) == 75 and sum(r["bytes"] for r in rows.values()) == 1305501
    entries = [json.loads(s) for s in LOG.read_text().splitlines()]
    assert len(entries) == 3 and [r["path"] for r in entries] == [g[0] for g in plan["dependency_groups"][:3]]
    summaries = []
    for i, entry in enumerate(entries, 1):
        data = (DESTINATION / entry["path"]).read_bytes()
        identity = verify(data, rows[entry["path"]])
        assert all(entry[k] == v for k, v in identity.items())
        assert entry["url"] == entry["effective_url"] == rows[entry["path"]]["url"]
        assert entry["http_status"] == 200 and entry["tls_verify_result"] == 0 and entry["redirects"] == 0
        sources[entry["path"]] = data
        group_file = GROUPS / f"group-{i:03}.json"
        group = json.loads(group_file.read_bytes())
        review = json.loads((GROUPS / f"review-{i:03}.json").read_bytes())
        assert review["group_sha256"] == digest(group_file.read_bytes()) and review["plan_sha256"] == PLAN_HASH
        assert group["plan_sha256"] == PLAN_HASH and group["newly_acquired"] == entry
        assert review["verdict"] == ("CONTINUE_STATIC_INSPECTION" if i < 3 else "STOP_NEW_REQUIRED_SOURCE")
        summaries.append({"group": i, "group_receipt_sha256": digest(group_file.read_bytes()),
                          "review": review, "status": group["status"],
                          "closure_modules": len(group["import_closure"]["visited_modules"]),
                          "verified_reachable_bodies": len(group["import_closure"]["graph"]),
                          "missing_source_count": len(group["missing_source_frontier"]),
                          "new_outside_source_count": group["new_outside_source_count"]})
    assert sum(r["bytes"] for r in entries) == 101207
    assert not list(DESTINATION.rglob("*.part"))
    expected_local = {r["path"] for r in previous["acquired_verified_files"]} | {r["path"] for r in entries}
    assert {str(p.relative_to(DESTINATION)) for p in DESTINATION.rglob("*.py")} == expected_local
    closure = build_closure(sources, indexed)
    frontier = []
    for path, reasons in sorted(closure.pop("missing").items()):
        row = indexed[path]
        frontier.append({"path": path, "bytes": row["size"], "git_blob_sha1": row["sha"], "sha256": None,
                         "url": f"https://raw.githubusercontent.com/vectorize-io/hindsight/{PIN}/{path}",
                         "required_purpose": reasons,
                         "status": "MISSING_APPROVED_UNACQUIRED" if path in rows else "MISSING_OUTSIDE_APPROVED_75"})
    assert len(frontier) == 75 and sum(r["status"] == "MISSING_OUTSIDE_APPROVED_75" for r in frontier) == 3
    assert set(closure["mandatory_external_imports"]) == set(previous["import_closure"]["mandatory_external_imports"])
    metadata = []
    for row in previous["metadata"]:
        data = (args.metadata_root / row["path"]).read_bytes()
        assert all(identities(data)[k] == row[k] for k in identities(data))
        metadata.append(row)
    sdk_plan_bytes = (ROOT / "manifests/phase-08d7-sdk-acquisition-plan.json").read_bytes()
    assert digest(sdk_plan_bytes) == "5543ed2470a56f0a3082ba51a1f81eb56b9ebc879aafaaf17d841365dd2f5b0a"
    wheelhouse = Path(json.loads(sdk_plan_bytes)["wheelhouse"])
    rehashed = 0
    for package in previous["known_package_lower_bound"]:
        artifact = package["selected_candidate_artifact"]
        if package["status"] == "READY_REHASHED_SDK_WHEEL":
            data = (wheelhouse / artifact["filename"]).read_bytes()
            assert len(data) == artifact["bytes"] and digest(data) == artifact["sha256"]
            rehashed += 1
        elif package["status"] == "READY_REHASHED_LOCAL_WHEEL":
            for local in package["local_matching_wheels"]:
                data = Path(local["path"]).read_bytes()
                assert len(data) == local["bytes"] and digest(data) == local["sha256"]
            rehashed += 1
    assert rehashed == 17
    # A new source byte cannot be parsed/accepted under the old pinned identity.
    try:
        verify((DESTINATION / entries[0]["path"]).read_bytes() + b"\n", rows[entries[0]["path"]])
    except ValueError:
        pass
    else:
        raise AssertionError("tampered source accepted")
    before = {str(p.relative_to(DESTINATION)): digest(p.read_bytes()) for p in DESTINATION.rglob("*") if p.is_file()}
    stopped = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "scripts/phase08d8_expanded_sources.py"),
                              "next", "--source-cache", str(args.source_cache), "--pinned-tree", str(args.pinned_tree),
                              "--plan-sha256", PLAN_HASH],
                             env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
                             capture_output=True, text=True, timeout=15)
    assert stopped.returncode != 0 and "previous group did not authorize further inspection" in stopped.stderr
    assert before == {str(p.relative_to(DESTINATION)): digest(p.read_bytes()) for p in DESTINATION.rglob("*") if p.is_file()}
    crypto_imports = []
    for path, data in sources.items():
        for node in ast.walk(ast.parse(data)):
            modules = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            if any(m == "cryptography" or m.startswith("cryptography.") for m in modules):
                crypto_imports.append({"path": path, "line": node.lineno})
    output = {"phase": "08D-8", "continuation_base": BASE,
              "authorization": "EXACT_75_SOURCE_FILES_ONLY_NO_EXECUTION",
              "reference_receipt_sha256": RECEIPT_SHA256, "frozen_plan_sha256": PLAN_HASH,
              "authorized_new_file_limit": 75, "authorized_new_byte_limit": 1305501,
              "acquired_verified_files": entries, "new_file_count": 3, "new_bytes": 101207,
              "prior_initializer_files_preserved": previous["acquired_verified_files"],
              "verified_source_count": len(sources), "groups": summaries,
              "stop_reason": "engine/db/__init__.py imports base, ops and result outside the approved 75",
              "acquisition_stopped": True, "import_closure": closure,
              "missing_source_frontier": frontier,
              "unacquired_approved_files": [r for r in plan["files"] if r["path"] not in {e["path"] for e in entries}],
              "metadata": metadata, "known_package_lower_bound": previous["known_package_lower_bound"],
              "rehashed_ready_wheel_artifacts": 17, "missing_selected_wheel_artifacts": 11,
              "crypto_direct_source_imports": crypto_imports,
              "cryptography": previous["cryptography"],
              "faithful_restricted_native_import": "UNKNOWN_NOT_YET_ESTABLISHED",
              "native_import_or_source_execution": 0, "package_download_install_build": 0,
              "checks": {"passed": 6, "failed": 0, "names": ["frozen_allowlist_and_pinned_tree",
                   "26_source_identities_and_transport_receipts", "group_reviews_and_expanded_graph",
                   "17_reusable_wheel_hashes_and_pinned_metadata", "tampered_source_rejected",
                   "STOP_rejects_before_curl_and_existing_files_unchanged"]},
              "runtime_gate": "BLOCKED_UNCHANGED", "D3": "PARTIAL", "D4": "BLOCKED", "D5": "PARTIAL"}
    with args.output.open("x") as stream:
        json.dump(output, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print("PASS: 6 static/integrity controls; 3 new sources / 101207 bytes; 3 new frontier files; acquisition STOPPED")


if __name__ == "__main__":
    main()
