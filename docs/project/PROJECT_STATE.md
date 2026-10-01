# Project State

This is the compact continuation map. Detailed evidence remains in linked phase
documents and manifests.

| Phase | Status | Important commit | Stable outcome / artifact | Continuation lesson or limitation |
| --- | --- | --- | --- | --- |
| 01 — bootstrap | PASS | `e524eb53e3f5242466f723dc8ec2847f2e508f21` | Provider-independent models, adapter contract, reference provider ([phase doc](../phases/PHASE_01_MEMLIFE_BOOTSTRAP.md)) | No real provider or enforcement yet. |
| 02A — Mem0 local | PASS | `669002e` phase HEAD | Mem0 2.2.1 adapter and local lifecycle/persistence ([phase doc](../phases/PHASE_02_PROVIDER_BRINGUP.md)) | Provider behavior is observed, not universal. |
| 02B0 — Jetstream automation | PASS | `b140e204c14bef8b9c72de62c3f22bffe6e3839c` | Managed lifecycle, owned temporary FIP, safe cleanup ([automation doc](../infrastructure/JETSTREAM2_AUTOMATION.md)) | Only run after explicit authorization. |
| 02B — Mem0 Jetstream | PASS | `813a32ad1b14736b08ba13f819cb18a8c22b6a34` tested | Persistent-volume Mem0 parity and reconstruction ([phase doc](../phases/PHASE_02B_MEM0_JETSTREAM.md)) | One pinned VM/provider/configuration. |
| 03 — lifecycle harness | PASS | `989af429749841024c2c03ab2b67c49968884648` | Provider-independent scenarios and exact visibility ([phase doc](../phases/PHASE_03_LIFECYCLE_HARNESS.md)) | Exact matching does not infer semantic residue. |
| 03B — provenance trace | PASS | `c125a59740819f264b5d57c67cde293fbf490346` | Trace and pre-LLM enforcement boundaries ([phase doc](../phases/PHASE_03B_PROVENANCE_TRACE.md)) | Unobserved lineage remains unknown. |
| 04 — Hindsight | PASS | `3851543d6d5ef013fbe635bfe495c443227c076c` tested; `b9913a2` phase HEAD | Hindsight 0.10.1 lifecycle, restart, provenance, derived-state probe ([phase doc](../phases/PHASE_04_HINDSIGHT_BRINGUP.md)) | Harness/provider environments must stay isolated. |
| 05 — OpenViking | PASS | `aa976a7d9b2ef37d8e8ba49b4c5091c1ec83e75e` live; `1436b55` phase HEAD | OpenViking 0.4.22 task quiescence, persistence, memory-diff correlation ([phase doc](../phases/PHASE_05_OPENVIKING_PREPARATION.md)) | Strict readiness and owned-process evidence are essential. |
| 06A — calibration/freeze | PASS | `ca2fd9fd7ea91623888722a7afa656ec3dc37797` tested; `f11a57b` phase HEAD | Mem0 calibration and immutable [Freeze v1](../experiments/EXPERIMENT_FREEZE_V1.md) | Protocol changes require freeze change control. |
| 06B — storage batch | PARTIAL | `a569a166093c626c5a99a7a33042e0aa7ddb7e74` tested | 32/42 runs; OpenViking S0 r2 `ERROR` ([phase doc](../phases/PHASE_06B_STORAGE_LIFECYCLE_BATCH.md)) | Never rerun executed IDs or majority-vote. |
| 06B-C — provenance repair | PASS | `f1221564c0c83cc67df9c8487c735bce3c42fc85`; `f88efd1e71a66c39ff4f702baf4231e01e75aa46` | Derived raw adds only `attempt_id` ([diagnostic](../phases/PHASE_06B_C_PROVENANCE_REPAIR_AND_DIAGNOSIS.md)) | Crash cause remains unknown. |
| Phase 06B-S0 — supplement design | PASS, LOCAL ONLY | `0f75d2b`; `478d226` tests | Ten-run plan, validation, handoff system | No live supplement or RQ3 authorization. |
| Phase 06B-S1 — supplement implementation | PASS, LOCAL ONLY | current local phase | Dedicated plan-derived runner, attempt isolation, provenance, bounded diagnostics, stop policy, combined-view derivation, pre-live gate | Zero supplement runs executed; explicit future live authorization still required. |
| Phase 06B-S2 — supplement execution | BLOCKED | `2224704e9bc8223a686a18c91e0eb879cb0a54d7` tested | Attempt `20261001T205742Z-67a4ab301c67`; 0/10 runs; [manifest](../../manifests/phase-06b-s2-openviking-supplement.json) | Remote preflight hashed LF checkout bytes against a CRLF-derived expected SHA; provider service never started. One lifecycle used and cleaned up; no retry authorized. |

Current branch: `phase-06b-storage-batch`. Jetstream default/end state:
`SHELVED`.
