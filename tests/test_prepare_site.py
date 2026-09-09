import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/pipeline'))
import prepare_site


class PrepareSiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / 'source/releases/reviewed'
        shutil.copytree(ROOT / 'source/releases/reviewed-20260909-r2', self.bundle)
        release = json.loads((self.bundle / 'release.json').read_text(encoding='utf-8'))
        self.config = {'schemaVersion': 'safety-site-selection-v1', 'bundle': 'reviewed',
                       'releaseHash': release['releaseHash']}
        self.selection = self.root / 'source/releases/site-selection.json'

    def run_prepare(self, **kwargs):
        self.selection.write_text(json.dumps(self.config), encoding='utf-8')
        return prepare_site.prepare(self.selection, kwargs.pop('output', self.root / 'dist'),
                                    repository=self.root, as_of=kwargs.pop('as_of', '2026-09-09'))

    def test_output_is_only_the_selected_verified_bundle(self):
        (self.root / 'source/master').mkdir()
        (self.root / 'source/master/private.txt').write_text('private source')
        result = self.run_prepare()
        self.assertFalse(result['deployed'])
        output = self.root / 'dist'
        source_files = {p.relative_to(self.bundle) for p in self.bundle.rglob('*') if p.is_file()}
        self.assertEqual(source_files, {p.relative_to(output) for p in output.rglob('*') if p.is_file()})
        self.assertTrue(all((output / p).read_bytes() == (self.bundle / p).read_bytes() for p in source_files))

    def test_tampered_or_unreviewed_extra_files_prevent_output(self):
        (self.bundle / 'private.txt').write_text('must not be published')
        with self.assertRaisesRegex(ValueError, '文件集合'):
            self.run_prepare()
        self.assertFalse((self.root / 'dist').exists())

    def test_wrong_selection_or_expired_proofs_prevent_output(self):
        self.config['releaseHash'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'releaseHash'):
            self.run_prepare()
        self.config['releaseHash'] = json.loads((self.bundle / 'release.json').read_text(encoding='utf-8'))['releaseHash']
        with self.assertRaisesRegex(ValueError, '发布当日'):
            self.run_prepare(as_of='2026-11-01')
        self.assertFalse((self.root / 'dist').exists())

    def test_source_escape_and_protected_output_are_rejected(self):
        self.config['bundle'] = '../../master'
        with self.assertRaisesRegex(ValueError, '发布选择'):
            self.run_prepare()
        self.config['bundle'] = 'reviewed'
        with self.assertRaisesRegex(ValueError, '托管输出不能'):
            self.run_prepare(output=self.root / 'source/master/new-site')
        self.assertFalse((self.root / 'source/master/new-site').exists())


if __name__ == '__main__':
    unittest.main()
