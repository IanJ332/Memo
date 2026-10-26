"""Bounded R2-only supervisor and worker. Import is offline; execute needs a grant.

Adapted from the qualified A3 local caller's create/inspect/start/closeout pattern.
Never import or invoke its historical fixed-path entrypoints. JSON verifies byte
bindings, not human authorization; supported external approval remains mandatory.
"""
from datetime import datetime, timezone
import os
import csv
import base64
from pathlib import Path
import re
import selectors
import shutil
import socket
import subprocess
import sys
import time

from memlife import r2

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / 'manifests/r2-execution-contract-v1.json'
DOCKER = '/usr/local/bin/docker'
ENDPOINT = 'unix:///Users/ian/.docker/run/docker.sock'
need, read, save, sha, canonical = r2.need, r2.read, r2.save, r2.sha, r2.canonical


def contract():
    value = read(CONTRACT)
    need(value['protocol_sha256'] == r2.DESIGN_SHA256, 'PROTOCOL_CONTRACT')
    need(value['sdk_calls'] == r2.design()['bounds']['sdk_calls'], 'SDK_CONTRACT')
    need(value['container']['memory_bytes'] == 8 * 1024**3, 'UNCHANGED_MEMORY')
    return value


def resources(info, running, free_disk):
    c = contract()
    need(info['MemTotal'] >= c['admission']['minimum_vm_bytes'], 'VM_MEMORY_CAPACITY')
    need(info['NCPU'] >= c['container']['cpus'], 'CPU_CAPACITY')
    need(info['MemoryLimit'] is True and info['PidsLimit'] is True, 'RESOURCE_ENFORCEMENT')
    need(not running, 'UNRELATED_RUNNING_WORKLOAD')
    need(free_disk >= c['admission']['minimum_disk_bytes'], 'WORKING_DISK')
    return {'memory_bytes': info['MemTotal'], 'headroom_bytes': info['MemTotal'] - 8 * 1024**3,
            'cpus': info['NCPU'], 'free_disk_bytes': free_disk,
            'basis': 'CAPACITY_AND_PLANNING_MARGIN_NOT_FREE_RAM_OR_MEASURED_R2_PEAK'}


def file_map(root, *, runtime=False):
    """Pin complete mounted membership. Qualified venv interpreter links are literal.

    No symlink is followed. Only qualified runtime bin interpreter links may point
    into the pinned image; all other links must stay inside the mounted root.
    """
    root = Path(root)
    need(root.is_dir() and root.resolve() == root, 'CANONICAL_PIN_ROOT')
    result = {}
    for p in sorted(root.rglob('*')):
        name = str(p.relative_to(root))
        if p.is_symlink():
            target = os.readlink(p)
            image_python = runtime and name.startswith('.venv/bin/python') and target in (
                '/usr/local/bin/python', 'python', 'python3', 'python3.12')
            need(image_python or p.resolve().is_relative_to(root), 'PIN_SYMLINK_ESCAPE')
            result[name] = {'link': target}
        elif p.is_file():
            need(p.stat().st_nlink == 1, 'PIN_HARDLINK')
            result[name] = {'sha256': sha(p.read_bytes()), 'bytes': p.stat().st_size}
        else:
            need(p.is_dir(), 'PIN_SPECIAL_FILE')
            result[name] = {'directory': True}
    return result


def runtime_map(root):
    # Wheelhouse is not mounted or used; retain the existing qualified closure.
    root = Path(root)
    result = {}
    for name in ('runtime', 'model-cache'):
        for path, identity in file_map(root / name, runtime=True).items():
            result[name + '/' + path] = identity
    result['requirements.lock'] = {'sha256': sha((root / 'requirements.lock').read_bytes())}
    return result


def translated(path, package, worker):
    if not worker:
        return Path(path)
    for key, mount in (('current_root', '/r2'), ('qualified_root', '/qualified')):
        root = Path(package['host'][key])
        if Path(path).is_relative_to(root):
            return Path(mount) / Path(path).relative_to(root)
    raise ValueError('UNMAPPED_SOURCE')


def staged_path(path, package):
    for key in ('current_root', 'qualified_root'):
        source_root = Path(package['host'][key])
        if Path(path).is_relative_to(source_root):
            return Path(package['source_mounts'][key]) / Path(path).relative_to(source_root)
    raise ValueError('UNMAPPED_STAGED_SOURCE')


def capsule_membership(package, worker):
    for key, mount in (('current_root', '/r2'), ('qualified_root', '/qualified')):
        original = Path(package['host'][key])
        expected = {str(Path(name).relative_to(original)): digest for name, digest in package['sources'].items()
                    if Path(name).is_relative_to(original)}
        directories = {str(parent) for name in expected for parent in Path(name).parents if str(parent) != '.'}
        root = Path(mount) if worker else Path(package['source_mounts'][key])
        actual = r2.tree(root)
        need({row['path']: row['sha256'] for row in actual if row['type'] == 'file'} == expected and
             {row['path'] for row in actual if row['type'] == 'directory'} == directories, 'SOURCE_CAPSULE_MEMBERSHIP')


def verify_package(path, expected, *, worker=False):
    need(sha(Path(path).read_bytes()) == expected, 'PACKAGE_HASH')
    p = read(path)
    need(p['schema'] == 'MEMLIFE_R2_EXECUTION_PACKAGE_V1', 'PACKAGE_SCHEMA')
    need(p['contract'] == contract(), 'EXECUTION_CONTRACT_DRIFT')
    need(p['protocol_sha256'] == r2.DESIGN_SHA256, 'SCIENCE_DRIFT')
    capsule_membership(p, worker)
    for name, digest in p['sources'].items():
        file = translated(name, p, worker)
        need(not file.is_symlink() and sha(file.read_bytes()) == digest, 'SOURCE_DRIFT:' + name)
        if not worker:
            staged = staged_path(name, p)
            need(not staged.is_symlink() and sha(staged.read_bytes()) == digest, 'STAGED_SOURCE_DRIFT')
    runtime = Path('/runtime') if worker else Path(p['host']['runtime_root'])
    need(runtime_map(runtime) == p['runtime_files'], 'RUNTIME_DRIFT')
    need(re.fullmatch(r'R2EX-[0-9]{8}-[a-f0-9]{12}', p['execution_id']), 'EXECUTION_ID')
    output = Path(p['host']['output'])
    current = Path(p['host']['current_root'])
    need(output.parent == current / '.local/r2-runs' and output.name == p['execution_id'], 'OWNED_OUTPUT')
    need(p['host']['endpoint'] == ENDPOINT and p['host']['docker'] == DOCKER, 'LOCAL_DOCKER_ONLY')
    if not worker:
        need(sha(Path(DOCKER).read_bytes()) == p['docker_sha256'], 'DOCKER_CLIENT_DRIFT')
    return p


def qualified_runtime(qualified_root, runtime_root):
    """Reuse original qualification or reject drift; never repin current bytes."""
    old = Path(qualified_root) / 'artifacts/native-runtime-qualification-20261022-v1'
    receipt = old / 'installed-record-verification.json'
    need(sha(receipt.read_bytes()) == 'af917fd3e6644f979d597513441f0833d45794ccb00d64ac2c92b053a4adf4ce', 'QUALIFIED_RECORD_RECEIPT')
    previous = read(receipt)
    root = Path(runtime_root)
    need(sha((root / 'requirements.lock').read_bytes()) == '713595e24f15917fc2eaf0f8e22a722f04bb13c2cab4a4cdf8c897b5bf43ca6a', 'QUALIFIED_LOCK')
    site = root / 'runtime/.venv/lib/python3.12/site-packages'
    need({p.name for p in site.glob('*.dist-info')} == {d['distribution'] for d in previous['distributions']}, 'INSTALLED_MEMBERSHIP')
    checked = 0
    for dist in previous['distributions']:
        folder = site / dist['distribution']
        need(sha((folder / 'RECORD').read_bytes()) == dist['record_sha256'] and
             sha((folder / 'METADATA').read_bytes()) == dist['metadata_sha256'], 'INSTALLED_IDENTITY')
        for name, expected, size in csv.reader((folder / 'RECORD').read_text().splitlines()):
            if not expected:
                continue
            target = (site / name).resolve()
            need(target.is_relative_to(root / 'runtime/.venv'), 'INSTALLED_PATH')
            algorithm, encoded = expected.split('=', 1)
            actual = base64.urlsafe_b64encode(bytes.fromhex(sha(target.read_bytes()))).decode().rstrip('=')
            need(algorithm == 'sha256' and actual == encoded and target.stat().st_size == int(size), 'INSTALLED_BYTES')
            checked += 1
    need(checked == previous['checked_hashed_files'], 'INSTALLED_RECORD_COUNT')
    plan = root.parent / 'acquisition-plan.json'
    need(sha(plan.read_bytes()) == '7a794cf70e14859d643ae2c598ef32bde10299805635ba163768bef71d168365', 'QUALIFIED_ACQUISITION_PLAN')
    for row in read(plan):
        if '/model-cache/' not in row['target']:
            continue
        target = root.parent / row['target']
        raw = target.read_bytes()
        if row.get('sha256'):
            need(sha(raw) == row['sha256'], 'MODEL_ARTIFACT_DRIFT')
        else:
            import hashlib
            need(hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['git_blob_sha1'], 'MODEL_BLOB_DRIFT')


CURRENT_FILES = (
    'src/memlife/__init__.py', 'src/memlife/r2.py', 'src/memlife/r2_execution.py',
    'scripts/research/r2.py', 'scripts/research/r2_execution.py',
    'manifests/r2-lifecycle-candidate-v1.json', 'manifests/r2-execution-contract-v1.json',
    'manifests/r1-qualified-source-pins-v1.json', 'tests/research/test_r2.py',
    'tests/research/test_r2_execution.py', 'docs/research/R2_EXECUTION_PACKAGE.md')


def prepare(directory, qualified_root, runtime_root):
    """Offline exact package; receipt and unapproved grant are separate later steps."""
    directory, qualified_root, runtime_root = [Path(p).resolve() for p in (directory, qualified_root, runtime_root)]
    need(not directory.exists(), 'FRESH_PACKAGE_ONLY')
    r2.qualified_sources(qualified_root)
    qualified_runtime(qualified_root, runtime_root)
    from uuid import uuid4
    execution_id = 'R2EX-' + datetime.now(timezone.utc).strftime('%Y%m%d') + '-' + uuid4().hex[:12]
    sources = {str(qualified_root / name): expected for name, expected in read(r2.PINS)['files'].items()}
    sources.update({str(ROOT / name): sha((ROOT / name).read_bytes()) for name in CURRENT_FILES})
    p = {'schema': 'MEMLIFE_R2_EXECUTION_PACKAGE_V1', 'execution_id': execution_id,
         'status': 'PROSPECTIVE_NOT_EXECUTED', 'protocol_sha256': r2.DESIGN_SHA256,
         'contract': contract(), 'image_id': r2.design()['runtime']['image_id'], 'sources': sources,
         'runtime_files': runtime_map(runtime_root), 'docker_sha256': sha(Path(DOCKER).read_bytes()),
         'host': {'current_root': str(ROOT), 'qualified_root': str(qualified_root),
                  'runtime_root': str(runtime_root), 'output': str(ROOT / '.local/r2-runs' / execution_id),
                  'endpoint': ENDPOINT, 'docker': DOCKER}, 'package_host_dir': str(directory),
         'source_mounts': {'current_root': str(directory / 'source-current'),
                           'qualified_root': str(directory / 'source-qualified')}}
    p['container_user'] = str(os.getuid()) + ':' + str(os.getgid())
    image = read(qualified_root / 'artifacts/native-runtime-qualification-20261022-v1/base-image-inspect.json')[0]
    need(image['Id'] == p['image_id'], 'QUALIFIED_IMAGE_RECEIPT')
    p['image_environment'] = image['Config']['Env']
    directory.mkdir()
    (ROOT / '.local/r2-runs').mkdir(parents=True, exist_ok=True)
    for name, digest in sources.items():
        dest = staged_path(name, p)
        dest.parent.mkdir(parents=True, exist_ok=True)
        need(sha(Path(name).read_bytes()) == digest, 'SOURCE_CHANGED_DURING_PREPARATION')
        with dest.open('xb') as f:
            f.write(Path(name).read_bytes()); f.flush(); os.fsync(f.fileno())
    save(directory / 'package.json', p)
    return sha((directory / 'package.json').read_bytes())


def review(path, expected, package_path, package):
    need(sha(Path(path).read_bytes()) == expected, 'REVIEW_RECEIPT_HASH')
    receipt = read(path)
    need(receipt['status'] == 'ACCEPT_EXACT_R2_PACKAGE' and receipt['material_defects'] == [], 'REVIEW_ACCEPTANCE')
    need(receipt['package_sha256'] == sha(Path(package_path).read_bytes()), 'REVIEW_PACKAGE_BINDING')
    need(receipt['sources'] == package['sources'] and receipt['runtime_files_sha256'] ==
         sha(canonical(package['runtime_files'])), 'REVIEW_COMPLETE_MAP')
    need(bool(receipt['reviewer']) and receipt['execution_authorized'] is False, 'INDEPENDENT_REVIEW_ONLY')
    return receipt


def owner_grant(package_path, review_path, review_hash):
    p = read(package_path)
    review(review_path, review_hash, package_path, p)
    return {'schema': 'MEMLIFE_R2_OWNER_GRANT_V1', 'approved': False,
            'package_sha256': sha(Path(package_path).read_bytes()),
            'review_sha256': review_hash, 'execution_id': p['execution_id'],
            'contract': p['contract'], 'host': p['host'], 'owner_provenance': None,
            'authorized_at': None, 'start_at': None, 'stop_at': None,
            'external_approval_reference': None}


def authorize(grant, p, package_hash, review_hash, now):
    need(grant['schema'] == 'MEMLIFE_R2_OWNER_GRANT_V1' and grant['approved'] is True, 'OWNER_UNAPPROVED')
    need(grant['package_sha256'] == package_hash and grant['review_sha256'] == review_hash,
         'GRANT_PACKAGE_REVIEW')
    need(grant['execution_id'] == p['execution_id'] and grant['contract'] == p['contract']
         and grant['host'] == p['host'], 'GRANT_EXACT_SCOPE')
    need(all(isinstance(grant[k], str) and grant[k].strip() for k in (
        'owner_provenance', 'authorized_at', 'start_at', 'stop_at', 'external_approval_reference')),
        'HUMAN_AND_EXTERNAL_PROVENANCE_REQUIRED')
    start, stop = [datetime.fromisoformat(grant[k]) for k in ('start_at', 'stop_at')]
    need(start.tzinfo is not None and stop.tzinfo is not None and start <= now < stop,
         'OWNER_TIME_WINDOW')
    need((stop - now).total_seconds() >= contract()['limits']['cleanup_seconds'], 'CLEANUP_WINDOW')
    return stop


class Docker:
    """Fixed local CLI, bounded calls; no shell or arbitrary command transport."""
    def call(self, *args):
        remaining = getattr(self, 'deadline', float('inf')) - time.monotonic()
        need(remaining > 0, 'DOCKER_DEADLINE')
        result = subprocess.run([DOCKER, '--host', ENDPOINT, *args], check=True,
                                capture_output=True, timeout=min(remaining, contract()['limits']['docker_command_seconds']))
        return result.stdout.decode().strip()

    def console(self, identity, path, root):
        """Drain exact stopped-container CLI console bytes with bounded custody."""
        available = contract()['limits']['working_bytes'] - working_bytes(root)
        deadline = min(self.deadline, time.monotonic() + contract()['limits']['docker_command_seconds'])
        need(available >= 0 and time.monotonic() < deadline, 'CONSOLE_BUDGET')
        with path.open('xb') as output:
            child = subprocess.Popen([DOCKER, '--host', ENDPOINT, 'logs', '--timestamps', identity],
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(child.stdout, selectors.EVENT_READ)
                    while True:
                        remaining = deadline - time.monotonic()
                        need(remaining > 0, 'CONSOLE_DEADLINE')
                        if not selector.select(min(.2, remaining)):
                            continue
                        raw = os.read(child.stdout.fileno(), 65536)
                        if not raw:
                            break
                        kept = raw[:available]
                        output.write(kept)
                        available -= len(kept)
                        need(len(kept) == len(raw), 'CONSOLE_WORKING_BUDGET')
                need(child.wait(timeout=max(.001, deadline-time.monotonic())) == 0, 'CONSOLE_RETRIEVAL_FAILED')
            finally:
                if child.poll() is None:
                    child.kill()  # Only this owned CLI reader, never an unrelated process.
                    child.wait(timeout=1)
                child.stdout.close()
                output.flush()
                os.fsync(output.fileno())

def json_value(raw):
    import json
    return json.loads(raw)


def inspect_container(driver, identity):
    return json_value(driver.call('inspect', identity))[0]


def admission(driver, p):
    info = json_value(driver.call('info', '--format', '{{json .}}'))
    running = driver.call('ps', '-q')
    value = resources(info, running, shutil.disk_usage(Path(p['host']['output']).parent).free)
    image = json_value(driver.call('image', 'inspect', p['image_id']))[0]
    need(image['Id'] == p['image_id'] and image['Os'] == 'linux' and image['Architecture'] == 'amd64',
         'QUALIFIED_IMAGE')
    need(image['Config']['Env'] == p['image_environment'], 'IMAGE_ENVIRONMENT')
    return value


def mounts(p, phase, package_dir):
    host = p['host']
    result = [
        (p['source_mounts']['current_root'], '/r2', True), (p['source_mounts']['qualified_root'], '/qualified', True),
        (host['runtime_root'] + '/runtime', '/runtime/runtime', True),
        (host['runtime_root'] + '/model-cache', '/runtime/model-cache', True),
        (host['runtime_root'] + '/requirements.lock', '/runtime/requirements.lock', True),
        (str(Path(package_dir) / 'package.json'), '/package/package.json', True),
        (host['output'], '/run', False), (host['output'] + '/supervisor', '/run/supervisor', True)]
    for earlier in p['contract']['phases'][:p['contract']['phases'].index(phase)]:
        result.append((host['output'] + '/evidence/' + earlier, '/run/evidence/' + earlier, True))
    if phase.startswith('DELETE'):
        result.append((host['output'] + '/stores/UPDATE', '/run/stores/UPDATE', True))
    return result


def create_command(p, phase, package_dir):
    host, c = p['host'], p['contract']['container']
    args = ['create', '--name', (p['execution_id'] + '-' + phase).lower(),
            '--label', 'memlife.r2=' + p['execution_id'], '--label', 'memlife.phase=' + phase,
            '--network', 'none', '--read-only', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges', '--cpus', str(c['cpus']),
            '--memory', str(c['memory_bytes']), '--memory-swap', str(c['memory_swap_bytes']),
            '--pids-limit', str(c['pids']), '--user', p['container_user'],
            '--tmpfs', '/tmp:rw,nosuid,nodev,size=' + str(c['tmpfs_bytes'])]
    for source, destination, readonly in mounts(p, phase, package_dir):
        args += ['--mount', 'type=bind,src=' + source + ',dst=' + destination + (',readonly' if readonly else '')]
    args += ['-e', 'HOME=/tmp/home', '-e', 'PYTHONDONTWRITEBYTECODE=1',
             '-e', 'MEMLIFE_R2_PACKAGE=' + p['_hash'],
             p['image_id'], '/runtime/runtime/.venv/bin/python', '-I', '-B', '-X', 'pycache_prefix=/tmp/r2-pycache',
             '/r2/scripts/research/r2_execution.py', 'worker', '--package', '/package/package.json',
             '--package-sha256', p['_hash'], '--phase', phase]
    return args


def container_check(c, p, phase):
    need(re.fullmatch('[a-f0-9]{64}', c['Id']), 'FULL_CONTAINER_ID')
    need(c['Image'] == p['image_id'], 'CONTAINER_IMAGE')
    need(c['Config']['Labels']['memlife.r2'] == p['execution_id'] and
         c['Config']['Labels']['memlife.phase'] == phase, 'CONTAINER_OWNER')
    h = c['HostConfig']; expected = p['contract']['container']
    need(h['NetworkMode'] == 'none' and h['ReadonlyRootfs'] and h['CapDrop'] == ['ALL']
         and h['SecurityOpt'] == ['no-new-privileges'] and not h.get('Privileged')
         and not h.get('Devices') and not h.get('CapAdd') and not h.get('PidMode')
         and not h.get('Binds') and not h.get('VolumesFrom'), 'CONTAINER_CONTAINMENT')
    need(h['Memory'] == expected['memory_bytes'] and h['MemorySwap'] == expected['memory_swap_bytes']
         and h['NanoCpus'] == expected['cpus'] * 10**9 and h['PidsLimit'] == expected['pids'], 'CONTAINER_RESOURCES')
    need(h['Tmpfs'] == {'/tmp': 'rw,nosuid,nodev,size=' + str(expected['tmpfs_bytes'])}, 'TMPFS_BOUND')
    observed_mounts = {m['Destination']: (m['Source'], m['RW']) for m in c['Mounts']}
    expected_mounts = {dest: (src, not ro) for src, dest, ro in mounts(p, phase, p['_package_dir'])}
    need(len(c['Mounts']) == len(expected_mounts) and observed_mounts == expected_mounts, 'EXACT_MOUNTS')
    need(c['Config']['Env'] is not None and 'MEMLIFE_R2_PACKAGE=' + p['_hash'] in c['Config']['Env'], 'CONTAINER_PACKAGE')
    command = create_command(p, phase, Path(p['_package_dir']))
    expected_cmd = command[command.index(p['image_id']) + 1:]
    need(c['Config']['Cmd'] == expected_cmd and c['Config']['Entrypoint'] in (None, []), 'CONTAINER_COMMAND')
    need(c['Config']['User'] == p['container_user'], 'CONTAINER_USER')
    need(c['Config']['Env'] == p['image_environment'] + ['HOME=/tmp/home', 'PYTHONDONTWRITEBYTECODE=1',
         'MEMLIFE_R2_PACKAGE=' + p['_hash']], 'EXACT_CONTAINER_ENVIRONMENT')
    return c['Id']


def working_bytes(root):
    return sum(p.stat().st_size for p in Path(root).rglob('*') if p.is_file())


def preserve_console(driver, identity, host, phase, root):
    path, receipt = host / (phase + '-console.log'), host / (phase + '-console.json')
    if receipt.exists():
        value = read(receipt)
        need(value['container_id'] == identity and value['complete'] is True and
             sha(path.read_bytes()) == value['sha256'], 'CONSOLE_RECEIPT_DRIFT')
        return
    need(not path.exists(), 'PARTIAL_CONSOLE_RETAIN_STOPPED_CONTAINER')
    driver.console(identity, path, root)
    save(receipt, {'container_id': identity, 'complete': True, 'sha256': sha(path.read_bytes()),
                   'basis': 'DOCKER_CLI_TIMESTAMPED_STDOUT_STDERR_MERGED_BYTES'})


def bindings(p):
    return {'source': sha(canonical(p['sources'])), 'runtime': sha(canonical(p['runtime_files'])),
            'protocol': r2.DESIGN_SHA256}


def cleanup_store(root, output, deadline, package):
    """Closed-process partial-state preservation precedes any owned deletion."""
    stores = root / 'stores'
    need(root == Path(package['host']['output']) and root.resolve() == root, 'CLEANUP_TASK_ROOT')
    owner = read(root / 'owner.json')
    need(owner['execution_id'] == package['execution_id'] and owner['package_sha256'] == package['_hash'], 'CLEANUP_TASK_OWNER')
    if not stores.exists():
        return
    need(stores.resolve() == stores and not stores.is_symlink(), 'CLEANUP_STORE_ROOT')
    need({x.name for x in stores.iterdir()} <= {'UPDATE', 'DELETE'}, 'CLEANUP_FOREIGN_STORE')
    for condition in stores.iterdir():
        r2.tree(condition)  # Reject special files/links, including claims.
        need({x.name for x in condition.iterdir()} <= {'qdrant','history','scratch','initial-claim.json','reopen-claim.json'}, 'CLEANUP_UNOWNED_MEMBER')
        claim = read(condition / 'initial-claim.json')
        initial = read(output / (condition.name + '-initial-created.json'))
        need(claim == {'output': '/run/evidence/' + condition.name + '-initial',
                       'process': initial['Id'], 'bindings': bindings(package)}, 'CLEANUP_INITIAL_OWNER')
    need(time.monotonic() < deadline, 'CLEANUP_DEADLINE')
    snapshot = output / 'closed-stores'
    def copy(source, destination):
        with open(source, 'rb') as src, open(destination, 'xb') as dst:
            while True:
                need(time.monotonic() < deadline, 'CLEANUP_DEADLINE')
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                dst.write(chunk)
            dst.flush()
            os.fsync(dst.fileno())
        return destination
    shutil.copytree(stores, snapshot, copy_function=copy)
    need(r2.tree(stores) == r2.tree(snapshot), 'CLEANUP_SNAPSHOT_INTEGRITY')
    for f in snapshot.rglob('*'):
        if f.is_file():
            with f.open('rb') as stream:
                os.fsync(stream.fileno())
    save(output / 'closed-store-seal.json', {'files': r2.tree(snapshot)})
    # Complete archive seal (including incomplete worker evidence) before delete.
    for directory in reversed([snapshot] + [p for p in snapshot.rglob('*') if p.is_dir()]):
        fd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    save(output / 'pre-cleanup-seal.json', {'files': r2.tree(root)})
    need(time.monotonic() < deadline, 'CLEANUP_DEADLINE')
    shutil.rmtree(stores)


def execute(package_path, package_hash, review_path, review_hash, grant_path, *, driver=None):
    """Future live entrypoint. Never called during offline qualification."""
    p = verify_package(package_path, package_hash)
    review(review_path, review_hash, package_path, p)
    stop = authorize(read(grant_path), p, package_hash, review_hash, datetime.now(timezone.utc))
    p = dict(p, _hash=package_hash, _package_dir=str(Path(package_path).parent.resolve()))
    driver = driver or Docker()
    root = Path(p['host']['output'])
    need(root.resolve() == root and not root.exists(), 'FRESH_EXECUTION_ONLY')
    capacity = admission(driver, p)
    root.mkdir()  # Exclusive campaign claim; never reuse after failure.
    save(root / 'owner.json', {'execution_id': p['execution_id'], 'package_sha256': package_hash,
                              'grant_sha256': sha(Path(grant_path).read_bytes()), 'review_sha256': review_hash})
    evidence = root / 'evidence'; evidence.mkdir()
    stores = root / 'stores'; stores.mkdir()
    host = root / 'supervisor'; host.mkdir()
    save(host / 'capacity.json', capacity)
    started = time.monotonic()
    hard_stop = min(started + contract()['limits']['execution_seconds'],
                    started + (stop - datetime.now(timezone.utc)).total_seconds() - contract()['limits']['cleanup_seconds'])
    driver.deadline = hard_stop
    identities, active, phase, status = [], None, None, 'INCOMPLETE'
    try:
        for phase in p['contract']['phases']:
            need(time.monotonic() < hard_stop, 'EXECUTION_DEADLINE')
            verify_package(package_path, package_hash)
            for earlier in p['contract']['phases'][:p['contract']['phases'].index(phase)]:
                binding = read(host / (earlier + '-completed.json'))
                r2.verify_seal(evidence / earlier, binding['seal_sha256'])
            admission(driver, p)
            need(working_bytes(root) <= contract()['limits']['working_bytes'], 'WORKING_DISK_CEILING')
            need(time.monotonic() < hard_stop and datetime.now(timezone.utc) < stop, 'PRE_CREATE_DEADLINE')
            command = create_command(p, phase, Path(package_path).parent.resolve())
            save(host / (phase + '-launch.json'), command)  # intent before Docker create
            active = (p['execution_id'] + '-' + phase).lower()  # recover only this name on uncertain create
            identity = driver.call(*command)
            need(re.fullmatch('[a-f0-9]{64}', identity), 'CREATED_ID')
            active = identity
            c = inspect_container(driver, identity)
            container_check(c, p, phase)
            need(identity not in identities and c['State']['Status'] == 'created', 'FRESH_PROCESS_IDENTITY')
            identities.append(identity)
            save(host / (phase + '-created.json'), c)
            need(time.monotonic() < hard_stop and datetime.now(timezone.utc) < stop, 'PRE_START_DEADLINE')
            phase_stop = min(hard_stop, time.monotonic() + contract()['limits']['phase_seconds'])
            driver.deadline = phase_stop
            driver.call('start', identity)
            while True:
                c = inspect_container(driver, identity)
                need(time.monotonic() < phase_stop, 'PHASE_DEADLINE')
                if not c['State']['Running']:
                    break
                need(working_bytes(root) <= contract()['limits']['working_bytes'], 'WORKING_DISK_CEILING')
                time.sleep(.25)
            save(host / (phase + '-exited.json'), c)
            driver.deadline = hard_stop
            preserve_console(driver, identity, host, phase, root)
            driver.call('rm', identity)
            save(host / (phase + '-removed.json'), {'id': identity, 'removed': True})
            active = None
            need(c['State']['Status'] == 'exited' and c['State']['ExitCode'] == 0
                 and not c['State']['OOMKilled'], 'PHASE_PROCESS_FAILURE')
            folder = evidence / phase
            result = r2.verify_seal(folder, sha((folder / 'seal.json').read_bytes()))
            need(result['process'] == identity and result['status'] == 'COMPLETED' and result['closed']
                 and result['bindings'] == bindings(p), 'PHASE_INCOMPLETE')
            save(host / (phase + '-completed.json'), {'container_id': identity,
                'seal_sha256': sha((folder / 'seal.json').read_bytes()), 'package_sha256': package_hash,
                'bindings': result['bindings'], 'phase': phase,
                'sdk_counts': verify_budget(folder, prior_counts(host, p, phase), p['contract']['phases'].index(phase))})
        status = 'COMPLETED'
    except Exception as exc:
        save(host / 'failure.json', {'phase': phase, 'class': type(exc).__name__, 'message': str(exc),
                                   'unperformed_observations': 'UNKNOWN', 'retry': False})
    finally:
        # At most 20s inspect + 20s kill + 20s rm; owned bytes retained on uncertainty.
        cleanup_deadline = min(time.monotonic() + contract()['limits']['cleanup_seconds'],
                               time.monotonic() + (stop - datetime.now(timezone.utc)).total_seconds())
        driver.deadline = cleanup_deadline
        try:
            if active is not None:
                c = inspect_container(driver, active)
                need((c['Id'] == active or c['Name'] == '/' + active) and
                     c['Config']['Labels'].get('memlife.r2') == p['execution_id'] and
                     c['Config']['Labels'].get('memlife.phase') == phase,
                     'CLEANUP_EXACT_OWNER')
                active = c['Id']
                if c['State']['Running']:
                    driver.call('kill', active)
                c = inspect_container(driver, active)
                need(not c['State']['Running'], 'CLEANUP_PROCESS_STILL_RUNNING')
                save(host / (phase + '-cleanup-exited.json'), c)
                preserve_console(driver, active, host, phase, root)
                driver.call('rm', active)
                save(host / (phase + '-cleanup-removed.json'), {'id': active, 'removed': True})
            need(not driver.call('ps', '-aq', '--filter', 'label=memlife.r2=' + p['execution_id']), 'CLEANUP_OWNED_CONTAINER_REMAINS')
            cleanup_store(root, host, cleanup_deadline, p)
        except Exception as exc:
            status = 'INCOMPLETE'
            save(host / 'cleanup-error.json', {'class': type(exc).__name__, 'message': str(exc),
                                              'stores_retained_on_uncertainty': True})
        save(host / 'result.json', {'status': status, 'container_ids': identities,
                                   'stores_removed': not stores.exists(), 'model_exposure': 'NOT_SENT'})
        save(root / 'seal.json', {'files': r2.tree(root)})
    return status


class Budget:
    """Reserve qualified boundary calls durably, including failed calls."""
    def __init__(self, folder, previous, phase_index):
        self.folder, self.counts, self.ordinal, self.halted = folder, dict(previous), 0, False
        self.limit = contract()['phase_sdk_totals'][phase_index]

    def reserve(self, method):
        try:
            need(not self.halted, 'SDK_BUDGET_HALTED')
            limits = contract()['sdk_calls']
            need(method in limits and self.ordinal < self.limit and self.counts[method] < limits[method], 'SDK_CEILING')
            counts = dict(self.counts)
            counts[method] += 1
            save(self.folder / ('sdk-intent-%03d.json' % (self.ordinal + 1)), {'method': method, 'counts': counts})
            self.counts = counts
            self.ordinal += 1
        except Exception:
            self.halted = True
            raise


def prior_counts(host, package, phase):
    ordinal = package['contract']['phases'].index(phase)
    if ordinal == 0:
        return {k: 0 for k in package['contract']['sdk_calls']}
    previous = package['contract']['phases'][ordinal-1]
    return read(host / (previous + '-completed.json'))['sdk_counts']


def verify_budget(folder, previous, ordinal):
    counts, methods = dict(previous), []
    need(set(counts) == set(contract()['sdk_calls']), 'BUDGET_KEYS')
    for n, path in enumerate(sorted(folder.glob('sdk-intent-*.json')), 1):
        need(path.name == 'sdk-intent-%03d.json' % n, 'BUDGET_INTENT_SEQUENCE')
        row = read(path); method = row['method']
        need(method in counts, 'BUDGET_METHOD')
        counts[method] += 1
        need(row['counts'] == counts and counts[method] <= contract()['sdk_calls'][method], 'BUDGET_CUMULATIVE')
        methods.append(method)
    need(len(methods) <= contract()['phase_sdk_totals'][ordinal], 'BUDGET_PHASE_TOTAL')
    captured = [read(path)['method'] for path in sorted((folder / 'capture/native-sdk').glob('*-input.json'))]
    need(methods == captured and bool(methods), 'SDK_CAPTURE_BUDGET_BINDING')
    return counts


def worker_audit(event, args):
    if event in ('socket.connect', 'socket.getaddrinfo', 'socket.sendto', 'socket.bind',
                 'subprocess.Popen', 'os.system', 'os.posix_spawn', 'os.exec', 'os.fork'):
        raise PermissionError('R2_NETWORK_OR_PROCESS_FORBIDDEN')


def guard_llm(cls):
    def denied(*args, **kwargs):
        raise PermissionError('R2_INTERNAL_LLM_FORBIDDEN')
    cls.generate_response = denied


def worker(package_path, package_hash, phase):
    """Runs only inside an admitted, inspected future container."""
    p = verify_package(package_path, package_hash, worker=True)
    p = dict(p, _hash=package_hash, _package_dir=str(Path(package_path).parent))
    p['_worker'] = True
    # Host source of /package is frozen into package at preparation.
    p['_package_dir'] = p['package_host_dir']
    c = read(Path('/run/supervisor') / (phase + '-created.json'))
    identity = container_check(c, p, phase)
    need(c['Config']['Hostname'] == socket.gethostname() and identity.startswith(socket.gethostname()), 'ACTUAL_CONTAINER_HOSTNAME')
    ordinal = p['contract']['phases'].index(phase)
    previous = {k: 0 for k in p['contract']['sdk_calls']}
    seals = {}
    for earlier in p['contract']['phases'][:ordinal]:
        old = read(Path('/run/supervisor') / (earlier + '-exited.json'))
        removed = read(Path('/run/supervisor') / (earlier + '-removed.json'))
        need(old['Id'] == removed['id'] and removed['removed'] and not old['State']['Running']
             and old['State']['ExitCode'] == 0 and old['Id'] != identity, 'CLOSED_PREDECESSOR')
        folder = Path('/run/evidence') / earlier
        completed = read(Path('/run/supervisor') / (earlier + '-completed.json'))
        need(completed['container_id'] == old['Id'] and completed['package_sha256'] == package_hash
             and completed['phase'] == earlier, 'EXACT_PHASE_COMPLETION')
        seals[earlier] = completed['seal_sha256']
        prior = r2.verify_seal(folder, seals[earlier])
        need(prior['bindings'] == completed['bindings'], 'PREDECESSOR_BINDINGS')
        previous = verify_budget(folder, previous, p['contract']['phases'].index(earlier))
        need(previous == completed['sdk_counts'], 'PREDECESSOR_SDK_COUNTS')
    os.environ.update({'MEM0_TELEMETRY': 'false', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
        'HF_HUB_DISABLE_TELEMETRY': '1', 'TOKENIZERS_PARALLELISM': 'false', 'OMP_NUM_THREADS': '2', 'MKL_NUM_THREADS': '2'})
    sys.addaudithook(worker_audit)  # Before provider import or construction.
    from importlib.metadata import version
    for name, expected in r2.design()['runtime']['versions'].items():
        need(version(name) == expected, 'RUNTIME_VERSION:' + name)
    import memlife
    memlife.__path__.append('/qualified/src/memlife')
    from mem0.llms.openai import OpenAILLM
    guard_llm(OpenAILLM)  # Class gate precedes Memory.from_config.
    from memlife.adapters.mem0 import Mem0MemoryAdapter, Mem0LocalPaths
    from memlife.research_collection import ResearchCapture
    from memlife.runner.phase08d3 import AttemptArtifactStore
    from memlife.native_provider_capture import CapturedMem0SDK
    folder = Path('/run/evidence') / phase
    budget = Budget(folder, previous, ordinal)
    original = CapturedMem0SDK.__getattr__
    def bounded(instance, method):
        value = original(instance, method)
        if method not in CapturedMem0SDK.METHODS:
            return value
        def call(*args, **kwargs):
            budget.reserve(method)
            try:
                return value(*args, **kwargs)
            except Exception:
                budget.halted = True
                raise
        return call
    CapturedMem0SDK.__getattr__ = bounded
    def factory(paths, output):
        for path in paths.values():
            Path(path).mkdir(exist_ok=True)
        principal = r2.design()['principal']
        record = ResearchCapture(AttemptArtifactStore(output), attempt_id=p['execution_id'] + '/' + phase,
            case_id='R2-' + phase, family='TEST_ONLY', provider='mem0', provider_version='2.2.1',
            stratum='NATIVE_PROVIDER_CAPTURE', configuration={'infer': False, 'package_sha256': package_hash},
            host_acl={'authored_by': 'HOST_TEST_FIXTURE', 'principal': principal, 'project': principal['project']},
            provenance={'source_manifest_sha256': sha(canonical(p['sources'])), 'experiment_manifest_sha256': r2.DESIGN_SHA256,
                        'collector_sha256': sha(Path('/qualified/src/memlife/research_collection.py').read_bytes())})
        record._event('r2-construction-intent', {'paths': paths, 'network': 'none', 'internal_llm': 'DENIED'})
        local = Mem0LocalPaths(data_root=Path('/run/stores'), provider_root=Path(paths['qdrant']).parent,
            qdrant=Path(paths['qdrant']), history=Path(paths['history']), scratch=Path(paths['scratch']), model_cache=Path('/runtime/model-cache'))
        adapter = Mem0MemoryAdapter(local)
        return r2.QualifiedSession(adapter, record, 'npq-' + sha(canonical(principal)))
    condition, mode = phase.split('-')
    args = dict(parent=Path('/run/stores'), output=folder, condition=condition, reopen=mode == 'reopen',
        process=identity, bindings=bindings(p), factory=factory)
    if ordinal:
        args['predecessor_seal'] = seals[p['contract']['phases'][ordinal - 1]]
    if mode == 'reopen':
        args.update(prior_folder=Path('/run/evidence') / (condition + '-initial'), prior_seal=seals[condition + '-initial'])
    result, _ = r2.phase(**args)
    need(result['status'] == 'COMPLETED' and result['closed'], 'WORKER_INCOMPLETE')
