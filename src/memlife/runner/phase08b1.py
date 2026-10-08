"""Deterministic evidence assembly for Phase 08B-1 Honcho acceptance."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Mapping, Sequence
from typing import Any

from memlife.models.authority import (
    AuthorityLedger,
    AuthorityLedgerEntry,
    content_sha256,
)
from memlife.models.lifecycle import LifecycleState
from memlife.models.mediator import EvidenceClass
from memlife.models.provider_acceptance import (
    AcceptanceCapability,
    AcceptanceDecision,
    CapabilityAssessment,
    CapabilityClassification,
    ProviderAcceptanceRecord,
    honcho_acceptance_decision,
)
from memlife.runner.phase08a import SCENARIO_NATIVE_REQUIREMENTS

BASE_COMMIT = "cb44f639642442b8277bc3cb2f6afb4b96d81307"
UPSTREAM_VERSION = "3.2.1"
UPSTREAM_TAG = "v3.2.1"
UPSTREAM_COMMIT = "79cb31645f4efdef626d1bd9316a648adb5da89b"
STATIC_AUDIT_PATH = (
    Path(__file__).resolve().parents[3]
    / "experiments"
    / "acceptance"
    / "phase08b1-honcho-v3.2.1-static-audit.json"
)
TEXT_GENERATION_MODEL = "gpt-oss-120b"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-MiniLM-L3-v2"
SENTENCE_TRANSFORMERS_VERSION = "6.1.0"
UPSTREAM_DEFAULT_EMBEDDING_VECTOR_DIMENSIONS = 1536
ACCEPTANCE_EMBEDDING_VECTOR_DIMENSIONS = 384
CURRENT_EMBEDDING_ASSESSMENT = "LOCAL_CACHE_ONLY_EMBEDDING_PREFLIGHT_REQUIRED"
CURRENT_PROVENANCE_ASSESSMENT = (
    "AUTHORIZED_NATIVE_DREAM_LINEAGE_PROBE_PENDING_LIVE_OBSERVATION"
)
ACCEPTANCE_DERIVER_FLUSH_ENABLED = True
ACCEPTANCE_DREAM_ENABLED = True
ACCEPTANCE_DREAM_ENABLED_TYPES = ("omni",)
REQUESTED_REASONING_EFFORT = "minimal"
EFFECTIVE_REASONING_EFFORT = "low"
REASONING_EFFORT_COMPATIBILITY_RESOLUTION = "MINIMAL_TO_LOW"
REASONING_EFFORT_COMPATIBILITY_REASON = (
    "Jetstream hosted chat endpoint accepts only low, medium, or high"
)
SUPPORTED_HOSTED_REASONING_EFFORTS = frozenset({"low", "medium", "high"})
ACCEPTANCE_DREAM_MODEL_CONFIG = {
    "transport": "openai",
    "model": "gpt-oss-120b",
    "base_url": "http://host.docker.internal:18081/v1/",
    "temperature": 0,
    "thinking_effort": REQUESTED_REASONING_EFFORT,
}
DREAM_OPERATION_BUDGET = 1
PROVIDER_INTERNAL_MODEL_REQUEST_BUDGET = 100
PROVENANCE_PROBE_PURPOSE = AcceptanceCapability.PROVENANCE_RELATIONSHIP_EDGES.value
DERIVED_CONCLUSION_LEVELS = frozenset({"deductive", "inductive", "contradiction"})
QUEUE_STATUS_FIELDS = (
    "total_work_units",
    "completed_work_units",
    "in_progress_work_units",
    "pending_work_units",
)
QUIESCENCE_MAX_CHECKS = 60
QUIESCENCE_POLL_SECONDS = 5
QUIESCENCE_MAX_WINDOW_SECONDS = QUIESCENCE_MAX_CHECKS * QUIESCENCE_POLL_SECONDS
REQUIRED_AUDIT_ENDPOINTS = frozenset(
    {
        "health",
        "workspace_create",
        "peer_create",
        "session_create_with_peer_membership",
        "message_write",
        "message_list",
        "workspace_message_search",
        "message_delete",
        "queue_status",
        "conclusions_list",
        "conclusion_get",
        "schedule_dream",
    }
)
REQUIRED_ARTIFACTS = (
    "bound-runtime-manifest.json",
    "environment-manifest.json",
    "runtime-file-lifecycle.json",
    "stage-a-preflight.json",
    "provider-config.json",
    "effective-config/api.json",
    "effective-config/deriver.json",
    "provider-version.json",
    "provider-stack-health.json",
    "acceptance-capabilities.json",
    "scenario-capabilities.json",
    "authority-ledger.jsonl",
    "provider-raw-response.json",
    "provider-surface-inventory.json",
    "provider-evidence-index.json",
    "retrieval-candidates.json",
    "lineage.json",
    "quiescence.json",
    "provider-internal-model-accounting.json",
    "latency.jsonl",
    "run-ledger.json",
    "provider-acceptance-record.json",
    "scenarios/S0/evidence.json",
)

CAPABILITY_PROBE_NAMES = {
    AcceptanceCapability.CREATE_WRITE: "honcho_capability_create_write_v1",
    AcceptanceCapability.UPDATE_SUPERSEDE: "honcho_capability_update_supersede_v1",
    AcceptanceCapability.HARD_DELETE: "honcho_capability_hard_delete_v1",
    AcceptanceCapability.RESTART_RECONSTRUCTION: (
        "honcho_capability_restart_reconstruction_v1"
    ),
    AcceptanceCapability.NATIVE_REDERIVATION_CONSOLIDATION: (
        "honcho_capability_native_rederivation_consolidation_v1"
    ),
    AcceptanceCapability.REVOKE_INVALIDATE: "honcho_capability_revoke_invalidate_v1",
    AcceptanceCapability.RAW_INSPECTION: "honcho_capability_raw_inspection_v1",
    AcceptanceCapability.RETRIEVAL: "honcho_capability_retrieval_v1",
    AcceptanceCapability.EXACT_PROVIDER_NATIVE_IDS: (
        "honcho_capability_exact_provider_native_ids_v1"
    ),
    AcceptanceCapability.SOURCE_VERSION_TRANSITIONS: (
        "honcho_capability_source_version_transitions_v1"
    ),
    AcceptanceCapability.TEMPORAL_VALIDITY: "honcho_capability_temporal_validity_v1",
    AcceptanceCapability.PROVENANCE_RELATIONSHIP_EDGES: (
        "honcho_capability_provenance_relationship_edges_v1"
    ),
    AcceptanceCapability.RESTART_PERSISTENCE: (
        "honcho_capability_restart_persistence_v1"
    ),
    AcceptanceCapability.QUIESCENCE_ASYNC_COMPLETION_PROOF: (
        "honcho_capability_quiescence_async_completion_proof_v1"
    ),
    AcceptanceCapability.DETERMINISTIC_OR_RECORDED_ORDERING: (
        "honcho_capability_deterministic_or_recorded_ordering_v1"
    ),
    AcceptanceCapability.EXACT_RAW_RESPONSE_CAPTURE: (
        "honcho_capability_exact_raw_response_capture_v1"
    ),
    AcceptanceCapability.PROVIDER_CONFIGURATION_PINNING: (
        "honcho_capability_provider_configuration_pinning_v1"
    ),
    AcceptanceCapability.PROVIDER_VERSION_COMMIT_PINNING: (
        "honcho_capability_provider_version_commit_pinning_v1"
    ),
}

CAPABILITY_EVIDENCE_ARTIFACTS = {
    AcceptanceCapability.CREATE_WRITE: frozenset(
        {"probes/create-write/evidence.json"}
    ),
    AcceptanceCapability.UPDATE_SUPERSEDE: frozenset(
        {"provider-surface-inventory.json"}
    ),
    AcceptanceCapability.HARD_DELETE: frozenset(
        {"provider-surface-inventory.json"}
    ),
    AcceptanceCapability.RESTART_RECONSTRUCTION: frozenset(
        {"probes/restart-reconstruction/evidence.json"}
    ),
    AcceptanceCapability.NATIVE_REDERIVATION_CONSOLIDATION: frozenset(
        {"lineage.json"}
    ),
    AcceptanceCapability.REVOKE_INVALIDATE: frozenset(
        {"provider-surface-inventory.json"}
    ),
    AcceptanceCapability.RAW_INSPECTION: frozenset(
        {"probes/raw-inspection/evidence.json"}
    ),
    AcceptanceCapability.RETRIEVAL: frozenset(
        {"probes/retrieval/evidence.json"}
    ),
    AcceptanceCapability.EXACT_PROVIDER_NATIVE_IDS: frozenset(
        {"probes/exact-native-ids/identity-map.json"}
    ),
    AcceptanceCapability.SOURCE_VERSION_TRANSITIONS: frozenset(
        {"provider-surface-inventory.json"}
    ),
    AcceptanceCapability.TEMPORAL_VALIDITY: frozenset(
        {"provider-surface-inventory.json"}
    ),
    AcceptanceCapability.PROVENANCE_RELATIONSHIP_EDGES: frozenset(
        {"lineage.json"}
    ),
    AcceptanceCapability.RESTART_PERSISTENCE: frozenset(
        {"probes/restart-persistence/evidence.json"}
    ),
    AcceptanceCapability.QUIESCENCE_ASYNC_COMPLETION_PROOF: frozenset(
        {"quiescence.json"}
    ),
    AcceptanceCapability.DETERMINISTIC_OR_RECORDED_ORDERING: frozenset(
        {"probes/retrieval-ordering/evidence.json"}
    ),
    AcceptanceCapability.EXACT_RAW_RESPONSE_CAPTURE: frozenset(
        {"probes/raw-capture/raw-response-identity.json"}
    ),
    AcceptanceCapability.PROVIDER_CONFIGURATION_PINNING: frozenset(
        {"provider-config.json"}
    ),
    AcceptanceCapability.PROVIDER_VERSION_COMMIT_PINNING: frozenset(
        {"provider-version.json"}
    ),
}

SURFACE_INVENTORY_CAPABILITIES = frozenset(
    {
        AcceptanceCapability.UPDATE_SUPERSEDE,
        AcceptanceCapability.HARD_DELETE,
        AcceptanceCapability.REVOKE_INVALIDATE,
        AcceptanceCapability.SOURCE_VERSION_TRANSITIONS,
        AcceptanceCapability.TEMPORAL_VALIDITY,
    }
)


def load_static_api_audit(path: Path = STATIC_AUDIT_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Phase 08B-1 static API audit must be a JSON object")
    return payload


def validate_static_api_audit(payload: Mapping[str, Any]) -> list[str]:
    """Validate the pinned source audit without importing Honcho dependencies."""

    errors: list[str] = []
    upstream = payload.get("upstream")
    if not isinstance(upstream, Mapping):
        errors.append("upstream contract is absent")
    else:
        expected = {
            "version": UPSTREAM_VERSION,
            "tag": UPSTREAM_TAG,
            "commit": UPSTREAM_COMMIT,
        }
        for key, value in expected.items():
            if upstream.get(key) != value:
                errors.append(f"upstream {key} must be {value}")

    compose = payload.get("compose_contract")
    if not isinstance(compose, Mapping):
        errors.append("compose contract is absent")
    else:
        if compose.get("service_names") != ["api", "deriver", "database", "redis"]:
            errors.append("pinned Compose service names changed")
        if compose.get("restart_service_names") != ["api", "deriver"]:
            errors.append("pinned Compose restart service names changed")

    endpoints = payload.get("endpoints")
    if not isinstance(endpoints, list):
        errors.append("endpoints must be a list")
        return errors
    by_id = {
        item.get("id"): item
        for item in endpoints
        if isinstance(item, Mapping) and isinstance(item.get("id"), str)
    }
    if set(by_id) != REQUIRED_AUDIT_ENDPOINTS:
        errors.append("static API audit endpoint IDs do not match the required set")
    for endpoint_id, item in by_id.items():
        for field in (
            "available",
            "method",
            "path",
            "request_body",
            "response_status",
            "response_shape",
            "source_basis",
        ):
            if field not in item:
                errors.append(f"{endpoint_id} omits {field}")
    delete_route = by_id.get("message_delete", {})
    if delete_route.get("available") is not False:
        errors.append("v3.2.1 message_delete must remain explicitly unavailable")
    queue_route = by_id.get("queue_status", {})
    if queue_route.get("session_id_filter_supported") is not True:
        errors.append("queue_status must record native session_id filtering")
    search_route = by_id.get("workspace_message_search", {})
    if search_route.get("method") != "POST" or search_route.get("path") != (
        "/v3/workspaces/{workspace_id}/search"
    ):
        errors.append("workspace_message_search route does not match pinned source")
    if search_route.get("request_schema") != "WorkspaceMessageSearchOptions":
        errors.append("workspace_message_search request schema changed")
    if search_route.get("response_shape") != "list[Message]":
        errors.append("workspace_message_search response shape changed")
    if search_route.get("session_scoping") != "filters.session_id":
        errors.append("workspace_message_search must remain session scoped")
    dream_route = by_id.get("schedule_dream", {})
    if dream_route.get("path") != "/v3/workspaces/{workspace_id}/schedule_dream":
        errors.append("schedule_dream path does not match pinned source")

    configuration = payload.get("configuration_contract")
    if not isinstance(configuration, Mapping):
        errors.append("configuration contract is absent")
        return errors
    embedding = configuration.get("embedding")
    if not isinstance(embedding, Mapping) or embedding.get("assessment") != (
        CURRENT_EMBEDDING_ASSESSMENT
    ):
        errors.append("embedding assessment must remain live-preflight-required")
    elif (
        embedding.get("default_vector_dimensions")
        != UPSTREAM_DEFAULT_EMBEDDING_VECTOR_DIMENSIONS
    ):
        errors.append("upstream default embedding dimension must remain 1536")
    else:
        acceptance = embedding.get("phase08b1_acceptance_configuration")
        expected_acceptance = {
            "backend": "local_cpu_sentence_transformer",
            "package": "sentence-transformers",
            "package_version": SENTENCE_TRANSFORMERS_VERSION,
            "model": EMBEDDING_MODEL,
            "vector_dimensions": ACCEPTANCE_EMBEDDING_VECTOR_DIMENSIONS,
            "offline_cache_only": True,
            "hosted_embedding_forwarding": False,
        }
        if acceptance != expected_acceptance:
            errors.append("Phase08B-1 local embedding configuration changed")
        bootstrap = embedding.get("non_default_pgvector_bootstrap")
        if not isinstance(bootstrap, Mapping):
            errors.append("non-default pgvector bootstrap contract is absent")
        else:
            expected_bootstrap = {
                "upstream_default_dimensions": 1536,
                "acceptance_dimensions": 384,
                "migration_command": "alembic upgrade head",
                "configuration_script": "scripts/configure_embeddings.py",
                "requires_empty_embedding_columns": True,
                "api_deriver_start_after_verified_bootstrap_only": True,
            }
            for key, value in expected_bootstrap.items():
                if bootstrap.get(key) != value:
                    errors.append(f"pgvector bootstrap {key} must be {value!r}")
    batching = configuration.get("deriver_batching")
    if not isinstance(batching, Mapping) or batching.get(
        "acceptance_flush_enabled"
    ) is not ACCEPTANCE_DERIVER_FLUSH_ENABLED:
        errors.append("authorized deriver flush configuration is absent")
    dream = configuration.get("dream")
    if not isinstance(dream, Mapping):
        errors.append("Dream configuration contract is absent")
    else:
        if dream.get("current_enabled") is not ACCEPTANCE_DREAM_ENABLED:
            errors.append("authorized Dream configuration is not enabled")
        if dream.get("enabled_types") != list(ACCEPTANCE_DREAM_ENABLED_TYPES):
            errors.append("authorized Dream types must be exactly omni")
        if dream.get("operation_budget") != DREAM_OPERATION_BUDGET:
            errors.append("Dream operation budget must remain one")
        for role in ("deduction_model", "induction_model"):
            if dream.get(role) != ACCEPTANCE_DREAM_MODEL_CONFIG:
                errors.append(f"{role} does not match the authorized model pin")
    request_contract = configuration.get("openai_request_contract")
    expected_request_contract = {
        "pinned_sdk": "openai==2.36.0",
        "deriver_transport": "openai",
        "deriver_model": "gpt-oss-120b",
        "deriver_temperature": None,
        "deriver_max_tokens": 2500,
        "deriver_structured_output_mode": "json_schema",
        "deriver_strict_json_schema": True,
        "dream_transport": "openai",
        "dream_model": "gpt-oss-120b",
        "dream_temperature": 0,
        "dream_reasoning_effort_field": "reasoning_effort",
        "requested_reasoning_effort": REQUESTED_REASONING_EFFORT,
        "effective_reasoning_effort": EFFECTIVE_REASONING_EFFORT,
        "compatibility_resolution": REASONING_EFFORT_COMPATIBILITY_RESOLUTION,
        "compatibility_reason": REASONING_EFFORT_COMPATIBILITY_REASON,
        "dream_max_tokens": 8192,
        "dream_tools_required": True,
    }
    if not isinstance(request_contract, Mapping):
        errors.append("pinned OpenAI request contract is absent")
    else:
        for key, value in expected_request_contract.items():
            if request_contract.get(key) != value:
                errors.append(f"OpenAI request contract {key} must be {value!r}")
    return errors


class DreamOperationGuard:
    """Fail closed before any second or out-of-purpose Dream scheduling attempt."""

    def __init__(self) -> None:
        self._scheduled = 0

    @property
    def scheduled(self) -> int:
        return self._scheduled

    def authorize(self, purpose: str) -> int:
        if purpose != PROVENANCE_PROBE_PURPOSE:
            raise RuntimeError("Dream is authorized only for the provenance relationship probe")
        if self._scheduled >= DREAM_OPERATION_BUDGET:
            raise RuntimeError("Dream operation budget exhausted; automatic retry is prohibited")
        self._scheduled += 1
        return self._scheduled


def validate_model_endpoint_compatibility(payload: Mapping[str, Any]) -> list[str]:
    """Return Stage-A blockers for the exact pinned model surfaces."""

    blockers: list[str] = []
    if payload.get("structured_output_supported") is not True:
        blockers.append("STRUCTURED_OUTPUT_COMPATIBILITY_FAILED")
    if (
        payload.get("structured_output_mode") != "json_schema"
        or payload.get("structured_output_strict") is not True
        or payload.get("deriver_temperature_omitted") is not True
    ):
        blockers.append("STRUCTURED_OUTPUT_REQUEST_FIDELITY_FAILED")
    if payload.get("dream_tool_calling_supported") is not True:
        blockers.append("DREAM_TOOL_COMPATIBILITY_FAILED")
    if payload.get("requested_reasoning_effort") != REQUESTED_REASONING_EFFORT:
        blockers.append("DREAM_REQUESTED_REASONING_EFFORT_FIDELITY_FAILED")
    if payload.get("effective_reasoning_effort") != EFFECTIVE_REASONING_EFFORT:
        blockers.append("DREAM_REASONING_EFFORT_COMPATIBILITY_FAILED")
    if (
        payload.get("compatibility_resolution")
        != REASONING_EFFORT_COMPATIBILITY_RESOLUTION
        or payload.get("compatibility_reason")
        != REASONING_EFFORT_COMPATIBILITY_REASON
    ):
        blockers.append("DREAM_REASONING_EFFORT_RESOLUTION_AUDIT_FAILED")
    if payload.get("embedding_supported") is not True:
        blockers.append("EMBEDDING_COMPATIBILITY_FAILED")
    dimensions = payload.get("embedding_vector_dimensions")
    if dimensions != ACCEPTANCE_EMBEDDING_VECTOR_DIMENSIONS:
        blockers.append("EMBEDDING_DIMENSION_COMPATIBILITY_FAILED")
    if payload.get("text_backend") != "jetstream_hosted":
        blockers.append("TEXT_BACKEND_PROVENANCE_FAILED")
    if payload.get("text_model") != TEXT_GENERATION_MODEL:
        blockers.append("TEXT_MODEL_PINNING_FAILED")
    if payload.get("embedding_backend") != "local_sentence_transformer":
        blockers.append("EMBEDDING_BACKEND_PROVENANCE_FAILED")
    if payload.get("embedding_model") != EMBEDDING_MODEL:
        blockers.append("EMBEDDING_MODEL_PINNING_FAILED")
    if payload.get("embedding_offline_cache_only") is not True:
        blockers.append("EMBEDDING_OFFLINE_GUARD_FAILED")
    if payload.get("hosted_embedding_forwarding") is not False:
        blockers.append("HOSTED_EMBEDDING_FORWARDING_VIOLATION")
    return blockers


def stage_a_allows_stage_b(payload: Mapping[str, Any]) -> bool:
    """Stage B is unreachable unless every static and model gate passed."""

    blockers = payload.get("blockers")
    compatibility = payload.get("model_endpoint_compatibility")
    return (
        payload.get("status") == "PASS"
        and isinstance(blockers, list)
        and not blockers
        and isinstance(compatibility, Mapping)
        and not validate_model_endpoint_compatibility(compatibility)
    )


def current_baseline_authority_ledger(
    *, attempt_id: str, namespace: str, content: str
) -> AuthorityLedger:
    """Represent the newly written S0-style proposition as current authority."""

    return AuthorityLedger(
        entries=(
            AuthorityLedgerEntry(
                experiment_event_id=f"{attempt_id}__write-v1",
                logical_fact_id=f"{attempt_id}__fact-v1",
                namespace=namespace,
                sequence=1,
                lifecycle_state=LifecycleState.ACTIVE,
                authoritative=True,
                authority_reason="current experiment-defined authority",
                source_content_sha256=content_sha256(content),
            ),
        )
    )


def derive_scenario_classifications(
    native_capabilities: Mapping[AcceptanceCapability, CapabilityClassification],
    *,
    provider_observed_scenarios: set[str] | frozenset[str],
) -> dict[str, CapabilityClassification]:
    """Apply the Phase 08A native-contradiction contract to observed scenarios."""

    unknown_capabilities = set(AcceptanceCapability) - set(native_capabilities)
    if unknown_capabilities:
        missing = ", ".join(sorted(item.value for item in unknown_capabilities))
        raise ValueError(f"native capability matrix is incomplete: {missing}")
    unknown_scenarios = set(provider_observed_scenarios) - set(
        SCENARIO_NATIVE_REQUIREMENTS
    )
    if unknown_scenarios:
        raise ValueError(
            "unknown provider-observed scenarios: " + ", ".join(sorted(unknown_scenarios))
        )

    result: dict[str, CapabilityClassification] = {}
    for scenario, requirements in SCENARIO_NATIVE_REQUIREMENTS.items():
        required = [native_capabilities[capability] for capability in requirements]
        if CapabilityClassification.UNSUPPORTED in required:
            result[scenario] = CapabilityClassification.UNSUPPORTED
        elif CapabilityClassification.BLOCKED in required:
            result[scenario] = CapabilityClassification.BLOCKED
        elif (
            scenario in provider_observed_scenarios
            and all(value is CapabilityClassification.SUPPORTED for value in required)
        ):
            result[scenario] = CapabilityClassification.SUPPORTED
        else:
            result[scenario] = CapabilityClassification.UNKNOWN
    return result


def build_scenario_evidence_matrix(
    scenario_classifications: Mapping[str, CapabilityClassification],
    native_classifications: Mapping[
        AcceptanceCapability, CapabilityClassification
    ],
    capability_bindings: Mapping[AcceptanceCapability, Mapping[str, Any]],
    direct_scenario_bindings: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Bind direct support and contradiction-derived scenario outcomes exactly."""

    if set(scenario_classifications) != set(SCENARIO_NATIVE_REQUIREMENTS):
        raise ValueError("scenario classification matrix is incomplete")
    if set(native_classifications) != set(AcceptanceCapability):
        raise ValueError("native capability matrix is incomplete")

    result: dict[str, dict[str, Any]] = {}
    for scenario, requirements in SCENARIO_NATIVE_REQUIREMENTS.items():
        classification = scenario_classifications[scenario]
        if classification is CapabilityClassification.SUPPORTED:
            binding = direct_scenario_bindings.get(scenario)
            if (
                not isinstance(binding, Mapping)
                or binding.get("provider_observed") is not True
                or not binding.get("artifact")
                or not binding.get("sha256")
            ):
                raise ValueError(
                    f"{scenario} SUPPORTED requires direct scenario evidence"
                )
            result[scenario] = {
                "classification": classification.value,
                "evidence_class": EvidenceClass.PROVIDER_OBSERVED.value,
                "evidence_mode": "DIRECT_SCENARIO_OBSERVATION",
                "direct_scenario_executed": True,
                "evidence_artifact": binding["artifact"],
                "evidence_sha256": binding["sha256"],
                "contradicting_capabilities": [],
                "derivation_rule": "ALL_REQUIRED_NATIVE_CAPABILITIES_SUPPORTED_AND_DIRECT_SCENARIO_OBSERVED",
            }
            continue
        if classification is CapabilityClassification.UNSUPPORTED:
            contradicted = sorted(
                (
                    capability
                    for capability in requirements
                    if native_classifications[capability]
                    is CapabilityClassification.UNSUPPORTED
                ),
                key=lambda item: item.value,
            )
            if not contradicted:
                raise ValueError(
                    f"{scenario} UNSUPPORTED lacks a native contradiction"
                )
            contradictions: list[dict[str, Any]] = []
            for capability in contradicted:
                binding = capability_bindings.get(capability)
                if (
                    not isinstance(binding, Mapping)
                    or binding.get("provider_observed") is not True
                    or not binding.get("artifact")
                    or not binding.get("sha256")
                ):
                    raise ValueError(
                        f"{scenario} contradiction lacks {capability.value} evidence"
                    )
                contradictions.append(
                    {
                        "capability": capability.value,
                        "evidence_artifact": binding["artifact"],
                        "evidence_sha256": binding["sha256"],
                    }
                )
            result[scenario] = {
                "classification": classification.value,
                "evidence_class": EvidenceClass.PROVIDER_OBSERVED.value,
                "evidence_mode": "DERIVED_NATIVE_CAPABILITY_CONTRADICTION",
                "direct_scenario_executed": False,
                "evidence_artifact": None,
                "evidence_sha256": None,
                "contradicting_capabilities": contradictions,
                "derivation_rule": "MANDATORY_NATIVE_CAPABILITY_PROVIDER_OBSERVED_UNSUPPORTED",
            }
            continue
        result[scenario] = {
            "classification": classification.value,
            "evidence_class": None,
            "evidence_mode": None,
            "direct_scenario_executed": False,
            "evidence_artifact": None,
            "evidence_sha256": None,
            "contradicting_capabilities": [],
            "derivation_rule": None,
        }
    return result


def classify_native_search_result(
    create_native_id: str,
    search_native_ids: Sequence[str],
    recorded_ranks: Sequence[int],
) -> dict[AcceptanceCapability, CapabilityClassification]:
    """Classify only the native workspace-search observation."""

    ordering_auditable = (
        bool(search_native_ids)
        and len(set(search_native_ids)) == len(search_native_ids)
        and list(recorded_ranks) == list(range(1, len(search_native_ids) + 1))
    )
    exact_match = (
        bool(create_native_id)
        and create_native_id in search_native_ids
        and ordering_auditable
    )
    return {
        AcceptanceCapability.RETRIEVAL: (
            CapabilityClassification.SUPPORTED
            if exact_match
            else CapabilityClassification.UNKNOWN
        ),
        AcceptanceCapability.EXACT_PROVIDER_NATIVE_IDS: (
            CapabilityClassification.SUPPORTED
            if exact_match
            else CapabilityClassification.UNKNOWN
        ),
        AcceptanceCapability.DETERMINISTIC_OR_RECORDED_ORDERING: (
            CapabilityClassification.SUPPORTED
            if ordering_auditable
            else CapabilityClassification.UNKNOWN
        ),
    }


def validate_queue_status(observation: Mapping[str, Any]) -> None:
    for field in QUEUE_STATUS_FIELDS:
        value = observation.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"queue-status field {field} must be a non-negative integer")


def evaluate_quiescence(
    observations: Sequence[Mapping[str, Any]], *, stable_checks_required: int = 2
) -> dict[str, Any]:
    """Require provider-observable completed work followed by stable empty checks."""

    if stable_checks_required < 2:
        raise ValueError("quiescence requires at least two stable checks")
    completion_observed = False
    stable_empty = 0
    for observation in observations:
        validate_queue_status(observation)
        completion_observed = completion_observed or (
            observation["total_work_units"] > 0
            and observation["completed_work_units"] > 0
        )
        empty = (
            observation["pending_work_units"] == 0
            and observation["in_progress_work_units"] == 0
        )
        stable_empty = stable_empty + 1 if empty else 0
    supported = completion_observed and stable_empty >= stable_checks_required
    return {
        "status": "SUPPORTED" if supported else "UNKNOWN",
        "criterion": "EMPTY_PENDING_QUEUE_AFTER_OBSERVED_COMPLETION"
        if supported
        else None,
        "completion_observed": completion_observed,
        "stable_empty_checks": stable_empty,
        "stable_checks_required": stable_checks_required,
        "sleep_only_success": False,
    }


def evaluate_trigger_relative_quiescence(
    baseline: Mapping[str, Any],
    observations: Sequence[Mapping[str, Any]],
    *,
    stable_checks_required: int = 2,
    maximum_checks: int = QUIESCENCE_MAX_CHECKS,
    poll_seconds: int = QUIESCENCE_POLL_SECONDS,
) -> dict[str, Any]:
    """Require new post-trigger queue activity followed by stable emptiness."""

    validate_queue_status(baseline)
    if stable_checks_required < 2:
        raise ValueError("quiescence requires at least two stable checks")
    if maximum_checks < stable_checks_required or poll_seconds <= 0:
        raise ValueError("quiescence observation bound is invalid")

    stable_empty = 0
    new_work_observed = False
    counter_reset_ambiguity = False
    baseline_empty = (
        baseline["pending_work_units"] == 0
        and baseline["in_progress_work_units"] == 0
    )
    delta_proof: list[dict[str, Any]] = []
    for ordinal, observation in enumerate(observations, start=1):
        validate_queue_status(observation)
        deltas = {
            field: observation[field] - baseline[field]
            for field in QUEUE_STATUS_FIELDS
        }
        reset = (
            deltas["total_work_units"] < 0
            or deltas["completed_work_units"] < 0
        )
        activity = deltas["total_work_units"] > 0 or (
            baseline_empty
            and any(
                deltas[field] > 0
                for field in (
                    "completed_work_units",
                    "in_progress_work_units",
                    "pending_work_units",
                )
            )
        )
        counter_reset_ambiguity = counter_reset_ambiguity or reset
        new_work_observed = new_work_observed or activity
        empty = (
            observation["pending_work_units"] == 0
            and observation["in_progress_work_units"] == 0
        )
        stable_empty = stable_empty + 1 if empty else 0
        delta_proof.append(
            {
                "observation": ordinal,
                "deltas_from_baseline": deltas,
                "new_work_signal": activity,
                "counter_reset_signal": reset,
                "empty": empty,
            }
        )

    supported = (
        new_work_observed
        and not counter_reset_ambiguity
        and stable_empty >= stable_checks_required
    )
    return {
        "status": "SUPPORTED" if supported else "UNKNOWN",
        "criterion": (
            "NEW_POST_TRIGGER_WORK_THEN_STABLE_EMPTY" if supported else None
        ),
        "new_work_observed_after_trigger": new_work_observed,
        "baseline_empty_at_trigger": baseline_empty,
        "counter_reset_or_cleanup_ambiguity": counter_reset_ambiguity,
        "stable_empty_checks": stable_empty,
        "stable_checks_required": stable_checks_required,
        "maximum_checks": maximum_checks,
        "poll_seconds": poll_seconds,
        "maximum_window_seconds": maximum_checks * poll_seconds,
        "observations_recorded": len(observations),
        "bounded_timeout_without_support": (
            len(observations) >= maximum_checks and not supported
        ),
        "delta_proof": delta_proof,
        "sleep_only_success": False,
    }


def evaluate_lineage(
    conclusions: Sequence[Mapping[str, Any]],
    resolved_sources: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Keep explicit conclusions separate and require native resolvable edges."""

    explicit: list[dict[str, Any]] = []
    derived: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    unresolved: list[dict[str, str]] = []
    for item in conclusions:
        level = item.get("level")
        normalized = dict(item)
        if level == "explicit":
            explicit.append(normalized)
            continue
        if level not in DERIVED_CONCLUSION_LEVELS:
            continue
        derived.append(normalized)
        conclusion_id = item.get("id")
        source_ids = item.get("source_ids")
        if not isinstance(conclusion_id, str) or not conclusion_id:
            continue
        if not isinstance(source_ids, list):
            continue
        for source_id in source_ids:
            if not isinstance(source_id, str) or not source_id:
                continue
            edge = {"conclusion_id": conclusion_id, "source_id": source_id}
            edges.append(edge)
            resolved = resolved_sources.get(source_id)
            if not isinstance(resolved, Mapping) or resolved.get("id") != source_id:
                unresolved.append(edge)
    supported = bool(edges) and not unresolved
    return {
        "status": "SUPPORTED" if supported else "UNKNOWN",
        "explicit_conclusions": explicit,
        "derived_conclusions": derived,
        "edges": edges,
        "resolved_source_ids": sorted(resolved_sources),
        "unresolved_edges": unresolved,
        "text_matching_fallback_used": False,
    }


def current_static_preflight_blockers() -> list[str]:
    """Known local-only blockers that require review before another live lifecycle."""

    return [CURRENT_EMBEDDING_ASSESSMENT]


def canonical_json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json_exclusive(path: Path, payload: object) -> str:
    data = canonical_json_bytes(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)
    return sha256_bytes(data)


def bound_runtime_manifest(source: Mapping[str, Any], attempt_id: str) -> dict[str, Any]:
    """Bind the published symbolic manifest without mutating it."""

    payload = dict(source)
    payload.update(
        status="AUTHORIZED_ATTEMPT_BOUND",
        required_base_commit=BASE_COMMIT,
        required_base_commit_resolution="BOUND_BY_PHASE08B1_AUTHORIZATION",
        live_execution_authorized=True,
        provider_internal_model_execution=True,
        provider_internal_model_execution_status="AUTHORIZED_IF_NATIVELY_REQUIRED",
        provider_internal_model_calls=None,
        attempt_id=attempt_id,
    )
    payload["downstream_model_execution"] = False
    payload["downstream_model_calls"] = 0
    payload["rq3_activated"] = False
    payload["rq3_calls"] = 0
    payload["freeze_v2_finalization"] = False
    return payload


def _openapi_operations(payload: Mapping[str, Any]) -> list[dict[str, str]]:
    operations: list[dict[str, str]] = []
    paths = payload.get("paths")
    if not isinstance(paths, Mapping):
        return operations
    for path in sorted(paths):
        path_item = paths[path]
        if not isinstance(path, str) or not isinstance(path_item, Mapping):
            continue
        for method in ("delete", "get", "patch", "post", "put"):
            operation = path_item.get(method)
            if not isinstance(operation, Mapping):
                continue
            operation_id = operation.get("operationId")
            operations.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "operation_id": operation_id if isinstance(operation_id, str) else "",
                }
            )
    return operations


def _openapi_schema_properties(payload: Mapping[str, Any]) -> list[str]:
    properties: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, Mapping):
            declared = value.get("properties")
            if isinstance(declared, Mapping):
                properties.update(
                    key.lower() for key in declared if isinstance(key, str)
                )
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload.get("components", {}))
    return sorted(properties)


def build_provider_surface_inventory(
    openapi: Mapping[str, Any],
    *,
    raw_artifact: str,
    raw_sha256: str,
    raw_bytes: int,
) -> dict[str, Any]:
    """Derive exact absence/presence signals from a live native OpenAPI response."""

    if not raw_artifact or len(raw_sha256) != 64 or raw_bytes <= 0:
        raise ValueError("live OpenAPI inventory requires exact raw-response identity")
    operations = _openapi_operations(openapi)
    schema_properties = _openapi_schema_properties(openapi)

    def selected(predicate: Any) -> list[dict[str, str]]:
        return [operation for operation in operations if predicate(operation)]

    message_operations = selected(lambda item: "/messages" in item["path"])
    message_create = selected(
        lambda item: item["method"] == "POST"
        and item["path"].endswith("/messages")
    )
    message_list = selected(
        lambda item: item["method"] in {"GET", "POST"}
        and item["path"].endswith("/messages/list")
    )
    workspace_message_search = selected(
        lambda item: item["method"] == "POST"
        and item["path"].endswith("/search")
        and "/workspaces/" in item["path"]
        and "/sessions/" not in item["path"]
        and "/peers/" not in item["path"]
    )
    message_update = selected(
        lambda item: item["method"] in {"PATCH", "PUT"}
        and "/messages" in item["path"]
    )
    message_delete = selected(
        lambda item: item["method"] == "DELETE"
        and "/messages/" in item["path"]
    )
    conclusion_operations = selected(lambda item: "/conclusions" in item["path"])
    revoke_operations = selected(
        lambda item: any(
            token in (item["path"] + " " + item["operation_id"]).lower()
            for token in ("revoke", "invalidate")
        )
    )
    transition_fields = sorted(
        set(schema_properties)
        & {
            "previous_version_id",
            "revision",
            "superseded_by",
            "supersedes",
            "version",
            "version_id",
        }
    )
    temporal_fields = sorted(
        set(schema_properties)
        & {
            "effective_at",
            "expires_at",
            "invalidated_at",
            "revoked_at",
            "valid_from",
            "valid_to",
        }
    )
    return {
        "schema_version": "phase08b1-provider-surface-inventory-v1",
        "provider_observed": True,
        "evidence_class": EvidenceClass.PROVIDER_OBSERVED.value,
        "native_request": {"method": "GET", "path": "/openapi.json"},
        "raw_response": {
            "artifact": raw_artifact,
            "sha256": raw_sha256,
            "bytes": raw_bytes,
            "captured_before_normalization": True,
        },
        "message_create_operations": message_create,
        "message_list_operations": message_list,
        "workspace_message_search_operations": workspace_message_search,
        "message_update_or_supersede_operations": message_update,
        "message_record_hard_delete_operations": message_delete,
        "native_revoke_or_invalidate_operations": revoke_operations,
        "conclusion_operations": conclusion_operations,
        "source_version_transition_fields": transition_fields,
        "temporal_validity_fields": temporal_fields,
        "all_message_operations": message_operations,
        "absence_rules": {
            AcceptanceCapability.UPDATE_SUPERSEDE.value: not message_update,
            AcceptanceCapability.HARD_DELETE.value: not message_delete,
            AcceptanceCapability.REVOKE_INVALIDATE.value: not revoke_operations,
            AcceptanceCapability.SOURCE_VERSION_TRANSITIONS.value: not transition_fields,
            AcceptanceCapability.TEMPORAL_VALIDITY.value: not temporal_fields,
        },
    }


def surface_inventory_classifications(
    inventory: Mapping[str, Any],
) -> dict[AcceptanceCapability, CapabilityClassification]:
    """Apply only the predeclared live-surface absence rules."""

    result = {
        capability: CapabilityClassification.UNKNOWN
        for capability in SURFACE_INVENTORY_CAPABILITIES
    }
    request = inventory.get("native_request")
    raw = inventory.get("raw_response")
    if (
        inventory.get("provider_observed") is not True
        or inventory.get("evidence_class") != EvidenceClass.PROVIDER_OBSERVED.value
        or request != {"method": "GET", "path": "/openapi.json"}
        or not isinstance(raw, Mapping)
        or not isinstance(raw.get("artifact"), str)
        or not isinstance(raw.get("sha256"), str)
        or len(raw["sha256"]) != 64
        or not isinstance(raw.get("bytes"), int)
        or raw["bytes"] <= 0
        or raw.get("captured_before_normalization") is not True
    ):
        return result
    observed_surfaces = {
        AcceptanceCapability.UPDATE_SUPERSEDE: (
            "message_update_or_supersede_operations"
        ),
        AcceptanceCapability.HARD_DELETE: (
            "message_record_hard_delete_operations"
        ),
        AcceptanceCapability.REVOKE_INVALIDATE: (
            "native_revoke_or_invalidate_operations"
        ),
        AcceptanceCapability.SOURCE_VERSION_TRANSITIONS: (
            "source_version_transition_fields"
        ),
        AcceptanceCapability.TEMPORAL_VALIDITY: "temporal_validity_fields",
    }
    for capability, field_name in observed_surfaces.items():
        surface = inventory.get(field_name)
        if isinstance(surface, list) and not surface:
            result[capability] = CapabilityClassification.UNSUPPORTED
    return result


def build_provider_raw_index(
    raw_responses: Sequence[Mapping[str, Any]],
    adapter_raw_captures: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Index only actual Honcho responses and never bless an empty index."""

    provider_observed = bool(raw_responses or adapter_raw_captures)
    return {
        "schema_version": "phase08b1-provider-raw-index-v2",
        "provider_observed": provider_observed,
        "evidence_class": (
            EvidenceClass.PROVIDER_OBSERVED.value if provider_observed else None
        ),
        "responses": [dict(item) for item in raw_responses],
        "adapter_raw_captures": [dict(item) for item in adapter_raw_captures],
    }


def index_adapter_raw_captures(
    attempt_root: Path,
    captures: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Verify adapter captures and make their pre-normalization identity reachable."""

    indexed: list[dict[str, Any]] = []
    root = attempt_root.resolve()
    for probe_name in sorted(captures):
        identity = captures[probe_name]
        raw_path = identity.get("artifact_path")
        if not isinstance(raw_path, str):
            raise ValueError(f"adapter capture {probe_name} omitted artifact_path")
        path = Path(raw_path)
        if not path.is_absolute():
            path = attempt_root / path
        resolved = path.resolve()
        if root not in resolved.parents:
            raise ValueError("adapter raw capture escaped the attempt root")
        if not resolved.is_file():
            raise FileNotFoundError(f"adapter raw capture is absent: {resolved}")
        data = resolved.read_bytes()
        digest = sha256_bytes(data)
        if identity.get("sha256") != digest or identity.get("byte_count") != len(data):
            raise ValueError(f"adapter raw capture identity mismatch: {probe_name}")
        indexed.append(
            {
                "probe_name": probe_name,
                "artifact": resolved.relative_to(root).as_posix(),
                "sha256": digest,
                "bytes": len(data),
                "captured_before_normalization": True,
            }
        )
    return indexed


def evidence_binding(
    capability: AcceptanceCapability,
    *,
    artifact: str,
    artifact_sha256: str,
    provider_observed: bool = True,
) -> dict[str, Any]:
    return {
        "capability": capability.value,
        "probe_name": CAPABILITY_PROBE_NAMES[capability],
        "artifact": artifact,
        "sha256": artifact_sha256,
        "provider_observed": provider_observed,
        "evidence_class": (
            EvidenceClass.PROVIDER_OBSERVED.value if provider_observed else None
        ),
    }


def build_capability_assessments(
    attempt_root: Path,
    classifications: Mapping[AcceptanceCapability, CapabilityClassification],
    bindings: Mapping[AcceptanceCapability, Mapping[str, Any]],
    notes: Mapping[AcceptanceCapability, str],
) -> dict[AcceptanceCapability, CapabilityAssessment]:
    """Fail closed unless conclusive claims have exact matching evidence."""

    if set(classifications) != set(AcceptanceCapability):
        raise ValueError("capability classification matrix is incomplete")
    root = attempt_root.resolve()
    result: dict[AcceptanceCapability, CapabilityAssessment] = {}
    for capability in AcceptanceCapability:
        classification = classifications[capability]
        binding = bindings.get(capability)
        if classification is CapabilityClassification.UNKNOWN and binding is None:
            result[capability] = assessment(classification, notes=notes[capability])
            continue
        if binding is None:
            raise ValueError(f"{capability.value} has no capability-specific evidence")
        if binding.get("capability") != capability.value:
            raise ValueError(f"{capability.value} evidence belongs to another capability")
        if binding.get("probe_name") != CAPABILITY_PROBE_NAMES[capability]:
            raise ValueError(f"{capability.value} evidence has the wrong probe identity")
        artifact = binding.get("artifact")
        claimed_sha = binding.get("sha256")
        if not isinstance(artifact, str) or not isinstance(claimed_sha, str):
            raise ValueError(f"{capability.value} evidence identity is incomplete")
        if artifact not in CAPABILITY_EVIDENCE_ARTIFACTS[capability]:
            raise ValueError(
                f"{capability.value} evidence artifact is not valid for that capability"
            )
        path = (attempt_root / artifact).resolve()
        if root not in path.parents or not path.is_file():
            raise FileNotFoundError(
                f"{capability.value} evidence artifact is absent or out of scope"
            )
        actual_sha = sha256_bytes(path.read_bytes())
        if actual_sha != claimed_sha:
            raise ValueError(f"{capability.value} evidence SHA-256 mismatch")
        if classification in {
            CapabilityClassification.SUPPORTED,
            CapabilityClassification.UNSUPPORTED,
        }:
            if (
                binding.get("provider_observed") is not True
                or binding.get("evidence_class")
                != EvidenceClass.PROVIDER_OBSERVED.value
            ):
                raise ValueError(
                    f"{capability.value} conclusive claim is not provider-observed"
                )
            evidence_class = EvidenceClass.PROVIDER_OBSERVED
        elif classification is CapabilityClassification.UNKNOWN:
            evidence_class = (
                EvidenceClass.PROVIDER_OBSERVED
                if binding.get("provider_observed") is True
                else None
            )
        elif classification is CapabilityClassification.BLOCKED:
            if binding.get("provider_observed") is True:
                raise ValueError("BLOCKED operational evidence cannot pretend to be provider-observed")
            evidence_class = None
        else:
            raise ValueError(f"unhandled classification: {classification.value}")
        result[capability] = CapabilityAssessment(
            classification=classification,
            evidence_class=evidence_class,
            evidence_artifact=artifact,
            evidence_sha256=actual_sha,
            notes=notes[capability],
        )
    return result


@dataclass
class LiveCalibrationState:
    """Scientific completion is monotonic and independent of cleanup status."""

    live_calibration_complete: bool = False
    operational_status: str = "PARTIAL"
    operational_blockers: list[str] = field(default_factory=list)

    def complete(
        self,
        *,
        stage_a_passed: bool,
        health_passed: bool,
        probes_terminal: bool,
        scenario_derived: bool,
        evidence_materialized: bool,
    ) -> None:
        gates = {
            "stage_a_passed": stage_a_passed,
            "health_passed": health_passed,
            "probes_terminal": probes_terminal,
            "scenario_derived": scenario_derived,
            "evidence_materialized": evidence_materialized,
        }
        missing = [name for name, value in gates.items() if not value]
        if missing:
            raise RuntimeError(
                "live calibration cannot complete before: " + ", ".join(missing)
            )
        self.live_calibration_complete = True
        self.operational_status = "PASS"

    def fail_operationally(self, blocker: str) -> None:
        self.operational_status = "BLOCKED"
        self.operational_blockers.append(blocker)


def assessment(
    classification: CapabilityClassification,
    *,
    artifact: str | None = None,
    artifact_sha256: str | None = None,
    notes: str | None = None,
) -> CapabilityAssessment:
    evidence_class = None
    if classification in {
        CapabilityClassification.SUPPORTED,
        CapabilityClassification.UNSUPPORTED,
    }:
        evidence_class = EvidenceClass.PROVIDER_OBSERVED
    return CapabilityAssessment(
        classification=classification,
        evidence_class=evidence_class,
        evidence_artifact=artifact,
        evidence_sha256=artifact_sha256,
        notes=notes,
    )


def acceptance_record(
    capabilities: Mapping[AcceptanceCapability, CapabilityAssessment],
    *,
    live_calibration_complete: bool,
) -> ProviderAcceptanceRecord:
    pending = ProviderAcceptanceRecord.model_construct(
        provider_id="honcho",
        decision=AcceptanceDecision.PENDING_LIVE_ACCEPTANCE,
        live_calibration_complete=live_calibration_complete,
        capabilities=dict(capabilities),
    )
    decision = honcho_acceptance_decision(pending)
    return ProviderAcceptanceRecord(
        provider_id="honcho",
        decision=decision,
        live_calibration_complete=live_calibration_complete,
        capabilities=dict(capabilities),
    )


def write_completion(attempt_root: Path, extra: Mapping[str, Any]) -> str:
    artifacts: dict[str, dict[str, object]] = {}
    for name in REQUIRED_ARTIFACTS:
        path = attempt_root / name
        if not path.is_file():
            raise FileNotFoundError(f"required Phase 08B-1 artifact is absent: {name}")
        data = path.read_bytes()
        artifacts[name] = {"sha256": sha256_bytes(data), "bytes": len(data)}
    payload = {
        "schema_version": "phase08b1-completion-v1",
        "artifacts": artifacts,
        "model_boundary_artifact_created": False,
        **dict(extra),
    }
    return write_json_exclusive(attempt_root / "completion.json", payload)
