"""Deterministic validation for the Phase 08B-0 Honcho preflight."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from memlife.models.provider_acceptance import (
    AcceptanceCapability,
    CapabilityClassification,
    HONCHO_REQUIRED_CAPABILITIES,
)
from memlife.runner.phase08a import SCENARIO_NATIVE_REQUIREMENTS

PHASE08A_COMMIT = "a17bc7cb05558012992c19bb264fc7a6e18ac06b"
UNKNOWN = CapabilityClassification.UNKNOWN.value
EXPECTED_ARTIFACTS = {
    "environment-manifest.json",
    "provider-config.json",
    "provider-version.json",
    "acceptance-capabilities.json",
    "scenario-capabilities.json",
    "authority-ledger.jsonl",
    "provider-raw-response.json",
    "retrieval-candidates.json",
    "lineage.json",
    "quiescence.json",
    "latency.jsonl",
    "run-ledger.json",
    "completion.json",
    "provider-acceptance-record.json",
}
EXPECTED_RAW_PIPELINE = (
    "NATIVE_RAW_RESPONSE",
    "IMMUTABLE_RAW_ARTIFACT_AND_SHA256",
    "NORMALIZED_ADAPTER_REPRESENTATION",
    "EVIDENCE_BOUND_CAPABILITY_ASSESSMENT",
)
EXPECTED_QUIESCENCE_CRITERIA = {
    "PROVIDER_JOB_COMPLETED",
    "STABLE_RETRIEVAL_ACROSS_BOUNDED_CHECKS",
    "EMPTY_PENDING_QUEUE",
    "EXPLICIT_PROVIDER_COMPLETION_SIGNAL",
}
EXPECTED_FAILURE_POLICY = {
    "installation_failure": "BLOCKED",
    "provider_health_check_failure": "BLOCKED",
    "missing_native_id": "EXACT_PROVIDER_NATIVE_IDS_CANNOT_BE_SUPPORTED",
    "missing_raw_response_capture": "EXACT_RAW_RESPONSE_CAPTURE_CANNOT_BE_SUPPORTED",
    "unverifiable_provider_version": (
        "PROVIDER_VERSION_COMMIT_PINNING_CANNOT_BE_SUPPORTED"
    ),
    "ambiguous_ordering": "DETERMINISTIC_OR_RECORDED_ORDERING_CANNOT_BE_SUPPORTED",
    "no_auditable_provenance_edge": (
        "PROVENANCE_RELATIONSHIP_EDGES_CANNOT_BE_SUPPORTED"
    ),
    "no_deterministic_async_completion_proof": (
        "QUIESCENCE_ASYNC_COMPLETION_PROOF_CANNOT_BE_SUPPORTED"
    ),
    "missing_or_inconclusive_evidence": (
        "UNKNOWN_UNLESS_AN_OPERATIONAL_BLOCKER_IS_AUDITED"
    ),
    "documentation_only_claim": "UNKNOWN",
}
EXPECTED_PROHIBITED_JUDGES = {
    "LLM",
    "EMBEDDING",
    "SEMANTIC_SIMILARITY",
    "FUZZY_EQUIVALENCE",
}
EXPECTED_EXECUTION_CONTROLS = {
    "honcho_live_execution": False,
    "honcho_provider_contact": False,
    "jetstream_used": False,
    "jetstream_state": "SHELVED",
    "rq3_activated": False,
    "rq3_calls": 0,
    "downstream_model_execution": False,
    "downstream_model_calls": 0,
    "provider_internal_model_execution": False,
    "provider_internal_model_calls": 0,
    "freeze_v2_finalization": False,
}
EXPECTED_LIVE_MANIFEST = {
    "phase": "08B-1",
    "provider": "honcho",
    "status": "PREDECLARED_NOT_AUTHORIZED",
    "execution_environment": "JETSTREAM2",
    "phase08a_required_base_commit": PHASE08A_COMMIT,
    "required_base_commit": "PHASE08B0_COMMITTED_HEAD",
    "required_base_commit_resolution": (
        "Resolve to the reviewed Phase08B-0 commit before separate live authorization"
    ),
    "probe_plan": "experiments/acceptance/phase08b0-honcho-probe-plan.json",
    "jetstream_initial_state": "SHELVED",
    "jetstream_final_state": "SHELVED",
    "downstream_model_execution": False,
    "downstream_model_calls": 0,
    "rq3_activated": False,
    "rq3_calls": 0,
    "provider_internal_model_execution": False,
    "provider_internal_model_execution_status": "NOT_CURRENTLY_AUTHORIZED",
    "provider_internal_model_authorization_requirement": (
        "REQUIRES_SEPARATE_PHASE08B1_AUTHORIZATION_IF_REQUIRED_BY_PINNED_"
        "HONCHO_CONFIGURATION"
    ),
    "provider_internal_model_calls": None,
    "provider_internal_model_configuration_pinning_required": True,
    "provider_internal_model_call_accounting_required": True,
    "provider_internal_model_role": (
        "PROVIDER_INTERNAL_BEHAVIOR_NOT_AUTHORITY_SECURITY_JUDGE"
    ),
    "freeze_v2_finalization": False,
    "live_execution_authorized": False,
}
EXPECTED_PROBE_FIELDS = {
    "capability",
    "required_for_honcho_entry",
    "future_probe_name",
    "expected_artifacts",
    "required_evidence_class",
    "supported_if",
    "unsupported_if",
    "blocked_if",
    "unknown_if",
    "current_outcome",
    "current_evidence_artifact",
    "current_evidence_sha256",
}
EXPECTED_SCENARIO_FIELDS = {
    "scenario",
    "future_probe_name",
    "required_native_capabilities",
    "required_evidence_class",
    "expected_artifacts",
    "supported_if",
    "unsupported_if",
    "blocked_if",
    "unknown_if",
    "current_outcome",
    "current_evidence_artifact",
    "current_evidence_sha256",
}


def _closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def load_json_object(path: Path) -> dict[str, Any]:
    """Load strict UTF-8 JSON with duplicate-key rejection."""

    text = path.read_text(encoding="utf-8")
    if text.startswith("\ufeff"):
        raise ValueError(f"{path} must not contain a UTF-8 BOM")
    payload = json.loads(text, object_pairs_hook=_closed_object)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _is_nonempty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_unknown(item: dict[str, Any], context: str) -> list[str]:
    errors: list[str] = []
    if item.get("current_outcome") != UNKNOWN:
        errors.append(f"{context} Phase 08B-0 outcome must remain UNKNOWN")
    if item.get("current_evidence_artifact") is not None:
        errors.append(f"{context} must not pre-populate an evidence artifact")
    if item.get("current_evidence_sha256") is not None:
        errors.append(f"{context} must not pre-populate an evidence SHA-256")
    return errors


def validate_probe_plan(payload: dict[str, Any]) -> list[str]:
    """Validate complete, evidence-neutral capability and scenario plans."""

    errors: list[str] = []
    if payload.get("schema_version") != "phase08b0-honcho-probe-plan-v1":
        errors.append("probe-plan schema version mismatch")
    if payload.get("phase") != "08B-0":
        errors.append("probe plan phase must be 08B-0")
    if payload.get("provider") != "honcho":
        errors.append("probe plan provider must be honcho")
    if payload.get("purpose") != "FUTURE_LIVE_ACCEPTANCE_PREFLIGHT_ONLY":
        errors.append("probe plan purpose must remain preflight-only")
    if payload.get("provider_contacted") is not False:
        errors.append("Phase 08B-0 cannot contact Honcho")
    if payload.get("provider_observed_evidence_created") is not False:
        errors.append("Phase 08B-0 cannot create provider-observed evidence")

    probes = payload.get("capability_probes")
    if not isinstance(probes, list):
        return errors + ["capability_probes must be a list"]
    expected_capabilities = {item.value for item in AcceptanceCapability}
    seen: set[str] = set()
    for index, item in enumerate(probes):
        context = f"capability_probes[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{context} must be an object")
            continue
        if set(item) != EXPECTED_PROBE_FIELDS:
            errors.append(f"{context} fields must match the exact contract")
        capability = item.get("capability")
        if capability not in expected_capabilities:
            errors.append(f"{context} capability is unknown")
            continue
        if capability in seen:
            errors.append(f"duplicate capability probe: {capability}")
        seen.add(capability)
        expected_required = AcceptanceCapability(capability) in HONCHO_REQUIRED_CAPABILITIES
        if item.get("required_for_honcho_entry") is not expected_required:
            errors.append(f"{capability} required-entry flag mismatch")
        if not _is_nonempty_text(item.get("future_probe_name")):
            errors.append(f"{capability} requires an exact future probe name")
        artifacts = item.get("expected_artifacts")
        if not isinstance(artifacts, list) or not artifacts or not all(
            _is_nonempty_text(value) for value in artifacts
        ):
            errors.append(f"{capability} expected artifacts must be explicit")
        if item.get("required_evidence_class") != "PROVIDER_OBSERVED":
            errors.append(f"{capability} support requires PROVIDER_OBSERVED evidence")
        for rule in ("supported_if", "unsupported_if", "blocked_if", "unknown_if"):
            if not _is_nonempty_text(item.get(rule)):
                errors.append(f"{capability} {rule} must be explicit")
        errors.extend(_validate_unknown(item, capability))
    if seen != expected_capabilities:
        errors.append("probe plan must enumerate every AcceptanceCapability exactly once")

    scenarios = payload.get("scenario_probes")
    if not isinstance(scenarios, list):
        errors.append("scenario_probes must be a list")
    else:
        seen_scenarios: set[str] = set()
        for index, item in enumerate(scenarios):
            context = f"scenario_probes[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{context} must be an object")
                continue
            if set(item) != EXPECTED_SCENARIO_FIELDS:
                errors.append(f"{context} fields must match the exact contract")
            scenario = item.get("scenario")
            if scenario not in SCENARIO_NATIVE_REQUIREMENTS:
                errors.append(f"{context} scenario must be S0 through S5")
                continue
            if scenario in seen_scenarios:
                errors.append(f"duplicate scenario probe: {scenario}")
            seen_scenarios.add(scenario)
            expected = sorted(
                capability.value
                for capability in SCENARIO_NATIVE_REQUIREMENTS[scenario]
            )
            if item.get("required_native_capabilities") != expected:
                errors.append(f"{scenario} native contradiction rules changed")
            if item.get("required_evidence_class") != "PROVIDER_OBSERVED":
                errors.append(f"{scenario} support requires its own provider evidence")
            if not _is_nonempty_text(item.get("future_probe_name")):
                errors.append(f"{scenario} requires an exact future probe name")
            artifacts = item.get("expected_artifacts")
            if not isinstance(artifacts, list) or not artifacts:
                errors.append(f"{scenario} expected artifacts must be explicit")
            for rule in ("supported_if", "unsupported_if", "blocked_if", "unknown_if"):
                if not _is_nonempty_text(item.get(rule)):
                    errors.append(f"{scenario} {rule} must be explicit")
            errors.extend(_validate_unknown(item, scenario))
        if seen_scenarios != set(SCENARIO_NATIVE_REQUIREMENTS):
            errors.append("scenario plan must enumerate S0-S5 exactly once")

    artifact_contract = payload.get("artifact_contract", {})
    if set(artifact_contract.get("required", [])) != EXPECTED_ARTIFACTS:
        errors.append("future acceptance artifact contract is incomplete")
    if "model-boundary.json" in set(artifact_contract.get("required", [])):
        errors.append("model-boundary.json cannot be unconditionally required")
    if artifact_contract.get("conditional", {}).get("model-boundary.json") != (
        "ONLY_IF_SEPARATELY_AUTHORIZED_DOWNSTREAM_MODEL_EXECUTION"
    ):
        errors.append("model-boundary.json must remain conditional and unauthorized")
    if artifact_contract.get("attempt_root") != (
        "artifacts/phase08b/attempts/{attempt_id}"
    ):
        errors.append("future attempt root must be attempt-scoped")
    if artifact_contract.get("exclusive_creation") is not True:
        errors.append("future attempt artifacts must use exclusive creation")

    raw = payload.get("raw_evidence_contract", {})
    if tuple(raw.get("pipeline", [])) != EXPECTED_RAW_PIPELINE:
        errors.append("raw evidence must be captured before normalization")
    if raw.get("provider_native_id_field") != "provider_native_id":
        errors.append("exact provider-native ID field is missing")
    if raw.get("canonical_proposition_id_field") != "canonical_proposition_id":
        errors.append("canonical proposition identity field is missing")
    if raw.get("logical_fact_id_field") != "logical_fact_id":
        errors.append("logical fact identity field is missing")
    if raw.get("identity_layers_must_remain_distinct") is not True:
        errors.append("identity layers must remain distinct")

    quiescence = payload.get("quiescence_contract", {})
    if set(quiescence.get("observable_success_criteria", [])) != (
        EXPECTED_QUIESCENCE_CRITERIA
    ):
        errors.append("quiescence observable criteria mismatch")
    if quiescence.get("bounded_checks_required") is not True:
        errors.append("quiescence checks must be bounded")
    if quiescence.get("sleep_only_success_allowed") is not False:
        errors.append("arbitrary sleep cannot establish quiescence")
    if quiescence.get("no_conclusion_outcomes") != [
        "UNKNOWN",
        "UNSUPPORTED",
        "BLOCKED",
    ]:
        errors.append("inconclusive quiescence classifications mismatch")

    if payload.get("failure_policy") != EXPECTED_FAILURE_POLICY:
        errors.append("future failure policy mismatch")
    if set(payload.get("semantic_judges_prohibited", [])) != (
        EXPECTED_PROHIBITED_JUDGES
    ):
        errors.append("semantic judge prohibitions mismatch")

    controls = payload.get("execution_controls")
    if not isinstance(controls, dict):
        errors.append("execution_controls must be an object")
    else:
        if set(controls) != set(EXPECTED_EXECUTION_CONTROLS):
            errors.append("execution_controls fields must match the exact contract")
        for key, value in EXPECTED_EXECUTION_CONTROLS.items():
            if controls.get(key) != value:
                errors.append(f"execution control {key} mismatch")
    return errors


def validate_live_manifest(payload: dict[str, Any]) -> list[str]:
    """Validate the future, non-executable Phase 08B-1 manifest."""

    errors: list[str] = []
    if set(payload) != set(EXPECTED_LIVE_MANIFEST):
        errors.append("future live manifest fields must match the exact contract")
    for key, value in EXPECTED_LIVE_MANIFEST.items():
        if payload.get(key) != value:
            errors.append(f"future live manifest {key} mismatch")
    forbidden_fragments = ("token", "password", "secret", "ssh_key", "address")
    for key in payload:
        if any(fragment in key.casefold() for fragment in forbidden_fragments):
            errors.append(f"future live manifest contains forbidden secret/address field: {key}")
    return errors
