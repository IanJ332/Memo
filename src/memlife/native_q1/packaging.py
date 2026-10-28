"""One exclusive prospective package; owner provenance is checked, never invented.

Actual platform approval applies to the exact tool invocation and all dependent
effects outside this process. This module does not issue a platform receipt or
authenticate a human from a file. Grant provenance must come from a genuine
direct owner message retained by the trusted launcher/operator.
"""
import base64
import csv
import importlib.metadata
from datetime import datetime, timezone
from pathlib import Path
import os
import subprocess
import time
import uuid
import sys

from .core import ROOT, Files, State, design_package
from memlife.r1.protocol import canonical, strict, sha, need


def identity(path):
    path = Path(path)
    data = path.read_bytes()
    return dict(path=str(path.resolve()), sha256=sha(data), bytes=len(data))


def verify_identity(item):
    need(identity(item['path']) == item, 'PINNED_ARTIFACT_DRIFT')


def verify_runtime(runtime):
    need(runtime['status'] == 'PASS_READ_ONLY_RUNTIME_IDENTITY_AND_CAPACITY' and runtime['native_imports_or_constructions'] == 0
         and runtime['containers_started'] == 0, 'QUALIFIED_RUNTIME_RECEIPT')
    for item in [runtime['dependency_lock'], runtime['original_qualification_inventory'],
                 *runtime['qualified_provenance'].values(), *runtime['embedding']['files']]:
        verify_identity(item)
    site = Path(runtime['site_packages'])
    venv = Path(runtime['venv_root']).resolve()
    distributions = runtime['installed_record_check']['distributions']
    need({p.name for p in site.glob('*.dist-info')} == {r['distribution'] for r in distributions}, 'RUNTIME_DISTRIBUTION_DRIFT')
    count = 0
    for row in distributions:
        folder = site/row['distribution']
        need(sha((folder/'RECORD').read_bytes()) == row['record_sha256']
             and sha((folder/'METADATA').read_bytes()) == row['metadata_sha256'], 'RUNTIME_RECORD_DRIFT')
        for name, expected, size in csv.reader((folder/'RECORD').read_text().splitlines()):
            if not expected:
                continue
            path = (site/name).resolve()
            need(path.is_relative_to(venv), 'RUNTIME_FILE_ESCAPE')
            algorithm, encoded = expected.split('=', 1)
            data = path.read_bytes()
            need(algorithm == 'sha256' and len(data) == int(size)
                 and base64.urlsafe_b64encode(bytes.fromhex(sha(data))).decode().rstrip('=') == encoded, 'RUNTIME_FILE_DRIFT')
            count += 1
    need(count == runtime['installed_record_check']['hashed_files'], 'RUNTIME_HASH_COUNT')
    return dict(installed_hashes=count, distributions=len(distributions), embedding_files=len(runtime['embedding']['files']))


def host_runtime_identity():
    rows = []
    for name in ('pydantic', 'pydantic_core', 'annotated-types', 'typing_extensions', 'typing-inspection'):
        dist = importlib.metadata.distribution(name)
        record = next(p for p in dist.files if str(p).endswith('.dist-info/RECORD'))
        record_path = Path(dist.locate_file(record))
        for relative, expected, size in csv.reader(record_path.read_text().splitlines()):
            if expected:
                algorithm, digest = expected.split('=', 1)
                path = Path(dist.locate_file(relative))
                data = path.read_bytes()
                need(algorithm == 'sha256' and len(data) == int(size)
                     and base64.urlsafe_b64encode(bytes.fromhex(sha(data))).decode().rstrip('=') == digest,
                     'HOST_DEPENDENCY_RECORD_DRIFT')
                rows.append(identity(path))
        rows.append(identity(record_path))
    return dict(python_version=sys.version, distributions=5, files=rows,
                bytecode='-I -B -X pycache_prefix=/dev/null prevents reading unverified cache files')


def verify_host_runtime(runtime):
    need(runtime['python_version'] == sys.version, 'HOST_INTERPRETER_VERSION_DRIFT')
    for item in runtime['files']:
        verify_identity(item)


def source_names():
    return sorted({str(p.relative_to(ROOT)) for p in (ROOT/'src/memlife').rglob('*.py')} |
        {str(p.relative_to(ROOT)) for p in (ROOT/'scripts/research').glob('native_q1*.py')} |
        {str(p.relative_to(ROOT)) for p in (ROOT/'manifests/next-lp-native-q1').glob('*.json')})


def prepare(destination, runtime_receipt, reviews, host_python):
    destination = Path(destination).resolve()
    need(Path(host_python).absolute() == Path(sys.executable).absolute(), 'EXACT_REPOSITORY_HOST_INTERPRETER_REQUIRED')
    need(not destination.exists(), 'ONE_PROSPECTIVE_PACKAGE_ONLY')
    need(destination.parent.is_dir() and not destination.is_symlink(), 'PRIVATE_PACKAGE_PARENT_REQUIRED')
    need(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip() == b'', 'REVIEWED_CLEAN_SOURCE_REQUIRED')
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    runtime = strict(Path(runtime_receipt).read_bytes())
    runtime_check = verify_runtime(runtime)
    accepted = [strict(Path(path).read_bytes()) for path in reviews]
    need(len(accepted) == 2 and all(r['verdict'] == 'ACCEPT' for r in accepted)
         and {r['role'] for r in accepted} == {'SCIENTIFIC', 'ENGINEERING'}, 'TWO_GENUINE_INDEPENDENT_SOURCE_REVIEWS')
    for review in accepted:
        for name, expected in review['source_bindings'].items():
            need(sha((ROOT/name).read_bytes()) == expected, 'INDEPENDENT_REVIEW_SOURCE_DRIFT')
    execution = 'Q1EX-' + datetime.now(timezone.utc).strftime('%Y%m%d') + '-' + uuid.uuid4().hex[:8]
    package = design_package(execution, 'q1-'+uuid.uuid4().hex)
    source = destination/'SOURCE'
    parent = destination.parent
    locations = dict(package=str(destination), source=str(source),
                     store=str(parent/'stores'/execution), evidence=str(parent/'evidence'/execution))
    package.update(source_revision=revision, sources={name: sha((ROOT/name).read_bytes()) for name in source_names()},
        runtime=runtime, runtime_receipt=identity(runtime_receipt), runtime_verification=runtime_check,
        source_reviews=[identity(path) for path in reviews], locations=locations,
        container_name='memlife-q1-'+execution.lower(), host_python=identity(host_python),
        host_python_command=str(Path(host_python).absolute()),
        host_runtime=host_runtime_identity(),
        authorization='UNAPPROVED_REQUIRES_DIRECT_EXACT_OWNER_DECISION_AND_SUPPORTED_TOOL_APPROVAL',
        time_policy=dict(maximum_total_seconds=2700, scientific_seconds_max=2640, cleanup_reserve_seconds=60,
                         absolute_window='MUST_BE_FIXED_BY_FRESH_DIRECT_OWNER_GRANT_BEFORE_LAUNCH'),
        dependent_effects=['read-only runtime/source admission','one isolated container','three native processes',
            '18 registered top-level SDK attempts maximum','immutable Host evidence and snapshots',
            'owned container/store cleanup and absence verification'],
        owner_provenance_requirement='Genuine direct owner message exact package/scope/window; file equality is not human authentication',
        platform_approval='Actual supported exact launcher tool review; no standalone receipt supplied or accepted')
    State(package)
    destination.mkdir(mode=0o700)
    files = Files(destination)
    for name, expected in package['sources'].items():
        data = (ROOT/name).read_bytes()
        need(sha(data) == expected, 'SOURCE_CHANGED_DURING_PACKAGE')
        path = source/name
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
    digest = files.write('package.json', package)
    files.write('owner-grant-candidate.json', dict(schema='Q1_OWNER_GRANT_V1', approved=False,
        execution_id=execution, package_sha256=digest, starts_at_utc=None, expires_at_utc=None,
        owner_message=None, declaration='UNAPPROVED_NOT_OWNER_AUTHORIZATION_NOT_PLATFORM_APPROVAL'))
    files.write('launcher.json', dict(command=[str(Path(host_python).absolute()), '-I', '-B', '-X',
        'pycache_prefix=/dev/null', str(source/'scripts/research/native_q1.py'), 'run',
        '--package', str(destination/'package.json'), '--grant', str(parent/'owner-grant-approved.json')],
        package_sha256=digest, effects=package['dependent_effects'], currently_authorized=False))
    files.seal()
    return dict(execution_id=execution, package_sha256=digest, path=str(destination/'package.json'), owner_grant='UNAPPROVED')


def verify_package(path):
    path = Path(path).resolve()
    root = path.parent
    inventory = strict((root/'inventory.json').read_bytes())
    names = [r['path'] for r in inventory['files']]
    need(len(names) == len(set(names)) and not any(p.is_symlink() for p in root.rglob('*')), 'PACKAGE_MEMBERS')
    need({str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()} == set(names)|{'inventory.json'}, 'PACKAGE_MEMBERS')
    for row in inventory['files']:
        p = root/row['path']
        need(not Path(row['path']).is_absolute() and p.resolve().is_relative_to(root), 'PACKAGE_PATH')
        need(sha(p.read_bytes()) == row['sha256'] and p.stat().st_size == row['bytes'], 'PACKAGE_MEMBER_DRIFT')
    package = strict(path.read_bytes())
    need(package['locations']['package'] == str(root) and package['locations']['source'] == str(root/'SOURCE'), 'PACKAGE_LOCATION')
    for name, expected in package['sources'].items():
        need(sha((root/'SOURCE'/name).read_bytes()) == expected, 'FROZEN_SOURCE_DRIFT')
    need(Path(package['locations']['store']).parent == root.parent/'stores'
         and Path(package['locations']['evidence']).parent == root.parent/'evidence', 'OWNED_RESOURCE_LOCATIONS')
    State(package)
    return package


def validate_grant(package, package_digest, grant, *, now=None):
    now = now or datetime.now(timezone.utc)
    need(grant.get('schema') == 'Q1_OWNER_GRANT_V1' and grant.get('approved') is True
         and grant.get('execution_id') == package['execution_id']
         and grant.get('package_sha256') == package_digest, 'FRESH_EXACT_OWNER_GRANT_REQUIRED')
    message = grant.get('owner_message')
    need(type(message) is dict and message.get('origin') == 'DIRECT_OWNER_MESSAGE', 'GENUINE_OWNER_PROVENANCE_REQUIRED')
    verify_identity({k: message[k] for k in ('path', 'sha256', 'bytes')})
    text = Path(message['path']).read_text()
    need(package['execution_id'] in text and package_digest in text and '18' in text
         and grant['starts_at_utc'] in text and grant['expires_at_utc'] in text, 'OWNER_MESSAGE_EXACT_SCOPE_AND_WINDOW')
    start, end = (datetime.fromisoformat(grant[key].replace('Z', '+00:00')) for key in ('starts_at_utc', 'expires_at_utc'))
    need(start.tzinfo is not None and end.tzinfo is not None and start <= now < end
         and 0 < (end-start).total_seconds() <= 2700, 'FRESH_OWNER_WINDOW_REQUIRED')
    return (end-now).total_seconds()


def run(path, grant_path):
    package = verify_package(path)
    digest = sha(Path(path).read_bytes())
    grant = strict(Path(grant_path).read_bytes())
    remaining = validate_grant(package, digest, grant)
    need(Path(sys.executable).absolute() == Path(package['host_python_command']).absolute(), 'HOST_VENV_SELECTION_DRIFT')
    verify_identity(package['host_python'])
    verify_host_runtime(package['host_runtime'])
    verify_runtime(package['runtime'])
    # Authorization and environment checks above occur before claiming evidence,
    # constructing Mem0 or making any state-changing Docker invocation.
    remaining = validate_grant(package, digest, grant)
    need(remaining > 60, 'INSUFFICIENT_APPROVED_CLEANUP_WINDOW')
    package['authorization_evidence'] = dict(approved_package=identity(path), approved_package_body=strict(Path(path).read_bytes()),
        grant=grant, grant_identity=identity(grant_path), owner_message=Path(grant['owner_message']['path']).read_text(),
        scope='DIRECT_OWNER_PROVENANCE_CUSTODY_REQUIRED_NOT_AUTHENTICATED_BY_FILE_HASH')
    package['authorized_deadline_monotonic'] = time.monotonic()+remaining
    out = Path(package['locations']['evidence'])
    out.parent.mkdir(parents=True, exist_ok=True)
    Path(package['locations']['store']).parent.mkdir(parents=True, exist_ok=True)
    from .runtime import DockerTransport
    from .core import execute
    transport = DockerTransport(package, out)
    return execute(package, out, transport, simulated=False)
