"""Offline LC12 controls. All REST peers and process observations are synthetic."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT))
from memlife import crossarch as lc
from memlife.adapters.hindsight import HindsightHTTPError
from tests.fakes.hindsight import FakeHindsightTransport


class Capture:
    def __init__(self):
        self.observations = []
    def lifecycle_intent(self, **kwargs):
        return 'synthetic-intent'
    def lifecycle(self, **kwargs):
        self.observations.append(kwargs)


class Budget:
    deadline = float('inf')
    def before(self):
        pass


class Banks(FakeHindsightTransport):
    """Existing REST fixture, with only the bank creation route added."""
    def _handle_request(self, method, path, *, query=None, payload=None):
        if method == 'PUT':
            self.banks.setdefault(self._parts(path)[3], {})
            return {'success': True}
        return super()._handle_request(method, path, query=query, payload=payload)


class Files:
    """Synthetic direct-file HTTP fixture matching the qualified client's seam."""
    def __init__(self):
        self.files, self.exchanges = {}, []
    def call(self, method, path, payload=None, expected=(200,)):
        from urllib.parse import urlsplit, parse_qs
        split = urlsplit(path)
        query = parse_qs(split.query)
        uri = query.get('uri', [None])[0]
        status = 200
        if method == 'POST' and split.path.endswith('/write'):
            self.files[payload['uri']] = payload['content']
            response = {'status': 'ok', 'result': {'vector_status': 'complete'}}
        elif method == 'DELETE':
            self.files.pop(uri)
            response = {'status': 'ok'}
        elif split.path.endswith('/read'):
            status = 200 if uri in self.files else 404
            response = {'result': self.files.get(uri)}
        elif split.path.endswith('/ls'):
            response = {'result': [{'uri': k} for k in self.files]}
        elif split.path.endswith('/find'):
            response = {'result': {'memories': [{'uri': k, 'content': v, 'score': .5} for k, v in self.files.items()]}}
        else:
            raise AssertionError(path)
        self.exchanges.append({'method': method, 'path': path, 'status': status})
        if status not in expected:
            raise AssertionError(status)
        return json.dumps(response).encode()


class CrossarchTests(unittest.TestCase):
    def api(self, unit, transport=None):
        return lc.NativeAPI(unit, 'lc12-offline-test', Capture(), Budget(),
                            hindsight_transport=transport or Banks(), ov_client=Files())

    def test_exact_ledger(self):
        registered = json.loads((ROOT / 'manifests/crossarch-units-v1.json').read_bytes())
        self.assertEqual(registered, lc.plan())
        self.assertEqual(len({u['unit_id'] for u in registered['units']}), 12)
        for provider in ('hindsight', 'openviking'):
            for condition in ('CONTROL', 'CONFLICT'):
                self.assertEqual(sum(u['provider'] == provider and u['condition'] == condition for u in registered['units']), 3)

    def test_both_provider_trajectories_and_reopen(self):
        for provider in ('hindsight', 'openviking'):
            unit = next(u for u in lc.plan()['units'] if u['provider'] == provider and u['condition'] == 'CONFLICT')
            api = self.api(unit)
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                first = lc.run_phase(api, unit, root / 'initial')
                self.assertEqual(first['status'], 'COMPLETED', first)
                self.assertTrue(first['checkpoints']['initial']['queries'][0]['raw_target_exposed'])
                self.assertFalse(first['checkpoints']['post-delete']['queries'][0]['raw_target_exposed'])
                # A new client and new fixture peer preserve only the old stored state.
                fresh = self.api(unit)
                if provider == 'hindsight':
                    fresh.transport.banks = copy.deepcopy(api.transport.banks)
                else:
                    fresh.client.files = copy.deepcopy(api.client.files)
                reopened = lc.run_phase(fresh, unit, root / 'reopen', prior=first)
                self.assertEqual(reopened['status'], 'COMPLETED', reopened)
                after = reopened['checkpoints']['post-reopen']
                self.assertEqual(after['lookups']['target'][0]['status'], 404)
                self.assertEqual(after['lookups']['current'][0]['status'], 200)

    def test_partial_checkpoint_is_preserved(self):
        unit = lc.plan()['units'][0]
        api = self.api(unit)
        with tempfile.TemporaryDirectory() as directory:
            api.get = lambda identifier: (_ for _ in ()).throw(TimeoutError('synthetic lookup failure'))
            output = Path(directory) / 'initial'
            result = lc.run_phase(api, unit, output)
            self.assertEqual(result['status'], 'UNKNOWN')
            self.assertEqual(result['checkpoints']['post-delete'], 'UNKNOWN')
            self.assertEqual(json.loads((output / 'initial.json').read_bytes())['status'], 'UNKNOWN')
            self.assertEqual(len(result['ids']), 2)

    def test_baseline_nonexposure_is_not_removal_evidence(self):
        unit = lc.plan()['units'][0]
        api = self.api(unit)
        api.search = lambda query: ({'synthetic': True}, [])
        with tempfile.TemporaryDirectory() as directory:
            result = lc.run_phase(api, unit, Path(directory) / 'phase')
        adequacy = result['checkpoints']['post-delete']['queries'][0]['baseline_adequacy']
        self.assertEqual(set(adequacy.values()), {'NOT_EXPOSED_AT_BASELINE'})

    def test_selection_keeps_literal_order_duplicates_and_original_positions(self):
        result = lc.select([{}, {'uri': 'x', 'content': '  literal  '},
                            {'uri': 'x', 'content': '  literal  '}], 'openviking')
        self.assertEqual([r['position'] for r in result['selected']], [2, 3])
        self.assertEqual(result['selected'][0]['content'], '  literal  ')
        self.assertEqual(len(result['selected']), 2)

    def test_missing_body_is_not_reconstructed_from_archive(self):
        self.assertEqual(lc.select([{'uri': 'x', 'abstract': 'old archived text'}], 'openviking')['selected'], [])

    def test_expected404_does_not_halt_later_lookup(self):
        unit = next(u for u in lc.plan()['units'] if u['provider'] == 'hindsight')
        api = self.api(unit)
        api.fresh()
        ids = api.add('current', unit['current'])
        self.assertEqual(api.get('absent')['status'], 404)
        self.assertEqual(api.get(ids[0])['status'], 200)

    def test_errors_are_not_absence(self):
        unit = next(u for u in lc.plan()['units'] if u['provider'] == 'hindsight')
        api = self.api(unit)
        api.transport.request = lambda *a, **k: (_ for _ in ()).throw(HindsightHTTPError(500, 'synthetic server failure'))
        with self.assertRaises(HindsightHTTPError):
            api.get('unknown')

    def test_reopen_cannot_use_failed_predecessor(self):
        unit = lc.plan()['units'][0]
        with tempfile.TemporaryDirectory() as directory:
            result = lc.run_phase(self.api(unit), unit, Path(directory) / 'phase',
                                  prior={'status': 'UNKNOWN', 'unit_id': unit['unit_id']})
            self.assertEqual(result['status'], 'UNKNOWN')

    def test_operation_budget_counts_before_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'http.jsonl'
            budget = lc.Budget(path, float('inf'))
            with patch.object(lc, 'MAX_HTTP', 1):
                budget.before()
                with self.assertRaises(RuntimeError):
                    budget.before()
            self.assertEqual(len(path.read_bytes().splitlines()), 1)

    def test_expired_deadline_sends_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'http.jsonl'
            with self.assertRaises(TimeoutError):
                lc.Budget(path, 0).before()
            self.assertFalse(path.exists())

    def test_m3_small_resource_gate(self):
        self.assertEqual(lc.resource_decision(2, 6 * 1024**3, 100 * 1024**3)['status'], 'BLOCKED')
        self.assertEqual(lc.resource_decision(4, 16 * 1024**3, 20 * 1024**3)['status'], 'PASS')

    def test_resource_failure_precedes_all_provider_and_image_actions(self):
        spec = importlib.util.spec_from_file_location('lc12_host_test', ROOT / 'scripts/research/crossarch_host.py')
        host = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(host)
        class Result:
            returncode = 0
            stdout = b'{"NCPU":2,"MemTotal":6442450944}'
        with tempfile.TemporaryDirectory() as directory:
            config = {'run_id': 'lc12-offline-resource', 'qualified_root': directory,
                      'runtime_root': directory, 'embedding_runtime': directory,
                      'output_parent': directory}
            with patch.object(host.subprocess, 'run', return_value=Result()) as run:
                with self.assertRaises(RuntimeError):
                    host.collect(config, lc, ROOT)
                self.assertEqual(run.call_count, 1)
                self.assertEqual(run.call_args.args[0][1], 'info')
            result = json.loads((Path(directory) / config['run_id'] / 'collection-result.json').read_bytes())
            self.assertEqual(result['retained_resources'], [])
            self.assertEqual(len(result['units']), 12)
            self.assertTrue(all(u['checkpoints'] == {c: 'UNKNOWN' for c in lc.CHECKPOINTS}
                                for u in result['units'].values()))

    def test_multichunk_documents_keep_all_native_ids(self):
        class Chunks(Banks):
            def _handle_request(self, method, path, *, query=None, payload=None):
                result = super()._handle_request(method, path, query=query, payload=payload)
                if method == 'POST' and path.endswith('/memories'):
                    bank = self.banks[self._parts(path)[3]]
                    last = copy.deepcopy(list(bank.values())[-1])
                    last['id'] += '-chunk2'
                    bank[last['id']] = last
                return result
        unit = next(u for u in lc.plan()['units'] if u['provider'] == 'hindsight')
        with tempfile.TemporaryDirectory() as directory:
            result = lc.run_phase(self.api(unit, Chunks()), unit, Path(directory) / 'phase')
        self.assertEqual(result['status'], 'COMPLETED')
        self.assertEqual(len(result['ids']['target']), 2)
        self.assertEqual([r['status'] for r in result['checkpoints']['post-delete']['lookups']['target']], [404, 404])

    def test_partial_http_entity_remains_unknown(self):
        from http.client import IncompleteRead
        unit = next(u for u in lc.plan()['units'] if u['provider'] == 'hindsight')
        api = self.api(unit)
        api.transport.request = lambda *a, **k: (_ for _ in ()).throw(IncompleteRead(b'partial-entity'))
        with self.assertRaises(IncompleteRead):
            api.get('unknown')
        self.assertEqual(api.capture.observations[-1]['outcome'], 'UNKNOWN')
        self.assertEqual(api.capture.observations[-1]['response_bytes'], b'partial-entity')

    def test_pagination_is_bounded(self):
        unit = next(u for u in lc.plan()['units'] if u['provider'] == 'hindsight')
        api = self.api(unit)
        api.transport.request = lambda *a, **k: {'items': [{'id': 'repeated'}], 'total': 1000}
        with self.assertRaisesRegex(RuntimeError, 'PAGINATION_BOUND'):
            api.listing('memories/list', 'items')

    def test_full_synthetic_docker_supervisor_all_twelve_units(self):
        """Actual host control flow; subprocess/Docker and provider peers are fakes."""
        import io
        import os
        import tarfile
        spec = importlib.util.spec_from_file_location('lc12_host_full', ROOT / 'scripts/research/crossarch_host.py')
        host = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(host)
        test = self
        class Result:
            returncode, stderr = 0, b''
            def __init__(self, value=b'', rc=0, error=b''):
                self.returncode, self.stderr = rc, error
                self.stdout = value if isinstance(value, bytes) else json.dumps(value).encode()
        class PipeProcess:
            def __init__(self, *args, **kwargs):
                content = io.BytesIO()
                with tarfile.open(fileobj=content, mode='w') as archive:
                    info = tarfile.TarInfo('data/SYNTHETIC_DATABASE')
                    info.size = 9
                    archive.addfile(info, io.BytesIO(b'SYNTHETIC'))
                read, write = os.pipe()
                self.stdout = os.fdopen(read, 'rb')
                # Archive is small enough for one pipe write on this test host.
                os.write(write, content.getvalue()[:2048])
                os.close(write)
                read, write = os.pipe()
                self.stderr = os.fdopen(read, 'rb')
                os.close(write)
            def poll(self): return 0
            def wait(self, **kwargs): return 0
            def kill(self): pass
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, qualified, runtime, embedding = [base / n for n in ('source', 'qualified', 'runtime', 'embedding')]
            for relative in ('src/memlife/crossarch.py', 'scripts/research/crossarch.py', 'scripts/research/crossarch_host.py'):
                lc.write(source / relative, b'SYNTHETIC_IMPLEMENTATION_NOT_EXECUTED', raw=True)
            lc.write(qualified / 'synthetic-helper.py', b'SYNTHETIC_QUALIFIED_SOURCE', raw=True)
            lc.write(source / 'manifests/crossarch-qualified-reuse-v1.json',
                     {'files': {'synthetic-helper.py': lc.sha(b'SYNTHETIC_QUALIFIED_SOURCE')}})
            lc.write(source / 'manifests/crossarch-units-v1.json', lc.plan())
            for path in (runtime / 'openviking/.venv/bin/python', runtime / 'hindsight/.venv/bin/python',
                         embedding / 'runtime/.venv/bin/python'):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.symlink_to('/usr/local/bin/python')
            config = {'run_id': 'lc12-synthetic-supervisor', 'qualified_root': str(qualified),
                      'runtime_root': str(runtime), 'embedding_runtime': str(embedding),
                      'output_parent': str(base / 'output'), 'database_image': lc.DATABASE_IMAGE}
            resources, peers, sequence = {}, {}, [0]
            def run(command, **kwargs):
                if command[0] == 'findmnt':
                    return Result(str(base).encode())
                args = command[1:]
                if args[0] == 'info':
                    return Result({'NCPU': 4, 'MemTotal': 16*1024**3, 'OSType': 'linux', 'Architecture': 'x86_64'})
                if args[:2] == ['image', 'inspect']:
                    return Result([{'Id': args[2]}])
                if len(args) >= 2 and args[1] == 'inspect':
                    if args[2] in resources:
                        return Result([resources[args[2]]])
                    return Result(rc=1, error=('No such object: ' + args[2]).encode())
                if args[0] in ('create', 'run'):
                    name = args[args.index('--name') + 1]
                    sequence[0] += 1
                    value = {'Id': f'synthetic-container-{sequence[0]}',
                             'Config': {'Labels': {'memlife.lc12': config['run_id']}},
                             'State': {'Running': False, 'ExitCode': 0, 'OOMKilled': False}, 'args': args}
                    resources[name] = resources[value['Id']] = value
                    return Result(value['Id'].encode())
                if args[:2] in (['network', 'create'], ['volume', 'create']):
                    resources[args[-1]] = {'Labels': {'memlife.lc12': config['run_id']}}
                    return Result(args[-1].encode())
                if len(args) > 1 and args[1] == 'rm':
                    resources.pop(args[2])
                    return Result()
                if args[0] == 'exec':
                    return Result()
                if args[0] in ('start', 'stop', 'wait'):
                    value = resources[args[-1]]
                    if args[0] == 'start' and '--phase' in value['args']:
                        params = value['args']
                        phase = params[params.index('--phase') + 1]
                        mount = next(p for p in params if p.startswith('type=bind,') and 'dst=/evidence' in p)
                        evidence = Path(mount.split('src=')[1].split(',dst=')[0])
                        unit = json.loads((evidence / 'unit.json').read_bytes())
                        if phase == 'initial':
                            api = test.api(unit)
                            peers[str(evidence)] = api
                            result = lc.run_phase(api, unit, evidence / phase)
                        else:
                            old = peers[str(evidence)]
                            api = test.api(unit)
                            api.transport.banks = copy.deepcopy(old.transport.banks)
                            api.client.files = copy.deepcopy(old.client.files)
                            prior = json.loads((evidence / 'initial/result.json').read_bytes())
                            result = lc.run_phase(api, unit, evidence / phase, prior=prior)
                        test.assertEqual(result['status'], 'COMPLETED', result)
                        lc.write(evidence / (phase + '-processes.json'), {'all_exited': True, 'container_id': value['Id']})
                    value['State']['Running'] = args[0] == 'start' and '--phase' not in value['args']
                    return Result(b'0')
                raise AssertionError(args)
            with patch.object(host.subprocess, 'run', side_effect=run), patch.object(host.subprocess, 'Popen', PipeProcess):
                host.collect(config, lc, source)
            output = base / 'output' / config['run_id']
            result = json.loads((output / 'collection-result.json').read_bytes())
            self.assertEqual(result['status'], 'COMPLETED')
            self.assertEqual(result['retained_resources'], [])
            self.assertTrue(all(u['status'] == 'COMPLETED' for u in result['units'].values()))
            self.assertTrue(all(all(isinstance(c, dict) for c in u['checkpoints'].values()) for u in result['units'].values()))
            intents = list((output / 'resource-intents').glob('*.json'))
            self.assertEqual(len(intents), 42)  # 24 API containers + six DB/network/volume triples.
            for unit in lc.plan()['units']:
                reopen = json.loads((output / unit['unit_id'] / 'reopen-evidence.json').read_bytes())
                self.assertNotEqual(reopen['initial_container'], reopen['reopen_container'])
            # Same-label collision in another output root must never imply ownership.
            previous_name = config['run_id'] + '-' + lc.plan()['units'][0]['unit_id'].lower() + '-initial'
            previous = {'Id': 'previous-run', 'Config': {'Labels': {'memlife.lc12': config['run_id']}},
                        'State': {'Running': True}}
            resources[previous_name] = previous
            config['output_parent'] = str(base / 'other-output')
            with patch.object(host.subprocess, 'run', side_effect=run), patch.object(host.subprocess, 'Popen', PipeProcess):
                with self.assertRaises(RuntimeError):
                    host.collect(config, lc, source)
            self.assertIs(resources[previous_name], previous)
            self.assertTrue(previous['State']['Running'])

    def test_container_runtime_link_need_not_resolve_on_host(self):
        with tempfile.TemporaryDirectory() as directory:
            link = Path(directory) / 'python'
            link.symlink_to('/usr/local/bin/python')
            self.assertEqual(lc.retained_interpreter(link), str(link))
            link.unlink()
            link.symlink_to('/unqualified/host/python')
            with self.assertRaises(ValueError):
                lc.retained_interpreter(link)


if __name__ == '__main__':
    unittest.main()
