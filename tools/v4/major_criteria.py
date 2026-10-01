"""Controlled major-criteria catalog and exact direct-basis topic.

This read-only projection never approves source reviews or creates hazards. Catalog
clauses need not have an H/K edge. Both projections retain the original chained
Gate, explicit source pins and strict date/evidence/privacy checks.
"""
import copy
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from canonical import content_hash
from field_profiles import (PRIVATE, ProfileContext, _selected_review_date_errors,
                            _selected_version_date_errors)
from release_gate_core import evaluate_release_gate

CONFIG_PATH = 'major-criteria/v1/catalog.json'
CATALOG_FILE = 'data/major-criteria-catalog.json'
TOPIC_FILE = 'data/major-criteria-topic.json'
HASH = re.compile(r'^[a-f0-9]{64}$')


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
    seen = set()
    for standard in config['standards']:
        fields = {'lawVersionId', 'identity', 'lawContentHash', 'versionContentHash',
                  'officialScope', 'scopeVerified', 'expectedJudgmentItemCount', 'clauses', 'topicLinks', 'pendingTopicLinks'}
        if not isinstance(standard, dict) or set(standard) != fields:
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
                not all(_official_url(url) for url in scope['sourceUrls']) or scope['wholeStandardComplete'] is not False):
            # v1 deliberately cannot claim complete norms or all-industry coverage.
            raise ValueError('MAJOR_SCOPE')
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
                if not isinstance(row, dict) or set(row) != fields or not _text(row.get(ident)) or row[ident] in ids:
                    raise ValueError('MAJOR_CONTROLLED_REFERENCE:' + key)
                ids.add(row[ident])
                pin = row['contentHash'] if key == 'clauses' else row['dependencyFingerprint']
                if not isinstance(pin, str) or not HASH.fullmatch(pin):
                    raise ValueError('MAJOR_SOURCE_PIN')
                if key == 'clauses' and (row['granularity'] not in ('whole_clause', 'subitem') or not _count(row['judgmentItemCount'])):
                    raise ValueError('MAJOR_CLAUSE_GRANULARITY')
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
            row = {'clauseId': cid, 'article': clause['articlePath'], 'quote': clause['quote'],
                   'lawVersionId': vid, 'sourceUrl': clause.get('sourceUrl') or lv['sourceUrl'],
                   'checked': _checked(context.reviews['clauses'][cid]), 'status': '现行有效',
                   'granularity': selected['granularity'],
                   'directHazardIds': sorted({a['hazardId'] for a in selected_associations if a['clauseId'] == cid})}
            if not _official_url(row['sourceUrl']) or not _safe_public(row):
                excluded.append({'clauseId': cid, 'reason': 'PUBLIC_TEXT_UNSAFE'})
                continue
            rows.append(row)
        if not rows:
            excluded.append({'lawVersionId': vid, 'reason': 'NO_PUBLISHABLE_CONTROLLED_CLAUSES'})
            continue
        complete = len(rows) == len(definition['clauses']) and definition['scopeVerified']
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
                         'reviewedJudgmentItemCount': known_items, 'wholeStandardComplete': False},
            'clauses': rows, 'directHazardIds': direct_hazards, 'directHazardCount': len(direct_hazards)})
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
