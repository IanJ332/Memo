"""Evidence-backed capability and Provider-5 acceptance contracts."""

from __future__ import annotations

import re
from enum import Enum
from typing import Self

from pydantic import model_validator

from memlife.models.mediator import EvidenceClass
from memlife.models.memory import NonEmptyText, StrictModel

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class AcceptanceCapability(str, Enum):
    CREATE_WRITE = "create_write"
    UPDATE_SUPERSEDE = "update_supersede"
    HARD_DELETE = "hard_delete"
    RESTART_RECONSTRUCTION = "restart_reconstruction"
    NATIVE_REDERIVATION_CONSOLIDATION = "native_rederivation_consolidation"
    REVOKE_INVALIDATE = "revoke_invalidate"
    RAW_INSPECTION = "raw_inspection"
    RETRIEVAL = "retrieval"
    EXACT_PROVIDER_NATIVE_IDS = "exact_provider_native_ids"
    SOURCE_VERSION_TRANSITIONS = "source_version_transitions"
    TEMPORAL_VALIDITY = "temporal_validity"
    PROVENANCE_RELATIONSHIP_EDGES = "provenance_relationship_edges"
    RESTART_PERSISTENCE = "restart_persistence"
    QUIESCENCE_ASYNC_COMPLETION_PROOF = "quiescence_async_completion_proof"
    DETERMINISTIC_OR_RECORDED_ORDERING = "deterministic_or_recorded_ordering"
    EXACT_RAW_RESPONSE_CAPTURE = "exact_raw_response_capture"
    PROVIDER_CONFIGURATION_PINNING = "provider_configuration_pinning"
    PROVIDER_VERSION_COMMIT_PINNING = "provider_version_commit_pinning"


class CapabilityClassification(str, Enum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    UNKNOWN = "UNKNOWN"
    BLOCKED = "BLOCKED"


class AcceptanceDecision(str, Enum):
    PENDING_LIVE_ACCEPTANCE = "PENDING_LIVE_ACCEPTANCE"
    GO = "GO"
    NO_GO = "NO_GO"


class CapabilityAssessment(StrictModel):
    """One capability classified only from captured calibration evidence."""

    classification: CapabilityClassification
    evidence_class: EvidenceClass | None = None
    evidence_artifact: NonEmptyText | None = None
    evidence_sha256: str | None = None
    notes: NonEmptyText | None = None

    @model_validator(mode="after")
    def conclusive_classification_requires_audit_evidence(self) -> Self:
        conclusive = {
            CapabilityClassification.SUPPORTED,
            CapabilityClassification.UNSUPPORTED,
            CapabilityClassification.BLOCKED,
        }
        if self.classification in {
            CapabilityClassification.SUPPORTED,
            CapabilityClassification.UNSUPPORTED,
        }:
            if self.evidence_class is not EvidenceClass.PROVIDER_OBSERVED:
                raise ValueError(
                    "SUPPORTED and UNSUPPORTED require PROVIDER_OBSERVED evidence"
                )
        if self.evidence_class is EvidenceClass.SYNTHETIC_RQ4_CHALLENGE:
            raise ValueError("capability classification cannot use synthetic evidence")
        if self.classification in conclusive:
            if not self.evidence_artifact or not self.evidence_sha256:
                raise ValueError(
                    "SUPPORTED, UNSUPPORTED, and BLOCKED require an evidence "
                    "artifact and SHA-256"
                )
        if (self.evidence_artifact is None) != (self.evidence_sha256 is None):
            raise ValueError(
                "evidence_artifact and evidence_sha256 must be populated together"
            )
        if self.evidence_class is not None and self.evidence_artifact is None:
            raise ValueError("classified evidence requires an artifact and SHA-256")
        if self.evidence_sha256 is not None and not _SHA256.fullmatch(
            self.evidence_sha256
        ):
            raise ValueError("evidence_sha256 must be lowercase SHA-256")
        return self


class ScenarioCapabilityAssessment(CapabilityAssessment):
    """Evidence-bound support classification for one provider/scenario cell."""


RETAINDB_REQUIRED_CAPABILITIES = frozenset(
    {
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
)

HONCHO_REQUIRED_CAPABILITIES = frozenset(
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

GRAPHITI_REQUIRED_CAPABILITIES = frozenset(
    {
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
)

_REQUIRED_CAPABILITIES_BY_PROVIDER = {
    "honcho": HONCHO_REQUIRED_CAPABILITIES,
    "retaindb-server": RETAINDB_REQUIRED_CAPABILITIES,
    "graphiti": GRAPHITI_REQUIRED_CAPABILITIES,
}


class ProviderAcceptanceRecord(StrictModel):
    """Future live-calibration record; Phase 08A leaves it pending."""

    provider_id: NonEmptyText
    decision: AcceptanceDecision = AcceptanceDecision.PENDING_LIVE_ACCEPTANCE
    live_calibration_complete: bool = False
    capabilities: dict[AcceptanceCapability, CapabilityAssessment]

    @model_validator(mode="after")
    def validate_complete_capability_matrix(self) -> Self:
        if set(self.capabilities) != set(AcceptanceCapability):
            raise ValueError("acceptance record must classify every capability")
        derived = provider_acceptance_decision(self)
        if self.decision is not derived:
            raise ValueError(
                f"declared decision {self.decision.value} disagrees with "
                f"derived decision {derived.value}"
            )
        return self


def provider_acceptance_decision(
    record: ProviderAcceptanceRecord,
) -> AcceptanceDecision:
    """Derive the sole acceptance decision from predeclared requirements."""

    try:
        required = _REQUIRED_CAPABILITIES_BY_PROVIDER[record.provider_id]
    except KeyError as exc:
        raise ValueError(
            f"provider {record.provider_id!r} has no predeclared acceptance gate"
        ) from exc
    if not record.live_calibration_complete:
        return AcceptanceDecision.PENDING_LIVE_ACCEPTANCE
    if all(
        record.capabilities[capability].classification
        is CapabilityClassification.SUPPORTED
        for capability in required
    ):
        return AcceptanceDecision.GO
    return AcceptanceDecision.NO_GO


def retaindb_acceptance_decision(
    record: ProviderAcceptanceRecord,
) -> AcceptanceDecision:
    """Apply the frozen RetainDB go/no-go gate without contacting a provider."""

    if record.provider_id != "retaindb-server":
        raise ValueError("RetainDB gate requires provider_id 'retaindb-server'")
    return provider_acceptance_decision(record)


def honcho_acceptance_decision(
    record: ProviderAcceptanceRecord,
) -> AcceptanceDecision:
    """Apply the predeclared Honcho entry gate without contacting a provider."""

    if record.provider_id != "honcho":
        raise ValueError("Honcho gate requires provider_id 'honcho'")
    return provider_acceptance_decision(record)


def graphiti_acceptance_decision(
    record: ProviderAcceptanceRecord,
) -> AcceptanceDecision:
    """Evaluate Graphiti independently after it becomes an eligible fallback."""

    if record.provider_id != "graphiti":
        raise ValueError("Graphiti gate requires provider_id 'graphiti'")
    return provider_acceptance_decision(record)
