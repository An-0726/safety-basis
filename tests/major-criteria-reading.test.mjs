import test from 'node:test';
import assert from 'node:assert/strict';
import {validateMajorReading,validateReadingDirectoryLinks,selectMajorReading} from '../web/js/major-criteria-reading-model.js';
import {selectMajorDirectory} from '../web/js/major-criteria-directory-model.js';

const asOf='2026-10-01',checked='2026-10-01T10:00:00+00:00';
function fixture(){
  const entries=['MAIN','SUPPLEMENT'].map((id,i)=>({id,lawId:`LF_${id}`,lawVersionId:`LV_${id}`,title:i?'金属非金属矿山补充情形':'金属非金属矿山重大事故隐患判定标准',documentNumber:i?'矿安〔2024〕41号':'矿安〔2022〕88号',versionKey:i?'2024':'2022',issuer:'国家矿山安全监察局',documentKind:'部门规范性文件',legalNature:'部门规范性文件',criterionKind:'major_hazard_determination',publicationDate:i?'2024-04-23':'2022-07-08',effectiveDate:i?null:'2022-09-01',effectiveDateNote:i?'通知未单列实施日；不以发布日期推填':'',referenceStatus:'current_in_use',statusLabel:'现行使用中',statusAsOf:asOf,checked,officialLink:`https://www.chinamine-safety.gov.cn/${id}.html`,officialTextLink:`https://www.chinamine-safety.gov.cn/${id}.pdf`,directoryGroup:{id:'noncoal',label:'金属非金属矿山',role:i?'supplement':'primary'},requiredCompanionIds:i?[]:['SUPPLEMENT'],supplementsReferenceId:i?'MAIN':null,scopeHint:'地下矿山、露天矿山、尾矿库',scopeCaveat:'须配套查阅并核对适用范围',contentKind:'official_document_reference_only',textMode:'link_only',publicationPermission:'metadata_only',fullTextReviewed:false,fullQuotePublicationReady:false,publicationReady:{metadata:true,fullText:false},reviewedClauseCount:0,directHazardCount:0,searchTopicCount:0,standaloneDeterminationAllowed:false,wholeStandardComplete:false}));
  const directory={schemaVersion:'safety-major-criteria-directory-v1',catalogScope:'controlled_official_metadata_directory',allIndustryCoverage:false,wholeNormNotFieldFinding:true,asOf,notice:'官方目录仅作题录查阅',directoryGroupCount:1,documentCount:2,directoryGroups:[{id:'noncoal',label:'金属非金属矿山',primaryReferenceId:'MAIN',documentIds:['MAIN','SUPPLEMENT']}],entries};
  const identityKeys=['lawId','lawVersionId','title','documentNumber','versionKey','issuer','documentKind','legalNature','officialLink','officialTextLink','publicationDate','effectiveDate','effectiveDateNote','scopeHint','scopeCaveat','directoryGroup','requiredCompanionIds','supplementsReferenceId'];
  const documents=entries.map((entry,i)=>({directoryReferenceId:entry.id,sourceIdentity:Object.fromEntries(identityKeys.map(key=>[key,structuredClone(entry[key])])),noticeText:`${i?'补充':'主文'}通知完整内容，引用应急管理部令第21号。`,sections:[{id:`SECTION_${i}`,title:i?'补充情形':'地下矿山',items:[{id:`ITEM_${i}`,articleLabel:i?'补充第（一）项':'第（一）项',quote:i?'红色橙色预警，补件独有触发。':'矿柱保护，主件独有条件，参考 GB 9999-2024。'}]}],firstLevelItemCount:1,fullTextReviewed:true,checked,currentUseEvidence:[{sourceDate:'2025-02-01',sourceUrl:'https://www.gov.cn/current.html',summary:'当前使用证据摘要，不是实施日期'}],officialClarifications:i?[{id:'NOTE_1',appliesToItemIds:['ITEM_1'],textMode:'reviewed_summary',text:'尾矿库巡查和抢险例外的完整条件整理。',sourceDate:'2024-06-05',sourceUrl:'https://www.chinamine-safety.gov.cn/explanation.html',sourcePages:[1,3],checked,isOfficialNormText:false}]:[]}));
  const reading={schemaVersion:'safety-major-criteria-reading-v1',asOf,catalogScope:'official_source_reading_only',referenceOnly:true,currentDeterminationBasis:false,reviewedCurrentClauseCount:0,directHazardCount:0,standaloneDeterminationAllowed:false,allIndustryCoverage:false,notice:'原文供查阅，不能自动作现场判定',readingGroupCount:1,sourceDocumentCount:2,firstLevelItemCount:2,readingGroups:[{id:'READ_NONCOAL',directoryGroupId:'noncoal',primaryReferenceId:'MAIN',requiredReferenceIds:['MAIN','SUPPLEMENT'],readingReason:'effective_date_not_fully_verified',warning:'补充未核准明确施行日，仅供查阅',checked,documents,publicationBasis:{basis:'copyright_law_article_5_official_administrative_document',legalSourceUrl:'https://www.gov.cn/copyright.html',checked,referenceTextPublicationApproved:true}}]};
  return {reading,directory};
}
const group=data=>data.readingGroups[0],doc=data=>group(data).documents[0],supplement=data=>group(data).documents[1],note=data=>supplement(data).officialClarifications[0];
const validate=data=>validateMajorReading(data,asOf);

test('pure reading model validates exact projection and whole directory identity without mutation',()=>{
  assert.equal(typeof globalThis.document,'undefined');const f=fixture(),before=structuredClone(f);
  assert.strictEqual(validate(f.reading),f.reading);assert.strictEqual(validateReadingDirectoryLinks(f.reading,f.directory),f.reading);
  assert.deepEqual(f,before);const result=selectMajorReading(f.reading);
  assert.equal(result.readingGroupCount,1);assert.equal(result.sourceDocumentCount,2);assert.equal(result.firstLevelItemCount,2);
  assert.deepEqual(f,before);assert.equal(supplement(f.reading).sourceIdentity.effectiveDate,null);
});

test('empty snapshot validates with explicit zero counts',()=>{
  const {reading}=fixture();Object.assign(reading,{readingGroups:[],readingGroupCount:0,sourceDocumentCount:0,firstLevelItemCount:0});
  assert.strictEqual(validate(reading),reading);assert.deepEqual(selectMajorReading(reading),{readingGroups:[],readingGroupCount:0,sourceDocumentCount:0,firstLevelItemCount:0});
});

for(const query of ['红色橙色预警','巡查','矿柱保护','矿安[2024]41号','矿安〔2024〕41号 预警','矿安（２０２２）８８号 矿柱','金属非金属矿山'])test(`reading search returns the complete companion group: ${query}`,()=>{
  const {reading}=fixture();const result=selectMajorReading(reading,{query});assert.equal(result.sourceDocumentCount,2);
  assert.equal(result.firstLevelItemCount,2);assert.deepEqual(result.readingGroups[0].documents.map(row=>row.directoryReferenceId),['MAIN','SUPPLEMENT']);
});
for(const query of ['矿安〔2024〕410号','矿安〔2024〕4号','矿安〔2023〕41号','GB9999-2024','应急管理部令第21号','主件独有 补件独有','矿安〔2022〕88号 预警','矿安〔2022〕88号 矿安〔2024〕41号','矿柱.*','非煤','巡察','2025-02-01','current.html','LF_MAIN'])test(`reading query cannot broaden or infer identity: ${query}`,()=>{
  assert.equal(selectMajorReading(fixture().reading,{query}).readingGroupCount,0);
});
test('reading group selector intersects the query and metadata-only directory excludes body text',()=>{
  const {reading,directory}=fixture();assert.equal(selectMajorReading(reading,{group:'noncoal',query:'预警'}).sourceDocumentCount,2);
  assert.equal(selectMajorReading(reading,{group:'MAIN',query:'预警'}).sourceDocumentCount,0);
  assert.equal(selectMajorDirectory(directory,{query:'预警'}).documentCount,0);
});

test('pending-link clarification is explicit non-normative text and nullable pages remain nullable',()=>{
  const {reading}=fixture();Object.assign(note(reading),{textMode:'official_link_pending',sourcePages:null});assert.strictEqual(validate(reading),reading);
});

const mutations=[
  ['schema',r=>{r.schemaVersion='safety-major-criteria-references-v1';}],
  ['scope',r=>{r.catalogScope='controlled_reviewed_standards_only';}],
  ['asOf invalid',r=>{r.asOf='2026-02-30';}],
  ['asOf mismatch',r=>{r.asOf='2026-09-30';}],
  ...['referenceOnly','currentDeterminationBasis','standaloneDeterminationAllowed','allIndustryCoverage'].map(key=>[key,r=>{r[key]=!r[key];}]),
  ...['reviewedCurrentClauseCount','directHazardCount'].map(key=>[key,r=>{r[key]=1;}]),
  ['root extension',r=>{r.hazards=[];}],
  ['group count',r=>{r.readingGroupCount=2;}],['document count',r=>{r.sourceDocumentCount=1;}],['item count',r=>{r.firstLevelItemCount=72;}],
  ['negative count',r=>{r.firstLevelItemCount=-1;}],['boolean count',r=>{r.firstLevelItemCount=true;}],
  ['group duplicate',r=>{r.readingGroups.push(structuredClone(group(r)));r.readingGroupCount++;}],
  ['wrong reason',r=>{group(r).readingReason='current';}],['empty warning',r=>{group(r).warning='';}],
  ['future group review',r=>{group(r).checked='2026-10-02';}],['invalid review time',r=>{group(r).checked='2026-10-01T25:00:00Z';}],
  ['publication approval',r=>{group(r).publicationBasis.referenceTextPublicationApproved=false;}],
  ['normative approval',r=>{group(r).publicationBasis.fullTextPublicationApproved=true;}],
  ['publication source',r=>{group(r).publicationBasis.legalSourceUrl='https://example.com/copyright';}],
  ['publication checked mismatch',r=>{group(r).publicationBasis.checked='2026-09-30';}],
  ['missing supplement',r=>{group(r).documents.pop();r.sourceDocumentCount--;r.firstLevelItemCount--;}],
  ['one document only',r=>{group(r).documents.pop();group(r).requiredReferenceIds=['MAIN'];doc(r).sourceIdentity.requiredCompanionIds=[];r.sourceDocumentCount--;r.firstLevelItemCount--;}],
  ['unknown companion',r=>{group(r).requiredReferenceIds.push('UNKNOWN');}],
  ['duplicate required ID',r=>{group(r).requiredReferenceIds.push('MAIN');}],
  ['wrong primary',r=>{group(r).primaryReferenceId='SUPPLEMENT';}],
  ['primary parent',r=>{doc(r).sourceIdentity.supplementsReferenceId='MAIN';}],
  ['primary missing companion',r=>{doc(r).sourceIdentity.requiredCompanionIds=[];}],
  ['supplement missing parent',r=>{supplement(r).sourceIdentity.supplementsReferenceId=null;}],
  ['supplement with companion',r=>{supplement(r).sourceIdentity.requiredCompanionIds=['MAIN'];}],
  ['group label mismatch',r=>{supplement(r).sourceIdentity.directoryGroup.label='不同分组';}],
  ['group identity mismatch',r=>{supplement(r).sourceIdentity.directoryGroup.id='OTHER';}],
  ['duplicate document',r=>{supplement(r).directoryReferenceId='MAIN';}],
  ['duplicate LV',r=>{supplement(r).sourceIdentity.lawVersionId=doc(r).sourceIdentity.lawVersionId;}],
  ['duplicate LF',r=>{supplement(r).sourceIdentity.lawId=doc(r).sourceIdentity.lawId;}],
  ['technical standard kind',r=>{doc(r).sourceIdentity.documentKind='国家标准';}],
  ['unknown date no explanation',r=>{supplement(r).sourceIdentity.effectiveDateNote='';}],
  ['no unknown date',r=>{supplement(r).sourceIdentity.effectiveDate='2024-04-23';}],
  ['invalid source date',r=>{doc(r).sourceIdentity.effectiveDate='2022-02-30';}],
  ['future publication',r=>{doc(r).sourceIdentity.publicationDate='2027-01-01';}],
  ['full text unreviewed',r=>{doc(r).fullTextReviewed=false;}],
  ['future text review',r=>{doc(r).checked='2026-10-02';}],
  ['empty notice',r=>{doc(r).noticeText='';}],
  ['empty sections',r=>{doc(r).sections=[];}],
  ['section duplicate',r=>{doc(r).sections.push(structuredClone(doc(r).sections[0]));}],
  ['empty items',r=>{doc(r).sections[0].items=[];}],
  ['duplicate item',r=>{supplement(r).sections[0].items[0].id=doc(r).sections[0].items[0].id;}],
  ['empty quote',r=>{doc(r).sections[0].items[0].quote='';}],
  ['C injection',r=>{doc(r).sections[0].items[0].clauseId='C_1';}],
  ['H injection',r=>{doc(r).directHazardIds=['H_1'];}],
  ['count disagreement',r=>{doc(r).firstLevelItemCount=64;}],
  ['missing current evidence',r=>{doc(r).currentUseEvidence=[];}],
  ['future current evidence',r=>{doc(r).currentUseEvidence[0].sourceDate='2026-10-02';}],
  ['evidenceId leak',r=>{doc(r).currentUseEvidence[0].evidenceId='E_PRIVATE';}],
  ['unknown note item',r=>{note(r).appliesToItemIds=['UNKNOWN'];}],
  ['note points other document',r=>{note(r).appliesToItemIds=['ITEM_0'];}],
  ['duplicate note',r=>{supplement(r).officialClarifications.push(structuredClone(note(r)));}],
  ['normative explanation',r=>{note(r).isOfficialNormText=true;}],
  ['unapproved note mode',r=>{note(r).textMode='official_excerpt';}],
  ['future explanation',r=>{note(r).sourceDate='2026-10-02';}],
  ['note review mismatch',r=>{note(r).checked='2026-09-30';}],
  ['empty note pages',r=>{note(r).sourcePages=[];}],['unordered pages',r=>{note(r).sourcePages=[2,1];}],
  ['duplicate pages',r=>{note(r).sourcePages=[1,1];}],['noninteger pages',r=>{note(r).sourcePages=[1.5];}],
  ['zero page',r=>{note(r).sourcePages=[0];}],['boolean page',r=>{note(r).sourcePages=[true];}],
  ['quote control character',r=>{doc(r).sections[0].items[0].quote='原文\u0000';}],
  ['hidden property',r=>{Object.defineProperty(group(r),'hidden',{value:'payload'});}],
  ['symbol property',r=>{doc(r)[Symbol('payload')]='payload';}],
  ['accessor property',r=>{Object.defineProperty(doc(r),'noticeText',{enumerable:true,get(){throw new Error('Accessor should not execute');}});}],
  ['array extension',r=>{r.readingGroups.extra=true;}],
  ['sparse array',r=>{delete group(r).documents[0];}],
  ['bad prototype',r=>{Object.setPrototypeOf(group(r),{inherited:true});}]
];
for(const [label,mutate] of mutations)test(`reading rejects ${label}`,()=>{
  const {reading}=fixture();mutate(reading);assert.throws(()=>validate(reading),/官方原文查阅数据校验失败/);
});
for(const url of ['http://www.gov.cn/x','https://www.gov.cn.evil.example/x','https://gov.cn/x','https://user@www.gov.cn/x','https://www.gov.cn:443/x','https://www.gov.cn:444/x','https://www.gov.cn/x y','https://www.gov.cn/\\evil','https://www.gov.cn/%0aevil','https://www.gov.cn/\u200bx','javascript:alert(1)'])test(`reading rejects noncanonical official URL ${JSON.stringify(url)}`,()=>{
  const {reading}=fixture();note(reading).sourceUrl=url;assert.throws(()=>validate(reading),/官方原文查阅数据校验失败/);
});

test('all 18 directory identity fields bind exactly and object key order is immaterial',()=>{
  const f=fixture();const identity=doc(f.reading).sourceIdentity;
  for(const key of Object.keys(identity)){
    const next=structuredClone(f);const value=doc(next.reading).sourceIdentity[key];
    // Keep the public shape valid where possible; either local or join rejection suffices.
    doc(next.reading).sourceIdentity[key]=typeof value==='string'?value+'不同':value===null?'2024-01-01':Array.isArray(value)?[]:{...value,label:'不同'};
    assert.throws(()=>validateReadingDirectoryLinks(next.reading,next.directory),undefined,key);
  }
  doc(f.reading).sourceIdentity=Object.fromEntries(Object.entries(identity).reverse());
  assert.strictEqual(validateReadingDirectoryLinks(f.reading,f.directory),f.reading);
});
test('an internally complete subset cannot omit a member in the actual directory group',()=>{
  const f=fixture();f.directory.entries[0].requiredCompanionIds.push('EXTRA');
  const extra=structuredClone(f.directory.entries[1]);Object.assign(extra,{id:'EXTRA',lawId:'LF_EXTRA',lawVersionId:'LV_EXTRA'});
  f.directory.entries.push(extra);f.directory.directoryGroups[0].documentIds.push('EXTRA');f.directory.documentCount++;
  assert.throws(()=>validateReadingDirectoryLinks(f.reading,f.directory),/DIRECTORY_GROUP_MISMATCH/);
});
test('a same-ID metadata edit and cross-snapshot directory never silently detach the quote',()=>{
  for(const mutate of [f=>{f.directory.entries[1].title='另一份文件';},f=>{f.directory.entries[1].effectiveDate='2024-04-23';},f=>{f.directory.asOf='2026-10-02';}]){
    const f=fixture();mutate(f);assert.throws(()=>validateReadingDirectoryLinks(f.reading,f.directory));
  }
});
