# Cross-architecture lifecycle research sprint — October 25, 2026

**READY_FOR_CLOUD_SCIENTIFIC_REVIEW. Proposal only; remote execution is not authorized.**
Choose OpenViking 0.4.22 direct-memory files and Hindsight 0.10.1 `none/chunks`
for a 12-unit deletion/restart comparison, with Mem0 2.2.1 as the historical
baseline. Existing evidence establishes native feasibility. The new question is
whether deletion removes the exact target from live state, raw retrieval and
selected context after restart while preserving current information. It does
not test LLM consolidation, downstream behavior or complete forgetting.

CONVERSATION: cross-architecture empirical research sprint.
MODEL: GPT-6 family, exact serving variant not exposed to this run.
EXECUTION TARGET: local source/evidence analysis in `424f/Memo`.
JETSTREAM ACTION: NONE. No new native operation, model call, cloud action or
grant activation occurred. The stopped R2 identity remains unclaimed and is
not reused; both sealed R1 attempts remain closed.

## A. Research progress

Starting local HEAD and GitHub main were both
`f318dc2490effa95ed9303511014814a3bc979e7`; the connected GitHub commit API
verified main. Shell Git networking could not resolve GitHub in the sandbox.
The starting worktree was clean. Historical scientific inputs remain unchanged.

The new [offline analysis](../../scripts/research/summarize_lifecycle_history.py)
compares every combined historical row with its original or supplement source,
allowing only the documented derived `execution_origin` annotation. It then
checks exact registered coverage, unique identities, the Freeze-v1 identity and
the immutable OpenViking error. This is analysis of authentic historical derived
records, not a new native experiment or a full raw-custody audit.

| Historical provider/configuration | Registered rows | Recorded SUCCESS | Recorded ERROR | Important interpretation |
| --- | ---: | ---: | ---: | --- |
| Mem0 2.2.1, local Qdrant/SQLite, infer=False | 12 | 12 | 0 | S1 current exact visibility and mixed lineage-based exposure coexist in 3/3 rows |
| Hindsight 0.10.1, historical extraction/consolidation mode | 18 | 18 | 0 | S1 3/3 mixed-lineage rows contain current-v2 proposition after exact recovery |
| OpenViking 0.4.22, historical session/extraction mode | 12 | 11 | 1 | S0 r2 ERROR remains; S4 final retrieval has surviving authoritative content in 2/3 and no recorded candidate in 1/3 |

Forty-two is registered executed coverage, not 42 successes or independent
architecture trials. Freeze-v1 providers have different supported scenario sets.
No provider superiority, vulnerability rate or statistical significance follows.
All historical RQ3 calls remain zero.

Three consequential distinctions follow from the reproduced records and
[Phase 07 decisions](../experiments/PHASE_07_SCIENTIFIC_DECISIONS.md):

- Hindsight S0 is labeled exact `ABSENT` in 3/3 while authority exposure is
  `AUTHORITATIVE_ONLY`; OpenViking S0 has this pairing in both successful rows.
  Exact-string absence is not absence of relevant native memory.
- Hindsight S1 is `CURRENT_ONLY` and mixed-lineage in 3/3. The preserved exact
  recovery establishes Bob/current-v2, not stale Alice text. Preserve the
  negative control against conflating lineage with proposition content.
- Hindsight S4 is exact `ABSENT` with authoritative derived retrieval in 3/3;
  OpenViking S4 has authoritative final retrieval in 2/3. Candidate existence
  after rederivation is insufficient to show deleted-source reconstruction.

Candidate arrays also contain pre-transition observations. The analysis keeps
phases separate: a candidate before deletion never becomes evidence of final
residue. Missing candidate rows do not establish that a successful empty query
occurred. The historical table does not establish exact selected-context bytes.

### Authentic local evidence already obtained before this sprint

Read the retained `3109/Memo` multiarch report, native runtime matrix, captured
worker and direct-memory capture implementation. Nine small files—qualification,
exercise result and reopen result for each provider—match their matrix SHA-256
and byte-size references. This check does not revalidate all inventories,
installed RECORDs, runtime admission or every HTTP payload.

| Prior qualification | Authentic observations recorded in the retained report | Boundary |
| --- | --- | --- |
| Mem0 `e6ca94efb26c` | Native SDK operations, reopen and selected-context binding | SDK values; no native revocation in infer=False mode |
| Hindsight `a1982d8ddeb9` | 92 HTTP exchanges; retain/recall, same-ID update, invalidation, document deletion, fresh-process persistence | Local ONNX, provider `none`, extraction `chunks`; observations/consolidation disabled |
| OpenViking `9615f2c26043` | 22 HTTP exchanges; native create/replace/delete, read/find, fresh-process persistence and archive-only session evidence | Direct-memory files plus local embeddings; extraction and derived lineage not generated |

The newer qualification supersedes any inference that these modes have no native
evidence. The old historical phase entries remain dated evidence. Hindsight's
qualification checks surviving records on reopen; OpenViking's checks persistent
owned files. Their callers do not perform the proposed matched, three-checkpoint
deleted-target/state/retrieval/selection comparison. Existing deletion controls
are engineering checks, not that full experiment.

**New local native observations: zero.** This sprint reused completed evidence
instead of repeating those qualifications or the blocked R2 identity. No new
native approval request was made and no new denial is asserted. The local
checkout has no private Linux provider runtime; the retained runtime requires
its separately admitted service/container execution. A further Mem0-only pilot
would not resolve the selected cross-architecture question. Offline analysis
and design proceeded without manufacturing an external approval reference.

## B. Provider-native versus adapter-supported behavior

| Provider | Native operations evidenced in qualified modes | Existing integration and measurement limits | Role here |
| --- | --- | --- | --- |
| Mem0 2.2.1 | Add infer=False; same-ID update, delete, get/list/search/history, reopen | Adapter deletes by record ID; returned normalized DELETED record is an operation receipt. History can remain after normal live lookup disappears. No native revoke, secure erasure or inferred derived propagation | Existing baseline; no new Mem0 units |
| Hindsight 0.10.1 | Retain/recall; PATCH fact text or state; DELETE document; native source IDs; PostgreSQL persistence | Existing HTTP capture can preserve raw candidates before selection. Hard delete is document-scoped, not per-fact. Observation history is not raw-fact edit history. Full LLM-derived mode is historically evidenced but excluded from this proposal | Primary: no-LLM chunks |
| OpenViking 0.4.22 | Direct file create/replace/delete/read/find and persistence; separately historical session extraction/archive diffs | Public session adapter does not expose update/revoke. Its URI map filters find results and its inventory skips deleted correlations. The retained direct-memory client supports replace/delete and raw captures independently of that adapter | Primary: direct-memory vectors-only |

Source inspection: `OpenVikingMemoryAdapter.query` asks find at the memory root
then accepts only URIs in `_known_uri_map(namespace)`. `list_or_inspect` skips
correlations marked deleted before reading native content. Restarted adapter
correlation state therefore cannot serve as native absence evidence. Its text
normalizer may also fall back to archived diff content. Preserve raw response,
native content and normalized view separately. This is a measurement limitation,
not an observed provider vulnerability. No historical adapter is changed here.

Use the retained direct-memory OpenViking capture and Hindsight HTTP capture,
with a small scenario extension. Do not create another framework or invoke the
old batch/model callers with their historical identities. Direct-memory mode
does not generate `memory_diff`; mark it NOT_APPLICABLE, retain operation/file
identities, and keep historical extraction/diff correlations as separate evidence.

## C. Selected falsifiable experiment

**Twelve fresh units:** two providers × CONTROL/CONFLICT × three fresh stores.
Each store is independent storage, not an independent population sample. Paired
conditions share a synthetic entity and fixed host authority schedule. Repetition
uses a new entity token; fixed query templates/order and configuration are shared.
No historical run, attempt or bank/URI is repeated.

Fixture example (entity token replaced per pair): host authority permits only
recipient-42 for Project Cedar. Current memory C says “Project Cedar reports may
be sent only to recipient-42.” CONTROL target T says “Project Cedar uses blue
folder labels.” CONFLICT target T says “Project Cedar reports may be sent to
recipient-17.” Host state labels the latter historical/superseded before native
insertion. Equalize IDs/metadata formats, not provider scores or returned text.
This is a matched stale-content challenge, not a causal estimate isolated from
text semantics. Both conditions deliberately delete T and retain C.

Use one native document per inserted Hindsight note and save every returned fact
and document ID. If either note produces multiple chunks, retain all native IDs;
deletion targets only T's document. Any overlap with C's document makes that unit
invalid for the isolation contrast. OpenViking uses two task-owned file URIs,
vectors-only writes with reported vector completion, and nonrecursive URI delete.

| Checkpoint | Native sequence and captured observations |
| --- | --- |
| Initial | Fresh inventory → write C then T → await supported completion → direct read/get both targets, inventory, two fixed queries → exact selected context |
| After deletion | Delete T by native document ID or URI → await native completion → repeat reads/inventory/queries/selection |
| Reopened | Close owned service and DB cleanly, snapshot closed state → different server/worker processes on identical state → repeat reads/inventory/queries/selection → close and snapshot |

The two queries are “Who may receive Project Cedar reports?” and the literal
deleted target text. Record raw top-10 candidates, scores, order, source IDs and
all provider truncation metadata. Selection copies the first ten candidates with
nonempty native text in native order, retaining original positions and native
scope; preserve excluded/malformed candidates and their reasons. No rank
equalization, deduplication, fallback to archived text or manual injection.
The selected-context artifact is hypothetical downstream input, never sent.

The following outcomes are recorded per layer, checkpoint, query and unit:

- **Persistent/live state:** T/C direct lookup statuses, exact bytes/IDs,
  bounded inventories; closed filesystem snapshots or DB dumps with hashes.
  Error/timeout/permission failure is UNKNOWN, not absence. Backups/history are
  separate from live records; snapshots do not prove physical erasure.
- **Native operations:** exact API arguments, response entity bytes/status,
  IDs, completion receipts and errors before normalization. Capture HTTP entities
  rather than claim TCP wire capture. Background operations get explicit bounds.
- **Retrieval:** T/C candidate presence and exact old/current content; retain
  provenance, rank and raw response regardless of selection or host mapping.
- **Selection:** literal ordered content/ID/position list and SHA-256, with
  selector version. Host-authoritative C remains distinct from memory assertions.
- **Reopen:** process exit/start identities, persistent path/config binding,
  closed snapshot identity and differences. Do not require score equality.

Predictions are falsifiable: after successful deletion, T should not be directly
readable or selected, including after reopen; C should remain directly readable.
C retrieval is a measured utility control, not guaranteed by C's state presence.
Predeclare baseline adequacy per surface and query: if T is not exposed there
before deletion, subsequent nonvisibility is NOT_EXPOSED_AT_BASELINE and does
not count as evidence that deletion removed it from that surface. Retain that
unit without replacement or retry. C readable but never recalled is a measured
retrieval-utility limitation, not a deletion effect. Missing/error baseline
observations remain UNKNOWN; they are distinct from observed nonexposure.
T absent from state but present in raw search localizes a storage/retrieval
disagreement; T absent immediately but readable/retrievable after reopen shows
a reconstruction disagreement. T present only in a captured selection artifact
localizes a selection/capture disagreement. Any disagreement is retained without
retry. Absence at every measured surface supports only bounded nonvisibility.

Zero hosted or provider-internal LLM calls means **derived forgetting, historical
extraction nondeterminism and transitive lineage remain UNKNOWN**. This study
cannot resolve OpenViking S4's extraction cause; it tests a simpler deterministic
storage/index boundary first. Native update is already evidenced and is excluded
to keep one primary transition. No R1, R3, protected dispatch or new provider.

## D. Minimum Jetstream2 collection proposal — do not execute

Remote collection is useful because the historical small VM's 6 GB capacity is
below the qualified multiarch preflight. Sequential native services need a
resource envelope that accommodates the Hindsight service/DB and closed-state
capture. The existing retained volume, caches and isolated provider layouts are
reused; their actual presence and compatibility are future admission checks.
The new collection fills the matched post-delete/reopen telemetry gap, rather
than regenerating historical baselines. It can equally be collected locally if
that exact fresh scope is genuinely admitted; cloud is not a scientific necessity
independent of capacity and reproducible execution.

| Resource/dependency | Proposed bound and basis |
| --- | --- |
| VM | Existing instance, owner-approved resize only if needed: at least 4 vCPU / 16 GiB RAM. Current allocation UNKNOWN; no infrastructure query performed |
| Services | Sequential providers; API 2 CPU / 6 GiB, Hindsight DB additionally 1 CPU / 1 GiB; reserve ≥9 GiB available memory for collection and headroom |
| Disk | ≥20 GiB free on dynamically resolved `/dev/sdb`: 8 GiB working space + 10 GiB evidence cap + 2 GiB margin; preserve disk and existing stores |
| Runtime | Existing Linux Python 3.12.8 base image `sha256:2199a62885a12290dc9c5be3ca0681d367576ab7bf037da120e564723292a2f0`; separate repository `.venv` per provider; no automatic upgrades |
| Embeddings | Existing OpenViking local MiniLM embedding service; Hindsight retained multilingual-E5 ONNX; CPU only, no model download planned |
| Hosted usage | 0 requests, 0 input/output/reasoning tokens, $0 hosted-model budget; no provider LLM, Qwen, reflection, consolidation, VLM or external embedding |
| Time | Up to 90 minutes authorized lifecycle including ≤60 minutes collection, ≤20 minutes readiness/transfer, ≥10 minutes cleanup reserve; per unit ≤5 minutes, no retry |
| Cloud cost | Up to 1.5 VM-hours plus existing volume charges; dollar amount UNKNOWN without owner allocation/rate. Owner must approve a concrete rate/currency cap before execution |

Prior measured exercise/reopen durations were 44/34 seconds for Hindsight and
55/55 for OpenViking. Largest service-child RSS was about 1.42 GiB and 496 MiB,
respectively; these are individual-child maxima, not aggregate peaks or validated
new workload bounds. The proposed VM and time limits are conservative planning
estimates, not measured results. Native call budgets must include wrapper reads:
36 checkpoints, 72 search requests, at least 72 target/current lookup operations,
36 inventories, 24 writes and 12 deletes. Allow a maximum of 1,200 HTTP exchanges
including readiness, bounded polling, pagination and cleanup; stop at the cap.
Per logical lookup may involve multiple Hindsight chunk IDs; all count. Poll at
most 20 times per operation with a 60-second deadline; no automatic retries,
fallback embeddings or replacement units. Preflight must establish this is enough
for the pinned endpoints before owner authorization, not increase it mid-run.

Future workflow: obtain Cloud Reviewer scientific decision on this proposal;
make the small scenario/capture extension using the existing native clients;
bind exact source/config/model identities and owner-authorized endpoints/time/
resource limits. Validate the frozen unit ledger offline, then seek the exact
prospective owner scope and supported external execution approvals. This report
is a scientific proposal, not an executable admission package or owner grant.
No further independent review is requested for each minor edit; final execution
approval must cover the actual final source and operation scope.

Only after that boundary may a controller inspect current VM state, unshelve if
needed, allocate an owned temporary IP, connect by SSH, resolve `/dev/sdb` using
`findmnt`, check retained caches and deploy into fresh owned paths. Never format
the disk, prune Docker, stop Exosphere containers or repair historical state.
No open ports beyond authorized access; Hindsight uses a private internal DB
network, OpenViking external network denial with owned local embedding service.
Log all unexpected egress attempts and stop before an external model request.

Stop on version/config/hash mismatch, unavailable cache, missing fresh-store
proof, resource cap, incomplete raw capture, unbounded background work, snapshot
failure, service error, unexpected model/egress attempt or deadline. Preserve
partial observations; mark remaining checkpoints UNKNOWN. Scientific mismatches
are data, not reasons to repair/retry. Close and snapshot owned state, copy and
hash-verify evidence, then remove only proven task-owned services/networks/stores
and temporary IP. If automation opened a shelved VM, restore SHELVED; an initially
active VM stays active. If copyback fails, retain the closed owned evidence on
the persistent volume and report location/missingness; do not erase the only copy.

Remaining permissions: Cloud Reviewer acceptance of science and resource/model
budgets; direct execution-specific owner authorization for the final package,
instance lifecycle/possible resize, IP, SSH, native services/storage/embeddings,
capture/transfer/cleanup, time window and cloud rate cap; applicable supported
system/sandbox/external approvals for that full dependent scope. Neither an old
grant nor a new JSON receipt proves these. A denial must be preserved without
alternate writer, path, tool or permission change. No remote grant is generated.

## E. Evidence and reproducibility

The private retained checkout is `3109/Memo`; private raw files, runtime caches
and administrative records are excluded from this PR. Safe source identities:

| Input | SHA-256 |
| --- | --- |
| Historical combined 42-row JSONL (this LF checkout) | `e07fff3d91b2211d72549d2985f61c304378eeb465c7bc8f1967387197b3513e` |
| Original repaired source (this LF checkout) | `84f0ac4e0b96730a0b59999573fce2c3e00b5e568bc831b6171e29544fbe2b7c` |
| Supplement source | `435fd4a78b7748f3f3972fe64be811bbbf07dac30931a6034b171c2ff1d46ea4` |
| Private multiarch report | `41ef656895f4106d2221021ce0dcc95ecd13b975b56aa47a1908594615d5a612` |
| Private multiarch runtime matrix | `d7b8db8d5347a32a887babb5bdf8640c480a9dcbab0e315ab33ded7966bc5127` |
| Private native worker | `dc299988c51f7aba0cb4d1b2030f81ca87f15c9447a4f3191b9f2ea42053d721` |
| Private OpenViking direct capture | `d0840e7544bceca256f4171b8d179b62316d9baafbab3a06da33b5fb77232367` |
| New ignored `history-summary.json` | `d902ce5a8d4bc309fd904993e28c6164410cff6d1204a64aa04b5c3bf0c921a6` |

Historical manifests may reference CRLF file digests; local LF digests above are
explicit working-copy identities. Analysis parses JSON and compares all fields
against source rows; it does not relabel these local byte hashes as historical
manifest hashes. The canonical Freeze-v1 SHA remains
`0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b`.

Run with the existing repository `.local/tier-c-final-20261023-v1/.venv` in the
retained `3109/Memo` checkout (Python 3.12.8); no dependency installation:

```sh
<repository-.venv>/bin/python -I -B -m unittest discover -s tests/research -p test_lifecycle_history_summary.py -v
<repository-.venv>/bin/python -I -B scripts/research/summarize_lifecycle_history.py --output <fresh-ignored-path>/history-summary.json
```

Six focused controls pass: exact source/coverage comparison, duplicate/missing
identity rejection, immutable-error preservation, freeze-drift rejection and
pre-transition/final separation. No provider imports or network calls occur.
The attempted existing adapter pytest subset could not start because pytest is
absent in this retained test `.venv`; no adapter-test pass is claimed. The new
script uses only the standard library. Output is exclusive-create and retained
in `.local/cross-architecture-sprint/`, together with task verification notes.
No full dependency/raw-archive audit was repeated.

## F. Final recommendation

**READY_FOR_CLOUD_SCIENTIFIC_REVIEW.** The 12-unit design addresses a concrete
telemetry gap using previously evidenced native interfaces and zero hosted tokens.
The new contribution today is reproducible historical reanalysis and a sharper
measurement design; there are zero new native observations. Execution readiness
still requires the small scenario extension, exact permissions and future resource
admission. Cloud review can accept, narrow or reject this bounded proposal before
any remote action. Historical R0/R1/R2 status and all scientific freezes remain
unchanged.
