# Phase 03B — Provenance and Enforcement Trace Foundation

## Motivation

Memory lifecycle behavior is only one part of an agentic outcome. A stale or
incorrect action can originate at the source lifecycle, a derived provider
surface, retrieval, pre-model enforcement, model resolution, or tool
authorization. Phase 03B adds the versioned evidence model and hook boundaries
needed to distinguish those locations in future experiments without folding
them into the Phase 03 lifecycle result.

`BenchmarkResult` and lifecycle benchmark version `0.1` are unchanged. A
separate `ExperimentTrace` uses trace schema version `0.1`. Existing Phase 03
JSON therefore remains readable by the existing deserializer.

## Agentic Pipeline Model

The research pipeline is represented as:

```text
source lifecycle event
    -> provider memory state
    -> derived state (when observable)
    -> retrieval candidate
    -> pre-LLM enforcement decision
    -> delivered candidate set
    -> future model decision
    -> future tool authorization/consequence
```

Phase 03B executes through the delivered-candidate set only. Model and tool
execution are recorded as `NOT_RUN`; no fake output is created.

An explicit experiment ID anchors deterministic lifecycle, retrieval,
candidate, enforcement, and decision IDs. Timestamps remain observations and
are not used as the sole correlation mechanism.

## Failure-Origin Taxonomy

The trace schema represents these possible attribution locations:

- `SOURCE_LIFECYCLE`
- `DERIVED_STATE`
- `RETRIEVAL`
- `ENFORCEMENT`
- `MODEL`
- `TOOL_AUTHORIZATION`
- `UNKNOWN`

`FailureAttribution` requires a rationale and evidence-event references. Phase
03B does not automatically emit attributions: an empty tuple means that no
failure-origin claim was made. These names are a trace taxonomy, not a report
that every failure has been observed.

## Provenance Model

`ProvenanceEvent` records stable event and optional parent IDs, event type,
source/derived/provider record IDs, relation, lifecycle status, memory surface,
evidence status, and an aware timestamp. Relations include `CREATED_FROM`,
`DERIVED_FROM`, `SUPERSEDES`, `INVALIDATES`, `RETRIEVED_AS`, `FILTERED_FROM`,
`PASSED_TO_MODEL`, `CAUSED_DECISION`, and `AUTHORIZED_ACTION`.

Missing evidence is never converted into a causal edge. `UNKNOWN`,
`UNSUPPORTED`, and `NOT_APPLICABLE` are first-class provenance values, and a
concrete relation requires `KNOWN` evidence. Scenario target references and
provider-ID matches may preserve experiment correlation while provider-internal
causality remains `UNKNOWN`.

## Memory Surfaces

The normalized surface vocabulary is `SOURCE`, `VECTOR_INDEX`, `DERIVED`,
`SUMMARY`, `PROFILE`, `GRAPH`, `CACHE`, `RETRIEVAL`, and `UNKNOWN`. It is a
labeling vocabulary, not a claim that a provider exposes every surface. The
reference provider uses `SOURCE` for its controlled records. Mem0 source and
derived internals remain `UNKNOWN`; an observed query return uses the
`RETRIEVAL` surface.

## Retrieval Trace

Each `RetrievalCandidate` has a deterministic candidate ID, optional provider
memory ID, sanitized content, optional score, surface, source experiment-event
IDs, normalized lifecycle status, provenance status, and sanitized metadata.
The normalized adapter does not guarantee a provider score, so the trace uses
`null` rather than inventing one.

`RetrievalTrace` links the query lifecycle event to a retrieval event, an
enforcement event, the candidate and decision sets, and exactly the non-blocked
delivered IDs. Validation rejects duplicate candidates, missing or duplicate
decisions, event-ID mismatches, and an inconsistent delivered set. Metadata is
recursively rejected when a key looks credential-bearing. The trace runner
omits provider content by default; a caller must supply an explicit sanitizer
to populate `sanitized_content` under its experiment logging policy.

## Pre-LLM Enforcement Hook

`CandidateFilter.inspect_candidates(candidates, context)` is the stable
provider-independent boundary. The context carries explicit experiment,
scenario, retrieval, and enforcement IDs. Implementations return exactly one
`EnforcementDecision` per candidate with `ALLOW`, `BLOCK`, or `TAG`, a reason
code, authoritative status, rule ID, and provenance basis.

This is a plumbing interface, not the complete Memory Authority Gateway.

## Pass-Through Control

`PassThroughFilter` is the transparent D0/control. It returns `ALLOW` for every
candidate, including candidates with inactive or unknown status. Its purpose is
to prove that the enforcement layer can be inserted without changing retrieval
behavior.

## Lifecycle-Status Filter Baseline

`LifecycleStatusFilter` is a small deterministic metadata-only primitive. It:

- allows explicit `ACTIVE` status;
- blocks explicit `REVOKED`, `DELETED`, `EXPIRED`, and `SUPERSEDED` status;
- never infers lifecycle status from natural language;
- defaults unknown, unsupported, and not-applicable status to `TAG`, which is
  non-blocking and therefore remains in the delivered set.

The unknown-status action is explicitly configurable. The default avoids
silently declaring ambiguity safe or unsafe. This baseline is not the final
authority defense and is not evidence of security effectiveness.

## Reference Provider Validation

The deterministic reference provider opts into `KNOWN` source provenance
because its state machine and successor links are controlled by this project.
Tests execute write, update/supersede, query, pass-through enforcement, and
delivery. They verify that the query candidate points to the successor event,
that the `CREATED_FROM` and `SUPERSEDES` links are stable, and that the
delivered set exactly matches non-blocked decisions.

## Mem0 Provenance Limitations

The local Mem0 OSS 2.2.1 check records directly observable facts only:

- provider memory IDs;
- normalized records returned by retrieval;
- native same-ID update behavior already exposed by the adapter;
- native history already exposed by Mem0;
- experiment lifecycle association established by matching the observed ID.

Mem0 does not expose complete provider-internal causal provenance from source
events through vector or other derived state. Source/update relations and
candidate causal provenance therefore remain `UNKNOWN`. A
`RETRIEVED_AS` event is `KNOWN` only because the retrieval return itself was
directly observed. No internal causal edge is inferred from semantic content.

## Future Multi-Model Layer

`ModelDecisionRecord` can later record model name, endpoint class, prompt
template version, temperature, delivered candidate IDs, raw and parsed output,
latency, token counts, and cost. Model identity is an experimental factor; the
schema contains no conclusion about `llama-4-scout`, `gpt-oss-120b`,
`muse-glimmer`, or model strength.

For Phase 03B, `model_execution` is `NOT_RUN` and `model_decision` is absent.

## Future Tool-Consequence Layer

`ToolActionRecord` reserves tool name, requested action, authorization result,
execution flag, and consequence class. A future consequence runner may consume
the delivered candidates and model decision, but `LifecycleRunner` remains
limited to lifecycle/provider observations.

For Phase 03B, `tool_execution` is `NOT_RUN`, `tool_action` is absent, and no
real or synthetic external action is executed.

## What Phase 03B Does Not Claim

No LLM was invoked.

No security-effectiveness claim is made.

No provider vulnerability claim is made.

Phase 03B does not install or characterize another provider, implement the full
Memory Authority Gateway, run attacks, judge model behavior, or measure tool
consequences. The failure classes are reserved attribution locations, not
observed findings.

## Next Provider Handoff

A future provider should implement the existing lifecycle adapter contract and
leave the default provenance declaration at `UNKNOWN` unless its adapter can
justify a directly observable surface and relation. It should run the unchanged
Phase 03 canonical suite, the trace contract, and provider-specific tests. New
derived/profile/graph evidence should be added as explicit surface observations
without changing unknown edges into guessed causality.
