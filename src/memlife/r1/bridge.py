"""Byte-pinned, narrow adaptations of qualified Tier C modules.

No legacy globals or historical source files are mutated. Relative imports bind
the versioned R1 contract/collection and explicit m3.quad access amendment.
"""
import sys
import types

from . import contract
from .protocol import ROOT, need, raw, sha, strict


def transformations(name, source):
    if name == 'access':
        # The complete original module is hash checked before transformation.
        # Preserve every other byte, including allocation/lifecycle restrictions.
        begin = source.index('def verify_flavor(cloud,server):')
        end = source.index('\ndef wait_state(', begin)
        source = source[:begin] + 'from .access_compat import verify_flavor\n' + source[end:]
    replacements = {
        'supervision': [("SCRIPT = ROOT/'scripts/research/tier_c_bounded.py'",
                         "SCRIPT = " + repr(str(ROOT / 'scripts/research/r1.py')) + "\nfrom pathlib import Path\nSCRIPT = Path(SCRIPT)")],
        'runner': [
            ("return [sys.executable,'-I','-B',str(SCRIPT),action,*map(str,extra)]",
             "return [sys.executable,'-I','-B',str(SCRIPT),action,'--package',str(__import__('memlife.r1.contract',fromlist=['PACKAGE']).PACKAGE),*map(str,extra)]"),
            ("'planned_units':60", "'planned_units':32"),
            ("'COMPLETED_60' if completed == 60", "'COMPLETED_32' if completed == 32"),
        ],
    }
    for before, after in replacements.get(name, []):
        need(source.count(before) == 1, 'QUALIFIED_TRANSFORM_FRONTIER:' + name)
        source = source.replace(before, after)
    return source


def effective_sources(accepted_root):
    result = {}
    for name in ('volume', 'access', 'policy', 'supervision', 'collection', 'runner'):
        path = 'src/memlife/tier_c_bounded/' + name + '.py'
        body = raw(accepted_root / path)
        pins = strict(raw(contract.QUALIFIED_PINS))['files']
        need(sha(body) == pins[path], 'QUALIFIED_MODULE_DRIFT')
        result[path] = dict(original_sha256=sha(body),
                            effective_sha256=sha(transformations(name, body.decode()).encode()))
    return result


def load(name, original=None):
    target = 'memlife.r1.' + name
    need(target not in sys.modules, 'R1_MODULE_ALREADY_LOADED')
    original = original or name
    path = contract.ROOT / ('src/memlife/tier_c_bounded/' + original + '.py')
    p = strict(raw(contract.PACKAGE))
    body = raw(path)
    need(sha(body) == p['accepted_sources'][str(path.relative_to(contract.ROOT))], 'QUALIFIED_MODULE_DRIFT')
    effective = transformations(original, body.decode())
    need(p['effective_sources'][str(path.relative_to(contract.ROOT))] ==
         dict(original_sha256=sha(body), effective_sha256=sha(effective.encode())),
         'EFFECTIVE_SOURCE_DRIFT')
    module = types.ModuleType(target)
    module.__file__ = str(path)
    module.__package__ = 'memlife.r1'
    sys.modules[target] = module
    try:
        exec(compile(effective, str(path), 'exec'), module.__dict__)
    except BaseException:
        del sys.modules[target]
        raise
    return module


def install():
    """Call only after offline verification, and owner admission for live commands."""
    for name in ('volume', 'access', 'policy', 'supervision'):
        load(name)
    # Unchanged native cleanup is reused; R1 collection supplies only its unit().
    legacy = load('_accepted_collection', 'collection')
    from . import collection
    collection.cleanup = legacy.cleanup
    return load('runner')
