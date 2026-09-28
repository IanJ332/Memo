# Hindsight 0.10.1

## Role in MemLife-NLIP

Hindsight is the second real provider behind the MemLife adapter contract. The
Phase 04 configuration is intended to measure native lifecycle propagation,
including provider-derived observations, rather than to force a failure. A
fully successful result is useful as a negative control for later RQ1/RQ2 work.

## First-Party Version Freeze

The configuration was derived from the official `vectorize-io/hindsight`
repository and Hindsight documentation. The tested release is `v0.10.1`, Git
commit `f8950b0c07d9e34c76493dba802bb309f0ce60fd`. The provider requirements are
isolated from `requirements/core.txt`:

```text
hindsight-api-slim[embedded-db,local-onnx]==0.10.1
hindsight-client==0.10.1
```

The service packages require Python 3.11 or newer; the Jetstream target uses
Python 3.12.3. The broad `local-ml` extra is intentionally not used because it
includes PyTorch. The officially supported `local-onnx` extra provides a CPU
embedding path for the no-GPU VM.

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
runtime environment is defined by `scripts/jetstream/phase04_remote.sh`. The
managed controller performs the single lifecycle, synchronizes the exact Git
commit, validates package resolution before installation, runs the compatibility
probe first, captures sanitized results, deletes its temporary floating IP, and
returns a VM that it opened to `SHELVED`.
