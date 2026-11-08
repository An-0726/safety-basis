import {zipSync, strToU8} from 'fflate';
import {HttpError, createStore, uid, now, clone, findingBody, FINDING_FIELDS} from './storage.mjs';

const PROJECT_FIELDS = ['company', 'name', 'inspection_date', 'inspectors', 'purpose'];
const TEXT_LIMITS = {location: 500, equipment: 500, observation: 12000, description: 12000,
  rectification: 12000, due_date: 40, assignee: 200, notes: 12000, finding_kind: 30};
const MAX_PHOTO = 20 * 1024 * 1024;
const PRIVATE_HEADERS = {'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer'};
const json = (body, status = 200) => new Response(JSON.stringify(body), {status, headers: {...PRIVATE_HEADERS, 'Content-Type': 'application/json; charset=utf-8'}});
const binary = (body, contentType, filename = '') => new Response(body, {headers: {...PRIVATE_HEADERS,
  'Content-Type': contentType, ...(filename ? {'Content-Disposition': `attachment; filename="${filename}"`} : {})}});
const isObject = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const utf8 = new TextEncoder();

function cleanText(value, limit = 12000) {
  if (typeof value !== 'string' || value.length > limit || /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(value)) throw new HttpError(422, '文本格式或长度无效');
  return value.trim();
}
function validDate(value) {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)
    && !Number.isNaN(Date.parse(`${value}T00:00:00Z`)) && new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) === value;
}
function shape(payload, allowed, message = '包含不支持的字段') {
  if (!isObject(payload) || Object.keys(payload).some(key => !allowed.includes(key))) throw new HttpError(422, message);
}
function projectData(payload, previous = null) {
  shape(payload, PROJECT_FIELDS);
  const data = {...(previous ? Object.fromEntries(PROJECT_FIELDS.map(key => [key, previous[key]])) : {inspectors: '', purpose: '安全检查'}), ...payload};
  const limits = {company: 200, name: 200, inspection_date: 10, inspectors: 300, purpose: 1000};
  for (const key of PROJECT_FIELDS) data[key] = cleanText(data[key], limits[key]);
  if (!data.company || !data.name) throw new HttpError(422, '企业名称和项目名称不能为空');
  if (!validDate(data.inspection_date)) throw new HttpError(422, '检查日期无效');
  return data;
}
function findingData(payload) {
  shape(payload, FINDING_FIELDS, '状态、法源和事实只能通过对应操作修改');
  const data = Object.fromEntries(FINDING_FIELDS.map(key => [key, cleanText(payload[key] ?? (key === 'finding_kind' ? 'onsite' : ''), TEXT_LIMITS[key])]));
  if (!['onsite', 'document_review'].includes(data.finding_kind)) throw new HttpError(422, '记录类型无效');
  if (data.due_date && !validDate(data.due_date)) throw new HttpError(422, '整改日期无效');
  return {...data, status: 'draft', bases: [], facts: []};
}
function positionValue(value) {
  if (!Number.isSafeInteger(value) || value < 0 || value > 100000) throw new HttpError(422, '排序位置无效');
  return value;
}
function normalizedIdentity(identity) {
  const input = typeof identity === 'string' ? {id: identity, source: 'injected'} : identity;
  const id = input?.id || input?.userId;
  if (typeof id !== 'string' || !id.trim() || id.length > 400 || /[\x00-\x1f\x7f]/.test(id)) throw new HttpError(401, '请先登录私有工作台');
  return {id: id.trim(), source: cleanText(input.source || 'injected', 100), displayName: cleanText(input.displayName || id, 400)};
}
async function limitedBody(request, limit) {
  const length = Number(request.headers.get('content-length') || 0);
  if (length > limit) throw new HttpError(413, '请求内容超过允许大小');
  if (!request.body) return new Uint8Array();
  const reader = request.body.getReader(), chunks = [];
  let size = 0;
  try {
    for (;;) {
      const {value, done} = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > limit) { await reader.cancel(); throw new HttpError(413, '请求内容超过允许大小'); }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  return bytes;
}
async function payloadOf(request) {
  const bytes = await limitedBody(request, 2 * 1024 * 1024);
  if (!bytes.length) return {};
  try { const value = JSON.parse(new TextDecoder().decode(bytes)); if (!isObject(value)) throw new Error(); return value; }
  catch { throw new HttpError(422, '请求必须为 JSON 对象'); }
}
function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (isObject(value)) return Object.fromEntries(Object.keys(value).sort().map(key => [key, stable(value[key] ?? null)]));
  return value ?? null;
}
async function sha256(bytes) {
  const hash = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(hash)].map(value => value.toString(16).padStart(2, '0')).join('');
}
const select = (object, keys) => Object.fromEntries(keys.map(key => [key, object?.[key] ?? null]));
export async function sourceFingerprint(detail, item, profile) {
  const source = {
    hazard: select(detail.hazard, ['id', 'title', 'conditions', 'description', 'measures']),
    ref: select(item.ref, ['linkId', 'clauseId', 'role', 'applicability', 'jurisdictionCode']),
    clause: select(item.clause, ['id', 'article', 'quote', 'lawId', 'sourceUrl']),
    law: select(item.law, ['id', 'name', 'documentNumber', 'effectiveDate', 'status', 'scope', 'sourceUrl']),
    profile, dispositions: (detail.profiles || []).map(value => select(value, ['id', 'inspectionClass', 'defaultFieldEntry', 'contentDisposition'])),
  };
  return sha256(utf8.encode(JSON.stringify(stable(source))));
}
export function invalidate(finding, resetFacts = false) {
  if (['confirmed', 'pending_review', 'rejected'].includes(finding.status)) finding.status = 'draft';
  if (resetFacts) for (const fact of finding.facts || []) { fact.status = 'unknown'; fact.note = ''; }
}
export function blockers(finding) {
  const issues = [];
  if (!finding.observation?.trim()) issues.push('请填写现场原话和观察记录');
  if (!finding.description?.trim()) issues.push('请填写经核实的专业隐患描述');
  if (!finding.rectification?.trim()) issues.push('请填写对应整改建议');
  if (!finding.bases?.length) issues.push('尚未选定正式条款；缺证记录可保存为草稿，不可确认');
  for (const hazard of new Set((finding.bases || []).map(basis => basis.hazard_id))) {
    if (!finding.bases.some(basis => basis.hazard_id === hazard && ['direct', 'fallback'].includes(basis.role))) issues.push(`${hazard} 仅选择了辅助依据，请选入直接或兜底依据后审核`);
  }
  for (const fact of finding.facts || []) {
    const valid = fact.status === (fact.expected || 'confirmed') || (fact.allows_denied && fact.status === 'denied');
    if (!valid) issues.push(`待核实：${fact.label}`);
    else if (!fact.note?.trim()) issues.push(`请记录核实依据：${fact.label}`);
  }
  if (finding.bases?.some(basis => basis.inspection_class === 'document_review') && finding.finding_kind !== 'document_review') issues.push('该依据用于资料核查，请将记录类型改为“资料核查”并核实资料缺口');
  return issues;
}
function display(value) { return typeof value === 'string' ? value : value ? JSON.stringify(value) : ''; }
export function rebuildFacts(finding, reset = false) {
  const previous = new Map((finding.facts || []).map(fact => [fact.key, fact]));
  const wanted = [['observation', '现场事实', '现场对象、具体缺陷与观察记录相符，已核实而非推测']];
  const profiles = new Set(), hazards = new Set(), optional = new Set();
  for (const basis of finding.bases) {
    if (!hazards.has(basis.hazard_id)) {
      hazards.add(basis.hazard_id);
      wanted.push([`hazard:${basis.hazard_id}`, '隐患适用范围', display(basis.hazard_conditions) || '已核实该隐患条目的适用条件']);
    }
    wanted.push([`applicability:${basis.id}`, '适用条件', display(basis.applicability) || '本条款的主体、地域和适用条件成立']);
    wanted.push([`scope:${basis.id}`, '地域与范围', `已核对 ${display(basis.scope) || '本条款'} 的地域、行业和适用对象`]);
    const profile = basis.profile;
    if (profile && !profiles.has(profile.id)) {
      profiles.add(profile.id);
      for (const [key, kind] of [['requires', '场景前提'], ['excludes', '误判边界'], ['perUseFacts', '本次事实']]) {
        (profile.applicability?.[key] || []).forEach((value, index) => {
          const factKey = `profile:${profile.id}:${key}:${index}`;
          let label = FACT_LABELS[value] || display(value);
          if (key === 'excludes') label = '已核对并遵守此边界：' + label;
          wanted.push([factKey, kind, label]);
          if (key === 'perUseFacts' && /(?:IfSelected|IfAsserted|IfApplicable)$/.test(value)) optional.add(factKey);
        });
      }
    }
  }
  const seen = new Set();
  finding.facts = wanted.filter(([, kind, label]) => { const key = `${kind}\0${label}`; if (seen.has(key)) return false; seen.add(key); return true; })
    .map(([key, kind, label]) => {
      const old = reset ? {} : previous.get(key) || {};
      return {key, kind, label, expected: 'confirmed', status: old.status || 'unknown', note: old.note || '', allows_denied: optional.has(key)};
    });
}

// The browser normalizes photos with canvas first. This second boundary checks
// JPEG structure and pixel dimensions and strips EXIF/IPTC/comments before R2.
// It performs no full-frame image decoding in the 128 MB Worker isolate.
export function sanitizeJpeg(input) {
  const bytes = input instanceof Uint8Array ? input : new Uint8Array(input);
  if (bytes.length > MAX_PHOTO) throw new HttpError(413, '单张照片不得超过20MB');
  if (bytes.length < 20 || bytes[0] !== 0xff || bytes[1] !== 0xd8) throw new HttpError(422, '仅接受经浏览器清理的 JPEG 图片，请重新选择照片');
  const parts = [bytes.subarray(0, 2)];
  let offset = 2, width = 0, height = 0, scan = false, ended = false;
  while (offset < bytes.length) {
    const start = offset;
    if (bytes[offset++] !== 0xff) throw new HttpError(422, 'JPEG 标记结构无效');
    while (bytes[offset] === 0xff) offset += 1;
    const marker = bytes[offset++];
    if (marker === 0xd9) {
      if (offset !== bytes.length || !scan || !width || !height) throw new HttpError(422, 'JPEG 图像不完整或包含额外数据');
      parts.push(bytes.subarray(start, offset)); ended = true; break;
    }
    if (marker === undefined || marker === 0 || marker === 0xd8 || marker === 1 || (marker >= 0xd0 && marker <= 0xd7) || offset + 2 > bytes.length) throw new HttpError(422, 'JPEG 标记无效');
    const length = (bytes[offset] << 8) | bytes[offset + 1], end = offset + length;
    if (length < 2 || end > bytes.length) throw new HttpError(422, 'JPEG 图像截断');
    if ([0xc0, 0xc1, 0xc2].includes(marker)) {
      if (length < 8 || bytes[offset + 2] !== 8) throw new HttpError(422, 'JPEG 图像编码不支持');
      height = (bytes[offset + 3] << 8) | bytes[offset + 4];
      width = (bytes[offset + 5] << 8) | bytes[offset + 6];
      const components = bytes[offset + 7];
      if (!width || !height || width * height > 40000000 || ![1, 3].includes(components) || length !== 8 + 3 * components) throw new HttpError(422, '仅接受40MP以内的有效灰度或RGB JPEG图片');
    } else if (marker >= 0xc0 && marker <= 0xcf && ![0xc4, 0xc8, 0xcc].includes(marker)) throw new HttpError(422, 'JPEG 图像编码不支持');
    if (![0xe1, 0xed, 0xfe].includes(marker)) parts.push(bytes.subarray(start, end));
    offset = end;
    if (marker === 0xda) {
      if (!width || !height || length < 6) throw new HttpError(422, 'JPEG 缺少有效尺寸信息');
      scan = true;
      const scanStart = offset;
      while (offset < bytes.length) {
        if (bytes[offset] !== 0xff) { offset += 1; continue; }
        const following = bytes[offset + 1];
        if (following === 0 || (following >= 0xd0 && following <= 0xd7)) { offset += 2; continue; }
        if (following === 0xff) { offset += 1; continue; }
        break;
      }
      if (offset === scanStart) throw new HttpError(422, 'JPEG 缺少图像内容');
      parts.push(bytes.subarray(scanStart, offset));
    }
  }
  if (!ended) throw new HttpError(422, 'JPEG 缺少结束标记');
  const content = new Uint8Array(parts.reduce((size, part) => size + part.length, 0));
  let position = 0;
  for (const part of parts) { content.set(part, position); position += part.length; }
  return {bytes: content, width, height, contentType: 'image/jpeg'};
}

function reportData(row) {
  const snapshot = JSON.parse(row.snapshot);
  return {id: row.id, project_id: row.project_id, mode: row.mode, created_at: row.created_at,
    docx_url: `/api/reports/${row.id}/docx`, pdf_url: `/api/reports/${row.id}/pdf`, snapshot_url: `/api/reports/${row.id}/snapshot`,
    pdf_engine: row.pdf_engine, excluded_count: snapshot.excluded_count || 0, finding_count: snapshot.findings.length};
}

export async function handleApi(request, env, options = {}) {
  const url = new URL(request.url);
  if (url.pathname !== '/api' && !url.pathname.startsWith('/api/')) return null;
  try {
    // Only the Worker entrypoint may inject identity after Sites admission.
    // A client-supplied oai-authenticated-user-id header is never read here.
    const identity = normalizedIdentity(options.identity);
    const origin = request.headers.get('origin');
    if ((origin && origin !== url.origin) || (request.headers.get('sec-fetch-site') === 'cross-site' && !['GET', 'HEAD'].includes(request.method))) throw new HttpError(403, '仅接受工作台本身发起的请求');
    const store = createStore(env, identity), knowledge = options.knowledge;
    const method = request.method === 'HEAD' ? 'GET' : request.method;
    let segments;
    try { segments = url.pathname.split('/').filter(Boolean).map(decodeURIComponent); }
    catch { throw new HttpError(404, '接口不存在'); }
    const [, resource, id, action, childId] = segments;
    const callKnowledge = async (operation, data = {}) => {
      if (!knowledge?.call) throw new HttpError(503, '正式知识包尚未就绪');
      try { return await knowledge.call(operation, data); }
      catch (error) { if (error instanceof HttpError) throw error; throw new HttpError(503, operation === 'detail' ? '该条目暂不能在当前正式知识包中核对' : '正式知识包读取失败，请稍后重试'); }
    };
    async function referenceIssues(finding) {
      const issues = [], details = new Map(), inspected = finding._project.inspection_date;
      for (const basis of finding.bases || []) {
        const effective = String(basis.effective_date || '').slice(0, 10), asOf = String(basis.as_of || '').slice(0, 10);
        if (!validDate(effective)) issues.push(`${basis.law_version_id} 缺少施行日期快照，请重新选入正式依据`);
        else if (inspected < effective) issues.push(`${basis.law_version_id} 于 ${effective} 施行，晚于本次检查日期 ${inspected}`);
        if (!validDate(asOf) || inspected > asOf) issues.push(`检查日期 ${inspected} 晚于或无法核对引用快照 ${asOf}，请更新知识包并重新选择依据`);
        try {
          if (!details.has(basis.hazard_id)) details.set(basis.hazard_id, callKnowledge('detail', {hazard_id: basis.hazard_id}));
          const detail = await details.get(basis.hazard_id);
          const item = detail.bases.find(candidate => candidate.ref.linkId === basis.link_id);
          const profileId = basis.profile?.id;
          const profile = profileId ? (detail.profiles || []).find(candidate => candidate.id === profileId) : null;
          if (!item || (profileId && !profile) || await sourceFingerprint(detail, item, profile) !== basis.source_fingerprint) issues.push(`${basis.link_id} 的依据或适用条件已变化，请按检查日期重新检索、选择并核实；历史报告保持原样`);
        } catch { issues.push(`${basis.hazard_id} 暂不能在当前正式包中核对，请按检查日期更新依据后审核`); }
      }
      return [...new Set(issues)];
    }
    async function complete(finding) { finding.blockers = [...blockers(finding), ...await referenceIssues(finding)]; return finding; }
    const finding = async fid => complete(await store.loadFinding(fid));
    async function selectBasis(fid, payload) {
      shape(payload, ['hazard_id', 'link_ids', 'profile_id']);
      const hazardId = cleanText(payload.hazard_id, 200);
      if (!hazardId) throw new HttpError(422, '请选择正式知识条目');
      const detail = await callKnowledge('detail', {hazard_id: hazardId});
      const available = new Map(detail.bases.map(item => [item.ref.linkId, item]));
      const selected = payload.link_ids ?? [...available.keys()];
      if (!Array.isArray(selected) || !selected.length || selected.length > 100 || selected.some(link => typeof link !== 'string' || !available.has(link))) throw new HttpError(422, '必须选择该正式条目的有效引用');
      let profile = null;
      if (payload.profile_id) {
        profile = (detail.profiles || []).find(item => item.id === payload.profile_id);
        if (!profile || !(profile.basisLinkIds || []).every(link => selected.includes(link))) throw new HttpError(422, '场景与所选条款不一致，请保留场景所需的全部引用');
      }
      const item = await store.loadFinding(fid);
      item.bases = item.bases.filter(basis => basis.hazard_id !== hazardId);
      for (const link of new Set(selected)) {
        const basis = available.get(link), {clause, law, ref} = basis, profiles = detail.profiles || [];
        item.bases.push({id: uid('B'), hazard_id: hazardId, hazard_title: detail.hazard.title,
          link_id: link, clause_id: clause.id, law_version_id: law.id, law_name: law.name,
          document_number: law.documentNumber || '', article: clause.article, text: clause.quote,
          source_url: basis.sourceUrl || clause.sourceUrl || law.sourceUrl || '', role: ref.role || '',
          applicability: ref.applicability || '', hazard_conditions: detail.hazard.conditions || '', scope: law.scope || '',
          jurisdiction_code: ref.jurisdictionCode || '', as_of: detail.meta.as_of, data_version: detail.meta.data_version,
          effective_date: law.effectiveDate || '', source_fingerprint: await sourceFingerprint(detail, basis, profile),
          release_hash: detail.meta.release_hash, queried_at: now(), profile: clone(profile),
          inspection_class: profile?.inspectionClass || (profiles.length && profiles.every(value => value.inspectionClass === 'document_review') ? 'document_review' : ''),
          hazard_inspection_classes: [...new Set(profiles.map(value => value.inspectionClass))].sort()});
      }
      rebuildFacts(item, true); invalidate(item);
      return complete(await store.mutateFinding(item, 'basis_selected'));
    }
    async function persistPhoto(fid, raw, filename, caption) {
      if (!env.BUCKET?.put) throw new HttpError(503, '私有照片存储尚未绑定');
      const sanitized = sanitizeJpeg(raw), item = await store.loadFinding(fid), photoId = uid('IMG');
      const objectKey = `photos/${photoId}.jpg`, stamp = now(), hash = await sha256(sanitized.bytes);
      filename = cleanText(String(filename || 'photo.jpg').split(/[\\/]/).pop().slice(0, 200), 200) || 'photo.jpg';
      caption = cleanText(caption, 1000);
      await env.BUCKET.put(objectKey, sanitized.bytes, {httpMetadata: {contentType: 'image/jpeg'}, customMetadata: {sha256: hash}});
      invalidate(item, true);
      try {
        return complete(await store.mutateFinding(item, 'photo_added', ({guard, parameters, prepare}) => [
          prepare(`INSERT INTO photos(id,finding_id,filename,object_key,mime_type,width,height,caption,position,sha256,created_at)
            SELECT ?,?,?,?,?,?,?,?,(SELECT COALESCE(MAX(position),0)+1 FROM photos WHERE finding_id=?),?,? WHERE ${guard}`,
            [photoId, fid, filename, objectKey, 'image/jpeg', sanitized.width, sanitized.height, caption, fid, hash, stamp, ...parameters]),
        ]));
      } catch (error) {
        // A failed read after a successful D1 batch is not a failed commit.
        // Only a definitive CAS rejection proves that no row references this
        // new object. Keep bytes when the commit outcome is uncertain.
        if (error instanceof HttpError && error.status === 409) await Promise.allSettled([env.BUCKET.delete(objectKey)]);
        throw error;
      }
    }
    async function createReport(projectId, payload) {
      shape(payload, ['mode']);
      const mode = payload.mode || 'confirmed';
      if (!['confirmed', 'draft'].includes(mode)) throw new HttpError(422, '报告类型无效');
      const loaded = await store.loadProjectSnapshot(projectId);
      const all = await Promise.all(loaded.findings.map(complete));
      const selected = all.filter(item => mode === 'draft' || item.status === 'confirmed');
      if (!selected.length) throw new HttpError(409, '没有可导出的记录；请完成审核或选择草稿报告');
      if (mode === 'confirmed') {
        const invalid = selected.flatMap(item => item.blockers);
        if (invalid.length) throw new HttpError(409, {message: '正式报告中的记录需要重新核实依据或事实；历史报告仍可下载', blockers: invalid});
      }
      const render = typeof options.reporting === 'function' ? options.reporting : options.reporting?.renderReport;
      if (!render || !env.BUCKET?.put) throw new HttpError(503, '报告生成服务尚未就绪');
      const reportId = uid('REP');
      const snapshot = {schema_version: 1, id: reportId, created_at: now(), mode, project: loaded.project,
        findings: clone(selected), excluded_count: all.length - selected.length, knowledge: await callKnowledge('meta'),
        template_version: 'inspection-cloud-v1', generated_by: {id: identity.id, source: identity.source}};
      let generated;
      try {
        generated = await render(snapshot, {getPhoto: async photo => {
          if (!photo?.object_key?.startsWith('photos/')) return null;
          const object = await env.BUCKET.get(photo.object_key);
          if (!object) return null;
          return {bytes: new Uint8Array(await object.arrayBuffer()), contentType: photo.mime_type || object.httpMetadata?.contentType || 'image/jpeg'};
        }});
      } catch (error) { throw new HttpError(422, `报告未生成：${error.message || '请检查照片和记录内容'}`); }
      if (!generated?.docx || !generated?.pdf) throw new HttpError(503, '报告生成服务未返回完整文件');
      snapshot.template_version = generated.template_version || snapshot.template_version;
      const keys = {docx: `reports/${reportId}/report.docx`, pdf: `reports/${reportId}/report.pdf`, pdf_engine: generated.pdf_engine || 'pdf-lib'};
      let databaseAttempted = false;
      try {
        await env.BUCKET.put(keys.docx, generated.docx, {httpMetadata: {contentType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}});
        await env.BUCKET.put(keys.pdf, generated.pdf, {httpMetadata: {contentType: 'application/pdf'}});
        databaseAttempted = true;
        return reportData(await store.saveReport(snapshot, keys, all));
      } catch (error) {
        // Once D1 was attempted, an exception may be from the final read or an
        // ambiguous transport result after commit. Preserve immutable exports
        // unless the guarded insert definitively rejected the stale snapshot.
        if (!databaseAttempted || (error instanceof HttpError && error.status === 409)) {
          await Promise.allSettled([env.BUCKET.delete(keys.docx), env.BUCKET.delete(keys.pdf)]);
        }
        throw error;
      }
    }

    let response;
    if (resource === 'health' && segments.length === 2 && method === 'GET') response = json({status: 'ok', version: '1.1.0', deployment: 'private-cloud', private_storage: true,
      viewer: {display_name: identity.displayName || '已登录用户', source: identity.source}, knowledge: await callKnowledge('meta')});
    else if (resource === 'knowledge' && method === 'GET') {
      if (id === 'meta' && segments.length === 3) response = json(await callKnowledge('meta'));
      else if (id === 'search' && segments.length === 3) {
        const q = cleanText(url.searchParams.get('q') || '', 1000);
        response = json(await callKnowledge('search', {q, filters: {region: url.searchParams.get('region') || '', category: url.searchParams.get('category') || ''},
          limit: Math.max(1, Math.min(100, Math.trunc(Number(url.searchParams.get('limit')) || 30)))}));
      } else if (id === 'hazards' && action && segments.length === 4) response = json(await callKnowledge('detail', {hazard_id: cleanText(action, 200)}));
    } else if (resource === 'projects' && !id) {
      if (method === 'GET') response = json(await store.listProjects());
      else if (method === 'POST') response = json(await store.createProject(projectData(await payloadOf(request))), 201);
    } else if (resource === 'projects' && id && !action) {
      if (method === 'GET') response = json(await store.getProject(id));
      else if (method === 'PATCH') { const project = await store.getProject(id); response = json(await store.editProject(project, projectData(await payloadOf(request), project))); }
    } else if (resource === 'projects' && action === 'findings' && segments.length === 4) {
      if (method === 'GET') { const loaded = await store.loadProjectSnapshot(id); response = json(await Promise.all(loaded.findings.map(complete))); }
      else if (method === 'POST') response = json(await complete(await store.createFinding(id, findingData(await payloadOf(request)))), 201);
    } else if (resource === 'projects' && action === 'reports' && segments.length === 4) {
      if (method === 'GET') { await store.getProject(id); const result = await store.prepare('SELECT * FROM reports WHERE project_id=? ORDER BY created_at DESC,rowid DESC', [id]).all(); response = json(store.rows(result).map(reportData)); }
      else if (method === 'POST') response = json(await createReport(id, await payloadOf(request)), 201);
    } else if (resource === 'projects' && action === 'photos.csv' && segments.length === 4 && method === 'GET') {
      const loaded = await store.loadProjectSnapshot(id), rows = [['记录ID', '位置', '照片ID', '原文件名', '说明', '顺序', 'SHA256']];
      for (const item of loaded.findings) for (const photo of item.photos) rows.push([item.id, item.location, photo.id, photo.filename, photo.caption, photo.position, photo.sha256]);
      const csv = rows.map(row => row.map(value => { let text = String(value); if (/^[=+@\-\t\r]/.test(text)) text = "'" + text; return `"${text.replaceAll('"', '""')}"`; }).join(',')).join('\r\n');
      response = binary('\ufeff' + csv, 'text/csv; charset=utf-8', 'photo-inventory.csv');
    } else if (resource === 'findings' && id && !action) {
      if (method === 'GET') response = json(await finding(id));
      else if (method === 'PATCH') {
        const payload = await payloadOf(request); shape(payload, [...FINDING_FIELDS, 'position', 'revision'], '状态、法源和事实只能通过对应操作修改');
        const item = await store.loadFinding(id);
        if ('revision' in payload && payload.revision !== item.revision) throw new HttpError(409, '记录已在其他页面修改，请重新打开后保存');
        let changed = false, substantive = false;
        for (const [key, raw] of Object.entries(payload)) {
          if (key === 'revision') continue;
          const value = key === 'position' ? positionValue(raw) : cleanText(raw, TEXT_LIMITS[key]);
          if (key === 'finding_kind' && !['onsite', 'document_review'].includes(value)) throw new HttpError(422, '记录类型无效');
          if (key === 'due_date' && value && !validDate(value)) throw new HttpError(422, '整改日期无效');
          if (item[key] !== value) { item[key] = value; changed = true; substantive ||= key !== 'position'; }
        }
        if (substantive) invalidate(item, true);
        response = json(await complete(changed ? await store.mutateFinding(item, 'finding_updated') : item));
      } else if (method === 'DELETE') response = json(await store.deleteFinding(await store.loadFinding(id)));
    } else if (resource === 'findings' && action === 'copy' && segments.length === 4 && method === 'POST') {
      const item = await store.loadFinding(id), body = clone(findingBody(item));
      body.status = 'draft'; body.observation = ''; invalidate(body, true);
      response = json(await complete(await store.createFinding(item.project_id, body, 'finding_copied', {from: item.id})), 201);
    } else if (resource === 'findings' && action === 'bases') {
      if (segments.length === 4 && method === 'POST') response = json(await selectBasis(id, await payloadOf(request)));
      else if (childId && segments.length === 5 && method === 'DELETE') {
        const item = await store.loadFinding(id), target = item.bases.find(basis => basis.id === childId);
        if (!target) throw new HttpError(404, '引用不存在');
        item.bases = item.bases.filter(basis => basis.id !== childId);
        for (const basis of item.bases) if (basis.profile?.basisLinkIds?.includes(target.link_id)) {
          basis.profile = null; basis.inspection_class = JSON.stringify(basis.hazard_inspection_classes) === '["document_review"]' ? 'document_review' : '';
        }
        rebuildFacts(item, true); invalidate(item);
        response = json(await complete(await store.mutateFinding(item, 'basis_removed')));
      }
    } else if (resource === 'findings' && action === 'facts' && segments.length === 4 && method === 'PUT') {
      const payload = await payloadOf(request); shape(payload, ['revision', 'facts']);
      if (!Array.isArray(payload.facts)) throw new HttpError(422, 'facts 必须是列表');
      const item = await store.loadFinding(id);
      if (payload.revision !== item.revision) throw new HttpError(409, '记录版本已变化或缺少版本号，请重新打开后核实；旧事实未覆盖新记录');
      const mapped = new Map(item.facts.map(fact => [fact.key, fact]));
      for (const update of payload.facts) {
        if (!isObject(update) || !mapped.has(update.key) || !['unknown', 'confirmed', 'denied'].includes(update.status)) throw new HttpError(422, '事实条目或状态无效');
        Object.assign(mapped.get(update.key), {status: update.status, note: cleanText(update.note || '', 4000)});
      }
      invalidate(item); response = json(await complete(await store.mutateFinding(item, 'facts_updated')));
    } else if (resource === 'findings' && action === 'review' && segments.length === 4 && method === 'POST') {
      const payload = await payloadOf(request); shape(payload, ['revision', 'decision', 'reviewer', 'comment']);
      if (!['submit', 'confirm', 'reject', 'reopen'].includes(payload.decision)) throw new HttpError(422, '审核动作无效');
      const item = await finding(id);
      if (payload.revision !== item.revision) throw new HttpError(409, '审核记录版本已变化或缺少版本号，请重新打开后审核');
      const reviewer = cleanText(payload.reviewer || '', 200), comment = cleanText(payload.comment || '', 4000);
      if (['confirm', 'reject'].includes(payload.decision) && (!reviewer || !comment)) throw new HttpError(422, '请填写审核人和审核意见');
      if (payload.decision === 'submit') item.status = item.blockers.length ? 'needs_facts' : 'pending_review';
      else if (payload.decision === 'confirm') {
        if (item.status !== 'pending_review' || item.blockers.length) throw new HttpError(409, {message: '请先完成事实核实并提交专业审核', blockers: item.blockers});
        item.status = 'confirmed';
      } else item.status = payload.decision === 'reject' ? 'rejected' : 'draft';
      response = json(await complete(await store.mutateFinding(item, `review_${payload.decision}`, ({guard, parameters, stamp, prepare}) => [
        prepare(`INSERT INTO reviews(id,finding_id,decision,reviewer,comment,revision,actor_id,actor_source,created_at)
          SELECT ?,?,?,?,?,?,?,?,? WHERE ${guard}`, [uid('R'), id, payload.decision, reviewer || identity.displayName,
          comment, item.revision + 1, identity.id, identity.source, stamp, ...parameters]),
      ])));
    } else if (resource === 'findings' && action === 'photos') {
      if (segments.length === 4 && method === 'POST') {
        const contentType = request.headers.get('content-type') || '';
        if (!contentType.startsWith('multipart/form-data')) throw new HttpError(422, '请使用图片上传表单');
        const bytes = await limitedBody(request, MAX_PHOTO + 1024 * 1024);
        let form;
        try { form = await new Response(bytes, {headers: {'Content-Type': contentType}}).formData(); }
        catch { throw new HttpError(422, '照片上传表单无法读取'); }
        const file = form.get('file');
        if (!file || typeof file.arrayBuffer !== 'function') throw new HttpError(422, '请选择 JPEG 照片');
        response = json(await persistPhoto(id, new Uint8Array(await file.arrayBuffer()), file.name, form.get('caption') || ''));
      } else if (childId && segments.length === 5 && ['PATCH', 'DELETE'].includes(method)) {
        const item = await store.loadFinding(id), photo = item.photos.find(value => value.id === childId);
        if (!photo) throw new HttpError(404, '照片不存在');
        const payload = method === 'PATCH' ? await payloadOf(request) : {};
        shape(payload, ['caption', 'position'], '照片字段无效');
        const caption = cleanText(payload.caption ?? photo.caption, 1000), position = positionValue(payload.position ?? photo.position);
        invalidate(item, true);
        response = json(await complete(await store.mutateFinding(item, method === 'PATCH' ? 'photo_updated' : 'photo_removed', ({guard, parameters, prepare}) => [
          method === 'PATCH' ? prepare(`UPDATE photos SET caption=?,position=? WHERE id=? AND finding_id=? AND ${guard}`, [caption, position, childId, id, ...parameters])
            : prepare(`DELETE FROM photos WHERE id=? AND finding_id=? AND ${guard}`, [childId, id, ...parameters]),
        ])));
        // R2 bytes remain immutable for earlier report snapshots and backups.
      }
    } else if (resource === 'findings' && action === 'audit' && segments.length === 4 && method === 'GET') {
      await store.loadFinding(id);
      const result = await store.prepare('SELECT * FROM audit WHERE entity_id=? ORDER BY created_at,rowid', [id]).all();
      response = json(store.rows(result).map(row => ({...row, detail: JSON.parse(row.detail)})));
    } else if (resource === 'photos' && id && segments.length === 3 && method === 'GET') {
      const photo = await store.prepare('SELECT * FROM photos WHERE id=?', [id]).first();
      if (!photo) throw new HttpError(404, '照片不存在');
      const object = await env.BUCKET.get(photo.object_key);
      if (!object) throw new HttpError(404, '照片文件不存在');
      response = binary(object.body || await object.arrayBuffer(), 'image/jpeg');
    } else if (resource === 'reports' && id && segments.length === 4 && method === 'GET') {
      if (!['docx', 'pdf', 'snapshot'].includes(action)) throw new HttpError(404, '报告格式不存在');
      const report = await store.prepare('SELECT * FROM reports WHERE id=?', [id]).first();
      if (!report) throw new HttpError(404, '报告不存在');
      if (action === 'snapshot') response = binary(report.snapshot, 'application/json; charset=utf-8', 'report-snapshot.json');
      else {
        const object = await env.BUCKET.get(report[`${action}_key`]);
        if (!object) throw new HttpError(404, '报告文件不存在');
        response = binary(object.body || await object.arrayBuffer(), action === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', `inspection-${id.slice(-8)}.${action}`);
      }
    } else if (resource === 'backup' && segments.length === 2 && method === 'GET') {
      const names = ['projects', 'findings', 'photos', 'reviews', 'reports', 'audit'];
      const results = await store.batch(names.map(name => store.prepare(`SELECT * FROM ${name}`)));
      const tables = Object.fromEntries(names.map((name, index) => [name, store.rows(results[index])]));
      const exported = {schema_version: 'safety-basis-cloud-backup-v1', exported_at: now(), knowledge: await callKnowledge('meta'), tables};
      const files = {'workspace.json': strToU8(JSON.stringify(exported, null, 2)), 'README.txt': strToU8('私有工作台备份，包含企业记录、照片、审核、报告和审计。请保存在受控位置。workspace.json为结构化D1数据，files/为原始私有对象。')};
      const keys = new Set(tables.photos.map(photo => photo.object_key));
      for (const report of tables.reports) {
        keys.add(report.docx_key); keys.add(report.pdf_key);
        for (const record of JSON.parse(report.snapshot).findings || []) for (const photo of record.photos || []) if (photo.object_key) keys.add(photo.object_key);
      }
      let size = Object.values(files).reduce((total, bytes) => total + bytes.length, 0);
      for (const key of keys) {
        if (!/^(?:photos|reports)\/[A-Za-z0-9_./-]+$/.test(key) || key.includes('..')) throw new HttpError(503, '备份对象路径无效');
        const object = await env.BUCKET.get(key);
        if (!object) throw new HttpError(409, '备份所需的照片或报告文件缺失，请先核对工作区数据');
        if (size + (object.size || 0) > 32 * 1024 * 1024) throw new HttpError(413, '在线完整备份超过32MB，请联系工作区维护人员从私有存储导出；现有数据未改变');
        const bytes = new Uint8Array(await object.arrayBuffer()); size += bytes.length;
        if (size > 32 * 1024 * 1024) throw new HttpError(413, '在线完整备份超过32MB，请从私有存储导出');
        files[`files/${key}`] = bytes;
      }
      response = binary(zipSync(files, {level: 0}), 'application/zip', `safety-basis-private-backup-${now().slice(0, 10)}.zip`);
    } else if (resource === 'demo' && segments.length === 2 && method === 'POST') {
      const meta = await callKnowledge('meta');
      const project = await store.createProject(projectData({company: '示例制造企业（脱敏演示）', name: '综合安全检查示例',
        inspection_date: String(meta.as_of).slice(0, 10), inspectors: '示例检查人', purpose: '合成样例，仅演示工作流程'}));
      const record = await store.createFinding(project.id, findingData({location: '示例车间东侧灭火器点位', equipment: '储压式灭火器',
        observation: '演示观察：压力指示器指针位于欠压区域。此处为合成样例，不代表真实企业情况。',
        description: '示例记录：储压式灭火器压力指示器指针位于欠压区域，实际状态和适用条件仍须核实。',
        rectification: '核实器材状态和适用要求后，以符合要求的器材替换，并完善巡查和更换记录。'}));
      await selectBasis(record.id, {hazard_id: 'H001'});
      const bytes = Uint8Array.from(atob(DEMO_PHOTO_BASE64), character => character.charCodeAt(0));
      const final = await persistPhoto(record.id, bytes, 'synthetic-demo.jpg', '完全合成的演示图片，不是现场证据');
      response = json({project: await store.getProject(project.id), finding: final}, 201);
    } else if (resource === 'docs' && segments.length === 2 && method === 'GET') {
      response = binary('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>私有工作台 API</title><h1>私有工作台 API</h1><p>所有接口均需经私有站点身份校验。企业数据保存在私有 D1 / R2，不进入公开知识库。</p><ul><li>/api/projects：项目及记录</li><li>/api/findings/{id}：记录、照片、依据、事实和审核</li><li>/api/knowledge/search：现有正式知识库检索</li><li>/api/projects/{id}/reports：生成及查看报告历史</li><li>/api/backup：私有完整备份下载</li></ul><p>事实和审核必须携带当前 revision；候选条款不自动确认现场事实。</p><a href="/">返回工作台</a></html>', 'text/html; charset=utf-8');
    }
    if (!response) throw new HttpError(404, '接口不存在或请求方法不支持');
    return request.method === 'HEAD' ? new Response(null, {status: response.status, headers: response.headers}) : response;
  } catch (error) {
    if (error instanceof HttpError) return json({detail: error.detail}, error.status);
    if (options.onError) options.onError(error);
    else console.error('workbench_api_failed', {name: error?.name});
    return json({detail: '私有工作台请求未能完整完成，请重新打开并核对当前状态后重试。'}, 503);
  }
}

const FACT_LABELS = {
  "applicableRequirementConfirmed": "核实本次适用要求、地域、主体和例外",
  "siteTriggerConfirmed": "核实本场景的现场触发条件",
  "defectObserved": "通过本次观察或测量核实所述具体缺陷",
  "actualDrillDatesConfirmed": "核实实际演练日期",
  "actualResidentialUseVerifiedIfAsserted": "如主张居住用途，核实实际居住使用情况",
  "branchAActualUnlicensedFillingConfirmedIfSelected": "如选用分支A，核实实际无许可充装事实",
  "branchBWrongMediumConfirmedIfSelected": "如选用分支B，核实错误介质充装事实",
  "branchCEmergencyCutoffDefectAndContinuedUseConfirmedIfSelected": "如选用分支C，核实紧急切断缺陷及继续使用事实",
  "branchSpecificEvidenceIdentified": "明确本次所选分支的对应证据",
  "combustibleDustExplosionScopeConfirmed": "核实属于可燃性粉尘爆炸危险适用范围",
  "conductiveDustCollectionPartConfirmed": "核实涉及导电性粉尘收集部位",
  "continuedUseAfterAdverseConclusionConfirmed": "核实不利检验结论后仍继续使用的事实",
  "criterionBranchSelectedAndFactsConfirmed": "明确所选判定分支并核实该分支事实",
  "determinationActorAndAuthorityScopeConfirmed": "核实判定主体及其权限范围",
  "determinationActorAndHandlingStatusConfirmed": "核实判定主体及处置状态",
  "dustTypeBranchConfirmed": "核实粉尘类型及对应分支",
  "electricalEquipmentAndWiringIdentified": "明确涉及的电气设备与线路",
  "entryScenarioAndPreventionArrangementsConfirmed": "核实进入场景及预防措施安排",
  "equipmentAndUseScopeConfirmed": "核实设备类别与使用范围",
  "equipmentFillingActivityAndExclusionsConfirmed": "核实设备、充装活动及排除情形",
  "equipotentialAndGroundingConditionObserved": "核实等电位连接与接地的实际状态",
  "evacuationDrillArrangementsAndExecutionConfirmed": "核实疏散演练安排及实际执行",
  "exclusionStatusConfirmed": "核实排除情形是否存在",
  "existingMajorHazardDeterminationAndTreatmentStatusConfirmed": "核实既有重大隐患判定及处置状态",
  "firefightingAndEvacuationContentConfirmed": "核实灭火与疏散演练内容",
  "flangeJumperConditionObservedIfApplicable": "如适用，核实法兰跨接的实际状态",
  "groundResistanceMeasurementValidatedIfAsserted": "如引用接地电阻数值，核实测量结果与适用性",
  "halfYearReviewWindowConfirmed": "核实本次半年核查时间窗口",
  "ignitionSourceMeasuresConfirmed": "核实点火源防范措施",
  "ignitionSourceProtectionAssessed": "评估点火源防护情况",
  "industryAndDustExplosionScopeConfirmed": "核实行业及粉尘爆炸危险适用范围",
  "inspectionConclusionExactlyNotMeetingRequirementsConfirmed": "核实检验结论原文确为“不符合要求”",
  "inspectionConclusionExactlyUnqualifiedConfirmed": "核实检验结论原文确为“不合格”",
  "inspectionReportAuthenticityAndDeviceMatchConfirmed": "核实检验报告真实性及对应设备",
  "installedMaterialFirePerformanceVerifiedIfAsserted": "如引用材料防火性能，核实已安装材料的性能证据",
  "jiangsuEducationalInstitutionConfirmed": "核实江苏地域及学校或其他教育机构主体",
  "jiangsuKeyFireSafetyUnitConfirmed": "核实江苏地域及消防安全重点单位身份",
  "jiangsuResidentialContextConfirmed": "核实江苏地域及住宅场景",
  "jiangsuUrbanRailScopeVerified": "核实江苏城市轨道交通适用范围",
  "latestInspectionAndRectificationTimelineConfirmed": "核实最近检验与整改时间线",
  "occupationalHazardEmployerAndWorkplaceScopeVerified": "核实职业病危害用人单位及工作场所适用范围",
  "operationalOrAdvertisingFacilityIdentityVerifiedIfAsserted": "如选用该情形，核实设施的经营或广告用途",
  "ownerOrUserRoleConfirmed": "核实所有人或使用人的主体身份",
  "prohibitedZoneAndActualShopUseVerifiedIfAsserted": "如选用该情形，核实禁止区域及实际商铺用途",
  "relevantEnclosureDustIngressProtectionAssessed": "评估相关外壳防粉尘进入的保护情况",
  "requiredOutputConfirmed": "核实本项要求形成的记录或成果",
  "selectedBranchRecorded": "记录本次选用的具体分支",
  "sludgeRemovalBranchAssessed": "评估清理泥浆分支是否适用及其实际措施",
  "systemPressureModeConfirmed": "核实系统压力运行方式",
  "testScopeConfirmed": "核实本次检测范围",
  "ventilationWhileRunningAssessed": "评估运行期间的通风措施",
  "ventilationWhileStoppedAssessed": "评估停运期间的通风措施",
  "visitArrangementsAndExecutionConfirmed": "核实参观活动安排及实际执行",
  "wetDustCollectorAndObjectsConfirmed": "核实湿式除尘器及其处理对象",
  "workAndLivingLayoutAndSeparationVerifiedIfAsserted": "如选用该情形，核实生产与居住布局及分隔情况"
};
const DEMO_PHOTO_BASE64 = "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";
