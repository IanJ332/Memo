# Phase 08D-9 — Stage 2 isolated dependency preparation

**STOPPED during acquisition qualification. Installation NOT_EXECUTED.**
D3/D5 PARTIAL; D4 BLOCKED; runtime safety UNKNOWN; semantic parity NOT_EXECUTED.

CONVERSATION: Phase 08D-9 Stage 2 dependency preparation.
MODEL: GPT-6 Codex runtime; no independent model-variant receipt.
EXECUTION TARGET: local `/Users/ian/.codex/worktrees/3a57/Memo`. JETSTREAM ACTION: none; remains SHELVED.
Date: 2026-10-13, America/Chicago.

## Authorized scope and completed preflight

Stage 1 passed independent human review and was separately fast-forwarded to
main. Fresh HTTPS `ls-remote` independently returned `a14b21f6157f7994ccb333994a85fd766aba540e` for both main
and phase-08d9-stage1-static-derivative. Stage 2 branch `phase-08d9-stage2-dependency-preparation` was clean
and exactly based on that commit before edits. No SSH, rewrite to SSH, hook
disablement, main merge or primary-checkout change occurred in Stage 2.

Read AGENTS.md, project handoff/state/debugging ledgers, the
[ADR](PHASE_08D9_PROVIDER_BOUNDARY_ARCHITECTURE.md),
[Stage 1 report](PHASE_08D9_STAGE1_STATIC_PROVIDER_BOUNDARY.md), D7/D8 tooling
and the source/SDK receipts. The exact approved
[source manifest](../../manifests/phase-08d9-provider-boundary-source.json)
remains SHA-256 `91bdb4c3cdb28e0879b686ba1bd5448d375c02b51a1e0cd612f120b2f7f4ad72`.
The unchanged independent Stage 1 verifier, SHA-256 `1aedece04cfc9816206ee59246f323e7a3fa18eb12031c4ab201bf27aa615098`, was
invoked read-only: all 131 source identities, three permitted transformations,
patch/export graph and 41-package closure revalidated. No rematerialization or
historical SDK test rerun occurred. All 19 original selected wheel artifacts
passed size/SHA-256, ZIP, WHEEL tags, METADATA and wheel RECORD checks, and were
rehashed unchanged after STOP. Exact original paths are in the dependency manifest.

CPython 3.12.8, macOS 15.7.4, x86_64, ABI
`cpython-312-darwin` and compatible wheel tags were verified.
The immutable ignored acquisition plan SHA-256 is
`dc477b3135f262a4ed4d3e421ff4d906ee040f0dfd0f9241926791931a8688b9`. It contains all names, versions, filenames,
exact HTTPS URLs, sizes, SHA-256s, tags, dependency edges, markers and source
identity. The missing set is exactly 22 unique artifacts / 4,390,044 bytes.
No broader Hindsight distribution, alternate wheel or dependency was selected.

## Exact acquisition outcome and STOP

All five promoted wheels and the 19 originals were also rechecked read-only
under OS denial of all networking after STOP.

Six exact allowlisted requests returned HTTP 200, TLS verification result zero,
zero redirects and the unchanged effective URL. Total downloaded bytes with
matching size/SHA-256: **1,425,689**. Failed HTTP requests: **0**. Retries: **0**.
Five artifacts passed all implemented checks and were exclusively promoted,
total **1,151,610 bytes**:

| Verified filename | Bytes | SHA-256 |
| --- | ---: | --- |
| `aiohappyeyeballs-2.6.1-py3-none-any.whl` | 15265 | `f349ba8f4b75cb25c99c5c2d84e997e485204d2902a9597802b0371f09331fb8` |
| `aiohttp-3.14.3-cp312-cp312-macosx_10_13_universal2.whl` | 754690 | `39aded8c7f3b935b54aab1d8d73c70ec0ee2d3ec3b943e0e86611bc150ba47f5` |
| `attrs-25.4.0-py3-none-any.whl` | 67615 | `adcf7e2a1fb3b36ac48d97835bb6d8ade15b8dcce26aba8bf1d14847b57a3373` |
| `frozenlist-1.8.0-py3-none-any.whl` | 13409 | `0c18a16eab41e82c295618a77502e17b195883241c563b00f0aa5106fc4eaa0d` |
| `googleapis_common_protos-1.75.0-py3-none-any.whl` | 300631 | `961ed60399c457ceb0ee8f285a84c870aabc9c6a832b9d37bb281b5bebde43ed` |

Request 6 fetched `greenlet-3.2.4-cp312-cp312-macosx_11_0_universal2.whl`, 274,079 bytes, SHA-256
`3b67ca49f54cede0186854a008109d6ee71f66bd57bb36abd6d0a0267b540cdd`. The preparation verifier rejected the member
`greenlet-3.2.4.data/headers/greenlet.h` under its blanket unsupported `.data`
relocation check. **This is a limitation in the new preparation verifier;
artifact incompatibility or corruption was not demonstrated.** There is no
executable `.pth` member. Read-only diagnosis after STOP confirms the exact
artifact identity, ZIP CRC, CPython/macOS WHEEL tag, METADATA name/version and
all 94 hashed wheel RECORD members. The header is inert data;
installing it still needs an explicit, tested destination/RECORD ownership map.
The STOP check was retained, not bypassed or quietly relaxed.

The unpromoted `.part` bytes, pre-request/result/STOP ledger and failing receipt
remain immutable under `.local/phase08d9/stage2/`. Each request is logged and
fsynced before invocation; results/failures are retained. Curl uses `-q`, an empty
proxy/credential environment, HTTPS-only protocol, normal TLS verification,
no redirect following, no retries and the exact per-file size limit. No resource
limit was exceeded. Six completed HTTP downloads count against the original
22-download allowance, including greenlet. **16 artifacts / 2,964,355 bytes were
never requested.** Any reviewed continuation must reuse those greenlet bytes
without redownloading and preserve total accounting and prior failed receipts.

An earlier offline read-only preflight probe selected the historical D7 bootstrap
without pip and raised `ModuleNotFoundError: No module named 'pip'`. The already
frozen repository installer `.venv` at worktree 9e5b, pip 24.3.1, was then used;
its METADATA hash was revalidated. No package was installed to repair that
diagnostic. Both diagnostics are recorded; neither changes scientific evidence.

## Reused 19 artifact identities

Sixteen are from D7's original ignored wheelhouse; aiosignal, charset-normalizer
and requests are from their original pip-cache body files. Original caches,
environments and D7 receipts are unchanged. These identities have been verified
as inert files, not imported by this phase.

| Filename | SHA-256 |
| --- | --- |
| `aiosignal-1.4.0-py3-none-any.whl` | `053243f8b92b990551949e63930a839ff0cf0b0ebbe0597b0f3fb19e1a0fe82e` |
| `annotated_types-0.7.0-py3-none-any.whl` | `1f02e8b43a8fbbc3f3e0d4f0f4bfc8131bcb4eebe8849b8e5c773f3a1c582a53` |
| `anyio-4.14.2-py3-none-any.whl` | `9f505dda5ac9f0c8309b5e8bd445a8c2bf7246f3ce950121e45ea15bc41d1494` |
| `certifi-2025.10.5-py3-none-any.whl` | `0f212c2744a9bb6de0c56639a6f68afe01ecd92d91f14ae897c4fe7bbeeef0de` |
| `charset_normalizer-3.4.4-cp312-cp312-macosx_10_13_universal2.whl` | `0a98e6759f854bd25a58a73fa88833fba3b7c491169f86ce1180c948ab3fd394` |
| `distro-1.9.0-py3-none-any.whl` | `7bffd925d65168f85027d8da9af6bddab658135b840670a223589bc0c8ef02b2` |
| `h11-0.16.0-py3-none-any.whl` | `63cf8bbe7522de3bf65932fda1d9c2772064ffb3dae62d55932da54b31cb6c86` |
| `httpcore-1.0.9-py3-none-any.whl` | `2d400746a40668fc9dec9810239072b40b4484b640a8c38fd654a024c7a1bf55` |
| `httpx-0.28.1-py3-none-any.whl` | `d909fcccc110f8c7faf814ca82a9a4d816bc5a6dbfea25d6591d6985b8ba59ad` |
| `idna-3.15-py3-none-any.whl` | `048adeaf8c2d788c40fee287673ccaa74c24ffd8dcf09ffa555a2fbb59f10ac8` |
| `jiter-0.12.0-cp312-cp312-macosx_10_12_x86_64.whl` | `305e061fa82f4680607a775b2e8e0bcb071cd2205ac38e6ef48c8dd5ebe1cf37` |
| `openai-2.24.0-py3-none-any.whl` | `fed30480d7d6c884303287bde864980a4b137b60553ffbcf9ab4a233b7a73d94` |
| `pydantic-2.12.5-py3-none-any.whl` | `e561593fccf61e8a20fc46dfc2dfe075b8be7d0188df33f221ad1f0139180f9d` |
| `pydantic_core-2.41.5-cp312-cp312-macosx_10_12_x86_64.whl` | `f41a7489d32336dbf2199c8c0a215390a751c5b014c2c1c5366e817202e9cdf7` |
| `requests-2.34.2-py3-none-any.whl` | `2a0d60c172f83ac6ab31e4554906c0f3b3588d37b5cb939b1c061f4907e278e0` |
| `sniffio-1.3.1-py3-none-any.whl` | `2f6da418d1f1e0fddd844478f41680e794e6051915791a034ff65e5f100525a2` |
| `tqdm-4.67.1-py3-none-any.whl` | `26445eca388f82e72884e0d580d5464cd801a3ea01e63e5601bdff9ba6a48de2` |
| `typing_extensions-4.15.0-py3-none-any.whl` | `f0fa19c6845758ab08074a0cfa8b7aecb71c999ca73d62883bc25cc018c4e548` |
| `typing_inspection-0.4.2-py3-none-any.whl` | `4ed1cacbdc298c220f1bd249ed5287caa16f34d44ef4e9c3d0cbad5b521545e7` |

## Installation and inventory

Fresh environment identity: **NOT_CREATED**. The proposed repository-owned
path is `/Users/ian/.codex/worktrees/3a57/Memo/.local/phase08d9/runtime/.venv`; its parent does not exist. No wheelhouse, requirements
installation, dependency resolution, build, editable install or target pip check
ran. Installed inventory: **0 distributions**. Installed METADATA/WHEEL/RECORD,
ownership, isolation and pip-check results are **NOT_EXECUTED**, not PASS.
This phase has no Stage 2 installation receipt to confuse with D7's SDK runtime.

The [dependency manifest](../../manifests/phase-08d9-provider-boundary-dependencies.json)
contains the frozen plan, outcome, all 19 reuse checks, exact raw receipt/tool
hashes, and this **pinned planned inventory**, which is not an installed inventory:

| Distribution | Pinned version | Artifact outcome |
| --- | --- | --- |
| `aiohappyeyeballs` | `2.6.1` | ACQUIRED_VERIFIED |
| `aiohttp` | `3.14.3` | ACQUIRED_VERIFIED |
| `aiosignal` | `1.4.0` | REUSED_VERIFIED |
| `annotated-types` | `0.7.0` | REUSED_VERIFIED |
| `anyio` | `4.14.2` | REUSED_VERIFIED |
| `attrs` | `25.4.0` | ACQUIRED_VERIFIED |
| `certifi` | `2025.10.5` | REUSED_VERIFIED |
| `charset-normalizer` | `3.4.4` | REUSED_VERIFIED |
| `distro` | `1.9.0` | REUSED_VERIFIED |
| `frozenlist` | `1.8.0` | ACQUIRED_VERIFIED |
| `googleapis-common-protos` | `1.75.0` | ACQUIRED_VERIFIED |
| `greenlet` | `3.2.4` | STOPPED_HEADER_RELOCATION |
| `h11` | `0.16.0` | REUSED_VERIFIED |
| `httpcore` | `1.0.9` | REUSED_VERIFIED |
| `httpx` | `0.28.1` | REUSED_VERIFIED |
| `idna` | `3.15` | REUSED_VERIFIED |
| `jiter` | `0.12.0` | REUSED_VERIFIED |
| `json-repair` | `0.63.2` | NOT_REQUESTED |
| `multidict` | `6.7.0` | NOT_REQUESTED |
| `openai` | `2.24.0` | REUSED_VERIFIED |
| `opentelemetry-api` | `1.44.0` | NOT_REQUESTED |
| `opentelemetry-exporter-otlp-proto-common` | `1.44.0` | NOT_REQUESTED |
| `opentelemetry-exporter-otlp-proto-http` | `1.44.0` | NOT_REQUESTED |
| `opentelemetry-exporter-prometheus` | `0.65b0` | NOT_REQUESTED |
| `opentelemetry-proto` | `1.44.0` | NOT_REQUESTED |
| `opentelemetry-sdk` | `1.44.0` | NOT_REQUESTED |
| `opentelemetry-semantic-conventions` | `0.65b0` | NOT_REQUESTED |
| `prometheus-client` | `0.23.1` | NOT_REQUESTED |
| `propcache` | `0.4.1` | NOT_REQUESTED |
| `protobuf` | `7.35.1` | NOT_REQUESTED |
| `pydantic` | `2.12.5` | REUSED_VERIFIED |
| `pydantic-core` | `2.41.5` | REUSED_VERIFIED |
| `python-dotenv` | `1.2.2` | NOT_REQUESTED |
| `requests` | `2.34.2` | REUSED_VERIFIED |
| `sniffio` | `1.3.1` | REUSED_VERIFIED |
| `sqlalchemy` | `2.0.44` | NOT_REQUESTED |
| `tqdm` | `4.67.1` | REUSED_VERIFIED |
| `typing-extensions` | `4.15.0` | REUSED_VERIFIED |
| `typing-inspection` | `0.4.2` | REUSED_VERIFIED |
| `urllib3` | `2.7.0` | NOT_REQUESTED |
| `yarl` | `1.22.0` | NOT_REQUESTED |

## Focused controls and reproduction

[Preparation script](../../scripts/prepare_phase08d9_provider_boundary.py) and
[deterministic controls](../../scripts/test_phase08d9_dependencies.py) are new
Stage 2 tooling; upstream, Stage 1 and D7 code remain unchanged. First controls:
38 passed. Final controls: **39 passed, zero failures/errors**, including a
deterministic reproduction of the header-relocation STOP. Controls cover hash,
size, missing hash, changed source/plan, duplicate closure/ZIP/RECORD ownership,
metadata/version/tag/marker drift, extra dependencies, unsafe ZIP/installed paths,
symlinks, executable `.pth`, URL credentials/host/protocol/query, redirects,
timeout/no retry, request/byte limits, exclusive promotion/receipt collision and
native/SDK/socket/DNS denial before execution. These tests do not certify import
safety or the unexecuted installation path.

Preflight, diagnostics and controls use repository-owned `.venv`, `-I -B`, a clean
environment and `/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)'`.
The Python audit guard rejects native/SDK imports and socket/DNS events. Only
acquisition's exact curl requests were network-authorized. Future install/verify
actions are implemented to run their installer, target stdlib probe and pip check
under OS network denial with `--no-index --no-deps --require-hashes
--only-binary=:all: --no-cache-dir --no-compile`; these actions were not executed.
The current tool refuses output/acquisition reuse. **Do not rerun acquisition or
replace the frozen plan to work around STOP.** Review a controlled continuation
that verifies/reuses the six existing exact downloads and accounts for the 16
remaining requests, plus header relocation validation and installed ownership.

Raw wheels, environments and receipts remain ignored/outside Git. Public
dependency manifest SHA-256: `2ac0757b1c525fde914bf8258f180e86b7610391d3d23fb23d5b4516f0bdd87d`.
Only scripts, this report, manifests and project ledgers are published to the
review branch; no main merge or scientific execution is part of this closeout.

## Review and Stage 3 prerequisites

Independent review must resolve the verifier's greenlet header relocation mapping
and bounded continuation before acquisition resumes. Stage 2 then still needs
all 41 wheels verified/staged, a fresh independently identified isolated venv,
exact hash-locked offline installation, installed distribution/Requires-Dist and
RECORD verification, no unexpected ownership/executable `.pth`, and pip check.
Only after independent Stage 2 acceptance can a separately authorized Stage 3
observe normal imports under pre-import OS network denial, bind source/runtime
identities, audit allowed import effects and reject excluded modules/features.
Construction, native methods, SDK/provider networking, workers/services/models,
reference parity and startup remain separately excluded/unqualified.

Pinned upstream LICENSE bytes remain unavailable. No new engineered Hindsight
distribution was constructed, packaged, published, redistributed or installed.
Obtaining/verifying LICENSE remains separately authorized before packaging.
Native/SDK imports, provider construction, models, embeddings, databases, workers,
services, Jetstream, SSH, downstream/RQ3 and empirical actions are zero.
Unconditional runtime BLOCKED gate and scientific denominators/evidence remain
unchanged. Freeze v1 still hashes to
`0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b`;
Candidate10 NO_GO and OpenViking S0 r2 ERROR remain frozen.
**Stop for independent review. Retrieved != Authoritative.**
