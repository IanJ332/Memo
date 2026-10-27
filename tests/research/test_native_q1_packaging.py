"""Independent pure packaging/runtime controls; no prospective package or native run."""
import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from types import SimpleNamespace

import pytest

from memlife.native_q1 import core, packaging, runtime


def identity(path):
    data = path.read_bytes()
    return dict(path=str(path.resolve()), sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))


def runtime_fixture(tmp_path):
    """Small scripted installed distribution, never the actual native runtime."""
    venv = tmp_path / "SYNTHETIC-NONEXECUTABLE-venv"
    site = venv / "site-packages"
    folder = site / "synthetic-1.dist-info"
    folder.mkdir(parents=True)
    module = site / "synthetic.py"
    module.write_bytes(b"# synthetic integrity fixture only\n")
    metadata = folder / "METADATA"
    metadata.write_bytes(b"Name: synthetic\nVersion: 1\n")
    record = folder / "RECORD"
    digest = base64.urlsafe_b64encode(hashlib.sha256(module.read_bytes()).digest()).decode().rstrip("=")
    record.write_text(f"synthetic.py,sha256={digest},{module.stat().st_size}\nsynthetic-1.dist-info/RECORD,,\n")
    support = tmp_path / "SYNTHETIC-support.json"
    support.write_text("{}")
    model = tmp_path / "SYNTHETIC-model-not-a-model.bin"
    model.write_bytes(b"synthetic cached bytes")
    receipt = dict(schema="NEXT_LP_NATIVE_Q1_RUNTIME_READINESS_V1",
        status="PASS_READ_ONLY_RUNTIME_IDENTITY_AND_CAPACITY", native_imports_or_constructions=0,
        containers_started=0, dependency_lock=identity(support), original_qualification_inventory=identity(support),
        qualified_provenance={"fixture": identity(support)}, embedding={"files": [identity(model)]},
        site_packages=str(site), venv_root=str(venv), installed_record_check=dict(hashed_files=1,
        distributions=[dict(distribution=folder.name, record_sha256=identity(record)["sha256"],
                            metadata_sha256=identity(metadata)["sha256"])]))
    return receipt, module, model


def test_exact_readiness_receipt_status_is_accepted(tmp_path):
    receipt, _, _ = runtime_fixture(tmp_path)
    assert packaging.verify_runtime(receipt) == dict(installed_hashes=1, distributions=1, embedding_files=1)


def test_runtime_drift_rejected_even_when_record_file_is_unchanged(tmp_path):
    receipt, module, _ = runtime_fixture(tmp_path)
    module.write_bytes(b"# changed executable source\n")
    with pytest.raises(ValueError, match="RUNTIME_FILE_DRIFT"):
        packaging.verify_runtime(receipt)


def test_extra_installed_distribution_rejected(tmp_path):
    receipt, _, _ = runtime_fixture(tmp_path)
    (Path(receipt["site_packages"]) / "unexpected-1.dist-info").mkdir()
    with pytest.raises(ValueError, match="RUNTIME_DISTRIBUTION_DRIFT"):
        packaging.verify_runtime(receipt)


def test_model_cache_drift_rejected(tmp_path):
    receipt, _, model = runtime_fixture(tmp_path)
    model.write_bytes(b"different synthetic bytes")
    with pytest.raises(ValueError, match="PINNED_ARTIFACT_DRIFT"):
        packaging.verify_runtime(receipt)


def synthetic_grant(tmp_path, *, duration=1800):
    """Unit-only provenance parser fixture; never an actual owner authorization."""
    now = datetime(2026, 10, 27, 12, tzinfo=timezone.utc)
    start, end = now - timedelta(seconds=1), now + timedelta(seconds=duration-1)
    package = dict(execution_id="SYNTHETIC-NO-LIVE-AUTHORITY")
    digest = "a" * 64
    message = tmp_path / "SYNTHETIC-NOT-HUMAN-AUTHORIZATION.txt"
    message.write_text(f"SYNTHETIC parser-only unit fixture. {package['execution_id']} {digest} 18 "
                       f"{start.isoformat()} {end.isoformat()}")
    grant = dict(schema="Q1_OWNER_GRANT_V1", approved=True, execution_id=package["execution_id"],
        package_sha256=digest, starts_at_utc=start.isoformat(), expires_at_utc=end.isoformat(),
        owner_message=dict(origin="DIRECT_OWNER_MESSAGE", **identity(message)))
    return package, digest, grant, now, message


def test_unapproved_grant_never_passes_provenance_checks(tmp_path):
    package, digest, grant, now, _ = synthetic_grant(tmp_path)
    grant["approved"] = False
    with pytest.raises(ValueError, match="FRESH_EXACT_OWNER_GRANT_REQUIRED"):
        packaging.validate_grant(package, digest, grant, now=now)


def test_grant_cannot_authorize_different_package(tmp_path):
    package, _, grant, now, _ = synthetic_grant(tmp_path)
    with pytest.raises(ValueError, match="FRESH_EXACT_OWNER_GRANT_REQUIRED"):
        packaging.validate_grant(package, "b" * 64, grant, now=now)


@pytest.mark.parametrize("seconds", [0, 1801])
def test_grant_window_is_current_not_merely_recorded(tmp_path, seconds):
    package, digest, grant, now, _ = synthetic_grant(tmp_path)
    check = now - timedelta(seconds=2) if seconds == 0 else now + timedelta(seconds=seconds)
    with pytest.raises(ValueError, match="FRESH_OWNER_WINDOW_REQUIRED"):
        packaging.validate_grant(package, digest, grant, now=check)


def test_grant_window_never_exceeds_registered_total(tmp_path):
    package, digest, grant, now, _ = synthetic_grant(tmp_path, duration=2701)
    with pytest.raises(ValueError, match="FRESH_OWNER_WINDOW_REQUIRED"):
        packaging.validate_grant(package, digest, grant, now=now)


def test_changed_provenance_file_is_not_silent_owner_consent(tmp_path):
    package, digest, grant, now, message = synthetic_grant(tmp_path)
    message.write_text("SYNTHETIC changed provenance")
    with pytest.raises(ValueError, match="PINNED_ARTIFACT_DRIFT"):
        packaging.validate_grant(package, digest, grant, now=now)


def test_run_rejects_unapproved_grant_before_runtime_or_transport(tmp_path, monkeypatch):
    path = tmp_path / "SYNTHETIC-package.json"
    path.write_text("{}")
    grant = tmp_path / "SYNTHETIC-unapproved.json"
    grant.write_text('{"approved":false}')
    monkeypatch.setattr(packaging, "verify_package", lambda path: dict(execution_id="SYNTHETIC"))
    monkeypatch.setattr(packaging, "verify_runtime", lambda value: pytest.fail("runtime reached before grant rejection"))
    monkeypatch.setattr(runtime.DockerTransport, "__init__", lambda *a, **k: pytest.fail("native transport constructed"))
    with pytest.raises(ValueError, match="FRESH_EXACT_OWNER_GRANT_REQUIRED"):
        packaging.run(path, grant)


def test_docker_mount_contract_never_exposes_host_associations(tmp_path):
    package = dict(execution_id="SYNTHETIC-NO-LIVE-AUTHORITY", container_name="synthetic-container",
        authorized_deadline_monotonic=time.monotonic()+2700,
        locations=dict(store=str(tmp_path/"store"), source=str(tmp_path/"SOURCE")),
        runtime=dict(runtime_root=str(tmp_path/"READONLY-runtime"),
            docker=dict(executable="SYNTHETIC-NOT-DOCKER", host="SYNTHETIC-NO-SOCKET", image=dict(Id="sha256:synthetic"))))
    transport = runtime.DockerTransport(package, tmp_path/"HOST-EVIDENCE")
    command = transport.create_command()
    mounts = [command[index+1] for index, value in enumerate(command) if value == "--mount"]
    assert len(mounts) == 3
    assert [value for value in mounts if not value.endswith(",readonly")] == [f"type=bind,src={tmp_path/'store'},dst=/state"]
    assert all("HOST-EVIDENCE" not in value for value in mounts)
    assert command[command.index("--network")+1] == "none"
    assert command[command.index("--memory")+1] == "6g"
    assert command[command.index("--cpus")+1] == "2"
    assert "--pull=never" in command and "--read-only" in command


def test_verify_package_rejects_member_tamper_without_creating_prospective_package(tmp_path):
    root = tmp_path / "SYNTHETIC-TEST-ARTIFACT-NOT-PROSPECTIVE"
    root.mkdir()
    source = root / "SOURCE/test-fixture.py"
    source.parent.mkdir()
    source.write_bytes(b"# synthetic package membership fixture only\n")
    package = core.design_package("SYNTHETIC-PACKAGE-NO-LIVE-AUTHORITY", "synthetic-package-test")
    package.update(locations=dict(package=str(root), source=str(root/"SOURCE"),
        store=str(tmp_path/"stores/synthetic"), evidence=str(tmp_path/"evidence/synthetic")),
        sources={"test-fixture.py": hashlib.sha256(source.read_bytes()).hexdigest()})
    core.Files(root).write("package.json", package)
    core.Files(root).seal()
    source.chmod(0o600)
    source.write_bytes(b"# changed fixture source\n")
    with pytest.raises(ValueError, match="PACKAGE_MEMBER_DRIFT"):
        packaging.verify_package(root/"package.json")


def mocked_transport(tmp_path):
    package = dict(execution_id="SYNTHETIC-NO-LIVE-AUTHORITY", container_name="synthetic-container",
        authorized_deadline_monotonic=time.monotonic()+2700,
        locations=dict(store=str(tmp_path/"store"), source=str(tmp_path/"SOURCE")),
        runtime=dict(runtime_root=str(tmp_path/"READONLY-runtime"),
            docker=dict(executable="SYNTHETIC-NOT-DOCKER", host="SYNTHETIC-NO-SOCKET", image=dict(Id="sha256:synthetic"))))
    out = tmp_path / "HOST-EVIDENCE"
    out.mkdir()
    transport = runtime.DockerTransport(package, out)
    transport.phase = 1
    return transport


def test_malformed_transport_bytes_are_retained_before_json_parse(tmp_path):
    transport = mocked_transport(tmp_path)
    read_fd, write_fd = os.pipe()
    os.write(write_fd, b"not valid JSON\n")
    os.close(write_fd)
    with os.fdopen(read_fd, "rb", buffering=0) as stream:
        transport.process = SimpleNamespace(stdout=stream)
        with pytest.raises(ValueError):
            transport.read()
    frames = list((transport.out / "transport").glob("*-frame-*.json"))
    assert len(frames) == 1
    retained = json.loads(frames[0].read_bytes())
    assert base64.b64decode(retained["base64"]) == b"not valid JSON\n"
    assert retained["bytes"] == len(b"not valid JSON\n")


def test_partial_response_survives_timeout_as_unknown(tmp_path, monkeypatch):
    transport = mocked_transport(tmp_path)
    transport.buffer = b'{"unfinished":'
    transport.deadline = 99
    monkeypatch.setattr(runtime.time, "monotonic", lambda: 100)
    read_fd, write_fd = os.pipe()
    os.close(write_fd)
    with os.fdopen(read_fd, "rb", buffering=0) as stream:
        transport.process = SimpleNamespace(stdout=stream)
        with pytest.raises(ValueError, match="SDK_RESPONSE_TIMEOUT"):
            transport.read()
    partial = list((transport.out / "transport").glob("*-partial-*.json"))
    assert len(partial) == 1
    retained = json.loads(partial[0].read_bytes())
    assert retained["completion"] == "MALFORMED_OR_PARTIAL_TRANSPORT_UNKNOWN"
    assert base64.b64decode(retained["base64"]) == b'{"unfinished":'


def test_cleanup_mode_cannot_start_another_scientific_process(tmp_path, monkeypatch):
    transport = mocked_transport(tmp_path)
    transport.cleaning = True
    transport.cleanup_until = time.monotonic()+60
    monkeypatch.setattr(runtime.subprocess, "run", lambda *a, **k: pytest.fail("scientific process reached dispatch"))
    with pytest.raises(ValueError, match="CLEANUP_ONLY_NO_SCIENTIFIC_EXTENSION"):
        transport.command(["exec", "synthetic-container", "anything"])


def test_reserved_cleanup_allows_only_bounded_owned_inspection(tmp_path, monkeypatch):
    transport = mocked_transport(tmp_path)
    transport.cleaning, transport.deadline, transport.cleanup_until = True, 90, 120
    monkeypatch.setattr(runtime.time, "monotonic", lambda: 100)
    calls = []
    def inspected(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout=b"[]", stderr=b"")
    monkeypatch.setattr(runtime.subprocess, "run", inspected)
    assert transport.command(["container", "inspect", transport.name]).returncode == 0
    assert len(calls) == 1 and calls[0][1]["timeout"] == 20


def test_expired_cleanup_does_not_dispatch_even_removal(tmp_path, monkeypatch):
    transport = mocked_transport(tmp_path)
    transport.cleaning, transport.cleanup_until = True, 99
    monkeypatch.setattr(runtime.time, "monotonic", lambda: 100)
    monkeypatch.setattr(runtime.subprocess, "run", lambda *a, **k: pytest.fail("expired cleanup reached dispatch"))
    with pytest.raises(ValueError, match="LIVE_OR_CLEANUP_WINDOW"):
        transport.command(["container", "rm", transport.name])


def test_cleanup_reserve_never_extends_absolute_owner_deadline(tmp_path, monkeypatch):
    transport = mocked_transport(tmp_path)
    transport.hard_deadline = 110
    monkeypatch.setattr(runtime.time, "monotonic", lambda: 100)
    monkeypatch.setattr(transport, "command", lambda args, **kwargs: subprocess.CompletedProcess(
        args, 1, stdout=b"", stderr=f"No such container: {transport.name}".encode()))
    result = transport.cleanup()
    assert result["container_absent"] and result["store_absent"]
    assert transport.cleaning and transport.cleanup_until == 110
