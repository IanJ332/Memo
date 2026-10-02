# Experiment Ledger

This is the canonical compact provenance ledger. It links to evidence rather
than copying raw logs.

## Experiment Freeze v1

- ID: `experiment-freeze-v1`
- SHA-256: `0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b`
- Definition: [`experiment-freeze-v1.json`](../../experiments/freeze/experiment-freeze-v1.json)
- Protocol: [`EXPERIMENT_FREEZE_V1.md`](../experiments/EXPERIMENT_FREEZE_V1.md)
- Matrix: S0–S5, 14 supported and 4 unsupported cells.
- Repetitions: exactly 3 per supported provider/scenario cell; 42 planned.

| Provider | Version | Configuration SHA-256 |
| --- | --- | --- |
| Mem0 | 2.2.1 | `23c068e16db7d4bb90aad7755b997d5a4104c433a4a0083ef43b3506680ff2e8` |
| Hindsight | 0.10.1 | `baca300bdce174d8cb2d00fa576df73d0cf5c4f9230aed370d2767bd35f4d73d` |
| OpenViking | 0.4.22 | `ad1216520de78aa6dd6fe0c34393e3830b05b035aa7dda367d92725dafe53258` |

Do not upgrade these during frozen execution.

## Phase 06B original attempt

- Attempt ID: `20261001T183940Z-1fc4c4929532`
- Tested commit: `a569a166093c626c5a99a7a33042e0aa7ddb7e74`
- Planned/executed/success/error/never executed: **42 / 32 / 31 / 1 / 10**.
- Provider coverage: Mem0 12/12; Hindsight 18/18; OpenViking 2/12.
- Original raw SHA-256: `fe6f8cca390fa30b714e7635b9e7e56b987bd8303611f625c3258e90eaea2ef4`.
- Derived provenance-repaired raw SHA-256: `80b82f177adf4a15659bc583df61c78dafaa034ac931b5592e22a47d01f67a9f`.
- Repair: added only `attempt_id=20261001T183940Z-1fc4c4929532` to each
  of 32 rows.
- RQ3 calls: **0**.

The original attempt directory and raw bytes are immutable. The tracked derived
artifact is [`freeze-v1-raw-runs.provenance-repaired.jsonl`](../../artifacts/phase06b/derived/20261001T183940Z-1fc4c4929532/freeze-v1-raw-runs.provenance-repaired.jsonl).

### Frozen error and residuals

`freeze-v1__openviking__S0__r2` is an executed `ERROR`, not an unexecuted
slot. It recorded `RemoteDisconnected: Remote end closed connection without
response`; the following health check observed `ServiceExitedBeforeReady`.
Never rerun, replace, or relabel it.

Residual cells: Mem0 S1, Hindsight S1, and Hindsight S4.

## Exact never-executed set

Only these IDs may appear in a later supplement:

1. `freeze-v1__openviking__S0__r3`
2. `freeze-v1__openviking__S2__r1`
3. `freeze-v1__openviking__S2__r2`
4. `freeze-v1__openviking__S2__r3`
5. `freeze-v1__openviking__S3__r1`
6. `freeze-v1__openviking__S3__r2`
7. `freeze-v1__openviking__S3__r3`
8. `freeze-v1__openviking__S4__r1`
9. `freeze-v1__openviking__S4__r2`
10. `freeze-v1__openviking__S4__r3`

Forbidden: every Mem0 and Hindsight run, OpenViking S0 r1/r2, any r4, and any
replacement. See the [supplement protocol](../experiments/PHASE_06B_OPENVIKING_SUPPLEMENT_PROTOCOL.md).

## Phase 06B-S1 implementation (local only)

- Dedicated supplement selection/execution path: implemented and locally
  validated; it accepts no caller-supplied run IDs.
- Supplement plan SHA-256:
  `2db182047dd2b1bfddcaddaad40ace58385f8bdcf0bb114354d9724ee5d6626a`.
- Change classification: `OBSERVABILITY_ONLY`; frozen payloads, provider
  configuration, models, timeouts, lifecycle semantics, and repetitions are
  unchanged.
- Attempt isolation: future remote and local artifacts use
  `phase06b/supplements/attempts/{attempt_id}` with exclusive creation.
- Live supplement observations executed: **0**. RQ3 calls: **0**.
- Jetstream remained `SHELVED`; live execution remains unauthorized.

## Phase 06B-S2 blocked supplement attempt

- Attempt ID: `20261001T205742Z-67a4ab301c67`.
- Tested commit: `2224704e9bc8223a686a18c91e0eb879cb0a54d7`.
- Status: **SUPPLEMENT_BLOCKED**; planned/executed/success/error/not executed:
  **10 / 0 / 0 / 0 / 10**.
- Blocker: remote preflight read the provenance-repaired artifact from the
  Linux checkout as LF bytes (SHA-256
  `84f0ac4e0b96730a0b59999573fce2c3e00b5e568bc831b6171e29544fbe2b7c`),
  while the asserted SHA-256
  `80b82f177adf4a15659bc583df61c78dafaa034ac931b5592e22a47d01f67a9f`
  is the Windows CRLF working-tree form. CRLF materialization of the Git blob
  reproduces the asserted SHA exactly.
- Provider service: **not started**. Supplement raw rows: **0**. RQ3 calls and
  downstream decision calls: **0**.
- Lifecycle: exactly one; run-owned floating IP deleted; final VM independently
  verified `SHELVED` with no external address; no retry attempted.
- Original coverage remains **42 / 32 / 31 / 1 / 10** and OpenViking S0 r2
  remains the frozen `ERROR`.
- Evidence: [supplement result](../../artifacts/phase06b/supplements/attempts/20261001T205742Z-67a4ab301c67/supplement-result.json)
  and [manifest](../../manifests/phase-06b-s2-openviking-supplement.json).

## Combined analysis rule

Canonical source artifacts remain unchanged. Any combined view is derived and
must retain `attempt_id` plus `execution_origin` (`ORIGINAL` or `SUPPLEMENT`)
per row. Do not add `execution_origin` by rewriting canonical originals. There
is no majority voting and no replacement of errors.

## Phase 06B-S2R local repair and derived closure

- Status: **PASS locally; publication pending**. No Jetstream/provider/RQ3
  action occurred and no supplement observation was executed.
- The provenance-repaired tracked JSONL is now read from the Git object,
  JSONL-validated without reserialization, and materialized as canonical CRLF
  bytes in memory. Its sole identity remains
  `80b82f177adf4a15659bc583df61c78dafaa034ac931b5592e22a47d01f67a9f`;
  the LF blob SHA is diagnostic only, not an accepted alternative identity.
- The immutable S2 attempt directory was not changed. Derived operational
  closure under
  `artifacts/phase06b/supplements/derived/20261001T205742Z-67a4ab301c67/`
  records 0 executed, 10 `BLOCKED_NOT_EXECUTED`, and marks missing disk and
  harness-prefix samples `NOT_SERIALIZED` rather than reconstructing them.
- Future attempts snapshot the plan and serialize its SHA/authorized IDs,
  exact selected harness path and `sys.prefix`, root/volume free bytes,
  per-run or blocked statuses, and canonical lifecycle status before provider
  work can proceed.
- Lifecycle status is canonically `PASS|PARTIAL|BLOCKED`; historical
  `SUPPLEMENT_*` values remain backward-compatible aliases.

## Phase 06B-S OpenViking missing-run supplement attempt

- Attempt ID: `20261002T000350Z-c272b34d2cc3`.
- Tested commit: `58e154a62e1c52e6a478e8f0e2041b437023582a`.
- Status: **PASS**; planned/executed/success/error/not executed:
  **10 / 10 / 10 / 0 / 0**.
- Provider service: **started successfully**. Supplement raw rows: **10**. RQ3 calls and
  downstream decision calls: **0**.
- Lifecycle: exactly one; run-owned floating IP deleted; final VM independently
  verified `SHELVED` with no external address; no retry attempted.
- Original coverage plus supplement coverage combined is **42 / 42 / 41 / 1 / 0** and OpenViking S0 r2
  remains the frozen `ERROR`.
- Evidence: `artifacts/phase06b/supplements/attempts/20261002T000350Z-c272b34d2cc3/supplement-result.json`.

## Phase 06B Closeout — Final Storage-Batch Inventory

- Phase 06B frozen storage batch: **COMPLETE**.
- Coverage: **42 / 42** (planned 42, executed 42, success 41, error 1, never executed 0).
- Historical ERROR: **OpenViking S0 r2** (`RemoteDisconnected`, then `ServiceExitedBeforeReady`; preserved without rerun).
- Jetstream: **SHELVED** (no active VM or external address).
- RQ3: **not yet executed** (0 downstream decision model calls).
- Next scientific step: **residual-only root-cause analysis / RQ3 eligibility review**.


