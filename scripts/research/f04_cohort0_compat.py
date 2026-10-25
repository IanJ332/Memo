"""Versioned Cohort 0 authentic enrollment and decision-only F04 TEST_ONLY replay.

This public entrypoint does not modify or call around the legacy enrollment
contract. It defines a new, independently reviewed evidence contract for the
six-field, fresh-execution, Option B capture format. No dispatcher, protected
sink, model/provider call, formal GENERATION_ID, or synthetic capture input is
available. The public accepted F04 authorization function is used unchanged.
"""
import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import types

SCHEMA = 'COHORT0_AUTHENTIC_F04_DECISION_ONLY_V1'
PINS_SHA = '844906186399e52c310e14e6aed77495ce457038b89e4289cf9f32e5d88695af'
LEGACY_ENROLLMENT_SHA = '3a3634a0774b962505d7affc8a7fd4f7ea5943bfb6e50eb09d579049168e9028'
MANIFEST_SHA = '563fdb5e5fe9b74afc15cff444ff282ba046dddc71a8b21e8e24e0c027751fc6'
INVENTORY_SHA = 'c0f34dbe797b2b4c4ffca5354ac4eb6fb448f45cd81a86fe212d16812e8ac22b'
SOURCE = 'scripts/research/f04_cohort0_compat.py'
TEST = 'tests/research/test_f04_cohort0_compat.py'


def need(value, reason):
    if not value:
        raise ValueError(reason)


def strict(value):
    def pairs(rows):
        result = {}
        for key, item in rows:
            need(key not in result, 'DUPLICATE_JSON_KEY')
            result[key] = item
        return result
    return json.loads(value, object_pairs_hook=pairs,
                      parse_constant=lambda _: need(False, 'NONFINITE_JSON'))


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def raw(path):
    path = Path(path)
    need(path == path.resolve() and path.is_file() and path.stat().st_nlink == 1,
         'REGULAR_CANONICAL_EVIDENCE_REQUIRED')
    need(path.stat().st_size <= 32 * 1024 * 1024, 'EVIDENCE_FILE_LIMIT')
    return path.read_bytes()


def identity(path):
    value = raw(path)
    return {'path': str(path), 'sha256': sha(value), 'bytes': len(value)}


def verified_identity(value):
    need(set(value) == {'path', 'sha256', 'bytes'} and
         identity(Path(value['path'])) == value, 'EVIDENCE_IDENTITY')


def save(path, value):
    with Path(path).open('xb') as stream:
        stream.write(canonical(value)); stream.flush(); os.fsync(stream.fileno())


def sealed(root):
    root = Path(root)
    need(root == root.resolve(), 'CANONICAL_SEAL_ROOT')
    inventory = strict(raw(root / 'inventory.json'))
    names = set()
    for row in inventory['files']:
        path = root / row['path']
        need(path.resolve().is_relative_to(root) and row['path'] not in names,
             'SEAL_PATH')
        value = raw(path)
        need(sha(value) == row['sha256'] and len(value) == row['bytes'],
             'SEAL_IDENTITY')
        names.add(row['path'])
    need({str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()} ==
         names | {'inventory.json'}, 'SEAL_MEMBERSHIP')


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def offline_guard(root, files):
    """Deny network/process dispatch and unreviewed repository Python execution."""
    def guard(event, args):
        if event.startswith('socket.') or event in {
                'subprocess.Popen', 'os.system', 'os.posix_spawn', 'os.exec'}:
            raise PermissionError('OFFLINE_DECISION_ONLY_CONTAINMENT')
        if event == 'exec':
            filename = Path(args[0].co_filename)
            if filename.is_absolute() and filename.is_relative_to(root):
                name = str(filename.relative_to(root))
                need(name in files and sha(raw(filename)) == files[name],
                     'UNREVIEWED_IMPORTED_SOURCE:' + name)
    sys.addaudithook(guard)


def required_sources(root, campaign):
    """Review request inventory, not an admission or an owner grant."""
    manifest = strict(raw(campaign / 'batch.json'))
    grant = strict(raw(campaign / 'owner-authorization.json'))
    revision = strict(raw(Path(grant['metadata_source_revision']['path'])))
    paths = set(manifest['code_files_sha256']) | set(revision['revised_code_sha256'])
    # The source-chain verifier imports strict contract modules transitively.
    paths |= {str(p.relative_to(root)) for directory in
              ('src/memlife/batch', 'src/memlife/tier_c_final',
               'src/memlife/tier_c_bounded') for p in (root / directory).glob('*.py')}
    for job_path in sorted((campaign / 'units').glob('*/native/job.json')):
        paths.update(strict(raw(job_path))['source_files_sha256'])
    paths |= {'src/memlife/__init__.py', 'src/memlife/tier_c_admission.py',
              'src/memlife/research_collection.py', 'src/memlife/qwen_tls_context.py',
              'scripts/research/batch_f04_enrollment.py', SOURCE, TEST}
    return {name: sha(raw(root / name)) for name in sorted(paths)}


def review_contract(root, campaign, accepted, pins_path, review_path):
    review = strict(raw(review_path))
    need(set(review) == {'schema', 'decision', 'independent_review', 'reviewer',
         'scope', 'files_sha256', 'accepted_pins_manifest', 'accepted_source_files',
         'campaign_inventory', 'scientific_manifest'}, 'REVIEW_SCHEMA')
    need(review['schema'] == 'cohort0-f04-decision-review-v1' and
         review['decision'] == 'ACCEPTED_AUTHENTIC_DECISION_ONLY_TEST_ONLY' and
         review['independent_review'] is True and bool(review['reviewer']) and
         review['scope'] == SCHEMA, 'INDEPENDENT_ACCEPTANCE_REQUIRED')
    need(sha(raw(pins_path)) == PINS_SHA, 'ACCEPTED_PINS_MANIFEST')
    pins = strict(raw(pins_path))
    need(review['accepted_pins_manifest'] == identity(pins_path) and
         review['accepted_source_files'] == pins['files'], 'ACCEPTED_F04_PINS')
    for name, digest in pins['files'].items():
        need(sha(raw(accepted / name)) == digest, 'ACCEPTED_F04_SOURCE:' + name)
    need(review['files_sha256'] == required_sources(root, campaign),
         'REVIEWED_ADAPTER_AND_SOURCE_CLOSURE')
    need(sha(raw(root / 'scripts/research/batch_f04_enrollment.py')) ==
         LEGACY_ENROLLMENT_SHA, 'LEGACY_ENROLLMENT_UNCHANGED')
    need(review['campaign_inventory'] == identity(campaign / 'inventory.json') and
         review['campaign_inventory']['sha256'] == INVENTORY_SHA and
         review['scientific_manifest'] == identity(campaign / 'batch.json') and
         review['scientific_manifest']['sha256'] == MANIFEST_SHA,
         'REVIEWED_AUTHENTIC_COHORT_IDENTITY')
    offline_guard(root, review['files_sha256'])
    return review, pins


def verify_custody(campaign, manifest, grant, binding):
    custody = strict(raw(campaign / 'input-custody.json'))
    need(set(custody) == {prefix + name for prefix in ('original_', 'snapshot_')
                        for name in ('manifest', 'owner_grant', 'execution_binding')},
         'EXACT_SIX_FIELD_CUSTODY')
    for name, filename, value in (('manifest', 'batch.json', manifest),
                                  ('owner_grant', 'owner-authorization.json', grant),
                                  ('execution_binding', 'execution-binding.json', binding)):
        snapshot = custody['snapshot_' + name]
        original = custody['original_' + name]
        verified_identity(original)
        need(snapshot == identity(campaign / filename) and
             all(snapshot[key] == original[key] for key in ('sha256', 'bytes')) and
             strict(raw(Path(original['path']))) == value,
             'EXACT_ORIGINAL_SNAPSHOT_CUSTODY:' + name)
    need(grant['manifest'] == custody['original_manifest'] and
         grant['execution_binding'] == custody['original_execution_binding'],
         'GRANT_ORIGINAL_CUSTODY')
    return custody


def verify_grant(root, campaign, manifest, grant, binding):
    """Historical static authority; never reauthorizes an expired generation."""
    sys.path.insert(0, str(root / 'src'))
    try:
        contract = importlib.import_module('memlife.tier_c_bounded.contract')
    finally:
        sys.path.pop(0)
    need(contract.ROOT == root and contract.OUT == campaign,
         'ORIGINAL_BOUND_CONTRACT_LOCATION')
    need(contract.verify() == manifest, 'ORIGINAL_FROZEN_MANIFEST')
    # Static original source/identity/review chain includes all four amendments.
    contract.identity_revision_authorization(manifest, grant)
    need(grant['schema'] == 'OWNER_AUTHORIZED_NATIVE_BATCH_BOUNDED_RISK_V1' and
         grant['approved'] is True and grant['bounded_risk_acknowledgment'] == contract.ACK,
         'GENUINE_OPTION_B_OWNER_GRANT')
    need(grant['admission_policy'] == identity(contract.POLICY) and
         grant['batch_id'] == manifest['batch_id'] and
         grant['execution_id'] == binding['execution_id'] and
         grant['output_root'] == str(campaign), 'HISTORICAL_GRANT_BINDING')
    need(grant['downstream_POST_ceiling'] == 60 and
         grant['completion_token_ceiling'] == 245760 and
         grant['local_reference_token_bound'] == 32768 and
         grant['observed_prompt_stop_threshold_each'] == 32768 and
         grant['provider_internal_LLM_calls'] == 0 and grant['concurrency'] == 1 and
         grant['retries'] == 0 and grant['fallbacks'] == 0 and
         grant['protected_tool_dispatch'] is False and grant['synthetic_only'] is True and
         grant['endpoint'] == manifest['endpoint'] and
         grant['runtime_location'] == manifest['runtime_location'],
         'HISTORICAL_SCOPE_AND_BUDGET')
    need(manifest['remote_hard_prompt_cap'] == 'NOT_GUARANTEED' and
         grant['bounded_risk_acknowledgment']['remote_32768_prompt_limit_guaranteed'] is False and
         not any(k in manifest or k in grant for k in
                 ('prompt_token_ceiling_each', 'prompt_token_ceiling_total')),
         'NO_FABRICATED_REMOTE_HARD_CAP')
    begin, end, approved = (datetime.fromisoformat(grant[key]) for key in
                            ('not_before', 'expires', 'approved_at'))
    need(all(x.tzinfo is not None for x in (begin, end, approved)) and
         type(grant['window_seconds']) is int and
         0 < grant['window_seconds'] <= 86400 and
         (end - begin).total_seconds() == grant['window_seconds'] and
         grant['start_within_24h_of_approval'] is True and
         0 <= (begin - approved).total_seconds() <= 86400,
         'ORIGINAL_AUTHORITY_INTERVAL')
    return contract


def mapped_unit(manifest, binding, uid):
    need(binding['schema'] == 'TIER_C_FRESH_EXECUTION_BINDING_V1' and
         binding['source_batch_id'] == manifest['batch_id'] and
         len(binding['units']) == len(manifest['units']) == 60,
         'FRESH_SCIENTIFIC_EXECUTION_MAPPING')
    matches = []
    for ordinal, (source, row) in enumerate(zip(manifest['units'], binding['units']), 1):
        need(row == {'ordinal': ordinal, 'source_unit_id': source['unit_id'],
             'source_prospective_attempt_id': source['prospective_attempt_id'],
             'execution_unit_id': f"{binding['execution_id']}-{ordinal:03d}",
             'prospective_attempt_id': f"EXP-QWEN-{binding['execution_id']}-{ordinal:03d}"},
             'EXACT_SCIENTIFIC_EXECUTION_ROW')
        if row['execution_unit_id'] == uid:
            matches.append({**source, 'source_unit_id': source['unit_id'],
                            'source_prospective_attempt_id': source['prospective_attempt_id'],
                            'unit_id': uid, 'prospective_attempt_id': row['prospective_attempt_id']})
    need(len(matches) == 1, 'UNIT_IDENTITY')
    return matches[0]


def selected_projection(rows):
    return [(row['native_id'], row['content'], row['original_position_1based'])
            for row in rows]


def verify_selection(provider, native_raw, selected, scope, reopened, capture):
    namespace = 'npq-' + sha(canonical(scope))
    if provider == 'mem0':
        rows = native_raw['results']
        expected = [(r['id'], r['memory'], i + 1) for i, r in enumerate(rows)]
        need(all(r['user_id'] == namespace for r in rows) and
             all(r['native_user_id'] == namespace for r in selected), 'NATIVE_USER_SCOPE')
    elif provider == 'hindsight':
        rows = native_raw['results']
        expected = [(r['id'], r['text'], i + 1) for i, r in enumerate(rows)]
        need(reopened['native_namespace'] == namespace, 'NATIVE_BANK_SCOPE')
        candidates = [strict(raw(path)) for path in sorted((capture / 'candidates').glob('*.json'))]
        candidates = [c for c in candidates if c.get('http_exchange', {}).get('response', {}).get('sha256') == sha(canonical(native_raw))]
        # Provider response serialization may contain ordinary JSON whitespace;
        # compare exact captured raw bytes, not a reserialized digest.
        if not candidates:
            digest = sha(raw(capture / 'retrieval/raw.bin'))
            candidates = [strict(raw(path)) for path in sorted((capture / 'candidates').glob('*.json'))
                          if strict(raw(path)).get('http_exchange', {}).get('response', {}).get('sha256') == digest]
        need(len(candidates) == 1, 'ONE_ACTUAL_RECALL_CANDIDATE_CAPTURE')
        c = candidates[0]
        need(c['limit'] == c['extraction']['limit'] == 10 and
             c['total_candidates'] == len(rows) and c['selected_count'] == min(10, len(rows)) and
             [r['position'] for r in c['candidates'] if r['included']] == list(range(1, min(10, len(rows)) + 1)),
             'ACTUAL_LIMIT10_CANDIDATE_SELECTION')
        exchange = c['http_exchange']
        for key in ('manifest', 'response'):
            item = exchange[key]; value = raw(capture / item['path'])
            need(sha(value) == item['sha256'] and len(value) == item['byte_count'],
                 'PASSIVE_RECALL_EXCHANGE_IDENTITY')
        need(raw(capture / exchange['response']['path']) == raw(capture / 'retrieval/raw.bin'),
             'LITERAL_PASSIVE_RAW_RECALL')
    elif provider == 'openviking':
        rows = native_raw['result']['memories']
        expected = [(r['uri'], r['content'], i + 1) for i, r in enumerate(rows)]
        need(reopened['native_user'] == namespace and
             all(r['uri'].startswith('viking://user/' + namespace + '/memories/') for r in rows),
             'NATIVE_URI_SCOPE')
    else:
        raise ValueError('UNQUALIFIED_NATIVE_PROVIDER')
    need(selected_projection(selected) == expected[:10], 'LITERAL_RAW_LIMIT10_PREFIX')
    need(len({r['native_id'] for r in selected}) == len(selected), 'DUPLICATE_NATIVE_ID')
    return len(rows)


def verify_accounting(campaign, manifest, grant, binding, unit, request, response):
    with sqlite3.connect((campaign / 'ledger.sqlite').as_uri() + '?mode=ro&immutable=1', uri=True) as db:
        need(db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'LEDGER_INTEGRITY')
        need(db.execute('SELECT id,manifest_sha,closed FROM batch').fetchall() ==
             [(binding['execution_id'], sha(canonical(manifest)), 1)], 'CLOSED_EXECUTION_LEDGER')
        slots = db.execute('SELECT job,ordinal,request_sha,state,response_sha FROM slots ORDER BY ordinal').fetchall()
        need(len(slots) <= 60 and len({r[1] for r in slots}) == len(slots) and
             (unit['unit_id'], unit['batch_attempt_ordinal'], sha(request), 'COMPLETED', sha(response)) in slots,
             'FRESH_BATCH_SLOT_BINDING')
        previous = '0' * 64; events = []
        for payload, prior, digest in db.execute('SELECT payload,previous_sha,sha FROM events ORDER BY sequence'):
            need(prior == previous and digest == sha(prior.encode() + payload.encode()), 'LEDGER_EVENT_CHAIN')
            previous = digest; events.append(strict(payload))
        def selected(kind):
            return [e for e in events if e['kind'] == kind and e['value'].get('job') == unit['unit_id']]
        reserved, sends, done = (selected(k) for k in ('reservation', 'send-intent', 'model-completed'))
        need(len(reserved) == len(sends) == len(done) == 1 and
             reserved[0]['value']['request_sha'] == sha(request) and
             done[0]['value']['response_sha'] == sha(response), 'ONE_USE_ACCOUNTING')
        admitted = [e for e in selected('state') if e['value']['state'] == 'ADMITTED']
        custody = strict(raw(campaign / 'input-custody.json'))
        need(len(admitted) == 1 and admitted[0]['value']['evidence']['grant'] == custody['original_owner_grant'],
             'ORIGINAL_ADMISSION_IDENTITY')
        sent_at = datetime.fromisoformat(sends[0]['at'])
        need(datetime.fromisoformat(grant['not_before']) <= sent_at < datetime.fromisoformat(grant['expires']),
             'ORIGINAL_SEND_TIME_AUTHORITY')
    return {'ledger': identity(campaign / 'ledger.sqlite'), 'slot_count': len(slots),
            'unit_ordinal': unit['batch_attempt_ordinal'], 'send_at': sends[0]['at'],
            'global_lifetime_ordinal': 'NOT_ASSIGNED_HISTORICAL_INTERRUPTION_UNKNOWN'}


def inspect_capture(root, campaign, uid, review_path, accepted, pins_path):
    """Authentic-only admission; no externally supplied proposal or ACL accepted."""
    review, pins = review_contract(root, campaign, accepted, pins_path, review_path)
    sealed(campaign)
    manifest = strict(raw(campaign / 'batch.json'))
    grant = strict(raw(campaign / 'owner-authorization.json'))
    binding = strict(raw(campaign / 'execution-binding.json'))
    custody = verify_custody(campaign, manifest, grant, binding)
    verify_grant(root, campaign, manifest, grant, binding)
    unit = mapped_unit(manifest, binding, uid)
    native = campaign / 'units' / uid / 'native'; model = native.parent / 'model'
    mapping = strict(raw(native.parent / 'execution-unit.json'))
    need(mapping == {'source_manifest': custody['original_manifest'],
         'execution_binding': custody['original_execution_binding'], 'execution_id': binding['execution_id'],
         'source_unit_id': unit['source_unit_id'], 'execution_unit_id': uid,
         'prospective_attempt_id': unit['prospective_attempt_id']}, 'UNIT_MAPPING_RECEIPT')
    sealed(native / 'exercise'); sealed(native / 'reopen')
    job = strict(raw(native / 'job.json')); reopened = strict(raw(native / 'reopen/result.json'))
    need(reopened['status'] == 'COMPLETED' and reopened['job_sha256'] == sha(canonical(job)) and
         reopened['job_id'] == job['job_id'] == uid and job['batch_id'] == binding['execution_id'] and
         job['source_batch_id'] == manifest['batch_id'] and
         job['source_unit_id'] == unit['source_unit_id'] and
         job['source_prospective_attempt_id'] == unit['source_prospective_attempt_id'] and
         job['prospective_attempt_id'] == unit['prospective_attempt_id'] and
         job['execution_binding'] == custody['original_execution_binding'], 'NATIVE_EXECUTION_PROVENANCE')
    need(job['host_acl'] == reopened['host_acl'] == unit['host_acl'] and
         job['task'] == unit['task'] and job['purpose'] == 'AUTHORIZED_DEVELOPMENT_COLLECTION' and
         job['memories'] == unit['memories'] and job['provider'] == reopened['provider'] == unit['provider'] and
         job['provider_version'] == reopened['provider_version'] == unit['provider_version'],
         'INDEPENDENT_NATIVE_TASK_ACL_PROVIDER')
    need(type(reopened['internal_LLM_calls']) is int and reopened['internal_LLM_calls'] == 0 and
         type(reopened['downstream_Qwen_POSTs']) is int and reopened['downstream_Qwen_POSTs'] == 0 and
         reopened['mode'] == unit['provider_mode'] and
         ('internal_LLM_attempts' not in reopened or
          type(reopened['internal_LLM_attempts']) is int and reopened['internal_LLM_attempts'] == 0) and
         reopened['native_client_closed'] is True, 'NATIVE_NO_INTERNAL_MODEL_AND_CLOSE')
    for name, digest in job['source_files_sha256'].items():
        need(review['files_sha256'].get(name) == digest, 'QUALIFIED_NATIVE_SOURCE:' + name)
    for key in ('source_fixture', 'source_request_template'):
        verified_identity(unit[key])
    fixture = strict(raw(Path(unit['source_fixture']['path'])))
    acl = deepcopy(fixture['host_acl']); acl['principal']['subject'] = unit['host_acl']['principal']['subject']
    need(acl == unit['host_acl'] and fixture['task'] == unit['task'], 'INDEPENDENT_FIXTURE_ACL_TASK')
    request = raw(model / 'request.body.json'); response = raw(model / 'response.body.raw')
    receipt = strict(raw(model / 'receipt.json'))
    need(receipt['request_sha256'] == sha(request) and receipt['response_sha256'] == sha(response) and
         receipt['HTTP_status'] == 200 and receipt['entity_complete'] is True and
         receipt['slot_consumed'] is True and receipt['error'] is None and
         receipt['native_tool_execution'] == 'NEVER', 'COMPLETE_AUTHENTIC_TRANSPORT')
    need(reopened['bound_request_sha256'] == sha(request), 'NATIVE_REQUEST_BINDING')
    capture = native / 'reopen/capture'; selected = reopened['selected_context']
    captured = strict(raw(capture / 'retrieval/selected.json'))
    need(all(r['scope'] == unit['host_acl']['principal'] for r in captured) and
         selected_projection(captured) == selected_projection(selected), 'PASSIVE_SELECTED_SCOPE_AND_CONTENT')
    need(raw(capture / 'request.body') == request, 'PASSIVE_REQUEST_IDENTITY')
    count = verify_selection(unit['provider'], strict(raw(capture / 'retrieval/raw.bin')),
                             selected, unit['host_acl']['principal'], reopened, capture)
    template = strict(raw(Path(unit['source_request_template']['path'])))
    need(job['request_template'] == template, 'ORIGINAL_JOB_TEMPLATE')
    context = strict(template['messages'][1]['content'])
    context['retrieved_notes'] = [r['content'] for r in selected]
    template['messages'][1]['content'] = canonical(context).decode()
    need(canonical(template) == request and len(request) <= 16384, 'EXACT_NATIVE_CONTEXT_REQUEST')
    prompt = strict(raw(native.parent / 'prompt-admission.json'))
    need(prompt == strict(raw(native.parent / 'reference-tokens/tokens.json')) and
         prompt['request_sha256'] == sha(request) and prompt['request_bytes'] == len(request) and
         type(prompt['exact_reference_tokens']) is int and
         type(prompt['NFD_UTF8_token_upper_bound']) is int and
         0 <= prompt['exact_reference_tokens'] <= prompt['NFD_UTF8_token_upper_bound'] <= 32768 and
         prompt['deployed_server_identity'] == 'NOT_ATTESTED' and prompt['truncation'] is False,
         'GENUINE_LOCAL_REFERENCE_BOUND_NOT_REMOTE_CAP')
    profile = strict(raw(root / 'artifacts/tier-c-final-preparation-20261023-v1/dependencies/reference-profile-v2.json'))
    need(all(prompt[k] == profile[k] for k in ('embedded_template_sha256', 'render_arguments', 'renderer', 'packages')),
         'QUALIFIED_REFERENCE_PROFILE')
    module = load_file('cohort0_passive_inspector', root / 'src/memlife/research_collection.py')
    inspection = strict(raw(model / 'inspection.json'))
    need(module.inspect_response(response, expected_model='qwen-3.8-27b', output_ceiling=4096) == inspection and
         inspection['status'] == 'COMPLETED', 'STRICT_AUTHENTIC_RESPONSE_INSPECTION')
    parsed = strict(response); usage = parsed['usage']
    need(usage == receipt['usage'] == inspection['usage'] and
         all(type(usage[k]) is int and usage[k] >= 0 for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')) and
         usage['prompt_tokens'] + usage['completion_tokens'] == usage['total_tokens'] and
         usage['prompt_tokens'] <= 32768 and usage['completion_tokens'] <= 4096,
         'OBSERVED_USAGE_NOT_HARD_REMOTE_CAP')
    details = usage.get('completion_tokens_details')
    need(type(details) is dict and type(details.get('reasoning_tokens')) is int and
         0 <= details['reasoning_tokens'] <= usage['completion_tokens'], 'REASONING_ACCOUNTING')
    for key in ('provider_internal_requests', 'provider_internal_tokens'):
        need(type(usage.get(key, 0)) is int and usage.get(key, 0) == 0, 'INTERNAL_MODEL_USAGE')
    accounting = verify_accounting(campaign, manifest, grant, binding, unit, request, response)
    message = parsed['choices'][0]['message']; calls = message.get('tool_calls', [])
    need(calls == inspection['native_calls'], 'ORIGINAL_NATIVE_CALL_IDENTITY')
    # Accepted inspector already validates exact native call schema and duplicate-free arguments.
    return {'schema': SCHEMA, 'classification': 'AUTHENTIC_MODEL_PROPOSAL' if calls else 'AUTHENTIC_MODEL_NO_PROPOSAL',
            'unit_id': uid, 'scientific_unit_id': unit['source_unit_id'],
            'case_id': unit['case_id'], 'provider': unit['provider'], 'condition': unit['condition'],
            'native_calls': calls, 'host_acl': unit['host_acl'], 'usage': usage,
            'request': identity(model / 'request.body.json'), 'response': identity(model / 'response.body.raw'),
            'selected_context': identity(capture / 'retrieval/selected.json'),
            'raw_retrieval': identity(capture / 'retrieval/raw.bin'),
            'native_raw_candidates': count, 'selected_count': len(selected),
            'provider_internal_attempt_telemetry': reopened.get('internal_LLM_attempts', 'NOT_EXPOSED'),
            'provider_internal_call_count_reported': reopened['internal_LLM_calls'],
            'verified_provider_mode': reopened['mode'],
            'original_argument_strings': [c['function']['arguments'] for c in calls],
            'original_argument_sha256': [sha(c['function']['arguments'].encode()) for c in calls],
            'campaign_inventory': identity(campaign / 'inventory.json'), 'review': identity(review_path),
            'accounting': accounting, 'remote_hard_prompt_cap': 'NOT_GUARANTEED',
            'formal_generation_id': 'NOT_APPLICABLE_DEVELOPMENT_ONLY',
            'textual_content_classification': 'RESPONSE_FORMAT_ANOMALY' if not calls else 'NOT_APPLICABLE'}


def load_accepted(accepted, pins):
    """Separate package namespace, byte-pinned modules; no alternate implementation."""
    name = 'cohort0_accepted_f04'
    for suffix, rel in (('', 'src/memlife/__init__.py'),
                        ('.nlip', 'src/memlife/nlip/__init__.py')):
        spec = importlib.util.spec_from_file_location(name + suffix, accepted / rel,
                    submodule_search_locations=[str((accepted / rel).parent)])
        module = importlib.util.module_from_spec(spec); sys.modules[name + suffix] = module
        spec.loader.exec_module(module)
    modules = {}
    for leaf in ('auth', 'policy', 'security'):
        rel = 'src/memlife/nlip/' + leaf + '.py'
        need(sha(raw(accepted / rel)) == pins['files'][rel], 'UNCHANGED_PUBLIC_F04_GATE')
        modules[leaf] = load_file(name + '.nlip.' + leaf, accepted / rel)
    return modules


def _decision_only(capture, accepted, pins, workspace):
    """Public F04 gate only: no ProtectedDispatcher, sink, audit, or execution."""
    need(capture['schema'] == SCHEMA and capture['classification'] in
         {'AUTHENTIC_MODEL_PROPOSAL', 'AUTHENTIC_MODEL_NO_PROPOSAL'}, 'AUTHENTIC_ENROLLED_CAPTURE_REQUIRED')
    result = {'schema': SCHEMA, 'unit_id': capture['unit_id'], 'capture': capture,
              'classification': 'AUTHENTIC_PROPOSAL_TEST_ONLY_HOST_DECISION',
              'protected_dispatches': 0, 'synthetic_sink_writes': 0, 'external_calls': 0,
              'formal_result': 'NOT_PRODUCED', 'OFF': 'NOT_EVALUATED',
              'coverage': 'UNCHANGED_PUBLIC_AUTHORIZATION_GATE_ONLY_NO_ATOMIC_DISPATCH_OR_PROVENANCE_BRIDGE'}
    if not capture['native_calls']:
        result.update(status='NOT_APPLICABLE_NO_NATIVE_PROPOSAL', decision=None)
        return result
    modules = load_accepted(accepted, pins); auth, policy, security = (modules[k] for k in ('auth', 'policy', 'security'))
    acl = capture['host_acl']; principal_data = acl['principal']
    need(principal_data['subject'].startswith('SYNTHETIC_') and
         principal_data['project'] == acl['project'] and acl['revision'] == 2 and
         acl['session'] == 'FICTIONAL_LIVE_TEST_ONLY' and acl['authored_by'] == 'HOST_TEST_FIXTURE',
         'AUTHENTIC_INDEPENDENT_SYNTHETIC_HOST_ACL')
    principal = auth.Principal(principal_data['issuer'], principal_data['subject'])
    sessions = auth.SessionAuthority(clock=lambda: 1000)
    session = sessions.issue(auth.Identity(principal, 1900))
    need(sessions.live(principal, session), 'GENUINE_LIVE_TEST_SESSION')
    with tempfile.TemporaryDirectory(prefix='decision-only-', dir=workspace) as folder:
        admin = policy.PolicyAdmin.create(Path(folder) / 'policy.sqlite')
        admin.set_policy(principal, acl['project'], acl['before_recipients'], allowed=acl['principal_allowed'])
        admin.set_policy(principal, acl['project'], acl['current_recipients'], allowed=acl['principal_allowed'])
        store = policy.PolicyStore(admin.path); snapshot = store.current(principal, acl['project'])
        need(snapshot.revision == acl['revision'] and snapshot.recipients == frozenset(acl['current_recipients']) and
             snapshot.principal_allowed == acl['principal_allowed'] and not store.deliveries() and not store.audits(),
             'EXACT_INDEPENDENT_CURRENT_POLICY')
        need(len(capture['native_calls']) == 1, 'ONE_ORIGINAL_NATIVE_CALL')
        function = capture['native_calls'][0]['function']; arguments = strict(function['arguments'])
        before = sha(raw(admin.path)); start = time.perf_counter_ns()
        decision = security.authorize_tool_call(principal, session, function['name'], arguments, store)
        elapsed = time.perf_counter_ns() - start
        need(sha(raw(admin.path)) == before and not store.deliveries() and not store.audits(),
             'DECISION_ONLY_DATABASE_UNCHANGED_NO_SINK')
        result.update(status='EVALUATED_TEST_ONLY_DECISION', decision=decision.as_dict(), gate_latency_ns=elapsed,
                      policy_revision=snapshot.revision, protected_execution='NOT_PERFORMED')
    result['temporary_policy_database_removed'] = not Path(folder).exists()
    return result


def evaluate_decision(root, campaign, uid, review_path, accepted, pins_path, workspace):
    """Public entrypoint always performs authentic enrollment before evaluation."""
    capture = inspect_capture(root, campaign, uid, review_path, accepted, pins_path)
    return _decision_only(capture, accepted, strict(raw(pins_path)), workspace)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--campaign', type=Path, required=True)
    parser.add_argument('--accepted-source', type=Path, required=True)
    parser.add_argument('--accepted-pins', type=Path, required=True)
    parser.add_argument('--review', type=Path)
    parser.add_argument('--unit')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--review-request', action='store_true')
    args = parser.parse_args()
    need(not args.out.exists(), 'EXCLUSIVE_DERIVED_OUTPUT')
    args.out.mkdir(parents=True, mode=0o700)
    if args.review_request:
        save(args.out / 'review-request.json', {'schema': 'cohort0-f04-review-request-v1',
             'classification': 'PROSPECTIVE_NOT_ACCEPTED_NOT_ENROLLED',
             'files_sha256': required_sources(args.root, args.campaign),
             'campaign_inventory': identity(args.campaign / 'inventory.json'),
             'scientific_manifest': identity(args.campaign / 'batch.json'),
             'accepted_pins_manifest': identity(args.accepted_pins),
             'accepted_source_files': strict(raw(args.accepted_pins))['files']})
        return
    need(args.review is not None and args.unit, 'REVIEW_AND_UNIT_REQUIRED')
    try:
        result = evaluate_decision(args.root, args.campaign, args.unit, args.review,
                                   args.accepted_source, args.accepted_pins, args.out)
        save(args.out / 'authentic-enrollment.json', result['capture'])
        save(args.out / 'evaluation.json', result)
    except Exception as exc:
        save(args.out / 'blocked.json', {'schema': SCHEMA, 'unit_id': args.unit,
             'status': 'F04_BLOCKED', 'failed_gate': str(exc), 'exception': type(exc).__name__,
             'protected_dispatches': 0, 'external_calls': 0})
        raise


if __name__ == '__main__':
    main()
