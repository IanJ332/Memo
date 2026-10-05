# Model Handoff — Start Here

## Project and research frame

**Project:** MemLife-NLIP

MemLife-NLIP studies cross-provider lifecycle security and authority
enforcement for agent memory systems. The core principle is:

> Retrieved != Authoritative

```text
source event
  -> memory write / derivation
  -> storage / cache / graph / profile
  -> retrieval
  -> authority enforcement
  -> delivered context
  -> LLM
  -> tool / action
```

The contribution is not merely that stale memory can affect an agent. It is
cross-provider authoritative lifecycle semantics, localization of
source/derived-state propagation, and provider-independent lineage-aware
enforcement before LLM reasoning. Model choice is a downstream moderator, not
the main storage-lifecycle experiment.

## Current authoritative state

| Item | State |
| --- | --- |
| Branch | `phase-08-expansion-freeze-v2` |
| Historical Phase 06B baseline | `f88efd1e71a66c39ff4f702baf4231e01e75aa46` |
| Published Phase 07 base | `481f9d698e7e48fe9d3d84868a303ec10aa676ea` |
| Current phase | Phase 08A expansion/Freeze-v2 draft foundation: LOCAL COMPLETE |
| Freeze | `experiment-freeze-v1` |
| Freeze SHA-256 | `0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b` |
| Original attempt | `20261001T183940Z-1fc4c4929532` (42 planned; 32 executed; 31 success; 1 error; 10 never executed) |
| Tested experiment commit | `58e154a62e1c52e6a478e8f0e2041b437023582a` |
| Successful supplement attempt | `20261002T000350Z-c272b34d2cc3`, tested commit `58e154a62e1c52e6a478e8f0e2041b437023582a` |
| Phase 06B coverage | 42 / 42 (42 planned; 42 executed; 41 success; 1 error; 0 never executed combined) |
| Provider coverage | Mem0 12/12; Hindsight 18/18; OpenViking 12/12 |
| Frozen error | OpenViking S0 r2: historical ERROR (`RemoteDisconnected`, then `ServiceExitedBeforeReady`) |
| Error root cause | `UNKNOWN`; classified only as provider process crash |
| Residual cells | Mem0 S1; Hindsight S1; Hindsight S4; OpenViking S4 (OpenViking S0 indexed by repetition disagreement) |
| Phase 07 RQ3 result | NOT ACTIVATED; 0 eligible empirical contexts; 0 calls |
| Freeze v2 | Non-final design draft only; no live provider accepted |
| Jetstream | Independently verified `SHELVED`, no external address; live execution is not authorized |

The baseline HEAD above is the scientific handoff point. Local documentation
commits may make `git rev-parse HEAD` newer without changing the original
experiment or origin state.

## What is complete

- Phases 01–05: provider-independent foundation and three provider bring-ups.
- Phase 06A: calibration and Experiment Freeze v1.
- Phase 06B: partial storage/lifecycle data, preserved without replacement.
- Phase 06B-C: provenance repair passed. The original raw artifact remains
  immutable; the derived artifact adds only the original attempt ID.
- Phase 06B-S2: one authorized managed lifecycle was used. Remote preflight
  blocked before provider startup because the tracked provenance-repaired
  artifact has LF bytes on Linux but its expected SHA-256 is over CRLF bytes.
  Zero supplement runs executed, no service started, RQ3 remained zero, the
  owned floating IP was deleted, and Jetstream returned to `SHELVED`.
- Phase 06B-S2R: local-only canonical Git-source validation now reproduces the
  historical CRLF artifact identity from LF or CRLF checkouts. Derived closure
  records the ten blocked IDs without modifying the attempt, future preflight
  evidence serialization is complete, and lifecycle vocabulary is normalized.
  No scientific row or canonical source artifact changed.
- Phase 06B-S2R2: local repair/validation passed; path-resolution bug (original raw artifact was bound to repo instead of MEMLIFE_DATA_ROOT) and SSH artifact-transfer timeout fragility identified. Published code at 88364966 was live-tested; Jetstream is shelved and provider never started. 10 frozen runs remain never executed. Local repair and validation of the path fix and bounded transfer retries passed; publication pending. No new live retry is authorized.
- Phase 06B-S: 10 runs of OpenViking successfully executed under attempt `20261002T000350Z-c272b34d2cc3`. Combined view derived with 42/42 runs. Jetstream shelved.
- Phase 07: exact Hindsight S1 recovery proved current-v2 proposition content
  with superseded lineage. RQ3 has zero eligible empirical contexts and remains
  unexecuted. The published closure commit is `481f9d698e7e48fe9d3d84868a303ec10aa676ea`.
- Phase 08A: local-only contract work defines a non-final Freeze-v2 draft,
  future Honcho and RetainDB/Graphiti acceptance gates, strict normalized RQ4
  evidence models, deterministic validation, and regression coverage. No
  provider, Jetstream, or model execution occurred.

See [`PROJECT_STATE.md`](PROJECT_STATE.md) for the phase map and
[`EXPERIMENT_LEDGER.md`](EXPERIMENT_LEDGER.md) for canonical provenance.

## Next authorized action

No live action is currently authorized. The next step is scientific review of
the Phase 08A draft and acceptance contract. Honcho is proposed but not
live-calibrated. RetainDB Server remains `PENDING_LIVE_ACCEPTANCE`; Graphiti is
fallback only. Do not start Jetstream, install or contact any proposed provider,
execute RQ3, call a hosted model, finalize Freeze v2, change Freeze v1, or rerun
any of the 42 historical repetitions without separate authorization.

## Safe continuation checklist

1. Run `git status` and preserve unrelated/untracked evidence.
2. Read [`DEBUGGING_LEDGER.md`](DEBUGGING_LEDGER.md) before changing runners.
3. Validate Freeze v1 from the Git blob, never checkout-dependent bytes.
4. Use the exact frozen provider versions and configuration hashes.
5. Treat attempt artifacts as immutable and use exclusive creation.
6. Keep Jetstream shelved unless a new prompt explicitly authorizes a live
   lifecycle.

When a future phase closes, update only the handoff files whose state changed.
At minimum inspect `PROJECT_STATE.md`, `EXPERIMENT_LEDGER.md`, and
`DEBUGGING_LEDGER.md`; do not rewrite the corpus wholesale.
