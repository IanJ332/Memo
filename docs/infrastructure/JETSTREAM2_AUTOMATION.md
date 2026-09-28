# Jetstream2 Automation Acceptance

## Phase 02B-0 result

Status: `BLOCKED`

The second and final controlled acceptance cycle ran on 2026-09-28 UTC against
only `jisheng3` (`5baeeae7-4c29-4903-89fe-2e9df0a8eced`). Authentication,
target validation, unshelving, transition to `ACTIVE`, and automatic cleanup
all succeeded. The final verified state is `SHELVED`.

The run stopped at `ADDRESS`: the live OpenStack server representation did not
contain an externally routable address. The selector correctly refused to use
the private candidate. Because no external address was selected, TCP 22, SSH,
and the remote read-only probe were not attempted.

Read-only diagnostics after cleanup found one port belonging to the target and
no floating-IP association for that port. The tracked DNS hostname did not
resolve while shelved. No numeric address, credential, or SSH private key is
stored in the repository.

## Controller safeguards

`scripts/jetstream/jetstreamctl.py` now:

- rejects private-only address sets;
- handles nested and string OpenStack address representations;
- separates TCP 22 readiness from SSH protocol and key authentication;
- classifies SSH failures without password fallback;
- captures remote repository HEAD, Python, volume mount, and capacity when a
  probe can run; and
- shelves only when the same acceptance run opened the instance.

The manifest at `manifests/jetstream-automation-acceptance.json` is the
machine-readable result. A future attempt requires explicit authorization for
a new lifecycle cycle after the external-address assignment/discovery blocker
is resolved.
