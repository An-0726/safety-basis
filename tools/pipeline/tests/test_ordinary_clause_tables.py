"""Ordinary-clause rich-body recovery QA. Synthetic mutations are not legal review."""
import copy
from datetime import date
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/v4'))
from canonical import content_hash
from normative_content import content_text, validate_ordinary_clause_content
from release_gate_core import gate_clause, evaluate_release_gate
from build_unified_release import project_clause_content
from verify_unified_bundle import check_clause_content, Failures


def source():
    return json.loads((ROOT / 'knowledge/clauses/C_12158_4_2_3_4.json').read_text())


class OrdinaryTableTests(unittest.TestCase):
    def test_nine_original_table_rows_and_explicit_last_branch(self):
        c=source(); parts=c['contentParts']; table=parts[1]
        self.assertEqual(validate_ordinary_clause_content(c, {'reviewedTableIds':['T_GB12158_2024_2']}), ['T_GB12158_2024_2'])
        self.assertEqual(len(table['bodyRows']),9)
        self.assertEqual([x['text'] for x in table['bodyRows'][-1]], ['2区','Ⅰ类','3.0','100'])
        self.assertEqual(table['sourcePages'],[11])
        self.assertEqual(table['headerRows'][0][0]['colSpan'],2)
        self.assertEqual(table['bodyRows'][0][0]['rowSpan'],4)
        self.assertEqual(table['bodyRows'][4][0]['rowSpan'],4)
        self.assertEqual(c['quote'],content_text(parts))
        self.assertIn('工艺需要',parts[0]['text']); self.assertIn('必要时',parts[0]['text'])
        self.assertIn('GB/T 3836.11',parts[-1]['text'])

    def test_projection_lossless_and_does_not_alias_or_leak_evidence(self):
        c=source(); projected=project_clause_content(c)
        self.assertEqual(projected,{'contentParts':c['contentParts']})
        projected['contentParts'][1]['bodyRows'][0][1]['text']='Mutated copy'
        self.assertNotEqual(projected['contentParts'],c['contentParts'])
        self.assertEqual(project_clause_content({'quote':'Plain text'}),{})

    def test_bad_bodies_rejected_in_projection_even_with_valid_quote_string(self):
        for mutation in [lambda c:c.update(contentParts=None),
                         lambda c:c['contentParts'][1]['bodyRows'][0][0].update(privatePath='/private/file'),
                         lambda c:c.update(quote='Truncated'),
                         lambda c:c['contentParts'][1]['bodyRows'][0].pop(),
                         lambda c:c['contentParts'][1].update(sourcePages=[11,11])]:
            c=source(); mutation(c)
            with self.assertRaises((ValueError, TypeError)): project_clause_content(c)

    def test_rebound_review_cannot_remove_a_declared_table_or_change_its_id(self):
        for mutation in [lambda c:c.pop('contentParts'),
                         lambda c:c['contentParts'][1].update(id='T_OTHER')]:
            c=source();mutation(c)
            if 'contentParts' in c:c['quote']=content_text(c['contentParts'])
            r={'decision':'verified','reviewedContentHash':content_hash(c),'evidenceRefs':['E_SYNTHETIC'], 'reviewedTableIds':['T_GB12158_2024_2']}
            ok,reasons=gate_clause(c,r,True,True)
            self.assertFalse(ok);self.assertTrue(any('BLOCK_CLAUSE_RICH_BODY' in x for x in reasons),reasons)

    def test_verifier_rejects_body_loss_tamper_and_quote_truncation(self):
        for mutation in [lambda c:c.pop('contentParts'),lambda c:c.update(quote='Truncated'),
                         lambda c:c['contentParts'][1]['bodyRows'][-1][-1].update(text='999')]:
            c=source(); mutated=copy.deepcopy(c);mutation(mutated); failures=Failures()
            check_clause_content(failures,c['id'],mutated,c)
            self.assertTrue(failures)
        c=source();f=Failures();check_clause_content(f,c['id'],copy.deepcopy(c),c);self.assertEqual(f,[])

    def test_recovery_guardrails_and_history_are_explicit(self):
        r=evaluate_release_gate(str(ROOT/'knowledge'),date(2026,10,4))
        for hid in ['H_12158_4_2_3_5_2','H_12158_6_3_1_1','H_12158_6_3_2_2','H_12158_7_6_1','H_12158_8_8_5_3','H052']:
            self.assertIn(hid,r.eligible_hazards)
            review=json.loads((ROOT/f'knowledge/reviews/hazards/{hid}.json').read_text())
            self.assertIn('previousReview',review)
        self.assertNotIn('H_12158_10_1_2',r.eligible_hazards)
        self.assertNotIn('K_be5a0deab9619bd1579c758f',r.eligible_links)
        self.assertNotIn('H_COM_MOBILE_ELECTRIC_CORD_SELECTION',r.eligible_hazards)
        self.assertNotIn('K_COM_PLUGSTRIP_CORD_GBT13869_5_2_2',r.eligible_links)
        self.assertIn('H_8ECAE760F5A5413D8013602429',r.eligible_hazards)
        glove=json.loads((ROOT/'knowledge/hazards/H_12158_10_2_1.json').read_text())
        self.assertNotIn('H_12158_10_1_2',glove['aliases'])
        merged=json.loads((ROOT/'knowledge/hazards/H_COM_MOBILE_ELECTRIC_CORD_SELECTION.json').read_text())
        self.assertEqual(merged['mergedInto'],'H_8ECAE760F5A5413D8013602429')
        self.assertEqual(merged['lifecycle'],'superseded')
