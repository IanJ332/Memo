# Architecture and Assumptions

## Research architecture

| Layer | Responsibility | Failure boundary |
| --- | --- | --- |
| Memory lifecycle | Apply source writes, supersession, invalidation, deletion, restart, and provider-native derivation; observe source/derived state. | F1/F2 |
| Authority | Maintain experiment-defined lifecycle authority and enforce it on directly observed evidence before model delivery. | F4 |
| Model | Interpret only the context that passes enforcement; model choice is a downstream moderator. | F5 |
| Tool | Authorize and execute consequences separately from model intent. | F6 |

Retrieval sits between memory and authority. It can expose a provider state but
does not make that state authoritative. The project distinguishes memory-system
failure, retrieval exposure, authority-enforcement failure, model
interpretation, and tool consequence.

## Frozen failure taxonomy

- **F1 SOURCE_LIFECYCLE:** intended source lifecycle transition failed.
- **F2 DERIVED_STATE:** derived/profile/graph/cache state failed to follow the
  source transition.
- **F3 RETRIEVAL:** retrieval exposed state inconsistent with observed source
  and authority evidence.
- **F4 ENFORCEMENT:** pre-LLM authority enforcement allowed disallowed evidence
  or suppressed allowed evidence.
- **F5 MODEL:** the model interpreted delivered context incorrectly.
- **F6 TOOL_AUTHORIZATION:** tool authorization/execution produced an unsafe
  consequence.
- **UNKNOWN:** evidence does not localize the failure.

Do not assign a class beyond what direct evidence supports.

## Two independent outcome channels

Exact visibility uses literal frozen content matching:

- `CURRENT_ONLY`
- `CURRENT_AND_STALE`
- `STALE_ONLY`
- `ABSENT`
- `UNSUPPORTED`
- `ERROR`

Authority exposure uses experiment IDs and directly observed correlation or
lineage:

- `AUTHORITATIVE_ONLY`
- `AUTHORITATIVE_AND_NONAUTHORITATIVE`
- `NONAUTHORITATIVE_ONLY`
- `NONE`
- `UNKNOWN_PROVENANCE`

A paraphrased derived record may be exactly `ABSENT` but authority-correlated.
Never bridge the channels with fuzzy matching, an embedding threshold, an LLM
judge, or semantic guessing. `UNKNOWN_PROVENANCE` means the provider evidence
cannot justify lineage; it must not be guessed from similar text.

## Scope guardrail

The strong framing is:

1. cross-provider authoritative lifecycle semantics;
2. source/derived-state propagation localization; and
3. provider-independent lineage-aware authority enforcement before LLM
   reasoning.

Do not reduce the work to “stale memory affects agents.” Model susceptibility
and tool consequence are later layers. The storage experiment first establishes
what remained, where it propagated, what retrieval exposed, and what authority
evidence can support.

## Scientific assumptions that require change control

- Authority comes from the experiment lifecycle ledger, not provider rank,
  recency, visibility, or semantic similarity.
- Unsupported native lifecycle operations stay unsupported; they are not
  emulated silently.
- Quiescence uses provider completion evidence, never fixed sleep alone.
- Raw repetitions are primary evidence; inconsistency is preserved and never
  majority-voted away.
- Freeze v1 fixes providers, versions, configurations, scenarios, repetitions,
  timeouts, normalization, advancement rules, defenses, and aggregation.
- Canonical originals are immutable. Repairs and combined datasets are derived,
  provenance-retaining artifacts.

See [`EXPERIMENT_FREEZE_V1.md`](../experiments/EXPERIMENT_FREEZE_V1.md) for the
full protocol and [`EXPERIMENT_LEDGER.md`](EXPERIMENT_LEDGER.md) for execution
provenance.
