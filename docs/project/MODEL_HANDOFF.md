# Model Handoff — Start Here

## Project and research frame

**Project:** MemLife-NLIP

MemLife-NLIP studies cross-provider lifecycle security and authority
enforcement for agent memory systems. The core principle is:

> Retrieved != Authoritative

```text
source event
  -> memory write / derivation
  -> storage / cache / graph / profile
  -> retrieval
  -> authority enforcement
  -> delivered context
  -> LLM
  -> tool / action
```

The contribution is not merely that stale memory can affect an agent. It is
cross-provider authoritative lifecycle semantics, localization of
source/derived-state propagation, and provider-independent lineage-aware
enforcement before LLM reasoning. Model choice is a downstream moderator, not
the main storage-lifecycle experiment.

## Current authoritative state

| Item | State |
| --- | --- |
| Branch | `phase-08d9-stage1-static-derivative`, based on verified merged `main` `523055af834c285ec6608ffa37e15b31ffc4e86b` |
| Published Phase 08A branch | `phase-08-expansion-freeze-v2` at `a17bc7cb05558012992c19bb264fc7a6e18ac06b` |
| Historical Phase 06B baseline | `f88efd1e71a66c39ff4f702baf4231e01e75aa46` |
| Published Phase 07 base | `481f9d698e7e48fe9d3d84868a303ec10aa676ea` |
| Current phase | Phase 08D-9 Stage 1: STATIC PASS; engineered source derivative; independent review pending; runtime/parity unexecuted; D3/D5 PARTIAL, D4 BLOCKED |
| Freeze | `experiment-freeze-v1` |
| Freeze SHA-256 | `0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b` |
| Original attempt | `20261001T183940Z-1fc4c4929532` (42 planned; 32 executed; 31 success; 1 error; 10 never executed) |
| Tested experiment commit | `58e154a62e1c52e6a478e8f0e2041b437023582a` |
| Successful supplement attempt | `20261002T000350Z-c272b34d2cc3`, tested commit `58e154a62e1c52e6a478e8f0e2041b437023582a` |
| Phase 06B coverage | 42 / 42 (42 planned; 42 executed; 41 success; 1 error; 0 never executed combined) |
| Provider coverage | Mem0 12/12; Hindsight 18/18; OpenViking 12/12 |
| Frozen error | OpenViking S0 r2: historical ERROR (`RemoteDisconnected`, then `ServiceExitedBeforeReady`) |
| Error root cause | `UNKNOWN`; classified only as provider process crash |
| Residual cells | Mem0 S1; Hindsight S1; Hindsight S4; OpenViking S4 (OpenViking S0 indexed by repetition disagreement) |
| Phase 07 RQ3 result | NOT ACTIVATED; 0 eligible empirical contexts; 0 calls |
| Freeze v2 | Non-final Phase 08A draft preserved unchanged; its Honcho-plus-Provider-5 schedule is blocked by frozen Honcho `NO_GO`; no live provider accepted |
| Jetstream | `SHELVED`; Candidate10 used one separately authorized lifecycle, which is complete and cleaned up; no new live action is authorized |

The branch base above is the current engineering handoff point. Historical
scientific commits and attempt denominators remain separately recorded; newer
documentation commits do not change them.

## What is complete

- Phases 01–05: provider-independent foundation and three provider bring-ups.
- Phase 06A: calibration and Experiment Freeze v1.
- Phase 06B: partial storage/lifecycle data, preserved without replacement.
- Phase 06B-C: provenance repair passed. The original raw artifact remains
  immutable; the derived artifact adds only the original attempt ID.
- Phase 06B-S2: one authorized managed lifecycle was used. Remote preflight
  blocked before provider startup because the tracked provenance-repaired
  artifact has LF bytes on Linux but its expected SHA-256 is over CRLF bytes.
  Zero supplement runs executed, no service started, RQ3 remained zero, the
  owned floating IP was deleted, and Jetstream returned to `SHELVED`.
- Phase 06B-S2R: local-only canonical Git-source validation now reproduces the
  historical CRLF artifact identity from LF or CRLF checkouts. Derived closure
  records the ten blocked IDs without modifying the attempt, future preflight
  evidence serialization is complete, and lifecycle vocabulary is normalized.
  No scientific row or canonical source artifact changed.
- Phase 06B-S2R2: local repair/validation passed; path-resolution bug (original raw artifact was bound to repo instead of MEMLIFE_DATA_ROOT) and SSH artifact-transfer timeout fragility identified. Published code at 88364966 was live-tested; Jetstream is shelved and provider never started. 10 frozen runs remain never executed. Local repair and validation of the path fix and bounded transfer retries passed; publication pending. No new live retry is authorized.
- Phase 06B-S: 10 runs of OpenViking successfully executed under attempt `20261002T000350Z-c272b34d2cc3`. Combined view derived with 42/42 runs. Jetstream shelved.
- Phase 07: exact Hindsight S1 recovery proved current-v2 proposition content
  with superseded lineage. RQ3 has zero eligible empirical contexts and remains
  unexecuted. The published closure commit is `481f9d698e7e48fe9d3d84868a303ec10aa676ea`.
- Phase 08A: published on `phase-08-expansion-freeze-v2` at
  `a17bc7cb05558012992c19bb264fc7a6e18ac06b`. It defines a non-final Freeze-v2
  draft, future Honcho and RetainDB/Graphiti acceptance gates, strict normalized
  RQ4 evidence models, deterministic validation, and regression coverage. No
  provider, Jetstream, or model execution occurred; Freeze v2 remains draft
  and is not finalized.
- Phase 08B-0: final review passed and the accepted preflight commit
  `7bf35a849987a255252954ac3ea907ee3cad7822` is published. The local-only
  Honcho preflight adds a fail-closed adapter skeleton,
  complete capability and S0-S5 probe plans, raw-evidence and quiescence
  contracts, a future non-executable Phase 08B-1 manifest, and deterministic
  validation. Honcho was not installed or contacted; all capability and
  scenario outcomes remain `UNKNOWN`; model calls of every kind were zero.
  Any future Honcho provider-internal model inference is provider behavior,
  remains separately unauthorized, must be configuration-pinned and counted,
  and cannot act as an authority/security judge or activate RQ3.
- Phase 08B-1 Candidate10: scientific closeout is accepted for attempt
  `20261007T165110Z-19d0ccd6b106`, with the deterministic provider decision
  frozen at `NO_GO`. The 18 capability classifications are 10 `SUPPORTED`,
  4 `UNSUPPORTED`, and 4 `UNKNOWN`. S0 was directly executed; S1 is `UNKNOWN`;
  S2-S5 are capability-derived `UNSUPPORTED`, not direct scenario executions.
  Native Dream quiescence is `UNKNOWN`. The provider made 21 internal calls
  (12 hosted text-generation and 9 local embedding); downstream and RQ3 calls
  were both zero. All 23 completion artifacts and all 95 indexed primary
  evidence files were independently verified. The raw appendix remains local
  and unpublished. The controller's SSH transport failure is distinct from
  scientific completion, and its root cause remains `UNKNOWN`. No security
  exploit was demonstrated. Freeze v1 is unchanged and Freeze v2 remains a
  non-final draft.
- Phase 08B-1 Git publication: the reviewed scientific closeout was originally
  published on `phase-08b1-candidate10-publication` at
  `54c1f7847af582cffc078fbc99aecfaab6b12dc2`. The latest published commit,
  `3c126216f4f5b7ac4f842e344598324c8d6a4097`, completes offline portability
  closure without changing scientific evidence or implementation. The main
  handoff was synchronized at `b1ff61b862a45df41405eb821d3a46318eb66c29`;
  the raw evidence ZIP remains local and unpublished.
  The historical preflight rule, "Phase 08B-1 requires separate authorization,"
  was satisfied for Candidate10 once and does not authorize a rerun or another
  candidate.
- Phase 08C-0: design-only reconciliation preserves the original Freeze-v2
  draft and records that Honcho `NO_GO` blocks its two-provider schedule and
  finalization prerequisites. A static RetainDB Server preview found an exact
  upstream repository and feasible source-commit pinning, but all acceptance
  capabilities remain `UNKNOWN` and acceptance remains
  `PENDING_LIVE_ACCEPTANCE`. The recommended sequence is offline deterministic
  RQ4 mediator implementation first, a separate RetainDB preflight, and no
  separately versioned Freeze-v2 revision until new evidence or an approved
  revised objective warrants one. See
  [`PHASE_08C0_RESEARCH_DESIGN_RECONCILIATION.md`](../experiments/PHASE_08C0_RESEARCH_DESIGN_RECONCILIATION.md).
- Phase 08C-1: the minimal offline exact-identity RQ4 policy passes 19 eligible
  cases (2 provider-observed controls, 9 LongMemEval-derived challenges, and 8
  hand-authored controls) with 0 incorrect ALLOW, 0 incorrect DENY, and 0/11
  non-ALLOW candidate byte strings in delivered context. Hindsight S4 and
  OpenViking S4 remain explicitly ineligible because exact final candidate
  bytes were not preserved. No provider, Jetstream, hosted model, downstream
  model, embedding, or RQ3 call occurred. See
  [`PHASE_08C1_RQ4_MINIMAL_PILOT.md`](../experiments/PHASE_08C1_RQ4_MINIMAL_PILOT.md).

See [`PROJECT_STATE.md`](PROJECT_STATE.md) for the phase map and
[`EXPERIMENT_LEDGER.md`](EXPERIMENT_LEDGER.md) for canonical provenance.

## Next authorized action

### Phase 08D-9 Stage 1 static derivative

Separately authorized Stage 1 produced the exclusive ignored engineered source
`memlife-hindsight-provider-boundary/0.1.0+upstream.f8950b0c07d9`. All 131
originals match the immutable D8 receipt; exactly engine/providers/worker
initializers change, and the other 128 files (including the entire native
provider and real root/helpers) remain byte-identical. Independent static
verification, deterministic rematerialization, immutable output controls and
31 tests PASS under OS network denial. Actual projection: 29 modules/41 packages,
matching the ADR; 19 artifact slots rehashed, 22 missing binary candidates
(4,390,044 bytes). No acquisition, install/build or native/SDK import/execution.
Source manifest SHA-256:
`91bdb4c3cdb28e0879b686ba1bd5448d375c02b51a1e0cd612f120b2f7f4ad72`.
See [Stage 1 report](../experiments/PHASE_08D9_STAGE1_STATIC_PROVIDER_BOUNDARY.md),
[manifest](../../manifests/phase-08d9-provider-boundary-source.json) and
[patch](../../patches/phase-08d9-provider-boundary-bootstrap.patch).

**Next action: independent Stage 1 review; stop after review-branch publication.**
Stage 2 needs explicit exact artifact acquisition/install authority, a new
dependency manifest and exclusive runtime `.venv`; imports/methods/reference
comparison remain later separately authorized stages. Pinned LICENSE bytes are
unavailable; packaging/redistribution needs separate source-byte authority and
provenance first. Inactive sources retained on disk do not authorize their use.
Static success grants no runtime safety, semantic parity or startup promotion.
All Git network operations in Stage 1 use HTTPS; configured SSH was explicitly
replaced and scripts reject SSH/rewrite targets. No infrastructure/Jetstream
action. D4 BLOCKED; D3/D5 PARTIAL; D1/D2, freezes, attempts and denominators intact.

### Phase 08D-9 provider boundary architecture review (historical)

Documentation-only design on `phase-08d9-provider-boundary-design`, base
`16fdb42afd4e1638dba1f2e38cf5cb3e57fdb897`, compares upstream-supported
provider-only packaging (not established at the inspected pin), a three-file
lazy-export refactor, and faithful ordinary import as the reference baseline.
It conditionally recommends the refactor of engine/providers/worker
initializers, preserving all native provider/helper bytes and identifying the
result as a versioned **engineered provider boundary**, never the unmodified
Hindsight runtime. The design specifies provenance, measurable method contracts,
final-request/serialized-attempt admission, containment of unowned clients and
separate reference-parity/readiness gates. No implementation or qualification
occurred. See the
[architecture decision](../experiments/PHASE_08D9_PROVIDER_BOUNDARY_ARCHITECTURE.md).

**Next action: independent design review; stop after documentation publication.**
The prior design-only authorization is satisfied, not permission to implement.
After approval, the exact proposed next authorization is Stage 1 static source
derivative/materializer/manifest work only, limited to the three listed
initializers and unchanged native methods. Acquisition, installation, imports,
native/SDK execution and later method/reference qualification each require their
own explicit scopes. The runtime startup gate stays unconditional; D4 BLOCKED,
D3/D5 PARTIAL. No provider/model/embedding/service/worker/SSH/Jetstream/RQ3 or
empirical action is authorized. D1/D2, freezes, attempts and denominators intact.

### Phase 08D-8 minimal native runtime preparation addendum (historical)

The bounded adaptive continuation from
`d226f7859fae94df0055cda43c5900571b0d66d5` acquired 101 pinned first-party sources
/ 1,692,988 bytes / 101 HTTPS requests (zero failed), under limits 150 files /
3.5 MB / 200 requests. All initial 72 plus 29 newly logged mandatory discoveries
were verified; 131 total source identities and eight static/integrity checks pass.
The mandatory literal graph is resolved at 125 modules. Conditional/deferred/
type-only targets and all dynamic/native/third-party runtime effects remain
unqualified. The mandatory import-root package metadata closure is 61 packages:
24 ready artifact slots, 36 matching-wheel gaps, one locked Intel compatibility
gap (cryptography 50.0.0). Eager Gemini import -> Google GenAI/Auth makes crypto
necessary in this ordinary-import package closure; SDK-only remains separate.
Engineering decision B: propose a separately reviewed genuine provider-only
entrypoint/packaging design with unchanged native methods and explicit parity/
provenance, not unmodified runtime qualification. **Not implemented.** No source
rewriting, initializer bypass, native/SDK execution, installation or gate change.
See the [adaptive receipt](../../manifests/phase-08d8-adaptive-source-closure.json)
and [updated report](../experiments/PHASE_08D8_MINIMAL_NATIVE_RUNTIME_PREPARATION.md).
Stop for independent review. Next authorization is design-only option-B review;
no further acquisition/build/install/source modification/native execution is
authorized by this handoff. D3/D5 PARTIAL, D4 BLOCKED; science/Freeze/D1/D2 unchanged.

The fixed-frontier remaining-source inspection below is historical:

The remaining-source continuation from
`d11a081855b84b85522fde6ad25deeb34a37ceaa` froze the exact 75-file /
1,259,799-byte plan. It acquired and verified db base/ops/result, then reflect's
initializer: four new files / 56,318 bytes. The database bodies are abstraction
definitions with no import-time backend/connection/model startup. Reflect's
initializer unconditionally imports unapproved `engine/reflect/agent.py`, so
acquisition STOPPED; 71 approved files remain untouched. Six static controls
pass, with 30 source identities and 17 reusable wheel hashes; prior six acquired
files, logs, plans and receipts remain intact. Native closure INCOMPLETE; faithful
import/construction and cryptography necessity UNKNOWN. Known package lower
bound 28 / 11 wheel gaps; D3/D5 PARTIAL, D4 BLOCKED.
See the [remaining-source receipt](../../manifests/phase-08d8-remaining-source-closure.json)
and [updated report](../experiments/PHASE_08D8_MINIMAL_NATIVE_RUNTIME_PREPARATION.md).
Independent review is next. Narrow next authorization: reflect `agent.py`,
91,029 bytes, source-only. Broader explicit resumption: 72 remaining files /
1,294,510 bytes. No package acquisition/install/build or native/provider/SDK,
model/database/worker/service, RQ3, SSH or Jetstream action is authorized by this
handoff. Startup gate unchanged; no scientific denominator/evidence change.

The expanded 75-file inspection below is historical:

The expanded source-only continuation from
`0e6d6a7d3d6faa5fc21fb6cae89fb45da91e30ef` froze the exact 75-file plan, then
acquired/verified `_thread_limits.py`, `engine/cross_encoder.py` and
`engine/db/__init__.py`: three new files / 101,207 bytes. Thread-limit behavior
only queries CPU/cgroup values and sets process environment defaults; model and
executor creation in the cross-encoder body is deferred. The database initializer
unconditionally imports out-of-allowlist `base.py`, `ops.py`, `result.py`, so
acquisition STOPPED; the other 72 approved files were untouched. Six static/
integrity controls pass, with 26 verified sources and 17 rehashed reusable wheels.
Known package lower bound remains 28, with 11 wheel gaps. Faithful native import
and cryptography necessity remain UNKNOWN; D3/D5 PARTIAL and D4 BLOCKED.
See the [expanded source receipt](../../manifests/phase-08d8-expanded-source-inspection.json)
and [updated report](../experiments/PHASE_08D8_MINIMAL_NATIVE_RUNTIME_PREPARATION.md).
Independent review is next. The narrow next source-only authorization covers the
three new database bodies (55,505 bytes); broader explicit resumption can cover
the exact remaining 75-file / 1,259,799-byte frontier. No wheel/package/build,
native import/construction/request, service/model/database or live action is
authorized by this handoff. The runtime BLOCKED gate is unchanged.

The prior 31-file inspection below is historical:

The source-only continuation from `a452984507e83f029ae25cb5c850aaca390354c4`
acquired and verified the three package initializers (7,029 bytes), then obeyed
the explicit STOP on finding root `_thread_limits.py` outside the 31-file
allowlist. The other 28 files were not acquired. Engine initialization imports
MemoryEngine/embeddings/cross-encoder modules eagerly; worker initialization
imports the poller. Static analysis of 23 verified sources exposes 75 missing
source nodes (28 unacquired allowlisted + 47 new), with exact pinned identities
and purposes. Known package lower bound: 28; 17 existing artifacts rehashed,
11 wheel gaps. Five source-only constraint checks pass. No native/SDK import,
construction/request, package download/install/build or live action occurred.
D3/D5 PARTIAL, D4 BLOCKED; native cryptography necessity remains UNKNOWN.
See the [source acquisition/static inspection receipt](../../manifests/phase-08d8-source-inspection.json)
and [updated report](../experiments/PHASE_08D8_MINIMAL_NATIVE_RUNTIME_PREPARATION.md).
Independent review is next. A new bounded source-only authorization is required
to resume at the expanded 75-file / 1,305,501-byte frontier; a narrower first
step can cover only `_thread_limits.py` (4,780 bytes). No installation or native
execution is authorized by this handoff.

The preparation summary below is historical, preceding source authorization:

Separately authorized preparation on `phase-08d8-native-runtime-preparation`,
base `e07de9832572a910e7055d2df582b919146c35fd`, reverified the existing 16-package
SDK environment, 20 pinned source files and dependency metadata with networking
denied. Four artifact rejection controls passed. Ordinary provider import runs
an eager initializer importing 13 sibling implementations; 31 source files are
missing from the known frontier. Ten additional helper dependency candidates
are known; only aiosignal has a matching local wheel. The complete minimal
native closure remains UNKNOWN. Cryptography is required by full distribution
metadata, absent from SDK closure, and unresolved for ordinary native import;
no workaround is justified. No acquisition, installation, native import or
construction occurred. D3/D5 remain PARTIAL and D4/runtime/pilot BLOCKED.
See the [Phase 08D-8 report and bounded source-only acquisition proposal](../experiments/PHASE_08D8_MINIMAL_NATIVE_RUNTIME_PREPARATION.md).
Stop for independent review. The proposed 31-file pinned source inspection
requires separate authorization before any request; no package, build, native
method, service, model, SSH or Jetstream action is authorized by this handoff.

### Phase 08D-7 SDK-only installation and qualification addendum (historical)

Separately authorized preparation on `phase-08d7-runtime-dependencies`, base
`d29742e9a59575d63f54c50e10205208654240c1`, verified pinned upstream dependency
metadata and inventoried existing local environments/caches without changing
them. The initial CPython 3.12.8 Intel macOS lock inventory had 33 locally
available matching wheels out of 184 packages; 151 were BLOCKED. The SDK-only
closure initially had nine ready wheels and seven missing. Full Hindsight lacks a
complete source/release artifact and a locked Intel macOS cryptography wheel.
Subsequent explicit user authorization acquired exactly seven allowlisted SDK
wheels and copied nine local wheels. All 16 pinned distributions installed
offline; hashes/RECORDs, imports and pip check passed. After correcting a harness
false positive on macOS encoding metadata (`__CF_USER_TEXT_ENCODING`), all 30
offline SDK/HTTPX/scripted-HTTPCore cases passed: 33 SDK invocations and 43 HTTPX
requests, zero real socket/DNS attempts beyond denied self-tests. Network guards
were unchanged. Scripted streams/TLS do not qualify live physical sends or native
Hindsight; it remains uninstalled. Runtime/pilot remain BLOCKED; D3/D5 PARTIAL,
D1/D2 evidence and scientific denominators unchanged. See the
[Phase 08D-7 report and acquisition restrictions](../experiments/PHASE_08D7_RUNTIME_DEPENDENCY_PREPARATION.md).
Stop for independent review of SDK-only results and native qualification gaps.
No qualification rerun, Hindsight installation, provider initialization or live
work is authorized by this handoff.

### Phase 08D-6 engineering review addendum (historical)

The separately authorized offline qualification on
`phase-08d6-runtime-qualification`, base
`58ab52dcd8e628400533173eac08ed5b1ea42faa`, verified 19 cached pinned Hindsight
source files and traced role/member/worker ownership and alternate/batch bypasses.
The available repository environment lacks Hindsight, OpenAI SDK, httpx/httpcore
and aiohttp: installed-runtime transport probes could not run without prohibited
installation. Static evidence and ownership counterexamples do not establish
native coverage. The focused suite passes 161 tests. D4 and pilot readiness remain
**BLOCKED**; D3/D5 remain **PARTIAL**. The unconditional runtime gate is unchanged.
No provider/model/embedding/downstream/RQ3, SSH or Jetstream action occurred;
scientific evidence and denominators remain unchanged. See the
[Phase 08D-6 report](../experiments/PHASE_08D6_NATIVE_RUNTIME_QUALIFICATION.md).
Next action is independent review; stop after review-branch publication. No
runtime startup or dependency installation is authorized by this handoff.

### Phase 08D-5 engineering review addendum (historical)

The separately authorized offline work on `phase-08d5-governed-sends`, base
`de011d8bde32ffda76512c87dee550f0baf688d5`, implements an optional governed
completions boundary for owned deterministic fake clients. The final focused
suite passes 143 tests. Real-provider D4 and the four-condition pilot remain
**BLOCKED**: complete client/worker/transport interception and defensible
endpoint-enforced total-token bounds are unverified. The runtime startup gate
rejects every configuration. No provider, model, embedding, downstream, RQ3,
SSH or Jetstream action occurred. See the
[Phase 08D-5 report and D1–D5 matrix](../experiments/PHASE_08D5_GOVERNED_SEND_INSTRUMENTATION.md).
Next authorized action for this branch is independent review; stop after
publication. No historical result or research denominator changed. The earlier
Phase 08C-1 handoff below remains historical context, not authorization for a
new pilot or live qualification.

Phase 08C-1 offline implementation and evaluation are complete on the review
branch. The next action is scientific review of the exact policy boundary,
fixture adaptation, exclusions, and reported metrics. A broader RQ4 evaluation,
production policy service, downstream model experiment, revised Freeze-v2, or
provider phase requires separate approval. A RetainDB static/preflight phase
may be prepared separately, but live calibration requires its own explicit
authorization. At present, no live action is authorized, Candidate10 must not
be rerun or replaced, and no revised Freeze-v2 draft is approved.

The current execution rule is: no live action is authorized.

Jetstream remains `SHELVED`. Honcho is not accepted for Freeze-v2 entry because
the frozen gate returned `NO_GO`. Freeze v2 remains a draft and is not
finalized. RQ3 was not activated and downstream model calls remain zero. The
provider-internal calls are separately accounted provider behavior and cannot
act as an authority/security judge or activate RQ3. The raw evidence appendix
is preserved locally but is not published with the repository.

RetainDB Server remains `PENDING_LIVE_ACCEPTANCE`; all previewed capabilities
remain `UNKNOWN`. Graphiti is fallback only and does not become eligible from
Honcho `NO_GO`. Do not start Jetstream, install or contact any proposed
provider, change Freeze v1, finalize or silently revise Freeze v2, or rerun any
historical repetition without separate authorization.

## Safe continuation checklist

1. Run `git status` and preserve unrelated/untracked evidence.
2. Read [`DEBUGGING_LEDGER.md`](DEBUGGING_LEDGER.md) before changing runners.
3. Validate Freeze v1 from the Git blob, never checkout-dependent bytes.
4. Use the exact frozen provider versions and configuration hashes.
5. Treat attempt artifacts as immutable and use exclusive creation.
6. Keep Jetstream shelved unless a new prompt explicitly authorizes a live
   lifecycle.

When a future phase closes, update only the handoff files whose state changed.
At minimum inspect `PROJECT_STATE.md`, `EXPERIMENT_LEDGER.md`, and
`DEBUGGING_LEDGER.md`; do not rewrite the corpus wholesale.
