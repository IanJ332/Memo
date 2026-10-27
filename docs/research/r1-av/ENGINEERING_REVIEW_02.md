# R1-AV engineering review 02 — REJECT pending row binding

Reviewer `/root/engineering_review`, separate from implementation authors, October 26, 2026. This independent review inspected actual corrected sources and retained qualified worker/selection/transport behavior. Review 01 and its failed development checks remain unchanged.

Independent focused command:

```sh
MEMLIFE_R1_TEST_ACCEPTED_ROOT=/Users/ian/.codex/worktrees/3109/Memo /Users/ian/.codex/worktrees/424f/Memo/.venv/bin/python -I -B -m pytest -q tests/research/test_r1_av.py tests/research/test_r1_av_runtime.py tests/research/test_r1.py tests/research/test_r1_access_compat.py tests/research/test_r1_volume_admission.py
```

Result: **130 passed, 20 subtests passed, zero failed/errors/skipped** in 17.53 seconds. These are deterministic engineering controls, not scientific observations. An initial invocation's remaining output was not captured by the review tool wrapper; the bounded command was repeated to obtain this complete result. No passing-count inflation is claimed.

The initial blockers are resolved: native request/selection/IDs/user scope are checked; synthetic evidence is separately labeled and rejected by scientific audit; ledger roster, ordinals, request and completed response digests bind; raw transport request bytes and receipt hashes bind; full classifiable entities survive independent transport/admission failure; ambiguous attempted slots stay UNKNOWN; known native exposure survives downstream pre-send failure. Frozen R1/R2 identities remain unchanged. Public private-instance identifiers were removed.

One substantive audit defect remains in the reviewed bytes: `row = {**saved, ...}` trusts `saved['slot_id']` without checking equality with the current registered slot. Swapping derived scoring labels can reassign otherwise correctly reproduced outcomes across conditions. Require equality to the current slot, and bind `saved['capture']` to that capture inventory; retain a negative test. This rejection is limited to that missing final row/capture binding, not a rejection of the retained qualified lifecycle.

No hosted request, provider operation, browser or remote action occurred. JSON provenance checks establish exact binding, not genuine human/platform approval. Source acceptance and package acceptance remain separate, and neither supplies live authority.

Exact reviewed development identities:

```json
{
  "manifests/r1-av/design-v1.json": "b81cb15d203ce566097ec6695cc5172079cb639fa0e031ed96bac867af34b5dc",
  "manifests/r1-av/diversity-review-v1.json": "9c02be4c6c350845f650790015b92da45d9071d642e72e928d22ea8e26fdc3ab",
  "manifests/r1-av/host-acl-v1.json": "0eef86dd50d75a4a6ed35b0ba8ab5aca58f08137d2e4a9595da5d4a152313275",
  "manifests/r1-av/preservation-v1.json": "40faf03d5277f2845e758fbc5ab9df0a8040c66956f98c95a110fbce1ecd8dce",
  "manifests/r1-av/registration-v1.json": "846b933926fb4aa8218aaaa8a1500547a3c97d95aabee227b47d776f6e10f29d",
  "manifests/r1-av/templates-a.json": "2f7fda740b35976551893c4c4bbe8b3840d4a546c9660b71c93a427fea30f7b9",
  "manifests/r1-av/templates-b.json": "2dc0979637c94dc8e3670cb6704b7079377956dffc87ff70609a70c75781fc46",
  "scripts/research/r1_av.py": "dccac8a561861ac40cce165fa41279db6e7ec48e48c40877b9b2707fdb85388c",
  "src/memlife/r1_av/__init__.py": "d07e86fd0218ee249d68a4e80f37f41d1724873bb78964bd5d0c488aa4fa61e7",
  "src/memlife/r1_av/audit.py": "f511f70a315d793c8beea35c6daa1341c5d1bf65139dd7c621321c71386bc1f3",
  "src/memlife/r1_av/contract.py": "1490710772beba7796e24c93244e9568843ec1d2e2ca3baa7b922d254d285f3d",
  "src/memlife/r1_av/native.py": "d1084283c4929e3e4b77f2775a477ca144dab945d538dab8261194cbb8743c48",
  "src/memlife/r1_av/protocol.py": "beb518488f387dafc566e25b5e8e55dd49079dd1c0270a41eb583d9a0b337e47",
  "src/memlife/r1_av/review.py": "389ff8b22a110839637622d20f7291b705430b6d8ba3606a2712cb52465db633",
  "src/memlife/r1_av/runtime.py": "c3629260741a808ffd95a781f8647ef6cb6481cf499be9fd7735995b4bbc84c8",
  "src/memlife/r1_av/synthetic.py": "a55e76f2193074ea8bec26430c4c3514f410f73157d27217a4b38b6c2c276889",
  "tests/research/test_r1_av.py": "bbcb94f5e98e564e0c7119d20bee540836ac480d16ed26bf1680662627c2daf0",
  "tests/research/test_r1_av_runtime.py": "883e60eb52fe1920e0c8a918e5c43bb932e3e20fbff2ce51ad490c90e077be17"
}
```
