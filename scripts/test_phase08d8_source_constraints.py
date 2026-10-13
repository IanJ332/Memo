"""Check source-only integrity and the mandatory acquisition STOP, without native imports."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from acquire_phase08d8_sources import DESTINATION, INITIALIZERS, load_plan, verify


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "manifests/phase-08d8-source-constraint-tests.json")
    args = parser.parse_args()
    plan = load_plan()
    rows = {r["path"]: r for r in plan["missing_source_acquisition_frontier"]}
    receipt = json.loads((ROOT / "manifests/phase-08d8-source-inspection.json").read_bytes())
    before = {str(p.relative_to(DESTINATION)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in DESTINATION.rglob("*") if p.is_file()}
    actual_files = {str(p.relative_to(DESTINATION)) for p in DESTINATION.rglob("*.py")}
    assert actual_files == set(INITIALIZERS)
    assert len(rows) == 31 and sum(r["bytes"] for r in rows.values()) == 586246
    assert receipt["aggregate_acquired_bytes"] == 7029
    for entry in receipt["acquired_verified_files"]:
        data = (DESTINATION / entry["path"]).read_bytes()
        identity = verify(data, rows[entry["path"]])
        assert all(entry[k] == v for k, v in identity.items())
        assert entry["http_status"] == 200 and entry["tls_verify_result"] == 0 and entry["redirects"] == 0
        assert entry["effective_url"] == rows[entry["path"]]["url"]
    data = (DESTINATION / INITIALIZERS[0]).read_bytes()
    try:
        verify(data + b"\n", rows[INITIALIZERS[0]])
    except ValueError as error:
        assert "identity mismatch" in str(error)
    else:
        raise AssertionError("tampered initializer accepted")
    result = subprocess.run(
        [sys.executable, "-I", "-B", str(ROOT / "scripts/acquire_phase08d8_sources.py"), "--stage", "remaining"],
        env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0 and "_thread_limits outside authorized allowlist" in result.stderr
    assert before == {str(p.relative_to(DESTINATION)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in DESTINATION.rglob("*") if p.is_file()}
    missing = receipt["missing_source_frontier"]
    assert len(missing) == 75
    assert sum(r["status"] == "MISSING_OUTSIDE_AUTHORIZED_ALLOWLIST" for r in missing) == 47
    assert sum(r["status"] == "MISSING_ALLOWLISTED_NOT_ACQUIRED" for r in missing) == 28
    assert len(receipt["known_package_lower_bound"]) == 28
    assert {"asyncpg", "orjson"} <= {r["name"] for r in receipt["known_package_lower_bound"]}
    assert receipt["source_execution_native_import_constructor_sdk_request"] == 0
    assert receipt["runtime_gate"] == "BLOCKED_UNCHANGED"
    output = {"phase": "08D-8", "scope": "SOURCE_ONLY_CONSTRAINTS",
              "checks": ["immutable_31_file_allowlist_and_limit", "three_initializer_transport_and_integrity_receipts",
                         "tampered_initializer_rejected", "remaining_acquisition_rejected_before_curl_and_files_unchanged",
                         "expanded_frontier_and_package_lower_bound_consistent"],
              "passed": 5, "failed": 0, "network_requests": 0, "native_or_sdk_imports": 0,
              "runtime_gate": "BLOCKED_UNCHANGED"}
    with args.output.open("x") as stream:
        json.dump(output, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print("PASS: 5 source-only constraint checks; STOP before curl; original files/log unchanged")


if __name__ == "__main__":
    main()
