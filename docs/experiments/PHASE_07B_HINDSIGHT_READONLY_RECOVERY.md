# Phase 07B — Hindsight Read-Only Recovery

> **Implementation:** `IMPLEMENTED LOCALLY`
> **Future live action:** `NOT AUTHORIZED`
> **Live recovery:** `NOT EXECUTED`
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
`tests/unit/test_phase07_recovery.py`. This local implementation does not
authorize or perform recovery.

## Implemented locally

The controller enforces this sequence:

```text
prove original provider/database offline
  -> hash original evidence tree
  -> prove target-filesystem capacity
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
  -> re-hash original evidence
  -> emit result and ledger
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
```

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
- loopback-only listening and server-default read-only mode.

The controller checks pg0's reported `data_dir` after startup. It uses the
retained environment's `psycopg2` dependency, requests
`default_transaction_read_only=on`, and then itself executes:

```sql
BEGIN TRANSACTION READ ONLY;
SHOW transaction_read_only;
```

`SHOW` must return `on` before any catalog or target query. The transaction is
rolled back, never committed. pg0 stop is attempted in `finally` cleanup after
startup even if connection, schema, target, hash, lineage, or artifact work
fails. The controller never invokes pg0 drop.

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
three verified parents, a controller-created read-only transaction, successful
pg0 cleanup, and identical original before/after tree identity. Partial target
evidence is retained, but any partial or guard failure yields overall
`FAIL_CLOSED`. No target is substituted, regenerated, replayed, or sent to a
model.

## Future live action — not authorized

No live command in this document is authorized by publication of the local
controller. A separate execution prompt would have to authorize a managed
Jetstream lifecycle and identify the exact published commit to test. Only then
could an operator:

1. verify Jetstream and persistent-volume state under the managed lifecycle;
2. run the controller with the retained Hindsight provider interpreter and a
   new attempt ID;
3. retrieve the complete attempt directory without rewriting it;
4. clean up only resources owned by that authorized lifecycle; and
5. return Jetstream to `SHELVED` if that lifecycle opened it.

## Explicitly not authorized

- Contacting, unshelving, probing, or changing Jetstream.
- Starting the original `memlife-phase04` data directory.
- Starting `hindsight-api` or initializing Hindsight application code.
- HTTP recovery, semantic recall, consolidation, MemoryEngine, migrations, or
  any write/replay path.
- RQ3 decision-model calls.
- Rerunning or replacing any Phase 06B repetition.
- Pushing the local implementation commit.

As of this document update, live recovery has not run, no recovery artifact
contains empirical target text, Jetstream remains shelved, and RQ3 calls remain
zero.
