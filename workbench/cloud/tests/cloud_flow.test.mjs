/**
 * Real cloud API / SQL business regressions, with no remote service or user data.
 *
 * D1 is backed by node:sqlite, including atomic batch and compare-and-swap writes.
 * R2 is an in-memory object store. Knowledge comes from the hash-verified public
 * bundle, not hand-authored legal fixtures. The report renderer is an explicitly
 * labelled test double for business cases. A separate integration case invokes the
 * real renderer and parses its Word/PDF outputs; visual layout is checked separately.
 *
 * Run on Node >= 22.13 after building source/releases/current:
 *   node --test workbench/cloud/tests/cloud_flow.test.mjs
 */
import assert from 'node:assert/strict';
import {before, test} from 'node:test';
import {readFileSync, readdirSync} from 'node:fs';
import {resolve, sep} from 'node:path';
import {fileURLToPath} from 'node:url';

import {createKnowledge} from '../knowledge.mjs';
import {MemoryD1, MemoryR2} from './memory-bindings.mjs';

const ROOT = fileURLToPath(new URL('../../../', import.meta.url));
const BUNDLE = resolve(process.env.WORKBENCH_BUNDLE || resolve(ROOT, 'source/releases/current'));
const ORIGIN = 'https://private-workbench.test';
const OWNER = {id: 'synthetic-owner', source: 'chatgpt', displayName: '合成浏览器身份'};
const SERVICE = {id: 'site-owner-service', source: 'site-owner-service'};
const JPEG = Buffer.from('/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAAIAAgDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDmKKKK8c/Uz//Z', 'base64');


let handleApi;
let governed;

async function verifiedKnowledge() {
  const assets = {async fetch(request) {
    const url = new URL(request.url);
    assert.equal(url.origin, 'https://workbench-assets.invalid', 'tests must never fetch a remote legal source');
    assert.ok(url.pathname.startsWith('/knowledge/'));
    const target = resolve(BUNDLE, decodeURIComponent(url.pathname.slice('/knowledge/'.length)));
    assert.ok(target.startsWith(BUNDLE + sep), 'public bundle path must remain inside the bundle');
    try { return new Response(readFileSync(target), {headers: {'Content-Type': 'application/json'}}); }
    catch (error) { if (error.code === 'ENOENT') return new Response('', {status: 404}); throw error; }
  }};
  const bridge = createKnowledge(assets);
  const meta = await bridge.call('meta');
  assert.ok(meta.release_hash, 'build and verify the real public bundle before cloud tests');
  const profiles = JSON.parse(readFileSync(resolve(BUNDLE, 'data/field-profiles.json'), 'utf8')).records;
  const ids = new Set(['H001', 'H003', 'H_JSXF_58_1', 'H_89016FC0F3E849C2B8B8755C35',
    ...profiles.map(profile => profile.hazardId)]);
  const details = new Map();
  for (const id of ids) details.set(id, await bridge.call('detail', {hazard_id: id}));
  return {meta, details, call: (...args) => bridge.call(...args)};
}

before(async () => {
  ({handleApi} = await import('../api.mjs'));
  governed = await verifiedKnowledge();
});

function harness(t, identity = OWNER) {
  const DB = new MemoryD1();
  const migrations = new URL('../migrations/', import.meta.url);
  for (const name of readdirSync(migrations).filter(name => name.endsWith('.sql')).sort()) {
    DB.connection.exec(readFileSync(new URL(name, migrations), 'utf8'));
  }
  t.after(() => DB.close());
  const BUCKET = new MemoryR2();
  const knowledge = {
    meta: structuredClone(governed.meta), details: structuredClone(governed.details),
    async call(op, args = {}) {
      if (op === 'meta') return structuredClone(this.meta);
      if (op === 'detail') {
        const detail = this.details.get(args.hazard_id);
        if (!detail) throw new Error('该条目不在当前正式发布包中');
        return structuredClone({...detail, meta: this.meta});
      }
      if (op === 'search') return governed.call(op, args);
      throw new Error(`Unsupported test knowledge operation: ${op}`);
    },
  };
  const rendered = [];
  const reporting = {async renderReport(snapshot, {getPhoto}) {
    rendered.push(structuredClone(snapshot));
    // Check that the API supplies the exact snapshot's private image bytes.
    for (const finding of snapshot.findings) for (const photo of finding.photos) {
      const image = await getPhoto(photo);
      assert.ok(image, 'report image access must resolve the snapshot photo');
    }
    return {docx: new TextEncoder().encode('DOCX-CLOUD-FLOW-TEST\n' + JSON.stringify(snapshot)),
      pdf: new TextEncoder().encode('%PDF-CLOUD-FLOW-TEST\n' + JSON.stringify(snapshot)),
      pdf_engine: 'explicit API test double; no layout validation', template_version: 'cloud-flow-test-v1'};
  }};
  const context = {env: {DB, BUCKET}, knowledge, reporting, rendered, identity};
  context.request = async (method, path, body, options = {}) => {
    const headers = new Headers(options.headers);
    const init = {method, headers};
    if (body !== undefined) {
      if (body instanceof FormData) init.body = body;
      else { headers.set('Content-Type', 'application/json'); init.body = JSON.stringify(body); }
    }
    const request = new Request(ORIGIN + path, init);
    const chosenIdentity = Object.hasOwn(options, 'identity') ? options.identity : context.identity;
    return handleApi(request, context.env, {knowledge, reporting, identity: chosenIdentity});
  };
  context.json = async (method, path, body, expected = 200, options) => {
    const response = await context.request(method, path, body, options);
    assert.ok(response instanceof Response, `${method} ${path} must return Response`);
    const text = await response.text();
    assert.equal(response.status, expected, `${method} ${path}: ${text.slice(0, 1600)}`);
    return text ? JSON.parse(text) : null;
  };
  return context;
}

async function createFinding(h, {hazard = 'H001', date = governed.meta.as_of, basis = {}, kind = 'onsite'} = {}) {
  const project = await h.json('POST', '/api/projects', {company: '完全合成的测试企业', name: '云端回归样例',
    inspection_date: date, inspectors: '合成检查人', purpose: '纯合成测试，不代表真实企业情况'}, 201);
  let finding = await h.json('POST', `/api/projects/${project.id}/findings`, {location: '合成车间点位',
    equipment: '合成设备', observation: '合成观察记录，须逐项核实', description: '合成专业描述',
    rectification: '合成整改建议', finding_kind: kind}, 201);
  if (hazard) finding = await h.json('POST', `/api/findings/${finding.id}/bases`, {hazard_id: hazard, ...basis});
  return {project, finding};
}

async function acknowledge(h, finding, {note = '合成测试的逐项核实说明，非真实企业事实', denied = []} = {}) {
  return h.json('PUT', `/api/findings/${finding.id}/facts`, {revision: finding.revision,
    facts: finding.facts.map(fact => ({key: fact.key, status: denied.includes(fact.key) || fact.allows_denied ? 'denied' : 'confirmed', note}))});
}

async function confirm(h, finding) {
  finding = await acknowledge(h, finding);
  assert.deepEqual(finding.blockers, [], 'synthetic acknowledged fixture must satisfy applicable checks');
  finding = await h.json('POST', `/api/findings/${finding.id}/review`, {decision: 'submit', revision: finding.revision});
  assert.equal(finding.status, 'pending_review');
  finding = await h.json('POST', `/api/findings/${finding.id}/review`, {decision: 'confirm', revision: finding.revision,
    reviewer: '合成专业审核人', comment: '仅验证合成业务流程'});
  assert.equal(finding.status, 'confirmed');
  return finding;
}

async function upload(h, finding, {name = 'synthetic.jpg', bytes = JPEG, type = 'image/jpeg', caption = '合成图片'} = {}) {
  const form = new FormData();
  form.append('file', new File([bytes], name, {type}));
  form.append('caption', caption);
  return h.request('POST', `/api/findings/${finding.id}/photos`, form);
}

test('D1 adapter rolls back the entire batch on a SQL constraint failure', async () => {
  const DB = new MemoryD1();
  try {
    await DB.exec('CREATE TABLE example(id TEXT PRIMARY KEY, value INTEGER NOT NULL)');
    await assert.rejects(DB.batch([DB.prepare('INSERT INTO example VALUES (?,?)').bind('same', 1),
      DB.prepare('INSERT INTO example VALUES (?,?)').bind('same', 2)]));
    assert.equal(await DB.prepare('SELECT COUNT(*) AS count FROM example').first('count'), 0);
  } finally { DB.close(); }
});

test('all API requests require trusted identity and ignore forged client identity headers', async t => {
  const h = harness(t);
  for (const [method, path, body] of [['GET', '/api/health'], ['GET', '/api/projects'], ['GET', '/api/knowledge/meta'],
    ['GET', '/api/backup'], ['POST', '/api/projects', {company: '伪造身份请求', name: '不应创建', inspection_date: governed.meta.as_of}]]) {
    const response = await h.request(method, path, body, {identity: undefined,
      headers: {'X-User-Id': 'synthetic-owner', 'X-Auth-Request-User': 'owner', 'Authorization': 'Bearer invented'}});
    assert.equal(response.status, 401, `${method} ${path} must fail closed without platform identity`);
  }
  const empty = await h.request('GET', '/api/projects', undefined, {identity: {}});
  assert.equal(empty.status, 401, 'an empty identity object is not authentication');
  assert.deepEqual(await h.json('GET', '/api/projects'), []);
  assert.equal(h.env.BUCKET.objects.size, 0);
});

test('private JSON is never publicly cached and cross-origin writes are refused', async t => {
  const h = harness(t);
  const response = await h.request('GET', '/api/projects');
  assert.match(response.headers.get('Cache-Control') || '', /no-store/);
  assert.equal(response.headers.get('Referrer-Policy'), 'no-referrer');
  const otherOrigin = await h.request('POST', '/api/projects', {company: '合成', name: '跨站', inspection_date: governed.meta.as_of},
    {headers: {Origin: 'https://other.invalid'}});
  assert.equal(otherOrigin.status, 403);
  assert.deepEqual(await h.json('GET', '/api/projects'), []);
});

test('browser and owner-service actors are retained without impersonating a reviewer', async t => {
  const h = harness(t, SERVICE);
  const {finding} = await createFinding(h);
  const audit = await h.json('GET', `/api/findings/${finding.id}/audit`);
  assert.match(JSON.stringify(audit), /site-owner-service/);
  assert.equal(finding.status, 'draft');
  assert.equal(finding.reviews.length, 0);
});

test('the governed search preserves uncertainty, exact titles and assessment', async t => {
  const h = harness(t);
  const exact = await h.json('GET', '/api/knowledge/search?q=' + encodeURIComponent('灭火器失压'));
  assert.equal(exact.items[0].id, 'H001');
  const uncertain = await h.json('GET', '/api/knowledge/search?q=' + encodeURIComponent('气瓶没有防震圈'));
  assert.deepEqual(uncertain.items, []);
  assert.ok(uncertain.guidance.notice);
  assert.equal(uncertain.assessment.classification, 'evidence_gap');
  assert.equal(uncertain.meta.as_of, governed.meta.as_of);
});

test('selecting a basis leaves every field fact unknown and cannot confirm a finding', async t => {
  const h = harness(t);
  let {finding} = await createFinding(h);
  assert.ok(finding.facts.length);
  assert.ok(finding.facts.every(fact => fact.status === 'unknown'));
  assert.ok(finding.bases.every(basis => basis.effective_date && basis.as_of && basis.text && basis.source_fingerprint));
  await h.json('POST', `/api/findings/${finding.id}/review`, {decision: 'confirm', revision: finding.revision,
    reviewer: '合成审核人', comment: '不能自动确认'}, 409);
  finding = await h.json('POST', `/api/findings/${finding.id}/review`, {decision: 'submit', revision: finding.revision});
  assert.equal(finding.status, 'needs_facts');
  assert.ok(finding.blockers.length);
});

test('clients cannot forge status, legal text, basis identity or fact keys', async t => {
  const h = harness(t);
  const {finding} = await createFinding(h);
  for (const payload of [{status: 'confirmed'}, {bases: [{text: '伪造法条'}]}, {facts: []}]) {
    await h.json('PATCH', `/api/findings/${finding.id}`, {...payload, revision: finding.revision}, 422);
  }
  await h.json('POST', `/api/findings/${finding.id}/bases`, {hazard_id: 'H001', link_ids: ['K_INVENTED']}, 422);
  await h.json('PUT', `/api/findings/${finding.id}/facts`, {revision: finding.revision,
    facts: [{key: 'invented', status: 'confirmed', note: '伪造'}]}, 422);
  const after = await h.json('GET', `/api/findings/${finding.id}`);
  assert.equal(after.revision, finding.revision);
  assert.ok(after.facts.every(fact => fact.status === 'unknown'));
});

test('confirmed facts still need evidence notes and mandatory denied facts stay blocking', async t => {
  const h = harness(t);
  let {finding} = await createFinding(h);
  finding = await acknowledge(h, finding, {note: '  '});
  assert.ok(finding.blockers.length, 'empty evidence notes must block');
  finding = await acknowledge(h, finding, {denied: [finding.facts.find(fact => !fact.allows_denied).key]});
  assert.ok(finding.blockers.length, 'a denied mandatory fact must block');
  finding = await h.json('POST', `/api/findings/${finding.id}/review`, {revision: finding.revision, decision: 'submit'});
  assert.equal(finding.status, 'needs_facts');
});

test('stale or missing revisions cannot restore old facts or approve another revision', async t => {
  const h = harness(t);
  const {finding: old} = await createFinding(h);
  let current = await h.json('PATCH', `/api/findings/${old.id}`, {revision: old.revision, observation: '新的合成观察，尚未核实'});
  const staleFacts = old.facts.map(fact => ({key: fact.key, status: 'confirmed', note: '旧页面的核实说明'}));
  await h.json('PUT', `/api/findings/${old.id}/facts`, {revision: old.revision, facts: staleFacts}, 409);
  await h.json('PUT', `/api/findings/${old.id}/facts`, {facts: staleFacts}, 409);
  current = await h.json('GET', `/api/findings/${old.id}`);
  assert.ok(current.facts.every(fact => fact.status === 'unknown'));
  current = await confirm(h, current);
  await h.json('POST', `/api/findings/${old.id}/review`, {revision: old.revision, decision: 'confirm', reviewer: '旧审核页', comment: '旧意见'}, 409);
  await h.json('POST', `/api/findings/${old.id}/review`, {decision: 'confirm', reviewer: '无版本审核页', comment: '不能通过'}, 409);
  assert.equal((await h.json('GET', `/api/findings/${old.id}`)).revision, current.revision);
});

test('simultaneous edits use SQL compare-and-swap so only one revision wins', async t => {
  const h = harness(t);
  const {finding} = await createFinding(h);
  const responses = await Promise.all(['合成编辑甲', '合成编辑乙'].map(description =>
    h.request('PATCH', `/api/findings/${finding.id}`, {revision: finding.revision, description})));
  assert.deepEqual(responses.map(response => response.status).sort(), [200, 409]);
  const current = await h.json('GET', `/api/findings/${finding.id}`);
  assert.equal(current.revision, finding.revision + 1);
  assert.ok(['合成编辑甲', '合成编辑乙'].includes(current.description));
});

test('supporting-only selection cannot substitute for a direct or fallback basis', async t => {
  const h = harness(t);
  const detail = [...h.knowledge.details.values()].find(value => value.bases.some(item => item.ref.role === 'supporting'));
  assert.ok(detail, 'verified public fixture must include a supporting link');
  const supporting = detail.bases.find(item => item.ref.role === 'supporting');
  let {finding} = await createFinding(h, {hazard: detail.hazard.id, basis: {link_ids: [supporting.ref.linkId]}});
  finding = await acknowledge(h, finding);
  assert.ok(finding.blockers.some(reason => /辅助|直接|兜底/.test(reason)));
  finding = await h.json('POST', `/api/findings/${finding.id}/review`, {decision: 'submit', revision: finding.revision});
  assert.equal(finding.status, 'needs_facts');
  await h.json('POST', `/api/findings/${finding.id}/review`, {decision: 'confirm', revision: finding.revision,
    reviewer: '合成审核人', comment: '辅助条款不能单独认定'}, 409);
});

test('profile selection preserves alternatives and conditional branches can remain unasserted', async t => {
  const h = harness(t);
  let {finding} = await createFinding(h, {hazard: 'H003', basis: {profile_id: 'FPR_EXTINGUISHER_ACCESS_BLOCKED'}});
  assert.ok(finding.facts.some(fact => fact.key.includes('FPR_EXTINGUISHER_ACCESS_BLOCKED')));
  assert.ok(finding.facts.every(fact => !fact.key.includes('FPR_EXTINGUISHER_BRACKET_OBSTRUCTION')));
  const detail = [...h.knowledge.details.values()].find(value => value.profiles.some(profile =>
    profile.applicability.perUseFacts.some(key => /IfSelected$|IfAsserted$|IfApplicable$/.test(key))));
  const profile = detail.profiles.find(value => value.applicability.perUseFacts.some(key => /IfSelected$|IfAsserted$|IfApplicable$/.test(key)));
  ({finding} = await createFinding(h, {hazard: detail.hazard.id, basis: {profile_id: profile.id}}));
  assert.ok(finding.facts.some(fact => fact.allows_denied));
  finding = await acknowledge(h, finding);
  assert.ok(finding.facts.filter(fact => fact.allows_denied).every(fact => fact.status === 'denied' && fact.note));
  assert.deepEqual(finding.blockers, []);
});

test('document duties cannot be confirmed as onsite defects', async t => {
  const h = harness(t);
  let {finding} = await createFinding(h, {hazard: 'H_JSXF_58_1'});
  assert.ok(finding.blockers.some(reason => /资料核查/.test(reason)));
  finding = await h.json('PATCH', `/api/findings/${finding.id}`, {revision: finding.revision, finding_kind: 'document_review'});
  assert.ok(!finding.blockers.some(reason => /请将记录类型/.test(reason)));
});

test('a law not yet effective or a snapshot older than the inspection date blocks approval', async t => {
  const h = harness(t);
  for (const date of ['2020-01-01', new Date(Date.parse(governed.meta.as_of + 'T00:00:00Z') + 86400000).toISOString().slice(0, 10)]) {
    let {finding} = await createFinding(h, {date});
    finding = await acknowledge(h, finding);
    finding = await h.json('POST', `/api/findings/${finding.id}/review`, {decision: 'submit', revision: finding.revision});
    assert.equal(finding.status, 'needs_facts');
    assert.ok(finding.blockers.some(reason => /日期|快照|施行/.test(reason)));
    await h.json('POST', `/api/findings/${finding.id}/review`, {decision: 'confirm', revision: finding.revision,
      reviewer: '合成审核人', comment: '不能跨越法源时间边界'}, 409);
  }
});

test('confirmed export contains only confirmed records; draft export keeps unresolved status', async t => {
  const h = harness(t);
  let {project, finding} = await createFinding(h);
  await h.json('POST', `/api/projects/${project.id}/reports`, {mode: 'confirmed'}, 409);
  const draft = await h.json('POST', `/api/projects/${project.id}/reports`, {mode: 'draft'}, 201);
  assert.equal((await h.json('GET', draft.snapshot_url)).findings[0].status, 'draft');
  finding = await confirm(h, finding);
  const second = await h.json('POST', `/api/projects/${project.id}/findings`, {observation: '仍待核实的第二条合成记录'}, 201);
  const report = await h.json('POST', `/api/projects/${project.id}/reports`, {mode: 'confirmed'}, 201);
  const snapshot = await h.json('GET', report.snapshot_url);
  assert.equal(snapshot.mode, 'confirmed');
  assert.deepEqual(snapshot.findings.map(item => item.id), [finding.id]);
  assert.equal(snapshot.excluded_count, 1);
  assert.ok(!snapshot.findings.some(item => item.id === second.id));
  assert.equal(h.rendered.at(-1).findings[0].status, 'confirmed');
  assert.equal((await h.request('GET', report.docx_url)).status, 200);
  assert.equal((await h.request('GET', report.pdf_url)).status, 200);
});

test('substantive edits and project context changes reset facts without rewriting historical reports', async t => {
  const h = harness(t);
  let {project, finding} = await createFinding(h);
  finding = await confirm(h, finding);
  const report = await h.json('POST', `/api/projects/${project.id}/reports`, {mode: 'confirmed'}, 201);
  const originalSnapshot = await (await h.request('GET', report.snapshot_url)).text();
  const originalWord = await (await h.request('GET', report.docx_url)).arrayBuffer();
  finding = await h.json('PATCH', `/api/findings/${finding.id}`, {revision: finding.revision, description: '修订后的合成描述，需重新核实'});
  assert.equal(finding.status, 'draft');
  assert.ok(finding.facts.every(fact => fact.status === 'unknown' && !fact.note));
  finding = await confirm(h, finding);
  const previousRevision = finding.revision;
  await h.json('PATCH', `/api/projects/${project.id}`, {company: '另一家完全合成的企业', inspection_date: '2020-01-01'});
  finding = await h.json('GET', `/api/findings/${finding.id}`);
  assert.equal(finding.status, 'draft');
  assert.ok(finding.revision > previousRevision);
  assert.ok(finding.facts.every(fact => fact.status === 'unknown' && !fact.note));
  await h.json('POST', `/api/projects/${project.id}/reports`, {mode: 'confirmed'}, 409);
  assert.equal(await (await h.request('GET', report.snapshot_url)).text(), originalSnapshot);
  assert.deepEqual(await (await h.request('GET', report.docx_url)).arrayBuffer(), originalWord);
});

test('current legal changes or withdrawal block new exports while old reports remain downloadable', async t => {
  const h = harness(t);
  let {project, finding} = await createFinding(h);
  finding = await confirm(h, finding);
  const report = await h.json('POST', `/api/projects/${project.id}/reports`, {mode: 'confirmed'}, 201);
  const original = await (await h.request('GET', report.pdf_url)).arrayBuffer();
  h.knowledge.details.get('H001').bases[0].ref.applicability += '（合成：适用条件已变化）';
  await h.json('POST', `/api/projects/${project.id}/reports`, {mode: 'confirmed'}, 409);
  h.knowledge.details.delete('H001');
  await h.json('POST', `/api/projects/${project.id}/reports`, {mode: 'confirmed'}, 409);
  assert.deepEqual(await (await h.request('GET', report.pdf_url)).arrayBuffer(), original);
});

test('invalid images are rejected; accepted photos invalidate approval and remain private', async t => {
  const h = harness(t);
  let {finding} = await createFinding(h);
  const invalid = await upload(h, finding, {bytes: Buffer.from('<script>not a JPEG</script>'), name: 'fake.jpg', type: 'image/jpeg'});
  assert.equal(invalid.status, 422);
  finding = await confirm(h, finding);
  const response = await upload(h, finding);
  assert.equal(response.status, 200, await response.clone().text());
  finding = await response.json();
  assert.equal(finding.status, 'draft');
  assert.ok(finding.facts.every(fact => fact.status === 'unknown'));
  assert.equal(finding.photos.length, 1);
  const photo = finding.photos[0];
  assert.equal((await h.request('GET', photo.url)).status, 200);
  assert.equal((await h.request('GET', photo.url, undefined, {identity: undefined})).status, 401);
});

test('copy clears observation, photos and facts; deleting the copy preserves the original', async t => {
  const h = harness(t);
  const {finding} = await createFinding(h);
  const copy = await h.json('POST', `/api/findings/${finding.id}/copy`, undefined, 201);
  assert.equal(copy.status, 'draft');
  assert.equal(copy.observation, '');
  assert.deepEqual(copy.photos, []);
  assert.ok(copy.bases.length);
  assert.ok(copy.facts.every(fact => fact.status === 'unknown' && !fact.note));
  await h.json('DELETE', `/api/findings/${copy.id}`);
  assert.equal((await h.request('GET', `/api/findings/${copy.id}`)).status, 404);
  assert.equal((await h.request('GET', `/api/findings/${finding.id}`)).status, 200);
});

test('JPEG metadata is stripped server-side before private storage', async t => {
  const h = harness(t);
  const {finding} = await createFinding(h);
  const payload = Buffer.from('Exif\0\0SYNTHETIC-GPS-AND-CAMERA-OWNER-NOT-REAL');
  const segment = Buffer.alloc(4);
  segment[0] = 0xff; segment[1] = 0xe1; segment.writeUInt16BE(payload.length + 2, 2);
  const tagged = Buffer.concat([JPEG.subarray(0, 2), segment, payload, JPEG.subarray(2)]);
  const response = await upload(h, finding, {bytes: tagged});
  assert.equal(response.status, 200, await response.clone().text());
  const saved = await response.json();
  const bytes = Buffer.from(await (await h.request('GET', saved.photos[0].url)).arrayBuffer());
  assert.ok(!bytes.includes(payload), 'the server must not retain the submitted EXIF segment');
  assert.equal(bytes[0], 0xff); assert.equal(bytes[1], 0xd8);
});

test('deleting a reopened record with cascading photos and reviews returns success', async t => {
  const h = harness(t);
  let {finding} = await createFinding(h);
  const photoResponse = await upload(h, finding);
  assert.equal(photoResponse.status, 200);
  finding = await confirm(h, await photoResponse.json());
  finding = await h.json('POST', `/api/findings/${finding.id}/review`, {revision: finding.revision, decision: 'reopen'});
  assert.ok(finding.photos.length && finding.reviews.length, 'fixture must exercise DELETE cascades');
  await h.json('DELETE', `/api/findings/${finding.id}`);
  assert.equal((await h.request('GET', `/api/findings/${finding.id}`)).status, 404);
});

test('editing during report rendering rejects the stale export and cleans its new objects', async t => {
  const h = harness(t);
  let {project, finding} = await createFinding(h);
  finding = await confirm(h, finding);
  const beforeObjects = [...h.env.BUCKET.objects.keys()].sort();
  const render = h.reporting.renderReport;
  h.reporting.renderReport = async (snapshot, options) => {
    await h.json('PATCH', `/api/findings/${finding.id}`, {revision: finding.revision, observation: '导出期间变更的合成观察'});
    return render(snapshot, options);
  };
  await h.json('POST', `/api/projects/${project.id}/reports`, {mode: 'confirmed'}, 409);
  assert.deepEqual(await h.json('GET', `/api/projects/${project.id}/reports`), []);
  assert.deepEqual([...h.env.BUCKET.objects.keys()].sort(), beforeObjects);
  assert.equal((await h.json('GET', `/api/findings/${finding.id}`)).status, 'draft');
});

test('private backup retains historical photo bytes after current-photo removal and fails on missing objects', async t => {
  const {unzipSync, strFromU8} = await import('fflate');
  const h = harness(t);
  let {project, finding} = await createFinding(h);
  const uploaded = await upload(h, finding);
  assert.equal(uploaded.status, 200);
  finding = await confirm(h, await uploaded.json());
  const photo = finding.photos[0];
  const historicalPhoto = new Uint8Array(await (await h.request('GET', photo.url)).arrayBuffer());
  const report = await h.json('POST', `/api/projects/${project.id}/reports`, {mode: 'confirmed'}, 201);
  finding = await h.json('DELETE', `/api/findings/${finding.id}/photos/${photo.id}`);
  assert.deepEqual(finding.photos, []);
  assert.equal(finding.status, 'draft');
  assert.equal((await h.request('GET', photo.url)).status, 404, 'removed photo is not listed as current evidence');
  const response = await h.request('GET', '/api/backup');
  assert.equal(response.status, 200);
  assert.match(response.headers.get('Cache-Control'), /no-store/);
  const files = unzipSync(new Uint8Array(await response.arrayBuffer()));
  const workspace = JSON.parse(strFromU8(files['workspace.json']));
  assert.equal(workspace.schema_version, 'safety-basis-cloud-backup-v1');
  assert.equal(workspace.tables.projects[0].id, project.id);
  assert.deepEqual(workspace.tables.photos, []);
  assert.ok(workspace.tables.reviews.some(review => review.decision === 'confirm'));
  assert.ok(workspace.tables.audit.some(event => event.action === 'photo_removed'));
  const archived = workspace.tables.reports.find(row => row.id === report.id);
  const snapshot = JSON.parse(archived.snapshot);
  const archivedPhoto = snapshot.findings[0].photos[0];
  assert.equal(archivedPhoto.id, photo.id);
  assert.deepEqual(files[`files/${archivedPhoto.object_key}`], historicalPhoto,
    'backup must include immutable photo bytes still referenced by old reports');
  assert.ok(files[`files/${archived.docx_key}`].length);
  assert.ok(files[`files/${archived.pdf_key}`].length);
  await h.env.BUCKET.delete(archivedPhoto.object_key);
  await h.json('GET', '/api/backup', undefined, 409);
  assert.equal((await h.json('GET', `/api/findings/${finding.id}`)).revision, finding.revision);
  assert.equal((await h.request('GET', report.snapshot_url)).status, 200);
});

test('a photo commit followed by a D1 read failure never deletes referenced object bytes', async t => {
  const h = harness(t);
  const {finding} = await createFinding(h);
  const batch = h.env.DB.batch.bind(h.env.DB);
  let committed = false, failNextRead = true;
  h.env.DB.batch = async statements => {
    if (committed && failNextRead && statements[0].sql.startsWith('SELECT f.*')) {
      failNextRead = false;
      throw new Error('synthetic transient D1 read failure after photo commit');
    }
    const result = await batch(statements);
    if (statements.some(statement => statement.sql.includes('INSERT INTO photos'))) committed = true;
    return result;
  };
  const response = await upload(h, finding);
  assert.ok([200, 503].includes(response.status), await response.clone().text());
  assert.ok(committed && !failNextRead, 'fixture must fail only the read after a committed photo mutation');
  const photos = (await h.env.DB.prepare('SELECT * FROM photos WHERE finding_id=?').bind(finding.id).all()).results;
  for (const photo of photos) assert.ok(await h.env.BUCKET.head(photo.object_key),
    'a committed D1 photo reference must never be left pointing to bytes removed by exception cleanup');
});

test('a report commit followed by a D1 read failure never deletes archived report bytes', async t => {
  const h = harness(t);
  let {project, finding} = await createFinding(h);
  finding = await confirm(h, finding);
  const batch = h.env.DB.batch.bind(h.env.DB), prepare = h.env.DB.prepare.bind(h.env.DB);
  let committed = false, failNextRead = true;
  h.env.DB.batch = async statements => {
    const result = await batch(statements);
    if (statements.some(statement => statement.sql.includes('INSERT INTO reports'))) committed = true;
    return result;
  };
  h.env.DB.prepare = sql => {
    const statement = prepare(sql);
    if (committed && failNextRead && sql === 'SELECT * FROM reports WHERE id=?') {
      const bind = statement.bind.bind(statement);
      statement.bind = (...values) => {
        const bound = bind(...values);
        bound.first = async () => { failNextRead = false; throw new Error('synthetic transient D1 read failure after report commit'); };
        return bound;
      };
    }
    return statement;
  };
  const response = await h.request('POST', `/api/projects/${project.id}/reports`, {mode: 'confirmed'});
  assert.ok([201, 503].includes(response.status), await response.clone().text());
  assert.ok(committed && !failNextRead, 'fixture must fail only the read after a committed report mutation');
  const reports = (await h.env.DB.prepare('SELECT * FROM reports WHERE project_id=?').bind(project.id).all()).results;
  for (const report of reports) {
    assert.ok(await h.env.BUCKET.head(report.docx_key), 'committed Word report bytes must survive a transient metadata read failure');
    assert.ok(await h.env.BUCKET.head(report.pdf_key), 'committed PDF report bytes must survive a transient metadata read failure');
  }
});

test('real cloud renderer produces parseable Word and PDF with a photo, full law and draft marker', async t => {
  const [{renderReport}, {unzipSync, strFromU8}, {PDFDocument}] = await Promise.all([
    import('../reporting.mjs'), import('fflate'), import('pdf-lib'),
  ]);
  const h = harness(t);
  h.reporting.renderReport = (snapshot, options) => renderReport(snapshot, {...options,
    fontBytes: new Uint8Array(readFileSync(new URL('../assets/report-font.ttf', import.meta.url)))});
  let {project, finding} = await createFinding(h);
  const uploadResponse = await upload(h, finding);
  assert.equal(uploadResponse.status, 200);
  finding = await uploadResponse.json();
  const report = await h.json('POST', `/api/projects/${project.id}/reports`, {mode: 'draft'}, 201);
  const wordBytes = new Uint8Array(await (await h.request('GET', report.docx_url)).arrayBuffer());
  const pdfBytes = new Uint8Array(await (await h.request('GET', report.pdf_url)).arrayBuffer());
  const entries = unzipSync(wordBytes);
  assert.ok(entries['word/document.xml'], 'Word must be a valid OOXML archive');
  assert.ok(Object.keys(entries).some(name => name.startsWith('word/media/')), 'Word must embed the private photo');
  const xml = strFromU8(entries['word/document.xml']);
  const plain = xml.replace(/<[^>]+>/g, '').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/\s+/g, '');
  assert.ok(plain.includes('草稿'));
  assert.ok(plain.includes('隐患照片'));
  assert.ok(plain.includes(project.company));
  for (const basis of finding.bases) {
    assert.ok(plain.includes(basis.text.replace(/\s+/g, '')), 'Word must contain the complete selected law text');
    assert.ok(plain.includes(basis.link_id) && plain.includes(basis.as_of));
  }
  const pdf = await PDFDocument.load(pdfBytes);
  assert.ok(pdf.getPageCount() >= 2, 'PDF must include the record plus law/fact appendices');
  assert.match(report.pdf_engine, /pdf-lib/);
});
