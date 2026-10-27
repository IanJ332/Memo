"""NEXT-LP-01 offline-only registration, evaluation and read-only audit."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"src"))


def no_external(event, args):
    if event.startswith("socket.") or event in ("subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.fork"):
        raise PermissionError("NEXT_LP01_NETWORK_AND_PROCESS_DISPATCH_FORBIDDEN")


def main():
    if not sys.flags.isolated or not sys.dont_write_bytecode:
        raise ValueError("REPOSITORY_VENV_-I_-B_REQUIRED")
    sys.addaudithook(no_external)
    from memlife import next_lp01 as study
    from memlife.r1.protocol import canonical
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("verify-registration", "run", "audit"))
    parser.add_argument("--out", type=Path)
    parser.add_argument("--review", type=Path)
    args = parser.parse_args()
    if args.command == "verify-registration":
        study.registration()
        result = dict(registered_rows=48, scientific_model_requests=0, execution="OFFLINE_ONLY")
    else:
        if args.out is None:
            raise ValueError("EXACT_EVIDENCE_DIRECTORY_REQUIRED")
        if args.command == "run":
            if args.review is None:
                raise ValueError("EXACT_INDEPENDENT_PRE_EXECUTION_SOURCE_REVIEW_REQUIRED")
            result = study.run(args.out, args.review.resolve())
        else:
            result = study.audit(args.out)
    print(canonical(result).decode())


if __name__ == "__main__":
    main()
