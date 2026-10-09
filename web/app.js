'use strict';
import {DataStore} from './js/store.js';
import {searchHazardsDetailed,searchLawsDetailed} from './js/search.js';
import {INSPECTION_LABELS,profileTemplateText,profileReferenceText} from './js/field-profiles.js';
import {renderNormativeContent} from './js/normative-content.js';

const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const MAX_RENDER=120;
const LEGACY_MAJOR_CATEGORY='重大事故隐患判定';
const state={view:'hazards',selectedHazard:'',selectedLaw:'',query:'',store:null,results:[],visibleCount:MAX_RENDER,pendingDetailScroll:false,routeWarnings:[],profileSelections:new Map()};

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
  const explicit=releaseManifest?.asOf||manifest?.asOf;
  if($('#dbVersion'))$('#dbVersion').textContent=explicit?`核验快照 ${dataDate}`:(dataDate==='未提供'?'快照日期未提供':`构建日期 ${dataDate} · 核验日期未提供`);
  if($('#dbDate'))$('#dbDate').textContent=dataDate;
  updateSnapshotNotice(explicit?dataDate:'');
  return dataDate;
}
export function snapshotNoticeText(dataDate,today){
  if(!/^\d{4}-\d{2}-\d{2}$/.test(dataDate))return '当前数据缺少明确快照日期。使用前请复核法规现行效力与现场条件。';
  if(dataDate<today)return `本页为 ${dataDate} 核验快照，未校验此后的法规变化。使用前请复核现行效力与现场条件。`;
  if(dataDate>today)return `快照日期 ${dataDate} 晚于当前日期，请先核对数据版本与实施日期。`;
  return '';
}
function updateSnapshotNotice(dataDate){
  const node=$('#snapshotNotice');if(!node)return;
  const parts=new Intl.DateTimeFormat('en',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
  const part=type=>parts.find(value=>value.type===type)?.value;
  const today=`${part('year')}-${part('month')}-${part('day')}`;
  node.textContent=snapshotNoticeText(dataDate,today);node.hidden=!node.textContent;
}
const HISTORICAL_REFERENCE_PREFIX='原 conditions 字段记录的引用依据为：';
function reliableNoteSegments(hazard={}){
  const segments=hazard.noteSegments;
  if(!Array.isArray(segments)||!segments.every(segment=>segment&&['business','maintenance'].includes(segment.kind)&&typeof segment.text==='string'))return null;
  const rawNote=typeof hazard.note==='string'?hazard.note:null;
  const combined=segments.map(segment=>segment.text).join('');
  return rawNote===null||combined===rawNote?segments:null;
}
function removeKnownMaintenance(note,maintenanceNote){
  const maintenance=String(maintenanceNote??'').split(/\r?\n/).filter(Boolean);
  if(!maintenance.length)return note;
  let remaining=note;
  let business='';
  for(const text of maintenance){
    const index=remaining.indexOf(text);
    if(index<0)return note;
    business+=remaining.slice(0,index);
    remaining=remaining.slice(index+text.length);
  }
  return business+remaining;
}
function noteTextForDisplay(hazard={}){
  if(typeof hazard.businessNote==='string')return hazard.businessNote;
  const rawNote=typeof hazard.note==='string'?hazard.note:'';
  const segments=reliableNoteSegments(hazard);
  if(segments)return segments.filter(segment=>segment.kind==='business').map(segment=>segment.text).join('');
  return typeof hazard.maintenanceNote==='string'&&hazard.maintenanceNote.trim()
    ? removeKnownMaintenance(rawNote,hazard.maintenanceNote)
    : rawNote;
}
function publicNoteParts(hazard={}){
  const business=[];
  const historicalReferences=[];
  for(const line of noteTextForDisplay(hazard).split(/\r?\n/)){
    if(line.startsWith(HISTORICAL_REFERENCE_PREFIX)){
      let reference=line.slice(HISTORICAL_REFERENCE_PREFIX.length);
      if(reference.startsWith('依据：'))reference=reference.slice('依据：'.length);
      if(reference.trim())historicalReferences.push(reference.trim());
    }else business.push(line);
  }
  return {businessNote:business.join('\n').trim(),historicalReferences};
}
function modeLabel(value){return ({direct:'直接适用',conditional:'有条件适用'})[value]||value||'未标注'}
function roleLabel(value){return ({direct:'直接依据',indirect:'间接依据',supporting:'间接／辅助依据',fallback:'上位法／兜底依据'})[value]||value||'未标注'}
function displayCategoryOf(row){return row.displayCategory??row.category??''}
function displayLevelOf(row){return row.displayLevel??row.level??''}
function currentFilters(){return state.view==='hazards'?{inspectionClass:$('#inspectionClass')?.value||'',category:$('#category').value,sceneTag:$('#scene').value,displayLevel:$('#level').value,level:$('#level').value,region:$('#region').value,mode:$('#mode').value}:{displayLevel:$('#lawLevel').value,level:$('#lawLevel').value,region:$('#lawRegion').value,status:$('#lawStatus').value}}

const URL_FILTERS={
  hazards:{inspectionClass:'#inspectionClass',category:'#category',scene:'#scene',level:'#level',region:'#region',mode:'#mode'},
  laws:{level:'#lawLevel',region:'#lawRegion',status:'#lawStatus'},
  data:{},
};

export function parseRoute(search=''){
  const p=new URLSearchParams(search);
  const view=['hazards','laws','data'].includes(p.get('view'))?p.get('view'):'hazards';
  const filters={};
  for(const key of Object.keys(URL_FILTERS[view]))filters[key]=p.get(key)||(key==='scene'?p.get('sceneTag'):'')||'';
  return {view,query:p.get('q')||'',selectedHazard:view==='hazards'?(p.get('id')||''):'',
    selectedLaw:view==='laws'?(p.get('law')||''):'',filters};
}

export function routeQuery(route={}){
  const view=['hazards','laws','data'].includes(route.view)?route.view:'hazards';
  const p=new URLSearchParams();
  if(view!=='hazards')p.set('view',view);
  if(route.query)p.set('q',route.query);
  if(view==='hazards'&&route.selectedHazard)p.set('id',route.selectedHazard);
  if(view==='laws'&&route.selectedLaw)p.set('law',route.selectedLaw);
  for(const key of Object.keys(URL_FILTERS[view])){
    const value=route.filters?.[key];
    if(value)p.set(key,value);
  }
  return p.toString();
}

function loadUrlState(){
  const route=parseRoute(location.search);
  state.view=route.view;state.query=route.query;
  state.selectedHazard=route.selectedHazard;state.selectedLaw=route.selectedLaw;
  return route;
}
export function canonicalCategoryFilter(value,rows=[]){
  if(!value||rows.some(row=>displayCategoryOf(row)===value))return value;
  const targets=new Set(rows.filter(row=>row.category===value).map(displayCategoryOf));
  // An old label may migrate only when the shipped, reviewed projection gives
  // it one unambiguous destination. Never infer a category from title words.
  return targets.size===1?[...targets][0]:value;
}
function applyUrlFilters(route){
  state.routeWarnings=[];
  for(const fields of Object.values(URL_FILTERS))for(const selector of Object.values(fields)){
    const select=$(selector);if(select)select.value='';
  }
  for(const [key,selector] of Object.entries(URL_FILTERS[route.view])){
    const select=$(selector),rawValue=route.filters[key]||'';
    const value=key==='category'?canonicalCategoryFilter(rawValue,state.store.searchIndex):rawValue;
    // Ignore unknown values instead of silently hiding the whole database.
    if(select&&[...select.options].some(option=>option.value===value))select.value=value;
    else if(value)state.routeWarnings.push(`链接中的筛选“${value}”已不再提供，请重新选择。`);
  }
  updateFilterSummary();
  if($('#hazardMoreFilters'))$('#hazardMoreFilters').open=['#scene','#level','#mode','#inspectionClass'].some(id=>$(id)?.value);
  if($('#lawMoreFilters'))$('#lawMoreFilters').open=['#lawLevel','#lawStatus'].some(id=>$(id)?.value);
}
function syncUrl(historyMode='replace'){
  const filters={};
  for(const [key,selector] of Object.entries(URL_FILTERS[state.view]||{}))filters[key]=$(selector)?.value||'';
  const query=routeQuery({...state,filters});
  const url=`${location.pathname}${query?'?'+query:''}${location.hash}`;
  if(`${location.pathname}${location.search}${location.hash}`===url)return;
  history[historyMode==='push'?'pushState':'replaceState'](null,'',url);
}

function initFilters(){const t=state.store.taxonomy;
  const categories=t.displayCategories||t.categories||[];
  const levels=t.displayLevels||t.lawLevels||[];
  const availableScenes=new Set(state.store.searchIndex.flatMap(row=>row.sceneTags||[]));
  const scenes=(t.sceneTagOptions||[]).filter(tag=>tag==='未细分场景'||availableScenes.has(tag));
  const modes=t.hazardModes||[];
  // The major-criteria topic is independent of professional categories. Keep
  // the old value hidden only to preserve old URLs without widening results.
  $('#category').innerHTML='<option value="">全部专业分类</option>'+categories.filter(value=>value!==LEGACY_MAJOR_CATEGORY).map(option).join('')+`<option value="${LEGACY_MAJOR_CATEGORY}" hidden disabled>重大事故隐患判定（旧分类）</option>`;
  $('#scene').innerHTML='<option value="">全部现场标签</option>'+(scenes.length?scenes.map(value=>optionPair(value,value==='未细分场景'?'未标注具体现场':value)).join(''):'');
  if($('#inspectionClass'))$('#inspectionClass').innerHTML='<option value="">全部条目（不限定用途）</option>'+Object.entries(INSPECTION_LABELS).filter(([key])=>state.store.searchIndex.some(row=>(row.inspectionClasses||[]).includes(key))).map(([key,label])=>optionPair(key,label+'（已审场景）')).join('');
  $('#level').innerHTML='<option value="">全部依据类型</option>'+levels.map(option).join('');
  $('#mode').innerHTML='<option value="">全部适用方式</option>'+modes.map(value=>optionPair(value,modeLabel(value))).join('');
  $('#lawLevel').innerHTML='<option value="">全部依据类型</option>'+levels.map(option).join('');
  $('#lawStatus').innerHTML='<option value="">全部已核验版本</option>'+t.lawStatuses.map(status=>`<option value="${esc(status)}">${esc(lawStatusLabel(status))}</option>`).join('');
}

function switchView(view,{keepQuery=false,initial=false,targetId=null,historyMode='push'}={}){
  if(!state.store)return;
  state.view=view;state.visibleCount=MAX_RENDER;state.pendingDetailScroll=false;if(!keepQuery)state.query='';
  if(targetId!==null){
    if(view==='hazards')state.selectedHazard=targetId;else if(view==='laws')state.selectedLaw=targetId;
    for(const selector of Object.values(URL_FILTERS[view]||{}))if($(selector))$(selector).value='';
  }
  $$('.nav').forEach(x=>x.classList.toggle('active',x.dataset.view===view));
  $('#searchView').hidden=view==='data';$('#dataView').hidden=view!=='data';
  $('#hazardFilters').hidden=view!=='hazards';$('#lawFilters').hidden=view!=='laws';
  $('#search').value=state.query;
  if(view==='hazards'){$('#search').placeholder='搜索隐患、现场现象、关键词或法规，如：配电箱门跨接、灭火器失压…';$('#sectionTitle').textContent='隐患速查';$('#sectionHint').textContent='现场问题 → 专业描述 → 直接依据 → 整改措施';}
  if(view==='laws'){$('#search').placeholder='搜索法规、标准、条款号，如：安全生产法、GB 55036…';$('#sectionTitle').textContent='法规库';$('#sectionHint').textContent='法规标准 → 收录条款 → 反查关联隐患';}
  if(view==='data'){
    detailRequests.invalidate();
    renderDataView();
  }else renderResults({mode:initial||targetId!==null?'initial':'view-change',historyMode});
  syncUrl(historyMode);
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

function renderResults({mode='normal',historyMode='replace'}={}){
  if(!state.store)return;
  const list=$('#list');
  const filterChanged=mode==='filter-change';
  const viewChanged=mode==='view-change';
  const initialDeepLink=mode==='initial';
  const previousScrollTop=filterChanged||viewChanged?0:(list?.scrollTop||0);
  if(filterChanged||viewChanged){state.visibleCount=MAX_RENDER;state.pendingDetailScroll=false;state.routeWarnings=[];}
  state.query=$('#search').value.trim();
  const filters=currentFilters();
  updateFilterSummary();
  if($('#majorTopicNotice'))$('#majorTopicNotice').hidden=state.view!=='hazards'||filters.category!==LEGACY_MAJOR_CATEGORY;
  const match=state.view==='hazards'?searchHazardsDetailed(state.store.searchIndex,state.query,filters):searchLawsDetailed(state.store.lawIndex,state.query,filters);
  const rows=match.rows;
  showSearchNotice(match);
  renderActiveFilters();
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
    : '试试缩短关键词或移除筛选；未检索到不代表不存在相关要求。';
  const empty=rows.length?'':'<div class="empty"><strong>没有找到匹配内容</strong><p>试试缩短关键词或移除筛选。</p><p>未检索到不代表不存在相关要求。</p></div>';
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
  syncUrl(historyMode);
}

function renderUnavailable(id,kind){
  detailRequests.invalidate();
  $('#detail').innerHTML=`<div class="empty"><strong>此${esc(kind)}未在当前已核验库中发布</strong><p>链接编号：${esc(id)}</p><p>可能尚待核验、已撤下或编号有误。请从列表选择其他内容，或搜索已核验的依据。</p></div>`
}

function hazardCard(r){
  const clues=(r.sceneTags||[]).join(' · ');
  return `<button class="card ${r.id===state.selectedHazard?'selected':''}" data-id="${esc(r.id)}" aria-pressed="${r.id===state.selectedHazard}"><div class="meta"><span>${esc(displayCategoryOf(r))}</span>${pill(r.status==='已核验'?modeLabel(r.mode):r.status)}</div><h3>${esc(r.title)}</h3>${clues?`<p>${esc(clues)}</p>`:''}${r.profileSummary?`<p class="profile-card-label">核查用途：${esc(r.profileSummary)}</p>`:''}<span class="arrow">↗</span></button>`;
}
function lawCard(r){return `<button class="card ${r.id===state.selectedLaw?'selected':''}" data-id="${esc(r.id)}" aria-pressed="${r.id===state.selectedLaw}"><div class="meta"><span>${esc(displayLevelOf(r))}</span>${pill(r.status)}</div><h3>${esc(r.name)}</h3><p>${esc(r.scope)} · ${r.clauseCount} 条收录条款 · 关联 ${r.hazardCount} 条隐患</p><span class="arrow">↗</span></button>`}

function selectHazard(id){state.selectedHazard=id;state.pendingDetailScroll=true;renderResults({mode:'selection',historyMode:'push'})}
function selectLaw(id){state.selectedLaw=id;state.pendingDetailScroll=true;renderResults({mode:'selection',historyMode:'push'})}

function historicalReferenceHtml(references=[]){
  if(!references.length)return '';
  return `<div class="history-reference"><span>历史引用（不替代当前依据）</span>${references.map(reference=>`<p>${esc(reference)}</p>`).join('')}</div>`;
}
function technicalInfoHtml({id,checked,places=[],historicalReferences=[]}){
  const placeText=places.length?places.join('；'):'未填写/不适用';
  return `<details class="record-info"><summary>条目信息</summary><div class="record-grid"><div><span>完整 ID</span><strong>${esc(id)}</strong></div><div><span>核验时间</span><strong>${esc(checked||'未填写')}</strong></div><div><span>数据版本</span><strong>${esc(state.store.manifest.dataVersion)}</strong></div><div class="record-places"><span>原始场所</span><strong>${esc(placeText)}</strong></div></div>${historicalReferenceHtml(historicalReferences)}<button id="copyRecordId" class="linkbutton">复制编号</button></details>`;
}
function updateStickyHeaderHeight(){
  const header=$('header');
  if(header)document.documentElement.style.setProperty('--sticky-header-height',`${header.getBoundingClientRect().height}px`);
}
function bindStickyHeaderHeight(){
  const header=$('header');if(!header)return;
  updateStickyHeaderHeight();
  // Header rows can wrap after resizing, zooming or a font finishes loading.
  if(typeof ResizeObserver!=='undefined')new ResizeObserver(updateStickyHeaderHeight).observe(header);
  window.addEventListener('resize',updateStickyHeaderHeight);
}
function backToResults(){const list=$('#list');if(!list)return;updateStickyHeaderHeight();list.focus?.({preventScroll:true});list.scrollIntoView?.({block:'start'})}
function bindDetailUtilities(id,checked,places){
  if($('#copyRecordId'))$('#copyRecordId').onclick=()=>copyText(id,'已复制编号');
  if($('#backResults'))$('#backResults').onclick=backToResults;
  if(state.pendingDetailScroll){
    state.pendingDetailScroll=false;
    updateStickyHeaderHeight();
    const title=$('#detail h2');
    const narrow=typeof window.matchMedia==='function'&&window.matchMedia('(max-width: 780px)').matches;
    const titleRect=title?.getBoundingClientRect?.();
    const headerBottom=$('header')?.getBoundingClientRect?.().bottom||0;
    // A long desktop results list can move the outer page while a card is
    // selected. Keep an already-visible heading still; reveal it if obscured.
    const outsideViewport=titleRect&&(titleRect.top<headerBottom+12||titleRect.bottom>window.innerHeight);
    if(narrow||outsideViewport)title?.scrollIntoView?.({block:'start'});
  }
}

async function renderHazardDetail({focusProfile=false}={}){
  const request=detailRequests.begin('hazards',state.selectedHazard);
  const index=state.store.searchIndex.find(x=>x.id===state.selectedHazard);
  if(!index){
    if(detailRequests.isCurrent(request)) $('#detail').innerHTML='<div class="empty"><strong>选择一个隐患查看详情</strong></div>';
    return;
  }
  setBusy('正在读取隐患详情');
  try{
    const {hazard,bases}=await state.store.getHazardDetail(index);
    const profiles=state.store.getFieldProfiles?.(hazard.id)||[];
    const selectedProfile=profiles.find(p=>p.id===state.profileSelections.get(hazard.id));
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
    const noteParts=publicNoteParts(hazard);
    const businessNote=noteParts.businessNote;
    const conditionsBlock=conditions?`<section class="block"><h3><span class="number">02</span>适用条件</h3><p>${esc(conditions)}</p></section>`:'';
    const basisNumber=conditions?'03':'02';
    const measuresNumber=conditions?'04':'03';
    const noteBlock=businessNote.trim()?`<section class="block note"><h3>补充说明</h3><p>${esc(businessNote.trim())}</p></section>`:'';
    const html=`<div class="detailtop"><div class="topline"><span class="eyebrow">${esc(hazard.displayCategory||displayCategoryOf(hazard))}</span>${pill(hazard.status==='已核验'?modeLabel(hazard.mode):hazard.status)}</div><h2>${esc(hazard.title)}</h2><div class="subtitle">${esc((hazard.places||[]).join(' · '))}<br>核验状态：${esc(hazard.status)} · ${esc(dateOnly(hazard.checked))} · 数据日期 ${esc(dataDateOf(state.store.manifest,state.store.verifiedFiles?.manifest))}</div></div><div class="detailbody">${candidateNotice}<section class="block"><h3><span class="number">01</span>${profiles.length?'条目说明（需按场景核实）':'隐患专业描述'}</h3><p>${esc(hazard.description)}</p></section>${conditionsBlock}${profileSectionHtml(hazard,profiles,selectedProfile,bases)}<section class="block"><h3><span class="number">${basisNumber}</span>法规原文依据 <small>${bases.length} 条</small></h3>${basisContent}</section><section class="block"><h3><span class="number">${measuresNumber}</span>整改措施</h3><p>${esc(hazard.measures)}</p></section>${noteBlock}${technicalInfoHtml({id:hazard.id,checked:hazard.checked,places:hazard.places||[],historicalReferences:noteParts.historicalReferences})}</div><div class="detailactions"><button class="primary" id="copy">复制整改条目</button><button id="copyfull">复制完整资料</button><button id="share">复制当前链接</button><button id="backResults">返回结果</button></div>`;
    if(!detailRequests.isCurrent(request)) return;
    $('#detail').innerHTML=html;
    if(!detailRequests.isCurrent(request)) return;
    const referencePrefix=profiles.length?'核查参考资料，非已核实的现场隐患。场景选择不代表条件成立或违规已发生。'+(profiles.every(p=>p.defaultFieldEntry==='exclude')?'本条已审场景不纳入默认现场检查；排除现场入口不等于本项要求不适用。':'')+'\n\n':'';
    const profileText=selectedProfile?profileReferenceText(selectedProfile)+'\n\n本场景选定依据：\n'+selectedProfile.basisLinkIds.map(id=>bases.find(b=>b.ref.linkId===id)).map(b=>`《${b.law.name}》${b.clause.article}\n本条依据适用范围：${basisApplicability(b.ref)}`).join('\n\n')+'\n\n条目完整参考：\n':'';
    if(profiles.length)$('#copy').textContent='复制核查参考';
    $('#copy').onclick=()=>copyText(referencePrefix+profileText+hazardText(hazard,bases),profiles.length?'已复制核查参考':'已复制整改条目');
    $('#copyfull').onclick=()=>copyText(referencePrefix+profileText+hazardFullText(hazard,bases),'已复制完整资料');
    if($('#profileSelect'))$('#profileSelect').onchange=()=>{
      const value=$('#profileSelect').value;
      if(profiles.some(p=>p.id===value))state.profileSelections.set(hazard.id,value);else state.profileSelections.delete(hazard.id);
      return renderHazardDetail({focusProfile:true});
    };
    if($('#clearProfile'))$('#clearProfile').onclick=()=>{state.profileSelections.delete(hazard.id);return renderHazardDetail({focusProfile:true});};
    if(focusProfile)$('#profileSelect')?.focus?.({preventScroll:true});
    $('#share').onclick=()=>copyText(location.href,'已复制当前链接');
    bindDetailUtilities(hazard.id,hazard.checked,hazard.places||[]);
    $$('.lawjump').forEach(b=>b.onclick=()=>switchView('laws',{targetId:b.dataset.law}));
  }catch(err){if(detailRequests.isCurrent(request)) showError(err)}
}

function profileSectionHtml(hazard,profiles,selected,bases){
  if(!profiles.length)return '';
  const list=values=>`<ul>${values.map(value=>`<li>${esc(value)}</li>`).join('')}</ul>`;
  const nonOnsite=profiles.every(p=>p.defaultFieldEntry==='exclude');
  const body=selected?`<div class="profile-guidance" data-profile-id="${esc(selected.id)}"><p class="profile-route"><strong>${esc(INSPECTION_LABELS[selected.inspectionClass])}</strong> · ${selected.defaultFieldEntry==='exclude'?'不纳入默认现场检查；仍可查阅本项要求':'有条件核查，尚未形成现场结论'}</p><h4>需核实的适用条件</h4>${list(selected.applicability.requires)}<h4>不适用 / 避免误判</h4>${list(selected.applicability.excludes)}<h4>最小取证要求</h4>${list(selected.evidenceRequirements)}<h4>本场景选定依据</h4>${selected.basisLinkIds.map(id=>{
    const b=bases.find(x=>x.ref.linkId===id);
    return `<div class="profile-basis" data-profile-link-id="${esc(id)}"><strong>${esc(b.law.name)} · ${esc(b.clause.article)}</strong><p>${esc(basisApplicability(b.ref))}</p><span>本关联地域：${esc(b.ref.jurisdictionCode??'未单独标注，按原文范围核实')}</span></div>`;
  }).join('')}<p class="profile-help">以上条件逐条对应选定依据；下方条目全部原文仍保留，不自动合并为本场景依据。</p>${profileTemplateText(selected)?`<details class="profile-template"><summary>未填描述模板（核查参考）</summary><p>仅供适用条件与实际事实分别核实后参考；当前未生成现场结论。</p><p>${esc(profileTemplateText(selected))}</p></details>`:'<p class="profile-help">本项仅提供核查用途与范围，不提供现场隐患描述模板。</p>'}<h4>整改方向参考</h4><p>${esc(selected.correctiveDirection)}</p></div>`:'';
  return `<section class="block field-profile"><h3>条件 / 场景适用性</h3><p id="profileHelp">选择仅帮助查阅已审场景，不代表已核实现场事实或确认违规。只在当前页面会话保留，不写入链接、不上传、不保存企业资料。</p>${nonOnsite?'<p class="profile-routing-note">此条的已审场景不纳入默认现场检查；排除现场入口不等于本项要求不适用。</p>':''}<label for="profileSelect">核查场景（可选）</label><div class="profile-controls"><select id="profileSelect" aria-describedby="profileHelp"><option value="">请选择场景，不影响原条目查阅</option>${profiles.map(p=>`<option value="${esc(p.id)}"${selected?.id===p.id?' selected':''}>${esc(p.title)}</option>`).join('')}</select>${selected?'<button id="clearProfile" type="button" class="quiet">清除选择</button>':''}</div>${body}</section>`;
}

function basisApplicability(ref){return typeof ref?.applicability==='string'&&ref.applicability.trim()?ref.applicability:''}
function basisHtml({ref,clause,law,sourceUrl}){const chkDate=clause.checked?dateOnly(clause.checked):'已核验',scope=basisApplicability(ref);return `<div class="basis" data-link-id="${esc(ref.linkId||'')}"><div class="basismeta"><span>${pill(roleLabel(ref.role))}</span><span class="article">${esc(law.displayLevel||law.level)} · ${esc(law.scope)} · ${esc(law.status)}</span></div><h4>${esc(law.name)}</h4><span class="article">${esc(clause.article)} · 条款核验：${esc(chkDate)}</span>${scope?`<div class="basis-applicability"><strong>本条依据适用范围</strong><p>${esc(scope)}</p></div>`:''}${renderNormativeContent(clause)}<div class="basislinks">${sourceUrl?`<a href="${esc(sourceUrl)}" target="_blank" rel="noopener noreferrer">查看来源原文 ↗</a>`:'<span class="article">来源待补充</span>'}<button class="linkbutton lawjump" data-law="${esc(law.id)}">在法规库查看</button></div></div>`}
function hazardText(h,bases){const conditions=h.conditions||'';return `${h.title}\n\n隐患专业描述：\n${h.description}${conditions?`\n\n适用条件：\n${conditions}`:''}\n\n法规依据：\n${bases.map(x=>`《${x.law.name}》${x.clause.article}${basisApplicability(x.ref)?`\n本条依据适用范围：${basisApplicability(x.ref)}`:''}\n${x.clause.quote}`).join('\n\n')}\n\n整改措施：\n${h.measures}`}
function hazardFullText(h,bases){const note=publicNoteParts(h);const sections=[hazardText(h,bases)];if(note.businessNote)sections.push(`补充说明：\n${note.businessNote}`);if(note.historicalReferences.length)sections.push(`历史引用（不替代当前依据）：\n${note.historicalReferences.join('\n\n')}`);sections.push(`核验状态：${h.status}；核验日期：${h.checked||'未填写'}；数据库版本：${state.store.manifest.dataVersion}。`);return sections.join('\n\n')}

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
    $$('.hazardjump').forEach(b=>b.onclick=()=>switchView('hazards',{targetId:b.dataset.id}));
  }catch(err){if(detailRequests.isCurrent(request)) showError(err)}
}
function lawClauseHtml(ref,c){return `<div class="basis"><div class="basismeta"><strong class="articletitle">${esc(c.article)}</strong>${pill(c.status)}</div>${renderNormativeContent(c)}<div class="article">核验日期：${esc(dateOnly(c.checked))} · 关联 ${ref.hazardIds.length} 条隐患</div></div>`}
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
  const hazardCount=['#scene','#level','#mode','#inspectionClass'].filter(id=>$(id)?.value).length;
  const lawCount=['#lawLevel','#lawStatus'].filter(id=>$(id)?.value).length;
  if($('#hazardFilterCount'))$('#hazardFilterCount').textContent=hazardCount?`（${hazardCount}）`:'';
  if($('#lawFilterCount'))$('#lawFilterCount').textContent=lawCount?`（${lawCount}）`:'';
}

function showSearchNotice(match){
  const node=$('#searchNotice');if(!node)return;
  node.textContent=match.matchKind==='related'
    ? '当前筛选下没有原词或同义词结果，以下为相关概念参考。请核对设备、作业对象与适用条件。'
    : match.matchKind==='corrected'
      ? `当前筛选下没有原词结果，按“${match.interpretedQuery}”尝试纠错。请确认是否符合原意。`
      : match.matchKind==='colloquial'
        ? `没有与原话完全一致的条目，已按“${match.interpretedQuery}”查找。请核对对象、缺陷与适用条件。`
        : '';
  node.textContent=[...state.routeWarnings,match.queryNotice,node.textContent,state.view==='hazards'?state.store.fieldProfileNotice:'',state.view==='hazards'&&$('#inspectionClass')?.value?'核查用途筛选仅覆盖已审场景，未归入此用途不代表不适用。':''].filter(Boolean).join(' ');
  node.hidden=!node.textContent;
}
function renderActiveFilters(){
  const node=$('#activeFilters');if(!node)return;
  const labels={inspectionClass:'核查用途',category:'专业分类',scene:'现场标签',level:'依据类型',region:'地区',mode:'适用方式',status:'效力状态'};
  const entries=Object.entries(URL_FILTERS[state.view]||{}).filter(([,selector])=>$(selector)?.value);
  node.hidden=!entries.length;
  node.innerHTML=entries.map(([key,selector])=>{
    const select=$(selector),label=select.selectedOptions?.[0]?.textContent||select.value;
    return `<button type="button" class="filter-chip" data-filter="${esc(key)}" aria-label="移除${esc(labels[key])}：${esc(label)}">${esc(labels[key])}：${esc(label)} <span aria-hidden="true">×</span></button>`;
  }).join('');
  node.querySelectorAll('button[data-filter]').forEach(button=>button.onclick=()=>{
    const selector=URL_FILTERS[state.view]?.[button.dataset.filter];if(!selector)return;
    $(selector).value='';renderResults({mode:'filter-change',historyMode:'push'});
    const disclosure=$(selector).closest?.('details');
    if(disclosure&&!disclosure.open)disclosure.querySelector('summary')?.focus();else $(selector).focus();
  });
}

function bind(){
  $$('.nav[data-view]').forEach(b=>b.onclick=()=>switchView(b.dataset.view));
  $('#search').oninput=()=>{state.query=$('#search').value;renderResults({mode:'filter-change'})};
  $('#clear').onclick=()=>{$('#search').value='';state.query='';renderResults({mode:'filter-change'});$('#search').focus()};
  const resetFilters=()=>{state.profileSelections.clear();$$('#hazardFilters select,#lawFilters select').forEach(x=>x.value='');$('#search').value='';state.query='';renderResults({mode:'filter-change',historyMode:'push'})};
  $('#reset').onclick=resetFilters;
  $('#resetLaw').onclick=resetFilters;
  $$('#hazardFilters select,#lawFilters select').forEach(x=>x.onchange=()=>renderResults({mode:'filter-change',historyMode:'push'}));
  window.addEventListener('popstate',()=>{
    if(!state.store)return;
    const route=loadUrlState();applyUrlFilters(route);
    switchView(route.view,{keepQuery:true,initial:true,historyMode:'replace'});
  });
  document.addEventListener('visibilitychange',()=>{
    if(!document.hidden&&state.store)setDataDateHeader(state.store.manifest,state.store.verifiedFiles?.manifest);
  });
  document.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();if(state.view==='data')switchView('hazards');$('#search').focus()}});
}

async function boot(){
  bindStickyHeaderHeight();
  const route=loadUrlState();bind();
  try{
    state.store=await new DataStore('.').init();
    initFilters();applyUrlFilters(route);
    setDataDateHeader(state.store.manifest,state.store.verifiedFiles?.manifest);
    $('#search').value=state.query;
    switchView(state.view,{keepQuery:true,initial:true,historyMode:'replace'});
    if('serviceWorker' in navigator) navigator.serviceWorker.register('./sw.js').catch(()=>{});
  }catch(err){showError(err);$('#list').innerHTML='<div class="empty"><strong>数据库未能初始化</strong></div>'}
}

if(typeof document!=='undefined') boot();
