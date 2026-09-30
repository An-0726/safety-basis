import {searchPilot, INSPECTION_LABELS} from './field-pilot-search.js';
import {DataStore} from './store.js';
const $ = s => document.querySelector(s);
const esc = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const list = items => `<ul>${items.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`;
let records=[], selected='', formalStore=null;
const params = new URLSearchParams(location.search);
$('#query').value=params.get('q') || '';
if(INSPECTION_LABELS[params.get('class')]) $('#inspection').value=params.get('class');
function render(){
  const rows=searchPilot(records,$('#query').value,$('#inspection').value);
  if(!rows.some(row=>row.id===selected)) selected=rows[0]?.id || '';
  $('#summary').textContent=`${INSPECTION_LABELS[$('#inspection').value]} · ${rows.length} 条候选。条件不足只限制判定，不阻止查找。`;
  $('#results').innerHTML=rows.length?rows.map(row=>`<button class="card" data-id="${esc(row.id)}" aria-pressed="${row.id===selected}"><span class="badge">${row.caseRole==='counterexample'?'分流 / 条件不足':'条件式现场候选'}</span><h2>${esc(row.title)}</h2><p>${esc(row.object)} · ${esc(row.defect)}</p></button>`).join(''):'<p class="empty">当前用途下未找到匹配项。可切换检查用途或缩短查询。</p>';
  document.querySelectorAll('.card').forEach(el=>el.onclick=()=>{selected=el.dataset.id;render()});
  renderDetail(records.find(row=>row.id===selected));
  const p=new URLSearchParams();if($('#query').value)p.set('q',$('#query').value);if($('#inspection').value!=='core_onsite_inspection')p.set('class',$('#inspection').value);if(selected)p.set('id',selected);
  history.replaceState(null,'',`${location.pathname}?${p}`);
}
function basisHtml(b){
  const url=b.sourceUrl;
  const safeUrl=url && /^https:\/\//i.test(url)?url:null;
  const state=b.associationRole==='trace_only_not_pilot_approval'?'原目录追溯 · 正式关联未重签':b.status==='candidate_basis_checked'?'候选条文及声明适用范围已核 · 当前现场事实须证实':b.quote?'取得部分原文对照 · 依据缺口见下文':'完整原文或适用依据待补';
  return `<section class="basis"><strong>${esc(b.name || b.clauseId)}</strong><p class="small">${esc(b.article)} · ${esc(state)}</p>${b.quote?`<blockquote>${esc(b.quote)}</blockquote>`:'<p>本项尚无可引用的已核准条文原文。</p>'}<p>${esc(b.applicabilityNote)}</p>${b.sourceLocator?`<p class="small">原文定位：${esc(b.sourceLocator)}</p>`:''}${safeUrl?`<a href="${esc(safeUrl)}" target="_blank" rel="noopener noreferrer">打开依据来源 ↗</a>`:''}</section>`;
}
function overlayHtml(review){
  if(!review)return '';
  return `<section class="review-overlay"><h3>补充适用边界与待核事项</h3><p class="small">候选审核补充 · ${esc(review.reviewId)} · 不替代正式批准</p><h4>适用范围</h4>${list(review.requires)}<h4>范围排除</h4>${list(review.excludes)}<h4>仍待核实</h4>${list(review.pending)}<h4>核验出处</h4>${list(review.sources)}</section>`;
}
function renderDetail(row){
  if(!row){$('#detail').innerHTML='<p>选择一个检查项查看详情。</p>';return}
  $('#detail').innerHTML=`<span class="badge">本地候选 · 未获正式批准</span><h2>${esc(row.title)}</h2><p class="small">${esc(INSPECTION_LABELS[row.inspectionClass])} · ${esc(row.id)}</p><h3>${row.findingTemplate?'可填写的缺陷描述':'判定条件缺口'}</h3><p class="template">${esc(row.findingTemplate || '当前条件不足，暂不提供确定违规描述。')}</p><p class="note">${esc(row.pendingEvidenceNote)} ${row.findingTemplate?'模板中的括号须按实际证据填写。':''}</p><h3>适用条件</h3>${list(row.applicability.requires)}<h3>不适用 / 避免误判</h3>${list(row.applicability.excludes)}${overlayHtml(row.reviewOverlay)}<h3>最小取证要求</h3>${list(row.evidenceRequirements)}<h3>直接依据及核验状态</h3>${row.bases.map(basisHtml).join('')}<h3>${row.findingTemplate?'针对性整改方向':'条件不足时的处理'}</h3><p>${esc(row.correctiveDirection)}</p><button class="copy" id="copy">复制候选检查项</button><details class="compare"><summary>对照原目录描述与来源定位</summary><div id="original"><p>正在读取原目录…</p></div><p class="small">${esc(row.sourceRefs.map(s=>s.sourceId).join(' / '))} · ${row.sourceRefs.some(s=>/synthetic/.test(s.kind))?'合成需求/条件场景，非现场频次':'历史或目录来源，非当前现场观察'}</p></details>`;
  if(row.applicability.designConformityNote) $('#detail ul').insertAdjacentHTML('afterend',`<p class="small">${esc(row.applicability.designConformityNote)}</p>`);
  $('#copy').onclick=async()=>{const text=`【候选检查项，非已确认结论】${row.title}\n描述模板：${row.findingTemplate||'条件不足，不输出违规描述'}\n适用条件：${row.applicability.requires.join('；')}\n不适用 / 避免误判：${row.applicability.excludes.join('；')}${row.reviewOverlay ? `\n补充适用范围：${row.reviewOverlay.requires.join('；')}\n补充范围排除：${row.reviewOverlay.excludes.join('；')}\n仍待核实：${row.reviewOverlay.pending.join('；')}\n核验出处：${row.reviewOverlay.sources.join('；')}` : ''}\n待补证据：${row.evidenceRequirements.join('；')}\n整改方向：${row.correctiveDirection}\n依据状态：${row.basisCheck?.status==='candidate_basis_checked'?'候选条文及声明适用范围已核，当前现场事实和正式批准待确认':'依据存在缺口：'+(row.basisCheck?.blockers||[]).join('；')}`;try{await navigator.clipboard.writeText(text);$('#copy').textContent='已复制候选检查项'}catch{$('#copy').textContent='复制不可用，请选择文本复制'}};
  loadOriginal(row);
}
async function loadOriginal(row){
  if(!row.hazardId){$('#original').innerHTML='<p>新增需求候选，无可直接等同的旧实体。</p>';return}
  try{
    formalStore ||= new DataStore();
    if(!formalStore.manifest)await formalStore.init();
    const index=formalStore.searchIndex.find(r=>r.id===row.hazardId);
    if(!index){if(selected===row.id)$('#original').innerHTML='<p>对应原实体未进入本地正式发布索引；生命周期和依据状态未被本试点提升。</p>';return}
    const old=await formalStore.getHazard(index);
    if(selected===row.id)$('#original').innerHTML=`<p><strong>原描述</strong>：${esc(old.description)}</p><p><strong>原适用说明</strong>：${esc(old.note)}</p><a href="index.html?id=${encodeURIComponent(row.hazardId)}">在正式速查中查看原条目 →</a>`;
  }catch{if(selected===row.id)$('#original').innerHTML='<p>原正式包对照暂不可读取；试点候选未进入该正式索引。</p>'}
}
$('#query').oninput=render;$('#inspection').onchange=render;
document.querySelectorAll('[data-q]').forEach(button=>button.onclick=()=>{$('#query').value=button.dataset.q;render()});
try{
  const response=await fetch('data/field-profiles-pilot.json',{cache:'no-store'});
  if(!response.ok)throw Error('本目录未开启试点构建');
  const payload=await response.json();if(payload.pilotOnly!==true || payload.formalApproval!==false)throw Error('试点隔离标记异常');
  records=payload.records;selected=params.get('id')||'';render();
}catch(error){$('#summary').textContent=`无法加载本地试点：${error.message}`;}
