"""R1-AV source-bound successor to R1 admission, without changing frozen R1.

JSON identity checks establish byte binding, never human or platform authority.
The caller must retain genuine owner/external provenance through supported gates.
"""
from pathlib import Path
from .runtime import basis, replace


def derived_source():
    source = basis('contract')
    source = replace(source, "from .bridge import effective_sources", "from .runtime import effective_sources", 2)
    source = replace(source, 'MEMLIFE_R1_', 'MEMLIFE_R1_AV_', 6)
    source = replace(source, "r'R1EX-", "r'R1AVEX-")
    source = replace(source, "'.local/r1-campaigns-v1'", "'.local/r1-av-campaigns-v1'", 2)
    source = replace(source, "'AUTHORIZE_R1_LIVE'", "'AUTHORIZE_R1_AV_LIVE'")
    source = replace(source, "stores_max=16, writes_max=24, queries_max=32", "stores_max=32, writes_max=64, queries_max=64")
    source = replace(source, "inspect_steps_max=64, history_reads_max=48, distinct_process_reopens_max=16", "inspect_steps_max=128, history_reads_max=128, distinct_process_reopens_max=32")
    source = replace(source, 'client_constructions_max=32', 'client_constructions_max=64')
    source = replace(source, "source_review=None, approval_provenance=None, approved_at=None, not_before=None, expires=None)",
                     "source_review=None, approval_provenance=None, external_approval_reference=None, approved_at=None, not_before=None, expires=None)")
    source = replace(source, "'approval_provenance', 'approved_at'", "'approval_provenance', 'external_approval_reference', 'approved_at'")
    source = replace(source, "need(grant['approved'] is True, 'NEW_OWNER_APPROVAL_REQUIRED_NO_LIVE_ACTION')",
                     "need(grant['approved'] is True, 'NEW_OWNER_APPROVAL_REQUIRED_NO_LIVE_ACTION')\n    need(type(grant['external_approval_reference']) is str and bool(grant['external_approval_reference'].strip()), 'SUPPORTED_EXTERNAL_PLATFORM_APPROVAL_REQUIRED')")
    return source


exec(compile(derived_source(), __file__ + ':R1-derived', 'exec'), globals())


def public_sources():
    """Exact public implementation, registration, tests and preserved reuse basis."""
    paths = [*sorted((PUBLIC_ROOT / 'src/memlife/r1_av').glob('*.py')),
             *sorted((PUBLIC_ROOT / 'src/memlife/r1').glob('*.py')),
             *sorted((PUBLIC_ROOT / 'manifests/r1-av').glob('*.json')),
             *sorted((PUBLIC_ROOT / 'tests/research').glob('test_r1_av*.py')),
             PUBLIC_ROOT / 'scripts/research/r1_av.py', QUALIFIED_PINS,
             PUBLIC_ROOT / 'manifests/r1-access-amendment-v1.json']
    return {str(p.relative_to(PUBLIC_ROOT)): sha(raw(p)) for p in paths}
