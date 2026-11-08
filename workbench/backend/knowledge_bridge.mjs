// Use the exact public DataStore and search engine, including verified joins.
import fs from 'node:fs/promises';
import path from 'node:path';
import readline from 'node:readline';
import {webcrypto} from 'node:crypto';
import {DataStore} from '../../web/js/store.js';
import {searchHazardsDetailed} from '../../web/js/search.js';

const root=path.resolve(process.argv[2]);
if(!globalThis.crypto)globalThis.crypto=webcrypto;
globalThis.fetch=async input=>{
  const url=new URL(String(input));
  if(url.origin!=='http://knowledge.local')throw new Error('Only the configured knowledge bundle is readable');
  const file=path.resolve(root,decodeURIComponent(url.pathname).replace(/^\/+/,''));
  if(!file.startsWith(root+path.sep))throw new Error('Invalid bundle path');
  try{return new Response(await fs.readFile(file),{status:200});}
  catch(error){if(error.code==='ENOENT')return new Response('',{status:404});throw error;}
};
const store=await new DataStore('http://knowledge.local').init();
if(!store.verifiedFiles.manifest)throw new Error('A verified site-manifest.json is required');
const meta={as_of:store.manifest.generatedAt,data_version:store.manifest.dataVersion,
  release_hash:store.manifest.releaseHash,counts:store.manifest.counts,profile_notice:store.fieldProfileNotice};
const output=value=>process.stdout.write(JSON.stringify(value)+'\n');
output({ready:true,meta});
for await (const line of readline.createInterface({input:process.stdin,crlfDelay:Infinity})){
  try{
    const request=JSON.parse(line);
    if(request.op==='meta'){output({ok:true,result:meta});continue;}
    if(request.op==='search'){
      const result=searchHazardsDetailed(store.searchIndex,String(request.q||''),request.filters||{});
      output({ok:true,result:{items:result.rows.slice(0,Math.min(request.limit||30,100)).map(row=>({
        id:row.id,title:row.title,category:row.displayCategory,scopes:row.scopes,mode:row.mode,
        inspectionClasses:row.inspectionClasses,profileSummary:row.profileSummary,
      })),total:result.rows.length,match_kind:result.matchKind,assessment:result.assessment,
      guidance:{notice:result.queryNotice,suggestions:result.suggestions||[]},meta}});continue;
    }
    if(request.op==='detail'){
      const row=store.searchIndex.find(row=>row.id===request.hazard_id);
      if(!row)throw new Error('该条目不在当前正式发布包中');
      output({ok:true,result:{...await store.getHazardDetail(row),profiles:store.getFieldProfiles(row.id),meta}});continue;
    }
    throw new Error('Unknown knowledge operation');
  }catch(error){output({ok:false,error:error.message});}
}
