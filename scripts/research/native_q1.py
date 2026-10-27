"""Narrow Q1 CLI. Readiness and simulation never construct a native provider."""
import argparse
import importlib.util
from pathlib import Path
import sys

if not sys.flags.isolated or not sys.dont_write_bytecode:
    raise SystemExit('Use repository .venv python -I -B')
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from memlife.r1.protocol import canonical


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    simulate = commands.add_parser('simulate'); simulate.add_argument('--out', required=True)
    audit = commands.add_parser('audit'); audit.add_argument('--out', required=True); audit.add_argument('--inventory-sha256')
    prepare = commands.add_parser('prepare'); prepare.add_argument('--destination', required=True)
    prepare.add_argument('--runtime-receipt', required=True); prepare.add_argument('--review', action='append', required=True)
    prepare.add_argument('--host-python', required=True)
    verify = commands.add_parser('verify-package'); verify.add_argument('--package', required=True)
    run = commands.add_parser('run'); run.add_argument('--package', required=True); run.add_argument('--grant', required=True)
    args = parser.parse_args()
    if args.command in ('simulate', 'audit'):
        def no_network(event, values):
            if event.startswith(('socket.', 'subprocess.', 'os.exec', 'os.spawn')) or event == 'os.system':
                raise RuntimeError('OFFLINE_ONLY')
        sys.addaudithook(no_network)
    from memlife.native_q1 import core, packaging
    if args.command == 'simulate':
        spec = importlib.util.spec_from_file_location('q1_explicitly_scripted', ROOT/'tests/fakes/q1_scripted.py')
        fake = importlib.util.module_from_spec(spec); spec.loader.exec_module(fake)
        result = core.execute(core.design_package(), args.out, fake.ScriptedTransport(), simulated=True)
    elif args.command == 'audit':
        result = core.audit(args.out, expected_inventory_sha256=args.inventory_sha256)
    elif args.command == 'prepare':
        result = packaging.prepare(args.destination, args.runtime_receipt, args.review, args.host_python)
    elif args.command == 'verify-package':
        package = packaging.verify_package(args.package)
        result = dict(status='PASS', execution_id=package['execution_id'], owner_grant='UNAPPROVED', native_actions=0)
    else:
        result = packaging.run(args.package, args.grant)
    print(canonical(result).decode())


if __name__ == '__main__':
    main()
