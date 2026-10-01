"""Exactly reviewed official metadata directory; never a current C/H basis.

This purpose-specific metadata admission allows an explicitly unknown effective
DATE only for an independently reviewed current-in-use entry. It does not alter
or reuse that exception in the shared normative release Gate.
"""
import copy
import re
import unicodedata
from datetime import date
from pathlib import Path

from canonical import content_hash
from field_profiles import ProfileContext, _selected_review_date_errors
from major_criteria import _chain, _safe_public, _text, HASH
from major_criteria_references import (read, _reference_url, _checked_date,
    DOCUMENT_FIELDS, SEARCH_FIELDS, REVIEW_FIELDS, IDENTIFIER, dependencies as source_dependencies)
from release_gate_core import gate_law, _review_binding

NAMESPACE = 'major-criteria-directory/v1'
DIRECTORY_FILE = 'data/major-criteria-directory.json'
SCHEMA = 'safety-major-criteria-directory-v1'
REVIEW_SCOPE = 'identity_dates_currentness_scope_official_links_only'
STATUS_LABELS = {'current': '现行有效', 'current_in_use': '现行使用中'}
NOTICE = '本目录仅提供官方文件题录和适用范围提示，未提供已审判定条款，不能独立用于现场重大隐患判定；目录主题并非互斥行业，也不表示全行业覆盖。'
FIELDS = {'schemaVersion', 'id', 'lawVersionId', 'officialLink', 'officialTextLink', 'directoryGroup',
          'requiredCompanionIds', 'supplementsReferenceId', 'legalNature', 'criterionKind',
          'scopeHint', 'scopeCaveat', 'referenceStatus', 'statusAsOf', 'effectiveDateNote'}


def _day(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _id(value):
    return isinstance(value, str) and bool(IDENTIFIER.fullmatch(value))


def _short(value, maximum, empty=False):
    return (isinstance(value, str) and len(value) <= maximum and (empty or bool(value)) and
            value == value.strip() and not any(unicodedata.category(ch) == 'Cc' for ch in value))


def validate_record(record):
    if not isinstance(record, dict) or set(record) != FIELDS:
        raise ValueError('DIRECTORY_RECORD_FIELDS')
    if type(record['schemaVersion']) is not int or record['schemaVersion'] != 1:
        raise ValueError('DIRECTORY_SCHEMA')
    if not all(_id(record[k]) for k in ('id', 'lawVersionId')):
        raise ValueError('DIRECTORY_ID')
    if not all(_reference_url(record[k]) for k in ('officialLink', 'officialTextLink')) or not _safe_public(record):
        raise ValueError('DIRECTORY_OFFICIAL_URL_OR_PRIVATE_TEXT')
    group = record['directoryGroup']
    if (not isinstance(group, dict) or set(group) != {'id', 'label', 'role'} or
            not _id(group['id']) or not _short(group['label'], 48) or group['role'] not in ('primary', 'supplement')):
        raise ValueError('DIRECTORY_GROUP')
    refs = record['requiredCompanionIds']
    parent = record['supplementsReferenceId']
    if (not isinstance(refs, list) or not all(_id(v) for v in refs) or len(set(refs)) != len(refs) or
            record['id'] in refs or (parent is not None and not _id(parent)) or parent == record['id'] or
            (group['role'] == 'primary' and parent is not None) or
            (group['role'] == 'supplement' and (parent is None or refs))):
        raise ValueError('DIRECTORY_COMPANION_REFERENCES')
    if (not _short(record['legalNature'], 100) or not _id(record['criterionKind']) or
            not _short(record['scopeHint'], 240) or not _short(record['scopeCaveat'], 240) or
            not _short(record['effectiveDateNote'], 180, empty=True) or
            record['referenceStatus'] not in STATUS_LABELS or _day(record['statusAsOf']) is None):
        raise ValueError('DIRECTORY_METADATA')


def load_records(knowledge):
    rows, versions = {}, set()
    for path in sorted((Path(knowledge) / NAMESPACE / 'records').glob('*.json')):
        row = read(path)
        validate_record(row)
        if path.stem != row['id'] or row['id'] in rows or row['lawVersionId'] in versions:
            raise ValueError('DIRECTORY_DUPLICATE_OR_FILENAME')
        rows[row['id']] = row
        versions.add(row['lawVersionId'])
    return rows


def relationships(records):
    """Every named group has one primary and exact reciprocal companions."""
    groups = {}
    for ident, row in records.items():
        group = row['directoryGroup']
        groups.setdefault(group['id'], []).append(row)
    for gid, rows in groups.items():
        primaries = [r for r in rows if r['directoryGroup']['role'] == 'primary']
        if len(primaries) != 1 or len({r['directoryGroup']['label'] for r in rows}) != 1:
            raise ValueError('DIRECTORY_GROUP_IDENTITY:' + gid)
        primary = primaries[0]
        expected = {r['id'] for r in rows if r['directoryGroup']['role'] == 'supplement'}
        if set(primary['requiredCompanionIds']) != expected or any(
                r['supplementsReferenceId'] != primary['id'] for r in rows if r['id'] != primary['id']):
            raise ValueError('DIRECTORY_COMPANION_GRAPH:' + gid)
    return groups


def dependencies(record, knowledge, publication, *, context=None):
    context = context if context is not None else ProfileContext(knowledge)
    deps = source_dependencies(record, knowledge, publication, context=context)
    companions = record['requiredCompanionIds'] + ([record['supplementsReferenceId']] if record['supplementsReferenceId'] else [])
    for ident in companions:
        path = Path(knowledge) / NAMESPACE / 'records' / (ident + '.json')
        other = read(path) if path.exists() else None
        deps['directory-records/' + ident] = other
        if other is not None:
            validate_record(other)
            # Bind the companion record and metadata chain, but not its directory
            # review: reciprocal reviews would otherwise have circular hashes.
            for key, value in source_dependencies(other, knowledge, publication, context=context).items():
                deps['companion/' + ident + '/' + key] = value
    return deps


def review_bindings(record, knowledge, publication):
    validate_record(record)
    return {'reviewedContentHash': content_hash(record),
            'dependencyFingerprint': content_hash(dependencies(record, knowledge, publication))}


def _metadata_errors(record, deps):
    vid = record['lawVersionId']
    lv = deps.get('law-versions/' + vid) or {}
    law = deps.get('laws/' + str(lv.get('lawId'))) or {}
    row, doc = deps['publication/law-index'], deps['publication/fulltext']
    if set(doc) != DOCUMENT_FIELDS or not _safe_public(doc):
        raise ValueError('DIRECTORY_FULLTEXT_METADATA_FIELDS')
    if deps['publication/fulltext-search'] != {k: doc[k] for k in SEARCH_FIELDS}:
        raise ValueError('DIRECTORY_FULLTEXT_SEARCH_METADATA')
    if (doc.get('textMode') != 'link_only' or doc.get('publicationPermission') != 'metadata_only' or
            doc.get('fullTextReviewed') is not False or doc.get('textPath', 'missing') is not None or
            doc.get('fullTextSha256') != ''):
        raise ValueError('DIRECTORY_PUBLICATION_RIGHTS')
    errors = []
    if any(value is None for value in deps.values()):
        errors.append('DIRECTORY_DEPENDENCY_MISSING')
    label = STATUS_LABELS[record['referenceStatus']]
    if (doc.get('lawId') != lv.get('lawId') or doc.get('officialUrl') != record['officialLink'] or
            lv.get('sourceUrl') != record['officialLink'] or row.get('sourceUrl') != record['officialLink'] or
            doc.get('effectiveDate') != lv.get('effectiveDate') or row.get('effectiveDate') != lv.get('effectiveDate') or
            row.get('documentNumber') != lv.get('documentNumber') or doc.get('version') != lv.get('versionKey') or
            doc.get('title') != row.get('name') or doc.get('status') != label or row.get('status') != label or
            not all(_short(v, 200) for v in (law.get('canonicalName'), law.get('issuer'), law.get('documentKind'),
                                           lv.get('versionKey'), lv.get('documentNumber'), doc.get('title')))):
        errors.append('DIRECTORY_METADATA_IDENTITY')
    evidence = [v for k, v in deps.items() if k.startswith('evidence/') and isinstance(v, dict)]
    for url in {record['officialLink'], record['officialTextLink']}:
        if not any(e.get('url') == url and e.get('tier') == 'authoritative-public' and
                   isinstance(e.get('snapshotSha256'), str) and HASH.fullmatch(e['snapshotSha256']) for e in evidence):
            errors.append('DIRECTORY_OFFICIAL_METADATA_EVIDENCE')
    return errors


def _admission_errors(record, deps, review, bindings, at):
    vid = record['lawVersionId']
    lv = deps.get('law-versions/' + vid) or {}
    law = deps.get('laws/' + str(lv.get('lawId'))) or {}
    law_review = deps.get('reviews/laws/' + str(lv.get('lawId')))
    lv_review = deps.get('reviews/law-versions/' + vid)
    errors = []
    if not gate_law(law, law_review)[0] or not _review_binding(lv, lv_review, need_evidence=True)[0]:
        errors.append('DIRECTORY_METADATA_REVIEW_GATE')
    if (lv.get('validityStatus') != 'active' or law.get('lifecycle', 'active') != 'active' or
            lv.get('lifecycle', 'active') != 'active'):
        errors.append('DIRECTORY_METADATA_NOT_ACTIVE')
    for key, value in deps.items():
        if key.startswith('reviews/') and (not isinstance(value, dict) or not _checked_date(value.get('checkedAt'))):
            errors.append('DIRECTORY_METADATA_REVIEW_DATE')
    errors += _selected_review_date_errors(deps, at)
    effective, end = lv.get('effectiveDate'), lv.get('endDate')
    if effective is None:
        if record['referenceStatus'] != 'current_in_use' or not record['effectiveDateNote']:
            errors.append('DIRECTORY_UNKNOWN_EFFECTIVE_DATE_UNEXPLAINED')
    elif _day(effective) is None or _day(effective) > at:
        errors.append('DIRECTORY_EFFECTIVE_DATE_INVALID_OR_FUTURE')
    if end not in (None, '') and (_day(end) is None or _day(end) <= at or
                                 (_day(effective) is not None and _day(end) <= _day(effective))):
        errors.append('DIRECTORY_EXPIRED_OR_INVALID_END')
    if _day(lv.get('publicationDate')) is None or _day(lv.get('publicationDate')) > at or _day(record['statusAsOf']) > at:
        errors.append('DIRECTORY_METADATA_DATE')
    if (not isinstance(review, dict) or set(review) != REVIEW_FIELDS or
            type(review.get('schemaVersion')) is not int or review.get('schemaVersion') != 1 or
            review.get('referenceId') != record['id'] or review.get('reviewScope') != REVIEW_SCOPE or
            review.get('fullQuotePublicationReady') is not False or not _checked_date(review.get('checkedAt')) or
            not all(_text(review.get(k)) for k in ('reviewer', 'reason'))):
        return errors + ['DIRECTORY_REVIEW_SCHEMA_OR_MISSING']
    if review['decision'] != 'verified':
        errors.append('DIRECTORY_REVIEW_NOT_VERIFIED')
    if any(review.get(k) != v for k, v in bindings.items()):
        errors.append('DIRECTORY_REVIEW_STALE')
    errors += _selected_review_date_errors({'reviews/directory': review}, at)
    if record['statusAsOf'] > review['checkedAt'][:10]:
        errors.append('DIRECTORY_CURRENTNESS_AFTER_REVIEW')
    return errors


def public_projection(knowledge, publication, *, as_of):
    if type(as_of) is not date:
        raise TypeError('as_of must be an explicit datetime.date')
    records = load_records(knowledge)
    groups = relationships(records)
    entries, excluded = {}, []
    context = ProfileContext(knowledge) if records else None
    for ident, record in records.items():
        deps = dependencies(record, knowledge, publication, context=context)
        review_path = Path(knowledge) / NAMESPACE / 'reviews' / (ident + '.json')
        review = read(review_path) if review_path.exists() else None
        errors = _metadata_errors(record, deps) + _admission_errors(
            record, deps, review, {'reviewedContentHash': content_hash(record), 'dependencyFingerprint': content_hash(deps)}, as_of)
        if errors:
            excluded.append({'referenceId': ident, 'reasons': sorted(set(errors))})
            continue
        lv = deps['law-versions/' + record['lawVersionId']]
        law = deps['laws/' + lv['lawId']]
        entry = {key: copy.deepcopy(record[key]) for key in sorted(FIELDS - {'schemaVersion'})}
        entry.update(lawId=lv['lawId'], title=deps['publication/fulltext']['title'], documentNumber=lv['documentNumber'],
                     versionKey=lv['versionKey'], issuer=law['issuer'], documentKind=law['documentKind'],
                     publicationDate=lv['publicationDate'], effectiveDate=lv.get('effectiveDate'),
                     statusLabel=STATUS_LABELS[record['referenceStatus']], checked=review['checkedAt'],
                     contentKind='official_document_reference_only', textMode='link_only', publicationPermission='metadata_only',
                     fullTextReviewed=False, fullQuotePublicationReady=False, publicationReady={'metadata': True, 'fullText': False},
                     reviewedClauseCount=0, directHazardCount=0, searchTopicCount=0,
                     standaloneDeterminationAllowed=False, wholeStandardComplete=False)
        if not _safe_public(entry):
            excluded.append({'referenceId': ident, 'reasons': ['DIRECTORY_PRIVATE_OUTPUT']})
            continue
        entries[ident] = entry
    public_groups = []
    for gid, rows in sorted(groups.items()):
        ids = sorted(r['id'] for r in rows)
        if not all(ident in entries for ident in ids):
            for ident in ids:
                entries.pop(ident, None)
            excluded.append({'directoryGroupId': gid, 'reasons': ['DIRECTORY_REQUIRED_GROUP_MEMBER_NOT_APPROVED']})
            continue
        primary = next(r for r in rows if r['directoryGroup']['role'] == 'primary')
        public_groups.append({'id': gid, 'label': primary['directoryGroup']['label'],
                              'primaryReferenceId': primary['id'], 'documentIds': ids})
    return {'public': {'schemaVersion': SCHEMA, 'asOf': as_of.isoformat(), 'catalogScope': 'controlled_official_metadata_directory',
                       'allIndustryCoverage': False, 'wholeNormNotFieldFinding': True, 'notice': NOTICE,
                       'directoryGroupCount': len(public_groups), 'documentCount': len(entries),
                       'directoryGroups': public_groups, 'entries': [entries[k] for k in sorted(entries)]},
            'inventory': {'excluded': excluded, 'controlledVersionIds': sorted(r['lawVersionId'] for r in records.values())}}


def project_publication(payload, projection):
    controlled = set(projection['inventory']['controlledVersionIds'])
    eligible = {e['lawVersionId'] for e in projection['public']['entries']}
    out = copy.deepcopy(payload)
    if controlled:
        out['asOf'] = projection['public']['asOf']
    out['documents'] = [d for d in out['documents'] if d.get('versionId') not in controlled or d['versionId'] in eligible]
    return out


def approved_status_overrides(knowledge, publication):
    """Only exact reviewed directory metadata can change source status labels.

    This is publication-source validation, not current normative eligibility.
    The explicit source catalog date is used; there is no implicit 'today'.
    """
    if not load_records(knowledge):
        return {}
    at = _day(read(Path(publication) / 'fulltext/catalog.json').get('asOf'))
    if at is None:
        raise ValueError('DIRECTORY_PUBLICATION_AS_OF')
    return {e['lawVersionId']: e['statusLabel'] for e in public_projection(knowledge, publication, as_of=at)['public']['entries']}
