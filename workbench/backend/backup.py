"""Consistent SQLite backups. Restore into a new, empty private directory."""
import json
import os
import sqlite3
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from .storage import now, uid, private_data_root


def create_backup(store):
    target = store.root / 'backups' / (uid('workbench-backup') + '.zip')
    with store.lock, tempfile.TemporaryDirectory() as temp:
        database = Path(temp) / 'workbench.sqlite3'
        with store.connect() as source, sqlite3.connect(database) as destination:
            source.backup(destination)
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.write(database, 'workbench.sqlite3')
            for folder in ('photos', 'reports', 'templates'):
                for path in sorted((store.root / folder).rglob('*')):
                    if path.is_file() and not path.is_symlink():
                        archive.write(path, path.relative_to(store.root).as_posix())
            archive.writestr('backup.json', json.dumps({
                'schema_version': 1, 'created_at': now(), 'private_data': True,
                'restore': 'python -m workbench restore FILE --data-dir NEW_EMPTY_DIRECTORY',
            }, ensure_ascii=False, indent=2))
    try:
        os.chmod(target, 0o600)
    except OSError:
        pass
    return target


def restore_backup(source, destination):
    destination = private_data_root(destination)
    if destination.exists() and any(destination.iterdir()):
        raise ValueError('恢复目标必须是空目录，以免覆盖正在使用的数据库')
    with zipfile.ZipFile(source) as archive:
        if 'workbench.sqlite3' not in archive.namelist() or 'backup.json' not in archive.namelist():
            raise ValueError('不是工作台备份文件')
        meta = json.loads(archive.read('backup.json'))
        if meta.get('schema_version') != 1:
            raise ValueError('不支持的备份版本')
        total = 0
        for member in archive.infolist():
            path = PurePosixPath(member.filename)
            if path.is_absolute() or '..' in path.parts or '\\' in member.filename or ':' in member.filename:
                raise ValueError('备份含有不安全路径')
            if (member.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('备份不能包含符号链接')
            if path.parts[0] not in ('workbench.sqlite3', 'backup.json', 'photos', 'reports', 'templates'):
                raise ValueError('备份含有未支持的文件')
            total += member.file_size
        if total > 10 * 1024 ** 3:
            raise ValueError('解压后备份超过10GB，请人工核对后迁移')
        destination.mkdir(parents=True, exist_ok=True, mode=0o700)
        archive.extractall(destination)
    with sqlite3.connect(destination / 'workbench.sqlite3') as conn:
        if conn.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('备份数据库完整性校验失败')
        if conn.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('备份数据库引用完整性校验失败')
    return destination
