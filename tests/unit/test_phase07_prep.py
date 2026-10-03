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
    assert rq3_data["approval_status"] == "SCIENTIFICALLY_CLOSED_NO_ELIGIBLE_RQ3_CONTEXTS"

    gate = rq3_data["evaluation_gate_summary"]
    assert gate["mem0_s1"]["gate_status"] == "MISSING_MODEL_BOUNDARY_TRACE"
    assert gate["hindsight_s1"]["gate_status"] == "RECOVERED_CURRENT_CONTENT_RQ3_INELIGIBLE"
    assert gate["mem0_s1"]["deterministic_mapping_to_model_boundary"] is False
    assert gate["hindsight_s1"]["exact_content_bytes_available"] is True
    assert gate["hindsight_s1"]["rq3_eligibility"] is False

    hs1_cell = next(c for c in rq3_data["cells"] if c["provider"] == "hindsight" and c["scenario"] == "S1")
    for rep in hs1_cell["repetitions"]:
        non_auth = rep["non_authoritative_candidate_content"]
        assert non_auth["legacy_field_name"] is True
        assert non_auth["authority_characterization"] == "MIXED_LINEAGE_CURRENT_V2_PROPOSITION"
        assert non_auth["content_identity_basis"] == "CANONICAL_PROPOSITION_BODY"
        assert non_auth["byte_identical_to_per_run_authoritative_source_record"] is False
        assert non_auth["proposition_matches_current_v2"] is True
        assert non_auth["proposition_matches_stale_v1"] is False

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
    assert "MISSING_MODEL_BOUNDARY_TRACE" in text_07b
    assert "RECOVERED_CURRENT_CONTENT_RQ3_INELIGIBLE" in text_07b


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
    assert "PROVENANCE_LINEAGE_RESIDUAL_CURRENT_CONTENT" in doc_text
    assert "LEGITIMATE_REDERIVATION_CANDIDATE" in doc_text
    assert "F2_DERIVED_STATE" in doc_text
    assert "ROOT_CAUSE_UNRESOLVED" in doc_text

    # Verify Task B discrimination
    assert "INSUFFICIENT_EVIDENCE" in doc_text

    # Verify Task C recovery inventory
    assert "f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6" in doc_text
    assert "Exact Provider-Native ID Lookup" in doc_text or "EXACT PROVIDER-NATIVE ID LOOKUP" in doc_text.upper()

    # Verify Task D sizing / retirement
    assert "RETIRED / NOT EXECUTABLE AFTER EXACT CONTEXT RECOVERY" in doc_text
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

    assert decisions["hindsight_s1"]["classification"] == "PROVENANCE_LINEAGE_RESIDUAL_CURRENT_CONTENT"
    assert decisions["hindsight_s1"]["rq3_eligibility"] == "NO"
    assert decisions["hindsight_s1"]["sole_empirical_rq3_candidate"] is False
    hs1_obs = decisions["hindsight_s1"]["observed_evidence"]
    assert hs1_obs["rank_2_raw_text_serialized"] is False
    assert hs1_obs["rank_2_exact_text_recovered"] is True
    assert hs1_obs["rank_2_recovery_attempt_id"] == "20261003T003809Z-7a3425bf2f4c"
    assert hs1_obs["rank_2_recovery_method"] == "EXACT_ID_DATABASE_SELECT_READ_ONLY"
    assert hs1_obs["rank_2_recovered_text"] == "Project Alder reports may be sent only to Bob."
    assert hs1_obs["raw_equals_normalized"] is True
    assert hs1_obs["content_identity"] == "CURRENT_V2"
    assert hs1_obs["content_identity_basis"] == "CANONICAL_PROPOSITION_BODY"
    assert hs1_obs["byte_identical_to_per_run_authoritative_source_record"] is False
    assert hs1_obs["proposition_matches_current_v2"] is True
    assert hs1_obs["proposition_matches_stale_v1"] is False
    assert hs1_obs["stale_v1_content"] is False

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
    assert rec["jetstream_read_only_access_was_required_for_recovery"] is True
    assert rec["further_jetstream_access_required"] is False
    assert rec["recovery_status"] == "COMPLETED_VERIFIED"
    assert rec["recovery_attempt_id"] == "20261003T003809Z-7a3425bf2f4c"
    assert len(rec["repetitions"]) == 3
    assert rec["repetitions"]["r1"]["authoritative_source_sha256"] == "ecb4e26bbc1a2f91c214dba0c7cf37fe8267190a68dc0b8418d3c76c4ccb234d"
    assert rec["repetitions"]["r2"]["authoritative_source_sha256"] == "2462e1492a9c8c93ec0d67ca88d4f651bc040d91be012f57bf3ab32e41c59b3d"
    assert rec["repetitions"]["r3"]["authoritative_source_sha256"] == "252a8d190876609383860b4e9dc7874c89cdc3752f1e61289c7a2244a89bc34a"
    assert len(rec["preferred_recovery_hierarchy"]) == 3
    assert rec["preferred_recovery_hierarchy"][0]["method"] == "EXACT_PROVIDER_NATIVE_ID_LOOKUP"
    assert rec["preferred_recovery_hierarchy"][1]["method"] == "EXACT_DATABASE_ROW_LOOKUP"
    assert rec["preferred_recovery_hierarchy"][2]["method"] == "EXACT_CONTENT_SHA_VERIFICATION"
    assert "semantic_search_re_query" in rec["forbidden_recovery_methods"]

    # Task D sizing retirement
    sizing = data["rq3_experimental_size"]
    assert sizing["status_label"] == "RETIRED_NOT_EXECUTABLE_AFTER_EXACT_CONTEXT_RECOVERY"
    assert sizing["empirical_eligible_contexts"] == 0
    assert sizing["contexts"] == 0
    assert sizing["models"] == 3
    assert sizing["repetitions"] == 3
    assert sizing["conditions"] == 3
    assert sizing["maximum_calls"] == 0
    assert sizing["executed_calls"] == 0


def test_hindsight_s1_recovery_review_and_scientific_closure() -> None:
    """Validate Hindsight S1 exact recovery review, content identity, and scientific closure."""
    review_path = REPO_ROOT / "artifacts" / "phase07" / "hindsight-s1-recovery-review.json"
    assert review_path.is_file()
    review = json.loads(review_path.read_text(encoding="utf-8"))

    # Schema and Phase
    assert review["schema_version"] == "memlife-phase07-hindsight-s1-recovery-review-v1"
    assert review["phase"] == "07C-HINDSIGHT-S1-RECOVERY-SCIENTIFIC-CLOSURE"
    assert review["governing_principle"] == "Retrieved != Authoritative"

    # Attempts
    attempts = review["recovery_attempts"]
    assert attempts["attempt_1"]["attempt_id"] == "20261002T230932Z-e018c8b90793"
    assert attempts["attempt_1"]["classification"] == "FAIL_CLOSED_HARNESS_ONLY"
    assert attempts["attempt_1"]["provider_behavior_impact"] is False

    att2 = attempts["attempt_2"]
    assert att2["attempt_id"] == "20261003T003809Z-7a3425bf2f4c"
    assert att2["status"] == "PASS"
    assert att2["completion_marker"] == "VALID / PASS"
    assert att2["transaction_read_only"] is True
    assert att2["recovery_pg0_cleanup_verified"] is True
    assert att2["errors"] == []
    assert att2["target_success_count"] == "3 / 3"

    # Mandatory artifact hashes
    mandatory = att2["mandatory_evidence_byte_sha256"]
    assert mandatory["recovery-ledger.json"] == "4e88e54bcd0a2b00d3b7895adc5fb505f829ad28b04094da2fa7b876b82107ab"
    assert mandatory["recovery-result.json"] == "9505e4b16f9c2c32b43d6a88b56b101636f219d19ab05f5bc3c74f57ff04b89a"
    assert mandatory["source-integrity-after.json"] == "6197e54a663753593e35c9a947f83564edfe10e474223ba0559716e1cc4b1e88"
    assert mandatory["source-integrity-before.json"] == "2048a865f51afba7ee27de36e6d76b50082a409da7fbca7e7bef4a562c71231c"

    # Source tree continuity
    expected_tree_sha = "fce438625dcf9c6775b8172e482bd1e535ed66502bb808a7c4d27501e53a2d0d"
    continuity = att2["source_tree_continuity"]
    assert continuity["source_tree_sha_before"] == expected_tree_sha
    assert continuity["source_tree_sha_after_copy"] == expected_tree_sha
    assert continuity["source_tree_sha_after_final"] == expected_tree_sha
    assert continuity["continuity_verified"] is True

    # Targets & Parents
    targets = review["exact_recovery_targets"]
    assert targets["r1"]["provider_memory_id"] == "d21e1d56-8224-4f7b-b144-9e7124fe4ef4"
    assert targets["r1"]["expected_parent_source_id"] == "bacf3934-5a34-48da-9580-80606d5b9c33"
    assert targets["r1"]["parent_match"] is True
    assert targets["r1"]["raw_equals_normalized"] is True

    assert targets["r2"]["provider_memory_id"] == "5adc67dd-1658-4ddf-a5e7-7b40e00d84a7"
    assert targets["r2"]["expected_parent_source_id"] == "b2fa69b9-d719-4531-86e9-06c69fc739bb"
    assert targets["r2"]["parent_match"] is True
    assert targets["r2"]["raw_equals_normalized"] is True

    assert targets["r3"]["provider_memory_id"] == "ea22a6bc-15be-4639-8060-c9eae4fcc5e5"
    assert targets["r3"]["expected_parent_source_id"] == "dfa63b99-ac6d-467b-b25e-bbc104545a2d"
    assert targets["r3"]["parent_match"] is True
    assert targets["r3"]["raw_equals_normalized"] is True

    # Exact Content & SHA Verification
    expected_v2_text = "Project Alder reports may be sent only to Bob."
    expected_v2_sha = "f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6"
    stale_v1_text = "Project Alder reports may be sent to Alice."
    stale_v1_sha = "d2adb98450de1e8e9257d915779f9ee79c489d17c5d1e4ccea012a7c1f4153a4"

    # Cryptographic validation of constants
    assert hashlib.sha256(expected_v2_text.encode("utf-8")).hexdigest() == expected_v2_sha
    assert hashlib.sha256(stale_v1_text.encode("utf-8")).hexdigest() == stale_v1_sha

    # Recovery content identity check
    ident = review["content_identity_verification"]
    assert ident["recovered_exact_text"] == expected_v2_text
    assert ident["recovered_exact_sha256"] == expected_v2_sha
    assert ident["content_identity"] == "CURRENT_V2"
    assert ident["content_identity_basis"] == "CANONICAL_PROPOSITION_BODY"
    assert ident["byte_identical_to_per_run_authoritative_source_record"] is False
    assert ident["proposition_matches_current_v2"] is True
    assert ident["proposition_matches_stale_v1"] is False
    assert ident["corresponds_to_alder_v2"] is True
    assert ident["corresponds_to_alder_v1"] is False
    assert ident["stale_v1_text_recovered"] is False

    # Authoritative source records SHA validation
    sources = ident["per_run_authoritative_source_records"]
    assert sources["r1"]["sha256"] == "ecb4e26bbc1a2f91c214dba0c7cf37fe8267190a68dc0b8418d3c76c4ccb234d"
    assert sources["r2"]["sha256"] == "2462e1492a9c8c93ec0d67ca88d4f651bc040d91be012f57bf3ab32e41c59b3d"
    assert sources["r3"]["sha256"] == "252a8d190876609383860b4e9dc7874c89cdc3752f1e61289c7a2244a89bc34a"
    assert hashlib.sha256("freeze-v1__hindsight__S1__r1: Project Alder reports may be sent only to Bob.".encode("utf-8")).hexdigest() == "ecb4e26bbc1a2f91c214dba0c7cf37fe8267190a68dc0b8418d3c76c4ccb234d"
    assert hashlib.sha256("freeze-v1__hindsight__S1__r2: Project Alder reports may be sent only to Bob.".encode("utf-8")).hexdigest() == "2462e1492a9c8c93ec0d67ca88d4f651bc040d91be012f57bf3ab32e41c59b3d"
    assert hashlib.sha256("freeze-v1__hindsight__S1__r3: Project Alder reports may be sent only to Bob.".encode("utf-8")).hexdigest() == "252a8d190876609383860b4e9dc7874c89cdc3752f1e61289c7a2244a89bc34a"

    # Target hashes correspond to ALDER_V2 and NOT ALDER_V1
    for r in ("r1", "r2", "r3"):
        assert targets[r]["raw_db_text"] == expected_v2_text
        assert targets[r]["recovered_sha256"] == expected_v2_sha
        assert targets[r]["recovered_sha256"] != stale_v1_sha

    # Scientific Reclassification & RQ3 Eligibility
    reclass = review["scientific_reclassification"]
    assert reclass["target"] == "hindsight_s1"
    assert reclass["new_classification"] == "PROVENANCE_LINEAGE_RESIDUAL_CURRENT_CONTENT"
    assert reclass["rq3_eligibility"] == "NO"
    assert reclass["sole_empirical_rq3_candidate"] is False

    # RQ3 Experimental Status
    rq3_stat = review["rq3_status"]
    assert rq3_stat["eligible_empirical_rq3_contexts"] == 0
    assert rq3_stat["executed_rq3_calls"] == 0
    assert rq3_stat["rq3_status"] == "NOT ACTIVATED"
    assert "RETIRED" in rq3_stat["provisional_27_call_plan_status"]

    # RQ4 Mediator Negative Control Implication
    rq4 = review["rq4_negative_control_implication"]
    assert rq4["is_valuable_mediator_negative_control"] is True
    assert "distinguish superseded lineage association from stale / unauthorized proposition content" in rq4["implication_summary"]


def test_no_secrets_in_phase07_prep_artifacts() -> None:
    """Phase 07 artifacts must not leak any secrets or sensitive keys."""
    forbidden = ["ghp_", "sk-", "AIzaSy", "password", "BEGIN " + "PRIVATE KEY", "client_secret"]
    for path in [
        ARTIFACTS_P07 / "root-cause-evidence.json",
        ARTIFACTS_P07 / "rq3-context-candidates.json",
        ARTIFACTS_P07 / "scientific-decisions.json",
        REPO_ROOT / "artifacts" / "phase07" / "hindsight-s1-recovery-review.json",
        DOCS_EXP / "PHASE_07A_ROOT_CAUSE_EVIDENCE.md",
        DOCS_EXP / "PHASE_07B_RQ3_CONTEXT_CANDIDATES.md",
        DOCS_EXP / "PHASE_07_SCIENTIFIC_DECISIONS.md",
    ]:
        content = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in content, f"Forbidden token {token} found in {path}"
