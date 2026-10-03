"""Pure negative tests for source-pinned browser acceptance; no browser launch."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('repair_acceptance', ROOT / 'tools/browser/repair_acceptance.py')
QA = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(QA)
FIXTURE = QA.load_expectations()


def rendered(row):
    value = {key: row['hazard'][key] for key in ('title', 'description', 'conditions', 'measures')}
    value.update(id=row['id'], category=row.get('displayCategory', row['hazard']['category']),
                 places=' · '.join(row['hazard']['places']), bases=[])
    for basis in row['bases']:
        got = {key: basis[key] for key in ('linkId', 'lawId', 'lawName', 'article', 'quote', 'applicability', 'sourceUrl')}
        got['roleLabel'] = QA.ROLE_LABELS[basis['role']]
        value['bases'].append(got)
    return value


def projection():
    clauses = sorted({b['clauseId'] for r in FIXTURE['records'] for b in r['bases']})
    clauses += [f'C_OTHER_PUBLIC_{i:04d}' for i in range(1362 - len(clauses))]
    return {'hazards': 1671, 'links': 1817, 'hazardClauseIds': list(clauses), 'lawClauseIds': list(clauses),
            'repairDetails': [{'id': r['id'], 'hazard': copy.deepcopy(r['hazard']),
                               'bases': copy.deepcopy(r['bases'])} for r in FIXTURE['records']]}


class RepairedBrowserAcceptanceTests(unittest.TestCase):
    def test_exact_37_record_fixture_and_four_cohorts(self):
        self.assertEqual(len(QA.validate_expectations(FIXTURE)), 37)
        self.assertEqual(FIXTURE['cohortCounts'], {'flange': 3, 'training': 5, 'occupational': 3, 'remaining': 26})
        self.assertEqual(len(FIXTURE['excludedClauseIds']), 27)
        self.assertTrue(set(FIXTURE['representativeIds']) <= {r['id'] for r in FIXTURE['records']})

    def test_duplicate_or_missing_hazard_expectation_rejected(self):
        for action in ('duplicate', 'missing'):
            f = copy.deepcopy(FIXTURE)
            if action == 'duplicate':
                f['records'][-1] = copy.deepcopy(f['records'][0])
            else:
                f['records'].pop()
            with self.assertRaises(AssertionError): QA.validate_expectations(f)

    def test_missing_source_pin_or_review_binding_rejected(self):
        f = copy.deepcopy(FIXTURE)
        f['sourceFiles'].pop(f'knowledge/hazards/{f["records"][0]["id"]}.json')
        with self.assertRaises(AssertionError): QA.validate_expectations(f)
        f = copy.deepcopy(FIXTURE); f['sourceFixtureHashes'].pop('remaining')
        with self.assertRaises(AssertionError): QA.validate_expectations(f)

    def test_quarantined_positive_expectation_rejected(self):
        f = copy.deepcopy(FIXTURE)
        f['records'][0]['bases'][0]['clauseId'] = f['excludedClauseIds'][0]
        with self.assertRaises(AssertionError): QA.validate_expectations(f)

    def test_inventory_cohort_and_exclusion_expectations_cannot_drift(self):
        for field, value in [('expectedHazards', 1672), ('expectedPublicLinks', 1818),
                             ('expectedPublicClauses', 1363), ('cohortCounts', {'flange': 37}), ('excludedClauseIds', [])]:
            f = copy.deepcopy(FIXTURE); f[field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError): QA.validate_expectations(f)

    def test_source_pins_bind_actual_bytes_and_reject_absent_or_modified_files(self):
        f = copy.deepcopy(FIXTURE); data = b'{"reviewed":"exact bytes"}'
        digest = hashlib.sha256(data).hexdigest()
        f['sourceFiles'] = {p: digest for p in f['sourceFiles']}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for relative in f['sourceFiles']:
                p = root / relative; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
            for cohort, filename in QA.SOURCE_FIXTURES.items():
                p = root / 'tools/pipeline/tests/fixtures' / filename
                p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
                f['sourceFixtureHashes'][cohort] = digest
            self.assertEqual(QA.validate_source_pins(f, root)['sourceFiles'], len(f['sourceFiles']))
            target = root / next(iter(f['sourceFiles'])); target.write_bytes(data + b' ')
            with self.assertRaises(AssertionError): QA.validate_source_pins(f, root)
            target.unlink()
            with self.assertRaises(AssertionError): QA.validate_source_pins(f, root)

    def test_all_37_exact_dom_snapshots_pass(self):
        for row in FIXTURE['records']:
            with self.subTest(id=row['id']):
                self.assertEqual(QA.validate_rendered_detail(row, rendered(row))['id'], row['id'])

    def test_hazard_identity_and_every_visible_business_field_are_bound(self):
        for row in FIXTURE['records']:
            for key in ('id', 'title', 'description', 'conditions', 'measures', 'category', 'places'):
                changed = rendered(row); changed[key] += '错误'
                with self.subTest(id=row['id'], field=key), self.assertRaises(AssertionError):
                    QA.validate_rendered_detail(row, changed)

    def test_every_repaired_basis_link_clause_text_scope_and_source_are_bound(self):
        for row in FIXTURE['records']:
            for key in ('linkId', 'lawId', 'lawName', 'roleLabel', 'article', 'quote', 'applicability', 'sourceUrl'):
                changed = rendered(row); changed['bases'][0][key] += '错误'
                with self.subTest(id=row['id'], field=key), self.assertRaises(AssertionError):
                    QA.validate_rendered_detail(row, changed)

    def test_missing_extra_or_duplicate_rendered_basis_fails(self):
        row = FIXTURE['records'][0]
        for bases in [[], rendered(row)['bases'] * 2]:
            changed = rendered(row); changed['bases'] = bases
            with self.assertRaises(AssertionError): QA.validate_rendered_detail(row, changed)

    def test_truncated_quote_or_wrong_penalty_body_fails_for_every_hazard(self):
        for row in FIXTURE['records']:
            for value in (row['bases'][0]['quote'][:20], '第七十二条 责令限期改正；处罚。'):
                changed = rendered(row); changed['bases'][0]['quote'] = value
                with self.subTest(id=row['id']), self.assertRaises(AssertionError): QA.validate_rendered_detail(row, changed)

    def test_whitespace_layout_is_ignored_but_words_and_punctuation_are_not(self):
        self.assertEqual(QA.visible_text('a\n\tb\u00a0c'), 'a b c')
        for actual, expected in [('ab', 'a b'), ('甲，乙', '甲；乙'), ('未保证佩戴', '保证佩戴')]:
            with self.assertRaises(AssertionError): QA.require_text(actual, expected, 'semantic character')
        row = FIXTURE['records'][0]; got = rendered(row)
        got['bases'][0]['quote'] = '\n  ' + got['bases'][0]['quote'] + '\t\n'
        QA.validate_rendered_detail(row, got)

    def test_mid_run_release_change_and_missing_identity_fail_closed(self):
        self.assertEqual(QA.validate_release_match('a' * 64, 'a' * 64), 'a' * 64)
        for actual, expected in [('b' * 64, 'a' * 64), (None, 'a' * 64), ('', ''), ('x' * 64, 'x' * 64)]:
            with self.assertRaises(AssertionError): QA.validate_release_match(actual, expected)

    def test_exact_public_projection_passes(self):
        result = QA.validate_public_projection(FIXTURE, projection())
        self.assertEqual(result['repairedHazards'], 37)
        self.assertEqual(result['quarantinedClausesAbsentFromHazardsAndLaws'], 27)

    def test_old_clause_is_rejected_in_either_hazard_or_law_catalogue(self):
        for field in ('hazardClauseIds', 'lawClauseIds'):
            for cid in FIXTURE['excludedClauseIds']:
                got = projection(); got[field][-1] = cid
                with self.subTest(field=field, clause=cid), self.assertRaises(AssertionError):
                    QA.validate_public_projection(FIXTURE, got)

    def test_clause_count_or_catalogue_join_drift_fails(self):
        for field in ('hazardClauseIds', 'lawClauseIds'):
            got = projection(); got[field].pop()
            with self.assertRaises(AssertionError): QA.validate_public_projection(FIXTURE, got)
            got = projection(); got[field][-1] = 'C_OTHER_UNEXPECTED'
            with self.assertRaises(AssertionError): QA.validate_public_projection(FIXTURE, got)

    def test_missing_or_duplicate_hydrated_repair_is_rejected(self):
        for mode in ('missing', 'duplicate'):
            got = projection()
            if mode == 'missing': got['repairDetails'].pop()
            else: got['repairDetails'][-1] = copy.deepcopy(got['repairDetails'][0])
            with self.assertRaises(AssertionError): QA.validate_public_projection(FIXTURE, got)

    def test_canonical_id_swap_fails_even_if_display_text_is_identical(self):
        got = projection(); got['repairDetails'][0]['bases'][0]['clauseId'] = 'C_WRONG_SAME_TEXT'
        with self.assertRaises(AssertionError): QA.validate_public_projection(FIXTURE, got)

    def test_unchanged_counts_do_not_hide_repaired_scope_or_quoted_text_drift(self):
        for group, key in [('hazard', 'conditions'), ('hazard', 'measures'), ('basis', 'applicability'), ('basis', 'quote')]:
            got = projection(); row = got['repairDetails'][0]
            if group == 'hazard': row['hazard'][key] += '扩大范围'
            else: row['bases'][0][key] += '扩大范围'
            with self.assertRaises(AssertionError): QA.validate_public_projection(FIXTURE, got)

    def test_public_inventory_count_change_fails(self):
        for key in ('hazards', 'links'):
            got = projection(); got[key] += 1
            with self.assertRaises(AssertionError): QA.validate_public_projection(FIXTURE, got)

    def test_browser_audit_keeps_existing_acceptance_and_invokes_repaired_layer(self):
        text = (ROOT / 'tools/browser/audit_browser.py').read_text()
        for name in ('six_common_hazards_exact_search_links_and_reload', 'sticky_header_485px_reduced_motion',
                     'exact_release_identity', 'all_published_hazards_laws_quotes_and_counts',
                     'run_repair_browser_acceptance(browser, base, run, page_errors, expect, repair_fixture,'):
            self.assertIn(name, text)
        self.assertLess(text.index('run_repair_browser_acceptance(browser,'), text.index("run('no_unhandled_javascript_errors'"))

    def test_extraction_reads_dom_fields_not_store_projection(self):
        self.assertIn('innerText', QA.DOM_SNAPSHOT)
        self.assertNotIn('DataStore', QA.DOM_SNAPSHOT)
        self.assertNotIn('fetch(', QA.DOM_SNAPSHOT)
        self.assertIn('basis-applicability', QA.DOM_SNAPSHOT)
        self.assertIn('getLawDetail', QA.HYDRATE_PROJECTION)


if __name__ == '__main__':
    unittest.main()
