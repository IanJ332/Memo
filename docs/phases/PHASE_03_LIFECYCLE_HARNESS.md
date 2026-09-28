# Phase 03 — Cross-Provider Lifecycle Benchmark Harness

## Objective

Phase 03 adds a provider-independent harness for observing authoritative/current
memory state after ordered lifecycle events. It keeps scenario intent, native
provider operations, observed provider state, and normalized evaluation as
separate data.

This phase is local-only. It did not use Jetstream2, install another provider,
call a hosted LLM, implement the Memory Authority Gateway, or execute downstream
security consequences.

## Scientific Role

The harness asks what a provider exposes after writes, corrections,
supersession, revocation, deletion, and reconstruction. Provider mechanics are
observations rather than universal requirements. In particular, Mem0's native
same-UUID update is not treated as a conformance rule: the reference provider
creates a successor ID and retains the predecessor, while Mem0 updates the
existing UUID.

Phase 03 is NOT yet a cross-provider empirical comparison because only the
reference provider and Mem0 are currently connected.

## Benchmark Version

The scenario and result schema version is `0.1`. Every scenario and result
record carries this explicit version; timestamps are run provenance and are not
used as a schema version.

## Scenario Model

`LifecycleScenario` records:

- `scenario_id`, `description`, and isolated `namespace`;
- `initial_memory` and ordered `lifecycle_steps`;
- deterministic `queries` with separate current and stale facts;
- final `expected_authoritative_state`;
- optional `tags` and `benchmark_version`.

Validation rejects blank required values, duplicate or unknown queries,
redeclared memory keys, and references to a memory key before its write. Memory
keys are scenario-local aliases; they do not prescribe provider UUID behavior.

## Lifecycle Events

Version 0.1 represents `WRITE`, `UPDATE`, `SUPERSEDE`, `REVOKE`, `DELETE`,
`RESTART`, `QUERY`, and `INSPECT`. An adapter may support one event through a
different native primitive, and may explicitly reject an event it cannot
natively perform.

## Native vs Normalized Semantics

Each step records both `intended_event` and `native_operation`. The runner calls
only the adapter contract; it does not instantiate providers, branch on provider
name, rewrite expectations, or emulate unsupported behavior.

Examples from the local validation:

- reference `SUPERSEDE` uses `reference.create_successor_record`;
- Mem0 `SUPERSEDE` uses `Memory.update(same UUID)`;
- Mem0 `REVOKE` is `UNSUPPORTED` because native deletion is not revocation.

## Canonical Scenario Suite

The suite contains five safe synthetic scenarios and 24 ordered steps:

1. `baseline`: write v1, query v1, inspect;
2. `correction-update`: write a $500 threshold, update it to $100, query both
   propositions, inspect;
3. `revocation`: write temporary Analyst-7 access, attempt native revocation,
   query it, inspect;
4. `delete-restart`: write and confirm a canary, delete and confirm absence,
   reconstruct, query again, inspect history;
5. `supersession`: replace Alice with Bob for Project Cedar, query both
   propositions, inspect.

The fixtures contain no real people, credentials, personal data, or external
actions.

## Result Schema

Each step produces a closed `BenchmarkResult` with benchmark/scenario/provider
identity, namespace, native lifecycle mode, ordered step and intended event,
native operation, operation status, IDs before and after, query text, retrieved
current/stale facts, observed record contents, expected authoritative state,
correctness/visibility flags, sanitized provider metadata, unsupported/error
details, latency, and an aware timestamp.

Serialization is deterministic JSON: stable field names and key ordering,
UTF-8-safe text, enum values rather than Python representations, and schema
round-trip validation. Metadata keys that look like credentials or secrets are
rejected.

## Outcome Normalization

Exact fixture-content presence maps query observations to:

- `CURRENT_ONLY`;
- `CURRENT_AND_STALE`;
- `STALE_ONLY`;
- `ABSENT`;
- `UNSUPPORTED`;
- `ERROR`.

These are lifecycle observations, not vulnerability labels. The benchmark does
not use an LLM judge or semantic residual score in version 0.1.

## Reference Provider Validation

The deterministic in-memory provider completed all 24 steps successfully. Its
exact substring query returns `ABSENT` when an old full proposition no longer
matches the current successor, and `CURRENT_ONLY` for the new proposition.
Revoked/deleted/superseded records remain visible through diagnostic inspection
and related history. Its restart hook is intentionally a logical no-op.

## Mem0 Validation

The local suite used `mem0ai==2.2.1`, `infer=False`,
`sentence-transformers/paraphrase-MiniLM-L3-v2`, embedded Qdrant, and SQLite
history. No LLM calls occurred.

Mem0 completed 23 steps and explicitly reported native revocation as the one
unsupported step. Both correction and supersession used native same-UUID
updates. Searches for both old and new propositions retrieved only the current
updated fact (`CURRENT_ONLY`). Because revocation was not emulated, the original
fact remained normally retrievable (`STALE_ONLY`). Deleted content was `ABSENT`
before and after provider reconstruction, while native history remained visible.

## Runtime Storage

Scenario definitions, schemas, code, tests, documentation, and the sanitized
phase manifest are tracked. Full JSON runs, Qdrant files, SQLite stores, model
caches, and temporary logs remain below the ignored `runtime/` tree. The CLI
rejects an output path outside the resolved local runtime directory.

## Reproduction Commands

Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
.venv\Scripts\python.exe -m memlife.runner.lifecycle_benchmark --provider reference --output runtime\runs\phase-03\reference.json
.venv\Scripts\python.exe -m memlife.runner.lifecycle_benchmark --provider mem0 --output runtime\runs\phase-03\mem0.json
.venv\Scripts\python.exe -m pytest -q
```

Linux/macOS:

```bash
PYTHONPATH=src HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m memlife.runner.lifecycle_benchmark --provider reference --output runtime/runs/phase-03/reference.json
PYTHONPATH=src HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m memlife.runner.lifecycle_benchmark --provider mem0 --output runtime/runs/phase-03/mem0.json
.venv/bin/python -m pytest -q
```

## Known Limitations

- Only the reference provider and Mem0 are connected.
- Exact fixture-content evaluation does not measure paraphrased residual memory.
- Reference restart is a deterministic logical hook, not process persistence.
- Version 0.1 does not test concurrency, load, attacks, or downstream actions.
- Native history is summarized by event/count; provider-specific raw blobs are
  not placed in cross-provider result records.

## Next Provider Handoff

A future provider should implement the existing adapter contract, declare its
capabilities, describe its native operations, expose sanitized history when
available, and run the unchanged canonical suite. Unsupported lifecycle intent
must remain explicit unless a later benchmark version deliberately introduces
and labels an emulation mode.
