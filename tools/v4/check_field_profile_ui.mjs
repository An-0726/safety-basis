// Headless data/controller integration, NOT browser or visual acceptance.
// Usage: node tools/v4/check_field_profile_ui.mjs path/to/verified/bundle
import assert from 'node:assert/strict';
import path from 'node:path';
import {readFile,access} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {webcrypto} from 'node:crypto';
const root=path.resolve(process.argv[2]||'source/releases/current');
// Import shipped modules, not the source checkout: missing transitive assets
// must fail this check before any data/controller pass can be reported.
const shipped=relative=>import(pathToFileURL(path.join(root,relative)).href);
const {DataStore}=await shipped('js/store.js');
const {searchHazardsDetailed}=await shipped('js/search.js');
const {profileTemplateText,validateProfileJoin}=await shipped('js/field-profiles.js');
await shipped('app.js');
const sw=await readFile(path.join(root,'sw.js'),'utf8');
for(const [,relative] of sw.matchAll(/'\.\/([^']*)'/g))await access(path.join(root,relative||'index.html'));
globalThis.crypto??=webcrypto;
globalThis.fetch=async request=>{
  const pathname=String(request).replace(/^\.\//,'').split('?')[0];
  if(pathname.includes('..')||path.isAbsolute(pathname))throw new Error('Unexpected local bundle path');
  try{return new Response(await readFile(path.join(root,pathname)),{status:200});}
  catch{return new Response('',{status:404});}
};
const store=await new DataStore('.').init();
const json=async p=>JSON.parse(await readFile(path.join(root,p),'utf8'));
const publicProfiles=await json(store.manifest.files.fieldProfiles);
const original=await json(store.manifest.files.searchIndex);
assert.equal(store.fieldProfileNotice,'');
assert.deepEqual(store.searchIndex.map(x=>x.id),original.filter(x=>x.status==='已核验'&&x.publishable!==false).map(x=>x.id));
const actual=[...store.fieldProfiles.values()].flat();
assert.deepEqual(actual.map(p=>p.id).sort(),publicProfiles.records.map(p=>p.id).sort());
assert.equal(searchHazardsDetailed(store.searchIndex,'').rows.length,store.searchIndex.length);
const profiles=[];
for(const p of actual){
  const detail=await store.getHazardDetail(store.searchIndex.find(h=>h.id===p.hazardId));
  assert.equal(validateProfileJoin(p,detail,publicProfiles.asOf),true);
  const filtered=searchHazardsDetailed(store.searchIndex,'',{inspectionClass:p.inspectionClass}).rows;
  assert.ok(filtered.some(h=>h.id===p.hazardId));
  if(p.findingTemplate===null)assert.equal(profileTemplateText(p),'');
  assert.equal(p.observedViolation,false);
  profiles.push({id:p.id,hazardId:p.hazardId,inspectionClass:p.inspectionClass,defaultFieldEntry:p.defaultFieldEntry,template:p.findingTemplate===null?'none':'unfilled_reference',exactLinks:p.basisLinkIds});
}
console.log(JSON.stringify({status:'passed',acceptanceType:'data_and_controller_only_not_GUI',asOf:publicProfiles.asOf,originalHazardsPreserved:store.searchIndex.length,profileCount:profiles.length,profiles},null,2));
