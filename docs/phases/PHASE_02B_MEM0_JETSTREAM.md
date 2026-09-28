# Phase 02B — Mem0 Jetstream2 Validation

## Objective

Phase 02B attempted to validate the approved Mem0 OSS 2.2.1 Phase 02A
configuration on the `jisheng3` Jetstream2 VM. This was a portability and
reproducibility run, not a provider redesign or security evaluation.

**Status: BLOCKED.** The single authorized managed session reached remote
dependency installation and embedding-model acquisition, then stopped before
the remote test gate because `/home/exouser/Memo/.venv` did not contain
`pytest`. No second VM lifecycle was started.

## Execution Environment

- Target: Jetstream2 instance `jisheng3`
- Verified instance UUID: `5baeeae7-4c29-4903-89fe-2e9df0a8eced`
- Machine class: `m3.small`, 2 vCPU, approximately 5.78 GiB RAM, no GPU
- OS baseline: Ubuntu 24.04.5 LTS
- Remote Python: 3.12.3
- Initial VM state: `SHELVED`
- Final VM state: `SHELVED`
- Temporary floating IP: created by the run, associated, then disassociated and
  deleted by the run; its numeric value was not persisted

The controller reused the Phase 02B-0 instance, identity, floating-IP ownership,
SSH, and cleanup safeguards. Remote work ran as a callback inside the same
managed `try/finally` lifecycle.

## Git Commit Tested

- Branch: `phase-02b-mem0-jetstream`
- Approved base: `b140e204c14bef8b9c72de62c3f22bffe6e3839c`
- Remote-work preparation commit:
  `3be787735a23c3a8853c7ef29251df1dec5538f9`

The remote clone was clean after preserving and locally excluding
`JETSTREAM2_SERVER_CONTEXT.txt`. It fetched the branch and verified the exact
commit before invoking the branch-only remote validation script. The initial
probe records the pre-sync clone state (`main` at `3a19888`); it is not the
commit used by the remote-work script.

## Live Storage Verification

Live `findmnt /dev/sdb` resolved the mount as:

```text
device: /dev/sdb
mount:  /media/volume/jisheng3_volume
size:   approximately 49G
```

The former cached path `/media/volume/sdb` was stale and was not used. The run
derived `MEMLIFE_DATA_ROOT` as:

```text
/media/volume/jisheng3_volume/memlife
```

The final sanitized result was not produced, so root- and volume-free byte
counts and the filesystem type were not transferred locally.

## Dependency Installation

The remote script redirected `PIP_CACHE_DIR`, `HF_HOME`, `TORCH_HOME`, and
`SENTENCE_TRANSFORMERS_HOME` beneath the persistent MemLife model cache. It ran
the provider requirements dry-run, established a CPU-only torch runtime, checked
for installed `nvidia-*` packages, installed the pinned provider requirements,
and reached successful loading of the approved embedding model.

The provider file pins `mem0ai==2.2.1` and
`sentence-transformers==6.1.0`. Exact remote `torch` and `qdrant-client`
versions were printed remotely but were not returned in the failure result, so
they remain unverified rather than inferred.

The blocking omission was that the remote script had not first installed the
pinned `requirements/core.txt`; consequently, the first remote pytest command
failed with `No module named pytest`. The preparation script now installs the
core requirements before the provider stack for a future separately authorized
attempt.

## CPU-Only Embedding Runtime

The installer accepted an existing torch only if `torch.version.cuda is None`;
otherwise it selected official CPU-only `torch==2.7.1+cpu`. It then rejected
the environment if any installed package name began with `nvidia-`, and asserted
both `torch.version.cuda is None` and `torch.cuda.is_available() is False`.
Those gates completed before the model load. No CUDA or NVIDIA runtime was
intentionally installed. The exact resulting torch version was not captured
locally and is therefore reported as unknown.

## Mem0 Configuration

The prepared configuration remained the Phase 02A research configuration:

- Mem0 OSS `Memory`, not hosted `MemoryClient`
- writes with `infer=False`
- telemetry disabled
- Hugging Face `sentence-transformers/paraphrase-MiniLM-L3-v2`
- embedded/local Qdrant, on disk
- SQLite native history
- loopback-only unused LLM placeholder
- no paid API, Mem0 cloud service, chat LLM, or Jetstream hosted LLM

Configuration SHA-256:
`23c068e16db7d4bb90aad7755b997d5a4104c433a4a0083ef43b3506680ff2e8`.

## Persistent Storage Layout

The remote script created the idempotent runtime layout below the live mount:

```text
/media/volume/jisheng3_volume/memlife/
├── providers/mem0/phase-02b/
│   ├── qdrant/
│   ├── history/
│   └── scratch/
├── model_cache/
│   ├── pip/
│   ├── huggingface/
│   └── torch/
├── runs/phase-02b-mem0/
├── logs/
└── artifacts/
```

Provider data and model caches were not placed in Git or under the repository's
root-disk `runtime/` directory. Persistent state was retained after shelving.

## Contract Validation

- Local unit suite before remote work: `30 passed`
- Local contract suite before remote work: `2 passed`
- Local complete suite before remote work: `35 passed`
- Remote provider-independent command:
  `/home/exouser/Memo/.venv/bin/python -m pytest tests/unit tests/contract -q -p no:cacheprovider`
- Remote result: **BLOCKED before collection** because the interpreter had no
  `pytest` module
- Remote Mem0 integration suite: **NOT RUN**

## Native Lifecycle Observations

No remote write, query, update, delete, list, or native-history operation ran.
The session stopped at the test gate. Phase 02A observations must not be
projected onto Jetstream.

## Restart / Reconstruction Result

**NOT RUN.** No claim is made about remote write persistence, post-delete
retrieval, or history visibility after reconstruction.

## Phase 02A vs Phase 02B Comparison

| Dimension | Result | Local Windows Phase 02A | Jetstream Ubuntu Phase 02B |
| --- | --- | --- | --- |
| Python | DIFFERENCE | 3.14.3 | 3.12.3 |
| mem0ai | MATCH | 2.2.1 | pinned 2.2.1 installation completed before blocker |
| sentence-transformers | MATCH | 6.1.0 | pinned 6.1.0 installation and model load completed |
| torch | NOT COMPARABLE | 2.14.0 | exact version not captured |
| qdrant-client | NOT COMPARABLE | 1.19.1 | exact version not captured |
| embedding model | MATCH | `paraphrase-MiniLM-L3-v2` | same model downloaded and loaded |
| infer mode | MATCH (configuration only) | false | configured false; operation not run |
| vector-store mode | MATCH (configuration only) | embedded/local Qdrant | same configured; operation not run |
| history store | MATCH (configuration only) | SQLite | same configured; operation not run |
| write behavior | NOT COMPARABLE | ADD observed | not run |
| query behavior | NOT COMPARABLE | v1/v2 retrieved | not run |
| update ID behavior | NOT COMPARABLE | same UUID | not run |
| update history | NOT COMPARABLE | UPDATE retained | not run |
| delete retrieval | NOT COMPARABLE | absent | not run |
| delete history | NOT COMPARABLE | DELETE retained | not run |
| reconstruction | NOT COMPARABLE | write persisted; deleted value absent | not run |

Overall: **NOT COMPARABLE for provider lifecycle semantics**. Only environment,
storage, configuration, dependency progression, model acquisition, and cleanup
facts were established.

## Reproducibility

The tracked sanitized manifest is
`manifests/phase-02b-mem0-jetstream.json`. Large caches, logs, dry-run reports,
and partial runtime directories remain on the persistent volume. A future run
requires new lifecycle authorization and should use the corrected branch code;
it must not assume the partially installed environment is equivalent to a
completed validation.

## Limitations

- The one authorized lifecycle ended before remote tests.
- Root/volume free-space snapshots and exact remote torch/Qdrant versions were
  not transferred before failure.
- No provider lifecycle or reconstruction observation exists for Jetstream.
- This run says nothing about Mem0 security, universal deletion durability, or
  stale-memory attack behavior.

## Git Trace

- `b140e20` — approved Phase 02B-0 predecessor
- `3be7877` — `chore: prepare Mem0 Jetstream validation`
- Result documentation commit: recorded in the branch history after this file

## Next Phase Handoff

Phase 02 is not complete. With new user authorization, rerun Phase 02B once
using the corrected core-dependency installation and UTF-8 output handling.
Do not start Hindsight, the Memory Authority Gateway, or attack experiments.
