import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {normativeContentText, validateNormativeClause, renderNormativeContent} from '../web/js/normative-content.js';
import {validateMajorData, selectMajorResults} from '../web/js/major-criteria-model.js';

// Layout fixtures are synthetic. Source shape checks do not certify legal text.
const cell = (text, colSpan = 1, rowSpan = 1) => ({text, colSpan, rowSpan});
function parts() {
  return [{type: 'text', text: 'Synthetic opening.'}, {type: 'table', id: 'T_SYNTHETIC',
    caption: 'Synthetic table', columnCount: 3, sourcePages: [4, 5],
    headerRows: [[cell('Sample', 1, 2), cell('S', 2)], [cell('kg/m'), cell('L/m')]],
    bodyRows: [[cell('Dry'), cell('6'), cell('5.4')],
      [cell('Other', 2), cell('K₁[mL/(g·min^(1/2))]')]]},
    {type: 'text', text: 'Synthetic closing.'}];
}
const clause = contentParts => ({clauseId: 'C_TEST', article: '1', lawVersionId: 'LV_TEST',
  sourceUrl: 'https://example.gov.cn/standard', status: '现行有效', checked: '2026-09-30',
  granularity: 'whole_clause', directHazardIds: [], quote: normativeContentText(contentParts), contentParts});
function fixture() {
  const sourceUrl = 'https://example.gov.cn/standard', asOf = '2026-09-30';
  const standard = {id: 'LV_TEST', lawVersionId: 'LV_TEST',
    standardVersion: {lawId: 'LF_TEST', name: 'Synthetic standard', documentNumber: 'Synthetic 1',
      versionKey: 'synthetic', officialSourceUrl: sourceUrl, effectiveDate: '2020-01-01', endDate: '', validityStatus: 'active'},
    officialScope: {label: 'Synthetic complete body', sourceUrls: [sourceUrl], wholeStandardComplete: true},
    publicationBasis: {basis: 'copyright_law_article_5_official_administrative_document',
      legalSourceUrl: 'https://example.gov.cn/copyright', checked: '2026-09-30T08:00:00+00:00', fullTextPublicationApproved: true},
    coverage: {status: 'reviewed_scope_complete', reviewedClauseCount: 1, reviewedWholeClauseCount: 1,
      reviewedSubitemClauseCount: 0, expectedWholeClauseCount: 1, expectedJudgmentItemCount: 1,
      reviewedJudgmentItemCount: 1, wholeStandardComplete: true, expectedTableCount: 1, reviewedTableCount: 1},
    clauses: [clause(parts())], directHazardIds: [], directHazardCount: 0};
  standard.clauses[0].applicationNotes = [{kind: 'official_application_clarification', isOfficialNormText: false,
    summary: 'Synthetic applicability clarification.', sourceUrl: 'https://example.gov.cn/clarification',
    sourceDate: '2026-09-29', checked: standard.publicationBasis.checked}];
  return {catalog: {schemaVersion: 1, asOf, wholeNormNotFieldFinding: true,
    catalogScope: 'controlled_reviewed_standards_only', allIndustryCoverage: false, standards: [standard]},
  topic: {schemaVersion: 1, asOf, wholeNormNotFieldFinding: true, associations: [], hazardIds: [],
    coverage: {excludedAssociationCount: 0, excludedHazardCount: 0, exclusionReason: '关联待复核'}}};
}
const validate = data => validateMajorData(data.catalog, data.topic, [], data.catalog.asOf);
const coalClauses = () => [5, 6].map(n => JSON.parse(readFileSync(
  new URL(`../knowledge/clauses/C_MEM_COAL_2026_${n}.json`, import.meta.url), 'utf8')));

test('ordered text and table fallback preserves empty span coordinates without modifying inputs', () => {
  const body = parts(), before = structuredClone(body);
  assert.equal(normativeContentText(body), 'Synthetic opening.\nSynthetic table\nSample\tS\t\n\tkg/m\tL/m\n'
    + 'Dry\t6\t5.4\nOther\t\tK₁[mL/(g·min^(1/2))]\nSynthetic closing.');
  assert.deepEqual(body, before);
  assert.deepEqual(validateNormativeClause(clause(body)), ['T_SYNTHETIC']);
});

test('seven coal source tables retain shape, continuation pages, merged headers and fallback', () => {
  const source = coalClauses(), tables = source.flatMap(c => c.contentParts.filter(p => p.type === 'table'));
  assert.deepEqual(source.map(c => validateNormativeClause(c)), [
    ['T_COAL_2026_1', 'T_COAL_2026_2', 'T_COAL_2026_3'],
    ['T_COAL_2026_4', 'T_COAL_2026_5', 'T_COAL_2026_6', 'T_COAL_2026_7']]);
  assert.deepEqual(tables.map(t => [t.columnCount, t.headerRows.length, t.bodyRows.length]),
    [[2, 1, 7], [2, 1, 6], [2, 1, 7], [3, 1, 2], [3, 1, 2], [4, 2, 1], [3, 2, 1]]);
  assert.deepEqual(tables.map(t => t.sourcePages), [[4], [4, 5], [5], [9], [9], [9], [9]]);
  assert.equal(tables[3].bodyRows[1][0].colSpan, 2);
  assert.deepEqual(tables[5].headerRows[0].map(c => c.rowSpan), [2, 2, 1]);
  assert.deepEqual(tables[5].headerRows[0].map(c => c.colSpan), [1, 1, 2]);
  const html = source.map(renderNormativeContent).join('');
  assert.equal((html.match(/<table /gu) || []).length, 7);
  assert.equal((html.match(/<caption>/gu) || []).length, 7);
  assert.match(html, /原PDF第 4、5 页/);
  assert.match(html, /min<sup>1\/2<\/sup>/);
  assert.doesNotMatch(html, /min\^\(1\/2\)/);
});

const malformedParts = [
  ['zero span', p => { p[1].bodyRows[0][0].colSpan = 0; }, 'SPAN'],
  ['negative span', p => { p[1].bodyRows[0][0].rowSpan = -1; }, 'SPAN'],
  ['boolean span', p => { p[1].bodyRows[0][0].colSpan = true; }, 'SPAN'],
  ['fractional span', p => { p[1].bodyRows[0][0].rowSpan = 1.5; }, 'SPAN'],
  ['span outside row', p => { p[1].bodyRows[1][0].rowSpan = 2; }, 'SPAN_BOUNDS'],
  ['grid hole', p => { p[1].bodyRows[0].pop(); }, 'GRID_HOLE'],
  ['grid overlap', p => { p[1].bodyRows = [[cell('a'), cell('b', 1, 2), cell('c')],
    [cell('overlap', 2), cell('d')]]; }, 'SPAN_OVERLAP'],
  ['empty grid row', p => { p[1].bodyRows[0] = []; }, 'ROW_CELLS'],
  ['hidden table field', p => { p[1].privatePath = '/workspace/private'; }, 'TABLE_FIELDS'],
  ['hidden cell field', p => { p[1].bodyRows[0][0].html = '<script>hidden</script>'; }, 'CELL'],
  ['hidden prose field', p => { p[0].html = '<script>hidden</script>'; }, 'TEXT'],
  ['control character', p => { p[1].bodyRows[0][0].text = 'a\tb'; }, 'CELL'],
  ['carriage return', p => { p[0].text = 'a\r\nb'; }, 'TEXT'],
  ['duplicate table', p => { p.push(structuredClone(p[1])); }, 'TABLE_ID'],
  ['table starts body', p => { p.shift(); }, 'FIRST_TEXT'],
  ['out-of-order pages', p => { p[1].sourcePages = [5, 4]; }, 'PAGES'],
  ['duplicate pages', p => { p[1].sourcePages = [4, 4]; }, 'PAGES'],
  ['boolean page', p => { p[1].sourcePages = [true]; }, 'PAGES'],
  ['out-of-bound page', p => { p[1].sourcePages = [1001]; }, 'PAGES'],
];
for (const [name, mutate, code] of malformedParts) {
  test(`fails closed for ${name}`, () => {
    const body = parts(); mutate(body);
    assert.throws(() => normativeContentText(body), new RegExp(code));
  });
}

test('different fallback and text-only rich body cannot replace reviewed table content', () => {
  for (const alter of [q => q + '\n', q => q.replaceAll('\t', ' '), () => 'Only a summary']) {
    const c = clause(parts()); c.quote = alter(c.quote);
    assert.throws(() => validateNormativeClause(c), /QUOTE_FALLBACK_MISMATCH/);
    assert.throws(() => renderNormativeContent(c), /QUOTE_FALLBACK_MISMATCH/);
  }
  assert.throws(() => validateNormativeClause(clause([{type: 'text', text: 'No table'}])), /TABLE_REQUIRED/);
  assert.throws(() => validateNormativeClause({quote: 'Legacy plain text', contentParts: null}), /PARTS/);
});

test('renderer escapes all prose, cells and caption attributes before rendering only the unit superscript', () => {
  const body = parts(), attack = '<img src=x onerror="alert(1)"> & \'quote\'';
  body[0].text = attack + ' prose ^(1/2)'; body[1].caption = attack;
  body[1].headerRows[0][0].text = attack;
  body[1].bodyRows[0][0].text = attack + ' min^(1/2)';
  const html = renderNormativeContent(clause(body));
  assert.doesNotMatch(html, /<img|<script|<iframe/iu);
  assert.match(html, /&lt;img src=x onerror=&quot;alert\(1\)&quot;&gt; &amp; &#39;quote&#39;/);
  assert.match(html, /aria-label="&lt;img src=x onerror=&quot;/);
  assert.match(html, /min<sup>1\/2<\/sup>/);
  assert.match(html, /prose \^\(1\/2\)/);
  assert.match(html, /<th colspan="1" rowspan="2">/);
  assert.match(html, /<td colspan="2" rowspan="1">Other<\/td>/);
  assert.match(html, /role="region" tabindex="0"/);
  assert.equal(renderNormativeContent({quote: attack}), `<blockquote>&lt;img src=x onerror=&quot;alert(1)&quot;&gt; &amp; &#39;quote&#39;</blockquote>`);
});

test('notes remain separate from original text and searchable without creating hazard membership', () => {
  const data = fixture(), before = structuredClone(data), model = validate(data);
  assert.deepEqual(data, before);
  assert.equal(model.standards[0].coverage.reviewedTableCount, 1);
  const c = model.standards[0].clauses[0];
  assert.equal(c.applicationNotes[0].isOfficialNormText, false);
  assert.ok(!c.quote.includes(c.applicationNotes[0].summary));
  assert.ok(!renderNormativeContent(c).includes(c.applicationNotes[0].summary));
  const found = selectMajorResults(model, {query: 'applicability clarification'});
  assert.equal(found.standards[0].clauses.length, 1);
  assert.deepEqual(found.hazards, []);
});

const invalidCatalogs = [
  ['missing table with retained coverage', s => { delete s.clauses[0].contentParts; }, 'TABLE_COVERAGE'],
  ['missing expected table count', s => { delete s.coverage.expectedTableCount; }, 'TABLE_COVERAGE'],
  ['missing reviewed table count', s => { delete s.coverage.reviewedTableCount; }, 'TABLE_COVERAGE'],
  ['inflated reviewed table count', s => { s.coverage.reviewedTableCount = 2; }, 'TABLE_COVERAGE'],
  ['omitted required table', s => { s.coverage.expectedTableCount = 2; }, 'TABLE_COVERAGE'],
  ['boolean count', s => { s.coverage.expectedTableCount = true; }, 'TABLE_COVERAGE'],
  ['negative count', s => { s.coverage.reviewedTableCount = -1; }, 'TABLE_COVERAGE'],
  ['note posing as original text', s => { s.clauses[0].applicationNotes[0].isOfficialNormText = true; }, 'APPLICATION_NOTE_CONTENT'],
  ['unknown note kind', s => { s.clauses[0].applicationNotes[0].kind = 'normative_text'; }, 'APPLICATION_NOTE_CONTENT'],
  ['hidden note field', s => { s.clauses[0].applicationNotes[0].evidenceId = 'E_PRIVATE'; }, 'APPLICATION_NOTE_CONTENT'],
  ['empty note list', s => { s.clauses[0].applicationNotes = []; }, 'APPLICATION_NOTES'],
  ['invalid note date', s => { s.clauses[0].applicationNotes[0].sourceDate = '2026-02-30'; }, 'APPLICATION_NOTE_CONTENT'],
  ['future note date', s => { s.clauses[0].applicationNotes[0].sourceDate = '2026-10-01'; }, 'APPLICATION_NOTE_CONTENT'],
  ['note after review', s => { s.publicationBasis.checked = '2026-09-28'; s.clauses[0].applicationNotes[0].checked = '2026-09-28'; }, 'APPLICATION_NOTE_CONTENT'],
  ['mismatched note review', s => { s.clauses[0].applicationNotes[0].checked = '2026-09-29'; }, 'APPLICATION_NOTE_CONTENT'],
  ['duplicate note source', s => { s.clauses[0].applicationNotes.push(structuredClone(s.clauses[0].applicationNotes[0])); }, 'APPLICATION_NOTE_CONTENT'],
  ['unofficial note source', s => { s.clauses[0].applicationNotes[0].sourceUrl = 'https://example.com/note'; }, 'APPLICATION_NOTE_CONTENT'],
  ['credential-bearing source', s => { s.clauses[0].applicationNotes[0].sourceUrl = 'https://user:secret@example.gov.cn/note'; }, 'APPLICATION_NOTE_CONTENT'],
  ['whitespace-bearing source', s => { s.clauses[0].applicationNotes[0].sourceUrl = 'https://example.gov.cn/\nnote'; }, 'APPLICATION_NOTE_CONTENT'],
];
for (const [name, mutate, code] of invalidCatalogs) {
  test(`catalog fails closed for ${name}`, () => {
    const data = fixture(); mutate(data.catalog.standards[0]);
    assert.throws(() => validate(data), new RegExp(code));
  });
}

test('table identity must be unique across clauses and standards', () => {
  const data = fixture(), s = data.catalog.standards[0];
  s.clauses.push({...structuredClone(s.clauses[0]), clauseId: 'C_OTHER'});
  assert.throws(() => validate(data), /TABLE_ID_DUPLICATE/);
});

test('tables and application notes require publication approval even for a partial body', () => {
  for (const notesOnly of [false, true]) {
    const data = fixture(), s = data.catalog.standards[0];
    s.officialScope.wholeStandardComplete = false; s.coverage.wholeStandardComplete = false;
    if (notesOnly) {
      delete s.clauses[0].contentParts;
      delete s.coverage.expectedTableCount; delete s.coverage.reviewedTableCount;
    } else delete s.clauses[0].applicationNotes;
    delete s.publicationBasis;
    assert.throws(() => validate(data), notesOnly ? /APPLICATION_NOTES/ : /TABLE_COVERAGE/);
  }
});

test('legacy plain body retains optional table counts and no fabricated notes', () => {
  const data = fixture(), s = data.catalog.standards[0];
  delete s.clauses[0].contentParts; delete s.clauses[0].applicationNotes;
  delete s.coverage.expectedTableCount; delete s.coverage.reviewedTableCount;
  s.clauses[0].quote = 'Synthetic plain text';
  const c = validate(data).standards[0].clauses[0];
  assert.equal(renderNormativeContent(c), '<blockquote>Synthetic plain text</blockquote>');
  assert.ok(!Object.hasOwn(c, 'applicationNotes'));
});
