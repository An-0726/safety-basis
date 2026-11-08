#!/usr/bin/env python3
"""Exercise the real workbench UI against a real, isolated API.

Default: python -m workbench.tests.browser_flow --output /tmp/workbench-ui-qa
Requires Playwright plus an available Chromium. For environments that cannot launch
browsers, --engine dom --dom-module /path/to/jsdom/lib/api.js explicitly runs the
same interaction flow in JSDOM. DOM runs do not claim visual/browser validation.
All fixture data, photographs, exports, and screenshots are synthetic and temporary.
No npm dependencies are required by the delivered application.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]

FLOW = r"""async ({png}) => {
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const checks = [];
  const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
  const check = (condition, label) => { if (!condition) throw Error(label); checks.push(label); };
  async function waitFor(predicate, label, timeout = 20000) {
    const until = Date.now() + timeout;
    while (Date.now() < until) { try { if (await predicate()) return; } catch (error) { if (!error.message.startsWith('Missing button:')) throw error; } await pause(60); }
    const errors = $$('.toast.error').map(element => element.textContent).join(' | ');
    throw Error(`Timeout: ${label}. ${errors}`);
  }
  async function request(url, options = {}) {
    const response = await fetch(url, options);
    if (!response.ok) throw Error(`${url}: ${response.status} ${await response.text()}`);
    return response.json();
  }
  function click(selector, root = document) {
    const element = typeof selector === 'string' ? $(selector, root) : selector;
    if (!element) throw Error(`Missing click target: ${selector}`);
    if (element.disabled) throw Error(`Disabled click target: ${element.textContent}`);
    element.click();
  }
  function textButton(text, root = document) {
    const element = $$('button', root).find(button => button.textContent.trim() === text);
    if (!element) throw Error(`Missing button: ${text}`);
    return element;
  }
  function setValue(selector, value, eventType = 'input') {
    const element = $(selector);
    if (!element || element.disabled || element.closest('fieldset[disabled]')) throw Error(`Cannot edit ${selector}`);
    element.value = value;
    element.dispatchEvent(new Event(eventType, {bubbles: true}));
  }
  function submit(selector) { $(selector).dispatchEvent(new Event('submit', {bubbles: true, cancelable: true})); }
  function selected() { return Object.fromEntries(new URLSearchParams(location.hash.slice(1))); }
  async function finding() { return request(`/api/findings/${selected().finding}`); }
  async function save() {
    document.dispatchEvent(new KeyboardEvent('keydown', {key:'s', ctrlKey:true, bubbles:true, cancelable:true}));
    await waitFor(() => $('.save-status')?.textContent.includes('已保存'), 'UI save completion');
  }
  async function tab(name) {
    click(`[data-tab="${name}"]`);
    await waitFor(() => $(`[data-tab="${name}"]`)?.classList.contains('active'), `tab ${name}`);
    await pause(100);
  }
  await waitFor(() => $('.welcome-card') || $('.page-header'), 'initial application');
  click('#new-project');
  await waitFor(() => $('#project-dialog').open, 'project dialog');
  const runId = Date.now().toString(36);
  const projectName = `自动化脱敏验收-${runId}`;
  const knowledgeMeta = await request('/api/knowledge/meta');
  setValue('#project-form [name="company"]', '合成样例企业（不对应真实企业）');
  setValue('#project-form [name="name"]', projectName);
  setValue('#project-form [name="inspection_date"]', knowledgeMeta.as_of.slice(0,10));
  setValue('#project-form [name="inspectors"]', '测试检查人员');
  setValue('#project-form [name="purpose"]', '仅供功能验收；全部数据与照片为合成样例。');
  submit('#project-form');
  await waitFor(() => !$('#project-dialog').open && selected().project, 'project creation');
  const projectId = selected().project;
  check((await request(`/api/projects/${projectId}`)).name === projectName, 'project created through UI');
  click(textButton('编辑项目'));
  await waitFor(() => $('#project-dialog').open, 'edit project dialog');
  setValue('#project-form [name="inspectors"]', '测试检查人员、复核人员');
  submit('#project-form');
  await waitFor(() => !$('#project-dialog').open && $('.project-meta-row')?.textContent.includes('复核人员'), 'edit project');
  check((await request(`/api/projects/${projectId}`)).inspectors.includes('复核人员'), 'project edits persisted');
  click(textButton('＋ 添加'));
  await waitFor(() => selected().finding && $('[data-field="observation"]'), 'finding creation');
  const originalId = selected().finding;
  setValue('[data-field="location"]', '样例一层包装区东侧');
  setValue('[data-field="equipment"]', '手提式灭火器');
  setValue('[data-field="observation"]', '合成现场：灭火器前方堆放纸箱，模拟阻碍取用。');
  setValue('[data-field="description"]', '样例记录：灭火器取用位置前方存在纸箱堆物，需要核实是否影响取用。');
  setValue('[data-field="rectification"]', '清理取用位置堆物，保持便于取用并复核布置。');
  setValue('[data-field="assignee"]', '样例责任人');
  setValue('[data-field="due_date"]', '2026-11-15');
  setValue('[data-field="notes"]', '<img src=x onerror="window.__unsafe=true"> 此字符串应按普通文字保存');
  setValue('[data-field="finding_kind"]', 'onsite', 'change');
  await save();
  let current = await finding();
  check(current.observation.includes('合成现场') && current.finding_kind === 'onsite', 'record fields saved with finding kind');
  check(!window.__unsafe && !$('#editor-panel img[src="x"]'), 'untrusted user strings remain inert');

  const bytes = Uint8Array.from(atob(png), char => char.charCodeAt(0));
  const files = ['sample-1.png','sample-2.png','sample-3.png'].map(name => new File([bytes], name, {type:'image/png'}));
  const input = $('#photo-upload');
  if (typeof DataTransfer === 'function') {
    const transfer = new DataTransfer(); files.forEach(file => transfer.items.add(file)); input.files = transfer.files;
  } else { Object.defineProperty(input, 'files', {configurable:true, value:files}); }
  input.dispatchEvent(new Event('change', {bubbles:true}));
  await waitFor(async () => (await finding()).photos.length === 3 && $$('.photo-card').length === 3, 'multi-photo upload');
  check((await finding()).photos.length === 3, 'multiple synthetic photos persisted');
  const firstPhotoId = (await finding()).photos[0].id;
  setValue('.photo-card input', '合成照片：取用通道模拟位置', 'change');
  await waitFor(async () => (await finding()).photos.find(photo => photo.id === firstPhotoId)?.caption.includes('取用通道') && $('.photo-card input')?.value.includes('取用通道') && !$('#finding-editor')?.hasAttribute('aria-busy'), 'photo caption UI completed');
  click('.photo-card button[aria-label="照片下移"]');
  await waitFor(async () => (await finding()).photos[1]?.id === firstPhotoId, 'photo reorder');
  check((await finding()).photos[1].id === firstPhotoId, 'photo ordering persisted');
  await waitFor(() => !$('#finding-editor')?.hasAttribute('aria-busy'), 'photo reorder idle');
  click('.photo-thumb-button');
  await waitFor(() => $('#photo-dialog').open, 'photo preview');
  check(Boolean($('#photo-dialog img')?.src.includes('/api/photos/')), 'full photo preview uses local image');
  click('#photo-dialog .close-dialog');
  click(textButton('删除', $$('.photo-card')[2]));
  await waitFor(() => $('#confirm-dialog').open, 'photo removal confirmation');
  click('#confirm-yes');
  await waitFor(async () => (await finding()).photos.length === 2 && $$('.photo-card').length === 2, 'photo removal');
  check((await finding()).photos.length === 2, 'photo removal persisted');

  await tab('bases');
  click(textButton('检索法规条款'));
  await waitFor(() => $('#search-dialog').open, 'knowledge search dialog');
  for (const [query, classification, label] of [
    ['灭火器前堆放纸箱', 'needs_conditions', '条件不足'],
    ['插座坏了', 'evidence_gap', '法源缺证'],
    ['尚未确认压力表损坏', 'fact_unconfirmed', '现场事实未确认'],
  ]) {
    setValue('#knowledge-query', query); submit('#knowledge-search-form');
    await waitFor(() => $('#search-guidance').dataset.classification === classification && !$('#knowledge-search-form button').disabled, `assessment ${classification}`);
    const facts = $$('#search-guidance .search-required-facts li');
    check($('#search-guidance .search-assessment-label')?.textContent.includes(label) && $('#search-guidance .search-assessment-reason')?.textContent.includes('评估原因：') && facts.length > 0 && facts.every(item => /[\u3400-\u9fff]/.test(item.textContent)) && (await finding()).bases.length === 0, `${classification} assessment shows Chinese reasons and required facts without confirming a finding`);
  }
  setValue('#knowledge-query', '灭火器被遮挡');
  submit('#knowledge-search-form');
  await waitFor(() => $('.knowledge-result[data-hazard-id="H003"]'), 'search existing knowledge');
  check($('#search-guidance').dataset.classification === 'candidate_matches' && $('#search-guidance').textContent.includes('候选结果不确认现场隐患') && $$('#search-guidance .search-required-facts li').length === 0, 'candidate assessment clears stale missing facts and preserves human confirmation');
  click('.knowledge-result[data-hazard-id="H003"]');
  await waitFor(() => $('#profile-select') && $('.law-choice'), 'knowledge detail');
  check($('#knowledge-detail .quote')?.textContent.includes('便于取用') && $('#knowledge-detail a[href^="http"]'), 'search returns full official clause and metadata');
  const profileOptions = [...$('#profile-select').options].filter(option => option.value && option.value !== '__generic__');
  const obstruction = profileOptions.find(option => /堆物|遮挡|纸箱/.test(option.textContent));
  setValue('#profile-select', obstruction?.value || '__generic__', 'change');
  click(textButton('关联所选条款', $('#knowledge-detail')));
  await waitFor(async () => !$('#search-dialog').open && (await finding()).bases.length > 0 && $('.fact-card'), 'basis snapshot binding');
  current = await finding();
  check(current.facts.every(fact => fact.status === 'unknown'), 'binding a reference never confirms field facts');
  check(current.bases.every(basis => basis.as_of && basis.data_version && basis.text), 'basis snapshot includes version, as-of and exact text');
  await tab('review');
  check(textButton('提交专业审核').disabled, 'unknown facts prevent review submission');
  await tab('facts');
  let cards = $$('.fact-card');
  check(cards.length > 0, 'fact checklist visible');
  click('input[value="denied"]', cards[0]);
  const firstNote = $('.fact-note', cards[0]); firstNote.value = '测试用否定：必须阻止提交'; firstNote.dispatchEvent(new Event('input',{bubbles:true}));
  await save();
  await tab('review');
  check(textButton('提交专业审核').disabled, 'denied mandatory field fact prevents confirmation');
  await tab('facts');
  const factCount = $$('.fact-card').length;
  for (let i = 0; i < factCount; i += 1) {
    cards = $$('.fact-card');
    const card = cards[i];
    const fact = (await finding()).facts[i];
    click(`input[value="${fact.allows_denied ? 'denied' : (fact.expected || 'confirmed')}"]`, card);
    const note = $('.fact-note', card);
    note.value = fact.allows_denied ? '合成验收：本条条件分支未采用，已核对其适用边界。' : `合成验收逐项核查说明 ${i + 1}：已对照样例、条款适用范围与记录核实。`;
    note.dispatchEvent(new Event('input', {bubbles:true}));
    // Save between edits to catch stale listener/object references after autosave.
    await save();
  }
  current = await finding();
  check(current.facts.every(fact => fact.note && (fact.status === (fact.expected || 'confirmed') || (fact.allows_denied && fact.status === 'denied'))), 'sequential fact saves preserve all confirmations and notes');
  check(current.blockers.length === 0, 'only explicit evidence and supported conditions clear blockers');
  check($('#facts-progress-text').textContent.startsWith(`${factCount} / ${factCount}`), 'checklist progress matches canonical facts');
  await tab('review');
  setValue('#reviewer-name', '样例检查人员');
  setValue('#review-comment', '仅用于合成数据功能验收，申请专业审核。');
  click(textButton('提交专业审核'));
  await waitFor(async () => (await finding()).status === 'pending_review' && textButton('确认通过审核'), 'submit review');
  setValue('#reviewer-name', '样例专业审核人员');
  setValue('#review-comment', '已逐条核对合成样例、法源范围、事实说明及整改建议；仅作功能验收。');
  click(textButton('确认通过审核'));
  await waitFor(async () => (await finding()).status === 'confirmed' && $('#editor-status').textContent.includes('已确认'), 'professional confirmation');
  check((await finding()).reviews.some(review => review.decision === 'confirm' && review.reviewer === '样例专业审核人员'), 'professional review is recorded');
  await tab('record');
  check(Boolean($('[data-record-fieldset]').disabled), 'confirmed records are read-only until reopened');
  await tab('review');
  const audit = $('.audit-history'); audit.open = true; audit.dispatchEvent(new Event('toggle'));
  await waitFor(() => $('.audit-item'), 'audit history');
  check((await request(`/api/findings/${originalId}/audit`)).length > 5, 'audit trail records workflow operations');
  click(textButton('生成报告 ↗'));
  await waitFor(() => $('#report-dialog').open && $('#report-form'), 'report dialog');
  click('#report-form input[value="confirmed"]');
  submit('#report-form');
  await waitFor(() => $('.report-result a[href$=".docx"]') || $('.report-result a[href*="docx"]'), 'confirmed report generation', 90000);
  const reportLinks = $$('.report-result a').map(link => ({text:link.textContent,url:link.href}));
  const reports = await request(`/api/projects/${projectId}/reports`);
  const confirmedReport = reports.find(report => report.mode === 'confirmed');
  check(Boolean(confirmedReport?.docx_url && confirmedReport?.pdf_url && confirmedReport?.snapshot_url), 'Word, PDF and immutable report snapshot generated');
  for (const [key, magic] of [['docx_url','PK'],['pdf_url','%PDF']]) {
    const response = await fetch(confirmedReport[key]);
    const data = new Uint8Array(await response.arrayBuffer());
    check(response.ok && String.fromCharCode(...data.slice(0,magic.length)) === magic, `downloaded ${key} has valid file signature`);
  }
  const snapshot = await request(confirmedReport.snapshot_url);
  check(Boolean(snapshot), 'immutable report snapshot readable');
  check(reportLinks.length >= 3, 'download controls rendered for generated report');
  click('#report-dialog .close-dialog');
  await tab('record');
  click(textButton('复制记录'));
  await waitFor(() => selected().finding !== originalId && $('[data-field="observation"]'), 'copy finding');
  const copiedId = selected().finding;
  current = await finding();
  check(current.photos.length === 0 && current.observation === '' && current.facts.every(fact => fact.status === 'unknown'), 'copy resets scene facts and excludes original photographs');
  await tab('bases');
  const basisId = current.bases[0].id;
  click(textButton('移除', $('.basis-card')));
  await waitFor(() => $('#confirm-dialog').open, 'remove basis confirmation');
  click('#confirm-yes');
  await waitFor(async () => !(await finding()).bases.some(basis => basis.id === basisId) && !$('#finding-editor')?.hasAttribute('aria-busy'), 'remove copied basis UI completed');
  check(!(await finding()).bases.some(basis => basis.id === basisId), 'reference can be removed without changing original');
  await tab('record');
  setValue('[data-field="observation"]', '第二条合成观察：条件与法源未完成，保持草稿。');
  await save();
  click(textButton('生成报告 ↗'));
  await waitFor(() => $('#report-dialog').open && $('#report-form'), 'report reopen');
  click('#report-form input[value="confirmed"]'); submit('#report-form');
  await waitFor(() => $('.report-result a'), 'report excluding draft', 90000);
  let allReports = await request(`/api/projects/${projectId}/reports`);
  check(allReports.some(report => report.mode === 'confirmed' && report.excluded_count === 1), 'unconfirmed copy excluded from confirmed report');
  click('#report-form input[value="draft"]'); submit('#report-form');
  await waitFor(async () => (await request(`/api/projects/${projectId}/reports`)).some(report => report.mode === 'draft'), 'draft report', 90000);
  await waitFor(() => !$('#report-form button[type="submit"]').disabled, 'report UI idle');
  allReports = await request(`/api/projects/${projectId}/reports`);
  check(allReports.length >= 3 && $$('.report-history-item').length >= 3, 'report history includes confirmed and draft versions');
  click('#report-dialog .close-dialog');
  const csvLink = $$('a').find(link => link.textContent === '照片清单');
  check(Boolean(csvLink) && (await fetch(csvLink.href)).ok, 'photo inventory CSV downloadable');
  click('#backup-button');
  await waitFor(() => $$('.toast.warning').some(toast => toast.textContent.includes('备份包含')), 'private backup warning');
  check($$('.toast.warning').some(toast => toast.textContent.includes('照片')), 'backup UI discloses private content');
  const backupResponse = await fetch('/api/backup');
  const backupBytes = new Uint8Array(await backupResponse.arrayBuffer());
  check(backupResponse.ok && backupBytes[0] === 80 && backupBytes[1] === 75, 'private backup endpoint returns a ZIP archive');
  click(textButton('删除草稿'));
  await waitFor(() => $('#confirm-dialog').open, 'draft deletion dialog'); click('#confirm-yes');
  await waitFor(() => selected().finding === originalId && $('#editor-status')?.textContent.includes('已确认'), 'draft deletion');
  check((await request(`/api/projects/${projectId}/findings`)).length === 1, 'draft deletion refreshes the project list');
  check((await request(`/api/findings/${originalId}`)).status === 'confirmed', 'draft deletion preserves original confirmed finding');
  check((await fetch(`/api/findings/${copiedId}`)).status === 404, 'deleted draft is unavailable');
  await tab('review');
  setValue('#reviewer-name', '样例修订人员');
  setValue('#review-comment', '验证重新打开后任何事实性编辑都需要重新核实。');
  click(textButton('重新打开并修订'));
  await waitFor(async () => (await finding()).status === 'draft' && $('#editor-status')?.textContent.includes('草稿') && !$('#finding-editor')?.hasAttribute('aria-busy'), 'reopen confirmed finding UI completed');
  await tab('record');
  setValue('[data-field="description"]', '合成样例修订：补充现场位置描述，须再次核实与审核。');
  await save();
  current = await finding();
  check(current.status !== 'confirmed' && current.facts.every(fact => fact.status === 'unknown'), 'substantive revision invalidates previous facts and approval');
  const historicalSnapshot = await request(confirmedReport.snapshot_url);
  check(JSON.stringify(historicalSnapshot) === JSON.stringify(snapshot), 'previous report snapshot remains immutable after revision');
  const beforeProjectRevision = current.revision;
  click(textButton('编辑项目'));
  await waitFor(() => $('#project-dialog').open, 'project context edit');
  setValue('#project-form [name="purpose"]', '变更后的合成检查范围；需要重新核实项目条件。');
  submit('#project-form');
  await waitFor(() => !$('#project-dialog').open && $('.project-purpose')?.textContent.includes('变更后的'), 'project context refresh');
  current = await finding();
  check(current.revision > beforeProjectRevision && current.status === 'draft' && current.facts.every(fact => fact.status === 'unknown'), 'project context edits reload invalidated current finding');
  check($$('.toast').some(toast => toast.textContent.includes('项目条件变更')), 'project change displays re-verification notice');
  click('#menu-button'); check($('#sidebar').classList.contains('open'), 'responsive navigation toggle opens');
  click('#sidebar-backdrop'); check(!$('#sidebar').classList.contains('open'), 'responsive navigation toggle closes');
  check(!window.__unsafe, 'no user-controlled HTML execution');
  return {checks,project_id:projectId,finding_id:originalId,report_count:allReports.length,fact_count:factCount,profile_id:obstruction?.value || null,final_status:current.status};
}"""

DOM_RUNNER = r"""
import fs from 'node:fs';
import {createRequire} from 'node:module';
const require = createRequire(import.meta.url);
const config = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const {JSDOM,VirtualConsole} = require(config.domModule);
const errors = [];
const virtualConsole = new VirtualConsole();
virtualConsole.on('jsdomError', error => {
  if (!/Not implemented: navigation/.test(error.message)) errors.push(error.message);
});
const markup = await (await fetch(config.url)).text();
const code = await (await fetch(new URL('/app.js', config.url))).text();
function createDOM(hash = '') {
  const dom = new JSDOM(markup, {url:config.url+hash,runScripts:'outside-only',pretendToBeVisual:true,virtualConsole});
  const win = dom.window;
  win.fetch = (url, options) => fetch(new URL(url, config.url), options);
  win.Headers = globalThis.Headers;
  win.AbortController = globalThis.AbortController;
  win.File = globalThis.File;
  win.Blob = globalThis.Blob;
  win.FormData = class extends globalThis.FormData {
    constructor(form) {
      super();
      if (form) for (const element of form.elements) {
        if (!element.name || element.disabled || ['submit','button','reset','file'].includes(element.type)) continue;
        if (['checkbox','radio'].includes(element.type) && !element.checked) continue;
        this.append(element.name, element.value);
      }
    }
  };
  win.HTMLDialogElement.prototype.showModal = function() { this.setAttribute('open',''); };
  win.HTMLDialogElement.prototype.close = function() { this.removeAttribute('open'); this.dispatchEvent(new win.Event('close')); };
  win.addEventListener('error', event => errors.push(event.error?.stack || event.message));
  win.eval(code);
  return dom;
}
let dom = createDOM();
try {
  const result = await dom.window.eval(`(${config.flow})` )({png:config.png});
  const selection = dom.window.location.hash;
  dom.window.close();
  dom = createDOM(selection);
  const end = Date.now()+15000;
  while (!dom.window.document.querySelector('[data-field="observation"]') && Date.now()<end) await new Promise(resolve=>setTimeout(resolve,70));
  if (!dom.window.document.querySelector('[data-field="observation"]')?.value.includes('合成现场')) throw Error('Persisted selection/record failed after page reload');
  result.checks.push('page reload restores persisted project and finding');
  if (errors.length) throw Error(errors.join('\n'));
  fs.writeFileSync(config.result, JSON.stringify({engine:'dom',visual_validation:false,...result},null,2));
  console.log(JSON.stringify({engine:'dom',checks:result.checks.length,project_id:result.project_id,visual_validation:false}));
} catch(error) {
  fs.writeFileSync(config.failureHTML, dom.serialize());
  console.error(error.stack || error);
  process.exitCode=1;
} finally { dom.window.close(); }
"""


def make_fixture() -> str:
    from PIL import Image, ImageDraw
    image = Image.new('RGB', (640, 400), '#e7efe9')
    draw = ImageDraw.Draw(image)
    draw.rectangle((210, 90, 280, 330), fill='#c9363e')
    draw.rectangle((320, 220, 510, 350), fill='#c8a16b')
    draw.text((24, 24), 'SYNTHETIC TEST PHOTO / NO REAL COMPANY', fill='#194c36')
    stream = io.BytesIO()
    image.save(stream, format='PNG')
    return base64.b64encode(stream.getvalue()).decode('ascii')


def start_server(data_dir: Path):
    import uvicorn
    from workbench.backend.app import create_app
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('127.0.0.1', 0))
    port = server_socket.getsockname()[1]
    app = create_app(data_dir=data_dir)
    server = uvicorn.Server(uvicorn.Config(app, log_level='warning'))
    thread = threading.Thread(target=server.run, kwargs={'sockets':[server_socket]}, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{port}'
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url+'/api/health', timeout=1) as response:
                if response.status == 200:
                    return url, server, thread
        except (OSError, TimeoutError):
            time.sleep(.05)
    raise RuntimeError('Isolated API did not start')


def run_browser(args, url, output, png):
    from playwright.sync_api import sync_playwright
    errors = []
    with sync_playwright() as playwright:
        executable = args.browser_executable or shutil.which('chromium') or shutil.which('chromium-browser')
        launch = {'headless':True, 'args':['--no-sandbox']}
        if executable:
            launch['executable_path'] = executable
        browser = playwright.chromium.launch(**launch)
        page = browser.new_page(viewport={'width':1440,'height':1000}, device_scale_factor=1)
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(url, wait_until='networkidle')
        try:
            result = page.evaluate(FLOW, {'png':png})
            page.reload(wait_until='networkidle')
            page.locator('[data-field="observation"]').wait_for()
            if '合成现场' not in page.locator('[data-field="observation"]').input_value():
                raise AssertionError('Persisted record failed after page reload')
            result['checks'].append('page reload restores persisted project and finding')
            page.screenshot(path=str(output/'desktop.png'), full_page=True)
            page.set_viewport_size({'width':390,'height':844})
            page.screenshot(path=str(output/'mobile.png'), full_page=True)
            overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
            if overflow:
                raise AssertionError('Mobile page overflows horizontally')
            result['checks'].append('mobile viewport has no horizontal overflow')
            if errors:
                raise AssertionError('\n'.join(errors))
            result = {'engine':'chromium','visual_validation':True,**result}
            (output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            return result
        except Exception:
            page.screenshot(path=str(output/'failure.png'), full_page=True)
            raise
        finally:
            browser.close()


def run_dom(args, url, output, png, temporary):
    module = args.dom_module or os.environ.get('WORKBENCH_JSDOM_MODULE')
    if not module or not Path(module).exists():
        raise RuntimeError('DOM mode requires --dom-module /path/to/jsdom/lib/api.js (external test dependency).')
    config = {'domModule':str(Path(module).resolve()),'url':url,'flow':FLOW,'png':png,
              'result':str(output/'result.json'),'failureHTML':str(output/'failure.html')}
    config_path = temporary/'dom-config.json'
    config_path.write_text(json.dumps(config,ensure_ascii=False),encoding='utf-8')
    runner_path = temporary/'dom-runner.mjs'
    runner_path.write_text(DOM_RUNNER,encoding='utf-8')
    subprocess.run([shutil.which('node') or 'node',str(runner_path),str(config_path)],check=True,timeout=300)
    return json.loads((output/'result.json').read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', help='Use an already-running workbench (creates synthetic data there). Default starts an isolated temporary service.')
    parser.add_argument('--output', default='/tmp/safety-basis-workbench-ui-qa', help='QA output directory outside the public repository.')
    parser.add_argument('--engine', choices=['browser','dom'], default='browser')
    parser.add_argument('--dom-module', help='Absolute jsdom/lib/api.js path for explicitly requested DOM-only integration.')
    parser.add_argument('--browser-executable', help='Chromium executable path.')
    args = parser.parse_args()
    output = Path(args.output).expanduser().resolve()
    try:
        output.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise SystemExit('QA artifacts must remain outside the public Git repository.')
    output.mkdir(parents=True,exist_ok=True)
    server = thread = None
    with tempfile.TemporaryDirectory(prefix='safety-basis-ui-') as temp_name:
        temporary = Path(temp_name)
        try:
            url = args.url.rstrip('/') if args.url else None
            if not url:
                url,server,thread = start_server(temporary/'private-data')
            fixture = make_fixture()
            result = run_browser(args,url,output,fixture) if args.engine == 'browser' else run_dom(args,url,output,fixture,temporary)
            print(json.dumps({'status':'passed','checks':len(result['checks']),'engine':result['engine'],
                              'visual_validation':result['visual_validation'],'result':str(output/'result.json')},ensure_ascii=False))
        finally:
            if server:
                server.should_exit = True
                thread.join(timeout=10)


if __name__ == '__main__':
    main()
