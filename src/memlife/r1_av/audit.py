"""Read-only reproduction; derived outputs must be outside sealed campaign trees."""
from pathlib import Path
from .protocol import (analyze, canonical, classify, identity, need, raw, registration,
                       request, sha, strict, exposure, verify_identity)


def reproduce(root, package, *, synthetic=False):
    from memlife.batch.evidence import verify_seal
    from memlife.batch.ledger import Ledger
    from .native import inspect_native, job_memories, host_fixture, retrieved_records
    root = Path(root).resolve()
    verify_seal(root)
    need(strict(raw(root / 'batch.json')) == package, 'AUDIT_ORIGINAL_PACKAGE')
    need(package.get('synthetic', False) is synthetic, 'AUDIT_SCIENTIFIC_SYNTHETIC_SEPARATION')
    m, acl, slots = registration()
    need(package['slots'] == slots, 'AUDIT_REGISTERED_ROSTER')
    need(len(package['units']) == 32 and all(all(u[k] == s[k] for k in s)
         for u, s in zip(package['units'], slots)), 'AUDIT_REGISTERED_UNIT_BINDING')
    snapshot = Ledger.read_only(root / 'ledger.sqlite', package['execution_id'], sha(canonical(package)))
    expected_jobs = {u['unit_id'] for u in package['units']}
    need(len(expected_jobs) == 32 and {j[0] for j in snapshot['jobs']} == expected_jobs,
         'AUDIT_EXACT_LEDGER_JOB_ROSTER')
    reserved = {s[0]: s for s in snapshot['slots']}
    unit_by_id = {u['unit_id']: u for u in package['units']}
    for job, ordinal, digest, state, response_digest in snapshot['slots']:
        need(job in unit_by_id and unit_by_id[job]['ordinal'] == ordinal, 'AUDIT_LEDGER_ORDINAL_BINDING')
        frozen = root / 'units' / job / 'frozen/request.body.json'
        need(sha(raw(frozen)) == digest, 'AUDIT_LEDGER_REQUEST_DIGEST')
        if state == 'COMPLETED':
            need(sha(raw(root / 'units' / job / 'model/response.body.raw')) == response_digest,
                 'AUDIT_LEDGER_RESPONSE_DIGEST')
    rows = []
    for slot in slots:
        unit = next(u for u in package['units'] if u['slot_id'] == slot['slot_id'])
        folder = root / 'units' / unit['unit_id']
        row = dict(slot_id=slot['slot_id'], primary='INCOMPLETE_OR_UNKNOWN',
                   unauthorized_indicator=None, complete_response=False,
                   attempted=unit['unit_id'] in reserved and reserved[unit['unit_id']][3] in ('SEND_UNKNOWN', 'COMPLETED'))
        block_index = int(slot['block_id'][2:])-1
        block, host = m['blocks'][block_index], acl['records'][block_index]
        capture = root / 'native' / slot['capture_id']
        selected = None
        # Native observability survives a downstream token/deadline/transport stop.
        # Partial unsealed native work remains UNKNOWN; never repaired or replayed.
        if (capture / 'inventory.json').exists():
            verify_seal(capture)
            job = strict(raw(capture / 'job.json'))
            need(job['memories'] == job_memories(block, slot['cell']) and job['task'] == block['query'], 'AUDIT_NATIVE_JOB')
            need(job['host_acl'] == host_fixture(block, host), 'AUDIT_INDEPENDENT_HOST_ACL')
            for phase in ('exercise', 'reopen'):
                phase_result = strict(raw(capture / phase / 'result.json'))
                need(phase_result.get('synthetic', False) is synthetic and phase_result.get('test_scope', False) is False,
                     'AUDIT_CAPTURE_SCIENTIFIC_SYNTHETIC_SEPARATION')
            selected = inspect_native(capture, job, block, host)
            row['exposure'] = exposure(block, slot['cell'], selected, stored=job['memories'],
                        retrieved=retrieved_records(strict(raw(capture / 'reopen/result.json'))['raw_retrieval']))
            if (folder / 'frozen/custody.json').exists():
                body = request(m, block, slot['cell'], selected)
                custody = strict(raw(folder / 'frozen/custody.json'))
                need(raw(folder / 'frozen/request.body.json') == body
                     and custody['package']['sha256'] == sha(canonical(package)), 'AUDIT_REQUEST_CUSTODY')
                for key in ('package', 'owner_grant', 'native_inventory', 'reopened', 'request'):
                    verify_identity(custody[key])
                need(custody['native_inventory'] == identity(capture / 'inventory.json')
                     and custody['reopened'] == identity(capture / 'reopen/result.json')
                     and custody['request'] == identity(folder / 'frozen/request.body.json')
                     and custody['selected_context_sha256'] == sha(canonical(selected)), 'AUDIT_FROZEN_BINDING')
        if (folder / 'model/receipt.json').exists():
            need(unit['unit_id'] in reserved and selected is not None, 'AUDIT_RECEIPT_WITHOUT_RESERVATION_OR_CAPTURE')
            receipt = strict(raw(folder / 'model/receipt.json'))
            need(receipt.get('synthetic', False) is synthetic and receipt.get('test_scope', False) is False,
                 'AUDIT_RESPONSE_SCIENTIFIC_SYNTHETIC_SEPARATION')
            need(receipt['POST_attempted_or_ambiguous'] is row['attempted'], 'AUDIT_ATTEMPTED_LEDGER_BINDING')
            body = raw(folder / 'frozen/request.body.json')
            need(raw(folder / 'model/request.body.json') == body and receipt['request_sha256'] == sha(body),
                 'AUDIT_TRANSPORT_REQUEST_BYTES')
            need(receipt['response_sha256'] == sha(raw(folder / 'model/response.body.raw')),
                 'AUDIT_TRANSPORT_RESPONSE_BYTES')
            result = classify(raw(folder / 'model/response.body.raw'), host, selected=selected, block=block,
                              entity_complete=receipt['entity_complete'], http_status=receipt['HTTP_status'])
            saved = strict(raw(folder / 'scoring.json'))
            need(saved['slot_id'] == slot['slot_id'] and saved['capture'] == identity(capture / 'inventory.json'),
                 'AUDIT_SCORING_SLOT_CAPTURE_BINDING')
            need(all(saved[k] == v for k, v in result.items()), 'AUDIT_SCORING_REPRODUCTION')
            need(saved['exposure'] == row['exposure'], 'AUDIT_EXPOSURE_REPRODUCTION')
            row = {**saved, 'attempted': row['attempted'], 'transport_error': receipt.get('error'),
                   'transport_completed': reserved[unit['unit_id']][3] == 'COMPLETED'}
        rows.append(row)
    result = analyze(rows, slots)
    result.update(scientific_collection='NOT_EXECUTED_SYNTHETIC_TEST' if synthetic else 'SEALED_CAMPAIGN_ROWS_ONLY',
                  inventory=identity(root / 'inventory.json'), ledger_jobs=len(snapshot['jobs']))
    return result
