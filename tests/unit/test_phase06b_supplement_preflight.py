import os
import json
import hashlib
import sys
from pathlib import Path
from unittest.mock import patch, Mock
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "scripts" / "jetstream") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "jetstream"))

from phase06b_supplement_remote import validate_pre_experiment_environment
from memlife.runner.phase06b_supplement import ORIGINAL_RAW_SHA256, FREEZE_SHA256, SUPPLEMENT_PLAN_SHA256

@pytest.fixture
def mock_env(monkeypatch, tmp_path):
    monkeypatch.setenv("PHASE06B_EXPECTED_COMMIT", "1234567890abcdef")
    monkeypatch.setenv("MEMLIFE_AUTHORIZE_PHASE06B_SUPPLEMENT_LIVE", "YES")
    monkeypatch.setenv("MEMLIFE_DATA_ROOT", str(tmp_path / "data_root"))
    monkeypatch.setenv("PHASE06B_HARNESS_VENV", str(tmp_path / "venv"))
    monkeypatch.setenv("PHASE06B_OPENVIKING_PYTHON", str(tmp_path / "venv" / "bin" / "python"))
    monkeypatch.setenv("PHASE05_OPENVIKING_CONFIG", str(tmp_path / "config"))
    
    data_root = tmp_path / "data_root"
    raw_path = data_root / "runs" / "phase06b" / "attempts" / "20261001T183940Z-1fc4c4929532" / "freeze-v1-raw-runs.jsonl"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(b"dummy bytes")

def mock_command_side_effect(cmd):
    if "pip" in cmd:
        return "[]"
    return FREEZE_SHA256

@patch("phase06b_supplement_remote._git_commit", return_value="1234567890abcdef")
@patch("phase06b_supplement_remote._command", side_effect=mock_command_side_effect)
@patch("phase06b_supplement_remote.select_approved_harness")
@patch("phase06b_supplement_remote._pip_check")
@patch("phase06b_supplement_remote._distribution_version", return_value="0.4.22")
@patch("phase06b_supplement_remote.hash_configuration")
@patch("phase06b_supplement_remote.EXPECTED_CONFIGURATION_HASHES", {"openviking": "hash"})
@patch("phase06b_supplement_remote._validate_openviking_runtime_config")
@patch("phase06b_supplement_remote.validate_supplement_selection")
@patch("phase06b_supplement_remote.materialize_tracked_jsonl")
@patch("sys.prefix")
def test_validate_preflight(
    mock_sys_prefix,
    mock_materialize,
    mock_val_sel,
    mock_val_config,
    mock_hash_config,
    mock_dist_version,
    mock_pip_check,
    mock_sel_harness,
    mock_command,
    mock_git,
    mock_env,
    tmp_path,
    monkeypatch
):
    mock_hash_config.return_value = "hash"
    
    mock_harness = Mock()
    mock_harness.venv = Path(tmp_path / "venv")
    mock_harness.python = Path(tmp_path / "venv" / "bin" / "python")
    mock_sel_harness.return_value = mock_harness
    
    mock_sys_prefix.__str__.return_value = str(mock_harness.venv)
    mock_sys_prefix.__fspath__.return_value = str(mock_harness.venv)
    monkeypatch.setattr(sys, "prefix", str(mock_harness.venv))

    raw_path = tmp_path / "data_root" / "runs" / "phase06b" / "attempts" / "20261001T183940Z-1fc4c4929532" / "freeze-v1-raw-runs.jsonl"
    
    raw_path.unlink()
    with pytest.raises(RuntimeError, match="original Phase 06B raw artifact is unavailable"):
        validate_pre_experiment_environment()
        
    raw_path.write_bytes(b"wrong bytes")
    with pytest.raises(RuntimeError, match="original Phase 06B raw SHA-256 mismatch"):
        validate_pre_experiment_environment()

@patch("phase06b_supplement_remote._git_commit", return_value="1234567890abcdef")
@patch("phase06b_supplement_remote._command", side_effect=mock_command_side_effect)
@patch("phase06b_supplement_remote.select_approved_harness")
@patch("phase06b_supplement_remote._pip_check")
@patch("phase06b_supplement_remote._distribution_version", return_value="0.4.22")
@patch("phase06b_supplement_remote.hash_configuration")
@patch("phase06b_supplement_remote.EXPECTED_CONFIGURATION_HASHES", {"openviking": "hash"})
@patch("phase06b_supplement_remote._validate_openviking_runtime_config")
@patch("phase06b_supplement_remote.validate_supplement_selection")
@patch("phase06b_supplement_remote.materialize_tracked_jsonl")
@patch("phase06b_supplement_remote.hashlib.sha256")
def test_validate_preflight_correct_sha(
    mock_sha256,
    mock_materialize,
    mock_val_sel,
    mock_val_config,
    mock_hash_config,
    mock_dist_version,
    mock_pip_check,
    mock_sel_harness,
    mock_command,
    mock_git,
    mock_env,
    tmp_path,
    monkeypatch
):
    mock_hash_config.return_value = "hash"
    
    mock_harness = Mock()
    mock_harness.venv = Path(tmp_path / "venv")
    mock_harness.python = Path(tmp_path / "venv" / "bin" / "python")
    mock_sel_harness.return_value = mock_harness
    monkeypatch.setattr(sys, "prefix", str(mock_harness.venv))

    mock_sha256.return_value.hexdigest.return_value = ORIGINAL_RAW_SHA256
    
    mock_val_sel.return_value = ([], Mock(run_ids=["run1", "run2"], runs=[1, 2]))
    
    mock_mat = Mock()
    mock_mat.sha256 = "derived_sha"
    mock_mat.git_blob = b"blob"
    mock_materialize.return_value = mock_mat
    
    evidence = {}
    validate_pre_experiment_environment(evidence)
    
    assert evidence["original_raw_gate"] == "PASS"
    assert evidence["derived_original_validation_source"] == "GIT_BLOB_CANONICAL_CRLF"
