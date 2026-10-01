import test from 'node:test';
import assert from 'node:assert/strict';
import {validateMajorReferences, selectMajorReferences} from '../web/js/major-criteria-reference-model.js';

const asOf = '2026-10-01';
const topic = (article, searchTopic) => ({article, searchTopic, contentKind: 'search_topic_only',
  isOfficialQuote: false, standaloneDeterminationAllowed: false});
const entry = (over = {}) => ({
  id: 'REF_AQ3067_2026', lawId: 'LF_AQ3067', lawVersionId: 'LV_AQ3067_2026',
  title: '化工和危险化学品生产经营企业重大生产安全事故隐患判定准则 AQ 3067-2026',
  standardNumber: 'AQ 3067-2026', versionKey: '2026', issuer: '应急管理部',
  effectiveDate: '2026-09-30', validityStatus: 'active', checked: '2026-10-01',
  officialLink: 'https://www.mem.gov.cn/reference.shtml',
  officialTextLink: 'https://www.mem.gov.cn/reference.pdf',
  contentKind: 'reference_only', textMode: 'link_only', publicationPermission: 'metadata_only',
  fullTextReviewed: false, fullQuotePublicationReady: false,
  publicationReady: {metadata: true, searchTopics: true, fullText: false},
  reviewedClauseCount: 0, directHazardCount: 0, standaloneDeterminationAllowed: false,
  wholeStandardComplete: false, searchTopicCount: 3,
  searchTopics: [topic('5.1.1', '负责人考核'), topic('5.1.10', '安全仪表配置'), topic('5.2.1', '装置设计与变更')],
  ...over,
});
function fixture() {
  return {schemaVersion: 'safety-major-criteria-references-v1', asOf,
    catalogScope: 'official_reference_entries_only', allIndustryCoverage: false,
    wholeNormNotFieldFinding: true,
    notice: '这些短主题仅帮助定位条款，不是法条原文，也不能独立用于重大事故隐患判定；请查官方原件。',
    referenceEntries: [entry(), entry({id: 'REF_GB9999_2025', lawId: 'LF_GB9999',
      lawVersionId: 'LV_GB9999_2025', title: '第二份官方题录 GB 9999-2025',
      standardNumber: 'GB 9999-2025', versionKey: '2025', effectiveDate: '2025-01-01',
      checked: '2026-09-20', searchTopicCount: 2,
      searchTopics: [topic('5.1.1', '负责人考核'), topic('6.1', 'SIS配置')],
    })]};
}
const validate = data => validateMajorReferences(data, asOf);
const select = query => selectMajorReferences(validate(fixture()), {query});
const ids = result => result.referenceEntries.map(row => row.id);
const first = data => data.referenceEntries[0];

test('pure module imports without DOM, network, or application boot', () => {
  assert.equal(typeof globalThis.document, 'undefined');
  assert.equal(typeof validateMajorReferences, 'function');
  assert.equal(typeof selectMajorReferences, 'function');
});

test('validation preserves the input identity, topic count is data-derived, and selection is immutable', () => {
  const data = fixture(), before = structuredClone(data);
  assert.strictEqual(validate(data), data);
  const results = selectMajorReferences(data);
  assert.equal(results.referenceStandardCount, 2);
  assert.equal(results.searchTopicCount, 5);
  assert.deepEqual(Object.keys(results), ['referenceEntries', 'referenceStandardCount', 'searchTopicCount']);
  assert.notStrictEqual(results.referenceEntries[0], first(data));
  assert.notStrictEqual(results.referenceEntries[0].searchTopics, first(data).searchTopics);
  assert.deepEqual(data, before);
});

test('an empty official snapshot and a zero-topic bibliography record are valid', () => {
  const data = fixture(); data.referenceEntries = [];
  assert.deepEqual(selectMajorReferences(validate(data)), {referenceEntries: [], referenceStandardCount: 0, searchTopicCount: 0});
  data.referenceEntries = [entry({searchTopicCount: 0, searchTopics: []})];
  assert.equal(selectMajorReferences(validate(data)).referenceStandardCount, 1);
  assert.equal(selectMajorReferences(data, {query: 'AQ3067'}).referenceStandardCount, 1);
  assert.equal(selectMajorReferences(data, {query: '5.1.1'}).referenceStandardCount, 0);
  assert.equal(selectMajorReferences(data, {query: '负责人考核'}).referenceStandardCount, 0);
});

test('not tied to one count, REF/LF/LV identity, or version key', () => {
  const data = fixture();
  data.referenceEntries = [entry({id: 'REF_NEW_2024', lawId: 'LF_NEW', lawVersionId: 'LV_NEW_2024',
    title: '另一份题录 AQ/T 7777-2024', standardNumber: 'AQ/T 7777-2024', versionKey: '2024-edition',
    effectiveDate: '2024-02-29', checked: '2026-09-15', searchTopicCount: 1,
    searchTopics: [topic('7.1', '管理制度')],
  })];
  const results = selectMajorReferences(validate(data), {query: 'AQ/T7777-2024'});
  assert.deepEqual(ids(results), ['REF_NEW_2024']);
  assert.equal(results.searchTopicCount, 1);
});

test('checked is a real ISO date at or before asOf, independent of full-text review', () => {
  const data = fixture(); first(data).checked = '2026-09-01';
  validate(data);
  assert.equal(first(data).fullTextReviewed, false);
  first(data).checked = '2024-02-29';
  validate(data);
});

test('notice text may be updated; fixed boolean/content boundaries remain required', () => {
  const data = fixture(); data.notice = '短检索主题不是判定原文，请查阅官方原件。';
  validate(data);
});

test('exact REF filter cannot be substituted with law/LV/title/number or unknown identity', () => {
  const data = validate(fixture());
  assert.deepEqual(ids(selectMajorReferences(data, {standard: 'REF_AQ3067_2026'})), ['REF_AQ3067_2026']);
  for (const standard of ['LF_AQ3067', 'LV_AQ3067_2026', 'AQ3067', 'REF_MISSING', 'ref_aq3067_2026']) {
    assert.equal(selectMajorReferences(data, {standard}).referenceStandardCount, 0, standard);
  }
  assert.equal(selectMajorReferences(data, {standard: 'REF_GB9999_2025', query: 'AQ3067'}).referenceStandardCount, 0);
});

for (const query of ['AQ3067', 'AQ 3067', 'AQ3067-2026', 'AQ 3067-2026', 'aq 3067 - 2026',
  'ＡＱ ３０６７－２０２６', 'AQ 3067 2026']) {
  test(`exact designation supports harmless typography: ${query}`, () => {
    assert.deepEqual(ids(select(query)), ['REF_AQ3067_2026']);
    assert.equal(select(query).searchTopicCount, 3);
  });
}
for (const query of ['GB3067', 'GB 3067-2026', 'AQ/T3067', 'AQ / T 3067-2026',
  'AQ30670', 'AQ03067', 'AQ3067.1', 'AQ3067-2025', 'AQ3067-20260', 'AQ 3067 2025',
  'AQ3067-2026.1', 'AQ3067/2025', 'AQ3067 GB9999', 'AQ3067-2026 AQ3067-2025']) {
  test(`designation never broadens wrong family, number, or edition: ${query}`, () => {
    assert.equal(select(query).referenceStandardCount, 0);
  });
}

test('reference identity comes only from standardNumber, not a title mentioning another standard', () => {
  const data = fixture(); first(data).title += ' 关联 GB 9999-2025';
  assert.deepEqual(ids(selectMajorReferences(validate(data), {query: 'GB9999-2025'})), ['REF_GB9999_2025']);
});

test('exact article identifiers never match longer articles, neighboring identifiers, or substrings', () => {
  const results = select('5.1.1');
  assert.equal(results.searchTopicCount, 2);
  assert.deepEqual(results.referenceEntries.flatMap(row => row.searchTopics.map(item => item.article)), ['5.1.1', '5.1.1']);
  assert.equal(select('5.1.10').searchTopicCount, 1);
  for (const query of ['5.1', '5.1.100', '5.10.1', '05.1.1', '5.1.1 5.1.10']) {
    assert.equal(select(query).searchTopicCount, 0, query);
  }
});

test('standard, title, article, and short topic terms narrow with literal AND', () => {
  const results = select('AQ3067 5.1.1 负责人');
  assert.equal(results.referenceStandardCount, 1);
  assert.equal(results.searchTopicCount, 1);
  assert.equal(results.referenceEntries[0].searchTopicCount, 3, 'source count is retained');
  assert.equal(select('化工').searchTopicCount, 3);
  assert.equal(select('5.1.10 安全仪表').searchTopicCount, 1);
  assert.equal(select('负责人 仪表').searchTopicCount, 0);
  assert.equal(select('SIS配置').searchTopicCount, 1);
  assert.equal(select('30670').searchTopicCount, 0);
});

test('search excludes issuer, IDs, review dates, URLs, notices and internal boundary fields', () => {
  for (const query of ['应急管理部', 'REF_AQ3067_2026', 'LV_AQ3067_2026', '2026-09-30',
    '2026-10-01', 'mem.gov.cn', 'link_only', '法条原文']) {
    assert.equal(select(query).referenceStandardCount, 0, query);
  }
});

test('no typo correction, synonym expansion, related concepts, or inferred site findings', () => {
  for (const query of ['负责人考亥', '负责人考核未通过', '重大隐患', '联锁保护', '安全管理人员', '现场隐患']) {
    assert.equal(select(query).searchTopicCount, 0, query);
  }
});

const invalid = [
  ['schema string', data => { data.schemaVersion = 1; }],
  ['unknown schema version', data => { data.schemaVersion = 'safety-major-criteria-references-v2'; }],
  ['invalid snapshot date', data => { data.asOf = '2026-02-30'; }],
  ['snapshot date mismatch', data => { data.asOf = '2026-09-30'; }],
  ['broadened catalog', data => { data.catalogScope = 'controlled_reviewed_standards_only'; }],
  ['all-industry claim', data => { data.allIndustryCoverage = true; }],
  ['finding boundary', data => { data.wholeNormNotFieldFinding = false; }],
  ['empty notice', data => { data.notice = ''; }],
  ['bad notice type', data => { data.notice = {}; }],
  ['unsafe entry id', data => { first(data).id = 'REF/AQ3067_2026'; }],
  ['empty law id', data => { first(data).lawId = ''; }],
  ['empty version id', data => { first(data).lawVersionId = ''; }],
  ['duplicate entry id', data => { data.referenceEntries[1].id = first(data).id; }],
  ['duplicate law id', data => { data.referenceEntries[1].lawId = first(data).lawId; }],
  ['duplicate version id', data => { data.referenceEntries[1].lawVersionId = first(data).lawVersionId; }],
  ['duplicate standard number', data => { data.referenceEntries[1].standardNumber = 'AQ3067-2026'; }],
  ['invalid standard number', data => { first(data).standardNumber = 'AQ3067-202'; }],
  ['missing edition', data => { first(data).standardNumber = 'AQ3067'; }],
  ['future effective date', data => { first(data).effectiveDate = '2026-10-02'; }],
  ['future checked date', data => { first(data).checked = '2026-10-02'; }],
  ['non-leap effective date', data => { first(data).effectiveDate = '2025-02-29'; }],
  ['invalid checked day', data => { first(data).checked = '2026-09-31'; }],
  ['checked timestamp without timezone', data => { first(data).checked = '2026-10-01T00:00:00'; }],
  ['upcoming status', data => { first(data).validityStatus = 'upcoming'; }],
  ['reference type changed', data => { first(data).contentKind = 'reviewed_clause'; }],
  ['text mode changed', data => { first(data).textMode = 'full_text'; }],
  ['publication permission changed', data => { first(data).publicationPermission = 'full_text'; }],
  ['full review claim', data => { first(data).fullTextReviewed = true; }],
  ['full quote claim', data => { first(data).fullQuotePublicationReady = true; }],
  ['nonzero reviewed clause count', data => { first(data).reviewedClauseCount = 1; }],
  ['nonzero hazard count', data => { first(data).directHazardCount = 1; }],
  ['standalone determination claim', data => { first(data).standaloneDeterminationAllowed = true; }],
  ['whole standard completeness claim', data => { first(data).wholeStandardComplete = true; }],
  ['metadata not ready', data => { first(data).publicationReady.metadata = false; }],
  ['topic publication not ready', data => { first(data).publicationReady.searchTopics = false; }],
  ['full text publication ready', data => { first(data).publicationReady.fullText = true; }],
  ['topic count mismatch', data => { first(data).searchTopicCount = 53; }],
  ['topic count wrong type', data => { first(data).searchTopicCount = '3'; }],
  ['topic count fractional', data => { first(data).searchTopicCount = 3.5; }],
  ['topic count negative', data => { first(data).searchTopicCount = -1; }],
  ['topic count infinite', data => { first(data).searchTopicCount = Infinity; }],
  ['duplicate article', data => { first(data).searchTopics[1].article = '5.1.1'; }],
  ['malformed article', data => { first(data).searchTopics[0].article = '5.1.1.'; }],
  ['article range', data => { first(data).searchTopics[0].article = '5.1.1-5.1.2'; }],
  ['quote content kind', data => { first(data).searchTopics[0].contentKind = 'official_quote'; }],
  ['official quote claim', data => { first(data).searchTopics[0].isOfficialQuote = true; }],
  ['topic standalone claim', data => { first(data).searchTopics[0].standaloneDeterminationAllowed = true; }],
];
for (const [name, mutate] of invalid) {
  test(`fail closed: ${name}`, () => {
    const data = fixture(); mutate(data);
    assert.throws(() => validate(data));
  });
}

for (const [label, pick] of [['root', data => data], ['entry', first],
  ['publicationReady', data => first(data).publicationReady], ['topic', data => first(data).searchTopics[0]]]) {
  test(`all ${label} fields are required, including explicit false values`, () => {
    for (const key of Object.keys(pick(fixture()))) {
      const data = fixture(); delete pick(data)[key];
      assert.throws(() => validate(data), undefined, key);
    }
  });
  test(`unknown ${label} fields cannot carry quotes, hazards, conditions, or unrelated payloads`, () => {
    for (const key of ['quote', 'clauseId', 'hazardId', 'hazardIds', 'linkId', 'associations',
      'applicability', 'summary', 'condition', 'extra']) {
      const data = fixture(); pick(data)[key] = '禁止混入';
      assert.throws(() => validate(data), undefined, key);
    }
  });
  test(`${label} also rejects hidden fields, symbols, and getters`, () => {
    const hidden = fixture(); Object.defineProperty(pick(hidden), 'quote', {value: 'hidden'});
    assert.throws(() => validate(hidden));
    const symbolic = fixture(); pick(symbolic)[Symbol('quote')] = 'hidden';
    assert.throws(() => validate(symbolic));
    const getter = fixture(), target = pick(getter), key = Object.keys(target)[0];
    Object.defineProperty(target, key, {enumerable: true, get() { throw new Error('getter must not run'); }});
    assert.throws(() => validate(getter), /FIELDS/);
  });
}

for (const value of ['', ' ', ' 负责人考核', '负责人考核 ', '负责人　考核', '𠀀', 'é', '负责人\n考核', '负责人\t考核', '负责人。考核', '负责人，考核',
  '负责人/考核', '<img>', '重大隐患！', 'a'.repeat(17), '😀', 'e\u0301', null, 123, {}]) {
  test(`reject non-short-topic content: ${JSON.stringify(value)}`, () => {
    const data = fixture(); first(data).searchTopics[0].searchTopic = value;
    assert.throws(() => validate(data), /SEARCH_TOPIC/);
  });
}

test('short-topic alphabet matches backend; internal ASCII spaces are allowed', () => {
  const data = fixture();
  for (const value of ['SIS1', '汉', '汉'.repeat(16), '负责人 考核']) {
    first(data).searchTopics[0].searchTopic = value;
    validate(data);
  }
  first(data).searchTopics[0].searchTopic = '𠀀'.repeat(17);
  assert.throws(() => validate(data), /SEARCH_TOPIC/);
});

for (const url of ['javascript:alert(1)', 'data:text/html,test', 'http://www.mem.gov.cn/a',
  '//www.mem.gov.cn/a', '/a', 'https://user@www.mem.gov.cn/a', 'https://user:pass@www.mem.gov.cn/a',
  'https://www.mem.gov.cn:444/a', 'https://www.mem.gov.cn.evil.example/a', 'https://evilmemgov.cn/a',
  'https://www.mem.gov.cn@evil.example/a', 'https://localhost/a', 'https://127.0.0.1/a',
  ' https://www.mem.gov.cn/a', 'https://www.mem.gov.cn/a b', 'https://www.mem.gov.cn/\na',
  'https://www.mem.gov.cn/\\evil', 'https://www.mem.gov.cn/a%0ab', 'https://www.mem.gov.cn./a', '', null]) {
  test(`reject unsafe or nonofficial source URL: ${JSON.stringify(url)}`, () => {
    for (const key of ['officialLink', 'officialTextLink']) {
      const data = fixture(); first(data)[key] = url;
      assert.throws(() => validate(data), /OFFICIAL_LINK/);
    }
  });
}

test('another government origin and a safe page fragment remain supported', () => {
  const data = fixture(); first(data).officialLink = 'https://std.samr.gov.cn/gb/search?x=1';
  first(data).officialTextLink += '#page=2';
  validate(data);
});

test('boolean and zero boundary fields reject coercible values', () => {
  for (const key of ['fullTextReviewed', 'fullQuotePublicationReady', 'standaloneDeterminationAllowed', 'wholeStandardComplete']) {
    for (const value of [0, 'false', null, undefined]) {
      const data = fixture(); first(data)[key] = value;
      assert.throws(() => validate(data));
    }
  }
  for (const key of ['reviewedClauseCount', 'directHazardCount']) {
    for (const value of ['0', false, null, undefined, NaN]) {
      const data = fixture(); first(data)[key] = value;
      assert.throws(() => validate(data));
    }
  }
});

test('arrays reject sparse elements and hidden payload properties', () => {
  const sparse = fixture(); delete first(sparse).searchTopics[1];
  assert.throws(() => validate(sparse), /FIELDS/);
  const extra = fixture(); extra.referenceEntries.quote = 'hidden';
  assert.throws(() => validate(extra), /FIELDS/);
});

test('validation rejects non-record input and unexpected snapshot arguments', () => {
  for (const data of [null, undefined, [], '', 1]) assert.throws(() => validate(data));
  for (const date of ['', null, 1, '2026-02-30', '2026-09-30']) {
    assert.throws(() => validateMajorReferences(fixture(), date), /EXPECTED_SNAPSHOT_MISMATCH/);
  }
});

test('selection revalidates and fails closed if a previously checked object was changed', () => {
  const data = validate(fixture()); first(data).searchTopics[0].quote = 'not admitted';
  assert.throws(() => selectMajorReferences(data), /TOPIC_FIELDS/);
});


test('checked accepts an exact ISO timestamp or date and compares its calendar date with asOf', () => {
  const data = fixture();
  for (const value of ['2026-10-01T08:58:25+00:00', '2026-10-01T00:00:00Z',
    '2026-10-01T08:58:25.123+08:00', '2024-02-29T23:59:59-05:30',
    '2026-10-01T23:59:59-12:00', '2026-10-01']) {
    first(data).checked = value;
    validate(data);
  }
});

for (const value of ['2026-02-30T08:58:25+00:00', '2026-10-01T25:00:00Z',
  '2026-10-01T24:00:00Z', '2026-10-01T23:60:00Z', '2026-10-01T23:59:60Z',
  '2026-10-01T08:58:25+24:00', '2026-10-01T08:58:25+08:60',
  '2026-10-01T08:58:25+0800', '2026-10-02T00:00:00+14:00',
  '2026-10-01garbage', '2026-10-01T08:58:25Zgarbage']) {
  test(`reject malformed or future checked timestamp: ${value}`, () => {
    const data = fixture(); first(data).checked = value;
    assert.throws(() => validate(data), /ENTRY_DATE/);
  });
}

test('zero components in an exact article number are valid and still do not prefix-match', () => {
  const data = fixture(); first(data).searchTopics[0].article = '5.0.1';
  validate(data);
  assert.equal(selectMajorReferences(data, {query: '5.0.1'}).searchTopicCount, 1);
  assert.equal(selectMajorReferences(data, {query: '5.0'}).searchTopicCount, 0);
});


test('legacy canonical IDs are preserved without requiring REF, LF, or LV prefixes', () => {
  const data = fixture();
  Object.assign(first(data), {id: 'R019', lawId: 'L019', lawVersionId: 'V019_2026'});
  validate(data);
  assert.deepEqual(ids(selectMajorReferences(data, {standard: 'R019'})), ['R019']);
  for (const key of ['id', 'lawId', 'lawVersionId']) {
    for (const value of ['', 'with space', 'bad/ID', 'bad.ID', 'bad-ID', '<b>', null, 123]) {
      const copy = structuredClone(data); first(copy)[key] = value;
      assert.throws(() => validate(copy), /ENTRY_ID/);
    }
  }
});
