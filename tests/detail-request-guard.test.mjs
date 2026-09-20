import test from 'node:test';
import assert from 'node:assert/strict';
import {createDetailRequestGuard} from '../web/app.js';

const deferred = () => {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
  return {promise, resolve, reject};
};

function harness() {
  const state = {
    view: 'hazards',
    selectedHazard: '',
    selectedLaw: '',
    body: 'empty',
    copied: null,
    error: null,
  };
  const guard = createDetailRequestGuard(() => ({
    view: state.view,
    selectedId: state.view === 'hazards' ? state.selectedHazard : state.selectedLaw,
  }));

  const render = (view, id, loader) => {
    state.view = view;
    if (view === 'hazards') state.selectedHazard = id;
    else state.selectedLaw = id;
    const token = guard.begin(view, id);
    state.body = `loading:${view}:${id}`;
    state.copied = null;
    state.error = null;
    return loader().then(result => {
      if (!guard.isCurrent(token)) return false;
      state.body = result.body;
      state.copied = result.copy;
      return true;
    }, error => {
      if (!guard.isCurrent(token)) return false;
      state.body = 'error';
      state.error = error.message;
      return true;
    });
  };

  const clear = () => {
    if (state.view === 'hazards') state.selectedHazard = '';
    else state.selectedLaw = '';
    guard.invalidate();
    state.body = 'empty';
    state.copied = null;
    state.error = null;
  };

  const unavailable = id => {
    if (state.view === 'hazards') state.selectedHazard = id;
    else state.selectedLaw = id;
    guard.invalidate();
    state.body = `unavailable:${id}`;
    state.copied = null;
    state.error = null;
  };

  return {state, guard, render, clear, unavailable};
}

test('A 后返回、B 先返回时正文和复制内容保持 B', async () => {
  const h = harness();
  const a = deferred();
  const b = deferred();
  const renderA = h.render('hazards', 'A', () => a.promise);
  const renderB = h.render('hazards', 'B', () => b.promise);

  b.resolve({body: 'Record B', copy: 'Copy B'});
  assert.equal(await renderB, true);
  a.resolve({body: 'Record A', copy: 'Copy A'});
  assert.equal(await renderA, false);
  assert.equal(h.state.body, 'Record B');
  assert.equal(h.state.copied, 'Copy B');
});

test('跨隐患/法规视图时，旧隐患响应不能覆盖法规详情', async () => {
  const h = harness();
  const hazard = deferred();
  const law = deferred();
  const renderHazard = h.render('hazards', 'H-A', () => hazard.promise);
  const renderLaw = h.render('laws', 'L-B', () => law.promise);

  hazard.resolve({body: 'Hazard A', copy: 'Hazard copy'});
  assert.equal(await renderHazard, false);
  law.resolve({body: 'Law B', copy: 'Law copy'});
  assert.equal(await renderLaw, true);
  assert.equal(h.state.body, 'Law B');
  assert.equal(h.state.copied, 'Law copy');
});

test('切到数据视图时，正在进行的详情请求立即失效', async () => {
  const h = harness();
  const old = deferred();
  const renderOld = h.render('hazards', 'H-A', () => old.promise);
  h.state.view = 'data';
  h.guard.invalidate();
  h.state.body = 'data-view';
  old.resolve({body: 'Hazard A', copy: 'Hazard copy'});
  assert.equal(await renderOld, false);
  assert.equal(h.state.body, 'data-view');
});

test('清空结果或选中无效链接后，旧响应不能重新填入详情', async () => {
  const h = harness();
  const old = deferred();
  const renderOld = h.render('hazards', 'H-OLD', () => old.promise);
  h.clear();
  old.resolve({body: 'Old detail', copy: 'Old copy'});
  assert.equal(await renderOld, false);
  assert.equal(h.state.body, 'empty');

  const invalidated = deferred();
  const renderInvalidated = h.render('hazards', 'H-OLD-2', () => invalidated.promise);
  h.unavailable('H-MISSING');
  invalidated.resolve({body: 'Old detail 2', copy: 'Old copy 2'});
  assert.equal(await renderInvalidated, false);
  assert.equal(h.state.body, 'unavailable:H-MISSING');
});

test('旧请求失败不能覆盖新请求成功', async () => {
  const h = harness();
  const old = deferred();
  const current = deferred();
  const renderOld = h.render('hazards', 'A', () => old.promise);
  const renderCurrent = h.render('hazards', 'B', () => current.promise);

  current.resolve({body: 'Record B', copy: 'Copy B'});
  assert.equal(await renderCurrent, true);
  old.reject(new Error('旧请求失败'));
  assert.equal(await renderOld, false);
  assert.equal(h.state.body, 'Record B');
  assert.equal(h.state.error, null);
});

test('同一条目 A → B → A 的交错响应仍由最新序号决定', async () => {
  const h = harness();
  const firstA = deferred();
  const b = deferred();
  const secondA = deferred();
  const renderFirstA = h.render('hazards', 'A', () => firstA.promise);
  const renderB = h.render('hazards', 'B', () => b.promise);
  const renderSecondA = h.render('hazards', 'A', () => secondA.promise);

  b.resolve({body: 'Record B', copy: 'Copy B'});
  assert.equal(await renderB, false);
  firstA.resolve({body: 'Record A old', copy: 'Copy A old'});
  assert.equal(await renderFirstA, false);
  secondA.resolve({body: 'Record A latest', copy: 'Copy A latest'});
  assert.equal(await renderSecondA, true);
  assert.equal(h.state.body, 'Record A latest');
  assert.equal(h.state.copied, 'Copy A latest');
});

test('当前有效请求正常成功或失败时仍更新正文/错误状态', async () => {
  const success = harness();
  const ok = deferred();
  const renderOk = success.render('laws', 'L-OK', () => ok.promise);
  ok.resolve({body: 'Law OK', copy: 'Law copy'});
  assert.equal(await renderOk, true);
  assert.equal(success.state.body, 'Law OK');
  assert.equal(success.state.copied, 'Law copy');

  const failure = harness();
  const bad = deferred();
  const renderBad = failure.render('hazards', 'H-BAD', () => bad.promise);
  bad.reject(new Error('当前请求失败'));
  assert.equal(await renderBad, true);
  assert.equal(failure.state.body, 'error');
  assert.equal(failure.state.error, '当前请求失败');
});
