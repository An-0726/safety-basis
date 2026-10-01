"""Independently reviewed administrative source text for reading only.

This namespace creates no C/H/K and never calls or relaxes their current-basis
Gate. A separate directory identity review and an exact whole-group text/rights
review are both required. Unknown starting dates remain unknown.
"""
import copy
import json
import re
from datetime import date
from pathlib import Path

from canonical import content_hash
from field_profiles import ProfileContext, _selected_review_date_errors
from major_criteria import _safe_public, HASH
from major_criteria_references import _reference_url, _checked_date
import major_criteria_directory as directory

NAMESPACE = 'major-criteria-reading/v1'
READING_FILE = 'data/major-criteria-reading.json'
SCHEMA = 'safety-major-criteria-reading-v1'
TEXT_SCOPE = 'official_administrative_reference_body_and_item_completeness'
SCOPE = 'official_reference_text_identity_rights_and_explanations_without_current_eligibility'
BASIS = 'copyright_law_article_5_official_administrative_document'
NOTICE = '本区仅供官方原文查阅，不授予本站现行判定依据资格；未知施行日不作推定，不能据此自动作现场判定。'
IDENTITY_FIELDS = {'lawId','lawVersionId','title','documentNumber','versionKey','issuer','documentKind',
    'legalNature','officialLink','officialTextLink','publicationDate','effectiveDate','effectiveDateNote',
    'scopeHint','scopeCaveat','directoryGroup','requiredCompanionIds','supplementsReferenceId'}
ADMIN_KINDS = {'部门规章','部门规范性文件','部门规范性文件（补充判定情形）',
    '部门规范性文件（以通知印发的判定标准）','部门规范性文件（通知所附判定标准）'}
IDENT = re.compile(r'^[A-Za-z0-9_]+$')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _require(ok, code):
    if not ok:
        raise ValueError('READING_' + code)


def _keys(value, fields):
    return isinstance(value, dict) and set(value) == set(fields)


def _id(value):
    return isinstance(value, str) and bool(IDENT.fullmatch(value))


def _text(value, maximum=50000, empty=False):
    return (isinstance(value, str) and (empty or bool(value.strip())) and len(value) <= maximum and
            not any(ord(c) < 32 and c != '\n' for c in value))


def _day(value):
    try:
        return isinstance(value, str) and date.fromisoformat(value).isoformat() == value
    except (TypeError, ValueError):
        return False


def _ids(value, empty=False):
    return isinstance(value, list) and (empty or bool(value)) and all(_id(x) for x in value) and len(set(value)) == len(value)


def body(document):
    return {k: copy.deepcopy(document[k]) for k in ('noticeText', 'sections')}


def items(document):
    return [item for section in document['sections'] for item in section['items']]


def source_identity(entry):
    return {k: copy.deepcopy(entry[k]) for k in sorted(IDENTITY_FIELDS)}


def validate_record(record):
    fields = {'schemaVersion','id','directoryGroupId','primaryReferenceId','requiredReferenceIds',
              'readingReason','warning','documents','evidence','publication'}
    _require(_keys(record, fields) and type(record['schemaVersion']) is int and record['schemaVersion'] == 1, 'RECORD_FIELDS')
    _require(all(_id(record[k]) for k in ('id','directoryGroupId','primaryReferenceId')) and
             _ids(record['requiredReferenceIds']) and record['primaryReferenceId'] in record['requiredReferenceIds'], 'GROUP_ID')
    _require(record['readingReason'] == 'effective_date_not_fully_verified' and _text(record['warning'], 1000), 'READING_REASON')
    publication = record['publication']
    _require(_keys(publication, {'basis','legalSourceUrl','evidenceIds'}) and publication['basis'] == BASIS and
             _reference_url(publication['legalSourceUrl']) and _ids(publication['evidenceIds']), 'PUBLICATION')
    evidence = record['evidence']
    _require(isinstance(evidence, dict) and evidence, 'EVIDENCE')
    for ident, row in evidence.items():
        _require(_id(ident) and _keys(row, {'id','url','tier','snapshotSha256','snapshotKind','locator','sourceDate','retrievedAt'}) and
                 row['id'] == ident and row['tier'] == 'authoritative-public' and _reference_url(row['url']) and
                 isinstance(row['snapshotSha256'], str) and HASH.fullmatch(row['snapshotSha256']) and
                 _text(row['snapshotKind'],500) and _text(row['locator'],2000) and
                 (row['sourceDate'] is None or _day(row['sourceDate'])) and _day(row['retrievedAt']) and
                 (row['sourceDate'] is None or row['sourceDate'] <= row['retrievedAt']), 'EVIDENCE_FIELDS')
    _require(isinstance(record['documents'], list) and record['documents'], 'DOCUMENTS')
    seen_docs, seen_items, seen_notes = set(), set(), set()
    used_evidence = set()
    for doc in record['documents']:
        _require(_keys(doc, {'directoryReferenceId','sourceIdentity','noticeText','sections','firstLevelItemCount',
                            'sourceEvidenceIds','currentUseEvidence','officialClarifications'}), 'DOCUMENT_FIELDS')
        ident = doc['directoryReferenceId']
        _require(_id(ident) and ident not in seen_docs, 'DOCUMENT_ID'); seen_docs.add(ident)
        identity = doc['sourceIdentity']
        _require(_keys(identity, IDENTITY_FIELDS) and isinstance(identity['documentKind'],str) and identity['documentKind'] in ADMIN_KINDS and
                 all(_id(identity[k]) for k in ('lawId','lawVersionId')) and
                 all(_text(identity[k], 2000) for k in ('title','documentNumber','versionKey','issuer','legalNature','scopeHint','scopeCaveat')) and
                 _text(identity['effectiveDateNote'],1000,True) and _reference_url(identity['officialLink']) and
                 _reference_url(identity['officialTextLink']) and _day(identity['publicationDate']) and
                 (identity['effectiveDate'] is None or _day(identity['effectiveDate'])) and
                 (identity['effectiveDate'] is not None or bool(identity['effectiveDateNote'].strip())) and
                 _keys(identity['directoryGroup'], {'id','label','role'}) and
                 identity['directoryGroup']['id'] == record['directoryGroupId'] and
                 identity['directoryGroup']['role'] in ('primary','supplement') and
                 _text(identity['directoryGroup']['label'],200) and _ids(identity['requiredCompanionIds'],True) and
                 (identity['supplementsReferenceId'] is None or _id(identity['supplementsReferenceId'])), 'SOURCE_IDENTITY')
        _require(_text(doc['noticeText']) and _ids(doc['sourceEvidenceIds']), 'SOURCE_BODY')
        used_evidence.update(doc['sourceEvidenceIds'])
        _require(isinstance(doc['sections'], list) and doc['sections'], 'SECTIONS')
        section_ids, doc_items = set(), set()
        for section in doc['sections']:
            _require(_keys(section, {'id','title','items'}) and _id(section['id']) and section['id'] not in section_ids and
                     _text(section['title'],1000) and isinstance(section['items'],list) and section['items'], 'SECTION')
            section_ids.add(section['id'])
            for item in section['items']:
                _require(_keys(item, {'id','articleLabel','quote'}) and _id(item['id']) and item['id'] not in seen_items and
                         _text(item['articleLabel'],100) and _text(item['quote']), 'ITEM')
                seen_items.add(item['id']); doc_items.add(item['id'])
        _require(type(doc['firstLevelItemCount']) is int and doc['firstLevelItemCount'] == len(doc_items), 'ITEM_COUNT')
        _require(isinstance(doc['currentUseEvidence'],list) and doc['currentUseEvidence'], 'CURRENT_USE_EVIDENCE')
        for usage in doc['currentUseEvidence']:
            _require(_keys(usage, {'sourceDate','sourceUrl','summary','evidenceId'}) and _day(usage['sourceDate']) and
                     _reference_url(usage['sourceUrl']) and _text(usage['summary'],1000) and _id(usage['evidenceId']), 'CURRENT_USE_FIELDS')
            used_evidence.add(usage['evidenceId'])
        _require(isinstance(doc['officialClarifications'],list), 'CLARIFICATIONS')
        for note in doc['officialClarifications']:
            _require(_keys(note, {'id','appliesToItemIds','textMode','text','sourceDate','sourceUrl','sourcePages','evidenceId'}) and
                     _id(note['id']) and note['id'] not in seen_notes and _ids(note['appliesToItemIds']) and
                     set(note['appliesToItemIds']) <= doc_items and note['textMode'] in ('reviewed_summary','official_link_pending') and
                     _text(note['text'],2500) and _day(note['sourceDate']) and _reference_url(note['sourceUrl']) and _id(note['evidenceId']), 'CLARIFICATION_FIELDS')
            pages = note['sourcePages']
            _require(pages is None or (isinstance(pages,list) and pages and all(type(p) is int and 1 <= p <= 1000 for p in pages) and pages == sorted(set(pages))), 'NOTE_PAGES')
            seen_notes.add(note['id']); used_evidence.add(note['evidenceId'])
    _require(seen_docs == set(record['requiredReferenceIds']), 'REQUIRED_DOCUMENTS')
    primary = [d for d in record['documents'] if d['sourceIdentity']['directoryGroup']['role'] == 'primary']
    _require(len(primary) == 1 and primary[0]['directoryReferenceId'] == record['primaryReferenceId'] and
             set(primary[0]['sourceIdentity']['requiredCompanionIds']) == seen_docs - {record['primaryReferenceId']} and
             all(d['sourceIdentity']['supplementsReferenceId'] == record['primaryReferenceId'] for d in record['documents'] if d is not primary[0]), 'COMPANION_GRAPH')
    _require(any(d['sourceIdentity']['effectiveDate'] is None for d in record['documents']), 'UNKNOWN_DATE_REASON_REQUIRED')
    _require(used_evidence == set(evidence), 'EXACT_EVIDENCE_MEMBERSHIP')
    _require(_safe_public({k:v for k,v in record.items() if k != 'evidence'}), 'PRIVATE_TEXT')
    for doc in record['documents']:
        _require(any(evidence[eid]['url'] in (doc['sourceIdentity']['officialLink'], doc['sourceIdentity']['officialTextLink']) for eid in doc['sourceEvidenceIds']), 'NORM_SOURCE_EVIDENCE')
        for row in doc['currentUseEvidence'] + doc['officialClarifications']:
            e = evidence[row['evidenceId']]
            _require(e['url'] == row['sourceUrl'] and e['sourceDate'] == row['sourceDate'], 'EXACT_SOURCE_EVIDENCE')


def load_records(knowledge):
    records, directory_groups = {}, set()
    for path in sorted((Path(knowledge)/NAMESPACE/'records').glob('*.json')):
        record = read(path); validate_record(record)
        _require(path.stem == record['id'] and record['id'] not in records and record['directoryGroupId'] not in directory_groups, 'DUPLICATE_RECORD')
        records[record['id']] = record; directory_groups.add(record['directoryGroupId'])
    return records


def text_review_binding(document):
    """Read-only item inventory for an independent textual review."""
    return {'reviewedContentHash':content_hash(body(document)), 'itemContentHashes':[
        {'itemId':item['id'],'reviewedContentHash':content_hash(item)} for item in items(document)]}


def dependencies(record, knowledge, publication):
    context = ProfileContext(knowledge)
    records = directory.load_records(knowledge)
    deps = {}
    for doc in record['documents']:
        ident = doc['directoryReferenceId']; source = records.get(ident)
        deps['directory-records/'+ident] = source
        p = Path(knowledge)/directory.NAMESPACE/'reviews'/(ident+'.json')
        deps['directory-reviews/'+ident] = read(p) if p.exists() else None
        if source is not None:
            for key,value in directory.dependencies(source,knowledge,publication,context=context).items():
                deps['directory/'+ident+'/'+key] = value
        p = Path(knowledge)/NAMESPACE/'text-reviews'/(ident+'.json')
        deps['text-reviews/'+ident] = read(p) if p.exists() else None
    for eid in record['publication']['evidenceIds']:
        deps['publication-evidence/'+eid] = context.entities['evidence'].get(eid)
    return deps


def review_bindings(record, knowledge, publication):
    validate_record(record)
    return {'reviewedContentHash':content_hash(record), 'dependencyFingerprint':content_hash(dependencies(record,knowledge,publication))}


def _text_review_ok(doc, review, at):
    fields = {'schemaVersion','directoryReferenceId','decision','reviewScope','reviewedContentHash',
              'itemDecisions','checkedAt','reviewer','reason'}
    expected = text_review_binding(doc)
    decisions = review.get('itemDecisions') if isinstance(review,dict) else None
    if (not isinstance(decisions,list) or not all(_keys(row,{'itemId','reviewedContentHash','decision'}) and
            row['decision'] == 'verified' for row in decisions)):
        return False
    hashes = [{k:v for k,v in row.items() if k != 'decision'} for row in decisions]
    return (_keys(review,fields) and type(review['schemaVersion']) is int and review['schemaVersion'] == 1 and
            review['directoryReferenceId'] == doc['directoryReferenceId'] and review['decision'] == 'verified' and
            review['reviewScope'] == TEXT_SCOPE and _checked_date(review['checkedAt']) and
            _text(review['reviewer'],500) and _text(review['reason'],20000) and
            not _selected_review_date_errors({'reviews/reading-text':review},at) and
            review['reviewedContentHash'] == expected['reviewedContentHash'] and hashes == expected['itemContentHashes'])


def _admitted(record, knowledge, publication, at, public_directory):
    deps = dependencies(record,knowledge,publication)
    if any(v is None for v in deps.values()): return None, 'DEPENDENCY_MISSING'
    entries = {e['id']:e for e in public_directory['entries']}
    group = next((g for g in public_directory['directoryGroups'] if g['id'] == record['directoryGroupId']),None)
    if (group is None or group['primaryReferenceId'] != record['primaryReferenceId'] or
            set(group['documentIds']) != set(record['requiredReferenceIds'])): return None, 'DIRECTORY_GROUP_NOT_ADMITTED'
    for doc in record['documents']:
        ident = doc['directoryReferenceId']
        if ident not in entries or source_identity(entries[ident]) != doc['sourceIdentity']: return None, 'DIRECTORY_IDENTITY_CHANGED'
        if not _text_review_ok(doc,deps['text-reviews/'+ident],at): return None, 'TEXT_REVIEW_FAILED'
    path = Path(knowledge)/NAMESPACE/'scope-reviews'/(record['id']+'.json')
    review = read(path) if path.exists() else None
    fields = {'schemaVersion','readingGroupId','decision','reviewScope','reviewedContentHash','dependencyFingerprint',
              'checkedAt','referenceTextPublicationReady','currentDeterminationBasis','reviewer','reason'}
    if (not _keys(review,fields) or type(review['schemaVersion']) is not int or review['schemaVersion'] != 1 or
            review['readingGroupId'] != record['id'] or review['decision'] != 'verified' or review['reviewScope'] != SCOPE or
            review['referenceTextPublicationReady'] is not True or review['currentDeterminationBasis'] is not False or
            not _checked_date(review['checkedAt']) or not _text(review['reviewer'],500) or not _text(review['reason'],30000) or
            _selected_review_date_errors({'reviews/reading-scope':review},at)): return None, 'SCOPE_REVIEW_FAILED'
    binding = {'reviewedContentHash':content_hash(record),'dependencyFingerprint':content_hash(deps)}
    if any(review[k] != v for k,v in binding.items()): return None, 'REVIEW_BINDING_STALE'
    checked = review['checkedAt'][:10]
    for doc in record['documents']:
        if deps['text-reviews/'+doc['directoryReferenceId']]['checkedAt'][:10] > checked: return None,'TEXT_REVIEW_AFTER_SCOPE'
    for source in record['evidence'].values():
        if ((source['sourceDate'] is not None and source['sourceDate'] > at.isoformat()) or
                source['retrievedAt'] > at.isoformat() or source['retrievedAt'] > checked):
            return None,'EVIDENCE_DATE_FAILED'
    rights = [deps['publication-evidence/'+eid] for eid in record['publication']['evidenceIds']]
    if not any(e.get('url') == record['publication']['legalSourceUrl'] for e in rights): return None,'RIGHTS_SOURCE_MISSING'
    for e in rights:
        if (e.get('tier') != 'authoritative-public' or not _reference_url(e.get('url')) or
                not HASH.fullmatch(str(e.get('snapshotSha256',''))) or not _text(e.get('locator')) or
                not _day(e.get('retrievedAt')) or e['retrievedAt'] > checked or e['retrievedAt'] > at.isoformat()):
            return None,'RIGHTS_EVIDENCE_FAILED'
    return review, None


def public_projection(knowledge, publication, *, as_of):
    if type(as_of) is not date: raise TypeError('as_of must be an explicit datetime.date')
    records = load_records(knowledge)
    metadata = directory.public_projection(knowledge,publication,as_of=as_of)['public']
    groups,excluded = [],[]
    for record in records.values():
        review,error = _admitted(record,knowledge,publication,as_of,metadata)
        if error:
            excluded.append({'readingGroupId':record['id'],'reason':error});continue
        docs=[]
        for doc in record['documents']:
            text_review = read(Path(knowledge)/NAMESPACE/'text-reviews'/(doc['directoryReferenceId']+'.json'))
            row={k:copy.deepcopy(doc[k]) for k in ('directoryReferenceId','sourceIdentity','noticeText','sections','firstLevelItemCount')}
            row.update(fullTextReviewed=True,checked=text_review['checkedAt'])
            row['currentUseEvidence']=[{k:v for k,v in usage.items() if k!='evidenceId'} for usage in doc['currentUseEvidence']]
            row['officialClarifications']=[{**{k:copy.deepcopy(v) for k,v in note.items() if k!='evidenceId'},
                'checked':review['checkedAt'],'isOfficialNormText':False} for note in doc['officialClarifications']]
            docs.append(row)
        group={'id':record['id'],'directoryGroupId':record['directoryGroupId'],'primaryReferenceId':record['primaryReferenceId'],
               'requiredReferenceIds':copy.deepcopy(record['requiredReferenceIds']),'readingReason':record['readingReason'],
               'warning':record['warning'],'checked':review['checkedAt'],'documents':docs,
               'publicationBasis':{'basis':BASIS,'legalSourceUrl':record['publication']['legalSourceUrl'],
                   'checked':review['checkedAt'],'referenceTextPublicationApproved':True}}
        if not _safe_public(group):
            excluded.append({'readingGroupId':record['id'],'reason':'PRIVATE_OUTPUT'});continue
        groups.append(group)
    public={'schemaVersion':SCHEMA,'asOf':as_of.isoformat(),'catalogScope':'official_source_reading_only',
        'referenceOnly':True,'currentDeterminationBasis':False,'reviewedCurrentClauseCount':0,'directHazardCount':0,
        'standaloneDeterminationAllowed':False,'allIndustryCoverage':False,'notice':NOTICE,
        'readingGroupCount':len(groups),'sourceDocumentCount':sum(len(g['documents']) for g in groups),
        'firstLevelItemCount':sum(d['firstLevelItemCount'] for g in groups for d in g['documents']), 'readingGroups':groups}
    return {'public':public,'inventory':{'excluded':excluded}}
