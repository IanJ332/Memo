# SPDX-License-Identifier: MIT
"""Shared first-cell qualification; hosted default closed with finite Phase 2B-5 bindings."""
import argparse
import hashlib
import json
import importlib.metadata
import os
import sys
import stat
import time
import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Protocol

ROOT = Path(__file__).resolve().parent.parent
INVENTORY = ROOT / ('docs/research/phase2b5a/inventory-smoke-v2.json'
                    if sys.platform == 'linux' else
                    'docs/research/phase2-provider-v2/inventory-phase2b5-macos-v1.json')
MANIFEST = ROOT / 'docs/research/phase2b1/manifest-v1.json'
MANIFEST_SHA = '5caad31ae6503986384b9dd19bd36c7422e57e040298adee1461cfb5eff0589b'
MODEL = 'gpt-4o-mini-2024-07-18'
DEFAULT_MODEL = 'qwen-3.8-27b'
CELLS = [('authorized', 'ON'), ('authorized', 'OFF'), ('authorized', 'DIAGNOSTIC'),
         ('misleading', 'OFF'), ('misleading', 'DIAGNOSTIC'), ('misleading', 'ON')]
PROTOCOL_LEDGER = ROOT / '.local/phase2b2/first-cell-reservations.sqlite'
MANIFEST_V2 = ROOT / 'docs/research/phase2-provider-v2/manifest-v2-final-r1.json'
MANIFEST_V2_SHA = '08a142369630fd8d80b49387d259677d9cf7455337dad726e881bb789a240685'

class GateError(Exception): pass

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify_loaded_sources(inventory):
    """Compare loaded first-party module origins and source bytes, not provenance.

    This runs after Python imports, so it cannot make untrusted import execution
    safe. The selected launcher and inventory require independent acceptance.
    """
    files = inventory['files']
    for name, module in tuple(sys.modules.items()):
        if name == 'scripts':
            roots = getattr(module, '__path__', ())
            if {Path(p).resolve() for p in roots} != {(ROOT / 'scripts').resolve()} or not (ROOT / 'scripts').resolve().is_relative_to(ROOT):
                raise GateError('MODULE_IMPORT_ROOT_MISMATCH')
            continue
        if not (name == 'memlife' or name.startswith('memlife.') or
                name in ('scripts.nlip_phase2b1_pilot', 'scripts.nlip_phase2b2_launcher')):
            continue
        expected_name = ('src/' + name.replace('.', '/') if name.startswith('memlife')
                         else name.replace('.', '/'))
        candidates = (expected_name + '.py', expected_name + '/__init__.py')
        origin = getattr(getattr(module, '__spec__', None), 'origin', None)
        if not isinstance(origin, str): raise GateError('MODULE_ORIGIN_MISMATCH')
        resolved = Path(origin).resolve()
        matching = [p for p in candidates if p in files and resolved == (ROOT / p).resolve()]
        if not resolved.is_relative_to(ROOT) or len(matching) != 1 or digest(resolved) != files[matching[0]]:
            raise GateError('MODULE_ORIGIN_OR_BYTES_MISMATCH')
        roots = getattr(module, '__path__', None)
        if roots is not None and [Path(p).resolve() for p in roots] != [resolved.parent]:
            raise GateError('MODULE_IMPORT_ROOT_MISMATCH')
    if Path(__file__).resolve() != (ROOT / 'scripts/nlip_phase2b2_launcher.py').resolve():
        raise GateError('ENTRYPOINT_MISMATCH')

def verify_package(expected_digest):
    raw = INVENTORY.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_digest:
        raise GateError('PACKAGE_MISMATCH')
    inventory = json.loads(raw)
    for name, expected in inventory['files'].items():
        p = ROOT / name
        if p.is_symlink() or not p.resolve().is_relative_to(ROOT) or not p.is_file() or digest(p) != expected:
            raise GateError('PACKAGE_MISMATCH')
    runtime = inventory['python']
    if sys.version != runtime['version'] or digest(Path(sys.executable).resolve()) != runtime['sha256']:
        raise GateError('RUNTIME_MISMATCH')
    if inventory.get('format') in ('phase2b5-linux-package-v1','phase2b5a-linux-package-v1'):
        from scripts.nlip_phase2b5_execution import verify_linux_runtime
        verify_linux_runtime(inventory)
    installed = {}
    for distribution in importlib.metadata.distributions():
        metadata = {}
        for name in ('METADATA', 'RECORD', 'WHEEL'):
            value = distribution.read_text(name)
            if value is not None: metadata[name] = hashlib.sha256(value.encode()).hexdigest()
        installed[(distribution.metadata['Name'], distribution.version)] = metadata
    expected = {(item['name'], item['version']): item['metadata_sha256'] for item in inventory['distributions']}
    if installed != expected: raise GateError('DEPENDENCIES_MISMATCH')
    if digest(MANIFEST) != MANIFEST_SHA:
        raise GateError('MANIFEST_MISMATCH')
    manifest = json.loads(MANIFEST.read_bytes())
    if manifest['model'] != MODEL or manifest['max_completion_tokens'] != 256 or manifest['campaign_seconds'] != 600 or manifest['max_request_bytes'] != 65536 or manifest['max_response_bytes'] != 16384:
        raise GateError('CONFIGURATION_MISMATCH')
    if digest(MANIFEST_V2) != MANIFEST_V2_SHA: raise GateError('MANIFEST_MISMATCH')
    v2 = json.loads(MANIFEST_V2.read_bytes())
    if (v2['provider'], v2['model'], v2['endpoint'], v2['authentication']) != (
            'jetstream2_direct', DEFAULT_MODEL,
            'https://llm.jetstream-cloud.org/qwen-3.8-27b/v1/chat/completions', 'NETWORK_SCOPED_NO_SECRET'):
        raise GateError('CONFIGURATION_MISMATCH')
    return inventory

def validate_destination(path):
    path = Path(path)
    parent = path.parent
    if not path.is_absolute() or not parent.is_dir() or parent.is_symlink():
        raise GateError('DESTINATION_PARENT_INVALID')
    info = parent.stat()
    if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise GateError('DESTINATION_PERMISSIONS')
    if path.exists() or path.is_symlink(): raise GateError('DESTINATION_EXISTS')

@dataclass(frozen=True)
class AuthorizationBindings:
    """Claims to compare only after a future trusted verifier establishes provenance.

    This data structure never establishes provenance or grants execution.
    UTC window bounds are seconds since the Unix epoch; end is exclusive.
    """
    package_digest: str
    manifest_digest: str
    model: str
    environment: str
    start_utc: int
    end_utc: int
    scope: str
    max_attempts: int
    cost_ceiling: Decimal
    evidence: str


class IndependentAuthorizationVerifier(Protocol):
    """Integration contract only; no trusted implementation is installed here.

    A future supported platform/owner verifier must authenticate provenance and
    return claims from that mechanism, not from local caller-controlled data.
    The CLI cannot select, configure or instantiate such a verifier today.
    """
    def verify(self) -> AuthorizationBindings: ...


def check_bindings(claims, expected, now_utc):
    """Check shape and exact bindings; this is not a verifier of provenance."""
    if type(claims) is not AuthorizationBindings or type(expected) is not AuthorizationBindings:
        raise GateError('AUTHORIZATION_INVALID')
    for claim in (claims, expected):
        if (any(type(x) is not str or len(x) != 64 or any(c not in '0123456789abcdef' for c in x)
                for x in (claim.package_digest, claim.manifest_digest)) or
            type(claim.model) is not str or not claim.model or
            type(claim.environment) is not str or not claim.environment or
            type(claim.evidence) is not str or not Path(claim.evidence).is_absolute() or
            type(claim.start_utc) is not int or type(claim.end_utc) is not int or
            claim.start_utc >= claim.end_utc or
            claim.scope not in ('FIRST_CELL_ONLY', 'FULL_CAMPAIGN') or
            type(claim.max_attempts) is not int or not 1 <= claim.max_attempts <= 6 or
            type(claim.cost_ceiling) is not Decimal or not claim.cost_ceiling.is_finite() or
            claim.cost_ceiling <= 0):
            raise GateError('AUTHORIZATION_INVALID')
    if (type(now_utc) is not int or not claims.start_utc <= now_utc < claims.end_utc or
        not expected.start_utc <= now_utc < expected.end_utc):
        raise GateError('AUTHORIZATION_EXPIRED')
    if any(getattr(claims, field) != getattr(expected, field) for field in
           ('package_digest', 'manifest_digest', 'model', 'environment', 'evidence')):
        raise GateError('AUTHORIZATION_BINDING_MISMATCH')
    if (expected.scope != claims.scope or expected.max_attempts > claims.max_attempts or
        expected.cost_ceiling > claims.cost_ceiling or expected.start_utc < claims.start_utc or
        expected.end_utc > claims.end_utc):
        raise GateError('AUTHORIZATION_SCOPE_MISMATCH')


# Live modes are hard-disabled: no command-line argument or local fixture grants authority.
# A future implementation needs a supported independent verifier and platform gates.
def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['DRY_RUN', 'FIRST_CELL_ONLY', 'FULL_CAMPAIGN'], default='DRY_RUN')
    parser.add_argument('--package-digest', required=True)
    parser.add_argument('--model', default=DEFAULT_MODEL)
    parser.add_argument('--evidence', required=True)
    args = parser.parse_args(argv)
    try:
        inventory = verify_package(args.package_digest)
        from scripts.nlip_phase2b1_pilot import Pilot  # load before origin checks
        verify_loaded_sources(inventory)
        if args.model != DEFAULT_MODEL: raise GateError('MODEL_MISMATCH')
        validate_destination(args.evidence)
        if args.mode != 'DRY_RUN': raise GateError('INDEPENDENT_AUTHORIZATION_UNAVAILABLE')
        print('DRY_RUN_OK: no credentials, provider, evidence file, or network accessed')
        return 0
    except (GateError, OSError, ValueError, KeyError, TypeError):
        print('BLOCKED: package, configuration, destination, or authorization check failed')
        return 1

if __name__ == '__main__': raise SystemExit(main())

# This simulator uses an in-memory scripted response transport only. It has no
# credential or networking interface and does not implement live authorization.
class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
    def send(self, body, timeout, max_bytes):
        from memlife.nlip.model_adapter import ModelError
        self.calls += 1
        if not self.responses: raise ModelError('PROVIDER_ERROR')
        response = self.responses.pop(0)
        if type(response) is not bytes: raise ModelError('PROVIDER_ERROR')
        return response

def reserve_first_cell(protocol='v1', cell=('authorized','ON')):
    """Consume the single persistent reservation; it is never refunded."""
    parent = PROTOCOL_LEDGER.parent
    if not parent.is_dir() or parent.is_symlink(): raise GateError('LEDGER_PARENT_INVALID')
    info = parent.stat()
    if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise GateError('LEDGER_PARENT_INVALID')
    if PROTOCOL_LEDGER.is_symlink(): raise GateError('LEDGER_INVALID')
    from scripts.nlip_phase2b1_pilot import (MANIFEST_V3,MANIFEST_V3_SHA256,MANIFEST_SMOKE,MANIFEST_SMOKE_SHA256,
        MANIFEST_V4,MANIFEST_V4_SHA256,MANIFEST_V4_SMOKE,MANIFEST_V4_SMOKE_SHA256)
    choices={'v1':(MANIFEST,MANIFEST_SHA),'v2':(MANIFEST_V2,MANIFEST_V2_SHA),
             'v3':(MANIFEST_V3,MANIFEST_V3_SHA256),'smoke':(MANIFEST_SMOKE,MANIFEST_SMOKE_SHA256),
             'v4':(MANIFEST_V4,MANIFEST_V4_SHA256),'v4-smoke':(MANIFEST_V4_SMOKE,MANIFEST_V4_SMOKE_SHA256)}
    if protocol not in choices: raise GateError('UNKNOWN_PROTOCOL')
    manifest,manifest_sha=choices[protocol]
    if digest(manifest) != manifest_sha: raise GateError('MANIFEST_MISMATCH')
    if type(cell) is not tuple or len(cell)!=2: raise GateError('CELL_SCOPE_MISMATCH')
    if protocol in ('smoke','v4-smoke'):
        if list(cell) not in json.loads(manifest.read_bytes())['live_cells']:raise GateError('CELL_SCOPE_MISMATCH')
    elif cell!=('authorized','ON'):raise GateError('CELL_SCOPE_MISMATCH')
    cell_id='/'.join(cell)
    reservation=(manifest_sha+':first-cell:'+cell_id if protocol=='v4' else
                 manifest_sha+':'+cell_id if protocol in ('smoke','v4-smoke') else manifest_sha)
    # V4 smoke is deliberately unavailable until the evidence-linked PASS gate is installed.
    if protocol=='v4-smoke': raise GateError('V4_COMPATIBILITY_PASS_GATE_UNAVAILABLE')
    # Exclusive lock and unique primary key make all supported invocations share
    # a single non-refundable reservation regardless of evidence path.
    with sqlite3.connect(PROTOCOL_LEDGER, timeout=2) as db:
        db.execute('PRAGMA synchronous=FULL')
        db.execute('CREATE TABLE IF NOT EXISTS reservations (protocol TEXT PRIMARY KEY, cell TEXT NOT NULL)')
        db.execute('BEGIN IMMEDIATE')
        try:
            db.execute('INSERT INTO reservations VALUES (?, ?)', (reservation, cell_id))
        except sqlite3.IntegrityError:
            raise GateError('FIRST_CELL_ALREADY_RESERVED') from None
    if sys.platform == 'linux':
        # A failed durability observation leaves the committed slot consumed.
        for path in (PROTOCOL_LEDGER, parent):
            fd = os.open(path, os.O_RDONLY)
            try: os.fsync(fd)
            finally: os.close(fd)

def fake_first_cell_operator(path, transport, *, authorization_window):
    """Legacy fake helper; no live authority is implied."""
    if type(transport) is not FakeTransport:
        raise GateError('INVALID_FAKE_SCOPE_OR_TRANSPORT')
    validate_destination(path)
    from scripts.nlip_phase2b1_pilot import Pilot
    reserve_first_cell()
    return Pilot(path, transport, authorization_window=authorization_window, protocol='v1').run('authorized', 'ON')

def first_cell_operator(path, responses, *, authorization_window, package_digest, protocol='v2', fake_transport=None):
    return _first_cell_orchestration(path, responses, authorization_window=authorization_window,
        package_digest=package_digest, protocol=protocol, fake_transport=fake_transport)

def require_hosted_admission(execution=None, *, path=None, authorization_window=None, package_digest=None, cell=('authorized','ON')):
    """Default closed; compare the reviewed finite Phase 2B-5 execution scope.

    No argument, local flag, tuple or digest can establish owner/platform approval.
    """
    if execution is None:
        raise GateError('HOSTED_ADMISSION_UNAVAILABLE')
    from scripts.nlip_phase2b5_execution import Phase2B5Execution
    from scripts.nlip_phase2b5_execution import Phase2B5AExecution,Phase2B5SmokeExecution
    if type(execution) not in (Phase2B5Execution,Phase2B5AExecution,Phase2B5SmokeExecution):
        raise GateError('HOSTED_ADMISSION_UNAVAILABLE')
    execution.check(path, authorization_window, package_digest,cell=cell)

def hosted_first_cell_operator(path, *, authorization_window, package_digest, offline_io=None, execution=None, protocol='v2', cell=('authorized','ON')):
    """Shared direct path; scripted I/O or separately reviewed finite execution."""
    return _first_cell_orchestration(path, [], authorization_window=authorization_window,
        package_digest=package_digest, protocol=protocol, direct=True, offline_io=offline_io, execution=execution,cell=cell)

def _first_cell_orchestration(path, responses, *, authorization_window, package_digest,
                              protocol, fake_transport=None, direct=False, offline_io=None, execution=None,cell=('authorized','ON')):
    """Shared operator orchestration, with explicit hosted admission before reserve.

    The supplied digest is an integrity comparison only, never an approval.
    The persistent reservation is taken before constructing any transport.
    """
    # V4 has no reviewed live execution binding yet. Never permit an older
    # execution object to authorize it, even though scripted direct I/O is safe.
    if protocol in ('v4', 'v4-smoke') and (not direct or offline_io is None):
        raise GateError('V4_HOSTED_ADMISSION_UNAVAILABLE')
    inventory = verify_package(package_digest)
    from scripts.nlip_phase2b1_pilot import Pilot
    verify_loaded_sources(inventory)
    if direct:
        from memlife.nlip.model_adapter import JetstreamDirectTransport, ScriptedDirectIO
        if offline_io is None:
            require_hosted_admission(execution, path=path,
                authorization_window=authorization_window, package_digest=package_digest,cell=cell)
        elif type(offline_io) is not ScriptedDirectIO: raise GateError('INVALID_OFFLINE_IO')
    if type(responses) is not list or any(type(item) is not bytes for item in responses):
        raise GateError('INVALID_FAKE_SCOPE_OR_TRANSPORT')
    if fake_transport is not None and type(fake_transport) is not FakeTransport:
        raise GateError('INVALID_FAKE_SCOPE_OR_TRANSPORT')
    if (type(authorization_window) is not tuple or len(authorization_window) != 2 or
        any(type(value) not in (int, float) for value in authorization_window) or
        not authorization_window[0] < authorization_window[1]):
        raise GateError('AUTHORIZATION_INVALID')
    if not authorization_window[0] <= time.time() < authorization_window[1]:
        raise GateError('AUTHORIZATION_EXPIRED')
    validate_destination(path)
    reserve_first_cell(protocol,cell)
    if not authorization_window[0] <= time.time() < authorization_window[1]:
        raise GateError('AUTHORIZATION_EXPIRED')
    try:
        transport = (JetstreamDirectTransport(provider='jetstream2_direct', model=DEFAULT_MODEL, offline_io=offline_io)
                     if direct else (fake_transport if fake_transport is not None else FakeTransport(responses)))
        return Pilot(path, transport, authorization_window=authorization_window, protocol=protocol).run(*cell)
    except Exception:
        # This fake-only boundary must not expose injected exception details.
        # The already committed protocol reservation remains consumed.
        raise GateError('OPERATOR_FAILED') from None

def fake_campaign(path, scope, transport, *, max_attempts=6, deadline_seconds=600, synthetic_claims=None, synthetic_expected=None, clock=None):
    """Legacy v1 fake regression only; no live authority or v2 budget."""
    if scope not in ('FIRST_CELL_ONLY', 'FULL_CAMPAIGN') or type(transport) is not FakeTransport:
        raise GateError('INVALID_FAKE_SCOPE_OR_TRANSPORT')
    if type(max_attempts) is not int or not 1 <= max_attempts <= 6 or not 0 < deadline_seconds <= 600:
        raise GateError('INVALID_FAKE_BUDGET')
    if synthetic_claims is not None or synthetic_expected is not None or clock is not None:
        if not callable(clock): raise GateError('AUTHORIZATION_INVALID')
        check_bindings(synthetic_claims, synthetic_expected, clock())
        if (synthetic_expected.scope != scope or synthetic_expected.max_attempts != max_attempts or
            synthetic_expected.evidence != str(path) or synthetic_expected.model != MODEL or
            synthetic_expected.manifest_digest != MANIFEST_SHA):
            raise GateError('AUTHORIZATION_BINDING_MISMATCH')
    validate_destination(path)
    from scripts.nlip_phase2b1_pilot import Pilot
    p = Pilot(path, transport, protocol='v1')
    p.started -= 600 - deadline_seconds
    rows = []
    for scenario, arm in CELLS[:max_attempts if scope == 'FULL_CAMPAIGN' else 1]:
        if time.monotonic() - p.started >= 600: break
        if clock is not None:
            try: check_bindings(synthetic_claims, synthetic_expected, clock())
            except GateError: break
        row = p.run(scenario, arm)
        rows.append(row)
        durable = p.observations()
        compatible = (durable == rows and row['state'] == 'FINISHED' and
                      row['model_status'] == 'ACCEPTED' and row['proposal_validity'] == 'VALID' and
                      row['model'] == MODEL and row['error'] is None and row['retries'] == 0 and
                      row['attempt_count'] == 1 and row['policy_evidence'] is not None and
                      time.monotonic() - p.started < 600)
        if len(rows) == 1:
            compatible = (compatible and row['model_outcome'] == 'PROPOSE_ACTION' and
                          row['dispatcher_decision'] == 'ALLOW' and row['delivered'] is True and
                          row['commit_status'] == 'COMMITTED' and row['task_outcome'] == 'AUTHORIZED_SUCCESS')
        else:
            outcome = (row['model_outcome'] == 'ABSTAIN' and row['delivered'] is False and
                       row['commit_status'] == 'NOT_ATTEMPTED') or (
                       row['model_outcome'] == 'PROPOSE_ACTION' and row['commit_status'] == 'COMMITTED' and
                       (row['dispatcher_decision'], row['delivered']) in (('ALLOW', True), ('DENY', False)))
            compatible = compatible and outcome
        if not compatible: break
    return rows
