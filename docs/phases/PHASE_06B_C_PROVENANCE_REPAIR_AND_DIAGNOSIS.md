# Phase 06B-C Provenance Repair and OpenViking Diagnosis

## Status

Phase 06B-C local repair and reassessment: **PASS**.

The live attempt remains **PARTIAL**. It executed 32 of 42 frozen repetitions: 31
ended `SUCCESS`, OpenViking S0 r2 ended `ERROR`, and 10 OpenViking repetitions
were never executed. No experiment was run during this repair, and Jetstream
remained `SHELVED`.

## Immutable source evidence

Attempt: `20261001T183940Z-1fc4c4929532`

The original attempt directory was hashed before content inspection or local
repair. Its original artifacts were:

| Artifact | SHA-256 |
| --- | --- |
| `blocker-evidence.json` | `732238df0acd14c737fcc92d5e3b5088f09a28e4152d7b8dfac5c0229ea10621` |
| `execution-ledger.json` | `cca324bb1d667c53bd4728d1ddd69b6a6bd52d8010f8420d7884c12558823882` |
| `freeze-v1-aggregate.json` | `d7968d0fa96147f6b4d28a4b57704b56af5ff8b89cebc0ec5facb94985134bfe` |
| `freeze-v1-raw-runs.jsonl` | `fe6f8cca390fa30b714e7635b9e7e56b987bd8303611f625c3258e90eaea2ef4` |
| `freeze-v1-residual-index.json` | `bdd288706e6b5337672f4d575ab8972400361b4a8e24f713a76747ac9c28f6b5` |
| `lifecycle-session.json` | `da7b79b836196e393b324f9ba0ce3119de7d183f5b79d529a2de4eeea1e19891` |
| `planned-runs.json` | `30fd48df351723a0f4df8d022d0e17e26f8a67179ac484ea48868064ef5ea4c5` |
| `remote-result.json` | `0655eeed4cc91cd3892555b72680133cf5f9c4a8c24a975444ebc124a732e067` |

The original raw SHA-256 remained
`fe6f8cca390fa30b714e7635b9e7e56b987bd8303611f625c3258e90eaea2ef4`
after repair and validation.

## Attempt attribution proof

The missing per-row `attempt_id` is safely repairable as metadata:

1. The enclosing local directory is named
   `20261001T183940Z-1fc4c4929532`.
2. `remote-result.json` records that exact `attempt_id`.
3. `lifecycle-session.json` records that exact controller attempt ID and repeats
   it in its embedded `remote_work` result.
4. The execution ledger's 32 completed run IDs are exactly the 32 raw run IDs.
   The controller result locates that ledger inside the exact remote attempt
   directory.
5. Every recorded remote raw, aggregate, residual, and ledger path has parent
   directory
   `/media/volume/jisheng3_volume/memlife/runs/phase06b/attempts/20261001T183940Z-1fc4c4929532`.

There is no mixed-attempt indicator. All 32 rows have tested commit
`a569a166093c626c5a99a7a33042e0aa7ddb7e74`, freeze ID
`experiment-freeze-v1`, and freeze SHA-256
`0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b`.
All 32 run IDs and namespaces are unique, every run identity matches its frozen
plan entry, and the ledger/raw run sets are equal.

## Derived repair and validation

The derived artifact is stored outside the immutable attempt directory at
`artifacts/phase06b/derived/20261001T183940Z-1fc4c4929532/freeze-v1-raw-runs.provenance-repaired.jsonl`, SHA-256
`80b82f177adf4a15659bc583df61c78dafaa034ac931b5592e22a47d01f67a9f`.
For each of 32 source objects, the transformation added only:

```json
"attempt_id": "20261001T183940Z-1fc4c4929532"
```

No field was modified or removed. An object-by-object comparison after removing
the added key reproduced every source object exactly.

The complete post-run validator passed against the derived raw artifact and the
unchanged original aggregate and residual artifacts. It proved 32 objects, 32
unique run IDs, 32 unique namespaces, consistent attempt ID/freeze/tested
commit, zero downstream decision calls, raw-to-aggregate consistency,
aggregate-to-residual consistency, no fourth repetitions, and no duplicate
execution.

The deterministically validated residual cells remain:

- Mem0 S1
- Hindsight S1
- Hindsight S4

## OpenViking S0 r2 diagnosis

Classification: **provider process crash; underlying cause UNKNOWN**.

Confidence is high that the owned provider process exited, because the S0 r2
query first recorded `RemoteDisconnected: Remote end closed connection without
response`, and the immediate health gate then raised
`ServiceExitedBeforeReady`. Confidence is low about why it exited because the
preserved local attempt did not include the process exit code or service log.

| Question | Preserved local evidence | Finding |
| --- | --- | --- |
| Process exit code | The ledger preserves only the exception type; the handled partial result did not serialize the exception message or controller exit code. | Unknown |
| stdout/stderr tail | The service controller merged both streams into remote `openviking/openviking.log`, but that log was not downloaded into the preserved local attempt. | Unavailable |
| Memory/OOM | No memory metric, kernel log, cgroup event, or OOM marker is present. | Unknown; OOM cannot be confirmed or excluded |
| Disk space | Root free space changed from 4,685,545,472 to 4,638,720,000 bytes; volume free space changed from 46,250,000,384 to 45,750,497,280 bytes. | Disk exhaustion is not supported by the recorded capacity evidence |
| Port/bind conflict | The service had become ready and completed S0 r1 plus S0 r2 reset/write before the failing query. No bind error is preserved. | Initial port/bind conflict is not supported; a later conflict cannot be proven |
| Provider health logs | Only `ServiceExitedBeforeReady` is retained after the failed health check. | Detailed health evidence unavailable |
| Provider task/extraction | S0 r2 write task `20f131b9-65b1-458e-a09f-d917749bbf99` completed; the row records one memory-diff update and a provider URI before the query failed. | Write/extraction quiesced successfully before failure; provider task logs are unavailable |
| Malformed request | No server response or log identifies a request-validation error. The failure was a connection close followed by process exit. | Not supported, but not fully excludable |
| Persistent-state corruption | No local corruption diagnostic or provider log is preserved. | Unknown |
| Harness/controller bug | The controller detected the dead owned child and fail-closed the remaining provider runs. | No harness/controller failure is demonstrated |

No OpenViking code or runtime repair is justified from this evidence alone. A
future authorized lifecycle should first preserve the exact exit code, bounded
sanitized service log tail, and memory/OOM evidence. This phase does not make
that runtime change.

## Missing-run-only supplement assessment

A scientifically defensible supplement can be designed using only these 10
never-executed frozen IDs:

- `freeze-v1__openviking__S0__r3`
- `freeze-v1__openviking__S2__r1`
- `freeze-v1__openviking__S2__r2`
- `freeze-v1__openviking__S2__r3`
- `freeze-v1__openviking__S3__r1`
- `freeze-v1__openviking__S3__r2`
- `freeze-v1__openviking__S3__r3`
- `freeze-v1__openviking__S4__r1`
- `freeze-v1__openviking__S4__r2`
- `freeze-v1__openviking__S4__r3`

Such a supplement must use a new attempt ID, retain all 32 existing rows,
retain OpenViking S0 r2 as `ERROR`, never create r4, never replace any executed
repetition, and record every intervening code/runtime change. No supplement is
authorized yet, and no Jetstream action was taken.
