"""Sequential local-Docker supervisor for LC12; no cloud or SSH operations."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import time


def collect(config, lc, root):
    """Called only by the explicitly invoked collect entrypoint after authorization."""
    run_id = config['run_id']
    if not re.fullmatch(r'lc12-[a-z0-9-]{1,32}', run_id):
        raise ValueError('FRESH_LC12_RUN_ID_REQUIRED')
    qualified = Path(config['qualified_root']).resolve()
    runtime = Path(config['runtime_root']).resolve()
    mem0 = Path(config['embedding_runtime']).resolve()
    output = Path(config['output_parent']).resolve() / run_id
    registered = json.loads((root / 'manifests/crossarch-units-v1.json').read_bytes())
    if registered != lc.plan():
        raise ValueError('REGISTERED_LEDGER_DRIFT')
    docker = [config.get('docker', 'docker')]
    started = time.time()
    deadline = started + 3600
    active_deadline = deadline
    owned = []
    resource_ordinal = 0
    docker_operations = 0
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    lc.write(output / 'ledger.json', lc.plan())
    outcomes = {u['unit_id']: {'status': 'UNKNOWN', 'checkpoints': {c: 'UNKNOWN' for c in lc.CHECKPOINTS}}
                for u in lc.plan()['units']}

    def command(args, *, timeout=60, raw_output=None, allow_failure=False, cleanup=False):
        nonlocal docker_operations
        if docker_operations >= (1000 if cleanup else 936):
            raise RuntimeError('DOCKER_OPERATION_LIMIT_CLEANUP_RESERVE')
        docker_operations += 1
        remaining_time = (started + 4200 if cleanup else active_deadline) - time.time()
        if remaining_time <= 0:
            raise TimeoutError('SUPERVISOR_DEADLINE')
        timeout = min(timeout, remaining_time)
        if raw_output is None:
            response = subprocess.run(docker + args, capture_output=True, timeout=timeout)
            if response.returncode and not allow_failure:
                raise RuntimeError('DOCKER_FAILED: ' + response.stderr.decode(errors='replace')[-500:])
            return response if allow_failure else response.stdout
        remaining = 10 * 1024**3 - sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
        if remaining <= 0:
            raise RuntimeError('EVIDENCE_CAP')
        process = subprocess.Popen(docker + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Streaming copy with an outer subprocess deadline, no unbounded in-memory dump.
        import selectors
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        selector.register(process.stderr, selectors.EVENT_READ)
        end, count, errors = time.time() + timeout, 0, bytearray()
        try:
            with Path(raw_output).open('xb') as stream:
                while selector.get_map():
                    if time.time() >= end:
                        raise TimeoutError('COPY_DEADLINE_PARTIAL_FILE_RETAINED')
                    for key, _ in selector.select(timeout=.2):
                        data = os.read(key.fileobj.fileno(), 65536)
                        if not data:
                            selector.unregister(key.fileobj)
                            continue
                        if key.fileobj is process.stdout:
                            count += len(data)
                            if count > remaining:
                                raise RuntimeError('EVIDENCE_CAP_PARTIAL_COPY_RETAINED')
                            stream.write(data)
                        else:
                            errors.extend(data[:max(0, 4096-len(errors))])
                stream.flush()
                os.fsync(stream.fileno())
            if process.wait(timeout=2):
                raise RuntimeError('COPY_FAILED:' + errors.decode(errors='replace'))
        finally:
            selector.close()
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            process.stdout.close()
            process.stderr.close()
        data_hash = __import__('hashlib').sha256()
        with Path(raw_output).open('rb') as stream:
            for block in iter(lambda: stream.read(1024**2), b''):
                data_hash.update(block)
        return {'path': str(raw_output), 'bytes': count, 'sha256': data_hash.hexdigest()}

    def inspect(kind, name, *, cleanup=False):
        return json.loads(command([kind, 'inspect', name], cleanup=cleanup))[0]

    def own(kind, name):
        nonlocal resource_ordinal
        probe = command([kind, 'inspect', name], timeout=10, allow_failure=True)
        message = probe.stderr.decode(errors='replace').lower()
        if probe.returncode == 0:
            raise ValueError('EXISTING_RESOURCE_NAME_REFUSED:' + name)
        if name.lower() not in message or not ('no such' in message or 'not found' in message):
            raise ValueError('RESOURCE_ABSENCE_UNKNOWN:' + name)
        # An ambiguous create is never retried; cleanup verifies this label.
        resource_ordinal += 1
        owned.append((kind, name))
        lc.write(output / 'resource-intents' / f'{resource_ordinal:03d}.json', {'kind': kind, 'name': name})

    def remove(kind, name):
        value = inspect(kind, name, cleanup=True)
        labels = value['Config'].get('Labels', {}) if kind == 'container' else value.get('Labels', {})
        if labels.get('memlife.lc12') != run_id:
            raise RuntimeError('FOREIGN_RESOURCE_CLEANUP_REFUSED')
        if kind == 'container':
            command(['stop', '--time', '5', name], timeout=15, cleanup=True)
            command(['logs', name], raw_output=output / 'logs' / (name + '.log'), timeout=20, cleanup=True)
        command([kind, 'rm', name], cleanup=True)
        owned.remove((kind, name))

    def db_ready(db):
        nonlocal docker_operations
        for _ in range(20):
            if time.time() >= min(deadline, active_deadline):
                raise TimeoutError('COLLECTION_DEADLINE')
            if docker_operations >= 936:
                raise RuntimeError('DOCKER_OPERATION_LIMIT_CLEANUP_RESERVE')
            docker_operations += 1
            result = subprocess.run(docker + ['exec', db, 'pg_isready', '-U', 'memlife'],
                                    capture_output=True, timeout=max(.001, min(3, active_deadline-time.time())))
            if result.returncode == 0:
                return
            time.sleep(max(0, min(1, active_deadline-time.time())))
        raise TimeoutError('DATABASE_READINESS_BOUND')

    def snapshot(state, unit_out, phase, db=None):
        if db:
            command(['stop', '--time', '10', db], timeout=20)
            value = inspect('container', db)
            if value['State']['Running']:
                raise RuntimeError('DB_NOT_CLOSED')
            lc.write(unit_out / (phase + '-database-exited.json'), value)
            identity = command(['cp', db + ':/var/lib/postgresql/data', '-'],
                               raw_output=unit_out / (phase + '-database.tar'), timeout=60)
        else:
            destination = unit_out / (phase + '-state.tar')
            remaining = 10 * 1024**3 - sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
            class BoundedArchive:
                def __init__(self, stream):
                    self.stream, self.written = stream, 0
                def write(self, data):
                    self.written += len(data)
                    if self.written > remaining or time.time() >= active_deadline:
                        raise RuntimeError('SNAPSHOT_SIZE_OR_TIME_BOUND_PARTIAL_RETAINED')
                    return self.stream.write(data)
            with destination.open('xb') as stream:
                with tarfile.open(fileobj=BoundedArchive(stream), mode='w|', dereference=False) as archive:
                    archive.add(state, arcname='state')
                stream.flush()
                os.fsync(stream.fileno())
            with destination.open('rb') as stream:
                os.fsync(stream.fileno())
            digest = __import__('hashlib').sha256()
            with destination.open('rb') as stream:
                for block in iter(lambda: stream.read(1024**2), b''):
                    digest.update(block)
            identity = {'path': str(destination), 'sha256': digest.hexdigest(),
                        'bytes': destination.stat().st_size}
        lc.write(unit_out / (phase + '-closed-snapshot.json'), identity)
        return identity

    def phase(unit, unit_out, state, phase_name, unit_deadline, network='none', environment=()):
        if time.time() >= unit_deadline or time.time() >= deadline:
            raise TimeoutError('DEADLINE_BEFORE_CREATE')
        name = run_id + '-' + unit['unit_id'].lower() + '-' + phase_name
        own('container', name)
        args = ['create', '--pull=never', '--name', name, '--label', 'memlife.lc12=' + run_id,
                '--network', network, '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                '--cpus', '2', '--memory', '6g', '--memory-swap', '6g', '--pids-limit', '512',
                '--user', f'{os.getuid()}:{os.getgid()}', '--tmpfs', '/tmp:rw,nosuid,nodev,size=1g']
        mounts = [(root / 'src', '/experiment/src', True), (root / 'scripts', '/experiment/scripts', True),
                  (qualified / 'src', '/qualified/src', True), (qualified / 'scripts', '/qualified/scripts', True),
                  (runtime / unit['provider'], '/runtime', True), (state, '/state', False),
                  (unit_out, '/evidence', False), (output, '/campaign', False)]
        if unit['provider'] == 'openviking':
            mounts.append((mem0, '/task', True))
        for source, target, readonly in mounts:
            args += ['--mount', f'type=bind,src={source},dst={target}' + (',readonly' if readonly else '')]
        env = ['HOME=/tmp/home', 'PYTHONDONTWRITEBYTECODE=1', 'HF_HUB_OFFLINE=1',
               'TRANSFORMERS_OFFLINE=1', 'HF_HUB_DISABLE_TELEMETRY=1', 'OTEL_SDK_DISABLED=true',
               'TOKENIZERS_PARALLELISM=false', 'OMP_NUM_THREADS=2', 'MKL_NUM_THREADS=2',
               'LC12_UNIT_DEADLINE=' + str(unit_deadline)] + list(environment)
        for item in env:
            args += ['-e', item]
        args += [lc.BASE_IMAGE, '/runtime/.venv/bin/python', '-I', '-B',
                 '/experiment/scripts/research/crossarch.py', '_service', '--phase', phase_name, '--run-id', run_id]
        identifier = command(args, timeout=15).decode().strip()
        created = inspect('container', identifier)
        lc.write(unit_out / (phase_name + '-container-created.json'), created)
        try:
            command(['start', identifier], timeout=10)
            command(['wait', identifier], timeout=max(.1, min(unit_deadline, deadline)-time.time()))
        finally:
            command(['stop', '--time', '5', identifier], timeout=15, cleanup=True)
            exited = inspect('container', identifier, cleanup=True)
            lc.write(unit_out / (phase_name + '-container-exited.json'), exited)
            remove('container', name)
        if exited['State']['Running'] or exited['State']['ExitCode'] != 0 or exited['State'].get('OOMKilled'):
            raise RuntimeError('NATIVE_PHASE_FAILED_PARTIAL_RETAINED')
        processes = json.loads((unit_out / (phase_name + '-processes.json')).read_bytes())
        result = json.loads((unit_out / phase_name / 'result.json').read_bytes())
        if not processes['all_exited'] or result['status'] != 'COMPLETED':
            raise RuntimeError('PHASE_COMPLETION_NOT_ESTABLISHED')
        return created['Id'], result

    primary, cleanup_errors = None, []
    try:
        (output / 'logs').mkdir()
        info = json.loads(command(['info', '--format', '{{json .}}']))
        decision = lc.resource_decision(info['NCPU'], info['MemTotal'], shutil.disk_usage(output).free)
        lc.write(output / 'resource-decision.json', decision)
        if decision['status'] != 'PASS':
            raise RuntimeError('RESOURCE_GATE: ' + '; '.join(decision['reasons']))
        if info.get('OSType') != 'linux' or info.get('Architecture') not in ('x86_64', 'amd64'):
            raise ValueError('QUALIFIED_LINUX_AMD64_DOCKER_REQUIRED')
        mounted = subprocess.run(['findmnt', '--noheadings', '--output', 'TARGET', '--source', '/dev/sdb'],
                                 capture_output=True, timeout=5, check=True).stdout.decode().strip()
        if not mounted or not output.is_relative_to(Path(mounted).resolve()):
            raise ValueError('OUTPUT_MUST_USE_DYNAMIC_SDB_MOUNT')
        lc.write(output / 'volume-location.json', {'source': '/dev/sdb', 'resolved_mount': mounted})
        for image in (lc.BASE_IMAGE, config['database_image']):
            if not re.fullmatch(r'sha256:[0-9a-f]{64}', image):
                raise ValueError('CACHED_IMAGE_DIGEST_REQUIRED')
            command(['image', 'inspect', image])
        if config['database_image'] != lc.DATABASE_IMAGE:
            raise ValueError('QUALIFIED_DATABASE_IMAGE_REQUIRED')
        pins = json.loads((root / 'manifests/crossarch-qualified-reuse-v1.json').read_bytes())
        for relative, digest in pins['files'].items():
            if lc.sha((qualified / relative).read_bytes()) != digest:
                raise ValueError('QUALIFIED_SOURCE_DRIFT:' + relative)
        for path in (runtime / 'openviking/.venv/bin/python', runtime / 'hindsight/.venv/bin/python',
                     mem0 / 'runtime/.venv/bin/python'):
            lc.retained_interpreter(path)
        source_ids = {'qualified': pins['files'], 'implementation': {str(p.relative_to(root)): lc.sha(p.read_bytes())
                     for p in (root / 'src/memlife/crossarch.py', root / 'scripts/research/crossarch.py',
                               root / 'scripts/research/crossarch_host.py')}}
        lc.write(output / 'source-identities.json', source_ids)
        for relative in source_ids['implementation']:
            lc.write(output / 'source-snapshot/implementation' / relative, (root / relative).read_bytes(), raw=True)
        for relative in pins['files']:
            lc.write(output / 'source-snapshot/qualified' / relative, (qualified / relative).read_bytes(), raw=True)
        for unit in lc.plan()['units']:
            if time.time() >= deadline:
                raise TimeoutError('COLLECTION_DEADLINE')
            unit_deadline = min(time.time() + 300, deadline)
            active_deadline = unit_deadline
            unit_out = output / unit['unit_id']
            unit_out.mkdir()
            state = unit_out / 'state'
            state.mkdir()
            lc.write(unit_out / 'unit.json', unit)
            db, network, env = None, 'none', []
            if unit['provider'] == 'hindsight':
                network = run_id + '-' + unit['unit_id'].lower() + '-net'
                volume, db = network + '-pg', network + '-db'
                own('network', network)
                command(['network', 'create', '--internal', '--label', 'memlife.lc12=' + run_id, network])
                own('volume', volume)
                command(['volume', 'create', '--label', 'memlife.lc12=' + run_id, volume])
                own('container', db)
                command(['run', '--pull=never', '--detach', '--name', db, '--label', 'memlife.lc12=' + run_id,
                         '--network', network, '--network-alias', 'db', '--memory', '1g', '--memory-swap', '1g',
                         '--cpus', '1', '--pids-limit', '128', '--mount',
                         f'type=volume,src={volume},dst=/var/lib/postgresql/data',
                         '-e', 'POSTGRES_USER=memlife', '-e', 'POSTGRES_DB=memlife',
                         '-e', 'POSTGRES_HOST_AUTH_METHOD=trust', config['database_image']])
                db_ready(db)
                env = hindsight_environment(unit['unit_id'])
            else:
                lc.write(state / 'ov.conf', openviking_configuration())
            initial_id, first = phase(unit, unit_out, state, 'initial', unit_deadline, network, env)
            outcomes[unit['unit_id']] = {'status': 'PARTIAL', 'checkpoints': first['checkpoints']}
            first_hash = lc.sha(lc.canonical(first))
            snap = snapshot(state, unit_out, 'initial', db)
            if db:
                command(['start', db])
                db_ready(db)
            if lc.sha(lc.canonical(json.loads((unit_out / 'initial/result.json').read_bytes()))) != first_hash:
                raise ValueError('PREDECESSOR_CHANGED')
            reopen_id, second = phase(unit, unit_out, state, 'reopen', unit_deadline, network, env)
            if reopen_id == initial_id:
                raise ValueError('DISTINCT_CONTAINER_REQUIRED')
            snapshot(state, unit_out, 'reopen', db)
            lc.write(unit_out / 'reopen-evidence.json', {'initial_container': initial_id, 'reopen_container': reopen_id,
                'closed_snapshot': snap, 'initial_result_sha256': first_hash, 'same_state_path': str(state),
                'process_evidence': ['initial-container-exited.json', 'reopen-container-created.json',
                                     'initial-processes.json', 'reopen-processes.json'], 'model_calls': 0})
            outcomes[unit['unit_id']] = {'status': 'COMPLETED', 'checkpoints': {
                **first['checkpoints'], **second['checkpoints']}}
            # Preserve state archives first. Never remove uncertain live data.
            if db:
                remove('container', db)
                remove('volume', volume)
                remove('network', network)
            shutil.rmtree(state)
    except Exception as exc:
        primary = {'class': type(exc).__name__, 'message': str(exc)[:800]}
    finally:
        # Unfinished DB volume/store remains recoverable; stop only owned containers.
        for kind, name in list(reversed(owned)):
            try:
                if kind == 'container':
                    remove(kind, name)
                # Incomplete volume/network resources are retained, explicitly listed.
            except Exception as exc:
                cleanup_errors.append({'kind': kind, 'name': name, 'error': str(exc)[:400]})
        for unit in lc.plan()['units']:
            paths = [output / unit['unit_id'] / phase / 'result.json' for phase in ('initial', 'reopen')]
            for path in paths:
                if path.exists():
                    observed = json.loads(path.read_bytes())
                    for name, checkpoint in observed.get('checkpoints', {}).items():
                        if isinstance(checkpoint, dict):
                            outcomes[unit['unit_id']]['checkpoints'][name] = checkpoint
                    outcomes[unit['unit_id']]['partial_artifacts'] = str(path.parent.parent)
        lc.write(output / 'collection-result.json', {'status': 'COMPLETED' if primary is None and not cleanup_errors else 'UNKNOWN',
            'units': outcomes, 'error': primary, 'cleanup_errors': cleanup_errors,
            'retained_resources': owned, 'elapsed_seconds': time.time()-started, 'docker_operations': docker_operations,
            'native_observations': 'SEE_PHASE_ARTIFACTS', 'hosted_requests': 0})
    if primary or cleanup_errors:
        raise RuntimeError('COLLECTION_STOPPED_PARTIAL_AND_UNPERFORMED_OBSERVATIONS_RETAINED')


def openviking_configuration():
    return {'server': {'host': '127.0.0.1', 'port': 1933, 'workers': 1, 'auth_mode': 'dev', 'with_bot': False},
        'storage': {'workspace': '/state/openviking-store', 'agfs': {'backend': 'local'}, 'vectordb': {'backend': 'local'}},
        'embedding': {'dense': {'provider': 'openai', 'model': 'paraphrase-MiniLM-L3-v2',
            'api_base': 'http://127.0.0.1:1934/v1', 'api_key': 'synthetic-local', 'dimension': 384,
            'input': 'text', 'encoding_format': 'float'}, 'max_concurrent': 1, 'max_retries': 0},
        'vlm': {}, 'memory': {'extraction_enabled': False, 'session_skill_extraction_enabled': False}}


def hindsight_environment(worker):
    return ['HINDSIGHT_API_DATABASE_URL=postgresql://memlife@db:5432/memlife',
        'HINDSIGHT_API_VECTOR_EXTENSION=pgvector', 'HINDSIGHT_API_TEXT_SEARCH_EXTENSION=native',
        'HINDSIGHT_API_EMBEDDINGS_PROVIDER=onnx', 'HINDSIGHT_API_EMBEDDINGS_ONNX_MODEL_ID=intfloat/multilingual-e5-small',
        'HINDSIGHT_API_EMBEDDINGS_ONNX_MODEL_PATH=/runtime/model/onnx/model.onnx',
        'HINDSIGHT_API_EMBEDDINGS_ONNX_TOKENIZER_NAME_OR_PATH=/runtime/model',
        'HINDSIGHT_API_EMBEDDINGS_ONNX_DIMENSIONS=384', 'HINDSIGHT_API_EMBEDDINGS_ONNX_POOLING=mean',
        'HINDSIGHT_API_EMBEDDINGS_ONNX_NORMALIZE=true', 'HINDSIGHT_API_EMBEDDINGS_ONNX_QUERY_PREFIX=query: ',
        'HINDSIGHT_API_EMBEDDINGS_ONNX_PASSAGE_PREFIX=passage: ', 'HINDSIGHT_API_RERANKER_PROVIDER=rrf',
        'HINDSIGHT_API_LLM_PROVIDER=none', 'HINDSIGHT_API_RETAIN_EXTRACTION_MODE=chunks',
        'HINDSIGHT_API_ENABLE_OBSERVATIONS=false', 'HINDSIGHT_API_ENABLE_AUTO_CONSOLIDATION=false',
        'HINDSIGHT_API_ENABLE_OBSERVATION_HISTORY=true', 'HINDSIGHT_API_ENABLE_MENTAL_MODEL_HISTORY=true',
        'HINDSIGHT_API_WORKERS=1', 'HINDSIGHT_API_WORKER_ENABLED=true', 'HINDSIGHT_API_WORKER_MAX_SLOTS=1',
        'HINDSIGHT_API_WORKER_ID=' + worker, 'HINDSIGHT_API_WORKER_CONSOLIDATION_RESERVED_SLOTS=0',
        'HINDSIGHT_API_MCP_ENABLED=false']
