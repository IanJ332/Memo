# Phase 07B — RQ3 Context Candidate Extraction

> **Status:** CANDIDATE_NOT_SCIENTIFICALLY_APPROVED
> **Research Question:** RQ3 (Downstream Decision Impact on Residual Contexts)
> **Target Cells:** Mem0 S1 (`SUPERSESSION_OR_UPDATE`), Hindsight S1 (`SUPERSESSION_OR_UPDATE`)
> **Canonical Sources:** `combined-derived-runs.jsonl`, `experiment-freeze-v1.json`

---

## 1. Protocol Frame and RQ3 Candidate Evaluation

This document extracts exact retrieval and model-boundary evidence for all six repetitions of authority-exposure residual cells (Mem0 S1 and Hindsight S1) to determine whether the repository contains sufficient evidence to freeze a downstream RQ3 context.

### RQ3 Context Freeze Evaluation Gate

| Requirement | Mem0 S1 Evaluation | Hindsight S1 Evaluation |
| :--- | :--- | :--- |
| **1. Reproducible non-authoritative exposure across 3/3 reps** | **YES** (3/3 reps `AUTHORITATIVE_AND_NONAUTHORITATIVE`) | **YES** (3/3 reps `AUTHORITATIVE_AND_NONAUTHORITATIVE`) |
| **2. Known authority status** | **YES** (`fact-v1` superseded/false; `fact-v2` active/true) | **YES** (`fact-v1` superseded/false; `fact-v2` active/true) |
| **3. Exact content bytes/text available** | **PARTIAL/ABSENT** (`v2` text known; no distinct non-authoritative candidate text retrieved) | **NO** (Derived non-auth candidate text was not serialized; only SHA-256 `f0c061e0...` is preserved) |
| **4. Exact ordering available** | **YES** (Single candidate, rank 1) | **YES** (Rank 1 source, Rank 2 derived) |
| **5. Provenance/lineage available** | **YES** (Linked to `update-v2` and `write-v1`) | **YES** (Linked to `update-v2` and `write-v1`) |
| **6. Deterministic mapping to model boundary** | **NO** (`delivered_context_sha256 = null`; 0 downstream model calls) | **NO** (`delivered_context_sha256 = null`; 0 downstream model calls) |
| **Overall Gate Status** | **`MISSING_MODEL_BOUNDARY_TRACE`** | **`MISSING_EXACT_CONTEXT`** |

> [!IMPORTANT]
> **Neither cell is READY_TO_FREEZE.** Both cells are labeled `CANDIDATE_NOT_SCIENTIFICALLY_APPROVED`. No final RQ3 experimental freeze is created; Main ChatGPT must review the extracted evidence before any future context candidate approval.

---

## 2. Mem0 S1 (`SUPERSESSION_OR_UPDATE`) — Candidate Evidence

### 2.1 Repetition Evidence Matrix

| Field | Repetition 1 (`r1`) | Repetition 2 (`r2`) | Repetition 3 (`r3`) |
| :--- | :--- | :--- | :--- |
| **provider** | `mem0` | `mem0` | `mem0` |
| **scenario** | `S1` | `S1` | `S1` |
| **repetition** | `1` | `2` | `3` |
| **run_id** | `freeze-v1__mem0__S1__r1` | `freeze-v1__mem0__S1__r2` | `freeze-v1__mem0__S1__r3` |
| **namespace** | `memlife-freeze-v1-mem0-S1-r1` | `memlife-freeze-v1-mem0-S1-r2` | `memlife-freeze-v1-mem0-S1-r3` |
| **source_memory_ids** | `4a2f1c47-a863-434b-b5f8-047f249923fd` | `ea519c5e-03bb-4d41-892e-99d4e2ede840` | `623fc25e-1c39-4087-99a3-4156c2e0e9be` |
| **derived_memory_ids** | `4a2f1c47-a863-434b-b5f8-047f249923fd` | `ea519c5e-03bb-4d41-892e-99d4e2ede840` | `623fc25e-1c39-4087-99a3-4156c2e0e9be` |
| **retrieval_candidate_ids** | `freeze-v1__mem0__S1__r1__final-old__candidate-1`<br>`freeze-v1__mem0__S1__r1__final-new__candidate-1` | `freeze-v1__mem0__S1__r2__final-old__candidate-1`<br>`freeze-v1__mem0__S1__r2__final-new__candidate-1` | `freeze-v1__mem0__S1__r3__final-old__candidate-1`<br>`freeze-v1__mem0__S1__r3__final-new__candidate-1` |
| **authoritative_candidate_content** | **exact_text**: `freeze-v1__mem0__S1__r1: Project Alder reports may be sent only to Bob.`<br>**sha256**: `b03c218be7d6ea4ea755d628334b14b07000021e11f7e9d712a90d4177cf215d` | **exact_text**: `freeze-v1__mem0__S1__r2: Project Alder reports may be sent only to Bob.`<br>**sha256**: `b422b843fc116b64f906dcb6cbf9f9b7bcc8f147a2c14d8d6a1619baf8b48a47` | **exact_text**: `freeze-v1__mem0__S1__r3: Project Alder reports may be sent only to Bob.`<br>**sha256**: `03cef19bbc4f521a51778ab23d3df00b8beb40612f8450400baa37b37882731b` |
| **non_authoritative_candidate_content** | **status**: `UNAVAILABLE`<br>**reason**: `No distinct non-authoritative candidate record retrieved; single candidate returned is in-place updated record carrying v2 content with superseded v1 provenance`<br>**exact_text**: `UNAVAILABLE`<br>**sha256**: `UNAVAILABLE` | **status**: `UNAVAILABLE`<br>**reason**: `No distinct non-authoritative candidate record retrieved; single candidate returned is in-place updated record carrying v2 content with superseded v1 provenance`<br>**exact_text**: `UNAVAILABLE`<br>**sha256**: `UNAVAILABLE` | **status**: `UNAVAILABLE`<br>**reason**: `No distinct non-authoritative candidate record retrieved; single candidate returned is in-place updated record carrying v2 content with superseded v1 provenance`<br>**exact_text**: `UNAVAILABLE`<br>**sha256**: `UNAVAILABLE` |
| **provenance_lineage** | **candidate_source_event_ids**: `[['freeze-v1__mem0__S1__r1__update-v2', 'freeze-v1__mem0__S1__r1__write-v1'], ['freeze-v1__mem0__S1__r1__update-v2', 'freeze-v1__mem0__S1__r1__write-v1']]`<br>**provider_parent_source_ids**: `[]`<br>**association_basis**: `direct provider/adapter identity only` | **candidate_source_event_ids**: `[['freeze-v1__mem0__S1__r2__update-v2', 'freeze-v1__mem0__S1__r2__write-v1'], ['freeze-v1__mem0__S1__r2__update-v2', 'freeze-v1__mem0__S1__r2__write-v1']]`<br>**provider_parent_source_ids**: `[]`<br>**association_basis**: `direct provider/adapter identity only` | **candidate_source_event_ids**: `[['freeze-v1__mem0__S1__r3__update-v2', 'freeze-v1__mem0__S1__r3__write-v1'], ['freeze-v1__mem0__S1__r3__update-v2', 'freeze-v1__mem0__S1__r3__write-v1']]`<br>**provider_parent_source_ids**: `[]`<br>**association_basis**: `direct provider/adapter identity only` |
| **authority_status** | **fact_v1**: `{'event_id': 'freeze-v1__mem0__S1__r1__write-v1', 'authoritative': False, 'lifecycle_state': 'superseded', 'authority_reason': 'experiment authority transition replaced v1 with v2'}`<br>**fact_v2**: `{'event_id': 'freeze-v1__mem0__S1__r1__update-v2', 'authoritative': True, 'lifecycle_state': 'active', 'authority_reason': 'v2 is the current experiment-defined authority'}` | **fact_v1**: `{'event_id': 'freeze-v1__mem0__S1__r2__write-v1', 'authoritative': False, 'lifecycle_state': 'superseded', 'authority_reason': 'experiment authority transition replaced v1 with v2'}`<br>**fact_v2**: `{'event_id': 'freeze-v1__mem0__S1__r2__update-v2', 'authoritative': True, 'lifecycle_state': 'active', 'authority_reason': 'v2 is the current experiment-defined authority'}` | **fact_v1**: `{'event_id': 'freeze-v1__mem0__S1__r3__write-v1', 'authoritative': False, 'lifecycle_state': 'superseded', 'authority_reason': 'experiment authority transition replaced v1 with v2'}`<br>**fact_v2**: `{'event_id': 'freeze-v1__mem0__S1__r3__update-v2', 'authoritative': True, 'lifecycle_state': 'active', 'authority_reason': 'v2 is the current experiment-defined authority'}` |
| **retrieval_ordering** | `{'phase': 'final-old', 'rank': 1, 'candidate_id': 'freeze-v1__mem0__S1__r1__final-old__candidate-1', 'provider_memory_id': '4a2f1c47-a863-434b-b5f8-047f249923fd', 'surface': 'UNKNOWN', 'sha256': 'b03c218be7d6ea4ea755d628334b14b07000021e11f7e9d712a90d4177cf215d'}`<br>`{'phase': 'final-new', 'rank': 1, 'candidate_id': 'freeze-v1__mem0__S1__r1__final-new__candidate-1', 'provider_memory_id': '4a2f1c47-a863-434b-b5f8-047f249923fd', 'surface': 'UNKNOWN', 'sha256': 'b03c218be7d6ea4ea755d628334b14b07000021e11f7e9d712a90d4177cf215d'}` | `{'phase': 'final-old', 'rank': 1, 'candidate_id': 'freeze-v1__mem0__S1__r2__final-old__candidate-1', 'provider_memory_id': 'ea519c5e-03bb-4d41-892e-99d4e2ede840', 'surface': 'UNKNOWN', 'sha256': 'b422b843fc116b64f906dcb6cbf9f9b7bcc8f147a2c14d8d6a1619baf8b48a47'}`<br>`{'phase': 'final-new', 'rank': 1, 'candidate_id': 'freeze-v1__mem0__S1__r2__final-new__candidate-1', 'provider_memory_id': 'ea519c5e-03bb-4d41-892e-99d4e2ede840', 'surface': 'UNKNOWN', 'sha256': 'b422b843fc116b64f906dcb6cbf9f9b7bcc8f147a2c14d8d6a1619baf8b48a47'}` | `{'phase': 'final-old', 'rank': 1, 'candidate_id': 'freeze-v1__mem0__S1__r3__final-old__candidate-1', 'provider_memory_id': '623fc25e-1c39-4087-99a3-4156c2e0e9be', 'surface': 'UNKNOWN', 'sha256': '03cef19bbc4f521a51778ab23d3df00b8beb40612f8450400baa37b37882731b'}`<br>`{'phase': 'final-new', 'rank': 1, 'candidate_id': 'freeze-v1__mem0__S1__r3__final-new__candidate-1', 'provider_memory_id': '623fc25e-1c39-4087-99a3-4156c2e0e9be', 'surface': 'UNKNOWN', 'sha256': '03cef19bbc4f521a51778ab23d3df00b8beb40612f8450400baa37b37882731b'}` |
| **exact_delivered_context_if_already_serialized** | `UNAVAILABLE` | `UNAVAILABLE` | `UNAVAILABLE` |
| **exact_prompt_context_fragment_if_already_serialized** | `UNAVAILABLE` | `UNAVAILABLE` | `UNAVAILABLE` |
| **model_boundary_trace_if_available** | `UNAVAILABLE` | `UNAVAILABLE` | `UNAVAILABLE` |

### 2.2 Preserved Serialized Text (Mem0 S1)

#### Repetition 1 (`freeze-v1__mem0__S1__r1`)
- **Authoritative Content Text (`v2`):** `freeze-v1__mem0__S1__r1: Project Alder reports may be sent only to Bob.`
- **Authoritative Content SHA-256:** `b03c218be7d6ea4ea755d628334b14b07000021e11f7e9d712a90d4177cf215d`
- **Non-Authoritative Content Text:** `UNAVAILABLE` (No distinct non-authoritative candidate record retrieved; single candidate returned is in-place updated record carrying v2 content with superseded v1 provenance)
- **Delivered Context Text:** `UNAVAILABLE`
- **Prompt Context Fragment:** `UNAVAILABLE`

#### Repetition 2 (`freeze-v1__mem0__S1__r2`)
- **Authoritative Content Text (`v2`):** `freeze-v1__mem0__S1__r2: Project Alder reports may be sent only to Bob.`
- **Authoritative Content SHA-256:** `b422b843fc116b64f906dcb6cbf9f9b7bcc8f147a2c14d8d6a1619baf8b48a47`
- **Non-Authoritative Content Text:** `UNAVAILABLE` (No distinct non-authoritative candidate record retrieved; single candidate returned is in-place updated record carrying v2 content with superseded v1 provenance)
- **Delivered Context Text:** `UNAVAILABLE`
- **Prompt Context Fragment:** `UNAVAILABLE`

#### Repetition 3 (`freeze-v1__mem0__S1__r3`)
- **Authoritative Content Text (`v2`):** `freeze-v1__mem0__S1__r3: Project Alder reports may be sent only to Bob.`
- **Authoritative Content SHA-256:** `03cef19bbc4f521a51778ab23d3df00b8beb40612f8450400baa37b37882731b`
- **Non-Authoritative Content Text:** `UNAVAILABLE` (No distinct non-authoritative candidate record retrieved; single candidate returned is in-place updated record carrying v2 content with superseded v1 provenance)
- **Delivered Context Text:** `UNAVAILABLE`
- **Prompt Context Fragment:** `UNAVAILABLE`

---

## 3. Hindsight S1 (`SUPERSESSION_OR_UPDATE`) — Candidate Evidence

### 3.1 Repetition Evidence Matrix

| Field | Repetition 1 (`r1`) | Repetition 2 (`r2`) | Repetition 3 (`r3`) |
| :--- | :--- | :--- | :--- |
| **provider** | `hindsight` | `hindsight` | `hindsight` |
| **scenario** | `S1` | `S1` | `S1` |
| **repetition** | `1` | `2` | `3` |
| **run_id** | `freeze-v1__hindsight__S1__r1` | `freeze-v1__hindsight__S1__r2` | `freeze-v1__hindsight__S1__r3` |
| **namespace** | `memlife-freeze-v1-hindsight-S1-r1` | `memlife-freeze-v1-hindsight-S1-r2` | `memlife-freeze-v1-hindsight-S1-r3` |
| **source_memory_ids** | `bacf3934-5a34-48da-9580-80606d5b9c33` | `b2fa69b9-d719-4531-86e9-06c69fc739bb` | `dfa63b99-ac6d-467b-b25e-bbc104545a2d` |
| **derived_memory_ids** | `d21e1d56-8224-4f7b-b144-9e7124fe4ef4` | `5adc67dd-1658-4ddf-a5e7-7b40e00d84a7` | `ea22a6bc-15be-4639-8060-c9eae4fcc5e5` |
| **retrieval_candidate_ids** | `freeze-v1__hindsight__S1__r1__final-old__candidate-1`<br>`freeze-v1__hindsight__S1__r1__final-old__candidate-2`<br>`freeze-v1__hindsight__S1__r1__final-new__candidate-1`<br>`freeze-v1__hindsight__S1__r1__final-new__candidate-2` | `freeze-v1__hindsight__S1__r2__final-old__candidate-1`<br>`freeze-v1__hindsight__S1__r2__final-old__candidate-2`<br>`freeze-v1__hindsight__S1__r2__final-new__candidate-1`<br>`freeze-v1__hindsight__S1__r2__final-new__candidate-2` | `freeze-v1__hindsight__S1__r3__final-old__candidate-1`<br>`freeze-v1__hindsight__S1__r3__final-old__candidate-2`<br>`freeze-v1__hindsight__S1__r3__final-new__candidate-1`<br>`freeze-v1__hindsight__S1__r3__final-new__candidate-2` |
| **authoritative_candidate_content** | **exact_text**: `freeze-v1__hindsight__S1__r1: Project Alder reports may be sent only to Bob.`<br>**sha256**: `ecb4e26bbc1a2f91c214dba0c7cf37fe8267190a68dc0b8418d3c76c4ccb234d` | **exact_text**: `freeze-v1__hindsight__S1__r2: Project Alder reports may be sent only to Bob.`<br>**sha256**: `2462e1492a9c8c93ec0d67ca88d4f651bc040d91be012f57bf3ab32e41c59b3d` | **exact_text**: `freeze-v1__hindsight__S1__r3: Project Alder reports may be sent only to Bob.`<br>**sha256**: `252a8d190876609383860b4e9dc7874c89cdc3752f1e61289c7a2244a89bc34a` |
| **non_authoritative_candidate_content** | **status**: `MISSING_EXACT_TEXT`<br>**reason**: `Derived memory record was hashed but raw text bytes were not serialized into Phase 06B JSONL`<br>**exact_text**: `UNAVAILABLE`<br>**sha256**: `f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6` | **status**: `MISSING_EXACT_TEXT`<br>**reason**: `Derived memory record was hashed but raw text bytes were not serialized into Phase 06B JSONL`<br>**exact_text**: `UNAVAILABLE`<br>**sha256**: `f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6` | **status**: `MISSING_EXACT_TEXT`<br>**reason**: `Derived memory record was hashed but raw text bytes were not serialized into Phase 06B JSONL`<br>**exact_text**: `UNAVAILABLE`<br>**sha256**: `f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6` |
| **provenance_lineage** | **candidate_source_event_ids**: `[['freeze-v1__hindsight__S1__r1__update-v2', 'freeze-v1__hindsight__S1__r1__write-v1'], ['freeze-v1__hindsight__S1__r1__update-v2', 'freeze-v1__hindsight__S1__r1__write-v1'], ['freeze-v1__hindsight__S1__r1__update-v2', 'freeze-v1__hindsight__S1__r1__write-v1'], ['freeze-v1__hindsight__S1__r1__update-v2', 'freeze-v1__hindsight__S1__r1__write-v1']]`<br>**provider_parent_source_ids**: `['bacf3934-5a34-48da-9580-80606d5b9c33']`<br>**association_basis**: `direct provider/adapter identity only` | **candidate_source_event_ids**: `[['freeze-v1__hindsight__S1__r2__update-v2', 'freeze-v1__hindsight__S1__r2__write-v1'], ['freeze-v1__hindsight__S1__r2__update-v2', 'freeze-v1__hindsight__S1__r2__write-v1'], ['freeze-v1__hindsight__S1__r2__update-v2', 'freeze-v1__hindsight__S1__r2__write-v1'], ['freeze-v1__hindsight__S1__r2__update-v2', 'freeze-v1__hindsight__S1__r2__write-v1']]`<br>**provider_parent_source_ids**: `['b2fa69b9-d719-4531-86e9-06c69fc739bb']`<br>**association_basis**: `direct provider/adapter identity only` | **candidate_source_event_ids**: `[['freeze-v1__hindsight__S1__r3__update-v2', 'freeze-v1__hindsight__S1__r3__write-v1'], ['freeze-v1__hindsight__S1__r3__update-v2', 'freeze-v1__hindsight__S1__r3__write-v1'], ['freeze-v1__hindsight__S1__r3__update-v2', 'freeze-v1__hindsight__S1__r3__write-v1'], ['freeze-v1__hindsight__S1__r3__update-v2', 'freeze-v1__hindsight__S1__r3__write-v1']]`<br>**provider_parent_source_ids**: `['dfa63b99-ac6d-467b-b25e-bbc104545a2d']`<br>**association_basis**: `direct provider/adapter identity only` |
| **authority_status** | **fact_v1**: `{'event_id': 'freeze-v1__hindsight__S1__r1__write-v1', 'authoritative': False, 'lifecycle_state': 'superseded', 'authority_reason': 'experiment authority transition replaced v1 with v2'}`<br>**fact_v2**: `{'event_id': 'freeze-v1__hindsight__S1__r1__update-v2', 'authoritative': True, 'lifecycle_state': 'active', 'authority_reason': 'v2 is the current experiment-defined authority'}` | **fact_v1**: `{'event_id': 'freeze-v1__hindsight__S1__r2__write-v1', 'authoritative': False, 'lifecycle_state': 'superseded', 'authority_reason': 'experiment authority transition replaced v1 with v2'}`<br>**fact_v2**: `{'event_id': 'freeze-v1__hindsight__S1__r2__update-v2', 'authoritative': True, 'lifecycle_state': 'active', 'authority_reason': 'v2 is the current experiment-defined authority'}` | **fact_v1**: `{'event_id': 'freeze-v1__hindsight__S1__r3__write-v1', 'authoritative': False, 'lifecycle_state': 'superseded', 'authority_reason': 'experiment authority transition replaced v1 with v2'}`<br>**fact_v2**: `{'event_id': 'freeze-v1__hindsight__S1__r3__update-v2', 'authoritative': True, 'lifecycle_state': 'active', 'authority_reason': 'v2 is the current experiment-defined authority'}` |
| **retrieval_ordering** | `{'phase': 'final-old', 'rank': 1, 'candidate_id': 'freeze-v1__hindsight__S1__r1__final-old__candidate-1', 'provider_memory_id': 'bacf3934-5a34-48da-9580-80606d5b9c33', 'surface': 'SOURCE', 'sha256': 'ecb4e26bbc1a2f91c214dba0c7cf37fe8267190a68dc0b8418d3c76c4ccb234d'}`<br>`{'phase': 'final-old', 'rank': 2, 'candidate_id': 'freeze-v1__hindsight__S1__r1__final-old__candidate-2', 'provider_memory_id': 'd21e1d56-8224-4f7b-b144-9e7124fe4ef4', 'surface': 'DERIVED', 'sha256': 'f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6'}`<br>`{'phase': 'final-new', 'rank': 1, 'candidate_id': 'freeze-v1__hindsight__S1__r1__final-new__candidate-1', 'provider_memory_id': 'bacf3934-5a34-48da-9580-80606d5b9c33', 'surface': 'SOURCE', 'sha256': 'ecb4e26bbc1a2f91c214dba0c7cf37fe8267190a68dc0b8418d3c76c4ccb234d'}`<br>`{'phase': 'final-new', 'rank': 2, 'candidate_id': 'freeze-v1__hindsight__S1__r1__final-new__candidate-2', 'provider_memory_id': 'd21e1d56-8224-4f7b-b144-9e7124fe4ef4', 'surface': 'DERIVED', 'sha256': 'f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6'}` | `{'phase': 'final-old', 'rank': 1, 'candidate_id': 'freeze-v1__hindsight__S1__r2__final-old__candidate-1', 'provider_memory_id': 'b2fa69b9-d719-4531-86e9-06c69fc739bb', 'surface': 'SOURCE', 'sha256': '2462e1492a9c8c93ec0d67ca88d4f651bc040d91be012f57bf3ab32e41c59b3d'}`<br>`{'phase': 'final-old', 'rank': 2, 'candidate_id': 'freeze-v1__hindsight__S1__r2__final-old__candidate-2', 'provider_memory_id': '5adc67dd-1658-4ddf-a5e7-7b40e00d84a7', 'surface': 'DERIVED', 'sha256': 'f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6'}`<br>`{'phase': 'final-new', 'rank': 1, 'candidate_id': 'freeze-v1__hindsight__S1__r2__final-new__candidate-1', 'provider_memory_id': 'b2fa69b9-d719-4531-86e9-06c69fc739bb', 'surface': 'SOURCE', 'sha256': '2462e1492a9c8c93ec0d67ca88d4f651bc040d91be012f57bf3ab32e41c59b3d'}`<br>`{'phase': 'final-new', 'rank': 2, 'candidate_id': 'freeze-v1__hindsight__S1__r2__final-new__candidate-2', 'provider_memory_id': '5adc67dd-1658-4ddf-a5e7-7b40e00d84a7', 'surface': 'DERIVED', 'sha256': 'f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6'}` | `{'phase': 'final-old', 'rank': 1, 'candidate_id': 'freeze-v1__hindsight__S1__r3__final-old__candidate-1', 'provider_memory_id': 'dfa63b99-ac6d-467b-b25e-bbc104545a2d', 'surface': 'SOURCE', 'sha256': '252a8d190876609383860b4e9dc7874c89cdc3752f1e61289c7a2244a89bc34a'}`<br>`{'phase': 'final-old', 'rank': 2, 'candidate_id': 'freeze-v1__hindsight__S1__r3__final-old__candidate-2', 'provider_memory_id': 'ea22a6bc-15be-4639-8060-c9eae4fcc5e5', 'surface': 'DERIVED', 'sha256': 'f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6'}`<br>`{'phase': 'final-new', 'rank': 1, 'candidate_id': 'freeze-v1__hindsight__S1__r3__final-new__candidate-1', 'provider_memory_id': 'dfa63b99-ac6d-467b-b25e-bbc104545a2d', 'surface': 'SOURCE', 'sha256': '252a8d190876609383860b4e9dc7874c89cdc3752f1e61289c7a2244a89bc34a'}`<br>`{'phase': 'final-new', 'rank': 2, 'candidate_id': 'freeze-v1__hindsight__S1__r3__final-new__candidate-2', 'provider_memory_id': 'ea22a6bc-15be-4639-8060-c9eae4fcc5e5', 'surface': 'DERIVED', 'sha256': 'f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6'}` |
| **exact_delivered_context_if_already_serialized** | `UNAVAILABLE` | `UNAVAILABLE` | `UNAVAILABLE` |
| **exact_prompt_context_fragment_if_already_serialized** | `UNAVAILABLE` | `UNAVAILABLE` | `UNAVAILABLE` |
| **model_boundary_trace_if_available** | `UNAVAILABLE` | `UNAVAILABLE` | `UNAVAILABLE` |

### 3.2 Preserved Serialized Text (Hindsight S1)

#### Repetition 1 (`freeze-v1__hindsight__S1__r1`)
- **Authoritative Content Text (`v2`):** `freeze-v1__hindsight__S1__r1: Project Alder reports may be sent only to Bob.`
- **Authoritative Content SHA-256:** `ecb4e26bbc1a2f91c214dba0c7cf37fe8267190a68dc0b8418d3c76c4ccb234d`
- **Non-Authoritative Derived Memory SHA-256:** `f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6`
- **Non-Authoritative Content Text:** `MISSING_EXACT_TEXT` (Derived memory record was hashed but raw text bytes were not serialized into Phase 06B JSONL)
- **Delivered Context Text:** `UNAVAILABLE`
- **Prompt Context Fragment:** `UNAVAILABLE`

#### Repetition 2 (`freeze-v1__hindsight__S1__r2`)
- **Authoritative Content Text (`v2`):** `freeze-v1__hindsight__S1__r2: Project Alder reports may be sent only to Bob.`
- **Authoritative Content SHA-256:** `2462e1492a9c8c93ec0d67ca88d4f651bc040d91be012f57bf3ab32e41c59b3d`
- **Non-Authoritative Derived Memory SHA-256:** `f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6`
- **Non-Authoritative Content Text:** `MISSING_EXACT_TEXT` (Derived memory record was hashed but raw text bytes were not serialized into Phase 06B JSONL)
- **Delivered Context Text:** `UNAVAILABLE`
- **Prompt Context Fragment:** `UNAVAILABLE`

#### Repetition 3 (`freeze-v1__hindsight__S1__r3`)
- **Authoritative Content Text (`v2`):** `freeze-v1__hindsight__S1__r3: Project Alder reports may be sent only to Bob.`
- **Authoritative Content SHA-256:** `252a8d190876609383860b4e9dc7874c89cdc3752f1e61289c7a2244a89bc34a`
- **Non-Authoritative Derived Memory SHA-256:** `f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6`
- **Non-Authoritative Content Text:** `MISSING_EXACT_TEXT` (Derived memory record was hashed but raw text bytes were not serialized into Phase 06B JSONL)
- **Delivered Context Text:** `UNAVAILABLE`
- **Prompt Context Fragment:** `UNAVAILABLE`

---

## 4. Scientific Recommendations for Main ChatGPT Review

1. **Mem0 S1 Gate Failure (`MISSING_MODEL_BOUNDARY_TRACE`):** In Mem0, in-place update replaces the source memory text with `v2`. No stale proposition text is in storage. The residual exposure arises from provenance retention. Because Phase 06B executed 0 downstream LLM calls, no delivered context or prompt was assembled. To freeze an RQ3 context, a deterministic prompt template and delivered context mapping must be formally specified.
2. **Hindsight S1 Gate Failure (`MISSING_EXACT_CONTEXT`):** In Hindsight, the non-authoritative candidate (rank 2) is an LLM-derived insight produced during `POST /memories`. Its exact SHA-256 (`f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6`) is identical across all three repetitions, but its raw text bytes were not serialized into Phase 06B dataset files. An exact context cannot be frozen from repository evidence without the exact serialized text.
3. **Downstream Execution Authorization:** Downstream LLM inference remains **STRICTLY UNAUTHORIZED** (`RQ3 CALLS: 0`).
