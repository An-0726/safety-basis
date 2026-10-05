"""Mutation guards for whole-public-set/browser source contracts, without GUI."""
import copy
from datetime import date
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
from official_clause_cohort_fixture import pre_official_repo_root
# Preserve the dated cohort against its exact, fail-closed batch predecessor.
ROOT = pre_official_repo_root(ROOT)
sys.path[:0] = [str(ROOT / 'tools/browser'), str(ROOT / 'tools/v4')]
import recovery_release_acceptance as QA
import electrical_candidate_acceptance as ELECTRICAL
import repair_acceptance as REPAIR
import technical_citation_acceptance as TECHNICAL
from release_gate_core import evaluate_release_gate, load_dir
from major_criteria import public_projection as major_projection
from field_profiles import public_projection as profile_projection
F = QA.load_expectations()


def projection(fixture=F):
    result = copy.deepcopy(fixture['expectedIds'])
    result['lawClauses'] = result['clauses'][:]
    result['details'] = [{'id': row['id'], 'hazard': {**copy.deepcopy(row['hazard']), 'displayCategory': row['displayCategory']},
                           'bases': copy.deepcopy(row['bases'])} for row in fixture['records']]
    return result


def rendered(row):
    result = {key: row['hazard'][key] for key in ('title', 'description', 'conditions', 'measures')}
    result.update(id=row['id'], category=row['displayCategory'], places=' · '.join(row['hazard']['places']), bases=[])
    for basis in row['bases']:
        got = {key: basis[key] for key in ('linkId', 'lawId', 'lawName', 'article', 'quote', 'applicability', 'sourceUrl')}
        got.update(roleLabel=REPAIR.ROLE_LABELS[basis['role']], metadataText='标准 · ' + basis['lawRegion'] + ' · 现行有效', tables=QA.expected_tables(basis))
        result['bases'].append(got)
    return result


class RecoveryBrowserAcceptanceTests(unittest.TestCase):
    def test_complete_snapshot_and_all_current_source_memberships_are_bound(self):
        QA.validate_source_pins(F, ROOT)
        as_of = date.fromisoformat(F['asOf'])
        gate = evaluate_release_gate(ROOT / 'knowledge', as_of)
        links = load_dir(ROOT / 'knowledge', 'links')
        kids = {k for k in gate.eligible_links if links[k]['hazardId'] in gate.eligible_hazards}
        expected = {'hazards': sorted(gate.eligible_hazards), 'links': sorted(kids),
            'clauses': sorted({links[k]['clauseId'] for k in kids}),
            'majorHazards': major_projection(ROOT / 'knowledge', as_of=as_of)['topic']['hazardIds'],
            'profiles': sorted(p['id'] for p in profile_projection(ROOT / 'knowledge', as_of=as_of)['public']['records'])}
        self.assertEqual(F['expectedIds'], expected)
        self.assertIn('H052', F['changedHazardIds'])
        self.assertNotIn(F['unpublishedProbeId'], expected['hazards'])

    def test_freeze_is_reproducible_from_source_without_reading_any_built_bundle(self):
        from freeze_recovery_expectations import project_expectations
        from release_snapshot import source_hashes, snapshot_digest
        hashes = source_hashes(ROOT / 'knowledge')
        baseline = dict(hashes)
        for path, change in F['sourceChanges'].items():
            if change['beforeSha256'] is None:
                baseline.pop(path, None)
            else:
                baseline[path] = change['beforeSha256']
        reproduced = project_expectations(ROOT / 'knowledge', date.fromisoformat(F['asOf']),
            hashes=hashes, baseline_commit=F['baselineCommit'], baseline=baseline)
        reproduced['knowledgeSnapshotHash'] = snapshot_digest(hashes)
        self.assertEqual(reproduced, F)

    def test_every_same_count_id_swap_duplicate_or_missing_member_fails(self):
        QA.validate_projection(F, projection())
        for key in (*QA.PUBLIC_SETS, 'lawClauses'):
            for mode in ('swap', 'duplicate', 'missing'):
                got = projection()
                if mode == 'swap': got[key][-1] += '_UNEXPECTED'
                elif mode == 'duplicate': got[key][-1] = got[key][0]
                else: got[key].pop()
                with self.subTest(key=key, mode=mode), self.assertRaises(AssertionError):
                    QA.validate_projection(F, got)

    def test_changed_cohort_positive_and_every_business_field_negative(self):
        for row in F['records']:
            QA.validate_rendered(row, rendered(row))
            for key in ('id', 'title', 'description', 'conditions', 'measures', 'category', 'places'):
                got = rendered(row); got[key] += '错误'
                with self.subTest(id=row['id'], field=key), self.assertRaises(AssertionError):
                    QA.validate_rendered(row, got)

    def test_every_current_basis_and_hydrated_identity_is_bound(self):
        for field in ('linkId', 'clauseId', 'lawId', 'lawName', 'role', 'applicability', 'article', 'quote', 'sourceUrl', 'jurisdictionCode', 'clauseRegion', 'lawRegion'):
            got = projection(); got['details'][0]['bases'][0][field] = 'WRONG'
            with self.subTest(field=field), self.assertRaises(AssertionError): QA.validate_projection(F, got)
        for mode in ('missing', 'duplicate', 'extra'):
            got = projection()
            if mode == 'missing': got['details'][0]['bases'].pop()
            else: got['details'][0]['bases'].append(copy.deepcopy(got['details'][0]['bases'][0]))
            with self.subTest(mode=mode), self.assertRaises(AssertionError): QA.validate_projection(F, got)
        for row in F['records']:
            for field in ('sourceUrl', 'applicability', 'quote'):
                got = rendered(row); got['bases'][-1][field] += '错误'
                with self.subTest(id=row['id'], field=field), self.assertRaises(AssertionError): QA.validate_rendered(row, got)

    def test_structured_tables_bind_every_cell_span_and_trailing_text(self):
        rows = [r for r in F['records'] if any(b['contentParts'] for b in r['bases'])]
        self.assertTrue(rows)
        for row in rows:
            table = next(i for i, b in enumerate(row['bases']) if b['contentParts'])
            for field in ('text', 'colSpan', 'rowSpan'):
                got = rendered(row)
                cell = got['bases'][table]['tables'][0]['bodyRows'][-1][-1]
                cell[field] = cell[field] + ('错' if field == 'text' else 1)
                with self.subTest(id=row['id'], field=field), self.assertRaises(AssertionError): QA.validate_rendered(row, got)
            got = rendered(row); got['bases'][table]['quote'] = row['bases'][table]['contentParts'][0]['text']
            with self.assertRaises(AssertionError): QA.validate_rendered(row, got)

    def test_snapshot_date_and_release_changes_fail_closed(self):
        release = {'releaseHash': 'a' * 64, 'asOf': F['asOf'], 'knowledge': {'snapshotSha256': F['knowledgeSnapshotHash']}}
        QA.validate_release_source(F, release, 'a' * 64)
        for field in ('releaseHash', 'asOf', 'knowledge'):
            got = copy.deepcopy(release); got[field] = {} if field == 'knowledge' else 'wrong'
            with self.subTest(field=field), self.assertRaises(AssertionError): QA.validate_release_source(F, got, 'a' * 64)
        bad = copy.deepcopy(F); bad['knowledgeSnapshotHash'] = '0' * 64
        with self.assertRaisesRegex(AssertionError, 'source snapshot changed'): QA.validate_source_pins(bad, ROOT)

    def test_full_copy_contains_every_basis_full_quote_scope_and_source_notes(self):
        for row in F['records']:
            plain, full = QA.expected_clipboard(row), QA.expected_full_clipboard(row, 'test.commit')
            self.assertTrue(full.startswith(plain + '\n\n'))
            self.assertTrue(full.endswith('数据库版本：test.commit。'))
            for b in row['bases']:
                self.assertIn(b['quote'], plain); self.assertIn(b['applicability'], plain)
            for note in row['copyNotes']['historicalReferences']:
                self.assertIn(note, full)

    def test_legacy_fixture_counts_stay_default_and_explicit_inventory_is_additive(self):
        from test_repaired_browser_acceptance import projection as old_projection
        old = REPAIR.load_expectations(); got = old_projection()
        current = {'hazards': got['hazards'] + 1, 'links': got['links'] + 1, 'clauses': len(got['lawClauseIds']) + 1}
        got['hazards'] += 1; got['links'] += 1
        for key in ('hazardClauseIds', 'lawClauseIds'): got[key].append('C_CURRENT_ADDITION')
        with self.assertRaises(AssertionError): REPAIR.validate_public_projection(old, got)
        REPAIR.validate_public_projection(old, got, public_inventory=current)
        from test_technical_citation_browser import projection as technical_projection
        tech = TECHNICAL.load_expectations(); got = technical_projection(); got['majorHazardCount'] += 1
        with self.assertRaises(AssertionError): TECHNICAL.validate_projection(tech, got)
        TECHNICAL.validate_projection(tech, got, public_inventory={'majorHazards': got['majorHazardCount'], 'profiles': got['profileCount']})

    def test_electrical_seven_h_ten_k_are_source_pinned_and_in_current_detail_cohort(self):
        electrical = ELECTRICAL.load_expectations()
        self.assertEqual(ELECTRICAL.validate_source_pins(electrical, ROOT)['basisLinks'], 10)
        self.assertTrue(ELECTRICAL.EXPECTED_IDS <= set(F['changedHazardIds']))
        got = {'details': [{'id': r['id'], 'hazard': copy.deepcopy(r['hazard']), 'bases': copy.deepcopy(r['bases'])} for r in electrical['records']]}
        ELECTRICAL.validate_projection(electrical, got)
        got['details'][0]['bases'][0]['clauseId'] += '_WRONG'
        with self.assertRaises(AssertionError): ELECTRICAL.validate_projection(electrical, got)

    def test_ci_runs_both_real_browser_harnesses_before_and_after_deploy(self):
        workflow = (ROOT / '.github/workflows/reviewed-site.yml').read_text()
        self.assertEqual(workflow.count('python tools/browser/audit_ordinary_tables.py'), 2)
        self.assertEqual(workflow.count('python tools/browser/audit_browser.py'), 2)
        self.assertGreaterEqual(workflow.count('--expected-commit "${GITHUB_SHA}"'), 4)
        audit = (ROOT / 'tools/browser/audit_browser.py').read_text()
        for token in ('run_electrical_browser_acceptance(browser,', 'run_recovery_release_acceptance(browser,', 'exact_release_identity_after_all_flows', 'unpublished_H_12158_10_1_2_deep_link'):
            self.assertIn(token, audit)
        self.assertNotIn('unpublished_H052', audit)
        recovery = (ROOT / 'tools/browser/recovery_release_acceptance.py').read_text()
        for token in ('page.go_back()', 'page.go_forward()', 'page.reload(', 'navigator.clipboard.readText()', 'recovery_exact_public_membership_after_flows'):
            self.assertIn(token, recovery)
        self.assertNotIn('.launch(', recovery)


if __name__ == '__main__':
    unittest.main()
