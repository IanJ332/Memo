"""Phase 06B managed-lifecycle and remote fail-closed preparation tests."""

from __future__ import annotations

import base64
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from memlife.adapters.mem0 import phase02a_manifest_configuration
from memlife.adapters.openviking import phase05a_manifest_configuration
from memlife.runner.manifest import hash_configuration
from memlife.runner.storage_batch import EXPECTED_CONFIGURATION_HASHES

ROOT = Path(__file__).resolve().parents[2]
CONTROLLER = ROOT / "scripts" / "jetstream" / "phase06b.py"
REMOTE_SHELL = ROOT / "scripts" / "jetstream" / "phase06b_remote.sh"
HARNESS_SELECTOR = ROOT / "scripts" / "jetstream" / "phase06b_harness.py"


def _controller_module():
    spec = importlib.util.spec_from_file_location("phase06b_controller", CONTROLLER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _harness_module():
    spec = importlib.util.spec_from_file_location("phase06b_harness", HARNESS_SELECTOR)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _fake_venv(path: Path) -> Path:
    python = path / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text("placeholder", encoding="utf-8")
    python.chmod(0o755)
    (path / "pyvenv.cfg").write_text("home = /usr/bin\n", encoding="utf-8")
    return path


def test_live_authorization_is_new_and_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _controller_module()
    monkeypatch.delenv("MEMLIFE_AUTHORIZE_PHASE06B_LIVE", raising=False)
    with pytest.raises(RuntimeError, match="disabled"):
        module.require_live_authorization()
    monkeypatch.setenv("MEMLIFE_AUTHORIZE_PHASE06B_LIVE", "YES")
    module.require_live_authorization()


def test_remote_sync_requires_exact_branch_and_commit() -> None:
    module = _controller_module()
    commit = "a" * 40
    command = module._sync_command(commit)
    assert "phase-06b-storage-batch" in command
    assert f"test \"$actual\" = '{commit}'" in command
    assert "git merge --ff-only" in command
    with pytest.raises(ValueError):
        module._sync_command("short")


def test_explicit_harness_environment_is_forwarded_to_remote_launch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _controller_module()
    monkeypatch.setenv(
        "PHASE06B_HARNESS_VENV",
        "/media/volume/jisheng3_volume/memlife/venvs/phase 06b explicit",
    )
    command = module._remote_batch_command("a" * 40)
    assert "PHASE06B_HARNESS_VENV='/media/volume/" in command
    assert "phase 06b explicit'" in command


def test_remote_shell_reuses_retained_environments_without_install_or_broad_kill() -> None:
    text = REMOTE_SHELL.read_text(encoding="utf-8")
    selector_text = HARNESS_SELECTOR.read_text(encoding="utf-8")
    assert "MEMLIFE_AUTHORIZE_PHASE06B_LIVE" in text
    assert 'findmnt -n -o TARGET /dev/sdb' in text
    assert "memlife-harness-phase04" in selector_text
    assert "phase06b_harness.py" in text
    assert 'export PHASE06B_HARNESS_VENV="$HARNESS_VENV"' in text
    assert "hindsight-0.10.1" in text
    assert "openviking-0.4.22" in text
    assert "pip install" not in text
    assert "docker prune" not in text
    assert "pkill" not in text
    assert "killall" not in text
    assert "mkfs" not in text


def test_repository_venv_is_rejected_as_explicit_phase06b_harness(
    tmp_path: Path,
) -> None:
    module = _harness_module()
    repo = tmp_path / "repo"
    data_root = tmp_path / "volume" / "memlife"
    legacy = _fake_venv(repo / ".venv")
    with pytest.raises(module.HarnessSelectionError, match="repository .venv"):
        module.select_approved_harness(
            repo=repo,
            data_root=data_root,
            explicit_venv=legacy,
            prefix_probe=lambda _: legacy,
        )


def test_approved_persistent_phase06b_harness_is_selected(tmp_path: Path) -> None:
    module = _harness_module()
    repo = tmp_path / "repo"
    data_root = tmp_path / "volume" / "memlife"
    approved = _fake_venv(data_root / "venvs" / "memlife-harness-phase04")
    selection = module.select_approved_harness(
        repo=repo,
        data_root=data_root,
        prefix_probe=lambda _: approved,
    )
    assert selection.venv == approved.resolve()
    assert selection.python == approved.resolve() / "bin" / "python"
    assert selection.source == "persistent-default"


def test_explicit_approved_phase06b_harness_takes_precedence(tmp_path: Path) -> None:
    module = _harness_module()
    repo = tmp_path / "repo"
    data_root = tmp_path / "volume" / "memlife"
    _fake_venv(data_root / "venvs" / "memlife-harness-phase04")
    explicit = _fake_venv(data_root / "venvs" / "phase06b-explicit")
    selection = module.select_approved_harness(
        repo=repo,
        data_root=data_root,
        explicit_venv=explicit,
        prefix_probe=lambda _: explicit,
    )
    assert selection.venv == explicit.resolve()
    assert selection.source == "explicit"


def test_missing_approved_phase06b_harness_fails_closed(tmp_path: Path) -> None:
    module = _harness_module()
    with pytest.raises(module.HarnessSelectionError, match="is missing"):
        module.select_approved_harness(
            repo=tmp_path / "repo",
            data_root=tmp_path / "volume" / "memlife",
            prefix_probe=lambda path: path,
        )


def test_remote_launch_selection_never_resolves_repository_venv(
    tmp_path: Path,
) -> None:
    module = _harness_module()
    repo = tmp_path / "repo"
    data_root = tmp_path / "volume" / "memlife"
    legacy = _fake_venv(repo / ".venv")
    approved = _fake_venv(data_root / "venvs" / "memlife-harness-phase04")
    selection = module.select_approved_harness(
        repo=repo,
        data_root=data_root,
        prefix_probe=lambda _: approved,
    )
    assert selection.python != legacy.resolve() / "bin" / "python"
    assert str(selection.python).startswith(str(data_root.resolve()))


def test_sync_evidence_records_distinct_remote_heads_and_tested_commit() -> None:
    module = _controller_module()
    commit = "a" * 40
    assert module._synced_remote_head(
        f"Updating old..new\nremote_branch=phase-06b-storage-batch\nremote_head={commit}\n"
    ) == commit
    with pytest.raises(RuntimeError, match="exactly one"):
        module._synced_remote_head("remote_head=short\n")


def test_remote_result_records_initial_synced_and_tested_commits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _controller_module()
    expected = "a" * 40
    initial = "b" * 40
    payload = {
        "status": "PASS",
        "git_commit_tested": expected,
        "freeze_sha256": (
            "0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b"
        ),
        "downstream_decision_model_calls": 0,
    }
    encoded = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    outputs = iter(
        [
            f"remote_branch=phase-06b-storage-batch\nremote_head={expected}\n",
            f"PHASE06B_RESULT_B64={encoded}\n",
        ]
    )

    def runner(command: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, next(outputs), "")

    monkeypatch.setenv("MEMLIFE_AUTHORIZE_PHASE06B_LIVE", "YES")
    monkeypatch.setattr(module, "LOCAL_RESULT", tmp_path / "result.json")
    monkeypatch.setattr(module, "_download_artifacts", lambda **kwargs: None)
    result = module.run_remote_validation(
        address="192.0.2.1",
        facts={"repo_head": initial, "resolved_volume_mount": "/volume"},
        expected_commit=expected,
        ssh_builder=lambda address, command: [address, command],
        runner=runner,
    )
    assert result["initial_remote_head"] == initial
    assert result["synced_remote_head"] == expected
    assert result["tested_commit"] == expected


def test_frozen_hash_semantics_match_mem0_and_openviking_evidence() -> None:
    mem0 = phase02a_manifest_configuration()
    mem0.update(
        phase="02B",
        vector_store_path_class="<live-volume>/memlife/providers/mem0/phase-02b/qdrant",
        history_path_class="<live-volume>/memlife/providers/mem0/phase-02b/history/history.db",
        model_cache_path_class="<live-volume>/memlife/model_cache/huggingface",
    )
    assert hash_configuration(mem0) == EXPECTED_CONFIGURATION_HASHES["mem0"]
    assert hash_configuration(phase05a_manifest_configuration()) == (
        EXPECTED_CONFIGURATION_HASHES["openviking"]
    )
    hindsight = json.loads(
        (ROOT / "manifests" / "phase-04-hindsight-bringup.json").read_text(
            encoding="utf-8"
        )
    )
    assert hindsight["config_sha256"] == EXPECTED_CONFIGURATION_HASHES["hindsight"]


def test_controller_rejects_sensitive_result_keys() -> None:
    module = _controller_module()
    assert module._contains_sensitive_key({"nested": {"api_key": "x"}})
    assert not module._contains_sensitive_key(
        {"provider_configuration_hash": "a" * 64, "status": "PASS"}
    )
