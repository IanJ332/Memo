"""Acquire only the human-authorized pinned Python source allowlist; never import it."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
BASE = "a452984507e83f029ae25cb5c850aaca390354c4"
PIN = "f8950b0c07d9e34c76493dba802bb309f0ce60fd"
MANIFEST_SHA256 = "99aea9f5bc42f0d53a3b13ae81b586f3ec92ab25027c3cb99b65c04441afe410"
LIMIT = 586246
PREFIX = "hindsight-api-slim/hindsight_api/"
INITIALIZERS = [PREFIX + p for p in ("__init__.py", "engine/__init__.py", "worker/__init__.py")]
DESTINATION = ROOT / ".local/phase08d8/source-frontier"


def identities(data: bytes) -> dict:
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "git_blob_sha1": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()}


def verify(data: bytes, row: dict) -> dict:
    result = identities(data)
    if result["bytes"] != row["bytes"] or result["git_blob_sha1"] != row["git_blob_sha1"]:
        raise ValueError("STOP: downloaded source identity mismatch: " + row["path"])
    return result


def load_plan() -> dict:
    raw = (ROOT / "manifests/phase-08d8-native-preparation.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise ValueError("STOP: authorized source acquisition manifest changed")
    plan = json.loads(raw)
    rows = plan["missing_source_acquisition_frontier"]
    if plan["upstream_commit"] != PIN or len(rows) != 31 or sum(r["bytes"] for r in rows) != LIMIT:
        raise ValueError("STOP: source acquisition limit changed")
    if len({r["path"] for r in rows}) != 31:
        raise ValueError("STOP: duplicate source paths")
    for row in rows:
        path = Path(row["path"])
        if path.is_absolute() or ".." in path.parts or not row["path"].startswith(PREFIX) or path.suffix != ".py":
            raise ValueError("STOP: invalid source path")
        expected = f"https://raw.githubusercontent.com/vectorize-io/hindsight/{PIN}/{row['path']}"
        url = urlsplit(row["url"])
        if row["url"] != expected or url.username or url.password or url.query or url.fragment:
            raise ValueError("STOP: source URL is not exactly allowlisted")
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("initializers", "remaining"), required=True)
    args = parser.parse_args()
    if sys.prefix == sys.base_prefix or ".venv" not in Path(sys.prefix).parts or not sys.flags.isolated:
        raise RuntimeError("STOP: use an existing repository .venv with -I -B")
    head = subprocess.check_output(["/usr/bin/git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    branch = subprocess.check_output(["/usr/bin/git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
    if branch != "phase-08d8-native-runtime-preparation" or (args.stage == "initializers" and head != BASE):
        raise RuntimeError("STOP: wrong authorized branch/base")
    plan = load_plan()
    rows = {r["path"]: r for r in plan["missing_source_acquisition_frontier"]}
    if args.stage == "initializers":
        DESTINATION.mkdir()  # Exclusive; no prior acquisition is replaced.
        order = INITIALIZERS
        log_mode = "x"
        total = 0
    else:
        files = {str(p.relative_to(DESTINATION)) for p in DESTINATION.rglob("*.py")}
        if files != set(INITIALIZERS) or list(DESTINATION.rglob("*.part")):
            raise RuntimeError("STOP: unexpected acquisition continuation state")
        entries = [json.loads(line) for line in (DESTINATION / "acquisition.jsonl").read_text().splitlines()]
        if [r["path"] for r in entries] != INITIALIZERS:
            raise RuntimeError("STOP: initializer log incomplete")
        total = 0
        for entry in entries:
            identity = verify((DESTINATION / entry["path"]).read_bytes(), rows[entry["path"]])
            if any(entry[key] != value for key, value in identity.items()):
                raise RuntimeError("STOP: initializer bytes/log changed")
            total += identity["bytes"]
        # Inspection of the first initializer exposes this mandatory out-of-plan
        # import and module-scope call. Enforce the user's STOP before any curl.
        root_source = (DESTINATION / INITIALIZERS[0]).read_bytes()
        root_tree = ast.parse(root_source)
        if any(isinstance(n, ast.ImportFrom) and n.level == 1 and n.module == "_thread_limits"
               for n in root_tree.body) and PREFIX + "_thread_limits.py" not in rows:
            raise RuntimeError("STOP: root initializer requires _thread_limits outside authorized allowlist; no remaining acquisition")
        if head != BASE:
            raise RuntimeError("STOP: wrong authorized acquisition base")
        order = sorted(set(rows) - set(INITIALIZERS))
        log_mode = "a"  # Append evidence; never replace prior verified records.
    with (DESTINATION / "acquisition.jsonl").open(log_mode) as log:
        for name in order:
            row = rows[name]
            if total + row["bytes"] > LIMIT:
                raise RuntimeError("STOP: aggregate source limit")
            target = DESTINATION / name
            target.parent.mkdir(parents=True, exist_ok=True)
            part = target.with_suffix(".py.part")
            if target.exists():
                raise RuntimeError("STOP: source destination already exists")
            # Curl 8.7.1 enforces max-filesize during streaming, including unknown
            # Content-Length. stdout is an exclusively opened local file descriptor.
            command = ["/usr/bin/curl", "-q", "--fail", "--silent", "--show-error",
                       "--proto", "=https", "--tlsv1.2", "--proxy", "", "--noproxy", "*",
                       "--max-redirs", "0", "--max-time", "60", "--max-filesize", str(row["bytes"]),
                       "--url", row["url"], "--output", "-", "--write-out",
                       "%{stderr}%{http_code}\n%{ssl_verify_result}\n%{num_redirects}\n%{url_effective}\n%{size_download}\n"]
            with part.open("xb") as stream:
                result = subprocess.run(command, env={}, stdin=subprocess.DEVNULL,
                                        stdout=stream, stderr=subprocess.PIPE, timeout=65)
            fields = result.stderr.decode().strip().splitlines()
            if result.returncode != 0 or len(fields) != 5:
                raise RuntimeError("STOP: source retrieval failed; partial evidence retained")
            code, tls, redirects, effective, size = fields
            data = part.read_bytes()
            if (code != "200" or tls != "0" or redirects != "0" or effective != row["url"]
                    or int(float(size)) != len(data)):
                raise RuntimeError("STOP: HTTPS acquisition constraints failed")
            identity = verify(data, row)  # Must precede parsing.
            total += len(data)
            if total > LIMIT:
                raise RuntimeError("STOP: aggregate source limit exceeded")
            ast.parse(data, filename=name)  # Parse only, never compile/import/execute.
            os.link(part, target)  # Exclusive final creation; refuses a raced destination.
            part.unlink()
            entry = {"path": name, "url": row["url"], **identity,
                     "http_status": int(code), "tls_verify_result": int(tls), "redirects": int(redirects),
                     "effective_url": effective, "source_parsed_after_identity_verification": True,
                     "source_executed": False}
            log.write(json.dumps(entry, sort_keys=True) + "\n")
            log.flush()
            print(f"VERIFIED {name}: {len(data)} bytes", flush=True)
    print(f"PASS: {args.stage}; aggregate verified source bytes={total}/{LIMIT}")


if __name__ == "__main__":
    main()
