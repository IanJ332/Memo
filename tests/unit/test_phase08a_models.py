"""Strict Phase 08A mediator and provider-acceptance contract tests."""

from copy import deepcopy
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from memlife.models.lifecycle import LifecycleState
from memlife.models.mediator import (
    AuthorityDecision,
    AuthoritySnapshot,
    CandidateEnvelope,
    EvidenceClass,
    MediatorAction,
    RelationEdge,
    canonical_contract_sha256,
    count_provider_observations,
)
from memlife.models.provenance import MemorySurface
from memlife.models.provider_acceptance import (
    GRAPHITI_REQUIRED_CAPABILITIES,
    HONCHO_REQUIRED_CAPABILITIES,
    RETAINDB_REQUIRED_CAPABILITIES,
    AcceptanceCapability,
    AcceptanceDecision,
    CapabilityAssessment,
    CapabilityClassification,
    ProviderAcceptanceRecord,
    graphiti_acceptance_decision,
    honcho_acceptance_decision,
    retaindb_acceptance_decision,
)

FIXED_TIME = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)
RAW_SHA = "1" * 64
BODY_SHA = "2" * 64
SOURCE_SHA = "3" * 64


def _candidate(**updates: object) -> CandidateEnvelope:
    values: dict[str, object] = {
        "provider": "fixture-provider",
        "namespace": "phase08a-test",
        "candidate_id": "candidate-1",
        "retrieval_rank": 1,
        "surface": MemorySurface.DERIVED,
        "raw_bytes_sha256": RAW_SHA,
        "canonical_body_sha256": BODY_SHA,
        "canonicalization_id": "fixture-body-v1",
        "logical_fact_id": "fact-1",
        "source_ids": ("source-1",),
        "relation_edges": (
            RelationEdge(
                source_id="source-1",
                target_id="candidate-1",
                relation="DERIVED_FROM",
            ),
        ),
        "lifecycle_hint": LifecycleState.ACTIVE,
        "retrieval_timestamp": FIXED_TIME,
        "evidence_class": EvidenceClass.PROVIDER_OBSERVED,
    }
    values.update(updates)
    return CandidateEnvelope.model_validate(values)


def _snapshot(**updates: object) -> AuthoritySnapshot:
    values: dict[str, object] = {
        "logical_fact_id": "fact-1",
        "version_id": "version-2",
        "source_event_id": "write-v2",
        "lifecycle_state": LifecycleState.ACTIVE,
        "authoritative": True,
        "sequence": 2,
        "supersedes": "version-1",
        "canonical_proposition_sha256": BODY_SHA,
        "source_record_sha256": SOURCE_SHA,
    }
    values.update(updates)
    return AuthoritySnapshot.model_validate(values)


def _decision(**updates: object) -> AuthorityDecision:
    values: dict[str, object] = {
        "decision": MediatorAction.QUARANTINE,
        "reason_codes": ("UNRESOLVED_SOURCE",),
        "current_witnesses": ("candidate-1",),
        "unresolved_edges": (
            RelationEdge(
                source_id="candidate-1",
                target_id="unknown-source",
                relation="CLAIMS_SOURCE",
            ),
        ),
        "input_bundle_sha256": "4" * 64,
        "authority_snapshot_sha256": "5" * 64,
        "policy_version": "rq4-design-only-v0",
        "decision_timestamp": FIXED_TIME,
    }
    values.update(updates)
    return AuthorityDecision.model_validate(values)


def test_candidate_envelope_is_strict_and_requires_evidence_class() -> None:
    candidate = _candidate()
    assert candidate.raw_bytes_sha256 == RAW_SHA
    assert candidate.canonical_body_sha256 == BODY_SHA
    assert candidate.evidence_class is EvidenceClass.PROVIDER_OBSERVED

    payload = candidate.model_dump(mode="json")
    payload.pop("evidence_class")
    with pytest.raises(ValidationError, match="evidence_class"):
        CandidateEnvelope.model_validate(payload)

    with pytest.raises(ValidationError, match="Extra inputs"):
        CandidateEnvelope.model_validate(
            {**candidate.model_dump(mode="json"), "semantic_match_score": 0.99}
        )


def test_candidate_rejects_invalid_hash_time_and_canonicalization() -> None:
    with pytest.raises(ValidationError, match="raw_bytes_sha256"):
        _candidate(raw_bytes_sha256="not-a-hash")
    with pytest.raises(ValidationError, match="retrieval_timestamp"):
        _candidate(retrieval_timestamp=datetime(2026, 10, 5, 12, 0))
    with pytest.raises(ValidationError, match="populated together"):
        _candidate(canonicalization_id=None)


def test_malformed_provenance_representation_fails_closed() -> None:
    payload = _candidate().model_dump(mode="json")
    payload["relation_edges"] = [
        {"source_id": "source-1", "relation": "DERIVED_FROM"}
    ]
    with pytest.raises(ValidationError, match="target_id"):
        CandidateEnvelope.model_validate(payload)
    with pytest.raises(ValidationError, match="endpoints must be distinct"):
        RelationEdge(
            source_id="same",
            target_id="same",
            relation="DERIVED_FROM",
        )


def test_authority_snapshot_enforces_authority_and_identity_fields() -> None:
    snapshot = _snapshot()
    assert snapshot.canonical_proposition_sha256 == BODY_SHA
    assert snapshot.source_record_sha256 == SOURCE_SHA
    assert snapshot.logical_fact_id == "fact-1"
    assert snapshot.version_id == "version-2"

    with pytest.raises(ValidationError, match="only ACTIVE"):
        _snapshot(lifecycle_state=LifecycleState.SUPERSEDED)
    with pytest.raises(ValidationError, match="cannot supersede itself"):
        _snapshot(supersedes="version-2")


def test_authority_decision_requires_auditable_disjoint_evidence() -> None:
    decision = _decision()
    assert decision.decision is MediatorAction.QUARANTINE
    with pytest.raises(ValidationError, match="reason_codes must be unique"):
        _decision(reason_codes=("X", "X"))
    with pytest.raises(ValidationError, match="must be disjoint"):
        _decision(stale_witnesses=("candidate-1",))


def test_record_proposition_and_logical_identities_remain_separate() -> None:
    candidate = _candidate()
    payload = candidate.model_dump(mode="json")
    assert payload["raw_bytes_sha256"] == RAW_SHA
    assert payload["canonical_body_sha256"] == BODY_SHA
    assert payload["logical_fact_id"] == "fact-1"
    assert len({RAW_SHA, BODY_SHA, payload["logical_fact_id"]}) == 3


def test_synthetic_challenges_never_count_as_provider_observations() -> None:
    provider = _candidate(candidate_id="provider")
    synthetic = _candidate(
        candidate_id="synthetic",
        retrieval_rank=2,
        evidence_class=EvidenceClass.SYNTHETIC_RQ4_CHALLENGE,
    )
    assert count_provider_observations((provider, synthetic)) == 1


def test_exact_input_hashing_is_deterministic_and_order_sensitive() -> None:
    first = _candidate(candidate_id="first", retrieval_rank=1)
    second = _candidate(candidate_id="second", retrieval_rank=2)
    digest = canonical_contract_sha256((first, second))
    assert digest == canonical_contract_sha256((first, second))
    assert digest != canonical_contract_sha256((second, first))
    assert digest != canonical_contract_sha256((deepcopy(first),))


def _assessments(
    default: CapabilityClassification,
) -> dict[AcceptanceCapability, CapabilityAssessment]:
    result: dict[AcceptanceCapability, CapabilityAssessment] = {}
    for capability in AcceptanceCapability:
        if default is CapabilityClassification.UNKNOWN:
            result[capability] = CapabilityAssessment(classification=default)
        else:
            result[capability] = CapabilityAssessment(
                classification=default,
                evidence_class=(
                    EvidenceClass.PROVIDER_OBSERVED
                    if default is not CapabilityClassification.BLOCKED
                    else None
                ),
                evidence_artifact=f"calibration/{capability.value}.json",
                evidence_sha256="a" * 64,
            )
    return result


def _observed_assessment(
    classification: CapabilityClassification,
) -> CapabilityAssessment:
    return CapabilityAssessment(
        classification=classification,
        evidence_class=(
            EvidenceClass.PROVIDER_OBSERVED
            if classification is not CapabilityClassification.BLOCKED
            else None
        ),
        evidence_artifact=f"calibration/{classification.value.casefold()}.json",
        evidence_sha256="b" * 64,
    )


def test_provider_acceptance_requires_complete_observed_capability_evidence() -> None:
    assessments = _assessments(CapabilityClassification.UNKNOWN)
    assessments.pop(AcceptanceCapability.RETRIEVAL)
    with pytest.raises(ValidationError, match="classify every capability"):
        ProviderAcceptanceRecord(
            provider_id="honcho",
            capabilities=assessments,
        )
    with pytest.raises(ValidationError, match="PROVIDER_OBSERVED"):
        CapabilityAssessment(classification=CapabilityClassification.SUPPORTED)


@pytest.mark.parametrize(
    "classification",
    [CapabilityClassification.UNSUPPORTED, CapabilityClassification.BLOCKED],
)
def test_conclusive_negative_capabilities_require_audit_evidence(
    classification: CapabilityClassification,
) -> None:
    with pytest.raises(ValidationError, match="evidence artifact"):
        CapabilityAssessment(
            classification=classification,
            evidence_class=(
                EvidenceClass.PROVIDER_OBSERVED
                if classification is CapabilityClassification.UNSUPPORTED
                else None
            ),
        )
    assert _observed_assessment(classification).classification is classification


def test_documentation_only_claim_cannot_establish_capability_support() -> None:
    with pytest.raises(ValidationError, match="PROVIDER_OBSERVED"):
        CapabilityAssessment(
            classification=CapabilityClassification.SUPPORTED,
            notes="Provider documentation says this operation is supported.",
        )


def test_capability_evidence_artifact_and_hash_are_atomic() -> None:
    with pytest.raises(ValidationError, match="populated together"):
        CapabilityAssessment(
            classification=CapabilityClassification.UNKNOWN,
            evidence_artifact="calibration/partial.json",
        )


def test_retaindb_gate_stays_pending_until_live_calibration() -> None:
    pending = ProviderAcceptanceRecord(
        provider_id="retaindb-server",
        capabilities=_assessments(CapabilityClassification.UNKNOWN),
    )
    assert retaindb_acceptance_decision(pending) is AcceptanceDecision.PENDING_LIVE_ACCEPTANCE


def test_provider_entry_requirements_are_predeclared_exactly() -> None:
    assert HONCHO_REQUIRED_CAPABILITIES == {
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
    assert RETAINDB_REQUIRED_CAPABILITIES == {
        AcceptanceCapability.CREATE_WRITE,
        AcceptanceCapability.EXACT_RAW_RESPONSE_CAPTURE,
        AcceptanceCapability.DETERMINISTIC_OR_RECORDED_ORDERING,
        AcceptanceCapability.EXACT_PROVIDER_NATIVE_IDS,
        AcceptanceCapability.SOURCE_VERSION_TRANSITIONS,
        AcceptanceCapability.TEMPORAL_VALIDITY,
        AcceptanceCapability.RETRIEVAL,
        AcceptanceCapability.RESTART_PERSISTENCE,
        AcceptanceCapability.PROVENANCE_RELATIONSHIP_EDGES,
        AcceptanceCapability.PROVIDER_CONFIGURATION_PINNING,
        AcceptanceCapability.PROVIDER_VERSION_COMMIT_PINNING,
    }
    assert GRAPHITI_REQUIRED_CAPABILITIES == {
        AcceptanceCapability.CREATE_WRITE,
        AcceptanceCapability.RETRIEVAL,
        AcceptanceCapability.EXACT_PROVIDER_NATIVE_IDS,
        AcceptanceCapability.EXACT_RAW_RESPONSE_CAPTURE,
        AcceptanceCapability.DETERMINISTIC_OR_RECORDED_ORDERING,
        AcceptanceCapability.PROVENANCE_RELATIONSHIP_EDGES,
        AcceptanceCapability.SOURCE_VERSION_TRANSITIONS,
        AcceptanceCapability.TEMPORAL_VALIDITY,
        AcceptanceCapability.RESTART_PERSISTENCE,
        AcceptanceCapability.PROVIDER_CONFIGURATION_PINNING,
        AcceptanceCapability.PROVIDER_VERSION_COMMIT_PINNING,
        AcceptanceCapability.QUIESCENCE_ASYNC_COMPLETION_PROOF,
    }


def test_retaindb_gate_is_go_only_when_every_required_field_is_supported() -> None:
    supported = _assessments(CapabilityClassification.SUPPORTED)
    go = ProviderAcceptanceRecord(
        provider_id="retaindb-server",
        decision=AcceptanceDecision.GO,
        live_calibration_complete=True,
        capabilities=supported,
    )
    assert retaindb_acceptance_decision(go) is AcceptanceDecision.GO

    unavailable = dict(supported)
    unavailable[AcceptanceCapability.TEMPORAL_VALIDITY] = _observed_assessment(
        CapabilityClassification.UNSUPPORTED
    )
    with pytest.raises(ValidationError, match="disagrees with derived decision"):
        ProviderAcceptanceRecord(
            provider_id="retaindb-server",
            decision=AcceptanceDecision.GO,
            live_calibration_complete=True,
            capabilities=unavailable,
        )
    no_go = ProviderAcceptanceRecord(
        provider_id="retaindb-server",
        decision=AcceptanceDecision.NO_GO,
        live_calibration_complete=True,
        capabilities=unavailable,
    )
    assert retaindb_acceptance_decision(no_go) is AcceptanceDecision.NO_GO

    with pytest.raises(ValidationError, match="disagrees with derived decision"):
        ProviderAcceptanceRecord(
            provider_id="retaindb-server",
            decision=AcceptanceDecision.NO_GO,
            live_calibration_complete=True,
            capabilities=supported,
        )


@pytest.mark.parametrize(
    "missing",
    [
        AcceptanceCapability.CREATE_WRITE,
        AcceptanceCapability.EXACT_RAW_RESPONSE_CAPTURE,
        AcceptanceCapability.DETERMINISTIC_OR_RECORDED_ORDERING,
    ],
)
def test_retaindb_cannot_go_without_minimum_runnability_evidence(
    missing: AcceptanceCapability,
) -> None:
    capabilities = _assessments(CapabilityClassification.SUPPORTED)
    capabilities[missing] = CapabilityAssessment(
        classification=CapabilityClassification.UNKNOWN
    )
    with pytest.raises(ValidationError, match="disagrees with derived decision"):
        ProviderAcceptanceRecord(
            provider_id="retaindb-server",
            decision=AcceptanceDecision.GO,
            live_calibration_complete=True,
            capabilities=capabilities,
        )
    rejected = ProviderAcceptanceRecord(
        provider_id="retaindb-server",
        decision=AcceptanceDecision.NO_GO,
        live_calibration_complete=True,
        capabilities=capabilities,
    )
    assert retaindb_acceptance_decision(rejected) is AcceptanceDecision.NO_GO


@pytest.mark.parametrize(
    "missing",
    [
        AcceptanceCapability.TEMPORAL_VALIDITY,
        AcceptanceCapability.SOURCE_VERSION_TRANSITIONS,
        AcceptanceCapability.RESTART_PERSISTENCE,
    ],
)
def test_graphiti_cannot_go_without_temporal_fallback_evidence(
    missing: AcceptanceCapability,
) -> None:
    capabilities = _assessments(CapabilityClassification.SUPPORTED)
    capabilities[missing] = CapabilityAssessment(
        classification=CapabilityClassification.UNKNOWN
    )
    with pytest.raises(ValidationError, match="disagrees with derived decision"):
        ProviderAcceptanceRecord(
            provider_id="graphiti",
            decision=AcceptanceDecision.GO,
            live_calibration_complete=True,
            capabilities=capabilities,
        )
    rejected = ProviderAcceptanceRecord(
        provider_id="graphiti",
        decision=AcceptanceDecision.NO_GO,
        live_calibration_complete=True,
        capabilities=capabilities,
    )
    assert graphiti_acceptance_decision(rejected) is AcceptanceDecision.NO_GO


def test_honcho_gate_uses_predeclared_entry_requirements_only() -> None:
    capabilities = _assessments(CapabilityClassification.UNKNOWN)
    for capability in HONCHO_REQUIRED_CAPABILITIES:
        capabilities[capability] = _observed_assessment(
            CapabilityClassification.SUPPORTED
        )
    accepted = ProviderAcceptanceRecord(
        provider_id="honcho",
        decision=AcceptanceDecision.GO,
        live_calibration_complete=True,
        capabilities=capabilities,
    )
    assert honcho_acceptance_decision(accepted) is AcceptanceDecision.GO
    assert capabilities[AcceptanceCapability.HARD_DELETE].classification is (
        CapabilityClassification.UNKNOWN
    )

    missing = dict(capabilities)
    missing[AcceptanceCapability.QUIESCENCE_ASYNC_COMPLETION_PROOF] = (
        CapabilityAssessment(classification=CapabilityClassification.UNKNOWN)
    )
    rejected = ProviderAcceptanceRecord(
        provider_id="honcho",
        decision=AcceptanceDecision.NO_GO,
        live_calibration_complete=True,
        capabilities=missing,
    )
    assert honcho_acceptance_decision(rejected) is AcceptanceDecision.NO_GO


def test_optional_identity_strings_reject_empty_or_whitespace_values() -> None:
    for field in ("canonicalization_id", "logical_fact_id"):
        with pytest.raises(ValidationError, match=field):
            _candidate(**{field: "   "})
    for field in ("supersedes", "superseded_by"):
        with pytest.raises(ValidationError, match=field):
            _snapshot(**{field: "   "})
