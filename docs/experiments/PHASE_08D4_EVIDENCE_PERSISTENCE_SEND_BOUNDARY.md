# Phase 08D-4 — Candidate-Evidence Persistence and Internal-Send Boundary Verification

**Status:** local engineering implementation and static audit complete; zero empirical executions.

**Base / branch:** `7d3593bb319b2aa945c5ff20dae4e725a7201e9c` / `phase-08d4-evidence-persistence`.  
**Execution target:** local macOS worktree (`/Users/ian/.codex/worktrees/9e5b/Memo`).  
**Jetstream:** no action; remains SHELVED.  
**Provider / hosted model / local embedding / downstream / RQ3 calls:** `0 / 0 / 0 / 0 / 0`.  
**Primary checkout unchanged:** `/Users/ian/Desktop/Memo` clean on `main` at base.

---

## 1. Executive Summary & Verdicts

| Area | Status | Evidence-Preserving Result and Boundary |
|---|---|---|
| **D1 exact HTTP capture** | IMPLEMENTED | Verified from Phase 08D-3. Captures raw wire request/response bytes before JSON decoding, headers (redacting auth/cookies), status codes, and latency with deterministic SHA-256 manifests. |
| **D2 candidate persistence** | IMPLEMENTED & VERIFIED | `CandidateArtifactSink` persists every candidate position to `AttemptArtifactStore` with private exclusive writes (`0o600`), deterministic formatting, decoded-field raw bytes, normalized bytes, native IDs, surfaces, parent IDs, and provenance basis. Linked to D1 HTTP response artifact with explicit transformation chains. Ordering and duplicate native IDs are strictly preserved. Validated via `verify_candidate_integrity`. Offline tests passing 32/32. |
| **D3 lifecycle completion** | PARTIAL | Paginated polling and terminal receipt validation implemented in Phase 08D-3. Quiescence listing cannot prove global worker quiescence; background and overall coverage remain explicitly `UNKNOWN`. |
| **D4 internal send boundary** | FEASIBLE_WITH_VERIFIED_BOUNDARY | Source audit of pinned Hindsight commit `f8950b0c07d9e34c76493dba802bb309f0ce60fd` establishes that all text-model sends pass through `OpenAICompatibleLLM._client.chat.completions.create`. `LLMProvider.call` is insufficient because startup verification bypasses it and native retries occur beneath it. Admission upper bounds and missing-usage coercion remain unresolved blockers for live enforcement. |
| **D5 attempt/evidence gates** | PARTIAL | Offline gate primitives, inventory validation, and fail-closed integrity checks implemented. No live pilot authorized. |
| **Four-Condition Pilot Readiness** | BLOCKED | D3/D5 remain PARTIAL; D4 runtime interception is verified as feasible but not wired; Jetstream is SHELVED; zero live runs authorized. |

---

## 2. Part A: D2 Candidate-Evidence Persistence Implementation

### 2.1 Implementation Architecture

The D2 persistence extension in `src/memlife/runner/phase08d3.py` builds upon `AttemptArtifactStore` to durably persist candidate extraction evidence without altering baseline adapter behavior when disabled:

1. **Candidate Position & Field Preservation:**
   `CandidateEvidence` records:
   - `position`: Native 0-indexed position within the raw response array.
   - `included`: Boolean selection decision (retaining native selection without inferring from ID alone).
   - `selection_reason`: Detailed reason (`selected_within_limit`, `discarded_beyond_limit`, `discarded_malformed_entry`, `discarded_blank_entry`).
   - `native_id`: Native fact ID string (preserving duplicates and order).
   - `parent_ids` / `source_ids`: Native lineage identifiers (`source_memory_ids`).
   - `surface`: Native fact surface/type (`fact_type`).
   - `decoded_field_bytes`: Exact UTF-8 decoded bytes of the raw text field.
   - `normalized_bytes`: Text after whitespace stripping and lowercasing.
   - `extraction_rule`: Exact extraction rule name (`hindsight_query_v1`).
   - `extraction_version`: Protocol version (`v1`).

2. **D1 Response Linkage & Transformation Chain:**
   Each candidate record links directly to the D1 HTTP response artifact:
   - `exchange_id`: Unique identifier of the HTTP exchange.
   - `http_response_artifact`: Relative path, SHA-256, and byte count of the captured raw response.
   - `transformations`: Explicit transformation records linking:
     - `json_pointer_to_utf8_decoded_field` (lossless extraction of decoded field from response bytes).
     - `utf8_decoded_field_to_strip_normalized` (lossy normalization).

3. **Artifact Persistence & Disposition:**
   `CandidateArtifactSink.capture_and_persist`:
   - Writes exact decoded field bytes to `candidates/raw/{exchange_id}-{position:04d}.bin`.
   - Writes normalized text bytes to `candidates/normalized/{exchange_id}-{position:04d}.bin`.
   - Serializes complete candidate metadata to `candidates/{exchange_id}.json` using deterministic indentation and sorted keys.
   - Enforces exclusive creation (`FileExistsError` on collision) and private permissions (`0o600`).
   - Assigns explicit extraction disposition:
     - `COMPLETE_EMPTY`: Native response array was empty.
     - `COMPLETE_NONEMPTY`: Native response contained candidate entries (selected or discarded).
     - `FILTERED_ALL`: Native response contained candidates, but all were filtered out.

4. **Integrity Verification (`verify_candidate_integrity`):**
   Validates that:
   - The candidate manifest exists within the store root.
   - The linked D1 HTTP response artifact exists and matches recorded byte count and SHA-256 hash.
   - Every candidate's raw and normalized binary artifacts exist and match recorded byte counts and SHA-256 hashes.
   - Any missing file, byte mismatch, or hash corruption fails closed (`False`).

5. **Separation from Proposition Binding:**
   Raw candidates and candidate-evidence manifests are captured strictly as extraction evidence. Proposition bindings are neither computed nor assumed during extraction; they remain decoupled until independently frozen authority rules and ground-truth evidence are evaluated.

6. **Adapter Backward Compatibility:**
   In `src/memlife/adapters/hindsight.py`, `UrllibHindsightTransport` records `self.last_exchange = manifest`. `HindsightMemoryAdapter.query` checks if `self.query_sink` is an instance of `CandidateArtifactSink` and passes the exchange manifest. When `query_sink` is `None` or a plain callback, transport and adapter behavior remains identical to baseline.

---

## 3. Part B: D4 Internal-Send Boundary Static Audit

### 3.1 Pinned Commit & Scope
- **Commit:** `f8950b0c07d9e34c76493dba802bb309f0ce60fd` (Hindsight 0.10.1).
- **Audit Objective:** Trace all potentially billable text-model sends and local ONNX embedding calls to determine if a single maintainable interception seam can observe, admit, attribute, and account for every send.

### 3.2 Send-Path Coverage Matrix

| Category | Call Site | File & Line | Invocation Path | Parameters / Payload |
|---|---|---|---|---|
| **Startup Probe** | Connection verification | `hindsight/memory_engine.py:5091` (`MemoryEngine.initialize`) | Direct call: `OpenAICompatibleLLM.verify_connection` (`openai_compatible_llm.py:976`) | `messages=[{"role": "user", "content": "Say 'ok'"}]`, `max_completion_tokens=16`, timeout 10.0s |
| **Health Probe** | LLM liveness probe | `hindsight/memory_engine.py:16162` (`MemoryEngine._probe_llm`) | Direct call: `verify_connection()` | Same as startup probe |
| **Foreground Retain** | Fact extraction | `hindsight/fact_extraction.py:2085` (`_extract_facts_from_chunks`) | Outer loop `range(outer_attempts)` -> `llm_config.call(**call_kwargs)` | Chunk text, schema prompt, `response_format` |
| **Foreground Retain** | Context resolution / title | `hindsight/memory_engine.py:17616` | `llm_config.call(...)` | Context resolution messages |
| **Background Consolidation** | Consolidation batch | `hindsight/consolidator.py:3245` (`_run_consolidation_batch`) | `llm_config.call(**call_kwargs)` with adaptive bisection on error | Unconsolidated memories, prompt, `consolidation_max_completion_tokens` |
| **Background Dedup** | Fact deduplication | `hindsight/consolidator.py:352` (`_evaluate_dedup_candidate`) | `dedup_llm_config.call(...)` | Candidate pair comparison prompt |
| **Unsay / Delta Curate** | Fact invalidation curation | `hindsight/memory_engine.py:17749` | `llm_config.call(...)` | Invalidation diff prompt |
| **Wire Transmission** | Physical HTTP Send | `hindsight/llm/openai_compatible_llm.py:1257` (structured), `1337` (unstructured), `1666` (tools) | `await self._client.chat.completions.create(**call_params)` inside retry loop `range(max_retries + 1)` (lines 1249-1525) | Pinned model, messages, temperature, max tokens |
| **Local Embeddings** | ONNX Vector Encoding | `hindsight/embeddings.py:502`, `568` | Local CPU `ort.InferenceSession.run` | **Zero external sends**; 100% local ONNX execution |
| **Worker Poller** | Async Task Processing | `hindsight/background/poller.py` (`WorkerPoller`) | `MemoryEngine.execute_task` (`memory_engine.py:3933`) | Shares same LLM config and client instances |

### 3.3 Proven vs Unverified Interception Seams

1. **Why `LLMProvider.call` is INSUFFICIENT:**
   - **Startup Probe Bypass:** `MemoryEngine.initialize` invokes `self.llm_config.verify_connection()`, which calls `OpenAICompatibleLLM.call()` directly on the provider instance, completely bypassing `LLMProvider.call()`.
   - **Retry Multiplicity:** Native retries (`range(max_retries + 1)`) are handled inside `OpenAICompatibleLLM.call()` (lines 1249-1525). A single invocation of `LLMProvider.call()` can produce multiple wire transmissions upon transient errors (`APIConnectionError`, `APIStatusError`, `json.JSONDecodeError`).

2. **Why Native `LLMTraceRecorder` is INSUFFICIENT:**
   - **Post-Response Only:** Native traces are recorded after execution finishes; they cannot enforce atomic admission before transmission.
   - **Transient & Fragile:** Traces are dropped if the database is not ready or if operations fail before trace persistence.
   - **Retry Oblivious:** Traces record the final logical attempt, not individual physical network retries.

3. **Proven Interception Seam:**
   - Interception must occur at `OpenAICompatibleLLM._client.chat.completions.create` or via a custom transport hook passed to `AsyncOpenAI` (`httpx.AsyncClient(transport=...)`).
   - Every text-model send (startup probe, retain extraction, consolidation batches, dedup, and native retries) converges strictly at `_client.chat.completions.create`.
   - Local embeddings are completely decoupled: `OnnxEmbeddings` uses `onnxruntime.InferenceSession` and makes zero calls to `_client`.

### 3.4 Feasibility Verdict & Specific Blockers

**Verdict: `FEASIBLE_WITH_VERIFIED_BOUNDARY`** for the interception boundary itself.

However, end-to-end token budgeting and gate enforcement remain conditionally blocked by the following provider-internal characteristics:

1. **Unbounded Consolidation Tokens:**
   `consolidation_max_completion_tokens` is unset (`None`) by default in `Consolidator` (`consolidator.py:3239`). Because output tokens are not capped before invocation, pre-send admission cannot compute a safe token ceiling without pinning `consolidation_max_completion_tokens` in Hindsight configuration.
2. **Missing Usage Coercion:**
   Native `OpenAICompatibleLLM` coerces missing or failed usage receipts to 0 tokens (`openai_compatible_llm.py:395, 1486`). A rigorous admission gate must treat missing usage as unverified/rejected rather than zero cost.
3. **Cross-Process Concurrency:**
   `SendAccounting` uses an in-memory `threading.Lock`. If background workers run as separate processes (e.g. `hindsight-worker` CLI), accounting cannot coordinate atomically across processes without a shared IPC/file lock. Single-process worker execution must be enforced.
4. **Endpoint Trustworthiness:**
   Static analysis cannot verify whether the target vLLM/Ollama endpoint (`gpt-oss-120b`) reliably returns valid token usage fields.

---

## 4. Minimal Future D4 Integration Design

If authorized in a future phase, the minimal non-intrusive interception wrapper would be structured as follows:

```python
# Conceptual wrapper around OpenAICompatibleLLM._client.chat.completions.create
class GovernedChatCompletions:
    def __init__(self, original_completions, accounting: SendAccounting, allowed_models: set[str]):
        self._original = original_completions
        self._accounting = accounting
        self._allowed_models = allowed_models

    async def create(self, *args, **kwargs):
        model = kwargs.get("model")
        if model not in self._allowed_models:
            raise SendAdmissionDeniedError(f"Unauthorized model: {model}")

        max_tokens = kwargs.get("max_tokens") or kwargs.get("max_completion_tokens")
        if max_tokens is None:
            raise SendAdmissionDeniedError("Unbounded completion tokens rejected")

        # Atomic pre-send admission
        reservation = self._accounting.admit_send(
            model=model,
            expected_max_tokens=max_tokens + estimated_prompt_tokens(kwargs.get("messages", [])),
        )
        try:
            response = await self._original.create(*args, **kwargs)
            usage = getattr(response, "usage", None)
            if usage is None or usage.total_tokens is None:
                self._accounting.record_missing_usage(reservation.reservation_id)
            else:
                self._accounting.settle_send(
                    reservation.reservation_id,
                    actual_tokens=usage.total_tokens,
                )
            return response
        except Exception:
            self._accounting.record_missing_usage(reservation.reservation_id)
            raise
```

---

## 5. Offline Test Evidence

### 5.1 Focused D2 Tests
All 9 new unit tests in `tests/unit/test_phase08d4_evidence_persistence.py` passed cleanly:
- `test_candidate_persistence_exact_bytes_and_deterministic_hashes`: exact byte equality and hash verification.
- `test_candidate_persistence_preserves_unicode_whitespace_and_escapes`: Unicode normalization and raw character preservation.
- `test_candidate_persistence_preserves_duplicate_ids_and_order`: non-collapse of duplicate native IDs.
- `test_candidate_persistence_distinguishes_empty_from_filtered`: `COMPLETE_EMPTY` vs `COMPLETE_NONEMPTY` vs `FILTERED_ALL`.
- `test_candidate_persistence_links_to_d1_response`: valid linkage and transformation tracking.
- `test_candidate_integrity_verification_detects_missing_or_corrupt_artifacts`: detects modified payload bytes and missing manifests.
- `test_candidate_persistence_fails_closed_on_write_conflict_or_missing_ref`: verifies exception handling.
- `test_disabled_instrumentation_backward_compatibility`: verifies uninstrumented adapter behaves identically to baseline.
- `test_adapter_query_sink_persists_evidence`: end-to-end adapter query integration with sink.

Targeted suite command:
```bash
./.venv/bin/python -m pytest \
  tests/unit/test_phase08d4_evidence_persistence.py \
  tests/unit/test_phase08d3_capture_accounting.py \
  tests/unit/test_hindsight_adapter.py \
  tests/unit/test_hindsight_lifecycle_trace.py -q
```
**Result: 32 passed in 0.49s.**

### 5.2 Full Test Suite Results
Full test suite run (`./.venv/bin/python -m pytest tests -q`):
**544 passed, 1 skipped, 13 failed, 6 errors**.

All 19 failures and errors are verified pre-existing environmental constraints:
1. Historical artifact absence:
   - `tests/unit/test_phase07_prep.py::test_phase06b_source_artifacts_integrity` (missing raw file under `artifacts/phase06b/attempts/20261001T183940Z-1fc4c4929532/`).
2. Ignored local review fixtures:
   - 10 tests in `tests/unit/test_phase08b1_honcho_live.py` require absent ignored `.local/review/honcho-upstream-v3.2.1/docker-compose.yml.example`.
   - 2 tests in `tests/unit/test_phase08b1_honcho_live.py` (`test_patch_transport...`, `test_exact_candidate8_patch...`) require uncommitted ignored Candidate10/Candidate8 patches.
3. Local socket bind denial:
   - `tests/unit/test_phase08b1_honcho_live.py::test_existing_proxy_routes_text_hosted_and_embeddings_local` denied 127.0.0.1 socket bind in sandbox.
4. macOS platform absence of Linux `findmnt`:
   - 6 Mem0 integration tests fail at fixture setup resolving `/dev/sdb`.

None of these failures were caused or modified by Phase 08D-4 changes.

---

## 6. Scientific & Execution Blockers

1. **D3 Lifecycle Quiescence:** Polling active operations cannot statically guarantee that background workers are not about to poll new tasks from SQLite/Postgres. Background coverage remains `UNKNOWN`.
2. **D4 Token Upper Bounds:** Hindsight consolidation token limits are unbound by default. Must be clamped in configuration before admission enforcement.
3. **Missing Usage Coercion:** Native Hindsight converts missing LLM usage to zero. Must be intercepted and treated as unverified.
4. **Jetstream State:** Jetstream remains SHELVED. Zero live requests authorized.
5. **Freeze v2 Blocked:** Candidate10 is frozen NO_GO; Freeze v2 remains unfinalized.

---

## 7. Operational Commitments

- **Base SHA Verified:** `7d3593bb319b2aa945c5ff20dae4e725a7201e9c`.
- **Review Branch:** `phase-08d4-evidence-persistence`.
- **Primary Checkout Untouched:** `/Users/ian/Desktop/Memo` remains clean on `main`.
- **Experimental Calls:** Exactly `0` provider calls, `0` hosted-model calls, `0` embedding calls, `0` Jetstream calls, `0` RQ3 calls.
