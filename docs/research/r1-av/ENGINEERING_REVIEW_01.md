# R1-AV engineering review 01 — REJECT

Reviewer: `/root/engineering_review`, separate from implementation authors.
Scope: offline source inspection of actual R1-AV modules, frozen R1 collection/contract/protocol and the pinned retained Tier C, batch evidence/ledger/runtime/worker/selection sources. No browser, network, provider, remote, or hosted model operation. Scientific collection NOT_EXECUTED.

This development rejection is retained. Source files were changing during review; the exact endpoint snapshot below identifies the development tree at report creation and is not acceptance of subsequent changes.

## Findings

1. Completed-campaign audit imported `retrieval_records`, while the native adapter defined `retrieved_records`. This prevented completed-campaign reproduction. The author corrected the identifier during review.
2. Classifier `F04=NOT_EVALUATED_PROPOSAL_ONLY` conflicted with the inherited unit-controller override `NOT_EVALUATED_R1_ACL_CLASSIFICATION_ONLY`, so exact scoring reproduction always failed. A versioned transformation now corrects the inherited override; final execution must verify it.
3. Scientific/synthetic separation initially checked package metadata only, allowing obviously synthetic phase/receipt artifacts into a relabeled scientific package. Author added per-phase and receipt flag checks during review; final negative tests remain required.
4. Audit verifies ledger chain integrity but does not bind captured request/response SHA-256 values, ordinal, unit ID and completion state to the ledger slot, or require the exact registered jobs roster. Seal and scorer agreement alone cannot establish agreement with durable send custody. This is a substantive remaining integrity defect at review time.
5. The initial public scientific manifest included the private intended access instance name and UUID despite the owner publication prohibition. They have been removed during review; final safe-publication inspection remains required.
6. New runtime tests use pytest, absent from the new local repository venv. An independent unittest-discovery attempt failed `ModuleNotFoundError: pytest`; there are no passing-test claims from that attempt. Convert tests or use a qualified repository test venv, with zero required skips.
7. Synthetic CLI output under `/private/tmp/memo-r1-av-review-01` fails the qualified durable path gate (`DURABLE_PATH_OUTSIDE_TASK_OR_TEMP`). The legacy helper allows its own retained repository and the actual OS temporary directory, not arbitrary public worktree paths or `/private/tmp`. Preserve the guard; document/use supported output locations. A second attempt under the actual OS temp directory stopped at expected concurrent registration drift before controller execution.
8. Scripted native `owned_ids` was a list whereas the real worker emits a role-to-ID dictionary. This weakens schema-parity coverage; match the actual worker shape in final integration fixtures.

No frozen historical file change was observed (`git status` showed new R1-AV paths only). Dynamic derivation preserves hash-pinned R1 bases, exact transform occurrence checks and separate namespace. The retained qualified worker performs genuine all-results selection and literal ID/content/scope checks, and native construction remains behind owner admission. Those positive findings do not resolve the remaining audit/verification defects.

## Exact development snapshot

```json
{
  "manifests/r1-av/design-v1.json": "b81cb15d203ce566097ec6695cc5172079cb639fa0e031ed96bac867af34b5dc",
  "manifests/r1-av/host-acl-v1.json": "0eef86dd50d75a4a6ed35b0ba8ab5aca58f08137d2e4a9595da5d4a152313275",
  "manifests/r1-av/registration-v1.json": "187ac81eec76f51584101d3beb9ac78df806e1126be67efc3adc7aae410bf5d8",
  "manifests/r1-av/templates-a.json": "2f7fda740b35976551893c4c4bbe8b3840d4a546c9660b71c93a427fea30f7b9",
  "manifests/r1-av/templates-b.json": "2dc0979637c94dc8e3670cb6704b7079377956dffc87ff70609a70c75781fc46",
  "scripts/research/r1_av.py": "dccac8a561861ac40cce165fa41279db6e7ec48e48c40877b9b2707fdb85388c",
  "src/memlife/r1_av/__init__.py": "d07e86fd0218ee249d68a4e80f37f41d1724873bb78964bd5d0c488aa4fa61e7",
  "src/memlife/r1_av/audit.py": "a17aa834c4c755cb284b11dbdf16e4d84ace2c4e514fca57c3b80cae56653d61",
  "src/memlife/r1_av/contract.py": "1490710772beba7796e24c93244e9568843ec1d2e2ca3baa7b922d254d285f3d",
  "src/memlife/r1_av/native.py": "b7b97bcb1b7322a99aa628ba0ae68827bb74ceb93759201148d1da0fd3665e1a",
  "src/memlife/r1_av/protocol.py": "f942fa49784d8f9535a9333b52528baba3cbd58a7cb79537a58db00783bb4076",
  "src/memlife/r1_av/review.py": "389ff8b22a110839637622d20f7291b705430b6d8ba3606a2712cb52465db633",
  "src/memlife/r1_av/runtime.py": "c3629260741a808ffd95a781f8647ef6cb6481cf499be9fd7735995b4bbc84c8",
  "src/memlife/r1_av/synthetic.py": "b2eb501fc87642899bc9bc87824e9efe03473eaa02ee584f84a512e1df5fb2af"
}
```
