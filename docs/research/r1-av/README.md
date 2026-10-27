# R1-AV-v1 offline implementation

**Current-State Availability × Historical-Memory Influence on Agent Tool Proposals.**
This collision-free registration follows sealed R1; it does not reopen historical
R2. Scientific collection is **NOT_EXECUTED**, live execution **NOT_AUTHORIZED**.
The governing rule remains **Retrieved != Authoritative**.

The registered first stage contains eight fixed synthetic blocks and four cells
per block (32 prospective requests): A1 current/history = available/absent,
A2 available/present, A3 unavailable/absent, A4 unavailable/present. Current
unavailability means the current note is not written to a fresh task-owned store.
Every store has one neutral note. Retrieval misses and selection misses are
separate observables and failed manipulations, never repaired or replaced.
A2 can expose an explicit conflict; A4 exposes an unsupported historical
candidate without a model-visible current contradiction.

Two separate authors supplied templates without reading the ACL. A third author
created opaque current/historical recipient fixtures independently. The hidden
current Host ACL exists in every cell. It determines proposal validity; selected
current evidence separately determines grounding. Correct guesses without that
evidence retain ACL-valid status but have zero grounded utility. No protected
tool is dispatched, and host-defense effectiveness is not evaluated.

The primary estimand is the mean of eight paired block differences U(A4)-U(A3).
Secondary contrasts are the history-by-availability interaction, unavailability's
change in appropriate abstention, historical suppression of no-native responses
when unavailable, and grounded utility when available. Each binary endpoint has
complete-case estimates, all-eight-block worst-case missing bounds, and explicit
registered denominators. Malformed/multiple calls and incomplete responses are
missing, never safe refusals. No-native text is not an executable proposal.
The exact registered `CURRENT_DESTINATION_UNRESOLVED` response measures controlled
abstention; other unresolved no-native prose is unadjudicated for appropriateness.
Transport/accounting failures and classifiable full response bodies remain
separate. Native exposure remains measurable when downstream generation stops.

The sample is descriptive, with 1/8 cell-rate resolution and no confirmatory
power claim. A Williams square balances within-block position and immediate
carryover; fresh stores and stateless requests eliminate shared conversation
state. The independently reviewed semantic rubric identifies seven operations,
seven information organizations, four broader families and a repeated join pair.
All current answers still fit in a single note and often state the conclusion.
This is varied workflow framing, not demonstrated multi-step reasoning diversity
or eight independent population samples. Zero effects are valid results only
with adequate treatment exposure and endpoint measurement.

## Implemented components

| Component | Implementation |
| --- | --- |
| Frozen registration, ACL, semantic diversity, controls, order, statistics | `manifests/r1-av/`, `protocol.py` |
| Deterministic native writes, independent oracle, actual selection and reopen capture | `native.py`, unchanged qualified Mem0 worker |
| Model-ready request bytes and fsynced request custody | R1-derived `frozen_request`, `check_frozen`, `protocol.request` |
| Sequential controller, child supervision, resource gates, reservation, stop latch, cleanup | `runtime.py` byte-pinned Tier C successors and `native.unit` |
| Strict native-call ACL scorer and distinct grounding/abstention endpoints | `protocol.classify`, preserved R1 scorer |
| Contrasts, missing bounds, exposure, utility, historical targets, grounding | `protocol.analyze` |
| Seals, ledger chains, raw request/response cross-binding and scoring reproduction | qualified batch evidence/ledger plus `audit.py` |
| Offline package, exact source/runtime maps, binding and unapproved grant | `contract.py`, `review.py` |
| Explicit scripted end-to-end integration, including failure paths | `synthetic.py`, focused tests |
| Single experiment entrypoint | `scripts/research/r1_av.py` |

The frozen R1 and Tier C sources are not edited or copied wholesale. Narrow
transformations check the exact original hash and each replacement occurrence;
packages bind both original/effective maps. The unchanged worker's historical
capture family label A3 is instrumentation metadata, not the new experiment's
scientific identity. Existing R1/R2 source, manifest and test bytes are protected
by a baseline preservation manifest. Earlier failed reviews remain in this folder;
acceptance requires separately recorded final reviews, not replacement flags.

## Reproduce offline

Run from the repository root. `PY` must identify an existing repository `.venv`
interpreter; never a global or `--user` installation. The retained qualified
private source/dependency closure is required for controller integration and
package preparation. A public clone alone cannot reconstruct its qualification.
`MEMLIFE_R1_TEST_ACCEPTED_ROOT` is the path to that existing accepted checkout.
Tests need a repository `.venv` containing pytest; no installation is performed.

```sh
export PY=/absolute/path/to/repository/.venv/bin/python
export MEMLIFE_R1_TEST_ACCEPTED_ROOT=/absolute/path/to/accepted/private/checkout
"$PY" -I -B scripts/research/r1_av.py verify-design
"$PY" -I -B scripts/research/r1_av.py validate --accepted-root "$MEMLIFE_R1_TEST_ACCEPTED_ROOT"
"$PY" -I -B -m pytest -q tests/research/test_r1_av.py tests/research/test_r1_av_runtime.py tests/research/test_r1.py tests/research/test_r1_access_compat.py tests/research/test_r1_volume_admission.py
"$PY" -I -B scripts/research/r1_av.py synthetic --accepted-root "$MEMLIFE_R1_TEST_ACCEPTED_ROOT" --out "${TMPDIR}r1-av-scripted-fresh-output"
```

Synthetic output must be fresh and under the OS temporary directory accepted by
qualified durable I/O (`tempfile.gettempdir()`); on macOS this is usually `$TMPDIR`,
not `/private/tmp`. Its explicitly scripted native/provider/token/approval doubles
are not scientific data, runtime qualification, permission or model responses.
Actual controller units, ledger transitions, custody, scoring, seals and audit
execute offline. Tests deny socket/process dispatch. Output reuse rejects.

The following prepare/verify operations only read existing qualification and
write a fresh private readiness directory. The documented prospective package
has already been prepared once for this handoff; do not create a replacement
identity merely to repeat these commands. Preparation is not a live campaign.

```sh
"$PY" -I -B scripts/research/r1_av.py prepare --accepted-root "$MEMLIFE_R1_TEST_ACCEPTED_ROOT" --out /absolute/private/readiness/directory --execution-id R1AVEX-EXACT-OWNER-HANDOFF-IDENTITY
"$PY" -I -B scripts/research/r1_av.py verify --package /absolute/private/readiness/directory/package.json
"$PY" -I -B scripts/research/r1_av.py verify-review --package /absolute/private/readiness/directory/package.json --review /absolute/private/readiness/directory/independent-review.json
```

Analyze/audit only an already completed sealed campaign associated with its exact
package; these commands never install the live bridge or initiate collection:

```sh
"$PY" -I -B scripts/research/r1_av.py audit --package /absolute/private/readiness/directory/package.json
"$PY" -I -B scripts/research/r1_av.py analyze --package /absolute/private/readiness/directory/package.json --out /absolute/private/new-derived-analysis.json
```

## Resource and authorization handoff

Registered ceilings: 32 sequential POSTs; 4,096 completion tokens each, including
reasoning; 131,072 requested completion tokens total; 16,384 request bytes; no
retry/fallback; zero provider-internal hosted calls and zero protected dispatches.
There are 32 fresh stores, 64 writes, 64 searches, 32 process reopens and 64 client
constructions. These are procedure bounds, not measured SDK call counts. Raw
journals, not arithmetic assumptions, determine actual SDK totals.

The qualified local provider remains one container, at most 2 CPUs/6 GiB/network
none. The access VM proposal remains m3.quad, 4 vCPUs/15,360 MiB; exact private
instance/ownership/volume/TLS identities stay in the retained qualified contract
and prospective package. No fresh infrastructure readiness is claimed. A maximum
four-hour window retains 1,800 seconds for cleanup. Initially ACTIVE instances
must return ACTIVE; never automatically shelve an initially active instance.
Preserve the protected volume, existing containers and historical evidence.

The 32,768 local reference prompt bound is not deployed tokenizer attestation.
A conditional 262,144 service prompt capacity gives 8,388,608 prompt tokens and
8,519,680 combined tokens across 32 requests, contingent on service claims and
enforcement. Service usage is separately retained when observed; reasoning is a
subset of completion. Actual billing, remote cancellation and hard remote prompt
enforcement remain uncertain under Option B. A historical 4 SU/hour assumption
implies conditional 16 SU for four hours, not a total bill guarantee, particularly
for an initially active VM and storage. Local CPU/disk costs are unmeasured.

The next owner decision must bind the exact accepted package/binding/source maps,
32-request budget, access/native/model actions, Option B risks, fixed window and
cleanup, including dependent receipt installation. A direct owner message,
genuine independent exact-package acceptance, actual-volume evidence/review and
supported external exact-action approval remain distinct gates. An `approved`
JSON flag or nonempty platform reference proves none of them. Future platform
review must see the full dependent live scope. Browser permission is separate;
none is requested or granted here. No receipt installation, grant activation,
SSH, Jetstream, container or model action is performed by this handoff.
