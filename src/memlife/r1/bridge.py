"""Byte-pinned, narrow adaptations of qualified Tier C modules.

No legacy globals or historical source files are mutated. Relative imports bind
the versioned R1 contract/collection while reusing qualified access and policy.
"""
import sys
import types

from . import contract
from .protocol import ROOT, need, raw, sha, strict


def transformations(name, source):
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


def load(name, original=None):
    target = 'memlife.r1.' + name
    need(target not in sys.modules, 'R1_MODULE_ALREADY_LOADED')
    original = original or name
    path = contract.ROOT / ('src/memlife/tier_c_bounded/' + original + '.py')
    p = strict(raw(contract.PACKAGE))
    body = raw(path)
    need(sha(body) == p['accepted_sources'][str(path.relative_to(contract.ROOT))], 'QUALIFIED_MODULE_DRIFT')
    module = types.ModuleType(target)
    module.__file__ = str(path)
    module.__package__ = 'memlife.r1'
    sys.modules[target] = module
    try:
        exec(compile(transformations(original, body.decode()), str(path), 'exec'), module.__dict__)
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
