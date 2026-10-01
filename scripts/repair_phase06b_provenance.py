#!/usr/bin/env python3
"""Create a provenance-only derivative of one preserved Phase 06B attempt."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from memlife.runner.storage_batch import (  # noqa: E402
    canonical_json,
    read_jsonl,
    validate_artifacts,
    write_jsonl,
)

ATTEMPT_PATTERN = re.compile(r"\d{8}T\d{6}Z-[0-9a-f]{12}")
DERIVED_NAME = "freeze-v1-raw-runs.provenance-repaired.jsonl"
MANIFEST_NAME = "provenance-repair-manifest.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def _remote_attempt_id(path_value: object) -> str:
    parts = str(path_value).replace("\\", "/").rstrip("/").split("/")
    if len(parts) < 2:
        raise ValueError("remote artifact path does not contain an attempt directory")
    return parts[-2]


def write_repaired_rows(source: Path, derived: Path, attempt_id: str) -> tuple[int, str]:
    """Add only ``attempt_id`` while proving the source bytes remain unchanged."""

    if derived.exists():
        raise FileExistsError(f"refusing to overwrite derived artifact: {derived}")
    source_before = sha256_file(source)
    rows = read_jsonl(source)
    if any("attempt_id" in row for row in rows):
        raise ValueError("source rows already contain attempt_id")
    repaired = [{**row, "attempt_id": attempt_id} for row in rows]
    write_jsonl(repaired, derived)
    if sha256_file(source) != source_before:
        raise RuntimeError("source artifact changed during provenance repair")
    for original, augmented in zip(rows, repaired, strict=True):
        restored = dict(augmented)
        if restored.pop("attempt_id", None) != attempt_id or restored != original:
            raise RuntimeError("derived row changed a field other than attempt_id")
    return len(rows), source_before


def repair_attempt(
    attempt_dir: Path,
    *,
    output_dir: Path,
    attempt_id: str,
    repair_code_commit: str,
    repair_timestamp: str,
) -> dict[str, Any]:
    if not ATTEMPT_PATTERN.fullmatch(attempt_id):
        raise ValueError("invalid attempt ID")
    if attempt_dir.name != attempt_id:
        raise ValueError("enclosing attempt directory does not match requested attempt ID")
    if not re.fullmatch(r"[0-9a-f]{40}", repair_code_commit):
        raise ValueError("repair code commit must be a full lowercase Git object ID")

    source = attempt_dir / "freeze-v1-raw-runs.jsonl"
    derived = output_dir / DERIVED_NAME
    manifest_path = output_dir / MANIFEST_NAME
    if manifest_path.exists():
        raise FileExistsError(f"refusing to overwrite repair manifest: {manifest_path}")

    names = (
        "blocker-evidence.json",
        "execution-ledger.json",
        "freeze-v1-aggregate.json",
        "freeze-v1-raw-runs.jsonl",
        "freeze-v1-residual-index.json",
        "lifecycle-session.json",
        "planned-runs.json",
        "remote-result.json",
    )
    original_hashes = {name: sha256_file(attempt_dir / name) for name in names}
    remote = _load_json(attempt_dir / "remote-result.json")
    lifecycle = _load_json(attempt_dir / "lifecycle-session.json")
    ledger = _load_json(attempt_dir / "execution-ledger.json")
    plan = _load_json(attempt_dir / "planned-runs.json")
    aggregate = _load_json(attempt_dir / "freeze-v1-aggregate.json")
    residual = _load_json(attempt_dir / "freeze-v1-residual-index.json")
    source_rows = read_jsonl(source)

    evidence_attempt_ids = {
        attempt_dir.name,
        remote.get("attempt_id"),
        lifecycle.get("attempt_id"),
        lifecycle.get("remote_work", {}).get("attempt_id"),
        *(
            _remote_attempt_id(remote.get(field))
            for field in (
                "raw_result_path",
                "aggregate_path",
                "residual_index_path",
                "execution_ledger_path",
            )
        ),
    }
    if evidence_attempt_ids != {attempt_id}:
        raise ValueError(f"PROVENANCE_REPAIR_UNSAFE: mixed attempt IDs {evidence_attempt_ids}")
    if len(source_rows) != 32:
        raise ValueError("PROVENANCE_REPAIR_UNSAFE: source object count is not 32")
    if any("attempt_id" in row for row in source_rows):
        raise ValueError("PROVENANCE_REPAIR_UNSAFE: source attempt_id state is not uniform")

    raw_ids = [str(row["run_id"]) for row in source_rows]
    raw_namespaces = [str(row["namespace"]) for row in source_rows]
    planned_by_id = {str(row["run_id"]): row for row in plan["runs"]}
    if len(raw_ids) != len(set(raw_ids)) or len(raw_namespaces) != len(set(raw_namespaces)):
        raise ValueError("PROVENANCE_REPAIR_UNSAFE: duplicate raw identity")
    if set(raw_ids) - set(planned_by_id):
        raise ValueError("PROVENANCE_REPAIR_UNSAFE: raw run is outside frozen plan")
    if set(raw_ids) != {str(value) for value in ledger["completed_run_ids"]}:
        raise ValueError("PROVENANCE_REPAIR_UNSAFE: execution ledger/raw run mismatch")
    for row in source_rows:
        spec = planned_by_id[str(row["run_id"])]
        if any(row.get(field) != spec.get(field) for field in ("provider", "scenario", "repetition", "namespace")):
            raise ValueError("PROVENANCE_REPAIR_UNSAFE: raw identity differs from frozen plan")

    tested_commits = {row.get("tested_git_commit") for row in source_rows}
    freeze_ids = {row.get("freeze_id") for row in source_rows}
    freeze_hashes = {row.get("freeze_sha256") for row in source_rows}
    expected_commit = remote.get("tested_commit")
    expected_freeze_id = remote.get("freeze_id")
    expected_freeze_hash = remote.get("freeze_sha256")
    if tested_commits != {expected_commit}:
        raise ValueError("PROVENANCE_REPAIR_UNSAFE: tested commit inconsistency")
    if freeze_ids != {expected_freeze_id} or freeze_ids != {plan.get("freeze_id")}:
        raise ValueError("PROVENANCE_REPAIR_UNSAFE: freeze ID inconsistency")
    if freeze_hashes != {expected_freeze_hash} or freeze_hashes != {plan.get("freeze_sha256")}:
        raise ValueError("PROVENANCE_REPAIR_UNSAFE: freeze hash inconsistency")

    output_dir.mkdir(parents=True, exist_ok=True)
    count, source_hash = write_repaired_rows(source, derived, attempt_id)
    repaired_rows = read_jsonl(derived)
    validation_errors = validate_artifacts(
        plan=plan,
        raw_runs=repaired_rows,
        aggregate=aggregate,
        residual=residual,
        require_complete=False,
        expected_attempt_id=attempt_id,
        expected_tested_commit=str(expected_commit),
    )
    if validation_errors:
        derived.unlink(missing_ok=True)
        raise ValueError(f"derived artifact validation failed: {validation_errors}")

    repo_source = source.relative_to(REPO_ROOT).as_posix()
    repo_derived = derived.relative_to(REPO_ROOT).as_posix()
    manifest: dict[str, Any] = {
        "repair_schema_version": "1.0",
        "source_attempt_id": attempt_id,
        "source_artifact_path": repo_source,
        "source_artifact_sha256": source_hash,
        "derived_artifact_path": repo_derived,
        "derived_artifact_sha256": sha256_file(derived),
        "source_object_count": count,
        "derived_object_count": len(repaired_rows),
        "exact_transformation_rule": (
            f'For each source JSON object, add "attempt_id": "{attempt_id}"; '
            "preserve every pre-existing key and value."
        ),
        "fields_added": ["attempt_id"],
        "fields_modified": [],
        "fields_removed": [],
        "proof_sources_used": [
            {"path": str(attempt_dir.relative_to(REPO_ROOT).as_posix()), "finding": f"enclosing directory name is {attempt_id}"},
            {"path": f"{attempt_dir.relative_to(REPO_ROOT).as_posix()}/remote-result.json", "sha256": original_hashes["remote-result.json"], "finding": "attempt_id and every remote artifact path identify the same attempt"},
            {"path": f"{attempt_dir.relative_to(REPO_ROOT).as_posix()}/lifecycle-session.json", "sha256": original_hashes["lifecycle-session.json"], "finding": "session attempt_id and embedded remote_work attempt_id identify the same attempt"},
            {"path": f"{attempt_dir.relative_to(REPO_ROOT).as_posix()}/execution-ledger.json", "sha256": original_hashes["execution-ledger.json"], "finding": "32 completed run IDs are exactly the 32 raw run IDs; remote-result locates this ledger in the same remote attempt directory"},
            {"path": "remote artifact paths recorded in remote-result.json and lifecycle-session.json", "finding": f"all parent directories end in attempts/{attempt_id}"},
        ],
        "tested_commit": expected_commit,
        "freeze_id": expected_freeze_id,
        "freeze_sha256": expected_freeze_hash,
        "repair_timestamp": repair_timestamp,
        "repair_code_commit": repair_code_commit,
        "original_artifact_sha256": original_hashes,
        "validation": {
            "status": "PASS",
            "object_count": len(repaired_rows),
            "unique_run_ids": len(set(raw_ids)),
            "unique_namespaces": len(set(raw_namespaces)),
            "attempt_id_consistency": "PASS",
            "freeze_consistency": "PASS",
            "tested_commit_consistency": "PASS",
            "downstream_decision_model_calls": sum(int(row["downstream_decision_model_calls"]) for row in repaired_rows),
            "raw_to_aggregate_consistency": "PASS",
            "aggregate_to_residual_consistency": "PASS",
            "fourth_repetitions": 0,
            "duplicate_executions": 0,
        },
    }
    manifest_path.write_text(canonical_json(manifest), encoding="utf-8")
    if sha256_file(source) != source_hash:
        raise RuntimeError("source artifact changed after manifest creation")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--repair-code-commit", required=True)
    parser.add_argument("--repair-timestamp", default=datetime.now(timezone.utc).isoformat())
    args = parser.parse_args()
    manifest = repair_attempt(
        args.attempt_dir.resolve(),
        output_dir=args.output_dir.resolve(),
        attempt_id=args.attempt_id,
        repair_code_commit=args.repair_code_commit,
        repair_timestamp=args.repair_timestamp,
    )
    print(canonical_json(manifest), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
