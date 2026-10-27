# Track B v1: source-level adversarial boundary findings

CONVERSATION: MEMO independent Track B source research, delegated by the root
agent. MODEL: GPT-6.1 Sol. EXECUTION TARGET: isolated local checkout
`/Users/ian/.codex/worktrees/memo-security-track-b/Memo`, accepted revision
`effda0c053bf03723b8089bc331e6b152ef9ab31`. JETSTREAM ACTION: NONE.

All results below concern those exact accepted source bytes. Only a new research
test and this report were added. No defense, frozen experiment, execution
package, historical source, test, raw evidence, or scientific denominator was
changed. No native provider operation, hosted request, protected action, real
recipient, browser, Docker, network, SSH, credential access, or Jetstream action
was performed. Synthetic content uses `synthetic-destination-*` strings.

## Result and interpretation

**Two deterministic authority-exposure scoring defects are VERIFIED.** One
trusts provider metadata as host event identity; the other loses evidence of
incomplete lineage. Neither is an observed protected-action bypass. A separate
Hindsight state-normalization hazard is OBSERVED for synthetic missing or
out-of-schema native states. The explicit lifecycle baseline's default TAG
visibility is implemented and documented; downstream exploitation is UNKNOWN.

The added test file is
[`tests/research/test_security_track_b_v1.py`](../../../tests/research/test_security_track_b_v1.py).
It imports actual pure repository helpers, rather than copying their algorithms.
The sole in-memory adapter run constructs a deterministic baseline observation;
Hindsight transport objects reject every request, and Mem0's static normalizer
is used without constructing any SDK/provider client. An autouse test guard
rejects Python socket creation, connection and DNS, subprocess creation,
`os.system`, fork and posix spawn; explicit negative controls exercise socket
and subprocess rejection. Reviewed module imports precede that per-test guard;
this is a focused offline test guard, not a new proof of full native runtime
containment.

Final command:

```text
/Users/ian/.codex/worktrees/424f/Memo/.venv/bin/python -m pytest -q -p no:cacheprovider tests/research/test_security_track_b_v1.py
........................                                                 [100%]
24 passed in 0.48s
```

An earlier 20-case run passed with an optional pytest-cache write warning from
the sandbox. Cache writing was disabled for the final run; no permission or
path workaround was attempted. A subsequent 21-case run added partial lineage
in the actual storage-payload builder. The final 24-case run adds the three
bounded scripted-message composition probes described below.

## Ranked finding B1 — provider metadata promoted to host event identity

**Status: VERIFIED at the pure normalization/scoring boundary. Priority: highest
of these findings for derived-result integrity; downstream severity unmeasured.**

Exact source/symbols at the accepted revision:

- `src/memlife/adapters/mem0.py:274–294`,
  `Mem0MemoryAdapter._normalized_record`: copies native `metadata` unchanged,
  apart from its revision/namespace handling and added observational keys.
- `src/memlife/runner/storage_batch.py:326–343`, `_correlated_event_ids`:
  metadata keys `experiment_event_id`, `source_event_id`, and
  `openviking_source_event_id` are accepted whenever their string value occurs
  in the independent authority ledger.
- `src/memlife/runner/storage_batch.py:346–392`, `_retrieval_payload`: any
  resulting source-event link becomes `provenance_status=KNOWN` and is described
  as direct provider/adapter identity.
- `src/memlife/models/authority.py:101–131`,
  `normalize_authority_exposure`: ledger authority of those links determines
  the result; text and scores are deliberately unused.

**Untrusted input:** a provider-visible metadata string naming an active host
event on an otherwise unrelated retrieved record. **Asset:** truthful attribution
and authority-exposure classifications, not a native tool permission.

**Causal mechanism and preconditions:** a caller/provider lets source writers
control these metadata keys, and the attacker knows a valid active event ID.
The direct-metadata path does not require the provider memory ID to occur in
`provider_events`, does not distinguish host-written from content-written keys,
and does not authenticate the claimed association. The synthetic record has
unrelated ID and stale bytes; its content hash differs from the ledger's current
source hash. A metadata string alone nevertheless yields the current event,
KNOWN provenance and AUTHORITATIVE_ONLY. The mismatch demonstrates identity
substitution; exact source-hash equality is not a general requirement for valid
derived records.

**Minimal reproduction:**
`test_provider_metadata_can_spoof_storage_exposure_authority`, parameterized for
`experiment_event_id` and `source_event_id`. Invoke the real Mem0 static
normalizer on a synthetic dictionary; pass its record to the real generic
storage payload builder with an empty provider-ID map and a one-entry current
host ledger. The generic correlation helper is exercised with the reference
adapter's pure trace hooks. No Mem0 SDK query, namespace ownership behavior or
native attacker write was tested.

**Secure expectation:** an unauthenticated provider metadata claim cannot alone
establish direct host-event identity. It remains unresolved/UNKNOWN unless a
separate trusted association attests it. **Observed outcome:**
AUTHORITATIVE_ONLY with KNOWN provenance for both keys.

**Alternatives/limits:** if an integration reserves these keys and only the host
can produce them, this particular attacker precondition does not hold. OpenViking
may supply its key through a host-maintained correlation path, which is different
from generic arbitrary source metadata. No historical record was shown to carry
forged metadata, and no historical result is reclassified here. This scorer
classifies lineage exposure, not semantic proposition authority.

**Remediation direction:** separate host-held ID associations from provider
metadata; restrict trusted reserved keys by adapter and provenance; quarantine
conflicting or unverifiable identity claims. Keep original evidence immutable;
any repaired score must be a versioned derived view. No repair implemented.

## Surface 5 addendum — scripted message serialization composition

**Status: VERIFIED synthetic composition of the B1 scoring mechanism. Actual
agent inference/delegation-runtime exploitability remains HYPOTHESIS.** This is
not a new independent vulnerability or an additional native observation.

The owner separately requested at most three small offline tests for this
surface after Track A was ordered stopped before admission. No grant was
activated and no Track A, native, remote or hosted action occurred here.

`_scripted_delegated_data` in the research test constructs an original
untrusted observation with explicit `role=observation-data`,
`origin=untrusted-provider`, and `taint=UNTRUSTED_DATA`. A literal scripted
summary prefixes its text and copies that origin/taint into metadata. A JSON
UTF-8 serialization/deserialization round trip produces summary data; a second
round trip produces delegated-message data carrying that summary. These labels
are data, never chat roles, authority channels, instructions to a model, real
messages, or a real delegation protocol.

The synthetic delegated data's native record fields are passed through the
actual `Mem0MemoryAdapter._normalized_record` static method and actual generic
storage-payload builder/scorer. No Mem0 instance or SDK is constructed. The
untrusted role/origin/taint survives into the normalized record's metadata.
The generic correlation helper nevertheless accepts the copied
`source_event_id=host-current`; its candidate output keeps the claimed host
link and describes a direct association, without carrying the message taint.

| Added bounded test | Secure expectation | Observed actual pure-path outcome |
| --- | --- | --- |
| `test_scripted_message_serialization_preserves_taint_but_claim_launders_scoring` | Summary and delegated-message data cannot authenticate a provider-controlled host-event claim. | With the claimed active event ID, the real scorer returns AUTHORITATIVE_ONLY despite retained UNTRUSTED_DATA at the normalized-record boundary. |
| `test_scripted_message_without_claim_does_not_acquire_host_correlation` | The same scripted composition without a claimed ID remains unresolved. | Empty source-event links and UNKNOWN_PROVENANCE; ordinary serialization or a delegated label alone does not create authority. |
| `test_scripted_delegated_summary_cannot_borrow_rq4_exact_byte_binding` | The newly prefixed summary bytes cannot reuse the exact current-proposition binding. | Real RQ4 returns QUARANTINE / UNRESOLVED_CONTENT_BINDING, empty delivered IDs, no summary bytes in framed context. |

**Preconditions/asset/mechanism:** same as B1: an attacker/provider can supply
claimed metadata and knows a valid current event ID; the affected asset is
correlation/scoring integrity. The scripted stages preserve the claim and
taint; they do not experimentally show that a model would copy the claim,
that a production summary/agent protocol accepts it, or that a protected action
uses the resulting score. **Alternative:** a real runtime that excludes reserved
metadata or authenticates it outside these data messages breaks the proposed
composition. The missing actual summary/delegation runtime is a deliberate
evidence boundary, not replaced by these scripts. Remediation remains the B1
trusted-association separation; no production repair was made.

## Derived-surface propagation coverage

Source-state revocation, an exact current proposition and stale lineage are
separate variables in the RQ4 fixture tests. Those pure tests do not exercise
provider-side regeneration, invalidation propagation, durable deletion or
restart. Existing LC12 handoff statements concern tested native base deletion
and reopen visibility; they do not establish forgetting on any of the derived
surfaces below. This Track B work generated zero new native evidence.

| Derived surface | What was actually inspected/tested here | Revocation/deletion propagation status |
| --- | --- | --- |
| Summary | `MemorySurface.SUMMARY` exists in `models/provenance.py`; the Surface 5 summary is literal scripted data only, then normalized through generic storage. | **NOT_EVALUATED** for a real summary producer, persisted summary, or native propagation. |
| Reflection | Hindsight observation normalization exposes a DERIVED surface and source IDs; pure tests inject observation dictionaries. No reflection invocation or producer runs. | **NOT_EVALUATED** for native reflection regeneration, revocation or deletion. |
| Graph | `MemorySurface.GRAPH` is a normalized enum; no native graph node/edge operation is executed. | **NOT_EVALUATED** for graph revocation, traversal, write-back descendants or persistence. |
| Cache | `MemorySurface.CACHE` is a normalized enum; no provider cache is read, populated, invalidated or reopened. | **NOT_EVALUATED** for cache invalidation, expiry or restart propagation. |
| Index | `MemorySurface.VECTOR_INDEX` is a normalized enum; no embedding/index operation or native retrieval is performed. CrossArch first-ten selection operates on supplied synthetic rows. | **NOT_EVALUATED** for native vector/index deletion, rank persistence or propagation. |

An in-memory test of the mediator's generic DERIVED contract is not evidence
for any provider surface's deletion or revocation semantics. Missing source
bytes, mappings, or actual native observations remain unknown; no base-surface
deletion result is promoted into a derived-surface forgetting claim.

## Ranked finding B2 — incomplete lineage becomes fully authoritative exposure

**Status: VERIFIED on two real pure paths. Priority: derived-result integrity.**

Exact source/symbols at the accepted revision:

- `src/memlife/runner/provenance.py:219–235`,
  `ProvenanceTraceRunner._retrieval_trace`: drops unmapped exposed source IDs
  from `source_event_ids` but correctly marks the candidate UNKNOWN when only
  part of the exposed lineage maps.
- `src/memlife/models/authority.py:117–128`,
  `normalize_authority_exposure`: ignores that UNKNOWN flag and classifies only
  the surviving event links. This contradicts its documented complete direct
  correlation requirement at lines 107–108.
- `src/memlife/runner/storage_batch.py:326–359`,
  `_correlated_event_ids` / `_retrieval_payload`: also discard unmapped exposed
  sources, then label any nonempty mapped subset KNOWN. Consequently, merely
  making the scorer reject UNKNOWN would not fix this producer path.

**Untrusted input:** an observation containing two exposed source IDs, one
mapped to a current authoritative event and one unresolved. **Asset:** accurate
uncertainty and mixed/noncurrent-lineage exposure measurement.

**Causal mechanism/preconditions:** incomplete provider-to-host ID coverage. This
can result from incomplete observable provenance without an attacker. An attacker
able to influence derived lineage could also exploit the same omission. The
candidate's source ID list contains `known-source` and `unresolved-source`.
Only `known-source` maps to `host-current`. The generic trace builder preserves
UNKNOWN but the scorer returns AUTHORITATIVE_ONLY. The storage payload builder
instead produces KNOWN and the same authoritative-only score.

**Minimal reproductions:**
`test_partial_lineage_unknown_is_misclassified_as_authoritative_by_real_scorer`
uses Hindsight's real record normalizer and per-record trace hooks plus the real
trace builder and exposure scorer;
`test_storage_payload_also_promotes_partial_lineage_to_known` exercises the
storage builder using the same Hindsight hooks and unresolved-source pair.
Every transport method is an explicit rejecting sentinel.

**Secure expectation:** UNKNOWN_PROVENANCE when any exposed source lacks direct
mapping. **Observed outcome:** AUTHORITATIVE_ONLY on both paths, with UNKNOWN
in the trace path and KNOWN in the storage path. The explicit-status baseline
also ALLOWs this candidate because its independent normalized record state is
ACTIVE; that baseline does not claim lineage enforcement.

**Alternatives/limits:** an unresolved source might ultimately prove current,
stale, or irrelevant. The experiment does not determine which; falsely resolving
uncertainty is the demonstrated defect. Complete trusted mapping would avoid
this case. No missing historical source is inferred and no historical score was
changed. This is a scorer/result defect, not observed model exposure or action.

**Remediation direction:** carry complete exposed-source coordinates plus
mapping completeness; enforce completeness in both producers and scorer. Do
not silently discard unresolved edges. Independent current-proposition evidence
may permit a current descendant despite stale ancestry, but that is a separate
RQ4 judgment, not proof that every exposed lineage source is authoritative.
The generic provenance flag also describes provider-internal causal evidence;
UNKNOWN alone is not proof that an independently matched direct source ID is
invalid. A blanket KNOWN-only rule would overblock legitimate direct identity
controls and still miss the storage builder's premature KNOWN. Preserve a
separate, explicit correlation-completeness fact. No repair implemented.

## Ranked finding B3 — missing/out-of-schema Hindsight state normalizes ACTIVE

**Status: OBSERVED synthetic normalization behavior; native exploitation
HYPOTHESIS/UNKNOWN. Priority: integration robustness, contingent on native input.**

Exact source/symbol: `src/memlife/adapters/hindsight.py:343–385`,
`HindsightMemoryAdapter._normalized_record`. `state=invalidated` is mapped to
REVOKED; an explicit `deleted=True` operation result maps to DELETED. Every other
native value, including an absent state defaulting to `valid`, maps to ACTIVE.
`LifecycleStatusFilter.inspect_candidates` at
`src/memlife/enforcement/filters.py:74–83` then ALLOWs ACTIVE.

**Untrusted input/asset:** native response lifecycle metadata; faithful lifecycle
normalization and baseline visibility. **Preconditions:** a malformed/new-schema
response or attacker-influenced provider response can omit state or supply
`revoked`, `deleted`, or another unfamiliar value. Those unfamiliar words are
synthetic schema challenges, not claims that pinned Hindsight emits them.

**Reproduction:** `test_hindsight_noninvalidated_state_defaults_to_active`, four
cases. Real normalization followed by the real baseline produces ACTIVE/ALLOW
for omitted, `revoked`, `deleted`, and `future-state`. The control `invalidated`
produces REVOKED. **Secure expectation:** absent/unrecognized lifecycle evidence
is rejected or explicitly represented as unresolved, unless a verified native
API contract guarantees that omission means valid. **Observed outcome:** ACTIVE.

**Alternatives/limits:** valid native schema may have only `valid` and
`invalidated`; query APIs may guarantee only valid records. Those guarantees
would make unexpected-state cases unreachable in the honest pinned service.
No service response, actual revoked-record retrieval, or native schema drift
was observed. `MemoryRecord.state` currently only admits lifecycle enum values,
so preserving uncertainty requires explicit adapter rejection or an intentional
new contract rather than an invented lifecycle value. RQ4 independently DENYs
revoked host authority even if the candidate hint is ACTIVE.

**Remediation direction:** validate native state enums and document/qualify any
safe omission rule; fail closed on unsupported shapes. No repair implemented.

## Implemented behavior and disproven hypotheses

| Probe | Actual source behavior and test | Status / boundary |
| --- | --- | --- |
| Revoked metadata lost to UNKNOWN becomes visible | LifecycleStatusFilter returns BLOCK for REVOKED, TAG for UNKNOWN; test explicitly mutates only the normalized synthetic candidate field. | OBSERVED baseline sensitivity; no provider transition demonstrated. |
| TAG is silently dropped | Disproven. `filters.py:42–49,63,81–83` documents default TAG delivery. `runner/provenance.py:296–313` delivers all non-BLOCK IDs; `models/provenance.py:242–248` requires exactly that set. Four ProvenanceStatus cases pass; configured unknown_action=BLOCK rejects. | VERIFIED implemented trace visibility. |
| This TAG runner already sends stale bytes to an LLM/tool | Not supported. Its only implemented consumer in `src` is trace construction and validation. `runner/provenance.py:310–313` explicitly writes model/tool NOT_RUN with absent decision/action records. | No protected dispatch; downstream effect UNKNOWN. |
| ACTIVE candidate hint overrides host revocation | Disproven by `test_independent_host_authority_recovers_revocation_despite_active_hint`. Real RQ4 returns DENY, empty delivered IDs. | VERIFIED deterministic mediation. |
| Forged raw bytes can reuse current canonical identity | Disproven by `test_changed_raw_bytes_cannot_borrow_current_host_binding`. Real RQ4 returns QUARANTINE / UNRESOLVED_CONTENT_BINDING and excludes stale bytes. This is the existing v2 fix, not a new defense. | VERIFIED pure byte-delivery boundary. |
| All stale ancestry must invalidate a current proposition | Disproven. Exact current bound proposition + linked SUPERSEDED ancestor => ALLOW; replacing ancestor state with REVOKED/DELETED => QUARANTINE. `rq4_policy.py:224–241,411–418` implements the distinction. | VERIFIED policy distinction; test-only fixture authorities. |
| Retrieval rank can turn RQ4 DENY into ALLOW | Disproven for exact fixture: rank 1 and rank 999 remain DENY. Policy evaluates every supplied candidate; rank is hashed evidence, not authority. | VERIFIED scoped negative control. |
| CrossArch first-ten selection enforces authority | Disproven. `crossarch.py:94–112` selects first ten nonempty native texts. Moving stale synthetic content from row 11 to row 1 changes selected exposure. `checkpoint` separately records raw and selected target exposure and adequacy (`115–144`). | VERIFIED selection sensitivity, explicit NOT_SENT; no authority or dispatch inference. |

`src/memlife/runner/rq4_policy.py:244–491` is an implemented deterministic
mediator with allow-only framed byte output. It is not just a score, but this
test invokes its pure API with synthetic trusted evidence; it does not bind an
actual model request or tool executor. `normalize_authority_exposure` is a pure
scorer, and LifecycleStatusFilter plus ProvenanceTraceRunner are a metadata
baseline and trace plumbing. CrossArch `select` is a candidate selector.

## Bounded next work supported by this evidence

An offline, versioned mapper-completeness/metadata-trust repair with independent
review is supported. Use the two demonstrated counterexamples as acceptance
tests, while preserving uncertain outcomes and original historical derivations.
A future native qualification would need separately authorized exact inputs and
evidence to establish whether these metadata/state shapes occur in a pinned
provider. New model calls, live provider effects and protected-action outcomes
remain UNKNOWN and are not authorized by this source research.
