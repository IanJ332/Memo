"""Phase 06B managed-lifecycle and remote fail-closed preparation tests."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from memlife.adapters.mem0 import phase02a_manifest_configuration
from memlife.adapters.openviking import phase05a_manifest_configuration
from memlife.runner.manifest import hash_configuration
from memlife.runner.storage_batch import EXPECTED_CONFIGURATION_HASHES

ROOT = Path(__file__).resolve().parents[2]
CONTROLLER = ROOT / "scripts" / "jetstream" / "phase06b.py"
REMOTE_SHELL = ROOT / "scripts" / "jetstream" / "phase06b_remote.sh"


def _controller_module():
    spec = importlib.util.spec_from_file_location("phase06b_controller", CONTROLLER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def test_remote_shell_reuses_retained_environments_without_install_or_broad_kill() -> None:
    text = REMOTE_SHELL.read_text(encoding="utf-8")
    assert "MEMLIFE_AUTHORIZE_PHASE06B_LIVE" in text
    assert 'findmnt -n -o TARGET /dev/sdb' in text
    assert "memlife-harness-phase04" in text
    assert "hindsight-0.10.1" in text
    assert "openviking-0.4.22" in text
    assert "pip install" not in text
    assert "docker prune" not in text
    assert "pkill" not in text
    assert "killall" not in text
    assert "mkfs" not in text


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
