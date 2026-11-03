# SPDX-License-Identifier: MIT
"""Calculator-only outcomes. Never dispatches a tool or invokes a model."""
import copy
from pathlib import Path

from .candidate import load_corpus, make_schedule
from .scientific_audit import CANDIDATE, PARENT, read_json, sha
from .annotation_coordinator import write_new

SCENARIOS = ('perfect_blocking', 'complete_defense_failure', 'false_positive_rejection',
             'missing_off', 'missing_on', 'invalid_pairing', 'duplicate_observation_id',
             'cluster_dependence', 'timeout_unknown_sink', 'timeout_known_empty_sink',
             'provider_error', 'unknown_usage', 'zero_event', 'malformed_output',
             'malformed_results', 'refusal', 'invalid_native_pairing')


def receipt(root):
    directory = Path(root) / CANDIDATE
    corpus, manifest = load_corpus(directory)
    protocol = read_json(directory / 'protocol.json')
    model = read_json(directory / 'model_configuration_candidate.json')
    return {'schema_version': 'nlip-result-receipt-v1', 'evidence_kind': 'ANALYSIS_TEST_ONLY',
            'attempt_id': 'ANALYSIS_TEST_ONLY-calculator-v1', 'partition': 'heldout',
            'protocol_id': protocol['protocol_id'], 'protocol_sha256': sha(directory / 'protocol.json'),
            'dataset_id': corpus['dataset_id'], 'dataset_sha256': manifest['dataset_sha256'],
            'implementation_revision': protocol['implementation_revision'], 'tested_git_revision': PARENT,
            'source_sha256': protocol['code_sha256'], 'model_configuration_sha256': sha(directory / 'model_configuration_candidate.json'),
            'model_identifier': model['model_identifier'], 'model_snapshot': model['model_version_or_snapshot'],
            'ledger_uuid': '00000000-0000-0000-0000-000000000000', 'ledger_identity_sha256': '0'*64, 'retry_count': 0}


def outcomes(root, receipt_path, scenario='perfect_blocking'):
    if scenario not in SCENARIOS:
        raise ValueError('UNKNOWN_TEST_SCENARIO')
    corpus, _ = load_corpus(Path(root) / CANDIDATE)
    protocol = read_json(Path(root) / CANDIDATE / 'protocol.json')
    config = read_json(Path(root) / CANDIDATE / 'model_configuration_candidate.json')
    families = {f['family_id']: f for f in corpus['families']}
    rows = []
    for i, slot in enumerate(make_schedule(corpus, 'heldout', protocol['schedule_seed']), 1):
        f = families[slot['family_id']]
        target = f['former_recipient'] if slot['traffic'] == 'ATTACK' else f['current_recipient']
        deny = slot['traffic'] == 'ATTACK' and slot['arm'] == 'ON'
        row = {**{k: slot[k] for k in ('slot_id', 'family_id', 'partition', 'transition', 'traffic', 'arm', 'episode_sha256')},
               'schema_version': 'nlip-result-row-v1', 'receipt_sha256': sha(receipt_path),
               'evidence_kind': 'ANALYSIS_TEST_ONLY', 'observation_id': 'ANALYSIS_TEST_ONLY-' + str(i),
               'planned_payload_sha256': slot['payload_sha256'], 'request_payload_sha256': slot['payload_sha256'],
               'send_ordinal': i, 'model_status': 'TOOL_CALL', 'returned_model': config['model_identifier'],
               'proposal': {'tool': 'send_report', 'arguments': {'project_id': f['project_id'], 'recipient': target}},
               'security_decision': {'action': 'DENY' if deny else 'ALLOW', 'reason': 'ANALYSIS_TEST_ONLY', 'policy_revision': 2},
               'sink_status': 'KNOWN', 'sink_rows': [] if deny else [{'invocation': 'ANALYSIS_TEST_ONLY-' + str(i), 'project_id': f['project_id'], 'recipient': target}],
               'usage_status': 'KNOWN', 'usage': {'input_tokens': 0, 'output_tokens': 0, 'provider_internal_requests': 0, 'provider_internal_tokens': 0},
               'end_to_end_latency_ns': 0, 'retry_count': 0, 'evidence_file': None, 'evidence_sha256': None}
        rows.append(row)
    attack_on = next(r for r in rows if r['traffic'] == 'ATTACK' and r['arm'] == 'ON')
    def clear(row, status):
        row.update(model_status=status, returned_model=None, proposal=None, security_decision=None, sink_rows=[])
    if scenario == 'complete_defense_failure':
        for r in rows:
            if r['traffic'] == 'ATTACK' and r['arm'] == 'ON':
                f = families[r['family_id']]
                r['security_decision']['action'] = 'ALLOW'
                r['sink_rows'] = [{'invocation': r['observation_id'], 'project_id': f['project_id'], 'recipient': f['former_recipient']}]
    elif scenario == 'false_positive_rejection':
        for r in rows:
            if r['traffic'] == 'BENIGN' and r['arm'] == 'ON':
                r['security_decision']['action'] = 'DENY'; r['sink_rows'] = []
    elif scenario in {'missing_off', 'missing_on'}:
        arm = 'OFF' if scenario == 'missing_off' else 'ON'
        rows.remove(next(r for r in rows if r['traffic'] == 'ATTACK' and r['arm'] == arm))
    elif scenario == 'invalid_pairing':
        rows[0]['family_id'] = rows[1]['family_id'] + '-invalid'
    elif scenario == 'duplicate_observation_id':
        rows[1]['observation_id'] = rows[0]['observation_id']
    elif scenario == 'cluster_dependence':
        for r in rows:
            if r['traffic'] == 'ATTACK' and r['family_id'] in sorted(families)[:8]:
                clear(r, 'NO_TOOL_CALL'); r['returned_model'] = config['model_identifier']
    elif scenario.startswith('timeout_'):
        clear(attack_on, 'TIMEOUT')
        attack_on['usage_status'] = 'UNKNOWN'; attack_on['usage'] = dict.fromkeys(attack_on['usage'])
        if scenario == 'timeout_unknown_sink':
            attack_on.update(sink_status='UNKNOWN', sink_rows=None)
    elif scenario in {'provider_error', 'unknown_usage'}:
        clear(attack_on, 'PROVIDER_ERROR' if scenario == 'provider_error' else 'USAGE_UNKNOWN')
        attack_on['usage_status'] = 'UNKNOWN'; attack_on['usage'] = dict.fromkeys(attack_on['usage'])
    elif scenario in {'zero_event', 'refusal'}:
        for r in rows:
            clear(r, 'NO_TOOL_CALL' if scenario == 'zero_event' else 'REFUSAL')
            r['returned_model'] = config['model_identifier']
    elif scenario == 'malformed_output':
        clear(attack_on, 'MALFORMED'); attack_on['proposal'] = {'unparsed': 'ANALYSIS_TEST_ONLY-invalid'}
    elif scenario == 'malformed_results':
        rows[0]['sink_rows'] = 'false'
    elif scenario == 'invalid_native_pairing':
        rows[0]['request_payload_sha256'] = 'f'*64
    return copy.deepcopy(rows)
