# Phase 07A — Root-Cause Evidence Extraction

> **Protocol Status:** EVIDENCE EXTRACTION ONLY
> **Root-Cause Conclusion:** NOT ATTEMPTED
> **Target Cells:** Hindsight S4 (`HARD_DELETE_REDERIVE`), OpenViking S4 (`HARD_DELETE_REDERIVE`)
> **Canonical Evidence Sources:** `artifacts/phase06b/derived/20261001T183940Z-1fc4c4929532/freeze-v1-raw-runs.provenance-repaired.jsonl`, `artifacts/phase06b/supplements/attempts/20261002T000350Z-c272b34d2cc3/supplement-raw-runs.jsonl`, `combined-derived-runs.jsonl`

---

## 1. Protocol Frame and Invariants

- **Governing Principle:** *Retrieved != Authoritative*.
- **Scientific Scope:** This document extracts deterministic, empirical evidence from canonical Phase 06B runs for re-derivation lifecycle residual cells (Hindsight S4 and OpenViking S4).
- **Root-Cause Attribution:** Explicitly **NOT ATTEMPTED**. No causal mechanism is asserted or concluded in this phase. Main ChatGPT will perform scientific review.
- **Preserved Error Exclusion:** `freeze-v1__openviking__S0__r2` is a frozen historical provider-crash `ERROR` (`RemoteDisconnected` / `ServiceExitedBeforeReady`) and is **EXCLUDED** from Phase 07 residual analysis.
- **Evidence Discipline:** No fields are fabricated. Missing values are explicitly recorded as `UNAVAILABLE`.

---

## 2. Hindsight S4 (`HARD_DELETE_REDERIVE`) — Root-Cause Evidence

### 2.1 Repetition Evidence Table

| Field | Repetition 1 (`r1`) | Repetition 2 (`r2`) | Repetition 3 (`r3`) |
| :--- | :--- | :--- | :--- |
| **provider** | `hindsight` | `hindsight` | `hindsight` |
| **scenario** | `S4` | `S4` | `S4` |
| **repetition** | `1` | `2` | `3` |
| **run_id** | `freeze-v1__hindsight__S4__r1` | `freeze-v1__hindsight__S4__r2` | `freeze-v1__hindsight__S4__r3` |
| **namespace** | `memlife-freeze-v1-hindsight-S4-r1` | `memlife-freeze-v1-hindsight-S4-r2` | `memlife-freeze-v1-hindsight-S4-r3` |
| **attempt_id** | `20261001T183940Z-1fc4c4929532` | `20261001T183940Z-1fc4c4929532` | `20261001T183940Z-1fc4c4929532` |
| **tested_commit** | `a569a166093c626c5a99a7a33042e0aa7ddb7e74` | `a569a166093c626c5a99a7a33042e0aa7ddb7e74` | `a569a166093c626c5a99a7a33042e0aa7ddb7e74` |
| **exact_visibility_outcome** | `ABSENT` | `ABSENT` | `ABSENT` |
| **authority_exposure_outcome** | `AUTHORITATIVE_ONLY` | `AUTHORITATIVE_ONLY` | `AUTHORITATIVE_ONLY` |
| **residual_signals** | **deleted_or_revoked_descendant_visible**: `False`<br>**nonauthoritative_correlated_derived_visible**: `False`<br>**nonauthoritative_exact_visible**: `False`<br>**reappeared_after_rederivation**: `True`<br>**reappeared_after_restart**: `False`<br>**repetition_authority_disagreement**: `False`<br>**source_derived_authority_disagreement**: `False` | **deleted_or_revoked_descendant_visible**: `False`<br>**nonauthoritative_correlated_derived_visible**: `False`<br>**nonauthoritative_exact_visible**: `False`<br>**reappeared_after_rederivation**: `True`<br>**reappeared_after_restart**: `False`<br>**repetition_authority_disagreement**: `False`<br>**source_derived_authority_disagreement**: `False` | **deleted_or_revoked_descendant_visible**: `False`<br>**nonauthoritative_correlated_derived_visible**: `False`<br>**nonauthoritative_exact_visible**: `False`<br>**reappeared_after_rederivation**: `True`<br>**reappeared_after_restart**: `False`<br>**repetition_authority_disagreement**: `False`<br>**source_derived_authority_disagreement**: `False` |
| **source_provider_ids** | `a2bdf16c-5421-4edf-bfa6-dc4ecd42ffe9`<br>`4e947d71-3a32-4f31-af46-50a80df910c8` | `15b6d607-a22c-4a3f-a3dd-9d3fe5c92fbf`<br>`335a917b-e5bc-47db-910c-bad0ad6120c4` | `6c5a9869-cf46-4833-b317-545df91096b9`<br>`66b4218e-2ceb-4e62-b0e7-cd3cb1e0a0f6` |
| **provider_parent_source_ids** | `a2bdf16c-5421-4edf-bfa6-dc4ecd42ffe9`<br>`4e947d71-3a32-4f31-af46-50a80df910c8` | `15b6d607-a22c-4a3f-a3dd-9d3fe5c92fbf`<br>`335a917b-e5bc-47db-910c-bad0ad6120c4` | `6c5a9869-cf46-4833-b317-545df91096b9`<br>`66b4218e-2ceb-4e62-b0e7-cd3cb1e0a0f6` |
| **provider_derived_ids** | `7226e521-560f-4c1d-b1a1-c01f01f08814`<br>`4aa1a705-ab1a-4e28-8a2a-d7aa5fccc366` | `42e9c866-41a3-4c07-ab3c-ec57e0603d24`<br>`4c95ef05-38bb-44ad-a542-51e7551a406d` | `9eb0dddd-bdd6-4886-b374-2979ead20de5`<br>`b7a7eb59-6f2a-4ea8-ba6d-058bed360f45` |
| **trace_ids** | `82388a22-d238-4578-bd1f-ce4950db828a`<br>`b594d89b-d02c-4595-bb07-12b4b6bb9f38`<br>`cda8f2ab-9692-40ab-8fd4-3eefb0ece341`<br>`370a99ea-1a0f-41a3-aca6-4ba00837130b`<br>`1b6271b9-c756-4a66-a9ae-972b85e9cc5e`<br>`97ff465a-d6ea-4a73-9698-06a188ebaa02` | `bb7c9b6e-9752-435d-9bec-ca244489d854`<br>`4fff7406-abd3-48c5-8ddc-eab78ba83f0a`<br>`1c7a63a1-556f-42dc-9917-d7724f0e2e8d`<br>`55f126d9-2ca7-4a16-a186-e13e02692917` | `5e2fed2b-e8f2-453e-880d-ce617c037d77`<br>`40021650-4107-4187-a3aa-c5e7a95e88ac`<br>`9062acda-5727-43f7-86a2-89d325e0ed8e`<br>`bd2f21ff-7563-4db8-a0c3-f244db488445` |
| **source_lifecycle_state** | `deleted` | `deleted` | `deleted` |
| **derived_lifecycle_state** | `active` | `active` | `active` |
| **retrieval_candidate_ids** | `freeze-v1__hindsight__S4__r1__observe-before-transition__candidate-1`<br>`freeze-v1__hindsight__S4__r1__observe-before-transition__candidate-2`<br>`freeze-v1__hindsight__S4__r1__final__candidate-1`<br>`freeze-v1__hindsight__S4__r1__final__candidate-2` | `freeze-v1__hindsight__S4__r2__observe-before-transition__candidate-1`<br>`freeze-v1__hindsight__S4__r2__observe-before-transition__candidate-2`<br>`freeze-v1__hindsight__S4__r2__final__candidate-1`<br>`freeze-v1__hindsight__S4__r2__final__candidate-2` | `freeze-v1__hindsight__S4__r3__observe-before-transition__candidate-1`<br>`freeze-v1__hindsight__S4__r3__observe-before-transition__candidate-2`<br>`freeze-v1__hindsight__S4__r3__final__candidate-1`<br>`freeze-v1__hindsight__S4__r3__final__candidate-2` |
| **candidate_surfaces** | `DERIVED`<br>`SOURCE`<br>`SOURCE`<br>`DERIVED` | `DERIVED`<br>`SOURCE`<br>`SOURCE`<br>`DERIVED` | `DERIVED`<br>`SOURCE`<br>`SOURCE`<br>`DERIVED` |
| **candidate_provenance** | `KNOWN`<br>`KNOWN`<br>`KNOWN`<br>`KNOWN` | `KNOWN`<br>`KNOWN`<br>`KNOWN`<br>`KNOWN` | `KNOWN`<br>`KNOWN`<br>`KNOWN`<br>`KNOWN` |
| **candidate_authority_state** | `NONAUTHORITATIVE`<br>`NONAUTHORITATIVE`<br>`AUTHORITATIVE`<br>`AUTHORITATIVE` | `NONAUTHORITATIVE`<br>`NONAUTHORITATIVE`<br>`AUTHORITATIVE`<br>`AUTHORITATIVE` | `NONAUTHORITATIVE`<br>`NONAUTHORITATIVE`<br>`AUTHORITATIVE`<br>`AUTHORITATIVE` |
| **before_delete_visibility** | `CANDIDATES_VISIBLE (2 candidates, exact v1 absent)` | `CANDIDATES_VISIBLE (2 candidates, exact v1 absent)` | `CANDIDATES_VISIBLE (2 candidates, exact v1 absent)` |
| **after_delete_visibility** | `ABSENT (inspected via _safe_inspect; intermediate query before rederive not in protocol)` | `ABSENT (inspected via _safe_inspect; intermediate query before rederive not in protocol)` | `ABSENT (inspected via _safe_inspect; intermediate query before rederive not in protocol)` |
| **post_restart_visibility** | `UNAVAILABLE (restart not part of S4 protocol)` | `UNAVAILABLE (restart not part of S4 protocol)` | `UNAVAILABLE (restart not part of S4 protocol)` |
| **post_rederive_visibility** | `CANDIDATES_VISIBLE (2 candidates from write-support, exact v1 absent)` | `CANDIDATES_VISIBLE (2 candidates from write-support, exact v1 absent)` | `CANDIDATES_VISIBLE (2 candidates from write-support, exact v1 absent)` |
| **explicit_rederivation_operation** | `POST /consolidate; poll operation status=completed` | `POST /consolidate; poll operation status=completed` | `POST /consolidate; poll operation status=completed` |
| **retrieved_state_actually_crossed_model_boundary** | `False` | `False` | `False` |

### 2.2 Reconstructed Causal Chain (Hindsight S4)

#### Repetition 1 (`freeze-v1__hindsight__S4__r1`)
```text
1. Source Event: freeze-v1__hindsight__S4__r1__write-v1 (v1) -> freeze-v1__hindsight__S4__r1__write-support (support)
2. Source Memory IDs: ['a2bdf16c-5421-4edf-bfa6-dc4ecd42ffe9', '4e947d71-3a32-4f31-af46-50a80df910c8']
3. Derived Memory IDs: ['7226e521-560f-4c1d-b1a1-c01f01f08814', '4aa1a705-ab1a-4e28-8a2a-d7aa5fccc366']
4. Lifecycle Transition Events: freeze-v1__hindsight__S4__r1__event-06 (DELETE) -> freeze-v1__hindsight__S4__r1__event-07 (REDERIVE) (POST /consolidate; poll operation status=completed)
5. Storage/Derived State After Transition: source_v1=deleted, inspection=v1 absent from storage, support=active
6. Retrieval Candidates (Final Query):
   - Rank 1: ID=4e947d71-3a32-4f31-af46-50a80df910c8 (SOURCE), SHA=f075c6db78f58d6e5a7357519db6b0948d27684320db3b98d6ee98ce2b37b882, Sources=['freeze-v1__hindsight__S4__r1__write-support']
   - Rank 2: ID=4aa1a705-ab1a-4e28-8a2a-d7aa5fccc366 (DERIVED), SHA=3ec69194ac47bc9b00f41651852446d57398828e5d6cb3ea645f6757635a59be, Sources=['freeze-v1__hindsight__S4__r1__write-support']
7. Authority Classification: exact=ABSENT, authority=AUTHORITATIVE_ONLY
8. Delivered Context: delivered_context_sha256=UNAVAILABLE, prompt_fragment=UNAVAILABLE
9. Residual Signal: {'deleted_or_revoked_descendant_visible': False, 'nonauthoritative_correlated_derived_visible': False, 'nonauthoritative_exact_visible': False, 'reappeared_after_rederivation': True, 'reappeared_after_restart': False, 'repetition_authority_disagreement': False, 'source_derived_authority_disagreement': False}
```

#### Repetition 2 (`freeze-v1__hindsight__S4__r2`)
```text
1. Source Event: freeze-v1__hindsight__S4__r2__write-v1 (v1) -> freeze-v1__hindsight__S4__r2__write-support (support)
2. Source Memory IDs: ['15b6d607-a22c-4a3f-a3dd-9d3fe5c92fbf', '335a917b-e5bc-47db-910c-bad0ad6120c4']
3. Derived Memory IDs: ['42e9c866-41a3-4c07-ab3c-ec57e0603d24', '4c95ef05-38bb-44ad-a542-51e7551a406d']
4. Lifecycle Transition Events: freeze-v1__hindsight__S4__r2__event-06 (DELETE) -> freeze-v1__hindsight__S4__r2__event-07 (REDERIVE) (POST /consolidate; poll operation status=completed)
5. Storage/Derived State After Transition: source_v1=deleted, inspection=v1 absent from storage, support=active
6. Retrieval Candidates (Final Query):
   - Rank 1: ID=335a917b-e5bc-47db-910c-bad0ad6120c4 (SOURCE), SHA=0857f48b2e8e25f013aa7b3174f7c0b56ceab20795c0ba013fb30c72bd535141, Sources=['freeze-v1__hindsight__S4__r2__write-support']
   - Rank 2: ID=4c95ef05-38bb-44ad-a542-51e7551a406d (DERIVED), SHA=3ec69194ac47bc9b00f41651852446d57398828e5d6cb3ea645f6757635a59be, Sources=['freeze-v1__hindsight__S4__r2__write-support']
7. Authority Classification: exact=ABSENT, authority=AUTHORITATIVE_ONLY
8. Delivered Context: delivered_context_sha256=UNAVAILABLE, prompt_fragment=UNAVAILABLE
9. Residual Signal: {'deleted_or_revoked_descendant_visible': False, 'nonauthoritative_correlated_derived_visible': False, 'nonauthoritative_exact_visible': False, 'reappeared_after_rederivation': True, 'reappeared_after_restart': False, 'repetition_authority_disagreement': False, 'source_derived_authority_disagreement': False}
```

#### Repetition 3 (`freeze-v1__hindsight__S4__r3`)
```text
1. Source Event: freeze-v1__hindsight__S4__r3__write-v1 (v1) -> freeze-v1__hindsight__S4__r3__write-support (support)
2. Source Memory IDs: ['6c5a9869-cf46-4833-b317-545df91096b9', '66b4218e-2ceb-4e62-b0e7-cd3cb1e0a0f6']
3. Derived Memory IDs: ['9eb0dddd-bdd6-4886-b374-2979ead20de5', 'b7a7eb59-6f2a-4ea8-ba6d-058bed360f45']
4. Lifecycle Transition Events: freeze-v1__hindsight__S4__r3__event-06 (DELETE) -> freeze-v1__hindsight__S4__r3__event-07 (REDERIVE) (POST /consolidate; poll operation status=completed)
5. Storage/Derived State After Transition: source_v1=deleted, inspection=v1 absent from storage, support=active
6. Retrieval Candidates (Final Query):
   - Rank 1: ID=66b4218e-2ceb-4e62-b0e7-cd3cb1e0a0f6 (SOURCE), SHA=f075c6db78f58d6e5a7357519db6b0948d27684320db3b98d6ee98ce2b37b882, Sources=['freeze-v1__hindsight__S4__r3__write-support']
   - Rank 2: ID=b7a7eb59-6f2a-4ea8-ba6d-058bed360f45 (DERIVED), SHA=3ec69194ac47bc9b00f41651852446d57398828e5d6cb3ea645f6757635a59be, Sources=['freeze-v1__hindsight__S4__r3__write-support']
7. Authority Classification: exact=ABSENT, authority=AUTHORITATIVE_ONLY
8. Delivered Context: delivered_context_sha256=UNAVAILABLE, prompt_fragment=UNAVAILABLE
9. Residual Signal: {'deleted_or_revoked_descendant_visible': False, 'nonauthoritative_correlated_derived_visible': False, 'nonauthoritative_exact_visible': False, 'reappeared_after_rederivation': True, 'reappeared_after_restart': False, 'repetition_authority_disagreement': False, 'source_derived_authority_disagreement': False}
```

---

## 3. OpenViking S4 (`HARD_DELETE_REDERIVE`) — Root-Cause Evidence

### 3.1 Repetition Evidence Table

| Field | Repetition 1 (`r1`) | Repetition 2 (`r2`) | Repetition 3 (`r3`) |
| :--- | :--- | :--- | :--- |
| **provider** | `openviking` | `openviking` | `openviking` |
| **scenario** | `S4` | `S4` | `S4` |
| **repetition** | `1` | `2` | `3` |
| **run_id** | `freeze-v1__openviking__S4__r1` | `freeze-v1__openviking__S4__r2` | `freeze-v1__openviking__S4__r3` |
| **namespace** | `memlife-freeze-v1-openviking-S4-r1` | `memlife-freeze-v1-openviking-S4-r2` | `memlife-freeze-v1-openviking-S4-r3` |
| **attempt_id** | `20261002T000350Z-c272b34d2cc3` | `20261002T000350Z-c272b34d2cc3` | `20261002T000350Z-c272b34d2cc3` |
| **tested_commit** | `58e154a62e1c52e6a478e8f0e2041b437023582a` | `58e154a62e1c52e6a478e8f0e2041b437023582a` | `58e154a62e1c52e6a478e8f0e2041b437023582a` |
| **exact_visibility_outcome** | `ABSENT` | `ABSENT` | `ABSENT` |
| **authority_exposure_outcome** | `AUTHORITATIVE_ONLY` | `NONE` | `AUTHORITATIVE_ONLY` |
| **residual_signals** | **deleted_or_revoked_descendant_visible**: `False`<br>**nonauthoritative_correlated_derived_visible**: `False`<br>**nonauthoritative_exact_visible**: `False`<br>**reappeared_after_rederivation**: `True`<br>**reappeared_after_restart**: `False`<br>**repetition_authority_disagreement**: `False`<br>**source_derived_authority_disagreement**: `False` | **deleted_or_revoked_descendant_visible**: `False`<br>**nonauthoritative_correlated_derived_visible**: `False`<br>**nonauthoritative_exact_visible**: `False`<br>**reappeared_after_rederivation**: `False`<br>**reappeared_after_restart**: `False`<br>**repetition_authority_disagreement**: `False`<br>**source_derived_authority_disagreement**: `False` | **deleted_or_revoked_descendant_visible**: `False`<br>**nonauthoritative_correlated_derived_visible**: `False`<br>**nonauthoritative_exact_visible**: `False`<br>**reappeared_after_rederivation**: `True`<br>**reappeared_after_restart**: `False`<br>**repetition_authority_disagreement**: `False`<br>**source_derived_authority_disagreement**: `False` |
| **source_provider_ids** | `[]` | `[]` | `[]` |
| **provider_parent_source_ids** | `freeze-v1__openviking__S4__r1__write-v1`<br>`freeze-v1__openviking__S4__r1__write-support` | `[]` | `freeze-v1__openviking__S4__r3__write-v1`<br>`freeze-v1__openviking__S4__r3__write-support` |
| **provider_derived_ids** | `viking://user/default/memories/entities/work/project_larch.md`<br>`viking://user/default/memories/entities/person/analyst_7.md` | `[]` | `viking://user/default/memories/events/2026/10/02/larch_report_sharing.md`<br>`viking://user/default/memories/entities/work/project_larch.md`<br>`viking://user/default/memories/entities/person/analyst_7.md` |
| **trace_ids** | `UNAVAILABLE` | `UNAVAILABLE` | `UNAVAILABLE` |
| **source_lifecycle_state** | `deleted` | `deleted` | `deleted` |
| **derived_lifecycle_state** | `active` | `UNAVAILABLE` | `active` |
| **retrieval_candidate_ids** | `freeze-v1__openviking__S4__r1__observe-before-transition__candidate-1`<br>`freeze-v1__openviking__S4__r1__observe-before-transition__candidate-2`<br>`freeze-v1__openviking__S4__r1__final__candidate-1` | `[]` | `freeze-v1__openviking__S4__r3__observe-before-transition__candidate-1`<br>`freeze-v1__openviking__S4__r3__observe-before-transition__candidate-2`<br>`freeze-v1__openviking__S4__r3__final__candidate-1` |
| **candidate_surfaces** | `DERIVED`<br>`DERIVED`<br>`DERIVED` | `[]` | `DERIVED`<br>`DERIVED`<br>`DERIVED` |
| **candidate_provenance** | `KNOWN`<br>`KNOWN`<br>`KNOWN` | `[]` | `KNOWN`<br>`KNOWN`<br>`KNOWN` |
| **candidate_authority_state** | `NONAUTHORITATIVE`<br>`NONAUTHORITATIVE`<br>`AUTHORITATIVE` | `[]` | `NONAUTHORITATIVE`<br>`NONAUTHORITATIVE`<br>`AUTHORITATIVE` |
| **before_delete_visibility** | `CANDIDATES_VISIBLE (2 candidates, exact v1 absent)` | `ABSENT` | `CANDIDATES_VISIBLE (2 candidates, exact v1 absent)` |
| **after_delete_visibility** | `ABSENT (inspected via _safe_inspect; intermediate query before rederive not in protocol)` | `ABSENT (inspected via _safe_inspect; intermediate query before rederive not in protocol)` | `ABSENT (inspected via _safe_inspect; intermediate query before rederive not in protocol)` |
| **post_restart_visibility** | `UNAVAILABLE (restart not part of S4 protocol)` | `UNAVAILABLE (restart not part of S4 protocol)` | `UNAVAILABLE (restart not part of S4 protocol)` |
| **post_rederive_visibility** | `CANDIDATES_VISIBLE (1 candidates from write-support, exact v1 absent)` | `ABSENT` | `CANDIDATES_VISIBLE (1 candidates from write-support, exact v1 absent)` |
| **explicit_rederivation_operation** | `POST /sessions/{id}/extract` | `POST /sessions/{id}/extract` | `POST /sessions/{id}/extract` |
| **retrieved_state_actually_crossed_model_boundary** | `False` | `False` | `False` |

### 3.2 Reconstructed Causal Chain (OpenViking S4)

#### Repetition 1 (`freeze-v1__openviking__S4__r1`)
```text
1. Source Event: freeze-v1__openviking__S4__r1__write-v1 (v1) -> freeze-v1__openviking__S4__r1__write-support (support)
2. Source Memory IDs: []
3. Derived Memory IDs: ['viking://user/default/memories/entities/work/project_larch.md', 'viking://user/default/memories/entities/person/analyst_7.md']
4. Lifecycle Transition Events: freeze-v1__openviking__S4__r1__event-06 (DELETE) -> freeze-v1__openviking__S4__r1__event-07 (REDERIVE) (POST /sessions/{id}/extract)
5. Storage/Derived State After Transition: source_v1=deleted, inspection=v1 absent from storage, support=active
6. Retrieval Candidates (Final Query):
   - Rank 1: ID=viking://user/default/memories/entities/person/analyst_7.md (DERIVED), Score=1.0, SHA=54bb4e2dda8723cd87b3fb9f050f1d561bb3305cdd20d924b777a8913b5f43c0, Sources=['freeze-v1__openviking__S4__r1__write-support']
7. Authority Classification: exact=ABSENT, authority=AUTHORITATIVE_ONLY
8. Delivered Context: delivered_context_sha256=UNAVAILABLE, prompt_fragment=UNAVAILABLE
9. Residual Signal: {'deleted_or_revoked_descendant_visible': False, 'nonauthoritative_correlated_derived_visible': False, 'nonauthoritative_exact_visible': False, 'reappeared_after_rederivation': True, 'reappeared_after_restart': False, 'repetition_authority_disagreement': False, 'source_derived_authority_disagreement': False}
```

#### Repetition 2 (`freeze-v1__openviking__S4__r2`)
```text
1. Source Event: freeze-v1__openviking__S4__r2__write-v1 (v1) -> freeze-v1__openviking__S4__r2__write-support (support)
2. Source Memory IDs: []
3. Derived Memory IDs: []
4. Lifecycle Transition Events: freeze-v1__openviking__S4__r2__event-06 (DELETE) -> freeze-v1__openviking__S4__r2__event-07 (REDERIVE) (POST /sessions/{id}/extract)
5. Storage/Derived State After Transition: source_v1=deleted, inspection=v1 absent from storage, support=active
6. Retrieval Candidates (Final Query):
   - None (0 candidates retrieved)
7. Authority Classification: exact=ABSENT, authority=NONE
8. Delivered Context: delivered_context_sha256=UNAVAILABLE, prompt_fragment=UNAVAILABLE
9. Residual Signal: {'deleted_or_revoked_descendant_visible': False, 'nonauthoritative_correlated_derived_visible': False, 'nonauthoritative_exact_visible': False, 'reappeared_after_rederivation': False, 'reappeared_after_restart': False, 'repetition_authority_disagreement': False, 'source_derived_authority_disagreement': False}
```

#### Repetition 3 (`freeze-v1__openviking__S4__r3`)
```text
1. Source Event: freeze-v1__openviking__S4__r3__write-v1 (v1) -> freeze-v1__openviking__S4__r3__write-support (support)
2. Source Memory IDs: []
3. Derived Memory IDs: ['viking://user/default/memories/events/2026/10/02/larch_report_sharing.md', 'viking://user/default/memories/entities/work/project_larch.md', 'viking://user/default/memories/entities/person/analyst_7.md']
4. Lifecycle Transition Events: freeze-v1__openviking__S4__r3__event-06 (DELETE) -> freeze-v1__openviking__S4__r3__event-07 (REDERIVE) (POST /sessions/{id}/extract)
5. Storage/Derived State After Transition: source_v1=deleted, inspection=v1 absent from storage, support=active
6. Retrieval Candidates (Final Query):
   - Rank 1: ID=viking://user/default/memories/entities/person/analyst_7.md (DERIVED), Score=0.8211756944656372, SHA=461c66d2d5b9a0b63b271977db3e0ce100b9c76cb2f2742cf8a8eda694f3ad1d, Sources=['freeze-v1__openviking__S4__r3__write-support']
7. Authority Classification: exact=ABSENT, authority=AUTHORITATIVE_ONLY
8. Delivered Context: delivered_context_sha256=UNAVAILABLE, prompt_fragment=UNAVAILABLE
9. Residual Signal: {'deleted_or_revoked_descendant_visible': False, 'nonauthoritative_correlated_derived_visible': False, 'nonauthoritative_exact_visible': False, 'reappeared_after_rederivation': True, 'reappeared_after_restart': False, 'repetition_authority_disagreement': False, 'source_derived_authority_disagreement': False}
```

---

## 4. Deterministic Side-by-Side Repetition Comparison

### 4.1 Hindsight S4: Repetition Differences (r1 vs r2 vs r3)

| Stage | Repetition 1 (`r1`) | Repetition 2 (`r2`) | Repetition 3 (`r3`) | Factual Difference Observed |
| :--- | :--- | :--- | :--- | :--- |
| **SOURCE_STATE** | source_provider_ids=[]; provider_parent_source_ids=[a2bdf16c-..., 4e947d71-...]; v1 deleted via DELETE /documents/{document_id} | source_provider_ids=[15b6d607-..., 335a917b-...]; provider_parent_source_ids=[15b6d607-..., 335a917b-...]; v1 deleted via DELETE /documents/{document_id} | source_provider_ids=[6c5a9869-..., 66b4218e-...]; provider_parent_source_ids=[6c5a9869-..., 66b4218e-...]; v1 deleted via DELETE /documents/{document_id} | r1 source_provider_ids is empty due to surface filtering while r2/r3 contain 2 source IDs. All 3 delete v1 identically. |
| **DERIVED_STATE** | 2 derived IDs (pre: 7226e521-..., post: 4aa1a705-...); pre derived sha=03f5c993..., post derived sha=3ec69194... | 2 derived IDs (pre: 42e9c866-..., post: 4c95ef05-...); pre derived sha=03f5c993..., post derived sha=3ec69194... | 2 derived IDs (pre: 9eb0dddd-..., post: b7a7eb59-...); pre derived sha=03f5c993..., post derived sha=3ec69194... | UUIDs differ per run; content SHA-256 for pre-transition derived memory is identical across r1, r2, r3 (03f5c993...); content SHA-256 for post-rederive derived memory is identical across r1, r2, r3 (3ec69194...). |
| **RETRIEVAL** | 4 retrievals total: pre-transition 2 (rank 1 DERIVED, rank 2 SOURCE); final 2 (rank 1 SOURCE, rank 2 DERIVED from write-support); score=UNAVAILABLE | 4 retrievals total: pre-transition 2 (rank 1 DERIVED, rank 2 SOURCE); final 2 (rank 1 SOURCE, rank 2 DERIVED from write-support); score=UNAVAILABLE | 4 retrievals total: pre-transition 2 (rank 1 DERIVED, rank 2 SOURCE); final 2 (rank 1 SOURCE, rank 2 DERIVED from write-support); score=UNAVAILABLE | Retrieval structure is identical (2 pre, 2 final). In final, rank 1 source content sha differs slightly between r1/r3 (f075c6db...) and r2 (0857f48b...) due to run_id prefix in text. |
| **AUTHORITY_CLASSIFICATION** | exact_visibility_outcome=ABSENT, authority_exposure_outcome=AUTHORITATIVE_ONLY, residual_signals.reappeared_after_rederivation=True | exact_visibility_outcome=ABSENT, authority_exposure_outcome=AUTHORITATIVE_ONLY, residual_signals.reappeared_after_rederivation=True | exact_visibility_outcome=ABSENT, authority_exposure_outcome=AUTHORITATIVE_ONLY, residual_signals.reappeared_after_rederivation=True | None. All 3 repetitions classify identically as ABSENT, AUTHORITATIVE_ONLY, and reappeared_after_rederivation=True. |
| **MODEL_BOUNDARY** | delivered_context_sha256=null, downstream_decision_model_calls=0, rq3_calls=0; crossed_boundary=False | delivered_context_sha256=null, downstream_decision_model_calls=0, rq3_calls=0; crossed_boundary=False | delivered_context_sha256=null, downstream_decision_model_calls=0, rq3_calls=0; crossed_boundary=False | None. Zero downstream calls crossed model boundary across all 3 repetitions. |

### 4.2 OpenViking S4: Repetition Differences (r1 vs r2 vs r3)

| Stage | Repetition 1 (`r1`) | Repetition 2 (`r2`) | Repetition 3 (`r3`) | Factual Difference Observed |
| :--- | :--- | :--- | :--- | :--- |
| **SOURCE_STATE** | source_provider_ids=[]; provider_parent_source_ids=[write-v1, write-support]; v1 deleted via DELETE /api/v1/fs | source_provider_ids=[]; provider_parent_source_ids=[]; v1 deleted via DELETE /api/v1/fs | source_provider_ids=[]; provider_parent_source_ids=[write-v1, write-support]; v1 deleted via DELETE /api/v1/fs | r2 has empty provider_parent_source_ids ([]), whereas r1 and r3 recorded 2 parent source event IDs. |
| **DERIVED_STATE** | 2 derived URIs (entities/work/project_larch.md, entities/person/analyst_7.md) | 0 derived URIs ([]) | 3 derived URIs (events/.../larch_report_sharing.md, entities/work/project_larch.md, entities/person/analyst_7.md) | r2 produced 0 derived IDs; r1 produced 2 derived IDs; r3 produced 3 derived IDs (including an additional event memory). |
| **RETRIEVAL** | 3 retrievals: pre-transition 2 (project_larch score=0.834, analyst_7 score=0.831); final 1 (analyst_7 score=1.0) | 0 retrievals: pre-transition 0; final 0 | 3 retrievals: pre-transition 2 (larch_report_sharing score=0.884, project_larch score=0.841); final 1 (analyst_7 score=0.821) | r2 retrieved 0 candidates across all phases; r1 and r3 each retrieved 2 pre-transition and 1 final candidate, but top pre-transition candidate differed (project_larch in r1 vs larch_report_sharing in r3) and scores varied. |
| **AUTHORITY_CLASSIFICATION** | exact_visibility_outcome=ABSENT, authority_exposure_outcome=AUTHORITATIVE_ONLY, residual_signals.reappeared_after_rederivation=True | exact_visibility_outcome=ABSENT, authority_exposure_outcome=NONE, residual_signals.reappeared_after_rederivation=False | exact_visibility_outcome=ABSENT, authority_exposure_outcome=AUTHORITATIVE_ONLY, residual_signals.reappeared_after_rederivation=True | r2 produced authority_exposure_outcome=NONE and reappeared_after_rederivation=False due to 0 candidates; r1 and r3 produced AUTHORITATIVE_ONLY and reappeared_after_rederivation=True. |
| **MODEL_BOUNDARY** | delivered_context_sha256=null, downstream_decision_model_calls=0, rq3_calls=0; crossed_boundary=False | delivered_context_sha256=null, downstream_decision_model_calls=0, rq3_calls=0; crossed_boundary=False | delivered_context_sha256=null, downstream_decision_model_calls=0, rq3_calls=0; crossed_boundary=False | None. Zero downstream calls crossed model boundary across all 3 repetitions. |

---

## 5. Summary of Available vs Missing Evidence

### Available Evidence
- Complete operation sequence, native operations, and timing latencies for all 6 repetitions.
- Complete authority ledger, transitions, and logical fact statuses.
- Candidate retrieval records with rank, memory surface, provenance status, and exact content SHA-256.
- Explicit re-derivation calls (`POST /consolidate` for Hindsight; `POST /sessions/{id}/extract` for OpenViking).
- OpenViking similarity scores recorded for retrieved candidates.

### Missing / Unavailable Evidence
- `delivered_context_sha256`: Not serialized in Phase 06B (`null`).
- `exact prompt-context fragment`: No downstream prompt construction was performed.
- `model-boundary trace`: Zero downstream decision model calls crossed the model boundary (`rq3_calls = 0`).
- Intermediate query between hard delete and re-derivation was not included in the S4 protocol (only `_safe_inspect` ran).
- Raw text bytes of derived memory records were not serialized in JSONL (only SHA-256 hashes are recorded).
