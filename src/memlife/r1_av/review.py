"""Offline exact-package review binding; never an authorization issuer."""
from .protocol import canonical, identity, need, raw, strict


def verify_review(package, path):
    from . import contract
    review = strict(raw(path))
    need(review['schema'] == 'MEMLIFE_R1_AV_INDEPENDENT_OFFLINE_REVIEW_V1'
         and review['accepted'] is True and review['independent_review'] is True
         and review.get('synthetic', False) is False and review.get('test_scope', False) is False
         and type(review.get('reviewer')) is str and review['reviewer'].strip(), 'INDEPENDENT_REVIEW_REQUIRED')
    for key in ('public_sources', 'accepted_sources', 'effective_sources', 'access_amendment'):
        need(canonical(review[key]) == canonical(package[key]), 'EXACT_PACKAGE_REVIEW_DRIFT:' + key)
    need(review['package'] == identity(contract.PACKAGE), 'EXACT_REVIEW_PACKAGE')
    # Genuine separate reviewer provenance must also exist outside this schema.
    return dict(status='EXACT_PACKAGE_REVIEW_BYTES_VERIFIED_NO_OWNER_OR_PLATFORM_AUTHORITY',
                review=identity(path), accepted=True, execution_authorized=False)
