"""Supplemental controls, separate from the frozen 48-row study.

These unregistered unit records never substitute for registered observations.
"""
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import socket
import subprocess

import pytest

from memlife.adapters.hindsight import HindsightMemoryAdapter
from memlife.adapters.reference import ReferenceMemoryAdapter
from memlife.models.authority import AuthorityLedger, AuthorityLedgerEntry, AuthorityExposureOutcome
from memlife.models.lifecycle import LifecycleState
from memlife.models.memory import MemoryRecord
from memlife.models.provenance import ProvenanceStatus
from memlife.next_lp01 import (NoTransport, StaticMem0TraceHooks, baseline_projection, query_observation, registration,
                              ARMS, PRODUCERS, analyze)
from memlife.r1.protocol import canonical, sha
from memlife.runner.provenance import ProvenanceTraceRunner
from memlife.runner.authority_correlation_v2 import (
    VERSION, HostAssociationSnapshot, correlate_record, storage_payload_v2, trace_payload_v2)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError("OFFLINE_SUPPLEMENTAL_CONTROL")
    for name in ("socket", "create_connection", "getaddrinfo"):
        monkeypatch.setattr(socket, name, denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    monkeypatch.setattr(os, "system", denied)


def case(*, derived=False, old=LifecycleState.SUPERSEDED):
    content = "Independent unit current proposition."
    current = AuthorityLedgerEntry(experiment_event_id="u-current", logical_fact_id="u-current-fact",
        namespace="unit-scope", sequence=2, lifecycle_state=LifecycleState.ACTIVE,
        authoritative=True, authority_reason="unit host", source_content_sha256=sha(content.encode()))
    previous = AuthorityLedgerEntry(experiment_event_id="u-old", logical_fact_id="u-old-fact",
        namespace="unit-scope", sequence=1, lifecycle_state=old, authoritative=False,
        authority_reason="unit host", source_content_sha256=sha(b"Previous source bytes"))
    ledger = AuthorityLedger(entries=(previous, current))
    if derived:
        adapter = HindsightMemoryAdapter(NoTransport())
        record = adapter._normalized_record("unit-scope", dict(id="u-child", text=content,
            fact_type="observation", source_memory_ids=["u-source-current", "u-source-old"]))
        rows = [dict(provider="unit-provider", namespace=record.namespace, record_id=record.memory_id,
            record_sha256=sha(record.content.encode()), source_native_id=s, event_id=e)
            for s, e in (("u-source-current", "u-current"), ("u-source-old", "u-old"))]
    else:
        adapter = StaticMem0TraceHooks()
        record = MemoryRecord(memory_id="u-direct", namespace="unit-scope", content=content,
                              metadata={}, state=LifecycleState.ACTIVE, revision=1)
        rows = [dict(provider="unit-provider", namespace=record.namespace, record_id=record.memory_id,
            record_sha256=sha(record.content.encode()), source_native_id=record.memory_id, event_id="u-current")]
    return adapter, record, ledger, rows


def snapshot(rows):
    data = canonical(dict(schema_version=VERSION, associations=rows))
    return HostAssociationSnapshot.from_host_bytes(data, expected_sha256=sha(data), artifact_id="UNIT_HOST_CUSTODY")


def score(adapter, record, ledger, rows, *, provider="unit-provider"):
    return storage_payload_v2(adapter=adapter, records=(record,), provider=provider, snapshot=snapshot(rows),
        phase="unit", run_id="unit", ledger=ledger, provider_events={})[1]


def test_registration_is_structural_only_and_unchanged():
    manifest, fixtures, oracle, ledger = registration()
    assert len(fixtures) == len(oracle) == 12 and manifest["evaluated_rows"] == 48
    assert len(manifest["original_source_sha256"]) == 14


def test_unknown_generic_provenance_does_not_destroy_attested_direct_identity():
    adapter, record, ledger, rows = case()
    result = score(adapter, record, ledger, rows)
    assert result.exposure is AuthorityExposureOutcome.AUTHORITATIVE_ONLY
    assert result.observations[0].complete
    assert result.candidates[0].provenance_status is ProvenanceStatus.UNKNOWN


@pytest.mark.parametrize("old", [LifecycleState.SUPERSEDED, LifecycleState.REVOKED, LifecycleState.DELETED])
def test_complete_current_mixed_ancestry_is_resolved_not_blanket_unknown(old):
    adapter, record, ledger, rows = case(derived=True, old=old)
    result = score(adapter, record, ledger, rows)
    assert result.exposure is AuthorityExposureOutcome.AUTHORITATIVE_AND_NONAUTHORITATIVE
    assert result.observations[0].complete
    # This is source exposure, not an RQ4 context/action permission.
    assert result.candidates[0].source_event_ids == ("u-current", "u-old")


def test_partial_ancestry_remains_explicit_and_unknown():
    adapter, record, ledger, rows = case(derived=True)
    result = score(adapter, record, ledger, rows[:1])
    assert result.exposure is AuthorityExposureOutcome.UNKNOWN_PROVENANCE
    assert result.observations[0].unresolved_source_ids == ("u-source-old",)
    assert result.observations[0].resolved == (("u-source-current", "u-current"),)
    assert not result.observations[0].complete


def test_record_metadata_cannot_self_issue_identity_or_completeness():
    adapter, record, ledger, rows = case()
    record = record.model_copy(update={"metadata": {"source_event_id": "u-current",
        "authority_correlation_v2": {"complete": True}, "host_artifact_sha256": "a"*64}})
    assert score(adapter, record, ledger, []).exposure is AuthorityExposureOutcome.UNKNOWN_PROVENANCE


@pytest.mark.parametrize("key,value", [("provider", "other"), ("namespace", "other"),
                                      ("record_id", "other"), ("record_sha256", "0"*64),
                                      ("source_native_id", "other"), ("event_id", "missing")])
def test_scope_bytes_and_unresolved_host_event_cannot_be_borrowed(key, value):
    adapter, record, ledger, rows = case()
    rows[0][key] = value
    assert score(adapter, record, ledger, rows).exposure is AuthorityExposureOutcome.UNKNOWN_PROVENANCE


@pytest.mark.parametrize("conflict", [False, True])
def test_duplicate_or_conflicting_scoped_associations_do_not_choose_a_winner(conflict):
    adapter, record, ledger, rows = case()
    rows.append({**rows[0], "event_id": "u-old" if conflict else "u-current"})
    assert score(adapter, record, ledger, rows).exposure is AuthorityExposureOutcome.UNKNOWN_PROVENANCE


def test_host_source_set_disagreement_is_preserved():
    adapter, record, ledger, rows = case(derived=True)
    rows.append({**rows[0], "source_native_id": "u-hidden-host-source"})
    result = score(adapter, record, ledger, rows)
    assert not result.observations[0].complete
    assert "HOST_NATIVE_SOURCESET_DISAGREEMENT" in result.observations[0].reasons


def test_direct_source_digest_must_match_registered_direct_ledger_identity():
    adapter, record, ledger, rows = case()
    changed = record.model_copy(update={"content": "Altered unit bytes."})
    rows[0]["record_sha256"] = sha(changed.content.encode())
    result = score(adapter, changed, ledger, rows)
    assert result.exposure is AuthorityExposureOutcome.UNKNOWN_PROVENANCE
    assert "DIRECT_SOURCE_CONTENT_MISMATCH" in result.observations[0].reasons


def test_derived_child_digest_need_not_equal_parent_digest():
    adapter, record, ledger, rows = case(derived=True)
    assert rows[1]["record_sha256"] != ledger.by_event_id()["u-old"].source_content_sha256
    assert score(adapter, record, ledger, rows).observations[0].complete


def test_host_artifact_drift_and_duplicate_json_keys_reject():
    data = canonical(dict(schema_version=VERSION, associations=[]))
    with pytest.raises(ValueError, match="CUSTODY_DRIFT"):
        HostAssociationSnapshot.from_host_bytes(data+b" ", expected_sha256=sha(data), artifact_id="host")
    duplicate = b'{"schema_version":"x","schema_version":"y","associations":[]}'
    with pytest.raises(ValueError, match="DUPLICATE_HOST_JSON"):
        HostAssociationSnapshot.from_host_bytes(duplicate, expected_sha256=sha(duplicate), artifact_id="host")


def test_association_order_does_not_change_source_order_or_mutate_record():
    adapter, record, ledger, rows = case(derived=True)
    before = record.model_dump_json()
    first, reverse = score(adapter, record, ledger, rows), score(adapter, record, ledger, rows[::-1])
    assert first.exposure == reverse.exposure and first.candidates[0].source_event_ids == reverse.candidates[0].source_event_ids
    assert before == record.model_dump_json()


def test_actual_trace_and_storage_v2_paths_agree_on_host_correlation():
    adapter, record, ledger, rows = case(derived=True)
    scenario, observation = query_observation(record, "unit-provider")
    trace, _, result = trace_payload_v2(runner=ProvenanceTraceRunner(adapter), experiment_id="unit",
        scenario=scenario, observation=observation, lifecycle_event_id="unit-query", provider_event_ids={},
        provider="unit-provider", snapshot=snapshot(rows), ledger=ledger)
    assert result.exposure == score(adapter, record, ledger, rows).exposure
    assert trace.candidates == result.candidates
    assert trace.model_execution.value == trace.tool_execution.value == "NOT_RUN"


def test_empty_input_is_none_not_unknown():
    adapter, record, ledger, rows = case()
    _, result = storage_payload_v2(adapter=adapter, records=(), provider="unit-provider", snapshot=snapshot([]),
        phase="unit", run_id="unit", ledger=ledger, provider_events={})
    assert result.exposure is AuthorityExposureOutcome.NONE


def test_baseline_projection_conflicts_are_symmetrical():
    _, _, _, rows = case()
    rows.append({**rows[0], "event_id": "u-old"})
    storage, trace, conflicts = baseline_projection(rows)
    assert storage == trace == {} and conflicts == ["u-direct"]


def test_missing_row_denominator_is_never_silently_reduced():
    with pytest.raises(ValueError, match="48_REGISTERED"):
        analyze([], {})


def test_offline_guards_reject_network_and_process():
    with pytest.raises(PermissionError):
        socket.create_connection(("127.0.0.1", 1))
    with pytest.raises(PermissionError):
        subprocess.run(["true"])
