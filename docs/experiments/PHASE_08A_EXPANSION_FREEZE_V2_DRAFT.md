# Phase 08A — Expansion and Freeze-v2 Draft Foundation

> **Status:** `LOCAL_CONTRACT_FOUNDATION_COMPLETE`
> **Execution:** `DESIGN_ONLY`
> **Jetstream:** `NOT_USED_IN_PHASE08A`
> **Hosted model calls:** `0`

## Scientific boundary

- **Freeze v1:** `IMMUTABLE`
- **Honcho:** `PROPOSED PROVIDER 4 — NOT YET LIVE-CALIBRATED`
- **RetainDB Server:** `PROPOSED PROVIDER 5 — PENDING ACCEPTANCE`
- **Graphiti:** `FALLBACK ONLY`
- **RQ3:** `NOT ACTIVATED`
- **RQ4:** `PRIMARY EXPANSION TARGET`

The published Phase 07 closure remains authoritative. In particular,
Hindsight S1 is `PROVENANCE_LINEAGE_RESIDUAL_CURRENT_CONTENT`: its canonical
proposition is current v2, not stale v1. Stale or superseded lineage is not
equivalent to stale or unauthorized proposition content.

The design artifact is
[`experiment-freeze-v2.draft.json`](../../experiments/freeze/experiment-freeze-v2.draft.json).
It is deliberately named, typed, and validated as a non-final draft. It does
not authorize provider execution and is not an immutable Experiment Freeze v2.

## Evidence and extension layers

| Layer | Phase 08A state | Rule |
| --- | --- | --- |
| Historical frozen evidence | Freeze v1, 3 providers, 42 runs | Referenced by exact SHA and never rerun or modified. |
| Proposed extension | Honcho plus one Provider 5 | Three repetitions per natively supported S0–S5 cell; at most 36 new runs. |
| Pending acceptance | Honcho and RetainDB/Graphiti | Capability values come from future observed evidence, not documentation prose. |
| Future live experiment | Not authorized | Unsupported native operations remain `UNSUPPORTED`; no synthetic substitute. |
| Future mediator evaluation | Contract foundation only | Authority firewall after retrieval and before serialization/model boundary. |

RetainDB and Graphiti are mutually exclusive Provider-5 choices. RetainDB
remains `PENDING_LIVE_ACCEPTANCE`. A future completed calibration yields
`NO_GO` if any required identity, transition, temporal-validity, retrieval,
restart-persistence, provenance, configuration, or version evidence is
unavailable or unstable; only then does Graphiti become the fallback candidate.
RetainDB `NO_GO` does not accept Graphiti. It only makes Graphiti eligible for
its own live acceptance; Graphiti becomes Provider 5 only after an independent
Graphiti `GO` result. At most one Provider-5 candidate can be active.

## Provider acceptance contract

Every future candidate provider must classify all required capabilities as
`SUPPORTED`, `UNSUPPORTED`, `UNKNOWN`, or `BLOCKED`. `SUPPORTED` requires
captured `PROVIDER_OBSERVED` evidence with an artifact identity. The contract
covers native lifecycle operations, raw inspection and retrieval, exact IDs,
source/version and temporal transitions, provenance edges, persistence,
quiescence, candidate ordering, raw response capture, and version/configuration
pinning.

Every declared acceptance result must equal the deterministic result derived
from its predeclared required-capability set. Incomplete calibration derives
`PENDING_LIVE_ACCEPTANCE`; a completed calibration derives `GO` only when all
required capabilities are `SUPPORTED` with adequate evidence, otherwise it
derives `NO_GO`. There is no manual override in Phase 08A. Conclusive
`UNSUPPORTED` and `BLOCKED` classifications also require deterministic
calibration or blocker artifacts; documentation prose is never sufficient.

The exact Honcho entry requirements are:

- create/write and retrieval;
- exact provider-native IDs and exact raw-response capture;
- configuration and version/commit pinning;
- deterministic or recorded retrieval ordering;
- provenance/relationship edges; and
- quiescence/asynchronous-completion proof.

These are entry-evidence requirements, not a claim that every S0–S5 operation
must be supported. Unsupported native lifecycle cells remain `UNSUPPORTED` and
receive no scheduled runs.

RetainDB's entry gate additionally requires create/write, exact raw-response
capture, and deterministic or recorded ordering, alongside its identity,
source/version transition, temporal-validity, retrieval, restart-persistence,
provenance, and pinning requirements. This is the minimum for deterministic
baseline execution and capture, not a requirement that every lifecycle
scenario be supported.

Graphiti's fallback gate is independently predeclared. In addition to baseline
write/retrieval, exact IDs and raw capture, ordering, provenance, quiescence,
and pinning, Graphiti must prove source/version transitions, temporal validity,
and restart persistence. These properties justify its scientific role as the
RetainDB substitute. It remains `NOT_ELIGIBLE` unless RetainDB first receives
`NO_GO`; eligibility is not acceptance.

No provider was contacted or installed in Phase 08A. Both native-capability
and provider/scenario matrices are therefore placeholders whose cells remain
`UNKNOWN` with null evidence. Each future cell is a strict evidence object.
`SUPPORTED` and `UNSUPPORTED` require `PROVIDER_OBSERVED` artifact identity;
`BLOCKED` requires an auditable blocker artifact; bare classification strings
fail closed.

A supported scenario is checked against deterministic minimum native
operations: S0 requires write/retrieval; S1 update/retrieval; S2 hard
delete/retrieval; S3 hard delete, restart/reconstruction, restart persistence,
and retrieval; S4 hard delete, native re-derivation, and retrieval; S5 native
revoke/invalidate and retrieval. This is one-way contradiction detection:
native support never infers scenario support, which still needs its own
provider-observed evidence.

## Normalized mediator contracts

`CandidateEnvelope` preserves provider, namespace, candidate rank/surface,
exact raw-byte SHA-256, optional fixture-canonical proposition SHA-256,
logical-fact identity, source IDs, structured relationship edges, lifecycle
and temporal hints, retrieval time, and mandatory evidence class.

`AuthoritySnapshot` independently represents logical fact/version identity,
source event, lifecycle authority, sequence and supersession links, canonical
proposition identity, and source-record identity.

`AuthorityDecision` provides the future deterministic audit shape:
`ALLOW`, `DENY`, or `QUARANTINE`, reason codes, current/stale witnesses,
unresolved edges, exact input and authority-snapshot hashes, policy version,
and decision time. Phase 08A does not implement or freeze the full D2 policy.

The identity layers remain separate:

1. exact provider-record byte identity;
2. deterministic fixture-canonical proposition-body identity;
3. logical fact/version identity.

Canonical proposition identity is absent unless a deterministic
fixture-defined canonicalization is declared. LLM equivalence and embedding
similarity are not authorization primitives; unresolved identity can be
quarantined.

## RQ3 and RQ4 gates

RQ3 is disabled. It can be considered only when all ten draft gates pass,
including `PROVIDER_OBSERVED` stale/revoked proposition content, independent
authority, exact proposition identity, repetition-policy reproduction, frozen
pre-LLM bytes, model-boundary SHA-256, frozen D0/D1/D2 semantics, unchanged
configuration, and separate authorization for model calls. Stale lineage by
itself is insufficient.

`SYNTHETIC_RQ4_CHALLENGE` inputs are permitted only for RQ4 stress testing.
They cannot count as empirical provider failures and cannot activate RQ3.

The future RQ4 mediator sits after provider retrieval and before context
serialization. The current foundation records the required input/output
contracts and deterministic hashes without implementing an LLM judge or final
policy engine. The validator locks the exact Phase 08A position, role, outputs,
and six future-policy invariants rather than checking only their presence.

## Future run evidence

Each future authorized run must emit environment and provider configuration,
authority ledger, exact provider raw response, normalized retrieval candidates,
lineage, mediator input/decision, latency, run ledger, and completion artifacts.
Raw record identity and canonical proposition identity remain separate.
`model-boundary.json` is required only when a downstream model call has been
separately authorized.

Future schedules are restricted to accepted Honcho plus exactly one accepted
Provider-5 choice. A scheduled `SUPPORTED` provider/scenario cell must contain
exactly repetitions 1, 2, and 3 with coordinate-derived run IDs. Unknown or
unsupported cells, synthetic substitutes, duplicate coordinates, historical
providers, and mixed RetainDB/Graphiti schedules fail closed. The Phase 08A
schedule remains empty.

For finalization, “completed capability matrix” means every scenario
classification consumed by the final schedule is evidence-bound and internally
consistent with native capability evidence. Provider entry `GO` alone is not
sufficient to finalize Freeze v2.

Validation is provided by `scripts/validate_phase08a.py` plus deterministic
unit coverage for model strictness, identity/evidence separation, acceptance
gates, fallback exclusivity, unsupported operations, no-rerun policy, RQ3
disablement, and artifact authorization.
