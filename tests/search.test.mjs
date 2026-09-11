import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { searchHazards, searchLaws, normalize } from '../js/search.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const golden = JSON.parse(readFileSync(join(HERE, 'search-golden.json'), 'utf8'));

test(`黄金用例回归（${golden.cases.length} 条，Search 2.0 召回/精确性）`, () => {
  const idx = JSON.parse(readFileSync(join(HERE, '..', 'data', 'search-index.json'), 'utf8'));
  const laws = JSON.parse(readFileSync(join(HERE, '..', 'data', 'law-index.json'), 'utf8'));
  const failures = [];
  for (const c of golden.cases) {
    const hits = c.law ? searchLaws(laws, c.q, {}) : searchHazards(idx, c.q, {});
    if (c.kind === 'miss') {
      if (hits.length !== 0) failures.push(`${c.q} 预期 0 命中，实际 ${hits.length}`);
    } else if (c.top) {
      if (!hits.some(x => x.id === c.top)) failures.push(`${c.q} 预期命中 ${c.top}，实际前 3：${hits.slice(0, 3).map(x => x.id).join(',')}`);
    } else if (hits.length === 0) {
      failures.push(`${c.q} 预期至少 1 条命中，实际 0`);
    }
  }
  assert.deepEqual(failures, []);
});

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
