'use strict';
import {browseGroupMatches} from './browse-groups.js';
import {hazardSearchGuidance} from './search-guidance.js';
import {pressureGaugeStateBoundary} from './search-boundaries.js';
import {splitFieldIssues, interpretFieldQuery, fieldObservationMatches, fieldDefectMatches, fieldCandidateScore} from './query-intent.js';

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
// DataStore adds fieldProfiles only after public hashes and exact basis joins
// validate. Their approved scenario titles can identify an object as well.
const objectHeading = row => normalize([row.title??row.name??'',...(row.aliases||[]),...(row.keywords||[]),...(row.fieldProfiles||[]).map(p=>p.title)].join(' '));

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
  const literalTitleQuery=normalize(query);
  // A user following a specific published title is browsing that rule, not
  // asserting its wording as an observed fact. Some legal titles themselves
  // contain “疑似” or “记录缺失”; keep these deliberate lookups reachable.
  const isTitleLookup=literalTitleQuery&&rows.some(r=>normalize(r.title)===literalTitleQuery);
  const guidance=isTitleLookup?{notice:'',suggestions:[]}:hazardSearchGuidance(query);
  if(guidance.suppressResults)return {rows:[],matchKind:'none',interpretedQuery:String(query??''),queryNotice:guidance.notice,suggestions:guidance.suggestions,assessment:guidance.assessment,suppressed:true};
  const prepared=prepareQuery(query),q=normalize(prepared.expanded),terms=termsOf(prepared.remainder);
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
  const exactTitleRows=isTitleLookup?out.filter(r=>normalize(r.title)===literalTitleQuery):[];
  const stateBoundary=isTitleLookup?null:pressureGaugeStateBoundary(query);
  const intent=isTitleLookup?null:interpretFieldQuery(query);
  const installationStates=intent?.objects.length?intent.defects.filter(defect=>['absent','damaged'].includes(defect)):[];
  const boundaryRows=out.filter(r=>(!stateBoundary||stateBoundary.heading.test(objectHeading(r)))
    &&installationStates.every(defect=>fieldDefectMatches(r,defect,intent)));
  const matched=isTitleLookup
    ? {rows:exactTitleRows,terms,matchKind:exactTitleRows.length?'standard':'none'}
    : matchingRows(boundaryRows,terms,prepared.remainder);
  const rankingQuery=matched.terms===terms ? q : matched.terms.join('');
  const scored=matched.rows.map((row,i)=>({row,score:matched.ranked?-i:hazardScore(row,rankingQuery,matched.terms)}));
  scored.sort((a,b)=>b.score-a.score || a.row.title.localeCompare(b.row.title,'zh-CN'));
  return {rows:scored.map(x=>x.row),matchKind:prepared.standards.length&&matched.matchKind==='all'?(matched.rows.length?'standard':'none'):matched.matchKind,interpretedQuery:matched.terms.join(' '),queryNotice:[prepared.queryNotice,guidance.notice,stateBoundary?.notice].filter(Boolean).join(' '),suggestions:guidance.suggestions,assessment:stateBoundary?{classification:'needs_conditions',reason:stateBoundary.reason,requiredFacts:stateBoundary.requiredFacts}:guidance.assessment||{classification:scored.length?'candidate_matches':'no_result',reason:scored.length?'retrieval_candidates':'no_retrieval_match',requiredFacts:[]}};
}

const searchChoice=(label,query,note)=>({label,query,note});
const passageChoices = [
  searchChoice('人员疏散通道', '疏散通道占用', '确认承担人员疏散用途，再核实堆物是否占用或影响通行。'),
  searchChoice('消防车道', '消防车道堵塞', '确认属于消防车辆通行车道，并核实实际通行障碍。'),
  searchChoice('配电箱操作通道', '配电箱前堆物', '确认属于配电箱操作或检修空间，再核实实际遮挡或占用。'),
];
const activeFilters = filters => Object.fromEntries(Object.entries(filters).filter(([,value])=>value!==''&&value!==null&&value!==undefined));

function issueGuidance(interpretation) {
  const {query,defects}=interpretation;
  const objects=defects.length?interpretation.subjects:interpretation.objects;
  if(objects.some(object=>object.key==='配电箱')&&!defects.length&&/不合格|出了问题|有问题|不知道|不清楚|未核实/.test(query))return {
    suppressResults:true,notice:'配电箱的具体缺陷尚未明确。请分别核实保护接地、内部线路和箱门状态，选择与现场事实相符的方向；“不合格”不能直接解释成其中任何一项。',
    suggestions:[searchChoice('核查保护接地','配电箱接地','核实保护导体及连接位置和实际状态。'),searchChoice('核查内部线路','电气线路绝缘损坏','核实线路绝缘及带电部位，不能只凭模糊照片认定。'),searchChoice('核查箱门连接','装有电器的可开启配电箱（柜）门与金属框架未可靠连接','核实箱门是否装有电器及保护连接。')],
    assessment:{classification:'needs_conditions',reason:'cabinet_defect_unconfirmed',requiredFacts:['实际缺陷部件','具体状态与现场证据','供电和设备使用场景']},
  };
  if(objects.some(object=>object.key==='插排')&&/额定|实测|电流|功率|超负荷|过载/.test(query))return {
    suppressResults:!defects.includes('overload'),
    notice:'插排负荷须核对同一设备的额定电流或功率与同时运行的实际负荷。电器数量不能证明超负荷；安培与瓦不能直接比较。已描述的数值仅用于寻找候选，仍须核实铭牌、测量方式和实际使用条件。',
    suggestions:[searchChoice('核查插排负荷依据','移动式插座（插线板）超负荷使用','记录额定值及同维度、同时运行的实际负荷，核对适用范围。')],
    assessment:{classification:'needs_conditions',reason:'power_strip_load_conditions',requiredFacts:['同一插排的额定电流或功率','同时运行的实际负荷与测量证据','单位和测量条件是否可直接比较','产品及使用场景的适用范围']},
  };
  if(objects.some(object=>object.key==='气瓶')&&defects.includes('unsecured'))return {
    notice:'按气瓶立放或放置时固定、防倾倒问题查找候选。缺少一条链条不能证明没有其他有效固定；须核实支架、卡箍等替代措施、实际稳定状态及瓶型和使用范围。',suggestions:[],
    assessment:{classification:'needs_conditions',reason:'cylinder_securing_conditions',requiredFacts:['气瓶类型及放置或使用状态','是否有其他可靠固定或防倾倒措施','实际稳定情况及现场证据','排除车用或固定使用瓶式压力容器等不适用情形']},
  };
  if(objects.some(object=>object.key==='安全阀')&&defects.includes('calibration_overdue'))return {
    notice:'安全阀校验与压力容器本体定期检验、压力表检定分别核查。本体检验有效不能代替安全阀校验；候选仍需核实所属设备、校验期限和继续使用状态。',suggestions:[],
    assessment:{classification:'needs_conditions',reason:'valve_calibration_conditions',requiredFacts:['安全阀及所属设备适用范围','校验记录、期限及证据','实际使用状态']},
  };
  if(objects.some(object=>object.key==='固定式压力容器')&&defects.includes('inspection_overdue'))return {
    notice:'按压力容器本体定期检验期限查找候选，须先核实是否属于特种设备监管及定检范围、有效期和继续使用状态。超期不等于已有“不合格”检验结论，也不能自动认定重大事故隐患。',suggestions:[],
    assessment:{classification:'needs_conditions',reason:'vessel_inspection_conditions',requiredFacts:['压力容器是否属于法定特种设备及定检范围','本体定期检验期限和实际检验记录','是否继续使用','不得把超期推成检验结论不合格']},
  };
  if(objects.some(object=>object.key==='压力表')&&defects.includes('pressure_mark_missing'))return {
    notice:'按压力表工作压力红线查找候选；玻璃完好与检定有效不代替刻度盘红线要求。仍须确认固定式压力容器适用范围及表盘实际标记。',suggestions:[],
    assessment:{classification:'needs_conditions',reason:'gauge_mark_conditions',requiredFacts:['所属设备及条款适用范围','指示工作压力的红线是否确实缺失','表盘和工作压力现场证据']},
  };
  if(objects.some(object=>['洒水喷头','感烟探测器'].includes(object.key))&&defects.includes('obstructed'))return {
    notice:'按已描述的消防设施遮挡查找候选。请核实设施类型、是否已投入或恢复使用及实际遮挡；喷头的临时施工保护与遗留障碍、点型探测器与线型光束探测器应分别处理。',suggestions:[],
    assessment:{classification:'needs_conditions',reason:'fire_device_obstruction_conditions',requiredFacts:['自动喷水系统或点型探测器的实际类型','投入或恢复使用状态','遮挡物位置和实际影响','施工临时保护是否已按要求拆除']},
  };
  if(objects.some(object=>object.key==='电动自行车')&&defects.includes('entry_elevator'))return {
    notice:'按电动自行车进入住宅电梯或户内的行为查找候选。须核实住宅场景、实际进入行为和地域范围；住户行为与物业劝阻义务分别检索。',suggestions:[],
    assessment:{classification:'needs_conditions',reason:'bicycle_entry_conditions',requiredFacts:['住宅电梯或户内场景','实际进入行为及行为主体','条款地域与生效范围']},
  };
  if(objects.some(object=>object.key==='配电箱')&&defects.includes('absent'))return {
    suppressResults:true,notice:'原话表示配电箱尚未安装，不能套用已安装后的配线、箱门接地或损坏规则。请核实供配电方案、是否应设、场所和使用阶段；当前库内没有足以凭这句话直接认定缺项的通用条目。',
    suggestions:[],assessment:{classification:'needs_conditions',reason:'cabinet_installation_unconfirmed',requiredFacts:['场所与供配电方式','是否依法或按适用设计应设置配电箱','尚未施工还是已投入使用','适用条款与现场证据']},
  };
  if(objects.some(object=>object.key==='电动自行车')&&/(?:拉线|拖线)充电/.test(query))return {
    notice:'按电动自行车充电方式查找候选；使用电线充电本身不能证明违规。请核实是否实际私拉乱接或飞线、所在场所及条目的地域适用范围。',
    suggestions:[],assessment:{classification:'needs_conditions',reason:'bicycle_charging_conditions',requiredFacts:['具体接线方式及现场证据','充电场所','条款地域与对象范围']},
  };
  if(objects.some(object=>object.key==='消防控制室')&&defects.includes('understaffed'))return {
    notice:'按消防控制室实际值班人数查找候选。仍须核对火灾报警系统类型、消防控制室设置及适用的地方规定，不能由单人观察推定所有时段或持证情况。',suggestions:[],
    assessment:{classification:'needs_conditions',reason:'control_room_staffing_scope',requiredFacts:['集中或控制中心报警系统等适用条件','实际班次及在岗人数','相关地域规定']},
  };
  if(objects.some(object=>object.key==='安全帽')&&defects.includes('not_worn'))return {
    notice:'按已描述的作业时未佩戴安全帽查找候选；仍须核实岗位风险、现场规定和实际佩戴状态，不推定所有工作场所都必须戴安全帽。',suggestions:[],
    assessment:{classification:'needs_conditions',reason:'helmet_use_scope',requiredFacts:['岗位头部防护需求或现场佩戴规定','实际作业及佩戴情况']},
  };
  if(objects.some(object=>object.key==='起升高度限位器')&&defects.includes('absent'))return {
    suppressResults:!interpretation.objects.some(object=>object.key==='起重机'),
    notice:'限位装置缺少与已经安装但动作失灵分别核查。须确认起重机型式、设计制造依据、目录参数及已有装置形式；原话数值和年份不会自动证明全部适用条件已满足。',
    suggestions:[],assessment:{classification:'needs_conditions',reason:'height_limiter_scope',requiredFacts:['所属设备及起重机型式','设计制造日期与适用依据','目录参数及限位装置形式']},
  };
  const genericPassage=objects.some(object=>object.key==='通道')
    &&!objects.some(object=>['疏散通道','消防车道','配电箱','配电室','安全出口'].includes(object.key));
  if(genericPassage&&defects.includes('obstructed'))return {
    suppressResults:true,notice:'“通道”用途尚不明确。请选择人员疏散、消防车辆通行或设备操作通道，并核实堆物是否实际妨碍通行；不自动套用喷涂、施工或某一地域的专用规则。',
    suggestions:passageChoices,assessment:{classification:'needs_conditions',reason:'passage_use_unconfirmed',requiredFacts:['通道实际用途','堆放物位置及通行受阻情况','场所与地域适用条件']},
  };
  if(objects.some(object=>object.key==='配电箱')&&defects.includes('grounding'))return {
    notice:'配电箱接地须分别核实箱体保护接地、保护导体连接及装有电器的箱门连接。候选中的箱门或施工临时用电条件必须现场确认，不能由“没接地”自动补齐。',
    suggestions:[searchChoice('保护接地线连接', '保护接地线连接不可靠或采用缠绕、挂钩', '确认该导体承担保护接地功能及实际连接情况。'),
      searchChoice('装有电器的可开启箱门', '装有电器的可开启配电箱（柜）门与金属框架未可靠连接', '仅在确认箱门装有电器、可开启及连接不可靠时选用。')],
    assessment:{classification:'needs_conditions',reason:'cabinet_grounding_conditions',requiredFacts:['保护接地或其他导体用途','箱体、箱门或导体的实际缺陷位置','是否属于装有电器的可开启门或施工临时用电场景']},
  };
  if(objects.some(object=>object.key==='起重机')&&defects.includes('damaged')&&!/吊钩|防脱|限位|制动|钢丝绳|联锁|急停/.test(query))return {
    suppressResults:true,notice:'已按起重设备理解“行车”，但“坏了”尚不能确定是吊钩、防脱装置、限位还是其他部件。请明确部件和失效表现；不因名称相符就套用吊钩损坏规则。',
    suggestions:[searchChoice('查看起重机相关候选', '起重机', '先核具体机型，再按实际部件和缺陷选择。')],
    assessment:{classification:'needs_conditions',reason:'crane_defect_unconfirmed',requiredFacts:['起重机型式与适用范围','具体故障部件','观察、测试和实际失效情况']},
  };
  if(objects.some(object=>object.key==='报警器')&&!/火灾|可燃|有毒|一氧化碳|危(?:险)?化(?:学)?品|生产设备/.test(query))return {
    suppressResults:true,notice:'报警器类型尚未明确。请先区分火灾、可燃气体或有毒气体报警，再核实未安装、已安装但故障或其他状态；这些设备与义务不能互换。',
    suggestions:[searchChoice('火灾报警设备','火灾自动报警系统','核实具体探测器或控制器，以及实际故障或配置问题。'),
      searchChoice('可燃气体报警设备','可燃气体','核实检测介质、危险区域和装置状态。'),
      searchChoice('有毒气体报警设备','有毒气体','核实气体种类、使用场景和装置状态。')],
    assessment:{classification:'needs_conditions',reason:'alarm_type_unconfirmed',requiredFacts:['检测或报警对象','装置类型与场所','实际安装与功能状态']},
  };
  return null;
}

function oneFieldIssue(rows, raw, filters, index, inheritedSubject=null) {
  const lookup=inheritedSubject?`${inheritedSubject.name}，${raw}`:raw;
  let interpretation={...interpretFieldQuery(lookup),original:raw,inheritedSubject};
  const exact=rows.some(row=>normalize(row.title)===normalize(raw))&&normalize(raw)!=='';
  let result=searchHazardsDetailed(rows,lookup,filters);
  if(interpretation.corrections.length&&result.rows.length&&result.matchKind!=='corrected'
    &&interpretation.corrections.some(item=>result.rows.some(row=>objectHeading(row).includes(item.from)))) {
    interpretation={...interpretFieldQuery(lookup,{correctTypos:false}),original:raw,inheritedSubject};
  }
  const initialAssessment=result.assessment?.classification;
  const protectedState=['fact_unconfirmed','evidence_gap'].includes(initialAssessment);
  const semanticGuidance=exact||initialAssessment==='evidence_gap'?null:issueGuidance(interpretation);
  // A deliberately chosen full title is kept as an exact lookup. Known-state
  // or known-source-gap guidance takes precedence over any natural-language
  // rewrite. Unknown wording is never silently discarded to force a hit.
  if(protectedState&&semanticGuidance?.suggestions?.length)result={...result,
    queryNotice:[result.queryNotice,semanticGuidance.notice].filter(Boolean).join(' '),
    suggestions:semanticGuidance.suggestions,
    assessment:{...result.assessment,requiredFacts:[...new Set([...(result.assessment?.requiredFacts||[]),...(semanticGuidance.assessment?.requiredFacts||[])])]}};
  else if(!protectedState&&semanticGuidance?.suppressResults)result={rows:[],matchKind:'none',interpretedQuery:interpretation.query,
    queryNotice:semanticGuidance.notice,suggestions:semanticGuidance.suggestions,assessment:semanticGuidance.assessment};
  else if(!exact&&!protectedState) {
    if(!result.rows.length&&interpretation.changed) {
      const alternative=searchHazardsDetailed(rows,interpretation.query,filters);
      // A safe interpretation may expose an existing ambiguity/negation guard
      // that a long prefix hid, even when it quite properly has no results.
      if(alternative.rows.length||alternative.queryNotice||alternative.suggestions?.length)result=alternative;
    }
    const canRefine=!result.suppressed&&['candidate_matches','no_result','needs_conditions'].includes(result.assessment?.classification);
    if(canRefine&&interpretation.objects.length) {
      const conforms=row=>fieldObservationMatches(row,interpretation);
      let candidates=result.rows.filter(conforms);
      // Only this controlled object+state fallback drops conversational words.
      // Each candidate must match an observed subject and its own defect.
      // Parent equipment and location remain context rather than extra ANDs.
      // Ambiguous, negated and documentary queries have already stopped above.
      if(interpretation.defects.length) {
        const standards=prepareQuery(interpretation.query).standards;
        const filtered=searchHazardsDetailed(rows,'',filters).rows.filter(row=>standardsMatch(row,standards,'hazards'));
        candidates=[...new Map([...candidates,...filtered.filter(conforms)].map(row=>[row.id,row])).values()];
      }
      const rankingIntent={...interpretation,scenes:[...interpretation.scenes,...['place','region','scene','sceneTag'].map(key=>filters[key]).filter(Boolean)]};
      const ranked=candidates.map((row,position)=>({row,score:fieldCandidateScore(row,rankingIntent,position)}))
        .sort((a,b)=>b.score-a.score||String(a.row.title).localeCompare(String(b.row.title),'zh-CN'));
      const changed=result.rows.length!==ranked.length||ranked.some((item,i)=>item.row.id!==result.rows[i]?.id);
      result={...result,rows:ranked.map(item=>item.row),matchKind:ranked.length?(result.matchKind==='none'?'colloquial':result.matchKind):'none',
        interpretedQuery:ranked.length&&changed?[...(interpretation.subjects.length?interpretation.subjects:interpretation.objects).map(object=>object.name),...interpretation.defects.map(defect=>({pressure_loss:'失压',grounding:'接地',verification_overdue:'检定超期',inspection_overdue:'定期检验超期',calibration_overdue:'校验超期',pressure_mark_missing:'工作压力红线缺失',damaged:'损坏',absent:'未设置',obstructed:'占用或遮挡',locked:'锁闭',unsecured:'防倾倒或固定',overload:'超负荷',entry_elevator:'进入住宅电梯或户内',charging_wiring:'飞线充电',not_worn:'未佩戴',understaffed:'值班人数不足'}[defect]))].join(' '):result.interpretedQuery,
        assessment:result.assessment?.classification==='needs_conditions'?result.assessment:{classification:ranked.length?'candidate_matches':'no_result',reason:ranked.length?'object_and_state_candidates':'no_object_state_match',requiredFacts:[]}};
    }
    if(interpretation.changed&&result.assessment?.classification==='candidate_matches') {
      const canonicalGuidance=hazardSearchGuidance(interpretation.query);
      if(canonicalGuidance.assessment?.classification==='needs_conditions')result={...result,
        queryNotice:[result.queryNotice,canonicalGuidance.notice].filter(Boolean).join(' '),
        suggestions:canonicalGuidance.suggestions,assessment:canonicalGuidance.assessment};
    }
    if(semanticGuidance&&!['fact_unconfirmed','evidence_gap'].includes(result.assessment?.classification))result={...result,
      queryNotice:[result.queryNotice,semanticGuidance.notice].filter(Boolean).join(' '),
      suggestions:[...(result.suggestions||[]),...semanticGuidance.suggestions],assessment:semanticGuidance.assessment};
    if(result.rows.length&&interpretation.quantitativeFacts.length)result={...result,
      queryNotice:[result.queryNotice,`原话中的数值条件已保留：${interpretation.quantitativeFacts.join('、')}。候选不代表已满足条款阈值、设备范围或设计制造日期要求，请逐项核对适用条件。`].filter(Boolean).join(' '),
      assessment:{...result.assessment,classification:'needs_conditions',requiredFacts:[...new Set([...(result.assessment?.requiredFacts||[]),'原话数值、日期与条款适用条件逐项核对'])]}};
  }
  const corrected=interpretation.corrections.length&&result.rows.length&&normalize(result.interpretedQuery)!==normalize(raw)
    ?interpretation.corrections.map(item=>`“${item.from}”→“${item.to}”`).join('、'):'';
  const changedNotice=interpretation.changed&&!exact&&!protectedState&&!semanticGuidance?.suppressResults
    ?`已保留原话，按“${interpretation.query}”查找${corrected?`（纠错：${corrected}）`:''}。`:'';
  const titleTerms=[...interpretation.objects.flatMap(object=>{
    const group=EQUIVALENT_GROUPS.find(names=>names.includes(object.name));return group||[object.name];
  }),...(result.interpretedQuery||'').split(/\s+/).filter(Boolean)];
  const cleanFilters=activeFilters(filters);
  let unfilteredCount=0,zeroReason='';
  if(!result.rows.length) {
    if(['fact_unconfirmed','evidence_gap'].includes(result.assessment?.classification)||semanticGuidance?.suppressResults)zeroReason=result.assessment?.classification||'needs_conditions';
    else if(Object.keys(cleanFilters).length) {
      const unfiltered=oneFieldIssue(rows,raw,{},index,inheritedSubject);
      unfilteredCount=unfiltered.rows.length;
      zeroReason=unfilteredCount?'filters_exclude_matches':(unfiltered.zeroReason||'no_library_match');
    } else zeroReason=result.assessment?.classification==='needs_conditions'?'needs_conditions':'no_library_match';
  }
  return {...result,id:`issue-${index+1}`,query:raw,originalQuery:raw,interpretation,
    queryNotice:[changedNotice,result.queryNotice].filter(Boolean).join(' '),
    highlightTerms:[...new Set(titleTerms)].filter(term=>term.length>=2),
    activeFilters:cleanFilters,unfilteredCount,zeroReason};
}

/** The original website's observation search. Each independent issue keeps
 * its own candidates and disposition; the aggregate is an OR union, never an
 * impossible AND across different equipment and defects. */
export function searchHazardIssuesDetailed(rows, query, filters={}) {
  const raw=String(query??'').trim();
  const exact=raw&&rows.some(row=>normalize(row.title)===normalize(raw));
  const parts=exact?[{query:raw}]:splitFieldIssues(raw);
  const issues=parts.map((part,index)=>oneFieldIssue(rows,part.query,filters,index,part.inheritedSubject));
  const combined=[...new Map(issues.flatMap(issue=>issue.rows).map(row=>[row.id,row])).values()];
  return {issues,rows:combined,isMultiIssue:issues.length>1,query:raw,
    queryNotice:issues.length>1?`已分为 ${issues.length} 个问题分别检索。每组仅提供候选，现场事实与适用条件仍需核实。`:issues[0]?.queryNotice||'',
    matchKind:issues.length>1?'multiple':issues[0]?.matchKind||'none',
    interpretedQuery:issues.map(issue=>issue.interpretedQuery).join('；'),
    suggestions:issues.length===1?issues[0].suggestions:[],assessment:issues.length===1?issues[0].assessment:null};
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
