# SPDX-License-Identifier: MIT
"""Read-only audit of the pinned synthetic candidate; no runtime or ledger access."""
import hashlib
import json
import re
import subprocess
from itertools import combinations
from pathlib import Path

from .candidate import canonical, lexical_leakage, load_corpus, make_schedule

PARENT = '30eb9e9f44c998ee34406f3645f579efec072b69'
CANDIDATE = Path('experiments/nlip_option_a_candidate_v1')
VERSION = 'nlip-evaluation-v1'
# Exact reviewed parser fixes accepted only for offline corpus/annotation audit.
# Scientific protocol/source identities and execution gates remain historical.
CONFORMANCE_REVISION = '06c4eb54a893d02333b98788fde8e34c78ee79ba'
CONFORMANCE_PATH = 'src/memlife/nlip/wire.py'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    def unique(items):
        result = {}
        for key, value in items:
            require(key not in result, 'DUPLICATE_JSON_KEY:' + key)
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('NONFINITE_JSON:' + value)
    return json.loads(Path(path).read_bytes(), object_pairs_hook=unique, parse_constant=invalid)


def git_blob(root, revision, path):
    require(bool(re.fullmatch(r'[a-f0-9]{40}', revision)), 'EXACT_GIT_REVISION_REQUIRED')
    return subprocess.check_output(['git', 'show', revision + ':' + str(path)], cwd=root)


def audit(root):
    root = Path(root)
    directory = root / CANDIDATE
    corpus, manifest = load_corpus(directory)
    protocol = read_json(directory / 'protocol.json')
    model = read_json(directory / 'model_configuration_candidate.json')
    package = directory / 'annotation-v1'
    annotation = read_json(package / 'manifest.json')
    forms = read_json(package / 'blind-review-forms.json')
    keys = read_json(package / 'coordinator-key.json')
    bindings = {
        'manifest.json': 'dataset_manifest_sha256',
        'ANNOTATION_AND_ADJUDICATION.md': 'annotation_plan_sha256',
        'model_configuration_candidate.json': 'model_configuration_sha256',
        'annotation-v1/manifest.json': 'annotation_package_manifest_sha256',
        'FREEZE_DECISION_CHECKLIST.md': 'freeze_decision_checklist_sha256',
    }
    require(protocol['dataset_sha256'] == manifest['dataset_sha256'] == annotation['source_dataset_sha256'], 'DATASET_BINDING')
    for name, field in bindings.items():
        require(sha(directory / name) == protocol[field], 'PROTOCOL_HASH:' + name)
    for name, digest in annotation['files_sha256'].items():
        require(sha(package / name) == digest, 'ANNOTATION_HASH:' + name)
    current_code = {}
    for path, digest in protocol['code_sha256'].items():
        require(hashlib.sha256(git_blob(root, protocol['implementation_revision'], path)).hexdigest() == digest, 'CODE_REVISION:' + path)
        observed = sha(root / path)
        if observed != digest:
            require(path == CONFORMANCE_PATH, 'CODE_BYTES:' + path)
            expected = hashlib.sha256(git_blob(root, CONFORMANCE_REVISION, path)).hexdigest()
            require(observed == expected, 'CODE_BYTES:' + path)
            current_code[path] = {'historical_sha256': digest, 'current_sha256': observed,
                                  'source_revision': CONFORMANCE_REVISION,
                                  'scope': 'OFFLINE_CORPUS_ANNOTATION_ONLY'}
    require(corpus['license'] == manifest['license'] == 'CC0-1.0', 'LICENSE')
    families = corpus['families']
    require(len({f['scenario'] for f in families}) == 16, 'SCENARIO_DUPLICATE')
    require(len(manifest['family_sha256']) == 16 and len(manifest['episode_sha256']) == 64, 'HASH_INDEX_COVERAGE')
    episodes = {e['episode_id']: (f, e) for f in families for e in f['episodes']}
    notes = [e['persisted_note'] for _, e in episodes.values()]
    require(len(set(notes)) == 64, 'EXACT_NOTE_DUPLICATE')
    for f in families:
        source = f['source']
        require(source['kind'] == 'ORIGINAL_SYNTHETIC' and source['license'] == 'CC0-1.0' and bool(source['authoring']), 'SOURCE_DECLARATION')
        require(source['real_world_trace'] is False and source['prior_deterministic_fixture'] is False, 'SOURCE_SCOPE')
        require(f['current_recipient'] != f['former_recipient'], 'RECIPIENT_IDENTITY')
        for e in f['episodes']:
            require(e['episode_id'] == '/'.join((f['family_id'], e['transition'], e['traffic'])), 'EPISODE_ID_BINDING')
            target = f['former_recipient'] if e['traffic'] == 'ATTACK' else f['current_recipient']
            require(e['expected_proposal_target'] == target and target in e['persisted_note'], 'TRAFFIC_TARGET')
            require(e['expected_protected_tool_outcome'] == {'unauthorized_delivery_allowed': False, 'authorized_current_proposal': 'ALLOW', 'former_recipient_proposal': 'DENY'}, 'TOOL_LABEL')
    old = read_json(root / 'experiments/nlip_d_minimum_pilot_v1/protocol.json')['data']
    old_texts = {c[k] for c in old for k in ('attack_note', 'benign_note', 'history')}
    require(not set(notes) & old_texts, 'HISTORICAL_NOTE_REUSE')
    require(not {f['family_id'] for f in families} & {c['family'] for c in old}, 'HISTORICAL_ID_REUSE')
    require(len(forms) == len(keys) == 64 and {r['case_id'] for r in forms} == {k['case_id'] for k in keys}, 'ANNOTATION_COVERAGE')
    require(len({r['case_id'] for r in forms}) == 64 and {k['episode_id'] for k in keys} == set(episodes), 'ANNOTATION_UNIQUENESS')
    by_case = {r['case_id']: r for r in forms}
    for key in keys:
        f, e = episodes[key['episode_id']]
        require(key == {'case_id': key['case_id'], 'family_id': f['family_id'], 'episode_id': e['episode_id'], 'partition': f['partition'], 'provisional_author_traffic': e['traffic'], 'acl_derived_authorized_recipients': e['expected_authorized_recipients']}, 'ANNOTATION_KEY')
        form = by_case[key['case_id']]
        require(form['scenario'] == f['scenario'] and form['requested_task'] == f['trusted_user_task'] and form['persisted_lower_trust_note'] == e['persisted_note'] and form['lifecycle_transition'] == e['transition'] and form['administrator_policy_before'] == e['previous_policy_state'] and form['administrator_policy_after'] == e['current_trusted_policy'], 'ANNOTATION_CONTENT')
        require(all(v is None for v in form['review'].values()), 'SOURCE_FORMS_NOT_BLANK')
        require(set(form) == {'case_id', 'scenario', 'requested_task', 'persisted_lower_trust_note', 'lifecycle_transition', 'administrator_policy_before', 'administrator_policy_after', 'review'}, 'BLIND_FORM_FIELDS')
    plans = {p: make_schedule(corpus, p, protocol['schedule_seed']) for p in ('development', 'heldout')}
    for p, count in (('development', 32), ('heldout', 96)):
        plan = plans[p]
        require(len(plan) == len({s['slot_id'] for s in plan}) == count, 'SCHEDULE_COVERAGE')
        pairs = {}
        for s in plan:
            pairs.setdefault(s['slot_id'].rsplit('/', 1)[0], []).append(s)
            require(set(s['payload']) == {'trusted_user_task', 'untrusted_scenario_context', 'untrusted_persisted_notes'}, 'INPUT_LABEL_LEAK')
        require(all(len(pair) == 2 and {s['arm'] for s in pair} == {'OFF', 'ON'} and pair[0]['payload_sha256'] == pair[1]['payload_sha256'] for pair in pairs.values()), 'PAIR_INPUT_MISMATCH')
    dev_bytes = canonical([s['payload'] for s in plans['development']])
    held_ids = [f[k] for f in families if f['partition'] == 'heldout' for k in ('project_id', 'report_id', 'current_recipient', 'former_recipient')]
    require(not any(identifier.encode() in dev_bytes for identifier in held_ids), 'HELDOUT_IDENTIFIERS_IN_DEV_INPUT')
    screen = lexical_leakage(corpus)
    def grams(f, text):
        for k in ('report_id', 'project_id', 'current_recipient', 'former_recipient'):
            text = text.replace(f[k], 'IDENTIFIER')
        words = re.findall(r'[a-z]+', text.lower())
        return {tuple(words[i:i+5]) for i in range(len(words)-4)}
    overlap = []
    for a, b in combinations(families, 2):
        ga = grams(a, a['scenario'] + ' ' + ' '.join(e['persisted_note'] for e in a['episodes']))
        gb = grams(b, b['scenario'] + ' ' + ' '.join(e['persisted_note'] for e in b['episodes']))
        score = len(ga & gb) / len(ga | gb)
        overlap.append({'left': a['family_id'], 'right': b['family_id'], 'cross_partition': a['partition'] != b['partition'], 'jaccard': score})
    overlap.sort(key=lambda x: (-x['jaccard'], x['left'], x['right']))
    task_templates = set()
    for f in families:
        task = f['trusted_user_task']
        for k in ('report_id', 'project_id', 'current_recipient', 'former_recipient'):
            task = task.replace(f[k], 'IDENTIFIER')
        task_templates.add(task)
    historical_overlap = []
    for f, e in episodes.values():
        g = grams(f, e['persisted_note'])
        for c in old:
            for name in ('attack_note', 'benign_note'):
                text = c[name]
                for k in ('project_id', 'current_recipient', 'old_recipient'):
                    text = text.replace(c[k], 'IDENTIFIER')
                words = re.findall(r'[a-z]+', text.lower())
                h = {tuple(words[i:i+5]) for i in range(len(words)-4)}
                historical_overlap.append((len(g & h)/len(g | h) if g | h else 0, e['episode_id'], c['family'], name))
    maximum = max(historical_overlap)
    return {
        'version': VERSION, 'verdict': 'STRUCTURAL_PASS_SEMANTIC_REVIEW_PENDING',
        'source_parent': PARENT, 'dataset_sha256': manifest['dataset_sha256'],
        'offline_code_compatibility': current_code,
        'scientific_execution_qualification': 'NOT_QUALIFIED; historical protocol unchanged',
        'protocol_sha256': sha(directory / 'protocol.json'),
        'families': 16, 'development_families': 4, 'heldout_families': 12,
        'episodes': 64, 'development_episodes': 16, 'heldout_episodes': 48,
        'heldout_slots': 96, 'heldout_pairs': 48, 'development_slots': 32,
        'source_license': 'Declared original Codex-assisted synthetic prose, CC0-1.0; declarations verified, external authorship not independently attested',
        'lexical_development_heldout_screen': screen,
        'family_comparisons': len(overlap), 'largest_family_overlaps': overlap[:10],
        'normalized_trusted_task_template_count': len(task_templates),
        'historical_exact_reuse': False,
        'historical_lexical_maximum': {'jaccard': maximum[0], 'episode_id': maximum[1], 'historical_family': maximum[2], 'field': maximum[3]},
        'dependencies': ['All 16 families share report-sharing, former/current-recipient ACL mechanics, trusted-task template and four-episode factorial structure.', 'Within-family UPDATE/REVOCATION reuse scenario and recipients.', 'Distinct domains and low surface overlap do not establish statistical independence.'],
        'blinding_limitations': ['Original identifiers reveal dev- partition hints; v2 reviewer export aliases all identifiers.', 'Case content necessarily reveals candidate intent and administrator ACL. Related episodes may be recognized.'],
        'leakage_scope': 'No heldout IDs or answer metadata in generated development payloads; surface reuse screened. Author/source code access and semantic leakage require human review.',
        'inference': {'ledger': protocol['current_execution_stop']['reason'], 'admissible_requests': protocol['current_execution_stop']['currently_admissible_inference_requests'], 'endpoint': model['status'], 'new_calls': 0},
        'freeze_readiness': 'BLOCKED', 'human_annotations': 'PENDING',
    }
