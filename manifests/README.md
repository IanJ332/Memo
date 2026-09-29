# Environment Manifests

Generated phase/run manifests may be written here when a reproducibility record
belongs in version control. Runtime-generated manifests should normally be kept
under the selected data root's `runs/` or `artifacts/` directory.

Manifest generation records environment metadata and configuration hashes, not
configuration values or secrets.

`phase-05c-openviking-live-validation.json` records the single controlled
OpenViking lifecycle, its pre-install dependency-plan blocker, and completed
Jetstream cleanup without serializing protected runtime configuration values.

`phase-05d-openviking-preflight-repair.json` records the local-only package-name
normalization repair, official CPU-wheel route, controller import isolation,
structured pre-validator coverage, and regression results before a future
separately authorized live retry.

`phase-05e-openviking-live-retry.json` records the one controlled retry at
commit `8104aa682650393a9d36c881c7224721ff7bc252`, its authoritative readiness
timeout after installation/configuration gates passed, and completed managed
service, floating-IP, and VM cleanup.
