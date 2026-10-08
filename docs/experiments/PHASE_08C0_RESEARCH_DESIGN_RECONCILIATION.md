# Phase 08C-0 — Research Design Reconciliation

> **Status:** `DESIGN_COMPLETE`
> **Execution:** `DOCUMENTATION_AND_OFFLINE_RESEARCH_ONLY`
> **Authoritative base:** `b1ff61b862a45df41405eb821d3a46318eb66c29`
> **Jetstream:** `NOT_USED`; remains `SHELVED`
> **Provider calls:** `0`
> **Hosted model calls:** `0`
> **Downstream/RQ3 calls:** `0 / 0`

## Decision

Preserve the published Phase 08A Freeze-v2 draft unchanged and keep its live
expansion schedule blocked. Prioritize a separately authorized, offline RQ4
mediator implementation and evaluation using frozen empirical evidence plus a
strictly separate synthetic challenge suite. In parallel only at the design
level, prepare a RetainDB Server acceptance preflight. Do not create a revised
Freeze-v2 draft until either (a) a Provider-5 acceptance result exists or (b)
the scientific role of a one-provider or Provider-5-only extension is approved
independently.

This is a staged combination of options A and C. Option B remains the correct
change-control mechanism if the expansion design is later changed, but it is
premature now. Freeze v2 is not finalized.

## Frozen premises

- Candidate10 attempt `20261007T165110Z-19d0ccd6b106` is scientifically closed.
- Honcho 3.2.1 at commit
  `79cb31645f4efdef626d1bd9316a648adb5da89b` has a frozen `NO_GO`
  acceptance result: 10 required capabilities `SUPPORTED`, 4 `UNSUPPORTED`,
  and 4 `UNKNOWN`. Only S0 was directly executed.
- Candidate10 is not rerun, replaced, reclassified, or used as evidence of a
  provider security failure.
- Experiment Freeze v1 and its canonical SHA-256
  `0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b`
  remain unchanged.
- The original
  [`experiment-freeze-v2.draft.json`](../../experiments/freeze/experiment-freeze-v2.draft.json)
  and its Phase 08A validator are unchanged. This report is not a silent gate
  revision or a new freeze.

## Freeze-v2 reconciliation

### Requirements that assume Honcho `GO` plus an accepted Provider 5

| Phase 08A requirement | Honcho `NO_GO` implication |
| --- | --- |
| Finalization requires completed live acceptance evidence for Honcho and the selected Provider 5. | The finalization prerequisite is unsatisfied and cannot become true for the frozen Honcho 3.2.1 Candidate10 result. |
| The proposed extension is Honcho plus exactly one mutually exclusive Provider-5 choice. | The proposed two-provider extension composition cannot be instantiated as written. |
| Future schedules are restricted to accepted Honcho plus one accepted Provider 5. | No live Freeze-v2 schedule can be generated under the current draft, even if RetainDB or Graphiti later receives `GO`. |
| The maximum-new-run calculation assumes two accepted new providers, with three repetitions per supported S0-S5 cell. | The stated maximum of 36 new runs is no longer an actionable schedule bound; it remains historical design intent only. |
| Provider 4 is fixed as Honcho with a pending acceptance gate and placeholder native/scenario matrices. | Candidate10 resolves the frozen acceptance result to `NO_GO`, but Phase 08A's immutable draft-specific validator intentionally still requires the original pending placeholder. The draft must not be edited in place. |
| Freeze-v2's five-provider expansion objective depends on adding both Provider 4 and Provider 5. | The five-provider empirical objective is blocked. A four-provider, Provider-5-only, or replacement-Provider-4 design would be a new scientific design requiring a separately versioned revision and approval. |

The blocked items are the future live schedule, the two-provider incremental
comparison, the five-provider contribution claim, and Freeze-v2 finalization.
The Honcho result does not block Provider-5 feasibility research, Provider-5
acceptance preparation, analysis of existing provider evidence, or offline RQ4
mediator research. It also does not make Graphiti eligible: the fallback gate
is activated only by a RetainDB `NO_GO`, not by a Honcho `NO_GO`.

### Decision options

| Option | Scientific value | Risk and decision |
| --- | --- | --- |
| A. Preserve the draft and leave expansion blocked. | Strongest protocol integrity; records that the predeclared design encountered a real feasibility boundary. | Necessary now, but alone would stall the central authority-enforcement contribution. Adopt as governance state. |
| B. Create a separately versioned design revision. | Correct way to study a replacement Provider 4, Provider-5-only extension, or changed schedule without rewriting history. | Premature before Provider-5 evidence or an approved revised objective; doing it now would optimize around an unknown provider. Defer. |
| C. Prioritize provider-independent RQ4 research. | Directly tests `Retrieved != Authoritative`, uses existing cross-provider evidence, and turns the Honcho boundary into motivation for pre-LLM enforcement. | Requires synthetic inputs for policy branches not present empirically; those inputs must remain segregated. Adopt as the immediate scientific priority. |

## RetainDB Server feasibility preview

### Source identity and deployment facts

The exact upstream identified on 2026-10-08 is
[`RetainDB/RetainDB`](https://github.com/RetainDB/RetainDB). The upstream
`main` history identified commit
[`2ad2cc4d6d58145eca1a6cbbce66dfc5b5380f38`](https://github.com/RetainDB/RetainDB/commit/2ad2cc4d6d58145eca1a6cbbce66dfc5b5380f38)
dated 2026-06-12. A future preflight can pin this or another explicitly
approved full commit and archive its Git tree, lockfile, build inputs, and
resulting image digests. The repository has a `pnpm-lock.yaml`; its root
package is private version `0.0.0`, while `packages/server` declares `1.0.0`.
No release artifact is relied upon here.

The self-hosted server path requires Node (declared `>=18`), pnpm, and Postgres
with pgvector. The upstream Compose builds the server and starts
`pgvector/pgvector:pg16`; the server image is built from `node:20` and
`node:20-slim`. These are mutable tags rather than digest pins. The Compose
publishes both ports 3000 and 5432, uses a named `pgdata` volume, and defaults
the shared deployment API key to `changeme`. A future acceptance configuration
must bind services to the smallest required network surface, use an
attempt-scoped secret, pin base images by digest, and place provider-owned data
under the dynamically resolved persistent-volume root. These configuration
changes must be declared, hashed, and checked against the audited source; they
cannot be silently applied.

The repository root carries an Apache-2.0 license file, while the README says
`packages/server` is Business Source License 1.1, self-hosting is free, and a
hosted competing service requires a commercial license. That package-specific
statement conflicts with the repository-level license signal and no separate
server license text was established in this preview. Treat server licensing as
a preflight blocker pending archival and review of the exact pinned commit's
applicable license materials; this report makes no legal conclusion.

The official API documentation describes memory write, search, read, update,
delete, and async job-status routes. The upstream schema contains memory IDs,
versions, `validFrom`/`validUntil`, `supersededBy`, relationship edges, source
versions, and job status/timestamps. The Compose persists PostgreSQL under its
named volume, and the server startup path recovers interrupted jobs. These are
useful static signals, not provider-observed acceptance evidence.

Primary sources used for this preview:

- [upstream README and deployment contract](https://github.com/RetainDB/RetainDB)
- [upstream commit history](https://github.com/RetainDB/RetainDB/commits/main/)
- [self-hosted Compose](https://raw.githubusercontent.com/RetainDB/RetainDB/main/docker-compose.yml)
- [server Dockerfile](https://raw.githubusercontent.com/RetainDB/RetainDB/main/packages/server/Dockerfile)
- [server package metadata](https://raw.githubusercontent.com/RetainDB/RetainDB/main/packages/server/package.json)
- [server data schema](https://raw.githubusercontent.com/RetainDB/RetainDB/main/packages/server/prisma/schema.prisma)
- [official Memory API](https://www.retaindb.com/docs/api/memory)

### Acceptance capability preview

All classifications remain `UNKNOWN`. The middle column is a static research
signal and must never be promoted to `SUPPORTED` without an independently
authorized live calibration artifact.

| Required capability | Static documentation/source signal | Acceptance state |
| --- | --- | --- |
| `create_write` | `POST /v1/memory` is documented. | `UNKNOWN` |
| `retrieval` | Search, direct read, profile, and session routes are documented. | `UNKNOWN` |
| `exact_provider_native_ids` | API examples and the schema expose memory IDs. | `UNKNOWN` |
| `exact_raw_response_capture` | HTTP surfaces appear capturable, but byte-preserving capture and error behavior are untested. | `UNKNOWN` |
| `source_version_transitions` | `SourceVersion` and memory version/supersession fields exist. Their native transition semantics are untested. | `UNKNOWN` |
| `temporal_validity` | `validFrom`, `validUntil`, `expiresAt`, and active-state fields exist. Enforcement at retrieval is untested. | `UNKNOWN` |
| `provenance_relationship_edges` | Memory and entity relation tables exist, with source/chunk links. Completeness and API exposure are untested. | `UNKNOWN` |
| `deterministic_or_recorded_ordering` | Search returns ranked results and scores. Stable tie-breaking and exact order capture are not established. | `UNKNOWN` |
| `restart_persistence` | PostgreSQL has a named persistent volume and startup recovery logic. No controlled restart observation exists. | `UNKNOWN` |
| `quiescence_async_completion_proof` | Async writes and job-status polling are documented; workers and recovery paths exist. A bounded completion criterion is not calibrated. | `UNKNOWN` |
| `provider_configuration_pinning` | Environment inputs are enumerable, but effective configuration capture is not yet designed. | `UNKNOWN` |
| `provider_version_commit_pinning` | Full Git commit pinning is feasible; dependency lockfile exists. Base images and the effective built image still need digest capture. | `UNKNOWN` |

Additional lifecycle capabilities (`update_supersede`, `hard_delete`,
`restart_reconstruction`, native rederivation/consolidation,
`revoke_invalidate`, and frozen-semantics raw inspection) also remain
`UNKNOWN`. Route names or schema fields do not establish their required
semantics.

### Hardware, storage, and model risks

Upstream publishes no minimum CPU, RAM, disk, or cold-start budget. The
available Jetstream instance has 2 vCPU, about 5.78 GiB RAM, no swap, a
constrained root disk, no GPU, and an approximately 49 GiB persistent volume.
The server builds native dependencies, runs Node plus Postgres/pgvector, and
can load a local embedding model. Therefore live feasibility on this hardware
is `UNKNOWN`, not assumed.

The default Compose named volume would use Docker's root storage rather than
the research persistent volume. A future preflight must estimate image/model/
database sizes without pruning or changing Exosphere-managed containers, then
design an attempt-scoped bind mount under the live-resolved `/dev/sdb` mount.
It must also decide whether provider-internal extraction and embeddings run
locally or through a pinned endpoint. Any provider-internal model calls require
separate authorization, configuration pinning, and accounting; they remain
distinct from downstream and RQ3 calls.

### Required future RetainDB preflight outputs

1. Archive exact repository URL, full commit, Git tree, lockfile hash, license
   materials, Compose/Dockerfile hashes, base-image digests, and built-image
   digest.
2. Produce an offline endpoint/source audit mapped to all 18 frozen
   capabilities, without declaring live outcomes.
3. Define an attempt-isolated configuration, network boundary, persistent-data
   path, model configuration, raw-response recorder, and secret redaction
   contract.
4. Define bounded readiness and quiescence probes, restart/persistence checks,
   ordering capture, and failure/cleanup policy.
5. Estimate CPU, peak RAM, root and persistent disk, build time, and possible
   model/API cost before requesting a live lifecycle.
6. Keep Graphiti `FALLBACK_ONLY`. Only a completed RetainDB `NO_GO` makes it
   eligible for its own independently authorized acceptance.

## RQ4 mediator research roadmap

### Offline research question

Can a deterministic, provider-independent authority firewall prevent
unauthorized or unresolved retrieved candidates from influencing serialized
LLM context while preserving current authoritative propositions that retain
historical or superseded lineage?

### Evidence separation

Two fixture registries must be physically and semantically separate:

1. `PROVIDER_OBSERVED`: deterministic normalized fixtures derived from frozen
   Phase 06B/07 evidence with exact attempt, run, artifact, and hash provenance.
   Initial cases are Mem0 S1 and Hindsight S1 as current-content/mixed-lineage
   negative controls, Hindsight S4 as legitimate rederivation, and OpenViking
   S4 as variable derived-state production without unauthorized exposure.
2. `SYNTHETIC_RQ4_CHALLENGE`: explicitly generated cases for stale proposition,
   revoked source, unresolved identity, missing lineage, and mixed-authority
   aggregation branches that existing empirical evidence does not instantiate.

Synthetic fixtures may evaluate RQ4 policy behavior. They cannot establish a
provider failure, change an empirical provider classification, activate RQ3,
or be pooled into provider-observation counts.

### Deterministic policy pipeline

1. **Source authority ledger.** Build an append-only ledger from source events,
   with logical-fact ID, version ID, source-event ID, sequence, lifecycle state,
   authorization state, exact source-record hash, canonical proposition hash,
   and supersession/revocation links. Reject duplicate or contradictory event
   coordinates.
2. **Canonical proposition identity.** Populate proposition identity only from
   fixture-declared byte canonicalization. Preserve raw provider-record identity
   separately. No embedding similarity, LLM equivalence, or free-text inference
   may create an authorization identity.
3. **Lineage-aware candidate normalization.** Convert retrieved evidence into
   `CandidateEnvelope` objects without discarding rank, surface, raw bytes,
   provider IDs, source IDs, relation edges, time hints, or evidence class.
   Unresolved identifiers remain unresolved.
4. **Authority resolution.** Join candidates to independent
   `AuthoritySnapshot` records by exact identities. Evaluate proposition
   currency separately from ancestry: a current proposition with superseded
   ancestry is not stale merely because its lineage is mixed.
5. **Policy decision.** `ALLOW` only when exact proposition authority is current
   and required identity/lineage evidence is resolved; `DENY` when exact
   evidence proves the candidate proposition or direct source is stale,
   revoked, deleted, or unauthorized; `QUARANTINE` when identity, lineage, or
   evidence is insufficient or contradictory.
6. **Pre-LLM enforcement.** Only `ALLOW` candidates enter the context serializer.
   `DENY` and `QUARANTINE` candidates are retained in separate audit artifacts
   and contribute zero bytes to model-boundary context.
7. **Auditability.** Emit canonical input/snapshot hashes, policy version,
   reason codes, current/stale witnesses, unresolved edges, per-candidate
   decisions, delivered-context bytes/hash, and a completion ledger. Use a
   frozen evaluation timestamp as policy input or exclude wall-clock metadata
   from the semantic decision hash so identical inputs yield identical
   decisions.

### Rejection and quarantine semantics

- `DENY` is a conclusive authority result supported by exact evidence. It is
  excluded from delivery but retained for audit.
- `QUARANTINE` is fail-closed uncertainty, not a provider failure and not a
  synonym for `DENY`. It is excluded from delivery, preserved with unresolved
  witnesses, and may be reevaluated only against a new explicitly versioned
  authority snapshot.
- Candidate-level decisions precede aggregation. A serializer must never
  smuggle denied/quarantined text through summaries, metadata, tool traces, or
  diagnostic fields.

### Offline evaluation and acceptance criteria

- Empirical negative controls must allow current v2 proposition content despite
  superseded ancestry; naive lineage-only denial must fail a regression test.
- Synthetic stale/revoked cases must deny, and unresolved cases must quarantine.
- Repeated evaluation of the same canonical bundle must produce the same action,
  reason codes, witnesses, and semantic hashes.
- Delivered-context byte scans and exact candidate accounting must prove zero
  unauthorized influence before any model boundary.
- Every output must resolve to an input fixture, authority snapshot, policy
  version, and exact SHA-256.
- Evaluation uses no LLM judge, embedding authorization, provider call,
  downstream model call, or RQ3 call.

## Recommended next phases

### Next scientific phase — Phase 08C-1

Implement and evaluate the offline deterministic RQ4 mediator against the
segregated empirical and synthetic fixture registries. This has the strongest
connection to the central thesis, immediately uses the three-provider frozen
evidence and the Honcho integration-boundary finding, has minimal blocked-run
risk, is reproducible on local hardware, and adds no provider/model cost. It
also supports a top-journal narrative centered on authority enforcement and
false-positive control rather than provider accumulation.

Phase 08C-1 must not claim empirical defense efficacy for synthetic branches.
Its empirical contribution is false-positive/availability preservation and
auditable handling of observed lineage; its synthetic contribution is policy
conformance and adversarial branch coverage.

### Next engineering phase — Phase 08C-1 implementation

1. Freeze an RQ4 policy draft and reason-code vocabulary without touching the
   Freeze-v2 experiment draft.
2. Extend strict models only as required for authority-ledger events,
   per-candidate resolution, and deterministic serialization.
3. Add exact-provenance fixture builders for frozen empirical cases and a
   separately rooted synthetic challenge corpus.
4. Implement the deterministic policy engine and allow-only context serializer.
5. Add unit, property, mutation, replay, and byte-leakage tests plus a local
   validator and completion manifest.
6. Produce an offline evaluation report separating empirical and synthetic
   results and recording zero model/provider calls.

### Subsequent provider phase — RetainDB preflight, then optional live acceptance

After or independently alongside Phase 08C-1, a design-only RetainDB preflight
may implement the six outputs listed above. A live RetainDB calibration is a
different phase and requires explicit authorization. Its result stays
`PENDING_LIVE_ACCEPTANCE` until then. Only after Provider-5 evidence exists
should the project choose whether a separately versioned Freeze-v2 revision is
scientifically warranted.

## Unresolved questions

- Does the exact pinned RetainDB Server source have an unambiguous applicable
  license for the intended research deployment?
- Can the server build and run within 2 vCPU, 5.78 GiB RAM, no swap, and the
  safe storage constraints without remote embeddings or extraction calls?
- Which API responses expose complete version, temporal, and relationship
  lineage rather than database-only fields?
- Are update, delete/deactivate, validity filtering, ordering, async completion,
  and restart semantics stable under the frozen acceptance definitions?
- Should a later expansion replace Honcho, run Provider 5 alone, or stop at the
  existing empirical provider set? That is a scientific design decision, not
  an installation convenience decision.
- Which RQ4 claims require additional provider-observed unauthorized
  proposition evidence rather than synthetic challenge coverage?
