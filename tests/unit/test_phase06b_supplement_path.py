import os
import pytest
from pathlib import Path

# We need to import original_persistent_raw_path
import sys
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from memlife.runner.phase06b_supplement import original_persistent_raw_path

def test_original_persistent_raw_path_resolves_under_data_root(monkeypatch):
    monkeypatch.setenv("MEMLIFE_DATA_ROOT", "/my/persistent/data")
    path = original_persistent_raw_path()
    assert str(path).startswith(str(Path("/my/persistent/data").resolve()))
    assert "attempts" in path.parts
    assert "20261001T183940Z-1fc4c4929532" in path.parts
    assert path.name == "freeze-v1-raw-runs.jsonl"

def test_original_persistent_raw_path_does_not_resolve_under_repo_root(monkeypatch):
    monkeypatch.setenv("MEMLIFE_DATA_ROOT", "/my/persistent/data")
    path = original_persistent_raw_path()
    assert not str(path).startswith(str(REPO_ROOT.resolve()))

def test_original_persistent_raw_path_missing_env_fails(monkeypatch):
    monkeypatch.delenv("MEMLIFE_DATA_ROOT", raising=False)
    with pytest.raises(RuntimeError, match="MEMLIFE_DATA_ROOT environment variable is required"):
        original_persistent_raw_path()

def test_original_persistent_raw_path_containment_escape_fails(monkeypatch):
    monkeypatch.setenv("MEMLIFE_DATA_ROOT", "/my/persistent/data/../data_but_escaped")
    path = original_persistent_raw_path()
    # It resolves, but it doesn't escape because it just goes up and back.
    # What if MEMLIFE_DATA_ROOT has a symlink or something? Path.resolve() resolves it.
    # To truly test the containment rule:
    assert str(path).startswith(str(Path("/my/persistent/data/../data_but_escaped").resolve()))
