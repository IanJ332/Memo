"""Validation and deterministic serialization for provenance trace models."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from memlife.models.provenance import (
    DownstreamExecutionStatus,
    ExperimentTrace,
    FailureAttribution,
    FailureOrigin,
    MemorySurface,
    ProvenanceEvent,
    ProvenanceRelation,
    ProvenanceStatus,
    RetrievalCandidate,
    deserialize_trace,
    deterministic_trace_id,
    serialize_trace,
)

FIXED_TIME = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)


def _unknown_event(**updates: object) -> ProvenanceEvent:
    values: dict[str, object] = {
        "event_id": "event-1",
        "event_type": "WRITE",
        "relation": ProvenanceRelation.UNKNOWN,
        "lifecycle_status": ProvenanceStatus.UNKNOWN,
        "provenance_surface": MemorySurface.UNKNOWN,
        "provenance_status": ProvenanceStatus.UNKNOWN,
        "timestamp": FIXED_TIME,
    }
    values.update(updates)
    return ProvenanceEvent.model_validate(values)


def test_provenance_model_requires_explicit_unknown_and_aware_time() -> None:
    event = _unknown_event()
    assert event.relation is ProvenanceRelation.UNKNOWN
    assert event.provenance_status is ProvenanceStatus.UNKNOWN

    with pytest.raises(ValidationError, match="UNKNOWN relation requires UNKNOWN"):
        _unknown_event(provenance_status=ProvenanceStatus.KNOWN)
    with pytest.raises(ValidationError, match="timestamp must include a timezone"):
        _unknown_event(timestamp=datetime(2026, 9, 28, 12, 0))


def test_stable_event_ids_depend_on_explicit_correlation_coordinates() -> None:
    first = deterministic_trace_id("lifecycle", "run-7", "scenario", 2)
    assert first == deterministic_trace_id("lifecycle", "run-7", "scenario", 2)
    assert first != deterministic_trace_id("lifecycle", "run-8", "scenario", 2)


def test_memory_surfaces_and_failure_taxonomy_serialize_by_value() -> None:
    event = _unknown_event(provenance_surface=MemorySurface.PROFILE)
    attribution = FailureAttribution(
        origin=FailureOrigin.DERIVED_STATE,
        evidence_event_ids=(event.event_id,),
        rationale="Synthetic validation fixture only.",
    )
    trace = ExperimentTrace(
        experiment_id="taxonomy-test",
        scenario_id="fixture",
        provider="reference-in-memory",
        lifecycle_events=(event,),
        failure_attributions=(attribution,),
        created_at=FIXED_TIME,
    )
    payload = trace.model_dump(mode="json")
    assert payload["lifecycle_events"][0]["provenance_surface"] == "PROFILE"
    assert payload["failure_attributions"][0]["origin"] == "DERIVED_STATE"
    assert set(item.value for item in FailureOrigin) == {
        "SOURCE_LIFECYCLE",
        "DERIVED_STATE",
        "RETRIEVAL",
        "ENFORCEMENT",
        "MODEL",
        "TOOL_AUTHORIZATION",
        "UNKNOWN",
    }


def test_retrieval_candidate_serialization_and_sensitive_metadata_rejection() -> None:
    candidate = RetrievalCandidate(
        candidate_id="candidate-1",
        provider_memory_id="memory-1",
        sanitized_content="Safe synthetic fixture.",
        score=0.75,
        surface=MemorySurface.RETRIEVAL,
        source_event_ids=("event-1",),
        provenance_status=ProvenanceStatus.UNKNOWN,
        metadata={"nested": {"revision": 2}},
    )
    payload = candidate.model_dump(mode="json")
    assert payload["surface"] == "RETRIEVAL"
    assert payload["provenance_status"] == "UNKNOWN"

    with pytest.raises(ValidationError, match="sensitive key"):
        RetrievalCandidate.model_validate(
            {**payload, "metadata": {"access_token": "forbidden"}}
        )


def test_trace_json_is_deterministic_and_round_trips() -> None:
    event = _unknown_event()
    trace = ExperimentTrace(
        experiment_id="round-trip",
        scenario_id="fixture",
        provider="reference-in-memory",
        lifecycle_events=(event,),
        created_at=FIXED_TIME,
    )
    first = serialize_trace(trace)
    assert first == serialize_trace(trace)
    assert deserialize_trace(first) == trace
    assert '"trace_schema_version": "0.1"' in first
    assert DownstreamExecutionStatus.NOT_RUN.value == "NOT_RUN"
