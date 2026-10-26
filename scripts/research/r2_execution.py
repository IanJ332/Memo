"""R2 offline verification and separately authorized future local-native entrypoint."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from memlife import r2_execution as execution


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('verify-package', 'execute', 'worker'))
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--package-sha256', required=True)
    parser.add_argument('--review', type=Path)
    parser.add_argument('--review-sha256')
    parser.add_argument('--grant', type=Path)
    parser.add_argument('--phase', choices=execution.contract()['phases'])
    args = parser.parse_args()
    if args.action == 'worker':
        execution.need(args.phase is not None, 'PHASE_REQUIRED')
        execution.worker(args.package, args.package_sha256, args.phase)
    elif args.action == 'execute':
        execution.need(args.review and args.review_sha256 and args.grant, 'AUTHORIZATION_INPUTS')
        execution.execute(args.package, args.package_sha256, args.review, args.review_sha256, args.grant)
    else:
        p = execution.verify_package(args.package, args.package_sha256)
        execution.need(args.review and args.review_sha256, 'EXACT_REVIEW_REQUIRED')
        execution.review(args.review, args.review_sha256, args.package, p)
        print('OFFLINE_PACKAGE_REVIEW_VERIFIED; EXECUTION_NOT_AUTHORIZED')


if __name__ == '__main__':
    main()
