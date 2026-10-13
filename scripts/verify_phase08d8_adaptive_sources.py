"""Finalize adaptive source/metadata evidence offline; no upstream or SDK imports."""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import phase08d8_adaptive_sources as run
from phase08d8_package_closure import closure as package_closure, active
from inspect_phase08d8_sources import build_closure

PLAN_HASH = "5916fcffee52ae100e3245d1e7412fdf9aeae75b9b05414bbdcc718a87af1ca9"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-cache", type=Path, required=True)
    parser.add_argument("--pinned-tree", type=Path, required=True)
    parser.add_argument("--metadata-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    def deny(event, arguments):
        if event.startswith("socket.") or (event == "import" and arguments[0].startswith(("hindsight", "openai", "httpx", "aiohttp"))):
            raise RuntimeError("STOP: native/SDK/network event during static verification")
    sys.addaudithook(deny)
    previous, indexed, sources, historical_manifests = run.prior(args.pinned_tree, args.source_cache)
    assert run.old.digest(run.PLAN.read_bytes()) == PLAN_HASH
    discovered, acquired, requests = run.restore(indexed, sources)
    assert len(acquired) == 101 and len(requests) == 101 and sum(r["bytes"] for r in acquired) == 1692988
    assert len(discovered) == 101 and acquired[0]["path"] == run.FIRST
    assert len(acquired) <= 150 and len(requests) <= 200 and sum(r["bytes"] for r in acquired) <= 3500000
    expected_local = {p for p in sources if (run.old.DESTINATION / p).exists()}
    assert {str(p.relative_to(run.old.DESTINATION)) for p in run.old.DESTINATION.rglob("*.py")} == expected_local
    assert not list(run.old.DESTINATION.rglob("*.part"))
    for row in acquired:
        assert row["http_status"] == 200 and row["tls_verify_result"] == 0 and row["redirects"] == 0
        assert row["url"] == row["effective_url"] == discovered[row["path"]]["url"]
    batches = []
    for number, path in enumerate(sorted(run.LOCAL.glob("batch-*.json")), 1):
        batch = json.loads(path.read_bytes())
        review = json.loads(path.with_name(f"review-{number:03}.json").read_bytes())
        assert review["batch_sha256"] == run.old.digest(path.read_bytes()) and review["plan_sha256"] == PLAN_HASH
        assert batch["status"] == "STATIC_BATCH_REVIEW_PENDING" and batch["prohibited_direct_call_findings"] == []
        batches.append({"batch": number, "batch_sha256": run.old.digest(path.read_bytes()),
                        "files": batch["files"], "bytes": batch["bytes"], "https_requests": batch["https_requests"],
                        "missing_source_count": len(batch["missing_source_frontier"]), "review": review})
    assert len(batches) == 15 and batches[-1]["review"]["verdict"] == "STOP_FEASIBILITY_GRAPH_RESOLVED"
    graph = build_closure(sources, indexed)
    assert graph["missing"] == {} and graph["unresolved_module_names"] == []
    assert len(graph["visited_modules"]) == 125 and len(graph["graph"]) == 125
    verified_sources = [{"path": p, **run.old.identities(data), "origin": "ADAPTIVE_ACQUISITION" if p in {r["path"] for r in acquired} else "PREVIOUSLY_VERIFIED"}
                        for p, data in sorted(sources.items())]
    assert len(verified_sources) == 131
    for row in previous["metadata"]:
        data = (args.metadata_root / row["path"]).read_bytes()
        assert all(run.old.identities(data)[k] == row[k] for k in run.old.identities(data))
    lock = tomllib.loads((args.metadata_root / "uv.lock").read_text())
    inventory = json.loads((ROOT / "manifests/phase-08d7-dependency-preparation.json").read_bytes())
    packages = package_closure(graph["mandatory_external_imports"], lock, inventory)
    assert len(packages["package_versions"]) == 61
    assert packages["package_versions"]["cryptography"] == "50.0.0"
    assert {("google-genai", "google-auth"), ("google-auth", "cryptography")} <= {(e["from"], e["to"]) for e in packages["edges"]}
    sdk_raw = (ROOT / "manifests/phase-08d7-sdk-acquisition-plan.json").read_bytes()
    assert run.old.digest(sdk_raw) == "5543ed2470a56f0a3082ba51a1f81eb56b9ebc879aafaaf17d841365dd2f5b0a"
    sdk_plan = json.loads(sdk_raw); wheelhouse = Path(sdk_plan["wheelhouse"])
    sdk_rows = {r["name"]: r["selected_candidate_artifact"] for r in previous["known_package_lower_bound"] if r["status"] == "READY_REHASHED_SDK_WHEEL"}
    inventory_rows = {r["name"]: r for r in inventory["packages"]}
    wheel_inventory = []
    for name, version in packages["package_versions"].items():
        row = inventory_rows[name]; local = row["local_matching_wheels"]
        if name in sdk_rows:
            artifact = sdk_rows[name]; data = (wheelhouse / artifact["filename"]).read_bytes()
            assert len(data) == artifact["bytes"] and run.old.digest(data) == artifact["sha256"]
            status = "READY_REHASHED_SDK_WHEEL"
        else:
            for artifact in local:
                data = Path(artifact["path"]).read_bytes()
                assert len(data) == artifact["bytes"] and run.old.digest(data) == artifact["sha256"]
            status = "READY_REHASHED_LOCAL_WHEEL" if local else "MISSING_COMPATIBLE_LOCK_WHEEL" if row["compatible_upstream_wheels"] else "BLOCKED_NO_COMPATIBLE_LOCK_WHEEL"
        wheel_inventory.append({"name": name, "version": version, "status": status,
                                "existing_wheels": local, "sdk_artifact": sdk_rows.get(name),
                                "compatible_locked_candidates": row["compatible_upstream_wheels"],
                                "installation_authorized": False})
    conditional = [{"required_by": module, **edge} for module, body in graph["graph"].items()
                   for edge in body["imports"] if edge["conditions"] or edge["phase"] != "IMPORT"]
    deferred_missing = []
    for edge in conditional:
        module = edge["module"]
        if module.startswith("hindsight_api"):
            stem = "hindsight-api-slim/" + module.replace(".", "/")
            for candidate in (stem + ".py", stem + "/__init__.py"):
                if candidate in indexed and candidate not in sources:
                    deferred_missing.append({"path": candidate, "git_blob_sha1": indexed[candidate]["sha"],
                                             "bytes": indexed[candidate]["size"], "trigger": edge})
                    break
    assert not active("sys_platform == 'win32'") and active("python_full_version < '3.13'")
    try:
        active("unrecognized_variable == 'x'")
    except ValueError: pass
    else: raise AssertionError("unknown marker accepted")
    try:
        run.old.verify((run.old.DESTINATION / acquired[0]["path"]).read_bytes() + b"\n", discovered[acquired[0]["path"]])
    except ValueError: pass
    else: raise AssertionError("tampered source accepted")
    try:
        run.identity("hindsight-api-slim/hindsight_api/../main.py", indexed, [])
    except ValueError: pass
    else: raise AssertionError("outside/ambiguous source path accepted")
    before = {str(p): run.old.digest(p.read_bytes()) for p in run.old.DESTINATION.rglob("*") if p.is_file()}
    blocked = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "scripts/phase08d8_adaptive_sources.py"), "next",
                "--source-cache", str(args.source_cache), "--pinned-tree", str(args.pinned_tree), "--plan-sha256", PLAN_HASH],
                env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True, timeout=15)
    assert blocked.returncode != 0 and "source graph sufficient for feasibility" in blocked.stderr
    assert before == {str(p): run.old.digest(p.read_bytes()) for p in run.old.DESTINATION.rglob("*") if p.is_file()}
    output = {"phase": "08D-8", "continuation_base": run.BASE, "upstream_commit": run.old.PIN,
              "authorization": "BOUNDED_ADAPTIVE_SOURCE_ONLY", "frozen_plan_sha256": PLAN_HASH,
              "reference_receipt_sha256": run.REF_HASH, "historical_manifests_unchanged": historical_manifests,
              "limits": {"files": 150, "bytes": 3500000, "requests": 200},
              "new_files": 101, "new_bytes": 1692988, "https_request_attempts": 101, "failed_requests": 0,
              "verified_sources": verified_sources, "acquisition_evidence": acquired,
              "discovery_ledger": list(discovered.values()), "new_mandatory_discoveries": 29,
              "batches": batches, "mandatory_literal_source_graph": graph,
              "mandatory_missing_sources": [], "conditional_deferred_type_only_imports": conditional,
              "unacquired_nonmandatory_source_edges": deferred_missing,
              "source_graph_status": "MANDATORY_LITERAL_GRAPH_RESOLVED_NOT_RUNTIME_PROOF",
              "minimum_pinned_package_closure": packages, "wheel_inventory": wheel_inventory,
              "wheel_readiness": dict(Counter(r["status"] for r in wheel_inventory)),
              "cryptography": {"ordinary_import_package_closure": "REQUIRED_BY_GOOGLE_GENAI_GOOGLE_AUTH_METADATA",
                    "version": "50.0.0", "sdk_only": "NOT_REQUIRED", "third_party_import_executed": False,
                    "locked_intel_macos_compatible_wheels": 0, "workaround_proposed": False},
              "engineering_decision": "B_PROPOSE_SEPARATELY_REVIEWED_REAL_PROVIDER_BOUNDARY_ARCHITECTURE",
              "option_B_implemented": False, "runtime_safe": "UNKNOWN_UNEXECUTED",
              "native_source_execution_or_provider_sdk_calls": 0, "package_download_install_build": 0,
              "checks": {"passed": 8, "failed": 0, "names": ["historical_receipts_131_sources_and_pinned_tree",
                     "adaptive_provenance_request_order_and_limits", "15_batch_reviews_and_literal_graph_closure",
                     "61_package_target_metadata_closure_and_crypto_chain", "available_wheel_hashes",
                     "metadata_marker_target_and_unknown_rejection", "source_tamper_and_outside_path_rejection",
                     "feasibility_STOP_before_curl_and_existing_evidence_unchanged"]},
              "runtime_gate": "BLOCKED_UNCHANGED", "D3": "PARTIAL", "D4": "BLOCKED", "D5": "PARTIAL"}
    with args.output.open("x") as stream:
        json.dump(output, stream, indent=2, sort_keys=True); stream.write("\n")
    print("PASS: 8 static/integrity controls; 101 files / 1692988 bytes / 101 requests; 61 packages; select B, no implementation")
    print("WHEEL_READINESS " + json.dumps(output["wheel_readiness"], sort_keys=True))
    print(f"NONMANDATORY_UNACQUIRED_EDGES {len(deferred_missing)}")


if __name__ == "__main__": main()
