"""Source-bound R1-AV derivatives of the accepted Tier C lifecycle.

No qualified file is edited. Each transformation has an exact occurrence gate;
both original and effective bytes belong to the prospective source map.
"""
import sys
import types

from memlife.r1.protocol import ROOT, need, raw, sha, strict

R1_BASES = {
    'contract': '9c79e88d993166cab76165cfec45b735d27bc2341a31574e971bee96a5adf2f0',
    'collection': '3e0e8d08fc87f99676506f012ee52582d53f15bc7f12b023c8a27b1c94b44732',
}


def replace(source, before, after, count=1):
    need(source.count(before) == count, 'R1_AV_EXACT_TRANSFORMATION_FRONTIER:' + before[:80])
    return source.replace(before, after)


def basis(name):
    data = raw(ROOT / ('src/memlife/r1/' + name + '.py'))
    need(sha(data) == R1_BASES[name], 'R1_AV_FROZEN_R1_BASIS_DRIFT:' + name)
    return data.decode()


def transform(name, source):
    if name == 'access':
        begin = source.index('def verify_flavor(cloud,server):')
        end = source.index('\ndef wait_state(', begin)
        source = source[:begin] + 'from memlife.r1.access_compat import verify_flavor\n' + source[end:]
    substitutions = {
        'supervision': [("SCRIPT = ROOT/'scripts/research/tier_c_bounded.py'",
                         "from pathlib import Path\nSCRIPT = Path(" + repr(str(ROOT / 'scripts/research/r1_av.py')) + ')')],
        'runner': [
            ("return [sys.executable,'-I','-B',str(SCRIPT),action,*map(str,extra)]",
             "return [sys.executable,'-I','-B',str(SCRIPT),action,'--package',str(__import__('memlife.r1_av.contract',fromlist=['PACKAGE']).PACKAGE),*map(str,extra)]"),
            ("'planned_units':60", "'planned_units':32"),
            ("'COMPLETED_60' if completed == 60", "'COMPLETED_32' if completed == 32"),
        ],
    }
    for before, after in substitutions.get(name, []):
        source = replace(source, before, after)
    return source


def effective_sources(accepted_root):
    from . import contract
    result = {}
    pins = strict(raw(contract.QUALIFIED_PINS))['files']
    for name in ('volume', 'access', 'policy', 'supervision', 'collection', 'runner'):
        path = 'src/memlife/tier_c_bounded/' + name + '.py'
        data = raw(accepted_root / path)
        need(sha(data) == pins[path], 'QUALIFIED_MODULE_DRIFT:' + name)
        result[path] = dict(original_sha256=sha(data), effective_sha256=sha(transform(name, data.decode()).encode()))
    from .native import derived_source
    result['public:src/memlife/r1/collection.py'] = dict(
        original_sha256=R1_BASES['collection'], effective_sha256=sha(derived_source().encode()))
    from .contract import derived_source as contract_source
    result['public:src/memlife/r1/contract.py'] = dict(
        original_sha256=R1_BASES['contract'], effective_sha256=sha(contract_source().encode()))
    return result


def load(name, original=None):
    from . import contract
    original = original or name
    target = 'memlife.r1_av.' + name
    need(target not in sys.modules, 'R1_AV_MODULE_ALREADY_LOADED')
    path = 'src/memlife/tier_c_bounded/' + original + '.py'
    data = raw(contract.ROOT / path)
    p = strict(raw(contract.PACKAGE))
    need(sha(data) == p['accepted_sources'][path], 'QUALIFIED_MODULE_DRIFT')
    source = transform(original, data.decode())
    need(p['effective_sources'][path] == dict(original_sha256=sha(data), effective_sha256=sha(source.encode())),
         'EFFECTIVE_SOURCE_DRIFT')
    module = types.ModuleType(target)
    module.__file__, module.__package__ = str(contract.ROOT / path), 'memlife.r1_av'
    sys.modules[target] = module
    try:
        exec(compile(source, str(contract.ROOT / path), 'exec'), module.__dict__)
    except BaseException:
        del sys.modules[target]
        raise
    return module


def install():
    """After owner admission for all live commands; never called by preparation."""
    for name in ('volume', 'access', 'policy', 'supervision'):
        load(name)
    legacy = load('_accepted_collection', 'collection')
    from . import native
    native.cleanup = legacy.cleanup
    sys.modules['memlife.r1_av.collection'] = native
    return load('runner')
