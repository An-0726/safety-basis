"""Exact reviewed noncoal reading text never becomes a current C/H/K source."""
import hashlib,json,sys,unittest
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];K=ROOT/'knowledge';P=ROOT/'source/publication'
sys.path.insert(0,str(ROOT/'tools/v4'))
from major_criteria_reading import load_records,public_projection,review_bindings,NAMESPACE
from major_criteria import public_projection as normative_projection

def read(p):return json.loads(p.read_text())

class NoncoalReadingSourceTests(unittest.TestCase):
    def test_four_exact_independent_source_files(self):
        f=read(ROOT/'tests/private/noncoal-reference-reading-source-v1.json')
        self.assertEqual(len(f['files']),4)
        for row in f['files']:
            with self.subTest(path=row['path']):self.assertEqual(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest(),row['sha256'])
        self.assertEqual(f['currentCanonicalDelta'],{'clauses':0,'hazards':0,'links':0,'evidence':0})

    def test_complete_64_plus_8_with_nested_conditions_and_exact_scope_binding(self):
        r=load_records(K)['READING_NONCOAL_2022_2024'];main,supp=r['documents']
        self.assertEqual([len(s['items']) for s in main['sections']],[32,13,19]);self.assertEqual([len(s['items']) for s in supp['sections']],[4,2,2])
        self.assertEqual([d['firstLevelItemCount'] for d in r['documents']],[64,8])
        self.assertIn('经批准的联合试运转除外',main['sections'][0]['items'][26]['quote'])
        self.assertIn('或者未采取有效治理措施',supp['sections'][0]['items'][1]['quote'])
        self.assertIn('或者月产量大于矿山设计年生产能力的20%及以上',main['sections'][0]['items'][29]['quote'])
        self.assertIn('独立选矿厂',main['sections'][2]['items'][17]['quote'])
        review=read(K/NAMESPACE/'scope-reviews'/f"{r['id']}.json")
        self.assertEqual({k:review[k] for k in review_bindings(r,K,P)},review_bindings(r,K,P))
        self.assertFalse(review['currentDeterminationBasis'])

    def test_required_explanation_and_pending_external_period_are_preserved(self):
        r=load_records(K)['READING_NONCOAL_2022_2024'];notes={n['id']:n for d in r['documents'] for n in d['officialClarifications']}
        self.assertEqual(len(notes),17)
        self.assertEqual(notes['RN_NONCOAL_8']['sourcePages'],[40,41]);self.assertEqual(notes['RN_NONCOAL_16']['sourcePages'],[5,6])
        tail=notes['RN_NONCOAL_17']['text']
        for word in ('威胁尾矿库安全','暴雨、洪水','红色或橙色','实时巡查','应急抢救','不属于这里要求撤出','不使普通生产作业豁免'):self.assertIn(word,tail)
        self.assertEqual(notes['RN_NONCOAL_3']['textMode'],'official_link_pending');self.assertNotIn('180',notes['RN_NONCOAL_3']['text'])
        self.assertNotIn('15%',notes['RN_NONCOAL_9']['text']);self.assertIn('不能',notes['RN_NONCOAL_9']['text'])
        self.assertTrue(all(n['textMode'] in ('reviewed_summary','official_link_pending') for n in notes.values()))

    def test_unknown_date_remains_null_and_no_canonical_entities_are_created(self):
        vids={'LV_NMSA_NONCOAL_MAJOR_2022','LV_NMSA_NONCOAL_MAJOR_SUPPLEMENT_2024'}
        self.assertEqual([read(p)['id'] for p in (K/'clauses').glob('*.json') if read(p).get('lawVersionId') in vids],[])
        self.assertIsNone(read(K/'law-versions/LV_NMSA_NONCOAL_MAJOR_SUPPLEMENT_2024.json')['effectiveDate'])
        m=read(K/'manifest.json');self.assertEqual((m['counts']['clauses'],m['counts']['evidence'],m['counts']['hazards'],m['counts']['links']),(3099,1306,2131,1971))
        self.assertEqual(sum(b['id']=='noncoal-reference-reading-20261001' for b in m['batches']),1)

    def test_actual_dates_and_reference_counts_do_not_change_current_catalog(self):
        for at,want in ((date(2026,9,30),(0,0,0)),(date(2026,10,1),(1,2,72))):
            r=public_projection(K,P,as_of=at)['public'];norm=normative_projection(K,as_of=at)
            original=[g for g in r['readingGroups'] if g['id'] not in {'READING_CIVIL_EXPLOSIVES_2024','READING_FIREWORKS_2017'}]
            self.assertEqual((len(original),sum(len(g['documents']) for g in original),sum(d['firstLevelItemCount'] for g in original for d in g['documents'])),want)
            self.assertFalse(r['currentDeterminationBasis']);self.assertFalse(r['standaloneDeterminationAllowed'])
            self.assertEqual((r['reviewedCurrentClauseCount'],r['directHazardCount']),(0,0))
            self.assertEqual((len(norm['catalog']['standards']),sum(len(s['clauses']) for s in norm['catalog']['standards']),len(norm['topic']['hazardIds'])),(6,110,20) if at.month==10 else (2,22,19))
            self.assertNotIn('snapshotSha256',json.dumps(r));self.assertNotIn('evidenceId',json.dumps(r));self.assertNotIn('reviewer',json.dumps(r))

if __name__=='__main__':unittest.main()
