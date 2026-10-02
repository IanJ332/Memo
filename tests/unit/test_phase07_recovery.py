import pytest
from unittest.mock import patch, MagicMock
from scripts.phase07_hindsight_recovery import (
    validate_target, TargetError, verify_sha256, HashMismatchError,
    http_get_recovery, pg_select_recovery, compute_sha256, EXPECTED_SHA
)

def test_validate_target():
    validate_target("memlife-freeze-v1-hindsight-S1-r1", "d21e1d56-8224-4f7b-b144-9e7124fe4ef4")
    with pytest.raises(TargetError):
        validate_target("wrong", "id")
    with pytest.raises(TargetError):
        validate_target("memlife-freeze-v1-hindsight-S1-r1", "wrong")

def test_hash_semantics():
    # If there is some exact text that gives expected sha, it works.
    # The expected sha is f0c061...
    # We just ensure the function uses exactly utf-8 encoding.
    assert compute_sha256("test") == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"

def test_verify_sha_mismatch():
    with pytest.raises(HashMismatchError):
        verify_sha256("wrong text")

def test_http_recovery_guards():
    # It constructs only exact path and uses GET
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"text": "dummy"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        http_get_recovery("http://test", "memlife-freeze-v1-hindsight-S1-r1", "d21e1d56-8224-4f7b-b144-9e7124fe4ef4")
        
        req = mock_urlopen.call_args[0][0]
        assert req.method == "GET"
        assert req.full_url == "http://test/v1/default/banks/memlife-freeze-v1-hindsight-S1-r1/memories/d21e1d56-8224-4f7b-b144-9e7124fe4ef4"

def test_db_recovery_guards():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_cur.fetchone.return_value = ("test text", "observation", "doc1", "[]")
    
    pg_select_recovery(mock_conn, "memlife-freeze-v1-hindsight-S1-r1", "d21e1d56-8224-4f7b-b144-9e7124fe4ef4")
    
    query = mock_cur.execute.call_args[0][0]
    assert "SELECT text, type, document_id, source_memory_ids FROM memories" in query
    assert "INSERT" not in query
    assert "UPDATE" not in query
    assert "DELETE" not in query

