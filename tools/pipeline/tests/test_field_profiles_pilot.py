import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'tools/v4'))
from field_profiles_pilot import context, projection, validate

class PilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = projection(ROOT/'knowledge')

    def test_candidate_isolation_and_trace(self):
        rows = self.payload['records']
        self.assertEqual(len(rows), 24)
        self.assertEqual(sum(p['caseRole']=='positive' for p in rows), 18)
        self.assertTrue(all(p['publishable'] is False and p['candidateStatus']=='candidate' for p in rows))
        self.assertTrue(all(p['sourceRefs'] and p['bases'] for p in rows))
        unknown = [p for p in rows if p['id'] in {'FP_N04','FP_N05','FP_N06'}]
        self.assertTrue(all(p['findingTemplate'] is None for p in unknown))
        self.assertTrue(all(p['frequencyEvidence'] is None for p in rows))
        by_id={p['id']:p for p in rows}
        self.assertIn('重大危险源', by_id['FP_N01']['applicability']['requires'][0])
        self.assertIn('生产、储存危险化学品', by_id['FP_N02']['applicability']['requires'][0])

    def test_content_and_all_association_dependencies_invalidate(self):
        original = json.loads((ROOT/'knowledge/field-profiles-pilot/records/FP_P13.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as tmp:
            knowledge = Path(tmp)
            def put(rel, data):
                path=knowledge/rel; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(data),encoding='utf-8')
            put(f"hazards/{original['hazardId']}.json", {'id': original['hazardId'], 'lifecycle':original['lifecycle']})
            put('clauses/C001.json', {'id':'C001','lawVersionId':'LV1','quote':'原文'})
            put('law-versions/LV1.json', {'id':'LV1','lawId':'LF1','validityStatus':'active'})
            put('laws/LF1.json', {'id':'LF1'})
            put('reviews/clauses/C001.json', {'evidenceRefs':['E1']})
            put('evidence/E1.json', {'id':'E1','snapshotSha256':'old'})
            put('field-profiles-pilot/evidence/PE_FIRE_16.json', {'quote':'原文'})
            profile=copy.deepcopy(original)
            profile['fieldReview']['contextFingerprint']=context(profile,knowledge)
            validate(profile,knowledge)
            changed=copy.deepcopy(profile);changed['findingTemplate'] += '内容改变'
            with self.assertRaisesRegex(ValueError,'stale'):validate(changed,knowledge)
            for rel, replacement in [
                ('clauses/C001.json', {'id':'C001','lawVersionId':'LV1','quote':'改文'}),
                ('law-versions/LV1.json', {'id':'LV1','lawId':'LF1','validityStatus':'repealed'}),
                ('evidence/E1.json', {'id':'E1','snapshotSha256':'new'}),
                ('field-profiles-pilot/evidence/PE_FIRE_16.json', {'quote':'改文'}),
                ('links/NEW.json', {'id':'NEW','hazardId':profile['hazardId'],'clauseId':'C001','lifecycle':'active'})
            ]:
                path=knowledge/rel;before=path.read_bytes() if path.exists() else None
                put(rel,replacement)
                with self.assertRaisesRegex(ValueError,'stale'):validate(profile,knowledge)
                if before is None:path.unlink()
                else:path.write_bytes(before)

    def test_design_omission_does_not_remove_applicable_field_candidate(self):
        # Hypothetical verified requirements, not approval of this pilot's pending laws.
        # The declared fact gate must retain observation/test thresholds while not
        # requiring existing drawings to have already complied with the requirement.
        by_id={p['id']:p for p in self.payload['records']}
        for id in ('FP_P01','FP_P03','FP_P04','FP_P05'):
            p=by_id[id]
            gate=p['applicability']['factGate']
            facts={key:True for key in gate}
            facts['designIncludesRequirement']=False
            self.assertTrue(all(facts.get(key,False) for key in gate),id)
            self.assertEqual(p['defaultFieldEntry'],'conditional')
            self.assertIsNotNone(p['findingTemplate'])
            self.assertFalse(p['publishable'])
            self.assertIn('defectObserved',gate)
            self.assertNotIn('designIncludesRequirement',gate)
            # Design omission alone, or a chemical name alone, proves no violation.
            for absent in ('applicableRequirementConfirmed','siteTriggerConfirmed','defectObserved'):
                incomplete={**facts,absent:False}
                self.assertFalse(all(incomplete.get(key,False) for key in gate),(id,absent))
        self.assertIn('requiredLogicConfirmed',by_id['FP_P03']['applicability']['factGate'])
        self.assertIn('requiredOutputConfirmed',by_id['FP_P04']['applicability']['factGate'])
        self.assertIn('requiredReceiverConfirmed',by_id['FP_P05']['applicability']['factGate'])

    def test_routing_and_promoting_are_rejected(self):
        p=json.loads((ROOT/'knowledge/field-profiles-pilot/records/FP_P01.json').read_text(encoding='utf-8'))
        p['inspectionClass']='everywhere'
        with self.assertRaisesRegex(ValueError,'routing'):validate(p,ROOT/'knowledge')
        p['inspectionClass']='core_onsite_inspection';p['candidateStatus']='approved'
        with self.assertRaisesRegex(ValueError,'promote'):validate(p,ROOT/'knowledge')

if __name__=='__main__':unittest.main()
