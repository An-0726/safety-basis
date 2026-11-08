"""Single-user / small-team inspection API. Run through ``python -m workbench``."""
import base64
import csv
import hashlib
import html
import io
import json
import os
import secrets
import shutil
import sqlite3
import zipfile
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field

from .knowledge import Knowledge, KnowledgeError
from .facts import FACT_LABELS, is_conditional_fact
from .storage import Store, blockers, dumps, invalidate, now, uid

ROOT = Path(__file__).resolve().parents[2]
PROJECT_FIELDS = {'company', 'name', 'inspection_date', 'inspectors', 'purpose'}
FINDING_FIELDS = {'location', 'equipment', 'observation', 'description', 'rectification',
                  'due_date', 'assignee', 'notes', 'position', 'finding_kind'}


class ProjectInput(BaseModel):
    company: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    inspection_date: date
    inspectors: str = Field(default='', max_length=300)
    purpose: str = Field(default='安全检查', max_length=1000)


class FindingInput(BaseModel):
    location: str = Field(default='', max_length=500)
    equipment: str = Field(default='', max_length=500)
    observation: str = Field(default='', max_length=12000)
    description: str = Field(default='', max_length=12000)
    rectification: str = Field(default='', max_length=12000)
    due_date: str = Field(default='', max_length=40)
    assignee: str = Field(default='', max_length=200)
    notes: str = Field(default='', max_length=12000)
    finding_kind: str = 'onsite'


class BasisInput(BaseModel):
    hazard_id: str
    link_ids: list[str] | None = None
    profile_id: str | None = None


class ReviewInput(BaseModel):
    decision: str
    revision: int | None = None
    reviewer: str = Field(default='', max_length=200)
    comment: str = Field(default='', max_length=4000)


def clean_text(value, limit=12000):
    if not isinstance(value, str) or len(value) > limit or any(
        ord(ch) < 32 and ch not in '\n\r\t' for ch in value
    ):
        raise HTTPException(422, '文本格式或长度无效')
    return value.strip()


def source_fingerprint(detail, item, profile):
    """Compare legal content and scope, independent of unrelated package changes."""
    source = {
        'hazard': {k: detail['hazard'].get(k) for k in ('id', 'title', 'conditions', 'description', 'measures')},
        'ref': {k: item['ref'].get(k) for k in ('linkId', 'clauseId', 'role', 'applicability', 'jurisdictionCode')},
        'clause': {k: item['clause'].get(k) for k in ('id', 'article', 'quote', 'lawId', 'sourceUrl')},
        'law': {k: item['law'].get(k) for k in ('id', 'name', 'documentNumber', 'effectiveDate', 'status', 'scope', 'sourceUrl')},
        'profile': profile,
        'dispositions': [{k: p.get(k) for k in ('id', 'inspectionClass', 'defaultFieldEntry', 'contentDisposition')} for p in detail['profiles']],
    }
    return hashlib.sha256(json.dumps(source, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def create_app(data_dir=None, bundle=None):
    data_root = Path(data_dir or os.environ.get('WORKBENCH_DATA_DIR') or
                     Path.home() / '.safety-basis-workbench').resolve()
    if data_root == ROOT or ROOT in data_root.parents:
        allowed = [ROOT / p for p in ('workbench/runtime', 'workbench/private', 'workbench-data', 'tmp')]
        if not any(data_root == p or p in data_root.parents for p in allowed):
            raise ValueError('仓库内请使用已忽略的 workbench/runtime 私有目录，或使用仓库外目录')
    # No endpoint exposes this directory; reject accidental placement in Pages/knowledge.
    for forbidden in (ROOT / 'web', ROOT / 'knowledge', ROOT / 'source/publication', ROOT / 'source/releases'):
        if data_root == forbidden or forbidden in data_root.parents:
            raise ValueError('工作台私有数据目录不能放入公开知识源或网站发布目录')
    store = Store(data_root)
    knowledge = Knowledge(bundle or os.environ.get('WORKBENCH_BUNDLE') or ROOT / 'source/releases/current')
    access_token = os.environ.get('WORKBENCH_ACCESS_TOKEN', '')

    @asynccontextmanager
    async def lifespan(app):
        yield
        knowledge.close()

    app = FastAPI(title='隐患检查工作台', version='1.0.0', lifespan=lifespan,
                  docs_url=None, redoc_url=None)
    app.state.store = store
    app.state.knowledge = knowledge

    @app.middleware('http')
    async def local_privacy(request: Request, call_next):
        # A browser page on another origin must not send private write requests.
        origin = request.headers.get('origin')
        if origin and origin != str(request.base_url).rstrip('/'):
            return JSONResponse({'detail': '仅接受工作台本身发起的请求'}, status_code=403)
        host = request.url.hostname
        local = host in ('localhost', '127.0.0.1', '::1', 'testserver')
        if not local and not access_token:
            return JSONResponse({'detail': '远程访问须设置 WORKBENCH_ACCESS_TOKEN 并经 HTTPS 反向代理'}, status_code=403)
        if access_token:
            auth = request.headers.get('authorization', '')
            password = ''
            if auth.startswith('Basic '):
                try:
                    password = base64.b64decode(auth[6:]).decode().split(':', 1)[1]
                except (ValueError, UnicodeError, IndexError):
                    pass
            if not secrets.compare_digest(password, access_token):
                return Response(status_code=401, headers={'WWW-Authenticate': 'Basic realm="Inspection workbench"'})
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; img-src 'self' blob: data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; connect-src 'self'; frame-ancestors 'none'; object-src 'none'"
        )
        return response

    @app.exception_handler(KnowledgeError)
    async def knowledge_error(_request, exc):
        return JSONResponse({'detail': str(exc)}, status_code=503)

    def project_or_404(conn, project_id):
        p = store.project(conn.execute('SELECT * FROM projects WHERE id=?', (project_id,)).fetchone())
        if p is None:
            raise HTTPException(404, '项目不存在')
        return p

    def finding_or_404(conn, finding_id):
        finding = store.finding(conn.execute('SELECT * FROM findings WHERE id=?', (finding_id,)).fetchone())
        if finding is None:
            raise HTTPException(404, '隐患记录不存在')
        finding['photos'] = [photo_dict(row) for row in conn.execute(
            'SELECT * FROM photos WHERE finding_id=? ORDER BY position,created_at,id', (finding_id,))]
        finding['reviews'] = [dict(row) for row in conn.execute(
            'SELECT * FROM reviews WHERE finding_id=? ORDER BY created_at,rowid', (finding_id,))]
        finding['blockers'] = blockers(finding) + reference_issues(finding, project_or_404(conn, finding['project_id']))
        return finding

    def reference_issues(finding, project):
        issues = []
        if not finding['bases']:
            return issues
        inspected = project['inspection_date']
        details = {}
        for basis in finding['bases']:
            effective = basis.get('effective_date')
            if not effective:
                issues.append(f'{basis["law_version_id"]} 缺少施行日期快照，请重新选入正式依据')
            elif inspected < effective:
                issues.append(f'{basis["law_version_id"]} 于 {effective} 施行，晚于本次检查日期 {inspected}')
            if inspected > basis['as_of']:
                issues.append(f'检查日期 {inspected} 晚于引用快照 {basis["as_of"]}，请更新知识包并重新选择依据')
            try:
                if basis['hazard_id'] not in details:
                    details[basis['hazard_id']] = knowledge.call('detail', hazard_id=basis['hazard_id'])
                detail = details[basis['hazard_id']]
                item = next((b for b in detail['bases'] if b['ref']['linkId'] == basis['link_id']), None)
                profile_id = (basis.get('profile') or {}).get('id')
                profile = next((p for p in detail['profiles'] if p['id'] == profile_id), None) if profile_id else None
                if item is None or (profile_id and profile is None) or source_fingerprint(detail, item, profile) != basis.get('source_fingerprint'):
                    issues.append(f'{basis["link_id"]} 的依据或适用条件已变化，请按检查日期重新检索、选择并核实；历史报告保持原样')
            except KnowledgeError:
                issues.append(f'{basis["hazard_id"]} 暂不能在当前正式包中核对，请按检查日期更新依据后审核')
        return list(dict.fromkeys(issues))

    def photo_dict(row):
        return {k: row[k] for k in ('id', 'finding_id', 'filename', 'caption', 'position', 'sha256', 'created_at')} | {
            'url': f'/api/photos/{row["id"]}',
        }

    def current_findings(conn, project_id):
        # Keep ID, photo, review and fact reads in one WAL snapshot. Otherwise a
        # concurrent draft deletion can turn a list request into a spurious 404.
        if not conn.in_transaction:
            conn.execute('BEGIN')
        ids = [row['id'] for row in conn.execute(
            'SELECT id FROM findings WHERE project_id=? ORDER BY position,created_at,id', (project_id,))]
        return [finding_or_404(conn, item) for item in ids]

    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'version': '1.0.0', 'private_storage': True, 'knowledge': knowledge.call('meta')}

    @app.get('/api/docs', include_in_schema=False, response_class=HTMLResponse)
    def api_docs():
        rows = []
        for path, methods in app.openapi()['paths'].items():
            for method, operation in methods.items():
                rows.append('<tr><td>' + html.escape(method.upper()) + '</td><td><code>' + html.escape(path)
                            + '</code></td><td>' + html.escape(operation.get('summary', '')) + '</td></tr>')
        return ('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>工作台API</title>'
                '<style>body{font:16px system-ui;max-width:1100px;margin:40px auto;padding:20px}'
                'td,th{border:1px solid #ccc;padding:10px;text-align:left}table{border-collapse:collapse}</style>'
                '<h1>工作台API</h1><p><a href="/">返回工作台</a> · <a href="/openapi.json">完整OpenAPI请求与响应结构</a></p>'
                '<p>本页面与接口均在本机提供；默认不请求外部文档CDN。</p>'
                '<table><tr><th>方法</th><th>路径</th><th>用途</th></tr>' + ''.join(rows) + '</table></html>')

    @app.get('/api/knowledge/meta')
    def knowledge_meta():
        return knowledge.call('meta')

    @app.get('/api/knowledge/search')
    def search(q: str = '', region: str = '', category: str = '', limit: int = 30):
        if len(q) > 1000:
            raise HTTPException(422, '检索内容过长')
        return knowledge.call('search', q=q, filters={'region': region, 'category': category}, limit=max(1, min(limit, 100)))

    @app.get('/api/knowledge/hazards/{hazard_id}')
    def hazard_detail(hazard_id: str):
        return knowledge.call('detail', hazard_id=hazard_id)

    @app.get('/api/projects')
    def list_projects():
        with store.connect() as conn:
            result = []
            for row in conn.execute('SELECT * FROM projects ORDER BY updated_at DESC,id'):
                p = store.project(row)
                fs = current_findings(conn, p['id'])
                p.update(findings_count=len(fs), confirmed_count=sum(f['status'] == 'confirmed' for f in fs))
                result.append(p)
            return result

    @app.post('/api/projects', status_code=201)
    def create_project(payload: ProjectInput):
        data = payload.model_dump(mode='json')
        data = {key: clean_text(value, 1000) for key, value in data.items()}
        if not data['company'] or not data['name']:
            raise HTTPException(422, '企业名称和项目名称不能为空')
        with store.lock, store.connect() as conn:
            project_id, stamp = uid('P'), now()
            conn.execute('INSERT INTO projects VALUES(?,?,?,?)', (project_id, dumps(data), stamp, stamp))
            store.audit(conn, project_id, 'project_created', data)
            return project_or_404(conn, project_id)

    @app.get('/api/projects/{project_id}')
    def get_project(project_id: str):
        with store.connect() as conn:
            p = project_or_404(conn, project_id)
            fs = current_findings(conn, project_id)
            return {**p, 'findings_count': len(fs), 'confirmed_count': sum(f['status'] == 'confirmed' for f in fs)}

    @app.patch('/api/projects/{project_id}')
    def edit_project(project_id: str, payload: dict):
        if set(payload) - PROJECT_FIELDS:
            raise HTTPException(422, '包含不支持的项目字段')
        with store.lock, store.connect() as conn:
            project = project_or_404(conn, project_id)
            data = {key: project[key] for key in PROJECT_FIELDS}
            data.update({key: clean_text(value, 1000) for key, value in payload.items()})
            if not data['company'] or not data['name']:
                raise HTTPException(422, '企业名称和项目名称不能为空')
            try:
                date.fromisoformat(data['inspection_date'])
            except ValueError as exc:
                raise HTTPException(422, '检查日期无效') from exc
            conn.execute('UPDATE projects SET body=?,updated_at=? WHERE id=?', (dumps(data), now(), project_id))
            store.audit(conn, project_id, 'project_updated', data)
            if any(data[key] != project[key] for key in PROJECT_FIELDS):
                for finding in current_findings(conn, project_id):
                    invalidate(finding, reset_facts=True)
                    finding['status'] = 'draft'
                    store.save_finding(conn, finding, 'project_context_changed')
            return project_or_404(conn, project_id)

    @app.get('/api/projects/{project_id}/findings')
    def list_findings(project_id: str):
        with store.connect() as conn:
            project_or_404(conn, project_id)
            return current_findings(conn, project_id)

    @app.post('/api/projects/{project_id}/findings', status_code=201)
    def create_finding(project_id: str, payload: FindingInput):
        data = {key: clean_text(value) for key, value in payload.model_dump().items()}
        if data['finding_kind'] not in ('onsite', 'document_review'):
            raise HTTPException(422, '记录类型无效')
        with store.lock, store.connect() as conn:
            project_or_404(conn, project_id)
            pos = conn.execute('SELECT COALESCE(MAX(position),0)+1 FROM findings WHERE project_id=?', (project_id,)).fetchone()[0]
            fid, stamp = uid('F'), now()
            data.update(status='draft', bases=[], facts=[])
            conn.execute('INSERT INTO findings VALUES(?,?,?,?,?,?,?)', (fid, project_id, dumps(data), pos, 1, stamp, stamp))
            conn.execute('UPDATE projects SET updated_at=? WHERE id=?', (stamp, project_id))
            store.audit(conn, fid, 'finding_created', data)
            return finding_or_404(conn, fid)

    @app.get('/api/findings/{finding_id}')
    def get_finding(finding_id: str):
        with store.connect() as conn:
            return finding_or_404(conn, finding_id)

    @app.patch('/api/findings/{finding_id}')
    def edit_finding(finding_id: str, payload: dict):
        if set(payload) - FINDING_FIELDS - {'revision'}:
            raise HTTPException(422, '状态、法源和事实只能通过对应操作修改')
        with store.lock, store.connect() as conn:
            finding = finding_or_404(conn, finding_id)
            if 'revision' in payload and payload['revision'] != finding['revision']:
                raise HTTPException(409, '记录已在其他页面修改，请重新打开后保存')
            changed = False
            substantive = False
            for key, value in payload.items():
                if key == 'revision':
                    continue
                if key == 'position':
                    if not isinstance(value, int) or not 0 <= value <= 100000:
                        raise HTTPException(422, '排序位置无效')
                else:
                    value = clean_text(value)
                if key == 'finding_kind' and value not in ('onsite', 'document_review'):
                    raise HTTPException(422, '记录类型无效')
                if finding.get(key) != value:
                    changed = True
                    substantive |= key != 'position'
                    finding[key] = value
            if changed:
                if substantive:
                    invalidate(finding, reset_facts=True)
                store.save_finding(conn, finding, 'finding_updated')
            return finding_or_404(conn, finding_id)

    @app.delete('/api/findings/{finding_id}')
    def delete_finding(finding_id: str):
        with store.lock, store.connect() as conn:
            finding = finding_or_404(conn, finding_id)
            if finding['status'] != 'draft':
                raise HTTPException(409, '请先重开记录为草稿后删除')
            store.audit(conn, finding_id, 'finding_deleted', finding)
            conn.execute('DELETE FROM findings WHERE id=?', (finding_id,))
            # Image bytes remain available to previously exported report snapshots.
            return {'deleted': finding_id}

    @app.post('/api/findings/{finding_id}/copy', status_code=201)
    def copy_finding(finding_id: str):
        with store.lock, store.connect() as conn:
            finding = finding_or_404(conn, finding_id)
            new_id, stamp = uid('F'), now()
            body = {key: finding[key] for key in FINDING_FIELDS if key != 'position'}
            body.update(status='draft', bases=finding['bases'], facts=finding['facts'])
            invalidate(body, reset_facts=True)
            position = conn.execute('SELECT COALESCE(MAX(position),0)+1 FROM findings WHERE project_id=?', (finding['project_id'],)).fetchone()[0]
            conn.execute('INSERT INTO findings VALUES(?,?,?,?,?,?,?)', (new_id, finding['project_id'], dumps(body), position, 1, stamp, stamp))
            # Copy text/bases only: photographs and observations require a new site check.
            body['observation'] = ''
            conn.execute('UPDATE findings SET body=? WHERE id=?', (dumps(body), new_id))
            store.audit(conn, new_id, 'finding_copied', {'from': finding_id})
            return finding_or_404(conn, new_id)

    def rebuild_facts(finding, reset=False):
        previous = {item['key']: item for item in finding.get('facts', [])}
        wanted = [('observation', '现场事实', '现场对象、具体缺陷与观察记录相符，已核实而非推测')]
        seen_profiles = set()
        seen_hazards = set()
        optional = set()
        for basis in finding['bases']:
            if basis['hazard_id'] not in seen_hazards:
                seen_hazards.add(basis['hazard_id'])
                wanted.append((f'hazard:{basis["hazard_id"]}', '隐患适用范围', basis['hazard_conditions']))
            wanted.append((f'applicability:{basis["id"]}', '适用条件', basis['applicability'] or '本条款的主体、地域和适用条件成立'))
            wanted.append((f'scope:{basis["id"]}', '地域与范围', f'已核对 {basis["scope"] or "本条款"} 的地域、行业和适用对象'))
            profile = basis.get('profile')
            if profile and profile['id'] not in seen_profiles:
                seen_profiles.add(profile['id'])
                for key, label in (('requires', '场景前提'), ('excludes', '误判边界'), ('perUseFacts', '本次事实')):
                    for index, value in enumerate(profile['applicability'].get(key, [])):
                        text = FACT_LABELS.get(value, value)
                        if key == 'excludes':
                            text = '已核对并遵守此边界：' + text
                        fact_key = f'profile:{profile["id"]}:{key}:{index}'
                        wanted.append((fact_key, label, text))
                        if key == 'perUseFacts' and is_conditional_fact(value):
                            optional.add(fact_key)
        facts = []
        seen_labels = set()
        for key, kind, label in wanted:
            if (kind, label) in seen_labels:
                continue
            seen_labels.add((kind, label))
            old = previous.get(key, {}) if not reset else {}
            facts.append({'key': key, 'kind': kind, 'label': label, 'expected': 'confirmed',
                          'status': old.get('status', 'unknown'), 'note': old.get('note', ''),
                          'allows_denied': key in optional})
        finding['facts'] = facts

    @app.post('/api/findings/{finding_id}/bases')
    def add_basis(finding_id: str, payload: BasisInput):
        detail = knowledge.call('detail', hazard_id=payload.hazard_id)
        available = {item['ref']['linkId']: item for item in detail['bases']}
        selected = payload.link_ids if payload.link_ids is not None else list(available)
        if not selected or set(selected) - set(available):
            raise HTTPException(422, '必须选择该正式条目的有效引用')
        profile = None
        if payload.profile_id:
            profile = next((p for p in detail['profiles'] if p['id'] == payload.profile_id), None)
            if profile is None or not set(profile['basisLinkIds']).issubset(set(selected)):
                raise HTTPException(422, '场景与所选条款不一致，请保留场景所需的全部引用')
        with store.lock, store.connect() as conn:
            finding = finding_or_404(conn, finding_id)
            # Reselection replaces this H's bindings, retaining other selected hazards.
            finding['bases'] = [b for b in finding['bases'] if b['hazard_id'] != payload.hazard_id]
            for link_id in dict.fromkeys(selected):
                item = available[link_id]
                clause, law, ref = item['clause'], item['law'], item['ref']
                finding['bases'].append({
                    'id': uid('B'), 'hazard_id': payload.hazard_id, 'hazard_title': detail['hazard']['title'],
                    'link_id': link_id, 'clause_id': clause['id'], 'law_version_id': law['id'],
                    'law_name': law['name'], 'document_number': law.get('documentNumber', ''),
                    'article': clause['article'], 'text': clause['quote'], 'source_url': item['sourceUrl'],
                    'role': ref.get('role', ''), 'applicability': ref.get('applicability', ''),
                    'hazard_conditions': detail['hazard'].get('conditions', ''),
                    'scope': law.get('scope', ''), 'jurisdiction_code': ref.get('jurisdictionCode', ''),
                    'as_of': detail['meta']['as_of'], 'data_version': detail['meta']['data_version'],
                    'effective_date': law.get('effectiveDate', ''),
                    'source_fingerprint': source_fingerprint(detail, item, profile),
                    'release_hash': detail['meta']['release_hash'], 'queried_at': now(),
                    'profile': profile, 'inspection_class': profile.get('inspectionClass', '') if profile else (
                        'document_review' if detail['profiles'] and all(p['inspectionClass'] == 'document_review' for p in detail['profiles']) else ''),
                    'hazard_inspection_classes': sorted({p['inspectionClass'] for p in detail['profiles']}),
                })
            rebuild_facts(finding, reset=True)
            invalidate(finding)
            store.save_finding(conn, finding, 'basis_selected')
            return finding_or_404(conn, finding_id)

    @app.delete('/api/findings/{finding_id}/bases/{basis_id}')
    def remove_basis(finding_id: str, basis_id: str):
        with store.lock, store.connect() as conn:
            finding = finding_or_404(conn, finding_id)
            target = next((b for b in finding['bases'] if b['id'] == basis_id), None)
            if not target:
                raise HTTPException(404, '引用不存在')
            finding['bases'] = [b for b in finding['bases'] if b['id'] != basis_id]
            for b in finding['bases']:
                if b.get('profile') and target['link_id'] in b['profile']['basisLinkIds']:
                    b['profile'] = None
                    b['inspection_class'] = 'document_review' if b.get('hazard_inspection_classes') == ['document_review'] else ''
            rebuild_facts(finding, reset=True)
            invalidate(finding)
            store.save_finding(conn, finding, 'basis_removed')
            return finding_or_404(conn, finding_id)

    @app.put('/api/findings/{finding_id}/facts')
    def update_facts(finding_id: str, payload: dict):
        updates = payload.get('facts')
        if not isinstance(updates, list):
            raise HTTPException(422, 'facts 必须是列表')
        with store.lock, store.connect() as conn:
            finding = finding_or_404(conn, finding_id)
            if payload.get('revision') != finding['revision']:
                raise HTTPException(409, '记录版本已变化或缺少版本号，请重新打开后核实；旧事实未覆盖新记录')
            mapped = {f['key']: f for f in finding['facts']}
            for item in updates:
                if not isinstance(item, dict) or item.get('key') not in mapped or item.get('status') not in ('unknown', 'confirmed', 'denied'):
                    raise HTTPException(422, '事实条目或状态无效')
                mapped[item['key']].update(status=item['status'], note=clean_text(item.get('note', ''), 4000))
            invalidate(finding)
            store.save_finding(conn, finding, 'facts_updated')
            return finding_or_404(conn, finding_id)

    @app.post('/api/findings/{finding_id}/review')
    def review(finding_id: str, payload: ReviewInput):
        if payload.decision not in ('submit', 'confirm', 'reject', 'reopen'):
            raise HTTPException(422, '审核动作无效')
        with store.lock, store.connect() as conn:
            finding = finding_or_404(conn, finding_id)
            if payload.revision != finding['revision']:
                raise HTTPException(409, '审核记录版本已变化或缺少版本号，请重新打开后审核')
            reviewer, comment = clean_text(payload.reviewer, 200), clean_text(payload.comment, 4000)
            if payload.decision in ('confirm', 'reject') and (not reviewer or not comment):
                raise HTTPException(422, '请填写审核人和审核意见')
            if payload.decision == 'submit':
                finding['status'] = 'needs_facts' if finding['blockers'] else 'pending_review'
            elif payload.decision == 'confirm':
                issues = finding['blockers']
                if finding['status'] != 'pending_review' or issues:
                    raise HTTPException(409, {'message': '需补全事实、证据并提交审核后才能确认', 'blockers': issues})
                finding['status'] = 'confirmed'
            elif payload.decision == 'reject':
                finding['status'] = 'rejected'
            else:
                finding['status'] = 'draft'
            conn.execute('INSERT INTO reviews VALUES(?,?,?,?,?,?,?)', (
                uid('R'), finding_id, payload.decision, reviewer or '本机操作人', comment,
                finding['revision'] + 1, now(),
            ))
            store.save_finding(conn, finding, 'review_' + payload.decision, reviewer or '本机操作人')
            return finding_or_404(conn, finding_id)

    def persist_photo(conn, finding, image_bytes, original_name, caption):
        if len(image_bytes) > 20 * 1024 * 1024:
            raise HTTPException(413, '单张照片不得超过20MB')
        try:
            with Image.open(io.BytesIO(image_bytes)) as original:
                if original.format not in ('JPEG', 'PNG', 'WEBP') or original.width * original.height > 40000000:
                    raise HTTPException(422, '仅接受40MP以内的 JPEG / PNG / WebP 图像')
                original.load()
                photo = ImageOps.exif_transpose(original)
                if photo.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', photo.size, 'white')
                    background.paste(photo, mask=photo.getchannel('A'))
                    photo = background
                else:
                    photo = photo.convert('RGB')
                photo.thumbnail((2400, 2400))
                result = io.BytesIO()
                photo.save(result, 'JPEG', quality=90, optimize=True)
                content = result.getvalue()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise HTTPException(422, '图像无法读取，请上传实际图片') from exc
        photo_id = uid('IMG')
        path = Path('photos') / (photo_id + '.jpg')
        (store.root / path).write_bytes(content)
        position = conn.execute('SELECT COALESCE(MAX(position),0)+1 FROM photos WHERE finding_id=?', (finding['id'],)).fetchone()[0]
        conn.execute('INSERT INTO photos VALUES(?,?,?,?,?,?,?,?)', (
            photo_id, finding['id'], Path(original_name or 'photo.jpg').name[:200], str(path),
            clean_text(caption, 1000), position, hashlib.sha256(content).hexdigest(), now(),
        ))
        invalidate(finding, reset_facts=True)
        store.save_finding(conn, finding, 'photo_added')
        return finding_or_404(conn, finding['id'])

    @app.post('/api/findings/{finding_id}/photos')
    async def upload_photo(finding_id: str, file: UploadFile = File(...), caption: str = Form('')):
        content = await file.read(20 * 1024 * 1024 + 1)
        await file.close()
        with store.lock, store.connect() as conn:
            finding = finding_or_404(conn, finding_id)
            return persist_photo(conn, finding, content, file.filename, caption)

    @app.get('/api/photos/{photo_id}')
    def get_photo(photo_id: str):
        with store.connect() as conn:
            row = conn.execute('SELECT * FROM photos WHERE id=?', (photo_id,)).fetchone()
            if row is None:
                raise HTTPException(404, '照片不存在')
            return FileResponse(store.root / row['path'], media_type='image/jpeg')

    @app.patch('/api/findings/{finding_id}/photos/{photo_id}')
    def update_photo(finding_id: str, photo_id: str, payload: dict):
        if set(payload) - {'caption', 'position'}:
            raise HTTPException(422, '照片字段无效')
        with store.lock, store.connect() as conn:
            finding = finding_or_404(conn, finding_id)
            row = conn.execute('SELECT * FROM photos WHERE id=? AND finding_id=?', (photo_id, finding_id)).fetchone()
            if row is None:
                raise HTTPException(404, '照片不存在')
            position = payload.get('position', row['position'])
            if not isinstance(position, int) or not 0 <= position <= 100000:
                raise HTTPException(422, '照片排序位置无效')
            caption = clean_text(payload.get('caption', row['caption']), 1000)
            conn.execute('UPDATE photos SET caption=?,position=? WHERE id=?', (caption, position, photo_id))
            invalidate(finding, reset_facts=True)
            store.save_finding(conn, finding, 'photo_updated')
            return finding_or_404(conn, finding_id)

    @app.delete('/api/findings/{finding_id}/photos/{photo_id}')
    def delete_photo(finding_id: str, photo_id: str):
        with store.lock, store.connect() as conn:
            finding = finding_or_404(conn, finding_id)
            found = conn.execute('SELECT id FROM photos WHERE id=? AND finding_id=?', (photo_id, finding_id)).fetchone()
            if not found:
                raise HTTPException(404, '照片不存在')
            conn.execute('DELETE FROM photos WHERE id=?', (photo_id,))
            invalidate(finding, reset_facts=True)
            store.save_finding(conn, finding, 'photo_removed')
            return finding_or_404(conn, finding_id)

    @app.get('/api/projects/{project_id}/photos.csv')
    def photo_inventory(project_id: str):
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(['记录ID', '位置', '照片ID', '原文件名', '说明', '顺序', 'SHA256'])
        def safe(value):
            value = str(value)
            return "'" + value if value.startswith(('=', '+', '-', '@', '\t', '\r')) else value
        with store.connect() as conn:
            project_or_404(conn, project_id)
            for finding in current_findings(conn, project_id):
                for p in finding['photos']:
                    writer.writerow([safe(v) for v in (finding['id'], finding['location'], p['id'], p['filename'], p['caption'], p['position'], p['sha256'])])
        return Response(stream.getvalue().encode('utf-8-sig'), media_type='text/csv',
                        headers={'Content-Disposition': 'attachment; filename="photo-inventory.csv"'})

    def report_dict(row):
        snapshot = json.loads(row['snapshot'])
        return {'id': row['id'], 'project_id': row['project_id'], 'mode': row['mode'], 'created_at': row['created_at'],
                'docx_url': f'/api/reports/{row["id"]}/docx', 'pdf_url': f'/api/reports/{row["id"]}/pdf',
                'snapshot_url': f'/api/reports/{row["id"]}/snapshot', 'pdf_engine': row['pdf_engine'],
                'excluded_count': snapshot.get('excluded_count', 0), 'finding_count': len(snapshot['findings'])}

    @app.get('/api/projects/{project_id}/reports')
    def list_reports(project_id: str):
        with store.connect() as conn:
            project_or_404(conn, project_id)
            return [report_dict(row) for row in conn.execute(
                'SELECT * FROM reports WHERE project_id=? ORDER BY created_at DESC,rowid DESC', (project_id,))]

    @app.post('/api/projects/{project_id}/reports', status_code=201)
    def create_report(project_id: str, payload: dict):
        from .reporting import generate_reports
        mode = payload.get('mode', 'confirmed')
        if mode not in ('confirmed', 'draft'):
            raise HTTPException(422, '报告类型无效')
        with store.lock, store.connect() as conn:
            project = project_or_404(conn, project_id)
            all_findings = current_findings(conn, project_id)
            findings = [f for f in all_findings if mode == 'draft' or f['status'] == 'confirmed']
            if not findings:
                raise HTTPException(409, '没有可导出的记录；请完成审核或选择草稿报告')
            if mode == 'confirmed':
                invalid = [reason for finding in findings for reason in finding['blockers']]
                if invalid:
                    raise HTTPException(409, {'message': '正式报告中的记录需要重新核实依据或事实；历史报告仍可下载', 'blockers': invalid})
            rid, stamp = uid('REP'), now()
            # Embed image locations in the immutable snapshot; only generated IDs are paths.
            for finding in findings:
                for photo in finding['photos']:
                    photo['path'] = conn.execute('SELECT path FROM photos WHERE id=?', (photo['id'],)).fetchone()[0]
            snapshot = {'schema_version': 1, 'id': rid, 'created_at': stamp, 'mode': mode,
                        'project': project, 'findings': findings, 'excluded_count': len(all_findings) - len(findings),
                        'knowledge': knowledge.call('meta'), 'template_version': 'inspection-v1'}
            out = store.root / 'reports' / rid
            out.mkdir(parents=True, exist_ok=False)
            try:
                generated = generate_reports(snapshot, store.root, out)
            except Exception:
                shutil.rmtree(out, ignore_errors=True)
                raise
            snapshot['template_version'] = generated['template_version']
            (out / 'snapshot.json').write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding='utf-8')
            conn.execute('INSERT INTO reports VALUES(?,?,?,?,?,?,?,?)', (
                rid, project_id, mode, dumps(snapshot), stamp,
                str(generated['docx'].relative_to(store.root)), str(generated['pdf'].relative_to(store.root)), generated['pdf_engine'],
            ))
            store.audit(conn, project_id, 'report_exported', {'report_id': rid, 'mode': mode, 'findings': len(findings)})
            return report_dict(conn.execute('SELECT * FROM reports WHERE id=?', (rid,)).fetchone())

    @app.get('/api/reports/{report_id}/{kind}')
    def report_download(report_id: str, kind: str):
        if kind not in ('docx', 'pdf', 'snapshot'):
            raise HTTPException(404, '报告格式不存在')
        with store.connect() as conn:
            row = conn.execute('SELECT * FROM reports WHERE id=?', (report_id,)).fetchone()
            if row is None:
                raise HTTPException(404, '报告不存在')
            if kind == 'snapshot':
                return Response(row['snapshot'], media_type='application/json', headers={'Content-Disposition': 'attachment; filename="report-snapshot.json"'})
            media = 'application/pdf' if kind == 'pdf' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            return FileResponse(store.root / row[kind + '_path'], media_type=media, filename=f'inspection-{report_id[-8:]}.{kind}')

    @app.get('/api/findings/{finding_id}/audit')
    def finding_audit(finding_id: str):
        with store.connect() as conn:
            finding_or_404(conn, finding_id)
            return [{**dict(r), 'detail': json.loads(r['detail'])} for r in conn.execute(
                'SELECT * FROM audit WHERE entity_id=? ORDER BY created_at,rowid', (finding_id,))]

    @app.get('/api/backup')
    def backup():
        from .backup import create_backup
        target = create_backup(store)
        return FileResponse(target, media_type='application/zip', filename=target.name)

    @app.post('/api/demo', status_code=201)
    def demo():
        from .demo import demo_photo
        project = create_project(ProjectInput(company='示例制造企业（脱敏演示）', name='综合安全检查示例',
            inspection_date=date.today(), inspectors='示例检查人', purpose='合成样例，仅演示工作流程'))
        finding = create_finding(project['id'], FindingInput(location='示例车间东侧灭火器点位', equipment='储压式灭火器',
            observation='演示观察：压力指示器指针位于欠压区域。此处为合成样例，不代表真实企业情况。',
            description='示例车间东侧配置的储压式灭火器压力指示器指针位于欠压区域，未保持完好有效。',
            rectification='以符合要求的灭火器替换失压器材，并组织检修，完善巡查和更换记录。'))
        add_basis(finding['id'], BasisInput(hazard_id='H001'))
        with store.lock, store.connect() as conn:
            finding = finding_or_404(conn, finding['id'])
            persist_photo(conn, finding, demo_photo(), 'synthetic-demo.jpg', '合成演示图片，不是现场证据')
        return {'project': get_project(project['id']), 'finding': get_finding(finding['id'])}

    frontend = ROOT / 'workbench/frontend'
    if frontend.is_dir():
        app.mount('/', StaticFiles(directory=frontend, html=True), name='workbench')
    return app
