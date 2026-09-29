# Phase 05A — OpenViking Integration Preparation

## Why OpenViking

OpenViking 0.4.22 provides session-first ingestion, asynchronous extraction,
filesystem content, a separate vector index, auditable memory diffs, and
persistent reconstruction. These boundaries provide new RQ1/RQ2 observability
without running the final experiment matrix.

## Verified Version

The current stable release was verified as `openviking==0.4.22`, released
2026-09-28, tag `v0.4.22`, commit
`e8716760934d95ef73414484a45bfe475b9296e2`, Python >=3.10. The current
standalone SDK is `openviking-sdk==0.1.12` (Python >=3.8). The full evidence and
source links are in [the provider freeze](../providers/OPENVIKING.md).

## Distribution / Deployment Model

The future design uses the full package only in
`<MEMLIFE_DATA_ROOT>/venvs/openviking-0.4.22`, launched with
`openviking-server` on `127.0.0.1:1933`. The MemLife harness uses a small direct
HTTP transport and does not co-install OpenViking, Mem0, or Hindsight provider
dependencies.

## Session Lifecycle

A normalized write creates an isolated adapter-owned session, adds one user
message, commits it, waits for the provider task to complete, then reads the
archive's `memory_diff.json`. The commit archive is the preserved source
surface; extracted files are derived provider memories.

## Async Processing

The adapter polls provider task status until `completed`, fails on
`failed`/`cancelled`/unknown status, and raises after a bounded timeout. It
records task ID, submitted/completed timestamps, status, and elapsed
quiescence time. No fixed delay establishes correctness.

## Memory Extraction Pipeline

Current extraction uses VLM candidate generation, vector pre-filtering, VLM
dedup/reconciliation, AGFS writes, and vectorization. Internal create,
merge, and delete decisions are not reclassified as external lifecycle APIs.

## Storage Architecture

AGFS holds authoritative L0/L1/L2 content and session archives; the local
vector backend stores indexes and references. Both live under one persistent
workspace in the prepared deployment. The model cache and run artifacts are
also on the persistent volume.

## Memory Surfaces

Committed messages map to `SOURCE`; archive abstracts/overviews to `SUMMARY`;
profile extraction to `PROFILE`; other extracted memory files to `DERIVED`;
vector records to `VECTOR_INDEX`; and `find` candidates to `RETRIEVAL`.
Unobserved structures remain `UNKNOWN`.

## Retrieval Surfaces

Direct `find` is selected over `search` or the deprecated `recall` preset. It
does not use query-planner intent analysis and returns identifiable URIs. The
adapter scopes results to correlated memory URIs for the current benchmark
namespace.

## Lifecycle Capability Mapping

| Scenario/capability | Preparation classification | Exact mapping |
| --- | --- | --- |
| baseline | needs mapping | session write is supported; exact extraction/content identity needs live qualification |
| correction/update | unsupported | no external canonical update mapping; internal diff update is not substituted |
| supersession | unsupported | no explicit replacement or `SUPERSEDES` relation |
| revocation | unsupported | no native revoke/invalidate/disable/tombstone |
| delete + restart | needs mapping | delete all diff-correlated memory URIs, restart service with the same workspace, then direct find |
| inspect/audit | supported | content reads plus commit memory diff |
| trigger derivation | supported provider helper | session extract endpoint, distinct from commit task |

`DELETE_OR_INVALIDATE` remains a combined generic capability in Phase 03. The
adapter declares it supported because delete is real, then rejects a requested
`REVOKED` disposition explicitly.

## Memory Diff / Audit Semantics

The parser validates adds, updates, deletes, skipped operations, archive URI,
and extraction timestamp. The adapter retains all provider memory URIs for one
source event. It never selects one result merely to satisfy a one-record
interface.

## Provenance Mapping

Directly observed edges and IDs are source event, session, archive, task,
completed status, diff operation, provider URI, and retrieval URI. A diff gives
known operation correlation at commit granularity. Fine-grained semantic
extraction lineage remains unknown. Trace metadata is credential-free and
passes the existing recursive sensitive-key validator.

## Restart vs Session Reset

Restart replaces the exact PID-owned server process and keeps workspace,
vector index, archive, tasks, venv, and cache. Reset deletes only
adapter-prefixed sessions. The two operations are never treated as synonyms.

## Model Dependencies

Summaries, extraction, and reconciliation require a compatible VLM. The
service supports documented OpenAI-compatible configuration, but no course
model was chosen or called in Phase 05A. Future execution requires explicit
provider/model/base URL values and must validate structured extraction first.

## Embedding Dependencies

Indexing and `find` require embeddings. The current server documents a built-in
local dense default, plus remote/local-compatible alternatives. Course chat
endpoints are not assumed to implement embeddings. The future tiny probe must
validate the built-in local path on CPU before the canonical run.

## Jetstream Feasibility

The target's Python 3.12 and Ubuntu x86-64 satisfy the release metadata and
prebuilt `manylinux_2_31` ABI3 wheel. The 28.8 MB main wheel avoids a Rust source
build. A small single-service run is plausible within about 5.78 GiB RAM, but
local embedding and VLM compatibility remain explicit live gates. Root disk is
protected; provider venv/state/cache/runs live beneath the dynamically resolved
volume mount. GPU/CUDA dependencies are rejected.

## Adapter Design

`src/memlife/adapters/openviking.py` contains the direct transport, task waiter,
memory-diff parser, lifecycle adapter, sanitized trace hooks, and configuration
freeze. `tests/fakes/openviking.py` models the documented REST shapes. The
normalized write ID is a MemLife source-event ID; provider memory URIs remain a
separate one-to-many correlation.

## Unsupported Semantics

Update, supersession, and revocation are explicit `UNSUPPORTED` results. No
text similarity creates lineage. Internal dedup deletes do not prove external
deletion or revocation semantics.

## Future Live Validation Plan

`scripts/jetstream/phase05_openviking.py` and
`phase05_openviking_remote.sh` are prepared but were not run. They are gated by
`MEMLIFE_AUTHORIZE_PHASE05_LIVE=YES`, exact Git synchronization, a mode-400 or
mode-600 Git-ignored `.local/phase05_openviking.env` containing future VLM
configuration, persistent-volume paths, disk checks, dependency checks,
loopback binding, run-owned PID control, provider-reported task completion,
persistence restart, a single canonical/provenance pass, and managed cleanup.
The controller reuses the existing rule: delete only an owned FIP and shelve
only a VM opened by the run.

## RQ1 / RQ2 Value

The trace can distinguish archive success, extraction-task failure, audit-diff
mutation, AGFS state, vector/retrieval visibility, and post-restart behavior.
This supports localization of residual or resurrected state rather than a
single opaque pass/fail result.

## Non-Claims

Jetstream remained shelved. OpenViking was not installed or started. Hosted
model calls, the canonical experiment matrix, RQ3, and final RQ4 evaluation
were not run. The live feasibility and provider semantics remain candidates
until one separately authorized controlled Phase 05 execution.
