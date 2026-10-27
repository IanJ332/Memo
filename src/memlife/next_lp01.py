"""Frozen 48-row NEXT-LP-01 evaluator; no native provider or model execution."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
from pathlib import Path
import sys

from memlife.r1.protocol import canonical, identity, need, raw, save, sha, strict
from memlife.models.authority import AuthorityLedger, AuthorityExposureOutcome, normalize_authority_exposure
from memlife.models.benchmark import BenchmarkResult, OperationStatus
from memlife.models.memory import MemoryRecord
from memlife.models.provenance import ProvenanceStatus
from memlife.adapters.hindsight import HindsightMemoryAdapter
from memlife.adapters.mem0 import Mem0MemoryAdapter
from memlife.adapters.reference import ReferenceMemoryAdapter
from memlife.runner.lifecycle import LifecycleStepObservation
from memlife.runner.provenance import ProvenanceTraceRunner
from memlife.runner.storage_batch import _retrieval_payload
from memlife.runner.authority_correlation_v2 import (
    HostAssociationSnapshot, VERSION, storage_payload_v2, trace_payload_v2)
from memlife.scenarios import LifecycleEvent, canonical_scenarios

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "manifests/next-lp-01/registration-v2.json"
MANIFEST_SHA = "3217aa1c4853a9437f708a60f634c012905634d114a7634cbef927a9f6f88c46"
IMPLEMENTATION = ROOT / "manifests/next-lp-01/implementation-v1.json"
PRODUCERS = ("STORAGE", "TRACE")
ARMS = ("ORIGINAL_BASELINE", "VERSIONED_CORRECTION")
NOW = datetime(2040, 6, 1, tzinfo=timezone.utc)


def repository_binding(path):
    """Portable content custody, not a live admission or path-authority token."""
    path = Path(path).resolve()
    need(path.is_relative_to(ROOT), "REVIEW_AND_SOURCE_MUST_BE_REPOSITORY_MEMBERS")
    value = identity(path)
    value["path"] = str(path.relative_to(ROOT))
    return value


class NoTransport:
    def request(self, *args, **kwargs):
        raise PermissionError("NEXT_LP01_NATIVE_TRANSPORT_FORBIDDEN")


class StaticMem0TraceHooks(ReferenceMemoryAdapter):
    """Declared pure-property projection only, never a constructed native adapter.

    The original per-record base hooks dispatch to these actual Mem0 properties.
    No other Mem0 method or SDK constructor is invoked.
    """
    @property
    def trace_provenance_status(self):
        return Mem0MemoryAdapter.trace_provenance_status.fget(self)

    @property
    def trace_source_surface(self):
        return Mem0MemoryAdapter.trace_source_surface.fget(self)


def registration():
    need(sha(raw(MANIFEST)) == MANIFEST_SHA, "NEXT_LP01_REGISTRATION_DRIFT")
    manifest = strict(raw(MANIFEST))
    for name, digest in {**manifest["frozen_artifacts"], **manifest["original_source_sha256"]}.items():
        need(sha(raw(ROOT / name)) == digest, "NEXT_LP01_SOURCE_OR_FIXTURE_DRIFT:" + name)
    fixtures = strict(raw(ROOT / "manifests/next-lp-01/fixtures-v1.json"))
    oracle = strict(raw(ROOT / "manifests/next-lp-01/oracle-v1.json"))
    ids = [f["fixture_id"] for f in fixtures["fixtures"]]
    need(ids == manifest["fixture_ids"] and len(ids) == len(set(ids)) == 12
         and ids == [r["fixture_id"] for r in oracle["cases"]], "NEXT_LP01_EXACT_12_CASES")
    ledger = AuthorityLedger.model_validate(fixtures["authority_ledger"])
    return manifest, fixtures["fixtures"], {r["fixture_id"]: r for r in oracle["cases"]}, ledger


def materialize(fixture):
    """Exactly registered static normalizers/hooks; no native client construction."""
    if fixture["provider"] == "hindsight":
        adapter = HindsightMemoryAdapter(NoTransport())
        record = adapter._normalized_record(fixture["namespace"], dict(id=fixture["record_id"],
            text=fixture["content"], state="valid", fact_type="observation" if fixture["source_native_ids"] else "world",
            source_memory_ids=fixture["source_native_ids"]))
        need(not fixture["metadata"], "REGISTERED_HINDSIGHT_METADATA_BOUNDARY")
    else:
        need(fixture["provider"] == "mem0" and not fixture["source_native_ids"], "REGISTERED_STATIC_MEM0_BOUNDARY")
        record = Mem0MemoryAdapter._normalized_record(dict(id=fixture["record_id"],
            user_id=fixture["namespace"], memory=fixture["content"], metadata=fixture["metadata"]))
        adapter = StaticMem0TraceHooks()
    if fixture["representation"] == "JSON_ROUNDTRIP":
        record = MemoryRecord.model_validate_json(record.model_dump_json())
    else:
        need(fixture["representation"] == "OBJECT", "REGISTERED_REPRESENTATION")
    need(record.content == fixture["content"] and record.state.value == "active", "REGISTERED_LITERAL_ACTIVE_RECORD")
    return adapter, record


def baseline_projection(associations):
    groups = {}
    for row in associations:
        groups.setdefault(row["source_native_id"], set()).add(row["event_id"])
    unique = {source: next(iter(events)) for source, events in groups.items() if len(events) == 1}
    conflicts = sorted(source for source, events in groups.items() if len(events) != 1)
    return {s: {e} for s, e in unique.items()}, unique, conflicts


def query_observation(record, provider):
    scenario = next(s for s in canonical_scenarios() if s.scenario_id == "baseline")
    step_index, step = next((i, s) for i, s in enumerate(scenario.lifecycle_steps) if s.event is LifecycleEvent.QUERY)
    # This is an authored synthetic observation envelope, not a claimed provider result.
    result = BenchmarkResult(scenario_id=scenario.scenario_id, provider=provider,
        namespace=record.namespace, lifecycle_mode="SYNTHETIC_OFFLINE_INPUT", step_index=step_index,
        intended_event=LifecycleEvent.QUERY, native_operation="NOT_EXECUTED_SYNTHETIC_RECORD",
        operation_status=OperationStatus.SUCCESS, latency_ms=0, timestamp=NOW)
    return scenario, LifecycleStepObservation(step_index, step, result, (record,))


def evaluate_one(fixture, *, producer, arm, ledger):
    adapter, record = materialize(fixture)
    before = record.model_dump_json()
    storage_map, trace_map, conflicts = baseline_projection(fixture["host_associations"])
    data = canonical(dict(schema_version=VERSION, associations=fixture["host_associations"]))
    snapshot = HostAssociationSnapshot.from_host_bytes(data, expected_sha256=sha(data),
        artifact_id="FROZEN_HOST_FIXTURE:" + fixture["fixture_id"])
    runner = ProvenanceTraceRunner(adapter)
    scenario, observation = query_observation(record, fixture["provider"])
    corrected_output = None
    if producer == "STORAGE":
        original_payload, candidates = _retrieval_payload(adapter=adapter, records=(record,), phase="synthetic",
            run_id=fixture["fixture_id"], provider_events=storage_map, ledger=ledger)
        original_output = original_payload
        if arm == "VERSIONED_CORRECTION":
            corrected_output, score = storage_payload_v2(adapter=adapter, records=(record,), provider=fixture["provider"],
                snapshot=snapshot, phase="synthetic", run_id=fixture["fixture_id"], ledger=ledger,
                provider_events=storage_map)
    else:
        need(producer == "TRACE", "REGISTERED_PRODUCER")
        trace, _ = runner._retrieval_trace(experiment_id="NEXT-LP-01", scenario=scenario,
            observation=observation, lifecycle_event_id="synthetic-query", provider_event_ids=trace_map)
        candidates = trace.candidates
        original_output = trace.model_dump(mode="json")
        if arm == "VERSIONED_CORRECTION":
            corrected_trace, _, score = trace_payload_v2(runner=runner, experiment_id="NEXT-LP-01", scenario=scenario,
                observation=observation, lifecycle_event_id="synthetic-query", provider_event_ids=trace_map,
                provider=fixture["provider"], snapshot=snapshot, ledger=ledger)
            corrected_output = corrected_trace.model_dump(mode="json")
    baseline_candidates = tuple(candidates)
    if arm == "ORIGINAL_BASELINE":
        outcome, complete, correlation = normalize_authority_exposure(candidates, ledger), None, None
    else:
        need(arm == "VERSIONED_CORRECTION", "REGISTERED_CLASSIFIER_ARM")
        candidates, outcome = score.candidates, score.exposure
        complete, correlation = score.observations[0].complete, score.observations[0].as_dict()
    events = ledger.by_event_id()
    candidate = candidates[0]
    # Output-derived current-evidence coverage, never copied from the oracle.
    supported_current = [e for e in candidate.source_event_ids if e in events and events[e].authoritative
        and any((a["provider"], a["namespace"], a["record_id"], a["record_sha256"], a["event_id"]) ==
                (fixture["provider"], record.namespace, record.memory_id, sha(record.content.encode()), e)
                for a in fixture["host_associations"])]
    retained = outcome is not AuthorityExposureOutcome.UNKNOWN_PROVENANCE and bool(supported_current)
    need(record.model_dump_json() == before, "PRODUCER_MUTATED_REGISTERED_INPUT")
    return dict(fixture_id=fixture["fixture_id"], producer=producer, arm=arm,
        exposure=outcome.value, error=None, explicit_complete=complete,
        generic_provenance_status=candidate.provenance_status.value,
        baseline_generic_provenance_status=baseline_candidates[0].provenance_status.value,
        baseline_source_event_ids=list(baseline_candidates[0].source_event_ids),
        original_producer_output=original_output,
        original_candidates=[c.model_dump(mode="json") for c in baseline_candidates],
        corrected_producer_output=corrected_output,
        source_event_ids=list(candidate.source_event_ids), exposed_native_source_ids=list(fixture["source_native_ids"]),
        supported_current_event_ids=supported_current, current_evidence_retained=retained,
        projection_conflicts=conflicts, correlation=correlation,
        normalized_record=record.model_dump(mode="json"), host_snapshot_sha256=snapshot.sha256,
        native_operations=0, model_requests=0, protected_dispatches=0)


def analyze(rows, oracle):
    need(len(rows) == 48 and len({(r["fixture_id"], r["producer"], r["arm"]) for r in rows}) == 48,
         "ALL_48_REGISTERED_ROWS_REQUIRED")
    expected = {(f, p, a) for f in oracle for p in PRODUCERS for a in ARMS}
    need({(r["fixture_id"], r["producer"], r["arm"]) for r in rows} == expected, "REGISTERED_ROW_ROSTER")
    arms = {}
    for arm in ARMS:
        group = [r for r in rows if r["arm"] == arm]
        known = [r for r in group if r["error"] is None]
        false_authority = [r for r in known if r["exposure"] == "AUTHORITATIVE_ONLY"
                           and oracle[r["fixture_id"]]["expected_exposure"] != "AUTHORITATIVE_ONLY"]
        incomplete = [r for r in group if not oracle[r["fixture_id"]]["expected_complete"]]
        benign = [r for r in group if oracle[r["fixture_id"]]["expected_complete"]
                  and oracle[r["fixture_id"]]["benign_current_evidence"]]
        complete = [r for r in group if oracle[r["fixture_id"]]["expected_complete"]]
        determinate_negative = [r for r in complete if oracle[r["fixture_id"]]["expected_exposure"] == "NONAUTHORITATIVE_ONLY"]
        determinate_positive = [r for r in complete if oracle[r["fixture_id"]]["expected_exposure"] in
                                ("AUTHORITATIVE_ONLY", "AUTHORITATIVE_AND_NONAUTHORITATIVE")]
        arms[arm] = dict(registered=24, evaluated=len(known), errors=24-len(known),
            classes=dict(Counter(r["exposure"] for r in known)), false_authoritative_only=len(false_authority),
            false_authoritative_only_missing_bounds=[len(false_authority), len(false_authority)+24-len(known)],
            oracle_agreement=sum(r["error"] is None and r["exposure"] == oracle[r["fixture_id"]]["expected_exposure"] for r in group),
            incomplete_registered=len(incomplete), incomplete_unknown_detected=sum(r["error"] is None and r["exposure"] == "UNKNOWN_PROVENANCE" for r in incomplete),
            complete_registered=len(complete), complete_correct=sum(r["error"] is None and r["exposure"] == oracle[r["fixture_id"]]["expected_exposure"] for r in complete),
            benign_registered=len(benign), benign_current_retained=sum(r["error"] is None and r["current_evidence_retained"] for r in benign),
            determinate_negative_registered=len(determinate_negative), false_positive_authority=sum(r["error"] is None and r["exposure"] in ("AUTHORITATIVE_ONLY", "AUTHORITATIVE_AND_NONAUTHORITATIVE") for r in determinate_negative),
            determinate_positive_registered=len(determinate_positive), lost_positive_resolution=sum(r["error"] is not None or r["exposure"] not in ("AUTHORITATIVE_ONLY", "AUTHORITATIVE_AND_NONAUTHORITATIVE") for r in determinate_positive))
    disagreements = {}
    for arm in ARMS:
        disagreements[arm] = sum(next(r for r in rows if (r["fixture_id"], r["producer"], r["arm"]) == (f, "STORAGE", arm))["exposure"] !=
                                 next(r for r in rows if (r["fixture_id"], r["producer"], r["arm"]) == (f, "TRACE", arm))["exposure"] for f in oracle)
    return dict(experiment_id="NEXT-LP-01", registered_rows=48, arms=arms,
        producer_exposure_disagreements=disagreements,
        paired_false_authority_reduction=arms[ARMS[0]]["false_authoritative_only"]-arms[ARMS[1]]["false_authoritative_only"],
        inference="DETERMINISTIC_SELECTED_COVERAGE_NO_POPULATION_OR_MODEL_EFFECT", live_model_requests=0,
        native_operations=0, Jetstream_actions=0, protected_dispatches=0,
        utility="OUTPUT_DERIVED_CURRENT_EVIDENCE_COVERAGE_NOT_TASK_SUCCESS_OR_ACTION_PERMISSION")


def implementation_sources():
    manifest = strict(raw(IMPLEMENTATION))
    need(manifest["schema"] == "NEXT_LP01_IMPLEMENTATION_V1"
         and manifest["registration_sha256"] == sha(raw(MANIFEST)), "EXACT_IMPLEMENTATION_REGISTRATION")
    for name, digest in manifest["files"].items():
        need(sha(raw(ROOT/name)) == digest, "FROZEN_EVALUATOR_SOURCE_DRIFT:"+name)
    return manifest


def source_review(review_path):
    review = strict(raw(review_path))
    need(review["schema"] == "NEXT_LP01_PRE_EXECUTION_SOURCE_REVIEW_V1"
         and review["decision"] == "ACCEPT_PRE_EXECUTION_SOURCE" and review["independent_review"] is True
         and type(review["reviewer"]) is str and bool(review["reviewer"].strip())
         and review["implementation"] == repository_binding(IMPLEMENTATION)
         and review["registration"] == repository_binding(MANIFEST),
         "GENUINE_EXACT_PRE_EXECUTION_SOURCE_REVIEW_REQUIRED")
    return review


def run(out, review_path):
    manifest, fixtures, oracle, ledger = registration()
    implementation = implementation_sources()
    source_review(review_path)
    out = Path(out).resolve()
    need(not out.exists(), "EXCLUSIVE_NEXT_LP01_OUTPUT_NO_REPLAY_OR_OVERWRITE")
    save(out/"inputs.json", dict(registration=repository_binding(MANIFEST), implementation=repository_binding(IMPLEMENTATION),
        review=repository_binding(review_path), frozen_artifacts=manifest["frozen_artifacts"],
        runtime=dict(python=sys.version, pydantic=importlib.metadata.version("pydantic")),
        evidence_class="SYNTHETIC_DETERMINISTIC_OFFLINE_NOT_PROVIDER_OR_MODEL_OBSERVATIONS"))
    rows = []
    for fixture in fixtures:
        for producer in PRODUCERS:
            for arm in ARMS:
                try:
                    row = evaluate_one(fixture, producer=producer, arm=arm, ledger=ledger)
                except Exception as exc:
                    row = dict(fixture_id=fixture["fixture_id"], producer=producer, arm=arm, exposure=None,
                        error=dict(type=type(exc).__name__, message=str(exc)), current_evidence_retained=None,
                        native_operations=0, model_requests=0, protected_dispatches=0)
                save(out/(fixture["fixture_id"]+"__"+producer+"__"+arm+".json"), row)
                rows.append(row)
    registration()
    implementation_sources()
    source_review(review_path)
    result = analyze(rows, oracle)
    save(out/"analysis.json", result)
    files = [dict(path=p.name, sha256=sha(raw(p)), bytes=p.stat().st_size) for p in sorted(out.iterdir())]
    save(out/"inventory.json", dict(schema="NEXT_LP01_OFFLINE_INVENTORY_V1", files=files))
    for path in out.iterdir():
        path.chmod(0o444)
    return dict(output=str(out), inventory=identity(out/"inventory.json"), analysis=result)


def audit(out):
    """Reproduce the sealed pure calculation read-only, never create another run."""
    out = Path(out).resolve()
    inventory = strict(raw(out/"inventory.json"))
    need(len(inventory["files"]) == 50 and {p.name for p in out.iterdir()} ==
         {r["path"] for r in inventory["files"]} | {"inventory.json"}, "EXACT_50_EVIDENCE_MEMBERS")
    for row in inventory["files"]:
        path = out/row["path"]
        need(path.parent == out and sha(raw(path)) == row["sha256"] and path.stat().st_size == row["bytes"], "OFFLINE_EVIDENCE_DRIFT")
    manifest, fixtures, oracle, ledger = registration()
    implementation_sources()
    inputs = strict(raw(out/"inputs.json"))
    need(inputs["registration"] == repository_binding(MANIFEST) and inputs["implementation"] == repository_binding(IMPLEMENTATION)
         and inputs["frozen_artifacts"] == manifest["frozen_artifacts"], "ORIGINAL_EVALUATOR_INPUT_CUSTODY")
    review_path = (ROOT/inputs["review"]["path"]).resolve()
    need(inputs["review"] == repository_binding(review_path), "EXACT_REVIEW_CUSTODY")
    source_review(review_path)
    rows = []
    for f in fixtures:
        for p in PRODUCERS:
            for a in ARMS:
                saved = strict(raw(out/(f["fixture_id"]+"__"+p+"__"+a+".json")))
                recomputed = evaluate_one(f, producer=p, arm=a, ledger=ledger)
                need(saved == recomputed, "READ_ONLY_PAIRED_REPRODUCTION_MISMATCH")
                rows.append(saved)
    result = analyze(rows, oracle)
    need(result == strict(raw(out/"analysis.json")), "ANALYSIS_REPRODUCTION_MISMATCH")
    return result
