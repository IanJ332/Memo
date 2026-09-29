# Environment Manifests

Generated phase/run manifests may be written here when a reproducibility record
belongs in version control. Runtime-generated manifests should normally be kept
under the selected data root's `runs/` or `artifacts/` directory.

Manifest generation records environment metadata and configuration hashes, not
configuration values or secrets.

`phase-05c-openviking-live-validation.json` records the single controlled
OpenViking lifecycle, its pre-install dependency-plan blocker, and completed
Jetstream cleanup without serializing protected runtime configuration values.
