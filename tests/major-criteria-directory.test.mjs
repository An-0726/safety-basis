import test from 'node:test';
import assert from 'node:assert/strict';
import {validateMajorDirectory, selectMajorDirectory} from '../web/js/major-criteria-directory-model.js';

const asOf = '2026-10-01';
const makeEntry = (id, group, label, title, number, overrides = {}) => ({
  id, lawId: `LF_${id}`, lawVersionId: `LV_${id}`, title, documentNumber: number,
  versionKey: number, issuer: '官方发布机关', documentKind: '官方文件', legalNature: '规范性文件',
  directoryGroup: {id: group, label, role: 'primary'}, requiredCompanionIds: [], supplementsReferenceId: null,
  criterionKind: 'major_accident_hazard_determination',
  scopeHint: `${label}相关适用范围`, scopeCaveat: '须按官方原件及具体适用范围核对',
  publicationDate: '2024-01-01', effectiveDate: '2024-02-29', effectiveDateNote: '',
  referenceStatus: 'current', statusLabel: '现行有效', statusAsOf: asOf,
  checked: '2026-10-01T09:39:09+00:00',
  officialLink: 'https://www.mem.gov.cn/reference.shtml',
  officialTextLink: 'https://www.mem.gov.cn/reference.pdf',
  contentKind: 'official_document_reference_only', textMode: 'link_only', publicationPermission: 'metadata_only',
  fullTextReviewed: false, fullQuotePublicationReady: false,
  publicationReady: {metadata: true, fullText: false},
  reviewedClauseCount: 0, directHazardCount: 0, searchTopicCount: 0,
  standaloneDeterminationAllowed: false, wholeStandardComplete: false, ...overrides,
});
const unknownEffective = {effectiveDate: null, effectiveDateNote: '通知要求遵照执行，未单列实施日；不虚填',
  referenceStatus: 'current_in_use', statusLabel: '现行使用中'};

function snapshot(entries) {
  const groups = [...new Set(entries.map(entry => entry.directoryGroup.id))].map(id => {
    const members = entries.filter(entry => entry.directoryGroup.id === id);
    return {id, label: members[0].directoryGroup.label,
      primaryReferenceId: members.find(entry => entry.directoryGroup.role === 'primary').id,
      documentIds: members.map(entry => entry.id)};
  });
  return {schemaVersion: 'safety-major-criteria-directory-v1', asOf,
    catalogScope: 'controlled_official_metadata_directory', allIndustryCoverage: false,
    wholeNormNotFieldFinding: true, notice: '本目录仅提供官方题录，不能独立用于现场判定；并非全行业覆盖。',
    directoryGroupCount: groups.length, documentCount: entries.length, directoryGroups: groups, entries};
}

function fixture() {
  return snapshot([
    makeEntry('DIR_GB35181_2025', 'fire', '消防重大火灾', '重大火灾隐患判定规则 GB 35181-2025', 'GB 35181-2025',
      {effectiveDate: '2025-11-01', publicationDate: '2025-04-25', legalNature: '强制性国家标准'}),
    makeEntry('DIR_MEM_COAL_2026', 'coal_mines', '煤矿',
      '煤矿重大事故隐患判定标准 应急管理部令第21号（2026年修订）', '应急管理部令第21号（2026年修订）'),
    makeEntry('DIR_MIIT_CIVIL_EXPLOSIVES_2024', 'civil_explosives', '民用爆炸物品',
      '民用爆炸物品行业重大事故隐患判定标准 工信部安全〔2024〕234号', '工信部安全〔2024〕234号', unknownEffective),
    makeEntry('DIR_MOHURD_CITY_GAS_2023', 'city_gas', '城镇燃气经营',
      '城镇燃气经营安全重大隐患判定标准 建城规〔2023〕4号', '建城规〔2023〕4号'),
    makeEntry('DIR_MOHURD_CONSTRUCTION_2024', 'construction', '房屋市政施工',
      '房屋市政工程生产安全重大事故隐患判定标准（2024版） 建质规〔2024〕5号', '建质规〔2024〕5号'),
    makeEntry('DIR_NDRC_POWER_2026', 'power', '电力',
      '电力重大事故隐患判定标准及治理监督管理规定 国家发展改革委令第41号（2026年）', '国家发展改革委令第41号（2026年）'),
    makeEntry('DIR_NMSA_NONCOAL_2022', 'noncoal_mines', '金属非金属矿山',
      '金属非金属矿山重大事故隐患判定标准 矿安〔2022〕88号', '矿安〔2022〕88号',
      {requiredCompanionIds: ['DIR_NMSA_NONCOAL_SUPPLEMENT_2024'], scopeHint: '地下矿山、露天矿山和尾矿库，须连同2024年补充情形使用',
        referenceStatus: 'current_in_use', statusLabel: '现行使用中'}),
    makeEntry('DIR_NMSA_NONCOAL_SUPPLEMENT_2024', 'noncoal_mines', '金属非金属矿山',
      '金属非金属矿山重大事故隐患判定标准补充情形 矿安〔2024〕41号', '矿安〔2024〕41号',
      {...unknownEffective, directoryGroup: {id: 'noncoal_mines', label: '金属非金属矿山', role: 'supplement'},
        supplementsReferenceId: 'DIR_NMSA_NONCOAL_2022', scopeHint: '金属非金属地下矿山、露天矿山和尾矿库的补充判定情形'}),
    makeEntry('DIR_SAWS_FIREWORKS_2017', 'fireworks', '烟花爆竹',
      '烟花爆竹生产经营单位重大生产安全事故隐患判定标准（试行） 安监总管三〔2017〕121号（烟花爆竹部分）',
      '安监总管三〔2017〕121号（烟花爆竹部分）', unknownEffective),
  ]);
}

const validate = data => validateMajorDirectory(data, asOf);
const first = data => data.entries[0];
const primary = data => data.entries.find(entry => entry.id === 'DIR_NMSA_NONCOAL_2022');
const supplement = data => data.entries.find(entry => entry.directoryGroup.role === 'supplement');
const noncoal = data => data.directoryGroups.find(group => group.id === 'noncoal_mines');
const select = query => selectMajorDirectory(fixture(), {query});
const groupIds = result => result.directoryGroups.map(group => group.id);

test('pure import has no DOM, boot, shared search, or network dependency', () => {
  assert.equal(typeof globalThis.document, 'undefined');
  assert.equal(typeof validateMajorDirectory, 'function');
  assert.equal(typeof selectMajorDirectory, 'function');
});

test('validates unchanged identity; separate group/document counts are derived and selection is immutable', () => {
  const data = fixture(), before = structuredClone(data);
  assert.strictEqual(validate(data), data);
  const result = selectMajorDirectory(data);
  assert.deepEqual(Object.keys(result), ['directoryGroups', 'directoryGroupCount', 'documentCount']);
  assert.equal(result.directoryGroupCount, 8);
  assert.equal(result.documentCount, 9);
  assert.deepEqual(data, before);
  for (const group of result.directoryGroups) {
    const original = data.directoryGroups.find(row => row.id === group.id);
    assert.deepEqual({...group, entries: undefined}, {...original, entries: undefined});
    assert.notStrictEqual(group, original);
    assert.equal(group.entries[0].id, group.primaryReferenceId);
    assert.equal(group.entries.length, group.documentIds.length);
    for (const entry of group.entries) assert.deepEqual(entry, data.entries.find(row => row.id === entry.id));
  }
});

test('empty and differently sized future catalogs are valid, without hardcoded counts or ID prefixes', () => {
  assert.deepEqual(selectMajorDirectory(validate(snapshot([]))), {directoryGroups: [], directoryGroupCount: 0, documentCount: 0});
  const data = snapshot([makeEntry('R019', 'new_group', '新增目录', '新增官方文件', '部门正式文号',
    {lawId: 'L019', lawVersionId: 'V019'})]);
  assert.strictEqual(validate(data), data);
  assert.equal(selectMajorDirectory(data).directoryGroupCount, 1);
  assert.equal(selectMajorDirectory(data).documentCount, 1);
  assert.equal(selectMajorDirectory(data, {query: '部门正式文号'}).documentCount, 1);
});

test('three unknown effective dates stay null with notes and current-in-use labels', () => {
  const data = validate(fixture());
  const unknown = data.entries.filter(entry => entry.effectiveDate === null);
  assert.equal(unknown.length, 3);
  for (const entry of unknown) {
    assert.ok(entry.effectiveDateNote);
    assert.equal(entry.referenceStatus, 'current_in_use');
    assert.equal(entry.statusLabel, '现行使用中');
  }
  assert.ok(primary(data).effectiveDate, 'current-in-use may also have a known date');
  assert.deepEqual(selectMajorDirectory(data).directoryGroups.flatMap(group => group.entries)
    .filter(entry => entry.effectiveDate === null).map(entry => entry.id).sort(), unknown.map(entry => entry.id).sort());
});

for (const query of ['GB35181', 'GB 35181', 'GB35181-2025', 'GB 35181-2025',
  'gb 35181 - 2025', 'ＧＢ　３５１８１－２０２５', 'GB 35181 2025']) {
  test(`technical designation typography: ${query}`, () => assert.deepEqual(groupIds(select(query)), ['fire']));
}
for (const [query, group] of [['应急管理部令第21号', 'coal_mines'], ['第21号', 'coal_mines'],
  ['应急管理部令第２１号(２０２６年修订)', 'coal_mines'], ['建质规〔2024〕5号', 'construction'],
  ['建质规[2024]5号', 'construction'], ['建质规（2024）5号', 'construction'],
  ['建质规 ［ 2024 ］ 5 号', 'construction'], ['工信部安全【2024】234号', 'civil_explosives'],
  ['安监总管三〔2017〕121号（烟花爆竹部分）', 'fireworks']]) {
  test(`department orders and normative document numbers: ${query}`, () => assert.deepEqual(groupIds(select(query)), [group]));
}

for (const query of ['矿安〔2024〕41号', '矿安[2024]41号', '矿安（2024）41号', '补充情形', '尾矿库', '金属非金属矿山']) {
  test(`a noncoal supplement match returns the entire reciprocal two-file group: ${query}`, () => {
    const result = select(query);
    assert.deepEqual(groupIds(result), ['noncoal_mines']);
    assert.equal(result.directoryGroupCount, 1);
    assert.equal(result.documentCount, 2);
    assert.deepEqual(result.directoryGroups[0].entries.map(entry => entry.id),
      ['DIR_NMSA_NONCOAL_2022', 'DIR_NMSA_NONCOAL_SUPPLEMENT_2024']);
  });
}

test('group selector is an exact group ID and intersects the query', () => {
  const data = fixture();
  assert.equal(selectMajorDirectory(data, {group: 'noncoal_mines'}).documentCount, 2);
  assert.equal(selectMajorDirectory(data, {group: 'noncoal_mines', query: '矿安〔2024〕41号'}).documentCount, 2);
  assert.equal(selectMajorDirectory(data, {group: 'fire', query: '矿安〔2024〕41号'}).documentCount, 0);
  for (const group of ['Noncoal_mines', '金属非金属矿山', 'DIR_NMSA_NONCOAL_2022', 'unknown']) {
    assert.equal(selectMajorDirectory(data, {group}).documentCount, 0, group);
  }
});

for (const query of ['GB3518', 'GB351810', 'GB035181', 'GB35181.1', 'GB35181-2024', 'GB35181-20250',
  'GB35181-2025.1', 'GB35181/2025', 'GB35181 2024', 'GB/T35181', 'AQ35181', '3518', '351810',
  '第2号', '第210号', '应急管理部令第2号', '应急管理部令第21号（2025年修订）',
  '建质规〔2024〕50号', '建质规〔2023〕5号', '矿安〔2024〕4号', '矿安〔2024〕410号',
  '矿安〔2022〕88号 矿安〔2024〕41号', 'GB35181 煤矿']) {
  test(`wrong numbers, editions, or incompatible literal AND terms do not broaden: ${query}`, () => {
    assert.equal(select(query).documentCount, 0);
  });
}

test('AND terms may span public fields on one entry, but not unrelated group members', () => {
  assert.equal(select('矿安〔2024〕41号 金属非金属矿山 尾矿库').documentCount, 2);
  assert.equal(select('房屋市政施工 建质规〔2024〕5号').documentCount, 1);
  const data = fixture(); primary(data).scopeHint = '主件独有'; supplement(data).scopeHint = '补件独有';
  assert.equal(selectMajorDirectory(data, {query: '主件独有 补件独有'}).documentCount, 0);
});

test('document identity never comes from references mentioned in title, group label, or scope', () => {
  const data = fixture();
  first(data).scopeHint = '对照 AQ 7777-2024、矿安〔2024〕41号和应急管理部令第21号（2026年修订）';
  first(data).title += ' 关联 GB 9999-2024 建质规〔2024〕5号';
  first(data).directoryGroup.label = data.directoryGroups[0].label = '参照 GB 8888-2024';
  assert.equal(selectMajorDirectory(data, {query: 'AQ7777-2024'}).documentCount, 0);
  assert.equal(selectMajorDirectory(data, {query: 'GB9999-2024'}).documentCount, 0);
  assert.equal(selectMajorDirectory(data, {query: 'GB8888-2024'}).documentCount, 0);
  assert.deepEqual(groupIds(selectMajorDirectory(data, {query: '矿安〔2024〕41号'})), ['noncoal_mines']);
  assert.deepEqual(groupIds(selectMajorDirectory(data, {query: '应急管理部令第21号'})), ['coal_mines']);
  assert.deepEqual(groupIds(selectMajorDirectory(data, {query: '建质规〔2024〕5号'})), ['construction']);
});

test('search excludes dates, URLs, IDs, issuer, private metadata, notice, caveat, notes, and status', () => {
  for (const query of ['2026-10-01', '2025-11-01', '2025-04-25', '09:39:09', 'mem.gov.cn', 'reference.pdf',
    'DIR_GB35181_2025', 'LF_DIR_GB35181_2025', 'LV_DIR_GB35181_2025', 'noncoal_mines',
    '官方发布机关', '规范性文件', 'link_only', '现行有效', '不虚填', '须按官方原件', '并非全行业覆盖']) {
    assert.equal(select(query).documentCount, 0, query);
  }
});

test('search does not infer aliases, repair typos, interpret queries as regex, or infer findings', () => {
  for (const query of ['非煤', '房屋市政施公', '现场隐患', '尾矿.*', '尾矿[库]', '矿安|GB35181']) {
    assert.equal(select(query).documentCount, 0, query);
  }
});

const invalid = [
  ['schema', data => { data.schemaVersion = 'safety-major-criteria-directory-v2'; }],
  ['invalid asOf', data => { data.asOf = '2026-02-30'; }],
  ['snapshot mismatch', data => { data.asOf = '2026-10-02'; }],
  ['catalog scope', data => { data.catalogScope = 'all_industries'; }],
  ['all-industry claim', data => { data.allIndustryCoverage = true; }],
  ['finding boundary', data => { data.wholeNormNotFieldFinding = false; }],
  ['empty notice', data => { data.notice = ''; }],
  ['group count mixed with documents', data => { data.directoryGroupCount = data.documentCount; }],
  ['document count mixed with groups', data => { data.documentCount = data.directoryGroupCount; }],
  ['duplicate group id', data => { data.directoryGroups[1].id = data.directoryGroups[0].id; }],
  ['duplicate entry id', data => { data.entries[1].id = first(data).id; }],
  ['duplicate law id', data => { data.entries[1].lawId = first(data).lawId; }],
  ['duplicate version id', data => { data.entries[1].lawVersionId = first(data).lawVersionId; }],
  ['missing group', data => { first(data).directoryGroup.id = 'missing'; }],
  ['inconsistent group label', data => { first(data).directoryGroup.label = 'another'; }],
  ['no primary', data => { primary(data).directoryGroup.role = 'supplement'; }],
  ['two primaries', data => { const entry = supplement(data); entry.directoryGroup.role = 'primary'; entry.supplementsReferenceId = null; }],
  ['wrong primary declaration', data => { noncoal(data).primaryReferenceId = supplement(data).id; }],
  ['missing listed primary', data => { noncoal(data).primaryReferenceId = 'missing'; }],
  ['omitted member', data => { noncoal(data).documentIds.pop(); }],
  ['unknown member', data => { noncoal(data).documentIds.push('missing'); }],
  ['duplicate member', data => { noncoal(data).documentIds.push(primary(data).id); }],
  ['cross-group member', data => { noncoal(data).documentIds[1] = first(data).id; }],
  ['missing companion backlink', data => { primary(data).requiredCompanionIds = []; }],
  ['missing companion', data => { primary(data).requiredCompanionIds = ['missing']; }],
  ['cross-group companion', data => { primary(data).requiredCompanionIds = [first(data).id]; }],
  ['duplicate companion', data => { primary(data).requiredCompanionIds.push(supplement(data).id); }],
  ['self companion', data => { primary(data).requiredCompanionIds = [primary(data).id]; }],
  ['orphan supplement', data => { supplement(data).supplementsReferenceId = 'missing'; }],
  ['cross-group supplement', data => { supplement(data).supplementsReferenceId = first(data).id; }],
  ['self supplement', data => { supplement(data).supplementsReferenceId = supplement(data).id; }],
  ['null supplement parent', data => { supplement(data).supplementsReferenceId = null; }],
  ['primary carrying parent', data => { primary(data).supplementsReferenceId = supplement(data).id; }],
  ['supplement carrying companions', data => { supplement(data).requiredCompanionIds = [primary(data).id]; }],
  ['empty effective date note for null date', data => { supplement(data).effectiveDateNote = ''; }],
  ['unknown effective date with current status', data => { Object.assign(supplement(data), {referenceStatus: 'current', statusLabel: '现行有效'}); }],
  ['status mismatch', data => { first(data).statusLabel = '现行使用中'; }],
  ['non-current status', data => { first(data).referenceStatus = 'upcoming'; }],
  ['non-current label', data => { first(data).statusLabel = '废止'; }],
  ['bad role', data => { first(data).directoryGroup.role = 'reference'; }],
  ['long group label', data => { first(data).directoryGroup.label = '字'.repeat(49); }],
  ['long scope', data => { first(data).scopeHint = '字'.repeat(241); }],
  ['long caveat', data => { first(data).scopeCaveat = '字'.repeat(241); }],
  ['long effective note', data => { first(data).effectiveDateNote = '字'.repeat(181); }],
];
for (const [name, mutate] of invalid) {
  test(`fail closed: ${name}`, () => { const data = fixture(); mutate(data); assert.throws(() => validate(data)); });
}

for (const [label, pick] of [['root', data => data], ['group', data => data.directoryGroups[0]],
  ['entry', first], ['entry group', data => first(data).directoryGroup], ['publicationReady', data => first(data).publicationReady]]) {
  test(`all ${label} fields are required and all extensions are rejected`, () => {
    for (const key of Object.keys(pick(fixture()))) {
      const data = fixture(); delete pick(data)[key]; assert.throws(() => validate(data), undefined, key);
    }
    for (const key of ['quote', 'fullText', 'searchTopics', 'topics', 'clauseId', 'hazardId', 'H', 'K',
      'hazardIds', 'linkId', 'associations', 'summary', 'condition', 'extra']) {
      const data = fixture();
      if (Object.hasOwn(pick(data), key)) continue;
      pick(data)[key] = '未审正文/主题不得混入'; assert.throws(() => validate(data), undefined, key);
    }
  });
  test(`${label} rejects symbols, hidden payload, getters, and non-JSON prototypes`, () => {
    const hidden = fixture(); Object.defineProperty(pick(hidden), 'quote', {value: 'hidden'}); assert.throws(() => validate(hidden));
    const symbolic = fixture(); pick(symbolic)[Symbol('quote')] = 'hidden'; assert.throws(() => validate(symbolic));
    const getter = fixture(), target = pick(getter), key = Object.keys(target)[0];
    Object.defineProperty(target, key, {enumerable: true, get() { throw new Error('must not run'); }});
    assert.throws(() => validate(getter), /FIELDS/);
    const prototype = fixture(); Object.setPrototypeOf(pick(prototype), {quote: 'inherited'}); assert.throws(() => validate(prototype));
  });
}

test('metadata-only literal constants reject type coercion and every permission escalation', () => {
  const expected = {contentKind: 'official_document_reference_only', textMode: 'link_only', publicationPermission: 'metadata_only',
    fullTextReviewed: false, fullQuotePublicationReady: false, reviewedClauseCount: 0, directHazardCount: 0,
    searchTopicCount: 0, standaloneDeterminationAllowed: false, wholeStandardComplete: false};
  for (const [key, correct] of Object.entries(expected)) {
    for (const value of [null, undefined, true, false, 0, 1, '0', 'false', 'reviewed_clause', NaN]) {
      if (Object.is(value, correct)) continue;
      const data = fixture(); first(data)[key] = value; assert.throws(() => validate(data), undefined, `${key}: ${value}`);
    }
  }
  for (const key of ['metadata', 'fullText']) {
    for (const value of [null, undefined, 0, 1, 'false', key === 'metadata' ? false : true]) {
      const data = fixture(); first(data).publicationReady[key] = value; assert.throws(() => validate(data));
    }
  }
});

test('all metadata text and IDs are checked without assuming every document is a technical standard', () => {
  for (const key of ['title', 'documentNumber', 'versionKey', 'issuer', 'documentKind', 'legalNature', 'scopeHint', 'scopeCaveat']) {
    for (const value of ['', ' ', ' leading', 'trailing ', 'control\ncharacter', null, 123, {}]) {
      const data = fixture(); first(data)[key] = value; assert.throws(() => validate(data), undefined, key);
    }
  }
  for (const key of ['id', 'lawId', 'lawVersionId', 'criterionKind']) {
    for (const value of ['', 'bad/id', 'bad-id', 'bad.id', 'with space', '<b>', null, 123]) {
      const data = fixture(); first(data)[key] = value; assert.throws(() => validate(data), undefined, key);
    }
  }
});

test('counts reject coercible, fractional, negative, and unsafe values', () => {
  for (const key of ['directoryGroupCount', 'documentCount']) {
    for (const value of ['8', null, false, -1, 0.5, NaN, Infinity, Number.MAX_SAFE_INTEGER + 1]) {
      const data = fixture(); data[key] = value; assert.throws(() => validate(data));
    }
  }
});

test('real ISO dates at or before asOf are required for every date field', () => {
  for (const key of ['publicationDate', 'effectiveDate', 'statusAsOf', 'checked']) {
    for (const value of ['', '2026-02-30', '2025-02-29', '0000-01-01', '2026-10-02', '2026-1-1', 20261001]) {
      const data = fixture(); first(data)[key] = value; assert.throws(() => validate(data), undefined, `${key}: ${value}`);
    }
  }
  const data = fixture();
  for (const key of ['publicationDate', 'effectiveDate', 'statusAsOf', 'checked']) first(data)[key] = '2024-02-29';
  validate(data);
});

test('checked accepts dates and explicit-zone ISO timestamps using their written calendar date', () => {
  for (const value of ['2026-10-01', '2026-10-01T09:39:09+00:00', '2026-10-01T00:00:00Z',
    '2026-10-01T08:58:25.123+08:00', '2024-02-29T23:59:59-05:30', '2026-10-01T23:59:59-12:00']) {
    const data = fixture(); first(data).checked = value; first(data).statusAsOf = value.slice(0, 10); validate(data);
  }
  for (const value of ['2026-02-30T08:58:25Z', '2026-10-01T24:00:00Z', '2026-10-01T23:60:00Z',
    '2026-10-01T23:59:60Z', '2026-10-01T08:58:25+24:00', '2026-10-01T08:58:25+08:60',
    '2026-10-01T08:58:25+0800', '2026-10-01T08:58:25', '2026-10-02T00:00:00+14:00', '2026-10-01T00:00:00Zextra']) {
    const data = fixture(); first(data).checked = value; assert.throws(() => validate(data), /ENTRY_DATE/);
  }
});

test('every URL is credential-free, port-free official HTTPS and rejects parser-normalized unsafe input', () => {
  for (const url of ['javascript:alert(1)', 'data:text/html,x', 'http://www.mem.gov.cn/a', '//www.mem.gov.cn/a',
    'https:www.mem.gov.cn/a', '/a', 'https://user@www.mem.gov.cn/a', 'https://user:pass@www.mem.gov.cn/a',
    'https://www.mem.gov.cn:443/a', 'https://www.mem.gov.cn:444/a', 'https://www.mem.gov.cn.evil.example/a',
    'https://evilmemgov.cn/a', 'https://www.mem.gov.cn@evil.example/a', 'https://localhost/a', 'https://127.0.0.1/a',
    ' https://www.mem.gov.cn/a', 'https://www.mem.gov.cn/a b', 'https://www.mem.gov.cn/\na',
    'https://www.mem.gov.cn/\\evil', 'https://www.mem.gov.cn/a%0ab', 'https://www.mem.gov.cn/a%7Fb',
    'https://www.mem.gov.cn./a', 'https://www.mem.gov.cn/\u0085', 'https://www.mem.gov.cn/\u200b', '', null]) {
    for (const key of ['officialLink', 'officialTextLink']) {
      const data = fixture(); first(data)[key] = url; assert.throws(() => validate(data), /OFFICIAL_LINK/);
    }
  }
  const data = fixture(); first(data).officialLink = 'https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=abc';
  first(data).officialTextLink = 'https://www.jiyuan.gov.cn/reference.pdf#page=2'; validate(data);
});

test('arrays reject sparse elements, hidden fields, symbols, and getters', () => {
  for (const pick of [data => data.entries, data => data.directoryGroups, data => noncoal(data).documentIds,
    data => primary(data).requiredCompanionIds]) {
    const sparse = fixture(); delete pick(sparse)[0]; assert.throws(() => validate(sparse), /FIELDS/);
    const extra = fixture(); pick(extra).quote = 'hidden'; assert.throws(() => validate(extra), /FIELDS/);
    const symbolic = fixture(); pick(symbolic)[Symbol('quote')] = 'hidden'; assert.throws(() => validate(symbolic), /FIELDS/);
    const getter = fixture(); Object.defineProperty(pick(getter), '0', {enumerable: true, get() { throw Error('must not run'); }});
    assert.throws(() => validate(getter), /FIELDS/);
  }
});

test('non-record snapshots and malformed expected dates fail closed; selection revalidates', () => {
  for (const data of [null, undefined, [], '', 1]) assert.throws(() => validate(data));
  for (const date of ['', null, 1, '2026-02-30', '2026-09-30']) {
    assert.throws(() => validateMajorDirectory(fixture(), date), /EXPECTED_SNAPSHOT_MISMATCH/);
  }
  const data = validate(fixture()); supplement(data).searchTopics = ['未审主题'];
  assert.throws(() => selectMajorDirectory(data), /ENTRY_FIELDS/);
});

test('all companions are required when a future group contains multiple supplements', () => {
  const data = fixture(), extra = structuredClone(supplement(data));
  Object.assign(extra, {id: 'R_EXTRA', lawId: 'L_EXTRA', lawVersionId: 'V_EXTRA', documentNumber: '矿安〔2025〕51号'});
  data.entries.push(extra); data.documentCount++; noncoal(data).documentIds.push(extra.id);
  primary(data).requiredCompanionIds.push(extra.id); validate(data);
  assert.equal(selectMajorDirectory(data, {query: '矿安〔2025〕51号'}).documentCount, 3);
  primary(data).requiredCompanionIds.pop(); assert.throws(() => validate(data), /GROUP_COMPANION_GRAPH/);
});

test('currentness observation cannot postdate its metadata review', () => {
  const data = fixture(); data.entries[0].checked = '2026-09-30T12:00:00+08:00';
  assert.throws(() => validate(data), /CURRENTNESS_AFTER_REVIEW/);
});
