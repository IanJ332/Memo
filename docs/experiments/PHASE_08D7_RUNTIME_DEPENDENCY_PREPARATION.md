# Phase 08D-7 — Isolated Runtime Dependency Preparation

**Dependency readiness: BLOCKED. No SDK/HTTP or native runtime test executed.**

CONVERSATION: Phase 08D-7 dependency preparation. MODEL: GPT-6 Codex runtime;
no independent model-variant receipt. EXECUTION TARGET: assigned local macOS
worktree `/Users/ian/.codex/worktrees/2373/Memo`. JETSTREAM ACTION: none;
remains SHELVED without querying infrastructure. Date: 2026-10-12,
America/Chicago.

The assigned checkout initially had clean detached HEAD `58ab52d`; the requested
base was available locally. The review branch `phase-08d7-runtime-dependencies`
was created at exactly `d29742e9a59575d63f54c50e10205208654240c1` before edits.
AGENTS, handoff/state/debugging ledgers and D5/D6 reports were read. No earlier
static send-path analysis or fake-only qualification test was repeated.

## Inventory and reproducible dependency selection

The [read-only inventory receipt](../../manifests/phase-08d7-dependency-preparation.json)
and [inventory script](../../scripts/prepare_phase08d7_inventory.py) record:

- Existing D4/D5/D6 repository venvs; D5/D6 reuse D4 through `.pth` files.
  D4 has 12 core distributions. The local Jetstream CLI venv has 56; it was
  inspected as files only, without running cloud tooling.
- Framework Python 3.12/3.13, the bundled artifact Python runtime, Conda base,
  `lite-msa`, and extracted Conda package metadata: 75 distinct site directories
  in total. Other interpreters, `.pth` code and provider modules were not run.
- The 1.2 GiB pip cache, including opaque HTTP-cache wheel bodies; 887 body/wheel
  files examined, with 279 wheel archives and 11 source archives identified.
  Cached metadata and source archives contain no Hindsight/OpenAI package.
  Conda cache wheels were also inspected. Both conventional uv
  cache directories are absent. No runtime lock was found in the inspected
  repository worktrees. Scope is these explicitly recorded local roots, not an
  exhaustive whole-machine absence claim.

Existing environments and caches were not modified. Metadata and relevant
artifact fingerprints were rechecked at audit completion; all were unchanged.
Compatible READY wheels also pass ZIP CRC checks and match exact upstream lock
SHA-256 values. Installed metadata alone never qualifies as a staged wheel.

The repository pins `hindsight-api-slim[embedded-db,local-onnx]==0.10.1`, but
does not pin its transitive dependencies. The Phase 04 provider fingerprint is
an aggregate hash, not a recoverable full package list; its OpenAI 3.20.0 entry
belongs to the **harness**, not the Hindsight environment. Infrastructure's
OpenAI 3.13.0 pin must not be substituted either.

New evidence is first-party dependency metadata at source commit
`f8950b0c07d9e34c76493dba802bb309f0ce60fd`:
[provider pyproject](https://github.com/vectorize-io/hindsight/blob/f8950b0c07d9e34c76493dba802bb309f0ce60fd/hindsight-api-slim/pyproject.toml)
and [workspace lock](https://github.com/vectorize-io/hindsight/blob/f8950b0c07d9e34c76493dba802bb309f0ce60fd/uv.lock).
Only these metadata files were retrieved over HTTPS, never package/model
artifacts. Their bytes match the already cached pinned Git tree:

| Metadata | Git blob SHA-1 | SHA-256 |
| --- | --- | --- |
| Provider pyproject | `e656821ca96c76b84a1d1cb1c7eb592f7f3b2563` | `4e73d3aae4711cb95639a2b3cfbe93ccf3a411b2ab3d4ad8924b7abc279930ec` |
| Workspace lock | `cd9687ebaa9a749e506ed396fc95c6f48925072a` | `c2df90ff2364b524453662e880d872edbe6307b3bddea4dea8604c7a8455cb5c` |

Marker evaluation targets **CPython 3.12.8, Intel macOS 15.7.4**. The selected
184-package closure includes the frozen requirement's two extras and satisfies
the declared direct constraints. This is a reproducible **proposed offline
qualification resolution**, not reconstruction or amendment of historical runs.
The receipt records every exact version, compatible artifact URL and hash,
available local artifact and missing package.

| Component / SDK dependency | Selected version | Local artifact readiness |
| --- | --- | --- |
| Hindsight API slim | 0.10.1, pinned source commit above | BLOCKED: source subset only; lock uses editable source, no wheel hash |
| OpenAI SDK | 2.24.0 | BLOCKED |
| HTTPX / HTTPCore | 0.28.1 / 1.0.9 | READY |
| AnyIO / certifi / distro | 4.14.2 / 2025.10.5 / 1.9.0 | BLOCKED |
| idna / jiter / pydantic | 3.15 / 0.12.0 / 2.12.5 | BLOCKED |
| h11 / sniffio / tqdm | 0.16.0 / 1.3.1 / 4.67.1 | READY |
| annotated-types / pydantic-core | 0.7.0 / 2.41.5 | READY |
| typing-extensions / typing-inspection | 4.15.0 / 0.4.2 | READY |
| aiohttp | 3.14.3 | BLOCKED: cached 3.14.0 is insufficient |
| cryptography | 50.0.0 | BLOCKED: no Intel macOS wheel in this lock; cached 50.0.1 differs |
| Full runtime closure | 184 packages | 33 READY local wheels; 151 BLOCKED |

No complete SDK or Hindsight environment can be staged from the inspected local
artifacts. A clean repository `.venv` was created with `--without-pip` using
D5's repository interpreter solely for inventory. It has no distributions,
system site packages or reuse `.pth`. The audit imports only the existing D4
`packaging` parser by explicit path and inspects other packages as data; an
audit hook denies socket connection/DNS attempts. This bootstrap is **not** an
installed qualification environment. No dependency installation, provider
import/construction, SDK request, service or model initialization occurred.

## Smallest separately authorized next step

The [SDK acquisition plan](../../manifests/phase-08d7-sdk-acquisition-plan.json)
lists **seven** missing wheels: OpenAI 2.24.0, AnyIO 4.14.2, certifi 2025.10.5,
distro 1.9.0, idna 3.15, jiter 0.12.0 and pydantic 2.12.5. Each has an exact
`files.pythonhosted.org` URL, size and full SHA-256 from the pinned lock.
The downloads total 2,279,867 bytes. The other nine SDK wheels can be copied
from the cache without modifying it.

Proposed wheelhouse:
`/Users/ian/.codex/worktrees/2373/Memo/.local/phase08d7/wheelhouse`.
Proposed isolated environment:
`/Users/ian/.codex/worktrees/2373/Memo/.local/phase08d7/runtime/.venv`.
Neither directory has been populated or used for installation.

**Separate authorization is required before acquisition or installation.**
Limit acquisition to the seven exact HTTPS artifact URLs; allow only
`pypi.org` / `files.pythonhosted.org`, verify TLS and lock hashes, and reject
cross-host redirects. Disable indexes and all networking for installation and
tests, including loopback. Install wheels only with `--no-index --no-deps
--require-hashes`; use the existing D4 repository pip 24.3.1 via `--python` to
target a new `--without-pip` venv, avoiding an additional pip download. Run
metadata/RECORD identity checks, `pip check` and import
checks before transport tests. Do not inherit credentials, `.env`, proxies or
user sites. No source builds, provider initialization or model downloads.

This SDK-only step cannot qualify Hindsight. Full native qualification still
requires the 151-package missing-artifact plan, a complete Hindsight source or
release wheel proven against the pin, and a separately reviewed solution for
cryptography's target-platform gap. A source build would need its own exact
build-tool/dependency plan; silently changing cryptography or architecture is
not an approved solution. No published Hindsight wheel hash is available in
the editable workspace lock, and none is invented here.

## Minimal deterministic transport tests to execute after preparation

Use the real pinned SDK serializers and HTTPX/HTTPCore stack, synthetic `.test`
endpoints and scripted responses. An HTTPX MockTransport can measure SDK
dispatches but bypasses HTTPCore; it alone cannot qualify physical-send behavior.
Also inject a scripted HTTPCore async network backend into the pinned HTTPX
transport, with all real sockets/DNS denied. Count complete HTTP request starts
separately from connection attempts, raw stream writes, logical SDK invocations
and usage receipts. Several writes can belong to one request. These are
simulated wire-boundary measurements; actual socket transmissions remain zero.

| Test | Required observation |
| --- | --- |
| Successful chat/tools request | One request for `max_retries=0`; bind final URL, method, model/body hash, admission and one receipt. |
| 429/500, connect/read timeout, connect failure | Measure SDK and transport retry layers separately; explicit zero-retry configuration emits no additional request. Compare a finite positive retry control; never assume failed connection means zero attempted work. |
| 307/308 same-host and cross-host redirects | Measure actual default behavior; explicit no-follow configuration emits one request. A governed allowlist rejects rerouting before a second request; record sensitive-header handling with synthetic credentials. |
| Routing / endpoint mutation | Resolve base path, default query/headers, per-call overrides and proxy configuration to the final transport destination; unauthorized destinations/parameters reject before stream write. |
| Resource ownership / cleanup | Retained, replaced and copied clients/resources share or bypass the transport as actually observed. Include Responses/files/batches as HTTP resource controls, without claiming HTTP counts equal batch inference counts; verify owned close/cancellation behavior. |
| Native restricted boundary, later | Only after complete Hindsight artifacts/import safety are verified: execute applicable pinned provider methods against the owned offline SDK, without engine/service/model initialization. Bind every observed attempt and native retry; preserve the unconditional runtime gate. |

No implementation of these tests or additional fake-only test was added.
D3/global worker ownership, endpoint-enforced total-token bounds and D5/native
attribution remain separate unresolved prerequisites.

## Verification and stop

Inventory completed with all inspected existing artifacts unchanged; exact READY
wheel hashes, platform tags and CRC checks passed. The two metadata files match
their pinned Git blobs. Freeze validation passes with canonical SHA-256
`0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b`.
No pytest or SDK transport test was run; D6's 161 tests are prior evidence only.
Preparation receipt/plan consistency, source parsing and diff checks pass;
protected runtime/test/configuration/evidence paths match the base.
The inventory accepts explicit metadata/site/cache/config paths and exclusively
creates new receipts; repeat it with the recorded inputs and a fresh output path.
Ignored metadata/bootstrap files are not published.

D1/D2 evidence, runtime `BLOCKED` gate, frozen attempts, Freeze v1/v2 draft,
Candidate10 NO_GO, OpenViking S0 r2 ERROR and scientific denominators are
unchanged. Provider/model/embedding/downstream/RQ3, SSH and Jetstream actions:
zero. Git publication uses HTTPS on this review branch only; main is not merged.
**Stop pending separate dependency acquisition/installation authorization.**
