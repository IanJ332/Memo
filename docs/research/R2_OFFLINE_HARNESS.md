# R2 minimal lifecycle harness — offline candidate

**DRAFT / NOT EXECUTED. Offline engineering only; no native or model observations.**
Based on reviewed main `306e4c56a8ca3e81f51061d114dc068720945189` and the accepted
[research decision](R0_TO_R2_RESEARCH_CONTINUATION.md). R0 and both sealed R1
attempts remain unchanged. This is preparation for a future package review, not
live qualification, an execution identity or an owner grant.

## Exact candidate and source reuse

[Candidate fixture/contract](../../manifests/r2-lifecycle-candidate-v1.json) fixes
literal strings, metadata, principal, trusted host-state schedule, query, native
operation order and resource/SDK ceilings. [Scenario source](../../src/memlife/r2.py)
checks its exact SHA-256. [Offline CLI](../../scripts/research/r2.py) offers only
`verify-design`; it has no provider construction/execution/cleanup command.

The scenario calls an injected session after freshness/reopen checks and an
exclusive claim. `QualifiedSession` wraps the unchanged Mem0 adapter,
`NativeLifecycleCapture`, `attach_mem0_capture` / `CapturedMem0SDK` and
`ResearchCapture` writer/finalizer. It never constructs Mem0. The qualified
adapter itself fixes native `infer=False`, local dense embeddings, Qdrant/SQLite,
same-ID Update and native Delete. No Tier C/R1 source was modified or invoked.

Read-only verification against the retained private checkout matched all 111
existing [accepted source pins](../../manifests/r1-qualified-source-pins-v1.json),
canonical bundle SHA-256
`f7842d164cbeee646a61a6cdc98c63dc010b75f64aef29946e0976a3ed07d384`.
Reusing this pinset is source identity reuse only; it imports no R1 grants,
attempt identities, controller or approval procedure. No historical caller ran.
Private source/runtime contents remain excluded from GitHub.

## Two trajectories and checkpoints

One synthetic scenario; two physically separate stores, **not independent
replications**. Both use target assignment `recipient-17` and the identical
unchanged plain-text-format sentinel. A separate host-authored schedule changes
the authorized recipient to `recipient-42` after baseline in both trajectories.
The DELETE trajectory deliberately retains no replacement assignment memory;
its lifecycle question is live-record absence, not task utility. No memory note
or provider namespace supplies authorization.

Four serial phases: `UPDATE-initial`, `UPDATE-reopen`, `DELETE-initial`,
`DELETE-reopen`. Each later phase requires the exact sealed completed predecessor
and a different process/container identity. Reopen also requires its own initial
phase's seal, exact source/runtime/protocol binding, identical canonical paths and
byte-identical closed state before the future factory may construct a client.
PIDs alone are inadequate; an admitted future supervisor must attest distinct
container IDs, exit, removal, mounts and serialization. This scenario does not
collect or authenticate Docker receipts.

| Phase | Exact scenario order | Registered checkpoints |
| --- | --- | --- |
| UPDATE initial | Inspect empty → Add target → Add sentinel → baseline → Update original target ID to recipient-42 → after → close | baseline, after |
| UPDATE reopen | Verify sealed state → distinct-process reconstruction → reopened → close | reopened |
| DELETE initial | Inspect empty → Add target → Add sentinel → baseline → Delete original target ID → after → close | baseline, after |
| DELETE reopen | Verify sealed state → distinct-process reconstruction → reopened → close | reopened |

Every checkpoint calls, in order: **Get target, Get sentinel, scoped get_all,
Search, history target, history sentinel**. Search fixes the answer-free query,
limit 10, no score threshold. Scoped get_all uses the qualified top_k=1000 over
two registered records. It is bounded inventory evidence, not a claim about an
unbounded namespace or complete provider state.

Get checks ID, namespace, content and fixture metadata; inventory and retrieval
compare live IDs/content and report scope separately. Native history remains a
separate evidence surface. Sentinel metadata and history are also compared across
checkpoints to detect changes beyond the fixture's named fields. Reopen compares
history to the sealed initial result;
ranking, scores and native access times need not be numerically identical.
All raw SDK candidate objects remain preserved; selected context copies every
candidate's exact ID/content/scope in native order. No result is inserted,
reordered, deduplicated or rewritten to force an expected outcome.

## Four evidence layers and scoring

1. Persistent state: native IDs/metadata, scoped inventory, independently copied
   closed Qdrant/SQLite/scratch trees, exact file membership and hashes. Current
   live records are distinct from histories/tombstones.
2. SDK returns: the qualified capture durably writes exact Python API arguments,
   returns and exceptions before adapter normalization. They are not HTTP bytes.
   Lifecycle before/after views and scenario checkpoint references stay linked.
3. Retrieval: complete raw candidate objects, fixed query/scope, scores, ranks,
   observed/missing target and sentinel. Search absence alone is not deletion.
4. Selected context: literal IDs/content/order, selector identity and canonical
   context hash. `MODEL_EXPOSURE=NOT_SENT`, `MODEL_PROPOSAL=NOT_GENERATED`.

Every expectation receives OBSERVED_MATCH / OBSERVED_MISMATCH / UNKNOWN and its
supporting receipt reference. Errors halt that phase without retry; partial reads
remain, unperformed checkpoints remain UNKNOWN. A successful Get returning None
can support live absence; a missing/error Get cannot. A mismatch is retained,
not repaired. `COMPLETED` means collection completed, never all expectations
matched or a security defense succeeded. No single success percentage is produced.

Phase output and store claims are exclusive, including after a crash. Reopen may
not be repeated through a different output directory. Seals hash exact evidence
membership, snapshots and result. Reopen/cleanup reject altered, additional,
symlinked or hardlinked evidence/state files. Cleanup validation returns only
the two exact owned directory candidates after final closed/sealed phases; it
deletes nothing. Future supervision must preserve snapshots before removal and
retain actual container/store cleanup receipts. No generic controller is added.

## Prospective bounds and remaining execution boundary

Use the existing pinned Linux image and 71-wheel/local model closure described
in the accepted decision. Proposed ceilings: two stores, four sequential clients,
one container at a time, **2 CPUs, 8 GiB RAM, 256 PIDs, 1 GiB tmpfs**, approximately
**5 GiB free working disk** beyond existing artifacts. These are proposed bounds,
not measured R2 use. Native objects remain small synthetic fixtures.

| Native SDK method | Maximum calls across four phases |
| --- | ---: |
| add | 4 |
| update | 1 |
| delete | 1 |
| get | 19 |
| get_all | 36 |
| search | 6 |
| history | 12 |
| Total | 79 |

Counts include the unchanged adapter's post-write/pre-mutation Gets and lifecycle
wrapper's before/after inventories, including three get_all calls for initial
INSPECT. Initial UPDATE/DELETE use at most 32/31 calls; each reopen uses eight.
These are SDK boundary calls, not embedding/internal transport attempt telemetry.
No retry, replacement store or rank/score equality is assumed. Errors may leave
fewer observed calls and UNKNOWN later checkpoints. Construction/close are
separate lifecycle events, not added SDK-method observations.

The scenario denies socket activity and subprocess dispatch while the future
factory/phase runs; the qualified bridge denies internal LLM generation. A future
factory must establish Docker `--network none`, telemetry/offline model settings,
read-only source/runtime/model mounts, no credentials and the pre-import network/
LLM guards **before native construction**. The bridge's later guard alone is not
construction governance. Zero Qwen/hosted inference, provider-internal LLM, SSH,
Jetstream, protected dispatch or dependency/model acquisition is permitted.

The CLI verifies source/fixture files only. There is deliberately no live launcher
or grant generator. A future separately reviewed package must supply an admitted
factory that creates the already qualified adapter/capture, actual source/runtime
identity verification, process/resource receipts, time/operation budgets and
owned cleanup. `bindings`/process arguments are equality constraints, not proofs
of approval or attestation. Actual capacity and artifact identities need genuine
independent re-verification before native work; the current task did none.

Require a new direct owner grant for that exact reviewed package/actions/resources/
window and supported external approval wherever applicable. Preserve denials;
never route a denied R1 action through this code. No R1 attempt is reopened, and
no R3 decision/dispatch comparison is implemented.

Scientific limits remain: one synthetic scenario, no population rate, no model
influence or security-effectiveness measure, no native revocation/secure erasure,
no complete derived-memory forgetting or lineage, no native authentication or
host authorization inferred from scope filtering, and no concurrency/crash
recovery qualification. Updating content is not revocation.

## Offline verification and independent review

Run synthetic controls with an existing repository `.venv` only:

```sh
<repository-.venv>/bin/python -I -B -m unittest discover -s tests/research -p test_r2.py -v
<repository-.venv>/bin/python -I -B scripts/research/r2.py verify-design
```

[Tests](../../tests/research/test_r2.py) use explicitly labeled synthetic file
doubles, not Mem0 stores. No Docker, model, provider or external service starts.

Offline verification: **28 R2 controls pass, zero skips** in the existing
repository `.local/tier-c-final-20261023-v1/.venv`, Python 3.12.8, `-I -B`.
The authentic R0 adapter/statistics regressions run on synthetic inputs:
**22 pass**. Unchanged R1 suite: **55 pass, seven skipped**, because its private
Tier C integration fixture prerequisites are absent from this public checkout;
this is not a 62-test integration pass or a qualification promotion. The CLI
independently verifies the candidate bytes and 111 accepted source pins without
importing provider code. Whitespace and local Markdown-link checks also pass.

| Final implementation input | SHA-256 |
| --- | --- |
| `src/memlife/r2.py` | `0fcc528b072fc9f012a6ef2ba895cf5f1a9dca15b20f758ab6f0e900bcb888ef` |
| `scripts/research/r2.py` | `236fbedd0bbff05d6191bb365bb085a5c6f2399bd61b50b80560fe84509a9c84` |
| `manifests/r2-lifecycle-candidate-v1.json` | `518a7ae2ed953663f774a3d17d5f95908b20a63e080245e302010f47db6bd33d` |
| `tests/research/test_r2.py` | `ea027ff816a5d580adf9afc1d8016e39d39cf0d69965c607624c0a41bf31cc70` |

Focused independent reviewer `/root/r2_review` checked scientific semantics,
qualified reuse/79-call accounting, order, persistence/custody, scoring, privacy
and the offline/live boundary. One actionable finding—empty directories were
missing from tree membership—was fixed with focused evidence/state drift controls.
The reviewer independently reran the synthetic suite and source-pin verification.
Final byte-bound acceptance is recorded with the GitHub synchronization; acceptance
is for offline package-review readiness only, not runtime qualification or a
future native execution package/grant.
