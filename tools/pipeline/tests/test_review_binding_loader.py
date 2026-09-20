import importlib.util
import json
import tempfile
import unittest
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
