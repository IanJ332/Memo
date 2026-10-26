"""Offline descriptive view of the completed Freeze-v1 cohort; no provider imports."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

BASE = "artifacts/phase06b/"
ORIGINAL = BASE + "derived/20261001T183940Z-1fc4c4929532/freeze-v1-raw-runs.provenance-repaired.jsonl"
SUPPLEMENT = BASE + "supplements/attempts/20261002T000350Z-c272b34d2cc3/supplement-raw-runs.jsonl"
COMBINED = BASE + "supplements/derived/20261002T000350Z-c272b34d2cc3/combined-derived-runs.jsonl"
FREEZE = "0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b"


def summarize(rows: list[dict]) -> dict:
    ids = [r["run_id"] for r in rows]
    expected = {
        f"freeze-v1__{p}__{s}__r{n}"
        for p, scenarios in {"mem0": ("S0", "S1", "S2", "S3"),
                             "hindsight": tuple(f"S{i}" for i in range(6)),
                             "openviking": ("S0", "S2", "S3", "S4")}.items()
        for s in scenarios for n in (1, 2, 3)
    }
    if len(ids) != len(set(ids)) or set(ids) != expected:
        raise ValueError("historical coverage or duplicate identity")
    if any(r["freeze_sha256"] != FREEZE for r in rows):
        raise ValueError("freeze identity")
    error = next(r for r in rows if r["run_id"] == "freeze-v1__openviking__S0__r2")
    if error["operation_status"] != "ERROR":
        raise ValueError("immutable ERROR was replaced")
    groups = []
    for provider, scenario in sorted({(r["provider"], r["scenario"]) for r in rows}):
        group = [r for r in rows if (r["provider"], r["scenario"]) == (provider, scenario)]
        groups.append({
            "provider": provider, "scenario": scenario, "registered_rows": len(group),
            "operation_status": dict(Counter(r["operation_status"] for r in group)),
            "legacy_exact_visibility": dict(Counter(r["exact_visibility_outcome"] for r in group)),
            "legacy_authority_exposure": dict(Counter(r["authority_exposure_outcome"] for r in group)),
            "runs": [{"run_id": r["run_id"], "attempt_id": r["attempt_id"],
                      "tested_git_commit": r["tested_git_commit"],
                      "execution_origin": r["execution_origin"],
                      # Candidate rows omit empty queries. Zero here is a recorded-row
                      # count, never proof that a query ran successfully or state vanished.
                      "recorded_candidate_rows_by_phase": dict(Counter(c["phase"] for c in r["retrievals"])),
                      "selected_context": "NOT_ESTABLISHED_BY_THIS_TABLE"}
                     for r in group],
        })
    return {"schema": "MEMLIFE_HISTORICAL_LIFECYCLE_DESCRIPTIVE_V1",
            "evidence_kind": "OFFLINE_REANALYSIS_OF_HISTORICAL_DERIVED_ROWS",
            "new_native_observations": 0, "registered_rows": len(rows),
            "operation_status": dict(Counter(r["operation_status"] for r in rows)),
            "downstream_calls": sum(r["rq3_calls"] for r in rows),
            "groups": groups}


def analyze(root: Path) -> dict:
    sources = {}
    inventory = []
    for path, origin in ((ORIGINAL, "ORIGINAL"), (SUPPLEMENT, "SUPPLEMENT")):
        data = (root / path).read_bytes()
        inventory.append({"path": path, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
        for line in data.splitlines():
            row = json.loads(line)
            row["execution_origin"] = origin
            if row["run_id"] in sources:
                raise ValueError("duplicate source identity")
            sources[row["run_id"]] = row
    data = (root / COMBINED).read_bytes()
    rows = [json.loads(line) for line in data.splitlines()]
    if {r["run_id"]: r for r in rows} != sources:
        raise ValueError("combined rows differ from source records")
    result = summarize(rows)
    result["inputs"] = inventory + [{"path": COMBINED, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}]
    result["source_comparison"] = "ALL_FIELDS_EQUAL_EXCEPT_DERIVED_EXECUTION_ORIGIN"
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.root)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
