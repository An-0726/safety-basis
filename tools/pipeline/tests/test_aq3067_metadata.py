"""Guard one separately reviewed metadata-only identity and locator index.

These checks do not approve normative text or determine any site hazard.
"""
from commerce_cohort_fixture import pre_commerce_manifest
import json
from pathlib import Path
import re
import sys
import unittest
from power_fixture import CLAUSES as POWER_CLAUSES, EVIDENCE as POWER_EVIDENCE, VERSION as POWER_VERSION
from coal_fixture import CLAUSES as COAL_CLAUSES, EVIDENCE as COAL_EVIDENCE, VERSION as COAL_VERSION
from construction_fixture import CLAUSES as CONSTRUCTION_CLAUSES, EVIDENCE as CONSTRUCTION_EVIDENCE
from city_gas_fixture import CLAUSES as GAS_CLAUSES, EVIDENCE as GAS_EVIDENCE
from sector_directory_fixture import LAWS as SECTOR_LAWS, VERSIONS as SECTOR_VERSIONS, EVIDENCE as SECTOR_EVIDENCE

ROOT = Path(__file__).resolve().parents[3]
from official_clause_cohort_fixture import pre_official_repo_root
# Preserve the dated cohort against its exact, fail-closed batch predecessor.
ROOT = pre_official_repo_root(ROOT)
KNOW = ROOT / 'knowledge'
sys.path.insert(0, str(ROOT / 'tools/v4'))
from canonical import content_hash

LF, LV, E = 'LF_AQ3067', 'LV_AQ3067_2026', 'E_AQ3067_2026_MEM_PDF'
REF = 'REF_AQ3067_2026'
NS = 'major-criteria-references/v1'
PDF_HASH = 'b2df271f61ac0b121e952b0fe890adaa85751df677a986de60fb7fa927016b89'
RECORD_HASH = 'c996e648b9cbcb9b165bcc46f9fb85f09040c7a99f5f7b50de96d1c2113dd330'
TITLE = '化工和危险化学品生产经营企业重大生产安全事故隐患判定准则'
LANDING = 'https://www.mem.gov.cn/fw/flfgbz/bz/bzwb/202603/t20260325_598035.shtml'
PDF = 'https://www.mem.gov.cn/fw/flfgbz/bz/bzwb/202603/W020260325395148825942.pdf'


def read(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


def entity(kind, ident):
    return read(f'knowledge/{kind}/{ident}.json')


def one(rows, key, value):
    found = [r for r in rows if r.get(key) == value]
    if len(found) != 1:
        raise AssertionError((key, value, len(found)))
    return found[0]


class AQ3067MetadataBoundaryTests(unittest.TestCase):
    def test_exact_identity_dates_scope_and_no_inferred_succession(self):
        law, version = entity('laws', LF), entity('law-versions', LV)
        self.assertEqual(law['canonicalName'], TITLE)
        self.assertEqual(law['issuer'], '应急管理部')
        self.assertEqual(law['documentKind'], '强制性行业标准')
        self.assertEqual(version['documentNumber'], 'AQ 3067-2026')
        self.assertEqual(version['publicationDate'], '2026-03-09')
        self.assertEqual(version['effectiveDate'], '2026-09-30')
        self.assertEqual(version['endDate'], '')
        self.assertEqual(version['validityStatus'], 'active')
        self.assertEqual(version['scope'], '全国；危险化学品生产、经营（有储存）企业及化工（含医药）企业')
        self.assertEqual(version['sourceUrl'], LANDING)
        for path in (KNOW / 'successions').glob('*.json'):
            self.assertNotIn(LV, json.loads(path.read_text()).values())

    def test_only_metadata_reviewed_with_actual_october_checked_at(self):
        evidence = entity('evidence', E)
        self.assertEqual(evidence['url'], PDF)
        self.assertEqual(evidence['tier'], 'authoritative-public')
        self.assertEqual(evidence['snapshotSha256'], PDF_HASH)
        for kind, ident in [('laws', LF), ('law-versions', LV)]:
            obj, review = entity(kind, ident), entity('reviews/' + kind, ident)
            self.assertEqual(review['decision'], 'verified')
            self.assertEqual(review['checkedAt'][:10], '2026-10-01')
            self.assertEqual(review['reviewScope'], 'identity_dates_scope_official_source_metadata_only')
            self.assertIs(review['fullQuotePublicationReady'], False)
            self.assertEqual(review['reviewedContentHash'], content_hash(obj))
            self.assertEqual(set(review['reviewedFields']), set(obj))
            self.assertEqual(review['evidenceRefs'], [E])
            self.assertEqual(review['sourceHashes'], {E: content_hash(evidence), 'officialPdfSha256': PDF_HASH})

    def test_exact_short_locator_topics_not_conditions_or_quotes(self):
        record = entity(NS + '/records', REF)
        self.assertEqual(content_hash(record), RECORD_HASH)
        expected = [f'5.{group}.{n}' for group, count in enumerate([5, 10, 6, 9, 12, 4, 7], 1)
                    for n in range(1, count + 1)]
        self.assertEqual([r['article'] for r in record['searchTopics']], expected)
        for row in record['searchTopics']:
            self.assertEqual(set(row), {'article', 'searchTopic'})
            self.assertRegex(row['searchTopic'], r'^[\u3400-\u9fffA-Za-z0-9 ]{1,16}$')
        self.assertEqual(record['officialLink'], LANDING)
        self.assertEqual(record['officialTextLink'], PDF)
        self.assertEqual(record['contentKind'], 'reference_only')
        self.assertNotIn('quote', record)

    def test_reference_review_binds_all_metadata_dependencies(self):
        record, review = entity(NS + '/records', REF), entity(NS + '/reviews', REF)
        deps = {
            'law-versions/' + LV: entity('law-versions', LV),
            'reviews/law-versions/' + LV: entity('reviews/law-versions', LV),
            'laws/' + LF: entity('laws', LF),
            'reviews/laws/' + LF: entity('reviews/laws', LF),
            'evidence/' + E: entity('evidence', E),
            'publication/law-index': one(read('source/publication/law-index.json'), 'id', LV),
            'publication/fulltext': one(read('source/publication/fulltext/catalog.json')['documents'], 'versionId', LV),
            'publication/fulltext-search': one(read('source/publication/fulltext/search-index.json')['documents'], 'versionId', LV),
        }
        self.assertEqual(review['reviewedContentHash'], content_hash(record))
        self.assertEqual(review['dependencyFingerprint'], content_hash(deps))
        self.assertEqual(review['checkedAt'][:10], '2026-10-01')
        self.assertEqual(review['reviewScope'], 'identity_dates_official_links_short_search_topics_only')
        self.assertIs(review['fullQuotePublicationReady'], False)

    def test_link_only_source_has_no_full_text_or_hazard_claim(self):
        catalog = read('source/publication/fulltext/catalog.json')
        search = read('source/publication/fulltext/search-index.json')
        self.assertEqual(catalog['asOf'], '2026-10-01')
        self.assertEqual(search['asOf'], catalog['asOf'])
        doc = one(catalog['documents'], 'versionId', LV)
        self.assertEqual(doc['textMode'], 'link_only')
        self.assertEqual(doc['publicationPermission'], 'metadata_only')
        self.assertIs(doc['fullTextReviewed'], False)
        self.assertIsNone(doc['textPath'])
        self.assertEqual(doc['fullTextSha256'], '')
        self.assertEqual(one(search['documents'], 'versionId', LV),
                         {k: doc[k] for k in ('lawId', 'versionId', 'title', 'version', 'textMode', 'textPath')})
        row = one(read('source/publication/law-index.json'), 'id', LV)
        self.assertEqual(row['clauseRefs'], [])
        self.assertEqual(row['clauseCount'], 0)
        self.assertEqual(row['hazardCount'], 0)
        self.assertEqual(row['replaces'], [])
        self.assertEqual(row['replacedBy'], [])
        for path in (KNOW / 'clauses').glob('*.json'):
            self.assertNotEqual(json.loads(path.read_text()).get('lawVersionId'), LV)
        for folder in ('clauses', 'hazards', 'links'):
            self.assertFalse(list((KNOW / 'reviews' / folder).glob('*AQ3067*')))

    def test_manifest_records_exact_metadata_additions_only(self):
        manifest = pre_commerce_manifest(read('knowledge/manifest.json'))
        batch = one(manifest['batches'], 'id', 'aq3067-metadata-reference-only-20261001')
        self.assertEqual({k: batch[k] for k in ('lawsAdded', 'lawVersionsAdded', 'evidenceAdded',
                                              'identityMetadataReviewsAdded', 'versionMetadataReviewsAdded')},
                         {'lawsAdded': 1, 'lawVersionsAdded': 1, 'evidenceAdded': 1,
                          'identityMetadataReviewsAdded': 1, 'versionMetadataReviewsAdded': 1})
        self.assertEqual(manifest['counts']['laws'] - len(SECTOR_LAWS), 110)
        self.assertEqual(manifest['counts']['lawVersions'] - len(SECTOR_VERSIONS), 113)
        self.assertEqual(manifest['counts']['evidence'] - len(SECTOR_EVIDENCE) - len(GAS_EVIDENCE) - len(CONSTRUCTION_EVIDENCE) - len(COAL_EVIDENCE) - len(POWER_EVIDENCE), 1265)
        self.assertEqual(manifest['counts']['clauses'] - len(GAS_CLAUSES) - len(CONSTRUCTION_CLAUSES) - len(COAL_CLAUSES) - len(POWER_CLAUSES), 3011)
        self.assertEqual(manifest['counts']['hazards'], 2131)
        self.assertEqual(manifest['counts']['links'], 1971)
        self.assertEqual(manifest['counts']['successions'], 26)


if __name__ == '__main__':
    unittest.main()
