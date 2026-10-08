"""Exact 331-ID scope, source-derived outcomes and no whole-claim overstatement."""
from collections import Counter
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
REAL_ROOT = ROOT
from pending_source_cohort_fixture import pre_pending_repo_root
ROOT = pre_pending_repo_root(ROOT)
sys.path[:0] = [str(ROOT / 'tools/browser'), str(ROOT / 'tools/v4')]
from freeze_complete_remaining_history import BASELINE, TREE, load_authorization


def require(condition, message):
    if not condition: raise AssertionError(message)


def validate_index(index, before, current, *, old_public, public, old_links, public_links,
                   links, clauses, versions, file_hashes, expected_total=331):
    require(index['schemaVersion'] == 'complete-remaining-disposition-index-v1', 'Wrong coverage index schema')
    require(index['baselineCommit'] == BASELINE and index['baselineTree'] == TREE, 'Wrong coverage predecessor')
    proposed = {hid for hid, h in before.items() if h['lifecycle'] == 'proposed'}
    excluded = {hid for hid, h in before.items() if h['lifecycle'] == 'active' and hid not in old_public}
    scope = proposed | excluded
    rows = index['records']; ids = [r['hazardId'] for r in rows]
    require(len(scope) == expected_total and len(ids) == len(set(ids)) == expected_total and set(ids) == scope,
            'Coverage must include every baseline proposed and active-excluded ID exactly once')
    source_chains = {}
    for kid in sorted(public_links):
        k = links[kid]; c = clauses[k['clauseId']]; lv = versions[c['lawVersionId']]
        source_chains.setdefault(k['hazardId'], []).append({'linkId': kid, 'clauseId': c['id'], 'lawVersionId': lv['id'],
            'articlePath': c.get('articlePath') or c.get('clauseNumber') or '', 'role': k['role'],
            'applicability': k['applicability'], 'sourceUrl': c.get('sourceUrl') or lv.get('sourceUrl') or ''})
    for row in rows:
        hid = row['hazardId']; h = current[hid]
        require(row['dispositionReviewCompleted'] is True, 'Missing individual disposition: ' + hid)
        require(row['substantiveReviewCompleted'] is (row['dispositionCode'] != 'explicitly_skipped'),
                'Skipped status cannot be counted as substantive source review: ' + hid)
        require(row['siteFactsConfirmed'] is False and row['wholeOriginalClaimCertified'] is False,
                'Bounded source coverage cannot certify site facts or the whole original claim: ' + hid)
        for field in ('unsupportedOriginalBranches', 'scopeExclusions', 'caseEvidenceRequirements'):
            require(isinstance(row[field], list) and all(isinstance(v, str) and v.strip() for v in row[field]),
                    'Three boundary types must remain distinct explicit arrays: ' + hid + ':' + field)
        require(isinstance(row['sourceOrRuleMappingGapRemains'], bool), 'Missing source-gap decision: ' + hid)
        require(row['baselineLifecycle'] == before[hid]['lifecycle'], 'Baseline lifecycle drift: ' + hid)
        require(row['currentLifecycle'] == h['lifecycle'], 'Current lifecycle drift: ' + hid)
        require(row['currentTitle'] == h['title'] and row['baselineTitle'] == before[hid]['title'], 'Title drift: ' + hid)
        require(row['currentPublicRule'] is (hid in public), 'Claimed public status differs from current Gate: ' + hid)
        require(row['entityFileSha256'] == file_hashes[hid], 'Indexed entity bytes changed: ' + hid)
        require(row['mergedInto'] == h.get('mergedInto'), 'Canonical mapping differs from source: ' + hid)
        require(row['finalDisposition'] and row['dispositionCode'] and row['dispositionReason'], 'Missing final result: ' + hid)
        chain = source_chains.get(hid, [])
        require(sorted(row['boundedRuleChain'], key=lambda b: b['linkId']) == chain,
                'Indexed bounded rule chain differs from exact current source: ' + hid)
        for candidate in row['comparisonCandidates']:
            require(candidate['currentlyPublic'] is (candidate['hazardId'] in public), 'Comparison public status drift: ' + hid)
            require(candidate['meaning'].startswith('comparison_only;'), 'Comparison silently became whole-claim coverage: ' + hid)
        if row['dispositionCode'] == 'bounded_merge':
            require(h['lifecycle'] == 'superseded' and row['mergedInto'] in public,
                    'Bounded merge needs an existing current canonical rule: ' + hid)
        if row['dispositionCode'] == 'explicitly_skipped':
            require(h == before[hid] and hid not in public and row['sourceCurrentnessReview'] == 'explicitly_skipped',
                    'Skipped item changed or gained a source-currentness claim: ' + hid)
    summary = index['summary']
    expected_summary = {
        'totalReviewedExistingIds': len(scope), 'baselineProposed': len(proposed), 'baselineActiveExcluded': len(excluded),
        'substantivelyReviewed': sum(r['dispositionCode'] != 'explicitly_skipped' for r in rows),
        'explicitUserSkips': sum(r['dispositionCode'] == 'explicitly_skipped' for r in rows),
        'byDisposition': dict(sorted(Counter(r['dispositionCode'] for r in rows).items())),
        'byGroup': dict(sorted(Counter(r['group'] for r in rows).items())),
        'originalSourceOrRuleMappingResidualIds': sum(r['sourceOrRuleMappingGapRemains'] for r in rows),
        'currentPublicFromOriginal331': len(scope & public),
        'currentActiveExcludedFromOriginal331': sum(current[hid]['lifecycle'] == 'active' and hid not in public for hid in scope),
        'currentProposedFromOriginal331': sum(current[hid]['lifecycle'] == 'proposed' for hid in scope),
        'currentSupersededFromOriginal331': sum(current[hid]['lifecycle'] == 'superseded' for hid in scope),
    }
    require(summary == expected_summary, 'Index totals or branch/source-gap accounting do not match its exact rows')
    expected_delta = {'baselineHazards': len(old_public), 'candidateHazards': len(public),
        'addedHazards': sorted(public - old_public), 'withdrawnHazards': sorted(old_public - public),
        'baselineLinks': len(old_links), 'candidateLinks': len(public_links),
        'addedLinks': sorted(public_links - old_links), 'withdrawnLinks': sorted(old_links - public_links)}
    require(index['publicationDelta'] == expected_delta, 'Publication delta differs from exact public source sets')


class CompleteRemainingCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from complete_remaining_cohort_fixture import pre_complete_repo_root
        from release_gate_core import evaluate_release_gate, load_dir
        import complete_remaining_acceptance as current_browser
        import residual_clause_acceptance as prior_browser
        cls.authority = load_authorization(ROOT)
        cls.index = json.loads((ROOT / cls.authority['coverageIndexPath']).read_text())
        prior = pre_complete_repo_root(ROOT)
        cls.predecessor_root = prior
        cls.before = load_dir(prior / 'knowledge', 'hazards')
        cls.before_links = load_dir(prior / 'knowledge', 'links')
        cls.current = load_dir(ROOT / 'knowledge', 'hazards')
        cls.links = load_dir(ROOT / 'knowledge', 'links')
        cls.clauses = load_dir(ROOT / 'knowledge', 'clauses')
        cls.versions = load_dir(ROOT / 'knowledge', 'law-versions')
        gate = evaluate_release_gate(ROOT / 'knowledge', date.fromisoformat(cls.index['asOf']))
        cls.public = set(gate.eligible_hazards)
        cls.public_links = {kid for kid in gate.eligible_links if cls.links[kid]['hazardId'] in cls.public}
        cls.prior_fixture, cls.current_fixture = prior_browser.load_expectations(), current_browser.load_expectations(root=ROOT)
        cls.old_public = set(cls.prior_fixture['expectedIds']['hazards'])
        cls.old_links = set(cls.prior_fixture['expectedIds']['links'])
        cls.file_hashes = {hid: hashlib.sha256((ROOT / f'knowledge/hazards/{hid}.json').read_bytes()).hexdigest() for hid in cls.current}

    def validate(self, index):
        validate_index(index, self.before, self.current, old_public=self.old_public, public=self.public,
            old_links=self.old_links, public_links=self.public_links, links=self.links, clauses=self.clauses,
            versions=self.versions, file_hashes=self.file_hashes)

    def test_exact_331_scope_final_rows_chains_and_summary_reproduce_from_source(self):
        self.validate(self.index)
        self.assertEqual(self.index['summary']['byGroup'], {'electrical-signs': 64, 'equipment-coating': 118,
            'fire-gas': 41, 'management-hazchem': 108})
        self.assertEqual(self.index['summary']['explicitUserSkips'], 4)
        self.assertEqual(self.index['publicationDelta']['withdrawnHazards'], sorted(self.authority['withdrawals']['hazards']))
        self.assertEqual(self.index['publicationDelta']['withdrawnLinks'], sorted(self.authority['withdrawals']['links']))
        current_scope_public = {r['hazardId'] for r in self.index['records'] if r['currentPublicRule']}
        self.assertLessEqual(current_scope_public, set(self.current_fixture['changedHazardIds']))

    def test_all_four_explicitly_skipped_hazard_and_link_records_keep_exact_baseline_bytes(self):
        skipped = [r['hazardId'] for r in self.index['records'] if r['dispositionCode'] == 'explicitly_skipped']
        self.assertEqual(len(skipped), 4)
        paths = set()
        for hid in skipped:
            old_links = {kid for kid, k in self.before_links.items() if k['hazardId'] == hid}
            new_links = {kid for kid, k in self.links.items() if k['hazardId'] == hid}
            self.assertEqual(new_links, old_links, 'Skipped link inventory changed: ' + hid)
            paths.update((f'knowledge/hazards/{hid}.json', f'knowledge/reviews/hazards/{hid}.json'))
            for kid in old_links:
                paths.update((f'knowledge/links/{kid}.json', f'knowledge/reviews/links/{kid}.json'))
        self.assertEqual(len(paths), 16)
        for relative in sorted(paths):
            with self.subTest(path=relative):
                self.assertEqual((ROOT / relative).read_bytes(), (self.predecessor_root / relative).read_bytes())

    def test_missing_duplicate_same_count_swap_and_false_whole_claim_fail(self):
        for mode in ('missing', 'duplicate', 'swap', 'whole_claim', 'public_status', 'entity_hash', 'summary'):
            index = copy.deepcopy(self.index)
            if mode == 'missing': index['records'].pop()
            elif mode == 'duplicate': index['records'][-1] = index['records'][0]
            elif mode == 'swap': index['records'][-1]['hazardId'] = 'H_UNKNOWN_SCOPE'
            elif mode == 'whole_claim': index['records'][0]['wholeOriginalClaimCertified'] = True
            elif mode == 'public_status': index['records'][0]['currentPublicRule'] = not index['records'][0]['currentPublicRule']
            elif mode == 'entity_hash': index['records'][0]['entityFileSha256'] = '0' * 64
            else: index['summary']['originalSourceOrRuleMappingResidualIds'] += 1
            with self.subTest(mode=mode), self.assertRaises(AssertionError): self.validate(index)

    def test_every_indexed_public_chain_requires_its_actual_applicability(self):
        for row in self.index['records']:
            if not row['boundedRuleChain']: continue
            index = copy.deepcopy(self.index)
            target = next(r for r in index['records'] if r['hazardId'] == row['hazardId'])
            target['boundedRuleChain'][0]['applicability'] = 'unrelated'
            with self.subTest(hazard=row['hazardId']), self.assertRaisesRegex(AssertionError, 'rule chain'):
                self.validate(index)


if __name__ == '__main__':
    unittest.main()
