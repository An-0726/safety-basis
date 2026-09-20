import fs from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import assert from 'node:assert/strict';

const APP_PATH = new URL('../web/app.js', import.meta.url);
const APP_SOURCE = fs.readFileSync(APP_PATH, 'utf8').replace(/\r\n/g, '\n');

const deferred = () => {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
  return {promise, resolve, reject};
};

class FakeElement {
  constructor(id = '') {
    this.id = id;
    this.onclick = null;
    this.listeners = new Map();
    this.classList = {add() {}, remove() {}};
    this.children = new Map();
    this._innerHTML = '';
  }

  set innerHTML(value) {
    this._innerHTML = String(value);
    this.children = new Map();
    for (const match of this._innerHTML.matchAll(/\bid="([^"]+)"/g)) {
      if (!this.children.has(match[1])) this.children.set(match[1], new FakeElement(match[1]));
    }
  }

  get innerHTML() { return this._innerHTML; }

  querySelector(selector) {
    if (selector.startsWith('#')) return this.children.get(selector.slice(1)) || null;
    if (selector === '.lawmeta') return this.children.get('lawmeta') || new FakeElement('lawmeta');
    return null;
  }

  insertAdjacentHTML(_position, html) { this._innerHTML += String(html); }
  addEventListener(name, handler) { this.listeners.set(name, handler); }
  select() {}
  remove() {}
}

function loadApp({removeHazardErrorGuard = false} = {}) {
  const detail = new FakeElement('detail');
  const toast = new FakeElement('toast');
  const dbVersion = new FakeElement('dbVersion');
  const dbDate = new FakeElement('dbDate');
  const clipboardWrites = [];
  const document = {
    querySelector(selector) {
      if (selector === '#detail') return detail;
      if (selector === '#toast') return toast;
      if (selector === '#dbVersion') return dbVersion;
      if (selector === '#dbDate') return dbDate;
      if (selector.startsWith('#detail ')) return detail.querySelector(selector.slice('#detail '.length));
      if (selector.startsWith('#')) return detail.querySelector(selector);
      return null;
    },
    querySelectorAll() { return []; },
    addEventListener() {},
    createElement(tag) { return new FakeElement(tag); },
  };

  const context = {
    document,
    navigator: {clipboard: {writeText: async value => { clipboardWrites.push(String(value)); }}},
    console: {error() {}, log() {}},
    location: {href: 'http://test.invalid/index.html'},
    history: {replaceState() {}},
    setTimeout() { return 0; },
    clearTimeout() {},
    URLSearchParams,
    encodeURIComponent,
  };
  context.window = context;

  let source = APP_SOURCE
    .replace(/^import[^\n]*\n/gm, '')
    .replace(/^export /gm, '')
    .replace("if(typeof document!=='undefined') boot();", '');

  if (removeHazardErrorGuard) {
    const guardLine = "  }catch(err){if(detailRequests.isCurrent(request)) showError(err)}";
    assert.ok(source.includes(guardLine), '突变哨兵未找到隐患详情失败保护线');
    source = source.replace(guardLine, '  }catch(err){showError(err)}');
  }
  source += '\n globalThis.__testApi={state,dataDateOf,setDataDateHeader,renderHazardDetail,renderLawDetail,renderUnavailable};';

  vm.createContext(context);
  new vm.Script(source, {filename: 'web/app.js'}).runInContext(context);

  const api = context.__testApi;
  const hazardQueues = new Map();
  const lawQueues = new Map();
  const store = {
    searchIndex: [],
    lawIndex: [],
    manifest: {dataVersion: 'vm-test-version', generatedAt: '2026-09-19T00:00:00+08:00'},
    getHazardDetail(index) {
      const queue = hazardQueues.get(index.id) || [];
      const pending = queue.shift();
      if (!pending) throw new Error(`缺少隐患受控 Promise：${index.id}`);
      return pending.deferred.promise.then(() => pending.detail);
    },
    getLawDetail(law) {
      const queue = lawQueues.get(law.id) || [];
      const pending = queue.shift();
      if (!pending) throw new Error(`缺少法规受控 Promise：${law.id}`);
      return pending.deferred.promise.then(() => pending.detail);
    },
  };
  api.state.store = store;

  const addQueue = (map, id, detailValue) => {
    const pending = {deferred: deferred(), detail: detailValue};
    const queue = map.get(id) || [];
    queue.push(pending);
    map.set(id, queue);
    return pending;
  };
  const queueHazard = (id, title, {conditions = '', note = '', businessNote, maintenanceNote, noteSegments, checked = '2026-09-19', omitConditions = false, omitNote = false, bases = []} = {}) => {
    if (!store.searchIndex.some(row => row.id === id)) store.searchIndex.push({id});
    const hazard = {
      id,
      title,
      category: '电气安全',
      status: '已核验',
      mode: 'direct',
      places: ['测试场所'],
      checked,
      description: '描述 ' + title,
      measures: '措施 ' + title,
      conditions,
      note,
    };
    if (businessNote !== undefined) hazard.businessNote = businessNote;
    if (maintenanceNote !== undefined) hazard.maintenanceNote = maintenanceNote;
    if (noteSegments !== undefined) hazard.noteSegments = noteSegments;
    if (omitConditions) delete hazard.conditions;
    if (omitNote) delete hazard.note;
    return addQueue(hazardQueues, id, {hazard, bases});
  };
  const queueLaw = (id, name) => {
    const law = {
      id,
      name,
      level: '法律',
      status: '现行有效',
      scope: '全国',
      checked: '2026-09-19',
      effectiveDate: '2026-01-01',
      clauseCount: 0,
      hazardCount: 0,
      sourceUrl: '',
    };
    if (!store.lawIndex.some(row => row.id === id)) store.lawIndex.push(law);
    return addQueue(lawQueues, id, {law, clauses: []});
  };

  return {
    api,
    document,
    header: {dbVersion, dbDate},
    clipboardWrites,
    queueHazard,
    queueLaw,
    selectHazard(id) {
      api.state.view = 'hazards';
      api.state.selectedHazard = id;
    },
    selectLaw(id) {
      api.state.view = 'laws';
      api.state.selectedLaw = id;
    },
  };
}

const detailHtml = harness => harness.document.querySelector('#detail').innerHTML;

test('页头数据日期优先使用明确 asOf，旧包缺失时清晰回退', () => {
  const harness = loadApp();
  harness.api.setDataDateHeader(
    {asOf: '2026-09-18', generatedAt: '2026-09-20T01:00:00+08:00'},
    {asOf: '2026-09-19'},
  );
  assert.equal(harness.header.dbVersion.textContent, '数据日期 2026-09-19');
  assert.equal(harness.header.dbDate.textContent, '2026-09-19');
  assert.doesNotMatch(harness.header.dbVersion.textContent, /数据库版本|dataVersion|stage/);

  harness.api.setDataDateHeader({generatedAt: '2026-09-20T01:00:00+08:00'}, {});
  assert.equal(harness.header.dbVersion.textContent, '数据日期 2026-09-20');
  harness.api.setDataDateHeader({}, {});
  assert.equal(harness.header.dbVersion.textContent, '数据日期 未提供');
});

async function clickCopy(harness, id) {
  const button = harness.document.querySelector(`#${id}`);
  assert.ok(button, `未渲染复制按钮：${id}`);
  assert.equal(typeof button.onclick, 'function', `复制按钮未绑定 onclick：${id}`);
  await button.onclick();
  return harness.clipboardWrites.at(-1);
}

async function runHazardABRace(harness) {
  const a = harness.queueHazard('H-A', 'Record A');
  const b = harness.queueHazard('H-B', 'Record B');
  harness.selectHazard('H-A');
  const renderA = harness.api.renderHazardDetail();
  harness.selectHazard('H-B');
  const renderB = harness.api.renderHazardDetail();

  b.deferred.resolve();
  await renderB;
  assert.match(detailHtml(harness), /Record B/);
  assert.match(await clickCopy(harness, 'copy'), /Record B/);

  a.deferred.resolve();
  await renderA;
  assert.match(detailHtml(harness), /Record B/);
  assert.match(await clickCopy(harness, 'copy'), /Record B/);
}

async function runHazardOldFailureRace(harness) {
  const old = harness.queueHazard('H-OLD', 'Old record');
  const current = harness.queueHazard('H-CURRENT', 'Current record');
  harness.selectHazard('H-OLD');
  const renderOld = harness.api.renderHazardDetail();
  harness.selectHazard('H-CURRENT');
  const renderCurrent = harness.api.renderHazardDetail();

  current.deferred.resolve();
  await renderCurrent;
  assert.match(await clickCopy(harness, 'copy'), /Current record/);
  old.deferred.reject(new Error('旧请求失败'));
  await renderOld;
  assert.match(detailHtml(harness), /Current record/);
}

test('真实隐患渲染接线保护 A/B 乱序，并保留真实复制按钮内容', async () => {
  await runHazardABRace(loadApp());
});

test('真实隐患→法规切视图时，旧隐患不能覆盖法规正文或复制内容', async () => {
  const harness = loadApp();
  const oldHazard = harness.queueHazard('H-A', 'Hazard A');
  const currentLaw = harness.queueLaw('L-B', 'Law B');

  harness.selectHazard('H-A');
  const renderHazard = harness.api.renderHazardDetail();
  harness.selectLaw('L-B');
  const renderLaw = harness.api.renderLawDetail();

  currentLaw.deferred.resolve();
  await renderLaw;
  assert.match(detailHtml(harness), /Law B/);
  assert.match(await clickCopy(harness, 'copylaw'), /Law B/);
  oldHazard.deferred.resolve();
  await renderHazard;
  assert.match(detailHtml(harness), /Law B/);
  assert.match(await clickCopy(harness, 'copylaw'), /Law B/);
});

test('真实法规→隐患切视图时，旧法规不能覆盖隐患正文或复制内容', async () => {
  const harness = loadApp();
  const oldLaw = harness.queueLaw('L-A', 'Law A');
  const currentHazard = harness.queueHazard('H-B', 'Hazard B');

  harness.selectLaw('L-A');
  const renderLaw = harness.api.renderLawDetail();
  harness.selectHazard('H-B');
  const renderHazard = harness.api.renderHazardDetail();

  currentHazard.deferred.resolve();
  await renderHazard;
  assert.match(detailHtml(harness), /Hazard B/);
  assert.match(await clickCopy(harness, 'copy'), /Hazard B/);
  oldLaw.deferred.resolve();
  await renderLaw;
  assert.match(detailHtml(harness), /Hazard B/);
  assert.match(await clickCopy(harness, 'copy'), /Hazard B/);
});

test('真实渲染区分适用条件和补充说明，并在两类复制中保持各自内容', async () => {
  const harness = loadApp();
  const pending = harness.queueHazard('H-COND', '条件记录', {
    conditions: '仅在 <特定> 场景 & 设备\n第二行条件',
    note: '补充 <限制> & 备注',
  });
  harness.selectHazard('H-COND');
  const render = harness.api.renderHazardDetail();
  pending.deferred.resolve();
  await render;

  const html = detailHtml(harness);
  assert.match(html, /适用条件/);
  assert.match(html, /仅在 &lt;特定&gt; 场景 &amp; 设备/);
  assert.match(html, /补充说明/);
  assert.match(html, /补充 &lt;限制&gt; &amp; 备注/);
  assert.doesNotMatch(html, /适用说明 \/ 兜底条件/);

  const itemText = await clickCopy(harness, 'copy');
  assert.match(itemText, /适用条件：\n仅在 <特定> 场景 & 设备\n第二行条件/);
  assert.doesNotMatch(itemText, /补充说明/);
  assert.doesNotMatch(itemText, /补充 <限制>/);

  const fullText = await clickCopy(harness, 'copyfull');
  assert.equal((fullText.match(/适用条件：/g) || []).length, 1);
  assert.equal((fullText.match(/补充说明：/g) || []).length, 1);
  assert.match(fullText, /补充说明：\n补充 <限制> & 备注/);
});

test('真实截图候选不显示维护日志，并将历史引用放入默认折叠条目信息', async () => {
  const maintenance = '2026-09-11 修订：原 measures 字段直接照抄隐患描述，已改写为针对该隐患的可执行整改措施。';
  const historical = '原 conditions 字段记录的引用依据为：依据：《化学化工实验室安全管理规范》第10.1.9条';
  const candidates = [
    ['H_4164E28510AC475EA9FB48337C', '高温室缺少当心烫伤'],
    ['H_9AA3291056764D6F82100EA716', '气瓶使用场所缺少当心窒息'],
  ];

  for (const [id, title] of candidates) {
    const harness = loadApp();
    const pending = harness.queueHazard(id, title, {
      note: maintenance + historical,
      businessNote: historical,
      maintenanceNote: maintenance,
      bases: [{
        ref: {role: 'direct', hazardIds: [id]},
        clause: {article: '第10.1.9条', quote: '正式依据原文', checked: '2026-09-19'},
        law: {id: 'L-LAB', name: '化学化工实验室安全管理规范', level: '国家标准', displayLevel: '国家标准', scope: '全国', status: '现行有效'},
        sourceUrl: '',
      }],
    });
    harness.selectHazard(id);
    const render = harness.api.renderHazardDetail();
    pending.deferred.resolve();
    await render;

    const html = detailHtml(harness);
    assert.match(html, /<details class="record-info">/);
    assert.match(html, /历史引用（不替代当前依据）/);
    assert.match(html, /化学化工实验室安全管理规范》第10\.1\.9条/);
    assert.doesNotMatch(html, /维护记录|copyMaintenance|2026-09-11 修订/);
    assert.doesNotMatch(html, /原 conditions 字段记录的引用依据为：/);

    const itemText = await clickCopy(harness, 'copy');
    const fullText = await clickCopy(harness, 'copyfull');
    assert.match(itemText, /正式依据原文/);
    assert.match(fullText, /正式依据原文/);
    assert.match(fullText, /历史引用（不替代当前依据）：/);
    assert.match(fullText, /化学化工实验室安全管理规范》第10\.1\.9条/);
    assert.doesNotMatch(fullText, /原 conditions 字段记录的引用依据为：|2026-09-11 修订|维护记录/);
  }
});

test('补充说明保留业务限制，历史引用和旧包维护分流不改正式条件/依据', async () => {
  const maintenance = '2026-09-11 修订：原 description 与 title 完全相同，已补写为完整描述。';
  const historical = '原 conditions 字段记录的引用依据为：依据：《化学化工实验室安全管理规范》第10.1.9条';
  const business = '仅在气瓶使用场所适用；须结合现场气瓶种类确认。';
  const id = 'H-MIXED-NOTE';
  const harness = loadApp();
  const pending = harness.queueHazard(id, '业务限制与历史引用', {
    conditions: '适用于气瓶使用场所；须结合现场气瓶种类确认具体要求。',
    note: `${maintenance}${business}\n${historical}`,
    businessNote: `${business}\n${historical}`,
    maintenanceNote: maintenance,
    bases: [{
      ref: {role: 'direct', hazardIds: [id]},
      clause: {article: '第10.1.9条', quote: '正式法规原文', checked: '2026-09-19'},
      law: {id: 'L-LAB', name: '化学化工实验室安全管理规范', level: '国家标准', displayLevel: '国家标准', scope: '全国', status: '现行有效'},
      sourceUrl: '',
    }],
  });
  harness.selectHazard(id);
  const render = harness.api.renderHazardDetail();
  pending.deferred.resolve();
  await render;

  const html = detailHtml(harness);
  assert.match(html, /补充说明/);
  assert.match(html, /仅在气瓶使用场所适用；须结合现场气瓶种类确认。/);
  assert.match(html, /适用条件/);
  assert.match(html, /正式法规原文/);
  assert.match(html, /历史引用（不替代当前依据）/);
  assert.doesNotMatch(html, /原 conditions 字段记录的引用依据为：|2026-09-11 修订|维护记录/);

  const fullText = await clickCopy(harness, 'copyfull');
  assert.match(fullText, /适用条件：\n适用于气瓶使用场所；须结合现场气瓶种类确认具体要求。/);
  assert.match(fullText, /补充说明：\n仅在气瓶使用场所适用；须结合现场气瓶种类确认。/);
  assert.match(fullText, /法规依据：\n《化学化工实验室安全管理规范》第10\.1\.9条\n正式法规原文/);
  assert.match(fullText, /历史引用（不替代当前依据）：\n《化学化工实验室安全管理规范》第10\.1\.9条/);
  assert.doesNotMatch(fullText, /原 conditions 字段记录的引用依据为：|2026-09-11 修订/);
});

test('旧包缺少 businessNote 时仅按可靠分段或已知维护文本回退', async () => {
  const maintenance = '2026-09-11 修订：原 description 与 title 完全相同，已补写为完整描述。';
  const historical = '原 conditions 字段记录的引用依据为：依据：《化学化工实验室安全管理规范》第10.1.9条';
  const id = 'H-OLD-PACKAGE';
  const harness = loadApp();
  const note = maintenance + historical;
  const pending = harness.queueHazard(id, '旧包兼容记录', {
    note,
    maintenanceNote: maintenance,
    noteSegments: [
      {kind: 'maintenance', text: maintenance, start: 0, end: maintenance.length},
      {kind: 'business', text: historical, start: maintenance.length, end: note.length},
    ],
  });
  harness.selectHazard(id);
  const render = harness.api.renderHazardDetail();
  pending.deferred.resolve();
  await render;

  const html = detailHtml(harness);
  assert.match(html, /历史引用（不替代当前依据）/);
  assert.doesNotMatch(html, /2026-09-11 修订|原 conditions 字段记录的引用依据为：|维护记录|copyMaintenance/);
  const fullText = await clickCopy(harness, 'copyfull');
  assert.match(fullText, /历史引用（不替代当前依据）：/);
  assert.doesNotMatch(fullText, /2026-09-11 修订|原 conditions 字段记录的引用依据为：/);
});

test('详情副标题只显示数据日期，完整资料和条目信息仍保留版本', async () => {
  const harness = loadApp();
  const pending = harness.queueHazard('H-VERSION', '版本显示记录', {
    note: '业务说明',
    businessNote: '业务说明',
    maintenanceNote: '2026-09-11 修订：原整改措施已改写为可执行动作。',
  });
  harness.selectHazard('H-VERSION');
  const render = harness.api.renderHazardDetail();
  pending.deferred.resolve();
  await render;

  const html = detailHtml(harness);
  assert.match(html, /数据日期 2026-09-19/);
  assert.doesNotMatch(html, /数据库版本/);
  assert.match(html, /数据版本/);
  const fullText = await clickCopy(harness, 'copyfull');
  assert.match(fullText, /数据库版本：vm-test-version/);
  assert.match(fullText, /补充说明：\n业务说明/);
  assert.doesNotMatch(html, /维护记录|copyMaintenance|2026-09-11 修订/);
  assert.doesNotMatch(fullText, /维护记录|2026-09-11 修订/);
});

test('真实渲染兼容缺失、空字符串和 null 条件/备注，且不生成空区块或空复制标题', async () => {
  const cases = [
    {id: 'H-MISSING', options: {omitConditions: true, omitNote: true}},
    {id: 'H-EMPTY', options: {conditions: '', note: ''}},
    {id: 'H-NULL', options: {conditions: null, note: null}},
  ];
  for (const {id, options} of cases) {
    const harness = loadApp();
    const pending = harness.queueHazard(id, id, options);
    harness.selectHazard(id);
    const render = harness.api.renderHazardDetail();
    pending.deferred.resolve();
    await render;

    assert.doesNotMatch(detailHtml(harness), /适用条件|补充说明/);
    assert.doesNotMatch(await clickCopy(harness, 'copy'), /适用条件|补充说明/);
    assert.doesNotMatch(await clickCopy(harness, 'copyfull'), /适用条件|补充说明/);
  }
});

test('真实详情把技术信息折叠到条目信息，并可复制完整编号', async () => {
  const harness = loadApp();
  const pending = harness.queueHazard('H-TECH-INFO', '技术信息记录');
  harness.selectHazard('H-TECH-INFO');
  const render = harness.api.renderHazardDetail();
  pending.deferred.resolve();
  await render;

  const html = detailHtml(harness);
  assert.match(html, /<details class="record-info">/);
  assert.match(html, /条目信息/);
  assert.match(html, /H-TECH-INFO/);
  assert.match(html, /数据版本/);
  assert.match(html, /直接适用/);
  const copiedId = await clickCopy(harness, 'copyRecordId');
  assert.equal(copiedId, 'H-TECH-INFO');
});

test('条目信息折叠保留带时区的完整核验时间', async () => {
  const harness = loadApp();
  const pending = harness.queueHazard('H-TIMESTAMP', '带时间记录', {checked: '2026-09-19T13:14:15+08:00'});
  harness.selectHazard('H-TIMESTAMP');
  const render = harness.api.renderHazardDetail();
  pending.deferred.resolve();
  await render;

  const html = detailHtml(harness);
  assert.match(html, /2026-09-19T13:14:15\+08:00/);
});

test('真实依据渲染分别显示直接依据和辅助依据标签', async () => {
  const harness = loadApp();
  const pending = harness.queueHazard('H-ROLE', '依据角色记录', {
    bases: [
      {ref: {role: 'direct', hazardIds: ['H-ROLE']}, clause: {article: '第一条', quote: '直接原文', checked: '2026-09-19'}, law: {id: 'L-D', name: '直接法规', level: '法律', displayLevel: '法律', scope: '全国', status: '现行有效'}, sourceUrl: ''},
      {ref: {role: 'supporting', hazardIds: ['H-ROLE']}, clause: {article: '第二条', quote: '辅助原文', checked: '2026-09-19'}, law: {id: 'L-S', name: '辅助标准', level: '国家标准', displayLevel: '国家标准', scope: '全国', status: '现行有效'}, sourceUrl: ''},
    ],
  });
  harness.selectHazard('H-ROLE');
  const render = harness.api.renderHazardDetail();
  pending.deferred.resolve();
  await render;
  assert.match(detailHtml(harness), /直接依据/);
  assert.match(detailHtml(harness), /辅助依据/);
});

test('真实渲染中旧失败不能覆盖当前成功，当前有效失败仍显示错误', async () => {
  const harness = loadApp();
  await runHazardOldFailureRace(harness);

  const failing = harness.queueHazard('H-FAIL', 'Failing record');
  harness.selectHazard('H-FAIL');
  const renderFailing = harness.api.renderHazardDetail();
  failing.deferred.reject(new Error('当前请求失败'));
  await renderFailing;
  assert.match(detailHtml(harness), /数据读取失败/);
  assert.match(detailHtml(harness), /当前请求失败/);
});

test('真实渲染中 A→B→A 只接受最后一次 A，并绑定最后一次复制内容', async () => {
  const harness = loadApp();
  const firstA = harness.queueHazard('H-A', 'Record A old');
  const b = harness.queueHazard('H-B', 'Record B');
  const secondA = harness.queueHazard('H-A', 'Record A latest');

  harness.selectHazard('H-A');
  const renderFirstA = harness.api.renderHazardDetail();
  harness.selectHazard('H-B');
  const renderB = harness.api.renderHazardDetail();
  harness.selectHazard('H-A');
  const renderSecondA = harness.api.renderHazardDetail();

  b.deferred.resolve();
  await renderB;
  firstA.deferred.resolve();
  await renderFirstA;
  secondA.deferred.resolve();
  await renderSecondA;
  assert.match(detailHtml(harness), /Record A latest/);
  assert.doesNotMatch(detailHtml(harness), /Record A old/);
  assert.match(await clickCopy(harness, 'copy'), /Record A latest/);
});

test('真实空状态和不可用状态会阻断仍在途的详情响应', async () => {
  const harness = loadApp();
  const old = harness.queueHazard('H-OLD', 'Old record');
  harness.selectHazard('H-OLD');
  const renderOld = harness.api.renderHazardDetail();

  harness.api.state.selectedHazard = '';
  await harness.api.renderHazardDetail();
  assert.match(detailHtml(harness), /选择一个隐患查看详情/);
  old.deferred.resolve();
  await renderOld;
  assert.match(detailHtml(harness), /选择一个隐患查看详情/);

  const oldUnavailable = harness.queueHazard('H-OLD-2', 'Old record 2');
  harness.selectHazard('H-OLD-2');
  const renderOldUnavailable = harness.api.renderHazardDetail();
  harness.api.state.selectedHazard = 'H-MISSING';
  harness.api.renderUnavailable('H-MISSING', '隐患');
  assert.match(detailHtml(harness), /H-MISSING/);
  oldUnavailable.deferred.resolve();
  await renderOldUnavailable;
  assert.match(detailHtml(harness), /H-MISSING/);
});

test('移除内存副本的一处旧失败保护时，对应回归测试会失败', async () => {
  const mutated = loadApp({removeHazardErrorGuard: true});
  await assert.rejects(runHazardOldFailureRace(mutated));
});
