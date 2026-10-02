import pytest
from unittest.mock import MagicMock
from scripts.phase07_hindsight_recovery import (
    validate_target, TargetError, verify_sha256, HashMismatchError,
    pg_select_recovery, compute_sha256, EXPECTED_SHA,
    SchemaVerificationError, ReadOnlyTransactionError, verify_schema
)

def test_validate_target():
    validate_target("memlife-freeze-v1-hindsight-S1-r1", "d21e1d56-8224-4f7b-b144-9e7124fe4ef4")
    with pytest.raises(TargetError):
        validate_target("wrong", "id")
    with pytest.raises(TargetError):
        validate_target("memlife-freeze-v1-hindsight-S1-r1", "wrong")

def test_hash_semantics():
    # sha matches normalized candidate text
    assert compute_sha256("test") == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"

def test_verify_sha_mismatch():
    with pytest.raises(HashMismatchError):
        verify_sha256("wrong hash")

def setup_mock_conn():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur

    def side_effect(query, params=None):
        if "SHOW transaction_read_only" in query:
            mock_cur.fetchone.return_value = ("on",)
        elif "COUNT(*) FROM information_schema.tables" in query:
            mock_cur.fetchone.return_value = (1,)
        elif "information_schema.columns" in query:
            # We return extra columns too, to verify subset logic
            mock_cur.fetchall.return_value = [("id",), ("bank_id",), ("text",), ("fact_type",), ("source_memory_ids",), ("document_id",), ("extra_col",)]
        elif "SELECT id, bank_id, text, fact_type, source_memory_ids, document_id" in query:
            mock_cur.fetchall.return_value = [
                ("d21e1d56-8224-4f7b-b144-9e7124fe4ef4", "memlife-freeze-v1-hindsight-S1-r1", " raw text ", "observation", '["bacf3934-5a34-48da-9580-80606d5b9c33"]', "doc1")
            ]

    mock_cur.execute.side_effect = side_effect
    return mock_conn, mock_cur

def test_schema_verification_subset():
    mock_conn, mock_cur = setup_mock_conn()
    verify_schema(mock_cur)

def test_db_recovery_guards():
    mock_conn, mock_cur = setup_mock_conn()
    pg_select_recovery(mock_conn, "memlife-freeze-v1-hindsight-S1-r1", "d21e1d56-8224-4f7b-b144-9e7124fe4ef4")

    calls = mock_cur.execute.call_args_list
    assert any("FROM public.memory_units" in call[0][0] for call in calls)

def test_db_recovery_parent_source_missing():
    mock_conn, mock_cur = setup_mock_conn()
    def side_effect(query, params=None):
        if "SHOW transaction_read_only" in query:
            mock_cur.fetchone.return_value = ("on",)
        elif "COUNT(*) FROM information_schema.tables" in query:
            mock_cur.fetchone.return_value = (1,)
        elif "information_schema.columns" in query:
            mock_cur.fetchall.return_value = [("id",), ("bank_id",), ("text",), ("fact_type",), ("source_memory_ids",), ("document_id",)]
        elif "SELECT id, bank_id, text, fact_type, source_memory_ids, document_id" in query:
            mock_cur.fetchall.return_value = [
                ("d21e1d56-8224-4f7b-b144-9e7124fe4ef4", "memlife-freeze-v1-hindsight-S1-r1", " raw text ", "observation", '["wrong-parent"]', "doc1")
            ]
    mock_cur.execute.side_effect = side_effect

    with pytest.raises(RuntimeError, match="Expected parent source"):
        pg_select_recovery(mock_conn, "memlife-freeze-v1-hindsight-S1-r1", "d21e1d56-8224-4f7b-b144-9e7124fe4ef4")

def test_db_recovery_not_read_only():
    mock_conn, mock_cur = setup_mock_conn()
    def side_effect(query, params=None):
        if "SHOW transaction_read_only" in query:
            mock_cur.fetchone.return_value = ("off",)
    mock_cur.execute.side_effect = side_effect
    with pytest.raises(ReadOnlyTransactionError):
        pg_select_recovery(mock_conn, "memlife-freeze-v1-hindsight-S1-r1", "d21e1d56-8224-4f7b-b144-9e7124fe4ef4")

def test_http_disabled():
    with pytest.raises(ImportError):
        from scripts.phase07_hindsight_recovery import http_get_recovery
