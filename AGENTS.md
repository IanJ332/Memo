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
