"""Controlled major-criteria catalog and exact direct-basis topic.

This read-only projection never approves source reviews or creates hazards. Catalog
clauses need not have an H/K edge. Both projections retain the original chained
Gate, explicit source pins and strict date/evidence/privacy checks.
"""
import copy
import json
import re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit

from canonical import content_hash
from field_profiles import (PRIVATE, ProfileContext, _selected_review_date_errors,
                            _selected_version_date_errors)
from release_gate_core import evaluate_release_gate
from normative_content import validate_clause_content

CONFIG_PATH = 'major-criteria/v1/catalog.json'
CATALOG_FILE = 'data/major-criteria-catalog.json'
TOPIC_FILE = 'data/major-criteria-topic.json'
HASH = re.compile(r'^[a-f0-9]{64}$')
SCOPE_REVIEW = 'official_administrative_document_text_completeness_and_publication'
RICH_SCOPE_REVIEW = 'official_administrative_document_text_tables_applicability_and_publication'
PUBLICATION_BASIS = 'copyright_law_article_5_official_administrative_document'


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _official_url(value):
    if not _text(value) or any(char.isspace() or ord(char) < 32 for char in value):
        return False
    url = urlsplit(value)
    return (url.scheme == 'https' and not url.username and not url.password and
            bool(url.hostname) and url.hostname.endswith('.gov.cn'))


def _safe_public(value):
    if isinstance(value, dict):
        return all(_safe_public(v) for v in value.values())
    if isinstance(value, list):
        return all(_safe_public(v) for v in value)
    if isinstance(value, str):
        return (_official_url(value) and not PRIVATE.search(value[len('https://'):])) if value.startswith('https://') else not PRIVATE.search(value)
    return True


def _count(value):
    return value is None or (type(value) is int and value >= 0)


def load_config(knowledge):
    path = Path(knowledge) / CONFIG_PATH
    config = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'schemaVersion': 1, 'standards': []}
    if not isinstance(config, dict) or set(config) != {'schemaVersion', 'standards'} or type(config['schemaVersion']) is not int or config['schemaVersion'] != 1 or not isinstance(config['standards'], list):
        raise ValueError('MAJOR_CONFIG_SCHEMA')
    seen, seen_tables = set(), set()
    for standard in config['standards']:
        fields = {'lawVersionId', 'identity', 'lawContentHash', 'versionContentHash',
                  'officialScope', 'scopeVerified', 'expectedJudgmentItemCount', 'clauses', 'topicLinks', 'pendingTopicLinks'}
        if not isinstance(standard, dict) or not fields <= set(standard) <= fields | {'publication', 'applicationNotes'}:
            raise ValueError('MAJOR_STANDARD_FIELDS')
        vid = standard['lawVersionId']
        identity, scope = standard['identity'], standard['officialScope']
        if not _text(vid) or vid in seen:
            raise ValueError('MAJOR_STANDARD_ID')
        seen.add(vid)
        if (not isinstance(identity, dict) or set(identity) != {'lawId', 'name', 'documentNumber', 'versionKey', 'officialSourceUrl'} or
                not all(_text(value) for value in identity.values()) or not _official_url(identity['officialSourceUrl'])):
            raise ValueError('MAJOR_STANDARD_IDENTITY')
        if (not isinstance(scope, dict) or set(scope) != {'label', 'sourceUrls', 'wholeStandardComplete'} or
                not _text(scope['label']) or not isinstance(scope['sourceUrls'], list) or not scope['sourceUrls'] or
                not all(_official_url(url) for url in scope['sourceUrls']) or type(scope['wholeStandardComplete']) is not bool):
            raise ValueError('MAJOR_SCOPE')
        publication = standard.get('publication')
        if publication is not None:
            if (not isinstance(publication, dict) or set(publication) != {'basis', 'legalSourceUrl', 'evidenceIds'} or
                    publication['basis'] != PUBLICATION_BASIS or not _official_url(publication['legalSourceUrl']) or
                    not isinstance(publication['evidenceIds'], list) or not publication['evidenceIds'] or
                    not all(isinstance(eid, str) and re.fullmatch(r'[A-Za-z0-9_]+', eid) for eid in publication['evidenceIds']) or
                    len(set(publication['evidenceIds'])) != len(publication['evidenceIds'])):
                raise ValueError('MAJOR_PUBLICATION_BASIS')
        if scope['wholeStandardComplete'] and (publication is None or standard['scopeVerified'] is not True):
            raise ValueError('MAJOR_WHOLE_SCOPE_REVIEW_REQUIRED')
        if type(standard['scopeVerified']) is not bool or not _count(standard['expectedJudgmentItemCount']):
            raise ValueError('MAJOR_COVERAGE')
        if not all(isinstance(standard[key], str) and HASH.fullmatch(standard[key]) for key in ('lawContentHash', 'versionContentHash')):
            raise ValueError('MAJOR_SOURCE_PIN')
        if not isinstance(standard['clauses'], list) or not standard['clauses'] or not isinstance(standard['topicLinks'], list) or not isinstance(standard['pendingTopicLinks'], list):
            raise ValueError('MAJOR_CONTROLLED_REFERENCES')
        for key, fields, ident in (
                ('clauses', {'clauseId', 'contentHash', 'granularity', 'judgmentItemCount'}, 'clauseId'),
                ('topicLinks', {'linkId', 'hazardId', 'clauseId', 'dependencyFingerprint'}, 'linkId')):
            ids = set()
            for row in standard[key]:
                allowed = fields | ({'tableIds'} if key == 'clauses' else set())
                if not isinstance(row, dict) or not fields <= set(row) <= allowed or not _text(row.get(ident)) or row[ident] in ids:
                    raise ValueError('MAJOR_CONTROLLED_REFERENCE:' + key)
                ids.add(row[ident])
                pin = row['contentHash'] if key == 'clauses' else row['dependencyFingerprint']
                if not isinstance(pin, str) or not HASH.fullmatch(pin):
                    raise ValueError('MAJOR_SOURCE_PIN')
                if key == 'clauses' and (row['granularity'] not in ('whole_clause', 'subitem') or not _count(row['judgmentItemCount'])):
                    raise ValueError('MAJOR_CLAUSE_GRANULARITY')
                if key == 'clauses' and 'tableIds' in row:
                    tables = row['tableIds']
                    if (publication is None or row['granularity'] != 'whole_clause' or not isinstance(tables, list) or
                            not tables or not all(isinstance(t, str) and re.fullmatch(r'[A-Za-z0-9_]+', t) for t in tables) or
                            len(set(tables)) != len(tables) or seen_tables.intersection(tables)):
                        raise ValueError('MAJOR_CONTROLLED_TABLES')
                    seen_tables.update(tables)
                if key == 'topicLinks' and not all(_text(row[k]) for k in ('hazardId', 'clauseId')):
                    raise ValueError('MAJOR_TOPIC_REFERENCE')
        pending_ids = set()
        active_ids = {row['linkId'] for row in standard['topicLinks']}
        for row in standard['pendingTopicLinks']:
            if (not isinstance(row, dict) or set(row) != {'linkId', 'hazardId', 'clauseId'} or
                    not all(_text(v) for v in row.values()) or row['linkId'] in pending_ids | active_ids):
                raise ValueError('MAJOR_PENDING_REFERENCE')
            pending_ids.add(row['linkId'])
        expected = standard['expectedJudgmentItemCount']
        numbers = [row['judgmentItemCount'] for row in standard['clauses']]
        if expected is not None and (not standard['scopeVerified'] or None in numbers or sum(numbers) != expected):
            raise ValueError('MAJOR_JUDGMENT_COUNT_UNSUPPORTED')
        if not _safe_public({key: standard[key] for key in ('identity', 'officialScope')}):
            raise ValueError('MAJOR_PRIVATE_TEXT')
        notes = standard.get('applicationNotes', [])
        if not isinstance(notes, list) or ('applicationNotes' in standard and (not notes or publication is None)):
            raise ValueError('MAJOR_APPLICATION_NOTES')
        selected_ids, note_keys = {r['clauseId'] for r in standard['clauses']}, set()
        for note in notes:
            if (not isinstance(note, dict) or set(note) != {'clauseId', 'summary', 'sourceUrl', 'sourceDate', 'evidenceId'} or
                    not all(_text(v) for v in note.values()) or note['clauseId'] not in selected_ids or
                    not _official_url(note['sourceUrl']) or not re.fullmatch(r'[A-Za-z0-9_]+', note['evidenceId']) or
                    len(note['summary']) > 1000 or not _safe_public(note)):
                raise ValueError('MAJOR_APPLICATION_NOTE_FIELDS')
            try:
                if date.fromisoformat(note['sourceDate']).isoformat() != note['sourceDate']:
                    raise ValueError()
            except (ValueError, TypeError):
                raise ValueError('MAJOR_APPLICATION_NOTE_DATE')
            key = (note['clauseId'], note['sourceUrl'])
            if key in note_keys:
                raise ValueError('MAJOR_APPLICATION_NOTE_DUPLICATE')
            note_keys.add(key)
    return config


def _chain(context, kind, ident):
    """Read exact selected C/LV/LF, reviews and evidence; no fabricated H needed."""
    result = {}
    def visit(namespace, key):
        label = namespace + '/' + str(key)
        if label in result:
            return
        obj = context.entities[namespace].get(key)
        result[label] = obj
        if namespace == 'evidence':
            return
        review = context.reviews[namespace].get(key)
        result['reviews/' + label] = review
        for source in (obj, review):
            if not source:
                continue
            refs = source.get('evidenceRefs', [])
            if not isinstance(refs, list):
                raise ValueError('MAJOR_EVIDENCE_REFERENCES')
            for ref in refs:
                eid = ref if isinstance(ref, str) else ref.get('evidenceId') or ref.get('id') if isinstance(ref, dict) else None
                if not _text(eid):
                    raise ValueError('MAJOR_EVIDENCE_IDENTITY')
                visit('evidence', eid)
        if obj and namespace == 'clauses':
            visit('law-versions', obj.get('lawVersionId'))
        elif obj and namespace == 'law-versions':
            visit('laws', obj.get('lawId'))
    visit(kind, ident)
    return result


def _dependencies_ok(deps, at):
    return not any(value is None for value in deps.values()) and not _selected_review_date_errors(deps, at)


def _checked(review):
    # Preserve a supplied review date; no made-up legacy fallback date.
    return str(review.get('checkedAt') or review.get('reviewedAt') or review.get('reviewedOn') or '')


def scope_review_bindings(definition, knowledge, *, context=None):
    """Read-only hashes for independent review; never creates an approval."""
    context = context or ProfileContext(knowledge)
    deps = _chain(context, 'law-versions', definition['lawVersionId'])
    for selected in definition['clauses']:
        deps.update(_chain(context, 'clauses', selected['clauseId']))
    for eid in definition.get('publication', {}).get('evidenceIds', []):
        deps['evidence/' + eid] = context.entities['evidence'].get(eid)
    for note in definition.get('applicationNotes', []):
        eid = note['evidenceId']
        deps['evidence/' + eid] = context.entities['evidence'].get(eid)
    return {'reviewedContentHash': content_hash(definition), 'dependencyFingerprint': content_hash(deps)}, deps


def required_scope_review(definition):
    return (RICH_SCOPE_REVIEW if definition.get('applicationNotes') or any(r.get('tableIds') for r in definition['clauses'])
            else SCOPE_REVIEW)


def _scope_publication(definition, context, at):
    """Metadata approval cannot silently become permission for normative text.

    Existing reviewed selections keep their original contract. A selection with
    a metadata-only LF/LV review, or a complete-body claim, requires this explicit
    independently reviewed publication scope. The review binds every C and its
    review atomically, so incomplete text can never retain a complete-body claim.
    """
    publication = definition.get('publication')
    version = context.entities['law-versions'].get(definition['lawVersionId'], {})
    metadata_only = any(context.reviews[kind].get(ident, {}).get('fullQuotePublicationReady') is False
                        for kind, ident in [('law-versions', definition['lawVersionId']),
                                            ('laws', version.get('lawId'))])
    if publication is None:
        return (not metadata_only), None
    path = context.root / 'major-criteria/v1/reviews' / (definition['lawVersionId'] + '.json')
    review = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None
    fields = {'schemaVersion', 'lawVersionId', 'decision', 'reviewedContentHash', 'dependencyFingerprint',
              'checkedAt', 'reviewScope', 'fullQuotePublicationReady', 'reviewer', 'reason'}
    if (not isinstance(review, dict) or set(review) != fields or type(review.get('schemaVersion')) is not int or
            review['schemaVersion'] != 1 or review.get('lawVersionId') != definition['lawVersionId'] or
            review.get('decision') != 'verified' or review.get('reviewScope') != required_scope_review(definition) or
            review.get('fullQuotePublicationReady') is not True or
            not all(_text(review.get(key)) for key in ('checkedAt', 'reviewer', 'reason'))):
        return False, None
    try:
        checked = review['checkedAt']
        if len(checked) == 10:
            checked_date = date.fromisoformat(checked)
        else:
            parsed = datetime.fromisoformat(checked.replace('Z', '+00:00'))
            if parsed.tzinfo is None:
                return False, None
            checked_date = parsed.date()
        if checked_date > at:
            return False, None
    except (ValueError, TypeError):
        return False, None
    bindings, deps = scope_review_bindings(definition, context.root, context=context)
    if (any(review.get(key) != value for key, value in bindings.items()) or
            not _dependencies_ok(deps, at) or
            not any(context.entities['evidence'].get(eid, {}).get('url') == publication['legalSourceUrl']
                    for eid in publication['evidenceIds'])):
        return False, None
    for eid in publication['evidenceIds']:
        evidence = context.entities['evidence'].get(eid, {})
        if (evidence.get('tier') != 'authoritative-public' or not _official_url(evidence.get('url')) or
                not HASH.fullmatch(str(evidence.get('snapshotSha256', ''))) or not _text(evidence.get('locator'))):
            return False, None
    result = {'basis': publication['basis'], 'legalSourceUrl': publication['legalSourceUrl'],
              'checked': checked, 'fullTextPublicationApproved': True}
    return _safe_public(result), result


def _public_application_notes(definition, context, at, publication):
    result = {}
    for note in definition.get('applicationNotes', []):
        evidence = context.entities['evidence'].get(note['evidenceId'], {})
        if (publication is None or note['sourceDate'] > at.isoformat() or
                note['sourceDate'] > publication['checked'][:10] or evidence.get('url') != note['sourceUrl'] or
                evidence.get('tier') != 'authoritative-public' or not HASH.fullmatch(str(evidence.get('snapshotSha256', ''))) or
                not _text(evidence.get('locator'))):
            return None
        result.setdefault(note['clauseId'], []).append({
            'kind': 'official_application_clarification', 'isOfficialNormText': False,
            'summary': note['summary'], 'sourceUrl': note['sourceUrl'], 'sourceDate': note['sourceDate'],
            'checked': publication['checked']})
    return result


def public_projection(knowledge, *, as_of):
    if type(as_of) is not date:
        raise TypeError('as_of must be an explicit datetime.date')
    config, context = load_config(knowledge), ProfileContext(knowledge)
    gate = evaluate_release_gate(knowledge, as_of)
    standards, associations, excluded = [], [], []
    pending = {row['linkId']: row['hazardId'] for d in config['standards'] for row in d['pendingTopicLinks']}
    for definition in config['standards']:
        vid, identity = definition['lawVersionId'], definition['identity']
        lv = context.entities['law-versions'].get(vid, {})
        law = context.entities['laws'].get(identity['lawId'], {})
        actual_identity = {'lawId': lv.get('lawId'), 'name': law.get('canonicalName'),
                           'documentNumber': lv.get('documentNumber'), 'versionKey': lv.get('versionKey'),
                           'officialSourceUrl': lv.get('sourceUrl')}
        if (actual_identity != identity or content_hash(lv) != definition['versionContentHash'] or
                content_hash(law) != definition['lawContentHash'] or
                not gate.law_versions.get(vid, {}).get('supports_current') or
                not gate.law_versions.get(vid, {}).get('ok') or
                _selected_version_date_errors(lv) or
                not _dependencies_ok(_chain(context, 'law-versions', vid), as_of)):
            excluded.append({'lawVersionId': vid, 'reason': 'STANDARD_IDENTITY_OR_CURRENT_GATE_FAILED'})
            continue
        publication_ok, publication = _scope_publication(definition, context, as_of)
        if not publication_ok:
            excluded.append({'lawVersionId': vid, 'reason': 'PUBLICATION_SCOPE_REVIEW_FAILED'})
            continue
        application_notes = _public_application_notes(definition, context, as_of, publication)
        if application_notes is None:
            excluded.append({'lawVersionId': vid, 'reason': 'APPLICATION_NOTE_EVIDENCE_OR_DATE_FAILED'})
            continue
        selected_associations = []
        for selected in definition['topicLinks']:
            kid, hid, cid = (selected[key] for key in ('linkId', 'hazardId', 'clauseId'))
            link = context.entities['links'].get(kid, {})
            clause = context.entities['clauses'].get(cid, {})
            profile = {'hazardId': hid, 'basisLinkIds': [kid]}
            if (kid not in gate.eligible_links or hid not in gate.eligible_hazards or link.get('role') != 'direct' or
                    link.get('hazardId') != hid or link.get('clauseId') != cid or clause.get('lawVersionId') != vid or
                    context.fingerprint(profile) != selected['dependencyFingerprint'] or
                    not _dependencies_ok(context.dependencies(profile, selected_only=True), as_of)):
                excluded.append({'linkId': kid, 'reason': 'EXACT_DIRECT_CHAIN_FAILED'})
                pending[kid] = hid
                continue
            record = {'hazardId': hid, 'linkId': kid, 'clauseId': cid, 'lawVersionId': vid,
                      'role': 'direct', 'applicability': link.get('applicability'),
                      'jurisdictionCode': link.get('jurisdictionCode')}
            if (not _text(record['applicability']) or
                    (record['jurisdictionCode'] is not None and not _text(record['jurisdictionCode'])) or
                    not _safe_public(record)):
                excluded.append({'linkId': kid, 'reason': 'PUBLIC_TEXT_UNSAFE'})
                pending[kid] = hid
                continue
            selected_associations.append(record)
        rows = []
        for selected in definition['clauses']:
            cid = selected['clauseId']
            clause = context.entities['clauses'].get(cid, {})
            if (clause.get('lawVersionId') != vid or content_hash(clause) != selected['contentHash'] or
                    not gate.clauses.get(cid, {}).get('ok') or
                    not _dependencies_ok(_chain(context, 'clauses', cid), as_of)):
                excluded.append({'clauseId': cid, 'reason': 'CONTROLLED_CLAUSE_GATE_FAILED'})
                continue
            try:
                validate_clause_content(clause, selected.get('tableIds', []))
            except ValueError:
                excluded.append({'clauseId': cid, 'reason': 'STRUCTURED_CLAUSE_CONTENT_FAILED'})
                continue
            row = {'clauseId': cid, 'article': clause['articlePath'], 'quote': clause['quote'],
                   'lawVersionId': vid, 'sourceUrl': clause.get('sourceUrl') or lv['sourceUrl'],
                   'checked': _checked(context.reviews['clauses'][cid]), 'status': '现行有效',
                   'granularity': selected['granularity'],
                   'directHazardIds': sorted({a['hazardId'] for a in selected_associations if a['clauseId'] == cid})}
            if 'contentParts' in clause:
                row['contentParts'] = copy.deepcopy(clause['contentParts'])
            if cid in application_notes:
                row['applicationNotes'] = application_notes[cid]
            if not _official_url(row['sourceUrl']) or not _safe_public(row):
                excluded.append({'clauseId': cid, 'reason': 'PUBLIC_TEXT_UNSAFE'})
                continue
            rows.append(row)
        if not rows:
            excluded.append({'lawVersionId': vid, 'reason': 'NO_PUBLISHABLE_CONTROLLED_CLAUSES'})
            continue
        complete = len(rows) == len(definition['clauses']) and definition['scopeVerified']
        # An explicit publication review approves the exact selected body as a
        # unit, even when a linked appendix is deliberately outside that body.
        # Losing a selected scope/definition article cannot leave other criteria
        # visible under the independently approved completeness statement.
        if (definition['officialScope']['wholeStandardComplete'] or publication is not None) and not complete:
            excluded.append({'lawVersionId': vid, 'reason': 'COMPLETE_BODY_INCOMPLETE'})
            continue
        published_ids = {row['clauseId'] for row in rows}
        counts = [row['judgmentItemCount'] for row in definition['clauses'] if row['clauseId'] in published_ids]
        known_items = sum(counts) if None not in counts and definition['scopeVerified'] else None
        direct_hazards = sorted({a['hazardId'] for a in selected_associations})
        standards.append({'id': vid, 'lawVersionId': vid,
            'standardVersion': {**copy.deepcopy(identity), 'effectiveDate': lv['effectiveDate'],
                                'endDate': lv.get('endDate') or '', 'validityStatus': lv['validityStatus']},
            'officialScope': copy.deepcopy(definition['officialScope']),
            'coverage': {'status': 'reviewed_scope_complete' if complete else 'partial',
                         'reviewedClauseCount': len(rows),
                         'reviewedWholeClauseCount': sum(r['granularity'] == 'whole_clause' for r in rows),
                         'reviewedSubitemClauseCount': sum(r['granularity'] == 'subitem' for r in rows),
                         'expectedWholeClauseCount': sum(r['granularity'] == 'whole_clause' for r in definition['clauses']),
                         'expectedJudgmentItemCount': definition['expectedJudgmentItemCount'],
                         'reviewedJudgmentItemCount': known_items,
                         'wholeStandardComplete': bool(complete and definition['officialScope']['wholeStandardComplete'])},
            'clauses': rows, 'directHazardIds': direct_hazards, 'directHazardCount': len(direct_hazards)})
        if publication is not None:
            standards[-1]['publicationBasis'] = publication
        expected_tables = sum(len(c.get('tableIds', [])) for c in definition['clauses'])
        if expected_tables:
            standards[-1]['coverage'].update(expectedTableCount=expected_tables,
                reviewedTableCount=sum(p['type'] == 'table' for c in rows for p in c.get('contentParts', [])))
        associations.extend(selected_associations)
    associations.sort(key=lambda row: (row['lawVersionId'], row['hazardId'], row['linkId']))
    common = {'schemaVersion': 1, 'asOf': as_of.isoformat(), 'wholeNormNotFieldFinding': True}
    return {'catalog': {**common, 'catalogScope': 'controlled_reviewed_standards_only',
                        'allIndustryCoverage': False, 'standards': standards},
            'topic': {**common, 'associations': associations,
                      'hazardIds': sorted({a['hazardId'] for a in associations}),
                      'coverage': {'excludedAssociationCount': len(pending),
                                   'excludedHazardCount': len(set(pending.values())),
                                   'exclusionReason': '受控专题中条文或适用关联待复核的项目未纳入；此数量不代表全行业缺口'}},
            'inventory': {'excluded': excluded}}
