const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const STATUS = { draft: '草稿', needs_facts: '待核实', pending_review: '待专业审核', confirmed: '已确认', rejected: '已退回' };
const FIELDS = ['finding_kind', 'location', 'equipment', 'observation', 'description', 'rectification', 'due_date', 'assignee', 'notes'];
const TABS = [['record', '现场记录'], ['bases', '法规依据'], ['facts', '事实核实'], ['review', '专业审核']];
const state = { projects: [], project: null, findings: [], finding: null, draft: {}, factDraft: [], meta: {}, tab: 'record', filter: 'all', dirty: false, factsDirty: false, editEpoch: 0, factEpoch: 0, savePromise: null, saveTimer: null, saveError: '', operation: false, request: 0, queryRequest: 0, selectedHazard: null, searchResults: [], projectEditing: null, reports: [] };

function node(tag, className, ...children) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    element.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return element;
}
function button(label, action, className = 'secondary', options = {}) {
  const result = node('button', `button ${className}`, label);
  result.type = 'button';
  result.addEventListener('click', action);
  Object.assign(result, options);
  return result;
}
function badge(status) { return node('span', `status-badge ${status || 'draft'}`, STATUS[status] || status || '草稿'); }
function setText(selector, text) { const element = $(selector); if (element) element.textContent = text; }
function readable(value) {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string' || typeof value === 'number') return String(value);
  if (Array.isArray(value)) return value.map(readable).filter(Boolean).join('；');
  if (typeof value === 'object') {
    const preferred = ['message', 'text', 'label', 'title', 'summary', 'description', 'question'];
    const parts = preferred.filter(key => value[key]).map(key => readable(value[key]));
    if (parts.length) return [...new Set(parts)].join(' · ');
    return Object.entries(value).filter(([, val]) => val && typeof val !== 'boolean').map(([key, val]) => `${key}：${readable(val)}`).join('；');
  }
  return '';
}
function listOf(data, key) { return Array.isArray(data) ? data : data?.[key] || data?.items || []; }
function unwrap(data, key) { return data?.[key] || data; }
function plainDate(value) { return value ? String(value).slice(0, 10) : '未填写日期'; }
function timeText(value) {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false });
}
function safeUrl(value, sameOrigin = false) {
  if (typeof value !== 'string' || !value.trim()) return '';
  try {
    const url = new URL(value, location.href);
    if (!['http:', 'https:'].includes(url.protocol)) return '';
    if (sameOrigin && url.origin !== location.origin) return '';
    return url.href;
  } catch { return ''; }
}
function downloadLink(label, url, className = 'secondary small') {
  const href = safeUrl(url, true);
  if (!href) return node('span', 'subtle tiny', `${label}暂不可用`);
  const link = node('a', `button ${className}`, label);
  link.href = href;
  link.download = '';
  return link;
}
function sourceLink(url, label = '查看官方法源 ↗') {
  const href = safeUrl(url);
  if (!href) return node('span', 'subtle tiny', '法源地址缺失');
  const link = node('a', '', label);
  link.href = href; link.target = '_blank'; link.rel = 'noopener noreferrer';
  return link;
}
function toast(message, kind = 'success', duration = 5500) {
  const entry = node('div', `toast ${kind}`, node('span', '', message));
  const close = node('button', 'icon-button', '×');
  close.type = 'button'; close.setAttribute('aria-label', '关闭提示'); close.onclick = () => entry.remove();
  entry.append(close); $('#toasts').append(entry);
  if (kind === 'error') entry.setAttribute('role', 'alert');
  if (duration) setTimeout(() => entry.remove(), duration);
}
function errorText(error) { return error?.message || '请求未完成，请重试。'; }
async function api(path, options = {}) {
  const { body, timeout = 45000, signal, ...rest } = options;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  if (signal) signal.addEventListener('abort', () => controller.abort(), { once: true });
  const headers = new Headers(rest.headers || {});
  let payload = body;
  if (body !== undefined && !(body instanceof FormData)) { headers.set('Content-Type', 'application/json'); payload = JSON.stringify(body); }
  try {
    const response = await fetch(path, { ...rest, body: payload, headers, signal: controller.signal, credentials: 'same-origin', cache: 'no-store' });
    let result;
    const type = response.headers.get('content-type') || '';
    if (type.includes('json')) result = await response.json(); else result = await response.text();
    if (!response.ok) {
      let detail = result?.detail || result?.message || result;
      if (Array.isArray(detail)) detail = detail.map(item => item.msg ? `${(item.loc || []).filter(x => x !== 'body').join(' / ')}：${item.msg}` : readable(item)).join('；');
      else if (typeof detail === 'object') detail = readable(detail);
      const error = new Error(detail || `请求失败（${response.status}）`);
      error.status = response.status; error.data = result; throw error;
    }
    return result;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('请求耗时较长或已取消。请检查工作区连接后重试。');
    if (error instanceof TypeError) throw new Error('无法连接工作台服务。请刷新页面或检查登录状态后重试。');
    throw error;
  } finally { clearTimeout(timer); }
}
function showDialog(id) { const dialog = $(id); if (!dialog.open) dialog.showModal(); }
function closeDialog(element) { element.closest('dialog')?.close(); }
async function confirmAction(title, description, yesLabel = '确认') {
  const dialog = $('#confirm-dialog');
  setText('#confirm-title', title); setText('#confirm-description', description); setText('#confirm-yes', yesLabel);
  return new Promise(resolve => {
    let accepted = false;
    const yes = () => { accepted = true; dialog.close(); };
    const no = () => dialog.close();
    const closed = () => { $('#confirm-yes').removeEventListener('click', yes); $('#confirm-no').removeEventListener('click', no); resolve(accepted); };
    $('#confirm-yes').addEventListener('click', yes); $('#confirm-no').addEventListener('click', no);
    dialog.addEventListener('close', closed, { once: true }); dialog.showModal();
  });
}
function setMobileMenu(open) { $('#sidebar').classList.toggle('open', open); $('#sidebar-backdrop').hidden = !open; $('#menu-button').setAttribute('aria-expanded', String(open)); }
function rememberSelection() {
  const id = state.project?.id || '', findingId = state.finding?.id || '';
  const hash = id ? `project=${encodeURIComponent(id)}${findingId ? `&finding=${encodeURIComponent(findingId)}` : ''}` : '';
  history.replaceState(null, '', `${location.pathname}${location.search}${hash ? `#${hash}` : ''}`);
  try { localStorage.setItem('safety-basis-selection', JSON.stringify({ project: id, finding: findingId })); } catch { /* Storage may be disabled; server persistence remains available. */ }
}
function requestedSelection() {
  const hash = new URLSearchParams(location.hash.slice(1));
  if (hash.get('project')) return { project: hash.get('project'), finding: hash.get('finding') };
  try { return JSON.parse(localStorage.getItem('safety-basis-selection') || '{}'); } catch { return {}; }
}
function isLocked() { return ['confirmed', 'pending_review'].includes(state.finding?.status); }
function editorTitle(finding = state.finding) { return finding?.equipment || finding?.location || finding?.observation?.slice(0, 28) || '未命名现场记录'; }
function counters() {
  return { total: state.findings.length, attention: state.findings.filter(f => ['draft', 'needs_facts', 'rejected'].includes(f.status)).length, review: state.findings.filter(f => f.status === 'pending_review').length, confirmed: state.findings.filter(f => f.status === 'confirmed').length };
}
function updateListEntry(finding) {
  const index = state.findings.findIndex(item => item.id === finding.id);
  if (index >= 0) state.findings[index] = { ...state.findings[index], ...finding };
  else state.findings.push(finding);
  const project = state.projects.find(item => item.id === finding.project_id);
  if (project) { const count = counters(); project.findings_count = count.total; project.confirmed_count = count.confirmed; }
}
function initializeDraft(finding) {
  state.finding = finding;
  state.draft = Object.fromEntries(FIELDS.map(key => [key, finding[key] || (key === 'finding_kind' ? 'onsite' : '')]));
  state.factDraft = (finding.facts || []).map(fact => ({ ...fact, status: fact.status || 'unknown', note: fact.note || '' }));
  state.dirty = false; state.factsDirty = false; state.saveError = ''; state.editEpoch += 1; state.factEpoch += 1;
  updateListEntry(finding);
}
function queueSave() {
  clearTimeout(state.saveTimer);
  state.saveTimer = setTimeout(() => saveCurrent().catch(() => {}), 1100);
  updateSaveUI();
}
async function saveCurrent() {
  clearTimeout(state.saveTimer);
  if (state.savePromise) { await state.savePromise; if (state.dirty || state.factsDirty) return saveCurrent(); return; }
  if (!state.finding || (!state.dirty && !state.factsDirty)) return;
  const id = state.finding.id, editEpoch = state.editEpoch, factEpoch = state.factEpoch;
  const saveFields = state.dirty, saveFacts = state.factsDirty;
  const payload = { ...state.draft, revision: state.finding.revision };
  const facts = state.factDraft.map(({ key, status, note }) => ({ key, status, note }));
  state.saveError = '';
  state.savePromise = (async () => {
    let latest = state.finding;
    try {
      if (saveFields) latest = unwrap(await api(`/api/findings/${encodeURIComponent(id)}`, { method: 'PATCH', body: payload }), 'finding');
      if (saveFacts) latest = unwrap(await api(`/api/findings/${encodeURIComponent(id)}/facts`, { method: 'PUT', body: { facts, revision: latest.revision } }), 'finding');
      if (!latest?.id || latest.id !== id || !('revision' in latest)) latest = unwrap(await api(`/api/findings/${encodeURIComponent(id)}`), 'finding');
      if (state.finding?.id === id) {
        state.finding = latest;
        if (saveFields && state.editEpoch === editEpoch) state.dirty = false;
        if (state.factEpoch === factEpoch) {
          const previous = new Map(state.factDraft.map(fact => [fact.key, fact]));
          state.factDraft = (latest.facts || []).map(fact => Object.assign(previous.get(fact.key) || {}, fact));
          if (saveFacts) state.factsDirty = false;
          updateFactProgress();
        }
        updateListEntry({ ...latest, ...state.draft }); updateProjectNumbers(); renderFindingList(); updateEditorStatus();
      }
    } catch (error) {
      if (state.finding?.id === id) state.saveError = error.status === 409 ? '记录已在其他页面更新。请先重新载入服务端版本，避免覆盖他人的更改。' : errorText(error);
      toast(state.saveError || errorText(error), 'error', 9000); throw error;
    } finally { state.savePromise = null; updateSaveUI(); }
  })();
  updateSaveUI();
  await state.savePromise;
  if (state.dirty || state.factsDirty) queueSave();
}
async function flushChanges() { clearTimeout(state.saveTimer); await saveCurrent(); if (state.dirty || state.factsDirty) await saveCurrent(); }
function updateSaveUI() {
  $$('.save-status').forEach(element => {
    element.className = 'save-status';
    if (state.saveError) { element.textContent = '保存失败'; element.classList.add('error'); }
    else if (state.savePromise) element.textContent = '正在保存…';
    else if (state.dirty || state.factsDirty) { element.textContent = '有待保存的更改'; element.classList.add('dirty'); }
    else { element.textContent = '✓ 已保存到工作区'; element.classList.add('saved'); }
  });
  const saveError = $('#editor-save-error');
  if (saveError) { saveError.hidden = !state.saveError; $('.error-message', saveError).textContent = state.saveError; }
}
function updateEditorStatus() {
  const target = $('#editor-status');
  if (target && state.finding) target.replaceChildren(badge(state.finding.status));
  TABS.forEach(([key]) => { const count = $(`[data-tab-count="${key}"]`); if (count) count.textContent = key === 'bases' ? String(state.finding?.bases?.length || 0) : key === 'facts' ? String(state.finding?.facts?.length || 0) : ''; });
  updateSaveUI();
}
function updateProjectNumbers() { const count = counters(); Object.entries(count).forEach(([key, value]) => setText(`[data-stat="${key}"]`, value)); }
async function reloadCurrent() {
  if (!state.finding) return;
  const id = state.finding.id;
  const finding = unwrap(await api(`/api/findings/${encodeURIComponent(id)}`), 'finding');
  if (state.finding?.id !== id) return;
  initializeDraft(finding); renderFindingList(); renderEditor(); updateProjectNumbers(); renderProjectList();
}
async function runMutation(action, success) {
  if (state.operation) return;
  try {
    await flushChanges(); state.operation = true;
    $('#finding-editor')?.setAttribute('aria-busy', 'true');
    $$('[data-record-fieldset], [data-fact-fieldset]').forEach(fieldset => { fieldset.disabled = true; });
    const result = await action();
    await reloadCurrent();
    if (success) toast(success);
    return result;
  } catch (error) { toast(errorText(error), 'error', 9000); }
  finally { state.operation = false; $('#finding-editor')?.removeAttribute('aria-busy'); $$('[data-record-fieldset], [data-fact-fieldset]').forEach(fieldset => { fieldset.disabled = isLocked(); }); }
}
async function refreshProjects() { state.projects = listOf(await api('/api/projects'), 'projects'); renderProjectList(); }
function renderProjectList() {
  setText('#project-count', state.projects.length);
  const target = $('#project-list'); target.replaceChildren();
  const query = $('#project-filter').value.trim().toLowerCase();
  const projects = state.projects.filter(project => `${project.name} ${project.company}`.toLowerCase().includes(query));
  if (!projects.length) { target.append(node('p', 'subtle tiny', query ? '没有匹配的项目' : '还没有项目。创建第一个检查项目开始工作。')); return; }
  for (const project of projects) {
    const item = node('button', `project-nav-item ${state.project?.id === project.id ? 'active' : ''}`,
      node('strong', '', project.name || '未命名项目'), node('span', 'company', project.company || '企业未填写'),
      node('span', 'project-nav-meta', node('span', '', plainDate(project.inspection_date)), node('span', '', `${project.findings_count || 0} 条记录`)));
    item.type = 'button'; item.setAttribute('aria-current', state.project?.id === project.id ? 'page' : 'false');
    item.onclick = () => openProject(project.id); target.append(item);
  }
}
async function openProject(id, findingId) {
  try {
    await flushChanges();
    const request = ++state.request;
    const [projectData, findingData] = await Promise.all([api(`/api/projects/${encodeURIComponent(id)}`), api(`/api/projects/${encodeURIComponent(id)}/findings`)]);
    if (request !== state.request) return;
    state.project = unwrap(projectData, 'project'); state.findings = listOf(findingData, 'findings'); state.finding = null; state.filter = 'all';
    state.dirty = false; state.factsDirty = false; state.saveError = '';
    const selection = findingId && state.findings.some(f => f.id === findingId) ? findingId : state.findings[0]?.id;
    if (selection) initializeDraft(unwrap(await api(`/api/findings/${encodeURIComponent(selection)}`), 'finding'));
    if (request !== state.request) return;
    setMobileMenu(false); renderProjectList(); renderMain(); rememberSelection();
  } catch (error) { toast(errorText(error), 'error', 9000); }
}
async function openFinding(id) {
  if (id === state.finding?.id) return;
  try {
    await flushChanges(); const request = ++state.request;
    const finding = unwrap(await api(`/api/findings/${encodeURIComponent(id)}`), 'finding');
    if (request !== state.request) return;
    initializeDraft(finding); renderFindingList(); renderEditor(); rememberSelection();
  } catch (error) { toast(errorText(error), 'error'); }
}
function renderMain() {
  const main = $('#main'); main.replaceChildren();
  if (!state.project) { renderLanding(main); setText('#breadcrumb-current', '项目概览'); return; }
  setText('#breadcrumb-current', state.project.name || '检查项目');
  const header = node('div', 'page-header');
  const title = node('div', '', node('span', 'eyebrow', 'INSPECTION WORKSPACE'), node('h1', '', state.project.name), node('p', 'page-subtitle', state.project.company));
  title.append(node('div', 'project-meta-row', node('span', '', `检查日期 ${plainDate(state.project.inspection_date)}`), node('span', '', `检查人员 ${readable(state.project.inspectors) || '待填写'}`)));
  if (state.project.purpose) title.append(node('p', 'project-purpose', state.project.purpose));
  header.append(title, node('div', 'button-row', button('编辑项目', () => openProjectDialog(state.project), 'secondary'), downloadLink('照片清单', `/api/projects/${encodeURIComponent(state.project.id)}/photos.csv`, 'quiet'), button('生成报告 ↗', openReports, 'primary')));
  main.append(header);
  const count = counters();
  const stats = node('div', 'project-stat-grid');
  [['total', '现场记录', '▤', ''], ['attention', '待完善 / 核实', '○', 'attention'], ['review', '待专业审核', '◷', ''], ['confirmed', '审核确认', '✓', 'complete']].forEach(([key, label, symbol, className]) => {
    const number = node('strong', '', count[key]); number.dataset.stat = key;
    stats.append(node('div', `stat-card ${className}`, node('div', '', node('div', 'stat-card-label', label), number), node('span', 'stat-mark', symbol)));
  });
  main.append(stats);
  const workspace = node('div', 'workspace');
  const rail = node('section', 'finding-rail'); rail.setAttribute('aria-label', '现场记录列表');
  rail.append(node('div', 'rail-header', node('h2', '', '现场记录'), button('＋ 添加', createFinding, 'quiet small')));
  const filters = node('div', 'rail-filters');
  [['all', '全部'], ['attention', '待完善'], ['pending_review', '待审核'], ['confirmed', '已确认']].forEach(([key, label]) => {
    const item = node('button', `filter-pill ${state.filter === key ? 'active' : ''}`, label); item.type = 'button'; item.dataset.filter = key;
    item.onclick = () => { state.filter = key; $$('.filter-pill').forEach(b => b.classList.toggle('active', b.dataset.filter === key)); renderFindingList(); }; filters.append(item);
  });
  const list = node('div', 'finding-list'); list.id = 'finding-list';
  rail.append(filters, list, node('div', 'rail-footer', node('span', 'subtle tiny', '记录先保存，结论再确认。')));
  const editor = node('section', 'finding-editor'); editor.id = 'finding-editor'; editor.setAttribute('aria-label', '当前现场记录');
  workspace.append(rail, editor); main.append(workspace); renderFindingList(); renderEditor();
}
function renderLanding(main) {
  const content = node('div', 'landing');
  const hero = node('section', 'welcome-card', node('span', 'eyebrow', 'EVIDENCE BEFORE CONCLUSION'), node('h1', '', '把现场记录，整理成', node('br'), '有依据的检查报告。'), node('p', 'intro', '从企业项目、现场照片到法规条款与事实核实，在同一个工作区完成记录、专业审核和报告导出。'), node('div', 'button-row', button('＋ 新建检查项目', () => openProjectDialog(), 'primary'), button('使用脱敏样例', loadDemo, 'secondary')));
  const flow = node('section', 'workflow-grid');
  [['01', '记录现场', '保留现场原话与照片，描述具体位置、设备和现象。'], ['02', '匹配法规', '复用安全依据知识库，保留条款原文与版本快照。'], ['03', '逐项核实', '核对事实、适用条件与误判边界，未知项保持待核实。'], ['04', '审核与导出', '由专业人员确认记录，生成带照片的 Word / PDF 报告。']].forEach(([step, title, text]) => flow.append(node('article', 'workflow-card', node('span', 'step', step), node('h3', '', title), node('p', '', text))));
  content.append(hero, flow, node('p', 'landing-note', '项目、照片和导出报告保存在当前私有工作区。请定期导出备份，并妥善保管企业资料。'));
  main.append(content);
}
function renderFindingList() {
  const list = $('#finding-list'); if (!list) return;
  const scroll = list.scrollTop, scrollLeft = list.scrollLeft; list.replaceChildren();
  const items = state.findings.filter(f => state.filter === 'all' || (state.filter === 'attention' ? ['draft', 'needs_facts', 'rejected'].includes(f.status) : f.status === state.filter));
  if (!items.length) { list.append(node('div', 'empty-state small', node('h3', '', state.findings.length ? '此状态暂无记录' : '尚无现场记录'), node('p', '', state.findings.length ? '切换筛选查看其他记录。' : '添加一条观察到的现场情况。'), state.findings.length ? null : button('＋ 添加记录', createFinding, 'secondary small'))); return; }
  items.forEach(finding => {
    const originalIndex = state.findings.findIndex(item => item.id === finding.id);
    const item = node('button', `finding-item ${state.finding?.id === finding.id ? 'active' : ''}`, node('div', 'finding-item-line', node('span', 'finding-number', `记录 ${String(originalIndex + 1).padStart(2, '0')}`), badge(finding.status)), node('strong', '', finding.observation || finding.description || '待填写现场情况'), node('div', 'location-line', [finding.location, finding.equipment].filter(Boolean).join(' · ') || '位置与设备待填写'));
    item.type = 'button'; item.dataset.findingId = finding.id; item.setAttribute('aria-pressed', String(state.finding?.id === finding.id)); item.onclick = () => openFinding(finding.id); list.append(item);
  });
  list.scrollTop = scroll; list.scrollLeft = scrollLeft;
}
function renderEditor() {
  const editor = $('#finding-editor'); if (!editor) return; editor.replaceChildren();
  if (!state.finding) { editor.append(node('div', 'empty-state no-finding', node('span', 'empty-symbol', '＋'), node('h3', '', '先记录现场，再形成结论'), node('p', '', '创建记录后，可添加多张照片、关联法规条款，并核实每一项适用条件。'), button('添加现场记录', createFinding, 'primary'))); return; }
  const status = node('span'); status.id = 'editor-status'; status.append(badge(state.finding.status));
  const saveStatus = node('span', 'save-status');
  const header = node('div', 'editor-header');
  const title = node('h2', '', editorTitle()); title.id = 'finding-title';
  header.append(node('div', 'editor-topline', node('div', 'editor-title', title, status), node('div', 'editor-actions', button('保存', async () => { try { await flushChanges(); toast('当前记录已保存。'); } catch {} }, 'secondary small'))));
  const reorderIndex = state.findings.findIndex(item => item.id === state.finding.id);
  const controls = node('div', 'editor-menu-row', button('复制记录', copyFinding, 'quiet small'), button('↑ 上移', () => moveFinding(-1), 'quiet small', { disabled: reorderIndex <= 0 }), button('↓ 下移', () => moveFinding(1), 'quiet small', { disabled: reorderIndex >= state.findings.length - 1 }), button('删除草稿', deleteFinding, 'danger-quiet small', { disabled: state.finding.status !== 'draft', title: state.finding.status !== 'draft' ? '仅可删除草稿；如需修改状态，请在专业审核中重新打开。' : '删除此草稿及关联照片' }));
  const controlLine = node('div', 'editor-topline', controls, saveStatus); controlLine.style.marginBottom = '0'; header.append(controlLine);
  editor.append(header);
  const error = node('div', 'notice error', node('span', 'error-message'), button('重新载入服务端版本', discardAndReload, 'secondary small')); error.id = 'editor-save-error'; error.hidden = true; editor.append(error);
  const tabs = node('div', 'editor-tabs'); tabs.setAttribute('role', 'tablist'); tabs.setAttribute('aria-label', '记录处理步骤');
  TABS.forEach(([key, label], index) => {
    const count = key === 'bases' || key === 'facts' ? node('span', 'tab-count', state.finding[key]?.length || 0) : null;
    if (count) count.dataset.tabCount = key;
    const tab = node('button', `editor-tab ${state.tab === key ? 'active' : ''}`, node('span', '', String(index + 1).padStart(2, '0')), label, count);
    tab.type = 'button'; tab.id = `tab-${key}`; tab.dataset.tab = key; tab.setAttribute('role', 'tab'); tab.setAttribute('aria-selected', String(state.tab === key)); tab.setAttribute('aria-controls', 'editor-panel');
    tab.onclick = async () => { try { await flushChanges(); state.tab = key; renderEditor(); } catch {} }; tabs.append(tab);
  });
  editor.append(tabs);
  const panel = node('div', 'editor-panel'); panel.id = 'editor-panel'; panel.setAttribute('role', 'tabpanel'); panel.setAttribute('aria-labelledby', `tab-${state.tab}`);
  if (isLocked() && state.tab !== 'review') panel.append(node('div', 'notice compact info', state.finding.status === 'confirmed' ? '此记录已审核确认。需要修改时，请在“专业审核”中重新打开。' : '此记录已提交专业审核。需要修改时，请先重新打开记录。'));
  ({ record: renderRecordPanel, bases: renderBasesPanel, facts: renderFactsPanel, review: renderReviewPanel }[state.tab] || renderRecordPanel)(panel);
  editor.append(panel);
  const index = TABS.findIndex(([key]) => key === state.tab), next = TABS[index + 1];
  editor.append(node('div', 'editor-bottom', node('span', '', `记录 ${state.finding.id} · 修订 ${state.finding.revision ?? 1}`), next ? button(`${next[1]} →`, async () => { try { await flushChanges(); state.tab = next[0]; renderEditor(); } catch {} }, 'secondary small') : node('span', 'save-status')));
  updateSaveUI();
}
async function discardAndReload() {
  if (await confirmAction('重新载入服务端版本', '此操作将丢弃当前页面尚未保存的编辑，显示工作区中最后保存的版本。', '重新载入')) {
    clearTimeout(state.saveTimer); state.dirty = false; state.factsDirty = false;
    try { await reloadCurrent(); } catch (error) { toast(errorText(error), 'error'); }
  }
}
function field(key, label, options = {}) {
  const wrapper = node('label', `field ${options.full ? 'full' : ''}`, node('span', '', label, options.hint ? node('i', '', options.hint) : null));
  const input = node(options.textarea ? 'textarea' : 'input');
  input.name = key; input.dataset.field = key; input.value = state.draft[key] || ''; input.placeholder = options.placeholder || ''; input.maxLength = options.maxLength || 10000;
  if (options.type) input.type = options.type;
  if (options.rows) input.rows = options.rows;
  input.addEventListener('input', () => { state.draft[key] = input.value; state.dirty = true; state.editEpoch += 1; state.saveError = ''; queueSave(); if (['location', 'equipment'].includes(key)) setText('#finding-title', editorTitle({ ...state.finding, ...state.draft })); });
  wrapper.append(input); if (options.help) wrapper.append(node('small', '', options.help)); return wrapper;
}
function renderRecordPanel(panel) {
  panel.append(node('div', 'section-heading', node('div', '', node('h3', '', '现场情况'), node('p', '', '保留观察到的现象。专业表述与法规适用性将在后续步骤核实。'))));
  const form = node('fieldset'); form.dataset.recordFieldset = ''; form.disabled = isLocked();
  const kind = node('select'); kind.name = 'finding_kind'; kind.dataset.field = 'finding_kind';
  [['onsite', '现场隐患'], ['document_review', '资料核查']].forEach(([value, label]) => { const option = node('option', '', label); option.value = value; kind.append(option); });
  kind.value = state.draft.finding_kind || 'onsite';
  kind.addEventListener('change', () => { state.draft.finding_kind = kind.value; state.dirty = true; state.editEpoch += 1; state.saveError = ''; queueSave(); });
  const grid = node('div', 'form-grid',
    node('label', 'field full', node('span', '', '记录类型'), kind, node('small', '', '资料核查类条款须选择“资料核查”；现场观察与资料核验分别记录。')),
    field('location', '现场位置', { placeholder: '例如：1 号车间东侧配电区', maxLength: 500 }),
    field('equipment', '设备 / 对象', { placeholder: '例如：低压配电柜、灭火器', maxLength: 500 }),
    field('observation', '现场原话 / 观察记录', { full: true, textarea: true, rows: 3, placeholder: '写下实际看到、测到或核验到的情况，避免直接预设违法结论。', help: '现场原话与专业表述分别保留，便于复核和追溯。' }),
    field('description', '专业隐患表述', { full: true, textarea: true, rows: 3, hint: '审核前为草稿', placeholder: '结合已核实的事实与适用条款，明确问题对象、位置和具体状态。' }),
    field('rectification', '整改建议', { full: true, textarea: true, rows: 3, placeholder: '填写与现场事实、适用条款相对应的整改措施。' }),
    field('assignee', '整改责任人 / 单位', { placeholder: '待企业确认的责任人或单位', maxLength: 200 }),
    field('due_date', '计划整改日期', { type: 'date', maxLength: 10 }),
    field('notes', '检查备注', { full: true, textarea: true, rows: 2, placeholder: '补充测量信息、资料来源、待补证内容或其他说明。' }));
  form.append(grid); panel.append(form, node('hr'));
  renderPhotos(panel);
}
function renderPhotos(panel) {
  panel.append(node('div', 'section-heading', node('div', '', node('h3', '', `现场照片 · ${state.finding.photos?.length || 0} 张`), node('p', '', '照片随记录保存，顺序与说明会用于报告。点击缩略图可放大查看。'))));
  if (!isLocked()) {
    const input = node('input', 'sr-only'); input.type = 'file'; input.accept = 'image/jpeg,image/png,image/webp'; input.multiple = true; input.id = 'photo-upload';
    const upload = node('label', 'photo-upload-zone', node('span', 'upload-icon', '＋'), node('div', '', node('strong', '', '添加现场照片'), node('small', '', '支持 JPG、PNG、WebP，单张不超过 20 MB，可多选或拖入。'))); upload.htmlFor = input.id; upload.tabIndex = 0;
    upload.addEventListener('keydown', event => { if (['Enter', ' '].includes(event.key)) { event.preventDefault(); input.click(); } });
    upload.addEventListener('dragover', event => { event.preventDefault(); upload.classList.add('dragover'); }); upload.addEventListener('dragleave', () => upload.classList.remove('dragover'));
    upload.addEventListener('drop', event => { event.preventDefault(); upload.classList.remove('dragover'); uploadPhotos([...event.dataTransfer.files]); });
    input.addEventListener('change', () => uploadPhotos([...input.files])); panel.append(input, upload);
  }
  const status = node('p', 'upload-status'); status.id = 'photo-upload-status'; status.hidden = true; panel.append(status);
  const grid = node('div', 'photo-grid');
  (state.finding.photos || []).forEach((photo, index, photos) => {
    const img = node('img'); img.src = safeUrl(photo.url, true); img.alt = photo.caption || `现场照片 ${index + 1}`; img.loading = 'lazy';
    const thumb = node('button', 'photo-thumb-button', img, node('span', 'photo-number', `照片 ${index + 1}`)); thumb.type = 'button'; thumb.setAttribute('aria-label', `放大${img.alt}`); thumb.onclick = () => showPhoto(photo);
    const caption = node('input'); caption.value = photo.caption || ''; caption.placeholder = '填写照片说明'; caption.setAttribute('aria-label', `照片 ${index + 1} 说明`); caption.maxLength = 1000; caption.disabled = isLocked();
    caption.addEventListener('change', () => runMutation(() => api(`/api/findings/${encodeURIComponent(state.finding.id)}/photos/${encodeURIComponent(photo.id)}`, { method: 'PATCH', body: { caption: caption.value } }), '照片说明已保存。'));
    const actions = node('div', 'button-row');
    actions.append(button('↑', () => movePhoto(photo, index - 1), 'quiet small', { disabled: isLocked() || index === 0, title: '照片上移', ariaLabel: '照片上移' }), button('↓', () => movePhoto(photo, index + 1), 'quiet small', { disabled: isLocked() || index === photos.length - 1, title: '照片下移', ariaLabel: '照片下移' }), button('删除', () => removePhoto(photo), 'danger-quiet small', { disabled: isLocked() }));
    grid.append(node('article', 'photo-card', thumb, node('div', 'photo-card-body', caption, node('div', 'photo-actions', node('span', 'filename', photo.filename || photo.id), actions))));
  });
  panel.append(grid);
  if (!(state.finding.photos || []).length && isLocked()) panel.append(node('p', 'subtle tiny', '此记录尚无现场照片。'));
}
function showPhoto(photo) { const img = $('#photo-preview'); img.src = safeUrl(photo.url, true); img.alt = photo.caption || '现场照片'; setText('#photo-preview-caption', photo.caption || photo.filename || '现场照片'); showDialog('#photo-dialog'); }
async function prepareCloudPhoto(file) {
  if (file.size > 20 * 1024 * 1024) throw new Error('单张照片不能超过 20 MB。');
  const source = URL.createObjectURL(file);
  let bitmap;
  try {
    bitmap = new Image();
    bitmap.src = source;
    await bitmap.decode();
    if (!bitmap.naturalWidth || !bitmap.naturalHeight || bitmap.naturalWidth * bitmap.naturalHeight > 40000000) throw new Error('照片尺寸无效或超过 4000 万像素。');
    const scale = Math.min(1, 2400 / Math.max(bitmap.naturalWidth, bitmap.naturalHeight));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(bitmap.naturalWidth * scale));
    canvas.height = Math.max(1, Math.round(bitmap.naturalHeight * scale));
    const context = canvas.getContext('2d');
    if (!context) throw new Error('浏览器无法处理照片，请换用支持图片处理的浏览器。');
    context.fillStyle = '#fff'; context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.9));
    canvas.width = 1; canvas.height = 1;
    if (!blob) throw new Error('照片处理失败，请重新选择照片。');
    return new File([blob], file.name.replace(/\.[^.]+$/, '') + '.jpg', {type: 'image/jpeg'});
  } finally { URL.revokeObjectURL(source); }
}
async function uploadPhotos(files) {
  if (!files.length || state.operation || isLocked()) return;
  const allowed = files.filter(file => ['image/jpeg', 'image/png', 'image/webp'].includes(file.type));
  if (allowed.length !== files.length) toast('部分文件格式不支持，仅接收 JPG、PNG、WebP。', 'warning');
  if (!allowed.length) return;
  await runMutation(async () => {
    let done = 0;
    for (const file of allowed) {
      const status = $('#photo-upload-status'); if (status) { status.hidden = false; status.textContent = `正在保存照片 ${done + 1} / ${allowed.length}…`; }
      const clean = document.documentElement.dataset.storage === 'cloud' ? await prepareCloudPhoto(file) : file;
      const form = new FormData(); form.append('file', clean, clean.name || file.name); form.append('caption', '');
      await api(`/api/findings/${encodeURIComponent(state.finding.id)}/photos`, { method: 'POST', body: form, timeout: 90000 }); done += 1;
    }
  }, `${allowed.length} 张照片已保存到当前记录。`);
}
async function movePhoto(photo, targetIndex) {
  const photos = state.finding.photos || [], other = photos[targetIndex]; if (!other) return;
  await runMutation(async () => {
    await api(`/api/findings/${encodeURIComponent(state.finding.id)}/photos/${encodeURIComponent(photo.id)}`, { method: 'PATCH', body: { position: other.position ?? targetIndex } });
    await api(`/api/findings/${encodeURIComponent(state.finding.id)}/photos/${encodeURIComponent(other.id)}`, { method: 'PATCH', body: { position: photo.position } });
  });
}
async function removePhoto(photo) {
  if (!await confirmAction('删除现场照片', '此照片将从当前记录移除。已生成的历史报告不受影响。', '删除照片')) return;
  await runMutation(() => api(`/api/findings/${encodeURIComponent(state.finding.id)}/photos/${encodeURIComponent(photo.id)}`, { method: 'DELETE' }), '照片已删除。');
}
function renderBasesPanel(panel) {
  panel.append(node('div', 'section-heading', node('div', '', node('h3', '', '已关联法规条款'), node('p', '', '条款以添加时的知识库版本形成快照。请核对条款、法源与适用场景。')), button('＋ 匹配法规', openKnowledgeSearch, 'primary small', { disabled: isLocked() })));
  const bases = state.finding.bases || [];
  if (!bases.length) { panel.append(node('div', 'empty-state', node('span', 'empty-symbol', '§'), node('h3', '', '还没有关联法规依据'), node('p', '', '使用现场原话检索，选择核查场景和条款。法规缺证或条件不足时，请保留待核实状态。'), button('检索法规条款', openKnowledgeSearch, 'secondary', { disabled: isLocked() }))); return; }
  const list = node('div', 'basis-list');
  bases.forEach(basis => {
    const heading = node('div', '', node('h4', '', basis.law_name || basis.lawName || '法规条款'), node('div', 'basis-article', basis.article || '条款编号待核实'));
    const card = node('article', 'basis-card', node('div', 'basis-card-top', heading, button('移除', () => removeBasis(basis), 'danger-quiet small', { disabled: isLocked() })), node('div', 'basis-document', basis.document_number || ''), node('div', 'basis-tags', node('span', 'chip', basis.hazard_id || ''), (basis.profile?.id || basis.profile_id) ? node('span', 'chip', basis.profile?.title || basis.profile_title || basis.profile?.id || basis.profile_id) : null), node('blockquote', 'quote', basis.text || basis.quote || '条款原文未提供'));
    if (basis.hazard_title) card.append(node('div', 'basis-scope', `核查参考：${basis.hazard_title}`));
    const applicability = readable(basis.applicability); if (applicability) card.append(node('div', 'basis-scope', `适用说明：${applicability}`));
    const scope = readable(basis.scope); if (scope) card.append(node('div', 'basis-scope', `适用范围：${scope}`));
    card.append(node('div', 'snapshot-meta', node('span', '', `法源快照 ${basis.as_of || '未标注'}`), node('span', '', `知识库 ${basis.data_version || '未标注'}`), node('span', '', basis.link_id || basis.clause_id || ''), sourceLink(basis.source_url)));
    list.append(card);
  });
  panel.append(list);
  if (state.finding.facts?.length) panel.append(node('div', 'notice compact warning', `已生成 ${state.finding.facts.length} 项核实要求。请前往“事实核实”逐条确认；当前条款关联不代表现场问题已成立。`));
}
async function removeBasis(basis) {
  if (!await confirmAction('移除法规依据', '将移除此条款快照；相关适用条件将由服务端重新计算，其他记录不受影响。', '移除条款')) return;
  await runMutation(() => api(`/api/findings/${encodeURIComponent(state.finding.id)}/bases/${encodeURIComponent(basis.id)}`, { method: 'DELETE' }), '条款已移除，请重新检查事实核实项。');
}
const KIND = { requirement: '适用前提', applicability: '适用前提', requires: '适用前提', scope: '适用范围', exclusion: '误判边界', excludes: '误判边界', boundary: '误判边界', evidence: '证据要求', fact: '现场事实', per_use: '本次现场事实', perUseFacts: '本次现场事实', generic: '适用性确认' };
function renderFactsPanel(panel) {
  panel.append(node('div', 'section-heading', node('div', '', node('h3', '', '逐条核实现场事实与适用条件'), node('p', '', '根据照片、测量和现场核验选择状态。没有证据时保持“待核实”，确认时须逐条填写核实说明，记录证据与核验过程。'))));
  const facts = state.factDraft;
  if (!facts.length) { panel.append(node('div', 'empty-state', node('span', 'empty-symbol', '○'), node('h3', '', '先关联适用的法规条款'), node('p', '', '选择核查场景后，系统会列出适用前提、现场事实和误判边界，供检查人员逐项核实。'), button('匹配法规', openKnowledgeSearch, 'secondary', { disabled: isLocked() }))); return; }
  const count = facts.filter(factSatisfied).length;
  const fill = node('span'); fill.style.width = `${count / facts.length * 100}%`; fill.id = 'facts-progress-fill';
  const summary = node('small', '', `${count} / ${facts.length} 项满足要求`); summary.id = 'facts-progress-text';
  panel.append(node('div', 'facts-summary', node('div', 'facts-progress', fill), summary));
  panel.append(node('div', 'notice compact info', '“不成立”表示该核查项不满足；“误判边界”项的确认表示已核对并遵守该边界。每一项都将进入审核记录。'));
  const fieldset = node('fieldset'); fieldset.dataset.factFieldset = ''; fieldset.disabled = isLocked();
  facts.forEach((fact, index) => {
    const expected = fact.expected || 'confirmed';
    const card = node('div', 'fact-card'); card.dataset.status = fact.status || 'unknown';
    card.append(node('div', 'fact-topline', node('span', 'fact-kind', `${String(index + 1).padStart(2, '0')} · ${KIND[fact.kind] || fact.kind || '核实要求'}`), node('span', 'fact-expected', `审核要求：${fact.allows_denied ? '核实或说明不适用' : expected === 'denied' ? '不成立' : '已确认'}`)), node('div', 'fact-label', fact.label || fact.key));
    const options = node('div', 'fact-status-options'); options.setAttribute('role', 'radiogroup'); options.setAttribute('aria-label', fact.label || fact.key);
    if (fact.allows_denied) card.append(node('p', 'conditional-fact-note', '此项仅在选用该分支或主张该事实时适用；未采用可选“不适用”，并填写核实说明。'));
    [['unknown', '待核实', '○'], ['confirmed', '已确认', '✓'], ['denied', fact.allows_denied ? '未采用 / 不适用' : '不成立', '×']].forEach(([status, label, mark]) => {
      const input = node('input'); input.type = 'radio'; input.name = `fact-${index}`; input.value = status; input.checked = fact.status === status; input.dataset.factKey = fact.key;
      input.addEventListener('change', () => { fact.status = status; card.dataset.status = status; state.factsDirty = true; state.factEpoch += 1; updateFactProgress(); queueSave(); });
      options.append(node('label', `fact-choice ${status}`, input, node('span', '', mark), label));
    });
    const note = node('textarea', 'fact-note'); note.rows = 2; note.value = fact.note || ''; note.maxLength = 4000; note.placeholder = fact.allows_denied ? '核实后必填：证据与核验过程，或说明未采用 / 不适用原因' : '确认时必填：证据、测量值、确认人；未知时可记录待补信息'; note.setAttribute('aria-label', `${fact.label || fact.key}的核实说明`);
    note.addEventListener('input', () => { fact.note = note.value; state.factsDirty = true; state.factEpoch += 1; updateFactProgress(); queueSave(); });
    card.append(options, node('label', 'fact-note-label', fact.allows_denied ? '核实说明（确认或不适用时必填）' : '核实说明（确认时必填）', note)); fieldset.append(card);
  });
  panel.append(fieldset);
}
function factSatisfied(fact) { return Boolean(fact.note?.trim()) && (fact.status === (fact.expected || 'confirmed') || (fact.allows_denied && fact.status === 'denied')); }
function updateFactProgress() {
  const count = state.factDraft.filter(factSatisfied).length;
  const fill = $('#facts-progress-fill'); if (fill) fill.style.width = `${count / Math.max(state.factDraft.length, 1) * 100}%`;
  setText('#facts-progress-text', `${count} / ${state.factDraft.length} 项满足要求`);
}
function blockerMessage(blocker) { return typeof blocker === 'string' ? blocker : blocker.message || blocker.label || blocker.reason || readable(blocker); }
function renderReviewPanel(panel) {
  const finding = state.finding;
  const descriptions = { draft: '完善现场记录、法规依据和核实项后，提交专业审核。', needs_facts: '仍有事实、适用条件或依据需要补充，当前不能形成确认结论。', pending_review: '检查记录已提交。专业人员应复核事实、适用条款、表述及整改建议。', confirmed: '此记录已由专业人员确认，可纳入审核报告。', rejected: '此记录已退回。请按审核意见补充或修订后再次提交。' };
  panel.append(node('div', 'review-status-card', node('span', 'review-state-icon', finding.status === 'confirmed' ? '✓' : finding.status === 'rejected' ? '↩' : '○'), node('div', '', node('h3', '', STATUS[finding.status] || '草稿'), node('p', '', descriptions[finding.status] || descriptions.draft))));
  const blockers = finding.blockers || [];
  if (blockers.length) panel.append(node('div', 'notice warning', node('strong', '', `还有 ${blockers.length} 项需要完成`), node('ul', '', blockers.map(blocker => node('li', '', blockerMessage(blocker))))));
  else if (finding.status !== 'confirmed') panel.append(node('div', 'notice compact', '系统核实项已满足。专业审核仍需核对现场实际、法规适用性、问题表述和整改建议。'));
  const form = node('form'); form.id = 'review-form';
  const name = node('input'); name.name = 'reviewer'; name.id = 'reviewer-name'; name.placeholder = '填写实际提交人或专业审核人'; name.maxLength = 200; name.required = true; name.autocomplete = 'name';
  const comment = node('textarea'); comment.name = 'comment'; comment.id = 'review-comment'; comment.rows = 3; comment.placeholder = '填写核查范围、审核意见，确认或退回时均须填写。'; comment.maxLength = 4000;
  form.append(node('div', 'form-grid', node('label', 'field full', node('span', '', '操作人 / 专业审核人', node('i', '', '必填')), name), node('label', 'field full', node('span', '', '审核意见', node('i', '', '确认 / 退回必填')), comment)));
  form.addEventListener('submit', event => event.preventDefault());
  const actions = node('div', 'review-actions');
  if (finding.status === 'pending_review') {
    actions.append(button('确认通过审核', () => review('confirm'), 'primary', { disabled: blockers.length > 0 }), button('退回补充', () => review('reject'), 'secondary'), button('重新打开记录', () => review('reopen'), 'quiet'));
  } else if (finding.status === 'confirmed') actions.append(button('重新打开并修订', () => review('reopen'), 'secondary'));
  else {
    actions.append(button('提交专业审核', () => review('submit'), 'primary', { disabled: blockers.length > 0 }));
    if (finding.status !== 'draft') actions.append(button('重新打开记录', () => review('reopen'), 'quiet'));
  }
  form.append(actions); panel.append(form);
  if (finding.status !== 'confirmed') panel.append(node('p', 'subtle tiny', '保存提交人和审核人姓名及意见，供项目内追溯；当前 MVP 保存项目内的审核记录，不能替代专业资格和正式签章。'));
  const history = node('section', 'review-history', node('h3', '', '审核与状态记录'));
  const reviews = finding.reviews || [];
  if (!reviews.length) history.append(node('p', 'subtle tiny', '尚无审核记录。'));
  else [...reviews].reverse().forEach(item => {
    const labels = { submit: '提交专业审核', confirm: '确认通过审核', reject: '退回补充', reopen: '重新打开记录' };
    const heading = node('div', 'history-heading', node('strong', '', `${labels[item.decision] || item.action || item.decision || '更新记录'} · ${item.reviewer || item.actor || '未署名'}`), node('time', '', timeText(item.created_at || item.timestamp || item.at)));
    history.append(node('article', 'history-item', heading, item.comment ? node('p', '', item.comment) : null));
  });
  panel.append(history);
  const audit = node('details', 'audit-history', node('summary', '', '操作审计记录'));
  const content = node('div', 'audit-content'); audit.append(content);
  audit.addEventListener('toggle', async () => {
    if (!audit.open || audit.dataset.loaded) return;
    content.replaceChildren(node('p', 'subtle tiny', '正在读取操作记录…'));
    try {
      const items = listOf(await api(`/api/findings/${encodeURIComponent(finding.id)}/audit`), 'audit');
      content.replaceChildren();
      [...items].reverse().forEach(item => content.append(node('div', 'audit-item', node('strong', '', auditLabel(item.action)), node('span', '', `${item.actor || '工作区操作人'} · ${timeText(item.created_at)}`))));
      if (!items.length) content.append(node('p', 'subtle tiny', '暂无操作记录。'));
      audit.dataset.loaded = 'true';
    } catch (error) { content.replaceChildren(node('p', 'form-error', errorText(error))); }
  });
  panel.append(audit);
}
function auditLabel(action) { return ({finding_created:'新建记录',finding_updated:'修改记录',finding_copied:'复制草稿',facts_updated:'保存事实核实',basis_added:'关联法规条款',basis_removed:'移除法规条款',photo_added:'添加照片',photo_updated:'更新照片',photo_removed:'移除照片',review_submit:'提交专业审核',review_confirm:'确认审核',review_reject:'退回补充',review_reopen:'重开记录'})[action] || action || '更新记录'; }
async function review(decision) {
  const form = $('#review-form');
  if (!form.reportValidity()) return;
  const reviewer = $('#reviewer-name').value.trim(), comment = $('#review-comment').value.trim();
  if (!reviewer) { toast('请填写实际操作人或审核人姓名。', 'warning'); $('#reviewer-name').focus(); return; }
  if (['confirm', 'reject'].includes(decision) && !comment) { toast('确认或退回时请填写具体审核意见。', 'warning'); $('#review-comment').focus(); return; }
  const messages = { submit: '已提交专业审核。', confirm: '专业审核已确认，此记录可纳入审核报告。', reject: '记录已退回，请补充核实。', reopen: '记录已重新打开，修改后需再次审核。' };
  await runMutation(() => api(`/api/findings/${encodeURIComponent(state.finding.id)}/review`, { method: 'POST', body: { decision, reviewer, comment, revision: state.finding.revision } }), messages[decision]);
  await refreshProjects().catch(() => {});
}
async function createFinding() {
  if (!state.project || state.operation) return;
  try {
    await flushChanges(); state.operation = true;
    const result = unwrap(await api(`/api/projects/${encodeURIComponent(state.project.id)}/findings`, { method: 'POST', body: { observation: '', location: '', equipment: '', description: '', rectification: '' } }), 'finding');
    const id = result.id || result.finding_id; if (!id) throw new Error('服务未返回新记录编号。');
    state.findings = listOf(await api(`/api/projects/${encodeURIComponent(state.project.id)}/findings`), 'findings');
    initializeDraft(unwrap(await api(`/api/findings/${encodeURIComponent(id)}`), 'finding')); state.tab = 'record'; state.filter = 'all'; renderMain(); rememberSelection(); await refreshProjects();
    $('[data-field="location"]')?.focus();
  } catch (error) { toast(errorText(error), 'error'); } finally { state.operation = false; }
}
async function copyFinding() {
  if (!state.finding || state.operation) return;
  try {
    await flushChanges(); state.operation = true;
    const result = unwrap(await api(`/api/findings/${encodeURIComponent(state.finding.id)}/copy`, { method: 'POST' }), 'finding');
    const id = result.id || result.finding_id;
    state.findings = listOf(await api(`/api/projects/${encodeURIComponent(state.project.id)}/findings`), 'findings');
    initializeDraft(unwrap(await api(`/api/findings/${encodeURIComponent(id)}`), 'finding')); state.tab = 'record'; state.filter = 'all'; renderMain(); rememberSelection(); await refreshProjects(); toast('已复制为新草稿，请按本次现场情况重新核实。');
  } catch (error) { toast(errorText(error), 'error'); } finally { state.operation = false; }
}
async function moveFinding(direction) {
  if (!state.finding || state.operation) return;
  const index = state.findings.findIndex(f => f.id === state.finding.id), other = state.findings[index + direction]; if (!other) return;
  try {
    await flushChanges();
    state.operation = true;
    const originalPosition = state.finding.position;
    await api(`/api/findings/${encodeURIComponent(state.finding.id)}`, { method: 'PATCH', body: { position: other.position ?? index + direction, revision: state.finding.revision } });
    await api(`/api/findings/${encodeURIComponent(other.id)}`, { method: 'PATCH', body: { position: originalPosition, revision: other.revision } });
    state.findings = listOf(await api(`/api/projects/${encodeURIComponent(state.project.id)}/findings`), 'findings'); await reloadCurrent();
  } catch (error) { toast(errorText(error), 'error'); } finally { state.operation = false; }
}
async function deleteFinding() {
  if (!state.finding || state.finding.status !== 'draft' || state.operation) return;
  if (!await confirmAction('删除此草稿记录', '将删除该草稿及其关联照片。请确认当前记录不再需要；需要保留时可先导出完整备份。', '删除草稿')) return;
  try {
    await flushChanges(); await api(`/api/findings/${encodeURIComponent(state.finding.id)}`, { method: 'DELETE' });
    state.finding = null; state.dirty = false; state.factsDirty = false; await refreshProjects(); await openProject(state.project.id); toast('草稿记录已删除。');
  } catch (error) { toast(errorText(error), 'error'); }
}
function openProjectDialog(project = null) {
  state.projectEditing = project?.id || null;
  const form = $('#project-form'); form.reset(); $('#project-form-error').hidden = true;
  const now = new Date(); const date = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  ['company', 'name', 'inspection_date', 'inspectors', 'purpose'].forEach(key => { form.elements[key].value = key === 'inspection_date' ? project?.[key] || date : readable(project?.[key]); });
  setText('#project-dialog-title', project ? '编辑检查项目' : '新建检查项目'); setText('#project-submit', project ? '保存项目' : '创建项目'); showDialog('#project-dialog');
}
async function submitProject(event) {
  event.preventDefault(); const form = event.currentTarget; if (!form.reportValidity()) return;
  const submit = $('#project-submit'); submit.disabled = true; $('#project-form-error').hidden = true;
  try {
    await flushChanges();
    const payload = Object.fromEntries(['company', 'name', 'inspection_date', 'inspectors', 'purpose'].map(key => [key, form.elements[key].value.trim()]));
    if (!payload.company || !payload.name) throw new Error('请填写企业名称和项目名称。');
    const contextChanged = !!state.projectEditing && ['company', 'name', 'inspection_date', 'inspectors', 'purpose'].some(key => payload[key] !== (state.project?.[key] || ''));
    const result = unwrap(await api(state.projectEditing ? `/api/projects/${encodeURIComponent(state.projectEditing)}` : '/api/projects', { method: state.projectEditing ? 'PATCH' : 'POST', body: payload }), 'project');
    const projectId = result.id || result.project_id || state.projectEditing;
    const findingId = state.project?.id === projectId ? state.finding?.id : null;
    $('#project-dialog').close(); await refreshProjects(); await openProject(projectId, findingId); toast(state.projectEditing ? (contextChanged && state.findings.length ? '项目条件变更，记录需重新核实。' : '项目已更新。') : '项目已创建，开始添加现场记录。');
  } catch (error) { setText('#project-form-error', errorText(error)); $('#project-form-error').hidden = false; }
  finally { submit.disabled = false; }
}
async function loadDemo() {
  const source = $('#load-demo'); source.disabled = true;
  try {
    await flushChanges(); const result = await api('/api/demo', { method: 'POST', timeout: 90000 });
    const project = unwrap(result, 'project'); const id = project.id || result.project_id;
    await refreshProjects(); if (id) await openProject(id); else if (state.projects[0]) await openProject(state.projects[0].id);
    toast('已打开完全合成的脱敏样例，可试用记录、照片、核实、审核与报告导出。', 'success', 8000);
  } catch (error) { toast(errorText(error), 'error'); } finally { source.disabled = false; }
}
async function downloadBackup() {
  try { await flushChanges(); } catch { return; }
  toast('备份包含工作区项目、照片和报告，请保存在受控位置。', 'warning', 8500);
  const link = downloadLink('下载备份', '/api/backup'); document.body.append(link); link.click(); link.remove();
}
async function openKnowledgeSearch() {
  if (!state.finding || isLocked()) return;
  try { await flushChanges(); } catch { return; }
  $('#knowledge-query').value = [state.draft.equipment, state.draft.observation].filter(Boolean).join(' ').slice(0, 1000);
  showDialog('#search-dialog'); $('#knowledge-query').focus();
  if ($('#knowledge-query').value.trim()) searchKnowledge();
}
function guidanceText(guidance) {
  if (!guidance) return '';
  if (typeof guidance === 'string' || Array.isArray(guidance)) return readable(guidance);
  const parts = [guidance.notice, guidance.suggestions, guidance.title, guidance.message, guidance.text, guidance.summary, guidance.explanation, guidance.warning, guidance.warnings, guidance.questions, guidance.missingFacts, guidance.requiredFacts].map(readable).filter(Boolean);
  return [...new Set(parts)].join(' · ');
}
const SEARCH_ASSESSMENTS = {
  candidate_matches: ['找到候选条款', '检索到相关条目，需继续核对具体场景、适用范围和现场事实。'],
  needs_conditions: ['条件不足，待核实', '现场问法中的适用条件或对象信息仍需补充。'],
  evidence_gap: ['法源缺证，待补证', '现有知识库缺少足以直接支持本次问题的对题依据。'],
  fact_unconfirmed: ['现场事实未确认', '保留原话中的否定、已完成或尚未核实状态，不推定存在缺陷。'],
  no_result: ['暂无匹配结果', '本次问法没有检索到匹配条目，可补充具体对象和实际现象。'],
};
const SEARCH_REASONS = {
  retrieval_candidates: '检索结果属于待核对的候选条款',
  no_retrieval_match: '当前问法未检索到匹配条目',
  unconfirmed_observation: '现场观察或检测事实尚未确认',
  negated_completed_or_unconfirmed: '原话包含否定、已完成或尚未核实状态',
  extinguisher_access_observation: '灭火器周边堆物对识别和取用的影响尚需核实',
  cylinder_ring_source_gap: '气瓶防震圈的对题法源不足',
  ordinary_chemical_identity: '物料身份、危险性和储存条件尚需核实',
  emergency_lighting_absent: '应急照明的应设条件尚需核实',
  fire_door_object: '门的类型、用途和实际状态尚需核实',
  fire_document_review: '消防检测实施情况与资料保存情况需分别核查',
  training_document_review: '培训实施情况与记录缺项需分别核查',
  equipment_document_review: '设备检验情况与报告保存情况需分别核查',
  gauge_verification_state: '压力表检定有效期与所属设备范围尚需核实',
  gauge_damage_state: '压力表实际损坏与所属设备范围尚需核实',
  socket_in_service_source_gap: '插座使用期缺陷的对题法源不足',
  industrial_floor_source_gap: '普通工业场所地面油污的对题法源不足',
  floor_scene_unconfirmed: '场所用途和实际滑跌风险尚需核实',
};
function renderSearchGuidance(response) {
  const target = $('#search-guidance');
  const assessment = response.assessment && typeof response.assessment === 'object' ? response.assessment : null;
  const guidance = guidanceText(response.guidance);
  target.replaceChildren();
  target.classList.toggle('warning', Boolean(guidance || (assessment && assessment.classification !== 'candidate_matches')));
  delete target.dataset.classification; delete target.dataset.reason;
  if (assessment) {
    const classification = String(assessment.classification || '');
    const [label, fallback] = SEARCH_ASSESSMENTS[classification] || ['检索条件待核对', '请核对具体对象、现场事实和条款适用范围。'];
    const reason = readable(assessment.reason);
    const reasonText = SEARCH_REASONS[reason] || (/\p{Script=Han}/u.test(reason) ? reason : readable(response.guidance?.notice)) || fallback;
    target.dataset.classification = classification;
    target.dataset.reason = reason;
    target.append(node('strong', 'search-assessment-label', label), node('p', 'search-assessment-reason', `评估原因：${reasonText}`));
    if (guidance && guidance !== reasonText) target.append(node('p', 'search-assessment-notice', guidance));
    const requiredFacts = [...new Set((Array.isArray(assessment.requiredFacts) ? assessment.requiredFacts : assessment.requiredFacts ? [assessment.requiredFacts] : []).map(readable).filter(Boolean))];
    if (requiredFacts.length) target.append(node('div', 'search-required-facts', node('strong', '', '还需逐项核实'), node('ul', '', requiredFacts.map(fact => node('li', '', fact)))));
  } else if (guidance) target.append(node('p', '', guidance));
  target.append(node('p', 'search-candidate-note', `检索到 ${response.total ?? state.searchResults.length} 项核查参考。候选结果不确认现场隐患，选用后仍须逐项核实并经专业审核。`));
}
async function searchKnowledge(event) {
  event?.preventDefault(); const query = $('#knowledge-query').value.trim();
  if (!query) { $('#knowledge-query').focus(); return; }
  const request = ++state.queryRequest;
  const submit = $('#knowledge-search-form button'); submit.disabled = true; submit.textContent = '检索中…';
  setText('#search-guidance', '正在核对现场问法、适用条件和法源…');
  $('#search-guidance').classList.remove('warning');
  delete $('#search-guidance').dataset.classification; delete $('#search-guidance').dataset.reason;
  $('#knowledge-results').replaceChildren(node('div', 'empty-state small', node('span', 'spinner'), node('p', '', '正在检索现有知识库…')));
  state.selectedHazard = null;
  $('#knowledge-detail').replaceChildren(node('div', 'detail-placeholder', node('span', 'empty-symbol', '§'), node('p', '', '选择检索结果，核对适用条件与条款原文')));
  try {
    const response = await api(`/api/knowledge/search?q=${encodeURIComponent(query)}`);
    if (request !== state.queryRequest) return;
    state.searchResults = listOf(response, 'items');
    renderSearchGuidance(response);
    renderKnowledgeResults();
  } catch (error) { if (request === state.queryRequest) { setText('#search-guidance', '检索未完成，请重试。'); $('#knowledge-results').replaceChildren(node('div', 'notice error', errorText(error))); } }
  finally { if (request === state.queryRequest) { submit.disabled = false; submit.textContent = '检索'; } }
}
function renderKnowledgeResults() {
  const target = $('#knowledge-results'); target.replaceChildren();
  if (!state.searchResults.length) {
    target.append(node('div', 'empty-state small', node('span', 'empty-symbol', '⌕'), node('h3', '', '暂无可匹配的正式条款'), node('p', '', '可以补充设备、场所和实际现象后再次检索。法源不足时，保留待补证状态。'))); return;
  }
  state.searchResults.forEach(item => {
    const id = item.id || item.hazard_id || item.hazardId;
    const result = node('button', `knowledge-result ${state.selectedHazard === id ? 'active' : ''}`, node('span', 'id', id || ''), node('strong', '', item.title || item.hazard_title || '核查参考'));
    result.type = 'button'; result.dataset.hazardId = id;
    if (item.description || item.summary) result.append(node('small', '', readable(item.description || item.summary).slice(0, 180)));
    const meta = node('div', 'result-meta');
    if (item.category) meta.append(node('span', 'chip', readable(item.category)));
    if (item.inspectionClass || item.inspectionClasses?.length) meta.append(node('span', 'chip', readable(item.inspectionClass || item.inspectionClasses)));
    if (item.fieldProfiles?.length) meta.append(node('span', 'chip', `${item.fieldProfiles.length} 个核查场景`));
    result.append(meta); result.onclick = () => openHazard(id); target.append(result);
  });
}
async function openHazard(id) {
  state.selectedHazard = id; renderKnowledgeResults(); const target = $('#knowledge-detail');
  target.replaceChildren(node('div', 'detail-placeholder', node('span', 'spinner'), node('p', '', '正在读取条款与场景…')));
  try {
    const detail = await api(`/api/knowledge/hazards/${encodeURIComponent(id)}`);
    if (state.selectedHazard !== id) return;
    renderHazardDetail(detail, id);
  } catch (error) { target.replaceChildren(node('div', 'notice error', errorText(error))); }
}
function conditionBlock(title, values) {
  if (!values || (Array.isArray(values) && !values.length)) return null;
  const list = Array.isArray(values) ? values : [values];
  return node('div', 'condition-group', node('strong', '', title), node('ul', '', list.map(value => node('li', '', readable(value)))));
}
function renderHazardDetail(detail, id) {
  const target = $('#knowledge-detail'); target.replaceChildren();
  const hazard = detail.hazard || detail, bases = detail.bases || [], profiles = detail.profiles || [];
  target.append(node('span', 'eyebrow', id), node('h3', '', hazard.title || '核查参考'));
  if (hazard.description) target.append(node('p', 'hazard-reference', hazard.description));
  if (hazard.conditions) target.append(node('div', 'notice compact warning', node('strong', '', '适用条件'), node('p', '', readable(hazard.conditions))));
  const profilePanel = node('div', 'profile-panel', node('h4', '', '选择本次核查场景'));
  const select = node('select'); select.id = 'profile-select'; select.setAttribute('aria-label', '选择本次核查场景');
  const placeholder = node('option', '', '请选择与现场相符的场景'); placeholder.value = ''; select.append(placeholder);
  profiles.forEach(profile => { const option = node('option', '', `${profile.title || profile.id}${profile.defaultFieldEntry === 'exclude' ? '（边界参考）' : ''}`); option.value = profile.id; select.append(option); });
  const generic = node('option', '', '仅核对通用条件（未选择具体场景）'); generic.value = '__generic__'; select.append(generic);
  if (!profiles.length) select.value = '__generic__';
  const profileContent = node('div'); profileContent.id = 'profile-content';
  const renderProfile = () => {
    profileContent.replaceChildren(); const profile = profiles.find(item => item.id === select.value);
    if (profile) {
      profileContent.append(...[conditionBlock('适用前提', profile.applicability?.requires), conditionBlock('误判边界', profile.applicability?.excludes), conditionBlock('证据要求', profile.evidenceRequirements)].filter(Boolean));
      const perUseCount = profile.applicability?.perUseFacts?.length || 0;
      if (perUseCount) profileContent.append(node('p', 'subtle tiny', `关联后将显示 ${perUseCount} 项本次现场事实核查要求。请在事实核实页逐项确认适用情况并记录核实说明。`));
      if (profile.correctiveDirection) profileContent.append(node('p', 'subtle tiny', `整改方向参考：${readable(profile.correctiveDirection)}`));
      if (profile.defaultFieldEntry === 'exclude') profileContent.append(node('div', 'notice compact warning', '此场景属于排除或边界参考，请先确认其用途和适用范围，不能直接形成隐患结论。'));
    } else if (select.value === '__generic__') profileContent.append(node('p', 'subtle tiny', '将采用通用适用性核实要求。具体条件不足时，请继续补充现场事实或选择对应场景。'));
    else profileContent.append(node('p', 'subtle tiny', '不同场景可能互斥，请明确选择一个；选择后仍需逐项核实。'));
    updateAddButton();
  };
  profilePanel.append(select, profileContent); target.append(profilePanel, node('h4', '', '选择需要关联的正式条款'));
  const chosen = new Set();
  bases.forEach((basis, index) => {
    const ref = basis.ref || basis, clause = basis.clause || {}, law = basis.law || {};
    const linkId = ref.linkId || ref.link_id || basis.link_id || ref.id;
    const check = node('input'); check.type = 'checkbox'; check.checked = true; check.value = linkId || '';
    check.setAttribute('aria-label', `${law.name || '法规'} ${clause.article || '条款'}关联选择`);
    if (linkId) chosen.add(linkId);
    check.addEventListener('change', () => { if (check.checked) chosen.add(linkId); else chosen.delete(linkId); updateAddButton(); });
    const content = node('div', '', node('h4', '', law.name || basis.law_name || '法规条款'), node('div', 'basis-document', law.documentNumber || basis.document_number || ''), node('div', 'basis-article', clause.article || basis.article || ''), node('blockquote', 'quote', clause.quote || clause.text || basis.text || '条款原文未提供'), sourceLink(basis.sourceUrl || clause.sourceUrl || basis.source_url));
    if (ref.applicability) content.append(node('p', 'subtle tiny', readable(ref.applicability)));
    const choice = node('label', 'law-choice', check, content); target.append(choice);
  });
  if (!bases.length) target.append(node('div', 'notice warning', '此参考场景暂无可关联的正式法源。请保留待补证记录，不能据此确认隐患。'));
  const add = button('关联所选条款', async () => {
    if (!chosen.size || !select.value || isLocked()) return;
    add.disabled = true; add.textContent = '正在保存快照…';
    const payload = { hazard_id: id, link_ids: [...chosen] };
    if (select.value !== '__generic__') payload.profile_id = select.value;
    const result = await runMutation(() => api(`/api/findings/${encodeURIComponent(state.finding.id)}/bases`, { method: 'POST', body: payload }), '条款快照已关联，请逐条核实对应条件和现场事实。');
    add.textContent = '关联所选条款'; updateAddButton();
    if (result !== undefined) { $('#search-dialog').close(); state.tab = 'facts'; renderEditor(); }
  }, 'primary');
  function updateAddButton() { add.disabled = !chosen.size || !select.value || isLocked(); }
  select.addEventListener('change', renderProfile);
  const actions = node('div', 'detail-actions', add, node('span', 'subtle tiny', '保存条款版本快照，现场事实保持待核实。'));
  target.append(actions);
  if (detail.meta?.as_of || detail.meta?.data_version) target.append(node('p', 'subtle tiny', `知识库 ${detail.meta.data_version || ''} · 法源基准 ${detail.meta.as_of || ''}`));
  renderProfile(); updateAddButton();
}
async function openReports() {
  if (!state.project) return;
  try { await flushChanges(); } catch { return; }
  setText('#report-project-name', `${state.project.company} · ${state.project.name}`);
  $('#report-body').replaceChildren(node('div', 'empty-state small', node('span', 'spinner'), node('p', '', '正在读取报告记录…')));
  showDialog('#report-dialog');
  try { state.reports = listOf(await api(`/api/projects/${encodeURIComponent(state.project.id)}/reports`), 'reports'); renderReportBody(); }
  catch (error) { $('#report-body').replaceChildren(node('div', 'notice error', errorText(error))); }
}
function renderReportBody(latest = null) {
  const body = $('#report-body'); body.replaceChildren(); const count = counters();
  const form = node('form'); form.id = 'report-form';
  const modes = node('div', 'report-modes');
  [['confirmed', '审核报告', `纳入 ${count.confirmed} 条已确认记录；其他 ${count.total - count.confirmed} 条不进入结论。`], ['draft', '草稿报告', `保留 ${count.total} 条记录及其状态，带草稿标识，用于内部核查与补证。`]].forEach(([value, title, description]) => {
    const input = node('input'); input.type = 'radio'; input.name = 'mode'; input.value = value; input.checked = value === (count.confirmed ? 'confirmed' : 'draft');
    modes.append(node('label', 'report-mode', input, node('div', '', node('strong', '', title), node('small', '', description))));
  });
  form.append(modes, node('div', 'notice compact info', '报告包含项目概况、现场问题、紧随其后的隐患照片、法规条款、整改建议及审核信息。采用可替换模板；本机版还可使用自有 Word 母版。'));
  const generate = node('button', 'button primary', '生成 Word / PDF'); generate.type = 'submit';
  const hint = node('span', 'subtle tiny', '生成后文件保存在工作区，并列入下方历史记录。');
  const result = node('div'); result.id = 'report-result';
  form.append(node('div', 'button-row', generate, hint), result);
  form.addEventListener('submit', async event => {
    event.preventDefault(); generate.disabled = true; generate.textContent = '正在生成报告…'; result.replaceChildren();
    const mode = new FormData(form).get('mode');
    if (mode === 'confirmed' && !count.confirmed) { result.append(node('div', 'notice warning', '当前没有已确认记录。请完成专业审核，或选择草稿报告。')); generate.disabled = false; generate.textContent = '生成 Word / PDF'; return; }
    try {
      await flushChanges(); const report = await api(`/api/projects/${encodeURIComponent(state.project.id)}/reports`, { method: 'POST', body: { mode }, timeout: 180000 });
      state.reports = listOf(await api(`/api/projects/${encodeURIComponent(state.project.id)}/reports`), 'reports'); renderReportBody(unwrap(report, 'report')); toast('Word / PDF 报告已生成。');
    } catch (error) { result.append(node('div', 'notice error', errorText(error))); generate.disabled = false; generate.textContent = '生成 Word / PDF'; }
  });
  body.append(form);
  if (latest) {
    const output = node('div', 'report-result', node('h3', '', latest.mode === 'draft' ? '草稿报告已生成' : '审核报告已生成'), node('p', '', `${latest.excluded_count ? `已排除 ${latest.excluded_count} 条尚未确认记录。` : ''}Word 和 PDF 已保存在工作区，可下载用于复核。`), node('div', 'button-row', downloadLink('↓ Word 报告', latest.docx_url, 'primary'), downloadLink('↓ PDF 报告', latest.pdf_url, 'secondary'), downloadLink('数据快照', latest.snapshot_url, 'quiet')));
    body.append(output);
  }
  const history = node('section', 'report-history-list', node('h3', '', `报告历史 · ${state.reports.length}`));
  if (!state.reports.length) history.append(node('p', 'subtle tiny', '还没有生成报告。每次导出都会保留独立版本。'));
  else state.reports.forEach(report => {
    history.append(node('article', 'report-history-item', node('div', '', node('strong', '', report.mode === 'draft' ? '草稿报告' : '审核报告'), node('small', '', `${timeText(report.created_at || report.generated_at)}${report.findings_count !== undefined ? ` · ${report.findings_count} 条记录` : ''}`)), node('div', 'button-row', downloadLink('Word', report.docx_url), downloadLink('PDF', report.pdf_url), downloadLink('快照', report.snapshot_url, 'quiet small'))));
  });
  body.append(history);
}
function renderBootError(error) {
  $('#main').replaceChildren(node('section', 'load-error', node('span', 'eyebrow', 'CONNECTION REQUIRED'), node('h1', '', '暂时无法打开检查工作区'), node('p', '', errorText(error)), node('p', '', '请检查登录状态和网络连接；若使用本机版，请确认工作台服务仍在运行。'), button('重新连接', initialize, 'primary')));
  setText('#local-status', '服务连接待恢复'); $('.online-dot')?.classList.add('offline');
}
async function initialize() {
  try {
    const [projects, meta, health] = await Promise.allSettled([api('/api/projects'), api('/api/knowledge/meta'), api('/api/health')]);
    if (projects.status === 'rejected') throw projects.reason;
    if (health.status === 'rejected') throw health.reason;
    state.projects = listOf(projects.value, 'projects');
    if (meta.status === 'fulfilled') state.meta = meta.value;
    if (health.status === 'fulfilled' && health.value?.demo) setText('#local-status', '脱敏样例工作区');
    else setText('#local-status', health.value?.deployment === 'private-cloud' ? (health.value?.viewer?.source === 'chatgpt' ? '已登录 · 私有云工作区' : '私有云工作区') : '本机私有工作区');
    document.documentElement.dataset.storage = health.status === 'fulfilled' && health.value?.deployment === 'private-cloud' ? 'cloud' : 'local';
    setText('.privacy-pill', document.documentElement.dataset.storage === 'cloud' ? '● 登录保护 · 私有存储' : '● 本机存储');
    $('#account-session')?.remove();
    if (health.value?.deployment === 'private-cloud' && health.value?.viewer?.source === 'chatgpt') {
      const account = node('div', 'notice info', node('strong', '', '当前登录'), node('p', '', health.value.viewer.display_name));
      account.id = 'account-session';
      const signOut = node('a', 'button quiet small', '退出登录');
      signOut.href = '/signout-with-chatgpt?return_to=%2F'; signOut.target = '_top';
      account.append(signOut); $('#help-dialog .help-content').append(account);
    }
    $('.online-dot')?.classList.remove('offline');
    const version = state.meta.data_version || state.meta.dataVersion || state.meta.version || '当前正式知识库';
    const asOf = state.meta.as_of || state.meta.asOf || state.meta.sourceAsOf;
    setText('#knowledge-version', `知识库 ${version}${asOf ? ` · 法源基准 ${asOf}` : ''}`);
    setText('#footer-version', `Safety Basis · ${version}`);
    renderProjectList();
    const requested = requestedSelection();
    if (requested.project && state.projects.some(p => p.id === requested.project)) await openProject(requested.project, requested.finding);
    else { state.project = null; state.finding = null; renderMain(); }
  } catch (error) { renderBootError(error); }
}
$$('.close-dialog').forEach(close => close.addEventListener('click', () => closeDialog(close)));
$$('dialog').forEach(dialog => dialog.addEventListener('click', event => { if (event.target !== dialog) return; const rect = dialog.getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close(); }));
$('#new-project').addEventListener('click', () => openProjectDialog());
$('#project-form').addEventListener('submit', submitProject);
$('#project-filter').addEventListener('input', renderProjectList);
$('#load-demo').addEventListener('click', loadDemo);
$('#backup-button').addEventListener('click', downloadBackup);
$('#menu-button').addEventListener('click', () => setMobileMenu(!$('#sidebar').classList.contains('open')));
$('#sidebar-backdrop').addEventListener('click', () => setMobileMenu(false));
$('#help-button').addEventListener('click', () => showDialog('#help-dialog'));
$('#knowledge-search-form').addEventListener('submit', searchKnowledge);
$('.brand').addEventListener('click', async event => { event.preventDefault(); try { await flushChanges(); state.project = null; state.finding = null; renderProjectList(); renderMain(); rememberSelection(); setMobileMenu(false); } catch {} });
window.addEventListener('beforeunload', event => { if (state.dirty || state.factsDirty || state.savePromise) { event.preventDefault(); event.returnValue = ''; } });
document.addEventListener('keydown', event => { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') { event.preventDefault(); flushChanges().then(() => toast('当前记录已保存。')).catch(() => {}); } });
initialize();
