"""Explicit scripted test artifacts. No provider, model, subprocess or network call."""
from contextlib import ExitStack
from pathlib import Path
import sys
import time
from unittest.mock import patch
from .protocol import canonical, identity, need, raw, registration, request, save, sha, strict, fixture


def qualified_sources(accepted_root):
    """Verify the retained source closure before importing reused offline components."""
    import memlife
    from memlife.r1.contract import QUALIFIED_PINS, QUALIFIED_PINS_SHA
    need(sha(raw(QUALIFIED_PINS)) == QUALIFIED_PINS_SHA, 'QUALIFIED_PINSET_DRIFT')
    accepted_root = Path(accepted_root).resolve()
    for path, digest in strict(raw(QUALIFIED_PINS))['files'].items():
        need(sha(raw(accepted_root / path)) == digest, 'QUALIFIED_SOURCE_DRIFT:' + path)
    private_path = str(accepted_root / 'src/memlife')
    if private_path not in memlife.__path__:
        memlife.__path__.append(private_path)
    return accepted_root


def response(recipient=None, project='AV01'):
    message = dict(role='assistant', content='CURRENT_DESTINATION_UNRESOLVED')
    if recipient:
        message.update(content=None, tool_calls=[dict(id='synthetic-call', type='function', function=dict(
            name='send_report', arguments=canonical(dict(project_id=project, recipient=recipient)).decode()))])
    return canonical(dict(model='qwen-3.8-27b', choices=[dict(index=0, message=message,
                     finish_reason='tool_calls' if recipient else 'stop')]))


def capture_fixture(root, job, block, selected=None):
    """Match qualified worker output schema using visibly scripted provenance."""
    from memlife.batch.evidence import durable, seal
    from memlife.batch.binding import bind
    notes = job['memories']
    scope = job['host_acl']['principal']
    records = [dict(memory_id=f'SYNTHETIC-{i}', content=text) for i, text in enumerate(notes)]
    selected = selected if selected is not None else [dict(native_id=r['memory_id'], content=r['content'],
                        original_position_1based=i+1, scope=scope, native_user_id='SYNTHETIC-NAMESPACE') for i, r in enumerate(records)]
    durable(root / 'job.json', job)
    for phase, pid in (('exercise', 101), ('reopen', 202)):
        result = dict(status='COMPLETED', synthetic=True, job_sha256=sha(canonical(job)),
                      store_identity=job['store_identity'], host_acl=job['host_acl'], provider='mem0',
                      provider_version='2.2.1', mode='INFER_FALSE_LOCAL_EMBEDDINGS', native_client_closed=True,
                      internal_LLM_calls=0, internal_LLM_attempts=0, downstream_Qwen_POSTs=0,
                      container_id='SYNTHETIC-'+phase, pid=pid, owned_ids={str(i): r['memory_id'] for i, r in enumerate(records)},
                      final_records=records, selected_context=selected,
                      raw_retrieval={'results': [dict(id=r['memory_id'], memory=r['content'], score=1., user_id='SYNTHETIC-NAMESPACE') for r in records]},
                      bound_request_sha256=sha(bind(job['request_template'], selected)))
        durable(root / phase / 'result.json', result)
        durable(root / phase / 'capture/retrieval/selected.json', selected)
        durable(root / phase / 'capture/request.body', bind(job['request_template'], selected), raw=True)
        durable(root / phase / 'capture/SYNTHETIC_OPERATIONS.json', dict(synthetic=True, writes=notes, query=job['task'], operations='SCRIPTED_NOT_NATIVE'))
        seal(root / phase)
    durable(root / 'store-cleanup.json', dict(absence_verified=True, synthetic=True))
    seal(root)
    return selected


def run(accepted_root, out, *, stop_ordinal=None, stop_before_model_ordinal=None, full_response_stop_ordinal=None):
    """Run the actual adapted unit controller with explicit scripted boundary doubles."""
    qualified_sources(accepted_root)
    from . import contract, native
    from memlife.batch.evidence import durable, seal, verify_seal
    from memlife.batch.ledger import Ledger
    import types
    out = Path(out).resolve()
    need(not out.exists(), 'SYNTHETIC_OUTPUT_REUSE_FORBIDDEN')
    m, acl, slots = registration()
    package = dict(schema='MEMLIFE_R1_AV_SYNTHETIC_PACKAGE_V1', synthetic=True,
                   execution_id='SYNTHETIC-R1-AV', slots=slots,
                   units=[{**s, 'unit_id': 'SYNTHETIC-'+str(s['ordinal']).zfill(3)} for s in slots])
    prep = out.parent / (out.name + '-synthetic-inputs')
    need(not prep.exists(), 'SYNTHETIC_INPUT_REUSE_FORBIDDEN')
    ppath, gpath = prep / 'package.json', prep / 'grant.json'
    save(ppath, package)
    save(gpath, dict(approved=False, synthetic=True, expires='2099-01-01T00:00:00+00:00'))
    durable(out / 'batch.json', package)
    durable(out / 'input-custody.json', dict(original_manifest=identity(ppath), original_owner_grant=identity(gpath)))
    durable(out / 'access-ready.json', dict(port=0, synthetic=True))
    ledger = Ledger(out / 'ledger.sqlite', package['execution_id'], sha(canonical(package)))
    for u in package['units']:
        ledger.plan(u['unit_id'])
    ledger.close()

    def capture(manifest, design, block, host, slot, root, ledger):
        job = dict(memories=fixture(block, slot['cell']), task=block['query'],
                   host_acl=native.host_fixture(block, host), store_identity='SYNTHETIC_STORE',
                   request_template=native.template(design, block, slot['cell']))
        cap = out / 'native' / slot['capture_id']
        ledger.own('SYNTHETIC-'+slot['slot_id'], 'SCRIPTED_STORE')
        selected = capture_fixture(cap, job, block)
        native.inspect_native(cap, job, block, host)
        ledger.removed('SYNTHETIC-'+slot['slot_id'])
        return cap, selected

    def generate(ledger, job, ordinal, body, folder, **kwargs):
        if ordinal == stop_before_model_ordinal:
            raise TimeoutError('SCRIPTED_BEFORE_SEND_STOP')
        kwargs['send_authorization_check']()
        durable(folder / 'request.body.json', body, raw=True)
        ledger.reserve(job, ordinal, sha(body))
        ledger.send_intent(job, sha(body))
        if ordinal == stop_ordinal:
            raise TimeoutError('SCRIPTED_AMBIGUOUS_SEND_NO_RETRY')
        slot = slots[ordinal-1]
        host = acl['records'][int(slot['block_id'][2:])-1]
        data = response(host['current_recipient'] if slot['cell'] in ('A1', 'A2') else None, slot['block_id'])
        durable(folder / 'response.body.raw', data, raw=True)
        durable(folder / 'receipt.json', dict(entity_complete=True, HTTP_status=200,
                    POST_attempted_or_ambiguous=True, usage=None, synthetic=True,
                    request_sha256=sha(body), response_sha256=sha(data),
                    error={'message': 'SCRIPTED_USAGE_LIMIT'} if ordinal == full_response_stop_ordinal else None))
        if ordinal == full_response_stop_ordinal:
            ledger.transition(job, 'FAILED', dict(synthetic=True, POST_slot_consumed=True))
            raise TimeoutError('SCRIPTED_FULL_RESPONSE_TRANSPORT_STOP')
        ledger.complete(job, sha(data))
        return dict(synthetic=True)

    policy = types.ModuleType('memlife.r1_av.policy'); policy.generate = generate
    tokens = types.ModuleType('memlife.tier_c_final.tokens'); tokens.qualify = lambda *a: dict(synthetic=True)
    access_collection = types.ModuleType('memlife.r1_av._accepted_collection')
    access_collection.verify_access = lambda _: None
    # Protocol, custody, scoring, actual unit transitions, ledger and seals run.
    # All external/native/tokenizer/approval boundaries are visibly scripted.
    stopped = None
    with ExitStack() as stack:
        for name, value in dict(PACKAGE=ppath, OUT=out, EXECUTION=package['execution_id']).items():
            stack.enter_context(patch.object(contract, name, value))
        stack.enter_context(patch.object(contract, 'authorize', lambda *args: (package, strict(raw(gpath)))))
        stack.enter_context(patch.object(native, 'capture_once', capture))
        stack.enter_context(patch.object(native, 'remaining_send_seconds', lambda *a, **kw: 220))
        stack.enter_context(patch.dict(sys.modules, {'memlife.r1_av.policy': policy,
            'memlife.r1_av._accepted_collection': access_collection, 'memlife.tier_c_final.tokens': tokens}))
        for slot in slots:
            try:
                native.unit(ppath, gpath, out, slot['ordinal'], time.monotonic()+10000)
            except TimeoutError as exc:
                stopped = str(exc)
                break
    ledger = Ledger(out / 'ledger.sqlite', package['execution_id'], sha(canonical(package)))
    snap = ledger.verify()
    # Unresolved sends retain their consumed slot and close future admission.
    if stopped:
        for job, state in snap['jobs']:
            if state == 'MODEL_SEND_UNKNOWN':
                ledger.transition(job, 'FAILED', dict(synthetic=True, no_retry=True))
                ledger.transition(job, 'SEALED'); ledger.transition(job, 'CLEANUP_VERIFIED')
            elif state == 'FAILED':
                ledger.transition(job, 'SEALED'); ledger.transition(job, 'CLEANUP_VERIFIED')
    ledger.close_batch(); ledger.close()
    durable(out / 'synthetic-closeout.json', dict(synthetic=True, stopped=stopped,
                hosted_requests=0, provider_operations=0, scientific_collection='NOT_EXECUTED'))
    seal(out); verify_seal(out)
    return dict(root=str(out), synthetic=True, scripted_slots=len(snap['slots']), genuine_model_requests=0,
                inventory=identity(out / 'inventory.json'))
