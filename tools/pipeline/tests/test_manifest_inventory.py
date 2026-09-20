import json
import sys
import tempfile
import unittest
from pathlib import Path

V4 = Path(__file__).resolve().parents[2] / "v4"
sys.path.insert(0, str(V4))
from check_manifest_inventory import validate_manifest_inventory  # noqa: E402


class ManifestInventoryTests(unittest.TestCase):
    def _repo(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        knowledge = root / "knowledge"
        names = {
            "laws": "laws",
            "lawVersions": "law-versions",
            "clauses": "clauses",
            "hazards": "hazards",
            "links": "links",
            "evidence": "evidence",
            "successions": "successions",
            "requirements": "requirements",
        }
        for dirname in names.values():
            (knowledge / dirname).mkdir(parents=True, exist_ok=True)
        (knowledge / "hazards" / "H1.json").write_text(
            json.dumps({"id": "H1", "lifecycle": "active"}), encoding="utf-8"
        )
        counts = {key: (1 if key == "hazards" else 0) for key in names}
        manifest = {
            "counts": counts.copy(),
            **counts,
            "activeHazards": 1,
            "proposedHazards": 0,
            "supersededHazards": 0,
            "lifecycle": {"active": 1, "proposed": 0, "superseded": 0},
        }
        (knowledge / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return td, root

    def test_matching_inventory_passes(self):
        td, root = self._repo()
        self.addCleanup(td.cleanup)
        self.assertEqual(validate_manifest_inventory(root), [])

    def test_manifest_drift_is_blocking(self):
        td, root = self._repo()
        self.addCleanup(td.cleanup)
        manifest_path = root / "knowledge" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["hazards"] = 0
        manifest["counts"]["hazards"] = 0
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        errors = validate_manifest_inventory(root)
        self.assertTrue(any("counts.hazards" in x for x in errors))
        self.assertTrue(any("manifest count mismatch hazards" in x for x in errors))


if __name__ == "__main__":
    unittest.main()
