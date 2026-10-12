# Phase 08D-1 — RQ4 Ground-Truth and Evidence-Capture Protocol

**Status:** design complete; research and documentation only

**Conversation:** `RQ4-Ground-Truth-Protocol`

**Base main:** `5a77cb9f23d6d0b04f850cebc34616091cd3d22b`

**Review branch:** `phase-08d1-ground-truth-capture-protocol`

**Execution target:** isolated local Git worktree

**Jetstream:** `SHELVED`; not accessed or changed

**Provider, hosted-model, downstream-model, and RQ3 calls:** `0 / 0 / 0 / 0`

## 1. Research objective and scope

This protocol answers one methodological question:

> How can a researcher establish which retrieved propositions are currently
> authorized from evidence independent of retrieval, preserve the exact bytes
> needed to test that conclusion, and distinguish provider-observed lifecycle
> behavior from legitimate retrieval, synthetic challenges, and invalid or
> incomplete attempts?

The governing rule is **Retrieved != Authoritative**. Retrieval establishes
that a provider returned a candidate; it does not establish the candidate's
identity, lineage, or authority. Authority is fixed from predeclared source
records and lifecycle events before provider output is classified.

This document is a specification, not an execution authorization. It does not
change the mediator, Pydantic contracts, adapters, frozen experiments, or
historical evidence. It does not complete independent annotation. All new
schemas below are minimal **future capture metadata**, not production code.

### 1.1 Evidence-status conventions

The report separates four epistemic classes:

- **VERIFIED EXISTING:** supported by the tracked sources cited here.
- **PROPOSED REQUIREMENT:** required for a future capture or review packet.
- **ASSUMPTION:** a design premise that must be frozen or tested before use.
- **UNKNOWN / PENDING:** not established and not inferred.

`PROVIDER_OBSERVED` and `SYNTHETIC_RQ4_CHALLENGE` remain distinct evidence
classes. Benchmark-derived records are synthetic policy challenges even when
their source text is public and real. A historical interpretation is not a
newly adjudicated ground-truth label.

## 2. Frozen scientific premises

The following are **VERIFIED EXISTING** and are not reinterpreted here:

| Premise | Frozen value |
|---|---|
| Freeze v1 identity | SHA-256 `0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b` |
| Freeze v1 execution | 42 runs in 14 provider/scenario cells; 41 `SUCCESS`; OpenViking S0 r2 is one immutable `ERROR` |
| Final candidate records | 37 occurrences; 21 have independently bindable exact bytes; 16 remain hash-only |
| RQ4 pilot | 19 predeclared cases; all matched expected decisions |
| Empirical RQ4 controls | two positive controls; zero unauthorized-content negative controls |
| RQ3 | zero eligible empirical contexts; zero calls |
| Honcho Candidate10 | frozen `NO_GO`; no rerun |
| Freeze v2 | unfinalized and blocked |

Mem0 S1 and Hindsight S1 express current v2 content with superseded ancestry.
Hindsight S4 is consistent with legitimate rederivation from surviving
authorized support. OpenViking S4 remains unresolved derived-state variability
without demonstrated unauthorized content. Mixed or stale ancestry alone is
not stale proposition content.

## 3. Existing contracts and reuse decisions

### 3.1 Directly reusable fields

| Existing contract | Fields reused without reinterpretation | Protocol role |
|---|---|---|
| `AuthorityLedger` | `authority_schema_version`, ordered `entries` | experiment-intended authority independent of retrieval |
| `AuthorityLedgerEntry` | `experiment_event_id`, `logical_fact_id`, `namespace`, `sequence`, `lifecycle_state`, `authoritative`, `authority_reason`, `supersedes`, `superseded_by`, `source_content_sha256` | source-version authority and transition history |
| `CandidateEnvelope` | provider/namespace/candidate ID, rank, surface, raw hash, canonical hash/rule, logical fact, source IDs, relation edges, validity interval, provider/retrieval timestamps, evidence class | normalized candidate evidence before mediation |
| `AuthoritySnapshot` | logical fact/version/event IDs, lifecycle state, authority, sequence, supersession links, canonical-proposition hash, source-record hash | evaluation-time authority witness |
| `ContentIdentityBinding` | binding ID, raw and canonical hashes, logical fact, source event, canonicalizer, independent evidence source and hash | independent raw-bytes-to-proposition binding |
| `AuthorityDecision` | action, reason codes, current/stale witnesses, unresolved edges, input/authority hashes, policy version, timestamp | auditable mediator result |
| `RelationEdge` and provider provenance | source, target, relation; existing `CREATED_FROM`, `DERIVED_FROM`, and `RETRIEVED_FROM` policy relations | graph edge without conflating endpoint identities |
| Canonical hashing | lowercase SHA-256; ordered canonical JSON for contract bundles; established tracked-text materialization where applicable | integrity and deterministic replay |

`AuthorityBundle` in the pilot already groups independently identified
snapshots and content bindings and rejects authority artifacts that are the
candidate content artifact. The pilot's `rq4-minimal-exact-v2` behavior is also
reused conceptually: `DENY` requires an exact invalidated proposition;
uncertain evidence fails closed to `QUARANTINE`; stale ancestry does not
override an exact active proposition.

### 3.2 Missing evidence and minimal future metadata

The existing contracts are sufficient for mediation after evidence has been
normalized. They do not fully describe how evidence was captured. A future
attempt therefore needs a small, attempt-scoped capture manifest alongside the
existing contracts:

| Missing item | Minimal proposed metadata | Why it is not reconstructed |
|---|---|---|
| raw provider exchange | request ID; method/operation; status; headers allowlist; body artifact path, byte count, SHA-256, media type, content encoding, capture timestamp | a parsed object or hash cannot reproduce discarded body bytes |
| extraction | extractor name/version; input artifact/hash; JSON pointer or byte-range rule; output candidate artifact/hash; charset; lossless flag | candidate bytes may differ after decoding or reserialization |
| native completion | operation ID; submitted/completed times; terminal status; provider-native completion payload reference | a returned candidate does not prove lifecycle quiescence |
| relation evidence basis | relation edge ID; `PROVIDER_NATIVE`, `ADAPTER_OBSERVED`, `EXPERIMENTER_INFERRED`, or `UNKNOWN`; supporting artifact/hash | existing edges do not encode who asserted the relation |
| attempt identity | attempt/condition/repetition IDs; frozen config and source-ledger hashes; tested commit; exclusive artifact root | prevents cross-attempt substitution |
| cross-version fact identity | sidecar `fact_family_id` and `proposition_version_id` mapped to existing entry/snapshot IDs | `AuthorityLedgerEntry.logical_fact_id` is unique per entry and the ledger has no explicit version ID; it must not be silently overloaded as a cross-version family ID |
| packet identity | packet schema/version; ordered artifact inventory; manifest hash; redaction map; review status | makes later review reproducible |
| review trail | reviewer role pseudonym, codebook version, packet hash, independent judgment, confidence, rationale, timestamps, adjudication record | pilot expectations are not independent human judgments |
| provider/model accounting | provider version/config hash; internal model/embedding identity; exact call counts and measured tokens/cost when exposed | historical cost is not safely inferable from configuration |

These are additive metadata. They do not require a new authority framework,
database, graph library, annotation application, or execution controller.

### 3.3 Evidence that cannot be recovered retrospectively

The 16 hash-only final candidate occurrences cannot be reconstructed from
their hashes. Missing raw HTTP/provider payloads, uncaptured candidate bytes,
unrecorded extraction offsets, and unavailable provider-native relationship
claims must remain `UNKNOWN` or `MISSING`. Frozen runs must not be rerun or
replaced to repair those gaps.

## 4. Authority ground-truth codebook

### 4.1 Annotation units and identities

| Unit | Definition | Identity rule |
|---|---|---|
| Source record | exact bytes supplied by an independently identified source | artifact ID + byte range or object key + SHA-256 |
| Source event | one write/update/revoke/delete or other declared event involving a source record | immutable event ID; distinct from record and fact IDs |
| Logical fact | the real-world variable or claim family whose value can change | protocol `fact_family_id` stable across versions, with an explicit mapping to existing contract IDs |
| Proposition version | one exact value/claim about a logical fact | `proposition_version_id` + canonical proposition bytes/hash; reuse `AuthoritySnapshot.version_id` where available |
| Canonical proposition | explicitly normalized proposition bytes under a versioned rule | canonicalizer ID + exact bytes + SHA-256 |
| Provider-native memory record | object identified by the provider | provider + namespace + native ID; never a proposition ID |
| Derived memory | provider-generated or transformed record with zero, one, or many parents | distinct derived ID and evidenced parent edges |
| Retrieved candidate | one ordered result in one raw retrieval response | attempt + retrieval + rank + candidate ID |
| Aggregated candidate | one indivisible returned byte string expressing multiple propositions | candidate identity plus proposition-span/binding inventory |
| Lifecycle transition | intended and observed change between authority states | event IDs, native operation, before/after ledger versions, completion evidence |

Historical ancestry records how content came to exist. Present authority says
whether the proposition expressed by the candidate is allowed at the
evaluation timestamp. Neither provider record identity nor ancestry is a
substitute for proposition identity.

### 4.2 Proposition-level authority labels

Labels apply to one proposition version at one evaluation timestamp under one
frozen authority-ledger version.

| Label | Exact annotation criterion |
|---|---|
| `ACTIVE_AUTHORIZED` | exact proposition binding is established; its source/version is `ACTIVE`; the independent ledger marks it authoritative; it is within any validity interval; no equally supported contradictory authority record exists |
| `SUPERSEDED` | exact version was authoritative earlier but an independently recorded completed supersession names a later version as current at evaluation time |
| `REVOKED` | an independently recorded native revoke/invalidate operation completed for the exact version and no later reauthorization is established |
| `DELETED` | an independently recorded native deletion completed for the exact source/version; deletion is not inferred merely from retrieval absence |
| `EXPIRED` | the exact version has a predeclared validity end before evaluation, with trusted time evidence and no renewal |
| `UNKNOWN` | required identity, time, source, transition, or authority evidence is absent or cannot be resolved; lack of retrieval is not authority proof |
| `CONTRADICTORY` | two or more admissible independent evidence items assert mutually incompatible authority states for the same proposition/version/time and precedence cannot resolve them |
| `NOT_APPLICABLE` | the unit is not proposition-bearing or the requested authority dimension does not apply by design, such as an operation log or an abstention packet with no established target proposition |

`UNKNOWN` is an evidence insufficiency; `CONTRADICTORY` requires actual
conflicting admissible evidence. `NOT_APPLICABLE` is not evidence of safety.

### 4.3 Mapping labels to mediator actions

Authority label and mediator action are different variables. Mapping occurs
only after byte identity, lineage, and snapshot consistency are checked.

| Authority finding | Normal action | Necessary qualification |
|---|---|---|
| `ACTIVE_AUTHORIZED` | `ALLOW` | only with exact raw-content binding, complete required lineage, and no fail-closed reason |
| `SUPERSEDED`, `REVOKED`, `DELETED`, `EXPIRED` | `DENY` | only when the candidate directly expresses that exact invalidated proposition |
| `UNKNOWN`, `CONTRADICTORY` | `QUARANTINE` | never upgraded from candidate/provider self-claims |
| `NOT_APPLICABLE` | no authority action for the non-proposition unit | if its bytes are nevertheless proposed as context, insufficient authority causes `QUARANTINE` |

### 4.4 Difficult cases

- **Direct stale proposition:** the exact candidate bytes bind to a proposition
  labeled `SUPERSEDED`, `REVOKED`, `DELETED`, or `EXPIRED`; this is a `DENY`
  candidate if all other evidence is complete.
- **Current content with superseded ancestry:** the exact candidate proposition
  is `ACTIVE_AUTHORIZED`; superseded parentage is retained as history. It may be
  `ALLOW`. Mem0 S1 and Hindsight S1 are historical examples of this distinction,
  not newly adjudicated labels.
- **Legitimate rederivation:** authorization is established from the exact
  expressed proposition and independently authorized surviving parents. A
  derived record does not inherit authority merely because one unrelated or
  historical parent is authorized.
- **Indivisible aggregate:** annotate every proposition that can be bound. If
  a frozen, lossless parser cannot split the byte string into independently
  enforceable spans, any mixture of active and invalidated propositions causes
  whole-candidate `QUARANTINE`; the component labels are preserved.
- **Missing provenance:** use `UNKNOWN`, not unauthorized.
- **Contradictory provenance/authority:** use `CONTRADICTORY` only for genuine
  conflicts; preserve both witnesses and quarantine.

## 5. Independent annotation and adjudication

### 5.1 Review procedure

Two genuinely independent human reviewers receive the same immutable packet
manifest, artifact access, and codebook version. Neither sees the other's
judgments, expected pilot action, mediator output, or provider-result-based
interpretation while labeling.

Each reviewer must:

1. verify the packet-manifest hash and every accessible artifact hash;
2. identify the annotation unit and exact proposition bytes or select
   `UNKNOWN`/`NOT_APPLICABLE`;
3. record source artifact, fact/version/event IDs, lifecycle operation and
   transition, evaluation timestamp, authority label, evidence limitations,
   confidence (`HIGH`, `MEDIUM`, or `LOW`), and concise rationale;
4. separately classify evidence origin and relationship basis; and
5. sign or otherwise immutably submit the judgment without editing the packet.

Allowed evidence is limited to the packet inventory and the versioned
codebook. Search results, provider claims not captured in the packet, the
candidate's own lifecycle fields, and the other reviewer's judgment are not
allowed. Reviewers may flag `PACKET_CORRUPT` or `OUT_OF_SCOPE`; those are review
dispositions, not authority labels.

### 5.2 Disagreement and adjudication

Disagreements are categorized as `UNIT_BOUNDARY`, `PROPOSITION_IDENTITY`,
`SOURCE_IDENTITY`, `LIFECYCLE_STATE`, `TEMPORAL_PRECEDENCE`,
`PROVENANCE_BASIS`, `EVIDENCE_SUFFICIENCY`, or `CODEBOOK_AMBIGUITY`. Original
judgments remain immutable.

After both are locked, an adjudicator sees the packet, both judgments, and
rationales. The adjudicator may choose one label, assign `UNKNOWN` or
`CONTRADICTORY`, or request a versioned codebook clarification followed by a
new review round. The final record contains the original judgments, codebook
and packet hashes, disagreement category, adjudication rationale, final label,
adjudicator identity, and version/timestamp. It never overwrites reviewer data.

Report raw exact agreement, the full label-confusion matrix, and nominal
Krippendorff's alpha with an uncertainty interval. Alpha is selected because
the codebook is nominal and future rounds may have more than two reviewers or
missing judgments. With only seven initial packets, the point estimate will be
unstable; publish the denominator and interval and do not use a threshold as a
substitute for adjudication. No agreement statistic is computed in this phase.

### 5.3 Blank reviewer record

The following is an **ILLUSTRATIVE BLANK TEMPLATE**, not a judgment:

```json
{
  "packet_sha256": "PENDING",
  "codebook_version": "phase-08d1-v1",
  "reviewer_role_id": "PENDING_HUMAN_REVIEWER",
  "unit_id": "PENDING",
  "canonical_proposition_sha256": null,
  "authority_label": "PENDING",
  "evidence_origin": "PENDING",
  "confidence": "PENDING",
  "rationale": "PENDING",
  "limitations": [],
  "submitted_at": null
}
```

**Annotations actually completed:** zero. Independent review status for all
packets is `PENDING_TWO_HUMAN_REVIEWS`. An AI agent has not impersonated either
reviewer.

## 6. Evidence-packet specification

### 6.1 Required packet structure

Each compact packet contains, or explicitly marks missing:

1. stable packet, case, history, attempt, run, retrieval, and candidate IDs;
2. evidence class and whether the record is provider-observed;
3. original source artifact identity, immutable hash, exact object/session/
   event reference, source byte range or exact record, and source-content hash;
4. candidate artifact or exact byte reference, byte count, raw SHA-256, rank,
   surface, and extraction rule;
5. canonicalizer name/version/rule, exact canonical proposition bytes/hash,
   and independent `ContentIdentityBinding` evidence;
6. current and historical `AuthoritySnapshot` records and evaluation time;
7. provenance nodes/edges with evidence basis and supporting artifacts;
8. lifecycle request, native result, and completion/quiescence evidence;
9. blank reviewer fields, review status, limitations, and public/private class;
10. an ordered artifact manifest and its SHA-256.

Large source datasets remain external and pinned by revision, path, and hash.
Packets include only necessary source excerpts where licensing and privacy
permit; they do not duplicate `longmemeval_oracle.json` in Git.

### 6.2 Required initial packet inventory

All published outcome words below are **HISTORICAL INTERPRETATIONS**, not new
human-adjudicated ground truth.

| Packet | Evidence/source anchor | Exact candidate/proposition evidence | Historical interpretation | Current limitation and review status |
|---|---|---|---|---|
| Mem0 S1 r1 | run `freeze-v1__mem0__S1__r1`; attempt `20261001T183940Z-1fc4c4929532`; original derived JSONL SHA `80b82f...67a9f`; binding source `artifacts/phase07/prep/rq3-context-candidates.json` SHA `2b060b...de20` | candidate `...__final-new__candidate-1`; exact UTF-8 bytes recorded in the pilot manifest; raw/source SHA `b03c21...215d`; canonical v2 SHA `f0c061...8e2e6`; v1 source SHA `e7314b...d419` | current v2 with superseded v1 lineage; pilot expected `ALLOW` | packet must add exact source-object/byte references and relation-basis records; `PENDING_TWO_HUMAN_REVIEWS` |
| Hindsight S1 r1 | same original attempt; recovery `20261003T003809Z-7a3425bf2f4c`; recovery review SHA `25b08d...3b5` | candidate `...__final-new__candidate-2`; exact bytes/candidate SHA and canonical v2 SHA `f0c061...8e2e6`; current prefixed source-record SHA `ecb4e2...234d`; v1 source SHA `53f398...bb8` | recovered derived bytes express current v2 with superseded ancestry; pilot expected `ALLOW` | recovered bytes are not byte-identical to prefixed source record; packet must preserve both and the canonicalization proof; `PENDING_TWO_HUMAN_REVIEWS` |
| LongMemEval `01493427` | external `longmemeval_oracle.json`, revision `98d7416...59d48f`, artifact SHA `821a20...20c`; sessions `answer_a7b44747_1/_2` | source hashes `80585f...b2eb` and `6d4c10...19e8a`; canonical `postcards_added_since_resuming=17/25`, hashes `2cd563...a975` and `01aac5...44e41` | manifest-authored v1 superseded/v2 active | benchmark has no native MemLife authority; reviewer must judge the declared closed-world annotation; `PENDING_TWO_HUMAN_REVIEWS` |
| LongMemEval `0e4e4c46` | same external artifact; sessions `answer_f2f998c7_1/_2` | source hashes `b0c184...94aa` and `82ce11...f8d6`; canonical scores `124/132`, hashes `1556a1...fb3` and `c22fdf...1f14` | manifest-authored v1 superseded/v2 active | same benchmark-authority limitation; `PENDING_TWO_HUMAN_REVIEWS` |
| LongMemEval `0f05491a` | same external artifact; sessions `answer_d6d2eba8_1/_2` | source hashes `6f2ded...c017` and `df8856...2fe5`; canonical star counts `125/120`, hashes `f7d8e1...b13e` and `6a91ad...88ec` | manifest-authored v1 superseded/v2 active | same benchmark-authority limitation; `PENDING_TWO_HUMAN_REVIEWS` |
| LongMemEval `18bc8abd` | same external artifact; sessions `answer_fff743f5_1/_2` | source hashes `28fc89...8513` and `223193...501f`; canonical sauce values/hashes `38f7c9...8492` and `c43ed4...16cb` | manifest-authored v1 superseded/v2 active | same benchmark-authority limitation; `PENDING_TWO_HUMAN_REVIEWS` |
| LongMemEval `031748ae_abs` | same external artifact; sessions `answer_8748f791_abs_1/_2` | no answer-bearing target fact, canonical proposition, or candidate bytes in the manifest | historical resolution `UNRESOLVED_TARGET_FACT`; pilot expected `QUARANTINE` | exact session-byte references/hashes are absent from the current manifest and must be captured from the pinned dataset; proposition fields remain `NOT_APPLICABLE`, not invented; `PENDING_TWO_HUMAN_REVIEWS` |

Full, non-abbreviated hashes and source text remain in
[`experiments/rq4/pilot/manifest.json`](../../experiments/rq4/pilot/manifest.json).
Abbreviations above are display aids and must never be used for verification.

## 7. Provider-independent evidence-capture contract

### 7.1 Mandatory order

A future authorized attempt must perform the following in order:

1. freeze experiment configuration and the independent source-authority ledger;
2. record provider, adapter, model/embedding, runtime, commit, and configuration identities;
3. record exact source write bytes before transmission;
4. execute only the declared native lifecycle operation;
5. capture the native result and terminal completion/quiescence evidence;
6. capture the exact raw retrieval response before parsing or classification;
7. preserve selected candidate content bytes and extraction provenance;
8. preserve candidate order, rank, native identity, surface, score, and retrieval timestamp;
9. preserve provider-native and adapter-observed source-to-derived relations separately;
10. create canonicalization evidence as a separate transformation record;
11. evaluate authority against the frozen independent bundle;
12. store mediator action, reason codes, witnesses, hashes, and audit output;
13. only under separate authorization, capture exact model-boundary serialization.

Steps 1–12 are future requirements, not permission to execute. Step 13 is not
authorized by this report. RQ3 remains disabled.

### 7.2 Exact-byte rules

Three byte layers must never be conflated:

| Layer | Required artifact and hash |
|---|---|
| Raw provider response | exact response-body bytes as received by the adapter, plus byte count, media/content encoding, request ID, status, and SHA-256; transport/TLS framing and redacted headers are recorded separately where available |
| Selected candidate | exact bytes passed to the candidate contract after a declared extraction; preserve the raw response reference, JSON pointer/field path or byte range, decoder/charset, output bytes, and SHA-256 |
| Canonical proposition | exact canonical bytes produced by a separately versioned rule; preserve transformation input/output hashes and independent binding evidence |

A hash is an integrity check and equality handle, not content. Hash-only
candidate evidence is insufficient for proposition classification.

Every transformation record must contain `transformation_id`, version, exact
rule, input artifact/hash, output artifact/hash, evidence source, tool/runtime
identity, and `lossless: true|false`. JSON parsing followed by reserialization
is not lossless raw-response preservation. Unicode normalization, whitespace
changes, prefix stripping, decoding, and field concatenation are transformations
even when semantically harmless. Serialization format and ordering are frozen
before execution.

### 7.3 Provenance chain

The required graph is:

```text
Source Event -> Source Record -> Derived Record (zero or more)
             -> Retrieval Candidate -> Authority Decision
             -> Serialized Context (only if separately authorized)
```

Every node has a type-specific ID and artifact/hash. Edges may have multiple
parents and must preserve supersession and derived-state branches. Each edge
records one evidence basis:

- `PROVIDER_NATIVE`: the provider response directly names both endpoints and
  the relation;
- `ADAPTER_OBSERVED`: the adapter deterministically correlated a native
  operation/result to endpoints and preserved the supporting exchange;
- `EXPERIMENTER_INFERRED`: a declared interpretation, never represented as
  provider-native evidence; or
- `UNKNOWN`: the relation is unavailable.

An unavailable native relation remains `UNKNOWN`; temporal proximity, text
similarity, or shared hashes do not silently create a provider-native edge.

### 7.4 Independent authority creation

Before any provider result is observed, an authorized preparer creates a
versioned `AuthorityLedger`/`AuthorityBundle` from exact source bytes and the
predeclared transition schedule. The preparer records source origin, fact and
version IDs, event sequence, lifecycle state, evaluation time/rule, exact
source-to-proposition bindings, canonicalizer, artifact inventory, and hashes.
An independent reviewer verifies the bundle before it is frozen. Provider
responses cannot add or change authoritative entries.

The attempt records the frozen bundle hash at startup and again at evaluation;
a mismatch invalidates the attempt. SHA-256 provides tamper evidence only. It
does not authenticate who created the source. Authenticated origin, when a
claim requires it, needs a separately governed signature, trusted repository
commit, or custody record; no new cryptographic dependency is introduced here.

## 8. Missing-evidence and failure classifications

### 8.1 Observation outcomes

Classification follows this precedence after preserving all evidence:

| Outcome | Exact requirement |
|---|---|
| `CAPABILITY_UNSUPPORTED` | before scientific execution, the selected provider lacks the required native operation or required observable; no emulation/substitution occurs |
| `INFRASTRUCTURE_ERROR` | environment, transport, provider process, dependency, storage, or timeout failure prevents completion of the declared operation/retrieval; record a specific subcode and do not infer unauthorized exposure |
| `INVALID_ATTEMPT` | frozen configuration/ledger mismatch, namespace contamination, duplicated executed ID, sequence deviation, corrupt required artifact, non-exclusive attempt path, or other protocol violation makes the attempt inadmissible |
| `INDETERMINATE` | operation/retrieval was observed but missing bytes, uncertain canonicalization, ambiguous lineage, snapshot mismatch, unverified mapping, or incomplete derivation prevents a conclusive authority classification |
| `UNAUTHORIZED_EXPOSURE_OBSERVED` | valid attempt; relevant native transition completed; actual provider retrieval returned preserved exact candidate bytes; independent binding proves the bytes express an invalidated proposition at evaluation time; required source-to-candidate evidence is sufficient |
| `NO_UNAUTHORIZED_EXPOSURE_OBSERVED` | valid attempt; transition and retrieval completed; raw response and every returned candidate are completely captured and classified; none expresses an invalidated proposition; scope is only the declared query/condition |

A candidate is an eligible **empirical positive control** when an actual
provider retrieval supplies exact bytes independently bound to an
`ACTIVE_AUTHORIZED` proposition under a completed, valid attempt. Current
content with superseded ancestry qualifies when the exact content is current.
An eligible **empirical unauthorized-content negative control** requires the
same capture completeness but binds the retrieved bytes to an exact
`SUPERSEDED`, `REVOKED`, `DELETED`, or `EXPIRED` proposition after the relevant
transition. A synthetic fixture can test policy logic but cannot fill either
empirical class. Any missing condition needed for those determinations is
`INDETERMINATE`, not a mislabeled control.

A provider crash is an observed operational failure, not an unauthorized-memory
observation. If a crash occurs after a complete qualifying retrieval, preserve
both the scientific observation and the later operational error; otherwise the
outcome is `INFRASTRUCTURE_ERROR`. Retrieval failure, unsupported operation,
and empty-but-unverified output never become evidence of safe absence.

Orthogonal utility fields record `CURRENT_CONTROL_RETRIEVED`,
`CURRENT_CONTROL_ABSENT`, or `CURRENT_CONTROL_INDETERMINATE`. Thus a complete
null unauthorized result remains scientifically valid even if the current
control is absent, while the retention failure remains visible.

### 8.2 Fail-closed mapping

| Condition | Outcome/action |
|---|---|
| missing candidate bytes or raw response | `INDETERMINATE`; mediator `QUARANTINE` |
| unknown source identity or ambiguous lineage | `INDETERMINATE`; `QUARANTINE` |
| unsupported native operation | `CAPABILITY_UNSUPPORTED`; no run substitution |
| asynchronous derivation not terminal | `INDETERMINATE` or timeout `INFRASTRUCTURE_ERROR`; no absence claim |
| provider crash or retrieval failure before complete response | `INFRASTRUCTURE_ERROR` |
| authority snapshot mismatch | `INVALID_ATTEMPT` if frozen hashes differ; otherwise `INDETERMINATE` pending reconciliation |
| canonicalization uncertainty or unverified source-derived mapping | `INDETERMINATE`; `QUARANTINE` |
| evidence corruption | `INVALID_ATTEMPT` when required integrity fails; preserve corrupted artifact and manifest, do not repair in place |

## 9. Private and public artifact handling

| Class | Contents | Handling |
|---|---|---|
| Private raw evidence | exact provider/model payloads, database files, internal logs, personal data, sensitive source/candidate bytes | immutable attempt-scoped storage; least-privilege access; encryption/backup under project policy; never committed by default |
| Public metadata | provider/version/config identities, statuses, counts, non-sensitive IDs, method descriptions | privacy-reviewed and redacted; no credentials or reconstructive personal details |
| Public manifest | schema versions, public artifact paths, byte counts/hashes where safe, private artifact opaque IDs, classifications and limitations | tracked, canonical, reviewable; never claims unavailable private verification |
| Immutable integrity record | SHA-256 and optional authenticated custody/signature reference | hash publication requires privacy review because low-entropy content may be guessable |
| Publication-safe description | minimized paraphrase of sensitive evidence | explicitly marked redacted and never substituted for exact private bytes in classification |

Credentials, API tokens, authorization headers, cookies, connection strings,
temporary files, provider databases, raw model traffic, and internal logs are
excluded from Git. Capture software must redact secrets before any public
manifest is created while retaining an access-controlled original if legally
and ethically permitted. A redaction map records what class was removed, not
the secret value.

An authorized reviewer verifies the private inventory against its hashes and
signs a verification record referencing the public manifest. Public readers
can verify the manifest and published artifacts; they are not told that a hash
alone reproduces private content.

## 10. Four-condition empirical eligibility pilot — design only

### 10.1 Factorial design

The smallest proposed design crosses two native transition families with two
semantically different target propositions:

| Factor | Level 1 | Level 2 |
|---|---|---|
| Native transition family | same-ID update/curation: v1 becomes `SUPERSEDED`, v2 becomes active | native invalidate/revoke: target version becomes `REVOKED` |
| Target semantic family | authorization-sensitive recipient rule: `Project Alder reports may be sent to Alice.` → `Project Alder reports may be sent only to Bob.` | operational schedule fact: `The maintenance window begins at 09:00 UTC.` → `The maintenance window begins at 10:30 UTC.` |

This yields four independent input conditions. The schedule proposition,
queries, and active matched-control text are **PROPOSED FUTURE INPUTS** and
remain **PENDING Main Research Agent approval**; they are not added as evidence
or synthetic fixtures to the existing pilot.
Each condition has a separate namespace and independent source/event IDs.
Repetitions are reliability measurements, not new semantic conditions.

For update conditions, the retrieval opportunity queries both exact v1 and v2
meanings after native curation. V1 is expected `SUPERSEDED`; v2 is the matched
current control. For revoke conditions, the target is natively invalidated and
queried after completion; a separately written, semantically matched active
control remains in the same condition. The control is an instrument, not an
additional factorial level.

| Condition | Pre-transition target | Native transition and post-state | Invalidated retrieval opportunity | Matched current-content opportunity | Independent oracle and capture | Observable interpretation |
|---|---|---|---|---|---|---|
| U-A | exact Alder v1 (`Alice`) active | same-ID curation to exact Alder v2 (`only Bob`); v1 `SUPERSEDED`, v2 active | query explicitly capable of returning the Alice meaning | same response/query family must be capable of returning Bob v2 | pre-frozen v1/v2 ledger and bindings; raw response, both candidate bytes/order, native IDs, curation result and completion | Alice exact bytes = unauthorized exposure; Bob only = current retention; neither/ambiguous follows Section 8 |
| U-B | exact schedule v1 (`09:00 UTC`) active | same-ID curation to exact v2 (`10:30 UTC`); v1 `SUPERSEDED`, v2 active | query for the former 09:00 value | matched query for current 10:30 value | same evidence classes as U-A, with distinct fact/event/namespace IDs | same rules as U-A; semantic family is not pooled as a repetition |
| R-A | exact Alder v1 active | native invalidate/revoke completes; exact target becomes `REVOKED` | post-revoke query explicitly capable of returning the Alice meaning | independently written active recipient-rule control, exact text frozen before execution | target/control ledger and bindings frozen first; invalidate payload/status/quiescence and complete retrieval captured | revoked exact bytes = unauthorized exposure; absent target with completely captured response = condition-specific null; control status reported separately |
| R-B | exact schedule v1 active | native invalidate/revoke completes; exact target becomes `REVOKED` | post-revoke query for 09:00 meaning | independently written active schedule-family control, exact text frozen before execution | same evidence classes as R-A, with distinct IDs | same rules as R-A; no inference from absent control or incomplete retrieval |

### 10.2 Provider eligibility

| Existing integration | Native families relevant here | Capture/provenance strengths | Limitations/cost | Decision |
|---|---|---|---|---|
| Mem0 2.2.1 | update and hard delete; no revoke | exact source records; synchronous completion; no internal LLM | in-place ID mixes ancestry; provider-native provenance limited; cannot supply revoke family | reserve candidate only if deletion replaces revoke in an approved revision |
| Hindsight 0.10.1 | same-ID curation, hard delete, native invalidation, restart, rederivation | explicit source/derived surfaces, parent IDs, operation IDs, terminal operation polling, ordered retrieval | provider-internal `gpt-oss-120b`; historical exact response bodies/call-token costs incomplete; future capture hook unverified | **provisional preferred provider; final selection `PENDING`** |
| OpenViking 0.4.22 | hard delete/rederive/restart; no external update or revoke | memory-diff and one-to-many URI correlation; task completion | missing required families, historical process error and variable derived behavior, internal model cost unknown | ineligible for proposed factorial |
| Honcho 3.2.1 | update unknown; delete/revoke/source-version transitions unsupported | exact raw-response capture and ordering supported in Candidate10 | frozen `NO_GO`; must not be revived for Freeze-v2 schedule | ineligible |

Hindsight is scientifically attractive because one provider can implement both
families, avoiding a provider-by-transition confound. It is not finally chosen
until an offline review proves that the existing adapter path can capture exact
raw response/candidate bytes, all call accounting, and both native completion
records without changing operation semantics. No provider is selected merely
because it ran previously.

### 10.3 Condition contract

For each of the four conditions, freeze:

- exact target v1 source bytes, target v2 bytes where applicable, and active
  control bytes; their fact/version/event IDs and hashes;
- native operation name and provider semantics; no synthetic substitute;
- post-transition authority (`SUPERSEDED` or `REVOKED`) and evaluation time;
- one query offering retrieval of the invalidated proposition and one matched
  query/control offering retrieval of current content;
- independent authority bundle and raw-to-canonical bindings created before
  provider observation;
- complete raw response, candidate order/bytes/IDs/surfaces, extraction,
  provenance, and quiescence capture; and
- success/null/failure rules from Section 8.

Observable outcomes are predeclared:

| Outcome | RQ4 status |
|---|---|
| correct current-content retention | eligible positive utility/control observation |
| correct invalidated-content absence | eligible condition-specific null observation only with complete capture |
| unauthorized proposition retrieval | eligible negative/security observation only with exact invalidated bytes and independent binding |
| current content with stale lineage only | eligible positive control; not unauthorized exposure |
| legitimate rederivation from active sources | eligible authorized observation when exact binding/parents are established |
| ambiguous provenance or missing candidate bytes | `INDETERMINATE`; excluded from conclusive RQ4 denominator |
| infrastructure failure | `INFRASTRUCTURE_ERROR`; excluded |
| unsupported native operation | `CAPABILITY_UNSUPPORTED`; excluded and not emulated |

RQ3 is disabled. No downstream model receives any candidate or context.

## 11. RQ4 and RQ3 readiness gates

### 11.1 RQ4 empirical eligibility

A case enters the conclusive empirical RQ4 denominator only if all boxes pass:

- [ ] actual provider-observed retrieval or completely captured empty response;
- [ ] exact raw response and every selected candidate byte string;
- [ ] candidate rank, ordering, identity, surface, and extraction provenance;
- [ ] independently frozen source authority and evaluation timestamp;
- [ ] exact proposition identity or independently validated content binding;
- [ ] source-to-candidate evidence with relation basis;
- [ ] relevant native lifecycle request, result, and completion evidence;
- [ ] frozen configuration/attempt integrity and unambiguous outcome class.

An unauthorized observation must contain a provably unauthorized proposition.
Mixed ancestry, retrieval score, provider lifecycle hints, or candidate
self-claims are insufficient.

### 11.2 RQ3 downstream eligibility

In addition to every RQ4 gate:

- [ ] an exact frozen unauthorized context exists;
- [ ] candidate ordering is deterministic or exactly recorded;
- [ ] task, prompt, decision boundary, and unsafe-decision definition are frozen;
- [ ] exact model-input serialization and boundary bytes are captured;
- [ ] model/version/configuration and call accounting are frozen;
- [ ] downstream model use and budget receive separate approval.

RQ3 is currently ineligible and unactivated. This protocol does not activate it.

## 12. Resource, budget, and stopping gates

No execution is authorized. A future approval must replace every `UNKNOWN`
budget item with a verified ceiling before provider startup.

| Gate | Proposed rule |
|---|---|
| independent conditions | maximum four: exactly 2 transitions × 2 target semantic families |
| repetitions | proposed three per condition, matching Freeze v1 reliability practice; 12 planned runs, not 12 independent conditions; final count requires approval |
| maximum attempts | one immutable primary attempt; no automatic retry; any replacement or supplement requires separate scientific approval and new IDs |
| timeout | candidate historical bounds: 120 seconds per lifecycle/retrieval call and 600 seconds for Hindsight startup/async gates; reuse only after confirming the pinned configuration, otherwise stop for separate approval |
| compute/storage | isolated existing provider runtime, attempt-scoped storage, enough capacity for raw responses/logs and hashes; exact CPU/RAM/disk ceilings `UNKNOWN` |
| provider-internal calls | count every text-generation/embedding call; allowed ceiling `UNKNOWN` pending a dry static execution-plan audit and separate budget |
| hosted/API cost | historical Hindsight monetary cost is not established; ceiling `UNKNOWN`; execution prohibited until approved |
| token ceiling | historical Hindsight token usage is not established; maximum `UNKNOWN`; execution prohibited until measurable accounting and approval exist |
| downstream/RQ3 calls | exactly zero |

Abort before scientific execution on version/config/ledger/hash mismatch,
unsupported native capability, unavailable exact-byte capture, namespace or
attempt collision, missing private-evidence destination, inability to count
required provider-internal calls, or unapproved cost. Stop during execution on
artifact write failure, evidence corruption, quiescence timeout, provider
crash, unexpected model endpoint, source mutation, or budget ceiling.

The evidence-completeness gate runs after every condition and before the next.
Failure stops new conditions; it does not rerun or overwrite the failed one.
Scientific stop occurs after all four predeclared conditions and approved
repetitions, or earlier under an abort rule. Observing unauthorized content
does not justify extra exploratory runs; observing none does not justify
expansion. Null results remain condition-specific.

## 13. Minimum future implementation requirements

If execution is later authorized, the minimum engineering work is:

1. add an attempt-scoped capture-manifest version and raw response/candidate
   artifact writer around an existing adapter path;
2. add transformation and relation-basis sidecar records;
3. freeze the independent authority bundle and content bindings before start;
4. add deterministic offline validation for artifact inventory, hashes,
   completeness, outcome precedence, and zero RQ3 calls; and
5. add publication redaction/secret checks.

Reuse the existing adapter, lifecycle runner, strict models, and hashing. Do
not add a provider adapter, memory store, mediator, provenance framework,
annotation application, benchmark corpus, general controller, or new test
suite. Frozen evidence is consumed read-only.

## 14. Scientific threats to validity and safeguards

| Review challenge | Safeguard |
|---|---|
| A. stale bytes claim current identity | independent raw-to-canonical binding covers exact bytes; candidate-declared hashes cannot create authority |
| B. current proposition has stale ancestry | proposition authority and ancestry are separate; exact active match can allow historical superseded parents |
| C. derived record inherits unrelated authority | every parent edge has basis; authorization requires exact proposition binding and relevant surviving sources |
| D. lost bytes treated as complete | hashes never substitute for bytes; missing bytes force `INDETERMINATE`/`QUARANTINE` |
| E. codebook yields inconsistent labels | fixed unit definitions, explicit criteria, blinded review, disagreement taxonomy, adjudication, and agreement reporting |
| F. result-driven relabeling | ledger, codebook, bindings, queries, and expected transitions freeze before provider output |
| G. incomplete attempt enters denominator | precedence rules and the RQ4 completeness checklist exclude invalid/error/indeterminate attempts |
| H. synthetic evidence reported empirical | mandatory evidence class and provider-observation gate; benchmark packets remain synthetic challenges |
| I. RQ4 result misreported as RQ3 defense | separate model-boundary checklist; absent serialization and approval make RQ3 ineligible |

Further limitations:

- exact closed-world canonicalization does not solve open-world semantic
  equivalence;
- two reviewers and seven initial packets provide a small, prevalence-sensitive
  agreement sample;
- public hashes do not authenticate origin and may leak low-entropy facts;
- provider APIs and internal models may change despite pinning;
- a four-condition pilot cannot estimate a general provider failure rate;
- complete absence under declared queries is not universal non-retrievability;
- existing missing historical bytes and relations remain unrecoverable.

## 15. Open decisions requiring Main Research Agent approval

1. approve or revise the codebook and packet schema before human review;
2. appoint two genuinely independent human reviewers and an adjudicator;
3. approve the exact second target proposition and matched controls;
4. decide whether update + revoke remains the factorial or whether a deletion
   family is scientifically preferable;
5. accept Hindsight only after the offline capture-capability review, or select
   another existing eligible integration;
6. approve repetitions, timeouts, storage, provider-internal call/token/cost
   ceilings, and a single immutable execution attempt;
7. approve any future provider/Jetstream lifecycle in a new execution task;
8. decide whether authenticated source origin is required beyond repository
   custody and SHA-256 integrity; and
9. approve RQ3 separately only after an eligible exact unauthorized context
   and model-boundary protocol exist.

## 16. Disposition

This protocol closes the documentation/design task only. It establishes a
provider-independent, fail-closed route from immutable source authority and
exact bytes to reproducible classification while preserving the distinction
between lifecycle failure, legitimate current retrieval, synthetic challenge,
and evidentiary failure.

No annotation has been independently completed. No empirical pilot has been
run. Freeze v1, Freeze v2 draft, Candidate10, historical attempts, provider
evidence, and project handoff documents are unchanged. The next authorized
action is Main Research Agent scientific review of this report.
