# Phase 2B-5A controlled reasoning amendment

The predecessor is a real, consumed negative observation: HTTP 200/exact model,
256 completion tokens all reported as reasoning, `length`, null content. It
supports a budget-exhaustion hypothesis; it does not establish schema rejection.
The prior manifest, reservation and evidence archive remain immutable.

New registration: `phase2-provider-v3-nonthinking-compatibility-1`, manifest
SHA-256 `6880f8b21824554b797df6ccaf758ccf7d423e24561aa0f1d9c721f3b1dd94bc`.
Exact request: 1,105 bytes, SHA-256
`76d31918876ab6094ed9e35338eff2752f1dffeee3c35896dc150c2a94e3bd3a`.
Removing only top-level `chat_template_kwargs: {enable_thinking: false}` reproduces
the predecessor's exact 1,056-byte request. Instructions, task, strict schema,
model/endpoint, 256-token budget and deadlines are unchanged. No `extra_body`
wrapper is serialized into HTTP JSON.

[Qwen's direct HTTP example](https://qwen.readthedocs.io/en/stable/deployment/vllm.html)
places `chat_template_kwargs` at the request root; its SDK example supplies it
through `extra_body`. [vLLM's reasoning documentation](https://docs.vllm.ai/en/stable/features/reasoning_outputs/)
describes this request-level template control.
[Jetstream's public API contract](https://docs.jetstream-cloud.org/inference-service/api/)
identifies the fixed direct network-scoped Qwen endpoint and OpenAI-compatible
backend interface. Those documents establish a candidate mechanism; only the
new bounded observation can establish this deployment's behavior.

The same canonical persistent ledger is reused with a distinct manifest key.
The old consumed row is mandatory before new hosted admission. Fresh evidence
and result paths are separate. The existing orchestration, sender, dispatcher
and private evidence pipeline remain in use. Valid abstention may establish
response compatibility but remains inappropriate abstention for this authorized
task's utility outcome. Positive reported reasoning or nonempty reasoning text
stops as `THINKING_MODE_IGNORED`; absent usage remains UNKNOWN.

Unchanged dependencies/runtime reuse their prior qualification. The versioned
successor inventory explicitly records reuse, not a new full installed-file
attestation. Its 168 checks bind source, interpreter/configuration, 57 dependency
metadata files, native/trust records, prior qualification and preserved failed
archive. No dependency acquisition/rebuild or 3,038-file sweep is performed.

Targeted offline results: 28 nonthinking/provider-evidence tests PASS; 16 affected
binding tests PASS, four predecessor-bootstrap fixture cases deselected. The sole
independent reviewer directly verified exact code/request/manifest/inventory,
nine safe delta members, all 89 source hashes and the 168-check coverage, and
independently reran the 28 tests. ACCEPT for the reviewed source/package does not
grant live authority. Supported exact-operation platform approval remains an
independent gate; denied actions must not be bypassed or repeatedly submitted
without a relevant changed authorization decision.

Actual runtime, request outcomes, conditional smoke and lifecycle are recorded
in the separate stage closeout. This amendment document does not claim a new
successful model observation or authorize a full campaign.
