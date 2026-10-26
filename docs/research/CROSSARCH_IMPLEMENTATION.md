# LC12 implementation and final remote collection handoff

**Implementation complete; BLOCKED for the existing m3.small target.**
The approved 12-unit design is implemented. Retained resource evidence does not
admit the unchanged sequential Hindsight service/DB configuration on approximately
6 GB RAM. No provider, Jetstream, SSH, floating IP, deployment or hosted inference
was executed. This is the engineering deliverable, not another scientific review.

CONVERSATION: accepted cross-architecture experiment implementation.
MODEL: GPT-6 family; exact serving variant unavailable.
EXECUTION TARGET: local source and synthetic fixture tests.
JETSTREAM ACTION: NONE.

## Implementation and entrypoint

- [Scenario and native mappings](../../src/memlife/crossarch.py): native writes,
  document/URI delete, direct lookups, bounded inventory/polling, raw search,
  literal selection, baseline adequacy and partial observations.
- [Entrypoint](../../scripts/research/crossarch.py): offline `ledger` and
  `resource-check`; separately authorized `collect`; internal service/worker
  processes run in owned containers and are not invoked by offline tests.
- [Sequential supervisor](../../scripts/research/crossarch_host.py): fresh stores,
  owned services/DB, close/snapshot/reopen, deadlines and exact owned cleanup.
- [Exact unit ledger](../../manifests/crossarch-units-v1.json) and
  [retained source identities](../../manifests/crossarch-qualified-reuse-v1.json).
- [Non-executable placeholder configuration](../../configs/crossarch-collection.example.json).
  Fill actual retained local paths and a fresh lowercase run ID only after the
  remote Go decision. The example is not a grant or a source of authority.

```sh
.venv/bin/python -I -B scripts/research/crossarch.py ledger
.venv/bin/python -I -B scripts/research/crossarch.py resource-check \
  --cpus 2 --ram-bytes 6442450944 --free-bytes 21474836480
```

Future authorized entrypoint on the collection host:

```sh
<repository-.venv>/bin/python -I -B scripts/research/crossarch.py collect --config <private-config.json>
```

This command manages local Docker only. It contains no SSH/cloud lifecycle or
owner-grant generator. The current instruction authorizes implementation and
offline tests, not invoking collect. Retained qualified Linux `.venv` trees,
models and cached exact image identities must exist; no runtime/model download,
installation, image pull or version upgrade is performed by collection.

## Exact execution ledger

Each ID has **initial → post-delete → post-reopen**, 36 checkpoints total.
The host runs initial/write/delete in one owned API container, waits for exit,
captures closed state, then starts a distinct API container on the same state.
Hindsight also stops its owned PostgreSQL instance for the initial snapshot and
restarts it before reopening. Every unit uses fresh physical state.

| Provider / condition | Repetition 1 | Repetition 2 | Repetition 3 |
| --- | --- | --- | --- |
| OpenViking CONTROL | LC12-OV-CONTROL-r1 | LC12-OV-CONTROL-r2 | LC12-OV-CONTROL-r3 |
| OpenViking CONFLICT | LC12-OV-CONFLICT-r1 | LC12-OV-CONFLICT-r2 | LC12-OV-CONFLICT-r3 |
| Hindsight CONTROL | LC12-HS-CONTROL-r1 | LC12-HS-CONTROL-r2 | LC12-HS-CONTROL-r3 |
| Hindsight CONFLICT | LC12-HS-CONFLICT-r1 | LC12-HS-CONFLICT-r2 | LC12-HS-CONFLICT-r3 |

All are NOT_STARTED. A fresh run ID scopes native bank/URI identifiers and the
exclusive output directory. No R1, R2 or Freeze-v1 identity is executed/replaced.
Do not rerun a partially collected run or select a different output parent to
reuse its identity. The owner-approved collection root is fixed for an execution.

## Reuse and evidence

The retained `3109/Memo` source closure supplies the qualified clients and capture
utilities. Twenty-six selected source hashes are checked; historical batch or
qualification callers are never invoked. No private raw evidence is published.

| Reused module | Actual use |
| --- | --- |
| `memlife.batch.openviking_capture.CapturedDirectMemory` | Exact direct-memory request/entity capture; create/delete/read/find, no extraction |
| `memlife.adapters.hindsight.UrllibHindsightTransport` | Pinned retain, fact lookup/list, document delete, operations and recall HTTP routes |
| `memlife.runner.phase08d3.HttpExchangeCapture`, `AttemptArtifactStore` | Raw Hindsight HTTP entities, request/response identities and exclusive writes |
| `memlife.research_collection.ResearchCapture` | Passive native intent/result journals and capture inventories; no model reservation/send |
| `scripts/research/batch_embedding_service.py` | Retained local MiniLM CPU embedding service, only inside the OpenViking owned container |
| `tests.fakes.hindsight.FakeHindsightTransport` | Existing synthetic REST fixture reused in offline tests, extended for bank creation |

Expected Hindsight 404 lookup responses are captured and permit subsequent
observations; other errors stop that unit. This deliberately uses the existing
base transport plus durable HTTP capture rather than resetting a halted qualified
capture wrapper. Native collection of this new scenario has not been qualified
by these synthetic tests. OpenViking's session adapter and correlation filter do
not define the direct-memory candidate or absence views.

Each checkpoint preserves direct current/target lookup results, inventory,
both raw query responses/candidate arrays and literal selected text/IDs/positions.
Selection preserves duplicates/order/whitespace and records exclusions and hash;
it never substitutes archived diff text. Hindsight preserves all fact IDs from
each separate native document. HTTP capture precedes normalization. Failed reads
are UNKNOWN, never absence. Baseline retrieval nonexposure remains explicitly
NOT_EXPOSED_AT_BASELINE. No model receives selected context.

Docker inspect output and exited-service process records provide reopen evidence
independent of client claims. Closed OpenViking state and stopped PostgreSQL data
are archived with byte counts and hashes. Actual native IDs, source copies,
results, raw captures and partial files remain beneath the fresh private output
root. The aggregate result retains earlier observed checkpoints if later work
fails; later checkpoints remain UNKNOWN. Snapshot/transfer uncertainty retains
the only state copy. Incomplete DB volumes/networks are listed for recovery;
cleanup stops/removes only containers with the exact execution label. It never
prunes Docker, alters Exosphere resources, formats a disk or deletes old stores.

## Jetstream m3.small decision and maximum budget

**BLOCKED on retained evidence, without starting or probing Jetstream.** The
qualified Hindsight API has a 6 GiB ceiling and its DB another 1 GiB. Sequential
provider scheduling does not remove the concurrent API/DB requirement. The retained
1.42 GiB largest-child RSS is not an aggregate peak and cannot qualify a lower
cap. Approximately 6 GB instance RAM is insufficient for the unchanged 7 GiB
limits plus headroom. CPU quotas also total 3 CPUs during Hindsight; this runner
requires three available CPUs rather than asserting a new 2-CPU qualification.

| Maximum or gate | Implemented value |
| --- | --- |
| Units/checkpoints | 12 / 36, sequential, no retry/replacement |
| Logical operations | 24 writes, 12 native deletes, 72 searches, 36 inventories, ≥72 lookups; multi-chunk IDs and native polling add HTTP operations |
| Native API/health HTTP hard ceiling | 1,200 boundary intents, including health/polls; counted before delegation, ambiguity consumes an intent. Provider-internal local embedding HTTP is outside this counter; no physical-send total is inferred |
| Docker CLI hard ceiling | 1,000, including up to 240 bounded DB-readiness probes; last 64 reserved for cleanup |
| Background bounds | ≤20 polls/operation; ≤60 seconds for native completion; ≤10 inventory pages |
| Unit / collection | 300 seconds/unit including startup and snapshots; 3,600 seconds collection, cleanup separately bounded |
| Cleanup / overall collection process | 600 seconds cleanup reserve; 4,200 seconds total process deadline |
| Overall remote lifecycle planning cap | 90 minutes including separately managed access/copyback; no cloud controller is added |
| API / DB | API 2 CPU, 6 GiB RAM, 512 PIDs, 1 GiB tmpfs; DB 1 CPU, 1 GiB RAM, 128 PIDs; memory swap ceiling equals RAM |
| Admission | Linux amd64 Docker; ≥3 CPU, ≥9 GiB effective RAM, ≥20 GiB free on dynamically resolved `/dev/sdb` |
| Evidence disk stop threshold | 10 GiB checked before native API/health intents and during streamed snapshot/log copies; partial files retained. This is not an aggregate filesystem quota |
| Hosted/model budget | 0 hosted requests/tokens/dollars; 0 internal LLM, reflection, consolidation or remote embeddings |

The CLI resource check for 2 CPUs / 6 GiB reports BLOCKED. It is an offline
calculation, not a fresh VM capacity measurement. Current Docker/runtime/image
availability on Jetstream remains unobserved. No new infrastructure architecture
or resize operation is implemented. A future Go needs a target satisfying these
retained configured limits, or genuinely measured aggregate evidence and review
supporting a smaller bound; this deliverable makes no smaller-bound claim.

The 1,200 HTTP cap is a hard stop, not a promise that every possible polling path
finishes the matrix. Deadline/cap failures preserve missingness; budgets are never
raised mid-run. Runtime/cache identity drift and unexpected native failures stop
collection. Scientific mismatches remain observations and are not repaired.

**Aggregate physical disk peak is UNKNOWN.** Live service/embedding/worker logs,
Hindsight HTTP reads, checkpoint duplication and finalization can grow between
the 10 GiB checks. Streamed snapshot/log copies enforce their remaining allowance,
but this runner does not impose a filesystem quota on all concurrent writers.
The 20 GiB free-space gate is an admission margin, not a measured peak or strict
maximum disk use. Final remote Go/No-Go must retain this disclosed limitation;
no new storage subsystem or native file-size restriction is introduced.

## Offline validation and GitHub synchronization

In the task-owned repository `.venv`, Python 3.12.8, pinned Pydantic 2.13.5 and
pytest 9.0.2 were installed for offline testing only. No provider packages/models
were installed or executed. `pip check` passes. The first retained test `.venv`
lacked Pydantic; that import failure is not a provider result.

**59 focused tests pass:** 18 new runner controls, 35 existing Hindsight/OpenViking
adapter/contract checks and six historical-analysis regressions. Controls cover
both provider trajectories/reopen using synthetic peers, all twelve identities,
multi-chunk deletion, partial state/HTTP, error-versus-404, ordering/literal text,
baseline nonexposure, finite pagination, intent/time limits and resource rejection
before provider/image actions. A full synthetic Docker supervisor test covers
all twelve units, 24 distinct API containers, 42 monotonic resource intents,
snapshots and cleanup, and rejects an existing same-label resource without
stopping/removing it. Retained interpreter links are validated for the pinned
container target without requiring host resolution. DB readiness respects the
unit deadline. These are synthetic tests, not live observations.

```sh
.venv/bin/python -I -B -m pytest -q -p no:cacheprovider \
  tests/research/test_crossarch.py tests/research/test_lifecycle_history_summary.py \
  tests/unit/test_hindsight_adapter.py tests/unit/test_openviking_adapter.py \
  tests/contract/test_hindsight_provider.py tests/contract/test_openviking_provider.py
```

PR #13 head `231235e11ba5b4a86504cb414bb411f246933c37` was unchanged and normally
merged as **`816c778b8d408ad3e3daa505633b6a640b2b2395`**. The implementation branch
starts at that synchronized main. The single implementation review and merged
implementation commit are recorded in the final PR/task handoff. Raw data,
private configuration, review administration and runtime caches stay out of GitHub.

The single focused independent implementation review checked all 26 retained
source hashes and independently ran all 59 tests. Its supervisor findings were
fixed and rechecked; the reviewer explicitly accepted disclosing the disk check
as a threshold with UNKNOWN aggregate peak for this BLOCKED-target handoff.
The review agent reached its usage limit before issuing a final byte-hash
acceptance receipt. No such receipt is claimed. Scientific design was not
re-reviewed, and no execution approval was supplied by this review.

## Remaining authorization and final verdict

**BLOCKED for m3.small; implementation ready for final remote Go/No-Go review.**
No repeated scientific review is required by this report. Remaining gates are a
resource-admitted target, owner execution-specific permission for exact sources,
fresh run/resources/time/cost scope, and applicable supported external execution
approvals. Remote access, instance lifecycle, temporary IP, deployment, native
collection, evidence transfer and cleanup require that future authorization.
No receipt or config supplies it. Preserve any denial and never route around it.
The runner is implemented; no new preparation phase or broad proposal is requested.
