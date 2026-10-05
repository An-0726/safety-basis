"""Deterministic small workflow artifacts retain every selected screenshot."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/browser'))
import package_focused_artifacts as PACK


def make_fixture(root, ids):
    path = root / 'fixture.json'
    path.write_text(json.dumps({'knowledgeSnapshotHash': 'a' * 64, 'changedHazardIds': ids,
        'batchAudit': {'currentBatchHazardIds': ids}}))
    return path


class FocusedArtifactPackagingTests(unittest.TestCase):
    def test_every_current_batch_image_is_present_once_with_separate_widths_and_small_parts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / 'raw'; source.mkdir()
            fixture = make_fixture(root, [f'H_{i:03d}' for i in range(175)])
            (source / 'browser.json').write_text('{"checks": [], "failed": 0}')
            screenshots = source / 'recovery-screenshots'; screenshots.mkdir()
            for width in (1440, 390):
                for hid in json.loads(fixture.read_text())['changedHazardIds']:
                    (screenshots / f'recovery-{width}-{hid}.png').write_bytes((str(width) + hid).encode())
            (screenshots / 'recovery-390-H_OLD_UNCHANGED.png').write_bytes(b'retained only in full artifact')
            result = PACK.package(source, root / 'out', fixture)
            self.assertEqual(result['missingScreenshotCount'], 0)
            self.assertEqual(result['presentScreenshotCount'], 350)
            self.assertEqual(len(result['parts']), 7)
            copied = []
            for part in result['parts']:
                directory = root / 'out' / part['part']
                self.assertLessEqual(part['images'], 60); self.assertLessEqual(part['bytes'], 24 * 1024 * 1024)
                manifest = json.loads((directory / 'part-manifest.json').read_text())
                for row in manifest['files']:
                    self.assertEqual(hashlib.sha256((directory / row['path']).read_bytes()).hexdigest(), row['sha256'])
                    if row['path'].endswith('.png'):
                        self.assertIn('recovery-' + part['group'].removeprefix('screenshots-') + '-', row['path'])
                        copied.append(row['path'])
                archive = root / (part['part'] + '.zip')
                with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
                    for path in directory.rglob('*'):
                        if path.is_file(): bundle.write(path, path.relative_to(directory))
                self.assertLess(archive.stat().st_size, 32 * 1024 * 1024)
            self.assertEqual(len(copied), len(set(copied)))
            self.assertEqual(set(copied), {f'recovery-screenshots/recovery-{w}-H_{i:03d}.png' for w in (1440, 390) for i in range(175)})
            self.assertTrue((screenshots / 'recovery-390-H_OLD_UNCHANGED.png').exists())

    def test_missing_and_failed_images_are_explicit_and_success_is_never_invented(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / 'raw'; source.mkdir()
            fixture = make_fixture(root, ['H_TEST'])
            (source / 'browser.json').write_text('{"failed": 1}')
            (source / 'recovery-screenshots').mkdir()
            (source / 'recovery-screenshots/FAILED-recovery-390-H_TEST.png').write_bytes(b'actual failure evidence')
            result = PACK.package(source, root / 'out', fixture)
            self.assertEqual(result['missingScreenshotCount'], 2)
            inventory = json.loads((root / 'out/part-01/focused-evidence-inventory.json').read_text())
            self.assertEqual(inventory['presentScreenshotCount'], 0)
            self.assertEqual(inventory['expectedScreenshotCount'], 2)
            self.assertEqual(len(inventory['missingScreenshotPaths']), 2)
            self.assertIn('not a pass verdict', inventory['note'])
            self.assertTrue((root / 'out/part-02/recovery-screenshots/FAILED-recovery-390-H_TEST.png').exists())
            (source / 'browser.json').write_text('{"failed": 0, "checks": [{"pass": true}]}')
            with self.assertRaisesRegex(AssertionError, 'reported success'):
                PACK.package(source, root / 'false-success', fixture)

    def test_size_overflow_too_many_parts_invalid_ids_and_stale_output_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / 'raw'; source.mkdir()
            fixture = make_fixture(root, ['H_TEST'])
            giant = source / 'giant.json'; giant.write_bytes(b'x' * 100)
            with self.assertRaisesRegex(AssertionError, 'Single evidence file'):
                PACK.partition([(giant, giant.name)], byte_limit=PACK.MANIFEST_RESERVE + 99)
            (source / 'recovery-screenshots').mkdir()
            for width in (1440, 390):
                (source / f'recovery-screenshots/recovery-{width}-H_TEST.png').write_bytes(b'image')
            with patch.object(PACK, 'MAX_PARTS', 2), self.assertRaisesRegex(AssertionError, 'no files omitted'):
                PACK.package(source, root / 'limited', fixture)
            PACK.package(source, root / 'existing', fixture)
            with self.assertRaisesRegex(AssertionError, 'stale evidence'):
                PACK.package(source, root / 'existing', fixture)
            make_fixture(root, ['H_../../escape'])
            with self.assertRaisesRegex(AssertionError, 'sorted current-batch'):
                PACK.package(source, root / 'bad', fixture)

    def test_workflow_preserves_full_artifacts_and_all_tests_with_bounded_upload_slots(self):
        text = (ROOT / '.github/workflows/reviewed-site.yml').read_text()
        for token in ('node --test tests/*.test.mjs', 'python -m unittest discover -s tools/pipeline/tests -v',
                      'name: common-hazards-browser-local-evidence', 'name: deployed-site-browser-evidence',
                      'timeout-minutes: 90', 'timeout-minutes: 75'):
            self.assertIn(token, text)
        self.assertNotIn('residual-clause-browser-local-focused', text)
        self.assertNotIn('residual-clause-online-verify-focused', text)
        for mode in ('local', 'online'):
            for number in range(1, 11):
                self.assertEqual(text.count(f"steps.focused_{mode}.outputs.part_{number:02d} == 'true'"), 1)
        self.assertEqual(text.count('tools/browser/package_focused_artifacts.py'), 2)


if __name__ == '__main__':
    unittest.main()
