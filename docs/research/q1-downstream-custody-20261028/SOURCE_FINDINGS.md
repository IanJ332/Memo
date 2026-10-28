# Q1 downstream source investigation — October 28, 2026

Baseline: `22fd438ffa85826e4635e37d0240c9a181b272c1`.
Investigator: `/root/postq1_consumers`, independent of the Q1 runner implementer.
This is a read-only source investigation. The binding file records exact original
source bytes; current claims do not establish deployment outside this repository.

**No implemented connection was found from the corrupted Q1 source attribution
to a security-policy decision, native proposal or protected dispatch.** The
strongest established consequence remains false attribution and measurement
integrity. Implemented report/triage consumers are separate from security
enforcement, and the existing context filter path does not consume Q1's corrupt
metadata attribution. This stops the downstream exploit claim at its missing
intervening edge.

## Actual consumer graph

| Component and exact location | Implemented value flow | Role and limit |
| --- | --- | --- |
| `models/authority.py:101–135`, `normalize_authority_exposure` | Candidate event IDs plus an independent authority ledger → exposure enum | Pure measurement function. No retrieval, context, model, authorization or dispatch call. |
| `runner/storage_batch.py:326–390`, `_correlated_event_ids` / `_retrieval_payload` | Matching provider metadata names are unioned with Host-held native-ID associations; any resolved source makes legacy producer provenance KNOWN | Proven Q1 attribution ingress. Result objects and payloads describe exposure; they do not authorize an action. |
| `runner/storage_batch.py:500–520` | Adapter query completes before payload/candidates are constructed | The scorer result cannot select the already-returned query records. No edge from exposure back to native retrieval is implemented. |
| `runner/storage_batch.py:628–789` | Exposure enum and candidate classes populate result fields and residual diagnostics | Research measurement. Filter/model/tool fields remain absent and downstream/RQ3 call counts are zero at781–798. |
| `runner/storage_batch.py:820–901`, `aggregate_runs`; `904–953`, `residual_index` | Exposure differences across repetitions can mark research inconsistency/residual and queue root-cause candidate cells | Real research-triage consumption, not memory admission or security authorization. The queue explicitly executes no probe. Q1's unchanged aggregate MIXED result does not itself flip this enum-based comparison. |
| `runner/experiment.py:63–91`, `aggregate_repetitions` | Exposure enums contribute to INCONSISTENT/residual classification | Research aggregation, with no model/dispatch action. `advances_to_rq3` at109–123 is a separate pure boolean helper; no in-repository execution caller consumes it. |
| `runner/calibration.py:219–311` | A matching metadata event takes precedence over other mappings, then exposure/provenance are recorded; the reference adapter has a measurement-oracle assertion | Calibration output/assertion, not context admission. Model-call invariants at84–110 forbid hosted/RQ3 calls. This is an additional legacy measurement ingress, not proof that Q1 ran through calibration. |
| `runner/provenance.py:198–317`, `_retrieval_trace` | Host-held native-ID links/provider-exposed IDs → actual CandidateFilter → delivered candidate ID list | Implemented pre-model trace/filter path. For Mem0, lines219–229 do not read experiment_event_id/source_event_id metadata claims. Mem0's source-ID hook is the base empty tuple (`adapters/base.py:126–131`), so direct Host ID mapping is used. |
| `enforcement/filters.py:15–39`, `PassThroughFilter` | Every candidate → ALLOW | Explicit control. Neither source attribution nor exposure is consulted. |
| `enforcement/filters.py:42–112`, `LifecycleStatusFilter` | Only `candidate.lifecycle_status` → ALLOW/BLOCK/configured unknown action | Metadata-only baseline, explicitly not the Memory Authority Gateway. Event IDs, exposure, correlation completeness and generic provenance do not govern its decisions. |
| `runner/authority_correlation_v2.py:142–175` | Scope/byte/source-bound Host association plus ledger → corrected event projection and exposure | Opt-in source-exposure correction. No action authorization or context filter call. |
| `runner/authority_correlation_v2.py:178–188`, `trace_payload_v2` | Original trace/filter is evaluated first, then only candidates are replaced by the corrected projection | The wrapper retains original decisions and delivered IDs. Existing concrete filters ignore the changed fields, so no current attribution-sensitive decision was found. This ordering must not be advertised as automatic quarantine or future policy reevaluation. |
| `models/provenance.py:205–255`, `RetrievalTrace` | Validates unique candidates, one decision per candidate and delivered IDs equal the non-BLOCK set | Schema/trace consistency, not an authority decision. Model and tool records must remain absent when NOT_RUN. `ExperimentTrace` at277–296 checks event references, not authorship or action permission. |
| `runner/rq4_policy.py:244–495`, `evaluate_candidates` | Separate CandidateEnvelope, exact raw bytes and independently bound proposition/authority/lineage → ALLOW/DENY/QUARANTINE and allow-only framed bytes | Implemented pure offline mediation. Current in-repository calls are tests; no production trace/storage/Q1 converter or consumer of its delivered bytes was found. External deployment is not established. |
| `models/mediator.py:67–126`, `CandidateEnvelope` | Requires a different schema with independent raw/proposition identity, logical fact, source IDs and relation evidence | A RetrievalCandidate is not this contract. No implemented Q1/legacy-attribution adapter exists. Constructing one for the audit would create the missing edge rather than prove an existing vulnerability. |
| `runner/rq4_policy.py:498–536`, `evaluate_baseline` | Deliberately limited pass-through or ancestry-only logic on CandidateEnvelope | Implemented experimental baselines, currently test-called. They are not consumers of Q1 attribution without an added adapter. |
| `native_q1/core.py:163–192` | Both source projections and exposure classes → recorded per-record/aggregate analysis | Qualification measurement only. The observed five false CURRENT links are not fed into a context or authorization gate by Q1. |

The principal source-to-context path is thus different from the demonstrated
metadata-to-measurement path. Feeding storage candidates directly into a generic
filter API can test field sensitivity, but no current application call connects
those two functions. It must not be described as an observed wired route.

## Model, independent authorization and protected action

The current R1 request builder (`r1/protocol.py:145–157`) copies literal selected
record content into `retrieved_notes`; it does not copy authority exposure or
candidate event links. R1 collection verifies actual selected identity/order and
request custody (`r1/collection.py:31–64,94–119`). Its proposal classifier uses
independent Host ACL fields and actual native argument strings
(`r1/protocol.py:160–233`). This is a distinct historical scientific path, not
evidence that Q1 metadata affected a model. No R1 request was made in this audit.

R1-AV uses selected literal content and independent ACL classification/grounding
(`r1_av/protocol.py:113–177`). It explicitly reports protected_dispatches=0.
Its stopped execution and registration remain separate; source availability is
not permission to activate or replay it.

`scripts/research/f04_cohort0_compat.py:447–503` loads byte-pinned historical
auth/policy/security modules and evaluates a separately enrolled authentic
model proposal against an independent Host ACL. The decision-only function
excludes ProtectedDispatcher, sink writes and execution. Q1 has no model proposal
or enrollment for that path. Neither Q1 event links nor exposure enums enter its
`authorize_tool_call` invocation. The retained separate authorization components
must not be called a Q1 consumer merely because their names mention authority.

No current protected-dispatch implementation is connected to these Q1 fields.
The narrower source conclusion is absence of a demonstrated path in the examined
repository, not universal immunity of an external application or future adapter.

## Supported read-only consequence checks

The actual legacy and V2 trace wrappers can receive the same sealed Q1 search
records under the existing two concrete filters. This preserves an implemented
producer→filter route without inventing an authority-sensitive filter or model
response. Any query observation envelope/trace timestamp created for this offline
replay is authored audit scaffolding, not an original native timestamp. Raw
native records and their original capture identities remain unchanged.

A separate **COUNTERFACTUAL_MISSING_HOST_ASSOCIATION** control is justified only
to falsify the concrete overclaim that V2 UNKNOWN automatically quarantines
context. It can supply an empty Host snapshot to the existing wrapper on the same
records: the correction then records unresolved attribution while the actual
metadata-only/control filters retain their decisions. This is not a condition
observed in native Q1 and not a promise those primitive filters make. It establishes
the API's division of responsibility, not an exploit or an extra native result.

No supported current path converts Q1 attribution into RQ4's independently bound
CandidateEnvelope. Do not manufacture that adapter, proposition identity or a
model response to claim a downstream consequence.

## Consequence ladder and research decision

1. **Native persistence:** observed and independently audited in sealed Q1.
2. **False source attribution:** observed, with legacy CURRENT contamination and
   V2 correction on the same native records.
3. **Security-decision influence:** not demonstrated. Current concrete context
   filters ignore the corrupted fields; the RQ4 bridge is not implemented.
4. **Model behavior:** not evaluated by Q1 or this investigation.
5. **Protected execution:** no connected path or executed action established.

Stop the action-authorization vulnerability claim at level2. Research aggregation
and diagnostic provenance labels can be affected, but they are not a security
policy or execution grant. Further provider/model collection is not justified by
this absent edge. A future study must first identify a real lower-trust ingestion
or attribution-consuming admission interface; building a new bridge would be a
prospective integration design, not confirmation of an existing exploit.
