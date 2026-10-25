"""Fresh R1 prospective grant. Closed Tier C grants never enroll this campaign."""
from copy import deepcopy
from datetime import datetime, timezone
import importlib
import os
from pathlib import Path
import stat
import sys

from .protocol import (ROOT as PUBLIC_ROOT, DESIGN, ACL, ENDPOINT, LIMITS, canonical,
                       identity, need, raw, registration, save, sha, strict, verify_identity)

PACKAGE = None
QUALIFIED_PINS = PUBLIC_ROOT / 'manifests/r1-qualified-source-pins-v1.json'
QUALIFIED_PINS_SHA = '9780fc908fae6edd613377f1248463d69d3cda3b6216de73e5c39ee105fc5fa4'
ROOT = BATCH = EXECUTION = OUT = EXECUTION_BINDING = None
HOST = DEST = HOST_ALIAS = HOST_KEY = INSTANCE = KEY = CREDENTIALS = None
PROJECT_ID = USER_ID = None
NATIVE_PROCEDURE = dict(stores_max=16, writes_max=24, queries_max=32, query_limit=10,
    inspect_steps_max=64, history_reads_max=48, distinct_process_reopens_max=16,
    client_constructions_max=32, updates=0, deletes=0, revokes=0,
    mode='INFER_FALSE_LOCAL_EMBEDDINGS', provider='mem0ai', version='2.2.1',
    sentence_transformers='6.1.0', operations_are_harness_bounds_not_sdk_attempt_telemetry=True)
RESOURCE_CONTRACT = dict(window_seconds_max=14400, cleanup_reserve_seconds_min=1800,
    access_VM_flavor='m3.small', access_VM_vcpus=2, access_VM_RAM_MiB=6144,
    existing_rate_SU_per_hour=2, four_hour_SU_ceiling_conditional_on_cleanup=8,
    cloud_billing_hard_cap=False, local_provider_container_memory='6g', local_provider_cpus=2,
    local_provider_network='none', maximum_concurrent_provider_containers=1,
    startup_metadata_GETs_max=1, protected_volume='PRESERVE_DYNAMIC_IDENTITY_VALIDATION_BEFORE_USE',
    lifecycle='CAPTURE_STABLE_INITIAL_STATE_RESTORE_EXACT_NEVER_SHELVE_INITIALLY_ACTIVE',
    routing_changes=False, maximum_owned_management_IPs=1)


def connect_sources(accepted_root):
    """Use the qualified private closure, not a reconstructed public-clone runtime."""
    global PROJECT_ID, USER_ID
    import memlife
    accepted_root = Path(accepted_root)
    need(accepted_root == accepted_root.resolve() and accepted_root != PUBLIC_ROOT, 'ACCEPTED_PRIVATE_CHECKOUT_REQUIRED')
    need(sha(raw(QUALIFIED_PINS)) == QUALIFIED_PINS_SHA, 'QUALIFIED_SOURCE_PINSET_DRIFT')
    for name, digest in strict(raw(QUALIFIED_PINS))['files'].items():
        need(sha(raw(accepted_root / name)) == digest, 'QUALIFIED_SOURCE_DRIFT:' + name)
    memlife.__path__[:] = [str(accepted_root / 'src/memlife'), str(PUBLIC_ROOT / 'src/memlife')]
    old = importlib.import_module('memlife.tier_c_bounded.contract')
    need(old.ROOT == accepted_root, 'ACCEPTED_IMPORT_ROOT_DRIFT')
    PROJECT_ID, USER_ID = old.PROJECT_ID, old.USER_ID
    return old


def source_files(accepted_root):
    files = {}
    for directory in ('src/memlife', 'scripts/research', 'scripts/native_qualification'):
        for path in sorted((accepted_root / directory).rglob('*.py')):
            files[str(path.relative_to(accepted_root))] = sha(raw(path))
    return files


def public_sources():
    paths = [*sorted((PUBLIC_ROOT / 'src/memlife/r1').glob('*.py')),
             PUBLIC_ROOT / 'scripts/research/r1.py', PUBLIC_ROOT / 'tests/research/test_r1.py', QUALIFIED_PINS]
    return {str(p.relative_to(PUBLIC_ROOT)): sha(raw(p)) for p in paths}


def acknowledgment(old):
    ack = deepcopy(old.ACK)
    ack.update(conditional_prompt_capacity_reserve=32 * 262144,
               requested_completion_budget_including_reasoning=131072,
               conditional_combined_capacity_reserve=32 * (262144 + 4096))
    return ack


def prepare(accepted_root, directory, execution_id):
    """Offline only: source/runtime checks, no Docker, provider, SSH or HTTP calls."""
    import re
    need(re.fullmatch(r'R1EX-[A-Za-z0-9-]{1,40}', execution_id), 'EXECUTION_ID')
    m, a, slots = registration()
    directory = Path(directory).resolve()
    need(not directory.exists(), 'EXCLUSIVE_READINESS_PACKAGE')
    accepted_root = Path(accepted_root).resolve()
    old = connect_sources(accepted_root)
    previous = old.verify()  # Accepted offline source/dependency/custody verification.
    old.authenticated_identity({
        'expected_keystone_project_id': old.PROJECT_ID, 'expected_project_name': old.PROJECT_NAME,
        'expected_keystone_user_id': old.USER_ID, 'authenticated_identity_receipt': identity(old.IDENTITY_RECEIPT),
        'access': old.ACCESS})
    output = accepted_root / '.local/r1-campaigns-v1' / execution_id
    need(not output.exists(), 'PROSPECTIVE_OUTPUT_ALREADY_EXISTS')
    package = dict(schema='MEMLIFE_R1_OFFLINE_PACKAGE_V1', execution_id=execution_id, batch_id=execution_id,
                   public_root=str(PUBLIC_ROOT), accepted_root=str(accepted_root), output_root=str(output),
                   design=identity(DESIGN), acl=identity(ACL), slots=slots, limits=LIMITS,
                   public_sources=public_sources(), accepted_sources=source_files(accepted_root),
                   accepted_scientific_manifest=identity(old.MANIFEST),
                   accepted_runtime_manifest=identity(old.strict_policy.MANIFEST),
                   runtime_identity={k: previous[k] for k in ('reference_sources', 'local_dependencies', 'reference_profile')},
                   resource_contract=RESOURCE_CONTRACT,
                   runtime_basis=previous['runtime_location'], endpoint=ENDPOINT,
                   access=old.ACCESS, bounded_risk_acknowledgment=acknowledgment(old),
                   authenticated_identity_receipt=identity(old.IDENTITY_RECEIPT),
                   expected_keystone_project_id=old.PROJECT_ID, expected_project_name=old.PROJECT_NAME,
                   expected_keystone_user_id=old.USER_ID,
                   native_procedure=NATIVE_PROCEDURE,
                   units=execution_units(dict(execution_id=execution_id, slots=slots)),
                   estimated_evidence_bytes=32 * 8 * 1024**2, execution_authorized=False)
    save(directory / 'package.json', package)
    binding = dict(schema='MEMLIFE_R1_EXECUTION_BINDING_V1', package=identity(directory / 'package.json'),
                   execution_id=execution_id, output_root=str(output), slots=slots,
                   native_context='FUTURE_AUTHORIZED_CAPTURE_NOT_YET_KNOWN',
                   requests='JIT_IMMUTABLE_CUSTODY_BEFORE_RESERVATION_AND_SEND')
    save(directory / 'execution-binding.json', binding)
    save(directory / 'owner-grant.json', grant_candidate(directory / 'package.json'))
    return dict(package=identity(directory / 'package.json'), owner_grant=identity(directory / 'owner-grant.json'),
                registered_slots=32, approved=False)


def configure(path):
    global PACKAGE, ROOT, BATCH, EXECUTION, OUT, EXECUTION_BINDING
    global HOST, DEST, HOST_ALIAS, HOST_KEY, INSTANCE, KEY, CREDENTIALS
    PACKAGE = Path(path).resolve()
    p = strict(raw(PACKAGE))
    need(p['schema'] == 'MEMLIFE_R1_OFFLINE_PACKAGE_V1' and p['public_root'] == str(PUBLIC_ROOT), 'PACKAGE_ROOT')
    ROOT = Path(p['accepted_root'])
    BATCH = EXECUTION = p['execution_id']
    OUT = Path(p['output_root'])
    EXECUTION_BINDING = PACKAGE.parent / 'execution-binding.json'
    old = connect_sources(ROOT)
    HOST, DEST, HOST_ALIAS, HOST_KEY, INSTANCE, KEY, CREDENTIALS = (
        old.HOST, old.DEST, old.HOST_ALIAS, old.HOST_KEY, old.INSTANCE, old.KEY, old.CREDENTIALS)
    return p


def verify(path=None):
    need(PACKAGE is not None and (path is None or Path(path) == PACKAGE), 'EXACT_PACKAGE_REQUIRED')
    p = strict(raw(PACKAGE))
    m, a, slots = registration()
    for key, expected in (('design', identity(DESIGN)), ('acl', identity(ACL)), ('slots', slots),
                          ('limits', LIMITS), ('public_sources', public_sources()), ('endpoint', ENDPOINT),
                          ('native_procedure', NATIVE_PROCEDURE), ('resource_contract', RESOURCE_CONTRACT)):
        need(canonical(p[key]) == canonical(expected), 'R1_PACKAGE_DRIFT:' + key)
    for name, digest in p['accepted_sources'].items():
        need(sha(raw(ROOT / name)) == digest, 'ACCEPTED_SOURCE_DRIFT:' + name)
    old = connect_sources(ROOT)
    previous = old.verify()
    need(p['accepted_scientific_manifest'] == identity(old.MANIFEST)
         and p['accepted_runtime_manifest'] == identity(old.strict_policy.MANIFEST)
         and p['access'] == old.ACCESS and p['bounded_risk_acknowledgment'] == acknowledgment(old), 'ACCEPTED_RUNTIME_OR_ACCESS_DRIFT')
    need(p['runtime_basis'] == previous['runtime_location'], 'ACCEPTED_RUNTIME_BASIS_DRIFT')
    need(p['runtime_identity'] == {k: previous[k] for k in ('reference_sources', 'local_dependencies', 'reference_profile')},
         'EXACT_RUNTIME_DEPENDENCY_IDENTITY')
    need(p['accepted_sources'] == strict(raw(QUALIFIED_PINS))['files'], 'EXACT_ACCEPTED_SOURCE_CLOSURE')
    old.authenticated_identity({k: p[k] for k in (
        'expected_keystone_project_id', 'expected_project_name', 'expected_keystone_user_id',
        'authenticated_identity_receipt', 'access')})
    binding = strict(raw(EXECUTION_BINDING))
    need(binding == dict(schema='MEMLIFE_R1_EXECUTION_BINDING_V1', package=identity(PACKAGE),
        execution_id=EXECUTION, output_root=str(OUT), slots=slots,
        native_context='FUTURE_AUTHORIZED_CAPTURE_NOT_YET_KNOWN',
        requests='JIT_IMMUTABLE_CUSTODY_BEFORE_RESERVATION_AND_SEND'), 'EXECUTION_BINDING_DRIFT')
    need(OUT == ROOT / '.local/r1-campaigns-v1' / EXECUTION, 'OUTPUT_SCOPE')
    need(p['batch_id'] == EXECUTION and p['units'] == execution_units(p)
         and p['estimated_evidence_bytes'] == 32 * 8 * 1024**2
         and p['execution_authorized'] is False, 'EXECUTION_PACKAGE_SHAPE')
    return p


def execution_units(p):
    return [{**s, 'unit_id': p['execution_id'] + '-' + str(s['ordinal']).zfill(3)} for s in p['slots']]


def grant_candidate(path):
    p = strict(raw(path))
    return dict(schema='MEMLIFE_R1_PROSPECTIVE_OWNER_GRANT_V1', approved=False,
                package=identity(path), execution_binding=identity(path.parent / 'execution-binding.json'),
                execution_id=p['execution_id'], output_root=p['output_root'], endpoint=ENDPOINT,
                design=p['design'], acl=p['acl'], limits=LIMITS, native_procedure=p['native_procedure'],
                resource_contract=p['resource_contract'], runtime_identity=p['runtime_identity'],
                access=p['access'], bounded_risk_acknowledgment=p['bounded_risk_acknowledgment'],
                window_seconds=14400, cleanup_reserve_seconds=1800, startup_seconds=600,
                local_reference_token_bound=32768, observed_prompt_stop_threshold_each=32768,
                start_within_24h_of_approval=True, protected_tool_dispatch=False, synthetic_only=True,
                expected_keystone_project_id=p['expected_keystone_project_id'],
                expected_project_name=p['expected_project_name'], expected_keystone_user_id=p['expected_keystone_user_id'],
                authenticated_identity_receipt=p['authenticated_identity_receipt'],
                volume_source_revision=identity(path.parent / 'execution-binding.json'),
                diagnostic_seconds_max=600, diagnosis_and_collection_share_one_window=True,
                source_review=None, approval_provenance=None, approved_at=None, not_before=None, expires=None)


def check_grant(p, grant, *, clock=None):
    """Pure owner-grant comparison; JSON fields do not establish human provenance."""
    candidate = grant_candidate(PACKAGE)
    mutable = {'approved', 'source_review', 'approval_provenance', 'approved_at', 'not_before', 'expires'}
    need(set(grant) == set(candidate), 'EXACT_R1_GRANT_SCHEMA')
    need(all(canonical(grant[k]) == canonical(candidate[k])
             for k in candidate.keys() - mutable), 'PROSPECTIVE_GRANT_SCOPE_OR_BUDGET_DRIFT')
    need(grant['approved'] is True, 'NEW_OWNER_APPROVAL_REQUIRED_NO_LIVE_ACTION')
    provenance = grant['approval_provenance']
    need(type(provenance) is dict and set(provenance) == {'kind', 'message_id', 'owner_message'}
         and provenance['kind'] == 'DIRECT_OWNER_MESSAGE' and type(provenance['message_id']) is str
         and bool(provenance['message_id'].strip()), 'GENUINE_OWNER_MESSAGE_PROVENANCE_REQUIRED')
    verify_identity(provenance['owner_message'])
    approval = raw(Path(provenance['owner_message']['path'])).decode()
    need('AUTHORIZE_R1_LIVE' in approval and sha(raw(PACKAGE)) in approval
         and EXECUTION in approval, 'OWNER_MESSAGE_MUST_BIND_EXACT_PROSPECTIVE_PACKAGE')
    times = [datetime.fromisoformat(grant[k]) for k in ('approved_at', 'not_before', 'expires')]
    approved, begin, end = times
    need(all(t.tzinfo is not None and t.utcoffset() is not None for t in times), 'AWARE_GRANT_TIMES')
    now = clock or datetime.now(timezone.utc)
    need(approved <= begin <= now < end and 0 <= (begin - approved).total_seconds() <= 86400
         and (end - begin).total_seconds() == grant['window_seconds'] <= 14400, 'GRANT_WINDOW_OR_APPROVAL_EXPIRED')
    review = grant['source_review']
    verify_identity(review)
    r = strict(raw(Path(review['path'])))
    need(r['schema'] == 'MEMLIFE_R1_INDEPENDENT_OFFLINE_REVIEW_V1' and r['accepted'] is True
         and r['independent_review'] is True and r['package'] == identity(PACKAGE)
         and r['public_sources'] == p['public_sources'] and r['accepted_sources'] == p['accepted_sources']
         and r.get('synthetic', False) is False and r.get('test_scope', False) is False,
         'INDEPENDENT_EXACT_SOURCE_REVIEW_REQUIRED')
    return grant


def authorize(manifest_path, grant_path):
    p = verify(manifest_path)
    g = strict(raw(grant_path))
    check_grant(p, g)
    return p, g


def campaign_owner(mid):
    return dict(batch_id=BATCH, execution_id=EXECUTION, manifest=mid,
                execution_binding=identity(EXECUTION_BINDING), scope='FRESH_TASK_OWNED_OUTPUT_NOT_EXECUTION_AUTHORITY')


def prepared(root, mid):
    need(Path(root) == OUT and OUT.is_dir() and OUT.stat().st_uid == os.getuid()
         and stat.S_IMODE(OUT.stat().st_mode) == 0o700, 'PRIVATE_FRESH_R1_OUTPUT')
    need({p.name for p in OUT.iterdir()} == {'campaign-owner.json'}
         and strict(raw(OUT / 'campaign-owner.json')) == campaign_owner(mid), 'OUTPUT_ALREADY_CONSUMED_NO_REPLAY')


def claim():
    need(not OUT.exists(), 'OUTPUT_REUSE_NO_REPLAY')
    for parent in (OUT, *OUT.parents):
        need(parent == parent.resolve() and not (parent / 'inventory.json').exists(), 'SEALED_OR_SYMLINK_OUTPUT')
    OUT.mkdir(parents=True, mode=0o700)
    save(OUT / 'campaign-owner.json', campaign_owner(identity(PACKAGE)))


def source_revision(_):
    # Compatibility with unchanged cleanup/source-bound runner interfaces.
    return {'revised_code_sha256': strict(raw(PACKAGE))['accepted_sources']}


def identity_revision_authorization(m, g):
    # Cleanup-only source/custody checks survive generation-grant expiry.
    verify(PACKAGE)
    need(g['package'] == identity(PACKAGE) and g['execution_id'] == EXECUTION
         and g['execution_binding'] == identity(EXECUTION_BINDING), 'CLEANUP_R1_INPUT_BINDING')
    return source_revision(m)
