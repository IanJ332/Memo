# OpenViking 0.4.22 Provider Notes

## Why OpenViking

OpenViking adds a session-driven, filesystem-backed memory architecture that is
materially different from Mem0 and Hindsight. A source conversation is archived
before asynchronous summary and memory extraction. Long-term memories are files
with Viking URIs, while a separate vector index stores retrieval metadata and
references. This gives MemLife observable propagation boundaries for RQ1/RQ2:
source message, session, archive, task, memory-diff operation, provider memory
URI, vector-backed retrieval, and restart.

## Verified Version

Phase 05A inspected current first-party sources on 2026-09-28 and freezes:

- main package: `openviking==0.4.22`;
- release date: 2026-09-28;
- Git tag: `v0.4.22`;
- tag/attested release commit:
  `e8716760934d95ef73414484a45bfe475b9296e2`;
- Python HTTP SDK: `openviking-sdk==0.1.12`, released 2026-09-18;
- main-package Python requirement: Python 3.10 or newer;
- SDK Python requirement: Python 3.8 or newer.

The task brief's tentative `v0.4.21` was superseded by `v0.4.22` on the day of
this review. Phase 05A therefore does not pin the stale candidate.

Primary evidence:

- <https://github.com/volcengine/OpenViking/releases/tag/v0.4.22>
- <https://github.com/volcengine/OpenViking/tree/v0.4.22>
- <https://pypi.org/project/openviking/0.4.22/>
- <https://pypi.org/project/openviking-sdk/0.1.12/>
- <https://docs.openviking.ai/en/>

## Distribution / Deployment Model

The release has separate distribution boundaries:

- `openviking`: full local runtime, HTTP server, Python compatibility client,
  and CLI entry points;
- `openviking-sdk`: small pure-Python HTTP client package;
- `openviking-server`: self-hosted server command;
- official Docker images and independent Rust/npm CLI artifacts.

The service defaults to `127.0.0.1:1933`; the official Docker image binds
inside the container and requires authentication when exposed. Phase 05 uses a
bare-metal provider-specific venv and direct HTTP from the clean MemLife
harness. It does not install either OpenViking package into the harness.

The selected boundary is direct HTTP, not the SDK. Every required preparation
operation is in the documented REST surface and `urllib.request` keeps the
provider's large dependency graph isolated.

## Session Lifecycle

The verified lifecycle is:

1. `POST /api/v1/sessions` creates a user-scoped session.
2. `POST /api/v1/sessions/{session_id}/messages` adds the synthetic source
   event.
3. `POST /api/v1/sessions/{session_id}/commit` synchronously archives eligible
   messages and clears them from the live session.
4. An archived commit returns `status=accepted`, `task_id`, `archive_uri`, and
   `archived=true`. A no-op returns `status=skipped` and no task.
5. The background `session_commit` task writes L0/L1 summaries, extracts and
   reconciles long-term memories, writes `memory_diff.json`, and finally writes
   `.done`. A failure can write `.failed.json`.

Commits for one session are serialized by archive number. A later archive waits
for the prior archive's `.done`; an unresolved earlier failure prevents later
commits.

## Async Processing

Task states are `pending`, `running`, `cancelling`, `completed`, `failed`, and
`cancelled`. Only `completed` is success. The adapter polls
`GET /api/v1/tasks/{task_id}` to a bounded deadline, records submission and
completion timestamps plus elapsed quiescence time, fails immediately on a
failed/cancelled/unknown terminal status, and raises on timeout. It never uses a
fixed sleep as correctness logic.

Task records are persisted in AGFS and can remain queryable after restart,
subject to provider retention. Receiving a task ID proves submission, not
completion.

## Memory Extraction Pipeline

The documented extraction pipeline is:

`messages -> LLM extraction -> candidate memories -> vector pre-filter -> LLM
dedup decision -> AGFS write -> vectorization`.

Candidate decisions include `skip`, `create`, and `none`; decisions against an
existing item include `merge` and `delete`. These are internal extraction and
dedup operations. They are not evidence that an external caller can request
canonical supersession or revocation.

Built-in memory types include `profile`, `preferences`, `entities`, `events`,
`identity`, `soul`, `cases`, `trajectories`, `experiences`, `tools`, and
`skills`. Active memory policy controls which types are extracted.

## Storage Architecture

VikingFS is the URI layer. AGFS is authoritative content storage for L0/L1/L2;
the vector index stores URIs, vectors, and metadata but not full file content.
The open-source standalone configuration can use local AGFS and local vector
storage under one persistent workspace. Removing a VikingFS URI synchronizes
vector deletion.

Session archive structure includes `messages.jsonl`, `.abstract.md`,
`.overview.md`, `.meta.json`, `memory_diff.json`, `.done`, and optionally
`.failed.json`. Long-term memories live below the authenticated user's
`memories` tree, separate from session archives.

## Memory Surfaces

Only directly observable structures are mapped:

| OpenViking structure | MemLife surface | Reason |
| --- | --- | --- |
| archived `messages.jsonl` / source event | `SOURCE` | committed input evidence |
| `.abstract.md` | `SUMMARY` | provider L0 summary |
| `.overview.md` | `SUMMARY` | provider L1 summary |
| full archive messages / memory file content | `SOURCE` for archive; `DERIVED` for extracted memory | L2 is a detail level, not one universal semantic surface |
| extracted `profile` memory | `PROFILE` | provider explicitly identifies profile memory |
| other extracted memory types | `DERIVED` | outputs of extraction/reconciliation |
| vector records | `VECTOR_INDEX` | secondary semantic index references |
| `find` results | `RETRIEVAL` | directly returned candidates |

No generic `GRAPH` or `CACHE` mapping is claimed. Memory types such as
entities/events are still extracted files; their names alone do not establish
a graph surface.

## Retrieval Surfaces

`find` is the primary benchmark primitive. It performs embedding/vector and
hierarchical retrieval without query-planner intent analysis. Results expose
URI, context type, level, abstract, optional overview/content, category, score,
and match reason. Phase 05 scopes it to `viking://~/memories` with context type
`memory` and requests content for exact observation.

`search` adds intent analysis, query expansion, and optional session context;
the deprecated `recall` route is a preset over `search(mode="context")`.
Neither is the primary canonical query because both add model-entangled
planning/assembly unnecessary for lifecycle-state inspection.

## Lifecycle Capability Mapping

| MemLife intent | Phase 05A mapping |
| --- | --- |
| reset namespace | delete only sessions with the adapter-owned namespace prefix; OpenViking owns associated session/memory cleanup |
| write | create isolated session, add one user message, commit, wait for completed task, parse memory diff |
| query | direct `find` over memory; retain only URIs correlated to the namespace |
| update | `UNSUPPORTED`; internal extraction update is not an external canonical update request |
| supersede | `UNSUPPORTED`; no explicit replacement or supersession edge is exposed |
| revoke/invalidate | `UNSUPPORTED`; no revoke/disable/tombstone primitive was found |
| delete | delete every provider memory URI directly correlated with the MemLife source event |
| history/audit | observed `memory_diff` operations for adapter-issued commits |
| inspect | read correlated provider memory URIs through content API |
| restart | stop/start only the run-owned service, retaining the same workspace |
| trigger derivation | explicit session `extract`; synchronous result list, distinct from commit task |

Session deletion and service restart are different. Session deletion is a data
lifecycle mutation; restart replaces only the process.

## Memory Diff / Audit Semantics

Every completed extraction writes a `memory_diff.json`, including an empty diff
when no operation applies. It contains archive URI, extraction time, `adds`,
`updates`, `deletes`, intentionally skipped operations with stable reasons, and
summary counts. Add rows have `after`; update rows have `before` and `after`;
delete rows have `deleted_content`.

This is directly observed operation provenance from one archive commit to the
changed memory URI set. It supports a known, coarse source-event/session/archive
to operation correlation. It does not prove which message span semantically
caused a particular field, why the LLM selected it, or that an internal merge
is a user-requested supersession.

## Provenance Mapping

The trace can directly record:

`MemLife source event -> session ID -> archive URI -> task ID -> completed task
-> memory-diff operation -> provider memory URI -> observed retrieval URI`.

The adapter never collapses this to a fabricated one-to-one memory ID. A
MemLife source event ID is the normalized write identity; provider memory URIs
are a separate zero/one/many set. Retrieval candidates carry the observed
source-event correlation when their URI appears in that commit's diff.

Known evidence: session/archive/task identifiers, task state, diff operation,
changed URI, direct retrieval URI. Unknown evidence: token/span-to-memory
semantic causality, unexposed extraction reasoning, and provider-internal
relationships not represented in the diff.

## Restart vs Session Reset

Future restart means stopping and starting the run-owned `openviking-server`
process against the same persistent workspace. The venv, AGFS content, vector
index, task records, archives, and model cache remain. Namespace reset deletes
only adapter-prefixed sessions and is never substituted for restart.

## Model Dependencies

The VLM performs semantic summaries, memory extraction, and dedup/reconciliation.
OpenViking documents Volcengine, OpenAI-compatible, OpenAI Codex, Kimi, GLM,
and LiteLLM routes. An OpenAI-compatible base URL is configurable, but Phase
05A does not assume a course chat model satisfies OpenViking's structured
extraction protocol. That compatibility remains a live preflight.

`search` may use a query planner (falling back to VLM); Phase 05 uses `find` to
avoid it. Audio/video understanding is optional and disabled. Reranking is
optional; when absent, retrieval uses vector similarity.

## Embedding Dependencies

Embedding is required for indexing and `find`. Current configuration documents
a built-in local dense default (`local` / `bge-small-zh-v1.5-f16`), Ollama,
OpenAI-compatible dense endpoints, Jina, Voyage, Gemini, Volcengine, and other
providers. Sparse/hybrid support is narrower. OpenAI compatibility for chat
does not imply an embeddings endpoint.

The prepared future run leaves the built-in local dense default in place and
does not configure sparse embedding or reranking. Its first live dependency
and resource check must validate model availability, CPU compatibility,
dimension, cache placement, memory, and latency before any canonical run.

## Jetstream Feasibility

The target Python 3.12 satisfies Python >=3.10. PyPI publishes a 28.8 MB
CPython 3.10 ABI3 `manylinux_2_31_x86_64` wheel, compatible in principle with
Ubuntu 24.04 x86-64, so the target should not need to compile the Rust/native
extensions. A source build would require CMake and Maturin and is not the
planned path. The wheel contains native RAGFS/vector-engine libraries and the
Rust CLI binary.

Official deployment guidance reports roughly 0.5 GB resident memory for a
typical small hosted service, but explicitly requires corpus/concurrency
measurement. With 2 vCPU, about 5.78 GiB RAM, no swap/GPU, and a constrained
root disk, a single-worker tiny validation is plausible, not yet proven. All
venv, workspace, cache, and run artifacts therefore live on the dynamically
resolved `/dev/sdb` volume. The script rejects unexpected CUDA/NVIDIA packages,
less than 1 GiB root free, or less than 8 GiB volume free.

Remaining live blockers are model-protocol compatibility and the actual local
embedding footprint/latency. Neither makes package installation impossible;
both must pass before canonical execution.

## Adapter Design

`OpenVikingTransport` is the provider boundary. `UrllibOpenVikingTransport`
validates URLs, sends optional credentials only as an authorization header,
unwraps the standard JSON envelope, and keeps secrets out of metadata. The
adapter records only sanitized identifiers/statuses in benchmark and trace
metadata.

The deterministic fake implements the documented create/add/commit/task/diff,
find/read/delete/extract, reset, and ready shapes. It covers multiple memories
per commit, failed tasks, non-terminal timeout, restart callback, and explicit
unsupported operations.

## Unsupported Semantics

- external canonical update;
- explicit supersession/replacement relation;
- semantic revocation/invalidation/disable/tombstone;
- per-span extraction lineage;
- treating internal dedup merge/delete as an externally requested lifecycle
  operation;
- treating session reset/deletion as service restart.

## Future Live Validation Plan

The inert, authorization-gated scripts will later: verify exact VM and Git
commit; resolve `/dev/sdb`; validate the clean harness; create/reuse
`<MEMLIFE_DATA_ROOT>/venvs/openviking-0.4.22`; reject CUDA/GPU dependencies;
write a private config; start a loopback-only run-owned service; check
readiness/version; run one session/commit/task/diff probe; retrieve it; restart
the service; verify persistence; then execute the canonical and provenance
instrumentation. The managed controller deletes only a floating IP it created
and shelves only a VM it opened.

The script requires `MEMLIFE_AUTHORIZE_PHASE05_LIVE=YES`. Future VLM values
must be placed in the Git-ignored remote file
`/home/exouser/Memo/.local/phase05_openviking.env` with mode `400` or `600`;
the values are sourced only on the VM and are never passed through command-line
arguments or result payloads. Phase 05A did not create that file or invoke the
script. The provenance runner produces the canonical benchmark rows and trace
in one pass, so no scenario is executed twice.

## RQ1 / RQ2 Value

OpenViking exposes more intermediate propagation state than the prior
providers. Future failures can be localized to synchronous archiving,
background task execution, memory reconciliation, AGFS content, vector index,
retrieval, or post-restart reconstruction. Successful convergence is equally
valuable as an architecture-diverse negative control.

## Non-Claims

Phase 05A made no live OpenViking call, provider installation, hosted model
call, canonical experiment, resurrection experiment, RQ3 decision-model run,
or final RQ4 defense evaluation. Feasibility is based on current official
metadata and must be live-qualified. Memory diff is an audit surface, not full
causal provenance.

## Phase 05B Live Readiness

Phase 05B remains local-only: Jetstream was not contacted, OpenViking was not
installed or started, and the course endpoint was not called. The readiness
changes are based on the exact upstream `v0.4.22` tag at commit
`e8716760934d95ef73414484a45bfe475b9296e2`, rather than current-main
assumptions. The pinned sources establish these contracts:

- `pyproject.toml:188-190` defines the `local-embed` extra as
  `llama-cpp-python>=0.3.0`;
- `openviking/models/embedder/local_embedders.py:19-39` defines the local
  cache default, model `bge-small-zh-v1.5-f16`, dimension 512, GGUF filename,
  and download URL;
- `openviking_cli/utils/config/embedding_config.py:57-125` defines
  `provider` as the current field, `backend` as deprecated compatibility, and
  supports `model_path` plus `cache_dir`; its local factory mapping at
  `985-993` passes those values to `LocalDenseEmbedder`;
- `openviking_cli/utils/config/vlm_config.py:135-205` supports `api_base`,
  `temperature`, `max_retries`, and `max_concurrent`, while
  `openviking/models/vlm/backends/openai_vlm.py` passes `api_base` to the
  OpenAI client's `base_url`;
- `openviking/server/routers/search.py:347-380` dispatches `/search/find` to
  `SearchService.find`, and `openviking/service/search_service.py:139-177`
  dispatches directly to `VikingFS.find`. It does not invoke the
  query-planner/VLM intent-analysis path used by `search`.

The provider requirement is now centralized at
`requirements/providers/openviking.txt` as
`openviking[local-embed]==0.4.22`. The future clean dependency proposal must contain
`llama-cpp-python` and must not contain `nvidia-*` or `cuda-*`; the installed
environment is checked for the same CPU-only policy. The requirement is
applied to both new and reusable isolated venvs. `llama-cpp-python` may
need a native Linux build if a compatible wheel is unavailable for the target,
so compiler time and memory remain a live risk rather than a presumed wheel.

Generated `ov.conf` now explicitly selects dense provider `local`, model
`bge-small-zh-v1.5-f16`, dimension 512, and cache directory
`<MEMLIFE_DATA_ROOT>/model_cache/openviking/embedding`. Storage remains local
AGFS/vector storage under the persistent provider workspace. Memory extraction
remains enabled.

The fixed provider-internal VLM is `openai` / `gpt-oss-120b` at
`https://llm.jetstream-cloud.org/gpt-oss-120b/v1/`, with the non-secret course
placeholder credential `empty`, temperature 0, concurrency 1, and one retry.
No backup model or aggressive output cap is configured. This is extraction
configuration, not the RQ3 decision model, and compatibility remains for the
controlled live probe to determine.

The managed controller now provisions
`/home/exouser/Memo/.local/phase05_openviking.env` automatically after exact
Git synchronization and before the remote runner. It creates `.local`, writes
all four fixed values with `umask 077`, enforces owner `exouser` and mode 600,
and never copies the values into result artifacts. `.local/` remains covered
by the repository runtime exclusion policy; no manual SSH setup is required.

Runtime/provider exceptions now serialize `status: BLOCKED`, blocker type,
sanitized blocker text, and a bounded sanitized service-log tail. They are not
re-raised by the validator. The remote shell emits `PHASE05_RESULT_B64` whenever
the result exists, even if an unexpected validator exit occurs; missing result
serialization remains a transport failure. The managed lifecycle controller
parses `payload.status` and treats non-PASS as the experiment blocker. PASS and
BLOCKED are the only Phase 05 live outcome values.

## Phase 05C Controlled Live Validation

The single authorized Jetstream2 lifecycle on 2026-09-29 is **BLOCKED before
installation and service startup**. Local and fetched remote branch heads were
both `913391b46eadde62a0d8dc7cd426f5a993ec8555`, and the managed session synced
the remote checkout to that exact commit. The live target was `jisheng3`
(`5baeeae7-4c29-4903-89fe-2e9df0a8eced`). The controller dynamically resolved
`/dev/sdb` to `/media/volume/jisheng3_volume`, used the persistent Phase 04
harness, and automatically provisioned the protected runtime file as
`exouser`, mode 600.

The required pip dry-run for `openviking[local-embed]==0.4.22` stopped on the
frozen guard:

```text
AssertionError: local-embed plan omitted llama-cpp-python
```

Per the no-live-fixes policy, the run did not install packages, change the
embedding provider, alter Python or package metadata, generate `ov.conf`, start
`openviking-server`, or retry. Consequently readiness, the compatibility
canary, provider-internal `gpt-oss-120b` compatibility, memory-diff parsing,
retrieval, restart persistence, canonical scenarios, and provenance were not
run. OpenViking made zero provider-internal model calls, and RQ3 decision calls
remain zero. No `PHASE05_RESULT_B64` payload was produced, so the remote result
status is `NOT_RETURNED`; the managed session status is `BLOCKED`.

The isolated provider venv, provider state, model cache, and run artifacts were
retained beneath the dynamically resolved persistent-volume root. The
run-created floating IP was disassociated and deleted, and the VM returned to
`SHELVED`. This result does not operationally qualify OpenViking and makes no
security, vulnerability, resurrection, or deletion-durability claim. The
tracked evidence is `manifests/phase-05c-openviking-live-validation.json`.

## Phase 05D Local Dependency and Controller Repair

Phase 05D confirmed that the Phase 05C blocker was a package-name
normalization defect, not evidence that the `local-embed` extra omitted its
dependency. The pinned OpenViking 0.4.22 metadata still declares
`llama-cpp-python>=0.3.0`; the resolved pip metadata spells the distribution
`llama_cpp_python`. Both canonicalize to `llama-cpp-python`, as does
`llama.cpp.python`. Plan validation now returns normalized names, both required
version candidates, missing requirements, and any forbidden `nvidia-*` or
`cuda-*` packages.

The locally observed candidate is `llama-cpp-python` 0.3.35. Its upstream
maintainer's CPU index provides a Python-compatible
`manylinux2014_x86_64.manylinux_2_17_x86_64` wheel, and a CPython 3.12 target
dry-run selected that artifact. The future remote commands use only that
official CPU index in addition to PyPI. They do not enable CUDA, GPU, Vulkan,
or an unofficial mirror. If wheel resolution changes and a source build is
required, the fallback needs a C/C++ compiler plus CMake and carries material
time/RAM risk on the small Jetstream VM.

The controller module no longer imports MemLife or Pydantic at local import
time. Runtime-only imports are confined to the remote validator. The undefined
`ROOT` manifest reference is replaced with `REPO_ROOT`, eliminating the
one-time Phase 05C recovery monkeypatch. Pre-validator gates now deliver
structured, bounded, sanitized `BLOCKED` results before returning a successful
transport exit, while the managed controller continues to decide live outcome
from the payload status. No provider or configuration semantics changed, and
Phase 05C still has no OpenViking semantic result because it stopped before
installation.

## Phase 05E Controlled Live Retry

The one authorized retry on 2026-09-29 tested commit
`8104aa682650393a9d36c881c7224721ff7bc252` through the normal managed
controller. Local and fetched origin heads matched, the remote checkout was
fast-forwarded to the same commit, `/dev/sdb` resolved live to
`/media/volume/jisheng3_volume`, and the protected runtime configuration was
provisioned automatically as `exouser` with mode 600.

The canonicalized dependency plan passed and execution advanced through
provider installation, `pip check`, exact OpenViking 0.4.22 metadata,
`llama-cpp-python` presence, the CUDA/NVIDIA rejection guard, executable
validation, and tracked config generation. These conclusions follow from the
remote shell's fail-closed gate order. The terminal result did not serialize
the exact live `llama-cpp-python`, pip, or config-hash values, so they remain
unreported rather than inferred.

The run is **BLOCKED at readiness**. The run-owned process started and its
sanitized log reported `OpenViking HTTP Server is running on 127.0.0.1:1933`,
but the adapter never observed readiness during the bounded 180-second window;
its final loopback error was connection refused. The controller emitted an
authoritative `PHASE05_RESULT_B64` payload with `status: BLOCKED` and a bounded
log tail. Per policy, no config change, model change, manual probe, repair, or
second live run was attempted.

Because readiness did not pass, the persistence canary, commit task,
provider-internal `gpt-oss-120b` compatibility, `memory_diff`, direct find,
restart persistence, canonical benchmark, deletion check, and provenance
trace were not run. RQ3 decision-model calls remained zero. The result makes
no provider-semantic or security claim.

Cleanup passed: the run-owned service stopped, the owned floating IP was
disassociated and deleted, retained provider assets remained on the persistent
volume, and a post-run read-only controller check reconfirmed `jisheng3` as
`SHELVED` with no address. Structured evidence is recorded in
`manifests/phase-05e-openviking-live-retry.json`; Phase 05C remains the earlier
pre-install blocker and Phase 05D remains the local repair.

## Phase 05F — Readiness Contract and Startup Diagnostics

Phase 05F is local-only. Jetstream remained shelved and no provider or hosted
model call was made. The exact `v0.4.22` source at commit
`e8716760934d95ef73414484a45bfe475b9296e2` establishes two separate system
contracts in `openviking/server/routers/system.py`:

- `GET /health` is liveness. Success is HTTP 200 with `status: "ok"`,
  `healthy: true`, and `version`.
- `GET /ready` is subsystem readiness. Success is HTTP 200 with
  `status: "ready"` and `checks`; initialization or a failed AGFS, vector DB,
  embedding, API-key-manager, or configured Ollama check returns HTTP 503 with
  `status: "not_ready"` and a reason or checks.

The old MemLife predicate accepted only literal `true`, `ready: true`, or
`healthy: true`. It therefore rejected the pinned provider's valid
`status: "ready"` response. The repaired predicate accepts `status == "ready"`
from `/ready`; it never treats `/health` or an arbitrary HTTP 200 as readiness.
The older boolean shapes remain only as compatibility for deterministic fakes
on the `/ready` endpoint. HTTP 503/not-ready, unknown payloads, and connection
failures are retried only until the bounded deadline. Final diagnostics retain
the last HTTP status, provider readiness status/checks, health status/version,
elapsed time, and request-error class without secrets.

The pinned bootstrap prints `OpenViking HTTP Server is running on ...` before
calling `uvicorn.run()`. ASGI lifespan then calls `service.initialize()`.
Consequently the banner proves neither socket/lifespan success nor AGFS,
vector DB, or embedding readiness.

The retained sanitized Phase 05E evidence contains the banner at 19:17:02,
workspace deprecation warnings, a session-manager shutdown at 19:19:55, and a
terminal connection-refused timeout. The log tail was collected after the
controller's `finally` cleanup, so the shutdown line may be cleanup itself; it
does not establish a pre-cleanup process exit. Nor does the evidence contain a
successful or rejected HTTP payload, lifespan traceback, or exit code. The
retained-log classification is therefore insufficient evidence for a second
root cause. Phase 05F does not infer embedding, vector DB, configuration, or
VLM failure from that evidence.

The run-owned controller now exposes `is_running()`, `exit_code()`, and a
bounded sanitized log tail for its own child only. Readiness stops immediately
if that child exits and future results report `stage: service_startup`,
`blocker_type: ServiceExitedBeforeReady`, the exit code, liveness/readiness
fields, and the log tail. No process-table scan or broad kill is used.

The next authorized runner preserves and validates
`<MEMLIFE_DATA_ROOT>/venvs/openviking-0.4.22`. If it exists, exact OpenViking
0.4.22 and `llama-cpp-python` metadata, `pip check`, executable presence, and
the CUDA/NVIDIA guard must pass; a bad retained environment blocks rather than
being replaced or upgraded. The embedding cache at
`<MEMLIFE_DATA_ROOT>/model_cache/openviking/embedding` is likewise preserved.
Provider configuration and all lifecycle mappings remain unchanged.

## Phase 05G — Live Semantic Qualification

The one authorized managed lifecycle on 2026-09-29 tested exact commit
`aa976a7d9b2ef37d8e8ba49b4c5091c1ec83e75e`. It began with `jisheng3`
`SHELVED`, created one owned temporary floating IP, synchronized the remote
checkout, resolved `/dev/sdb` to `/media/volume/jisheng3_volume`, ran the
frozen provider path, deleted the owned IP, and returned the VM to `SHELVED`.
No repair or second lifecycle was attempted.

The authoritative `PHASE05_RESULT_B64` payload is **PASS**. OpenViking 0.4.22,
`llama-cpp-python`, `pip check`, and the no-CUDA/NVIDIA guard passed before the
validator. Provider readiness returned `status: ready`; AGFS, vector DB, and
embedding were `ok`. The live health payload exposed `healthy: true` and
version `0.4.22`, but no `status` value. The strict result therefore records
service liveness as `NOT_ESTABLISHED` rather than inventing `status: ok`.

The persistence canary produced source event
`4fe51613-4c42-4867-bb24-4f2de8bad4c6` and correlated provider URI
`viking://user/default/memories/entities/system_component/phase_05_persistence_canary.md`.
Direct find returned one result before restart and one after restart. This
establishes provider-internal `gpt-oss-120b` compatibility for the exercised
extraction path, useful memory-diff correlation, direct-find retrieval, and
restart persistence. RQ3 decision calls remained zero.

All five canonical scenarios and Phase 03B traces ran. Update, supersession,
and revocation remained explicitly `UNSUPPORTED`; delete plus restart ran as
supported. The baseline find returned semantically relevant provider records,
although the benchmark's exact-match normalizer classified the query outcome
`ABSENT` and `current_state_correct=false`. Supersession correctly recorded
the operation as `UNSUPPORTED`, while its final inspect step separately
recorded `KeyError: 'v2'`. These observations are preserved rather than
relabelled.

The controller's top-level semantic result does not promote the canary session
ID, archive URI, task ID, quiescence duration, per-operation memory-diff
counts, service PID, exact `llama-cpp-python` version, environment-reuse flag,
or config hash. Those fields remain unreported. For the same reason, and
because strict liveness was not established, this record does not claim every
Phase 05 completion checkbox is satisfied even though Phase 05G's
authoritative remote status is PASS. Exact tracked evidence is in
`manifests/phase-05g-openviking-live-retry.json`.

## Phase 05H — Local Bring-up Closure

Phase 05H is a local-only closure on base
`acbad71da6073eb477c08f03da79893b1bb19d5b`; Jetstream remained shelved and no
provider or hosted-model call was made. The chronology is 05A PASS, 05B PASS,
05C BLOCKED, 05D PASS, 05E BLOCKED, 05F PASS, 05G LIVE PASS, and 05H LOCAL
PASS. Phase 05 is complete.

Provider operational facts remain those established by 05G: OpenViking 0.4.22
started, became ready, completed semantic extraction through the configured
provider-internal model, emitted and completed tasks, exposed memory diffs,
returned directly correlated memory through `find`, and retained it across an
owned-service restart. Phase 05H did not change the provider configuration,
embedding, VLM, capability map, source/derived distinction, or lifecycle
semantics.

The apparent liveness gap was an HTTP transport normalization defect. A
successful response with `status: ok` and a `result` member still unwraps the
result. A successful response without `result` now preserves the entire
provider mapping, including its real status. Strict liveness requires both
observed `status=ok` and `healthy=true`; `healthy=true` alone does not fabricate
status.

Future results serialize the explicit provider-environment reuse boolean,
exact OpenViking and `llama-cpp-python` versions from `importlib.metadata`, the
PID of the controller-owned child, and SHA-256 of the exact config bytes without
serializing those credential-bearing bytes. Completed-write evidence promotes
session, archive, task status/timestamps, provider-reported quiescence duration,
provider memory URI count, and separate add/update/delete/skipped diff counts.

The supersession `KeyError: 'v2'` was generic runner bookkeeping, not an
OpenViking failure. A dependent target now inherits `UNSUPPORTED` from an
unsupported producer or `ERROR` from an errored producer; unrelated queries
continue. Supported producers and existing Mem0/Hindsight behavior are
unchanged.

Phase 03 exact-text normalization is unchanged, and transformed derived memory
is never overwritten with source text. A supplementary diagnostic records only
directly observed, known source correlation: correlated retrieval count,
source IDs, and provider record IDs. It uses no similarity, LLM judge, or
inferred lineage. The experiment-wide authority rule remains an
experiment-freeze decision.

The retained 05G result is authoritative `PASS`/`complete`; its bounded service
log, collected in cleanup after semantic work, restart/persistence, canonical
execution, and PASS assignment, ends with `RuntimeError: Event loop is closed`.
This is retained as an upstream shutdown-cleanup warning and does not invalidate
operational qualification.
