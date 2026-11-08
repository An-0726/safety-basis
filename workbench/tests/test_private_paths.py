"""Business records must never be restored into public source directories."""
import tempfile
import unittest
from pathlib import Path

from workbench.backend.backup import restore_backup
from workbench.backend.storage import Store, private_data_root

ROOT = Path(__file__).resolve().parents[2]


class PrivatePathsTest(unittest.TestCase):
    def test_store_and_restore_reject_public_paths_before_writing(self):
        for relative in ('web/private-company', 'knowledge/private-company', 'source/releases/private-company', 'workbench/company'):
            target = ROOT / relative
            with self.subTest(path=relative):
                with self.assertRaisesRegex(ValueError, '公开仓库'):
                    Store(target)
                with self.assertRaisesRegex(ValueError, '公开仓库'):
                    restore_backup('/nonexistent-backup.zip', target)
                self.assertFalse(target.exists())

    def test_external_and_ignored_runtime_paths_are_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(private_data_root(directory), Path(directory).resolve())
        self.assertEqual(private_data_root(ROOT / 'workbench/runtime/team'), ROOT / 'workbench/runtime/team')


if __name__ == '__main__':
    unittest.main()
