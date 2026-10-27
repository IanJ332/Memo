"""Custody rejection controls for retrospective native evidence analysis."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/research/next_lp_native01.py"
spec = importlib.util.spec_from_file_location("next_lp_native01", SCRIPT)
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


def fixture(tmp_path, monkeypatch, rows=None):
    data = b'{"value":1}'
    (tmp_path / "record.json").write_bytes(data)
    row = dict(path="record.json", bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    raw = json.dumps(dict(files=[row] if rows is None else rows)).encode()
    (tmp_path / "inventory.json").write_bytes(raw)
    monkeypatch.setattr(study, "INVENTORY_SHA", hashlib.sha256(raw).hexdigest())
    return study.RetainedEvidence(tmp_path)


def test_original_inventory_identity_required(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch)
    (tmp_path / "inventory.json").write_bytes(b'{"files":[]}')
    with pytest.raises(ValueError, match="ORIGINAL_INVENTORY_DRIFT"):
        study.RetainedEvidence(tmp_path)


def test_original_member_identity_required(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch)
    (tmp_path / "record.json").write_bytes(b'{"value":2}')
    with pytest.raises(ValueError, match="ORIGINAL_MEMBER_DRIFT"):
        study.RetainedEvidence(tmp_path)


def test_member_rechecked_at_use(tmp_path, monkeypatch):
    evidence = fixture(tmp_path, monkeypatch)
    (tmp_path / "record.json").write_bytes(b'{"value":2}')
    with pytest.raises(ValueError, match="EVIDENCE_CHANGED_DURING_ANALYSIS"):
        evidence.read("record.json")


def test_unindexed_member_rejected(tmp_path, monkeypatch):
    evidence = fixture(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="UNINDEXED_EVIDENCE"):
        evidence.read("not-in-original-inventory.json")


def test_escaping_inventory_path_rejected(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match="EVIDENCE_PATH_ESCAPE"):
        fixture(tmp_path, monkeypatch, [dict(path="../outside.json", bytes=0, sha256="0" * 64)])


def test_duplicate_member_rejected(tmp_path, monkeypatch):
    data = b'{"value":1}'
    row = dict(path="record.json", bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    with pytest.raises(ValueError, match="DUPLICATE_INVENTORY_PATH"):
        fixture(tmp_path, monkeypatch, [row, row])
