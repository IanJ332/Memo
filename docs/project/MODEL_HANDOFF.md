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
| Branch | `phase-08c0-research-reconciliation`, based on authoritative `origin/main` `b1ff61b862a45df41405eb821d3a46318eb66c29` |
| Published Phase 08A branch | `phase-08-expansion-freeze-v2` at `a17bc7cb05558012992c19bb264fc7a6e18ac06b` |
| Historical Phase 06B baseline | `f88efd1e71a66c39ff4f702baf4231e01e75aa46` |
| Published Phase 07 base | `481f9d698e7e48fe9d3d84868a303ec10aa676ea` |
| Current phase | Phase 08C-0 research design reconciliation: DESIGN COMPLETE; original Freeze-v2 draft preserved; publication pending |
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
| Freeze v2 | Non-final Phase 08A draft preserved unchanged; its Honcho-plus-Provider-5 schedule is blocked by frozen Honcho `NO_GO`; no live provider accepted |
| Jetstream | `SHELVED`; Candidate10 used one separately authorized lifecycle, which is complete and cleaned up; no new live action is authorized |

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
- Phase 08A: published on `phase-08-expansion-freeze-v2` at
  `a17bc7cb05558012992c19bb264fc7a6e18ac06b`. It defines a non-final Freeze-v2
  draft, future Honcho and RetainDB/Graphiti acceptance gates, strict normalized
  RQ4 evidence models, deterministic validation, and regression coverage. No
  provider, Jetstream, or model execution occurred; Freeze v2 remains draft
  and is not finalized.
- Phase 08B-0: final review passed and the accepted preflight commit
  `7bf35a849987a255252954ac3ea907ee3cad7822` is published. The local-only
  Honcho preflight adds a fail-closed adapter skeleton,
  complete capability and S0-S5 probe plans, raw-evidence and quiescence
  contracts, a future non-executable Phase 08B-1 manifest, and deterministic
  validation. Honcho was not installed or contacted; all capability and
  scenario outcomes remain `UNKNOWN`; model calls of every kind were zero.
  Any future Honcho provider-internal model inference is provider behavior,
  remains separately unauthorized, must be configuration-pinned and counted,
  and cannot act as an authority/security judge or activate RQ3.
- Phase 08B-1 Candidate10: scientific closeout is accepted for attempt
  `20261007T165110Z-19d0ccd6b106`, with the deterministic provider decision
  frozen at `NO_GO`. The 18 capability classifications are 10 `SUPPORTED`,
  4 `UNSUPPORTED`, and 4 `UNKNOWN`. S0 was directly executed; S1 is `UNKNOWN`;
  S2-S5 are capability-derived `UNSUPPORTED`, not direct scenario executions.
  Native Dream quiescence is `UNKNOWN`. The provider made 21 internal calls
  (12 hosted text-generation and 9 local embedding); downstream and RQ3 calls
  were both zero. All 23 completion artifacts and all 95 indexed primary
  evidence files were independently verified. The raw appendix remains local
  and unpublished. The controller's SSH transport failure is distinct from
  scientific completion, and its root cause remains `UNKNOWN`. No security
  exploit was demonstrated. Freeze v1 is unchanged and Freeze v2 remains a
  non-final draft.
- Phase 08B-1 Git publication: the reviewed scientific closeout was originally
  published on `phase-08b1-candidate10-publication` at
  `54c1f7847af582cffc078fbc99aecfaab6b12dc2`. The latest published commit,
  `3c126216f4f5b7ac4f842e344598324c8d6a4097`, completes offline portability
  closure without changing scientific evidence or implementation. The main
  handoff was synchronized at `b1ff61b862a45df41405eb821d3a46318eb66c29`;
  the raw evidence ZIP remains local and unpublished.
  The historical preflight rule, "Phase 08B-1 requires separate authorization,"
  was satisfied for Candidate10 once and does not authorize a rerun or another
  candidate.
- Phase 08C-0: design-only reconciliation preserves the original Freeze-v2
  draft and records that Honcho `NO_GO` blocks its two-provider schedule and
  finalization prerequisites. A static RetainDB Server preview found an exact
  upstream repository and feasible source-commit pinning, but all acceptance
  capabilities remain `UNKNOWN` and acceptance remains
  `PENDING_LIVE_ACCEPTANCE`. The recommended sequence is offline deterministic
  RQ4 mediator implementation first, a separate RetainDB preflight, and no
  separately versioned Freeze-v2 revision until new evidence or an approved
  revised objective warrants one. See
  [`PHASE_08C0_RESEARCH_DESIGN_RECONCILIATION.md`](../experiments/PHASE_08C0_RESEARCH_DESIGN_RECONCILIATION.md).

See [`PROJECT_STATE.md`](PROJECT_STATE.md) for the phase map and
[`EXPERIMENT_LEDGER.md`](EXPERIMENT_LEDGER.md) for canonical provenance.

## Next authorized action

Phase 08C-0 design reconciliation is complete. The original Phase 08A draft
remains the historical design record and must not be edited to conceal the
Honcho gate result. Its future live schedule and finalization remain blocked.
The recommended next scientific and engineering phase is a separately
authorized Phase 08C-1 offline deterministic RQ4 mediator implementation and
evaluation. A RetainDB static/preflight phase may be prepared separately, but
live calibration requires its own explicit authorization. At present, no live
action is authorized, Candidate10 must not be rerun or replaced, and no revised
Freeze-v2 draft is approved.

The current execution rule is: no live action is authorized.

Jetstream remains `SHELVED`. Honcho is not accepted for Freeze-v2 entry because
the frozen gate returned `NO_GO`. Freeze v2 remains a draft and is not
finalized. RQ3 was not activated and downstream model calls remain zero. The
provider-internal calls are separately accounted provider behavior and cannot
act as an authority/security judge or activate RQ3. The raw evidence appendix
is preserved locally but is not published with the repository.

RetainDB Server remains `PENDING_LIVE_ACCEPTANCE`; all previewed capabilities
remain `UNKNOWN`. Graphiti is fallback only and does not become eligible from
Honcho `NO_GO`. Do not start Jetstream, install or contact any proposed
provider, change Freeze v1, finalize or silently revise Freeze v2, or rerun any
historical repetition without separate authorization.

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
