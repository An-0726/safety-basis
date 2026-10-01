import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import * as model from '../web/js/major-criteria-model.js';
import * as referenceModel from '../web/js/major-criteria-reference-model.js';
import * as directoryModel from '../web/js/major-criteria-directory-model.js';
import * as readingModel from '../web/js/major-criteria-reading-model.js';
import * as normativeContent from '../web/js/normative-content.js';

const source=fs.readFileSync(new URL('../web/js/major-criteria.js',import.meta.url),'utf8').replace(/^import .*;\r?\n/gm,'').replace("if(typeof document!=='undefined')boot();",'globalThis.testBoot=boot;');
const fixture=()=>{
  const asOf='2026-10-01',lawVersionId='LV_TEST',hazardId='H_TEST';
  const clauses=['4.1','4.2'].map((n,i)=>({clauseId:`C${i}`,article:`第${n}条`,quote:i?'电梯有下列情形的，应核实判定条件。':'压力容器有下列情形的，应核实判定条件。',checked:asOf,status:'现行有效',sourceUrl:'https://example.org/standard',lawVersionId,granularity:'whole_clause',directHazardIds:i?[]:[hazardId]}));
  const standard={id:lawVersionId,lawVersionId,standardVersion:{lawId:'LF_TEST',name:'特种设备重大事故隐患判定准则',documentNumber:'GB 45067-2024',versionKey:'2024',effectiveDate:'2024-12-01',endDate:'',validityStatus:'active',officialSourceUrl:'https://example.org/standard'},officialScope:{label:'仅第4.1—4.2条测试范围，不代表完整标准',sourceUrls:['https://example.org/standard'],wholeStandardComplete:false},coverage:{status:'reviewed_scope_complete',reviewedClauseCount:2,reviewedWholeClauseCount:2,reviewedSubitemClauseCount:0,expectedWholeClauseCount:2,expectedJudgmentItemCount:null,reviewedJudgmentItemCount:null,wholeStandardComplete:false},clauses,directHazardIds:[hazardId],directHazardCount:1};
  const catalog={schemaVersion:1,asOf,wholeNormNotFieldFinding:true,catalogScope:'controlled_reviewed_standards_only',allIndustryCoverage:false,standards:[standard]};
  const topic={schemaVersion:1,asOf,wholeNormNotFieldFinding:true,associations:[{hazardId,linkId:'K_TEST',clauseId:'C0',lawVersionId,role:'direct',applicability:'仅适用于已确认的压力容器现场条件',jurisdictionCode:'CN'}],hazardIds:[hazardId],coverage:{excludedHazardCount:1,excludedAssociationCount:1,exclusionReason:'条文或适用关联待复核'}};
  const index=[{id:hazardId,title:'压力容器测试隐患',category:'特种设备',displayCategory:'特种设备',status:'已核验',publishable:true,searchText:'压力容器 测试隐患'}];
  return {catalog,topic,index};
};

async function load({search='',mutate,includeReferences=false,includeDirectory=false,includeReading=false}={}){
  const f=fixture();f.references=referenceFixture();f.directory=directoryFixture();f.reading=readingFixture(f.directory);f.paths={majorCriteriaCatalog:'catalog',majorCriteriaTopic:'topic',searchIndex:'index',...(includeReferences?{majorCriteriaReferences:'references'}:{}),...(includeDirectory?{majorCriteriaDirectory:'directory'}:{}),...(includeReading?{majorCriteriaReading:'reading'}:{})};mutate?.(f);
  const ids=['snapshotDate','catalogSummary','snapshotNotice','reviewNotice','clausesTab','hazardsTab','referencesTab','results','categoryLabel','topicQuery','standardFilter','categoryFilter','viewHelp','routeNotice','resultCount','clearQuery','resetTopic'];
  const elements=new Map(ids.map(id=>[id,{id,value:'',textContent:'',innerHTML:'',hidden:false,disabled:true,attributes:{},eventHandlers:{},addEventListener(k,v){this.eventHandlers[k]=v;},setAttribute(k,v){this.attributes[k]=v;},focus(){this.focused=true;},click(){this.onclick?.();}}]));
  const listeners={},historyCalls=[];
  const location={pathname:'/major-criteria.html',search};
  const update=(kind,_state,_title,url)=>{historyCalls.push({kind,url});location.search=new URL(url,'https://example.org').search;};
  class VerifiedFiles{
    constructor(){this.manifest={asOf:f.catalog.asOf};}
    async init(){return this;}
    async read(path){return {'data/manifest.json':{files:f.paths},catalog:f.catalog,topic:f.topic,index:f.index,references:f.references,directory:f.directory,reading:f.reading}[path];}
  }
  const context={...model,...referenceModel,...directoryModel,...readingModel,...normativeContent,VerifiedFiles,URL,URLSearchParams,Intl,Date,location,history:{pushState:update.bind(null,'push'),replaceState:update.bind(null,'replace')},window:{addEventListener(k,v){listeners[k]=v;}},document:{querySelector(selector){return elements.get(selector.slice(1));},querySelectorAll(){return [...elements.values()];}}};
  vm.createContext(context);new vm.Script(source).runInContext(context);await context.testBoot();
  return {elements,listeners,historyCalls,location,fixture:f};
}

test('controller shows canonical clauses without H and controlled coverage/review notice',async()=>{
  const {elements}=await load();
  assert.match(elements.get('results').innerHTML,/第4\.1条/);
  assert.match(elements.get('results').innerHTML,/第4\.2条/);
  assert.match(elements.get('results').innerHTML,/暂无专题关联隐患/);
  assert.match(elements.get('results').innerHTML,/不代表标准全部内容/);
  assert.match(elements.get('reviewNotice').textContent,/1 条候选关联隐患暂未纳入/);
  assert.equal(elements.get('categoryLabel').hidden,true);
});

test('controller switches views, displays link applicability and restores URL via popstate',async()=>{
  const {elements,listeners,location,historyCalls}=await load();
  elements.get('hazardsTab').click();
  assert.equal(elements.get('categoryLabel').hidden,false);
  assert.match(elements.get('results').innerHTML,/仅适用于已确认的压力容器现场条件/);
  assert.equal(elements.get('resultCount').textContent,'1 条专题关联隐患');
  assert.ok(historyCalls.some(x=>x.kind==='push'&&x.url.includes('view=hazards')));
  location.search='?standard=LV_TEST&q=电梯';listeners.popstate();
  assert.equal(elements.get('categoryLabel').hidden,true);
  assert.match(elements.get('results').innerHTML,/第4\.2条/);
  assert.doesNotMatch(elements.get('results').innerHTML,/第4\.1条/);
  assert.ok(historyCalls.every(x=>!x.url.includes('??')));
});

test('controller standard-number search finds canonical clauses and wrong edition returns explicit empty state',async()=>{
  const {elements}=await load();
  elements.get('topicQuery').value='GB45067';elements.get('topicQuery').oninput();
  assert.match(elements.get('resultCount').textContent,/2 条已收录判定条文/);
  elements.get('topicQuery').value='GB45067-2025';elements.get('topicQuery').oninput();
  assert.match(elements.get('results').innerHTML,/当前条件没有匹配记录/);
  elements.get('clearQuery').click();assert.match(elements.get('resultCount').textContent,/2 条已收录判定条文/);
});

test('controller malformed catalog fails closed and renders no source clauses',async()=>{
  const {elements}=await load({mutate:f=>{f.catalog.schemaVersion=99;}});
  assert.equal(elements.get('resultCount').textContent,'专题暂时不可用');
  assert.match(elements.get('results').innerHTML,/未能通过读取或一致性校验/);
  assert.doesNotMatch(elements.get('results').innerHTML,/压力容器有下列情形/);
  assert.equal(elements.get('hazardsTab').disabled,true);
});

test('controller exposes related-device fallback and typo correction instead of implying exact matches',async()=>{
  const {elements}=await load({mutate:f=>{f.catalog.standards[0].clauses[1].quote='场内电动车的检测要求';}});
  elements.get('topicQuery').value='电动自行车';elements.get('topicQuery').oninput();
  assert.match(elements.get('routeNotice').textContent,/相关概念参考.*设备.*判定适用条件/);
  elements.get('topicQuery').value='压历容器';elements.get('topicQuery').oninput();
  assert.match(elements.get('routeNotice').textContent,/按“压力容器”尝试纠错/);
});

test('topic H search uses strict standard identities and shows abbreviation explanation',async()=>{
  const {elements}=await load();elements.get('hazardsTab').click();
  for(const q of ['GB4506','GB45067-202','GB45067-2025','GB/T45067']){
    elements.get('topicQuery').value=q;elements.get('topicQuery').oninput();
    assert.equal(elements.get('resultCount').textContent,'0 条专题关联隐患',q);
  }
  elements.get('topicQuery').value='GB45067';elements.get('topicQuery').oninput();
  assert.equal(elements.get('resultCount').textContent,'1 条专题关联隐患');
  elements.get('topicQuery').value='重大隐患';elements.get('topicQuery').oninput();
  assert.equal(elements.get('resultCount').textContent,'1 条专题关联隐患');
  assert.match(elements.get('routeNotice').textContent,/按检索别名.*不代表现场已构成/);
});

test('unknown standard URL gets an explicit compatibility warning and reset clears it',async()=>{
  const {elements}=await load({search:'?standard=UNKNOWN'});
  assert.match(elements.get('routeNotice').textContent,/不在当前视图收录范围/);
  elements.get('resetTopic').click();assert.equal(elements.get('routeNotice').hidden,true);
});

test('shared and topic headers have explicit narrow-screen wrapping for the separate entry',()=>{
  const shared=fs.readFileSync(new URL('../web/style.css',import.meta.url),'utf8');
  const topic=fs.readFileSync(new URL('../web/major-criteria.css',import.meta.url),'utf8');
  assert.match(shared,/@media\(max-width:780px\).*header nav\{[^}]*flex-basis:100%;[^}]*flex-wrap:wrap/s);
  assert.match(topic,/@media\(max-width:760px\).*nav\{[^}]*order:3;[^}]*width:100%/s);
});

function referenceFixture(){
  return {schemaVersion:'safety-major-criteria-references-v1',asOf:'2026-10-01',catalogScope:'official_reference_entries_only',allIndustryCoverage:false,wholeNormNotFieldFinding:true,notice:'这些短主题仅帮助定位条款，不是法条原文，也不能独立用于重大事故隐患判定；请查官方原件。',referenceEntries:[{
    id:'REF_AQ_TEST',lawId:'LF_AQ_TEST',lawVersionId:'LV_AQ_TEST',title:'化工和危险化学品生产经营企业重大生产安全事故隐患判定准则 AQ 3067-2026',standardNumber:'AQ 3067-2026',versionKey:'source-version',issuer:'应急管理部',effectiveDate:'2026-09-30',validityStatus:'active',checked:'2026-10-01',officialLink:'https://www.mem.gov.cn/standard.html',officialTextLink:'https://www.mem.gov.cn/standard.pdf',contentKind:'reference_only',textMode:'link_only',publicationPermission:'metadata_only',fullTextReviewed:false,fullQuotePublicationReady:false,publicationReady:{metadata:true,searchTopics:true,fullText:false},reviewedClauseCount:0,directHazardCount:0,standaloneDeterminationAllowed:false,wholeStandardComplete:false,searchTopicCount:2,searchTopics:[{article:'5.1.1',searchTopic:'负责人考核',contentKind:'search_topic_only',isOfficialQuote:false,standaloneDeterminationAllowed:false},{article:'5.1.2',searchTopic:'管理人员任职条件',contentKind:'search_topic_only',isOfficialQuote:false,standaloneDeterminationAllowed:false}]
  }]};
}

test('reference view counts official entries and short topics separately without changing reviewed clauses or H',async()=>{
  const {elements}=await load({includeReferences:true});
  assert.equal(elements.get('referencesTab').hidden,false);
  assert.equal(elements.get('catalogSummary').textContent,'1 部已审条文目录 · 2 条已收录整条 · 1 条专题关联隐患；另有 1 部官方查阅入口 · 2 个短检索主题');
  assert.equal(elements.get('resultCount').textContent,'1 部依据 · 2 条已收录判定条文');
  assert.doesNotMatch(elements.get('results').innerHTML,/AQ 3067/);
  elements.get('referencesTab').click();
  assert.equal(elements.get('resultCount').textContent,'1 部官方查阅入口 · 2 个短检索主题（非判定原文）');
  assert.equal(elements.get('categoryLabel').hidden,true);
  assert.match(elements.get('results').innerHTML,/负责人考核/);
  assert.match(elements.get('results').innerHTML,/题录与短主题核对：2026-10-01/);
  assert.match(elements.get('results').innerHTML,/不能独立用于现场重大事故隐患判定/);
  assert.match(elements.get('results').innerHTML,/打开官方 PDF 原件/);
  assert.doesNotMatch(elements.get('results').innerHTML,/<blockquote|class="clause-card"|\?id=|查看隐患完整依据/);
  elements.get('hazardsTab').click();
  assert.equal(elements.get('resultCount').textContent,'1 条专题关联隐患');
  assert.doesNotMatch(elements.get('results').innerHTML,/负责人考核|AQ 3067/);
});

test('reference topic, article and compact standard search remain reference-only',async()=>{
  const {elements}=await load({includeReferences:true,search:'?view=references'});
  for(const [query,topics] of [['AQ3067',2],['AQ 3067-2026',2],['5.1.1',1],['负责人',1]]){
    elements.get('topicQuery').value=query;elements.get('topicQuery').oninput();
    assert.equal(elements.get('resultCount').textContent,`1 部官方查阅入口 · ${topics} 个短检索主题（非判定原文）`,query);
  }
  for(const query of ['AQ3067-2025','GB3067','AQ/T3067','AQ30670','5.1.10']){
    elements.get('topicQuery').value=query;elements.get('topicQuery').oninput();
    assert.equal(elements.get('resultCount').textContent,'0 部官方查阅入口 · 0 个短检索主题（非判定原文）',query);
  }
  elements.get('clearQuery').click();assert.equal(elements.get('resultCount').textContent,'1 部官方查阅入口 · 2 个短检索主题（非判定原文）');
});

test('reference routes switch standard namespace explicitly and Back restores each view without loops',async()=>{
  const {elements,listeners,location,historyCalls}=await load({includeReferences:true,search:'?view=hazards&standard=LV_TEST&category=特种设备'});
  elements.get('referencesTab').click();
  assert.match(elements.get('routeNotice').textContent,/清除了上一视图/);
  assert.equal(elements.get('standardFilter').value,'');
  assert.equal(elements.get('categoryFilter').value,'');
  elements.get('standardFilter').value='REF_AQ_TEST';elements.get('standardFilter').onchange();
  const before=historyCalls.length;
  location.search='?view=hazards&standard=LV_TEST&category=特种设备';listeners.popstate();
  assert.equal(historyCalls.length,before);
  assert.equal(elements.get('standardFilter').value,'LV_TEST');
  assert.equal(elements.get('resultCount').textContent,'1 条专题关联隐患');
  location.search='?view=references&standard=REF_AQ_TEST&q=5.1.1';listeners.popstate();
  assert.equal(historyCalls.length,before);
  assert.equal(elements.get('standardFilter').value,'REF_AQ_TEST');
  assert.equal(elements.get('resultCount').textContent,'1 部官方查阅入口 · 1 个短检索主题（非判定原文）');
  elements.get('resetTopic').click();
  assert.equal(elements.get('resultCount').textContent,'1 部官方查阅入口 · 2 个短检索主题（非判定原文）');
  assert.ok(historyCalls.every(call=>!call.url.includes('??')));
});

test('old bundle without optional references retains two views and explains a new reference URL',async()=>{
  const {elements}=await load({search:'?view=references&standard=REF_AQ_TEST'});
  assert.equal(elements.get('referencesTab').hidden,true);
  assert.match(elements.get('routeNotice').textContent,/未包含官方查阅入口/);
  assert.equal(elements.get('resultCount').textContent,'1 部依据 · 2 条已收录判定条文');
  assert.doesNotMatch(elements.get('catalogSummary').textContent,/官方查阅入口/);
  elements.get('hazardsTab').click();assert.equal(elements.get('resultCount').textContent,'1 条专题关联隐患');
});

test('reference tab keyboard navigation uses three visible tabs and two for legacy data',async()=>{
  for(const includeReferences of [false,true]){
    const {elements}=await load({includeReferences});
    elements.get('hazardsTab').onkeydown({key:'End',preventDefault(){}});
    const selected=includeReferences?'referencesTab':'hazardsTab';
    assert.equal(elements.get(selected).attributes['aria-selected'],'true');
    assert.equal(elements.get(selected).focused,true);
    elements.get(selected).onkeydown({key:'ArrowRight',preventDefault(){}});
    assert.equal(elements.get('clausesTab').attributes['aria-selected'],'true');
  }
});

for(const [label,mutate] of [
  ['quote injection',f=>{f.references.referenceEntries[0].searchTopics[0].quote='不得公开的原文';}],
  ['H association',f=>{f.references.referenceEntries[0].directHazardCount=1;}],
  ['reviewed clause inflation',f=>{f.references.referenceEntries[0].reviewedClauseCount=53;}],
  ['full text approval',f=>{f.references.referenceEntries[0].fullTextReviewed=true;}],
  ['full quote permission',f=>{f.references.referenceEntries[0].fullQuotePublicationReady=true;}],
  ['standalone determination',f=>{f.references.referenceEntries[0].searchTopics[0].standaloneDeterminationAllowed=true;}],
  ['count mismatch',f=>{f.references.referenceEntries[0].searchTopicCount=53;}],
  ['date mismatch',f=>{f.references.asOf='2026-09-30';}],
  ['catalog identity overlap',f=>{f.references.referenceEntries[0].lawVersionId='LV_TEST';}],
  ['declared but missing payload',f=>{f.references=undefined;}],
  ['declared but invalid path',f=>{f.paths.majorCriteriaReferences=null;}]
])test(`invalid reference payload fails closed: ${label}`,async()=>{
  const {elements,listeners,location}=await load({includeReferences:true,mutate});
  location.search='?view=hazards';listeners.popstate();
  assert.equal(elements.get('resultCount').textContent,'专题暂时不可用');
  assert.doesNotMatch(elements.get('results').innerHTML,/负责人考核|不得公开的原文|压力容器有下列情形/);
  assert.equal(elements.get('hazardsTab').disabled,true);
});


test('reference route round trips with its independent selector and never leaks into clause selection',()=>{
  const route={view:'references',standard:'REF_AQ_TEST',category:'',query:'AQ3067 5.1.1'};
  assert.deepEqual(model.parseMajorRoute('?'+model.majorRouteQuery(route)),route);
  const f=fixture(),validated=model.validateMajorData(f.catalog,f.topic,f.index,f.catalog.asOf);
  assert.equal(model.selectMajorResults(validated,{view:'clauses',query:'AQ3067'}).standards.length,0);
  assert.equal(model.selectMajorResults(validated,{view:'hazards',query:'AQ3067'}).hazards.length,0);
});


test('reference metadata is escaped and a category deep link is explicitly cleared',async()=>{
  const {elements}=await load({includeReferences:true,search:'?view=references&category=特种设备',mutate:f=>{f.references.referenceEntries[0].title='<script>alert(1)</script> AQ 3067-2026';}});
  assert.match(elements.get('routeNotice').textContent,/官方查阅入口不使用专业分类/);
  assert.equal(elements.get('categoryFilter').value,'');
  assert.match(elements.get('results').innerHTML,/&lt;script&gt;/);
  assert.doesNotMatch(elements.get('results').innerHTML,/<script>/);
});


test('a valid empty reference snapshot shows zero entry count without borrowing reviewed clauses',async()=>{
  const {elements}=await load({includeReferences:true,search:'?view=references',mutate:f=>{f.references.referenceEntries=[];}});
  assert.equal(elements.get('referencesTab').hidden,false);
  assert.equal(elements.get('resultCount').textContent,'0 部官方查阅入口 · 0 个短检索主题（非判定原文）');
  assert.match(elements.get('catalogSummary').textContent,/1 部已审条文目录 · 2 条已收录整条.*另有 0 部官方查阅入口 · 0 个短检索主题/);
  assert.doesNotMatch(elements.get('results').innerHTML,/压力容器有下列情形/);
  elements.get('clausesTab').click();assert.equal(elements.get('resultCount').textContent,'1 部依据 · 2 条已收录判定条文');
});

test('reference checked timestamp is labeled only as metadata and short-topic review date',async()=>{
  const {elements}=await load({includeReferences:true,search:'?view=references',mutate:f=>{f.references.referenceEntries[0].checked='2026-10-01T08:58:25+00:00';}});
  assert.match(elements.get('results').innerHTML,/题录与短主题核对：2026-10-01/);
  assert.doesNotMatch(elements.get('results').innerHTML,/08:58:25|正文审核|已审原文/);
});

function directoryFixture(){
  const group=(id,label,primaryReferenceId,documentIds)=>({id,label,primaryReferenceId,documentIds});
  const entry=(id,groupId,label,title,documentNumber,extra={})=>({id,lawId:'LF_'+id,lawVersionId:'LV_'+id,title,documentNumber,versionKey:documentNumber,issuer:'测试发布机关',documentKind:'部门规范性文件',legalNature:'部门规范性文件',criterionKind:'major_hazard_determination',publicationDate:'2024-02-03',effectiveDate:'2024-03-01',effectiveDateNote:'',referenceStatus:'current',statusLabel:'现行有效',statusAsOf:'2026-10-01',checked:'2026-10-01T09:39:09+00:00',officialLink:'https://www.mem.gov.cn/test.html',officialTextLink:'https://www.mem.gov.cn/test.pdf',directoryGroup:{id:groupId,label,role:'primary'},requiredCompanionIds:[],supplementsReferenceId:null,scopeHint:'仅用于测试题录查阅范围提示',scopeCaveat:'须查阅官方原件，不得据题录独立判定',contentKind:'official_document_reference_only',textMode:'link_only',publicationPermission:'metadata_only',fullTextReviewed:false,fullQuotePublicationReady:false,publicationReady:{metadata:true,fullText:false},reviewedClauseCount:0,directHazardCount:0,searchTopicCount:0,standaloneDeterminationAllowed:false,wholeStandardComplete:false,...extra});
  return {schemaVersion:'safety-major-criteria-directory-v1',catalogScope:'controlled_official_metadata_directory',allIndustryCoverage:false,wholeNormNotFieldFinding:true,asOf:'2026-10-01',notice:'仅提供官方文件题录；目录组并非互斥行业，不能独立用于现场判定。',directoryGroupCount:2,documentCount:3,directoryGroups:[group('fire','消防重大火灾','DIR_FIRE',['DIR_FIRE']),group('noncoal','金属非金属矿山','DIR_MINE',['DIR_MINE','DIR_SUPPLEMENT'])],entries:[entry('DIR_FIRE','fire','消防重大火灾','重大火灾隐患判定规则 GB 35181-2025','GB 35181-2025'),entry('DIR_MINE','noncoal','金属非金属矿山','金属非金属矿山重大事故隐患判定标准','矿安〔2022〕88号',{requiredCompanionIds:['DIR_SUPPLEMENT']}),entry('DIR_SUPPLEMENT','noncoal','金属非金属矿山','金属非金属矿山补充情形','矿安〔2024〕41号',{directoryGroup:{id:'noncoal',label:'金属非金属矿山',role:'supplement'},supplementsReferenceId:'DIR_MINE',effectiveDate:null,effectiveDateNote:'通知未单列实施日；不以发布日期推填',referenceStatus:'current_in_use',statusLabel:'现行使用中'})]};
}

test('official directory counts groups and documents separately from reviewed clauses, H and AQ topics',async()=>{
  const {elements}=await load({includeReferences:true,includeDirectory:true});
  assert.equal(elements.get('resultCount').textContent,'1 部依据 · 2 条已收录判定条文');
  assert.match(elements.get('catalogSummary').textContent,/1 部已审条文目录 · 2 条已收录整条 · 1 条专题关联隐患/);
  assert.match(elements.get('catalogSummary').textContent,/另有 1 部官方查阅入口 · 2 个短检索主题；行业官方文件目录 2 组 · 3 份官方文件（不计入已审条文）/);
  elements.get('referencesTab').click();
  assert.equal(elements.get('resultCount').textContent,'短主题入口：1 部 · 2 个短主题；文件目录：2 组 · 3 份官方文件（分区计数，均非判定原文）');
  const html=elements.get('results').innerHTML;
  assert.match(html,/短检索主题入口/);assert.match(html,/行业官方文件目录/);
  assert.match(html,/组数不等于互斥行业数/);
  assert.doesNotMatch(html,/<blockquote|class="clause-card"|href="\.\/\?id=/);
  elements.get('hazardsTab').click();assert.equal(elements.get('resultCount').textContent,'1 条专题关联隐患');
});

test('directory supplement search keeps the complete group and does not manufacture a second industry',async()=>{
  const {elements}=await load({includeReferences:true,includeDirectory:true,search:'?view=references&q=矿安〔2024〕41号'});
  assert.equal(elements.get('resultCount').textContent,'短主题入口：0 部 · 0 个短主题；文件目录：1 组 · 2 份官方文件（分区计数，均非判定原文）');
  assert.match(elements.get('results').innerHTML,/金属非金属矿山重大事故隐患判定标准/);
  assert.match(elements.get('results').innerHTML,/金属非金属矿山补充情形/);
  assert.match(elements.get('results').innerHTML,/主文件与补充文件须配套查阅/);
  assert.match(elements.get('results').innerHTML,/补充文件 · 须结合主文件/);
});

test('directory unknown implementation date remains unknown with the original note and metadata status',async()=>{
  const {elements}=await load({includeDirectory:true,search:'?view=references&standard=directory:noncoal'});
  const html=elements.get('results').innerHTML;
  assert.match(html,/实施日期未核准/);
  assert.match(html,/通知未单列实施日；不以发布日期推填/);
  assert.match(html,/现行使用中（题录状态，截至 2026-10-01）/);
  assert.match(html,/文件日期：2024-02-03/);
  assert.doesNotMatch(html,/实施：2024-02-03/);
  assert.match(html,/题录与范围提示核对：2026-10-01/);
  assert.doesNotMatch(html,/正文核验|全文已审/);
});

test('directory and AQ selectors use independent namespaces and Back restores each exact selection',async()=>{
  const {elements,location,listeners,historyCalls}=await load({includeReferences:true,includeDirectory:true,search:'?view=references&standard=directory:noncoal'});
  assert.equal(elements.get('standardFilter').value,'directory:noncoal');
  assert.match(elements.get('resultCount').textContent,/短主题入口：0 部.*文件目录：1 组 · 2 份/);
  elements.get('standardFilter').value='REF_AQ_TEST';elements.get('standardFilter').onchange();
  assert.match(elements.get('resultCount').textContent,/短主题入口：1 部.*文件目录：0 组 · 0 份/);
  const n=historyCalls.length;location.search='?view=references&standard=directory:noncoal';listeners.popstate();
  assert.equal(historyCalls.length,n);assert.equal(elements.get('standardFilter').value,'directory:noncoal');
  assert.match(elements.get('resultCount').textContent,/文件目录：1 组 · 2 份/);
  elements.get('resetTopic').click();assert.match(elements.get('resultCount').textContent,/短主题入口：1 部.*文件目录：2 组 · 3 份/);
  elements.get('clausesTab').click();assert.equal(elements.get('standardFilter').value,'');
  assert.equal(elements.get('resultCount').textContent,'1 部依据 · 2 条已收录判定条文');
  assert.ok(historyCalls.every(call=>!call.url.includes('??')));
});

test('directory-only manifest enables the official view without requiring the AQ payload',async()=>{
  const {elements}=await load({includeDirectory:true,search:'?view=references'});
  assert.equal(elements.get('referencesTab').hidden,false);
  assert.match(elements.get('resultCount').textContent,/短主题入口：0 部 · 0 个短主题；文件目录：2 组 · 3 份/);
  assert.doesNotMatch(elements.get('results').innerHTML,/负责人考核/);
});

test('a legacy bundle without directory keeps old AQ view and explains an unknown directory URL',async()=>{
  const {elements}=await load({includeReferences:true,search:'?view=references&standard=directory:noncoal'});
  assert.match(elements.get('routeNotice').textContent,/不在当前视图收录范围/);
  assert.equal(elements.get('resultCount').textContent,'1 部官方查阅入口 · 2 个短检索主题（非判定原文）');
  assert.doesNotMatch(elements.get('catalogSummary').textContent,/行业官方文件目录/);
});

test('empty directory snapshot retains zero directory counts without borrowing the AQ or clause data',async()=>{
  const {elements}=await load({includeReferences:true,includeDirectory:true,search:'?view=references',mutate:f=>{f.directory.directoryGroups=[];f.directory.entries=[];f.directory.directoryGroupCount=0;f.directory.documentCount=0;}});
  assert.match(elements.get('resultCount').textContent,/短主题入口：1 部.*文件目录：0 组 · 0 份/);
  assert.match(elements.get('catalogSummary').textContent,/行业官方文件目录 0 组 · 0 份/);
});

for(const [label,mutate] of [
  ['quote injection',f=>{f.directory.entries[0].quote='禁止公开的正文';}],
  ['topics injection',f=>{f.directory.entries[0].searchTopics=[];}],
  ['clause count inflation',f=>{f.directory.entries[0].reviewedClauseCount=1;}],
  ['H association inflation',f=>{f.directory.entries[0].directHazardCount=1;}],
  ['group-document count conflation',f=>{f.directory.directoryGroupCount=3;}],
  ['missing companion',f=>{f.directory.entries.pop();f.directory.documentCount=2;}],
  ['future review',f=>{f.directory.entries[0].checked='2026-10-02T00:00:00Z';}],
  ['unknown effective date without note',f=>{f.directory.entries[2].effectiveDateNote='';}],
  ['catalog LV overlap',f=>{f.directory.entries[0].lawVersionId='LV_TEST';}],
  ['AQ LV overlap',f=>{f.directory.entries[0].lawVersionId='LV_AQ_TEST';}],
  ['declared missing directory',f=>{f.directory=undefined;}],
  ['invalid directory path',f=>{f.paths.majorCriteriaDirectory=null;}]
])test(`invalid directory fails closed including Back: ${label}`,async()=>{
  const {elements,listeners,location}=await load({includeReferences:true,includeDirectory:true,mutate});
  location.search='?view=references';listeners.popstate();
  assert.equal(elements.get('resultCount').textContent,'专题暂时不可用');
  assert.equal(elements.get('referencesTab').hidden,true);
  assert.equal(elements.get('clausesTab').disabled,true);
  assert.doesNotMatch(elements.get('results').innerHTML,/禁止公开的正文|金属非金属矿山重大事故隐患判定标准|负责人考核/);
});

test('directory renders escaped metadata and preserves legitimate official query-string links',async()=>{
  const {elements}=await load({includeDirectory:true,search:'?view=references&standard=directory:fire',mutate:f=>{
    f.directory.entries[0].title='<script>alert(1)</script> GB 35181-2025';
    f.directory.entries[0].officialTextLink='https://zfxxgk.ndrc.gov.cn/web/iteminfo.jsp?id=20619';
  }});
  const html=elements.get('results').innerHTML;
  assert.match(html,/&lt;script&gt;/);assert.doesNotMatch(html,/<script>/);
  assert.match(html,/href="https:\/\/zfxxgk\.ndrc\.gov\.cn\/web\/iteminfo\.jsp\?id=20619"/);
  assert.doesNotMatch(html,/href="\.\/\?id=/);
});

function matchingReviewedDirectory(f){
  const s=f.catalog.standards[0],v=s.standardVersion,e=f.directory.entries[0];
  s.officialScope.wholeStandardComplete=true;s.coverage.wholeStandardComplete=true;
  s.publicationBasis={basis:'copyright_law_article_5_official_administrative_document',legalSourceUrl:'https://www.nsfc.gov.cn/copyright',checked:'2026-10-01T11:37:27+00:00',fullTextPublicationApproved:true};
  Object.assign(e,{lawVersionId:s.lawVersionId,lawId:v.lawId,title:`${v.name} ${v.documentNumber}`,documentNumber:v.documentNumber,versionKey:v.versionKey,effectiveDate:v.effectiveDate});
}
test('exact metadata entry links its reviewed complete body without double-counting',async()=>{
  const {elements,location,listeners}=await load({includeDirectory:true,search:'?view=references',mutate:matchingReviewedDirectory});
  assert.match(elements.get('results').innerHTML,/另见已审正文：2 条/);
  assert.match(elements.get('results').innerHTML,/此题录与正文为同一版本，计数不相加/);
  assert.doesNotMatch(elements.get('results').innerHTML,/<blockquote/);
  location.search='?standard=LV_TEST';listeners.popstate();
  assert.match(elements.get('results').innerHTML,/标准正文已完整核对/);
  assert.match(elements.get('results').innerHTML,/逐条核对适用主体、条件和例外/);
  assert.doesNotMatch(elements.get('results').innerHTML,/不代表标准全部内容/);
  assert.equal(elements.get('resultCount').textContent,'1 部依据 · 2 条已收录判定条文');
  location.search='?view=references';listeners.popstate();
  assert.match(elements.get('results').innerHTML,/另见已审正文：2 条/);
});
test('same LV with conflicting metadata never renders a normative cross-link',async()=>{
  const {elements}=await load({includeDirectory:true,mutate:f=>{matchingReviewedDirectory(f);f.directory.entries[0].title='不同文件';}});
  assert.equal(elements.get('resultCount').textContent,'专题暂时不可用');
  assert.doesNotMatch(elements.get('results').innerHTML,/另见已审正文/);
});


function readingFixture(directory){
  const identityKeys=['lawId','lawVersionId','title','documentNumber','versionKey','issuer','documentKind','legalNature','officialLink','officialTextLink','publicationDate','effectiveDate','effectiveDateNote','scopeHint','scopeCaveat','directoryGroup','requiredCompanionIds','supplementsReferenceId'];
  const checked='2026-10-01T10:00:00Z';
  const documents=directory.entries.filter(entry=>entry.directoryGroup.id==='noncoal').map((entry,i)=>({
    directoryReferenceId:entry.id,sourceIdentity:Object.fromEntries(identityKeys.map(key=>[key,structuredClone(entry[key])])),noticeText:`${i?'补充':'主文件'}通知完整原文，仅为测试。`,
    sections:[{id:`SECTION_${i}`,title:i?'补充情形':'地下矿山情形',items:[{id:`ITEM_${i}`,articleLabel:i?'补充第一项':'第一项',quote:i?'橙色预警时，应当采取规定措施。':'矿柱条件主件独有，引用 GB 9999-2024。'}]}],
    firstLevelItemCount:1,fullTextReviewed:true,checked,
    currentUseEvidence:[{sourceDate:'2025-02-01',sourceUrl:'https://www.chinamine-safety.gov.cn/usage.html',summary:'官方使用证据测试，不推定施行日'}],
    officialClarifications:i?[{id:'NOTE_TAILINGS',appliesToItemIds:['ITEM_1'],textMode:'reviewed_summary',text:'尾矿库巡查和抢险人员例外须核对完整条件。',sourceDate:'2024-06-01',sourceUrl:'https://www.chinamine-safety.gov.cn/explanation.html',sourcePages:[2,3],checked,isOfficialNormText:false}]:[]
  }));
  return {schemaVersion:'safety-major-criteria-reading-v1',asOf:'2026-10-01',catalogScope:'official_source_reading_only',referenceOnly:true,currentDeterminationBasis:false,reviewedCurrentClauseCount:0,directHazardCount:0,standaloneDeterminationAllowed:false,allIndustryCoverage:false,notice:'本区仅供官方原文查阅，不能据此自动作现场判定。',readingGroupCount:1,sourceDocumentCount:2,firstLevelItemCount:2,readingGroups:[{id:'READ_NONCOAL',directoryGroupId:'noncoal',primaryReferenceId:'DIR_MINE',requiredReferenceIds:['DIR_MINE','DIR_SUPPLEMENT'],readingReason:'effective_date_not_fully_verified',warning:'补充文件未核准明确施行日，仅供查阅。',checked,documents,publicationBasis:{basis:'copyright_law_article_5_official_administrative_document',legalSourceUrl:'https://www.gov.cn/copyright.html',checked,referenceTextPublicationApproved:true}}]};
}

test('reading expands once inside its existing directory group with unchanged catalog and AQ counts',async()=>{
  const {elements}=await load({includeReferences:true,includeDirectory:true,includeReading:true,search:'?view=references'});
  assert.equal(elements.get('resultCount').textContent,'短主题入口：1 部 · 2 个短主题；文件目录：2 组 · 3 份官方文件（题录计数，不计入现行判定条文）；其中 1 组 2 份可展开原文');
  assert.match(elements.get('catalogSummary').textContent,/1 部已审条文目录 · 2 条已收录整条 · 1 条专题关联隐患/);
  assert.match(elements.get('catalogSummary').textContent,/其中 1 组 2 份可展开原文/);
  const html=elements.get('results').innerHTML;
  assert.equal((html.match(/class="reading-details"/g)||[]).length,1);
  assert.match(html,/主文件 1 项 ＋ 补充文件 1 项，共 2 个一级项原文/);
  assert.ok(html.indexOf('未核准明确施行日')<html.indexOf('<details class="reading-details"'));
  assert.match(html,/不能据此自动作现场判定/);
  assert.match(html,/依据官方说明整理（非规范原文）/);
  assert.match(html,/尾矿库巡查和抢险人员例外须核对完整条件/);
  assert.match(html,/对应：补充情形 补充第一项/);
  assert.match(html,/来源第 2、3 页/);
  assert.doesNotMatch(html,/均非判定原文|class="clause-card"|href="\.\/\?id=/);
  assert.equal(elements.get('standardFilter').innerHTML.includes('reading:'),false);
  elements.get('clausesTab').click();
  assert.equal(elements.get('resultCount').textContent,'1 部依据 · 2 条已收录判定条文');
  assert.doesNotMatch(elements.get('results').innerHTML,/矿柱条件主件独有|橙色预警/);
  elements.get('hazardsTab').click();assert.equal(elements.get('resultCount').textContent,'1 条专题关联隐患');
});

test('reading keeps unknown date distinct from publication and current-use evidence dates',async()=>{
  const {elements}=await load({includeDirectory:true,includeReading:true,search:'?view=references&standard=directory:noncoal'});
  const html=elements.get('results').innerHTML;
  assert.match(html,/原文件载明实施日期：2024-03-01/);
  assert.match(html,/原文件未明示施行日，未核准明确施行日/);
  assert.match(html,/官方当前使用证据（不作为施行起始日）/);
  assert.match(html,/2025-02-01/);
  assert.doesNotMatch(html,/实施日期：2025-02-01|实施日期：2024-02-03/);
});

test('reading text and explanation queries return full group once without changing metadata-only search',async()=>{
  const {elements}=await load({includeReferences:true,includeDirectory:true,includeReading:true,search:'?view=references'});
  for(const query of ['橙色预警','巡查','矿安〔2024〕41号 橙色预警','矿柱条件主件独有']){
    elements.get('topicQuery').value=query;elements.get('topicQuery').oninput();
    assert.match(elements.get('resultCount').textContent,/文件目录：1 组 · 2 份.*其中 1 组 2 份/);
    const html=elements.get('results').innerHTML;
    assert.match(html,/矿柱条件主件独有/);assert.match(html,/橙色预警/);assert.match(html,/巡查和抢险/);
    assert.equal((html.match(/class="directory-group"/g)||[]).length,1);
  }
  for(const query of ['矿安〔2024〕410号','GB9999-2024','主件独有 橙色预警','矿安〔2022〕88号 橙色预警']){
    elements.get('topicQuery').value=query;elements.get('topicQuery').oninput();
    assert.match(elements.get('resultCount').textContent,/文件目录：0 组 · 0 份.*其中 0 组 0 份/);
  }
  elements.get('clausesTab').click();elements.get('topicQuery').value='巡查';elements.get('topicQuery').oninput();
  assert.equal(elements.get('resultCount').textContent,'0 部依据 · 0 条已收录判定条文');
  elements.get('hazardsTab').click();assert.equal(elements.get('resultCount').textContent,'0 条专题关联隐患');
});

test('reading Back restores directory selection, and native expansion survives render without a new route',async()=>{
  const {elements,location,listeners,historyCalls}=await load({includeDirectory:true,includeReading:true,search:'?view=references&standard=directory:noncoal'});
  elements.get('results').eventHandlers.toggle({target:{dataset:{readingGroup:'noncoal'},open:true}});
  elements.get('topicQuery').value='巡查';elements.get('topicQuery').oninput();
  assert.match(elements.get('results').innerHTML,/data-reading-group="noncoal" open/);
  elements.get('hazardsTab').click();const count=historyCalls.length;
  location.search='?view=references&standard=directory:noncoal';listeners.popstate();
  assert.equal(historyCalls.length,count);assert.equal(elements.get('standardFilter').value,'directory:noncoal');
  assert.match(elements.get('results').innerHTML,/data-reading-group="noncoal" open/);
  elements.get('results').eventHandlers.toggle({target:{dataset:{readingGroup:'noncoal'},open:false}});
  elements.get('resetTopic').click();assert.doesNotMatch(elements.get('results').innerHTML,/data-reading-group="noncoal" open/);
  assert.ok(historyCalls.every(call=>!call.url.includes('reading:')&&!call.url.includes('view=reading')));
});

test('empty reading projection remains a metadata directory without borrowing current clauses',async()=>{
  const {elements}=await load({includeDirectory:true,includeReading:true,search:'?view=references',mutate:f=>{Object.assign(f.reading,{readingGroups:[],readingGroupCount:0,sourceDocumentCount:0,firstLevelItemCount:0});}});
  assert.match(elements.get('resultCount').textContent,/文件目录：2 组 · 3 份.*其中 0 组 0 份/);
  assert.doesNotMatch(elements.get('results').innerHTML,/reading-details|压力容器有下列情形/);
});

test('reading escapes original and explanatory text and explicitly labels a pending official link',async()=>{
  const {elements}=await load({includeDirectory:true,includeReading:true,search:'?view=references',mutate:f=>{
    const doc=f.reading.readingGroups[0].documents[1];doc.sections[0].items[0].quote='<script>original</script>';
    Object.assign(doc.officialClarifications[0],{textMode:'official_link_pending',text:'<img src=x onerror=alert(1)>',sourcePages:null});
  }});
  const html=elements.get('results').innerHTML;
  assert.match(html,/&lt;script&gt;original/);assert.match(html,/&lt;img/);
  assert.match(html,/官方说明待核，请查官方来源（非规范原文）/);
  assert.doesNotMatch(html,/<script>|<img src=x/);
});

for(const [label,mutate] of [
  ['missing payload',f=>{f.reading=undefined;}],
  ['invalid path',f=>{f.paths.majorCriteriaReading=null;}],
  ['empty path',f=>{f.paths.majorCriteriaReading='';}],
  ['missing directory',f=>{delete f.paths.majorCriteriaDirectory;}],
  ['current eligibility',f=>{f.reading.currentDeterminationBasis=true;}],
  ['current clause count',f=>{f.reading.reviewedCurrentClauseCount=2;}],
  ['H count',f=>{f.reading.directHazardCount=1;}],
  ['schema',f=>{f.reading.schemaVersion='safety-major-criteria-references-v1';}],
  ['snapshot',f=>{f.reading.asOf='2026-09-30';}],
  ['missing companion',f=>{f.reading.readingGroups[0].documents.pop();}],
  ['identity mismatch',f=>{f.reading.readingGroups[0].documents[0].sourceIdentity.title='不同文件';}],
  ['date inferred',f=>{f.reading.readingGroups[0].documents[1].sourceIdentity.effectiveDate='2024-02-03';}],
  ['malicious URL',f=>{f.reading.readingGroups[0].documents[0].currentUseEvidence[0].sourceUrl='https://www.gov.cn.evil.example/x';}],
  ['C injection',f=>{f.reading.readingGroups[0].documents[0].sections[0].items[0].clauseId='C_FAKE';}]
])test(`invalid reading fails closed including Back: ${label}`,async()=>{
  const {elements,location,listeners}=await load({includeReferences:true,includeDirectory:true,includeReading:true,mutate});
  location.search='?view=references&standard=directory:noncoal';listeners.popstate();
  assert.equal(elements.get('resultCount').textContent,'专题暂时不可用');
  assert.equal(elements.get('referencesTab').hidden,true);assert.equal(elements.get('clausesTab').disabled,true);
  assert.doesNotMatch(elements.get('results').innerHTML,/矿柱条件主件独有|橙色预警|负责人考核|压力容器有下列情形/);
});


test('single-document reading never claims there is a companion supplement',async()=>{
  const {elements}=await load({includeDirectory:true,includeReading:true,search:'?view=references&standard=directory:noncoal',mutate:f=>{
    f.directory.entries=f.directory.entries.filter(e=>e.id!=='DIR_SUPPLEMENT');
    const entry=f.directory.entries.find(e=>e.id==='DIR_MINE');
    entry.requiredCompanionIds=[];entry.effectiveDate=null;entry.referenceStatus='current_in_use';entry.statusLabel='现行使用中';entry.effectiveDateNote='原通知未明示施行日';
    const group=f.directory.directoryGroups.find(g=>g.id==='noncoal');group.documentIds=['DIR_MINE'];
    f.directory.documentCount-=1;
    f.reading=readingFixture(f.directory);const r=f.reading.readingGroups[0];
    r.requiredReferenceIds=['DIR_MINE'];r.warning='本文件未核准明确施行日，仅供查阅。';
    f.reading.sourceDocumentCount=1;f.reading.firstLevelItemCount=1;
  }});
  const html=elements.get('results').innerHTML;
  assert.notEqual(elements.get('resultCount').textContent,'专题暂时不可用');
  assert.match(html,/展开官方原文（共 1 份）/);
  assert.doesNotMatch(html,/主文件与补充文件须配套查阅|主文件与补充文件，共/);
  assert.match(html,/未核准明确施行日/);
});
