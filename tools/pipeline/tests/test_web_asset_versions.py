import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'v4'))
from web_assets import render_web_asset


class WebAssetVersionTests(unittest.TestCase):
    def test_transitive_and_dynamic_imports_share_the_data_version(self):
        source = b'''import {x} from './x.js';\nexport {y} from "../y.js";\nimport './startup.js';\nconst p=import('./lazy.js');\nconst marker='__SAFETY_BASIS_DATA_VERSION__';'''
        built = render_web_asset('app.js', source, '2026.11.08.test').decode()
        for reference in ['./x.js', '../y.js', './startup.js', './lazy.js']:
            self.assertIn(reference + '?v=2026.11.08.test', built)
        self.assertNotIn('__SAFETY_BASIS_DATA_VERSION__', built)

    def test_html_versions_assets_without_changing_navigation_or_official_links(self):
        source = b'''<head><link href="style.css"><script src="app.js"></script><a href="library.html">library</a><script src="https://example.org/a.js"></script></head>'''
        built = render_web_asset('index.html', source, 'build-7').decode()
        self.assertIn('href="style.css?v=build-7"', built)
        self.assertIn('src="app.js?v=build-7"', built)
        self.assertIn('href="library.html"', built)
        self.assertIn('src="https://example.org/a.js"', built)
        self.assertIn('name="safety-basis-version" content="build-7"', built)

    def test_bad_identity_is_not_inserted_into_html_or_script(self):
        for version in ['', 'bad"version', '../other', 'x\nalert(1)']:
            with self.subTest(version=version), self.assertRaises(ValueError):
                render_web_asset('index.html', b'<head></head>', version)

    def test_non_code_assets_and_existing_version_meta_remain_stable(self):
        binary = b'\xff\x00'
        self.assertEqual(render_web_asset('icon.svg', binary, 'test'), binary)
        source = b'<head><meta name="safety-basis-version" content="__SAFETY_BASIS_DATA_VERSION__"></head>'
        built = render_web_asset('index.html', source, 'test')
        self.assertEqual(built.count(b'name="safety-basis-version"'), 1)


if __name__ == '__main__':
    unittest.main()
