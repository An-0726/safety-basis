from remaining_clause_fixture import pre_remaining_source_bytes
"""Exact post-PR105 integration contract; no new Gate or cohort authorizations."""
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import unittest

from common_hazards_fixture import ADMITTED_IDS, ADDED_IDS, pre_common_gate
from flange_scope_fixture import pre_flange_source_bytes
from occupational_citation_fixture import pre_occupational_source_bytes
from training_citation_fixture import pre_training_source_hashes
ROOT = Path(__file__).resolve().parents[3]
KNOW = ROOT / 'knowledge'
sys.path.insert(0, str(ROOT / 'tools/v4'))
from release_gate_core import evaluate_release_gate
BASELINE = json.loads((Path(__file__).parent / 'fixtures' /
                       'common_hazards_published_baseline_20261003.json').read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


class CommonHazardsIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = {day: evaluate_release_gate(KNOW, date.fromisoformat(day))
                       for day in ('2026-10-02', '2026-10-03')}

    def assert_exact_delta(self, gate):
        self.assertTrue(ADMITTED_IDS <= gate.eligible_hazards)
        self.assertTrue(ADDED_IDS['links'] <= gate.eligible_links)
        inherited = pre_common_gate(gate)
        public_links = {kid for kid in inherited.eligible_links
                        if inherited.links[kid]['hazardId'] in inherited.eligible_hazards}
        for values, key in [(inherited.eligible_hazards, 'publishedHazards'),
                            (inherited.eligible_links, 'rawGateLinks'),
                            (public_links, 'publishedLinks')]:
            self.assertEqual(len(values), BASELINE[key]['count'])
            self.assertEqual(digest(sorted(values)), BASELINE[key]['idsSha256'])
        self.assertEqual(len(gate.eligible_hazards), 1671)
        self.assertEqual(len({kid for kid in gate.eligible_links
                              if gate.links[kid]['hazardId'] in gate.eligible_hazards}), 1817)

    def test_both_dates_preserve_exact_1665_hazards_and_add_only_six(self):
        for day, gate in self.results.items():
            with self.subTest(day=day):
                self.assert_exact_delta(gate)

    def test_every_inherited_public_hazard_source_file_is_byte_identical(self):
        inherited = pre_common_gate(self.results['2026-10-03']).eligible_hazards
        paths = [f'knowledge/hazards/{hid}.json' for hid in sorted(inherited)]
        # Compose the disjoint exact inverses of the reviewed flange, training,
        # and occupational repairs. Preserve the original historical digest;
        # each adapter rejects unexpected bytes and leaves unknown edits visible.
        hashes = {p: hashlib.sha256(pre_flange_source_bytes(
            p, pre_occupational_source_bytes(p, pre_remaining_source_bytes(p, (ROOT / p).read_bytes())))).hexdigest() for p in paths}
        self.assertEqual(digest(pre_training_source_hashes(hashes)), BASELINE['inheritedHazardSourceFilesSha256'])

    def test_final_independent_reviewed_field_hashes_remain_exact(self):
        reviewed = json.loads((ROOT / 'docs/common-hazards-final-field-review-20261003.json').read_text())
        for record in reviewed['records']:
            self.assertEqual(hashlib.sha256((ROOT / record['path']).read_bytes()).hexdigest(),
                             record['fileSha256'], record['path'])

    def test_unknown_addition_or_unrelated_loss_cannot_pass_exact_delta(self):
        for add, remove in [('H_UNREVIEWED', None), (None, 'H001'), ('H_UNREVIEWED', 'H001')]:
            altered = copy.deepcopy(self.results['2026-10-03'])
            if add:
                altered.eligible_hazards.add(add)
            if remove:
                altered.eligible_hazards.remove(remove)
            with self.subTest(add=add, remove=remove), self.assertRaises(AssertionError):
                self.assert_exact_delta(altered)

    def test_pr105_withdrawn_hazard_cannot_be_restored_as_an_unrelated_swap(self):
        altered = copy.deepcopy(self.results['2026-10-03'])
        altered.eligible_hazards.add('H052')
        altered.eligible_hazards.remove('H001')
        with self.assertRaises(AssertionError):
            self.assert_exact_delta(altered)


if __name__ == '__main__':
    unittest.main()
