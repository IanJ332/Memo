# Experiment Ledger

This is the canonical compact provenance ledger. It links to evidence rather
than copying raw logs.

## Experiment Freeze v1

- ID: `experiment-freeze-v1`
- SHA-256: `0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b`
- Definition: [`experiment-freeze-v1.json`](../../experiments/freeze/experiment-freeze-v1.json)
- Protocol: [`EXPERIMENT_FREEZE_V1.md`](../experiments/EXPERIMENT_FREEZE_V1.md)
- Matrix: S0–S5, 14 supported and 4 unsupported cells.
- Repetitions: exactly 3 per supported provider/scenario cell; 42 planned.

| Provider | Version | Configuration SHA-256 |
| --- | --- | --- |
| Mem0 | 2.2.1 | `23c068e16db7d4bb90aad7755b997d5a4104c433a4a0083ef43b3506680ff2e8` |
| Hindsight | 0.10.1 | `baca300bdce174d8cb2d00fa576df73d0cf5c4f9230aed370d2767bd35f4d73d` |
| OpenViking | 0.4.22 | `ad1216520de78aa6dd6fe0c34393e3830b05b035aa7dda367d92725dafe53258` |

Do not upgrade these during frozen execution.

## Phase 06B original attempt

- Attempt ID: `20261001T183940Z-1fc4c4929532`
- Tested commit: `a569a166093c626c5a99a7a33042e0aa7ddb7e74`
- Planned/executed/success/error/never executed: **42 / 32 / 31 / 1 / 10**.
- Provider coverage: Mem0 12/12; Hindsight 18/18; OpenViking 2/12.
- Original raw SHA-256: `fe6f8cca390fa30b714e7635b9e7e56b987bd8303611f625c3258e90eaea2ef4`.
- Derived provenance-repaired raw SHA-256: `80b82f177adf4a15659bc583df61c78dafaa034ac931b5592e22a47d01f67a9f`.
- Repair: added only `attempt_id=20261001T183940Z-1fc4c4929532` to each
  of 32 rows.
- RQ3 calls: **0**.

The original attempt directory and raw bytes are immutable. The tracked derived
artifact is [`freeze-v1-raw-runs.provenance-repaired.jsonl`](../../artifacts/phase06b/derived/20261001T183940Z-1fc4c4929532/freeze-v1-raw-runs.provenance-repaired.jsonl).

### Frozen error and residuals

`freeze-v1__openviking__S0__r2` is an executed `ERROR`, not an unexecuted
slot. It recorded `RemoteDisconnected: Remote end closed connection without
response`; the following health check observed `ServiceExitedBeforeReady`.
Never rerun, replace, or relabel it.

Residual cells: Mem0 S1, Hindsight S1, and Hindsight S4.

## Exact never-executed set

Only these IDs may appear in a later supplement:

1. `freeze-v1__openviking__S0__r3`
2. `freeze-v1__openviking__S2__r1`
3. `freeze-v1__openviking__S2__r2`
4. `freeze-v1__openviking__S2__r3`
5. `freeze-v1__openviking__S3__r1`
6. `freeze-v1__openviking__S3__r2`
7. `freeze-v1__openviking__S3__r3`
8. `freeze-v1__openviking__S4__r1`
9. `freeze-v1__openviking__S4__r2`
10. `freeze-v1__openviking__S4__r3`

Forbidden: every Mem0 and Hindsight run, OpenViking S0 r1/r2, any r4, and any
replacement. See the [supplement protocol](../experiments/PHASE_06B_OPENVIKING_SUPPLEMENT_PROTOCOL.md).

## Phase 06B-S1 implementation (local only)

- Dedicated supplement selection/execution path: implemented and locally
  validated; it accepts no caller-supplied run IDs.
- Supplement plan SHA-256:
  `2db182047dd2b1bfddcaddaad40ace58385f8bdcf0bb114354d9724ee5d6626a`.
- Change classification: `OBSERVABILITY_ONLY`; frozen payloads, provider
  configuration, models, timeouts, lifecycle semantics, and repetitions are
  unchanged.
- Attempt isolation: future remote and local artifacts use
  `phase06b/supplements/attempts/{attempt_id}` with exclusive creation.
- Live supplement observations executed: **0**. RQ3 calls: **0**.
- Jetstream remained `SHELVED`; live execution remains unauthorized.

## Phase 06B-S2 blocked supplement attempt

- Attempt ID: `20261001T205742Z-67a4ab301c67`.
- Tested commit: `2224704e9bc8223a686a18c91e0eb879cb0a54d7`.
- Status: **SUPPLEMENT_BLOCKED**; planned/executed/success/error/not executed:
  **10 / 0 / 0 / 0 / 10**.
- Blocker: remote preflight read the provenance-repaired artifact from the
  Linux checkout as LF bytes (SHA-256
  `84f0ac4e0b96730a0b59999573fce2c3e00b5e568bc831b6171e29544fbe2b7c`),
  while the asserted SHA-256
  `80b82f177adf4a15659bc583df61c78dafaa034ac931b5592e22a47d01f67a9f`
  is the Windows CRLF working-tree form. CRLF materialization of the Git blob
  reproduces the asserted SHA exactly.
- Provider service: **not started**. Supplement raw rows: **0**. RQ3 calls and
  downstream decision calls: **0**.
- Lifecycle: exactly one; run-owned floating IP deleted; final VM independently
  verified `SHELVED` with no external address; no retry attempted.
- Original coverage remains **42 / 32 / 31 / 1 / 10** and OpenViking S0 r2
  remains the frozen `ERROR`.
- Evidence: [supplement result](../../artifacts/phase06b/supplements/attempts/20261001T205742Z-67a4ab301c67/supplement-result.json)
  and [manifest](../../manifests/phase-06b-s2-openviking-supplement.json).

## Combined analysis rule

Canonical source artifacts remain unchanged. Any combined view is derived and
must retain `attempt_id` plus `execution_origin` (`ORIGINAL` or `SUPPLEMENT`)
per row. Do not add `execution_origin` by rewriting canonical originals. There
is no majority voting and no replacement of errors.

## Phase 06B-S2R local repair and derived closure

- Status: **PASS locally; publication pending**. No Jetstream/provider/RQ3
  action occurred and no supplement observation was executed.
- The provenance-repaired tracked JSONL is now read from the Git object,
  JSONL-validated without reserialization, and materialized as canonical CRLF
  bytes in memory. Its sole identity remains
  `80b82f177adf4a15659bc583df61c78dafaa034ac931b5592e22a47d01f67a9f`;
  the LF blob SHA is diagnostic only, not an accepted alternative identity.
- The immutable S2 attempt directory was not changed. Derived operational
  closure under
  `artifacts/phase06b/supplements/derived/20261001T205742Z-67a4ab301c67/`
  records 0 executed, 10 `BLOCKED_NOT_EXECUTED`, and marks missing disk and
  harness-prefix samples `NOT_SERIALIZED` rather than reconstructing them.
- Future attempts snapshot the plan and serialize its SHA/authorized IDs,
  exact selected harness path and `sys.prefix`, root/volume free bytes,
  per-run or blocked statuses, and canonical lifecycle status before provider
  work can proceed.
- Lifecycle status is canonically `PASS|PARTIAL|BLOCKED`; historical
  `SUPPLEMENT_*` values remain backward-compatible aliases.

## Phase 06B-S OpenViking missing-run supplement attempt

- Attempt ID: `20261002T000350Z-c272b34d2cc3`.
- Tested commit: `58e154a62e1c52e6a478e8f0e2041b437023582a`.
- Status: **PASS**; planned/executed/success/error/not executed:
  **10 / 10 / 10 / 0 / 0**.
- Provider service: **started successfully**. Supplement raw rows: **10**. RQ3 calls and
  downstream decision calls: **0**.
- Lifecycle: exactly one; run-owned floating IP deleted; final VM independently
  verified `SHELVED` with no external address; no retry attempted.
- Original coverage plus supplement coverage combined is **42 / 42 / 41 / 1 / 0** and OpenViking S0 r2
  remains the frozen `ERROR`.
- Evidence: `artifacts/phase06b/supplements/attempts/20261002T000350Z-c272b34d2cc3/supplement-result.json`.

## Phase 06B Closeout — Final Storage-Batch Inventory

- Phase 06B frozen storage batch: **COMPLETE**.
- Coverage: **42 / 42** (planned 42, executed 42, success 41, error 1, never executed 0).
- Historical ERROR: **OpenViking S0 r2** (`RemoteDisconnected`, then `ServiceExitedBeforeReady`; preserved without rerun).
- Jetstream: **SHELVED** (no active VM or external address).
- RQ3: **not yet executed** (0 downstream decision model calls).
- Next scientific step: **residual-only root-cause analysis / RQ3 eligibility review**.

## Phase 08B-1 Candidate10 Honcho acceptance

- Attempt ID: `20261007T165110Z-19d0ccd6b106`.
- Experiment base commit: `cb44f639642442b8277bc3cb2f6afb4b96d81307`.
- Provider: Honcho 3.2.1 at commit
  `79cb31645f4efdef626d1bd9316a648adb5da89b`, Git tree
  `80e5aaa7104b3566aa88d55954340c4593cf9cd7`.
- Scientific status: **COMPLETE**. Frozen provider decision: **NO_GO**.
- Capability classifications: **10 SUPPORTED / 4 UNSUPPORTED / 4 UNKNOWN**.
- Scenarios: S0 directly executed and `SUPPORTED`; S1 `UNKNOWN`; S2-S5
  capability-derived `UNSUPPORTED` and not directly executed.
- Quiescence: normal deriver `SUPPORTED`; native Dream `UNKNOWN` under the
  frozen new-work-then-stable-empty criterion.
- Model accounting: 21 provider-internal calls (12 hosted text-generation,
  9 local embedding); downstream calls **0**; RQ3 calls **0**.
- Required completion evidence: **23 / 23** present with exact SHA-256 and
  byte-count matches. Authoritative completion SHA-256:
  `ca636f62ec87bfad5aa3e456a3584ed65f48bdb585d4747afce34bcbe1700f23`.
- Indexed primary evidence: **95 / 95** paths present and SHA-256 verified;
  all 88 recorded byte expectations match. See the
  [verification manifest](../../manifests/phase-08b1-candidate10-evidence-verification.json)
  and [provenance/gaps report](../experiments/PHASE_08B1_EVIDENCE_PROVENANCE_AND_GAPS.md).
- Accepted review bundle SHA-256:
  `43e63ce4632735ba30582a649a942f9dd98a31e33b241045c01d906120a4d5d9`.
- Raw appendix identity: SHA-256
  `3eae5e4c07552c562aaff56bd5f1de2eb5ca61648d6a99d29ff2ac159d6b91df`,
  60,291 bytes. It remains preserved locally and is **not published** in the
  repository; see the [appendix reference](../experiments/PHASE_08B1_PRIMARY_RAW_EVIDENCE_APPENDIX.md).
- Controller outcome: remote scientific completion preceded a local primary
  SSH timeout. The transport root cause remains `UNKNOWN`; the operational
  `BLOCKED` controller record does not negate or explain the frozen scientific
  `NO_GO` result.
- Lifecycle: exactly one authorized Candidate10 execution; instance returned
  to `SHELVED`; owned floating IP removed. Candidate10 must not be rerun or
  replaced.
- Interpretation: no security exploit was demonstrated. Freeze v1 is unchanged;
  Freeze v2 remains a non-final draft.
- Scientific record: [closeout](../experiments/PHASE_08B1_HONCHO_SCIENTIFIC_CLOSEOUT.md).
- Git publication: the original scientific closeout commit on
  `phase-08b1-candidate10-publication` is
  `54c1f7847af582cffc078fbc99aecfaab6b12dc2`. The latest published portability
  closure is `3c126216f4f5b7ac4f842e344598324c8d6a4097`; merge to `main` remains
  pending. The raw evidence ZIP remains local and unpublished.

## Phase 08C-1 minimal deterministic RQ4 mediator pilot

- Base main: `43b50ae437e5dfb7f56b20a06509ac2bb0a49094`.
- Execution class: offline deterministic policy evaluation only.
- Evidence inventory: 2 eligible and 2 ineligible empirical controls; 9
  LongMemEval-derived `SYNTHETIC_RQ4_CHALLENGE` cases; 8 hand-authored
  `SYNTHETIC_RQ4_CHALLENGE` cases.
- Eligible outcomes: 19 total; 8 `ALLOW`, 7 `DENY`, 4 `QUARANTINE`; 0 incorrect
  ALLOW; 0 incorrect DENY; 0/11 non-ALLOW candidate byte strings in serialized
  context.
- Empirical exclusions: Hindsight S4 and OpenViking S4 are
  `NOT_ELIGIBLE_FOR_EMPIRICAL_MEDIATION` because exact final candidate bytes
  were not preserved. No evidence was reconstructed.
- LongMemEval source: `longmemeval_oracle.json` at dataset revision
  `98d7416c24c778c2fee6e6f3006e7a073259d48f`, SHA-256
  `821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c`;
  source file retained outside Git; derived cases are not provider evidence.
- Jetstream/provider/hosted-model/downstream-model/RQ3 calls: **0 / 0 / 0 / 0 / 0**.
- Freeze v1, the original Freeze-v2 draft, all historical attempts, and frozen
  evidence remain unchanged.
- Scientific record: [pilot report](../experiments/PHASE_08C1_RQ4_MINIMAL_PILOT.md).

## Phase 08D-5 offline engineering qualification (no empirical attempt)

- Base: `de011d8bde32ffda76512c87dee550f0baf688d5`; review branch:
  `phase-08d5-governed-sends`.
- Owned deterministic fake completions admission/accounting tested; 143 focused
  tests pass. No provider, hosted model, ONNX embedding, downstream or RQ3 calls.
- Real runtime governance and pilot readiness remain **BLOCKED**; startup rejects
  pending complete interception, process ownership and endpoint-enforced bounds.
- Tests are engineering evidence only, never new empirical rows or denominators.
  Frozen evidence and prior attempts remain unchanged; Jetstream remains SHELVED.
- Engineering report: [Phase 08D-5](../experiments/PHASE_08D5_GOVERNED_SEND_INSTRUMENTATION.md).

## Phase 08D-6 offline native-boundary qualification (no empirical attempt)

- Base: `58ab52dcd8e628400533173eac08ed5b1ea42faa`; review branch:
  `phase-08d6-runtime-qualification`.
- 19 cached pinned Hindsight source files verified; client/worker/alternate/batch
  paths traced. Missing local Hindsight and SDK/HTTP dependencies prevent
  installed-runtime interception proof. Actual SDK transport probes: **0**.
- Focused deterministic qualification/regressions: **161 passed**. Ownership
  counterexamples are engineering tests, not native-runtime or provider evidence.
- D4/pilot **BLOCKED**; D3/D5 **PARTIAL**; runtime startup gate unchanged.
- Provider/hosted-model/embedding/downstream/RQ3/SSH/Jetstream calls: **0**.
  D1/D2 evidence, Freeze v1, attempts and denominators remain unchanged.
- Engineering report: [Phase 08D-6](../experiments/PHASE_08D6_NATIVE_RUNTIME_QUALIFICATION.md).

## Phase 08D-7 dependency preparation (no empirical attempt)

- Base: `d29742e9a59575d63f54c50e10205208654240c1`; review branch:
  `phase-08d7-runtime-dependencies`.
- Pinned upstream dependency metadata and local caches/environments inventoried
  read-only. Proposed runtime closure: 33/184 matching local wheels; SDK subset
  9/16 ready. Separate acquisition/installation authorization remains required.
- No package installation, SDK/native transport test, provider/model/embedding/
  downstream/RQ3 execution, SSH or Jetstream action. No empirical row or new
  denominator. D1/D2 evidence, runtime BLOCKED gate and frozen attempts unchanged.
- Engineering report: [Phase 08D-7](../experiments/PHASE_08D7_RUNTIME_DEPENDENCY_PREPARATION.md).

### Phase 08D-7 SDK-only authorized installation continuation

- Start: `310a94c43bb47ae08423fe629d10845adeec3b1a`, clean same review branch.
- Exact allowlist: seven TLS-verified downloads and nine immutable cache copies;
  16 pinned distributions installed offline. Metadata/versions, wheel/installed
  RECORDs, imports and pip check passed. No Hindsight or additional package.
- Initial preflight false positive on macOS encoding metadata corrected; OS/
  Python network guards unchanged. **30 SDK-only offline cases PASS**, with
  **33 SDK invocations / 43 HTTPX requests**, zero real SDK socket/DNS attempts.
  Scripted HTTPCore/TLS are not live physical sends. D4 BLOCKED, D3/D5 PARTIAL.
- Provider/model/embedding/downstream/RQ3/SSH/Jetstream actions: zero. No new
  empirical row, denominator or scientific evidence; D1/D2 and freezes unchanged.
- [Installation/qualification receipt](../../manifests/phase-08d7-sdk-installation-qualification.json).

## Phase 08D-8 minimal native runtime preparation (no empirical attempt)

- Base `e07de9832572a910e7055d2df582b919146c35fd`; review branch
  `phase-08d8-native-runtime-preparation` in the assigned local worktree.
- Existing 16 SDK distributions/imports, 1,412 wheel and 1,464 installed RECORD
  hashes, 20 source identities and upstream metadata reverified offline.
  Four real-artifact rejection controls pass; originals unchanged.
- Normal native import has 31 missing source files in the known frontier;
  complete source/dependency closure and native cryptography necessity UNKNOWN.
  Ten known helper dependencies include one reusable local wheel and nine gaps.
- No acquisition, installation, build, native import/construction/method call,
  provider/model/embedding/downstream/RQ3/SSH/Jetstream action or empirical row.
  D1/D2/freezes and scientific denominators unchanged. D4 BLOCKED, D3/D5 PARTIAL.
- [Preparation report](../experiments/PHASE_08D8_MINIMAL_NATIVE_RUNTIME_PREPARATION.md)
  and [artifact receipt](../../manifests/phase-08d8-native-preparation.json).
  Independent review next; bounded source-only acquisition separately authorized.
