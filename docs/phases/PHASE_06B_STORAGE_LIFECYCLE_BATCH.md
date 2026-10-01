# Phase 06B — Frozen Storage/Lifecycle Batch

## Status

Phase 06B is **BLOCKED** before experimental execution. Exactly one authorized
managed Jetstream2 lifecycle was used. No provider service started, no
experimental namespace ran, and no downstream or RQ3 decision model was
called.

The prepared and tested live commit was
`d7e9814171f755d749dc03d9fff965fbaa13fe3d`, on
`phase-06b-storage-batch`, based on
`f11a57b27467d8012ef36520f931f281d1b61486`.

## Frozen preflight blocker

The local freeze validator passed and the local working-tree bytes at
`experiments/freeze/experiment-freeze-v1.json` had the required SHA-256:

`0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b`

The exact remote Git sync completed, but the first remote batch gate computed:

`6b41176154070dd8c58db24a5c5adfe5365e39d0c31408c033019e7d6108b3c9`

No experiment ran after that mismatch. Local byte inspection established that
the required hash is the canonical JSON with CRLF line endings, while the Git
blob and ordinary Linux checkout use LF line endings and produce the remote
hash. This is an exact-byte checkout blocker, not a semantic freeze change or
provider result.

A repository-scoped `.gitattributes` rule now requests CRLF checkout only for
the frozen JSON. The freeze file itself was not modified. This repair has not
been live-tested because a second Jetstream lifecycle was not authorized.

Local repair validation used four isolated no-local clones. At the prepared
commit, `core.autocrlf=true` produced the required CRLF hash while
`core.autocrlf=false` with `core.eol=lf` reproduced the remote LF hash. At the
repaired commit, both configurations produced 15,274-byte files with 413 CRLF
line endings and the required `0e02a8...49b` SHA-256. The repository's local
and global settings are unset; Windows Git's system-level `core.autocrlf=true`
explains the original local conversion. The exact remote Git setting was not
captured, but its checkout behavior was unambiguously no-CRLF conversion.

## Planned coverage

The plan was generated only from Freeze v1 and is tracked at
`artifacts/phase06b/planned-runs.json`.

- Supported provider/scenario cells: 14
- Unsupported cells: 4
- Repetitions per supported cell: 3
- Planned supported repetitions: 42
- Order: provider, scenario, repetition
- Executed repetitions: 0
- Blocked/not executed repetitions: 42

The unsupported cells remain capability facts: Mem0 S4/S5 and OpenViking
S1/S5. No substitute operation was executed.

## Provider runtime validation and outcomes

Provider environment and semantic-configuration validation did not run because
the freeze byte gate precedes provider startup. Mem0 2.2.1, Hindsight 0.10.1,
and OpenViking 0.4.22 therefore each have zero executed repetitions and no
scientific exact-visibility or authority-exposure outcomes. No raw-run,
aggregate, or residual-index artifact was generated, and no residual candidate
count can be inferred.

The local preparation verified the frozen configuration-hash evidence:

- Mem0: `23c068e16db7d4bb90aad7755b997d5a4104c433a4a0083ef43b3506680ff2e8`
- Hindsight: `baca300bdce174d8cb2d00fa576df73d0cf5c4f9230aed370d2767bd35f4d73d`
- OpenViking: `ad1216520de78aa6dd6fe0c34393e3830b05b035aa7dda367d92725dafe53258`

## Local gates

- Focused Phase 06B tests: 10 passed
- Unit: 152 passed
- Contract: 6 passed
- Integration: 6 passed, 1 expected live-Hindsight skip
- Mem0 regression: 5 passed
- Hindsight regression: 11 passed, 1 expected live-service skip
- OpenViking regression: 52 passed
- Phase 03 regression: 21 passed
- Phase 03B regression: 13 passed
- Freeze validator: PASS locally
- Freeze file diff: none

## Managed lifecycle and cleanup

The lifecycle began with `jisheng3` (`5baeeae7-4c29-4903-89fe-2e9df0a8eced`)
SHELVED. It unshelved the VM, created and associated one owned temporary
floating IP, verified `/dev/sdb` at `/media/volume/jisheng3_volume`, synchronized
the exact prepared commit, and stopped at the remote freeze hash gate.

The controller then disassociated and deleted the owned floating IP, shelved
the VM, and verified the final state as SHELVED. A separate read-only status
check independently confirmed SHELVED with no address. No run-owned provider
service needed cleanup because none started. Persistent state and model caches
were retained. No second lifecycle was attempted.

Downstream decision calls and RQ3 calls were both zero. The provider-internal
Hindsight and OpenViking models were not invoked.
