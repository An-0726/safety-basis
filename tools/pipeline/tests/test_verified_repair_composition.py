"""Combined repaired source remains fail-closed under historical test projections.

Every assertion below exercises test-only adapters; none changes the production
Gate, the repaired entities, or any earlier golden expectation.
"""
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import unittest

from common_hazards_fixture import pre_common_gate, pre_common_inventory
from flange_scope_fixture import pre_flange_source_bytes, HAZARD_EDITS
from occupational_citation_fixture import (
    pre_occupational_gate, pre_occupational_inventory,
    pre_occupational_source_bytes, F as OCCUPATIONAL,
)
from training_citation_fixture import (
    pre_training_gate, pre_training_inventory,
    pre_training_source_hashes, F as TRAINING,
)
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/v4'))
from release_gate_core import evaluate_release_gate


def historical_hashes(raw_files):
    hashes = {path: hashlib.sha256(pre_flange_source_bytes(
        path, pre_occupational_source_bytes(path, raw))).hexdigest()
        for path, raw in raw_files.items()}
    return pre_training_source_hashes(hashes)


class VerifiedRepairCompositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = evaluate_release_gate(ROOT / 'knowledge', date(2026, 10, 3))

    def test_repaired_entity_cohorts_are_disjoint(self):
        cohorts = [set(HAZARD_EDITS), {r['path'] for r in TRAINING['entities']},
                   {r['path'] for r in OCCUPATIONAL['entities']}]
        for i, left in enumerate(cohorts):
            for right in cohorts[i + 1:]:
                self.assertFalse(left & right)

    def test_all_eleven_repaired_hazards_restore_only_their_exact_old_bytes(self):
        rows = list(HAZARD_EDITS.values()) + TRAINING['entities'] + OCCUPATIONAL['entities']
        rows = [r for r in rows if '/hazards/' in r['path']]
        self.assertEqual(len(rows), 11)
        for row in rows:
            path = row['path']
            raw = (ROOT / path).read_bytes()
            self.assertEqual(historical_hashes({path: raw}),
                             {path: hashlib.sha256(row['beforeFileText'].encode()).hexdigest()})
            with self.assertRaises(AssertionError):
                historical_hashes({path: raw + b' '})

    def test_unknown_source_bytes_remain_visible(self):
        path, raw = 'knowledge/hazards/H_UNREVIEWED.json', b'unknown change'
        self.assertEqual(historical_hashes({path: raw}),
                         {path: hashlib.sha256(raw).hexdigest()})

    def test_gate_inverses_commute_without_mutating_production_result(self):
        original = copy.deepcopy(self.gate)
        first = pre_training_gate(pre_occupational_gate(self.gate))
        second = pre_occupational_gate(pre_training_gate(self.gate))
        self.assertEqual(first.links, second.links)
        self.assertEqual(first.eligible_links, second.eligible_links)
        self.assertEqual(first.eligible_hazards, second.eligible_hazards)
        self.assertEqual(self.gate, original)

    def test_composed_gate_rejects_any_of_eight_wrong_repaired_links(self):
        ids = [r['linkId'] for r in TRAINING['fiveLinks']] + list(OCCUPATIONAL['gateLinkTransitions'])
        self.assertEqual(len(set(ids)), 8)
        for kid in ids:
            with self.subTest(link=kid):
                bad = copy.deepcopy(self.gate)
                bad.links[kid]['clauseId'] = 'C_UNKNOWN_MUTATION'
                with self.assertRaises(AssertionError):
                    pre_common_gate(bad)

    def test_three_quarantined_lifecycles_are_inverted_and_drift_is_rejected(self):
        rows = [(TRAINING['badClauseId'], 'proposed')]
        rows += [(cid, 'superseded') for cid in OCCUPATIONAL['badClauseIds']]
        expected = sorted((cid, 'active') for cid, state in rows)
        self.assertEqual(pre_common_inventory('clauses', rows), expected)
        self.assertEqual(pre_training_inventory('clauses', pre_occupational_inventory('clauses', rows)),
                         sorted(pre_occupational_inventory('clauses', pre_training_inventory('clauses', rows))))
        for cid, state in rows:
            with self.assertRaises(AssertionError):
                pre_common_inventory('clauses', [(cid, 'active')])
        self.assertEqual(pre_common_inventory('clauses', [('C_UNKNOWN', 'proposed')]),
                         [('C_UNKNOWN', 'proposed')])

    def test_unknown_gate_changes_are_preserved_by_composition(self):
        changed = copy.deepcopy(self.gate)
        changed.links['K_UNKNOWN'] = {'ok': False}
        changed.eligible_hazards.add('H_UNKNOWN')
        prior = pre_common_gate(changed)
        self.assertEqual(prior.links['K_UNKNOWN'], {'ok': False})
        self.assertIn('H_UNKNOWN', prior.eligible_hazards)


if __name__ == '__main__':
    unittest.main()
