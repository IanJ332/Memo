# R0 evidence and R2 native lifecycle decision — 2026-10-25

**R0 ACCEPTED / CLOSED. R2 PROPOSED / NOT EXECUTED. Offline decision only.**

## A. Current verified research state

Remote `IanJ332/Memo` main and the clean local starting checkout both resolve to
`90d4ccaa697ac2dc3b4d4c9e5f41b730aa9a17e6`. This document follows the
[status](RESEARCH_STATUS_20261024.md), [claims register](CLAIMS_REGISTER.md),
[roadmap v3](RESEARCH_ROADMAP_V3.md) and [R0 reproduction contract](REPRODUCE_R0.md).
It changes no accepted evidence, experiment source, registration or authority.

R1's registered scientific design remains conditionally accepted. Attempts
`R1EX-20261025-01` and `R1EX-20261025-02` are sealed: each has zero native
operations, zero model POSTs and 32 unobserved outcomes. Their startup/admission
failures are operational records, not scientific results or independent negative
replications. See [attempt 01](r1-live-20261025/REPORT.md),
[attempt 02](r1-live-20261025-02/REPORT.md) and the existing
[governance finding](R1_ADMISSION_GOVERNANCE_REPAIR_20261025.md). No approval
debugging, R1 retry or new live action is proposed here.

Public evidence identities used below:

- Cohort `TCEX-20261024-03`; scientific manifest SHA-256
  `563fdb5e5fe9b74afc15cff444ff282ba046dddc71a8b21e8e24e0c027751fc6`;
  original inventory `c0f34dbe797b2b4c4ffca5354ac4eb6fb448f45cd81a86fe212d16812e8ac22b`.
- [R0 reconciliation](evidence/cohort0-reconciliation.json), SHA-256
  `926eea90762510446e79c054325ffdca271139e62e54269fd5141bef0bc6a33c`;
  [audit explanation](AUDIT_RECONCILIATION_20261024.md).
- [Authentic F04 decision summary](evidence/f04-decision-summary.json), contract
  `COHORT0_AUTHENTIC_F04_DECISION_ONLY_V1`, preserving per-unit receipt hashes;
  [independent R0 review](evidence/independent-review.json).
- [Private archive index](../../manifests/research-evidence-20261024.json): original
  ZIP SHA-256 `27632cd157254b982d9b71e5981af66a137f6b68f69442b625c671d18f01a41e`.
  Raw evidence and excluded administrative inputs remain private. No archive was
  regenerated or replayed for this decision.

Two preserved private reports were read in the retained `3109/Memo` checkout;
their paths are relative to that checkout, not promised public links:

| Evidence key | Preserved report and verified report SHA-256 | Scope |
| --- | --- | --- |
| NQ | `docs/research/native-runtime-qualification/REPORT.md`; `312ba7743a29afadafbfa214db3a4fbef89fda94f748a3b5c37cc9c7fe54e87e` | October 22 real Mem0 qualification; 84 SDK calls, five journals, 571 inventoried files |
| A3 | `docs/research/native-mem0-a3-pilot/REPORT.md`; `a8ab35fecef6e4c9307d3b632b274470a1bb1212af3f54a94c61461b03555083` | Existing `DEV2-A3-01` matched native pilot; manifest SHA-256 `f485c8dabc175308971625d0564124098ca475688273247ea0b4d2091058bb17`; 54 SDK calls, four journals, 396 inventoried files |

These are authentic native operations on synthetic fixture content. Reading
reports/source is not a fresh raw-inventory audit or current runtime qualification.

## B. Manuscript evidence-to-claim matrix

SUPPORTED means the narrow statement in that row is established; PARTIAL marks
coverage of only part of the research question. Observations, calls and replayed
decisions are never counted as independent replications.

| RQ / claim | Exact evidence and type | Units and independence | Directly establishes | Does not establish | Status |
| --- | --- | --- | --- | --- | --- |
| RQ1: prompt-specified baseline proposal behavior | Cohort 0 response/accounting records; reconciliation and F04 per-unit summary; authentic model observations | 55 complete responses / 60 planned; 54 native proposals, one anomaly (034). 056 SEND_UNKNOWN; 057–060 not started. 55 are correlated response observations, not 55 independent experiments | All 54 evaluated native proposals matched the supplied current recipient/ACL under this baseline | Memory necessity, memory immunity, unauthorized execution or a population vulnerability rate | SUPPORTED |
| RQ1: conflict-associated reasoning usage | Reconciliation complete-pair/request-hash/case tables; authentic usage, offline recomputation | 27 complete pairs; 24 positive differences; nine complete case groups, eight positive means. 56 existing request bodies form 22 hash groups; 55 complete bodies form 21. No independent provider replication count is justified | A descriptive difference in server-reported reasoning-token accounting within these paired records | Reasoning content/intent, causal memory effect, independent provider superiority, confirmatory significance | PARTIAL |
| RQ1: removing task answer exposes stale-state influence | Registered [R1 protocol](NEXT_EXPERIMENT_PROTOCOL.md); prospective design | Eight planned shared-template blocks × four arms; zero observed blocks, no independent empirical units | A falsifiable interaction and missingness plan exists | Any observed memory-necessary effect; startup stops supply no observations | BLOCKED |
| RQ2: native persistence and mutation are observable | NQ Q1/Q2/Q3B/Q5/Q6; authentic native operations, synthetic fixtures | One qualification exercise plus distinct-process continuation; one update and one delete, four synthetic scopes. 84 calls are instrumentation events, not n=84 | Same-ID updated content survived reconstruction; deleted fourth ID absent from get/search after reopen; histories retained; scoped routes separated fixture records | Native revocation, complete forgetting, secure erasure, authentication, crash/concurrency safety or scientific authority-drift rate | SUPPORTED |
| RQ2: current and historical state can coexist in selected context | A3 literal candidate/selection receipts and closed-store snapshots; authentic native operations, synthetic fixture | One existing case, two matched physical stores, each initial/reopened; four processes and 54 calls, no independent case replication | CONTROL selected CURRENT; CONFLICT selected CURRENT then HISTORICAL_BRANCH, before/after reopen; IDs/content persisted | Model influence, mutation effect (this pilot used adds only), unauthorized proposal, derived-lineage propagation or actual model exposure | PARTIAL |
| RQ2: authority-content transition after native update/delete | Roadmap R2 and section D below; prospective design | Zero new R2 stores/transitions; planned two disposable trajectories, no empirical units | A bounded state/retrieval hypothesis can be tested without a model | Any new lifecycle-security result or cross-provider generalization | PLANNED |
| RQ2: transitive derived-memory revocation | Roadmap unsupported-capability boundary; prospective only | Zero qualifying lineage/revocation trials | Existing mode lacks qualified evidence for this claim | That deleting/updating a source invalidates every derived fact, cache, profile, graph or history | BLOCKED |
| RQ3: legitimate proposal preservation at decision layer | F04 summary and original per-unit evaluation receipts; offline replay of authentic proposals | 55 enrolled complete captures; 54 applicable decisions, 54 ALLOW / 0 DENY; 034 NOT_APPLICABLE. Same correlated cohort; zero new independent model units | Unchanged public authorization function permits these 54 correct-recipient proposals (policy revision 2) | Unauthorized-proposal denial effectiveness; 54 ALLOW is not defense effectiveness | SUPPORTED |
| RQ3: defense/enforcement comparisons | F04 coverage fields; roadmap R3; no authentic comparison evaluation | Zero unauthorized authentic challenges evaluated; no OFF/hardened comparison trials or protected dispatches | Coverage boundary only; legacy 54 BLOCKED enrollments remain separate | Atomic dispatch, TOCTOU, ProvenanceBridge, protected-action safety or ECMA-430/434 conformance | NOT_EVALUATED |
| RQ1–3: offline control tests | R0 reproduction/review, 22 focused source/statistics/negative controls; synthetic tests | Zero independent scientific units; test count is not experiment n | Checked source/statistical/admission behavior under fixtures | New native/model observations or security efficacy | SUPPORTED |

Native state, retrieved candidates, selected context, model proposals, host
decisions and protected actions require separate evidence. A3 selection was a
literal extraction receipt, not a model request; Cohort 0 had authentic responses.
Missing outcomes remain UNKNOWN, never inferred as abstention, denial or failure.

## C. Manuscript position and main scientific gaps

**Verdict: a manuscript-ready descriptive baseline and evidence-methods account;
the central causal lifecycle/enforcement thesis remains incomplete.** Empirical
findings ready for narrowly worded reporting are the captured baseline proposal
outcomes, the one native-format anomaly, verified evidence/accounting identities,
legitimate-request preservation in authentic decision replay, and the qualified
native persistence/selection observations above. NQ and A3 are supporting
development evidence, not new R0 scientific replications.

The 24/27 reasoning differences, 8/9 case means and provider-specific summaries
require explicit descriptive qualification. Byte-identical prompts, shared cases,
one model/configuration and repeated deterministic calls prevent naive causal or
independent-sample interpretation. Server reasoning tokens do not reveal intent.
The active task supplied the answer; 034 is not a demonstrated parser bypass.
Incomplete 056 has unknown usage and no replacement; complete-response analyses
must disclose this missingness and the four unstarted units.

R1 observations are needed for the registered memory-necessity interaction,
resolvability/abstention and unauthorized native-proposal outcomes. R2 needs
fresh transition evidence linking authority-related content, durable IDs/state
and retrieval after mutation/reopen. R3 needs authentic unauthorized challenges,
legitimate utility preservation and reviewed decision comparators; actual
protected execution remains a separate unauthorized scope. No present evidence
supports universal revocation, population attack rates or provider ranking.

Existing evidence can support: (1) a planned/complete/native/anomaly/unknown flow
table; (2) all 27 paired reasoning differences grouped by nine cases with request
hash dependencies annotated; (3) the 54 ALLOW plus one NOT_APPLICABLE decision
table, explicitly showing zero unauthorized-challenge coverage; (4) an NQ/A3
state-versus-selection timeline with existing receipt IDs. Private content must
be reduced to safe labels. No R1/R2 outcome bars, efficacy percentage or invented
confidence interval is warranted. No new figures are required for this decision.

## D. Minimal R2 protocol candidate — PROPOSED / NOT EXECUTED

Reuse the Mem0 transition row of roadmap v3. Narrow the first R2 milestone to
native state/retrieval; model proposals and host decisions are NOT_EVALUATED.
Roadmap counts depend on R1 and capability verification: this two-trajectory
feasibility candidate does not settle a later R1-informed scientific sample size.
Proceeding with it before R1 requires a separate explicit research decision.

Use **two fresh physically separate disposable Qdrant/SQLite stores**, one
UPDATE trajectory and one DELETE trajectory, run serially. Each starts with one
synthetic routing assignment (neutral recipient A) and one unchanged sentinel
record. An independently host-authored state schedule specifies the later
assignment B; memory content never grants authority. This is one synthetic
scenario with two trajectories, not two independent replications or an estimated
security rate. No R1 store, payload package, execution identity or denied action
is reused.

Before implementation review, fix exact fixture strings, namespace mapping,
query without recipient A/B, metadata, selector and search limit **10**, no
score threshold, at every checkpoint. Two known records allow an inventory
comparison, but even a generously sized top-k is not a deletion oracle. Retain
every raw candidate, score and native order; apply the same literal selector,
with no inserted/repaired result. A native history may legitimately retain old
content: report it rather than interpreting absence from retrieval as erasure.

| Trajectory / process | Native sequence and checkpoints | Required observation / falsifiable expectation |
| --- | --- | --- |
| UPDATE / initial | Inspect empty; Add target A and sentinel (`infer=False`); direct Get, scoped get_all, Search, history; native Update same target ID to assignment B; repeat Get/get_all/Search/history; close | Preserve actual Add/Update arguments and returns; test same-ID live content becomes B and sentinel stays unchanged; record whether A/B appear in candidates and selected context |
| UPDATE / new process | Verify prior sealed inventory/expectations before construction; reconstruct on identical persistent paths/configuration; Get/get_all/Search/history; close | Test updated ID/content and sentinel persist; compare raw ranks/selection and history, without assuming identical scores or stable ranking |
| DELETE / initial | Inspect empty; Add fresh target A and sentinel; baseline Get/get_all/Search/history; native Delete target ID; repeat Get/get_all/Search/history; close | Record Delete return independently; test direct Get absence, inventory absence and search absence separately; sentinel survival checks store usability |
| DELETE / new process | Verify prior sealed inventory/expectations; reconstruct on identical paths/configuration; direct Get/get_all/Search/history for deleted ID and sentinel; close | Test deleted ID remains absent from live lookup/inventory/retrieval; retain tombstone/history/error behavior verbatim; verify sentinel persists |

Four sequential processes total; each constructs a fresh client. No in-process
reinitialization is counted as Reopen. No repeats, retries or replacement stores
are inferred from failed expectations. Capture unexpected returns/errors and
seal partial outcomes; failure before an observation leaves it UNKNOWN. A later
checkpoint is not silently repaired to produce the expected transition.

Keep four observation layers distinct:

1. **Persistent state:** native IDs, exact content, scoped inventories and closed
   Qdrant/SQLite snapshots; history/events reported separately from live records.
   Hash equality supports custody, not semantic interpretation by itself.
2. **Operation returns:** exact Python SDK arguments, returns, exceptions and
   times, including provider UUIDs. Adapter-normalized values cannot replace raw
   returns; these are not fabricated HTTP wire bytes.
3. **Retrieval:** fixed query/scope/limit, all candidates with IDs/scores/ranks,
   missing IDs and unchanged-sentinel behavior at every checkpoint.
4. **Selected context:** exact literal selection and order plus hash and selector
   identity. Record `MODEL_EXPOSURE=NOT_SENT`, `MODEL_PROPOSAL=NOT_GENERATED`;
   this candidate sends nothing to a model.

Classify each expectation OBSERVED_MATCH / OBSERVED_MISMATCH / UNKNOWN with the
supporting receipt, rather than a blended success rate. Update measures a content
transition, never native revocation. Delete tests live-record absence through
specified interfaces, never complete forgetting or secure erasure. Histories,
backups, embeddings and unexposed derivatives bound that interpretation. This
mode has no qualified source→derived invalidation, native authentication,
ID-level host authorization, concurrency/crash guarantees or global quiescence.
Namespace route/filter isolation does not prove host authorization. Dense local
retrieval omits optional spaCy/BM25 features and full LLM consolidation.

## E. Feasibility, reuse and resources

**Technically feasible with the preserved qualified local infrastructure; current
operational readiness is unverified. No Jetstream or Qwen is needed.** Only
read-only files were inspected; no Docker/provider check or construction ran.
The retained Linux runtime directory exists; the current public checkout lacks
that private source/runtime closure and has no local `.venv`.

Reuse the NQ `REPRODUCE.md` identities: CPython 3.12.8 Linux amd64 image
`sha256:2199a62885a12290dc9c5be3ca0681d367576ab7bf037da120e564723292a2f0`,
Mem0 2.2.1, sentence-transformers 6.1.0, CPU Torch 2.14.0+cpu,
Transformers 5.20.2, Qdrant client 1.20.0 and qualified Pydantic 2.13.5 closure.
The 71-wheel hash lock and 11 model artifacts total 387,040,477 acquisition bytes.
Local `paraphrase-MiniLM-L3-v2` revision is
`4ca70771034acceecb2e72475f72050fcdde4ddc`. Qdrant is the qualified local embedded
store, not a proposed network provider service. The macOS Torch plan was
incompatible; do not substitute it or re-resolve dependencies as if qualified.

Existing private entrypoints are
`scripts/native_qualification/qualify_mem0_runtime.py` (exercise/reopen, including
pre-construction persistence binding), `mem0_a3_pilot.py` / `mem0_a3_pilot_local.py`
(separate physical stores and literal selection), and the task-owned historical
`run_phase.py` container caller. Reuse the existing `Mem0MemoryAdapter`,
`NativeLifecycleCapture`, `attach_mem0_capture` and `ResearchCapture` seams.
These sources remain in the private checkout and are not supplied by a fresh
public clone. Historical callers contain fixed identities/output paths and must
never be invoked unchanged for R2.

The minimal future change is a separate bounded scenario caller/fixture and
expectation binding for two stores, authority-content update, sentinel checks and
each checkpoint's direct Get/inventory/selection. Keep accepted mechanisms and
source untouched. No new controller/provider framework is needed. Source review
must verify scoped get_all completeness and all capture/close behavior before
claiming readiness. This task implements none of those changes.

Use the historical per-container ceiling as a planning basis: **2 CPU, 8 GiB
RAM, 256 PIDs, 1 GiB temporary filesystem**, one container at a time. This is a
resource proposal, not measured R2 peak use. Reserve approximately **5 GiB free
local disk** for fresh stores, journals and closed snapshots in addition to the
existing image/runtime/cache; installed/image footprint and R2 snapshot size
were not measured here. A future bounded plan should stop on the disk budget,
not prune other data. No GPU, external inference, package/model download or
paid remote compute is needed if existing artifacts reverify.

Retain Docker `--network none`, read-only source/runtime/model mounts, dropped
capabilities, no credentials, Python socket denial before provider import,
telemetry off and the fail-closed internal-LLM guard. Use only the qualified
repository `.venv`; no global/user installation or new dependency work is proposed.

Custody requires exclusive fresh output, source/runtime/configuration hashes,
durable pre-operation intents, exact arguments/returns, native IDs, before/after
views, candidate/selection receipts, process/container identity and exit records.
Bind reopen to the original closed-store snapshots, inventory, paths and sealed
expectations before construction. Preserve errors and partial captures. After
closing clients, snapshot and hash SQLite/Qdrant including history; independently
check the inventories before removing owned mutable stores. Retain immutable raw
evidence privately, and publish only reviewed safe aggregates/IDs/hashes.

Cleanup removes only future task-owned containers, stores and temporary files
after evidence preservation; verify ownership and absence with receipts. Leave
the pre-existing daemon, caches, other/Exosphere-managed containers and `/dev/sdb`
untouched. No SSH, volume operation, cloud lifecycle or shelving is required.

## F. Exact future authorization requirements

This document is neither an execution grant nor a frozen manifest/live identity.
A separate decision must first accept the native-only milestone and authorize
any minimal offline caller preparation. Before native execution, require:

- Genuine independent review of the exact final scientific plan, caller/source
  closure, fixture/selection rules, operation bounds, custody and cleanup.
- A new direct execution-specific owner grant binding that reviewed package,
  fresh disposable stores, local host/Docker endpoint, exact image/.venv/cache,
  two trajectories/four sequential processes, exact operation ceilings, CPU/RAM/
  disk caps, time window and stop/cleanup deadlines. Permit only Add, Update,
  Delete, Get/get_all/Search/history, snapshots and distinct-process reopen of
  owned stores; enumerate readiness and cleanup actions too. Final call ceilings
  must include capture-internal reads; no live identity is created now.
- Supported external approval for the complete dependent action scope and
  genuine owner provenance wherever required by system/sandbox/tool gates.
  Review/grant JSON alone proves neither human permission nor external approval.
  Preserve a denial; no alternate writer/path/runtime may achieve its outcome.

Explicitly exclude Qwen/other model requests, provider-internal LLMs, SSH,
Jetstream, remote access, protected dispatch, R1 continuation/replay and
cross-provider expansion. No historical receipt, grant or identity authorizes
R2. Missing or rejected authority means stop and clean up within original bounds.
R2 is a different native lifecycle question, not a route around R1's denied live
operation. Historical Freeze v1/v2, the frozen OpenViking error and Candidate10
NO_GO remain immutable.

## G. Recommendation and review

Accept the scoped R0 evidence map for manuscript planning. Next decide whether
to prepare the two-trajectory native-only R2 caller for package review, with no
model or enforcement efficacy claim. Its deliverable would be one falsifiable
state/return/retrieval/selection transition table with persistence and cleanup
receipts. Defer a larger sample, causal claims, derived-lineage experiments and
R3 comparisons until their missing evidence and authority are separately resolved.

Independent reviewer `/root/scientific_review` returned **ACCEPT, no actionable
findings**, on the substantive draft SHA-256
`36b29e08a417d53b8f6eb36144dacc620cb1ec46723081d2a9765ddc8ff8652c`.
The read-only review checked R0/F04 identities and denominators, NQ/A3 report
hashes, roadmap consistency, qualified reuse/resources, scientific limits,
historical freezes and privacy. This paragraph records that outcome; it does not
extend acceptance to future implementation, execution or authorization. No new
raw-inventory audit or runtime qualification was performed.
