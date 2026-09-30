"""Public synthetic tests. These do not verify the private 24 field cases."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'tools/v4'))
from field_profiles_pilot import context, projection, validate


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.knowledge = Path(self.tmp.name)
        self.put('hazards/SYN_H.json', {'id':'SYN_H', 'lifecycle':'proposed'})
        self.put('clauses/SYN_C.json', {'id':'SYN_C', 'lawVersionId':'SYN_V', 'articlePath':'synthetic', 'quote':'Synthetic text, not law'})
        self.put('law-versions/SYN_V.json', {'id':'SYN_V', 'lawId':'SYN_L'})
        self.put('laws/SYN_L.json', {'id':'SYN_L'})
        self.put('reviews/clauses/SYN_C.json', {'evidenceRefs':['SYN_E']})
        self.put('evidence/SYN_E.json', {'id':'SYN_E', 'snapshotSha256':'synthetic-old'})
        self.put('field-profiles-pilot/evidence/SYN_PE.json', {'quote':'Synthetic evidence, not law'})
        self.profile = dict(id='SYN_00', hazardId='SYN_H', subitemTrace=[], title='Synthetic case',
            inspectionClass='core_onsite_inspection', defaultFieldEntry='conditional',
            recommendedDisposition='candidate', lifecycle='proposed', candidateStatus='candidate',
            object='Synthetic object', defect='Synthetic defect', sourceRefs=[{'sourceId':'SYN_ONLY'}],
            applicability={'requires':['synthetic requirement'], 'excludes':['synthetic exclusion']},
            findingTemplate='〔synthetic observation〕', pendingEvidenceNote='Synthetic only',
            evidenceRequirements=['synthetic evidence'], correctiveDirection='Synthetic action',
            basisRefs=[{'clauseId':'SYN_C','pilotEvidenceId':'SYN_PE'}], fieldReview={}, caseRole='positive')
        self.sign(self.profile)

    def put(self, rel, data):
        path=self.knowledge/rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding='utf-8')

    def sign(self, profile):
        # Only fabricated test profiles are signed here. Never touch private reviews.
        profile['fieldReview']={'status':'reviewed_candidate', 'contextFingerprint':context(profile,self.knowledge)}

    def test_content_and_dependencies_invalidate_review(self):
        validate(self.profile,self.knowledge)
        changed=copy.deepcopy(self.profile); changed['findingTemplate'] += 'changed'
        with self.assertRaisesRegex(ValueError,'stale'): validate(changed,self.knowledge)
        mutations = [
            ('clauses/SYN_C.json', {'id':'SYN_C','quote':'changed'}),
            ('law-versions/SYN_V.json', {'id':'SYN_V','lawId':'SYN_L','validityStatus':'repealed'}),
            ('laws/SYN_L.json', {'id':'SYN_L','name':'changed'}),
            ('evidence/SYN_E.json', {'id':'SYN_E','snapshotSha256':'changed'}),
            ('field-profiles-pilot/evidence/SYN_PE.json', {'quote':'changed'}),
            ('reviews/hazards/SYN_H.json', {'status':'changed'}),
            ('links/SYN_NEW.json', {'id':'SYN_NEW','hazardId':'SYN_H','clauseId':'SYN_C'})]
        for rel,data in mutations:
            with self.subTest(rel=rel):
                path=self.knowledge/rel; old=path.read_bytes() if path.exists() else None
                self.put(rel,data)
                with self.assertRaisesRegex(ValueError,'stale'): validate(self.profile,self.knowledge)
                if old is None: path.unlink()
                else: path.write_bytes(old)
        link={'id':'SYN_LINK','hazardId':'SYN_H','clauseId':'SYN_C'}
        self.put('links/SYN_LINK.json',link); self.sign(self.profile)
        (self.knowledge/'links/SYN_LINK.json').unlink()
        with self.assertRaisesRegex(ValueError,'stale'): validate(self.profile,self.knowledge)

    def test_invalid_content_and_promotion_rejected(self):
        for key,value,message in [('inspectionClass','bad','routing'),('candidateStatus','approved','promote'),
                                  ('findingTemplate',None,'template'),('object','','empty')]:
            with self.subTest(key=key):
                p=copy.deepcopy(self.profile);p[key]=value
                with self.assertRaisesRegex(ValueError,message):validate(p,self.knowledge)
        p=copy.deepcopy(self.profile);p['lifecycle']='active';self.sign(p)
        with self.assertRaisesRegex(ValueError,'drift'):validate(p,self.knowledge)

    def test_projection_is_candidate_only_and_does_not_mutate_sources(self):
        for i in range(24):
            p=copy.deepcopy(self.profile);p['id']=f'SYN_{i:02}'
            if i>=18:p.update(caseRole='counterexample',findingTemplate=None)
            self.sign(p);self.put(f'field-profiles-pilot/records/{p["id"]}.json',p)
        before={p:p.read_bytes() for p in self.knowledge.rglob('*.json')}
        payload=projection(self.knowledge)
        self.assertTrue(payload['pilotOnly']);self.assertFalse(payload['formalApproval'])
        self.assertEqual(len(payload['records']),24)
        for p in payload['records']:
            self.assertFalse(p['publishable']);self.assertEqual(p['candidateStatus'],'candidate')
            self.assertNotIn('fieldReview',p);self.assertTrue(p['bases'])
        self.assertTrue(all(p.read_bytes()==b for p,b in before.items()))
        (self.knowledge/'field-profiles-pilot/records/SYN_00.json').unlink()
        with self.assertRaisesRegex(ValueError,'24 unique'):projection(self.knowledge)

    def test_review_overlay_is_bound_and_never_changes_original_records(self):
        for i in range(24):
            row=copy.deepcopy(self.profile);row['id']=f'SYN_{i:02}'
            self.sign(row);self.put(f'field-profiles-pilot/records/{row["id"]}.json',row)
        original=self.knowledge/'field-profiles-pilot/records/SYN_00.json'
        before=original.read_bytes();row=json.loads(before)
        item={'id':'SYN_00','sourceContextFingerprint':row['fieldReview']['contextFingerprint'],
              'requires':['Synthetic scope'],'excludes':['Synthetic exception'],
              'pending':['Synthetic pending fact'],'sources':['Synthetic locator']}
        overlay={'schemaVersion':1,'reviewId':'synthetic-r1','formalApproval':False,'cases':[item]}
        rel='field-profiles-pilot/review-overlay.json'
        self.put(rel,overlay);payload=projection(self.knowledge)
        self.assertEqual(payload['records'][0]['reviewOverlay']['excludes'],['Synthetic exception'])
        self.assertEqual(original.read_bytes(),before)
        self.assertNotIn('reviewOverlay',payload['records'][1])
        for key,value in [('sourceContextFingerprint','stale'),('pending',[]),('id','missing')]:
            changed=copy.deepcopy(overlay);changed['cases'][0][key]=value;self.put(rel,changed)
            with self.assertRaises(ValueError):projection(self.knowledge)
        changed=copy.deepcopy(overlay);changed['formalApproval']=True;self.put(rel,changed)
        with self.assertRaises(ValueError):projection(self.knowledge)
        changed=copy.deepcopy(overlay);changed['cases'][0]['candidateStatus']='approved';self.put(rel,changed)
        with self.assertRaises(ValueError):projection(self.knowledge)

    def test_missing_private_material_is_not_acceptance(self):
        result=subprocess.run([sys.executable,str(ROOT/'tools/v4/check_field_pilot_acceptance.py'),
            '--knowledge',str(self.knowledge)],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('NOT_ACCEPTED',result.stdout)


if __name__=='__main__':unittest.main()
