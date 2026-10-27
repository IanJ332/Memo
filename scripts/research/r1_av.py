"""R1-AV-v1 offline commands; live subcommands require separately bound authority."""
import argparse
import json
import os
from pathlib import Path
import select
import signal
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from memlife.r1_av.protocol import (canonical, diversity, identity, need, raw, registration, save, strict)


def stop(*_):
    raise SystemExit('OWNED_PROCESS_STOP_NO_RETRY')


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
    parser.add_argument('command', choices=('verify-design', 'validate', 'synthetic', 'prepare', 'verify',
                        'verify-review', 'analyze', 'audit', 'execute', 'guardian', 'unit', 'cleanup-native', 'cleanup-owned'))
    for key in ('accepted-root', 'out', 'package', 'manifest', 'grant', 'root', 'review'):
        parser.add_argument('--'+key, type=Path)
    parser.add_argument('--execution-id')
    parser.add_argument('--ordinal', type=int)
    parser.add_argument('--deadline', type=float)
    args = parser.parse_args()
    m, _, slots = registration()
    if args.command in ('verify-design', 'validate'):
        # Pure offline structural and source transformation checks; focused tests
        # are a separate command so validation never silently spawns a process.
        from memlife.r1_av import contract, native
        from memlife.r1_av.runtime import effective_sources
        result = dict(registered_slots=len(slots), experiment=m['experiment'], execution_authorized=False,
                      diversity=diversity(m['blocks']), transformations='PASS')
        if args.accepted_root:
            from memlife.r1_av.synthetic import qualified_sources
            qualified_sources(args.accepted_root)
            result['effective_sources'] = effective_sources(args.accepted_root.resolve())
        print(json.dumps(result)); return
    if args.command == 'synthetic':
        need(args.accepted_root and args.out, 'SYNTHETIC_INPUTS')
        from memlife.r1_av.synthetic import run
        print(json.dumps(run(args.accepted_root, args.out))); return
    from memlife.r1_av import contract
    if args.command == 'prepare':
        need(args.accepted_root and args.out and args.execution_id, 'EXACT_PREPARATION_INPUTS_REQUIRED')
        print(json.dumps(contract.prepare(args.accepted_root, args.out, args.execution_id))); return
    need(args.package is not None, 'EXACT_OFFLINE_PACKAGE_REQUIRED')
    contract.configure(args.package)
    package = contract.verify(args.package.resolve())
    if args.command == 'verify':
        print(json.dumps(dict(status='OFFLINE_VERIFIED_OWNER_APPROVAL_REQUIRED',
                    package=identity(contract.PACKAGE), registered_slots=32, execution_authorized=False))); return
    if args.command == 'verify-review':
        need(args.review, 'EXACT_PACKAGE_REVIEW_REQUIRED')
        from memlife.r1_av.review import verify_review
        print(json.dumps(verify_review(package, args.review.resolve()))); return
    if args.command in ('analyze', 'audit'):
        from memlife.r1_av.audit import reproduce
        result = reproduce(contract.OUT, package)
        if args.command == 'analyze':
            need(args.out, 'EXCLUSIVE_ANALYSIS_OUTPUT_REQUIRED')
            save(args.out.resolve(), result)
            result = dict(output=identity(args.out.resolve()), registered_slots=32)
        print(json.dumps(result)); return
    if args.command not in ('cleanup-native', 'cleanup-owned'):
        need(args.grant is not None, 'NEW_OWNER_GRANT_REQUIRED')
        contract.authorize(contract.PACKAGE, args.grant.resolve())
    else:
        need(args.root and args.root.resolve() == contract.OUT and not (contract.OUT / 'inventory.json').exists(),
             'EXACT_UNSEALED_R1_AV_CLEANUP_ONLY')
        need((contract.OUT / 'owner-authorization.json').exists(), 'NO_AUTHORIZED_ATTEMPT_TO_CLEAN')
        contract.identity_revision_authorization(package, strict(raw(contract.OUT / 'owner-authorization.json')))
    from memlife.r1_av.runtime import install
    runner = install()
    if args.command == 'execute':
        contract.claim()
        print(json.dumps(runner.execute(contract.PACKAGE, args.grant.resolve()))); return
    need(args.root and args.root.resolve() == contract.OUT, 'EXACT_CAMPAIGN_ROOT_REQUIRED')
    if args.command == 'cleanup-native':
        from memlife.r1_av.native import cleanup
        cleanup(contract.OUT)
    elif args.command == 'cleanup-owned':
        print(json.dumps(runner.recovery(contract.OUT)))
    elif args.command == 'unit':
        need(args.ordinal is not None and args.deadline is not None, 'UNIT_IDENTITY_AND_DEADLINE_REQUIRED')
        from memlife.r1_av.native import unit
        unit(contract.PACKAGE, args.grant.resolve(), contract.OUT, args.ordinal, args.deadline)
    else:
        from memlife.r1_av.supervision import ParentWatcher
        with ParentWatcher(sys.stdin.buffer, lambda: os.kill(os.getpid(), signal.SIGTERM)):
            runner.guardian(contract.PACKAGE, args.grant.resolve(), contract.OUT)


if __name__ == '__main__':
    main()
