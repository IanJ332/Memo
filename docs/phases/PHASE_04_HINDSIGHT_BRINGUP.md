# Phase 04 — Hindsight Bring-up

## Objective

Pin Hindsight, connect its native operations to the MemLife adapter and Phase
03B trace, then validate the self-hosted runtime in one controlled Jetstream2
session. Attempt 1 was **BLOCKED before service startup** by a shared-environment
dependency incompatibility. Phase 04A passed the isolated-runtime redesign.
The one authorized attempt 2 is also **BLOCKED**: its mandatory harness
preflight found that attempt 1's incompatible packages remained installed in
the remote harness `.venv`. Phase 04B then passed its local clean-harness
recovery and regression gates. Attempt 3 executed the prepared live flow at
commit `8187ccdd718a1b40be1079cfd1660e9f8ea5689d`. Both isolated environments,
the pre/post Hindsight harness checks, and the Mem0 semantic gate passed. The
run then stopped before service startup because the validator attempted to read
an unset result-metadata environment variable. Phase 04C fixed that local
shell-to-validator handoff and added full required-key contract coverage. Phase
04D executed commit `3851543d6d5ef013fbe635bfe495c443227c076c` and is
**PASS**: the retained environments, live service, structured-output probe,
persistence restart, canonical benchmark, provenance trace, derived-state
probe, post-provider Mem0 regression, and full suite all passed.

## Why Hindsight

Hindsight exposes primary facts, derived observations, and observation source
IDs. This makes it useful for later RQ1/RQ2 propagation measurement and, if its
lifecycle behavior converges correctly, as a negative control. Phase 04 did not
seek a vulnerability and made no RQ3 or final RQ4 claim.

## Version Freeze

- Release/package version: `0.10.1`
- Upstream tag: `v0.10.1`
- Upstream commit: `f8950b0c07d9e34c76493dba802bb309f0ce60fd`
- API package: `hindsight-api-slim[embedded-db,local-onnx]==0.10.1`
- Python client: not installed; the adapter uses `urllib.request` over REST
- Attempt 1: 2026-09-28, tested commit
  `59222a27fcd59dc474ec282141a8b33bbc376088`
- Attempt 2: 2026-09-29, tested commit
  `2f85ba07a3172103c6008f566c3c017fd5cce884`
- Phase 04B base: `b366e3cb3c0abda521955cf99410141117de32ef`
- Phase 04B locally validated implementation:
  `e28d47de8ec1c27530159347699f0a24cce71c6d`
- Attempt 3: 2026-09-29, tested commit
  `8187ccdd718a1b40be1079cfd1660e9f8ea5689d`
- Phase 04C handoff-fix commit / Phase 04D tested commit:
  `3851543d6d5ef013fbe635bfe495c443227c076c`
- Blocked live-attempt configuration SHA-256:
  `1174925b29fa288e88899f9d0fd906865d5117ecc671d16d4af93ec356436b00`
- Isolated-retry configuration SHA-256:
  `baca300bdce174d8cb2d00fa576df73d0cf5c4f9230aed370d2767bd35f4d73d`

Current first-party release source, package metadata, REST routes, and provider
configuration were inspected before installation. Hindsight API 0.10.1 requires
Python 3.11 or newer; the target reported Python 3.12.3.

## Deployment Architecture

The frozen design uses a loopback-only bare-metal `hindsight-api` service on the
Ubuntu 24.04 Jetstream VM. It avoids Docker so Exosphere-managed containers and
networks are untouched. The API, embedded worker, local ONNX embedding model,
embedded database, and fixed internal LLM endpoint form the provider runtime.

Attempt 1 stopped during dependency validation. Attempt 2 stopped during the
pre-provider harness gate. Attempt 3 live-qualified the isolated dependency
boundary but stopped in result assembly before the service process was started.
Phase 04D then reused both retained environments and live-qualified the
loopback service, embedded pg0 state, and native behavior without changing the
frozen architecture.

## Provider Runtime Isolation

The first attempt co-installed Hindsight and Mem0 in the project `.venv`.
Hindsight 0.10.1 requires `protobuf>=7.35.1`; Mem0 2.2.1 requires
`protobuf>=5.29.6,<7.0.0`. Pip resolved protobuf 7.36.2 and correctly reported
the single shared environment as inconsistent.

Phase 04B separates three environment identities:

- Legacy contaminated environment: `/home/exouser/Memo/.venv`, retained as
  forensic evidence and explicitly excluded from execution.
- Clean harness environment:
  `<live /dev/sdb mount>/memlife/venvs/memlife-harness-phase04`, containing
  MemLife, tests, Mem0, benchmark code, trace code, and result collection.
- Provider environment:
  `<live /dev/sdb mount>/memlife/venvs/hindsight-0.10.1`, containing only the
  self-hosted Hindsight service runtime.
- Communication boundary: loopback HTTP at `127.0.0.1:8888` through the
  existing `UrllibHindsightTransport`.

The live mount remains dynamically derived with `findmnt /dev/sdb`.
`HARNESS_PYTHON` is the interpreter below the persistent-volume clean harness,
never an activated or repository-local interpreter. Harness health (`mem0ai`,
protobuf, OpenAI, optional LiteLLM, sentence-transformers, Torch,
qdrant-client, and `pip check`) is captured before and after provider setup.
The provider environment has its own Hindsight/protobuf inspection and `pip
check`. Cross-environment protobuf versions need not match; a failed check
inside either environment is still fatal.

An absent provider venv may be created and populated from the service-only
requirements. A present venv is reused only after validation. Incomplete or
inconsistent state fails closed with bounded diagnostics and is never removed
automatically. The provider fingerprint records Python, pip, Hindsight, and
protobuf versions plus a SHA-256 of normalized `pip freeze` output.

The clean harness follows the same fail-closed rule. A new venv is resolved and
installed from `requirements/core.txt` plus
`requirements/providers/mem0.txt`. A combined `pip install --dry-run --report`
is inspected before installation. CPU Torch is selected through the official
CPU wheel index; CUDA/NVIDIA packages are rejected. An existing candidate must
match its recorded environment fingerprint exactly and pass `pip check` and
the pinned direct-version checks. It is never deleted or repaired in place.

Service start uses the executable inside `HINDSIGHT_VENV/bin`. The benchmark
and validation entry point use `HARNESS_PYTHON`. Restart replaces only the
run-owned API process and preserves the provider venv, pg0 state, and caches.
Exact PID ownership prevents broad Python cleanup; PID and service logs remain
under the persistent Phase 04 run directory.

This isolation is infrastructure architecture, not a defense. It cannot affect
lifecycle semantics, retrieval semantics, provenance results, or security
claims: the unchanged benchmark client still exercises Hindsight 0.10.1 through
the same public service API.

Attempt 2 did not contradict this design. Its pre-provider gate found that the
existing harness itself was unhealthy: `mem0ai==2.2.1` was paired with
`protobuf==7.36.2`, and `litellm==1.103.0` was paired with
`openai==3.13.0`. `pip check` failed exactly as required. Because the failure
preceded provider setup, the run neither installed nor validated the separate
Hindsight venv.

## Phase 04B Clean Harness Recovery

The repository-wide ownership audit found no OpenAI SDK import in production
MemLife modules or tests. The sole direct import is
`scripts/test_jetstream_llm.py`. Its `openai==3.13.0` pin moved from core to
`requirements/infra/jetstream-llm.txt`. Mem0 2.2.1 itself directly requires
`openai>=1.90.0` and `protobuf>=5.29.6,<7.0.0`; its optional `llms` extra is not
installed. Hindsight 0.10.1 directly requires LiteLLM on Linux, so the
LiteLLM/OpenAI conflict observed in attempt 2 belongs to the contaminated
shared history, not the new Mem0-only harness graph.

No protobuf or OpenAI override was added. In a disposable Windows Python 3.14.3
venv, the combined direct requirement set resolved to Mem0 2.2.1, protobuf
6.33.6, OpenAI 3.20.0, no LiteLLM, sentence-transformers 6.1.0, CPU-only Torch
2.14.0+cpu, and qdrant-client 1.19.1. `pip check` passed. These are local
validation facts, not fabricated future Jetstream versions; the live resolver
may select other compatible transitive versions.

Before Hindsight paths or service state are prepared, the remote flow now runs
unit/contract tests and `phase04_mem0_regression.py`. The latter constructs
Mem0 and requires write, query, same-ID update, native history, reconstruction,
delete, reconstructed history, and post-delete absence. Failure prevents all
Hindsight setup. The clean harness fingerprint records Python, pip, Mem0,
protobuf, OpenAI, optional LiteLLM, sentence-transformers, Torch,
qdrant-client, and normalized `pip freeze` SHA-256.

## Attempt 3 — Final Prepared Live Retry

The managed run began from a clean local branch whose local and fetched remote
heads both equaled `8187ccdd718a1b40be1079cfd1660e9f8ea5689d`. The focused
local isolation preflight passed 21 tests. Jetstream began `SHELVED`, the
controller created and owned a temporary floating IP, reached the exact VM by
SSH, resolved `/dev/sdb` to `/media/volume/jisheng3_volume`, and synchronized
the remote branch before executing the frozen script.

Execution advanced beyond every environment and predecessor gate that had
blocked the earlier attempts:

- the persistent-volume clean harness passed `pip check`, Mem0 2.2.1,
  sentence-transformers 6.1.0, CPU-only Torch, and no-CUDA/no-NVIDIA checks;
- remote unit/contract tests completed successfully;
- the Phase 02B Mem0 write/query/update/history/delete/reconstruction semantic
  regression completed successfully;
- the isolated Hindsight environment passed its version, executable,
  `pip check`, and no-Torch/no-CUDA/no-NVIDIA checks; and
- the clean harness passed its post-install health check, confirming that
  provider installation did not mutate it.

The next command invoked `phase04_hindsight_validate.py`. While constructing
the initial sanitized result object, line 141 read
`PHASE04_HARNESS_VENV_CREATED_BY_THIS_RUN` from `os.environ`. The shell script
had exported that name without assigning it from
`HARNESS_VENV_CREATED_BY_THIS_RUN`, so Bash did not place a value in the child
environment and Python raised `KeyError`. The analogous Hindsight-created flag
has the same wiring defect, although evaluation stopped at the first missing
name. The failure preceded the validator's `try` block and its
`start_hindsight_service` call. Therefore the API, health/version endpoints,
structured-output probe, persistence smoke, benchmark, and trace were all
**NOT RUN**.

No live repair or second attempt was made. The controller disassociated and
deleted only its owned floating IP, shelved the VM, and a separate read-only
status check confirmed `SHELVED` with no address. The valid persistent-volume
environments and provider state were retained.

## Phase 04C — Environment Handoff Repair

Phase 04C ran locally only from base
`8756bd3d4b420337c9f0a7f15cdaa8f8d0d865f8`. It assigned both
`PHASE04_HARNESS_VENV_CREATED_BY_THIS_RUN` and
`PHASE04_HINDSIGHT_VENV_CREATED_BY_THIS_RUN` from their lowercase-valued shell
source variables. A focused contract test derives all 21 strict
`os.environ[...]` keys from the validator and requires an explicit-value shell
export for each. No other missing required handoff was found.

The existing reuse paths remain unchanged. A retained clean harness records
`false`, skips installation, and must match its fingerprint and pass health,
version, CPU-only, and no-CUDA checks. A retained Hindsight venv likewise
records `false`, skips installation, and must pass its executable, version,
dependency, and no-CUDA checks. The next authorized live run can therefore
reuse both retained environments without recreating them.

## Internal LLM Configuration

The fixed provider-internal configuration is OpenAI-compatible provider
`openai`, model `gpt-oss-120b`, using only the course-authorized hosted endpoint
and its supported non-secret placeholder. Its intended purpose is Hindsight fact
extraction and consolidation.

This is distinct from a future downstream decision LLM. Phase 04 made zero RQ3
decision-model calls. Phase 04D's Alice compatibility retain/recall passed and
confirmed structured-output parsing. No alternate course model was tried.

## Storage Architecture

Live `findmnt` resolved `/dev/sdb` as ext4 mounted at
`/media/volume/jisheng3_volume`. The run created these path classes beneath its
`memlife` root:

- `providers/hindsight/`
- `model_cache/hindsight/`
- `runs/phase-04-hindsight/`
- `artifacts/`

The backend is embedded pg0/PostgreSQL with pgvector and the named URL
`pg0://memlife-phase04`. `/home/exouser/.pg0` was managed as a link to the
persistent provider root. Attempt 3 validated the isolated provider environment
and retained it on the volume. Phase 04D started the provider, preserved recalled
records across service restart, and live-verified derived and async state.

## Native Memory Model

The pinned source defines retain for fact extraction, recall for direct memory
retrieval, `world`/`experience` facts, derived `observation` rows, mental models,
knowledge structures, document deletion, reversible fact invalidation, and
asynchronous consolidation operations. Phase 04 uses recall, not reflect, for
lifecycle retrieval.

## Source vs Derived Surfaces

The adapter classifies listed `world` and `experience` memory units as the
provider's primary `SOURCE` surface and `observation` memory units as `DERIVED`.
The original retained document is tracked by its native document ID but is not
invented as an additional normalized memory record. Mental models and knowledge
structures remain unmapped in Phase 04 because the selected recall/list path
does not justify equating them with these records.

Phase 04D confirmed these classifications against the running service: two
`world` rows were SOURCE and one `observation` row was DERIVED. The observation
directly exposed both source record IDs.

## Lifecycle Capability Mapping

| Capability | Pinned native mapping | Live result |
| --- | --- | --- |
| Write | synchronous retain | PASS |
| Query | recall over world, experience, observation | PASS |
| Update | same-ID memory text curation | PASS — `CURRENT_ONLY` |
| Supersede | same-ID edit; no native supersession edge | PASS — `CURRENT_ONLY`; edge remains unsupported |
| Revoke/invalidate | state=`invalidated` curation | PASS — `ABSENT` |
| Delete | document-scoped native delete | PASS — `ABSENT` |
| History | observation history endpoint; source facts may be empty | PASS with native scope retained |
| Inspect | list valid and invalidated memory units | PASS |
| Restart | stop/start service against the same pg0 instance | PASS |
| Trigger derivation | submit consolidation and poll operation | PASS |

Unsupported or non-equivalent semantics are explicit. In particular, the
adapter does not fabricate a supersession relationship, source-fact history, or
per-fact hard delete when Hindsight exposes only a document-scoped primitive.

## Provenance Capability Mapping

Known when exposed: an observation's native `source_memory_ids` (or recall
`source_fact_ids`) can identify provider records from which it was derived;
retrieval itself is directly observed. Unknown: causal lineage for primary
facts, supersession caused by same-ID text editing, and any relationship whose
source ID cannot be resolved to an experiment lifecycle event. Text similarity
is never used to create provenance.

The provider-independent trace extension and PassThroughFilter behavior passed
local tests, including a fake observation with explicit source IDs. Phase 04D
also completed the real five-scenario trace and bounded derived-state probe.
Directly exposed observation source IDs are known; primary-fact causal lineage
and same-ID edit supersession remain unknown.

## Async / Quiescence Semantics

Retain is frozen as synchronous. Consolidation and maintenance are treated as
asynchronous provider operations. The adapter captures operation IDs that
pre-date a mutation and polls new operations until none is `pending` or
`processing`; a failed operation is an error. Explicit consolidation polls its
returned ID until `completed`. Benchmark metadata records submitted/completed
timestamps and the quiescence criterion.

This mechanism passed deterministic unit tests and the live service run.
Operation IDs, submitted/completed timestamps, and the no-pending-or-processing
quiescence condition were recorded in benchmark metadata.

## Canonical Benchmark Result

Phase 04D completed all 24 canonical benchmark steps with no operation errors:

- baseline: `CURRENT_ONLY`;
- correction/update: `CURRENT_ONLY`;
- supersession: `CURRENT_ONLY` using the frozen same-ID edit mapping;
- revocation: `ABSENT`; and
- delete + restart: `CURRENT_ONLY` before deletion, then `ABSENT` after delete
  and again after service restart.

No stale state was visible in a canonical query. Only `CURRENT_ONLY` and
`ABSENT` were observed; unsupported semantics remain explicit rather than
emulated.

## Restart Result

**PASS.** The smoke probe recalled two records before restart and two after the
run-owned service restarted against the same provider venv and pg0 state. The
delete scenario also remained `ABSENT` after restart.

## Negative-Control Interpretation

Hindsight propagated every measured lifecycle change without stale canonical
recall, making the provider a useful negative control for later RQ1/RQ2 work.
The benchmark was not changed to manufacture a failure.

## Limitations

- The first three authorized lifecycles ended before the compatibility probe;
  Phase 04D completed it and the remaining live flow.
- Attempt 1 exposed the shared-environment conflict; attempt 2 exposed its
  persisted contamination during harness preflight.
- Attempt 3 validated dependency isolation but exposed a benchmark-code result
  assembly defect before service startup.
- The earlier blockers remain environment/automation history, not Hindsight
  memory-semantics results.
- No alternate version, internal LLM, embedding backend, database backend, or
  scenario was attempted. Phase 04D reused the retained clean harness and
  Hindsight venv.
- Local Windows tests use a deterministic fake transport; they do not replace
  the real self-hosted evidence now recorded from Phase 04D.

## Reproduction

Local preparation at the tested commit:

```powershell
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.venv\Scripts\python.exe scripts\jetstream\jetstreamctl.py phase04
```

The attempt-2 local preparation results were `71 passed` (unit), `5 passed`
(contract), `5 passed, 1 skipped` (integration), and `81 passed, 1 skipped`
(full). The skip is the opt-in real Hindsight integration test; the Mem0
regression subset remained green with `5 passed`, and the focused Phase 03/03B
lifecycle/trace regression had `17 passed`. The second command is historical
reproduction provenance only. Attempt 3 consumed the one lifecycle authorized
for its conversation and must not be rerun without separate explicit approval.

Phase 04B validation used a newly created disposable environment rather than
the development `.venv`: `74 passed` (unit), `5 passed` (contract), `5 passed,
1 skipped` (integration), and `84 passed, 1 skipped` (full). The direct Phase
02B semantic gate passed every lifecycle check. Focused Phase 03 and Phase 03B
regressions passed `15` and `13` tests respectively. The skip remains the
opt-in real Hindsight service test. Jetstream was not contacted.

Phase 04C local validation passed the 11-test runtime-isolation suite, 75 unit
tests, 5 contract tests, 5 integration tests with the live Hindsight test
skipped, the 15-test Phase 03 regression, the 13-test Phase 03B regression, the
Phase 02B Mem0 semantic gate, and the full suite at 85 passed with 1 skipped.
Windows could not instantiate its optional WSL `bash.exe` (`E_ACCESSDENIED`),
so `bash -n` was unavailable; the all-required-key static contract test passed.
Jetstream was not contacted.

The controller recorded exact VM UUID
`5baeeae7-4c29-4903-89fe-2e9df0a8eced`, deleted the temporary floating IP it
created, and returned the initially shelved VM to `SHELVED`.

Attempt 2 synchronized commit
`2f85ba07a3172103c6008f566c3c017fd5cce884`, verified `/dev/sdb` mounted at
`/media/volume/jisheng3_volume`, reached SSH with public-key authentication,
then failed the harness `pip check`. It deleted and disassociated its owned
temporary floating IP and independently reverified `jisheng3` as `SHELVED`
with no address.

Attempt 3 synchronized and executed commit
`8187ccdd718a1b40be1079cfd1660e9f8ea5689d`. Its live clean-harness,
Mem0-regression, provider-environment, and post-provider harness gates passed.
The result validator then raised
`KeyError: PHASE04_HARNESS_VENV_CREATED_BY_THIS_RUN` before starting the
Hindsight service. The controller deleted and disassociated its owned temporary
floating IP and returned `jisheng3` to `SHELVED`; the final read-only status
check reported no address.

Phase 04D synchronized and executed commit
`3851543d6d5ef013fbe635bfe495c443227c076c`. The retained clean harness and
Hindsight environment matched their fingerprints and passed independent `pip
check` gates. Remote unit/contract tests passed `80` tests, the Phase 02B Mem0
semantic gate passed, the real Hindsight integration passed, the post-provider
Mem0 regression passed `5` tests, and the full remote suite passed `86` tests.
The authoritative `phase-04-result.json` reports `PASS`; the service log ends
with graceful Hindsight, worker, PostgreSQL-pool, and pg0 shutdown.

After the result and log were complete, the local controller remained blocked
waiting on the finished SSH command (`CONTROLLER_POST_RESULT_HANG`). Cleanup
recovery copied and validated the result before sending Ctrl+C to the original
controller. Because its cleanup did not execute, the recovery path
disassociated and deleted only the temporary floating IP created by this run,
shelved the already-active `jisheng3`, and verified `SHELVED` with no associated
floating IP. No second experiment run, Hindsight start, benchmark, or model call
occurred.

## Git Trace

- `4bc25488ba4579cf1d3dcea872aba1ccdb168841` — freeze Hindsight configuration
- `7508bd7d2244f98f842e657e45a0568485bd60ed` — add Hindsight adapter
- `59222a27fcd59dc474ec282141a8b33bbc376088` — add tests and managed validation; exact live tested commit
- `31e7cc6d975e2ae708b5736734c5c59961b63387` — record the sanitized blocked result
- `2f85ba07a3172103c6008f566c3c017fd5cce884` — complete Phase 04A isolated-runtime retry preparation; exact retry tested commit
- `7af3156` — record the sanitized attempt-2 harness-preflight blocker
- `31ea2a4172c8fb68ee04e8f81517fabd83ef8d6b` — separate harness dependency ownership
- `b87db40cb3c0efc30d3f295413fad23217e34673` — prepare the clean persistent-volume harness runtime
- `e28d47de8ec1c27530159347699f0a24cce71c6d` — validate clean-harness recovery and fail-closed behavior
- `8187ccdd718a1b40be1079cfd1660e9f8ea5689d` — prepare the final live retry; exact attempt-3 tested commit
- `3851543d6d5ef013fbe635bfe495c443227c076c` — fix the shell handoff and prepare Phase 04D; exact live tested commit

The Phase 04B documentation commit is the branch HEAD reported in the
completion response. The Phase 04B base is
`b366e3cb3c0abda521955cf99410141117de32ef`.

## Next Experiment Handoff

Phase 04 is complete with a structured remote `PASS`. Continue to the next
planned project phase without rerunning Phase 04D. Preserve the legacy `.venv`
as forensic evidence and retain the clean harness, isolated Hindsight venv,
provider database, and model cache on the persistent volume.
