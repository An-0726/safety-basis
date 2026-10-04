"""Source-backed 24-C/26-H/26-K branch repair with exact, fail-closed regressions.

Text assertions pin verified legal branches, not a fabricated site fact engine.
Professional/source judgment is preserved separately in scoped reviews.
"""
from public_technical_citation_fixture import pre_technical_source_bytes
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from remaining_clause_fixture import F, pre_remaining_gate, pre_remaining_inventory, pre_remaining_source_bytes
ROOT = Path(__file__).resolve().parents[3]
from recovery_cohort_fixture import pre_recovery_repo_root, evaluate_historical_snapshot
# This dated cohort is tested against its SHA-guarded predecessor, not new admissions.
ROOT = pre_recovery_repo_root(ROOT)
KNOW = ROOT / 'knowledge'
sys.path.insert(0, str(ROOT / 'tools/v4'))
from canonical import content_hash
from field_profiles import ProfileContext
from release_gate_core import evaluate_release_gate
from recovery_cohort_fixture import evaluate_historical_snapshot as evaluate_release_gate
ASOF = date(2026, 10, 3)
sha = lambda b: hashlib.sha256(b).hexdigest()
def source_bytes(path): return pre_technical_source_bytes(path, (ROOT / path).read_bytes())
def read(path): return json.loads(source_bytes(path))
def write(root, rel, obj):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False))
def hazard(hid): return read(f'knowledge/hazards/{hid}.json')

def exact_case(row):
    def test(self):
        hid, kid, cid = row['hazardId'], row['linkId'], row['clauseId']
        h, k = hazard(hid), read(f'knowledge/links/{kid}.json')
        h0, k0 = copy.deepcopy(row['hazardBefore']), copy.deepcopy(row['linkBefore'])
        h0.update(row['hazardChanges']); k0.update(row['linkChanges'])
        self.assertEqual(h, h0); self.assertEqual(k, k0)
        self.assertEqual(k['clauseId'], cid)
        self.assertEqual(k['applicability'], h['conditions'])
        self.assertNotIn('通用场所', h['places'])
        self.assertEqual(k['jurisdictionCode'], 'CN-32' if row['lawVersionId'] == 'L020' else 'CN')
        self.assertEqual(h['lifecycle'], 'active'); self.assertEqual(k['lifecycle'], 'active')
        rev = read(f'knowledge/reviews/links/{kid}.json')
        self.assertEqual(rev['locator'], row['operativeLocator'])
        self.assertEqual(rev['reviewEvidence']['officialSourceUrl'], row['sourceUrl'])
        self.assertFalse(rev['reviewEvidence']['siteFactsVerified'])
    return test
class RemainingBranchCases(unittest.TestCase): pass
for row in F['rows']:
    setattr(RemainingBranchCases, 'test_exact_branch_' + row['hazardId'], exact_case(row))

class RemainingRepairBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.gate = evaluate_release_gate(KNOW, ASOF)
    def test_exact_81_entities_81_reviews_and_complete_history(self):
        self.assertEqual(len(F['entities']), 81); self.assertEqual(len(F['reviews']), 81)
        self.assertEqual(len(F['badClauseIds']), 24); self.assertEqual(len(F['rows']), 26)
        for row in F['entities']:
            path = row['path']; got = read(path)
            self.assertEqual(got, row['record'], path)
            self.assertEqual(got['id'], row['before']['id'])
            self.assertEqual(sha(source_bytes(path)), row['fileSha256'])
            self.assertEqual(sha(row['beforeFileText'].encode()), row['oldFileSha256'])
            self.assertEqual({k: got[k] for k in row['unchangedFields']}, row['unchangedFields'])
        for row in F['reviews']:
            path = row['path']; got = read(path); ent = read(path.replace('/reviews', ''))
            self.assertEqual(got, row['record'], path)
            self.assertEqual(got['previousReview'], json.loads(row['beforeFileText']))
            self.assertEqual(content_hash(got['previousReview']), got['historySha256'])
            self.assertEqual(sha(row['beforeFileText'].encode()), got['previousReviewFileSha256'])
            self.assertEqual(content_hash(ent), got['reviewedContentHash'])
            self.assertEqual(got['reviewedValues'], {p: ent[p[1:]] for p in got['reviewedFields']})
            self.assertFalse(got['reviewEvidence']['profileAdmission'])
            if got['entityType'] == 'link':
                self.assertEqual(got['contextHashes'], {'hazard':content_hash(hazard(ent['hazardId'])), 'clause':content_hash(read(f"knowledge/clauses/{ent['clauseId']}.json"))})
    def test_quarantine_preserves_every_old_literal_and_id(self):
        rows = {r['id']:r for r in F['entities']}
        for cid in F['badClauseIds']:
            old, got = rows[cid]['before'], read(f'knowledge/clauses/{cid}.json')
            self.assertEqual(rows[cid]['modifiedFields'], ['lifecycle'])
            self.assertEqual(got, {**old, 'lifecycle':'proposed'})
            rev = read(f'knowledge/reviews/clauses/{cid}.json')
            self.assertEqual(rev['decision'], 'rejected'); self.assertEqual(rev['previousEntity'], old)
            self.assertFalse(self.gate.clauses[cid]['ok'])
        for p in (KNOW/'links').glob('*.json'):
            self.assertNotIn(json.loads(p.read_text()).get('clauseId'), F['badClauseIds'])
    def test_complete_originals_and_article34_three_paragraph_restoration(self):
        norm = lambda q: re.sub(r'^第[一二三四五六七八九十百]+条', '', re.sub(r'\s+', '', q).replace(':','：'))
        for cid, row in F['canonicals'].items():
            got = read(f'knowledge/clauses/{cid}.json')['quote']
            if cid == 'C074': self.assertTrue(norm(row['completeOfficialQuote']).startswith(norm(got)))
            else: self.assertEqual(norm(got), norm(row['completeOfficialQuote']), cid)
        c = read('knowledge/clauses/C_A7D8C5192004B9B1DB48E5CC.json')
        self.assertIn('发生变更时应当重新进行安全风险辨识评估', c['quote'])
        self.assertIn('具体目录由国务院应急管理部门会同有关部门制定并公布', c['quote'])
        rq = read('knowledge/requirements/RQ_2CF7D138668E5CEF23C2AC.json')
        self.assertEqual(rq['sourceQuote'], c['quote']); self.assertEqual(rq['canonicalHash'], content_hash(rq))
        self.assertEqual(len(rq['checkItems']), 3); self.assertIn('变更', rq['checkItems'][1])
    def test_training_canonical_pending_history_and_two_nondefects_untouched(self):
        for path, h in F['preservedFiles'].items(): self.assertEqual(sha(source_bytes(path)), h, path)
        self.assertFalse(set(F['badClauseIds']) & set(F['excludedBoundedCorrectIds']))
        for row in F['rows']:
            self.assertIn(row['hazardId'], self.gate.eligible_hazards); self.assertIn(row['linkId'], self.gate.eligible_links)
        self.assertEqual(len(self.gate.eligible_hazards), 1671)
        self.assertEqual(len([k for k in self.gate.eligible_links if self.gate.links[k]['hazardId'] in self.gate.eligible_hazards]), 1817)
        self.assertNotIn('K_84CD742E5092AF652C2CEF43', self.gate.eligible_links)
    def test_smoking_and_dangerous_work_are_different_laws_and_branches(self):
        smoke = hazard('H_1201F11443914660BCC291055B')
        for token in ['火灾、爆炸危险','不能仅凭存放任意化学品','施工等特殊情况','事先办理审批手续','相应消防安全措施','不能仅因使用明火判为违规']:
            self.assertIn(token, smoke['conditions'])
        for suffix in ['2','3']:
            h = hazard('H_301DCA3CAE2A494C399B323116_'+suffix)
            self.assertIn('江苏省行政区域内',h['conditions']); self.assertIn('危险作业',h['conditions'])
        self.assertEqual(read('knowledge/links/K_XLSX_NEW14_08D430A73A95A65640FD0F8D.json')['clauseId'], 'C074')
    def test_agreement_or_contract_and_no_mechanical_template(self):
        h = hazard('H_462D38828DEBA46C8E23C177D2_1')
        self.assertIn('既未',h['title']); self.assertIn('也未',h['title'])
        for f in ['conditions','measures']:
            self.assertIn('或者',h[f]); self.assertIn('合同',h[f])
        for f in ['conditions','places','measures']:
            for bad in ['机械运动','防护装置','试运行']:
                self.assertNotIn(bad,str(h[f]))
        self.assertEqual(h['category'],'安全管理')
    def test_death_retraining_and_special_operators_keep_distinct_subjects(self):
        death = hazard('H_9F790C9B0EA34E59207BCCC1AD_4')
        special = hazard('H_9F790C9B0EA34E59207BCCC1AD_5')
        for token in ['第一款','矿山','金属冶炼','船舶修造','船舶拆解','运输单位','人员死亡','主要负责人和安全生产管理人员']:
            self.assertIn(token,death['conditions'])
        self.assertIn('不受第一款',special['conditions']); self.assertIn('特种作业人员',special['conditions'])
        self.assertIn('方可上岗作业',special['measures'])
        self.assertNotIn('不得独立',death['measures']); self.assertNotIn('六个月',death['measures'])
    def test_staffing_small_unit_exception_and_delegated_worker_count(self):
        small = hazard('H_326EBA1B38E66D1B605FA45292_3')
        big = hazard('H_326EBA1B38E66D1B605FA45292_2')
        for h in [small,big]:
            for token in ['第一款','以外','被派遣劳动者','国家']: self.assertIn(token,h['conditions'])
        for token in ['二十人以下','位置相邻','行业相近','业态相似','互助帮扶联合体','责任仍由本单位负责']:
            self.assertIn(token,small['conditions'])
        self.assertIn('超过一百人',big['conditions']); self.assertIn('一百人以下',small['conditions'])
    def test_hazchem_no_unreviewed_expansion_and_fire_all_five_categories(self):
        for hid in ['H_A7D8C5192004B9B1DB48E5CC_1','H_7FCC0C85E0C313B5599EBC67_1']:
            h = hazard(hid)
            self.assertIn('使用危险化学品从事生产的企业',h['conditions'])
            self.assertIn('任意',h['conditions'])
        fire = hazard('H_32B64EF4F22A7AAC5B023DFCB5_1')
        for token in ['大型核设施','主要港口','易燃易爆危险品','大型仓库','距离国家综合性消防救援队较远','全国重点文物保护单位']:
            self.assertIn(token,fire['conditions']); self.assertIn(token,fire['description'])
    def test_helpers_are_exact_nonmutating_and_keep_unknown_changes_visible(self):
        original = copy.deepcopy(self.gate); prior = pre_remaining_gate(self.gate)
        self.assertEqual(self.gate,original)
        changed = F['gateSnapshots']['2026-10-03']['changedLinks']
        self.assertEqual({k for k,v in self.gate.links.items() if prior.links[k]!=v},set(changed))
        for row in F['entities']+F['reviews']:
            raw = (ROOT/row['path']).read_bytes()
            self.assertEqual(pre_remaining_source_bytes(row['path'],raw),row['beforeFileText'].encode())
            with self.assertRaises(AssertionError): pre_remaining_source_bytes(row['path'],raw+b' ')
        self.assertEqual(pre_remaining_source_bytes('unknown',b'new'),b'new')
        for cid in F['badClauseIds']:
            self.assertEqual(pre_remaining_inventory('clauses',[(cid,'proposed')]),[(cid,'active')])
            with self.assertRaises(AssertionError): pre_remaining_inventory('clauses',[(cid,'active')])
        for kid in changed:
            bad = copy.deepcopy(self.gate); bad.links[kid]['clauseId']='C_UNREVIEWED'
            with self.assertRaises(AssertionError): pre_remaining_gate(bad)
        bad = copy.deepcopy(self.gate); bad.links['K_UNKNOWN']={'ok':False}
        self.assertEqual(pre_remaining_gate(bad).links['K_UNKNOWN'],{'ok':False})
    def test_negative_direction_corrections_do_not_label_compliance_as_hazard(self):
        alarm = hazard('H_2456A494C71E6807975B908C_1')
        risk = hazard('H_A7D8C5192004B9B1DB48E5CC_1')
        for f in ['title','description']:
            self.assertIn('或者',alarm[f]); self.assertIn('未',alarm[f])
            self.assertNotIn('并保证处于适用状态',alarm[f])
        for token in ['未建立','未开展','未按']:
            self.assertIn(token,risk['title'])
        self.assertIn('一项或多项',risk['description'])
        accident = hazard('H_462D38828DEBA46C8E23C177D2_3')
        self.assertIn('或者未通知',accident['title'])
        fire = hazard('H_32B64EF4F22A7AAC5B023DFCB5_1')
        self.assertIn('未依法建立承担',fire['title'])
    def test_alternative_failure_branches_and_unrelated_templates_removed(self):
        staff = hazard('H_326EBA1B38E66D1B605FA45292_2')
        for f in ['title','description']:
            self.assertIn('既未',staff[f]); self.assertIn('也未',staff[f])
            self.assertNotIn('安全防护、识别、监测或应急保障',staff[f])
        for hid in ['H_7D2425A6472F9ED7098B49315B_1','H_7D2425A6472F9ED7098B49315B_2','H_B8B0F1300667A2468DE9DD9B0D_1']:
            h = hazard(hid)
            self.assertIn('或者',h['title']); self.assertIn('或者',h['description'])
            self.assertNotIn('缺少完整、有效的文件或执行记录',h['description'])
        system = hazard('H_7FCC0C85E0C313B5599EBC67_1')
        self.assertNotIn('缺少完整、有效的文件或执行记录',system['description'])
        self.assertEqual(hazard('H_96049FDA8623F7EF0CDA4B1F73_1')['category'],'安全管理')
    def test_unqualified_training_institution_never_switches_off_supervision(self):
        h = hazard('H_D7F4B2B8F70D67B625BE3E5E95_3')
        self.assertIn('委托开展安全生产培训的情形',h['conditions'])
        self.assertIn('不能因受托机构不具备培训条件而免除',h['conditions'])
        self.assertNotIn('仅适用于江苏省行政区域内生产经营单位委托具备',h['conditions'])
        self.assertIn('另应选择具备安全生产培训条件的机构',h['conditions'])
    def snapshot(self):
        t=tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup); root=Path(t.name); ctx=ProfileContext(KNOW)
        for row in F['rows']:
            for key,obj in ctx.dependencies({'hazardId':row['hazardId'],'basisLinkIds':[row['linkId']]}).items():
                if key!='associationIds' and obj is not None: write(root,key+'.json',obj)
        return root
    def test_all_26_stale_or_tampered_branches_fail_closed(self):
        root=self.snapshot()
        for row in F['rows']:
            kid,hid=row['linkId'],row['hazardId']; rel=f'links/{kid}.json'; original=json.loads((root/rel).read_text())
            mutated={**original,'applicability':'未核全国通用范围'}; write(root,rel,mutated)
            gate=evaluate_release_gate(root,ASOF)
            self.assertNotIn(kid,gate.eligible_links); self.assertNotIn(hid,gate.eligible_hazards)
            write(root,rel,original)
        for row in F['reviews']:
            if '/hazards/' in row['path'] or '/links/' in row['path']:
                write(root,row['path'].removeprefix('knowledge/'),row['record']['previousReview'])
        gate=evaluate_release_gate(root,ASOF)
        self.assertFalse({r['linkId'] for r in F['rows']} & gate.eligible_links)

if __name__ == '__main__': unittest.main()
