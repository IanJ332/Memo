"""Two-trajectory R2 scenario and offline custody checks, not a live controller.

No provider factory, Docker/SSH/model transport, owner grant or execution CLI.
QualifiedSession wraps an already admitted adapter/capture; future supervision
must verify runtime, external approval, ownership, deadlines and process receipts
before construction. Tests inject explicitly synthetic sessions only.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

_OFFLINE_DEPTH = 0


def _deny(event, args):
    if _OFFLINE_DEPTH and (event.startswith('socket.') or event in
                          ('subprocess.Popen', 'os.system', 'os.posix_spawn', 'os.exec')):
        raise PermissionError('R2_NETWORK_AND_PROCESS_DISPATCH_FORBIDDEN')


sys.addaudithook(_deny)

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT / 'manifests/r2-lifecycle-candidate-v1.json'
PINS = ROOT / 'manifests/r1-qualified-source-pins-v1.json'
DESIGN_SHA256 = '518a7ae2ed953663f774a3d17d5f95908b20a63e080245e302010f47db6bd33d'
PINS_SHA256 = '9780fc908fae6edd613377f1248463d69d3cda3b6216de73e5c39ee105fc5fa4'


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result, 'DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    return json.loads(Path(path).read_bytes(), object_pairs_hook=unique,
                      parse_constant=lambda _: need(False, 'NONFINITE_JSON'))


def save(path, value):
    """Exclusive durable scenario receipt; no overwrite, including partial runs."""
    path = Path(path)
    with path.open('xb') as stream:
        stream.write(canonical(value))
        stream.flush()
        os.fsync(stream.fileno())
    for directory in (path.parent, path.parent.parent):
        fd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    return {'path': path.name, 'sha256': sha(path.read_bytes())}


def design():
    need(sha(DESIGN.read_bytes()) == DESIGN_SHA256, 'CANDIDATE_DESIGN_DRIFT')
    value = read(DESIGN)
    need(value['retrieval']['limit'] == 10 and value['retrieval']['score_threshold'] is None,
         'FIXED_RETRIEVAL')
    return value


def qualified_sources(root):
    """Read-only check of existing accepted closure; never imports a provider."""
    root = Path(root).resolve()
    need(sha(PINS.read_bytes()) == PINS_SHA256, 'QUALIFIED_PINSET_DRIFT')
    pins = read(PINS)['files']
    for name, expected in pins.items():
        path = root / name
        need(not path.is_symlink() and path.resolve().is_relative_to(root), 'SOURCE_PATH')
        need(sha(path.read_bytes()) == expected, 'QUALIFIED_SOURCE_DRIFT:' + name)
    return sha(canonical(pins))


def store_paths(parent, condition):
    need(condition in ('UPDATE', 'DELETE'), 'CONDITION')
    parent = Path(parent)
    need(parent.is_absolute() and parent.resolve() == parent, 'CANONICAL_OWNED_PARENT')
    paths = {name: str(parent / condition / name) for name in ('qdrant', 'history', 'scratch')}
    for path in paths.values():
        need(Path(path).resolve() == Path(path), 'SYMLINK_STORE_PATH')
    return paths


def tree(root):
    """Exact membership and hashes, rejecting symbolic links and special files."""
    root = Path(root)
    need(root.is_dir() and not root.is_symlink(), 'STATE_DIRECTORY')
    rows = []
    for path in sorted(root.rglob('*')):
        need(not path.is_symlink(), 'SYMLINK_STATE')
        need(path.is_file() or path.is_dir(), 'SPECIAL_STATE_FILE')
        if path.is_dir():
            rows.append({'path': str(path.relative_to(root)), 'type': 'directory'})
        if path.is_file():
            need(path.stat().st_nlink == 1, 'HARDLINK_STATE')
            raw = path.read_bytes()
            rows.append({'path': str(path.relative_to(root)), 'type': 'file',
                         'bytes': len(raw), 'sha256': sha(raw)})
    return rows


def selected(raw, namespace):
    """Copy literal SDK candidates; no rank repair, deduplication or injection."""
    candidates = raw.get('results') if type(raw) is dict else raw
    need(type(candidates) is list and len(candidates) <= 10, 'CANDIDATES_SHAPE')
    ids, result = set(), []
    for rank, row in enumerate(candidates, 1):
        need(type(row) is dict and isinstance(row.get('id'), str)
             and row['id'] and row['id'] not in ids, 'CANDIDATE_ID')
        need(row.get('user_id') == namespace and isinstance(row.get('memory'), str),
             'CANDIDATE_SCOPE_CONTENT')
        ids.add(row['id'])
        result.append({'native_id': row['id'], 'content': row['memory'],
                       'native_user_id': row['user_id'], 'original_position_1based': rank})
    return {'selector': design()['retrieval']['selector'], 'selected': result,
            'context_sha256': sha(canonical(result)), 'MODEL_EXPOSURE': 'NOT_SENT',
            'MODEL_PROPOSAL': 'NOT_GENERATED'}


def score(observation, expected, reference):
    """Missing/error evidence cannot be counted as a mismatch or absence."""
    status = ('UNKNOWN' if observation is None else
              'OBSERVED_MATCH' if observation == expected else 'OBSERVED_MISMATCH')
    return {'status': status, 'evidence': reference, 'expected': expected,
            'observed': observation}


class QualifiedSession:
    """R2-specific bridge over unchanged qualified capture and adapter methods.

    The future admitted factory constructs ResearchCapture / Mem0MemoryAdapter
    under the qualified runtime guards. This bridge never constructs Mem0.
    """
    def __init__(self, adapter, record, namespace):
        from memlife.native_provider_capture import NativeLifecycleCapture, attach_mem0_capture
        from memlife.models.memory import WriteCommand, SupersedeCommand, DeleteCommand, QueryCommand
        self.commands = dict(ADD=WriteCommand, UPDATE=SupersedeCommand,
                             DELETE=DeleteCommand, SEARCH=QueryCommand)
        self.adapter, self.record, self.namespace = adapter, record, namespace
        def no_llm(*args, **kwargs):
            raise PermissionError('R2_INTERNAL_LLM_FORBIDDEN')
        adapter.native_memory.llm.generate_response = no_llm
        self.proxy = attach_mem0_capture(adapter, record)
        self.lifecycle = NativeLifecycleCapture(adapter, record, namespace=namespace)

    def call(self, operation, **kwargs):
        if operation in ('ADD', 'UPDATE', 'DELETE', 'SEARCH', 'INSPECT'):
            command = (self.commands[operation](namespace=self.namespace, **kwargs)
                       if operation != 'INSPECT' else None)
            result = self.lifecycle.step({'ADD': 'WRITE', 'SEARCH': 'QUERY'}.get(operation, operation), command)
            if operation == 'ADD':
                return result.memory_id
            if operation == 'SEARCH':
                raw = next(row for row in reversed(self.proxy.values) if row['method'] == 'search')
                candidates = raw['value']['results'] if type(raw['value']) is dict else raw['value']
                need([(r.memory_id, r.content, r.namespace) for r in result] ==
                     [(r['id'], r['memory'], r['user_id']) for r in candidates], 'LITERAL_ADAPTER_EXTRACTION')
                return deepcopy(raw['value'])
            return [r.model_dump(mode='json') for r in result] if operation == 'INSPECT' else None
        if operation == 'GET':
            return self.proxy.get(kwargs['memory_id'])
        if operation == 'GET_ALL':
            return self.proxy.get_all(filters={'user_id': self.namespace}, top_k=1000)
        if operation == 'HISTORY':
            return self.proxy.history(kwargs['memory_id'])
        raise ValueError('R2_OPERATION_ONLY')

    def write(self, name, value):
        return self.record._write('r2/' + name + '.json', canonical(value))

    def close(self):
        self.adapter.close()
        self.record._event('r2-client-closed', {'native_client_closed': True})
        self.record.finalize(cleanup_receipt_bytes=canonical({
            'native_client_closed': True, 'store_cleanup': 'FUTURE_CALLER_AFTER_SNAPSHOTS'}))


def checkpoint(session, condition, stage, ids, prior=None):
    """Six exact observations. A native exception halts; partial results survive."""
    fixture = design()
    observed, refs, outcomes = {}, {}, {}
    absent = condition == 'DELETE' and stage != 'baseline'
    expected_content = {role: row['before'] for role, row in fixture['records'].items()}
    if condition == 'UPDATE' and stage != 'baseline':
        expected_content['target'] = fixture['records']['target']['after']
    error = None
    for name, op, kwargs in (
        ('target', 'GET', {'memory_id': ids['target']}),
        ('sentinel', 'GET', {'memory_id': ids['sentinel']}),
        ('inventory', 'GET_ALL', {}),
        ('retrieval', 'SEARCH', {'query': fixture['retrieval']['query'], 'limit': 10}),
        ('history_target', 'HISTORY', {'memory_id': ids['target']}),
        ('history_sentinel', 'HISTORY', {'memory_id': ids['sentinel']}),
    ):
        if error:
            continue
        try:
            observed[name] = session.call(op, **kwargs)
            refs[name] = session.write(stage + '-' + name, observed[name])
        except Exception as exc:
            error = {'operation': name, 'class': type(exc).__name__, 'message': str(exc)}
            refs[name] = session.write(stage + '-error', error)
    for role in ('target', 'sentinel'):
        value = observed.get(role)
        valid = role in observed and (value is None or type(value) is dict)
        expect = None if role == 'target' and absent else expected_content[role]
        # Explicit successful Get(None) is absence; missing/error stays UNKNOWN.
        match = (value is None if expect is None else value is not None and
                 value.get('id') == ids[role] and value.get('user_id') == session.namespace
                 and value.get('memory') == expect and all(
                     value.get('metadata', {}).get(k) == v
                     for k, v in fixture['records'][role]['metadata'].items())) if valid else None
        outcomes[role + '_live'] = score(match, True, refs.get(role))
    if prior is not None:
        sentinel = observed.get('sentinel')
        old_sentinel = prior.get('sentinel')
        outcomes['sentinel_metadata_preserved'] = score(
            sentinel.get('metadata') if type(sentinel) is dict else None,
            old_sentinel.get('metadata') if type(old_sentinel) is dict else None,
            {'current': refs.get('sentinel'), 'prior_checkpoint': 'baseline' if stage == 'after' else 'after'})
    for layer in ('inventory', 'retrieval'):
        rows = observed.get(layer)
        rows = rows.get('results') if type(rows) is dict else rows
        valid = (type(rows) is list and all(type(r) is dict and isinstance(r.get('id'), str)
                 for r in rows)
                 and len({r['id'] for r in rows}) == len(rows))
        expected = {ids[role]: text for role, text in expected_content.items()
                    if not (role == 'target' and absent)}
        # Inventory is scoped top_k=1000 over two registered records, not a global enumeration claim.
        actual = {r['id']: r.get('memory') for r in rows} if valid else None
        outcomes[layer + '_live'] = score(actual, expected, refs.get(layer))
        outcomes[layer + '_scope'] = score(
            all(r.get('user_id') == session.namespace for r in rows) if valid else None,
            True, refs.get(layer))
    try:
        selection = selected(observed['retrieval'], session.namespace)
        refs['selection'] = session.write(stage + '-selection', selection)
        outcomes['literal_selection'] = score(True, True, refs['selection'])
    except (KeyError, ValueError, TypeError):
        outcomes['literal_selection'] = score(False if 'retrieval' in observed else None,
                                             True, refs.get('retrieval'))
        selection = None
    for role in ('target', 'sentinel'):
        key = 'history_' + role
        rows = observed.get(key)
        valid = type(rows) is list and bool(rows) and all(
            type(r) is dict and r.get('memory_id') == ids[role] for r in rows)
        outcomes[key] = score(valid if key in observed else None, True, refs.get(key))
        if prior is not None and (stage == 'reopened' or role == 'sentinel'):
            outcomes[key + '_persistent'] = score(rows, prior.get(key), refs.get(key))
    return {'stage': stage, 'raw': observed, 'references': refs, 'selection': selection,
            'outcomes': outcomes, 'error': error}


def verify_seal(folder, expected):
    folder = Path(folder)
    need(sha((folder / 'seal.json').read_bytes()) == expected, 'SEAL_DRIFT')
    seal = read(folder / 'seal.json')
    actual = [r for r in tree(folder) if r['path'] != 'seal.json']
    need(actual == seal['files'], 'SEALED_MEMBERSHIP_OR_BYTES')
    return read(folder / 'result.json')


def verify_reopen(folder, seal_hash, paths, process, bindings):
    prior = verify_seal(folder, seal_hash)
    need(prior['status'] == 'COMPLETED' and prior['closed'], 'INCOMPLETE_PRIOR_PHASE')
    need(prior['paths'] == paths and prior['bindings'] == bindings, 'REOPEN_PATH_SOURCE_RUNTIME_BINDING')
    need(prior['process'] != process, 'DISTINCT_PROCESS_REQUIRED')
    owner = Path(paths['qdrant']).parent
    tree(owner)  # Reject symlink/hardlink/special ownership markers too.
    need(read(owner / 'initial-claim.json') == {
        'output': str(folder), 'process': prior['process'], 'bindings': bindings}, 'STORE_OWNER_BINDING')
    need(prior['snapshots'] == {k: tree(v) for k, v in paths.items()}, 'PERSISTENT_STATE_DRIFT')
    return prior


def phase(*, parent, output, condition, reopen, process, bindings, factory,
          prior_folder=None, prior_seal=None, predecessor_seal=None):
    """Scenario function for a future admitted caller, fixtures in this task.

    Process must be a verified container ID (PID alone is insufficient). Bindings
    contain source/runtime/package identities verified by future supervision.
    No authorization is inferred from these arguments. No implicit retries.
    Factory is called only after fresh-store or exact reopen checks and claim.
    """
    global _OFFLINE_DEPTH
    paths = store_paths(parent, condition)
    need(isinstance(process, str) and bool(process), 'PROCESS_ID')
    need(set(bindings) == {'source', 'runtime', 'protocol'} and
         all(isinstance(v, str) and len(v) == 64 for v in bindings.values()), 'BOUND_IDENTITIES')
    need(bindings['protocol'] == sha(DESIGN.read_bytes()), 'PROTOCOL_BINDING')
    output = Path(output)
    need(output.is_absolute() and output.parent.is_dir(), 'EVIDENCE_PARENT')
    need(not output.is_relative_to(Path(parent)) and not Path(parent).is_relative_to(output),
         'SEPARATE_STORES_AND_EVIDENCE')
    phase_name = condition + ('-reopen' if reopen else '-initial')
    need(output.name == phase_name and output.resolve() == output, 'EXACT_PHASE_OUTPUT')
    ordinal = design()['phases'].index(phase_name)
    if ordinal:
        need(predecessor_seal is not None, 'PREDECESSOR_REQUIRED')
        expected = predecessor_seal
        for position in reversed(range(ordinal)):
            previous = verify_seal(output.parent / design()['phases'][position], expected)
            need(previous['closed'] and previous['status'] == 'COMPLETED'
                 and previous['process'] != process and previous['bindings'] == bindings,
                 'SERIAL_CLOSED_PREDECESSOR')
            expected = previous['predecessor_seal']
    prior = None
    if reopen:
        need(prior_folder is not None and prior_seal is not None, 'PRIOR_SEAL_REQUIRED')
        prior = verify_reopen(prior_folder, prior_seal, paths, process, bindings)
        need(prior['condition'] == condition and not prior['reopen'], 'EXACT_INITIAL_PHASE')
    else:
        need(not (Path(parent) / condition).exists(), 'FRESH_STORE_REQUIRED')
    output.mkdir()  # Exclusive durable no-replay claim precedes factory construction.
    save(output / 'claim.json', {'condition': condition, 'reopen': reopen, 'process': process,
                                'paths': paths, 'bindings': bindings,
                                'predecessor_seal': predecessor_seal, 'initial_seal': prior_seal})
    owned = Path(parent) / condition
    if not reopen:
        owned.mkdir()
    save(owned / ('reopen-claim.json' if reopen else 'initial-claim.json'),
         {'output': str(output), 'process': process, 'bindings': bindings})
    result = {'condition': condition, 'reopen': reopen, 'process': process, 'paths': paths,
              'bindings': bindings, 'status': 'INCOMPLETE', 'closed': False,
              'predecessor_seal': predecessor_seal, 'initial_seal': prior_seal,
              'checkpoints': {}, 'native_ids': prior['native_ids'] if prior else {},
              'MODEL_EXPOSURE': 'NOT_SENT', 'MODEL_PROPOSAL': 'NOT_GENERATED'}
    session = None
    _OFFLINE_DEPTH += 1
    try:
        session = factory(paths, output / 'capture')
        if isinstance(session, QualifiedSession):
            need({k: str(getattr(session.adapter.paths, k)) for k in paths} == paths,
                 'CONSTRUCTED_STORE_PATHS')
        need(session.namespace == 'npq-' + sha(canonical(design()['principal'])), 'HOST_NAMESPACE_MAPPING')
        ids = result['native_ids']
        fixture = design()
        if not reopen:
            need(not session.call('INSPECT'), 'EMPTY_FRESH_STORE')
            for role in ('target', 'sentinel'):
                row = fixture['records'][role]
                ids[role] = session.call('ADD', content=row['before'], metadata=row['metadata'])
                need(isinstance(ids[role], str) and ids[role], 'NATIVE_ID_REQUIRED')
            need(len(set(ids.values())) == 2, 'DISTINCT_NATIVE_IDS')
            result['checkpoints']['baseline'] = checkpoint(session, condition, 'baseline', ids)
            need(not result['checkpoints']['baseline']['error'], 'CHECKPOINT_ERROR_STOP')
            if condition == 'UPDATE':
                session.call('UPDATE', memory_id=ids['target'], content=fixture['records']['target']['after'],
                             metadata=fixture['records']['target']['metadata'])
            else:
                session.call('DELETE', memory_id=ids['target'])
            stage = 'after'
        else:
            stage = 'reopened'
        previous = (prior['checkpoints']['after']['raw'] if prior else
                    result['checkpoints']['baseline']['raw'])
        result['checkpoints'][stage] = checkpoint(session, condition, stage, ids, previous)
        need(not result['checkpoints'][stage]['error'], 'CHECKPOINT_ERROR_STOP')
        result['status'] = 'COMPLETED'  # Collection completion, never all-expectations-match.
    except Exception as exc:
        result['error'] = {'class': type(exc).__name__, 'message': str(exc)}
    finally:
        if session is not None:
            try:
                session.close()
                result['closed'] = True
            except Exception as exc:
                result['status'] = 'INCOMPLETE'
                result['close_error'] = {'class': type(exc).__name__, 'message': str(exc)}
        # Missing checkpoints remain explicit UNKNOWN; do not invent raw results.
        for stage in (('reopened',) if reopen else ('baseline', 'after')):
            if stage not in result['checkpoints']:
                result['checkpoints'][stage] = {'outcomes': {'checkpoint': score(None, 'COMPLETE', None)}}
        if result['closed']:
            try:
                result['snapshots'] = {k: tree(v) for k, v in paths.items()}
                for name, path in paths.items():
                    shutil.copytree(path, output / ('snapshot-' + name))
                    need(tree(output / ('snapshot-' + name)) == result['snapshots'][name], 'SNAPSHOT_COPY_DRIFT')
                    for copied in (output / ('snapshot-' + name)).rglob('*'):
                        if copied.is_file():
                            with copied.open('rb') as stream:
                                os.fsync(stream.fileno())
                    directories = [output / ('snapshot-' + name)] + [
                        p for p in (output / ('snapshot-' + name)).rglob('*') if p.is_dir()]
                    for directory in reversed(directories):
                        fd = os.open(directory, os.O_RDONLY)
                        try:
                            os.fsync(fd)
                        finally:
                            os.close(fd)
            except Exception as exc:
                result['status'] = 'INCOMPLETE'
                result['snapshot_error'] = {'class': type(exc).__name__, 'message': str(exc)}
        try:
            save(output / 'result.json', result)
            seal = save(output / 'seal.json', {'files': tree(output)})
        finally:
            _OFFLINE_DEPTH -= 1
    return result, seal['sha256']


def cleanup_candidates(parent, sealed_phases):
    """Validate exact owned directories for future cleanup; does not delete anything.

    Require final reopen receipts for both stores and reverify snapshots. Caller
    still needs deadline/ownership/container cleanup approval and removal receipts.
    """
    need(set(sealed_phases) == {'UPDATE', 'DELETE'}, 'BOTH_FINAL_PHASES')
    result = []
    for condition in ('UPDATE', 'DELETE'):
        folder, expected = sealed_phases[condition]
        prior = verify_seal(folder, expected)
        paths = store_paths(parent, condition)
        need(prior['condition'] == condition and prior['reopen'] and prior['closed']
             and prior['status'] == 'COMPLETED' and prior['paths'] == paths, 'OWNED_CLOSED_FINAL_PHASE')
        need(prior['snapshots'] == {k: tree(v) for k, v in paths.items()}, 'CLEANUP_STATE_DRIFT')
        owned = Path(parent) / condition
        tree(owned)
        need({p.name for p in owned.iterdir()} == {
            'qdrant', 'history', 'scratch', 'initial-claim.json', 'reopen-claim.json'}, 'EXACT_OWNED_MEMBERSHIP')
        need(read(owned / 'reopen-claim.json') == {
            'output': str(folder), 'process': prior['process'], 'bindings': prior['bindings']},
            'CLEANUP_OWNER_BINDING')
        result.append(str(Path(parent) / condition))
    return result
