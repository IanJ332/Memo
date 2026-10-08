# Phase 08B-1 Candidate10 controller hardening recommendations

## Scope

These recommendations address the separate controller/SSH operational failure
observed after Candidate10 had already completed remotely. They do not modify
the frozen provider decision, do not authorize a rerun, and were not
implemented as part of this closeout.

Root-cause status remains `UNKNOWN`. The proven locus is the local controller's
primary SSH subprocess: it did not return before the 5,400-second timeout, so
result parsing and copyback were never reached even though remote
`completion.json` had already been written.

## Recommended changes

1. Persist the structured remote result atomically in the attempt directory
   before publishing completion. Use a temporary file plus atomic rename, and
   bind the result to the attempt ID and completion hash.
2. Redirect remote stdout and stderr to attempt-scoped files. Treat the SSH
   channel as transport, not as the only carrier of the authoritative result.
3. Replace one long-lived execution/copy session with short, bounded status and
   copy calls. Record the primary SSH start time, remote-Python exit time, SSH
   EOF time, and each status/copy attempt.
4. On primary SSH timeout, perform read-only recovery: verify the exact
   completion identity and persisted result, then copy evidence without
   re-entering scientific execution. Never infer permission to rerun from a
   transport timeout.
5. Enumerate the required-artifact allowlist from completion and copy each file
   independently. A permission error on optional/protected state should be
   recorded per path and must not prevent recovery of unrelated readable
   evidence.
6. Retry only bounded transport operations. Retries may repeat status checks or
   evidence transfer; they must never repeat provider probes, model calls,
   Dream triggers, scenario execution, or other scientific behavior.
7. Keep lifecycle cleanup in a controller-owned `finally` path and record
   cleanup separately from scientific status. A provider result and a VM/SSH
   result must remain independent fields.
8. Add an offline regression test that simulates remote completion followed by
   a non-returning SSH channel. The expected behavior is exact completion/result
   recovery, no scientific rerun, bounded copyback, and preserved timeout
   evidence.

Increasing the 5,400-second timeout is not recommended. It would mask the
separation failure without improving evidence integrity or identifying the
underlying transport mechanism.
