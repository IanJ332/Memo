# Debugging Ledger

## Q1 fixed controller readiness invariants — October 27, 2026

- Host intent must be exclusive/durable before every attempted dispatch; failed
  or ambiguous slots are spent, never retried/resumed. Original raw returns,
  malformed/partial transport bytes and errors remain beside derived results.
- Add-return ID is provisional until get confirms raw native namespace and exact
  bytes. Host oracle/snapshots are never provider-writable. Metadata/digests do
  not authenticate Host authorship. Complete baseline history mapping is retained.
- Update invalidates the old binding; get11 compares actual preserved old digest
  only when eligible, then may confirm a distinct refreshed Host revision.
- Independent development review found audit could accept a stopped attempt
  relabeled COMPLETE after resealing. Final audit reconstructs phase/count/status,
  stop, cleanup and immutable snapshots; rehashed semantic tamper tests reject it.
- Pinned SDK uses top_k10 for semantic limit10. Same-ID persistence alone is not
  byte freshness. Python -B alone permits oldpyc reads; /dev/null pycache prefix
  prevents unverified cache reads in Host and provider processes.
- [Architecture/tests](../research/next-lp-native-q1/README.md):140passed; actual
  CLI scripted18slots/audit18rows. No live scientific result or old artifact changed.

## Native direct association applicability and staleness — October 27, 2026

- Retrospective R1 join: independently registered host bytes/ACL → SDK input →
  unique add-return ID → exact raw retrieval scope/bytes. All 48 instances resolve;
  authority comes from the host snapshot, never provider metadata or similarity.
- Original evidence inventory is pinned and every consumed member rechecked.
  Retrospective analytical event IDs are not historical V2 artifacts or native
  authentication. Capture-time custody and atomic authority revision remain gaps.
- Authentic same-ID Mem0 update changes content bytes. A stable native ID does
  not keep an old exact-byte association valid; independently refresh after update.
- V2 remains opt-in. Ordinary storage batch, provenance and calibration keep
  legacy scoring; reports must not imply that these callers were migrated.
- [Evidence and six new custody controls](../research/next-lp-native-01/README.md);
  combined focused suite71passed. No original source or sealed evidence changed.

## NEXT-LP-01 versioned repair and reproducibility — October 27, 2026

- Opt-in `authority_correlation_v2` replaces provider metadata identity claims
  with independently held scope/child-byte/source-bound host associations and
  explicit unresolved coordinates. It never reads candidate metadata as proof
  of completeness. Host custody remains an external prerequisite.
- Preserve generic provider causal provenance separately: legitimate direct
  UNKNOWN with complete host identity remains authoritative. Complete current
  plus superseded/revoked sources remain MIXED exposure, not action permission.
- A pre-study unit control found ReferenceMemoryAdapter=KNOWN versus Mem0=UNKNOWN.
  Preserve v1 artifacts; v2 registration forwards actual pure Mem0 properties
  without native construction. No fixture/oracle or post-seal evaluator change.
- Frozen implementation/evidence audit uses portable repository-relative content
  bindings; these are not live platform approval tokens. Exact LF materialization
  preserves raw source/evidence identities across checkout settings.
- 48-row result: unsupported authoritative-only7→0, complete benign10/10 both;
  partial-current LP01-04 remains diagnostically supported but whole UNKNOWN.
  Four failures arise under the declared baseline scope/byte projection loss.
- [Exact source, controls and independent review](../research/next-lp-01/README.md).
  65 focused tests passed. Legacy bodies/TrackB probes remain untouched; no
  historical observations were rescored and no protected action was evaluated.

## Unrepaired Track B correlation defects — October 27, 2026

- `_correlated_event_ids` accepts matching host event IDs from provider metadata;
  the tested generic storage path can mark unrelated records KNOWN and
  AUTHORITATIVE_ONLY. Native attacker reach is not established.
- Partial exposed parent mappings are discarded. The trace retains UNKNOWN but
  the exposure scorer ignores it; storage instead labels the mapped subset
  KNOWN. A scorer-only UNKNOWN rule would miss that producer's uncertainty loss.
- Generic causal provenance and host-correlation completeness are different
  facts; a blanket KNOWN-only rule can also overblock independently attested
  direct identity. No production fix or historical reclassification was made.
- Hindsight missing/unrecognized state defaults ACTIVE in synthetic schema
  probes; honest pinned native schema reachability is unverified.
- The 40 passing research tests intentionally reproduce current behavior. They
  are not repaired-security invariants or native/model/dispatch observations.
  Existing RQ4 byte/host-authority controls held in scoped counterexamples.
- [Exact source and independent review](../research/security-track-b-v1/README.md).
  Keep the stopped R1-AV package and all sealed evidence unchanged.

## R1-AV observability, abstention and custody — October 26, 2026

- A complete no-native response need not be appropriate abstention. Only the
  registered exact unresolved-destination signal is a measured positive;
  unadjudicated prose remains UNKNOWN for appropriateness. Null-content refusals
  preserve the native endpoint without crashing. Missing grounding counts remain
  in registered UNKNOWN denominators.
- Native exposure survives a downstream token/deadline/transport stop. A full
  response can remain classifiable when transport/accounting fails and its slot
  remains SEND_UNKNOWN; report those facts separately. A consumed send with no
  receipt is attempted/ambiguous UNKNOWN, never an unattempted safe refusal.
- Audit the registered slot/capture identity, exact transport/frozen request
  bytes, receipt/raw response digests, ledger reservation/completion hashes and
  exact job roster. Matching duplicated derived views alone is insufficient.
- Scientific audit rejects explicit synthetic/test-scope capture/response flags.
  Synthetic test campaigns cannot establish native observations or permission.
- Semantic diversity requires a reviewed operation rubric; unequal prose labels
  do not establish independence. Preserve all rejected reviews and earlier
  identities. Qualified durable output uses the OS temporary directory rather
  than assuming macOS `/private/tmp` is its accepted temporary anchor.
- Protection: `tests/research/test_r1_av*.py`, final independent source reviews,
  [implementation guide](../research/r1-av/README.md). Final suite: 131 tests and
  20 subtests passed, zero failures/skips. All historical experiment bytes stay
  unchanged; no new execution is authorized.

## R1 SDK total reconciliation — October 26, 2026

- Original sealed capture journals contain 432 SDK intents and 432 matched
  returns: add 24, get 24, search 32, history 48, get_all 304. Zero SDK error
  events or unmatched intents. The original independent audit already says 432.
- The earlier REPORT/SAFE_SUMMARY and derived safe analysis hard-coded 424;
  their operation categories correctly sum to 432. No eight-call exclusion or
  alternate completed-operation denominator is supported. Preserve those earlier
  artifacts and the private Release; publish a separately dated derived erratum.
- Count one invocation per SDK intent, not input + return artifacts as two
  calls, nor lifecycle/view/identity/binding events as extra SDK calls. Repeated
  get_all captures are not evidence of retries. SDK-internal retry behavior is
  not independently inferred from this journal.
- [Reconciliation and custody identities](../research/R1_CLOSEOUT_20261026.md)
  preserve all raw observations, the original scientific analysis and audit.

## R1 inherited flavor admission — October 26, 2026

- Public resource fields alone cannot amend a hash-pinned verifier. Preserve the
  original Tier C files/pins and explicitly identify the engineered R1 derivative.
- Retained authoritative flavor metadata specifies m3.quad / 4 CPUs / 15,360 MiB;
  guest effective RAM and approximate 16 GiB descriptions are different quantities.
- Package V2 binds original/effective bridge hashes and the public amendment;
  grants and package review bind the same maps. Changed bytes reject before load.
- Preserve allocation/unshelve quota and exact server/project/user checks, all
  original volume/SSH/custody/lifecycle restrictions, and provider 2 CPU / 6 GiB /
  network-none / one-container limits. A conditional 16 SU window estimate does
  not bound total billing for an initially ACTIVE instance.
- The [amendment](../research/R1_ACCESS_AMENDMENT_20261026.md) and focused tests
  establish offline compatibility only. Original `R1EX-20261026-01` is immutable;
  genuine package, owner, actual-volume and external approvals stay separate.

## R2 exact-owner intake — 2026-10-26 UTC / October 25 local

- Genuine owner receipt is 00:55:34.210 UTC; its at-most-60-minute window ends
  01:55:34.210 UTC. Preserve the original timestamped record and attachment,
  rather than substituting a later clock reading for message receipt.
- Owner permission and exact-package review do not supply the separately
  required accepted external native-approval reference. Read-only tool success,
  inferred dispatch acceptance and self-written references are insufficient.
- Stop before the exclusive execution claim if that evidence is unavailable;
  record UNPERFORMED/UNKNOWN rather than provider failure or a consumed attempt.
  See the [pre-admission closeout](../research/R2_NATIVE_ADMISSION_STOP_20261026.md).

## R2 execution integration invariants — 2026-10-25

- Read-only recovery reports 12,536,020,992 bytes effective VM RAM; retain the
  8 GiB container ceiling and 9 GiB admission threshold. Headroom is a planning
  margin, never measured R2 consumption or free RAM.
- Freeze exact source-capsule membership, not just expected-file hashes; an
  additional module can shadow a qualified import. Mount only mapped runtime
  trees and the lock file, not unpinned sibling artifacts or owner grants.
- Recheck deadlines before create/start and bound start/inspect by the phase
  deadline, including an exited observation. Unknown create outcomes use only
  the pre-bound owned name for cleanup; never retry create.
- Pin completed seals in read-only host custody before reopen. Count SDK intents
  before delegation and cross-check them against captured native input files.
- Validate package/root/store ownership and closed-process evidence before
  preserving, sealing and deleting owned stores; retain bytes on uncertainty.
- Preserve bounded, durable Docker console bytes before removal. Failed console
  custody retains the stopped owned container and stores; a superseded review
  receipt cannot authorize an earlier development package.
- [Implementation and offline qualification](../research/R2_EXECUTION_PACKAGE.md)
  supply no owner or external approval and no native observations.

## R2 memory feasibility — 2026-10-25

- Docker reports 8,215,871,488 bytes effective VM memory; an 8 GiB container
  ceiling is 8,589,934,592 bytes. Host RAM and accepted Docker arguments cannot
  substitute for actual daemon capacity and headroom.
- Historical `OOMKilled=false` and successful exits under an 8 GiB configured
  limit do not establish a measured peak or qualify a smaller memory ceiling.
- Fail the resource-first package gate rather than silently changing the
  accepted candidate or presenting an unreviewed grant. See the
  [blocked preparation](../research/R2_EXECUTION_PREPARATION_20261025.md).

## Current direction — 2026-10-24

Active offline phase: **R0 research reconciliation**. [Roadmap v3](../research/RESEARCH_ROADMAP_V3.md), [current status](../research/RESEARCH_STATUS_20261024.md), [claims](../research/CLAIMS_REGISTER.md) and [prospective R1 protocol](../research/NEXT_EXPERIMENT_PROTOCOL.md) govern continuation. Cohort 0 is the Prompt-Specified Baseline; no new model/provider/Jetstream or protected execution is authorized. Historical scientific freezes and closed attempts remain immutable.

The dated entries below are preserved historical records, not current grants. Some historical links resolve only in the retained private evidence checkout; public archive provenance is linked from the current status.

## October 23 native A3 request binding and F04 admission invariants

- Bind only the actual sealed reopened SDK selection: count/order/ID/user scope/
  literal contents and raw return/envelope/task must agree before serialization.
- Pair must differ only in user-context `retrieved_notes`; preserve validated
  system, native send_report schema and 4,096-token Qwen configuration.
- Verify the accepted historical F04 review receipt and all reviewed source hashes
  before loading even its pure fixture validator. Capture before/after source
  hashes. Schema-valid fixtures do not confer authentic enrollment.
- Unchanged legacy CLI does not admit this A3 host basis/package path. Do not
  alias families, bypass the validator, use synthetic admission for authentic
  responses or invent lifetime ordinals from conservative liability provisions.
- Eleven offline controls and independent review are linked from the
  [readiness report](../research/native-mem0-a3-qwen/READINESS.md). No POST/evaluation.

## October 22 — matched native A3 capture

- Reusing a qualified source list must compare each current hash with the old
  expected hash before adding new pilot files. Replacing expected hashes with
  current values silently repins drift and defeats qualification reuse.
- Match the task, current-recipient policy, fresh host principal and current
  note across CONTROL/CONFLICT, while separating physical Qdrant/SQLite stores.
  Historical role labels are host fixtures, never native age/lineage assertions.
- Preserve actual search order and literal selected content. A host context
  envelope is not a model request/proposal. Without authentic generation, mark
  MODEL_NATIVE_PROPOSAL=NOT_GENERATED and authentic F04 evaluation NOT_APPLICABLE.

## October 22 — local native runtime/capture qualification

- Intel macOS resolves Torch 2.2.2 for the requested stack, but the resolved
  Transformers 5.20.2 requires Torch ≥2.6. Keep Mem0/ST pins unchanged and use
  the separately hash-locked local Linux CPU closure; never disable that check.
- A reopen gate must bind the successful exercise, archived/current source
  identities, expectation hash/size, exact four cases, native history and full
  inventory membership before constructing the client. Empty expectations or
  unindexed event files must fail closed. Preserve original exercise bytes.
- SDK candidate selection binds count, original order, UUID, literal content and
  native user_id. Namespace filtering does not establish native authentication.
- Record cleanup errors independently of operation errors. Propagate exact-owned
  Docker removal failures; store/container removal requires a separate receipt.
- Expansion tests import a separate historical `memlife` tree and auth runtime.
  Run their accepted command separately; combined discovery can select the wrong
  package. Preserve failed logs and do not modify accepted sources to mask it.

This ledger records project-specific failures and the invariant that prevents
each regression. It is not generic troubleshooting advice.

## Native qualification capture ownership and immutable callbacks

- Preserve transport intent before dispatch, including exact encoded query URL;
  normalized adapter views cannot stand in for native HTTP or SDK evidence.
- A transport exception must halt later dispatch; setting a halt flag without
  checking it on entry is insufficient. Preserve response/partial bytes where
  observed; missing response and post-mutation capture failure retain UNKNOWN.
- Candidate callbacks must check collector phase and hold its lock before the
  existing sink writes; a callback after finalization must not modify the sealed
  artifact inventory. Native journal construction requires linked adapter,
  transport/SDK, candidate sink and record identities.
- Acquire collector lock before transport lock consistently with lifecycle
  operations. Capture serialization is not provider concurrency qualification.
- Protection: `src/memlife/native_provider_capture.py`,
  `tests/research/test_native_provider_capture.py` and the independent native
  qualification review. Accepted expansion-v2 files remain byte-identical.

## Offline development v2 capture phase and response-shape guards

- Independent review found that the initial NoteStore wrapper appended before
  checking whether a model request had already been bound/reserved. It could
  mutate storage and then reject without a lifecycle receipt.
- Correction: check phase before mutation under the capture lock; persist
  lifecycle intent before the existing append; record completion separately.
  Unresolved intents block request binding. This adds instrumentation only,
  without changing the accepted NoteStore or host authorization code.
- A malformed object-valued refusal was initially treated as complete no-call.
  Require string/null content and refusal; retain original native call objects
  before validating other message metadata. Malformed/truncated data remains
  UNKNOWN and never becomes an attack failure or F04 admission.
- Protection: `tests/research/test_expansion_v2.py`, independent review receipts,
  and `src/memlife/research_collection.py`. Synthetic fixture charge records
  remain distinct from actual interrupted-campaign send evidence.

## Freeze CRLF/LF mismatch

- **Symptom:** Windows and Jetstream produced different Freeze v1 hashes.
  Expected canonical CRLF: `0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b`;
  LF Git blob: `6b41176154070dd8c58db24a5c5adfe5365e39d0c31408c033019e7d6108b3c9`.
- **Root cause:** the authoritative byte representation used CRLF while an
  ordinary Linux checkout used LF.
- **Wrong / insufficient:** `.gitattributes text eol=crlf`; a fast-forward did
  not rematerialize the unchanged file in an existing Linux worktree.
- **Correct fix:** read `git show HEAD:experiments/freeze/experiment-freeze-v1.json`,
  validate canonical JSON, materialize canonical CRLF bytes in memory, and hash
  those bytes.
- **Regression invariant:** freeze validation never depends on working-tree EOL.
- **Protection:** `scripts/validate_experiment_freeze.py`,
  `tests/unit/test_phase06_freeze.py`, commit `a570b64`.

## Provenance-repaired artifact CRLF/LF mismatch

- **Symptom:** Phase 06B-S2 attempt `20261001T205742Z-67a4ab301c67` passed the
  Windows local pre-live gate but remote Linux preflight blocked before provider
  startup with `provenance-repaired original raw SHA-256 mismatch`.
- **Root cause:** the asserted derived SHA-256
  `80b82f177adf4a15659bc583df61c78dafaa034ac931b5592e22a47d01f67a9f`
  hashes the 32-line CRLF working-tree form. The Git blob and Linux checkout use
  LF and hash to
  `84f0ac4e0b96730a0b59999573fce2c3e00b5e568bc831b6171e29544fbe2b7c`.
- **Wrong / insufficient:** validate the ordinary checkout bytes and assume
  the local pass is platform-independent; consume a second live lifecycle to
  test a repair.
- **Correct fix:** read the tracked JSONL from the Git object, validate each
  non-empty logical line as JSON without reserialization, normalize only line
  endings, materialize canonical CRLF bytes in memory, and compare one SHA.
- **Regression invariant:** provenance evidence validation must not depend on
  checkout EOL conversion.
- **Protection:** `src/memlife/runner/tracked_text.py`,
  `tests/unit/test_phase06b_s2r.py`; the blocked attempt remains immutable and
  no second lifecycle is authorized. This generalizes the earlier Freeze-v1
  repair without changing artifact content.

## Supplement lifecycle status vocabulary mismatch

- **Symptom:** the generic managed-session wrapper accepts remote status only
  as `PASS` or `PARTIAL`, while the supplement emits `SUPPLEMENT_COMPLETE`,
  `SUPPLEMENT_PARTIAL`, or `SUPPLEMENT_BLOCKED`.
- **Root cause:** the supplement-specific status vocabulary was added without
  normalization at the generic lifecycle boundary; the entrypoint test mocks
  the managed wrapper and therefore does not exercise this integration.
- **Impact:** after artifact download, even a scientifically complete future
  supplement would be labeled controller `BLOCKED`; cleanup still runs in the
  wrapper's `finally` path. The S2 attempt was already scientifically blocked,
  so this was not its experimental blocker.
- **Canonical vocabulary:** shared lifecycle evidence emits `PASS`, `PARTIAL`,
  or `BLOCKED`. Historical `SUPPLEMENT_COMPLETE`, `SUPPLEMENT_PARTIAL`, and
  `SUPPLEMENT_BLOCKED` parse as `PASS`, `PARTIAL`, and `BLOCKED`; the
  supplement-specific value remains separately preserved as
  `supplement_status` in future evidence.
- **Correct fix:** normalize at the shared managed-lifecycle boundary and emit
  only the canonical vocabulary in the future remote result `status` field.
- **Regression invariant:** provider/phase result vocabularies must be
  normalized explicitly at shared lifecycle boundaries.
- **Protection:** `src/memlife/runner/lifecycle_status.py`, integrated wrapper
  coverage in `tests/unit/test_jetstreamctl.py`, and future-result coverage in
  `tests/unit/test_phase06b_s2r.py`.

## Virtualenv identity false positive

- **Symptom:** the approved persistent harness was mistaken for the forbidden
  repository `.venv`.
- **Root cause:** both resolved Python executable paths pointed to the same
  underlying system Python.
- **Wrong / insufficient:** compare `Path(python).resolve()` values.
- **Correct fix:** validate the allowed venv root, `pyvenv.cfg`, `sys.prefix`,
  executable availability, and symlink containment.
- **Regression invariant:** virtualenv identity is not resolved interpreter
  binary identity.
- **Protection:** `scripts/jetstream/phase06b_harness.py`,
  `tests/unit/test_phase06b_remote_preparation.py`, commit `3ece8c3`.

## Artifact overwrite risk

- **Symptom:** Phase 06B initially used fixed local and remote output paths.
- **Root cause:** outputs had no controller-owned attempt scope.
- **Wrong / insufficient:** reuse a fixed path and copy the newest result over
  it; this can destroy failed-attempt evidence.
- **Correct fix:** controller-generated attempt IDs, remote
  `runs/phase06b/attempts/{attempt_id}/`, local
  `artifacts/phase06b/attempts/{attempt_id}/`, and exclusive directory/file
  creation that fails closed on collision.
- **Regression invariant:** experiment attempts are immutable.
- **Protection:** `scripts/jetstream/phase06b.py`,
  `tests/unit/test_phase06b_remote_preparation.py`, commit `a569a16`.

## Missing attempt_id in raw rows

- **Symptom:** all 32 scientifically useful Phase 06B rows lacked per-row
  `attempt_id`.
- **Root cause:** the original runner did not pass the controller attempt ID
  into each raw row.
- **Wrong / insufficient:** silently rewrite the original raw artifact.
- **Correct fix:** preserve original bytes; create a derived artifact that adds
  only the proven attempt ID; require all new rows to carry it at creation.
- **Regression invariant:** historical evidence is immutable; new raw rows have
  `attempt_id` from creation.
- **Protection:** `scripts/repair_phase06b_provenance.py`,
  `tests/unit/test_phase06b_provenance_repair.py`, commits `f122156`, `f88efd1`.

## Initial remote HEAD ambiguity

- **Symptom:** the controller first observed an older checkout, then
  synchronized the experimental commit.
- **Root cause:** initial checkout state and tested state were represented by a
  single ambiguous field.
- **Wrong / insufficient:** treat initial remote HEAD as the tested commit.
- **Correct fix:** preserve `initial_remote_head`, `synced_remote_head`, and
  `tested_commit` separately.
- **Regression invariant:** initial checkout != tested experimental commit.
- **Protection:** Phase 06B `remote-result.json`, lifecycle session, and
  `tests/unit/test_phase06b_remote_preparation.py`.

## OpenViking process crash observation

- **Symptom:** `freeze-v1__openviking__S0__r2` returned
  `RemoteDisconnected`; the next health check raised
  `ServiceExitedBeforeReady`.
- **Root cause:** **UNKNOWN**. The process exit is supported; its cause is not.
- **Wrong / insufficient:** infer OOM, provider corruption, or a harness bug
  without an exit code, service log, or kernel/memory evidence; rerun the cell.
- **Correct fix:** preserve S0 r2 as `ERROR`, stop remaining OpenViking runs,
  and design bounded observability for any future supplement.
- **Regression invariant:** never rerun or replace S0 r2.
- **Protection:** original attempt ledger and raw artifact; derived raw SHA
  `80b82f...67a9f`; supplement-plan validator.

## Hindsight shared-environment dependency conflict

- **Symptom:** Phase 04 attempt 1 was blocked before service startup by a
  protobuf dependency incompatibility; attempt 2 found the reused harness
  already contaminated.
- **Root cause:** harness and provider dependencies shared an environment.
- **Wrong / insufficient:** install Hindsight into the approved Mem0 harness.
- **Correct fix:** separate clean harness and Hindsight provider runtimes with
  pre/post `pip check` and fingerprint gates.
- **Regression invariant:** provider environment ownership is isolated from the
  benchmark harness.
- **Protection:** `scripts/jetstream/phase04_runtime.py`,
  `tests/unit/test_phase04_runtime_isolation.py`, Phase 04 manifest.

## Phase 04 created-by-run environment handoff

- **Symptom:** attempt 3 raised
  `KeyError: PHASE04_HARNESS_VENV_CREATED_BY_THIS_RUN` before service startup.
- **Root cause:** the shell script exported two required names without first
  assigning their corresponding local shell values.
- **Wrong / insufficient:** rely on implicit shell state.
- **Correct fix:** explicitly assign/export both flags and test the complete
  validator environment-key contract.
- **Regression invariant:** every validator-required environment variable is
  assigned before handoff.
- **Protection:** `scripts/jetstream/phase04_remote.sh`,
  `tests/unit/test_phase04_runtime_isolation.py`, commits `9e12050`, `841a6ad`.

## OpenViking package/readiness normalization

- **Symptom:** an installed package-name normalization mismatch blocked Phase
  05C; later a healthy response carrying `status=ok` without a `result`
  envelope was incorrectly normalized and failed strict liveness.
- **Root cause:** preflight and response parsing assumed representations more
  specific than the provider contracts.
- **Wrong / insufficient:** weaken readiness to any HTTP response or fabricate
  status.
- **Correct fix:** normalize distribution names, preserve non-envelope mappings,
  and require observed `status=ok` plus `healthy=true`; detect owned-child exit.
- **Regression invariant:** readiness is strict and evidence-preserving.
- **Protection:** `scripts/jetstream/phase05_openviking.py`, Phase 05 tests and
  `manifests/phase-05h-openviking-closure.json`.

## Resource and accounting invariants

- `/dev/sdb` is the persistent disk. Its last verified mount was
  `/media/volume/jisheng3_volume`; always resolve it live. Never `mkfs` or
  reformat it.
- `jisheng3` normally ends `SHELVED`. Create an owned temporary FIP only for an
  authorized run, delete it afterward, and never broadly delete cloud resources.
- Hindsight and OpenViking can call provider-internal `gpt-oss-120b`. These are
  not downstream RQ3 decision-model calls. Phase 06B RQ3 calls remain zero.

## Supplement plan checkout dependence (Phase 06B-S2R)

- **Symptom:** Phase 06B-S2 preflight blocked on a clean checkout because the expected phase06b-openviking-missing-runs-v1.json SHA-256 did not match path.read_bytes() due to Windows EOL materialization (CRLF vs LF).
- **Root cause:** The plan validation relied on working-tree byte hashing instead of the canonical tracked-text infrastructure.
- **Wrong / insufficient:** Change the official LF Git-blob SHA, accept multiple hashes, or rewrite the established artifact contract.
- **Correct fix:** Use materialize_tracked_text(plan_path).git_blob to read the repository-canonical source bytes regardless of working-tree line endings.
- **Regression invariant:** No tracked text artifact used as scientific/protocol identity may depend on working-tree EOL representation.
- **Protection:** src/memlife/runner/phase06b_supplement.py, scripts/validate_phase06b_supplement.py, 	ests/unit/test_phase06b_supplement_plan_eol.py.

## Supplement live original-raw path bound to repository tree

- **Symptom:** Supplement live original-raw path incorrectly bound to repository tree.
- **Root cause:** Persistent empirical artifact path and tracked repository path were conflated.
- **Wrong / insufficient:** Relying on tracked artifacts for authoritative raw persistence.
- **Correct fix:** Implement `original_persistent_raw_path()` resolving `MEMLIFE_DATA_ROOT`.
- **Regression invariant:** Live source evidence must resolve from its authoritative storage class.
- **Protection:** `scripts/jetstream/phase06b_supplement_remote.py` usage and `tests/unit/test_phase06b_supplement_path.py`.

## Supplement artifact retrieval fragility

- **Symptom:** Supplement artifact retrieval was fragile to one SSH transfer timeout.
- **Root cause:** Artifact transfer had no bounded retry, failing the entire download step on a single transient SSH timeout.
- **Wrong / insufficient:** Rerunning the whole experiment or changing scientific outcome due to network error.
- **Correct fix:** Implement bounded retry solely on the base64 SSH read command, preserving already downloaded files and failing clearly after retries.
- **Regression invariant:** Transport retry may retry evidence retrieval only, never scientific execution.
- **Protection:** `scripts/jetstream/phase06b_supplement.py` bounded retry and `tests/unit/test_phase06b_supplement_retrieval.py`.

## Candidate10 patch fixture absent from clean clones

- **Symptom:** A clean checkout fails
  `test_patch_transport_is_file_based_and_candidate_reproduces_local_bytes`
  with `FileNotFoundError` for the ignored Candidate10 patch. The development
  worktree passed only because `.local/review` was a machine-specific junction.
- **Root cause:** The controller intentionally transports a file from ignored
  `.local` storage, but the historical fixture had no repository-contained,
  offline preparation process. On Windows with global `core.autocrlf=true`, a
  fresh checkout also materialized the nine frozen sources as CRLF even though
  their Git blobs and the validator's source-byte contract are LF.
- **Separate fixture dependencies:** Several other frozen Phase08B-1 tests read
  the historical Candidate8 patch or pinned Honcho compose example. They do not
  consume the Candidate10 patch and are not Python dependency failures.
- **Correct fix:** From a checkout containing the full branch history, run the
  repository `.venv` interpreter on
  `scripts/prepare_phase08b1_candidate10_patch.py`. It reconstructs the patch
  from base `cb44f639642442b8277bc3cb2f6afb4b96d81307` and publication commit
  `54c1f7847af582cffc078fbc99aecfaab6b12dc2`, using only the nine frozen
  implementation paths and pinned Git diff settings. It writes the ignored
  fixture exclusively and refuses to overwrite different bytes. Exact
  `.gitattributes` rules materialize those nine tracked files as LF without
  changing their Git-blob bytes.
- **Regression invariant:** The prepared patch is exactly 369,953 LF bytes with
  SHA-256 `593b18eda51b8d9291b004683b875c06ebed70f4a8424f02108228bf18261ca3`.
  Never regenerate different bytes and label them as the original Candidate10
  patch.
- **Protection:** `scripts/prepare_phase08b1_candidate10_patch.py`,
  `tests/unit/test_phase08b1_candidate10_patch_fixture.py`, and isolated-clone
  execution of the named transport/reproduction test after fixture preparation.

## Phase 08B-1 remote completion separated from SSH transport

- **Symptom:** Candidate10 wrote authoritative remote completion at
  `2026-10-07T17:00:30.443178+00:00`, but the local controller remained inside
  its primary SSH subprocess until the 5,400-second timeout and therefore did
  not reach result parsing or copyback.
- **Root cause:** **UNKNOWN**. The supported failure locus is the controller's
  SSH transport after remote scientific completion; no evidence identifies an
  inherited handle, blocked remote-Python exit path, or specific SSH defect.
- **Wrong / insufficient:** convert transport `BLOCKED` into provider failure,
  infer a transport mechanism without evidence, increase the timeout as a
  substitute for diagnosis, or rerun Candidate10 to recover evidence.
- **Correct handling:** recover completion and evidence read-only, verify exact
  attempt-scoped hashes, keep scientific and controller statuses separate, and
  retry only bounded status/copy operations—never scientific execution.
- **Regression invariant:** remote scientific completion, provider decision,
  controller transport outcome, and lifecycle cleanup are independent fields.
  A transport timeout never authorizes or implies a scientific rerun.
- **Protection:**
  [`PHASE_08B1_CONTROLLER_HARDENING_RECOMMENDATIONS.md`](../infrastructure/PHASE_08B1_CONTROLLER_HARDENING_RECOMMENDATIONS.md),
  the immutable Candidate10 attempt, and the independently verified completion
  and evidence manifests.

## Hindsight completions seam is not complete runtime governance

- **Finding:** pinned 0.10.1 disables OpenAI SDK retries and native retries
  re-enter `chat.completions.create`, but Ollama native HTTP bypasses it.
  Distinct role/multi-LLM clients and separately constructed worker engines
  are outside a single owned instance. Generic failover may catch admission errors.
- **Insufficient:** wrapping one resource, using estimated prompt tokens, or
  trusting a quiet task list cannot establish complete sends or hard total bounds.
- **Invariant:** every admitted actual attempt needs its own pre-send reservation
  and durable attribution. Missing usage/failures retain capacity and close further
  admission. Unsupported workers must reject before construction; real startup
  remains BLOCKED until complete ownership and endpoint bounds are qualified.
- **Protection:** `src/memlife/runner/phase08d5.py` and
  `tests/unit/test_phase08d5_governed_sends.py`; fake-only qualification is distinct
  from real-provider readiness. No native entrypoint is qualified by this phase.

## Phase 08D-6 wrapper ownership and native-startup qualification limits

- **Finding:** an old-wrapper identity check runs only when that wrapper is
  called. A retained resource, replacement client/resource or unowned member can
  avoid it. Native batch uploads/submissions also bypass chat completions. Native
  startup catches verification failures and continues; a probe rejection cannot
  serve as a pre-construction readiness gate.
- **Evidence limit:** deterministic ownership counterexamples and 19 verified
  pinned cached sources; installed Hindsight/OpenAI/httpx/httpcore/aiohttp are
  absent in the available repository environment. Actual SDK retries, redirects
  and final routing remain unverified, not statically qualified.
- **Invariant:** no native readiness promotion from static scans, metadata,
  fake resources or probe success. Gate before constructing/importing engines;
  reject uncovered roles, members, workers, transports and batch/alternate paths.
- **Protection:** unchanged `require_hindsight_runtime_ready()`,
  `tests/unit/test_phase08d6_runtime_qualification.py`, and
  [qualification report](../experiments/PHASE_08D6_NATIVE_RUNTIME_QUALIFICATION.md).

## Phase 08D-7 SDK test environment whitelist false positive

- **Finding:** exact SDK-only installation, RECORD integrity, imports and pip
  check passed, but test preflight rejected `__CF_USER_TEXT_ENCODING`, present
  before SDK imports despite an empty-environment launch. Initial SDK calls were
  zero; no proxy, credential or network bypass was demonstrated.
- **Correction:** diagnosed names only and explicitly allowed the non-network
  encoding key. OS sandbox and Python socket/DNS guard remained unchanged.
  Subsequent full SDK-only qualification passed 30 cases; no real SDK networking.
- **Invariant:** distinguish harness false positives from actual network-policy
  failures; never silently relax socket/DNS or credential/proxy restrictions.
  SDK-only/scripted-stream results cannot promote native readiness.
- **Next:** independent review; D4 BLOCKED, D3/D5 PARTIAL.
  [Report](../experiments/PHASE_08D7_RUNTIME_DEPENDENCY_PREPARATION.md).

## Phase 08D-8 native submodule import expands through package initializers

- **Finding:** the verified providers initializer eagerly imports 13 other
  implementations. Ordinary import of OpenAI-compatible executes it; missing
  root/engine/worker initializers and helper bodies leave a 31-file source
  frontier. The SDK plus ten known helper packages is not a complete closure.
- **Invariant:** never use stub packages, extracted helpers or omitted real
  initializers to claim native import qualification. Source/dependency UNKNOWN
  cannot become optional from absence in a cache. Keep runtime BLOCKED.
- **Portability:** the D7 installer deliberately binds its ignored environment
  to its original worktree. Read-only reuse verifies the immutable plan and
  original observed artifact paths; it does not assume a new checkout owns or
  contains those artifacts. Originals and D7 loader remain unchanged.
- **Cryptography:** full distribution metadata requires its security floor;
  SDK closure does not. Native necessity is UNKNOWN until missing source is
  inspected, so no downgrade, architecture substitution or build is justified.
- **Protection:** `scripts/prepare_phase08d8_native.py`, four artifact rejection
  controls and [preparation report](../experiments/PHASE_08D8_MINIMAL_NATIVE_RUNTIME_PREPARATION.md).

### Phase 08D-8 initializer inspection expands beyond the authorized frontier

- **Verified finding:** root initializer lazily exports public classes but eagerly
  imports `_thread_limits` and calls `apply_default_thread_limits()` at module
  scope. Engine initializer itself is eager and imports MemoryEngine, embeddings,
  cross-encoder, database/search helpers. Worker initializer imports the poller.
- **Authorized stop:** three initializer downloads (7,029 bytes) completed, then
  acquisition stopped on the out-of-allowlist `_thread_limits` dependency. The
  remaining 28 approved files were not fetched. Five source-only checks confirm
  integrity and rejection before another curl/file creation.
- **Invariant:** lazy root exports do not imply lazy parent subpackages. Import
  exposure is distinct from instance initialization, and uninspected bodies
  remain UNKNOWN. A scoped acquisition authorization cannot cross a new frontier.
- **Updated gap:** 75 missing source nodes and 28 known packages, not a complete
  native environment; cryptography necessity remains UNKNOWN. No native/SDK
  import/construction/request, installation or gate relaxation occurred.
- **Protection:** `scripts/acquire_phase08d8_sources.py`,
  `scripts/inspect_phase08d8_sources.py`, source-only constraint tests and the
  [acquisition/inspection receipt](../../manifests/phase-08d8-source-inspection.json).

### Phase 08D-8 expanded inspection reaches database abstraction bodies

- **Verified behavior:** `_thread_limits` imports only os; the root-triggered
  function reads CPU/cgroup information and supplies four process environment
  defaults. Cross-encoder model/client/executor creation is deferred to methods;
  its mandatory helpers remain uninspected. No source was executed.
- **New frontier:** `engine/db/__init__.py:15–17` imports base, ops and result
  unconditionally even though database/backend instance factories are deferred.
  These three bodies lie outside the authorized 75-file set. Three new files
  (101,207 bytes) acquired, then STOP; remaining 72 approved files untouched.
- **Invariant:** deferred backend construction does not make required database
  module imports optional. Missing-body safety and crypto dependencies remain
  UNKNOWN. A frozen allowlist/group review binds exact bytes; a STOP prevents
  further curl before any new file creation.
- **Protection:** `scripts/phase08d8_expanded_sources.py`,
  `scripts/verify_phase08d8_expanded_sources.py`, six static/integrity controls and
  [expanded source receipt](../../manifests/phase-08d8-expanded-source-inspection.json).
  D4 gate unchanged; next action is independent review.

### Phase 08D-8 database abstractions close; reflect agent import expands frontier

- **Verified:** db base/ops/result imports are standard library and one another;
  base's reverse ops dependency is type-check-only. ABC/dataclass/protocol setup
  and constants do not create backends or connections; operation methods are
  deferred. Source was inspected, never executed.
- **New frontier:** reflect initializer line 10 unconditionally imports agent.py,
  reached through cached MemoryEngine's reflect import and the eager engine parent.
  It exports run_reflect_agent without calling it, but the agent body is missing
  outside the authorized remaining 75. Four new files / 56,318 bytes, then STOP.
- **Invariant:** exporting a function does not make its source module optional or
  certify import safety. A source prerequisite does not authorize reflection or
  scientific execution. Missing-body crypto/safety and complete wheel closure
  remain UNKNOWN; no partial graph becomes installation-ready.
- **Protection:** `scripts/phase08d8_remaining_sources.py`,
  `scripts/verify_phase08d8_remaining_sources.py`, six static controls and
  [immutable closure receipt](../../manifests/phase-08d8-remaining-source-closure.json).
  D4 startup gate and historical scientific evidence unchanged.

### Phase 08D-8 adaptive closure exposes ordinary import's crypto coupling

- **Resolved evidence:** adaptive source-only authorization eliminates fixed
  frontier interruptions while retaining pinned identity, append-only provenance,
  request/byte/file budgets and source-execution prohibitions. 101 files acquired,
  29 new discoveries; mandatory literal graph resolved at 125 modules.
- **Coupling:** real providers initializer eagerly imports Gemini, whose module
  unconditionally imports Google GenAI. Pinned Google Auth metadata requires
  crypto 50.0.0; ordinary-import declared package closure is 61, not SDK-only 16.
  Locked crypto has no Intel macOS wheel. This is metadata necessity, not measured
  SDK/crypto behavior. Native import/library side effects remain UNKNOWN.
- **Import effects:** real ORM/dataclass/pydantic/locks/config/logging setup;
  allocator-symbol resolution and wall-clock prompt constants. Do not equate
  syntactic graph resolution with runtime-safe startup or complete dynamic paths.
- **Decision/invariant:** B design review may propose genuine provider packaging/
  lazy export changes with native method parity, but no architecture is implemented
  and no initializer bypass, stub, upstream rewrite or gate change is approved.
- **Protection:** adaptive plan/ledger, `phase08d8_adaptive_sources.py`, metadata
  closure verifier, eight static controls and
  [immutable receipt](../../manifests/phase-08d8-adaptive-source-closure.json).
  Scientific evidence/denominators and D4 BLOCKED gate remain unchanged.

### Phase 08D-9 static derivative preserves targets but cannot qualify execution

- **Implemented:** only three reviewed initializers use PEP 562 export maps;
  128 other files, native methods, real root and helpers remain byte-identical.
  Original public maps, docstrings and exact `__all__` text are preserved.
- **Verifier correction:** original eager import order differs from `__all__`
  order. The first independent AST oracle rejected a valid initializer. Build
  its map in preserved public-list order; retain the failed development receipt,
  then create separate final receipts. Final 31 static controls pass.
- **Invariant:** static graph resolution/hash equality cannot establish runtime
  import safety, lazy-cycle behavior or B/C semantic parity. Keep original
  target exceptions and all excluded bodies unchanged; retained source does not
  authorize imports. Current projection is 29 modules/41 packages, with no eager
  engine/poller/sibling imports on that path; optional/dynamic effects UNKNOWN.
- **Provenance:** versioned engineered identity, exact patch/manifest, exclusive
  ignored trees and immutable receipts; no source-cache overwrite. LICENSE has
  pinned blob identity but absent bytes/SHA-256, never fabricated or downloaded.
- **Transport:** Git remotes and effective rewrites must be HTTPS; reject SSH
  before networking. No infrastructure/Jetstream action. D4 remains BLOCKED.
- **Protection:** `scripts/materialize_phase08d9_provider_boundary.py`,
  `scripts/verify_phase08d9_provider_boundary.py`,
  `scripts/test_phase08d9_static_derivative.py`, and
  [Stage 1 report](../experiments/PHASE_08D9_STAGE1_STATIC_PROVIDER_BOUNDARY.md).

## Phase 08D-9 Stage 2 greenlet header-relocation verifier STOP

- **Observed:** exact greenlet 3.2.4 binary wheel matches authorized size/hash,
  CRC, METADATA/WHEEL tags and all 94 hashed RECORD files, but the new preparation
  verifier rejects `.data/headers/greenlet.h` under its unsupported-relocation check.
- **Root cause:** the verifier lacks destination/ownership mapping for ordinary
  wheel `.data` headers. No artifact incompatibility/corruption was demonstrated;
  no executable `.pth` exists in this wheel. Existing pip 24.3.1 installer source
  recognizes the headers scheme, but the qualification verifier does not yet do so.
- **Initial handling:** preserve STOP and all six downloads/request/failure receipts;
  no rerun, redownload, alternate artifact, installation or native import. Five
  wheels are fully promoted. 39 deterministic controls pass, including the same
  header rejection; this does not establish installation readiness.
- **Authorized correction:** only the exact pinned greenlet header may spread
  through pinned pip 24.3.1's actual target scheme. Separate archive names,
  resolved destinations and installed RECORD-relative names; preserve byte/hash/
  size equality, containment and one-to-one exclusive ownership. All other `.data`
  schemes still reject. A separate acceptance retains historical STOP and partial;
  no redownload. 16 remaining requests complete exactly 22 / 4,390,044 bytes.
- **Qualification:** 41 isolated installed distributions; 2,677 wheel / 2,807
  installed RECORD hashes; header and global ownership/isolation/pip check PASS.
  Original 39 plus new controls: 73 passed before acquisition, final 76 passed.
  No upstream/native/SDK import or runtime readiness promotion.
- **Protection:** `scripts/prepare_phase08d9_provider_boundary.py`,
  `scripts/test_phase08d9_dependencies.py`,
  `scripts/continue_phase08d9_dependencies.py`,
  `scripts/test_phase08d9_continuation.py` and
  [Stage 2 report](../experiments/PHASE_08D9_STAGE2_DEPENDENCY_PREPARATION.md).
  D4 BLOCKED, D3/D5 PARTIAL; runtime safety UNKNOWN, parity NOT_EXECUTED.

## Phase 08D-9 nested OS sandbox rejected before venv interpreter

- **Observed:** offline creation helper nested `sandbox-exec` under the calling
  deny-network sandbox. macOS rejected `sandbox_apply` (exit 71); Python/venv/pip
  never ran, no `.venv` existed, zero distributions installed. Initial failed
  creation, identity and diagnostic receipts are preserved unchanged.
- **Correction:** observe kernel `sandbox_check` inbound/outbound policy. When
  both operations are denied, child processes inherit verified denial and no
  second apply is attempted. Otherwise launch through the explicit deny-network
  profile; unknown policy rejects before child execution. No sandbox relaxation,
  escape, dependency substitution or actual pip failure repair.
- **Evidence:** three added controls test inherited child denial, explicit profile
  selection and unavailable-policy rejection. Final 76 controls pass under OS
  denial. Completion uses separate receipts and the actual fresh environment UUID,
  distinct from the pre-interpreter attempted identity. Final pip execution and
  installed METADATA/RECORD/ownership checks pass. Independent review is next.
- **Protection:** `offline_run()` / `os_network_denial()` in
  `scripts/prepare_phase08d9_provider_boundary.py` and the continuation tooling.
  Full runtime safety UNKNOWN; D4 BLOCKED; no provider/SDK import qualification.

## Phase 08D-9 engineered bootstrap and transport claim boundaries

- **Design finding:** lazifying engine/providers/worker exports is a minimal
  candidate that can preserve provider/helper file bytes. It changes package
  import timing and creates an engineered runtime; native method identity does
  not certify ordinary-import parity or the complete MemoryEngine application.
  Real config still reaches SQLAlchemy; native success still imports tracing.
- **Transport invariant:** SDK create/HTTPX dispatch/core connection/serialized
  request start are separate units. A final-request reservation needs a bound,
  single-use pre-serialization check; an old resource-wrapper identity check
  cannot govern replacements or unowned clients. Offline OS network denial is
  the containment root. Live exclusive egress and endpoint inclusive bounds
  remain unqualified, requiring independent designs/permissions.
- **Protection proposed, not implemented:** exact three-file transformation
  allowlist, original/derivative manifests, real lazy exports, unchanged helpers,
  staged import/method/reference gates and negative controls in the
  [Phase 08D-9 design](../experiments/PHASE_08D9_PROVIDER_BOUNDARY_ARCHITECTURE.md).
  No implementation, test execution or readiness promotion occurred; D4 BLOCKED,
  D3/D5 PARTIAL. Stop for independent review before static derivative work.
