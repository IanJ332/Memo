# Hindsight 0.10.1

## Role in MemLife-NLIP

Hindsight is the second real provider behind the MemLife adapter contract. The
Phase 04 configuration is intended to measure native lifecycle propagation,
including provider-derived observations, rather than to force a failure. A
fully successful result is useful as a negative control for later RQ1/RQ2 work.

## First-Party Version Freeze

The configuration was derived from the official `vectorize-io/hindsight`
repository and Hindsight documentation. The pinned candidate is `v0.10.1`, Git
commit `f8950b0c07d9e34c76493dba802bb309f0ce60fd`. The service requirements are
isolated from `requirements/core.txt`:

```text
hindsight-api-slim[embedded-db,local-onnx]==0.10.1
```

`hindsight-client` is intentionally not installed. The MemLife adapter uses
the standard-library `urllib.request` transport against the REST API, so a
Python client would add an unjustified package dependency without changing the
experiment interface.

The service packages require Python 3.11 or newer; the Jetstream target uses
Python 3.12.3. The broad `local-ml` extra is intentionally not used because it
includes PyTorch. The officially supported `local-onnx` extra provides a CPU
embedding path for the no-GPU VM.

The single live installation attempt on 2026-09-28 stopped at `pip check`:
Hindsight 0.10.1 requires `protobuf>=7.35.1`, whereas the predecessor's pinned
Mem0 2.2.1 installation requires `protobuf>=5.29.6,<7.0.0`. Pip selected
protobuf 7.36.2 for Hindsight, making the shared virtual environment
inconsistent. In accordance with the one-run failure policy, no alternate
Hindsight version, Mem0 version, virtual environment, or backend was tried in
that live lifecycle.

The one authorized isolated-runtime retry ran on 2026-09-29 at commit
`2f85ba07a3172103c6008f566c3c017fd5cce884`. It stopped at the mandatory
harness preflight, before the isolated provider venv was created or installed.
The preexisting harness still contained protobuf 7.36.2 from attempt 1, which
is incompatible with Mem0 2.2.1, and also contained OpenAI 3.13.0, which is
incompatible with LiteLLM 1.103.0's `<3.0.0` constraint. No Hindsight service,
compatibility probe, benchmark, or real trace ran. This is a persisted harness
state blocker, not evidence against the isolation architecture or Hindsight's
memory semantics.

## Provider Runtime Isolation

The reviewed retry architecture uses two intentionally independent Python
process environments. The MemLife harness and Mem0 remain in
`/home/exouser/Memo/.venv`. The Hindsight API runtime is derived from the live
`/dev/sdb` mount as
`<MEMLIFE_DATA_ROOT>/venvs/hindsight-0.10.1`. Only
`requirements/core.txt` is applied to the harness during Phase 04 setup; only
`requirements/providers/hindsight.txt` is applied to the provider venv.

Each environment must pass its own `pip check`. The harness is inspected for
`mem0ai` and `protobuf` before and after provider setup, and the provider venv
is separately inspected for Hindsight and protobuf. Different protobuf
versions across the two environments are expected and valid. An incompatibility
inside either individual environment remains a hard failure. Existing provider
venvs are reused only if their interpreter, pinned package, executable, and
dependency graph validate; incomplete state fails closed and is not deleted or
rebuilt automatically.

The boundary is loopback HTTP at `127.0.0.1:8888`. Hindsight owns its API,
embedded pg0 process, ONNX runtime, and provider dependencies; the harness owns
the adapter, benchmark, tests, and result collection. The service is launched
from the provider venv, while every benchmark/test command uses the harness
Python. Restart stops and starts only the run-owned service process against the
same database, venv, and caches. A PID file and logs live under the persistent
Phase 04 run directory, outside Git.

This is infrastructure architecture, not a defense. It does not alter
lifecycle or retrieval semantics, provenance interpretation, or security
claims. The same benchmark adapter calls the same Hindsight 0.10.1 service API;
isolation only prevents unrelated package constraints from corrupting Mem0's
validated experimental environment.

## Deployment

The selected deployment is one bare-metal self-hosted `hindsight-api` process.
It uses the package's embedded pg0 PostgreSQL distribution with pgvector. This
avoids modifying the Exosphere-managed Docker environment. The service binds to
loopback only and is called through Hindsight's public REST API.

The live `/dev/sdb` mount is resolved for every run. The managed
`/home/exouser/.pg0` path is a symlink to the provider directory on that volume;
the run refuses to replace an existing non-symlink path. Hindsight's model cache,
run artifacts, and database therefore remain on the persistent volume. The
database URL is `pg0://memlife-phase04`; pg0's own instance layout remains
provider-managed beneath that redirected root.

The first live attempt created the persistent-volume directories and pg0 path
link, but it stopped before starting the API. The retry stopped even earlier at
harness health validation. Consequently no Hindsight database was initialized
and no persistence or restart claim was measured.

## Fixed Provider-Internal LLM

Hindsight's internal fact extraction and consolidation use one fixed
OpenAI-compatible configuration: provider `openai`, model `gpt-oss-120b`, and
the course-authorized hosted endpoint. The API-key field contains only the
course-supported placeholder. The first live operation is a tiny structured
output compatibility probe; failure stops the run without changing model or
backend.

This provider-internal LLM is not a downstream decision model. Phase 04 makes
zero RQ3 decision-model calls and does not compare course models.

## Embedding and Reranking

- Embeddings: in-process ONNX, `intfloat/multilingual-e5-small`, 384 dimensions
- Query prefix: `query: `
- Passage prefix: `passage: `
- Reranker: reciprocal-rank fusion (`rrf`), with no cross-encoder model
- Retrieval: native `recall`, not `reflect`

Recall requests include `world`, `experience`, and `observation` records. They
also request the source-fact fields for observation results so that derived
influence is not hidden from the lifecycle benchmark.

## Native Operation Mapping

| MemLife intent | Hindsight 0.10.1 operation |
| --- | --- |
| Reset namespace | `DELETE /v1/default/banks/{bank}/memories` |
| Write | synchronous `POST .../memories` retain |
| Query | `POST .../memories/recall` |
| Update | `PATCH .../memories/{id}` text curation |
| Supersede | same-ID text curation; no native supersession edge |
| Revoke | `PATCH .../memories/{id}` with `state=invalidated` |
| Delete | `DELETE .../documents/{document_id}` |
| Inspect | `GET .../memories/list` for valid and invalidated rows |
| History | `GET .../memories/{id}/history` (observation history only) |
| Restart | stop/start API and reconstruct from the same pg0 instance |
| Trigger derivation | `POST .../consolidate`, then poll operation status |

The adapter retains one uniquely identified document per MemLife write. It
accepts the returned record only when Hindsight exposes one unambiguous source
fact for that document. Hard deletion is document-scoped. Observations cannot be
curated through the source-fact edit/invalidation endpoint. No unsupported edge
or tombstone is synthesized.

## Source, Derived, and Provenance Surfaces

Hindsight 0.10.1 lists `world` and `experience` facts as provider source
surfaces. `observation` rows are classified as derived. Mental models and
knowledge structures exist as separate native concepts but are not mapped into
the Phase 04 lifecycle contract because the tested recall/list path does not
justify treating them as the same memory records.

Observation rows expose `source_memory_ids`; recall exposes the corresponding
`source_fact_ids` when requested. Only those explicit IDs support a known
`DERIVED_FROM` association. Source facts do not expose causal lineage, and a
same-ID edit does not establish `SUPERSEDES`, so those relations remain
`UNKNOWN`. Retrieval itself is directly observed and recorded as
`RETRIEVED_AS` by the existing Phase 03B trace.

## Async Semantics

Retain is configured synchronously, but consolidation and maintenance can run
through provider operations. The adapter captures the set of pre-existing
operation IDs, submits the native mutation, and polls new operations until none
is `pending` or `processing`; failures are surfaced as adapter errors. Explicit
consolidation polls its returned operation ID until `completed`. Submitted and
completed timestamps plus the quiescence criterion are attached to benchmark
metadata. Arbitrary long sleeps are not used as the correctness mechanism.

## Scope and Limitations

These mappings apply only to Hindsight 0.10.1 under the frozen Phase 04
configuration. The benchmark uses small synthetic facts on one Ubuntu VM. It is
not a performance, concurrency, attack, RQ3, or final RQ4 evaluation. Provider
history is observation history, not a general source-edit audit log. Native
same-ID curation is not represented as a fabricated supersession chain.

## Reproduction

The exact non-secret configuration is in `configs/hindsight-phase04.json`; the
runtime environment is defined by `scripts/jetstream/phase04_remote.sh`, with
service ownership and environment fingerprinting in
`scripts/jetstream/phase04_runtime.py`. A future separately authorized recovery
must first repair or recreate the harness `.venv` under an explicitly reviewed
procedure; no further live retry is authorized by Phase 04 attempt 2.

For the 2026-09-28 run, dependency installation blocked before the compatibility
probe. The controller still deleted its temporary floating IP and returned the
VM to `SHELVED`. See `manifests/phase-04-hindsight-bringup.json` and
`docs/phases/PHASE_04_HINDSIGHT_BRINGUP.md` for the measured result.

For the 2026-09-29 retry, the controller synchronized the retry commit and
stopped when the harness preflight exposed the persisted protobuf/OpenAI
conflicts. It did not touch the isolated provider environment or start a
service. Cleanup again deleted the owned temporary floating IP and verified the
VM `SHELVED` with no address.
