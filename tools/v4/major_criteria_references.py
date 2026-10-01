"""Reviewed, link-only finding aids; never normative text or field findings.

Metadata/short-topic approval is distinct from C/LV normative approval. Exact
review bindings cover the record, its complete metadata chain, and publication
source rows. No H/K/C is created, selected, inferred or required by this module.
"""
import copy
import json
import re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit

from canonical import content_hash
from field_profiles import ProfileContext, _selected_review_date_errors, _selected_version_date_errors
from major_criteria import _chain, _official_url, _safe_public, _text, HASH
from release_gate_core import evaluate_release_gate

NAMESPACE = 'major-criteria-references/v1'
REFERENCE_FILE = 'data/major-criteria-references.json'
SCHEMA = 'safety-major-criteria-references-v1'
REVIEW_SCOPE = 'identity_dates_official_links_short_search_topics_only'
NOTICE = '这些短主题仅帮助定位条款，不是法条原文，也不能独立用于重大事故隐患判定；请查官方原件。'
DOCUMENT_FIELDS = {'lawId', 'versionId', 'title', 'version', 'officialUrl', 'effectiveDate', 'status',
                   'textMode', 'fullTextSha256', 'textPath', 'fullTextReviewed', 'publicationPermission', 'validityNote'}
SEARCH_FIELDS = {'lawId', 'versionId', 'title', 'version', 'textMode', 'textPath'}
RECORD_FIELDS = {'schemaVersion', 'id', 'lawVersionId', 'contentKind', 'officialLink', 'officialTextLink', 'searchTopics'}
REVIEW_FIELDS = {'schemaVersion', 'referenceId', 'decision', 'reviewedContentHash', 'dependencyFingerprint',
                 'checkedAt', 'reviewScope', 'fullQuotePublicationReady', 'reviewer', 'reason'}
TOPIC = re.compile(r'^[\u3400-\u9fffA-Za-z0-9 ]{1,16}$')
ARTICLE = re.compile(r'^[1-9]\d*(?:\.(?:0|[1-9]\d*))*$')
IDENTIFIER = re.compile(r'^[A-Za-z0-9_]+$')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _reference_url(value):
    if not _official_url(value) or '\\' in value or re.search(r'%(?:0[0-9a-f]|1[0-9a-f]|7f)', value, re.I):
        return False
    try:
        url = urlsplit(value)
        return not url.port and bool(re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+gov\.cn', url.hostname, re.I))
    except ValueError:
        return False


def _checked_date(value):
    if not isinstance(value, str):
        return False
    try:
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            date.fromisoformat(value)
        elif re.fullmatch(r'\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)', value):
            datetime.fromisoformat(value)
        else:
            return False
        return True
    except ValueError:
        return False


def validate_record(record):
    if not isinstance(record, dict) or set(record) != RECORD_FIELDS:
        raise ValueError('REFERENCE_RECORD_FIELDS')
    if type(record['schemaVersion']) is not int or record['schemaVersion'] != 1 or record['contentKind'] != 'reference_only':
        raise ValueError('REFERENCE_RECORD_KIND')
    if not all(isinstance(record[k], str) and IDENTIFIER.fullmatch(record[k]) for k in ('id', 'lawVersionId')):
        raise ValueError('REFERENCE_ID')
    if not all(_reference_url(record[k]) for k in ('officialLink', 'officialTextLink')) or not _safe_public(record):
        raise ValueError('REFERENCE_OFFICIAL_URL_OR_PRIVATE_TEXT')
    topics = record['searchTopics']
    if not isinstance(topics, list):
        raise ValueError('REFERENCE_TOPICS')
    seen = set()
    for topic in topics:
        if (not isinstance(topic, dict) or set(topic) != {'article', 'searchTopic'} or
                not isinstance(topic['article'], str) or not ARTICLE.fullmatch(topic['article']) or
                topic['article'] in seen or not isinstance(topic['searchTopic'], str) or
                not TOPIC.fullmatch(topic['searchTopic']) or not topic['searchTopic'].strip() or
                topic['searchTopic'] != topic['searchTopic'].strip()):
            raise ValueError('REFERENCE_SHORT_TOPIC')
        seen.add(topic['article'])


def load_records(knowledge):
    records, versions = {}, set()
    for path in sorted((Path(knowledge) / NAMESPACE / 'records').glob('*.json')):
        record = read(path)
        validate_record(record)
        ident, vid = record['id'], record['lawVersionId']
        if path.stem != ident or ident in records or vid in versions:
            raise ValueError('REFERENCE_DUPLICATE_OR_FILENAME')
        records[ident] = record
        versions.add(vid)
    return records


def _single(rows, field, ident):
    if not isinstance(rows, list):
        raise ValueError('REFERENCE_PUBLICATION_LIST')
    matches = [r for r in rows if isinstance(r, dict) and r.get(field) == ident]
    if len(matches) != 1:
        raise ValueError('REFERENCE_PUBLICATION_IDENTITY:' + str(ident))
    return matches[0]


def dependencies(record, knowledge, publication, *, context=None):
    """Private binding material. Never serialize this into a public payload."""
    context = context if context is not None else ProfileContext(knowledge)
    deps = _chain(context, 'law-versions', record['lawVersionId'])
    pub = Path(publication)
    deps['publication/law-index'] = _single(read(pub / 'law-index.json'), 'id', record['lawVersionId'])
    deps['publication/fulltext'] = _single(read(pub / 'fulltext/catalog.json')['documents'], 'versionId', record['lawVersionId'])
    deps['publication/fulltext-search'] = _single(read(pub / 'fulltext/search-index.json')['documents'], 'versionId', record['lawVersionId'])
    return deps


def review_bindings(record, knowledge, publication):
    """Compute pins only. This is not an approval or a review-writing API."""
    validate_record(record)
    return {'reviewedContentHash': content_hash(record),
            'dependencyFingerprint': content_hash(dependencies(record, knowledge, publication))}


def _metadata_errors(record, deps):
    vid = record['lawVersionId']
    lv = deps.get('law-versions/' + vid) or {}
    law = deps.get('laws/' + str(lv.get('lawId'))) or {}
    row, doc = deps['publication/law-index'], deps['publication/fulltext']
    errors = []
    if set(doc) != DOCUMENT_FIELDS or not _safe_public(doc):
        raise ValueError('REFERENCE_FULLTEXT_METADATA_FIELDS')
    if deps['publication/fulltext-search'] != {k: doc[k] for k in SEARCH_FIELDS}:
        raise ValueError('REFERENCE_FULLTEXT_SEARCH_METADATA')
    if any(value is None for value in deps.values()):
        errors.append('REFERENCE_DEPENDENCY_MISSING')
    if (doc.get('lawId') != lv.get('lawId') or doc.get('officialUrl') != record['officialLink'] or
            lv.get('sourceUrl') != record['officialLink'] or row.get('sourceUrl') != record['officialLink'] or
            doc.get('effectiveDate') != lv.get('effectiveDate') or row.get('effectiveDate') != lv.get('effectiveDate') or
            row.get('documentNumber') != lv.get('documentNumber') or
            doc.get('version') != lv.get('versionKey') or doc.get('title') != row.get('name') or
            doc.get('status') != row.get('status') or
            doc.get('status') != {'active': '现行有效', 'upcoming': '即将生效', 'repealed': '已废止', 'unknown': '待核验'}.get(lv.get('validityStatus')) or
            not all(_text(v) for v in (law.get('canonicalName'), law.get('issuer'), lv.get('versionKey'),
                                     lv.get('documentNumber'), doc.get('title')))):
        errors.append('REFERENCE_METADATA_IDENTITY')
    if (doc.get('textMode') != 'link_only' or doc.get('publicationPermission') != 'metadata_only' or
            doc.get('fullTextReviewed') is not False or doc.get('textPath', 'missing') is not None or
            doc.get('fullTextSha256') != ''):
        # An excluded reference must not leak raw text through the legacy fulltext copy.
        raise ValueError('REFERENCE_PUBLICATION_RIGHTS')
    evidence = [value for key, value in deps.items() if key.startswith('evidence/') and isinstance(value, dict)]
    if not any(e.get('url') == record['officialTextLink'] and e.get('tier') == 'authoritative-public' and
               isinstance(e.get('snapshotSha256'), str) and HASH.fullmatch(e['snapshotSha256']) for e in evidence):
        errors.append('REFERENCE_OFFICIAL_TEXT_EVIDENCE')
    return errors


def _review_errors(record, review, bindings, at):
    if (not isinstance(review, dict) or set(review) != REVIEW_FIELDS or
            type(review.get('schemaVersion')) is not int or review.get('schemaVersion') != 1 or
            review.get('referenceId') != record['id'] or review.get('reviewScope') != REVIEW_SCOPE or
            review.get('fullQuotePublicationReady') is not False or not _checked_date(review.get('checkedAt')) or
            not all(_text(review.get(k)) for k in ('reviewer', 'reason', 'checkedAt'))):
        return ['REFERENCE_REVIEW_SCHEMA_OR_MISSING']
    errors = []
    if review['decision'] != 'verified':
        errors.append('REFERENCE_REVIEW_NOT_VERIFIED')
    for key, value in bindings.items():
        if review.get(key) != value:
            errors.append('REFERENCE_REVIEW_STALE:' + key)
    errors += _selected_review_date_errors({'reviews/reference': review}, at)
    return errors


def public_projection(knowledge, publication, *, as_of):
    if type(as_of) is not date:
        raise TypeError('as_of must be an explicit datetime.date')
    records = load_records(knowledge)
    context = ProfileContext(knowledge)
    gate = evaluate_release_gate(knowledge, as_of)
    entries, excluded = [], []
    for ident, record in records.items():
        deps = dependencies(record, knowledge, publication)
        errors = _metadata_errors(record, deps)
        vid = record['lawVersionId']
        lv = context.entities['law-versions'].get(vid, {})
        law = context.entities['laws'].get(lv.get('lawId'), {})
        if not gate.law_versions.get(vid, {}).get('ok') or not gate.law_versions.get(vid, {}).get('supports_current'):
            errors.append('REFERENCE_CURRENT_METADATA_GATE')
        errors += _selected_version_date_errors(lv)
        errors += _selected_review_date_errors(deps, as_of)
        if any(not isinstance(value, dict) or not _text(value.get('checkedAt'))
               for key, value in deps.items() if key.startswith('reviews/')):
            errors.append('REFERENCE_METADATA_REVIEW_DATE_REQUIRED')
        review_path = Path(knowledge) / NAMESPACE / 'reviews' / (ident + '.json')
        review = read(review_path) if review_path.exists() else None
        errors += _review_errors(record, review, review_bindings(record, knowledge, publication), as_of)
        if errors:
            excluded.append({'referenceId': ident, 'lawVersionId': vid, 'reasons': sorted(set(errors))})
            continue
        entry = {'id': ident, 'lawId': lv['lawId'], 'lawVersionId': vid,
                 'title': deps['publication/fulltext']['title'], 'standardNumber': lv['documentNumber'],
                 'versionKey': lv['versionKey'], 'issuer': law['issuer'], 'effectiveDate': lv['effectiveDate'],
                 'validityStatus': lv['validityStatus'], 'checked': review['checkedAt'],
                 'officialLink': record['officialLink'], 'officialTextLink': record['officialTextLink'],
                 'contentKind': 'reference_only', 'textMode': 'link_only', 'publicationPermission': 'metadata_only',
                 'fullTextReviewed': False, 'fullQuotePublicationReady': False,
                 'publicationReady': {'metadata': True, 'searchTopics': True, 'fullText': False},
                 'reviewedClauseCount': 0, 'directHazardCount': 0, 'standaloneDeterminationAllowed': False,
                 'wholeStandardComplete': False, 'searchTopicCount': len(record['searchTopics']),
                 'searchTopics': [{**topic, 'contentKind': 'search_topic_only', 'isOfficialQuote': False,
                                   'standaloneDeterminationAllowed': False} for topic in record['searchTopics']]}
        if not _safe_public(entry):
            excluded.append({'referenceId': ident, 'lawVersionId': vid, 'reasons': ['REFERENCE_PRIVATE_OUTPUT']})
            continue
        entries.append(entry)
    return {'public': {'schemaVersion': SCHEMA, 'asOf': as_of.isoformat(),
                       'catalogScope': 'official_reference_entries_only', 'allIndustryCoverage': False,
                       'wholeNormNotFieldFinding': True, 'notice': NOTICE, 'referenceEntries': entries},
            'inventory': {'excluded': excluded, 'controlledVersionIds': sorted(r['lawVersionId'] for r in records.values())}}


def project_publication(payload, projection):
    """Filter only controlled link-only entries by their actual dated approval.

    Legacy documents are unchanged. Link-only records never have gram postings
    or text files, so only the two metadata documents[] lists need projection.
    """
    controlled = set(projection['inventory']['controlledVersionIds'])
    eligible = {e['lawVersionId'] for e in projection['public']['referenceEntries']}
    out = copy.deepcopy(payload)
    if controlled:
        out['asOf'] = projection['public']['asOf']
    out['documents'] = [d for d in out['documents'] if d.get('versionId') not in controlled or d['versionId'] in eligible]
    return out
