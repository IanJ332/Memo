#!/usr/bin/env python3
"""Narrow lifecycle controller for the project's single Jetstream2 VM."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import platform
import re
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_ROOT = REPO_ROOT / ".local"
CREDENTIAL_FILE = LOCAL_ROOT / "credentials" / "CIS261698_IU-openrc.ps1"
SSH_KEY = LOCAL_ROOT / "ssh" / "id_ed25519_jisheng3"
KNOWN_HOSTS = LOCAL_ROOT / "jetstream" / "known_hosts"
CONFIG_FILE = REPO_ROOT / "configs" / "jetstream.json"
ACCEPTANCE_FILE = REPO_ROOT / "manifests" / "jetstream-automation-acceptance.json"
OPENSTACK = LOCAL_ROOT / "jetstream" / "cli-venv" / "Scripts" / "openstack.exe"

EXPECTED_NAME = "jisheng3"
EXPECTED_SERVER_UUID = "5baeeae7-4c29-4903-89fe-2e9df0a8eced"
EXPECTED_PROJECT = "CIS261698"
REMOTE_USER = "exouser"
DNS_HOSTNAME = "jisheng3.cis261698.projects.jetstream-cloud.org"
VOLUME_DEVICE = "/dev/sdb"
ALLOWED_OS_VARIABLES = {
    "OS_APPLICATION_CREDENTIAL_ID",
    "OS_APPLICATION_CREDENTIAL_SECRET",
    "OS_AUTH_TYPE",
    "OS_AUTH_URL",
    "OS_IDENTITY_API_VERSION",
    "OS_INTERFACE",
    "OS_REGION_NAME",
}
SECRET_VARIABLES = {"OS_APPLICATION_CREDENTIAL_SECRET", "OS_PASSWORD", "OS_TOKEN"}
ASSIGNMENT_RE = re.compile(
    r"^\s*\$env:(OS_[A-Z0-9_]+)\s*=\s*(['\"])(.*?)\2\s*;?\s*$",
    re.IGNORECASE,
)


class JetstreamError(RuntimeError):
    """Expected, safely reportable lifecycle failure."""


def normalize_state(value: object) -> str:
    state = str(value or "").strip().upper().replace("-", "_")
    if state in {"SHELVED", "SHELVED_OFFLOADED"}:
        return "SHELVED"
    return state


def was_opened_by_run(initial_state: object) -> bool:
    """Return whether acceptance owns the SHELVED-to-ACTIVE transition."""

    return normalize_state(initial_state) == "SHELVED"


def load_credentials(path: Path = CREDENTIAL_FILE) -> dict[str, str]:
    """Parse only expected PowerShell OS_* assignments; never evaluate the file."""

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = ASSIGNMENT_RE.fullmatch(line)
        if not match:
            raise JetstreamError("credential file contains an unsupported statement")
        name, _, value = match.groups()
        name = name.upper()
        if name not in ALLOWED_OS_VARIABLES:
            raise JetstreamError(f"credential file contains unexpected variable {name}")
        values[name] = value
    required = {"OS_AUTH_URL", "OS_AUTH_TYPE", "OS_APPLICATION_CREDENTIAL_ID", "OS_APPLICATION_CREDENTIAL_SECRET"}
    missing = required - values.keys()
    if missing:
        raise JetstreamError(f"credential file is missing expected variables: {', '.join(sorted(missing))}")
    return values


def safe_environment(credentials: Mapping[str, str]) -> dict[str, str]:
    env = os.environ.copy()
    env.update(credentials)
    return env


def command_for_openstack(arguments: Sequence[str]) -> list[str]:
    return [str(OPENSTACK), *arguments]


def run_command(
    command: Sequence[str], *, env: Mapping[str, str] | None = None, timeout: int = 90
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(command), capture_output=True, text=True, env=env, timeout=timeout, check=False
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        raise JetstreamError(detail)
    return result


def openstack_json(arguments: Sequence[str], credentials: Mapping[str, str]) -> Any:
    result = run_command(
        command_for_openstack([*arguments, "-f", "json"]), env=safe_environment(credentials)
    )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise JetstreamError("OpenStack returned invalid JSON") from exc


def load_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def resolve_server(credentials: Mapping[str, str]) -> tuple[dict[str, Any], dict[str, Any]]:
    config = load_config()
    servers = openstack_json(["server", "list"], credentials)
    matches = [
        item for item in servers
        if str(field(item, "name")) == EXPECTED_NAME
        and (
            str(field(item, "id")).lower() == EXPECTED_SERVER_UUID
        )
    ]
    if len(matches) != 1:
        raise JetstreamError(f"expected exactly one current-project target, found {len(matches)}")
    target = str(field(matches[0], "id"))
    server = openstack_json(["server", "show", target], credentials)
    token = openstack_json(["token", "issue"], credentials)
    validate_identity(server, token, config)
    return server, token


def field(record: Mapping[str, Any], *names: str) -> Any:
    lowered = {str(key).lower().replace(" ", "_"): value for key, value in record.items()}
    for name in names:
        key = name.lower().replace(" ", "_")
        if key in lowered:
            return lowered[key]
    return None


def validate_identity(
    server: Mapping[str, Any], token: Mapping[str, Any], config: Mapping[str, Any] | None = None
) -> None:
    if str(field(server, "name")) != EXPECTED_NAME:
        raise JetstreamError("resolved server name does not match jisheng3")
    server_id = str(field(server, "id") or "")
    if server_id.lower() != EXPECTED_SERVER_UUID:
        raise JetstreamError("resolved server UUID does not match the authorized target")
    configured_id = str((config or {}).get("server_uuid") or "")
    if configured_id and server_id.lower() != configured_id.lower():
        raise JetstreamError("resolved server UUID does not match tracked target")
    server_project = str(field(server, "project_id", "tenant_id") or "")
    token_project = str(field(token, "project_id") or "")
    if server_project and token_project and server_project.lower() != token_project.lower():
        raise JetstreamError("server belongs to a different OpenStack project")
    project_name = str(field(token, "project_name", "project") or "")
    expected = str((config or {}).get("expected_project") or EXPECTED_PROJECT)
    if project_name and project_name != expected:
        raise JetstreamError(f"authenticated project is {project_name!r}, expected {expected!r}")


def require_target_uuid(server_id: object) -> str:
    value = str(server_id or "").lower()
    if value != EXPECTED_SERVER_UUID:
        raise JetstreamError("refusing mutation for a server other than the authorized target")
    return EXPECTED_SERVER_UUID


def select_external_network(networks: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    """Accept only an unambiguous external network discovery result."""

    candidates = [
        {"id": str(field(network, "id") or ""), "name": str(field(network, "name") or "")}
        for network in networks
        if field(network, "id")
    ]
    if len(candidates) != 1:
        raise JetstreamError(
            f"expected exactly one external network; discovered {len(candidates)}"
        )
    return candidates[0]


def discover_external_network(credentials: Mapping[str, str]) -> dict[str, str]:
    networks = openstack_json(["network", "list", "--external"], credentials)
    if not isinstance(networks, list):
        raise JetstreamError("OpenStack external network list was not a list")
    return select_external_network(networks)


def list_server_ports(
    credentials: Mapping[str, str], server_id: object
) -> list[dict[str, Any]]:
    target = require_target_uuid(server_id)
    ports = openstack_json(["port", "list", "--server", target], credentials)
    if not isinstance(ports, list):
        raise JetstreamError("OpenStack target port list was not a list")
    return ports


def select_target_port(ports: Sequence[Mapping[str, Any]]) -> str:
    port_ids = [str(field(port, "id")) for port in ports if field(port, "id")]
    if len(port_ids) != 1:
        raise JetstreamError(f"expected exactly one target port; discovered {len(port_ids)}")
    return port_ids[0]


def parse_floating_ip(record: Mapping[str, Any]) -> dict[str, str | None]:
    floating_id = str(field(record, "id") or "")
    address = str(field(record, "floating_ip_address") or "")
    if not floating_id or not address:
        raise JetstreamError("floating IP result omitted its ID or address")
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError as exc:
        raise JetstreamError("floating IP result contained an invalid address") from exc
    if not parsed.is_global:
        raise JetstreamError("floating IP result was not externally routable")
    return {
        "id": floating_id,
        "address": address,
        "port_id": str(field(record, "port", "port_id") or "") or None,
        "network_id": str(field(record, "floating_network", "floating_network_id") or "") or None,
    }


def list_floating_ips(credentials: Mapping[str, str]) -> list[dict[str, Any]]:
    records = openstack_json(["floating", "ip", "list"], credentials)
    if not isinstance(records, list):
        raise JetstreamError("OpenStack floating IP list was not a list")
    return records


def find_server_floating_ip(
    records: Sequence[Mapping[str, Any]], target_port_ids: set[str]
) -> dict[str, str | None] | None:
    matches = [
        parse_floating_ip(record)
        for record in records
        if str(field(record, "port", "port_id") or "") in target_port_ids
    ]
    if len(matches) > 1:
        raise JetstreamError("multiple floating IPs are associated with the target server")
    return matches[0] if matches else None


def create_temporary_floating_ip(
    credentials: Mapping[str, str], external_network_id: str
) -> dict[str, str | None]:
    record = openstack_json(
        [
            "floating", "ip", "create", "--description",
            "MemLife Phase 02B-0 temporary acceptance", external_network_id,
        ],
        credentials,
    )
    if not isinstance(record, Mapping):
        raise JetstreamError("OpenStack floating IP creation result was not an object")
    return parse_floating_ip(record)


def associate_floating_ip(
    credentials: Mapping[str, str], server_id: object, target_port_id: str,
    floating_ip_id: str,
) -> None:
    require_target_uuid(server_id)
    current_port_ids = {
        str(field(port, "id")) for port in list_server_ports(credentials, server_id)
        if field(port, "id")
    }
    if target_port_id not in current_port_ids:
        raise JetstreamError("refusing floating IP association with a non-target port")
    run_command(
        command_for_openstack(
            ["floating", "ip", "set", "--port", target_port_id, floating_ip_id]
        ),
        env=safe_environment(credentials),
    )


def floating_ip_show(
    credentials: Mapping[str, str], floating_ip_id: str
) -> dict[str, str | None]:
    record = openstack_json(["floating", "ip", "show", floating_ip_id], credentials)
    if not isinstance(record, Mapping):
        raise JetstreamError("OpenStack floating IP show result was not an object")
    return parse_floating_ip(record)


def wait_for_floating_ip_association(
    credentials: Mapping[str, str], server_id: object, target_port_id: str,
    floating_ip_id: str, *, timeout: int = 120, interval: int = 5,
) -> dict[str, Any]:
    target = require_target_uuid(server_id)
    deadline = time.monotonic() + timeout
    while True:
        floating = floating_ip_show(credentials, floating_ip_id)
        server = openstack_json(["server", "show", target], credentials)
        if (
            floating["port_id"] == target_port_id
            and select_address(server) == floating["address"]
        ):
            return dict(server)
        if time.monotonic() >= deadline:
            raise JetstreamError("timed out waiting for floating IP association visibility")
        time.sleep(interval)


def disassociate_floating_ip(
    credentials: Mapping[str, str], server_id: object, floating_ip_id: str,
    *, created_by_this_run: bool,
) -> None:
    require_target_uuid(server_id)
    if not created_by_this_run:
        raise JetstreamError("refusing to disassociate an unowned floating IP")
    target_ports = {
        str(field(port, "id")) for port in list_server_ports(credentials, server_id)
        if field(port, "id")
    }
    floating = floating_ip_show(credentials, floating_ip_id)
    if not floating["port_id"]:
        return
    if floating["port_id"] not in target_ports:
        raise JetstreamError("refusing to disassociate a floating IP from a non-target port")
    run_command(
        command_for_openstack(["floating", "ip", "unset", "--port", floating_ip_id]),
        env=safe_environment(credentials),
    )


def wait_for_floating_ip_disassociation(
    credentials: Mapping[str, str], floating_ip_id: str, *, timeout: int = 120,
    interval: int = 5,
) -> None:
    deadline = time.monotonic() + timeout
    while True:
        if not floating_ip_show(credentials, floating_ip_id)["port_id"]:
            return
        if time.monotonic() >= deadline:
            raise JetstreamError("timed out waiting for floating IP disassociation")
        time.sleep(interval)


def delete_owned_floating_ip(
    credentials: Mapping[str, str], floating_ip_id: str, *, created_by_this_run: bool
) -> None:
    if not created_by_this_run:
        raise JetstreamError("refusing to delete an unowned floating IP")
    if floating_ip_show(credentials, floating_ip_id)["port_id"]:
        raise JetstreamError("refusing to delete an associated floating IP")
    run_command(
        command_for_openstack(["floating", "ip", "delete", floating_ip_id]),
        env=safe_environment(credentials),
    )


def wait_for_floating_ip_deletion(
    credentials: Mapping[str, str], floating_ip_id: str, *, timeout: int = 120,
    interval: int = 5,
) -> None:
    deadline = time.monotonic() + timeout
    while True:
        remaining_ids = {
            str(field(record, "id")) for record in list_floating_ips(credentials)
            if field(record, "id")
        }
        if floating_ip_id not in remaining_ids:
            return
        if time.monotonic() >= deadline:
            raise JetstreamError("timed out waiting for floating IP deletion")
        time.sleep(interval)


def iter_addresses(value: Any, network: str = "") -> list[tuple[str, str, str]]:
    found: list[tuple[str, str, str]] = []
    if isinstance(value, Mapping):
        address = value.get("addr") or value.get("address")
        if address:
            kind = str(value.get("OS-EXT-IPS:type") or value.get("type") or "")
            found.append((str(address), kind, network))
        else:
            for key, child in value.items():
                found.extend(iter_addresses(child, str(key)))
    elif isinstance(value, list):
        for child in value:
            found.extend(iter_addresses(child, network))
    elif isinstance(value, str):
        for group in value.split(";"):
            net, _, addresses = group.partition("=")
            for address in addresses.split(",") if addresses else group.split(","):
                candidate = address.strip()
                try:
                    ipaddress.ip_address(candidate)
                except ValueError:
                    continue
                found.append((candidate, "", net.strip() if addresses else network))
    return found


def select_address(server: Mapping[str, Any]) -> str | None:
    candidates = [
        item
        for item in iter_addresses(field(server, "addresses") or {})
        if ipaddress.ip_address(item[0]).is_global
    ]
    if not candidates:
        return None
    def rank(item: tuple[str, str, str]) -> tuple[int, int]:
        address, kind, network = item
        ip = ipaddress.ip_address(address)
        floating = "floating" in kind.lower() or "public" in network.lower()
        return (
            0 if floating else 1,
            0 if ip.version == 4 else 1,
        )
    return sorted(candidates, key=rank)[0][0]


def wait_for_state(
    credentials: Mapping[str, str], desired: str, *, timeout: int = 600, interval: int = 10
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while True:
        server, _ = resolve_server(credentials)
        state = normalize_state(field(server, "status"))
        if state == desired:
            return server
        if state == "ERROR":
            raise JetstreamError("server entered ERROR state")
        if time.monotonic() >= deadline:
            raise JetstreamError(f"timed out waiting for {desired}; last state was {state}")
        time.sleep(interval)


def ssh_command(address: str, remote_command: str) -> list[str]:
    KNOWN_HOSTS.parent.mkdir(parents=True, exist_ok=True)
    return [
        "ssh", "-i", str(SSH_KEY), "-o", "BatchMode=yes",
        "-o", "IdentitiesOnly=yes", "-o", "StrictHostKeyChecking=accept-new",
        "-o", f"UserKnownHostsFile={KNOWN_HOSTS}", "-o", f"HostKeyAlias={DNS_HOSTNAME}",
        "-o", "ConnectTimeout=20", f"{REMOTE_USER}@{address}", remote_command,
    ]


def wait_for_tcp_22(address: str, timeout: int = 300, interval: int = 10) -> float:
    started = time.monotonic()
    deadline = started + timeout
    while True:
        try:
            with socket.create_connection((address, 22), timeout=5):
                return time.monotonic() - started
        except OSError:
            if time.monotonic() >= deadline:
                raise JetstreamError("TCP_TIMEOUT: port 22 did not become reachable")
            time.sleep(interval)


def classify_ssh_error(detail: str) -> str:
    lowered = detail.lower()
    if "permission denied" in lowered or "authentication failed" in lowered:
        return "AUTH_DENIED"
    if "host key verification failed" in lowered or "remote host identification has changed" in lowered:
        return "HOST_KEY_ERROR"
    if "timed out" in lowered or "connection refused" in lowered or "no route to host" in lowered:
        return "TCP_TIMEOUT"
    return "SSH_PROTOCOL_ERROR"


def verify_ssh(address: str) -> None:
    try:
        run_command(ssh_command(address, "true"), timeout=30)
    except subprocess.TimeoutExpired as exc:
        raise JetstreamError("TCP_TIMEOUT: SSH client timed out") from exc
    except JetstreamError as exc:
        raise JetstreamError(f"{classify_ssh_error(str(exc))}: {exc}") from exc


def wait_for_ssh(address: str, timeout: int = 300) -> None:
    """Compatibility helper for explicit ssh-check/probe commands."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            verify_ssh(address)
            return
        except (JetstreamError, subprocess.TimeoutExpired):
            if time.monotonic() >= deadline:
                raise JetstreamError("timed out waiting for SSH")
            time.sleep(10)


PROBE_SCRIPT = r'''set -eu
actual_mount="$(findmnt -n -o TARGET /dev/sdb)"
printf 'remote_user=%s\n' "$(whoami)"
printf 'remote_hostname=%s\n' "$(hostname)"
printf 'remote_uname_b64=%s\n' "$(uname -a | base64 -w0)"
printf 'repo_branch=%s\n' "$(git -C /home/exouser/Memo branch --show-current)"
printf 'repo_head=%s\n' "$(git -C /home/exouser/Memo rev-parse HEAD)"
printf 'repo_status_b64=%s\n' "$(git -C /home/exouser/Memo status --short | base64 -w0)"
printf 'volume_device=/dev/sdb\n'
printf 'resolved_volume_mount=%s\n' "$actual_mount"
printf 'volume_capacity=%s\n' "$(df -h --output=size "$actual_mount" | tail -n 1 | xargs)"
findmnt /dev/sdb >&2
df -h "$actual_mount" >&2
printf 'python=%s\n' "$(/home/exouser/Memo/.venv/bin/python --version 2>&1)"
'''


def parse_key_values(output: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in output.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            result[key.strip()] = value.strip()
    return result


def probe(address: str) -> dict[str, str]:
    result = run_command(ssh_command(address, PROBE_SCRIPT), timeout=90)
    facts = parse_key_values(result.stdout)
    if facts.get("remote_user") != REMOTE_USER or facts.get("remote_hostname") != EXPECTED_NAME:
        raise JetstreamError("remote identity validation failed")
    mount = facts.get("resolved_volume_mount", "")
    if not mount.startswith("/"):
        raise JetstreamError("/dev/sdb did not resolve to an absolute mountpoint")
    return facts


def status_payload(server: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": field(server, "id"),
        "name": field(server, "name"),
        "status": normalize_state(field(server, "status")),
        "address_available": select_address(server) is not None,
    }


def server_action(credentials: Mapping[str, str], action: str) -> None:
    server, _ = resolve_server(credentials)
    server_id = require_target_uuid(field(server, "id"))
    run_command(command_for_openstack(["server", action, server_id]), env=safe_environment(credentials))


def collect_security_group_evidence(
    credentials: Mapping[str, str], server_id: object
) -> dict[str, Any]:
    group_ids: set[str] = set()
    for port in list_server_ports(credentials, server_id):
        port_id = str(field(port, "id") or "")
        if not port_id:
            continue
        detail = openstack_json(["port", "show", port_id], credentials)
        raw_groups = field(detail, "security_group_ids", "security_groups") or []
        if isinstance(raw_groups, str):
            group_ids.update(re.findall(r"[0-9a-fA-F-]{36}", raw_groups))
        elif isinstance(raw_groups, list):
            group_ids.update(str(item) for item in raw_groups)
    evidence: dict[str, Any] = {"security_group_ids": sorted(group_ids), "groups": []}
    for group_id in sorted(group_ids):
        rules = openstack_json(["security", "group", "rule", "list", group_id], credentials)
        ssh_ingress = False
        if isinstance(rules, list):
            for rule in rules:
                direction = str(field(rule, "direction") or "").lower()
                protocol = str(field(rule, "protocol") or "").lower()
                port_range = str(field(rule, "port_range", "port_range_min") or "")
                if direction == "ingress" and protocol in {"tcp", "6"} and (
                    port_range == "22" or "22:22" in port_range
                ):
                    ssh_ingress = True
        evidence["groups"].append(
            {"id": group_id, "rule_count": len(rules) if isinstance(rules, list) else None,
             "tcp_22_ingress_rule_observed": ssh_ingress}
        )
    return evidence


def cleanup_owned_floating_ip(
    credentials: Mapping[str, str], server_id: object,
    floating_state: Mapping[str, Any], result: dict[str, Any],
) -> list[str]:
    """Best-effort cleanup; mutate only a floating IP created by this run."""

    errors: list[str] = []
    created = bool(floating_state.get("created_by_this_run"))
    floating_id = str(floating_state.get("id") or "")
    if not created:
        result["floating_ip_cleanup_success"] = True
        result["floating_ip_deleted_after_run"] = False
        result["floating_ip_disassociation_success"] = None
        return errors
    if not floating_id:
        errors.append("owned floating IP ID was unavailable for cleanup")
        result["floating_ip_cleanup_success"] = False
        result["floating_ip_deleted_after_run"] = False
        result["floating_ip_disassociation_success"] = False
        return errors
    try:
        disassociate_floating_ip(
            credentials, server_id, floating_id, created_by_this_run=True
        )
        wait_for_floating_ip_disassociation(credentials, floating_id)
        result["floating_ip_disassociation_success"] = True
    except BaseException as exc:
        errors.append(f"floating IP disassociation cleanup failed: {type(exc).__name__}")
        result["floating_ip_disassociation_success"] = False
    try:
        delete_owned_floating_ip(
            credentials, floating_id, created_by_this_run=True
        )
        wait_for_floating_ip_deletion(credentials, floating_id)
        result["floating_ip_deleted_after_run"] = True
    except BaseException as exc:
        errors.append(f"floating IP deletion cleanup failed: {type(exc).__name__}")
        result["floating_ip_deleted_after_run"] = False
    result["floating_ip_cleanup_success"] = not errors
    return errors


def sanitize_acceptance_payload(
    payload: Any, credentials: Mapping[str, str], transient_address: str | None
) -> Any:
    secrets = [str(credentials.get(name) or "") for name in SECRET_VARIABLES]
    replacements = [value for value in [*secrets, transient_address or ""] if value]

    def sanitize(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                str(key): sanitize(child)
                for key, child in value.items()
                if str(key).lower() != "floating_ip_address"
            }
        if isinstance(value, list):
            return [sanitize(child) for child in value]
        if isinstance(value, str):
            for replacement in replacements:
                value = value.replace(replacement, "<redacted>")
        return value

    return sanitize(payload)


def write_acceptance_manifest(
    result: Mapping[str, Any], credentials: Mapping[str, str],
    transient_address: str | None,
) -> None:
    sanitized = sanitize_acceptance_payload(result, credentials, transient_address)
    serialized = json.dumps(sanitized, indent=2) + "\n"
    if transient_address and transient_address in serialized:
        raise JetstreamError("refusing to serialize the transient floating IP address")
    for name in SECRET_VARIABLES:
        secret = str(credentials.get(name) or "")
        if secret and secret in serialized:
            raise JetstreamError("refusing to serialize an OpenStack credential")
    ACCEPTANCE_FILE.write_text(serialized, encoding="utf-8")


def run_acceptance(credentials: Mapping[str, str]) -> dict[str, Any]:
    initial, _ = resolve_server(credentials)
    target_uuid = require_target_uuid(field(initial, "id"))
    initial_state = normalize_state(field(initial, "status"))
    if initial_state not in {"ACTIVE", "SHELVED"}:
        raise JetstreamError(f"acceptance requires ACTIVE or SHELVED, found {initial_state}")
    opened = was_opened_by_run(initial_state)
    result: dict[str, Any] = {
        "phase": "02B-0", "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "IN_PROGRESS",
        "branch": run_command(["git", "branch", "--show-current"]).stdout.strip(),
        "git_commit": run_command(["git", "rev-parse", "HEAD"]).stdout.strip(),
        "workstation_platform": platform.platform(),
        "openstack_client_version": run_command([str(OPENSTACK), "--version"]).stdout.strip(),
        "target_instance_name": EXPECTED_NAME, "target_uuid": target_uuid,
        "initial_vm_state": initial_state, "unshelve_success": not opened,
        "external_network": None,
        "floating_ip_required": False, "floating_ip_preexisting": False,
        "floating_ip_created_by_this_run": False,
        "floating_ip_associated_by_this_run": False,
        "floating_ip_cleanup_success": None,
        "floating_ip_deleted_after_run": False,
        "external_address_resolved": False, "tcp_22_ready": False,
        "active_to_tcp_ready_seconds": None, "ssh_success": False,
        "ssh_failure_category": None, "remote_user": None, "hostname": None,
        "verified_volume_device": VOLUME_DEVICE, "verified_volume_mount": None,
        "final_vm_state": None,
        "opened_by_this_run": opened, "auto_shelve_success": False,
        "numeric_address_persisted": False,
    }
    failure: BaseException | None = None
    cleanup_errors: list[str] = []
    transient_address: str | None = None
    floating_state: dict[str, Any] = {
        "preexisting": False,
        "created_by_this_run": False,
        "associated_by_this_run": False,
        "id": None,
    }
    try:
        external_network = discover_external_network(credentials)
        result["external_network"] = external_network
        target_ports = list_server_ports(credentials, target_uuid)
        target_port_id = select_target_port(target_ports)
        existing = find_server_floating_ip(
            list_floating_ips(credentials), {target_port_id}
        )
        result["floating_ip_required"] = existing is None
        if existing:
            floating_state.update(preexisting=True, id=existing["id"])
            result["floating_ip_preexisting"] = True
        if opened:
            server_action(credentials, "unshelve")
            initial = wait_for_state(credentials, "ACTIVE")
            result["unshelve_success"] = True
        target_ports = list_server_ports(credentials, target_uuid)
        target_port_id = select_target_port(target_ports)
        current = find_server_floating_ip(
            list_floating_ips(credentials), {target_port_id}
        )
        if current:
            floating_state.update(preexisting=True, id=current["id"])
            result["floating_ip_preexisting"] = True
        else:
            result["failure_stage"] = "FLOATING_IP_ALLOCATION"
            current = create_temporary_floating_ip(credentials, external_network["id"])
            floating_state.update(created_by_this_run=True, id=current["id"])
            result["floating_ip_created_by_this_run"] = True
            transient_address = str(current["address"])
            result["failure_stage"] = "FLOATING_IP_ASSOCIATION"
            associate_floating_ip(
                credentials, target_uuid, target_port_id, str(current["id"])
            )
            floating_state["associated_by_this_run"] = True
            result["floating_ip_associated_by_this_run"] = True
        transient_address = str(current["address"])
        initial = wait_for_floating_ip_association(
            credentials, target_uuid, target_port_id, str(current["id"])
        )
        address = select_address(initial)
        if not address or address != transient_address:
            result["failure_stage"] = "ADDRESS"
            raise JetstreamError("associated floating IP was not externally routable")
        result["external_address_resolved"] = True
        try:
            result["tracked_dns_resolved"] = socket.gethostbyname(DNS_HOSTNAME) == address
        except OSError:
            result["tracked_dns_resolved"] = False
        try:
            result["active_to_tcp_ready_seconds"] = round(wait_for_tcp_22(address), 3)
            result["tcp_22_ready"] = True
        except JetstreamError:
            result["failure_stage"] = "TCP_22"
            try:
                result["security_group_evidence"] = collect_security_group_evidence(
                    credentials, target_uuid
                )
            except BaseException as evidence_exc:
                result["security_group_evidence_error"] = type(evidence_exc).__name__
            raise
        try:
            verify_ssh(address)
        except JetstreamError as exc:
            result["ssh_failure_category"] = str(exc).split(":", 1)[0]
            result["failure_stage"] = (
                "SSH_AUTH" if result["ssh_failure_category"] == "AUTH_DENIED" else "SSH_PROTOCOL"
            )
            raise
        result["ssh_success"] = True
        result["ssh_failure_category"] = "SSH_SUCCESS"
        facts = probe(address)
        result.update(
            remote_user=facts["remote_user"],
            hostname=facts["remote_hostname"],
            remote_uname_b64=facts.get("remote_uname_b64"),
            verified_volume_mount=facts["resolved_volume_mount"],
            volume_capacity=facts.get("volume_capacity"),
            remote_repo="/home/exouser/Memo",
            remote_repo_branch=facts.get("repo_branch"),
            remote_repo_head=facts.get("repo_head"),
            remote_repo_clean=not bool(facts.get("repo_status_b64")),
            remote_python=facts.get("python"),
            derived_memlife_root=facts["resolved_volume_mount"].rstrip("/") + "/memlife",
        )
    except BaseException as exc:
        failure = exc
        result["status"] = "BLOCKED"
        result["error"] = type(exc).__name__
        result["error_message"] = str(exc)
        result.setdefault("failure_stage", "REMOTE_PROBE")
    finally:
        cleanup_errors.extend(
            cleanup_owned_floating_ip(credentials, target_uuid, floating_state, result)
        )
        if opened:
            try:
                server_action(credentials, "shelve")
                wait_for_state(credentials, "SHELVED")
                result["auto_shelve_success"] = True
            except BaseException as exc:
                cleanup_errors.append(f"VM shelving cleanup failed: {type(exc).__name__}")
            try:
                current, _ = resolve_server(credentials)
                result["final_vm_state"] = normalize_state(field(current, "status"))
            except BaseException as exc:
                cleanup_errors.append(f"final VM state check failed: {type(exc).__name__}")
        else:
            try:
                current, _ = resolve_server(credentials)
                result["final_vm_state"] = normalize_state(field(current, "status"))
            except BaseException as exc:
                cleanup_errors.append(f"final VM state check failed: {type(exc).__name__}")
    if cleanup_errors:
        result["cleanup_errors"] = cleanup_errors
        result["status"] = "BLOCKED"
        result.setdefault("failure_stage", "CLEANUP")
    elif failure is None:
        result["status"] = "PASS"
    write_acceptance_manifest(result, credentials, transient_address)
    if failure is not None or cleanup_errors:
        raise JetstreamError(str(failure or "; ".join(cleanup_errors)))
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("doctor", "status", "unshelve", "address", "ssh-check", "probe", "shelve", "acceptance"))
    args = parser.parse_args(argv)
    try:
        credentials = load_credentials()
        if args.command == "doctor":
            checks = {
                "credential_file": CREDENTIAL_FILE.is_file(), "ssh_key": SSH_KEY.is_file(),
                "openstack_client": OPENSTACK.is_file(), "config": CONFIG_FILE.is_file(),
            }
            if not all(checks.values()):
                raise JetstreamError(f"doctor checks failed: {checks}")
            output: Any = {**checks, "openstack_version": run_command([str(OPENSTACK), "--version"]).stdout.strip()}
        else:
            server, _ = resolve_server(credentials)
            if args.command == "status":
                output = status_payload(server)
            elif args.command == "unshelve":
                server_action(credentials, "unshelve")
                output = status_payload(wait_for_state(credentials, "ACTIVE"))
            elif args.command == "shelve":
                server_action(credentials, "shelve")
                output = status_payload(wait_for_state(credentials, "SHELVED"))
            elif args.command == "address":
                output = {"dynamic_address_resolved": bool(select_address(server)), "dns_hostname": DNS_HOSTNAME}
            elif args.command in {"ssh-check", "probe"}:
                address = select_address(server)
                if not address:
                    raise JetstreamError("no current OpenStack address was reported")
                wait_for_ssh(address)
                output = {"ssh_success": True} if args.command == "ssh-check" else probe(address)
            else:
                output = run_acceptance(credentials)
        print(json.dumps(output, indent=2))
        return 0
    except (JetstreamError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
