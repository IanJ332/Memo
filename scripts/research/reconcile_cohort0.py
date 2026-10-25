#!/usr/bin/env python3
"""Read-only Cohort 0 reconciliation; emits IDs, hashes and aggregates, never notes.

Use --root for an authoritative checkout and --output for a new derived JSON file.
No network, inference, or provider operations. The Wilcoxon values are descriptive:
request duplication and shared case clusters invalidate a naive independent-trials
interpretation. Exact conditional signs additionally assume symmetric independent
nonzero differences and therefore are not publication-ready causal inference.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import statistics
import zipfile

MANIFEST = 'manifests/tier-c-bounded-execution-20261023-v1.json'
CAMPAIGN = 'artifacts/tier-c-metadata-campaign-20261024-v1/TCEX-20261024-03'
ZIP = '.local/research-exports/20261024-v1/MemLife_Research_Evidence_20261024.zip'
PINS = {
    'manifest': '563fdb5e5fe9b74afc15cff444ff282ba046dddc71a8b21e8e24e0c027751fc6',
    'inventory': 'c0f34dbe797b2b4c4ffca5354ac4eb6fb448f45cd81a86fe212d16812e8ac22b',
    'zip': '27632cd157254b982d9b71e5981af66a137f6b68f69442b625c671d18f01a41e',
    'integrity/FILE_MANIFEST.json': '82c6e3c9eca1c729e0ab2c7c5129f5553ccefc51945edd625926d102fe7afac2',
    'integrity/SHA256SUMS.txt': '2b9e51e0e00c71cf4f9df322e1808f129c1c8635a210343214ebdcbcda76ae5a',
}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def load(path):
    return json.loads(path.read_bytes())

def safe_member(root, name):
    p = PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or '\\' in name:
        raise ValueError('unsafe evidence member')
    result = root.joinpath(*p.parts)
    if any(parent.is_symlink() for parent in [result, *result.parents] if parent != root and root in parent.parents):
        raise ValueError('symlink evidence member')
    return result

def verify_inventory(root, expected=None):
    raw = (root / 'inventory.json').read_bytes()
    if expected and sha(raw) != expected:
        raise ValueError('inventory identity mismatch')
    records = json.loads(raw)['files']
    seen = set()
    for row in records:
        name = row['path']
        if name in seen:
            raise ValueError('duplicate inventory member')
        seen.add(name)
        body = safe_member(root, name).read_bytes()
        if len(body) != row['bytes'] or sha(body) != row['sha256']:
            raise ValueError('evidence integrity mismatch: ' + name)
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if actual != seen | {'inventory.json'}:
        raise ValueError('inventory membership mismatch')
    return {'sha256': sha(raw), 'verified_files': len(records)}

def verify_export(path):
    if sha(path.read_bytes()) != PINS['zip']:
        raise ValueError('archive identity mismatch')
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if len(names) != len(set(names)):
            raise ValueError('duplicate archive member')
        matches = [n for n in names if n.endswith('/integrity/FILE_MANIFEST.json')]
        if len(matches) != 1:
            raise ValueError('ambiguous archive root')
        prefix = matches[0][:-len('integrity/FILE_MANIFEST.json')]
        for member in ('integrity/FILE_MANIFEST.json', 'integrity/SHA256SUMS.txt'):
            if sha(z.read(prefix + member)) != PINS[member]:
                raise ValueError('archive internal identity mismatch')
        sums = z.read(prefix + 'integrity/SHA256SUMS.txt').decode().splitlines()
        checked_names = set()
        for line in sums:
            digest, name = line.split('  ', 1)
            if name in checked_names:
                raise ValueError('duplicate archive checksum member')
            checked_names.add(name)
            if sha(z.read(prefix + name)) != digest:
                raise ValueError('archive payload mismatch')
        fm = json.loads(z.read(prefix + 'integrity/FILE_MANIFEST.json'))
        payload_names = set()
        for row in fm['files']:
            name = row['path']
            if name in payload_names:
                raise ValueError('duplicate indexed archive payload')
            payload_names.add(name)
            body = z.read(prefix + name)
            if len(body) != row['bytes'] or sha(body) != row['sha256']:
                raise ValueError('indexed archive payload mismatch')
        if len(fm['files']) != 20929 or len(sums) != 20931 or len(names) != 20932:
            raise ValueError('archive membership count differs from authoritative identities')
        return {'sha256': PINS['zip'], 'entries': len(names),
                'checksum_entries': len(sums), 'file_manifest_sha256': PINS['integrity/FILE_MANIFEST.json'],
                'sha256sums_sha256': PINS['integrity/SHA256SUMS.txt'],
                'indexed_payload_files': len(fm['files'])}

def wilcoxon(differences):
    """Two-sided signed-rank: wilcox zeros; average ties; normal and exact signs.

    Exact uses a subset-sum DP over doubled average ranks; unlike untied-rank
    lookup this respects actual ties. Includes observed-tail equality, no mid-p.
    Normal approximation uses tie-corrected variance and no continuity correction.
    """
    values = [v for v in differences if v != 0]
    if not values:
        return {'n_nonzero': 0, 'zeros_removed': len(differences), 'W_plus': 0,
                'W_minus': 0, 'p_normal_no_continuity': None, 'p_exact_conditional_signs': 1.0,
                'method': 'degenerate: no nonzero differences; no informative normal statistic'}
    absolute = sorted(abs(v) for v in values)
    ranks = {v: sum(i + 1 for i, x in enumerate(absolute) if x == v) / absolute.count(v)
             for v in set(absolute)}
    weights = [int(2 * ranks[abs(v)]) for v in values]
    plus = sum(ranks[abs(v)] for v in values if v > 0)
    n = len(values)
    total = n * (n + 1) / 2
    variance = n * (n + 1) * (2 * n + 1) / 24 - sum(t ** 3 - t for t in Counter(absolute).values()) / 48
    distribution = Counter({0: 1})
    for weight in weights:
        nxt = distribution.copy()
        for s, count in distribution.items():
            nxt[s + weight] += count
        distribution = nxt
    small = round(2 * min(plus, total - plus))
    exact = min(1.0, 2 * sum(count for s, count in distribution.items() if s <= small) / 2 ** n)
    return {'n_nonzero': n, 'zeros_removed': len(differences) - n,
            'W_plus': plus, 'W_minus': total - plus, 'variance_tie_corrected': variance,
            'absolute_rank_tie_sizes': sorted(t for t in Counter(absolute).values() if t > 1),
            'p_normal_no_continuity': math.erfc(abs(plus - total / 2) / math.sqrt(2 * variance)),
            'p_normal_continuity_0_5': math.erfc(max(0, abs(plus - total / 2) - .5) / math.sqrt(2 * variance)),
            'p_exact_conditional_signs': exact,
            'method': 'two-sided; wilcox zero removal; average tied ranks; conditional exact sign subset sums; normal tie correction; no independence claim'}

def describe(values):
    return {'n': len(values), 'mean': statistics.mean(values) if values else None,
            'median': statistics.median(values) if values else None,
            'sum': sum(values), 'sample_sd': statistics.stdev(values) if len(values) > 1 else None}

def paired(rows):
    groups = defaultdict(dict)
    for row in rows:
        if row['status'] == 'COMPLETE':
            if row['condition'] in groups[row['pair_id']]:
                raise ValueError('duplicate matched condition')
            groups[row['pair_id']][row['condition']] = row
    results = []
    for pair_id, group in groups.items():
        if set(group) == {'CONTROL', 'CONFLICT'}:
            a, b = group['CONTROL'], group['CONFLICT']
            if (a['case_id'], a['provider']) != (b['case_id'], b['provider']):
                raise ValueError('inconsistent matched group')
            results.append({'pair_id': pair_id, 'case_id': a['case_id'], 'provider': a['provider'],
                            'control_unit': a['unit'], 'conflict_unit': b['unit'],
                            'reasoning_difference': b['reasoning_tokens'] - a['reasoning_tokens']})
    return results

def reconcile(root):
    manifest_bytes = (root / MANIFEST).read_bytes()
    if sha(manifest_bytes) != PINS['manifest']:
        raise ValueError('scientific manifest identity mismatch')
    manifest = json.loads(manifest_bytes)
    campaign = root / CAMPAIGN
    integrity = verify_inventory(campaign, PINS['inventory'])
    archive = verify_export(root / ZIP)
    rows = []
    for i, unit in enumerate(manifest['units'], 1):
        name = 'TCEX-20261024-03-' + str(i).zfill(3)
        directory = campaign / 'units' / name
        req, response = directory / 'model/request.body.json', directory / 'model/response.body.raw'
        row = {'unit': name, 'case_id': unit['case_id'], 'family': unit['family'],
               'provider': unit['provider'], 'condition': unit['condition'], 'pair_id': unit['pair_id'],
               'status': 'NOT_STARTED', 'request_sha256': sha(req.read_bytes()) if req.exists() else None}
        if req.exists():
            row['status'] = 'UNKNOWN_RESPONSE'
        if response.exists() and response.stat().st_size:
            raw = response.read_bytes()
            record = json.loads(raw)
            usage = record['usage']
            numbers = [usage['prompt_tokens'], usage['completion_tokens'], usage['total_tokens'],
                       usage['completion_tokens_details']['reasoning_tokens']]
            if any(type(n) is not int or n < 0 for n in numbers) or numbers[0] + numbers[1] != numbers[2] or numbers[3] > numbers[1]:
                raise ValueError('inconsistent usage')
            if record['model'] != 'qwen-3.8-27b' or len(record['choices']) != 1:
                raise ValueError('response identity/choice mismatch')
            choice = record['choices'][0]
            row.update(status='COMPLETE', response_sha256=sha(raw),
                       prompt_tokens=numbers[0], completion_tokens=numbers[1], total_tokens=numbers[2],
                       reasoning_tokens=numbers[3], native_tool_call_count=len(choice['message'].get('tool_calls') or []),
                       finish_reason=choice['finish_reason'])
        rows.append(row)
    pairs = paired(rows)
    differences = [p['reasoning_difference'] for p in pairs]
    clusters = []
    for case in sorted({p['case_id'] for p in pairs}):
        group = [p for p in pairs if p['case_id'] == case]
        clusters.append({'case_id': case, 'complete_provider_pairs': len(group),
                         'mean_reasoning_difference': statistics.mean(p['reasoning_difference'] for p in group)})
    complete = [r for r in rows if r['status'] == 'COMPLETE']
    conditions = {c: describe([r['reasoning_tokens'] for r in complete if r['condition'] == c]) for c in ['CONTROL', 'CONFLICT']}
    eq = defaultdict(list)
    for row in rows:
        if row['request_sha256']:
            eq[row['request_sha256']].append(row['unit'])
    provider = {}
    for p in sorted({r['provider'] for r in rows}):
        rs = [r for r in complete if r['provider'] == p]
        ds = [x['reasoning_difference'] for x in pairs if x['provider'] == p]
        provider[p] = {'completed_units': len(rs), 'complete_pairs': len(ds),
                       'reasoning_by_condition': {c: describe([r['reasoning_tokens'] for r in rs if r['condition'] == c]) for c in conditions},
                       'paired_difference': describe(ds), 'positive_pairs': sum(d > 0 for d in ds)}
    return {'schema': 'MEMLIFE_COHORT0_RECONCILIATION_V1', 'cohort': 'Prompt-Specified Baseline',
            'source_manifest_sha256': PINS['manifest'], 'source_campaign_inventory': integrity, 'archive_integrity': archive,
            'interpretation': 'Exploratory descriptions only. Shared byte-identical requests and case clusters prevent treating provider pairs as independent causal trials. No F04 decisions inferred from ACL matching.',
            'units': rows, 'complete_units': len(complete), 'missingness': dict(Counter(r['status'] for r in rows)),
            'native_tool_proposals': sum(r['native_tool_call_count'] for r in complete),
            'completed_without_native_tool': [r['unit'] for r in complete if not r['native_tool_call_count']],
            'complete_pairs': pairs, 'positive_pairs': sum(d > 0 for d in differences), 'negative_pairs': sum(d < 0 for d in differences),
            'reasoning_by_condition': conditions, 'unpaired_mean_ratio_conflict_to_control': conditions['CONFLICT']['mean'] / conditions['CONTROL']['mean'],
            'paired_difference': describe(differences), 'wilcoxon_descriptive': wilcoxon(differences),
            'case_clusters': clusters, 'positive_case_clusters': sum(c['mean_reasoning_difference'] > 0 for c in clusters),
            'provider_descriptive': provider, 'request_equivalence_groups': [{'request_sha256': h, 'units': ids} for h, ids in sorted(eq.items())],
            'distinct_request_bodies': len(eq), 'request_group_size_counts': dict(Counter(map(len, eq.values()))),
            'known_usage': {key: sum(r[key] for r in complete) for key in ['prompt_tokens', 'completion_tokens', 'reasoning_tokens', 'total_tokens']},
            'F04': 'NOT_INFERRED_REQUIRES_INDEPENDENT_AUTHENTIC_ENROLLMENT_AND_TEST_ONLY_EVALUATION'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = reconcile(args.root.resolve())
    data = json.dumps(result, indent=2, sort_keys=True).encode() + b'\n'
    with args.output.open('xb') as stream:
        stream.write(data)
    print(json.dumps({'result_sha256': sha(data), 'complete_units': result['complete_units'], 'complete_pairs': len(result['complete_pairs'])}))

if __name__ == '__main__':
    main()
