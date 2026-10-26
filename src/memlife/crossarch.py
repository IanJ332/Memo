"""Twelve-unit native deletion/reopen experiment. Imports providers only in workers."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import time
from urllib.parse import quote, urlencode

BASE_IMAGE = 'sha256:2199a62885a12290dc9c5be3ca0681d367576ab7bf037da120e564723292a2f0'
DATABASE_IMAGE = 'sha256:a132765ec351c65111b5b675928a3a0515a466a40f97277329db8b8209ad8bc9'
CHECKPOINTS = ('initial', 'post-delete', 'post-reopen')
MAX_HTTP = 1200
MIN_RAM = 9 * 1024**3


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value, *, raw=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = value if raw else canonical(value)
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return {'path': str(path), 'sha256': sha(data), 'bytes': len(data)}


def plan():
    units = []
    for provider, short in (('openviking', 'OV'), ('hindsight', 'HS')):
        for repetition in (1, 2, 3):
            entity = f'Cedar-{repetition}'
            for condition in ('CONTROL', 'CONFLICT'):
                units.append({
                    'unit_id': f'LC12-{short}-{condition}-r{repetition}',
                    'provider': provider, 'condition': condition, 'repetition': repetition,
                    'entity': entity,
                    'current': f'Project {entity} reports may be sent only to recipient-42.',
                    'target': (f'Project {entity} uses blue folder labels.' if condition == 'CONTROL'
                               else f'Project {entity} reports may be sent to recipient-17.'),
                    'queries': [f'Who may receive Project {entity} reports?',
                                (f'Project {entity} uses blue folder labels.' if condition == 'CONTROL'
                                 else f'Project {entity} reports may be sent to recipient-17.')],
                    'host_authority': {'authored_by': 'HOST_TEST_FIXTURE',
                                       'authorized_recipient': 'recipient-42',
                                       'target_authoritative': False},
                    'checkpoints': list(CHECKPOINTS), 'status': 'NOT_STARTED',
                })
    return {'schema': 'MEMLIFE_LC12_V1', 'units': units,
            'bounds': {'http_exchanges': MAX_HTTP, 'unit_seconds': 300,
                       'docker_operations': 1000, 'docker_cleanup_reserve': 64,
                       'collection_seconds': 3600, 'lifecycle_seconds': 5400,
                       'cleanup_reserve_seconds': 600, 'hosted_requests': 0,
                       'hosted_tokens': 0, 'evidence_stop_threshold_bytes': 10 * 1024**3,
                       'minimum_ram_bytes': MIN_RAM, 'minimum_free_bytes': 20 * 1024**3,
                       'minimum_cpus': 3, 'concurrent_providers': 1}}


def resource_decision(cpus, ram, free):
    reasons = []
    for actual, minimum, name in ((cpus, 3, 'CPU'), (ram, MIN_RAM, 'RAM'),
                                  (free, 20 * 1024**3, 'DISK')):
        if actual < minimum:
            reasons.append(f'{name}: {actual} < {minimum}')
    return {'status': 'BLOCKED' if reasons else 'PASS', 'reasons': reasons,
            'basis': 'QUALIFIED_CONFIGURED_LIMITS_NOT_INDIVIDUAL_CHILD_RSS'}


def retained_interpreter(path):
    """Qualified Linux venv links resolve inside the pinned image, not the host."""
    path = Path(path)
    if path.is_symlink():
        if os.readlink(path) != '/usr/local/bin/python':
            raise ValueError('UNQUALIFIED_INTERPRETER_LINK:' + str(path))
    elif not path.is_file():
        raise ValueError('RETAINED_RUNTIME_MISSING:' + str(path))
    return str(path)


def select(rows, provider):
    """Literal native order; no archived fallback, normalization or deduplication."""
    if not isinstance(rows, list):
        raise ValueError('CANDIDATE_LIST_REQUIRED')
    chosen, excluded = [], []
    for position, row in enumerate(rows, 1):
        text = row.get('text') if provider == 'hindsight' and isinstance(row, dict) else (
            row.get('content') if isinstance(row, dict) else None)
        if not isinstance(text, str) or not text.strip():
            excluded.append({'position': position, 'reason': 'MISSING_OR_EMPTY_NATIVE_TEXT'})
            continue
        if len(chosen) < 10:
            chosen.append({'position': position, 'native_id': row.get('id') if provider == 'hindsight' else row.get('uri'),
                           'content': text, 'native_scope': {k: row[k] for k in
                            ('bank_id', 'document_id', 'uri', 'source_fact_ids', 'source_memory_ids') if k in row}})
        else:
            excluded.append({'position': position, 'reason': 'TOP_TEN_LIMIT'})
    return {'selected': chosen, 'excluded': excluded, 'sha256': sha(canonical(chosen)),
            'selector': 'FIRST_TEN_NONEMPTY_NATIVE_TEXT_V1', 'model_exposure': 'NOT_SENT'}


def checkpoint(api, unit, ids, output, name, baseline=None):
    result = {'checkpoint': name, 'status': 'UNKNOWN', 'lookups': {}, 'inventory': 'UNKNOWN',
              'queries': [], 'host_authority': unit['host_authority']}
    try:
        for role in ('current', 'target'):
            result['lookups'][role] = [api.get(identifier) for identifier in ids[role]]
        result['inventory'] = api.inventory()
        for index, query in enumerate(unit['queries']):
            response, rows = api.search(query)
            selection = select(rows, unit['provider'])
            target_ids = set(ids['target'])
            exposed = any(r['native_id'] in target_ids or r['content'] == unit['target']
                          for r in selection['selected'])
            raw_exposed = any(isinstance(r, dict) and
                              (r.get('id', r.get('uri')) in target_ids or
                               r.get('text', r.get('content')) == unit['target']) for r in rows)
            adequacy = {}
            for surface, present in (('raw', raw_exposed), ('selected', exposed)):
                before = present if baseline is None else baseline['queries'][index][surface + '_target_exposed']
                adequacy[surface] = 'EXPOSED_AT_BASELINE' if before else 'NOT_EXPOSED_AT_BASELINE'
            result['queries'].append({'query': query, 'native_response': response, 'candidates': rows,
                                      'selection': selection, 'raw_target_exposed': raw_exposed,
                                      'selected_target_exposed': exposed, 'baseline_adequacy': adequacy})
        result['status'] = 'COMPLETED'
    finally:
        write(output / (name + '.json'), result)
    return result


def run_phase(api, unit, output, *, prior=None):
    """Injected native session; tests inject the existing synthetic REST fixture."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    result = {'unit_id': unit['unit_id'], 'status': 'UNKNOWN', 'ids': 'UNKNOWN',
              'checkpoints': {name: 'UNKNOWN' for name in (CHECKPOINTS if prior is None else ('post-reopen',))}}
    try:
        if prior is None:
            api.fresh()
            ids = {}
            result['ids'] = ids
            for role in ('current', 'target'):
                ids[role] = api.add(role, unit[role])
            if not ids['current'] or not ids['target'] or set(ids['current']) & set(ids['target']):
                raise ValueError('DISTINCT_NATIVE_IDS_REQUIRED')
            api.validate_documents(ids)
            result['ids'] = ids
            result['checkpoints']['initial'] = checkpoint(api, unit, ids, output, 'initial')
            api.delete_target(ids)
            result['checkpoints']['post-delete'] = checkpoint(
                api, unit, ids, output, 'post-delete', result['checkpoints']['initial'])
        else:
            if prior['status'] != 'COMPLETED' or prior['unit_id'] != unit['unit_id']:
                raise ValueError('COMPLETED_PREDECESSOR_REQUIRED')
            ids = prior['ids']
            api.restore(ids, prior['documents'])
            result['ids'] = ids
            result['checkpoints']['post-reopen'] = checkpoint(
                api, unit, ids, output, 'post-reopen', prior['checkpoints']['initial'])
        result['documents'] = api.documents
        result['status'] = 'COMPLETED'
    except Exception as exc:
        result['error'] = {'class': type(exc).__name__, 'message': str(exc)[:400]}
    finally:
        result['documents'] = api.documents
        write(output / 'result.json', result)
    return result


class Budget:
    """Serial HTTP intent counter, not an authority or approval mechanism."""
    def __init__(self, path, deadline):
        self.path, self.deadline = Path(path), deadline

    def before(self):
        if time.time() >= self.deadline:
            raise TimeoutError('UNIT_DEADLINE')
        count = len(self.path.read_bytes().splitlines()) if self.path.exists() else 0
        if count >= MAX_HTTP:
            raise RuntimeError('HTTP_LIMIT')
        if sum(p.stat().st_size for p in self.path.parent.rglob('*') if p.is_file()) >= 10 * 1024**3:
            raise RuntimeError('EVIDENCE_LIMIT')
        with self.path.open('ab') as stream:
            stream.write(canonical({'ordinal': count + 1, 'at': time.time()}) + b'\n')
            stream.flush()
            os.fsync(stream.fileno())


class NativeAPI:
    """Thin scenario mapping over the retained qualified HTTP clients/capture."""
    def __init__(self, unit, run_id, capture, budget, *, hindsight_transport=None, ov_client=None):
        self.unit, self.capture, self.budget = unit, capture, budget
        self.provider = unit['provider']
        self.scope = 'lc12-' + sha((run_id + '/' + unit['unit_id']).encode())[:32]
        self.base = f'/v1/default/banks/{self.scope}'
        self.uri = f'viking://user/{self.scope}/memories/preferences'
        self.transport, self.client, self.documents = hindsight_transport, ov_client, {}

    def call(self, method, path, payload=None, *, missing=False, query=None):
        self.budget.before()
        if self.provider == 'openviking':
            target = path + ('?' + urlencode(query) if query else '')
            raw = self.client.call(method, target, payload, expected=(200, 404) if missing else (200,))
            status = self.client.exchanges[-1]['status']
            return {'status': status, 'value': json.loads(raw) if raw else None}
        from memlife.adapters.hindsight import HindsightHTTPError
        arguments = canonical({'method': method, 'path': path, 'query': query, 'payload': payload})
        intent = self.capture.lifecycle_intent(intended_operation=method + ' ' + path,
            native_operation='HINDSIGHT_HTTP', input_bytes=arguments, before_bytes=b'UNKNOWN')
        try:
            value = self.transport.request(method, path, query=query, payload=payload)
            status = (self.transport.last_exchange or {}).get('status_code', 200)
        except HindsightHTTPError as exc:
            if not missing or exc.status_code != 404:
                raise
            value, status = None, 404
        except Exception as exc:
            partial = getattr(exc, 'partial', None)
            self.capture.lifecycle(intended_operation=method + ' ' + path, native_operation='HINDSIGHT_HTTP',
                input_bytes=arguments, response_bytes=partial if isinstance(partial, bytes) else None,
                before_bytes=None, after_bytes=canonical({'exception': type(exc).__name__}),
                outcome='UNKNOWN', operation_id=intent)
            raise
        self.capture.lifecycle(intended_operation=method + ' ' + path, native_operation='HINDSIGHT_HTTP',
            input_bytes=arguments, response_bytes=None, before_bytes=None,
            after_bytes=canonical({'http_entity': 'SEE_HTTP_CAPTURE', 'status': status}),
            outcome='COMPLETED', operation_id=intent)
        return {'status': status, 'value': value}

    def inventory(self):
        if self.provider == 'openviking':
            return self.call('GET', '/api/v1/fs/ls', query={'uri': self.uri, 'recursive': 'true'})
        return self.listing('memories/list', 'items', {'state': 'valid'})

    def listing(self, endpoint, key, query=None):
        rows = []
        for _ in range(10):
            result = self.call('GET', self.base + '/' + endpoint,
                               query={**(query or {}), 'limit': 100, 'offset': len(rows)})['value']
            page = result[key]
            if not isinstance(page, list):
                raise ValueError('NATIVE_PAGE_REQUIRED')
            rows.extend(page)
            if not page or len(rows) >= result.get('total', len(rows)):
                return rows
        raise RuntimeError('PAGINATION_BOUND')

    def quiesce(self):
        if self.provider == 'openviking':
            return
        until = min(time.time() + 60, self.budget.deadline)
        for _ in range(20):
            operations = self.listing('operations', 'operations')
            if any(o.get('status') == 'failed' for o in operations):
                raise RuntimeError('NATIVE_OPERATION_FAILED')
            if all(o.get('status') in ('completed', 'cancelled') for o in operations):
                return
            if time.time() + 1 >= until:
                break
            time.sleep(1)
        raise TimeoutError('QUIESCENCE_BOUND')

    def fresh(self):
        if self.provider == 'hindsight':
            self.call('PUT', self.base, {'name': self.scope})
            if self.inventory():
                raise ValueError('BANK_NOT_EMPTY')
        # OpenViking uses a fresh physical store and hashed URI, attested by host.

    def add(self, role, text):
        if self.provider == 'openviking':
            identifier = self.uri + '/' + role + '.md'
            response = self.call('POST', '/api/v1/content/write', {
                'uri': identifier, 'content': text, 'mode': 'create', 'wait': True,
                'timeout': 60, 'processing_mode': 'vectors_only', 'telemetry': False})['value']
            if response.get('status') != 'ok' or response['result'].get('vector_status') != 'complete':
                raise ValueError('NATIVE_VECTOR_COMPLETION')
            return [identifier]
        document = self.scope + '-' + role
        response = self.call('POST', self.base + '/memories', {
            'items': [{'content': text, 'document_id': document}], 'async': False})['value']
        if response.get('success') is not True:
            raise ValueError('RETAIN_FAILED')
        self.quiesce()
        rows = self.listing('memories/list', 'items', {'state': 'valid', 'document_id': document})
        identifiers = [r['id'] for r in rows]
        if any(r.get('document_id') != document for r in rows):
            raise ValueError('DOCUMENT_SCOPE_MISMATCH')
        self.documents[role] = document
        return identifiers

    def validate_documents(self, ids):
        if self.provider == 'hindsight' and self.documents['current'] == self.documents['target']:
            raise ValueError('DOCUMENT_OVERLAP')

    def restore(self, ids, documents):
        self.documents = documents
        self.validate_documents(ids)

    def get(self, identifier):
        response = (self.call('GET', '/api/v1/content/read', missing=True,
                             query={'uri': identifier, 'raw': 'true'}) if self.provider == 'openviking'
                    else self.call('GET', self.base + '/memories/' + quote(identifier, safe=''), missing=True))
        return {'native_id': identifier, **response}

    def delete_target(self, ids):
        if self.provider == 'openviking':
            self.call('DELETE', '/api/v1/fs', query={'uri': ids['target'][0],
                      'recursive': 'false', 'wait': 'true', 'timeout': '60'})
        else:
            self.call('DELETE', self.base + '/documents/' + quote(self.documents['target'], safe=''))
            self.quiesce()

    def search(self, query):
        if self.provider == 'openviking':
            response = self.call('POST', '/api/v1/search/find', {
                'query': query, 'target_uri': self.uri, 'context_type': 'memory',
                'level': 2, 'limit': 10, 'read_content': True,
                'include_provenance': True, 'telemetry': False})
            return response, response['value']['result']['memories']
        response = self.call('POST', self.base + '/memories/recall', {
            'query': query, 'types': ['world', 'experience', 'observation'],
            'budget': 'low', 'max_tokens': 4096, 'include': {'entities': None, 'source_facts': {}}})
        return response, response['value']['results']
