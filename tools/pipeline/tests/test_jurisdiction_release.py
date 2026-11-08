"""Synthetic regional projection checks; no new legal facts or field findings."""
import copy
from itertools import permutations
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'v4'))
from canonical import content_hash
from jurisdiction import (JurisdictionError, basis_jurisdiction, candidate_scopes,
                          clause_jurisdiction, intersect_jurisdictions,
                          jurisdiction_code, region_label, version_jurisdiction,
                          version_scope_code)
import test_field_profiles as fixtures
import test_field_profile_release as release_fixtures


class JurisdictionContainmentTests(unittest.TestCase):
    def test_ancestor_containment_is_order_independent_and_national_does_not_widen(self):
        for codes in permutations(['CN', 'CN-32', 'CN-3201', 'CN-320102']):
            self.assertEqual(intersect_jurisdictions(*codes), 'CN-320102')
        self.assertEqual(intersect_jurisdictions('CN-3201', 'CN', 'CN-32'), 'CN-3201')

    def test_different_local_branches_conflict_instead_of_falling_back_to_national(self):
        for codes in [('CN-32', 'CN-33'), ('CN-3201', 'CN-3202'),
                      ('CN-320102', 'CN-320104')]:
            for ordered in [codes, tuple(reversed(codes))]:
                with self.assertRaisesRegex(JurisdictionError, 'JURISDICTION_CONFLICT'):
                    intersect_jurisdictions('CN', *ordered)

    def test_missing_metadata_is_unknown_and_invalid_codes_never_become_national(self):
        self.assertIsNone(intersect_jurisdictions(None, None))
        for value in [False, 32, {}, [], '中国', 'CN-XYZ', 'CN-3', 'CN-３２', '/home/private/source']:
            with self.subTest(value=value), self.assertRaises(JurisdictionError):
                jurisdiction_code(value)
        with self.assertRaisesRegex(JurisdictionError, 'JURISDICTION_MISSING'):
            version_jurisdiction({'scope': 'CN'}, {})
        self.assertEqual(jurisdiction_code('全国'), 'CN')
        self.assertEqual(region_label('CN-11'), 'CN-11')

    def test_only_a_whole_version_code_participates_and_prose_is_not_parsed(self):
        law = {'jurisdictionCode': 'CN-32', 'canonicalName': '南京 title does not decide scope'}
        for text in ['全国', '全国；按条款确认对象', '南京市行政区域', 'CN-3201（南京）']:
            with self.subTest(text=text):
                self.assertIsNone(version_scope_code(text))
                self.assertEqual(version_jurisdiction({'scope': text}, law), 'CN-32')
        self.assertEqual(version_jurisdiction({'scope': 'CN-3201'}, law), 'CN-3201')

    def test_each_reviewed_parent_can_narrow_broad_descendant_codes(self):
        for link, clause, version, law, expected in [
                ({'jurisdictionCode': 'CN'}, {'jurisdictionCode': 'CN'}, {'scope': 'CN'}, {'jurisdictionCode': 'CN-32'}, 'CN-32'),
                ({'jurisdictionCode': 'CN'}, {'jurisdictionCode': 'CN'}, {'scope': 'CN-3201'}, {'jurisdictionCode': 'CN'}, 'CN-3201'),
                ({'jurisdictionCode': 'CN'}, {'jurisdictionCode': 'CN-32'}, {'scope': 'CN'}, {'jurisdictionCode': 'CN'}, 'CN-32'),
                ({'jurisdictionCode': 'CN-3201'}, {}, {}, {'jurisdictionCode': 'CN'}, 'CN-3201'),
                ({'jurisdictionCode': '全国'}, {}, {}, {'jurisdictionCode': 'CN-32'}, 'CN-32')]:
            with self.subTest(expected=expected, link=link, clause=clause, version=version, law=law):
                before = copy.deepcopy([link, clause, version, law])
                self.assertEqual(basis_jurisdiction(link, clause, version, law), expected)
                self.assertEqual([link, clause, version, law], before)

    def test_local_link_does_not_relabel_the_shared_national_clause_or_version(self):
        law, version, clause, link = {'jurisdictionCode': 'CN'}, {}, {}, {'jurisdictionCode': 'CN-3201'}
        self.assertEqual(version_jurisdiction(version, law), 'CN')
        self.assertEqual(clause_jurisdiction(clause, version, law), 'CN')
        self.assertEqual(basis_jurisdiction(link, clause, version, law), 'CN-3201')

    def test_candidate_scope_uses_direct_and_fallback_but_never_supporting(self):
        self.assertEqual(candidate_scopes([
            {'role': 'direct', 'jurisdictionCode': 'CN-3201'},
            {'role': 'supporting', 'jurisdictionCode': 'CN'},
        ]), ['南京'])
        self.assertEqual(candidate_scopes([
            {'role': 'fallback', 'jurisdictionCode': 'CN-32'},
            {'role': 'supporting', 'jurisdictionCode': 'CN'},
        ]), ['江苏'])
        self.assertEqual(candidate_scopes([{'role': 'supporting', 'jurisdictionCode': 'CN'}]), [])
        self.assertEqual(candidate_scopes([
            {'role': 'direct', 'jurisdictionCode': 'CN'},
            {'role': 'direct', 'jurisdictionCode': 'CN-3201'},
        ]), ['全国', '南京'])


class JurisdictionReleaseTests(unittest.TestCase):
    fixture_type = fixtures.FieldProfileTests
    build = release_fixtures.FieldProfileReleaseTests.build
    read = release_fixtures.FieldProfileReleaseTests.read
    reseal = release_fixtures.FieldProfileReleaseTests.reseal
    verify = release_fixtures.FieldProfileReleaseTests.verify

    def setUp(self):
        release_fixtures.FieldProfileReleaseTests.setUp(self)
        self.f = self.fixture

    def refresh(self):
        f = self.f
        for group, value in [('laws', f.law), ('law-versions', f.version),
                             ('clauses', f.clause), ('links', f.link)]:
            f.entity(group, value)
        f.approve_synthetic()

    def add_national_supporting(self):
        f = self.f
        law = {**f.law, 'id': 'LF_NATIONAL', 'jurisdictionCode': 'CN'}
        version = {**f.version, 'id': 'LV_NATIONAL', 'lawId': law['id'], 'scope': 'CN'}
        clause = {**f.clause, 'id': 'C_NATIONAL', 'lawVersionId': version['id'], 'jurisdictionCode': 'CN'}
        link = {**f.link, 'id': 'K_SUPPORT', 'clauseId': clause['id'], 'jurisdictionCode': 'CN', 'role': 'supporting'}
        for group, value in [('laws', law), ('law-versions', version), ('clauses', clause)]:
            f.entity(group, value)
        f.put('links/' + link['id'] + '.json', link)
        f.put('reviews/links/' + link['id'] + '.json', {
            'entityId': link['id'], 'decision': 'verified', 'evidenceRefs': ['E_TEST'],
            'reviewedContentHash': content_hash(link), 'reason': 'Synthetic supporting basis review',
            'contextHashes': {'hazard': content_hash(f.hazard), 'clause': content_hash(clause)}})
        f.approve_synthetic()

    def assert_region_chain(self, *, candidate, basis, clause, law):
        self.assertEqual(self.read('data/search-index.json')[0]['scopes'], [candidate])
        hazard = self.read('data/hazards/h0000.json')['records'][0]
        ref = next(value for value in hazard['basisRefs'] if value['linkId'] == 'K_TEST')
        self.assertEqual(ref['jurisdictionCode'], basis)
        clauses = {value['id']: value for value in self.read('data/clauses/c0000.json')['records']}
        self.assertEqual(clauses['C_TEST']['region'], clause)
        laws = {value['id']: value for value in self.read('data/law-index.json')}
        self.assertEqual(laws['LV_TEST']['scope'], law)
        profile = self.read('data/field-profiles.json')['records'][0]
        self.assertEqual(profile['bases'][0]['jurisdictionCode'], basis)
        self.assertEqual(region_label(profile['bases'][0]['lawJurisdictionCode']), law)
        self.assertEqual(profile['bases'][0]['applicability'], self.f.link['applicability'])
        self.assertEqual(profile['sourceHazard']['conditions'], self.f.hazard['conditions'])
        rc, report = self.verify()
        self.assertEqual(rc, 0, report)

    def test_local_direct_and_national_supporting_keep_candidate_local(self):
        self.f.law['jurisdictionCode'] = 'CN-3201'
        self.f.version['scope'] = 'CN-3201'
        self.f.clause['jurisdictionCode'] = 'CN'
        self.f.link['jurisdictionCode'] = 'CN'
        self.refresh()
        self.add_national_supporting()
        self.build()
        self.assert_region_chain(candidate='南京', basis='CN-3201', clause='南京', law='南京')
        refs = self.read('data/hazards/h0000.json')['records'][0]['basisRefs']
        self.assertEqual(next(ref for ref in refs if ref['linkId'] == 'K_SUPPORT')['jurisdictionCode'], 'CN')

    def test_national_law_with_local_k_and_missing_c_code_stays_local_in_candidates(self):
        self.f.link['jurisdictionCode'] = 'CN-3201'
        self.refresh()
        self.build()
        self.assert_region_chain(candidate='南京', basis='CN-3201', clause='全国', law='全国')

    def test_local_law_parent_is_not_overridden_by_national_version_clause_or_link(self):
        self.f.law['jurisdictionCode'] = 'CN-32'
        self.f.version['scope'] = 'CN'
        self.f.clause['jurisdictionCode'] = 'CN'
        self.f.link['jurisdictionCode'] = 'CN'
        self.refresh()
        self.build()
        self.assert_region_chain(candidate='江苏', basis='CN-32', clause='江苏', law='江苏')

    def test_local_version_narrows_national_law_and_keeps_profile_join_consistent(self):
        self.f.version['scope'] = 'CN-3201'
        self.f.clause['jurisdictionCode'] = 'CN'
        self.f.link['jurisdictionCode'] = 'CN'
        self.refresh()
        self.build()
        self.assert_region_chain(candidate='南京', basis='CN-3201', clause='南京', law='南京')

    def test_fallback_qualifies_but_national_supporting_cannot_expand_it(self):
        self.f.link.update(role='fallback', jurisdictionCode='CN-32')
        self.refresh()
        self.add_national_supporting()
        self.build()
        self.assert_region_chain(candidate='江苏', basis='CN-32', clause='全国', law='全国')

    def test_conflicting_reviewed_local_codes_exclude_profile_and_abort_release(self):
        self.f.version['scope'] = 'CN-32'
        self.f.clause['jurisdictionCode'] = 'CN-33'
        self.f.link['jurisdictionCode'] = 'CN'
        self.refresh()
        projection = self.f.project()
        self.assertEqual(projection['public']['records'], [])
        self.assertTrue(any('JURISDICTION_CONFLICT' in reason
                            for item in projection['inventory']['excludedProfiles'] for reason in item['reasons']))
        with self.assertRaisesRegex(JurisdictionError, 'JURISDICTION_CONFLICT'):
            self.build()

    def test_resealed_regional_widening_in_any_public_projection_is_rejected(self):
        self.f.version['scope'] = 'CN-3201'
        self.refresh()
        self.build()
        cases = [
            ('data/search-index.json', lambda value: value[0], 'scopes', ['全国'], '搜索索引地域'),
            ('data/hazards/h0000.json', lambda value: value['records'][0]['basisRefs'][0], 'jurisdictionCode', 'CN', '逐K依据身份'),
            ('data/clauses/c0000.json', lambda value: value['records'][0], 'region', '全国', '条款地域'),
            ('data/law-index.json', lambda value: value[0], 'scope', '全国', '法规地域'),
            ('data/field-profiles.json', lambda value: value['records'][0]['bases'][0], 'jurisdictionCode', 'CN', '精确公开投影'),
            ('data/field-profiles.json', lambda value: value['records'][0]['bases'][0], 'lawJurisdictionCode', 'CN', '精确公开投影'),
        ]
        for rel, selected, key, value, message in cases:
            with self.subTest(file=rel, key=key):
                path = self.out / rel
                original = path.read_bytes()
                payload = json.loads(original)
                selected(payload)[key] = value
                path.write_text(json.dumps(payload), encoding='utf-8')
                self.reseal()
                rc, report = self.verify()
                self.assertEqual(rc, 1, report)
                self.assertTrue(any(message in error for error in report['errors']), report)
                self.assertFalse(any('哈希' in error or 'Hash' in error for error in report['errors']), report)
                path.write_bytes(original)


if __name__ == '__main__':
    unittest.main()
