"""Dedicated supplement controller and attempt-isolation gates."""

from __future__ import annotations

import base64
import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CONTROLLER = ROOT / "scripts" / "jetstream" / "phase06b_supplement.py"
SHELL = ROOT / "scripts" / "jetstream" / "phase06b_supplement_remote.sh"
ATTEMPT = "20261001T230000Z-123456abcdef"


def _module():
    scripts = ROOT / "scripts" / "jetstream"
    import sys

    sys.path.insert(0, str(scripts))
    try:
        spec = importlib.util.spec_from_file_location("phase06b_supplement_controller", CONTROLLER)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(scripts))


def test_supplement_authorization_is_distinct_and_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    monkeypatch.delenv(module.LIVE_AUTH_ENV, raising=False)
    with pytest.raises(RuntimeError, match="disabled"):
        module.require_live_authorization()
    monkeypatch.setenv(module.LIVE_AUTH_ENV, "YES")
    module.require_live_authorization()


def test_remote_command_has_no_run_id_injection_surface() -> None:
    module = _module()
    command = module._remote_supplement_command("a" * 40, ATTEMPT)
    assert "phase06b_supplement_remote.sh" in command
    assert "PHASE06B_SUPPLEMENT_ATTEMPT_ID" in command
    assert "--run-id" not in command
    assert "eligible_run_ids" not in command


def _runner(module: object, marker: bytes):
    def run(command: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        joined = " ".join(str(part) for part in command)
        name = next(name for name in module.ARTIFACT_NAMES if name in joined)
        encoded = base64.b64encode(marker + b":" + name.encode()).decode()
        return subprocess.CompletedProcess(command, 0, encoded, "")

    return run


def test_local_supplement_attempt_collision_fails_without_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _module()
    root = tmp_path / "supplements" / "attempts"
    collision = root / ATTEMPT
    collision.mkdir(parents=True)
    evidence = collision / "supplement-execution-ledger.json"
    evidence.write_bytes(b"preserve")
    monkeypatch.setattr(module, "LOCAL_ARTIFACT_ROOT", root)
    with pytest.raises(FileExistsError):
        module._download_artifacts(
            address="192.0.2.1",
            mount="/volume",
            attempt_id=ATTEMPT,
            ssh_builder=lambda address, command: [address, command],
            runner=_runner(module, b"replacement"),
        )
    assert evidence.read_bytes() == b"preserve"


def test_remote_supplement_path_is_exclusive_and_never_installs_or_broadly_kills() -> None:
    text = SHELL.read_text(encoding="utf-8")
    assert 'RUN_PARENT="$MEMLIFE_DATA_ROOT/runs/phase06b/supplements/attempts"' in text
    assert 'mkdir "$RUN_ROOT"' in text
    assert 'test "$PHASE06B_SUPPLEMENT_ATTEMPT_ID" != 20261001T183940Z-1fc4c4929532' in text
    assert "phase06b_supplement_remote.py" in text
    assert "pip install" not in text
    assert "pkill" not in text
    assert "killall" not in text
    assert "mkfs" not in text
