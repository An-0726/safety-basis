"""A current duplicate merge cannot silently rewrite an older admission receipt."""
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/v4'))
from commerce_merge_history import (APPROVAL, HISTORY, OLD_H, OLD_K, TARGET_H,
                                    approved_atomic_history)
from check_commerce_candidate_dispositions import validate_commerce_dispositions


class CommerceMergeHistoryTests(unittest.TestCase):
    def setUp(self):
        self.owner = tempfile.TemporaryDirectory()
        self.addCleanup(self.owner.cleanup)
        self.root = Path(self.owner.name)
        self.approval = json.loads((ROOT / APPROVAL).read_text())
        merge = self.approval['mobileMerge']
        paths = {APPROVAL, HISTORY} | set(merge['sourceBindings']) | set(merge['historicalIndependentReviewsUnchanged'])
        paths.update(row['path'] for row in merge['objects'])
        for relative in paths:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        self.entities = {}
        for folder in ('hazards', 'links', 'clauses', 'law-versions'):
            self.entities[folder] = {d['id']: d for p in (self.root / 'knowledge' / folder).glob('*.json')
                                     for d in [json.loads(p.read_text())]}

    def test_exact_approved_history_does_not_change_current_entities(self):
        original = copy.deepcopy(self.entities)
        historical, errors = approved_atomic_history(self.root, self.entities)
        self.assertEqual(errors, [])
        self.assertEqual(self.entities, original)
        self.assertEqual(self.entities['hazards'][OLD_H]['lifecycle'], 'superseded')
        self.assertEqual(historical['hazards'][OLD_H]['lifecycle'], 'active')
        self.assertEqual(historical['links'][OLD_K]['lifecycle'], 'active')
        self.assertEqual(historical['hazards'][TARGET_H], self.entities['hazards'][TARGET_H])

    def test_absent_or_unapproved_new_receipt_fails(self):
        for verdict in ('CHANGES', 'PENDING'):
            changed = copy.deepcopy(self.approval)
            changed['verdict'] = verdict
            (self.root / APPROVAL).write_text(json.dumps(changed))
            self.assertTrue(approved_atomic_history(self.root, self.entities)[1])
        (self.root / APPROVAL).unlink()
        self.assertTrue(approved_atomic_history(self.root, self.entities)[1])

    def test_current_source_or_old_receipt_byte_change_fails(self):
        paths = [f'knowledge/hazards/{TARGET_H}.json', HISTORY,
                 *self.approval['mobileMerge']['sourceBindings'],
                 *self.approval['mobileMerge']['historicalIndependentReviewsUnchanged']]
        for relative in paths:
            with self.subTest(path=relative):
                path = self.root / relative
                raw = path.read_bytes()
                path.write_bytes(raw + b' ')
                self.assertTrue(approved_atomic_history(self.root, self.entities)[1])
                path.write_bytes(raw)

    def test_other_merge_target_or_missing_upstream_proof_fails(self):
        altered = copy.deepcopy(self.entities)
        altered['hazards'][OLD_H]['mergedInto'] = 'H_UNREVIEWED'
        self.assertTrue(approved_atomic_history(self.root, altered)[1])
        changed = copy.deepcopy(self.approval)
        changed['mobileMerge']['sourceBindings'] = {}
        (self.root / APPROVAL).write_text(json.dumps(changed))
        self.assertTrue(approved_atomic_history(self.root, self.entities)[1])

    def test_real_aggregate_validates_old_and_new_approvals(self):
        self.assertEqual(validate_commerce_dispositions(ROOT), [])


if __name__ == '__main__':
    unittest.main()
