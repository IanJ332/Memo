"""Provider-independent provenance, retrieval, and consequence trace models."""

from __future__ import annotations

import json
import re
from datetime import datetime
from enum import Enum
from typing import Any, Self, TypeAlias
from uuid import NAMESPACE_URL, uuid5

from pydantic import Field, field_validator, model_validator

from memlife.models.lifecycle import LifecycleState
from memlife.models.memory import NonEmptyText, StrictModel
from memlife.models.safety import reject_sensitive_keys

TRACE_SCHEMA_VERSION = "0.1"
_ID_KIND = re.compile(r"^[a-z][a-z0-9-]*$")


class ProvenanceStatus(str, Enum):
    """How much evidence supports a provenance assertion."""

    KNOWN = "KNOWN"
    UNKNOWN = "UNKNOWN"
    UNSUPPORTED = "UNSUPPORTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ProvenanceRelation(str, Enum):
    CREATED_FROM = "CREATED_FROM"
    DERIVED_FROM = "DERIVED_FROM"
    SUPERSEDES = "SUPERSEDES"
    INVALIDATES = "INVALIDATES"
    RETRIEVED_AS = "RETRIEVED_AS"
    FILTERED_FROM = "FILTERED_FROM"
    PASSED_TO_MODEL = "PASSED_TO_MODEL"
    CAUSED_DECISION = "CAUSED_DECISION"
    AUTHORIZED_ACTION = "AUTHORIZED_ACTION"
    UNKNOWN = "UNKNOWN"
    UNSUPPORTED = "UNSUPPORTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class MemorySurface(str, Enum):
    SOURCE = "SOURCE"
    VECTOR_INDEX = "VECTOR_INDEX"
    DERIVED = "DERIVED"
    SUMMARY = "SUMMARY"
    PROFILE = "PROFILE"
    GRAPH = "GRAPH"
    CACHE = "CACHE"
    RETRIEVAL = "RETRIEVAL"
    UNKNOWN = "UNKNOWN"


class EnforcementAction(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    TAG = "TAG"


class FailureOrigin(str, Enum):
    SOURCE_LIFECYCLE = "SOURCE_LIFECYCLE"
    DERIVED_STATE = "DERIVED_STATE"
    RETRIEVAL = "RETRIEVAL"
    ENFORCEMENT = "ENFORCEMENT"
    MODEL = "MODEL"
    TOOL_AUTHORIZATION = "TOOL_AUTHORIZATION"
    UNKNOWN = "UNKNOWN"


class DownstreamExecutionStatus(str, Enum):
    NOT_RUN = "NOT_RUN"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"


LifecycleStatus: TypeAlias = LifecycleState | ProvenanceStatus


def deterministic_trace_id(kind: str, *parts: object) -> str:
    """Build a stable ID from explicit experiment coordinates, not time."""

    if not _ID_KIND.fullmatch(kind):
        raise ValueError("trace ID kind must use lowercase letters, digits, and hyphens")
    material = json.dumps([kind, *parts], ensure_ascii=False, separators=(",", ":"))
    return f"{kind}-{uuid5(NAMESPACE_URL, material)}"


class ProvenanceEvent(StrictModel):
    """One evidence-bounded relationship observed along the agentic pipeline."""

    event_id: NonEmptyText
    parent_event_id: NonEmptyText | None = None
    event_type: NonEmptyText
    source_record_id: str | None = None
    derived_record_id: str | None = None
    provider_record_id: str | None = None
    relation: ProvenanceRelation
    lifecycle_status: LifecycleStatus = ProvenanceStatus.UNKNOWN
    provenance_surface: MemorySurface = MemorySurface.UNKNOWN
    provenance_status: ProvenanceStatus = ProvenanceStatus.UNKNOWN
    timestamp: datetime

    @field_validator("timestamp")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return value

    @model_validator(mode="after")
    def missing_relation_is_explicit(self) -> Self:
        missing = {
            ProvenanceRelation.UNKNOWN: ProvenanceStatus.UNKNOWN,
            ProvenanceRelation.UNSUPPORTED: ProvenanceStatus.UNSUPPORTED,
            ProvenanceRelation.NOT_APPLICABLE: ProvenanceStatus.NOT_APPLICABLE,
        }
        expected = missing.get(self.relation)
        if expected is not None and self.provenance_status is not expected:
            raise ValueError(
                f"{self.relation.value} relation requires {expected.value} provenance"
            )
        if expected is None and self.provenance_status is not ProvenanceStatus.KNOWN:
            raise ValueError("a concrete provenance relation requires KNOWN provenance")
        return self


class RetrievalCandidate(StrictModel):
    """One normalized candidate returned by a provider retrieval surface."""

    candidate_id: NonEmptyText
    provider_memory_id: str | None = None
    sanitized_content: str | None = None
    score: float | None = None
    surface: MemorySurface = MemorySurface.RETRIEVAL
    source_event_ids: tuple[NonEmptyText, ...] = ()
    lifecycle_status: LifecycleStatus = ProvenanceStatus.UNKNOWN
    provenance_status: ProvenanceStatus = ProvenanceStatus.UNKNOWN
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def metadata_has_no_sensitive_keys(cls, value: dict[str, Any]) -> dict[str, Any]:
        return reject_sensitive_keys(value, field_name="metadata")


class EnforcementDecision(StrictModel):
    """A transparent pre-model decision for exactly one candidate."""

    decision_id: NonEmptyText
    enforcement_event_id: NonEmptyText
    candidate_id: NonEmptyText
    decision: EnforcementAction
    reason_code: NonEmptyText
    authoritative_status: LifecycleStatus = ProvenanceStatus.UNKNOWN
    rule_id: NonEmptyText
    provenance_basis: NonEmptyText
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def metadata_has_no_sensitive_keys(cls, value: dict[str, Any]) -> dict[str, Any]:
        return reject_sensitive_keys(value, field_name="metadata")


class FailureAttribution(StrictModel):
    """An evidence-backed attribution; an empty set means no claim was made."""

    origin: FailureOrigin
    evidence_event_ids: tuple[NonEmptyText, ...] = ()
    rationale: NonEmptyText


class ModelDecisionRecord(StrictModel):
    """Reserved downstream record. Phase 03B leaves it absent and NOT_RUN."""

    execution_status: DownstreamExecutionStatus = DownstreamExecutionStatus.NOT_RUN
    model_name: str | None = None
    model_endpoint_class: str | None = None
    prompt_template_version: str | None = None
    temperature: float | None = None
    delivered_candidate_ids: tuple[NonEmptyText, ...] = ()
    output: str | None = None
    parsed_decision: str | None = None
    latency_ms: float | None = Field(default=None, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)


class ToolActionRecord(StrictModel):
    """Reserved tool-consequence record; no real action runs in Phase 03B."""

    execution_status: DownstreamExecutionStatus = DownstreamExecutionStatus.NOT_RUN
    tool_name: str | None = None
    requested_action: str | None = None
    authorization_result: str | None = None
    executed: bool = False
    consequence_class: str | None = None


class RetrievalTrace(StrictModel):
    """Candidate-to-enforcement-to-delivery trace for one provider query."""

    retrieval_event_id: NonEmptyText
    lifecycle_event_id: NonEmptyText
    enforcement_event_id: NonEmptyText
    candidates: tuple[RetrievalCandidate, ...] = ()
    decisions: tuple[EnforcementDecision, ...] = ()
    delivered_candidate_ids: tuple[NonEmptyText, ...] = ()
    model_execution: DownstreamExecutionStatus = DownstreamExecutionStatus.NOT_RUN
    tool_execution: DownstreamExecutionStatus = DownstreamExecutionStatus.NOT_RUN
    model_decision: ModelDecisionRecord | None = None
    tool_action: ToolActionRecord | None = None
    timestamp: datetime

    @field_validator("timestamp")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return value

    @model_validator(mode="after")
    def candidate_flow_is_complete(self) -> Self:
        candidate_ids = [candidate.candidate_id for candidate in self.candidates]
        decision_ids = [decision.candidate_id for decision in self.decisions]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("candidate IDs must be unique")
        if len(decision_ids) != len(set(decision_ids)):
            raise ValueError("each candidate must have exactly one decision")
        if set(decision_ids) != set(candidate_ids):
            raise ValueError("decisions must cover every retrieval candidate")
        if any(
            decision.enforcement_event_id != self.enforcement_event_id
            for decision in self.decisions
        ):
            raise ValueError("decision enforcement_event_id must match the trace")
        expected_delivered = {
            decision.candidate_id
            for decision in self.decisions
            if decision.decision is not EnforcementAction.BLOCK
        }
        if set(self.delivered_candidate_ids) != expected_delivered:
            raise ValueError("delivered candidates must be exactly the non-blocked set")
        if self.model_execution is DownstreamExecutionStatus.NOT_RUN:
            if self.model_decision is not None:
                raise ValueError("NOT_RUN model execution cannot have a decision record")
        if self.tool_execution is DownstreamExecutionStatus.NOT_RUN:
            if self.tool_action is not None:
                raise ValueError("NOT_RUN tool execution cannot have an action record")
        return self


class ExperimentTrace(StrictModel):
    """Versioned companion to Phase 03 benchmark results."""

    trace_schema_version: str = TRACE_SCHEMA_VERSION
    experiment_id: NonEmptyText
    scenario_id: NonEmptyText
    provider: NonEmptyText
    lifecycle_events: tuple[ProvenanceEvent, ...]
    retrieval_traces: tuple[RetrievalTrace, ...] = ()
    failure_attributions: tuple[FailureAttribution, ...] = ()
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must include a timezone")
        return value

    @model_validator(mode="after")
    def trace_links_are_closed(self) -> Self:
        if self.trace_schema_version != TRACE_SCHEMA_VERSION:
            raise ValueError(
                f"trace_schema_version must be {TRACE_SCHEMA_VERSION!r}"
            )
        event_ids = [event.event_id for event in self.lifecycle_events]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("provenance event IDs must be unique")
        known_events = set(event_ids)
        for event in self.lifecycle_events:
            if event.parent_event_id is not None and event.parent_event_id not in known_events:
                raise ValueError("parent_event_id must reference an event in this trace")
        for retrieval in self.retrieval_traces:
            if retrieval.lifecycle_event_id not in known_events:
                raise ValueError("retrieval must reference a lifecycle event")
            for candidate in retrieval.candidates:
                if not set(candidate.source_event_ids).issubset(known_events):
                    raise ValueError("candidate source_event_ids must reference this trace")
        return self


def serialize_trace(trace: ExperimentTrace) -> str:
    """Serialize one trace with deterministic key ordering and UTF-8 text."""

    return json.dumps(
        trace.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        separators=(",", ": "),
    ) + "\n"


def deserialize_trace(value: str) -> ExperimentTrace:
    """Parse and validate a serialized trace document."""

    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise ValueError("experiment trace document must be a JSON object")
    return ExperimentTrace.model_validate(payload)
