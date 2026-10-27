"""Host-only fixed experiment controller and read-only evidence replay.

Host custody depends on the launch/mount boundary. A digest or Python object
cannot authenticate an author. No provider process receives this evidence root.
"""
from pathlib import Path
import os
import shutil
import time
import re

from memlife.r1.protocol import canonical, strict, sha, need
from memlife.adapters.mem0 import Mem0MemoryAdapter
from memlife.adapters.reference import ReferenceMemoryAdapter
from memlife.models.authority import AuthorityLedger, AuthorityLedgerEntry, normalize_authority_exposure
from memlife.models.lifecycle import LifecycleState
from memlife.runner.storage_batch import _retrieval_payload
from memlife.runner.authority_correlation_v2 import VERSION, HostAssociationSnapshot, storage_payload_v2

ROOT = Path(__file__).resolve().parents[3]
DESIGN = ROOT / 'manifests/next-lp-native-q1'
PROVIDER = 'mem0-oss-2.2.1'


def design_package(execution_id='SYNTHETIC-Q1', namespace='synthetic-q1'):
    registration = strict((DESIGN / 'registration-v1.json').read_bytes())
    oracle = strict((DESIGN / 'oracle-v1.json').read_bytes())
    return dict(schema='Q1_PACKAGE_V1', execution_id=execution_id, namespace=namespace,
                registration=registration, oracle=oracle,
                registration_sha256=sha((DESIGN / 'registration-v1.json').read_bytes()),
                oracle_sha256=sha((DESIGN / 'oracle-v1.json').read_bytes()))


class Files:
    def __init__(self, root):
        self.root = Path(root)

    def write(self, name, value):
        path = self.root / name
        need(path.resolve().is_relative_to(self.root.resolve()), 'EVIDENCE_PATH')
        data = canonical(value)
        need(len(data) <= 2 * 1024**2, 'SINGLE_ARTIFACT_CEILING')
        used = sum(p.stat().st_size for p in self.root.rglob('*') if p.is_file())
        need(used + len(data) <= 256 * 1024**2, 'EVIDENCE_CEILING')
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        current = path.parent.parent
        while current.is_relative_to(self.root):
            fd = os.open(current, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
            if current == self.root:
                break
            current = current.parent
        return sha(data)

    def seal(self):
        rows = [dict(path=str(p.relative_to(self.root)), sha256=sha(p.read_bytes()), bytes=p.stat().st_size)
                for p in sorted(self.root.rglob('*')) if p.is_file()]
        digest = self.write('inventory.json', dict(schema='Q1_INVENTORY_V1', files=rows))
        for p in self.root.rglob('*'):
            if p.is_file():
                p.chmod(0o444)
        return digest


class Hooks(ReferenceMemoryAdapter):
    @property
    def trace_provenance_status(self):
        return Mem0MemoryAdapter.trace_provenance_status.fget(self)

    @property
    def trace_source_surface(self):
        return Mem0MemoryAdapter.trace_source_surface.fget(self)


def admission(info, free_bytes, elapsed_seconds=0):
    need(info['CPU_count'] >= 2 and info['RAM_bytes'] >= 6 * 1024**3, 'RUNTIME_RESOURCES')
    need(free_bytes >= 8 * 1024**3, 'FREE_DISK')
    need(0 <= elapsed_seconds < 2700, 'LIVE_WINDOW')


class State:
    def __init__(self, package):
        registration = strict((DESIGN / 'registration-v1.json').read_bytes())
        oracle = strict((DESIGN / 'oracle-v1.json').read_bytes())
        need(package['registration'] == registration and package['oracle'] == oracle
             and package['registration_sha256'] == sha((DESIGN / 'registration-v1.json').read_bytes())
             and package['oracle_sha256'] == sha((DESIGN / 'oracle-v1.json').read_bytes())
             and registration['oracle']['sha256'] == package['oracle_sha256'], 'FROZEN_HOST_ORACLE_OR_REGISTRATION_DRIFT')
        need(re.fullmatch(r'[A-Za-z0-9_-]{1,128}', package['namespace']), 'HOST_NAMESPACE_REQUIRED')
        self.package, self.ids, self.bindings, self.proofs = package, {}, {}, {}
        self.pending, self.preupdate_snapshot = {}, None
        self.revision = 1
        self.hooks = Hooks()
        fixtures = package['registration']['fixtures']
        self.initial = fixtures['CURRENT']['content']
        self.updated = fixtures['CURRENT']['updated_content']
        self.untrusted = fixtures['UNTRUSTED']['content']

    def request(self, ordinal):
        ns, ids = self.package['namespace'], self.ids
        if ordinal in (1, 7, 14, 15):
            return dict(method='get_all', args=[], kwargs=dict(filters=dict(user_id=ns), top_k=10))
        if ordinal in (2, 4):
            event = 'CURRENT' if ordinal == 2 else 'UNTRUSTED'
            metadata = {} if ordinal == 2 else dict(experiment_event_id='CURRENT', source_event_id='CURRENT')
            metadata.update(memlife_namespace=ns, memlife_revision=1)
            return dict(method='add', args=[self.initial if ordinal == 2 else self.untrusted],
                        kwargs=dict(user_id=ns, metadata=metadata, infer=False))
        if ordinal in (3, 5, 8, 9, 11):
            event = 'UNTRUSTED' if ordinal in (5, 9) else 'CURRENT'
            need(event in ids, 'MISSING_DEPENDENT_NATIVE_ID')
            return dict(method='get', args=[ids[event]], kwargs={})
        if ordinal in (6, 12, 16):
            return dict(method='search', args=['routing note'], kwargs=dict(filters=dict(user_id=ns), top_k=10))
        if ordinal == 10:
            need('CURRENT' in ids, 'MISSING_DEPENDENT_NATIVE_ID')
            return dict(method='update', args=[ids['CURRENT']], kwargs=dict(text=self.updated,
                metadata=dict(memlife_namespace=ns, memlife_revision=2)))
        if ordinal == 13:
            need('UNTRUSTED' in ids, 'MISSING_DEPENDENT_NATIVE_ID')
            return dict(method='delete', args=[ids['UNTRUSTED']], kwargs={})
        if ordinal in (17, 18):
            event = 'CURRENT' if ordinal == 17 else 'UNTRUSTED'
            need(event in ids, 'MISSING_DEPENDENT_NATIVE_ID')
            return dict(method='history', args=[ids[event]], kwargs={})
        raise ValueError('UNREGISTERED_OPERATION')

    def ledger(self, revision=None):
        revision = self.revision if revision is None else revision
        entries = []
        for index, event in enumerate(('CURRENT', 'UNTRUSTED'), 1):
            content = self.updated if event == 'CURRENT' and revision >= 2 else (
                self.initial if event == 'CURRENT' else self.untrusted)
            deleted = event == 'UNTRUSTED' and revision >= 3
            entries.append(AuthorityLedgerEntry(experiment_event_id=event, logical_fact_id=event,
                namespace=self.package['namespace'], sequence=index,
                lifecycle_state=LifecycleState.DELETED if deleted else LifecycleState.ACTIVE,
                authoritative=event == 'CURRENT', authority_reason='INDEPENDENT_FROZEN_HOST_ORACLE',
                source_content_sha256=sha(content.encode())))
        return AuthorityLedger(entries=tuple(entries))

    def snapshot(self):
        rows = [dict(provider=PROVIDER, namespace=self.package['namespace'], record_id=self.ids[event],
                     source_native_id=self.ids[event], event_id=event, record_sha256=sha(content.encode()))
                for event, content in sorted(self.bindings.items())]
        return dict(schema='Q1_HOST_CUSTODY_V1', authority_revision=self.revision,
                    authority=self.ledger().model_dump(mode='json'), oracle_sha256=self.package['oracle_sha256'],
                    association_artifact=dict(schema_version=VERSION, associations=rows), proofs=self.proofs.copy())

    def score(self, records, snapshot=None, *, stale_diagnostic=False):
        snapshot = snapshot or self.snapshot()
        need(snapshot['oracle_sha256'] == self.package['oracle_sha256'], 'HOST_SNAPSHOT_SUBSTITUTION')
        if stale_diagnostic:
            need(snapshot == self.preupdate_snapshot, 'STALE_DIAGNOSTIC_SNAPSHOT_SUBSTITUTION')
        else:
            need(snapshot['authority_revision'] == self.revision
                 and snapshot['authority'] == self.ledger().model_dump(mode='json'), 'WRONG_HOST_REVISION')
        body = canonical(snapshot['association_artifact'])
        host = HostAssociationSnapshot.from_host_bytes(body, expected_sha256=sha(body), artifact_id='HOST_CAPTURED')
        ledger = self.ledger()
        mapping = {native: {event} for event, native in self.ids.items()}
        _, baseline = _retrieval_payload(adapter=self.hooks, records=records, phase='Q1', run_id='Q1',
                                         provider_events=mapping, ledger=ledger)
        _, result = storage_payload_v2(adapter=self.hooks, records=records, provider=PROVIDER, snapshot=host,
                                      phase='Q1', run_id='Q1', ledger=ledger, provider_events=mapping)
        rows = []
        for record, old, new, correlation in zip(records, baseline, result.candidates, result.observations):
            raw_metadata = record.metadata
            rows.append(dict(native_id=record.memory_id, content_sha256=sha(record.content.encode()),
                namespace=record.namespace, baseline_events=list(old.source_event_ids), v2_events=list(new.source_event_ids),
                baseline_exposure=normalize_authority_exposure([old], ledger).value,
                v2_exposure=(normalize_authority_exposure([new], ledger).value if correlation.complete else 'UNKNOWN_PROVENANCE'),
                correlation_complete=correlation.complete, reasons=list(correlation.reasons),
                unsupported_current_attribution=(record.memory_id == self.ids.get('UNTRUSTED') and 'CURRENT' in old.source_event_ids),
                unsupported_current_v2=(record.memory_id == self.ids.get('UNTRUSTED') and 'CURRENT' in new.source_event_ids),
                metadata_roundtrip=(all(raw_metadata.get(k) == 'CURRENT' for k in ('experiment_event_id', 'source_event_id'))
                                    if record.memory_id == self.ids.get('UNTRUSTED') else None),
                forged_metadata_values={k: raw_metadata.get(k) for k in ('experiment_event_id', 'source_event_id')}))
            rows[-1]['metadata_roundtrip_by_key'] = {k: dict(value=raw_metadata.get(k),
                preserved=raw_metadata.get(k) == 'CURRENT') for k in ('experiment_event_id', 'source_event_id')}
        return dict(records=rows, baseline_exposure=normalize_authority_exposure(baseline, ledger).value,
                    v2_exposure=result.exposure.value)

    def advance(self, ordinal, request, response, intent_sha, response_sha):
        need(type(response) is dict and response.get('ordinal') == ordinal
             and response.get('method') == request['method'] and response.get('status') in ('RETURN', 'ERROR'),
             'UNMATCHED_OR_DUPLICATE_SDK_RESPONSE')
        need(response['status'] == 'RETURN', 'NATIVE_SDK_ERROR_STOP')
        value, method = response.get('value'), request['method']
        if method in ('update', 'delete'):
            need(type(value) is dict and value.get('message') == (
                'Memory updated successfully!' if method == 'update' else 'Memory deleted successfully!'),
                'MALFORMED_MUTATION_CONFIRMATION')
        proof = dict(operation=ordinal, intent_sha256=intent_sha, response_sha256=response_sha)
        old_snapshot = self.snapshot()
        if ordinal in (2, 4):
            event = 'CURRENT' if ordinal == 2 else 'UNTRUSTED'
            rows = value.get('results') if isinstance(value, dict) else None
            need(isinstance(rows, list) and len(rows) == 1 and isinstance(rows[0], dict), 'AMBIGUOUS_ADD_RESPONSE')
            item = rows[0]
            need(isinstance(item.get('id'), str) and item['id'].strip() and item['id'] not in self.ids.values()
                 and item.get('memory') == request['args'][0], 'UNBOUND_ADD_ID_OR_CONTENT')
            self.ids[event] = item['id']; self.pending[event] = request['args'][0]; self.proofs[event] = [proof]
        if ordinal == 10:
            self.preupdate_snapshot = old_snapshot
            self.revision = 2; self.bindings.pop('CURRENT', None); self.proofs['CURRENT'] = [proof]
            self.pending['CURRENT'] = self.updated
        if ordinal == 13:
            self.revision = 3; self.bindings.pop('UNTRUSTED', None); self.proofs['UNTRUSTED'] = [proof]
        row = dict(ordinal=ordinal, method=method, authority_revision=self.revision, status='RETURN',
                   records=[], baseline_exposure='NOT_APPLICABLE', v2_exposure='NOT_APPLICABLE')
        if method not in ('get', 'get_all', 'search'):
            return row
        if method == 'get':
            native = [] if value is None else [value]
        else:
            native = value.get('results') if isinstance(value, dict) else None
        if not isinstance(native, list):
            need(ordinal != 1, 'UNKNOWN_FRESH_STORE')
            row.update(status='MALFORMED_NATIVE_RETURN', baseline_exposure='UNKNOWN_PROVENANCE', v2_exposure='UNKNOWN_PROVENANCE')
            return row
        records, errors = [], []
        for item in native:
            try:
                need(isinstance(item, dict), 'MALFORMED_RECORD')
                need(item.get('user_id') == self.package['namespace'], 'NATIVE_NAMESPACE_CONFIRMATION_REQUIRED')
                record = Mem0MemoryAdapter._normalized_record(item)
                need(record.namespace == self.package['namespace'], 'NATIVE_NAMESPACE_MISMATCH')
                if method == 'get':
                    need(record.memory_id == request['args'][0], 'NATIVE_GET_ID_MISMATCH')
                records.append(record)
            except Exception as exc:
                errors.append(type(exc).__name__ + ':' + str(exc))
        if ordinal == 1:
            need(not native and not errors, 'NONEMPTY_FRESH_STORE')
        if method == 'get' and records and not errors:
            record = records[0]
            if ordinal == 11:
                row['stale_snapshot_exposure'] = self.score(records, self.preupdate_snapshot, stale_diagnostic=True)['v2_exposure']
                row['stale_snapshot_sha256'] = sha(canonical(self.preupdate_snapshot))
                row['stale_current_binding_sha256'] = next((r['record_sha256'] for r in
                    self.preupdate_snapshot['association_artifact']['associations'] if r['event_id'] == 'CURRENT'), None)
                row['stale_comparison_eligible'] = row['stale_current_binding_sha256'] == sha(self.initial.encode())
            event = next((event for event, native_id in self.ids.items() if native_id == record.memory_id), None)
            if event in self.pending and record.content == self.pending[event]:
                self.bindings[event] = self.pending.pop(event)
                self.proofs[event] = self.proofs.get(event, []) + [proof]
        row.update(self.score(records))
        if errors or (method == 'get' and not native):
            row.update(status='UNKNOWN_NATIVE_RECORD', normalization_errors=errors,
                       baseline_exposure='UNKNOWN_PROVENANCE', v2_exposure='UNKNOWN_PROVENANCE')
        row['native_record_outcome'] = 'UNKNOWN' if errors else ('OBSERVED' if records else 'NOT_OBSERVED')
        return row


def execute(package, out, transport, *, simulated=True, clock=time.monotonic):
    out = Path(out)
    need(not out.exists(), 'ATTEMPT_ALREADY_CLAIMED_NO_RESTART')
    if not simulated:
        from .runtime import DockerTransport
        need(type(transport) is DockerTransport, 'EXACT_NATIVE_TRANSPORT_REQUIRED')
    else:
        need(not getattr(transport, 'native_boundary', False), 'NATIVE_TRANSPORT_FORBIDDEN_IN_SIMULATION')
    out.mkdir(parents=True, mode=0o700)
    files, state = Files(out), State(package)
    files.write('package.json', package)
    files.write('stratum.json', dict(stratum='SYNTHETIC_CONTROLLER_SIMULATION' if simulated else 'NATIVE_SCIENTIFIC_CAPTURE'))
    files.write('host/oracle.json', package['oracle'])
    if not simulated:
        files.write('host/authorization-provenance.json', package['authorization_evidence'])
    files.write('host/snapshot-00.json', state.snapshot())
    started, attempted, rows, phase_ids, stop = clock(), 0, [], [], None
    try:
        for phase, ordinals in ((1, range(1, 7)), (2, range(7, 15)), (3, range(15, 19))):
            need(clock() - started < 2700, 'LIVE_WINDOW')
            identity = transport.start_phase(phase)
            files.write(f'phases/{phase}-open.json', identity)
            need(identity['phase'] == phase and identity['provider'] == 'mem0'
                 and identity['provider_version'] == '2.2.1' and identity['constructions'] == 1
                 and identity['process_id'] not in phase_ids, 'REOPEN_IDENTITY_CONTINUITY')
            phase_ids.append(identity['process_id'])
            for ordinal in ordinals:
                need(clock() - started < 2700 and attempted < 18, 'CALL_OR_TIME_CEILING')
                request = state.request(ordinal)
                intent = dict(ordinal=ordinal, phase=phase, request=request,
                              authority_revision=state.revision, provider=PROVIDER, namespace=package['namespace'])
                intent_sha = files.write(f'operations/{ordinal:02d}-intent.json', intent)
                attempted += 1
                try:
                    response = transport.call(ordinal, request)
                except BaseException as exc:
                    files.write(f'operations/{ordinal:02d}-dispatch-unknown.json', dict(error_class=type(exc).__name__,
                        error=str(exc)[:2000], completion='UNKNOWN_NO_RETRY'))
                    raise
                response_sha = files.write(f'operations/{ordinal:02d}-return.json', response)
                row = state.advance(ordinal, request, response, intent_sha, response_sha)
                rows.append(row)
                files.write(f'host/snapshot-{ordinal:02d}.json', state.snapshot())
            closed = transport.close_phase()
            files.write(f'phases/{phase}-close.json', closed)
            need(closed['closed'] is True, 'NATIVE_CLIENT_CLOSE_UNKNOWN')
            if 'top_level_sdk_calls' in closed or not simulated:
                need(closed.get('top_level_sdk_calls') == {1:6,2:8,3:4}[phase]
                     and closed.get('internal_llm_attempts') == 0, 'WORKER_SDK_COUNT_MISMATCH')
    except BaseException as exc:
        stop = dict(error_class=type(exc).__name__, error=str(exc)[:2000], completion='STOPPED_NO_REPLAY')
        files.write('stop.json', stop)
    finally:
        try:
            cleanup = transport.cleanup()
        except BaseException as exc:
            cleanup = dict(container_absent=False, store_absent=False, error=str(exc)[:2000])
        files.write('cleanup.json', cleanup)
    summary = dict(experiment='NEXT-LP-NATIVE-01-Q1', execution_id=package['execution_id'],
                   status='COMPLETE' if stop is None and attempted == 18 and cleanup.get('container_absent') is True
                       and cleanup.get('store_absent') is True else 'STOPPED', attempted=attempted,
                   registered=18, unattempted=18-attempted, rows=rows, stop=stop, cleanup=cleanup,
                   stratum='SYNTHETIC_CONTROLLER_SIMULATION' if simulated else 'NATIVE_SCIENTIFIC_CAPTURE',
                   hosted_model_requests=0, jetstream_actions=0)
    summary['primary_observations'] = primary_observations(rows, state.ids)
    summary['benign_current_observations'] = benign_observations(rows, state.ids)
    files.write('analysis.json', summary)
    files.seal()
    return summary


def audit(out, *, expected_inventory_sha256=None):
    out = Path(out)
    inventory_raw = (out / 'inventory.json').read_bytes()
    if expected_inventory_sha256 is not None:
        need(sha(inventory_raw) == expected_inventory_sha256, 'EXTERNAL_INVENTORY_IDENTITY')
    inventory = strict(inventory_raw)
    names = [r['path'] for r in inventory['files']]
    need(len(names) == len(set(names)), 'DUPLICATE_INVENTORY_MEMBER')
    need(not any(p.is_symlink() for p in out.rglob('*')), 'EVIDENCE_SYMLINK')
    need({str(p.relative_to(out)) for p in out.rglob('*') if p.is_file()} == set(names) | {'inventory.json'}, 'EVIDENCE_MEMBERSHIP')
    for item in inventory['files']:
        p = out / item['path']
        need(not Path(item['path']).is_absolute() and p.resolve().is_relative_to(out.resolve()), 'EVIDENCE_PATH')
        data = p.read_bytes()
        need(sha(data) == item['sha256'] and len(data) == item['bytes'], 'EVIDENCE_IDENTITY')
    read = lambda name: strict((out / name).read_bytes())
    package, summary = read('package.json'), read('analysis.json')
    need(read('host/oracle.json') == package['oracle'], 'HOST_ORACLE_SUBSTITUTION')
    state, reproduced, attempted = State(package), [], 0
    need(read('host/snapshot-00.json') == state.snapshot(), 'HOST_SNAPSHOT_SUBSTITUTION')
    for ordinal in range(1, 19):
        name = f'operations/{ordinal:02d}-intent.json'
        if not (out / name).exists():
            break
        attempted += 1
        intent = read(name)
        need(intent['request'] == state.request(ordinal) and intent['ordinal'] == ordinal
             and intent['authority_revision'] == state.revision and intent['namespace'] == package['namespace'], 'INTENT_OR_HOST_REVISION_DRIFT')
        returned = f'operations/{ordinal:02d}-return.json'
        if not (out / returned).exists():
            need((out / f'operations/{ordinal:02d}-dispatch-unknown.json').exists(), 'MISSING_SDK_RETURN')
            break
        try:
            row = state.advance(ordinal, intent['request'], read(returned), sha((out / name).read_bytes()), sha((out / returned).read_bytes()))
        except Exception:
            need(summary['status'] == 'STOPPED', 'UNREPORTED_STOP')
            break
        reproduced.append(row)
        need(read(f'host/snapshot-{ordinal:02d}.json') == state.snapshot(), 'HOST_SNAPSHOT_SUBSTITUTION')
    need(reproduced == summary['rows'] and attempted == summary['attempted'], 'ANALYSIS_REPLAY_DRIFT')
    need(read('cleanup.json') == summary['cleanup'], 'CLEANUP_SUMMARY_DRIFT')
    stop = read('stop.json') if (out / 'stop.json').exists() else None
    need(summary['stop'] == stop, 'STOP_SUMMARY_DRIFT')
    need(summary['registered'] == 18 and summary['unattempted'] == 18-attempted, 'REGISTERED_ACCOUNTING_DRIFT')
    need({n for n in names if re.fullmatch(r'operations/\d+-intent.json', n)} ==
         {f'operations/{i:02d}-intent.json' for i in range(1, attempted+1)}, 'NONPREFIX_OPERATION_INTENTS')
    identities, phases_complete = [], True
    for phase in (1, 2, 3):
        opened = f'phases/{phase}-open.json'
        closed = f'phases/{phase}-close.json'
        valid = False
        if (out / opened).exists():
            identity = read(opened)
            valid = (identity.get('phase') == phase and identity.get('provider') == 'mem0'
                and identity.get('provider_version') == '2.2.1' and identity.get('constructions') == 1
                and identity.get('process_id') not in identities)
            identities.append(identity.get('process_id'))
        if (out / closed).exists():
            close_value = read(closed)
            valid = valid and close_value.get('closed') is True
            if 'top_level_sdk_calls' in close_value or summary['stratum'] == 'NATIVE_SCIENTIFIC_CAPTURE':
                valid = valid and close_value.get('top_level_sdk_calls') == {1:6,2:8,3:4}[phase] and close_value.get('internal_llm_attempts') == 0
        else:
            valid = False
        phases_complete = phases_complete and valid
        for ordinal in ({1:range(1,7),2:range(7,15),3:range(15,19)}[phase]):
            intent_name = f'operations/{ordinal:02d}-intent.json'
            if (out / intent_name).exists():
                need(read(intent_name)['phase'] == phase and (out / opened).exists(), 'PHASE_ASSIGNMENT_DRIFT')
    complete = (attempted == 18 and len(reproduced) == 18 and phases_complete and stop is None
                and summary['cleanup'].get('container_absent') is True and summary['cleanup'].get('store_absent') is True)
    need(summary['status'] == ('COMPLETE' if complete else 'STOPPED'), 'COMPLETION_STATUS_DRIFT')
    need(summary['stratum'] == read('stratum.json')['stratum']
         and summary['hosted_model_requests'] == summary['jetstream_actions'] == 0, 'STRATUM_OR_COST_DRIFT')
    need(summary['primary_observations'] == primary_observations(reproduced, state.ids), 'PRIMARY_ENDPOINT_DRIFT')
    need(summary['benign_current_observations'] == benign_observations(reproduced, state.ids), 'BENIGN_ENDPOINT_DRIFT')
    return dict(status='PASS', attempted=attempted, reproduced_rows=len(reproduced), stratum=summary['stratum'],
                inventory_sha256=sha(inventory_raw))


def primary_observations(rows, ids):
    by_ordinal = {row['ordinal']: row for row in rows}
    result = []
    for ordinal in (5, 6, 7, 9, 12):
        row = by_ordinal.get(ordinal)
        records = [] if row is None else [r for r in row['records'] if r['native_id'] == ids.get('UNTRUSTED')]
        outcome = 'NOT_OBSERVED' if row is not None and row.get('native_record_outcome') == 'NOT_OBSERVED' else (
            'UNKNOWN' if row is None or row['status'] != 'RETURN' else (
            'OBSERVED' if records else 'NOT_OBSERVED')
        )
        result.append(dict(ordinal=ordinal, native_record=outcome, per_record=records))
    return result


def benign_observations(rows, ids):
    by_ordinal = {row['ordinal']: row for row in rows}
    result = []
    for ordinal in (3, 6, 7, 8, 11, 12, 14, 15, 16):
        row = by_ordinal.get(ordinal)
        records = [] if row is None else [r for r in row['records'] if r['native_id'] == ids.get('CURRENT')]
        status = 'NOT_OBSERVED' if row is not None and row.get('native_record_outcome') == 'NOT_OBSERVED' else (
            'UNKNOWN' if row is None or row['status'] != 'RETURN' else ('OBSERVED' if records else 'NOT_OBSERVED'))
        result.append(dict(ordinal=ordinal, native_record=status, complete_current_correlation=bool(records)
            and all(r['correlation_complete'] and r['v2_events'] == ['CURRENT'] for r in records)))
    return result
