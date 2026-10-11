# RQ4 Evidence Coverage Audit

**Conversation:** `RQ4-Evidence-Coverage-Audit`

**Model:** GPT-5 (Codex)

**Base main SHA:** `d9fdcc5ac1f221471ae9ed1da92a4971becd79ab`

**Review branch:** `phase-08d0-evidence-coverage-audit`

**Execution target:** isolated local Git worktree; read-only scientific analysis except this report

**Jetstream action:** `SHELVED` — not accessed or changed

**Audit date:** 2026-10-11

## 1. Executive research finding

MemLife-NLIP contains substantially more implementation evidence than empirical
security-efficacy evidence. Freeze v1 contains 42 executions, but these are
three repetitions of only 14 provider/scenario cells. At a provider-independent
level they exercise six lifecycle families using five substantive source
propositions. Run IDs, namespaces, timestamps, and run-specific prefixes do not
create independent scientific inputs.

The RQ4 pilot establishes deterministic conformance of
`rq4-minimal-exact-v2`: 19/19 predeclared decisions, 0/11 non-`ALLOW` candidate
byte strings released, and 0/1 forged-content regression released. Its
empirical component is much narrower: two provider-observed positive controls,
zero provider-observed negative controls, and two excluded S4 observations
whose exact final candidate bytes were never preserved. The two eligible
observations are one semantic condition—current content with superseded
lineage—seen on two providers/surfaces. They support correct allowance of
current content; they do not test detection of an unauthorized proposition.

The proposed central deficiency is therefore confirmed:

> There is no provider-observed unauthorized proposition for which exact
> candidate bytes and independently supported authority ground truth are both
> available.

No frozen finding was reinterpreted to reach that conclusion. Mem0 S1 and
Hindsight S1 contain current-v2 content; Hindsight S4 is legitimate
rederivation; OpenViking S4 is unresolved derived-state variability without
demonstrated unauthorized exposure; and OpenViking S0 r2 remains a frozen
provider `ERROR`.

The minimum defensible next milestone is staged. First, complete a small
offline ground-truth and evidence-capture specification (Option B), with dual
review of the existing two empirical controls and five LongMemEval histories.
Only after that prerequisite is accepted should a separately authorized,
pre-registered empirical eligibility pilot (Option C) target four independent
conditions: two lifecycle-transition families crossed with two semantically
different propositions, using existing integrations and matched authorized and
unauthorized retrieval opportunities. Repetitions would measure execution
reliability, not add independent cases. A broad benchmark expansion (Option A)
is lower priority and should add only structurally new temporal, conflict, or
abstention histories.

## 2. Scope, sources, and evidence accounting rules

### 2.1 Authoritative internal sources

This audit used the repository state at the base SHA and the following tracked
sources:

- `docs/project/PROJECT_STATE.md`, `docs/project/MODEL_HANDOFF.md`,
  `docs/project/EXPERIMENT_LEDGER.md`, and
  `docs/project/DEBUGGING_LEDGER.md`;
- `docs/experiments/EXPERIMENT_FREEZE_V1.md`,
  `docs/experiments/PHASE_07_SCIENTIFIC_DECISIONS.md`,
  `docs/experiments/PHASE_08B1_HONCHO_SCIENTIFIC_CLOSEOUT.md`,
  `docs/experiments/PHASE_08C0_RESEARCH_DESIGN_RECONCILIATION.md`, and
  `docs/experiments/PHASE_08C1_RQ4_MINIMAL_PILOT.md`;
- `experiments/freeze/experiment-freeze-v1.json` (canonical SHA-256
  `0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b`)
  and `experiments/freeze/experiment-freeze-v2.draft.json`;
- `artifacts/phase06b/supplements/derived/20261002T000350Z-c272b34d2cc3/combined-derived-runs.jsonl`
  (42 rows; file SHA-256
  `d89bc4504aad4e3f25e04100915d78ef52b2f42593f61b9f5b12f490709dfd38`);
- `artifacts/phase07/prep/rq3-context-candidates.json` (SHA-256
  `2b060baf1aab8be57aa1863c36aa43c2212ed94ead7caad5a262be75ebb5de20`)
  and the linked Phase 07 decision/recovery records;
- `experiments/rq4/pilot/manifest.json` (SHA-256
  `50d5fba375a2c26b0c5a88e37d99e555ce2d934512167d74b2433a97c31a2d88`),
  `src/memlife/runner/rq4_policy.py`, `tests/unit/test_rq4_policy.py`, and
  `scripts/verify_rq4_pilot_provenance.py`.

No unpublished archive was opened. Public research was limited to primary
papers, canonical repositories, dataset cards, schemas, and small public
records. No external evaluation code or multi-gigabyte corpus was downloaded.

### 2.2 Counting units

The following units are deliberately not interchangeable:

| Unit | Counting rule | Freeze v1 value |
|---|---|---:|
| Experimental run | One executed run ID. A provider `ERROR` is still an execution observation. | 42 |
| Provider/scenario cell | One provider under one frozen lifecycle scenario, irrespective of repetition. | 14 |
| Independent test case | A distinct logical condition. Provider behavior is part of the condition when provider comparison is the claim. | 14 provider-conditioned cells |
| Lifecycle family | A provider-independent transition structure, S0–S5. | 6 |
| Substantive source proposition | Semantically distinct content after removing run/provider prefixes and IDs. | 5 |
| Repetition | Re-execution of the same provider/scenario/content template. | 3 per cell |
| Retrieved candidate | One ranked provider output record at one retrieval phase. It is an observation, not automatically a new test case. | 77 all phases; 37 final-phase records |

The five substantive propositions are Birch current content, Alder v1, Alder
v2, Larch v1, and Larch support. S0, S2, S3, and S5 reuse Birch. S1 uses the
same Alder v1→v2 update template across providers and repetitions. S4 uses the
same Larch deletion/support/rederivation template. A unique UUID, timestamp,
namespace, or textual run prefix is technical isolation, not semantic
independence.

Consequently, this report does not offer a single inflated “sample size.” For
execution reliability the denominator is 42. For cross-provider lifecycle
coverage it is 14 cells. For transition diversity it is six families. For
content diversity it is five propositions.

### 2.3 Evidence-status vocabulary

- `AVAILABLE`: the required evidence is directly tracked, exactly
  reproducible from tracked material with a verifying hash, or explicitly
  demonstrated by the frozen record.
- `PARTIAL`: some but not all repetitions, bytes, identities, or links are
  available.
- `MISSING`: the evidence required for the claim was not preserved or produced.
- `NOT_APPLICABLE`: the dimension is outside that condition by design.
- `UNVERIFIED`: a plausible artifact or relationship exists but this audit
  could not verify it from allowed sources.

Absence of a retrieved unauthorized candidate is not counted as a negative
RQ4 control. Likewise, a provider capability claim is not counted as an
observation.

## 3. Freeze v1 diversity and repetition analysis

### 3.1 Run and scenario distribution

| Provider | Supported scenario cells | Runs | Successful | Error |
|---|---|---:|---:|---:|
| Mem0 2.2.1 | S0, S1, S2, S3 | 12 | 12 | 0 |
| Hindsight 0.10.1 | S0–S5 | 18 | 18 | 0 |
| OpenViking | S0, S2, S3, S4 | 12 | 11 | 1 |
| **Total** | **14 cells** | **42** | **41** | **1** |

The scenario totals are S0=9, S1=6, S2=9, S3=9, S4=6, and S5=3.
Every supported cell has exactly three repetitions. Unsupported cells—Mem0
S4/S5 and OpenViking S1/S5—were not executions and are not inserted into the
denominator. Equivalently, r1=14, r2=14, and r3=14; the repetition index is
balanced but carries no new semantic input.

The frozen outcomes are:

- exact visibility: 32 `ABSENT`, 9 `CURRENT_ONLY`, 1 `ERROR`;
- authority exposure: 13 `AUTHORITATIVE_ONLY`, 6
  `AUTHORITATIVE_AND_NONAUTHORITATIVE`, and 23 `NONE`;
- run-level provenance: 19 `KNOWN`, 23 `NOT_APPLICABLE`;
- operation status: 41 `SUCCESS`, 1 frozen OpenViking S0 r2 `ERROR`.

`AUTHORITATIVE_AND_NONAUTHORITATIVE` is a lineage classification, not proof
that unauthorized content bytes were retrieved. Phase 07 established current
content in all six S1 runs.

### 3.2 Lifecycle operations and authority transitions

Across the 42 records there are 260 intended lifecycle events:

| Intended event | Count | Intended event | Count |
|---|---:|---|---:|
| `RESET_NAMESPACE` | 42 | `WRITE` | 48 |
| `UPDATE` | 6 | `DELETE` | 24 |
| `REVOKE` | 3 | `RESTART` | 9 |
| `CREATE_DERIVED_STATE` | 6 | `REDERIVE` | 6 |
| `QUERY` | 75 | `INSPECT` | 41 |

The input authority structures are:

| Scenario | Runs | Distinct transition structure | Reused semantic input |
|---|---:|---|---|
| S0 | 9 | active, no invalidation | Birch current content |
| S1 | 6 | v1 active→superseded; v2 active | Alder v1→v2 |
| S2 | 9 | active→deleted | Birch |
| S3 | 9 | active→deleted, then restart | Birch |
| S4 | 6 | v1 active→deleted; support active; rederive | Larch v1 + support |
| S5 | 3 | active→revoked | Birch |

These are six distinct lifecycle structures, not 42 distinct authority
transitions. Provider-native implementations differ and justify retaining the
14 provider/scenario cells as a second, finer granularity.

After removing run IDs and provider prefixes, query content also repeats: one
Birch query serves S0/S2/S3/S5, S1 has old-Alder and new-Alder queries, and S4
has one Larch query—four semantic query templates in total. Native operation
names differ by provider, but within a provider/scenario cell the same operation
sequence is repeated. Exact derived-text diversity is `UNKNOWN` for the
hash-only records and must not be inferred from distinct provider IDs.

### 3.3 Retrieval surfaces and candidate-byte availability

The 37 final-phase records occur in 19 runs; 23 runs have no final candidate.
Their surfaces are 16 `DERIVED`, 12 `SOURCE`, and 9 `UNKNOWN`. Across all
retrieval phases there are 77 records: 38 `DERIVED`, 24 `SOURCE`, and 15
`UNKNOWN`.

All 37 final records preserve a content SHA-256 and rank, but the combined
Phase 06B JSONL serializes raw candidate bytes for 0/37. Exact content is still
recoverable for a subset: 15 final records match a tracked source-content hash,
and six Hindsight S1 derived records were recovered and hash-verified in Phase
07. Thus exact bytes can be bound for 21/37 final record occurrences; 16/37
remain hash-only under the allowed tracked evidence. The RQ4 pilot consumes
only one Mem0 S1 and one Hindsight S1 provider observation, not all repeated
record occurrences.

The distinction matters: a hash proves equality to known bytes only when those
bytes are independently available. A hash by itself does not recover missing
candidate content.

### 3.4 Cell-level scientific classification

| Provider/cell | Final records | Surface | Frozen/Phase 07 interpretation |
|---|---:|---|---|
| Mem0 S0 | 3 | unknown | current-content positive observation |
| Mem0 S1 | 6 | unknown | current v2 with superseded lineage; RQ4 positive control |
| Mem0 S2 | 0 | — | absent after deletion |
| Mem0 S3 | 0 | — | absent after deletion and restart |
| Hindsight S0 | 6 | source + derived | current-content positive observation |
| Hindsight S1 | 12 | source + derived | current v2 derived proposition with superseded lineage; RQ4 positive control |
| Hindsight S2 | 0 | — | absent after deletion |
| Hindsight S3 | 0 | — | absent after deletion and restart |
| Hindsight S4 | 6 | source + derived | legitimate rederivation candidate; no unauthorized exposure shown |
| Hindsight S5 | 0 | — | absent after revocation |
| OpenViking S0 | 2 | derived | two authorized observations; r2 frozen `ERROR` |
| OpenViking S2 | 0 | — | absent after deletion |
| OpenViking S3 | 0 | — | absent after deletion and restart |
| OpenViking S4 | 2 | derived | derived-state variability; root cause unresolved; no unauthorized exposure shown |

## 4. RQ4 pilot evidence audit

### 4.1 Empirical evidence

The manifest investigates four empirical candidates but admits two:

| Candidate | Exact candidate bytes | Independent authority basis | RQ4 eligibility | Reason |
|---|---|---|---|---|
| Mem0 S1 r1 | available | tracked v1 supersession/v2 active ledger plus exact-content binding | eligible positive | current v2 in an in-place record with mixed lineage |
| Hindsight S1 r1 | available | tracked ledger, provider identity, and Phase 07 read-only recovery | eligible positive | derived record expresses current v2, not stale v1 |
| Hindsight S4 | missing | transition and attribution available | excluded | exact final candidate bytes unavailable |
| OpenViking S4 | missing | partial attribution; root cause unresolved | excluded | exact final candidate bytes unavailable |

Therefore:

- distinct provider-observed positive controls: **2 observations**, but **1
  semantic authority condition** across two providers/surfaces;
- provider-observed negative controls: **0**;
- eligible empirical observations with exact bytes: **2/2 admitted**, or **2/4
  investigated**;
- admitted observations with independently supported authority ground truth:
  **2/2**;
- empirical observations capable of conclusive RQ4 evaluation: **2 positive,
  0 negative**.

Observational eligibility and hypothesis relevance are different. Both controls
are eligible for testing correct allowance of current content. Neither is
relevant evidence for detecting an unauthorized proposition.

### 4.2 LongMemEval-derived evidence

The pilot pins the LongMemEval oracle artifact at dataset revision
`98d7416c24c778c2fee6e6f3006e7a073259d48f`, SHA-256
`821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c`.
It contains eight version cases from four update histories plus one abstention
case:

| Question ID | Original update structure | Derived cases | Independent history count |
|---|---|---:|---:|
| `01493427` | postcards 17→25 | current + stale | 1 |
| `0e4e4c46` | Ticket to Ride 124→132 | current + stale | 1 |
| `0f05491a` | Starbucks 125→120 | current + stale | 1 |
| `18bc8abd` | barbecue sauce brand update | current + stale | 1 |
| `031748ae_abs` | no answer-bearing target fact | quarantine | 1 |

The correct accounting is five logical histories, eight source versions in the
four update histories, four authority transitions, and nine policy cases. It
is not nine independent conversations. The benchmark supplies original
question, history, session/date structure, and answer-evidence markers. The
pilot adds lifecycle state, canonical proposition identity, candidate content,
and expected policy decision under
`rq4-longmemeval-explicit-annotation-v1`.

Those additions are useful but assumption-bearing. Chronological update evidence
does not natively assert MemLife authority, revocation, deletion, or a complete
source-to-derived graph. The annotations establish exact fixture identities
under a declared closed-world interpretation; they do not validate general
semantic canonicalization or provider behavior.

### 4.3 Hand-authored synthetic evidence

| Case | Decision | Distinct information contributed |
|---|---|---|
| exact current authority | `ALLOW` | canonical allow branch; overlaps LongMemEval current cases |
| exact stale version | `DENY` | superseded deny branch; overlaps LongMemEval stale cases |
| revoked source | `DENY` | distinct lifecycle state, same conclusive-invalidated decision family |
| deleted source | `DENY` | distinct lifecycle state, same conclusive-invalidated decision family |
| missing proposition identity | `QUARANTINE` | fail closed on missing binding |
| contradictory authority | `QUARANTINE` | fail closed on inconsistent authority |
| superseded ancestry/current content | `ALLOW` | prevents ancestry-only false rejection; overlaps the empirical semantic condition |
| mixed-authority aggregate | `QUARANTINE` | indivisible aggregate cannot be safely split |

All eight are useful regression fixtures, but they do not equal eight new
empirical conditions. At the policy-semantics level they represent about six
families: current allow; conclusive invalidation; missing identity;
contradictory authority; current content with stale ancestry; and indivisible
mixed authority. Revocation and deletion distinguish lifecycle semantics but
exercise the same high-level deny family. Three fixtures intentionally overlap
the empirical or LongMemEval branches.

Across all 19 pilot cases the distribution is 8 `ALLOW`, 7 `DENY`, and 4
`QUARANTINE`. The eight hand-authored cases contribute 2/3/3 respectively; the
nine LongMemEval-derived cases contribute 4/4/1; the two empirical controls are
both `ALLOW`. The forged-content test is a separate regression and not a 20th
pilot case.

### 4.4 Baseline validity

Pass-through produces 11 incorrect allows and no incorrect denies. This is a
meaningful sanity check that all predeclared non-`ALLOW` fixture bytes would
flow through an unmediated retrieval path. It is not a competitive security
baseline: its failure is definitional.

Naive ancestry-only filtering produces one incorrect allow and five incorrect
denies. Its useful comparison is narrower: it demonstrates that source ancestry
alone conflates current content with stale lineage and therefore rejects the
two empirical S1 positives plus overlapping synthetic cases. It also misses an
indivisible unsafe aggregate. These are expected consequences of the deliberately
weak rule, not evidence that the mediator outperforms a mature authority system.

Adding more weak baselines would increase table size without increasing
scientific information. A stronger baseline becomes worthwhile only if it has
a defensible authority model and the same exact evidence inputs.

## 5. Internal evidence coverage matrix

The matrix uses `A`=`AVAILABLE`, `P`=`PARTIAL`, `M`=`MISSING`,
`N`=`NOT_APPLICABLE`, and `U`=`UNVERIFIED`. “Unauthorized −” means an observed
unauthorized candidate with exact bytes, not successful absence.

### 5.1 Provider/scenario cells: identity and provenance

| Source / independent input family / authority condition | Native operation observed | Exact candidate bytes | Independent source identity | Canonical proposition identity | Provenance completeness | Authority transition evidence |
|---|---|---|---|---|---|---|
| Mem0 S0 / no invalidation / active | A | A | A | P | P (surface unknown) | N |
| Mem0 S1 / update / v1 superseded, v2 active | A | A | A | A | P (in-place mixed lineage) | A |
| Mem0 S2 / deletion / deleted | A | N | A | N | N | A |
| Mem0 S3 / deletion+restart / deleted | A | N | A | N | N | A |
| Hindsight S0 / no invalidation / active | A | M | A | P | A | N |
| Hindsight S1 / update / v1 superseded, v2 active | A | A | A | A | A | A |
| Hindsight S2 / deletion / deleted | A | N | A | N | N | A |
| Hindsight S3 / deletion+restart / deleted | A | N | A | N | N | A |
| Hindsight S4 / delete+rederive / active support, deleted v1 | A | M | A | P | A | A |
| Hindsight S5 / revocation / revoked | A | N | A | N | N | A |
| OpenViking S0 / no invalidation / active | P (2 success, 1 error) | M | P | M | P | N |
| OpenViking S2 / deletion / deleted | A | N | A | N | N | A |
| OpenViking S3 / deletion+restart / deleted | A | N | A | N | N | A |
| OpenViking S4 / delete+rederive / active support, deleted v1 | A | M | A | M | P | A |

Exact source bytes and source-event identities are available from deterministic
tracked inputs and authority ledgers for the 41 successful runs; the intended
input also exists for the failed run, but there is no successful provider
startup observation. Retrieval ordering is available for every serialized
candidate and empty result. Exact model-boundary bytes are `NOT_APPLICABLE`:
all Phase 06B rows have `delivered_context_sha256=null` and zero downstream
decision-model calls.

### 5.2 Provider/scenario cells: controls and evaluation eligibility

| Source / cell | Current + | Unauthorized − | Unresolved/quarantine | Temporal validity | Restart persistence | Derived reconstruction | RQ4 eligible | RQ3 eligible |
|---|---|---|---|---|---|---|---|---|
| Mem0 S0 | A | M | M | N | N | N | P (positive only, not selected) | N |
| Mem0 S1 | A | M | M | N | N | N | P (r1 positive selected) | N |
| Mem0 S2 | N | M | M | N | N | N | N | N |
| Mem0 S3 | N | M | M | N | A | N | N | N |
| Hindsight S0 | A | M | M | N | N | N | M (bytes incomplete) | N |
| Hindsight S1 | A | M | M | N | N | N | P (r1 positive selected) | N |
| Hindsight S2 | N | M | M | N | N | N | N | N |
| Hindsight S3 | N | M | M | N | A | N | N | N |
| Hindsight S4 | A | M | M | N | N | A | M (candidate bytes missing) | N |
| Hindsight S5 | N | M | M | N | N | N | N | N |
| OpenViking S0 | P | M | U (error is not a control) | N | N | N | M | N |
| OpenViking S2 | N | M | M | N | N | N | N | N |
| OpenViking S3 | N | M | M | N | A | N | N | N |
| OpenViking S4 | P | M | U (root cause unresolved) | N | N | P | M | N |

The S3 rows prove provider-state reconstruction/persistence for absence after
restart. S4 proves that a rederivation operation occurred, but OpenViking's
derived-state cause remains unresolved and neither S4 cell preserves exact
final bytes. Freeze v1 has sequence-based lifecycle transitions, not explicit
wall-clock validity intervals or expiry labels; temporal-validity coverage is
therefore `NOT_APPLICABLE`, not silently inferred.

### 5.3 RQ4 pilot strata

| Evidence stratum | Independent family count | Native operation | Exact bytes | Source ID | Proposition ID | Provenance | Transition | Current + | Unauthorized − | Quarantine | Temporal | RQ4 | RQ3 |
|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|
| Empirical S1 positives | 1 semantic / 2 providers | A | A | A | A | A | A | A | M | N | N | A | N |
| Empirical S4 exclusions | 2 provider cells | A | M | A | P | P | A | P | M | U | N | M | N |
| LongMemEval updates | 4 histories | N | A | A | P | P | P | A | A (derived fixture) | N | P | A | N |
| LongMemEval abstention | 1 history | N | N | A | M | P | U | N | N | A | P | A | N |
| Hand-authored conclusive cases | 5 cases / 2 broad families | N | A | P | A | A | A | A | A (synthetic) | N | N | A | N |
| Hand-authored fail-closed cases | 3 configurations | N | A | P | P | A | P | N | N | A | N | A | N |

“RQ4 eligible” in the benchmark and synthetic rows means eligible for
deterministic policy evaluation, not provider-efficacy estimation. There are
zero eligible downstream RQ3 contexts and zero RQ3 calls.

## 6. External ecosystem research

### 6.1 LongMemEval

The [canonical repository](https://github.com/xiaowu0162/LongMemEval),
[dataset card](https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned),
and [paper](https://arxiv.org/abs/2410.10813) provide 500 evaluation instances
covering information extraction, multi-session reasoning, temporal reasoning,
knowledge updates, and abstention. The schema includes question type, answer,
question date, session IDs/dates, session content, answer-session IDs, and
turn-level answer evidence. The oracle file is only the evidence-bearing
sessions. The repository is pinned here at
[`9e0b455`](https://github.com/xiaowu0162/LongMemEval/commit/9e0b455f4ef0e2ab8f2e582289761153549043fc)
and the reused dataset revision at
[`98d7416`](https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/tree/98d7416c24c778c2fee6e6f3006e7a073259d48f).
Code and data are MIT licensed.

Knowledge-update, temporal, and abstention records can broaden offline policy
challenges, but the benchmark does not natively label source authority,
deletion/revocation, or provider-derived lineage. Additional cases should be
selected by transition structure, not by swapping names or values in the same
update template.

### 6.2 MemoryAgentBench

The [repository](https://github.com/HUST-AI-HYZ/MemoryAgentBench),
[dataset](https://huggingface.co/datasets/ai-hyz/MemoryAgentBench), and
[paper](https://arxiv.org/abs/2507.05257) evaluate accurate retrieval, test-time
learning, long-range understanding, and conflict resolution. The public dataset
has 146 rows; the conflict-resolution split has eight rows and exposes
`context`, questions, acceptable answers, and metadata including sessions,
keypoints, previous events, dates, IDs, question types, and source. A small
public conflict record was inspected: it supplies conflicting factual content
and answer aliases but no independently authoritative source event or lifecycle
status. The MIT-licensed repository is pinned at
[`5380260`](https://github.com/HUST-AI-HYZ/MemoryAgentBench/commit/538026089d1a8a8eff05121d0db89b388f360eba)
and the dataset at
[`7ea0669`](https://huggingface.co/datasets/ai-hyz/MemoryAgentBench/tree/7ea066982b140a19337e17e60d45d4076e042faf).

Its conflict tasks measure answer correctness under contradictory context. They
do not by themselves identify which memory is authorized under a lifecycle
policy.

### 6.3 MemoryArena

The [ICML 2026 paper](https://proceedings.mlr.press/v306/he26am.html),
[project](https://memoryarena.github.io/),
[repository](https://github.com/ZexueHe/MemoryArena), and
[dataset](https://huggingface.co/datasets/ZexueHe/memoryarena) define
multi-session Memory-Agent-Environment loops with interdependent subtasks. The
public schema exposes task IDs, question lists, answers, and backgrounds across
five configurations. The dataset is CC BY 4.0; a repository-root code license
was not verified and remains `UNKNOWN`. The inspected revisions are
[`6cd9de1`](https://github.com/ZexueHe/MemoryArena/commit/6cd9de14b71915e39ac742a20dc33785e14b6aab)
and
[`da1a37c`](https://huggingface.co/datasets/ZexueHe/memoryarena/tree/da1a37c8b19280e18627ca01cf368195a5e1d92e).

Its useful contribution is methodology for dependency-aware downstream task
evaluation. The public schema does not establish independent revocation,
source-authority, or source-to-derived labels.

### 6.4 AMA-Bench

The [repository](https://github.com/AMA-Bench/AMA-Bench),
[dataset](https://huggingface.co/datasets/AMA-bench/AMA-bench), and
[paper](https://arxiv.org/abs/2602.22769) expose 208 long agent trajectories
with actions, observations, QA pairs, domains, success labels, turn counts, and
question types including state updating and causal reasoning. The code and
dataset are MIT licensed. The inspected revisions are
[`ddfd319`](https://github.com/AMA-Bench/AMA-Bench/commit/ddfd319e0be33424288c13806f1eafc63e625b59)
and
[`a577737`](https://huggingface.co/datasets/AMA-bench/AMA-bench/tree/a5777378066f53229a94557a7b192435cd027909).

Long trajectories may inspire repeated-decision and state-update methodology,
but their observations are not independent authority ledgers. Full evaluation
also introduces a large model or API-based agent and an LLM judge, which is
unnecessary for the present RQ4 evidence gap.

### 6.5 AgentDojo

The [repository](https://github.com/ethz-spylab/agentdojo) and
[paper](https://openreview.net/forum?id=m1YYAQjO3w) provide a dynamic environment
for indirect prompt-injection attacks and defenses, with separate utility and
security outcomes. The MIT-licensed revision inspected was
[`089ed46`](https://github.com/ethz-spylab/agentdojo/commit/089ed468cf3ed0322acc66b0211f26d9d90dbf60).

The transferable idea is experimental separation of benign-task utility,
attack opportunity, and security success under deterministic task state.
Tool-output prompt injection is not unauthorized-memory lifecycle exposure, so
AgentDojo records are not substitutable RQ4 cases. No agent or attack was run.

### 6.6 LoCoMo

The [repository](https://github.com/snap-research/locomo) and
[paper](https://arxiv.org/abs/2402.17753) expose ten long conversations with
session timestamps, speaker turns, dialogue IDs, event summaries, and QA
evidence dialogue IDs. The compact `data/locomo10.json` therefore offers more
precise source anchors and temporal structure than most candidates. The pinned
repository revision is
[`3eb6f2c`](https://github.com/snap-research/locomo/commit/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376).

The [official license](https://raw.githubusercontent.com/snap-research/locomo/main/LICENSE.txt)
is CC BY-NC 4.0. Non-commercial and attribution restrictions are material.
LoCoMo still lacks native MemLife authority, supersession, deletion, or
source-to-derived labels, so adaptation would require manual annotation. Its
annotation quality was not independently revalidated in this audit.

No additional benchmark was added: none found in the targeted search supplied
a clearly distinct, decision-relevant authority label unavailable from these
candidates.

## 7. Mandatory Reuse Audit

The revision pins below record what was inspected; they are not a request to
vendor or execute those projects.

| Candidate | Exact reusable artifact/schema | Availability and license | Maintenance/revision evidence | Lifecycle and authority compatibility | Transformation, compute, and API cost | Expected scientific value | Classification |
|---|---|---|---|---|---|---|---|
| LongMemEval | oracle histories; question/session/date/evidence schema | public code/data; MIT | repo `9e0b455`; dataset `98d7416`; no release status beyond the pinned public revisions was assumed | update/temporal/abstention compatible after annotation; no independent authority labels | oracle about 15.4 MB; low manual dual annotation; no model/API required; full cleaned corpus is multi-GB and unnecessary | high for structurally new offline cases, none for provider failure rate | `ADAPT` |
| MemoryAgentBench | conflict-resolution split; context/questions/answers/metadata | public code/data; MIT | repo `5380260`; dataset `7ea0669`; current public dataset inspected; no tagged release relied upon | conflict relevance, but no ordered authoritative source lifecycle | medium/high manual relabeling; 1.49 MB conflict parquet; no API for static inspection | moderate methodological value, weak direct RQ4 evidence | `REFERENCE_ONLY` |
| MemoryArena | multi-session tasks; IDs/questions/answers/backgrounds | public; dataset CC BY 4.0; code license `UNKNOWN` | repo `6cd9de1`; dataset `da1a37c`; project states active maintenance; no tagged release relied upon | task dependencies, no independent authority/revocation/provenance labels | static inspection low; full environments and model/API execution high | downstream RQ3 methodology after an eligible context exists | `REFERENCE_ONLY` |
| AMA-Bench | trajectories with action/observation and state-update QA | public; MIT | repo `ddfd319`; dataset `a577737`; public 2026 release artifacts | sequential state evidence, but observation is not authority provenance | static 50.5 MB dataset; full run requires substantial model/GPU or API and LLM judge | methodology for repeated decisions, little immediate RQ4 value | `REFERENCE_ONLY` |
| AgentDojo | task/attack/defense evaluation methodology | public code; MIT | repo `089ed46`; maintained release series and evolving API | separates utility/security, but prompt injection is a different threat mechanism | no transformation justified; full runs require tool/model calls | strong security-design reference, no reusable lifecycle observations | `REFERENCE_ONLY` |
| LoCoMo | `data/locomo10.json`; timestamps, dialogue IDs, QA evidence IDs | public; CC BY-NC 4.0 | repo `3eb6f2c`; no formal release pin verified | temporal/source anchors useful; authority and lifecycle labels absent | low storage (~2.68 MB) and manual annotation; no API needed for a small subset | moderate for temporal/source diversity subject to license | `ADAPT` |

There is no `DIRECT_REUSE` candidate. Openness alone is insufficient: every
candidate lacks at least one of independent authority ground truth, lifecycle
state, exact source-to-derived provenance, or a license suitable for
unqualified reuse. Public metadata supported this audit without installing any
framework or incurring model/API cost.

## 8. Scientific evidence gaps

### Gap 1 — no empirical unauthorized exact-byte observation

- **Claim prevented:** empirical unauthorized-memory detection efficacy,
  false-negative rate, provider failure prevalence, or recall of the mediator.
- **Already tracked?** No. Six S1 runs have mixed lineage but current v2
  content. S4 does not establish unauthorized content and lacks exact bytes.
- **Public benchmark?** It can provide synthetic unauthorized fixtures, not a
  provider observation.
- **Manual annotation?** It can improve ground truth but cannot manufacture a
  missing provider output.
- **New provider evidence?** Yes, if that empirical claim is pursued.
- **Downstream LLM needed?** No for RQ4; only later for RQ3 after an eligible
  exact context exists.
- **Minimum implementation/cost:** modify no mediator and add no provider;
  pre-register a small run plan using existing adapters, serialize every raw
  candidate before interpretation, and bind it to an independent ledger. A
  separate authorization is required. Cost is medium engineering plus bounded
  provider/internal-model expense.

### Gap 2 — incomplete raw candidate preservation

- **Claim prevented:** retrospective canonical identity, complete RQ4
  eligibility, and independent reanalysis for 16/37 final candidate records.
- **Already tracked?** Hashes, rank, and IDs are tracked; missing bytes cannot
  be recovered from hashes. Phase 07 closes only a subset.
- **Public benchmark/manual annotation?** Neither can recover historical
  provider bytes.
- **New evidence needed?** New capture is necessary for those empirical claim
  types; frozen runs must not be rerun or replaced.
- **Minimum cost:** an evidence-capture requirement in a future, separately
  authorized protocol; no new framework is necessary.

### Gap 3 — authority and canonicalization remain mostly experiment-authored

- **Claim prevented:** generalization from exact closed-world fixtures to
  independently adjudicated, semantically varied authority decisions.
- **Already tracked?** Strong for the two empirical positives; manual but
  explicit for five LongMemEval histories; missing or partial elsewhere.
- **Public benchmark?** LongMemEval and LoCoMo supply source anchors and time,
  not authority labels.
- **Manual annotation?** Yes. Dual, blinded annotation with adjudication and an
  explicit “unknown” option is sufficient for an offline improvement.
- **New provider or LLM needed?** No.
- **Minimum cost:** low/medium human review; no model/API cost.

### Gap 4 — limited independent lifecycle and content diversity

- **Claim prevented:** robustness across transition structures and semantic
  domains; any statistical provider failure-rate estimate.
- **Already tracked?** Six lifecycle families and five substantive
  propositions, repeated across 14 cells.
- **Public benchmark?** LongMemEval can supply update/temporal/abstention
  diversity; LoCoMo can supply temporal/source anchors. Neither supplies native
  deletion or revocation authority.
- **Manual annotation?** Sufficient for deterministic policy challenges, not
  provider behavior.
- **Minimum cost:** select a small, deduplicated set only after enumerating
  transition structures. The exact count is `UNKNOWN` until that sampling frame
  is audited; names/values alone must not count as diversity.

### Gap 5 — no empirical quarantine or temporal-validity control

- **Claim prevented:** evidence that uncertainty handling and explicit
  validity intervals work on observed provider outputs.
- **Already tracked?** Synthetic quarantine exists; Freeze v1 has ordered
  transitions but no expiry/validity intervals.
- **Public benchmark?** LongMemEval/LoCoMo can supply offline temporal cases.
- **Manual annotation?** Sufficient for offline policy conformance.
- **New provider evidence?** Required only for an empirical claim.
- **Minimum cost:** low offline annotation; medium if later included in a
  controlled provider pilot.

### Gap 6 — no eligible downstream RQ3 context

- **Claim prevented:** downstream decision-harm or mitigation claims.
- **Already tracked?** No; Phase 07 correctly records zero eligible contexts.
- **Benchmark/manual annotation?** They can support synthetic model tests but
  not convert them into provider-observed exposure.
- **New provider evidence?** A prerequisite for the intended empirical RQ3
  path.
- **Downstream LLM needed?** Eventually, but only after exact context,
  authority, ordering, and prompt-boundary evidence are frozen.
- **Minimum cost now:** zero; RQ3 should remain inactive.

## 9. Options A, B, and C

| Criterion | A — benchmark-derived challenges | B — authority/provenance annotations | C — controlled empirical provider experiment |
|---|---|---|---|
| Scientific contribution | broader deterministic branch and semantic coverage | stronger ground-truth validity and auditability | direct provider-behavior evidence; only option that can close Gap 1 |
| Novel evidence | synthetic/benchmark-derived transitions | adjudicated identities, authority states, evidence-quality labels | new provider-observed authorized or unauthorized candidates with raw bytes |
| Distinct input conditions | `UNKNOWN` until structural deduplication; select only new families | existing 1 empirical semantic condition + 5 benchmark histories receive stronger labels | proposed minimum 4: 2 transition families × 2 semantic propositions; repetitions separate |
| Evaluation validity | high for exact-fixture conformance; none for provider failure rate | improves construct validity; cannot recover missing bytes | high if capture and authority prerequisites are met; small denominator limits rate estimates |
| Engineering effort | low/medium; no new framework | low/medium, mostly scientific annotation and review | medium; reuse existing adapters and runner, add capture only if absent |
| Compute/API cost | negligible for static subsets | none beyond local validation | bounded provider/internal-model cost; downstream LLM unnecessary |
| Reproducibility | high with pinned records and annotation protocol | high with dual review and adjudication trail | medium/high with frozen inputs/configs; provider versioning remains a risk |
| Publication relevance | supports benchmark breadth but not efficacy | strong methods/audit contribution | highest relevance to empirical security claim if eligible outputs occur |
| Main dependency/blocker | defensible sampling frame and licensing | independent reviewers and explicit uncertainty policy | separate authorization, exact-byte capture, independent authority ledger, provider availability |

Option A alone risks making 19 cases into a larger conformance suite without
answering the principal empirical question. Option B is the cheapest
prerequisite and prevents a future experiment from again producing ineligible
hash-only observations. Option C is scientifically necessary only if the next
claim is empirical efficacy; it should not be framed as guaranteed production
of a provider failure. A null unauthorized-exposure result would still be a
valid observation for the predeclared conditions, not proof of universal
safety.

## 10. Recommended minimum next milestone

### Stage 1 — RQ4 ground-truth and capture protocol (recommended now)

Produce a small, reviewable specification—not a new framework—with:

1. dual independent authority/canonical-proposition annotation for the two
   empirical S1 controls and five existing LongMemEval histories;
2. exact source-event IDs, source bytes, candidate bytes, source-to-derived
   links, ordering, provider surface, and explicit `UNKNOWN` handling;
3. a predeclared rule that candidate bytes are serialized before scientific
   classification and that hashes never substitute for absent bytes;
4. a structural sampling rubric for any LongMemEval/LoCoMo addition, counting
   histories and transitions rather than version rows; and
5. an eligibility checklist separating RQ4 policy evaluation from RQ3
   model-boundary eligibility.

This stage needs no provider, Jetstream, experimental model, or new mediator.
It cannot recover historical bytes; it is a prerequisite, not a claim that the
central empirical gap is closed.

### Stage 2 — separately authorize a four-condition empirical eligibility pilot

If the Main Research Agent chooses an empirical efficacy claim, open a new
conversation and separately authorize a narrow Option C experiment. Use two
transition families crossed with two semantically different propositions,
with matched current and unauthorized retrieval opportunities. Reuse existing
provider integrations; do not revive Freeze v2's blocked Honcho-plus-Provider-5
schedule. Any repetitions are reliability checks. Predeclare stopping,
classification, null-result reporting, costs, and immutable attempt-scoped
evidence.

The exact providers and lifecycle families should be selected only after Stage
1 verifies that their native operations can preserve all required evidence.
This report does not authorize or implement Stage 1 or Stage 2.

## 11. Estimated scientific benefit versus engineering cost

| Milestone | Benefit | Cost | Evidence efficiency |
|---|---|---|---|
| Stage 1 protocol and adjudication | materially improves construct validity and prevents unusable future observations | low/medium human effort; negligible compute; no API | **highest immediate value per engineering unit** |
| Small structurally deduplicated Option A supplement | modest increase in temporal/conflict/abstention breadth | low/medium annotation; negligible compute | useful only after Stage 1, with diminishing returns |
| Four-condition Option C pilot | first opportunity for a conclusive empirical negative control; also yields matched positives/nulls | medium engineering and provider cost; separate authorization | **highest potential scientific value**, but prerequisite-dependent |
| Downstream RQ3 run | no value until an eligible exact unauthorized context exists | model/API cost and new validity concerns | zero current value; defer |

The recommended sequence maximizes evidence per unit effort by spending first
on ground-truth quality, then on the smallest empirical design capable of
producing the missing evidence class. It explicitly rejects provider-count,
case-count, and infrastructure growth as goals.

## 12. Limitations and unresolved questions

- This is a coverage audit, not a new empirical result. No provider was
  contacted and no historical experiment was rerun.
- Independence is a design judgment. The report exposes multiple granularities
  rather than treating 14 cells, six transitions, or five propositions as a
  universal effective sample size.
- The 21/37 exact-byte figure counts final record occurrences whose bytes can
  be bound through tracked source-hash equality or the Hindsight S1 recovery;
  it does not imply 21 independent observations.
- Public dataset schemas and small records were inspected, but full corpora
  were not downloaded. Counts or licenses that could not be verified from
  primary sources are marked `UNKNOWN`.
- MemoryArena's dataset license is verified as CC BY 4.0; a repository-root
  code license was not verified.
- LoCoMo's CC BY-NC 4.0 terms require a project-level reuse decision before
  adapted material is distributed or used beyond permitted scope.
- The number of genuinely new LongMemEval/LoCoMo histories is `UNKNOWN` until a
  structural deduplication pass is performed; this audit does not estimate it.
- A four-condition empirical pilot can materially improve evidence coverage
  but cannot estimate a general provider failure rate. Null exposure remains
  condition-specific.
- No model-boundary bytes exist for Freeze v1 and no downstream model execution
  occurred in the RQ4 pilot. RQ3 remains unactivated.
- Honcho 3.2.1 remains frozen `NO_GO`; Freeze v2 remains an unfinalized draft;
  neither was rerun, revised, or reinterpreted.
- OpenViking S0 r2 remains the immutable historical `ERROR` observation.

## Audit disposition

**Current task:** reproducible RQ4 evidence coverage assessment and next-stage
planning.

**Next authorized action:** Main Research Agent scientific review of this
report only.

**Publication state:** published by the enclosing Git commit on the review
branch; the immutable commit SHA belongs in the task handoff because a tracked
file cannot reliably contain its own commit hash. No main merge is authorized.
