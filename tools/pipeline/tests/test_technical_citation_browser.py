"""Source-grounded CI overlay and mutation tests; deliberately no browser launch."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/browser'))
import technical_citation_acceptance as QA
import repair_acceptance as OLD
F=QA.load_expectations()

def rendered(row):
    got={key:row['hazard'][key] for key in ('title','description','conditions','measures')}
    got.update(id=row['id'],category=row['displayCategory'],places=' · '.join(row['hazard']['places']),bases=[])
    for b in row['bases']:
        v={key:b[key] for key in ('linkId','lawId','lawName','article','quote','applicability','sourceUrl')}
        v.update(roleLabel=OLD.ROLE_LABELS[b['role']],metadataText='标准 · '+b['lawRegion']+' · 现行有效');got['bases'].append(v)
    return got

def projection():
    return {'details':[{'id':r['id'],'hazard':copy.deepcopy(r['hazard']),'bases':copy.deepcopy(r['bases'])} for r in F['records']],
            'jgjLawClauseIds':['C_JGJ91_10_1_7','C_JGJ91_10_2_5','C_JGJ91_10_2_6','C_JGJ91_10_4_3'],
            'majorAssociations':[copy.deepcopy(F['expectedMajorAssociation'])],'majorHazardCount':20,'profileCount':25}

class TechnicalBrowserAcceptanceTests(unittest.TestCase):
    def test_both_actual_fixture_layers_validate_against_current_source(self):
        self.assertEqual(QA.validate_source_pins(F,ROOT)['basisLinks'],13)
        self.assertEqual(OLD.validate_source_pins(OLD.load_expectations(),ROOT)['hazards'],37)

    def test_ten_records_include_exact_six_corrections_and_four_jiangsu_consumers(self):
        self.assertEqual(len(QA.validate_expectations(F)),10)
        self.assertEqual(sum(r['cohort']=='technical' for r in F['records']),6)
        self.assertEqual(sum(r['cohort']=='jiangsu_geography' for r in F['records']),4)
        for bad in ['missing','duplicate']:
            f=copy.deepcopy(F)
            if bad=='missing':f['records'].pop()
            else:f['records'][-1]=f['records'][0]
            with self.assertRaises(AssertionError):QA.validate_expectations(f)

    def test_full_dom_fields_quotes_roles_and_source_links_are_pinned(self):
        for row in F['records']:QA.validate_rendered(row,rendered(row))
        for field in ['title','conditions','measures','description']:
            got=rendered(F['records'][0]);got[field]+='错改'
            with self.assertRaises(AssertionError):QA.validate_rendered(F['records'][0],got)
        for field in ['quote','article','sourceUrl','applicability','lawId']:
            got=rendered(F['records'][0]);got['bases'][0][field]+='错改'
            with self.assertRaises(AssertionError):QA.validate_rendered(F['records'][0],got)

    def test_jiangsu_display_cannot_fall_back_to_national(self):
        row=next(r for r in F['records'] if r['id']=='H061');got=rendered(row)
        b=next(b for b in got['bases'] if b['linkId']=='K_5A0522BE823232ED4D92A276');b['metadataText']='全国'
        with self.assertRaises(AssertionError):QA.validate_rendered(row,got)

    def test_mixed_or_extra_rendered_region_is_rejected(self):
        row=next(r for r in F['records'] if r['id']=='H061')
        for text in ['标准 · 全国／江苏 · 现行有效','标准 · 江苏省 · 现行有效','标准 · 江苏 · 全国 · 现行有效']:
            got=rendered(row)
            b=next(b for b in got['bases'] if b['linkId']=='K_5A0522BE823232ED4D92A276');b['metadataText']=text
            with self.assertRaises(AssertionError):QA.validate_rendered(row,got)

    def test_hydrated_clause_regions_and_link_regions_are_not_interchangeable(self):
        QA.validate_projection(F,projection())
        for field in ['jurisdictionCode','clauseRegion','lawRegion']:
            got=projection();row=next(r for r in got['details'] if r['id']=='H061');b=next(b for b in row['bases'] if b['linkId']=='K_5A0522BE823232ED4D92A276');b[field]='CN' if field=='jurisdictionCode' else '全国'
            with self.assertRaises(AssertionError):QA.validate_projection(F,got)

    def test_flame_quoting_buried_clause_or_restoring_retired_public_join_fails(self):
        got=projection();row=next(r for r in got['details'] if r['id']=='H_701AAE9385E74703A71396776E');row['bases'][0]['clauseId']='C_JGJ91_10_2_7'
        with self.assertRaises(AssertionError):QA.validate_projection(F,got)
        got=projection();got['jgjLawClauseIds'].append('C_JGJ91_10_2_7')
        with self.assertRaises(AssertionError):QA.validate_projection(F,got)

    def test_major_membership_and_trigger_cannot_inherit_jiangsu_alone(self):
        for field,value in [('jurisdictionCode','CN-32'),('linkId','K_5A0522BE823232ED4D92A276'),('applicability','仅未及时督促整改')]:
            got=projection();got['majorAssociations'][0][field]=value
            with self.assertRaises(AssertionError):QA.validate_projection(F,got)
        for key in ['majorHazardCount','profileCount']:
            got=projection();got[key]-=1
            with self.assertRaises(AssertionError):QA.validate_projection(F,got)

    def test_shared_clause_browser_pin_transition_is_metadata_only_and_explicit(self):
        old=OLD.load_expectations();rows=old['sourcePinTransitions'];self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['path'],'knowledge/clauses/C_462D38828DEBA46C8E23C177D2.json')
        self.assertEqual(rows[0]['beforeSha256'],'dcc46d1ba099f30b4be0514ddc683df64fc49b7fc7691b37b6a70328417cd5cf')
        self.assertEqual(rows[0]['afterSha256'],old['sourceFiles'][rows[0]['path']])
        self.assertEqual(len(old['records']),37)

    def test_existing_browser_and_narrow_width_coverage_is_kept(self):
        s=(ROOT/'tools/browser/audit_browser.py').read_text();t=(ROOT/'tools/browser/technical_citation_acceptance.py').read_text()
        for token in ['run_repair_browser_acceptance(browser,','run_technical_browser_acceptance(browser,',"run('no_unhandled_javascript_errors'"]:
            self.assertIn(token,s)
        self.assertLess(s.index('run_repair_browser_acceptance(browser,'),s.index('run_technical_browser_acceptance(browser,'))
        self.assertIn('(1440,375,390,485)',t)
        self.assertIn('page.evaluate(DOM_SNAPSHOT)',t);self.assertIn('metadataText',t);self.assertIn('major-criteria.html?view=hazards&standard=L019',t)
        self.assertNotIn('.launch(',t)

if __name__=='__main__':unittest.main()
