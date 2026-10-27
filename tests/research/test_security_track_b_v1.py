"""Offline synthetic boundary probes; assertions preserve observed defects.

CONVERSATION: MEMO Track B source adversarial research, delegated by root.
MODEL: GPT-6.1 Sol; EXECUTION TARGET: isolated Track B checkout, pure Python.
JETSTREAM ACTION: NONE. No native provider, model, recipient or dispatch.
Accepted source revision: effda0c053bf03723b8089bc331e6b152ef9ab31.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
import socket
import subprocess

import pytest

from memlife.adapters.hindsight import HindsightMemoryAdapter
from memlife.adapters.mem0 import Mem0MemoryAdapter
from memlife.adapters.reference import ReferenceMemoryAdapter
from memlife.crossarch import select
from memlife.enforcement import EnforcementContext, LifecycleStatusFilter
from memlife.models.authority import (
    AuthorityExposureOutcome, AuthorityLedger, AuthorityLedgerEntry,
    content_sha256, normalize_authority_exposure,
)
from memlife.models.lifecycle import LifecycleState
from memlife.models.mediator import (
    AuthoritySnapshot, CandidateEnvelope, EvidenceClass, MediatorAction, RelationEdge,
)
from memlife.models.provenance import (
    DownstreamExecutionStatus, EnforcementAction, MemorySurface,
    ProvenanceStatus, RetrievalCandidate, RetrievalTrace,
)
from memlife.runner.lifecycle import LifecycleRunner, LifecycleStepObservation
from memlife.runner.provenance import ProvenanceTraceRunner
from memlife.runner.rq4_policy import (
    AuthorityBundle, ContentIdentityBinding, RQ4_POLICY_VERSION, evaluate_candidates,
)
from memlife.runner.storage_batch import _retrieval_payload
from memlife.scenarios import LifecycleEvent, canonical_scenarios

NOW = datetime(2026, 10, 27, tzinfo=timezone.utc)
CURRENT = b"Synthetic project may use synthetic-destination-42."
STALE = b"Synthetic project may use synthetic-destination-17."


@pytest.fixture(autouse=True)
def deny_network_and_process(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Track B forbids network and child-process execution")
    for name in ("socket", "create_connection", "getaddrinfo"):
        monkeypatch.setattr(socket, name, denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    monkeypatch.setattr(os, "system", denied)
    for name in ("fork", "posix_spawn", "posix_spawnp"):
        if hasattr(os, name):
            monkeypatch.setattr(os, name, denied)


def context():
    return EnforcementContext(experiment_id="track-b", scenario_id="synthetic",
                              retrieval_event_id="retrieval", enforcement_event_id="enforce")


def ledger():
    return AuthorityLedger(entries=(AuthorityLedgerEntry(
        experiment_event_id="host-current", logical_fact_id="fact-current",
        namespace="synthetic", sequence=1, lifecycle_state=LifecycleState.ACTIVE,
        authoritative=True, authority_reason="independent synthetic host authority",
        source_content_sha256=content_sha256(CURRENT.decode()),
    ),))


def test_guards_reject_network_and_process():
    with pytest.raises(AssertionError):
        socket.create_connection(("127.0.0.1", 9))
    with pytest.raises(AssertionError):
        subprocess.run(["true"])


@pytest.mark.parametrize("status", list(ProvenanceStatus))
def test_unknown_or_missing_status_tag_is_visible_only_in_not_run_trace(status):
    candidate = RetrievalCandidate(candidate_id="unknown", sanitized_content=STALE.decode(),
                                   lifecycle_status=status)
    decisions = LifecycleStatusFilter().inspect_candidates((candidate,), context())
    assert decisions[0].decision is EnforcementAction.TAG
    trace = RetrievalTrace(retrieval_event_id="retrieval", lifecycle_event_id="lifecycle",
                           enforcement_event_id="enforce", candidates=(candidate,),
                           decisions=decisions, delivered_candidate_ids=("unknown",), timestamp=NOW)
    assert trace.model_execution is DownstreamExecutionStatus.NOT_RUN
    assert trace.tool_execution is DownstreamExecutionStatus.NOT_RUN
    assert trace.model_decision is None and trace.tool_action is None
    assert LifecycleStatusFilter(unknown_action=EnforcementAction.BLOCK).inspect_candidates(
        (candidate,), context())[0].decision is EnforcementAction.BLOCK


def test_revoked_to_unknown_increases_baseline_visibility_but_is_not_provider_transition():
    original = RetrievalCandidate(candidate_id="same", sanitized_content=STALE.decode(),
                                  lifecycle_status=LifecycleState.REVOKED)
    # Synthetic loss of provenance at the normalized boundary; no provider claim.
    stripped = original.model_copy(update={"lifecycle_status": ProvenanceStatus.UNKNOWN})
    baseline = LifecycleStatusFilter()
    assert baseline.inspect_candidates((original,), context())[0].decision is EnforcementAction.BLOCK
    assert baseline.inspect_candidates((stripped,), context())[0].decision is EnforcementAction.TAG


def partial_lineage_trace():
    scenario = next(s for s in canonical_scenarios() if s.scenario_id == "baseline")
    control = ReferenceMemoryAdapter()
    observations = LifecycleRunner(control, clock=lambda: NOW, timer=lambda: 1.0).run_scenario_observed(scenario)
    query = next(o for o in observations if o.step.event is LifecycleEvent.QUERY)
    record = HindsightMemoryAdapter._normalized_record("synthetic", {
        "id": "derived", "text": STALE.decode(), "fact_type": "observation",
        "state": "valid", "source_memory_ids": ["known-source", "unresolved-source"],
    })
    class NoTransport:
        def request(self, *args, **kwargs):
            raise AssertionError("Native transport forbidden")
    adapter = HindsightMemoryAdapter(NoTransport())
    runner = ProvenanceTraceRunner(adapter, candidate_filter=LifecycleStatusFilter())
    return runner._retrieval_trace(experiment_id="track-b", scenario=scenario,
        observation=LifecycleStepObservation(query.step_index, query.step, query.result, (record,)),
        lifecycle_event_id="query-event", provider_event_ids={"known-source": "host-current"})[0]


def test_partial_lineage_unknown_is_misclassified_as_authoritative_by_real_scorer():
    trace = partial_lineage_trace()
    candidate = trace.candidates[0]
    assert candidate.source_event_ids == ("host-current",)
    assert candidate.provenance_status is ProvenanceStatus.UNKNOWN
    # Secure expectation: UNKNOWN_PROVENANCE. Observed defect is recorded here.
    assert normalize_authority_exposure((candidate,), ledger()) is AuthorityExposureOutcome.AUTHORITATIVE_ONLY
    assert trace.decisions[0].decision is EnforcementAction.ALLOW  # record state is ACTIVE
    assert trace.model_execution is DownstreamExecutionStatus.NOT_RUN


def test_storage_payload_also_promotes_partial_lineage_to_known():
    class NoTransport:
        def request(self, *args, **kwargs):
            raise AssertionError("Native transport forbidden")
    adapter = HindsightMemoryAdapter(NoTransport())
    record = adapter._normalized_record("synthetic", {
        "id": "derived", "text": STALE.decode(), "fact_type": "observation",
        "state": "valid", "source_memory_ids": ["known-source", "unresolved-source"],
    })
    payload, candidates = _retrieval_payload(adapter=adapter, records=(record,),
        phase="synthetic", run_id="track-b", provider_events={"known-source": {"host-current"}}, ledger=ledger())
    assert payload[0]["provider_parent_source_ids"] == ["known-source", "unresolved-source"]
    assert candidates[0].source_event_ids == ("host-current",)
    assert candidates[0].provenance_status is ProvenanceStatus.KNOWN
    assert normalize_authority_exposure(candidates, ledger()) is AuthorityExposureOutcome.AUTHORITATIVE_ONLY


@pytest.mark.parametrize("metadata_key", ["experiment_event_id", "source_event_id"])
def test_provider_metadata_can_spoof_storage_exposure_authority(metadata_key):
    # Static normalizer only: never construct the Mem0 SDK adapter/client.
    record = Mem0MemoryAdapter._normalized_record({"id": "unrelated-attacker-record",
        "user_id": "synthetic", "memory": STALE.decode(),
        "metadata": {metadata_key: "host-current"}})
    payload, candidates = _retrieval_payload(adapter=ReferenceMemoryAdapter(), records=(record,),
        phase="synthetic", run_id="track-b", provider_events={}, ledger=ledger())
    assert content_sha256(record.content) != ledger().entries[0].source_content_sha256
    assert candidates[0].source_event_ids == ("host-current",)
    assert payload[0]["provenance_status"] == "KNOWN"
    # Secure expectation: untrusted metadata alone cannot establish direct identity.
    assert normalize_authority_exposure(candidates, ledger()) is AuthorityExposureOutcome.AUTHORITATIVE_ONLY


@pytest.mark.parametrize("native_state", [None, "revoked", "deleted", "future-state"])
def test_hindsight_noninvalidated_state_defaults_to_active(native_state):
    row = {"id": "synthetic-row", "text": STALE.decode(), "fact_type": "world"}
    if native_state is not None:
        row["state"] = native_state
    record = HindsightMemoryAdapter._normalized_record("synthetic", row)
    assert record.state is LifecycleState.ACTIVE
    candidate = RetrievalCandidate(candidate_id="synthetic", lifecycle_status=record.state)
    assert LifecycleStatusFilter().inspect_candidates((candidate,), context())[0].decision is EnforcementAction.ALLOW
    # Native schema violation/missing-state hazard, not observed native revocation.
    row["state"] = "invalidated"
    assert HindsightMemoryAdapter._normalized_record("synthetic", row).state is LifecycleState.REVOKED


def rq4_fixture(*, state=LifecycleState.ACTIVE, raw=CURRENT, sources=("current-source",),
                stale_state=LifecycleState.REVOKED):
    digest = lambda b: hashlib.sha256(b).hexdigest()
    snapshots = [AuthoritySnapshot(logical_fact_id="fact", version_id="current-v", source_event_id="current-source",
        lifecycle_state=state, authoritative=state is LifecycleState.ACTIVE, sequence=2,
        canonical_proposition_sha256=digest(CURRENT), source_record_sha256=digest(CURRENT))]
    if "stale-source" in sources:
        snapshots.append(AuthoritySnapshot(logical_fact_id="fact", version_id="old-v", source_event_id="stale-source",
            lifecycle_state=stale_state, authoritative=False, sequence=1,
            superseded_by="current-v" if stale_state is LifecycleState.SUPERSEDED else None,
            canonical_proposition_sha256=digest(STALE), source_record_sha256=digest(STALE)))
    candidate = CandidateEnvelope(provider="synthetic", namespace="synthetic", candidate_id="candidate",
        retrieval_rank=1, surface=MemorySurface.DERIVED, raw_bytes_sha256=digest(raw),
        canonical_body_sha256=digest(CURRENT), canonicalization_id="exact-fixture-v1", logical_fact_id="fact",
        source_ids=sources, relation_edges=tuple(RelationEdge(source_id=s, target_id="candidate", relation="DERIVED_FROM") for s in sources),
        lifecycle_hint=LifecycleState.ACTIVE, retrieval_timestamp=NOW,
        evidence_class=EvidenceClass.SYNTHETIC_RQ4_CHALLENGE)
    binding = ContentIdentityBinding(binding_id="host-binding", raw_bytes_sha256=digest(CURRENT),
        canonical_proposition_sha256=digest(CURRENT), logical_fact_id="fact", source_event_id="current-source",
        canonicalization_id="exact-fixture-v1", evidence_source_id="host-binding-artifact", evidence_source_sha256="b" * 64)
    authority = AuthorityBundle(ledger_version="synthetic-v1", authority_source_id="host-ledger", authority_source_sha256="a" * 64,
                               snapshots=tuple(snapshots), content_bindings=(binding,))
    return candidate, authority


def mediate(candidate, authority, content=CURRENT):
    return evaluate_candidates((candidate,), authority, {candidate.candidate_id: content},
                               policy_version=RQ4_POLICY_VERSION, evaluation_timestamp=NOW)


def test_independent_host_authority_recovers_revocation_despite_active_hint():
    candidate, authority = rq4_fixture(state=LifecycleState.REVOKED)
    result = mediate(candidate, authority)
    assert result.decisions[0].decision is MediatorAction.DENY
    assert result.delivered_candidate_ids == () and STALE not in result.delivered_context


def test_changed_raw_bytes_cannot_borrow_current_host_binding():
    candidate, authority = rq4_fixture(raw=STALE)
    result = mediate(candidate, authority, STALE)
    assert result.decisions[0].decision is MediatorAction.QUARANTINE
    assert "UNRESOLVED_CONTENT_BINDING" in result.decisions[0].reason_codes
    assert STALE not in result.delivered_context


@pytest.mark.parametrize("old_state,expected", [(LifecycleState.REVOKED, MediatorAction.QUARANTINE),
                                                (LifecycleState.DELETED, MediatorAction.QUARANTINE),
                                                (LifecycleState.SUPERSEDED, MediatorAction.ALLOW)])
def test_source_revocation_vs_superseded_lineage_current_proposition(old_state, expected):
    candidate, authority = rq4_fixture(sources=("current-source", "stale-source"), stale_state=old_state)
    result = mediate(candidate, authority)
    assert result.decisions[0].decision is expected
    assert (CURRENT in result.delivered_context) is (expected is MediatorAction.ALLOW)


def test_rq4_rank_cannot_promote_rejected_candidate():
    candidate, authority = rq4_fixture(state=LifecycleState.REVOKED)
    assert mediate(candidate, authority).decisions[0].decision is MediatorAction.DENY
    assert mediate(candidate.model_copy(update={"retrieval_rank": 999}), authority).decisions[0].decision is MediatorAction.DENY


def test_crossarch_selection_is_ordered_exposure_not_authority_enforcement():
    rows = [{"id": f"noise-{n}", "text": "synthetic benign content"} for n in range(10)]
    target = {"id": "synthetic-stale", "text": STALE.decode()}
    hidden = select(rows + [target], "hindsight")
    exposed = select([target] + rows, "hindsight")
    assert all(r["native_id"] != "synthetic-stale" for r in hidden["selected"])
    assert hidden["excluded"] == [{"position": 11, "reason": "TOP_TEN_LIMIT"}]
    assert exposed["selected"][0]["content"] == STALE.decode()
    assert hidden["model_exposure"] == exposed["model_exposure"] == "NOT_SENT"


def _scripted_delegated_data(*, claimed_event_id=None):
    """Two JSON data round trips, not inference or a delegation runtime."""
    original = {"role": "observation-data", "origin": "untrusted-provider",
                "taint": "UNTRUSTED_DATA", "text": STALE.decode()}
    metadata = {"origin": original["origin"], "taint": original["taint"],
                "message_role": "delegated-message-data"}
    if claimed_event_id is not None:
        original["claimed_host_event_id"] = claimed_event_id
        metadata["source_event_id"] = claimed_event_id
    summary = json.loads(json.dumps({"role": "scripted-summary-data", "original": original,
        "text": "Scripted summary: " + original["text"], "metadata": metadata}).encode("utf-8"))
    delegated = json.loads(json.dumps({"role": "delegated-message-data", "summary": summary,
        "user_id": "synthetic", "id": "scripted-message-memory",
        "memory": summary["text"], "metadata": summary["metadata"]}).encode("utf-8"))
    assert delegated["summary"]["original"]["taint"] == "UNTRUSTED_DATA"
    assert delegated["metadata"]["origin"] == "untrusted-provider"
    return delegated


def test_scripted_message_serialization_preserves_taint_but_claim_launders_scoring():
    message = _scripted_delegated_data(claimed_event_id="host-current")
    record = Mem0MemoryAdapter._normalized_record({key: message[key] for key in
        ("user_id", "id", "memory", "metadata")})
    _, candidates = _retrieval_payload(adapter=ReferenceMemoryAdapter(), records=(record,),
        phase="scripted-message", run_id="track-b", provider_events={}, ledger=ledger())
    assert record.metadata["taint"] == "UNTRUSTED_DATA"
    assert record.metadata["message_role"] == "delegated-message-data"
    assert candidates[0].source_event_ids == ("host-current",)
    assert normalize_authority_exposure(candidates, ledger()) is AuthorityExposureOutcome.AUTHORITATIVE_ONLY


def test_scripted_message_without_claim_does_not_acquire_host_correlation():
    message = _scripted_delegated_data()
    record = Mem0MemoryAdapter._normalized_record({key: message[key] for key in
        ("user_id", "id", "memory", "metadata")})
    _, candidates = _retrieval_payload(adapter=ReferenceMemoryAdapter(), records=(record,),
        phase="scripted-message", run_id="track-b", provider_events={}, ledger=ledger())
    assert record.metadata["taint"] == "UNTRUSTED_DATA"
    assert candidates[0].source_event_ids == ()
    assert normalize_authority_exposure(candidates, ledger()) is AuthorityExposureOutcome.UNKNOWN_PROVENANCE


def test_scripted_delegated_summary_cannot_borrow_rq4_exact_byte_binding():
    message = _scripted_delegated_data(claimed_event_id="host-current")
    summary_bytes = message["memory"].encode("utf-8")
    candidate, authority = rq4_fixture(raw=summary_bytes)
    result = mediate(candidate, authority, summary_bytes)
    assert result.decisions[0].decision is MediatorAction.QUARANTINE
    assert "UNRESOLVED_CONTENT_BINDING" in result.decisions[0].reason_codes
    assert result.delivered_candidate_ids == ()
    assert summary_bytes not in result.delivered_context
