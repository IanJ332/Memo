from __future__ import annotations

import base64
import hashlib
import importlib.util
import http.client
import json
import os
from pathlib import Path
import subprocess

import pytest

from memlife.adapters.honcho import DirectoryRawArtifactCapture
from memlife.models.provider_acceptance import (
    AcceptanceCapability,
    AcceptanceDecision,
    CapabilityClassification,
    HONCHO_REQUIRED_CAPABILITIES,
)
from memlife.runner.phase08b1 import (
    ACCEPTANCE_DERIVER_FLUSH_ENABLED,
    ACCEPTANCE_DREAM_ENABLED,
    ACCEPTANCE_DREAM_ENABLED_TYPES,
    ACCEPTANCE_DREAM_MODEL_CONFIG,
    ACCEPTANCE_EMBEDDING_VECTOR_DIMENSIONS,
    BASE_COMMIT,
    CURRENT_EMBEDDING_ASSESSMENT,
    CURRENT_PROVENANCE_ASSESSMENT,
    DREAM_OPERATION_BUDGET,
    EMBEDDING_MODEL,
    EFFECTIVE_REASONING_EFFORT,
    DreamOperationGuard,
    LiveCalibrationState,
    PROVENANCE_PROBE_PURPOSE,
    PROVIDER_INTERNAL_MODEL_REQUEST_BUDGET,
    QUIESCENCE_MAX_CHECKS,
    QUIESCENCE_MAX_WINDOW_SECONDS,
    QUIESCENCE_POLL_SECONDS,
    REASONING_EFFORT_COMPATIBILITY_REASON,
    REASONING_EFFORT_COMPATIBILITY_RESOLUTION,
    REQUESTED_REASONING_EFFORT,
    UPSTREAM_COMMIT,
    UPSTREAM_DEFAULT_EMBEDDING_VECTOR_DIMENSIONS,
    UPSTREAM_TAG,
    acceptance_record,
    assessment,
    bound_runtime_manifest,
    build_capability_assessments,
    build_provider_raw_index,
    build_provider_surface_inventory,
    build_scenario_evidence_matrix,
    classify_native_search_result,
    current_baseline_authority_ledger,
    derive_scenario_classifications,
    evidence_binding,
    evaluate_lineage,
    evaluate_quiescence,
    evaluate_trigger_relative_quiescence,
    load_static_api_audit,
    index_adapter_raw_captures,
    stage_a_allows_stage_b,
    surface_inventory_classifications,
    validate_model_endpoint_compatibility,
    validate_queue_status,
    validate_static_api_audit,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REMOTE_SCRIPT = REPO_ROOT / "scripts" / "jetstream" / "phase08b1_honcho_remote.py"
CONTROLLER_SCRIPT = REPO_ROOT / "scripts" / "jetstream" / "phase08b1_honcho.py"


def _controller_module():
    spec = importlib.util.spec_from_file_location("phase08b1_honcho", CONTROLLER_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _remote_module():
    spec = importlib.util.spec_from_file_location(
        "phase08b1_honcho_remote", REMOTE_SCRIPT
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fake_local_embedding_backend(
    remote, tmp_path: Path, *, output_dimensions: int = 384
):
    snapshot = tmp_path / "cache" / "hub" / "models--sentence-transformers--paraphrase-MiniLM-L3-v2" / "snapshots" / ("a" * 40)
    snapshot.mkdir(parents=True)
    (snapshot / "config.json").write_text('{"model_type":"bert"}\n', encoding="utf-8")
    construction: dict[str, object] = {}

    class FakeModel:
        def encode(self, inputs, **kwargs):
            construction["encode_kwargs"] = kwargs
            return [
                [float(len(text))] * output_dimensions
                for text in inputs
            ]

    def factory(model_path, **kwargs):
        construction["model_path"] = model_path
        construction["factory_kwargs"] = kwargs
        return FakeModel()

    backend = remote.LocalSentenceTransformerEmbeddings(
        tmp_path / "cache",
        snapshot_path=snapshot,
        revision="a" * 40,
        model_factory=factory,
        installed_version="6.1.0",
    )
    return backend, construction


def test_runtime_manifest_binds_base_and_preserves_prohibitions() -> None:
    source = json.loads(
        open(
            "manifests/phase-08b1-honcho-live-acceptance.json",
            encoding="utf-8",
        ).read()
    )
    bound = bound_runtime_manifest(source, "20261005T000000Z-deadbeef0001")
    assert bound["required_base_commit"] == BASE_COMMIT
    assert bound["live_execution_authorized"] is True
    assert bound["downstream_model_execution"] is False
    assert bound["downstream_model_calls"] == 0
    assert bound["rq3_activated"] is False
    assert bound["rq3_calls"] == 0
    assert bound["freeze_v2_finalization"] is False


def test_acceptance_decision_is_derived_only_from_frozen_gate() -> None:
    assert HONCHO_REQUIRED_CAPABILITIES == frozenset(
        {
            AcceptanceCapability.CREATE_WRITE,
            AcceptanceCapability.RETRIEVAL,
            AcceptanceCapability.EXACT_PROVIDER_NATIVE_IDS,
            AcceptanceCapability.EXACT_RAW_RESPONSE_CAPTURE,
            AcceptanceCapability.PROVIDER_CONFIGURATION_PINNING,
            AcceptanceCapability.PROVIDER_VERSION_COMMIT_PINNING,
            AcceptanceCapability.DETERMINISTIC_OR_RECORDED_ORDERING,
            AcceptanceCapability.PROVENANCE_RELATIONSHIP_EDGES,
            AcceptanceCapability.QUIESCENCE_ASYNC_COMPLETION_PROOF,
        }
    )
    capabilities = {
        capability: assessment(CapabilityClassification.UNKNOWN)
        for capability in AcceptanceCapability
    }
    for capability in HONCHO_REQUIRED_CAPABILITIES:
        capabilities[capability] = assessment(
            CapabilityClassification.SUPPORTED,
            artifact=f"probes/{capability.value}.json",
            artifact_sha256="a" * 64,
        )
    record = acceptance_record(capabilities, live_calibration_complete=True)
    assert record.decision is AcceptanceDecision.GO
    capabilities[AcceptanceCapability.PROVENANCE_RELATIONSHIP_EDGES] = assessment(
        CapabilityClassification.UNKNOWN
    )
    record = acceptance_record(capabilities, live_calibration_complete=True)
    assert record.decision is AcceptanceDecision.NO_GO


def _unknown_capabilities():
    return {
        capability: assessment(CapabilityClassification.UNKNOWN)
        for capability in AcceptanceCapability
    }


def _gate_passing_capabilities():
    capabilities = _unknown_capabilities()
    for capability in HONCHO_REQUIRED_CAPABILITIES:
        capabilities[capability] = assessment(
            CapabilityClassification.SUPPORTED,
            artifact=f"probes/{capability.value}.json",
            artifact_sha256="a" * 64,
        )
    return capabilities


@pytest.mark.parametrize(
    "missing_gate",
    ["stage_a_passed", "health_passed", "probes_terminal", "scenario_derived"],
    ids=[
        "stage-a-embedding-failure",
        "health-failure",
        "partial-provenance-probe-failure",
        "scenario-derivation-failure",
    ],
)
def test_incomplete_calibration_failure_remains_pending(missing_gate: str) -> None:
    state = LiveCalibrationState()
    gates = {
        "stage_a_passed": True,
        "health_passed": True,
        "probes_terminal": True,
        "scenario_derived": True,
        "evidence_materialized": True,
    }
    gates[missing_gate] = False
    with pytest.raises(RuntimeError, match=missing_gate):
        state.complete(**gates)
    state.fail_operationally(f"{missing_gate} failed")
    record = acceptance_record(
        _unknown_capabilities(),
        live_calibration_complete=state.live_calibration_complete,
    )
    assert state.live_calibration_complete is False
    assert record.decision is AcceptanceDecision.PENDING_LIVE_ACCEPTANCE


def test_complete_calibration_derives_no_go_and_go_without_override() -> None:
    state = LiveCalibrationState()
    state.complete(
        stage_a_passed=True,
        health_passed=True,
        probes_terminal=True,
        scenario_derived=True,
        evidence_materialized=True,
    )
    failed_gate = _gate_passing_capabilities()
    failed_gate[AcceptanceCapability.PROVENANCE_RELATIONSHIP_EDGES] = assessment(
        CapabilityClassification.UNKNOWN
    )
    assert acceptance_record(
        failed_gate,
        live_calibration_complete=state.live_calibration_complete,
    ).decision is AcceptanceDecision.NO_GO
    assert acceptance_record(
        _gate_passing_capabilities(),
        live_calibration_complete=state.live_calibration_complete,
    ).decision is AcceptanceDecision.GO


def test_cleanup_failure_preserves_completed_scientific_decision() -> None:
    state = LiveCalibrationState()
    state.complete(
        stage_a_passed=True,
        health_passed=True,
        probes_terminal=True,
        scenario_derived=True,
        evidence_materialized=True,
    )
    record = acceptance_record(
        _gate_passing_capabilities(), live_calibration_complete=True
    )
    state.fail_operationally("stack shutdown failed")
    assert state.live_calibration_complete is True
    assert state.operational_status == "BLOCKED"
    assert record.decision is AcceptanceDecision.GO


def _openapi_fixture(*, include_update: bool = False) -> dict[str, object]:
    message_item: dict[str, object] = {"post": {"operationId": "create_message"}}
    if include_update:
        message_item["put"] = {"operationId": "update_message"}
    return {
        "openapi": "3.1.0",
        "paths": {
            "/v3/workspaces/{workspace_id}/search": {
                "post": {"operationId": "search_workspace"}
            },
            "/v3/workspaces/{workspace_id}/sessions/{session_id}/messages": (
                message_item
            ),
            "/v3/workspaces/{workspace_id}/sessions/{session_id}/messages/list": {
                "post": {"operationId": "list_messages"}
            },
            "/v3/workspaces/{workspace_id}/conclusions/list": {
                "post": {"operationId": "list_conclusions"}
            },
        },
        "components": {"schemas": {"Message": {"properties": {"id": {}}}}},
    }


def test_only_live_openapi_inventory_can_produce_surface_unsupported() -> None:
    static_results = surface_inventory_classifications(load_static_api_audit())
    assert set(static_results.values()) == {CapabilityClassification.UNKNOWN}

    inventory = build_provider_surface_inventory(
        _openapi_fixture(),
        raw_artifact="provider-raw-responses/002-openapi.json",
        raw_sha256="a" * 64,
        raw_bytes=100,
    )
    live_results = surface_inventory_classifications(inventory)
    assert inventory["workspace_message_search_operations"] == [
        {
            "method": "POST",
            "path": "/v3/workspaces/{workspace_id}/search",
            "operation_id": "search_workspace",
        }
    ]
    assert live_results[AcceptanceCapability.UPDATE_SUPERSEDE] is (
        CapabilityClassification.UNSUPPORTED
    )
    assert live_results[AcceptanceCapability.HARD_DELETE] is (
        CapabilityClassification.UNSUPPORTED
    )
    with_update = build_provider_surface_inventory(
        _openapi_fixture(include_update=True),
        raw_artifact="provider-raw-responses/002-openapi.json",
        raw_sha256="b" * 64,
        raw_bytes=101,
    )
    assert surface_inventory_classifications(with_update)[
        AcceptanceCapability.UPDATE_SUPERSEDE
    ] is CapabilityClassification.UNKNOWN


def test_capability_assessments_require_exact_matching_evidence(
    tmp_path: Path,
) -> None:
    classifications = {
        capability: CapabilityClassification.UNKNOWN
        for capability in AcceptanceCapability
    }
    notes = {capability: "test" for capability in AcceptanceCapability}
    capability_artifacts = {
        AcceptanceCapability.CREATE_WRITE: "probes/create-write/evidence.json",
        AcceptanceCapability.RETRIEVAL: "probes/retrieval/evidence.json",
        AcceptanceCapability.EXACT_PROVIDER_NATIVE_IDS: (
            "probes/exact-native-ids/identity-map.json"
        ),
        AcceptanceCapability.PROVENANCE_RELATIONSHIP_EDGES: "lineage.json",
        AcceptanceCapability.QUIESCENCE_ASYNC_COMPLETION_PROOF: "quiescence.json",
    }
    bindings = {}
    for capability, artifact in capability_artifacts.items():
        path = tmp_path / artifact
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'{{"capability":"{capability.value}"}}\n', encoding="utf-8")
        digest = __import__("hashlib").sha256(path.read_bytes()).hexdigest()
        classifications[capability] = CapabilityClassification.SUPPORTED
        bindings[capability] = evidence_binding(
            capability, artifact=artifact, artifact_sha256=digest
        )
    built = build_capability_assessments(
        tmp_path, classifications, bindings, notes
    )
    for capability, artifact in capability_artifacts.items():
        assert built[capability].evidence_artifact == artifact

    config_artifact = tmp_path / "provider-config.json"
    config_artifact.write_text(
        '{"runtime_verified":false}\n', encoding="utf-8"
    )
    config_digest = __import__("hashlib").sha256(
        config_artifact.read_bytes()
    ).hexdigest()
    unknown_bindings = dict(bindings)
    unknown_bindings[AcceptanceCapability.PROVIDER_CONFIGURATION_PINNING] = (
        evidence_binding(
            AcceptanceCapability.PROVIDER_CONFIGURATION_PINNING,
            artifact="provider-config.json",
            artifact_sha256=config_digest,
        )
    )
    built_with_unknown_evidence = build_capability_assessments(
        tmp_path, classifications, unknown_bindings, notes
    )
    unknown_config = built_with_unknown_evidence[
        AcceptanceCapability.PROVIDER_CONFIGURATION_PINNING
    ]
    assert unknown_config.classification is CapabilityClassification.UNKNOWN
    assert unknown_config.evidence_artifact == "provider-config.json"
    assert unknown_config.evidence_sha256 == config_digest

    wrong = dict(bindings)
    wrong[AcceptanceCapability.CREATE_WRITE] = bindings[
        AcceptanceCapability.RETRIEVAL
    ]
    with pytest.raises(ValueError, match="another capability"):
        build_capability_assessments(tmp_path, classifications, wrong, notes)

    generic = tmp_path / "provider-raw-response.json"
    generic.write_text('{"provider_observed":true}\n', encoding="utf-8")
    generic_digest = __import__("hashlib").sha256(generic.read_bytes()).hexdigest()
    wrong = dict(bindings)
    wrong[AcceptanceCapability.CREATE_WRITE] = evidence_binding(
        AcceptanceCapability.CREATE_WRITE,
        artifact="provider-raw-response.json",
        artifact_sha256=generic_digest,
    )
    with pytest.raises(ValueError, match="not valid for that capability"):
        build_capability_assessments(tmp_path, classifications, wrong, notes)

    wrong_sha = {capability: dict(binding) for capability, binding in bindings.items()}
    wrong_sha[AcceptanceCapability.CREATE_WRITE]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        build_capability_assessments(
            tmp_path, classifications, wrong_sha, notes
        )


def test_empty_raw_index_is_not_provider_observed_and_adapter_captures_are_indexed(
    tmp_path: Path,
) -> None:
    empty = build_provider_raw_index([], [])
    assert empty["provider_observed"] is False
    assert empty["evidence_class"] is None

    capture = DirectoryRawArtifactCapture(tmp_path / "probes")
    identity = capture.capture_raw(
        probe_name="honcho_capability_create_write_v1",
        native_bytes=b'{"id":"native-1"}',
    )
    indexed = index_adapter_raw_captures(
        tmp_path,
        {
            "honcho_capability_create_write_v1": identity.model_dump(mode="json")
        },
    )
    assert indexed[0]["sha256"] == identity.sha256
    assert indexed[0]["bytes"] == identity.byte_count
    assert indexed[0]["captured_before_normalization"] is True
    combined = build_provider_raw_index([], indexed)
    assert combined["provider_observed"] is True
    assert combined["adapter_raw_captures"] == indexed
    remote_source = REMOTE_SCRIPT.read_text(encoding="utf-8")
    assert '"provider-evidence-index.json"' in remote_source
    assert '"adapter_raw_captures": adapter_capture_index' in remote_source


def test_retrieval_does_not_automatically_support_raw_inspection() -> None:
    source = REMOTE_SCRIPT.read_text(encoding="utf-8")
    assert (
        "classifications[AcceptanceCapability.RAW_INSPECTION] = "
        "CapabilityClassification.UNKNOWN"
    ) in source
    assert "RAW_INSPECTION] = CapabilityClassification.SUPPORTED" not in source


def test_pinned_static_api_audit_is_complete_and_exact() -> None:
    audit = load_static_api_audit()
    assert validate_static_api_audit(audit) == []
    assert audit["upstream"] == {
        "version": "3.2.1",
        "tag": UPSTREAM_TAG,
        "commit": UPSTREAM_COMMIT,
        "source_root": ".local/review/honcho-upstream-v3.2.1",
    }
    endpoints = {item["id"]: item for item in audit["endpoints"]}
    assert endpoints["message_delete"]["available"] is False
    assert endpoints["schedule_dream"]["path"].endswith("/schedule_dream")
    assert endpoints["queue_status"]["session_id_filter_supported"] is True
    assert endpoints["conclusion_get"]["method"] == "GET"
    assert endpoints["workspace_message_search"] == {
        "id": "workspace_message_search",
        "available": True,
        "method": "POST",
        "path": "/v3/workspaces/{workspace_id}/search",
        "request_schema": "WorkspaceMessageSearchOptions",
        "request_body": {
            "query": "<deterministic_fictional_query>",
            "filters": {"session_id": "<isolated_session_id>"},
            "limit": "integer[1,100]",
        },
        "response_status": [200],
        "response_shape": "list[Message]",
        "session_scoping": "filters.session_id",
        "source_basis": (
            "src/routers/workspaces.py:search_workspace; "
            "src/schemas/api.py:WorkspaceMessageSearchOptions,Message"
        ),
    }
    for endpoint in endpoints.values():
        assert "request_body" in endpoint
        assert "response_status" in endpoint
        assert "response_shape" in endpoint
        assert endpoint["source_basis"]


def test_split_embedding_config_and_authorized_provenance_config_are_pinned() -> None:
    audit = load_static_api_audit()
    assert CURRENT_EMBEDDING_ASSESSMENT == (
        "LOCAL_CACHE_ONLY_EMBEDDING_PREFLIGHT_REQUIRED"
    )
    assert CURRENT_PROVENANCE_ASSESSMENT == (
        "AUTHORIZED_NATIVE_DREAM_LINEAGE_PROBE_PENDING_LIVE_OBSERVATION"
    )
    embedding = audit["configuration_contract"]["embedding"]
    assert embedding["mandatory_for_required_path"] is True
    assert embedding["natively_disableable_for_required_create_derive_conclusion_path"] is False
    assert embedding["openai_compatible_path"] == "/embeddings"
    assert embedding["default_vector_dimensions"] == (
        UPSTREAM_DEFAULT_EMBEDDING_VECTOR_DIMENSIONS
    )
    assert UPSTREAM_DEFAULT_EMBEDDING_VECTOR_DIMENSIONS == 1536
    acceptance = embedding["phase08b1_acceptance_configuration"]
    assert acceptance == {
        "backend": "local_cpu_sentence_transformer",
        "package": "sentence-transformers",
        "package_version": "6.1.0",
        "model": EMBEDDING_MODEL,
        "vector_dimensions": ACCEPTANCE_EMBEDDING_VECTOR_DIMENSIONS,
        "offline_cache_only": True,
        "hosted_embedding_forwarding": False,
    }
    assert ACCEPTANCE_EMBEDDING_VECTOR_DIMENSIONS == 384
    assessments = audit["current_assessments"]
    assert assessments["embedding_configuration_modified"] is True
    assert assessments["provider_config_change_required_before_live_retry"] is False
    assert assessments[
        "provider_config_change_applied_pending_live_validation"
    ] is True
    assert assessments["honcho_acceptance"] == "PENDING_LIVE_ACCEPTANCE"
    dream = audit["configuration_contract"]["dream"]
    assert dream["current_enabled"] is True
    assert dream["enabled_types"] == ["omni"]
    assert dream["authorized_change_materialized"] is True
    assert dream["operation_budget"] == 1
    assert dream["deduction_model"] == ACCEPTANCE_DREAM_MODEL_CONFIG
    assert dream["induction_model"] == ACCEPTANCE_DREAM_MODEL_CONFIG
    assert dream["explicit_source_ids_semantics"] == "empty"
    request_contract = audit["configuration_contract"]["openai_request_contract"]
    assert request_contract["pinned_sdk"] == "openai==2.36.0"
    assert request_contract["deriver_temperature"] is None
    assert request_contract["deriver_structured_output_mode"] == "json_schema"
    assert request_contract["deriver_strict_json_schema"] is True
    assert request_contract["dream_reasoning_effort_field"] == "reasoning_effort"
    assert request_contract["requested_reasoning_effort"] == "minimal"
    assert request_contract["effective_reasoning_effort"] == "low"
    assert request_contract["compatibility_resolution"] == "MINIMAL_TO_LOW"
    assert request_contract["compatibility_reason"] == (
        "Jetstream hosted chat endpoint accepts only low, medium, or high"
    )
    remote_source = REMOTE_SCRIPT.read_text(encoding="utf-8")
    assert '"effective_configuration_status": "NOT_OBSERVED"' in remote_source
    assert '"runtime_verified": False' in remote_source
    assert '"live_compatibility_evidence": "stage-a-preflight.json"' in remote_source
    assert "executing Honcho image identity was not observable" in remote_source


def test_queue_status_contract_and_observable_quiescence() -> None:
    pending = {
        "total_work_units": 1,
        "completed_work_units": 0,
        "in_progress_work_units": 0,
        "pending_work_units": 1,
    }
    complete = {
        "total_work_units": 1,
        "completed_work_units": 1,
        "in_progress_work_units": 0,
        "pending_work_units": 0,
    }
    validate_queue_status(pending)
    assert evaluate_quiescence([pending, complete, complete])["status"] == "SUPPORTED"
    sleep_only_empty = {
        "total_work_units": 0,
        "completed_work_units": 0,
        "in_progress_work_units": 0,
        "pending_work_units": 0,
    }
    result = evaluate_quiescence([sleep_only_empty, sleep_only_empty])
    assert result["status"] == "UNKNOWN"
    assert result["sleep_only_success"] is False
    with pytest.raises(ValueError, match="pending_work_units"):
        validate_queue_status({**pending, "pending_work_units": "0"})


def _queue(total: int, completed: int, pending: int, active: int) -> dict[str, int]:
    return {
        "total_work_units": total,
        "completed_work_units": completed,
        "pending_work_units": pending,
        "in_progress_work_units": active,
    }


def test_explicit_quiescence_requires_new_work_relative_to_pre_write_baseline() -> None:
    baseline = _queue(4, 4, 0, 0)
    observations = [
        _queue(5, 4, 1, 0),
        _queue(5, 5, 0, 0),
        _queue(5, 5, 0, 0),
    ]
    result = evaluate_trigger_relative_quiescence(baseline, observations)
    assert result["status"] == "SUPPORTED"
    assert result["new_work_observed_after_trigger"] is True
    assert result["stable_empty_checks"] == 2


def test_dream_quiescence_cannot_reuse_old_completed_work() -> None:
    baseline = _queue(8, 8, 0, 0)
    old_counts = [_queue(8, 8, 0, 0), _queue(8, 8, 0, 0)]
    result = evaluate_trigger_relative_quiescence(baseline, old_counts)
    assert result["status"] == "UNKNOWN"
    assert result["new_work_observed_after_trigger"] is False
    assert result["stable_empty_checks"] == 2
    nonempty_baseline = _queue(9, 8, 1, 0)
    prior_work_finishes = evaluate_trigger_relative_quiescence(
        nonempty_baseline,
        [_queue(9, 9, 0, 0), _queue(9, 9, 0, 0)],
    )
    assert prior_work_finishes["status"] == "UNKNOWN"
    assert prior_work_finishes["baseline_empty_at_trigger"] is False
    assert prior_work_finishes["new_work_observed_after_trigger"] is False


def test_quiescence_counter_reset_and_bounded_timeout_remain_unknown() -> None:
    baseline = _queue(9, 9, 0, 0)
    reset = evaluate_trigger_relative_quiescence(
        baseline,
        [_queue(0, 0, 0, 0), _queue(0, 0, 0, 0)],
    )
    assert reset["status"] == "UNKNOWN"
    assert reset["counter_reset_or_cleanup_ambiguity"] is True

    timeout = evaluate_trigger_relative_quiescence(
        baseline,
        [_queue(9, 9, 0, 0)] * QUIESCENCE_MAX_CHECKS,
    )
    assert QUIESCENCE_MAX_CHECKS == 60
    assert QUIESCENCE_POLL_SECONDS == 5
    assert QUIESCENCE_MAX_WINDOW_SECONDS == 300
    assert timeout["status"] == "UNKNOWN"
    assert timeout["bounded_timeout_without_support"] is True
    source = REMOTE_SCRIPT.read_text(encoding="utf-8")
    explicit_baseline = source.index(
        'explicit_queue_baseline = queue_observation('
    )
    write_trigger = source.index("written = adapter.write(")
    dream_baseline = source.index(
        'dream_queue_baseline = queue_observation("dream-queue-baseline", 0)'
    )
    dream_trigger = source.index(
        'f"v3/workspaces/{workspace}/schedule_dream"'
    )
    assert explicit_baseline < write_trigger
    assert dream_baseline < dream_trigger


def test_native_search_non_match_is_unknown_and_order_comes_from_search() -> None:
    non_match = classify_native_search_result(
        "created-1", ["other-1", "other-2"], [1, 2]
    )
    assert non_match[AcceptanceCapability.RETRIEVAL] is (
        CapabilityClassification.UNKNOWN
    )
    assert non_match[AcceptanceCapability.EXACT_PROVIDER_NATIVE_IDS] is (
        CapabilityClassification.UNKNOWN
    )
    assert non_match[
        AcceptanceCapability.DETERMINISTIC_OR_RECORDED_ORDERING
    ] is CapabilityClassification.SUPPORTED

    matched = classify_native_search_result(
        "created-1", ["other-1", "created-1"], [1, 2]
    )
    assert matched[AcceptanceCapability.RETRIEVAL] is (
        CapabilityClassification.SUPPORTED
    )
    assert matched[AcceptanceCapability.EXACT_PROVIDER_NATIVE_IDS] is (
        CapabilityClassification.SUPPORTED
    )
    source = REMOTE_SCRIPT.read_text(encoding="utf-8")
    assert '"workspace_search_provider_native_ids": retrieved_ids' in source
    assert '"provider_returned_order": retrieved_ids' in source
    assert '"captures": [create_raw, retrieval_raw]' in source
    assert "retrieval_provider_native_ids" not in source


def test_lineage_support_requires_a_resolvable_native_derived_edge() -> None:
    explicit = {
        "id": "explicit-1",
        "level": "explicit",
        "source_ids": [],
        "content": "fictional fact",
    }
    assert evaluate_lineage([explicit], {})["status"] == "UNKNOWN"

    derived = {
        "id": "deductive-1",
        "level": "deductive",
        "source_ids": ["explicit-1"],
        "content": "fictional deduction",
    }
    unresolved = evaluate_lineage([explicit, derived], {})
    assert unresolved["status"] == "UNKNOWN"
    assert unresolved["unresolved_edges"] == [
        {"conclusion_id": "deductive-1", "source_id": "explicit-1"}
    ]
    supported = evaluate_lineage(
        [explicit, derived], {"explicit-1": {"id": "explicit-1"}}
    )
    assert supported["status"] == "SUPPORTED"
    assert supported["explicit_conclusions"] == [explicit]
    assert supported["derived_conclusions"] == [derived]
    assert supported["text_matching_fallback_used"] is False


def test_remote_design_separates_deriver_dream_and_model_roles() -> None:
    source = REMOTE_SCRIPT.read_text(encoding="utf-8")
    assert "explicit-conclusions-list" in source
    assert "post-dream-conclusions-list" in source
    assert 'f"v3/workspaces/{workspace}/schedule_dream"' in source
    assert 'f"v3/workspaces/{workspace}/conclusions/{source_id}"' in source
    assert '"DELETE",' not in source
    assert "TEXT_MODEL = \"gpt-oss-120b\"" in source
    assert (
        'EMBEDDING_MODEL = "sentence-transformers/paraphrase-MiniLM-L3-v2"'
        in source
    )
    assert "DERIVER_MODEL_CONFIG__MODEL" in source
    assert "EMBEDDING_MODEL_CONFIG__MODEL" in source
    assert '"DREAM_ENABLED=true"' in source
    assert "DREAM_CONFIG_CHANGE_AUTHORIZED = True" in source
    assert '"DERIVER_FLUSH_ENABLED=true"' in source
    assert "DERIVER_FLUSH_CHANGE_AUTHORIZED = True" in source
    assert "DreamOperationGuard()" in source
    assert "dream_guard.authorize(PROVENANCE_PROBE_PURPOSE)" in source
    assert source.count('f"v3/workspaces/{workspace}/schedule_dream"') == 1


def test_two_stage_preflight_precedes_provider_start_and_is_accounted() -> None:
    source = REMOTE_SCRIPT.read_text(encoding="utf-8")
    static_index = source.index("stage_a = static_stage_a_preflight")
    compatibility_index = source.index("compatibility = run_model_endpoint_preflight")
    provider_start_index = source.index(
        '[*compose_cmd, "up", "-d", "redis", "api", "deriver"]'
    )
    assert static_index < compatibility_index < provider_start_index
    assert '"provider_internal_model_calls": 0' in source
    assert '"downstream_model_calls": 0' in source
    assert '"rq3_calls": 0' in source
    assert '"/v1/embeddings"' in source
    assert '"type": "json_schema"' in source
    assert '"tool_choice": "required"' in source


def test_authorized_flush_and_minimal_fixture_are_recorded() -> None:
    audit = load_static_api_audit()
    batching = audit["configuration_contract"]["deriver_batching"]
    assert batching["default_work_unit_target_tokens"] == 512
    assert batching["default_max_age_seconds"] == 1800
    assert batching["authorized_acceptance_only_change"] == "DERIVER_FLUSH_ENABLED=true"
    assert batching["acceptance_flush_enabled"] is True
    assert audit["fixture_contract"]["one_peer_self_observation_supported"] is True
    assert audit["fixture_contract"]["current_one_short_message_sufficient_under_current_config"] is True
    assert audit["fixture_contract"]["scientific_scenario_semantics_changed"] is False
    assert audit["fixture_contract"]["messages"] == [
        {
            "content": "Fictional benchmark subject Rowan keeps the amber notebook in cabinet seven.",
            "metadata": {"benchmark": "phase08b1", "fictional": True},
        }
    ]


def test_dream_guard_is_one_shot_and_provenance_only() -> None:
    assert DREAM_OPERATION_BUDGET == 1
    guard = DreamOperationGuard()
    assert guard.authorize(PROVENANCE_PROBE_PURPOSE) == 1
    assert guard.scheduled == 1
    with pytest.raises(RuntimeError, match="budget exhausted"):
        guard.authorize(PROVENANCE_PROBE_PURPOSE)
    assert guard.scheduled == 1

    wrong_purpose = DreamOperationGuard()
    with pytest.raises(RuntimeError, match="only for the provenance"):
        wrong_purpose.authorize("RETRIEVAL")
    assert wrong_purpose.scheduled == 0


def test_stage_a_model_gates_fail_closed_before_stage_b() -> None:
    passing = {
        "structured_output_supported": True,
        "structured_output_mode": "json_schema",
        "structured_output_strict": True,
        "deriver_temperature_omitted": True,
        "dream_tool_calling_supported": True,
        "requested_reasoning_effort": REQUESTED_REASONING_EFFORT,
        "effective_reasoning_effort": EFFECTIVE_REASONING_EFFORT,
        "compatibility_resolution": REASONING_EFFORT_COMPATIBILITY_RESOLUTION,
        "compatibility_reason": REASONING_EFFORT_COMPATIBILITY_REASON,
        "embedding_supported": True,
        "embedding_vector_dimensions": 384,
        "text_backend": "jetstream_hosted",
        "text_model": "gpt-oss-120b",
        "embedding_backend": "local_sentence_transformer",
        "embedding_model": EMBEDDING_MODEL,
        "embedding_offline_cache_only": True,
        "hosted_embedding_forwarding": False,
    }
    stage_a = {
        "status": "PASS",
        "blockers": [],
        "model_endpoint_compatibility": passing,
    }
    assert validate_model_endpoint_compatibility(passing) == []
    assert stage_a_allows_stage_b(stage_a) is True

    for key, expected in (
        ("structured_output_supported", "STRUCTURED_OUTPUT_COMPATIBILITY_FAILED"),
        ("dream_tool_calling_supported", "DREAM_TOOL_COMPATIBILITY_FAILED"),
        ("embedding_supported", "EMBEDDING_COMPATIBILITY_FAILED"),
    ):
        failed = {**passing, key: False}
        assert expected in validate_model_endpoint_compatibility(failed)
        assert stage_a_allows_stage_b(
            {**stage_a, "model_endpoint_compatibility": failed}
        ) is False
    wrong_dimensions = {**passing, "embedding_vector_dimensions": 3072}
    assert "EMBEDDING_DIMENSION_COMPATIBILITY_FAILED" in (
        validate_model_endpoint_compatibility(wrong_dimensions)
    )
    assert stage_a_allows_stage_b(
        {**stage_a, "model_endpoint_compatibility": wrong_dimensions}
    ) is False
    wrong_effort = {**passing, "effective_reasoning_effort": "minimal"}
    assert "DREAM_REASONING_EFFORT_COMPATIBILITY_FAILED" in (
        validate_model_endpoint_compatibility(wrong_effort)
    )
    loose_schema = {**passing, "structured_output_strict": False}
    assert "STRUCTURED_OUTPUT_REQUEST_FIDELITY_FAILED" in (
        validate_model_endpoint_compatibility(loose_schema)
    )


def test_runtime_env_materializes_only_authorized_config(tmp_path: Path) -> None:
    provider = tmp_path / "provider"
    state = tmp_path / "state"
    provider.mkdir()
    state.mkdir()
    pinned_compose = (
        REPO_ROOT
        / ".local"
        / "review"
        / "honcho-upstream-v3.2.1"
        / "docker-compose.yml.example"
    ).read_text(encoding="utf-8")
    (provider / "docker-compose.yml.example").write_text(
        pinned_compose,
        encoding="utf-8",
    )
    compose_path, env_path = _remote_module().write_runtime_files(provider, state)
    compose = compose_path.read_text(encoding="utf-8")
    assert compose.count(f"- {state / 'lancedb'}:/app/lancedb_data") == 2
    assert compose.count(f"- {state / 'postgres'}:/var/lib/postgresql/data/") == 1
    assert compose.count(f"- {state / 'redis'}:/data") == 1
    assert compose.count('      - "host.docker.internal:host-gateway"') == 2
    assert "- lancedb-data:/app/lancedb_data" not in compose
    assert "- pgdata:/var/lib/postgresql/data/" not in compose
    assert "- redis-data:/data" not in compose
    env = env_path.read_text(encoding="utf-8").splitlines()
    assert ACCEPTANCE_DERIVER_FLUSH_ENABLED is True
    assert ACCEPTANCE_DREAM_ENABLED is True
    assert ACCEPTANCE_DREAM_ENABLED_TYPES == ("omni",)
    assert "DERIVER_FLUSH_ENABLED=true" in env
    assert "DREAM_ENABLED=true" in env
    assert 'DREAM_ENABLED_TYPES=["omni"]' in env
    for prefix in ("DREAM_DEDUCTION_MODEL_CONFIG", "DREAM_INDUCTION_MODEL_CONFIG"):
        assert f"{prefix}__TRANSPORT=openai" in env
        assert f"{prefix}__MODEL=gpt-oss-120b" in env
        assert (
            f"{prefix}__OVERRIDES__BASE_URL=http://host.docker.internal:18081/v1/"
            in env
        )
        assert f"{prefix}__TEMPERATURE=0" in env
        assert f"{prefix}__THINKING_EFFORT=minimal" in env

    # Candidate3 must preserve candidate2's embedding configuration verbatim.
    assert "EMBEDDING_MODEL_CONFIG__TRANSPORT=openai" in env
    assert f"EMBEDDING_MODEL_CONFIG__MODEL={EMBEDDING_MODEL}" in env
    assert (
        "EMBEDDING_MODEL_CONFIG__OVERRIDES__BASE_URL="
        "http://host.docker.internal:18081/v1/" in env
    )
    assert "EMBEDDING_MODEL_CONFIG__ENCODING_FORMAT_MODE=float" in env
    assert "EMBEDDING_VECTOR_DIMENSIONS=384" in env
    assert PROVIDER_INTERNAL_MODEL_REQUEST_BUDGET == 100
    with pytest.raises(FileExistsError):
        _remote_module().write_runtime_files(provider, state)


def _managed_runtime_fixture(
    tmp_path: Path, *, attempt_id: str = "prior-attempt"
) -> tuple[object, Path, Path, Path, Path]:
    remote = _remote_module()
    mount = tmp_path / "mount"
    provider = tmp_path / "provider"
    state = (
        mount
        / "memlife"
        / "runs"
        / "phase08b"
        / "attempts"
        / attempt_id
        / "provider-state"
    )
    provider.mkdir()
    state.mkdir(parents=True)
    pinned_compose = (
        REPO_ROOT
        / ".local"
        / "review"
        / "honcho-upstream-v3.2.1"
        / "docker-compose.yml.example"
    ).read_text(encoding="utf-8")
    (provider / "docker-compose.yml.example").write_text(
        pinned_compose, encoding="utf-8"
    )
    compose, env = remote.write_runtime_files(provider, state)
    return remote, mount, provider, compose, env


def test_runtime_residue_classifier_accepts_no_residue(tmp_path: Path) -> None:
    remote = _remote_module()
    provider = tmp_path / "provider"
    provider.mkdir()
    result = remote.classify_managed_runtime_residue(
        provider, mount=tmp_path / "mount"
    )
    assert result["status"] == "NO_RESIDUE"
    assert result["cleanup_tokens"] == []


@pytest.mark.parametrize(
    ("model", "dimensions", "classification"),
    [
        ("gpt-oss-120b", 1536, "PHASE08B1_CANDIDATE8_RUNTIME_ENV"),
        (
            "sentence-transformers/paraphrase-MiniLM-L3-v2",
            384,
            "PHASE08B1_CANDIDATE9_RUNTIME_ENV",
        ),
    ],
)
def test_runtime_residue_classifier_accepts_only_candidate8_or_candidate9(
    tmp_path: Path, model: str, dimensions: int, classification: str
) -> None:
    remote, mount, provider, _, env = _managed_runtime_fixture(tmp_path)
    env.write_text(
        remote.runtime_environment_content(
            embedding_model=model,
            embedding_vector_dimensions=dimensions,
        ),
        encoding="utf-8",
        newline="\n",
    )
    result = remote.classify_managed_runtime_residue(provider, mount=mount)
    assert result["status"] == "RECOGNIZED_MANAGED_RESIDUE"
    assert result["prior_attempt_id"] == "prior-attempt"
    prior_state = Path(result["prior_state_path"])
    assert prior_state.name == "provider-state"
    assert prior_state.parent.name == "prior-attempt"
    assert {item["classification"] for item in result["files"]} == {
        classification,
        "PHASE08B1_RUNTIME_COMPOSE",
    }


def test_recognized_residue_evidence_is_secret_safe_and_precedes_removal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    remote, mount, provider, compose, env = _managed_runtime_fixture(tmp_path)
    attempt_root = tmp_path / "new-attempt"
    attempt_root.mkdir()
    original_cleanup = remote.cleanup_runtime_files
    cleanup_observation: dict[str, object] = {}

    def observing_cleanup(identities):
        evidence_path = attempt_root / "preexisting-runtime-residue.json"
        cleanup_observation["evidence_exists"] = evidence_path.is_file()
        cleanup_observation["evidence"] = json.loads(
            evidence_path.read_text(encoding="utf-8")
        )
        return original_cleanup(identities)

    monkeypatch.setattr(remote, "cleanup_runtime_files", observing_cleanup)
    result = remote.preserve_and_remove_managed_runtime_residue(
        provider, mount=mount, attempt_root=attempt_root
    )
    assert cleanup_observation["evidence_exists"] is True
    evidence = cleanup_observation["evidence"]
    assert evidence["redacted_parsed_environment"]["LLM_OPENAI_API_KEY"] == (
        "<REDACTED>"
    )
    assert "empty" not in json.dumps(evidence["redacted_parsed_environment"])
    assert evidence["compose_sha256"]
    assert result["cleanup"]["status"] == "PASS"
    assert not compose.exists()
    assert not env.exists()


def test_runtime_residue_classifier_rejects_arbitrary_env_without_deleting(
    tmp_path: Path,
) -> None:
    remote = _remote_module()
    mount = tmp_path / "mount"
    provider = tmp_path / "provider"
    provider.mkdir()
    env = provider / ".env"
    env.write_text("ARBITRARY=true\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="UNRECOGNIZED_RUNTIME_ENV"):
        remote.classify_managed_runtime_residue(provider, mount=mount)
    assert env.read_text(encoding="utf-8") == "ARBITRARY=true\n"


def test_runtime_residue_classifier_rejects_arbitrary_compose_without_deleting(
    tmp_path: Path,
) -> None:
    remote, mount, provider, compose, env = _managed_runtime_fixture(tmp_path)
    env.unlink()
    compose.write_text(
        compose.read_text(encoding="utf-8") + "# arbitrary\n",
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(RuntimeError, match="UNRECOGNIZED_RUNTIME_COMPOSE"):
        remote.classify_managed_runtime_residue(provider, mount=mount)
    assert compose.exists()
    assert compose.read_text(encoding="utf-8").endswith("# arbitrary\n")


def test_current_runtime_files_are_identity_cleaned_on_normal_path(
    tmp_path: Path,
) -> None:
    remote, _, _, compose, env = _managed_runtime_fixture(tmp_path)
    identities = remote.capture_runtime_file_identities((compose, env))
    cleanup = remote.cleanup_runtime_files(identities)
    assert cleanup["status"] == "PASS"
    assert {item["status"] for item in cleanup["files"]} == {"REMOVED"}
    assert not compose.exists()
    assert not env.exists()


def test_current_runtime_files_are_cleaned_on_stage_a_failure_path(
    tmp_path: Path,
) -> None:
    remote, _, _, compose, env = _managed_runtime_fixture(tmp_path)
    identities = remote.capture_runtime_file_identities((compose, env))
    cleanup = None
    try:
        raise RuntimeError("simulated Stage-A blocker")
    except RuntimeError:
        pass
    finally:
        cleanup = remote.cleanup_runtime_files(identities)
    assert cleanup["status"] == "PASS"
    assert not compose.exists()
    assert not env.exists()
    source = REMOTE_SCRIPT.read_text(encoding="utf-8")
    main_finally = source.index("    finally:", source.index("def main()"))
    runtime_cleanup = source.index(
        "runtime_cleanup = cleanup_runtime_files(", main_finally
    )
    lifecycle_write = source.index(
        'attempt_root / "runtime-file-lifecycle.json"', runtime_cleanup
    )
    assert main_finally < runtime_cleanup < lifecycle_write


def test_modified_current_runtime_file_is_preserved_with_cleanup_blocker(
    tmp_path: Path,
) -> None:
    remote, _, _, compose, env = _managed_runtime_fixture(tmp_path)
    identities = remote.capture_runtime_file_identities((compose, env))
    env.write_text("CHANGED=true\n", encoding="utf-8")
    cleanup = remote.cleanup_runtime_files(identities)
    assert cleanup["status"] == "BLOCKED"
    assert cleanup["blockers"] == ["RUNTIME_FILE_IDENTITY_CHANGED: .env"]
    assert env.read_text(encoding="utf-8") == "CHANGED=true\n"
    assert not compose.exists()


def test_runtime_file_lifecycle_uses_no_git_cleanup_commands() -> None:
    source = REMOTE_SCRIPT.read_text(encoding="utf-8")
    lifecycle = source[
        source.index("def runtime_file_identity(") :
        source.index("def validate_provider_source_checkout(")
    ]
    for forbidden in ('"clean"', '"reset"', '"restore"'):
        assert forbidden not in lifecycle


def test_declared_config_is_separate_and_cannot_claim_runtime_support(
    tmp_path: Path,
) -> None:
    remote = _remote_module()
    provider = tmp_path / "provider"
    state = tmp_path / "state"
    provider.mkdir()
    state.mkdir()
    for name in ("postgres", "redis", "lancedb"):
        (state / name).mkdir()
    pinned_compose = (
        REPO_ROOT
        / ".local"
        / "review"
        / "honcho-upstream-v3.2.1"
        / "docker-compose.yml.example"
    ).read_text(encoding="utf-8")
    (provider / "docker-compose.yml.example").write_text(
        pinned_compose, encoding="utf-8"
    )
    compose, env = remote.write_runtime_files(provider, state)
    declared = remote.build_declared_provider_configuration(
        compose_project="candidate7",
        provider=provider,
        state=state,
        compose=compose,
        env=env,
        provider_version={
            "observed_commit": UPSTREAM_COMMIT,
            "git_tree": "a" * 40,
            "tracked_source_clean": True,
            "cached_source_clean": True,
            "untracked_files": [],
        },
    )
    runtime_env = declared["declared_configuration"]["runtime_environment"]
    assert runtime_env["DERIVER_FLUSH_ENABLED"] == "true"
    assert runtime_env["DREAM_DEDUCTION_MODEL_CONFIG__THINKING_EFFORT"] == "minimal"
    assert runtime_env["EMBEDDING_VECTOR_DIMENSIONS"] == "384"
    assert runtime_env["LLM_OPENAI_API_KEY"] == "<REDACTED>"
    assert declared["runtime_verified"] is False
    assert declared["unresolved_configuration_defaults"]
    assert remote.provider_configuration_support_ready(
        declared, provider_healthy=True
    ) is False
    manually_cleared = {**declared, "unresolved_configuration_defaults": []}
    assert remote.provider_configuration_support_ready(
        manually_cleared, provider_healthy=True
    ) is False


def _effective_settings_fixture() -> dict[str, object]:
    return {
        "LLM": {
            "OPENAI_API_KEY": "super-secret-key",
            "DEFAULT_MAX_TOKENS": 2500,
        },
        "DB": {
            "CONNECTION_URI": "postgresql://user:password@database/db",
        },
        "DERIVER": {
            "WORKERS": 1,
            "FLUSH_ENABLED": True,
            "REPRESENTATION_BATCH_WORK_UNIT_TARGET_TOKENS": 512,
        },
        "DREAM": {
            "ENABLED": True,
            "ENABLED_TYPES": ["omni"],
            "DEDUCTION_MODEL_CONFIG": {
                "model": "gpt-oss-120b",
                "transport": "openai",
                "temperature": 0,
                "thinking_effort": "minimal",
                "overrides": {"base_url": "http://host.docker.internal:18081/v1/"},
            },
        },
        "VECTOR_STORE": {"TYPE": "lancedb"},
        "AUTH": {"USE_AUTH": False, "JWT_SECRET": "must-not-leak"},
        "SENTRY": {"DSN": "https://public:private@sentry.invalid/1"},
        "CACHE": {"URL": "redis://cache-user:cache-password@redis:6379/0"},
    }


def test_effective_config_redaction_preserves_behavior_fields_and_hashes() -> None:
    remote = _remote_module()
    redacted, paths = remote.redact_secret_settings(_effective_settings_fixture())
    encoded = json.dumps(redacted, sort_keys=True)
    assert "super-secret-key" not in encoded
    assert "user:password" not in encoded
    assert "must-not-leak" not in encoded
    assert "private@sentry" not in encoded
    assert "cache-password" not in encoded
    assert redacted["LLM"]["OPENAI_API_KEY"] == "<REDACTED>"
    assert redacted["DB"]["CONNECTION_URI"] == "<REDACTED>"
    assert redacted["AUTH"]["JWT_SECRET"] == "<REDACTED>"
    assert redacted["SENTRY"]["DSN"] == "<REDACTED>"
    assert redacted["CACHE"]["URL"] == "redis://<REDACTED>@redis:6379/0"
    assert redacted["LLM"]["DEFAULT_MAX_TOKENS"] == 2500
    assert redacted["DERIVER"]["REPRESENTATION_BATCH_WORK_UNIT_TARGET_TOKENS"] == 512
    assert redacted["DREAM"]["DEDUCTION_MODEL_CONFIG"]["thinking_effort"] == "minimal"
    assert redacted["DREAM"]["DEDUCTION_MODEL_CONFIG"]["overrides"]["base_url"].endswith("/v1/")
    assert redacted["VECTOR_STORE"]["TYPE"] == "lancedb"
    assert paths == [
        "AUTH.JWT_SECRET",
        "CACHE.URL",
        "DB.CONNECTION_URI",
        "LLM.OPENAI_API_KEY",
        "SENTRY.DSN",
    ]
    first = remote.sha256_bytes(remote.canonical_json_bytes(redacted))
    second = remote.sha256_bytes(remote.canonical_json_bytes(redacted))
    assert first == second


@pytest.mark.parametrize("service", ["api", "deriver"])
def test_effective_runtime_config_is_captured_redacted_inside_each_service(
    service: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    remote = _remote_module()
    redacted, paths = remote.redact_secret_settings(_effective_settings_fixture())
    digest = remote.sha256_bytes(remote.canonical_json_bytes(redacted))
    container_payload = {
        "effective_settings": redacted,
        "redacted_paths": paths,
        "effective_settings_sha256": digest,
    }
    observed: dict[str, object] = {}

    def fake_run(command, *, cwd=None, timeout=1800):
        observed["command"] = command
        observed["cwd"] = cwd
        observed["timeout"] = timeout
        return "PHASE08B1_EFFECTIVE_CONFIG=" + json.dumps(container_payload)

    monkeypatch.setattr(remote, "run", fake_run)
    captured = remote.capture_effective_settings(
        ["docker", "compose", "-f", "compose.yml"], tmp_path, service
    )
    assert captured["service"] == service
    assert captured["status"] == "OBSERVED"
    assert captured["effective_settings_sha256"] == digest
    assert captured["redacted_paths"] == paths
    assert service in observed["command"]
    capture_code = observed["command"][-1]
    assert "from src.config import settings" in capture_code
    assert "redact(settings.model_dump" in capture_code


def test_configuration_support_requires_matching_hashed_runtime_evidence() -> None:
    remote = _remote_module()
    config = remote.initial_provider_configuration()
    config.update(
        declared_configuration={"status": "PRESERVED"},
        declared_runtime_env_sha256="a" * 64,
        transformed_compose_sha256="b" * 64,
        effective_api_configuration_sha256="c" * 64,
        effective_deriver_configuration_sha256="d" * 64,
        effective_shared_configuration_matches=True,
        unresolved_configuration_defaults=[],
        effective_configuration_status="VERIFIED",
    )
    assert remote.provider_configuration_support_ready(
        config, provider_healthy=True
    ) is True
    assert remote.provider_configuration_support_ready(
        config, provider_healthy=False
    ) is False
    mismatched = {
        **config,
        "effective_shared_configuration_matches": False,
        "effective_configuration_status": "MISMATCH",
    }
    assert remote.provider_configuration_support_ready(
        mismatched, provider_healthy=True
    ) is False
    api = {"status": "OBSERVED", "effective_settings": {"DREAM": {"ENABLED": True}}}
    deriver = {"status": "OBSERVED", "effective_settings": {"DREAM": {"ENABLED": False}}}
    assert remote.effective_shared_configuration_matches(api, deriver) is False


def test_config_evidence_binding_never_mislabels_declared_only_state(
    tmp_path: Path,
) -> None:
    remote = _remote_module()
    declared_only = remote.initial_provider_configuration()
    declared_only["declared_configuration"] = {"status": "PRESERVED"}
    config_path = tmp_path / "provider-config.json"
    config_path.write_text(json.dumps(declared_only) + "\n", encoding="utf-8")
    assert config_path.exists()
    assert declared_only["runtime_verified"] is False
    assert declared_only["effective_configuration_status"] == "NOT_OBSERVED"
    assert remote.provider_configuration_evidence_is_provider_observed(
        declared_only, CapabilityClassification.UNKNOWN
    ) is False

    runtime_verified = {
        **declared_only,
        "runtime_verified": True,
        "effective_configuration_status": "VERIFIED",
        "effective_shared_configuration_matches": True,
        "unresolved_configuration_defaults": [],
    }
    assert remote.provider_configuration_evidence_is_provider_observed(
        runtime_verified, CapabilityClassification.SUPPORTED
    ) is True
    assert remote.provider_configuration_evidence_is_provider_observed(
        declared_only, CapabilityClassification.SUPPORTED
    ) is False


def test_stage_a_failure_keeps_config_unknown_unobserved_and_pending() -> None:
    remote = _remote_module()
    contact = remote.ProviderContactState()
    config = remote.initial_provider_configuration()
    calibration = LiveCalibrationState()
    calibration.fail_operationally("EMBEDDING_COMPATIBILITY_FAILED")
    capabilities = _unknown_capabilities()
    record = acceptance_record(
        capabilities, live_calibration_complete=calibration.live_calibration_complete
    )
    assert contact.contacted is False
    assert remote.provider_configuration_evidence_is_provider_observed(
        config, CapabilityClassification.UNKNOWN
    ) is False
    assert capabilities[
        AcceptanceCapability.PROVIDER_CONFIGURATION_PINNING
    ].classification is CapabilityClassification.UNKNOWN
    assert calibration.live_calibration_complete is False
    assert record.decision is AcceptanceDecision.PENDING_LIVE_ACCEPTANCE


def test_compose_start_is_explicitly_scoped_to_required_services() -> None:
    remote = _remote_module()
    assert remote.REQUIRED_COMPOSE_SERVICES == (
        "database",
        "redis",
        "api",
        "deriver",
    )
    assert "mcp" not in remote.REQUIRED_COMPOSE_SERVICES
    source = REMOTE_SCRIPT.read_text(encoding="utf-8")
    assert '[*compose_cmd, "up", "-d", "database"]' in source
    scoped = '[*compose_cmd, "up", "-d", "redis", "api", "deriver"]'
    assert scoped in source
    assert '[*compose_cmd, "up", "-d", "mcp"]' not in source
    assert '"initial_observed_running_service_names"' in source
    assert '"final_observed_running_service_names"' in source


def _fresh_bootstrap_paths(tmp_path: Path) -> tuple[Path, Path, Path]:
    attempt = tmp_path / "runs" / "phase08b" / "attempts" / "attempt-1"
    state = attempt / "provider-state"
    provider = tmp_path / "provider"
    provider.mkdir()
    for path in (
        state / "postgres",
        state / "redis",
        state / "lancedb",
    ):
        path.mkdir(parents=True)
    (attempt / "bound-runtime-manifest.json").write_text("{}\n", encoding="utf-8")
    return provider, state, attempt


def test_pgvector_bootstrap_uses_native_script_and_verifies_384(
    tmp_path: Path,
) -> None:
    remote = _remote_module()
    provider, state, attempt = _fresh_bootstrap_paths(tmp_path)
    commands: list[list[str]] = []

    def fake_run(command, *, cwd=None, timeout=1800):
        commands.append(command)
        query = command[-1] if command and command[-2:-1] == ["-c"] else ""
        if "SUM(n)" in query:
            return "0\n"
        if "atttypmod" in query:
            return "documents|384\nmessage_embeddings|384\n"
        return ""

    evidence = remote.bootstrap_pgvector_schema(
        ["docker", "compose", "-f", "compose.yml"],
        provider,
        state,
        attempt,
        run_command=fake_run,
        sleep_command=lambda _: None,
    )
    assert evidence["status"] == "PASS"
    assert evidence["initial_state_empty"] is True
    assert evidence["database_row_count_before_configuration"] == 0
    assert evidence["verified_dimensions"] == {
        "documents": 384,
        "message_embeddings": 384,
    }
    joined = [" ".join(command) for command in commands]
    assert joined[0].endswith("up -d database")
    migration = next(i for i, command in enumerate(joined) if "alembic upgrade head" in command)
    empty_check = next(i for i, command in enumerate(joined) if "SUM(n)" in command)
    dry_run = next(i for i, command in enumerate(joined) if command.endswith("--dry-run"))
    apply = next(i for i, command in enumerate(joined) if command.endswith("--yes"))
    verify = next(i for i, command in enumerate(joined) if "atttypmod" in command)
    assert migration < empty_check < dry_run < apply < verify
    assert all(" up -d api" not in command for command in joined)
    assert all(" up -d deriver" not in command for command in joined)
    assert all("mcp" not in command for command in joined)


def test_pgvector_bootstrap_refuses_nonempty_run_state_before_docker(
    tmp_path: Path,
) -> None:
    remote = _remote_module()
    provider, state, attempt = _fresh_bootstrap_paths(tmp_path)
    (state / "postgres" / "old-evidence").write_text("occupied", encoding="utf-8")
    calls: list[list[str]] = []
    with pytest.raises(RuntimeError, match="REFUSES_NONEMPTY_STATE"):
        remote.bootstrap_pgvector_schema(
            ["docker", "compose"],
            provider,
            state,
            attempt,
            run_command=lambda command, **kwargs: calls.append(command) or "",
        )
    assert calls == []


def test_pgvector_bootstrap_wrong_result_dimension_fails_closed(
    tmp_path: Path,
) -> None:
    remote = _remote_module()
    provider, state, attempt = _fresh_bootstrap_paths(tmp_path)

    def fake_run(command, **kwargs):
        query = command[-1] if command and command[-2:-1] == ["-c"] else ""
        if "SUM(n)" in query:
            return "0\n"
        if "atttypmod" in query:
            return "documents|1536\nmessage_embeddings|1536\n"
        return ""

    with pytest.raises(RuntimeError, match="DIMENSION_VERIFICATION_FAILED"):
        remote.bootstrap_pgvector_schema(
            ["docker", "compose"],
            provider,
            state,
            attempt,
            run_command=fake_run,
            sleep_command=lambda _: None,
        )


def test_api_and_deriver_start_only_after_pgvector_bootstrap_pass() -> None:
    source = REMOTE_SCRIPT.read_text(encoding="utf-8")
    bootstrap = source.index("bootstrap_evidence = bootstrap_pgvector_schema(")
    authorize = source.index(
        'bootstrap_evidence.get("api_deriver_start_authorized") is not True'
    )
    api_start = source.index(
        '[*compose_cmd, "up", "-d", "redis", "api", "deriver"]'
    )
    assert bootstrap < authorize < api_start


def test_required_service_health_requires_api_and_every_owned_service(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    remote = _remote_module()
    observed_commands: list[list[str]] = []

    def all_running(command, *, cwd=None, timeout=1800):
        observed_commands.append(command)
        return "database\nredis\napi\nderiver\n"

    monkeypatch.setattr(remote, "run", all_running)
    healthy = remote.observe_required_provider_health(
        ["docker", "compose", "-f", "compose.yml"],
        tmp_path,
        phase="initial",
        api_health_payload={"status": "ok"},
        api_health_raw_evidence={"artifact": "raw/health.json"},
    )
    assert observed_commands[0][-4:] == ["ps", "--services", "--status", "running"]
    assert healthy["passed"] is True
    assert healthy["deriver_running"] is True
    assert healthy["database_running"] is True
    assert healthy["redis_running"] is True
    assert healthy["optional_mcp_running"] is False
    remote.require_required_provider_health(healthy)

    monkeypatch.setattr(remote, "run", lambda *args, **kwargs: "database\nredis\napi\n")
    dead_deriver = remote.observe_required_provider_health(
        ["docker", "compose", "-f", "compose.yml"],
        tmp_path,
        phase="initial",
        api_health_payload={"status": "ok"},
        api_health_raw_evidence={"artifact": "raw/health.json"},
    )
    assert dead_deriver["api_health_passed"] is True
    assert dead_deriver["deriver_running"] is False
    assert dead_deriver["passed"] is False
    with pytest.raises(RuntimeError, match="REQUIRED_SERVICE_HEALTH.*deriver"):
        remote.require_required_provider_health(dead_deriver)

    monkeypatch.setattr(
        remote, "run", lambda *args, **kwargs: "database\nredis\napi\nderiver\n"
    )
    bad_api = remote.observe_required_provider_health(
        ["docker", "compose", "-f", "compose.yml"],
        tmp_path,
        phase="initial",
        api_health_payload={"status": "starting"},
        api_health_raw_evidence={"artifact": "raw/health.json"},
    )
    assert bad_api["api_running"] is True
    assert bad_api["api_health_passed"] is False
    assert bad_api["passed"] is False


def test_dead_deriver_or_config_capture_failure_remains_operational_pending() -> None:
    remote = _remote_module()
    with pytest.raises(RuntimeError, match="EFFECTIVE_CONFIG_CAPTURE.*deriver"):
        remote.require_effective_settings_capture(
            {
                "api": {"status": "OBSERVED"},
                "deriver": {"status": "CAPTURE_FAILED"},
            }
        )
    calibration = LiveCalibrationState()
    calibration.fail_operationally("BLOCKED_EFFECTIVE_CONFIG_CAPTURE: deriver")
    record = acceptance_record(
        _unknown_capabilities(),
        live_calibration_complete=calibration.live_calibration_complete,
    )
    assert calibration.live_calibration_complete is False
    assert record.decision is AcceptanceDecision.PENDING_LIVE_ACCEPTANCE


def test_initial_and_restart_health_gate_precedes_scientific_observation() -> None:
    source = REMOTE_SCRIPT.read_text(encoding="utf-8")
    initial_health = source.index("initial_health = observe_required_provider_health")
    initial_gate = source.index("require_required_provider_health(initial_health)")
    workspace_create = source.index('name="workspace-create"')
    assert initial_health < initial_gate < workspace_create

    restart = source.index('run([*compose_cmd, "restart", "api", "deriver"]')
    restart_health = source.index("restart_health = observe_required_provider_health")
    restart_gate = source.index("require_required_provider_health(restart_health)")
    post_restart = source.index('name="post-restart-messages"')
    assert restart < restart_health < restart_gate < post_restart


def test_provider_config_artifact_is_write_once_with_final_state(tmp_path: Path) -> None:
    remote = _remote_module()
    config = remote.initial_provider_configuration()
    path = tmp_path / "provider-config.json"
    first_sha = remote.write_json_once(tmp_path, path.name, config)
    config["runtime_verified"] = True
    second_sha = remote.write_json_once(tmp_path, path.name, config)
    assert first_sha == second_sha
    assert json.loads(path.read_text(encoding="utf-8"))["runtime_verified"] is False
    source = REMOTE_SCRIPT.read_text(encoding="utf-8")
    assert 'write_json_once(attempt_root, "provider-config.json", provider_config)' in source
    assert 'write_json_exclusive(attempt_root / "provider-config.json"' not in source


@pytest.mark.parametrize(
    ("pre_ids", "post_ids", "healthy", "expected"),
    [
        ([], ["created"], True, CapabilityClassification.UNKNOWN),
        (["other"], ["created"], True, CapabilityClassification.UNKNOWN),
        (["created"], ["created"], True, CapabilityClassification.SUPPORTED),
        (["created"], [], True, CapabilityClassification.UNSUPPORTED),
        (["created"], None, True, CapabilityClassification.UNKNOWN),
        (["created"], ["created"], False, CapabilityClassification.UNKNOWN),
    ],
)
def test_restart_persistence_requires_exact_created_native_id(
    pre_ids: list[str] | None,
    post_ids: list[str] | None,
    healthy: bool,
    expected: CapabilityClassification,
) -> None:
    remote = _remote_module()
    assert remote.classify_restart_persistence(
        "created", pre_ids, post_ids, restart_healthy=healthy
    ) is expected
    assert remote.native_message_ids({"items": []}) == []
    assert remote.native_message_ids({"items": [{"id": "created"}]}) == ["created"]
    assert remote.native_message_ids({"items": [{}]}) is None


def test_restart_evidence_observes_exact_id_before_and_after_owned_restart() -> None:
    source = REMOTE_SCRIPT.read_text(encoding="utf-8")
    pre = source.index('name="pre-restart-messages"')
    restart = source.index('run([*compose_cmd, "restart", "api", "deriver"]')
    post = source.index('name="post-restart-messages"')
    assert pre < restart < post
    assert '"written_message_provider_native_id": created_id' in source
    assert '"pre_restart_exact_match": pre_restart_exact_match' in source
    assert '"post_restart_exact_match": post_restart_exact_match' in source


def _initialize_provider_git_checkout(path: Path) -> str:
    path.mkdir()
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    source = path / "src" / "provider.py"
    source.parent.mkdir()
    source.write_text("PINNED = True\n", encoding="utf-8")
    subprocess.run(["git", "add", "src/provider.py"], cwd=path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Phase08B1 Test",
            "-c",
            "user.email=phase08b1@example.invalid",
            "commit",
            "-m",
            "pinned provider",
        ],
        cwd=path,
        check=True,
        capture_output=True,
    )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_provider_source_checkout_requires_clean_tree_and_records_tree_id(
    tmp_path: Path,
) -> None:
    remote = _remote_module()
    provider = tmp_path / "provider"
    commit = _initialize_provider_git_checkout(provider)
    identity = remote.validate_provider_source_checkout(
        provider, expected_commit=commit
    )
    assert identity["observed_commit"] == commit
    assert len(identity["git_tree"]) == 40
    assert identity["tracked_source_clean"] is True
    assert identity["cached_source_clean"] is True
    assert identity["untracked_files"] == []

    (provider / "src" / "provider.py").write_text(
        "PINNED = False\n", encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match="TRACKED_SOURCE_DIRTY"):
        remote.validate_provider_source_checkout(provider, expected_commit=commit)


def test_provider_source_checkout_rejects_untracked_build_input(
    tmp_path: Path,
) -> None:
    remote = _remote_module()
    provider = tmp_path / "provider"
    commit = _initialize_provider_git_checkout(provider)
    (provider / "src" / "injected.py").write_text("UNSAFE = True\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="UNTRACKED_BUILD_INPUT.*src/injected.py"):
        remote.validate_provider_source_checkout(provider, expected_commit=commit)


def test_provider_version_support_requires_commit_tree_cleanliness_and_image() -> None:
    remote = _remote_module()
    complete = {
        "observed_commit": UPSTREAM_COMMIT,
        "git_tree": "a" * 40,
        "tracked_source_clean": True,
        "cached_source_clean": True,
        "untracked_files": [],
        "image_digests": [
            {
                "identity": "sha256:abc",
                "compose_record": {"ID": "sha256:abc", "Service": "api"},
            }
        ],
    }
    assert remote.provider_version_identity_complete(complete) is True
    for field, value in (
        ("git_tree", None),
        ("tracked_source_clean", False),
        ("untracked_files", ["src/injected.py"]),
        ("image_digests", []),
    ):
        assert remote.provider_version_identity_complete(
            {**complete, field: value}
        ) is False
    assert remote.parse_compose_image_identities(
        '{"ID":"sha256:abc","Service":"api"}\n'
        '{"Digest":"sha256:def","Service":"deriver"}\n'
    ) == [
        {
            "identity": "sha256:abc",
            "compose_record": {"ID": "sha256:abc", "Service": "api"},
        },
        {
            "identity": "sha256:def",
            "compose_record": {
                "Digest": "sha256:def",
                "Service": "deriver",
            },
        },
    ]
    with pytest.raises(RuntimeError, match="omitted ID/digest"):
        remote.parse_compose_image_identities('{"Service":"api"}')
    source = REMOTE_SCRIPT.read_text(encoding="utf-8")
    source_validation = source.index(
        "source_identity = validate_provider_source_checkout(provider)"
    )
    residue_classification = source.index(
        "preexisting_residue = preserve_and_remove_managed_runtime_residue("
    )
    runtime_generation = source.index("compose, env = write_runtime_files(")
    provider_start = source.index(
        '[*compose_cmd, "up", "-d", "redis", "api", "deriver"]'
    )
    assert (
        residue_classification
        < source_validation
        < runtime_generation
        < provider_start
    )


def test_compose_transform_fails_closed_on_pinned_shape_drift(tmp_path: Path) -> None:
    remote = _remote_module()
    pinned = (
        REPO_ROOT
        / ".local"
        / "review"
        / "honcho-upstream-v3.2.1"
        / "docker-compose.yml.example"
    ).read_text(encoding="utf-8")
    changed = pinned.replace("- redis-data:/data", "- other-volume:/data")
    with pytest.raises(RuntimeError, match="Compose shape mismatch"):
        remote.transform_pinned_compose(changed, tmp_path / "state")


def test_direct_model_preflight_sends_nonsecret_honcho_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    remote = _remote_module()
    observed: dict[str, str | None] = {}

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return b"{}"

    def fake_urlopen(request, timeout: int):
        observed["authorization"] = request.get_header("Authorization")
        observed["url"] = request.full_url
        return Response()

    monkeypatch.setattr(remote.urllib.request, "urlopen", fake_urlopen)
    assert remote._preflight_post("/v1/chat/completions", {"model": "test"}) == {}
    assert observed == {
        "authorization": "Bearer empty",
        "url": "http://127.0.0.1:18081/v1/chat/completions",
    }


def _structured_response(content: str) -> dict[str, object]:
    return {
        "choices": [
            {"message": {"role": "assistant", "content": content}}
        ]
    }


def test_structured_output_is_parsed_and_schema_validated() -> None:
    remote = _remote_module()
    expected = {"explicit": [{"content": "fictional observation"}]}
    assert remote.validate_structured_output_response(
        _structured_response(json.dumps(expected))
    ) == expected


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("ordinary prose", "not valid JSON"),
        ("{", "not valid JSON"),
        (json.dumps({"other": []}), "contain only explicit"),
        (json.dumps({"explicit": {}}), "explicit must be a list"),
        (json.dumps({"explicit": [{"content": 7}]}), "must be a string"),
    ],
)
def test_structured_output_rejects_ignored_or_invalid_schema(
    content: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _remote_module().validate_structured_output_response(
            _structured_response(content)
        )


def test_dream_tool_gate_requires_the_native_function_call() -> None:
    remote = _remote_module()
    valid = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {
                                "name": "finish_preflight",
                                "arguments": "{}",
                            },
                        }
                    ]
                }
            }
        ]
    }
    remote.validate_dream_tool_response(valid)
    invalid = json.loads(json.dumps(valid))
    invalid["choices"][0]["message"]["tool_calls"][0]["function"]["name"] = "other"
    with pytest.raises(ValueError, match="wrong native tool call"):
        remote.validate_dream_tool_response(invalid)


def test_text_preflights_match_pinned_openai_request_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    remote = _remote_module()
    requests: list[tuple[str, dict[str, object]]] = []
    dream_response = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {
                                "name": "finish_preflight",
                                "arguments": "{}",
                            },
                        }
                    ]
                }
            }
        ]
    }

    def fake_post(path: str, payload: dict[str, object]) -> dict[str, object]:
        requests.append((path, payload))
        if path == "/v1/embeddings":
            return {"data": [{"embedding": [0.0] * 384}]}
        if "tools" in payload:
            return dream_response
        return _structured_response(
            json.dumps({"explicit": [{"content": "fictional observation"}]})
        )

    monkeypatch.setattr(remote, "_preflight_post", fake_post)
    result = remote.run_model_endpoint_preflight()
    structured = requests[0][1]
    dream = requests[2][1]
    assert "temperature" not in structured
    assert structured["max_tokens"] == 2500
    assert structured["response_format"]["type"] == "json_schema"
    assert structured["response_format"]["json_schema"]["strict"] is True
    assert dream["model"] == "gpt-oss-120b"
    assert dream["temperature"] == 0
    assert dream["reasoning_effort"] == "minimal"
    assert dream["max_tokens"] == 8192
    assert dream["tool_choice"] == "required"
    assert result["deriver_temperature_omitted"] is True
    assert result["requested_reasoning_effort"] == "minimal"
    assert result["effective_reasoning_effort"] == "low"
    assert result["compatibility_resolution"] == "MINIMAL_TO_LOW"
    assert result["compatibility_reason"] == (
        "Jetstream hosted chat endpoint accepts only low, medium, or high"
    )
    assert validate_model_endpoint_compatibility(result) == []


def test_configured_dream_request_rejection_prevents_stage_b(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    remote = _remote_module()
    calls = 0

    def fake_post(path: str, payload: dict[str, object]) -> dict[str, object]:
        nonlocal calls
        calls += 1
        if calls == 1:
            return _structured_response(json.dumps({"explicit": []}))
        if calls == 2:
            return {"data": [{"embedding": [0.0] * 384}]}
        assert payload["reasoning_effort"] == "minimal"
        raise RuntimeError("configured Dream request shape rejected")

    monkeypatch.setattr(remote, "_preflight_post", fake_post)
    with pytest.raises(RuntimeError, match="configured Dream request shape rejected"):
        remote.run_model_endpoint_preflight()
    assert stage_a_allows_stage_b(
        {
            "status": "BLOCKED",
            "blockers": ["MODEL_ENDPOINT_COMPATIBILITY_FAILED"],
            "model_endpoint_compatibility": {"status": "FAIL"},
        }
    ) is False


def test_local_embedding_single_and_batch_contract_preserves_order(
    tmp_path: Path,
) -> None:
    remote = _remote_module()
    backend, _ = _fake_local_embedding_backend(remote, tmp_path)
    single = backend.embed_request(
        {
            "model": remote.EMBEDDING_MODEL,
            "input": "one",
            "encoding_format": "float",
            "dimensions": 384,
        }
    )
    assert single["object"] == "list"
    assert single["model"] == remote.EMBEDDING_MODEL
    assert single["data"][0]["index"] == 0
    assert single["data"][0]["embedding"] == [3.0] * 384
    batch = backend.embed_request(
        {"model": remote.EMBEDDING_MODEL, "input": ["a", "four"]}
    )
    assert [item["index"] for item in batch["data"]] == [0, 1]
    assert batch["data"][0]["embedding"] == [1.0] * 384
    assert batch["data"][1]["embedding"] == [4.0] * 384
    assert "usage" not in batch


@pytest.mark.parametrize(
    ("request_update", "message"),
    [
        ({"model": "wrong"}, "exact pin"),
        ({"dimensions": 1536}, "dimensions must equal 384"),
        ({"encoding_format": "base64"}, "only float"),
        ({"input": []}, "non-empty strings"),
        ({"input": ["ok", 7]}, "non-empty strings"),
        ({"input": {"ambiguous": True}}, "string or list"),
        ({"unsupported": True}, "unsupported embedding request fields"),
    ],
)
def test_local_embedding_rejects_unsupported_requests(
    tmp_path: Path, request_update: dict[str, object], message: str
) -> None:
    remote = _remote_module()
    backend, _ = _fake_local_embedding_backend(remote, tmp_path)
    request: dict[str, object] = {
        "model": remote.EMBEDDING_MODEL,
        "input": "valid",
        "encoding_format": "float",
        "dimensions": 384,
    }
    request.update(request_update)
    with pytest.raises(remote.LocalEmbeddingRequestError, match=message):
        backend.embed_request(request)


def test_local_embedding_rejects_wrong_model_output_dimension(tmp_path: Path) -> None:
    remote = _remote_module()
    backend, _ = _fake_local_embedding_backend(
        remote, tmp_path, output_dimensions=383
    )
    with pytest.raises(remote.LocalEmbeddingRequestError, match="wrong dimension"):
        backend.embed_request(
            {"model": remote.EMBEDDING_MODEL, "input": ["valid"]}
        )


def test_local_embedding_loader_is_cpu_offline_cache_only(tmp_path: Path) -> None:
    remote = _remote_module()
    backend, construction = _fake_local_embedding_backend(remote, tmp_path)
    assert os.environ["HF_HUB_OFFLINE"] == "1"
    assert os.environ["TRANSFORMERS_OFFLINE"] == "1"
    assert os.environ["HF_HOME"] == str((tmp_path / "cache").resolve())
    assert construction["factory_kwargs"] == {
        "cache_folder": str((tmp_path / "cache").resolve()),
        "device": "cpu",
        "local_files_only": True,
    }
    provenance = backend.provenance(observed_dimension=384)
    assert provenance["model_id"] == remote.EMBEDDING_MODEL
    assert provenance["sentence_transformers_version"] == "6.1.0"
    assert provenance["resolved_revision"] == "a" * 40
    assert provenance["artifact_file_count"] == 1
    assert len(provenance["artifact_fingerprint_sha256"]) == 64
    assert provenance["observed_dimension"] == 384


def test_missing_local_embedding_cache_fails_without_model_factory(
    tmp_path: Path,
) -> None:
    remote = _remote_module()
    called = False

    def forbidden_factory(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("model factory must not be reached")

    with pytest.raises(remote.LocalEmbeddingUnavailable, match="CACHE_MISSING"):
        remote.LocalSentenceTransformerEmbeddings(
            tmp_path / "missing-cache",
            model_factory=forbidden_factory,
            installed_version="6.1.0",
        )
    assert called is False


def test_existing_proxy_routes_text_hosted_and_embeddings_local(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    remote = _remote_module()
    backend, _ = _fake_local_embedding_backend(remote, tmp_path)
    upstream_requests: list[tuple[str, dict[str, object]]] = []

    class UpstreamResponse:
        status = 200
        headers = {"Content-Type": "application/json"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"choices":[],"usage":{"prompt_tokens":2,"completion_tokens":1}}'

    def fake_urlopen(request, timeout=0):
        upstream_requests.append((request.full_url, json.loads(request.data)))
        return UpstreamResponse()

    monkeypatch.setattr(remote.urllib.request, "urlopen", fake_urlopen)
    proxy = remote.ModelBudgetProxy(
        backend, server_address=("127.0.0.1", 0)
    )
    proxy.start()
    port = proxy.server.server_address[1]
    try:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request(
            "POST",
            "/v1/chat/completions",
            body=b'{"model":"gpt-oss-120b","messages":[],"reasoning_effort":"minimal"}',
            headers={"Content-Type": "application/json"},
        )
        assert connection.getresponse().status == 200
        connection.close()
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request(
            "POST",
            "/v1/embeddings",
            body=json.dumps(
                {"model": remote.EMBEDDING_MODEL, "input": ["local"]}
            ).encode(),
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        embedding_payload = json.loads(response.read())
        assert response.status == 200
        connection.close()
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request(
            "POST",
            "/v1/embeddings",
            body=json.dumps(
                {"model": remote.EMBEDDING_MODEL, "input": ["local"], "dimensions": 1536}
            ).encode(),
            headers={"Content-Type": "application/json"},
        )
        assert connection.getresponse().status == 400
        connection.close()
    finally:
        proxy.stop()
    assert upstream_requests == [
        (
            remote.MODEL_ENDPOINT + "chat/completions",
            {
                "model": "gpt-oss-120b",
                "messages": [],
                "reasoning_effort": "low",
            },
        )
    ]
    assert len(embedding_payload["data"][0]["embedding"]) == 384
    accounting = proxy.accounting()
    assert accounting["provider_internal_total_requests"] == 3
    assert accounting["maximum_requests"] == 100
    assert accounting["hosted_text_generation_call_count"] == 1
    assert accounting["local_embedding_call_count"] == 2
    assert accounting["local_embedding_success_count"] == 1
    assert accounting["local_embedding_failure_count"] == 1
    assert accounting["input_tokens"] == 2
    assert accounting["output_tokens"] == 1
    assert accounting["calls"][0]["reasoning_effort_compatibility"] == {
        "requested_reasoning_effort": "minimal",
        "effective_reasoning_effort": "low",
        "compatibility_resolution": "MINIMAL_TO_LOW",
        "compatibility_reason": (
            "Jetstream hosted chat endpoint accepts only low, medium, or high"
        ),
    }


@pytest.mark.parametrize("effort", ["low", "medium", "high"])
def test_supported_hosted_reasoning_efforts_pass_through(effort: str) -> None:
    remote = _remote_module()
    body = json.dumps({"reasoning_effort": effort, "sentinel": "unchanged"}).encode()
    normalized, audit = remote.normalize_hosted_chat_body(
        "/v1/chat/completions", body
    )
    assert json.loads(normalized) == {
        "reasoning_effort": effort,
        "sentinel": "unchanged",
    }
    assert audit == {
        "requested_reasoning_effort": effort,
        "effective_reasoning_effort": effort,
        "compatibility_resolution": "ALREADY_SUPPORTED",
        "compatibility_reason": "Requested reasoning effort is natively supported",
    }


def test_unsupported_hosted_reasoning_effort_fails_closed_without_forwarding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    remote = _remote_module()
    forwarded = False

    def forbidden_urlopen(*args, **kwargs):
        nonlocal forwarded
        forwarded = True
        raise AssertionError("unsupported reasoning effort must not reach Jetstream")

    monkeypatch.setattr(remote.urllib.request, "urlopen", forbidden_urlopen)
    status, body, _, audit = remote.ModelBudgetProxy._forward_hosted(
        "/v1/chat/completions",
        b'{"reasoning_effort":"extreme"}',
        {"Content-Type": "application/json"},
    )
    assert status == 400
    assert json.loads(body)["error"]["error_type"] == (
        "HOSTED_REASONING_EFFORT_REJECTED"
    )
    assert audit == {
        "requested_reasoning_effort": "extreme",
        "effective_reasoning_effort": None,
        "compatibility_resolution": "REJECTED_UNSUPPORTED",
        "compatibility_reason": (
            "Jetstream hosted chat endpoint accepts only low, medium, or high"
        ),
    }
    assert forwarded is False


def test_reasoning_effort_normalization_does_not_touch_embedding_body() -> None:
    remote = _remote_module()
    body = b'{"model":"embedding-model","reasoning_effort":"minimal"}'
    normalized, audit = remote.normalize_hosted_chat_body("/v1/embeddings", body)
    assert normalized is body
    assert audit is None


def test_model_proxy_origin_policy_is_local_and_docker_bridge_only() -> None:
    allowed = _remote_module().model_proxy_client_allowed
    assert allowed("127.0.0.1") is True
    assert allowed("::1") is True
    assert allowed("172.17.0.2") is True
    assert allowed("172.31.255.254") is True
    assert allowed("10.0.0.2") is False
    assert allowed("192.168.1.2") is False
    assert allowed("8.8.8.8") is False
    assert allowed("not-an-address") is False


def test_provider_contact_state_cannot_hide_started_or_polled_provider() -> None:
    remote = _remote_module()
    started = remote.ProviderContactState()
    assert started.contacted is False
    started.mark_stack_start_attempted()
    assert started.contacted is True
    started.mark_stack_started()
    assert started.contacted is True
    assert started.provider_health_passed is False

    polled = remote.ProviderContactState()
    polled.mark_health_attempted()
    assert polled.contacted is True
    assert polled.provider_contact_attempted is True
    assert polled.provider_health_passed is False
    polled.mark_api_health_passed()
    assert polled.provider_api_health_passed is True
    assert polled.provider_health_passed is False
    polled.mark_required_services_passed()
    assert polled.provider_health_passed is True


def test_current_baseline_authority_is_active_and_authoritative() -> None:
    ledger = current_baseline_authority_ledger(
        attempt_id="20261006T000000Z-deadbeef0001",
        namespace="phase08b1-fictional-session",
        content="Fictional current proposition.",
    )
    entry = ledger.entries[0]
    assert entry.lifecycle_state.value == "active"
    assert entry.authoritative is True
    assert entry.authority_reason == "current experiment-defined authority"
    source = REMOTE_SCRIPT.read_text(encoding="utf-8")
    assert '"authoritative": False' not in source


def test_scenario_classification_reuses_native_contradiction_contract() -> None:
    native = {
        capability: CapabilityClassification.UNKNOWN
        for capability in AcceptanceCapability
    }
    native[AcceptanceCapability.CREATE_WRITE] = CapabilityClassification.SUPPORTED
    native[AcceptanceCapability.RETRIEVAL] = CapabilityClassification.SUPPORTED
    without_scenario_evidence = derive_scenario_classifications(
        native, provider_observed_scenarios=set()
    )
    assert without_scenario_evidence["S0"] is CapabilityClassification.UNKNOWN

    with_s0_evidence = derive_scenario_classifications(
        native, provider_observed_scenarios={"S0"}
    )
    assert with_s0_evidence["S0"] is CapabilityClassification.SUPPORTED

    native[AcceptanceCapability.HARD_DELETE] = CapabilityClassification.UNSUPPORTED
    native[AcceptanceCapability.REVOKE_INVALIDATE] = CapabilityClassification.UNSUPPORTED
    contradicted = derive_scenario_classifications(
        native, provider_observed_scenarios={"S0"}
    )
    for scenario in ("S2", "S3", "S4", "S5"):
        assert contradicted[scenario] is CapabilityClassification.UNSUPPORTED


def test_scenario_evidence_requires_direct_s0_and_binds_contradictions() -> None:
    native = {
        capability: CapabilityClassification.UNKNOWN
        for capability in AcceptanceCapability
    }
    native[AcceptanceCapability.CREATE_WRITE] = CapabilityClassification.SUPPORTED
    native[AcceptanceCapability.RETRIEVAL] = CapabilityClassification.SUPPORTED
    scenarios = derive_scenario_classifications(
        native, provider_observed_scenarios={"S0"}
    )
    with pytest.raises(ValueError, match="S0 SUPPORTED requires direct"):
        build_scenario_evidence_matrix(scenarios, native, {}, {})

    matrix = build_scenario_evidence_matrix(
        scenarios,
        native,
        {},
        {
            "S0": {
                "provider_observed": True,
                "artifact": "scenarios/S0/evidence.json",
                "sha256": "a" * 64,
            }
        },
    )
    assert matrix["S0"]["direct_scenario_executed"] is True
    assert matrix["S0"]["evidence_artifact"] == "scenarios/S0/evidence.json"
    assert matrix["S1"]["classification"] == "UNKNOWN"
    assert matrix["S1"]["evidence_class"] is None
    assert matrix["S1"]["evidence_artifact"] is None

    native[AcceptanceCapability.HARD_DELETE] = CapabilityClassification.UNSUPPORTED
    contradicted = derive_scenario_classifications(
        native, provider_observed_scenarios={"S0"}
    )
    hard_delete_binding = {
        "provider_observed": True,
        "artifact": "provider-surface-inventory.json",
        "sha256": "b" * 64,
    }
    matrix = build_scenario_evidence_matrix(
        contradicted,
        native,
        {AcceptanceCapability.HARD_DELETE: hard_delete_binding},
        {
            "S0": {
                "provider_observed": True,
                "artifact": "scenarios/S0/evidence.json",
                "sha256": "a" * 64,
            }
        },
    )
    for scenario in ("S2", "S3", "S4"):
        entry = matrix[scenario]
        assert entry["classification"] == "UNSUPPORTED"
        assert entry["direct_scenario_executed"] is False
        assert entry["evidence_mode"] == "DERIVED_NATIVE_CAPABILITY_CONTRADICTION"
        assert entry["contradicting_capabilities"][0] == {
            "capability": "hard_delete",
            "evidence_artifact": "provider-surface-inventory.json",
            "evidence_sha256": "b" * 64,
        }
    source = REMOTE_SCRIPT.read_text(encoding="utf-8")
    completion_block = source[
        source.index("if terminal_capabilities != set(AcceptanceCapability):") :
        source.index("record = acceptance_record(")
    ]
    assert completion_block.index("materialize_scenario_evidence()") < (
        completion_block.index("calibration.complete(")
    )
    assert '"scenarios/S0/evidence.json"' in source


def test_patch_transport_is_file_based_and_candidate_reproduces_local_bytes() -> None:
    source = CONTROLLER_SCRIPT.read_text(encoding="utf-8")
    controller = _controller_module()
    assert '"scp"' in source
    assert "implementation.patch" in source
    assert controller.PATCH_PATH.name == (
        "phase08b1-honcho-live-acceptance-candidate10.patch"
    )
    assert "phase08b1-honcho-live-acceptance-candidate9r2.patch" not in source
    assert "phase08b1-honcho-live-acceptance-candidate9.patch" not in source
    assert "phase08b1-honcho-live-acceptance-candidate9r.patch" not in source
    assert "base64.b64encode(patch" not in source
    validation = controller.validate_patch_for_transfer()
    assert validation["git_apply_check_exit_status"] == 0
    assert validation["git_apply_check_stderr"] == ""
    assert validation["git_apply_check_nowarn_exit_status"] == 0
    assert validation["git_apply_check_nowarn_stderr"] == ""
    assert set(validation["byte_identical_files"]) == set(
        controller.IMPLEMENTATION_FILES
    )
    assert set(validation["patch_changed_files"]) == set(
        controller.IMPLEMENTATION_FILES
    )
    assert "tests/unit/test_project_handoff.py" in validation["byte_identical_files"]


def test_remote_sync_uses_attempt_detached_worktree_without_canonical_switch() -> None:
    controller = _controller_module()
    attempt_id = "20261006T120000Z-abcdef123456"
    sync = controller._sync_command(attempt_id)
    prepare = controller._prepare_remote_command(
        attempt_id,
        "/media/volume/test",
        "a" * 64,
        123,
        {"scripts/jetstream/phase08b1_honcho_remote.py": "b" * 64},
    )
    assert controller.REMOTE_EXECUTION_BRANCH == (
        "phase-08b1-honcho-live-acceptance"
    )
    assert "phase-08b-honcho-acceptance" not in sync
    assert "git worktree add --detach" in sync
    assert controller.BASE_COMMIT in sync
    assert "git switch" not in sync
    assert "git checkout" not in sync
    assert "git diff --quiet" not in sync
    assert "git diff --cached --quiet" not in sync
    paths = controller._remote_attempt_paths(attempt_id)
    assert f"cd {paths['worktree']}" in prepare
    assert f"cd {controller.REMOTE_REPO}" not in prepare
    assert paths["patch"] in prepare
    assert "git apply --check" in prepare
    scp = controller._scp_command(
        "user@host",
        Path("candidate9r2.patch"),
        attempt_id,
        lambda address, command: [
            "ssh",
            "-o",
            "BatchMode=yes",
            address,
            command,
        ],
    )
    assert scp[-1] == f"user@host:{paths['patch']}"
    assert f"{controller.REMOTE_REPO}/.local" not in scp[-1]


def test_remote_cleanup_preserves_canonical_identity_without_broad_git_repair() -> None:
    controller = _controller_module()
    cleanup = controller._cleanup_command("20261006T120000Z-abcdef123456")
    assert "canonical-state-before.sha256" in cleanup
    assert "canonical_identity" in cleanup
    assert "CANONICAL_STATE_CHANGED" in cleanup
    assert "git worktree remove" in cleanup
    assert "apply --reverse" in cleanup
    for forbidden in (
        "git reset",
        "git clean",
        "git restore",
        "git switch",
        "git checkout",
        "--force",
    ):
        assert forbidden not in cleanup


def _controller_runner_fixture(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    execution_error: Exception | None = None,
    cleanup_status: str = "PASS",
):
    controller = _controller_module()
    attempt_id = "20261006T120000Z-abcdef123456"
    patch = tmp_path / "candidate9r2.patch"
    patch.write_bytes(b"test-patch\n")
    monkeypatch.setenv(controller.AUTH_ENV, "YES")
    monkeypatch.setattr(controller, "PATCH_PATH", patch)
    monkeypatch.setattr(
        controller,
        "validate_patch_for_transfer",
        lambda: {"sha256": hashlib.sha256(patch.read_bytes()).hexdigest()},
    )
    monkeypatch.setattr(controller, "_source_manifest", lambda: {})
    monkeypatch.setattr(
        controller,
        "_download",
        lambda **kwargs: {
            "completion_artifacts": ["runtime-file-lifecycle.json"],
            "copied_artifacts": [
                "completion.json",
                "runtime-file-lifecycle.json",
            ],
            "optional_preexisting_residue": "NOT_PRESENT",
        },
    )
    commands: list[list[str]] = []
    result_payload = {
        "attempt_id": attempt_id,
        "base_commit": controller.BASE_COMMIT,
        "remote_evidence_root": "/evidence",
        "completion_manifest_sha256": "c" * 64,
        "status": "PASS",
        "cleanup_blockers": [],
        "provider_acceptance_decision": "GO",
    }

    def ssh_builder(address: str, command: str) -> list[str]:
        return ["ssh", "-o", "BatchMode=yes", address, command]

    def runner(command, **kwargs):
        command = list(command)
        commands.append(command)
        if command[0] == "scp":
            return subprocess.CompletedProcess(command, 0, stdout="")
        remote_command = command[-1]
        if controller.WORKTREE_CLEANUP_PREFIX in remote_command:
            cleanup_output = (
                f"{controller.WORKTREE_CLEANUP_PREFIX}STATUS={cleanup_status}\n"
                f"{controller.WORKTREE_CLEANUP_PREFIX}CANONICAL_STATE_PRESERVED="
                f"{'true' if cleanup_status == 'PASS' else 'false'}\n"
                f"{controller.WORKTREE_CLEANUP_PREFIX}BLOCKERS="
                f"{'ATTEMPT_WORKTREE_REMOVE_FAILED' if cleanup_status == 'BLOCKED' else ''}\n"
            )
            return subprocess.CompletedProcess(command, 0, stdout=cleanup_output)
        if controller.AUTH_ENV in remote_command:
            if execution_error is not None:
                raise execution_error
            encoded = base64.b64encode(
                json.dumps(result_payload).encode("utf-8")
            ).decode("ascii")
            return subprocess.CompletedProcess(
                command, 0, stdout=controller.RESULT_PREFIX + encoded + "\n"
            )
        return subprocess.CompletedProcess(command, 0, stdout="")

    return controller, attempt_id, ssh_builder, runner, commands


def test_attempt_worktree_cleanup_runs_after_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    controller, attempt_id, ssh_builder, runner, commands = (
        _controller_runner_fixture(monkeypatch, tmp_path)
    )
    result = controller.run_remote_validation(
        address="user@host",
        facts={"resolved_volume_mount": "/volume", "repo_head": "dirty-head"},
        expected_commit=controller.BASE_COMMIT,
        attempt_id=attempt_id,
        ssh_builder=ssh_builder,
        runner=runner,
    )
    assert result["controller_worktree_cleanup"] == {
        "status": "PASS",
        "canonical_state_preserved": True,
        "blockers": [],
    }
    assert "git worktree remove" in commands[-1][-1]
    assert result["initial_remote_head"] == "dirty-head"


def test_attempt_worktree_cleanup_runs_after_provider_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    controller, attempt_id, ssh_builder, runner, commands = (
        _controller_runner_fixture(
            monkeypatch,
            tmp_path,
            execution_error=RuntimeError("simulated Stage-A/provider failure"),
        )
    )
    with pytest.raises(RuntimeError, match="Stage-A/provider failure"):
        controller.run_remote_validation(
            address="user@host",
            facts={"resolved_volume_mount": "/volume"},
            expected_commit=controller.BASE_COMMIT,
            attempt_id=attempt_id,
            ssh_builder=ssh_builder,
            runner=runner,
        )
    assert "git worktree remove" in commands[-1][-1]


def test_attempt_worktree_cleanup_failure_is_accounted_separately(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    controller, attempt_id, ssh_builder, runner, _ = _controller_runner_fixture(
        monkeypatch, tmp_path, cleanup_status="BLOCKED"
    )
    result = controller.run_remote_validation(
        address="user@host",
        facts={"resolved_volume_mount": "/volume"},
        expected_commit=controller.BASE_COMMIT,
        attempt_id=attempt_id,
        ssh_builder=ssh_builder,
        runner=runner,
    )
    assert result["status"] == "BLOCKED"
    assert result["provider_acceptance_decision"] == "GO"
    assert result["cleanup_blockers"] == ["ATTEMPT_WORKTREE_REMOVE_FAILED"]
    assert result["controller_worktree_cleanup"]["status"] == "BLOCKED"


def _copyback_fixture(*, include_optional: bool = False):
    lifecycle = {
        "schema_version": "phase08b1-runtime-file-lifecycle-v1",
        "preexisting_residue": {"status": "NO_RESIDUE"},
    }
    remote_files = {
        "run-ledger.json": b'{"status":"PASS"}\n',
    }
    if include_optional:
        optional = b'{"status":"RECOGNIZED_MANAGED_RESIDUE"}\n'
        remote_files["preexisting-runtime-residue.json"] = optional
        lifecycle["preexisting_residue"] = {
            "status": "RECOGNIZED_MANAGED_RESIDUE",
            "evidence_artifact": "preexisting-runtime-residue.json",
            "evidence_sha256": hashlib.sha256(optional).hexdigest(),
        }
    lifecycle_bytes = json.dumps(lifecycle, sort_keys=True).encode("utf-8") + b"\n"
    remote_files["runtime-file-lifecycle.json"] = lifecycle_bytes
    completion = {
        "artifacts": {
            name: {
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
            for name, data in remote_files.items()
            if name != "preexisting-runtime-residue.json"
        }
    }
    completion_bytes = json.dumps(completion, sort_keys=True).encode("utf-8") + b"\n"
    remote_files["completion.json"] = completion_bytes
    return remote_files, hashlib.sha256(completion_bytes).hexdigest()


def _run_copyback(controller, remote_files, completion_sha256, local_root):
    requested: list[str] = []

    def ssh_builder(address: str, command: str) -> list[str]:
        return ["ssh", address, command]

    def runner(command, **kwargs):
        remote_path = command[-1].split()[-1].strip("'")
        name = remote_path.removeprefix("/remote/")
        requested.append(name)
        data = remote_files[name]
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=base64.b64encode(data).decode("ascii"),
        )

    result = controller._download(
        address="user@host",
        remote_root="/remote",
        local_root=local_root,
        ssh_builder=ssh_builder,
        runner=runner,
        completion_sha256=completion_sha256,
    )
    return result, requested


def test_completion_driven_copyback_verifies_and_downloads_every_artifact(
    tmp_path: Path,
) -> None:
    controller = _controller_module()
    remote_files, completion_sha = _copyback_fixture()
    result, requested = _run_copyback(
        controller, remote_files, completion_sha, tmp_path / "evidence"
    )
    assert requested[0] == "completion.json"
    assert set(requested[1:]) == {
        "run-ledger.json",
        "runtime-file-lifecycle.json",
    }
    assert set(result["completion_artifacts"]) == set(requested[1:])
    assert (tmp_path / "evidence" / "runtime-file-lifecycle.json").is_file()


@pytest.mark.parametrize("corruption", ["sha256", "bytes"])
def test_completion_driven_copyback_fails_closed_on_identity_mismatch(
    tmp_path: Path, corruption: str
) -> None:
    controller = _controller_module()
    remote_files, completion_sha = _copyback_fixture()
    completion = json.loads(remote_files["completion.json"])
    identity = completion["artifacts"]["run-ledger.json"]
    if corruption == "sha256":
        identity["sha256"] = "0" * 64
    else:
        identity["bytes"] += 1
    completion_bytes = json.dumps(completion, sort_keys=True).encode("utf-8") + b"\n"
    remote_files["completion.json"] = completion_bytes
    completion_sha = hashlib.sha256(completion_bytes).hexdigest()
    with pytest.raises(RuntimeError, match="mismatch"):
        _run_copyback(
            controller,
            remote_files,
            completion_sha,
            tmp_path / f"evidence-{corruption}",
        )


def test_optional_preexisting_residue_is_copied_and_sha_verified(
    tmp_path: Path,
) -> None:
    controller = _controller_module()
    remote_files, completion_sha = _copyback_fixture(include_optional=True)
    result, requested = _run_copyback(
        controller, remote_files, completion_sha, tmp_path / "evidence"
    )
    assert result["optional_preexisting_residue"] == "COPIED_AND_VERIFIED"
    assert requested[-1] == "preexisting-runtime-residue.json"
    assert (tmp_path / "evidence" / "preexisting-runtime-residue.json").is_file()


def test_exact_candidate8_patch_applies_to_governed_cb44_base(tmp_path: Path) -> None:
    patch = (
        REPO_ROOT
        / ".local"
        / "review"
        / "phase08b1-honcho-live-acceptance-candidate8.patch"
    )
    body = patch.read_bytes()
    import hashlib

    assert len(body) == 272733
    assert hashlib.sha256(body).hexdigest() == (
        "f4a86a991bdf86872d7dd4b44ceb9def7852834785aa06a625941bd560350592"
    )
    environment = os.environ.copy()
    environment["GIT_INDEX_FILE"] = str(tmp_path / "candidate8.index")
    read_tree = subprocess.run(
        ["git", "read-tree", "cb44f639642442b8277bc3cb2f6afb4b96d81307"],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert read_tree.returncode == 0, read_tree.stderr
    apply_check = subprocess.run(
        ["git", "apply", "--cached", "--check", str(patch)],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert apply_check.returncode == 0, apply_check.stderr
