# Phase 2 public and private artifacts

This migration publishes first-party implementation and synthetic tests. Historical
raw evidence, reservation ledgers, private execution bindings, and detailed runtime
inventories remain private. Some historical tests require the exact privately held
manifests or inventories and cannot be reproduced from this public checkout alone;
they must not be replaced with altered files while claiming the original hashes.
No published derivative establishes authority for an experiment.

The original V2 first-cell manifest SHA-256 is
`08a142369630fd8d80b49387d259677d9cf7455337dad726e881bb789a240685`;
V3 compatibility `6880f8b21824554b797df6ccaf758ccf7d423e24561aa0f1d9c721f3b1dd94bc`;
V3 smoke `ac94d2a732d604e03d45d0ec5e3ee9932303c26ea235820869aac43834613da7`.
V4 compatibility and smoke offline candidates are respectively
`9da79903d6dad8f9a470a9679699ee7996994aa0d8902fb981cc65da77f03255` and
`4ef8990d2f54daf77a28ec06b788d8955edd60a31bc2f4ecb257744a300d9505`.
V4 has not run and is not live-integrated or authorized.

For public portability, `scripts/nlip_phase1_evaluate.py` now resolves its
historical freeze relative to the checkout. `scripts/nlip_phase2b5_execution.py`
uses a nonconfigured placeholder deployment path; it cannot reproduce the
historical deployment. These source bytes are not the accepted historical source
package and do not confer live execution authority. Preserve private originals.

The V3 compatibility request returned HTTP 200, the registered model identity
and valid structured output with zero reported reasoning tokens. The V3 smoke
stopped on its second cell when the validator rejected an ABSTAIN with non-null
arguments; no misleading-context smoke was attempted. These are observational
summaries, not the private provider responses or reservation records.

To run the standalone public schema test, install jsonschema in a repository
virtual environment and run `python -m pytest tests/nlip_phase2b5b/test_public_schema.py`
with `src` on `PYTHONPATH`. Other 2B-5B tests skip when their private manifests
are absent; the captured-response regression fixture is retained privately.
