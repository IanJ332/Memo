"""Exact local Docker transport: one container, three SDK processes, no Host mount."""
from pathlib import Path
import os
import selectors
import shutil
import subprocess
import threading
import time
import base64

from .core import Files, admission
from memlife.r1.protocol import canonical, strict, sha, need


class DockerTransport:
    native_boundary = True

    def __init__(self, package, out, *, docker_command=None):
        self.package, self.out = package, Path(out)
        self.locations, self.runtime = package['locations'], package['runtime']
        self.docker = docker_command or [self.runtime['docker']['executable'], '--host', self.runtime['docker']['host']]
        self.name = package['container_name']
        self.store = Path(self.locations['store'])
        self.process, self.buffer, self.stderr, self.stderr_overflow = None, b'', bytearray(), False
        self.started, self.phase, self.created = time.monotonic(), 0, False
        self.frames, self.cleaning = 0, False
        self.hard_deadline = min(self.started+2700, package['authorized_deadline_monotonic'])
        self.deadline = self.hard_deadline-60

    def command(self, args, *, timeout=30, check=True):
        if self.cleaning:
            need(args[:2] in (['container', 'inspect'], ['container', 'rm']), 'CLEANUP_ONLY_NO_SCIENTIFIC_EXTENSION')
        remaining = (self.cleanup_until if self.cleaning else self.deadline) - time.monotonic()
        need(remaining > 0, 'LIVE_OR_CLEANUP_WINDOW')
        result = subprocess.run(self.docker+args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=max(.001, min(timeout, remaining)))
        need(len(result.stdout) + len(result.stderr) <= 2 * 1024**2, 'DOCKER_DIAGNOSTIC_CEILING')
        if check:
            need(result.returncode == 0, 'DOCKER_COMMAND_FAILED:' + result.stderr.decode(errors='replace')[:1000])
        return result

    def absent(self, result):
        error = result.stderr.decode(errors='replace').lower()
        return result.returncode != 0 and self.name.lower() in error and ('no such' in error or 'not found' in error)

    def create_command(self):
        return ['create', '--pull=never', '--name', self.name, '--label', 'memlife.q1='+self.package['execution_id'],
            '--network', 'none', '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
            '--cpus', '2', '--memory', '6g', '--pids-limit', '512', '--user', '501:20',
            '--tmpfs', '/tmp:rw,nosuid,nodev,size=1g',
            '--mount', f"type=bind,src={self.locations['source']},dst=/code,readonly",
            '--mount', f"type=bind,src={self.runtime['runtime_root']},dst=/task,readonly",
            '--mount', f'type=bind,src={self.store},dst=/state',
            '-e', 'HOME=/tmp/home', '--entrypoint', '/bin/sleep', self.runtime['docker']['image']['Id'],
            str(max(1, min(2700, int(self.hard_deadline-time.monotonic()))))]

    def create(self):
        need(not self.created and not self.store.exists() and not self.store.is_symlink(), 'FRESH_OWNED_STORE')
        info_raw = self.command(['info', '--format', '{{json .NCPU}} {{json .MemTotal}}']).stdout.decode().split()
        admission(dict(CPU_count=int(info_raw[0]), RAM_bytes=int(info_raw[1])), shutil.disk_usage(self.store.parent).free)
        self.command(['image', 'inspect', self.runtime['docker']['image']['Id']])
        need(self.absent(self.command(['container', 'inspect', self.name], check=False)), 'FRESH_OWNED_CONTAINER')
        self.store.mkdir(mode=0o700)
        marker = dict(execution_id=self.package['execution_id'], store=str(self.store))
        Files(self.store).write('.q1-owner.json', marker)
        Files(self.out).write('resources.json', marker | dict(container=self.name))
        command = self.create_command()
        Files(self.out).write('docker-create-intent.json', dict(command=self.docker+command))
        self.command(command)
        self.created = True
        value = strict(self.command(['container', 'inspect', self.name]).stdout)[0]
        need(value['Config']['Labels'].get('memlife.q1') == self.package['execution_id']
             and value['HostConfig']['NetworkMode'] == 'none' and value['HostConfig']['Memory'] == 6*1024**3
             and value['HostConfig']['NanoCpus'] == 2*10**9, 'CONTAINER_ISOLATION')
        Files(self.out).write('docker-container.json', value)
        self.command(['start', self.name])

    def _drain_stderr(self, stream):
        while True:
            chunk = stream.read(4096)
            if not chunk:
                break
            if len(self.stderr) + len(chunk) > 128*1024:
                self.stderr_overflow = True
                if self.process:
                    self.process.kill()
                break
            self.stderr.extend(chunk)

    def read(self):
        until = min(self.deadline, time.monotonic()+600)
        selector = selectors.DefaultSelector()
        selector.register(self.process.stdout, selectors.EVENT_READ)
        try:
            while b'\n' not in self.buffer:
                need(not self.stderr_overflow and time.monotonic() < until, 'SDK_RESPONSE_TIMEOUT_OR_DIAGNOSTIC_CEILING')
                ready = selector.select(min(1, max(.001, until-time.monotonic())))
                if ready:
                    value = os.read(self.process.stdout.fileno(), 65536)
                    need(bool(value), 'SDK_PROCESS_ENDED_WITHOUT_RESPONSE')
                    self.buffer += value
                    need(len(self.buffer) <= 1024**2, 'SDK_RESPONSE_CEILING')
            line, self.buffer = self.buffer.split(b'\n', 1)
            self.frames += 1
            Files(self.out).write(f'transport/phase-{self.phase}-frame-{self.frames:02d}.json',
                dict(evidence_basis='EXACT_WORKER_PYTHON_API_JSON_LINE_NOT_SDK_HTTP_WIRE',
                     base64=base64.b64encode(line+b'\n').decode(), bytes=len(line)+1))
            return strict(line)
        except BaseException:
            self.frames += 1
            Files(self.out).write(f'transport/phase-{self.phase}-partial-{self.frames:02d}.json',
                dict(completion='MALFORMED_OR_PARTIAL_TRANSPORT_UNKNOWN',
                     base64=base64.b64encode(self.buffer[:1024**2]).decode(), bytes=min(len(self.buffer),1024**2)))
            raise
        finally:
            selector.close()

    def start_phase(self, phase):
        need(phase == self.phase+1 and self.process is None, 'ONE_PHASE_PROCESS_NO_RETRY')
        if phase == 1:
            self.create()
        self.phase = phase
        command = ['exec', '-i', self.name, '/task/runtime/.venv/bin/python', '-I', '-B',
                   '-X', 'pycache_prefix=/dev/null', '/code/scripts/research/native_q1_worker.py', '--phase', str(phase)]
        Files(self.out).write(f'docker-phase-{phase}-intent.json', dict(command=self.docker+command))
        self.buffer, self.stderr, self.stderr_overflow = b'', bytearray(), False
        self.process = subprocess.Popen(self.docker+command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.stderr_thread = threading.Thread(target=self._drain_stderr, args=(self.process.stderr,), daemon=True)
        self.stderr_thread.start()
        return self.read()

    def call(self, ordinal, request):
        need(self.process is not None and not self.buffer, 'UNEXPECTED_DUPLICATE_OR_UNSOLICITED_RESPONSE')
        data = canonical(dict(ordinal=ordinal, request=request))+b'\n'
        need(len(data) <= 65536, 'SDK_REQUEST_CEILING')
        self.process.stdin.write(data); self.process.stdin.flush()
        return self.read()

    def close_phase(self):
        closed = self.read()
        self.process.stdin.close()
        code = self.process.wait(timeout=max(.001, min(30, self.deadline-time.monotonic())))
        trailing = self.process.stdout.read(1024**2+1)
        self.stderr_thread.join(timeout=2)
        Files(self.out).write(f'docker-phase-{self.phase}-stderr.json', dict(stderr=self.stderr.decode(errors='replace')))
        if trailing:
            Files(self.out).write(f'transport/phase-{self.phase}-unsolicited.json',
                dict(base64=base64.b64encode(trailing[:1024**2]).decode(), bytes=min(len(trailing),1024**2)))
        need(code == 0 and not self.buffer and not trailing and not self.stderr_overflow and closed.get('internal_llm_attempts') == 0,
             'PROVIDER_CLOSE_OR_UNSOLICITED_OUTPUT')
        need(closed.get('top_level_sdk_calls') == {1:6, 2:8, 3:4}[self.phase], 'WORKER_SDK_COUNT_MISMATCH')
        self.process = None
        return closed

    def cleanup(self):
        errors = []
        # Cleanup is separately bounded and allowed after the scientific deadline.
        self.cleaning, self.cleanup_until = True, min(time.monotonic()+60, self.hard_deadline)
        if self.process:
            self.process.kill()
            self.process.wait(timeout=10)
            self.stderr_thread.join(timeout=2)
            path = self.out/f'docker-phase-{self.phase}-interrupted-stderr.json'
            if not path.exists():
                Files(self.out).write(path.name, dict(stderr=self.stderr.decode(errors='replace')))
            self.process = None
        inspected = self.command(['container', 'inspect', self.name], check=False)
        container_absent = self.absent(inspected)
        if inspected.returncode == 0:
            value = strict(inspected.stdout)[0]
            need(value['Config']['Labels'].get('memlife.q1') == self.package['execution_id'], 'FOREIGN_CONTAINER_CLEANUP_DENIED')
            self.command(['container', 'rm', '--force', value['Id']])
            container_absent = self.absent(self.command(['container', 'inspect', self.name], check=False))
        need(container_absent, 'CONTAINER_ABSENCE_UNKNOWN')
        if self.store.exists():
            marker = strict((self.store/'.q1-owner.json').read_bytes())
            need(not self.store.is_symlink() and marker == dict(execution_id=self.package['execution_id'], store=str(self.store)),
                 'FOREIGN_STORE_CLEANUP_DENIED')
            shutil.rmtree(self.store)
        return dict(container_absent=container_absent, store_absent=not self.store.exists(), errors=errors)
