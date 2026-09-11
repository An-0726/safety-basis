import test from 'node:test';
import assert from 'node:assert/strict';
import { searchHazards, searchLaws, normalize } from '../js/search.js';

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
