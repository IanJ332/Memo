"""Opt-in source-exposure repair; original experiment scorers stay immutable.

The host caller supplies provider scope and an independently hash-pinned
association artifact. Its trusted custody is a prerequisite, not something a
provider metadata field, Python type or self-supplied hash can establish.
This module classifies source exposure; it does not authorize an action or
decide whether a derived current proposition is semantically valid.
"""
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Iterable

from memlife.models.authority import AuthorityLedger, AuthorityExposureOutcome, normalize_authority_exposure
from memlife.models.memory import MemoryRecord, NonEmptyText, StrictModel
from memlife.models.provenance import ProvenanceStatus, RetrievalCandidate, RetrievalTrace

VERSION = "HOST_ASSOCIATION_COMPLETENESS_V2"


def _need(value, reason):
    if not value:
        raise ValueError(reason)


class HostAssociation(StrictModel):
    provider: NonEmptyText
    namespace: NonEmptyText
    record_id: NonEmptyText
    record_sha256: NonEmptyText
    source_native_id: NonEmptyText
    event_id: NonEmptyText


@dataclass(frozen=True)
class HostAssociationSnapshot:
    artifact_id: str
    sha256: str
    associations: tuple[HostAssociation, ...]

    @classmethod
    def from_host_bytes(cls, data: bytes, *, expected_sha256: str, artifact_id: str):
        """Verify exact custody bytes; expected identity must come from the host.

        This deliberately cannot authenticate an arbitrary caller or artifact.
        Do not obtain expected_sha256/artifact_id from retrieved memory.
        """
        digest = hashlib.sha256(data).hexdigest()
        _need(type(expected_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", expected_sha256)
              and digest == expected_sha256, "HOST_ASSOCIATION_CUSTODY_DRIFT")
        _need(type(artifact_id) is str and bool(artifact_id.strip()), "HOST_CUSTODY_ID_REQUIRED")

        def pairs(items):
            result = {}
            for key, value in items:
                _need(key not in result, "DUPLICATE_HOST_JSON_KEY")
                result[key] = value
            return result

        body = json.loads(data, object_pairs_hook=pairs)
        _need(type(body) is dict and set(body) == {"schema_version", "associations"}
              and body["schema_version"] == VERSION and type(body["associations"]) is list,
              "HOST_ASSOCIATION_SCHEMA")
        rows = tuple(HostAssociation.model_validate(row) for row in body["associations"])
        _need(all(re.fullmatch(r"[0-9a-f]{64}", row.record_sha256) for row in rows), "HOST_RECORD_DIGEST")
        return cls(artifact_id, digest, rows)


@dataclass(frozen=True)
class CorrelationObservation:
    expected_source_ids: tuple[str, ...]
    resolved: tuple[tuple[str, str], ...]
    unresolved_source_ids: tuple[str, ...]
    complete: bool
    reasons: tuple[str, ...]
    generic_provenance_status: str
    host_artifact_id: str
    host_artifact_sha256: str

    @property
    def event_ids(self):
        return tuple(dict.fromkeys(event for _, event in self.resolved))

    def as_dict(self):
        return dict(version=VERSION, expected_source_ids=list(self.expected_source_ids),
                    resolved=[dict(source_native_id=s, event_id=e) for s, e in self.resolved],
                    unresolved_source_ids=list(self.unresolved_source_ids), complete=self.complete,
                    reasons=list(self.reasons), generic_provenance_status=self.generic_provenance_status,
                    host_artifact_id=self.host_artifact_id, host_artifact_sha256=self.host_artifact_sha256)


@dataclass(frozen=True)
class ExposureV2:
    exposure: AuthorityExposureOutcome
    candidates: tuple[RetrievalCandidate, ...]
    observations: tuple[CorrelationObservation, ...]


def correlate_record(adapter, record: MemoryRecord, *, provider: str,
                     snapshot: HostAssociationSnapshot, ledger: AuthorityLedger):
    """Retain every exposed coordinate and reject untrusted identity substitution."""
    _need(type(snapshot) is HostAssociationSnapshot and type(provider) is str and provider.strip(),
          "TRUSTED_HOST_SNAPSHOT_AND_PROVIDER_REQUIRED")
    exposed = tuple(adapter.trace_source_provider_ids_for(record))
    expected = exposed or (record.memory_id,)
    reasons, resolved, unresolved = [], [], []
    if len(set(expected)) != len(expected):
        reasons.append("DUPLICATE_EXPOSED_SOURCE")
    digest = hashlib.sha256(record.content.encode()).hexdigest()
    exact = tuple(row for row in snapshot.associations if
                  (row.provider, row.namespace, row.record_id, row.record_sha256) ==
                  (provider, record.namespace, record.memory_id, digest))
    if not exact:
        reasons.append("NO_SCOPE_AND_BYTE_BOUND_HOST_ASSOCIATION")
    if exact and set(row.source_native_id for row in exact) != set(expected):
        reasons.append("HOST_NATIVE_SOURCESET_DISAGREEMENT")
    events = ledger.by_event_id()
    for source in expected:
        matches = [row for row in exact if row.source_native_id == source]
        if len(matches) != 1:
            unresolved.append(source)
            reasons.append("MISSING_OR_AMBIGUOUS_SOURCE_ASSOCIATION")
            continue
        event = events.get(matches[0].event_id)
        if event is None or event.namespace != record.namespace:
            unresolved.append(source)
            reasons.append("UNKNOWN_OR_WRONG_SCOPE_HOST_EVENT")
            continue
        if not exposed and event.source_content_sha256 != digest:
            unresolved.append(source)
            reasons.append("DIRECT_SOURCE_CONTENT_MISMATCH")
            continue
        resolved.append((source, event.experiment_event_id))
    return CorrelationObservation(expected, tuple(resolved), tuple(unresolved),
                                  not reasons and not unresolved,
                                  tuple(dict.fromkeys(reasons)),
                                  adapter.trace_provenance_status_for(record).value,
                                  snapshot.artifact_id, snapshot.sha256)


def _score(adapter, records, candidates, *, provider, snapshot, ledger):
    records, candidates = tuple(records), tuple(candidates)
    _need(len(records) == len(candidates), "V2_RECORD_CANDIDATE_CARDINALITY")
    observations, projected = [], []
    for record, candidate in zip(records, candidates):
        _need(record.memory_id == candidate.provider_memory_id, "V2_RECORD_CANDIDATE_ID")
        correlation = correlate_record(adapter, record, provider=provider, snapshot=snapshot, ledger=ledger)
        observations.append(correlation)
        metadata = dict(candidate.metadata)
        # Diagnostic output only. The scorer never reads this metadata to decide
        # trust/completeness; it recomputes from records and host custody above.
        metadata["authority_correlation_v2"] = correlation.as_dict()
        projected.append(candidate.model_copy(update=dict(
            source_event_ids=correlation.event_ids,
            provenance_status=ProvenanceStatus(correlation.generic_provenance_status), metadata=metadata)))
    outcome = (normalize_authority_exposure(projected, ledger)
               if all(row.complete for row in observations) else AuthorityExposureOutcome.UNKNOWN_PROVENANCE)
    return ExposureV2(outcome, tuple(projected), tuple(observations))


def storage_payload_v2(*, adapter, records: Iterable[MemoryRecord], provider: str,
                       snapshot: HostAssociationSnapshot, phase: str, run_id: str,
                       ledger: AuthorityLedger, provider_events):
    """Use the real storage producer, then replace only its correlation projection."""
    from memlife.runner.storage_batch import _retrieval_payload
    records = tuple(records)
    payload, candidates = _retrieval_payload(adapter=adapter, records=records, phase=phase,
            run_id=run_id, provider_events=provider_events, ledger=ledger)
    score = _score(adapter, records, candidates, provider=provider, snapshot=snapshot, ledger=ledger)
    corrected = [dict(row, source_event_ids=list(candidate.source_event_ids),
                      provenance_status=candidate.provenance_status.value,
                      authority_correlation_v2=correlation.as_dict())
                 for row, candidate, correlation in zip(payload, score.candidates, score.observations)]
    return corrected, score


def trace_payload_v2(*, runner, experiment_id, scenario, observation,
                     lifecycle_event_id, provider_event_ids, provider: str,
                     snapshot: HostAssociationSnapshot, ledger: AuthorityLedger):
    """Use the real trace producer; no native query, model or dispatcher is added."""
    trace, events = runner._retrieval_trace(experiment_id=experiment_id, scenario=scenario,
        observation=observation, lifecycle_event_id=lifecycle_event_id, provider_event_ids=provider_event_ids)
    score = _score(runner.adapter, observation.records, trace.candidates,
                   provider=provider, snapshot=snapshot, ledger=ledger)
    body = trace.model_dump()
    body["candidates"] = score.candidates
    return RetrievalTrace.model_validate(body), events, score
