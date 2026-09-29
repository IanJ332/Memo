from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
PYTHON_SCRIPT = ROOT / "scripts" / "jetstream" / "phase05_openviking.py"
REMOTE_SCRIPT = ROOT / "scripts" / "jetstream" / "phase05_openviking_remote.sh"


def _module():
    spec = importlib.util.spec_from_file_location("phase05_openviking", PYTHON_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_future_execution_is_disabled_without_separate_authorization(monkeypatch) -> None:
    monkeypatch.delenv("MEMLIFE_AUTHORIZE_PHASE05_LIVE", raising=False)
    with pytest.raises(RuntimeError, match="disabled"):
        _module().require_live_authorization()


def test_remote_script_has_isolation_and_resource_guards() -> None:
    text = REMOTE_SCRIPT.read_text(encoding="utf-8")
    assert "findmnt -n -o TARGET /dev/sdb" in text
    assert "openviking-0.4.22" in text
    assert "http://127.0.0.1:1933" in text
    assert "openviking==0.4.22" in text
    assert "memlife-harness-phase04" in text
    assert "nvidia-" in text and "cuda-" in text
    assert '.local/phase05_openviking.env' in text
    assert '400|600' in text
    assert "/media/volume/sdb" not in text
    assert "sleep 30" not in text


def test_future_validator_runs_canonical_and_provenance_once() -> None:
    text = PYTHON_SCRIPT.read_text(encoding="utf-8")
    assert "ProvenanceTraceRunner(adapter).run_scenario" in text
    assert "LifecycleRunner(adapter).run_suite" not in text


def test_managed_controller_owns_fip_cleanup_and_shelving() -> None:
    controller = (ROOT / "scripts" / "jetstream" / "jetstreamctl.py").read_text(
        encoding="utf-8"
    )
    assert "run_phase05" in controller
    assert "cleanup_owned_floating_ip" in controller
    assert 'server_action(credentials, "shelve")' in controller
