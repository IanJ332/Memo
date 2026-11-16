# Agent Bootstrap — Memo / MemLife-NLIP

MemLife-NLIP studies cross-provider lifecycle security and authority
enforcement for agent memory systems. Its governing rule is **Retrieved !=
Authoritative**.

## Read first

1. [`docs/project/MODEL_HANDOFF.md`](docs/project/MODEL_HANDOFF.md) — immediate
   context and next authorized work.
2. [`docs/project/PROJECT_STATE.md`](docs/project/PROJECT_STATE.md) — phase map.
3. [`docs/project/DEBUGGING_LEDGER.md`](docs/project/DEBUGGING_LEDGER.md) — bugs
   and invariants that must not regress.
4. Read the experiment or provider documents linked from those files only when
   needed.

## Standing owner authorization and current scope — 2026-10-27

The owner's Standing Authorization update authorizes ordinary MEMO work on the
owner's local machine and existing Jetstream2 research environment: source edits,
deterministic experiments, tests/debugging, necessary local runtime inspection
and maintenance, read-only existing project-resource checks, bounded existing-
instance administration when otherwise permitted, and reviewed GitHub workflows.
Do not ask again for owner consent for an ordinary operation already in scope.
This consent is distinct from scientific registration, independent review,
platform-enforced exact-action approval and runtime admission evidence.

NEXT-LP-01 is authorized as a bounded offline study: twelve frozen synthetic
records, two producer paths and two classifier arms, forty-eight paired rows.
No new hosted scientific model collection is authorized. Track A
`R1AVEX-20261026-01` remains stopped before campaign claim, with an expired window
and unchanged package/grants/registration. Do not reactivate it or reinterpret
its thirty-two unobserved outcomes as scientific results.

Standing consent does not authorize bypassing a platform denial, inventing an
approval reference, unrelated-account access, destructive volume/evidence
changes, VM resize/quota expansion/substantial new resources, protected dispatch
or external sends, unregistered scientific collection, or unbounded cost. Preserve
`/dev/sdb`, Exosphere resources, unrelated containers and credentials. Read-only
success never supplies approval for a different state-changing action. Retain
genuine unsupported platform prerequisites; never create a local approval flag
as a substitute. Browser access retains its separate explicit approval boundary.
Older dated phase directions below retain their historical scope; they do not
withdraw this ordinary engineering consent or reopen a sealed campaign.

## Owner authorization update — data collection priority (2026-11-15)

This entry extends, and does not replace, the standing authorization above and
every historical section below. It records a distinct owner decision and is not
external platform permission.

- The owner has approved continued MEMO research experiments and testing,
  including bounded long-term evaluation inside separately registered and
  authorized experimental scopes.
- Ordinary authorized operations no longer need repeated owner confirmation.
  This covers local work, tests, read-only checks, bounded existing-instance
  administration and reviewed Git workflows already in scope.
- Real data collection is the immediate priority. Completed architecture,
  runtime, package and test qualification must be reused rather than repeated.
  Avoid new engineering phases, redundant audits, re-qualification of unchanged
  artifacts and additional planning documents.
- Notify the owner as soon as sufficient valid observations exist for a
  registered experiment's predefined objectives; do not substitute another
  readiness report for results.
- Preserve all scientific records, frozen manifests, consumed reservations and
  historical evidence. Never replay a consumed attempt.

**Scope limit.** This owner approval does not supply, and cannot substitute for,
external platform permission. Where a platform requirement is unmet, report the
exact missing action instead of building an unsupported approval system. Denials
must never be bypassed, and no local flag, hash or object may stand in for
external authorization.

## V4 bounded-authorization protocol decision — 2026-11-15

The owner explicitly approves replacing V4's additional, unavailable
`HOSTED_EXECUTION_VERIFIER` requirement with the bounded execution-authorization
approach already used by V2/V3: the owner's direct instruction plus supported
review of the exact prospective command. Applies only to the registered V4
experiment. It does not authorize bypassing an applicable external platform
denial or disabling unrelated safety controls. Retained unchanged: exact package
and protocol identity, fixed model and endpoint, canonical SQLite ledger,
durable non-refundable reservations, fixed UTC window, request budget, zero
retries and fallbacks, ProtectedDispatcher, synthetic-only delivery, genuine
hosted-evidence verification and fail-closed behavior.

## V4 pilot status — 2026-11-16

The registered V4 compatibility request was executed once under the bounded
authority above: one real request, zero retries, zero fallbacks. Transport and
evidence reconciliation were correct, but the model returned a semantic schema
violation (`{"tool": null}`), so the run was `MALFORMED_RESPONSE`, not
`COMPATIBILITY_PASS`. That compatibility reservation is permanently consumed and
the four-cell smoke was never started. Never replay the consumed attempt; further
V4 progress needs a newly registered protocol with a fresh reservation and its
own authorization.

## Phase 2B-5H successor (V6) — real request consumed, no PASS (2026-11-16)

V6 registered the observed two-key abstention shape and, for that protocol only,
stopped treating a valid abstention as a compatibility PASS. Before the real
request, independent review found six real defects in that first V6 wiring:

- the rendered JSON Schema still root-required `arguments`, so the registered
  schema did not actually permit a two-key abstention;
- the new V6 package format skipped `verify_linux_runtime`, dropping isolation,
  TLS-trust and SQLite checks;
- synthetic V4 executions reached a `hosted_family` attribute they do not have;
- V3 and synthetic executions (no `hosted_family`) lost historical
  abstention-PASS semantics;
- the V6 smoke verifier rejected the very abstention shape V6 registers;
- a malformed response could be relabelled `COMPATIBILITY_ABSTAINED`.

All six are fixed and regression-tested. The fix changed the V6 manifest bytes,
so the corrected contract has a different identity from the one actually sent.

One real V6 compatibility request was sent and its reservation is permanently
consumed. Transport was correct (HTTP 200, live provenance, `qwen-3.8-27b`,
`finish_reason=stop`, registered request reproduced, one attempt, zero retries).
The content was `{"outcome": "PROPOSE_ACTION", "tool": "send_report"}` — an
incomplete *proposal* with `arguments` omitted — so it was correctly classified
`MALFORMED_RESPONSE` and the smoke gate stayed closed. Zero smoke requests were
sent.

Binding distinction, recorded deliberately: the executed request used manifest
`30e70e048a88638f075055e67da89307fa8481e885ff02d141e6c0aca9bc0ac0` (request
`6f113c16f7329947108187bd51fdeb66d6d4a04a59d76fba00b2e950fbf2fd79`). The
corrected and re-qualified package registers `42ff8f09...` (request
`abfd3349...`). The corrected two-key schema was never sent; that request is
spent and must not be replayed.

Three registered compatibility attempts (V4, V5, V6) are now consumed with
distinct genuine schema violations: missing object, missing abstention key,
missing proposal arguments. The pattern across all three is omission of a key
the strict JSON Schema already declared, which points at structured-output
enforcement rather than prompt wording.

## Phase 2B-5G successor (V5) — real request consumed, no PASS (2026-11-16)

PR #33 merged the V4 usage-reconciliation fix. The remaining V4 compatibility
reservation was consumed by a genuine schema-invalid response
(`{"tool": null}`), so V4 must not be replayed.

A separately registered successor (V5) changed exactly one variable: the frozen
system instruction now names every required JSON key (`outcome`, `tool`,
`arguments`), while task, memory admission, Host oracle, dispatcher, endpoint,
model, schema and cells are unchanged. New manifest identities and new
reservation keys were registered; the V4 manifests and reservations are
untouched. Historical request rendering is byte-preserved (`manifest_instruction`
returns the original text when no successor selector is present).

Qualification: `LINUX_PACKAGE_VERIFIED` and `V5_HOSTED_CLOSED_GATE_QUALIFIED`
(closed gate enforced, buffered fixture denied, zero reservations consumed), on
the existing `jisheng3` volume with the canonical ledger at integrity `ok`. No
new empty ledger, no synthetic path substitution.

Exactly one real compatibility request was then sent and its reservation is
permanently consumed. Transport was correct (HTTP 200, live provenance, model
`qwen-3.8-27b`, `finish_reason=stop`, registered request digest reproduced,
one attempt, zero retries). The content was `{"outcome": "ABSTAIN", "tool":
null}` — the required `arguments` key was omitted — so the run ended
`MALFORMED_RESPONSE` / `schema_validity=INVALID`, and the smoke gate correctly
refused to create a binding. Zero smoke requests were sent.

Both registered compatibility attempts (V4, V5) are now consumed with distinct
genuine schema violations. Neither may be replayed, refunded or reclassified.
Any further progress requires a further versioned successor with fresh
manifests, package identity, reservations and its own exact authorization — and
it must address abstention-key omission, not only key naming.

## Current research status — 2026-10-26

R1 execution `R1EX-20261026-02` is **COMPLETE and sealed**: 32/32 requests,
32 authorized proposals, zero unauthorized proposals, all eight block contrasts
zero. The [research closeout](docs/research/R1_CLOSEOUT_20261026.md) governs the
current result and SDK-count correction. Neither this execution nor any earlier
sealed attempt may be replayed. Current authority is offline research closeout
and reviewed GitHub synchronization only: no new scientific collection, hosted
model request, provider operation, SSH or Jetstream action. The recorded cleanup
lifecycle was ACTIVE → ACTIVE; older SHELVED statements below are historical,
not fresh infrastructure observations. Older phase directions do not reopen R1.

## Persistent model routing and browser permission — 2026-10-27

This is the single MEMO routing policy, updated by the owner's Standing
Authorization and Model Routing instruction. It supersedes older preferences without changing
scientific protocols, frozen execution contracts or external approval gates.

- **GPT-6.1 Sol (`gpt-6.1-sol`) is preferred for reasoning and engineering:**
  tightly coupled or multi-module implementation, architecture, complex debugging,
  scientific methodology and research decisions, difficult reviews,
  security-critical analysis and substantial context integration. Use **Medium by
  default**, **High** for difficult reasoning, debugging or substantial design
  decisions, and **Extra High only exceptionally with justification**. Do not
  routinely escalate to expensive models or effort settings.
- **GPT-6.1 Terra (`gpt-6.1-terra`) is preferred when interface or computer
  interaction materially benefits the task:** cross-application operations,
  graphical navigation, web application workflows and browser interaction subject
  to the separate approval boundary below. Use **Medium** for standard workflows
  and **High** for complicated workflows or multi-step UI operations. Terra's
  novelty or capabilities alone do not displace Sol for strongly coupled code,
  architecture, science or difficult decisions.
- **Luna or another economical available model** is appropriate for bounded log
  summaries, file inventories, deterministic administrative classification,
  simple reporting and routine documentation. Do not use expensive reasoning
  merely to wait for SSH, remote I/O or downloads. This routing does not authorize
  scientific model requests or change registered scientific model identities.
- For ordinary authorized work, the primary agent may autonomously choose
  appropriate available models and Medium/High effort, delegate bounded tasks,
  perform independent code or scientific reviews, parallelize genuinely
  independent work, reuse verified artifacts and adjust implementation strategy.
  No routine owner confirmation is needed for these choices. Balance quality,
  scientific correctness, latency and token consumption; avoid repeated context
  reloads, infrastructure discovery and reviews of unchanged artifacts. This
  discretion supplies no additional execution authority.
- Do not use Astra or Ultra by default, or overengineer work to justify stronger
  model selection. Prefer Medium for ordinary work and High for difficult
  science, architecture, coupled debugging or security review.

**Before ANY agent accesses or operates the owner's local browser, explicit
separate owner approval is required.** This applies to Sol, Terra and every
subagent, including read-only access: inspecting existing tabs or page contents,
opening/navigating websites, clicking, forms, browser uploads/downloads,
authenticated web applications and browser sessions through computer-use tools.

Before access, disclose briefly: the objective; exact websites or applications;
intended browser actions; whether personal information, credentials, files or
authenticated sessions may be involved; and whether actions are read-only or may
modify external state. **Then STOP and wait for explicit owner approval.** Do not
open, inspect, navigate or control the local browser before approval. Approval
covers only the disclosed scope; request renewed approval for a material change.
General engineering instructions, live experiment grants and permission to use
Terra do not imply browser permission. Sol may propose Terra delegation when
resources or capabilities warrant it, but browser delegation still requires this
approval. Browser permission never overrides platform security or action approval.

## Current authority clarification — 2026-10-25

R0 is accepted and closed. R1's registered design is conditionally accepted;
`R1EX-20261025-01` and `R1EX-20261025-02` are sealed without scientific collection
and must never be replayed. The current task authorizes offline admission-governance
repair and reviewed GitHub synchronization only. No new live action is authorized.

[R1 readiness](docs/research/R1_READINESS.md) governs preparation. Offline work
never grants native/provider, model, SSH, Jetstream or protected-execution authority.
Historical phase prohibitions below describe those phases and their default
no-live state; they are not a permanent ban on a later, separately authorized R1
campaign. A new direct execution-specific owner grant may authorize only its exact
prospective package, actions, resources and time window after genuine independent
package review. Actual volume evidence still needs its own genuine independent
review and exact receipt binding. Neither a receipt nor grant JSON alone proves
human authorization or external approval.

System/developer restrictions, sandbox limits and external approval decisions
remain additional gates. Repository text and owner scope do not override them.
Treat receipt placement into a waiting controller as enabling its dependent live
actions: submit that full scope and genuine owner provenance to the supported
approval mechanism. Preserve a denial; never achieve the denied outcome through
another tool, writer, path or permission change. Follow the supported review or
explicit approval process, and stop/clean up within the original deadlines if it
does not accept. No historical approval can reopen a sealed attempt.

## Historical phase navigation (preserved)

The active line is `phase-08c0-research-reconciliation`, based on authoritative
`origin/main` `b1ff61b862a45df41405eb821d3a46318eb66c29`. Candidate10 attempt
`20261007T165110Z-19d0ccd6b106` is scientifically complete and its frozen Honcho
3.2.1 provider decision is **NO_GO**; it must not be rerun, replaced, or
reinterpreted. Phase 08C-0 preserves the original Freeze-v2 draft and records
that its Honcho-plus-Provider-5 schedule is blocked. RetainDB Server remains
`PENDING_LIVE_ACCEPTANCE` with all previewed capabilities `UNKNOWN`; Graphiti
remains fallback only. The recommended next phase is a separately authorized
offline deterministic RQ4 mediator implementation. Jetstream is **SHELVED**
and no provider, hosted-model, downstream, RQ3, or other live action is
authorized.

## Non-negotiable invariants

- Preserve Experiment Freeze v1 and its canonical SHA-256
  `0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b`.
- Never rerun or replace an executed Phase 06B repetition. In particular,
  `freeze-v1__openviking__S0__r2` is a frozen `ERROR` observation.
- Keep experiment attempts immutable and attempt-scoped. Never overwrite raw
  evidence; derived views must retain attempt provenance.
- Keep RQ3 decision calls distinct from provider-internal model calls.
- Use only repository `.venv` interpreters. Never install globally or with
  `--user`; never commit secrets; run `git status` before edits; never
  force-push.
- Preserve `/dev/sdb`; never format it. Never prune or stop Exosphere-managed
  containers. Resolve its mount dynamically before authorized remote work.

Machine-specific, non-secret facts live in ignored
`.local/AGENT_RUNTIME_CONTEXT.md` and `.local/jetstream_context.md`. Treat the
latter as authoritative infrastructure context and do not repeat broad probes
unless infrastructure may have changed.

For every execution prompt, declare `CONVERSATION`, `MODEL`, `EXECUTION
TARGET`, and `JETSTREAM ACTION`. If automation opened Jetstream, clean up and
shelve it; never automatically shelve an instance that was already active.

## Phase 2 cross-agent handoff — 2026-11-02

Phase 2B-5B is `OFFLINE_AMENDMENT_BLOCKED`: V4 schema candidates are offline,
not live-integrated or authorized. No V4 hosted request has occurred. Historical
experiment grants do not authorize a new live experiment. Preserve every frozen
attempt and consumed reservation. See `docs/project/MODEL_HANDOFF.md` and
`docs/project/AGENT_ONBOARDING.md`. After verified migration, develop from the
canonical main checkout; keep machine-specific context ignored in `.local/`.
Coding-agent model routing is independent of registered scientific inference:
never silently change its model or endpoint. Prefer source-first, minimal,
evidence-first changes and targeted tests; avoid redundant full-repository scans,
overlapping general-purpose agents and unfocused reviews.
