"""Screenshot state guards: real scrolling, unchanged DOM and preserved flows."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/browser'))
import capture_evidence as C


def geometry():
    return {'scrollX': 0, 'scrollY': 0, 'header': {'top': 0, 'height': 96, 'bottom': 96},
        'content': {'top': 740, 'height': 1400}, 'textRectCount': 35, 'overlaps': [],
        'fontStatus': 'loaded', 'toastVisible': False, 'documentWidth': 390,
        'documentHeight': 2400, 'activeElementId': 'copy'}


class Page:
    def __init__(self, before=None, after=None, screenshot_error=False):
        self.position = {'x': 0, 'y': 1280}; self.calls = []
        self.states = [before or geometry(), after or before or geometry()]
        self.screenshot_error = screenshot_error
    def evaluate(self, script, arg=None):
        self.calls.append(('evaluate', script, copy.deepcopy(arg)))
        if script == C.SCROLL_POSITION: return dict(self.position)
        if script == C.SCROLL_TO: self.position = dict(arg)
        elif script == C.CAPTURE_GEOMETRY: return copy.deepcopy(self.states.pop(0))
    def wait_for_function(self, script, *, arg=None):
        self.calls.append(('wait', script, copy.deepcopy(arg)))
        if script == C.SCROLL_AT: assert self.position == arg
    def screenshot(self, **kwargs):
        self.calls.append(('screenshot', kwargs))
        if self.screenshot_error: raise RuntimeError('real capture failure')


class CaptureEvidenceTests(unittest.TestCase):
    def test_success_waits_scroll_fonts_toast_layout_then_captures_and_restores(self):
        page = Page(); result = C.capture_full_page(page, '/tmp/evidence.png')
        self.assertEqual(page.position, {'x': 0, 'y': 1280})
        self.assertEqual(result['originalScroll'], result['restoredScroll'])
        self.assertEqual(result['captureState']['scrollY'], 0)
        self.assertFalse(result['domOrStyleAltered'])
        methods = [(row[0], row[1]) for row in page.calls]
        screenshot = next(i for i, row in enumerate(page.calls) if row[0] == 'screenshot')
        for action in [('wait', C.SCROLL_AT), ('evaluate', C.FONTS_READY), ('wait', C.TOAST_GONE), ('evaluate', C.SETTLED_LAYOUT)]:
            self.assertLess(methods.index(action), screenshot)
        self.assertEqual(page.calls[screenshot][1], {'path': '/tmp/evidence.png', 'full_page': True})
        self.assertEqual([row[2] for row in page.calls if row[:2] == ('evaluate', C.SCROLL_TO)],
                         [{'x': 0, 'y': 0}, {'x': 0, 'y': 1280}])

    def test_midpage_header_overlap_toast_and_unsettled_fonts_cannot_be_signed(self):
        changes = [{'scrollY': 1200}, {'header': {'top': 800, 'height': 96}},
            {'overlaps': ['a hidden legal title']}, {'toastVisible': True}, {'fontStatus': 'loading'},
            {'textRectCount': 0}, {'content': None}, {'header': None}]
        for change in changes:
            page = Page(before={**geometry(), **change})
            with self.subTest(change=change), self.assertRaises(AssertionError): C.capture_full_page(page, '/tmp/rejected.png')
            self.assertFalse(any(row[0] == 'screenshot' for row in page.calls))
            self.assertEqual(page.position, {'x': 0, 'y': 1280})

    def test_capture_failure_or_after_capture_layout_drift_restores_the_real_scroll(self):
        page = Page(screenshot_error=True)
        with self.assertRaisesRegex(RuntimeError, 'real capture failure'): C.capture_full_page(page, '/tmp/failed.png')
        self.assertEqual(page.position['y'], 1280)
        page = Page(after={**geometry(), 'documentHeight': 2500})
        with self.assertRaisesRegex(AssertionError, 'changed settled geometry'): C.capture_full_page(page, '/tmp/unstable.png')
        self.assertEqual(page.position['y'], 1280)

    def test_viewport_readiness_wait_never_changes_the_current_scroll(self):
        page = Page(); result = C.wait_capture_ready(page)
        self.assertEqual(result, {'x': 0, 'y': 1280})
        self.assertFalse(any(row[:2] == ('evaluate', C.SCROLL_TO) for row in page.calls))
        self.assertFalse(any(row[0] == 'screenshot' for row in page.calls))
        self.assertIn(('wait', C.TOAST_GONE, None), page.calls)

    def test_real_javascript_toast_predicate_requires_natural_class_and_opacity_end(self):
        script = r'''
const assert=require('node:assert/strict');const fs=require('node:fs');
const predicate=eval('('+JSON.parse(fs.readFileSync(0,'utf8'))+')');
let present=true,show=true,opacity='1';
global.document={querySelector:()=>present?{classList:{contains:()=>show}}:null};
global.getComputedStyle=()=>({display:'block',visibility:'visible',opacity});
assert.equal(predicate(),false);show=false;opacity='0.5';assert.equal(predicate(),false);
opacity='0';assert.equal(predicate(),true);show=true;assert.equal(predicate(),false);
present=false;assert.equal(predicate(),true);
'''
        result = subprocess.run(['node', '-e', script], input=json.dumps(C.TOAST_GONE), text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_real_javascript_geometry_detects_header_intersection_and_compiles_all_capture_scripts(self):
        scripts = {name: getattr(C, name) for name in ('SCROLL_POSITION', 'SCROLL_TO', 'SCROLL_AT',
            'FONTS_READY', 'TOAST_GONE', 'SETTLED_LAYOUT', 'CAPTURE_GEOMETRY')}
        script = r'''const assert=require('node:assert/strict'),fs=require('node:fs');
const scripts=JSON.parse(fs.readFileSync(0,'utf8'));for(const text of Object.values(scripts))new Function('return ('+text+')');
let y=800;const text={textContent:'完整法条'};
const header={getBoundingClientRect:()=>({left:0,top:0,right:390,bottom:96,width:390,height:96})};
const content={getBoundingClientRect:()=>({left:12,top:740,right:378,bottom:2400,width:366,height:1660})};
global.scrollX=0;global.scrollY=0;global.NodeFilter={SHOW_TEXT:4};
global.document={fonts:{status:'loaded'},activeElement:{id:'copy'},documentElement:{scrollWidth:390,scrollHeight:2400},
 querySelector:s=>s==='header'?header:s==='#detail'?content:null,
 createTreeWalker:()=>{let sent=false;return {nextNode:()=>sent?null:(sent=true,text)}},
 createRange:()=>({selectNodeContents:()=>{},getClientRects:()=>[{left:20,top:y,right:360,bottom:y+20,width:340,height:20}]})};
const measure=eval('('+scripts.CAPTURE_GEOMETRY+')');
assert.deepEqual(measure('#detail').overlaps,[]);assert.equal(measure('#detail').textRectCount,1);
y=40;assert.deepEqual(measure('#detail').overlaps,['完整法条']);
'''
        result = subprocess.run(['node', '-e', script], input=json.dumps(scripts), text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_success_full_page_entrypoints_use_normalization_but_failures_remain_raw(self):
        shared = (ROOT / 'tools/browser/recovery_release_acceptance.py').read_text()
        capture = shared.index("result['screenshotCapture'] = capture_full_page")
        self.assertLess(shared.index("page.reload(wait_until='domcontentloaded'); detail(row)"), capture)
        self.assertLess(shared.rfind('release_check(page)', 0, capture), capture)
        self.assertEqual(shared.count("page.reload(wait_until='domcontentloaded'); detail(row)"), 1)
        self.assertIn("flowState'] = 'after_verified_reload'", shared)
        self.assertIn("for button in ('#copy', '#copyfull', '#copy')", shared)
        self.assertIn('for width in (1440, 375, 390, 485)', shared)
        for token in ('page.go_back()', 'page.go_forward()', 'navigator.clipboard.readText()'):
            self.assertIn(token, shared)
        self.assertIn("page.screenshot(path=str(artifact_dir / f'FAILED-recovery-", shared)
        tables = (ROOT / 'tools/browser/audit_ordinary_tables.py').read_text()
        self.assertIn('law_capture = capture_full_page', tables)
        self.assertIn('wait_capture_ready(page)', tables)
        self.assertIn("region.evaluate('x=>x.scrollLeft') == table_scroll", tables)
        self.assertIn("page.screenshot(path=str(args.out.parent / f'ordinary-table-", tables)
        self.assertIn("page.screenshot(path=str(args.out.parent / f'FAILED-ordinary-table-", tables)
        self.assertIn("capture_full_page(tab, shot, content_selector='#libraryDetail')",
                      (ROOT / 'tools/browser/audit_browser.py').read_text())

    def test_capture_helper_never_masks_elements_or_edits_styles_and_pixels(self):
        source = (ROOT / 'tools/browser/capture_evidence.py').read_text()
        for forbidden in ('add_style_tag', 'classList.remove', 'classList.add', '.style.', 'removeChild',
                          'visibility:hidden', 'display:none', 'PIL', 'Image.open', 'animations=', 'mask='):
            self.assertNotIn(forbidden, source)


if __name__ == '__main__':
    unittest.main()
