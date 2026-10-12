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
| **D2 candidate persistence** | IMPLEMENTED & VERIFIED | `CandidateArtifactSink` reparses persisted response bytes and independently validates candidate values, positions, transformations, selection decisions, and disposition. Fails closed on missing or malformed `results` or forged candidates. Replaces shared mutable transport state with thread-local exchange correlation and validates recall endpoint association. Decoded UTF-8 string bytes are preserved separately from stripped normalized bytes and wire JSON. Validated via `verify_candidate_integrity`. All 13 focused tests passing 100%. |
| **D3 lifecycle completion** | PARTIAL | Paginated polling and terminal receipt validation implemented in Phase 08D-3. Quiescence listing cannot prove global worker quiescence; background and overall coverage remain explicitly `UNKNOWN`. |
| **D4 internal send boundary** | PARTIALLY_FEASIBLE / BLOCKED | Candidate OpenAI-compatible send seam identified at `OpenAICompatibleLLM._client.chat.completions.create` (or `AsyncOpenAI` `httpx` transport). However, complete runtime interception across all background worker paths is **not** independently proven statically. Actual-send enforcement remains **BLOCKED**. Local ONNX embeddings execute in-process on CPU via `ort.InferenceSession.run`, but `OnnxEmbeddings.initialize` requires pre-cached model paths to prevent network downloads via `snapshot_download`. |
| **D5 attempt/evidence gates** | PARTIAL | Offline gate primitives, inventory validation, and fail-closed integrity checks implemented. No live pilot authorized. |
| **Four-Condition Pilot Readiness** | BLOCKED | D3/D5 remain PARTIAL; D4 runtime interception is unproven and actual-send enforcement is BLOCKED; Jetstream is SHELVED; zero live runs authorized. |

---

## 2. Part A: D2 Candidate-Evidence Persistence Implementation

### 2.1 Implementation Architecture

The D2 persistence extension in `src/memlife/runner/phase08d3.py` builds upon `AttemptArtifactStore` to durably persist candidate extraction evidence with full source binding and integrity validation:

1. **Reparsing Response Bytes & Candidate Source Binding:**
   `CandidateArtifactSink.capture_and_persist` does not rely on caller-supplied candidates alone. It:
   - Reads the linked D1 HTTP response artifact from disk and validates byte count and SHA-256.
   - Decodes response bytes as UTF-8 and parses JSON.
   - Verifies the response is a JSON object containing a `"results"` key.
   - Enforces that `"results"` is a list. If `"results"` is missing, non-list, or null, it raises `CaptureFailure` rather than incorrectly classifying the response as empty.
   - Validates that any caller-supplied `results` parameter strictly matches the reparsed response `results`.
   - Derives authoritative candidate extraction directly from the reparsed response array.

2. **Candidate Position, Indexing & JSON Field Paths:**
   - Positions in `CandidateEvidence.position` are **1-indexed** (`position: 1 .. N`), matching natural sequence order.
   - Explicit RFC 6901 JSON pointer paths are recorded for each candidate:
     - `json_path`: Pointer to the candidate object in the response array (`/results/{idx}`, where `idx = position - 1`).
     - `field_path`: Pointer to the extracted text field (`/results/{idx}/text`).
   - Invalid selection positions (`pos < 1`, `pos > len(results)`, non-integer) are rejected with `CaptureFailure`.
   - Selecting candidates with blank or non-string text is rejected with `CaptureFailure`.
   - In Hindsight recall semantics, acceptable candidates must be selected in prefix order up to `limit`; out-of-order or inconsistent selection decisions fail closed.

3. **Distinction Between Byte Representations:**
   The implementation strictly preserves the distinction between three byte representations:
   - `response_bytes`: The original wire JSON payload bytes before decoding (which include JSON formatting, quotes, indentation, and escape sequences).
   - `decoded_field_bytes`: The exact UTF-8 bytes of the decoded string value of `item["text"]` extracted from the parsed JSON object (e.g., escape sequences like `\n` become byte `0x0A`). Persisted to `candidates/{exchange_id}/candidate-{position:04d}.decoded.bin`.
   - `normalized_bytes`: The UTF-8 bytes of the string after whitespace stripping (`text.strip()`). Persisted to `candidates/{exchange_id}/candidate-{position:04d}.normalized.bin`.
   - Documented transformations link these representations:
     - Transformation 1: `json_pointer_to_utf8_decoded_field` (lossless extraction of decoded field from wire response bytes at `json_pointer`).
     - Transformation 2: `utf8_decoded_field_to_strip_normalized` (lossy normalization via `.strip()`, preserving character case).

4. **Disposition Tracking:**
   - `COMPLETE_EMPTY`: The HTTP response `"results"` list was explicitly present and empty (`[]`).
   - `FILTERED_ALL`: The HTTP response contained candidate results, but zero were selected (e.g. all entries had blank or non-string text).
   - `COMPLETE_NONEMPTY`: The HTTP response contained candidate results, and at least one was selected.

5. **Airtight Integrity Validation (`verify_candidate_integrity`):**
   `verify_candidate_integrity(store, exchange_id)` independently validates that:
   - The candidate manifest exists and is valid JSON.
   - The linked D1 response artifact exists and matches recorded byte count and SHA-256.
   - The response bytes are re-parsed as valid JSON with a `"results"` list.
   - `manifest["total_candidates"]` and `manifest["candidates"]` length equal `len(results)`.
   - `manifest["selected_count"]` equals the count of candidates with `included is True`.
   - `manifest["retrieval_disposition"]` matches the actual results and selection counts.
   - For every candidate at index `idx` (position `idx + 1`):
     - `json_path` matches `/results/{idx}` and `field_path` matches `/results/{idx}/text`.
     - `native_id`, `surface`, and `parent_ids` match raw response fields.
     - Decoded field artifact exists on disk and its bytes match `raw_text.encode("utf-8")`.
     - Normalized artifact exists on disk and its bytes match `raw_text.strip().encode("utf-8")`.
     - Both transformation records match expected rules, inputs, and output hashes.
   - Any missing file, hash mismatch, or forged/inconsistent candidate returns `False`.

6. **Exchange Correlation & Thread Safety:**
   - `UrllibHindsightTransport` and `FakeHindsightTransport` use thread-local storage (`_thread_local`) for `last_exchange` rather than shared mutable instance attributes.
   - Transports provide `pop_last_exchange()`, ensuring that each exchange is safely consumed by the issuing query and cannot be leaked or reused by subsequent operations.
   - In `HindsightMemoryAdapter.query`, the consumed exchange is validated against the expected recall endpoint (`POST /v1/default/banks/{bank}/memories/recall`). If an exchange from an interleaved operation or mismatched endpoint is detected, it raises `AdapterError`.
   - On HTTP failure paths (e.g. 404/500 errors), the failed exchange is captured on the thread-local for audit, and subsequent successful queries do not reuse stale error exchanges.

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
| **Local Embeddings** | ONNX Vector Encoding | `hindsight/embeddings.py:502`, `568` | Local CPU `ort.InferenceSession.run` | In-process CPU forward pass; **network download during initialization if un-cached** |
| **Worker Poller** | Async Task Processing | `hindsight/background/poller.py` (`WorkerPoller`) | `MemoryEngine.execute_task` (`memory_engine.py:3933`) | Shares same LLM config and client instances |

### 3.3 ONNX Initialization & Network-Access Qualification

In `hindsight/embeddings.py` (lines 515–532 and 547):
- `OnnxEmbeddings.encode` executes forward passes locally on CPU via `ort.InferenceSession.run` with zero external model calls.
- **However**, `OnnxEmbeddings.initialize` performs network I/O if the model or tokenizer are not explicitly pre-staged:
  - If `self.model_path` is not set, `snapshot_download(repo_id=self.model_id, allow_patterns=[...])` reaches out to the Hugging Face Hub over the network.
  - `AutoTokenizer.from_pretrained(self.tokenizer_name_or_path)` may also perform remote lookups.
- Therefore, ONNX embeddings are only guaranteed local and offline when `HINDSIGHT_API_EMBEDDINGS_ONNX_MODEL_PATH` and local tokenizer paths are pre-cached and pinned in deployment configuration.

### 3.4 Proven vs Unverified Interception Seams

1. **Why `LLMProvider.call` is INSUFFICIENT:**
   - **Startup Probe Bypass:** `MemoryEngine.initialize` invokes `self.llm_config.verify_connection()`, which calls `OpenAICompatibleLLM.call()` directly on the provider instance, completely bypassing `LLMProvider.call()`.
   - **Retry Multiplicity:** Native retries (`range(max_retries + 1)`) are handled inside `OpenAICompatibleLLM.call()` (lines 1249-1525). A single invocation of `LLMProvider.call()` can produce multiple wire transmissions upon transient errors (`APIConnectionError`, `APIStatusError`, `json.JSONDecodeError`).

2. **Why Native `LLMTraceRecorder` is INSUFFICIENT:**
   - **Post-Response Only:** Native traces are recorded after execution finishes; they cannot enforce atomic admission before transmission.
   - **Transient & Fragile:** Traces are dropped if the database is not ready or if operations fail before trace persistence.
   - **Retry Oblivious:** Traces record the final logical attempt, not individual physical network retries.

3. **Candidate Interception Seam:**
   - Interception can be targeted at `OpenAICompatibleLLM._client.chat.completions.create` or via a custom transport hook passed to `AsyncOpenAI` (`httpx.AsyncClient(transport=...)`).
   - Every text-model send (startup probe, retain extraction, consolidation batches, dedup, and native retries) converges at `_client.chat.completions.create`.

### 3.5 Reassessed Feasibility Verdict & Specific Blockers

**Verdict: `PARTIALLY_FEASIBLE` (Candidate Seam Identified) / `BLOCKED` (Actual-Send Enforcement).**

While the code-level seam at `_client.chat.completions.create` covers all currently identified text sends in the codebase, complete runtime interception and actual-send enforcement remain **BLOCKED** due to the following unresolved scientific and architectural gaps:

1. **Unproven Runtime Interception Completeness:**
   Static analysis identifies the send call sites, but cannot independently prove runtime completeness across all worker deployment configurations (e.g. background workers launched via separate CLI commands or multiprocess pools that do not share in-process hooks).
2. **Unbounded Consolidation Tokens:**
   `consolidation_max_completion_tokens` is unset (`None`) by default in `Consolidator` (`consolidator.py:3239`). Because output tokens are not capped before invocation, pre-send admission cannot compute a safe token ceiling without pinning `consolidation_max_completion_tokens` in Hindsight configuration.
3. **Missing Usage Coercion:**
   Native `OpenAICompatibleLLM` coerces missing or failed usage receipts to 0 tokens (`openai_compatible_llm.py:395, 1486`). A rigorous admission gate must treat missing usage as unverified/rejected rather than zero cost.
4. **Cross-Process Concurrency:**
   `SendAccounting` uses an in-memory `threading.Lock`. If background workers run as separate processes (e.g. `hindsight-worker` CLI), accounting cannot coordinate atomically across processes without a shared IPC/file lock. Single-process worker execution must be enforced.
5. **Endpoint Trustworthiness:**
   Static analysis cannot verify whether the target vLLM/Ollama endpoint (`gpt-oss-120b`) reliably returns valid token usage fields.

*Per explicit instruction, no runtime interception hooks or live SendAccounting connections were implemented in this phase.*

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
All 13 unit tests in `tests/unit/test_phase08d4_evidence_persistence.py` passed cleanly:
- `test_d2_unicode_whitespace_and_json_escapes`: exact byte equality and hash verification.
- `test_d2_duplicate_native_ids_and_truncation`: non-collapse of duplicate native IDs with distinct artifact paths.
- `test_d2_empty_and_malformed_responses`: complete empty retrieval vs filtered all.
- `test_d2_candidate_to_response_correlation`: valid linkage, transformation rules, and deterministic SHA-256 hashes.
- `test_d2_exact_byte_integrity_and_deterministic_hashes`: negative regression test proving that candidate results inconsistent with persisted HTTP response are rejected and fail closed.
- `test_d2_exact_byte_integrity_and_deterministic_hashes_positive`: positive companion verifying exact bytes and hashes when candidates match response.
- `test_d2_missing_or_corrupt_artifacts_fail_closed`: fails closed on missing exchange references, tampered response bytes, or missing response files.
- `test_d2_write_failures_and_partial_capture_fail_closed`: fails closed on artifact write failures.
- `test_d2_disabled_instrumentation_backward_compatibility`: verifies uninstrumented adapter behaves identically to baseline.
- `test_d2_adapter_query_integration_with_fake_and_urllib_transports`: end-to-end adapter query integration with sink and complete empty queries.
- `test_d2_rejects_missing_or_malformed_results`: rejects missing `"results"` key, non-list results, and null results without classifying as empty.
- `test_d2_evidence_completeness_and_json_field_paths`: verifies RFC 6901 field paths (`/results/{idx}` and `/results/{idx}/text`), rejects invalid positions and blank selection, and preserves distinction between wire JSON and decoded UTF-8 bytes.
- `test_d2_exchange_correlation_concurrent_and_failure_paths`: verifies thread-local exchange isolation under concurrent queries, correct bank correlation, and proper error-exchange recording without stale reuse.

Targeted suite command:
```bash
./.venv/bin/python -m pytest \
  tests/unit/test_phase08d4_evidence_persistence.py \
  tests/unit/test_phase08d3_capture_accounting.py \
  tests/unit/test_hindsight_adapter.py \
  tests/unit/test_hindsight_lifecycle_trace.py -v
```
**Result: 36 passed in 0.55s.**

### 5.2 Full Test Suite Results
Full test suite run (`./.venv/bin/python -m pytest tests -q`):
**544 passed, 1 skipped, 13 failed, 6 errors**.

All 19 failures and errors are verified pre-existing environmental constraints:
1. **Historical Raw Artifact Absence (1 failure):**
   - `tests/unit/test_phase07_prep.py::test_phase06b_source_artifacts_integrity`: missing raw file under `artifacts/phase06b/attempts/20261001T183940Z-1fc4c4929532/`.
2. **Ignored Local Compose Fixture Missing (10 failures in `test_phase08b1_honcho_live.py`):**
   - `test_runtime_env_materializes_only_authorized_config`
   - `test_runtime_residue_classifier_accepts_only_candidate8_or_candidate9[gpt-oss-120b-1536-PHASE08B1_CANDIDATE8_RUNTIME_ENV]`
   - `test_runtime_residue_classifier_accepts_only_candidate8_or_candidate9[sentence-transformers/paraphrase-MiniLM-L3-v2-384-PHASE08B1_CANDIDATE9_RUNTIME_ENV]`
   - `test_recognized_residue_evidence_is_secret_safe_and_precedes_removal`
   - `test_runtime_residue_classifier_rejects_arbitrary_compose_without_deleting`
   - `test_current_runtime_files_are_identity_cleaned_on_normal_path`
   - `test_current_runtime_files_are_cleaned_on_stage_a_failure_path`
   - `test_modified_current_runtime_file_is_preserved_with_cleanup_blocker`
   - `test_declared_config_is_separate_and_cannot_claim_runtime_support`
   - `test_compose_transform_fails_closed_on_pinned_shape_drift`
   (All 10 raise `FileNotFoundError` for ignored `.local/review/honcho-upstream-v3.2.1/docker-compose.yml.example`).
3. **Ignored Local Patch Fixtures Missing (2 failures in `test_phase08b1_honcho_live.py`):**
   - `test_patch_transport_is_file_based_and_candidate_reproduces_local_bytes` (missing `.local/review/phase08b1-honcho-live-acceptance-candidate10.patch`).
   - `test_exact_candidate8_patch_applies_to_governed_cb44_base` (missing `.local/review/phase08b1-honcho-live-acceptance-candidate8.patch`).
4. **Platform Tool Absence: macOS Missing Linux `findmnt` (6 errors in Mem0 integration tests):**
   - `tests/integration/test_mem0_adapter.py::test_mem0_uses_required_oss_mode_and_reusable_contract`
   - `tests/integration/test_mem0_adapter.py::test_mem0_native_cedar_lifecycle`
   - `tests/integration/test_mem0_adapter.py::test_mem0_restart_write_and_delete_sanity`
   - `tests/integration/test_mem0_lifecycle_suite.py::test_mem0_runs_canonical_lifecycle_suite`
   - `tests/integration/test_mem0_lifecycle_suite.py::test_mem0_trace_keeps_provider_internal_causality_unknown`
   - `tests/integration/test_phase06a_mem0_calibration.py::test_mem0_calibration_runs_three_isolated_repetitions`
   (All 6 fail during fixture setup resolving `/dev/sdb` mount via Linux `findmnt`).

None of these 19 failures were caused or modified by Phase 08D-4 changes.

---

## 6. Scientific & Execution Blockers

1. **D3 Lifecycle Quiescence:** Polling active operations cannot statically guarantee that background workers are not about to poll new tasks from SQLite/Postgres. Background coverage remains `UNKNOWN`.
2. **D4 Runtime Interception Completeness:** A static send seam exists at `_client.chat.completions.create`, but complete runtime interception across all background worker and process configurations is not proven.
3. **D4 Token Upper Bounds:** Hindsight consolidation token limits are unbound (`None`) by default. Must be clamped in configuration before admission enforcement.
4. **D4 Missing Usage Coercion:** Native Hindsight converts missing LLM usage to zero. Must be intercepted and treated as unverified.
5. **D4 ONNX Model Pre-caching:** ONNX embeddings must be configured with local paths to prevent network downloads during `OnnxEmbeddings.initialize`.
6. **Jetstream State:** Jetstream remains SHELVED. Zero live requests authorized.
7. **Freeze v2 Blocked:** Candidate10 is frozen NO_GO; Freeze v2 remains unfinalized.

---

## 7. Operational Commitments

- **Base SHA Verified:** `7d3593bb319b2aa945c5ff20dae4e725a7201e9c`.
- **Review Branch:** `phase-08d4-evidence-persistence`.
- **Primary Checkout Untouched:** `/Users/ian/Desktop/Memo` remains clean on `main`.
- **Experimental Calls:** Exactly `0` provider calls, `0` hosted-model calls, `0` embedding calls, `0` Jetstream calls, `0` RQ3 calls.
