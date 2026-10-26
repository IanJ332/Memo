"""LC12 entrypoint. ledger/resource-check are offline; collect requires live authority."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('lc12', ROOT / 'src/memlife/crossarch.py')
lc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lc)


def worker(args):
    """Native client process; service lifecycle is owned by a separate process."""
    sys.path.insert(0, str(Path(args.qualified_root) / 'src'))
    from importlib.metadata import version
    from memlife.runner.phase08d3 import AttemptArtifactStore, HttpExchangeCapture
    from memlife.research_collection import ResearchCapture
    from memlife.adapters.hindsight import UrllibHindsightTransport
    from memlife.batch.openviking_capture import CapturedDirectMemory

    unit = json.loads(Path('/evidence/unit.json').read_bytes())
    provider = unit['provider']
    if version('openviking' if provider == 'openviking' else 'hindsight-api-slim') != (
            '0.4.22' if provider == 'openviking' else '0.10.1'):
        raise ValueError('PROVIDER_VERSION')
    # OS containment is configured by collect before importing native clients.
    # This additional client guard permits only the two pinned loopback APIs.
    connect = socket.socket.connect
    def local_only(sock, address):
        if not isinstance(address, tuple) or address[0] != '127.0.0.1' or address[1] not in (1933, 8888):
            raise RuntimeError('CLIENT_NETWORK_OUTSIDE_LOCAL_PROVIDER')
        return connect(sock, address)
    socket.socket.connect = local_only
    scope = {'issuer': 'lc12-host-fixture', 'subject': unit['unit_id'], 'project': unit['entity']}
    acl = {**unit['host_authority'], 'principal': scope, 'project': scope['project']}
    capture = ResearchCapture(AttemptArtifactStore(Path('/evidence') / (args.phase + '-capture')),
        attempt_id=args.run_id + '/' + unit['unit_id'] + '/' + args.phase,
        case_id=unit['unit_id'], family='TEST_ONLY', provider=provider,
        provider_version='0.4.22' if provider == 'openviking' else '0.10.1',
        stratum='NATIVE_PROVIDER_CAPTURE', configuration={'mode': 'NATIVE_ONLY_NO_LLM'}, host_acl=acl,
        provenance={'source_manifest_sha256': lc.sha(Path('/campaign/source-identities.json').read_bytes()),
                    'experiment_manifest_sha256': lc.sha(lc.canonical(lc.plan())),
                    'collector_sha256': lc.sha((Path(args.qualified_root) / 'src/memlife/research_collection.py').read_bytes())})
    budget = lc.Budget('/campaign/http-intents.jsonl', float(os.environ['LC12_UNIT_DEADLINE']))
    api = lc.NativeAPI(unit, args.run_id, capture, budget)
    if provider == 'openviking':
        api.client = CapturedDirectMemory(capture, 'synthetic-' + args.run_id, api.scope)
    else:
        class DurableExchange(HttpExchangeCapture):
            def capture(self, **kwargs):
                manifest = super().capture(**kwargs)
                for key in ('request', 'response', 'manifest'):
                    with (self.store.root / manifest[key]['path']).open('rb') as stream:
                        os.fsync(stream.fileno())
                return manifest
        api.transport = UrllibHindsightTransport(base_url='http://127.0.0.1:8888',
            timeout_seconds=20, capture=DurableExchange(capture.store, attempt_id=capture.attempt_id))
    prior = json.loads(Path('/evidence/initial/result.json').read_bytes()) if args.phase == 'reopen' else None
    try:
        result = lc.run_phase(api, unit, Path('/evidence') / args.phase, prior=prior)
    finally:
        capture.finalize()
    if result['status'] != 'COMPLETED':
        raise RuntimeError('PARTIAL_NATIVE_RESULT_RETAINED')


def service(args):
    """Only task-owned subprocesses; every phase exits before host snapshots."""
    unit = json.loads(Path('/evidence/unit.json').read_bytes())
    provider, children, logs, polls = unit['provider'], [], [], []
    deadline = float(os.environ['LC12_UNIT_DEADLINE'])
    def start(command, name):
        log = (Path('/evidence') / (args.phase + '-' + name + '.log')).open('xb')
        logs.append(log)
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        children.append(process)
        return process
    def ready(url, child):
        from urllib.request import urlopen
        for _ in range(20):
            if child.poll() is not None or time.time() >= deadline:
                raise RuntimeError('SERVICE_EXIT_OR_DEADLINE')
            lc.Budget('/campaign/http-intents.jsonl', deadline).before()
            try:
                with urlopen(url, timeout=min(2, max(.1, deadline-time.time()))) as response:
                    body = response.read(65537)
                    polls.append({'url': url, 'status': response.status, 'body_hex': body.hex()})
                    if len(body) > 65536:
                        raise ValueError('HEALTH_ENTITY_BOUND')
                    value = json.loads(body)
                    if response.status == 200 and (not url.endswith('/ready') or value.get('status') == 'ready'):
                        return
            except (OSError, ValueError) as exc:
                polls.append({'url': url, 'error': type(exc).__name__})
            time.sleep(min(2, max(0, deadline-time.time())))
        raise TimeoutError('HEALTH_POLL_BOUND')
    try:
        if provider == 'openviking':
            embed = start(['/task/runtime/.venv/bin/python', '-I', '-B',
                           '/qualified/scripts/research/batch_embedding_service.py'], 'embedding')
            ready('http://127.0.0.1:1934/health', embed)
            command = [sys.executable, '-I', '-B', '-m', 'openviking.server.bootstrap', '--config', '/state/ov.conf']
            health = 'http://127.0.0.1:1933/ready'
        else:
            command = [sys.executable, '-I', '-B', '-m', 'uvicorn', 'hindsight_api.server:app',
                       '--host', '127.0.0.1', '--port', '8888', '--workers', '1', '--no-access-log']
            health = 'http://127.0.0.1:8888/health'
        server = start(command, 'service')
        ready(health, server)
        child = start([sys.executable, '-I', '-B', str(Path(__file__).resolve()), '_worker',
                       '--phase', args.phase, '--run-id', args.run_id, '--qualified-root', '/qualified'], 'worker')
        if child.wait(timeout=max(.1, deadline-time.time())):
            raise RuntimeError('WORKER_FAILED')
    finally:
        for child in reversed(children):
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=5)
        lc.write(Path('/evidence') / (args.phase + '-processes.json'), {
            'container_id': os.environ.get('HOSTNAME'), 'pids': [p.pid for p in children],
            'exits': [p.returncode for p in children], 'all_exited': all(p.poll() is not None for p in children),
            'health': polls})
        for log in logs:
            log.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('ledger')
    resources = sub.add_parser('resource-check')
    resources.add_argument('--cpus', type=int, required=True)
    resources.add_argument('--ram-bytes', type=int, required=True)
    resources.add_argument('--free-bytes', type=int, required=True)
    collect = sub.add_parser('collect')
    collect.add_argument('--config', type=Path, required=True)
    for name in ('_worker', '_service'):
        phase = sub.add_parser(name)
        phase.add_argument('--qualified-root', default='/qualified')
        phase.add_argument('--run-id', required=True)
        phase.add_argument('--phase', choices=('initial', 'reopen'), required=True)
    args = parser.parse_args()
    if args.command == 'ledger':
        print(json.dumps(lc.plan(), indent=2))
    elif args.command == 'resource-check':
        print(json.dumps(lc.resource_decision(args.cpus, args.ram_bytes, args.free_bytes)))
    elif args.command == 'collect':
        host_spec = importlib.util.spec_from_file_location('lc12_host', ROOT / 'scripts/research/crossarch_host.py')
        host = importlib.util.module_from_spec(host_spec)
        host_spec.loader.exec_module(host)
        host.collect(json.loads(args.config.read_bytes()), lc, ROOT)
    elif args.command == '_worker':
        worker(args)
    else:
        service(args)


if __name__ == '__main__':
    main()
