"""Rich-body format and publication-gate QA; synthetic reviews are not legal approval."""
import copy
from datetime import date
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/v4'))
from canonical import content_hash
import check_major_criteria
import major_criteria as major
from normative_content import content_text, validate_clause_content
import test_field_profiles as fixtures
from test_major_criteria import synthetic_config

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError:  # Optional schema tooling is not a pipeline runtime dependency.
    Draft202012Validator = None


def cell(text, col=1, row=1):
    return {'text': text, 'colSpan': col, 'rowSpan': row}


def parts():
    return [{'type': 'text', 'text': '1 Synthetic opening.'}, {
        'type': 'table', 'id': 'T_SYNTHETIC', 'caption': 'Synthetic table',
        'columnCount': 3, 'sourcePages': [4, 5],
        'headerRows': [[cell('Sample', row=2), cell('S', col=2)],
                       [cell('kg/m'), cell('L/m')]],
        'bodyRows': [[cell('Dry'), cell('6'), cell('5.4')],
                     [cell('Other', col=2), cell('K₁[mL/(g·min^(1/2))]')]]},
        {'type': 'text', 'text': 'Synthetic closing.'}]


def coal_clauses():
    return [json.loads((ROOT / f'knowledge/clauses/C_MEM_COAL_2026_{n}.json').read_text())
            for n in (5, 6)]


class NormativeContentTests(unittest.TestCase):
    def test_deterministic_grid_retains_order_spans_and_complete_fallback(self):
        body = parts()
        before = copy.deepcopy(body)
        self.assertEqual(content_text(body), '1 Synthetic opening.\nSynthetic table\n'
            'Sample\tS\t\n\tkg/m\tL/m\nDry\t6\t5.4\n'
            'Other\t\tK₁[mL/(g·min^(1/2))]\nSynthetic closing.')
        self.assertEqual(body, before)
        self.assertEqual(validate_clause_content({'contentParts': body, 'quote': content_text(body)},
                                                ['T_SYNTHETIC']), ['T_SYNTHETIC'])

    def test_coal_seven_source_tables_have_expected_shape_and_page_mapping(self):
        tables = []
        for clause, ids in zip(coal_clauses(), [range(1, 4), range(4, 8)]):
            expected = [f'T_COAL_2026_{i}' for i in ids]
            self.assertEqual(validate_clause_content(clause, expected), expected)
            tables.extend(p for p in clause['contentParts'] if p['type'] == 'table')
        self.assertEqual([(t['columnCount'], len(t['headerRows']), len(t['bodyRows'])) for t in tables],
                         [(2, 1, 7), (2, 1, 6), (2, 1, 7), (3, 1, 2), (3, 1, 2), (4, 2, 1), (3, 2, 1)])
        self.assertEqual([t['sourcePages'] for t in tables], [[4], [4, 5], [5], [9], [9], [9], [9]])
        self.assertEqual(tables[1]['bodyRows'][0][0]['text'], '5≤Q<10')
        self.assertEqual(tables[1]['bodyRows'][-1][0]['text'], 'Q≥100')
        self.assertEqual(tables[3]['bodyRows'][1][0]['colSpan'], 2)
        self.assertEqual([c['rowSpan'] for c in tables[5]['headerRows'][0]], [2, 2, 1])
        self.assertEqual([c['colSpan'] for c in tables[5]['headerRows'][0]], [1, 1, 2])
        self.assertIn('min^(1/2)', tables[4]['headerRows'][0][2]['text'])
        self.assertEqual([c['text'] for c in tables[6]['bodyRows'][0]], ['5', '6', '5.4'])

    def test_bad_grid_layout_and_span_types_fail_closed(self):
        cases = [
            ('zero', lambda t: t['bodyRows'][0][0].update(colSpan=0), 'SPAN'),
            ('negative', lambda t: t['bodyRows'][0][0].update(rowSpan=-1), 'SPAN'),
            ('boolean', lambda t: t['bodyRows'][0][0].update(colSpan=True), 'SPAN'),
            ('float', lambda t: t['bodyRows'][0][0].update(rowSpan=1.5), 'SPAN'),
            ('outside columns', lambda t: t['bodyRows'][0][0].update(colSpan=4), 'SPAN_BOUNDS'),
            ('outside rows', lambda t: t['bodyRows'][1][0].update(rowSpan=2), 'SPAN_BOUNDS'),
            ('hole', lambda t: t['bodyRows'][0].pop(), 'GRID_HOLE'),
            ('overlap', lambda t: t.update(bodyRows=[[cell('a'), cell('b', row=2), cell('c')],
                                                     [cell('overlap', col=2), cell('d')]]), 'SPAN_OVERLAP'),
            ('empty row', lambda t: t['bodyRows'].__setitem__(0, []), 'ROW_CELLS'),
        ]
        for name, mutate, error in cases:
            with self.subTest(name=name):
                body = parts(); mutate(body[1])
                with self.assertRaisesRegex(ValueError, error): content_text(body)

    def test_unknown_fields_control_chars_duplicate_ids_and_pages_are_rejected(self):
        for mutate, error in [
            (lambda p: p[0].update(html='<b>hidden</b>'), 'TEXT'),
            (lambda p: p[1].update(privatePath='/workspace/private'), 'TABLE_FIELDS'),
            (lambda p: p[1]['bodyRows'][0][0].update(rawHtml='<script>bad</script>'), 'CELL'),
            (lambda p: p[1]['bodyRows'][0][0].update(text='a\tb'), 'CELL'),
            (lambda p: p[0].update(text='a\r\nb'), 'TEXT'),
            (lambda p: p[1].update(columnCount=True), 'COLUMNS'),
            (lambda p: p.append(copy.deepcopy(p[1])), 'TABLE_ID'),
            (lambda p: p[1].update(sourcePages=[5, 4]), 'PAGES'),
            (lambda p: p[1].update(sourcePages=[4, 4]), 'PAGES'),
            (lambda p: p[1].update(sourcePages=[True]), 'PAGES'),
            (lambda p: p[1].update(sourcePages=[1001]), 'PAGES'),
            (lambda p: p.pop(0), 'FIRST_TEXT'),
        ]:
            with self.subTest(error=error):
                body = parts(); mutate(body)
                with self.assertRaisesRegex(ValueError, error): content_text(body)

    def test_missing_extra_reordered_tables_and_different_fallback_are_rejected(self):
        clause = {'contentParts': parts(), 'quote': content_text(parts())}
        for expected in ([], ['T_OTHER'], ['T_SYNTHETIC', 'T_MISSING']):
            with self.subTest(expected=expected), self.assertRaisesRegex(ValueError, 'TABLE_MEMBERSHIP'):
                validate_clause_content(clause, expected)
        with self.assertRaisesRegex(ValueError, 'REQUIRED_TABLE_MISSING'):
            validate_clause_content({'quote': 'Synthetic plain text'}, ['T_SYNTHETIC'])
        for quote in (clause['quote'] + '\n', clause['quote'].replace('\t', ' '), 'Only a summary'):
            with self.subTest(quote=quote), self.assertRaisesRegex(ValueError, 'QUOTE_FALLBACK_MISMATCH'):
                validate_clause_content({**clause, 'quote': quote}, ['T_SYNTHETIC'])
        other = copy.deepcopy(clause['contentParts'][1]); other['id'] = 'T_SECOND'
        body = clause['contentParts'] + [other]
        with self.assertRaisesRegex(ValueError, 'TABLE_MEMBERSHIP'):
            validate_clause_content({'contentParts': body, 'quote': content_text(body)},
                                    ['T_SECOND', 'T_SYNTHETIC'])
        self.assertEqual(validate_clause_content({'quote': 'Legacy plain text'}, []), [])

    def test_explicit_null_parts_cannot_be_treated_as_absent_legacy_content(self):
        with self.assertRaisesRegex(ValueError, 'PARTS'):
            validate_clause_content({'quote': 'Legacy plain text', 'contentParts': None}, [])


class RichPublicationTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.FieldProfileTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.config = synthetic_config(self.f); self.s = self.config['standards'][0]
        self.s['topicLinks'] = []
        self.s['officialScope']['wholeStandardComplete'] = True
        self.s['publication'] = {'basis': major.PUBLICATION_BASIS,
            'legalSourceUrl': 'https://example.gov.cn/copyright', 'evidenceIds': ['E_RIGHTS']}
        self.s['applicationNotes'] = [{'clauseId': 'C_TEST', 'summary': 'Synthetic scope clarification.',
            'sourceUrl': 'https://example.gov.cn/clarification', 'sourceDate': '2026-09-29', 'evidenceId': 'E_NOTE'}]
        for eid, url in [('E_RIGHTS', self.s['publication']['legalSourceUrl']),
                         ('E_NOTE', self.s['applicationNotes'][0]['sourceUrl'])]:
            self.f.put(f'evidence/{eid}.json', {'id': eid, 'url': url, 'tier': 'authoritative-public',
                'snapshotSha256': 'a' * 64, 'locator': 'Synthetic source only'})
        self.f.clause.update(contentParts=parts(), quote=content_text(parts()))
        self.s['clauses'][0]['tableIds'] = ['T_SYNTHETIC']
        self.save_clause(); self.save()

    def save(self): self.f.put(major.CONFIG_PATH, self.config)
    def save_clause(self):
        self.f.entity('clauses', self.f.clause)
        self.s['clauses'][0]['contentHash'] = content_hash(self.f.clause)
    def project(self): return major.public_projection(self.f.root, as_of=date(2026, 9, 30))
    def approve_synthetic(self, scope=None, checked='2026-09-30T08:00:00+00:00'):
        binding, _ = major.scope_review_bindings(self.s, self.f.root)
        self.f.put('major-criteria/v1/reviews/LV_TEST.json', {'schemaVersion': 1,
            'lawVersionId': 'LV_TEST', 'decision': 'verified', **binding, 'checkedAt': checked,
            'reviewScope': scope or major.RICH_SCOPE_REVIEW, 'fullQuotePublicationReady': True,
            'reviewer': 'Synthetic test only', 'reason': 'Synthetic test only; no production approval'})

    def test_rich_scope_requires_a_separate_exact_review(self):
        self.assertEqual(self.project()['catalog']['standards'], [])
        self.approve_synthetic(major.SCOPE_REVIEW)
        self.assertEqual(self.project()['catalog']['standards'], [])
        self.approve_synthetic()
        row = self.project()['catalog']['standards'][0]
        self.assertEqual((row['coverage']['expectedTableCount'], row['coverage']['reviewedTableCount']), (1, 1))
        self.assertEqual(row['clauses'][0]['contentParts'], parts())
        note = row['clauses'][0]['applicationNotes'][0]
        self.assertEqual(note['kind'], 'official_application_clarification')
        self.assertIs(note['isOfficialNormText'], False)
        self.assertNotIn(note['summary'], row['clauses'][0]['quote'])
        self.assertNotIn('evidenceId', note)
        self.assertEqual(row['directHazardIds'], [])
        self.assertEqual(self.project()['topic']['hazardIds'], [])
        self.assertNotIn('reviewer', json.dumps(row))
        self.assertEqual(check_major_criteria.validate_namespace(self.f.root)['errors'], [])

    def test_note_and_note_evidence_changes_invalidate_exact_scope_binding(self):
        self.approve_synthetic()
        before, deps = major.scope_review_bindings(self.s, self.f.root)
        self.assertIn('evidence/E_NOTE', deps)
        self.s['applicationNotes'][0]['summary'] = 'Changed clarification.'; self.save()
        self.assertEqual(self.project()['catalog']['standards'], [])
        self.approve_synthetic()
        note = copy.deepcopy(deps['evidence/E_NOTE']); note['locator'] = 'Changed source section'
        self.f.put('evidence/E_NOTE.json', note)
        self.assertEqual(self.project()['catalog']['standards'], [])
        after, _ = major.scope_review_bindings(self.s, self.f.root)
        self.assertNotEqual(before['dependencyFingerprint'], after['dependencyFingerprint'])

    def test_note_evidence_and_dates_still_fail_after_synthetic_rebinding(self):
        original = json.loads((self.f.root / 'evidence/E_NOTE.json').read_text())
        for change in ({'url': 'https://example.gov.cn/other'}, {'tier': 'third-party'},
                       {'snapshotSha256': ''}, {'locator': ''}):
            with self.subTest(change=change):
                self.f.put('evidence/E_NOTE.json', {**original, **change}); self.approve_synthetic()
                self.assertEqual(self.project()['catalog']['standards'], [])
        self.f.put('evidence/E_NOTE.json', original)
        for source_date, checked in [('2026-10-01', '2026-09-30'), ('2026-09-30', '2026-09-29')]:
            self.s['applicationNotes'][0]['sourceDate'] = source_date; self.save()
            self.approve_synthetic(checked=checked)
            self.assertEqual(self.project()['catalog']['standards'], [])
        (self.f.root / 'evidence/E_NOTE.json').unlink(); self.approve_synthetic()
        self.assertEqual(self.project()['catalog']['standards'], [])

    def test_invalid_note_fields_membership_and_duplicate_sources_are_rejected(self):
        original = copy.deepcopy(self.s['applicationNotes'])
        for change in ({'clauseId': 'C_OTHER'}, {'isOfficialNormText': True}, {'summary': ''},
                       {'sourceUrl': 'https://example.com/note'}, {'sourceDate': '2026-02-30'},
                       {'evidenceId': '../private'}, {'summary': '/workspace/private/note'}):
            with self.subTest(change=change):
                self.s['applicationNotes'] = [{**original[0], **change}]; self.save()
                with self.assertRaisesRegex(ValueError, 'APPLICATION_NOTE'): major.load_config(self.f.root)
        self.s['applicationNotes'] = original * 2; self.save()
        with self.assertRaisesRegex(ValueError, 'APPLICATION_NOTE_DUPLICATE'): major.load_config(self.f.root)

    def test_missing_table_wrong_fallback_and_hidden_cell_cannot_publish_complete_body(self):
        original = copy.deepcopy(self.f.clause)
        for mutate in (lambda c: c.pop('contentParts'), lambda c: c.update(quote='Truncated fallback'),
                       lambda c: c['contentParts'][1]['bodyRows'][0][0].update(hidden='private')):
            self.f.clause = copy.deepcopy(original); mutate(self.f.clause)
            self.save_clause(); self.save(); self.approve_synthetic()
            self.assertEqual(self.project()['catalog']['standards'], [])
            self.assertTrue(check_major_criteria.validate_namespace(self.f.root)['errors'])

    def test_namespace_gate_rejects_explicit_null_even_without_selected_table_ids(self):
        self.f.clause['contentParts'] = None
        self.f.clause['quote'] = '1 Synthetic plain body'
        del self.s['clauses'][0]['tableIds']
        self.save_clause(); self.save(); self.approve_synthetic()
        errors = check_major_criteria.validate_namespace(self.f.root)['errors']
        self.assertIn('NORMATIVE_CONTENT_PARTS:C_TEST', errors)
        self.assertEqual(self.project()['catalog']['standards'], [])

    def test_notes_without_tables_still_require_rich_review_and_preserve_plain_body(self):
        del self.f.clause['contentParts']; self.f.clause['quote'] = '1 Synthetic plain body'
        del self.s['clauses'][0]['tableIds']; self.save_clause(); self.save()
        self.approve_synthetic(major.SCOPE_REVIEW)
        self.assertEqual(self.project()['catalog']['standards'], [])
        self.approve_synthetic(); row = self.project()['catalog']['standards'][0]
        self.assertNotIn('contentParts', row['clauses'][0])
        self.assertNotIn('expectedTableCount', row['coverage'])
        self.assertEqual(row['clauses'][0]['quote'], '1 Synthetic plain body')
        self.assertEqual(len(row['clauses'][0]['applicationNotes']), 1)

    @unittest.skipUnless(Draft202012Validator is not None, 'Optional jsonschema package is unavailable')
    def test_catalog_schema_accepts_rich_projection_and_rejects_extra_or_malformed_fields(self):
        schema = json.loads((ROOT / 'tools/v4/schemas/major-criteria-catalog.schema.json').read_text())
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        self.approve_synthetic(); catalog = self.project()['catalog']; validator.validate(catalog)
        mutations = [
            lambda s: s['clauses'][0].update(hidden='private'),
            lambda s: s['clauses'][0]['contentParts'][1].update(rawHtml='<table>'),
            lambda s: s['clauses'][0]['contentParts'][1]['bodyRows'][0][0].update(colSpan=0),
            lambda s: s['clauses'][0]['contentParts'][1]['bodyRows'][0][0].update(text='hidden\ttext'),
            lambda s: s['clauses'][0]['applicationNotes'][0].update(isOfficialNormText=True),
            lambda s: s['clauses'][0]['applicationNotes'][0].update(evidenceId='E_PRIVATE'),
            lambda s: s['clauses'][0]['applicationNotes'][0].update(sourceDate='2026-02-30'),
            lambda s: s['coverage'].pop('expectedTableCount'),
            lambda s: s['coverage'].pop('reviewedTableCount'),
            lambda s: s['coverage'].update(expectedTableCount=0),
            lambda s: s.pop('publicationBasis'),
            lambda s: s['standardVersion'].pop('lawId'),
            lambda s: s['clauses'][0].pop('quote'),
        ]
        for i, mutate in enumerate(mutations):
            with self.subTest(mutation=i):
                bad = copy.deepcopy(catalog); mutate(bad['standards'][0])
                self.assertTrue(list(validator.iter_errors(bad)))
        legacy = copy.deepcopy(catalog); s = legacy['standards'][0]
        s['clauses'][0].pop('contentParts'); s['clauses'][0].pop('applicationNotes')
        s['coverage'].pop('expectedTableCount'); s['coverage'].pop('reviewedTableCount')
        validator.validate(legacy)


if __name__ == '__main__': unittest.main()
