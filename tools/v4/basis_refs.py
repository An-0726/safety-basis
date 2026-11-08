"""Allowlisted per-link legal scope for ordinary hazard detail/copy consumers.

Applicability stays verbatim. The effective jurisdiction is the reviewed
K/C/version/law intersection, never inferred from prose or another K.
"""
from field_profiles import PRIVATE
from jurisdiction import basis_jurisdiction

ROLE_ORDER = {'direct': 0, 'fallback': 1, 'supporting': 2}


def basis_sort_key(link):
    return (ROLE_ORDER.get(link.get('role'), 9), link.get('clauseId', ''),
            link.get('role', ''), link.get('id', ''))


def project_basis_reference(link, clause_shard, *, clause, version, law):
    """Serialize one current Gate-approved K; caller owns H/C/Gate selection.

    Unsafe or malformed newly exposed text aborts instead of leaking, silently
    coercing values or widening/dropping a legal boundary.
    """
    for key in ('id', 'clauseId', 'applicability'):
        value = link.get(key)
        if not isinstance(value, str) or not value.strip() or PRIVATE.search(value):
            raise ValueError('BASIS_PUBLIC_FIELD_UNSAFE:' + key)
    raw_jurisdiction = link.get('jurisdictionCode')
    if raw_jurisdiction is not None and (not isinstance(raw_jurisdiction, str) or PRIVATE.search(raw_jurisdiction)):
        raise ValueError('BASIS_PUBLIC_FIELD_UNSAFE:jurisdictionCode')
    if link.get('role') not in ROLE_ORDER:
        raise ValueError('BASIS_PUBLIC_ROLE')
    if not isinstance(clause_shard, str) or not clause_shard:
        raise ValueError('BASIS_CLAUSE_SHARD')
    jurisdiction = basis_jurisdiction(link, clause, version, law)
    return {'linkId': link['id'], 'clauseId': link['clauseId'],
            'clauseShard': clause_shard, 'role': link['role'],
            'applicability': link['applicability'], 'jurisdictionCode': jurisdiction}
