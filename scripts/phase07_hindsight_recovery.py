import hashlib
import json
import sqlite3
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional, Literal

EXPECTED_SHA = "f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6"

ALLOWED_TARGETS = {
    "memlife-freeze-v1-hindsight-S1-r1": "d21e1d56-8224-4f7b-b144-9e7124fe4ef4",
    "memlife-freeze-v1-hindsight-S1-r2": "5adc67dd-1658-4ddf-a5e7-7b40e00d84a7",
    "memlife-freeze-v1-hindsight-S1-r3": "ea22a6bc-15be-4639-8060-c9eae4fcc5e5",
}

@dataclass
class RecoveryResult:
    namespace: str
    provider_memory_id: str
    recovery_method: Literal["EXACT_ID_HTTP_GET", "EXACT_ID_DATABASE_SELECT"]
    fact_type: str
    exact_text: str
    exact_text_utf8_sha256: str
    expected_sha256: str
    sha_match: bool
    parent_source_ids: list[str]
    document_id: str
    original_attempt_id: str
    recovered_at: str
    read_only_assertion: bool

class ReadOnlyError(Exception):
    pass

class TargetError(Exception):
    pass

class HashMismatchError(Exception):
    pass

def validate_target(namespace: str, memory_id: str) -> None:
    if namespace not in ALLOWED_TARGETS:
        raise TargetError(f"Namespace {namespace} not in allowlist.")
    if ALLOWED_TARGETS[namespace] != memory_id:
        raise TargetError(f"Memory ID {memory_id} does not match allowed ID for namespace.")

def compute_sha256(text: str) -> str:
    # Phase 06B exact hashing semantics: hashlib.sha256(content.encode("utf-8")).hexdigest()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def verify_sha256(text: str) -> None:
    sha = compute_sha256(text)
    if sha != EXPECTED_SHA:
        raise HashMismatchError(f"Hash mismatch. Expected {EXPECTED_SHA}, got {sha}")

def http_get_recovery(base_url: str, namespace: str, memory_id: str) -> dict:
    validate_target(namespace, memory_id)
    path = f"/v1/default/banks/{namespace}/memories/{memory_id}"
    url = f"{base_url}{path}"
    
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP Error {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"URL Error: {e.reason}")

def pg_select_recovery(conn, namespace: str, memory_id: str) -> dict:
    validate_target(namespace, memory_id)
    # Using parameterized SELECT. The connection should be read-only if supported by the driver.
    # We will simulate pg8000/psycopg2 with generic DB-API
    cur = conn.cursor()
    # Read-only guards: Only execute this precise SELECT
    cur.execute(
        "SELECT text, type, document_id, source_memory_ids FROM memories WHERE id = %s AND bank_id = %s;",
        (memory_id, namespace)
    )
    row = cur.fetchone()
    if not row:
        raise RuntimeError("Row not found in database.")
    
    text, fact_type, doc_id, source_ids = row
    if isinstance(source_ids, str):
        try:
            source_ids = json.loads(source_ids)
        except:
            source_ids = []
            
    return {
        "text": text,
        "type": fact_type,
        "document_id": doc_id,
        "source_memory_ids": source_ids or []
    }

def run_recovery_http(base_url: str, namespace: str, memory_id: str) -> RecoveryResult:
    import datetime
    data = http_get_recovery(base_url, namespace, memory_id)
    text = str(data.get("text") or "").strip()
    verify_sha256(text)
    return RecoveryResult(
        namespace=namespace,
        provider_memory_id=memory_id,
        recovery_method="EXACT_ID_HTTP_GET",
        fact_type=str(data.get("fact_type") or data.get("type") or "unknown"),
        exact_text=text,
        exact_text_utf8_sha256=EXPECTED_SHA,
        expected_sha256=EXPECTED_SHA,
        sha_match=True,
        parent_source_ids=data.get("source_memory_ids", []),
        document_id=str(data.get("document_id") or ""),
        original_attempt_id="20261001T183940Z-1fc4c4929532",
        recovered_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        read_only_assertion=True
    )

def run_recovery_db(conn, namespace: str, memory_id: str) -> RecoveryResult:
    import datetime
    data = pg_select_recovery(conn, namespace, memory_id)
    text = str(data.get("text") or "").strip()
    verify_sha256(text)
    return RecoveryResult(
        namespace=namespace,
        provider_memory_id=memory_id,
        recovery_method="EXACT_ID_DATABASE_SELECT",
        fact_type=str(data.get("type") or "unknown"),
        exact_text=text,
        exact_text_utf8_sha256=EXPECTED_SHA,
        expected_sha256=EXPECTED_SHA,
        sha_match=True,
        parent_source_ids=data.get("source_memory_ids", []),
        document_id=str(data.get("document_id") or ""),
        original_attempt_id="20261001T183940Z-1fc4c4929532",
        recovered_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        read_only_assertion=True
    )
