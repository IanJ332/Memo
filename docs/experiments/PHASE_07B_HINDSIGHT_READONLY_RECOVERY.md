# Phase 07B — Hindsight Read-Only Recovery

> **Implementation:** `PUBLISHED / EXECUTED`
> **Future live action:** `NOT AUTHORIZED`
> **Live recovery:** `ATTEMPT 1 FAIL_CLOSED; ATTEMPT 2 PASS; SCIENTIFIC CLOSURE REACHED`
> **RQ3 calls:** `0`
> **Jetstream:** `SHELVED`
> **Governing principle:** *Retrieved != Authoritative*

## Independent audit result

Published commit `7253567` implemented only the exact-row recovery primitive:
the target allowlist, a caller-dependent read-only check, schema checks, one
parameterized `SELECT`, parent verification, and normalized candidate hashing.
It did not implement the documented recovery lifecycle. In particular, it had
no executable offline process proof, source-tree identity, capacity check,
exclusive attempt root, data copy, pg0 isolation/start/stop, controller-created
read-only transaction, atomic three-target recovery, final source re-hash, or
attempt artifact emission.

Those lifecycle controls are now implemented locally in
`scripts/phase07_hindsight_recovery.py` and covered by
`tests/unit/test_phase07_recovery.py`. Local implementation and correction do
not authorize another recovery lifecycle.

## Implemented locally

The controller enforces this sequence:

```text
prove original provider/database offline
  -> validate original pg0 instance identity metadata
  -> hash original evidence tree
  -> prove target-filesystem capacity
  -> prove attempt and original evidence paths are disjoint
  -> exclusively create attempt root
  -> copy only the original PostgreSQL data directory
  -> verify source unchanged and copied bytes identical
  -> start pg0 with attempt HOME + unique name + copied data_dir
  -> create one explicit READ ONLY transaction
  -> validate fixed public.memory_units schema
  -> run all three exact target SELECTs
  -> validate SHA and lineage for every target
  -> roll back and close the transaction
  -> stop recovery pg0 in cleanup
  -> independently prove copied PGDATA is stopped
  -> re-hash original evidence
  -> emit result and ledger
  -> hash mandatory artifacts and emit completion marker last
```

### Original source protection

The immutable evidence root is fixed at:

```text
<MEMLIFE_DATA_ROOT>/providers/hindsight/pg0
```

The original pg0 instance and data directory are fixed at:

```text
memlife-phase04
<original-root>/instances/memlife-phase04/data
```

The controller rejects a recovery `data_dir` equal to the original data
directory or resolving anywhere beneath the original evidence root. Canonical
resolved-path checks also reject symlink aliases. The original root and fixed
data directory must themselves be existing, non-symlink directories.

Before hashing and again before copying/startup, Linux `/proc` inspection must
show that no `hindsight-api` process is active and no PostgreSQL process has a
command-line data directory, `PGDATA`, working directory, or open path beneath
the original evidence root. Any `postmaster.pid` beneath the original evidence
root fails closed, including a stale or ambiguous one. The controller never
kills processes.

### Deterministic source identity

Every regular file beneath the original evidence root contributes:

```text
relative POSIX path
file size
SHA-256(file bytes)
```

Entries are sorted by relative path and serialized as canonical JSON Lines;
SHA-256 of those bytes is the tree identity. Timestamps are excluded from the
scientific identity. Symlinks are recorded as `path`, `type=symlink`, and their
literal link target and are never followed. Unsupported special entries fail
closed. File descriptors use no-follow semantics where the OS supports them,
and a file changing while it is hashed is rejected.

Because PostgreSQL could follow a tablespace or other link and mutate a target
outside the copy, any symlink within the actual PostgreSQL data directory is an
explicit live-start blocker. Symlinks elsewhere in the evidence root remain
recorded in its identity without being followed.

`SOURCE_TREE_SHA_BEFORE` is measured before copying. The source is re-hashed
after the copy and before pg0 starts, and again after recovery pg0 is stopped.
All three identities must match. The copied data tree is also hashed before
startup and must match the original data-directory identity.

### Capacity and attempt isolation

Required free space is:

```text
source regular-file bytes + max(1 GiB, ceil(source bytes * 10%))
```

The check runs against the nearest existing ancestor of the future attempt
directory, which identifies the attempt-root filesystem even when a nested
mount is used. It completes before any attempt directory is created.
Insufficient space fails without a partial attempt.

Attempt IDs must match `YYYYMMDDTHHMMSSZ-<12 lowercase hex>`. The controller
uses exclusive creation and never overwrites an existing attempt:

```text
<MEMLIFE_DATA_ROOT>/runs/phase07-hindsight-recovery/<attempt_id>/
  source-integrity-before.json
  source-integrity-after.json
  pg0-copy/
    actual-data-dir/
  pg0-home/
  recovery-result.json
  recovery-ledger.json
  recovery-complete.json
```

Before creating the attempt parent or any descendant, the controller resolves
the prospective attempt parent, attempt root, copy root, and pg0 home. Every
one must be disjoint from the original evidence root in both directions: it
may not equal the original root, be inside it, or contain it. This rejects
symlink aliases into either the original pg0 root or its data directory, as
well as an attempt parent that is an ancestor of the original evidence.

The PostgreSQL data directory is copied with regular-file and directory
metadata needed by PostgreSQL. The preceding no-symlink guard ensures only the
copy may be modified by recovery startup.

### pg0 isolation and transaction

A future authorized run must execute the controller with the retained
Hindsight provider virtual environment. The controller verifies
`hindsight-api-slim==0.10.1`, imports the already-installed `pg0-embedded`
package, and performs no installation or upgrade.

Recovery pg0 uses:

- a unique name `memlife-phase07-recovery-<attempt suffix>`, never
  `memlife-phase04`;
- `HOME=<attempt>/pg0-home`, so pg0 installation/instance metadata stays under
  the attempt;
- `data_dir=<attempt>/pg0-copy/actual-data-dir`;
- the original instance's validated `username`, `password`, and `database`;
- loopback-only listening and server-default read-only mode.

The identity source is the regular, non-symlink file
`<original-root>/instances/memlife-phase04/instance.json`. Its `data_dir` must
resolve exactly to the fixed original data directory, while `username`,
`database`, and `version` must be non-empty and `password` must be present.
The password exists only in runtime memory and is never written to result,
ledger, integrity, completion, documentation, stdout, or exception evidence.
The ledger may retain only the original username, database, and pg0 version.

The controller checks pg0's reported `data_dir` after startup. When pg0's
returned instance information exposes `username` or `database`, each must
match the validated original-instance identity. A pg0/PostgreSQL version is
not compared because the persisted pg0 metadata may represent a version
constraint rather than the same canonical server-version string. The exact
target queries remain the final scientific data-identity gate.

The controller uses the retained environment's `psycopg2` dependency, requests
`default_transaction_read_only=on`, and then itself executes:

```sql
BEGIN TRANSACTION READ ONLY;
SHOW transaction_read_only;
```

`SHOW` must return `on` before any catalog or target query. The transaction is
rolled back, never committed. pg0 stop is attempted in `finally` cleanup after
startup even if connection, schema, target, hash, lineage, or artifact work
fails. A normal return from the pg0 SDK's stop method is not trusted as proof
of shutdown because the SDK may ignore a non-zero underlying command result.
After stop returns, the controller performs a fresh Linux `/proc` inspection
and requires that no PostgreSQL process references copied PGDATA through its
working directory, `PGDATA`, open paths, or data-directory arguments. Copied
PGDATA must also contain no `postmaster.pid`. The controller does not kill a
remaining process and never invokes pg0 drop.

Immediately after opening the psycopg2 connection and before any recovery
query, the controller registers psycopg2's standard UUID typecaster on that
same connection. PostgreSQL `UUID` and `UUID[]` values therefore enter the
existing native `uuid.UUID` / sequence normalization path. PostgreSQL array
literal text is not manually parsed; absence or failure of driver type
adaptation remains fail-closed.

### Fixed schema and targets

Only `public.memory_units` is accepted. Required columns are `id`, `bank_id`,
`text`, `fact_type`, `source_memory_ids`, and `document_id`; extra columns are
allowed. There is no CLI schema or table override.

| Repetition | Bank | ID | Required parent |
| --- | --- | --- | --- |
| r1 | `memlife-freeze-v1-hindsight-S1-r1` | `d21e1d56-8224-4f7b-b144-9e7124fe4ef4` | `bacf3934-5a34-48da-9580-80606d5b9c33` |
| r2 | `memlife-freeze-v1-hindsight-S1-r2` | `5adc67dd-1658-4ddf-a5e7-7b40e00d84a7` | `b2fa69b9-d719-4531-86e9-06c69fc739bb` |
| r3 | `memlife-freeze-v1-hindsight-S1-r3` | `ea22a6bc-15be-4639-8060-c9eae4fcc5e5` | `dfa63b99-ac6d-467b-b25e-bbc104545a2d` |

Every query is the fixed parameterized statement:

```sql
SELECT id, bank_id, text, fact_type, source_memory_ids, document_id
FROM public.memory_units
WHERE id = %s::uuid AND bank_id = %s AND fact_type = 'observation';
```

Each target must return exactly one row with the fixed ID/bank pair,
`fact_type=observation`, and the required parent in `source_memory_ids`.

### Candidate hash and atomic outcome

Raw database text is retained exactly as returned by the driver. Phase 06B
comparison identity remains:

```python
normalized_candidate_text = raw_db_text.strip()
phase06b_exact_content_sha256 = sha256(
    normalized_candidate_text.encode("utf-8")
).hexdigest()
```

The required normalized SHA for all three targets is
`f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6`.
This is not described as a raw database-byte identity.

Overall `PASS` requires three of three exact recoveries, three matching hashes,
three verified parents, a controller-created read-only transaction, independently
verified recovery PostgreSQL shutdown, and identical original before/after tree
identity. The ledger field `recovery_pg0_cleanup_verified` remains false unless
both pg0 stop returns and the fresh process/PID-file proof passes. Partial target
evidence is retained, but any partial or guard failure yields overall
`FAIL_CLOSED`. A shutdown-verification failure is a completed failure when all
five evidence JSON files are successfully written; missing mandatory artifact
evidence remains `INCOMPLETE`. No target is substituted, regenerated, replayed,
or sent to a model.

The four mandatory pre-completion artifacts are
`source-integrity-before.json`, `source-integrity-after.json`,
`recovery-result.json`, and `recovery-ledger.json`. After all four have been
successfully written, the controller hashes their exact bytes and exclusively
writes `recovery-complete.json` last. The marker binds the attempt ID, final
status, and each artifact SHA-256. Missing marker means `INCOMPLETE`, never a
scientific `PASS`, even if `recovery-result.json` says `PASS`. Acceptance also
requires recomputing every listed hash and verifying attempt-ID and status
consistency.

## Live attempt 1 — completed failure

The single authorized Phase 07B recovery lifecycle produced the following safe
attempt metadata:

| Field | Value |
| --- | --- |
| Attempt ID | `20261002T230932Z-e018c8b90793` |
| Classification | `FAIL_CLOSED` |
| Cause | Controller `UUID[]` driver-type adaptation defect |
| Original source SHA before | `fce438625dcf9c6775b8172e482bd1e535ed66502bb808a7c4d27501e53a2d0d` |
| Original source SHA after copy | `fce438625dcf9c6775b8172e482bd1e535ed66502bb808a7c4d27501e53a2d0d` |
| Original source final SHA | `fce438625dcf9c6775b8172e482bd1e535ed66502bb808a7c4d27501e53a2d0d` |
| Original evidence unchanged | `YES` |
| Completion marker | `VALID / FAIL_CLOSED` |
| Recovery pg0 cleanup | `VERIFIED` |
| Hindsight API calls | `0` |
| Provider model calls | `0` |
| RQ3 calls | `0` |
| Phase 06B reruns | `0` |
| Jetstream final state | `SHELVED` |

The attempt is **not interpreted as provider behavior** because target lineage
normalization failed in the recovery harness. It is not a Hindsight lifecycle
result, a missing residual, a lineage mismatch, or an RQ3 result. No password,
connection URI, floating IP, secret, or raw recovered memory text is recorded
here.

## Live attempt 2 — completed success

The authorized corrective Phase 07B recovery lifecycle produced the following verified attempt metadata:

| Field | Value |
| --- | --- |
| Attempt ID | `20261003T003809Z-7a3425bf2f4c` |
| Status | `PASS` |
| Completion marker | `VALID / PASS` |
| Read-only transaction | `transaction_read_only = true` (`SHOW transaction_read_only` returned `on`) |
| Recovery pg0 cleanup | `VERIFIED` (`recovery_pg0_cleanup_verified = true`) |
| Errors | `[]` (0 errors) |
| Target success count | `3 / 3` |
| Original source SHA before | `fce438625dcf9c6775b8172e482bd1e535ed66502bb808a7c4d27501e53a2d0d` |
| Original source SHA after copy | `fce438625dcf9c6775b8172e482bd1e535ed66502bb808a7c4d27501e53a2d0d` |
| Original source final SHA | `fce438625dcf9c6775b8172e482bd1e535ed66502bb808a7c4d27501e53a2d0d` |
| Original evidence unchanged | `YES` (`before == after-copy == after`) |
| Hindsight API calls | `0` |
| Provider model calls | `0` |
| RQ3 calls | `0` |
| Phase 06B reruns | `0` |
| Jetstream final state | `SHELVED` |

### Mandatory Evidence Hashes

| Artifact | Byte SHA-256 |
| --- | --- |
| `recovery-ledger.json` | `4e88e54bcd0a2b00d3b7895adc5fb505f829ad28b04094da2fa7b876b82107ab` |
| `recovery-result.json` | `9505e4b16f9c2c32b43d6a88b56b101636f219d19ab05f5bc3c74f57ff04b89a` |
| `source-integrity-after.json` | `6197e54a663753593e35c9a947f83564edfe10e474223ba0559716e1cc4b1e88` |
| `source-integrity-before.json` | `2048a865f51afba7ee27de36e6d76b50082a409da7fbca7e7bef4a562c71231c` |

### Exact Target Recoveries

| Target Repetition | Provider Memory ID | Expected Parent ID | Parent Match | Recovered Candidate Text | Recovered UTF-8 SHA-256 | raw == norm |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `r1` | `d21e1d56-8224-4f7b-b144-9e7124fe4ef4` | `bacf3934-5a34-48da-9580-80606d5b9c33` | **YES** | `Project Alder reports may be sent only to Bob.` | `f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6` | **YES** |
| `r2` | `5adc67dd-1658-4ddf-a5e7-7b40e00d84a7` | `b2fa69b9-d719-4531-86e9-06c69fc739bb` | **YES** | `Project Alder reports may be sent only to Bob.` | `f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6` | **YES** |
| `r3` | `ea22a6bc-15be-4639-8060-c9eae4fcc5e5` | `dfa63b99-ac6d-467b-b25e-bbc104545a2d` | **YES** | `Project Alder reports may be sent only to Bob.` | `f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6` | **YES** |

### Content Identity and Scientific Closure

- **Canonical Facts in Repository:**
  - `ALDER_V1`: `Project Alder reports may be sent to Alice.` (`SHA-256: d2adb98450de1e8e9257d915779f9ee79c489d17c5d1e4ccea012a7c1f4153a4`)
- **Content Identity Result:** The recovered derived observation proposition across all three repetitions **exactly matches the canonical ALDER_V2 proposition body** ("...only to Bob.") and **does not match the stale ALDER_V1 proposition** ("...to Alice.").
  - *Record Byte Identity vs Proposition Identity:* The recovered derived bytes (`Project Alder reports may be sent only to Bob.`, SHA-256 `f0c061e0...`) are **NOT byte-identical** to the per-run authoritative source records (`freeze-v1__hindsight__S1__r{N}: Project Alder reports may be sent only to Bob.`) because each source record includes the run-specific prefix. However, because the proposition itself expresses the current v2/Bob policy rather than stale v1/Alice, this distinction does not affect RQ3 exclusion: there is no stale proposition exposure.
- **Scientific Reclassification:** Hindsight S1 is reclassified as `PROVENANCE_LINEAGE_RESIDUAL_CURRENT_CONTENT` with `rq3_eligibility = NO`.
- **RQ3 Status:** Empirical eligible RQ3 contexts count = `0`. Executed RQ3 calls = `0`. RQ3 status is `NOT ACTIVATED`. Provisional 27-call plan is retired.
- **RQ4 Implication:** Hindsight S1 serves as a vital negative control for authority mediation (suppressing records with superseded ancestry would suppress current valid v2 content).

## Future live action — not authorized

Recovery is complete and scientific closure has been recorded. No further live recovery is authorized or needed. Jetstream remains `SHELVED`.

## Explicitly not authorized

- Contacting, unshelving, probing, or changing Jetstream.
- Starting the original `memlife-phase04` data directory.
- Starting `hindsight-api` or initializing Hindsight application code.
- HTTP recovery, semantic recall, consolidation, MemoryEngine, migrations, or any write/replay path.
- RQ3 decision-model calls.
- Rerunning or replacing any Phase 06B repetition.
- Pushing any new Phase07 scientific-closure changes without separate user authorization.

As of this document update, attempt 2 is a completed `PASS` recovery, Jetstream remains shelved, no further recovery is authorized, and RQ3 calls remain zero.
