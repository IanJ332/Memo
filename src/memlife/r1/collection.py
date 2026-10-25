"""R1-only unit binding; native worker, TLS sender, ledger and cleanup are reused."""
from datetime import datetime, timezone
from pathlib import Path
import time

from . import contract
from .protocol import (ARMS, LIMITS, canonical, classify, identity, need, raw,
                       registration, request, save, sha, strict, template, verify_identity)


def host_fixture(block, acl):
    return dict(authored_by='HOST_TEST_FIXTURE', project=block['project_id'],
                principal={**acl['principal'], 'project': block['project_id']},
                principal_allowed=acl['allowed'], current_recipients=acl['current_recipients'],
                before_recipients=[acl['forbidden_historical_recipient']], revision=2,
                session='FICTIONAL_LIVE_TEST_ONLY')


def native_job(m, block, acl, slot, state):
    from memlife.batch.jobs import qualification_job
    job = qualification_job('mem0', contract.EXECUTION, slot['capture_id'], state)
    names = ['current_record'] if slot['condition'] == 'CONTROL' else block['write_order_conflict']
    native_arm = 'MEMORY_NECESSARY_' + slot['condition']
    job.update(purpose='AUTHORIZED_R1_COLLECTION', case_id=block['block_id'], family='A3',
               task=block['retrieval_query'], memories=[block[name] for name in names],
               host_acl=host_fixture(block, acl), request_template=template(m, block, native_arm),
               source_manifest_sha256=contract.verify()['design']['sha256'])
    return job


def inspect_native(capture, job, block, acl):
    from memlife.batch.evidence import verify_seal
    for phase in ('exercise', 'reopen'):
        verify_seal(capture / phase)
        result = strict(raw(capture / phase / 'result.json'))
        need(result['status'] == 'COMPLETED' and result['job_sha256'] == sha(canonical(job))
             and result['store_identity'] == job['store_identity'] and result['host_acl'] == job['host_acl']
             and result['provider'] == 'mem0' and result['provider_version'] == '2.2.1'
             and result['mode'] == 'INFER_FALSE_LOCAL_EMBEDDINGS' and result['native_client_closed'] is True
             and result['internal_LLM_calls'] == result['internal_LLM_attempts'] == result['downstream_Qwen_POSTs'] == 0,
             'AUTHENTIC_NATIVE_REOPEN_OR_INTERNAL_USAGE')
    first = strict(raw(capture / 'exercise/result.json'))
    reopened = strict(raw(capture / 'reopen/result.json'))
    need(first['container_id'] != reopened['container_id'] and first['pid'] > 0 and reopened['pid'] > 0,
         'DISTINCT_NATIVE_PROCESSES')
    need(first['owned_ids'] == reopened['owned_ids'] and len(first['owned_ids']) == len(job['memories'])
         and {r['memory_id']: r['content'] for r in first['final_records']} ==
             {r['memory_id']: r['content'] for r in reopened['final_records']}
         and sorted(r['content'] for r in reopened['final_records']) == sorted(job['memories']), 'NATIVE_PERSISTENCE_AND_EXACT_WRITES')
    selected = reopened['selected_context']
    scope = job['host_acl']['principal']
    capture_selected = strict(raw(capture / 'reopen/capture/retrieval/selected.json'))
    need([r['content'] for r in capture_selected] == [r['content'] for r in selected]
         and [r['native_id'] for r in capture_selected] == [r['native_id'] for r in selected]
         and [r['original_position_1based'] for r in capture_selected] == [r['original_position_1based'] for r in selected]
         and all(r['scope'] == scope for r in capture_selected), 'SELECTED_NATIVE_CAPTURE_SCOPE_AND_ORDER')
    # The byte-pinned worker preserves native raw candidates and selected indices.
    # Recheck its literal selection/request binding without replacing selection.
    from memlife.batch.binding import bind
    native_request = bind(job['request_template'], selected)
    need(sha(native_request) == reopened['bound_request_sha256']
         and raw(capture / 'reopen/capture/request.body') == native_request,
         'NATIVE_SELECTION_REQUEST_CUSTODY')
    return selected


def capture_once(manifest, m, block, acl, slot, root, ledger):
    from memlife.batch import runtime
    from memlife.batch.evidence import durable, seal, verify_seal
    capture = root / 'native' / slot['capture_id']
    state = runtime.TASK / 'stores' / (contract.EXECUTION + '-' + slot['capture_id'])
    job = native_job(m, block, acl, slot, state)
    if capture.exists():
        verify_seal(capture)  # Incomplete native work never authorizes repair/replay.
        need(strict(raw(capture / 'job.json')) == job, 'PAIRED_NATIVE_JOB_REUSE_DRIFT')
    else:
        resources = runtime.information()
        need(resources['RAM_bytes'] >= 7 * 1024**3 and resources['CPU_count'] >= 2
             and resources['local_free_bytes'] >= 8 * 1024**3 + manifest['estimated_evidence_bytes'],
             'LOCAL_NATIVE_RESOURCE_ADMISSION')
        result = runtime.qualify_mem0(job, capture, state, ledger)
        need(not any(not r[3] for r in ledger.snapshot()['resources']), 'OWNED_NATIVE_RESOURCES_REMAIN')
        inspect_native(capture, job, block, acl)
        durable(capture / 'r1-native-result.json', dict(accepted_runtime_return=result,
            authorized_native_procedure=contract.NATIVE_PROCEDURE,
            operation_interpretation='LEGACY_CAPABILITY_LABELS_ARE_NOT_OBSERVED_R1_OPERATION_TELEMETRY_USE_RAW_TRACES'))
        seal(capture)
    selected = inspect_native(capture, job, block, acl)
    need(strict(raw(capture / 'store-cleanup.json'))['absence_verified'] is True
         and not state.exists(), 'STORE_CLEANUP_REQUIRED_BEFORE_MODEL')
    return capture, selected


def frozen_request(root, m, block, arm, capture, selected, grant_path):
    need(not root.exists(), 'REQUEST_FREEZE_REUSE')
    root.mkdir(parents=True)
    body = request(m, block, arm, selected)
    # Bind both task variants to exactly the same literal selected-context bytes.
    selected_id = identity(capture / 'reopen/result.json')
    save(root / 'request.body.json', body, binary=True)
    save(root / 'custody.json', dict(package=identity(contract.PACKAGE), owner_grant=identity(grant_path),
            native_inventory=identity(capture / 'inventory.json'), reopened=selected_id,
            selected_context_sha256=sha(canonical(selected)), request=identity(root / 'request.body.json'),
            block_id=block['block_id'], arm=arm, request_schema='EXACT_REGISTERED_R1_ENVELOPE'))
    for path in root.iterdir():
        path.chmod(0o444)
    return body


def check_frozen(root, body, capture, selected, grant_path):
    custody = strict(raw(root / 'custody.json'))
    for item in ('package', 'owner_grant', 'native_inventory', 'reopened', 'request'):
        verify_identity(custody[item])
    need(custody['owner_grant'] == identity(grant_path) and custody['package'] == identity(contract.PACKAGE)
         and custody['native_inventory'] == identity(capture / 'inventory.json')
         and custody['reopened'] == identity(capture / 'reopen/result.json')
         and custody['selected_context_sha256'] == sha(canonical(selected))
         and raw(root / 'request.body.json') == body
         and custody['request']['sha256'] == sha(body), 'FROZEN_TRANSMITTED_BYTES_OR_CONTEXT_DRIFT')


def remaining_send_seconds(deadline, expires, *, mono=None, wall=None):
    mono = time.monotonic() if mono is None else mono
    wall = datetime.now(timezone.utc) if wall is None else wall
    left = min(deadline - mono, (datetime.fromisoformat(expires) - wall).total_seconds())
    need(left >= 250, 'WHOLE_POST_AND_SEAL_ALLOWANCE_EXHAUSTED_NO_SEND')
    return min(220, left - 30)


def unit(manifest_path, grant_path, root, ordinal, deadline):
    from memlife.batch.ledger import Ledger
    from memlife.batch.evidence import durable, seal, verify_seal
    from ._accepted_collection import verify_access
    manifest, grant = contract.authorize(manifest_path, grant_path)
    root = Path(root)
    need(root == contract.OUT and type(ordinal) is int and 1 <= ordinal <= 32, 'R1_ROOT_OR_ORDINAL')
    verify_access(root)
    input_custody = strict(raw(root / 'input-custody.json'))
    need(input_custody['original_manifest'] == identity(manifest_path)
         and input_custody['original_owner_grant'] == identity(grant_path), 'CHILD_INPUT_CUSTODY')
    m, acl, _ = registration()
    slot = manifest['units'][ordinal - 1]
    block_index = int(slot['block_id'].rsplit('-', 1)[1]) - 1
    block, host = m['blocks'][block_index], acl['records'][block_index]
    gid = identity(grant_path)
    out = root / 'units' / slot['unit_id']
    need(not out.exists(), 'R1_UNIT_REPLAY_FORBIDDEN')
    out.mkdir(parents=True)

    class BoundLedger(Ledger):
        def reserve(self, job, index, digest):
            need(job == slot['unit_id'] and index == ordinal <= 32 and digest == sha(body), 'EXACT_R1_SLOT_REQUEST_BUDGET')
            need(len(self.snapshot()['slots']) * 4096 + 4096 <= 131072, 'R1_TOTAL_COMPLETION_RESERVATION')
            check_frozen(out / 'frozen', body, capture, selected, grant_path)
            return super().reserve(job, index, digest)

    ledger = BoundLedger(root / 'ledger.sqlite', contract.EXECUTION, sha(canonical(manifest)))
    try:
        need(ledger.state(slot['unit_id']) == 'PLANNED', 'R1_UNIT_ALREADY_STARTED')
        ledger.transition(slot['unit_id'], 'PREFLIGHTED', {'package': identity(manifest_path)})
        ledger.transition(slot['unit_id'], 'ADMITTED', {'owner_grant': gid})
        ledger.transition(slot['unit_id'], 'PROVIDER_RUNNING')
        capture, selected = capture_once(manifest, m, block, host, slot, root, ledger)
        ledger.transition(slot['unit_id'], 'MEMORY_CAPTURED', {'reused_native_capture': identity(capture / 'inventory.json')})
        body = frozen_request(out / 'frozen', m, block, slot['arm'], capture, selected, grant_path)
        from memlife.tier_c_final.tokens import qualify
        durable(out / 'prompt-admission.json', qualify(body, out / 'reference-tokens', ledger))

        def before_send():
            need(identity(grant_path) == gid, 'OWNER_GRANT_CHANGED')
            contract.authorize(manifest_path, grant_path)
            verify_access(root)
            verify_seal(capture)
            check_frozen(out / 'frozen', body, capture, selected, grant_path)
            return remaining_send_seconds(deadline, grant['expires'])

        try:
            from .policy import generate
            observed = generate(ledger, slot['unit_id'], ordinal, body, out / 'model',
                    send_authorization_check=before_send, observed_prompt_stop_threshold=32768,
                    port=strict(raw(root / 'access-ready.json'))['port'])
        finally:
            if (out / 'model/receipt.json').exists():
                receipt = strict(raw(out / 'model/receipt.json'))
                result = classify(raw(out / 'model/response.body.raw'), host,
                                  entity_complete=receipt['entity_complete'], http_status=receipt['HTTP_status'])
                result.update(slot_id=slot['slot_id'], attempted=receipt['POST_attempted_or_ambiguous'],
                              usage=receipt['usage'], capture=identity(capture / 'inventory.json'),
                              selected_current_positions=[r['original_position_1based'] for r in selected if r['content'] == block['current_record']],
                              selected_historical_positions=[r['original_position_1based'] for r in selected if r['content'] == block['historical_record']],
                              F04='NOT_EVALUATED_R1_ACL_CLASSIFICATION_ONLY', protected_dispatches=0)
                durable(out / 'scoring.json', result)
        ledger.transition(slot['unit_id'], 'F04_PENDING', {'R1_ACL_scoring': identity(out / 'scoring.json'), 'no_dispatch': True})
        ledger.transition(slot['unit_id'], 'SEALED')
        ledger.transition(slot['unit_id'], 'CLEANUP_VERIFIED')
        seal(out)
    except BaseException:
        if ledger.state(slot['unit_id']) in ('PROVIDER_RUNNING', 'MEMORY_CAPTURED'):
            ledger.transition(slot['unit_id'], 'FAILED', {'effect': 'UNKNOWN_NO_REPLAY'})
        raise
    finally:
        ledger.close()
