# NEXT-LP-NATIVE-01-Q1 — complete offline execution architecture

Starting source: `ec378d75a50676408be7a076a68cba1987b8535a`.
This task implements prospective readiness, **not native scientific collection**.
The fixed Mem0 2.2.1 infer=False study has eighteen SDK slots, three distinct
provider processes in one task-owned container, two synthetic records and one
fresh namespace/store. No prior experiment is reopened or modified.

The independent [registration](REGISTRATION.md),
[frozen protocol](../../../manifests/next-lp-native-q1/registration-v1.json) and
[Host oracle](../../../manifests/next-lp-native-q1/oracle-v1.json) precede the
scripted controller observations. Scientific parameters remain unchanged.
Exact prospective package identity and review decisions are recorded separately
in the final package handoff after source acceptance; private contents stay local.

## Implemented execution and custody

`scripts/research/native_q1.py` exposes simulate, audit, prepare, verify-package
and the separately gated run command. The controller is in
`src/memlife/native_q1/{core,runtime,packaging}.py`; the bounded native worker is
`scripts/research/native_q1_worker.py`. Existing Mem0 construction/configuration,
normalizer, pure baseline storage producer, authority ledger/scorer and V2
projection are reused unchanged. New code does not migrate ordinary callers.

The Host seals its independent oracle before provider construction. It writes
and fsyncs every registered intent before transport dispatch, consumes failed or
ambiguous attempts, retains the response/error and never retries or resumes a
claimed attempt. A restarted controller may audit or perform separately scoped
owned-resource recovery; it cannot continue/replay scientific slots. Missing
dependent add identity stops dependent work. Failed native calls remain recorded;
successful missing/malformed read outcomes retain explicit uncertainty.

An add response establishes a provisional native-ID coordinate from the paired
Host intent. A later get must agree on exact ID, raw user_id and literal content
before the Host activates the byte-bound association. Metadata cannot supply
the Host event or rescue a missing native scope. The Host stores immutable
association/authority artifacts outside every provider mount. Each association
retains its originating intent/response digests. Hashes establish continuity
relative to this independently controlled Host path, not authorship by themselves.

Slot10 invalidates CURRENT's old association and advances the independent Host
authority revision after a genuine successful update return. Get11 may confirm
the new bytes and create a separate refreshed artifact. It also evaluates the
actual preserved pre-update binding, recording the compared original digest and
whether this stale-byte comparison was eligible. Missing old bindings cannot
be counted as successful stale-digest rejection. Slot13 removes UNTRUSTED's live
association after successful deletion while preserving its Host-known baseline
mapping and deleted ledger entry. Returned deleted records remain observed;
V2 uncertainty is distinct from native absence.

The worker receives SDK requests, not a writable oracle or association store.
Mounts are exact source RO, qualified runtime/model cache RO, and fresh store RW.
No Host evidence, grant or private package directory is mounted. Network none,
read-only root, cap-drop ALL, no-new-privileges, 2 CPUs, 6GiB and bounded tmpfs/PIDs
contain the one container. `--pull=never` forbids implicit image acquisition.
Three sequential docker-exec processes each construct Memory.from_config once;
no provider is constructed by import, simulation, prepare or package verification.
Worker call counters must agree with the Host's 6/8/4 phase roster.

Each parsed SDK response is retained with its intent. Bounded exact worker JSON
transport lines, malformed/partial stdout, stderr and unsolicited trailing output
are separately retained. These are Python API return/transport representations,
**not SDK HTTP wire evidence**. Raw evidence is never replaced by a summary.

## Measurements and limits

The complete legitimate native-ID→Host-event mapping is preserved in baseline,
including UNTRUSTED and deleted history. A forged CURRENT claim may therefore
produce MIXED rather than AUTHORITATIVE_ONLY. Primary evidence is unsupported
CURRENT attribution to the UNTRUSTED record, reported per record as well as for
the full returned set. V2 correlation, completeness, unresolved reasons and
exposure are recorded on the identical normalized native records.

Each forged key is reported independently on each observed surface. Primary
eligible slots5/6/7/9/12 remain explicit even when omitted or UNKNOWN. Benign
current-source coverage has fixed eligible slots3/6/7/8/11/12/14/15/16; missing
records do not vanish from its denominator. Successful empty retrieval is NONE;
get(None) is native NOT_OBSERVED with scoring UNKNOWN, not proof that metadata
was stripped. Malformed records, wrong namespace, missing/ambiguous identity,
stale bytes, wrong authority revision and incomplete mappings remain explicit.

Controlled forged metadata tests a reachable interface, not attacker privileges.
This direct-record infer=False study cannot establish derived-lineage completeness,
model behavior, semantic task utility, protected-tool authorization or general
provider security. All scripted outcomes below are synthetic, not native findings.

## Offline validation and reproduction

The explicitly scripted transport performs no Mem0 import/construction, model,
Docker or network action. The real CLI simulation completed all eighteen slots
and its read-only audit reproduced all eighteen rows. Its original inventory is
`cfcbdae351864f0d65aa1abf4d2f889e646616b8ae70acad85666199031f92c1`.
The private raw simulation is retained unchanged; [safe validation metadata](VALIDATION.json)
records its synthetic stratum. Synthetic baseline attribution and V2 results
validate implementation, not the prospective native hypotheses.

Use only an existing repository `.venv` interpreter. No installation is needed:

```sh
"$PY" -I -B -X pycache_prefix=/dev/null -m pytest -q -p no:cacheprovider tests/research/test_native_q1.py tests/research/test_native_q1_packaging.py
"$PY" -I -B -X pycache_prefix=/dev/null scripts/research/native_q1.py simulate --out /absolute/fresh/synthetic-output
"$PY" -I -B -X pycache_prefix=/dev/null scripts/research/native_q1.py audit --out /absolute/sealed/evidence --inventory-sha256 ACCEPTED_INVENTORY_SHA256
```

Simulation is a checkout development command using tests/fakes/q1_scripted.py;
the private frozen package supports verify-package, run and audit. The CLI
simulation/audit paths install a network/process audit guard. Audit verifies
exact membership and bytes, then independently replays intent/response joins,
immutable Host snapshots, phase identity/counts, endpoints, cleanup and terminal
status. An externally retained inventory identity remains the custody anchor;
recomputing a local hash is not authentication. Audit writes no replacement data.

Focused controls cover every requested failure class, including missing and
duplicated responses, pre-dispatch intent durability, actual get/search divergence,
reopen IDs, stale/refreshed snapshots, namespace and revision mismatch, tampered
snapshots despite a rehashed inventory, ambiguous dispatch/no retry, restart stop,
resource limits, evidence ceiling, owned cleanup, raw malformed transport and
stopped-attempt relabeling. The earlier audit-status defect found during independent
development review was fixed before final source acceptance; no scientific result
or original sealed evidence was rewritten.

## Runtime and prospective package

Read-only readiness checks found the exact cached image and qualified local
runtime available. Independent verification checked 27,613 installed hashes,
72 distributions and 11 embedding files against accepted prior qualification.
Zero provider imports/constructions or container starts were used for this check.
Private administrative/runtime paths are excluded from public source artifacts.

The package snapshots exact source, registration, oracle, genuine scientific and
engineering source-review identities, runtime receipt, dependency lock/model
identities, fresh execution/namespace/store, resource envelope and supported
launcher. It retains an immutable **UNAPPROVED** owner-grant candidate. Preparation
requires clean committed reviewed source and an unused package location; it does
not dispatch Docker, import Mem0 or activate any grant. Package verification checks
the complete sealed membership and source materialization.

Future run requires genuine direct owner provenance for the exact package and a
concrete UTC window no longer than2700seconds. This is a continuity check on
trusted retained provenance; a JSON approved flag or file hash does not prove a
human decision. The actual supported platform must separately review the exact
launcher and its full dependent effects. No standalone platform receipt is
invented, and the frozen old live gates/grants remain unchanged.

Before native work, launch rechecks exact package/source/Host interpreter and
the five actually imported Host dependency RECORD closures, full qualified native
runtime/model identities, capacity, free disk, expiry, fresh store/container and
mount/resource isolation. Python uses `-I -B -X pycache_prefix=/dev/null` to avoid
reading unverified .pyc files from either installed cache or provider-writable tmp.

Maximum18 attempted SDK calls, three constructions, one store/container, zero
hosted inference, zero downloads/builds, 256MiB evidence and minimum8GiB free disk
remain fixed. Scientific transport stops with60seconds reserved inside the
maximum45-minute approved window. Only exact owned-container inspection/removal
and owned-store deletion are permitted during cleanup, bounded by that same hard
deadline. The container has a bounded-lifetime watchdog. If absence cannot be
verified before the deadline, report STOPPED/unverified cleanup and preserve
evidence; do not extend scientific work or claim successful cleanup.

Primary configuration is inherited owner-selected Sol/High. Separate Sol agents
authored/reviewed science and engineering; deterministic tests used a separate
bounded author. Browser and Jetstream were not used. No live collection is
authorized by source acceptance, this report, the simulation or a package file.
