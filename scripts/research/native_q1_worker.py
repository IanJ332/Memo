"""Fixed native SDK process. Only /state is provider-writable; Host stays outside.

This file is not invoked by offline simulation or readiness commands.
"""
import argparse
from contextlib import redirect_stdout
import os
from pathlib import Path
import sys
import uuid

if not sys.flags.isolated or not sys.dont_write_bytecode:
    raise SystemExit('ISOLATED_BYTECODE_DISABLED_REQUIRED')
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from memlife.r1.protocol import canonical, strict, need


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', type=int, choices=(1, 2, 3), required=True)
    args = parser.parse_args()
    wire = sys.stdout

    def emit(value):
        data = canonical(value)
        need(len(data) < 1024**2, 'NATIVE_RESPONSE_CEILING')
        wire.write(data.decode() + '\n'); wire.flush()

    def guard(event, values):
        if event.startswith('socket.') and event not in ('socket.__new__',):
            raise RuntimeError('ZERO_NETWORK_AND_HOSTED_INFERENCE')
        if event.startswith(('subprocess.', 'os.exec', 'os.spawn')) or event == 'os.system':
            raise RuntimeError('PROVIDER_PROCESS_DISPATCH_FORBIDDEN')
    sys.addaudithook(guard)
    os.environ.update(MEM0_TELEMETRY='false', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
        HF_HUB_DISABLE_TELEMETRY='1', TOKENIZERS_PARALLELISM='false', OMP_NUM_THREADS='2', MKL_NUM_THREADS='2',
        HF_HUB_DISABLE_PROGRESS_BARS='1')
    adapter = None
    calls, llm_attempts = 0, []
    try:
        with redirect_stdout(sys.stderr):
            from memlife.adapters.mem0 import Mem0LocalPaths, Mem0MemoryAdapter
            state = Path('/state')
            paths = Mem0LocalPaths(data_root=state, provider_root=state/'provider', qdrant=state/'provider/qdrant',
                history=state/'provider/history', scratch=state/'provider/scratch', model_cache=Path('/task/model-cache'))
            for path in (paths.qdrant, paths.history, paths.scratch):
                path.mkdir(parents=True, exist_ok=True)
            if args.phase == 1:
                need(not any(paths.qdrant.iterdir()) and not any(paths.history.iterdir()), 'FRESH_STORE_ONLY')
            adapter = Mem0MemoryAdapter(paths)
            def deny_llm(*a, **k):
                llm_attempts.append(True)
                raise RuntimeError('HOSTED_LLM_FORBIDDEN')
            adapter.native_memory.llm.generate_response = deny_llm
        emit(dict(phase=args.phase, process_id=str(os.getpid()) + ':' + str(uuid.uuid4()),
                  provider='mem0', provider_version='2.2.1', constructions=1))
        ordinals = {1: range(1, 7), 2: range(7, 15), 3: range(15, 19)}[args.phase]
        methods = {1:'get_all',2:'add',3:'get',4:'add',5:'get',6:'search',7:'get_all',8:'get',9:'get',
                   10:'update',11:'get',12:'search',13:'delete',14:'get_all',15:'get_all',16:'search',17:'history',18:'history'}
        for ordinal in ordinals:
            line = sys.stdin.buffer.readline(65537)
            need(line and len(line) <= 65536, 'ONE_BOUNDED_REQUEST_REQUIRED')
            command = strict(line)
            request = command['request']
            need(command['ordinal'] == ordinal and request['method'] == methods[ordinal], 'FIXED_SDK_ROSTER')
            calls += 1
            try:
                with redirect_stdout(sys.stderr):
                    value = getattr(adapter.native_memory, request['method'])(*request['args'], **request['kwargs'])
                emit(dict(ordinal=ordinal, method=request['method'], status='RETURN', value=value))
            except Exception as exc:
                emit(dict(ordinal=ordinal, method=request['method'], status='ERROR',
                          error=dict(error_class=type(exc).__name__, message=str(exc)[:2000])))
                return
        with redirect_stdout(sys.stderr):
            adapter.close(); adapter = None
        emit(dict(closed=True, top_level_sdk_calls=calls, internal_llm_attempts=len(llm_attempts)))
    finally:
        if adapter is not None:
            with redirect_stdout(sys.stderr):
                adapter.close()


if __name__ == '__main__':
    main()
