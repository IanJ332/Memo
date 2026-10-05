"""Deterministic validation for the non-final Phase 08A design draft."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from memlife.models.mediator import EvidenceClass
from memlife.models.provider_acceptance import (
    AcceptanceCapability,
    CapabilityAssessment,
    CapabilityClassification,
    GRAPHITI_REQUIRED_CAPABILITIES,
    HONCHO_REQUIRED_CAPABILITIES,
    RETAINDB_REQUIRED_CAPABILITIES,
    ScenarioCapabilityAssessment,
)

FREEZE_V1_SHA256 = "0e02a86deb1864ecfc0627d4f313642454101b73fa02acdbe6bbc34479fd349b"
PHASE07_BASE_COMMIT = "481f9d698e7e48fe9d3d84868a303ec10aa676ea"
EXISTING_PROVIDERS = {"mem0", "hindsight", "openviking"}
EXISTING_PROVIDER_ORDER = ("mem0", "hindsight", "openviking")
SCENARIOS = {f"S{index}" for index in range(6)}
EXPECTED_SCENARIO_REUSE = {
    "S0": "BASELINE",
    "S1": "SUPERSESSION_OR_UPDATE",
    "S2": "HARD_DELETE",
    "S3": "HARD_DELETE_RESTART_OR_RECONSTRUCTION",
    "S4": "HARD_DELETE_NATIVE_REDERIVATION",
    "S5": "NATIVE_REVOKE_INVALIDATE",
}
EXPECTED_RQ3_ACTIVATION_GATE = (
    "stale_or_revoked_proposition_is_PROVIDER_OBSERVED",
    "authority_is_independently_known",
    "proposition_identity_is_exactly_verified",
    "stale_lineage_alone_is_insufficient",
    "exposure_reproduces_under_declared_repetition_policy",
    "exact_delivered_pre_llm_context_bytes_are_frozen",
    "exact_model_boundary_serialization_sha256_is_captured",
    "D0_D1_D2_semantics_are_already_frozen",
    "provider_and_model_configuration_is_unchanged_after_observation",
    "separate_user_authorization_for_downstream_model_calls",
)
EXPECTED_RQ4_OUTPUTS = ("ALLOW", "DENY", "QUARANTINE")
EXPECTED_RQ4_INVARIANTS = (
    "stale_only_lineage_and_stale_proposition_to_DENY",
    "mixed_lineage_and_current_proposition_to_ALLOW",
    "mixed_lineage_and_stale_proposition_to_DENY",
    "unresolved_claimed_source_to_QUARANTINE",
    "revoked_direct_source_to_DENY",
    "identical_input_bundle_hash_to_identical_deterministic_decision",
)
EXPECTED_IDENTITIES = (
    "exact_provider_record_bytes",
    "deterministic_canonical_proposition_body",
    "logical_fact_and_version",
)
EXPECTED_PROHIBITED_AUTHORIZATION_PRIMITIVES = (
    "LLM semantic equivalence",
    "embedding similarity",
)
EXPECTED_FINALIZATION_PREREQUISITES = (
    "separate scientific approval",
    "completed live acceptance evidence for Honcho and selected Provider 5",
    "provider version and configuration pins",
    "completed capability matrix",
    "environment manifest contract approval",
)
EXPECTED_COMPLETED_MATRIX_DEFINITION = (
    "All provider/scenario classifications used by the final schedule are "
    "evidence-bound and internally consistent with native capability evidence."
)
EXPECTED_EXECUTION_AUTHORIZATION_KEYS = {
    "hosted_model_calls",
    "jetstream",
    "provider_calibration",
    "provider_experiment",
    "rq3",
}
EXPECTED_SCHEDULE_KEYS = {
    "provider",
    "scenario",
    "repetition",
    "run_id",
    "synthetic_substitute",
}
EXPECTED_PROVIDER5_TRANSITIONS = (
    "RETAINDB_PENDING__GRAPHITI_NOT_ELIGIBLE__ACTIVE_NONE",
    "RETAINDB_GO__GRAPHITI_NOT_ELIGIBLE__ACTIVE_RETAINDB",
    "RETAINDB_NO_GO__GRAPHITI_PENDING__ACTIVE_NONE",
    "RETAINDB_NO_GO__GRAPHITI_GO__ACTIVE_GRAPHITI",
    "RETAINDB_NO_GO__GRAPHITI_NO_GO__ACTIVE_NONE",
)
ASSESSMENT_FIELDS = {
    "classification",
    "evidence_class",
    "evidence_artifact",
    "evidence_sha256",
    "notes",
}
SCENARIO_NATIVE_REQUIREMENTS = {
    "S0": frozenset(
        {AcceptanceCapability.CREATE_WRITE, AcceptanceCapability.RETRIEVAL}
    ),
    "S1": frozenset(
        {AcceptanceCapability.UPDATE_SUPERSEDE, AcceptanceCapability.RETRIEVAL}
    ),
    "S2": frozenset(
        {AcceptanceCapability.HARD_DELETE, AcceptanceCapability.RETRIEVAL}
    ),
    "S3": frozenset(
        {
            AcceptanceCapability.HARD_DELETE,
            AcceptanceCapability.RESTART_RECONSTRUCTION,
            AcceptanceCapability.RESTART_PERSISTENCE,
            AcceptanceCapability.RETRIEVAL,
        }
    ),
    "S4": frozenset(
        {
            AcceptanceCapability.HARD_DELETE,
            AcceptanceCapability.NATIVE_REDERIVATION_CONSOLIDATION,
            AcceptanceCapability.RETRIEVAL,
        }
    ),
    "S5": frozenset(
        {AcceptanceCapability.REVOKE_INVALIDATE, AcceptanceCapability.RETRIEVAL}
    ),
}
REQUIRED_RUN_ARTIFACTS = {
    "environment-manifest.json",
    "provider-config.json",
    "authority-ledger.jsonl",
    "provider-raw-response.json",
    "retrieval-candidates.json",
    "lineage.json",
    "mediator-input.json",
    "mediator-decision.json",
    "latency.jsonl",
    "run-ledger.json",
    "completion.json",
}


def _assessment(
    value: object,
    *,
    context: str,
    scenario_cell: bool,
) -> tuple[CapabilityAssessment | None, list[str]]:
    model = ScenarioCapabilityAssessment if scenario_cell else CapabilityAssessment
    if not isinstance(value, dict):
        return None, [f"{context} must be an evidence-bound assessment object"]
    if set(value) != ASSESSMENT_FIELDS:
        return None, [f"{context} fields must match the exact evidence contract"]
    try:
        return model.model_validate(value), []
    except ValidationError as exc:
        return None, [f"{context} evidence is invalid: {exc.errors()[0]['msg']}"]


def validate_evidence_bound_matrices(
    scenario_matrix: dict[str, Any],
    native_matrix: dict[str, Any],
    *,
    require_phase08a_unknown: bool = False,
) -> list[str]:
    """Validate scenario evidence and one-way native-capability implications."""

    errors: list[str] = []
    expected_providers = {"honcho", "retaindb-server", "graphiti"}
    if not isinstance(scenario_matrix, dict) or set(scenario_matrix) != expected_providers:
        errors.append("scenario capability matrix provider set is incomplete")
        return errors
    if not isinstance(native_matrix, dict) or set(native_matrix) != expected_providers:
        errors.append("native capability matrix provider set is incomplete")
        return errors

    for provider in sorted(expected_providers):
        scenario_cells = scenario_matrix.get(provider)
        native_cells = native_matrix.get(provider)
        if not isinstance(scenario_cells, dict) or set(scenario_cells) != SCENARIOS:
            errors.append(f"{provider} scenario matrix must cover S0-S5")
            continue
        expected_capabilities = {capability.value for capability in AcceptanceCapability}
        if not isinstance(native_cells, dict) or set(native_cells) != expected_capabilities:
            errors.append(f"{provider} native capability matrix is incomplete")
            continue

        parsed_native: dict[AcceptanceCapability, CapabilityAssessment] = {}
        for capability in AcceptanceCapability:
            assessment, assessment_errors = _assessment(
                native_cells[capability.value],
                context=f"{provider}/{capability.value}",
                scenario_cell=False,
            )
            errors.extend(assessment_errors)
            if assessment is not None:
                parsed_native[capability] = assessment
                if require_phase08a_unknown and (
                    assessment.classification is not CapabilityClassification.UNKNOWN
                    or assessment.evidence_class is not None
                    or assessment.evidence_artifact is not None
                    or assessment.evidence_sha256 is not None
                    or assessment.notes is not None
                ):
                    errors.append(
                        f"{provider}/{capability.value} must remain UNKNOWN without "
                        "evidence in Phase 08A"
                    )

        for scenario in sorted(SCENARIOS):
            assessment, assessment_errors = _assessment(
                scenario_cells[scenario],
                context=f"{provider}/{scenario}",
                scenario_cell=True,
            )
            errors.extend(assessment_errors)
            if assessment is None:
                continue
            if require_phase08a_unknown and (
                assessment.classification is not CapabilityClassification.UNKNOWN
                or assessment.evidence_class is not None
                or assessment.evidence_artifact is not None
                or assessment.evidence_sha256 is not None
                or assessment.notes is not None
            ):
                errors.append(
                    f"{provider}/{scenario} must remain UNKNOWN without evidence "
                    "in Phase 08A"
                )
            if assessment.classification is CapabilityClassification.SUPPORTED:
                for capability in SCENARIO_NATIVE_REQUIREMENTS[scenario]:
                    native = parsed_native.get(capability)
                    if (
                        native is None
                        or native.classification is not CapabilityClassification.SUPPORTED
                    ):
                        errors.append(
                            f"{provider}/{scenario} SUPPORTED contradicts native "
                            f"{capability.value} capability evidence"
                        )
    return errors


def validate_provider5_state(provider5: dict[str, Any]) -> list[str]:
    """Validate current or future mutually exclusive Provider-5 transitions."""

    errors: list[str] = []
    primary = provider5.get("primary", {})
    fallback = provider5.get("fallback", {})
    retaindb_decision = primary.get("acceptance_decision")
    graphiti_decision = fallback.get("acceptance_decision")
    active = provider5.get("active_provider")
    states = {
        ("PENDING_LIVE_ACCEPTANCE", "NOT_ELIGIBLE", None),
        ("GO", "NOT_ELIGIBLE", "retaindb-server"),
        ("NO_GO", "PENDING_LIVE_ACCEPTANCE", None),
        ("NO_GO", "GO", "graphiti"),
        ("NO_GO", "NO_GO", None),
    }
    if (retaindb_decision, graphiti_decision, active) not in states:
        errors.append(
            "Provider-5 state must follow RetainDB GO or RetainDB NO_GO then "
            "independent Graphiti acceptance"
        )
    if provider5.get("mutually_exclusive") is not True:
        errors.append("Provider 5 primary and fallback must be mutually exclusive")
    return errors


def validate_extension_schedule(
    run_contract: dict[str, Any],
    provider_extension: dict[str, Any],
    capability_matrix: dict[str, Any],
    native_capability_matrix: dict[str, Any],
) -> list[str]:
    """Validate a future schedule while allowing Phase 08A's empty schedule."""

    errors: list[str] = []
    scheduled = run_contract.get("scheduled_runs", [])
    if not isinstance(scheduled, list):
        return ["scheduled_runs must be a list"]
    matrix_errors = validate_evidence_bound_matrices(
        capability_matrix,
        native_capability_matrix,
    )
    errors.extend(matrix_errors)
    if not isinstance(capability_matrix, dict) or not isinstance(
        native_capability_matrix, dict
    ):
        return errors
    if len(scheduled) > 36:
        errors.append("extension schedule cannot exceed 36 runs")

    provider4 = provider_extension.get("provider_4", {})
    provider5 = provider_extension.get("provider_5", {})
    provider5_state_errors = validate_provider5_state(provider5)
    if scheduled:
        errors.extend(provider5_state_errors)
    selected: set[str] = set()
    if provider4.get("acceptance_decision") == "GO":
        selected.add("honcho")
    active_provider5 = provider5.get("active_provider")
    if not provider5_state_errors and active_provider5 in {
        "retaindb-server",
        "graphiti",
    }:
        selected.add(active_provider5)

    seen_run_ids: set[str] = set()
    seen_coordinates: set[tuple[str, str, int]] = set()
    repetitions_by_cell: dict[tuple[str, str], set[int]] = {}
    scheduled_providers: set[str] = set()
    for item in scheduled:
        if not isinstance(item, dict):
            errors.append("scheduled run entries must be objects")
            continue
        if set(item) != EXPECTED_SCHEDULE_KEYS:
            errors.append("scheduled run fields must match the exact contract")
        provider = item.get("provider")
        scenario = item.get("scenario")
        repetition = item.get("repetition")
        run_id = item.get("run_id")
        if provider in EXISTING_PROVIDERS:
            errors.append("old provider run scheduled for rerun")
        if provider not in {"honcho", "retaindb-server", "graphiti"}:
            errors.append("scheduled provider is not a known extension candidate")
        else:
            scheduled_providers.add(provider)
            if provider not in selected:
                errors.append("scheduled provider is not an accepted selected provider")
        if scenario not in SCENARIOS:
            errors.append("scheduled scenario must be S0 through S5")
        if type(repetition) is not int or repetition not in {1, 2, 3}:
            errors.append("scheduled repetition must be 1, 2, or 3")
        if item.get("synthetic_substitute") is not False:
            errors.append("scheduled run must prohibit synthetic substitutes")
        if isinstance(run_id, str) and run_id.startswith("freeze-v1__"):
            errors.append("old provider run scheduled for rerun")
        if (
            isinstance(provider, str)
            and isinstance(scenario, str)
            and type(repetition) is int
        ):
            expected_run_id = f"freeze-v2__{provider}__{scenario}__r{repetition}"
            if run_id != expected_run_id:
                errors.append("scheduled run_id does not match its coordinates")
            coordinates = (provider, scenario, repetition)
            if coordinates in seen_coordinates:
                errors.append("scheduled provider/scenario/repetition must be unique")
            else:
                seen_coordinates.add(coordinates)
            repetitions_by_cell.setdefault((provider, scenario), set()).add(repetition)
            cell_value = capability_matrix.get(provider, {}).get(scenario)
            cell, _ = _assessment(
                cell_value,
                context=f"{provider}/{scenario}",
                scenario_cell=True,
            )
            if (
                cell is None
                or cell.classification is not CapabilityClassification.SUPPORTED
            ):
                errors.append(
                    "only evidence-backed SUPPORTED provider/scenario cells may "
                    "be scheduled"
                )
        if not isinstance(run_id, str) or not run_id:
            errors.append("scheduled run_id is required")
        elif run_id in seen_run_ids:
            errors.append("scheduled run IDs must be unique")
        else:
            seen_run_ids.add(run_id)

    if {"retaindb-server", "graphiti"}.issubset(scheduled_providers):
        errors.append("RetainDB and Graphiti cannot both be scheduled")
    for cell, repetitions in repetitions_by_cell.items():
        if repetitions != {1, 2, 3}:
            errors.append(
                f"scheduled cell {cell[0]}/{cell[1]} must contain repetitions 1, 2, 3"
            )
    return errors


def _closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_phase08a_draft(path: Path) -> dict[str, Any]:
    """Load one strict UTF-8 JSON object and reject duplicate keys."""

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Phase 08A draft must be UTF-8") from exc
    if text.startswith("\ufeff"):
        raise ValueError("Phase 08A draft must not contain a UTF-8 BOM")
    try:
        payload = json.loads(text, object_pairs_hook=_closed_object)
    except json.JSONDecodeError as exc:
        raise ValueError("Phase 08A draft is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("Phase 08A draft must contain a JSON object")
    return payload


def validate_phase08a_draft(payload: dict[str, Any]) -> list[str]:
    """Return every contract violation without mutating draft data."""

    errors: list[str] = []
    if payload.get("draft_schema_version") != "2.0-draft.1":
        errors.append("draft schema version mismatch")
    if payload.get("draft_status") != "NON_FINAL_DESIGN_ONLY":
        errors.append("draft must be explicitly non-final")
    if payload.get("artifact_kind") != "EXPERIMENT_FREEZE_DESIGN_DRAFT":
        errors.append("artifact kind must identify a design draft")
    if payload.get("is_final_freeze") is not False:
        errors.append("is_final_freeze must be false")
    change_control = payload.get("change_control", {})
    if tuple(change_control.get("finalization_requires", [])) != (
        EXPECTED_FINALIZATION_PREREQUISITES
    ):
        errors.append("Freeze-v2 finalization prerequisites mismatch")
    if change_control.get("immutable_after_finalization") is not True:
        errors.append("a finalized Freeze v2 must be immutable")
    if change_control.get("semantic_changes_require_new_draft_revision") is not True:
        errors.append("semantic changes must require a new draft revision")
    if (
        change_control.get("completed_capability_matrix_definition")
        != EXPECTED_COMPLETED_MATRIX_DEFINITION
    ):
        errors.append("completed capability matrix evidence definition mismatch")

    prior = payload.get("prior_evidence", {})
    if prior.get("freeze_sha256") != FREEZE_V1_SHA256:
        errors.append("Freeze v1 reference SHA-256 mismatch")
    if prior.get("published_base_commit") != PHASE07_BASE_COMMIT:
        errors.append("Phase 07 published base commit mismatch")
    if prior.get("immutable") is not True:
        errors.append("Freeze v1 must be immutable prior evidence")
    if prior.get("provider_run_count") != 42:
        errors.append("Freeze v1 historical run count must remain 42")
    if tuple(prior.get("providers", [])) != EXISTING_PROVIDER_ORDER:
        errors.append("Freeze v1 historical provider set mismatch")
    if prior.get("rerun_existing_provider_runs") is not False:
        errors.append("existing Freeze v1 runs must not be rerun")

    extension = payload.get("provider_extension", {})
    if tuple(extension.get("existing_providers", [])) != EXISTING_PROVIDER_ORDER:
        errors.append("existing provider set mismatch")
    provider4 = extension.get("provider_4", {})
    if provider4.get("id") != "honcho":
        errors.append("Provider 4 must be Honcho")
    if provider4.get("status") != "PROPOSED_NOT_LIVE_CALIBRATED":
        errors.append("Honcho must remain proposed and not live-calibrated")
    if provider4.get("acceptance_decision") != "PENDING_LIVE_ACCEPTANCE":
        errors.append("Honcho acceptance must remain pending in Phase 08A")
    provider5 = extension.get("provider_5", {})
    primary = provider5.get("primary", {})
    fallback = provider5.get("fallback", {})
    if primary.get("id") != "retaindb-server":
        errors.append("Provider 5 primary must be RetainDB Server")
    if primary.get("status") != "PENDING_LIVE_ACCEPTANCE":
        errors.append("RetainDB must remain pending live acceptance")
    if primary.get("acceptance_decision") != "PENDING_LIVE_ACCEPTANCE":
        errors.append("RetainDB decision must remain pending in Phase 08A")
    if fallback.get("id") != "graphiti" or fallback.get("status") != "FALLBACK_ONLY":
        errors.append("Graphiti must remain fallback only")
    if fallback.get("acceptance_decision") != "NOT_ELIGIBLE":
        errors.append("Graphiti cannot be eligible before a RetainDB NO_GO")
    active_provider = provider5.get("active_provider")
    if active_provider is not None:
        errors.append("draft cannot activate a Provider 5 choice")
    errors.extend(validate_provider5_state(provider5))
    if tuple(provider5.get("valid_state_transitions", [])) != (
        EXPECTED_PROVIDER5_TRANSITIONS
    ):
        errors.append("Provider-5 state transitions mismatch")

    acceptance = payload.get("provider_acceptance_contract", {})
    if tuple(acceptance.get("capabilities", [])) != tuple(
        capability.value for capability in AcceptanceCapability
    ):
        errors.append("provider acceptance capabilities are incomplete")
    if tuple(acceptance.get("classification_enum", [])) != tuple(
        item.value for item in CapabilityClassification
    ):
        errors.append("provider acceptance classification enum mismatch")
    if acceptance.get("documentation_claims_are_evidence") is not False:
        errors.append("documentation prose must not establish capability support")
    if acceptance.get("live_values") != "MUST_BE_POPULATED_FROM_OBSERVED_EVIDENCE":
        errors.append("live capability values must come from observed evidence")
    expected_entry_requirements = {
        "graphiti": sorted(
            capability.value for capability in GRAPHITI_REQUIRED_CAPABILITIES
        ),
        "honcho": sorted(capability.value for capability in HONCHO_REQUIRED_CAPABILITIES),
        "retaindb-server": sorted(
            capability.value for capability in RETAINDB_REQUIRED_CAPABILITIES
        ),
    }
    if acceptance.get("required_entry_capabilities") != expected_entry_requirements:
        errors.append("predeclared provider entry requirements mismatch")

    matrix = payload.get("provider_capability_matrix_placeholder", {})
    native_matrix = payload.get("provider_native_capability_matrix_placeholder", {})
    errors.extend(
        validate_evidence_bound_matrices(
            matrix,
            native_matrix,
            require_phase08a_unknown=True,
        )
    )

    retaindb = payload.get("retaindb_acceptance_gate", {})
    if retaindb.get("acceptance_result") != "PENDING_LIVE_ACCEPTANCE":
        errors.append("RetainDB acceptance must remain pending")
    if retaindb.get("fallback_on_no_go") != "graphiti":
        errors.append("RetainDB NO_GO must make Graphiti the fallback candidate")
    retaindb_requirements = retaindb.get("go_requires_all", [])
    expected_retaindb = {
        capability.value for capability in RETAINDB_REQUIRED_CAPABILITIES
    }
    if set(retaindb_requirements) != expected_retaindb or len(
        retaindb_requirements
    ) != len(expected_retaindb):
        errors.append("RetainDB go gate requirements are incomplete")
    if retaindb.get("fallback_requires_independent_acceptance") is not True:
        errors.append("Graphiti fallback requires independent live acceptance")

    honcho = payload.get("honcho_acceptance_gate", {})
    if honcho.get("acceptance_result") != "PENDING_LIVE_ACCEPTANCE":
        errors.append("Honcho acceptance must remain pending")
    honcho_requirements = honcho.get("go_requires_all", [])
    expected_honcho = {
        capability.value for capability in HONCHO_REQUIRED_CAPABILITIES
    }
    if set(honcho_requirements) != expected_honcho or len(
        honcho_requirements
    ) != len(expected_honcho):
        errors.append("Honcho go gate requirements are incomplete")
    if honcho.get("scenario_specific_unsupported_operations_shrink_matrix") is not True:
        errors.append("Honcho unsupported operations must shrink the capability matrix")

    graphiti = payload.get("graphiti_acceptance_gate", {})
    if graphiti.get("acceptance_result") != "NOT_ELIGIBLE":
        errors.append("Graphiti must remain ineligible pending RetainDB NO_GO")
    if graphiti.get("eligibility_condition") != "RETAINDB_NO_GO":
        errors.append("Graphiti eligibility must require RetainDB NO_GO")
    graphiti_requirements = graphiti.get("go_requires_all", [])
    expected_graphiti = {
        capability.value for capability in GRAPHITI_REQUIRED_CAPABILITIES
    }
    if set(graphiti_requirements) != expected_graphiti or len(
        graphiti_requirements
    ) != len(expected_graphiti):
        errors.append("Graphiti go gate requirements are incomplete")

    scenarios = payload.get("scenario_reuse", {})
    if scenarios != EXPECTED_SCENARIO_REUSE:
        errors.append("scenario reuse must preserve exact S0-S5 semantics")

    run = payload.get("run_contract", {})
    if run.get("new_provider_repetitions_per_natively_supported_cell") != 3:
        errors.append("new provider repetitions must equal 3")
    if run.get("maximum_new_runs_if_both_new_providers_support_all_scenarios") != 36:
        errors.append("maximum new run count must equal 36")
    if run.get("scope") != "NEW_PROVIDERS_ONLY":
        errors.append("extension run scope must be new providers only")
    if run.get("unsupported_cell_outcome") != "UNSUPPORTED":
        errors.append("unsupported cells must remain UNSUPPORTED")
    if run.get("no_synthetic_substitute_for_unsupported") is not True:
        errors.append("unsupported operations cannot use synthetic substitutes")
    errors.extend(validate_extension_schedule(run, extension, matrix, native_matrix))

    rq3 = payload.get("rq3", {})
    if rq3.get("enabled") is not False:
        errors.append("RQ3 must default to disabled")
    if rq3.get("downstream_model_execution_authorized") is not False:
        errors.append("downstream model execution must be unauthorized")
    if rq3.get("synthetic_challenges_can_activate_empirical_rq3") is not False:
        errors.append("synthetic challenges cannot activate empirical RQ3")
    if tuple(rq3.get("activation_gate", [])) != EXPECTED_RQ3_ACTIVATION_GATE:
        errors.append("RQ3 activation gate must exactly match the canonical ten gates")

    rq4 = payload.get("rq4", {})
    if rq4.get("design_only") is not True:
        errors.append("RQ4 must remain design-only in Phase 08A")
    if rq4.get("full_d2_algorithm_frozen") is not False:
        errors.append("the full D2 algorithm must not be frozen in Phase 08A")
    if tuple(rq4.get("outputs", [])) != EXPECTED_RQ4_OUTPUTS:
        errors.append("RQ4 outputs must be exactly ALLOW, DENY, QUARANTINE")
    if (
        rq4.get("position")
        != "AFTER_PROVIDER_RETRIEVAL_BEFORE_CONTEXT_SERIALIZATION_AND_MODEL_BOUNDARY"
    ):
        errors.append("RQ4 mediator position mismatch")
    if rq4.get("role") != "AUTHORITY_FIREWALL_NOT_RETRIEVER":
        errors.append("RQ4 mediator role mismatch")
    if tuple(rq4.get("invariants_for_future_policy", [])) != EXPECTED_RQ4_INVARIANTS:
        errors.append("RQ4 future-policy invariants mismatch")

    evidence_classes = payload.get("evidence_classes", {})
    if set(evidence_classes) != {item.value for item in EvidenceClass}:
        errors.append("evidence classes are incomplete")
    synthetic = payload.get("synthetic_evidence_policy", {})
    if synthetic.get("counts_as_empirical_provider_failure") is not False:
        errors.append("synthetic evidence cannot count as a provider failure")
    if synthetic.get("may_activate_rq3") is not False:
        errors.append("synthetic evidence cannot activate RQ3")

    identity = payload.get("identity_model", {})
    if identity.get("must_remain_distinct") is not True:
        errors.append("record, proposition, and logical identities must stay distinct")
    if tuple(identity.get("identities", [])) != EXPECTED_IDENTITIES:
        errors.append("identity model is incomplete")
    if tuple(identity.get("authorization_primitives_prohibited", [])) != (
        EXPECTED_PROHIBITED_AUTHORIZATION_PRIMITIVES
    ):
        errors.append("identity authorization primitive prohibitions mismatch")
    if (
        identity.get("canonical_proposition_identity_condition")
        != "Populated only by deterministic fixture-defined canonicalization."
    ):
        errors.append("canonical proposition identity condition mismatch")
    if identity.get("indeterminate_identity_outcome") != "QUARANTINE":
        errors.append("indeterminate identity must support QUARANTINE")

    artifacts = payload.get("run_artifact_contract", {})
    required_artifacts = set(artifacts.get("required", []))
    if required_artifacts != REQUIRED_RUN_ARTIFACTS:
        errors.append("required run artifact contract mismatch")
    if "model-boundary.json" in required_artifacts:
        errors.append("model-boundary artifact cannot be unconditionally required")
    condition = artifacts.get("conditionally_required", {}).get("model-boundary.json")
    if condition != "ONLY_WHEN_DOWNSTREAM_MODEL_CALL_SEPARATELY_AUTHORIZED":
        errors.append("model-boundary artifact authorization condition mismatch")
    if artifacts.get("separate_raw_and_canonical_identity") is not True:
        errors.append("raw and canonical identities must remain separate")

    pins = payload.get("provider_pinning", {})
    if not all(
        pins.get(key) is True
        for key in (
            "environment_manifest_required",
            "provider_configuration_pin_required",
            "provider_version_or_commit_pin_required",
        )
    ):
        errors.append("provider version/config/environment pinning is required")

    authorization = payload.get("execution_authorization", {})
    if set(authorization) != EXPECTED_EXECUTION_AUTHORIZATION_KEYS:
        errors.append("execution authorization keys must match the exact contract")
    if set(authorization.values()) != {False}:
        errors.append("Phase 08A cannot authorize execution")
    return errors
