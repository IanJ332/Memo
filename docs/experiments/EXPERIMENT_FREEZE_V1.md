# Experiment Freeze v1

Experiment Freeze v1 fixes the upstream MemLife-NLIP protocol before the first three-provider batch. Its canonical machine-readable form is `experiments/freeze/experiment-freeze-v1.json`. Phase 06A calibrates measurement and freezes protocol; it does not report comparative provider results.

## Research Questions

- **RQ1:** Across heterogeneous memory providers, how reliably do supersession, revocation/invalidation, deletion, and restart/reconstruction converge to intended authority across source and derived surfaces?
- **RQ2:** When a lifecycle transition leaves operational influence, which surface or propagation edge causes residual or resurrected state, and under which reconstruction or re-derivation event does it appear?
- **RQ3:** For lifecycle failures exposing the same unauthorized context, how much does downstream model choice change stale-memory-driven unsafe-decision probability? RQ3 is subordinate and runs only on frozen residual contexts.
- **RQ4:** Can a provider-independent pre-LLM mediator enforce authority using lifecycle state and directly observed provenance while retaining history for audit?

There is no separate RQ5. F1 through F6 are the causal evaluation taxonomy.

## Provider Set

The closed set is Mem0 2.2.1, Hindsight 0.10.1, and OpenViking 0.4.22. A fourth provider is out of scope.

## Why Three Providers Are Sufficient

The set intentionally spans three architectures: a conventional vector/history baseline (Mem0), an explicit source/observation/derived-state architecture and lifecycle negative control (Hindsight), and a session/archive system with asynchronous extraction, `memory_diff`, and one-to-many memory URIs (OpenViking). Phase 06 evaluates those contrasts rather than expanding breadth.

## Provider Versions and Configurations

| Provider | Frozen storage configuration | Provider-internal model | Tracked configuration hash |
|---|---|---|---|
| Mem0 2.2.1 | `infer=False`; `sentence-transformers/paraphrase-MiniLM-L3-v2`; sentence-transformers 6.1.0; local on-disk Qdrant; telemetry disabled | none | `23c068e16db7d4bb90aad7755b997d5a4104c433a4a0083ef43b3506680ff2e8` |
| Hindsight 0.10.1 | isolated HTTP service; PostgreSQL/pgvector; `intfloat/multilingual-e5-small`, 384 dimensions, ONNX/CPU; RRF | `gpt-oss-120b`, temperature 0 | `baca300bdce174d8cb2d00fa576df73d0cf5c4f9230aed370d2767bd35f4d73d` |
| OpenViking 0.4.22 | isolated HTTP service; local `bge-small-zh-v1.5-f16`, 512 dimensions, CPU llama-cpp-python; direct find; `memory_diff.json` | `gpt-oss-120b`, temperature 0 | `ad1216520de78aa6dd6fe0c34393e3830b05b035aa7dda367d92725dafe53258` |

Hashes come only from tracked Phase 02B, Phase 04, and Phase 05 evidence. Phase 06B must record actual runtime hashes and fail before experiment execution on incompatibility.

## Capability Matrix

| Scenario | Mem0 | Hindsight | OpenViking |
|---|---|---|---|
| S0 baseline | SUPPORTED | SUPPORTED | SUPPORTED |
| S1 supersession/update | SUPPORTED: same-ID update | SUPPORTED: same-ID curation | UNSUPPORTED |
| S2 hard delete | SUPPORTED | SUPPORTED: document-scoped | SUPPORTED: correlated URI deletion |
| S3 delete + restart | SUPPORTED | SUPPORTED | SUPPORTED |
| S4 delete + re-derive | UNSUPPORTED | SUPPORTED: consolidation | SUPPORTED: session extraction |
| S5 revoke/invalidate | UNSUPPORTED | SUPPORTED: invalidated state | UNSUPPORTED |

No cell remains `NEEDS_FROZEN_MAPPING`. Missing primitives are never emulated.

## Authority Ledger

Authority is experiment intent, not provider truth. Each logical source version records an event ID, logical fact ID, namespace, sequence, lifecycle state, authority boolean and reason, supersession links, and SHA-256 content identity. Retrieval rank, text recency, visibility, and semantic similarity never confer authority.

## Exact Visibility

The Phase 03 `CURRENT_ONLY`, `CURRENT_AND_STALE`, `STALE_ONLY`, `ABSENT`, `UNSUPPORTED`, and `ERROR` meanings remain unchanged. This channel uses exact string equality.

## Authority Exposure

The supplementary outcomes are `AUTHORITATIVE_ONLY`, `AUTHORITATIVE_AND_NONAUTHORITATIVE`, `NONAUTHORITATIVE_ONLY`, `NONE`, and `UNKNOWN_PROVENANCE`. Classification uses only experiment event/fact IDs, provider source or derived IDs, provider-exposed lineage, adapter-observed write correlation, and retrieval candidate identities.

## Why the Metrics Are Separate

A derived provider record may paraphrase a source. It can therefore be exactly `ABSENT` while its direct correlation is `AUTHORITATIVE_ONLY` or `NONAUTHORITATIVE_ONLY`. No embedding, fuzzy match, semantic judge, or LLM judge bridges the channels.

## Calibration

Three isolated reference runs preceded three isolated local Mem0 runs. The synthetic Alder v1 authority was replaced by v2. Reference produced `CURRENT_ONLY` and `AUTHORITATIVE_ONLY` in 3/3 runs, validating the oracle. Mem0 also produced those observations in 3/3 runs, but Mem0 behavior was not a pass assertion. The Mem0 operation was honestly recorded as `Memory.update(same UUID)`; no revoke was claimed. Hosted and RQ3 calls were zero. Raw results are in `artifacts/calibration/mem0-calibration-v1.json`.

## Scenario Families

- **S0 BASELINE:** write, retrieve, inspect.
- **S1 SUPERSESSION_OR_UPDATE:** v1, native update/supersession, authority transition to v2, retrieve old/new, inspect.
- **S2 HARD_DELETE:** write, observe, native delete, retrieve, inspect.
- **S3 HARD_DELETE_RESTART:** S2 followed by reconstruction over the same persistent state, then retrieve and inspect.
- **S4 HARD_DELETE_REDERIVE:** produce derived state, delete correlated state, invoke a real native re-derivation trigger, retrieve, inspect.
- **S5 REVOKE_INVALIDATE:** write, real native revoke/invalidate, retrieve, inspect.

## Repetitions

Every supported provider/scenario cell runs exactly three repetitions. Supplemental repetitions require separate post-freeze documentation and do not alter the initial batch.

## Run IDs

The deterministic template is `freeze-v1__{provider}__{scenario}__r{repetition}`. Timestamps may be metadata but never primary identity.

## Namespace Isolation

The template is `memlife-freeze-v1-{provider}-{scenario}-r{repetition}`. Provider, scenario, and repetition state must not leak across namespaces.

## Run Order

The order is provider, then S0 through S5, then repetitions 1 through 3: Mem0, Hindsight, OpenViking. It is not randomized, which makes execution reproducible and state/cleanup auditing simpler.

## Restart Semantics

- Mem0 reconstructs a client over the same persistent Qdrant and SQLite history.
- Hindsight restarts the run-owned service/client over the same PostgreSQL/pgvector state.
- OpenViking restarts the run-owned service over the same workspace, vector index, archive, task, and cache state.

Restart never clears a namespace, reinstalls a provider, or creates a fresh database.

## Re-Derivation Semantics

Mem0 is unsupported. Hindsight submits native consolidation and polls its operation. OpenViking invokes the native session extraction endpoint and waits for task completion. Rewriting the same fact is not re-derivation.

## Quiescence

Mem0 completes synchronously when the adapter call returns. Hindsight requires its provider operation to report completed. OpenViking requires task status `completed`. Fixed sleep is never correctness evidence; failed operations are `ERROR`.

## Timeouts

Timeouts are centralized in the freeze JSON. Lifecycle and retrieval calls use 120 seconds. Hindsight startup/async/restart gates use 600 seconds based on Phase 04 validation; OpenViking startup/restart use 180 seconds and extraction uses 300 seconds; Mem0 startup uses 30 seconds and reconstruction uses 120 seconds. A timeout yields `BLOCKED` or `ERROR` according to whether infrastructure or an invoked operation prevented completion.

## Failure Taxonomy

`F1 SOURCE_LIFECYCLE`, `F2 DERIVED_STATE`, `F3 RETRIEVAL`, `F4 ENFORCEMENT`, `F5 MODEL`, `F6 TOOL_AUTHORIZATION`, and `UNKNOWN` are frozen. F1–F4 can apply in Phase 06B. F5 and F6 are `NOT_APPLICABLE` because no decision model or tool consequence runs.

## Residual Advancement

Root-cause work begins if non-authoritative exact content remains visible; correlated non-authoritative derived state is retrievable; deleted/revoked descendants remain; state reappears after restart or re-derivation; source and derived surfaces disagree; or repetitions disagree on authority exposure. Paraphrasing alone is not residual evidence.

## Root-Cause Advancement

Only residual cases inspect `SOURCE`, `DERIVED`, `SUMMARY`, `PROFILE`, `GRAPH`, `CACHE`, `VECTOR_INDEX`, `RETRIEVAL`, or `UNKNOWN`, tracing lifecycle event to source state to derived state to retrieval candidate. Clean cases are not exhaustively probed.

## RQ3 Advancement

RQ3 requires reproducible non-authoritative exposure, a frozen exact delivered context, sufficient known authority for defense comparison, and actual arrival at the model boundary. Storage-only inconsistencies do not advance.

## Provider-Internal Model Calls

Hindsight and OpenViking may use frozen `gpt-oss-120b` calls for normal provider extraction. Those are provider-internal calls, not RQ3. Mem0's frozen path uses no internal LLM. Phase 06B downstream decision calls are zero.

## Future RQ3 Model Set

The planning default is two residual contexts, three models (`llama-4-scout`, `gpt-oss-120b`, `muse-glimmer`), three repetitions, and three defenses, capped at 54 decision calls. Phase 06A executes none.

## D0 / D1 / D2

- **D0:** provider/default retrieval, no authority filtering, only safe serialization/sanitization.
- **D1:** pre-LLM enforcement using directly visible lifecycle or conflict state, without inferred provenance.
- **D2:** pre-LLM enforcement using lifecycle authority plus directly observed provenance/lineage; an LLM judge is not a security boundary.

## Trace Schema

The frozen trace covers experiment/run/repetition identity; lifecycle event and logical fact authority; provider source, derived, and parent IDs when exposed; surface; retrieval rank/score; SHA-256 content identity; correlation/provenance; filter decision/reason; delivered-context hash; downstream model decision; and tool action. Phase 06B filter/model/tool fields remain null or `NOT_APPLICABLE`; unavailable provider lineage is never fabricated.

## Aggregation

Each provider/scenario aggregate records supported repetitions, exact and authority outcome counts, residual and inconsistency flags, operation error count, median latency, and provenance-known fraction. Raw repetitions remain primary evidence.

## Inconsistency

Any repetition disagreement is preserved and labeled `INCONSISTENT`; it is never majority-voted away and automatically advances to root-cause analysis.

## Freeze SHA-256

The canonical freeze bytes hash to `0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b`. The hash is recorded in the Phase 06A manifest, not recursively inside the freeze file.

## Change-Control Policy

Provider version/configuration semantics, scenarios, repetition count, authority, normalization, residual rules, quiescence, timeouts, RQ3 model set, or D0/D1/D2 changes require Experiment Freeze v2. Typo-only documentation fixes do not. Freeze v1 must not change silently after Phase 06B begins.

## Phase 06B Entry Gate

`scripts/validate_experiment_freeze.py` validates the artifact and manifest hash. Its `--phase06b-preflight` mode additionally requires an exact expected commit and runtime-evidence JSON. It fails before Jetstream experiment execution on branch/commit, freeze hash, provider set/version/hash, repetition, or downstream-call mismatch. Phase 06B must also check the correct VM, `/dev/sdb`, persistent environments, and provider health before a run.

## Non-Claims

Phase 06A does not establish cross-provider failure rates, Hindsight superiority, OpenViking vulnerability, Mem0 insecurity, model susceptibility, defense effectiveness, or tool consequence rates. It establishes only a calibrated measurement pipeline and frozen experiment protocol.

