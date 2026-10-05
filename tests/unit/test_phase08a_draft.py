"""Fail-closed validation tests for the Phase 08A Freeze-v2 draft."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from memlife.models.provider_acceptance import AcceptanceCapability
from memlife.runner.phase08a import (
    EXPECTED_PROVIDER5_TRANSITIONS,
    EXPECTED_RQ3_ACTIVATION_GATE,
    FREEZE_V1_SHA256,
    SCENARIO_NATIVE_REQUIREMENTS,
    load_phase08a_draft,
    validate_evidence_bound_matrices,
    validate_extension_schedule,
    validate_phase08a_draft,
    validate_provider5_state,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DRAFT_PATH = REPO_ROOT / "experiments" / "freeze" / "experiment-freeze-v2.draft.json"
MANIFEST_PATH = REPO_ROOT / "manifests" / "phase-08a-expansion-freeze-v2-foundation.json"


def _draft() -> dict[str, object]:
    return load_phase08a_draft(DRAFT_PATH)


def _errors(payload: dict[str, object]) -> str:
    return "\n".join(validate_phase08a_draft(payload))


def _cell(
    classification: str,
    *,
    observed: bool = True,
) -> dict[str, object]:
    if classification == "UNKNOWN":
        return {
            "classification": classification,
            "evidence_class": None,
            "evidence_artifact": None,
            "evidence_sha256": None,
            "notes": None,
        }
    return {
        "classification": classification,
        "evidence_class": "PROVIDER_OBSERVED" if observed else None,
        "evidence_artifact": f"calibration/{classification.casefold()}.json",
        "evidence_sha256": "c" * 64,
        "notes": None,
    }


def _support_scenario(
    payload: dict[str, object], provider: str, scenario: str
) -> None:
    payload["provider_capability_matrix_placeholder"][provider][scenario] = _cell(
        "SUPPORTED"
    )
    for capability in SCENARIO_NATIVE_REQUIREMENTS[scenario]:
        payload["provider_native_capability_matrix_placeholder"][provider][
            capability.value
        ] = _cell("SUPPORTED")


def _valid_honcho_schedule() -> dict[str, object]:
    payload = deepcopy(_draft())
    payload["provider_extension"]["provider_4"]["acceptance_decision"] = "GO"
    _support_scenario(payload, "honcho", "S0")
    payload["run_contract"]["scheduled_runs"] = [
        {
            "provider": "honcho",
            "scenario": "S0",
            "repetition": repetition,
            "run_id": f"freeze-v2__honcho__S0__r{repetition}",
            "synthetic_substitute": False,
        }
        for repetition in (1, 2, 3)
    ]
    return payload


def _schedule_errors(payload: dict[str, object]) -> str:
    return "\n".join(
        validate_extension_schedule(
            payload["run_contract"],
            payload["provider_extension"],
            payload["provider_capability_matrix_placeholder"],
            payload["provider_native_capability_matrix_placeholder"],
        )
    )


def _matrix_errors(payload: dict[str, object]) -> str:
    return "\n".join(
        validate_evidence_bound_matrices(
            payload["provider_capability_matrix_placeholder"],
            payload["provider_native_capability_matrix_placeholder"],
        )
    )


def test_repository_phase08a_draft_is_valid_and_non_final() -> None:
    payload = _draft()
    assert validate_phase08a_draft(payload) == []
    assert payload["is_final_freeze"] is False
    assert payload["prior_evidence"]["freeze_sha256"] == FREEZE_V1_SHA256


def test_phase08a_manifest_records_local_only_validation() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["status"] == "PASS"
    assert manifest["freeze_v1"]["modified"] is False
    assert manifest["freeze_v2"]["finalized"] is False
    assert manifest["provider_execution"] is False
    assert manifest["jetstream_used"] is False
    assert manifest["hosted_model_calls"] == 0
    assert manifest["rq3"] == {
        "activated": False,
        "calls": 0,
        "empirical_contexts": 0,
    }


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda item: item.update(is_final_freeze=True), "is_final_freeze"),
        (
            lambda item: item.update(draft_status="FINAL"),
            "explicitly non-final",
        ),
        (
            lambda item: item.update(artifact_kind="EXPERIMENT_FREEZE"),
            "design draft",
        ),
        (
            lambda item: item["prior_evidence"].update(freeze_sha256="0" * 64),
            "Freeze v1 reference",
        ),
        (
            lambda item: item["run_contract"].update(
                new_provider_repetitions_per_natively_supported_cell=2
            ),
            "repetitions must equal 3",
        ),
        (
            lambda item: item["run_contract"].update(
                no_synthetic_substitute_for_unsupported=False
            ),
            "synthetic substitutes",
        ),
        (lambda item: item["rq3"].update(enabled=True), "RQ3 must default"),
        (
            lambda item: item["rq3"].update(
                synthetic_challenges_can_activate_empirical_rq3=True
            ),
            "synthetic challenges cannot activate",
        ),
        (
            lambda item: item["retaindb_acceptance_gate"].update(
                acceptance_result="GO"
            ),
            "RetainDB acceptance must remain pending",
        ),
        (
            lambda item: item["provider_extension"]["provider_5"].update(
                active_provider="graphiti"
            ),
            "draft cannot activate",
        ),
    ],
)
def test_draft_validator_rejects_contract_regressions(mutation, message: str) -> None:
    payload = deepcopy(_draft())
    mutation(payload)
    assert message in _errors(payload)


def test_rq3_activation_gate_requires_exact_ordered_membership() -> None:
    assert tuple(_draft()["rq3"]["activation_gate"]) == EXPECTED_RQ3_ACTIVATION_GATE

    replaced = deepcopy(_draft())
    replaced["rq3"]["activation_gate"][3] = "lineage_is_enough"
    assert "exactly match" in _errors(replaced)

    deleted = deepcopy(_draft())
    deleted["rq3"]["activation_gate"].pop()
    assert "exactly match" in _errors(deleted)

    duplicated = deepcopy(_draft())
    duplicated["rq3"]["activation_gate"][9] = duplicated["rq3"]["activation_gate"][0]
    assert len(duplicated["rq3"]["activation_gate"]) == 10
    assert "exactly match" in _errors(duplicated)


def test_predeclared_provider_acceptance_gates_are_locked() -> None:
    honcho = deepcopy(_draft())
    honcho["honcho_acceptance_gate"]["go_requires_all"].pop()
    assert "Honcho go gate requirements" in _errors(honcho)

    retaindb = deepcopy(_draft())
    retaindb["retaindb_acceptance_gate"]["go_requires_all"].pop()
    assert "RetainDB go gate requirements" in _errors(retaindb)

    fallback = deepcopy(_draft())
    fallback["retaindb_acceptance_gate"][
        "fallback_requires_independent_acceptance"
    ] = False
    assert "independent live acceptance" in _errors(fallback)

    graphiti = deepcopy(_draft())
    graphiti["graphiti_acceptance_gate"]["acceptance_result"] = "GO"
    assert "must remain ineligible" in _errors(graphiti)


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("design_only", False, "design-only"),
        ("full_d2_algorithm_frozen", True, "must not be frozen"),
        ("outputs", ["ALLOW", "DENY"], "outputs must be exactly"),
        ("position", "BEFORE_RETRIEVAL", "position mismatch"),
        ("role", "RETRIEVER", "role mismatch"),
        ("invariants_for_future_policy", ["ALLOW_ALL"], "invariants mismatch"),
    ],
)
def test_rq4_design_semantics_are_exactly_locked(
    field: str, replacement: object, message: str
) -> None:
    payload = deepcopy(_draft())
    payload["rq4"][field] = replacement
    assert message in _errors(payload)


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("identities", ["logical_fact_and_version"], "identity model"),
        (
            "authorization_primitives_prohibited",
            ["embedding similarity"],
            "primitive prohibitions",
        ),
        (
            "canonical_proposition_identity_condition",
            "LLM-approved canonicalization",
            "identity condition",
        ),
        ("indeterminate_identity_outcome", "ALLOW", "QUARANTINE"),
    ],
)
def test_identity_security_semantics_are_exactly_locked(
    field: str, replacement: object, message: str
) -> None:
    payload = deepcopy(_draft())
    payload["identity_model"][field] = replacement
    assert message in _errors(payload)


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("finalization_requires", ["approval"], "prerequisites mismatch"),
        ("immutable_after_finalization", False, "must be immutable"),
        (
            "semantic_changes_require_new_draft_revision",
            False,
            "new draft revision",
        ),
        (
            "completed_capability_matrix_definition",
            "A string-only matrix is complete.",
            "evidence definition mismatch",
        ),
    ],
)
def test_change_control_is_exactly_locked(
    field: str, replacement: object, message: str
) -> None:
    payload = deepcopy(_draft())
    payload["change_control"][field] = replacement
    assert message in _errors(payload)


def test_execution_authorization_requires_exact_false_keyset() -> None:
    extra = deepcopy(_draft())
    extra["execution_authorization"]["future_provider"] = False
    assert "keys must match" in _errors(extra)

    missing = deepcopy(_draft())
    del missing["execution_authorization"]["jetstream"]
    assert "keys must match" in _errors(missing)

    enabled = deepcopy(_draft())
    enabled["execution_authorization"]["rq3"] = True
    assert "cannot authorize execution" in _errors(enabled)


def test_phase08a_unknown_scenario_and_native_cells_need_no_evidence() -> None:
    payload = _draft()
    assert validate_evidence_bound_matrices(
        payload["provider_capability_matrix_placeholder"],
        payload["provider_native_capability_matrix_placeholder"],
        require_phase08a_unknown=True,
    ) == []


@pytest.mark.parametrize(
    ("cell", "message"),
    [
        (
            {
                "classification": "SUPPORTED",
                "evidence_class": None,
                "evidence_artifact": None,
                "evidence_sha256": None,
                "notes": None,
            },
            "PROVIDER_OBSERVED",
        ),
        (
            {
                "classification": "SUPPORTED",
                "evidence_class": "SYNTHETIC_RQ4_CHALLENGE",
                "evidence_artifact": "synthetic.json",
                "evidence_sha256": "d" * 64,
                "notes": None,
            },
            "PROVIDER_OBSERVED",
        ),
        (
            {
                "classification": "UNSUPPORTED",
                "evidence_class": None,
                "evidence_artifact": None,
                "evidence_sha256": None,
                "notes": None,
            },
            "PROVIDER_OBSERVED",
        ),
        (
            {
                "classification": "BLOCKED",
                "evidence_class": None,
                "evidence_artifact": None,
                "evidence_sha256": None,
                "notes": None,
            },
            "evidence artifact",
        ),
        ("SUPPORTED", "evidence-bound assessment object"),
    ],
)
def test_scenario_cells_fail_closed_without_required_evidence(
    cell: object, message: str
) -> None:
    payload = deepcopy(_draft())
    payload["provider_capability_matrix_placeholder"]["honcho"]["S0"] = cell
    assert message in _matrix_errors(payload)


@pytest.mark.parametrize(
    "classification",
    ["UNKNOWN", "UNSUPPORTED", "BLOCKED"],
)
def test_schedule_rejects_every_non_supported_cell(classification: str) -> None:
    payload = _valid_honcho_schedule()
    payload["provider_capability_matrix_placeholder"]["honcho"]["S0"] = _cell(
        classification
    )
    assert "only evidence-backed SUPPORTED" in _schedule_errors(payload)


def test_schedule_rejects_supported_looking_cell_without_observed_evidence() -> None:
    payload = _valid_honcho_schedule()
    payload["provider_capability_matrix_placeholder"]["honcho"]["S0"] = {
        "classification": "SUPPORTED",
        "evidence_class": None,
        "evidence_artifact": None,
        "evidence_sha256": None,
        "notes": None,
    }
    errors = _schedule_errors(payload)
    assert "PROVIDER_OBSERVED" in errors
    assert "only evidence-backed SUPPORTED" in errors

    bare = _valid_honcho_schedule()
    bare["provider_capability_matrix_placeholder"]["honcho"]["S0"] = "SUPPORTED"
    bare_errors = _schedule_errors(bare)
    assert "evidence-bound assessment object" in bare_errors
    assert "only evidence-backed SUPPORTED" in bare_errors


@pytest.mark.parametrize(
    ("scenario", "capability"),
    [
        ("S1", AcceptanceCapability.UPDATE_SUPERSEDE),
        ("S3", AcceptanceCapability.RESTART_PERSISTENCE),
        ("S4", AcceptanceCapability.NATIVE_REDERIVATION_CONSOLIDATION),
        ("S5", AcceptanceCapability.REVOKE_INVALIDATE),
    ],
)
def test_supported_scenario_rejects_native_capability_contradiction(
    scenario: str, capability: AcceptanceCapability
) -> None:
    payload = deepcopy(_draft())
    _support_scenario(payload, "honcho", scenario)
    payload["provider_native_capability_matrix_placeholder"]["honcho"][
        capability.value
    ] = _cell("UNSUPPORTED")
    errors = _matrix_errors(payload)
    assert f"{scenario} SUPPORTED contradicts native {capability.value}" in errors


def test_native_support_does_not_infer_scenario_support() -> None:
    payload = deepcopy(_draft())
    payload["provider_native_capability_matrix_placeholder"]["honcho"][
        AcceptanceCapability.UPDATE_SUPERSEDE.value
    ] = _cell("SUPPORTED")
    assert _matrix_errors(payload) == ""


def test_valid_future_schedule_requires_exact_three_repetitions() -> None:
    payload = _valid_honcho_schedule()
    assert _schedule_errors(payload) == ""

    missing = deepcopy(payload)
    missing["run_contract"]["scheduled_runs"].pop()
    assert "must contain repetitions 1, 2, 3" in _schedule_errors(missing)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda run: run.update(provider="mem0", run_id="freeze-v1__mem0__S0__r1"),
            "old provider run scheduled",
        ),
        (
            lambda run: run.update(provider="unknown", run_id="freeze-v2__unknown__S0__r1"),
            "not a known extension candidate",
        ),
        (lambda run: run.update(scenario="S6"), "scenario must be S0 through S5"),
        (lambda run: run.update(repetition=4), "repetition must be 1, 2, or 3"),
        (lambda run: run.update(repetition=True), "repetition must be 1, 2, or 3"),
        (lambda run: run.update(run_id="wrong"), "run_id does not match"),
        (lambda run: run.update(synthetic_substitute=True), "synthetic substitutes"),
    ],
)
def test_schedule_rejects_invalid_coordinates_and_substitutes(
    mutation, message: str
) -> None:
    payload = _valid_honcho_schedule()
    mutation(payload["run_contract"]["scheduled_runs"][0])
    assert message in _schedule_errors(payload)


def test_schedule_rejects_duplicates_unsupported_cells_and_overflow() -> None:
    duplicate = _valid_honcho_schedule()
    duplicate["run_contract"]["scheduled_runs"].append(
        deepcopy(duplicate["run_contract"]["scheduled_runs"][0])
    )
    errors = _schedule_errors(duplicate)
    assert "provider/scenario/repetition must be unique" in errors
    assert "run IDs must be unique" in errors

    unsupported = _valid_honcho_schedule()
    unsupported["provider_capability_matrix_placeholder"]["honcho"]["S0"] = (
        _cell("UNSUPPORTED")
    )
    assert "only evidence-backed SUPPORTED" in _schedule_errors(unsupported)

    overflow = _valid_honcho_schedule()
    overflow["run_contract"]["scheduled_runs"] = (
        overflow["run_contract"]["scheduled_runs"] * 13
    )
    assert len(overflow["run_contract"]["scheduled_runs"]) > 36
    assert "cannot exceed 36" in _schedule_errors(overflow)


def test_schedule_requires_exact_fields_and_rejects_both_provider5_candidates() -> None:
    missing_field = _valid_honcho_schedule()
    del missing_field["run_contract"]["scheduled_runs"][0]["scenario"]
    assert "fields must match the exact contract" in _schedule_errors(missing_field)

    both = _valid_honcho_schedule()
    both["provider_extension"]["provider_5"]["active_provider"] = "retaindb-server"
    _support_scenario(both, "retaindb-server", "S0")
    _support_scenario(both, "graphiti", "S0")
    for provider in ("retaindb-server", "graphiti"):
        both["run_contract"]["scheduled_runs"].extend(
            {
                "provider": provider,
                "scenario": "S0",
                "repetition": repetition,
                "run_id": f"freeze-v2__{provider}__S0__r{repetition}",
                "synthetic_substitute": False,
            }
            for repetition in (1, 2, 3)
        )
    assert "cannot both be scheduled" in _schedule_errors(both)


def test_provider5_state_machine_requires_independent_graphiti_acceptance() -> None:
    current = deepcopy(_draft()["provider_extension"]["provider_5"])
    assert tuple(current["valid_state_transitions"]) == EXPECTED_PROVIDER5_TRANSITIONS
    assert validate_provider5_state(current) == []

    retaindb_go = deepcopy(current)
    retaindb_go["primary"]["acceptance_decision"] = "GO"
    retaindb_go["active_provider"] = "retaindb-server"
    assert validate_provider5_state(retaindb_go) == []

    graphiti_pending = deepcopy(current)
    graphiti_pending["primary"]["acceptance_decision"] = "NO_GO"
    graphiti_pending["fallback"]["acceptance_decision"] = "PENDING_LIVE_ACCEPTANCE"
    assert validate_provider5_state(graphiti_pending) == []

    graphiti_go = deepcopy(graphiti_pending)
    graphiti_go["fallback"]["acceptance_decision"] = "GO"
    graphiti_go["active_provider"] = "graphiti"
    assert validate_provider5_state(graphiti_go) == []

    auto_accepted = deepcopy(current)
    auto_accepted["primary"]["acceptance_decision"] = "NO_GO"
    auto_accepted["fallback"]["acceptance_decision"] = "NOT_ELIGIBLE"
    auto_accepted["active_provider"] = "graphiti"
    assert "independent Graphiti acceptance" in "\n".join(
        validate_provider5_state(auto_accepted)
    )


def test_no_freeze_v1_run_can_be_scheduled_for_rerun() -> None:
    payload = deepcopy(_draft())
    payload["run_contract"]["scheduled_runs"] = [
        {
            "provider": "mem0",
            "run_id": "freeze-v1__mem0__S1__r1",
            "repetition": 1,
            "synthetic_substitute": False,
        }
    ]
    assert "old provider run scheduled for rerun" in _errors(payload)


def test_scheduled_unsupported_operation_cannot_use_synthetic_equivalent() -> None:
    payload = deepcopy(_draft())
    payload["run_contract"]["scheduled_runs"] = [
        {
            "provider": "honcho",
            "run_id": "freeze-v2__honcho__S5__r1",
            "repetition": 1,
            "synthetic_substitute": True,
        }
    ]
    assert "scheduled run must prohibit synthetic substitutes" in _errors(payload)


def test_evidence_class_is_mandatory_in_draft_contract() -> None:
    payload = deepcopy(_draft())
    del payload["evidence_classes"]["PROVIDER_OBSERVED"]
    assert "evidence classes are incomplete" in _errors(payload)


def test_graphiti_fallback_and_retaindb_primary_are_exclusive() -> None:
    payload = deepcopy(_draft())
    payload["provider_extension"]["provider_5"]["mutually_exclusive"] = False
    assert "must be mutually exclusive" in _errors(payload)


def test_model_boundary_artifact_requires_separate_model_authorization() -> None:
    payload = deepcopy(_draft())
    payload["run_artifact_contract"]["required"].append("model-boundary.json")
    errors = _errors(payload)
    assert "required run artifact contract mismatch" in errors
    assert "cannot be unconditionally required" in errors


def test_loader_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    malformed = tmp_path / "duplicate.json"
    malformed.write_text('{"draft_status":"x","draft_status":"y"}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        load_phase08a_draft(malformed)
