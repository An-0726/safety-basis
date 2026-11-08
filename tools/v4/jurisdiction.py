"""Deterministic jurisdiction containment for already reviewed source chains.

Only structured jurisdiction codes take part. In particular, a title, clause
quote, H.conditions, applicability prose and free-form version scope cannot
supply or widen a jurisdiction. The existing legacy metadata value 全国 is
normalized to CN; arbitrary natural-language scope is never parsed.
"""
import re


REGION_LABELS = {'CN': '全国', 'CN-32': '江苏', 'CN-3201': '南京'}
CODE = re.compile(r'CN(?:-[0-9]{2}(?:[0-9]{2}){0,2})?\Z')
QUALIFYING_ROLES = {'direct', 'fallback'}


class JurisdictionError(ValueError):
    def __init__(self, code, context):
        self.code = code
        super().__init__(code + ':' + context)


def jurisdiction_code(value, *, context='jurisdictionCode', required=False):
    """Normalize a metadata code; absent is unknown, never an implicit CN."""
    if value is None or value == '':
        if required:
            raise JurisdictionError('JURISDICTION_MISSING', context)
        return None
    if not isinstance(value, str):
        raise JurisdictionError('JURISDICTION_INVALID', context)
    code = value.strip()
    if code == '全国':  # Existing release Gate's explicit national-code alias.
        return 'CN'
    if not CODE.fullmatch(code):
        raise JurisdictionError('JURISDICTION_INVALID', context)
    return code


def version_scope_code(value):
    """Use a whole normalized code only; ignore free-form statutory scope."""
    if value is None or value == '':
        return None
    if not isinstance(value, str):
        raise JurisdictionError('JURISDICTION_INVALID', 'lawVersion.scope')
    code = value.strip()
    return code if CODE.fullmatch(code) else None


def intersect_jurisdictions(*codes, context='source chain'):
    """Return the narrowest compatible ancestor/descendant, or reject conflict.

    CN contains all coded regions. Within China the normalized two/four/six
    digit administrative hierarchy supplies containment; different local
    branches have no intersection and must not fall back to a national label.
    """
    result = None
    for value in codes:
        code = jurisdiction_code(value, context=context)
        if code is None:
            continue
        if result is None or result == 'CN' or code.startswith(result):
            result = code
        elif code != 'CN' and not result.startswith(code):
            raise JurisdictionError('JURISDICTION_CONFLICT', context)
    return result


def version_jurisdiction(version, law):
    return intersect_jurisdictions(
        jurisdiction_code(law.get('jurisdictionCode'),
                          context='law/' + str(law.get('id', '')), required=True),
        version_scope_code(version.get('scope')),
        context='lawVersion/' + str(version.get('id', '')),
    )


def clause_jurisdiction(clause, version, law):
    return intersect_jurisdictions(
        version_jurisdiction(version, law),
        jurisdiction_code(clause.get('jurisdictionCode'),
                          context='clause/' + str(clause.get('id', ''))),
        context='clause/' + str(clause.get('id', '')),
    )


def basis_jurisdiction(link, clause, version, law):
    return intersect_jurisdictions(
        clause_jurisdiction(clause, version, law),
        jurisdiction_code(link.get('jurisdictionCode'),
                          context='link/' + str(link.get('id', ''))),
        context='link/' + str(link.get('id', '')),
    )


def region_label(code):
    code = jurisdiction_code(code, required=True)
    # An unfamiliar but valid local code stays explicit; never call it 全国.
    return REGION_LABELS.get(code, code)


def candidate_scopes(basis_refs):
    """Only an independently qualifying basis may supply a candidate region."""
    return sorted({region_label(ref.get('jurisdictionCode')) for ref in basis_refs
                   if ref.get('role') in QUALIFYING_ROLES})
