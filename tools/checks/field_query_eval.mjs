#!/usr/bin/env node
/** Offline field-query evaluation using the production DataStore/search implementation.
 * No telemetry, external API, upload, model-generated legal conclusion, or automatic
 * conversion of a suggestion into a confirmed match. See docs/SEARCH_EVALUATION.md.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {createHash, webcrypto} from 'node:crypto';
import {DataStore} from '../../web/js/store.js';
import {searchHazardsDetailed} from '../../web/js/search.js';

export const SCHEMA_VERSION = 'field-query-evaluation-v1';
export const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const MAX_INPUT_BYTES = 16 * 1024 * 1024;
const MAX_CASES = 10000;
const OUTCOMES = new Set(['candidate_matches', 'needs_conditions', 'evidence_gap', 'fact_unconfirmed', 'no_result']);
const LABELS = new Set(['direct_correct', 'needs_conditions', 'evidence_gap', 'object_mismatch', 'state_mismatch', 'scope_mismatch', 'document_fact_mismatch', 'no_result', 'fact_unconfirmed', 'unreviewed']);
const FILTERS = new Set(['region', 'category', 'displayCategory', 'place', 'scene', 'sceneTag', 'level', 'displayLevel', 'mode', 'status', 'browse', 'inspectionClass']);
const JSON_FIELDS = new Set(['filters', 'required_facts']);
const ARRAY_FIELDS = new Set(['expected_hazard_ids', 'expected_basis_ids', 'forbidden_hazard_ids', 'forbidden_basis_ids']);
const FIELDS = new Set(['id', 'query', 'source_kind', 'source_reference', 'captured_at', 'deidentified', 'publishable', 'annotation_origin', 'review_status', 'expert_label', 'expert_judgment', 'expected_outcome', 'expected_target_route', 'forbidden_match_kind', 'group', ...JSON_FIELDS, ...ARRAY_FIELDS]);
const fail = (message, line) => {throw new Error(`${line ? `第 ${line} 条记录：` : ''}${message}`);};
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const ratio = (numerator, denominator) => ({numerator, denominator, rate: denominator ? numerator / denominator : null});
const inside = (root, candidate) => candidate === root || candidate.startsWith(`${root}${path.sep}`);

// RFC4180-style quoted commas/newlines/escaped quotes, CRLF and UTF-8 BOM.
// Malformed records fail with a row number, never by echoing private field text.
export function parseCsv(text) {
  text = String(text).replace(/^\uFEFF/, '');
  const records = [];
  let row = [], value = '', quoted = false, closed = false, line = 1;
  const field = () => {row.push(value); value = ''; closed = false;};
  const finish = () => {field(); if (row.some(cell => cell !== '')) records.push(row); row = [];};
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"') {if (text[i + 1] === '"') {value += '"'; i++;} else {quoted = false; closed = true;}}
      else {value += c; if (c === '\n') line++;}
      continue;
    }
    if (c === '"') {if (value || closed) fail('CSV 引号位置无效', line); quoted = true; continue;}
    if (c === ',') {field(); continue;}
    if (c === '\n' || c === '\r') {finish(); if (c === '\r' && text[i + 1] === '\n') i++; line++; continue;}
    if (closed) fail('CSV 结束引号后只能接分隔符或换行', line);
    value += c;
  }
  if (quoted) fail('CSV 引号未闭合', line);
  if (value !== '' || row.length || closed) finish();
  if (!records.length) fail('CSV 没有表头');
  const headers = records.shift();
  if (headers.some(h => !h || h !== h.trim()) || new Set(headers).size !== headers.length) fail('CSV 表头为空、重复或含边缘空白');
  for (const h of headers) if (!FIELDS.has(h)) fail(`不支持的 CSV 列名：${h}`);
  return records.map((cells, index) => {
    if (cells.length !== headers.length) fail('CSV 列数与表头不一致', index + 2);
    const item = {};
    for (let i = 0; i < headers.length; i++) {
      const key = headers[i], raw = cells[i];
      if (raw === '' && key !== 'query') continue;
      if (JSON_FIELDS.has(key) || ARRAY_FIELDS.has(key)) {
        try {item[key] = JSON.parse(raw);} catch {fail(`${key} 必须是 JSON 值；CSV 中的引号须双写`, index + 2);}
      } else if (key === 'deidentified' || key === 'publishable') {
        if (!['true', 'false'].includes(raw)) fail(`${key} 只能是 true 或 false`, index + 2);
        item[key] = raw === 'true';
      } else item[key] = raw;
    }
    return item;
  });
}

export function validateCases(input) {
  if (!Array.isArray(input) || !input.length || input.length > MAX_CASES) fail(`数据集须含 1–${MAX_CASES} 条记录`);
  const seen = new Set();
  return input.map((row, i) => {
    const n = i + 1;
    if (!object(row)) fail('记录必须为对象', n);
    for (const key of Object.keys(row)) if (!FIELDS.has(key)) fail(`不支持的字段：${key}`, n);
    if (typeof row.id !== 'string' || !/^[A-Za-z0-9_.-]{1,96}$/.test(row.id) || seen.has(row.id)) fail('id 须为唯一的匿名字母数字标识', n);
    seen.add(row.id);
    if (typeof row.query !== 'string' || !row.query.trim() || row.query.length > 4000) fail('query 必须为 1–4000 字符的非空原始问法', n);
    if (!['synthetic', 'real_deidentified'].includes(row.source_kind)) fail('source_kind 须为 synthetic 或 real_deidentified', n);
    if (!['assistant_synthetic', 'human', 'historical_regression'].includes(row.annotation_origin)) fail('必须声明 annotation_origin', n);
    if (row.source_kind === 'real_deidentified' && row.deidentified !== true) fail('真实记录须先脱敏并设置 deidentified=true', n);
    if (row.annotation_origin === 'assistant_synthetic' && row.source_kind !== 'synthetic') fail('真实记录不能标作 assistant_synthetic', n);
    if (!['reviewed', 'pending'].includes(row.review_status)) fail('review_status 须为 reviewed 或 pending', n);
    if (!LABELS.has(row.expert_label)) fail('expert_label 取值无效', n);
    if (row.review_status === 'reviewed' && row.expert_label === 'unreviewed') fail('已复核记录不能标作 unreviewed', n);
    if (row.review_status === 'reviewed' && (typeof row.expert_judgment !== 'string' || !row.expert_judgment.trim())) fail('已复核记录须保留判读说明 expert_judgment', n);
    if (row.expected_outcome !== undefined && !OUTCOMES.has(row.expected_outcome)) fail('expected_outcome 取值无效', n);
    if (row.expected_target_route !== undefined && !['direct', 'suggestion', 'either', 'none'].includes(row.expected_target_route)) fail('expected_target_route 取值无效', n);
    for (const key of ['deidentified', 'publishable']) if (row[key] !== undefined && typeof row[key] !== 'boolean') fail(`${key} 须为布尔值`, n);
    for (const key of ['source_reference', 'captured_at', 'expert_judgment', 'group', 'forbidden_match_kind']) if (row[key] !== undefined && typeof row[key] !== 'string') fail(`${key} 须为字符串`, n);
    if (row.forbidden_match_kind !== undefined && !['object_mismatch', 'state_mismatch', 'scope_mismatch', 'document_fact_mismatch'].includes(row.forbidden_match_kind)) fail('forbidden_match_kind 取值无效', n);
    const filters = row.filters ?? {};
    if (!object(filters)) fail('filters 须为 JSON 对象', n);
    for (const [k, v] of Object.entries(filters)) if (!FILTERS.has(k) || typeof v !== 'string') fail('filters 含未知筛选项或非字符串值', n);
    const facts = row.required_facts ?? [];
    if (!Array.isArray(facts) || facts.some(f => !object(f) || typeof f.fact !== 'string' || !f.fact.trim() || !['confirmed', 'unconfirmed', 'not_applicable'].includes(f.status) || (f.evidence !== undefined && typeof f.evidence !== 'string') || Object.keys(f).some(k => !['fact', 'status', 'evidence'].includes(k)))) fail('required_facts 须含 fact、status 和可选 evidence，不自动确认事实', n);
    const arrays = {};
    for (const key of ARRAY_FIELDS) {
      const values = row[key] ?? [];
      const prefix = key.includes('hazard') ? 'H' : 'K';
      if (!Array.isArray(values) || values.some(v => typeof v !== 'string' || !new RegExp(`^${prefix}[A-Za-z0-9_]+$`).test(v)) || new Set(values).size !== values.length) fail(`${key} 须为不重复的稳定编号数组`, n);
      arrays[key] = [...values];
    }
    if (arrays.expected_hazard_ids.some(id => arrays.forbidden_hazard_ids.includes(id)) || arrays.expected_basis_ids.some(id => arrays.forbidden_basis_ids.includes(id))) fail('同一编号不能同时为期望和禁止结果', n);
    const expectedTargetRoute = row.expected_target_route ?? (arrays.expected_hazard_ids.length || arrays.expected_basis_ids.length ? 'direct' : 'none');
    if (expectedTargetRoute !== 'none' && !arrays.expected_hazard_ids.length && !arrays.expected_basis_ids.length) fail('指定目标路径时须有期望 H 或 K', n);
    if (expectedTargetRoute === 'none' && (arrays.expected_hazard_ids.length || arrays.expected_basis_ids.length)) fail('none 路径不能附带期望目标', n);
    if (row.review_status === 'reviewed' && !row.expected_outcome && !Object.values(arrays).some(values => values.length)) fail('已复核记录须至少有期望分类、目标 H/K 或禁止 H/K 之一', n);
    return {...row, filters: {...filters}, required_facts: facts.map(f => ({...f})), ...arrays, expected_target_route: expectedTargetRoute, publishable: row.publishable ?? false};
  });
}

export async function readDataset(filename) {
  const bytes = await fs.readFile(filename);
  if (bytes.length > MAX_INPUT_BYTES) fail('输入文件超过 16 MiB');
  let text;
  try {text = new TextDecoder('utf-8', {fatal: true}).decode(bytes);} catch {fail('输入必须为 UTF-8；请先导出为 UTF-8 CSV 或 JSONL');}
  let records;
  const ext = path.extname(filename).toLowerCase();
  if (ext === '.csv') records = parseCsv(text);
  else if (ext === '.jsonl' || ext === '.ndjson') records = text.replace(/^\uFEFF/, '').split(/\r?\n/).flatMap((line, i) => {
    if (!line.trim()) return [];
    try {return [JSON.parse(line)];} catch {fail('JSONL 对象无法解析', i + 1);}
  });
  else fail('输入扩展名须为 .csv、.jsonl 或 .ndjson');
  return {cases: validateCases(records), inputSha256: createHash('sha256').update(bytes).digest('hex')};
}

export async function openPublicStore(bundlePath) {
  const root = await fs.realpath(bundlePath);
  const siteManifest = JSON.parse(await fs.readFile(path.join(root, 'site-manifest.json'), 'utf8'));
  if (siteManifest.schemaVersion !== 'safety-site-bundle-v1') fail('必须使用已生成且有完整性清单的正式发布包');
  // Bind loopback only and serve bundle files read-only. DataStore still performs
  // its own manifest hashes and exact field-profile joins as in the website.
  const server = http.createServer(async (req, res) => {
    try {
      if (req.method !== 'GET') {res.writeHead(405).end(); return;}
      const pathname = decodeURIComponent(new URL(req.url, 'http://127.0.0.1').pathname);
      const requested = path.resolve(root, `.${pathname}`);
      if (!inside(root, requested)) {res.writeHead(403).end(); return;}
      const real = await fs.realpath(requested);
      if (!inside(root, real)) {res.writeHead(403).end(); return;}
      const bytes = await fs.readFile(real);
      res.writeHead(200, {'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store'}).end(bytes);
    } catch {res.writeHead(404).end();}
  });
  await new Promise((resolve, reject) => {server.once('error', reject); server.listen(0, '127.0.0.1', resolve);});
  const close = () => new Promise(resolve => {server.close(resolve); server.closeAllConnections?.();});
  try {
    if (!globalThis.crypto) globalThis.crypto = webcrypto;
    const store = await new DataStore(`http://127.0.0.1:${server.address().port}`).init();
    if (store.fieldProfileNotice) fail('现场画像验证失败，不能按与正式网站不同的降级索引评分');
    return {store, siteManifest, close};
  } catch (error) {await close(); throw error;}
}

const isReviewed = row => row.review_status === 'reviewed';
export const hasExpected = row => row.expected_hazard_ids.length > 0 || row.expected_basis_ids.length > 0;
const accepts = (row, candidate) => (!row.expected_hazard_ids.length || row.expected_hazard_ids.includes(candidate.hazard_id))
  && (!row.expected_basis_ids.length || candidate.basis_ids.some(id => row.expected_basis_ids.includes(id)));
const isForbidden = (row, candidate) => row.forbidden_hazard_ids.includes(candidate.hazard_id)
  || candidate.basis_ids.some(id => row.forbidden_basis_ids.includes(id));

export async function evaluateCases(cases, store) {
  const details = new Map();
  const candidate = async row => {
    if (!details.has(row.id)) details.set(row.id, store.getHazardDetail(row).then(detail => ({
      hazard_id: row.id, title: row.title,
      basis_ids: detail.bases.map(b => b.ref.linkId).filter(Boolean),
      bases: detail.bases.map(b => ({basis_id: b.ref.linkId, clause_id: b.clause.id, law_id: b.law.id, applicability: b.ref.applicability || '', source_url: b.sourceUrl || ''})),
    })));
    return details.get(row.id);
  };
  const byId = new Map(store.searchIndex.map(row => [row.id, row]));
  const labelBasisIds = new Set(cases.flatMap(row => [...row.expected_basis_ids, ...row.forbidden_basis_ids]));
  const availableBasisIds = new Set();
  // Validate labels against this exact public snapshot, not unreviewed source data.
  if (labelBasisIds.size) for (const row of store.searchIndex) {
    const item = await candidate(row);
    for (const id of item.basis_ids) if (labelBasisIds.has(id)) availableBasisIds.add(id);
  }
  const output = [];
  for (const sample of cases) {
    const missingExpected = [...sample.expected_hazard_ids.filter(id => !byId.has(id)), ...sample.expected_basis_ids.filter(id => !availableBasisIds.has(id))];
    const missingForbidden = [...sample.forbidden_hazard_ids.filter(id => !byId.has(id)), ...sample.forbidden_basis_ids.filter(id => !availableBasisIds.has(id))];
    const result = searchHazardsDetailed(store.searchIndex, sample.query, sample.filters);
    const top3 = await Promise.all(result.rows.slice(0, 3).map(candidate));
    const suggestions = [];
    for (const suggestion of result.suggestions || []) {
      const next = searchHazardsDetailed(store.searchIndex, suggestion.query, sample.filters);
      suggestions.push({...suggestion, result_count: next.rows.length, top3: await Promise.all(next.rows.slice(0, 3).map(candidate))});
    }
    const observedOutcome = result.assessment?.classification || (result.queryNotice ? 'needs_conditions' : result.rows.length ? 'candidate_matches' : 'no_result');
    const forbidden = top3.filter(row => isForbidden(sample, row));
    const forbiddenSuggestions = suggestions.flatMap(s => s.top3.filter(row => isForbidden(sample, row)).map(row => ({query: s.query, ...row})));
    output.push({sample, actual: {
      result_count: result.rows.length, top3, match_kind: result.matchKind,
      interpreted_query: result.interpretedQuery, notice: result.queryNotice,
      assessment: result.assessment || null, outcome: observedOutcome, suggestions,
    }, checks: {
      unavailable_expected_ids: missingExpected, unavailable_forbidden_ids: missingForbidden,
      direct_top3_hit: hasExpected(sample) ? top3.some(row => accepts(sample, row)) : null,
      suggestion_top3_hit: hasExpected(sample) ? suggestions.some(s => s.top3.some(row => accepts(sample, row))) : null,
      classification_match: sample.expected_outcome ? observedOutcome === sample.expected_outcome : null,
      conditions_detected: sample.expected_outcome === 'needs_conditions' ? observedOutcome === 'needs_conditions' && Boolean(result.queryNotice) : null,
      evidence_gap_detected: sample.expected_outcome === 'evidence_gap' ? observedOutcome === 'evidence_gap' && Boolean(result.queryNotice) : null,
      severe_mismatch_top3: forbidden.length > 0,
      forbidden_hits: forbidden, forbidden_suggestion_hits: forbiddenSuggestions,
    }});
  }
  return output;
}

export function summarize(results) {
  const reviewed = results.filter(r => isReviewed(r.sample));
  const scoreable = reviewed.filter(r => !r.checks.unavailable_expected_ids.length && !r.checks.unavailable_forbidden_ids.length);
  const direct = scoreable.filter(r => hasExpected(r.sample) && r.sample.expected_target_route === 'direct');
  const suggestion = scoreable.filter(r => hasExpected(r.sample) && r.sample.expected_target_route === 'suggestion');
  const either = scoreable.filter(r => hasExpected(r.sample) && r.sample.expected_target_route === 'either');
  const classified = scoreable.filter(r => r.sample.expected_outcome);
  const conditions = scoreable.filter(r => r.sample.expected_outcome === 'needs_conditions');
  const gaps = scoreable.filter(r => r.sample.expected_outcome === 'evidence_gap');
  const forbiddenReviewed = scoreable.filter(r => r.sample.forbidden_hazard_ids.length || r.sample.forbidden_basis_ids.length);
  const countLabels = {};
  for (const r of results) countLabels[r.sample.expert_label] = (countLabels[r.sample.expert_label] || 0) + 1;
  return {
    samples: results.length, reviewed: reviewed.length, pending: results.length - reviewed.length,
    unavailable_label_samples: reviewed.length - scoreable.length,
    direct_top3: ratio(direct.filter(r => r.checks.direct_top3_hit).length, direct.length),
    conditional_suggestion_top3: ratio(suggestion.filter(r => r.checks.suggestion_top3_hit).length, suggestion.length),
    either_route_top3: ratio(either.filter(r => r.checks.direct_top3_hit || r.checks.suggestion_top3_hit).length, either.length),
    classification_agreement: ratio(classified.filter(r => r.checks.classification_match).length, classified.length),
    conditions_detection: ratio(conditions.filter(r => r.checks.conditions_detected).length, conditions.length),
    evidence_gap_detection: ratio(gaps.filter(r => r.checks.evidence_gap_detected).length, gaps.length),
    severe_mismatch_top3: ratio(forbiddenReviewed.filter(r => r.checks.severe_mismatch_top3).length, forbiddenReviewed.length),
    forbidden_suggestion_samples: forbiddenReviewed.filter(r => r.checks.forbidden_suggestion_hits.length).length,
    unreviewed_mismatch_risk_samples: results.length - forbiddenReviewed.length,
    annotation_labels: countLabels,
  };
}

export function buildReport(results, provenance = {}) {
  const groups = {};
  for (const name of [...new Set(results.map(r => r.sample.group || 'ungrouped'))].sort()) groups[name] = summarize(results.filter(r => (r.sample.group || 'ungrouped') === name));
  const real = results.filter(r => r.sample.source_kind === 'real_deidentified');
  const humanReal = real.filter(r => r.sample.annotation_origin === 'human' && r.sample.review_status === 'reviewed');
  return {
    schema_version: SCHEMA_VERSION, generated_at: new Date().toISOString(), provenance,
    interpretation: '本工具评价显式标注目标的检索表现，标注来源独立声明；合成断言不代表专业人工复核。候选不等于确认隐患；点击建议后的命中不计入原始问法直接 Top3。零分母指标为 null。严重误配仅覆盖明确标注的禁止 H/K；未标注样本不视为安全。',
    real_sample_count: real.length, human_reviewed_real_sample_count: humanReal.length,
    summary: summarize(results), synthetic: summarize(results.filter(r => r.sample.source_kind === 'synthetic')),
    real: summarize(real), human_reviewed_real: summarize(humanReal), groups, results,
  };
}

const escaped = value => String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\\/g, '\\\\').replace(/\|/g, '\\|').replace(/[\r\n]/g, ' ');
const percent = metric => metric.rate === null ? `未评估（0 样本）` : `${metric.numerator}/${metric.denominator}（${(metric.rate * 100).toFixed(1)}%）`;
export function renderMarkdown(report) {
  const rows = ['# 现场检索评估结果', '', `生成时间：${report.generated_at}`, '',
    `真实脱敏样本：**${report.real_sample_count}**；经人工复核的真实样本：**${report.human_reviewed_real_sample_count}**。`, '', report.interpretation, '',
    '| 指标 | 全部样本（含合成） | 经人工复核真实样本 |', '| --- | --- | --- |'];
  for (const [key, label] of [['direct_top3', '原问法直接 Top3'], ['conditional_suggestion_top3', '有条件建议 Top3 可达'], ['either_route_top3', '任一路径 Top3'], ['classification_agreement', '分类一致'], ['conditions_detection', '条件不足提示'], ['evidence_gap_detection', '缺证提示'], ['severe_mismatch_top3', '已标注严重误配']]) rows.push(`| ${label} | ${percent(report.summary[key])} | ${percent(report.human_reviewed_real[key])} |`);
  rows.push('', `未具备禁止 H/K 标注的样本：${report.summary.unreviewed_mismatch_risk_samples}；期望或禁止编号不在本发布包的已复核样本：${report.summary.unavailable_label_samples}。`, '',
    '## 逐条结果', '', '| 匿名编号 | 原始问法 | 判读标签 / 标注来源 | 实际结果 | 前三 H / K | 需复核事项 |', '| --- | --- | --- | --- | --- | --- |');
  for (const r of report.results) {
    const issues = [];
    if (r.checks.unavailable_expected_ids.length) issues.push(`期望编号不可用：${r.checks.unavailable_expected_ids.join(', ')}`);
    if (r.checks.unavailable_forbidden_ids.length) issues.push(`禁止编号不可用：${r.checks.unavailable_forbidden_ids.join(', ')}`);
    if (r.checks.classification_match === false) issues.push('分类不一致');
    if (r.sample.expected_target_route === 'direct' && r.checks.direct_top3_hit === false) issues.push('原问法 Top3 未达期望');
    if (r.sample.expected_target_route === 'suggestion' && r.checks.suggestion_top3_hit === false) issues.push('建议 Top3 未达期望');
    if (r.sample.expected_target_route === 'either' && !r.checks.direct_top3_hit && !r.checks.suggestion_top3_hit) issues.push('任一路径 Top3 均未达期望');
    if (r.checks.severe_mismatch_top3) issues.push('触发禁止结果');
    if (r.checks.forbidden_suggestion_hits.length) issues.push('建议触发禁止结果');
    rows.push(`| ${escaped(r.sample.id)} | ${escaped(r.sample.query)} | ${escaped(`${r.sample.expert_label} / ${r.sample.annotation_origin}`)} | ${escaped(r.actual.outcome)} | ${escaped(r.actual.top3.map(x => `${x.hazard_id} [${x.basis_ids.join(', ')}]`).join('; '))} | ${escaped(issues.join('；') || '详见 JSON 中原始标注、适用性与提示')} |`);
  }
  rows.push('', '完整原始问法、来源代号、筛选条件、期望 H/K、必要事实、判读说明、官方来源链接及逐项检查均保存在同目录 JSON。', '');
  return rows.join('\n');
}

export async function assertSafeOutput(outputDir, cases) {
  const resolved = path.resolve(outputDir);
  if (!cases.some(c => c.source_kind === 'real_deidentified' || !c.publishable)) return resolved;
  // Resolve existing ancestors too, so a symlink under private-intake cannot
  // redirect sensitive reports into a tracked/public directory.
  let existing = resolved;
  const tails = [];
  while (true) {
    try {existing = await fs.realpath(existing); break;} catch (e) {
      if (e.code !== 'ENOENT') throw e;
      const parent = path.dirname(existing); if (parent === existing) throw e;
      tails.unshift(path.basename(existing)); existing = parent;
    }
  }
  const actual = path.resolve(existing, ...tails);
  const privateRoot = path.join(REPO_ROOT, 'private-intake');
  const canonicalPrivateRoot = await fs.realpath(privateRoot).catch(() => privateRoot);
  if (inside(REPO_ROOT, actual) && (canonicalPrivateRoot !== privateRoot || !inside(privateRoot, actual))) fail('真实或不可公开数据的评估报告只能写入仓库 private-intake/ 或仓库外私有目录');
  return resolved;
}

export async function main(argv = process.argv.slice(2)) {
  const options = {};
  for (let i = 0; i < argv.length; i++) {
    const key = argv[i];
    if (key === '--help') {
      console.log('用法：node tools/checks/field_query_eval.mjs --input 私有问法.csv|jsonl --bundle source/releases/current [--output private-intake/search-evaluation/latest] [--check]\n--check 仅在已复核期望、分类、条件/缺证提示及禁止结果检查均通过时成功；零真实样本不代表通过真实现场验收。');
      return 0;
    }
    if (key === '--check') {options.check = true; continue;}
    if (!['--input', '--bundle', '--output'].includes(key) || !argv[i + 1] || argv[i + 1].startsWith('--')) fail('参数无效；使用 --help 查看用法');
    options[key.slice(2)] = argv[++i];
  }
  if (!options.input || !options.bundle) fail('必须指定 --input 和 --bundle');
  const dataset = await readDataset(options.input);
  const output = await assertSafeOutput(options.output || path.join(REPO_ROOT, 'private-intake/search-evaluation/latest'), dataset.cases);
  const opened = await openPublicStore(path.resolve(options.bundle));
  let report;
  try {
    const results = await evaluateCases(dataset.cases, opened.store);
    report = buildReport(results, {input_sha256: dataset.inputSha256, public_bundle_schema: opened.siteManifest.schemaVersion,
      data_manifest: opened.store.manifest, public_hazard_count: opened.store.searchIndex.length,
      search_implementation: 'web/js/store.js + web/js/search.js', source_kind: 'offline_explicit_import'});
  } finally {await opened.close();}
  await fs.mkdir(output, {recursive: true, mode: 0o700});
  await fs.writeFile(path.join(output, 'report.json'), JSON.stringify(report, null, 2) + '\n', {mode: 0o600});
  await fs.writeFile(path.join(output, 'report.md'), renderMarkdown(report), {mode: 0o600});
  // stdout deliberately omits original queries, source labels and findings.
  console.log(JSON.stringify({schema_version: report.schema_version, samples: report.summary.samples,
    real_samples: report.real_sample_count, human_reviewed_real_samples: report.human_reviewed_real_sample_count,
    summary: report.summary, report_directory: output}, null, 2));
  if (!options.check) return 0;
  return checkReport(report) ? 0 : 1;
}


// A check run must contain reviewed assertions; pending-only data is a useful
// capture/report but can never be a successful acceptance gate.
export function checkReport(report) {
  const reviewed = report.results.filter(r => isReviewed(r.sample));
  if (!reviewed.length) return false;
  return reviewed.every(r => !(
    r.checks.unavailable_expected_ids.length || r.checks.unavailable_forbidden_ids.length || r.checks.classification_match === false
    || (r.sample.expected_target_route === 'direct' && !r.checks.direct_top3_hit)
    || (r.sample.expected_target_route === 'suggestion' && !r.checks.suggestion_top3_hit)
    || (r.sample.expected_target_route === 'either' && !r.checks.direct_top3_hit && !r.checks.suggestion_top3_hit)
    || r.checks.severe_mismatch_top3 || r.checks.forbidden_suggestion_hits.length));
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  main().then(code => {process.exitCode = code;}).catch(error => {console.error(`评估未完成：${error.message}`); process.exitCode = 2;});
}
