# R1 Docker recovery and fresh readiness — 2026-10-25

`R1EX-20261025-01` remains sealed and unchanged. It stopped before native
construction, remote access, or model generation because Docker Desktop was not
running. Its 32 registered outcomes remain unobserved; it is never reused.

## Recovery evidence

Docker Desktop 4.51.0 was installed. Both the active `default` context and the
`desktop-linux` context point to the qualified explicit socket
`unix:///Users/ian/.docker/run/docker.sock`; no Docker environment override was
present. The socket existed, but Docker Desktop's user helper was exited and the
client could not connect. Starting the existing Docker Desktop application was
the sole corrective action.

After startup, client and daemon were both Docker 28.5.2. The qualified
read-only resource check reported 16 CPUs, 8,215,879,680 bytes of RAM,
651,581,726,720 bytes of local free space, and sequential-provider mode. No
provider container, native store, model request, SSH connection, Jetstream
operation, or protected dispatch occurred during diagnosis or recovery.

## Fresh offline package

`R1EX-20261025-02` is a fresh prospective execution identity. Its package has
SHA-256 `ede298b4694c89e16678230f1df8562984c491749795c89ab8c19c676a3dc844`.
Its design SHA-256 remains
`a00453a0187013295b46e43ca9a8db048862028b6c92bdd5efcc6b51a5ac09e4`, and
its independent host ACL SHA-256 remains
`01bea38cdcafde30f6a6bcd612b3ecc072d04a8360932fe699b45489272a203f`.

The package and its owner grant are retained only in the qualified private
readiness directory. The grant has `approved: false`, no approval provenance,
and no approval times. The fresh output directory is distinct from the sealed
attempt. The public source implementation, registration, scoring, resource
bounds, provider mode, Qwen configuration, and evidence rules are unchanged.

Focused offline validation passed: 62 R1 tests and 9 subtests. The test suite
uses synthetic fixtures and blocks network/process dispatch; it is not a native
provider or model run. Pytest could not write its cache in the read-only
qualified checkout, which produced one non-test warning only.

## Remaining authorization

No R1 collection is authorized. A future direct owner message must bind
`AUTHORIZE_R1_LIVE`, `R1EX-20261025-02`, and the exact package SHA-256 above;
accept the package's Option B acknowledgment and bounded native/access scope;
then supply genuine message provenance and UTC-aware approval/window times.
Only the resulting new grant may authorize prospective native capture and any
dependent Qwen send. The sealed `R1EX-20261025-01` grant cannot be reused.
