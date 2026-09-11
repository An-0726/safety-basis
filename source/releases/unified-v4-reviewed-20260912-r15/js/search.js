'use strict';

export const normalize = value => String(value ?? '').normalize('NFKC').toLowerCase()
  .replace(/[，。；：、（）()【】\[\]《》“”‘’'"·•…—–_-]+/g,' ')
  .replace(/\s+/g,' ').trim();

const termsOf = query => normalize(query).split(' ').filter(Boolean);
const allTermsMatch = (text,terms) => terms.every(t=>text.includes(t));

// 概念同义词组（Search 2.0 第一步，交接说明书第 8 章）：
// 查询词命中间组内任一变体即可召回，解决口语词与库内规范用语不一致（如 配电房→配电室/配电箱）。
const SYNONYM_GROUPS = [
  ['配电房','配电室','配电间','配电箱','配电柜','低压配电','变电所'],
  ['安全员','安管员','安全管理人员'],
  ['灭火器失压','灭火器没压','灭火器欠压','灭火器压力不足','灭火器压力不够'],
  ['应急灯','应急照明'],
  ['疏散通道','消防通道','疏散走道'],
  ['安全出口指示','疏散指示标志','疏散指示'],
  ['电瓶车','电动车','电动自行车'],
  ['危废','危险废物'],
  ['劳动防护用品','劳保用品','防护用品'],
  ['特种作业证','特种作业操作证','特种作业人员证'],
  ['消火栓','消防栓'],
  ['防爆柜','安全柜'],
];
const variantsOf = term => {
  for (const group of SYNONYM_GROUPS) {
    if (group.includes(term)) return [...new Set([term, ...group])];
  }
  return [term];
};
// 返回 2=原词命中，1=同义变体命中，0.5=二元切词多数命中（弱召回），0=未命中。
// 二元切词兜底解决中文整句无空格查询（如“配电房警示标志”）拆不出词导致的 0 命中。
const gramsOf = term => {
  const chars = Array.from(term);
  return chars.length < 3 ? [] : [...new Set(chars.slice(0, -1).map((c, i) => c + chars[i + 1]))];
};
const gramsMatch = (text, term) => {
  const grams = gramsOf(term);
  if (!grams.length) return false;
  const hit = grams.filter(g => text.includes(g)).length;
  return hit >= Math.ceil(grams.length / 2);
};
const tokenMatch = (text, term) => {
  if (text.includes(term)) return 2;
  for (const v of variantsOf(term)) {
    if (v !== term && text.includes(v)) return 1;
  }
  return gramsMatch(text, term) ? 0.5 : 0;
};
const termsMatch = (text,terms) => terms.every(t=>tokenMatch(text,t)>0);

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
    else if(variantsOf(t).some(v=>v!==t&&title.includes(v))) score+=12;
    else if(variantsOf(t).some(v=>v!==t&&(aliases.includes(v)||keywords.includes(v)))) score+=8;
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
    if(terms.length && !termsMatch(r.searchText,terms)) continue;
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
    else if(variantsOf(t).some(v=>v!==t&&name.includes(v))) score+=12;
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
    if(terms.length && !termsMatch(r.searchText,terms)) continue;
    out.push({row:r,score:lawScore(r,q,terms)});
  }
  out.sort((a,b)=>b.score-a.score || a.row.name.localeCompare(b.row.name,'zh-CN'));
  return out.map(x=>x.row);
}
