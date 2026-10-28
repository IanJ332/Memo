"""Focused synthetic contract controls; actual native-input replay is separate."""
import importlib.util
from pathlib import Path
import socket
import subprocess
import os

import pytest

from memlife.models.authority import AuthorityLedger, AuthorityLedgerEntry
from memlife.models.lifecycle import LifecycleState
from memlife.models.memory import MemoryRecord
from memlife.enforcement import PassThroughFilter, LifecycleStatusFilter

spec=importlib.util.spec_from_file_location('q1_downstream_audit',Path(__file__).resolve().parents[2]/'scripts/research/q1_downstream_audit.py')
study=importlib.util.module_from_spec(spec);spec.loader.exec_module(study)


@pytest.fixture(autouse=True)
def no_external_effects(monkeypatch):
    def denied(*args,**kwargs):
        raise AssertionError('OFFLINE_COMPONENT_CONTROL_NO_NATIVE_OR_EXTERNAL_ACTION')
    for name in ('socket','create_connection','getaddrinfo'):
        monkeypatch.setattr(socket,name,denied)
    monkeypatch.setattr(subprocess,'Popen',denied)
    monkeypatch.setattr(os,'system',denied)
    monkeypatch.setattr(study.Mem0MemoryAdapter,'__init__',denied)


def unit_inputs(two_records):
    records=[];entries=[];associations=[];mapping={}
    for seq,event in enumerate(('CURRENT','UNTRUSTED'),1):
        content='Synthetic unit bytes for '+event
        native_id='SYNTHETIC-'+event
        record=MemoryRecord(memory_id=native_id,namespace='synthetic-unit',content=content,
            metadata={} if event=='CURRENT' else dict(experiment_event_id='CURRENT',source_event_id='CURRENT'),
            state=LifecycleState.ACTIVE,revision=1)
        records.append(record);mapping[native_id]=event
        entries.append(AuthorityLedgerEntry(experiment_event_id=event,logical_fact_id=event,namespace=record.namespace,
            sequence=seq,lifecycle_state=LifecycleState.ACTIVE,authoritative=event=='CURRENT',
            authority_reason='SYNTHETIC_UNIT_HOST_FIXTURE',source_content_sha256=study.sha(content.encode())))
        associations.append(dict(provider=study.PROVIDER,namespace=record.namespace,record_id=native_id,
            record_sha256=study.sha(content.encode()),source_native_id=native_id,event_id=event))
    return (tuple(records) if two_records else (records[1],),dict(ledger=AuthorityLedger(entries=tuple(entries)),
        provider_map=mapping,host_snapshot=dict(association_artifact=dict(associations=associations))))


@pytest.mark.parametrize('cls',[PassThroughFilter,LifecycleStatusFilter])
@pytest.mark.parametrize('two_records',[False,True])
def test_real_trace_route_does_not_import_storage_metadata_attribution(cls,two_records):
    records,kwargs=unit_inputs(two_records)
    result=study.compare(records,filter_instance=cls(),**kwargs)
    untrusted=next(r for r in result['records'] if r['host_event']=='UNTRUSTED')
    assert set(untrusted['legacy_storage_events'])=={'CURRENT','UNTRUSTED'}
    assert untrusted['v2_storage_events']==['UNTRUSTED']
    assert untrusted['legacy_trace_events']==untrusted['v2_trace_events']==['UNTRUSTED']
    assert result['decisions_legacy']==result['decisions_v2']==['ALLOW']*len(records)
    assert result['same_delivered_ids'] and result['delivered_legacy']==result['delivered_v2']==len(records)
    assert result['model_execution']==result['tool_execution']=='NOT_RUN'
    assert not result['models_or_actions_created']


@pytest.mark.parametrize('cls',[PassThroughFilter,LifecycleStatusFilter])
def test_counterfactual_unknown_projection_is_not_a_context_admission_policy(cls):
    records,kwargs=unit_inputs(True)
    before=[r.model_dump_json() for r in records]
    result=study.compare(records,filter_instance=cls(),missing_host=True,**kwargs)
    assert result['condition']=='COUNTERFACTUAL_MISSING_HOST_ASSOCIATION'
    assert result['v2_exposure']=='UNKNOWN_PROVENANCE' and not result['v2_complete']
    assert all(r['v2_trace_events']==[] for r in result['records'])
    assert result['decisions_v2']==['ALLOW','ALLOW'] and result['same_delivered_ids']
    assert result['delivered_v2']==2
    assert result['v2_model_execution']==result['v2_tool_execution']=='NOT_RUN'
    assert before==[r.model_dump_json() for r in records]


def test_replay_hook_cannot_query_or_mutate_a_provider():
    adapter=study.NoNativeHooks()
    for name in ('reset_namespace','write','query','update_or_supersede','delete_or_invalidate','list_or_inspect','restart'):
        with pytest.raises(RuntimeError,match='NO_PROVIDER_OPERATIONS'):
            getattr(adapter,name)()
