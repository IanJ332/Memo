# Phase 08D-7 — SDK Dependency Installation and Qualification

**SDK-only installation VERIFIED; 30 deterministic offline qualification cases
PASS. Native D4 remains BLOCKED and D3/D5 PARTIAL. Stop for independent review.**

CONVERSATION: Phase 08D-7 SDK-only acquisition and qualification. MODEL: GPT-6
Codex runtime; no independent model-variant receipt. EXECUTION TARGET: assigned
local worktree `/Users/ian/.codex/worktrees/2373/Memo`. JETSTREAM ACTION: none;
remains SHELVED without querying infrastructure. Date: 2026-10-12,
America/Chicago.

## Scope and preserved preparation evidence

The original phase base is `d29742e9a59575d63f54c50e10205208654240c1`.
This continuation started at `310a94c43bb47ae08423fe629d10845adeec3b1a`, with
review branch `phase-08d7-runtime-dependencies` verified and worktree clean.
The prior report is preserved in that commit. AGENTS and project handoffs were
read; scientific evidence, requirements, runtime gates and provider code are
unchanged.

The initial [inventory receipt](../../manifests/phase-08d7-dependency-preparation.json)
records 75 local site directories, repository/framework/bundled/Conda runtimes,
pip/Conda caches, 887 pip body/wheel files, 279 wheel archives and 11 source
archives. Existing runtimes/caches were inspected without modification.
Initial artifact readiness was 33/184 runtime wheels and 9/16 SDK wheels.
This is historical preparation readiness, not a new runtime inventory.

The proposed qualification resolution comes from Hindsight source commit
`f8950b0c07d9e34c76493dba802bb309f0ce60fd`, with verified metadata identities:

| Metadata | Git blob SHA-1 | SHA-256 |
| --- | --- | --- |
| Provider pyproject | `e656821ca96c76b84a1d1cb1c7eb592f7f3b2563` | `4e73d3aae4711cb95639a2b3cfbe93ccf3a411b2ab3d4ad8924b7abc279930ec` |
| Workspace lock | `cd9687ebaa9a749e506ed396fc95c6f48925072a` | `c2df90ff2364b524453662e880d872edbe6307b3bddea4dea8604c7a8455cb5c` |

Target: CPython 3.12.8, Intel macOS 15.7.4. This resolution is not a
reconstruction or amendment of the historical provider runtime. Phase 04's
OpenAI 3.20.0 fingerprint entry belongs to its harness; infrastructure's 3.13.0
pin is also separate. Neither was substituted.

## Exact authorized acquisition and installation

The user authorized the immutable
[SDK acquisition plan](../../manifests/phase-08d7-sdk-acquisition-plan.json),
SHA-256 `5543ed2470a56f0a3082ba51a1f81eb56b9ebc879aafaaf17d841365dd2f5b0a`.
Its historical `REQUIRED_NOT_GRANTED` field remains unchanged; the later user
authorization is recorded in the
[installation/qualification receipt](../../manifests/phase-08d7-sdk-installation-qualification.json).

Reproducible verification code: [exact acquisition/offline installer](../../scripts/acquire_phase08d7_sdk.py),
[RECORD/import verifier](../../scripts/verify_phase08d7_sdk.py) and
[socket/DNS guard](../../scripts/phase08d7_offline_guard.py). Local receipts are
created exclusively; existing acquisition/environment outputs are not replaced.

Exactly seven wheels were downloaded from their exact HTTPS URLs, totaling
2,279,867 bytes. System curl used an empty environment, disabled configuration
(`-q`) and proxies, no redirect following, and verified TLS. All seven responses
were HTTP 200, with certificate verification result zero and zero redirects.
Each byte count and full SHA-256 matched the allowlist before use.

Nine matching wheels were copied from the existing cache. The originals and
existing installer metadata were rechecked and remain unchanged. All sixteen
staged wheels match the exact plan; no additional artifact was acquired.

Wheelhouse: `/Users/ian/.codex/worktrees/2373/Memo/.local/phase08d7/wheelhouse`.
Isolated environment:
`/Users/ian/.codex/worktrees/2373/Memo/.local/phase08d7/runtime/.venv`.
These, requirements and raw logs remain ignored/outside Git.

Installation used existing repository pip **24.3.1** via `--python`, targeting
a fresh `--without-pip` venv, with `--no-index --no-deps --require-hashes
--only-binary=:all: --no-cache-dir --no-compile`. Installer subprocesses had
empty/specified environments, disabled pip configuration and the macOS profile
`(version 1)(allow default)(deny network*)`. No source build, target pip,
additional package or Hindsight installation occurred.

| Installed packages | Exact versions |
| --- | --- |
| OpenAI / HTTPX / HTTPCore | 2.24.0 / 0.28.1 / 1.0.9 |
| AnyIO / certifi / distro | 4.14.2 / 2025.10.5 / 1.9.0 |
| idna / jiter / h11 | 3.15 / 0.12.0 / 0.16.0 |
| pydantic / pydantic-core | 2.12.5 / 2.41.5 |
| annotated-types / sniffio / tqdm | 0.7.0 / 1.3.1 / 4.67.1 |
| typing-extensions / typing-inspection | 4.15.0 / 0.4.2 |

## Verification results

Installation verification passed: exactly **16 distributions**, their metadata
and installed versions; **1,412 wheel RECORD file hashes** and **1,464 installed
RECORD file hashes**; installed package bytes equal wheel bytes; `pip check`;
and **16/16 imports** from the isolated environment. Full wheel hashes/sizes
are in the concise receipt. No system/user-site or `.pth` dependency inheritance.

Verification ran under the macOS deny-network profile and a Python audit guard.
Socket construction and DNS self-tests were rejected before their syscalls;
package imports attempted neither. Hindsight imports are forbidden by the guard.
The prepared async test harness replaces asyncio's socketpair wakeup with
nonblocking OS pipes, so it can retain socket denial during future async tests.

The first test invocation stopped at an overly strict harness whitelist on
`__CF_USER_TEXT_ENCODING`, before any SDK call. Read-only diagnosis found this
non-network macOS encoding key present before SDK imports despite `env -i`;
only names were inspected. The harness was corrected to tolerate that key.
This corrected a preflight false positive; the macOS sandbox and Python socket/
DNS guard remained unchanged, and proxy/credential environment entries remain
rejected. No artifact, dependency or actual network-policy check failed.

The subsequent full run passed **30 cases**, recording **33 SDK invocations**
and **43 HTTPX transport requests** separately. SDK test socket/DNS attempts:
**0**, excluding two deliberately denied guard self-tests. Actual SDK socket
transmissions: **0**. Authorized acquisition's seven HTTPS requests are a
separate engineering action, not offline SDK traffic.

## Offline transport observations and remaining blockers

The [test harness](../../scripts/test_phase08d7_sdk_offline.py) exercised
success/tools, zero and finite SDK retry controls for 429/500/connect/read
failures, same/cross-host 307/308 redirects, routing/query/header/model overrides,
proxy-disabled clients, retained/copied/replaced resources, cleanup/cancellation,
and Responses/files/batches as HTTP resource controls. Explicit SDK invocation
counts are separate from HTTPX dispatches and usage receipts.

| Observed control | SDK invocations | HTTPX requests | Result |
| --- | --- | --- | --- |
| Success/tools | 1 | 1 | Parsed response and usage; owned client closed |
| 429/500/connect/read failure, SDK retries 0 | 1 per case | 1 per case | Correct SDK exception; no hidden SDK retry |
| Same failures, SDK retries 1 | 1 per case | 2 per case | Retry control recovered with one usage receipt |
| 307/308, SDK retries 0, default redirects | 1 per case | 2 per case | Same/cross-host POST preserved; cross-host Authorization removed |
| Redirect following explicitly disabled | 1 per case | 1 per case | SDK status error |
| Responses/files/batches control | 3 | 3 | Distinct HTTP resources; no remote inference count claim |

SDK-owned client defaults observed: `max_retries=0`, HTTPX
`follow_redirects=True`, `trust_env=True`. Qualified injected clients instead
use `trust_env=False`; a synthetic proxy environment setting did not create a
proxy mount. Query/header/base-path overrides reached the transport, and
`extra_body` can replace the wire model. A copied SDK shares its HTTP client;
closing the copy closes that shared client. Replacing the completions resource
reroutes to another client's transport, while a retained old resource still
uses its original client. These are measured ownership/routing limits, not
complete governance.

A second layer uses the installed HTTPCore pool with scripted streams, measuring
connection attempts, serialized HTTP request starts and raw writes separately.
TLS is simulated there. Six HTTPCore cases passed, with **9 connection attempts**
and **7 serialized HTTP request starts**. The zero-retry connect failure had one
HTTPX dispatch and no request start; the positive transport retry control had
two connections and one request start beneath one SDK invocation/HTTPX dispatch.
Read timeout followed one serialized request; redirects produced two. All
scripted streams closed. MockTransport alone does not qualify HTTPCore physical
sends, and simulated streams/TLS do not prove live socket or endpoint behavior.
Batch HTTP submission counts do not establish remote inference counts.

Independent review is next; no additional test or live run is authorized by this
report. Full Hindsight still needs a
complete pinned source/release artifact and its own dependency preparation;
the editable workspace lock has no Hindsight wheel hash. The locked
cryptography 50.0.0 has no Intel macOS wheel in that lock. A version/architecture
substitution or source build requires a separately reviewed plan, not a silent
change. D3 global worker coverage, endpoint-enforced inclusive token bounds and
D5 native ownership/attribution remain unresolved.

No Hindsight/provider initialization, model loading/download, hosted endpoint,
embedding, downstream/RQ3, empirical experiment, SSH or Jetstream action occurred.
D1/D2 evidence, Freeze v1/v2 draft, Candidate10 NO_GO, OpenViking S0 r2 ERROR and
scientific denominators remain unchanged. Publication is HTTPS to this review
branch only; main is not merged. **Stop for independent review.**
