import test from 'node:test';
import assert from 'node:assert/strict';
import { searchHazards, searchLaws, normalize } from '../web/js/search.js';

const hazardRow = (over = {}) => ({
  id: 'H_TEST', title: '配电室未设置警示标志', aliases: [], keywords: [], lawNames: [],
  stdNumbers: [], places: [], levels: [], scopes: ['全国'], mode: '直接适用',
  status: '已核验', category: '电气安全', searchText: '配电室 未设置警示标志',
  ...over,
});

test('口语词“配电房”通过同义词组召回“配电室”记录', () => {
  const rows = [hazardRow()];
  const hits = searchHazards(rows, '配电房', {});
  assert.equal(hits.length, 1);
});

test('同义组内其他变体（配电箱）同样可召回', () => {
  const rows = [hazardRow()];
  assert.equal(searchHazards(rows, '配电箱', {}).length, 1);
});

test('无同义关系的词不应被放行（精确性不放松）', () => {
  const rows = [hazardRow()];
  assert.equal(searchHazards(rows, '灭火器', {}).length, 0);
});

test('原词命中仍优先于同义变体（评分排序不变）', () => {
  const exact = hazardRow({ id: 'EXACT' });
  const variant = hazardRow({ id: 'VARIANT', title: '配电箱未设置警示标志', searchText: '配电箱 未设置警示标志' });
  const hits = searchHazards([variant, exact], '配电室', {});
  assert.equal(hits[0].id, 'EXACT');
});

test('法规搜索同样使用同义词组', () => {
  const laws = [{ id: 'L_TEST', name: '低压配电设计规范', aliases: [], level: '国家标准', scope: '全国',
                  status: '现行有效', searchText: '低压配电设计规范' }];
  assert.equal(searchLaws(laws, '配电房规范', {}).length, 1);
});

test('normalize 行为保持不变（查询与 searchText 同形）', () => {
  assert.equal(normalize('配电室，未设置！'), '配电室,未设置!');
  assert.equal(normalize('  灭火器　失压  '), '灭火器 失压');
});

test('错字容错：单字符错字仍可召回（灭活器→灭火器）', () => {
  const rows = [hazardRow({ title: '灭火器失压', searchText: '灭火器失压 灭火器 欠压' })];
  assert.equal(searchHazards(rows, '灭活器', {}).length, 1);
});

test('错字容错不误放完全无关的词', () => {
  const rows = [hazardRow()];
  assert.equal(searchHazards(rows, '消防水袋', {}).length, 0);
});

test('扩容同义组：危化品→危险化学品、叉车→厂内机动车、消火栓→消防栓', () => {
  const haz = hazardRow({ title: '危险化学品仓库未设置警示标志', searchText: '危险化学品 仓库 警示标志' });
  assert.equal(searchHazards([haz], '危化品', {}).length, 1);
  const che = hazardRow({ title: '叉车未定期检验', searchText: '厂内机动车 叉车 检验' });
  assert.equal(searchHazards([che], '叉车', {}).length, 1);
  const hydrant = hazardRow({ title: '消火栓被遮挡', searchText: '消火栓 遮挡' });
  assert.equal(searchHazards([hydrant], '消防栓', {}).length, 1);
});

test('无空格中文复合查询（配电箱遮挡）精准切词且拒绝假阳性', () => {
  const mismatch = hazardRow({
    id: 'H_MISMATCH',
    title: '照明配电箱（盘）内配线不整齐或存在绞接',
    searchText: '照明配电箱 盘 内配线不整齐或存在绞接 配电箱 配电 配线 绞接',
  });
  const match = hazardRow({
    id: 'H_MATCH',
    title: '配电箱前堆放杂物遮挡操作通道',
    searchText: '配电箱前堆放杂物遮挡操作通道 配电箱 堆放 堆物 杂物 遮挡 操作 通道',
  });
  const hits = searchHazards([mismatch, match], '配电箱遮挡', {});
  assert.equal(hits.length, 1);
  assert.equal(hits[0].id, 'H_MATCH');
});

test('复合查询各概念分别支持同义词扩展（配电柜堵塞 / 配电箱堆物）', () => {
  const row = hazardRow({
    id: 'H_MATCH',
    title: '配电箱前堆放杂物遮挡操作通道',
    searchText: '配电箱前堆放杂物遮挡操作通道 配电箱 堆放 堆物 杂物 遮挡 操作 通道',
  });
  assert.equal(searchHazards([row], '配电柜堵塞', {}).length, 1);
  assert.equal(searchHazards([row], '配电箱堆物', {}).length, 1);
});

test('受控展示字段支持主题、场景、依据类型和未细分场景筛选', () => {
  const rows = [
    hazardRow({id: 'H_ELEC', displayCategory: '电气安全', sceneTags: ['电气与配电'], displayLevels: ['国家标准']}),
    hazardRow({id: 'H_UNCLASSIFIED', displayCategory: '电气安全', sceneTags: [], displayLevels: ['国家标准']}),
    hazardRow({id: 'H_OTHER', displayCategory: '机械与设备安全', sceneTags: ['机械加工'], displayLevels: ['行业标准']}),
  ];
  assert.deepEqual(searchHazards(rows, '', {category: '电气安全', sceneTag: '电气与配电', displayLevel: '国家标准'}).map(x => x.id), ['H_ELEC']);
  assert.deepEqual(searchHazards(rows, '', {sceneTag: '__unclassified__'}).map(x => x.id), ['H_UNCLASSIFIED']);
  assert.deepEqual(searchHazards(rows, '', {category: '机械与设备安全'}).map(x => x.id), ['H_OTHER']);
});

test('稳定编号展示覆盖后的主题筛选仍可召回，且不把原始主题当展示主题', () => {
  const corrected = hazardRow({
    id: 'H_133DEA3AE07CE30E3CA5CBF4FF_1',
    category: '设备设施',
    displayCategory: '安全管理',
    searchText: '设备设施 安全管理 现场管理',
  });
  assert.deepEqual(searchHazards([corrected], '', {category: '安全管理'}).map(x => x.id), [corrected.id]);
  assert.equal(searchHazards([corrected], '', {category: '设备设施'}).length, 0);
});

test('直接适用的英文枚举仍参与排序加分，旧中文值也兼容', () => {
  const direct = hazardRow({id: 'H_DIRECT', mode: 'direct', title: '安全问题', searchText: '安全问题'});
  const conditional = hazardRow({id: 'H_CONDITIONAL', mode: 'conditional', title: '安全问题', searchText: '安全问题'});
  assert.equal(searchHazards([conditional, direct], '安全', {}).at(0).id, 'H_DIRECT');
  assert.equal(searchHazards([hazardRow({mode: '直接适用'})], '', {}).length, 1);
});

test('法规索引优先使用 displayLevel 筛选并兼容旧 level 字段', () => {
  const laws = [
    {id: 'L_A', name: 'A', aliases: [], level: '强制性国家标准', displayLevel: '国家标准', scope: '全国', status: '现行有效', searchText: 'a'},
    {id: 'L_B', name: 'B', aliases: [], level: '行业标准', scope: '全国', status: '现行有效', searchText: 'b'},
  ];
  assert.deepEqual(searchLaws(laws, '', {displayLevel: '国家标准'}).map(x => x.id), ['L_A']);
  assert.deepEqual(searchLaws([{...laws[1]}], '', {level: '行业标准'}).map(x => x.id), ['L_B']);
});

test('安全员只匹配岗位及同义叫法，不匹配安全出口、安全阀或安全帽', () => {
  const titles = ['场车安全员未开展检查', '未配备安全生产管理人员', '安全出口堵塞', '安全阀未检验', '未佩戴安全帽'];
  const rows = titles.map((title, i) => hazardRow({id: String(i), title, searchText: title}));
  assert.deepEqual(new Set(searchHazards(rows, '安全员').map(r => r.id)), new Set(['0', '1']));
  assert.deepEqual(searchHazards(rows, '安全帽').map(r => r.id), ['4']);
  assert.equal(searchHazards(rows.slice(2), '安全员').length, 0);
});

test('完整领域词不使用正文中散落的字片凑匹配', () => {
  const row = hazardRow({searchText: '安全管理 管理人员 人员培训'});
  assert.equal(searchHazards([row], '安全管理人员').length, 0);
});

test('安全员培训同时要求岗位和培训，不放入其他安全培训', () => {
  const rows = ['安全生产管理人员未接受培训', '员工消防安全培训', '场车安全员未开展检查']
    .map((title, i) => hazardRow({id: String(i), title, searchText: title}));
  for (const query of ['安全员培训', '安全员 培训', '安管员培训']) {
    assert.deepEqual(searchHazards(rows, query).map(r => r.id), ['0']);
  }
});

test('错字只纠正到确定的词典词，仍须满足组合查询的每个条件', () => {
  const rows = ['灭火器失压', '灭火器未检查', '加热装置防止火灾']
    .map((title, i) => hazardRow({id: String(i), title, searchText: title}));
  for (const query of ['灭活器失压', '灭活器 失压', '火灭器失压']) {
    assert.deepEqual(searchHazards(rows, query).map(r => r.id), ['0']);
  }
});

test('原词已有结果时不混入纠错结果，筛选后才判断是否需要纠错', () => {
  const rows = [
    hazardRow({id: 'LITERAL', title: '灭活器检查', searchText: '灭活器检查', displayCategory: '其他'}),
    hazardRow({id: 'CORRECTED', title: '灭火器检查', searchText: '灭火器检查', displayCategory: '消防安全'}),
  ];
  assert.deepEqual(searchHazards(rows, '灭活器').map(r => r.id), ['LITERAL']);
  assert.deepEqual(searchHazards(rows, '灭活器', {category: '消防安全'}).map(r => r.id), ['CORRECTED']);
});

test('有歧义的错字不猜测，编号与标准号不允许单字通配', () => {
  const rows = [hazardRow({searchText: '安全员 安全帽 安全阀 gb 55036 2022 h1234'})];
  for (const query of ['安全圆', 'GB 55037 2022', 'H1235']) {
    assert.equal(searchHazards(rows, query).length, 0);
  }
});

test('法规搜索也拒绝安全通配误命中并保留词典纠错', () => {
  const laws = ['安全出口设计规范', '安全管理人员培训要求', '灭火器配置规范']
    .map((name, i) => ({id: String(i), name, aliases: [], level: '国家标准', scope: '全国', status: '现行有效', searchText: name}));
  assert.deepEqual(searchLaws(laws, '安全员').map(r => r.id), ['1']);
  assert.deepEqual(searchLaws(laws, '灭活器').map(r => r.id), ['2']);
});

test('纠错后按纠正词排序，完整设备名优先于正文附带提及', () => {
  const rows = ['其他消防设施检查', '灭火器失压'].map((title, i) =>
    hazardRow({id: String(i), title, searchText: `${title} 灭火器`}));
  assert.deepEqual(searchHazards(rows, '灭活器').map(r => r.id), searchHazards(rows, '灭火器').map(r => r.id));
  assert.equal(searchHazards(rows, '灭活器')[0].id, '1');
});
