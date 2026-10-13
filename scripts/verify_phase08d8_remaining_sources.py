"""Verify remaining-source acquisition/closure offline without importing upstream code."""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import phase08d8_remaining_sources as run
from inspect_phase08d8_sources import build_closure

PLAN_HASH = "579e8fe5b860bf3ce0a627e94c70161f7a06096628f7d65bafb20a8d2c0387fd"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-cache", type=Path, required=True)
    parser.add_argument("--pinned-tree", type=Path, required=True)
    parser.add_argument("--metadata-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sys.prefix == sys.base_prefix or ".venv" not in Path(sys.prefix).parts or not sys.flags.isolated:
        raise RuntimeError("STOP: repository .venv with -I -B required")

    def deny(event, arguments):
        if event.startswith("socket.") or (event == "import" and arguments[0].startswith(("hindsight", "openai", "httpx", "aiohttp"))):
            raise RuntimeError("STOP: networking/native import during static verification")
    sys.addaudithook(deny)
    previous, indexed, sources = run.prior(args.pinned_tree, args.source_cache)
    plan_raw = run.PLAN_PATH.read_bytes()
    assert run.historical.digest(plan_raw) == PLAN_HASH
    plan = json.loads(plan_raw)
    rows = {r["path"]: r for r in plan["files"]}
    assert len(rows) == 75 and sum(r["bytes"] for r in rows.values()) == 1259799
    entries = [json.loads(s) for s in run.LOG.read_text().splitlines()]
    assert len(entries) == 4 and sum(r["bytes"] for r in entries) == 56318
    assert [r["path"] for r in entries] == [p for g in plan["dependency_groups"][:2] for p in g]
    for entry in entries:
        data = (run.historical.DESTINATION / entry["path"]).read_bytes()
        identity = run.historical.verify(data, rows[entry["path"]])
        assert all(entry[k] == v for k, v in identity.items())
        assert entry["url"] == entry["effective_url"] == rows[entry["path"]]["url"]
        assert entry["http_status"] == 200 and entry["tls_verify_result"] == 0 and entry["redirects"] == 0
        sources[entry["path"]] = data
    assert len(sources) == 30 and not list(run.historical.DESTINATION.rglob("*.part"))
    expected_local = {r["path"] for r in previous["prior_initializer_files_preserved"] + previous["acquired_verified_files"] + entries}
    assert {str(p.relative_to(run.historical.DESTINATION)) for p in run.historical.DESTINATION.rglob("*.py")} == expected_local
    summaries = []
    for number in (1, 2):
        file = run.GROUPS / f"group-{number:03}.json"
        group = json.loads(file.read_bytes())
        review = json.loads((run.GROUPS / f"review-{number:03}.json").read_bytes())
        assert review["group_sha256"] == run.historical.digest(file.read_bytes()) and review["plan_sha256"] == PLAN_HASH
        assert review["verdict"] == ("CONTINUE_STATIC_INSPECTION" if number == 1 else "STOP_NEW_REQUIRED_SOURCE")
        summaries.append({"group": number, "group_receipt_sha256": run.historical.digest(file.read_bytes()),
                          "review": review, "newly_acquired": group["newly_acquired"], "status": group["status"],
                          "known_modules": len(group["import_closure"]["visited_modules"]),
                          "verified_reachable_bodies": len(group["import_closure"]["graph"]),
                          "missing_source_count": len(group["missing_source_frontier"]),
                          "outside_required_source_count": group["outside_required_source_count"]})
    closure = build_closure(sources, indexed)
    frontier = []
    for path, reasons in sorted(closure.pop("missing").items()):
        row = indexed[path]
        frontier.append({"path": path, "bytes": row["size"], "git_blob_sha1": row["sha"], "sha256": None,
                         "url": f"https://raw.githubusercontent.com/vectorize-io/hindsight/{run.PIN}/{path}",
                         "required_purpose": reasons,
                         "status": "MISSING_APPROVED_UNACQUIRED" if path in rows else "MISSING_OUTSIDE_APPROVED_REMAINING_75"})
    assert len(frontier) == 72 and sum(r["status"] == "MISSING_OUTSIDE_APPROVED_REMAINING_75" for r in frontier) == 1
    assert set(closure["mandatory_external_imports"]) == set(previous["import_closure"]["mandatory_external_imports"])
    for row in previous["metadata"]:
        data = (args.metadata_root / row["path"]).read_bytes()
        assert all(run.historical.identities(data)[k] == row[k] for k in run.historical.identities(data))
    sdk_bytes = (ROOT / "manifests/phase-08d7-sdk-acquisition-plan.json").read_bytes()
    assert run.historical.digest(sdk_bytes) == "5543ed2470a56f0a3082ba51a1f81eb56b9ebc879aafaaf17d841365dd2f5b0a"
    wheelhouse = Path(json.loads(sdk_bytes)["wheelhouse"])
    ready = 0
    for package in previous["known_package_lower_bound"]:
        artifact = package["selected_candidate_artifact"]
        if package["status"] == "READY_REHASHED_SDK_WHEEL":
            data = (wheelhouse / artifact["filename"]).read_bytes()
            assert len(data) == artifact["bytes"] and run.historical.digest(data) == artifact["sha256"]
            ready += 1
        elif package["status"] == "READY_REHASHED_LOCAL_WHEEL":
            for local in package["local_matching_wheels"]:
                data = Path(local["path"]).read_bytes()
                assert len(data) == local["bytes"] and run.historical.digest(data) == local["sha256"]
            ready += 1
    assert ready == 17
    try:
        run.historical.verify((run.historical.DESTINATION / entries[0]["path"]).read_bytes() + b"\n", rows[entries[0]["path"]])
    except ValueError:
        pass
    else:
        raise AssertionError("tampered database source accepted")
    before = {str(p): run.historical.digest(p.read_bytes()) for p in run.historical.DESTINATION.rglob("*") if p.is_file()}
    blocked = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "scripts/phase08d8_remaining_sources.py"), "next",
                              "--source-cache", str(args.source_cache), "--pinned-tree", str(args.pinned_tree), "--plan-sha256", PLAN_HASH],
                             env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
                             capture_output=True, text=True, timeout=15)
    assert blocked.returncode != 0 and "prior group exposed a required outside source" in blocked.stderr
    assert before == {str(p): run.historical.digest(p.read_bytes()) for p in run.historical.DESTINATION.rglob("*") if p.is_file()}
    crypto = []
    for path, data in sources.items():
        for node in ast.walk(ast.parse(data)):
            modules = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            if any(m == "cryptography" or m.startswith("cryptography.") for m in modules):
                crypto.append({"path": path, "line": node.lineno})
    output = {"phase": "08D-8", "continuation_base": run.BASE, "upstream_commit": run.PIN,
              "authorization": "EXACT_REMAINING_75_SOURCE_FILES_ONLY",
              "reference_receipt_sha256": run.REFERENCE_SHA256, "frozen_plan_sha256": PLAN_HASH,
              "authorized_new_file_limit": 75, "authorized_new_byte_limit": 1259799,
              "acquired_verified_files": entries, "new_file_count": 4, "new_bytes": 56318,
              "six_prior_files_preserved": previous["prior_initializer_files_preserved"] + previous["acquired_verified_files"],
              "verified_source_count": 30, "groups": summaries, "acquisition_stopped": True,
              "stop_reason": "reflect package initializer line 10 unconditionally imports unapproved engine/reflect/agent.py",
              "import_closure": closure, "missing_source_frontier": frontier,
              "unacquired_approved_files": [r for r in plan["files"] if r["path"] not in {e["path"] for e in entries}],
              "next_frontier_source_bytes": sum(r["bytes"] for r in frontier),
              "metadata": previous["metadata"], "known_package_lower_bound": previous["known_package_lower_bound"],
              "rehashed_ready_wheel_artifacts": 17, "missing_selected_wheel_artifacts": 11,
              "cryptography_direct_source_imports": crypto, "cryptography": previous["cryptography"],
              "native_import_closure": "INCOMPLETE", "faithful_import_and_construction_feasibility": "UNKNOWN",
              "native_import_or_source_execution": 0, "package_download_install_build": 0,
              "checks": {"passed": 6, "failed": 0, "names": ["frozen_scope_tree_and_existing_evidence",
                    "30_source_hashes_and_transport_receipts", "group_reviews_and_closure_integrity",
                    "17_reusable_wheels_and_pinned_metadata", "tampered_source_rejected_before_parsing",
                    "STOP_before_curl_and_all_existing_source_evidence_unchanged"]},
              "runtime_gate": "BLOCKED_UNCHANGED", "D3": "PARTIAL", "D4": "BLOCKED", "D5": "PARTIAL"}
    with args.output.open("x") as stream:
        json.dump(output, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print("PASS: 6 static/integrity controls; 4 new files / 56318 bytes; reflect agent frontier; acquisition STOPPED")


if __name__ == "__main__":
    main()
