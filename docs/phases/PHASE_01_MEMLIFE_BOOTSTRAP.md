# Phase 01 — MemLife Bootstrap

## Objective

Establish a small, reproducible, provider-independent experiment foundation for
MemLife-NLIP. Phase 01 defines stable data structures, an explicit provider
adapter boundary, offline contract validation, safe runtime storage selection,
and environment manifests. It does not implement the Memory Authority Gateway,
integrate real memory providers, or run attacks.

## Starting State

Phase 01 was created from local commit
`8a6a364bee166465a127590b8619cc5c187c4fed`, which was one commit ahead of
`origin/main`. Inspection classified it as a valid project change (CASE A): it
added `AGENTS.md` repository operating guidance and ignored the machine-local
`.local/` directory. The commit remains in the Phase 01 lineage.

Before work began, a local recovery pointer named
`local-pre-phase01-8a6a364` was created at that commit. The untracked local
`JETSTREAM2_SERVER_CONTEXT.txt` file was retained and excluded with the
clone-local `.git/info/exclude`; it is not part of repository history.

## Changes Introduced

- Added the `src/memlife` package and explicit lifecycle models.
- Added an abstract, capability-aware memory provider adapter contract.
- Added a deterministic in-memory reference provider.
- Added reusable provider contract tests and focused unit tests.
- Added safe Jetstream/local runtime-path selection and idempotent setup.
- Added non-secret environment manifest generation with configuration hashing.
- Pinned the small common dependency set and preserved existing dependencies.

## Repository Structure

```text
Memo/
├── requirements.txt
├── requirements/core.txt
├── src/memlife/
│   ├── adapters/{base.py,reference.py}
│   ├── config/paths.py
│   ├── models/{lifecycle.py,memory.py}
│   └── runner/manifest.py
├── configs/README.md
├── manifests/README.md
├── scripts/setup/prepare_runtime.py
├── tests/
│   ├── contract/{provider_contract.py,test_reference_provider.py}
│   └── unit/
└── docs/phases/
```

Only directories with a Phase 01 responsibility were added.

## Dependency Policy

`requirements/core.txt` pins every direct dependency. Existing `openai` and
`psutil` dependencies remain. Phase 01 adds only `pydantic` for boundary models
and `pytest` for offline validation. No memory-provider SDK, vector database,
LangChain, LlamaIndex, local model weight, or provider service is installed.

All installation commands must use the repository-local `.venv` interpreter.

## Runtime Storage Policy

Storage selection follows this precedence:

1. `MEMLIFE_DATA_ROOT`, with relative values resolved under the repository.
2. `/media/volume/sdb/memlife` when `/media/volume/sdb` exists on POSIX.
3. `<repository>/runtime` on other development machines.

The setup script idempotently creates `providers/`, `datasets/`, `model_cache/`,
`runs/`, `logs/`, and `artifacts/`. `runtime/` is gitignored. The implementation
contains no formatting, partitioning, deletion, Docker, or container operation.

## Provider Adapter Contract

`MemoryProviderAdapter` defines:

- `reset_namespace`
- `write`
- `query`
- `update_or_supersede`
- `delete_or_invalidate`
- `list_or_inspect`
- `restart`

Every adapter declares each operation as `SUPPORTED` or `UNSUPPORTED`.
Unsupported operations must be surfaced explicitly and must not be silently
emulated. The lifecycle vocabulary is limited to `ACTIVE`, `SUPERSEDED`,
`REVOKED`, `DELETED`, and `EXPIRED`; these are normalized observations, not an
authority-enforcement policy.

## Reference Provider

`ReferenceMemoryAdapter` is a deterministic, namespace-isolated, in-memory
control. It retains lifecycle history for inspection and uses stable IDs within
each reset namespace. Its `restart` method is intentionally a documented no-op:
there is no process or persistent backend to restart, so records remain in the
current adapter instance. It does not imitate Mem0 or any other real provider.

## Validation Performed

- The reusable contract exercised reset, write v1, query v1, supersede with v2,
  query current state, delete, and verify no current result.
- Unit tests covered namespace isolation, lifecycle errors, reference history,
  restart behavior, runtime selection/setup, manifest output, stable config
  hashing, and sensitive-key rejection.
- Runtime setup was executed twice against the local fallback and remained
  idempotent.
- The existing Jetstream/environment bootstrap scripts were not modified.
- Final Phase 01 result: `9 passed` with no external API calls.

## Commands to Reproduce

Windows:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe scripts\setup\prepare_runtime.py
.venv\Scripts\python.exe -m pytest -q
```

Linux, macOS, or Jetstream2:

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/setup/prepare_runtime.py
.venv/bin/python -m pytest -q
```

Manifest callers use `memlife.runner.manifest.build_manifest` with a resolved
`DataRootConfig`, then `write_manifest` to place JSON under a run or artifact
directory. Git data is read at call time; a missing commit remains `null` rather
than being fabricated.

## Acceptance Criteria

- [x] Existing environment/bootstrap scripts are untouched.
- [x] Python packages are repository-local.
- [x] No real memory provider is installed.
- [x] No secrets are committed or written to manifests.
- [x] `runtime/` is gitignored.
- [x] The reference provider passes the reusable contract workflow.
- [x] Unit and contract tests pass offline.
- [x] Runtime setup is idempotent.
- [x] Jetstream volume handling is non-destructive.
- [x] Phase 01 and Phase 02 handoff documentation exist.
- [x] Phase 01 work is isolated on `phase-01-memlife-bootstrap`.

## Known Limitations

- No real provider adapter or provider SDK exists in Phase 01.
- The reference provider is process-local and intentionally non-durable.
- Query behavior is deterministic substring matching, not semantic retrieval.
- Lifecycle states are data vocabulary only; no authorization or enforcement
  policy has been implemented.
- Manifest generation is a library mechanism, not a full experiment runner.

## Git Trace

- Branch: `phase-01-memlife-bootstrap`
- Preserved base: `8a6a364` — `docs: add AGENTS.md guidelines and ignore .local/ context directory`
- `b539c08` — `chore: scaffold MemLife-NLIP phase 1 structure`
- `8669341` — `feat: add provider-independent memory adapter contract`
- `8006101` — `test: add phase 1 reference provider and contract validation`
- Test command: `.venv\Scripts\python.exe -m pytest -q`
- Result: `9 passed`

The documentation commit and full immutable SHAs are available in the branch
history and final execution report.

## Phase 02 Handoff

Phase 02 may begin only after review of this branch. Its first integration target
is Mem0 using the existing adapter surface and reusable lifecycle smoke workflow.
The exact SDK version, configuration hash, observed capability differences, and
runtime manifest must be captured without weakening or silently emulating the
provider's behavior. See [PHASE_02_PROVIDER_BRINGUP.md](PHASE_02_PROVIDER_BRINGUP.md).
