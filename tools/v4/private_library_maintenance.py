#!/usr/bin/env python3
"""Safely audit and repair the private full-text SQLite search index.

This tool intentionally does not merge/delete documents or touch archive files.
It supports two operations:

* audit: read-only integrity/count/content-digest report.
* rebuild-fts: create a SQLite-consistent backup, rebuild only the FTS5 index,
  then verify strong before/after invariants.

The private full-text database is a search aid, not the legal authority source.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any, Iterable

EXPECTED_FORMAT = "safety-fulltext-v1"
EXPECTED_SCHEMA_VERSION = "1"


def _db_path(value: Path) -> Path:
    p = value.expanduser().resolve()
    if p.is_dir():
        p = p / "fulltext.sqlite3"
    if not p.is_file():
        raise ValueError(f"全文库不存在: {p}")
    return p


def _readonly(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _validate_schema(conn: sqlite3.Connection) -> None:
    tables = {
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    required = {"fulltext_meta", "documents", "fulltext_fts"}
    missing = required - tables
    if missing:
        raise ValueError(f"不是 safety fulltext 数据库，缺少表: {sorted(missing)}")
    meta = dict(conn.execute("SELECT key, value FROM fulltext_meta"))
    if meta.get("format") != EXPECTED_FORMAT:
        raise ValueError(f"全文库 format 不支持: {meta.get('format')!r}")
    if meta.get("schemaVersion") != EXPECTED_SCHEMA_VERSION:
        raise ValueError(f"全文库 schemaVersion 不支持: {meta.get('schemaVersion')!r}")


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _content_digest(conn: sqlite3.Connection) -> str:
    """Digest user-visible FTS rows, independent of inverted-index bytes."""
    h = hashlib.sha256()
    # FTS rowid is stable across an in-place `rebuild`; ordering by rowid avoids
    # a large sort on 200k+ paragraphs while still detecting content-row change.
    cur = conn.execute(
        "SELECT rowid, document_key, paragraph_no, title, version, content "
        "FROM fulltext_fts ORDER BY rowid"
    )
    for row in cur:
        parts = (
            str(row["rowid"]),
            str(row["document_key"] or ""),
            str(row["paragraph_no"] or ""),
            str(row["title"] or ""),
            str(row["version"] or ""),
            str(row["content"] or ""),
        )
        h.update(("\x1e".join(parts) + "\x1f").encode("utf-8"))
    return h.hexdigest()


def audit(db_value: Path, *, include_file_sha: bool = True) -> dict[str, Any]:
    db = _db_path(db_value)
    conn = _readonly(db)
    try:
        _validate_schema(conn)
        integrity = [row[0] for row in conn.execute("PRAGMA integrity_check")]
        fk_errors = len(conn.execute("PRAGMA foreign_key_check").fetchall())
        documents = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        fts_rows = conn.execute("SELECT COUNT(*) FROM fulltext_fts").fetchone()[0]
        paragraph_sum = conn.execute(
            "SELECT COALESCE(SUM(paragraph_count),0) FROM documents"
        ).fetchone()[0]
        mismatches = [
            dict(row) for row in conn.execute(
                """
                SELECT d.document_key, d.paragraph_count, COUNT(f.rowid) AS fts_count
                FROM documents AS d
                LEFT JOIN fulltext_fts AS f ON f.document_key=d.document_key
                GROUP BY d.document_key
                HAVING fts_count<>d.paragraph_count
                ORDER BY d.document_key
                """
            )
        ]
        duplicate_sha_groups = conn.execute(
            "SELECT COUNT(*) FROM (SELECT sha256 FROM documents GROUP BY sha256 HAVING COUNT(*)>1)"
        ).fetchone()[0]
        duplicate_document_rows = conn.execute(
            "SELECT COALESCE(SUM(n),0) FROM (SELECT COUNT(*) AS n FROM documents GROUP BY sha256 HAVING COUNT(*)>1)"
        ).fetchone()[0]
        result: dict[str, Any] = {
            "ok": True,
            "database": str(db),
            "fileSize": db.stat().st_size,
            "integrity": integrity,
            "foreignKeyErrors": fk_errors,
            "documents": documents,
            "ftsRows": fts_rows,
            "paragraphCountSum": paragraph_sum,
            "perDocumentParagraphMismatches": mismatches,
            "duplicateShaGroups": duplicate_sha_groups,
            "duplicateDocumentRows": duplicate_document_rows,
            "ftsContentSha256": _content_digest(conn),
        }
    finally:
        conn.close()
    if include_file_sha:
        result["databaseFileSha256"] = _file_sha256(db)
    return result


def _timestamp() -> str:
    return dt.datetime.now().astimezone().strftime("%Y%m%d-%H%M%S%z")


def backup_database(db_value: Path, backup_dir: Path) -> tuple[Path, dict[str, Any]]:
    db = _db_path(db_value)
    backup_dir = backup_dir.expanduser().resolve()
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"fulltext.sqlite3.bak-{_timestamp()}"
    if target.exists():
        raise ValueError(f"备份目标已存在: {target}")

    source = _readonly(db)
    try:
        _validate_schema(source)
        dest = sqlite3.connect(target)
        try:
            source.backup(dest)
            dest.commit()
        finally:
            dest.close()
    finally:
        source.close()

    report = audit(target, include_file_sha=True)
    return target, report


def _same_content_invariants(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("documents", "ftsRows", "paragraphCountSum", "ftsContentSha256"):
        if before.get(key) != after.get(key):
            errors.append(f"{key} 变化: {before.get(key)!r} -> {after.get(key)!r}")
    if before.get("ftsRows") != before.get("paragraphCountSum"):
        errors.append("修复前 ftsRows 与 paragraphCountSum 不一致")
    if after.get("ftsRows") != after.get("paragraphCountSum"):
        errors.append("修复后 ftsRows 与 paragraphCountSum 不一致")
    if before.get("perDocumentParagraphMismatches"):
        errors.append("修复前存在逐 document 段落计数不一致")
    if after.get("perDocumentParagraphMismatches"):
        errors.append("修复后存在逐 document 段落计数不一致")
    if after.get("foreignKeyErrors"):
        errors.append(f"修复后 foreign_key_check={after['foreignKeyErrors']}")
    if after.get("integrity") != ["ok"]:
        errors.append(f"修复后 integrity_check 非 ok: {after.get('integrity')!r}")
    return errors


def rebuild_fts(db_value: Path, backup_dir: Path) -> dict[str, Any]:
    db = _db_path(db_value)
    before = audit(db, include_file_sha=True)
    backup_path, backup_report = backup_database(db, backup_dir)

    # SQLite Backup API produces a logical snapshot, so its file bytes may
    # differ. Semantic invariants must match. The backup intentionally preserves
    # the pre-rebuild FTS corruption, so an integrity error there is expected.
    backup_errors = _same_content_invariants(before, backup_report)
    backup_errors = [
        error for error in backup_errors
        if not error.startswith("修复后 integrity_check")
    ]
    if backup_errors:
        raise RuntimeError("备份语义核验失败: " + "; ".join(backup_errors))

    conn = sqlite3.connect(db)
    try:
        _validate_schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("INSERT INTO fulltext_fts(fulltext_fts) VALUES('rebuild')")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    after = audit(db, include_file_sha=True)
    errors = _same_content_invariants(before, after)
    return {
        "ok": not errors,
        "operation": "rebuild-fts",
        "backup": str(backup_path),
        "before": before,
        "backupAudit": backup_report,
        "after": after,
        "invariantErrors": errors,
        "manualRestoreRequired": bool(errors),
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database", type=Path, required=True,
        help="fulltext.sqlite3 文件或包含它的 source/library 目录",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    audit_cmd = commands.add_parser("audit", help="只读完整性与内容摘要审计")
    audit_cmd.add_argument(
        "--skip-file-sha", action="store_true",
        help="跳过数据库文件本身的 SHA-256（不影响全文内容摘要）",
    )
    rebuild_cmd = commands.add_parser(
        "rebuild-fts", help="备份后仅重建 FTS5 倒排索引"
    )
    rebuild_cmd.add_argument(
        "--backup-dir", type=Path, required=True,
        help="私有备份目录；必须位于 Git 管理范围之外或 gitignored 路径",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        if args.command == "audit":
            result = audit(args.database, include_file_sha=not args.skip_file_sha)
        else:
            result = rebuild_fts(args.database, args.backup_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 2
    except Exception as exc:
        print(
            json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
