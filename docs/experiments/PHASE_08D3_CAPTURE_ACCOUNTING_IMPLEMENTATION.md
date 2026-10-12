# Phase 08D-3 — Minimal Capture and Accounting Instrumentation

**Status:** local engineering implementation; no empirical execution.

**Base / branch:** `238ce6bc6e47bca6a4357144a567f400bd16b373` / `phase-08d3-capture-accounting`.
**Execution target:** local macOS worktree only. **Jetstream:** no action;
remains SHELVED. **Provider / hosted model / local embedding / downstream / RQ3
calls:** `0 / 0 / 0 / 0 / 0`.

## Result

| Area | Status | Evidence-preserving result and boundary |
| --- | --- | --- |
| D1 exact HTTP capture | IMPLEMENTED | Optional `HttpExchangeCapture` records request bytes and response bytes before decoding, including `HTTPError` bodies, with exclusive private artifact files, hashes, byte counts, timestamps, request ID and status. Capture-write failure raises and does not continue with an uncaptured response. Disabled transport behavior is unchanged. |
| D2 candidate evidence | IMPLEMENTED | Optional query sink receives every original result position, including malformed, blank, filtered, and truncated entries. It preserves decoded text-field UTF-8 bytes separately from existing stripped normalized bytes, native IDs, source IDs, surface and provenance basis. It never reconstructs response JSON. |
| D3 lifecycle completion | PARTIAL | Operation listing now paginates and rejects malformed/unknown states; explicit operation polling retains terminal receipt and actual poll timestamps. Quiescence records pre-existing operation receipts and labels overall coverage `UNKNOWN` when they exist. This is not proof of full provider background-task coverage. |
| D4 internal model accounting | BLOCKED AT VERIFIED BOUNDARY | The thread-safe `SendAccounting` primitive provides pre-send reservations, concurrent ceiling enforcement, endpoint/model identity, receipts, retries/failures through outcomes, and explicit `USAGE_MISSING`. It is not connected to Hindsight's internal startup/background/retry sends: the static audit did not establish a complete safe interception boundary. Consequently no actual-send completeness or enforceable token/cost ceiling is claimed. |
| D5 attempt/evidence gates | PARTIAL | Exclusive private attempt roots, frozen source/config hashes, immutable inventory verification, resource gate state, and fail-closed outcome precedence are implemented as reusable offline primitives. They are deliberately not a new experiment runner and do not authorize a pilot. |

## Modified code

- `src/memlife/runner/phase08d3.py`: new local-only capture, candidate,
  lifecycle-coverage, accounting, artifact-inventory, and gate primitives.
- `src/memlife/adapters/hindsight.py`: optional HTTP capture and candidate sink;
  paginated operation observations with explicit UNKNOWN coverage for pre-existing
  work. Existing paths remain disabled by default.
- `tests/unit/test_phase08d3_capture_accounting.py`: deterministic fake-only
  coverage for byte identity/Unicode/escapes, error capture, capture failure,
  filter/order parity, accounting reservation exhaustion/missing usage, evidence
  corruption, and gates.

## Offline verification

`./.venv/bin/python -m pytest tests/unit/test_phase08d3_capture_accounting.py tests/unit/test_hindsight_adapter.py tests/unit/test_hindsight_lifecycle_trace.py -q`

passed **19/19**. `compileall` over `src` also passed. The adapter tests provide
the behavioral-parity check for disabled instrumentation; the capture tests
additionally assert the existing query order and limit are unchanged.

The full offline suite was attempted: **529 passed, 1 skipped, 14 failed, 6
errors**. None is attributed to this patch. The failures/errors require absent
ignored historical `.local/review` fixtures, Linux-only `findmnt`/`/dev/sdb`
integration assumptions, or a local socket bind prohibited in this execution
environment. They are not live validation and were not repaired or bypassed.

## Remaining gates

A separately authorized operational verification must demonstrate that the
provider's startup, foreground, background, retry and failure sends all pass a
single admission point with independently defensible per-send bounds and usage
receipts. It must also demonstrate native task coverage rather than treating a
quiet list as global quiescence. Until then D3 coverage is potentially UNKNOWN,
D4 is BLOCKED, incomplete attempts cannot enter conclusive denominators, and
the four-condition pilot remains blocked.
