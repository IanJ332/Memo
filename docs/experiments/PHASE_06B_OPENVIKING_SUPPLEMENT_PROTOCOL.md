# Phase 06B-S — OpenViking Missing-Run Supplement Protocol

## Status and boundary

**Design status:** validated. **Implementation status:** Phase 06B-S1 local
implementation complete. **Execution status:** not authorized. Jetstream must
remain `SHELVED`.

This protocol preserves the original experiment. It does not create Freeze v2
because no scientific definition changes: it schedules only frozen run IDs that
were never executed. Experiment Freeze v1 remains the definition; a supplement
is a later, independently attributable attempt.

| Role | Identity |
| --- | --- |
| Original freeze | `experiment-freeze-v1`, SHA-256 `0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b` |
| Original attempt | `20261001T183940Z-1fc4c4929532`, tested commit `a569a166093c626c5a99a7a33042e0aa7ddb7e74` |
| Supplement execution plan | [`phase06b-openviking-missing-runs-v1.json`](../../experiments/supplements/phase06b-openviking-missing-runs-v1.json), SHA-256 `2db182047dd2b1bfddcaddaad40ace58385f8bdcf0bb114354d9724ee5d6626a`; future new attempt ID required |

The dedicated implementation is
`scripts/jetstream/phase06b_supplement.py` →
`phase06b_supplement_remote.sh` → `phase06b_supplement_remote.py`. It has no
run-ID injection option. The local pre-live gate is
`scripts/validate_phase06b_supplement.py`; it performs no cloud or provider
operation.

## Scientific rules

1. The 32 original observations remain immutable.
2. `freeze-v1__openviking__S0__r2` remains an `ERROR` observation.
3. Only the ten never-executed IDs below are eligible.
4. There are no extra repetitions, r4 runs, majority votes, retries, or
   replacement observations.
5. The supplement uses a new controller-generated attempt ID and immutable,
   attempt-scoped paths created exclusively.
6. Every new raw row contains its supplement `attempt_id` at creation.
7. Every code/runtime difference from the original tested commit and runtime is
   recorded before execution.
8. Combined analysis is derived and retains the source `attempt_id` and
   `execution_origin` for every row.

Eligible IDs, in frozen order:

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

Every Mem0 run, every Hindsight run, OpenViking S0 r1/r2, any r4, and any
replacement for an existing success/error are forbidden.

## Local OpenViking crash diagnosis

The supported classification is **provider process crash**. The underlying
cause is **UNKNOWN**. Preserved evidence includes the original raw/ledger,
remote result, lifecycle session, Phase 06B-C diagnostic, Git history, and
Phase 05 operational instrumentation. The Phase 06B attempt did not download
the OpenViking service log and did not serialize its exit code.

| Hypothesis | Supporting evidence | Contradicting evidence | Status |
| --- | --- | --- | --- |
| OOM / memory pressure | VM had about 5.78 GiB RAM, no swap, and OpenViking used local CPU inference; a sudden process exit is compatible. | No memory samples, OOM markers, cgroup events, or kernel log were preserved. | POSSIBLE |
| Process-level crash | Query connection closed without a response; immediate owned-process health check raised `ServiceExitedBeforeReady`. | Exit code and process log are absent, so the mechanism is unknown. | SUPPORTED |
| Python exception | A provider-side unhandled exception could terminate the service. | No traceback or log was preserved. | POSSIBLE |
| llama-cpp failure | Frozen runtime used `llama-cpp-python==0.3.35`; local inference occurs in the provider process. | No llama-cpp error, signal, or native backtrace exists locally. | POSSIBLE |
| Provider-internal gpt-oss request failure | OpenViking uses provider-internal `gpt-oss-120b`; the failing query followed completed write/extraction work. | No provider request log or upstream error was preserved, and provider-internal calls are not RQ3 calls. | POSSIBLE |
| HTTP server failure | The HTTP connection closed and the service was no longer alive. | No server log distinguishes HTTP-layer failure from a lower process crash. | POSSIBLE |
| Malformed response | A client-side parse failure could appear during query handling. | `RemoteDisconnected` means no HTTP response arrived, followed by confirmed process loss; no malformed payload exists. | UNLIKELY |
| Connection reset / close | `RemoteDisconnected: Remote end closed connection without response` is direct evidence. | It describes the transport symptom, not why the process exited. | SUPPORTED |
| Persistent-state corruption | The failure occurred after a successful S0 r1 and S0 r2 write/task completion on retained state. | No corruption message, consistency check, or provider log was preserved. | UNKNOWN |
| Port conflict | Port failure can prevent service availability. | The same process became ready and completed S0 r1 and the S0 r2 reset/write before failing; no bind error exists. | UNLIKELY |
| Disk exhaustion | None. | Root still had 4,638,720,000 bytes free and the persistent volume 45,750,497,280 bytes free after the run. | UNLIKELY |
| Controller / harness error | The controller is involved in process ownership and health checking. | It preserved the error, detected the dead child, stopped remaining runs, cleaned up, and isolated attempt artifacts as designed; no defect is demonstrated. | UNLIKELY |

S0 r2's provider task `20f131b9-65b1-458e-a09f-d917749bbf99`
completed and its row recorded a memory-diff update/provider URI before the
query failed. This narrows the timing but does not diagnose the crash.

## Required future observability

Before an authorized supplement, add an **observability-only** capture around
the existing owned OpenViking process. It must record, in the supplement
attempt directory:

- process PID, exit code, start timestamp, stop timestamp, and alive status;
- bounded sanitized stdout/stderr (currently merged) tail, full service-log
  SHA-256, and log path class without credentials;
- total/system and provider-process memory before launch, before each run, and
  after each run; use read-only `/proc` data where available;
- kernel/cgroup OOM evidence after abnormal exit when safely readable, with
  access failure recorded as unavailable rather than fatal;
- root and resolved persistent-volume free bytes at launch and per run;
- port 1933 listen/connection status, readiness probe result, HTTP exception
  class/detail, and owned-process liveness at each gate;
- task/extraction ID, terminal status, submitted/completed timestamps, and the
  last provider operation completed before failure.

Diagnostics must be timestamped and sanitized. Collection failure must not
silently change run semantics. No diagnostic may modify the provider config,
payload, scenario, namespace, lifecycle operation, quiescence rule, order, or
repetition count. Instrumentation is not permission to restart, tune memory,
change models, clear state, or repair the provider.

## Code-change classification

Existing evidence proves no harness/controller bug. The executable supplement
now has:

- selection code that consumes the validated ten-ID plan rather than the full
  42-run plan; and
- the observability-only capture above.

These are **OBSERVABILITY_ONLY** changes, including execution scoping. No provider or
experimental-behavior fix is justified. Any change to provider configuration,
scenario semantics, payload, lifecycle behavior, timeouts, quiescence, model,
or frozen outcome rules is an **EXPERIMENTAL-BEHAVIOR CHANGE**, requires new
scientific review, and is not authorized by this protocol.

## Attempt and aggregation semantics

The supplement writes only to new exclusive paths:

```text
remote: <live-mount>/memlife/runs/phase06b/supplements/attempts/{attempt_id}/
local:  artifacts/phase06b/supplements/attempts/{attempt_id}/
```

Canonical original and supplement raw artifacts remain separate. A derived
combined view may add:

```json
{"attempt_id": "...", "execution_origin": "ORIGINAL|SUPPLEMENT"}
```

It must verify 42 frozen run identities at most, preserve the original S0 r2
error, reject duplicates, preserve both attempts' tested commits/configuration
evidence, and aggregate without majority voting. `execution_origin` is a view
field; do not rewrite canonical rows merely to add it.

## Stop rule

If any supplement run errors, immediately evaluate provider integrity. If the
owned process exited, readiness fails, or service integrity is otherwise lost:

1. preserve the current run result as observed;
2. capture and hash diagnostics;
3. mark every remaining eligible ID `BLOCKED_NOT_EXECUTED` without invoking it;
4. stop only the run-owned service, perform owned cleanup, and shelve if this
   lifecycle opened the VM;
5. do not restart or retry within the lifecycle.

Even when service integrity remains healthy, an invoked run is never retried;
its observed success/error is final for that frozen run ID.

## Pre-authorization gates

An execution prompt must explicitly authorize exactly this supplement and
declare conversation, model, execution target, and Jetstream action. Before
unshelving, the local validator must pass, the branch/commit and all intervening
changes must be recorded, Freeze v1 must validate from Git, secrets checks must
pass, and the attempt ID/paths must not exist. RQ3 remains unauthorized.
