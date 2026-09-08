import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const CONTENT = path.join(ROOT, 'content');
const DATA = path.join(ROOT, 'data');

const readJson = async name => JSON.parse(await fs.readFile(path.join(CONTENT, name), 'utf8'));
const writeJson = async (file, value) => {
  await fs.mkdir(path.dirname(file), { recursive: true });
  await fs.writeFile(file, JSON.stringify(value, null, 2) + '\n', 'utf8');
};
const fail = msg => { throw new Error(msg); };
const assert = (cond, msg) => { if (!cond) fail(msg); };
const uniq = xs => [...new Set(xs)].sort((a, b) => String(a).localeCompare(String(b), 'zh-CN'));
const dateRe = /^\d{4}-\d{2}-\d{2}$/;
const idRe = /^[A-Z][A-Z0-9_-]{1,31}$/;
const urlRe = /^https?:\/\//i;
const norm = value => String(value ?? '').normalize('NFKC').toLowerCase()
  .replace(/[，。；：、（）()【】\[\]《》“”‘’'"·•…—–_-]+/g, ' ')
  .replace(/\s+/g, ' ').trim();

const recordMap = (rows, kind) => {
  const m = new Map();
  for (const row of rows) {
    assert(row && typeof row === 'object' && !Array.isArray(row), `${kind} 存在非对象记录`);
    assert(typeof row.id === 'string' && idRe.test(row.id), `${kind} ID 无效：${row.id}`);
    assert(!m.has(row.id), `${kind} ID 重复：${row.id}`);
    m.set(row.id, row);
  }
  return m;
};
const requireString = (obj, key, ctx, {allowEmpty=false}={}) => {
  assert(typeof obj[key] === 'string', `${ctx}.${key} 必须为字符串`);
  if (!allowEmpty) assert(obj[key].trim(), `${ctx}.${key} 不能为空`);
};
const requireStringArray = (obj, key, ctx, {allowEmpty=false}={}) => {
  assert(Array.isArray(obj[key]) && obj[key].every(x => typeof x === 'string'), `${ctx}.${key} 必须为字符串数组`);
  if (!allowEmpty) assert(obj[key].length, `${ctx}.${key} 不能为空`);
};

const readBatchFiles = async () => {
  const dir = path.join(CONTENT, 'batches');
  let names = [];
  try {
    names = (await fs.readdir(dir)).filter(name => name.endsWith('.json')).sort();
  } catch (err) {
    if (err?.code !== 'ENOENT') throw err;
  }
  const batches = [];
  for (const name of names) {
    const batch = JSON.parse(await fs.readFile(path.join(dir, name), 'utf8'));
    assert(batch && typeof batch === 'object' && !Array.isArray(batch), `batch:${name} 必须为对象`);
    for (const key of ['hazards','laws','clauses','links']) {
      if (batch[key] === undefined) batch[key] = [];
      assert(Array.isArray(batch[key]), `batch:${name}.${key} 必须为数组`);
    }
    batches.push({name, ...batch});
  }
  return batches;
};

const [settings, baseHazards, baseLaws, baseClauses, baseLinks, batches] = await Promise.all([
  readJson('settings.json'),
  readJson('hazards.json'),
  readJson('laws.json'),
  readJson('clauses.json'),
  readJson('links.json'),
  readBatchFiles()
]);

// All source records are validated, but only fully verified/current records are published.
const allHazards = [...baseHazards, ...batches.flatMap(b => b.hazards)];
const allLaws = [...baseLaws, ...batches.flatMap(b => b.laws)];
const allClauses = [...baseClauses, ...batches.flatMap(b => b.clauses)];
const allLinks = [...baseLinks, ...batches.flatMap(b => b.links)];

assert(settings.schemaVersion === 2, 'settings.schemaVersion 必须为 2');
assert(typeof settings.dataVersion === 'string' && settings.dataVersion, 'settings.dataVersion 不能为空');
assert(dateRe.test(settings.generatedAt), 'settings.generatedAt 必须为 YYYY-MM-DD');
assert(Number.isInteger(settings.hazardShardSize) && settings.hazardShardSize >= 100 && settings.hazardShardSize <= 2000, 'hazardShardSize 应为 100~2000');
assert(Number.isInteger(settings.clauseShardSize) && settings.clauseShardSize >= 100 && settings.clauseShardSize <= 2000, 'clauseShardSize 应为 100~2000');

const allHazardMap = recordMap(allHazards, 'hazard');
const allLawMap = recordMap(allLaws, 'law');
const allClauseMap = recordMap(allClauses, 'clause');

const hazardModes = ['直接适用','条件适用','上位法兜底'];
const hazardStatuses = ['待核验','已核验','已失效'];
const lawStatuses = ['现行有效','即将生效','已废止','待核验'];
const clauseStatuses = ['待核验','已核验','已失效'];

for (const h of allHazards) {
  const ctx = `hazard:${h.id}`;
  for (const key of ['title','category','description','measures','note','mode','status','checked']) requireString(h,key,ctx,{allowEmpty:key==='checked'});
  requireStringArray(h,'aliases',ctx,{allowEmpty:true});
  requireStringArray(h,'places',ctx);
  requireStringArray(h,'keywords',ctx);
  assert(hazardModes.includes(h.mode), `${ctx}.mode 无效`);
  assert(hazardStatuses.includes(h.status), `${ctx}.status 无效`);
  if (h.checked) assert(dateRe.test(h.checked), `${ctx}.checked 日期无效`);
}
for (const l of allLaws) {
  const ctx = `law:${l.id}`;
  for (const key of ['name','level','scope','status','checked','sourceUrl','effectiveDate']) requireString(l,key,ctx,{allowEmpty:['checked','sourceUrl','effectiveDate'].includes(key)});
  requireStringArray(l,'aliases',ctx,{allowEmpty:true});
  requireStringArray(l,'replaces',ctx,{allowEmpty:true});
  requireStringArray(l,'replacedBy',ctx,{allowEmpty:true});
  assert(lawStatuses.includes(l.status), `${ctx}.status 无效`);
  if (l.checked) assert(dateRe.test(l.checked), `${ctx}.checked 日期无效`);
  if (l.effectiveDate) assert(dateRe.test(l.effectiveDate), `${ctx}.effectiveDate 日期无效`);
  if (l.sourceUrl) assert(urlRe.test(l.sourceUrl), `${ctx}.sourceUrl 必须是 http(s)`);
  for (const ref of [...l.replaces, ...l.replacedBy]) assert(allLawMap.has(ref), `${ctx} 引用不存在法规：${ref}`);
}
for (const c of allClauses) {
  const ctx = `clause:${c.id}`;
  for (const key of ['lawId','article','quote','checked','status','sourceUrl']) requireString(c,key,ctx,{allowEmpty:['quote','checked','sourceUrl'].includes(key)});
  assert(allLawMap.has(c.lawId), `${ctx}.lawId 不存在：${c.lawId}`);
  assert(clauseStatuses.includes(c.status), `${ctx}.status 无效`);
  if (c.checked) assert(dateRe.test(c.checked), `${ctx}.checked 日期无效`);
  if (c.sourceUrl) assert(urlRe.test(c.sourceUrl), `${ctx}.sourceUrl 必须是 http(s)`);
  if (c.status === '已核验') {
    assert(c.quote.trim(), `${ctx} 已核验但原文为空`);
    const law = allLawMap.get(c.lawId);
    assert((c.sourceUrl || law.sourceUrl || '').trim(), `${ctx} 已核验但无来源链接`);
  }
}

const linkKeys = new Set();
const allLinksByHazard = new Map();
for (const link of allLinks) {
  const ctx = `link:${link.hazardId}->${link.clauseId}`;
  requireString(link,'hazardId',ctx);
  requireString(link,'clauseId',ctx);
  requireString(link,'role',ctx);
  assert(allHazardMap.has(link.hazardId), `${ctx} 隐患不存在`);
  assert(allClauseMap.has(link.clauseId), `${ctx} 条款不存在`);
  assert(Number.isFinite(link.priority), `${ctx}.priority 必须为数字`);
  const key = `${link.hazardId}\u0000${link.clauseId}`;
  assert(!linkKeys.has(key), `${ctx} 重复关联`);
  linkKeys.add(key);
  if (!allLinksByHazard.has(link.hazardId)) allLinksByHazard.set(link.hazardId, []);
  allLinksByHazard.get(link.hazardId).push(link);
}
for (const h of allHazards) assert((allLinksByHazard.get(h.id) || []).length > 0, `hazard:${h.id} 没有关联任何法规条款`);

// Public gate: pending/expired data can stay in source staging, but never enters runtime.
const isActiveLaw = law => law?.status === '现行有效';
const isVerifiedClause = clause => clause?.status === '已核验' && isActiveLaw(allLawMap.get(clause.lawId));
const publishableHazardIds = new Set(allHazards.filter(h => {
  if (h.status !== '已核验') return false;
  const refs = allLinksByHazard.get(h.id) || [];
  return refs.length > 0 && refs.every(ref => isVerifiedClause(allClauseMap.get(ref.clauseId)));
}).map(h => h.id));

const hazards = allHazards.filter(h => publishableHazardIds.has(h.id));
const links = allLinks.filter(x => publishableHazardIds.has(x.hazardId) && isVerifiedClause(allClauseMap.get(x.clauseId)));
const publishedClauseIds = new Set(links.map(x => x.clauseId));
const clauses = allClauses.filter(c => publishedClauseIds.has(c.id));
const publishedLawIds = new Set(clauses.map(c => c.lawId));
const laws = allLaws.filter(l => publishedLawIds.has(l.id) || ((l.status === '现行有效' || l.status === '即将生效') && l.checked && l.sourceUrl));

const lawMap = new Map(laws.map(x => [x.id, x]));
const clauseMap = new Map(clauses.map(x => [x.id, x]));
for (const h of hazards) {
  const refs = links.filter(x => x.hazardId === h.id);
  assert(refs.length > 0, `公开隐患 ${h.id} 缺少已核验依据`);
  for (const ref of refs) {
    const c = clauseMap.get(ref.clauseId);
    const l = c && allLawMap.get(c.lawId);
    assert(c?.status === '已核验', `公开隐患 ${h.id} 关联未核验条款 ${ref.clauseId}`);
    assert(l?.status === '现行有效', `公开隐患 ${h.id} 关联非现行法规 ${c?.lawId}`);
  }
}

const sortedHazards = [...hazards].sort((a,b)=>a.id.localeCompare(b.id,'zh-CN'));
const sortedClauses = [...clauses].sort((a,b)=>a.id.localeCompare(b.id,'zh-CN'));
const hazardShardOf = new Map();
const clauseShardOf = new Map();
const hazardShards = [];
const clauseShards = [];
for (let i=0; i<sortedHazards.length; i += settings.hazardShardSize) {
  const id = `h${String(hazardShards.length).padStart(4,'0')}`;
  const rows = sortedHazards.slice(i, i + settings.hazardShardSize);
  rows.forEach(r => hazardShardOf.set(r.id,id));
  hazardShards.push({id,url:`data/hazards/${id}.json`,count:rows.length,firstId:rows[0]?.id||'',lastId:rows.at(-1)?.id||'',rows});
}
for (let i=0; i<sortedClauses.length; i += settings.clauseShardSize) {
  const id = `c${String(clauseShards.length).padStart(4,'0')}`;
  const rows = sortedClauses.slice(i, i + settings.clauseShardSize);
  rows.forEach(r => clauseShardOf.set(r.id,id));
  clauseShards.push({id,url:`data/clauses/${id}.json`,count:rows.length,firstId:rows[0]?.id||'',lastId:rows.at(-1)?.id||'',rows});
}

const linksByHazard = new Map();
const linksByClause = new Map();
for (const x of links) {
  if (!linksByHazard.has(x.hazardId)) linksByHazard.set(x.hazardId,[]);
  if (!linksByClause.has(x.clauseId)) linksByClause.set(x.clauseId,[]);
  linksByHazard.get(x.hazardId).push(x);
  linksByClause.get(x.clauseId).push(x);
}
for (const xs of linksByHazard.values()) xs.sort((a,b)=>a.priority-b.priority || a.clauseId.localeCompare(b.clauseId));

const runtimeHazards = new Map();
const searchIndex = [];
for (const h of sortedHazards) {
  const refs = (linksByHazard.get(h.id)||[]).map(x=>({clauseId:x.clauseId,clauseShard:clauseShardOf.get(x.clauseId),role:x.role,priority:x.priority}));
  runtimeHazards.set(h.id,{...h,basisRefs:refs});
  const linkedClauses = refs.map(x=>clauseMap.get(x.clauseId));
  const linkedLaws = linkedClauses.map(c=>allLawMap.get(c.lawId));
  const lawNames = uniq(linkedLaws.map(l=>l.name));
  const articles = uniq(linkedClauses.map(c=>c.article));
  const levels = uniq(linkedLaws.map(l=>l.level));
  const scopes = uniq(linkedLaws.map(l=>l.scope));
  const searchParts=[h.id,h.title,...h.aliases,h.category,...h.places,...h.keywords,...lawNames,...articles];
  searchIndex.push({id:h.id,title:h.title,aliases:h.aliases,category:h.category,places:h.places,keywords:h.keywords,status:h.status,mode:h.mode,checked:h.checked,levels,scopes,lawNames,articles,shard:hazardShardOf.get(h.id),searchText:norm(searchParts.join(' '))});
}

const lawIndex = [];
for (const law of [...laws].sort((a,b)=>a.id.localeCompare(b.id,'zh-CN'))) {
  const lawClauses = sortedClauses.filter(c=>c.lawId===law.id);
  const clauseRefs = lawClauses.map(c=>{
    const hids=uniq((linksByClause.get(c.id)||[]).map(x=>x.hazardId));
    return {id:c.id,article:c.article,shard:clauseShardOf.get(c.id),hazardIds:hids};
  });
  const hazardIds=uniq(clauseRefs.flatMap(x=>x.hazardIds));
  lawIndex.push({...law,clauseRefs,hazardCount:hazardIds.length,clauseCount:clauseRefs.length,searchText:norm([law.id,law.name,...law.aliases,law.level,law.scope,...clauseRefs.map(x=>x.article)].join(' '))});
}

const taxonomy = {
  categories: uniq(hazards.map(x=>x.category)),
  places: uniq(hazards.flatMap(x=>x.places)),
  lawLevels: uniq(laws.map(x=>x.level)),
  scopes: uniq(laws.map(x=>x.scope)),
  hazardModes,
  hazardStatuses,
  lawStatuses
};
const stagedHazardIds = allHazards.filter(x => !publishableHazardIds.has(x.id)).map(x => x.id);
const stagedLawIds = allLaws.filter(x => x.status === '待核验').map(x => x.id);
const publicBatchNames = batches.filter(b => b.hazards.some(h => publishableHazardIds.has(h.id)) || b.laws.some(l => lawMap.has(l.id))).map(b => b.name);
const stagedBatchNames = batches.filter(b => b.hazards.some(h => stagedHazardIds.includes(h.id)) || b.laws.some(l => stagedLawIds.includes(l.id)) || b.clauses.some(c => c.status === '待核验')).map(b => b.name);

const health = {
  verifiedHazards: hazards.length,
  pendingHazards: 0,
  expiredHazards: 0,
  activeLaws: laws.filter(x=>x.status==='现行有效').length,
  pendingLaws: 0,
  invalidReferences: 0,
  stagedHazards: stagedHazardIds.length,
  stagedLaws: stagedLawIds.length
};
const manifest = {
  schemaVersion: settings.schemaVersion,
  dataVersion: settings.dataVersion,
  generatedAt: settings.generatedAt,
  publicScope: settings.publicScope,
  counts: {hazards:hazards.length,laws:laws.length,clauses:clauses.length,links:links.length},
  sourceCounts: {hazards:allHazards.length,laws:allLaws.length,clauses:allClauses.length,links:allLinks.length},
  health,
  batches: publicBatchNames,
  stagedBatches: stagedBatchNames,
  files: {searchIndex:'data/search-index.json',lawIndex:'data/law-index.json',taxonomy:'data/taxonomy.json'},
  hazardShards: hazardShards.map(({rows,...x})=>x),
  clauseShards: clauseShards.map(({rows,...x})=>x)
};

await fs.rm(path.join(DATA,'hazards'),{recursive:true,force:true});
await fs.rm(path.join(DATA,'clauses'),{recursive:true,force:true});
await fs.mkdir(path.join(DATA,'hazards'),{recursive:true});
await fs.mkdir(path.join(DATA,'clauses'),{recursive:true});
for (const shard of hazardShards) await writeJson(path.join(ROOT,shard.url), {schemaVersion:2,shard:shard.id,records:shard.rows.map(h=>runtimeHazards.get(h.id))});
for (const shard of clauseShards) await writeJson(path.join(ROOT,shard.url), {schemaVersion:2,shard:shard.id,records:shard.rows});
await writeJson(path.join(DATA,'search-index.json'),searchIndex);
await writeJson(path.join(DATA,'law-index.json'),lawIndex);
await writeJson(path.join(DATA,'taxonomy.json'),taxonomy);
await writeJson(path.join(DATA,'manifest.json'),manifest);

console.log(`Built public data v${settings.dataVersion}: ${hazards.length} verified hazards, ${laws.length} laws, ${clauses.length} clauses, ${links.length} links. Staged/unpublished: ${stagedHazardIds.length} hazards, ${stagedLawIds.length} laws.`);
