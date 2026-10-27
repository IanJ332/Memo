# NEXT-LP-NATIVE-01-Q1 — narrow prospective qualification scope

**DESIGN ONLY / NOT EXECUTED / NOT READY FOR LIVE AUTHORIZATION.** This names a
proposal, not a claimed execution or fresh store. Existing evidence is sufficient
for direct-record V2 applicability and same-ID/reopen behavior. This optional
study would resolve exact hostile metadata roundtrip and capture-time custody.
Do not launch it from the standing engineering authorization.

## Hypotheses and host oracle

Mem0 OSS 2.2.1, infer=False, embedded local Qdrant/SQLite and existing cached
MiniLM embeddings only. One fresh isolated store and one fresh namespace; two
records maximum. No Hindsight or provider expansion. No derived-lineage claim.

Host oracle, sealed before native startup outside the provider-writable mount:
event CURRENT authorizes exact bytes `Current routing note: destination ALPHA.`;
event UNTRUSTED does not authorize exact bytes
`Untrusted routing note: destination OMEGA.`. The second record's write metadata
contains experiment_event_id=CURRENT and source_event_id=CURRENT. It is a
deliberate lower-trust treatment, never the oracle. Update CURRENT to exact bytes
`Current routing note: destination BETA.`; host policy revision2 authorizes the
new bytes and retains revision1 as obsolete. Both records use the namespace
selected by the fresh execution package. SDK-native IDs are learned from each
uniquely paired add return, not predicted or recovered from metadata.

The host retains operation input, paired raw SDK response, normalized bytes,
provider/version, namespace, native ID/source ID, host event, authority revision
and byte identity before any scoring. A separate host output location retains
the association artifact; provider processes receive no write access to it.
Host journal custody must be independently reviewed; a caller-supplied digest
does not authenticate itself. Namespace filtering and exact content equality
are checks on recorded coordinates, not proof of provider trustworthiness.

## Exact native SDK ceiling and lifecycle

Maximum **18 top-level SDK invocations**, no automatic retries, no fallback or
replacement store. Count each attempted invocation before dispatch, including
failed/ambiguous operations. Underlying local embedding/vector/SQLite work is
separate; journal it where supported and do not call 18 a bound on internal work.
Memory.from_config construction ceiling3, explicit close after each phase.

| Ordinal | SDK operation | Purpose |
| --- | --- | --- |
| 1 | get_all(namespace) | Prove fresh namespace empty; otherwise STOP |
| 2–3 | add(CURRENT,infer=False); get(returned ID) | Independent direct binding |
| 4–5 | add(UNTRUSTED,forged metadata,infer=False); get(returned ID) | Exact metadata treatment |
| 6 | search("routing note",namespace,limit10) | Preserve raw native ordering and all returned records |
| — | close; new process/reopen same store | No reset or reinsertion |
| 7–9 | get_all(namespace); get(CURRENT ID); get(UNTRUSTED ID) | Identity, byte and metadata persistence |
| 10–12 | update(CURRENT ID,new bytes); get(CURRENT ID); search(same query) | Same-ID mutation; old association UNKNOWN, independently refreshed association complete |
| 13–14 | delete(UNTRUSTED ID); get_all(namespace) | Native absence plus host revocation of the treatment association |
| — | close; new process/reopen same store | No reset or reinsertion |
| 15–18 | get_all(namespace); search(same query); history(CURRENT ID); history(UNTRUSTED ID) | Persistence and recorded native history, without inventing causal ancestry |

After final close, remove only the fresh task-owned store and container, verify
absence at the host filesystem/container boundary and retain the journals.
There is no native reset/reinitialization or uncounted cleanup SDK call.

Evaluate original storage producer and V2 on the identical normalized native
observations offline. Preserve the complete host-known provider_events mapping
for both records in the baseline; do not discard the UNTRUSTED binding to
manufacture an AUTHORITATIVE_ONLY result. Report per-record source-event
attribution and classification, separately from full-returned-set exposure.
The primary metadata endpoint is an unsupported CURRENT source attributed to
UNTRUSTED. With its legitimate nonauthoritative mapping retained, the baseline
may classify this record MIXED, not AUTHORITATIVE_ONLY. A full-set MIXED label
alone cannot distinguish that contamination from legitimate mixed exposure.
Unsupported AUTHORITATIVE_ONLY is a secondary endpoint, not a required result.
Capture-time host association for UNTRUSTED points to its
own nonauthoritative host event, despite forged metadata. Keep original and
refreshed snapshots separate; never rewrite the initial artifact. Freeze all
oracle expectations and analysis before dispatch. Search omission is an observed
retrieval outcome, not evidence that a forged metadata value was stripped.

Outcomes: exact metadata roundtrip OBSERVED/NOT_OBSERVED/UNKNOWN; independent
direct binding COMPLETE/INCOMPLETE; baseline unsupported-authority YES/NO/UNKNOWN;
V2 authoritative/mixed/nonauthoritative/NONE/UNKNOWN. Missing association remains
UNKNOWN rather than malicious. Unknown native outcomes remain in the denominator.
No infer=False experiment establishes partial derived-ancestry completeness.

## Prospective resource and approval envelope

Local only; no Jetstream dependency. One task-owned cached provider container at
a time, maximum2 CPUs/6GiB, network none; existing locally cached embeddings,
zero package/model downloads, zero provider-internal hosted LLM calls, zero hosted
decision-model requests, zero protected dispatch. Maximum45 minutes from an exact
authorized start and maximum256MiB newly written evidence. Require minimum8GiB
free host disk before launch. No new image build, VM resource change or unrelated
container operation. Missing runtime/model cache means STOP, not installation.

Cleanup removes only the fresh task-owned container/store and verifies absence;
preserve all evidence and failures. Any early stop retains spent call count and
partial observations, attempts only already approved owned-resource cleanup, and
never replays the attempt. No Exosphere resource, protected volume or old store
is touched. No browser, SSH, external send or cloud action is needed.

Before an authorization request is reviewable, the execution handoff must bind
exact runner/runtime/source/fixture/oracle SHA-256 values,
fresh attempt and store identities, concrete UTC window, supported exact launch
command, all native/cleanup effects and genuine independent review. The owner
decision must cover that scientific collection; the actual supported platform
mechanism must review the complete exact invocation/effects where required.
Owner consent, review, runtime admission and tool approval remain separate.
No fake standalone receipt or self-issued authorization flag is acceptable.

This is the narrowest proposed scientific scope, **not a current request for
approval**. Qualification of the small execution handoff precedes asking the
owner to authorize it. No native operation has been performed or authorized by
this document.
