# -*- coding: utf-8 -*-
"""PHASE 8：公开前端 / 本地私有版一致性审计。

公开侧针对 fresh unified bundle 验证 candidate 隔离、canonical law-version 身份、
条款/隐患跳转完整性与 publication 全文边界；私有侧可选地只读 fulltext.sqlite3，
验证 documents/FTS 数量、archive_ref 结构与 SHA 绑定。脚本不写 SQLite/archive。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_REF_RE = re.compile(r"^archive/([0-9a-f]{64})/original$")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_entity_map(path: Path) -> dict[str, dict]:
    out = {}
    for file in sorted(path.glob("*.json")):
        row = read_json(file)
        entity_id = row.get("id")
        if entity_id:
            out[entity_id] = row
    return out


def require(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def audit_public(bundle: Path) -> dict:
    errors: list[str] = []
    release = read_json(bundle / "release.json")
    manifest = read_json(bundle / "data" / "manifest.json")
    search_index = read_json(bundle / "data" / "search-index.json")
    law_index = read_json(bundle / "data" / "law-index.json")
    catalog = read_json(bundle / "data" / "fulltext" / "catalog.json")

    knowledge_hazards = load_entity_map(ROOT / "knowledge" / "hazards")
    knowledge_versions = load_entity_map(ROOT / "knowledge" / "law-versions")
    publication_index = read_json(ROOT / "source" / "publication" / "law-index.json")
    publication_ids = {row["id"] for row in publication_index}
    version_ids = set(knowledge_versions)
    proposed_ids = {
        hid for hid, row in knowledge_hazards.items()
        if (row.get("lifecycle") or "active") == "proposed"
    }

    hazards = []
    for shard in manifest.get("hazardShards", []):
        payload = read_json(bundle / shard["url"])
        hazards.extend(payload.get("records", []))
    clauses = []
    for shard in manifest.get("clauseShards", []):
        payload = read_json(bundle / shard["url"])
        clauses.extend(payload.get("records", []))

    public_hazard_ids = {row["id"] for row in hazards}
    search_ids = {row["id"] for row in search_index}
    public_clause_ids = {row["id"] for row in clauses}
    formal_version_ids = {row["id"] for row in law_index}
    catalog_version_ids = {row["versionId"] for row in catalog.get("documents", [])}

    require(errors, len(public_hazard_ids) == len(hazards), "公开隐患分片存在重复 ID")
    require(errors, len(search_ids) == len(search_index), "公开 search-index 存在重复隐患 ID")
    require(errors, public_hazard_ids == search_ids, "search-index 与隐患分片 ID 集不一致")
    require(errors, not (public_hazard_ids & proposed_ids), "proposed 隐患泄漏到公开包")
    require(errors, all(row.get("status") == "已核验" for row in hazards), "公开隐患存在非“已核验”状态")
    require(errors, all(row.get("publishable") is True for row in hazards), "公开隐患存在 publishable!=true")
    require(errors, all((row.get("lifecycle") or "active") == "active" for row in hazards), "公开隐患存在非 active lifecycle")

    gate = release.get("knowledge", {}).get("gate", {})
    require(errors, gate.get("publicProposalHazards") == 0, "release gate 报告 publicProposalHazards 非 0")
    require(errors, manifest.get("counts", {}).get("hazards") == len(hazards), "manifest hazards 数量与分片不一致")
    require(errors, release.get("counts", {}).get("hazards") == len(hazards), "release hazards 数量与分片不一致")

    require(errors, len(formal_version_ids) == len(law_index), "正式法规索引存在重复 version ID")
    require(errors, formal_version_ids <= version_ids, "正式法规索引含非 knowledge canonical version ID")
    require(errors, formal_version_ids <= publication_ids, "正式法规索引含未归整到 publication 的 version ID")
    require(errors, catalog_version_ids <= version_ids, "全文 catalog 含非 knowledge canonical version ID")
    require(errors, catalog_version_ids <= publication_ids, "全文 catalog 含非 publication canonical version ID")

    clause_by_id = {row["id"]: row for row in clauses}
    for hazard in hazards:
        for ref in hazard.get("basisRefs", []):
            require(errors, ref.get("clauseId") in public_clause_ids,
                    f"隐患 {hazard.get('id')} 指向未发布条款 {ref.get('clauseId')}")
    for clause in clauses:
        require(errors, clause.get("lawId") in formal_version_ids,
                f"条款 {clause.get('id')} 指向未发布法规版本 {clause.get('lawId')}")
    for law in law_index:
        for ref in law.get("clauseRefs", []):
            cid = ref.get("clauseId")
            require(errors, cid in clause_by_id, f"法规 {law.get('id')} 指向缺失条款 {cid}")
            for hid in ref.get("hazardIds", []):
                require(errors, hid in public_hazard_ids, f"法规 {law.get('id')} 指向未发布隐患 {hid}")

    full_text_count = 0
    link_only_count = 0
    for doc in catalog.get("documents", []):
        mode = doc.get("textMode")
        if mode == "full_text":
            full_text_count += 1
            require(errors, doc.get("fullTextReviewed") is True,
                    f"全文 {doc.get('versionId')} 未标记 fullTextReviewed")
            require(errors, doc.get("publicationPermission") == "official_legal_text",
                    f"全文 {doc.get('versionId')} publicationPermission 非 official_legal_text")
            text_path = doc.get("textPath")
            require(errors, bool(text_path) and (bundle / "data" / "fulltext" / text_path).is_file(),
                    f"全文 {doc.get('versionId')} textPath 缺失")
        elif mode == "link_only":
            link_only_count += 1
            require(errors, doc.get("publicationPermission") == "metadata_only",
                    f"题录 {doc.get('versionId')} publicationPermission 非 metadata_only")
            require(errors, not doc.get("textPath"), f"metadata-only {doc.get('versionId')} 意外携带 textPath")
        else:
            errors.append(f"未知 textMode: {doc.get('versionId')}={mode}")

    require(errors, release.get("fullText", {}).get("count") == full_text_count,
            "release fullText.count 与 catalog 不一致")
    require(errors, release.get("fullText", {}).get("officialLinkCount") == link_only_count,
            "release officialLinkCount 与 catalog 不一致")

    catalog_only = sorted(catalog_version_ids - formal_version_ids)
    library_js = (ROOT / "web" / "js" / "library.js").read_text(encoding="utf-8")
    if catalog_only:
        require(errors, "formalLawIds.has(doc.versionId)" in library_js,
                "全文资料包含未进入正式 law-index 的 canonical versions，但前端仍无条件显示正式法规跳转")

    private_markers = ("source/library", "fulltext.sqlite3", "archive_ref", "evidence/")
    marker_hits = []
    for path in bundle.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".json", ".js", ".html", ".css"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for marker in private_markers:
            if marker in text:
                marker_hits.append(f"{path.relative_to(bundle)}:{marker}")
    require(errors, not marker_hits, "公开包出现私有边界 marker: " + ", ".join(marker_hits[:10]))

    result = {
        "status": "PASS" if not errors else "FAIL",
        "publicHazards": len(hazards),
        "publicClauses": len(clauses),
        "formalLawVersions": len(law_index),
        "catalogDocuments": len(catalog.get("documents", [])),
        "catalogFullText": full_text_count,
        "catalogLinkOnly": link_only_count,
        "catalogOnlyCanonicalVersions": len(catalog_only),
        "proposedInKnowledge": len(proposed_ids),
        "proposedInPublic": len(public_hazard_ids & proposed_ids),
        "privateBoundaryMarkerHits": marker_hits,
        "errors": errors,
    }
    return result


def audit_private(db: Path, expected_sha256: str | None) -> dict:
    errors: list[str] = []
    actual_sha = sha256_file(db)
    if expected_sha256:
        require(errors, actual_sha == expected_sha256, "私有 SQLite SHA-256 与已验证基线不一致")

    with sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True) as conn:
        docs = conn.execute(
            "SELECT document_key, sha256, paragraph_count, archive_ref FROM documents"
        ).fetchall()
        fts_rows = conn.execute("SELECT COUNT(*) FROM fulltext_fts").fetchone()[0]
        paragraph_sum = conn.execute("SELECT SUM(paragraph_count) FROM documents").fetchone()[0]
        fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()

    archive_rows = 0
    legacy_rows = 0
    archive_shas: set[str] = set()
    sha_mismatches = []
    unknown_refs = []
    for key, sha, _paragraph_count, ref in docs:
        match = ARCHIVE_REF_RE.fullmatch(ref or "")
        if match:
            archive_rows += 1
            archive_sha = match.group(1)
            archive_shas.add(archive_sha)
            if archive_sha != sha:
                sha_mismatches.append(key)
        elif (ref or "").startswith("evidence/"):
            legacy_rows += 1
        else:
            unknown_refs.append((key, ref))

    require(errors, fts_rows == paragraph_sum, "fulltext_fts 行数与 paragraph_count 合计不一致")
    require(errors, not fk_errors, "SQLite foreign_key_check 非空")
    require(errors, not sha_mismatches, "archive_ref SHA 与 documents.sha256 不一致")
    require(errors, not unknown_refs, "发现 archive/evidence 之外的未知 archive_ref")

    return {
        "status": "PASS" if not errors else "FAIL",
        "databaseSha256": actual_sha,
        "documents": len(docs),
        "ftsRows": fts_rows,
        "paragraphCountSum": paragraph_sum,
        "archiveBackedDocumentRows": archive_rows,
        "distinctArchiveShas": len(archive_shas),
        "legacyEvidenceProvenanceRows": legacy_rows,
        "archiveShaMismatches": len(sha_mismatches),
        "foreignKeyErrors": len(fk_errors),
        "unknownArchiveRefs": len(unknown_refs),
        "errors": errors,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", default=str(ROOT / "source" / "releases" / "current"))
    ap.add_argument("--private-db")
    ap.add_argument("--expected-private-sha256")
    ap.add_argument("--output")
    args = ap.parse_args()

    report = {"schemaVersion": "phase8-consistency-audit-v1"}
    bundle = Path(args.bundle).resolve()
    report["public"] = audit_public(bundle)
    if args.private_db:
        report["private"] = audit_private(Path(args.private_db).resolve(), args.expected_private_sha256)

    report["status"] = "PASS" if all(
        section.get("status") == "PASS"
        for key, section in report.items() if key in {"public", "private"}
    ) else "FAIL"

    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8", newline="\n")
    print(payload, end="")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
