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
| Historical Phase 06B baseline | `f88efd1e71a66c39ff4f702baf4231e01e75aa46` |
| Origin HEAD | `2224704e9bc8223a686a18c91e0eb879cb0a54d7` |
| Current phase | Phase 06B-S2R local repair/validation passed; publication pending; S2 remains blocked with 0/10 executed |
| Freeze | `experiment-freeze-v1` |
| Freeze SHA-256 | `0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b` |
| Original attempt | `20261001T183940Z-1fc4c4929532` |
| Tested experiment commit | `a569a166093c626c5a99a7a33042e0aa7ddb7e74` |
| Blocked supplement attempt | `20261001T205742Z-67a4ab301c67`, tested commit `2224704e9bc8223a686a18c91e0eb879cb0a54d7` |
| Phase 06B coverage | 42 planned; 32 executed; 31 success; 1 error; 10 never executed |
| Provider coverage | Mem0 12/12; Hindsight 18/18; OpenViking 2/12 |
| Frozen error | OpenViking S0 r2: `RemoteDisconnected`, then `ServiceExitedBeforeReady` |
| Error root cause | `UNKNOWN`; classified only as provider process crash |
| Residual cells | Mem0 S1; Hindsight S1; Hindsight S4 |
| RQ3 calls | 0 |
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

See [`PROJECT_STATE.md`](PROJECT_STATE.md) for the phase map and
[`EXPERIMENT_LEDGER.md`](EXPERIMENT_LEDGER.md) for canonical provenance.

## Next authorized action

No live action is currently authorized. The next safe work remains **LOCAL
REPAIR / VALIDATION**: review and publish/synchronize the S2R commits, then
repeat the local gates from the published checkout. Publication does not
authorize execution. Any later live attempt requires new explicit
authorization. Until then, do not start Jetstream, execute any supplement run,
execute RQ3, probe the remote provider-crash root cause, change Freeze v1, or
rerun any completed repetition.

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
