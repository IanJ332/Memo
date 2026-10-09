# Phase 08C-1 — Minimal Deterministic RQ4 Mediator Pilot

## Status and scope

**Status:** PASS, OFFLINE PILOT; ready for scientific review.

**Base main:** `43b50ae437e5dfb7f56b20a06509ac2bb0a49094`.

**Policy:** `rq4-minimal-exact-v1`.

**Evaluation time:** `2026-10-08T18:00:00Z`.

**Execution:** local only. Jetstream, providers, hosted models, downstream
models, embeddings, and RQ3 were not executed.

This pilot tests a narrow claim: a deterministic, provenance-aware boundary
can exclude candidate bytes that lack exact current authority while retaining
exact current propositions, including propositions with superseded ancestry.
It does not test model behavior, prompt-injection resistance, or real-world LLM
defense efficacy.

## Reuse and implementation audit

Direct reuse:

- `CandidateEnvelope`, `AuthoritySnapshot`, `AuthorityDecision`, evidence
  classes, lifecycle states, and relation edges from the Phase 08A contracts.
- Existing canonical contract hashing and SHA-256 content identity patterns.
- Existing strict Pydantic base contracts and project pytest environment.
- Immutable Phase 06B and Phase 07 evidence.

Original implementation is limited to
`src/memlife/runner/rq4_policy.py`. It adds one versioned authority bundle,
exact deterministic decision logic, two deliberately weak baselines, and an
allow-only length-framed byte serialization. It performs no text extraction,
semantic similarity, embedding, keyword authorization, or model call. No
existing or frozen model contract changed. No dependency was added.

## Decision and serialization contract

The policy requires candidate raw bytes to match `raw_bytes_sha256`; exact
logical-fact and canonical-proposition identities; resolved, explicit lineage
edges; and an independent authority artifact identity.

- `ALLOW`: an exact proposition/version match has current `ACTIVE`
  authoritative evidence. Resolved stale ancestors do not override that exact
  current match.
- `DENY`: the exact proposition/version match is independently established as
  superseded, revoked, deleted, or expired.
- `QUARANTINE`: bytes, identity, lineage, source binding, or authority evidence
  is missing, ambiguous, contradictory, or has no exact match.

Only `ALLOW` bytes enter `MEMLIFE-RQ4-CONTEXT-V1` frames. `DENY` and
`QUARANTINE` decisions remain in separate audit output. An indivisible
mixed-authority aggregate has no exact aggregate authority record and is
quarantined in full.

## Empirical controls

The four requested Phase 06B/07 cells were investigated. Two are eligible and
two remain explicitly ineligible.

| Control | Eligibility | Result | Evidence and limitation |
| --- | --- | --- | --- |
| Mem0 S1 r1 | Eligible | `ALLOW` | Current v2 candidate bytes and authority source record are exact; lineage contains both `write-v1` and `update-v2`. |
| Hindsight S1 r1 derived | Eligible | `ALLOW` | Read-only recovery attempt `20261003T003809Z-7a3425bf2f4c` established exact current-v2 bytes while lineage retains superseded v1. |
| Hindsight S4 | `NOT_ELIGIBLE_FOR_EMPIRICAL_MEDIATION` | Not evaluated | Immutable rows retain final hashes and write-support attribution, but not exact final candidate bytes. |
| OpenViking S4 | `NOT_ELIGIBLE_FOR_EMPIRICAL_MEDIATION` | Not evaluated | Repetitions disagree on derived-state production; immutable rows retain final hashes but not exact final candidate bytes. |

Eligible / ineligible empirical controls: **2 / 2**. Eligible decision counts:
**2 ALLOW / 0 DENY / 0 QUARANTINE**. Quarantine rate: **0/2 (0%)**.
Incorrect ALLOW / incorrect DENY: **0 / 0**.

The manifest binds the original attempt and run IDs and hashes the canonical
tracked artifacts. No missing candidate bytes or authority snapshots were
invented for S4.

## LongMemEval-derived challenges

Source checks passed for the public cleaned LongMemEval oracle artifact:

- Dataset: `xiaowu0162/longmemeval-cleaned`.
- Revision: `98d7416c24c778c2fee6e6f3006e7a073259d48f`.
- File: `longmemeval_oracle.json` (kept outside the tracked repository).
- SHA-256: `821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c`.
- License: MIT; the upstream notice is retained in
  `experiments/rq4/pilot/LONGMEMEVAL_LICENSE.txt`.

Four manually audited knowledge-update histories contribute exact stale and
current candidates: `01493427`, `0e4e4c46`, `0f05491a`, and `18bc8abd`. The
manifest preserves original question IDs, answer-bearing source session IDs,
dates, source-record hashes, and deterministic fixture proposition identities.
One related abstention history, `031748ae_abs`, is quarantined because its
history does not establish the requested Software Engineer Manager fact.

Every adapted case is `SYNTHETIC_RQ4_CHALLENGE`, never
`PROVIDER_OBSERVED`. Counts: **9 cases; 4 ALLOW / 4 DENY / 1 QUARANTINE**.
Quarantine rate: **1/9 (11.1%)**. Incorrect ALLOW / incorrect DENY:
**0 / 0**.

These cases test the policy on source-grounded transitions; they do not
measure LongMemEval question-answering accuracy and are not provider evidence.

## Hand-authored synthetic controls

Eight cases cover exact current authority, exact stale version, revoked
source, deleted source, missing proposition identity, contradictory authority,
current content with superseded ancestry, and an indivisible mixed-authority
aggregate.

Counts: **8 cases; 2 ALLOW / 3 DENY / 3 QUARANTINE**. Quarantine rate:
**3/8 (37.5%)**. Incorrect ALLOW / incorrect DENY: **0 / 0**.

The current-with-superseded-ancestry case is allowed. The naive ancestry-only
baseline denies it, demonstrating the intended false-positive control.

## Aggregate results and baselines

| Evidence class | Eligible cases | ALLOW | DENY | QUARANTINE | Incorrect ALLOW | Incorrect DENY | Quarantine rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Empirical provider-observed | 2 | 2 | 0 | 0 | 0 | 0 | 0/2 (0%) |
| Benchmark-derived synthetic | 9 | 4 | 4 | 1 | 0 | 0 | 1/9 (11.1%) |
| Hand-authored synthetic | 8 | 2 | 3 | 3 | 0 | 0 | 3/8 (37.5%) |
| Total | 19 | 8 | 7 | 4 | 0 | 0 | 4/19 (21.1%) |

Baseline errors use the identical fixture inputs and count an ALLOW or DENY as
incorrect whenever it disagrees with the independently supported expected
outcome, including cases whose supported outcome is fail-closed quarantine.

| Policy | Empirical IA / ID | Benchmark IA / ID | Synthetic IA / ID | Total IA / ID | Principal limitation |
| --- | ---: | ---: | ---: | ---: | --- |
| Exact RQ4 pilot | 0 / 0 | 0 / 0 | 0 / 0 | **0 / 0** | Requires pre-established exact identity and independent authority evidence. |
| Pass-through retrieval | 0 / 0 | 5 / 0 | 6 / 0 | **11 / 0** | Treats retrieval as authorization. |
| Naive ancestry-only | 0 / 2 | 0 / 0 | 1 / 3 | **1 / 5** | Over-denies current content with stale ancestry and cannot reason about proposition identity. |

## Leakage, replay, provenance, and witness checks

- Byte-level unauthorized-context leakage: **0/11 non-ALLOW candidate byte
  strings present** in delivered context. Only the 8 ALLOW candidates were
  framed, and each recovered byte-for-byte from the frame.
- Deterministic replay: **PASS**. Repeated identical inputs produced identical
  decisions, input hashes, authority hashes, audit output, and serialized
  context bytes.
- Fixture hash validation: **PASS** for all four tracked empirical source
  artifacts using checkout-independent canonical tracked-text materialization;
  the external dataset file was pinned by revision and SHA-256.
- Evidence-class validation: **PASS**. The two empirical candidates are
  `PROVIDER_OBSERVED`; all 17 benchmark-derived or hand-authored cases are
  `SYNTHETIC_RQ4_CHALLENGE`.
- Witness completeness: **15/15 conclusive decisions** contain the applicable
  exact current or invalidated authority witness. All four quarantines contain
  explicit fail-closed reason codes. The one abstention case intentionally has
  no proposition or lineage witness because the source history does not
  establish the target fact.

## Scientific limitations

The pilot uses exact fixture-defined proposition identities; it does not solve
open-world proposition extraction or semantic equivalence. Authority bundle
independence is enforced by artifact identity and evidence provenance, not by
a trusted online authority service. The benchmark subset is small and manually
audited. Two requested empirical S4 controls are excluded because the required
candidate bytes were never preserved. Binary framing demonstrates byte
exclusion but is not a production prompt format. No downstream model saw the
output, so no claim about model decisions, task utility, prompt injection, or
real-world defense efficacy follows.

## Validation

- Focused RQ4 policy suite: **13 passed**.
- Full repository suite with existing local-only model/review/source fixtures
  visible: **533 passed, 1 skipped, 1 failed**. The sole failure is the
  pre-existing checkout-dependent assertion in
  `test_phase06b_source_artifacts_integrity`: on Windows it hashes the tracked
  supplement working-tree CRLF bytes (`331782...e8d69`) while asserting the LF
  Git-blob hash (`435fd4...46ea4`). The immutable artifact was not rewritten.
- Full suite with that one known checkout-EOL assertion deselected:
  **533 passed, 1 skipped, 1 deselected**.
- Freeze v1 validator: **PASS**, canonical SHA-256
  `0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b`.
- Phase 08A draft validator: **PASS**.
- Python compile validation and `git diff --check`: **PASS**.
- Publication audit: the 15.4 MB source dataset remains outside Git; no raw
  provider evidence, runtime cache, local review input, credential, token, or
  secret is added.

## Invariants and execution accounting

- Freeze v1 and its SHA-256 are unchanged.
- The original Freeze-v2 draft is unchanged.
- Historical attempts, raw evidence, and the frozen OpenViking S0 r2 `ERROR`
  observation are unchanged.
- Candidate10 was not rerun. Honcho `NO_GO` is unchanged.
- Jetstream used: **NO**.
- Provider calls: **0**.
- Hosted model calls: **0**.
- Downstream model calls: **0**.
- RQ3 calls: **0**.
- New dependencies: **none**.

This offline pilot is ready for main ChatGPT scientific review. It does not
authorize a broader evaluation, revised freeze, provider phase, Jetstream
lifecycle, or model execution.
