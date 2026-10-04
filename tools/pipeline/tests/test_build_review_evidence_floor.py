"""A direct build cannot bypass current review Evidence-ID validation."""
from datetime import date
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/v4'))
from build_unified_release import build


class BuildReviewEvidenceFloorTests(unittest.TestCase):
    def test_invalid_current_evidence_ref_stops_before_overwriting_output(self):
        for refs in (['E_MISSING'], 'E_MISSING', [{'id': 'E_MISSING'}]):
            with self.subTest(refs=refs), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                knowledge = root / 'knowledge'
                folder = knowledge / 'reviews/clauses'
                folder.mkdir(parents=True)
                (folder / 'C_TEST.json').write_text(json.dumps({
                    'entityId': 'C_TEST', 'decision': 'verified', 'evidenceRefs': refs
                }), encoding='utf-8')
                out = root / 'existing-output'
                out.mkdir()
                sentinel = out / 'keep.txt'
                sentinel.write_text('untouched', encoding='utf-8')
                args = SimpleNamespace(data_version='test', out=out, overwrite=True,
                                       field_profiles_pilot=False)
                with self.assertRaises(ValueError):
                    build(args, knowledge, 'test-source-hash', date(2026, 10, 4))
                self.assertEqual(sentinel.read_text(), 'untouched')


if __name__ == '__main__':
    unittest.main()
