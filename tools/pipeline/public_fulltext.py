"""Evidence-gated export of reviewed legal full text.

This command is intentionally separate from :mod:`fulltext`: a private search
index may contain pending text, while this exporter reads the master database
and requires current law/version proofs, matching evidence bytes, a review
checklist and an explicit publication permission before writing public output.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import unicodedata
from typing import Any, Iterable

import exchange
import fulltext
import legal_text
import master
import verification


FORMAT = "safety-public-fulltext-v1"
CHECKLIST_SCHEMA = "safety-public-fulltext-checklist-v1"
TEXT_SCHEMA = "safety-public-fulltext-text-v1"
SEARCH_SCHEMA = "safety-public-fulltext-search-v1"
GRAM_SCHEMA = "safety-public-fulltext-grams-v1"
PERMISSIONS = {"official_legal_text", "explicit_permission", "metadata_only"}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
ITEM_FIELDS = {
    "lawId", "versionId", "fullTextSha256", "evidenceId", "publicationPermission",
    "permissionReason", "permissionSource", "fullTextReviewed", "reviewer", "reviewedAt",
}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"JSON 无法读取: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError("JSON 根必须是对象")
    return value


def _checklist(path: Path) -> list[dict[str, Any]]:
    payload = _read_json(path)
    if payload.get("schemaVersion") != CHECKLIST_SCHEMA or set(payload) != {"schemaVersion", "documents"}:
        raise ValueError(f"清单 schemaVersion 必须为 {CHECKLIST_SCHEMA} 且只含 documents")
    documents = payload["documents"]
    if not isinstance(documents, list):
        raise ValueError("清单 documents 必须为数组")
    result = []
    seen: set[tuple[str, str]] = set()
    for ordinal, item in enumerate(documents, 1):
        if not isinstance(item, dict) or set(item) != ITEM_FIELDS:
            raise ValueError(f"documents[{ordinal}] 字段必须精确匹配公开审阅清单 schema")
        if any(not isinstance(item[key], str) for key in ITEM_FIELDS - {"fullTextReviewed"}):
            raise ValueError(f"documents[{ordinal}] 文本字段类型无效")
        if type(item["fullTextReviewed"]) is not bool or (item["fullTextSha256"] and not item["fullTextReviewed"]):
            raise ValueError(f"documents[{ordinal}] 发布全文时 fullTextReviewed 必须为 true")
        for key in ("lawId", "versionId", "evidenceId", "permissionReason", "permissionSource", "reviewer", "reviewedAt"):
            if not item[key].strip():
                raise ValueError(f"documents[{ordinal}].{key} 不能为空")
        if item["publicationPermission"] not in PERMISSIONS:
            raise ValueError(f"documents[{ordinal}] publicationPermission 无效")
        if item["fullTextSha256"] and item["publicationPermission"] == "metadata_only":
            raise ValueError(f"documents[{ordinal}] metadata_only 不允许发布全文")
        if item["fullTextSha256"] and not SHA256.fullmatch(item["fullTextSha256"]):
            raise ValueError(f"documents[{ordinal}].fullTextSha256 必须为 SHA-256 或空（link_only）")
        try:
            verification.timestamp(item["reviewedAt"])
        except ValueError as exc:
            raise ValueError(f"documents[{ordinal}].reviewedAt 必须为带时区时间") from exc
        key = (item["lawId"], item["versionId"])
        if key in seen:
            raise ValueError(f"清单重复 lawId/versionId: {key[0]}/{key[1]}")
        seen.add(key)
        result.append(item)
    return result


def _write_new_json(path: Path, payload: Any) -> None:
    if path.exists():
        raise ValueError(f"输出已存在，拒绝覆盖: {path}")
    exchange.install_output(path, (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def _private_report_path(output: Path) -> Path:
    return output.parent / (output.name + ".blockers.json")


def _archive_ok(db: Path, evidence: dict[str, Any]) -> bool:
    # verification.load_evidence already resolved snapshot_ref relative to the
    # master and checked the bytes against sha256.
    return bool(evidence.get("archive_ok")) and bool(SHA256.fullmatch(evidence.get("sha256", "")))


def _library_document(library: Path, law_id: str, version_key: str) -> tuple[sqlite3.Connection, sqlite3.Row | None, Path]:
    conn, db = fulltext._connect(library, create=False)
    row = conn.execute(
        "SELECT * FROM documents WHERE document_id=? AND version=?", (law_id, version_key)
    ).fetchone()
    return conn, row, db


def _fulltext_reasons(row: sqlite3.Row, library_db: Path, law: dict[str, Any], version: dict[str, Any], evidence: dict[str, Any], item: dict[str, Any], as_of: date) -> list[str]:
    reasons: list[str] = []
    if row["document_id"] != law["id"] or row["version"] != version["version_key"]:
        reasons.append("全文库 documentId/version 与母库 law_version 不匹配")
    accepted_titles = {version["official_name"], law.get("canonical_name", "")}
    if row["title"] not in accepted_titles:
        reasons.append("全文库 title 与母库 official_name 不匹配")
    if row["sha256"] != item["fullTextSha256"]:
        reasons.append("清单全文 SHA 与全文库原件 SHA 不匹配")
    if row["sha256"] != evidence["sha256"]:
        reasons.append("全文原件 SHA 与核验证据 SHA 不匹配")
    if row["official_url"] != evidence["official_url"]:
        reasons.append("全文库官方 URL 与核验证据 URL 不匹配")
    try:
        archive = library_db.parent / row["archive_ref"]
        blob = archive.read_bytes()
    except (OSError, TypeError):
        reasons.append("全文库归档缺失")
        return reasons
    if hashlib.sha256(blob).hexdigest() != row["sha256"]:
        reasons.append("全文库归档哈希不匹配")
        return reasons
    try:
        paragraphs = fulltext.extract_paragraphs(blob)
    except Exception as exc:  # extraction adapters must fail closed
        reasons.append("全文重新解析失败: " + type(exc).__name__)
        return reasons
    try:
        directory = legal_text.directory(blob)
    except Exception as exc:  # the article adapter must fail closed
        reasons.append("法规条目目录解析失败: " + type(exc).__name__)
    else:
        reasons.extend("法规条目目录：" + issue for issue in directory["extractionIssues"])
    if not paragraphs or any(not text.strip() for text in paragraphs):
        reasons.append("全文解析结果为空或含空段落")
    if any('\ufffd' in text for text in paragraphs):
        reasons.append("全文含编码损坏的替换字符")
    if len(paragraphs) != row["paragraph_count"]:
        reasons.append("全文段落数与全文库索引不一致")
    text_sha = hashlib.sha256("\n".join(paragraphs).encode("utf-8")).hexdigest()
    if text_sha != row["text_sha256"]:
        reasons.append("全文解析文本 SHA 与全文库索引不一致")
    if row["as_of"] > as_of.isoformat():
        reasons.append("全文快照 asOf 晚于导出基准日")
    return reasons


def _normalized_grams(paragraphs: Iterable[str]) -> set[str]:
    """Return normalized adjacent two-codepoint grams for one document."""
    grams: set[str] = set()
    for paragraph in paragraphs:
        normalized = re.sub(r"[\u0009-\u000d\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]+", "", unicodedata.normalize("NFKC", paragraph).lower())
        chars = list(normalized)
        for ordinal in range(len(chars) - 1):
            gram = "".join(chars[ordinal:ordinal + 2])
            grams.add(gram)
    return grams


def _add_document_grams(shards: dict[str, dict[str, set[str]]], version_id: str, paragraphs: Iterable[str]) -> None:
    for gram in _normalized_grams(paragraphs):
        prefix = hashlib.sha256(gram.encode("utf-8")).hexdigest()[:2]
        shards.setdefault(prefix, {}).setdefault(gram, set()).add(version_id)


def export_public(db: Path, library: Path, checklist: Path, as_of: str, output: Path) -> dict[str, Any]:
    """Export only law versions that pass the master and text evidence gates."""
    as_of_date = verification.date(as_of)
    output = Path(output).expanduser().resolve()
    if output.exists():
        raise ValueError("公开输出必须是新目录，拒绝覆盖")
    report_path = _private_report_path(output)
    if report_path.exists():
        raise ValueError(f"私有阻断报告已存在，拒绝覆盖: {report_path}")
    items = _checklist(Path(checklist).expanduser().resolve())
    db = Path(db).expanduser().resolve()
    library = Path(library).expanduser().resolve()
    with closing(master.connect_readonly(db)) as conn:
        conn.execute('BEGIN')
        exchange.check_integrity(conn)
        graph = verification.graph_from_db(conn)
        verification.validate_graph(graph)
        proofs = verification.load_proofs(conn)
        evidence_map = verification.load_evidence(conn, db)
        laws = {row["id"]: row for row in graph["laws"]}
        versions = {row["id"]: row for row in graph["law_versions"]}
        # verification.graph_from_db intentionally omits version_key from its
        # dependency material; retain it in a side map for exact text lookup.
        version_keys = {row[0]: row[1] for row in conn.execute("SELECT id,version_key FROM law_versions")}
        public: list[dict[str, Any]] = []
        shards: list[tuple[str, dict[str, Any]]] = []
        gram_shards: dict[str, dict[str, set[str]]] = {}
        blockers: list[dict[str, Any]] = []
        for item in items:
            law_id, version_id = item["lawId"], item["versionId"]
            reasons: list[str] = []
            law, version = laws.get(law_id), versions.get(version_id)
            if not law:
                reasons.append("母库 law 不存在")
            if not version:
                reasons.append("母库 law_version 不存在")
            if version and version["law_id"] != law_id:
                reasons.append("law_version 不属于清单 lawId")
            if not law or not version:
                blockers.append({"lawId": law_id, "versionId": version_id, "evidenceId": item["evidenceId"], "reasons": reasons})
                continue
            version_key = version_keys.get(version_id, "")
            if not version_key:
                reasons.append("母库 law_version 缺少版本键")
            reasons.extend(verification.own_errors(graph, "law", law_id, proofs, evidence_map, as_of_date))
            reasons.extend(verification.own_errors(graph, "law_version", version_id, proofs, evidence_map, as_of_date))
            evidence = evidence_map.get(item["evidenceId"])
            if not evidence:
                reasons.append("清单 evidenceId 不存在")
            else:
                if not _archive_ok(db, evidence):
                    reasons.append("证据原件缺失或哈希不匹配")
                if version["source_url"] and version["source_url"] != evidence["official_url"]:
                    reasons.append("母库法规版本 URL 与清单证据 URL 不匹配")
            try:
                reviewed = verification.timestamp(item["reviewedAt"])
                if verification.business_date(reviewed) > as_of_date:
                    reasons.append("全文 reviewedAt 晚于导出基准日")
                if evidence and verification.timestamp(evidence['retrieved_at']) > reviewed:
                    reasons.append("全文审阅时间早于证据取得时间")
            except (ValueError, TypeError):
                reasons.append("全文 reviewedAt 无效")
            full_text = bool(item["fullTextSha256"])
            if full_text:
                try:
                    library_conn, text_row, library_db = _library_document(library, law_id, version_key)
                except Exception as exc:
                    text_row, library_db = None, library / "fulltext.sqlite3"
                    reasons.append("全文库 schema 或连接失败: " + type(exc).__name__)
                    library_conn = None
                if text_row is None:
                    reasons.append("全文库缺少对应版本全文")
                elif evidence:
                    reasons.extend(_fulltext_reasons(text_row, library_db, law, {**version, "version_key": version_key}, evidence, item, as_of_date))
                if library_conn:
                    library_conn.close()
            elif item["publicationPermission"] not in PERMISSIONS:
                reasons.append("link_only publicationPermission 无效")
            if not item["permissionReason"].strip() or not item["permissionSource"].strip():
                reasons.append("出版授权理由或出处为空")
            if reasons:
                blockers.append({"lawId": law_id, "versionId": version_id, "evidenceId": item["evidenceId"], "reasons": sorted(set(reasons))})
                continue
            mode = "full_text" if full_text else "link_only"
            text_path = f"texts/{version_id}.json" if full_text else None
            public.append({
                "lawId": law_id, "versionId": version_id, "title": version["official_name"],
                "version": version_key, "officialUrl": evidence["official_url"] if evidence else version["source_url"],
                "effectiveDate": version["effective_date"], "status": version["validity_status"],
                "textMode": mode, "fullTextSha256": item["fullTextSha256"], "textPath": text_path,
                "fullTextReviewed": item["fullTextReviewed"], "publicationPermission": item["publicationPermission"],
            })
            if full_text:
                library_conn, text_row, library_db = _library_document(library, law_id, version_key)
                archive = library_db.parent / text_row["archive_ref"]
                paragraphs = fulltext.extract_paragraphs(archive.read_bytes())
                library_conn.close()
                shard = {"schemaVersion": TEXT_SCHEMA, "lawId": law_id, "versionId": version_id,
                         "title": version["official_name"], "version": version_key,
                         "paragraphs": [{"location": f"paragraph:{number}", "text": text}
                                        for number, text in enumerate(paragraphs, 1)]}
                shards.append((text_path, shard))
                _add_document_grams(gram_shards, version_id, paragraphs)
        report = {"schemaVersion": "safety-private-fulltext-blockers-v1", "asOf": as_of,
                  "blockers": blockers, "blockedCount": len(blockers)}
    output.mkdir(parents=True)
    (output / "texts").mkdir()
    (output / "grams").mkdir()
    for text_path, shard in shards:
        _write_new_json(output / text_path, shard)
    gram_paths = {}
    for prefix in sorted(gram_shards):
        gram_path = f"grams/{prefix}.json"
        gram_paths[prefix] = gram_path
        payload = {"schemaVersion": GRAM_SCHEMA,
                   "grams": {gram: sorted(documents) for gram, documents in sorted(gram_shards[prefix].items())}}
        _write_new_json(output / gram_path, payload)
    catalog = {"schemaVersion": FORMAT, "asOf": as_of, "documents": public}
    search_index = {"schemaVersion": SEARCH_SCHEMA, "asOf": as_of,
                    "documents": [{"lawId": item["lawId"], "versionId": item["versionId"],
                                   "title": item["title"], "version": item["version"],
                                   "textMode": item["textMode"], "textPath": item["textPath"]}
                                  for item in public],
                    "gramShards": gram_paths}
    _write_new_json(output / "catalog.json", catalog)
    _write_new_json(output / "search-index.json", search_index)
    _write_new_json(report_path, report)
    return {"ok": True, "publicCount": len(public), "blockedCount": len(blockers),
            "output": str(output), "blockerReport": str(report_path)}


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True, help="私有 safety master SQLite")
    parser.add_argument("--library", type=Path, required=True, help="私有 fulltext 库目录")
    parser.add_argument("--checklist", type=Path, required=True, help="公开全文审阅/授权清单")
    parser.add_argument("--as-of", required=True, help="导出基准日 YYYY-MM-DD")
    parser.add_argument("--output", type=Path, required=True, help="新建公开输出目录")
    args = parser.parse_args(list(argv) if argv is not None else None)
    print(json.dumps(export_public(args.db, args.library, args.checklist, args.as_of, args.output), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    main()
