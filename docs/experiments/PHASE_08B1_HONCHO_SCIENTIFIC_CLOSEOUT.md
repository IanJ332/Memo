# Phase 08B-1 Candidate10 scientific closeout

## Closeout decision

Phase 08B-1 Candidate10 is scientifically complete as a provider live
acceptance attempt with a frozen **NO_GO** provider decision.

| Field | Frozen value |
| --- | --- |
| Attempt | `20261007T165110Z-19d0ccd6b106` |
| Provider | Honcho 3.2.1 |
| Provider commit | `79cb31645f4efdef626d1bd9316a648adb5da89b` |
| Provider Git tree | `80e5aaa7104b3566aa88d55954340c4593cf9cd7` |
| Experiment base commit | `cb44f639642442b8277bc3cb2f6afb4b96d81307` |
| Stage A | PASS |
| Stage B | Completed operationally |
| Provider acceptance | NO_GO |
| Completion SHA-256 | `ca636f62ec87bfad5aa3e456a3584ed65f48bdb585d4747afce34bcbe1700f23` |
| Accepted review bundle SHA-256 | `43e63ce4632735ba30582a649a942f9dd98a31e33b241045c01d906120a4d5d9` |
| Required completion evidence | 23/23 independently verified |

This closeout preserves the observed result. It does not alter Experiment
Freeze v1, finalize Freeze v2, rerun Candidate10, or authorize Candidate11.

## Operational chronology

All timestamps below are UTC.

1. The managed controller session began at
   `2026-10-07T16:51:18.850775+00:00` from an initially shelved instance.
2. Stage A passed. It validated the pinned Honcho source/configuration and the
   provider-internal split model backends without scientific provider contact.
3. Stage B started the required Honcho services, contacted the native API,
   completed the authorized probes and direct S0 observation, performed the
   single authorized native Dream trigger, shut down the provider stack, and
   wrote `completion.json` at `2026-10-07T17:00:30.443178+00:00`.
4. The local controller remained inside the primary SSH subprocess until its
   5,400-second timeout. The earliest timeout inferred from controller-session
   start is `2026-10-07T18:21:18.850775+00:00`; therefore remote completion
   preceded that bound by at least 4,848.408 seconds.
5. The original controller recorded an operational `BLOCKED` result because
   it did not reach result parsing or copyback. Later read-only recovery proved
   remote completion and verified every required completion artifact.
6. The instance was returned to `SHELVED`; the owned floating IP was removed.

The controller transport failure and the provider acceptance result are
separate observations. The former does not convert the latter into a provider
failure, and the provider decision does not explain the transport timeout.

## Acceptance methodology and results

The provider gate classifies 18 frozen capabilities as `SUPPORTED`,
`UNSUPPORTED`, or `UNKNOWN`. `UNSUPPORTED` requires affirmative provider-
observed contradiction of a mandatory native requirement. `UNKNOWN` is
preserved when the frozen semantics were not proved, even when a superficially
related API operation exists. The deterministic gate produced `NO_GO`; no
manual override was applied.

### Capability classifications

| Classification | Count | Capabilities |
| --- | ---: | --- |
| SUPPORTED | 10 | create/write; deterministic or recorded ordering; exact provider-native IDs; exact raw-response capture; native rederivation/consolidation; provenance relationship edges; provider configuration pinning; provider version/commit pinning; restart persistence; retrieval |
| UNSUPPORTED | 4 | message-record hard deletion; revoke/invalidate; source-version transitions; temporal validity |
| UNKNOWN | 4 | async-completion quiescence proof; raw inspection under the frozen diagnostic semantics; restart reconstruction; update/supersede |

These are acceptance-gate classifications for the observed pinned provider
surface and run. They are not universal claims about every possible Honcho
deployment or future version.

### API-surface interpretation

The live OpenAPI surface exposes conclusion deletion. The frozen `hard_delete`
requirement, however, is specifically message-record hard deletion, and no
native message-record delete operation was exposed. Its classification remains
`UNSUPPORTED`. This evidence does **not** establish that all deletion in Honcho
is impossible.

The live surface also exposes a message `PUT` operation. Presence of that
operation does not prove the frozen lineage-aware update/supersession semantics,
so `update_supersede` remains `UNKNOWN` rather than being promoted to
`SUPPORTED` or demoted to `UNSUPPORTED`.

### Scenario classifications

| Scenario | Classification | Basis |
| --- | --- | --- |
| S0 | SUPPORTED | Direct provider-observed scenario execution |
| S1 | UNKNOWN | Not directly executed; requirements not fully resolved |
| S2 | UNSUPPORTED | Derived from provider-observed contradiction of a mandatory native capability |
| S3 | UNSUPPORTED | Derived from provider-observed contradiction of a mandatory native capability |
| S4 | UNSUPPORTED | Derived from provider-observed contradiction of a mandatory native capability |
| S5 | UNSUPPORTED | Derived from provider-observed contradiction of a mandatory native capability |

S2-S5 are four capability-derived classifications. They are **not** four
directly executed scenarios and must not be described as four failed scenario
runs.

## Quiescence findings

The explicit normal-deriver path is `SUPPORTED`. After its trigger, the native
queue showed new work, transition through pending/in-progress state, and then
the required stable empty observations.

The native Dream path is `UNKNOWN`. Its single authorized trigger returned
success, but all 60 bounded post-trigger queue observations were empty and
showed no new-work signal or counter transition. Consequently, the frozen
new-work-then-stable-empty criterion did not prove completion. This is a
quiescence-evidence limitation, not a Dream failure. The derived conclusion
and exact lineage remain evidence for the separately classified native
rederivation and provenance capabilities.

## Model-call accounting

Candidate10 recorded 21 provider-internal requests: 12 hosted text-generation
requests to the pinned `gpt-oss-120b` endpoint and 9 local embedding requests
using `sentence-transformers/paraphrase-MiniLM-L3-v2`. The text requests
recorded 19,554 input tokens and 1,479 output tokens. These calls are Honcho
provider behavior and are distinct from downstream authority decisions.

Downstream model calls were 0. RQ3 was not activated and RQ3 calls were 0.

## Reproducibility and evidence identity

The authoritative completion file matches the accepted SHA-256 above. All 23
artifacts declared by completion are present and match their declared hashes
and byte counts. The 27-member review bundle matches its accepted SHA-256.

The two provider evidence indexes resolve to 95 deduplicated primary paths:
80 provider raw responses, 3 adapter raw captures, 11 unique capability-
evidence paths, and 1 direct S0 scenario-evidence path. All 95 are present and
match their recorded SHA-256 values. Eighty-eight have a recorded byte-count
expectation and all 88 match it; the remaining seven probe-evidence artifacts
have no recorded byte expectation, so their actual byte counts are reported
without inventing an expected value.

The primary-evidence appendix preserves exact original bytes. No sanitized
derivative was substituted for an original. The indexed `provider-config.json`
was already redacted at source and is archived byte-for-byte in that redacted
form.

## Scientific interpretation

Candidate10 establishes that the pinned Honcho deployment can support the ten
listed native evidence and lifecycle capabilities, including exact identifiers,
raw capture, retrieval, persistence, and derived lineage. It also establishes
that the observed native API surface does not satisfy four mandatory lifecycle
requirements and leaves four other requirements unresolved. Under the frozen
gate, that evidence is sufficient for `NO_GO` provider acceptance.

The result is a provider-integration boundary finding, not evidence of a
security vulnerability. In the cross-provider lifecycle study it reinforces
the distinction between retrieval and authority: a provider can retrieve and
derive memory successfully while lacking native primitives needed to enforce
message-level deletion, invalidation, version transition, or temporal validity.
Provider-independent authority enforcement must therefore remain outside the
assumption that retrieved state is authoritative.

## Limitations

- The evidence describes Honcho 3.2.1 at one pinned commit and configuration;
  it is not a claim about all releases or deployments.
- Only S0 was directly executed as a scenario. S2-S5 are derived
  classifications, and S1 remains unknown.
- Native Dream quiescence remains unknown under the frozen criterion despite
  60 exact bounded observations; this must not be rewritten as a failure.
- Raw inspection, restart reconstruction, and update/supersede remain unknown
  under their frozen semantics.
- The protected Redis dump and broader provider-state database contents were
  neither read nor archived. They are not required completion evidence.
- Provider-root inspection was metadata-only and did not establish a complete
  log archive.
- The exact transport mechanism that prevented SSH EOF/result delivery after
  remote completion is unknown.

## Transport root-cause status

`UNKNOWN`. The supported failure locus is the local controller waiting inside
the primary SSH call after remote completion had already been written. No
evidence identifies an inherited handle, blocked remote-Python exit path, or
specific SSH/session defect. Controller hardening recommendations are recorded
separately and were not implemented during this closeout.
