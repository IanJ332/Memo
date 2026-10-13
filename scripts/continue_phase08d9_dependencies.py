"""Bounded continuation of the original six-request Stage 2 acquisition.

Historical evidence is immutable. New receipts belong to its continuation,
not a replacement acquisition attempt. Imports of native/provider/SDK modules
are prohibited; all actions except the 16 exact curl requests run OS-offline.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_phase08d9_provider_boundary as p

START = "582a9f0ff3aa21c2ba08b8d59e47362386c9ff65"
MANIFEST_SHA = "2ac0757b1c525fde914bf8258f180e86b7610391d3d23fb23d5b4516f0bdd87d"
PLAN_SHA = "dc477b3135f262a4ed4d3e421ff4d906ee040f0dfd0f9241926791931a8688b9"
EXISTING_SHA = "73b723f39511fdcd97d8ac01aa35ead794d8111b55ace085e48c1671ea115584"
C = p.AREA / "continuation"
INSTALL_COMPLETION = C / "installation-completion"
OLD_REQUESTS = 6
OLD_BYTES = 1_425_689
ADDITIONAL_REQUESTS = 16
ADDITIONAL_BYTES = 2_964_355


def pin_receipt(name):
    raw = p.regular(C / name)
    return {"path": str(C / name), "bytes": len(raw), "sha256": p.sha(raw)}


def historical_evidence(plan):
    raw = p.regular(p.ROOT / "manifests/phase-08d9-provider-boundary-dependencies.json")
    p.require(p.sha(raw) == MANIFEST_SHA, "immutable initial dependency manifest changed")
    original = json.loads(raw)
    p.require(plan == original["frozen_acquisition_plan"] and p.sha(p.regular(p.AREA / "acquisition-plan.json")) == PLAN_SHA,
              "frozen plan changed")
    snapshot_raw = p.regular(C / "existing-evidence.json")
    p.require(p.sha(snapshot_raw) == EXISTING_SHA, "existing-evidence snapshot altered")
    snapshot = json.loads(snapshot_raw)
    p.require(snapshot["starting_commit"] == START and snapshot["original_manifest_sha256"] == MANIFEST_SHA
              and snapshot["plan_sha256"] == PLAN_SHA, "continuation snapshot identity drift")
    for row in snapshot["historical_inputs"]:
        data = p.regular(p.ROOT / row["relative_path"])
        p.require(len(data) == row["bytes"] and p.sha(data) == row["sha256"], "historical evidence tamper")
    installer = plan["installer"]
    p.require(p.sha(p.regular(installer["metadata"]["path"])) == installer["metadata"]["sha256"], "pinned installer drift")
    site = Path(installer["repository_venv"]) / "lib/python3.12/site-packages"
    for name, row in snapshot["installer_scheme_sources"].items():
        data = p.regular(site / name)
        p.require(len(data) == row["bytes"] and p.sha(data) == row["sha256"], "pinned installer scheme code changed")
    original_ledger = p.regular(p.AREA / "requests.jsonl")
    p.require(p.sha(original_ledger) == snapshot["original_request_ledger_sha256"], "original request ledger changed")
    validate_original_ledger([json.loads(line) for line in original_ledger.splitlines()], plan)
    return snapshot


def download_rows(plan):
    return [a for a in plan["artifacts"] if a["origin"] == "AUTHORIZED_DOWNLOAD"]


def validate_original_ledger(events, plan):
    shape = [s for _ in range(5) for s in ("REQUEST_BEGIN", "REQUEST_RESULT", "VERIFIED")]
    shape += ["REQUEST_BEGIN", "REQUEST_RESULT", "STOP"]
    p.require([e["event"] for e in events] == shape, "altered/replayed original request ledger")
    rows = download_rows(plan)
    for index, artifact in enumerate(rows[:6], 1):
        base = (index - 1) * 3
        begin, result, gate = events[base:base + 3]
        p.require(all(e["request"] == index for e in (begin, result, gate)), "original request identity replay")
        p.require(begin["name"] == artifact["name"] and begin["url"] == artifact["url"]
                  and begin["expected_bytes"] == artifact["bytes"] and begin["expected_sha256"] == artifact["sha256"],
                  "altered original request artifact")
        validate_result(result, artifact)
        if index < 6:
            p.require(gate["filename"] == artifact["filename"] and gate["sha256"] == artifact["sha256"]
                      and gate["bytes"] == artifact["bytes"] and gate["name"] == artifact["name"], "original promotion evidence drift")
        else:
            p.require(gate == {"error": "ValueError", "event": "STOP", "message": "STOP: executable .pth or unsupported wheel relocation",
                               "request": 6}, "historical STOP reinterpreted")
    p.require(sum(a["bytes"] for a in rows[:6]) == OLD_BYTES, "original accounting discrepancy")


def validate_result(result, artifact):
    p.require(result["exit_code"] == 0 and result["stderr"] == "" and result["observed_bytes"] == artifact["bytes"]
              and result["observed_sha256"] == artifact["sha256"]
              and result["curl_fields"] == ["200", "0", "0", artifact["url"], str(artifact["bytes"])],
              "HTTP/TLS/redirect/hash/accounting evidence mismatch")


def repair_inputs(plan, greenlet_promoted=False):
    snapshot = historical_evidence(plan)
    p.original_wheels(plan)
    rows = download_rows(plan)
    for row in rows[:5]:
        p.verify_wheel(p.AREA / "downloads" / row["filename"], row, plan)
    greenlet = rows[5]
    p.require(greenlet["filename"] == p.GREENLET_FILENAME and greenlet["sha256"] == p.GREENLET_SHA, "wrong greenlet identity")
    partial = p.AREA / "downloads" / (greenlet["filename"] + ".part")
    checked = p.verify_wheel(partial, greenlet, plan)
    expected = {a["filename"] for a in rows[:5]} | {greenlet["filename"] + ".part"}
    if greenlet_promoted:
        expected.add(greenlet["filename"])
    p.require({a.name for a in (p.AREA / "downloads").iterdir()} == expected, "pre-continuation downloaded inventory drift")
    return snapshot, checked


def tools():
    return {"scripts/" + name: p.sha(p.regular(p.ROOT / "scripts" / name)) for name in (
        "prepare_phase08d9_provider_boundary.py", "continue_phase08d9_dependencies.py",
        "test_phase08d9_dependencies.py", "test_phase08d9_continuation.py")}


def verify_repair():
    plan = p.load_plan()
    snapshot, checked = repair_inputs(plan)
    test_raw = p.regular(C / "tests-final.json")
    tests = json.loads(test_raw)
    p.require(tests["failures"] == [] and tests["errors"] == [] and tests["existing_tests"] == 39
              and tests["tools"] == tools(), "offline repair suite absent/failed or tooling changed")
    row = download_rows(plan)[5]
    scheme = p.installer_scheme(p.RUNTIME, row["name"])
    with zipfile.ZipFile(p.AREA / "downloads" / (row["filename"] + ".part")) as z:
        mapping = p.member_destinations(z, row, scheme, p.RUNTIME)
    receipt = {"status": "REPAIR_OFFLINE_VERIFIED", "starting_commit": START,
        "source_manifest_sha256": p.SOURCE_SHA, "frozen_plan_sha256": PLAN_SHA,
        "historical_request_ledger_sha256": snapshot["original_request_ledger_sha256"],
        "historical_inputs_unchanged": True, "tests_sha256": p.sha(test_raw), "tools": tools(),
        "greenlet_check": checked, "projected_scheme": scheme,
        "header_destination": str(mapping[p.GREENLET_HEADER]), "os_network": "DENY_ALL",
        "native_sdk_imports": 0, "no_runtime": not p.RUNTIME.exists()}
    p.require(not p.RUNTIME.parent.exists(), "pre-repair runtime exists")
    p.write_new(C / "repair-verification.json", p.canonical(receipt))
    print("PASS: repaired verifier and full offline controls; original evidence and plan unchanged")


def repair_gate():
    plan = p.load_plan()
    historical_evidence(plan)
    repair = json.loads(p.regular(C / "repair-verification.json"))
    p.require(repair["frozen_plan_sha256"] == PLAN_SHA
              and repair["tests_sha256"] == p.sha(p.regular(C / "tests-final.json")), "repair qualification drift")
    if repair["tools"] != tools():
        wrapper = json.loads(p.regular(C / "wrapper-repair-verification.json"))
        tests = json.loads(p.regular(C / "tests-after-wrapper-repair.json"))
        p.require(wrapper["initial_repair_receipt_sha256"] == p.sha(p.regular(C / "repair-verification.json"))
                  and wrapper["tools"] == tools() and wrapper["tests_sha256"] == p.sha(p.regular(C / "tests-after-wrapper-repair.json"))
                  and tests["tools"] == tools() and not tests["failures"] and not tests["errors"], "wrapper repair qualification drift")
    return plan, repair


def accept_greenlet():
    plan, repair = repair_gate()
    _, checked = repair_inputs(plan)
    row = download_rows(plan)[5]
    partial = p.AREA / "downloads" / (row["filename"] + ".part")
    destination = p.AREA / "downloads" / row["filename"]
    p.require(not destination.exists(), "greenlet promotion collision/replay")
    receipt = {"status": "GREENLET_ACCEPTED_AFTER_REPAIR_NO_REDOWNLOAD", "original_request": 6,
        "original_gate": "STOP_PRESERVED", "frozen_plan_sha256": PLAN_SHA,
        "historical_request_ledger_sha256": repair["historical_request_ledger_sha256"],
        "repair_receipt": pin_receipt("repair-verification.json"), "wheel": checked,
        "partial_preserved": str(partial), "additional_requests": 0, "additional_downloaded_bytes": 0,
        "promotion": "EXCLUSIVE_HARD_LINK_FROM_VERIFIED_PRESERVED_PARTIAL", "os_network": "DENY_ALL"}
    # Receipt is separate from the historical failed gate. The partial remains
    # byte-for-byte intact after promotion; a collision never overwrites it.
    p.write_new(C / "greenlet-acceptance.json", p.canonical(receipt))
    os.link(partial, destination)
    p.verify_wheel(destination, row, plan)
    print("PASS: original greenlet bytes accepted/promoted; no new request; original STOP and partial preserved")


def ledger_header(plan):
    snapshot = historical_evidence(plan)
    return {"event": "CONTINUATION_BEGIN", "frozen_plan_sha256": PLAN_SHA,
        "original_ledger_sha256": snapshot["original_request_ledger_sha256"],
        "greenlet_acceptance_sha256": p.sha(p.regular(C / "greenlet-acceptance.json")),
        "original_requests": OLD_REQUESTS, "original_download_bytes": OLD_BYTES,
        "additional_request_limit": ADDITIONAL_REQUESTS, "additional_byte_limit": ADDITIONAL_BYTES,
        "cumulative_request_limit": p.LIMIT_FILES, "cumulative_byte_limit": p.LIMIT_BYTES}


def acquire_remaining():
    plan, _ = repair_gate()
    repair_inputs(plan, greenlet_promoted=True)
    acceptance = json.loads(p.regular(C / "greenlet-acceptance.json"))
    row = download_rows(plan)[5]
    p.require(acceptance["wheel"]["sha256"] == row["sha256"] and acceptance["additional_requests"] == 0,
              "greenlet acceptance drift")
    p.verify_wheel(p.AREA / "downloads" / row["filename"], row, plan)
    remaining = download_rows(plan)[6:]
    p.require(len(remaining) == ADDITIONAL_REQUESTS and sum(a["bytes"] for a in remaining) == ADDITIONAL_BYTES,
              "remaining allowlist/accounting discrepancy")
    records = []
    with (C / "requests.jsonl").open("xb") as stream:
        p.log_event(stream, ledger_header(plan))
        for row in remaining:
            index = OLD_REQUESTS + len(records) + 1
            total = OLD_BYTES + sum(r["bytes"] for r in records)
            records.append(p.download(row, plan, p.AREA / "downloads", stream, index, total))
            print("verified continuation: " + row["filename"], flush=True)
    validate_continuation(plan)
    p.write_new(C / "remaining-acquisition.json", p.canonical({"status": "PASS", "frozen_plan_sha256": PLAN_SHA,
        "historical_ledger_sha256": ledger_header(plan)["original_ledger_sha256"],
        "continuation_ledger_sha256": p.sha(p.regular(C / "requests.jsonl")),
        "additional_requests": len(records), "additional_download_bytes": sum(r["bytes"] for r in records),
        "cumulative_requests": OLD_REQUESTS + len(records), "cumulative_download_bytes": OLD_BYTES + sum(r["bytes"] for r in records),
        "failed_http_requests": 0, "retries": 0, "redirects": 0, "wheels": records}))


def validate_continuation(plan, events=None):
    events = events if events is not None else [json.loads(line) for line in p.regular(C / "requests.jsonl").splitlines()]
    p.require(events and events[0] == ledger_header(plan), "continuation lineage/accounting changed")
    p.require([e["event"] for e in events[1:]] == [s for _ in range(16) for s in ("REQUEST_BEGIN", "REQUEST_RESULT", "VERIFIED")],
              "replayed/missing/additional continuation request")
    for offset, artifact in enumerate(download_rows(plan)[6:]):
        begin, result, verified = events[1 + offset * 3:4 + offset * 3]
        index = offset + 7
        p.require(all(e["request"] == index for e in (begin, result, verified)), "continuation request index replay")
        p.require(begin == {"event": "REQUEST_BEGIN", "request": index, "name": artifact["name"], "url": artifact["url"],
                            "expected_bytes": artifact["bytes"], "expected_sha256": artifact["sha256"]}, "continuation artifact drift")
        validate_result(result, artifact)
        p.require(verified["name"] == artifact["name"] and verified["filename"] == artifact["filename"]
                  and verified["sha256"] == artifact["sha256"] and verified["bytes"] == artifact["bytes"], "continuation verification drift")
    p.require(sum(e["observed_bytes"] for e in events if e["event"] == "REQUEST_RESULT") == ADDITIONAL_BYTES,
              "continuation byte accounting mismatch")


def complete_inventory():
    plan, _ = repair_gate()
    validate_continuation(plan)
    acquisition_raw = p.regular(C / "remaining-acquisition.json")
    acquisition = json.loads(acquisition_raw)
    p.require(acquisition["continuation_ledger_sha256"] == p.sha(p.regular(C / "requests.jsonl"))
              and acquisition["cumulative_requests"] == 22 and acquisition["cumulative_download_bytes"] == p.LIMIT_BYTES,
              "completed acquisition receipt/accounting drift")
    expected = {a["filename"] for a in download_rows(plan)} | {p.GREENLET_FILENAME + ".part"}
    p.require({x.name for x in (p.AREA / "downloads").iterdir()} == expected, "download file inventory discrepancy")
    checks, ownership = [], {}
    for row in plan["artifacts"]:
        path = Path(row["original_path"]) if row["original_path"] else p.AREA / "downloads" / row["filename"]
        checks.append(p.verify_wheel(path, row, plan))
        with zipfile.ZipFile(path) as z:
            scheme = p.installer_scheme(p.RUNTIME, row["name"])
            mapping = p.member_destinations(z, row, scheme, p.RUNTIME)
            for source, destination in mapping.items():
                p.require(destination not in ownership, "cross-distribution destination ownership collision")
                ownership[destination] = {"name": row["name"], "archive_path": source}
    dependencies = p.dependencies(checks, plan)
    wheelhouse = Path(plan["wheelhouse"])
    p.require(not p.RUNTIME.parent.exists(), "runtime already exists before complete inventory")
    wheelhouse.mkdir(mode=0o700)
    for row in plan["artifacts"]:
        source = Path(row["original_path"]) if row["original_path"] else p.AREA / "downloads" / row["filename"]
        with source.open("rb") as incoming, (wheelhouse / row["filename"]).open("xb") as outgoing:
            shutil.copyfileobj(incoming, outgoing)
            outgoing.flush()
            os.fsync(outgoing.fileno())
        p.verify_wheel(wheelhouse / row["filename"], row, plan)
    requirements = "".join((wheelhouse / a["filename"]).as_uri() + " --hash=sha256:" + a["sha256"] + "\n" for a in plan["artifacts"])
    p.write_new(C / "requirements.txt", requirements.encode())
    p.write_new(C / "complete-inventory.json", p.canonical({"status": "EXACT_41_WHEELS_VERIFIED_STAGED",
        "source_manifest_sha256": p.SOURCE_SHA, "plan_sha256": PLAN_SHA, "wheels": checks,
        "dependencies": dependencies, "requirements_sha256": p.sha(requirements.encode()),
        "destination_map_sha256": p.sha(p.canonical({str(k): v for k, v in ownership.items()})),
        "acquisition_receipt_sha256": p.sha(acquisition_raw), "originals_unchanged": True,
        "os_network": "DENY_ALL", "native_sdk_imports": 0}))
    print("PASS: all 41 unique exact wheels; dependency metadata and exclusive destination ownership; staged offline")


def runtime_files():
    result = {}
    for path in sorted(p.RUNTIME.rglob("*")):
        relative = str(path.relative_to(p.RUNTIME))
        if path.is_symlink():
            result[relative] = {"type": "SYMLINK", "target": os.readlink(path)}
        elif path.is_file():
            data = p.regular(path)
            result[relative] = {"type": "FILE", "bytes": len(data), "sha256": p.sha(data)}
    return result


def install(receipt_area=C, recover_wrapper=False):
    plan, _ = repair_gate()
    validate_continuation(plan)
    inventory = json.loads(p.regular(C / "complete-inventory.json"))
    p.require(inventory["plan_sha256"] == PLAN_SHA and len(inventory["wheels"]) == 41
              and p.sha(p.regular(C / "requirements.txt")) == inventory["requirements_sha256"], "staged inventory/hash lock changed")
    for row in plan["artifacts"]:
        p.verify_wheel(Path(plan["wheelhouse"]) / row["filename"], row, plan)
    p.require({x.name for x in Path(plan["wheelhouse"]).iterdir()} == {a["filename"] for a in plan["artifacts"]}, "wheelhouse discrepancy")
    if recover_wrapper:
        validate_wrapper_failure()
        receipt_area.mkdir(mode=0o700)
    else:
        p.require(not p.RUNTIME.parent.exists(), "fresh environment collision/replay")
        p.RUNTIME.parent.mkdir(mode=0o700)
    identity = {"id": str(uuid.uuid4()), "path": str(p.RUNTIME), "repository": str(p.ROOT),
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "plan_sha256": PLAN_SHA,
        "inventory_receipt_sha256": p.sha(p.regular(C / "complete-inventory.json")), "fresh_creation": True,
        "distinct_from_d7_runtime": "/Users/ian/.codex/worktrees/2373/Memo/.local/phase08d7/runtime/.venv"}
    if recover_wrapper:
        identity["pre_interpreter_failed_identity_receipt"] = pin_receipt("environment-identity.json")
    p.write_new(receipt_area / "environment-identity.json", p.canonical(identity))
    p.offline_run([sys.executable, "-I", "-B", "-m", "venv", "--without-pip", str(p.RUNTIME)], receipt_area / "venv-creation.json")
    p.write_new(receipt_area / "environment-before-install.json", p.canonical(runtime_files()))
    actual = p.offline_run([str(p.RUNTIME / "bin/python"), "-I", "-B", str(Path(__file__).resolve()), "scheme"], receipt_area / "target-scheme.json")
    scheme = json.loads(actual.stdout)
    p.require(scheme == p.installer_scheme(p.RUNTIME, "greenlet"), "actual target installer scheme differs from qualified projection")
    p.write_new(receipt_area / "header-scheme-verification.json", p.canonical({"status": "PASS", "scheme": scheme,
        "actual_target_interpreter": str(p.RUNTIME / "bin/python"), "pinned_pip": plan["installer"],
        "target_scheme_log_sha256": p.sha(p.regular(receipt_area / "target-scheme.json")), "os_network": "DENY_ALL"}))
    for row in plan["artifacts"]:
        with zipfile.ZipFile(Path(plan["wheelhouse"]) / row["filename"]) as z:
            for dest in p.member_destinations(z, row, p.installer_scheme(p.RUNTIME, row["name"]), p.RUNTIME).values():
                p.require(not dest.exists(), "installation destination already owned/collision")
    installer = str(Path(plan["installer"]["repository_venv"]) / "bin/python")
    p.offline_run([installer, "-I", "-B", "-m", "pip", "--isolated", "--python", str(p.RUNTIME),
        "--disable-pip-version-check", "install", "--no-index", "--no-deps", "--require-hashes", "--only-binary=:all:",
        "--no-cache-dir", "--no-compile", "-r", str(C / "requirements.txt")], receipt_area / "pip-install.json")
    print("PASS: 41 pinned distributions installed offline; actual target header scheme bound before installation")


def verify():
    plan, _ = repair_gate()
    validate_continuation(plan)
    receipt_area = INSTALL_COMPLETION if INSTALL_COMPLETION.is_dir() else C
    receipt = p.verify_installation(plan, receipt_area=receipt_area)
    scheme = json.loads(p.regular(receipt_area / "header-scheme-verification.json"))
    p.require(scheme["scheme"] == p.installer_scheme(p.RUNTIME, "greenlet"), "installed header scheme drift")
    before = json.loads(p.regular(receipt_area / "environment-before-install.json"))
    after = runtime_files()
    p.require(all(after.get(name) == value for name, value in before.items()), "installer modified baseline environment ownership")
    site = p.RUNTIME / "lib/python3.12/site-packages"
    owners = {}
    for dist in p.importlib.metadata.distributions(path=[str(site)]):
        rows = p.csv.reader(p.io.StringIO(dist.read_text("RECORD")))
        for name, _, _ in rows:
            dest = p.installed_path(site, name)
            key = str(dest.relative_to(p.RUNTIME))
            p.require(key not in before and key not in owners, "installed/baseline or distribution ownership collision")
            owners[key] = dist.metadata["Name"]
    p.require(set(after) == set(before) | set(owners), "unexpected unowned files anywhere in fresh runtime")
    p.require(len(receipt["relocations"]) == 1 and receipt["relocations"][0]["archive_path"] == p.GREENLET_HEADER,
              "missing/unexpected installed header relocation")
    receipt.update(continuation_of_start_commit=START, historical_inputs_unchanged=True,
        original_ledger_sha256=ledger_header(plan)["original_ledger_sha256"],
        continuation_ledger_sha256=p.sha(p.regular(C / "requests.jsonl")),
        cumulative_http_requests=22, cumulative_download_bytes=p.LIMIT_BYTES,
        full_environment_ownership="PASS", baseline_files_preserved=len(before),
        owned_installed_files=len(owners), actual_header_scheme_receipt=pin_receipt(str((receipt_area / "header-scheme-verification.json").relative_to(C))))
    p.write_new(receipt_area / "installation-verification.json", p.canonical(receipt))
    print("PASS: 41 distributions, METADATA/WHEEL/RECORD/header relocation/global ownership/isolation/pip check; no SDK/native imports")


def target_scheme():
    # Run only in the fresh target. Load installer code explicitly from the
    # frozen existing repository venv; no target distribution is imported.
    plan = json.loads(p.regular(p.AREA / "acquisition-plan.json"))
    p.require(p.sha(p.regular(p.AREA / "acquisition-plan.json")) == PLAN_SHA and Path(sys.prefix) == p.RUNTIME,
              "scheme probe target/plan mismatch")
    site = Path(plan["installer"]["repository_venv"]) / "lib/python3.12/site-packages"
    sys.path.insert(0, str(site))
    historical_evidence(plan)
    print(json.dumps(p.installer_scheme(p.RUNTIME, "greenlet"), sort_keys=True))


def validate_wrapper_failure():
    failure_raw = p.regular(C / "venv-creation.json")
    failure = json.loads(failure_raw)
    p.require(failure["returncode"] == 71 and failure["stdout"] == ""
              and failure["stderr"] == "sandbox-exec: sandbox_apply: Operation not permitted\n", "not the diagnosed pre-interpreter wrapper failure")
    p.require(not p.RUNTIME.exists() and p.RUNTIME.parent.is_dir() and not list(p.RUNTIME.parent.iterdir()),
              "runtime artifacts exist; do not repair an actual installation failure")
    return failure_raw


def qualify_wrapper():
    plan = p.load_plan()
    historical_evidence(plan)
    failure_raw = validate_wrapper_failure()
    tests_raw = p.regular(C / "tests-after-wrapper-repair.json")
    tests = json.loads(tests_raw)
    p.require(tests["tools"] == tools() and tests["existing_tests"] == 39 and not tests["failures"] and not tests["errors"],
              "corrected wrapper suite failed/changed")
    state = p.os_network_denial()
    p.require(all(v == 1 for v in state.values()), "OS denial missing during wrapper qualification")
    p.write_new(C / "wrapper-repair-verification.json", p.canonical({"status": "PASS_PRE_INTERPRETER_WRAPPER_REPAIR",
        "initial_repair_receipt_sha256": p.sha(p.regular(C / "repair-verification.json")), "tools": tools(),
        "tests_sha256": p.sha(tests_raw), "preserved_failure_sha256": p.sha(failure_raw),
        "kernel_network_policy": state, "initial_pip_executions": 0, "initial_runtime_created": False,
        "scope": "Avoid rejected nested sandbox_apply; inherit observed OS denial; no artifact or dependency change"}))
    print("PASS: wrapper repair suite; kernel network denial verified; original pre-interpreter failure preserved")


def install_after_wrapper_repair():
    repair_gate()
    install(receipt_area=INSTALL_COMPLETION, recover_wrapper=True)


def main():
    p.guard()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("verify_repair", "accept_greenlet", "acquire_remaining", "complete_inventory", "install",
                                         "qualify_wrapper", "install_after_wrapper_repair", "verify", "scheme"))
    args = parser.parse_args()
    try:
        (target_scheme if args.action == "scheme" else globals()[args.action])()
    except BaseException as error:
        if C.is_dir():
            p.write_new(C / ("failure-" + str(uuid.uuid4()) + ".json"), p.canonical({"action": args.action,
                "error": type(error).__name__, "message": str(error),
                "utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}))
        raise


if __name__ == "__main__":
    main()
