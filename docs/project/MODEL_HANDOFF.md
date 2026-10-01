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
| Branch | `phase-06b-storage-batch` |
| Phase baseline and origin HEAD | `f88efd1e71a66c39ff4f702baf4231e01e75aa46` |
| Current phase | Phase 06B-S1 local supplement implementation complete; live execution unauthorized |
| Freeze | `experiment-freeze-v1` |
| Freeze SHA-256 | `0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b` |
| Original attempt | `20261001T183940Z-1fc4c4929532` |
| Tested experiment commit | `a569a166093c626c5a99a7a33042e0aa7ddb7e74` |
| Phase 06B coverage | 42 planned; 32 executed; 31 success; 1 error; 10 never executed |
| Provider coverage | Mem0 12/12; Hindsight 18/18; OpenViking 2/12 |
| Frozen error | OpenViking S0 r2: `RemoteDisconnected`, then `ServiceExitedBeforeReady` |
| Error root cause | `UNKNOWN`; classified only as provider process crash |
| Residual cells | Mem0 S1; Hindsight S1; Hindsight S4 |
| RQ3 calls | 0 |
| Jetstream | `SHELVED`; live execution is not authorized |

The baseline HEAD above is the scientific handoff point. Local documentation
commits may make `git rev-parse HEAD` newer without changing the original
experiment or origin state.

## What is complete

- Phases 01–05: provider-independent foundation and three provider bring-ups.
- Phase 06A: calibration and Experiment Freeze v1.
- Phase 06B: partial storage/lifecycle data, preserved without replacement.
- Phase 06B-C: provenance repair passed. The original raw artifact remains
  immutable; the derived artifact adds only the original attempt ID.

See [`PROJECT_STATE.md`](PROJECT_STATE.md) for the phase map and
[`EXPERIMENT_LEDGER.md`](EXPERIMENT_LEDGER.md) for canonical provenance.

## Next authorized action

Phase 06B-S1 is implemented and locally validated. No live action is currently
authorized. A later prompt may explicitly authorize the exact ten-run
OpenViking supplement after the local pre-live gate passes. Until then, do not
start Jetstream, execute any supplement run, execute RQ3, probe the remote root
cause, change Freeze v1, or rerun any completed repetition.

The dedicated runner derives only OpenViking S0 r3 and S2/S3/S4 r1–r3 from the
validated plan. It uses a new attempt ID, emits
`execution_origin=SUPPLEMENT`, preserves the S0 r2 error, captures bounded
observability-only diagnostics, and stops without retry if provider integrity
is lost. Combined analysis is derived and retains both source attempts.

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
