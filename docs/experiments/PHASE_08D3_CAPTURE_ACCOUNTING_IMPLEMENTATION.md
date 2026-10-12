# Phase 08D-3 — Minimal Capture and Accounting Instrumentation

**Status:** local engineering implementation; no empirical execution.

**Base / branch:** `238ce6bc6e47bca6a4357144a567f400bd16b373` / `phase-08d3-capture-accounting`.
**Execution target:** local macOS worktree only. **Jetstream:** no action;
remains SHELVED. **Provider / hosted model / local embedding / downstream / RQ3
calls:** `0 / 0 / 0 / 0 / 0`.

## Result

| Area | Status | Evidence-preserving result and boundary |
| --- | --- | --- |
| D1 exact HTTP capture | IMPLEMENTED | Optional `HttpExchangeCapture` records request bytes and response bytes before decoding, including `HTTPError` bodies, with exclusive private artifact files, hashes, byte counts, timestamps, request ID and status. Only `Content-Type`, `Content-Encoding`, and `X-Request-ID` response headers enter a manifest; cookies and authorization-related headers are excluded. Capture-write failure raises and does not continue with an uncaptured response. Disabled transport behavior is unchanged. |
| D2 candidate evidence | PARTIAL | Optional query sink receives every original result position, including malformed, blank, filtered, and truncated entries. Position-aware selection preserves duplicate native-ID behavior. It retains decoded text-field UTF-8 bytes separately from existing stripped normalized bytes, native IDs, source IDs, surface and provenance basis, and never reconstructs response JSON. Sink delivery is explicitly `CALLBACK_ONLY`: durable candidate-artifact persistence is incomplete and not claimed. |
| D3 lifecycle completion | PARTIAL | Operation listing now paginates and rejects malformed/unknown states; explicit operation polling preserves terminal receipts and actual poll timestamps. Cancelled operations fail closed, and all quiescence paths report background coverage and overall coverage as `UNKNOWN`; no list observation claims complete global quiescence. |
| D4 internal model accounting | BLOCKED AT VERIFIED BOUNDARY | The thread-safe `SendAccounting` primitive separates committed usage from outstanding reservations, rejects actual usage over an admitted bound, retains missing-usage reservations, and applies the ceiling to both committed and unresolved capacity. It is not connected to Hindsight's internal startup/background/retry sends: the static audit did not establish a complete safe interception boundary. Consequently no actual-send completeness or enforceable token/cost ceiling is claimed. |
| D5 attempt/evidence gates | PARTIAL | Exclusive private attempt roots, frozen source/config hashes, immutable inventory verification, resource gate state, and fail-closed outcome precedence are implemented as reusable offline primitives. They are deliberately not a new experiment runner and do not authorize a pilot. |

## Modified code

- `src/memlife/runner/phase08d3.py`: new local-only capture, candidate,
  lifecycle-coverage, accounting, artifact-inventory, and gate primitives.
- `src/memlife/adapters/hindsight.py`: optional HTTP capture and candidate sink;
  paginated operation observations with explicit UNKNOWN coverage for pre-existing
  work. Existing paths remain disabled by default.
- `tests/unit/test_phase08d3_capture_accounting.py`: deterministic fake-only
  coverage for byte identity/Unicode/escapes, header redaction, error capture,
  capture failure, duplicate-ID/truncation parity, sequential and concurrent
  accounting overruns, cancellation/UNKNOWN quiescence, evidence corruption,
  and gates.

## Offline verification

`./.venv/bin/python -m pytest tests/unit/test_phase08d3_capture_accounting.py tests/unit/test_hindsight_adapter.py tests/unit/test_hindsight_lifecycle_trace.py -q`

passed **23/23**. `compileall` over `src` also passed. The adapter tests are a
targeted disabled-instrumentation regression check; they do not establish
baseline equivalence beyond the tested query ordering and limit behavior.

The full offline suite was attempted after these corrections: **534 passed, 1
skipped, 14 failed, 6 errors**. This is not a baseline-equivalence result. The
failing IDs and direct environmental evidence are:

- `tests/unit/test_phase07_prep.py::test_phase06b_source_artifacts_integrity`:
  the asserted historical raw file under
  `artifacts/phase06b/attempts/20261001T183940Z-1fc4c4929532/` is absent.
- The ten listed fixture failures in
  `tests/unit/test_phase08b1_honcho_live.py`—from
  `test_runtime_env_materializes_only_authorized_config` through
  `test_compose_transform_fails_closed_on_pinned_shape_drift`, excluding the
  socket test below—raise `FileNotFoundError` for ignored
  `.local/review/honcho-upstream-v3.2.1/docker-compose.yml.example`.
- `tests/unit/test_phase08b1_honcho_live.py::test_patch_transport_is_file_based_and_candidate_reproduces_local_bytes`
  and `::test_exact_candidate8_patch_applies_to_governed_cb44_base` require
  absent ignored Candidate10/Candidate8 patch fixtures.
- `tests/unit/test_phase08b1_honcho_live.py::test_existing_proxy_routes_text_hosted_and_embeddings_local`
  is denied while binding `127.0.0.1` by this sandbox (`PermissionError`).
- The six Mem0 integration errors (`test_mem0_uses_required_oss_mode_and_reusable_contract`,
  `test_mem0_native_cedar_lifecycle`, `test_mem0_restart_write_and_delete_sanity`,
  `test_mem0_runs_canonical_lifecycle_suite`,
  `test_mem0_trace_keeps_provider_internal_causality_unknown`, and
  `test_mem0_calibration_runs_three_isolated_repetitions`) fail at setup because
  macOS lacks Linux `findmnt` used to resolve `/dev/sdb`.

These classifications are based on the reproduced exception paths above, not
on an assertion that the tests passed before this change. They were not
repaired, bypassed, or used for live validation.

## Remaining gates

A separately authorized operational verification must demonstrate that the
provider's startup, foreground, background, retry and failure sends all pass a
single admission point with independently defensible per-send bounds and usage
receipts. It must also demonstrate native task coverage rather than treating a
quiet list as global quiescence. Until then D3 coverage is potentially UNKNOWN,
D4 is BLOCKED, incomplete attempts cannot enter conclusive denominators, and
the four-condition pilot remains blocked.
