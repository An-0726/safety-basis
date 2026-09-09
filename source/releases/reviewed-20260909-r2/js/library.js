import {normalizeText, queryGrams, intersectDocuments, matchingParagraphs} from './fulltext-search.js';
import {VerifiedFiles} from './verified-files.js';

const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const BASE = 'data/fulltext/';
const cache = new Map();
const verifiedFiles = new VerifiedFiles();
let catalog, index, sequence = 0, selected = '';

async function read(path) {
  if (!/^(catalog|search-index)\.json$|^texts\/[A-Za-z0-9_-]+\.json$|^grams\/[0-9a-f]{2}\.json$/.test(path)) throw new Error('目录中的文件路径无效');
  if (!cache.has(path)) {
    cache.set(path, verifiedFiles.read(BASE + path).catch(error => { cache.delete(path); throw error; }));
  }
  return cache.get(path);
}

function officialLink(url, title = '查看官方来源 ↗') {
  try { if (!['https:', 'http:'].includes(new URL(url).protocol)) return ''; } catch { return ''; }
  return `<a class="sourcecta" href="${esc(url)}" target="_blank" rel="noopener noreferrer">${title}</a>`;
}

function statusLabel(status) {
  return status === '即将生效' ? '已发布 · 尚未实施' : status;
}

function versionNotice(doc) {
  const current = catalog.documents.filter(other => other.lawId === doc.lawId && other.versionId !== doc.versionId && other.status === '现行有效');
  const message = (doc.status === '即将生效' ? `<p><strong>已发布 · 尚未实施</strong>：将于 ${esc(doc.effectiveDate)} 实施，可提前查阅和准备。</p>` : '') +
    (doc.validityNote ? `<p><strong>版本说明：</strong>${esc(doc.validityNote)}</p>` : '');
  const links = current.map(other => `<a class="sourcecta" href="?document=${encodeURIComponent(other.versionId)}">查看现行版：${esc(other.title)} →</a>`).join('');
  return message || links ? `<section class="block">${message}${links}</section>` : '';
}

async function candidateIds(query) {
  const grams = queryGrams(query);
  if (!grams.length || !index.gramShards) return null;
  const lists = await Promise.all(grams.map(async gram => {
    const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(gram));
    const prefix = new Uint8Array(hash)[0].toString(16).padStart(2, '0');
    const path = index.gramShards[prefix];
    if (!path) return [];
    const shard = await read(path);
    if (shard.schemaVersion !== 'safety-public-fulltext-grams-v1') throw new Error('不支持的全文索引格式');
    return shard.grams[gram] || [];
  }));
  return intersectDocuments(lists);
}

function snippet(text, query) {
  const offset = text.toLowerCase().indexOf(query.toLowerCase());
  const start = Math.max(0, offset - 35);
  return (start ? '…' : '') + text.slice(start, start + 155) + (text.length > start + 155 ? '…' : '');
}

function paintResults(results, query, total, failures = 0) {
  $('#libraryResults').replaceChildren();
  $('#libraryResultCount').textContent = `${query ? `${total} 处匹配` : `${total} 份法规`} · 显示 ${results.length} 项${failures ? `；${failures} 份正文读取失败，可重试搜索` : ''}`;
  for (const {doc, paragraph} of results) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'library-hit' + (doc.versionId === selected ? ' selected' : '');
    button.innerHTML = `<strong>${esc(doc.title)}</strong><small>${doc.textMode === 'full_text' ? '已收全文' : '官方链接'} · ${esc(statusLabel(doc.status))} · ${esc(doc.effectiveDate)} 施行</small>${paragraph ? `<p>${esc(snippet(paragraph.text, query))}</p>` : ''}`;
    button.addEventListener('click', () => showDocument(doc, paragraph?.location));
    $('#libraryResults').append(button);
  }
  if (!results.length) $('#libraryResults').innerHTML = '<div class="empty"><strong>当前收录范围内没有匹配结果</strong><p>可缩短关键词，或到法规库查看已收条款及官方来源。</p></div>';
}

async function search() {
  const turn = ++sequence;
  const query = $('#textQuery').value.trim();
  const mode = $('#coverage').value, version = $('#documentFilter').value, validity = $('#validityFilter').value;
  let docs = catalog.documents.filter(doc => (!mode || doc.textMode === mode) && (!version || doc.versionId === version) && (!validity || doc.status === validity));
  const url = new URL(location.href);
  query ? url.searchParams.set('q', query) : url.searchParams.delete('q');
  history.replaceState(null, '', url);
  if (!query) { paintResults(docs.map(doc => ({doc})), '', docs.length); return; }
  $('#libraryResultCount').textContent = '正在检索已收全文…';
  $('#libraryResults').replaceChildren();
  try {
    const ids = await candidateIds(query);
    if (turn !== sequence) return;
    docs = docs.filter(doc => normalizeText(doc.title).includes(normalizeText(query)) ||
      (doc.textMode === 'full_text' && (!ids || ids.has(doc.versionId))));
    const results = [];
    let total = 0, failures = 0;
    for (let start = 0; start < docs.length; start += 4) {
      const batch = await Promise.allSettled(docs.slice(start, start + 4).map(async doc => {
        const paragraphs = doc.textMode === 'full_text' ? matchingParagraphs((await read(doc.textPath)).paragraphs, query) : [];
        return {doc, paragraphs};
      }));
      if (turn !== sequence) return;
      for (const result of batch) {
        if (result.status === 'rejected') { failures++; continue; }
        const {doc, paragraphs} = result.value;
        if (paragraphs.length) {
          total += paragraphs.length;
          for (const paragraph of paragraphs) if (results.length < 80) results.push({doc, paragraph});
        } else if (normalizeText(doc.title).includes(normalizeText(query))) {
          total++;
          if (results.length < 80) results.push({doc});
        }
      }
    }
    paintResults(results, query, total, failures);
  } catch (error) {
    if (turn === sequence) $('#libraryResultCount').textContent = `检索未完成：${error.message}。请重试。`;
  }
}

async function showDocument(doc, hitLocation = '') {
  selected = doc.versionId;
  $('#libraryDetail').innerHTML = '<div class="empty"><strong>正在读取原文</strong></div>';
  const url = new URL(location.href); url.searchParams.set('document', selected); history.replaceState(null, '', url);
  try {
    const text = doc.textMode === 'full_text' ? await read(doc.textPath) : null;
    if (selected !== doc.versionId) return;
    $('#libraryDetail').innerHTML = `<div class="detailtop"><div class="eyebrow">${doc.textMode === 'full_text' ? '已收全文' : '官方链接'}</div><h2>${esc(doc.title)}</h2><p class="library-meta">${esc(statusLabel(doc.status))} · ${esc(doc.effectiveDate)} 施行<br>目录核验基准：${esc(catalog.asOf)}${text ? ` · ${text.paragraphs.length} 个原文段落` : ''}</p></div><div class="detailbody">${versionNotice(doc)}<section class="block">${officialLink(doc.officialUrl)}<a class="sourcecta" href="./?view=laws&amp;law=${encodeURIComponent(doc.versionId)}">查看收录条款与关联隐患 →</a></section><section class="block" id="textBody"></section></div>`;
    if (!text) { $('#textBody').textContent = '本库尚未公开此文件的全文，请通过官方入口查阅。'; return; }
    const body = $('#textBody');
    let cursor = hitLocation ? Math.max(0, text.paragraphs.findIndex(row => row.location === hitLocation) - 2) : 0;
    if (cursor > 0) {
      const top = document.createElement('button'); top.textContent = '从全文开头阅读';
      top.addEventListener('click', () => showDocument(doc)); body.append(top);
    }
    const more = document.createElement('button'); more.className = 'library-more';
    const append = () => {
      more.remove();
      const end = Math.min(text.paragraphs.length, cursor + 100);
      for (; cursor < end; cursor++) {
        const row = text.paragraphs[cursor];
        const section = document.createElement('section');
        section.className = 'library-article' + (row.location === hitLocation ? ' hit' : '');
        const p = document.createElement('p'); p.textContent = row.text;
        section.append(p); body.append(section);
      }
      if (cursor < text.paragraphs.length) {
        more.textContent = `继续阅读（剩余 ${text.paragraphs.length - cursor} 段）`; body.append(more);
      }
    };
    more.addEventListener('click', append); append();
    if (hitLocation) $('#textBody .hit')?.scrollIntoView({block:'nearest'});
  } catch (error) {
    if (selected === doc.versionId) $('#libraryDetail').innerHTML = `<div class="empty"><strong>原文读取失败</strong><p>${esc(error.message)}</p></div>`;
  }
}

async function boot() {
  try {
    await verifiedFiles.init({required:true});
    [catalog, index] = await Promise.all([read('catalog.json'), read('search-index.json')]);
    if (catalog.schemaVersion !== 'safety-public-fulltext-v1' || index.schemaVersion !== 'safety-public-fulltext-search-v1') throw new Error('不支持的目录格式');
    const full = catalog.documents.filter(doc => doc.textMode === 'full_text').length;
    $('#libraryDate').textContent = `核验基准 ${catalog.asOf}`;
    $('#coverageSummary').textContent = `${full} 份已收全文 · ${catalog.documents.length - full} 份官方链接 · 持续补充收录`;
    for (const doc of catalog.documents) {
      const option = document.createElement('option'); option.value = doc.versionId; option.textContent = doc.title; $('#documentFilter').append(option);
    }
    const params = new URLSearchParams(location.search);
    $('#textQuery').value = params.get('q') || '';
    $('#librarySearch').addEventListener('submit', event => { event.preventDefault(); search(); });
    $('#coverage').addEventListener('change', search); $('#documentFilter').addEventListener('change', search); $('#validityFilter').addEventListener('change', search);
    $('#clearTextQuery').addEventListener('click', () => { $('#textQuery').value = ''; search(); });
    await search();
    const doc = catalog.documents.find(doc => doc.versionId === params.get('document'));
    if (doc) showDocument(doc);
  } catch (error) {
    $('#libraryDate').textContent = '全文包未就绪';
    $('#coverageSummary').textContent = '当前站点尚未发布全文数据包';
    $('#libraryResultCount').textContent = '全文目录暂不可用';
    $('#libraryResults').innerHTML = `<div class="empty"><strong>全文数据尚未就绪</strong><p>隐患和已收条款仍可通过原入口查询。</p><a href="./?view=laws">前往法规库 →</a></div>`;
    $('#libraryDetail').innerHTML = `<div class="empty"><p>${esc(error.message)}</p></div>`;
  }
}

boot();
