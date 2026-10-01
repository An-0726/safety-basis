'use strict';

import { EQUIVALENT_GROUPS, RELATED_GROUPS, SEGMENT_TERMS } from './search-vocabulary.js';

export const normalize = value => String(value ?? '').normalize('NFKC').toLowerCase()
  .replace(/[，。；：、（）()【】\[\]《》“”‘’'"·•…—–_-]+/g,' ')
  .replace(/\s+/g,' ').trim();

// Parse only recognized GB designations, never compact all prose or match a
// standard number as an arbitrary numeric substring. Keep family and year.
const STANDARD_NUMBER = /\bgb(?:\s*\/\s*([tz])|\s*(t))?[\s_-]*(\d+(?:\.\d+)?)(?:\s*[-_/—–]\s*(\d+)|\s+(\d+))?(?![a-z0-9.])/gi;
const extractStandardNumbers = value => {
  const standards=[];
  const remainder=String(value??'').normalize('NFKC').replace(STANDARD_NUMBER,(_match,kind,compactT,number,year,spacedYear)=>{
    standards.push({family:`gb${kind||compactT?`/${(kind||compactT).toLowerCase()}`:''}`,number,year:year||spacedYear||''});
    return ' ';
  });
  return {standards,remainder};
};
const prepareQuery = query => {
  const original=String(query??'').normalize('NFKC');
  const aliasExpanded=original.includes('重大隐患');
  // This expands a search phrase only. It grants no classification, source
  // coverage, or conclusion that a real site has a major accident hazard.
  const expanded=original.replaceAll('重大隐患','重大事故隐患');
  return {...extractStandardNumbers(expanded),expanded,queryNotice:aliasExpanded
    ? '已将“重大隐患”按检索别名“重大事故隐患”展开。检索结果不代表现场已构成重大事故隐患，仍须核实判定条件和现场事实。'
    : ''};
};
const standardsMatch = (row, wanted, kind) => {
  if(!wanted.length)return true;
  // Match dedicated identities only. A title mentioning another standard is
  // not evidence that this row is that standard or has its current basis.
  const values=kind==='hazards'?(row.stdNumbers||[]):[row.documentNumber||''];
  const available=values.flatMap(value=>extractStandardNumbers(value).standards);
  return wanted.every(q=>available.some(s=>s.family===q.family&&s.number===q.number&&(!q.year||s.year===q.year)));
};


const displayCategoryOf = row => row.displayCategory ?? row.category ?? '';
const displayLevelsOf = row => Array.isArray(row.displayLevels) ? row.displayLevels : (row.levels || []);
const sceneTagsOf = row => Array.isArray(row.sceneTags) ? row.sceneTags : [];
const sceneFilterMatch = (row, value) => {
  if(!value) return true;
  const tags=sceneTagsOf(row);
  return value==='__unclassified__' || value==='未细分场景'
    ? tags.length===0
    : tags.includes(value);
};
const modeMatches = (row, value) => {
  if(!value) return true;
  if(row.mode===value) return true;
  return (value==='direct' && row.mode==='直接适用') ||
    (value==='conditional' && row.mode==='有条件适用');
};

// Search vocabulary is kept separately so equivalence and fallback relevance can be audited.
const groupMap = groups => {
  const map = new Map();
  for (const group of groups) {
    const words = [...new Set(group.map(normalize))];
    for (const word of words) {
      const related = map.get(word) || new Set([word]);
      for (const variant of words) related.add(variant);
      map.set(word, related);
    }
  }
  return map;
};
// Keep literal abbreviation hits as well as the expanded formal phrase.
// This vocabulary is for retrieval only, never the major-hazard topic catalog.
const EQUIVALENTS = groupMap([...EQUIVALENT_GROUPS,['重大事故隐患','重大隐患']]);
const RELATED = groupMap(RELATED_GROUPS);
const VOCAB_SET = new Set([...EQUIVALENTS.keys(), ...RELATED.keys(), ...SEGMENT_TERMS.map(normalize)]);
const SORTED_VOCAB = Array.from(VOCAB_SET).sort((a, b) => b.length - a.length);

const segmentTerm = term => {
  if (VOCAB_SET.has(term) || term.length < 4) return [term];
  const result = [];
  let i = 0;
  while (i < term.length) {
    let matched = false;
    for (const word of SORTED_VOCAB) {
      if (term.startsWith(word, i)) {
        result.push(word);
        i += word.length;
        matched = true;
        break;
      }
    }
    if (!matched) {
      let j = i + 1;
      while (j < term.length) {
        if (SORTED_VOCAB.some(w => term.startsWith(w, j))) break;
        j++;
      }
      result.push(term.slice(i, j));
      i = j;
    }
  }
  return result.filter(w => w.trim().length > 0);
};

const termsOf = query => {
  const raw = normalize(query).split(" ").filter(Boolean);
  return raw.flatMap(segmentTerm);
};

const variantsOf = term => [...(EQUIVALENTS.get(term) || [term])];
const relatedVariantsOf = term => {
  const variants = new Set(variantsOf(term));
  for (const variant of [...variants]) {
    for (const related of RELATED.get(variant) || []) {
      for (const equivalent of variantsOf(related)) variants.add(equivalent);
    }
  }
  return [...variants];
};
// 正确的领域词不能对正文做单字通配或散落字片匹配：
// “安全员”不能因为正文有“安全阀/安全出口”就命中。
const termsMatch = (text, groups) => groups.every(variants=>variants.some(t=>text.includes(t)));

// 只为词典外的中文词提供单字替换或相邻错序纠正；歧义时不猜。
// 在当前筛选范围内完全没有原词/同义词结果时，才启用纠正查询。
const isTypoOf = (term, word) => {
  if(!/^[\u4e00-\u9fff]{3,}$/.test(term) || term.length!==word.length) return false;
  const differences=[];
  for(let i=0;i<term.length;i++) if(term[i]!==word[i]) differences.push(i);
  if(differences.length===1) return true;
  if(differences.length!==2) return false;
  const [a,b]=differences;
  return b===a+1 && term[a]===word[b] && term[b]===word[a];
};
const correctedTerm = term => {
  if(VOCAB_SET.has(term)) return term;
  const candidates=SORTED_VOCAB.filter(word=>isTypoOf(term,word));
  return candidates.length===1 ? candidates[0] : term;
};
const matchingRows = (rows, terms) => {
  if(!terms.length) return {rows,terms,matchKind:'all'};
  const groups=terms.map(variantsOf);
  const exact=rows.filter(r=>termsMatch(r.searchText,groups));
  if(exact.length) return {rows:exact,terms,matchKind:'standard'};
  const relatedGroups=terms.map(relatedVariantsOf);
  const related=rows.filter(r=>termsMatch(r.searchText,relatedGroups));
  if(related.length) return {rows:related,terms,matchKind:'related'};
  const corrected=terms.map(correctedTerm);
  if(corrected.every((t,i)=>t===terms[i])) return {rows:[],terms,matchKind:'none'};
  const correctedGroups=corrected.map(variantsOf);
  const correctedRows=rows.filter(r=>termsMatch(r.searchText,correctedGroups));
  return {rows:correctedRows,terms:corrected,matchKind:correctedRows.length?'corrected':'none'};
};

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
  if(r.mode==='direct' || r.mode==='直接适用') score+=2;
  return score;
};

export function searchHazardsDetailed(rows, query, filters={}) {
  const prepared=prepareQuery(query),q=normalize(prepared.expanded),terms=termsOf(prepared.remainder);
  const out=[];
  for(const r of rows){
    if(!standardsMatch(r,prepared.standards,'hazards')) continue;
    if(r.status==='已失效' && filters.status!=='已失效') continue;
    if(filters.category && displayCategoryOf(r)!==filters.category) continue;
    if(filters.displayCategory && displayCategoryOf(r)!==filters.displayCategory) continue;
    if(filters.place && !r.places.includes(filters.place)) continue;
    if(filters.sceneTag && !sceneFilterMatch(r,filters.sceneTag)) continue;
    if(filters.scene && !sceneFilterMatch(r,filters.scene)) continue;
    if(filters.level && !displayLevelsOf(r).includes(filters.level)) continue;
    if(filters.displayLevel && !displayLevelsOf(r).includes(filters.displayLevel)) continue;
    if(filters.region && !scopeMatch(r.scopes,filters.region)) continue;
    if(!modeMatches(r,filters.mode)) continue;
    if(filters.status && r.status!==filters.status) continue;
    out.push(r);
  }
  const matched=matchingRows(out,terms);
  const rankingQuery=matched.terms===terms ? q : matched.terms.join('');
  const scored=matched.rows.map(row=>({row,score:hazardScore(row,rankingQuery,matched.terms)}));
  scored.sort((a,b)=>b.score-a.score || a.row.title.localeCompare(b.row.title,'zh-CN'));
  return {rows:scored.map(x=>x.row),matchKind:prepared.standards.length&&matched.matchKind==='all'?(matched.rows.length?'standard':'none'):matched.matchKind,interpretedQuery:matched.terms.join(' '),queryNotice:prepared.queryNotice};
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

export function searchLawsDetailed(rows, query, filters={}) {
  const prepared=prepareQuery(query),q=normalize(prepared.expanded),terms=termsOf(prepared.remainder);
  const out=[];
  for(const r of rows){
    if(!standardsMatch(r,prepared.standards,'laws')) continue;
    if(r.status==='已废止' && filters.status!=='已废止') continue;
    if(filters.level && (r.displayLevel??r.level)!==filters.level) continue;
    if(filters.displayLevel && (r.displayLevel??r.level)!==filters.displayLevel) continue;
    if(filters.region && !scopeMatch([r.scope],filters.region)) continue;
    if(filters.status && r.status!==filters.status) continue;
    out.push(r);
  }
  const matched=matchingRows(out,terms);
  const rankingQuery=matched.terms===terms ? q : matched.terms.join('');
  const scored=matched.rows.map(row=>({row,score:lawScore(row,rankingQuery,matched.terms)}));
  scored.sort((a,b)=>b.score-a.score || a.row.name.localeCompare(b.row.name,'zh-CN'));
  return {rows:scored.map(x=>x.row),matchKind:prepared.standards.length&&matched.matchKind==='all'?(matched.rows.length?'standard':'none'):matched.matchKind,interpretedQuery:matched.terms.join(' '),queryNotice:prepared.queryNotice};
}

// Preserve the original array API for the field pilot, callers and stored links.
export function searchHazards(rows, query, filters={}) {
  return searchHazardsDetailed(rows,query,filters).rows;
}
export function searchLaws(rows, query, filters={}) {
  return searchLawsDetailed(rows,query,filters).rows;
}
