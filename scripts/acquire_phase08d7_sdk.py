"""Acquire only the user-authorized immutable SDK wheel allowlist; fail closed."""

from __future__ import annotations

import argparse
import email
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "manifests/phase-08d7-sdk-acquisition-plan.json"
PLAN_SHA256 = "5543ed2470a56f0a3082ba51a1f81eb56b9ebc879aafaaf17d841365dd2f5b0a"
SANDBOX = "(version 1)(allow default)(deny network*)"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_plan() -> dict:
    if digest(PLAN) != PLAN_SHA256:
        raise ValueError("authorized allowlist identity changed")
    plan = json.loads(PLAN.read_bytes())
    if len(plan["downloads"]) != 7 or len(plan["existing_local_artifacts"]) != 9:
        raise ValueError("unexpected dependency count")
    if Path(plan["wheelhouse"]) != ROOT / ".local/phase08d7/wheelhouse":
        raise ValueError("unexpected wheelhouse")
    if Path(plan["runtime"]) != ROOT / ".local/phase08d7/runtime/.venv":
        raise ValueError("unexpected isolated environment")
    return plan


def verify(path: Path, artifact: dict, package: dict) -> dict:
    if path.stat().st_size != artifact["bytes"] or digest(path) != artifact["sha256"]:
        raise ValueError(f"artifact size/hash mismatch: {package['name']}")
    with zipfile.ZipFile(path) as archive:
        names = [n for n in archive.namelist()
                 if n.count("/") == 1 and n.endswith(".dist-info/METADATA")]
        if len(names) != 1 or archive.testzip() is not None:
            raise ValueError(f"invalid wheel: {package['name']}")
        metadata = email.message_from_bytes(archive.read(names[0]))
        if (metadata["Name"].lower().replace("_", "-") != package["name"]
                or metadata["Version"] != package["version"]):
            raise ValueError(f"unexpected wheel identity: {package['name']}")
    return {"name": package["name"], "version": package["version"],
            "filename": path.name, "bytes": artifact["bytes"],
            "sha256": artifact["sha256"]}


def clean_environment() -> dict:
    return {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1", "PIP_CONFIG_FILE": os.devnull}


def validate_stage(plan: dict, staged: dict) -> None:
    expected = {p["name"]: (p["version"], p["artifacts"][0]["sha256"], p["artifacts"][0]["bytes"])
                for p in plan["downloads"] + plan["existing_local_artifacts"]}
    observed = {p["name"]: (p["version"], p["sha256"], p["bytes"]) for p in staged["wheels"]}
    if (staged["authorized_plan_sha256"] != PLAN_SHA256 or len(staged["wheels"]) != 16
            or observed != expected):
        raise ValueError("STOP: staged dependencies differ from immutable authorized allowlist")


def acquire(plan: dict) -> None:
    # Check all existing inputs before the first authorized network request.
    for package in plan["existing_local_artifacts"]:
        artifact = package["artifacts"][0]
        verify(Path(artifact["path"]), artifact, package)
    wheelhouse = Path(plan["wheelhouse"])
    wheelhouse.mkdir(mode=0o700)  # Exclusive; never replace an earlier stage.
    log = wheelhouse.parent / "sdk-acquisition-local.jsonl"
    records = []
    with log.open("x", encoding="utf-8") as stream:
        for package in plan["downloads"]:
            if len(package["artifacts"]) != 1:
                raise ValueError("ambiguous download artifact")
            artifact = package["artifacts"][0]
            url = urlsplit(artifact["url"])
            if (url.scheme != "https" or url.hostname != "files.pythonhosted.org"
                    or url.username or url.password or url.query or url.fragment
                    or Path(url.path).name != artifact["filename"]):
                raise ValueError("unexpected authorized URL")
            target = wheelhouse / artifact["filename"]
            temporary = target.with_suffix(".whl.part")
            with temporary.open("xb"):
                pass
            # -q must be first: no curlrc, netrc, inherited proxy or credentials.
            command = ["/usr/bin/curl", "-q", "--fail", "--silent", "--show-error",
                       "--proto", "=https", "--proxy", "", "--noproxy", "*",
                       "--max-redirs", "0", "--max-time", "60", "--url", artifact["url"],
                       "--output", str(temporary), "--write-out",
                       "%{http_code}\n%{ssl_verify_result}\n%{num_redirects}\n%{url_effective}\n"]
            result = subprocess.run(command, env={"PATH": "/usr/bin:/bin"},
                                    capture_output=True, text=True, timeout=65)
            if result.returncode:
                stream.write(json.dumps({"name": package["name"], "status": "STOP",
                                         "curl_exit_code": result.returncode}) + "\n")
                stream.flush()
                raise RuntimeError(f"STOP: acquisition failed for {package['name']}; curl exit {result.returncode}")
            fields = result.stdout.splitlines()
            if fields != ["200", "0", "0", artifact["url"]]:
                raise RuntimeError(f"STOP: HTTP/TLS/redirect policy failed for {package['name']}")
            record = verify(temporary, artifact, package)
            temporary.rename(target)
            record.update(filename=target.name, origin="AUTHORIZED_HTTPS", http_status=200,
                          tls_verification=True, redirects=0)
            records.append(record)
            stream.write(json.dumps(record, sort_keys=True) + "\n")
            stream.flush()
            print(f"verified download: {package['name']} {package['version']}", flush=True)
        for package in plan["existing_local_artifacts"]:
            artifact = package["artifacts"][0]
            if len(artifact["tags"]) != 1:
                raise ValueError("unsupported local wheel tag combination")
            filename = f"{package['name'].replace('-', '_')}-{package['version']}-{artifact['tags'][0]}.whl"
            source = Path(artifact["path"])
            verify(source, artifact, package)
            target = wheelhouse / filename
            with source.open("rb") as incoming, target.open("xb") as outgoing:
                shutil.copyfileobj(incoming, outgoing)
            record = verify(target, artifact, package)
            verify(source, artifact, package)  # Original cache file is unchanged.
            record["origin"] = "EXISTING_LOCAL_CACHE_COPY"
            records.append(record)
            stream.write(json.dumps(record, sort_keys=True) + "\n")
        if len(records) != 16 or len({r["name"] for r in records}) != 16:
            raise ValueError("unexpected staged dependency set")
    with (wheelhouse.parent / "sdk-staged-wheels.json").open("x") as stream:
        json.dump({"authorized_plan_sha256": PLAN_SHA256, "wheels": records}, stream, indent=2)
        stream.write("\n")
    with (wheelhouse.parent / "sdk-offline-requirements.txt").open("x") as stream:
        for record in sorted(records, key=lambda r: r["name"]):
            stream.write(f"{(wheelhouse / record['filename']).as_uri()} --hash=sha256:{record['sha256']}\n")
    print("PASS: seven downloads and nine immutable cache copies verified")


def install(plan: dict) -> None:
    runtime = Path(plan["runtime"])
    staged = json.loads((Path(plan["wheelhouse"]).parent / "sdk-staged-wheels.json").read_bytes())
    validate_stage(plan, staged)
    for record in staged["wheels"]:
        verify(Path(plan["wheelhouse"]) / record["filename"], record, record)
    installer = plan["installer"]
    if digest(Path(installer["metadata"]["path"])) != installer["metadata"]["sha256"]:
        raise ValueError("installer identity changed")
    runtime.parent.mkdir(mode=0o700)
    if runtime.exists():
        raise ValueError("isolated environment already exists")
    prefix = ["/usr/bin/sandbox-exec", "-p", SANDBOX]
    subprocess.run(prefix + [sys.executable, "-m", "venv", "--without-pip", str(runtime)],
                   env=clean_environment(), check=True)
    installer_python = str(Path(installer["repository_venv"]) / "bin/python")
    command = [installer_python, "-m", "pip", "--isolated", "--python", str(runtime),
               "--disable-pip-version-check", "install", "--no-index", "--no-deps",
               "--require-hashes", "--only-binary=:all:", "--no-cache-dir", "--no-compile",
               "-r", str(Path(plan["wheelhouse"]).parent / "sdk-offline-requirements.txt")]
    result = subprocess.run(prefix + command, env=clean_environment(), capture_output=True, text=True)
    with (runtime.parent.parent / "sdk-install-local.log").open("x") as stream:
        stream.write(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f"STOP: offline pip installation failed: {result.returncode}")
    check = subprocess.run(prefix + [installer_python, "-m", "pip", "--isolated", "--python", str(runtime),
                            "--disable-pip-version-check", "check"], env=clean_environment(),
                           capture_output=True, text=True)
    if check.returncode or check.stdout.strip() != "No broken requirements found.":
        raise RuntimeError("STOP: pip check failed")
    print("PASS: offline installation and pip check")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("acquire", "install"))
    args = parser.parse_args()
    if Path(sys.prefix) != ROOT / ".venv":
        parser.error("use the assigned repository bootstrap .venv")
    plan = load_plan()
    if args.action == "acquire":
        acquire(plan)
    else:
        install(plan)  # Every installer subprocess has its own deny-network sandbox.


if __name__ == "__main__":
    main()
