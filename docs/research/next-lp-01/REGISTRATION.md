# NEXT-LP-01 v1 registration

CONVERSATION: Owner-authorized NEXT-LP-01 offline study, independent registration author.
MODEL: GPT-6.1 Sol / High; independent scientific design and security-critical identity semantics.
EXECUTION TARGET: Local synthetic normalization and exposure classification in the synchronized MEMO worktree; repository `.venv` only.
JETSTREAM ACTION: NONE.

This registration was authored by delegated agent `/root/nextlp_registration`, independently from the versioned correction implementer. The author inspected original source and the owner's scope, but did not execute either classifier arm or observe corrected results. Registration status is **REGISTERED BEFORE CORRECTED EVALUATION**; results and independent review belong to separate artifacts. No acceptance receipt is asserted here.

The original production basis is `effda0c053bf03723b8089bc331e6b152ef9ab31`. Reviewed Track B candidate `d3c844adf2d7d1d32c36a04e45938f91203acbad` was synchronized through PR #21 to verified main `a6bc55057fbb901d141a14befc2370e8f474b937` before any registration write. The 14 original source byte pins in [registration-v1.json](../../../manifests/next-lp-01/registration-v1.json) were checked against both the original Git blobs and synchronized working files. Production source is unchanged by registration.

The question is whether independently held host associations and explicit correlation completeness prevent unsupported authoritative-exposure classifications while preserving legitimate current evidence. This is a deterministic measurement experiment, not an action-enforcement or model-safety benchmark. The governing rule remains **Retrieved != Authoritative**.

## Prospective design refinement

The earlier [related-work proposal](../security-track-b-v1/RELATED_WORK.md) suggested 2 ancestry classes × 3 mapping conditions × 2 representations. The owner's subsequent required targets also include metadata identity spoofing, supersession, deleted ancestry, inconsistent scope or bytes, conflicting associations, and benign direct identity with generic provenance UNKNOWN. That original factorial cannot cover all of those within 12 fixed records. Before any corrected evaluation, this registration therefore selects **12 coverage cases**, preserving one equivalent object/JSON pair. It does not claim factorial coverage or independent sampling of the pair.

| ID | Fixed coverage | Oracle exposure | Complete | Current evidence |
| --- | --- | --- | --- | --- |
| LP01-01 | Current + current ancestry, object | AUTHORITATIVE_ONLY | yes | yes |
| LP01-02 | Same record/associations, JSON round trip | AUTHORITATIVE_ONLY | yes | yes |
| LP01-03 | Mem0 metadata names real host event; no host association | UNKNOWN_PROVENANCE | no | no |
| LP01-04 | Current + revoked ancestry; only current source mapped | UNKNOWN_PROVENANCE | no | yes, partial |
| LP01-05 | Both exposed sources unmapped | UNKNOWN_PROVENANCE | no | no |
| LP01-06 | Complete current + superseded lineage | AUTHORITATIVE_AND_NONAUTHORITATIVE | yes | yes |
| LP01-07 | Complete current + revoked lineage | AUTHORITATIVE_AND_NONAUTHORITATIVE | yes | yes |
| LP01-08 | Complete deleted-only ancestry | NONAUTHORITATIVE_ONLY | yes | no |
| LP01-09 | Direct ID association belongs to other namespace | UNKNOWN_PROVENANCE | no | no |
| LP01-10 | Direct ID association binds other content bytes | UNKNOWN_PROVENANCE | no | no |
| LP01-11 | Conflicting duplicate scoped native-ID associations | UNKNOWN_PROVENANCE | no | no |
| LP01-12 | Benign direct current identity; generic provenance UNKNOWN | AUTHORITATIVE_ONLY | yes | yes |

Every retrieved record's own lifecycle hint remains ACTIVE. The independent host ledger separately contains active, superseded, revoked and deleted source entries. This prevents the child hint from deciding ancestor authority. The content and mapping cases are selected synthetic fixtures and support no prevalence estimate.

## Independent oracle and custody

[fixtures-v1.json](../../../manifests/next-lp-01/fixtures-v1.json) holds the records, the original-schema host authority ledger, and independently held host associations. [oracle-v1.json](../../../manifests/next-lp-01/oracle-v1.json) holds expected exposure, completeness and current-evidence labels. Neither file contains anticipated baseline observations or fabricated experimental results.

An association binds `(provider, namespace, record_id, SHA256(exact UTF-8 record content), source_native_id)` to a host ledger event. It is supplied from a host-authored snapshot, outside provider metadata. For a direct record, the source ID equals the record ID and its content matches the ledger source-content digest. For a derived record, each exposed source ID requires a separate association bound to the retrieved child's bytes; those child bytes need not equal each parent's bytes. Another namespace or another content version cannot lend its binding. Missing, duplicate or conflicting scoped bindings remain UNKNOWN, with no arbitrary choice.

The experiment assumes independent ownership of this snapshot. It does not establish cryptographic custody or show that any native provider exposes authenticated lineage. Provider-controlled metadata, content similarity, retrieval rank and an ACTIVE child hint never create host identity.

**Exposure and current-proposition validity are distinct.** Complete current-plus-superseded ancestry is mixed authority exposure, not UNKNOWN, and the independently supported current proposition remains current evidence. The superseded source acquires no renewed authority. The same distinction applies to complete current-plus-revoked ancestry. This does not certify whole-record truth or permission to execute an action. LP01-04 contains a supported current proposition but unresolved whole-source exposure; utility success never permits dropping its unresolved ancestor.

The primary complete-evidence utility denominator is LP01-01, LP01-02, LP01-06, LP01-07 and LP01-12: expected complete **and** benign current evidence. LP01-04 is reported separately as partial current evidence. Blanket UNKNOWN on every generic provenance UNKNOWN would incorrectly lose LP01-12; blanket AUTHORITATIVE_ONLY on every record with any current support would incorrectly erase mixed or unresolved exposure.

## Actual producer paths and paired arms

Use the same normalized record and same ledger through both actual original pure producer paths:

1. `memlife.runner.storage_batch._retrieval_payload`
2. `memlife.runner.provenance.ProvenanceTraceRunner._retrieval_trace`

Evaluate original `normalize_authority_exposure` and the versioned correction, for exactly **12 × 2 × 2 = 48 rows**. Do not copy a producer into the harness or simulate its output. The correction may wrap the actual producer projection and add independently evidenced correlation; original frozen producer/classifier bytes remain unchanged. Preserve each original producer's source IDs, generic provenance status and payload/trace in results. Source-ID and mapping completeness disagreement must remain visible.

The storage producer unions provider metadata, exposed-source maps and the direct-record map. The trace producer prefers exposed-source maps when exposed IDs exist, falls back to direct mapping otherwise, and records incomplete exposed-source provenance UNKNOWN. These differences are part of the comparison, not harmonized away.

For original interfaces, project the fixed host association rows by native source ID only: exactly one distinct event ID becomes the storage set and trace scalar; conflicting distinct IDs cause that native ID to be omitted symmetrically. Do not choose the first or last event. Preserve this conflict diagnostic. Original map interfaces cannot represent provider, namespace or content-digest bindings; the explicit loss explains the scope/byte cases and is not evidence of a native-provider exploit. The corrected arm receives the same original producer output plus the intact independently held host snapshot.

Mem0 fixtures use only `Mem0MemoryAdapter._normalized_record`, followed by `ReferenceMemoryAdapter` default pure trace hooks; no Mem0 client is constructed. This is a normalized-record-boundary test. Hindsight fixtures use the actual static normalizer and pure hooks with a transport that raises on every request. Construct synthetic Hindsight rows with native `state=valid`, `fact_type=observation` when parent IDs exist, and `source_memory_ids` from the frozen source list. Arbitrary metadata is tested through Mem0 because Hindsight's static normalizer does not retain it. JSON_ROUNDTRIP means `MemoryRecord.model_validate_json(record.model_dump_json())` before either producer. The equivalent pair shares every semantic record and association field.

No provider operation, hosted model or embedding request, native service, container, network, local browser, SSH, Jetstream or protected dispatch is needed or authorized by this registration. Existing RQ4 mediation may inform versioned implementation, but a scoring repair is not evidence of actual execution protection. The separate conditional B3 lifecycle-normalization finding remains outside the primary study.

## Frozen artifacts and stopping rule

| Artifact | SHA-256 |
| --- | --- |
| fixtures-v1.json | `576c3fd12da878ef0db3c5b7f493f2880609fc2ef8719e7e658a23e6e9dfb58e` |
| oracle-v1.json | `e7bd10745fa0fc360449b6c87dc2101110de6b3ab41d38498c2ecf68b1a07f0c` |
| registration-v1.json | `dea8b1699c185a39d4ea5086362d7683e5ad67d5c88cebe3dba43ff1e71680e3` |

Freeze these fixture/oracle bytes and original source pins before evaluating corrected code. Run one reviewed frozen evaluator over all 48 fixed rows. Preserve UNKNOWN and errors, with no replacement, adaptive expansion or oracle/fixture changes after observation. If a later correction changes evaluated code, retain all original results and identify the new evaluator/results version explicitly.

Report false authoritative-only outcomes, exact exposure agreement, incomplete-source UNKNOWN detection, missing-lineage handling, producer disagreement, complete benign-current utility and corresponding false positives/negatives. Report full paired rows, generic provenance separately from explicit correlation completeness, and row-level failures. Any unsupported authoritative-only result blocks promotion; every complete benign-current case must retain its correct exposure and usable current evidence, and the complete deleted-only case must remain nonauthoritative. A deterministic zero proves these fixtures pass only.

Independent review must assess hypotheses, oracle independence, exact pairing, source identity, trusted snapshot handling, completeness, benign utility, implementation and interpretation. Review acceptance belongs to an authentic separate reviewer artifact. No sealed R1, R2, LC12 or prior Track B evidence is reclassified or rerun.
