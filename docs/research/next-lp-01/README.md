# NEXT-LP-01 — completed offline correlation study

**COMPLETE: 12 frozen synthetic records × 2 actual producer paths × 2 classifier
arms = 48 paired deterministic rows.** All rows completed without error. Genuine
independent pre-execution and final reviews accepted the exact source and result.
No native provider, hosted scientific model, protected dispatch, browser, SSH or
Jetstream operation occurred.

Public main was verified at `effda0c053bf03723b8089bc331e6b152ef9ab31` before
synchronization. The preserved Track B candidate `d3c844ad...` was published and
merged through [PR #21](https://github.com/IanJ332/Memo/pull/21), producing the
implementation starting point `a6bc55057fbb901d141a14befc2370e8f474b937`.
Original production scoring code and historical R1/R2/LC12/Track B evidence were
not edited. The new correction is an **opt-in versioned projection**, not a silent
replacement of legacy callers or a historical reclassification.

## Registered results

| Measure | Baseline, 24 rows | Correction, 24 rows |
| --- | ---: | ---: |
| Unsupported AUTHORITATIVE_ONLY | 7 | 0 |
| Exact independent-oracle agreement | 17/24 | 24/24 |
| Incomplete correlation classified UNKNOWN | 5/12 | 12/12 |
| Complete-source controls correct | 12/12 | 12/12 |
| Complete benign-current evidence retained | 10/10 | 10/10 |
| Deleted-only false authority | 0/2 | 0/2 |
| Lost complete positive resolution | 0/10 | 0/10 |
| Evaluation errors | 0 | 0 |

Producer exposure disagreement fell from one of twelve fixture pairs to zero.
The seven unsupported baseline labels are one metadata-substitution storage row,
two partial-lineage rows, two namespace-mismatch rows and two byte-mismatch rows.
The last four exercise the prospectively declared loss of scope/digest information
when projecting into the original native-ID-only maps. They are not four newly
observed native vulnerabilities. Incomplete cases have unknown authority, not a
known-negative authority label; unsupported confidence is counted separately
from false positives among the complete deleted-only controls.

The benign denominator was frozen as complete, independently supported current
evidence: five fixtures × two paths. LP01-04 has partial current support and is
excluded. Its resolved current event remains in diagnostics, but whole-source
exposure becomes UNKNOWN and its whole-observation retention indicator is false.
Thus 10/10 retention does not mean every partially evidenced record remains
resolved. Retention measures source-evidence coverage, not content delivery,
semantic truth, task completion or permission to act. Complete current plus
superseded or revoked ancestry remains MIXED exposure; deleted-only remains
nonauthoritative.

See [sealed analysis](evidence/evaluation-v1/analysis.json),
[original row inventory](evidence/evaluation-v1/inventory.json), and
[final independent review](FINAL_REVIEW_01.md). Each row retains literal normalized
record, original producer payload/trace and candidates, corrected projection,
source IDs, generic provenance, explicit completeness and supported-current IDs.

## Minimal versioned repair

`src/memlife/runner/authority_correlation_v2.py` provides `storage_payload_v2` and
`trace_payload_v2`, reusing the actual original producers and authority scorer.
A separately held host association binds provider, namespace, retrieved record
ID, exact normalized content bytes, native source ID and host event ID. Arbitrary
provider metadata cannot supply that association. Direct identity additionally
matches the ledger source digest; a derived child's bytes need not equal its
parent's bytes. Every exposed source must resolve uniquely. Missing, duplicate,
conflicting or mismatched associations remain explicitly unresolved.

Generic provider-internal causal provenance stays separate from correlation
completeness. The benign direct Mem0 generic-UNKNOWN control remains authoritative
with complete host evidence. The scorer recomputes correlation from records and
the host snapshot; it never trusts a candidate's self-asserted completeness flag.
Host ownership/custody and trusted provider scope remain caller prerequisites,
not properties proved by a Python type or self-supplied hash. No deployed
reference monitor or native backend security is established.

The two existing producer bodies, `models/authority.py`, original adapters and
RQ4 policy are unchanged. Legacy Track B probes still reproduce their historical
baseline behavior; new callers must explicitly select the v2 API. B3 Hindsight
normalization is conditional and was not folded into this study or repaired.

## Registration, custody and review

Twelve selected coverage cases replace the earlier factorial proposal before
observation, to cover the owner's expanded targets. This is not a statistical
sample. Fixture/oracle authorship is independent of the repair implementer.
The equivalent object/JSON pair is not independent replication.

A supplemental unit test exposed a pre-evaluation materialization error: the
reference adapter reports KNOWN, unlike Mem0's UNKNOWN property. All v1 artifacts
and the initial development failure are preserved. Prospective registration v2
uses a declared synthetic facade that forwards two actual pure Mem0 properties;
it never constructs a native adapter or SDK. Fixture and oracle bytes stayed
unchanged, and no registered row ran until the amendment and implementation were
independently accepted. See [registration](REGISTRATION.md),
[amendment](REGISTRATION_AMENDMENT_02.md), and [pre-execution decision](PRE_EXECUTION_SOURCE_REVIEW_02.json).

| Artifact | SHA-256 |
| --- | --- |
| Fixtures | `576c3fd12da878ef0db3c5b7f493f2880609fc2ef8719e7e658a23e6e9dfb58e` |
| Oracle | `e7bd10745fa0fc360449b6c87dc2101110de6b3ab41d38498c2ecf68b1a07f0c` |
| Registration v2 | `3217aa1c4853a9437f708a60f634c012905634d114a7634cbef927a9f6f88c46` |
| Implementation v1 | `8cdcbb12078eebcf58cc38b37a1ba645c2171abf3ba0b82a20ebb5c831319205` |
| Sealed evaluation inventory | `6441a911c4ec9b84dcca971b6482d2b3fa70d9a8977060e38d7c63f4167c14fa` |
| Final independent review | `165a5174fbe3bede0612d62657ebbfeb60e9d19b2eff335ef21a7ab6849e1de9` |

The inventory binds 48 original rows plus input custody and analysis. Public
source/evidence uses exact LF materialization; Freeze v1 keeps its existing CRLF
rule. Scientific content bindings are repository-relative for reproducibility;
they are not path-authority or live-platform approval tokens.

## Reproduce without creating another run

Use an existing repository `.venv` with pytest and the original Pydantic
requirements. No installation was performed. The original result records actual
Python/Pydantic versions in `inputs.json`.

```sh
export PY=/absolute/path/to/repository/.venv/bin/python
"$PY" -I -B scripts/research/next_lp01.py verify-registration
"$PY" -I -B scripts/research/next_lp01.py audit --out "$PWD/docs/research/next-lp-01/evidence/evaluation-v1"
"$PY" -I -B -m pytest -q -p no:cacheprovider tests/research/test_next_lp01.py tests/research/test_security_track_b_v1.py tests/research/test_security_track_b_defenses_v1.py
```

The audit checks every evidence member, source/registration/review binding, all
48 rows by read-only exact recomputation, and analysis counts. It does not create
a replacement result. `run` requires a fresh output directory and the genuine
exact pre-execution review; output reuse rejects. Do not rerun to replace evidence.
The CLI denies socket/DNS and process dispatch before importing study code.
Independent and parent focused suites passed **65 tests, zero failures/skips**:
25 supplemental correction controls plus the preserved 40 Track B probes. These
65 tests are distinct from the 48 registered rows.

## Owner consent, platform boundary and follow-on decision

The standing scoped owner consent and permanent routing policy are recorded in
the single authoritative root AGENTS.md. Sol High was used for scientific design,
security architecture and the approval-contract audit; the independent focused
review used Sol Medium. No interface workflow required a browser or GUI agent.
Ordinary authorized work was not interrupted for renewed owner permission.

[Platform contract audit](PLATFORM_CONTRACT_AUDIT.md) finds the standalone reference
string is an additional project rule, not an established receipt interface exposed
by the current tools. Actual exact-action platform review remains mandatory
where applicable. The prospective successor design places that gate at the real
tool boundary and forbids self-issued approval evidence. Live integration remains
unimplemented/unqualified; removing the frozen check alone would be unsafe.
Track A remains stopped/expired with its original package/grants and 32 unobserved
slots intact. No replacement grant/package or live attempt was created.

**Next research decision: NARROW.** Native data is unnecessary to establish these
pure-code counterexamples and the correction's deterministic fixture result.
It could answer separate questions about native metadata/lineage reachability and
availability/custody of independent host associations, which constrain deployability.
Do not launch a larger native/model campaign automatically. Any future native
study first needs exact provider/version/operations, fresh identity, store/SDK and
internal-model ceilings, resources/window/cleanup/evidence, independent review
and applicable owner/platform gates. New hosted scientific collection is not
authorized by the standing instruction. No end-to-end tool protection, model
behavior effect, native exploit, prevalence, significance or universal safety is
claimed.
