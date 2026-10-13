"""Freeze and inspect the exact authorized 75-file frontier, one dependency group at a time.

Only source HTTPS acquisition is possible. Hindsight/SDK imports, execution,
installation and out-of-allowlist acquisition are never performed.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from acquire_phase08d8_sources import identities, verify, PIN, PREFIX, DESTINATION
from inspect_phase08d8_sources import ALIASES, build_closure, analyze, source_module

BASE = "0e6d6a7d3d6faa5fc21fb6cae89fb45da91e30ef"
RECEIPT_SHA256 = "053ef0d487dd4c546732bfcedf9ff08f6fb70908018cd02cc2aa54036afaf038"
TREE_SHA256 = "b23c03c1c9daf42b764988da19b5aa70e7bd710c8b05092f290773acef35ed33"
INITIAL_LOG_SHA256 = "4e84d2c2de36fbd0df87a3a2baa2ff68b117f977c117b7dfc542e942f9aa00ee"
PLAN_PATH = ROOT / "manifests/phase-08d8-expanded-source-plan.json"
GROUPS = DESTINATION / "expanded-groups"
LOG = DESTINATION / "expanded-acquisition.jsonl"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def reference(tree_path):
    raw = (ROOT / "manifests/phase-08d8-source-inspection.json").read_bytes()
    if digest(raw) != RECEIPT_SHA256:
        raise ValueError("STOP: authorized 75-file reference receipt changed")
    receipt = json.loads(raw)
    tree_raw = tree_path.read_bytes()
    if digest(tree_raw) != TREE_SHA256:
        raise ValueError("STOP: pinned source tree changed")
    tree = json.loads(tree_raw)
    if tree["sha"] != PIN or tree["truncated"] is not False:
        raise ValueError("STOP: wrong/truncated pinned tree")
    indexed = {r["path"]: r for r in tree["tree"] if r["type"] == "blob"}
    rows = receipt["missing_source_frontier"]
    if len(rows) != 75 or len({r["path"] for r in rows}) != 75 or sum(r["bytes"] for r in rows) != 1305501:
        raise ValueError("STOP: 75-file scope or byte limit changed")
    for row in rows:
        p = Path(row["path"])
        if p.is_absolute() or ".." in p.parts or not row["path"].startswith(PREFIX) or p.suffix != ".py":
            raise ValueError("STOP: invalid allowlisted path")
        item = indexed[row["path"]]
        if row["git_blob_sha1"] != item["sha"] or row["bytes"] != item["size"]:
            raise ValueError("STOP: allowlist/tree identity mismatch")
        if row["url"] != f"https://raw.githubusercontent.com/vectorize-io/hindsight/{PIN}/{row['path']}":
            raise ValueError("STOP: source URL is not exactly pinned")
    return receipt, indexed


def existing_sources(receipt, cache):
    source = {}
    if digest((DESTINATION / "acquisition.jsonl").read_bytes()) != INITIAL_LOG_SHA256:
        raise ValueError("STOP: prior initializer acquisition log changed")
    for row in receipt["verified_existing_sources"]:
        relative = row["path"].removeprefix(PREFIX)
        data = (cache / ALIASES.get(relative, Path(relative).name)).read_bytes()
        verify(data, row)
        if digest(data) != row["sha256"]:
            raise ValueError("STOP: existing verified source changed")
        source[row["path"]] = data
    for row in receipt["acquired_verified_files"]:
        data = (DESTINATION / row["path"]).read_bytes()
        verify(data, row)
        if digest(data) != row["sha256"]:
            raise ValueError("STOP: prior initializer changed")
        source[row["path"]] = data
    return source


def freeze(receipt, indexed, sources):
    rows = [{k: r[k] for k in ("path", "url", "git_blob_sha1", "bytes", "purposes")}
            for r in receipt["missing_source_frontier"]]
    priority = [PREFIX + "_thread_limits.py", PREFIX + "engine/cross_encoder.py"]
    # Engine's first eager child is cross_encoder. Singleton dependency groups
    # minimize additional retrieval before a newly exposed frontier is checked.
    priority += sorted(r["path"] for r in rows if r["path"].endswith("/__init__.py"))
    order = list(dict.fromkeys(priority + sorted(r["path"] for r in rows)))
    if set(order) != {r["path"] for r in rows} or any(p in sources for p in order):
        raise ValueError("STOP: unexpected acquisition order or existing source in new plan")
    plan = {"phase": "08D-8", "base_commit": BASE, "upstream_commit": PIN,
            "authorization": "USER_GRANTED_EXACT_EXPANDED_SOURCE_FRONTIER_ONLY",
            "reference_receipt_sha256": RECEIPT_SHA256, "pinned_tree_sha256": TREE_SHA256,
            "maximum_new_files": 75, "maximum_new_bytes": 1305501, "files": rows,
            "dependency_groups": [[p] for p in order],
            "scope": "SOURCE_ACQUISITION_AND_STATIC_INSPECTION_ONLY",
            "prohibited": ["new_frontier_acquisition", "wheel_download", "package_install", "source_build",
                           "native_import", "provider_construction", "SDK_request", "model_or_database_initialization"],
            "runtime_gate": "BLOCKED_UNCHANGED"}
    with PLAN_PATH.open("x") as stream:
        json.dump(plan, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print("FROZEN plan SHA256=" + digest(PLAN_PATH.read_bytes()))


def acquire(row):
    target = DESTINATION / row["path"]
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".py.part")
    if target.exists():
        raise RuntimeError("STOP: cannot overwrite/reacquire source")
    command = ["/usr/bin/curl", "-q", "--fail", "--silent", "--show-error", "--proto", "=https",
               "--tlsv1.2", "--proxy", "", "--noproxy", "*", "--max-redirs", "0", "--max-time", "60",
               "--max-filesize", str(row["bytes"]), "--url", row["url"], "--output", "-", "--write-out",
               "%{stderr}%{http_code}\n%{ssl_verify_result}\n%{num_redirects}\n%{url_effective}\n%{size_download}\n"]
    with partial.open("xb") as stream:
        result = subprocess.run(command, env={}, stdin=subprocess.DEVNULL, stdout=stream,
                                stderr=subprocess.PIPE, timeout=65)
    fields = result.stderr.decode().strip().splitlines()
    if result.returncode != 0 or len(fields) != 5:
        raise RuntimeError("STOP: acquisition failed; partial evidence retained")
    status, tls, redirects, effective, downloaded = fields
    data = partial.read_bytes()
    if (status != "200" or tls != "0" or redirects != "0" or effective != row["url"]
            or int(float(downloaded)) != len(data)):
        raise RuntimeError("STOP: HTTPS constraints failed")
    identity = verify(data, row)  # Before parsing.
    ast.parse(data, filename=row["path"])
    os.link(partial, target)
    partial.unlink()
    return data, {"path": row["path"], "url": row["url"], **identity, "http_status": 200,
                  "tls_verify_result": 0, "redirects": 0, "effective_url": effective,
                  "identity_verified_before_parsing": True, "source_executed": False}


def inspect_group(plan, receipt, indexed, sources, plan_hash):
    prior_groups = sorted(GROUPS.glob("group-*.json")) if GROUPS.exists() else []
    entries = [json.loads(s) for s in LOG.read_text().splitlines()] if LOG.exists() else []
    rows = {r["path"]: r for r in plan["files"]}
    if len(entries) != len(prior_groups):
        raise RuntimeError("STOP: incomplete prior group; do not silently resume")
    for i, group_file in enumerate(prior_groups):
        group = json.loads(group_file.read_bytes())
        if group["plan_sha256"] != plan_hash or group["status"] != "STATIC_GROUP_REVIEW_PENDING":
            raise RuntimeError("STOP: previous group did not authorize further inspection")
        # Human/agent static review is explicitly persisted before another curl.
        reviewed = GROUPS / f"review-{i + 1:03}.json"
        review = json.loads(reviewed.read_bytes()) if reviewed.exists() else {}
        if (review.get("verdict") != "CONTINUE_STATIC_INSPECTION"
                or review.get("group_sha256") != digest(group_file.read_bytes())
                or review.get("plan_sha256") != plan_hash):
            raise RuntimeError("STOP: prior group needs static side-effect review")
    for entry in entries:
        data = (DESTINATION / entry["path"]).read_bytes()
        verify(data, rows[entry["path"]])
        if digest(data) != entry["sha256"]:
            raise ValueError("STOP: acquired source changed")
        sources[entry["path"]] = data
    if len(entries) >= 75:
        raise RuntimeError("STOP: maximum new file count reached")
    next_path = plan["dependency_groups"][len(entries)][0]
    row = rows[next_path]
    # A static STOP can be reverified from later review commits, but new
    # acquisition remains bound to the exact human-authorized starting commit.
    current_head = subprocess.check_output(["/usr/bin/git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if current_head != BASE:
        raise RuntimeError("STOP: wrong acquisition base")
    total = sum(r["bytes"] for r in entries)
    if total + row["bytes"] > 1305501:
        raise RuntimeError("STOP: aggregate source bound")
    data, entry = acquire(row)
    sources[next_path] = data
    GROUPS.mkdir(exist_ok=True)
    with LOG.open("a" if entries else "x") as stream:
        stream.write(json.dumps(entry, sort_keys=True) + "\n")
    closure = build_closure(sources, indexed)
    frontier = []
    for path, reasons in sorted(closure.pop("missing").items()):
        item = indexed[path]
        frontier.append({"path": path, "git_blob_sha1": item["sha"], "bytes": item["size"],
                         "url": f"https://raw.githubusercontent.com/vectorize-io/hindsight/{PIN}/{path}",
                         "required_purpose": reasons, "sha256": None,
                         "status": "MISSING_APPROVED_UNACQUIRED" if path in rows else "MISSING_OUTSIDE_APPROVED_75"})
    outside = [r for r in frontier if r["status"] == "MISSING_OUTSIDE_APPROVED_75"]
    analysis = analyze(data, source_module(next_path), next_path.endswith("/__init__.py"))
    group = {"phase": "08D-8", "group_number": len(entries) + 1, "plan_sha256": plan_hash,
             "status": "STOP_NEW_REQUIRED_SOURCE" if outside or closure["unresolved_module_names"] else "STATIC_GROUP_REVIEW_PENDING",
             "newly_acquired": entry, "aggregate_new_files": len(entries) + 1,
             "aggregate_new_bytes": total + len(data), "analysis": analysis, "import_closure": closure,
             "missing_source_frontier": frontier, "new_outside_source_count": len(outside),
             "native_source_execution": 0, "runtime_gate": "BLOCKED_UNCHANGED"}
    with (GROUPS / f"group-{len(entries) + 1:03}.json").open("x") as stream:
        json.dump(group, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"VERIFIED {next_path}: {len(data)} bytes; {group['status']}; outside={len(outside)}")


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
        raise RuntimeError("STOP: wrong acquisition branch/base")
    receipt, indexed = reference(args.pinned_tree)
    sources = existing_sources(receipt, args.source_cache)
    if args.mode == "freeze":
        freeze(receipt, indexed, sources)
    else:
        raw = PLAN_PATH.read_bytes()
        if not args.plan_sha256 or digest(raw) != args.plan_sha256:
            raise ValueError("STOP: frozen acquisition plan hash mismatch")
        plan = json.loads(raw)
        if plan["files"] != [{k: r[k] for k in ("path", "url", "git_blob_sha1", "bytes", "purposes")}
                              for r in receipt["missing_source_frontier"]]:
            raise ValueError("STOP: frozen plan differs from authorized source set")
        inspect_group(plan, receipt, indexed, sources, args.plan_sha256)


if __name__ == "__main__":
    main()
