# Phase 06A — Mem0 Calibration and Experiment Freeze

## Status

Phase 06A is complete locally. Jetstream remained shelved; Hindsight and OpenViking were not started; hosted and RQ3 decision calls were zero. The tested scientific implementation commit is `ca2fd9fd7ea91623888722a7afa656ec3dc37797`.

## Measurement Changes

`memlife.models.authority` adds a deterministic, serializable authority ledger and `AuthorityExposureOutcome`. The existing Phase 03 `NormalizedOutcome` and serialized results are unchanged. Direct identity/correlation evidence drives authority exposure; candidate text, score, retrieval rank, and semantic similarity do not.

`memlife.runner.experiment` fixes deterministic identities, three-repetition aggregation, inconsistency preservation, residual advancement, and RQ3 gates. It is deliberately small and is not a Phase 06B batch orchestrator.

## Calibration Execution

`scripts/run_phase06a_calibration.py` executed three reference and three local Mem0 repetitions with isolated run IDs and namespaces. It forced Hugging Face/Transformers offline mode and replaced Mem0's LLM response hook with a hard failure. The local provider used Mem0 2.2.1, `infer=False`, sentence-transformers 6.1.0, the cached MiniLM-L3-v2 embedder, CPU, telemetry disabled, and a local on-disk Qdrant instance under excluded `runtime/`.

The reference oracle was checked before Mem0. All reference runs returned exact `CURRENT_ONLY` and authority `AUTHORITATIVE_ONLY`. All Mem0 runs happened to return the same outcomes. The latter is an observation, not a calibration assertion. The authority ledger records Alder v1 as superseded/non-authoritative and v2 as active/authoritative. Mem0 records native same-UUID update; no native revoke is claimed.

Raw, canonical results are in `artifacts/calibration/mem0-calibration-v1.json`. No model cache, runtime database, absolute machine path, or credential is tracked.

## Freeze Result

The canonical protocol is `experiments/freeze/experiment-freeze-v1.json`, with SHA-256 `0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b`. It freezes exactly three provider versions, six scenarios, every capability cell, three repetitions, deterministic order/identity, restart and re-derivation semantics, quiescence and timeouts, F1–F6, residual/root-cause/RQ3 gates, the future 54-call RQ3 cap, D0/D1/D2, trace fields, and aggregation.

The validator rejects a fourth provider, version drift, incomplete or unresolved matrix cells, repetition drift, non-positive timeouts, missing normalization/advancement/defense definitions, suspicious credential fields, non-canonical JSON, and manifest hash mismatch. Its future preflight mode also checks runtime evidence and an explicitly supplied Git commit before Phase 06B.

## Capability Evidence

Mem0 mappings follow the Phase 02/03 adapter and Phase 02B remote validation. Hindsight mappings follow the Phase 04 adapter, manifest, and completed live evidence. OpenViking mappings follow the Phase 05 adapter, preparation manifest, live retry, and closure evidence. No live provider was contacted in Phase 06A and no missing primitive was inferred from desired symmetry.

## Tests

- Phase 06 focused: 13 passed.
- Calibration: 2 passed.
- Unit: 142 passed.
- Contract: 6 passed.
- Integration: 6 passed, 1 skipped because no local live Hindsight service was configured.
- Mem0 regression: 5 passed.
- Hindsight regression: 22 passed, 1 expected live-service skip.
- OpenViking regression: 52 passed.
- Phase 03 regression: 20 passed.
- Phase 03B regression: 14 passed.
- Full suite: 154 passed, 1 expected skip.

All commands used `.venv\Scripts\python.exe` and disabled only pytest's cache provider because the pre-existing `.pytest_cache` ACL is not part of the experiment.

## Phase 06B Contract

Phase 06B must use the exact pushed Phase 06 commit and freeze hash; exact provider versions and compatible recorded runtime configuration hashes; the intended VM and `/dev/sdb`; persistent provider environments; successful provider health gates; three repetitions; and zero storage-batch downstream decision calls. Any mismatch stops before experiment execution. Provider-internal extraction calls remain distinct from downstream RQ3 calls.

## Non-Claims

This phase establishes calibrated measurement and a frozen protocol. It does not establish provider failure rates, comparative superiority, vulnerabilities, model susceptibility, defense effectiveness, or tool consequences.

