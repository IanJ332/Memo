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
*   **r2 Target:** 
    *   Namespace: `memlife-freeze-v1-hindsight-S1-r2`
    *   Provider Memory ID: `5adc67dd-1658-4ddf-a5e7-7b40e00d84a7`
*   **r3 Target:** 
    *   Namespace: `memlife-freeze-v1-hindsight-S1-r3`
    *   Provider Memory ID: `ea22a6bc-15be-4639-8060-c9eae4fcc5e5`

**Expected SHA-256 (all three targets):** `f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6`

### 1.2 Hash Semantics

Phase 06B exact hashing computation was isolated in `src/memlife/models/authority.py:content_sha256`:
```python
hashlib.sha256(content.encode("utf-8")).hexdigest()
```
The text is normalized exactly by `.strip()` before hashing, without any other JSON normalization or serialization.

### 1.3 Service Start Safety Conclusion

*   **Classification:** `HTTP_GET_SAFETY_UNPROVEN`
*   **Evidence:** The self-hosted Hindsight API source code is not available locally (`client_package: not installed; urllib.request REST transport`). We cannot guarantee that starting the service process does not trigger schema migrations, initializations, or asynchronous `POST /consolidate` background metadata updates. Consequently, any live startup without inspection carries a mutation risk.

### 1.4 Database Contract

*   **Storage Path:** `<MEMLIFE_DATA_ROOT>/providers/hindsight/pg0`
*   **Database URL:** `pg0://memlife-phase04` (persistent volume `/dev/sdb`)
*   **Schema:** Table `memories`.
    *   **ID Column:** `id`
    *   **Namespace Column:** `bank_id`
    *   **Text Column:** `text`
    *   **Fact Type Column:** `type`
    *   **Lineage Column:** `source_memory_ids`

### 1.5 Read-Only Guards

*   **HTTP Mode:** Strictly restricted to exact path `GET /v1/default/banks/{namespace}/memories/{memory_id}`.
*   **Database Mode:** Strictly restricted to parameterized `SELECT text, type, document_id, source_memory_ids FROM memories WHERE id = %s AND bank_id = %s;`.
*   **Blocked Mechanisms:** Semantic recall, writes, updates, deletions, and any `POST /consolidate` operations are completely forbidden and isolated from the harness.

### 1.6 Output Schema

```json
{
  "namespace": "...",
  "provider_memory_id": "...",
  "recovery_method": "EXACT_ID_HTTP_GET | EXACT_ID_DATABASE_SELECT",
  "fact_type": "...",
  "exact_text": "...",
  "exact_text_utf8_sha256": "...",
  "expected_sha256": "...",
  "sha_match": true,
  "parent_source_ids": ["..."],
  "document_id": "...",
  "original_attempt_id": "20261001T183940Z-1fc4c4929532",
  "recovered_at": "...",
  "read_only_assertion": true
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
7.  Perform exact-ID read-only database recovery using the local harness.
8.  Write recovery result to a NEW Phase 07 artifact path.
9.  Download the artifact locally.
10. Cleanup the temporary floating IP.
11. **SHELVE** Jetstream instance.
12. Independently verify Jetstream is **SHELVED**.

### 2.1 Stop Conditions
*   Mismatching hash between recovered text and expected `f0c061e0...`.
*   Missing database row / target ID.
*   Inability to confirm read-only connection.
If any condition fails, execution must strictly STOP, shelve, and fail closed without attempting any replay or LLM text generation.
