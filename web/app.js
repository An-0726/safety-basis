'use strict';
import {DataStore} from './js/store.js';
import {searchHazards,searchLaws} from './js/search.js';

const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const MAX_RENDER=120;
const state={view:'hazards',selectedHazard:'',selectedLaw:'',query:'',store:null,results:[],visibleCount:MAX_RENDER,pendingDetailScroll:false};

export function createDetailRequestGuard(getCurrentState){
  if(typeof getCurrentState!=='function') throw new TypeError('getCurrentState must be a function');
  let sequence=0;
  const begin=(view,selectedId)=>Object.freeze({sequence:++sequence,view,selectedId:selectedId??''});
  const invalidate=()=>++sequence;
  const isCurrent=token=>{
    if(!token||token.sequence!==sequence) return false;
    const current=getCurrentState()||{};
    return current.view===token.view&&(current.selectedId??'')===token.selectedId;
  };
  return {begin,invalidate,isCurrent};
}

const detailRequests=createDetailRequestGuard(()=>({
  view:state.view,
  selectedId:state.view==='hazards'?state.selectedHazard:state.selectedLaw,
}));

function toast(text){const el=$('#toast');el.textContent=text;el.classList.add('show');clearTimeout(window.__toast);window.__toast=setTimeout(()=>el.classList.remove('show'),2800)}
function setBusy(text='加载中…'){$('#detail').innerHTML=`<div class="empty"><span class="spinner" aria-hidden="true"></span><strong>${esc(text)}</strong></div>`}
function download(name,text,type='application/json'){const a=document.createElement('a');const blob=new Blob([text],{type});a.href=URL.createObjectURL(blob);a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1500)}
async function copyText(text,msg='已复制'){try{await navigator.clipboard.writeText(text);toast(msg)}catch{const t=document.createElement('textarea');t.value=text;document.body.append(t);t.select();const ok=document.execCommand('copy');t.remove();toast(ok?msg:'复制失败')}}
function option(v){return `<option value="${esc(v)}">${esc(v)}</option>`}
function optionPair(value,label){return `<option value="${esc(value)}">${esc(label)}</option>`}
function statusClass(v){return /失效|废止/.test(v)?'red':/待核|条件|兜底|即将/.test(v)?'amber':''}
function lawStatusLabel(status){return status==='即将生效'?'已发布 · 尚未实施':status}
function pill(text,extra=''){return `<span class="pill ${statusClass(text)} ${extra}">${esc(lawStatusLabel(text))}</span>`}
function displayHazardId(id){const s=String(id||'');if(/^H\d+$/.test(s))return s;if(s.length<=18)return s;return `${s.slice(0,10)}…${s.slice(-5)}`}
function dateOnly(value){const text=String(value??'');return text?text.slice(0,10):'未填写'}
function dataDateOf(manifest={},releaseManifest={}){
  // Prefer the deployment manifest's explicit asOf; generatedAt is only a legacy fallback.
  const explicit=releaseManifest?.asOf||manifest?.asOf;
  if(explicit)return dateOnly(explicit);
  return manifest?.generatedAt?dateOnly(manifest.generatedAt):'未提供';
}
function setDataDateHeader(manifest,releaseManifest){
  const dataDate=dataDateOf(manifest,releaseManifest);
  if($('#dbVersion'))$('#dbVersion').textContent=`数据日期 ${dataDate}`;
  if($('#dbDate'))$('#dbDate').textContent=dataDate;
  return dataDate;
}
function modeLabel(value){return ({direct:'直接适用',conditional:'有条件适用'})[value]||value||'未标注'}
function roleLabel(value){return ({direct:'直接依据',supporting:'辅助依据'})[value]||value||'未标注'}
function displayCategoryOf(row){return row.displayCategory??row.category??''}
function displayLevelOf(row){return row.displayLevel??row.level??''}
function currentFilters(){return state.view==='hazards'?{category:$('#category').value,sceneTag:$('#scene').value,displayLevel:$('#level').value,level:$('#level').value,region:$('#region').value,mode:$('#mode').value}:{displayLevel:$('#lawLevel').value,level:$('#lawLevel').value,region:$('#lawRegion').value,status:$('#lawStatus').value}}

function loadUrlState(){const p=new URLSearchParams(location.search);state.view=['hazards','laws','data'].includes(p.get('view'))?p.get('view'):'hazards';state.query=p.get('q')||'';state.selectedHazard=p.get('id')||'';state.selectedLaw=p.get('law')||''}
function syncUrl(){const p=new URLSearchParams();if(state.view!=='hazards')p.set('view',state.view);if(state.query)p.set('q',state.query);if(state.view==='hazards'&&state.selectedHazard)p.set('id',state.selectedHazard);if(state.view==='laws'&&state.selectedLaw)p.set('law',state.selectedLaw);history.replaceState(null,'',`${location.pathname}${p.size?'?'+p.toString():''}${location.hash}`)}

function initFilters(){const t=state.store.taxonomy;
  const categories=t.displayCategories||t.categories||[];
  const levels=t.displayLevels||t.lawLevels||[];
  const scenes=t.sceneTagOptions||[];
  const modes=t.hazardModes||[];
  $('#category').innerHTML='<option value="">全部主题</option>'+categories.map(option).join('');
  $('#scene').innerHTML='<option value="">全部适用场景</option>'+(scenes.length?scenes.map(value=>optionPair(value,value==='未细分场景'?'未细分场景':'适用：'+value)).join(''):'');
  $('#level').innerHTML='<option value="">全部依据类型</option>'+levels.map(option).join('');
  $('#mode').innerHTML='<option value="">全部适用方式</option>'+modes.map(value=>optionPair(value,modeLabel(value))).join('');
  $('#lawLevel').innerHTML='<option value="">全部依据类型</option>'+levels.map(option).join('');
  $('#lawStatus').innerHTML='<option value="">全部已核验版本</option>'+t.lawStatuses.map(status=>`<option value="${esc(status)}">${esc(lawStatusLabel(status))}</option>`).join('');
}

function switchView(view,{keepQuery=false,initial=false}={}){
  state.view=view;state.visibleCount=MAX_RENDER;state.pendingDetailScroll=false;if(!keepQuery)state.query='';
  $$('.nav').forEach(x=>x.classList.toggle('active',x.dataset.view===view));
  $('#searchView').hidden=view==='data';$('#dataView').hidden=view!=='data';
  $('#hazardFilters').hidden=view!=='hazards';$('#lawFilters').hidden=view!=='laws';
  $('#search').value=state.query;
  if(view==='hazards'){$('#search').placeholder='搜索隐患、现场现象、关键词或法规，如：配电箱门跨接、灭火器失压…';$('#sectionTitle').textContent='隐患速查';$('#sectionHint').textContent='现场问题 → 专业描述 → 直接依据 → 整改措施';}
  if(view==='laws'){$('#search').placeholder='搜索法规、标准、条款号，如：安全生产法、GB 55036…';$('#sectionTitle').textContent='法规库';$('#sectionHint').textContent='法规标准 → 收录条款 → 反查关联隐患';}
  if(view==='data'){
    detailRequests.invalidate();
    renderDataView();
  }else renderResults({mode:initial?'initial':'view-change'});
  syncUrl();
}

function resolveSelectedId(rows,currentId,mode,allRows){
  if(mode==='initial'&&currentId&&!allRows.some(x=>x.id===currentId))return currentId;
  if(!rows.length)return '';
  if(mode==='filter-change'||mode==='view-change'||!currentId)return rows[0].id;
  const knownSelection=allRows.some(x=>x.id===currentId);
  const visibleSelection=rows.some(x=>x.id===currentId);
  if(knownSelection&&!visibleSelection)return rows[0].id;
  return currentId;
}

function renderResults({mode='normal'}={}){
  const list=$('#list');
  const filterChanged=mode==='filter-change';
  const viewChanged=mode==='view-change';
  const initialDeepLink=mode==='initial';
  const previousScrollTop=filterChanged||viewChanged?0:(list?.scrollTop||0);
  if(filterChanged||viewChanged){state.visibleCount=MAX_RENDER;state.pendingDetailScroll=false;}
  state.query=$('#search').value.trim();
  const filters=currentFilters();
  updateFilterSummary();
  const rows=state.view==='hazards'?searchHazards(state.store.searchIndex,state.query,filters):searchLaws(state.store.lawIndex,state.query,filters);
  state.results=rows;
  if(state.view==='hazards'){
    state.selectedHazard=resolveSelectedId(rows,state.selectedHazard,mode,state.store.searchIndex);
    const selectedIndex=rows.findIndex(x=>x.id===state.selectedHazard);
    if(initialDeepLink&&selectedIndex>=state.visibleCount)state.visibleCount=Math.ceil((selectedIndex+1)/MAX_RENDER)*MAX_RENDER;
  }else{
    state.selectedLaw=resolveSelectedId(rows,state.selectedLaw,mode,state.store.lawIndex);
    const selectedIndex=rows.findIndex(x=>x.id===state.selectedLaw);
    if(initialDeepLink&&selectedIndex>=state.visibleCount)state.visibleCount=Math.ceil((selectedIndex+1)/MAX_RENDER)*MAX_RENDER;
  }
  const shownRows=rows.slice(0,state.visibleCount);
  $('#count').textContent=rows.length;
  $('#summary').textContent=rows.length
    ? `已展示 ${shownRows.length} / ${rows.length}；${state.view==='hazards'?'选择隐患查看完整依据':'选择法规查看收录条款与关联隐患'}`
    : '可缩短关键词、清除筛选，或在后续资料整理时补入数据库。';
  const empty=rows.length?'':'<div class="empty"><strong>没有找到匹配内容</strong><p>可缩短关键词、清除筛选，或在后续资料整理时补入数据库。</p></div>';
  const more=shownRows.length<rows.length?`<button type="button" id="loadMore" class="loadmore">加载更多（再显示 ${Math.min(MAX_RENDER,rows.length-shownRows.length)} 条）</button>`:'';
  list.innerHTML=rows.length?shownRows.map(state.view==='hazards'?hazardCard:lawCard).join('')+more:empty;
  list.scrollTop=previousScrollTop;
  if($('#loadMore'))$('#loadMore').onclick=()=>{state.visibleCount=Math.min(rows.length,state.visibleCount+MAX_RENDER);renderResults({mode:'pagination'})};
  if(state.view==='hazards'){
    $$('.card').forEach(el=>el.onclick=()=>selectHazard(el.dataset.id));
    if(state.selectedHazard&&state.store.searchIndex.some(x=>x.id===state.selectedHazard))renderHazardDetail();
    else if(state.selectedHazard)renderUnavailable(state.selectedHazard,'隐患');
    else renderHazardDetail();
  }else{
    $$('.card').forEach(el=>el.onclick=()=>selectLaw(el.dataset.id));
    if(state.selectedLaw&&state.store.lawIndex.some(x=>x.id===state.selectedLaw))renderLawDetail();
    else if(state.selectedLaw)renderUnavailable(state.selectedLaw,'法规版本');
    else renderLawDetail();
  }
  syncUrl();
}

function renderUnavailable(id,kind){
  detailRequests.invalidate();
  $('#detail').innerHTML=`<div class="empty"><strong>此${esc(kind)}未在当前已核验库中发布</strong><p>链接编号：${esc(id)}</p><p>可能尚待核验、已撤下或编号有误。请从列表选择其他内容，或搜索已核验的依据。</p></div>`
}

function hazardCard(r){return `<button class="card ${r.id===state.selectedHazard?'selected':''}" data-id="${esc(r.id)}" aria-pressed="${r.id===state.selectedHazard}"><div class="meta"><span>${esc(displayCategoryOf(r))}</span>${pill(r.status==='已核验'?modeLabel(r.mode):r.status)}</div><h3>${esc(r.title)}</h3><p>${esc((r.sceneTags||r.places||[]).join(' · ')||'未细分场景')}</p><span class="arrow">↗</span></button>`}
function lawCard(r){return `<button class="card ${r.id===state.selectedLaw?'selected':''}" data-id="${esc(r.id)}" aria-pressed="${r.id===state.selectedLaw}"><div class="meta"><span>${esc(displayLevelOf(r))}</span>${pill(r.status)}</div><h3>${esc(r.name)}</h3><p>${esc(r.scope)} · ${r.clauseCount} 条收录条款 · 关联 ${r.hazardCount} 条隐患</p><span class="arrow">↗</span></button>`}

function selectHazard(id){state.selectedHazard=id;state.pendingDetailScroll=true;renderResults({mode:'selection'})}
function selectLaw(id){state.selectedLaw=id;state.pendingDetailScroll=true;renderResults({mode:'selection'})}

function technicalInfoHtml({id,checked,places=[]}){
  const placeText=places.length?places.join('；'):'未填写/不适用';
  return `<details class="record-info"><summary>条目信息</summary><div class="record-grid"><div><span>完整 ID</span><strong>${esc(id)}</strong></div><div><span>核验时间</span><strong>${esc(checked||'未填写')}</strong></div><div><span>数据版本</span><strong>${esc(state.store.manifest.dataVersion)}</strong></div><div class="record-places"><span>原始场所</span><strong>${esc(placeText)}</strong></div></div><button id="copyRecordId" class="linkbutton">复制编号</button></details>`;
}
function backToResults(){const list=$('#list');if(!list)return;list.focus?.({preventScroll:true});list.scrollIntoView?.({block:'start'})}
function bindDetailUtilities(id,checked,places){
  if($('#copyRecordId'))$('#copyRecordId').onclick=()=>copyText(id,'已复制编号');
  if($('#backResults'))$('#backResults').onclick=backToResults;
  if(state.pendingDetailScroll){
    state.pendingDetailScroll=false;
    if(typeof window.matchMedia==='function'&&window.matchMedia('(max-width: 780px)').matches){
      $('#detail h2')?.scrollIntoView?.({block:'start'});
    }
  }
}

async function renderHazardDetail(){
  const request=detailRequests.begin('hazards',state.selectedHazard);
  const index=state.store.searchIndex.find(x=>x.id===state.selectedHazard);
  if(!index){
    if(detailRequests.isCurrent(request)) $('#detail').innerHTML='<div class="empty"><strong>选择一个隐患查看详情</strong></div>';
    return;
  }
  setBusy('正在读取隐患详情');
  try{
    const {hazard,bases}=await state.store.getHazardDetail(index);
    if(!detailRequests.isCurrent(request)) return;
    const proposalHelp={
      workbook_revised_pending_clause_rebind:{label:'待补齐正式条款证据',text:'下一步：按直接依据定位官方或已授权原文，确认版本与实施状态，核对条款号、原文和适用范围，建立“证据 → 条款 → 直接关联 → 审核记录”链后，才能转为已核验。'},
      basis_catalog_only:{label:'只有法规题录',text:'下一步：取得可合法核对的全文，定位具体条款并核对适用范围；不能只凭标准名称发布。'},
      basis_name_unresolved:{label:'法规身份未完全确认',text:'下一步：先确认法规/标准编号、版次和效力状态，再定位条款原文。'},
      same_title_review:{label:'同名或重复待合并',text:'下一步：与已有隐患比较对象、场景和整改措施，确认合并或保留，再绑定正式条款。'}
    };
    const proposal=proposalHelp[hazard.proposalStatus]||{label:'待补充核验材料',text:'下一步：补齐法规版本、具体条款、原文证据和适用性审核；完成前不能直接作为正式依据。'};
    const candidateNotice=hazard.status==='待审核候选'?`<div class="candidateNotice"><strong>${esc(proposal.label)}</strong><p>这条记录已经上线供查询，但还不是正式法规依据。${esc(proposal.text)}</p><p class="candidateMeta">处置状态：${esc(hazard.proposalStatus||'待核验')}；Excel来源第 ${esc(hazard.sourceRow||'未知')} 行。</p></div>`:'';
    const basisContent=bases.length?bases.map(basisHtml).join(''):`<div class="candidateNotice muted"><strong>暂无已审核条款关联</strong><p>候选依据和待办说明需完成核验后才能生成正式关联。</p></div>`;
    const conditions=hazard.conditions||'';
    const businessNote=String(hazard.businessNote??hazard.note??'');
    const maintenanceNote=String(hazard.maintenanceNote||'');
    const conditionsBlock=conditions?`<section class="block"><h3><span class="number">02</span>适用条件</h3><p>${esc(conditions)}</p></section>`:'';
    const basisNumber=conditions?'03':'02';
    const measuresNumber=conditions?'04':'03';
    const noteBlock=businessNote.trim()?`<section class="block note"><h3>补充说明</h3><p>${esc(businessNote.trim())}</p></section>`:'';
    const maintenanceBlock=maintenanceNote.trim()?`<details class="maintenance-record"><summary>维护记录</summary><p>${esc(maintenanceNote.trim())}</p><button type="button" id="copyMaintenance" class="linkbutton">复制维护记录</button></details>`:'';
    const html=`<div class="detailtop"><div class="topline"><span class="eyebrow">${esc(hazard.displayCategory||displayCategoryOf(hazard))}</span>${pill(hazard.status==='已核验'?modeLabel(hazard.mode):hazard.status)}</div><h2>${esc(hazard.title)}</h2><div class="subtitle">${esc((hazard.places||[]).join(' · '))}<br>核验状态：${esc(hazard.status)} · ${esc(dateOnly(hazard.checked))} · 数据日期 ${esc(dataDateOf(state.store.manifest,state.store.verifiedFiles?.manifest))}</div></div><div class="detailbody">${candidateNotice}<section class="block"><h3><span class="number">01</span>隐患专业描述</h3><p>${esc(hazard.description)}</p></section>${conditionsBlock}<section class="block"><h3><span class="number">${basisNumber}</span>法规原文依据 <small>${bases.length} 条</small></h3>${basisContent}</section><section class="block"><h3><span class="number">${measuresNumber}</span>整改措施</h3><p>${esc(hazard.measures)}</p></section>${noteBlock}${maintenanceBlock}${technicalInfoHtml({id:hazard.id,checked:hazard.checked,places:hazard.places||[]})}</div><div class="detailactions"><button class="primary" id="copy">复制整改条目</button><button id="copyfull">复制完整资料</button><button id="share">复制当前链接</button><button id="backResults">返回结果</button></div>`;
    if(!detailRequests.isCurrent(request)) return;
    $('#detail').innerHTML=html;
    if(!detailRequests.isCurrent(request)) return;
    $('#copy').onclick=()=>copyText(hazardText(hazard,bases),'已复制整改条目');
    $('#copyfull').onclick=()=>copyText(hazardFullText(hazard,bases),'已复制完整资料');
    if($('#copyMaintenance'))$('#copyMaintenance').onclick=()=>copyText(maintenanceNote.trim(),'已复制维护记录');
    $('#share').onclick=()=>copyText(location.href,'已复制当前链接');
    bindDetailUtilities(hazard.id,hazard.checked,hazard.places||[]);
    $$('.lawjump').forEach(b=>b.onclick=()=>{state.selectedLaw=b.dataset.law;switchView('laws',{keepQuery:false})});
  }catch(err){if(detailRequests.isCurrent(request)) showError(err)}
}

function basisHtml({ref,clause,law,sourceUrl}){const chkDate=clause.checked?dateOnly(clause.checked):'已核验';return `<div class="basis"><div class="basismeta"><span>${pill(roleLabel(ref.role))}</span><span class="article">${esc(law.displayLevel||law.level)} · ${esc(law.scope)} · ${esc(law.status)}</span></div><h4>${esc(law.name)}</h4><span class="article">${esc(clause.article)} · 条款核验：${esc(chkDate)}</span><blockquote>${esc(clause.quote||'尚未录入原文，请核验后补充。')}</blockquote><div class="basislinks">${sourceUrl?`<a href="${esc(sourceUrl)}" target="_blank" rel="noopener noreferrer">查看来源原文 ↗</a>`:'<span class="article">来源待补充</span>'}<button class="linkbutton lawjump" data-law="${esc(law.id)}">在法规库查看</button></div></div>`}
function hazardText(h,bases){const conditions=h.conditions||'';return `${h.title}\n\n隐患专业描述：\n${h.description}${conditions?`\n\n适用条件：\n${conditions}`:''}\n\n法规依据：\n${bases.map(x=>`《${x.law.name}》${x.clause.article}\n${x.clause.quote}`).join('\n\n')}\n\n整改措施：\n${h.measures}`}
function hazardFullText(h,bases){const note=String(h.businessNote??h.note??'');return `${hazardText(h,bases)}${note.trim()?`\n\n补充说明：\n${note.trim()}`:''}\n\n核验状态：${h.status}；核验日期：${h.checked||'未填写'}；数据库版本：${state.store.manifest.dataVersion}。`}

async function renderLawDetail(){
  const request=detailRequests.begin('laws',state.selectedLaw);
  const law=state.store.lawIndex.find(x=>x.id===state.selectedLaw);
  if(!law){
    if(detailRequests.isCurrent(request)) $('#detail').innerHTML='<div class="empty"><strong>选择一部法规或标准查看详情</strong></div>';
    return;
  }
  setBusy('正在读取法规条款');
  try{
    const detail=await state.store.getLawDetail(law);
    const related=[...new Set(detail.clauses.flatMap(x=>x.ref.hazardIds))].map(id=>state.store.searchIndex.find(h=>h.id===id)).filter(Boolean);
    if(!detailRequests.isCurrent(request)) return;
    const html=`<div class="detailtop"><div class="topline"><span class="eyebrow">${esc(law.displayLevel||law.level)}</span>${pill(law.status)}</div><h2>${esc(law.name)}</h2><div class="subtitle">适用范围：${esc(law.scope)} · 核验日期：${esc(dateOnly(law.checked))} · 本库收录 ${law.clauseCount} 个条款 / 关联 ${law.hazardCount} 条隐患</div></div><div class="detailbody"><section class="block lawmeta"><h3><span class="number">01</span>法规状态</h3><div class="metagrid"><div><span>效力状态</span><strong>${esc(law.status)}</strong></div><div><span>实施日期</span><strong>${esc(dateOnly(law.effectiveDate))}</strong></div><div><span>地区</span><strong>${esc(law.scope)}</strong></div><div><span>数据库核验</span><strong>${esc(dateOnly(law.checked))}</strong></div></div>${law.sourceUrl?`<a class="sourcecta" href="${esc(law.sourceUrl)}" target="_blank" rel="noopener noreferrer">打开来源原文 ↗</a>`:''}</section><section class="block"><h3><span class="number">02</span>本库已收录条款</h3>${detail.clauses.map(({ref,clause})=>lawClauseHtml(ref,clause)).join('')}</section><section class="block"><h3><span class="number">03</span>关联隐患 <small>${related.length} 条</small></h3><div class="related">${related.map(h=>`<button class="relateditem hazardjump" data-id="${esc(h.id)}">${esc(h.title)}</button>`).join('')||'<p>暂无关联隐患。</p>'}</div></section>${technicalInfoHtml({id:law.id,checked:law.checked})}</div><div class="detailactions"><button class="primary" id="copylaw">复制法规资料</button><button id="share">复制当前链接</button><button id="backResults">返回结果</button></div>`;
    if(!detailRequests.isCurrent(request)) return;
    $('#detail').innerHTML=html;
    if(!detailRequests.isCurrent(request)) return;
    if(law.status==='即将生效') $('#detail .lawmeta').insertAdjacentHTML('afterbegin',`<p><strong>已发布 · 尚未实施</strong>：将于 ${esc(dateOnly(law.effectiveDate))} 实施，可提前查阅和准备。<a class="sourcecta" href="library.html?document=${encodeURIComponent(law.id)}">查看版本目录与现行版入口 →</a></p>`);
    $('#copylaw').onclick=()=>copyText(lawText(detail),'已复制法规资料');
    $('#share').onclick=()=>copyText(location.href,'已复制当前链接');
    bindDetailUtilities(law.id,law.checked,[]);
    $$('.hazardjump').forEach(b=>b.onclick=()=>{state.selectedHazard=b.dataset.id;switchView('hazards',{keepQuery:false})});
  }catch(err){if(detailRequests.isCurrent(request)) showError(err)}
}
function lawClauseHtml(ref,c){return `<div class="basis"><div class="basismeta"><strong class="articletitle">${esc(c.article)}</strong>${pill(c.status)}</div><blockquote>${esc(c.quote||'原文待核验')}</blockquote><div class="article">核验日期：${esc(dateOnly(c.checked))} · 关联 ${ref.hazardIds.length} 条隐患</div></div>`}
function lawText({law,clauses}){return `${law.name}\n效力状态：${lawStatusLabel(law.status)}\n实施日期：${dateOnly(law.effectiveDate)}\n适用范围：${law.scope}\n来源：${law.sourceUrl||'待补'}\n\n${clauses.map(x=>`${x.clause.article}\n${x.clause.quote}`).join('\n\n')}`}

function renderDataView(){
  const m=state.store.manifest,h=m.health;
  $('#dataView').innerHTML=`<div class="datahead"><span class="eyebrow">DATABASE / V2</span><h2>数据库状态与维护</h2><p>公开站点只展示已核验隐患和实际引用的法规版本；候选与来源目录继续留在审核链中。企业报告、现场照片和未脱敏资料仍留在私有资料源。</p></div><div class="stats"><div><span>隐患</span><strong>${m.counts.hazards}</strong><small>${h.verifiedHazards} 条已核验 · ${h.pendingHazards} 条待审核候选</small></div><div><span>法规 / 标准</span><strong>${m.counts.laws}</strong><small>${h.activeLaws} 部现行有效</small></div><div><span>条款</span><strong>${m.counts.clauses}</strong><small>${m.counts.links} 个正式关联关系</small></div><div><span>数据版本</span><strong class="version">${esc(m.dataVersion)}</strong><small>${esc(dateOnly(m.generatedAt))} 构建</small></div></div><div class="maintgrid"><section><h3>数据架构</h3><p><b>母库：</b>隐患、法规、条款、关联关系分开保存，法规原文不在每条隐患中重复复制。</p><p><b>运行层：</b>首页先加载轻量索引；点击结果后按需加载对应分片。</p><p><b>版本控制：</b>每次更新通过 Git 留痕，可比较、回滚；网站显示数据库版本和核验日期。</p></section><section><h3>报告入库流程</h3><ol><li>报告 / 检查表留在私有资料源。</li><li>提取候选隐患、法规和整改语料。</li><li>与现有库去重、拆分、合并并核验现行法规。</li><li>更新母库，自动校验并生成网站数据。</li><li>审阅发布预览和增减清单，再更新正式网站。</li></ol></section></div><div class="dataactions"><button class="primary" id="refreshData">重新加载最新数据库</button><button id="exportSource">导出当前公开数据</button><button id="clearCache">清除离线缓存</button><a class="buttonlink" href="https://github.com/An-0726/safety-basis" target="_blank" rel="noopener noreferrer">打开 GitHub 仓库 ↗</a></div><div class="health"><span class="dot good"></span><strong>当前发布包校验</strong><span>引用关系错误 ${h.invalidReferences} · 公开待核隐患 ${h.pendingHazards} · 公开待核法规 ${h.pendingLaws}；此处不统计私有母库待办</span></div>`;
  $('#refreshData').onclick=()=>location.reload();
  $('#exportSource').onclick=async()=>{try{toast('正在导出公开数据…');const bundle=await state.store.exportPublicBundle();download(`安全隐患法规库_公开快照_${m.dataVersion}_ChatGPT.json`,JSON.stringify({schemaVersion:2,dataVersion:m.dataVersion,exportedAt:new Date().toISOString(),...bundle},null,2));toast('公开数据已导出')}catch(e){showError(e)}};
  $('#clearCache').onclick=clearOfflineCache;
}

async function clearOfflineCache(){try{if('caches' in window){for(const k of await caches.keys())if(k.startsWith('safety-basis-'))await caches.delete(k)}state.store.clearMemoryCache();toast('离线缓存已清除')}catch(e){showError(e)}}
function showError(err){console.error(err);$('#detail').innerHTML=`<div class="empty error"><strong>数据读取失败</strong><p>${esc(err?.message||err)}</p><button id="retry">重新加载</button></div>`;$('#retry')?.addEventListener('click',()=>location.reload())}

function updateFilterSummary(){
  const hazardCount=['#level','#mode'].filter(id=>$(id)?.value).length;
  const lawCount=['#lawLevel','#lawStatus'].filter(id=>$(id)?.value).length;
  if($('#hazardFilterCount'))$('#hazardFilterCount').textContent=hazardCount?`（${hazardCount}）`:'';
  if($('#lawFilterCount'))$('#lawFilterCount').textContent=lawCount?`（${lawCount}）`:'';
}

function bind(){
  $$('.nav[data-view]').forEach(b=>b.onclick=()=>switchView(b.dataset.view));
  $('#search').oninput=()=>{state.query=$('#search').value;renderResults({mode:'filter-change'})};
  $('#clear').onclick=()=>{$('#search').value='';state.query='';renderResults({mode:'filter-change'});$('#search').focus()};
  const resetFilters=()=>{$$('#hazardFilters select,#lawFilters select').forEach(x=>x.value='');$('#search').value='';state.query='';renderResults({mode:'filter-change'})};
  $('#reset').onclick=resetFilters;
  $('#resetLaw').onclick=resetFilters;
  $$('#hazardFilters select,#lawFilters select').forEach(x=>x.onchange=()=>renderResults({mode:'filter-change'}));
  document.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();if(state.view==='data')switchView('hazards');$('#search').focus()}});
}

async function boot(){
  loadUrlState();bind();
  try{
    state.store=await new DataStore('.').init();
    initFilters();
    setDataDateHeader(state.store.manifest,state.store.verifiedFiles?.manifest);
    $('#search').value=state.query;
    switchView(state.view,{keepQuery:true,initial:true});
    if('serviceWorker' in navigator) navigator.serviceWorker.register('./sw.js').catch(()=>{});
  }catch(err){showError(err);$('#list').innerHTML='<div class="empty"><strong>数据库未能初始化</strong></div>'}
}

if(typeof document!=='undefined') boot();
