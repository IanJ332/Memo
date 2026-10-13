# Debugging Ledger

This ledger records project-specific failures and the invariant that prevents
each regression. It is not generic troubleshooting advice.

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
