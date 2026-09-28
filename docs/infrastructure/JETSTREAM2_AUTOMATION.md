# Jetstream2 Automation Acceptance

## Phase 02B-0 result

Status: `PASS`

The single authorized corrective acceptance cycle ran on 2026-09-28 UTC
against only `jisheng3` (`5baeeae7-4c29-4903-89fe-2e9df0a8eced`). OpenStack
authentication, exact-target validation, unshelving, temporary floating-IP
management, TCP 22, public-key SSH, the remote read-only probe, owned-resource
cleanup, and shelving all succeeded. The final verified VM state is `SHELVED`.

Read-only discovery found exactly one external network, `public`
(`3fe22c05-6206-4db2-9a13-44f04b6796e6`). No floating IP was associated with
the target before the cycle, so the controller allocated one temporary
floating IP, associated it with jisheng3's exact port, and waited for both the
port association and server address view to agree. The numeric address was
used only in process memory and is not stored in Git.

TCP 22 was ready 0.049 seconds after address visibility. SSH succeeded with
the existing workstation public key, and the read-only probe verified:

- remote identity: `exouser` on `jisheng3`;
- repository: `/home/exouser/Memo`, branch `main`, clean at
  `3a1988815ec9c453f56aa892792e82334c572654`;
- project Python: `Python 3.12.3`;
- persistent device: `/dev/sdb`;
- live mount: `/media/volume/jisheng3_volume` with `49G` capacity; and
- derived MemLife root: `/media/volume/jisheng3_volume/memlife`.

Cleanup first disassociated the run-owned floating IP, verified that the port
association was gone, deleted that exact resource, and verified its absence.
The project floating-IP count was four both before and after the cycle, the
target had zero floating-IP associations afterward, and no pre-existing or
unowned floating IP was modified. The controller then shelved the VM and a
post-run read-only check reconfirmed `SHELVED`.

## Correct lifecycle architecture

Shelving releases jisheng3's public address. Future CLI-driven work therefore
uses this ownership-aware sequence:

1. authenticate and validate the exact server UUID;
2. discover an unambiguous external network before any mutation;
3. unshelve only when the initial state is `SHELVED`;
4. reuse an already-associated floating IP without taking ownership, or
   allocate one dedicated temporary IP when none is associated;
5. associate a run-created IP only with jisheng3's exact port;
6. use the dynamically discovered numeric address for TCP and SSH without
   persisting it;
7. disassociate and delete only an IP created by the same run; and
8. shelve only when the same run opened the VM.

A private RFC1918 address remains insufficient for workstation SSH. The
controller does not weaken address selection or claim an unrelated free
floating IP. DNS is informational and is not an acceptance prerequisite.

## Controller safeguards

`scripts/jetstream/jetstreamctl.py`:

- hard-gates all server mutations to the authorized UUID;
- stops on ambiguous external networks or target ports;
- tracks whether a floating IP was pre-existing, created by this run, and
  associated by this run;
- refuses to disassociate or delete an unowned floating IP;
- performs best-effort IP cleanup before VM shelving on every failure path;
- separates TCP readiness from SSH protocol, host-key, and authentication
  failures, with no password fallback;
- collects read-only security-group evidence if TCP 22 times out;
- resolves `/dev/sdb` dynamically for capacity and MemLife-root reporting; and
- redacts the transient numeric address and OpenStack secrets before writing
  the acceptance manifest.

The offline suite passed (`33 passed`) before the live cycle. The authoritative
machine-readable result is
`manifests/jetstream-automation-acceptance.json`.
