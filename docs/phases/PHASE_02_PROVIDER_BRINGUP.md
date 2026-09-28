# Phase 02 — Provider Bring-up

## Status

**PHASE 02A — LOCAL MEM0 BRING-UP**

Phase 02A is implemented on branch `phase-02-mem0-bringup` from approved Phase
01 commit `e524eb53e3f5242466f723dc8ec2847f2e508f21`.

**PHASE 02B JETSTREAM VALIDATION HAS NOT STARTED.**

## Phase 02A Baseline

- Provider: Mem0 OSS Python SDK via `from mem0 import Memory`
- Exact version: `mem0ai==2.2.1`
- Embedding: local Hugging Face
  `sentence-transformers/paraphrase-MiniLM-L3-v2` (384 dimensions)
- Vector store: embedded local Qdrant with on-disk persistence
- History store: project-local SQLite
- Writes: raw-memory ingestion with `infer=False`
- Telemetry: disabled with `MEM0_TELEMETRY=false`
- LLM: constructor-only placeholder directed to an unused loopback endpoint;
  integration tests fail if Mem0 invokes it
- Runtime root: repository-local `runtime/`

## Adapter Status

`Mem0MemoryAdapter` implements the Phase 01 interface using native Mem0 calls:

```text
reset_namespace       -> delete_all(user_id=namespace)
write                 -> add(..., user_id=namespace, infer=False)
query                 -> search(..., filters={user_id: namespace})
update_or_supersede   -> update(memory_id, text=...)
delete_or_invalidate  -> delete(memory_id)
list_or_inspect       -> get_all(filters={user_id: namespace})
restart               -> close and reconstruct Memory with identical paths
```

Mem0 native update mutates the existing ID. Phase 02A does not label that as a
semantic `SUPERSEDED_BY` relation. Native revocation is not available through
this path; a request for `REVOKED` is explicitly rejected rather than emulated.

## Validation Results

- Tier 1 provider-independent tests: `10 passed`
- Tier 2 Mem0 integration tests: `3 passed`
- Complete suite: `13 passed`
- Reusable provider contract: passed against real Mem0
- Cedar reset/write/query/update/query/inspect/delete/query/inspect workflow:
  passed
- Restart sanity: written canary survived reconstruction; after deletion it
  remained absent after another reconstruction
- Exact dependencies: `pip check` reported no broken requirements

## Observed Native Behavior

Mem0 assigned a UUID at write. Native update retained that UUID, replaced the
current text, and appended an `UPDATE` row to SQLite history containing old and
new text. Native delete removed the vector from search and `get_all`, while
SQLite history retained `ADD`, `UPDATE`, and `DELETE` events; the delete event
had `is_deleted=true`. These are characterization results, not vulnerability
claims.

## Unresolved Issues and Limitations

- Phase 02A validates Windows local execution on Python 3.14 only.
- `fastembed` was not installed, so optional Qdrant BM25 scoring is disabled;
  dense semantic search passed.
- spaCy NLP extras were not installed; Mem0 logged lemmatization fallback
  warnings, while required operations still passed.
- Normal list/search surfaces expose current records, not deleted records.
- No authorization gateway, attack workflow, decision model, or security
  consequence experiment exists yet.

## Phase 02A / Phase 02B Boundary

Phase 02A ends with a pinned local adapter, offline integration tests, observed
native lifecycle behavior, a local persistence check, provider documentation,
and a reproducibility manifest.

Phase 02B requires separate authorization. It may validate this baseline on
Jetstream, but must not silently change provider versions, embedding models,
storage modes, or lifecycle claims. No Jetstream VM was accessed or unshelved
during Phase 02A.

## Later Extension Points

Hindsight, RetainDB, OpenViking, and Honcho remain uninstalled and unconfigured.
They require separately authorized provider phases after the Mem0 baseline is
reviewed.
