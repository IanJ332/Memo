# NEXT-LP-01 independent pre-evaluation review 02

Decision: **ACCEPT registration v2 and the exact pre-execution source package below for the bounded offline 48-row study.** Reviewer: delegated agent `/root/nextlp_independent_review`, GPT-6.1 Sol / Medium, independently from registration author and implementation author. This report and its accompanying JSON are genuine reviewer-authored decisions, not platform approval or a live execution grant. Final result review remains separate.

CONVERSATION: NEXT-LP-01 independent review. MODEL: GPT-6.1 Sol / Medium. EXECUTION TARGET: local static source, registration and supplemental unit controls only. JETSTREAM ACTION: NONE.

## Correction to review 01

Review 01 missed an incorrect materialization assumption: original ReferenceMemoryAdapter generic hooks return KNOWN/SOURCE, whereas original Mem0 hooks return UNKNOWN/UNKNOWN. Its acceptance of that v1 Mem0 materialization clause is withdrawn. Preserve review 01 and all v1 bytes as historical records. The error was found in supplemental development controls before the registered study, reported as 63 passes and two failures; it did not arise from registered 48-row results.

Registration v2 replaces the incorrect Reference-default clause with an explicit static facade forwarding only the two actual original Mem0 property `fget` bodies. Those bodies return constants and do not access SDK/client fields. The facade inherits base per-record hooks and normalizes synthetic records through the actual original static Mem0 normalizer. No Mem0 SDK/native constructor is used. This correctly realizes the already-frozen LP01-12 generic-UNKNOWN direct-identity control, without changing its oracle. The unrelated query-helper correction to `scenario.lifecycle_steps` matches the original scenario schema.

## Exact accepted bindings

- Registration v2: `manifests/next-lp-01/registration-v2.json`, 12,589 bytes, SHA-256 `3217aa1c4853a9437f708a60f634c012905634d114a7634cbef927a9f6f88c46`.
- Amendment narrative: `docs/research/next-lp-01/REGISTRATION_AMENDMENT_02.md`, SHA-256 `8121a55c22034811904adabc2d3d744c1240fd4de247b120e15d863942f3810a`.
- Implementation map: `manifests/next-lp-01/implementation-v1.json`, 950 bytes, SHA-256 `8cdcbb12078eebcf58cc38b37a1ba645c2171abf3ba0b82a20ebb5c831319205`.

The five implementation hashes were independently recomputed and matched. They cover the new correction, evaluator, CLI and supplemental tests plus the original R1 immutable-I/O helper. The v1 fixture/oracle hashes remain `576c3fd12da878ef0db3c5b7f493f2880609fc2ef8719e7e658a23e6e9dfb58e` / `e7bd10745fa0fc360449b6c87dc2101110de6b3ab41d38498c2ecf68b1a07f0c`. Review 01 remains SHA-256 `dce0dcfbb547208e5408fc61e8cce5d96d571dbc10d5e206a5ad02f1fc045c60`. The 14 original source maps and frozen fixture/oracle maps are equal between registrations v1 and v2. No original production source was changed.

## Source assessment and verification

Both wrappers invoke the actual original pure producer paths. Original payload/trace and candidates are retained, as are corrected payload/trace. The scorer recomputes correlation from the original normalized record and separately supplied host snapshot; candidate metadata cannot self-assert trusted identity or completeness. Scope and exact child bytes bind every source association. Missing, duplicate, conflicting or extra scoped source bindings stay incomplete; direct identities additionally match the ledger content digest. Derived-child hashes remain distinct from parent content hashes. Generic causal provenance and explicit correlation completeness remain separate. Source-order preservation and association-order independence are covered by supplemental controls.

The paired evaluator preserves fixed fixture/producer/arm keys, complete denominators, UNKNOWN and errors, and supports retained result reproduction. Current-evidence coverage is derived from returned event IDs and independently scoped byte-bound host rows rather than copied from oracle labels. It is a narrow coverage metric, not semantic task success or action permission. The baseline projection's scope/byte loss and storage/trace differences remain visible. All original and corrected source outputs are retained for final inspection.

The final portable `repository_binding()` resolves paths and enforces membership under the resolved repository root before emitting relative path/content identity. Audit resolves a stored review path and compares it to that same normalized membership/content binding; `..`, absolute outside paths and escaping symlinks cannot acquire repository membership. These are scientific custody checks, not authentication of a reviewer or platform authorization. Genuineness of this independent decision comes from the actual reviewer workflow, not a boolean field alone.

Independent command: repository `.venv` Python `-m pytest -q -p no:cacheprovider tests/research/test_next_lp01.py`: **25 passed**, zero failures/skips, 0.38 seconds. These tests use separate supplemental unit records and structurally inspect registration; this reviewer did not call `evaluate_one` on registered fixtures, run the study, or view registered results. The last subsequent portability edit was statically inspected and implementation hashes verified; unchanged controls were not redundantly rerun.

The platform-contract report was inspected as an audit-only prospective design. It preserves the historical stop and unsatisfied gate, does not supply a fake approval reference, and implements no live admission change. Its external documentation retrieval is the audit author's evidence; this reviewer did not independently browse those pages. No live contract acceptance follows from this review.

Independent host-snapshot custody remains an explicit experimental prerequisite, not a cryptographic fact established by this code. The accepted package measures selected synthetic exposure classifications; it establishes no native exploit reachability, model effect, protected-action enforcement, physical erasure, or universal security. Final results/source interpretation must still receive independent review after the one frozen evaluation.
