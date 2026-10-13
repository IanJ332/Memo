# Phase 08D-6 — Native Runtime Boundary Qualification

**Verdict: D4 BLOCKED. Installed-runtime qualification could not be completed
offline. D5's owned fake completions boundary does not establish native coverage.**

CONVERSATION: Phase 08D-6 native runtime boundary qualification. MODEL: GPT-6
Codex runtime; no independent model-variant receipt. EXECUTION TARGET: assigned
local worktree `/Users/ian/.codex/worktrees/e1a4/Memo`. JETSTREAM ACTION: none;
remains SHELVED without querying infrastructure. Date: 2026-10-12,
America/Chicago.

The clean assigned detached HEAD was exactly the requested base
`58ab52dcd8e628400533173eac08ed5b1ea42faa` before creating review branch
`phase-08d6-runtime-qualification`. No native provider initialization, SDK request,
service, embedding, hosted-model, downstream/RQ3, SSH or Jetstream action occurred.
No download, package installation, upstream modification or proxy was introduced.
Git publication is confined to the review branch; main is not merged.

## Evidence class and exact runtime blocker

The [offline qualification receipt](../../manifests/phase-08d6-offline-qualification.json)
records **19 verified cached first-party files** at Hindsight 0.10.1 source commit
`f8950b0c07d9e34c76493dba802bb309f0ce60fd`. The 16 D5 files match their previous
SHA-256, Git blob SHA-1 and byte counts. Three additional cached files
(`engine/llm_interface.py`, `engine/retain/orchestrator.py`,
`engine/task_backend.py`) match the previously cached non-truncated pinned GitHub
tree, whose SHA-256 matches the D5 manifest. All 19 parse as Python source;
none was imported or executed. No fresh upstream request was made.

The assigned worktree initially lacked `.venv`. A repository-owned Python 3.12.8
venv was created with `--without-pip` using the existing D5 repository venv.
Its ignored `.pth` reuses the already installed D4 core test dependencies.
`PYTHONDONTWRITEBYTECODE=1` prevents writes to those reused packages. Dependency
inspection used top-level `find_spec` and distribution metadata, not provider
imports:

| Required local component | Import available | Distribution version |
| --- | --- | --- |
| `hindsight_api` / `hindsight-api-slim` | No | Absent |
| `openai` | No | Absent |
| `httpx` | No | Absent |
| `httpcore` | No | Absent |
| `aiohttp` | No | Absent |

This is an inventory of the available repository test environment, not a claim
about every environment on the machine or the historical remote runtime. The
Hindsight requirement pins `hindsight-api-slim[embedded-db,local-onnx]==0.10.1`;
it does not supply an installed wheel, resolved SDK/transport versions or their
effective configuration here. The cached files are not an installable runtime.
With downloads/installation prohibited, **zero actual SDK/HTTP transport probes
could run**. Effective retry multiplicity, redirects, proxy/env routing, SDK
resource identity and installed Hindsight behavior remain **UNVERIFIED**.
No synthetic SDK or stubbed Hindsight import was used to fill that gap.

The [audit harness](../../scripts/qualify_phase08d6_offline.py) is deliberately
read-only with respect to upstream source and runtime. It checks cached bytes,
enumerates syntactic call sites and provider factory labels, records dependency
availability, and exclusively creates an engineering receipt. It never grants
readiness, including when dependencies are available. A successful script exit
means the static audit completed; the receipt still says `BLOCKED`.

## Native construction, ownership and worker coverage

Paths below are relative to pinned `hindsight-api-slim/hindsight_api/`; line
numbers refer to the verified source, not the MemLife adapter. The
[pinned engine source](https://github.com/vectorize-io/hindsight/blob/f8950b0c07d9e34c76493dba802bb309f0ce60fd/hindsight-api-slim/hindsight_api/engine/memory_engine.py)
and receipt bind these observations. “Candidate seam” means a statically
identified interception opportunity, never runtime qualification.

| Construction / execution path | Pinned source evidence | Ownership / D5 coverage |
| --- | --- | --- |
| Single-process API CLI | `main.py:380–420` constructs `MemoryEngine`, then `create_app(initialize_memory=True)` | Independent engine; no native invocation of the MemLife readiness gate or injection hook. UNVERIFIED. |
| Reload / multiple API workers | `main.py:380–455` selects `hindsight_api.server:app`; `server.py:70` constructs an engine at module import | Each imported app can own a distinct engine. D5's fork rejection does not cover spawned/reloaded independent engines. UNSUPPORTED topology; must reject before import/construction. |
| Standalone worker CLI | `worker/main.py:284–291` constructs another engine with `WorkerTaskBackend`, then initializes it | Separate clients/accounting/address space. UNSUPPORTED; the native CLI has no D5 gate. |
| Default, retain, reflect and consolidation | `memory_engine.py:2365/2413/2509/2628`, `llm_wrapper.py:1082`, provider constructor `openai_compatible_llm.py:893–915` | Separate `LLMConfig` construction even when settings match; each may construct `AsyncOpenAI`. One wrapped default client is insufficient. UNVERIFIED. |
| Vision | `memory_engine.py:2447–2487` constructs its own config when configured; otherwise aliases retain | Vision override is deliberately outside retain multi-LLM fallback. It must be inventoried separately. UNVERIFIED. |
| Mental-model refresh | `memory_engine.py:2536–2609` selects reflect dynamically when unset or constructs its own override/chain | A captured reflect alias can become stale after config replacement. UNVERIFIED. |
| Multi-LLM extra members | `_member_to_llm:651–700`, `_build_llm:714–763`; `multi_llm.py:164–186/254–277` | Each member has its own provider/retry settings. Failover, weighted round-robin, metadata selection and first batch-capable member can choose other clients. Single-wrapper coverage is UNSUPPORTED. |
| Per-bank operation wrappers | `llm_wrapper.py:1628–1669`; engine `6715/12762/15352/17559` | `with_config()` reuses a provider, rather than creating an SDK client. This helps only if that provider and every chain member are already owned. D5 attribution is not propagated by these native wrappers. UNVERIFIED. |
| Startup probes | Engine `5070–5105`; provider `976–995` calls its own `call(max_retries=2)` | Direct implementation call reaches the candidate seam for applicable chat paths. Dedup is by provider/model, not client identity; vision is absent from this probe list. Probe success cannot certify ownership. UNVERIFIED. |
| Health probes | Engine `_probe_llm:16153–16171`, `check_bank_llm:16173` | Direct verification can send again; failure becomes health status. Health coverage excludes mental-model refresh override. UNVERIFIED. |
| Foreground extraction / tools / curation | Fact extraction `2085`; engine `15352/17616/17749`; provider `1257/1337/1666` | Selects retain/vision/reflect/refresh configurations and retries, not just the default client. Candidate seam only for chat-completions implementations. UNVERIFIED. |
| API background poller | `api/http.py:4887/4914–4928` initializes the engine, then creates `WorkerPoller(executor=memory.execute_task)` | Same engine in this API process, but worker coverage and attribution are not demonstrated by fake tests. UNVERIFIED. |
| Task execution, replay and child tasks | Engine `3933–3962/5400`; `worker/poller.py:1055–1086/1159–1260`; `engine/task_backend.py:189–255` persists broker tasks | Database task payloads cross time/process boundaries; Python ContextVars/accounting locks do not. Async tasks and replay need fresh, explicit attribution. D3 global quiescence remains UNKNOWN. |
| Consolidation and dedup | Consolidator `2316–2319/3239–3245`, dedup `352` | Dedup uses the consolidation config; outer retries/adaptive subdivision can add calls. No fixed calls-per-operation bound. UNVERIFIED. |
| Legacy client reference / replacement | Engine `2393` stores `_llm_client`; wrapper `_client:1112–1126` exposes underlying client | A separate handle or replaced provider/client can avoid a resource wrapper entirely. Native mutation/recreation completeness remains UNVERIFIED. |

Engine initialization catches LLM verification exceptions and logs a warning
(`memory_engine.py:5090–5100`); multi-member verification also soft-fails secondary
members (`multi_llm.py:201–220`). A governance exception therefore cannot serve as
the startup gate. Initialization concurrently schedules database and model
initialization before any post-initialize inventory would run (`5109–5138`).
Admission readiness must be established **before `MemoryEngine` construction and
before importing entrypoints that construct it**, not by relying on probe failure.

## Send-path support matrix

“SUPPORTED” below is restricted to D5's existing deterministic fake contract.
There are **no supported native runtime configurations** in D6. “UNSUPPORTED”
means D5 does not govern that path/configuration; “UNVERIFIED” means installed
behavior or complete coverage was not proven. All unsupported/unverified native
paths must remain rejected by the unconditional runtime gate.

| Send path / factory selection | Static route | Classification |
| --- | --- | --- |
| Owned deterministic `provider=openai` fake, admitted JSON subset | Wrapped `chat.completions.create` | SUPPORTED: offline wrapper only; not a native configuration. |
| Native OpenAI-compatible chat, structured/unstructured/tools | `openai_compatible_llm.py:1257/1337/1666` | UNVERIFIED runtime candidate seam. Real contracts rejected by D5. |
| Native Ollama structured calls or configured `ollama_num_ctx` | `call:1139` selects `_call_ollama_native`; `1880` uses loop-local aiohttp `session.post(.../api/chat)` | UNSUPPORTED bypass of chat resource. Includes applicable startup probes. `ollama-cloud` takes the factory's compatible branch; its runtime remains unverified. |
| OpenAI/Groq batch retain | `fact_extraction.py:2804/2888` selects implementation; provider `2121/2129` invokes `files.create` / `batches.create` | UNSUPPORTED. Upload/submission bypasses create; one submission represents many future model calls. A transport request ceiling alone would not bound remote batch executions. |
| Batch polling / results | Provider `2158/2196/2206` invokes `batches.retrieve` / `files.content` | UNSUPPORTED HTTP paths. Polling/results are control-plane requests, not evidence of one model inference each. |
| `openai-responses` | Factory `llm_wrapper.py:765–780` selects `OpenAIResponsesLLM`, explicitly a `/v1/responses` implementation | UNSUPPORTED by chat wrapper; implementation file is absent from verified local cache, so its detailed SDK/HTTP/retry behavior is UNVERIFIED. |
| `groq`, `ollama`, `ollama-cloud`, `lmstudio`, `minimax`, `deepseek`, `volcano`, `openrouter`, `requesty`, `zai`, `opencode-go`, `atlas`, `meta` | Factory `782–814` selects `OpenAICompatibleLLM` | UNSUPPORTED by D5 provider allowlist (`openai` only), even for chat routes sharing the seam. Native behavior UNVERIFIED; Ollama/batch exceptions above apply. |
| `fireworks`, `nous` | Separate factory classes; comments describe compatible online inference and additional batch/auth behavior (`714–749`) | UNSUPPORTED. Inheritance, auth refresh, native batch and any additional sends UNVERIFIED: implementation bytes unavailable locally. |
| `gemini`, `vertexai`, `anthropic` | Factory selects Gemini/Anthropic implementations (`613–646`) | UNSUPPORTED alternative SDK paths. Detailed sends, caching/control-plane calls and retries UNVERIFIED. |
| `litellm`, `litellmrouter`, `bedrock` | Factory selects LiteLLM/Router (`648–691`) | UNSUPPORTED routing/SDK paths; router members, internal retries and downstream transports UNVERIFIED. |
| `openai-codex`, `cursor`, `claude-code`, `github-copilot`, `xai-oauth` | Separate factory classes (`560–601/751–763`) | UNSUPPORTED alternative client/auth/process paths. Detailed sends and subprocess behavior UNVERIFIED. |
| `llamacpp`, `mock`, `none` | Separate implementations (`603–611/693–712`) | UNSUPPORTED by this D4 boundary. Local/native behavior not executed; no hosted call exemption establishes global runtime readiness. |
| Unknown provider name | Factory `816–817` raises `ValueError` | Statically rejected by native factory; no runtime proof. |
| ONNX / other embeddings, query analyzer, cross-encoder, extensions | Separate initialization/execution, outside chat completions | UNSUPPORTED by hosted-send accounting. ONNX source can download model/tokenizer (`embeddings.py:515–547`); no initialization/inference executed. Other extension/embedding transports are not exhaustively audited and remain UNVERIFIED. |

The receipt enumerates all 31 explicit factory labels and direct client call
sites in the cached OpenAI-compatible implementation. `self._client.close` is
also enumerated syntactically; it is cleanup, not an inference call. Factory
enumeration is not an exhaustive dynamic call-graph or transport proof. Uncached
alternate provider implementations, database backends, extensions and arbitrary
replacement clients prevent an all-native-send completeness claim.

## SDK transport, retries, routing and bypass evidence

The [pinned compatible provider](https://github.com/vectorize-io/hindsight/blob/f8950b0c07d9e34c76493dba802bb309f0ce60fd/hindsight-api-slim/hindsight_api/engine/providers/openai_compatible_llm.py)
constructs `AsyncOpenAI(max_retries=0)` (`893–915`). It supplies default headers,
extracts URL query parameters into `default_query`, normalizes some local base
URLs, and delegates HTTP client construction to the SDK. It does not explicitly
supply a transport or redirect policy. Native text/tool retries re-enter create
(`1249–1257/1337/1662–1666`); the verification call requests two retries. Native
extraction has an outer retry loop (`fact_extraction.py:2056–2085`), output-limit
splitting (`2451`), and consolidation has outer attempts/adaptive subdivision
(`consolidator.py:3204–3245`). Worker replay and member failover add further layers.
These are **verified source facts, not measured SDK send counts**.

| Question | Available evidence | Qualification |
| --- | --- | --- |
| Does `max_retries=0` yield one HTTP attempt per create? | Source argument only; SDK/httpcore absent | UNVERIFIED. No measured status/connection/timeout retry counts. |
| Can a redirect multiply/reroute a governed send? | No explicit native redirect policy; installed httpx absent | UNVERIFIED, including cross-host redirect handling and credential forwarding. Do not infer SDK defaults. |
| Are path, query, headers and model admission bound to the final wire request? | Native `default_query/default_headers`, `extra_body:1184–1195`, bank/cache/session helpers `1236–1245/1656` | UNVERIFIED. D5 checks base URL, model and create kwargs; it does not inspect effective SDK defaults, env proxies or the final wire destination. |
| Can native parameters be accepted without modification? | Provider can raise a reasoning output cap to 16000 (`1166–1172`), omit consolidation cap, or include extra body | D5 rejects absent/over-bound caps and extras. Stripping extras, lowering a native cap or treating output cap as total would change semantics or invent a bound. No parity claim. |
| Can client replacement bypass identity checks? | D5 checks identity only inside the invoked old wrapper | Deterministic ownership counterexample verified; actual SDK replacement mechanics UNVERIFIED. |
| Can other members continue after an admission error? | Generic `Exception` triggers native `_should_failover` (`multi_llm.py:46–57/164–186`) | Static bypass risk. Shared governed fake session closes other owned members; unowned members remain outside it. Native failover not executed. |

The [18 new tests](../../tests/unit/test_phase08d6_runtime_qualification.py) include
six ownership counterexamples: an exhausted one-call session does not prevent a
direct retained resource, replacement completion resource, replacement client,
Responses resource, batch resource or unowned member from executing an in-memory
stub outside the wrapper. The old-wrapper replacement test in D5 remains valid:
it rejects when the **old wrapper itself is invoked**. It does not guard ordinary
lookup of the new object. No upstream exploit or actual SDK behavior is claimed.

A synthetic below-create resource also performs two stub actions for one admitted
invocation and returns only one usage receipt. This establishes the wrapper's
accounting unit, not the retry/redirect behavior of any SDK. Actual transport
interception tests for success, 429/5xx, connection errors, timeouts, same-/cross-
host redirects, effective query/header/proxy routing, replaced/copy clients and
alternate resources remain **NOT EXECUTED** because their dependencies are absent.

## Pre-send enforcement and ceilings

Complete admission before native initialization is **not established**. The
repository's `require_hindsight_runtime_ready()` is unchanged and rejects every
topology. New tests verify the specified call order cannot enter even an offline
engine factory after that gate. They do not assert native entrypoints call it;
they do not. No MemLife launcher or native startup integration was enabled.
Therefore uncovered clients/workers/sends fail closed at the proposed repository
launch boundary by refusing launch altogether. Direct upstream startup is outside
this boundary and must not be described as governed.

D5's call ceiling counts admitted create invocations. It becomes a ceiling on
actual internal model attempts only after proving complete ownership, no hidden
transport retries/redirects, and one accounted attempt per actual inference.
Batch remote work invalidates that one-to-one assumption. A single in-memory
session cannot bound independent workers or recover reservations across restart.
Native metadata and trace ContextVars do not establish D5 attempt/logical-call
attribution on startup, tasks or database replay.

D5 reserves an inclusive fake total maximum and settles raw SDK usage before
Hindsight's missing-usage/visible-token transformations. The regression tests
retain unresolved capacity for failures and missing usage. **No independently
verified native endpoint inclusive total-token maximum exists.** Output caps,
estimated input tokens and an advertised context window remain insufficient.
Reasoning, cache, failed/aborted calls, batch usage and billing categories are not
endpoint-qualified. Returning a response with valid usage does not retroactively
enforce a pre-send ceiling on an already over-bound call. D5 appropriately rejects
real contracts rather than manufacturing bounds; no monetary ceiling is claimed.

## Required minimum changes for complete D4 enforcement

These are prerequisites for separately authorized work, not implemented native
changes or authorization to start a provider:

1. Supply an already staged, immutable installed Hindsight 0.10.1 runtime with
   resolved SDK/HTTP dependency identities. Execute its construction and native
   methods against deterministic offline transport interception, with outbound
   networking denied. Static cached bytes cannot substitute for this evidence.
2. Add a launch gate before engine construction/import side effects, evaluating
   the full effective role/member/provider/topology/configuration set. For the
   minimum restricted configuration, reject native Ollama, Responses, alternate
   providers, batch retain, reload, multiple processes and standalone workers.
   Audit embedding/model initialization, optional extensions and caches before
   admission; do not let probe warnings downgrade a rejection.
3. Establish owned client construction/injection for every accepted role/member,
   before probes or workers run. Inventory actual object identities, forbid
   unowned replacements/retained handles, and ensure all accepted routes share
   the same attempt session. Alternatively keep multi-LLM unsupported. Native
   failover, outer retries and worker replay must never escape a latched denial.
4. Qualify the final outbound boundary below create, including effective URL,
   query, headers and transport. Either prove one attempt per admission for the
   pinned transport or account/admit every physical inference attempt. Reject
   rerouting/redirects and unknown client/transport overrides unless separately
   qualified. This phase chooses no new proxy or upstream patch architecture.
5. Propagate explicit attempt/role/task/condition/logical-call identity through
   probes, foreground paths and accepted background tasks. Unsupported process
   creation must reject before construction; any later cross-process support
   needs shared atomic accounting and crash/restart evidence, beyond D5's PID
   guard.
6. Obtain defensible endpoint-enforced inclusive token bounds and raw usage
   semantics for the exact endpoint/model/request modes. Admit final native
   parameters without rewriting them. Reject absent caps, unknown bounds and
   overrides; retain unresolved reservations and stop on ambiguous outcomes.
   Requiring new caps changes an accepted configuration and must be reviewed,
   not silently imposed on frozen provider behavior.

## Verification and updated readiness

```text
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/qualify_phase08d6_offline.py \
  --source-cache /private/tmp/hindsight_audit \
  --pinned-tree /private/tmp/phase08d5-pinned-tree.json \
  --output manifests/phase-08d6-offline-qualification.json

PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest \
  tests/unit/test_phase08d6_runtime_qualification.py \
  tests/unit/test_phase08d5_governed_sends.py \
  tests/unit/test_phase08d3_capture_accounting.py \
  tests/unit/test_phase08d4_evidence_persistence.py \
  tests/unit/test_hindsight_adapter.py \
  tests/unit/test_hindsight_lifecycle_trace.py \
  tests/contract/test_hindsight_provider.py \
  tests/unit/test_phase06_freeze.py tests/unit/test_rq4_policy.py -q
```

**161 passed in 3.34s**: 18 new qualification tests and 143 prior regressions.
No SDK tests or opt-in service tests ran; no full-suite pass is claimed. The new
tests also reject source-byte/EOL/identity drift and inspect dependency metadata
without importing the runtime. The audit receipt's source cache is local and
uncommitted; rerunning requires those exact cached files and a new exclusive
output path. Test execution itself does not require the cache.

`scripts/validate_experiment_freeze.py` passes with canonical SHA-256
`0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b`.
`git diff --check` and changed-source parsing pass. D1/D2 implementation/evidence,
the D5 runtime guard and instrumentation, frozen manifests/attempts and research
denominators are unchanged.

| Gate | Updated verdict |
| --- | --- |
| D1 adapter HTTP capture | IMPLEMENTED / existing regressions pass; no new empirical capture |
| D2 candidate persistence | IMPLEMENTED / existing regressions pass; preserved evidence |
| D3 lifecycle completion | PARTIAL; global worker coverage/quiescence UNKNOWN |
| D4 native internal sends | BLOCKED; static construction/bypass audit extended, installed transport/native coverage UNVERIFIED |
| D5 attempt/evidence gates | PARTIAL; fake boundaries retained, native attribution/process/resource prerequisites unresolved |
| Four-condition pilot | BLOCKED; no empirical eligibility or new denominator entry |

Freeze v1, the non-final Freeze-v2 draft, Candidate10's frozen NO_GO and the
OpenViking S0 r2 ERROR remain unchanged. Provider/hosted-model/embedding/downstream/
RQ3 calls are all zero for this phase. Jetstream remains SHELVED. **Stop for
independent review after publishing the review branch.** No further runtime or
live execution is authorized by this report. Retrieved != Authoritative.
