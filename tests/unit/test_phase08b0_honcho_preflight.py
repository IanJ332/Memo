"""Local-only Phase 08B-0 Honcho preflight regression tests."""

from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import socket

import pytest
from pydantic import ValidationError

from memlife.adapters.honcho import (
    DirectoryRawArtifactCapture,
    HonchoAdapterConfig,
    HonchoAdapterSkeleton,
    HonchoLiveAdapter,
    HonchoLiveConfig,
    LiveProviderExecutionNotAuthorized,
    NativeHonchoResponse,
    NormalizedHonchoRecord,
    QuiescenceContract,
    RawArtifactIdentity,
    capture_before_normalization,
)
from memlife.models.lifecycle import LifecycleState
from memlife.models.mediator import EvidenceClass
from memlife.models.memory import (
    DeleteCommand,
    QueryCommand,
    SupersedeCommand,
    WriteCommand,
)
from memlife.models.provider_acceptance import (
    AcceptanceCapability,
    AcceptanceDecision,
    CapabilityAssessment,
    CapabilityClassification,
    HONCHO_REQUIRED_CAPABILITIES,
    ProviderAcceptanceRecord,
    honcho_acceptance_decision,
)
from memlife.runner.phase08a import SCENARIO_NATIVE_REQUIREMENTS, load_phase08a_draft
from memlife.runner.phase08b0 import (
    load_json_object,
    validate_live_manifest,
    validate_probe_plan,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = (
    REPO_ROOT / "experiments" / "acceptance" / "phase08b0-honcho-probe-plan.json"
)
LIVE_MANIFEST_PATH = REPO_ROOT / "manifests" / "phase-08b1-honcho-live-acceptance.json"
FREEZE_V2_DRAFT = REPO_ROOT / "experiments" / "freeze" / "experiment-freeze-v2.draft.json"


def _plan() -> dict[str, object]:
    return load_json_object(PLAN_PATH)


def _all_unknown() -> dict[AcceptanceCapability, CapabilityAssessment]:
    return {
        capability: CapabilityAssessment(
            classification=CapabilityClassification.UNKNOWN
        )
        for capability in AcceptanceCapability
    }


def _supported(capability: AcceptanceCapability) -> CapabilityAssessment:
    return CapabilityAssessment(
        classification=CapabilityClassification.SUPPORTED,
        evidence_class=EvidenceClass.PROVIDER_OBSERVED,
        evidence_artifact=f"test-only/{capability.value}.json",
        evidence_sha256="b" * 64,
    )


def test_honcho_live_methods_fail_closed_without_network(monkeypatch) -> None:
    def network_forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("unit test attempted network access")

    monkeypatch.setattr(socket, "create_connection", network_forbidden)
    adapter = HonchoAdapterSkeleton()
    calls = (
        lambda: adapter.capabilities,
        lambda: adapter.reset_namespace("phase08b0"),
        lambda: adapter.write(WriteCommand(namespace="n", content="value")),
        lambda: adapter.query(QueryCommand(namespace="n", query="value")),
        lambda: adapter.update_or_supersede(
            SupersedeCommand(namespace="n", memory_id="native-1", content="v2")
        ),
        lambda: adapter.delete_or_invalidate(
            DeleteCommand(
                namespace="n",
                memory_id="native-1",
                disposition=LifecycleState.DELETED,
            )
        ),
        lambda: adapter.list_or_inspect("n"),
        adapter.restart,
        lambda: adapter.trigger_native_rederivation("n"),
        lambda: adapter.wait_for_quiescence("operation-1"),
    )
    for call in calls:
        with pytest.raises(LiveProviderExecutionNotAuthorized, match="08B-0"):
            call()


def test_phase08b0_configuration_cannot_authorize_live_execution() -> None:
    config = HonchoAdapterConfig()
    assert config.live_execution_authorized is False
    assert config.network_access_authorized is False
    assert config.provider_sdk_installed is False
    with pytest.raises(ValidationError, match="False"):
        HonchoAdapterConfig(live_execution_authorized=True)


def test_raw_native_bytes_are_captured_before_normalization() -> None:
    events: list[str] = []
    raw = b'{"id":"honcho-native-1","content":"fixture"}'

    class Capture:
        def capture_raw(
            self, *, probe_name: str, native_bytes: bytes
        ) -> RawArtifactIdentity:
            events.append(f"capture:{probe_name}")
            return RawArtifactIdentity(
                artifact_path="probes/retrieval/provider-raw-response.json",
                sha256=hashlib.sha256(native_bytes).hexdigest(),
                byte_count=len(native_bytes),
            )

    def normalize(
        native_bytes: bytes, identity: RawArtifactIdentity
    ) -> NormalizedHonchoRecord:
        events.append("normalize")
        assert native_bytes == raw
        return NormalizedHonchoRecord(
            provider_native_id="honcho-native-1",
            canonical_proposition_id="fixture-proposition-v1",
            logical_fact_id="fixture-fact-1",
            raw_artifact=identity,
            retrieval_rank=1,
        )

    record = capture_before_normalization(
        probe_name="honcho_capability_retrieval_v1",
        native_bytes=raw,
        capture=Capture(),
        normalize=normalize,
    )
    assert events == ["capture:honcho_capability_retrieval_v1", "normalize"]
    assert len(
        {
            record.provider_native_id,
            record.canonical_proposition_id,
            record.logical_fact_id,
        }
    ) == 3


def test_raw_capture_identity_mismatch_fails_before_normalization() -> None:
    normalized = False

    class BadCapture:
        def capture_raw(
            self, *, probe_name: str, native_bytes: bytes
        ) -> RawArtifactIdentity:
            return RawArtifactIdentity(
                artifact_path="raw.json",
                sha256="0" * 64,
                byte_count=len(native_bytes),
            )

    def normalize(
        native_bytes: bytes, identity: RawArtifactIdentity
    ) -> NormalizedHonchoRecord:
        nonlocal normalized
        normalized = True
        raise AssertionError("normalizer must not run")

    with pytest.raises(ValueError, match="SHA-256"):
        capture_before_normalization(
            probe_name="probe",
            native_bytes=b"native",
            capture=BadCapture(),
            normalize=normalize,
        )
    assert normalized is False


def test_probe_plan_is_complete_required_and_evidence_neutral() -> None:
    plan = _plan()
    assert validate_probe_plan(plan) == []
    probes = plan["capability_probes"]
    by_capability = {item["capability"]: item for item in probes}
    assert set(by_capability) == {item.value for item in AcceptanceCapability}
    assert {
        AcceptanceCapability(name)
        for name, item in by_capability.items()
        if item["required_for_honcho_entry"]
    } == HONCHO_REQUIRED_CAPABILITIES
    assert {item["current_outcome"] for item in probes} == {"UNKNOWN"}
    assert all(item["current_evidence_artifact"] is None for item in probes)
    assert all(item["current_evidence_sha256"] is None for item in probes)

    prepopulated = deepcopy(plan)
    prepopulated["capability_probes"][0]["current_outcome"] = "SUPPORTED"
    assert "must remain UNKNOWN" in "\n".join(validate_probe_plan(prepopulated))


def test_exact_native_ids_do_not_require_raw_inspection_for_honcho_entry() -> None:
    plan = _plan()
    probes = {
        item["capability"]: item for item in plan["capability_probes"]
    }
    native_ids = probes[AcceptanceCapability.EXACT_PROVIDER_NATIVE_IDS.value]
    raw_inspection = probes[AcceptanceCapability.RAW_INSPECTION.value]

    assert raw_inspection["current_outcome"] == "UNKNOWN"
    assert raw_inspection["required_for_honcho_entry"] is False
    assert AcceptanceCapability.RAW_INSPECTION not in HONCHO_REQUIRED_CAPABILITIES
    assert native_ids["required_for_honcho_entry"] is True
    rule = native_ids["supported_if"].casefold()
    assert "create/write and retrieval" in rule
    assert "optional raw/native inspection" in rule
    assert "not required" in rule

    assessments = _all_unknown()
    for capability in HONCHO_REQUIRED_CAPABILITIES:
        assessments[capability] = _supported(capability)
    record = ProviderAcceptanceRecord(
        provider_id="honcho",
        decision=AcceptanceDecision.GO,
        live_calibration_complete=True,
        capabilities=assessments,
    )
    assert record.capabilities[
        AcceptanceCapability.RAW_INSPECTION
    ].classification is CapabilityClassification.UNKNOWN
    assert record.capabilities[
        AcceptanceCapability.EXACT_PROVIDER_NATIVE_IDS
    ].classification is CapabilityClassification.SUPPORTED
    assert honcho_acceptance_decision(record) is AcceptanceDecision.GO


def test_scenario_plan_preserves_phase08a_contradiction_rules() -> None:
    plan = _plan()
    scenarios = {item["scenario"]: item for item in plan["scenario_probes"]}
    assert set(scenarios) == set(SCENARIO_NATIVE_REQUIREMENTS)
    assert {item["current_outcome"] for item in scenarios.values()} == {"UNKNOWN"}
    for scenario, requirements in SCENARIO_NATIVE_REQUIREMENTS.items():
        assert scenarios[scenario]["required_native_capabilities"] == sorted(
            capability.value for capability in requirements
        )
        assert "scenario lacks its own" in scenarios[scenario]["unknown_if"]

    changed = deepcopy(plan)
    changed["scenario_probes"][0]["required_native_capabilities"] = ["retrieval"]
    assert "native contradiction rules changed" in "\n".join(
        validate_probe_plan(changed)
    )


def test_quiescence_contract_prohibits_sleep_only_success() -> None:
    contract = QuiescenceContract()
    assert contract.sleep_only_success_allowed is False
    assert contract.maximum_checks >= contract.stable_retrieval_checks_required >= 2
    plan = _plan()
    assert plan["quiescence_contract"]["sleep_only_success_allowed"] is False
    assert plan["quiescence_contract"]["bounded_checks_required"] is True


def test_failure_policy_and_semantic_judges_are_predeclared() -> None:
    plan = _plan()
    assert plan["failure_policy"]["installation_failure"] == "BLOCKED"
    assert plan["failure_policy"]["missing_native_id"].endswith(
        "CANNOT_BE_SUPPORTED"
    )
    assert plan["failure_policy"]["documentation_only_claim"] == "UNKNOWN"
    assert set(plan["semantic_judges_prohibited"]) == {
        "LLM",
        "EMBEDDING",
        "SEMANTIC_SIMILARITY",
        "FUZZY_EQUIVALENCE",
    }


def test_unknown_acceptance_record_stays_pending_and_uses_frozen_gate() -> None:
    record = ProviderAcceptanceRecord(
        provider_id="honcho",
        decision=AcceptanceDecision.PENDING_LIVE_ACCEPTANCE,
        live_calibration_complete=False,
        capabilities=_all_unknown(),
    )
    assert honcho_acceptance_decision(record) is AcceptanceDecision.PENDING_LIVE_ACCEPTANCE
    assert set(record.capabilities) == set(AcceptanceCapability)


def test_synthetic_evidence_cannot_become_provider_observed_capability_evidence() -> None:
    with pytest.raises(ValidationError, match="synthetic evidence"):
        CapabilityAssessment(
            classification=CapabilityClassification.BLOCKED,
            evidence_class=EvidenceClass.SYNTHETIC_RQ4_CHALLENGE,
            evidence_artifact="synthetic.json",
            evidence_sha256="a" * 64,
        )


def test_execution_controls_and_future_manifest_remain_unauthorized() -> None:
    plan = _plan()
    controls = plan["execution_controls"]
    assert controls["rq3_activated"] is False
    assert controls["rq3_calls"] == 0
    assert controls["downstream_model_execution"] is False
    assert controls["downstream_model_calls"] == 0
    assert controls["provider_internal_model_execution"] is False
    assert controls["provider_internal_model_calls"] == 0
    assert controls["freeze_v2_finalization"] is False
    assert controls["jetstream_state"] == "SHELVED"

    manifest = load_json_object(LIVE_MANIFEST_PATH)
    assert validate_live_manifest(manifest) == []
    assert manifest["live_execution_authorized"] is False
    assert manifest["required_base_commit"] == "PHASE08B0_COMMITTED_HEAD"
    assert manifest["downstream_model_execution"] is False
    assert manifest["downstream_model_calls"] == 0
    assert manifest["rq3_activated"] is False
    assert manifest["rq3_calls"] == 0
    assert manifest["provider_internal_model_execution"] is False
    assert manifest["provider_internal_model_execution_status"] == (
        "NOT_CURRENTLY_AUTHORIZED"
    )
    assert manifest["provider_internal_model_authorization_requirement"] == (
        "REQUIRES_SEPARATE_PHASE08B1_AUTHORIZATION_IF_REQUIRED_BY_PINNED_"
        "HONCHO_CONFIGURATION"
    )
    assert manifest["provider_internal_model_calls"] is None
    assert manifest["provider_internal_model_configuration_pinning_required"] is True
    assert manifest["provider_internal_model_call_accounting_required"] is True
    assert manifest["provider_internal_model_role"] == (
        "PROVIDER_INTERNAL_BEHAVIOR_NOT_AUTHORITY_SECURITY_JUDGE"
    )


def test_live_manifest_rejects_extra_and_missing_top_level_fields() -> None:
    manifest = load_json_object(LIVE_MANIFEST_PATH)

    extra = deepcopy(manifest)
    extra["undeclared_authorization_override"] = True
    assert "fields must match the exact contract" in "\n".join(
        validate_live_manifest(extra)
    )

    missing = deepcopy(manifest)
    missing.pop("downstream_model_calls")
    assert "fields must match the exact contract" in "\n".join(
        validate_live_manifest(missing)
    )


def test_execution_controls_reject_extra_and_missing_fields() -> None:
    plan = _plan()

    extra = deepcopy(plan)
    extra["execution_controls"]["undeclared_authorization_override"] = True
    assert "execution_controls fields must match the exact contract" in "\n".join(
        validate_probe_plan(extra)
    )

    missing = deepcopy(plan)
    missing["execution_controls"].pop("downstream_model_calls")
    assert "execution_controls fields must match the exact contract" in "\n".join(
        validate_probe_plan(missing)
    )


def test_model_boundary_is_conditional_and_freeze_v2_remains_non_final() -> None:
    plan = _plan()
    artifacts = plan["artifact_contract"]
    assert "model-boundary.json" not in artifacts["required"]
    assert artifacts["conditional"]["model-boundary.json"] == (
        "ONLY_IF_SEPARATELY_AUTHORIZED_DOWNSTREAM_MODEL_EXECUTION"
    )
    draft = load_phase08a_draft(FREEZE_V2_DRAFT)
    assert draft["is_final_freeze"] is False
    assert draft["draft_status"] == "NON_FINAL_DESIGN_ONLY"


def test_phase08b1_live_adapter_captures_native_bytes_before_mapping(tmp_path) -> None:
    create_raw = (
        b'[{"id":"msg-native-1","content":"fictional alpha",'
        b'"peer_id":"peer-a","created_at":"2026-10-05T00:00:00Z"}]'
    )
    search_raw = (
        b'[{"id":"msg-native-1","content":"fictional alpha",'
        b'"peer_id":"peer-a","created_at":"2026-10-05T00:00:00Z"}]'
    )
    inspection_raw = (
        b'{"items":[{"id":"msg-native-1","content":"fictional alpha",'
        b'"peer_id":"peer-a","created_at":"2026-10-05T00:00:00Z"}],'
        b'"total":1,"page":1,"size":10,"pages":1}'
    )

    class Transport:
        requests = []
        responses = [
            NativeHonchoResponse(status_code=201, body=create_raw),
            NativeHonchoResponse(status_code=200, body=search_raw),
            NativeHonchoResponse(status_code=200, body=inspection_raw),
        ]

        def request(self, method, path, *, payload=None):
            self.requests.append((method, path, payload))
            return self.responses.pop(0)

    adapter = HonchoLiveAdapter(
        HonchoLiveConfig(
            base_url="http://127.0.0.1:8000",
            workspace_id="phase08b1-attempt",
            session_id="phase08b1-session",
            peer_id="peer-a",
        ),
        transport=Transport(),
        capture=DirectoryRawArtifactCapture(tmp_path),
    )
    written = adapter.write(
        WriteCommand(namespace="phase08b1-session", content="fictional alpha")
    )
    retrieved = adapter.query(
        QueryCommand(
            namespace="phase08b1-session",
            query="Where is fictional alpha?",
            limit=10,
        )
    )
    inspected = adapter.list_or_inspect("phase08b1-session")
    assert written.memory_id == retrieved[0].memory_id == "msg-native-1"
    assert inspected[0].memory_id == "msg-native-1"
    assert retrieved[0].metadata["retrieval_rank"] == 1
    assert Transport.requests[1] == (
        "POST",
        "v3/workspaces/phase08b1-attempt/search",
        {
            "query": "Where is fictional alpha?",
            "filters": {"session_id": "phase08b1-session"},
            "limit": 10,
        },
    )
    assert "/messages/list" in Transport.requests[2][1]
    assert Transport.requests[1][1] != Transport.requests[2][1]
    create_path = (
        tmp_path
        / "honcho_capability_create_write_v1"
        / "provider-raw-response.json"
    )
    retrieval_path = (
        tmp_path / "honcho_capability_retrieval_v1" / "provider-raw-response.json"
    )
    assert create_path.read_bytes() == create_raw
    inspection_path = (
        tmp_path / "honcho_capability_raw_inspection_v1" / "provider-raw-response.json"
    )
    assert retrieval_path.read_bytes() == search_raw
    assert inspection_path.read_bytes() == inspection_raw


def test_phase08b1_live_adapter_rejects_empty_retrieval_query(tmp_path) -> None:
    class NoTransport:
        def request(self, method, path, *, payload=None):
            raise AssertionError("empty query must fail before provider contact")

    adapter = HonchoLiveAdapter(
        HonchoLiveConfig(
            base_url="http://127.0.0.1:8000",
            workspace_id="w",
            session_id="s",
            peer_id="p",
        ),
        transport=NoTransport(),
        capture=DirectoryRawArtifactCapture(tmp_path),
    )
    with pytest.raises(Exception, match="non-empty search query"):
        adapter.query(QueryCommand(namespace="s", query="", limit=1))
