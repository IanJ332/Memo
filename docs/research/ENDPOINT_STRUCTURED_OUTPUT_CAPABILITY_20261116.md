# Endpoint structured-output capability check — November 16, 2026

**Outcome: `ENFORCEMENT_UNCONFIRMED`.**

Purpose: endpoint capability verification only. This record adds no model
request, no reservation, no package build, no VM lifecycle action and no change
to any V4–V6 result. `main` baseline: `cc8c4212` (after PR #35).

## Question

Our three registered contracts each sent `response_format = {"type":
"json_schema", "json_schema": {"strict": true, "schema": ...}}` and each came
back missing a key that schema required. Does this endpoint actually enforce
the schema, i.e. constrain decoding, or does it merely forward the parameter?

## What was checked

### 1. Serving identity (documented)

- `qwen-3.8-27b` is served by **vLLM**, not SGLang: "vLLM serves Qwen3.8-27B
  from a single NVIDIA H100 cloud instance running on Jetstream2, using
  speculative decoding to speed up generation"
  (`https://docs.jetstream-cloud.org/inference-service/overview/`).
- Direct model routes (`https://llm.jetstream-cloud.org/qwen-3.8-27b/v1/...`)
  reach vLLM behind Caddy. The LiteLLM gateway is documented only for the
  `/api/` chat-UI proxy route, so it is not in this request path.
- Response headers confirm the shape: the model route returns
  `server: Caddy`; `/api/*` and `/health` return `server: uvicorn` with
  `via: 1.1 Caddy`.

### 2. Published parameter support (documented)

- The official inference-service pages (`overview`, `api`, `api-examples`,
  `status`, `ui`) never mention `response_format`, `json_schema`,
  structured/guided decoding, grammars or logit constraints. A scan of all 146
  sitemap URLs found no statement either way.
- Only `tool_choice` is illustrated (function-calling example). Parameter
  pass-through beyond that is undocumented.
- **No engine version is published** anywhere in that documentation, so no
  version-gated capability claim can be made from it.

### 3. Observed compliance (recorded, prior work)

Three requests, one per contract, all with `strict: true`:

| | Schema required | Model returned | Missing |
| --- | --- | --- | --- |
| V4 | `outcome`, `tool`, `arguments` | `{"tool": null}` | `outcome`, `arguments` |
| V5 | `outcome`, `tool`, `arguments` | `{"outcome": "ABSTAIN", "tool": null}` | `arguments` |
| V6 | `outcome`, `tool` (+branch rules) | `{"outcome": "PROPOSE_ACTION", "tool": "send_report"}` | `arguments` |

Enforcing decoders cannot emit an object that violates the supplied schema:
constrained decoding masks disallowed tokens, so an incomplete object is
unreachable. Three non-conforming outputs are therefore positive evidence that
enforcement was **not** active for these requests. They say nothing about
whether the deployment could enforce it if configured differently.

### 4. Not established

- Engine version and whether its guided-decoding path is enabled. vLLM's
  structured outputs are gated by backend availability (xgrammar / guidance)
  and by request form; a version-compatible server can still be started in a
  configuration where the schema is advertised but unenforced, or where the
  parameter is dropped.
- Whether vLLM returned a validation error, silently ignored
  `response_format`, or accepted and ignored `json_schema` while honoring
  `json_object`. Our preserved evidence records `content-type` and
  `x-request-id` only; the harness deliberately whitelists headers, so no
  engine banner was captured.
- Whether any other supported parameter form (`guided_json` inside
  `extra_body`, `structured_outputs`, `json_object`) is honored here. None of
  these was ever sent, so no observation exists.

## Reading

Two distinct claims must be kept apart, as required:

1. **Documented configuration:** partially known — vLLM engine identified, no
   version, no structured-output statement.
2. **Observed compliance:** failed three times with a strict schema declared.
3. **Verified decoding enforcement:** not established, and the three failures
   argue it was off rather than on.

`ENFORCEMENT_UNAVAILABLE` is not supportable either: "unenforced in three
observed calls" is not "unsupportable by this deployment". The correct finding
is `ENFORCEMENT_UNCONFIRMED`.

## Consequence for the research line

No probe is registered here, and none was executed. Item 3 of the task
conditioned a probe on first establishing that supported enforcement exists;
that precondition failed. Registering a probe now would be a fourth attempt to
discover the same unknown through the same request path, which is exactly the
iteration the closeout forbids.

The remaining gap is not decidable from this checkout. Closing it needs one of:

- an operator statement of the engine version and whether guided decoding is
  enabled for this model, or
- a request that would only succeed under enforcement (a negative-control
  schema the model could not satisfy by luck), which is still a live inference
  request and needs its own authorization.

Until one of those exists, treat `response_format` on this endpoint as
advisory and do not build experiment contracts that depend on it.

## Effect on prior results

None. V4, V5 and V6 classifications, evidence, digests and consumed
reservations are unchanged and unreplayed. This document adds no authority.

## Documentation correction

`AGENTS.md` previously said the corrected V6 request "is spent". That conflated
two objects. Corrected: the executed manifest
`30e70e048a88638f075055e67da89307fa8481e885ff02d141e6c0aca9bc0ac0` holds the
single `V6_COMPAT` reservation and is consumed; the corrected manifest
`42ff8f09094a657e4b9b8e576225b607385210621bf9c215d3a6e77276fbe85c` was never
sent and holds no reservation. Neither fact authorizes a replay.
