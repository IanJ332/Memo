"""Offline safeguards for the narrow Jetstream2 lifecycle controller."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import types

import pytest

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "jetstream" / "jetstreamctl.py"
SPEC = importlib.util.spec_from_file_location("jetstreamctl", MODULE_PATH)
assert SPEC and SPEC.loader
jetstreamctl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(jetstreamctl)


def test_state_normalization_and_opened_rule() -> None:
    assert jetstreamctl.normalize_state("shelved_offloaded") == "SHELVED"
    assert jetstreamctl.normalize_state("ACTIVE") == "ACTIVE"
    assert jetstreamctl.normalize_state("building") == "BUILDING"
    assert jetstreamctl.was_opened_by_run("SHELVED") is True
    assert jetstreamctl.was_opened_by_run("ACTIVE") is False


def test_managed_wrapper_maps_historical_supplement_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    server = {
        "id": jetstreamctl.EXPECTED_SERVER_UUID,
        "name": jetstreamctl.EXPECTED_NAME,
        "status": "ACTIVE",
        "addresses": {
            "public": [{"addr": "8.8.8.8", "OS-EXT-IPS:type": "floating"}]
        },
    }
    monkeypatch.setattr(jetstreamctl, "resolve_server", lambda credentials: (server, {}))
    monkeypatch.setattr(
        jetstreamctl, "discover_external_network", lambda credentials: {"id": "public"}
    )
    monkeypatch.setattr(
        jetstreamctl, "list_server_ports", lambda credentials, server_id: [{"ID": "port"}]
    )
    monkeypatch.setattr(
        jetstreamctl,
        "list_floating_ips",
        lambda credentials: [
            {"ID": "fip", "Floating IP Address": "8.8.8.8", "Port": "port"}
        ],
    )
    monkeypatch.setattr(
        jetstreamctl, "wait_for_floating_ip_association", lambda *args, **kwargs: server
    )
    monkeypatch.setattr(jetstreamctl.socket, "gethostbyname", lambda host: "8.8.8.8")
    monkeypatch.setattr(jetstreamctl, "wait_for_tcp_22", lambda address: 0.01)
    monkeypatch.setattr(jetstreamctl, "verify_ssh", lambda address: None)
    monkeypatch.setattr(
        jetstreamctl,
        "probe",
        lambda address: {
            "remote_user": "exouser",
            "remote_hostname": "jisheng3",
            "resolved_volume_mount": "/volume",
            "repo_head": "a" * 40,
        },
    )
    monkeypatch.setattr(
        jetstreamctl, "cleanup_owned_floating_ip", lambda *args, **kwargs: []
    )
    monkeypatch.setattr(
        jetstreamctl,
        "run_command",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, "test\n", ""),
    )
    result = jetstreamctl.run_managed_session(
        {},
        phase="06B-S",
        manifest_path=tmp_path / "session.json",
        remote_work=lambda address, facts: {"status": "SUPPLEMENT_COMPLETE"},
    )
    assert result["status"] == "PASS"
    assert result["remote_lifecycle_status"] == "PASS"
    assert result["remote_work"]["status"] == "SUPPLEMENT_COMPLETE"


def test_identity_accepts_only_expected_target() -> None:
    server = {
        "id": jetstreamctl.EXPECTED_SERVER_UUID,
        "name": "jisheng3",
        "project_id": "project-1",
    }
    token = {"project_id": "project-1", "project_name": "CIS261698"}
    jetstreamctl.validate_identity(
        server, token, {"server_uuid": jetstreamctl.EXPECTED_SERVER_UUID}
    )
    with pytest.raises(jetstreamctl.JetstreamError):
        jetstreamctl.validate_identity({**server, "name": "another-vm"}, token)
    with pytest.raises(jetstreamctl.JetstreamError):
        jetstreamctl.validate_identity(server, {**token, "project_id": "project-2"})


def test_dynamic_address_parser_prefers_floating_ipv4() -> None:
    server = {"addresses": {"private": [{"addr": "10.0.0.2", "OS-EXT-IPS:type": "fixed"}], "public": [{"addr": "203.0.113.5", "OS-EXT-IPS:type": "floating"}]}}
    assert jetstreamctl.select_address(server) is None
    assert jetstreamctl.select_address({"addresses": "net=10.0.0.2, 192.168.1.3"}) is None
    assert jetstreamctl.select_address({"addresses": "net=10.0.0.2, 8.8.8.8"}) == "8.8.8.8"


def test_dynamic_address_parser_handles_openstack_structures() -> None:
    server = {
        "addresses": {
            "auto_allocated_network": [
                {"addr": "10.0.0.2", "OS-EXT-IPS:type": "fixed"},
                {"addr": "8.8.4.4", "OS-EXT-IPS:type": "floating"},
            ]
        }
    }
    assert jetstreamctl.select_address(server) == "8.8.4.4"


def test_ssh_error_classification() -> None:
    assert jetstreamctl.classify_ssh_error("Permission denied (publickey)") == "AUTH_DENIED"
    assert jetstreamctl.classify_ssh_error("Host key verification failed") == "HOST_KEY_ERROR"
    assert jetstreamctl.classify_ssh_error("Connection timed out") == "TCP_TIMEOUT"
    assert jetstreamctl.classify_ssh_error("kex_exchange_identification failed") == "SSH_PROTOCOL_ERROR"


def test_command_construction_is_scoped_and_noninteractive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(jetstreamctl, "KNOWN_HOSTS", tmp_path / "known_hosts")
    command = jetstreamctl.ssh_command("192.0.2.8", "true")
    joined = " ".join(command)
    assert "BatchMode=yes" in joined
    assert "IdentitiesOnly=yes" in joined
    assert "StrictHostKeyChecking=accept-new" in joined
    assert "exouser@192.0.2.8" in command
    assert jetstreamctl.command_for_openstack(["server", "show", "vm"])[-3:] == ["server", "show", "vm"]


def test_credential_parser_rejects_commands_and_does_not_serialize_secret(tmp_path: Path) -> None:
    secret = "do-not-leak-this-value"
    credential = tmp_path / "openrc.ps1"
    credential.write_text(
        "$env:OS_AUTH_URL='https://example.invalid'\n"
        "$env:OS_AUTH_TYPE='v3applicationcredential'\n"
        "$env:OS_APPLICATION_CREDENTIAL_ID='id'\n"
        f"$env:OS_APPLICATION_CREDENTIAL_SECRET='{secret}'\n",
        encoding="utf-8",
    )
    values = jetstreamctl.load_credentials(credential)
    assert values["OS_APPLICATION_CREDENTIAL_SECRET"] == secret
    assert secret not in json.dumps({"status": "ok"})
    credential.write_text("Write-Host 'unsafe'\n", encoding="utf-8")
    with pytest.raises(jetstreamctl.JetstreamError):
        jetstreamctl.load_credentials(credential)


def test_secret_paths_are_gitignored() -> None:
    paths = [
        ".local/credentials/CIS261698_IU-openrc.ps1",
        ".local/ssh/id_ed25519_jisheng3",
    ]
    result = subprocess.run(["git", "check-ignore", *paths], cwd=jetstreamctl.REPO_ROOT, capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert set(result.stdout.splitlines()) == set(paths)


def test_phase05_entrypoint_uses_repository_manifest_without_root_monkeypatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorization_calls: list[bool] = []
    fake_phase05 = types.ModuleType("phase05_openviking")
    fake_phase05.require_live_authorization = lambda: authorization_calls.append(True)
    fake_phase05.run_remote_validation = lambda **kwargs: {"status": "BLOCKED"}
    monkeypatch.setitem(sys.modules, "phase05_openviking", fake_phase05)
    monkeypatch.setattr(
        jetstreamctl,
        "run_command",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, "a" * 40 + "\n", ""),
    )
    captured: dict[str, object] = {}

    def fake_managed_session(credentials, **kwargs):
        captured.update(kwargs)
        return {"status": "BLOCKED"}

    monkeypatch.setattr(jetstreamctl, "run_managed_session", fake_managed_session)
    result = jetstreamctl.run_phase05({"credential": "not-used"})
    assert result["status"] == "BLOCKED"
    assert authorization_calls == [True]
    assert captured["manifest_path"] == (
        jetstreamctl.REPO_ROOT
        / "runtime_reports"
        / "phase-05-openviking-session.json"
    )


def test_phase06b_entrypoint_uses_one_attempt_scoped_namespace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempt_id = "20260930T120000Z-abcdef123456"
    authorization_calls: list[bool] = []
    remote_calls: list[dict[str, object]] = []
    fake_phase06b = types.ModuleType("phase06b")
    fake_phase06b.require_live_authorization = lambda: authorization_calls.append(True)
    fake_phase06b.new_attempt_id = lambda: attempt_id
    fake_phase06b.run_remote_validation = lambda **kwargs: remote_calls.append(kwargs) or {
        "status": "PASS"
    }
    monkeypatch.setitem(sys.modules, "phase06b", fake_phase06b)
    monkeypatch.setattr(jetstreamctl, "PHASE06B_SESSION_ROOT", tmp_path / "attempts")
    monkeypatch.setattr(
        jetstreamctl,
        "run_command",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, "a" * 40 + "\n", ""),
    )
    captured: dict[str, object] = {}

    def fake_managed_session(credentials, **kwargs):
        captured.update(kwargs)
        kwargs["remote_work"]("address", {"repo_head": "b" * 40})
        return {"status": "PASS"}

    monkeypatch.setattr(jetstreamctl, "run_managed_session", fake_managed_session)
    result = jetstreamctl.run_phase06b({"credential": "not-used"})
    assert result["status"] == "PASS"
    assert authorization_calls == [True]
    assert captured["attempt_id"] == attempt_id
    assert captured["manifest_path"] == tmp_path / "attempts" / f"{attempt_id}.json"
    assert remote_calls[0]["attempt_id"] == attempt_id


def test_phase06b_supplement_entrypoint_uses_separate_attempt_namespace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempt_id = "20261001T230000Z-123456abcdef"
    authorization_calls: list[bool] = []
    remote_calls: list[dict[str, object]] = []
    fake_supplement = types.ModuleType("phase06b_supplement")
    fake_supplement.require_live_authorization = lambda: authorization_calls.append(True)
    fake_supplement.new_attempt_id = lambda: attempt_id
    fake_supplement.run_remote_validation = lambda **kwargs: remote_calls.append(kwargs) or {
        "status": "SUPPLEMENT_COMPLETE"
    }
    monkeypatch.setitem(sys.modules, "phase06b_supplement", fake_supplement)
    monkeypatch.setattr(
        jetstreamctl, "PHASE06B_SUPPLEMENT_SESSION_ROOT", tmp_path / "supplements"
    )
    monkeypatch.setattr(
        jetstreamctl,
        "run_command",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, "a" * 40 + "\n", ""),
    )
    captured: dict[str, object] = {}

    def fake_managed_session(credentials, **kwargs):
        captured.update(kwargs)
        kwargs["remote_work"]("address", {"repo_head": "b" * 40})
        return {"status": "SUPPLEMENT_COMPLETE"}

    monkeypatch.setattr(jetstreamctl, "run_managed_session", fake_managed_session)
    result = jetstreamctl.run_phase06b_supplement({"credential": "not-used"})
    assert result["status"] == "SUPPLEMENT_COMPLETE"
    assert authorization_calls == [True]
    assert captured["phase"] == "06B-S"
    assert captured["attempt_id"] == attempt_id
    assert captured["manifest_path"] == tmp_path / "supplements" / f"{attempt_id}.json"
    assert remote_calls[0]["attempt_id"] == attempt_id


def test_external_network_selection_requires_unambiguous_result() -> None:
    assert jetstreamctl.select_external_network(
        [{"ID": "network-1", "Name": "public"}]
    ) == {"id": "network-1", "name": "public"}
    with pytest.raises(jetstreamctl.JetstreamError):
        jetstreamctl.select_external_network([])
    with pytest.raises(jetstreamctl.JetstreamError):
        jetstreamctl.select_external_network(
            [{"ID": "one", "Name": "public"}, {"ID": "two", "Name": "external"}]
        )


def test_existing_floating_ip_detection_matches_only_target_ports() -> None:
    records = [
        {
            "ID": "owned-elsewhere",
            "Floating IP Address": "8.8.8.8",
            "Port": "other-port",
        },
        {
            "ID": "target-floating",
            "Floating IP Address": "1.1.1.1",
            "Port": "target-port",
        },
        {
            "ID": "free-unowned",
            "Floating IP Address": "9.9.9.9",
            "Port": None,
        },
    ]
    assert jetstreamctl.find_server_floating_ip(records, {"target-port"}) == {
        "id": "target-floating",
        "address": "1.1.1.1",
        "port_id": "target-port",
        "network_id": None,
    }
    assert jetstreamctl.find_server_floating_ip(records, {"missing-port"}) is None


def test_temporary_floating_ip_creation_parses_id_and_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_openstack(arguments: list[str], credentials: dict[str, str]) -> dict[str, str]:
        calls.append(arguments)
        return {
            "id": "floating-1",
            "floating_ip_address": "8.8.4.4",
            "port_id": "",
            "floating_network_id": "network-1",
        }

    monkeypatch.setattr(jetstreamctl, "openstack_json", fake_openstack)
    created = jetstreamctl.create_temporary_floating_ip({}, "network-1")
    assert created == {
        "id": "floating-1",
        "address": "8.8.4.4",
        "port_id": None,
        "network_id": "network-1",
    }
    assert calls[0][-1] == "network-1"


def test_association_is_scoped_to_exact_target_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []
    monkeypatch.setattr(
        jetstreamctl,
        "list_server_ports",
        lambda credentials, server_id: [{"ID": "target-port"}],
    )
    monkeypatch.setattr(
        jetstreamctl,
        "run_command",
        lambda command, **kwargs: commands.append(list(command)),
    )
    jetstreamctl.associate_floating_ip(
        {}, jetstreamctl.EXPECTED_SERVER_UUID, "target-port", "floating-1"
    )
    assert commands[0][-6:] == [
        "floating", "ip", "set", "--port", "target-port", "floating-1"
    ]
    with pytest.raises(jetstreamctl.JetstreamError):
        jetstreamctl.associate_floating_ip(
            {}, jetstreamctl.EXPECTED_SERVER_UUID, "other-port", "floating-1"
        )
    with pytest.raises(jetstreamctl.JetstreamError):
        jetstreamctl.associate_floating_ip({}, "another-server", "target-port", "floating-1")


def test_owned_floating_ip_cleanup_disassociates_then_deletes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        jetstreamctl,
        "disassociate_floating_ip",
        lambda *args, **kwargs: calls.append("disassociate"),
    )
    monkeypatch.setattr(
        jetstreamctl,
        "wait_for_floating_ip_disassociation",
        lambda *args, **kwargs: calls.append("wait-disassociate"),
    )
    monkeypatch.setattr(
        jetstreamctl,
        "delete_owned_floating_ip",
        lambda *args, **kwargs: calls.append("delete"),
    )
    monkeypatch.setattr(
        jetstreamctl,
        "wait_for_floating_ip_deletion",
        lambda *args, **kwargs: calls.append("wait-delete"),
    )
    result: dict[str, object] = {}
    errors = jetstreamctl.cleanup_owned_floating_ip(
        {}, jetstreamctl.EXPECTED_SERVER_UUID,
        {"created_by_this_run": True, "id": "floating-1"}, result,
    )
    assert errors == []
    assert calls == ["disassociate", "wait-disassociate", "delete", "wait-delete"]
    assert result["floating_ip_cleanup_success"] is True
    assert result["floating_ip_deleted_after_run"] is True


def test_unowned_floating_ip_is_never_cleaned_up(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(jetstreamctl.JetstreamError):
        jetstreamctl.delete_owned_floating_ip(
            {}, "preexisting", created_by_this_run=False
        )
    with pytest.raises(jetstreamctl.JetstreamError):
        jetstreamctl.disassociate_floating_ip(
            {}, jetstreamctl.EXPECTED_SERVER_UUID, "preexisting",
            created_by_this_run=False,
        )
    monkeypatch.setattr(
        jetstreamctl,
        "disassociate_floating_ip",
        lambda *args, **kwargs: pytest.fail("must not disassociate an unowned IP"),
    )
    monkeypatch.setattr(
        jetstreamctl,
        "delete_owned_floating_ip",
        lambda *args, **kwargs: pytest.fail("must not delete an unowned IP"),
    )
    result: dict[str, object] = {}
    assert jetstreamctl.cleanup_owned_floating_ip(
        {}, jetstreamctl.EXPECTED_SERVER_UUID,
        {"created_by_this_run": False, "id": "preexisting"}, result,
    ) == []
    assert result["floating_ip_cleanup_success"] is True
    assert result["floating_ip_deleted_after_run"] is False


@pytest.mark.parametrize("fail_after_association", [False, True])
def test_acceptance_failure_cleans_owned_ip_and_shelves_owned_vm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fail_after_association: bool,
) -> None:
    state = {"vm": "SHELVED"}
    actions: list[str] = []
    cleanup_states: list[dict[str, object]] = []
    manifest = tmp_path / "acceptance.json"
    monkeypatch.setattr(jetstreamctl, "ACCEPTANCE_FILE", manifest)

    def server() -> dict[str, object]:
        return {
            "id": jetstreamctl.EXPECTED_SERVER_UUID,
            "name": "jisheng3",
            "status": state["vm"],
            "addresses": {"private": ["10.0.0.2"]},
        }

    monkeypatch.setattr(jetstreamctl, "resolve_server", lambda credentials: (server(), {}))
    monkeypatch.setattr(
        jetstreamctl,
        "server_action",
        lambda credentials, action: (
            actions.append(action), state.update(vm="ACTIVE" if action == "unshelve" else "SHELVED")
        ),
    )
    monkeypatch.setattr(
        jetstreamctl, "wait_for_state", lambda credentials, desired, **kwargs: server()
    )
    monkeypatch.setattr(
        jetstreamctl, "discover_external_network",
        lambda credentials: {"id": "network-1", "name": "public"},
    )
    monkeypatch.setattr(
        jetstreamctl, "list_server_ports",
        lambda credentials, server_id: [{"ID": "target-port"}],
    )
    monkeypatch.setattr(jetstreamctl, "list_floating_ips", lambda credentials: [])
    monkeypatch.setattr(
        jetstreamctl, "create_temporary_floating_ip",
        lambda credentials, network_id: {
            "id": "floating-1", "address": "8.8.8.8", "port_id": None,
            "network_id": network_id,
        },
    )

    def associate(*args: object, **kwargs: object) -> None:
        if not fail_after_association:
            raise jetstreamctl.JetstreamError("association failed")

    monkeypatch.setattr(jetstreamctl, "associate_floating_ip", associate)
    monkeypatch.setattr(
        jetstreamctl,
        "wait_for_floating_ip_association",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            jetstreamctl.JetstreamError("association visibility failed")
        ),
    )

    def cleanup(credentials: object, server_id: object, floating_state: dict[str, object], result: dict[str, object]) -> list[str]:
        cleanup_states.append(dict(floating_state))
        result["floating_ip_cleanup_success"] = True
        result["floating_ip_deleted_after_run"] = True
        return []

    monkeypatch.setattr(jetstreamctl, "cleanup_owned_floating_ip", cleanup)

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        joined = " ".join(command)
        stdout = ""
        if "branch --show-current" in joined:
            stdout = "phase-02b0-jetstream-automation\n"
        elif "rev-parse HEAD" in joined:
            stdout = "deadbeef\n"
        elif "--version" in joined:
            stdout = "openstack test\n"
        return subprocess.CompletedProcess(command, 0, stdout, "")

    monkeypatch.setattr(jetstreamctl, "run_command", fake_run)
    with pytest.raises(jetstreamctl.JetstreamError):
        jetstreamctl.run_acceptance({"OS_APPLICATION_CREDENTIAL_SECRET": "secret-value"})

    recorded = json.loads(manifest.read_text(encoding="utf-8"))
    assert actions == ["unshelve", "shelve"]
    assert cleanup_states[0]["created_by_this_run"] is True
    assert cleanup_states[0]["associated_by_this_run"] is fail_after_association
    assert recorded["floating_ip_created_by_this_run"] is True
    assert recorded["floating_ip_associated_by_this_run"] is fail_after_association
    assert recorded["final_vm_state"] == "SHELVED"
    assert "8.8.8.8" not in manifest.read_text(encoding="utf-8")
    assert "secret-value" not in manifest.read_text(encoding="utf-8")


def test_manifest_sanitizer_removes_numeric_fip_and_credentials(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = tmp_path / "acceptance.json"
    monkeypatch.setattr(jetstreamctl, "ACCEPTANCE_FILE", manifest)
    jetstreamctl.write_acceptance_manifest(
        {
            "status": "BLOCKED",
            "error_message": "failed for 8.8.8.8 with top-secret",
            "floating_ip_address": "8.8.8.8",
        },
        {"OS_APPLICATION_CREDENTIAL_SECRET": "top-secret"},
        "8.8.8.8",
    )
    text = manifest.read_text(encoding="utf-8")
    assert "8.8.8.8" not in text
    assert "top-secret" not in text
    assert "floating_ip_address" not in text
