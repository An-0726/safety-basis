"""Knowledge closeout coverage and the real 2026-11-01 version boundary."""
from datetime import date
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('knowledge_closeout', ROOT / 'tools/checks/knowledge_closeout.py')
closeout = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(closeout)


class KnowledgeCloseoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit, cls.candidates = closeout.build_audit(ROOT / 'knowledge', date(2026, 11, 8), date(2026, 10, 16))

    def test_every_proposed_has_one_traceable_action_and_no_publication(self):
        hazards, _ = closeout.read_records(ROOT / 'knowledge', 'hazards')
        expected = {hid for hid, h in hazards.items() if h['lifecycle'] == 'proposed'}
        actual = [r['hazardId'] for r in self.candidates]
        self.assertEqual(set(actual), expected)
        self.assertEqual(len(actual), len(set(actual)))
        self.assertEqual(len(actual), 265)
        self.assertNotIn('H_0A53849CB39848628056FDADEB', expected)
        self.assertFalse(expected & set(self.audit['currentProjection']['ids']['hazards']))
        for row in self.candidates:
            self.assertTrue(row['minimumEvidenceActions'])
            self.assertTrue(row['factConfirmation'])
            self.assertEqual(row['disposition'], 'retain_proposed')
            self.assertEqual(row['contentHash'], closeout.content_hash(hazards[row['hazardId']]))

    def test_active_reconciliation_and_existing_rejections_are_retained(self):
        current = set(self.audit['currentProjection']['ids']['hazards'])
        excluded = {r['hazardId'] for r in self.audit['activeExcluded']}
        self.assertFalse(current & excluded)
        self.assertEqual(len(current) + len(excluded), self.audit['lifecycle']['active'])
        self.assertEqual((len(current), len(excluded)), (1766, 11))
        self.assertTrue({'H_0A53849CB39848628056FDADEB',
                         'H_HAZCHEM_COMMUNICATION_DEVICE_INOPERABLE'} <= current)
        self.assertIn('H_CE94D2ACC8C544BCA0FB0AA026', excluded)
        self.assertEqual(self.audit['validationErrors'], [])
        for row in self.audit['activeExcluded']:
            self.assertNotIn('保持proposed', ' '.join(row['minimumEvidenceActions']))

    def test_projection_requires_both_link_and_hazard_admission(self):
        gate = SimpleNamespace(eligible_links={'good', 'orphan'}, eligible_hazards={'H1'})
        projected = closeout.project(gate, {'good': {'hazardId': 'H1', 'clauseId': 'C1'},
                                          'orphan': {'hazardId': 'H2', 'clauseId': 'C2'}},
                                    {'C1': {'lawVersionId': 'V1'}, 'C2': {'lawVersionId': 'V2'}})
        self.assertEqual(projected['ids']['links'], ['good'])
        self.assertEqual(projected['ids']['lawVersions'], ['V1'])

    def test_standard_text_variants_do_not_skip_replacement_leads(self):
        self.assertEqual(closeout.standard_refs('旧 GB / T 12801—2008；GBZ/T 205-2007；AQ 3013-2008'),
                         {'GB/T12801-2008', 'GBZ/T205-2007', 'AQ3013-2008'})

    def test_fingerprint_and_outputs_detect_source_or_queue_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            path = directory / 'entity.json'
            path.write_text('{"id":"A"}')
            before = closeout.source_fingerprint(directory)
            path.write_text('{"id":"B"}')
            self.assertNotEqual(before, closeout.source_fingerprint(directory))
        outputs = closeout.output_files(self.audit, self.candidates)
        rows = [json.loads(line) for line in outputs['CANDIDATE_INVENTORY_20261108.jsonl'].splitlines()]
        self.assertEqual(len(rows), 265)
        self.assertEqual(len(self.audit['priorityHazardIds']), 40)
        self.assertEqual(len(set(self.audit['priorityHazardIds'])), 40)


class LightningSuccessorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = closeout.evaluate_release_gate(ROOT / 'knowledge', date(2026, 10, 31))
        cls.after = closeout.evaluate_release_gate(ROOT / 'knowledge', date(2026, 11, 1))

    def test_effective_day_swaps_versions_without_public_rule_loss(self):
        old = 'LV_CMA_LIGHTNING_MANAGEMENT_2025'
        new = 'LV_CMA_LIGHTNING_MANAGEMENT_2026_AMENDED'
        self.assertTrue(self.before.law_versions[old]['supports_current'])
        self.assertFalse(self.before.law_versions[new]['supports_current'])
        self.assertFalse(self.after.law_versions[old]['supports_current'])
        self.assertTrue(self.after.law_versions[new]['supports_current'])
        hid = 'H_89016FC0F3E849C2B8B8755C35'
        self.assertIn(hid, self.before.eligible_hazards)
        self.assertIn(hid, self.after.eligible_hazards)
        self.assertEqual(self.before.eligible_hazards, self.after.eligible_hazards)
        for article in (13, 17):
            kid = f'K_CLOSEOUT_{hid}_C_CMA_2026_AMENDED_{article}'
            self.assertNotIn(kid, self.before.eligible_links)
            self.assertIn(kid, self.after.eligible_links)

    def test_revision_preserves_exact_detection_obligations_and_roles(self):
        for article, role in ((13, 'direct'), (17, 'supporting')):
            old = json.loads((ROOT / f'knowledge/clauses/C_CMA44_2025_{article}.json').read_text())
            new = json.loads((ROOT / f'knowledge/clauses/C_CMA_2026_AMENDED_{article}.json').read_text())
            self.assertEqual(old['quote'], new['quote'])
            kid = f'K_CLOSEOUT_H_89016FC0F3E849C2B8B8755C35_C_CMA_2026_AMENDED_{article}'
            link = json.loads((ROOT / f'knowledge/links/{kid}.json').read_text())
            self.assertEqual(link['role'], role)
            self.assertIn('不得', link['applicability'])
            self.assertIn('重大事故隐患', link['applicability'])


if __name__ == '__main__':
    unittest.main()
