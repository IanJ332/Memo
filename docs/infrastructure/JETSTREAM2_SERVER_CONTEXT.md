# Jetstream2 Server Context

Last verified: 2026-09-28 by the Phase 02B-0 automated live acceptance cycle.

## Sanitized identity and compute

- Platform: Jetstream2 / Exosphere
- Allocation/project: `CIS261698`
- Instance: `jisheng3`
- Server UUID: `5baeeae7-4c29-4903-89fe-2e9df0a8eced`
- Flavor: `m3.small`
- Compute: 2 vCPU, approximately 5.78 GiB RAM, no GPU
- OS: Ubuntu 24.04.x
- Remote user: `exouser`
- Repository: `/home/exouser/Memo`
- DNS hostname: `jisheng3.cis261698.projects.jetstream-cloud.org`

Numeric public addresses are ephemeral and are released while the instance is
shelved. Never store or hardcode one. Query OpenStack networking on every run,
provision a dedicated temporary floating IP when no association exists, and
return a run-owned IP before shelving.

## Persistent storage

The durable identity is the block device `/dev/sdb`, not a mount directory.
Always resolve its current mount dynamically:

```sh
actual_mount="$(findmnt -n -o TARGET /dev/sdb)"
runtime_root="${actual_mount}/memlife"
```

The 2026-09-28 live probe resolved `/dev/sdb` to
`/media/volume/jisheng3_volume`, reported `49G` capacity, and derived
`/media/volume/jisheng3_volume/memlife` as the MemLife data root. A future live
`findmnt` result supersedes this cached value.

Do not format, detach, or migrate `/dev/sdb` as part of lifecycle automation.
Phase 02B-0 did not create provider data or the derived MemLife directory.

## Runtime and safety policy

Keep source and lightweight configuration under `/home/exouser/Memo`. Put
datasets, model caches, databases, logs, traces, and large experiment artifacts
under the dynamically derived MemLife runtime root. The root disk is small; do
not perform broad cleanup to reclaim it.

Use `/home/exouser/Memo/.venv/bin/python` for project Python work. Never install
project dependencies globally or with `pip install --user`.

Exosphere manages Guacamole Docker containers on this VM. Never run Docker
system/image prune operations or stop/remove those containers.

## Lifecycle automation

The tracked controller is `scripts/jetstream/jetstreamctl.py`. Its local
OpenStack client lives in ignored `.local/jetstream/cli-venv`; it reads the
ignored OpenRC through a strict assignment parser and reuses the ignored
workstation SSH key. It stores host keys in an ignored tool-specific
known-hosts file without globally disabling verification.

From the repository root on Windows:

```powershell
.\.local\jetstream\cli-venv\Scripts\python.exe scripts\jetstream\jetstreamctl.py doctor
.\.local\jetstream\cli-venv\Scripts\python.exe scripts\jetstream\jetstreamctl.py status
.\.local\jetstream\cli-venv\Scripts\python.exe scripts\jetstream\jetstreamctl.py acceptance
```

The acceptance command discovers the external network before unshelving,
records lifecycle and floating-IP ownership separately, and associates a new
temporary IP only with jisheng3's exact port. Cleanup disassociates and deletes
only a floating IP created by that same run. The VM is auto-shelved only when
the same run changed it from `SHELVED` to `ACTIVE`.

## Phase 02B-0 acceptance status

The authorized corrective cycle is `PASS`:

- OpenStack authentication and exact UUID validation: pass
- Initial state: `SHELVED`
- Unshelve and `ACTIVE`: pass
- External network: unambiguous `public`
- Temporary floating IP allocation and exact-port association: pass
- External address visibility: pass; numeric address not persisted
- TCP 22: pass in 0.049 seconds
- Public-key SSH and identity (`exouser` / `jisheng3`): pass
- Read-only repository, Python, and storage probe: pass
- Owned floating-IP disassociation, deletion, and absence verification: pass
- Final state: `SHELVED`
- Post-run target floating-IP association count: zero
- Offline tests before the cycle: `33 passed`

No manual server action is required before Phase 02B. Phase 02B itself has not
started.
