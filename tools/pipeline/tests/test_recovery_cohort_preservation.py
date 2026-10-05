"""Current recovery pins plus strict historical views, never production policy."""
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import unittest

from recovery_cohort_fixture import (F, pre_recovery_source_bytes,
    pre_recovery_gate, pre_recovery_ids, pre_recovery_manifest,
    pre_recovery_inventory)

ROOT = Path(__file__).resolve().parents[3]
from official_clause_cohort_fixture import pre_official_repo_root
# Preserve the dated cohort against its exact, fail-closed batch predecessor.
ROOT = pre_official_repo_root(ROOT)
sys.path.insert(0, str(ROOT / 'tools/v4'))
from release_gate_core import evaluate_release_gate
sha = lambda raw: hashlib.sha256(raw).hexdigest()


class RecoveryCohortPreservationTests(unittest.TestCase):
    def test_current_files_and_complete_prior_bytes_are_exact(self):
        self.assertEqual(F['baselineCommit'], 'ffdfee5d79717c9fefe736830174e177cec4703c')
        self.assertTrue(F['records'])
        for path, row in F['records'].items():
            with self.subTest(path=path):
                raw = (ROOT / path).read_bytes()
                self.assertEqual(sha(raw), row['afterSha256'])
                before = pre_recovery_source_bytes(path, raw)
                if row['beforeFileText'] is None:
                    self.assertIsNone(before)
                else:
                    self.assertEqual(before, row['beforeFileText'].encode())
                    self.assertEqual(sha(before), row['beforeSha256'])
                with self.assertRaises(AssertionError):
                    pre_recovery_source_bytes(path, raw + b' ')

    def test_unknown_bytes_ids_and_lifecycle_changes_are_never_hidden(self):
        self.assertEqual(pre_recovery_source_bytes('knowledge/hazards/H_UNKNOWN.json', b'changed'), b'changed')
        self.assertIn('H_UNKNOWN', pre_recovery_ids('hazards', {'H_UNKNOWN'}))
        self.assertEqual(pre_recovery_inventory('hazards', [('H_UNKNOWN', 'superseded')]),
                         [('H_UNKNOWN', 'superseded')])
        for kind, rows in F['lifecycleChanges'].items():
            for ident, states in rows.items():
                with self.assertRaises(AssertionError):
                    pre_recovery_inventory(kind, [(ident, 'unreviewed-state')])

    def test_gate_views_preserve_original_input_and_unknown_changes(self):
        current = evaluate_release_gate(ROOT / 'knowledge', date(2026, 10, 4))
        original = copy.deepcopy(current)
        prior = pre_recovery_gate(current)
        self.assertEqual(current, original)
        snapshot = F['gateSnapshots']['2026-10-04']
        self.assertEqual(len(current.eligible_hazards), snapshot['countsAfter']['eligible_hazards'])
        self.assertEqual(len(current.eligible_links), snapshot['countsAfter']['eligible_links'])
        self.assertEqual(len(prior.eligible_hazards), snapshot['countsBefore']['eligible_hazards'])
        self.assertEqual(len(prior.eligible_links), snapshot['countsBefore']['eligible_links'])
        changed = copy.deepcopy(current)
        changed.eligible_hazards.add('H_UNKNOWN')
        self.assertIn('H_UNKNOWN', pre_recovery_gate(changed).eligible_hazards)
        for kind, rows in snapshot['judgments'].items():
            for ident, row in rows.items():
                if row['after'] is None:
                    continue
                changed = copy.deepcopy(current)
                getattr(changed, kind)[ident] = {'unreviewed': True}
                with self.assertRaises(AssertionError):
                    pre_recovery_gate(changed)
                break

    def test_manifest_inverse_does_not_hide_an_unknown_increment(self):
        current = json.loads((ROOT / 'knowledge/manifest.json').read_text())
        old = pre_recovery_manifest(current)
        changed = copy.deepcopy(current)
        changed['counts']['evidence'] += 1
        self.assertEqual(pre_recovery_manifest(changed)['counts']['evidence'], old['counts']['evidence'] + 1)
        self.assertEqual(pre_recovery_manifest(current), old)


if __name__ == '__main__':
    unittest.main()
