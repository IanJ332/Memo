# Phase 05A — OpenViking Integration Preparation

## Why OpenViking

OpenViking 0.4.22 provides session-first ingestion, asynchronous extraction,
filesystem content, a separate vector index, auditable memory diffs, and
persistent reconstruction. These boundaries provide new RQ1/RQ2 observability
without running the final experiment matrix.

## Verified Version

The current stable release was verified as `openviking==0.4.22`, released
2026-09-28, tag `v0.4.22`, commit
`e8716760934d95ef73414484a45bfe475b9296e2`, Python >=3.10. The current
standalone SDK is `openviking-sdk==0.1.12` (Python >=3.8). The full evidence and
source links are in [the provider freeze](../providers/OPENVIKING.md).

## Distribution / Deployment Model

The future design uses the full package only in
`<MEMLIFE_DATA_ROOT>/venvs/openviking-0.4.22`, launched with
`openviking-server` on `127.0.0.1:1933`. The MemLife harness uses a small direct
HTTP transport and does not co-install OpenViking, Mem0, or Hindsight provider
dependencies.

## Session Lifecycle

A normalized write creates an isolated adapter-owned session, adds one user
message, commits it, waits for the provider task to complete, then reads the
archive's `memory_diff.json`. The commit archive is the preserved source
surface; extracted files are derived provider memories.

## Async Processing

The adapter polls provider task status until `completed`, fails on
`failed`/`cancelled`/unknown status, and raises after a bounded timeout. It
records task ID, submitted/completed timestamps, status, and elapsed
quiescence time. No fixed delay establishes correctness.

## Memory Extraction Pipeline

Current extraction uses VLM candidate generation, vector pre-filtering, VLM
dedup/reconciliation, AGFS writes, and vectorization. Internal create,
merge, and delete decisions are not reclassified as external lifecycle APIs.

## Storage Architecture

AGFS holds authoritative L0/L1/L2 content and session archives; the local
vector backend stores indexes and references. Both live under one persistent
workspace in the prepared deployment. The model cache and run artifacts are
also on the persistent volume.

## Memory Surfaces

Committed messages map to `SOURCE`; archive abstracts/overviews to `SUMMARY`;
profile extraction to `PROFILE`; other extracted memory files to `DERIVED`;
vector records to `VECTOR_INDEX`; and `find` candidates to `RETRIEVAL`.
Unobserved structures remain `UNKNOWN`.

## Retrieval Surfaces

Direct `find` is selected over `search` or the deprecated `recall` preset. It
does not use query-planner intent analysis and returns identifiable URIs. The
adapter scopes results to correlated memory URIs for the current benchmark
namespace.

## Lifecycle Capability Mapping

| Scenario/capability | Preparation classification | Exact mapping |
| --- | --- | --- |
| baseline | needs mapping | session write is supported; exact extraction/content identity needs live qualification |
| correction/update | unsupported | no external canonical update mapping; internal diff update is not substituted |
| supersession | unsupported | no explicit replacement or `SUPERSEDES` relation |
| revocation | unsupported | no native revoke/invalidate/disable/tombstone |
| delete + restart | needs mapping | delete all diff-correlated memory URIs, restart service with the same workspace, then direct find |
| inspect/audit | supported | content reads plus commit memory diff |
| trigger derivation | supported provider helper | session extract endpoint, distinct from commit task |

`DELETE_OR_INVALIDATE` remains a combined generic capability in Phase 03. The
adapter declares it supported because delete is real, then rejects a requested
`REVOKED` disposition explicitly.

## Memory Diff / Audit Semantics

The parser validates adds, updates, deletes, skipped operations, archive URI,
and extraction timestamp. The adapter retains all provider memory URIs for one
source event. It never selects one result merely to satisfy a one-record
interface.

## Provenance Mapping

Directly observed edges and IDs are source event, session, archive, task,
completed status, diff operation, provider URI, and retrieval URI. A diff gives
known operation correlation at commit granularity. Fine-grained semantic
extraction lineage remains unknown. Trace metadata is credential-free and
passes the existing recursive sensitive-key validator.

## Restart vs Session Reset

Restart replaces the exact PID-owned server process and keeps workspace,
vector index, archive, tasks, venv, and cache. Reset deletes only
adapter-prefixed sessions. The two operations are never treated as synonyms.

## Model Dependencies

Summaries, extraction, and reconciliation require a compatible VLM. The
service supports documented OpenAI-compatible configuration, but no course
model was chosen or called in Phase 05A. Future execution requires explicit
provider/model/base URL values and must validate structured extraction first.

## Embedding Dependencies

Indexing and `find` require embeddings. The current server documents a built-in
local dense default, plus remote/local-compatible alternatives. Course chat
endpoints are not assumed to implement embeddings. The future tiny probe must
validate the built-in local path on CPU before the canonical run.

## Jetstream Feasibility

The target's Python 3.12 and Ubuntu x86-64 satisfy the release metadata and
prebuilt `manylinux_2_31` ABI3 wheel. The 28.8 MB main wheel avoids a Rust source
build. A small single-service run is plausible within about 5.78 GiB RAM, but
local embedding and VLM compatibility remain explicit live gates. Root disk is
protected; provider venv/state/cache/runs live beneath the dynamically resolved
volume mount. GPU/CUDA dependencies are rejected.

## Adapter Design

`src/memlife/adapters/openviking.py` contains the direct transport, task waiter,
memory-diff parser, lifecycle adapter, sanitized trace hooks, and configuration
freeze. `tests/fakes/openviking.py` models the documented REST shapes. The
normalized write ID is a MemLife source-event ID; provider memory URIs remain a
separate one-to-many correlation.

## Unsupported Semantics

Update, supersession, and revocation are explicit `UNSUPPORTED` results. No
text similarity creates lineage. Internal dedup deletes do not prove external
deletion or revocation semantics.

## Future Live Validation Plan

`scripts/jetstream/phase05_openviking.py` and
`phase05_openviking_remote.sh` are prepared but were not run. They are gated by
`MEMLIFE_AUTHORIZE_PHASE05_LIVE=YES`, exact Git synchronization, a mode-400 or
mode-600 Git-ignored `.local/phase05_openviking.env` containing future VLM
configuration, persistent-volume paths, disk checks, dependency checks,
loopback binding, run-owned PID control, provider-reported task completion,
persistence restart, a single canonical/provenance pass, and managed cleanup.
The controller reuses the existing rule: delete only an owned FIP and shelve
only a VM opened by the run.

## RQ1 / RQ2 Value

The trace can distinguish archive success, extraction-task failure, audit-diff
mutation, AGFS state, vector/retrieval visibility, and post-restart behavior.
This supports localization of residual or resurrected state rather than a
single opaque pass/fail result.

## Non-Claims

Jetstream remained shelved. OpenViking was not installed or started. Hosted
model calls, the canonical experiment matrix, RQ3, and final RQ4 evaluation
were not run. The live feasibility and provider semantics remain candidates
until one separately authorized controlled Phase 05 execution.

## Phase 05B Live Readiness

Phase 05B hardened the prepared live path without contacting Jetstream or any
hosted model. Exact tag `v0.4.22` / commit
`e8716760934d95ef73414484a45bfe475b9296e2` was inspected locally. Its
`pyproject.toml:188-190` maps the official `local-embed` extra to
`llama-cpp-python>=0.3.0`. Its local embedding implementation and schema are in
`openviking/models/embedder/local_embedders.py:19-112` and
`openviking_cli/utils/config/embedding_config.py:57-125, 675-685, 985-993`:
the supported field is `provider` (not deprecated `backend`), the supported
model/default is `bge-small-zh-v1.5-f16`, its fixed dimension is 512, and
`cache_dir` is supported.

The future runtime therefore installs
`requirements/providers/openviking.txt`, pinned to
`openviking[local-embed]==0.4.22`. Its clean pip proposal must include
`llama-cpp-python`; proposal and installed environment continue to reject
`nvidia-*` and `cuda-*`. A compatible `llama-cpp-python` wheel is not assumed:
native compilation on Ubuntu is a documented live resource/time risk.

Generated `ov.conf` explicitly contains the supported `server`, `storage`,
`embedding`, `vlm`, and `memory` sections. Dense embedding is local
`bge-small-zh-v1.5-f16`, dimension 512, input `text`, with cache at
`<MEMLIFE_DATA_ROOT>/model_cache/openviking/embedding`. The provider-internal
VLM is fixed to provider `openai`, model `gpt-oss-120b`, API base
`https://llm.jetstream-cloud.org/gpt-oss-120b/v1/`, and course placeholder
credential `empty`. It uses temperature 0, concurrency 1, one retry, no backup,
and no guessed output-token cap. No local VLM call was made.

The managed controller now provisions the Git-ignored live environment file
at `/home/exouser/Memo/.local/phase05_openviking.env` before execution. It
creates the directory, writes exactly four required values, enforces owner
`exouser` and mode 600, and requires no manual SSH action. Neither config values
nor the API-key field are serialized into manifests/results.

Provider/service experiment errors now become a serialized `BLOCKED` result
with blocker information and an optional bounded, sanitized service-log tail.
The validator does not re-raise after successful serialization. The shell
always base64-emits an existing result before checking an unexpected validator
exit, and the managed controller evaluates `payload.status`; therefore a
provider incompatibility remains visible as an experiment blocker while a
missing payload remains a transport failure.

Pinned retrieval source confirms that `/api/v1/search/find` calls
`SearchService.find` and then `VikingFS.find` directly
(`openviking/server/routers/search.py:347-380` and
`openviking/service/search_service.py:139-177`). It uses the embedding model
for vector retrieval but not query-planner/VLM intent analysis. The adapter and
canonical lifecycle capability mapping are unchanged.

## Phase 05C — Controlled Live Validation Result

Phase 05C used exactly one managed Jetstream2 lifecycle from initial
`SHELVED` state at live commit
`913391b46eadde62a0d8dc7cd426f5a993ec8555`. Target identity, SSH, the live
`/dev/sdb` mount (`/media/volume/jisheng3_volume`), persistent clean harness,
and protected mode-600 runtime configuration passed. The prepared dependency
dry-run then returned a proposal that failed the mandatory
`llama-cpp-python`-presence assertion:

```text
AssertionError: local-embed plan omitted llama-cpp-python
```

The result is **BLOCKED** and Phase 05 is not complete. In accordance with the
frozen failure policy, no live repair or second experiment was attempted.
OpenViking and `llama-cpp-python` were not installed; `pip check`, installed
CUDA/NVIDIA inspection, config generation, service startup/readiness, internal
VLM compatibility, the persistence canary, direct find retrieval, service
restart, canonical benchmark, delete/restart check, memory-diff audit, and
provenance trace were not run. RQ3 decision calls were zero. Because failure
preceded validator invocation, the shell emitted no `PHASE05_RESULT_B64` and
the authoritative remote result is `NOT_RETURNED`, while the managed session
record is `BLOCKED`.

Cleanup completed: the run-owned floating IP was disassociated and deleted,
and `jisheng3` was verified `SHELVED`. The provider venv/state/cache and dry-run
artifact were retained on the persistent volume. Exact structured evidence is
in `manifests/phase-05c-openviking-live-validation.json`; Phase 05A and 05B
history above remains unchanged.

## Phase 05D — Local Preflight Repair

Phase 05D is local-only and does not reinterpret Phase 05C as an OpenViking
runtime failure. The Phase 05C pip report used distribution metadata name
`llama_cpp_python`, while the shell compared the raw lowercased value with
`llama-cpp-python`. Python distribution names are equivalent after PEP
503-style canonicalization: lowercase and replace each run of `-`, `_`, or `.`
with `-`. A deterministic fixture confirms the old comparison rejects the
reported spelling and the canonicalized comparison accepts it.

The pinned `v0.4.22` source at commit
`e8716760934d95ef73414484a45bfe475b9296e2` was rechecked: its `local-embed`
extra requires `llama-cpp-python>=0.3.0`. A local no-install pip report resolved
OpenViking 0.4.22 and `llama_cpp_python` 0.3.35. The official upstream CPU
wheel index contains a `0.3.35` `manylinux2014_x86_64` wheel, and a target
resolver check for CPython 3.12 selected it. The future remote dry-run and
installation therefore include the official CPU-only index; CUDA/NVIDIA
distributions remain forbidden. Source compilation is only a fallback; it
would require a C/C++ compiler and CMake and is undesirable on the 2-vCPU,
5.78-GiB target.

Local controller imports are now stdlib-only. MemLife adapter, command,
scenario, and provenance imports occur lazily inside `validate_remote`, under
the remote clean harness, so the OpenStack CLI interpreter does not own or
need Pydantic. `run_phase05` now uses `REPO_ROOT` for
`runtime_reports/phase-05-openviking-session.json`; callers no longer inject a
process-local `ROOT` binding.

Expected pre-validator failures now serialize sanitized `status: BLOCKED`
payloads for dependency dry-run, dependency-plan validation, provider install,
pip check, executable validation, and config generation. Dependency-plan
results retain normalized observed names, required names, version candidates,
and forbidden distributions. Install diagnostics are bounded to their final
8,000 sanitized characters. The shell emits `PHASE05_RESULT_B64` and exits
successfully after delivery; the managed controller continues to treat
`payload["status"]`, not SSH status, as authoritative. Phase 05B protected
configuration and all provider, embedding, VLM, and lifecycle semantics remain
unchanged.

## Phase 05E — Controlled Live Retry Result

Phase 05E used exactly one managed Jetstream2 lifecycle from initial `SHELVED`
state. The required local preflight was clean on branch
`phase-05-openviking-bringup`; local and origin heads were both
`8104aa682650393a9d36c881c7224721ff7bc252`. The normal controller entrypoint
unshelved the exact target UUID, created and associated one owned temporary
floating IP, synchronized the remote repository to the tested commit,
provisioned the mode-600 runtime config, and resolved `/dev/sdb` to
`/media/volume/jisheng3_volume`.

The run advanced beyond every fail-closed pre-validator gate: normalized
dependency-plan validation, provider installation, `pip check`, OpenViking
0.4.22 and `llama-cpp-python` metadata checks, executable validation,
CUDA/NVIDIA rejection, and config generation. Accordingly those gates passed.
The structured terminal payload did not include the exact installed
`llama-cpp-python` version, pip version, free-space samples, or config hash;
the record marks those fields `NOT_RETURNED` instead of reconstructing them.

The validator started its run-owned OpenViking process. The bounded sanitized
service log says the HTTP server was running on `127.0.0.1:1933`, along with
non-fatal warnings that deprecated storage path fields were ignored in favor
of the same configured workspace. Nevertheless, adapter readiness timed out
after 180 seconds and the final request reported connection refused. The
authoritative `PHASE05_RESULT_B64` payload therefore returned `BLOCKED` with
`TimeoutError` at readiness.

The frozen failure policy was followed: no speculative live fix, configuration
change, provider/model substitution, manual SSH experiment, or second run was
performed. Readiness blocked all semantic work, so session creation, message
addition, commit/archive, async task completion, internal-VLM compatibility,
memory-diff correlation, retrieval, restart persistence, canonical scenarios,
delete/restart, and provenance are `NOT_RUN`. RQ3 decision-model calls are
zero, and Phase 05 is not complete.

Cleanup completed within the managed lifecycle. The run-owned OpenViking
process shut down, the owned floating IP was disassociated and deleted, and
the VM was automatically shelved. A separate read-only status check then
confirmed UUID `5baeeae7-4c29-4903-89fe-2e9df0a8eced` was `SHELVED` with no
address. The provider venv, state, caches, and run artifacts were retained on
the persistent volume. Phase 05C's original blocker and Phase 05D's repair
remain unchanged; the exact Phase 05E record is
`manifests/phase-05e-openviking-live-retry.json`.

## Phase 05F — Local Readiness-Contract and Startup-Diagnostic Repair

Phase history remains cumulative:

- 05A: **PASS** — architecture preparation;
- 05B: **PASS** — live-readiness hardening;
- 05C: **BLOCKED** — package-name checker false negative;
- 05D: **PASS** — dependency/controller repair;
- 05E: **BLOCKED** — installation and configuration passed; readiness and all
  provider semantics remained unestablished;
- 05F: local readiness-contract and startup diagnosis.

Phase 05F used base commit
`1271ed4ae6cb5aa5b123c23252f804357656cab1` and did not contact Jetstream. The
pinned OpenViking router at `v0.4.22` commit
`e8716760934d95ef73414484a45bfe475b9296e2` returns liveness from `/health` as
`{"status":"ok","healthy":true,...}` and successful readiness from `/ready`
as `{"status":"ready","checks":{...}}`. `/ready` returns HTTP 503 with
`status: not_ready` during initialization or when configured subsystems fail.

MemLife's former readiness predicate could not accept the pinned successful
shape. It accepted only literal `true`, `ready: true`, or `healthy: true`. The
new gate requires `status == "ready"` for the pinned contract, keeps 503 and
transport failure retryable until a bounded deadline, and records final health,
readiness, HTTP, elapsed-time, and exception-class diagnostics. A healthy
`/health` response cannot satisfy readiness.

The preserved local Phase 05E result and session report were inspected before
code changes. They show the pre-uvicorn startup banner, repeated benign
workspace-path deprecation warnings, session-manager shutdown near the end of
the 180-second interval, and final connection refusal. Because the log tail was
collected after `finally` stopped the owned process, the shutdown line may be
normal cleanup and does not prove a pre-cleanup exit. The artifacts contain no
HTTP payload, traceback, or exit code. The retained-log classification and
secondary startup root cause are therefore **insufficient evidence**, not an
inferred embedding, vector DB, configuration, or VLM defect.

Pinned `openviking/server/bootstrap.py` prints the startup banner before
`uvicorn.run()`, and ASGI lifespan performs `service.initialize()` afterward.
The banner is no longer treated as readiness evidence. The controller now
checks only its owned `Popen` child, reports its exit code, preserves PID
ownership, and supplies a bounded sanitized tail. An exit during readiness
immediately yields `BLOCKED` at `service_startup` with
`ServiceExitedBeforeReady`; it does not consume the remaining 180 seconds.

The future result contract distinguishes `service_liveness` from
`service_readiness` and records `health_status`, `health_version`,
`readiness_status`, `readiness_checks`, `service_process_alive`, and
`service_exit_code` where observable. The future shell also reuses the retained
OpenViking venv fail-closed after exact metadata, executable, `pip check`, and
no-CUDA validation. It does not delete the venv or embedding cache.

No provider settings changed: embedding remains local
`bge-small-zh-v1.5-f16` dimension 512, and VLM remains OpenAI-compatible
`gpt-oss-120b` at the course endpoint with temperature 0, concurrency 1, and
one retry. Session/message/commit/task/memory-diff writes, direct-find queries,
unsupported update/supersession/revocation, correlated URI deletion, and
service restart semantics are unchanged.

## Phase 05G — OpenViking Readiness and Semantic Live Retry

Phase 05G used exactly one managed Jetstream2 lifecycle on 2026-09-29. Local,
origin, and the remote execution checkout all tested
`aa976a7d9b2ef37d8e8ba49b4c5091c1ec83e75e` on
`phase-05-openviking-bringup`. The VM began `SHELVED`; the normal controller
unshelved it, created and associated one owned temporary floating IP, used the
live `/dev/sdb` mount at `/media/volume/jisheng3_volume`, deleted the owned IP,
and automatically returned the VM to `SHELVED`. There was no live repair and
no second execution.

The remote validator emitted an authoritative `status: PASS`, `stage:
complete` payload. The fail-closed environment gates passed for OpenViking
0.4.22, `llama-cpp-python`, `pip check`, the executable, and absence of
CUDA/NVIDIA packages. `/ready` passed with `status: ready`; AGFS filesystem,
vector DB, and embedding reported `ok`. `/health` supplied `healthy: true` and
version `0.4.22` but a null status, leaving the strict `service_liveness` field
`NOT_ESTABLISHED`. This mismatch is retained as an incomplete Phase 05
criterion even though the remote validator status is PASS.

The single-message amber canary completed extraction and correlated source
event `4fe51613-4c42-4867-bb24-4f2de8bad4c6` to
`viking://user/default/memories/entities/system_component/phase_05_persistence_canary.md`.
Direct `/api/v1/search/find` retrieval returned one result before service
restart and one afterward. The run therefore exercised session/message/commit,
provider-reported async completion, memory-diff parsing, provider-internal
`gpt-oss-120b`, direct retrieval, owned-service restart, and persistence. RQ3
decision-model calls were zero.

The canonical benchmark emitted 24 results across baseline,
correction/update, revocation, delete/restart, and supersession, plus five
Phase 03B provenance traces. Update, supersession, and revocation remained
`UNSUPPORTED` as designed. Delete/restart completed. The baseline query's
provider records were semantically relevant but failed the benchmark's exact
string-currentness normalization, and the supersession scenario's final
inspect recorded `KeyError: 'v2'` after the expected unsupported operation.

Phase 05G itself is PASS, but Phase 05 is not marked fully complete. Besides
strict liveness, the serialized contract omitted the canary's session/archive/
task IDs, quiescence duration, per-operation memory-diff counts, the exact
`llama-cpp-python` version, the environment-reuse flag, service PID, and config
hash. The detailed chronological record is
`manifests/phase-05g-openviking-live-retry.json`; earlier 05C through 05F
diagnoses remain unchanged.
