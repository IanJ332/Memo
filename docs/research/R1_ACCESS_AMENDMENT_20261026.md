# R1 access compatibility amendment — October 26, 2026

The engineered R1 access amendment v1 admits only the intended `jisheng3`
instance, UUID `5baeeae7-4c29-4903-89fe-2e9df0a8eced`, on **m3.quad / 4 vCPUs /
15,360 MiB**. The retained cloud inspection contains both exact flavor metadata
and server identity; its safe hash/size are in the
[amendment manifest](../../manifests/r1-access-amendment-v1.json). Effective guest
RAM is distinct from the flavor's configured RAM. No new operational check or
resize was performed.

The [official flavor table](https://docs.jetstream-cloud.org/general/vmsizes/),
checked October 26, lists **4 SU/hour**. Four hours correspond to a conditional
**16 compute SU** estimate. This is no billing hard cap; prior/subsequent uptime
and storage charges remain separate. An initially ACTIVE VM must remain ACTIVE
after cleanup, so continued owner-controlled billing can exceed that estimate.

## Source and admission contract

All 111 original qualified source pins and their original files remain unchanged.
The existing R1 bridge explicitly replaces only the original access module's
`verify_flavor` definition with the versioned public
[`access_compat.py`](../../src/memlife/r1/access_compat.py) function. Every other
access byte remains identical, including cloud authentication, lifecycle, volume,
SSH and receipt checks. Exact instance/project/user identity is additionally
checked inside flavor admission; exact integer CPU/RAM and consistent flavor
names are required. Existing current-allocation and offloaded-unshelve quota
checks remain enforced. Historical Tier C execution is not requalified or edited.

Package schema V2 binds the original source map, complete public source map,
amendment manifest, and original/effective hashes for all six bridge inputs.
Module loading rechecks both identities before compilation. The existing runner
and supervision adaptations are represented in that same effective map. Grants
and independent package receipts also bind the amendment/effective map. Old
packages remain verifiable through their preserved original entrypoints; the new
entrypoint rejects their V1 schema rather than relabeling them.

The local provider ceiling remains **2 CPUs / 6 GiB / network none / one active
container**. The inherited local Docker host gate remains at least 3 CPUs,
7 GiB RAM and 8 GiB plus estimated evidence free; that host is distinct from the
remote access VM. This amendment does not establish current Docker/provider/cache,
remote runtime, model/TLS or actual-volume availability. Existing qualified native
procedure/dependencies are reused only after their offline integrity checks;
current operational checks remain behind their required authorizations.

## Scientific and authority boundaries

The eight blocks, four arms, 32 registered requests, frozen design and independent
hidden ACL remain byte-identical. No native observations or model outcomes were
collected. Independent source acceptance and synthetic tests qualify this narrow
engineering amendment offline, not a live native runtime or scientific result.

`R1EX-20261026-01` retains its original package SHA-256
`0c29420ad4dacc97e83dd07d39e840d2bd0c250b3c0b7fa91f42ad3364364a92`;
its preparation and review must remain unchanged. Exactly one replacement may be
prepared after source acceptance and then requires independent exact-byte package
review. Leave the new owner grant unapproved. The
[readiness sequence](R1_READINESS.md#receipt-placement-preflight--2026-10-25)
still requires a separate direct owner decision, applicable external exact-action
approval, and independent actual-volume review. Earlier sealed attempts and LC12
must not be replayed.
