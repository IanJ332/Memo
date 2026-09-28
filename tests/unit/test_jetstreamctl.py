"""Offline safeguards for the narrow Jetstream2 lifecycle controller."""

import importlib.util
import json
from pathlib import Path

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


def test_identity_accepts_only_expected_target() -> None:
    server = {"id": "vm-123", "name": "jisheng3", "project_id": "project-1"}
    token = {"project_id": "project-1", "project_name": "CIS261698"}
    jetstreamctl.validate_identity(server, token, {"server_uuid": "vm-123"})
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
    import subprocess

    paths = [
        ".local/credentials/CIS261698_IU-openrc.ps1",
        ".local/ssh/id_ed25519_jisheng3",
    ]
    result = subprocess.run(["git", "check-ignore", *paths], cwd=jetstreamctl.REPO_ROOT, capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert set(result.stdout.splitlines()) == set(paths)
