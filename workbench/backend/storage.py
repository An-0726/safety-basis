"""Local business records, separated from the public knowledge repository."""
import json
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def uid(prefix):
    return prefix + '_' + uuid.uuid4().hex


def dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def private_data_root(value):
    """Apply the same private path boundary to serving, backup and restore."""
    root = Path(value).resolve()
    repository = Path(__file__).resolve().parents[2]
    if root == repository or repository in root.parents:
        allowed = [repository / item for item in ('workbench/runtime', 'workbench/private', 'workbench-data', 'tmp')]
        if not any(root == item or item in root.parents for item in allowed):
            raise ValueError('私有工作台数据只能保存在仓库外或已忽略的私有运行目录，不能写入公开仓库路径')
    return root


class Store:
    def __init__(self, root):
        self.root = private_data_root(root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        for folder in ('photos', 'reports', 'backups', 'templates'):
            (self.root / folder).mkdir(exist_ok=True, mode=0o700)
        self.lock = threading.RLock()
        self.database = self.root / 'workbench.sqlite3'
        with self.connect() as conn:
            conn.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS projects (
              id TEXT PRIMARY KEY, body TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS findings (
              id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
              body TEXT NOT NULL, position INTEGER NOT NULL DEFAULT 0,
              revision INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS finding_project ON findings(project_id, position);
            CREATE TABLE IF NOT EXISTS photos (
              id TEXT PRIMARY KEY, finding_id TEXT NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
              filename TEXT NOT NULL, path TEXT NOT NULL, caption TEXT NOT NULL DEFAULT '',
              position INTEGER NOT NULL DEFAULT 0, sha256 TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS reviews (
              id TEXT PRIMARY KEY, finding_id TEXT NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
              decision TEXT NOT NULL, reviewer TEXT NOT NULL, comment TEXT NOT NULL,
              revision INTEGER NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS reports (
              id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
              mode TEXT NOT NULL, snapshot TEXT NOT NULL, created_at TEXT NOT NULL,
              docx_path TEXT NOT NULL, pdf_path TEXT NOT NULL, pdf_engine TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS audit (
              id TEXT PRIMARY KEY, entity_id TEXT NOT NULL, action TEXT NOT NULL,
              actor TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL);
            PRAGMA user_version=1;
            ''')
        try:
            os.chmod(self.database, 0o600)
        except OSError:
            pass

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.database, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def audit(self, conn, entity, action, detail=None, actor='本机操作人'):
        conn.execute('INSERT INTO audit VALUES(?,?,?,?,?,?)',
                     (uid('A'), entity, action, actor, dumps(detail or {}), now()))

    @staticmethod
    def project(row):
        if row is None:
            return None
        return {**json.loads(row['body']), 'id': row['id'], 'created_at': row['created_at'],
                'updated_at': row['updated_at']}

    @staticmethod
    def finding(row):
        if row is None:
            return None
        return {**json.loads(row['body']), 'id': row['id'], 'project_id': row['project_id'],
                'position': row['position'], 'revision': row['revision'],
                'created_at': row['created_at'], 'updated_at': row['updated_at']}

    def save_finding(self, conn, finding, action, actor='本机操作人'):
        body = {k: v for k, v in finding.items() if k not in {
            'id', 'project_id', 'created_at', 'updated_at', 'position', 'revision',
            'photos', 'reviews', 'blockers', 'audit',
        }}
        conn.execute('UPDATE findings SET body=?,position=?,revision=revision+1,updated_at=? WHERE id=?',
                     (dumps(body), finding['position'], now(), finding['id']))
        conn.execute('UPDATE projects SET updated_at=? WHERE id=?', (now(), finding['project_id']))
        self.audit(conn, finding['id'], action,
                   {'revision': finding['revision'] + 1, 'status': finding['status'], 'body': body}, actor)


def blockers(finding):
    reasons = []
    if not finding.get('observation', '').strip():
        reasons.append('请填写现场原话和观察记录')
    if not finding.get('description', '').strip():
        reasons.append('请填写经核实的专业隐患描述')
    if not finding.get('rectification', '').strip():
        reasons.append('请填写对应整改建议')
    if not finding.get('bases'):
        reasons.append('尚未选定正式条款；缺证记录可保存为草稿，不可确认')
    by_hazard = {}
    for basis in finding.get('bases', []):
        by_hazard.setdefault(basis['hazard_id'], []).append(basis)
    for hazard_id, bases in by_hazard.items():
        if not any(b.get('role') in ('direct', 'fallback') for b in bases):
            reasons.append(f'{hazard_id} 仅选择了辅助依据，请选入直接或兜底依据后审核')
    for fact in finding.get('facts', []):
        valid = fact['status'] == fact.get('expected', 'confirmed') or (
            fact.get('allows_denied', False) and fact['status'] == 'denied')
        if not valid:
            reasons.append('待核实：' + fact['label'])
        elif not fact.get('note', '').strip():
            reasons.append('请记录核实依据：' + fact['label'])
    if any(b.get('inspection_class') == 'document_review' for b in finding.get('bases', [])):
        if finding.get('finding_kind') != 'document_review':
            reasons.append('该依据用于资料核查，请将记录类型改为“资料核查”并核实资料缺口')
    return reasons


def invalidate(finding, reset_facts=False):
    if finding['status'] in ('confirmed', 'pending_review', 'rejected'):
        finding['status'] = 'draft'
    if reset_facts:
        for fact in finding.get('facts', []):
            fact['status'] = 'unknown'
            fact['note'] = ''
