"""Actual controlled selector regression for independently reviewed MEM10 repair."""
from datetime import date
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/v4'))
from basis_refs import project_basis_reference
from major_criteria import public_projection

KID = 'K_XLSX_WEB_H_B3F07B77A1834B489F43F05A0D'
HID = 'H_B3F07B77A1834B489F43F05A0D'


class Mem10CatalogIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = public_projection(ROOT / 'knowledge', as_of=date(2026, 9, 30))
        cls.after = public_projection(ROOT / 'knowledge', as_of=date(2026, 10, 1))
        cls.link = json.loads((ROOT / 'knowledge/links' / (KID + '.json')).read_text())

    def test_repaired_selector_retains_exact_light_industry_subitem_scope(self):
        rows = [r for r in self.after['topic']['associations'] if r['linkId'] == KID]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['clauseId'], 'C_PDDB_8')
        self.assertEqual(rows[0]['hazardId'], HID)
        self.assertEqual(rows[0]['applicability'], self.link['applicability'])
        self.assertIn('轻工企业', rows[0]['applicability'])
        self.assertIn('第八条第（七）项', rows[0]['applicability'])
        self.assertIn('不将其他分项自动套用', rows[0]['applicability'])
        basis = project_basis_reference(self.link, 'c0000')
        self.assertEqual(basis['applicability'], rows[0]['applicability'])
        self.assertEqual(basis['jurisdictionCode'], rows[0]['jurisdictionCode'])

    def test_new_review_does_not_backdate_topic_eligibility(self):
        self.assertNotIn(KID, {r['linkId'] for r in self.before['topic']['associations']})
        self.assertIn(KID, {r['linkId'] for r in self.after['topic']['associations']})
        self.assertEqual(self.before['topic']['coverage']['excludedAssociationCount'],
                         self.after['topic']['coverage']['excludedAssociationCount'] + 1)

    def test_known_wrong_and_fragment_texts_never_become_catalog_body(self):
        excluded_hazards = {'H_366610E8AA084C77844EFFBAAD', 'H_68196C0A0FBDDAF0354E0F71',
                            'H_B552B08A4FD28A8770CDC2BB', 'H_B0B7C75B5F0D423386A84AB73D'}
        for projection in (self.before, self.after):
            ids = {c['clauseId'] for s in projection['catalog']['standards'] for c in s['clauses']}
            self.assertTrue({'C_GB45067_4_2', 'C_GB45067_4_6', 'C_GB45067_4_8', 'C_GB45067_4_9'} <= ids)
            self.assertFalse({'C_MEM10_13', 'C_MEM10_4_2', 'C_MEM10_8_7'} & ids)
            self.assertFalse(excluded_hazards & set(projection['topic']['hazardIds']))
            self.assertFalse(projection['catalog']['allIndustryCoverage'])
            self.assertTrue(projection['catalog']['wholeNormNotFieldFinding'])


if __name__ == '__main__':
    unittest.main()
