# Phase 08D-8 — Minimal Hindsight Native Runtime Preparation

**Adaptive source inspection completed sufficiently for the feasibility decision.
101 new sources / 1,692,988 bytes / 101 HTTPS requests; 29 new mandatory imports
discovered. Mandatory literal graph: 125 modules, no missing body. Ordinary
import's pinned package footprint: 61 packages, including cryptography 50.0.0.
Recommend B: separately reviewed real provider-boundary architecture; not
implemented. Runtime safety UNKNOWN; D3 PARTIAL, D4 BLOCKED, D5 PARTIAL.**

## Bounded adaptive native source closure — 2026-10-13

CONVERSATION: Phase 08D-8 bounded adaptive native source closure. MODEL: GPT-6
Codex runtime; no independent model-variant receipt. EXECUTION TARGET: assigned
local worktree `/Users/ian/.codex/worktrees/b648/Memo`. JETSTREAM ACTION: none;
remains SHELVED without querying infrastructure.

The attached execution request authorized adaptive acquisition of required
first-party Python sources within pinned commit
`f8950b0c07d9e34c76493dba802bb309f0ce60fd`, superseding fixed-file discovery
stops only. Starting review branch and clean HEAD were verified exactly as
`phase-08d8-native-runtime-preparation` /
`d226f7859fae94df0055cda43c5900571b0d66d5`. The current source receipt remained
unchanged at SHA-256
`ca0d9b4996ce73e8b7192317938417ee9945e8738c9931b5c74f0f251d875cd0`.
All historical Phase 08D manifests were checked byte-for-byte against this Git
commit; chained raw-source hashes and acquisition logs were verified. Prior
30 source files, source plans/receipts and ten locally acquired bodies were
preserved, not reacquired.

### Frozen scope, append-only discovery and acquisition

The [adaptive source plan](../../manifests/phase-08d8-adaptive-source-plan.json)
was frozen before requests, SHA-256
`5916fcffee52ae100e3245d1e7412fdf9aeae75b9b05414bbdcc718a87af1ca9`.
Its limits are 150 additional successful source files, 3,500,000 source bytes,
and 200 HTTPS request attempts including failures. Only `.py` blobs within
`hindsight-api-slim/hindsight_api/` in the previously verified non-truncated tree
are eligible. Identity/path/size and exact commit-qualified URL are resolved
before each request. No package, archive, binary or model acquisition is allowed.

The [immutable adaptive receipt](../../manifests/phase-08d8-adaptive-source-closure.json)
records every acquired path, Git blob SHA-1, length, SHA-256, HTTPS result and
request/discovery attribution. It also contains the complete discovery ledger
and graph. Raw source/evidence remain ignored under
`.local/phase08d8/source-frontier/`; downloaded source is not committed.

| Resource/evidence | Result | Authorized ceiling |
| --- | --- | --- |
| New acquired and verified files | **101** | 150 |
| Additional source bytes | **1,692,988** | 3,500,000 |
| HTTPS request attempts | **101** | 200 |
| Successful requests / failed requests | **101 / 0** | Failures consume request budget |
| Initially required files acquired | **72 / 72** | Initial frontier, not a limit on adaptive discoveries |
| Newly discovered mandatory files acquired | **29 / 29** | Pinned subtree and cumulative bounds |
| Dependency-aware batches reviewed | **15** | First reflect agent alone; later batches at most eight files |
| Total source files verified, including history | **131** | Prior 30 excluded from continuation limits |

`engine/reflect/agent.py` was acquired first. Every newly exposed required source
was appended to a discovery ledger **before** its acquisition, recording the
triggering import, pinned tree identity and trigger-source SHA-256. Request
intent is persisted before curl, so failure cannot disappear from the request
ceiling. Successful source evidence is appended separately. Batch receipts and
static reviews are exclusive, hash-bound files. Existing files are refused;
there is no silent recovery/retry over incomplete evidence.

[Acquisition code](../../scripts/phase08d8_adaptive_sources.py) uses the unchanged
strict primitive: exact HTTPS URL, TLS verification/TLS 1.2 minimum, no redirects,
empty curl environment, no configuration/proxies/credentials, exclusive partial
and final files, streamed per-file limits, SHA-1/length verification before AST
parsing, then SHA-256 recording. No file outside the allowed subtree/tree was
retrieved. Acquisition stopped when the source graph was sufficient for the
feasibility question, with unused file/byte/request capacity.

### Source graph and import-time assessment

The ordinary OpenAI-compatible import plus its successful-call tracing seam has
**125 reachable source modules and 125 verified bodies**, with zero missing
mandatory literal module imports and zero unresolved required module names in
that graph. The other six historical verified source files are not reachable in
this slice. This is a resolved **literal, unconditional import graph**, not a
proof of full dynamic Python import semantics or runtime safety.

```text
OpenAI-compatible provider
  -> real root initializer -> CPU/cgroup reads + thread environment defaults
  -> real engine initializer
       -> MemoryEngine module declarations (no engine instance constructed)
       -> db / SQLAlchemy ORM / pgvector / NumPy
       -> retain / reflect / search / storage / query/date parsing / tokenizer
  -> real providers initializer -> 13 sibling implementation modules
       -> Gemini module -> Google GenAI -> Google Auth -> cryptography
  -> real worker initializer -> poller module declarations
  -> llm_wrapper -> raw config / HTTP logging / cross-loop semaphores
  -> metrics / tracing -> OpenTelemetry API/SDK/exporter module imports
```

The discovery ledger records all 29 additional modules. Representative new
requirements include reflect prompts/tokenization/tool schemas; retain chunk,
embedding/entity/fact/link handling; search graph/retrieval/link expansion;
SQL/storage bases; PostgreSQL pool instrumentation; Codex/OAuth helpers; and
text-search/query helpers. Each entry retains a scientific purpose: resolving
the actual import prerequisites of the native provider, never executing those
operations or adding experimental observations.

The graph separately records **637 deferred-function import edges, 53
type-checking-only edges and 3 guarded/conditional import edges**. There are
**44 distinct unacquired first-party source targets** represented by 293 such
nonmandatory edges. They were not fetched because they are outside the demonstrated
mandatory slice needed for this feasibility decision. Arbitrary extension
module names/configuration-dependent dynamic imports and third-party module
effects remain UNKNOWN; no all-configurations completeness claim is made.

Reviewed prospective import-time effects include:

- CPU/cgroup reads and four process thread-limit defaults from the real root.
- Raw configuration resolution, HTTP logger configuration and cross-loop
  semaphore/lock/deque construction. Semaphore constructors do not start workers.
- Pydantic/dataclass/protocol setup; SQLAlchemy column/index/relationship metadata
  construction. Metadata objects are not database connections or table creation.
- Regex/constants, ContextVars, native no-op metrics/tracer objects and composite
  span-recorder registration. Exporter/background-poller startup is deferred.
- `local_device._resolve_heap_trim()` resolves platform allocator symbols through
  ctypes at module scope. Actual trim/inference is deferred; native-library
  loading effects remain UNKNOWN.
- Prompt constants include a **wall-clock-derived datetime section**. They are
  not all immutable text; this source observation does not execute a model.
- Environment/path reads in sibling auth/llama.cpp modules; credential refresh,
  subprocesses, clients and model loading remain in deferred paths.

No demonstrated source-level import-time MemoryEngine instance construction,
database connection, embedding/model load, worker/service launch or hosted call
was found in the reviewed acquired bodies. This negative static finding is not
runtime-safe certification. The eight source/integrity checks do not import any
of these modules. Reviews preserve UNKNOWN effects of third-party imports and
dynamic/native behavior. Final AST phase classifications correct early review
shorthand: Anthropic/Claude SDK imports are deferred constructor paths; prompt
building includes the clock read noted above.

### Updated minimum declared package footprint and cryptography

[Metadata closure code](../../scripts/phase08d8_package_closure.py) resolves only
the external packages required by verified mandatory import roots, including
dependency-selected extras and target markers, using the existing pinned lock.
It does not select full Hindsight extras or optional providers merely because
they are declared in the full distribution. Unknown metadata syntax rejects.

The result is **61 packages**, versus the prior partial lower bound of 28 and
the full-runtime resolution of 184. Exact versions, dependency edges, applicable
extras/markers and candidate artifact identities are in the adaptive receipt.
This is the minimum **declared metadata closure of the demonstrated import
roots**, not proof that no third-party dynamic dependency exists. Nor is it a
dependency-compliant installation of the full `hindsight-api-slim` distribution:
its full metadata must not be silently trimmed.

| Added eager package family | Required by verified source |
| --- | --- |
| Google GenAI 2.18.1 / Google Auth 2.56.3 | Gemini sibling module imported by real provider initializer |
| cryptography 50.0.0 / cffi / pyasn1 family | Google Auth's selected base dependency metadata |
| OpenTelemetry API/SDK/exporters/protobuf/Prometheus | Real metrics and tracing module imports |
| SQLAlchemy 2.0.44 / greenlet / pgvector 0.4.1 / NumPy 2.3.4 | Real engine database/ORM/search imports |
| dateparser 1.4.2 / regex / date/timezone dependencies | Real query analysis module |
| toktok-rs 0.1.3 | Real engine tokenizer module; vocabulary loading itself deferred |

| Artifact status on pinned CPython 3.12.8 Intel macOS target | Count |
| --- | --- |
| READY: rehashed qualified SDK wheel artifacts | 16 |
| READY: other rehashed matching cached wheel artifacts | 8 |
| MISSING: compatible locked candidates exist but matching local artifact absent | 36 |
| BLOCKED: no compatible wheel in the pinned lock | 1 (cryptography 50.0.0) |

This is a bounded artifact inventory, not a repeat machine scan or new package
acquisition. No installed native runtime or third-party import was requalified.

**Cryptography is now necessary in the dependency-complete pinned ordinary-import
package closure**, with evidence chain:

```text
providers/__init__.py -> gemini_llm.py:21–23 (unconditional Google GenAI imports)
Google GenAI 2.18.1 -> Google Auth 2.56.3 [requests]
Google Auth 2.56.3 -> cryptography 50.0.0
```

This is a verified source edge plus pinned metadata dependency, not a measured
execution of Google/Auth/cryptography. The OpenAI/HTTP SDK-only 16-package closure
still does not require cryptography. Full Hindsight metadata separately retains
its `cryptography>=50.0.0` security floor. There is no compatible Intel macOS
cryptography 50.0.0 wheel in this pinned lock; this does not claim current global
PyPI availability or a demonstrated CPU failure. No downgrade, source build,
architecture substitution or workaround is proposed or executed here.

### Engineering decision: B, proposal only

| Option | Evidence, cost and limits | Decision |
| --- | --- | --- |
| A: faithful ordinary import of the pinned source | Literal first-party graph resolved; reviewed source separates module declarations from engine/model/service instance initialization. Requires 125 source modules and a 61-package declared footprint, 37 non-ready artifact slots and the locked Intel cryptography gap. Third-party import/native effects, actual constructor behavior and complete runtime governance remain unqualified. It need not install all 184 packages, but substantially expands beyond a provider/SDK test. | Technically plausible pending artifacts and offline runtime evidence; installation is not ready or authorized. |
| B: separately reviewed real provider-boundary architecture | Make the provider entrypoint independent of engine/retain/search/database/sibling SDK bootstrap through a genuine first-party packaging/lazy-export design, retaining native provider methods and actual SDK semantics. Explicitly distinguish the engineered boundary from unmodified 0.10.1 ordinary runtime. | **Recommended next direction; not implemented.** |

The proposed B design review should define a genuine minimal first-party provider
entrypoint/package, real helper dependency contracts and a provenance manifest
for unchanged provider/method bytes. One candidate is a reviewed lazy-export
refactor of the real engine/provider initializers, consistent with the existing
lazy root pattern; another is an upstream-supported provider-only library.
Either needs its own explicit source/packaging review and versioned identity.
It cannot use `sys.modules` stubs, fake package initializers or a claimed native
readiness exemption. A changed bootstrap would qualify that engineered boundary,
not retrospectively certify the unmodified frozen runtime.

The design must preserve model/headers/query/body/schema/tool/reasoning/token
parameters, native retry behavior, and raw SDK usage before native transformations.
Any later qualification must use the actual SDK with the separately authorized
D7 offline transport and preserve HTTP attempt accounting. Complete worker/role
ownership and endpoint inclusive-token bounds remain separate D4 prerequisites.
No extraction, lazy-initializer patch, source rewrite, import hook or test
architecture was implemented in this phase.

**Precise next authorization: design-only review of option B's real provider
entrypoint/packaging, provenance and semantic-parity contract.** It would not
authorize acquisition, installation, source modification or native execution
unless those are expressly added to a subsequent prompt. If option A is chosen
instead, a separately reviewed compatible-artifact/platform plan is necessary;
the current 61-package inventory is not an executable install authorization.
Additional deferred sources need not be acquired merely to exhaust this budget.

### Static/integrity checks and readiness

[Final verification](../../scripts/verify_phase08d8_adaptive_sources.py) ran with
the existing repository SDK `.venv`, `-I -B`, empty environment, macOS
deny-all-network profile and a Python audit hook rejecting native/SDK imports
and socket events. **Eight checks PASS:** historical manifests/131 source
identities/tree; adaptive discovery/request order/ceilings; 15 reviews/literal
graph; 61-package markers/extras/crypto chain; ready-wheel hashes; marker target
and unknown-marker rejection; source tamper/outside-path rejection; and the
feasibility STOP before curl with all prior evidence unchanged. Static checks
made zero requests; acquisition's 101 authorized HTTPS requests are separate.

The receipt is immutable and all raw sources remain ignored. D1/D2, Freeze v1,
frozen attempts and scientific denominators are unchanged. No Hindsight import
or source execution, provider construction, SDK request, package acquisition/
installation/build, model/embedding/database/worker/service initialization,
Jetstream, SSH, RQ3 or empirical action occurred. **D3 PARTIAL, D4 BLOCKED,
D5 PARTIAL; startup gate unchanged. Stop for independent review.**

## Prior remaining native source closure (historical) — 2026-10-13

CONVERSATION: Phase 08D-8 remaining native source closure. MODEL: GPT-6 Codex
runtime; no independent model-variant receipt. EXECUTION TARGET: assigned local
worktree `/Users/ian/.codex/worktrees/b648/Memo`. JETSTREAM ACTION: none; remains
SHELVED without infrastructure queries.

The clean review branch was verified at exactly
`d11a081855b84b85522fde6ad25deeb34a37ceaa`. The authorizing expanded receipt is
unchanged, SHA-256
`c7bf586e727475ec4a8c045f11ac9b1ab3036435e2b1ddb9fd08d2d5151cde17`.
Its 75 remaining source paths, Git blob SHA-1 identities, byte counts and exact
commit-qualified HTTPS URLs were verified against the pinned non-truncated
Hindsight 0.10.1 tree. The 26 prior source identities and both prior acquisition
logs were checked before acquisition. Scope was 75 additional source files /
1,259,799 bytes; no package or native execution was authorized.

### Frozen plan and acquired evidence

The new immutable [remaining-source plan](../../manifests/phase-08d8-remaining-source-plan.json)
was frozen **before requests**, SHA-256
`579e8fe5b860bf3ce0a627e94c70161f7a06096628f7d65bafb20a8d2c0387fd`.
It groups the three database files first, then the remaining required package
initializers and source dependencies. Each group gets a closure recomputation
and an explicit static side-effect review bound to its receipt/plan hashes.
Historical plans and receipts are preserved; no prior file is reacquired.

The [new immutable integrity/closure receipt](../../manifests/phase-08d8-remaining-source-closure.json)
records **four new files / 56,318 bytes**, four HTTP 200 source responses, TLS
verification result zero, zero redirects and exact allowlisted effective URLs.
Every Git blob SHA-1 and length matched before parsing; each SHA-256 is recorded.
Raw sources and group evidence remain ignored under
`.local/phase08d8/source-frontier/`. All six previously acquired sources and logs
remain unchanged. There are now ten acquired files / 164,554 bytes across the
separate authorizations, plus the 20 original verified cached sources.

| Acquired path, relative to `hindsight-api-slim/hindsight_api/` | Bytes | Git blob SHA-1 | SHA-256 |
| --- | --- | --- | --- |
| `engine/db/base.py` | 13,415 | `ab1b55394584e8eccfc2bfaea6e533d4e723df2d` | `1e2be0e5b01b3362791356286f5361719a91cb35406d07f42e3ee4aabc2ff87e` |
| `engine/db/ops.py` | 38,673 | `878424b69baee60e86005ebbf3eb199a11dfec97` | `c482a1d320c22ac515d938f549cd3cbb296c92c95afc7d926d48d88a9be3c106` |
| `engine/db/result.py` | 3,417 | `4d16a2544c9137260e8de8cf1fe1148c859fb2de` | `a4d33a8130d1a05ebfd6930a62fa58d5dfec74133e3c229a1eab4b74ffc8a3c6` |
| `engine/reflect/__init__.py` | 813 | `25f818224fed0a922ab378c45b79ef548489ff4c` | `155c2f0d7757c5be21d1725f2e22a98ffe50050a2cbfa0f8ae57832665c849e8` |

The [remaining acquisition/group verifier](../../scripts/phase08d8_remaining_sources.py)
reuses the unchanged strict acquisition primitive: HTTPS-only exact URLs, TLS
verification/TLS 1.2 minimum, empty curl environment, disabled configuration and
proxies, no redirects, exclusive partial/final source files, streamed per-file
size bounds and SHA-1/length verification before parsing. Both cumulative
75-file/1,259,799-byte limits are enforced. Only the new log receives append-only
records. Partial/mismatched evidence would stop without promotion or overwrite.

### Static findings and mandatory stop

| Group | Import-time assessment | Graph after group | Decision |
| --- | --- | --- | --- |
| 1: db base/ops/result | Abstract classes, dataclasses, standard-library typing protocol/decorators and constants. Their mandatory imports are standard library and the three verified database files; the reverse ops import in base is TYPE_CHECKING-only. Database/SQL work remains in deferred methods. No backend/driver instance, connection, worker or model initialization in these bodies. | 94 known modules; 22 verified reachable bodies; 72 approved missing bodies | Continue static inspection |
| 2: reflect initializer | Unconditionally imports `.agent` at line 10 and `.models` at line 19. Exports `run_reflect_agent` and result/error/tool-limit symbols, without calling them. Agent body is outside the approved 75; models body remains approved but unacquired. | 95 known modules; 23 verified reachable bodies; 71 approved missing + 1 new outside body | **STOP** |

The database base/result/ops imports form a source-resolved cycle: base imports
result and mentions ops only for type checking; ops imports base/result. Actual
database operations are defined on ABC methods, not invoked by these import
bodies. Protocol/dataclass decorators execute when classes are defined, but
these are standard-library class setup rather than database initialization.
No source was executed to reach these conclusions.

The exact new mandatory source is:

| Source | Git blob SHA-1 | Bytes | Trigger and scientific relevance |
| --- | --- | --- | --- |
| `hindsight-api-slim/hindsight_api/engine/reflect/agent.py` | `e88a5b978a5c042286274afa8acd833d042e0870` | 91,029 | `engine/reflect/__init__.py:10` imports agent symbols unconditionally. Cached MemoryEngine imports the reflect package at module scope, which ordinary provider import reaches through the engine initializer. Thus this is a prerequisite for faithful import qualification, not authorization to execute reflection or add scientific observations. |

Its exact pinned raw URL is recorded in the receipt's `missing_source_frontier`.
No SHA-256 is claimed because the bytes were not acquired. **Acquisition stopped
after group 2; `agent.py` was not fetched, and the remaining 71 approved files
were untouched.** The guard test proves another `next` invocation rejects before
curl and preserves all existing raw sources/logs.

### Closure, minimum package requirements and feasibility

The ordinary native provider import/method graph is **INCOMPLETE**: 95 known
source modules, 23 verified reachable bodies and 72 missing bodies. Total source
integrity coverage is 30 files; the other seven cached verified files are not
needed by the currently exposed graph. Conditional/deferred imports are retained
separately in the receipt rather than silently promoted or omitted. Further
missing bodies can expand both source and third-party dependencies.

The new database/reflect initializer bodies add no mandatory third-party root.
The inspected roots remain aiohttp, asyncpg, dotenv, httpx, json_repair, openai,
orjson and pydantic. Their pinned target-specific lock closure remains the
**28-package lower bound**, with exact versions/artifact identities retained in
the new receipt: **17 current reusable wheel artifacts rehashed; 11 selected
matching wheels missing** in the bounded prior inventory (1,647,815 bytes).
Ready means artifact integrity/availability, not an installed native runtime.
No SDK import or installed-environment requalification was attempted; no package
was downloaded, installed or built.

Cryptography verdict: **REQUIRED by full-distribution metadata at >=50.0.0;
NOT REQUIRED by the qualified SDK; UNKNOWN for ordinary native import/provider
construction.** No direct cryptography import appears in the 30 verified source
bodies. Missing reflect/provider/auth/database/observability bodies and their
third-party transitive imports prevent proving absence. The pinned lock's Intel
macOS cryptography 50.0.0 wheel gap is unchanged; no downgrade, source build,
architecture change or workaround is justified.

These database abstraction bodies do not require constructing MemoryEngine or
starting a backend during import. The reflect initializer imports an agent
function without invoking it. This supports a distinction between module
dependencies and runtime operation, but **faithful restricted import and
construction feasibility remain UNKNOWN**. The missing agent and many other
bodies could still impose prohibited initialization or further dependencies.
Neither feasibility nor the smallest complete installation set has been proven.
Do not install the lower-bound 28 packages or the entire 184-package runtime,
bypass real initializers, introduce stubs or weaken the startup BLOCKED gate.

### Exact next authorization and focused checks

The narrow next source-only authorization is the **one pinned reflect agent
file / 91,029 bytes**, with the identity and triggering import above. A broader
explicit resumption can cover the 71 suspended approved files plus this new
file: **72 remaining files / 1,294,510 bytes**, exactly enumerated in the new
receipt. The 71 approved-but-unacquired files alone total 1,203,481 bytes. Each
resumption must stop at another newly exposed source or prohibited import-time
initialization. Neither option authorizes reflection, native imports/provider
construction, packages, models, services, databases or an empirical run.

[Focused verification](../../scripts/verify_phase08d8_remaining_sources.py) ran
under the macOS deny-all-network profile, using the existing repository SDK
`.venv` interpreter with `-I -B` and an empty environment. Only our verification
code and standard-library parsing/hashing execute; an audit hook rejects socket
events and native/SDK imports. **Six checks PASS:** frozen scope/tree/prior
evidence; 30 source hashes and transport receipts; group reviews/closure;
17 wheel hashes and pinned metadata; tampered database bytes rejected before
parsing; and STOP before curl with source evidence unchanged. Acquisition's
four authorized HTTPS requests are distinct from zero static-check requests.

D1/D2, Freeze v1, all historical scientific evidence and denominators remain
unchanged. No Hindsight execution, native import, provider construction, SDK
request, package acquisition/install/build, service/model/embedding/database,
worker, Jetstream, SSH, RQ3 or empirical action occurred. **D3 PARTIAL, D4 BLOCKED,
D5 PARTIAL; startup gate unchanged. Stop for independent review.**

## Prior expanded pinned source inspection (historical) — 2026-10-13

CONVERSATION: Phase 08D-8 expanded pinned source inspection. MODEL: GPT-6 Codex
runtime; no independent model-variant receipt. EXECUTION TARGET: assigned local
worktree `/Users/ian/.codex/worktrees/b648/Memo`. JETSTREAM ACTION: none; remains
SHELVED without infrastructure queries.

The continuation verified clean branch `phase-08d8-native-runtime-preparation`
at exactly `0e6d6a7d3d6faa5fc21fb6cae89fb45da91e30ef`. The existing 75-file
source receipt remained unchanged, SHA-256
`053ef0d487dd4c546732bfcedf9ff08f6fb70908018cd02cc2aa54036afaf038`.
All 75 paths, exact commit-qualified URLs, lengths and Git blob SHA-1 identities
were checked against the previously verified non-truncated pinned source tree.
The 20 cached sources, three prior initializers and prior acquisition log were
reverified. The user superseded the old 31-file limit with 75 new files and
1,305,501 new source bytes; no package/native execution authorization followed.

### Frozen plan and exact acquired files

Before the first request, the exclusive
[expanded acquisition plan](../../manifests/phase-08d8-expanded-source-plan.json)
was frozen at SHA-256
`f5d1bce8158dad16c6300e18aef04f2d58ed69b80a9c56ac742817df66fafb94`.
It contains the exact 75-file allowlist and singleton dependency groups. The
first group is `_thread_limits.py`; the next is `engine/cross_encoder.py`, the
engine initializer's first eager child; then required package initializers.
Each group receives a closure recomputation and a recorded static side-effect
review before another request. Singleton groups bound acquisition at each
newly exposed dependency. No plan or prior acquisition record was overwritten.

The [expanded source-integrity/graph receipt](../../manifests/phase-08d8-expanded-source-inspection.json)
records three new files, **101,207 bytes**, acquired in three HTTPS requests.
Each response was HTTP 200, TLS verification result zero, zero redirects, and
the exact pinned effective URL. SHA-1 and size were verified before parsing,
and SHA-256 recorded. Source bodies and raw group receipts remain ignored under
`.local/phase08d8/source-frontier/`. The three prior initializer files were
neither reacquired nor modified; total locally acquired source is now six files
/ 108,236 bytes across both separate authorizations.

| New source, relative to `hindsight-api-slim/hindsight_api/` | Bytes | Git blob SHA-1 | SHA-256 |
| --- | --- | --- | --- |
| `_thread_limits.py` | 4,780 | `2a690711d4651dbb75304248d11d5bf2f7fdaf2f` | `1d7460ef59675b658b7871e777042581eb1df3360719ed888ddea6f3402a3c8b` |
| `engine/cross_encoder.py` | 93,469 | `124fb210e2ada35182cf1d41bb0f48165610541e` | `0e7f2f9ce61dbcc597159a09c28451b89f3c9ab1e474439184146c1854609ed5` |
| `engine/db/__init__.py` | 2,958 | `3e9fde9fd8908778ab7ae65819a2ab57716e7e21` | `f580d13c226508070e00601ecf20b6445a8013cc894861c1f913a2441d6943b9` |

The [expanded acquisition/static group code](../../scripts/phase08d8_expanded_sources.py)
retains strict HTTPS-only curl controls, TLS verification/TLS 1.2 minimum,
empty subprocess environment, disabled curl configuration/proxies, no redirects,
exclusive partial/final files and streaming per-file bounds. Both cumulative
75-file and 1,305,501-byte limits are enforced. Review records bind the frozen
plan and exact group-receipt hashes. A STOP group rejects another acquisition
before curl. Actual acquisition remains bound to the authorized base; a later
review commit may reverify a STOP without gaining acquisition permission.

### Import-time behavior and group decisions

| Group | Static evidence | Closure after group | Decision |
| --- | --- | --- | --- |
| 1: thread limits | Imports only standard-library `os`. Root-triggered `apply_default_thread_limits()` computes a CPU cap and calls `os.environ.setdefault` for four thread variables. | 91 known modules; 17 verified reachable bodies; 74 missing approved bodies; no new outside source | Continue static inspection |
| 2: cross-encoder | Mandatory helper imports stay inside the approved set. Module-level call is `logging.getLogger`. Model/client/executor construction is deferred to constructors/initialization methods. | 91 known modules; 18 verified reachable bodies; 73 missing approved bodies; no new outside source | Continue static inspection |
| 3: database initializer | Lines 15–17 unconditionally import `.base`, `.ops`, `.result`, none in the approved 75. Backend factories defer instance construction; module defines an empty operations cache. | 94 known modules; 19 verified reachable bodies; 72 approved missing + 3 new outside bodies | **STOP** |

Thread-limit behavior is now source-verified: `_available_cpu_count()` queries
CPU count/affinity and reads cgroup v1/v2 CPU quota files, handling absence or
invalid content. `default_native_thread_count()` caps the result at 16.
`apply_default_thread_limits()` supplies `OMP_NUM_THREADS`,
`OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`, and `NUMEXPR_NUM_THREADS` only when
unset. These are prospective process environment mutations/read-only CPU and
filesystem queries, not observed effects: source was never executed. The
implementation contains no model import, thread-pool creation, model load,
worker/database/service initialization or network call, so it did not trigger
the prohibited-initialization stop.

Cross-encoder `sentence_transformers`, flashrank, MLX and other backend SDK/model
imports and model/executor creation occur in deferred method paths. They do not
become required merely by inspecting this body or by calling the OpenAI-compatible
provider. Its mandatory `_cross_loop`, config, aiohttp-session, attribution,
local-device and retry helper bodies still need inspection before their own
import side effects can be certified. No inferred bypass or package extra is
introduced from the absence of execution.

The database initializer's `create_database_backend()` and
`create_data_access_ops()` call backend/ops constructors only when invoked;
Oracle/PostgreSQL selection imports inside those factories are deferred.
However, `.base`, `.ops` and `.result` are unconditional **module** imports.
Their missing bodies therefore block a faithful ordinary import even when no
database factory is called. Source inspection cannot assume they are harmless.
**Acquisition stopped at group 3; the remaining 72 approved files were not
acquired and no new frontier file was fetched.**

### Feasibility, dependency readiness and cryptography

There is no verified requirement in these three new bodies to construct
MemoryEngine or initialize a model/database during ordinary import. Their
inspected code separates those constructions from module imports. That improves
the evidence, but **faithful restricted native import is still UNKNOWN / not
established**, because it executes real engine/provider/worker initializers and
many required bodies remain missing. It has not been shown impossible, safe,
or dependency-complete. No native import or provider construction was attempted.
Package initializer bypasses, module stubs, upstream edits and runtime-gate
exceptions remain prohibited.

| Inventory | Updated result |
| --- | --- |
| VERIFIED source | 26 source files total; 19 reachable verified bodies in the known ordinary-import/method graph |
| MISSING source | 75 bodies: 72 suspended approved files plus 3 newly required out-of-allowlist files |
| READY wheel artifacts | 17 rehashed current artifacts: 16 qualified SDK wheels + aiosignal; no SDK import or installed-runtime requalification |
| MISSING wheel artifacts | 11 matching selected artifacts in the bounded recorded inventory, totaling 1,647,815 bytes |
| UNKNOWN | Further source/third-party closure, missing-body side effects, complete minimal installation set and native cryptography necessity |

The known mandatory external import roots remain aiohttp, asyncpg, dotenv,
httpx, json_repair, openai, orjson and pydantic. Root `os` and cross-encoder's
`concurrent.futures` are standard-library dependencies. The pinned metadata
and target-selected closure therefore leave the prior **28-package lower
bound unchanged**. All exact candidate identities remain in the expanded
receipt, with the prior receipt hash binding their provenance. This lower bound
does not justify installing 28 packages or the full 184-package runtime.

Cryptography remains **REQUIRED by full-distribution metadata; NOT REQUIRED by
the qualified SDK; UNKNOWN for ordinary native import and provider methods**.
There are zero direct cryptography imports in all 26 verified source bodies.
That does not rule out a transitive import from the missing database, auth,
provider or observability bodies. The pinned lock's cryptography 50.0.0 Intel
macOS wheel gap remains unchanged. No version substitution, source build,
architecture workaround or security-floor change is proposed.

### Exact next source authorization and checks

The narrow next source-only authorization would add these three files, **55,505
bytes total**, with the same pinned commit and strict transport/integrity
controls. Inspect/recompute after each and stop at another new requirement:

| Required source | Git blob SHA-1 | Bytes | Required purpose |
| --- | --- | --- | --- |
| `engine/db/base.py` | `ab1b55394584e8eccfc2bfaea6e533d4e723df2d` | 13,415 | Unconditional import in db initializer line 15 |
| `engine/db/ops.py` | `878424b69baee60e86005ebbf3eb199a11dfec97` | 38,673 | Unconditional import in db initializer line 16 |
| `engine/db/result.py` | `4d16a2544c9137260e8de8cf1fe1148c859fb2de` | 3,417 | Unconditional import in db initializer line 17 |

Their exact commit-qualified raw URLs and identities are in the expanded
receipt's `missing_source_frontier`. The remaining 72 approved files are
suspended by this run's STOP, not silently added to a resumed run. A broader
explicit resumption plan could cover those 72 plus the three new files: **75
remaining files / 1,259,799 bytes**, exactly enumerated in that frontier.
Neither choice authorizes installation or execution. No wheel acquisition or
installation plan is ready for approval before source closure is established.

[Focused static/integrity verification](../../scripts/verify_phase08d8_expanded_sources.py)
ran under the macOS deny-all-network profile with the existing repository SDK
`.venv` interpreter, `-I -B`, and an empty environment. The verifier uses only
our code and standard-library parsing/hashing; an audit hook forbids native/SDK
imports and socket events. **Six checks PASS:** frozen scope/tree, 26 source
identities and transport receipts, group review/graph integrity, 17 wheel hashes
and pinned dependency metadata, tampered-source rejection before parsing, and
STOP rejection before curl with existing files/logs unchanged. Earlier derived
verification receipts remain ignored and preserved; the tracked expanded receipt
is the final pass. Prior authorizing receipts/plans and raw source remain intact.

Source acquisition made exactly three separately authorized HTTPS requests.
Static inspection/checks made zero requests. No native/SDK source execution,
provider construction, package download/install/build, service/database/model,
embedding, RQ3, SSH, Jetstream or empirical action occurred. D1/D2, Freeze v1,
scientific denominators and historical evidence are unchanged. **D3 PARTIAL,
D4 BLOCKED, D5 PARTIAL; the startup gate is unchanged. Stop for independent
review.**

## Prior 31-file authorized inspection (historical, 2026-10-12)

CONVERSATION: Phase 08D-8 authorized pinned source inspection. MODEL: GPT-6
Codex runtime; no independent model-variant receipt. EXECUTION TARGET: assigned
local worktree `/Users/ian/.codex/worktrees/b648/Memo`. JETSTREAM ACTION: none;
remains SHELVED without infrastructure queries. Date: 2026-10-12,
America/Chicago.

The continuation started at exactly
`a452984507e83f029ae25cb5c850aaca390354c4` on
`phase-08d8-native-runtime-preparation`, with a clean worktree. The authorized
manifest is unchanged, SHA-256
`99aea9f5bc42f0d53a3b13ae81b586f3ec92ab25027c3cb99b65c04441afe410`.
Its 31 unique commit-qualified source URLs and 586,246-byte limit were validated
before acquisition. This authorization is source acquisition and static
inspection only; no package acquisition/installation or native execution.

### Acquisition and mandatory stop

The [acquisition/integrity and static inspection receipt](../../manifests/phase-08d8-source-inspection.json)
records **three HTTPS requests, three verified files, 7,029 aggregate bytes**.
All returned HTTP 200, TLS verification result zero, zero redirects, and the
exact allowlisted effective URL. Each file matched its expected byte count and
Git blob SHA-1 before AST parsing; SHA-256 was then recorded. Source bodies
remain ignored under `.local/phase08d8/source-frontier/`, never in Git.

| Acquired path, relative to `hindsight-api-slim/hindsight_api/` | Bytes | Git blob SHA-1 | SHA-256 |
| --- | --- | --- | --- |
| `__init__.py` | 5,227 | `cbd06145d17392c98482df0a1ccd29d740666e61` | `bcc7731940bd700adbfcc094677c648fa21c9853634ceccf5ec3ac79310355b9` |
| `engine/__init__.py` | 1,546 | `8ec70075bae971adef5d6bd941a2f1db7fe1787c` | `abdce96a0c096bf31ffeacc9e4390d5f72ca6ff4dbc38636caf14857aadc6863` |
| `worker/__init__.py` | 256 | `8eb27f9f0d8ce79fc4c29f731d4cbf40615f550a` | `873a4c2ef39f80bd8a2abae293ff68baf13309dbc94ab1fea63e547452badc9d` |

The [acquisition code](../../scripts/acquire_phase08d8_sources.py) uses system
curl 8.7.1 with an empty child environment and disabled curl configuration,
proxies and redirect following. HTTPS-only/TLS verification and a TLS 1.2
minimum are enforced. Per-file `--max-filesize` bounds streaming output; planned
and actual aggregate bytes cannot exceed 586,246. An exclusively opened partial
file descriptor receives the body; verified final paths are created by exclusive
hard link. Existing destinations are rejected. The raw acquisition log is
append-only; incomplete or mismatched evidence would be retained, not promoted.

The initializers were acquired as the first inspection group. Static inspection
then met task 8's explicit stop condition:

- Root `__init__.py:39` imports `._thread_limits`; line 41 calls
  `apply_default_thread_limits()` at module scope. `_thread_limits.py` is outside
  the 31-file allowlist and is not among the 20 existing verified sources.
- `engine/__init__.py:11–30` eagerly imports cross-encoder, embeddings,
  MemoryEngine, database helpers, response models and search modules. The root's
  lazy public `MemoryEngine` export does **not** make the engine package lazy.
- `worker/__init__.py:9` imports `WorkerPoller`. Importing `worker.stage` therefore
  also reaches the existing poller, its schema/backpressure/exception imports,
  and the engine parent package.

**Further acquisition stopped immediately after inspecting this three-file
group. The remaining 28 allowlisted files were not retrieved.** No source outside
the allowlist was fetched. The acquisition script's continuation mode now
explicitly rejects the discovered `_thread_limits` boundary before curl or file
creation. Acquiring all 31 despite this finding would contradict the stop rule.

### Recomputed import closure, side effects and cryptography

The [static analyzer](../../scripts/inspect_phase08d8_sources.py) reverified all
20 existing sources, the three newly acquired files, the pinned non-truncated
tree, pyproject and lock metadata. It never executes source, imports native or
SDK modules, or constructs providers. Imports are labeled by module scope,
deferred function body, type-check-only scope and conditional/ImportError guard.
Function decorators/defaults and class-body calls are recorded as import-phase
execution. Dynamic lazy export targets and unresolved helper bodies are not
treated as proven safe.

```text
ordinary OpenAI-compatible provider import
  -> root initializer -> _thread_limits [MISSING, out of allowlist]
                        apply_default_thread_limits() [module-scope call]
  -> engine initializer [eager]
       -> cross_encoder [MISSING]
       -> embeddings [VERIFIED] -> orjson + local_device/retry helpers [MISSING]
       -> MemoryEngine module [VERIFIED] -> asyncpg + DB/SQL/search/retain/
                                            reflect/storage helpers [MISSING]
       -> llm_wrapper [VERIFIED] -> config/logging/semaphore setup
  -> providers initializer [VERIFIED] -> 13 sibling implementations [MISSING]
  -> provider [VERIFIED] -> helpers/metrics/tracing [MISSING]
  -> worker initializer -> poller [VERIFIED] -> schema/backpressure/exceptions [MISSING]
```

The known traversal contains **91 distinct source modules: 16 verified reachable
bodies and 75 missing bodies**. Of the missing bodies, 28 belong to the original
allowlist and **47 are newly exposed outside it**. The receipt's
`missing_source_frontier` gives every exact pinned path, raw URL, Git blob SHA-1,
expected byte count and required purpose/import line. No SHA-256 is claimed for
unacquired bytes. This frontier is not a complete closure: reading those bodies
can reveal further dependencies, conditional imports or side effects.

Known import-time execution includes the root's thread-limit call; wrapper
logging/config resolution and global/per-operation semaphore construction;
MemoryEngine module ContextVars, dataclasses, decorators and sentinel objects;
embedding module locks/class definitions; and poller dataclass/configuration
records. Module **imports** are distinct from engine/model/database **instance
initialization**. No actual database connection, model load or worker startup
was observed because nothing was executed. Safety cannot be inferred from that
absence: `_thread_limits`, cross-encoder, local-device, database and other missing
bodies remain UNKNOWN. Constructor prerequisites remain blocked; constructing
only the provider class cannot avoid its real package initializers.

Cryptography verdict remains: **REQUIRED by full distribution metadata,
NOT REQUIRED by the qualified SDK, UNKNOWN for ordinary native import and
provider methods**. No direct cryptography import was found in the 23 inspected
source bodies or the demonstrated package lower bound. Unacquired auth/provider,
database and observability modules prevent proving transitive absence. The
pinned lock still provides no compatible Intel macOS cryptography 50.0.0 wheel.
No downgrade, build, architecture substitution or security-floor change is
proposed. No cryptography installation authorization is justified yet.

### Revised minimal source/wheel plan and exact next authorization

| Evidence/status | Current result |
| --- | --- |
| VERIFIED first-party source | 20 prior cached files + 3 acquired initializers; 16 of these participate in the known traversal |
| READY reusable artifacts | 16 SDK wheels and one aiosignal wheel rehashed from current bytes; no SDK import or installed-runtime requalification in this continuation |
| MISSING source | 75 known source nodes: 28 unacquired prior-allowlist + 47 new out-of-allowlist; exact identities/purposes in receipt |
| MISSING wheels | 11 matching local artifacts in the bounded recorded inventory |
| UNKNOWN | Further source/third-party closure, missing-body side effects, native cryptography necessity and safe normal import/construction |

The known package lower bound increases from 26 to **28** because the ordinary
engine import requires `asyncpg==0.30.0`, and embeddings imports
`orjson==3.12.0`. The mandatory inspected external imports are aiohttp, asyncpg,
dotenv, httpx, json_repair, openai, orjson and pydantic. Their pinned lock closure
adds no further packages beyond the existing 26 plus those two on Python 3.12
Intel macOS. Conditional/deferred third-party imports and missing source bodies
remain separately unresolved. No optional extras/full distribution closure are
automatically selected.

The prior 16 SDK versions and ten helper versions remain as listed below.
Additional exact candidates are:

| Package | Candidate artifact | Bytes | SHA-256 |
| --- | --- | --- | --- |
| asyncpg 0.30.0 | `asyncpg-0.30.0-cp312-cp312-macosx_10_13_x86_64.whl` | 673,162 | `c902a60b52e506d38d7e80e0dd5399f657220f24635fee368117b8b5fce1142e` |
| orjson 3.12.0 | `orjson-3.12.0-cp312-cp312-macosx_10_15_x86_64.macosx_11_0_arm64.macosx_10_15_universal2.whl` | 223,427 | `aa3e43a6846e91d7bde3d5a9c66090fcd8744f569a9b6cffc5e1ca38f6a461c0` |

The receipt's `known_package_lower_bound` records an exact selected artifact for
all 28 packages, including filename/hash/length and the lock URLs for new wheel
candidates. The 11 missing selected wheel candidates total **1,647,815 bytes**.
This is a candidate lower bound, not an executable minimal installation plan.
Missing statuses reflect the existing bounded inventory, not a repeat machine
scan. No wheel or package was acquired/installed/built.

**Next authorization required: resume source-only inspection with an explicitly
expanded allowlist.** The exact known frontier is 75 files / **1,305,501 bytes**,
as enumerated in `missing_source_frontier` and summarized in `next_source_plan`.
It includes the 28 previously authorized but unacquired files and 47 newly
identified files. Start with `_thread_limits.py`, pinned Git blob
`2a690711d4651dbb75304248d11d5bf2f7fdaf2f`, exactly 4,780 bytes; its purpose is
to inspect the mandatory root import and module-level environment/thread-limit
call. A narrower authorization can cover that one file first, but would leave
the rest of normal native import blocked. Any expanded inspection must use the
same strict HTTPS/exclusive/hash controls and stop at a newly exposed frontier.
Neither source plan implies installation or execution authorization.

Do **not** install even the known 28-package set yet. Only a closed static source
graph and reviewed import-side-effect plan can justify a later exact wheel
acquisition/install proposal. No blank package initializers, `sys.modules`
stubs, extracted helper functions, rewritten native methods or weakened runtime
gate are approved. This evidence shows why the former conditional 26-package
proposal was insufficient; it does not justify preparing all 184 packages.

### Verification and readiness

Static analysis and [five source-only constraint checks](../../manifests/phase-08d8-source-constraint-tests.json)
ran using the existing repository SDK `.venv` interpreter with `-I -B`, an empty
environment, and the macOS deny-all-network profile. The interpreter hosts only
our verification code and standard-library parsing/hashing; upstream and SDK
modules are not imported. One initial static lock pass rejected an unsupported
Windows marker before producing a receipt; the final analyzer evaluates the
actual pinned marker syntax against an explicit Darwin/Python target without
`eval()` or upstream execution. Earlier derived receipts remain ignored and
preserved; the tracked receipt is the final pass.

Checks PASS: immutable 31-file allowlist/limit; three exact transport/integrity
receipts; tampered initializer rejected before parsing; further acquisition
rejected before curl with acquired files/log unchanged; and graph/package-plan
consistency. Source acquisition made three separately authorized HTTPS requests;
static inspection/tests made zero requests. No native/SDK/provider calls,
package acquisition/install/build, services, models, embeddings, RQ3, SSH or
Jetstream action occurred. Freeze v1, D1/D2, scientific denominators and all
historical artifacts remain unchanged.

| Dimension | Readiness |
| --- | --- |
| D3 | PARTIAL: global tasks/workers/quiescence not qualified |
| D4 | BLOCKED: native import closure/safety, complete send ownership and endpoint inclusive token bounds unresolved; existing startup gate unchanged |
| D5 | PARTIAL: prior scoped results preserved; native ownership/attribution unqualified |

**Stopped for independent review. No additional acquisition, installation or
native import/construction/method test is authorized by this report.**

## Original preparation at a452984 (historical scope and results)

CONVERSATION: Phase 08D-8 minimal native runtime preparation. MODEL: GPT-6
Codex runtime; no independent model-variant receipt. EXECUTION TARGET: assigned
local worktree `/Users/ian/.codex/worktrees/b648/Memo`. JETSTREAM ACTION: none;
remains SHELVED without querying infrastructure. Date: 2026-10-12,
America/Chicago.

The assigned checkout initially had clean detached HEAD `58ab52d`. The requested
base object was verified as `e07de9832572a910e7055d2df582b919146c35fd`, the SDK
installation/qualification commit. Review branch
`phase-08d8-native-runtime-preparation` was created at that exact base in the
assigned worktree. AGENTS, the project handoffs/debugging ledger, D6/D7 reports,
and the SDK acquisition and installation receipts were read. This prompt
authorizes this preparation only, superseding historical review-stop language
for the present offline work.

No package was downloaded, installed, built or copied into an environment. No
Hindsight module was imported or constructed. No service, MemoryEngine, database,
embedding, background worker, model, provider/hosted endpoint, empirical attempt,
RQ3, SSH or Jetstream action occurred. Publication is confined to this review
branch; main is not merged.

## Evidence and scope

The [preparation receipt](../../manifests/phase-08d8-native-preparation.json)
contains verified source identities, an import graph with execution-phase
labels, exact SDK identities, the known additional dependency inventory, and a
bounded source acquisition frontier. The
[verifier](../../scripts/prepare_phase08d8_native.py) reuses D6 source hashing
and D7 wheel/RECORD checks, but evaluates **imports**, rather than repeating the
send-site audit. The [negative controls](../../scripts/test_phase08d8_artifact_guards.py)
and [test receipt](../../manifests/phase-08d8-artifact-guard-tests.json) use
temporary copies of real cached artifacts, with no fake provider tests.

All upstream identities refer to Hindsight 0.10.1 commit
`f8950b0c07d9e34c76493dba802bb309f0ce60fd`. The existing non-truncated pinned
tree response is rechecked against SHA-256
`b23c03c1c9daf42b764988da19b5aa70e7bd710c8b05092f290773acef35ed33`.
The 19 D6 cached sources are reverified; the additionally inspected
`worker/stage.py` matches that same tree. All 20 sources parse, without executing
upstream code. Only eight cached modules are reachable in the known import
graph; the others are evidence inputs, not proposed runtime files.

Dependency metadata is reverified, not fetched:

| Artifact | Git blob SHA-1 | SHA-256 |
| --- | --- | --- |
| `hindsight-api-slim/pyproject.toml` | `e656821ca96c76b84a1d1cb1c7eb592f7f3b2563` | `4e73d3aae4711cb95639a2b3cfbe93ccf3a411b2ab3d4ad8924b7abc279930ec` |
| Workspace `uv.lock` | `cd9687ebaa9a749e506ed396fc95c6f48925072a` | `c2df90ff2364b524453662e880d872edbe6307b3bddea4dea8604c7a8455cb5c` |

The target remains CPython 3.12.8, Intel macOS. Lock selections are qualification
candidates, not a reconstruction of the historical remote runtime. Full
`hindsight-api-slim[embedded-db,local-onnx]` installation would resolve 184
packages; that is **not** the proposed provider-level environment.

## Minimal import graph and unresolved closure

Ordinary Python import of the native provider executes real parent package
initializers. The verified `engine/providers/__init__.py` imports 14 provider
implementations unconditionally, including OpenAI-compatible and **13 others**.
Importing the submodule by its full name does not avoid this initializer.
Therefore a list consisting only of the provider and OpenAI SDK is insufficient.

```text
ordinary import hindsight_api.engine.providers.openai_compatible_llm
  -> hindsight_api/__init__.py                    UNKNOWN body, missing
  -> engine/__init__.py                           UNKNOWN body, missing
  -> providers/__init__.py                        verified; 13 other providers
       -> alternate provider implementation bodies UNKNOWN, missing
  -> openai_compatible_llm.py                     verified
       -> openai, aiohttp                         mandatory third-party imports
       -> config                                 dotenv + pydantic
            -> _pg_search, _vector_index, utils   UNKNOWN bodies, missing
       -> aiohttp_session                        UNKNOWN body, missing
       -> bank_attribution, cache_affinity        UNKNOWN bodies, missing
       -> llm_interface -> response_models        response_models missing
       -> llm_trace -> db_utils                   db_utils missing
       -> llm_transport                          aiohttp + httpx + config
            -> aiohttp_session
       -> llm_wrapper                            json_repair + pydantic
            -> _cross_loop, provider_auth         UNKNOWN bodies, missing
            -> config + llm_transport + interface + cache_affinity
            -> google.oauth2.service_account      optional ImportError-guarded
       -> llm_debug, openai_compatible_headers     UNKNOWN bodies, missing
       -> structured_output, metrics              UNKNOWN bodies, missing
       -> worker/__init__.py -> worker/stage.py    initializer missing; stage verified
  successful native call/tools -> tracing.py      late import, missing
```

The receipt gives exact import lines and distinguishes unconditional module
imports, `ImportError`-guarded imports, imports inside methods/functions, and
`TYPE_CHECKING` imports. This is a **partial closure with an explicit frontier**:
31 required-to-inspect missing files, totaling 586,246 source bytes. It is not
a proof that these are the final complete source set or that 26 packages suffice.
Their bodies can reveal further mandatory dependencies or prohibited import
side effects. In particular, the top-level and engine initializers could expand
the import graph substantially before the provider is reached.

The factory's `from .providers import ...` is inside a function; direct class
construction avoids calling that factory, but does not avoid Python's parent
initializer. `llm_trace` has a mandatory module import of `db_utils` even though
the selected provider only needs its usage ContextVar. Database **imports** and
database **initialization** must be distinguished: whether `db_utils` can import
safely remains UNKNOWN. Function-local trace persistence/schema/database imports
are not automatically required for a provider test, but their containing modules
must still be inspected for module-level effects.

No function extraction, patched initializer, blank namespace package,
`sys.modules` stub, fake metrics/config module or catch-and-ignore missing import
is proposed. Those shortcuts would qualify a modified import environment and
could conceal side effects. If normal import proves inseparable from prohibited
initialization, stop and seek a separately reviewed isolation design; do not
silently expand to the 184-package runtime.

## Exact READY/BLOCKED package inventory

READY means verified artifact availability, not native-provider readiness.
The existing D7 environment contains exactly the following 16 distributions;
all were reverified against the immutable SDK acquisition plan and tracked D7
installation receipt, including wheel hashes, both RECORD sets, installed-byte
equality, and import origin. The receipt includes full wheel names/hashes/sizes
and installed `Requires-Dist` edges.

| READY: existing isolated SDK | Version |
| --- | --- |
| openai | 2.24.0 |
| httpx | 0.28.1 |
| httpcore | 1.0.9 |
| anyio | 4.14.2 |
| certifi | 2025.10.5 |
| distro | 1.9.0 |
| idna | 3.15 |
| jiter | 0.12.0 |
| pydantic | 2.12.5 |
| pydantic-core | 2.41.5 |
| annotated-types | 0.7.0 |
| sniffio | 1.3.1 |
| tqdm | 4.67.1 |
| h11 | 0.16.0 |
| typing-extensions | 4.15.0 |
| typing-inspection | 0.4.2 |

SDK dependency edges are OpenAI -> AnyIO, distro, HTTPX, jiter, pydantic,
sniffio, tqdm, typing-extensions; HTTPX -> AnyIO, certifi, HTTPCore, idna;
HTTPCore -> certifi, h11; AnyIO -> idna, typing-extensions on Python 3.12;
pydantic -> annotated-types, pydantic-core, typing-extensions, typing-inspection;
pydantic-core/typing-inspection -> typing-extensions. Optional HTTPX/HTTPCore
extras are not selected. No cryptography edge exists in this SDK set.

Verified cached source proves the additional mandatory direct imports of
`aiohttp`, `dotenv`, and `json_repair`. Their lock closure adds ten distributions:

| Additional package | Version | Dependency role | Artifact readiness / installation |
| --- | --- | --- | --- |
| aiohttp | 3.14.3 | Provider and transport direct import | BLOCKED: matching wheel absent; not installed |
| python-dotenv | 1.2.2 | config direct import | BLOCKED: matching wheel absent; not installed |
| json-repair | 0.63.2 | llm_wrapper direct import | BLOCKED: matching wheel absent; not installed |
| aiohappyeyeballs | 2.6.1 | aiohttp transitive | BLOCKED: matching wheel absent; not installed |
| aiosignal | 1.4.0 | aiohttp transitive | READY: existing matching cache wheel rehashed; installation not authorized |
| attrs | 25.4.0 | aiohttp transitive | BLOCKED: matching wheel absent; not installed |
| frozenlist | 1.8.0 | aiohttp and aiosignal transitive | BLOCKED: matching CPython 3.12/pure wheel absent; not installed |
| multidict | 6.7.0 | aiohttp and yarl transitive | BLOCKED: matching wheel absent; not installed |
| propcache | 0.4.1 | aiohttp and yarl transitive | BLOCKED: matching wheel absent; not installed |
| yarl | 1.22.0 | aiohttp transitive | BLOCKED: matching wheel absent; not installed |

Aiohttp additionally reuses SDK typing-extensions on Python <3.13; aiosignal
also needs frozenlist and typing-extensions; yarl needs SDK idna, multidict and
propcache. python-dotenv/json-repair have no base lock dependencies. Each
candidate wheel has an exact URL, filename, size and SHA-256 in the receipt.
Use locked pure Python wheels where supplied; otherwise the exact CPython 3.12
Intel wheel. No speedups, CLI, HTTP2, SOCKS, tracing/exporter or model extras are
selected merely because they exist.

The nine missing candidate wheels total 751,226 bytes; the reusable aiosignal
wheel is 7,490 bytes. These are **known dependency candidates**, not authorization
to acquire/install them and not a completed native runtime plan. Other-version
installed metadata, CPython 3.13 native wheels and unrelated Conda/bundled
environments do not satisfy this target. Missing source bodies make additional
third-party imports UNKNOWN. Google auth is optional at the inspected wrapper
site, but may be mandatory elsewhere through eager alternate providers; do not
generalize that local optionality to the whole import graph.
Missing-wheel status is bounded to D7's recorded inventory; no repeat broad
machine/cache scan was performed. The SDK stage and the one matching helper
wheel were rechecked from actual current bytes.

An installed `hindsight-api-slim` distribution and complete reproducible native
source tree remain BLOCKED. There is no locally verified release wheel for it.
The first-party source-only proposal must not be described as an installed,
dependency-compliant Hindsight distribution.

## Required first-party source artifact identities

Paths below are relative to `hindsight-api-slim/hindsight_api/`. Eight verified
cached modules participate in the known graph. Their full SHA-256 and byte
counts are recorded in the receipt; the pinned Git blob identities are:

| Verified source | Git blob SHA-1 |
| --- | --- |
| config.py | `20436ec768e9fde0dbc7291c9d5d9718611b2967` |
| engine/llm_interface.py | `052397b6495afbb72d8f6711d51c280354d41aab` |
| engine/llm_trace.py | `a5300b872495fe9bf32fd7d2ecd72f6aa6aea20a` |
| engine/llm_transport.py | `afbbaaa451faa724d43ec55983aa0439ff69e02f` |
| engine/llm_wrapper.py | `76575260f47a1ea20efe610710ee16a315bbfa10` |
| engine/providers/__init__.py | `5f8e42ecc549e1ea35b4d6472c71ae755935f6f6` |
| engine/providers/openai_compatible_llm.py | `ae5952f216ca9dcd78435ce7f1966ddfb0b1515b` |
| worker/stage.py | `9bd2f53d9c5af301915592b065d64639faaf32f8` |

The exact 31-file missing-source allowlist, with commit-qualified raw URLs,
individual Git blob SHA-1 identities and lengths, is
`missing_source_acquisition_frontier` in the receipt. It consists of:

- Package initializers: `__init__.py`, `engine/__init__.py`, `worker/__init__.py`.
- Config/wrapper helpers: `_cross_loop.py`, `_pg_search.py`, `_vector_index.py`,
  `utils.py`, `engine/provider_auth.py`.
- Provider helpers: `engine/aiohttp_session.py`, `engine/bank_attribution.py`,
  `engine/cache_affinity.py`, `engine/db_utils.py`, `engine/response_models.py`,
  `engine/structured_output.py`, `engine/providers/llm_debug.py`,
  `engine/providers/openai_compatible_headers.py`.
- Observability modules: `metrics.py`, `tracing.py`.
- Eager sibling implementations: `engine/providers/anthropic_llm.py`,
  `claude_code_llm.py`, `codex_llm.py`, `cursor_llm.py`, `fireworks_llm.py`,
  `gemini_llm.py`, `github_copilot_llm.py`, `litellm_llm.py`,
  `litellm_router_llm.py`, `llamacpp_llm.py`, `mock_llm.py`, `none_llm.py`,
  `openai_responses_llm.py` (all in `engine/providers/`).

Missing files have no claimed SHA-256 because their bytes have not been
acquired. The existing verified tree pins their Git blob hashes and lengths;
future acquisition must verify both and then record SHA-256 before parsing.
Cached sources and metadata live outside this assigned checkout. The verifier
requires explicit paths and does not assume these ignored files are portable
or tracked. A clean clone alone is insufficient to reproduce native imports.

## Cryptography verdict

Three different requirements must remain separate:

1. **Full distribution metadata: REQUIRED.** The pinned pyproject directly
   declares `cryptography>=50.0.0` as a security floor. The lock selects 50.0.0
   with a cffi dependency on CPython. Omitting it from a full installation or
   downgrading it would violate this metadata, irrespective of provider choice.
2. **Qualified SDK closure: NOT REQUIRED.** The exact 16-package SDK metadata
   and successful imports do not require cryptography. Python's standard TLS
   support is not the cryptography distribution.
3. **Restricted ordinary native import/method closure: UNKNOWN.** No inspected
   mandatory provider/config/wrapper import directly imports cryptography.
   However, missing parent initializers, eager auth/provider siblings, metrics,
   tracing and db_utils prevent proving its absence from the transitive graph.
   Thus it is not demonstrated essential for this test, nor proven removable.

The pinned lock has **zero compatible Intel macOS wheels for cryptography
50.0.0**, as rechecked from its artifact list. This is a limitation of this
specific resolution/artifact set, not a newly checked claim about current PyPI
availability or a demonstrated CPU instruction failure. Other local versions
and architectures do not satisfy it. **No workaround is proposed.** First
inspect the minimal source frontier. If a mandatory restricted import requires
cryptography, return for separately reviewed platform/artifact/build planning;
do not substitute versions, weaken security floors, switch architectures or
build from source under this authorization.

## Initialization and interception proposal

These are prerequisites for a future native-provider test, not executed probes.
The native provider body remains intact.

| Boundary | Safe proposed scope / condition |
| --- | --- |
| Before any native import | Deny all network including loopback at OS level; install socket/DNS audit denial. Reject service/MemoryEngine/embedding/task/worker entrypoints and imports with unreviewed module side effects. Inspect real parent initializers first. |
| config / llm_wrapper import | Controlled empty environment; never call `load_dotenv_for_entrypoint()`. Cached config source loads dotenv only in that explicit helper. Wrapper import itself calls logging configuration, resolves raw config, and constructs global/per-operation `CrossLoopSemaphore` objects. Cross-loop implementation is missing, so its safety is UNKNOWN. |
| Direct provider constructor | Construct only `OpenAICompatibleLLM(provider="openai", api_key="offline-sentinel", base_url="https://native.test/v1", model="offline-model", timeout=...)`; bypass factory invocation, not package initialization. Constructor creates AsyncOpenAI and a LoopLocalSession wrapper. Confirm wrapper construction opens no aiohttp session/task; its source is presently missing. |
| SDK creation in constructor | Intercept the provider module's `AsyncOpenAI` factory with a delegating factory that constructs the **actual qualified SDK**, records native kwargs verbatim, and supplies only the offline HTTP transport. Do not replace the SDK or completion resource with fakes. Preserve native SDK retries, headers, default query and timeout arguments. |
| HTTPX and HTTPCore | Reuse D7 transport instrumentation, immutable scripted HTTP responses/streams and pipe-based event loop. Record native invocation, SDK create, HTTPX dispatch, HTTPCore connection/request-start and usage separately. Default-equivalent redirect/routing settings need parity checks; an explicit `trust_env=False` variant must be labeled as such. No live TLS/socket claim. |
| Native startup probe | Call provider `verify_connection()` only, after construction/import safety is established. Its native two-retry configuration remains intact. Never initialize an engine to reach it. |
| Native structured/unstructured/tool calls | Invoke actual `call()` and `call_with_tools()`, with real pydantic schemas and native tool-choice types. Preserve soft JSON prompt augmentation, strict schema conversion, token-cap adjustments, extra-body merging, attribution/cache headers and raw SDK usage before native transformations. Successful calls also need real metrics/tracing modules. |
| Native retries | Script status/connection/read/JSON-validation failures at transport/response level. Preserve native exceptions and retry loops; count every SDK/HTTP attempt. Native `attempt_context` can observe per-attempt entry but is not a replacement for transport counting. Do not replace `call`, parsing helpers or retry logic. |
| Cleanup | Use native `cleanup()`; prove SDK and any loop-local session close, no pending tasks, no extra imports/sends, and no credential/environment inheritance. |

No full-engine topology, independent worker, role/multi-LLM client, batch,
Responses, Ollama-native or alternate provider is qualified by this procedure.
These remain outside the restricted method test. The unconditional repository
runtime BLOCKED gate is untouched; a future isolated engineering test must not
turn it into a launcher or readiness exception.

## Smallest proposed procedure and acquisition/install plan

The **smallest established reusable component** is the exact verified 16-package
SDK environment. A smallest complete native environment is not yet known;
pretending the known 26-package lower bound is sufficient would conceal the
eager imports. The next bounded authorization should be **source inspection
only**, with no wheel acquisition or installation yet:

1. Exclusively create `.local/phase08d8/source-frontier/` in the assigned
   checkout. Read the three missing parent initializers first, using their
   exact allowlisted URLs/identities. Continue through the remaining 28 files
   only within the same 31-file allowlist. Do not fetch a repository archive,
   follow branches, update a tag, clone an unpinned tree or acquire a wheel.
2. HTTPS requests may target only the exact
   `raw.githubusercontent.com/vectorize-io/hindsight/<pinned-commit>/<path>`
   URLs in the receipt. Empty environment; no curl config, proxy, netrc,
   credentials or redirect following; verify TLS. Record status, effective URL,
   redirects, byte count, Git blob SHA-1 and SHA-256. Exclusive destination files;
   never overwrite cached evidence. Maximum source body bytes: 586,246.
3. Parse sources only. Resolve mandatory imports and parent initialization
   side effects recursively. **Stop if a dependency leaves the allowlist** or
   needs prohibited initialization. Produce a supplemental exact source and
   wheel closure for review. Uninspected modules are UNKNOWN, not optional.

The receipt also supplies exact candidate artifacts for the ten known helper
dependencies. If later source closure proves them sufficient, the subsequent
installation proposal is a fresh repository-owned
`.local/phase08d8/native-runtime/.venv` created with the existing repository
interpreter and `--without-pip`. Reuse the 16 D7 wheels after rehashing, and the
existing aiosignal wheel after rehashing; acquire only the nine missing
allowlisted candidates. **This conditional 26-package plan is not yet complete
or executable.** Any further mandatory dependencies require their own explicit
identities and review, and the currently known candidates are not acquired now.

The later offline installer must use existing repository pip with `--python`
targeting the fresh venv, `--no-index --no-deps --require-hashes
--only-binary=:all: --no-cache-dir --no-compile`, an explicit deny-network OS
profile and no system/user-site or `.pth` inheritance. No editable build,
Hindsight packaging build, source distribution, global or `--user` install.
First-party files would be reconstructed as verified unchanged source files
with real package initializers after closure inspection, not installed as a
falsely dependency-compliant Hindsight distribution.

Only after separately authorized complete acquisition/installation should an
import-only subprocess validate actual native class/module identities with
network denied and no constructor/method call. If that succeeds and safety
conditions hold, a **separate native-method qualification authorization** can
cover constructor, startup probe, unstructured/soft/strict JSON, tools, native
retry/error/usage paths and cleanup against D7's offline transport. It cannot
authorize an engine/service/model or empirical run. No native import-only test
was attempted here because the existing verified artifacts do not suffice.

## Authorized verification results and readiness

Verification used the existing repository SDK interpreter at
`/Users/ian/.codex/worktrees/2373/Memo/.local/phase08d7/runtime/.venv/bin/python`
with `-I -B`, an empty environment, and macOS
`(version 1)(allow default)(deny network*)`. Python audit self-tests rejected
socket creation and DNS before syscalls; subsequent imports attempted neither.
The outer execution sandbox initially prevented applying the macOS sandbox;
the authorized tool escalation applied that same explicit network-denial
profile. No network policy was relaxed.

The D7 installation loader intentionally binds artifacts to its own worktree.
An initial reuse attempt rejected a different caller ROOT before verification;
the final verifier instead checks the immutable D7 plan hash and its original
explicit paths without changing D7 code/artifacts or rebinding ignored paths.
The initial successful preparation receipt remains ignored and preserved; the
tracked receipt comes from the final verifier.

| Check | Result |
| --- | --- |
| SDK distribution identities and import origins | PASS: exactly 16 distributions; 16/16 imports |
| Wheel / installed RECORD hashes | PASS: 1,412 / 1,464 hashed files |
| Installed SDK bytes equal qualified wheel bytes | PASS |
| Pinned source/tree and pyproject/lock identities | PASS: 20 sources, tree, two metadata artifacts |
| Existing aiosignal wheel identity | PASS: exact 7,490-byte locked wheel |
| Artifact guard negative controls | PASS: 4/4; source/tree/metadata tampering rejected; existing receipt preserved |
| Original source/metadata hashes after negative controls | Unchanged |
| Canonical Git-source Freeze v1 validation | PASS: `0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b` |
| Socket/DNS attempts during package imports | 0, excluding two deliberately denied guard self-tests |
| Native import / constructor / method calls | NOT EXECUTED / 0 / 0 |
| New acquisition / installation / source builds | 0 / 0 / 0 |

To reproduce artifact verification where the same explicitly named ignored
inputs still exist, use the verifier with `--source-cache /private/tmp/hindsight_audit`,
`--pinned-tree /private/tmp/phase08d5-pinned-tree.json`,
`--metadata-root /Users/ian/.codex/worktrees/2373/Memo/.local/phase08d7`, and
`--output <new-exclusive-receipt-path>`, under the interpreter/profile above.
The guard-test script accepts the same arguments. Neither script acquires
inputs. Missing inputs fail; a clean checkout is not claimed self-sufficient.

| Dimension | Updated verdict | Remaining limitation |
| --- | --- | --- |
| D3 | PARTIAL | No engine/task replay/global quiescence or cross-worker coverage established. |
| D4 | BLOCKED | Faithful native import closure incomplete; no native method qualification, complete runtime send ownership, or endpoint-enforced inclusive token bound. |
| D5 | PARTIAL | Existing owned-fake governance and SDK transport observations remain valid within their scopes; native attribution/ownership remains unqualified. |

D1/D2 evidence, Freeze v1 and the v2 draft, historical attempts and scientific
denominators remain unchanged. No experiment row or eligible empirical context
was added. Honcho Candidate10 remains frozen NO_GO; OpenViking S0 r2 remains
ERROR. **Next authorization: the bounded 31-file pinned source inspection plan
above. No package installation, cryptography workaround, native startup or live
execution is authorized. Stop for independent review.**
