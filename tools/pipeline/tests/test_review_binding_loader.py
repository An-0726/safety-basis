import importlib.util
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "v4" / "check_review_binding.py"
SPEC = importlib.util.spec_from_file_location("check_review_binding_under_test", MODULE_PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)

class ReviewBindingLoaderTests(unittest.TestCase):
    def test_entities_are_indexed_by_internal_id_not_filename(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "hazards").mkdir()
            (root / "hazards" / "escaped.json").write_text(
                json.dumps({"id": "H_JS140_七_1"}, ensure_ascii=False), encoding="utf-8"
            )
            old = MOD.KNOW
            MOD.KNOW = str(root)
            try:
                rows = MOD.load_dir("hazards")
            finally:
                MOD.KNOW = old
            self.assertIn("H_JS140_七_1", rows)
            self.assertNotIn("escaped", rows)

    def test_explicit_missing_evidence_blocks_each_current_review_kind(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for kind in ('laws', 'law-versions', 'clauses', 'hazards', 'links', 'field-profiles'):
                folder = root / 'reviews' / kind
                folder.mkdir(parents=True)
                (folder / 'r.json').write_text(json.dumps({
                    'entityId': kind, 'decision': 'rejected', 'evidenceRefs': ['E_MISSING', 'EH_MISSING']
                }), encoding='utf-8')
            missing = MOD.missing_review_evidence_refs(root)
            self.assertEqual(len(missing), 12)
            self.assertEqual({row[1] for row in missing},
                             {'laws', 'law-versions', 'clauses', 'hazards', 'links', 'field-profiles'})

    def test_evidence_internal_id_not_filename_and_legacy_history_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'evidence').mkdir()
            (root / 'evidence' / 'different_filename.json').write_text(
                json.dumps({'id': 'E_PRESENT'}), encoding='utf-8')
            folder = root / 'reviews' / 'hazards'
            folder.mkdir(parents=True)
            (folder / 'r.json').write_text(json.dumps({
                'entityId': 'H_TEST', 'evidenceRefs': ['E_PRESENT', 'legacy descriptive source'],
                'previousReview': {'evidenceRefs': ['E_UNRECOVERED_HISTORY']}
            }), encoding='utf-8')
            self.assertEqual(MOD.missing_review_evidence_refs(root), [])

    def test_unresolved_evidence_changes_validator_exit_code(self):
        with patch.object(MOD, 'load_dir', return_value={}), \
             patch.object(MOD, 'missing_review_evidence_refs', return_value=[('reviews/hazards/x', 'H_X', 'E_MISSING')]):
            self.assertEqual(MOD.main(), 1)

    def test_malformed_current_evidence_refs_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td) / 'reviews' / 'hazards'
            folder.mkdir(parents=True)
            for refs in ('E_MISSING', [{'id': 'E_MISSING'}], None, {'E_MISSING': True}):
                with self.subTest(refs=refs):
                    (folder / 'r.json').write_text(json.dumps({
                        'entityId': 'H_TEST', 'evidenceRefs': refs
                    }), encoding='utf-8')
                    with self.assertRaisesRegex(ValueError, 'list of strings'):
                        MOD.missing_review_evidence_refs(td)

    def test_comparison_evidence_role_cannot_bypass_existence_or_shape_checks(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td) / 'reviews' / 'links'
            folder.mkdir(parents=True)
            p = folder / 'r.json'
            p.write_text(json.dumps({'entityId': 'K_TEST', 'evidenceRefs': [],
                                    'comparisonEvidenceRefs': ['EH_MISSING']}))
            self.assertEqual(MOD.missing_review_evidence_refs(td)[0][2], 'EH_MISSING')
            p.write_text(json.dumps({'entityId': 'K_TEST', 'comparisonEvidenceRefs': 'E_MISSING'}))
            with self.assertRaisesRegex(ValueError, 'list of strings'):
                MOD.missing_review_evidence_refs(td)

    def test_duplicate_evidence_internal_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td) / 'evidence'
            folder.mkdir()
            for name in ('a', 'b'):
                (folder / (name + '.json')).write_text(json.dumps({'id': 'E_DUP'}), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'duplicate evidence'):
                MOD.missing_review_evidence_refs(td)

    def test_duplicate_internal_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "hazards").mkdir()
            for name in ("a.json", "b.json"):
                (root / "hazards" / name).write_text(json.dumps({"id": "H_DUP"}), encoding="utf-8")
            old = MOD.KNOW
            MOD.KNOW = str(root)
            try:
                with self.assertRaises(ValueError):
                    MOD.load_dir("hazards")
            finally:
                MOD.KNOW = old

if __name__ == "__main__":
    unittest.main()
