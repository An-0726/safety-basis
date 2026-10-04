"""Exact scope, history and fail-closed tests for three existing flange entries.

These tests bind reviewed prose and source branches; they do not classify field
facts or claim that the production Gate interprets arbitrary legal language.
"""
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

from flange_scope_fixture import FIXTURE, HAZARD_EDITS, pre_flange_source_bytes
ROOT = Path(__file__).resolve().parents[3]
from recovery_cohort_fixture import pre_recovery_repo_root, evaluate_historical_snapshot
# This dated cohort is tested against its SHA-guarded predecessor, not new admissions.
ROOT = pre_recovery_repo_root(ROOT)
KNOW = ROOT / 'knowledge'
sys.path.insert(0, str(ROOT / 'tools/v4'))
from canonical import content_hash
from field_profiles import ProfileContext, public_projection
from release_gate_core import evaluate_release_gate
from recovery_cohort_fixture import evaluate_historical_snapshot as evaluate_release_gate

HAZARDS = {r['id'] for r in FIXTURE['entities'] if '/hazards/' in r['path']}
LINKS = {r['id'] for r in FIXTURE['entities'] if '/links/' in r['path']}
sha = lambda value: hashlib.sha256(value).hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def write(root, path, value):
    destination = root / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')


def replay(raw, row):
    if sha(raw) != row['oldFileSha256']:
        raise ValueError('baseline_file_sha256')
    result = json.loads(raw)
    if content_hash(result) != row['oldContentHash']:
        raise ValueError('baseline_content_hash')
    for key, expected in row['before'].items():
        if result[key] != expected:
            raise ValueError('baseline_field:' + key)
    result.update(row['after'])
    return result


class FlangeScopeSourceTests(unittest.TestCase):
    def test_exact_six_records_sixteen_fields_and_stable_unreviewed_fields(self):
        self.assertEqual(FIXTURE['baselineCommit'], 'cf7ef4de02e7df204fce5043b52c7fb70f2b60d9')
        self.assertEqual(len(FIXTURE['entities']), 6)
        self.assertEqual(sum(len(r['modifiedFields']) for r in FIXTURE['entities']), 16)
        for row in FIXTURE['entities']:
            with self.subTest(path=row['path']):
                actual = read(row['path'])
                self.assertEqual(actual, row['record'])
                self.assertEqual(actual, replay(row['beforeFileText'].encode(), row))
                self.assertEqual(sha((ROOT / row['path']).read_bytes()), row['fileSha256'])
                self.assertEqual(content_hash(actual), row['contentHash'])
                self.assertEqual({k:actual[k] for k in row['unchangedFields']}, row['unchangedFields'])
                self.assertFalse({'id','title','description','lifecycle','mode','role'} & set(row['modifiedFields']))
                expected = {'conditions','places','measures'} if '/hazards/' in row['path'] else {'applicability','reason'}
                if row['id'] == 'H_12158_9_11_1':
                    expected.add('category')
                self.assertEqual(set(row['modifiedFields']), expected)

    def test_guarded_replay_rejects_wrong_baseline_hash_and_field(self):
        for row in FIXTURE['entities']:
            raw = row['beforeFileText'].encode()
            with self.assertRaisesRegex(ValueError, 'baseline_file_sha256'):
                replay(raw+b' ', row)
            bad = copy.deepcopy(row)
            bad['oldContentHash'] = '0'*64
            with self.assertRaisesRegex(ValueError, 'baseline_content_hash'):
                replay(raw, bad)
            bad = copy.deepcopy(row)
            bad['before'][row['modifiedFields'][0]] = 'wrong source'
            with self.assertRaisesRegex(ValueError, 'baseline_field'):
                replay(raw, bad)

    def test_complete_original_clause_stays_byte_identical(self):
        row = FIXTURE['clause']
        self.assertEqual(sha((ROOT / row['path']).read_bytes()), row['fileSha256'])
        self.assertEqual(read(row['path']), row['record'])
        self.assertEqual(row['fileSha256'], '5e74d9618a0505271cd2cdc834593aca37bdba6cd668b3869b8d3b00699bc7dc')
        self.assertIn('导线跨接或金属法兰连接等措施', row['record']['quote'])
        self.assertIn('且不另接跨接线', row['record']['quote'])
        self.assertIn('大于0.03Ω', row['record']['quote'])

    def test_three_links_use_exact_same_scopes_and_existing_source_identity(self):
        for kid in LINKS:
            link = read(f'knowledge/links/{kid}.json')
            hazard = read(f"knowledge/hazards/{link['hazardId']}.json")
            self.assertEqual(link['applicability'], hazard['conditions'])
            self.assertEqual(link['clauseId'], 'C_12158_9_11')
            self.assertEqual(link['role'], 'direct')
            self.assertEqual(link['lifecycle'], 'active')
            self.assertEqual(hazard['category'], '电气安全')

    def test_six_substantive_reviews_preserve_history_and_bind_actual_contexts(self):
        self.assertEqual(len(FIXTURE['reviews']), 6)
        for row in FIXTURE['reviews']:
            review = read(row['path'])
            entity_path = row['path'].replace('/reviews', '')
            entity = read(entity_path)
            contract = next(r for r in FIXTURE['entities'] if r['path']==entity_path)
            self.assertEqual(review, row['record'])
            self.assertEqual(sha((ROOT/row['path']).read_bytes()), row['fileSha256'])
            self.assertEqual(review['reviewedContentHash'], content_hash(entity))
            self.assertEqual(review['historySha256'], content_hash(review['previousReview']))
            self.assertEqual(review['previousReviewFileSha256'], row['previousFileSha256'])
            self.assertNotEqual(review['reason'], review['previousReview']['reason'])
            self.assertEqual(review['checkedAt'], '2026-10-03')
            self.assertEqual(review['reviewedValues'], {'/'+k:entity[k] for k in contract['modifiedFields']})
            self.assertEqual(set(review['reviewedFields']), set(review['reviewedValues']))
            self.assertEqual(set(review['fieldEvidenceRefs']), set(review['reviewedFields']))
            self.assertEqual(review['evidenceRefs'], ['E_12158_GB 12158'])
            self.assertFalse(review['reviewEvidence']['siteFactsVerified'])
            self.assertFalse(review['reviewEvidence']['profileAdmission'])
            if review['entityType']=='link':
                self.assertEqual(review['contextHashes'], {
                    'hazard': content_hash(read(f"knowledge/hazards/{entity['hazardId']}.json")),
                    'clause': content_hash(read(f"knowledge/clauses/{entity['clauseId']}.json"))})

    def test_official_currency_and_original_pdf_provenance_are_distinguished(self):
        source = FIXTURE['sourceReview']
        self.assertEqual(source['originalPdfSha256'], 'd0444f1a030b8531482649b7b5bd7283eb1a0ae52dc3d7dacbc9b0028f7fac65')
        self.assertIn('openstd.samr.gov.cn', source['officialIdentityUrl'])
        self.assertIn('hipc.org.cn', source['originalPdfUrl'])
        self.assertIn('非标准发布机关原发页', source['sourceClass'])
        self.assertEqual(source['effectiveDate'], '2026-01-01')
        self.assertEqual(source['officialStatus'], '现行')
        self.assertIn('不适用于火炸药、电火工品、烟花爆竹', source['scopeQuote'])

    def test_historical_pin_projection_rejects_drift_and_preserves_unrelated_bytes(self):
        for path,row in HAZARD_EDITS.items():
            raw = (ROOT/path).read_bytes()
            self.assertEqual(sha(pre_flange_source_bytes(path,raw)), row['oldFileSha256'])
            with self.assertRaisesRegex(AssertionError,'flange final source drift'):
                pre_flange_source_bytes(path,raw+b' ')
        self.assertEqual(pre_flange_source_bytes('knowledge/hazards/H_UNKNOWN.json',b'drift'),b'drift')


class FlangeSemanticBoundaryTests(unittest.TestCase):
    def test_chapter_one_exclusions_and_chapter_nine_scope_are_explicit(self):
        for hid in HAZARDS:
            scope = read(f'knowledge/hazards/{hid}.json')['conditions']
            for text in ['静电放电引发燃烧和爆炸','静电危险场所设计和管理','气态和粉态物料',
                         '金属设备与设备之间、管道与管道之间','不适用于火炸药、电火工品、烟花爆竹',
                         '静电电击','仅可参考使用']:
                self.assertIn(text,scope)
            self.assertNotIn('金属管道连接处',scope)

    def test_conductivity_branch_preserves_alternative_implementation(self):
        h = read('knowledge/hazards/H_12158_9_11_1.json')
        self.assertIn('导线跨接、金属法兰连接等均可作为实现方式',h['conditions'])
        self.assertIn('不以未另设跨接线这一外观单独判定本分支不符合',h['conditions'])
        self.assertIn('导线跨接或金属法兰连接等适用措施',h['measures'])
        self.assertIn('保证连接处导电良好',h['measures'])

    def test_bolt_branch_keeps_both_trigger_conditions_and_source_term(self):
        h = read('knowledge/hazards/H_12158_9_11_2.json')
        for field in ['conditions','measures']:
            self.assertIn('金属法兰连接且不另接跨接线',h[field])
            self.assertIn('两个以上的螺栓连接',h[field])
            self.assertNotIn('三个',h[field])
        self.assertIn('不向所有法兰或所有用电场所无条件推广',h['conditions'])
        self.assertIn('大于0.03Ω时',h['measures'])

    def test_resistance_branch_preserves_strict_threshold_and_observation_boundary(self):
        h = read('knowledge/hazards/H_12158_9_11_3.json')
        self.assertIn('仅当每一对法兰或螺纹接头间电阻值大于0.03Ω时',h['conditions'])
        self.assertIn('未测电阻且仅观察到未设独立跨接线',h['conditions'])
        self.assertIn('不能据此直接认定本分支不符合',h['conditions'])
        self.assertNotIn('大于或等于',h['conditions'])
        self.assertNotIn('≥',h['conditions'])
        self.assertIn('每一对法兰或螺纹接头间电阻值大于0.03Ω',h['measures'])

    def test_no_branch_exempts_dust_collector_flange_independent_requirement(self):
        self.assertIn('管道连接法兰应进行防静电跨接', FIXTURE['sourceReview']['section9_5'])
        for hid in HAZARDS:
            self.assertIn('除尘系统管道连接法兰还应独立核对第9.5条的防静电跨接要求，不能据本分支免除',
                          read(f'knowledge/hazards/{hid}.json')['conditions'])

    def test_mechanical_and_general_energization_templates_are_removed(self):
        for hid in HAZARDS:
            h = read(f'knowledge/hazards/{hid}.json')
            text = ' '.join([h['conditions'],h['measures']]+h['places'])
            for contamination in ['夹卷','剪切','临时用电','再送电使用','防护装置、结构、通道','一般用电场所']:
                self.assertNotIn(contamination,text)


class FlangeScopeGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = ProfileContext(KNOW)

    def snapshot(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for kid in LINKS:
            link = read(f'knowledge/links/{kid}.json')
            deps = self.context.dependencies({'hazardId':link['hazardId'],'basisLinkIds':[kid]})
            for key,obj in deps.items():
                if key!='associationIds':
                    self.assertIsNotNone(obj,key)
                    write(root,key+'.json',obj)
        return root

    def test_current_gate_and_all_inherited_profiles_remain_available(self):
        gate = evaluate_release_gate(KNOW,date(2026,10,3))
        self.assertTrue(HAZARDS<=gate.eligible_hazards)
        self.assertTrue(LINKS<=gate.eligible_links)
        self.assertEqual(len(gate.eligible_hazards),1671)
        self.assertEqual(len({kid for kid in gate.eligible_links if gate.links[kid]['hazardId'] in gate.eligible_hazards}),1817)
        self.assertNotIn('H052',gate.eligible_hazards)
        profiles = public_projection(KNOW,as_of=date(2026,10,3))
        self.assertEqual(len(profiles['public']['records']),25)
        self.assertEqual(profiles['inventory']['excludedProfiles'],[])

    def test_old_review_reuse_fails_both_content_and_context_bindings(self):
        root=self.snapshot()
        for row in FIXTURE['reviews']:
            write(root,row['path'].removeprefix('knowledge/'),row['record']['previousReview'])
        gate=evaluate_release_gate(root,date(2026,10,3))
        self.assertFalse(HAZARDS&gate.eligible_hazards)
        self.assertFalse(LINKS&gate.eligible_links)
        for kid in LINKS:
            self.assertIn('BLOCK_REVIEW_STALE',gate.links[kid]['reasons'])
            self.assertIn('BLOCK_REVIEW_CONTEXT_STALE:hazard_context_stale',gate.links[kid]['reasons'])

    def test_old_scope_or_threshold_mutations_fail_closed_without_resigning(self):
        root=self.snapshot()
        for row in FIXTURE['entities']:
            changed=copy.deepcopy(row['record'])
            field='conditions' if '/hazards/' in row['path'] else 'applicability'
            changed[field]=row['before'][field]
            write(root,row['path'].removeprefix('knowledge/'),changed)
        gate=evaluate_release_gate(root,date(2026,10,3))
        self.assertFalse(HAZARDS&gate.eligible_hazards)
        self.assertFalse(LINKS&gate.eligible_links)
        root=self.snapshot()
        h=read('knowledge/hazards/H_12158_9_11_3.json')
        h['conditions']=h['conditions'].replace('大于0.03Ω','大于或等于0.03Ω')
        write(root,'hazards/'+h['id']+'.json',h)
        gate=evaluate_release_gate(root,date(2026,10,3))
        self.assertNotIn(h['id'],gate.eligible_hazards)

    def test_link_hash_only_refresh_cannot_hide_old_hazard_context(self):
        root=self.snapshot()
        for row in FIXTURE['reviews']:
            if '/links/' not in row['path']:continue
            changed=copy.deepcopy(row['record']['previousReview'])
            changed['reviewedContentHash']=row['record']['reviewedContentHash']
            write(root,row['path'].removeprefix('knowledge/'),changed)
        gate=evaluate_release_gate(root,date(2026,10,3))
        self.assertFalse(LINKS&gate.eligible_links)
        self.assertFalse(HAZARDS&gate.eligible_hazards)

    def test_current_version_does_not_apply_before_2026_effective_date(self):
        root=self.snapshot()
        old=evaluate_release_gate(root,date(2025,12,31))
        current=evaluate_release_gate(root,date(2026,1,1))
        self.assertFalse(HAZARDS&old.eligible_hazards)
        self.assertFalse(LINKS&old.eligible_links)
        self.assertTrue(HAZARDS<=current.eligible_hazards)
        self.assertTrue(LINKS<=current.eligible_links)


if __name__=='__main__':
    unittest.main()
