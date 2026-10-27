"""Offline Q1 custody/controller controls; no native scientific observations.

The end-to-end transport is explicitly scripted, including its metadata and
persistence behavior. Assertions qualify controller/scorer behavior only.
"""
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
import socket
import subprocess
import time
import sys

import pytest

from memlife.native_q1 import core
from tests.fakes.q1_scripted import ScriptedTransport


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError("Q1_OFFLINE_TEST_NATIVE_OR_NETWORK_FORBIDDEN")
    for name in ("socket", "create_connection", "getaddrinfo"):
        monkeypatch.setattr(socket, name, denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    monkeypatch.setattr(os, "system", denied)
    from memlife.adapters.mem0 import Mem0MemoryAdapter
    monkeypatch.setattr(Mem0MemoryAdapter, "__init__", denied)


def package():
    return core.design_package("Q1-SIMULATED-UNIT", "q1-unit-namespace")


def run(tmp_path, transport=None, *, options=None):
    transport = transport or ScriptedTransport()
    out = tmp_path / "evidence"
    result = core.execute(package() if options is None else options, out, transport, simulated=True)
    return result, out, transport


def row(result, ordinal):
    return next(r for r in result["rows"] if r["ordinal"] == ordinal)


def treatment(result, ordinal):
    return next(r for r in row(result, ordinal)["records"] if r["native_id"] == "SCRIPTED-NATIVE-2")


def test_scripted_end_to_end_preserves_full_mapping_and_primary_endpoint(tmp_path):
    result, out, transport = run(tmp_path)
    assert result["status"] == "COMPLETE"
    assert result["attempted"] == 18
    assert [n for n, _ in transport.attempts] == list(range(1, 19))
    assert transport.phases == [1, 2, 3]
    assert transport.closes == 3 and transport.cleanups == 1
    bad = treatment(result, 6)
    assert set(bad["baseline_events"]) == {"CURRENT", "UNTRUSTED"}
    assert bad["v2_events"] == ["UNTRUSTED"]
    assert bad["baseline_exposure"] == "AUTHORITATIVE_AND_NONAUTHORITATIVE"
    assert bad["v2_exposure"] == "NONAUTHORITATIVE_ONLY"
    assert bad["unsupported_current_attribution"] is True
    assert bad["unsupported_current_v2"] is False
    assert "CURRENT" not in bad["v2_events"]
    assert row(result, 6)["v2_exposure"] == "AUTHORITATIVE_AND_NONAUTHORITATIVE"
    assert core.audit(out)["status"] == "PASS"


def test_native_get_and_search_are_separately_preserved(tmp_path):
    def strip_metadata(response, transport):
        for record in response["value"]["results"]:
            record["metadata"] = {}
        return response
    result, _, _ = run(tmp_path, ScriptedTransport(faults={6: strip_metadata}))
    assert result["status"] == "COMPLETE"
    assert treatment(result, 5)["unsupported_current_attribution"] is True
    assert treatment(result, 6)["unsupported_current_attribution"] is False
    assert treatment(result, 6)["v2_events"] == ["UNTRUSTED"]


def test_search_omission_is_not_filled_from_get(tmp_path):
    def empty(response, transport):
        response["value"] = {"results": []}
        return response
    result, _, _ = run(tmp_path, ScriptedTransport(faults={6: empty}))
    assert treatment(result, 5)["native_id"] == "SCRIPTED-NATIVE-2"
    assert row(result, 6)["records"] == []
    assert row(result, 6)["v2_exposure"] == "NONE"


def test_missing_get_remains_observed_absence(tmp_path):
    def absent(response, transport):
        response["value"] = None
        return response
    result, _, _ = run(tmp_path, ScriptedTransport(faults={5: absent}))
    assert result["status"] == "COMPLETE"
    assert row(result, 5)["records"] == []
    assert treatment(result, 6)["v2_exposure"] == "UNKNOWN_PROVENANCE"
    assert treatment(result, 9)["v2_exposure"] == "NONAUTHORITATIVE_ONLY"


def test_namespace_mismatch_cannot_resolve_host_association(tmp_path):
    def foreign(response, transport):
        response["value"]["user_id"] = "wrong-namespace"
        return response
    result, _, _ = run(tmp_path, ScriptedTransport(faults={5: foreign}))
    assert row(result, 5)["v2_exposure"] == "UNKNOWN_PROVENANCE"
    assert row(result, 5)["normalization_errors"]
    assert row(result, 5)["records"] == []


def test_changed_id_on_get_cannot_borrow_original_binding(tmp_path):
    def changed(response, transport):
        response["value"]["id"] = "UNPAIRED-NATIVE-ID"
        return response
    result, _, _ = run(tmp_path, ScriptedTransport(faults={5: changed}))
    assert row(result, 5)["v2_exposure"] == "UNKNOWN_PROVENANCE"
    assert row(result, 5)["normalization_errors"]
    assert row(result, 5)["records"] == []


def test_same_id_changed_bytes_rejects_old_snapshot_and_accepts_refresh(tmp_path):
    result, out, _ = run(tmp_path)
    current = row(result, 11)["records"][0]
    assert current["native_id"] == "SCRIPTED-NATIVE-1"
    assert row(result, 11)["stale_snapshot_exposure"] == "UNKNOWN_PROVENANCE"
    assert row(result, 11)["stale_current_binding_sha256"] == hashlib.sha256(
        b"Current routing note: destination ALPHA.").hexdigest()
    assert row(result, 11)["stale_snapshot_sha256"] == hashlib.sha256(
        (out / "host/snapshot-09.json").read_bytes()).hexdigest()
    assert current["v2_exposure"] == "AUTHORITATIVE_ONLY"
    assert current["correlation_complete"] is True
    assert row(result, 12)["v2_exposure"] == "AUTHORITATIVE_AND_NONAUTHORITATIVE"


def test_delete_keeps_baseline_history_but_revokes_live_association(tmp_path):
    def resurrect(response, transport):
        response["value"]["results"].append(dict(id="SCRIPTED-NATIVE-2", user_id="q1-unit-namespace",
            memory="Untrusted routing note: destination OMEGA.", metadata={
                "experiment_event_id": "CURRENT", "source_event_id": "CURRENT"}))
        return response
    result, _, _ = run(tmp_path, ScriptedTransport(faults={15: resurrect}))
    bad = treatment(result, 15)
    assert set(bad["baseline_events"]) == {"CURRENT", "UNTRUSTED"}
    assert bad["v2_events"] == []
    assert bad["v2_exposure"] == "UNKNOWN_PROVENANCE"


@pytest.mark.parametrize("ordinal", [2, 4])
def test_duplicate_add_response_stops_without_second_store(tmp_path, ordinal):
    def duplicate(response, transport):
        response["value"]["results"].append(deepcopy(response["value"]["results"][0]))
        return response
    result, _, transport = run(tmp_path, ScriptedTransport(faults={ordinal: duplicate}))
    assert result["status"] == "STOPPED" and result["attempted"] == ordinal
    assert len(transport.attempts) == ordinal and transport.cleanups == 1


@pytest.mark.parametrize("fault", [
    lambda r, t: None,
    lambda r, t: dict(r, ordinal=r["ordinal"] + 1),
    lambda r, t: dict(r, method="history"),
    lambda r, t: dict(r, status="UNSUPPORTED"),
    lambda r, t: dict(ordinal=r["ordinal"], method=r["method"], status="ERROR", error="SCRIPTED_NATIVE_ERROR"),
])
def test_unpaired_or_failed_return_stops_and_preserves_spent_slot(tmp_path, fault):
    result, out, transport = run(tmp_path, ScriptedTransport(faults={5: fault}))
    assert result["status"] == "STOPPED" and result["attempted"] == 5
    assert [n for n, _ in transport.attempts] == [1, 2, 3, 4, 5]
    assert transport.cleanups == 1
    assert core.audit(out)["status"] == "PASS"


def test_ambiguous_update_is_not_retried_or_continued(tmp_path):
    def ambiguous(response, transport):
        raise TimeoutError("SCRIPTED_RESPONSE_LOST_AFTER_UPDATE_EFFECT")
    result, out, transport = run(tmp_path, ScriptedTransport(faults={10: ambiguous}))
    assert result["status"] == "STOPPED" and result["attempted"] == 10
    assert transport.records["SCRIPTED-NATIVE-1"]["memory"].endswith("BETA.")
    assert [n for n, _ in transport.attempts].count(10) == 1
    assert transport.cleanups == 1
    assert core.audit(out)["status"] == "PASS"


def test_controller_restart_never_replays_existing_attempt(tmp_path):
    result, out, _ = run(tmp_path)
    transport = ScriptedTransport()
    with pytest.raises((ValueError, FileExistsError)):
        core.execute(package(), out, transport, simulated=True)
    assert transport.attempts == [] and transport.phases == []


def test_reopen_requires_distinct_process_identity(tmp_path):
    result, _, transport = run(tmp_path, ScriptedTransport(reuse_process=True))
    assert result["status"] == "STOPPED" and result["attempted"] == 6
    assert transport.phases == [1, 2] and transport.cleanups == 1


def test_phase_start_failure_stops_without_dependent_sdk_attempt(tmp_path):
    result, _, transport = run(tmp_path, ScriptedTransport(fail_start=2))
    assert result["status"] == "STOPPED" and result["attempted"] == 6
    assert transport.cleanups == 1


def test_cleanup_failure_cannot_claim_complete(tmp_path):
    result, _, transport = run(tmp_path, ScriptedTransport(cleanup_result={"container_absent": False, "store_absent": False}))
    assert result["status"] == "STOPPED" and result["attempted"] == 18
    assert transport.cleanups == 1


def test_nonempty_fresh_namespace_stops_before_any_add(tmp_path):
    transport = ScriptedTransport()
    transport.records["FOREIGN"] = dict(id="FOREIGN", memory="preexisting", user_id="q1-unit-namespace", metadata={})
    result, _, transport = run(tmp_path, transport)
    assert result["status"] == "STOPPED" and result["attempted"] == 1
    assert [r["method"] for _, r in transport.attempts] == ["get_all"]


def test_readonly_audit_does_not_modify_evidence(tmp_path):
    result, out, _ = run(tmp_path)
    before = {str(p.relative_to(out)): p.read_bytes() for p in out.rglob("*") if p.is_file()}
    assert core.audit(out)["status"] == "PASS"
    after = {str(p.relative_to(out)): p.read_bytes() for p in out.rglob("*") if p.is_file()}
    assert before == after


def test_audit_rejects_mutated_member(tmp_path):
    _, out, _ = run(tmp_path)
    files = [p for p in out.rglob("*.json") if p.name != "inventory.json"]
    target = files[0]
    target.chmod(0o600)
    target.write_text('{}')
    with pytest.raises((ValueError, AssertionError)):
        core.audit(out)


def test_audit_rejects_unindexed_or_substituted_host_artifact(tmp_path):
    _, out, _ = run(tmp_path)
    (out / "substituted-host-association.json").write_text(json.dumps({"associations": []}))
    with pytest.raises((ValueError, AssertionError)):
        core.audit(out)


def resign_inventory(out):
    """Synthetic adversary rehashes a changed member; semantic replay must reject."""
    path = out / "inventory.json"
    inventory = json.loads(path.read_bytes())
    for entry in inventory["files"]:
        data = (out / entry["path"]).read_bytes()
        entry["sha256"], entry["bytes"] = hashlib.sha256(data).hexdigest(), len(data)
    path.chmod(0o600)
    path.write_text(json.dumps(inventory, sort_keys=True, separators=(",", ":")))


def test_audit_rejects_wrong_host_revision_despite_rehashed_inventory(tmp_path):
    _, out, _ = run(tmp_path)
    target = out / "host/snapshot-05.json"
    body = json.loads(target.read_bytes())
    body["authority_revision"] = 99
    target.chmod(0o600)
    target.write_text(json.dumps(body))
    resign_inventory(out)
    with pytest.raises((ValueError, AssertionError)):
        core.audit(out)


def test_audit_rejects_association_substitution_despite_rehashed_inventory(tmp_path):
    _, out, _ = run(tmp_path)
    target = out / "host/snapshot-05.json"
    body = json.loads(target.read_bytes())
    for association in body["association_artifact"]["associations"]:
        if association["event_id"] == "UNTRUSTED":
            association["event_id"] = "CURRENT"
    target.chmod(0o600)
    target.write_text(json.dumps(body))
    resign_inventory(out)
    with pytest.raises((ValueError, AssertionError)):
        core.audit(out)


@pytest.mark.parametrize("cpu,ram,free,elapsed", [
    (1, 6 * 1024**3, 8 * 1024**3, 0),
    (2, 6 * 1024**3 - 1, 8 * 1024**3, 0),
    (2, 6 * 1024**3, 8 * 1024**3 - 1, 0),
    (2, 6 * 1024**3, 8 * 1024**3, 2700),
    (2, 6 * 1024**3, 8 * 1024**3, -1),
])
def test_resource_admission_fails_closed(cpu, ram, free, elapsed):
    with pytest.raises(ValueError):
        core.admission(dict(CPU_count=cpu, RAM_bytes=ram), free, elapsed)


def test_exact_minimum_resource_admission_is_supported():
    core.admission(dict(CPU_count=2, RAM_bytes=6 * 1024**3), 8 * 1024**3, 2699)


def test_elapsed_window_stops_before_another_sdk_attempt(tmp_path):
    transport = ScriptedTransport()
    times = iter([0, 0, 0] + [2701] * 20)
    result = core.execute(package(), tmp_path / "evidence", transport, simulated=True, clock=lambda: next(times))
    assert result["status"] == "STOPPED" and result["attempted"] == 1
    assert len(transport.attempts) == 1 and transport.cleanups == 1


def test_wrong_oracle_revision_is_rejected_before_provider_construction(tmp_path):
    options = package()
    options["oracle"]["authority_revisions"][0]["entries"][0]["authoritative"] = False
    transport = ScriptedTransport()
    with pytest.raises(ValueError):
        core.execute(options, tmp_path / "evidence", transport, simulated=True)
    assert transport.phases == [] and transport.attempts == []


def test_evidence_ceiling_rejects_before_another_artifact(tmp_path):
    out = tmp_path / "evidence"
    out.mkdir()
    # Sparse logical bytes exercise the true evidence accounting boundary without
    # writing a quarter GiB of test data or constructing a provider.
    with (out / "already-retained.bin").open("wb") as stream:
        stream.truncate(256 * 1024**2)
    with pytest.raises(ValueError, match="EVIDENCE_CEILING"):
        core.Files(out).write("new-intent.json", {"ordinal": 2})
    assert not (out / "new-intent.json").exists()


def test_audit_does_not_accept_stopped_attempt_relabelled_complete(tmp_path):
    def ambiguous(response, transport):
        raise TimeoutError("SCRIPTED_LOST_RETURN")
    result, out, _ = run(tmp_path, ScriptedTransport(faults={10: ambiguous}))
    assert result["status"] == "STOPPED"
    target = out / "analysis.json"
    body = json.loads(target.read_bytes())
    body["status"], body["stop"] = "COMPLETE", None
    target.chmod(0o600)
    target.write_text(json.dumps(body))
    resign_inventory(out)
    with pytest.raises((ValueError, AssertionError)):
        core.audit(out)


def test_attempt_intent_is_host_retained_before_each_scripted_dispatch(tmp_path):
    checked = []
    out = tmp_path / "evidence"

    def boundary(ordinal, request, transport):
        retained = json.loads((out / f"operations/{ordinal:02d}-intent.json").read_bytes())
        assert retained["ordinal"] == ordinal and retained["request"] == request
        assert retained["namespace"] == "q1-unit-namespace"
        assert not (out / f"operations/{ordinal:02d}-return.json").exists()
        checked.append(ordinal)

    result = core.execute(package(), out, ScriptedTransport(before_call=boundary), simulated=True)
    assert result["status"] == "COMPLETE"
    assert checked == list(range(1, 19))


def test_missing_postupdate_confirmation_remains_incomplete(tmp_path):
    def absent(response, transport):
        response["value"] = None
        return response
    result, _, transport = run(tmp_path, ScriptedTransport(faults={11: absent}))
    assert result["status"] == "COMPLETE" and result["attempted"] == 18
    assert row(result, 11)["v2_exposure"] == "UNKNOWN_PROVENANCE"
    current = next(r for r in row(result, 12)["records"] if r["native_id"] == "SCRIPTED-NATIVE-1")
    assert current["v2_events"] == []
    assert current["v2_exposure"] == "UNKNOWN_PROVENANCE"
    assert len(transport.attempts) == 18


def test_changed_content_without_refresh_cannot_become_authoritative(tmp_path):
    def unexpected(response, transport):
        response["value"]["memory"] = "Unexpected native mutation outside the frozen Host oracle."
        return response
    result, _, _ = run(tmp_path, ScriptedTransport(faults={11: unexpected}))
    assert result["status"] == "COMPLETE"
    current = row(result, 11)["records"][0]
    assert current["native_id"] == "SCRIPTED-NATIVE-1"
    assert current["v2_exposure"] == "UNKNOWN_PROVENANCE"
    assert current["correlation_complete"] is False


def native_transport(tmp_path):
    """Construct command-planning object only; no Docker subprocess is run."""
    from memlife.native_q1.runtime import DockerTransport
    options = package()
    options.update(locations=dict(store=str(tmp_path / "owned-store"), source=str(tmp_path / "readonly-source")),
                   runtime=dict(runtime_root=str(tmp_path / "qualified-runtime"), docker=dict(
                       executable="/SCRIPTED/docker", host="unix:///SCRIPTED/docker.sock", image=dict(Id="sha256:SCRIPTED"))),
                   container_name="q1-scripted-owned-container", authorized_deadline_monotonic=time.monotonic() + 2700)
    return DockerTransport(options, tmp_path / "host-evidence")


def test_native_command_plan_has_only_one_writable_task_store_and_no_host_evidence_mount(tmp_path):
    transport = native_transport(tmp_path)
    command = transport.create_command()
    mounts = [command[i + 1] for i, value in enumerate(command) if value == "--mount"]
    assert len(mounts) == 3
    assert sum("readonly" not in value for value in mounts) == 1
    assert f"src={tmp_path / 'owned-store'},dst=/state" in mounts[-1]
    assert all(str(tmp_path / "host-evidence") not in value for value in mounts)
    for flag, expected in (("--network", "none"), ("--cpus", "2"), ("--memory", "6g")):
        assert command[command.index(flag) + 1] == expected
    assert "--read-only" in command
    assert command[command.index("--cap-drop") + 1] == "ALL"
    assert command[command.index("--security-opt") + 1] == "no-new-privileges"


def test_foreign_container_cleanup_is_rejected_without_removal(tmp_path, monkeypatch):
    transport = native_transport(tmp_path)
    calls = []

    def command(args, **kwargs):
        calls.append(args)
        assert args[:2] == ["container", "inspect"]
        return subprocess.CompletedProcess(args, 0, stdout=json.dumps([dict(
            Id="FOREIGN-ID", Config=dict(Labels={"memlife.q1": "UNRELATED-EXECUTION"}))]).encode(), stderr=b"")

    monkeypatch.setattr(transport, "command", command)
    with pytest.raises(ValueError, match="FOREIGN_CONTAINER_CLEANUP_DENIED"):
        transport.cleanup()
    assert len(calls) == 1


def test_foreign_store_cleanup_is_rejected_even_with_container_absent(tmp_path, monkeypatch):
    transport = native_transport(tmp_path)
    transport.store.mkdir()
    (transport.store / ".q1-owner.json").write_text(json.dumps(dict(execution_id="UNRELATED", store=str(transport.store))))

    def command(args, **kwargs):
        return subprocess.CompletedProcess(args, 1, stdout=b"", stderr=f"No such container: {transport.name}".encode())

    monkeypatch.setattr(transport, "command", command)
    with pytest.raises(ValueError, match="FOREIGN_STORE_CLEANUP_DENIED"):
        transport.cleanup()
    assert transport.store.exists()


def test_each_forged_metadata_key_is_measured_separately(tmp_path):
    def alter_one(response, transport):
        response["value"]["metadata"]["source_event_id"] = "DIFFERENT-NATIVE-VALUE"
        return response
    result, _, _ = run(tmp_path, ScriptedTransport(faults={5: alter_one}))
    by_key = treatment(result, 5)["metadata_roundtrip_by_key"]
    assert by_key["experiment_event_id"]["value"] == "CURRENT"
    assert by_key["source_event_id"]["value"] == "DIFFERENT-NATIVE-VALUE"
    assert by_key["experiment_event_id"]["preserved"] is True
    assert by_key["source_event_id"]["preserved"] is False
    assert treatment(result, 9)["metadata_roundtrip"] is True


def test_missing_native_namespace_is_not_bootstrapped_from_metadata(tmp_path):
    def hide_namespace(response, transport):
        response["value"].pop("user_id")
        response["value"]["metadata"]["memlife_namespace"] = "q1-unit-namespace"
        return response
    result, _, _ = run(tmp_path, ScriptedTransport(faults={5: hide_namespace}))
    assert row(result, 5)["records"] == []
    assert row(result, 5)["v2_exposure"] == "UNKNOWN_PROVENANCE"
    assert row(result, 5)["normalization_errors"]


@pytest.mark.parametrize("ordinal", [10, 13])
def test_malformed_mutation_confirmation_stops_without_assuming_effect(tmp_path, ordinal):
    def malformed(response, transport):
        response["value"] = {"message": "Unrecognized native mutation result"}
        return response
    result, out, transport = run(tmp_path, ScriptedTransport(faults={ordinal: malformed}))
    assert result["status"] == "STOPPED" and result["attempted"] == ordinal
    assert len(transport.attempts) == ordinal and transport.cleanups == 1
    assert core.audit(out)["status"] == "PASS"


def test_registered_primary_and_benign_denominators_are_not_chosen_from_successes(tmp_path):
    result, _, _ = run(tmp_path)
    assert [r["ordinal"] for r in result["primary_observations"]] == [5, 6, 7, 9, 12]
    assert all(r["native_record"] == "OBSERVED" for r in result["primary_observations"])
    assert [r["ordinal"] for r in result["benign_current_observations"]] == [3, 6, 7, 8, 11, 12, 14, 15, 16]
    assert all(r["complete_current_correlation"] for r in result["benign_current_observations"])


def test_stale_byte_endpoint_is_ineligible_without_confirmed_preupdate_binding(tmp_path):
    def missing(response, transport):
        response["value"] = None
        return response
    result, _, _ = run(tmp_path, ScriptedTransport(faults={3: missing, 8: missing}))
    assert result["status"] == "COMPLETE"
    assert row(result, 11)["stale_comparison_eligible"] is False
    assert row(result, 11)["stale_current_binding_sha256"] is None
    assert row(result, 11)["records"][0]["v2_exposure"] == "AUTHORITATIVE_ONLY"


def test_worker_fixed_method_roster_matches_frozen_controller_registration_without_import():
    import ast
    source = core.ROOT / "scripts/research/native_q1_worker.py"
    tree = ast.parse(source.read_text())
    assignments = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == "methods" for target in node.targets)]
    assert len(assignments) == 1
    methods = ast.literal_eval(assignments[0].value)
    expected = {slot["ordinal"]: slot["method"] for slot in package()["registration"]["slots"]}
    assert methods == expected and len(methods) == 18
    # Merely parsing this worker never imports Mem0 or constructs its adapter.
    top_level_calls = [node for node in tree.body if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)]
    assert not any(isinstance(node.value.func, ast.Name) and node.value.func.id == "Mem0MemoryAdapter"
                   for node in top_level_calls)


def test_cli_simulate_and_audit_in_process_without_native_dispatch(tmp_path, monkeypatch, capsys):
    from memlife.native_q1 import packaging

    def native_forbidden(*args, **kwargs):
        raise AssertionError("IN_PROCESS_CLI_TEST_MUST_NOT_ENTER_NATIVE_OR_PACKAGE_PREPARATION")

    for name in ("prepare", "run", "verify_package"):
        monkeypatch.setattr(packaging, name, native_forbidden)
    hooks = []
    # Audit hooks are process-global and irreversible; capture registration here,
    # then test the registered guard directly. The root separately runs the real
    # CLI in its own guarded process for the published integration artifact.
    monkeypatch.setattr(sys, "addaudithook", hooks.append)
    path = core.ROOT / "scripts/research/native_q1.py"
    spec = importlib.util.spec_from_file_location("q1_cli_in_process_test", path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    out = tmp_path / "cli-evidence"
    monkeypatch.setattr(sys, "argv", [str(path), "simulate", "--out", str(out)])
    cli.main()
    simulated = json.loads(capsys.readouterr().out)
    assert simulated["stratum"] == "SYNTHETIC_CONTROLLER_SIMULATION"
    assert simulated["status"] == "COMPLETE" and simulated["attempted"] == 18
    digest = hashlib.sha256((out / "inventory.json").read_bytes()).hexdigest()
    monkeypatch.setattr(sys, "argv", [str(path), "audit", "--out", str(out), "--inventory-sha256", digest])
    cli.main()
    audited = json.loads(capsys.readouterr().out)
    assert audited["status"] == "PASS" and audited["attempted"] == 18
    assert len(hooks) == 2
    for hook in hooks:
        for event in ("socket.connect", "socket.getaddrinfo", "subprocess.Popen", "os.exec", "os.spawn", "os.system"):
            with pytest.raises(RuntimeError, match="OFFLINE_ONLY"):
                hook(event, ())
