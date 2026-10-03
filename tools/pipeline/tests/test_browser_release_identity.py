"""Pure manifest-schema checks for the real-browser release audit."""
import copy
from pathlib import Path
import runpy
import unittest

AUDIT = runpy.run_path(str(Path(__file__).resolve().parents[2] / 'browser/audit_browser.py'))
CHECK = AUDIT['validate_release_identity']

class BrowserReleaseIdentityTests(unittest.TestCase):
    def setUp(self):
        self.release = {'asOf': '2026-10-03', 'releaseHash': 'hash', 'counts': {'hazards': 1671}}
        self.manifest = {'dataVersion': '2026.10.03.9372be6ad367', 'releaseHash': 'hash', 'counts': {'hazards': 1671}}

    def test_reads_version_from_data_manifest_and_date_from_release(self):
        result = CHECK(self.release, self.manifest, '9372be6ad3674586474564584fd7f48563e96557')
        self.assertEqual(result['dataVersion'], self.manifest['dataVersion'])
        self.assertEqual(result['asOf'], self.release['asOf'])

    def test_rejects_stale_commit_or_disagreeing_metadata(self):
        with self.assertRaises(AssertionError):
            CHECK(self.release, self.manifest, 'b81c1af2d6d5092e30502198806f65c27523f869')
        for field, value in [('releaseHash', 'other'), ('counts', {'hazards': 1665})]:
            changed = copy.deepcopy(self.manifest); changed[field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError):
                CHECK(self.release, changed)

    def test_release_hash_is_required_even_without_commit_check(self):
        with self.assertRaises(AssertionError):
            CHECK({'counts': {}}, {'counts': {}})

if __name__ == '__main__':
    unittest.main()
