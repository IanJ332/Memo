# Reproduce R0 — scope and custody

## Public versus private inputs

This public repository publishes the new decision-only adapter, reconciliation script, focused synthetic negative controls, prospective protocol and safe derived summaries. It does not publish original model notes/proposals, machine identity, administrative grants, runtime caches or the historical deployment implementation. The private archive manifest records a single authenticated-download-verified ZIP; authorization is required to access unpublished evidence.

**A fresh public clone alone cannot authentically replay F04.** Full replay needs the preserved original authoritative checkout/campaign, independently reviewed historical source closure, exact accepted F04 source and byte-bound independent acceptance receipt. The ZIP intentionally excludes administrative/private records and is not a substitute for those gates. Do not reconstruct omitted identities or fabricate a review to make the adapter pass. Authorized researchers can inspect exact exported request/response bytes and their original-to-export mapping without privileged replay inputs.

## Focused tests

Use an existing repository `.venv` interpreter; install nothing globally or with `--user`. Both new test modules use the standard library and synthetic fixtures only. These controls do not count as authentic provider/model observations.

```sh
.venv/bin/python -I -B -m unittest discover -s tests/research -p test_reconcile_cohort0.py -v
.venv/bin/python -I -B -m unittest discover -s tests/research -p test_f04_cohort0_compat.py -v
```

The actual reviewed test environment is a separately identified repository `.venv`, Python3.12.8; no new dependency or provider runtime was installed for R0. See the byte-bound [review summary](evidence/independent-review.json). A test pass alone does not grant authentic enrollment.

## Original statistics

```sh
.venv/bin/python -I -B scripts/research/reconcile_cohort0.py \
  --root /absolute/path/to/authoritative-checkout \
  --output /new/exclusive/derived-cohort0.json
```

The root must retain the original campaign inventory and all 19,053 members, exact frozen scientific manifest and the original ZIP under its documented relative location. The script verifies hashes, sizes, membership and all ZIP indexed payload/checksum entries before aggregating per-unit server usage. It never opens a network connection. Output includes unit/case/request-hash records and aggregate statistics, not raw memory, ACL or native arguments. [Published derived result](evidence/cohort0-reconciliation.json) has SHA`926eea90762510446e79c054325ffdca271139e62e54269fd5141bef0bc6a33c`.

Wilcoxon reports normal tie-corrected approximation and an explicitly distinct exact conditional-sign calculation respecting tied ranks. Neither eliminates request/case dependence. Inspect the actual complete-pair and case-cluster tables; never infer independent causal provider trials from duplicated requests.

## Authentic decision-only F04

Contract: `COHORT0_AUTHENTIC_F04_DECISION_ONLY_V1`. The public CLI always enrolls first, requires independent byte-bound review of its full source closure and exact accepted public F04 source pins, and fails closed. No dispatcher, protected sink, inference or alternate authentication is available. Accepted legacy source is loaded into a separate module namespace; the original verifier and formal GENERATION_ID validation remain unchanged.

Required checks cover six-field custody, actual OptionB historical owner grant/source amendments, execution-to-scientific unit identity, native scope/selected-order/raw candidates, response identity/exact native arguments, observed usage/local reference accounting and durable send reservation. Historical authority checks do not reauthorize an expired generation. This fixed-cohort adapter checks static historical grant/source/identity/send-time provenance and sealed prior live-admission evidence; it does not rerun the original expired live-startup validator or prove current remote conditions. Admission is pinned to this exact inventory, not a generic future-campaign contract. Mem0's explicit internal-LLM attempt telemetry differs from Hindsight/OpenViking's unexposed attempt metric; recorded mode/calls/downstream counts and source pins are checked without inventing missing telemetry.

Run the adapter's `--help` for required original paths. First produce a `--review-request` in a new directory; an independent reviewer must inspect and issue a genuine acceptance receipt before the CLI can evaluate any unit. Supply `--root`, `--campaign`, `--accepted-source`, `--accepted-pins`, `--review`, `--unit`, and a fresh `--out`. Never reuse a receipt after changing reviewed bytes. Exact source hashes and new per-unit receipt hashes are in [F04 summary](evidence/f04-decision-summary.json). All outputs are new derived evidence; original legacy54 BLOCKED remains historical truth.

Decision replay creates a disposable synthetic policy SQLite database from the exact independent captured ACL, issues a TEST_ONLY session through the unchanged session authority, invokes only `security.authorize_tool_call`, and verifies no delivery/audit rows or database mutation. Measured latency covers the gate call, not enrollment or protected execution. Temporary policy database removal is recorded per applicable case. F04 OFF, full legacy enrollment, hardened-policy comparison, atomic dispatcher/ProvenanceBridge/TOCTOU and protected execution are not established by this result.

## Preservation and cloud backup

Never alter sealed attempts or export bytes. The [archive manifest](../../manifests/research-evidence-20261024.json) distinguishes original ZIP from any new R0 supplement. Validate remote bytes by a fresh authenticated download and SHA256, not only upload status. Source commits and repository review are separate from scientific evidence and from GitHub-required human approvals. Private archive location disclosure is not publication permission.
