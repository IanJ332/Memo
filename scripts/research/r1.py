"""R1 entrypoint: offline preparation by default; explicit new owner grant for live work."""
import argparse
import json
import os
from pathlib import Path
import select
import signal
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from memlife.r1 import contract
from memlife.r1.protocol import (canonical, classify, identity, need, raw, registration,
                                save, sha, strict, analyze)


def stop(*_):
    raise SystemExit('OWNED_PROCESS_STOP_NO_RETRY')


def analysis(package, output):
    """Read-only reproduction after collection; no authentic F04 enrollment implied."""
    from memlife.batch.evidence import verify_seal
    verify_seal(contract.OUT)
    need(strict(raw(contract.OUT / 'batch.json')) == package, 'ANALYSIS_ORIGINAL_PACKAGE')
    rows = []
    for slot in package['units']:
        folder = contract.OUT / 'units' / slot['unit_id']
        path = folder / 'scoring.json'
        result = dict(primary='INCOMPLETE_OR_UNKNOWN', unauthorized_indicator=None,
                      complete_response=False, attempted=False, slot_id=slot['slot_id'])
        if (folder / 'model/receipt.json').exists():
            receipt = strict(raw(folder / 'model/receipt.json'))
            bid = int(slot['block_id'].rsplit('-', 1)[1]) - 1
            _, acl, _ = registration()
            recomputed = classify(raw(folder / 'model/response.body.raw'), acl['records'][bid],
                                  entity_complete=receipt['entity_complete'], http_status=receipt['HTTP_status'])
            need(path.exists(), 'SCORING_RECEIPT_MISSING_FOR_CAPTURED_MODEL_OUTCOME')
            saved = strict(raw(path))
            need(all(saved[k] == v for k, v in recomputed.items()), 'REPRODUCED_SCORING_MISMATCH')
            result = {**saved, 'slot_id': slot['slot_id'], 'attempted': receipt['POST_attempted_or_ambiguous']}
        rows.append(result)
    result = analyze(rows, package['slots'])
    result['campaign_inventory'] = identity(contract.OUT / 'inventory.json')
    # Safe aggregate plus per-unit exposure/usage; no raw notes or argument strings.
    result['units'] = [{k: r[k] for k in ('slot_id', 'primary', 'unauthorized_indicator',
        'attempted', 'complete_response', 'format_flags', 'usage', 'selected_current_positions',
        'selected_historical_positions') if k in r} for r in rows]
    save(output, result)
    return dict(output=identity(output), registered_slots=32, complete_blocks=result['complete_blocks'])


def main():
    need(sys.flags.isolated and sys.dont_write_bytecode, 'REPOSITORY_VENV_-I_-B_REQUIRED')
    signal.signal(signal.SIGTERM, stop)
    if len(sys.argv) > 1 and sys.argv[1] == 'exec-go':
        need(select.select([sys.stdin], [], [], 10)[0], 'NO_DURABLE_GO_TIMEOUT')
        need(sys.stdin.buffer.readline(4) == b'GO\n', 'NO_DURABLE_GO_EOF')
        args = sys.argv[3:]
        need(sys.argv[2] == '--' and bool(args), 'BOOTSTRAP_EXACT_COMMAND')
        os.execvpe(args[0], args, os.environ)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('verify-design', 'prepare', 'verify', 'execute',
                        'guardian', 'unit', 'cleanup-native', 'cleanup-owned', 'analyze'))
    parser.add_argument('--accepted-root', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--execution-id')
    parser.add_argument('--package', type=Path)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--grant', type=Path)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--ordinal', type=int)
    parser.add_argument('--deadline', type=float)
    args = parser.parse_args()
    if args.command == 'verify-design':
        _, _, slots = registration()
        print(json.dumps(dict(registered_slots=len(slots), execution_authorized=False)))
        return
    if args.command == 'prepare':
        need(args.accepted_root and args.out and args.execution_id, 'EXACT_PREPARATION_INPUTS_REQUIRED')
        print(json.dumps(contract.prepare(args.accepted_root, args.out, args.execution_id)))
        return
    need(args.package is not None, 'EXACT_OFFLINE_PACKAGE_REQUIRED')
    contract.configure(args.package)
    package = contract.verify(args.package.resolve())
    if args.command == 'verify':
        print(json.dumps(dict(status='OFFLINE_VERIFIED_OWNER_APPROVAL_REQUIRED',
                              package=identity(contract.PACKAGE), registered_slots=32, execution_authorized=False)))
        return
    if args.command == 'analyze':
        need(args.out is not None, 'EXCLUSIVE_ANALYSIS_OUTPUT_REQUIRED')
        print(json.dumps(analysis(package, args.out.resolve())))
        return
    # Admission precedes bridge installation, native construction, SSH or HTTP.
    if args.command not in ('cleanup-native', 'cleanup-owned'):
        need(args.grant is not None, 'NEW_OWNER_GRANT_REQUIRED')
        contract.authorize(contract.PACKAGE, args.grant.resolve())
    else:
        need(args.root is not None and args.root.resolve() == contract.OUT and
             not (contract.OUT / 'inventory.json').exists(), 'EXACT_UNSEALED_R1_CLEANUP_ONLY')
        need((contract.OUT / 'owner-authorization.json').exists(), 'NO_EXISTING_AUTHORIZED_ATTEMPT_TO_CLEAN')
        grant = strict(raw(contract.OUT / 'owner-authorization.json'))
        contract.identity_revision_authorization(package, grant)
    from memlife.r1.bridge import install
    runner = install()
    if args.command == 'execute':
        contract.claim()
        print(json.dumps(runner.execute(contract.PACKAGE, args.grant.resolve())))
        return
    need(args.root is not None and args.root.resolve() == contract.OUT, 'EXACT_CAMPAIGN_ROOT_REQUIRED')
    if args.command == 'cleanup-native':
        from memlife.r1.collection import cleanup
        cleanup(contract.OUT)
    elif args.command == 'cleanup-owned':
        print(json.dumps(runner.recovery(contract.OUT)))
    elif args.command == 'unit':
        need(args.ordinal is not None and args.deadline is not None, 'UNIT_IDENTITY_AND_DEADLINE_REQUIRED')
        from memlife.r1.collection import unit
        unit(contract.PACKAGE, args.grant.resolve(), contract.OUT, args.ordinal, args.deadline)
    else:
        from memlife.r1.supervision import ParentWatcher
        with ParentWatcher(sys.stdin.buffer, lambda: os.kill(os.getpid(), signal.SIGTERM)):
            runner.guardian(contract.PACKAGE, args.grant.resolve(), contract.OUT)


if __name__ == '__main__':
    main()
