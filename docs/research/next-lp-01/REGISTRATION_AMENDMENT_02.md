# NEXT-LP-01 registration amendment 02

CONVERSATION: Owner-authorized NEXT-LP-01, independent prospective registration amendment.
MODEL: GPT-6.1 Sol / High; security-critical fixture realization and source identity.
EXECUTION TARGET: Local registration artifacts and static original source inspection only.
JETSTREAM ACTION: NONE.

This prospective amendment corrects the Mem0 trace-hook materialization clause **before the registered 48-row evaluation**. Root reported that supplemental unit-development controls found two failures with 63 passes. Those controls are not registered study observations and their original record is retained separately. No fixture, oracle, original source pin, hypothesis, association, row count or stopping rule changes. The independent registration author has not run either producer/classifier arm.

The v1 wording incorrectly proposed `ReferenceMemoryAdapter` default trace hooks as a way to materialize Mem0's generic provider provenance UNKNOWN. Original source inspection establishes that Reference overrides its generic trace properties to KNOWN and SOURCE, whereas `Mem0MemoryAdapter.trace_provenance_status` and `.trace_source_surface` return UNKNOWN and UNKNOWN. The already-frozen LP01-12 control therefore needs the actual Mem0 property values to instantiate its intended condition. This is a harness materialization defect, not an oracle change or experimental result.

[registration-v2.json](../../../manifests/next-lp-01/registration-v2.json) replaces only that Mem0 materialization clause with a declared static source projection:

- Normalize synthetic Mem0 rows through the actual `Mem0MemoryAdapter._normalized_record`.
- Use a test-only `ReferenceMemoryAdapter` subclass that forwards **only** the original pure properties via `Mem0MemoryAdapter.trace_provenance_status.fget(self)` and `Mem0MemoryAdapter.trace_source_surface.fget(self)`.
- Inherit the original base per-record trace hooks. Every Mem0 fixture still has an empty exposed-source list.
- Never instantiate `Mem0MemoryAdapter`, an SDK/client or a native service. The facade is static source projection, not a native Mem0 instance, native qualification or provider observation.

Both actual original producer paths remain unchanged and are still called by the evaluator. The correction remains a separately versioned projection over their outputs. Forwarding original pure properties is necessary to preserve the frozen distinction between generic causal provenance and separately complete direct host identity; it supplies no provider evidence.

A second supplemental unit issue used nonexistent `scenario.steps` rather than the actual `scenario.lifecycle_steps` field. Correcting that query-helper reference is a harness implementation fix with no registration or oracle effect.

The predecessor registration remains preserved at SHA-256 `dea8b1699c185a39d4ea5086362d7683e5ad67d5c88cebe3dba43ff1e71680e3`. The complete v2 registration SHA-256 is **`3217aa1c4853a9437f708a60f634c012905634d114a7634cbef927a9f6f88c46`**. Its original 14 source pins and frozen artifact bindings are identical to v1:

| Preserved artifact | SHA-256 |
| --- | --- |
| fixtures-v1.json | `576c3fd12da878ef0db3c5b7f493f2880609fc2ef8719e7e658a23e6e9dfb58e` |
| oracle-v1.json | `e7bd10745fa0fc360449b6c87dc2101110de6b3ab41d38498c2ecf68b1a07f0c` |
| REGISTRATION.md | `18f9020eee6d0f768fd0c7c6104cdcaff73082f33f06c7ff9700371ee758000d` |
| PRE_EVALUATION_REVIEW_01.md | `dce0dcfbb547208e5408fc61e8cce5d96d571dbc10d5e206a5ad02f1fc045c60` |

These files, plus registration-v1.json, were hashed before and after creating v2 and remained unchanged. The prior independent review is historical and does not accept the amended unseen evaluator. A new genuine independent pre-evaluation review must accept v2 and its exact source projection before study execution. Preserve every original study row, UNKNOWN and error; no adaptive replacement or fixture/oracle changes after observation. The study remains exactly 12 fixed coverage cases × two actual original producer paths × two arms = 48 deterministic rows, with no native or model collection.
