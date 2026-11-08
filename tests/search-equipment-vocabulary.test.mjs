import test from 'node:test';
import assert from 'node:assert/strict';
import {searchHazardsDetailed} from '../web/js/search.js';

// Synthetic headings exercise retrieval vocabulary, not legal applicability.
const row = (id, title) => ({
  id, title, aliases: [], keywords: [], lawNames: [], stdNumbers: [], places: [],
  levels: [], scopes: ['全国'], category: '综合安全', mode: 'direct', status: '已核验',
  searchText: title.toLowerCase(),
});
const ids = (rows, query) => searchHazardsDetailed(rows, query).rows.map(value => value.id);

test('正式装置名和现场设备名可以互查，不需要整句问法映射', () => {
  const rows = [
    row('rcd', '电动工具回路未安装漏电保护器'),
    row('strip', '插排超负荷使用'),
    row('argon', '氩气钢瓶放置不稳'),
  ];
  for (const [query, expected] of [
    ['剩余电流动作保护装置', 'rcd'], ['移动式插座', 'strip'], ['氩气瓶', 'argon'],
  ]) assert.deepEqual(ids(rows, query), [expected], query);
});

test('喷头与点型烟感分别召回，不能由于同属消防设备而交换对象', () => {
  const rows = [row('sprinkler', '洒水喷头被遮挡'), row('smoke', '点型感烟探测器被遮挡')];
  assert.deepEqual(ids(rows, '喷淋头遮挡'), ['sprinkler']);
  assert.deepEqual(ids(rows, '点型烟感遮挡'), ['smoke']);
});

test('显式检验、校验、检定不通过口语退路互换', () => {
  const inspection = row('inspection', '安全附件未检验');
  const calibration = row('calibration', '安全附件未校验');
  const verification = row('verification', '安全附件未检定');
  assert.deepEqual(ids([calibration, verification], '安全附件未检验'), []);
  assert.deepEqual(ids([inspection, verification], '安全附件未校验'), []);
  assert.deepEqual(ids([inspection, calibration], '安全附件未检定'), []);
  assert.deepEqual(ids([row('overdue', '安全附件超过校验周期')], '安全附件校验过期'), ['overdue']);
});

test('立放状态可定位气瓶条目，但缺少链条不等同缺少所有可靠防倾倒措施', () => {
  const rows = [row('cylinder', '气瓶立放使用时未采取可靠防倾倒措施')];
  assert.deepEqual(ids(rows, '气瓶立着用'), ['cylinder']);
  assert.deepEqual(ids(rows, '气瓶没有链条'), []);
});
