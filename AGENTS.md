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

The active line is `phase-08b1-candidate10-publication`. The original Candidate10
publication commit is `54c1f7847af582cffc078fbc99aecfaab6b12dc2`; the published
portability closure is `3c126216f4f5b7ac4f842e344598324c8d6a4097`. Scientific
closeout is accepted and merge to `main` remains pending final review. Candidate10
attempt `20261007T165110Z-19d0ccd6b106` is scientifically complete and its frozen
Honcho provider decision is **NO_GO**. The result preserves 10
`SUPPORTED`, 4 `UNSUPPORTED`, and 4 `UNKNOWN` capabilities; only S0 was
directly executed.
S1 remains `UNKNOWN`, S2-S5 are capability-derived `UNSUPPORTED`, and native
Dream quiescence remains `UNKNOWN`. The controller SSH transport failure is
separate from scientific completion and its root cause remains `UNKNOWN`.
Candidate10 must not be rerun or replaced. The raw evidence appendix remains
local and unpublished. Jetstream is **SHELVED** and no new live action is
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
