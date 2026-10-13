# Phase 08D-5 — Governed Internal-Send Instrumentation

**Result: OFFLINE ENFORCEMENT TESTED; REAL-PROVIDER D4 / PILOT BLOCKED.**

CONVERSATION: Phase 08D-5 governed internal sends. MODEL: GPT-6 Codex runtime;
no independent model-variant receipt. EXECUTION TARGET: assigned local macOS
worktree `/Users/ian/.codex/worktrees/d946/Memo`. JETSTREAM ACTION: none;
remains SHELVED without querying live infrastructure.

Base verified: `de011d8bde32ffda76512c87dee550f0baf688d5`, clean detached
assigned HEAD before edits. Review branch: `phase-08d5-governed-sends` only.
Date: 2026-10-12, America/Chicago. No provider, hosted experimental model,
embedding, downstream or RQ3 execution occurred. No Jetstream or SSH action,
upstream installation/fork, global monkeypatch, or new network proxy occurred.
Public GitHub source reads and HTTPS Git publication are engineering actions.
Main was not merged or edited.

## Readiness matrix

| Gate | Current readiness | Evidence and remaining limit |
| --- | --- | --- |
| D1 exact adapter HTTP capture | IMPLEMENTED, OFFLINE TESTED | Existing exclusive request/response artifacts and allowlisted response headers; focused regressions pass. This is the adapter HTTP boundary, not internal LLM-send capture. |
| D2 candidate persistence | IMPLEMENTED, OFFLINE TESTED | Phase 08D-4 response-linked candidate persistence/integrity regressions pass; no new empirical candidate bytes collected. |
| D3 lifecycle completion | PARTIAL / GLOBAL COVERAGE UNKNOWN | Existing operation receipts/pagination retained. No proof of complete worker quiescence; the new send gate does not prove task completion. |
| D4 internal hosted-LLM sends | OWNED FAKE BOUNDARY TESTED / REAL RUNTIME BLOCKED | Reservations, separate call/token/concurrency ceilings, attribution, receipts, failure stops and exclusive accounting events work for deterministic owned fake clients. No installed-runtime transport or complete engine/client/worker qualification. Real-provider startup gate rejects every configuration. |
| D5 attempt/evidence gates | PARTIAL | Attempt identity, private exclusive accounting files, immutable policy/contract references, request hashes, and integrity checks implemented. Full runner ownership, resource limits, source/bank configuration freeze and empirical eligibility remain unqualified. |
| Four-condition pilot | BLOCKED | D3/D4/D5 and independent scientific review remain gates. No empirical execution or denominator entry is authorized. |

## Pinned-source verification and integration decision

The [source audit manifest](../../manifests/phase-08d5-upstream-source-audit.json)
records 16 inspected first-party files, their Git blob SHA-1, SHA-256, and byte
counts at Hindsight 0.10.1 commit
`f8950b0c07d9e34c76493dba802bb309f0ce60fd`. Cached source bytes were independently
matched to the freshly read, non-truncated GitHub recursive tree for that commit.
Files were parsed/read as source only, never imported or installed. This verifies
these source bytes, not an installed wheel or all runtime configurations.

| Path | Verified static behavior | Coverage implication |
| --- | --- | --- |
| `engine/providers/openai_compatible_llm.py:893–915` | Constructs `AsyncOpenAI` with `max_retries=0` at line 896. | No SDK-retry-disable change is introduced. This source setting is insufficient proof of effective SDK/HTTP transport retry or redirect behavior in an installed environment. |
| Same file: `verify_connection:976`, `call:1249`, sends `1257/1337`, `call_with_tools:1662`, send `1666` | Startup/health probes call the implementation directly. Structured/unstructured/tool sends re-enter `chat.completions.create` inside native retry loops. | An explicitly owned completions instance is the smallest candidate seam for this restricted configuration. Wrapping `LLMProvider.call` misses probe/retry granularity. |
| Same file: `call:1139–1140`, `_call_ollama_native:1796`, `session.post:1880` | Structured Ollama and configured native context-window calls bypass the SDK resource, including applicable startup probes. | The Phase 08D-4 statement that every text send converges at `create` is too broad. Native Ollama is unsupported by this wrapper. |
| `engine/llm_wrapper.py:447/1082/765/785` | Factory has other implementations, including OpenAI Responses. | A chat-completions seam cannot cover arbitrary provider selection. |
| `engine/memory_engine.py:2365/2413/2447/2509/2566/2628`, `_build_llm:763` | Default, retain, vision, reflect, mental-model refresh and consolidation can own separate clients; multi-LLM strategies add members. | Wrapping one client does not wrap the engine. All members would require ownership verification before initialization. |
| `engine/llm_wrapper.py:1628–1669` | `with_config()` wraps and reuses the underlying provider/client. | Per-bank configuration wrappers alone do not create new clients. This does not eliminate distinct role/member clients or alternate implementations. |
| `engine/multi_llm.py:46/164–186` | Generic `Exception` failures can trigger member failover. | Admission rejection is terminal at each governed boundary. A shared session blocks another owned member; an unwrapped member could bypass it. Native failover is not qualified. |
| `engine/memory_engine.py:5076–5091/16201`; extraction `2085`; consolidation `352/3245`; worker poller | Probe, foreground, consolidation, dedup and worker tasks select those configurations. Consolidation adds an output cap only if configured (`3239–3240`). | Each actual attempt needs its own admission. Missing caps are rejected rather than synthesized; no fixed calls-per-operation assumption is used. |
| `main.py:380–420/453–455`, `server.py:70`, `worker/main.py:284–291` | API reload/multiple workers and standalone worker CLI construct independent engines. | An in-process hook is not inherited complete governance. No native CLI startup checks were patched or qualified. |
| `engine/embeddings.py:502/515–532/547/568` | ONNX execution is distinct; initialization may download models/tokenizers. | No embedding import, initialization, inference, download or counting is performed by this module. Local embedding qualification remains separate. |

Smallest implemented mechanism: optional, explicit replacement of
`provider._client.chat.completions` **on one owned fake instance**, with a wrapper
that calls the original resource. No class/factory/global patch is installed.
No provider runner or native CLI was changed. The public runtime guard
`require_hindsight_runtime_ready()` rejects before any future engine construction,
even for a single process. There is no accepted real-provider launch path in this
phase. Merely calling `instrument_owned_provider()` on native objects is not a
qualified launch and is outside this phase's tested contract.

## Implemented admission and evidence

[Implementation](../../src/memlife/runner/phase08d5.py) reuses Phase 08D-3
`SendAccounting`, `AttemptArtifactStore`, and `verify_inventory`.

- An explicit endpoint/model pair allowlist, finite positive integer call/token/
  concurrency ceilings, and an immutable policy are required at construction.
  Only `.test` endpoints and `DETERMINISTIC_FAKE_TOTAL` contracts are accepted.
  Real-endpoint attestations, prompt estimates and unknown bounds are rejected.
  Contract artifacts must exist, match their hashes and bind the same endpoint,
  model, basis and total-token maximum. This is fake-specification evidence,
  not proof of an actual endpoint's limits.
- Each `create()` invocation reserves the **whole independently specified fake
  total maximum**, including input and output consumption. The completion cap
  is required but is never added to a prompt estimate to manufacture a bound.
  Call slots are permanently consumed before dispatch. Admission tests committed
  tokens plus outstanding full reservations against the token ceiling.
- A session lock serializes validation, accounting reservation and exclusive
  pre-send event creation across threads/event loops. The underlying call starts
  only after the reservation event is written. All owned clients must share the
  same session. Concurrent tasks carry isolated `ContextVar` attribution. The
  caller must supply attempt, role, operation and logical-call identity; task and
  condition IDs are retained when present, never guessed from native outputs.
- Startup checks reject multiple API processes, reload, nonzero separate-worker
  count and standalone-worker mode. PID ownership is checked before acquiring a
  possibly inherited mutex and before sends/settlement. An actual fork test
  verifies rejection with the parent mutex locked. These are enforceable library
  checks, not proof that native CLI launch paths call them. Spawned native engines
  and independently launched workers remain blocked; no shared IPC is claimed.
- Effective client endpoint, SDK `max_retries=0` and wrapper ownership are checked
  again before every governed invocation. Streaming, multiple completions,
  extra-body/header/query overrides and request parameters outside the tested
  JSON-shaped subset are rejected. Parameters are not silently stripped or caps
  changed. Supported arguments are copied before awaiting the client to isolate
  them from caller mutation. The original response object is returned unchanged
  only after valid usage and accounting evidence are written.
- Usage is read before native missing-usage-to-zero coercion. Required prompt,
  completion and total counts must be nonnegative integers with consistent
  totals. Reasoning and cache counts are preserved as optional inclusive subsets,
  not double counted. Malformed or missing receipts retain the full reservation
  and latch the session closed. An actual total above the admitted bound preserves
  the raw observed counts and full unresolved reservation as `BOUND_VIOLATION`.
- Transport/SDK exceptions, timeouts and cancellations do not establish zero
  billing. They retain unresolved capacity and close admission. Ordinary failures
  become `AccountingRejected` rather than an SDK retry exception; cancellation
  propagates after accounting. Already admitted calls may finish and settle;
  no subsequent admission is allowed. A native retry after a successfully
  receipted response/parse failure consumes a fresh reservation and call slot.
- Policy/reservation/receipt/rejection files are exclusively created in a private
  attempt root. Events carry attempt/channel/PID/timestamp, role/task/condition,
  reservation identity, model/endpoint, contract identity, request hash and requested
  completion cap. Prompts, credentials and exception messages are not recorded.
  Inventory identities preserve hashes/counts. Contract/event integrity is checked
  before further admission. Write failure withholds dispatch or response and
  closes admission; earlier evidence is never overwritten. This is exclusive-file
  persistence, not a power-loss durability or external custody guarantee. A crash
  after reservation leaves an unresolved record; resuming the same root is not
  supported because the policy file collides.

Hosted internal-LLM usage has its own channel. ONNX and downstream/RQ3 context
labels are rejected and never charged to this session. Zero execution in those
channels is not an assertion about historical provider-internal counts.

Disabled instrumentation returns the original provider without inspecting it,
altering any resource, creating evidence or intercepting exceptions. Identity,
payload, response and exception parity are tested with fakes; existing Hindsight
adapter/contract regressions pass. Neither enabled-mode timing equivalence nor
installed-provider semantic equivalence is claimed. Enabled-mode I/O, copies,
unsupported-request rejection and failure stops are intentional effects.

## Offline validation

All tests used the assigned repository `.venv/bin/python` (Python 3.12.8).
That isolated venv was created from the existing Phase 08D-4 repository venv;
an ignored local `.pth` reuses its already installed pinned core test dependencies.
No global/user/provider package installation occurred. No ignored artifact or
venv is committed. Bytecode writing to reused dependencies was disabled.

Final command:

```text
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest \
  tests/unit/test_phase08d5_governed_sends.py \
  tests/unit/test_phase08d3_capture_accounting.py \
  tests/unit/test_phase08d4_evidence_persistence.py \
  tests/unit/test_hindsight_adapter.py \
  tests/unit/test_hindsight_lifecycle_trace.py \
  tests/contract/test_hindsight_provider.py \
  tests/unit/test_phase06_freeze.py tests/unit/test_rq4_policy.py -q
```

**143 passed**: 74 new governed-send cases and 69 existing regressions.
The earlier focused run had 113 passes and one opt-in real-service test skipped;
no real-service test ran. The full suite with known absent private fixtures was
not run and no complete-suite pass is claimed.

New tests cover direct startup/health fake probes; foreground/background/dedup/
tools; receipted response-validation retries; shared-session fallback rejection;
thread and async-task concurrency; committed-plus-outstanding exhaustion;
call/concurrency ceilings; absent/ambiguous/nonfinite limits; missing/malformed
usage; reasoning/cache subsets; failures/cancellation/overruns; unauthorized
models/endpoints/channel/attempts; client mutation/SDK retry drift; fork/startup
configuration rejection; evidence corruption/collision/write loss; context
isolation; and disabled parity. Fake probe/retry/task methods exercise the wrapper
contract, not execution of upstream Hindsight methods or a real SDK/transport.

`scripts/validate_experiment_freeze.py` passes with canonical SHA-256
`0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b`.
Changed sources parse successfully and `git diff --check` passes. No frozen source,
configuration, attempt, empirical row or research denominator is changed.

## Remaining blockers and review boundary

1. No complete installed-runtime boundary is established for every role/member,
   alternate implementation, native batch mode, worker or entrypoint. The owned
   fake resource wrapper cannot guarantee those paths. No all-send runtime
   completeness claim follows from the static audit or fake call counts.
2. Installed SDK/transport physical-send multiplicity, redirects, client
   replacement and process ownership need independent qualification. Native
   worker/CLI enforcement and complete attribution propagation are not connected.
3. No independently established endpoint-enforced inclusive token maximum exists.
   A configured output cap, estimated prompt size or advertised context window
   alone is insufficient. Usage reliability, reasoning/cache semantics and billing
   categories on a real endpoint are unverified. Real contracts are rejected.
4. Native multi-LLM failover may catch governance exceptions and call unwrapped
   members. A future complete boundary must demonstrate closure across all members
   and forbid unsupported provider configurations before construction.
5. D3 global quiescence, D5 resource/eligibility prerequisites and independent
   scientific review remain unresolved. Monetary ceilings are not claimed.

**Stop for independent review after branch publication.** Any runtime qualification,
provider/model/embedding call, Jetstream lifecycle, new interception architecture
or empirical pilot needs separate authorization. Freeze v1, Freeze-v2 draft,
Candidate10 `NO_GO`, frozen OpenViking S0 r2 ERROR and existing denominators remain
unchanged. Retrieved != Authoritative remains the governing rule.
