# Phase 07 — Scientific Decisions and Recovery Plan

> **Protocol Phase:** `07C-HINDSIGHT-S1-RECOVERY-SCIENTIFIC-CLOSURE`
> **Status:** `SCIENTIFIC_CLOSURE_RECORDED`
> **Governing Principle:** *Retrieved != Authoritative*
> **Live Execution:** `NOT AUTHORIZED`
> **RQ3 Execution:** `NOT ACTIVATED` (0 calls executed; 0 empirical eligible contexts)
> **Jetstream Status:** `SHELVED`
> **Git Push:** `NOT AUTHORIZED`

---

## 1. Executive Frame and Decision Summary

This document records the approved scientific interpretations and classifications established by Main ChatGPT for the Phase 07 residual cells and RQ3 experimental frame. In accordance with project governance, these classifications represent binding scientific interpretations and decision gates, strictly separated from empirical observed evidence and open questions.

### Approved Scenario Classification Summary

| Provider & Scenario | Main ChatGPT Approved Classification | RQ3 Eligibility | Relevant Research Questions | Recovery / Advancement Gate |
| :--- | :--- | :--- | :--- | :--- |
| **Mem0 S1** (`SUPERSESSION_OR_UPDATE`) | `PROVENANCE_LINEAGE_RESIDUAL` | **`NO`** | RQ1, RQ2, RQ4 | In-place update retains only `v2` content; mixed authority arises from retained lineage. Excluded from RQ3 stale-content downstream testing. |
| **Hindsight S1** (`SUPERSESSION_OR_UPDATE`) | `PROVENANCE_LINEAGE_RESIDUAL_CURRENT_CONTENT` | **`NO`** (Provisional `RQ3_CANDIDATE` retired) | RQ1, RQ2, RQ4 | Exact recovery (attempt `20261003T003809Z-7a3425bf2f4c`, `PASS`) proved derived candidate text is current `v2` content (`Project Alder reports may be sent only to Bob.`), not stale `v1`. Ineligible for RQ3; serves as RQ4 negative control. |
| **Hindsight S4** (`HARD_DELETE_REDERIVE`) | `LEGITIMATE_REDERIVATION_CANDIDATE` | **`NO`** | RQ2 | Derived state is reconstructed from surviving authoritative `write-support` source after `v1` deletion. No deleted-`v1` lineage demonstrated. Excluded from RQ3. |
| **OpenViking S4** (`HARD_DELETE_REDERIVE`) | `F2_DERIVED_STATE` / `ROOT_CAUSE_UNRESOLVED` | **`NO`** | RQ1, RQ2 | Cross-repetition variability at derived state production (r1: present, r2: none, r3: present). Exposure is `AUTHORITATIVE_ONLY` or `NONE`. Excluded from RQ3. |
| **OpenViking S0** (`RETAIN_QUERY_NO_LIFECYCLE`) | `EXCLUDED` | **`NO`** | Historical baseline | Preserved historical provider crash in r2 (`RemoteDisconnected` / `ServiceExitedBeforeReady`). Invariant: never rerun or replaced. |

---

## 2. Cell-by-Cell Scientific Decisions

Each cell analysis explicitly separates **Observed Evidence**, **Main-ChatGPT Scientific Interpretation**, and **Unresolved Questions**.

### 2.1 Mem0 S1 (`SUPERSESSION_OR_UPDATE`)

#### Observed Evidence
- **Runs Analyzed:** `freeze-v1__mem0__S1__r1`, `freeze-v1__mem0__S1__r2`, `freeze-v1__mem0__S1__r3` (Attempt `20261001T183940Z-1fc4c4929532`).
- **Retrieved Content:** Single candidate returned at rank 1 in both `final-old` and `final-new` queries across all 3 repetitions.
- **Content Identity:** In all 3 repetitions, the single retrieved candidate contains **only current `v2` content** (`Project Alder reports may be sent only to Bob.`). No text representing superseded `v1` exists in storage or was retrieved.
- **Authority Exposure Outcome:** Classified in Phase 06B as `AUTHORITATIVE_AND_NONAUTHORITATIVE`.
- **Lineage Attribution:** The adapter associates the single updated provider object with both `write-v1` (superseded, non-authoritative) and `update-v2` (active, authoritative) because Mem0 modifies the record in-place without generating a distinct replacement entity.

#### Main-ChatGPT Scientific Interpretation
- Mem0 S1 is **NOT an RQ3 stale-content context**.
- **Reason:** Retrieval contains current `v2` content only. Its mixed authority classification originates entirely from provenance/lineage linking the same updated provider object to superseded `v1` and active `v2`.
- **Classification:** `PROVENANCE_LINEAGE_RESIDUAL`.
- **RQ3 Status:** `NO`.
- **Relevant RQs:** `RQ1` (exact vs derived authority exposure), `RQ2` (lifecycle failure localization), `RQ4` (defense efficacy on provenance tracking).

#### Unresolved Questions
- How should lineage-aware authority filters evaluate single-object in-place updates when the textual content is fully authoritative but the historical object identity predates the superseding transition?

---

### 2.2 Hindsight S1 (`SUPERSESSION_OR_UPDATE`)

#### Observed Evidence
- **Runs Analyzed:** `freeze-v1__hindsight__S1__r1`, `freeze-v1__hindsight__S1__r2`, `freeze-v1__hindsight__S1__r3` (Attempt `20261001T183940Z-1fc4c4929532`).
- **Retrieved Candidates:** In all 3 repetitions, queries retrieved exactly 2 candidates:
  - **Rank 1 (Source):** Curated in-place updated `v2` content (`Project Alder reports may be sent only to Bob.`).
  - **Rank 2 (Derived):** Provider observation fact produced during initial write (`fact_type = observation`, `surface = DERIVED`), linked to `write-v1`.
- **Derived Candidate Hash:** Identical across all 3 repetitions: `SHA-256 = f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6`.
- **Completed Exact Context Recovery:**
  - **Corrective Recovery Attempt:** `20261003T003809Z-7a3425bf2f4c` (`STATUS: PASS`, Completion marker: `VALID / PASS`).
  - **Source Tree Continuity:** Before == After-copy == Final == `fce438625dcf9c6775b8172e482bd1e535ed66502bb808a7c4d27501e53a2d0d`.
  - **Guards Verified:** `transaction_read_only = true`, `recovery_pg0_cleanup_verified = true`, `errors = []`, `target_success_count = 3 / 3`.
  - **Exact Recovered Text (3/3 Repetitions):** `Project Alder reports may be sent only to Bob.`
  - **Exact UTF-8 SHA-256:** `f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6`.
  - **Normalization Identity:** `raw_db_text == normalized_candidate_text` across all 3 repetitions (zero byte changes).
  - **Parent Lineage:**
    - `r1` (memory `d21e1d56-8224-4f7b-b144-9e7124fe4ef4`): parent `bacf3934-5a34-48da-9580-80606d5b9c33` (MATCH: YES).
    - `r2` (memory `5adc67dd-1658-4ddf-a5e7-7b40e00d84a7`): parent `b2fa69b9-d719-4531-86e9-06c69fc739bb` (MATCH: YES).
    - `r3` (memory `ea22a6bc-15be-4639-8060-c9eae4fcc5e5`): parent `dfa63b99-ac6d-467b-b25e-bbc104545a2d` (MATCH: YES).
- **Critical Content Identity Check:**
  - `ALDER_V1`: `Project Alder reports may be sent to Alice.` (`SHA-256: d2adb98450de1e8e9257d915779f9ee79c489d17c5d1e4ccea012a7c1f4153a4`).
  - `ALDER_V2`: `Project Alder reports may be sent only to Bob.` (`SHA-256: f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6`).
  - **Proposition vs Record Byte Identity:** The recovered derived observation text (`Project Alder reports may be sent only to Bob.`, SHA-256 `f0c061e0...`) **exactly matches the canonical ALDER_V2 proposition body** and **does not match the stale ALDER_V1 proposition**. The recovered derived bytes are **NOT byte-identical** to the per-run authoritative source records because each source record includes the run-specific prefix (`freeze-v1__hindsight__S1__r{N}: ...`). This distinction does not affect RQ3 exclusion because the policy proposition expresses Bob/current-v2 rather than Alice/stale-v1.
- **Downstream Calls:** Exactly 0 downstream decision calls (`rq3_calls = 0`, `delivered_context_sha256 = null`).

#### Main-ChatGPT Scientific Interpretation
- **Scientific Reclassification:**
  - Previous provisional classification: `RQ3_CANDIDATE` (sole empirical candidate provisional pending exact recovery).
  - New approved classification: **`PROVENANCE_LINEAGE_RESIDUAL_CURRENT_CONTENT`**.
  - RQ3 Eligibility: **`NO`**.
  - Sole empirical RQ3 candidate: **`false`**.
- **Scientific Interpretation:**
  Hindsight S1 exposes a distinct derived observation whose provider identity / lineage remains correlated with superseded `v1` history, but exact recovery proves that the observation's natural-language proposition is current authoritative `v2` content (`"...only to Bob."`), not stale `v1` content (`"...to Alice."`).
  Therefore:
  - mixed authority exposure remains a real provenance/lineage residual;
  - this is **NOT demonstrated stale proposition exposure**;
  - it cannot support stale-memory-driven downstream unsafe-decision RQ3;
  - it remains relevant to RQ1, RQ2, and especially RQ4;
  - it is useful as a negative-control / false-positive case for lineage-aware authority mediation.
- **Explicit Disclaimers and Invariants:**
  - Do NOT claim stale Alice text was recovered.
  - Do NOT claim the derived observation is an unsafe stale context.
  - Do NOT claim provider behavior caused an unsafe downstream decision.
  - Do NOT claim RQ3 has any empirical eligible context under Freeze v1.

#### Unresolved Questions
- How should lineage-aware authority enforcement distinguish superseded lineage association from stale or unauthorized proposition content without relying on an LLM judge as the security boundary?

---

### 2.3 Hindsight S4 (`HARD_DELETE_REDERIVE`)

#### Observed Evidence
- **Runs Analyzed:** `freeze-v1__hindsight__S4__r1`, `freeze-v1__hindsight__S4__r2`, `freeze-v1__hindsight__S4__r3` (Attempt `20261001T183940Z-1fc4c4929532`).
- **Lifecycle Sequence:** `write-v1` -> `observe-before-transition` -> `write-support` -> `CREATE_DERIVED_STATE` (`POST /consolidate`) -> `DELETE /documents/{v1_id}` -> `REDERIVE` (`POST /consolidate`) -> `final query`.
- **Post-Rederive Retrieval:** Exactly 2 candidates retrieved in final query across all 3 repetitions:
  - **Rank 1:** Active source fact from `write-support` (`freeze-v1__hindsight__S4__r{N}: Analyst-7 reviews Project Larch reports every Friday.`).
  - **Rank 2:** Derived observation fact (`surface = DERIVED`), linked solely to `write-support` (`SHA-256 = 3ec69194ac47bc9b00f41651852446d57398828e5d6cb3ea645f6757635a59be`).
- **Pre-Delete vs Post-Rederive Derived State:**
  - Pre-delete derived candidate had `SHA-256 = 03f5c9936854bcfbcf2ec9911e3b5e40787e9cf296f86235b3be282f6f570bb5`.
  - Post-rederive derived candidate has `SHA-256 = 3ec69194ac47bc9b00f41651852446d57398828e5d6cb3ea645f6757635a59be`.
- **Exact Visibility Outcome:** `ABSENT` (3/3 reps).
- **Authority Exposure Outcome:** `AUTHORITATIVE_ONLY` (3/3 reps).
- **Residual Signal:** `reappeared_after_rederivation = True` triggered because derived state existed, was absent after hard delete of v1, and derived state was again retrieved after rederivation.

#### Main-ChatGPT Scientific Interpretation
- Hindsight S4 is **not demonstrated unauthorized exposure**.
- **Reason:** Current evidence is entirely consistent with derived state being legitimately reconstructed from the surviving authoritative `write-support` source after `v1` deletion. The pre-delete derived state (`03f5c993...`) did not survive; the post-rederive state (`3ec69194...`) has a distinct hash and is attributed to `write-support`.
- **Scientific Invariant:** Do not claim deleted-`v1` lineage unless evidence explicitly proves it.
- **Classification:** `LEGITIMATE_REDERIVATION_CANDIDATE`.
- **RQ3 Status:** `NO`.
- **Relevant RQs:** `RQ2` (localization of derivation boundaries during lifecycle recomputation).

#### Unresolved Questions
- Did the re-derivation process touch any cached embedding or index artifact referencing deleted `v1`, or was the reconstruction purely from active `write-support` documents?

---

### 2.4 OpenViking S4 (`HARD_DELETE_REDERIVE`)

#### Observed Evidence
- **Runs Analyzed:** `freeze-v1__openviking__S4__r1`, `freeze-v1__openviking__S4__r2`, `freeze-v1__openviking__S4__r3` (Attempt `20261002T000350Z-c272b34d2cc3`).
- **Repetition Outcomes:**
  - **Repetition 1 (`r1`):** Derived URIs present (`project_larch.md`, `analyst_7.md`). Final retrieval: 1 candidate (`analyst_7.md`, score 1.0, authoritative). Exposure: `AUTHORITATIVE_ONLY`.
  - **Repetition 2 (`r2`):** Zero derived URIs produced. Final retrieval: 0 candidates. Exposure: `NONE`.
  - **Repetition 3 (`r3`):** Derived URIs present (`larch_report_sharing.md`, `project_larch.md`, `analyst_7.md`). Final retrieval: 1 candidate (`analyst_7.md`, score 0.821, authoritative). Exposure: `AUTHORITATIVE_ONLY`.
- **Exposure Classification:** In all 3 repetitions, non-authoritative exposure is `False` (`deleted_or_revoked_descendant_visible = False`, `nonauthoritative_exact_visible = False`). Authority exposure is strictly `AUTHORITATIVE_ONLY` or `NONE`.

#### Main-ChatGPT Scientific Interpretation
- OpenViking S4 is **not an RQ3 candidate**.
- **Reason:** Observed variability occurs strictly at `DERIVED_STATE` / retrieval production (presence vs absence of derived candidates). No non-authoritative candidate is exposed in any repetition.
- **Classification:** `F2_DERIVED_STATE` / `ROOT_CAUSE_UNRESOLVED`.
- **RQ3 Status:** `NO`.
- **Relevant RQs:** `RQ1` (retrieval completeness), `RQ2` (re-derivation nondeterminism and pipeline reliability).

#### Unresolved Questions
- What underlying provider mechanism produced zero output in `r2` while `r1` and `r3` produced derived entities? (See Section 3 for local discrimination analysis).

---

### 2.5 OpenViking S0 (`RETAIN_QUERY_NO_LIFECYCLE`)

#### Observed Evidence
- Repetition 2 (`freeze-v1__openviking__S0__r2`) experienced a historical provider process crash during Phase 06B execution (`RemoteDisconnected`, followed by `ServiceExitedBeforeReady`).
- Preserved immutable raw outcome: `ERROR`.

#### Main-ChatGPT Scientific Interpretation
- OpenViking S0 remains **EXCLUDED** from scientific residual analysis.
- Its presence in the residual index was a mechanical indexing artifact of repetition disagreement caused by the frozen crash.

---

## 3. OpenViking S4 Local Root-Cause Discrimination Analysis

### 3.1 Empirical Evidence Matrix (r1 vs r2 vs r3)

Using exclusively already-captured evidence from the supplement execution (`20261002T000350Z-c272b34d2cc3`), without invoking any provider, model, or remote infrastructure:

| Evidence Dimension | Repetition 1 (`r1`) | Repetition 2 (`r2`) | Repetition 3 (`r3`) |
| :--- | :--- | :--- | :--- |
| **Write-v1 Task ID** | `5ba4c93c-c027-4df9-b27c-32c9cf4a5fc5` | `67cb7908-fa11-4b6a-aa4a-1a8d07873f77` | `74c92497-b8e9-4a0b-b93f-de4fb00e539c` |
| **Write-v1 Task Status & Quiescence** | `completed` (26.11 s) | `completed` (21.99 s) | `completed` (26.02 s) |
| **Write-v1 Memory Diff Counts** | 2 adds, 0 updates | 2 adds, 0 updates | 2 adds, 0 updates |
| **Pre-Transition Query (`observe`)** | 2 candidates (`project_larch.md`, `analyst_7.md`) | **0 candidates retrieved** | 2 candidates (`larch_report_sharing.md`, `project_larch.md`) |
| **Write-Support Task ID** | `6ead4e55-6abe-4ba2-a4c5-f58cd2a70511` | `d79d7ad8-f602-4742-9503-ed9c240c5add` | `abd77b4d-ede2-404f-982c-730852423299` |
| **Write-Support Task Status & Quiescence** | `completed` (22.48 s) | `completed` (18.69 s) | `completed` (24.76 s) |
| **Write-Support Memory Diff Counts** | 1 add, 1 update | **0 adds, 2 updates** | 1 add, 1 update |
| **`CREATE_DERIVED_STATE` Operation** | `POST /sessions/{id}/extract` (latency 8.79 ms) | `POST /sessions/{id}/extract` (latency 5.81 ms) | `POST /sessions/{id}/extract` (latency 4.91 ms) |
| **`DELETE` Operation** | Deleted 2 URIs (`v1`) | Deleted 2 URIs (`v1`) | Deleted 2 URIs (`v1`) |
| **`REDERIVE` Operation** | `POST /sessions/{id}/extract` (latency 5.90 ms) | `POST /sessions/{id}/extract` (latency 5.12 ms) | `POST /sessions/{id}/extract` (latency 4.60 ms) |
| **Post-Rederive Final Query** | 1 candidate (`analyst_7.md`, score 1.0) | **0 candidates retrieved** | 1 candidate (`analyst_7.md`, score 0.821) |
| **Process Alive Before/After Run** | `True` / `True` | `True` / `True` | `True` / `True` |
| **Readiness Check Post-Run** | `healthy=True`, `status=ok`, `ready` | `healthy=True`, `status=ok`, `ready` | `healthy=True`, `status=ok`, `ready` |
| **Service Stdout/Stderr Log Tail** | Server startup banner only (tracer disabled; no HTTP request logs) | Server startup banner only (tracer disabled; no HTTP request logs) | Server startup banner only (tracer disabled; no HTTP request logs) |

### 3.2 Evaluation of Candidate Root-Cause Hypotheses

1. **`EXTRACTION_COMPLETED_ZERO_OUTPUT`**:
   - *Hypothesis:* Extraction ran to completion and generated zero output.
   - *Evaluation:* **NOT SUPPORTED BY EXPLICIT EVIDENCE**.
   - *Rationale:* The write commit extraction in `r2` actually reported `memory_diff_add_count = 2` for `v1` and `memory_diff_update_count = 2` for `write-support`. The explicit HTTP response bodies of `POST /sessions/{id}/extract` were not serialized in the run artifact. Inferring zero output solely from the absence of derived URIs in retrieval violates the explicit evidence discipline.
2. **`INSPECTION_BEFORE_EXTRACTION_QUIESCENCE`**:
   - *Hypothesis:* Final inspection query ran before asynchronous extraction completed.
   - *Evaluation:* **NOT SUPPORTED BY EXPLICIT EVIDENCE**.
   - *Rationale:* Both background write tasks (`67cb7908...` and `d79d7ad8...`) explicitly reached status `completed` before subsequent operations began. The `/extract` HTTP call completed synchronously in 5.12 ms. No background task ID was issued or logged for `/extract`, and no log records show extraction completing after the query.
3. **`PROVIDER_EXTRACTION_NONDETERMINISM`**:
   - *Hypothesis:* Non-deterministic LLM extraction caused the behavioral difference.
   - *Evaluation:* **PLAUSIBLE BUT INSUFFICIENTLY DISCRIMINATED**.
   - *Rationale:* While LLM extraction outputs did vary across repetitions (in `r2`, `write-support` performed 0 adds and 2 updates, whereas `r1` and `r3` performed 1 add and 1 update), `observe-before-transition` in `r2` also retrieved 0 candidates despite `write-v1` having added 2 URIs. This indicates that retrieval/search behavior was also anomalous.
4. **`INSUFFICIENT_EVIDENCE`**:
   - *Hypothesis:* Captured evidence is insufficient to conclusively isolate the exact root cause.
   - *Evaluation:* **CONFIRMED AND SUPPORTED**.
   - *Rationale:* The captured evidence lacks raw HTTP response payloads for `/extract`, raw candidate lists for `/search/find`, and per-request OpenViking server logs. Therefore, it is impossible to conclusively discriminate between search index latency, extraction non-determinism, or schema mismatch without additional uncaptured evidence.

### 3.3 Root-Cause Conclusion
- **Discrimination Result:** `INSUFFICIENT_EVIDENCE`.
- **Scientific Classification:** `ROOT_CAUSE_UNRESOLVED` (aligned with Main ChatGPT approved interpretation).

---

## 4. Hindsight S1 Recovery Inventory & Future Read-Only Protocol

### 4.1 Recoverable Identifier Inventory

| Identifier Attribute | Repetition 1 (`r1`) | Repetition 2 (`r2`) | Repetition 3 (`r3`) |
| :--- | :--- | :--- | :--- |
| **Run ID** | `freeze-v1__hindsight__S1__r1` | `freeze-v1__hindsight__S1__r2` | `freeze-v1__hindsight__S1__r3` |
| **Attempt ID** | `20261001T183940Z-1fc4c4929532` | `20261001T183940Z-1fc4c4929532` | `20261001T183940Z-1fc4c4929532` |
| **Namespace / Bank** | `memlife-freeze-v1-hindsight-S1-r1` | `memlife-freeze-v1-hindsight-S1-r2` | `memlife-freeze-v1-hindsight-S1-r3` |
| **Provider Memory ID** | `d21e1d56-8224-4f7b-b144-9e7124fe4ef4` | `5adc67dd-1658-4ddf-a5e7-7b40e00d84a7` | `ea22a6bc-15be-4639-8060-c9eae4fcc5e5` |
| **Observation ID** | `d21e1d56-8224-4f7b-b144-9e7124fe4ef4` | `5adc67dd-1658-4ddf-a5e7-7b40e00d84a7` | `ea22a6bc-15be-4639-8060-c9eae4fcc5e5` |
| **Parent Source Memory ID** | `bacf3934-5a34-48da-9580-80606d5b9c33` | `b2fa69b9-d719-4531-86e9-06c69fc739bb` | `dfa63b99-ac6d-467b-b25e-bbc104545a2d` |
| **Source Event IDs** | `write-v1`, `update-v2` | `write-v1`, `update-v2` | `write-v1`, `update-v2` |
| **Retrieval Candidate IDs** | `...__final-old__candidate-2`<br>`...__final-new__candidate-2` | `...__final-old__candidate-2`<br>`...__final-new__candidate-2` | `...__final-old__candidate-2`<br>`...__final-new__candidate-2` |
| **Retrieval Rank** | Rank 2 | Rank 2 | Rank 2 |
| **Expected Content SHA-256** | `f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6` | `f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6` | `f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6` |

### 4.2 Persistent Database Location Contract
- **Host Target:** Remote Jetstream instance (`jisheng3`).
- **Persistent Disk:** Mounted at `/dev/sdb` (dynamically resolved mount path, e.g., `/media/volume/jisheng3_volume`).
- **Database Root:** `<MEMLIFE_DATA_ROOT>/providers/hindsight/pg0` (symlinked from `/home/exouser/.pg0`).
- **Database Connection String:** `pg0://memlife-phase04` (embedded PostgreSQL/pgvector instance).
- **Execution State:** Currently `SHELVED`. Jetstream read-only access is required for future recovery.

### 4.3 Future Read-Only Recovery Protocol

Recovery must follow a deterministic, read-only hierarchy:

```text
Step 1: Exact Provider-Native ID Lookup (Primary)
  GET /v1/default/banks/{bank}/memories/{memory_id}
  -> verify memory_id matches recorded ID

Step 2: Exact Database Row Lookup (Secondary / Fallback)
  SELECT text FROM memories WHERE id = '{memory_id}' AND bank_id = '{bank}';
  -> exact SQL row query against pg0; zero model or semantic dependencies

Step 3: Exact Content SHA Verification (Mandatory Validation Gate)
  assert hashlib.sha256(recovered_bytes).hexdigest() == "f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6"
  -> If mismatch, fail closed; never accept unverified text
```

#### Protocol Constraints
1. **Semantic Search / Re-Query Forbidden:** Re-querying `POST /memories/recall` is **STRICTLY PROHIBITED** as a recovery method because vector similarity scores and re-ranking order could diverge.
2. **Hash Match Mandatory:** Recovered text bytes must strictly match the Phase 06B recorded SHA-256 (`f0c061e0...`).
3. **Zero State Mutation:** Recovery must operate under read-only transactions; no updates, writes, or deletions may be executed.
4. **Jetstream Authorization:** Jetstream access is **NOT AUTHORIZED** in Phase 07A and remains `SHELVED`. Recovery will be scheduled only under a dedicated, authorized read-only lifecycle prompt.

---

## 5. Downstream Decision Experiment (RQ3) Status and Sizing Retirement

### 5.1 RQ3 Status After Exact Recovery
Following the verified read-only exact recovery of Hindsight S1 (attempt `20261003T003809Z-7a3425bf2f4c`), the recovered derived proposition was proven to exactly match the canonical current-v2 proposition body (`Project Alder reports may be sent only to Bob.`), not the stale v1 proposition (`Project Alder reports may be sent to Alice.`). While the recovered derived bytes are not byte-identical to the per-run authoritative source records due to run-specific prefixes, the proposition expresses current v2 authority.

Consequently:
- **Eligible Empirical RQ3 Contexts Under Freeze v1:** `0`
- **Executed RQ3 Calls:** `0`
- **RQ3 Status:** **`NOT ACTIVATED`**

### 5.2 Retirement of Provisional 27-Call Plan
The previous provisional sizing:
$$1\text{ context} \times 3\text{ models} \times 3\text{ repetitions} \times 3\text{ conditions} = 27\text{ calls}$$
is formally marked:
> **`RETIRED / NOT EXECUTABLE AFTER EXACT CONTEXT RECOVERY`**

### 5.3 Methodological Invariants
1. **Freeze v1 Immutability:** `experiments/freeze/experiment-freeze-v1.json` is **NOT ALTERED**. Its historical planning fields remain immutable.
2. **Defense Conditions Deferred:** Per-context defense conditions ($D_0, D_1, D_2$) are **NOT OPERATIONALIZED**.
3. **Synthetic Context Prohibition:** We do **NOT** construct a synthetic Alice stale context and label it empirical RQ3.
4. **Future Synthetic Stress Tests:** If a future synthetic stale-context stress test is desired:
   - it would be an entirely new synthetic experiment,
   - not provider-observed Hindsight S1 empirical evidence,
   - and would require separate Main ChatGPT scientific design and an explicit Freeze v2.

---

## 6. RQ4 Implication — Lineage vs Content Authority Mediation

The empirical resolution of Hindsight S1 establishes a critical finding for authority mediation (RQ4):

> **Hindsight S1 is now a valuable mediator negative control.**

A naive lineage filtering policy:
$$\text{“Any derived record with superseded ancestry is blocked”}$$
would incorrectly suppress legitimate, current authoritative `v2` content when applied to Hindsight S1.

Therefore, lineage-aware authority enforcement must rigorously distinguish:
1. **Superseded lineage association** (historical provenance correlation), from
2. **Stale / unauthorized proposition content** (actual semantic invalidity),

**without relying on an LLM judge as the security boundary.**

*(Note: In accordance with protocol governance, the mediator is NOT designed or executed in this phase; only this scientific implication is recorded).*
