"""Tests for metadata-only Phase 06B provenance repair."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "repair_phase06b_provenance.py"
ATTEMPT_ID = "20261001T183940Z-1fc4c4929532"


def _module():
    spec = importlib.util.spec_from_file_location("phase06b_provenance_repair", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_repair_adds_only_attempt_id_and_preserves_source_bytes(tmp_path: Path) -> None:
    module = _module()
    source = tmp_path / "source.jsonl"
    derived = tmp_path / "derived.jsonl"
    source_bytes = b'{"run_id":"one","scientific":{"value":7}}\n'
    source.write_bytes(source_bytes)

    count, source_hash = module.write_repaired_rows(source, derived, ATTEMPT_ID)

    assert count == 1
    assert source.read_bytes() == source_bytes
    assert module.sha256_file(source) == source_hash
    row = json.loads(derived.read_text(encoding="utf-8"))
    assert row.pop("attempt_id") == ATTEMPT_ID
    assert row == {"run_id": "one", "scientific": {"value": 7}}


def test_repair_refuses_to_overwrite_source_attempt_metadata(tmp_path: Path) -> None:
    module = _module()
    source = tmp_path / "source.jsonl"
    derived = tmp_path / "derived.jsonl"
    source.write_text(json.dumps({"attempt_id": "other"}) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="already contain"):
        module.write_repaired_rows(source, derived, ATTEMPT_ID)
    assert not derived.exists()
