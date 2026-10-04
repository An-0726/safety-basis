"""Verify one approved same-obligation successor before auditing its old receipt.

This preserves the 2026-10-02 independent review as history. It does not make a
superseded H/K publishable, sign a new review, or permit arbitrary merges.
"""
import copy
import hashlib
import json
from pathlib import Path
from canonical import content_hash

APPROVAL = 'docs/STATIC_FIRE_INDEPENDENT_REVIEW_20261004.json'
HISTORY = 'docs/STATIC_FIRE_RECOVERY_HISTORY_20261004.json'
OLD_H = 'H_COM_MOBILE_ELECTRIC_CORD_SELECTION'
OLD_K = 'K_COM_PLUGSTRIP_CORD_GBT13869_5_2_2'
TARGET_H = 'H_8ECAE760F5A5413D8013602429'
TARGET_K = 'K_8ECAE760_GBT13869_5_2_2'


def approved_atomic_history(root, entities):
    root = Path(root)
    old_h = entities.get('hazards', {}).get(OLD_H)
    if not old_h or old_h.get('lifecycle') != 'superseded':
        return entities, []
    errors = []
    def require(ok, message):
        if not ok:
            raise ValueError(message)
    def path_for(relative):
        path = Path(relative)
        require(not path.is_absolute() and '..' not in path.parts and
                path.parts[0] in {'knowledge', 'docs'}, 'unsafe approval path')
        return root / path
    def read(relative):
        return json.loads(path_for(relative).read_text(encoding='utf-8'))
    def file_hash(relative):
        return hashlib.sha256(path_for(relative).read_bytes()).hexdigest()
    try:
        approval, history = read(APPROVAL), read(HISTORY)
        merge = approval.get('mobileMerge', {})
        require(approval.get('verdict') == 'APPROVE' and
                merge.get('result') == 'APPROVE_same_obligation_bounded_merge',
                'new independent same-obligation merge approval missing')
        for key, expected in [('supersededHazardId', OLD_H), ('supersededLinkId', OLD_K),
                              ('canonicalHazardId', TARGET_H), ('canonicalLinkId', TARGET_K)]:
            require(merge.get(key) == expected and history['mobileMerge'].get(key) == expected,
                    'merge identity changed: ' + key)
        proofs = {r['path']: r for r in merge['objects']}
        prior = {r['path']: r for r in history['mobileMerge']['objects']}
        required = {f'knowledge/{folder}/{ident}.json' for folder, ident in
                    [('hazards', OLD_H), ('hazards', TARGET_H), ('links', OLD_K), ('links', TARGET_K),
                     ('reviews/hazards', OLD_H), ('reviews/hazards', TARGET_H),
                     ('reviews/links', OLD_K), ('reviews/links', TARGET_K)]}
        require(set(proofs) == set(prior) == required, 'exact eight merge objects required')
        for relative in sorted(required):
            proof, saved, current = proofs[relative], prior[relative], read(relative)
            require(proof.get('exactHistoryVerified') is True, 'history not independently verified')
            require(file_hash(relative) == proof['currentFileSha256'] == saved['afterSha256'] ==
                    approval['fileSha256'][relative], 'current merge bytes changed: ' + relative)
            require(current == saved['afterObject'] and
                    content_hash(current) == proof['currentContentHash'], 'current object changed')
            require(saved['beforeSha256'] == proof['previousFileSha256'] and
                    content_hash(saved['beforeObject']) == proof['previousContentHash'],
                    'historical object changed: ' + relative)
            if '/reviews/' in relative:
                require(current.get('previousReview') == saved['beforeObject'],
                        'old independent-era review not completely preserved: ' + relative)
        require(file_hash(HISTORY) == approval['fileSha256'][HISTORY], 'merge history receipt changed')
        old_k = entities['links'][OLD_K]
        target_h, target_k = entities['hazards'][TARGET_H], entities['links'][TARGET_K]
        require(old_h.get('mergedInto') == TARGET_H and old_k.get('lifecycle') == 'superseded' and
                old_k.get('hazardId') == OLD_H, 'superseded source relation changed')
        require(target_h.get('lifecycle') == 'active' and not target_h.get('mergedInto') and
                target_k.get('lifecycle') == 'active' and target_k.get('hazardId') == TARGET_H and
                target_k.get('clauseId') == old_k.get('clauseId'), 'canonical same-obligation chain changed')
        require(read(f'knowledge/reviews/links/{OLD_K}.json').get('decision') == 'rejected',
                'superseded duplicate current association must remain withdrawn')
        cid = target_k['clauseId']; clause = entities['clauses'][cid]
        vid = clause['lawVersionId']; version = entities['law-versions'][vid]
        lid = version['lawId']
        dependency_paths = set()
        for folder, ident in [('clauses', cid), ('law-versions', vid), ('laws', lid)]:
            dep_path, review_path = f'knowledge/{folder}/{ident}.json', f'knowledge/reviews/{folder}/{ident}.json'
            dependency_paths.update((dep_path, review_path))
            entity, review = read(dep_path), read(review_path)
            require(review.get('decision') == 'verified' and
                    review.get('reviewedContentHash') == content_hash(entity), 'dependency review changed')
            for obj in (entity, review):
                for eid in obj.get('evidenceRefs', []):
                    require(isinstance(eid, str), 'malformed dependency evidence')
                    dependency_paths.add(f'knowledge/evidence/{eid}.json')
        for ident in (OLD_H, TARGET_H, OLD_K, TARGET_K):
            folder = 'hazards' if ident in (OLD_H, TARGET_H) else 'links'
            review = read(f'knowledge/reviews/{folder}/{ident}.json')
            for eid in review.get('evidenceRefs', []):
                dependency_paths.add(f'knowledge/evidence/{eid}.json')
        bindings = merge.get('sourceBindings', {})
        require(dependency_paths <= set(bindings), 'independent upstream source bindings incomplete')
        for relative, expected in bindings.items():
            require(file_hash(relative) == expected, 'independent upstream source changed: ' + relative)
        previous_reviews = merge.get('historicalIndependentReviewsUnchanged', {})
        require(set(previous_reviews) == {'docs/commerce-independent-review-20261002.json',
                    'docs/commerce-remaining-gaps-independent-review-20261002.json'},
                'both old independent reviews must remain intact')
        for relative, expected in previous_reviews.items():
            require(file_hash(relative) == expected, 'old independent review was modified')
        # Only these two objects are restored for the historical approval audit.
        # The current release Gate still consumes the actual superseded objects.
        view = copy.deepcopy(entities)
        view['hazards'][OLD_H] = copy.deepcopy(prior[f'knowledge/hazards/{OLD_H}.json']['beforeObject'])
        view['links'][OLD_K] = copy.deepcopy(prior[f'knowledge/links/{OLD_K}.json']['beforeObject'])
        return view, []
    except (KeyError, TypeError, ValueError, OSError) as exc:
        errors.append('mobile-cord independent carry-forward: ' + str(exc))
        return entities, errors
