"""Validate the applied, evidence-bounded disposition of the 44 commerce candidates.

This is a lineage/integrity gate, not a substitute for substantive legal review.
It never promotes a record, refreshes reviews, or establishes a site finding.
"""
from __future__ import annotations

import json
from pathlib import Path
from canonical import content_hash

LEDGER = 'docs/commerce-candidate-dispositions-20261002.jsonl'
INDEPENDENT_REVIEW = 'docs/commerce-independent-review-20261002.json'
CONTINUATION_REVIEW = 'docs/commerce-remaining-gaps-independent-review-20261002.json'
ATOMIC_SPLITS = 'docs/commerce-remaining-gap-atomic-splits-20261002.json'
ACTIONS = {
    'admitted_narrowed_definition', 'merged_conditionally', 'out_of_scope',
    'verification_only', 'basis_text_pending', 'basis_rebind_required',
    'scope_facts_pending', 'scope_split_required',
    'excluded_unsupported_claim', 'verification_protocol_complete',
}


def validate_rows(rows, hazards, reviews, source_map):
    errors = []
    ids = [r.get('hazardId') for r in rows]
    if len(ids) != 44 or len(set(ids)) != 44:
        errors.append('expected 44 unique source candidates')
    for row in rows:
        hid = row.get('hazardId')
        action = row.get('action')
        h, review = hazards.get(hid), reviews.get(hid)
        if not h or not review:
            errors.append(f'{hid}: missing entity or review')
            continue
        if action not in ACTIONS:
            errors.append(f'{hid}: unknown action')
        if row.get('appliedContentHash') != content_hash(h):
            errors.append(f'{hid}: disposition content hash is stale')
        if review.get('reviewedContentHash') != content_hash(h):
            errors.append(f'{hid}: review content hash is stale')
        if row.get('appliedLifecycle') != h.get('lifecycle'):
            errors.append(f'{hid}: lifecycle does not reconcile')
        if row.get('fieldViolationEstablished') is not False or row.get('remediationEstablished') is not False:
            errors.append(f'{hid}: source disposition must not establish a field finding or remediation')
        sources = [s for s in source_map if any(m.get('hazardId') == hid for m in s.get('mappedHazards', []))]
        if sorted(row.get('sourceCandidateIds', [])) != sorted(s['candidateId'] for s in sources):
            errors.append(f'{hid}: source row lineage differs from original ingest map')
        if sorted(row.get('sourceDocumentCodes', [])) != sorted({d for s in sources for d in s['sources']}):
            errors.append(f'{hid}: source document lineage differs from original ingest map')
        if not row.get('decisionReason') or not row.get('minimumProjectEvidence'):
            errors.append(f'{hid}: missing substantive reason or application evidence conditions')
        if action == 'merged_conditionally':
            target = row.get('canonicalHazardId')
            th = hazards.get(target)
            if h.get('lifecycle') != 'superseded' or h.get('mergedInto') != target or not target or target == hid:
                errors.append(f'{hid}: conditional merge not applied or invalid')
            if not th or th.get('lifecycle') != 'active' or th.get('mergedInto'):
                errors.append(f'{hid}: canonical target must be an unmerged active definition')
            elif row.get('canonicalTargetContentHash') != content_hash(th):
                errors.append(f'{hid}: canonical target changed; reassess merge applicability')
            if review.get('decision') != 'verified' or not row.get('remainingSourceClaims'):
                errors.append(f'{hid}: missing merge review or residual source boundary')
        elif action == 'admitted_narrowed_definition':
            if h.get('lifecycle') != 'active' or review.get('decision') != 'verified' or not row.get('reusedClauseIds'):
                errors.append(f'{hid}: admitted definition lacks active reviewed chain')
        else:
            if h.get('lifecycle') != 'proposed' or h.get('mergedInto'):
                errors.append(f'{hid}: unresolved/out-of-scope record must remain unpublished proposed')
            required = 'rejected' if action in {'out_of_scope', 'excluded_unsupported_claim'} else 'pending'
            if review.get('decision') != required:
                errors.append(f'{hid}: incorrect review decision for disposition')
        if h.get('proposalStatus') != action:
            errors.append(f'{hid}: proposalStatus not applied')
        if action != 'admitted_narrowed_definition' and row.get('releaseEligibleByThisDisposition') is not False:
            errors.append(f'{hid}: disposition must not grant release eligibility')
    return errors


def validate_independent_review(rows, independent, entities, atomic_rows=None):
    """Bind the separately authored decision without manufacturing a review."""
    errors = []
    expected = {r['hazardId']: r for r in rows + list(atomic_rows or []) if r['action'] in
                {'admitted_narrowed_definition', 'merged_conditionally'}}
    items = independent.get('items', [])
    if (len(items) != len(expected) or {i.get('hazardId') for i in items} != set(expected)
            or independent.get('result') != 'passed_for_bounded_generic_admission_and_conditional_merges'):
        errors.append('independent review must cover the exact applied definitions/merges including atomic splits')
    for item in items:
        hid = item.get('hazardId')
        if hid not in expected:
            continue
        row = expected[hid]
        if (item.get('action') != row['action']
                or item.get('independentContentScopeReview') != 'passed'
                or item.get('independentCurrencyReview') != 'bounded_current_technical_use_supported'
                or item.get('siteFactEstablished') is not False):
            errors.append(f'{hid}: independent scope/currency decision differs')
        bindings = [('hazards', hid, item.get('hazardHash'))]
        if row['action'] == 'merged_conditionally':
            if item.get('targetId') != row.get('canonicalHazardId'):
                errors.append(f'{hid}: independent merge target differs')
            bindings.append(('hazards', item.get('targetId'), item.get('targetHash')))
        elif {k.get('linkId') for k in item.get('links', [])} != set(row.get('appliedLinkIds', [])):
            errors.append(f'{hid}: independent selected link set differs')
        for link in item.get('links', []):
            bindings.extend([(folder, link.get(id_key), link.get(hash_key)) for folder, id_key, hash_key in
                [('links', 'linkId', 'linkHash'), ('clauses', 'clauseId', 'clauseHash'),
                 ('law-versions', 'lawVersionId', 'lawVersionHash')]])
        for folder, entity_id, expected_hash in bindings:
            entity = entities.get(folder, {}).get(entity_id)
            if not entity or content_hash(entity) != expected_hash:
                errors.append(f'{hid}: independent review stale for {entity_id}')
    return errors


def validate_commerce_dispositions(root: Path):
    rows = [json.loads(x) for x in (root / LEDGER).read_text(encoding='utf-8').splitlines() if x.strip()]
    hazards = {x['id']: x for p in (root/'knowledge/hazards').glob('*.json') for x in [json.loads(p.read_text(encoding='utf-8'))]}
    reviews = {x['entityId']: x for p in (root/'knowledge/reviews/hazards').glob('*.json') for x in [json.loads(p.read_text(encoding='utf-8'))]}
    source_map = [json.loads(x) for x in (root/'docs/commerce-ingest-map-20260921.jsonl').read_text(encoding='utf-8').splitlines()]
    errors = validate_rows(rows, hazards, reviews, source_map)
    independent = json.loads((root/INDEPENDENT_REVIEW).read_text(encoding='utf-8'))
    entities = {'hazards': hazards}
    for folder in ['links', 'clauses', 'law-versions']:
        entities[folder] = {x['id']: x for p in (root/'knowledge'/folder).glob('*.json')
                            for x in [json.loads(p.read_text(encoding='utf-8'))]}
    atomic_rows = json.loads((root/ATOMIC_SPLITS).read_text(encoding='utf-8'))['items']
    continuation = json.loads((root/CONTINUATION_REVIEW).read_text(encoding='utf-8'))
    expected_continuation = {r['hazardId'] for r in rows if r.get('continuedFromDisposition') and r['action'] in {'admitted_narrowed_definition', 'merged_conditionally'}} | {r['hazardId'] for r in atomic_rows}
    if (len(continuation.get('items', [])) != len(expected_continuation)
            or {i.get('hazardId') for i in continuation.get('items', [])} != expected_continuation):
        errors.append('continuation independent source review must cover exact new definitions and merge')
    independent = dict(independent, items=independent.get('items', []) + continuation.get('items', []))
    errors += validate_atomic_splits(atomic_rows, rows, source_map, entities)
    return errors + validate_independent_review(rows, independent, entities, atomic_rows)


def validate_atomic_splits(atomic_rows, rows, source_map, entities):
    errors = []
    if len(atomic_rows) != 1 or atomic_rows[0].get('hazardId') != 'H_COM_MOBILE_ELECTRIC_CORD_SELECTION':
        return ['exact one new independent electrical-cord atom is required']
    row = atomic_rows[0]
    hid, old_id = row['hazardId'], row.get('splitFromHazardId')
    h = entities.get('hazards', {}).get(hid)
    old = next((r for r in rows if r['hazardId'] == old_id), None)
    if (not h or not old or old['action'] != 'excluded_unsupported_claim'
            or old.get('splitAtomicHazardIds') != [hid]
            or h.get('lifecycle') != 'active' or row.get('action') != 'admitted_narrowed_definition'):
        errors.append('atomic split must preserve excluded original combustible-layout predicate')
    if not h or row.get('appliedContentHash') != content_hash(h):
        errors.append('atomic split hazard hash is stale')
    if row.get('fieldViolationEstablished') is not False or row.get('remediationEstablished') is not False:
        errors.append('atomic split cannot establish a field finding or remediation')
    exact = [s for s in source_map if any(m.get('hazardId') == hid for m in s.get('mappedHazards', []))]
    if [s['candidateId'] for s in exact] != ['SC118'] or exact[0].get('sources') != ['D15']:
        errors.append('atomic split must retain exact SC118/D15 map-only lineage')
    if row.get('sourceRead', {}).get('originalStatementMatched') is not False:
        errors.append('map-only atomic split cannot assert a new original-file reading')
    for source in exact:
        for mapping in source.get('mappedHazards', []):
            if mapping.get('hazardId') == hid and (mapping.get('originalFileReread') is not False or mapping.get('fieldViolationEstablished') is not False):
                errors.append('atomic mapping cannot assert a new file reading or field finding')
    return errors


if __name__ == '__main__':
    errors = validate_commerce_dispositions(Path(__file__).resolve().parents[2])
    print(f'commerce candidates: 44; errors: {len(errors)}')
    for error in errors:
        print(error)
    raise SystemExit(bool(errors))
