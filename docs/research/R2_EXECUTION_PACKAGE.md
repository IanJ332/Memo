# R2 local-native execution package — offline preparation

**PROSPECTIVE / NOT EXECUTED. No execution authority is supplied here.**
The owner-authorized recovery task resumes from reviewed main
`bc69a8edffb95a846473ea0c475474d62787f37b`. It preserves the
[accepted R2 candidate](../../manifests/r2-lifecycle-candidate-v1.json), SHA-256
`518a7ae2ed953663f774a3d17d5f95908b20a63e080245e302010f47db6bd33d`,
and [scenario](../../src/memlife/r2.py), SHA-256
`0fcc528b072fc9f012a6ef2ba895cf5f1a9dca15b20f758ab6f0e900bcb888ef`.
R0, both sealed R1 attempts and all historical freezes remain unchanged.

## Resource recovery and prospective bounds

Read-only inspection of `desktop-linux` at the local Unix socket found Docker
28.5.2, **12,536,020,992 bytes effective VM RAM**, 16 CPUs, memory/PID enforcement
support, the exact qualified Linux amd64 image, ample working disk and no running
containers. Capacity above the 8 GiB ceiling is **3,946,086,400 bytes**; above the
9 GiB initial admission threshold it is **2,872,344,576 bytes**. The original
8,215,871,488-byte allocation is no longer effective. No Docker setting changed
in this task. Capacity is distinct from free RAM and measured R2 peak use.

The versioned [execution contract](../../manifests/r2-execution-contract-v1.json)
retains 2 CPUs, **8 GiB RAM**, 256 PIDs, 1 GiB tmpfs, one container at a time and
a 5 GiB working allowance. It preserves the historical qualified combined
memory-plus-swap ceiling of 16 GiB (at most 8 GiB additional swap); this neither
promises available swap nor measures use. Admission requires at least 9 GiB
effective VM capacity, 5 GiB free disk, working resource controls and no competing
running container. It rejects inadequate capacity rather than lowering limits.

Each process has a 300-second deadline beginning before Docker start; the whole
execution has 1,200 seconds, followed by at most 120 seconds for owned cleanup.
The owner's eventual absolute stop time bounds both. Docker commands have a
20-second maximum further bounded by remaining time. Rechecking hashes consumes
execution time; it does not extend the deadline. SDK boundary ceilings are
unchanged: add 4, update 1, delete 1, get 19, get_all 36, search 6, history 12,
**79 total**, zero retries. No actual consumption is asserted.

## Minimal qualified integration

[R2 supervisor/worker](../../src/memlife/r2_execution.py) adapts the existing
qualified A3 caller's create/inspect/start/closeout pattern without importing or
invoking historical fixed-path callers. It reuses the unchanged Mem0 adapter,
`NativeLifecycleCapture`, `CapturedMem0SDK`, `ResearchCapture` and artifact writer.
Accepted Tier C/R1 execution files and the R2 scenario are untouched.

Preparation verifies the accepted 111-file source pinset and original runtime
RECORD/model identities before freezing current bytes. Source capsules contain
only the verified source closure, with exact file/directory membership; runtime
and local model trees have complete literal membership/hash/link maps. A fresh
package binds those maps, exact protocol/configuration, image, Docker client,
local endpoint, unique execution identity and exclusive future output path.
No dependency installation, resolution or download occurs. Original caches stay
in place. Python uses an empty tmpfs bytecode-cache prefix rather than existing
unhashed `.pyc` files.

Four distinct full Docker IDs execute UPDATE initial/reopen then DELETE
initial/reopen. Host inspect receipts verify command, user, environment, exact
mounts, image, containment and resources before start. The worker also verifies
its actual container hostname and package binding. Before the next process,
the host fixes each completed seal hash and source/runtime/protocol binding in
a durable completion receipt. Supervisor receipts and preceding phase evidence
are read-only in the worker. Reopen uses that exact predecessor/initial seal,
original physical store paths and byte-identical closed persistent state.

Network-disabled containers, read-only root/source/runtime/model mounts, dropped
capabilities, no-new-privileges and no mounted credentials precede provider
construction. Python denies network/process dispatch before provider imports;
the qualified OpenAI LLM class's generator is denied before Mem0 construction.
The accepted scenario adds its own factory/phase audit guard. Local embeddings
and telemetry/offline settings are retained. Package JSON is mounted alone;
owner grants and human/external approval provenance stay host-only.

SDK reservations are durable before native delegation, including failed calls.
Completed phase verification cross-checks reservation methods against literal
captured SDK input files. Raw returns/exceptions, persistent snapshots, native
candidate ranks/scores/scope and exact selected context retain separate custody.
History is distinct from live-record availability. OBSERVED_MATCH,
OBSERVED_MISMATCH and UNKNOWN semantics remain those of the accepted scenario.

Exceptions halt without replacing stores or retrying phases. An uncertain create
is resolved only by its pre-bound exact owned name/labels, never by recreating it.
Before any removal, timestamped merged Docker stdout/stderr bytes are read under
time/disk bounds, durably written and hash-bound. Retrieval failure retains the
stopped owned container and original stores, preserves partial console bytes,
and marks cleanup incomplete rather than discarding remaining console evidence.
After verified process closure/removal, successful or partial evidence and owned
store bytes are copied, verified and sealed before store deletion. Ownership,
snapshot or deadline uncertainty retains bytes and records incomplete cleanup.
No unrelated container, cache, volume or protected device is touched.

## Review and authorization boundary

The [CLI](../../scripts/research/r2_execution.py) provides `verify-package`, a
separately gated future `execute`, and an inspected-container `worker` command.
Only offline verification is invoked in this task. `execute` requires the exact
accepted independent package-review receipt and an approved, exact-scope,
time-bounded owner grant. Preparation emits a prospective grant only after
package review, with `approved: false` and all human provenance, authorization
timestamps, execution window and external-approval reference unset.

Review and grant JSON do not prove human authorization or external acceptance.
Before future execution, obtain a direct owner grant for the complete dependent
local-native scope and submit that scope/provenance through the supported
system/sandbox/tool approval mechanism wherever required. Inspection approval
from this task supplies no execution authority. Preserve any denial; do not
route around it or reopen R1. No Qwen, hosted model, SSH, Jetstream, protected
dispatch or provider-internal LLM is in this package's allowed scope.

## Offline qualification and private artifacts

Focused tests combine the unchanged 28 accepted R2 scenario controls with new
synthetic resource, source/runtime drift, capture-budget, supervisor, no-replay,
cleanup, time and review/grant admission controls. Docker/LLM/session doubles are
explicitly synthetic and provide no native runtime observation. Actual native
worker import/construction/SDK execution is **NOT EXECUTED** under this task's
scope; no private integration pass is inferred. R0/R1 scientific reviews and
unrelated regressions are not repeated for this isolated wrapper.

The final byte-bound independent review must inspect the actual prospective
package and complete source/runtime maps, independently rerun focused controls
and accept the exact bytes before the grant template is generated. Earlier
blocker-report acceptance is not reused. Exact package, review and grant paths/
hashes are recorded in the private preparation closeout and final owner report;
they are excluded from public GitHub. These offline results establish package
review readiness, not scientific completion or native-worker qualification.
