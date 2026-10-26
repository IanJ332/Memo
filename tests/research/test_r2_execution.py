"""R2 integration doubles only: never create a Docker/provider process."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from memlife import r2, r2_execution as ex


def fixture(root):
    return {'schema': 'MEMLIFE_R2_EXECUTION_PACKAGE_V1', 'execution_id': 'R2EX-20261025-abcdef012345',
        'status': 'SYNTHETIC_TEST_ONLY', 'contract': ex.contract(), 'protocol_sha256': r2.DESIGN_SHA256,
        'image_id': r2.design()['runtime']['image_id'], 'sources': {}, 'runtime_files': {},
        'container_user': str(os.getuid()) + ':' + str(os.getgid()), 'image_environment': ['PATH=/usr/bin'],
        'source_mounts': {'current_root': str(root / 'source-current'), 'qualified_root': str(root / 'source-qualified')},
        'host': {'current_root': str(root), 'qualified_root': str(root / 'qualified'),
                 'runtime_root': str(root / 'runtime'), 'output': str(root / '.local/r2-runs/R2EX-20261025-abcdef012345'),
                 'endpoint': ex.ENDPOINT, 'docker': ex.DOCKER}, 'package_host_dir': str(root)}


def container(p, phase, identity):
    command = ex.create_command(p, phase, Path(p['_package_dir']))
    return {'Id': identity, 'Name': '/' + (p['execution_id'] + '-' + phase).lower(), 'Image': p['image_id'],
        'Config': {'Labels': {'memlife.r2': p['execution_id'], 'memlife.phase': phase}, 'Hostname': identity[:12],
            'Env': p['image_environment'] + ['HOME=/tmp/home', 'PYTHONDONTWRITEBYTECODE=1', 'MEMLIFE_R2_PACKAGE=' + p['_hash']],
            'Cmd': command[command.index(p['image_id']) + 1:], 'Entrypoint': None, 'User': p['container_user']},
        'HostConfig': {'NetworkMode': 'none', 'ReadonlyRootfs': True, 'CapDrop': ['ALL'], 'SecurityOpt': ['no-new-privileges'],
            'Memory': 8589934592, 'MemorySwap': 17179869184, 'NanoCpus': 2000000000, 'PidsLimit': 256,
            'Tmpfs': {'/tmp': 'rw,nosuid,nodev,size=1073741824'}},
        'Mounts': [{'Source': src, 'Destination': dest, 'RW': not ro} for src, dest, ro in ex.mounts(p, phase, p['_package_dir'])],
        'State': {'Status': 'created', 'Running': False, 'ExitCode': 0, 'OOMKilled': False}}


class SyntheticDocker:
    """Fake lifecycle only. Synthetic result files are not native observations."""
    def __init__(self, p, fail=None):
        self.p, self.fail, self.calls, self.objects = p, fail, [], {}
        self.info = {'MemTotal': 12536020992, 'NCPU': 16, 'MemoryLimit': True, 'PidsLimit': True}

    def console(self, identity, path, root):
        self.calls.append(('console', identity))
        with path.open('xb') as output:
            output.write(b'SYNTHETIC_CONSOLE_ONLY\n')
        if self.fail == 'console':
            raise TimeoutError('SYNTHETIC_PARTIAL_CONSOLE')

    def call(self, *args):
        self.calls.append(args)
        action = args[0]
        if action == 'info':
            return json.dumps(self.info)
        if action == 'ps':
            return '\n'.join(self.objects) if '-aq' in args else ''
        if action == 'image':
            return json.dumps([{'Id': self.p['image_id'], 'Os': 'linux', 'Architecture': 'amd64',
                                'Config': {'Env': self.p['image_environment']}}])
        if action == 'create':
            name = args[args.index('--name') + 1]
            phase = next(x for x in self.p['contract']['phases'] if name.endswith(x.lower()))
            identity = str(self.p['contract']['phases'].index(phase) + 1) * 64
            self.objects[identity] = container(self.p, phase, identity)
            if self.fail == 'uncertain-create':
                raise TimeoutError('SYNTHETIC_CREATE_OUTCOME_UNKNOWN')
            return identity
        identity = args[-1]
        if action == 'inspect':
            found = next((c for key, c in self.objects.items() if key == identity or c['Name'] == '/' + identity), None)
            if found is None:
                raise ValueError('SYNTHETIC_NOT_FOUND')
            return json.dumps([found])
        c = self.objects[identity]
        if action == 'start':
            phase = c['Config']['Labels']['memlife.phase']
            root = Path(self.p['host']['output'])
            folder = root / 'evidence' / phase
            folder.mkdir()
            condition = phase.split('-')[0]
            store = root / 'stores' / condition
            if not store.exists():
                store.mkdir()
                r2.save(store / 'initial-claim.json', {'output': '/run/evidence/' + condition + '-initial',
                        'process': identity, 'bindings': ex.bindings(self.p)})
                (store/'qdrant').mkdir()
                (store/'qdrant/SYNTHETIC_STORE').write_text('SYNTHETIC_ONLY')
            result = {'status': 'INCOMPLETE' if self.fail == 'incomplete' else 'COMPLETED', 'closed': True,
                      'process': identity, 'bindings': ex.bindings(self.p)}
            counts = ex.prior_counts(root/'supervisor', self.p, phase)
            budget = ex.Budget(folder, counts, self.p['contract']['phases'].index(phase))
            budget.reserve('get_all')
            inputs = folder/'capture/native-sdk'; inputs.mkdir(parents=True)
            r2.save(inputs/'000001-input.json', {'method':'get_all','args':[], 'kwargs':{}})
            r2.save(folder / 'result.json', result)
            r2.save(folder / 'seal.json', {'files': r2.tree(folder)})
            c['State']['Status'] = 'exited'
            return identity
        if action == 'kill':
            c['State'].update(Running=False, Status='exited', ExitCode=137)
            return identity
        if action == 'rm':
            del self.objects[identity]
            return identity
        raise AssertionError(args)


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.p = fixture(self.root)
        self.package = self.root / 'package.json'
        r2.save(self.package, self.p)
        self.package_hash = r2.sha(self.package.read_bytes())
        self.p['_hash'], self.p['_package_dir'] = self.package_hash, str(self.root)
        self.review = self.root / 'review.json'
        r2.save(self.review, {'status': 'ACCEPT_EXACT_R2_PACKAGE', 'material_defects': [],
            'package_sha256': self.package_hash, 'sources': self.p['sources'],
            'runtime_files_sha256': r2.sha(r2.canonical(self.p['runtime_files'])),
            'reviewer': 'SYNTHETIC_TEST_DOUBLE_NOT_A_REAL_REVIEW', 'execution_authorized': False})
        self.review_hash = r2.sha(self.review.read_bytes())
        self.grant = self.root / 'grant.json'
        self.g = ex.owner_grant(self.package, self.review, self.review_hash)

    def admitted_grant(self):
        now = datetime.now(timezone.utc)
        g = dict(self.g, approved=True, owner_provenance='SYNTHETIC_ONLY', authorized_at=now.isoformat(),
                 start_at=(now-timedelta(seconds=1)).isoformat(), stop_at=(now+timedelta(minutes=30)).isoformat(),
                 external_approval_reference='SYNTHETIC_ONLY_NO_EXTERNAL_APPROVAL')
        return g

    def supervise(self, fail=None, grant=None):
        r2.save(self.grant, grant or self.admitted_grant())
        Path(self.p['host']['output']).parent.mkdir(parents=True)
        driver = SyntheticDocker(self.p, fail)
        self.driver = driver
        with patch.object(ex, 'verify_package', return_value=deepcopy(self.p)):
            return ex.execute(self.package, self.package_hash, self.review, self.review_hash, self.grant, driver=driver)

    def test_resource_threshold_and_actual_recovery(self):
        info = {'MemTotal': 12536020992, 'NCPU': 16, 'MemoryLimit': True, 'PidsLimit': True}
        result = ex.resources(info, '', 6*1024**3)
        self.assertEqual(result['headroom_bytes'], 3946086400)
        for ram in (8215871488, 8589934592, 9663676415):
            with self.assertRaisesRegex(ValueError, 'VM_MEMORY'):
                ex.resources(dict(info, MemTotal=ram), '', 6*1024**3)
        ex.resources(dict(info, MemTotal=9663676416), '', 6*1024**3)

    def test_enforcement_cpu_disk_and_conflicts_reject(self):
        info = {'MemTotal': 12536020992, 'NCPU': 16, 'MemoryLimit': True, 'PidsLimit': True}
        for changed in ({'MemoryLimit': False}, {'PidsLimit': False}, {'NCPU': 1}):
            with self.assertRaises(ValueError):
                ex.resources(dict(info, **changed), '', 6*1024**3)
        for running, disk in (('other-owned-container', 6*1024**3), ('', 1024)):
            with self.assertRaises(ValueError):
                ex.resources(info, running, disk)

    def test_exact_docker_configuration_and_readonly_custody(self):
        for phase in self.p['contract']['phases']:
            c = container(self.p, phase, 'a'*64)
            ex.container_check(c, self.p, phase)
            for field, value in (('NetworkMode', 'bridge'), ('Memory', 7*1024**3), ('PidsLimit', 0)):
                bad = deepcopy(c); bad['HostConfig'][field] = value
                with self.assertRaises(ValueError):
                    ex.container_check(bad, self.p, phase)
            for field, value in (('Cmd', ['sh']), ('User', '0'), ('Entrypoint', ['sh']), ('Env', ['OPENAI_API_KEY=fake'])):
                bad = deepcopy(c); bad['Config'][field] = value
                with self.assertRaises(ValueError):
                    ex.container_check(bad, self.p, phase)
            self.assertFalse(next(m for m in c['Mounts'] if m['Destination']=='/run/supervisor')['RW'])
            self.assertIn('/package/package.json', [m['Destination'] for m in c['Mounts']])

    def test_sdk_intents_enforce_global_and_phase_bounds(self):
        counts = {name: 0 for name in ex.contract()['sdk_calls']}
        budget = ex.Budget(self.root, counts, 0)
        budget.reserve('update')
        with self.assertRaisesRegex(ValueError, 'SDK_CEILING'):
            budget.reserve('update')
        self.assertEqual(len(list(self.root.glob('sdk-intent*'))), 1)
        budget.halted = False
        budget.ordinal = 32
        with self.assertRaises(ValueError):
            budget.reserve('get')
        budget.ordinal = 0; budget.halted = True
        with self.assertRaisesRegex(ValueError, 'HALTED'):
            budget.reserve('get')

    def test_review_missing_invalid_and_wrong_maps_reject(self):
        with self.assertRaises(FileNotFoundError):
            ex.review(self.root/'missing', 'a'*64, self.package, self.p)
        with self.assertRaisesRegex(ValueError, 'HASH'):
            ex.review(self.review, 'a'*64, self.package, self.p)
        changed = deepcopy(self.p); changed['sources'] = {'different': 'a'*64}
        with self.assertRaisesRegex(ValueError, 'COMPLETE_MAP'):
            ex.review(self.review, self.review_hash, self.package, changed)

    def test_unapproved_grant_has_no_human_fields_and_cannot_dispatch(self):
        self.assertFalse(self.g['approved'])
        self.assertTrue(all(self.g[k] is None for k in ('owner_provenance','authorized_at','start_at','stop_at','external_approval_reference')))
        with self.assertRaisesRegex(ValueError, 'OWNER_UNAPPROVED'):
            self.supervise(grant=self.g)
        self.assertEqual(self.driver.calls, [])

    def test_expired_or_scope_drift_grant_rejects(self):
        now = datetime.now(timezone.utc)
        for g in (dict(self.admitted_grant(), stop_at=(now-timedelta(seconds=1)).isoformat()),
                  dict(self.admitted_grant(), execution_id='different'),
                  dict(self.admitted_grant(), owner_provenance=None)):
            with self.assertRaises(ValueError):
                ex.authorize(g, self.p, self.package_hash, self.review_hash, now)

    def test_synthetic_supervisor_four_distinct_serial_processes_and_no_replay(self):
        self.assertEqual(self.supervise(), 'COMPLETED')
        phases = [next(x for x in self.p['contract']['phases'] if args[args.index('--name')+1].endswith(x.lower()))
                  for args in self.driver.calls if args[0]=='create']
        self.assertEqual(phases, self.p['contract']['phases'])
        root = Path(self.p['host']['output'])
        result = r2.read(root/'supervisor/result.json')
        self.assertEqual(len(set(result['container_ids'])), 4)
        self.assertFalse((root/'stores').exists())
        self.assertTrue((root/'supervisor/closed-stores/UPDATE/qdrant/SYNTHETIC_STORE').is_file())
        self.assertTrue((root/'supervisor/closed-stores/DELETE/qdrant/SYNTHETIC_STORE').is_file())
        self.assertTrue((root/'seal.json').exists())
        with patch.object(ex, 'verify_package', return_value=self.p), self.assertRaisesRegex(ValueError, 'FRESH_EXECUTION'):
            ex.execute(self.package,self.package_hash,self.review,self.review_hash,self.grant,driver=self.driver)

    def test_incomplete_stops_no_retry_and_preserves_evidence_before_cleanup(self):
        self.assertEqual(self.supervise('incomplete'), 'INCOMPLETE')
        self.assertEqual(sum(c[0]=='create' for c in self.driver.calls), 1)
        root = Path(self.p['host']['output'])
        self.assertEqual(r2.read(root/'supervisor/failure.json')['unperformed_observations'], 'UNKNOWN')
        self.assertTrue((root/'evidence/UPDATE-initial/seal.json').is_file())
        self.assertTrue((root/'supervisor/pre-cleanup-seal.json').is_file())
        self.assertFalse((root/'stores').exists())

    def test_uncertain_create_is_not_retried_and_only_owned_name_cleaned(self):
        self.assertEqual(self.supervise('uncertain-create'), 'INCOMPLETE')
        self.assertEqual(sum(c[0]=='create' for c in self.driver.calls), 1)
        self.assertEqual(self.driver.objects, {})
        self.assertFalse(any(c[0]=='start' for c in self.driver.calls))

    def test_cleanup_rejects_foreign_or_symlink_and_retains_bytes(self):
        root=Path(self.p['host']['output']); root.mkdir(parents=True)
        r2.save(root/'owner.json',{'execution_id':self.p['execution_id'],'package_sha256':self.package_hash})
        stores = root/'stores'; stores.mkdir()
        (stores/'FOREIGN').mkdir()
        with self.assertRaisesRegex(ValueError, 'FOREIGN'):
            ex.cleanup_store(root, root, float('inf'), self.p)
        self.assertTrue((stores/'FOREIGN').exists())

    def test_preconstruction_guards_are_fail_closed_with_doubles(self):
        for event in ('socket.connect','socket.getaddrinfo','socket.sendto','subprocess.Popen','os.exec','os.fork'):
            with self.assertRaises(PermissionError):
                ex.worker_audit(event, ())
        class SyntheticLLM:
            def generate_response(self):
                raise AssertionError('must not reach synthetic body')
        ex.guard_llm(SyntheticLLM)
        with self.assertRaisesRegex(PermissionError, 'INTERNAL_LLM'):
            SyntheticLLM().generate_response()

    def test_complete_runtime_map_detects_added_empty_dirs_and_changed_bytes(self):
        runtime = self.root/'runtime'; (runtime/'runtime').mkdir(parents=True); (runtime/'model-cache').mkdir()
        (runtime/'requirements.lock').write_text('SYNTHETIC')
        file = runtime/'runtime/source.py'; file.write_text('original')
        original = ex.runtime_map(runtime)
        file.write_text('drift'); self.assertNotEqual(ex.runtime_map(runtime),original)
        file.write_text('original'); (runtime/'model-cache/added').mkdir()
        self.assertNotEqual(ex.runtime_map(runtime),original)

    def test_package_source_and_runtime_drift_before_dispatch(self):
        current = self.root/'source.py'; current.write_text('original')
        staged = self.root/'source-current/source.py'; staged.parent.mkdir(); staged.write_text('original')
        (self.root/'source-qualified').mkdir()
        runtime = self.root/'runtime'; (runtime/'runtime').mkdir(parents=True); (runtime/'model-cache').mkdir()
        (runtime/'requirements.lock').write_text('SYNTHETIC')
        p = r2.read(self.package); p['sources']={str(current):r2.sha(current.read_bytes())}
        p['runtime_files']=ex.runtime_map(runtime); p['docker_sha256']=r2.sha(Path(ex.DOCKER).read_bytes())
        changed=self.root/'changed-package.json'; r2.save(changed,p); digest=r2.sha(changed.read_bytes())
        ex.verify_package(changed,digest)
        current.write_text('drift')
        with self.assertRaisesRegex(ValueError,'SOURCE_DRIFT'):
            ex.verify_package(changed,digest)
        current.write_text('original'); (runtime/'model-cache/new').write_text('drift')
        with self.assertRaisesRegex(ValueError,'RUNTIME_DRIFT'):
            ex.verify_package(changed,digest)

    def test_extra_capsule_module_and_budget_custody_tamper_reject(self):
        for key in ('current_root','qualified_root'):
            Path(self.p['source_mounts'][key]).mkdir()
        ex.capsule_membership(self.p,False)
        extra=Path(self.p['source_mounts']['current_root'])/'shadow.py'; extra.write_text('unreviewed')
        with self.assertRaisesRegex(ValueError,'CAPSULE_MEMBERSHIP'):
            ex.capsule_membership(self.p,False)
        folder=self.root/'phase'; folder.mkdir()
        counts={k:0 for k in ex.contract()['sdk_calls']}
        budget=ex.Budget(folder,counts,0); budget.reserve('add')
        with self.assertRaisesRegex(ValueError,'CAPTURE_BUDGET'):
            ex.verify_budget(folder,counts,0)

    def test_expiry_during_preflight_cannot_create(self):
        clock=[0.0]
        r2.save(self.grant,self.admitted_grant())
        Path(self.p['host']['output']).parent.mkdir(parents=True)
        driver=SyntheticDocker(self.p)
        calls=[0]
        def verify(*args,**kwargs):
            calls[0]+=1
            if calls[0]>1:
                clock[0]=1300.0
            return deepcopy(self.p)
        with patch.object(ex,'verify_package',side_effect=verify), patch.object(ex.time,'monotonic',side_effect=lambda:clock[0]):
            result=ex.execute(self.package,self.package_hash,self.review,self.review_hash,self.grant,driver=driver)
        self.assertEqual(result,'INCOMPLETE')
        self.assertFalse(any(c[0]=='create' for c in driver.calls))

    def test_exited_observation_after_phase_deadline_is_incomplete(self):
        clock=[0.0]
        original=SyntheticDocker.call
        def slow_start(driver,*args):
            result=original(driver,*args)
            if args[0]=='start':
                clock[0]=301.0
            return result
        with patch.object(SyntheticDocker,'call',slow_start),patch.object(ex.time,'monotonic',side_effect=lambda:clock[0]):
            self.assertEqual(self.supervise(),'INCOMPLETE')
        self.assertEqual(sum(c[0]=='create' for c in self.driver.calls),1)
        self.assertEqual(self.driver.objects,{})

    def test_console_bytes_precede_every_removal(self):
        self.assertEqual(self.supervise(),'COMPLETED')
        for n,args in enumerate(self.driver.calls):
            if args[0]=='rm':
                self.assertIn(('console',args[-1]),self.driver.calls[:n])
        root=Path(self.p['host']['output'])
        for phase in self.p['contract']['phases']:
            console=root/'supervisor'/(phase+'-console.log')
            receipt=r2.read(console.with_suffix('.json'))
            self.assertEqual(receipt['sha256'],r2.sha(console.read_bytes()))

    def test_failed_console_retains_stopped_container_and_store_without_retry(self):
        self.assertEqual(self.supervise('console'),'INCOMPLETE')
        self.assertEqual(sum(c[0]=='console' for c in self.driver.calls),1)
        self.assertFalse(any(c[0]=='rm' for c in self.driver.calls))
        self.assertTrue(self.driver.objects)
        self.assertTrue(all(not c['State']['Running'] for c in self.driver.objects.values()))
        root=Path(self.p['host']['output'])
        self.assertTrue((root/'stores/UPDATE/qdrant/SYNTHETIC_STORE').exists())
        self.assertTrue((root/'supervisor/UPDATE-initial-console.log').exists())
        self.assertTrue((root/'supervisor/cleanup-error.json').exists())

    def test_console_reader_enforces_byte_and_time_bounds_with_pipe_double(self):
        class PipeProcess:
            def __init__(self,*args,**kwargs):
                read_fd,write_fd=os.pipe()
                os.write(write_fd,b'SYNTHETIC_CONSOLE\n'); os.close(write_fd)
                self.stdout=os.fdopen(read_fd,'rb')
            def poll(self):return 0
            def wait(self,timeout=None):return 0
        driver=ex.Docker(); driver.deadline=float('inf')
        c=deepcopy(ex.contract()); c['limits']['working_bytes']=3
        with patch.object(ex.subprocess,'Popen',PipeProcess),patch.object(ex,'working_bytes',return_value=0),patch.object(ex,'contract',return_value=c):
            with self.assertRaisesRegex(ValueError,'CONSOLE_WORKING_BUDGET'):
                driver.console('a'*64,self.root/'partial.log',self.root)
        self.assertEqual((self.root/'partial.log').read_bytes(),b'SYN')
        with patch.object(ex.subprocess,'Popen',PipeProcess),patch.object(ex.time,'monotonic',side_effect=[0,0,21]):
            with self.assertRaisesRegex(ValueError,'CONSOLE_DEADLINE'):
                driver.console('b'*64,self.root/'timed-out.log',self.root)


if __name__ == '__main__':
    unittest.main()
