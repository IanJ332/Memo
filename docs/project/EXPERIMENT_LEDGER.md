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

## Combined analysis rule

Canonical source artifacts remain unchanged. Any combined view is derived and
must retain `attempt_id` plus `execution_origin` (`ORIGINAL` or `SUPPLEMENT`)
per row. Do not add `execution_origin` by rewriting canonical originals. There
is no majority voting and no replacement of errors.
