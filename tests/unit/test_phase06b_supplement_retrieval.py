import subprocess
import base64
from pathlib import Path
from unittest.mock import Mock, call
import pytest
import shutil

# We need to import _download_artifacts from scripts.jetstream.phase06b_supplement
import sys
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "scripts" / "jetstream") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "jetstream"))

from phase06b_supplement import _download_artifacts, ARTIFACT_NAMES, LOCAL_ARTIFACT_ROOT

@pytest.fixture
def clean_artifacts(tmp_path, monkeypatch):
    import phase06b_supplement
    monkeypatch.setattr(phase06b_supplement, "LOCAL_ARTIFACT_ROOT", tmp_path / "artifacts")
    return tmp_path / "artifacts"

def test_download_artifacts_retry_success(clean_artifacts):
    # first artifact SSH transfer times out, second succeeds
    address = "1.2.3.4"
    mount = "/media/volume"
    attempt_id = "20261001T999999Z-000000000000"
    
    def ssh_builder(addr, cmd):
        return ["ssh", addr, cmd]
    
    mock_runner = Mock()
    timeout_exc = subprocess.TimeoutExpired(cmd="ssh", timeout=600)
    success_result = Mock(stdout=base64.b64encode(b"success_bytes").decode("utf-8"))
    
    # We want the first call to timeout, then succeed.
    # Since there are multiple artifacts, we will mock side_effect to raise for the first call of the first artifact,
    # then succeed for the rest.
    def runner_side_effect(*args, **kwargs):
        if runner_side_effect.call_count == 0:
            runner_side_effect.call_count += 1
            raise timeout_exc
        runner_side_effect.call_count += 1
        return success_result
    runner_side_effect.call_count = 0
    
    mock_runner.side_effect = runner_side_effect
    
    local_root = _download_artifacts(
        address=address,
        mount=mount,
        attempt_id=attempt_id,
        ssh_builder=ssh_builder,
        runner=mock_runner
    )
    
    # Check that successful bytes are written exactly once
    assert (local_root / ARTIFACT_NAMES[0]).read_bytes() == b"success_bytes"
    # only artifact-read command is retried
    # The first artifact is requested twice (first timeout, then success)
    assert mock_runner.call_count == len(ARTIFACT_NAMES) + 1

def test_download_artifacts_repeated_failure_bounded(clean_artifacts):
    address = "1.2.3.4"
    mount = "/media/volume"
    attempt_id = "20261001T999999Z-000000000000"
    
    def ssh_builder(addr, cmd):
        return ["ssh", addr, cmd]
    
    mock_runner = Mock()
    timeout_exc = subprocess.TimeoutExpired(cmd="ssh", timeout=600)
    mock_runner.side_effect = timeout_exc
    
    with pytest.raises(RuntimeError, match="failed to download .* after 3 attempts"):
        _download_artifacts(
            address=address,
            mount=mount,
            attempt_id=attempt_id,
            ssh_builder=ssh_builder,
            runner=mock_runner
        )
    
    assert mock_runner.call_count == 3

def test_download_artifacts_invalid_base64_fails_closed(clean_artifacts):
    address = "1.2.3.4"
    mount = "/media/volume"
    attempt_id = "20261001T999999Z-000000000000"
    
    def ssh_builder(addr, cmd):
        return ["ssh", addr, cmd]
    
    mock_runner = Mock(return_value=Mock(stdout="invalid base 64!!!"))
    
    with pytest.raises(RuntimeError, match="failed to download .* after 3 attempts"):
        _download_artifacts(
            address=address,
            mount=mount,
            attempt_id=attempt_id,
            ssh_builder=ssh_builder,
            runner=mock_runner
        )
    
    assert mock_runner.call_count == 3

def test_download_artifacts_no_overwrite(clean_artifacts):
    address = "1.2.3.4"
    mount = "/media/volume"
    attempt_id = "20261001T999999Z-000000000000"
    
    def ssh_builder(addr, cmd):
        return ["ssh", addr, cmd]
    
    mock_runner = Mock(return_value=Mock(stdout=base64.b64encode(b"success").decode("utf-8")))
    
    # Simulate already existing attempt directory
    clean_artifacts.mkdir(parents=True, exist_ok=True)
    (clean_artifacts / attempt_id).mkdir(exist_ok=True)
    
    with pytest.raises(FileExistsError):
        _download_artifacts(
            address=address,
            mount=mount,
            attempt_id=attempt_id,
            ssh_builder=ssh_builder,
            runner=mock_runner
        )

def test_download_artifacts_preserves_earlier_successes(clean_artifacts):
    address = "1.2.3.4"
    mount = "/media/volume"
    attempt_id = "20261001T999999Z-000000000000"
    
    def ssh_builder(addr, cmd):
        return ["ssh", addr, cmd]
    
    mock_runner = Mock()
    success_result = Mock(stdout=base64.b64encode(b"success_bytes").decode("utf-8"))
    timeout_exc = subprocess.TimeoutExpired(cmd="ssh", timeout=600)
    
    # First artifact succeeds, second artifact fails 3 times
    def runner_side_effect(*args, **kwargs):
        if runner_side_effect.call_count == 0:
            runner_side_effect.call_count += 1
            return success_result
        runner_side_effect.call_count += 1
        raise timeout_exc
    runner_side_effect.call_count = 0
    mock_runner.side_effect = runner_side_effect
    
    with pytest.raises(RuntimeError):
        _download_artifacts(
            address=address,
            mount=mount,
            attempt_id=attempt_id,
            ssh_builder=ssh_builder,
            runner=mock_runner
        )
    
    # Check that first artifact is preserved
    local_root = clean_artifacts / attempt_id
    assert (local_root / ARTIFACT_NAMES[0]).is_file()
    assert (local_root / ARTIFACT_NAMES[0]).read_bytes() == b"success_bytes"
    assert not (local_root / ARTIFACT_NAMES[1]).is_file()
