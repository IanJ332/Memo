# R2 native-only execution preparation — 2026-10-25

**BLOCKED at the required resource-feasibility gate. NOT EXECUTED.**
Starting local HEAD and read-only verified GitHub main were
`376ad2be1d7ed74a440baf38888485cc15fbb96d`. The owner authorized offline package
preparation and read-only environment checks. The request explicitly requires:
"If resource feasibility cannot be established, report BLOCKED and do not
prepare an execution-ready package."

## Actual resource findings

Read-only Docker inspection succeeded through the supported sandbox approval
mechanism. Initial sandbox socket denial was a local inspection restriction,
not evidence that the daemon was down. No container was created or started.

| Check | Observed result |
| --- | --- |
| Local daemon | Docker 28.5.2, available |
| Effective Docker VM memory | **8,215,871,488 bytes = approximately 7.65 GiB** |
| Candidate container memory ceiling | **8,589,934,592 bytes = 8 GiB** |
| Capacity shortfall before other VM overhead | **374,063,104 bytes**, approximately 356.73 MiB |
| CPUs | Docker reports 16; host reports 16 logical CPUs; candidate requests 2 |
| Host physical RAM | 17,179,869,184 bytes = 16 GiB; not Docker capacity |
| Free local working filesystem | 653,885,890,560 bytes, approximately 609 GiB at inspection; exceeds proposed 5 GiB working allowance |
| Resource controls | Daemon reports memory and PID limit support |
| Qualified image | Exact image ID below is present, Linux amd64, 45,389,175 bytes |
| Docker Desktop settings file | Content read did not complete; inspection was interrupted; configured allocation remains unverified |

Daemon `MemTotal` is effective VM memory, not measured free headroom or R2 peak
consumption. The settings-file limitation does not change the observed shortfall.
No Docker settings were changed. An accepted `--memory 8g` create argument would
not establish that the daemon can supply an 8 GiB ceiling. No such create probe
was performed.

## Memory decision

**Retain the accepted candidate unchanged; do not silently lower its limit.**
The retained qualification and A3 pilot caller/exit receipts configure 8 GiB and
record successful historical exits without OOM termination. They do not provide
a measured peak or establish a smaller independently enforceable bound. In
particular, `OOMKilled=false`, artifact sizes, small fixture counts and successful
embedding imports cannot justify a 7 GiB or other reduced limit. Historical swap
settings also cannot establish RAM capacity or a measured working set.

No smallest scientifically supported reduced ceiling was established from the
retained evidence inspected. Resource feasibility therefore remains BLOCKED.
Changing Docker Desktop allocation is outside this read-only task. A separately
authorized infrastructure correction followed by read-only re-verification could
retain the existing 8 GiB proposal; effective capacity and VM headroom would still
need review. Alternatively, genuinely qualified evidence for a versioned reduced
ceiling would need independent review before any contract change. Neither path
is implemented or authorized here; no new native resource measurement was run.

## Retained identities and offline checks

The qualified runtime/cache exists in the retained private checkout. A read-only
byte verification checked all **82 acquired artifacts (71 wheels and 11 model
files)** against the original acquisition plan using SHA-256 or original Git
blob identity as recorded. All **27,613 hashed installed RECORD entries** and
the original distribution METADATA/RECORD identities matched. These file checks
do not import the Linux runtime or establish current runtime behavior.

The existing `verify-design --qualified-root` command matched all **111 accepted
source pins**, bundle SHA-256
`f7842d164cbeee646a61a6cdc98c63dc010b75f64aef29946e0976a3ed07d384`.
No Tier C, R1, adapter, qualified caller, dependency or cache bytes were changed.

| Accepted input | Unchanged identity |
| --- | --- |
| Candidate manifest | `518a7ae2ed953663f774a3d17d5f95908b20a63e080245e302010f47db6bd33d` |
| `src/memlife/r2.py` | `0fcc528b072fc9f012a6ef2ba895cf5f1a9dca15b20f758ab6f0e900bcb888ef` |
| `scripts/research/r2.py` | `236fbedd0bbff05d6191bb365bb085a5c6f2399bd61b50b80560fe84509a9c84` |
| `tests/research/test_r2.py` | `ea027ff816a5d580adf9afc1d8016e39d39cf0d69965c607624c0a41bf31cc70` |
| Qualified image | `sha256:2199a62885a12290dc9c5be3ca0681d367576ab7bf037da120e564723292a2f0` |
| Local embedding revision | `4ca70771034acceecb2e72475f72050fcdde4ddc` |

The accepted R2 synthetic suite was rerun with an existing repository `.venv`,
Python 3.12.8, `-I -B`: **28 passed, zero skipped**. No implementation changes
require R0/R1 regression reruns. Future-wrapper requirements, including actual
resource validation, Docker identity attestation, review/grant admission and
deadlines, were **not implemented or qualified**. Synthetic scenario results
are not native observations or external approval.

## Withheld deliverables and preserved bounds

No fresh execution identity, final execution package/hash, live entrypoint,
package-review receipt or prospective owner grant was prepared. There is no
controller waiting for a receipt. Human approval fields were not populated.
The existing CLI still provides only offline `verify-design`.

The unchanged proposal retains two physically separate stores, four sequential
phases (UPDATE initial/reopen, DELETE initial/reopen), one container at a time,
2 CPUs, 8 GiB RAM, 256 PIDs, 1 GiB tmpfs and approximately 5 GiB free working
disk. Qualified SDK boundary upper bounds remain add 4, update 1, delete 1,
get 19, get_all 36, search 6, history 12: **79 total**, zero retries. These are
proposals and upper bounds, not measured consumption or completed calls.
Execution/cleanup deadlines remain unset because no execution package exists.

A separate independent reviewer checked the resource evidence and final blocker
report. Its byte-bound receipt is retained privately and referenced in the PR
closeout; that is a review of this blocked preparation, **not acceptance of an
execution package**. Private feasibility records, runtime paths and review inputs
remain excluded from the public repository.

Future execution still requires the final exact package's independent acceptance,
a direct execution-specific owner grant, and supported external approval wherever
system/sandbox/tool gates apply to the full dependent local-native scope. The
read-only inspection approval obtained here supplies none of that authority.
No inference about future external acceptance is made. R2 cannot route around a
denied R1 action. R0, both sealed R1 attempts, historical freezes and the accepted
R2 scientific design remain unchanged.

Zero native SDK operations, provider containers, hosted requests, SSH, Jetstream
or protected dispatch occurred. No task-owned live resources were created, so
no provider cleanup was necessary. Qualified caches and unrelated resources were
preserved. Reviewed GitHub synchronization publishes only this blocker record
and navigation updates.
