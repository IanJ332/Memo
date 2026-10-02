"""Tests for Phase 07 prep: residual trace extraction and RQ3 context candidate freeze."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from memlife.runner.tracked_text import materialize_tracked_jsonl, materialize_tracked_text

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_P07 = REPO_ROOT / "artifacts" / "phase07" / "prep"
DOCS_EXP = REPO_ROOT / "docs" / "experiments"

FREEZE_EXPECTED_SHA = "0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b"
ORIG_RAW_EXPECTED_SHA = "fe6f8cca390fa30b714e7635b9e7e56b987bd8303611f625c3258e90eaea2ef4"
DERIVED_ORIG_EXPECTED_SHA = "80b82f177adf4a15659bc583df61c78dafaa034ac931b5592e22a47d01f67a9f"
SUPPLEMENT_RAW_EXPECTED_SHA = "435fd4a78b7748f3f3972fe64be811bbbf07dac30931a6034b171c2ff1d46ea4"


def test_phase06b_source_artifacts_integrity() -> None:
    """Phase 06B source artifacts must remain immutable with exact expected hashes."""
    # 1. Freeze SHA
    freeze_path = REPO_ROOT / "experiments" / "freeze" / "experiment-freeze-v1.json"
    assert freeze_path.is_file()
    freeze_mat = materialize_tracked_text(freeze_path)
    assert freeze_mat.sha256 == FREEZE_EXPECTED_SHA

    # 2. Original raw SHA (bytes)
    orig_raw_path = (
        REPO_ROOT
        / "artifacts"
        / "phase06b"
        / "attempts"
        / "20261001T183940Z-1fc4c4929532"
        / "freeze-v1-raw-runs.jsonl"
    )
    assert orig_raw_path.is_file()
    assert hashlib.sha256(orig_raw_path.read_bytes()).hexdigest() == ORIG_RAW_EXPECTED_SHA

    # 3. Derived original canonical SHA (CRLF-materialized JSONL)
    derived_orig_path = (
        REPO_ROOT
        / "artifacts"
        / "phase06b"
        / "derived"
        / "20261001T183940Z-1fc4c4929532"
        / "freeze-v1-raw-runs.provenance-repaired.jsonl"
    )
    assert derived_orig_path.is_file()
    derived_mat = materialize_tracked_jsonl(derived_orig_path)
    assert derived_mat.sha256 == DERIVED_ORIG_EXPECTED_SHA

    # 4. Supplement raw SHA (bytes)
    supp_raw_path = (
        REPO_ROOT
        / "artifacts"
        / "phase06b"
        / "supplements"
        / "attempts"
        / "20261002T000350Z-c272b34d2cc3"
        / "supplement-raw-runs.jsonl"
    )
    assert supp_raw_path.is_file()
    assert hashlib.sha256(supp_raw_path.read_bytes()).hexdigest() == SUPPLEMENT_RAW_EXPECTED_SHA


def test_residual_cell_set_and_s0_exclusion() -> None:
    """Scientific residual cell set is exactly Mem0 S1, Hindsight S1, Hindsight S4, OpenViking S4.

    OpenViking S0 is explicitly excluded from scientific residual analysis because
    its index flag resulted from a historical provider crash and repetition disagreement.
    """
    runs_path = (
        REPO_ROOT
        / "artifacts"
        / "phase06b"
        / "supplements"
        / "derived"
        / "20261002T000350Z-c272b34d2cc3"
        / "combined-derived-runs.jsonl"
    )
    rows = [json.loads(line) for line in runs_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 42

    # Preserved historical error
    s0_r2 = next(r for r in rows if r["run_id"] == "freeze-v1__openviking__S0__r2")
    assert s0_r2["exact_visibility_outcome"] == "ERROR"
    assert s0_r2["authority_exposure_outcome"] == "NONE"
    assert "RemoteDisconnected" in s0_r2["error"]

    # Verify target scientific residual cells in 07A and 07B artifacts
    rc_path = ARTIFACTS_P07 / "root-cause-evidence.json"
    rc_data = json.loads(rc_path.read_text(encoding="utf-8"))
    rc_cells = {(c["provider"], c["scenario"]) for c in rc_data["cells"]}
    assert rc_cells == {("hindsight", "S4"), ("openviking", "S4")}

    rq3_path = ARTIFACTS_P07 / "rq3-context-candidates.json"
    rq3_data = json.loads(rq3_path.read_text(encoding="utf-8"))
    rq3_cells = {(c["provider"], c["scenario"]) for c in rq3_data["cells"]}
    assert rq3_cells == {("mem0", "S1"), ("hindsight", "S1")}

    all_phase07_cells = rc_cells | rq3_cells
    assert all_phase07_cells == {
        ("mem0", "S1"),
        ("hindsight", "S1"),
        ("hindsight", "S4"),
        ("openviking", "S4"),
    }
    assert ("openviking", "S0") not in all_phase07_cells


def test_no_rq3_calls_and_no_downstream_inference() -> None:
    """All Phase 06B runs must record 0 RQ3 calls and delivered_context_sha256 as null."""
    runs_path = (
        REPO_ROOT
        / "artifacts"
        / "phase06b"
        / "supplements"
        / "derived"
        / "20261002T000350Z-c272b34d2cc3"
        / "combined-derived-runs.jsonl"
    )
    rows = [json.loads(line) for line in runs_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    for r in rows:
        assert r.get("rq3_calls", 0) == 0
        assert r.get("downstream_decision_model_calls", 0) == 0
        assert r.get("delivered_context_sha256") is None


def test_phase07_prep_artifacts_structure_and_gates() -> None:
    """Phase 07 prep artifacts must be valid, labeled properly, and strictly reflect gate status."""
    rc_json = ARTIFACTS_P07 / "root-cause-evidence.json"
    assert rc_json.is_file()
    rc_data = json.loads(rc_json.read_text(encoding="utf-8"))
    assert rc_data["root_cause_conclusion"] == "NOT ATTEMPTED"
    assert rc_data["status"] == "EVIDENCE_EXTRACTION_COMPLETE"

    rq3_json = ARTIFACTS_P07 / "rq3-context-candidates.json"
    assert rq3_json.is_file()
    rq3_data = json.loads(rq3_json.read_text(encoding="utf-8"))
    assert rq3_data["approval_status"] == "CANDIDATE_NOT_SCIENTIFICALLY_APPROVED"

    gate = rq3_data["evaluation_gate_summary"]
    assert gate["mem0_s1"]["gate_status"] == "MISSING_MODEL_BOUNDARY_TRACE"
    assert gate["hindsight_s1"]["gate_status"] == "MISSING_EXACT_CONTEXT"
    assert gate["mem0_s1"]["deterministic_mapping_to_model_boundary"] is False
    assert gate["hindsight_s1"]["exact_content_bytes_available"] is False

    # Check documentation artifacts exist and contain required headers
    doc_07a = DOCS_EXP / "PHASE_07A_ROOT_CAUSE_EVIDENCE.md"
    assert doc_07a.is_file()
    text_07a = doc_07a.read_text(encoding="utf-8")
    assert "**Root-Cause Conclusion:** NOT ATTEMPTED" in text_07a
    assert "EVIDENCE EXTRACTION ONLY" in text_07a
    assert "SOURCE_STATE" in text_07a
    assert "DERIVED_STATE" in text_07a
    assert "RETRIEVAL" in text_07a
    assert "AUTHORITY_CLASSIFICATION" in text_07a
    assert "MODEL_BOUNDARY" in text_07a

    doc_07b = DOCS_EXP / "PHASE_07B_RQ3_CONTEXT_CANDIDATES.md"
    assert doc_07b.is_file()
    text_07b = doc_07b.read_text(encoding="utf-8")
    assert "CANDIDATE_NOT_SCIENTIFICALLY_APPROVED" in text_07b
    assert "MISSING_MODEL_BOUNDARY_TRACE" in text_07b
    assert "MISSING_EXACT_CONTEXT" in text_07b


def test_phase07_scientific_decisions_artifact_and_doc() -> None:
    """Scientific decisions document and JSON artifact must record exact approved classifications."""
    doc_path = DOCS_EXP / "PHASE_07_SCIENTIFIC_DECISIONS.md"
    assert doc_path.is_file()
    doc_text = doc_path.read_text(encoding="utf-8")

    # Verify structural sections
    assert "OBSERVED EVIDENCE" in doc_text.upper()
    assert "MAIN-CHATGPT SCIENTIFIC INTERPRETATION" in doc_text.upper()
    assert "UNRESOLVED QUESTIONS" in doc_text.upper()

    # Verify approved classifications in doc
    assert "PROVENANCE_LINEAGE_RESIDUAL" in doc_text
    assert "RQ3_CANDIDATE" in doc_text
    assert "LEGITIMATE_REDERIVATION_CANDIDATE" in doc_text
    assert "F2_DERIVED_STATE" in doc_text
    assert "ROOT_CAUSE_UNRESOLVED" in doc_text

    # Verify Task B discrimination
    assert "INSUFFICIENT_EVIDENCE" in doc_text

    # Verify Task C recovery inventory
    assert "f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6" in doc_text
    assert "Exact Provider-Native ID Lookup" in doc_text or "EXACT PROVIDER-NATIVE ID LOOKUP" in doc_text.upper()

    # Verify Task D sizing
    assert "PROVISIONAL_UNTIL_CONTEXT_RECOVERY" in doc_text
    assert "27" in doc_text

    # Verify machine-readable JSON artifact
    json_path = ARTIFACTS_P07 / "scientific-decisions.json"
    assert json_path.is_file()
    data = json.loads(json_path.read_text(encoding="utf-8"))

    assert data["schema_version"] == "memlife-phase07-scientific-decisions-v1"
    assert data["live_execution_authorized"] is False
    assert data["rq3_authorized"] is False
    assert data["jetstream_status"] == "SHELVED"

    decisions = data["decisions"]
    assert decisions["mem0_s1"]["classification"] == "PROVENANCE_LINEAGE_RESIDUAL"
    assert decisions["mem0_s1"]["rq3_eligibility"] == "NO"
    assert "RQ1" in decisions["mem0_s1"]["relevant_rqs"]

    assert decisions["hindsight_s1"]["classification"] == "RQ3_CANDIDATE"
    assert decisions["hindsight_s1"]["rq3_eligibility"] == "YES"
    assert decisions["hindsight_s1"]["sole_empirical_rq3_candidate"] is True

    assert decisions["hindsight_s4"]["classification"] == "LEGITIMATE_REDERIVATION_CANDIDATE"
    assert decisions["hindsight_s4"]["rq3_eligibility"] == "NO"

    assert decisions["openviking_s4"]["classification"] == "F2_DERIVED_STATE"
    assert decisions["openviking_s4"]["root_cause_status"] == "ROOT_CAUSE_UNRESOLVED"
    assert decisions["openviking_s4"]["rq3_eligibility"] == "NO"

    assert decisions["openviking_s0"]["classification"] == "EXCLUDED"
    assert decisions["openviking_s0"]["rq3_eligibility"] == "NO"

    # Task B discrimination
    assert data["openviking_s4_root_cause_discrimination"]["discrimination_result"] == "INSUFFICIENT_EVIDENCE"

    # Task C recovery inventory
    rec = data["hindsight_s1_recovery_inventory"]
    assert rec["expected_sha256"] == "f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6"
    assert rec["requires_jetstream_read_only_access"] is True
    assert len(rec["repetitions"]) == 3
    assert len(rec["preferred_recovery_hierarchy"]) == 3
    assert rec["preferred_recovery_hierarchy"][0]["method"] == "EXACT_PROVIDER_NATIVE_ID_LOOKUP"
    assert rec["preferred_recovery_hierarchy"][1]["method"] == "EXACT_DATABASE_ROW_LOOKUP"
    assert rec["preferred_recovery_hierarchy"][2]["method"] == "EXACT_CONTENT_SHA_VERIFICATION"
    assert "semantic_search_re_query" in rec["forbidden_recovery_methods"]

    # Task D sizing
    sizing = data["rq3_experimental_size"]
    assert sizing["status_label"] == "PROVISIONAL_UNTIL_CONTEXT_RECOVERY"
    assert sizing["contexts"] == 1
    assert sizing["models"] == 3
    assert sizing["repetitions"] == 3
    assert sizing["conditions"] == 3
    assert sizing["maximum_calls"] == 27
    assert sizing["executed_calls"] == 0


def test_no_secrets_in_phase07_prep_artifacts() -> None:
    """Phase 07 artifacts must not leak any secrets or sensitive keys."""
    forbidden = ["ghp_", "sk-", "AIzaSy", "password", "BEGIN " + "PRIVATE KEY", "client_secret"]
    for path in [
        ARTIFACTS_P07 / "root-cause-evidence.json",
        ARTIFACTS_P07 / "rq3-context-candidates.json",
        ARTIFACTS_P07 / "scientific-decisions.json",
        DOCS_EXP / "PHASE_07A_ROOT_CAUSE_EVIDENCE.md",
        DOCS_EXP / "PHASE_07B_RQ3_CONTEXT_CANDIDATES.md",
        DOCS_EXP / "PHASE_07_SCIENTIFIC_DECISIONS.md",
    ]:
        content = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in content, f"Forbidden token {token} found in {path}"
