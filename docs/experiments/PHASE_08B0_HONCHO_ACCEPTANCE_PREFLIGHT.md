# Phase 08B-0 — Honcho Live-Acceptance Preflight

> **Status:** `LOCAL_PREFLIGHT_COMPLETE`
> **Execution:** `PREPARATION_ONLY`
> **Honcho contact:** `NONE`
> **Jetstream:** `SHELVED_NOT_USED`
> **Phase 08B-0 model calls:** downstream `0`; RQ3 `0`; provider-internal `0`

## Scientific boundary

Phase 08B-0 prepares a future Honcho live-acceptance run. It does not install
Honcho, import a newly installed Honcho SDK, start a service, call a provider,
access Jetstream, create provider-observed evidence, execute a lifecycle
scenario, activate RQ3, or finalize Experiment Freeze v2.

Honcho has **not** been accepted. Every native capability and every S0–S5
scenario remains `UNKNOWN`, with null current evidence artifact and SHA-256.
The sole future acceptance decision remains the deterministic result of
`ProviderAcceptanceRecord` and `honcho_acceptance_decision(...)`; this phase
does not assign `GO` or `NO_GO`.

## Model-execution accounting boundary

Phase 08B-0 made zero model calls of any kind. Downstream model execution and
RQ3 remain prohibited in Phase 08B-1: `downstream_model_execution=false`,
`downstream_model_calls=0`, `rq3_activated=false`, and `rq3_calls=0`.

Honcho's native asynchronous derivation or reasoning pipeline may require
provider-internal model inference. That inference is distinct from the
downstream agent/model boundary and never activates RQ3. If the pinned Honcho
configuration requires it, provider-internal model execution needs separate,
explicit Phase 08B-1 user authorization. The exact model, provider, and
configuration must be pinned, and every provider-internal call must be counted
and accounted for separately. No future provider-internal call count is
predeclared before live observation.

Provider-internal model inference is provider behavior, not an authority or
security judge. Its output cannot decide capability support, proposition
authority, lineage validity, scenario support, or any RQ3 result.

The exact gate is inherited unchanged from Phase 08A. Honcho entry requires:

- `CREATE_WRITE` and `RETRIEVAL`;
- `EXACT_PROVIDER_NATIVE_IDS` and `EXACT_RAW_RESPONSE_CAPTURE`;
- `PROVIDER_CONFIGURATION_PINNING` and
  `PROVIDER_VERSION_COMMIT_PINNING`;
- `DETERMINISTIC_OR_RECORDED_ORDERING`;
- `PROVENANCE_RELATIONSHIP_EDGES`; and
- `QUIESCENCE_ASYNC_COMPLETION_PROOF`.

The machine-readable source is
[`phase08b0-honcho-probe-plan.json`](../../experiments/acceptance/phase08b0-honcho-probe-plan.json).
It enumerates all 18 `AcceptanceCapability` values, not only the nine entry
requirements.

## Fail-closed adapter foundation

[`honcho.py`](../../src/memlife/adapters/honcho.py) reuses the existing
provider-independent lifecycle command and adapter shapes. It contains no
Honcho SDK import, HTTP transport, endpoint, credentials, or live operation.
Its configuration type fixes provider/network authorization to `false`.
Capability discovery, write, retrieval, update/supersede, delete/revoke,
inspection, restart, native rederivation, and quiescence calls all raise
`LiveProviderExecutionNotAuthorized` before any provider action.

The skeleton does not label an untested Honcho operation `UNSUPPORTED` and
does not emulate missing provider semantics. It also reports no provider
version until an authorized live probe observes and verifies one.

## Future capability probes

Each capability has one exact probe name, required-entry flag, expected
artifact list, evidence class, and separate rules for `SUPPORTED`,
`UNSUPPORTED`, `BLOCKED`, and `UNKNOWN`. The required entry probes are:

| Capability | Future probe |
| --- | --- |
| create/write | `honcho_capability_create_write_v1` |
| retrieval | `honcho_capability_retrieval_v1` |
| exact provider-native IDs | `honcho_capability_exact_provider_native_ids_v1` |
| exact raw-response capture | `honcho_capability_exact_raw_response_capture_v1` |
| provider configuration pinning | `honcho_capability_provider_configuration_pinning_v1` |
| provider version/commit pinning | `honcho_capability_provider_version_commit_pinning_v1` |
| deterministic or recorded ordering | `honcho_capability_deterministic_or_recorded_ordering_v1` |
| provenance/relationship edges | `honcho_capability_provenance_relationship_edges_v1` |
| quiescence/asynchronous completion proof | `honcho_capability_quiescence_async_completion_proof_v1` |

The plan also predeclares probes for update/supersede, hard delete,
restart/reconstruction, restart persistence, native
rederivation/consolidation, revoke/invalidate, source/version transitions,
temporal validity, and raw inspection. These probes characterize later
scenario support; they do not expand the frozen Honcho entry gate.

## Scenario evaluation

S0–S5 each have a separate future provider-observed probe. Native capability
support is a necessary contradiction check, never sufficient scenario
evidence. The Phase 08A rules remain unchanged:

| Scenario | Native capabilities required before scenario support is possible |
| --- | --- |
| S0 | create/write + retrieval |
| S1 | update/supersede + retrieval |
| S2 | hard delete + retrieval |
| S3 | hard delete + restart/reconstruction + restart persistence + retrieval |
| S4 | hard delete + native rederivation/consolidation + retrieval |
| S5 | revoke/invalidate + retrieval |

All six current scenario outcomes are `UNKNOWN`. No synthetic substitute is
permitted for an unsupported native operation.

## Raw evidence and identity contract

Future probes must apply this order:

```text
native raw response
  -> immutable raw artifact and SHA-256
  -> normalized adapter representation
  -> evidence-bound CapabilityAssessment
```

The local `capture_before_normalization(...)` seam verifies the raw byte count
and SHA-256 before invoking a normalizer. Normalized records keep
`provider_native_id`, `canonical_proposition_id`, and `logical_fact_id` as
separate fields. LLMs, embeddings, semantic similarity, and fuzzy equivalence
cannot establish support, identity, authority, lineage, or scenario outcomes.

## Quiescence policy

Elapsed sleep is never proof of completion. A future probe may establish
quiescence only from bounded observation of at least one predeclared signal:

- provider job/task completion;
- stable retrieval state across bounded repeated checks;
- an empty provider pending queue; or
- an explicit provider completion signal.

If no deterministic primitive can be observed, the quiescence capability is
classified `UNKNOWN`, `UNSUPPORTED`, or `BLOCKED` according to the evidence.
No semantic completion signal may be invented.

## Future attempt artifact contract

An authorized attempt will use exclusive creation under
`artifacts/phase08b/attempts/{attempt_id}`. Its required contract is:

- `environment-manifest.json`, `provider-config.json`, and
  `provider-version.json`;
- `acceptance-capabilities.json` and `scenario-capabilities.json`;
- `authority-ledger.jsonl`;
- exact `provider-raw-response.json` or an equivalent per-probe raw capture;
- `retrieval-candidates.json`, `lineage.json`, and `quiescence.json`;
- `latency.jsonl`, `run-ledger.json`, and `completion.json`; and
- `provider-acceptance-record.json`.

`model-boundary.json` is conditional on separate downstream-model
authorization and is not required or authorized here.

## Failure classification

Installation and provider-health failures are `BLOCKED`. Missing native IDs,
raw capture, verifiable provider version, recorded ordering, auditable
provenance edges, or deterministic completion proof prevent the corresponding
required capability from becoming `SUPPORTED`. Missing or inconclusive
evidence remains `UNKNOWN` unless an operational blocker is itself audited;
it is not silently reinterpreted as provider failure. A conclusive
`UNSUPPORTED` result requires provider-observed evidence.

## Future live manifest

[`phase-08b1-honcho-live-acceptance.json`](../../manifests/phase-08b1-honcho-live-acceptance.json)
is a non-executable predeclaration. It fixes Phase `08B-1`, provider `honcho`,
environment `JETSTREAM2`, initial/final Jetstream state `SHELVED`, zero
downstream model calls, zero RQ3 calls, no downstream model execution, and no
Freeze-v2 finalization. Provider-internal model execution is
`NOT_CURRENTLY_AUTHORIZED`; if required by the pinned Honcho configuration, it
requires separate Phase 08B-1 authorization, exact configuration pinning, and
separate call accounting. The manifest deliberately leaves the future
provider-internal call count null rather than inventing a value. Its
`required_base_commit` is the symbolic
`PHASE08B0_COMMITTED_HEAD`, which must be resolved to the reviewed commit only
before separately authorized live execution. This avoids an impossible
self-referential commit hash in the Phase 08B-0 commit.

## Result

Phase 08B-0 supplies implementation and test evidence only. Freeze v1 is
unchanged, Freeze v2 remains a non-final draft, Phase06B and Phase07 empirical
evidence are unchanged, Honcho remains not yet evaluated, RQ3 remains disabled,
and Jetstream remains shelved.
