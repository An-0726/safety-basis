import test from 'node:test';
import assert from 'node:assert/strict';
import {profileEnvelope,validateProfileJoin,profileSummary,profileTemplateText,profileReferenceText} from '../web/js/field-profiles.js';
import {DataStore,publicSourceUrl} from '../web/js/store.js';
import {searchHazardsDetailed} from '../web/js/search.js';

const asOf='2026-10-01';
const source=()=>({
  profile:{schemaVersion:1,recordKind:'reusable_field_profile',observedViolation:false,id:'FPR_ONE',revision:1,
    hazardId:'H1',title:'现场场景',inspectionClass:'core_onsite_inspection',defaultFieldEntry:'conditional',contentDisposition:'onsite_finding',
    applicability:{requires:['确切适用条件'],excludes:['不能仅凭照片认定'],perUseFacts:['applicableRequirementConfirmed','siteTriggerConfirmed','defectObserved']},
    evidenceRequirements:['现场核验资料'],correctiveDirection:'整改方向',findingTemplate:{text:'{{place}}处存在{{defect}}。',slots:[{key:'place',label:'位置'},{key:'defect',label:'已核实缺陷'}]},
    basisLinkIds:['K1'],sourceHazard:{id:'H1',title:'原条目',conditions:'原条目范围'},bases:[{linkId:'K1',clauseId:'C1',role:'direct',applicability:'只适用设备甲',jurisdictionCode:'CN',lawVersionId:'LV1',lawId:'L1',lawJurisdictionCode:'CN'}]},
  detail:{hazard:{id:'H1',title:'原条目',conditions:'原条目范围',status:'已核验',publishable:true},
    bases:[{ref:{linkId:'K1',clauseId:'C1',role:'direct',applicability:'只适用设备甲',jurisdictionCode:'CN'},clause:{id:'C1',lawId:'LV1',status:'现行有效',quote:'完整原文'},law:{id:'LV1',name:'法律甲',status:'现行有效',effectiveDate:'2025-01-01'},sourceUrl:'https://example.gov.cn/law'}]},
});
const envelope=records=>({payload:{schemaVersion:1,asOf,records},release:{asOf,fileHashes:{'data/field-profiles.json':'a'.repeat(64)}},manifest:{files:{fieldProfiles:'data/field-profiles.json'},counts:{fieldProfiles:records.length}}});
const row=(id,profiles=[])=>({id,title:'条目',status:'已核验',mode:'direct',aliases:[],keywords:[],lawNames:[],searchText:'条目',inspectionClasses:profiles.map(p=>p.inspectionClass)});

test('valid public envelope and exact selected-K join',()=>{
  const {profile,detail}=source(), {payload,release,manifest}=envelope([profile]);
  assert.equal(profileEnvelope(payload,release,manifest)[0],profile);
  assert.equal(validateProfileJoin(profile,detail,asOf),true);
  assert.match(profileTemplateText(profile),/〔位置〕/);
  assert.doesNotMatch(profileTemplateText(profile),/\{\{/);
  assert.match(profileReferenceText(profile),/非现场结论/);
});
for(const [name,mutate] of [
  ['missing manifest',x=>x.release=null], ['missing hash',x=>x.release.fileHashes={}],
  ['wrong date',x=>x.payload.asOf='2026-09-30'],['invalid date',x=>x.release.asOf=x.payload.asOf='2026-02-30'],
  ['missing date',x=>delete x.release.asOf],['wrong schema',x=>x.payload.schemaVersion=2],
  ['count drift',x=>x.manifest.counts.fieldProfiles=0],['duplicate id',x=>{x.payload.records.push(x.payload.records[0]);x.manifest.counts.fieldProfiles=2;}],
]) test(`envelope fails closed: ${name}`,()=>{const x=envelope([source().profile]);mutate(x);assert.throws(()=>profileEnvelope(x.payload,x.release,x.manifest));});
for(const [name,mutate] of [
  ['observed fact',x=>x.profile.observedViolation=true],['unknown class',x=>x.profile.inspectionClass='undetermined'],
  ['unknown route',x=>x.profile.defaultFieldEntry='undetermined'],['unknown kind',x=>x.profile.profileKind='guess'],
  ['explicit null kind',x=>x.profile.profileKind=null],['missing template',x=>delete x.profile.findingTemplate],
  ['missing condition',x=>x.profile.applicability.requires=[]],['missing fact boundary',x=>x.profile.applicability.perUseFacts=[]],
  ['missing evidence',x=>x.profile.evidenceRequirements=[]],['unknown placeholder',x=>x.profile.findingTemplate.text='{{unknown}}'],
  ['leftover braces',x=>x.profile.findingTemplate.text+=' {{'],['bad slot key',x=>{x.profile.findingTemplate.text='{{not valid}}';x.profile.findingTemplate.slots=[{key:'not valid',label:'x'}];}],
  ['private reviewer field',x=>x.profile.reviewer='private'],['onsite fact value injection',x=>x.profile.applicability.defectObserved=true],
  ['missing identity',x=>delete x.profile.bases[0].lawId],['invalid profile ID',x=>x.profile.id='not-a-profile'],['array profile ID',x=>x.profile.id=['FPR_ONE']],['array class',x=>x.profile.inspectionClass=['core_onsite_inspection']],['empty scope',x=>x.profile.bases[0].applicability=''],['null law scope',x=>x.profile.bases[0].lawJurisdictionCode=null],['24 hour timestamp',x=>x.detail.hazard.checked='2026-09-30T24:00:00Z'],
  ['missing source',x=>delete x.profile.sourceHazard],['source mismatch',x=>x.profile.sourceHazard.conditions='扩大范围'],
  ['candidate source',x=>x.detail.hazard.status='待审核候选'],['wrong hazard',x=>x.profile.hazardId='H2'],
  ['unselected basis',x=>x.profile.basisLinkIds=['K2']],['duplicate basis',x=>{x.profile.bases.push(x.profile.bases[0]);x.profile.basisLinkIds.push('K2');}],
  ['cross-linked scope',x=>x.profile.bases[0].applicability='另一个关联条件'],['wrong region',x=>x.profile.bases[0].jurisdictionCode='CN-32'],
  ['wrong clause',x=>x.profile.bases[0].clauseId='C2'],['wrong version',x=>x.profile.bases[0].lawVersionId='LV2'],
  ['supporting only',x=>x.profile.bases[0].role=x.detail.bases[0].ref.role='supporting'],
  ['missing quote',x=>x.detail.bases[0].clause.quote=''],['missing source URL',x=>x.detail.bases[0].sourceUrl=''],
  ['expired status',x=>x.detail.bases[0].law.status='已失效'],['expired clause',x=>x.detail.bases[0].clause.status='已失效'],
  ['end exclusive',x=>x.detail.bases[0].law.endDate=asOf],['bad end',x=>x.detail.bases[0].law.endDate='nonsense'],['false end',x=>x.detail.bases[0].law.endDate=false],['zero end',x=>x.detail.bases[0].law.endDate=0],
  ['future source check',x=>x.detail.hazard.checked='2026-10-02'],['bad law check',x=>x.detail.bases[0].law.checked='no'],['bad clause check',x=>x.detail.bases[0].clause.checked='2026-02-30'],
  ['future effective',x=>x.detail.bases[0].law.effectiveDate='2026-10-02'],['invalid effective',x=>x.detail.bases[0].law.effectiveDate='2026-02-30'],
]) test(`profile join fails closed: ${name}`,()=>{const x=source();mutate(x);assert.equal(validateProfileJoin(x.profile,x.detail,asOf),false);});
test('different selected Ks keep their own applicability; unselected supporting links cannot fill a selected gap',()=>{
  const x=source();x.detail.bases.push({...x.detail.bases[0],ref:{...x.detail.bases[0].ref,linkId:'K2',applicability:'只适用设备乙'}});
  assert.equal(validateProfileJoin(x.profile,x.detail,asOf),true);
  x.detail.bases=x.detail.bases.slice(1);assert.equal(validateProfileJoin(x.profile,x.detail,asOf),false);
});
for(const [inspectionClass,contentDisposition] of [['document_review','document_check'],['legal_obligation','legal_obligation'],['special_review','special_check']]) test(`exclude is a route, not a finding: ${inspectionClass}`,()=>{
  const x=source();Object.assign(x.profile,{profileKind:'routing_only',inspectionClass,contentDisposition,defaultFieldEntry:'exclude',findingTemplate:null});
  assert.equal(validateProfileJoin(x.profile,x.detail,asOf),true);
  assert.equal(profileTemplateText(x.profile),'');assert.match(profileReferenceText(x.profile),/不提供现场隐患描述模板/);
  assert.ok(profileSummary([x.profile]));
  const rows=[row('H1',[x.profile]),row('H2')];
  assert.equal(searchHazardsDetailed(rows,'').rows.length,2);
  assert.equal(searchHazardsDetailed(rows,'',{inspectionClass}).rows.length,1);
  assert.equal(searchHazardsDetailed(rows,'',{inspectionClass:'core_onsite_inspection'}).rows.length,0);
  x.profile.findingTemplate=source().profile.findingTemplate;assert.equal(validateProfileJoin(x.profile,x.detail,asOf),false);
});
test('onsite routing-only also stays null and never creates a finding',()=>{
  const x=source();x.profile.profileKind='routing_only';x.profile.findingTemplate=null;
  assert.equal(validateProfileJoin(x.profile,x.detail,asOf),true);assert.equal(profileTemplateText(x.profile),'');
});
test('empty profile inventory keeps all original search records',()=>{
  const {payload,release,manifest}=envelope([]);assert.deepEqual(profileEnvelope(payload,release,manifest),[]);
  assert.equal(searchHazardsDetailed([row('H1'),row('H2')],'').rows.length,2);
});
async function storeWith(read) {
  const store=new DataStore();const {release,manifest}=envelope([source().profile]);
  store.manifest=manifest;store.verifiedFiles={manifest:release,read};store.searchIndex=[row('H1'),row('H2')];
  store.getHazardDetail=async()=>source().detail;await store.loadFieldProfiles();return store;
}
test('store loads only verified bytes and enriches without removing unprofiled rows',async()=>{
  const store=await storeWith(async()=>envelope([source().profile]).payload);
  assert.equal(store.searchIndex.length,2);assert.equal(store.getFieldProfiles('H1').length,1);
  assert.equal(store.getFieldProfiles('H2').length,0);assert.equal(store.fieldProfileNotice,'');
});
test('store catches hash/load/review projection failure without replacing original search',async()=>{
  const store=await storeWith(async()=>{throw new Error('hash mismatch');});
  assert.equal(store.searchIndex.length,2);assert.equal(store.getFieldProfiles('H1').length,0);
  assert.match(store.fieldProfileNotice,/暂不可用/);
});
test('one failed dependency prevents partial profile admission',async()=>{
  const p=source().profile, bad=structuredClone(p);bad.id='FPR_BAD';bad.bases[0].applicability='wrong';
  const store=new DataStore(),e=envelope([p,bad]);store.manifest=e.manifest;store.verifiedFiles={manifest:e.release,read:async()=>e.payload};store.searchIndex=[row('H1')];store.getHazardDetail=async()=>source().detail;
  await store.loadFieldProfiles();assert.equal(store.fieldProfiles.size,0);assert.match(store.fieldProfileNotice,/暂不可用/);
});

test('official clause label falls back to verified law URL; unsafe schemes are never linked',()=>{
  assert.equal(publicSourceUrl('flk.npc.gov.cn/law-search/download/pc (OBS 直链)','https://flk.npc.gov.cn/detail?id=x'),'https://flk.npc.gov.cn/detail?id=x');
  assert.equal(publicSourceUrl('javascript:alert(1)','file:///private'),'');
  assert.equal(publicSourceUrl('https://user:pass@example.com'),'');
});

test('approved null source conditions join the public detail empty-string projection',()=>{
  const x=source();x.profile.sourceHazard.conditions=null;x.detail.hazard.conditions='';
  assert.equal(validateProfileJoin(x.profile,x.detail,asOf),true);
  x.profile.sourceHazard.conditions=false;assert.equal(validateProfileJoin(x.profile,x.detail,asOf),false);
});
