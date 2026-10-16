'use strict';
import {browseGroupMatches} from './browse-groups.js';
import {hazardSearchGuidance} from './search-guidance.js';

import { EQUIVALENT_GROUPS, RELATED_GROUPS, SEGMENT_TERMS, COLLOQUIAL_TERMS, COLLOQUIAL_FILLERS, COLLOQUIAL_WORDS, COLLOQUIAL_IGNORED_CHARS, COLLOQUIAL_LEADING_VERBS } from './search-vocabulary.js';

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
const latinTermPatterns = new Map();
const termOccurs = (text, term) => {
  if(term==='行车')return /(?<!自)行车(?!制动|或驻车制动|和驻车制动|道|路线|速度)/.test(text);
  if(term==='天车')return /(?<![露每])天车/.test(text);
  // Acronyms such as PPE, RCD, SDS and LEL are whole Latin words; do not
  // retrieve copper, parallel or an unrelated identifier by a short substring.
  if(/^[a-z][a-z0-9]+$/.test(term)){
    if(!latinTermPatterns.has(term))latinTermPatterns.set(term,new RegExp(`(?<![a-z0-9])${term}(?![a-z0-9])`));
    return latinTermPatterns.get(term).test(text);
  }
  return text.includes(term);
};
const termsMatch = (text, groups) => groups.every(variants=>variants.some(t=>termOccurs(text,t)));
const objectHeading = row => normalize([row.title??row.name??'',...(row.aliases||[]),...(row.keywords||[])].join(' '));

// Topic choices must describe the rule's object. Background prose mentioning
// another device or a general chapter does not establish that object.
const PRIMARY_TOPICS = new Map([
  ['疏散通道',[['疏散通道','疏散走道','逃生通道']]],
  ['消防车道',[['消防车道','消防车通道']]],
  ['防火门',[['防火门']]],
  ['安全出口',[['安全出口','疏散出口','逃生出口']]],
  ['感烟火灾探测器',[['感烟','烟感','点型火灾探测器']]],
  ['火灾自动报警系统',[['火灾自动报警系统','火灾报警系统','火灾报警控制器','消防报警主机','火警主机']]],
  ['可燃气体',[['可燃气体','燃气','煤气','氢气']]],
  ['有毒气体',[['有毒气体']]],
  ['一氧化碳',[['一氧化碳']]],
  ['有限空间气体检测',[['有限空间'],['气体检测']]],
  ['便携式可燃气体检测',[['便携式'],['可燃气体'],['检测']]],
  ['固定式压力容器',[['固定式压力容器']]],
  ['气瓶',[['气瓶','液化石油气钢瓶']]],
  ['压力表',[['压力表']]],
  ['个人防坠落用品',[['个人防坠落用品']]],
  ...['危险化学品仓库','危化品仓库','危化库'].map(query=>[query,[['危险化学品仓库','危化品仓库','危化库']]]),
]);
const primaryTopicRows = (rows, query) => {
  const groups=PRIMARY_TOPICS.get(normalize(query));
  return groups?rows.filter(row=>termsMatch(objectHeading(row),groups)):rows;
};

// Workshop crane names refer to the rule's equipment, not a bicycle substring,
// road-vehicle braking, or a crane mentioned only in another rule's exclusions.
// Use the same object check for hazards and law names; complete title lookups
// remain handled separately below.
const CRANE_QUERY_TERMS = new Set(['行车','天车','起重机','起重机械','起重设备','门式起重机','龙门吊']);
const craneObjectRows = (rows, terms) => !terms.some(t=>CRANE_QUERY_TERMS.has(t)) ? rows : rows.filter(row=>{
  const heading=objectHeading(row);
  return ['起重机','起重机械','起重设备','天车','行车','龙门吊'].some(term=>termOccurs(heading,term));
});

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
// 口语查询解释：只在原词、相关概念和纠错都没有结果时使用。去掉“没/了/被”等
// 虚词，把口语缺陷词换成条文用语；识别出的每个部分仍须全部命中，不做部分匹配。
// 换出来的缺陷用语必须出现在条目标题、别名或关键词里：正文里顺带提到“损坏”
// 的“未设置”类条目不算命中。
const COLLOQUIAL = new Map(Object.entries(COLLOQUIAL_TERMS).map(([key,values])=>[normalize(key),values.map(normalize)]));
const FILLERS = new Set(COLLOQUIAL_FILLERS.map(normalize));
const COLLOQUIAL_LEXICON = [...new Set([...VOCAB_SET,...COLLOQUIAL.keys(),...FILLERS,...COLLOQUIAL_WORDS.map(normalize)])]
  .sort((a,b)=>b.length-a.length);
const interpretColloquial = query => {
  const groups=[],labels=[],spokenGroups=[];
  let rewritten=false;
  const add=(label,variants,spoken=false)=>{groups.push(variants);labels.push(label);if(spoken)spokenGroups.push(variants);};
  for(const chunk of normalize(query).split(' ').filter(Boolean)){
    let run='';
    // 词典外的片段按原样要求命中；剩下的单个字（没水→水）须出现在标题里，
    // 方位字和虚化动词除外。
    const flush=()=>{while(run.length>1&&COLLOQUIAL_LEADING_VERBS.includes(run[0])){run=run.slice(1);rewritten=true;}if(run.length>1)add(run,[run]);else if(run){rewritten=true;if(!COLLOQUIAL_IGNORED_CHARS.includes(run))add(run,[run],true);}run='';};
    for(let i=0;i<chunk.length;){
      const word=COLLOQUIAL_LEXICON.find(w=>chunk.startsWith(w,i));
      if(!word){run+=chunk[i++];continue;}
      flush();i+=word.length;
      if(FILLERS.has(word)){rewritten=true;continue;}
      const spoken=COLLOQUIAL.get(word);
      if(spoken)rewritten=true;
      if(spoken)add(spoken[0],spoken,true);else add(word,relatedVariantsOf(word));
    }
    flush();
  }
  return rewritten&&groups.length ? {groups,labels,spokenGroups} : null;
};
const colloquialRows = (rows, query) => {
  const parsed=interpretColloquial(query);
  if(!parsed) return null;
  const nameOf=row=>String(row.title??row.name??'');
  // 标题直接出现所说对象或首选条文用语的条目排前，其次是标题出现其他等价用语的条目。
  const titleHits=row=>{const title=normalize(nameOf(row));return parsed.groups.reduce((sum,g,i)=>sum+(termOccurs(title,parsed.labels[i])?3:g.some(t=>termOccurs(title,t))?2:0),0);};
  const headingOf=row=>normalize([nameOf(row),...(row.aliases||[]),...(row.keywords||[])].join(' '));
  const hits=rows.filter(r=>termsMatch(r.searchText,parsed.groups)&&termsMatch(headingOf(r),parsed.spokenGroups)).map(row=>({row,score:titleHits(row)}));
  if(!hits.length) return null;
  hits.sort((a,b)=>b.score-a.score || nameOf(a.row).length-nameOf(b.row).length || nameOf(a.row).localeCompare(nameOf(b.row),'zh-CN'));
  return {rows:hits.map(x=>x.row),terms:parsed.labels,matchKind:'colloquial',ranked:true};
};
const matchingRows = (rows, terms, query='') => {
  rows=primaryTopicRows(craneObjectRows(rows,terms),query);
  const strict=strictRows(rows,terms);
  return strict.matchKind==='none' ? (colloquialRows(rows,query)||strict) : strict;
};
const strictRows = (rows, terms) => {
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
  else if(title.startsWith(q)&&termOccurs(title,q)) score+=120;
  else if(termOccurs(title,q)) score+=95;
  if(termOccurs(aliases,q)) score+=70;
  if(termOccurs(keywords,q)) score+=55;
  if(termOccurs(laws,q)) score+=35;
  for(const t of terms){
    if(termOccurs(title,t)) score+=28;
    else if(termOccurs(aliases,t)) score+=20;
    else if(termOccurs(keywords,t)) score+=14;
    else if(termOccurs(laws,t)) score+=8;
    else if(variantsOf(t).some(v=>v!==t&&termOccurs(title,v))) score+=12;
    else if(variantsOf(t).some(v=>v!==t&&(termOccurs(aliases,v)||termOccurs(keywords,v)))) score+=8;
    else score+=2;
  }
  if(r.status==='已核验') score+=3;
  if(r.mode==='direct' || r.mode==='直接适用') score+=2;
  return score;
};

export function searchHazardsDetailed(rows, query, filters={}) {
  const guidance=hazardSearchGuidance(query);
  if(guidance.suppressResults)return {rows:[],matchKind:'none',interpretedQuery:String(query??''),queryNotice:guidance.notice,suggestions:guidance.suggestions};
  const prepared=prepareQuery(query),q=normalize(prepared.expanded),terms=termsOf(prepared.remainder);
  const literalTitleQuery=normalize(query);
  const out=[];
  for(const r of rows){
    // A complete prose title can mention a different standard from its basis.
    // Retrieve that literal title without promoting the mention to an identity;
    // designation-only and other keyword queries still require dedicated bases.
    const exactTitle=prepared.standards.length>0 && terms.length>0 && normalize(r.title)===literalTitleQuery;
    if(!exactTitle && !standardsMatch(r,prepared.standards,'hazards')) continue;
    if(r.status==='已失效' && filters.status!=='已失效') continue;
    if(filters.inspectionClass && !(r.inspectionClasses||[]).includes(filters.inspectionClass)) continue;
    if(filters.browse && !browseGroupMatches(r,filters.browse)) continue;
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
  // A complete existing title is a deliberate item lookup, including suggestion clicks.
  // Keep all same-title IDs, but do not substitute body mentions when filters exclude it.
  const isTitleLookup=literalTitleQuery&&rows.some(r=>normalize(r.title)===literalTitleQuery);
  const exactTitleRows=isTitleLookup?out.filter(r=>normalize(r.title)===literalTitleQuery):[];
  const matched=isTitleLookup
    ? {rows:exactTitleRows,terms,matchKind:exactTitleRows.length?'standard':'none'}
    : matchingRows(out,terms,prepared.remainder);
  const rankingQuery=matched.terms===terms ? q : matched.terms.join('');
  const scored=matched.rows.map((row,i)=>({row,score:matched.ranked?-i:hazardScore(row,rankingQuery,matched.terms)}));
  scored.sort((a,b)=>b.score-a.score || a.row.title.localeCompare(b.row.title,'zh-CN'));
  return {rows:scored.map(x=>x.row),matchKind:prepared.standards.length&&matched.matchKind==='all'?(matched.rows.length?'standard':'none'):matched.matchKind,interpretedQuery:matched.terms.join(' '),queryNotice:[prepared.queryNotice,guidance.notice].filter(Boolean).join(' '),suggestions:guidance.suggestions};
}

const lawScore=(r,q,terms)=>{
  if(!terms.length) return 0;
  const name=normalize(r.name), aliases=normalize(r.aliases.join(' '));
  let score=0;
  if(name===q) score+=160;
  else if(name.startsWith(q)&&termOccurs(name,q)) score+=120;
  else if(termOccurs(name,q)) score+=95;
  if(termOccurs(aliases,q)) score+=60;
  for(const t of terms){
    if(termOccurs(name,t)) score+=28;
    else if(termOccurs(aliases,t)) score+=18;
    else if(variantsOf(t).some(v=>v!==t&&termOccurs(name,v))) score+=12;
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
  const matched=matchingRows(out,terms,prepared.remainder);
  const rankingQuery=matched.terms===terms ? q : matched.terms.join('');
  const scored=matched.rows.map((row,i)=>({row,score:matched.ranked?-i:lawScore(row,rankingQuery,matched.terms)}));
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
