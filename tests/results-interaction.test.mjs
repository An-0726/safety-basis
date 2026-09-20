import fs from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import assert from 'node:assert/strict';
import {searchHazards, searchLaws} from '../web/js/search.js';

const APP_SOURCE = fs.readFileSync(new URL('../web/app.js', import.meta.url), 'utf8')
  .replace(/\r\n/g, '\n');

class FakeElement {
  constructor(id = '') {
    this.id = id;
    this.value = '';
    this.textContent = '';
    this.hidden = false;
    this.scrollTop = 0;
    this.onclick = null;
    this.className = '';
    this.dataset = {};
    this.classList = {toggle() {}, add() {}, remove() {}};
    this.children = new Map();
    this.cards = [];
    this._innerHTML = '';
    this.focused = false;
    this.scrolledIntoView = false;
  }

  set innerHTML(value) {
    this._innerHTML = String(value);
    this.children = new Map();
    this.cards = [];
    for (const match of this._innerHTML.matchAll(/\bid="([^"]+)"/g)) {
      if (!this.children.has(match[1])) this.children.set(match[1], new FakeElement(match[1]));
    }
    for (const match of this._innerHTML.matchAll(/data-id="([^"]+)"[^>]*aria-pressed="([^"]+)"/g)) {
      const card = new FakeElement('card');
      card.dataset.id = match[1];
      card.ariaPressed = match[2];
      this.cards.push(card);
    }
  }

  get innerHTML() { return this._innerHTML; }
  querySelector(selector) {
    if (selector.startsWith('#')) return this.children.get(selector.slice(1)) || null;
    return null;
  }
  querySelectorAll(selector) {
    if (selector === '.card') return this.cards;
    return [];
  }
  focus() { this.focused = true; }
  click() { this.onclick?.(); }
  scrollIntoView() { this.scrolledIntoView = true; }
  addEventListener() {}
  select() {}
  remove() {}
  insertAdjacentHTML(_position, html) { this.innerHTML += String(html); }
}

function loadResultsApp({rowCount = 365, lawCount = 0} = {}) {
  const ids = [
    'detail', 'toast', 'search', 'category', 'scene', 'level', 'region', 'mode',
    'lawLevel', 'lawRegion', 'lawStatus', 'count', 'summary', 'list',
    'hazardFilterCount', 'lawFilterCount', 'searchView', 'dataView',
  ];
  const elements = new Map(ids.map(id => [id, new FakeElement(id)]));
  const document = {
    activeElement: {tagName: 'BODY'},
    querySelector(selector) {
      if (selector.startsWith('#')) {
        const id = selector.slice(1);
        if (id === 'loadMore') return elements.get('list').children.get('loadMore') || null;
        return elements.get(id) || null;
      }
      if (selector === '#detail h2') return null;
      return null;
    },
    querySelectorAll(selector) {
      if (selector === '.card') return elements.get('list').cards;
      return [];
    },
    addEventListener() {},
    createElement(tag) { return new FakeElement(tag); },
  };
  const context = {
    document,
    searchHazards,
    searchLaws,
    DataStore: class {},
    navigator: {clipboard: {writeText: async () => {}}},
    console: {error() {}, log() {}},
    location: {href: 'http://test.invalid/index.html', search: '', pathname: '/index.html', hash: ''},
    history: {replaceState() {}},
    setTimeout() { return 0; },
    clearTimeout() {},
    URLSearchParams,
    URL,
    Blob,
    encodeURIComponent,
  };
  context.window = context;
  let source = APP_SOURCE
    .replace(/^import[^\n]*\n/gm, '')
    .replace(/^export /gm, '')
    .replace("if(typeof document!=='undefined') boot();", '');
  source += '\n globalThis.__testApi={state,renderResults,selectHazard,selectLaw};';
  vm.createContext(context);
  new vm.Script(source, {filename: 'web/app.js'}).runInContext(context);

  const rows = Array.from({length: rowCount}, (_, index) => {
    const id = `H${String(index).padStart(3, '0')}`;
    return {
      id,
      title: `隐患 ${index}`,
      aliases: [],
      keywords: ['隐患'],
      lawNames: [],
      places: ['测试场所'],
      sceneTags: index % 2 ? ['生产现场'] : [],
      levels: ['国家标准'],
      displayLevels: ['国家标准'],
      scopes: ['全国'],
      mode: 'direct',
      status: '已核验',
      category: '电气安全',
      displayCategory: '电气安全',
      searchText: `隐患 ${index}`,
      checked: '2026-09-19',
      shard: 'h0000',
    };
  });
  const lawRows = Array.from({length: lawCount}, (_, index) => ({
    id: `L${String(index).padStart(3, '0')}`,
    name: `法规 ${String(index).padStart(3, '0')}`,
    aliases: [],
    searchText: `法规 ${String(index).padStart(3, '0')}`,
    level: '国家标准',
    displayLevel: '国家标准',
    scope: '全国',
    status: '现行有效',
    clauseCount: 1,
    hazardCount: 1,
    checked: '2026-09-19',
  }));
  context.__testApi.state.store = {
    searchIndex: rows,
    lawIndex: lawRows,
    manifest: {dataVersion: 'test-version'},
    getHazardDetail(index) {
      return Promise.resolve({hazard: {...index, description: '描述', measures: '措施', conditions: '', note: ''}, bases: []});
    },
    getLawDetail(law) {
      return Promise.resolve({law, clauses: []});
    },
  };
  context.__testApi.state.view = 'hazards';
  // Boot state has no selection; initial/view-change behavior must choose it.
  context.__testApi.state.selectedHazard = '';
  elements.get('search').value = '';
  for (const id of ['category', 'scene', 'level', 'region', 'mode', 'lawLevel', 'lawRegion', 'lawStatus']) elements.get(id).value = '';
  return {api: context.__testApi, elements};
}

async function settle() {
  await new Promise(resolve => setImmediate(resolve));
}

test('真实结果列表支持加载更多、深链接展开、选择保持批次和滚动位置', async () => {
  const {api, elements} = loadResultsApp();
  api.renderResults({mode: 'filter-change'});
  await settle();
  const list = elements.get('list');
  assert.equal(api.state.visibleCount, 120);
  assert.equal(list.cards.length, 120);
  assert.doesNotMatch(list.innerHTML, /隐患编号|完整记录ID/);
  assert.ok(list.children.get('loadMore').onclick);

  list.scrollTop = 37;
  api.selectHazard('H010');
  await settle();
  assert.equal(api.state.visibleCount, 120);
  assert.equal(list.scrollTop, 37);
  assert.match(list.innerHTML, /data-id="H010"[^>]*aria-pressed="true"/);

  list.children.get('loadMore').onclick();
  await settle();
  assert.equal(api.state.visibleCount, 240);
  assert.equal(list.cards.length, 240);

  const deepId = api.state.results[180].id;
  api.state.selectedHazard = deepId;
  api.state.visibleCount = 120;
  api.renderResults({mode: 'filter-change'});
  await settle();
  assert.equal(api.state.visibleCount, 120);
  assert.equal(api.state.selectedHazard, api.state.results[0].id);
  assert.match(list.innerHTML, new RegExp(`data-id="${api.state.results[0].id}"[^>]*aria-pressed="true"`));

  api.state.selectedHazard = deepId;
  api.state.visibleCount = 120;
  api.renderResults({mode: 'initial'});
  await settle();
  assert.equal(api.state.visibleCount, 240);
  assert.match(list.innerHTML, new RegExp(`data-id="${deepId}"[^>]*aria-pressed="true"`));
});

test('检索条件变化重置展示批次，空场景选项仍由搜索层处理', async () => {
  const {api, elements} = loadResultsApp();
  api.state.visibleCount = 240;
  elements.get('scene').value = '__unclassified__';
  api.renderResults({mode: 'filter-change'});
  await settle();
  assert.equal(api.state.visibleCount, 120);
  assert.equal(api.state.results.length, 183);
  assert.equal(elements.get('list').cards.length, 120);
});

test('无效隐患深链接仍更新计数、分页和详情提示，并可恢复有效选择', async () => {
  const {api, elements} = loadResultsApp();
  api.state.selectedHazard = 'MISSING-ID';
  api.renderResults({mode: 'initial'});
  await settle();

  const list = elements.get('list');
  assert.equal(elements.get('count').textContent, 365);
  assert.match(elements.get('summary').textContent, /已展示 120 \/ 365/);
  assert.equal(list.cards.length, 120);
  assert.ok(list.children.get('loadMore')?.onclick);
  assert.match(elements.get('detail').innerHTML, /MISSING-ID/);

  list.children.get('loadMore').click();
  await settle();
  assert.match(elements.get('summary').textContent, /已展示 240 \/ 365/);
  assert.ok(list.children.get('loadMore')?.onclick);

  elements.get('scene').value = '__unclassified__';
  api.renderResults({mode: 'filter-change'});
  await settle();
  assert.equal(api.state.results.length, 183);
  assert.equal(api.state.selectedHazard, api.state.results[0].id);
  assert.match(elements.get('summary').textContent, /已展示 120 \/ 183/);
  assert.ok(list.children.get('loadMore')?.onclick);
  list.children.get('loadMore').click();
  await settle();
  assert.match(elements.get('summary').textContent, /已展示 183 \/ 183/);
  assert.equal(list.children.get('loadMore'), undefined);
});

test('无效隐患和法规深链接在零结果时仍保留不可用编号提示', async () => {
  const {api, elements} = loadResultsApp({rowCount: 365, lawCount: 365});
  const noMatch = '__NO_MATCH_20260920__';
  elements.get('search').value = noMatch;

  api.state.selectedHazard = 'MISSING-ID';
  api.renderResults({mode: 'initial'});
  await settle();
  assert.equal(api.state.results.length, 0);
  assert.equal(api.state.selectedHazard, 'MISSING-ID');
  assert.equal(elements.get('count').textContent, 0);
  assert.match(elements.get('detail').innerHTML, /MISSING-ID/);

  api.state.view = 'laws';
  api.state.selectedLaw = 'MISSING-LAW';
  api.renderResults({mode: 'initial'});
  await settle();
  assert.equal(api.state.results.length, 0);
  assert.equal(api.state.selectedLaw, 'MISSING-LAW');
  assert.equal(elements.get('count').textContent, 0);
  assert.match(elements.get('detail').innerHTML, /MISSING-LAW/);
});

test('隐患首批、整批和最后一批边界的计数与加载按钮一致', async () => {
  for (const total of [0, 1, 120, 121, 365]) {
    const {api, elements} = loadResultsApp({rowCount: total});
    api.renderResults({mode: 'filter-change'});
    await settle();
    const list = elements.get('list');
    assert.equal(elements.get('count').textContent, total, `总数 ${total}`);
    assert.equal(list.cards.length, Math.min(120, total), `首批 ${total}`);
    if (total <= 120) {
      assert.equal(list.children.get('loadMore'), undefined, `不应加载更多 ${total}`);
      continue;
    }
    assert.ok(list.children.get('loadMore')?.onclick, `应加载更多 ${total}`);
    while (list.children.get('loadMore')) {
      list.children.get('loadMore').click();
      await settle();
    }
    assert.equal(list.cards.length, total, `末批 ${total}`);
    assert.match(elements.get('summary').textContent, new RegExp(`已展示 ${total} / ${total}`));
  }
});

test('法规视图区分初始化深链接、筛选重置和无效编号', async () => {
  const {api, elements} = loadResultsApp({rowCount: 0, lawCount: 365});
  api.state.view = 'laws';
  api.state.selectedLaw = api.state.store.lawIndex[180].id;
  api.state.visibleCount = 120;
  api.renderResults({mode: 'initial'});
  await settle();
  assert.equal(api.state.visibleCount, 240);
  assert.match(elements.get('list').innerHTML, /L180/);

  api.state.visibleCount = 240;
  api.state.selectedLaw = api.state.store.lawIndex[180].id;
  api.renderResults({mode: 'filter-change'});
  await settle();
  assert.equal(api.state.visibleCount, 120);
  assert.equal(api.state.selectedLaw, api.state.results[0].id);

  api.state.selectedLaw = 'MISSING-LAW';
  api.state.visibleCount = 120;
  api.renderResults({mode: 'initial'});
  await settle();
  assert.equal(elements.get('count').textContent, 365);
  assert.match(elements.get('summary').textContent, /已展示 120 \/ 365/);
  assert.ok(elements.get('list').children.get('loadMore')?.onclick);
  assert.match(elements.get('detail').innerHTML, /MISSING-LAW/);
});

test('空初始选择选中首条隐患并保持列表详情一致', async () => {
  const {api, elements} = loadResultsApp({rowCount: 365});
  const list = elements.get('list');

  api.state.selectedHazard = '';
  api.state.visibleCount = 120;
  api.renderResults({mode: 'initial'});
  await settle();
  assert.equal(api.state.selectedHazard, api.state.results[0].id);
  assert.match(list.innerHTML, new RegExp(`data-id="${api.state.results[0].id}"[^>]*aria-pressed="true"`));
});

test('视图切换始终重置为首条隐患并保持列表详情一致', async () => {
  const {api, elements} = loadResultsApp({rowCount: 365});
  const list = elements.get('list');
  api.state.selectedHazard = api.state.store.searchIndex[180].id;
  api.state.visibleCount = 120;
  api.renderResults({mode: 'view-change'});
  await settle();
  assert.equal(api.state.visibleCount, 120);
  assert.equal(api.state.selectedHazard, api.state.results[0].id);
  assert.match(list.innerHTML, new RegExp(`data-id="${api.state.results[0].id}"[^>]*aria-pressed="true"`));
  assert.doesNotMatch(list.innerHTML, new RegExp(`data-id="${api.state.results[180].id}"`));
});

test('空初始选择选中首条法规并保持列表详情一致', async () => {
  const {api, elements} = loadResultsApp({rowCount: 0, lawCount: 365});
  const list = elements.get('list');
  api.state.view = 'laws';

  api.state.selectedLaw = '';
  api.state.visibleCount = 120;
  api.renderResults({mode: 'initial'});
  await settle();
  assert.equal(api.state.selectedLaw, api.state.results[0].id);
  assert.match(list.innerHTML, new RegExp(`data-id="${api.state.results[0].id}"[^>]*aria-pressed="true"`));
});

test('法规视图切换始终重置为首条并保持列表详情一致', async () => {
  const {api, elements} = loadResultsApp({rowCount: 0, lawCount: 365});
  const list = elements.get('list');
  api.state.view = 'laws';
  api.state.selectedLaw = api.state.store.lawIndex[180].id;
  api.state.visibleCount = 120;
  api.renderResults({mode: 'view-change'});
  await settle();
  assert.equal(api.state.visibleCount, 120);
  assert.equal(api.state.selectedLaw, api.state.results[0].id);
  assert.match(list.innerHTML, new RegExp(`data-id="${api.state.results[0].id}"[^>]*aria-pressed="true"`));
  assert.doesNotMatch(list.innerHTML, new RegExp(`data-id="${api.state.results[180].id}"`));
});
