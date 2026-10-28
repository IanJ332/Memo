"""Read-only Q1 source replay through existing trace/filter APIs, never SDK calls.

This is an offline consumer comparison, not a deployed Q1-to-filter connection.
Its authored query envelope and timestamp are scaffolding, not native telemetry.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from memlife.r1.protocol import canonical, strict, sha, need
from memlife.native_q1.core import State, Hooks, PROVIDER, audit
from memlife.adapters.mem0 import Mem0MemoryAdapter
from memlife.enforcement import PassThroughFilter, LifecycleStatusFilter
from memlife.models.benchmark import BenchmarkResult, OperationStatus
from memlife.scenarios import canonical_scenarios
from memlife.scenarios.models import LifecycleEvent
from memlife.runner.lifecycle import LifecycleStepObservation
from memlife.runner.provenance import ProvenanceTraceRunner
from memlife.runner.storage_batch import _retrieval_payload
from memlife.runner.authority_correlation_v2 import HostAssociationSnapshot, VERSION, storage_payload_v2, trace_payload_v2

ORIGINAL_INVENTORY = '648d14e445d0d8b9b89105d30b05a1ce7e68b41b4999f53b14865c0e3ee52246'
ENVELOPE_TIMESTAMP = datetime(2026, 10, 28, tzinfo=timezone.utc)  # Authored, not observed SDK time.


class NoNativeHooks(Hooks):
    @property
    def provider_name(self):
        return Mem0MemoryAdapter.provider_name.fget(self)

    @property
    def provider_version(self):
        return Mem0MemoryAdapter.provider_version.fget(self)

    def blocked(self, *args, **kwargs):
        raise RuntimeError('READ_ONLY_CAPTURE_REPLAY_NO_PROVIDER_OPERATIONS')

    reset_namespace = write = query = update_or_supersede = delete_or_invalidate = list_or_inspect = restart = blocked


def query_envelope(records):
    need(bool(records), 'ACTUAL_NONEMPTY_SEARCH_RECORDS_REQUIRED')
    scenario = next(s for s in canonical_scenarios() if s.scenario_id == 'baseline')
    scenario = scenario.model_copy(update=dict(namespace=records[0].namespace))
    index, step = next((i, s) for i, s in enumerate(scenario.lifecycle_steps) if s.event is LifecycleEvent.QUERY)
    result = BenchmarkResult(scenario_id=scenario.scenario_id, provider=PROVIDER, provider_version='2.2.1',
        namespace=records[0].namespace, lifecycle_mode='AUTHORED_OFFLINE_QUERY_ENVELOPE', step_index=index,
        intended_event=LifecycleEvent.QUERY, native_operation='NOT_EXECUTED_READ_ONLY_PRESERVED_SEARCH',
        operation_status=OperationStatus.SUCCESS, query_text='routing note', latency_ms=0,
        timestamp=ENVELOPE_TIMESTAMP)
    return scenario, LifecycleStepObservation(index, step, result, tuple(records))


def compare(records, *, ledger, provider_map, host_snapshot, filter_instance, missing_host=False):
    """Same source records, actual existing APIs; no invented authority consumer."""
    records = tuple(records)
    before = tuple(r.model_dump_json() for r in records)
    adapter = NoNativeHooks()
    source = canonical(dict(schema_version=VERSION,
        associations=[] if missing_host else host_snapshot['association_artifact']['associations']))
    host = HostAssociationSnapshot.from_host_bytes(source, expected_sha256=sha(source), artifact_id='OFFLINE_HOST_REPLAY')
    _, storage = _retrieval_payload(adapter=adapter, records=records, phase='READ_ONLY', run_id='Q1-POST',
        provider_events={k:{v} for k,v in provider_map.items()}, ledger=ledger)
    _, corrected_storage = storage_payload_v2(adapter=adapter, records=records, provider=PROVIDER,
        snapshot=host, phase='READ_ONLY', run_id='Q1-POST', ledger=ledger,
        provider_events={k:{v} for k,v in provider_map.items()})
    scenario, observation = query_envelope(records)
    runner = ProvenanceTraceRunner(adapter, candidate_filter=filter_instance)
    args = dict(experiment_id='OFFLINE-Q1-CONSUMER-REPLAY', scenario=scenario, observation=observation,
                lifecycle_event_id='OFFLINE-QUERY-ENVELOPE', provider_event_ids=provider_map)
    trace, _ = runner._retrieval_trace(**args)
    v2_trace, _, v2_score = trace_payload_v2(runner=runner, provider=PROVIDER, snapshot=host, ledger=ledger, **args)
    need(before == tuple(r.model_dump_json() for r in records), 'SOURCE_RECORDS_MUTATED')
    projected = []
    for record, old_storage, new_storage, old_trace, new_trace in zip(records, storage,
            corrected_storage.candidates, trace.candidates, v2_trace.candidates):
        projected.append(dict(host_event=provider_map[record.memory_id], content_sha256=sha(record.content.encode()),
            legacy_storage_events=list(old_storage.source_event_ids), v2_storage_events=list(new_storage.source_event_ids),
            legacy_trace_events=list(old_trace.source_event_ids), v2_trace_events=list(new_trace.source_event_ids)))
    return dict(filter=type(filter_instance).__name__, condition='COUNTERFACTUAL_MISSING_HOST_ASSOCIATION' if missing_host
        else 'PRESERVED_Q1_HOST_ASSOCIATION', record_count=len(records), records=projected,
        decisions_legacy=[d.decision.value for d in trace.decisions], decisions_v2=[d.decision.value for d in v2_trace.decisions],
        same_delivered_ids=trace.delivered_candidate_ids == v2_trace.delivered_candidate_ids,
        delivered_legacy=len(trace.delivered_candidate_ids), delivered_v2=len(v2_trace.delivered_candidate_ids),
        v2_exposure=v2_score.exposure.value, v2_complete=all(o.complete for o in v2_score.observations),
        model_execution=trace.model_execution.value, tool_execution=trace.tool_execution.value,
        v2_model_execution=v2_trace.model_execution.value, v2_tool_execution=v2_trace.tool_execution.value,
        models_or_actions_created=any(x is not None for x in (trace.model_decision,trace.tool_action,
                                                            v2_trace.model_decision,v2_trace.tool_action)))


def replay(root):
    root = Path(root)
    integrity = audit(root, expected_inventory_sha256=ORIGINAL_INVENTORY)
    state = State(strict((root/'package.json').read_bytes()))
    comparisons = []
    for ordinal in range(1,19):
        intent_path, return_path = (root/f'operations/{ordinal:02d}-{part}.json' for part in ('intent','return'))
        intent, response = strict(intent_path.read_bytes()), strict(return_path.read_bytes())
        state.advance(ordinal,intent['request'],response,sha(intent_path.read_bytes()),sha(return_path.read_bytes()))
        if ordinal not in (6,12,16):
            continue
        records = tuple(Mem0MemoryAdapter._normalized_record(r) for r in response['value']['results'])
        mapping = {native:event for event,native in state.ids.items()}
        for cls in (PassThroughFilter,LifecycleStatusFilter):
            for missing in (False,True):
                result = compare(records,ledger=state.ledger(),provider_map=mapping,host_snapshot=state.snapshot(),
                    filter_instance=cls(),missing_host=missing)
                result['original_search_slot'] = ordinal
                comparisons.append(result)
    return dict(schema='Q1_OFFLINE_DOWNSTREAM_AUDIT_V1', original_inventory_sha256=ORIGINAL_INVENTORY,
        original_integrity=integrity, scope='READ_ONLY_NATIVE_INPUT_REPLAY_PLUS_SEPARATE_HOST_COUNTERFACTUAL',
        query_envelope='AUTHORED_OFFLINE_SCAFFOLDING_NOT_NATIVE_SDK_TIME_OR_NEW_QUERY',
        existing_route='ProvenanceTraceRunner._retrieval_trace -> existing CandidateFilter -> trace delivery only',
        missing_application_edge='No storage_batch corrupted candidate -> implemented security policy connection',
        rq4_bridge='NOT_IMPLEMENTED_DO_NOT_INVENT', comparisons=comparisons,
        new_native_operations=0,new_hosted_model_requests=0,protected_dispatches=0,jetstream_actions=0)


if __name__ == '__main__':
    need(sys.flags.isolated and sys.flags.dont_write_bytecode,'USE_REPOSITORY_VENV_PYTHON_-I_-B')
    def guard(event, args):
        if event.startswith(('socket.','subprocess.','os.exec','os.spawn')) or event == 'os.system':
            raise RuntimeError('OFFLINE_AUDIT_NO_NETWORK_PROCESS_OR_NATIVE_OPERATIONS')
    sys.addaudithook(guard)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-root',required=True)
    args = parser.parse_args()
    print(canonical(replay(args.evidence_root)).decode())
