from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/pipeline'))
import site_bundle
import test_public_fulltext as fixtures


class SiteBundleTests(unittest.TestCase):
    def test_reviewed_bundle_is_complete_private_free_and_deterministic(self):
        node=os.environ.get('SAFETY_NODE') or shutil.which('node')
        if not node:
            self.skipTest('Node runtime unavailable')
        fixture=fixtures.PublicFullTextTests()
        fixture.setUp()
        try:
            checklist=fixture.checklist()
            first=fixture.root/'site'
            second=fixture.root/'repeat'
            for output in (first,second):
                if output==first:
                    result=site_bundle.build_site(fixture.db,fixture.library,checklist,'2026-09-09',output,node=node)
                else:
                    script="import json,sys;sys.path.insert(0,sys.argv[1]);import site_bundle;print(json.dumps(site_bundle.build_site(*sys.argv[2:7],node=sys.argv[7])))"
                    run=subprocess.run([sys.executable,'-X','utf8','-c',script,str(Path(site_bundle.__file__).parent),
                                        str(fixture.db),str(fixture.library),str(checklist),'2026-09-09',str(output),str(node)],
                                       capture_output=True,text=True,encoding='utf-8',check=True,env={**os.environ,'PYTHONHASHSEED':'42'})
                    result=json.loads(run.stdout)
                self.assertEqual(result['fullTextCount'],1)
                manifest=json.loads((output/'site-manifest.json').read_text(encoding='utf-8'))
                self.assertIn('data/fulltext/texts/LV_TEST.json',manifest['fileHashes'])
                checksums=json.loads((output/'checksums.json').read_text(encoding='utf-8'))
                self.assertEqual(set(checksums),{p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file() and p.name!='checksums.json'})
                for name,sha in checksums.items():
                    self.assertEqual(site_bundle.exchange.sha256_bytes((output/name).read_bytes()),sha)
                    if name.endswith('.json'):
                        self.assertNotIn(b'\r\n',(output/name).read_bytes(),name)
                self.assertTrue((output/'library.html').is_file())
                self.assertTrue(site_bundle.verify_bundle(output)['ok'])
                self.assertFalse(any('blockers' in name or 'review.json' in name or 'sqlite' in name for name in checksums))
            for file in first.rglob('*'):
                if file.is_file():
                    self.assertEqual(file.read_bytes(),(second/file.relative_to(first)).read_bytes())
            (second/'library.html').write_text('changed',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'哈希'):
                site_bundle.verify_bundle(second)
        finally:
            fixture.tearDown()
