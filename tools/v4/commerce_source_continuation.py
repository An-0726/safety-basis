"""One independently approved source-metadata continuation, never a new admission.

The original commerce report and all its other items remain byte-identical. This
helper validates the separate exact proof, then changes only one LV hash in an
in-memory audit view. No source, report, Gate decision or legal scope is written.
"""
import copy
import hashlib
import json
from pathlib import Path
from canonical import content_hash

PROOF = 'docs/COMPLETE_REMAINING_COMMERCE_SOURCE_CONTINUATION_20261005.json'
PROOF_SHA256 = '519ef5f4ffb532e63cca99e5a70774a783843a7962ddec6ef969654b4fb3bc06'
LEGACY_REPORT = 'docs/commerce-independent-review-20261002.json'
LEGACY_REPORT_SHA256 = 'bf693e5e2418096039e51654bfa7d2dde272cce6964729a51fd7f27b85350d1d'
HAZARD = 'H_COM_PAINT_SHIFT_QUANTITY'
LINK = 'K_COM_20261002_PAINT_SHIFT_QUANTITY_GB6514_6_2_1_2'
CLAUSE = 'C_GB6514_6_2_1_2'
VERSION = 'LV_STD_GB6514'
VERSION_PATH = 'knowledge/law-versions/' + VERSION + '.json'
REVIEW_PATH = 'knowledge/reviews/law-versions/' + VERSION + '.json'
BASELINE_COMMIT = '475856179bfd3c6c3446d10cfc4de73e51f228f3'
BASELINE_TREE = 'fc62800c09421f687c0734f699b95befa8231f2f'
BEFORE_VERSION_SHA256 = 'd608678dddef83c7550711a4f3dcf6f338372ab48fe1461b3a7ca9d4e3708995'
BEFORE_VERSION_HASH = 'dbbe411a3913bcf5afbfb8d2a8d5369d4262d3f6b8dc6acdc2b24ad662e3e629'
AFTER_VERSION_SHA256 = '5398cd078f1c2abe62a20feffae6a8ab32c4ddda3dff3fadda3df1cb9ceceaee'
AFTER_VERSION_HASH = '3220e9bfd5fee61dfe4799ae33e478f53b865c3fdb5425eae8f5b2114aa7e15c'
AFTER_REVIEW_SHA256 = '968fa279e55843093d09504accffdbb73d33fd3e79c962e7a93a62e99ae80e94'
UNCHANGED = {
    'knowledge/hazards/' + HAZARD + '.json': '19505f09b9326693e2849620576c8ef859635b3b6cf2d1b3d8da387ba2b7ab99',
    'knowledge/links/' + LINK + '.json': '8bc2ff59d725bd91af32c8f74b95e97cddb509b7d7eb5c3bf152dbd6dbe8d88f',
    'knowledge/clauses/' + CLAUSE + '.json': 'ba5075bf1672bf5a77f7c8272e9058110e37e307692e7eaa940ed222fe959a30',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def approved_source_continuation(root, independent, entities):
    root = Path(root)
    if not (root / PROOF).is_file():
        return independent, []  # Historical snapshots retain their original audit.
    try:
        def require(ok, message):
            if not ok: raise ValueError(message)
        proof_raw = (root / PROOF).read_bytes()
        require(sha(proof_raw) == PROOF_SHA256, 'independent continuation proof bytes changed')
        proof = json.loads(proof_raw)
        require(proof['schemaVersion'] == 'complete-remaining-commerce-source-continuation-v1' and
                proof['decision'] == 'approved_exact_source_metadata_continuation', 'missing exact independent approval')
        require(proof['targetHazardId'] == HAZARD and proof['targetLawVersionId'] == VERSION,
                'continuation target changed')
        require(proof['baselineCommit'] == BASELINE_COMMIT and proof['baselineTree'] == BASELINE_TREE,
                'continuation baseline changed')
        require(proof['allowedChangedVersionFields'] == ['scope', 'sourceUrl'], 'allowed metadata fields changed')
        require(proof['siteFactsConfirmed'] is False and proof['siteFactEstablished'] is False and
                proof['newDutiesApproved'] is False and proof['enterpriseRemediationConfirmed'] is False and
                proof['legacyReportBytesPreserved'] is True, 'continuation claims a new duty or site finding')
        legacy_raw = (root / LEGACY_REPORT).read_bytes()
        require(sha(legacy_raw) == LEGACY_REPORT_SHA256 == proof['legacyReport']['sha256'] and
                proof['legacyReport']['path'] == LEGACY_REPORT, 'legacy independent report bytes changed')
        legacy = json.loads(legacy_raw)
        old_items = [item for item in legacy['items'] if item['hazardId'] == HAZARD]
        require(len(old_items) == 1 and old_items[0] == proof['legacyReport']['item'] and
                len(legacy['items']) == proof['legacyReport']['itemCount'] == 24, 'legacy target item changed')
        require(proof['otherItemsUnchanged'] == 23, 'other legacy items must remain unchanged')
        for old_item in legacy['items']:
            matches = [item for item in independent['items'] if item['hazardId'] == old_item['hazardId']]
            require(matches == [old_item], 'legacy item missing, duplicated or altered in input view')
        original_item = old_items[0]
        require(len(original_item['links']) == 1 and original_item['links'][0]['linkId'] == LINK and
                original_item['links'][0]['clauseId'] == CLAUSE and
                original_item['links'][0]['lawVersionId'] == VERSION and
                original_item['links'][0]['lawVersionHash'] == BEFORE_VERSION_HASH, 'legacy selected source chain changed')
        before = proof['beforeVersion']; before_raw = before['fileTextUtf8'].encode('utf-8')
        require(before['path'] == VERSION_PATH and before['fileSha256'] == BEFORE_VERSION_SHA256 == sha(before_raw),
                'historical version bytes are not the true baseline')
        require(json.loads(before_raw) == before['definition'] and
                content_hash(before['definition']) == before['contentHash'] == BEFORE_VERSION_HASH,
                'historical version definition changed')
        after = proof['afterVersion']; after_raw = (root / VERSION_PATH).read_bytes(); version = json.loads(after_raw)
        require(after['path'] == VERSION_PATH and after['fileSha256'] == AFTER_VERSION_SHA256 == sha(after_raw) and
                after['contentHash'] == AFTER_VERSION_HASH == content_hash(version) and after['definition'] == version,
                'current version differs from the exact independently approved metadata')
        changed = {key for key in set(before['definition']) | set(version) if before['definition'].get(key) != version.get(key)}
        require(changed == {'scope', 'sourceUrl'}, 'version change exceeds the two approved metadata fields')
        review_raw = (root / REVIEW_PATH).read_bytes(); review = json.loads(review_raw)
        require(after['reviewPath'] == REVIEW_PATH and
                after['reviewFileSha256'] == AFTER_REVIEW_SHA256 == sha(review_raw), 'current version review bytes changed')
        require(review['entityId'] == VERSION and review['decision'] == 'verified' and
                review['reviewedContentHash'] == AFTER_VERSION_HASH, 'current version review is stale or not verified')
        rows = proof['unchangedEntities']; pinned = {row['path']: row for row in rows}
        require(len(rows) == 3 and set(pinned) == set(UNCHANGED), 'exact unchanged H/K/C set required')
        for relative, expected in UNCHANGED.items():
            raw = (root / relative).read_bytes(); entity = json.loads(raw); row = pinned[relative]
            folder, ident = Path(relative).parts[1], Path(relative).stem
            require(sha(raw) == expected == row['fileSha256'] and entity['id'] == row['entityId'] == ident and
                    content_hash(entity) == row['contentHash'], 'unchanged source bytes differ: ' + relative)
            require(entities[folder][ident] == entity, 'caller source view changed: ' + relative)
        require(entities['law-versions'][VERSION] == version, 'caller version view changed')
        candidates = [i for i, item in enumerate(independent['items']) if item['hazardId'] == HAZARD]
        require(len(candidates) == 1 and independent['items'][candidates[0]] == original_item,
                'input target item is missing, duplicated or already altered')
        # The sole allowed mutation. Every other field/item is a deep copy of the
        # original independent view; the old report on disk is never modified.
        current = copy.deepcopy(independent)
        current['items'][candidates[0]]['links'][0]['lawVersionHash'] = AFTER_VERSION_HASH
        return current, []
    except (KeyError, TypeError, ValueError, OSError) as exc:
        return independent, ['commerce paint source continuation: ' + str(exc)]
