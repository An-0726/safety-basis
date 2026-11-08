// D1 statements are prepared individually and committed in transactional batches.
// Tables are migration-owned: request handling never creates or alters schema.
export class HttpError extends Error {
  constructor(status, detail) { super(typeof detail === 'string' ? detail : detail.message); this.status = status; this.detail = detail; }
}
export const uid = prefix => `${prefix}_${crypto.randomUUID().replaceAll('-', '')}`;
export const now = () => new Date().toISOString();
export const clone = value => JSON.parse(JSON.stringify(value));
export const FINDING_FIELDS = ['location', 'equipment', 'observation', 'description', 'rectification', 'due_date', 'assignee', 'notes', 'finding_kind'];

export function findingBody(finding) {
  return Object.fromEntries([...FINDING_FIELDS, 'status', 'bases', 'facts'].map(key => [key, finding[key]]));
}
function projectFromRow(row) {
  return row ? {...JSON.parse(row.body), id: row.id, revision: row.revision, created_at: row.created_at, updated_at: row.updated_at} : null;
}
function photoFromRow(row) { return {...row, url: `/api/photos/${row.id}`}; }
function findingFromRow(row, project, photos, reviews) {
  const finding = {...JSON.parse(row.body), id: row.id, project_id: row.project_id,
    position: row.position, revision: row.revision, created_at: row.created_at, updated_at: row.updated_at,
    photos: photos.map(photoFromRow), reviews};
  Object.defineProperties(finding, {
    _project_revision: {value: project.revision, enumerable: false},
    _project: {value: project, enumerable: false},
  });
  return finding;
}

export function createStore(env, identity) {
  const db = env.DB;
  if (!db?.prepare || !db?.batch) throw new HttpError(503, '私有数据库尚未绑定');
  const prepare = (sql, values = []) => db.prepare(sql).bind(...values);
  async function batch(statements) {
    const results = await db.batch(statements);
    if (results.some(result => result.success === false)) throw new HttpError(503, '数据库操作未完成，请重试');
    return results;
  }
  const rows = result => result.results || [];
  const changed = result => Number(result.meta?.changes ?? result.changes ?? 0);
  function auditStatement(entity, action, detail = {}, guard = '1', parameters = [], stamp = now(), auditId = uid('A')) {
    return prepare('INSERT INTO audit(id,entity_id,action,actor,actor_id,actor_source,detail,created_at) SELECT ?,?,?,?,?,?,?,? WHERE ' + guard,
      [auditId, entity, action, identity.displayName || identity.id, identity.id, identity.source,
        JSON.stringify(detail), stamp, ...parameters]);
  }
  async function getProject(id) {
    const row = await prepare(`SELECT p.*,
      (SELECT COUNT(*) FROM findings f WHERE f.project_id=p.id) AS findings_count,
      (SELECT COUNT(*) FROM findings f WHERE f.project_id=p.id AND json_extract(f.body,'$.status')='confirmed') AS confirmed_count
      FROM projects p WHERE p.id=?`, [id]).first();
    if (!row) throw new HttpError(404, '项目不存在');
    return {...projectFromRow(row), findings_count: row.findings_count, confirmed_count: row.confirmed_count};
  }
  async function listProjects() {
    const result = await prepare(`SELECT p.*,
      (SELECT COUNT(*) FROM findings f WHERE f.project_id=p.id) AS findings_count,
      (SELECT COUNT(*) FROM findings f WHERE f.project_id=p.id AND json_extract(f.body,'$.status')='confirmed') AS confirmed_count
      FROM projects p ORDER BY p.updated_at DESC,p.id`).all();
    return rows(result).map(row => ({...projectFromRow(row), findings_count: row.findings_count, confirmed_count: row.confirmed_count}));
  }
  async function loadFinding(id) {
    const result = await batch([
      prepare(`SELECT f.*,p.body AS project_body,p.revision AS project_revision,p.created_at AS project_created_at,
        p.updated_at AS project_updated_at FROM findings f JOIN projects p ON p.id=f.project_id WHERE f.id=?`, [id]),
      prepare('SELECT * FROM photos WHERE finding_id=? ORDER BY position,created_at,id', [id]),
      prepare('SELECT * FROM reviews WHERE finding_id=? ORDER BY created_at,rowid', [id]),
    ]);
    const row = rows(result[0])[0];
    if (!row) throw new HttpError(404, '隐患记录不存在');
    const project = projectFromRow({id: row.project_id, body: row.project_body, revision: row.project_revision,
      created_at: row.project_created_at, updated_at: row.project_updated_at});
    return findingFromRow(row, project, rows(result[1]), rows(result[2]));
  }
  async function loadProjectSnapshot(id) {
    // One read transaction prevents a concurrent deletion from invalidating an
    // ID list half way through loading its records and photographs.
    const result = await batch([
      prepare('SELECT * FROM projects WHERE id=?', [id]),
      prepare('SELECT * FROM findings WHERE project_id=? ORDER BY position,created_at,id', [id]),
      prepare('SELECT p.* FROM photos p JOIN findings f ON f.id=p.finding_id WHERE f.project_id=? ORDER BY p.position,p.created_at,p.id', [id]),
      prepare('SELECT r.* FROM reviews r JOIN findings f ON f.id=r.finding_id WHERE f.project_id=? ORDER BY r.created_at,r.rowid', [id]),
    ]);
    const project = projectFromRow(rows(result[0])[0]);
    if (!project) throw new HttpError(404, '项目不存在');
    const photos = rows(result[2]), reviews = rows(result[3]);
    const findings = rows(result[1]).map(row => findingFromRow(row, project,
      photos.filter(photo => photo.finding_id === row.id), reviews.filter(review => review.finding_id === row.id)));
    project.findings_count = findings.length;
    project.confirmed_count = findings.filter(finding => finding.status === 'confirmed').length;
    return {project, findings};
  }
  async function createProject(body) {
    const id = uid('P'), stamp = now();
    await batch([
      prepare('INSERT INTO projects(id,body,revision,mutation_id,created_at,updated_at) VALUES(?,?,1,?,?,?)', [id, JSON.stringify(body), uid('M'), stamp, stamp]),
      auditStatement(id, 'project_created', body, '1', [], stamp),
    ]);
    return getProject(id);
  }
  async function editProject(project, body) {
    if (Object.keys(body).every(key => body[key] === project[key])) return getProject(project.id);
    const stamp = now(), mutation = uid('M');
    const guard = 'EXISTS(SELECT 1 FROM projects WHERE id=? AND mutation_id=?)';
    const parameters = [project.id, mutation];
    const result = await batch([
      prepare('UPDATE projects SET body=?,revision=revision+1,mutation_id=?,updated_at=? WHERE id=? AND revision=?',
        [JSON.stringify(body), mutation, stamp, project.id, project.revision]),
      auditStatement(project.id, 'project_updated', body, guard, parameters, stamp),
      prepare(`UPDATE findings SET body=json_set(body,'$.status','draft','$.facts',json(COALESCE(
        (SELECT json_group_array(json_set(value,'$.status','unknown','$.note','')) FROM json_each(findings.body,'$.facts')),'[]'))),
        revision=revision+1,mutation_id=?,updated_at=? WHERE project_id=? AND ${guard}`, [mutation, stamp, project.id, ...parameters]),
      prepare(`INSERT INTO audit(id,entity_id,action,actor,actor_id,actor_source,detail,created_at)
        SELECT 'A_'||lower(hex(randomblob(16))),id,'project_context_changed',?,?,?,
        json_object('revision',revision,'status','draft','project_id',project_id),? FROM findings
        WHERE project_id=? AND mutation_id=? AND ${guard}`,
        [identity.displayName || identity.id, identity.id, identity.source, stamp, project.id, mutation, ...parameters]),
    ]);
    if (changed(result[0]) !== 1) throw new HttpError(409, '项目已在其他页面修改，请重新打开后保存');
    return getProject(project.id);
  }
  async function createFinding(projectId, body, action = 'finding_created', detail = null) {
    const project = await getProject(projectId), id = uid('F'), stamp = now();
    const guard = 'EXISTS(SELECT 1 FROM findings WHERE id=?)';
    const result = await batch([
      prepare(`INSERT INTO findings(id,project_id,body,position,revision,mutation_id,created_at,updated_at)
        SELECT ?,?,?,(SELECT COALESCE(MAX(position),0)+1 FROM findings WHERE project_id=?),1,?,?,?
        FROM projects WHERE id=? AND revision=?`,
        [id, projectId, JSON.stringify(body), projectId, uid('M'), stamp, stamp, projectId, project.revision]),
      prepare(`UPDATE projects SET updated_at=? WHERE id=? AND ${guard}`, [stamp, projectId, id]),
      auditStatement(id, action, detail || body, guard, [id], stamp),
    ]);
    if (changed(result[0]) !== 1) throw new HttpError(409, '项目条件已变化，请重新打开后创建记录');
    return loadFinding(id);
  }
  async function mutateFinding(finding, action, extraStatements = () => [], detail = null) {
    const stamp = now(), mutation = uid('M'), body = findingBody(finding);
    const guard = 'EXISTS(SELECT 1 FROM findings WHERE id=? AND mutation_id=?)';
    const parameters = [finding.id, mutation];
    const result = await batch([
      prepare(`UPDATE findings SET body=?,position=?,revision=revision+1,mutation_id=?,updated_at=?
        WHERE id=? AND revision=? AND EXISTS(SELECT 1 FROM projects WHERE id=? AND revision=?)`,
        [JSON.stringify(body), finding.position, mutation, stamp, finding.id, finding.revision,
          finding.project_id, finding._project_revision]),
      ...extraStatements({guard, parameters, stamp, mutation, prepare}),
      prepare(`UPDATE projects SET updated_at=? WHERE id=? AND ${guard}`, [stamp, finding.project_id, ...parameters]),
      auditStatement(finding.id, action, detail || {revision: finding.revision + 1, status: finding.status, body}, guard, parameters, stamp),
    ]);
    if (changed(result[0]) !== 1) throw new HttpError(409, '记录或项目条件已变化，请重新打开后保存；旧数据未覆盖新记录');
    return loadFinding(finding.id);
  }
  async function deleteFinding(finding) {
    if (finding.status !== 'draft') throw new HttpError(409, '请先重开记录为草稿后删除');
    const stamp = now(), auditId = uid('A');
    const predicate = "id=? AND revision=? AND json_extract(body,'$.status')='draft' AND EXISTS(SELECT 1 FROM projects WHERE id=? AND revision=?)";
    const parameters = [finding.id, finding.revision, finding.project_id, finding._project_revision];
    const result = await batch([
      auditStatement(finding.id, 'finding_deleted', finding, `EXISTS(SELECT 1 FROM findings WHERE ${predicate})`, parameters, stamp, auditId),
      prepare(`DELETE FROM findings WHERE ${predicate}`, parameters),
      prepare('UPDATE projects SET updated_at=? WHERE id=? AND EXISTS(SELECT 1 FROM audit WHERE id=?)', [stamp, finding.project_id, auditId]),
    ]);
    // D1 counts cascaded photo/review deletions as well as the parent row.
    if (changed(result[1]) < 1) throw new HttpError(409, '记录已变化，请重新打开后删除');
    return {deleted: finding.id};
  }
  async function saveReport(snapshot, keys, expectedFindings) {
    const guard = `p.id=? AND p.revision=? AND (SELECT COUNT(*) FROM findings WHERE project_id=p.id)=?
      AND NOT EXISTS(SELECT 1 FROM json_each(?) expected LEFT JOIN findings f ON f.id=json_extract(expected.value,'$.id')
        WHERE f.id IS NULL OR f.project_id<>p.id OR f.revision<>json_extract(expected.value,'$.revision'))`;
    const parameters = [snapshot.project.id, snapshot.project.revision, expectedFindings.length,
      JSON.stringify(expectedFindings.map(f => ({id: f.id, revision: f.revision})))];
    const result = await batch([
      prepare(`INSERT INTO reports(id,project_id,mode,snapshot,created_at,docx_key,pdf_key,pdf_engine)
        SELECT ?,?,?,?,?,?,?,? FROM projects p WHERE ${guard}`,
        [snapshot.id, snapshot.project.id, snapshot.mode, JSON.stringify(snapshot), snapshot.created_at,
          keys.docx, keys.pdf, keys.pdf_engine, ...parameters]),
      auditStatement(snapshot.project.id, 'report_exported', {report_id: snapshot.id, mode: snapshot.mode, findings: snapshot.findings.length},
        'EXISTS(SELECT 1 FROM reports WHERE id=?)', [snapshot.id], snapshot.created_at),
    ]);
    if (changed(result[0]) !== 1) throw new HttpError(409, '项目或记录在生成报告期间发生变化，请重新核实并导出；未保存过时报告');
    return prepare('SELECT * FROM reports WHERE id=?', [snapshot.id]).first();
  }
  return {db, prepare, batch, rows, changed, auditStatement, getProject, listProjects, loadFinding,
    loadProjectSnapshot, createProject, editProject, createFinding, mutateFinding, deleteFinding, saveReport};
}
