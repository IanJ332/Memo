# NEXT-LP-NATIVE-01 — evidence-first native applicability investigation

**Offline investigation complete; next decision NARROW.** Accepted starting main:
`a89ffb0015fa01ea6be137193a94c64c3161c77b`. No scientific collection was started.
The new read-only projection uses authentic retained Mem0 SDK captures, not new
native calls or synthetic replacement records. Historical R1, LC12, Track B and
NEXT-LP-01 observations, source and classifications remain unchanged.

## Findings and evidence classes

| Question | Classification | Supported conclusion and limit |
| --- | --- | --- |
| RQ1 Mem0 native identity reachability | VERIFIED source route; OBSERVED benign native metadata; exact hostile treatment UNKNOWN | Pinned Mem0 2.2.1 preserves arbitrary metadata through infer=False payload insertion and get/search return; unchanged adapter copies it into the original vulnerable storage correlation path. Native captures preserve benign metadata. No recorded forged event-ID treatment or demonstrated untrusted-writer access. |
| RQ2 Host association custody | VERIFIED retrospective reconstruction; prospective capture-time custody UNKNOWN | Independently retained registered design/ACL and host SDK inputs identify scope, exact bytes and operation order; paired native add returns supply IDs. Reconstructed associations are analytical artifacts, not historical authenticated V2 artifacts. |
| RQ3 lifecycle/reopen | OBSERVED | 16 R1 stores preserve direct ID→bytes across two processes. Separate authentic qualification updates bytes under the same ID and deletes a disposable record before reopening. An ID alone cannot guarantee binding freshness. Native revocation/derived lineage is not supplied by infer=False. |
| RQ4 V2 applicability | OBSERVED retrospective direct-record projection | 48 retrieved native record instances across 32 retrieval observations resolve completely using 24 reconstructed host associations; 32 current records have complete authoritative correlation. This is later offline use of V2, not a historical deployed defense. |
| RQ5 caller coverage | VERIFIED source audit | V2 is called by NEXT-LP-01, its tests and this explicit retrospective script only. Ordinary storage batch, provenance runner and calibration retain original behavior. No caller migration occurred. |
| Hindsight native derived applicability | UNKNOWN | LC12 none/chunks captures contain direct world facts, not a missing-derived-parent treatment. Historical derived views demonstrate native parent IDs, but do not establish capture-time V2 custody or complete native lineage. No expansion to Hindsight is justified here. |

## Authentic retained evidence and reproducible analysis

The original R1 inventory is pinned to
`2f5c7d44d3c8b1a0e3a12a61e048a65efe7438c9e8b3977346e7b90222daba83`.
The script verifies every **4,666 indexed member** before analysis and rechecks
each consumed member at use. This establishes continuity with the previously
accepted host-retained capture, not independent authentication by a self-supplied
hash. Original raw records and administrative material remain private.

The [aggregate output](retrospective-summary-v1.json) contains no native IDs,
namespaces, raw content, host ACL values or administrative payloads. It binds the
accepted adapter, V2 source, host design/ACL and reconstructed association set.
It is a new derived analysis, not a replacement original result or new campaign.

| Retrospective observation | Count |
| --- | ---: |
| Host add input/return bindings | 24 |
| Stores exercised and reopened | 16 |
| Actual search observations | 32 |
| Retrieved native record instances / complete direct correlations | 48 / 48 |
| Current records with complete authoritative correlation | 32 / 32 |
| Exposure AUTHORITATIVE_ONLY / MIXED | 16 / 16 |
| New native operations / hosted scientific model requests / Jetstream actions | 0 / 0 / 0 |

These repeated observations are not independent population samples. The 32 R1
retrieval observations are exercise/reopen captures, not the 32 downstream R1
model requests. No model output was rescored. Historical records are labeled
nonauthoritative using the independent registered current-record/ACL assignment;
their provider lifecycle state remains ACTIVE. No native supersession is invented.

Reconstruction joins **host-authored job/design → exact SDK add input → unique
add-return ID → later raw search ID/scope/bytes → independently retained authority
snapshot**. It never selects authority from batch_role, case, provider metadata,
retrieval rank or content similarity. Event labels beginning RETROSPECTIVE are
new analytical names for the host write operations. They are not claimed to be
native event IDs or preexisting V2 host journal entries. Generic Mem0 provenance
remains UNKNOWN while direct host association completeness is true.

Use an existing qualified repository `.venv`; no dependency installation or
native adapter construction is required:

```sh
"$PY" -I -B scripts/research/next_lp_native01.py --evidence-root /absolute/private/R1EX-20261026-02
"$PY" -I -B -m pytest -q -p no:cacheprovider tests/research/test_next_lp_native01.py
```

The evidence root must be the original retained inventory, not a provider export
with an invented custody claim. The script emits only aggregates to stdout and
denies socket/DNS and process dispatch before importing project code. Its
ReferenceMemoryAdapter subclass is only a receiver for the actual pure Mem0
trace properties; native records come from real SDK return artifacts. It does
not pretend to instantiate Mem0 offline. Six supplemental tests exercise
inventory/member tamper, use-time changes, unindexed members, path escape and
duplicate-member rejection; these are custody controls, not native observations.

## Original source and secondary observations

| Artifact | SHA-256 |
| --- | --- |
| Mem0 adapter | `cf244d7896a1787b0bac7fb2cc0f4fa59b5ba7070411bf1f8b458ba6f0a84d16` |
| V2 correlation | `e0c400040a16c4018cf7eb8bc13df4bc153d8a9e5cf7327d8efda8db6d752362` |
| Original storage producer | `fce4f1f7772b2f547ed27ab890c4ccbdb1ee8bb9737421a5315f0bceb46e0d23` |
| Original provenance runner | `acd33ab2d537a2f46e20c1d2aa209ae46869e00073ce3c6c10ae3ef490213364` |
| Qualified Mem0 2.2.1 wheel | `fe91bb91ac8926231993a4aa58df00a60c6c74c709e6a338fe399500776eef4d` |
| Wheel mem0/memory/main.py | `f329ca4a17af1fbefb32ac10d4cc7ae7ddbdb7435a87eb74c30915cff98b8b7c` |
| Earlier Mem0 qualification exercise inventory | `664e54459a4fc6a8768cf789b66709f7b61cce5e41bd2fc7ed0e0cfe5b48b0e4` |
| Earlier Mem0 qualification reopen inventory | `bb9952d626ab9b56d840769272968ded9d47d3a455633dfd79465978288a9f9c` |

The pinned SDK's `_add_to_vector_store` (881+) deepcopies infer=False metadata;
`_create_memory` (1975+) includes it in native payload; get (1262+), get_all
(1383+) and search (1735+) return arbitrary non-core keys as metadata. Tenant
identity keys are treated specially; experiment_event_id/source_event_id are not
stripped. The unchanged adapter normalizer copies metadata. This establishes a
source route, not a measured hostile backend treatment or authorization to write.
Complete host-known ID mappings can also change the consequence: the original
correlator unions metadata claims with the record's own mapped event. A forged
current event on a known nonauthoritative record can therefore add an unsupported
authoritative source while producing MIXED, rather than AUTHORITATIVE_ONLY.
The synthetic B1 result must not be projected onto every native caller. A future
test must preserve real host mappings and report per-record attribution; an
aggregate mixed label can conceal the difference. The prospective protocol
includes this independently identified measurement distinction.

Earlier qualification `e6ca94efb26c` raw journals contain actual same-ID update
at exercise event27 and delete at event51, with 29 exercise +10 reopen SDK
intents. Updated bytes persist and deleted records remain absent at reopen.
The independent reviewer examined original input/return journals rather than
only summaries. Same-ID update invalidates an old exact-byte association until
the host independently records a refreshed association and authority snapshot;
it does not imply an identity-substitution exploit. Native absence after delete
does not prove all derived state was forgotten.

Hindsight LC12 evidence: six units × three checkpoints, 36 query observations,
48 direct candidate instances (world, source_fact_ids=null), and 24 inventory fact
instances (valid, source_memory_ids=[]). These do not challenge unknown-state
normalization or derived mapping completeness. Historical Phase06B derived views
are useful source/lineage observations but have different custody and scope.
No Hindsight V2 native efficacy or B3 exploit claim is promoted.

## Integration and remaining trust boundary

`storage_batch.py` still invokes `_retrieval_payload` and the original scorer;
`provenance.py` still calls `_retrieval_trace`; `calibration.py` invokes the
original `normalize_authority_exposure`. Their APIs cannot be assumed to gain V2
semantics because a separate research report uses V2. The pure wrapper is opt-in.
Neither the R1 collector nor R1-AV controller is migrated or replayed.

A future caller needs a host-owned association store outside provider write
authority, trusted provider/namespace identity, independently bound current
authority snapshot and update/delete invalidation rules. Provider-supplied IDs
are usable coordinates after an observed host write response; they are not
proof of host authorship. SHA-256 provides byte continuity only. V2 currently
accepts a supplied ledger and snapshot separately; the caller must bind the
chosen authority revision to its observation. This reanalysis checks the original
host job/results against the independent ACL and records the ACL hash, but does
not implement capture-time cross-process authentication, an atomic snapshot
store, a deployed monitor or TOCTOU-safe protected dispatch.

Benign utility here means complete source-correlation retention of the actual
current native records: 32/32. It does not measure content delivery, task success,
model behavior or tool permission. There is no native challenge with missing
derived ancestry, so absence of over-quarantine in that condition is UNKNOWN.

## Disposition

Standing owner consent covered local evidence inspection, offline analysis,
focused engineering, independent review and reviewed GitHub synchronization.
No browser, network provider access, hosted inference, protected dispatch, SSH
or Jetstream action occurred. Track A remains stopped/expired with its frozen
package/grants untouched. No receipt or approval reference was generated.

Sol handled source/scientific integration and a separate Sol reviewer inspected
original evidence, pinned SDK source, the new code and interpretation. Exact
final review bindings accompany this report. No GUI workflow required Terra.

**NARROW**, rather than repeating the existing direct-record qualification.
The remaining potentially useful experiment tests exact forged event-ID metadata
and capture-time host custody. [One prospective bounded protocol](PROSPECTIVE_PROTOCOL.md)
defines the scope; it is not an execution grant or GO declaration. No live runner
or exact execution package has been qualified in this offline investigation.
Before requesting execution, freeze and independently review that small runner,
runtime/source package, fresh identity, concrete time window and cleanup plan.
Do not manufacture another platform-reference interface or reopen old attempts.
