# Phase 08D-8 — Minimal Hindsight Native Runtime Preparation

**Authorized source inspection STOPPED after 3/31 files (7,029 bytes). Parent
initializers expose mandatory imports outside the allowlist. The known frontier
is now 75 missing source nodes; the known package lower bound is 28. Complete
native closure remains UNKNOWN. D3 PARTIAL, D4 BLOCKED, D5 PARTIAL.**

## Authorized pinned source inspection continuation

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
