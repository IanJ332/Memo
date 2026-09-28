# Phase 04 — Hindsight Bring-up

## Objective

Pin Hindsight, connect its native operations to the MemLife adapter and Phase
03B trace, then validate the self-hosted runtime in one controlled Jetstream2
session. The first live lifecycle is **BLOCKED before service startup** by an
exact dependency incompatibility. The isolated retry design is locally
**READY_FOR_RETRY**, but no second live lifecycle has been authorized or run.

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
- Install attempt: 2026-09-28
- Exact tested repository commit: `59222a27fcd59dc474ec282141a8b33bbc376088`
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

The live run stopped during dependency validation, so this architecture was not
started or runtime-qualified.

## Provider Runtime Isolation

The first attempt co-installed Hindsight and Mem0 in the project `.venv`.
Hindsight 0.10.1 requires `protobuf>=7.35.1`; Mem0 2.2.1 requires
`protobuf>=5.29.6,<7.0.0`. Pip resolved protobuf 7.36.2 and correctly reported
the single shared environment as inconsistent.

The reviewed retry separates the dependency graphs:

- Harness environment: `/home/exouser/Memo/.venv`, containing MemLife, Mem0,
  tests, benchmark code, and result collection.
- Provider environment:
  `<live /dev/sdb mount>/memlife/venvs/hindsight-0.10.1`, containing only the
  self-hosted Hindsight service runtime.
- Communication boundary: loopback HTTP at `127.0.0.1:8888` through the
  existing `UrllibHindsightTransport`.

The live mount remains dynamically derived with `findmnt /dev/sdb`. Explicit
`HARNESS_PYTHON`, `HINDSIGHT_VENV`, and `HINDSIGHT_PYTHON` names prevent command
ownership from being blurred. Harness health (`mem0ai`, protobuf, and `pip
check`) is captured before and after provider setup. The provider environment
has its own Hindsight/protobuf inspection and `pip check`. Cross-environment
protobuf versions need not match; a failed check inside either environment is
still fatal.

An absent provider venv may be created and populated from the service-only
requirements. A present venv is reused only after validation. Incomplete or
inconsistent state fails closed with bounded diagnostics and is never removed
automatically. The provider fingerprint records Python, pip, Hindsight, and
protobuf versions plus a SHA-256 of normalized `pip freeze` output.

Service start uses the executable inside `HINDSIGHT_VENV/bin`. The benchmark
and validation entry point use `HARNESS_PYTHON`. Restart replaces only the
run-owned API process and preserves the provider venv, pg0 state, and caches.
Exact PID ownership prevents broad Python cleanup; PID and service logs remain
under the persistent Phase 04 run directory.

This isolation is infrastructure architecture, not a defense. It cannot affect
lifecycle semantics, retrieval semantics, provenance results, or security
claims: the unchanged benchmark client still exercises Hindsight 0.10.1 through
the same public service API.

## Internal LLM Configuration

The fixed provider-internal configuration is OpenAI-compatible provider
`openai`, model `gpt-oss-120b`, using only the course-authorized hosted endpoint
and its supported non-secret placeholder. Its intended purpose is Hindsight fact
extraction and consolidation.

This is distinct from a future downstream decision LLM. Phase 04 made zero RQ3
decision-model calls. Because the service never started, structured-output
compatibility is **NOT RUN**, and no alternate course model was tried.

## Storage Architecture

Live `findmnt` resolved `/dev/sdb` as ext4 mounted at
`/media/volume/jisheng3_volume`. The run created these path classes beneath its
`memlife` root:

- `providers/hindsight/`
- `model_cache/hindsight/`
- `runs/phase-04-hindsight/`
- `artifacts/`

The planned backend is embedded pg0/PostgreSQL with pgvector and the named URL
`pg0://memlife-phase04`. `/home/exouser/.pg0` was managed as a link to the
persistent provider root. The blocker occurred before service startup, so no
provider database, derived state, or async state was runtime-verified.

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

These classifications passed deterministic fake-transport tests but were not
confirmed against a running service in the blocked live attempt.

## Lifecycle Capability Mapping

| Capability | Pinned native mapping | Live result |
| --- | --- | --- |
| Write | synchronous retain | NOT RUN |
| Query | recall over world, experience, observation | NOT RUN |
| Update | same-ID memory text curation | NOT RUN |
| Supersede | same-ID edit; no native supersession edge | NOT RUN |
| Revoke/invalidate | state=`invalidated` curation | NOT RUN |
| Delete | document-scoped native delete | NOT RUN |
| History | observation history endpoint; source facts may be empty | NOT RUN |
| Inspect | list valid and invalidated memory units | NOT RUN |
| Restart | stop/start service against the same pg0 instance | NOT RUN |
| Trigger derivation | submit consolidation and poll operation | NOT RUN |

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
local tests, including a fake observation with explicit source IDs. A real
Hindsight trace was not produced because dependency validation failed first.

## Async / Quiescence Semantics

Retain is frozen as synchronous. Consolidation and maintenance are treated as
asynchronous provider operations. The adapter captures operation IDs that
pre-date a mutation and polls new operations until none is `pending` or
`processing`; a failed operation is an error. Explicit consolidation polls its
returned ID until `completed`. Benchmark metadata records submitted/completed
timestamps and the quiescence criterion.

This mechanism passed deterministic unit tests but did not run against the live
service.

## Canonical Benchmark Result

The canonical Phase 03 scenarios were **NOT RUN**. The shared remote `.venv`
became inconsistent after Hindsight installation: Hindsight 0.10.1 requires
`protobuf>=7.35.1`, while Mem0 2.2.1 requires
`protobuf>=5.29.6,<7.0.0`. `pip check` reported protobuf 7.36.2 as incompatible
with Mem0 and the script stopped before starting Hindsight, exactly as required
by the failure policy.

No normalized provider outcome is reported for baseline, correction/update,
supersession, revocation, or delete+restart.

## Restart Result

**NOT RUN.** Neither service startup nor pg0 reconstruction occurred.

## Negative-Control Interpretation

No negative-control interpretation is possible from this run. The result is an
environment/package co-installation blocker, not evidence for or against
Hindsight lifecycle propagation.

## Limitations

- The only authorized lifecycle ended before the compatibility probe.
- The blocker concerns co-installing current pinned Hindsight and predecessor
  Mem0 in one virtual environment; it is not a Hindsight memory-semantics result.
- No alternate version, isolated provider virtual environment, internal LLM,
  embedding backend, database backend, or second lifecycle was attempted.
- Local Windows tests use a deterministic fake transport; they do not replace
  the required real self-hosted validation.

## Reproduction

Local preparation at the tested commit:

```powershell
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.venv\Scripts\python.exe scripts\jetstream\jetstreamctl.py phase04
```

The isolated-runtime preparation results were `71 passed` (unit), `5 passed`
(contract), `5 passed, 1 skipped` (integration), and `81 passed, 1 skipped`
(full). The skip is the opt-in real Hindsight integration test; the Mem0
regression subset remained green with `5 passed`, and the focused Phase 03/03B
lifecycle/trace regression had `15 passed`. The second command is recorded only
as historical reproduction provenance: the one authorized Phase 04 lifecycle
has already been consumed and must not be rerun without explicit approval.

The controller recorded exact VM UUID
`5baeeae7-4c29-4903-89fe-2e9df0a8eced`, deleted the temporary floating IP it
created, and returned the initially shelved VM to `SHELVED`.

## Git Trace

- `4bc25488ba4579cf1d3dcea872aba1ccdb168841` — freeze Hindsight configuration
- `7508bd7d2244f98f842e657e45a0568485bd60ed` — add Hindsight adapter
- `59222a27fcd59dc474ec282141a8b33bbc376088` — add tests and managed validation; exact live tested commit
- `31e7cc6d975e2ae708b5736734c5c59961b63387` — record the sanitized blocked result

The final trace-only documentation commit is the branch HEAD reported in the
completion response. The approved base remains
`c125a59740819f264b5d57c67cde293fbf490346`.

## Next Experiment Handoff

The isolated provider virtual environment is now reviewed and locally tested.
A new conversation and separate authorization may run one managed Phase 04
Jetstream retry from the current branch; until then the original live result
remains BLOCKED and all live benchmark fields remain NOT RUN.
