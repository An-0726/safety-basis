# -*- coding: utf-8 -*-
"""给Excel新增隐患候选生成不入库的处置结果。"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / "source" / "proposals" / "excel-20260913" / "new-hazard-candidates.json"
DEDUP = ROOT / "source" / "proposals" / "excel-20260913" / "new-candidate-dedup.json"
OUT = ROOT / "source" / "proposals" / "excel-20260913" / "new-hazard-disposition.json"


def norm(value: str) -> str:
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", str(value or "")).lower()


def core_name(value: str) -> str:
    value = norm(value)
    for prefix in ("中华人民共和国", "国家标准", "行业标准"):
        value = value.replace(prefix, "")
    return value


payload = json.loads(PROPOSAL.read_text(encoding="utf-8"))
dedup = json.loads(DEDUP.read_text(encoding="utf-8"))
dedup_by_id = {row["hazardId"]: row for row in dedup["records"]}
rows = payload["rows"]

catalog = json.loads((ROOT / "source" / "publication" / "law-index.json").read_text(encoding="utf-8"))
catalog_names = [(row["id"], core_name(row.get("name", ""))) for row in catalog]

conn = sqlite3.connect(ROOT / "source" / "library" / "fulltext.sqlite3")
try:
    docs = [(row[0], core_name(row[1] + " " + row[2])) for row in conn.execute("SELECT document_id,title,version FROM documents")]
finally:
    conn.close()

records = []
for row in rows:
    hid = row["hazardId"]
    fields = row.get("changedFields") or {}
    basis = row.get("directBasis", "")
    basis_norm = core_name(basis)
    names = [ident for ident, name in catalog_names if len(name) >= 6 and (name in basis_norm or basis_norm in name)]
    docs_match = [ident for ident, name in docs if len(name) >= 6 and (name in basis_norm or basis_norm in name)]
    d = dedup_by_id.get(hid, {})

    if d.get("exactSemanticExistingIds") or d.get("sameCandidateSemanticIds"):
        disposition = "duplicate_or_merge"
        reason = "标题和专业描述与现有实体或候选重复，先合并，不直接新增"
    elif d.get("sameTitleExistingIds"):
        disposition = "same_title_review"
        reason = "与现有实体标题相同，需确认是否为不同场景或同一隐患"
    elif d.get("catalogIds") or names:
        if d.get("fulltextDocumentHits") or docs_match:
            disposition = "basis_found_private_text"
            reason = "依据已匹配公开题录和本地全文，可进入条款定位批次"
        else:
            disposition = "basis_catalog_only"
            reason = "依据已匹配公开题录，但本地全文或条款仍需补齐"
    elif d.get("numbers"):
        disposition = "basis_number_unresolved"
        reason = "有标准编号，但未匹配当前法规目录，需核对编号、版本或地方/团体属性"
    elif basis.strip():
        disposition = "basis_name_unresolved"
        reason = "有依据文字但没有可确认编号，需从法规名称和原文定位"
    else:
        disposition = "missing_basis"
        reason = "Excel未提供可定位的直接依据"

    records.append({
        "hazardId": hid,
        "sourceRow": row["sourceRow"],
        "disposition": disposition,
        "reason": reason,
        "catalogNameMatches": names,
        "privateDocumentMatches": docs_match,
        "directBasis": basis,
        "title": fields.get("title", ""),
        "description": fields.get("description", ""),
        "conditions": fields.get("conditions", ""),
        "measures": fields.get("measures", ""),
    })

summary = {
    "candidateCount": len(records),
    "dispositions": Counter(row["disposition"] for row in records),
    "readyForClauseMapping": sum(row["disposition"] == "basis_found_private_text" for row in records),
    "notAdmitted": len(records),
}
OUT.write_text(json.dumps({"summary": summary, "records": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
