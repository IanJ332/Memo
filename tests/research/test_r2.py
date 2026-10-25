"""R2 synthetic fixture controls only; no Mem0/Docker/runtime startup."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import socket
import subprocess
import shutil
import sys
import tempfile
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from memlife import r2


class SyntheticSession:
    """Explicit synthetic file double. Its IDs/results are not native evidence."""
    def __init__(self, paths, output, *, fail=None, changed_sentinel=False, reverse=False,
                 corrupt_sentinel_metadata=False):
        self.paths, self.output = paths, output
        self.namespace = 'npq-' + r2.sha(r2.canonical(r2.design()['principal']))
        self.fail, self.changed_sentinel, self.reverse = fail, changed_sentinel, reverse
        self.corrupt_sentinel_metadata = corrupt_sentinel_metadata
        self.calls = []
        self.output.mkdir()
        self.state_file = Path(paths['qdrant']) / 'SYNTHETIC.json'
        for path in paths.values():
            Path(path).mkdir(exist_ok=True)
        self.state = r2.read(self.state_file) if self.state_file.exists() else {'records': {}, 'histories': {}}

    def persist(self):
        # This mutable fake state is separate from the exclusive evidence writer.
        self.state_file.write_bytes(r2.canonical(self.state))

    def call(self, operation, **kwargs):
        self.calls.append((operation, deepcopy(kwargs)))
        ordinal = len(self.calls)
        self.write(str(ordinal) + '-intent', {'operation': operation, 'kwargs': kwargs,
                                           'evidence_type': 'SYNTHETIC_TEST_ONLY'})
        if operation == self.fail:
            self.write(str(ordinal) + '-exception', {'class': 'RuntimeError', 'effect': 'UNKNOWN'})
            raise RuntimeError('SYNTHETIC_NATIVE_ERROR')
        records, histories = self.state['records'], self.state['histories']
        memory_id = kwargs.get('memory_id')
        if operation == 'INSPECT':
            result = list(records.values())
        elif operation == 'ADD':
            memory_id = Path(self.paths['qdrant']).parent.name + '-synthetic-' + str(len(histories) + 1)
            records[memory_id] = {'id': memory_id, 'memory': kwargs['content'],
                                  'metadata': kwargs['metadata'], 'user_id': self.namespace}
            histories[memory_id] = [{'memory_id': memory_id, 'event': 'ADD', 'new_memory': kwargs['content']}]
            result = memory_id
        elif operation in ('UPDATE', 'DELETE'):
            histories[memory_id].append({'memory_id': memory_id, 'event': operation})
            if operation == 'UPDATE':
                records[memory_id]['memory'] = kwargs['content']
            else:
                del records[memory_id]
            if self.corrupt_sentinel_metadata:
                for row in records.values():
                    if row['metadata']['fixture_role'] == 'sentinel':
                        row['metadata']['unexpected'] = 'SYNTHETIC_UNRELATED_CHANGE'
            result = None
        elif operation == 'GET':
            result = deepcopy(records.get(memory_id))
            if self.changed_sentinel and result and result['metadata']['fixture_role'] == 'sentinel':
                result['memory'] = 'SYNTHETIC_UNEXPECTED_CHANGE'
        elif operation == 'GET_ALL':
            result = {'results': list(records.values())}
        elif operation == 'SEARCH':
            values = list(records.values())
            if self.reverse:
                values.reverse()
            result = {'results': [{**row, 'score': 0.5 + i / 100} for i, row in enumerate(values)]}
        elif operation == 'HISTORY':
            result = histories[memory_id]
        else:
            raise ValueError(operation)
        self.persist()
        self.write(str(ordinal) + '-return', result)
        return deepcopy(result)

    def write(self, name, value):
        return r2.save(self.output / (name + '.json'), value)

    def close(self):
        self.write('closed', {'closed': True, 'type': 'SYNTHETIC_TEST_ONLY'})


class R2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.parent, self.out = self.root / 'stores', self.root / 'evidence'
        self.parent.mkdir()
        self.out.mkdir()
        self.bindings = {'source': 'a' * 64, 'runtime': 'b' * 64,
                         'protocol': r2.sha(r2.DESIGN.read_bytes())}
        self.sessions, self.seals = [], {}

    def run_phase(self, name, **options):
        condition, mode = name.split('-')
        kwargs = dict(parent=self.parent, output=self.out / name, condition=condition,
                      reopen=mode == 'reopen', process='SYNTHETIC-PROCESS-' + name,
                      bindings=self.bindings, factory=self.factory(options))
        ordinal = r2.design()['phases'].index(name)
        if ordinal:
            kwargs['predecessor_seal'] = self.seals[r2.design()['phases'][ordinal - 1]]
        if mode == 'reopen':
            kwargs.update(prior_folder=self.out / (condition + '-initial'),
                          prior_seal=self.seals[condition + '-initial'])
        result, digest = r2.phase(**kwargs)
        self.seals[name] = digest
        return result

    def factory(self, options):
        def create(paths, output):
            session = SyntheticSession(paths, output, **options)
            self.sessions.append(session)
            return session
        return create

    def all_phases(self):
        return [self.run_phase(name) for name in r2.design()['phases']]

    def test_exact_fixture_bytes_and_independent_host_schedule(self):
        m = r2.design()
        self.assertEqual(m['host_state_schedule'][1]['authorized_recipient'], 'recipient-42')
        self.assertNotIn('recipient-17', m['retrieval']['query'])
        self.assertNotIn('recipient-42', m['retrieval']['query'])
        self.assertEqual(m['retrieval']['limit'], 10)
        self.assertIsNone(m['retrieval']['score_threshold'])
        self.assertEqual(m['records']['target']['before'],
                         'Routing assignment for routing-project-01: deliver the synthetic status report to recipient-17.')
        self.assertEqual(m['bounds']['sdk_total'], sum(m['bounds']['sdk_calls'].values()))

    def test_exact_operations_and_checkpoint_coverage(self):
        results = self.all_phases()
        checkpoint = ['GET', 'GET', 'GET_ALL', 'SEARCH', 'HISTORY', 'HISTORY']
        for i, session in enumerate(self.sessions):
            expected = (['INSPECT', 'ADD', 'ADD'] + checkpoint +
                        [('UPDATE' if i == 0 else 'DELETE')] + checkpoint if i in (0, 2) else checkpoint)
            self.assertEqual([op for op, _ in session.calls], expected)
            for op, args in session.calls:
                if op == 'SEARCH':
                    self.assertEqual(args, {'query': r2.design()['retrieval']['query'], 'limit': 10})
        self.assertTrue(all(r['status'] == 'COMPLETED' for r in results))
        self.assertTrue(all(v['status'] == 'OBSERVED_MATCH' for r in results
                            for c in r['checkpoints'].values() for v in c['outcomes'].values()))

    def test_same_native_id_mutations_and_no_condition_contamination(self):
        rows = self.all_phases()
        self.assertNotEqual(rows[0]['paths'], rows[2]['paths'])
        self.assertTrue(set(rows[0]['native_ids'].values()).isdisjoint(rows[2]['native_ids'].values()))
        for i, mutation in ((0, 'UPDATE'), (2, 'DELETE')):
            call = next(args for op, args in self.sessions[i].calls if op == mutation)
            self.assertEqual(call['memory_id'], rows[i]['native_ids']['target'])
            self.assertNotEqual(call['memory_id'], rows[i]['native_ids']['sentinel'])

    def test_sentinel_mismatch_is_observed_not_repaired(self):
        row = self.run_phase('UPDATE-initial', changed_sentinel=True)
        self.assertEqual(row['checkpoints']['after']['outcomes']['sentinel_live']['status'], 'OBSERVED_MISMATCH')
        self.assertEqual(row['status'], 'COMPLETED')  # Collection, not security success.

    def test_added_sentinel_metadata_is_detected(self):
        row = self.run_phase('UPDATE-initial', corrupt_sentinel_metadata=True)
        self.assertEqual(row['checkpoints']['after']['outcomes']['sentinel_metadata_preserved']['status'],
                         'OBSERVED_MISMATCH')

    def test_delete_history_survives_live_absence(self):
        rows = self.all_phases()
        last = rows[-1]['checkpoints']['reopened']
        self.assertIsNone(last['raw']['target'])
        self.assertTrue(last['raw']['history_target'])
        self.assertEqual(last['outcomes']['target_live']['status'], 'OBSERVED_MATCH')

    def test_native_error_stops_without_retry_and_unknown_checkpoints(self):
        row = self.run_phase('UPDATE-initial', fail='UPDATE')
        self.assertEqual(row['status'], 'INCOMPLETE')
        self.assertEqual(row['checkpoints']['after']['outcomes']['checkpoint']['status'], 'UNKNOWN')
        self.assertEqual([op for op, _ in self.sessions[0].calls].count('UPDATE'), 1)
        r2.verify_seal(self.out / 'UPDATE-initial', self.seals['UPDATE-initial'])

    def test_checkpoint_error_preserves_partial_observations(self):
        row = self.run_phase('UPDATE-initial', fail='GET_ALL')
        cp = row['checkpoints']['baseline']
        self.assertEqual(cp['outcomes']['target_live']['status'], 'OBSERVED_MATCH')
        self.assertEqual(cp['outcomes']['inventory_live']['status'], 'UNKNOWN')
        self.assertEqual(cp['outcomes']['history_target']['status'], 'UNKNOWN')
        self.assertFalse(any(op == 'UPDATE' for op, _ in self.sessions[0].calls))

    def test_missing_is_unknown(self):
        self.assertEqual(r2.score(None, None, None)['status'], 'UNKNOWN')
        self.assertEqual(r2.score(False, True, {'path': 'raw'})['status'], 'OBSERVED_MISMATCH')

    def test_literal_selection_preserves_order_contents_and_hash(self):
        raw = [{'id': 'b', 'memory': 'literal\n B ', 'score': .6, 'user_id': 'ns'},
               {'id': 'a', 'memory': 'literal A', 'score': .7, 'user_id': 'ns'}]
        value = r2.selected(raw, 'ns')
        self.assertEqual([r['native_id'] for r in value['selected']], ['b', 'a'])
        self.assertEqual(value['selected'][0]['content'], 'literal\n B ')
        self.assertEqual(value['context_sha256'], r2.sha(r2.canonical(value['selected'])))
        self.assertEqual(value['MODEL_EXPOSURE'], 'NOT_SENT')
        self.assertEqual(value['MODEL_PROPOSAL'], 'NOT_GENERATED')

    def test_duplicate_and_foreign_candidates_rejected(self):
        row = {'id': 'a', 'memory': 'x', 'user_id': 'ns'}
        for raw in ([row, row], [{**row, 'user_id': 'foreign'}]):
            with self.assertRaises(ValueError):
                r2.selected(raw, 'ns')

    def test_reopen_ranking_and_scores_may_change(self):
        self.run_phase('UPDATE-initial')
        row = self.run_phase('UPDATE-reopen', reverse=True)
        self.assertEqual(row['status'], 'COMPLETED')
        self.assertEqual(row['checkpoints']['reopened']['outcomes']['inventory_live']['status'], 'OBSERVED_MATCH')

    def test_reopen_requires_seal_before_factory(self):
        with self.assertRaisesRegex(ValueError, 'PREDECESSOR_REQUIRED'):
            r2.phase(parent=self.parent, output=self.out / 'UPDATE-reopen', condition='UPDATE', reopen=True,
                     process='SYNTHETIC', bindings=self.bindings, factory=lambda *_: self.fail('constructed'))

    def test_reopen_rejects_state_path_runtime_and_process_drift(self):
        row = self.run_phase('UPDATE-initial')
        args = [self.out / 'UPDATE-initial', self.seals['UPDATE-initial'], row['paths'], 'new-process', self.bindings]
        for changed in (dict(index=2, value=r2.store_paths(self.parent, 'DELETE')),
                        dict(index=3, value=row['process']),
                        dict(index=4, value={**self.bindings, 'runtime': 'c' * 64})):
            bad = list(args)
            bad[changed['index']] = changed['value']
            with self.assertRaises(ValueError):
                r2.verify_reopen(*bad)
        self.sessions[0].state_file.write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'PERSISTENT_STATE_DRIFT'):
            r2.verify_reopen(*args)

    def test_incomplete_prior_cannot_reopen(self):
        self.run_phase('UPDATE-initial', fail='UPDATE')
        with self.assertRaisesRegex(ValueError, 'SERIAL_CLOSED_PREDECESSOR'):
            self.run_phase('UPDATE-reopen')

    def test_seal_detects_changes_and_added_files(self):
        self.run_phase('UPDATE-initial')
        folder = self.out / 'UPDATE-initial'
        (folder / 'extra').write_text('unregistered')
        with self.assertRaisesRegex(ValueError, 'SEALED_MEMBERSHIP_OR_BYTES'):
            r2.verify_seal(folder, self.seals['UPDATE-initial'])

    def test_empty_directory_drift_is_rejected_in_evidence_and_state(self):
        row = self.run_phase('UPDATE-initial')
        folder = self.out / 'UPDATE-initial'
        (folder / 'unregistered-empty').mkdir()
        with self.assertRaisesRegex(ValueError, 'SEALED_MEMBERSHIP_OR_BYTES'):
            r2.verify_seal(folder, self.seals['UPDATE-initial'])
        (folder / 'unregistered-empty').rmdir()
        (Path(row['paths']['qdrant']) / 'unregistered-empty').mkdir()
        with self.assertRaisesRegex(ValueError, 'PERSISTENT_STATE_DRIFT'):
            r2.verify_reopen(folder, self.seals['UPDATE-initial'], row['paths'], 'new', self.bindings)

    def test_all_four_process_identities_must_differ(self):
        for name in r2.design()['phases'][:3]:
            self.run_phase(name)
        with self.assertRaisesRegex(ValueError, 'SERIAL_CLOSED_PREDECESSOR'):
            r2.phase(parent=self.parent, output=self.out / 'DELETE-reopen', condition='DELETE', reopen=True,
                     process='SYNTHETIC-PROCESS-UPDATE-initial', bindings=self.bindings,
                     factory=lambda *_: self.fail('constructed'),
                     predecessor_seal=self.seals['DELETE-initial'],
                     prior_folder=self.out / 'DELETE-initial', prior_seal=self.seals['DELETE-initial'])

    def test_no_replay_even_with_alternate_output_root(self):
        self.run_phase('UPDATE-initial')
        self.run_phase('UPDATE-reopen')
        alternative = self.root / 'other-evidence'
        alternative.mkdir()
        shutil.copytree(self.out / 'UPDATE-initial', alternative / 'UPDATE-initial')
        # Same original state still cannot be reconstructed twice.
        with self.assertRaises(FileExistsError):
            r2.phase(parent=self.parent, output=alternative / 'UPDATE-reopen', condition='UPDATE', reopen=True,
                     process='different', bindings=self.bindings, factory=lambda *_: self.fail('constructed'),
                     predecessor_seal=self.seals['UPDATE-initial'],
                     prior_folder=self.out / 'UPDATE-initial', prior_seal=self.seals['UPDATE-initial'])

    def test_initial_fresh_store_required_and_no_replay(self):
        self.run_phase('UPDATE-initial')
        with self.assertRaisesRegex(ValueError, 'FRESH_STORE_REQUIRED'):
            self.run_phase('UPDATE-initial')

    def test_cleanup_lists_only_two_owned_roots_and_deletes_nothing(self):
        self.all_phases()
        phases = {c: (self.out / (c + '-reopen'), self.seals[c + '-reopen']) for c in ('UPDATE', 'DELETE')}
        expected = [str(self.parent / c) for c in ('UPDATE', 'DELETE')]
        self.assertEqual(r2.cleanup_candidates(self.parent, phases), expected)
        self.assertTrue(all(Path(p).exists() for p in expected))
        with self.assertRaises(ValueError):
            r2.cleanup_candidates(self.root, phases)

    def test_store_symlink_rejected(self):
        (self.parent / 'UPDATE').symlink_to(self.out, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'SYMLINK_STORE_PATH'):
            r2.store_paths(self.parent, 'UPDATE')

    def test_snapshots_are_separate_copies(self):
        row = self.run_phase('UPDATE-initial')
        snap = self.out / 'UPDATE-initial/snapshot-qdrant/SYNTHETIC.json'
        self.assertEqual(snap.read_bytes(), self.sessions[0].state_file.read_bytes())
        self.assertNotEqual(snap.stat().st_ino, self.sessions[0].state_file.stat().st_ino)

    def test_no_network_or_process_dispatch_in_factory(self):
        def blocked(paths, output):
            socket.getaddrinfo('invalid.example', 443)
        result, _ = r2.phase(parent=self.parent, output=self.out / 'UPDATE-initial', condition='UPDATE',
                            reopen=False, process='SYNTHETIC', bindings=self.bindings, factory=blocked)
        self.assertEqual(result['error']['class'], 'PermissionError')
        self.assertEqual(result['status'], 'INCOMPLETE')
        self.assertEqual(r2._OFFLINE_DEPTH, 0)

    def test_model_guard_and_command_binding_in_bridge_with_synthetic_dependencies(self):
        capture, memory = ModuleType('synthetic_capture'), ModuleType('synthetic_memory')
        calls = []
        class SyntheticLifecycle:
            def __init__(self, *args, **kwargs):
                pass

            def step(self, operation, command):
                calls.append((operation, command))
        capture.NativeLifecycleCapture = SyntheticLifecycle
        capture.attach_mem0_capture = lambda adapter, _: adapter.native_memory
        for name in ('WriteCommand', 'SupersedeCommand', 'DeleteCommand', 'QueryCommand'):
            setattr(memory, name, lambda **kwargs: SimpleNamespace(**kwargs))
        with patch.dict(sys.modules, {'memlife.native_provider_capture': capture, 'memlife.models.memory': memory}):
            adapter = SimpleNamespace(native_memory=SimpleNamespace(llm=SimpleNamespace()))
            session = r2.QualifiedSession(adapter, object(), 'fixture-ns')
            with self.assertRaisesRegex(PermissionError, 'R2_INTERNAL_LLM_FORBIDDEN'):
                adapter.native_memory.llm.generate_response('must never generate')
            session.call('UPDATE', memory_id='original-id', content='new', metadata={'role': 'target'})
            session.call('DELETE', memory_id='original-id')
            self.assertEqual([op for op, _ in calls], ['UPDATE', 'DELETE'])
            self.assertEqual([c.memory_id for _, c in calls], ['original-id', 'original-id'])

    def test_process_dispatch_is_blocked_without_launch(self):
        def blocked(*_):
            subprocess.run(['SYNTHETIC_MUST_NOT_LAUNCH'], check=True)
        row, _ = r2.phase(parent=self.parent, output=self.out / 'UPDATE-initial', condition='UPDATE',
                          reopen=False, process='SYNTHETIC', bindings=self.bindings, factory=blocked)
        self.assertEqual(row['error']['class'], 'PermissionError')

    def test_cleanup_rejects_unowned_extra_file(self):
        self.all_phases()
        (self.parent / 'UPDATE/unrelated').write_text('must preserve')
        phases = {c: (self.out / (c + '-reopen'), self.seals[c + '-reopen']) for c in ('UPDATE', 'DELETE')}
        with self.assertRaisesRegex(ValueError, 'EXACT_OWNED_MEMBERSHIP'):
            r2.cleanup_candidates(self.parent, phases)

    def test_fixture_drift_rejected(self):
        changed = self.root / 'candidate.json'
        changed.write_bytes(r2.DESIGN.read_bytes() + b'\n')
        with patch.object(r2, 'DESIGN', changed):
            with self.assertRaisesRegex(ValueError, 'CANDIDATE_DESIGN_DRIFT'):
                r2.design()


if __name__ == '__main__':
    unittest.main()
