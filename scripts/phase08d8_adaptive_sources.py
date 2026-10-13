"""Bounded adaptive pinned first-party source acquisition; no upstream execution.

Every discovery is logged before acquisition. Request intents persist before
curl; failures consume request budget and stop. Source-only authorization never
grants native startup, package installation or an import-safety classification.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import phase08d8_remaining_sources as previous_run
from inspect_phase08d8_sources import build_closure, analyze, source_module

old = previous_run.historical
BASE = "d226f7859fae94df0055cda43c5900571b0d66d5"
REF_PATH = ROOT / "manifests/phase-08d8-remaining-source-closure.json"
REF_HASH = "ca0d9b4996ce73e8b7192317938417ee9945e8738c9931b5c74f0f251d875cd0"
LAST_LOG_HASH = "4155d6ea4f7a51cb80be3a590dba7642b9286b1e37e44770777decd1f9cf0327"
PLAN = ROOT / "manifests/phase-08d8-adaptive-source-plan.json"
LOCAL = old.DESTINATION / "adaptive"
DISCOVERIES = LOCAL / "discoveries.jsonl"
REQUESTS = LOCAL / "requests.jsonl"
ACQUIRED = LOCAL / "acquired.jsonl"
MAX_FILES, MAX_BYTES, MAX_REQUESTS = 150, 3500000, 200
FIRST = old.PREFIX + "engine/reflect/agent.py"


def read_jsonl(path):
    return [json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []


def append(path, value):
    with path.open("a" if path.exists() else "x") as stream:
        stream.write(json.dumps(value, sort_keys=True) + "\n")
        stream.flush()


def prior(tree_path, cache):
    _, indexed, sources = previous_run.prior(tree_path, cache)
    raw = REF_PATH.read_bytes()
    if old.digest(raw) != REF_HASH or old.digest(previous_run.LOG.read_bytes()) != LAST_LOG_HASH:
        raise ValueError("STOP: historical source receipt/log changed")
    receipt = json.loads(raw)
    for row in receipt["acquired_verified_files"]:
        data = (old.DESTINATION / row["path"]).read_bytes()
        old.verify(data, row)
        if old.digest(data) != row["sha256"]:
            raise ValueError("STOP: previously acquired source changed")
        sources[row["path"]] = data
    if len(sources) != 30:
        raise ValueError("STOP: incomplete historical 30-source evidence")
    # Check every historical phase manifest against the authorized starting Git
    # commit. This protects all source plans/receipts, not only the newest link.
    manifests = {}
    historical_paths = subprocess.check_output(["/usr/bin/git", "ls-tree", "-r", "--name-only", BASE, "manifests"], cwd=ROOT, text=True).splitlines()
    for relative in sorted(p for p in historical_paths if p.startswith("manifests/phase-08d") and p.endswith(".json")):
        path = ROOT / relative
        committed = subprocess.check_output(["/usr/bin/git", "show", BASE + ":" + relative], cwd=ROOT)
        if path.read_bytes() != committed:
            raise ValueError("STOP: historical phase manifest changed: " + relative)
        manifests[relative] = old.digest(committed)
    return receipt, indexed, sources, manifests


def identity(path, indexed, reasons):
    p = Path(path)
    if (not path.startswith(old.PREFIX) or p.suffix != ".py" or p.is_absolute()
            or ".." in p.parts or path not in indexed):
        raise ValueError("STOP: required source outside pinned authorized Python subtree: " + path)
    row = indexed[path]
    if row["type"] != "blob":
        raise ValueError("STOP: required source is not a pinned blob")
    return {"path": path, "git_blob_sha1": row["sha"], "bytes": row["size"],
            "url": f"https://raw.githubusercontent.com/vectorize-io/hindsight/{old.PIN}/{path}",
            "mandatory_import_provenance": reasons}


def freeze(receipt, indexed, sources, manifests):
    seed = [identity(r["path"], indexed, r["required_purpose"]) for r in receipt["missing_source_frontier"]]
    if len(seed) != 72 or sum(r["bytes"] for r in seed) != 1294510 or any(r["path"] in sources for r in seed):
        raise ValueError("STOP: wrong initial adaptive frontier")
    plan = {"phase": "08D-8", "continuation_base": BASE, "upstream_commit": old.PIN,
            "reference_receipt_sha256": REF_HASH, "pinned_tree_sha256": old.TREE_SHA256,
            "authorization": "USER_GRANTED_BOUNDED_ADAPTIVE_PINNED_SOURCE_ONLY",
            "maximum_additional_files": MAX_FILES, "maximum_additional_bytes": MAX_BYTES,
            "maximum_https_request_attempts": MAX_REQUESTS, "source_prefix": old.PREFIX,
            "allowed_extension": ".py", "first_source": FIRST, "initial_frontier": seed,
            "historical_manifest_sha256": manifests,
            "new_mandatory_imports_inside_pinned_subtree": "APPEND_DISCOVERY_BEFORE_ACQUISITION",
            "package_and_native_execution_authorized": False, "runtime_gate": "BLOCKED_UNCHANGED"}
    with PLAN.open("x") as stream:
        json.dump(plan, stream, indent=2, sort_keys=True)
        stream.write("\n")
    LOCAL.mkdir()  # Exclusive continuation evidence namespace.
    for row in seed:
        append(DISCOVERIES, {**row, "discovery_index": len(read_jsonl(DISCOVERIES)) + 1,
                             "origin": "INITIAL_72_FRONTIER", "reference_receipt_sha256": REF_HASH})
    print("FROZEN adaptive plan SHA256=" + old.digest(PLAN.read_bytes()))


def restore(indexed, sources):
    discovered = read_jsonl(DISCOVERIES)
    by_path = {}
    for row in discovered:
        if row["path"] in by_path:
            raise ValueError("STOP: duplicate discovery record")
        expected = identity(row["path"], indexed, row["mandatory_import_provenance"])
        if any(row[k] != expected[k] for k in expected):
            raise ValueError("STOP: discovery/tree identity mismatch")
        by_path[row["path"]] = row
    acquired = read_jsonl(ACQUIRED)
    requests = read_jsonl(REQUESTS)
    if len(requests) != len(acquired):
        raise RuntimeError("STOP: failed/incomplete request consumes budget; do not silently retry")
    if len(acquired) > MAX_FILES or len(requests) > MAX_REQUESTS or sum(r["bytes"] for r in acquired) > MAX_BYTES:
        raise RuntimeError("STOP: adaptive resource limit exceeded")
    for ordinal, row in enumerate(acquired, 1):
        if row["path"] in sources or row["path"] not in by_path:
            raise ValueError("STOP: reacquired/undiscovered source")
        if requests[ordinal - 1]["request_ordinal"] != ordinal or requests[ordinal - 1]["path"] != row["path"]:
            raise ValueError("STOP: request/acquisition attribution mismatch")
        data = (old.DESTINATION / row["path"]).read_bytes()
        old.verify(data, by_path[row["path"]])
        if old.digest(data) != row["sha256"]:
            raise ValueError("STOP: acquired adaptive source changed")
        sources[row["path"]] = data
    return by_path, acquired, requests


def snapshot(indexed, sources, plan_hash, batch):
    closure = build_closure(sources, indexed)
    if closure["unresolved_module_names"]:
        status = "STOP_UNRESOLVED_REQUIRED_IMPORT"
    else:
        status = "STATIC_BATCH_REVIEW_PENDING"
    frontier = []
    ledger = {r["path"]: r for r in read_jsonl(DISCOVERIES)}
    for path, reasons in sorted(closure.pop("missing").items()):
        row = identity(path, indexed, reasons)
        frontier.append(row)
        if path not in ledger:
            entry = {**row, "origin": "NEW_MANDATORY_IMPORT", "discovery_index": len(ledger) + 1,
                     "discovered_after_batch": batch, "plan_sha256": plan_hash,
                     "trigger_source_sha256": {r["required_by"]: old.digest(sources[r["required_by"]])
                            for r in reasons if r.get("required_by") in sources}}
            append(DISCOVERIES, entry)
            ledger[path] = entry
    acquired = read_jsonl(ACQUIRED)
    request_count = len(read_jsonl(REQUESTS))
    # Only unambiguous direct import-phase startup calls are stop findings.
    # Other executable statements retain UNKNOWN side effects for human review.
    blocked_names = {"MemoryEngine", "WorkerPoller", "SentenceTransformer", "CrossEncoder",
                     "asyncpg.create_pool", "uvicorn.run", "ray.init", "subprocess.Popen", "asyncio.create_task"}
    prohibited = [{"path": "hindsight-api-slim/" + module.replace(".", "/") + ".py", **call}
                  for module, data in closure["graph"].items() for call in data["import_phase_calls"]
                  if call["call"] in blocked_names and not call["conditions"]]
    if prohibited:
        status = "STOP_DEMONSTRABLE_PROHIBITED_IMPORT_CALL"
    record = {"phase": "08D-8", "batch": batch, "plan_sha256": plan_hash, "status": status,
              "files": len(acquired), "bytes": sum(r["bytes"] for r in acquired), "https_requests": request_count,
              "newly_acquired": acquired if batch == 1 else [], "import_closure": closure,
              "missing_source_frontier": frontier, "prohibited_direct_call_findings": prohibited,
              "source_execution": False, "import_safety": "UNKNOWN_STATIC_ONLY", "runtime_gate": "BLOCKED_UNCHANGED"}
    with (LOCAL / f"batch-{batch:03}.json").open("x") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"BATCH {batch}: files={record['files']} bytes={record['bytes']} requests={request_count} missing={len(frontier)} modules={len(closure['visited_modules'])} status={status}", flush=True)


def next_batch(plan_hash, size, indexed, sources):
    files = sorted(LOCAL.glob("batch-*.json"))
    for number, file in enumerate(files, 1):
        receipt = json.loads(file.read_bytes())
        review_path = LOCAL / f"review-{number:03}.json"
        review = json.loads(review_path.read_bytes()) if review_path.exists() else {}
        if review.get("verdict") == "STOP_FEASIBILITY_GRAPH_RESOLVED":
            raise RuntimeError("STOP: source graph sufficient for feasibility; no further acquisition authorized by engineering decision")
        if receipt["status"] != "STATIC_BATCH_REVIEW_PENDING":
            raise RuntimeError("STOP: previous batch has a blocking static finding")
        if (review.get("verdict") != "CONTINUE_STATIC_INSPECTION" or review.get("batch_sha256") != old.digest(file.read_bytes())
                or review.get("plan_sha256") != plan_hash):
            raise RuntimeError("STOP: batch static review missing or mismatched")
    discovered, acquired, requests = restore(indexed, sources)
    closure = build_closure(sources, indexed)
    if closure["unresolved_module_names"]:
        raise RuntimeError("STOP: required import cannot be resolved reliably")
    for path, reasons in closure["missing"].items():
        if path not in discovered:
            raise RuntimeError("STOP: missing pre-acquisition discovery record")
    missing = list(closure["missing"])
    if not missing:
        raise RuntimeError("STOP: mandatory static source graph complete; no unnecessary acquisition")
    if not acquired:
        order = [FIRST]
    else:
        def priority(path):
            return (0 if path.endswith("/__init__.py") else 1,
                    len(Path(path).parts), path)
        order = sorted(missing, key=priority)[:size]
    total = sum(r["bytes"] for r in acquired)
    count, request_count = len(acquired), len(requests)
    head = subprocess.check_output(["/usr/bin/git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != BASE:
        raise RuntimeError("STOP: acquisition bound to authorized starting commit")
    for path in order:
        row = discovered[path]
        if count + 1 > MAX_FILES or total + row["bytes"] > MAX_BYTES or request_count + 1 > MAX_REQUESTS:
            append(LOCAL / "stop.jsonl", {"reason": "RESOURCE_LIMIT", "path": path, "files": count,
                   "bytes": total, "requests": request_count})
            raise RuntimeError("STOP: adaptive resource limit reached")
        request_count += 1
        append(REQUESTS, {"request_ordinal": request_count, "path": path, "url": row["url"],
                          "discovery_index": row["discovery_index"], "plan_sha256": plan_hash,
                          "request_intent_persisted_before_curl": True})
        try:
            data, evidence = old.acquire(row)
        except Exception as error:
            append(LOCAL / "stop.jsonl", {"reason": "ACQUISITION_OR_INTEGRITY_FAILURE", "path": path,
                   "request_ordinal": request_count, "exception_class": type(error).__name__})
            raise
        append(ACQUIRED, evidence)
        sources[path] = data
        count += 1
        total += len(data)
        print("VERIFIED " + path + f" ({len(data)} bytes)", flush=True)
    snapshot(indexed, sources, plan_hash, len(files) + 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("freeze", "next"))
    parser.add_argument("--source-cache", type=Path, required=True)
    parser.add_argument("--pinned-tree", type=Path, required=True)
    parser.add_argument("--plan-sha256")
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()
    if sys.prefix == sys.base_prefix or ".venv" not in Path(sys.prefix).parts or not sys.flags.isolated:
        raise RuntimeError("STOP: existing repository .venv with -I -B required")
    if not 1 <= args.batch_size <= 8:
        raise ValueError("STOP: batch size must be 1..8")
    branch = subprocess.check_output(["/usr/bin/git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
    if branch != "phase-08d8-native-runtime-preparation":
        raise RuntimeError("STOP: wrong review branch")
    receipt, indexed, sources, manifests = prior(args.pinned_tree, args.source_cache)
    if args.mode == "freeze":
        if subprocess.check_output(["/usr/bin/git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != BASE:
            raise RuntimeError("STOP: wrong adaptive starting commit")
        freeze(receipt, indexed, sources, manifests)
    else:
        raw = PLAN.read_bytes()
        if not args.plan_sha256 or old.digest(raw) != args.plan_sha256:
            raise ValueError("STOP: adaptive frozen plan hash mismatch")
        next_batch(args.plan_sha256, args.batch_size, indexed, sources)


if __name__ == "__main__":
    main()
