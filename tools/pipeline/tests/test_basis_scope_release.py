"""Ordinary basisRefs retain exact per-K scope, including same-C associations."""
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'v4'))
from basis_refs import project_basis_reference
from canonical import content_hash
import test_field_profiles as fixtures
import test_field_profile_release as release_fixtures


class BasisScopeReleaseTests(unittest.TestCase):
    fixture_type = fixtures.FieldProfileTests
    build = release_fixtures.FieldProfileReleaseTests.build
    read = release_fixtures.FieldProfileReleaseTests.read
    reseal = release_fixtures.FieldProfileReleaseTests.reseal
    verify = release_fixtures.FieldProfileReleaseTests.verify

    def setUp(self):
        release_fixtures.FieldProfileReleaseTests.setUp(self)
        self.f = self.fixture

    def add_link(self, link, hazard, clause):
        self.f.put('links/' + link['id'] + '.json', link)
        self.f.put('reviews/links/' + link['id'] + '.json', {
            'entityId': link['id'], 'decision': 'verified',
            'reviewedContentHash': content_hash(link), 'reason': 'Synthetic exact scope review',
            'contextHashes': {'hazard': content_hash(hazard), 'clause': content_hash(clause)}})

    def hazard_rows(self):
        return {row['id']: row for row in self.read('data/hazards/h0000.json')['records']}

    def test_multiple_clauses_same_clause_multiple_links_and_other_hazards_do_not_mix_scope(self):
        f = self.f
        f.link['applicability'] = 'Light industry only; article 8 item (7); defective battery storage'
        f.link['jurisdictionCode'] = 'CN'
        f.entity('links', f.link)
        second_c = {**f.clause, 'id': 'C_SECOND', 'articlePath': '2', 'quote': '2 Synthetic other requirement'}
        f.entity('clauses', second_c)
        second = {**f.link, 'id': 'K_SECOND', 'clauseId': second_c['id'], 'applicability': 'Pressure equipment only', 'jurisdictionCode': None}
        same_c = {**f.link, 'id': 'K_SAME_C', 'applicability': 'Independent subject and trigger on same clause'}
        other_h = {**f.hazard, 'id': 'H_OTHER', 'title': 'Other synthetic hazard'}
        f.entity('hazards', other_h)
        other = {**f.link, 'id': 'K_OTHER', 'hazardId': other_h['id'], 'applicability': 'Other hazard only'}
        for link, hazard, clause in [(second, f.hazard, second_c), (same_c, f.hazard, f.clause), (other, other_h, f.clause)]:
            self.add_link(link, hazard, clause)
        f.approve_synthetic()
        self.build()
        rows = self.hazard_rows()
        actual = {r['linkId']: r for r in rows['H_TEST']['basisRefs']}
        self.assertEqual(set(actual), {'K_TEST', 'K_SECOND', 'K_SAME_C'})
        for link in (f.link, second, same_c):
            self.assertEqual(actual[link['id']]['applicability'], link['applicability'])
            self.assertEqual(actual[link['id']]['clauseId'], link['clauseId'])
            self.assertEqual(actual[link['id']]['jurisdictionCode'], link.get('jurisdictionCode'))
        self.assertEqual(rows['H_OTHER']['basisRefs'][0]['applicability'], 'Other hazard only')
        self.assertEqual(rows['H_TEST']['conditions'], f.hazard['conditions'])
        self.assertEqual(len(rows['H_TEST']['basisRefs']), 3)
        rc, report = self.verify(); self.assertEqual(rc, 0, report)

    def test_verbatim_scope_and_missing_jurisdiction_are_not_inferred(self):
        link = {**self.f.link, 'applicability': '  Exact scope\nSecond line  '}
        row = project_basis_reference(link, 'c0000')
        self.assertEqual(row['applicability'], link['applicability'])
        self.assertIsNone(row['jurisdictionCode'])
        self.assertEqual(set(row), {'linkId', 'clauseId', 'clauseShard', 'role', 'applicability', 'jurisdictionCode'})

    def test_invalid_or_private_new_scope_fields_abort(self):
        for key, values in [('applicability', [None, '', 2, {}, '/workspace/private/report', 'C:\\private\\report']),
                            ('jurisdictionCode', [False, {}, '/home/private/report']),
                            ('id', ['', '/tmp/link'])]:
            for value in values:
                with self.subTest(key=key, value=value):
                    with self.assertRaisesRegex(ValueError, 'BASIS_PUBLIC_FIELD_UNSAFE'):
                        project_basis_reference({**self.f.link, key: value}, 'c0000')

    def test_resealed_scope_or_link_identity_tamper_cannot_hide_behind_same_clause_role(self):
        self.build()
        base = self.read('data/hazards/h0000.json')
        for key, value in [('applicability', 'All industries without conditions'),
                           ('linkId', 'K_OTHER'), ('jurisdictionCode', 'CN-32')]:
            altered = copy.deepcopy(base)
            altered['records'][0]['basisRefs'][0][key] = value
            (self.out / 'data/hazards/h0000.json').write_text(json.dumps(altered))
            self.reseal()
            rc, report = self.verify(); self.assertEqual(rc, 1, report)
            self.assertTrue(any('逐K依据身份或适用范围' in error for error in report['errors']), report)

    def test_missing_boundary_and_cross_link_scope_swap_are_rejected(self):
        f = self.f
        second = {**f.link, 'id': 'K_SECOND', 'applicability': 'Other independent trigger'}
        self.add_link(second, f.hazard, f.clause)
        f.approve_synthetic()
        self.build()
        base = self.read('data/hazards/h0000.json')
        variants = []
        stripped = copy.deepcopy(base)
        for ref in stripped['records'][0]['basisRefs']:
            for key in ('linkId', 'applicability', 'jurisdictionCode'):
                ref.pop(key)
        variants.append(stripped)
        swapped = copy.deepcopy(base)
        refs = swapped['records'][0]['basisRefs']
        refs[0]['applicability'], refs[1]['applicability'] = refs[1]['applicability'], refs[0]['applicability']
        variants.append(swapped)
        for altered in variants:
            (self.out / 'data/hazards/h0000.json').write_text(json.dumps(altered))
            self.reseal()
            rc, report = self.verify(); self.assertEqual(rc, 1, report)
            self.assertTrue(any('逐K依据身份或适用范围' in error for error in report['errors']), report)

    def test_proposed_or_unreviewed_link_does_not_supply_boundary(self):
        f = self.f
        second = {**f.link, 'id': 'K_PROPOSED', 'applicability': 'Unapproved broad scope', 'lifecycle': 'proposed'}
        self.add_link(second, f.hazard, f.clause)
        f.approve_synthetic()
        self.build()
        self.assertEqual([r['linkId'] for r in self.hazard_rows()['H_TEST']['basisRefs']], ['K_TEST'])
        rc, report = self.verify(); self.assertEqual(rc, 0, report)


if __name__ == '__main__':
    unittest.main()
