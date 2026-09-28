# Jetstream2 Server Context

Last verified: 2026-09-27 (manual mount check); Phase 02B-0 live acceptance updates the live-result fields.

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

Numeric public addresses are ephemeral and may change whenever the instance is
unshelved, especially because the public address is released on shelving. Never
store or hardcode a numeric address. Query OpenStack networking on every run.

## Persistent storage

The durable identity is the block device `/dev/sdb`, not a mount directory.
Always resolve its current mount dynamically:

```sh
actual_mount="$(findmnt -n -o TARGET /dev/sdb)"
runtime_root="${actual_mount}/memlife"
```

The previous cached mount `/media/volume/sdb` is **STALE as of the 2026-09-27
manual verification**. The current manually verified mount is
`/media/volume/jisheng3_volume`, making the current expected MemLife runtime root
`/media/volume/jisheng3_volume/memlife`. A newer live `findmnt` result supersedes
both values and must be documented.

Do not format, detach, or migrate `/dev/sdb` as part of lifecycle automation.
Read/write validation should only test the existing mount's permissions.

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
existing ignored OpenRC through a strict assignment parser and reuses the
existing ignored workstation SSH key. It stores host keys in an ignored,
tool-specific known-hosts file without globally disabling verification.

From the repository root on Windows:

```powershell
.\.local\jetstream\cli-venv\Scripts\python.exe scripts\jetstream\jetstreamctl.py doctor
.\.local\jetstream\cli-venv\Scripts\python.exe scripts\jetstream\jetstreamctl.py status
.\.local\jetstream\cli-venv\Scripts\python.exe scripts\jetstream\jetstreamctl.py acceptance
```

The acceptance command records the initial state. It auto-shelves only when
that same run performed the `SHELVED` to `ACTIVE` transition. It never
auto-shelves an instance that was already `ACTIVE`.
