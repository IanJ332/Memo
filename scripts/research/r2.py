"""Offline verification only. No native execution command exists."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from memlife import r2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['verify-design'])
    parser.add_argument('--qualified-root', type=Path)
    args = parser.parse_args()
    candidate = r2.design()
    sources = r2.qualified_sources(args.qualified_root) if args.qualified_root else 'NOT_CHECKED'
    print(json.dumps({'status': 'OFFLINE_CANDIDATE_ONLY', 'execution_authorized': False,
                      'protocol_sha256': r2.sha(r2.DESIGN.read_bytes()),
                      'qualified_sources': sources, 'phases': candidate['phases'],
                      'sdk_bounds': candidate['bounds']['sdk_calls']}))


if __name__ == '__main__':
    main()
