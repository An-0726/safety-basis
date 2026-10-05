"""Reviewed administrative reading stays separate from current C/H/K eligibility."""
from commerce_cohort_fixture import pre_commerce_manifest
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
from official_clause_cohort_fixture import pre_official_repo_root
# Preserve the dated cohort against its exact, fail-closed batch predecessor.
ROOT = pre_official_repo_root(ROOT)
K, P = ROOT / 'knowledge', ROOT / 'source/publication'
sys.path.insert(0, str(ROOT / 'tools/v4'))
import major_criteria_reading as reading
from release_gate_core import evaluate_release_gate

IDS = ('READING_CIVIL_EXPLOSIVES_2024', 'READING_FIREWORKS_2017')


class CivilFireworksReadingSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = reading.load_records(K)

    def test_six_exact_independently_reviewed_files_and_bounded_batch(self):
        fixture = reading.read(ROOT / 'tests/private/civil-fireworks-reference-reading-source-v1.json')
        self.assertEqual(len(fixture['files']), 6)
        for row in fixture['files']:
            with self.subTest(path=row['path']):
                self.assertEqual(hashlib.sha256((ROOT / row['path']).read_bytes()).hexdigest(), row['sha256'])
        self.assertEqual(fixture['currentCanonicalDelta'], dict(clauses=0, hazards=0, links=0, evidence=0))
        manifest = pre_commerce_manifest(reading.read(K / 'manifest.json'))
        self.assertEqual(sum(b['id'] == fixture['batch'] for b in manifest['batches']), 1)
        self.assertEqual(manifest['batch'], fixture['batch'])

    def test_civil_complete_items_and_six_inline_notes_preserve_exceptions(self):
        doc = self.records[IDS[0]]['documents'][0]
        items = reading.items(doc)
        self.assertEqual(doc['firstLevelItemCount'], 17)
        self.assertEqual(len(items), 17)
        self.assertEqual(sum(i['quote'].count('注1：') + i['quote'].count('注2：') + i['quote'].count('注：') for i in items), 6)
        for index, exact in [(2, '任职之日起6个月后'), (4, '可能导致本单元或更大范围安全失控'),
                             (12, '乙级以上（含乙级）'), (13, '不含GB28263中的二类技改项目'),
                             (14, '报废半年后仍未实施销爆处理')]:
            self.assertIn(exact, items[index]['quote'])
        notes = {n['id']: n for n in doc['officialClarifications']}
        self.assertEqual(len(notes), 7)
        self.assertEqual({n['id'] for n in notes.values() if n['textMode'] == 'official_link_pending'},
                         {'RN_CIVIL_3', 'RN_CIVIL_4', 'RN_CIVIL_15'})
        self.assertIn('不能换算成180天', notes['RN_CIVIL_15']['text'])
        self.assertIn('不因此取得6个月宽限', notes['RN_CIVIL_3']['text'])

    def test_fireworks_twenty_items_variant_and_use_evidence_do_not_expand_scope(self):
        record = self.records[IDS[1]]
        doc = record['documents'][0]
        items = reading.items(doc)
        self.assertEqual((doc['firstLevelItemCount'], len(items)), (20, 20))
        self.assertIn('其它爆炸物', items[18]['quote'])
        self.assertEqual(items[19]['quote'], '二十、零售点与居民居住场所设置在同一建筑物内或者在零售场所使用明火。')
        self.assertEqual(len(doc['officialClarifications']), 1)
        variant = doc['officialClarifications'][0]
        self.assertEqual(variant['appliesToItemIds'], ['RI_FIREWORKS_2017_I19'])
        self.assertIn('其他爆炸物', variant['text'])
        locator = record['evidence']['E_READ_FIREWORKS_USE']['locator']
        self.assertIn('第112项（4月13日）明确引用烟花标准第二十项', locator)
        self.assertIn('第115项（4月20日）引用标准名称', locator)

    def test_both_exact_scope_and_text_reviews_bind_complete_selected_bodies(self):
        for gid in IDS:
            with self.subTest(group=gid):
                record = self.records[gid]
                scope = reading.read(K / reading.NAMESPACE / 'scope-reviews' / (gid + '.json'))
                self.assertEqual({k: scope[k] for k in reading.review_bindings(record, K, P)},
                                 reading.review_bindings(record, K, P))
                self.assertFalse(scope['currentDeterminationBasis'])
                doc = record['documents'][0]
                review = reading.read(K / reading.NAMESPACE / 'text-reviews' / (doc['directoryReferenceId'] + '.json'))
                self.assertEqual(len(review['itemDecisions']), doc['firstLevelItemCount'])
                self.assertTrue(reading._text_review_ok(doc, review, date(2026, 10, 1)))

    def test_unknown_dates_still_fail_current_basis_gate_without_any_new_clauses(self):
        vids = {self.records[gid]['documents'][0]['sourceIdentity']['lawVersionId'] for gid in IDS}
        gate = evaluate_release_gate(K, date(2026, 10, 1))
        for vid in vids:
            self.assertIsNone(reading.read(K / 'law-versions' / (vid + '.json'))['effectiveDate'])
            self.assertFalse(gate.law_versions[vid]['supports_current'])
        self.assertEqual([p.name for p in (K / 'clauses').glob('*.json') if reading.read(p).get('lawVersionId') in vids], [])

    def test_final_reading_counts_are_separate_and_never_backdated(self):
        for day, expected in [(date(2026, 9, 30), (0, 0, 0)), (date(2026, 10, 1), (3, 4, 109))]:
            public = reading.public_projection(K, P, as_of=day)['public']
            self.assertEqual(tuple(public[k] for k in ('readingGroupCount', 'sourceDocumentCount', 'firstLevelItemCount')), expected)
            self.assertFalse(public['currentDeterminationBasis'])
            self.assertFalse(public['standaloneDeterminationAllowed'])
            self.assertEqual((public['reviewedCurrentClauseCount'], public['directHazardCount']), (0, 0))

    def test_changed_exception_or_scope_never_uses_existing_approval(self):
        mutations = [
            (IDS[0], lambda r: r['documents'][0]['sections'][0]['items'][13].update(quote='Altered missing exception')),
            (IDS[1], lambda r: r['documents'][0]['sections'][0]['items'].pop()),
            (IDS[1], lambda r: r['documents'][0]['sourceIdentity'].update(effectiveDate='2018-01-01')),
        ]
        for gid, mutate in mutations:
            with self.subTest(group=gid):
                records = copy.deepcopy(self.records)
                mutate(records[gid])
                with patch.object(reading, 'load_records', return_value=records):
                    public = reading.public_projection(K, P, as_of=date(2026, 10, 1))['public']
                self.assertNotIn(gid, {g['id'] for g in public['readingGroups']})
                self.assertIn('READING_NONCOAL_2022_2024', {g['id'] for g in public['readingGroups']})


if __name__ == '__main__':
    unittest.main()
