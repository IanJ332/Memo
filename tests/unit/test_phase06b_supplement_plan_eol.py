from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from memlife.runner.phase06b_supplement import SUPPLEMENT_PLAN_SHA256, sha256_canonical_tracked
from memlife.runner.tracked_text import materialize_tracked_text

REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN = REPO_ROOT / "experiments" / "supplements" / "phase06b-openviking-missing-runs-v1.json"


def test_supplement_plan_has_lf_git_blob_identity():
    # Prove the identity is the Git LF blob hash.
    materialization = materialize_tracked_text(PLAN)
    assert hashlib.sha256(materialization.git_blob).hexdigest() == SUPPLEMENT_PLAN_SHA256


def test_supplement_plan_canonical_crlf_sha_differs_from_identity():
    # Prove canonical CRLF SHA differs but tracking resolves to the blob.
    materialization = materialize_tracked_text(PLAN)
    assert materialization.sha256 != SUPPLEMENT_PLAN_SHA256


def test_supplement_plan_canonical_tracking():
    # This tests that validation works regardless of the file's current EOL.
    # The actual validation logic relies on Git, so we just verify the plan is tracked.
    assert sha256_canonical_tracked(PLAN) == SUPPLEMENT_PLAN_SHA256
