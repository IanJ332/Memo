# Phase 08D-9 — Provider Boundary Architecture Design Review

**Decision: propose B, a versioned three-initializer lazy-export refactor, for
independent review. No implementation or runtime qualification occurred.
D3 PARTIAL; D4 BLOCKED; D5 PARTIAL.**

CONVERSATION: Phase 08D-9 provider boundary architecture design review.
MODEL: GPT-6 Codex runtime; no independent model-variant receipt.
EXECUTION TARGET: local worktree `/Users/ian/.codex/worktrees/812d/Memo`,
documentation only. JETSTREAM ACTION: none; remains SHELVED without querying
infrastructure. Date: 2026-10-13, America/Chicago.

Expected base `16fdb42afd4e1638dba1f2e38cf5cb3e57fdb897` was verified as an
ancestor of freshly fetched `origin/main`; that ref was exactly the expected
SHA. The assigned checkout was clean before creating
`phase-08d9-provider-boundary-design` at that base. Git publication is authorized
only for this documentation review branch. Main is not merged by this phase.

## Evidence and scope

Read AGENTS.md, the project handoff/state/debugging ledgers and the
[D5](PHASE_08D5_GOVERNED_SEND_INSTRUMENTATION.md),
[D6](PHASE_08D6_NATIVE_RUNTIME_QUALIFICATION.md),
[D7](PHASE_08D7_RUNTIME_DEPENDENCY_PREPARATION.md) and
[D8](PHASE_08D8_MINIMAL_NATIVE_RUNTIME_PREPARATION.md) reports. Design evidence
includes the immutable [adaptive source receipt](../../manifests/phase-08d8-adaptive-source-closure.json)
and [SDK qualification receipt](../../manifests/phase-08d7-sdk-installation-qualification.json).
Their current SHA-256 identities are respectively
`772680fb16cc79b2dd85b8c07ae435a07e56b6329f926e84ed6b3457991f87dd`
and `bd93ebf5b537c0c53a7c9570b6ae4daf810d42891d40b6477855108b05d13aca`.
Existing cached pinned source and dependency metadata were read as text only.
No source acquisition, transformation, native import, SDK execution, dependency
installation or empirical experiment was performed.

D8 resolved the demonstrated mandatory literal graph at 125 modules, within
131 verified source identities. Its ordinary-import metadata closure is 61
packages: 24 ready artifact slots, 36 missing matching artifacts and one locked
Intel macOS gap, cryptography 50.0.0. The full distribution resolution is 184
packages. These are different closures; neither graph resolution nor artifact
availability certifies safe execution. Dynamic, conditional, deferred and
third-party effects remain separately unqualified.

D7 qualified OpenAI 2.24.0, HTTPX 0.28.1 and HTTPCore 1.0.9 within its exact
16-distribution environment: 30 cases, 33 SDK invocations, 43 HTTPX requests,
9 scripted core connection attempts and 7 serialized request starts. Actual SDK
socket transmissions were zero. D7 observed redirects despite SDK retries zero,
transport retries below HTTPX, body overrides changing the wire model, resource
replacement rerouting requests, and copies sharing an HTTP client. Scripted
streams/TLS do not certify live physical sends, DNS, TLS or endpoint bounds.

## ADR-08D9-01: choose the smallest explicit engineered bootstrap

**Status: PROPOSED, independent review required.** The aim is to exercise the
actual pinned provider class and unchanged methods with the actual qualified SDK
and deterministic offline transport. It is not to construct MemoryEngine or
claim that the unmodified Hindsight application has been qualified.

Paths in the next tables are relative to `hindsight-api-slim/hindsight_api/`
at commit `f8950b0c07d9e34c76493dba802bb309f0ce60fd` (Hindsight 0.10.1).
Option labels here follow the Phase 08D-9 request; D8 called faithful import A.

| Alternative | Dependency footprint | Source changes and semantic divergence | Auditability / reproducibility | Long-term maintenance | Decision |
| --- | --- | --- | --- | --- | --- |
| A. Upstream-supported provider-only entrypoint | Would be preferable if the pinned upstream supplied an independently importable provider package with its own complete metadata. That artifact is not established by the inspected pin. Direct import of the exported class still executes eager parent initializers. | No local upstream change if such an entrypoint exists; its configuration and helpers must still be qualified. Moving to a different release changes the pin and requires review. | Strongest provenance if upstream ships/hash-pins it. A name exported by `providers/__init__.py` is not proof of independent packaging. | Lowest local patch burden, but depends on upstream contract/version support. | Not currently actionable at this pin. Reconsider if independent evidence establishes a supported artifact; no upstream outreach or new acquisition authorized here. |
| B. Minimal versioned lazy-export refactor | Removes eager MemoryEngine/search/embedding/poller/sibling-provider roots. Retains real config, parser, response models, metrics/tracing and their dependencies. Smaller than C, larger than SDK-only. | Exactly three initializer files proposed to change; provider and helper bodies unchanged. Import timing, side effects and failure timing necessarily diverge. Test injection is an additional explicitly labeled engineered component. | Small reviewable patch; original and resulting hashes, exact export maps and closed source manifest. Normal Python imports, no stubs or extracted functions. | Local patch must be re-reviewed at every upstream pin; lazy resolution, circular imports, export identity and optional dependency behavior need regression checks. | Recommended conditionally, with staged STOP gates below. No claim that B is already correct or qualified. |
| C. Faithful ordinary import with complete closure | Reference baseline: 125 demonstrated modules / 61 declared import-root packages, plus any runtime-discovered requirements. A fully installed upstream distribution must honor its complete metadata; the 61-package slice is not such an installation. | No bootstrap/method changes. Full ordinary import preserves eager effects; test transport injection still must be labeled separately from default runtime. | Best differential reference once exact sources, metadata, platform and artifacts are available. Currently missing artifacts and locked crypto gap prevent declaring it ready. | No local bootstrap patch; larger artifact/platform maintenance and third-party side-effect review. | Retain as reference baseline. Do not acquire 184 packages by default or downgrade crypto to make it run. Compatible reference planning needs separate authorization. |

At the inspected pin, the root already uses real lazy exports but deliberately
calls `_thread_limits.apply_default_thread_limits()`. The engine initializer
eagerly imports MemoryEngine and supporting modules; the providers initializer
imports 14 implementations, including the selected provider and 13 siblings;
the worker initializer imports WorkerPoller. The pyproject's console entrypoints
are API, worker, local MCP and admin, not a demonstrated provider-only package.
This is a conclusion about the inspected pin, not all upstream releases.

B is preferred because it attacks the demonstrated bootstrap coupling without
changing provider behavior or fabricating helper replacements. Keep real root
initialization, config/environment defaults, native JSON parsing, native response
types, metrics, tracing and lazy loop-local session implementation. The root's
thread defaults and CPU/cgroup reads are explicit accepted import effects to
record. A no-op collector already supplied by native code is acceptable; a fake
metrics/tracing module or deleting imports to obtain one is not.

The refactor replaces eager export statements with a name-to-module/attribute
map and PEP 562 resolution, analogous to the real root: retain every `__all__`
export and its actual target, cache the resolved actual object, provide `__dir__`
and type-check-only reexports, and raise `AttributeError` for unknown names.
Import failures propagate when a requested target is resolved. `from package
import *` will resolve the full export set and may need the full dependencies;
it is outside the provider-only path. Existing public identities are preserved,
but eager failure/side-effect timing is intentionally changed. Do not claim
full-package import-semantic equivalence.

## Source provenance and transformation boundaries

The immutable originals remain authoritative; produce an exclusive derivative
source tree in a new repository-owned ignored directory. Never patch the old
source cache, installed D7 environment or an upstream checkout in place.

| Original file | Git blob SHA-1 | SHA-256 | Proposed treatment |
| --- | --- | --- | --- |
| `engine/__init__.py` (1,546 bytes) | `8ec70075bae971adef5d6bd941a2f1db7fe1787c` | `abdce96a0c096bf31ffeacc9e4390d5f72ca6ff4dbc38636caf14857aadc6863` | Modified lazy exports only |
| `engine/providers/__init__.py` (987 bytes) | `5f8e42ecc549e1ea35b4d6472c71ae755935f6f6` | `ba35543c65d3166834eb0b03ce20da749dc384793d7b64c1eaef3ff4458df41a` | Modified lazy exports only |
| `worker/__init__.py` (256 bytes) | `8eb27f9f0d8ce79fc4c29f731d4cbf40615f550a` | `873a4c2ef39f80bd8a2abae293ff68baf13309dbc94ab1fea63e547452badc9d` | Modified WorkerPoller export only |
| `engine/providers/openai_compatible_llm.py` (105,773 bytes) | `ae5952f216ca9dcd78435ce7f1966ddfb0b1515b` | `7c6aad58263b6b4134a7a67c2c5c289d22d106c90532f15a321fc28f6b05abae` | Entire file byte-identical, including constructor, calls, retries, parsing, batch/Ollama bodies and cleanup |

All other included source identities must come from `verified_sources` in the
adaptive receipt, with original path, size, Git blob hash and SHA-256, not copied
informally from a working tree. Retain the root `__version__ = "0.10.1"` so native
headers remain identical; that string alone must never identify this runtime.
Root and `_thread_limits.py` remain unchanged. No change to `llm_wrapper.py`,
`llm_trace.py`, `db_utils.py`, config, metrics/tracing or provider imports is
proposed. Do not extract `parse_llm_json`, migrate ContextVars, omit real package
initializers, use `sys.modules` stubs or an import hook that supplies fake modules.

The future reproducible manifest must contain:

- Schema version; upstream repository, exact commit, tree/metadata/receipt
  hashes; license/notice identities; target interpreter/platform; selected
  native method/configuration scope and excluded features.
- Each source's original identity and classification `UNCHANGED_NATIVE_SOURCE`
  or `MODIFIED_BOOTSTRAP`, derivative path/size/SHA-256/Git blob identity, and
  inclusion reason. Hash source bytes with original LF representation; reject
  EOL or content drift. A separate observed-tree hash binds actual materialized
  bytes. Never overwrite a mismatch or accept multiple source hashes.
- A versioned patch/transform specification with exact original preconditions,
  the three permissible paths, export target maps, diff hash and transformer
  identity. Any hunk outside those paths is STOP. No hashes of future modified
  files are invented in this design; they must be recorded before execution.
- Sorted source/dependency manifests with a specified canonical serialization
  (UTF-8 JSON, sorted keys, compact separators, LF terminator); exact wheel
  names/hashes/sizes, markers/extras, metadata and installed RECORD identities.
  Native source identity and installed-distribution identity are separate.
- Test adapter/harness Git commit and file hashes; actual SDK factory injection,
  HTTP transport/backend identity and settings; controlled environment and
  import effects; fixture/receipt hashes and evidence-layer labels.

Proposed identity:
`memlife-hindsight-provider-boundary/0.1.0+upstream.f8950b0c07d9`, additionally
bound to manifest and patch SHA-256. Changed inputs require a new immutable
identity/receipt; no mutable "latest" lookup. Qualification receipts must say
`ENGINEERED_PROVIDER_BOUNDARY`, `UNMODIFIED_HINDSIGHT_RUNTIME=false`, with
unchanged native method provenance separately reported. Scoped replacement of
the provider module's `AsyncOpenAI` binding by a delegating construction adapter
is a runtime transformation even if provider file bytes stay unchanged: record
original callable origin, replacement identity, activation/restoration scope and
kwargs. No global SDK class patch is proposed.

A source slice does not satisfy `hindsight-api-slim`'s full Requires-Dist.
If packaged later, use a distinct engineered distribution name, preserve native
module paths and licensing, declare that slice's complete reviewed metadata and
forbid coexistence with another distribution owning `hindsight_api` in the
qualification environment. Do not edit upstream pyproject requirements or
advertise a truncated installation as upstream Hindsight. Initial source
materialization can avoid a packaging build altogether.

## Candidate package boundary and remaining dependencies

```text
isolated offline qualification entrypoint (no engine/service launcher)
  -> engineered bootstrap manifest / import gate
  -> real root + lazy engine/providers/worker packages
  -> unchanged OpenAICompatibleLLM + unchanged real helpers
  -> scoped actual-SDK construction adapter + raw-usage observer
  -> owned final-request admission transport
  -> pinned HTTPX / HTTPCore, retries constrained and audited
  -> deterministic scripted backend; OS denies all network
```

A counterfactual traversal of D8's recorded graph, suppressing only eager import
edges in the three proposed initializers and retaining the successful-call
tracing seed, projects **29 source modules and 41 declared packages**. This is
design analysis over the existing receipt, not a transformed-source closure
receipt, import test or install allowlist. Recompute from the actual derivative
before accepting these numbers. Conditional imports and method-time behavior
can enlarge it.

The projected direct roots are aiohttp, HTTPX, OpenAI, pydantic/pydantic-core,
python-dotenv, json-repair, SQLAlchemy and the real OpenTelemetry
API/SDK/Prometheus/OTLP HTTP exporters. Config reaches `_pg_extensions` through
its helpers, which imports SQLAlchemy's `text`; retain this real import rather
than remove it. Database import does not authorize a database connection.
Successful native methods import tracing even with no exporter initialized.

In addition to D7's 16 pinned SDK distributions, expected candidates are:

| Family | Expected additional locked distributions / versions |
| --- | --- |
| Native HTTP/config/parser | aiohttp 3.14.3, aiohappyeyeballs 2.6.1, aiosignal 1.4.0, attrs 25.4.0, frozenlist 1.8.0, multidict 6.7.0, propcache 0.4.1, yarl 1.22.0, python-dotenv 1.2.2, json-repair 0.63.2 |
| Configuration helper metadata | SQLAlchemy 2.0.44, greenlet 3.2.4 |
| Real observability imports | opentelemetry-api/sdk/proto/exporter-otlp-proto-common/exporter-otlp-proto-http 1.44.0; exporter-prometheus and semantic-conventions 0.65b0; googleapis-common-protos 1.75.0; protobuf 7.35.1; prometheus-client 0.23.1; requests 2.34.2; charset-normalizer 3.4.4; urllib3 2.7.0 |

This projected closure has no Google GenAI/Auth/cryptography edge. It does not
remove upstream's cryptography security floor from a full distribution or prove
all dynamic dependencies absent. Preserve the native optional Google OAuth
import's real ImportError behavior; never supply a stub. A fresh isolated slice
environment intentionally excludes optional Google support, while reference
comparisons must document whether it is present. Missing or incompatible wheels,
new import roots, security-floor conflicts and unexpected helper effects require
review, not installation or a quiet fallback. No new artifact readiness claim
is made here.

## Semantic parity contract

Three claims must be kept distinct: byte-identical native method provenance;
measured method behavior under an engineered bootstrap/transport; and observed
equivalence to C's ordinary-import baseline. Identical method bytes are necessary
but insufficient for the last two. Compare both variants in separate processes
with identical fixtures, environment, clock/random controls where needed, SDK,
transport injection and invocation arguments. C must retain real initializers.
If C cannot run, report differential parity `NOT_EXECUTED`, never PASS.

The initial positive scope is one direct `OpenAICompatibleLLM(provider="openai")`
instance, explicit `.test` HTTPS base URL, synthetic key/model, nonstreaming chat
completions, native `verify_connection`, `call`, `call_with_tools` and `cleanup`.
Model-name variations exercise native shaping without executing those models.
No `LLMProvider` factory, ConfiguredLLMProvider or multi-LLM construction is
implicitly covered. Rejected configurations are explicit exclusions, not
parameters silently rewritten into accepted ones.

| Invariant / measurable oracle | Existing D7 capability | Additional qualification / permission required |
| --- | --- | --- |
| Configuration: constructor argument/default resolution, `get_config` cache behavior, timeout phases, headers, query extraction, cache/bank attribution and allowed environment effects match pinned source and, when available, C | Real SDK accepts actual kwargs and supports controlled environment/routing fixtures | B materialization, real helpers/dependencies, import and constructor permission; record config/logging/thread defaults without replacing them |
| Model/endpoint: compare constructor identity, effective SDK base URL and final serialized wire model; include `extra_body` precedence and query-bearing base URLs | D7 demonstrates base/query/body overrides and model replacement | Native-method fixtures; admit effective wire value, never just `self.model` |
| Request body/headers/query: exact body-byte hashes, ordered URL/query representation and stable headers equal between B/C under the same harness | HTTPX/core capture is available; D7 is not native evidence | Native calls and snapshot oracle; normalize only explicitly listed SDK-generated IDs/timing in comparison, retain their raw receipts; synthetic Authorization may be inspected privately, real credentials never persisted |
| Structured/unstructured: strict pydantic schemas, soft JSON prompt augmentation, fences/reasoning stripping, repair only at native allowed finish states, missing/empty content and length/validation errors preserve results/types | SDK response fixtures available | Actual pydantic/native parser/helper execution and cases; no fake parser or schema helper |
| Tools: AUTO/NONE/REQUIRED/named selection, native filtering/strict schemas, messages, malformed arguments (`_raw`), finish reason and tool IDs/results unchanged | Real SDK tools success qualified | Native tool method fixtures, real LLMToolChoice/response types; schemas compare complete structures, not only names |
| Reasoning/token caps: parameter names, explicit omission, native model-specific 16000 floor where applicable, temperature suppression, reasoning_effort, service-tier and extra-body merging match | SDK serializes parameters; raw reasoning/cache usage fixtures can be supplied | Native shaping tests; preserve floor, do not lower cap to fit admission. Tool and ordinary call shaping are tested separately. Output cap is not an inclusive bound |
| Exceptions: SDK class/status/cause, native OutputTooLongError/quota/reset/ProviderResponseError/JSON validation behavior and verification wrapping match ordinary provider behavior for admitted fixtures | SDK status/connect/read/cancel controls available | Native exception/retry fixtures; raw transport error passes through unchanged in observation mode. Governance denial is separately labeled intentional divergence |
| Retries/failover: native retry budget, backoff schedule, status/auth/quota classification and parse retries produce the expected ordered SDK/HTTP/core events | D7 proves SDK/core multiplicity separately | Native loops tested with bounded real delays or explicitly labeled harness clock control. Native multi-LLM failover remains unqualified and unsupported; it cannot be inferred from direct provider success |
| Raw SDK usage: receipt captured before native missing-usage-to-zero or visible-output transformations; prompt/completion/total, reasoning/cache subsets and missing/malformed raw values preserved | SDK fixtures and actual response objects available | Instance-scoped observation adapter/native calls. Correlate each response to its physical-attempt receipt; compare native transformed result independently |
| Lifecycle: native cleanup closes SDK and any created loop-local sessions, cancellation propagates, no new send/admission after close, no leaked tasks/descriptors and no side-effect engine/database imports | D7 client-copy close/cancellation and scripted-stream cleanup qualified | Actual constructor/cleanup and cross-loop native session checks. No aiohttp inference path accepted; no unreviewed third-party task/exporter startup |

Observation/parity mode forwards exact native requests, returned SDK objects and
exceptions without accounting-driven substitution; it is offline only, bounded
by finite fixture sequences, watchdog/resource ceilings and deny-network policy.
Governed mode reserves and may reject: denial, receipt I/O and failure latching
are designed semantic differences. Do not use governed failures as proof of
transparent exception parity. Existing D5 fake-only admission cannot simply be
applied to real native calls: it rejects extras and changes failures. Reuse its
invariants and evidence vocabulary only after reviewing compatibility.

Minimum method-contract acceptance requires: all included unchanged hashes
match; no unapproved imports/side effects; every listed applicable matrix case
has source-derived expected outcomes and complete raw receipts; zero mismatches
in request, schema, result, exception classification, retry order and cleanup;
zero unmatched request starts; all negative controls reject at their specified
boundary. Source-derived fixtures can qualify the engineered method contract,
but are weaker than executing C. Strong **B/C observational parity PASS** requires
the same fixture corpus against the actual ordinary-import reference, with zero
unexplained differences. A blocked C leaves this stronger claim unresolved and
does not prevent an explicitly limited engineered-boundary receipt.

## Transport ownership and attempt admission

The inference accounting unit is a dispatched, serialized inference request
attempt, not a native method, SDK `create`, HTTPX dispatch, TCP connection or
stream `write`. One request can have many writes; a connection failure can have
zero request starts; one SDK invocation can redirect/retry into several requests.
Retain all those counts separately. Offline scripted starts are simulations;
this phase and any proposed offline test have zero accepted live sends.

1. **Own construction before any probe.** A scoped provider-module factory
   delegates to the actual pinned AsyncOpenAI, records native kwargs without
   rewriting them, and adds only an owned actual HTTPX client/transport. One
   process/loop/session initially; use explicit attempt/role/operation/logical
   call context for the direct verification probe too. Publish an immutable
   registry of SDK, HTTP client, transport/pool/backend/resource identities.
   Preserve native `max_retries=0`. Do not invoke engine startup to obtain a
   probe; engine verification catches failures and can continue.
2. **Gate the final request.** Immediately before delegating an HTTPX request,
   inspect method, scheme, host, port, path, ordered query, all effective headers,
   serialized body and wire model. Allow only the exact configured inference
   route and parameter/schema scope. Reject userinfo/fragments, unexpected
   routing headers/proxy mounts, unknown extensions/methods and incompatible
   body overrides. Hash exact request bytes; do not repair them. Bind Host,
   origin, core connection authority and simulated TLS server name. A trusted
   future live connector must also verify actual DNS/peer/TLS identity; D7
   simulation cannot attest that destination.
3. **Reserve before dispatch and bind serialization.** Atomically create an
   exclusive pre-send reservation/event before delegating to the core pool.
   A separate request-start sentinel must verify that reservation and consume
   its single-use capability before serialization/first request-byte write.
   Record connection attempts, starts and writes separately. If a backend emits
   a second request start for one capability, reject before that start; if a
   new HTTP request legitimately occurs it needs a new reservation. This
   sentinel is a proposed extension of the scripted backend, not something D7
   already enforces. Restrict the initial pool to HTTP/1.1, no proxies, no
   alternate mounts and transport retries zero; unsupported protocols STOP.
4. **Treat redirects as new attempts.** Retain the SDK-default redirect setting
   in observation mode to measure source/SDK behavior. In governed mode, the
   final-request gate rejects every redirect-derived dispatch (same-host too)
   before it is sent, using parent-request attribution and a tested propagation
   mechanism. If HTTPX cannot reliably expose/bind that ancestry, explicitly
   set `follow_redirects=False` in the governed adapter and version that
   divergence; do not claim native transport parity. No hidden refund of the
   initial request's reservation. Positive redirect controls use a separate
   offline observation fixture and cannot earn readiness.
5. **Distinguish retry layers.** Native retries re-enter actual create and get
   fresh request reservations. SDK retry-setting drift, pool retry drift or
   unknown resend behavior rejects/STOPs. Connection attempts and failed writes
   do not prove zero endpoint consumption. A send with ambiguous outcome keeps
   its full reservation. Governed mode latches further admission closed after
   ambiguous failure or evidence loss, even if native code catches the error
   and tries again. Observation mode retains native retry behavior only within
   its offline fixture limits. Neither mode changes native loop bodies.
6. **Handle replacement at transport, not old-wrapper lookup.** Retained
   resources and SDK copies sharing the owned transport still hit its gate.
   Register permitted aliases explicitly and reject missing/wrong invocation
   attribution. A replacement using another registered transport must share
   the same session; a new unregistered client has no accepted capability.
   An identity check in an old completions wrapper cannot enforce this rule.
   Runtime mutation to another HTTP client/backend or resource requires a
   registry check at dispatch, plus process containment below all clients.
7. **Reject alternate resources.** Responses, files, batches, embeddings,
   Ollama-native/aiohttp and other provider/auth HTTP paths are excluded before
   construction/configuration and again at the owned dispatch gate. A batch
   control-plane request is not one physical inference attempt. A retained
   SDK handle may bypass native method observation, but never the owned
   transport; it must fail without a valid method invocation context.
8. **Capture and settle without hiding uncertainty.** Raw SDK usage observation
   occurs before returning the response to native parsing. Bind it to request
   and response hashes and capability ID; avoid counting one usage receipt
   for multiple requests. Valid prompt/completion/total consistency is checked;
   reasoning/cache are inclusive subsets, not additions. Missing/invalid
   usage, cancellation, response-write loss, over-bound usage and crash leave
   unresolved reservations and stop future admission. Keep raw and native
   transformed usage separate. No receipt means no inferred zero billing.

Every event carries engineered identity, evidence layer, qualification attempt,
PID, client/transport IDs, native invocation/retry index, SDK invocation ID,
HTTP request ID, request-start/capability ID, role/scope, effective destination,
wire model, policy/contract identities and hashes. Fixtures hold synthetic
content/keys only; public receipts omit credentials. Exclusive pre-send events
must be durable to the stated contract (including fsync if crash durability is
claimed); D5's exclusive writes alone do not prove power-loss durability. A
crashed or colliding attempt is closed, never resumed over prior evidence.

**Enforcement root:** a mutable Python object graph is not a security boundary
against arbitrary code creating another client. Offline, OS denial of all
network including loopback and socket/DNS audit checks contain unowned clients;
they cannot transmit even if they evade observers. Unexpected import, socket,
subprocess/child process, database, model/cache download, telemetry exporter or
aiohttp-session creation fails the qualification. Restrict source/artifact
writes and process resources; bootstrap changes do not grant execution authority.

For any future live contract, all sockets must be denied in the provider process
and an independently owned egress custodian must be the only network-capable
component. It would receive immutable final requests over a controlled channel,
admit/reserve before transmission, own DNS/TLS/routing/retries and return bound
responses. Its minimal initial rule would forbid redirects/resends and unknown
resources. That is a separate transport/infrastructure design and permission,
not this offline adapter and not a currently qualified cross-process accounting
system. Without kernel-enforced exclusive egress and custodian qualification,
unowned clients remain a STOP condition and no physical inference is accepted.

There is no endpoint-enforced inclusive token bound here. Offline fixture totals
are fixture contracts only. A future real endpoint/model/mode must supply an
independently qualified inclusive maximum for input, output, reasoning/cache and
ambiguous/failed attempts before admission can enforce a real token ceiling.
Configured output caps, tokenizer estimates, context-window advertisements or
post-send usage alone cannot establish that bound. Reject, do not synthesize it.

## Threat model and negative controls

The provider's semantic transforms are trusted only as the pinned native method
scope; retrieved/model content never acquires authority to alter policy,
configuration, attribution, destination or source identity. Trusted components
are the reviewed materializer/manifest, admission/evidence store and offline OS
containment. Mutable SDK/native objects, environment defaults, optional helpers,
redirect/status responses and asynchronous context are possible bypass inputs.
An arbitrary hostile interpreter/kernel compromise is outside this design;
object identity checks are not presented as containment against it.

| Threat / counterexample | Required negative control / fail point |
| --- | --- |
| Wrong pin, source tamper/EOL drift, patch outside initializer allowlist, missing helper or mixed installed namespace | Reject before import; verify originals remain unchanged and no partial artifact becomes accepted |
| Lazy export resolves sibling/MemoryEngine/poller, JSON formatter reaches MemoryEngine, optional Google/config path expands closure | Import/method audit rejects before executing the unapproved body; STOP for closure review. Use controlled native logging settings, not a fake formatter |
| Extra body replaces model; headers/query/base path reroute | Reject final request before delegation; preserve native request for private synthetic comparison, never strip overrides |
| Same/cross-host 307/308, SDK/pool positive retry setting, second serialized start under one admission | Positive offline observation controls expose multiplicity; governed controls reject redirected dispatch/drift/second start before any unreserved start |
| Retained/copied/replaced resource/client, shared-client close, unowned SDK or aiohttp session | Same owned transport enforces context/capability; unowned egress is OS-denied; close forbids further dispatch; no old-wrapper-only pass |
| Responses/files/batch/embedding/native Ollama, unexpected worker/child process | Pre-construction exclusion plus dispatch/OS denial; zero accepted request starts outside the route |
| Missing/cross-task attribution, cross-thread/loop/PID session reuse, replayed capability | Reject before reservation/serialization; cancellation/context reset cannot transfer attribution to another call |
| Missing/malformed usage, parse retry after valid usage, timeout/cancel after start, evidence collision/corruption/disk failure/crash | Preserve raw/previous evidence and unresolved capacity; fresh reservation for a new allowed request; latched close survives native catch/retry |
| Native cap raised above admitted policy or no independently enforced inclusive bound | Reject final shaped request/configuration; no silent lowering, output-to-total conversion or live readiness promotion |

## Concrete implementation stages for later authorization

No file named in this section is created or changed by Phase 08D-9. These are
proposed paths, to be frozen in the next authorization and manifest.

| Stage | Exact expected files / boundary | Evidence and release gate |
| --- | --- | --- |
| 0. Independent design review | This report and ledgers only | Accept/change/reject ADR, three-file allowlist, claim labels, transport threat model and parity gates. No implementation authority follows from publication |
| 1. Static derivative proposal | New `scripts/materialize_phase08d9_provider_boundary.py`, `scripts/verify_phase08d9_provider_boundary.py`, `manifests/phase-08d9-provider-boundary-source.json`; exclusive ignored `.local/phase08d9/provider-boundary/0.1.0/` source tree. Only the three upstream initializers listed above differ | Byte/diff/export-map verification, complete proposed method-time/import graph and dependency metadata/artifact plan; no import, dependency acquisition/install or method execution. Stop and review actual patch/manifest |
| 2. Reviewed artifact preparation | New `manifests/phase-08d9-provider-boundary-dependencies.json`; if authorized, new `scripts/prepare_phase08d9_provider_boundary.py` and fresh `.local/phase08d9/runtime/.venv` | Exact binary wheel allowlist after actual closure; rehash D7 reuse, install only into fresh repository venv, no inherited sites/.pth/editable build. Version/RECORD/metadata checks under deny-network. Acquisition and installation require explicit permission and a reviewed artifact plan |
| 3. Offline import qualification | New `scripts/qualify_phase08d9_provider_boundary.py`, `tests/unit/test_phase08d9_provider_boundary.py`; new `src/memlife/provider_boundary/__init__.py` and `bootstrap.py` for engineered identity/entry gate | Normal Python imports of real packages with network denied before import; trace all imports and permitted effects, prove no engine/poller/embedding/service construction; constructor/methods still excluded. Immutable new receipt; independent review before methods |
| 4. Offline method/transport qualification | New `src/memlife/provider_boundary/transport.py` and `receipts.py`; new `tests/unit/test_phase08d9_provider_transport.py`; extend the new qualification script/corpus | Scoped actual-SDK factory/observer, transport reservation and scripted request-start sentinel; real native probe/calls/tools/retries/cleanup with all parity and negative controls. No edits to provider bodies, SDK sources or D7 harness/evidence; no real sockets/services/models |
| 5. Reference comparison, separately scoped | New reference receipt/corpus results through the same new qualification script; unchanged ordinary C source tree/environment | Compatible pinned C artifacts/platform need separate review. Compare exact same fixture corpus. Full-distribution metadata cannot be trimmed; crypto gap cannot be bypassed. If unavailable, retain `B_C_PARITY_NOT_EXECUTED` and limited engineered method-contract label |
| 6. Native engine/D4 proposal, no automatic progression | Separate future design/authorization; no change now to `src/memlife/runner/phase08d5.py` or `require_hindsight_runtime_ready()` | Requires complete role/member/worker/task/transport inventory, exclusive egress and endpoint bounds plus D3/D5/scientific review. Provider-only receipt cannot authorize startup or pilot |

Import restrictions must also inspect the MemLife adapter package's own parents
before using that proposed entrypoint. If they import prohibited components,
STOP for review rather than add stubs or weaken the guard. All Python analysis,
materialization and future verification use repository-owned `.venv`
interpreters. New receipts are engineering qualifications, with separate
attempt IDs; none is an empirical cell or amendment to a scientific attempt.

## Readiness gates and STOP rules

| Gate | Required evidence | Current state / claim allowed |
| --- | --- | --- |
| G0 Design approval | Independent review of this ADR and exact next scope | PENDING; documentation design only |
| G1 Reproducible engineered source | Approved three-file patch, unchanged provider/helpers, complete manifest, license and source/dependency closure | NOT IMPLEMENTED; static projected closure only |
| G2 Artifact/import safety | Exact isolated artifacts and observed normal imports, allowed effects only | NOT EXECUTED; D7 SDK-only qualification preserved |
| G3 Engineered provider method contract | Full applicable parity/negative corpus, raw usage, cleanup, actual SDK/core simulations, zero unmatched starts | NOT EXECUTED; no native-provider PASS |
| G4 Ordinary-import differential parity | Actual unchanged C baseline, same inputs/transport, zero unexplained differences | NOT EXECUTED; method source identity alone cannot grant it |
| D1 / D2 | Existing adapter capture / candidate persistence evidence | Preserved unchanged, no new empirical evidence |
| D3 | Native operations, startup/health probes, background workers, child tasks/replay and complete global quiescence | PARTIAL; provider cleanup is not MemoryEngine lifecycle completion |
| D4 | Every role/member/process send owned before startup, final destination and physical-attempt enforcement, qualified endpoint inclusive bounds | BLOCKED; offline provider design/simulations grant none of these full-runtime claims |
| D5 | Attempt/bank/source/config identity, durable evidence and resource/eligibility gates across the accepted execution topology | PARTIAL; direct-provider attribution is not task replay/cross-process coverage |
| Four-condition pilot / RQ3 | D3/D4/D5 plus independent scientific authorization | BLOCKED; no new calls, contexts or denominators |

STOP and seek independent review on any non-initializer source change, provider
or helper rewrite, unexpected dynamic import or initialization, enlarged
dependency/source/platform scope, incompatible/missing artifact, optional auth
activation, source/manifest mismatch, semantic mismatch, undocumented harness
normalization, unowned client/transport/process, uncertain physical multiplicity,
network guard failure, unbound receipt, evidence loss or absent endpoint bound.
Preserve failing receipts; do not rerun over them or promote a partial result.
Changing logging, redirect policy, factory injection, retry/exception handling
or environment behavior requires explicit claim/version updates even if native
method bytes remain unchanged.

## Exact next authorization and closeout

After independent approval of this design, the narrow next request should say:

> Authorize Stage 1 only: reproducibly materialize a versioned engineered source
> derivative from existing verified Hindsight 0.10.1 commit
> f8950b0c07d9e34c76493dba802bb309f0ce60fd, changing only
> hindsight-api-slim/hindsight_api/engine/__init__.py,
> hindsight-api-slim/hindsight_api/engine/providers/__init__.py and
> hindsight-api-slim/hindsight_api/worker/__init__.py to the reviewed lazy-export
> contract. Add the specified materializer/verifier and source manifest; perform
> static byte/export/import/dependency analysis only with a repository .venv.
> Preserve originals and all native provider/helper bytes. Produce the actual
> patch, source identities and exact artifact plan, commit/push the review branch
> and stop for independent review. No acquisition, install/build, native or SDK
> import/execution, model/provider/embedding/database/service/worker/RQ3,
> SSH, Jetstream or empirical action is authorized.

Stages 2–5 need separately explicit artifact/install/import/method/reference
permissions after their prerequisites are reviewed. Stage 6/live egress and any
endpoint qualification are independent authorizations. No stage is authorized
by this document itself.

Documentation verification passed: 82 local links across the new report and
updated ledgers resolve; the stated source/receipt hashes match the recorded
identities; `git diff --check` passes; code, manifests, freezes and evidence have
no diff from the base. Read-only Git-blob CRLF materialization reproduces the
canonical Freeze v1 hash below. These are document/byte checks using standard
tools and a repository `.venv` for JSON/link checks; no SDK/native imports or
runtime qualification tests were run.

Phase 08D-9 changed documentation only. D1/D2 evidence, all D5–D8 source/SDK
receipts and code, the unconditional runtime gate, Freeze v1 and the non-final
Freeze-v2 draft, Candidate10's frozen NO_GO, OpenViking S0 r2 ERROR, immutable
attempts and scientific denominators remain unchanged. Canonical Freeze v1
SHA-256 remains `0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b`.
Provider/model/embedding/downstream/RQ3/native/SDK executions for this phase are
zero. Jetstream remains SHELVED. **Stop for independent review after documentation
publication. Retrieved != Authoritative.**
