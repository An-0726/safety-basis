"""Pure rendered-table contract tests; no launch and no GUI-pass claim."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/browser'))
import audit_ordinary_tables as QA
from recovery_release_acceptance import load_expectations, expected_tables
from repair_acceptance import DOM_CONTENT_HELPERS
F = load_expectations()
R = next(r for r in F['records'] if r['id'] == QA.HAZARD_ID)
B = R['bases'][0]


class OrdinaryTableBrowserTests(unittest.TestCase):
    def test_nine_rows_keyboard_region_and_narrow_scroll_are_required(self):
        value = {'rows': 9, 'tabIndex': 0, 'pageWidth': 390, 'scroll': 600, 'client': 350}
        QA.validate_table_geometry(value, 390)
        for key, wrong in [('rows', 8), ('rows', 10), ('tabIndex', -1), ('pageWidth', 700), ('scroll', 350)]:
            got = {**value, key: wrong}
            with self.subTest(key=key, value=wrong), self.assertRaises(AssertionError): QA.validate_table_geometry(got, 390)

    def test_dom_reader_retains_all_text_cells_and_spans_but_skips_ui_annotation(self):
        # Minimal DOM-shaped objects exercise the very JS used by Playwright.
        # They deliberately contain a UI-only source/scroll note between parts.
        script = DOM_CONTENT_HELPERS + r'''
const parts = JSON.parse(process.argv[1]);
const rows = value => ({rows:value.map(row=>({cells:row.map(cell=>({...cell,cloneNode:()=>({textContent:cell.text,querySelectorAll:()=>[]})}))}))});
const children=parts.flatMap(part=>{
 if(part.type==='text')return [{matches:s=>s==='blockquote',innerText:part.text}];
 const table={caption:{innerText:part.caption},tHead:rows(part.headerRows),tBodies:[rows(part.bodyRows)]};
 return [{matches:s=>s==='.normative-table-region',querySelector:()=>table},
  {matches:s=>s==='.normative-table-source',innerText:'UI ANNOTATION MUST NOT BECOME LEGAL QUOTE'}];
});
console.log(JSON.stringify(normative({querySelector:()=>({children})})));
'''
        result = subprocess.run(['node', '-e', script, json.dumps(B['contentParts'], ensure_ascii=False)], check=True, capture_output=True, text=True)
        value = json.loads(result.stdout)
        self.assertEqual(value['quote'], B['quote'])
        self.assertEqual(value['tables'], expected_tables(B))
        self.assertNotIn('UI ANNOTATION', value['quote'])
        self.assertIn('2区\tⅠ类\t3.0\t100', value['quote'])
        self.assertTrue(value['quote'].endswith('注：爆炸性气体类别见GB/T 3836.11。'))

    def test_law_table_comparison_rejects_truncation_same_size_swap_and_cell_drift(self):
        actual = [{'article': B['article'], 'quote': B['quote'], 'tables': expected_tables(B)}]
        QA.validate_law_tables([B], actual)
        for mutation in ('quote', 'article', 'cell', 'span', 'missing'):
            got = copy.deepcopy(actual)
            if mutation == 'quote': got[0]['quote'] = B['contentParts'][0]['text']
            elif mutation == 'article': got[0]['article'] = '同字异条'
            elif mutation == 'cell': got[0]['tables'][0]['bodyRows'][-1][-1]['text'] = '999'
            elif mutation == 'span': got[0]['tables'][0]['bodyRows'][0][0]['rowSpan'] = 1
            else: got.clear()
            with self.subTest(mutation=mutation), self.assertRaises(AssertionError): QA.validate_law_tables([B], got)

    def test_cli_supports_bundle_and_public_url_with_identity_and_screenshots(self):
        text = (ROOT / 'tools/browser/audit_ordinary_tables.py').read_text()
        for value in ("source.add_argument('--bundle'", "source.add_argument('--url'", "parser.add_argument('--expected-commit'", 'validate_release_source(', 'release_check()', "region.press('ArrowRight')", 'page.screenshot(', 'expected_full_clipboard(', 'validate_law_tables('):
            self.assertIn(value, text)
        self.assertNotIn('window.__copies', text)


if __name__ == '__main__':
    unittest.main()
