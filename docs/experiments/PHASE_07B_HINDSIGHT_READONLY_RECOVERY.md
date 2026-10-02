# Phase 07B — Hindsight Read-Only Recovery

> **Status:** HARNESS_PREPARED
> **Governing Principle:** *Retrieved != Authoritative*
> **Live Execution:** `NOT AUTHORIZED` (LOCAL PREP ONLY)
> **Jetstream Status:** `SHELVED`

---

## 1. Local Harness Prep

This document defines the strict exact-ID recovery protocol necessary to retrieve the exact raw text bytes corresponding to the derived memory observation generated during Phase 06B Hindsight S1. No live recovery is performed here. 

### 1.1 Recovery Targets

The recovery targets exactly match the missing non-authoritative candidate content identified in `PHASE_07B_RQ3_CONTEXT_CANDIDATES.md`.

*   **r1 Target:** 
    *   Namespace: `memlife-freeze-v1-hindsight-S1-r1`
    *   Provider Memory ID: `d21e1d56-8224-4f7b-b144-9e7124fe4ef4`
    *   Expected parent source: `bacf3934-5a34-48da-9580-80606d5b9c33`
*   **r2 Target:** 
    *   Namespace: `memlife-freeze-v1-hindsight-S1-r2`
    *   Provider Memory ID: `5adc67dd-1658-4ddf-a5e7-7b40e00d84a7`
    *   Expected parent source: `b2fa69b9-d719-4531-86e9-06c69fc739bb`
*   **r3 Target:** 
    *   Namespace: `memlife-freeze-v1-hindsight-S1-r3`
    *   Provider Memory ID: `ea22a6bc-15be-4639-8060-c9eae4fcc5e5`
    *   Expected parent source: `dfa63b99-ac6d-467b-b25e-bbc104545a2d`

**Expected SHA-256 (all three targets):** `f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6`

### 1.2 Hash Semantics

Phase 06B uses `content_sha256(record.content)` where:
```python
content_sha256(content) = hashlib.sha256(content.encode("utf-8")).hexdigest()
```

For Hindsight, `MemoryRecord.content` is built from `str(native["text"]).strip()`. Therefore future recovery must preserve `raw_db_text` and separately compute:
```python
normalized_candidate_text = raw_db_text.strip()
phase06b_exact_content_sha256 = hashlib.sha256(normalized_candidate_text.encode("utf-8")).hexdigest()
```
The expected SHA `f0c061e0...` identifies the normalized `MemoryRecord.content` used by Phase 06B, not the raw database bytes.

### 1.3 Service Start Safety Conclusion

*   **HTTP Recovery:** `DISABLED_NOT_AUTHORIZED`
*   **Reason:** Hindsight v0.10.1 API startup defaults to running database migrations and initializes MemoryEngine. Live HTTP mode must not be invoked to prevent mutation. Only the Direct PG0 database mode is allowed.

### 1.4 Database Contract

*   **Storage Path:** `<MEMLIFE_DATA_ROOT>/providers/hindsight/pg0`
*   **Database URL:** `pg0://memlife-phase04` (persistent volume `/dev/sdb`)
*   **Table:** `memory_units`
*   **Columns:**
    *   `id`
    *   `bank_id`
    *   `text`
    *   `fact_type`
    *   `source_memory_ids`
    *   `document_id`

### 1.5 Read-Only Guards

*   **Live recovery:** `DIRECT_PG0_DATABASE_ONLY`
*   **Database Mode:** Strictly restricted to an explicit `READ ONLY` transaction (`SHOW transaction_read_only` must be `on`). Followed by schema verification queries, and then a parameterized `SELECT id, bank_id, text, fact_type, source_memory_ids, document_id FROM public.memory_units WHERE id = %s::uuid AND bank_id = %s AND fact_type = 'observation';`.
*   **Blocked Mechanisms:** HTTP recovery, semantic recall, writes, updates, deletions, and any `POST /consolidate` operations are completely forbidden and isolated from the harness.

### 1.6 Attempt-Scoped PG0 Copy & Isolation

*   **Original Evidence Immutable:** `YES`. Starting PostgreSQL modifies physical evidence files (WAL/control/log) even in read-only mode. The future live recovery MUST NOT start PostgreSQL directly against the original Phase 06B Hindsight data directory.
*   **Copy Process:** The stopped `pg0` data directory must be copied preserving filesystem metadata to an attempt-scoped root (e.g. `runs/phase07-hindsight-recovery/<attempt_id>/pg0-copy/`). The source is `<MEMLIFE_DATA_ROOT>/providers/hindsight/pg0`.
*   **Integrity Hash:** A deterministic file tree hash (`SOURCE_TREE_SHA_BEFORE`) is computed on the source before the copy. After recovery, `SOURCE_TREE_SHA_AFTER` is computed on the source and must match exactly.
*   **Isolation:** The pg0 HOME/metadata must also be isolated (e.g. `runs/phase07-hindsight-recovery/<attempt_id>/pg0-home/`) to avoid mutating `~/.pg0` or the original symlink.

### 1.7 Output Schema

```json
{
  "namespace": "...",
  "provider_memory_id": "...",
  "recovery_method": "EXACT_ID_DATABASE_SELECT",
  "fact_type": "observation",

  "raw_db_text": "...",
  "normalized_candidate_text": "...",

  "phase06b_exact_content_sha256": "...",
  "expected_sha256": "...",
  "sha_match": true,

  "source_memory_ids": ["..."],
  "expected_parent_source_id": "...",
  "expected_parent_present": true,

  "document_id": "...",
  "original_attempt_id": "20261001T183940Z-1fc4c4929532",

  "database_transaction_read_only": true,
  "recovered_at": "...",

  "status": "RECOVERED_EXACT"
}
```

---

## 2. Future Live Read-Only Recovery

> Do NOT execute this process now.

1.  **SHELVED** verification.
2.  **UNSHELVE** and spin up a temporary floating IP.
3.  Establish an **SSH** connection to Jetstream.
4.  Verify published tested commit checkout on Jetstream.
5.  Verify `/dev/sdb` persistent volume is mounted and resolved.
6.  Verify persistent Hindsight `pg0` evidence exists.
7.  Perform exact-ID read-only database recovery using the local harness. Use Hindsight's pg0 resolver to start the embedded PostgreSQL engine ONLY after local source inspection proves that this path starts pg0/PostgreSQL without invoking Hindsight migrations or MemoryEngine initialization.
8.  Write recovery result to a NEW Phase 07 artifact path.
9.  Download the artifact locally.
10. Cleanup the temporary floating IP.
11. **SHELVE** Jetstream instance.
12. Independently verify Jetstream is **SHELVED**.

### 2.1 Stop Conditions
*   Mismatching hash between recovered text and expected `f0c061e0...`.
*   Missing database row, multiple rows returned, wrong `fact_type`, or missing expected parent source ID.
*   Inability to confirm read-only connection or verify exact schema.
If any condition fails, execution must strictly STOP, shelve, and fail closed without attempting any replay or LLM text generation.
