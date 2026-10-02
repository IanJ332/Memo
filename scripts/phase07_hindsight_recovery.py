import hashlib
import json
from dataclasses import dataclass
from typing import Literal, Optional, List

EXPECTED_SHA = "f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6"

ALLOWED_TARGETS = {
    "memlife-freeze-v1-hindsight-S1-r1": {
        "id": "d21e1d56-8224-4f7b-b144-9e7124fe4ef4",
        "parent_source": "bacf3934-5a34-48da-9580-80606d5b9c33"
    },
    "memlife-freeze-v1-hindsight-S1-r2": {
        "id": "5adc67dd-1658-4ddf-a5e7-7b40e00d84a7",
        "parent_source": "b2fa69b9-d719-4531-86e9-06c69fc739bb"
    },
    "memlife-freeze-v1-hindsight-S1-r3": {
        "id": "ea22a6bc-15be-4639-8060-c9eae4fcc5e5",
        "parent_source": "dfa63b99-ac6d-467b-b25e-bbc104545a2d"
    },
}

@dataclass
class RecoveryResult:
    namespace: str
    provider_memory_id: str
    recovery_method: Literal["EXACT_ID_DATABASE_SELECT"]
    fact_type: str
    raw_db_text: str
    normalized_candidate_text: str
    phase06b_exact_content_sha256: str
    expected_sha256: str
    sha_match: bool
    source_memory_ids: list[str]
    expected_parent_source_id: str
    expected_parent_present: bool
    document_id: str
    original_attempt_id: str
    database_transaction_read_only: bool
    recovered_at: str
    status: Literal["RECOVERED_EXACT"]

class TargetError(Exception):
    pass

class HashMismatchError(Exception):
    pass

class SchemaVerificationError(Exception):
    pass

class ReadOnlyTransactionError(Exception):
    pass

def validate_target(namespace: str, memory_id: str) -> dict:
    if namespace not in ALLOWED_TARGETS:
        raise TargetError(f"Namespace {namespace} not in allowlist.")
    target = ALLOWED_TARGETS[namespace]
    if target["id"] != memory_id:
        raise TargetError(f"Memory ID {memory_id} does not match allowed ID for namespace.")
    return target

def compute_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def verify_sha256(sha: str) -> None:
    if sha != EXPECTED_SHA:
        raise HashMismatchError(f"Hash mismatch. Expected {EXPECTED_SHA}, got {sha}")

def verify_schema(cur) -> None:
    # Verify memory_units table exists in public schema (Hindsight v0.10.1 default)
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'memory_units';"
    )
    count = cur.fetchone()[0]
    if count != 1:
        raise SchemaVerificationError("memory_units table not found in public schema.")

    # Require subset logic: exact 6 required columns must be present, extra columns are okay
    cur.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'memory_units';"
    )
    columns = {row[0] for row in cur.fetchall()}
    required_columns = {"id", "bank_id", "text", "fact_type", "source_memory_ids", "document_id"}
    if not required_columns.issubset(columns):
        missing = required_columns - columns
        raise SchemaVerificationError(f"Missing required columns in memory_units: {missing}")

def verify_read_only(cur) -> None:
    cur.execute("SHOW transaction_read_only;")
    val = cur.fetchone()[0]
    if str(val).lower() != "on":
        raise ReadOnlyTransactionError("Transaction is not read-only.")

def pg_select_recovery(conn, namespace: str, memory_id: str) -> dict:
    target_info = validate_target(namespace, memory_id)

    cur = conn.cursor()
    verify_read_only(cur)
    verify_schema(cur)

    cur.execute(
        "SELECT id, bank_id, text, fact_type, source_memory_ids, document_id FROM public.memory_units WHERE id = %s::uuid AND bank_id = %s AND fact_type = 'observation';",
        (memory_id, namespace)
    )
    rows = cur.fetchall()
    if len(rows) == 0:
        raise RuntimeError("Row not found in database or wrong fact_type.")
    if len(rows) > 1:
        raise RuntimeError("Multiple rows found in database for exact ID.")

    row = rows[0]
    _id, _bank_id, text, fact_type, source_ids, doc_id = row

    if isinstance(source_ids, str):
        try:
            source_ids = json.loads(source_ids)
        except:
            source_ids = []

    if target_info["parent_source"] not in source_ids:
        raise RuntimeError(f"Expected parent source {target_info['parent_source']} not in source_memory_ids.")

    return {
        "text": text,
        "fact_type": fact_type,
        "document_id": doc_id,
        "source_memory_ids": source_ids or [],
        "expected_parent_source_id": target_info["parent_source"]
    }

def run_recovery_db(conn, namespace: str, memory_id: str) -> RecoveryResult:
    import datetime
    data = pg_select_recovery(conn, namespace, memory_id)

    raw_db_text = str(data.get("text") or "")
    normalized_candidate_text = raw_db_text.strip()

    sha = compute_sha256(normalized_candidate_text)
    verify_sha256(sha)

    return RecoveryResult(
        namespace=namespace,
        provider_memory_id=memory_id,
        recovery_method="EXACT_ID_DATABASE_SELECT",
        fact_type=data["fact_type"],
        raw_db_text=raw_db_text,
        normalized_candidate_text=normalized_candidate_text,
        phase06b_exact_content_sha256=sha,
        expected_sha256=EXPECTED_SHA,
        sha_match=True,
        source_memory_ids=data["source_memory_ids"],
        expected_parent_source_id=data["expected_parent_source_id"],
        expected_parent_present=True,
        document_id=str(data["document_id"] or ""),
        original_attempt_id="20261001T183940Z-1fc4c4929532",
        database_transaction_read_only=True,
        recovered_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status="RECOVERED_EXACT"
    )
