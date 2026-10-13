"""Exact remaining 75-file source-only authorization, with immutable group evidence."""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import phase08d8_expanded_sources as historical
from inspect_phase08d8_sources import build_closure, analyze, source_module

BASE = "d11a081855b84b85522fde6ad25deeb34a37ceaa"
REFERENCE = ROOT / "manifests/phase-08d8-expanded-source-inspection.json"
REFERENCE_SHA256 = "c7bf586e727475ec4a8c045f11ac9b1ab3036435e2b1ddb9fd08d2d5151cde17"
PRIOR_LOG_SHA256 = "2aea0ce3a97e5a6aba0db50f53c201731ece7aea820b83cd515d2a1dca6a4694"
PLAN_PATH = ROOT / "manifests/phase-08d8-remaining-source-plan.json"
GROUPS = historical.DESTINATION / "remaining-groups"
LOG = historical.DESTINATION / "remaining-acquisition.jsonl"
PREFIX, PIN = historical.PREFIX, historical.PIN
DATABASE_FIRST = [PREFIX + "engine/db/" + p for p in ("base.py", "ops.py", "result.py")]


def prior(tree_path, cache):
    older, indexed = historical.reference(tree_path)
    sources = historical.existing_sources(older, cache)
    raw = REFERENCE.read_bytes()
    if historical.digest(raw) != REFERENCE_SHA256:
        raise ValueError("STOP: authorized remaining-source receipt changed")
    receipt = json.loads(raw)
    if historical.digest(historical.LOG.read_bytes()) != PRIOR_LOG_SHA256:
        raise ValueError("STOP: prior expanded acquisition log changed")
    for row in receipt["acquired_verified_files"]:
        data = (historical.DESTINATION / row["path"]).read_bytes()
        historical.verify(data, row)
        if historical.digest(data) != row["sha256"]:
            raise ValueError("STOP: prior verified source changed")
        sources[row["path"]] = data
    if len(sources) != 26:
        raise ValueError("STOP: prior 26-source evidence incomplete")
    rows = receipt["missing_source_frontier"]
    if len(rows) != 75 or len({r["path"] for r in rows}) != 75 or sum(r["bytes"] for r in rows) != 1259799:
        raise ValueError("STOP: remaining 75-file/byte scope changed")
    for row in rows:
        p = Path(row["path"])
        if p.is_absolute() or ".." in p.parts or not row["path"].startswith(PREFIX) or p.suffix != ".py":
            raise ValueError("STOP: invalid approved source path")
        item = indexed[row["path"]]
        if row["git_blob_sha1"] != item["sha"] or row["bytes"] != item["size"]:
            raise ValueError("STOP: remaining source/tree identity mismatch")
        if row["url"] != f"https://raw.githubusercontent.com/vectorize-io/hindsight/{PIN}/{row['path']}" or row["path"] in sources:
            raise ValueError("STOP: incorrect pinned URL or attempted reacquisition")
    return receipt, indexed, sources


def freeze(receipt):
    rows = [{k: r[k] for k in ("path", "url", "git_blob_sha1", "bytes", "required_purpose")}
            for r in receipt["missing_source_frontier"]]
    order = sorted(r["path"] for r in rows if r["path"].endswith("/__init__.py"))
    order += sorted(r["path"] for r in rows if r["path"] not in set(DATABASE_FIRST) | set(order))
    groups = [DATABASE_FIRST] + [[p] for p in order]
    assert {p for g in groups for p in g} == {r["path"] for r in rows}
    plan = {"phase": "08D-8", "continuation_base": BASE, "upstream_commit": PIN,
            "reference_receipt_sha256": REFERENCE_SHA256, "pinned_tree_sha256": historical.TREE_SHA256,
            "authorization": "EXACT_REMAINING_SOURCE_FRONTIER_ONLY",
            "maximum_new_files": 75, "maximum_new_bytes": 1259799,
            "files": rows, "dependency_groups": groups,
            "six_prior_acquisitions_must_remain_unchanged": True,
            "scope": "SOURCE_ACQUISITION_AND_STATIC_INSPECTION_ONLY",
            "new_frontier_action": "STOP", "package_or_native_execution_authorized": False,
            "runtime_gate": "BLOCKED_UNCHANGED"}
    with PLAN_PATH.open("x") as stream:
        json.dump(plan, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print("FROZEN plan SHA256=" + historical.digest(PLAN_PATH.read_bytes()))


def inspect_next(plan, plan_hash, receipt, indexed, sources):
    group_files = sorted(GROUPS.glob("group-*.json")) if GROUPS.exists() else []
    entries = [json.loads(s) for s in LOG.read_text().splitlines()] if LOG.exists() else []
    rows = {r["path"]: r for r in plan["files"]}
    if sum(len(g) for g in plan["dependency_groups"][:len(group_files)]) != len(entries):
        raise RuntimeError("STOP: partial previous group; evidence retained")
    for i, file in enumerate(group_files, 1):
        group = json.loads(file.read_bytes())
        if group["status"] != "STATIC_GROUP_REVIEW_PENDING" or group["plan_sha256"] != plan_hash:
            raise RuntimeError("STOP: prior group exposed a required outside source or prohibited initialization")
        review_file = GROUPS / f"review-{i:03}.json"
        review = json.loads(review_file.read_bytes()) if review_file.exists() else {}
        if (review.get("verdict") != "CONTINUE_STATIC_INSPECTION" or review.get("group_sha256") != historical.digest(file.read_bytes())
                or review.get("plan_sha256") != plan_hash):
            raise RuntimeError("STOP: static group review missing or mismatched")
    for entry in entries:
        data = (historical.DESTINATION / entry["path"]).read_bytes()
        historical.verify(data, rows[entry["path"]])
        if historical.digest(data) != entry["sha256"]:
            raise ValueError("STOP: new source evidence changed")
        sources[entry["path"]] = data
    if len(group_files) >= len(plan["dependency_groups"]):
        raise RuntimeError("STOP: approved set exhausted")
    head = subprocess.check_output(["/usr/bin/git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != BASE:
        raise RuntimeError("STOP: wrong authorized acquisition base")
    next_group = plan["dependency_groups"][len(group_files)]
    total = sum(r["bytes"] for r in entries)
    if len(entries) + len(next_group) > 75 or total + sum(rows[p]["bytes"] for p in next_group) > 1259799:
        raise RuntimeError("STOP: remaining acquisition limits")
    acquired = []
    for path in next_group:
        data, entry = historical.acquire(rows[path])  # Same strict curl/exclusive/hash-before-parse primitive.
        sources[path] = data
        with LOG.open("a" if LOG.exists() else "x") as stream:
            stream.write(json.dumps(entry, sort_keys=True) + "\n")
        acquired.append(entry)
    closure = build_closure(sources, indexed)
    frontier = []
    for path, reasons in sorted(closure.pop("missing").items()):
        row = indexed[path]
        frontier.append({"path": path, "bytes": row["size"], "git_blob_sha1": row["sha"], "sha256": None,
                         "url": f"https://raw.githubusercontent.com/vectorize-io/hindsight/{PIN}/{path}",
                         "required_purpose": reasons,
                         "status": "MISSING_APPROVED_UNACQUIRED" if path in rows else "MISSING_OUTSIDE_APPROVED_REMAINING_75"})
    outside = [r for r in frontier if r["status"] == "MISSING_OUTSIDE_APPROVED_REMAINING_75"]
    GROUPS.mkdir(exist_ok=True)
    group = {"phase": "08D-8", "group_number": len(group_files) + 1, "plan_sha256": plan_hash,
             "newly_acquired": acquired, "aggregate_new_files": len(entries) + len(acquired),
             "aggregate_new_bytes": total + sum(r["bytes"] for r in acquired),
             "status": "STOP_NEW_REQUIRED_SOURCE" if outside or closure["unresolved_module_names"] else "STATIC_GROUP_REVIEW_PENDING",
             "analysis": {p: analyze(sources[p], source_module(p), p.endswith("/__init__.py")) for p in next_group},
             "import_closure": closure, "missing_source_frontier": frontier,
             "outside_required_source_count": len(outside), "source_execution": False, "runtime_gate": "BLOCKED_UNCHANGED"}
    with (GROUPS / f"group-{len(group_files) + 1:03}.json").open("x") as stream:
        json.dump(group, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"VERIFIED group {group['group_number']}: {len(acquired)} files; total {group['aggregate_new_files']} / {group['aggregate_new_bytes']} bytes; {group['status']}; outside={len(outside)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("freeze", "next"))
    parser.add_argument("--source-cache", type=Path, required=True)
    parser.add_argument("--pinned-tree", type=Path, required=True)
    parser.add_argument("--plan-sha256")
    args = parser.parse_args()
    if sys.prefix == sys.base_prefix or ".venv" not in Path(sys.prefix).parts or not sys.flags.isolated:
        raise RuntimeError("STOP: existing repository .venv with -I -B required")
    branch = subprocess.check_output(["/usr/bin/git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
    head = subprocess.check_output(["/usr/bin/git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if branch != "phase-08d8-native-runtime-preparation" or (args.mode == "freeze" and head != BASE):
        raise RuntimeError("STOP: wrong branch/base")
    receipt, indexed, sources = prior(args.pinned_tree, args.source_cache)
    if args.mode == "freeze":
        freeze(receipt)
    else:
        raw = PLAN_PATH.read_bytes()
        if not args.plan_sha256 or historical.digest(raw) != args.plan_sha256:
            raise ValueError("STOP: frozen remaining plan changed")
        plan = json.loads(raw)
        if plan["files"] != [{k: r[k] for k in ("path", "url", "git_blob_sha1", "bytes", "required_purpose")}
                              for r in receipt["missing_source_frontier"]]:
            raise ValueError("STOP: frozen plan differs from approved source set")
        inspect_next(plan, args.plan_sha256, receipt, indexed, sources)


if __name__ == "__main__":
    main()
