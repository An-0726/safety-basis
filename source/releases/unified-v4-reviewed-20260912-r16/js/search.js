'use strict';

export const normalize = value => String(value ?? '').normalize('NFKC').toLowerCase()
  .replace(/[，。；：、（）()【】\[\]《》“”‘’'"·•…—–_-]+/g,' ')
  .replace(/\s+/g,' ').trim();

const termsOf = query => normalize(query).split(' ').filter(Boolean);
const allTermsMatch = (text,terms) => terms.every(t=>text.includes(t));

// 概念同义词组（Search 2.0，交接说明书第 8 章）：
// 查询词命中间组内任一变体即可召回，解决口语词与库内规范用语不一致（如 配电房→配电室/配电箱）。
// 组表按库内 searchText 实际覆盖校准（2026-09-12，50 组）。
const SYNONYM_GROUPS = [
  ['配电房','配电室','配电间','配电箱','配电柜','低压配电','变电所'],
  ['安全员','安管员','安全管理人员','安全生产管理人员'],
  ['灭火器失压','灭火器没压','灭火器欠压','灭火器压力不足','灭火器压力不够'],
  ['应急灯','应急照明'],
  ['疏散通道','消防通道','疏散走道','逃生通道'],
  ['安全出口指示','疏散指示标志','疏散指示'],
  ['安全出口','疏散出口','逃生出口'],
  ['电瓶车','电动车','电动自行车'],
  ['危废','危险废物'],
  ['危化品','危险化学品'],
  ['劳动防护用品','劳保用品','防护用品','个人防护用品'],
  ['特种作业证','特种作业操作证','特种作业人员证'],
  ['消火栓','消防栓'],
  ['防爆柜','安全柜','化学品柜','试剂柜'],
  ['有限空间','受限空间'],
  ['有限空间作业','受限空间作业'],
  ['动火作业','焊接作业','电焊作业'],
  ['防雷','避雷','接闪'],
  ['漏电保护','剩余电流保护','漏保'],
  ['保护接地','接地接零','等电位连接'],
  ['安全标识','安全标志','警示标识','警示标志'],
  ['职业健康','职业卫生'],
  ['粉尘防爆','粉尘爆炸'],
  ['粉尘','可燃性粉尘','木粉尘'],
  ['防爆电气','防爆电器'],
  ['应急预案演练','应急演练'],
  ['安全生产培训','安全教育培训','安全教育','三级教育'],
  ['叉车','厂内机动车','场（厂）内专用机动车辆'],
  ['起重机','行车','天车'],
  ['安全帽','头部防护'],
  ['防护眼镜','护目镜'],
  ['防尘口罩','口罩'],
  ['防护手套','绝缘手套'],
  ['洗眼器','冲淋装置'],
  ['通风橱','通风柜'],
  ['静电接地','防静电','静电跨接'],
  ['静电','静电积聚'],
  ['防爆工具','无火花工具'],
  ['隐患排查','安全检查','隐患排查治理'],
  ['风险分级管控','风险分级','双重预防'],
  ['安全生产责任制','全员安全生产责任制','责任制'],
  ['气瓶','氧气瓶','乙炔瓶','液化石油气钢瓶'],
  ['压力容器','储气罐','空气储罐','储罐'],
  ['灭火器材','消防器材','消防设施'],
  ['安全联锁','联锁保护','联锁装置'],
  ['事故排风','事故通风'],
  ['泄压','泄爆'],
  ['隔爆','爆炸隔离'],
  ['除尘器','收尘器','布袋除尘'],
  ['应急处置卡','应急处置牌'],
];
const variantsOf = term => {
  for (const group of SYNONYM_GROUPS) {
    if (group.includes(term)) return [...new Set([term, ...group])];
  }
  return [term];
};
// 返回 2=原词命中，1=同义变体命中，0.5=二元切词多数命中（弱召回），
// 0.25=单字符错字容错（单字符通配），0=未命中。
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
const escapeRe = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
// 单字符错字容错：把查询词的某一位置替换为通配符（灭活器→/灭.器/ 等），
// 仅在原词、同义变体、二元切词全部未命中时作为最弱召回使用。
const fuzzyRe = term => {
  const chars = Array.from(term);
  if (chars.length < 3) return null;
  const parts = chars.map((c, i) => chars.map((x, j) => (j === i ? '.' : escapeRe(x))).join(''));
  try { return new RegExp(parts.join('|')); } catch { return null; }
};
const tokenMatch = (text, term) => {
  if (text.includes(term)) return 2;
  for (const v of variantsOf(term)) {
    if (v !== term && text.includes(v)) return 1;
  }
  if (gramsMatch(text, term)) return 0.5;
  const re = fuzzyRe(term);
  return re && re.test(text) ? 0.25 : 0;
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
