import test from 'node:test';
import assert from 'node:assert/strict';
import {validateMajorData, validateDirectoryCatalogLinks, parseMajorRoute, majorRouteQuery, selectMajorResults,
  snapshotNoticeText} from '../web/js/major-criteria-model.js';

const asOf = '2026-10-01';
const sourceUrl = 'https://www.mem.gov.cn/example.shtml';
const clause = (id, version, quote, hazardIds = []) => ({clauseId: id,
  article: `条文 ${id}`, quote, checked: '2026-09-30', status: '现行有效', sourceUrl,
  lawVersionId: version, granularity: 'whole_clause', directHazardIds: hazardIds});
const standard = (id, version, name, clauses, hazardIds) => ({id, lawVersionId: version,
  standardVersion: {lawId: `LF-${version}`, name, documentNumber: `标准 ${version}`,
    versionKey: `${version}-2026`, effectiveDate: '2026-01-01', endDate: '',
    validityStatus: 'active', officialSourceUrl: sourceUrl},
  officialScope: {label: `${name}受控判定范围`, sourceUrls: [sourceUrl], wholeStandardComplete: false},
  coverage: {status: 'reviewed_scope_complete', reviewedClauseCount: clauses.length,
    reviewedWholeClauseCount: clauses.length, reviewedSubitemClauseCount: 0,
    expectedWholeClauseCount: clauses.length, expectedJudgmentItemCount: null,
    reviewedJudgmentItemCount: null, wholeStandardComplete: false},
  clauses, directHazardIds: hazardIds, directHazardCount: hazardIds.length});
const association = (hazardId, linkId, clauseId, lawVersionId, applicability) => ({
  hazardId, linkId, clauseId, lawVersionId, role: 'direct', applicability, jurisdictionCode: 'CN'});
const hazard = (id, title, category, over = {}) => ({id, title, category,
  displayCategory: category, searchText: title.toLowerCase(), status: '已核验', publishable: true, ...over});

function fixture() {
  const standards = [
    standard('standard-a', 'LV-A', '工贸判定标准', [
      clause('C-A1', 'LV-A', '粉尘设备缺少隔爆措施。', ['H-A']),
      clause('C-A2', 'LV-A', '无关联隐患的独立判定条文，须保持可见。'),
    ], ['H-A', 'H-SHARED']),
    standard('standard-b', 'LV-B', '特种设备判定标准', [
      clause('C-B1', 'LV-B', '起重机械安全装置失效。', ['H-B', 'H-SHARED']),
    ], ['H-B', 'H-SHARED']),
  ];
  return {
    catalog: {schemaVersion: 1, asOf, wholeNormNotFieldFinding: true,
      catalogScope: 'controlled_reviewed_standards_only', allIndustryCoverage: false, standards},
    topic: {schemaVersion: 1, asOf, wholeNormNotFieldFinding: true, associations: [
      association('H-A', 'K-A', 'C-A1', 'LV-A', '只适用于粉尘工贸企业'),
      association('H-SHARED', 'K-A-SUB', 'C-A-EXCERPT', 'LV-A', '甲范围适用要求'),
      association('H-B', 'K-B', 'C-B1', 'LV-B', '只适用于起重机械'),
      association('H-SHARED', 'K-B-SHARED', 'C-B1', 'LV-B', '乙范围适用要求'),
    ], hazardIds: ['H-A', 'H-B', 'H-SHARED'],
    coverage: {excludedAssociationCount: 4, excludedHazardCount: 4, exclusionReason: '关联待复核'}},
    searchIndex: [
      hazard('H-A', '粉尘除尘器 ABC 安全装置失效', '粉尘防爆'),
      hazard('H-B', '起重机械装置失效', '特种设备'),
      hazard('H-SHARED', '安全装置未设置', '安全管理', {displayCategory: '机械安全'}),
      hazard('H-KEYWORD', '重大事故隐患关键词命中', '粉尘防爆'),
    ],
  };
}
const validate = data => validateMajorData(data.catalog, data.topic, data.searchIndex, asOf);
const ids = rows => rows.map(row => row.id);

test('可独立导入纯模型，无需 DOM 或应用启动', () => {
  assert.equal(typeof validateMajorData, 'function');
  assert.equal(typeof globalThis.document, 'undefined');
});

test('数量来自发布数据，规范条文不依赖是否已有 H，保留专题覆盖提示', () => {
  const data = fixture(), model = validate(data), results = selectMajorResults(model);
  assert.equal(results.standards.length, 2);
  assert.equal(results.standards.flatMap(row => row.clauses).length, 3);
  assert.equal(results.hazards.length, 3);
  assert.equal(model.topic.coverage.excludedHazardCount, 4);
  const found = selectMajorResults(model, {query: '独立判定'});
  assert.equal(found.standards[0].clauses[0].clauseId, 'C-A2');
  assert.equal(found.hazards.length, 0);
});

test('重大关键词不能把专题之外的 H 纳入', () => {
  const model = validate(fixture());
  assert.ok(!ids(model.hazards).includes('H-KEYWORD'));
  assert.deepEqual(ids(selectMajorResults(model, {query: '重大'}).hazards), []);
});

test('专业过滤正交于专题归属，优先 displayCategory 且不改变原始 category', () => {
  const data = fixture(), before = structuredClone(data), model = validate(data);
  assert.deepEqual(ids(selectMajorResults(model, {category: '机械安全'}).hazards), ['H-SHARED']);
  assert.deepEqual(ids(selectMajorResults(model, {category: '安全管理'}).hazards), []);
  assert.equal(selectMajorResults(model, {category: '机械安全'}).standards.length, 2);
  assert.equal(model.hazards[2].category, '安全管理');
  assert.strictEqual(model.hazards[2], data.searchIndex[2]);
  assert.deepEqual(data, before);
});

test('无 displayCategory 时保留原 category 的精确筛选', () => {
  const data = fixture(); delete data.searchIndex[0].displayCategory;
  assert.deepEqual(ids(selectMajorResults(validate(data), {category: '粉尘防爆'}).hazards), ['H-A']);
});

test('标准按精确 LV 限制专题关联，不按标准 id、名称或 H 的其他依据推测', () => {
  const model = validate(fixture());
  const a = selectMajorResults(model, {standard: 'LV-A'});
  assert.deepEqual(ids(a.standards), ['standard-a']);
  assert.deepEqual(ids(a.hazards), ['H-A', 'H-SHARED']);
  assert.deepEqual(ids(selectMajorResults(model, {standard: 'LV-B'}).hazards), ['H-B', 'H-SHARED']);
  assert.deepEqual(selectMajorResults(model, {standard: 'standard-a'}), {standards: [], hazards: [], matchKind: 'all', interpretedQuery: '', queryNotice: ''});
  assert.deepEqual(selectMajorResults(model, {standard: 'unknown'}), {standards: [], hazards: [], matchKind: 'all', interpretedQuery: '', queryNotice: ''});
  assert.deepEqual(ids(selectMajorResults(model, {standard: 'LV-A', category: '特种设备'}).hazards), []);
});

test('关联的摘项 C 不必出现在整条目录，适用范围 query 只看选中的 LV', () => {
  const model = validate(fixture());
  assert.ok(model.topic.associations.some(row => row.clauseId === 'C-A-EXCERPT'));
  assert.deepEqual(ids(selectMajorResults(model, {standard: 'LV-A', query: '甲范围'}).hazards), ['H-SHARED']);
  assert.deepEqual(ids(selectMajorResults(model, {standard: 'LV-B', query: '甲范围'}).hazards), []);
});

test('空格 AND 与 Unicode 规范化仅在受控集合内过滤', () => {
  const model = validate(fixture());
  assert.deepEqual(ids(selectMajorResults(model, {query: '粉尘 ＡＢＣ'}).hazards), ['H-A']);
  assert.deepEqual(ids(selectMajorResults(model, {query: '粉尘 起重'}).hazards), []);
  assert.equal(selectMajorResults(model, {query: '工贸 隔爆'}).standards[0].clauses.length, 1);
  assert.equal(selectMajorResults(model, {query: '工贸'}).standards[0].clauses.length, 2);
});

test('路由默认值、未知 view 回退、URL 编解码和序列化往返', () => {
  const defaults = {view: 'clauses', standard: '', category: '', query: ''};
  assert.deepEqual(parseMajorRoute(''), defaults);
  assert.deepEqual(parseMajorRoute('?view=all&ignored=1'), defaults);
  assert.equal(majorRouteQuery(defaults), '');
  const route = {view: 'hazards', standard: 'standard-a', category: '粉尘防爆', query: '粉尘 ABC & +'};
  const query = majorRouteQuery(route);
  assert.ok(query.startsWith('view=hazards&standard=standard-a&category='));
  assert.deepEqual(parseMajorRoute(query), route);
  assert.equal(majorRouteQuery(parseMajorRoute(query)), query);
  assert.deepEqual(parseMajorRoute('?q=++粉尘+++ABC++&view=hazards'), {...defaults, view: 'hazards', query: '粉尘 ABC'});
  assert.deepEqual(parseMajorRoute(majorRouteQuery({view: 'bad', standard: 'unknown'})), {...defaults, standard: 'unknown'});
});

test('快照同日无警告，过去、未来、缺失或无效日期明确警告且不依赖时钟', () => {
  assert.equal(snapshotNoticeText(asOf, asOf), '');
  assert.match(snapshotNoticeText(asOf, '2026-10-02'), /早于当前日期/);
  assert.match(snapshotNoticeText(asOf, '2027-01-01'), /2026-10-01/);
  assert.match(snapshotNoticeText(asOf, '2026-09-30'), /晚于当前日期/);
  assert.match(snapshotNoticeText('2026-02-30', asOf), /日期缺失或无效/);
  assert.match(snapshotNoticeText('', asOf), /日期缺失或无效/);
  assert.match(snapshotNoticeText(asOf, ''), /当前日期无法确认/);
});

test('标准号紧凑写法在受控条文中可召回，family/编号/年份均不得误扩', () => {
  const data = fixture();
  data.catalog.standards[1].standardVersion.documentNumber = 'GB 45067-2024';
  const model = validate(data);
  for (const query of ['GB45067', 'GB 45067', 'GB45067-2024', 'ＧＢ４５０６７']) {
    assert.deepEqual(ids(selectMajorResults(model, {query}).standards), ['standard-b'], query);
  }
  for (const query of ['GB450670', 'GB45067-2025', 'GB/T45067']) {
    assert.deepEqual(ids(selectMajorResults(model, {query}).standards), [], query);
  }
});

const invalidCases = [
  ['未知 catalog schema', data => { data.catalog.schemaVersion = 2; }, 'CATALOG_SCHEMA'],
  ['字符串 schema', data => { data.topic.schemaVersion = '1'; }, 'TOPIC_SCHEMA'],
  ['专题日期不一致', data => { data.topic.asOf = '2026-09-30'; }, 'SNAPSHOT_MISMATCH'],
  ['非法日历日期', data => { data.catalog.asOf = '2026-02-30'; }, 'CATALOG_DATE'],
  ['扩大全行业口径', data => { data.catalog.allIndustryCoverage = true; }, 'CATALOG_SCOPE'],
  ['取消非现场认定边界', data => { data.topic.wholeNormNotFieldFinding = false; }, 'TOPIC_FINDING_BOUNDARY'],
  ['重复标准 ID', data => { data.catalog.standards[1].id = 'standard-a'; }, 'STANDARD_ID'],
  ['重复标准 LV', data => { data.catalog.standards[1].lawVersionId = 'LV-A'; }, 'STANDARD_VERSION_ID'],
  ['条文错配 LV', data => { data.catalog.standards[0].clauses[0].lawVersionId = 'LV-B'; }, 'CLAUSE_VERSION'],
  ['未知条文粒度', data => { data.catalog.standards[0].clauses[0].granularity = 'subitem'; }, 'CLAUSE_GRANULARITY'],
  ['缺正文', data => { data.catalog.standards[0].clauses[0].quote = ''; }, 'CLAUSE_CONTENT'],
  ['脚本来源链接', data => { data.catalog.standards[0].clauses[0].sourceUrl = 'javascript:alert(1)'; }, 'CLAUSE_CONTENT'],
  ['夸大全标准完整度', data => { data.catalog.standards[0].coverage.wholeStandardComplete = true; }, 'COMPLETE_BODY_COVERAGE'],
  ['错误条文数量', data => { data.catalog.standards[0].coverage.reviewedClauseCount = 99; }, 'COVERAGE_COUNTS'],
  ['完整范围的判定项数量矛盾', data => {
    data.catalog.standards[0].coverage.expectedJudgmentItemCount = 4;
    data.catalog.standards[0].coverage.reviewedJudgmentItemCount = 3;
  }, 'JUDGMENT_COMPLETENESS'],
  ['非 direct role', data => { data.topic.associations[0].role = 'reference'; }, 'ASSOCIATION_ROLE'],
  ['缺适用条件', data => { data.topic.associations[0].applicability = ''; }, 'ASSOCIATION_CONTENT'],
  ['目录外 LV', data => { data.topic.associations[0].lawVersionId = 'LV-OUTSIDE'; }, 'ASSOCIATION_VERSION'],
  ['已知整条 C 错配 LV', data => { data.topic.associations[0].lawVersionId = 'LV-B'; }, 'ASSOCIATION_CLAUSE_VERSION'],
  ['重复关联 K', data => { data.topic.associations.push({...data.topic.associations[0]}); }, 'ASSOCIATION_DUPLICATE'],
  ['公开索引缺少 H', data => { data.searchIndex = data.searchIndex.filter(row => row.id !== 'H-A'); }, 'ASSOCIATION_HAZARD_MISSING'],
  ['公开索引重复 H', data => { data.searchIndex.push({...data.searchIndex[0]}); }, 'SEARCH_INDEX_ID'],
  ['专题多报 H', data => { data.topic.hazardIds.push('H-KEYWORD'); }, 'TOPIC_HAZARD_MEMBERSHIP'],
  ['专题漏报 H', data => { data.topic.hazardIds.pop(); }, 'TOPIC_HAZARD_MEMBERSHIP'],
  ['专题 H 重复', data => { data.topic.hazardIds.push('H-A'); }, 'TOPIC_HAZARD_IDS_DUPLICATE'],
  ['标准直接 H 数量错误', data => { data.catalog.standards[0].directHazardCount = 99; }, 'STANDARD_HAZARD_COUNT'],
  ['标准直接 H 归属错误', data => { data.catalog.standards[0].directHazardIds[0] = 'H-B'; }, 'STANDARD_HAZARD_MEMBERSHIP'],
  ['条文直接 H 归属错误', data => { data.catalog.standards[0].clauses[1].directHazardIds = ['H-A']; }, 'CLAUSE_HAZARD_MEMBERSHIP'],
  ['禁止发布 H', data => { data.searchIndex[0].publishable = false; }, 'TOPIC_HAZARD_CONTENT'],
  ['未核验 H', data => { data.searchIndex[0].status = '待审核候选'; }, 'TOPIC_HAZARD_CONTENT'],
];
for (const [name, mutate, code] of invalidCases) {
  test(`fail-closed：${name}`, () => {
    const data = fixture(); mutate(data);
    assert.throws(() => validate(data), new RegExp(code));
  });
}

test('要求发布清单日期与两个专题文件一致', () => {
  const data = fixture();
  assert.throws(() => validateMajorData(data.catalog, data.topic, data.searchIndex, '2026-09-30'),
    /EXPECTED_SNAPSHOT_MISMATCH/);
});

test('空的受控快照合法且不会自动从关键词补足内容', () => {
  const data = fixture();
  data.catalog.standards = []; data.topic.associations = []; data.topic.hazardIds = [];
  assert.deepEqual(selectMajorResults(validate(data)), {standards: [], hazards: [], matchKind: 'all', interpretedQuery: '', queryNotice: ''});
});


test('显式空审核日期和null辖区按契约保留，不推断缺失值', () => {
  const data=fixture();
  data.catalog.standards[0].clauses[0].checked='';
  data.topic.associations[0].jurisdictionCode=null;
  const result=validate(data);
  assert.equal(result.standards[0].clauses[0].checked,'');
  assert.equal(result.topic.associations[0].jurisdictionCode,null);
});

test('审核日期及辖区仍拒绝缺字段、乱类型和无效日期', () => {
  for(const value of [undefined,null,4,{},'2026-02-30','2026-10-01garbage']){
    const data=fixture();data.catalog.standards[0].clauses[0].checked=value;
    assert.throws(()=>validate(data),/CLAUSE_CONTENT/);
  }
  for(const value of [undefined,'',false,4,{}]){
    const data=fixture();data.topic.associations[0].jurisdictionCode=value;
    assert.throws(()=>validate(data),/ASSOCIATION_CONTENT/);
  }
});

function fullBody(data=fixture()) {
  const s=data.catalog.standards[0];
  s.officialScope.wholeStandardComplete=true;s.coverage.wholeStandardComplete=true;
  s.publicationBasis={basis:'copyright_law_article_5_official_administrative_document',legalSourceUrl:'https://www.nsfc.gov.cn/copyright',checked:'2026-10-01T11:37:27+00:00',fullTextPublicationApproved:true};
  return data;
}
test('complete official administrative body requires its separate publication review',()=>{
  const data=fullBody();assert.equal(validate(data).standards[0].coverage.wholeStandardComplete,true);
  delete data.catalog.standards[0].publicationBasis;
  assert.throws(()=>validate(data),/COMPLETE_BODY_REVIEW/);
});
for(const [name,change] of [
  ['future review',p=>p.checked='2026-10-02'],['missing timezone',p=>p.checked='2026-10-01T11:00:00'],
  ['nonofficial rights source',p=>p.legalSourceUrl='https://example.com/copyright'],
  ['metadata approval only',p=>p.fullTextPublicationApproved=false],['different legal basis',p=>p.basis='official_website_exists']
])test(`complete body rejects ${name}`,()=>{const data=fullBody();change(data.catalog.standards[0].publicationBasis);assert.throws(()=>validate(data),/PUBLICATION_BASIS/);});
test('complete body cannot retain a partial-coverage label',()=>{const data=fullBody();data.catalog.standards[0].coverage.status='partial';assert.throws(()=>validate(data),/COMPLETE_BODY_COVERAGE/);});
test('directory can link only the exact reviewed normative version without creating clauses or H',()=>{
  const data=fullBody(),m=validate(data),v=m.standards[0].standardVersion;
  const entry={lawVersionId:'LV-A',lawId:v.lawId,title:v.name,documentNumber:v.documentNumber,versionKey:v.versionKey,effectiveDate:v.effectiveDate};
  assert.doesNotThrow(()=>validateDirectoryCatalogLinks(m,{entries:[entry]}));
  assert.doesNotThrow(()=>validateDirectoryCatalogLinks(m,{entries:[{...entry,title:`${v.name} ${v.documentNumber}`}]}));
  for(const key of ['lawId','title','documentNumber','versionKey','effectiveDate'])assert.throws(()=>validateDirectoryCatalogLinks(m,{entries:[{...entry,[key]:'wrong'}]}),/DIRECTORY_CATALOG_IDENTITY/);
  delete m.standards[0].publicationBasis;
  assert.throws(()=>validateDirectoryCatalogLinks(m,{entries:[entry]}),/DIRECTORY_CATALOG_IDENTITY/);
});

test('shared scope notes do not make every article match a cited article number or exception',()=>{
  const data=fixture(),s=data.catalog.standards[0];
  s.officialScope.label='第九条保留经营者责任前提，第六条例外需核对';
  s.clauses[0].article='第9条';s.clauses[0].quote='第九条 经营者发现问题后未按规定采取措施';
  s.clauses[1].article='第6条';s.clauses[1].quote='第六条 除确需穿过且已采取有效防护措施外';
  const result=selectMajorResults(validate(data),{standard:'LV-A',query:'第九条'});
  assert.deepEqual(result.standards[0].clauses.map(c=>c.clauseId),['C-A1']);
  assert.deepEqual(selectMajorResults(validate(data),{standard:'LV-A',query:'有效防护'}).standards[0].clauses.map(c=>c.clauseId),['C-A2']);
});

test('explicit administrative numbers match current identity and do not inherit a repealed citation',()=>{
  const data=fixture(),s=data.catalog.standards[0];
  s.standardVersion.documentNumber='建质规〔2024〕5号';s.standardVersion.versionKey='建质规〔2024〕5号';
  s.clauses[0].article='第18条';s.clauses[0].quote='第十八条 本标准执行。2022版（建质规〔2022〕2号）同时废止。';
  const m=validate(data);
  assert.deepEqual(selectMajorResults(m,{query:'建质规〔2022〕2号'}).standards,[]);
  assert.equal(selectMajorResults(m,{query:'建质规〔2024〕5号'}).standards[0].clauses.length,2);
  assert.deepEqual(selectMajorResults(m,{query:'建质规〔2024〕5号 第18条'}).standards[0].clauses.map(c=>c.clauseId),['C-A1']);
  assert.deepEqual(selectMajorResults(m,{query:'2022版'}).standards[0].clauses.map(c=>c.clauseId),['C-A1']);
  s.standardVersion.documentNumber='应急管理部令第21号';s.clauses[0].quote='依据应急管理部令第8号。';
  assert.deepEqual(selectMajorResults(validate(data),{standard:'LV-A',query:'应急管理部令第8号'}).standards,[]);
});
