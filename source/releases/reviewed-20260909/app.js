'use strict';
import {DataStore} from './js/store.js';
import {searchHazards,searchLaws} from './js/search.js';

const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const MAX_RENDER=120;
const state={view:'hazards',selectedHazard:'',selectedLaw:'',query:'',store:null,results:[]};

function toast(text){const el=$('#toast');el.textContent=text;el.classList.add('show');clearTimeout(window.__toast);window.__toast=setTimeout(()=>el.classList.remove('show'),2800)}
function setBusy(text='加载中…'){$('#detail').innerHTML=`<div class="empty"><span class="spinner" aria-hidden="true"></span><strong>${esc(text)}</strong></div>`}
function download(name,text,type='application/json'){const a=document.createElement('a');const blob=new Blob([text],{type});a.href=URL.createObjectURL(blob);a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1500)}
async function copyText(text,msg='已复制'){try{await navigator.clipboard.writeText(text);toast(msg)}catch{const t=document.createElement('textarea');t.value=text;document.body.append(t);t.select();const ok=document.execCommand('copy');t.remove();toast(ok?msg:'复制失败')}}
function option(v){return `<option>${esc(v)}</option>`}
function statusClass(v){return /失效|废止/.test(v)?'red':/待核|条件|兜底|即将/.test(v)?'amber':''}
function pill(text,extra=''){return `<span class="pill ${statusClass(text)} ${extra}">${esc(text)}</span>`}
function currentFilters(){return state.view==='hazards'?{category:$('#category').value,place:$('#place').value,level:$('#level').value,region:$('#region').value,mode:$('#mode').value,status:$('#status').value}:{level:$('#lawLevel').value,region:$('#lawRegion').value,status:$('#lawStatus').value}}

function loadUrlState(){const p=new URLSearchParams(location.search);state.view=['hazards','laws','data'].includes(p.get('view'))?p.get('view'):'hazards';state.query=p.get('q')||'';state.selectedHazard=p.get('id')||'';state.selectedLaw=p.get('law')||''}
function syncUrl(){const p=new URLSearchParams();if(state.view!=='hazards')p.set('view',state.view);if(state.query)p.set('q',state.query);if(state.view==='hazards'&&state.selectedHazard)p.set('id',state.selectedHazard);if(state.view==='laws'&&state.selectedLaw)p.set('law',state.selectedLaw);history.replaceState(null,'',`${location.pathname}${p.size?'?'+p.toString():''}${location.hash}`)}

function initFilters(){const t=state.store.taxonomy;
  $('#category').innerHTML='<option value="">全部主题</option>'+t.categories.map(option).join('');
  $('#place').innerHTML='<option value="">全部场所</option>'+t.places.map(option).join('');
  $('#level').innerHTML='<option value="">全部法规类别</option>'+t.lawLevels.map(option).join('');
  $('#mode').innerHTML='<option value="">全部匹配类型</option>'+t.hazardModes.map(option).join('');
  $('#status').innerHTML='<option value="">有效条目</option>'+t.hazardStatuses.map(option).join('');
  $('#lawLevel').innerHTML='<option value="">全部法规类别</option>'+t.lawLevels.map(option).join('');
  $('#lawStatus').innerHTML='<option value="">有效法规</option>'+t.lawStatuses.map(option).join('');
}

function switchView(view,{keepQuery=false}={}){
  state.view=view;if(!keepQuery)state.query='';
  $$('.nav').forEach(x=>x.classList.toggle('active',x.dataset.view===view));
  $('#searchView').hidden=view==='data';$('#dataView').hidden=view!=='data';
  $('#hazardFilters').hidden=view!=='hazards';$('#lawFilters').hidden=view!=='laws';
  $('#search').value=state.query;
  if(view==='hazards'){$('#search').placeholder='搜索隐患、现场现象、关键词或法规，如：配电箱门跨接、灭火器失压…';$('#sectionTitle').textContent='隐患速查';$('#sectionHint').textContent='现场问题 → 专业描述 → 直接依据 → 整改措施';}
  if(view==='laws'){$('#search').placeholder='搜索法规、标准、条款号，如：安全生产法、GB 55036…';$('#sectionTitle').textContent='法规库';$('#sectionHint').textContent='法规标准 → 收录条款 → 反查关联隐患';}
  if(view==='data')renderDataView();else renderResults();
  syncUrl();
}

function renderResults(){
  state.query=$('#search').value.trim();
  const filters=currentFilters();
  const rows=state.view==='hazards'?searchHazards(state.store.searchIndex,state.query,filters):searchLaws(state.store.lawIndex,state.query,filters);
  state.results=rows;
  $('#count').textContent=rows.length;
  $('#summary').textContent=rows.length>MAX_RENDER?`显示相关度最高的前 ${MAX_RENDER} 条`:(state.view==='hazards'?'选择隐患查看完整依据':'选择法规查看收录条款与关联隐患');
  $('#list').innerHTML=rows.length?rows.slice(0,MAX_RENDER).map(state.view==='hazards'?hazardCard:lawCard).join(''):'<div class="empty"><strong>没有找到匹配内容</strong><p>可缩短关键词、清除筛选，或在后续资料整理时补入数据库。</p></div>';
  if(state.view==='hazards'){
    if(!rows.some(x=>x.id===state.selectedHazard)) state.selectedHazard=rows[0]?.id||'';
    $$('.card').forEach(el=>el.onclick=()=>selectHazard(el.dataset.id));
    renderHazardDetail();
  }else{
    if(!rows.some(x=>x.id===state.selectedLaw)) state.selectedLaw=rows[0]?.id||'';
    $$('.card').forEach(el=>el.onclick=()=>selectLaw(el.dataset.id));
    renderLawDetail();
  }
  syncUrl();
}

function hazardCard(r){return `<button class="card ${r.id===state.selectedHazard?'selected':''}" data-id="${esc(r.id)}" aria-pressed="${r.id===state.selectedHazard}"><div class="meta"><span>${esc(r.id)} · ${esc(r.category)}</span>${pill(r.status==='已核验'?r.mode:r.status)}</div><h3>${esc(r.title)}</h3><p>${esc(r.places.join(' / '))}</p><span class="arrow">↗</span></button>`}
function lawCard(r){return `<button class="card ${r.id===state.selectedLaw?'selected':''}" data-id="${esc(r.id)}" aria-pressed="${r.id===state.selectedLaw}"><div class="meta"><span>${esc(r.id)} · ${esc(r.level)}</span>${pill(r.status)}</div><h3>${esc(r.name)}</h3><p>${esc(r.scope)} · ${r.clauseCount} 条收录条款 · 关联 ${r.hazardCount} 条隐患</p><span class="arrow">↗</span></button>`}

function selectHazard(id){state.selectedHazard=id;renderResults()}
function selectLaw(id){state.selectedLaw=id;renderResults()}

async function renderHazardDetail(){
  const index=state.store.searchIndex.find(x=>x.id===state.selectedHazard);
  if(!index){$('#detail').innerHTML='<div class="empty"><strong>选择一个隐患查看详情</strong></div>';return}
  setBusy('正在读取隐患详情');
  try{
    const {hazard,bases}=await state.store.getHazardDetail(index);
    $('#detail').innerHTML=`<div class="detailtop"><div class="topline"><span class="eyebrow">${esc(hazard.id)} / ${esc(hazard.category)}</span>${pill(hazard.status==='已核验'?hazard.mode:hazard.status)}</div><h2>${esc(hazard.title)}</h2><div class="subtitle">${esc(hazard.places.join(' · '))}<br>核验状态：${esc(hazard.status)} · ${esc(hazard.checked||'未填写日期')} · 数据库版本 ${esc(state.store.manifest.dataVersion)}</div></div><div class="detailbody"><section class="block"><h3><span class="number">01</span>隐患专业描述</h3><p>${esc(hazard.description)}</p></section><section class="block"><h3><span class="number">02</span>法规原文依据 <small>${bases.length} 条</small></h3>${bases.map(basisHtml).join('')}</section><section class="block"><h3><span class="number">03</span>整改措施</h3><p>${esc(hazard.measures)}</p></section><section class="block note"><h3>ⓘ 适用说明 / 兜底条件</h3><p>${esc(hazard.note)}</p></section></div><div class="detailactions"><button class="primary" id="copy">复制整改条目</button><button id="copyfull">复制完整资料</button><button id="share">复制当前链接</button></div>`;
    $('#copy').onclick=()=>copyText(hazardText(hazard,bases),'已复制整改条目');
    $('#copyfull').onclick=()=>copyText(hazardFullText(hazard,bases),'已复制完整资料');
    $('#share').onclick=()=>copyText(location.href,'已复制当前链接');
    $$('.lawjump').forEach(b=>b.onclick=()=>{state.selectedLaw=b.dataset.law;switchView('laws',{keepQuery:false})});
  }catch(err){showError(err)}
}

function basisHtml({ref,clause,law,sourceUrl}){return `<div class="basis"><div class="basismeta"><span>${pill(ref.role)}</span><span class="article">${esc(law.level)} · ${esc(law.scope)} · ${esc(law.status)}</span></div><h4>${esc(law.name)}</h4><span class="article">${esc(clause.article)} · 条款核验 ${esc(clause.checked||'待核')}</span><blockquote>${esc(clause.quote||'尚未录入原文，请核验后补充。')}</blockquote><div class="basislinks">${sourceUrl?`<a href="${esc(sourceUrl)}" target="_blank" rel="noopener noreferrer">查看来源原文 ↗</a>`:'<span class="article">来源待补充</span>'}<button class="linkbutton lawjump" data-law="${esc(law.id)}">在法规库查看</button></div></div>`}
function hazardText(h,bases){return `${h.title}\n\n隐患专业描述：\n${h.description}\n\n法规依据：\n${bases.map(x=>`《${x.law.name}》${x.clause.article}\n${x.clause.quote}`).join('\n\n')}\n\n整改措施：\n${h.measures}`}
function hazardFullText(h,bases){return `${hazardText(h,bases)}\n\n适用说明 / 兜底条件：\n${h.note}\n\n核验状态：${h.status}；核验日期：${h.checked||'未填写'}；数据库版本：${state.store.manifest.dataVersion}。`}

async function renderLawDetail(){
  const law=state.store.lawIndex.find(x=>x.id===state.selectedLaw);
  if(!law){$('#detail').innerHTML='<div class="empty"><strong>选择一部法规或标准查看详情</strong></div>';return}
  setBusy('正在读取法规条款');
  try{
    const detail=await state.store.getLawDetail(law);
    const related=[...new Set(detail.clauses.flatMap(x=>x.ref.hazardIds))].map(id=>state.store.searchIndex.find(h=>h.id===id)).filter(Boolean);
    $('#detail').innerHTML=`<div class="detailtop"><div class="topline"><span class="eyebrow">${esc(law.id)} / ${esc(law.level)}</span>${pill(law.status)}</div><h2>${esc(law.name)}</h2><div class="subtitle">适用范围：${esc(law.scope)} · 核验日期：${esc(law.checked||'未填写')} · 本库收录 ${law.clauseCount} 个条款 / 关联 ${law.hazardCount} 条隐患</div></div><div class="detailbody"><section class="block lawmeta"><h3><span class="number">01</span>法规状态</h3><div class="metagrid"><div><span>效力状态</span><strong>${esc(law.status)}</strong></div><div><span>实施日期</span><strong>${esc(law.effectiveDate||'未录入')}</strong></div><div><span>地区</span><strong>${esc(law.scope)}</strong></div><div><span>数据库核验</span><strong>${esc(law.checked||'待核')}</strong></div></div>${law.sourceUrl?`<a class="sourcecta" href="${esc(law.sourceUrl)}" target="_blank" rel="noopener noreferrer">打开来源原文 ↗</a>`:''}</section><section class="block"><h3><span class="number">02</span>本库已收录条款</h3>${detail.clauses.map(({ref,clause})=>lawClauseHtml(ref,clause)).join('')}</section><section class="block"><h3><span class="number">03</span>关联隐患 <small>${related.length} 条</small></h3><div class="related">${related.map(h=>`<button class="relateditem hazardjump" data-id="${esc(h.id)}"><span>${esc(h.id)}</span>${esc(h.title)}</button>`).join('')||'<p>暂无关联隐患。</p>'}</div></section></div><div class="detailactions"><button class="primary" id="copylaw">复制法规资料</button><button id="share">复制当前链接</button></div>`;
    $('#copylaw').onclick=()=>copyText(lawText(detail),'已复制法规资料');
    $('#share').onclick=()=>copyText(location.href,'已复制当前链接');
    $$('.hazardjump').forEach(b=>b.onclick=()=>{state.selectedHazard=b.dataset.id;switchView('hazards',{keepQuery:false})});
  }catch(err){showError(err)}
}
function lawClauseHtml(ref,c){return `<div class="basis"><div class="basismeta"><strong class="articletitle">${esc(c.article)}</strong>${pill(c.status)}</div><blockquote>${esc(c.quote||'原文待核验')}</blockquote><div class="article">核验日期：${esc(c.checked||'未填写')} · 关联 ${ref.hazardIds.length} 条隐患</div></div>`}
function lawText({law,clauses}){return `${law.name}\n效力状态：${law.status}\n适用范围：${law.scope}\n来源：${law.sourceUrl||'待补'}\n\n${clauses.map(x=>`${x.clause.article}\n${x.clause.quote}`).join('\n\n')}`}

function renderDataView(){
  const m=state.store.manifest,h=m.health;
  $('#dataView').innerHTML=`<div class="datahead"><span class="eyebrow">DATABASE / V2</span><h2>数据库状态与维护</h2><p>公开站点只保存经过整理的知识数据；企业报告、现场照片和未脱敏资料继续放在你的私有资料源，不直接上传到公开仓库。</p></div><div class="stats"><div><span>隐患</span><strong>${m.counts.hazards}</strong><small>${h.verifiedHazards} 条已核验</small></div><div><span>法规 / 标准</span><strong>${m.counts.laws}</strong><small>${h.activeLaws} 部现行有效</small></div><div><span>条款</span><strong>${m.counts.clauses}</strong><small>${m.counts.links} 个关联关系</small></div><div><span>数据版本</span><strong class="version">${esc(m.dataVersion)}</strong><small>${esc(m.generatedAt)} 构建</small></div></div><div class="maintgrid"><section><h3>数据架构</h3><p><b>母库：</b>隐患、法规、条款、关联关系分开保存，Excel 提供查看和编辑入口，法规原文不在每条隐患中重复复制。</p><p><b>运行层：</b>首页只加载轻量搜索索引；点击结果后再按需加载对应分片，数据量增长时不会让所有正文一次进入手机内存。</p><p><b>版本控制：</b>每次更新通过 GitHub Commit 留痕，可比较、回滚；网站显示数据库版本和核验日期。</p></section><section><h3>报告入库流程</h3><ol><li>报告 / 检查表留在私有资料源。</li><li>提取候选隐患、法规和整改语料。</li><li>与现有库去重、拆分、合并并核验现行法规。</li><li>将审阅结果更新母库，自动校验并生成网站数据。</li><li>审阅发布预览和增减清单，再更新正式网站。</li></ol></section></div><div class="dataactions"><button class="primary" id="refreshData">重新加载最新数据库</button><button id="exportSource">导出当前公开数据</button><button id="clearCache">清除离线缓存</button><a class="buttonlink" href="https://github.com/An-0726/safety-basis" target="_blank" rel="noopener noreferrer">打开 GitHub 仓库 ↗</a></div><div class="health"><span class="dot good"></span><strong>当前发布包校验</strong><span>引用关系错误 ${h.invalidReferences} · 公开待核隐患 ${h.pendingHazards} · 公开待核法规 ${h.pendingLaws}；此处不统计私有母库待办</span></div>`;
  $('#refreshData').onclick=()=>location.reload();
  $('#exportSource').onclick=async()=>{try{toast('正在导出公开数据…');const bundle=await state.store.exportPublicBundle();download(`安全隐患法规库_公开快照_${m.dataVersion}_ChatGPT.json`,JSON.stringify({schemaVersion:2,dataVersion:m.dataVersion,exportedAt:new Date().toISOString(),...bundle},null,2));toast('公开数据已导出')}catch(e){showError(e)}};
  $('#clearCache').onclick=clearOfflineCache;
}

async function clearOfflineCache(){try{if('caches' in window){for(const k of await caches.keys())if(k.startsWith('safety-basis-'))await caches.delete(k)}state.store.clearMemoryCache();toast('离线缓存已清除')}catch(e){showError(e)}}
function showError(err){console.error(err);$('#detail').innerHTML=`<div class="empty error"><strong>数据读取失败</strong><p>${esc(err?.message||err)}</p><button id="retry">重新加载</button></div>`;$('#retry')?.addEventListener('click',()=>location.reload())}

function bind(){
  $$('.nav[data-view]').forEach(b=>b.onclick=()=>switchView(b.dataset.view));
  $('#search').oninput=()=>{state.query=$('#search').value;renderResults()};
  $('#clear').onclick=()=>{$('#search').value='';state.query='';renderResults();$('#search').focus()};
  $('#reset').onclick=()=>{$$('#hazardFilters select,#lawFilters select').forEach(x=>x.value='');$('#search').value='';state.query='';renderResults()};
  $$('#hazardFilters select,#lawFilters select').forEach(x=>x.onchange=renderResults);
  document.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();if(state.view==='data')switchView('hazards');$('#search').focus()}});
}

async function boot(){
  loadUrlState();bind();
  try{
    state.store=await new DataStore('.').init();
    initFilters();
    $('#dbVersion').textContent=`数据 ${state.store.manifest.dataVersion}`;
    $('#dbDate').textContent=state.store.manifest.generatedAt;
    $('#search').value=state.query;
    switchView(state.view,{keepQuery:true});
    if('serviceWorker' in navigator) navigator.serviceWorker.register('./sw.js').catch(()=>{});
  }catch(err){showError(err);$('#list').innerHTML='<div class="empty"><strong>数据库未能初始化</strong></div>'}
}

boot();
