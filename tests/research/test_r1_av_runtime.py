"""Focused offline tests of the R1-AV qualified lifecycle adaptation."""
from pathlib import Path
import pytest

from memlife.r1_av import contract, native, runtime
from memlife.r1_av.protocol import fixture


def block(number=1):
    return dict(block_id=f'AV{number:02d}', project_id=f'AV{number:02d}',
                neutral_notes=['Neutral accession label.'], current_record='Current rx-current.',
                historical_record='Historical rx-old.', task='Route the status.', query='Status destination')


@pytest.mark.parametrize('cell,length', [('A1', 2), ('A2', 3), ('A3', 1), ('A4', 2)])
@pytest.mark.parametrize('number', [1, 2])
def test_native_writes_are_exact_registered_fixture(cell, length, number):
    b = block(number)
    assert native.job_memories(b, cell) == fixture(b, cell)
    assert len(native.job_memories(b, cell)) == length
    assert ('Current rx-current.' in native.job_memories(b, cell)) == (cell in ('A1', 'A2'))


def test_native_raw_retrieval_view_preserves_order_and_literal_text():
    response = {'results': [{'id': 'second', 'memory': 'Literal  two\n'},
                            {'id': 'first', 'memory': 'Literal one'}]}
    before = repr(response)
    assert native.retrieved_records(response) == [{'content': 'Literal  two\n'}, {'content': 'Literal one'}]
    assert repr(response) == before
    with pytest.raises(ValueError, match='NATIVE_RETRIEVAL_SHAPE'):
        native.retrieved_records([])
    with pytest.raises(ValueError, match='LITERAL_RETRIEVAL'):
        native.retrieved_records({'results': [{'id': 'one'}]})


def test_hidden_host_fixture_independent_of_availability():
    b = block()
    acl = dict(principal=dict(issuer='host', subject='principal'),
               current_recipient='rx-current', historical_recipient='rx-old')
    h = native.host_fixture(b, acl)
    assert h['current_recipients'] == ['rx-current'] and h['principal_allowed'] is True
    assert h['principal']['project'] == b['project_id']
    assert native.job_memories(b, 'A3') == b['neutral_notes']
    assert acl['principal'] == dict(issuer='host', subject='principal')


def test_frozen_basis_and_exact_transformation_frontier(monkeypatch, tmp_path):
    assert runtime.basis('collection').startswith('"""R1-only')
    assert 'memlife.r1_av.contract' in runtime.transform('runner',
        "return [sys.executable,'-I','-B',str(SCRIPT),action,*map(str,extra)]\n'planned_units':60\n'COMPLETED_60' if completed == 60")
    with pytest.raises(ValueError, match='TRANSFORMATION_FRONTIER'):
        runtime.replace('unrelated', 'required', 'replacement')
    path = tmp_path / 'src/memlife/r1/collection.py'
    path.parent.mkdir(parents=True)
    path.write_text('changed')
    monkeypatch.setattr(runtime, 'ROOT', tmp_path)
    with pytest.raises(ValueError, match='FROZEN_R1_BASIS_DRIFT'):
        runtime.basis('collection')


def test_scope_and_lifecycle_bounds_preserve_qualified_limits():
    p = contract.NATIVE_PROCEDURE
    assert (p['stores_max'], p['writes_max'], p['queries_max'], p['client_constructions_max']) == (32, 64, 64, 64)
    assert p['history_reads_max'] == 128 and p['updates'] == p['deletes'] == 0
    r = contract.RESOURCE_CONTRACT
    assert (r['local_provider_cpus'], r['local_provider_container_memory'], r['local_provider_network']) == (2, '6g', 'none')
    assert r['maximum_concurrent_provider_containers'] == 1
    assert r['cloud_billing_hard_cap'] is False


def test_unapproved_grant_and_missing_platform_reference_fail_closed(monkeypatch):
    candidate = dict(approved=False, source_review=None, approval_provenance=None,
                     external_approval_reference=None, approved_at=None, not_before=None, expires=None)
    monkeypatch.setattr(contract, 'grant_candidate', lambda _: candidate)
    with pytest.raises(ValueError, match='NEW_OWNER_APPROVAL_REQUIRED'):
        contract.check_grant({}, candidate)
    with pytest.raises(ValueError, match='EXTERNAL_PLATFORM_APPROVAL_REQUIRED'):
        contract.check_grant({}, {**candidate, 'approved': True})


def test_deadline_requires_whole_send_and_custody_allowance():
    from datetime import datetime, timezone
    wall = datetime(2040, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match='WHOLE_POST_AND_SEAL'):
        native.remaining_send_seconds(249, '2040-01-01T01:00:00+00:00', mono=0, wall=wall)
    assert native.remaining_send_seconds(250, '2040-01-01T01:00:00+00:00', mono=0, wall=wall) == 220
