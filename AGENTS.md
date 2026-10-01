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

The active line is `phase-06b-storage-batch`. Phase 06B is partial; Phase
06B-C passed; the next phase is local-only Phase 06B-S0 supplement design.
Jetstream is **SHELVED** by default and must not be started without explicit
authorization.

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
