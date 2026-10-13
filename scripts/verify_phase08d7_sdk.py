"""Verify the exact installed SDK wheel set and RECORDs without any network."""

from __future__ import annotations

import base64
import csv
import hashlib
import importlib
import importlib.metadata
import io
import json
from pathlib import Path
import sys
import sysconfig
import zipfile

from phase08d7_offline_guard import activate, verify_denial, DENIED_EVENTS
from acquire_phase08d7_sdk import ROOT, PLAN_SHA256, load_plan, verify, validate_stage

IMPORTS = {
    "annotated-types": "annotated_types", "anyio": "anyio", "certifi": "certifi",
    "distro": "distro", "h11": "h11", "httpcore": "httpcore", "httpx": "httpx",
    "idna": "idna", "jiter": "jiter", "openai": "openai", "pydantic": "pydantic",
    "pydantic-core": "pydantic_core", "sniffio": "sniffio", "tqdm": "tqdm",
    "typing-extensions": "typing_extensions", "typing-inspection": "typing_inspection",
}


def check_rows(rows, read, label: str) -> int:
    count = 0
    for name, hash_value, size in rows:
        if not hash_value:
            if not name.endswith(".dist-info/RECORD") or size:
                raise ValueError(f"STOP: unsupported unhashed RECORD member: {label}")
            continue
        algorithm, expected = hash_value.split("=", 1)
        if algorithm != "sha256":
            raise ValueError(f"STOP: unsupported RECORD hash algorithm: {label}")
        data = read(name)
        actual = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
        if actual != expected or len(data) != int(size):
            raise ValueError(f"STOP: RECORD integrity mismatch: {label}")
        count += 1
    return count


def main() -> None:
    activate()
    plan = load_plan()
    runtime = Path(plan["runtime"])
    if Path(sys.prefix) != runtime or sys.prefix == sys.base_prefix:
        raise RuntimeError("STOP: wrong verification environment")
    if "include-system-site-packages = false" not in (runtime / "pyvenv.cfg").read_text():
        raise RuntimeError("STOP: inherited system site packages")
    if any(Path(sysconfig.get_path("purelib")).glob("*.pth")):
        raise RuntimeError("STOP: unexpected .pth inheritance")
    guard = verify_denial()
    start_events = len(DENIED_EVENTS)
    staged = json.loads((Path(plan["wheelhouse"]).parent / "sdk-staged-wheels.json").read_text())
    validate_stage(plan, staged)
    expected = {x["name"]: x["version"] for x in staged["wheels"]}
    distributions = list(importlib.metadata.distributions())
    installed = {d.metadata["Name"].lower().replace("_", "-"): d.version for d in distributions}
    if installed != expected or len(distributions) != 16:
        raise RuntimeError("STOP: unexpected installed dependency set")
    by_name = {d.metadata["Name"].lower().replace("_", "-"): d for d in distributions}
    checks = []
    for artifact in sorted(staged["wheels"], key=lambda r: r["name"]):
        name = artifact["name"]
        wheel = Path(plan["wheelhouse"]) / artifact["filename"]
        verify(wheel, artifact, artifact)
        distribution = by_name[name]
        record = distribution.read_text("RECORD")
        if record is None:
            raise RuntimeError("STOP: missing installed RECORD")
        def read_installed(path: str) -> bytes:
            target = Path(distribution.locate_file(path)).resolve()
            if not target.is_relative_to(runtime):
                raise RuntimeError("STOP: installed RECORD escapes isolated environment")
            return target.read_bytes()
        installed_count = check_rows(csv.reader(io.StringIO(record)), read_installed, name)
        with zipfile.ZipFile(wheel) as archive:
            records = [n for n in archive.namelist()
                       if n.count("/") == 1 and n.endswith(".dist-info/RECORD")]
            if len(records) != 1:
                raise RuntimeError("STOP: missing or ambiguous wheel RECORD")
            wheel_record = archive.read(records[0]).decode()
            wheel_count = check_rows(csv.reader(io.StringIO(wheel_record)), archive.read, name)
            for path, hash_value, _ in csv.reader(io.StringIO(wheel_record)):
                if not hash_value:
                    continue
                if ".data/" in path:
                    raise RuntimeError("STOP: unsupported wheel .data relocation")
                if read_installed(path) != archive.read(path):
                    raise RuntimeError("STOP: installed bytes differ from authorized wheel")
        module = importlib.import_module(IMPORTS[name])
        if not Path(module.__file__).resolve().is_relative_to(runtime):
            raise RuntimeError("STOP: imported package is outside the isolated environment")
        checks.append({**artifact, "wheel_record_files_verified": wheel_count,
                       "installed_record_files_verified": installed_count,
                       "installed_bytes_match_wheel": True, "import": IMPORTS[name],
                       "installed_version": distribution.version})
    if len(DENIED_EVENTS) != start_events:
        raise RuntimeError("STOP: package import attempted networking")
    if any(name.startswith("hindsight") for name in sys.modules):
        raise RuntimeError("STOP: unexpected provider import")
    receipt = {"phase": "08D-7", "scope": "SDK_ONLY", "status": "INSTALLATION_VERIFIED",
               "authorized_plan_sha256": PLAN_SHA256, "python": sys.version.split()[0],
               "distribution_count": 16, "pip_check": "PASS", "guard": guard,
               "import_socket_or_dns_attempts": 0, "actual_socket_transmissions": 0,
               "packages": checks, "D3": "PARTIAL", "D4": "BLOCKED", "D5": "PARTIAL"}
    destination = ROOT / ".local/phase08d7/sdk-install-verification.json"
    with destination.open("x") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print("PASS: exact 16 distributions, wheel/installed RECORDs, imports and isolation verified")


if __name__ == "__main__":
    main()
