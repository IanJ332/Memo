# Phase 08D-9 — Stage 1 static provider boundary derivative

**STATIC PASS; independent review required. Engineered source only. D3/D5 PARTIAL;
D4 BLOCKED; runtime safety UNKNOWN; semantic parity NOT_EXECUTED.**

CONVERSATION: Phase 08D-9 Stage 1 Static Provider Boundary Derivative.
MODEL: GPT-6 Codex runtime; no independent model-variant receipt.
EXECUTION TARGET: local worktree `/Users/ian/.codex/worktrees/aba1/Memo`.
JETSTREAM ACTION: none; remains SHELVED without infrastructure access.
Date: 2026-10-13, America/Chicago.

The clean assigned checkout initially had detached HEAD `16fdb42`. Expected base
`523055af834c285ec6608ffa37e15b31ffc4e86b` was verified as merged using an HTTPS
fetch of main; fetched `origin/main` was exactly that SHA. Review branch
`phase-08d9-stage1-static-derivative` starts at the expected base. The configured
SSH origin was explicitly rejected and changed to
`https://github.com/IanJ332/Memo.git` before successful network operations.
An initial sandboxed configuration change and fetch were blocked on Git metadata
permissions before transport; neither contacted Git over SSH. Subsequent fetch
and publication use HTTPS. The scripts reject configured non-HTTPS URLs and
non-HTTPS effective fetch/push URLs after Git rewrite expansion. No infrastructure
or Jetstream SSH, main merge or force push is authorized or performed.

## Governing evidence and implemented boundary

Read AGENTS.md, handoff/state/debugging ledgers, the
[architecture decision](PHASE_08D9_PROVIDER_BOUNDARY_ARCHITECTURE.md),
[D8 source-closure evidence](PHASE_08D8_MINIMAL_NATIVE_RUNTIME_PREPARATION.md)
and [D7 qualification](PHASE_08D7_RUNTIME_DEPENDENCY_PREPARATION.md).
The immutable D8 source receipt SHA-256 is
`772680fb16cc79b2dd85b8c07ae435a07e56b6329f926e84ed6b3457991f87dd`;
D7 qualification receipt is
`bd93ebf5b537c0c53a7c9570b6ae4daf810d42891d40b6477855108b05d13aca`.
D7's historical SDK tests were read, never rerun. Their SDK-only result remains
separate from this source derivative.

Upstream is Hindsight 0.10.1, commit
`f8950b0c07d9e34c76493dba802bb309f0ce60fd`. The pinned recursive tree-response
SHA-256 is `b23c03c1c9daf42b764988da19b5aa70e7bd710c8b05092f290773acef35ed33`.
Exact engineered identity is
`memlife-hindsight-provider-boundary/0.1.0+upstream.f8950b0c07d9`, additionally
bound to the manifest and patch hashes. **ENGINEERED_PROVIDER_BOUNDARY;
UNMODIFIED_HINDSIGHT_RUNTIME=false.** Native root `__version__ = "0.10.1"` is
preserved for native headers; it is insufficient to identify this derivative.

The [materializer](../../scripts/materialize_phase08d9_provider_boundary.py)
checks all 131 original byte counts, Git blob SHA-1s and SHA-256s against the
immutable D8 receipt and pinned tree before parsing/transformation. It validates
pinned metadata, exact selected cache/frontier inventories and rehashes reusable
binary artifacts as inert bytes. Missing, extra, modified, EOL-drifted or symlinked
inputs reject. `api_main.py` is a documented historical non-input in the shared
cache: it is neither read nor materialized; other extra Python inputs reject.
There is no download, install, build or upstream-code execution path.

Materialized output is a new exclusive ignored tree:
`.local/phase08d9/provider-boundary/0.1.0/`, with source under
`source/hindsight-api-slim/hindsight_api/`, plus `bootstrap.patch` and canonical
`receipt.json`. Originals in `/private/tmp/hindsight_audit` and the D8 worktree
source frontier remain unchanged. No existing output or published receipt is
replaced; failed partial outputs require a new exclusive directory. A second
independent materialization is retained at
`.local/phase08d9/verification/rematerialization-001/`.

## Source identities and transformation

There are **131 retained files**, **3 modified** and **128 byte-identical**.
Original aggregate bytes: **4,829,894**; derivative aggregate bytes: **4,834,053**.
The entire 105,773-byte OpenAI-compatible provider is unchanged, including native
constructor, calls/tools, retries, parsing, cleanup, batch and Ollama bodies.
All included helpers, real root initialization and `_thread_limits.py` remain
byte-identical. Retaining a body does not authorize calling it.

The [source manifest](../../manifests/phase-08d9-provider-boundary-source.json)
lists every included original and derivative path, byte count, SHA-1, SHA-256,
classification and inclusion reason. The provider-only literal graph contains
29 modules; 102 other verified sources remain inactive for audit and original
export-target retention. They are not added to the 41-package installation
projection. This is an engineered source collection, not a truncated upstream
installed distribution.

| Path relative to `hindsight_api/` | Original / derivative bytes | Original SHA-256 | Derivative SHA-256 |
| --- | --- | --- | --- |
| `engine/__init__.py` | 1546 / 3648 | `abdce96a0c096bf31ffeacc9e4390d5f72ca6ff4dbc38636caf14857aadc6863` | `35ad19e2b216a2e91f7eee502d4c8c284da3553ddb9c80ed5236381b5858fb56` |
| `engine/providers/__init__.py` | 987 / 2410 | `ba35543c65d3166834eb0b03ce20da749dc384793d7b64c1eaef3ff4458df41a` | `92239e5a55f4dcb32d0efcbd9208389ed0522019fd473bc65bc4154cbf769728` |
| `engine/providers/openai_compatible_llm.py` | 105773 / 105773 | `7c6aad58263b6b4134a7a67c2c5c289d22d106c90532f15a321fc28f6b05abae` | `7c6aad58263b6b4134a7a67c2c5c289d22d106c90532f15a321fc28f6b05abae` |
| `worker/__init__.py` | 256 / 890 | `873a4c2ef39f80bd8a2abae293ff68baf13309dbc94ab1fea63e547452badc9d` | `130d94524d70829c9a1c0c2d06434dec707499bee34b4b5f0b359390e50cc23d` |

| Path | Original Git blob SHA-1 | Derivative Git blob SHA-1 |
| --- | --- | --- |
| `engine/__init__.py` | `8ec70075bae971adef5d6bd941a2f1db7fe1787c` | `5287f86f6ee9d9ad3b6eac3638674d97a53372c5` |
| `engine/providers/__init__.py` | `5f8e42ecc549e1ea35b4d6472c71ae755935f6f6` | `96b2d2778118e0c45c474d810cf499de661ff136` |
| `engine/providers/openai_compatible_llm.py` | `ae5952f216ca9dcd78435ce7f1966ddfb0b1515b` | `ae5952f216ca9dcd78435ce7f1966ddfb0b1515b` |
| `worker/__init__.py` | `8eb27f9f0d8ce79fc4c29f731d4cbf40615f550a` | `d702ad92dd4fcec685ea0b55cb1595655bfa5f31` |

Canonical original source-tree SHA-256:
`efce66ca78ff390ca5bf9c1055dee28a832f0b20c78a3a200a806eef4dc03450`.
Canonical observed derivative source-tree SHA-256:
`acc7bbd98c69451108a2f547709be7980f1fe575799a9eea77ba753900142a40`.
Both hash a sorted path-to-identity JSON map, UTF-8, compact sorted keys,
`ensure_ascii=false`, with one LF terminator; they are not Git tree object IDs.

[Reviewable patch](../../patches/phase-08d9-provider-boundary-bootstrap.patch):
7,741 LF bytes; SHA-256 `8792b771f8c6a0c69075ca3d37d512ad409de33ec669dabba5715c14939a499b`;
Git blob SHA-1 `200bc27ad0b99a2dc9dabb6c382a7f56778654a7`.
Transform specification: `pep562-three-initializers/1.0.0`.
Source manifest SHA-256:
`91bdb4c3cdb28e0879b686ba1bd5448d375c02b51a1e0cd612f120b2f7f4ad72`.

Each transformed initializer preserves its original documentation and exact
`__all__` text/order/comments. Original imports become TYPE_CHECKING reexports;
the same names map to the same relative modules and attributes. PEP 562
`__getattr__` caches the real resolved object. Only unknown-name lookup KeyError
becomes AttributeError; original target import/getattr exceptions propagate.
`__dir__` includes globals and public exports. No fake packages, module stubs,
import hooks, initializer bypasses, extracted methods or source substitutions.

The verifier independently builds an AST oracle from the original export
statements and its own reviewed resolver syntax, without importing the
materializer. It rejects extra executable statements, changed targets/names,
exception swallowing and eager implementation imports. Lazy target edges match
original eager target edges exactly; no new first-party target edge or potential
target cycle is introduced by the transform. On the projected provider-only
path, none of the transformed packages eagerly imports an implementation and no
internal lazy export is activated. Runtime reentrancy/circular resolution of
other exports remains untested. Star import/full-export resolution may require
the full dependencies and is excluded.

## Independent verification and focused controls

[Independent verifier](../../scripts/verify_phase08d9_provider_boundary.py)
passed identities, exact three-path modifications, every other byte comparison,
public maps and syntax, complete observed literal graph, actual metadata closure,
exact patch and tooling hashes, no substitutions, canonical receipts, fresh
byte-identical rematerialization, repeat-output rejection and original-input
rehash after verification. [Verification receipt](../../manifests/phase-08d9-stage1-static-verification.json)
SHA-256: `63bc5a1e954d6056e79c06f3d4340a3f3bff8e27a39b3d6c3cfe6a9aad219772`.

[31 focused tests](../../scripts/test_phase08d9_static_derivative.py) passed,
zero failures/errors. Controls cover original tamper/EOL/missing/extra/symlink,
wrong tree/receipt/metadata/artifact, derivative missing/extra/symlink/empty
package directory, altered public names/targets/all, swallowed exception, eager
excluded target and extra execution, out-of-scope provider/root patches including
forged identities, patch/claim/dependency forgery, immutable output/publication,
path traversal, SSH URLs and pre-execution SDK/socket/DNS denial. Positive
verification accompanies the rejection controls. [Test receipt](../../manifests/phase-08d9-stage1-static-tests.json)
SHA-256: `212727a963b0d9f35e9046b64d246ad8e07d3f28b7d5c9423f3aa001fb9e76e2`.

The first development test receipt recorded one verifier-oracle error: original
import order differs from `__all__` order. The independent oracle now orders the
map by the preserved public list. The failed development receipt remains in
ignored `.local/phase08d9/tests-dev01.json`; final receipts are separate and
exclusive. The first sandbox-exec launch was denied before Python startup;
subsequent host-approved launches applied OS network denial successfully.

All final tests/materialization/verification used the existing repository D7
`.venv` interpreter with `-I -B`, and
`/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)'`.
The static audit hook rejects native/SDK imports and socket/DNS events; it also
rejects already loaded native/SDK modules. Only standard-library and repository
static tooling execute. D7's installed site, SDK sources, artifacts and receipts
were not altered. Static success does not establish safe import or runtime parity.

## Recomputed source and dependency closure

**Actual: 29 modules / 41 packages**, matching the ADR projection exactly.
Seeds are normal provider submodule import and the successful native method's
late tracing import. Real Python parent packages are included. All mandatory
literal module bodies are available; conditional/deferred/type-only edges are
listed in the manifest and remain unqualified. This is a method-scope projection,
not an exhaustive dynamic-dependency proof or execution observation.

```text
hindsight_api
hindsight_api._cross_loop
hindsight_api._pg_extensions
hindsight_api._pg_search
hindsight_api._thread_limits
hindsight_api._vector_index
hindsight_api.config
hindsight_api.engine
hindsight_api.engine.aiohttp_session
hindsight_api.engine.bank_attribution
hindsight_api.engine.cache_affinity
hindsight_api.engine.db_utils
hindsight_api.engine.llm_interface
hindsight_api.engine.llm_trace
hindsight_api.engine.llm_transport
hindsight_api.engine.llm_wrapper
hindsight_api.engine.metadata_utils
hindsight_api.engine.provider_auth
hindsight_api.engine.providers
hindsight_api.engine.providers.llm_debug
hindsight_api.engine.providers.openai_compatible_headers
hindsight_api.engine.providers.openai_compatible_llm
hindsight_api.engine.response_models
hindsight_api.engine.structured_output
hindsight_api.metrics
hindsight_api.tracing
hindsight_api.utils
hindsight_api.worker
hindsight_api.worker.stage
```

Direct package roots: `aiohttp`, `httpx`, `json-repair`, `openai`, `opentelemetry-api`, `opentelemetry-exporter-otlp-proto-http`, `opentelemetry-exporter-prometheus`, `opentelemetry-sdk`, `pydantic`, `pydantic-core`, `python-dotenv`, `sqlalchemy`.
Target metadata environment is pinned CPython 3.12.8, Intel macOS (`darwin`,
`x86_64`); no alternate interpreter/platform/package resolution is accepted.
SQLAlchemy and native observability imports are retained. No Google GenAI,
Google Auth or cryptography is in this projection; optional Google OAuth is
excluded and its native ImportError behavior is preserved. The full upstream
distribution still has its cryptography floor and full Requires-Dist; this
source collection does not satisfy or weaken them.

| Package | Locked version | Stage 1 artifact availability |
| --- | --- | --- |
| `aiohappyeyeballs` | `2.6.1` | MISSING_PINNED_BINARY |
| `aiohttp` | `3.14.3` | MISSING_PINNED_BINARY |
| `aiosignal` | `1.4.0` | LOCAL_REHASHED |
| `annotated-types` | `0.7.0` | LOCAL_REHASHED |
| `anyio` | `4.14.2` | LOCAL_REHASHED |
| `attrs` | `25.4.0` | MISSING_PINNED_BINARY |
| `certifi` | `2025.10.5` | LOCAL_REHASHED |
| `charset-normalizer` | `3.4.4` | LOCAL_REHASHED |
| `distro` | `1.9.0` | LOCAL_REHASHED |
| `frozenlist` | `1.8.0` | MISSING_PINNED_BINARY |
| `googleapis-common-protos` | `1.75.0` | MISSING_PINNED_BINARY |
| `greenlet` | `3.2.4` | MISSING_PINNED_BINARY |
| `h11` | `0.16.0` | LOCAL_REHASHED |
| `httpcore` | `1.0.9` | LOCAL_REHASHED |
| `httpx` | `0.28.1` | LOCAL_REHASHED |
| `idna` | `3.15` | LOCAL_REHASHED |
| `jiter` | `0.12.0` | LOCAL_REHASHED |
| `json-repair` | `0.63.2` | MISSING_PINNED_BINARY |
| `multidict` | `6.7.0` | MISSING_PINNED_BINARY |
| `openai` | `2.24.0` | LOCAL_REHASHED |
| `opentelemetry-api` | `1.44.0` | MISSING_PINNED_BINARY |
| `opentelemetry-exporter-otlp-proto-common` | `1.44.0` | MISSING_PINNED_BINARY |
| `opentelemetry-exporter-otlp-proto-http` | `1.44.0` | MISSING_PINNED_BINARY |
| `opentelemetry-exporter-prometheus` | `0.65b0` | MISSING_PINNED_BINARY |
| `opentelemetry-proto` | `1.44.0` | MISSING_PINNED_BINARY |
| `opentelemetry-sdk` | `1.44.0` | MISSING_PINNED_BINARY |
| `opentelemetry-semantic-conventions` | `0.65b0` | MISSING_PINNED_BINARY |
| `prometheus-client` | `0.23.1` | MISSING_PINNED_BINARY |
| `propcache` | `0.4.1` | MISSING_PINNED_BINARY |
| `protobuf` | `7.35.1` | MISSING_PINNED_BINARY |
| `pydantic` | `2.12.5` | LOCAL_REHASHED |
| `pydantic-core` | `2.41.5` | LOCAL_REHASHED |
| `python-dotenv` | `1.2.2` | MISSING_PINNED_BINARY |
| `requests` | `2.34.2` | LOCAL_REHASHED |
| `sniffio` | `1.3.1` | LOCAL_REHASHED |
| `sqlalchemy` | `2.0.44` | MISSING_PINNED_BINARY |
| `tqdm` | `4.67.1` | LOCAL_REHASHED |
| `typing-extensions` | `4.15.0` | LOCAL_REHASHED |
| `typing-inspection` | `0.4.2` | LOCAL_REHASHED |
| `urllib3` | `2.7.0` | MISSING_PINNED_BINARY |
| `yarl` | `1.22.0` | MISSING_PINNED_BINARY |

**19 ready local artifact slots** were rehashed: 16 D7 SDK artifacts and three
other matching local wheels. **22 missing binaries**, selected candidate total
**4,390,044 bytes**, need separate acquisition authority. No locked compatibility
gap appears in this provider-only metadata projection. D8's ordinary-import
61-package closure has 24 ready slots/36 missing/one crypto gap; those are
separate counts, not an enlarged Stage 1 install scope.

The manifest includes the complete markers/extras/edges, target environment and
one selected exact filename/URL/size/hash for each projected package, plus
compatible locked alternatives. This is the proposed installation plan only;
`installation_authorized=false`. No package was downloaded, installed, built,
imported or executed by Stage 1.

## Deviations, limitations and next authorization

No source or package-count deviation from the reviewed ADR: exactly the three
approved initializers change; 29/41 remains correct. Two explicit preparation
limits require review:

- All 131 verified sources are retained for provenance/export targets; only 29
  are projected active. Excluded features remain on disk and must be rejected by
  a future reviewed import/entry gate, not treated as unavailable or authorized.
- LICENSE bytes are absent from the verified receipt. The pinned tree records
  1,075 bytes and Git blob SHA-1 `8dce7b4d4c2632990bdf8b4101694ea19ba6ad46`;
  SHA-256 is explicitly null/unobserved. No NOTICE path is present in that tree.
  No missing file was fetched. License-byte materialization/provenance is a
  separately authorized prerequisite for packaging or redistribution.

Still UNKNOWN/NOT_EXECUTED: real root thread defaults/CPU/cgroup effects;
third-party import side effects and platform/native compatibility; lazy export
resolution/reentrancy/failure timing; logging/config/optional/dynamic expansion;
provider construction and complete native method behavior; SDK factory/transport
ownership, request multiplicity, final-wire enforcement, cleanup and accounting;
ordinary-import B/C parity. The static literal graph cannot qualify any of these.
No changed `require_hindsight_runtime_ready()`; D4 stays BLOCKED.

**Stage 2 requires independent acceptance of this exact source manifest, patch,
export contract, verifier/tests and 41-package plan, then explicit artifact-only
authorization.** The authorization must name the reviewed manifest SHA and exact
22 missing binary filenames/HTTPS URLs/sizes/SHA-256s, request/byte limits
(22 files / 4,390,044 candidate bytes if unchanged), and rehash/copy of the 19
existing slots. It must permit new
`manifests/phase-08d9-provider-boundary-dependencies.json` and
`scripts/prepare_phase08d9_provider_boundary.py`, and an exclusive
`.local/phase08d9/runtime/.venv` owned by this repository. Freeze a dedicated
exact dependency allowlist before acquisition; reject redirects, changed hashes,
unavailable wheels, new platform/closure, builds/sdists or quiet alternatives.
No provider/source build is part of this plan.

If installation is explicitly authorized, use binary-only, no-index, no-deps,
require-hashes installation into that fresh isolated venv, with no inherited
site packages, `.pth`/editable ownership or another distribution owning
`hindsight_api`. Verify artifacts, versions, metadata and RECORD under network
denial. Preserve D7's environment and all receipts; no Hindsight/SDK import,
construction or method execution follows from artifact installation permission.
Packaging/redistribution additionally requires explicit pinned LICENSE source
acquisition/verification and a distinct engineered distribution, without editing
upstream requirements or claiming a full upstream installation. A manifest,
closure, artifact or licensing mismatch returns to review.

Stage 3 imports, Stage 4 methods/transport and Stage 5 reference comparison each
need separate authorization. No Stage 2 artifact readiness or Stage 1 static
result may promote full native startup, scientific pilot or RQ3 readiness.

## Reproduction and preserved state

Use the materializer with the existing source cache, D8 source-frontier root,
pinned tree-response file and D7 metadata directory as explicit arguments. The
scripts never discover a mutable latest cache. Existing output/publication paths
must not be reused. Tool identities are in the source manifest; new tooling or
input bytes require a new reviewed engineered version/receipt.

```sh
phase08d9_python=/Users/ian/.codex/worktrees/2373/Memo/.local/phase08d7/runtime/.venv/bin/python
/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' \
  "$phase08d9_python" -I -B scripts/materialize_phase08d9_provider_boundary.py \
  --source-cache /private/tmp/hindsight_audit \
  --source-frontier /Users/ian/.codex/worktrees/b648/Memo/.local/phase08d8/source-frontier \
  --pinned-tree /private/tmp/phase08d5-pinned-tree.json \
  --metadata-root /Users/ian/.codex/worktrees/2373/Memo/.local/phase08d7 \
  --output .local/phase08d9/review/new-exclusive-tree
# Verifier uses the same four input arguments, plus:
# --derivative <tree> --manifest <tree>/receipt.json
# --rematerialize-output <fresh-ignored-tree> --receipt-output <new-receipt>
# Focused tests use the same four inputs, plus --receipt-output <new-receipt>.
```

Frozen evidence, denominators, Candidate10 NO_GO, OpenViking S0 r2 ERROR,
D1/D2 receipts and all D5–D8 code/receipts are unchanged. Canonical Freeze v1
SHA-256 remains
`0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b`;
Freeze v2 remains draft. Native/SDK imports, provider construction, actual
provider/model/embedding/downstream/RQ3 calls, acquisition/install/build,
empirical runs and infrastructure actions are zero for this phase.
Commit/push only the review branch, then **stop for independent review**.
Retrieved != Authoritative.
