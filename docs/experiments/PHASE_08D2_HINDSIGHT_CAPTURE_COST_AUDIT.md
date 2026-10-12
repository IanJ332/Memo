# Phase 08D-2 — Hindsight Offline Capture-Capability and Cost Audit

**STATUS:** static audit complete; execution prerequisites unresolved.

**CONVERSATION:** NEW; `Hindsight-Capture-Cost-Audit`. Subsequent review and
corrections continue in this conversation.

**MODEL:** GPT Sol — High requested; the agent runtime identifies GPT-6 but
does not expose a verifiable deployment variant or reasoning-setting receipt.
The requested label is not independent proof of the exact model used.

**HOST:** macOS x86_64; macOS 15.7.4 verified. **EXECUTION:** Codex Local.
**WORKTREE MODE:** Enabled. **EXECUTION TARGET / WORKTREE PATH:**
`/Users/ian/.codex/worktrees/9c4d/Memo`.

**BASE SHA VERIFIED:** `cf01cd9d4a749cd012f40abcfbbccf02b99dc345`;
assigned HEAD, primary `main`, fetched `origin/main`, and remote main agreed
before editing. **REVIEW BRANCH:** `phase-08d2-hindsight-capture-cost-audit`.
The assigned detached worktree was used to establish this branch; no additional
worktree was created.

**AUDIT DATE:** 2026-10-12, America/Chicago.
**LOCAL DEPENDENCIES INSTALLED:** NO. No `.venv` was created or modified.
Standard-library validation used
`/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12`, which
reports Python **3.12.8**, rather than the supplied 3.12.14. Default `python3`
reports 3.13.9 and was not used for the audit analysis scripts.

**JETSTREAM ACTION:** NONE; project state remains `SHELVED`, without a live
state query. **Provider / experimental hosted LLM / local embedding /
downstream / RQ3 executions:** `0 / 0 / 0 / 0 / 0`.
Public source/documentation reads and Git fetch/publication are audit actions,
not provider or experimental model calls.

**PRIMARY CHECKOUT UNCHANGED:** `/Users/ian/Desktop/Memo` remained clean on
`main` at the required base. Fetch updates shared Git refs; it does not change
primary checkout files, index, branch selection, or HEAD.

## 1. Executive feasibility verdict

**Recommendation D — INSUFFICIENT EVIDENCE for execution readiness.**
Hindsight remains the strongest provisional existing integration for the
update × revoke factorial. Both native transition families have implemented
paths and tracked historical provider observations. Exact response capture
has a clear local patch boundary. There is no demonstrated fundamental native
capability deficiency warranting recommendation C.

However, a minimal adapter capture wrapper cannot establish complete internal
call accounting or prevent token overruns. Native provider tracing is a useful
reuse opportunity, but its persistence and retry granularity are insufficient
as an independent admission/budget control. Endpoint usage completeness,
enforcement at each actual send, background attribution, and present resource
headroom remain unverified. Thus **B — MINIMAL CAPTURE/ACCOUNTING PATCH REQUIRED
is a conditional engineering path**, not a finding that a bounded patch has
already been proven sufficient. A separately authorized implementation and
verification phase must resolve those gaps before execution can be considered.

| Dimension | Verdict | Evidence and exact limit |
|---|---|---|
| `RAW_CAPTURE` | `NEEDS_MINIMAL_PATCH` | E1: `response.read()` obtains body bytes but no artifact is written. Capture before decoding, including errors. |
| `CANDIDATE_BYTES` | `NEEDS_MINIMAL_PATCH` | E2/E3: text stripping, filtering, limiting and hash-only serialization lose bytes and original positions. Preserve extraction and normalized outputs separately. |
| `CONTENT_BINDING` | `NEEDS_MINIMAL_PATCH` | E5: existing contracts/policy are reusable; future independent bindings and frozen algorithms/authority inputs are not populated for these conditions. |
| `UPDATE_NATIVE_OPERATION` | `READY` | E2/H1/H2: native same-ID source curation is implemented and historically observed. READY applies only to this operation, not native supersession/version provenance. |
| `REVOKE_NATIVE_OPERATION` | `READY` | E2/H1/H2: native `state=invalidated` is implemented and historically observed. It is not hard deletion or universal non-retrievability. |
| `QUIESCENCE` | `NEEDS_MINIMAL_PATCH` | E2/H1: existing polling supplies useful evidence, but one-page listings, 404-as-empty, incomplete status handling and transient metadata prevent the required completion proof. |
| `PROVENANCE` | `NEEDS_MINIMAL_PATCH` | E2/E3/E4/H3: native parent IDs and observed correlations exist; relation basis, exact exchange references and version attribution need sidecars. Unavailable native lineage stays UNKNOWN. |
| `INTERNAL_CALL_ACCOUNTING` | `BLOCKED` | E6/P2/P3/P4: no attempt-level complete send ledger; best-effort native traces are not all-request counters, especially for startup and retries. |
| `TOKEN_ACCOUNTING` | `UNKNOWN` | H1/H2/P3: historical tokens absent; endpoint usage completeness and a trustworthy per-send bound are unverified. Missing usage must not mean zero. |
| `MONETARY_COST_ACCOUNTING` | `UNKNOWN` | H1/H2/P7: public no-charge policy exists, but historical/future attempt-specific billing and measured usage are not established. |
| `CPU_RAM_FEASIBILITY` | `UNKNOWN` | H1/H4: historical operation on the small VM is supported; current headroom and Hindsight peak working set are not measured here. |
| `STORAGE_FEASIBILITY` | `UNKNOWN` | H4/H5: historical capacity/free bytes exist; current availability, capture limits and database/cache growth ceilings are unresolved. |
| `FOUR_CONDITION_PILOT_READINESS` | `BLOCKED` | Protocol §§10–12: capture, completion, accounting, approved inputs, review and resource/budget gates do not all pass. |

The source-code basis for raw capture corresponds to
`NEEDS_MINIMAL_CAPTURE_PATCH` in Audit A's vocabulary. No condition is approved
for execution by this report.

## 2. Scope, current state, and evidence levels

The required project handoffs, experiment ledger, debugging ledger,
[Phase 08D-0 audit](RQ4_EVIDENCE_COVERAGE_AUDIT.md),
[Phase 08D-1 protocol](PHASE_08D1_RQ4_GROUND_TRUTH_CAPTURE_PROTOCOL.md),
[Phase 08C-1 pilot](PHASE_08C1_RQ4_MINIMAL_PILOT.md),
[Phase 07 decisions](PHASE_07_SCIENTIFIC_DECISIONS.md), and
[Phase 04 bring-up](../phases/PHASE_04_HINDSIGHT_BRINGUP.md) were inspected.
Historical phase labels in handoff files do not override verified Git history
or the accepted scientific reports.

Established findings remain: Freeze v1 has 42 executions / 14 cells / 41
successes / one frozen OpenViking S0 r2 ERROR; 37 final candidate occurrences,
21 bindable and 16 hash-only; the published RQ4 pilot is 19/19 with two empirical
positive controls and zero empirical unauthorized-content controls. Seven
initial annotation packets remain pending two human reviews. Honcho Candidate10
is frozen NO_GO; Freeze v2 remains unfinalized and blocked; RetainDB is pending
live acceptance and Graphiti remains fallback. RQ3 has no eligible empirical
context and remains inactive. No historical run was rerun or reinterpreted.

Evidence levels used below:

- **STATIC / VERIFIED:** direct source behavior, not live qualification.
- **TEST-SUPPORTED / VERIFIED:** what an inspected controlled test asserts;
  tests were not executed in this audit.
- **HISTORICAL / VERIFIED:** a claim present in tracked provider-observation
  records, with internal IDs/hashes checked where available. This is not fresh
  authentication of the unavailable original private evidence.
- **PROPOSED / INFERRED:** future design, with sufficiency still to be verified.
- **UNKNOWN:** not established from the permitted evidence.

### Evidence register

Line references are one-based at the verified base. Each row states what its
source proves and the limit on that proof. E/H/P identifiers are used throughout
the matrices to keep important conclusions traceable.

| ID | Exact source, symbols or artifact field | Claim proved; claim not proved | Level/status |
|---|---|---|---|
| E1 | [adapter](../../src/memlife/adapters/hindsight.py), `UrllibHindsightTransport.request`, lines 116–149; `HindsightHTTPError`, 85 | Body read, JSON decode, error conversion; no durable capture. Does not prove response size or content on a future service. | STATIC / VERIFIED |
| E2 | Same adapter: `_normalized_record` 306; `query` 592; `update_or_supersede` 625; `delete_or_invalidate` 646; `_list_operations` 425; `_wait_for_operation` 442; `wait_for_quiescence` 478; provenance hooks 246–288 | Native request and normalization/polling paths exist. Does not prove a future provider response or full convergence. | STATIC / VERIFIED |
| E3 | [storage batch](../../src/memlife/runner/storage_batch.py), `_correlated_event_ids` 326, `_retrieval_payload` 346, `run_repetition` 402, `write_jsonl` 956, `validate_artifacts` 969 | Normalized hashes/ranks, event correlation, error classification and frozen-row validation. No exact response persistence or complete new-protocol eligibility gate. | STATIC / VERIFIED |
| E4 | [lifecycle](../../src/memlife/runner/lifecycle.py), `LifecycleStepObservation` 33, `normalize_query_observation` 46, metadata refresh 305; [trace runner](../../src/memlife/runner/provenance.py), `ProvenanceTraceRunner`, 35, candidate construction 250 | Normalized records and optional sanitized content; observed correlation basis. No raw exchange or native version edge guarantee. | STATIC / VERIFIED |
| E5 | [authority](../../src/memlife/models/authority.py), `content_sha256` 31, `AuthorityLedgerEntry` 37, `AuthorityLedger` 60; [mediator](../../src/memlife/models/mediator.py), `CandidateEnvelope` 67, `AuthoritySnapshot` 127, `RelationEdge` 41; [policy](../../src/memlife/runner/rq4_policy.py), `ContentIdentityBinding` 41, `AuthorityBundle` 67, `_frame_allowed_content` 200, `evaluate_candidates` 244 | Exact binding/authority and allow-only byte interfaces exist. They do not collect or independently establish provider evidence. | STATIC / VERIFIED |
| E6 | [frozen config](../../configs/hindsight-phase04.json), `internal_llm`, `embeddings`, `reranker`, `processing`; [requirements](../../requirements/providers/hindsight.txt), line 5; adapter `phase04_manifest_configuration` 42 | Version 0.10.1, pinned source commit, model and deployment choices. Configuration is not usage measurement or full runtime override detection. | STATIC / VERIFIED |
| E7 | [runtime](../../scripts/jetstream/phase04_runtime.py), `Phase04RuntimePaths` 33, fingerprint functions 154/191, `HindsightServiceController` 203; [Phase 06B harness](../../scripts/jetstream/phase06b_harness.py), `select_approved_harness` 56; [remote runner](../../scripts/jetstream/phase06b_remote.py), `validate_pre_experiment_environment` 148 | Isolated runtime, owned service, prefix/version/config guards. Does not establish current remote installation, capacity or call-budget control. | STATIC / VERIFIED |
| E8 | [Phase 04 controller](../../scripts/jetstream/phase04.py), `run_remote_validation` 46; [Phase 04 shell](../../scripts/jetstream/phase04_remote.sh), provider env and launch; [Phase 06B controller](../../scripts/jetstream/phase06b.py), `new_attempt_id` 42, `_download_artifacts` 128, `_write_local_result` 157; [Phase 06B shell](../../scripts/jetstream/phase06b_remote.sh), 100–123 | Existing lifecycle ownership and attempt-exclusive patterns. Phase 04 fixed result path and Phase 06B frozen 42-run orchestration must not be used to execute a new pilot unchanged. | STATIC / VERIFIED |
| E9 | [base contract](../../src/memlife/adapters/base.py), `MemoryProviderAdapter` 50; [memory](../../src/memlife/models/memory.py), `NonEmptyText` 11, `MemoryRecord` 55; [provenance model](../../src/memlife/models/provenance.py), `RetrievalCandidate` 131, `RetrievalTrace` 205 | Existing interfaces, content whitespace constraints and closed models. Declarations/validation do not prove live evidence. | STATIC / VERIFIED |
| H1 | [Phase 04 manifest](../../manifests/phase-04-hindsight-bringup.json), `attempt_history.attempt_4`, `lifecycle_result_summary`, `persistence_restart`, runtime fingerprints; tested commit `3851543d6d5ef013fbe635bfe495c443227c076c` | Tracked historical PASS for curation, invalidation, isolated environments and restart. No independently measured internal call/token/cost totals or peak resource profile. | HISTORICAL / VERIFIED |
| H2 | [combined derived rows](../../artifacts/phase06b/supplements/derived/20261002T000350Z-c272b34d2cc3/combined-derived-runs.jsonl), Hindsight S1/S5 r1–r3, `provider_native_operations`, `retrievals`, `quiescence_evidence`; original attempt `20261001T183940Z-1fc4c4929532` | Native mutation success and recorded final retrieval outcomes/operation IDs. Derived rows do not reproduce original HTTP payloads or every terminal status. | HISTORICAL / VERIFIED |
| H3 | [recovery review](../../artifacts/phase07/hindsight-s1-recovery-review.json), `exact_recovery_targets`, `content_identity_verification`; recovery `20261003T003809Z-7a3425bf2f4c` | Three exact current-v2 texts, hashes and parent identities match H2. Unavailable private DB/recovery files were not independently replayed; no raw recall response is supplied by this review. | HISTORICAL / VERIFIED |
| H4 | [server context](../infrastructure/JETSTREAM2_SERVER_CONTEXT.md), compute/storage sections; [automation](../infrastructure/JETSTREAM2_AUTOMATION.md), Phase 02B-0 result; [setup](../JETSTREAM2_SETUP.md), baseline; [target config](../../configs/jetstream.json) | Cached m3.small/2-vCPU/5.78-GiB/no-GPU Ubuntu target and `/dev/sdb` identity. No current live capacity or resource measurement. | HISTORICAL / VERIFIED as cached context |
| H5 | [supplement preflight](../../artifacts/phase06b/supplements/attempts/20261002T000350Z-c272b34d2cc3/supplement-preflight.json), free-byte fields; [diagnostics](../../artifacts/phase06b/supplements/attempts/20261002T000350Z-c272b34d2cc3/supplement-diagnostics.jsonl), line 1, `system_memory_before_provider_startup` | Historical disk free bytes and pre-OpenViking system memory. OpenViking process RSS is not a Hindsight memory measurement. | HISTORICAL / VERIFIED |

Pinned first-party source inspection used GitHub's recursive tree at
`f8950b0c07d9e34c76493dba802bb309f0ce60fd`. Eleven selected source files were
read into temporary storage and each Git blob SHA-1 matched the tree entry.
No source was imported, installed, executed or added to the repository.
The inspected source is not proof that a historical installed wheel had
identical bytes or runtime defaults; that equivalence requires a future
runtime/source fingerprint check.

| ID | Pinned first-party file and exact symbol/line | Proves; does not prove | Status |
|---|---|---|---|
| P1 | [API](https://github.com/vectorize-io/hindsight/blob/f8950b0c07d9e34c76493dba802bb309f0ce60fd/hindsight-api-slim/hindsight_api/api/http.py#L5762), `api_update_memory` 5762 | Curation handler calls `update_memory_unit`; response is memory data, not a mandatory mutation operation ID. No live completion guarantee. | STATIC / VERIFIED |
| P2 | [engine](https://github.com/vectorize-io/hindsight/blob/f8950b0c07d9e34c76493dba802bb309f0ce60fd/hindsight-api-slim/hindsight_api/engine/memory_engine.py#L11691), `update_memory_unit` 11691, `_reembed_memory_text` 11660, `initialize` 4997, `recall_async` 7893 | Local edit/re-embedding, invalidation/archive and conditional background submissions; initialization and recall paths. Does not identify historical effective settings or full send counts. | STATIC / VERIFIED |
| P3 | [OpenAI-compatible implementation](https://github.com/vectorize-io/hindsight/blob/f8950b0c07d9e34c76493dba802bb309f0ce60fd/hindsight-api-slim/hindsight_api/engine/providers/openai_compatible_llm.py#L392), `_usage_from_openai_response` 392, client construction 893, `verify_connection` 976, send loop 1249, successful tracing 1387 | Usage consumption, explicit retries and real startup probe; missing usage can become zeros. Does not prove endpoint usage/billing completeness or a row per send. | STATIC / VERIFIED |
| P4 | [native trace](https://github.com/vectorize-io/hindsight/blob/f8950b0c07d9e34c76493dba802bb309f0ce60fd/hindsight-api-slim/hindsight_api/engine/llm_trace.py#L407), `LLMTraceRecorder` 407, `_writable` 443, `_safe_write` 572, `stash_response_usage` 120; [API export](https://github.com/vectorize-io/hindsight/blob/f8950b0c07d9e34c76493dba802bb309f0ce60fd/hindsight-api-slim/hindsight_api/api/http.py#L10088), `api_list_llm_requests` 10088; [config](https://github.com/vectorize-io/hindsight/blob/f8950b0c07d9e34c76493dba802bb309f0ce60fd/hindsight-api-slim/hindsight_api/config.py#L1939), trace defaults 1939 | Existing bank/trace/scope/model/token/status export; best-effort persistence and limited retention. Not admission control or complete retry accounting. | STATIC / VERIFIED |
| P5 | [fact extraction](https://github.com/vectorize-io/hindsight/blob/f8950b0c07d9e34c76493dba802bb309f0ce60fd/hindsight-api-slim/hindsight_api/engine/retain/fact_extraction.py#L2085), LLM call 2085; [consolidator](https://github.com/vectorize-io/hindsight/blob/f8950b0c07d9e34c76493dba802bb309f0ce60fd/hindsight-api-slim/hindsight_api/engine/consolidation/consolidator.py#L3245), calls 352/3245 | Model-generating extraction and conditional consolidation paths. No fixed calls-per-native-operation ratio. | STATIC / VERIFIED |
| P6 | [embeddings](https://github.com/vectorize-io/hindsight/blob/f8950b0c07d9e34c76493dba802bb309f0ce60fd/hindsight-api-slim/hindsight_api/engine/embeddings.py#L440), `OnnxEmbeddings`, `initialize` 502, `encode` 568 | In-process ONNX, possible cache download at initialization. No measured invocation/cache size for this attempt. | STATIC / VERIFIED |
| P7 | [Jetstream inference overview](https://docs.jetstream-cloud.org/inference-service/overview/), “Why is this valuable” and terms, accessed 2026-10-12 | Public policy states no charge/no inference-service SUs for eligible communities. Does not supply historical usage receipts, experiment authorization or a per-token billing record. | DOCUMENTARY / VERIFIED; attempt accounting UNKNOWN |

**MISSING UNTRACKED EVIDENCE IMPACT:** Candidate10 private ZIPs, original
untracked Phase 06B evidence, private Phase 07 recovery files and external
LongMemEval oracle are unavailable. None blocks source inspection or internal
consistency checks of tracked reports. They prevent independent re-verification
of original raw exchange completeness, historical usage, private recovery
custody, and full dataset provenance. No claim in this audit implies those
artifacts were opened. Their absence is not permission to retrieve them or rerun
anything. The ignored migration report was not needed, copied or published.

## 3. Reuse-first implementation inventory

| Component | Classification | Reason and scope of reuse |
|---|---|---|
| `MemoryProviderAdapter` / command types (E9) | `DIRECT_REUSE` | Keep interface/native intent; no new adapter framework. Source inputs must also be preserved before command whitespace validation. |
| `UrllibHindsightTransport.request` (E1) | `REUSE_WITH_MINIMAL_PATCH` | Capture at the byte-read seam; wrapping its already-parsed return is too late. |
| Hindsight native methods/provenance hooks (E2) | `REUSE_WITH_MINIMAL_PATCH` | Keep payloads/ordering; add extraction, native identity and operation sidecars. |
| Config/package pin (E6) | `DIRECT_REUSE` | Reuse intended version/model choices; freeze and verify effective per-role/per-bank overrides separately. |
| Runtime ownership/fingerprints and harness selection (E7) | `DIRECT_REUSE` | Reuse retained environments conditionally on later validation; no installation in this audit. |
| Phase 04/06B launch shells/controllers (E8) | `REFERENCE_ONLY` | Existing lifecycle/attempt patterns suffice; their frozen workloads, installation paths and fixed output destinations are not a new-pilot execution recipe. |
| `storage_batch.run_repetition` and JSONL writer (E3) | `REFERENCE_ONLY` | Frozen scenarios/denominators and overwrite-capable `write_jsonl` must remain unchanged. Reuse concepts, not an unchanged rerun. |
| `LifecycleRunner` / trace observations (E4) | `REUSE_WITH_MINIMAL_PATCH` | Useful normalized events; protocol packet must additionally retain raw exchanges and actual completion evidence. |
| Authority/mediator/provenance contracts and `rq4-minimal-exact-v2` (E5/E9) | `DIRECT_REUSE` | Keep strict identity and fail-closed decisions. Add capture metadata beside the contracts. |
| Current durable raw/call/token accounting (E1/E3/H2) | `INSUFFICIENT` | No existing complete attempt ledger or exact exchange archive. |
| Native LLM request traces (P4) | `REUSE_WITH_MINIMAL_PATCH` | Export as corroborating evidence; independently reconcile sends and persistence. |
| Installed provider's present instrumentation/capacity | `UNKNOWN` | No live host/package/accounting inspection occurred. |
| Existing unit/contract/trace tests | `REFERENCE_ONLY` | Controlled interface evidence, not current live qualification. |

The inspected [unit tests](../../tests/unit/test_hindsight_adapter.py) cover
`test_native_edit_invalidation_inspection_and_document_delete` (line 50),
exposed observation parents and explicit derivation completion. The
[contract](../../tests/contract/test_hindsight_provider.py) uses
`FakeHindsightTransport`; the [trace tests](../../tests/unit/test_hindsight_lifecycle_trace.py)
exercise known/unknown lineage and zero downstream execution.
The [integration test](../../tests/integration/test_hindsight_adapter.py),
`test_real_retain_recall_inspect_and_invalidate` (line 23), is opt-in and
contacts the service. H1 records its historical pass; it was not run here.
No inspected test establishes exact persisted HTTP bytes or complete costs.

## 4. Exact-byte capture data flow and loss points

Five distinct products must remain identifiable: (1) body bytes returned by
the client read, (2) parsed application objects, (3) selected candidate content
UTF-8 bytes, (4) canonical proposition bytes, and (5) final context bytes.
An escaped JSON string's lexical bytes need not equal its decoded text's UTF-8
bytes. A frozen extractor can produce layer 3 from layer 1 with an explicit
JSON pointer, charset and transformation record. This does not capture TLS,
HTTP framing or original compressed transfer bytes; record content encoding
and the actual client boundary without claiming lower-layer visibility.

| File/function | Input → output | Preserved | Transformed/discarded; existing capture | Smallest future hook |
|---|---|---|---|---|
| E1 `request` request construction | method/path/query/payload → `Request` | Native endpoint and payload intent | `json.dumps(...).encode('utf-8')`; serialized request not retained | Preserve exact outbound body, safe metadata, local request ID and attempt/condition/repetition before send |
| E1 `request`, successful `response.read()` | HTTP response → `bytes` → parsed JSON | Complete returned body exists transiently in `raw` | Status/headers/body/capture time are not persisted; UTF-8 decode and JSON parse remove lexical representation | Write exact read bytes exclusively before parse; hash/count/status, allowlisted headers, encoding and timestamps |
| E1 HTTP/transport errors | `HTTPError`/network failure → exception | HTTP error code and interpreted detail | Error bytes decoded with replacement, detail simplified; network error has no complete body | Capture error body before decode; mark incomplete reads/timeouts explicitly and retain original failure classification |
| E2 `query` | parsed mapping → ordered `MemoryRecord` tuple | Native ID, returned relative order, selected surfaces/parent IDs | Non-mappings/blank texts removed; `records[:limit]`; envelope fields and original positions lost; missing `results` defaults to empty | Inventory every raw result and disposition before filtering/truncation; retain raw index and selected rank separately |
| E2 `_normalized_record`; E9 `MemoryRecord` | native item → normalized record | ID, text-derived content, state, curated metadata | `str(...).strip()` and whitespace-constrained types; state defaults valid; revisions reduced to 1/2 from edited timestamp; unspecified fields discarded | Save untrimmed decoded field bytes and normalized bytes, exact extraction rule/version and both hashes; do not change adapter semantics silently |
| E4 lifecycle/trace observation | tuple of normalized records → observation/trace | Normalized contents in memory; IDs/events, optional sanitized content | Trace default stores no text; sanitization is not raw evidence | Reference captured exchange/candidate artifacts and record relation basis per edge |
| E3 `_retrieval_payload` → `write_jsonl` | normalized records → dicts → JSONL | Normalized UTF-8 SHA-256, selected ranks, IDs, surfaces, parents, event correlations | Candidate content omitted; raw response omitted; JSONL is reconstructed evidence metadata | Add capture-manifest references beside frozen-compatible data; every required artifact must commit before eligible classification |
| E5 `CandidateEnvelope` / policy | separately constructed envelope + byte map + independent bundle → decisions/context | Independently verified candidate hash, binding and ordered allowed bytes | Envelope contains hashes, not content or extractor; no automatic live Hindsight-to-RQ4 conversion exists | Build envelope from captured artifacts; construct binding after capture using preregistered algorithm and independent evidence |
| E5 `_frame_allowed_content` | approved candidate byte map → length-framed context | Exact allowed payloads in deterministic frames | Adds framing; distinct context hash; absent in historical H2 (`delivered_context_sha256=null`) | Capture serialized context only under its separate authorization; RQ3 remains disabled |

`query` can return `()` without an HTTP request when ACTIVE is excluded. That
is not a captured provider-empty response. A missing `results` field or silently
filtered malformed row also cannot support a condition-specific null finding.
Future completeness validation must distinguish these cases from an explicitly
valid, fully captured empty result list. Limiting selected results cannot justify
a claim about every candidate in the response; the packet needs the complete
raw-result inventory even when mediation uses only a declared selected subset.

H2 serializes candidate bytes for **0/37** final occurrences. Fifteen match
known tracked source hashes; six more match H3 recovery bytes, giving the
unchanged **21/37**, with **16/37 hash-only**. Hindsight contributes 24 final
occurrences, including the six recovered S1 derived occurrences. That recovery
does not restore original response bodies or missing extraction metadata.

Two additional STATIC / VERIFIED limits matter for completeness: E3
`_safe_inspect` (395) converts inspection exceptions to an empty tuple, so an
empty inspection cannot prove complete source-state evidence. E2's descriptive
`native_operation_for('QUERY')` says world + experience only, while the actual
`query` payload includes observation. The recorded label must not be used as
proof of the surfaces requested; preserve the actual payload in future capture.

## 5. Native update and revoke capability matrix

| Dimension | Family U — same-ID curation | Family R — native invalidation |
|---|---|---|
| Implemented API (STATIC / VERIFIED) | E2: GET target; snapshot operations; PATCH `/memories/{id}` with `text`; normalize response | E2: GET target; snapshot operations; PATCH same native ID with `state=invalidated` and reason; normalize response |
| Actual target/version identity | Native source ID retained; independent v1/v2 event/version IDs required; no native supersession edge | Same source ID becomes invalidated; do not replace with DELETE or call invalidation hard deletion |
| Deterministic test evidence | E9 tests assert same ID/revision and edit path with fake transport | Fake tests assert REVOKED and recall absence; no proof of all live derived surfaces |
| Historical real-provider evidence | H1 correction/supersession CURRENT_ONLY; H2 `freeze-v1__hindsight__S1__r1`, r2, r3 SUCCESS/CURRENT_ONLY | H1 revocation ABSENT; H2 `freeze-v1__hindsight__S5__r1`, r2, r3 SUCCESS/ABSENT |
| Response success and completion | Adapter accepts mapping; does not separately assert returned ID/text against target or retain raw success status. Queue metadata exists, not full mutation completion payload | Adapter accepts mapping; state normalization maps invalidated to revoked but no explicit fail-closed assertion that requested invalidated state was returned; raw response absent |
| Background observations | H2 records two operation IDs after each update; H3 independently binds current-v2 derived content | H2 records two operation IDs after each revoke; no final candidate in each run; original empty HTTP bodies not preserved |
| Historical source preservation | Independent frozen ledger retains v1/v2 identities/hashes; same native object is edited. `history_for` is observation history, not source version history | Invalidated source can be listed; this is distinct from deletion. Exact historical archive payloads are not reproduced by H2 |
| Derived attribution and authority | Native parents plus adapter correlation can carry superseded ancestry; H3 proves current Bob proposition, not stale Alice | Parent evidence must be captured if retrieval returns derived content; absence in these queries is not universal absence |
| Final capability conclusion | READY for native operation only; future schedule content not historically demonstrated | READY for native operation only; recipient/schedule revoke conditions not historically demonstrated |

H2 update r1 records operation IDs
`0c9738f8-7287-4312-ac55-ad6311ea4385` and
`2c9402d0-b2c2-4480-bb00-4b55fc61e88b`; revoke r1 records
`228dcf6e-50f1-451a-b05b-ffd70d66c47d` and
`99761148-3884-4d1a-8d15-c139c182beba`.
These are observed async IDs, not a separately named synchronous PATCH
operation receipt. All six mutation steps have recorded SUCCESS.

**STATIC / VERIFIED:** P1 returns memory data from synchronous handler work.
P2 permits background consolidation/maintenance after mutation; submission
failure can be logged without failing the memory response. Therefore native
transition validity and subsequent derived-state completion need separate
evidence. Hindsight supports the proposed native families; a success mapping
alone cannot instantiate independent source authority under the protocol.

## 6. Completion and quiescence assessment

E2 `_wait_for_operation` targets an explicit consolidation ID, accepts only
`completed`, rejects `failed`/`cancelled`, and times out otherwise. It returns
the parsed terminal payload, but the adapter stores only compact metadata.
Its “submitted” timestamp is when polling starts, not proof of native submission
time. This is useful reuse, with raw submit/status payload capture still required.

`wait_for_quiescence` is weaker:

- `_list_operations` requests only limit 100 / offset 0 and treats 404 as `[]`.
- It excludes all pre-existing IDs, even if those operations remain active.
- Only `pending`/`processing` block; only `failed` is explicitly rejected.
  Cancelled or unrecognized statuses may appear quiet.
- Seen IDs are collected only while active; already completed work may never
  enter the recorded set. No terminal payload per ID is persisted.
- One quiet poll ends the gate. `_last_operation` is reused in later query or
  reset metadata, so repeated timestamps/IDs are not fresh completion receipts.
- Request timeout (120 s) and polling deadline (default 300 s; historical
  override 600 s) are different controls. A blocking request can outlast the
  remaining polling deadline; these are not strict end-to-end ceilings.

**VERIFIED** limits are in E2 and recorded in H2. **UNKNOWN:** whether every
relevant background queue/task/trace write is represented by the operation
listing in the installed runtime. No quiet queue proves universal semantic
stability. Future verification must establish task coverage and mapping, not
merely add an arbitrary sleep or repeated quiet polls.

Minimum future gate: save mutation response/post-state, enumerate all relevant
operations/pages including baseline pending work, track known IDs to explicit
terminal success, reject absent/malformed/unknown/error status evidence, capture
deadline/failure payloads, and reconcile background trace writes before closing
a condition. A preregistered stable-empty criterion is necessary only if justified
by the verified queue semantics; it cannot substitute for missing task coverage.
These changes affect when observation occurs and must be separately approved
and frozen for a new attempt. Historical polling/evidence remains unchanged.

## 7. Internal model and embedding call-path audit

E6 verifies `openai` / `gpt-oss-120b`, ONNX /
`intfloat/multilingual-e5-small` / 384 dimensions, and RRF. No local hosting
of the 120b text model is implied. Reflect is unused and batch retain is disabled.

| Path | Model activity and evidence | Accounting implication/status |
|---|---|---|
| Startup/initialization | P2/P3: conditional verification invokes an actual text call; P6 loads local embedding assets and may download missing cache files | Count startup before scientific conditions; native bank trace may skip it before DB readiness (P4). Exact historical count UNKNOWN |
| Source retain/fact extraction | E2 sends synchronous retain; P5 extraction calls LLM on applicable chunks; embeddings process extracted facts | Text calls conditional on successful extraction path; neither one write nor one document implies one send |
| Same-ID text curation | P2 re-embeds edited source; no fact-extraction replay credited for text-only curation | Local embedding work; conditional subsequent consolidation text calls; actual count UNKNOWN |
| Invalidation | E2/P2 native state change; no direct text generation credited to state-only mutation | Conditional dependent-state/background activity; do not assert one LLM call per revoke |
| Recall | E2 types world/experience/observation; P2 query embedding; E6 RRF; no reflect request | Local query embedding, not hosted embedding; no direct generative call identified for the configured ordinary recall path; concurrent background activity is separately attributable |
| Observation/consolidation | E2 native consolidation; P5 generation/dedup call sites and embedding work | Text and local embedding counts depend on pending sources/state and branches, not HTTP count |
| Quiescence/readiness polling | E2 GET health/version/operations/status | Adapter itself invokes no model; workers may continue during polling; polls are not internal model calls |
| Restart/failure/retry | E7 owns service restart; P3 has retry loop with SDK retries set to zero in inspected source | Reinitialization probes, provider retries and worker retries require separate send records; actual installed SDK/source behavior must be verified |

“Guaranteed by code” means that when a cited branch is reached it invokes the
identified call/embedding function. It is not a guarantee that the branch ran
historically or runs for every native request. Conditional configuration,
pending state, failures and retries prevent exact static usage totals.

## 8. Historical usage evidence and missing accounting

H2 contains 18 Hindsight runs, all SUCCESS. It records **21 WRITE, 3 UPDATE,
3 REVOKE, 33 QUERY**, plus reset/inspect/delete/restart/derivation operations.
These are adapter lifecycle-event counts, not internal model-send or embedding
counts. HTTP polls and secondary requests make even adapter events differ
from HTTP request totals.

H1/H2 record provider/model identity and operation timing but no complete
internal request IDs/counts, token receipts, retries, failed-send usage,
background totals, embedding invocations, cache hits/misses or billed amounts.
All such historical quantities are **UNKNOWN**, not zero. H2 does explicitly
record zero downstream/RQ3 calls; H3 recovery also records zero provider model
calls for its read-only recovery path. Those zeros do not imply zero internal
model activity in the original Hindsight lifecycle runs. Candidate10's 21
Honcho calls are unrelated and are not imported into Hindsight accounting.

P4 native tracing offers bank/operation/scope/trace/span/model/status/token
fields and paginated API export. Inspected defaults enable all scopes but keep
traces one day; actual historical configuration/export is unknown. Persistence
is fire-and-forget/best-effort, can skip before DB readiness, and logs write
failure without failing the provider operation. Prompt/output material may be
stored and must remain private. Retry usage can be overwritten by the last
response (P4); P3 records success after its retry loop and maps absent usage to
zero. Consequently native trace rows alone cannot be counted as every attempted
send or accepted as complete billable token evidence.

## 9. Cost formula, measurement and enforcement

Let S be every attempted provider-internal text send, including retries,
startup and attributable background work. For each send s, preserve measured
billable token categories `I_s`, `O_s`, any separately billed category `X_s`,
their endpoint/model/rate-version identities, and a usage-present flag. With
rates expressed per token:

```text
Cost_text = sum over s in S of
            (I_s * r_input,s + O_s * r_output,s + X_s * r_other,s)
Cost_total = Cost_text + other independently verified billable charges
```

If a verified tariff is per million tokens, divide its rate by 1,000,000 first.
Cached/reasoning tokens must follow the endpoint's verified billing definitions:
do not count them twice if included in prompt/completion totals. A failed or
unreceipted send has UNKNOWN usage until reconciled; absence is not zero.
Local embedding invocation/text/batch counts and CPU time are separate resource
units, not hosted text or embedding fees. VM allocation SUs are also distinct.

P7 independently documents no inference charge and no inference-service SUs
for eligible communities. This is stronger than mere course authorization,
but is a public policy statement, not a measured historical cost ledger or an
approved budget for this attempt. No dollar amount is assigned. Effective
entitlement, applicable terms, billable categories and future accounting
remain to be pinned/approved. Provider code can consume usage fields, but
whether the course endpoint supplies complete trustworthy usage—including
failures/reasoning/retries—is **UNKNOWN** without separately authorized
verification. The documentation inspected does not provide that receipt.

### Minimum accounting controls — PROPOSED / INFERRED

Reuse native tracing as corroboration. Add a small provider-runtime ledger at
the existing OpenAI-compatible **actual-send boundary**, installed before
initialization; reuse its HTTP client rather than add a proxy/service/database.
The harness REST transport sees no internal sends and is insufficient here.
Every retry must re-enter admission, and unknown endpoints/models must be
rejected. A provider-level `call()` counter alone misses retry multiplicity.

Persist a reservation before send and a completion/failure record afterward:
attempt/condition/repetition, startup-versus-condition category, native bank,
operation/trace/scope where exposed, local send ID, provider request ID if
present, model/endpoint class, status, retry ordinal, usage-present flag, raw
usage categories and timestamps. Missing IDs remain explicitly unavailable.
Use exclusive artifacts and a lock shared by all provider workers/processes.
One namespace per condition/repetition plus serialized condition progression
helps attribution; time windows alone do not prove causality. Map worker/task
IDs where available and mark unassigned background calls explicitly. Reconcile
pending sends, operation IDs and native trace exports before closing a case.

Add local ONNX counting at `encode`/batch boundaries; report invocations, batches
and text counts separately. Track observable cache loading/hits only at a
verified cache boundary. Do not manufacture cache statistics from elapsed time.

A call ceiling can be enforced before sends with atomic reservations across
foreground/startup/background/retry paths. A strict token/cost ceiling additionally
requires a verified upper bound on billable input and output per admitted send,
including reasoning and in-flight reservations:

```text
admit only if committed_usage + outstanding_reservations
              + verified_new_send_upper_bound <= approved_ceiling
```

Post-response token totals cannot prevent an overrun already incurred.
`recall.max_tokens=4096` limits retrieval output, not provider LLM consumption.
Timeouts, retry caps and a no-charge policy are not token-budget enforcement.
If an input/output bound or usage contract cannot be verified, stop before
experimental sends; do not declare a bounded token budget. Changing retry
behavior, output caps or worker scheduling is a scientific configuration change
requiring approval, not an invisible accounting patch.

## 10. Infrastructure and storage feasibility

H4 records `jisheng3`, m3.small, 2 vCPU, approximately 5.78 GiB RAM, no GPU,
Ubuntu 24.04 and persistent `/dev/sdb`. H1 records Hindsight service/ONNX,
curation/revocation, restart and retained isolated environments operating
successfully on that historical target. This supports reuse-first feasibility,
not current acceptance or a guaranteed peak memory margin.

H5 supplies actual measurements: preflight persistent free bytes
**45,750,427,648**, root free bytes **4,588,425,216**; diagnostic line 1,
2026-10-02T00:05:50.223981Z, system `MemTotal_kib=6,057,500`,
`MemAvailable_kib=5,058,688`, swap total/free zero. These precede **OpenViking**
startup and cannot establish Hindsight peak RSS or present availability. H4's
`49G` is reported volume **capacity**, not measured current free space.

| Resource | Established | Unresolved future measurement |
|---|---|---|
| CPU/RAM | Small CPU-only VM historically ran pinned Hindsight; ONNX local, hosted text model | Provider + pg0 + harness peak RSS, available memory, CPU time and capture-write overhead; no arbitrary minimum or utilization percentage assigned |
| Environments | H1 reused provider and clean harness with fingerprint/pip-check gates | Continued existence, source/wheel identity and current dependency health, validated only in a separately authorized preflight |
| Database/cache | Historical retained persistent pg0/model caches; P6 may download missing assets | Current cache sizes, model file hashes/revisions, missing-cache policy and database/WAL growth |
| Capture storage | Additional response/candidate/log files necessarily consume bytes | Complete response limits, request/poll/send ceilings, log growth and disk free space; no empirical size measurements here |

For a frozen future maximum request count `N_http`, per-body cap `B_http`,
candidate artifact count/cap `N_cand,B_cand`, and explicitly approved metadata,
log, internal-ledger, DB/WAL and cache-growth byte ceilings:

```text
D_required = N_http * B_http + N_cand * B_cand
             + B_metadata + B_logs + B_internal_ledger
             + B_db_wal_growth + B_cache_growth + B_reserved_free
```

Count duplicated body/candidate artifacts and per-call artifacts explicitly;
do not use an arbitrary multiplier. All ceiling values are currently UNKNOWN.
Admit only if fresh free bytes satisfy this sum on the authoritative volume.
`N_http` includes operation/status pages, errors and polls; poll deadlines alone
do not fix a safe maximum file count. Bound accumulated bytes/counts and stop
on oversized responses, partial reads or write failure. Do not silently truncate
and classify the response as complete. Streaming to a private artifact could
reduce future read-buffer pressure, but needs parity/timing validation; current
`response.read()` loads the complete body before parse.

A later authorized preflight may resolve the mount dynamically, measure free
bytes, cache/DB sizes and resource headroom, and validate limits. No OpenStack,
infrastructure SSH session, VM state query, remote DB inspection or service
startup occurred here. Git used the configured SSH repository transport for
authorized remote-ref checks/fetch/publication; it did not connect to Jetstream.
No new VM, GPU, provider or logging infrastructure is justified by current
evidence. macOS RAM/CPU are audit-host facts, not substitution for the remote
provider's measured resource profile.

## 11. Four-condition readiness matrix

The accepted protocol's four independent conditions remain distinct from its
proposed three repetitions per condition. No exact new source/control/query
packet or independent review was produced by this audit.

| Gate | U-A recipient update | U-B schedule update | R-A recipient revoke | R-B schedule revoke |
|---|---|---|---|---|
| Native operation | STATICALLY_SUPPORTED + historical family U | STATICALLY_SUPPORTED; new semantic input untested | STATICALLY_SUPPORTED + historical family R | STATICALLY_SUPPORTED; new semantic input untested |
| Exact response/candidate capture | Needs E1/E2 patch | Same | Same | Same |
| Provenance/completion | Needs basis/version sidecars and strengthened gate | Same | Needs invalidation post-state and background gate | Same |
| Authority preregistration | Exact inputs/queries/control packet not frozen here | Schedule proposition/control still pending approval | Target and matched active control not frozen here | Schedule/control still pending approval |
| Candidate binding | Existing E5 interface; future bytes/binding not available | Same | Same | Same |
| Call/token/cost gates | Complete sends blocked; token/cost receipts unresolved | Same | Same | Same |
| Current resource ceiling | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Scientific controls | Old/current query opportunity proposed; current-v2 with stale ancestry must remain authorized | Same structure; semantically independent schedule input | Separate matched active control proposed; captured null distinguished from missing bytes | Same structure; exact schedule control pending |
| Overall Audit E condition class | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` |

The narrower capture defect is `NEEDS_MINIMAL_CAPTURE_PATCH`; the overall
condition is BLOCKED because accounting and approvals cannot be solved by
claiming that the native endpoint exists. No null result is a security negative
control, and no current proposition with stale parents becomes unauthorized.

Protocol §10.2 is sufficient for the limited alternatives comparison: Mem0
2.2.1 supports update/delete but not native revoke; OpenViking 0.4.22 lacks
external update and revoke; Honcho is frozen NO_GO. Substituting delete for
revoke changes the approved factorial. Hindsight remains provisionally preferred
because one existing provider supplies both families, reducing a provider-by-
transition confound. This is an inference from existing capability evidence,
not final provider selection or revival of the blocked expansion.

## 12. Minimal future implementation delta — design only

No implementation, test, manifest or historical evidence file is changed by
this phase. The following bounded proposals reuse existing files/seams; all
are required before an empirical pilot except optional separately authorized
context serialization. No new adapter framework, database, orchestration
framework, annotation application or broad test suite is proposed.

| Delta / existing boundary | Requirement and smallest change | Added evidence / privacy | Runtime, tests and semantic risk |
|---|---|---|---|
| D1: adapter `UrllibHindsightTransport.request` (E1) | Optional attempt-scoped byte sink before success/error decoding; exclusive write, hash/count/status and failure disposition; record outbound body and safe metadata | Exact client-body artifacts including non-JSON/errors, request correlation; private storage, allowlisted headers, no authorization/cookies/secrets | Additional I/O and possible timing effect; targeted offline tests for exact whitespace/Unicode/escapes, empty/error/malformed/timeout/partial read, write failure and collision; parity of returned objects and exceptions |
| D2: adapter `query`/`_normalized_record`, runner extraction boundary (E2/E3/E4) | Capture every native item/index and explicit selected/discarded mapping; raw decoded field UTF-8 and normalized bytes; transformation/version references and relation basis | Candidate bytes, ranks, surfaces, native parents and independent source/event/version sidecars; raw originals private, redacted public derivatives separately hashed | No changed filtering/order/text semantics; tests for invalid/blank rows, missing results, limits, Unicode/whitespace and complete null evidence |
| D3: adapter mutation methods/polling (E2) | Verify target ID and requested post-state; save raw success/terminal evidence; full operation pagination, baseline pending handling and explicit unknown/cancelled/failure classification | Mutation receipts, per-ID status and actual polling timestamps; safe errors without secret bodies in public output | Observation timing changes require approved criterion; tests for page overflow, 404, pre-existing pending, instant completion, failed/cancelled/unknown states, late tasks and timeout |
| D4: `scripts/jetstream/phase04_runtime.py`, `HindsightServiceController.start`; provider client/initialization boundary (P3/P4/P6) | Launch through a small attempt-scoped provider entrypoint that installs private per-send admission/receipt hooks before initialization; native trace export/reconciliation; count ONNX operations separately; atomically reserve across worker/send/retry paths | Send/retry/request IDs where available, usage-present/raw categories, task/condition attribution and export hashes; retain secrets/prompts outside public report | Completeness still UNKNOWN until verified against installed source/all send paths; no new service; targeted mock-provider tests for startup, concurrent background/retry sends, trace write loss, missing usage, reasoning/cache categories and boundary exhaustion |
| D5: reuse `scripts/jetstream/phase06b.py` `_write_local_result` exclusive-output pattern and `phase06b_remote.py` `validate_pre_experiment_environment` guard pattern at a separately approved new-pilot boundary; E5 `AuthorityBundle` | Use exclusive new attempt root, effective config/role/bank/source/hash gate, storage/resource limits and protocol outcome precedence; immutable preregistration then post-capture bindings; stop before next condition on any failed gate | Frozen input/config hash, byte inventory/completion record, independent binding evidence and private/public map | Reuse lifecycle ownership and contracts; do not run/change frozen Phase 06B plan. Focused offline checks for source version attribution, forbidden self-binding, artifact corruption, config mismatch and failure denominator exclusion |

D4 cannot be replaced by D1 or by merely enabling native trace export. Verify
installed SDK retry behavior and every outbound path; prohibit uninstrumented
fallback endpoints. A local admission rejection must propagate as a terminal
budget stop instead of becoming a retryable provider exception. No global
monkeypatch, retry-disable decision or output-token setting is assumed safe
without review. Existing worker ownership/context and HTTP-client seams are
preferred; if they cannot cover sends atomically, return to scientific review
with that specific limitation instead of introducing new infrastructure.

## 13. Scientific failure-mode audit

| Mode | Existing protection / remaining change | Finding |
|---|---|---|
| A: transient response discarded | E1 no sink; D1 necessary | VERIFIED gap |
| B: normalized text differs without transform | E2/E9 stripping and E3 hash; D2 necessary | VERIFIED gap |
| C: same-ID update loses version attribution | E5 ledger keeps independent intent; native ID is not version; D2/D5 preserve independent v1/v2 | Partial protection; native version edge unavailable |
| D: invalidation success precedes derived completion | E2 polls; incomplete status/task coverage; D3 | Partial protection |
| E: background LLM calls unattributed | No attempt send ledger; P4 bank traces insufficient; D4 | BLOCKED |
| F: unavailable usage called bounded budget | Missing usage can become zero in P3; D4 must retain UNKNOWN and reject unbounded admission | VERIFIED gap; enforcement UNKNOWN |
| G: local embeddings called hosted LLM | E6 pins ONNX; D4 separate invocation/text/batch units | Config distinction supported; counts UNKNOWN |
| H: restart/timeout enters valid denominator | E3 records ERROR; new protocol requires infrastructure/invalid/indeterminate precedence and no retry | Partial protection; D5 |
| I: hash-only treated as bytes | E5 exact binding/policy, accepted exclusions protect pilot; D1/D2 completeness required for future capture | Pilot protection verified; historic bytes remain missing |
| J: inferred relation called native | E4 some association basis; E3 source-event correlation includes experiment mappings | Partial protection; D2 explicit basis and witnesses |
| K: successful retrieval then storage failure | Current transport has no durable evidence commit; D1/D5 fail closed before eligibility/next condition | VERIFIED gap |
| L: current content with stale ancestry denied | E5 policy and H3 current-v2 evidence; preserve existing false-positive control | Existing policy protection; no newly adjudicated human label |
| M: substituted version/model/config | E7 version/config guards and E2 `/version` help; full effective role/bank/source/model-cache identity not covered | Partial protection; D5 |
| N: hook changes ordering/bytes/timing | No new hook implemented; D1–D4 parity/timing checks needed | Future operational capability UNKNOWN |
| O: partial audit promoted to approval | Protocol gates, separate verdicts and recommendation D forbid promotion | Explicit governance control |

Outcome precedence follows protocol §8: unsupported capability, infrastructure
error, invalid attempt, indeterminate, then conclusive exposure/absence where
all evidence gates pass. Stop on partial capture, unsafe budget admission,
unexpected endpoint/model, lost completion evidence or corrupt artifact;
preserve failed attempts and exclude them from conclusive denominators.
No automatic retry, source repair, replacement repetition or extra exploratory
condition follows from failure or null observations.

## 14. Validation and publication boundary

Offline validation used standard-library JSON/JSONL/hash/AST/path checks without
importing project/provider/model modules. Results:

- PASS: required main SHA after `git fetch origin`; remote main verification;
  clean assigned/primary checkouts; correct repository remote and worktree.
- PASS: canonical Freeze-v1 Git-source CRLF SHA-256
  `0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b`.
- PASS: frozen `configs/hindsight-phase04.json` Git-blob bytes reproduce
  SHA-256 `baca300bdce174d8cb2d00fa576df73d0cf5c4f9230aed370d2767bd35f4d73d`;
  all Hindsight rows/manifest agree. This is the file identity, not the hash of
  the adapter's separately shaped configuration dictionary or reserialized JSON.
- PASS: 42 unique combined run IDs, 41 SUCCESS / one frozen OpenViking ERROR;
  18 Hindsight rows; six native U/R successes and exact run/operation references.
- PASS: 37 final candidates; 15 source-hash matches + six recovered occurrences;
  H3 UTF-8 hashes/native IDs/parent IDs match H2 for all three recovery targets.
- PASS: cited local paths, source symbols/line references and pinned upstream
  blob identities; symbolic formula units and explicit UNKNOWN bounds checked.
- PASS: source/expected-label freeze precedes provider observation; candidate
  hashes/bindings follow capture; evidence classes and human review status remain
  separate; all verdicts reference their supporting evidence and limitations.
- PASS: Markdown relative links and anchors checked; `git diff --check`;
  report secret/private-evidence review. Only this report is added. No private
  archive, migration report, credential or reconstructed historical artifact is
  included. Linked sources are already tracked or public first-party material.
- `NOT_RUN — DEPENDENCY_UNAVAILABLE`: pytest/Pydantic-dependent unit and contract
  validation; both unavailable in the selected Python and project `.venv` absent.
  Inspected tests are not reported as newly passing. No dependency installed.
- `NOT_RUN — NOT_AUTHORIZED`: live integration, provider/model/embedding execution,
  endpoint usage verification, Jetstream inspection and four-condition pilot.
- PASS: final diff scope, source/freeze/evidence preservation and unchanged
  primary checkout checked before publication.

Publication is one report commit and a normal push to the required review
branch, with remote HEAD verification; no PR, merge or force push. The published
commit is recorded in the conversation handoff after Git returns its identity,
avoiding a self-referential hash in this document.

## 15. Final recommendation and authorization decisions

Keep Hindsight **provisionally preferred**. Recommendation **D** applies to
present execution readiness; the specific D1–D5 path may support recommendation
**B** after independent completeness and budget-enforcement verification.
Preserve **Retrieved != Authoritative**: native source state, raw candidate
content, independent proposition binding and authority are separate evidence.
No unauthorized-content exposure was discovered or manufactured in this audit.

Main Research Agent decisions remain:

1. Approve the bounded future capture/completion/accounting patch scope and its
   focused offline verification; decide whether its actual-send gate can cover
   startup, workers, retries and unknown usage without changing native semantics.
2. Approve effective pinned runtime/model/source/cache identity and call/token/
   cost/storage/resource ceilings only after missing quantities are established;
   decide whether public no-charge policy suffices for the monetary gate while
   preserving measured usage and finite call/token/resource limits.
3. Approve exact second proposition, controls, queries, repetitions and justified
   completion criterion; complete the two-human-review/adjudication prerequisites.
4. Select Hindsight finally only after these evidence gates pass. Any further
   operational verification or empirical/provider/Jetstream lifecycle needs
   separate authorization. RQ3/model-boundary serialization remains separate.

**READY FOR MAIN CHATGPT SCIENTIFIC REVIEW:** YES, as a completed static audit.
**READY FOR EMPIRICAL EXECUTION:** NO. Next authorized action after review-branch
publication is scientific review and corrections in this same conversation.
No recommended patch is implemented. Stop after publication.
