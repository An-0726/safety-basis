"""Local, private full-text storage for official document snapshots.

The input is a private manifest with this shape::

    {"schemaVersion": "safety-fulltext-manifest-v1", "documents": [
      {"documentId": "GB50016", "title": "...", "version": "2014",
       "officialUrl": "https://...", "snapshotPath": "./GB50016.pdf",
       "asOf": "2026-09-09", "currentStatus": "现行有效",
       "reviewStatus": "待核验"}
    ]}

``snapshotPath`` is read only and is never stored in the library.  A document
is eligible to be presented as a current basis only when both its current
status and its explicit review status pass the conservative checks below.
The library is deliberately separate from the safety master and public data.
"""
from __future__ import annotations

import argparse
import datetime as dt
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterable

import exchange
import legal_text
import review


FORMAT = "safety-fulltext-v1"
MANIFEST_SCHEMA = "safety-fulltext-manifest-v1"
SCHEMA_VERSION = "1"
DEFAULT_REVIEW_STATUS = "待核验"
PASS_REVIEW_STATUSES = {"passed", "已通过", "已核验"}
CURRENT_STATUSES = {"current", "active", "现行有效", "现行", "现行使用中"}
REQUIRED_DOCUMENT_FIELDS = {
    "documentId", "title", "version", "officialUrl", "snapshotPath",
    "asOf", "currentStatus",
}
OPTIONAL_DOCUMENT_FIELDS = {"reviewStatus"}


class _HtmlParagraphs(HTMLParser):
    """Small HTML adapter that keeps block boundaries for search locations."""

    BLOCKS = {
        "address", "article", "aside", "blockquote", "br", "dd", "div",
        "dl", "dt", "footer", "h1", "h2", "h3", "h4", "h5", "h6",
        "header", "hr", "li", "main", "nav", "ol", "p", "pre", "section",
        "table", "td", "th", "tr", "ul",
    }

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.current: list[str] = []
        self.skip = 0

    def _flush(self) -> None:
        text = "".join(self.current).strip()
        if text:
            self.parts.append(text)
        self.current = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript"}:
            self._flush()
            self.skip += 1
        elif not self.skip and tag in self.BLOCKS:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript"} and self.skip:
            self.skip -= 1
        elif not self.skip and tag in self.BLOCKS:
            self._flush()

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.current.append(data)

    def finish(self) -> list[str]:
        self._flush()
        return self.parts


def _normal_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _official_url(value: Any) -> str:
    url = _normal_text(value)
    if not re.match(r"^https?://[^\s]+$", url, flags=re.IGNORECASE):
        raise ValueError("officialUrl 必须是 http(s) URL")
    return url


def _date(value: Any, field: str) -> str:
    text = _normal_text(value)
    try:
        parsed = dt.date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field} 必须为 YYYY-MM-DD") from exc
    if parsed > dt.date.today() + dt.timedelta(days=1):
        raise ValueError(f"{field} 不能晚于当前日期")
    return parsed.isoformat()


def _document_key(document_id: str, version: str) -> str:
    return document_id + "\x1f" + version


def _decode_text(blob: bytes) -> str:
    try:
        return blob.decode("utf-8-sig")
    except UnicodeDecodeError:
        return blob.decode("gb18030")


def extract_paragraphs(blob: bytes) -> list[str]:
    """Extract non-empty searchable paragraphs from DOCX, PDF, HTML or text."""
    if not blob:
        raise ValueError("原件为空")
    if blob.startswith(b"PK"):
        paragraphs = legal_text.paragraphs(blob)
    elif blob.startswith(b"%PDF"):
        # review.snapshot_text uses pypdf and preserves page text boundaries.
        paragraphs = review.snapshot_text(blob).splitlines()
    else:
        decoded = _decode_text(blob)
        parser = _HtmlParagraphs()
        if re.search(r"<\s*(html|body|p|div|article|section|h[1-6])(?:\s|>)", decoded, re.I):
            parser.feed(decoded)
            paragraphs = parser.finish()
        else:
            paragraphs = decoded.splitlines()
    cleaned = [re.sub(r"\s+", " ", str(value)).strip() for value in paragraphs]
    cleaned = [value for value in cleaned if value]
    if not cleaned:
        raise ValueError("原件无法提取非空文本；扫描件需提供可提取文本适配器")
    return cleaned


def _dangerous_library(path: Path) -> bool:
    parts = {part.lower() for part in path.parts}
    if path.name.lower() == "safety.sqlite3":
        return True
    # Reject the repository's master/staging locations even when a caller
    # supplies a path through a symlink or relative spelling.
    return "source" in parts and bool(parts & {"master", "staging"})


def _library_db(library: Path) -> Path:
    library = Path(library).expanduser().resolve()
    if _dangerous_library(library):
        raise ValueError("全文库路径不能指向 safety master/staging")
    if library.exists() and not library.is_dir():
        raise ValueError("--library 必须是全文库目录")
    library.mkdir(parents=True, exist_ok=True)
    return library / "fulltext.sqlite3"


def _schema(conn: sqlite3.Connection, *, create: bool) -> None:
    row = conn.execute(
        "SELECT value FROM fulltext_meta WHERE key='schemaVersion'"
    ).fetchone() if _has_table(conn, "fulltext_meta") else None
    if row and row[0] != SCHEMA_VERSION:
        raise ValueError(f"全文库 schemaVersion 不支持: {row[0]}")
    format_row = conn.execute(
        "SELECT value FROM fulltext_meta WHERE key='format'"
    ).fetchone() if _has_table(conn, "fulltext_meta") else None
    if format_row and format_row[0] != FORMAT:
        raise ValueError(f"全文库 format 不支持: {format_row[0]}")
    if not create and not row:
        raise ValueError("已有库不是 safety-fulltext schema，拒绝写入")
    if not row:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS fulltext_meta (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );
            INSERT INTO fulltext_meta(key,value) VALUES
              ('schemaVersion','1'), ('format','safety-fulltext-v1');
            CREATE TABLE IF NOT EXISTS documents (
              document_key TEXT PRIMARY KEY,
              document_id TEXT NOT NULL,
              title TEXT NOT NULL,
              version TEXT NOT NULL,
              official_url TEXT NOT NULL,
              as_of TEXT NOT NULL,
              current_status TEXT NOT NULL,
              review_status TEXT NOT NULL,
              sha256 TEXT NOT NULL,
              text_sha256 TEXT NOT NULL,
              paragraph_count INTEGER NOT NULL,
              archive_ref TEXT NOT NULL,
              imported_at TEXT NOT NULL,
              UNIQUE(document_id, version)
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS fulltext_fts USING fts5(
              document_key UNINDEXED,
              paragraph_no UNINDEXED,
              title,
              version,
              content,
              tokenize='trigram'
            );
            """
        )


def _has_table(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=?", (name,)
    ).fetchone() is not None


def _connect(library: Path, *, create: bool = True) -> tuple[sqlite3.Connection, Path]:
    db = _library_db(library)
    existed = db.exists()
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        _schema(conn, create=create and not existed)
        conn.commit()
    except Exception:
        conn.close()
        raise
    return conn, db


def _manifest(path: Path) -> list[dict[str, str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"清单无法读取: {path}") from exc
    if not isinstance(payload, dict) or payload.get("schemaVersion") != MANIFEST_SCHEMA:
        raise ValueError(f"清单 schemaVersion 必须为 {MANIFEST_SCHEMA}")
    docs = payload.get("documents")
    if not isinstance(docs, list):
        raise ValueError("清单 documents 必须为数组")
    result: list[dict[str, str]] = []
    for ordinal, item in enumerate(docs, 1):
        if not isinstance(item, dict):
            raise ValueError(f"documents[{ordinal}] 必须为对象")
        unknown = set(item) - REQUIRED_DOCUMENT_FIELDS - OPTIONAL_DOCUMENT_FIELDS
        missing = REQUIRED_DOCUMENT_FIELDS - set(item)
        if missing or unknown:
            raise ValueError(f"documents[{ordinal}] 字段无效；缺少={sorted(missing)} 未知={sorted(unknown)}")
        values = {field: _normal_text(item[field]) for field in REQUIRED_DOCUMENT_FIELDS}
        if any(not values[field] for field in REQUIRED_DOCUMENT_FIELDS):
            raise ValueError(f"documents[{ordinal}] 必填字段不能为空")
        values["officialUrl"] = _official_url(values["officialUrl"])
        values["asOf"] = _date(values["asOf"], "asOf")
        values["reviewStatus"] = _normal_text(item.get("reviewStatus")) or DEFAULT_REVIEW_STATUS
        if "documentId" in values and "version" in values:
            result.append(values)
    keys = [_document_key(item["documentId"], item["version"]) for item in result]
    if len(keys) != len(set(keys)):
        raise ValueError("清单中存在重复 documentId+version")
    return result


def _archive_blob(library: Path, blob: bytes, sha256: str) -> str:
    archive_dir = Path(library).resolve() / "archive" / sha256
    archive_ref = Path("archive") / sha256 / "original"
    destination = archive_dir / "original"
    archive_dir.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if not destination.is_file() or exchange.sha256_bytes(destination.read_bytes()) != sha256:
            raise ValueError(f"全文库原件归档损坏: {archive_ref.as_posix()}")
    else:
        exchange.install_output(destination, blob)
    return archive_ref.as_posix()


def _eligible(current_status: str, review_status: str) -> bool:
    return current_status.strip() in CURRENT_STATUSES and review_status.strip() in PASS_REVIEW_STATUSES


def _literal_fts_query(value: str) -> str:
    # Search is literal by default; callers do not get to inject FTS operators.
    return '"' + value.replace('"', '""') + '"'


def _like_pattern(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _like_snippet(text: str, query: str) -> str:
    folded, needle = text.casefold(), query.casefold()
    start = folded.find(needle)
    if start < 0:
        return text[:180]
    left, right = max(0, start - 72), min(len(text), start + len(query) + 108)
    prefix = "…" if left else ""
    suffix = "…" if right < len(text) else ""
    offset = start - left
    end = offset + len(query)
    return prefix + text[left:left + offset] + "[" + text[left + offset:left + end] + "]" + text[left + end:right] + suffix


def import_manifest(library: Path, manifest: Path) -> dict[str, Any]:
    """Import snapshots, returning counts without exposing source paths."""
    library = Path(library).expanduser().resolve()
    manifest = Path(manifest).expanduser().resolve()
    docs = _manifest(manifest)
    prepared: list[dict[str, Any]] = []
    for doc in docs:
        source = Path(doc["snapshotPath"])
        if not source.is_absolute():
            source = manifest.parent / source
        if not source.is_file():
            raise ValueError(f"原件不存在: {doc['documentId']}@{doc['version']}")
        blob = source.read_bytes()
        paragraphs = extract_paragraphs(blob)
        prepared.append({
            **doc,
            "blob": blob,
            "sha256": exchange.sha256_bytes(blob),
            "text_sha256": exchange.sha256_bytes("\n".join(paragraphs).encode("utf-8")),
            "paragraphs": paragraphs,
            "document_key": _document_key(doc["documentId"], doc["version"]),
        })
    conn, db = _connect(library, create=True)
    added = already = 0
    try:
        conn.execute("BEGIN IMMEDIATE")
        for doc in prepared:
            key = doc["document_key"]
            existing = conn.execute("SELECT * FROM documents WHERE document_key=?", (key,)).fetchone()
            if existing:
                if existing["sha256"] != doc["sha256"]:
                    raise ValueError(f"版本冲突：{doc['documentId']}@{doc['version']} 已存在不同 SHA")
                archive_path = db.parent / existing["archive_ref"]
                if not archive_path.is_file() or exchange.sha256_bytes(archive_path.read_bytes()) != existing["sha256"]:
                    raise ValueError(f"全文库原件归档缺失或损坏：{existing['archive_ref']}")
                already += 1
                continue
            archive_ref = _archive_blob(db.parent, doc["blob"], doc["sha256"])
            conn.execute(
                "INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (key, doc["documentId"], doc["title"], doc["version"], doc["officialUrl"],
                 doc["asOf"], doc["currentStatus"], doc["reviewStatus"], doc["sha256"],
                 doc["text_sha256"], len(doc["paragraphs"]), archive_ref, exchange.utc_now()),
            )
            conn.executemany(
                "INSERT INTO fulltext_fts(document_key,paragraph_no,title,version,content) VALUES(?,?,?,?,?)",
                [(key, number, doc["title"], doc["version"], text)
                 for number, text in enumerate(doc["paragraphs"], 1)],
            )
            added += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {"ok": True, "format": FORMAT, "added": added, "alreadyImported": already,
            "documentCount": len(prepared)}


def search(library: Path, query: str, limit: int = 20) -> list[dict[str, Any]]:
    """Search staged and reviewed text; every result states its eligibility."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("搜索词不能为空")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit 必须为 1..100")
    conn, _ = _connect(Path(library), create=False)
    try:
        literal = query.strip()
        try:
            rows = conn.execute(
                """
                SELECT d.*, f.paragraph_no,
                       snippet(fulltext_fts, 4, '[', ']', '…', 24) AS hit
                FROM fulltext_fts AS f
                JOIN documents AS d ON d.document_key=f.document_key
                WHERE fulltext_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """, (_literal_fts_query(literal), limit),
            ).fetchall()
        except sqlite3.OperationalError as exc:
            raise ValueError(f"搜索词不是有效的 FTS5 查询: {query}") from exc
        # SQLite's trigram tokenizer intentionally does not index one- or
        # two-character terms. A literal LIKE fallback keeps short Chinese
        # searches useful and also handles punctuation-heavy queries.
        if len(literal) < 3 or not rows:
            rows = conn.execute(
                """
                SELECT d.*, f.paragraph_no, f.content
                FROM fulltext_fts AS f
                JOIN documents AS d ON d.document_key=f.document_key
                WHERE f.content LIKE ? ESCAPE '\\'
                ORDER BY d.document_id, d.version, f.paragraph_no
                LIMIT ?
                """, (f"%{_like_pattern(literal)}%", limit),
            ).fetchall()
            return [{
                "documentId": row["document_id"], "title": row["title"], "version": row["version"],
                "officialUrl": row["official_url"], "asOf": row["as_of"],
                "currentStatus": row["current_status"], "reviewStatus": row["review_status"],
                "eligibleAsCurrentBasis": _eligible(row["current_status"], row["review_status"]),
                "basisStatus": "已核验现行" if _eligible(row["current_status"], row["review_status"])
                               else "仅全文参考（未核验或非现行）",
                "location": f"paragraph:{row['paragraph_no']}",
                "snippet": _like_snippet(row["content"], literal),
                "sha256": row["sha256"], "archiveRef": row["archive_ref"],
            } for row in rows]
        return [{
            "documentId": row["document_id"], "title": row["title"], "version": row["version"],
            "officialUrl": row["official_url"], "asOf": row["as_of"],
            "currentStatus": row["current_status"], "reviewStatus": row["review_status"],
            "eligibleAsCurrentBasis": _eligible(row["current_status"], row["review_status"]),
            "basisStatus": "已核验现行" if _eligible(row["current_status"], row["review_status"])
                           else "仅全文参考（未核验或非现行）",
            "location": f"paragraph:{row['paragraph_no']}", "snippet": row["hit"],
            "sha256": row["sha256"], "archiveRef": row["archive_ref"],
        } for row in rows]
    finally:
        conn.close()


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path, required=True, help="独立全文库目录")
    commands = parser.add_subparsers(dest="command", required=True)
    import_cmd = commands.add_parser("import", help="导入私有 JSON 清单及原件")
    import_cmd.add_argument("--manifest", type=Path, required=True)
    search_cmd = commands.add_parser("search", help="搜索全文库")
    search_cmd.add_argument("--query", required=True)
    search_cmd.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "import":
        result = import_manifest(args.library, args.manifest)
    else:
        result = search(args.library, args.query, args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    main()
