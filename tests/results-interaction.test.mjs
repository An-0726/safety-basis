import fs from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import assert from 'node:assert/strict';
import {searchHazardsDetailed, searchLawsDetailed} from '../web/js/search.js';

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
    this.filterButtons = [];
    this.options = [{value: '', textContent: ''}];
    this.open = false;
    this._innerHTML = '';
    this.focused = false;
    this.scrolledIntoView = false;
  }

  set innerHTML(value) {
    this._innerHTML = String(value);
    this.children = new Map();
    this.cards = [];
    this.filterButtons = [];
    this.options = [...this._innerHTML.matchAll(/<option value="([^"]*)"[^>]*>([^<]*)<\/option>/g)].map(match=>({value:match[1],textContent:match[2]}));
    for(const match of this._innerHTML.matchAll(/data-filter="([^"]+)"/g)){
      const button=new FakeElement('chip');button.dataset.filter=match[1];this.filterButtons.push(button);
    }
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
  get selectedOptions() { return this.options.filter(option=>option.value===this.value); }
  querySelector(selector) {
    if (selector.startsWith('#')) return this.children.get(selector.slice(1)) || null;
    return null;
  }
  querySelectorAll(selector) {
    if (selector === '.card') return this.cards;
    if (selector === 'button[data-filter]') return this.filterButtons;
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
    'activeFilters', 'searchNotice', 'hazardMoreFilters', 'lawMoreFilters', 'majorTopicNotice',
    'clear', 'reset', 'resetLaw', 'hazardFilters', 'lawFilters', 'sectionTitle', 'sectionHint',
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
      if(selector === '#hazardFilters select,#lawFilters select')return ['category','scene','level','region','mode','lawLevel','lawRegion','lawStatus'].map(id=>elements.get(id));
      return [];
    },
    addEventListener() {},
    createElement(tag) { return new FakeElement(tag); },
  };
  const context = {
    document,
    searchHazardsDetailed,
    searchLawsDetailed,
    DataStore: class {},
    navigator: {clipboard: {writeText: async () => {}}},
    console: {error() {}, log() {}},
    location: {href: 'http://test.invalid/index.html', search: '', pathname: '/index.html', hash: ''},
    history: {replaceState() {}, pushState() {}},
    setTimeout() { return 0; },
    clearTimeout() {},
    URLSearchParams,
    URL,
    Blob,
    encodeURIComponent,
    addEventListener() {},
  };
  context.window = context;
  let source = APP_SOURCE
    .replace(/^import[^\n]*\n/gm, '')
    .replace(/^export /gm, '')
    .replace("if(typeof document!=='undefined') boot();", '');
  source += '\n globalThis.__testApi={state,renderResults,selectHazard,selectLaw,bind,initFilters,applyUrlFilters,basisHtml,hazardText,hazardFullText};';
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
    taxonomy:{displayCategories:['电气安全'],displayLevels:['国家标准'],sceneTagOptions:['生产现场','不存在的现场','未细分场景'],hazardModes:['direct','conditional'],lawStatuses:['现行有效']},
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


test('只有专业分类和地区常显，现场标签及其他条件渐进展示',()=>{
  const html=fs.readFileSync(new URL('../web/index.html',import.meta.url),'utf8');
  const filters=html.slice(html.indexOf('id="hazardFilters"'),html.indexOf('id="lawFilters"'));
  const primary=filters.slice(0,filters.indexOf('<details'));
  assert.match(primary,/专业分类/);assert.match(primary,/id="region"/);
  assert.doesNotMatch(primary,/id="scene"|id="level"|id="mode"|适用场景/);
  assert.match(filters,/<details[^>]+>[\s\S]*id="scene"[\s\S]*id="level"[\s\S]*id="mode"/);
  assert.match(html,/id="search"[^>]+aria-describedby="searchHelp"/);
  assert.match(html,/id="scene"[^>]+aria-describedby="sceneHelp"/);
});

test('现场选项只显示真实结果中的标签，无泛主题或空选项',()=>{
  const {api,elements}=loadResultsApp();api.initFilters();
  assert.match(elements.get('scene').innerHTML,/生产现场/);
  assert.match(elements.get('scene').innerHTML,/未标注具体现场/);
  assert.doesNotMatch(elements.get('scene').innerHTML,/不存在的现场|适用：/);
});

test('隐藏筛选计数与可移除条件同步，移除不清空用户查询',async()=>{
  const {api,elements}=loadResultsApp();api.initFilters();
  elements.get('search').value='隐患';elements.get('scene').value='生产现场';
  elements.get('level').value='国家标准';
  api.renderResults({mode:'filter-change'});await settle();
  assert.equal(elements.get('hazardFilterCount').textContent,'（2）');
  assert.match(elements.get('activeFilters').innerHTML,/现场标签：生产现场/);
  const chip=elements.get('activeFilters').filterButtons.find(button=>button.dataset.filter==='scene');
  chip.click();await settle();
  assert.equal(elements.get('scene').value,'');assert.equal(elements.get('search').value,'隐患');
  assert.equal(elements.get('level').value,'国家标准');
  assert.equal(elements.get('hazardFilterCount').textContent,'（1）');
  assert.equal(elements.get('scene').focused,true);
});

test('共享链接高级条件自动展开，已删除旧标签明确提示未恢复',async()=>{
  const {api,elements}=loadResultsApp();api.initFilters();
  api.applyUrlFilters({view:'hazards',filters:{scene:'生产现场',level:'国家标准'}});
  assert.equal(elements.get('hazardMoreFilters').open,true);
  api.renderResults({mode:'initial'});await settle();
  assert.equal(elements.get('hazardFilterCount').textContent,'（2）');
  api.applyUrlFilters({view:'hazards',filters:{scene:'电气与配电'}});
  api.renderResults({mode:'initial'});await settle();
  assert.match(elements.get('searchNotice').textContent,/电气与配电.*已不再提供/);
  assert.equal(elements.get('searchNotice').hidden,false);
  elements.get('scene').value='生产现场';api.renderResults({mode:'filter-change'});await settle();
  assert.equal(elements.get('searchNotice').hidden,true);
});

test('清空仅清查询，全部重置清查询和条件，仍恢复首条与列表',async()=>{
  const {api,elements}=loadResultsApp();api.initFilters();api.bind();
  elements.get('search').value='隐患';elements.get('category').value='电气安全';
  elements.get('scene').value='生产现场';api.renderResults({mode:'filter-change'});await settle();
  elements.get('clear').click();await settle();
  assert.equal(elements.get('search').value,'');assert.equal(elements.get('scene').value,'生产现场');
  assert.equal(elements.get('category').value,'电气安全');assert.equal(elements.get('search').focused,true);
  elements.get('reset').click();await settle();
  assert.equal(elements.get('category').value,'');assert.equal(elements.get('scene').value,'');
  assert.equal(elements.get('activeFilters').hidden,true);
  assert.equal(api.state.results.length,365);assert.equal(api.state.selectedHazard,api.state.results[0].id);
});

test('重大隐患查询别名显示解释但保留用户输入，清空后提示消失',async()=>{
  const {api,elements}=loadResultsApp({rowCount:1});api.initFilters();api.bind();
  Object.assign(api.state.store.searchIndex[0],{title:'重大事故隐患判定条件',searchText:'重大事故隐患 判定条件'});
  elements.get('search').value='重大隐患';api.renderResults({mode:'filter-change'});await settle();
  assert.equal(api.state.results.length,1);
  assert.equal(elements.get('search').value,'重大隐患');
  assert.match(elements.get('searchNotice').textContent,/按检索别名.*重大事故隐患.*不代表现场已构成/);
  assert.equal(elements.get('searchNotice').hidden,false);
  elements.get('clear').click();await settle();
  assert.equal(elements.get('searchNotice').hidden,true);
});

test('旧重大分类URL保留窄结果并提示专题，移除chip及历史恢复不扩大或循环',async()=>{
  const {api,elements}=loadResultsApp({rowCount:3});
  const legacy='重大事故隐患判定';
  api.state.store.taxonomy.displayCategories.push(legacy);
  Object.assign(api.state.store.searchIndex[0],{category:legacy,displayCategory:legacy});
  api.initFilters();
  const options=elements.get('category').innerHTML;
  assert.match(options,/<option value="重大事故隐患判定" hidden disabled>/);
  assert.doesNotMatch(options,/<option value="重大事故隐患判定">/);
  const restore=()=>{api.applyUrlFilters({view:'hazards',filters:{category:legacy}});api.renderResults({mode:'initial'});};
  restore();await settle();
  assert.equal(api.state.results.length,1);assert.equal(elements.get('majorTopicNotice').hidden,false);
  elements.get('activeFilters').filterButtons.find(button=>button.dataset.filter==='category').click();await settle();
  assert.equal(elements.get('category').value,'');assert.equal(api.state.results.length,3);
  assert.equal(elements.get('majorTopicNotice').hidden,true);
  restore();await settle();
  assert.equal(api.state.results.length,1);assert.equal(elements.get('category').value,legacy);
  assert.equal(elements.get('majorTopicNotice').hidden,false);
  api.applyUrlFilters({view:'hazards',filters:{category:'电气安全'}});api.renderResults({mode:'initial'});await settle();
  assert.equal(api.state.results.length,2);assert.equal(elements.get('majorTopicNotice').hidden,true);
});

test('旧分类提示与主导航都提供明确专题入口，不把专业记录批量改类',()=>{
  const html=fs.readFileSync(new URL('../web/index.html',import.meta.url),'utf8');
  assert.match(html,/id="majorTopicNotice"[^>]+hidden/);
  assert.match(html,/此筛选仅保留旧分类中的记录/);
  assert.ok((html.match(/href="major-criteria\.html"/g)||[]).length>=2);
});

test('每条K的依据适用范围独立显示并随两种复制输出保留，不从H宽条件推断',()=>{
  const {api}=loadResultsApp({rowCount:1});
  const h={title:'锂电池测试隐患',description:'测试描述',conditions:'仓库通用宽条件',measures:'测试整改',note:'',status:'已核验',checked:'2026-10-01'};
  const common={clause:{article:'第八条',quote:'第一项……第七项……',checked:'2026-10-01'},law:{id:'L019',name:'测试判定标准',level:'部门规章',scope:'全国',status:'现行有效'},sourceUrl:'https://example.org/standard'};
  const narrow={...common,ref:{role:'direct',linkId:'K_NARROW',applicability:'仅限轻工企业第八条第（七）项，不含其余列项'}};
  const other={...common,ref:{role:'direct',linkId:'K_OTHER',applicability:'另一K独立限制 <不得扩大>'}};
  const html=api.basisHtml(narrow),otherHtml=api.basisHtml(other);
  assert.match(html,/本条依据适用范围.*仅限轻工企业第八条第（七）项/);
  assert.doesNotMatch(html,/仓库通用宽条件|另一K独立限制/);
  assert.match(otherHtml,/另一K独立限制 &lt;不得扩大&gt;/);
  for(const text of [api.hazardText(h,[narrow,other]),api.hazardFullText(h,[narrow,other])]){
    assert.equal((text.match(/本条依据适用范围：/g)||[]).length,2);
    assert.match(text,/仅限轻工企业第八条第（七）项/);assert.match(text,/另一K独立限制/);
  }
  assert.doesNotMatch(api.basisHtml({...common,ref:{role:'direct'}}),/本条依据适用范围/);
});


test('逐K复制保留范围首尾空白和换行，不因展示判空改变原值',()=>{
  const {api}=loadResultsApp({rowCount:1});
  const scope='  仅限轻工企业\n第八条第（七）项  ';
  const h={title:'测试',description:'描述',measures:'整改',conditions:'',note:'',status:'已核验',checked:'2026-10-01'};
  const basis={ref:{role:'direct',linkId:'K_SCOPE',applicability:scope},clause:{article:'第八条',quote:'正文',checked:'2026-10-01'},law:{id:'L019',name:'测试标准',level:'部门规章',scope:'全国',status:'现行有效'},sourceUrl:'https://example.org/standard'};
  for(const value of [api.hazardText(h,[basis]),api.hazardFullText(h,[basis])])assert.ok(value.includes('本条依据适用范围：'+scope+'\n正文'));
  assert.ok(api.basisHtml(basis).includes(scope));
});
