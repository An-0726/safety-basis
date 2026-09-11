'use strict';

export const normalize = value => String(value ?? '').normalize('NFKC').toLowerCase()
  .replace(/[，。；：、（）()【】\[\]《》“”‘’'"·•…—–_-]+/g,' ')
  .replace(/\s+/g,' ').trim();

const termsOf = query => normalize(query).split(' ').filter(Boolean);
const allTermsMatch = (text,terms) => terms.every(t=>text.includes(t));
const scopeMatch = (scopes, region) => !region || scopes.some(x => region==='全国' ? x==='全国' : x.includes(region));

const hazardScore=(r,q,terms)=>{
  if(!terms.length) return 0;
  const title=normalize(r.title), aliases=normalize(r.aliases.join(' ')), keywords=normalize(r.keywords.join(' ')), laws=normalize(r.lawNames.join(' '));
  let score=0;
  if(title===q) score+=160;
  else if(title.startsWith(q)) score+=120;
  else if(title.includes(q)) score+=95;
  if(aliases.includes(q)) score+=70;
  if(keywords.includes(q)) score+=55;
  if(laws.includes(q)) score+=35;
  for(const t of terms){
    if(title.includes(t)) score+=28;
    else if(aliases.includes(t)) score+=20;
    else if(keywords.includes(t)) score+=14;
    else if(laws.includes(t)) score+=8;
    else score+=2;
  }
  if(r.status==='已核验') score+=3;
  if(r.mode==='直接适用') score+=2;
  return score;
};

export function searchHazards(rows, query, filters={}) {
  const q=normalize(query), terms=termsOf(query);
  const out=[];
  for(const r of rows){
    if(r.status==='已失效' && filters.status!=='已失效') continue;
    if(filters.category && r.category!==filters.category) continue;
    if(filters.place && !r.places.includes(filters.place)) continue;
    if(filters.level && !r.levels.includes(filters.level)) continue;
    if(filters.region && !scopeMatch(r.scopes,filters.region)) continue;
    if(filters.mode && r.mode!==filters.mode) continue;
    if(filters.status && r.status!==filters.status) continue;
    if(terms.length && !allTermsMatch(r.searchText,terms)) continue;
    out.push({row:r,score:hazardScore(r,q,terms)});
  }
  out.sort((a,b)=>b.score-a.score || a.row.title.localeCompare(b.row.title,'zh-CN'));
  return out.map(x=>x.row);
}

const lawScore=(r,q,terms)=>{
  if(!terms.length) return 0;
  const name=normalize(r.name), aliases=normalize(r.aliases.join(' '));
  let score=0;
  if(name===q) score+=160;
  else if(name.startsWith(q)) score+=120;
  else if(name.includes(q)) score+=95;
  if(aliases.includes(q)) score+=60;
  for(const t of terms){
    if(name.includes(t)) score+=28;
    else if(aliases.includes(t)) score+=18;
    else score+=3;
  }
  if(r.status==='现行有效') score+=3;
  return score;
};

export function searchLaws(rows, query, filters={}) {
  const q=normalize(query), terms=termsOf(query);
  const out=[];
  for(const r of rows){
    if(r.status==='已废止' && filters.status!=='已废止') continue;
    if(filters.level && r.level!==filters.level) continue;
    if(filters.region && !scopeMatch([r.scope],filters.region)) continue;
    if(filters.status && r.status!==filters.status) continue;
    if(terms.length && !allTermsMatch(r.searchText,terms)) continue;
    out.push({row:r,score:lawScore(r,q,terms)});
  }
  out.sort((a,b)=>b.score-a.score || a.row.name.localeCompare(b.row.name,'zh-CN'));
  return out.map(x=>x.row);
}
