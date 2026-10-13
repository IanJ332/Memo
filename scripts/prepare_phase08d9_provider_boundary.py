"""Stage 2 only: exact wheels, isolated offline install, metadata qualification.

No upstream/native/SDK imports. Each action uses an exclusive output/receipt.
Run preflight/install/verify under OS network denial with a repository .venv -I -B.
Acquisition invokes only configuration-free curl against frozen exact HTTPS URLs.
"""
from __future__ import annotations

import argparse
import base64
import csv
import datetime
import email
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import stat
import subprocess
import sys
import sysconfig
import uuid
from urllib.parse import urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "manifests/phase-08d9-provider-boundary-source.json"
SOURCE_SHA = "91bdb4c3cdb28e0879b686ba1bd5448d375c02b51a1e0cd612f120b2f7f4ad72"
BASE = "a14b21f6157f7994ccb333994a85fd766aba540e"
BRANCH = "phase-08d9-stage2-dependency-preparation"
VERIFIER_SHA = "1aedece04cfc9816206ee59246f323e7a3fa18eb12031c4ab201bf27aa615098"
STAGE1_RECEIPT_SHA = "63bc5a1e954d6056e79c06f3d4340a3f3bff8e27a39b3d6c3cfe6a9aad219772"
AREA = ROOT / ".local/phase08d9/stage2"
RUNTIME = ROOT / ".local/phase08d9/runtime/.venv"
SANDBOX = "(version 1)(allow default)(deny network*)"
BANNED = {"hindsight", "hindsight_api", "hindsight_client", "openai", "httpx", "httpcore", "aiohttp"}
LIMIT_FILES = 22
LIMIT_BYTES = 4_390_044


def require(condition, message):
    if not condition:
        raise ValueError("STOP: " + message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def regular(path):
    path = Path(path)
    require(not any(p.is_symlink() for p in (path, *path.parents)), "symlink input: " + str(path))
    require(path.is_file(), "missing regular file: " + str(path))
    return path.read_bytes()


def write_new(path, data):
    with Path(path).open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def clean_env():
    return {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1", "PIP_CONFIG_FILE": os.devnull}


def guard():
    require(sys.prefix != sys.base_prefix and ".venv" in Path(sys.prefix).parts
            and any((p / "AGENTS.md").is_file() and (p / ".git").exists() for p in Path(sys.prefix).parents),
            "repository .venv required")
    require(sys.flags.isolated and sys.dont_write_bytecode, "-I -B required")
    require(not any(n.split(".")[0] in BANNED for n in sys.modules), "prohibited module already loaded")
    def audit(event, args):
        if event.startswith("socket.") or (event == "import" and args[0].split(".")[0] in BANNED):
            raise RuntimeError("STOP: native/SDK/Python network execution denied: " + event)
    sys.addaudithook(audit)


def packaging():
    # pip's metadata/tag parser belongs to the existing repository installer,
    # never the target environment or an upstream/native package.
    from pip._vendor.packaging.requirements import Requirement
    from pip._vendor.packaging.specifiers import SpecifierSet
    from pip._vendor.packaging.tags import sys_tags, parse_tag
    from pip._vendor.packaging.utils import canonicalize_name, parse_wheel_filename
    return Requirement, SpecifierSet, sys_tags, parse_tag, canonicalize_name, parse_wheel_filename


def target():
    require(platform.python_version() == "3.12.8" and sys.implementation.name == "cpython"
            and sys.platform == "darwin" and platform.machine() == "x86_64", "interpreter/platform drift")
    tags = sorted(str(t) for t in packaging()[2]())
    return {"implementation": "cpython", "python": "3.12.8", "system": "Darwin",
            "machine": "x86_64", "macos": platform.mac_ver()[0],
            "soabi": sysconfig.get_config_var("SOABI"), "compatible_tags": tags}


def load_source(path=SOURCE):
    data = regular(path)
    require(sha(data) == SOURCE_SHA, "approved source manifest changed")
    value = json.loads(data)
    require(canonical(value) == data, "noncanonical source manifest")
    return value


def url_ok(artifact):
    u = urlsplit(artifact["url"])
    require(u.scheme == "https" and u.hostname == "files.pythonhosted.org" and u.netloc == u.hostname
            and not u.username and not u.password and not u.query and not u.fragment
            and u.path.startswith("/packages/") and PurePosixPath(u.path).name == artifact["filename"],
            "URL outside exact HTTPS artifact policy")


def artifact_ok(row, compatible):
    require(isinstance(row.get("bytes"), int) and row["bytes"] > 0, "missing artifact size")
    require(isinstance(row.get("sha256"), str) and len(row["sha256"]) == 64
            and all(c in "0123456789abcdef" for c in row["sha256"]), "missing/invalid artifact SHA-256")
    require(Path(row["filename"]).name == row["filename"], "unsafe filename")
    _, _, _, _, normalize, parse = packaging()
    name, version, build, tags = parse(row["filename"])
    require(normalize(row["name"]) == name and str(version) == row["version"] and not build,
            "filename distribution/version mismatch")
    require(bool({str(t) for t in tags} & set(compatible)), "incompatible wheel filename")
    require(sorted(str(t) for t in tags) == row["tags"], "wheel filename tag drift")
    url_ok(row)


def build_plan(source):
    packages = source["included_source_closure"]["packages"]
    observed_target = target()
    sdk_plan = json.loads(regular(ROOT / "manifests/phase-08d7-sdk-acquisition-plan.json"))
    artifacts = []
    for item in packages["artifact_plan"]:
        selected = item["selected_candidate_artifact"]
        # SDK receipt has no URL; recover the same hash identity from the lock.
        matching = [w for w in item["compatible_locked_candidates"]
                    if w["sha256"] == selected["sha256"] and w["filename"] == selected["filename"]
                    and w["bytes"] == selected["bytes"]]
        require(len(matching) == 1, "ambiguous/missing exact locked artifact")
        wheel = matching[0]
        tags = sorted(str(t) for t in packaging()[5](wheel["filename"])[3])
        row = {"name": item["name"], "version": item["version"], **wheel, "tags": tags}
        if item["sdk_artifact"]:
            row.update(origin="REUSED_D7_WHEEL", original_path=str(Path(sdk_plan["wheelhouse"]) / wheel["filename"]))
        elif item["existing_wheels"]:
            matches = [w for w in item["existing_wheels"] if w["sha256"] == wheel["sha256"]]
            require(len(matches) == 1, "ambiguous original reusable artifact")
            row.update(origin="REUSED_ORIGINAL_CACHE", original_path=matches[0]["path"])
        else:
            row.update(origin="AUTHORIZED_DOWNLOAD", original_path=None)
        artifact_ok(row, observed_target["compatible_tags"])
        artifacts.append(row)
    require(len(artifacts) == 41 and len({a["name"] for a in artifacts}) == 41
            and {a["name"]: a["version"] for a in artifacts} == packages["package_versions"], "dependency set drift")
    require(len({a["filename"] for a in artifacts}) == 41 and len({a["sha256"] for a in artifacts}) == 41,
            "duplicate wheel identity")
    missing = [a for a in artifacts if a["origin"] == "AUTHORIZED_DOWNLOAD"]
    require(len(missing) == LIMIT_FILES and sum(a["bytes"] for a in missing) == LIMIT_BYTES,
            "authorized acquisition limits differ")
    require(len(artifacts) - len(missing) == 19, "reuse count differs")
    return {"schema_version": 1, "phase": "08D-9_STAGE_2", "approved_base": BASE,
            "source_manifest_sha256": SOURCE_SHA, "stage1_verifier_sha256": VERIFIER_SHA,
            "engineered_identity": source["engineered_runtime_identity"],
            "target": observed_target, "metadata_marker_environment": packages["target"],
            "dependency_roots": packages["roots"], "dependency_edges": packages["edges"],
            "artifacts": sorted(artifacts, key=lambda a: a["name"]),
            "limits": {"successful_downloads": LIMIT_FILES, "requests": LIMIT_FILES,
                       "verified_download_bytes": LIMIT_BYTES, "retries": 0},
            "installer": sdk_plan["installer"], "runtime": str(RUNTIME),
            "wheelhouse": str(AREA / "wheelhouse"), "network": "EXACT_URLS_ONLY_FOR_ACQUISITION;DENY_ALL_FOR_INSTALL_VERIFY",
            "qualification": "METADATA_ONLY_NO_NATIVE_OR_SDK_IMPORTS"}


def load_plan():
    raw = regular(AREA / "acquisition-plan.json")
    require(sha(raw) == regular(AREA / "acquisition-plan.sha256").decode().strip(), "frozen plan hash drift")
    plan = json.loads(raw)
    require(raw == canonical(build_plan(load_source())), "frozen plan differs from approved inputs/platform")
    return plan


def check_record(raw, read, members=None):
    rows = list(csv.reader(io.StringIO(raw.decode())))
    require(all(len(r) == 3 for r in rows) and len({r[0] for r in rows}) == len(rows), "malformed/duplicate RECORD")
    if members is not None:
        require({r[0] for r in rows} == set(members), "wheel RECORD missing/extra members")
    count = 0
    for name, value, size in rows:
        if not value:
            require(name.endswith(".dist-info/RECORD") and not size, "unhashed RECORD member")
            continue
        algorithm, expected = value.split("=", 1)
        require(algorithm == "sha256", "unsupported RECORD hash")
        data = read(name)
        require(base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode() == expected
                and str(len(data)) == size, "RECORD size/hash mismatch: " + name)
        count += 1
    return count, rows


def verify_wheel(path, row, plan):
    data = regular(path)
    require(len(data) == row["bytes"] and sha(data) == row["sha256"], "wheel size/hash mismatch: " + row["name"])
    artifact_ok(row, plan["target"]["compatible_tags"])
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos = z.infolist()
        names = [i.filename for i in infos if not i.is_dir()]
        require(len({i.filename for i in infos}) == len(infos), "duplicate ZIP paths")
        for info in infos:
            name = PurePosixPath(info.filename)
            require(not name.is_absolute() and ".." not in name.parts and "\\" not in info.filename
                    and not stat.S_ISLNK(info.external_attr >> 16), "unsafe ZIP path/symlink")
            require(not info.flag_bits & 1, "encrypted ZIP member")
            require(not info.filename.endswith(".pth") and not any(p.endswith(".data") for p in name.parts),
                    "executable .pth or unsupported wheel relocation")
        require(z.testzip() is None, "ZIP CRC failure")
        metadata_names = [n for n in names if n.count("/") == 1 and n.endswith(".dist-info/METADATA")]
        require(len(metadata_names) == 1, "ambiguous wheel metadata")
        prefix = metadata_names[0].removesuffix("METADATA")
        require({n.split("/")[0] for n in names if ".dist-info/" in n} == {prefix.rstrip("/")},
                "unexpected distribution ownership")
        md_raw, wheel_raw, record_raw = (z.read(prefix + f) for f in ("METADATA", "WHEEL", "RECORD"))
        md, wh = email.message_from_bytes(md_raw), email.message_from_bytes(wheel_raw)
        _, Specifier, _, parse_tag, normalize, _ = packaging()
        require(normalize(md["Name"]) == row["name"] and md["Version"] == row["version"], "wheel METADATA identity mismatch")
        require(wh["Wheel-Version"] == "1.0" and wh["Root-Is-Purelib"] in {"true", "false"}, "unsupported WHEEL metadata")
        tags = {str(t) for text in wh.get_all("Tag", []) for t in parse_tag(text)}
        require(tags == set(row["tags"]), "WHEEL tags differ from filename")
        require(not md["Requires-Python"] or Specifier(md["Requires-Python"]).contains("3.12.8"), "Requires-Python incompatible")
        count, _ = check_record(record_raw, z.read, names)
        return {"name": row["name"], "version": row["version"], "sha256": row["sha256"],
                "filename": row["filename"], "bytes": row["bytes"], "tags": sorted(tags),
                "requires_python": md["Requires-Python"], "requires_dist": md.get_all("Requires-Dist", []),
                "metadata_sha256": sha(md_raw), "wheel_metadata_sha256": sha(wheel_raw),
                "wheel_record_sha256": sha(record_raw), "wheel_record_files_verified": count,
                "zip_integrity": "PASS"}


def dependencies(wheels, plan):
    Requirement, _, _, _, normalize, _ = packaging()
    versions = {a["name"]: a["version"] for a in plan["artifacts"]}
    require({w["name"]: w["version"] for w in wheels} == versions and len(wheels) == len(versions),
            "metadata inventory differs from exact closure")
    observed, selections = set(), []
    for wheel in wheels:
        for text in wheel["requires_dist"]:
            dep = Requirement(text)
            require(not dep.url, "direct URL dependency")
            selected = dep.marker is None or dep.marker.evaluate(plan["metadata_marker_environment"])
            selections.append({"from": wheel["name"], "requires_dist": text, "selected": selected, "extra": ""})
            if not selected:
                continue
            name = normalize(dep.name)
            require(name in versions and dep.specifier.contains(versions[name]), "additional/incompatible dependency: " + name)
            require(not dep.extras, "unexpected selected dependency extras")
            observed.add((wheel["name"], name))
    expected = {(e["from"], e["to"]) for e in plan["dependency_edges"]}
    require(observed == expected, "actual METADATA dependency relationships differ from frozen closure")
    return {"status": "PASS", "active_edges": [list(e) for e in sorted(observed)], "marker_selections": selections}


def original_wheels(plan):
    return [verify_wheel(Path(a["original_path"]), a, plan) for a in plan["artifacts"] if a["original_path"]]


def preflight():
    source = load_source()
    require(sha(regular(ROOT / "scripts/verify_phase08d9_provider_boundary.py")) == VERIFIER_SHA, "Stage 1 verifier identity drift")
    receipt_raw = regular(ROOT / "manifests/phase-08d9-stage1-static-verification.json")
    require(sha(receipt_raw) == STAGE1_RECEIPT_SHA, "Stage 1 verification receipt drift")
    # Read-only invocation of the unchanged independent Stage 1 verifier. No
    # materializer/rematerialization, upstream import, or prior test rerun.
    sys.path.insert(0, str(ROOT / "scripts"))
    import verify_phase08d9_provider_boundary as verifier
    verifier.static.guard()
    args = argparse.Namespace(source_cache=Path("/private/tmp/hindsight_audit"),
        source_frontier=Path("/Users/ian/.codex/worktrees/b648/Memo/.local/phase08d8/source-frontier"),
        pinned_tree=Path("/private/tmp/phase08d5-pinned-tree.json"),
        metadata_root=Path("/Users/ian/.codex/worktrees/2373/Memo/.local/phase08d7"),
        derivative=Path("/Users/ian/.codex/worktrees/aba1/Memo/.local/phase08d9/provider-boundary/0.1.0"),
        manifest=SOURCE)
    verifier.verify_tree(args)
    plan = build_plan(source)
    reused = original_wheels(plan)
    installer = plan["installer"]
    require(sha(regular(installer["metadata"]["path"])) == installer["metadata"]["sha256"], "installer metadata drift")
    require(Path(sys.prefix) == Path(installer["repository_venv"]), "use frozen repository installer .venv")
    require(not AREA.exists() and not RUNTIME.parent.exists(), "fresh output/environment already exists")
    AREA.parent.mkdir(parents=True, exist_ok=True)
    AREA.mkdir(mode=0o700)
    write_new(AREA / "acquisition-plan.json", canonical(plan))
    write_new(AREA / "acquisition-plan.sha256", (sha(canonical(plan)) + "\n").encode())
    write_new(AREA / "preflight.json", canonical({"status": "PASS", "source_manifest_sha256": SOURCE_SHA,
        "verifier_sha256": VERIFIER_SHA, "source_files_revalidated": 131, "plan_sha256": sha(canonical(plan)),
        "target": plan["target"], "reused_artifacts": reused, "downloads": 22, "download_bytes": LIMIT_BYTES,
        "native_sdk_imports": 0, "raw_output_directory": str(AREA)}))
    print("PASS: frozen plan, 131 source files, 19 original wheels; 22 exact downloads / 4,390,044 bytes")


def log_event(stream, event):
    stream.write(canonical(event))
    stream.flush()
    os.fsync(stream.fileno())


def download_command(row, partial):
    url_ok(row)
    return ["/usr/bin/curl", "-q", "--fail", "--silent", "--show-error", "--proto", "=https",
            "--proto-redir", "=https", "--proxy", "", "--noproxy", "*", "--no-location",
            "--max-redirs", "0", "--retry", "0", "--max-time", "60", "--max-filesize", str(row["bytes"]),
            "--url", row["url"], "--output", str(partial), "--write-out",
            "%{http_code}\n%{ssl_verify_result}\n%{num_redirects}\n%{url_effective}\n%{size_download}\n"]


def download(row, plan, folder, stream, index, verified_bytes, runner=subprocess.run):
    require(1 <= index <= LIMIT_FILES and verified_bytes + row["bytes"] <= LIMIT_BYTES, "acquisition budget exceeded")
    partial = folder / (row["filename"] + ".part")
    write_new(partial, b"")
    log_event(stream, {"event": "REQUEST_BEGIN", "request": index, "name": row["name"], "url": row["url"],
                       "expected_bytes": row["bytes"], "expected_sha256": row["sha256"]})
    try:
        result = runner(download_command(row, partial), env={"PATH": "/usr/bin:/bin"},
                        capture_output=True, text=True, timeout=65)
        fields = result.stdout.splitlines()
        log_event(stream, {"event": "REQUEST_RESULT", "request": index, "exit_code": result.returncode,
                          "curl_fields": fields, "stderr": result.stderr,
                          "observed_bytes": partial.stat().st_size, "observed_sha256": sha(regular(partial))})
        require(result.returncode == 0, "download failure: " + row["name"])
        require(len(fields) == 5 and fields[:4] == ["200", "0", "0", row["url"]]
                and float(fields[4]) == row["bytes"], "HTTP/TLS/redirect/size policy mismatch")
        checked = verify_wheel(partial, row, plan)
        # Hard-link promotion fails exclusively if a destination exists.
        os.link(partial, folder / row["filename"])
        partial.unlink()
        log_event(stream, {"event": "VERIFIED", "request": index, **checked})
        return checked
    except BaseException as error:
        log_event(stream, {"event": "STOP", "request": index, "error": type(error).__name__, "message": str(error)})
        raise


def acquire():
    plan = load_plan()
    original_wheels(plan)  # STOP before the first request on original drift.
    folder = AREA / "downloads"
    folder.mkdir(mode=0o700)
    records = []
    with (AREA / "requests.jsonl").open("xb") as stream:
        for row in plan["artifacts"]:
            if row["origin"] == "AUTHORIZED_DOWNLOAD":
                records.append(download(row, plan, folder, stream, len(records) + 1,
                                        sum(r["bytes"] for r in records)))
                print("verified: " + row["filename"], flush=True)
    require(len(records) == LIMIT_FILES and sum(r["bytes"] for r in records) == LIMIT_BYTES, "acquisition incomplete")
    original_wheels(plan)
    write_new(AREA / "acquisition.json", canonical({"status": "PASS", "plan_sha256": sha(canonical(plan)),
        "request_count": len(records), "success_count": len(records), "failed_requests": 0,
        "verified_bytes": sum(r["bytes"] for r in records), "wheels": records,
        "request_log_sha256": sha(regular(AREA / "requests.jsonl"))}))


def stage(plan):
    acquisition = json.loads(regular(AREA / "acquisition.json"))
    require(acquisition["plan_sha256"] == sha(canonical(plan)) and acquisition["success_count"] == 22
            and acquisition["verified_bytes"] == LIMIT_BYTES and acquisition["failed_requests"] == 0,
            "acquisition receipt mismatch")
    events = [json.loads(line) for line in regular(AREA / "requests.jsonl").splitlines()]
    require(sha(regular(AREA / "requests.jsonl")) == acquisition["request_log_sha256"]
            and [e["event"] for e in events] == [s for _ in range(22) for s in ("REQUEST_BEGIN", "REQUEST_RESULT", "VERIFIED")],
            "request ledger mismatch")
    expected_files = {a["filename"] for a in plan["artifacts"] if a["origin"] == "AUTHORIZED_DOWNLOAD"}
    require({p.name for p in (AREA / "downloads").iterdir()} == expected_files, "additional/missing download artifacts")
    checks = []
    # Verify all 41 before any copy/environment creation.
    for row in plan["artifacts"]:
        path = Path(row["original_path"]) if row["original_path"] else AREA / "downloads" / row["filename"]
        checks.append(verify_wheel(path, row, plan))
    dep = dependencies(checks, plan)
    wheelhouse = Path(plan["wheelhouse"])
    wheelhouse.mkdir(mode=0o700)
    for row in plan["artifacts"]:
        path = Path(row["original_path"]) if row["original_path"] else AREA / "downloads" / row["filename"]
        with path.open("rb") as incoming, (wheelhouse / row["filename"]).open("xb") as outgoing:
            shutil.copyfileobj(incoming, outgoing)
            outgoing.flush()
            os.fsync(outgoing.fileno())
        verify_wheel(wheelhouse / row["filename"], row, plan)
    requirements = "".join((wheelhouse / a["filename"]).as_uri() + " --hash=sha256:" + a["sha256"] + "\n"
                           for a in plan["artifacts"])
    write_new(AREA / "requirements.txt", requirements.encode())
    write_new(AREA / "staged.json", canonical({"status": "PASS", "wheels": checks, "dependency_check": dep,
        "plan_sha256": sha(canonical(plan)), "requirements_sha256": sha(requirements.encode())}))


def offline_run(command, log):
    result = subprocess.run(["/usr/bin/sandbox-exec", "-p", SANDBOX, *command], env=clean_env(),
                            capture_output=True, text=True, timeout=120)
    write_new(log, canonical({"command": command, "returncode": result.returncode,
                              "stdout": result.stdout, "stderr": result.stderr, "os_network": "DENY_ALL"}))
    require(result.returncode == 0, "offline subprocess failed; see " + str(log))
    return result


def install():
    plan = load_plan()
    stage(plan)
    require(not RUNTIME.parent.exists(), "runtime already exists")
    installer = plan["installer"]
    require(sha(regular(installer["metadata"]["path"])) == installer["metadata"]["sha256"], "installer drift")
    RUNTIME.parent.mkdir(mode=0o700)
    identity = {"id": str(uuid.uuid4()), "path": str(RUNTIME), "repository": str(ROOT),
                "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "plan_sha256": sha(canonical(plan)), "fresh_creation": True,
                "distinct_from_d7_runtime": "/Users/ian/.codex/worktrees/2373/Memo/.local/phase08d7/runtime/.venv"}
    write_new(AREA / "environment-identity.json", canonical(identity))
    offline_run([sys.executable, "-I", "-B", "-m", "venv", "--without-pip", str(RUNTIME)], AREA / "venv-creation.json")
    installer_python = str(Path(installer["repository_venv"]) / "bin/python")
    offline_run([installer_python, "-I", "-B", "-m", "pip", "--isolated", "--python", str(RUNTIME),
        "--disable-pip-version-check", "install", "--no-index", "--no-deps", "--require-hashes", "--only-binary=:all:",
        "--no-cache-dir", "--no-compile", "-r", str(AREA / "requirements.txt")], AREA / "pip-install.json")
    print("PASS: 41 verified wheels installed offline into fresh isolated environment")


def installed_path(site, name):
    require(not PurePosixPath(name).is_absolute() and "\\" not in name, "absolute/invalid installed RECORD path")
    path = site / name
    require(not any(p.is_symlink() for p in (path, *path.parents)), "installed symlink")
    resolved = path.resolve()
    require(resolved.is_relative_to(RUNTIME) and resolved.is_file(), "installed ownership escapes runtime")
    return resolved


def verify_installation(plan):
    cfg = regular(RUNTIME / "pyvenv.cfg")
    require(b"include-system-site-packages = false" in cfg, "inherited site packages")
    site = RUNTIME / "lib/python3.12/site-packages"
    require(not list(site.rglob("*.pth")) and not list(site.rglob("*.egg-link")), "executable pth/editable inheritance")
    probe = offline_run([str(RUNTIME / "bin/python"), "-I", "-B", "-c",
        "import sys,site,json,platform; print(json.dumps({'prefix':sys.prefix,'base_prefix':sys.base_prefix,'path':sys.path,'user_site':site.ENABLE_USER_SITE,'python':platform.python_version()}))"],
        AREA / "environment-probe.json")
    runtime_probe = json.loads(probe.stdout)
    require(runtime_probe["prefix"] == str(RUNTIME) and runtime_probe["prefix"] != runtime_probe["base_prefix"]
            and runtime_probe["user_site"] is False and runtime_probe["python"] == "3.12.8", "target environment identity/inheritance mismatch")
    require([p for p in runtime_probe["path"] if "site-packages" in p or "dist-packages" in p] == [str(site)], "inherited target site path")
    normalize = packaging()[4]
    distributions = list(importlib.metadata.distributions(path=[str(site)]))
    expected = {a["name"]: a["version"] for a in plan["artifacts"]}
    by_name = {normalize(d.metadata["Name"]): d for d in distributions}
    require(len(distributions) == 41 and {n: d.version for n, d in by_name.items()} == expected, "unexpected installed distributions")
    require(not any(p.name.startswith("hindsight") for p in site.iterdir()), "unexpected Hindsight namespace ownership")
    checks, ownership = [], {}
    for row in plan["artifacts"]:
        wheel = Path(plan["wheelhouse"]) / row["filename"]
        checked = verify_wheel(wheel, row, plan)
        dist = by_name[row["name"]]
        record = dist.read_text("RECORD")
        require(record is not None, "missing installed RECORD")
        def read(name):
            return regular(installed_path(site, name))
        count, rows = check_record(record.encode(), read)
        for name, _, _ in rows:
            path = installed_path(site, name)
            require(path not in ownership, "distribution ownership conflict: " + str(path))
            ownership[path] = row["name"]
        with zipfile.ZipFile(wheel) as z:
            md_name = next(n for n in z.namelist() if n.endswith(".dist-info/METADATA"))
            prefix = md_name.removesuffix("METADATA")
            for info in z.infolist():
                if not info.is_dir() and info.filename != prefix + "RECORD":
                    require(read(info.filename) == z.read(info.filename), "installed bytes differ from exact wheel")
            installed_members = {n for n, _, _ in rows}
            original_members = {i.filename for i in z.infolist() if not i.is_dir()}
            extras = installed_members - original_members
            allowed = {prefix + n for n in ("INSTALLER", "REQUESTED", "direct_url.json")}
            # pip generates only the pinned wheel's declared console/gui scripts.
            ep_raw = z.read(prefix + "entry_points.txt").decode() if prefix + "entry_points.txt" in z.namelist() else ""
            import configparser
            parser = configparser.ConfigParser(interpolation=None)
            parser.optionxform = str
            parser.read_string(ep_raw)
            for group in ("console_scripts", "gui_scripts"):
                if parser.has_section(group):
                    for name in parser[group]:
                        require(Path(name).name == name and name not in {".", ".."}, "unsafe entrypoint name")
                        allowed.add("../../../bin/" + name)
            require(extras <= allowed, "unexpected generated installed files")
            direct = json.loads(read(prefix + "direct_url.json"))
            require(direct["url"] == wheel.as_uri() and direct["archive_info"]["hashes"] == {"sha256": row["sha256"]},
                    "installed archive provenance mismatch")
            require(read(prefix + "INSTALLER") == b"pip\n", "unexpected installer")
        checked.update(installed_record_sha256=sha(record.encode()), installed_record_files_verified=count,
                       installed_bytes_match_wheel=True, generated_files=sorted(extras))
        checks.append(checked)
    observed_files = {p.resolve() for p in site.rglob("*") if p.is_file()}
    require(not any(p.is_symlink() for p in site.rglob("*")), "symlink target site ownership")
    require(observed_files == {p for p in ownership if p.is_relative_to(site)}, "unowned files in target site")
    require({p.name for p in Path(plan["wheelhouse"]).iterdir()} == {a["filename"] for a in plan["artifacts"]}, "wheelhouse inventory drift")
    dep = dependencies(checks, plan)
    installer = str(Path(plan["installer"]["repository_venv"]) / "bin/python")
    pip_check = offline_run([installer, "-I", "-B", "-m", "pip", "--isolated", "--python", str(RUNTIME),
                           "--disable-pip-version-check", "check"], AREA / "pip-check.json")
    require(pip_check.stdout.strip() == "No broken requirements found.", "pip check failed")
    original_wheels(plan)
    identity = json.loads(regular(AREA / "environment-identity.json"))
    identity.update(pyvenv_cfg_sha256=sha(cfg), directory_device=RUNTIME.stat().st_dev,
                    directory_inode=RUNTIME.stat().st_ino, interpreter_realpath=str((RUNTIME / "bin/python").resolve()),
                    installed_inventory_sha256=sha(canonical(expected)))
    return {"phase": "08D-9_STAGE_2", "status": "METADATA_INSTALLATION_PASS_NO_IMPORT_QUALIFICATION",
            "plan_sha256": sha(canonical(plan)), "source_manifest_sha256": SOURCE_SHA,
            "environment": identity, "environment_probe": runtime_probe, "packages": checks,
            "dependency_check": dep, "distribution_count": 41, "pip_check": "PASS",
            "wheel_record_files_verified": sum(w["wheel_record_files_verified"] for w in checks),
            "installed_record_files_verified": sum(w["installed_record_files_verified"] for w in checks),
            "ownership_conflicts": 0, "unexpected_distributions": 0, "executable_pth": 0,
            "original_wheels_unchanged": True, "native_sdk_imports": 0,
            "D3": "PARTIAL", "D4": "BLOCKED", "D5": "PARTIAL", "runtime_safety": "UNKNOWN",
            "semantic_parity": "NOT_EXECUTED"}


def verify():
    plan = load_plan()
    write_new(AREA / "installation.json", canonical(verify_installation(plan)))
    print("PASS: exact 41 distributions; METADATA/WHEEL/RECORD/ownership/dependencies/pip check; zero native/SDK imports")


def main():
    guard()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preflight", "acquire", "install", "verify"))
    args = parser.parse_args()
    try:
        globals()[args.action]()
    except BaseException as error:
        if AREA.is_dir():
            failure = {"action": args.action, "error": type(error).__name__, "message": str(error),
                       "utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
            write_new(AREA / ("failure-" + str(uuid.uuid4()) + ".json"), canonical(failure))
        raise


if __name__ == "__main__":
    main()
