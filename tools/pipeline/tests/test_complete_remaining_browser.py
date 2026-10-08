"""Complete source-pinned public cohort, exact withdrawals and all rendered flows."""
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
REAL_ROOT = ROOT
from pending_source_cohort_fixture import pre_pending_repo_root
ROOT = pre_pending_repo_root(ROOT)
sys.path[:0] = [str(ROOT / 'tools/browser'), str(ROOT / 'tools/v4')]
import complete_remaining_acceptance as CURRENT
import residual_clause_acceptance as PRIOR
import recovery_release_acceptance as QA
from complete_remaining_cohort_fixture import fixture as history_fixture, pre_complete_repo_root
from freeze_complete_remaining_history import load_authorization
from freeze_recovery_expectations import project_expectations
from release_gate_core import evaluate_release_gate, load_dir
from release_snapshot import source_hashes, snapshot_digest


def projection(frozen):
    result = copy.deepcopy(frozen['expectedIds'])
    result['lawClauses'] = result['clauses'][:]
    result['details'] = [{'id': r['id'], 'hazard': {**copy.deepcopy(r['hazard']), 'displayCategory': r['displayCategory']},
        'bases': copy.deepcopy(r['bases'])} for r in frozen['records']]
    return result


def mutate_detail(original, hid, field, value, basis_index=None):
    # Validators are read-only: copy only the mutated branch, keeping negatives
    # exhaustive without repeatedly copying every unrelated quote/table.
    result = dict(original); result['details'] = list(original['details'])
    index = next(i for i, r in enumerate(result['details']) if r['id'] == hid)
    row = dict(result['details'][index]); result['details'][index] = row
    if basis_index is None:
        row['hazard'] = {**row['hazard'], field: value}
    else:
        row['bases'] = list(row['bases']); row['bases'][basis_index] = {**row['bases'][basis_index], field: value}
    return result


class CompleteRemainingBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.current, cls.prior = CURRENT.load_expectations(root=ROOT), PRIOR.load_expectations()
        cls.authority = load_authorization(ROOT)
        cls.public_authored = set(cls.current['batchAudit']['requiredFormalHazardIds'])

    def test_all_membership_and_authored_or_dependent_formal_details_are_source_derived(self):
        f = self.current
        self.assertEqual(f['asOf'], '2026-10-05')
        QA.validate_source_pins(f, ROOT)
        gate = evaluate_release_gate(ROOT / 'knowledge', date.fromisoformat(f['asOf']))
        links = load_dir(ROOT / 'knowledge', 'links')
        kids = {kid for kid in gate.eligible_links if links[kid]['hazardId'] in gate.eligible_hazards}
        self.assertEqual(f['expectedIds']['hazards'], sorted(gate.eligible_hazards))
        self.assertEqual(f['expectedIds']['links'], sorted(kids))
        self.assertEqual(f['expectedIds']['clauses'], sorted({links[kid]['clauseId'] for kid in kids}))
        self.assertEqual(len(self.prior['records']), 211)
        affected_hazards = {Path(path).stem for path in history_fixture()['records']
            if Path(path).parts[:2] == ('knowledge', 'hazards')}
        self.assertEqual(self.public_authored, affected_hazards & gate.eligible_hazards)
        batch_paths = {p.removeprefix('knowledge/') for p in history_fixture()['records'] if p.startswith('knowledge/')}
        affected_details = sorted(r['id'] for r in f['records'] if set(r['changedDependencies']) & batch_paths)
        self.assertEqual(f['batchAudit']['currentBatchHazardIds'], affected_details)
        self.assertTrue(self.public_authored)
        self.assertLessEqual(self.public_authored, set(f['changedHazardIds']))
        self.assertEqual(f['batchAudit']['withdrawals'], self.authority['withdrawals'])
        CURRENT.validate_preservation(f, self.prior, self.authority['withdrawals'])

    def test_current_major_catalog_keeps_110_clauses_and_exact_25_hazards_with_four_bounded_additions(self):
        from major_criteria import public_projection
        projected = public_projection(ROOT / 'knowledge', as_of=date(2026, 10, 5))
        clauses = {c['clauseId'] for standard in projected['catalog']['standards'] for c in standard['clauses']}
        self.assertEqual(len(clauses), 110)
        added = {
            ('H_CF_MAJOR_01', 'K_CF_MAJOR_01_C_PDDB_11', 'C_PDDB_11'),
            ('H_CF_MAJOR_06', 'K_CF_MAJOR_06_C_PDDB_7', 'C_PDDB_7'),
            ('H_CF_MAJOR_08', 'K_CF_MAJOR_08_C_PDDB_11', 'C_PDDB_11'),
            ('H_AA6382B9890B42B1B70DC3EA3B', 'K_XLSX_NEW14_0A6A84FB4A52AA3F93F30386', 'C_PDDB_7'),
        }
        added_hazards = {hid for hid, _, _ in added}
        expected_hazards = sorted(set(self.prior['expectedIds']['majorHazards']) | added_hazards)
        self.assertEqual(len(expected_hazards), 25)
        self.assertEqual(projected['topic']['hazardIds'], expected_hazards)
        self.assertEqual(self.current['expectedIds']['majorHazards'], expected_hazards)
        actual_added = [a for a in projected['topic']['associations'] if a['hazardId'] in added_hazards]
        self.assertEqual(len(actual_added), 4)
        self.assertEqual({(a['hazardId'], a['linkId'], a['clauseId']) for a in actual_added}, added)
        for association in actual_added:
            source = json.loads((ROOT / f"knowledge/links/{association['linkId']}.json").read_text())
            self.assertEqual(association['lawVersionId'], 'L019')
            self.assertEqual(association['role'], 'direct')
            self.assertEqual(association['jurisdictionCode'], 'CN')
            self.assertEqual(association['applicability'], source['applicability'])
        pending = {'H_68196C0A0FBDDAF0354E0F71', 'H_B552B08A4FD28A8770CDC2BB'}
        self.assertFalse(pending & set(expected_hazards))
        self.assertFalse(pending & set(self.current['expectedIds']['hazards']))
        catalog = json.loads((ROOT / 'knowledge/major-criteria/v1/catalog.json').read_text())
        national = next(s for s in catalog['standards'] if s['lawVersionId'] == 'L019')
        self.assertEqual({r['hazardId'] for r in national['pendingTopicLinks']}, pending)
        from field_profiles import public_projection as profile_projection
        profiles = profile_projection(ROOT / 'knowledge', as_of=date(2026, 10, 5))['public']['records']
        self.assertEqual(len(profiles), 25)
        self.assertEqual(sorted(p['id'] for p in profiles), self.prior['expectedIds']['profiles'])
        self.assertEqual(self.current['expectedIds']['profiles'], self.prior['expectedIds']['profiles'])

    def test_every_approved_withdrawal_has_precise_negative_membership_and_detail_checks(self):
        for kind, rows in self.authority['withdrawals'].items():
            self.assertEqual(set(self.prior['expectedIds'][kind]) - set(self.current['expectedIds'][kind]), set(rows))
            for ident, reason in rows.items():
                with self.subTest(kind=kind, ident=ident):
                    self.assertTrue(reason.strip())
                    self.assertNotIn(ident, self.current['expectedIds'][kind])
                    got = projection(self.current)
                    got[kind] = sorted([*got[kind], ident])
                    with self.assertRaises(AssertionError): QA.validate_projection(self.current, got)
                    if kind == 'hazards':
                        self.assertNotIn(ident, self.current['changedHazardIds'])
                    else:
                        self.assertFalse(any(b['linkId'] == ident for row in self.current['records'] for b in row['bases']))

    def test_freeze_reproduces_only_from_current_source_and_exact_saved_change_hashes(self):
        f = self.current
        hashes = source_hashes(ROOT / 'knowledge'); baseline = dict(hashes)
        for path, change in f['sourceChanges'].items():
            self.assertEqual(hashes.get(path), change['afterSha256'])
            if change['beforeSha256'] is None: baseline.pop(path, None)
            else: baseline[path] = change['beforeSha256']
        reproduced = project_expectations(ROOT / 'knowledge', date.fromisoformat(f['asOf']), hashes=hashes,
            baseline_commit=f['baselineCommit'], baseline=baseline)
        reproduced['knowledgeSnapshotHash'] = snapshot_digest(hashes)
        source_projection = copy.deepcopy(f); source_projection.pop('batchAudit')
        self.assertEqual(reproduced, source_projection)
        for relative, row in history_fixture()['records'].items():
            if not relative.startswith('knowledge/'): continue
            path = relative.removeprefix('knowledge/')
            # If a current edit exactly restores the original oldest baseline,
            # it has no cumulative delta; it still needs current detail coverage.
            if path in f['sourceChanges']:
                self.assertEqual(f['sourceChanges'][path]['afterSha256'], row['afterSha256'])
        for row in f['records']:
            self.assertLessEqual(set(row['changedDependencies']), set(f['sourceChanges']))

    def test_previous_fixture_cannot_authorize_current_source_or_release(self):
        self.assertNotEqual(CURRENT.FIXTURE, PRIOR.FIXTURE)
        QA.validate_source_pins(self.prior, pre_complete_repo_root(ROOT))
        with self.assertRaisesRegex(AssertionError, 'source snapshot changed'): QA.validate_source_pins(self.prior, ROOT)
        with self.assertRaisesRegex(AssertionError, 'not the source-pinned'):
            QA.validate_release_source(self.current, {'releaseHash': 'a' * 64, 'asOf': self.current['asOf'],
                'knowledge': {'snapshotSha256': self.prior['knowledgeSnapshotHash']}}, 'a' * 64)
        with self.assertRaisesRegex(AssertionError, 'effective date'):
            QA.validate_release_source(self.current, {'releaseHash': 'a' * 64, 'asOf': '2020-01-01',
                'knowledge': {'snapshotSha256': self.current['knowledgeSnapshotHash']}}, 'a' * 64)

    def test_all_authored_formal_fields_and_every_exact_basis_reject_mutation(self):
        original = projection(self.current)
        QA.validate_projection(self.current, original)
        for hid in self.public_authored:
            row = next(r for r in self.current['records'] if r['id'] == hid)
            for field in ('title', 'description', 'conditions', 'measures', 'category', 'places', 'checked', 'status', 'displayCategory'):
                got = mutate_detail(original, hid, field, ['wrong'] if field == 'places' else 'wrong')
                with self.subTest(hazard=hid, field=field), self.assertRaises(AssertionError):
                    QA.validate_projection(self.current, got)
            for index in range(len(row['bases'])):
                for field in ('linkId', 'clauseId', 'lawId', 'lawName', 'article', 'quote', 'role', 'applicability',
                              'sourceUrl', 'jurisdictionCode', 'clauseRegion', 'lawRegion', 'contentParts'):
                    got = mutate_detail(original, hid, field, ['wrong'] if field == 'contentParts' else 'wrong', index)
                    with self.subTest(hazard=hid, basis=index, field=field), self.assertRaises(AssertionError):
                        QA.validate_projection(self.current, got)

    def test_same_count_swaps_duplicates_missing_ids_and_unknown_source_changes_fail(self):
        for key in (*QA.PUBLIC_SETS, 'lawClauses'):
            for mode in ('swap', 'duplicate', 'missing'):
                got = projection(self.current)
                if mode == 'swap': got[key][-1] += '_UNEXPECTED'
                elif mode == 'duplicate': got[key][-1] = got[key][0]
                else: got[key].pop()
                with self.subTest(key=key, mode=mode), self.assertRaises(AssertionError): QA.validate_projection(self.current, got)
        hashes = source_hashes(ROOT / 'knowledge')
        for mode in ('unknown_addition', 'removal', 'known_mutation'):
            changed = dict(hashes)
            if mode == 'unknown_addition': changed['hazards/H_UNREVIEWED.json'] = '0' * 64
            elif mode == 'removal': del changed[next(iter(changed))]
            else: changed[next(iter(changed))] = '0' * 64
            with self.subTest(mode=mode), patch('release_snapshot.source_hashes', return_value=changed):
                with self.assertRaisesRegex(AssertionError, 'source snapshot changed'): QA.validate_source_pins(self.current, ROOT)

    def test_copy_retains_all_quotes_applicability_and_verified_dates(self):
        for row in self.current['records']:
            if row['id'] not in self.public_authored: continue
            plain = QA.expected_clipboard(row); full = QA.expected_full_clipboard(row, 'test.complete')
            self.assertTrue(full.startswith(plain + '\n\n'))
            self.assertTrue(full.endswith('数据库版本：test.complete。'))
            self.assertIn(row['hazard']['checked'], full)
            for basis in row['bases']:
                self.assertIn(basis['quote'], plain); self.assertIn(basis['applicability'], plain)

    def test_date_advance_requires_identical_complete_source_projection_and_audit(self):
        projected = CURRENT.fixture_for_release_date(self.current, '2026-10-06', ROOT)
        expected = copy.deepcopy(self.current); expected['asOf'] = '2026-10-06'
        self.assertEqual(projected, expected)
        with self.assertRaisesRegex(AssertionError, 'new review and freeze'):
            CURRENT.fixture_for_release_date(self.current, '2027-02-01', ROOT)

    def test_historical_loader_keeps_its_original_fixture_and_render_contract(self):
        self.assertEqual(CURRENT.load_expectations(root=ROOT), self.current)
        with self.assertRaisesRegex(AssertionError, 'Reviewed batch audit source changed'):
            CURRENT.load_expectations(root=REAL_ROOT)


if __name__ == '__main__':
    unittest.main()
