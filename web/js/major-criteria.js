import {VerifiedFiles} from './verified-files.js';
import {renderNormativeContent} from './normative-content.js';
import {validateMajorDirectory,selectMajorDirectory} from './major-criteria-directory-model.js';
import {validateMajorReferences,selectMajorReferences} from './major-criteria-reference-model.js';
import {validateMajorReading,validateReadingDirectoryLinks,selectMajorReading} from './major-criteria-reading-model.js';
import {validateMajorData,validateDirectoryCatalogLinks,parseMajorRoute,majorRouteQuery,selectMajorResults,snapshotNoticeText} from './major-criteria-model.js';

const $=selector=>document.querySelector(selector);
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const sourceLink=(url,label)=>{
  try{const parsed=new URL(url);return ['https:','http:'].includes(parsed.protocol)?`<a href="${esc(parsed.href)}" target="_blank" rel="noopener noreferrer">${esc(label)} ↗</a>`:'';}catch{return '';}
};
const hazardLink=id=>`./?id=${encodeURIComponent(id)}`;
let model=null;
let references=null;
let directory=null;
let reading=null;
let readingByDirectory=new Map();
const openReadingGroups=new Set();
let referenceById=new Map();
let route=parseMajorRoute(location.search);
let routeWarning='';
let hazardById=new Map();
let standardById=new Map();
const hasReferenceData=()=>Boolean(references||directory);
const directoryNotice=()=>reading?'本目录提供官方文件题录和适用范围提示，部分配套文件可展开官方原文。题录与原文查阅均不授予本站现行判定依据资格，不能据此自动作现场判定；目录主题并非互斥行业，也不表示全行业覆盖。':directory?.notice;

function coverageHtml(standard){
  const c=standard.coverage||{},scope=standard.officialScope||{};
  const label=c.wholeStandardComplete?'标准正文已完整核对':c.status==='reviewed_scope_complete'?'列明判定范围已核对':'判定范围仍有待补核内容';
  const items=Number.isInteger(c.reviewedJudgmentItemCount)&&Number.isInteger(c.expectedJudgmentItemCount)
    ? `<span>列明范围判定项：${c.reviewedJudgmentItemCount} / ${c.expectedJudgmentItemCount}</span>`
    : '<span>判定项总数尚未逐项确认</span>';
  const boundary=c.wholeStandardComplete?'已完整收录上述标准正文；仍须逐条核对适用主体、条件和例外，不能据此直接认定现场隐患。':'上述数量仅对应列明范围，不代表标准全部内容或现场已构成重大事故隐患。';
  return `<div class="coverage"><strong>${esc(label)}</strong><p>${esc(scope.label||'以本页列出的条文和核验范围为准')}</p><div class="coverage-counts"><span>已收录整条：${esc(c.reviewedWholeClauseCount??standard.clauses.length)}${Number.isInteger(c.expectedWholeClauseCount)?` / ${c.expectedWholeClauseCount}`:''}</span>${items}${Number.isInteger(c.expectedTableCount)?`<span>正文表格：${c.reviewedTableCount} / ${c.expectedTableCount}</span>`:''}</div><p>${esc(boundary)}</p>${standard.publicationBasis?`<p>官方规范正文公开范围核对：${esc(standard.publicationBasis.checked.slice(0,10))} · ${sourceLink(standard.publicationBasis.legalSourceUrl,'公开引用法律依据')}</p>`:''}</div>`;
}
function clauseHtml(clause,standard){
  const related=(clause.directHazardIds||[]).filter(id=>model.topic.associations.some(a=>a.hazardId===id&&a.lawVersionId===standard.lawVersionId)&&hazardById.has(id));
  const relatedHtml=related.map(id=>{const links=model.topic.associations.filter(a=>a.hazardId===id&&a.lawVersionId===standard.lawVersionId&&a.clauseId===clause.clauseId);return `<div><a href="${hazardLink(id)}">${esc(hazardById.get(id).title)} ↗</a>${links.map(a=>`<p class="association-scope"><strong>本条依据适用范围：</strong>${esc(a.applicability)}</p>`).join('')}</div>`;}).join('');
  const notes=(clause.applicationNotes||[]).map(note=>`<aside class="official-clarification"><strong>主管部门适用说明（非标准正文）</strong><p>${esc(note.summary)}</p><p class="clause-foot">官方答复：${esc(note.sourceDate)} · 本次核对：${esc(note.checked.slice(0,10))} ${sourceLink(note.sourceUrl,'查看官方答复')}</p></aside>`).join('');
  return `<details class="clause-card"><summary>${esc(clause.article)}<span class="clause-count">${related.length?`关联 ${related.length} 条专题隐患`:'暂无专题关联隐患'}</span></summary>${notes}${renderNormativeContent(clause)}<div class="clause-foot"><span>${esc(clause.status)}</span><span>核验：${esc(String(clause.checked||'未提供').slice(0,10))}</span>${sourceLink(clause.sourceUrl||standard.standardVersion.officialSourceUrl,'查看来源')}</div>${related.length?`<div class="clause-related">${relatedHtml}</div>`:''}</details>`;
}
function standardHtml(standard){
  const v=standard.standardVersion||{},name=v.name||v.documentNumber||standard.lawVersionId;
  const validity={active:'现行有效',upcoming:'尚未实施',repealed:'已废止',expired:'已届有效期'}[v.validityStatus]||v.validityStatus||'以核验快照为准';
  return `<section class="standard-card"><div class="standard-head"><h2>${esc(name)}${v.documentNumber&&!name.includes(v.documentNumber)?` <small>${esc(v.documentNumber)}</small>`:''}</h2><div class="standard-meta"><span>${esc(validity)}</span><span>实施：${esc(v.effectiveDate||'未提供')}</span></div><div class="source-links">${sourceLink(v.officialSourceUrl,'官方来源')}${standard.directHazardCount?`<a href="./?view=laws&amp;law=${encodeURIComponent(standard.lawVersionId)}">查看法规关联记录 ↗</a>`:''}</div></div>${coverageHtml(standard)}<div class="clause-list">${standard.clauses.map(c=>clauseHtml(c,standard)).join('')||'<p>当前搜索未匹配到已收录条文。</p>'}</div></section>`;
}
function hazardHtml(hazard){
  const associations=model.topic.associations.filter(a=>a.hazardId===hazard.id&&(!route.standard||a.lawVersionId===route.standard));
  const byLaw=new Map();for(const a of associations){const list=byLaw.get(a.lawVersionId)||[];list.push(a);byLaw.set(a.lawVersionId,list);}
  const bases=[...byLaw].map(([id,rows])=>{const standard=standardById.get(id),name=standard?.standardVersion?.name||id;return `<p>${esc(name)}</p>${rows.map(a=>`<p class="association-scope"><strong>本条依据适用范围：</strong>${esc(a.applicability||'逐项核对条文、适用条件与现场事实')}</p>`).join('')}`;}).join('');
  return `<article class="hazard-card"><span class="tag">${esc(hazard.displayCategory||hazard.category||'未分类')}</span><h3><a href="${hazardLink(hazard.id)}">${esc(hazard.title)}</a></h3><div class="hazard-bases">${bases}</div><a class="hazard-action" href="${hazardLink(hazard.id)}">查看隐患完整依据与适用条件 ↗</a></article>`;
}
function referenceHtml(entry){
  return `<section class="reference-card"><div class="standard-head"><h2>${esc(entry.title)}</h2><div class="standard-meta"><span>官方查阅入口 · 仅题录与短检索主题</span><span>发布机关：${esc(entry.issuer)}</span><span>实施：${esc(entry.effectiveDate)}</span></div><div class="source-links">${sourceLink(entry.officialLink,'官方发布页')}${sourceLink(entry.officialTextLink,'打开官方 PDF 原件')}</div></div><div class="reference-boundary"><strong>短检索主题不是判定原文</strong><p>本入口未提供法条原文或经审定的完整条件，不能独立用于现场重大事故隐患判定。请打开官方原件，逐项核对适用主体、条件、例外与注释。</p><p>题录与短主题核对：${esc(entry.checked.slice(0,10))} · 本入口已审条文：0 条 · 本入口专题关联隐患：0 条</p></div><ul class="reference-topics" aria-label="短检索主题，仅供定位">${entry.searchTopics.map(topic=>`<li><span class="reference-article">${esc(topic.article)}</span><span>${esc(topic.searchTopic)}</span></li>`).join('')}</ul></section>`;
}
function reviewedDirectoryText(entry){
  const standard=standardById.get(entry.lawVersionId);
  return standard?`<p class="directory-reviewed-text"><a href="?standard=${encodeURIComponent(standard.lawVersionId)}">另见已审正文：${standard.coverage.reviewedWholeClauseCount} 条 ↗</a> · 此题录与正文为同一版本，计数不相加</p>`:'';
}
function readingGroupHtml(group){
  const total=group.documents.reduce((n,doc)=>n+doc.firstLevelItemCount,0);
  const documents=[...group.documents].sort((a,b)=>Number(b.directoryReferenceId===group.primaryReferenceId)-Number(a.directoryReferenceId===group.primaryReferenceId));
  return `<div class="reading-boundary"><strong>官方原文查阅 · 未纳入本站现行判定条文</strong><p>${esc(group.warning)}</p><p>本组存在未核准明确施行日的文件；仅供查阅，不能据此自动作现场判定。${documents.length>1?'主文件与补充文件须配套查阅。':''}</p></div><details class="reading-details" data-reading-group="${esc(group.directoryGroupId)}"${openReadingGroups.has(group.directoryGroupId)?' open':''}><summary>展开官方原文（${documents.length>1?'主文件与补充文件，共 ':'共 '}${documents.length} 份）</summary><div class="reading-body"><p class="reading-count">${documents.map(doc=>`${doc.sourceIdentity.directoryGroup.role==='primary'?'主文件':'补充文件'} ${doc.firstLevelItemCount} 项`).join(' ＋ ')}，共 ${total} 个一级项原文；不计入现行判定条文和关联隐患数量。</p><p class="reading-review">原文查阅范围核对：${esc(group.checked.slice(0,10))} · ${sourceLink(group.publicationBasis.legalSourceUrl,'原文公开法律依据')}</p>${documents.map(doc=>{
    const identity=doc.sourceIdentity;
    const notes=doc.officialClarifications.map(note=>{
      const labels=doc.sections.flatMap(section=>section.items.filter(item=>note.appliesToItemIds.includes(item.id)).map(item=>`${section.title} ${item.articleLabel}`));
      return `<aside class="official-clarification reading-clarification"><strong>${note.textMode==='reviewed_summary'?'依据官方说明整理（非规范原文）':'官方说明待核，请查官方来源（非规范原文）'}</strong><p class="reading-note-scope">对应：${labels.map(esc).join('、')}</p><p class="reading-note-text">${esc(note.text)}</p><p>来源日期：${esc(note.sourceDate)}${note.sourcePages?` · 来源第 ${note.sourcePages.join('、')} 页`:''} · 核对：${esc(note.checked.slice(0,10))} ${sourceLink(note.sourceUrl,'查看官方说明')}</p></aside>`;
    }).join('');
    return `<article class="reading-document"><h4>${esc(identity.directoryGroup.role==='primary'?'主文件':'补充文件')}：${esc(identity.title)}</h4><div class="standard-meta"><span>文件日期：${esc(identity.publicationDate)}</span><span>${identity.effectiveDate===null?'原文件未明示施行日，未核准明确施行日':`原文件载明实施日期：${esc(identity.effectiveDate)}`}</span><span>原文核对：${esc(doc.checked.slice(0,10))}</span></div>${identity.effectiveDateNote?`<p class="directory-date-note">${esc(identity.effectiveDateNote)}</p>`:''}<div class="reading-current-use"><strong>官方当前使用证据（不作为施行起始日）</strong>${doc.currentUseEvidence.map(usage=>`<p>${esc(usage.sourceDate)} · ${esc(usage.summary)} ${sourceLink(usage.sourceUrl,'查看使用证据')}</p>`).join('')}</div><div class="reading-source-notice"><h5>官方通知原文</h5><blockquote>${esc(doc.noticeText)}</blockquote></div>${notes}${doc.sections.map(section=>`<section class="reading-section"><h5>${esc(section.title)}</h5>${section.items.map(item=>`<div class="reading-item"><h6>${esc(item.articleLabel)}</h6><blockquote>${esc(item.quote)}</blockquote></div>`).join('')}</section>`).join('')}</article>`;
  }).join('')}</div></details>`;
}
function directoryGroupHtml(group){
  return `<section class="directory-group"><div class="directory-group-head"><h2>${esc(group.label)}</h2><p>${group.entries.length} 份官方文件${group.entries.length>1?' · 主文件与补充文件须配套查阅':''}</p></div>${group.entries.map(entry=>`<article class="directory-document"><span class="tag">${entry.directoryGroup.role==='supplement'?'补充文件 · 须结合主文件':'主文件'}</span><h3>${esc(entry.title)}</h3><div class="standard-meta"><span>${esc(entry.statusLabel)}（题录状态，截至 ${esc(entry.statusAsOf)}）</span><span>${esc(entry.documentKind)}</span><span>文件日期：${esc(entry.publicationDate)}</span><span>${entry.effectiveDate===null?'实施日期未核准':`实施：${esc(entry.effectiveDate)}`}</span></div>${entry.effectiveDateNote?`<p class="directory-date-note">实施日期说明：${esc(entry.effectiveDateNote)}</p>`:''}<p class="directory-issuer">发布机关：${esc(entry.issuer)} · 文件性质：${esc(entry.legalNature)}</p><div class="directory-scope"><p><strong>查阅范围提示：</strong>${esc(entry.scopeHint)}</p><p><strong>适用边界提示：</strong>${esc(entry.scopeCaveat)}</p></div><div class="source-links">${sourceLink(entry.officialLink,'官方发布页')}${sourceLink(entry.officialTextLink,'官方原文入口')}</div><p class="directory-review">题录与范围提示核对：${esc(entry.checked.slice(0,10))} · 以上为题录与范围提示</p>${reviewedDirectoryText(entry)}</article>`).join('')}${readingByDirectory.has(group.id)?readingGroupHtml(readingByDirectory.get(group.id)):''}</section>`;
}
function referenceResults(){
  const directorySelection=route.standard.startsWith('directory:');
  const topics=references&&!directorySelection?selectMajorReferences(references,route):{referenceEntries:[],referenceStandardCount:0,searchTopicCount:0};
  const options={group:directorySelection?route.standard.slice('directory:'.length):'',query:route.query};
  const documents=directory&&(!route.standard||directorySelection)?selectMajorDirectory(directory,options):{directoryGroups:[],directoryGroupCount:0,documentCount:0};
  if(reading&&(!route.standard||directorySelection)){
    const matched=selectMajorReading(reading,options);
    const ids=new Set([...documents.directoryGroups.map(group=>group.id),...matched.readingGroups.map(group=>group.directoryGroupId)]);
    // Return each complete directory group once, keeping its original ordering.
    const complete=selectMajorDirectory(directory);
    documents.directoryGroups=complete.directoryGroups.filter(group=>ids.has(group.id));
    documents.directoryGroupCount=documents.directoryGroups.length;
    documents.documentCount=documents.directoryGroups.reduce((n,group)=>n+group.entries.length,0);
  }
  const readable=documents.directoryGroups.filter(group=>readingByDirectory.has(group.id));
  return {...topics,directory:documents,readingGroupCount:readable.length,readingDocumentCount:readable.reduce((n,group)=>n+group.entries.length,0)};
}
function referenceOptions(){
  const topics=references?`<optgroup label="短检索主题入口">${references.referenceEntries.map(entry=>`<option value="${esc(entry.id)}">${esc(entry.title)}</option>`).join('')}</optgroup>`:'';
  const groups=directory?`<optgroup label="行业官方文件目录">${directory.directoryGroups.map(group=>`<option value="directory:${esc(group.id)}">${esc(group.label)}</option>`).join('')}</optgroup>`:'';
  return '<option value="">全部官方查阅入口</option>'+topics+groups;
}
function referenceResultsHtml(results){
  if(!directory)return results.referenceEntries.map(referenceHtml).join('');
  const empty='<p class="view-help">当前条件无匹配入口</p>';
  return `${references?`<section class="reference-section"><h2>短检索主题入口</h2><p>仅用短主题定位官方条号，不提供判定原文。</p>${results.referenceEntries.map(referenceHtml).join('')||empty}</section>`:''}<section class="reference-section"><h2>行业官方文件目录</h2><p>${esc(directoryNotice())}</p><p>按目录组显示；命中主文或补充文件时，配套文件一并列示。组数不等于互斥行业数，文件数不等于已审条款数。</p>${results.directory.directoryGroups.map(directoryGroupHtml).join('')||empty}</section>`;
}
function checkedRoute(next){
  routeWarning='';
  if(next.view==='references'&&!hasReferenceData()){routeWarning='当前发布包未包含官方查阅入口，已显示已审条文目录。';next.view='clauses';next.standard='';}
  const activeStandards=next.view==='references'?referenceById:standardById;
  if(next.standard&&!activeStandards.has(next.standard)){routeWarning+=' 链接中的判定依据或官方查阅入口不在当前视图收录范围，已恢复为本视图全部入口。';next.standard='';}
  if(next.view==='references'&&next.category){routeWarning+=' 官方查阅入口不使用专业分类，已清除该条件。';next.category='';}
  const categories=new Set(model.hazards.map(h=>h.displayCategory||h.category||''));
  if(next.category&&!categories.has(next.category)){routeWarning+=' 链接中的专业分类当前没有专题关联记录，已清除该条件。';next.category='';}
  return next;
}
function render(historyMode='replace'){
  if(!model)return;
  const referenceView=route.view==='references',clauseView=route.view==='clauses';
  const results=referenceView?referenceResults():selectMajorResults(model,route);
  const tabId=referenceView?'referencesTab':clauseView?'clausesTab':'hazardsTab';
  for(const id of ['clausesTab','hazardsTab','referencesTab'])$('#'+id).setAttribute('aria-selected',String(id===tabId));
  $('#results').setAttribute('aria-labelledby',tabId);
  $('#categoryLabel').hidden=route.view!=='hazards';$('#topicQuery').value=route.query;$('#categoryFilter').value=route.category;
  $('#standardFilter').innerHTML=referenceView?referenceOptions():'<option value="">全部已收录依据</option>'+model.standards.map(s=>`<option value="${esc(s.lawVersionId)}">${esc(s.standardVersion.name)}${s.standardVersion.documentNumber&&!s.standardVersion.name.includes(s.standardVersion.documentNumber)?` ${esc(s.standardVersion.documentNumber)}`:''}</option>`).join('');
  $('#standardFilter').value=route.standard;
  $('#topicQuery').placeholder=referenceView?(directory?(reading?'搜索文件、文号、目录组或可查阅原文':'搜索文件名称、文号、目录组或查阅范围'):'搜索标准名称、文号、条号或短检索主题'):clauseView?'搜索标准名称、条款号或正文关键词':'搜索当前专题关联隐患';
  $('#viewHelp').textContent=referenceView?[references?.notice,directoryNotice(),reading?.notice].filter(Boolean).join(' '):clauseView?'条文按已核验范围收录；没有关联隐患的条文也可查看。':'仅展示与本专题判定依据存在已核验直接关联的隐患；专业分类可交叉筛选。记录不是现场判定结论。';
  const searchExplanation=results.matchKind==='related'
    ? '当前条件下没有原词或同义词结果，以下仅为相关概念参考；请核对设备、作业对象与判定适用条件。'
    : results.matchKind==='corrected'?`当前条件下没有原词结果，按“${results.interpretedQuery}”尝试纠错；请确认是否符合原意。`
    : results.matchKind==='colloquial'?`没有与原话完全一致的内容，已按“${results.interpretedQuery}”查找；请核对对象、缺陷与适用条件。`:'';
  $('#routeNotice').textContent=[routeWarning,results.queryNotice,searchExplanation].filter(Boolean).join(' ');$('#routeNotice').hidden=!$('#routeNotice').textContent;
  const total=referenceView?results.referenceStandardCount+results.directory.directoryGroupCount:clauseView?results.standards.reduce((n,s)=>n+s.clauses.length,0):results.hazards.length;
  $('#resultCount').textContent=referenceView?(directory?`短主题入口：${results.referenceStandardCount} 部 · ${results.searchTopicCount} 个短主题；文件目录：${results.directory.directoryGroupCount} 组 · ${results.directory.documentCount} 份官方文件${reading?`（题录计数，不计入现行判定条文）；其中 ${results.readingGroupCount} 组 ${results.readingDocumentCount} 份可展开原文`:"（分区计数，均非判定原文）"}`:`${results.referenceStandardCount} 部官方查阅入口 · ${results.searchTopicCount} 个短检索主题（非判定原文）`):clauseView?`${results.standards.length} 部依据 · ${total} 条已收录判定条文`:`${total} 条专题关联隐患`;
  $('#results').innerHTML=total?(referenceView?referenceResultsHtml(results):clauseView?results.standards.map(standardHtml).join(''):`<div class="hazard-grid">${results.hazards.map(hazardHtml).join('')}</div>`):'<div class="empty"><strong>当前条件没有匹配记录</strong>可缩短关键词或清除筛选；未检索到不代表不存在相关判定要求。</div>';
  const query=majorRouteQuery(route),url=`${location.pathname}${query?'?'+query:''}`;
  if(historyMode&&`${location.pathname}${location.search}`!==url)history[historyMode==='push'?'pushState':'replaceState'](null,'',url);
}
function bind(){
  const view=value=>{routeWarning='';if(value==='references'&&!hasReferenceData())return;if((value==='references')!==(route.view==='references')){if(route.standard||route.category)routeWarning='已切换查阅范围，清除了上一视图的依据与专业筛选。';route.standard='';route.category='';}route.view=value;render('push');};
  $('#results').addEventListener('toggle',event=>{const id=event.target.dataset?.readingGroup;if(id){if(event.target.open)openReadingGroups.add(id);else openReadingGroups.delete(id);}},true);
  $('#clausesTab').onclick=()=>view('clauses');$('#hazardsTab').onclick=()=>view('hazards');$('#referencesTab').onclick=()=>view('references');
  $('#topicQuery').oninput=()=>{routeWarning='';route.query=$('#topicQuery').value;render();};
  $('#clearQuery').onclick=()=>{routeWarning='';route.query='';render();$('#topicQuery').focus();};
  $('#standardFilter').onchange=()=>{routeWarning='';route.standard=$('#standardFilter').value;render('push');};
  $('#categoryFilter').onchange=()=>{routeWarning='';route.category=$('#categoryFilter').value;render('push');};
  $('#resetTopic').onclick=()=>{routeWarning='';route={view:route.view,standard:'',category:'',query:''};render('push');};
  window.addEventListener('popstate',()=>{if(model){route=checkedRoute(parseMajorRoute(location.search));render(null);}});
  for(const id of ['clausesTab','hazardsTab','referencesTab'])$('#'+id).onkeydown=event=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();const tabs=['clausesTab','hazardsTab',...(hasReferenceData()?['referencesTab']:[])],i=tabs.indexOf(id);const target=event.key==='Home'?tabs[0]:event.key==='End'?tabs.at(-1):tabs[(i+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length];$('#'+target).click();$('#'+target).focus();}};
}
async function boot(){
  bind();
  try{
    const files=await new VerifiedFiles('.').init({required:true});
    const manifest=await files.read('data/manifest.json');
    const paths=manifest.files||{};
    if(!paths.majorCriteriaCatalog||!paths.majorCriteriaTopic||!paths.searchIndex)throw new Error('当前发布包尚未包含重大隐患专题数据');
    const [catalog,topic,index]=await Promise.all([files.read(paths.majorCriteriaCatalog),files.read(paths.majorCriteriaTopic),files.read(paths.searchIndex)]);
    model=validateMajorData(catalog,topic,index,files.manifest.asOf);
    hazardById=new Map(model.hazards.map(h=>[h.id,h]));standardById=new Map(model.standards.map(s=>[s.lawVersionId,s]));
    if(Object.hasOwn(paths,'majorCriteriaReferences')){
      if(typeof paths.majorCriteriaReferences!=='string'||!paths.majorCriteriaReferences)throw new Error('官方查阅入口文件路径无效');
      references=validateMajorReferences(await files.read(paths.majorCriteriaReferences),files.manifest.asOf);
      if(references.referenceEntries.some(entry=>standardById.has(entry.lawVersionId)))throw new Error('官方查阅入口与已审条文目录身份重复');
      referenceById=new Map(references.referenceEntries.map(entry=>[entry.id,entry]));
    }
    if(Object.hasOwn(paths,'majorCriteriaDirectory')){
      if(typeof paths.majorCriteriaDirectory!=='string'||!paths.majorCriteriaDirectory)throw new Error('行业官方文件目录路径无效');
      directory=validateMajorDirectory(await files.read(paths.majorCriteriaDirectory),files.manifest.asOf);
      validateDirectoryCatalogLinks(model,directory);
      const knownVersions=new Set((references?.referenceEntries||[]).map(entry=>entry.lawVersionId));
      if(directory.entries.some(entry=>knownVersions.has(entry.lawVersionId)))throw new Error('行业官方文件目录与既有入口身份重复');
      for(const group of directory.directoryGroups)referenceById.set(`directory:${group.id}`,group);
    }
    if(Object.hasOwn(paths,'majorCriteriaReading')){
      if(typeof paths.majorCriteriaReading!=='string'||!paths.majorCriteriaReading)throw new Error('官方原文查阅文件路径无效');
      reading=validateMajorReading(await files.read(paths.majorCriteriaReading),files.manifest.asOf);
      if(!directory)throw new Error('官方原文查阅缺少配套目录');
      validateReadingDirectoryLinks(reading,directory);
      const currentVersions=new Set([...standardById.keys(),...(references?.referenceEntries||[]).map(entry=>entry.lawVersionId)]);
      if(reading.readingGroups.some(group=>group.documents.some(doc=>currentVersions.has(doc.sourceIdentity.lawVersionId))))throw new Error('官方原文查阅与判定条文或短主题入口身份重复');
      readingByDirectory=new Map(reading.readingGroups.map(group=>[group.directoryGroupId,group]));
    }
    $('#referencesTab').hidden=!hasReferenceData();
    $('#snapshotDate').textContent=`核验快照 ${catalog.asOf}`;
    const clauseCount=model.standards.reduce((n,standard)=>n+standard.clauses.length,0);
    $('#catalogSummary').textContent=`${model.standards.length} 部已审条文目录 · ${clauseCount} 条已收录整条 · ${model.hazards.length} 条专题关联隐患`+(references?`；另有 ${references.referenceEntries.length} 部官方查阅入口 · ${references.referenceEntries.reduce((n,entry)=>n+entry.searchTopicCount,0)} 个短检索主题`:'')+(directory?`；行业官方文件目录 ${directory.directoryGroupCount} 组 · ${directory.documentCount} 份官方文件（不计入已审条文）${reading?`，其中 ${reading.readingGroupCount} 组 ${reading.sourceDocumentCount} 份可展开原文`:''}`:'');
    const today=new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
    $('#snapshotNotice').textContent=snapshotNoticeText(catalog.asOf,today);$('#snapshotNotice').hidden=!$('#snapshotNotice').textContent;
    const review=topic.coverage||{};
    const messages=(topic.warnings||[]).map(w=>typeof w==='string'?w:w.message).filter(Boolean);
    if(Number.isInteger(review.excludedHazardCount)&&review.excludedHazardCount>0)messages.unshift(`${review.excludedHazardCount} 条候选关联隐患暂未纳入专题：${review.exclusionReason||'条文或适用关联待复核'}。`);
    $('#reviewNotice').textContent=[...new Set(messages)].join(' ');$('#reviewNotice').hidden=!$('#reviewNotice').textContent;
    const categories=[...new Set(model.hazards.map(h=>h.displayCategory||h.category).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'zh-CN'));
    $('#categoryFilter').innerHTML='<option value="">全部专业分类</option>'+categories.map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join('');
    document.querySelectorAll('button:disabled,input:disabled,select:disabled').forEach(el=>el.disabled=false);
    route=checkedRoute(route);render();
  }catch(error){
    model=null;references=null;directory=null;reading=null;readingByDirectory.clear();openReadingGroups.clear();referenceById.clear();hazardById.clear();standardById.clear();
    document.querySelectorAll('button,input,select').forEach(el=>el.disabled=true);$('#referencesTab').hidden=true;
    $('#snapshotDate').textContent='专题数据未能完成校验';$('#catalogSummary').textContent='没有载入可用的已核验专题数据';
    $('#resultCount').textContent='专题暂时不可用';$('#results').innerHTML=`<div class="empty"><strong>数据未能通过读取或一致性校验</strong>${esc(error.message)}。请刷新后重试，或先使用法规库查阅已发布依据。</div>`;
  }
}
if(typeof document!=='undefined')boot();
