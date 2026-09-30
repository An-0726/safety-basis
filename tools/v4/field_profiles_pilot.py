"""Explicit local pilot projection. Never changes or approves formal knowledge."""
import copy
import hashlib
import json
from pathlib import Path

CLASSES = {'core_onsite_inspection', 'document_review', 'special_review', 'legal_obligation', 'undetermined'}
ENTRIES = {'include', 'conditional', 'exclude', 'undetermined'}
REQUIRED = {'id', 'hazardId', 'subitemTrace', 'title', 'inspectionClass', 'defaultFieldEntry',
            'recommendedDisposition', 'lifecycle', 'candidateStatus', 'object', 'defect',
            'sourceRefs', 'applicability', 'findingTemplate', 'pendingEvidenceNote',
            'evidenceRequirements', 'correctiveDirection', 'basisRefs', 'fieldReview', 'caseRole'}

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def digest(payload):
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()

def context(profile, knowledge):
    """Bind the entire profile and all upstream links, text, evidence and reviews.

    Addition/removal of a link also changes the digest. Missing entities are represented
    explicitly, so later completion invalidates the earlier semantic review.
    """
    knowledge = Path(knowledge)
    profile_body = {k: v for k, v in profile.items() if k != 'fieldReview'}
    bound = {}
    def bind(rel):
        path = knowledge / rel
        if rel in bound:
            return
        if not path.exists():
            bound[rel] = None
            return
        if path.is_dir():
            for child in sorted(path.rglob('*.json')):
                bind(child.relative_to(knowledge).as_posix())
        else:
            bound[rel] = read(path)
    hid = profile['hazardId']
    clause_ids = {ref['clauseId'] for ref in profile['basisRefs'] if ref.get('clauseId')}
    if hid:
        bind(f'hazards/{hid}.json')
        bind(f'reviews/hazards/{hid}.json')
        for path in sorted((knowledge/'links').glob('*.json')):
            link = read(path)
            if link.get('hazardId') == hid:
                bind(path.relative_to(knowledge).as_posix())
                bind(f"reviews/links/{link['id']}.json")
                if link.get('clauseId'):
                    clause_ids.add(link['clauseId'])
    for cid in sorted(clause_ids):
        bind(f'clauses/{cid}.json')
        bind(f'reviews/clauses/{cid}.json')
        clause = bound.get(f'clauses/{cid}.json') or {}
        vid = clause.get('lawVersionId')
        if vid:
            bind(f'law-versions/{vid}.json')
            bind(f'reviews/law-versions/{vid}.json')
            bind(f'evidence/{vid}')
            version = bound.get(f'law-versions/{vid}.json') or {}
            lid = version.get('lawId')
            if lid:
                bind(f'laws/{lid}.json')
                bind(f'reviews/laws/{lid}.json')
    for ref in profile['basisRefs']:
        if ref.get('pilotEvidenceId'):
            bind(f"field-profiles-pilot/evidence/{ref['pilotEvidenceId']}.json")
    # Existing evidence is a flat E_* namespace referenced by reviews.
    for entity in list(bound.values()):
        if isinstance(entity, dict):
            for ref in entity.get('evidenceRefs', []):
                eid = ref if isinstance(ref, str) else ref.get('evidenceId') or ref.get('id')
                if eid:
                    bind(f'evidence/{eid}.json')
    return digest({'profile': profile_body, 'upstream': bound})

def validate(profile, knowledge):
    missing = REQUIRED - profile.keys()
    if missing:
        raise ValueError(f"{profile.get('id')}: missing {sorted(missing)}")
    if profile['inspectionClass'] not in CLASSES or profile['defaultFieldEntry'] not in ENTRIES:
        raise ValueError(f"{profile['id']}: invalid routing")
    if profile['candidateStatus'] != 'candidate':
        raise ValueError(f"{profile['id']}: pilot cannot promote status")
    if profile['lifecycle'] not in {'active', 'proposed', 'superseded'}:
        raise ValueError(f"{profile['id']}: invalid lifecycle")
    if not all(profile[k] for k in ('object', 'defect', 'sourceRefs', 'evidenceRequirements', 'correctiveDirection', 'basisRefs')):
        raise ValueError(f"{profile['id']}: empty required content")
    if not profile['applicability'].get('requires') or not profile['applicability'].get('excludes'):
        raise ValueError(f"{profile['id']}: incomplete applicability")
    template = profile['findingTemplate']
    if profile['caseRole'] == 'positive' and (not template or '〔' not in template):
        raise ValueError(f"{profile['id']}: concrete fillable template required")
    if template and any(term in template for term in ('先核实', '再判定', '整改后复查')):
        raise ValueError(f"{profile['id']}: evidence process mixed into finding")
    review = profile['fieldReview']
    if review.get('status') != 'reviewed_candidate' or review.get('contextFingerprint') != context(profile, knowledge):
        raise ValueError(f"{profile['id']}: field review invalid/stale")
    if profile['hazardId']:
        hazard = read(Path(knowledge)/f"hazards/{profile['hazardId']}.json")
        if profile['lifecycle'] != hazard['lifecycle']:
            raise ValueError(f"{profile['id']}: lifecycle drift")

def projection(knowledge):
    knowledge = Path(knowledge)
    profiles = [read(path) for path in sorted((knowledge/'field-profiles-pilot/records').glob('*.json'))]
    if len(profiles) != 24 or len({p['id'] for p in profiles}) != 24:
        raise ValueError('pilot must contain exactly 24 unique cases')
    for profile in profiles:
        validate(profile, knowledge)
    result = []
    for profile in profiles:
        p = copy.deepcopy(profile)
        # Audit bindings are used by the builder, not piled into the user interface.
        p.pop('fieldReview')
        p['publishable'] = False
        p['status'] = ('本地候选 · 候选依据已核，现场事实待证实'
                       if p.get('basisCheck', {}).get('status') == 'candidate_basis_checked'
                       else '本地候选 · 依据缺口待补')
        p['description'] = p['findingTemplate'] or p['pendingEvidenceNote']
        p['category'] = p['inspectionClass']
        p['places'] = [p['object']]
        p['levels'] = []
        p['aliases'] = p.get('searchTerms', [])
        p['keywords'] = [p['object'], p['defect']]
        p['lawNames'] = []
        p['scopes'] = ['CN']
        p['regions'] = ['CN']
        p['mode'] = 'conditional'
        p['searchText'] = ' '.join([p['id'], p['hazardId'] or '', p['title'], p['object'], p['defect'],
                                   p['findingTemplate'] or '', *p.get('searchTerms', [])])
        p['bases'] = []
        for ref in p['basisRefs']:
            basis = dict(ref)
            cid = ref.get('clauseId')
            if cid:
                clause = read(knowledge/f'clauses/{cid}.json')
                version = read(knowledge/f"law-versions/{clause['lawVersionId']}.json")
                basis.update(article=clause['articlePath'], quote=clause['quote'],
                             sourceUrl=clause.get('sourceUrl', ''), lawVersionId=version['id'],
                             name=version.get('officialName', version.get('name', version['id'])) + ' ' + version.get('documentNumber', ''))
            eid = ref.get('pilotEvidenceId')
            if eid:
                basis.update(read(knowledge/f'field-profiles-pilot/evidence/{eid}.json'))
            p['bases'].append(basis)
        result.append(p)
    return {'schemaVersion': 1, 'pilotOnly': True, 'formalApproval': False, 'records': result}

def build_pilot(knowledge, web, out):
    out = Path(out)
    payload = projection(knowledge)
    (out/'data/field-profiles-pilot.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    import shutil
    for asset in ('field-pilot.html', 'field-pilot.css', 'js/field-pilot.js', 'js/field-pilot-search.js'):
        target = out/asset
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(web)/asset, target)
    return payload
