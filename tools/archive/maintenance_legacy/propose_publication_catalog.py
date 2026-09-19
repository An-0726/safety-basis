# -*- coding: utf-8 -*-
"""从已确认的私有全文manifest生成公开法规metadata提案，不发布私有全文。"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUB = ROOT / "source" / "publication" / "law-index.json"
OUT = ROOT / "source" / "proposals" / "excel-20260913" / "publication-metadata-proposal.json"
EXCLUDE = {"LV_TSG_R7001_2013", "LV_RULE_WAREHOUSE_1990"}


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def level(version: str, title: str) -> str:
    v = version.upper()
    if v.startswith("GB/T") or v.startswith("GBT"):
        return "推荐性国家标准"
    if v.startswith("GB"):
        return "工程建设国家标准" if re.search(r"GB\s*5\d{4}", v) else "强制性国家标准"
    if v.startswith("DB32"):
        return "江苏地方标准"
    if v.startswith("HJ"):
        return "生态环境标准"
    if v.startswith(("AQ", "YJ/", "YJT", "DL/", "DLT", "JB/", "JBT", "JGJ")):
        return "行业标准"
    return "规范性文件/标准参考"


existing = json.loads(PUB.read_text(encoding="utf-8"))
existing_ids = {row["id"] for row in existing}
items = []
seen = set()
for manifest in sorted((ROOT / "source" / "library" / "incoming-20260913").rglob("manifest*.json")):
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception:
        continue
    for doc in payload.get("documents", []):
        ident = doc.get("documentId", "")
        status = norm(doc.get("currentStatus", ""))
        if not ident or ident in existing_ids or ident in seen or ident in EXCLUDE:
            continue
        if ident.startswith("LV_GROUP_") or "团体标准" in status or "参考" in status or "部分范围失效" in status:
            continue
        if not status.startswith(("现行有效", "过渡期现行", "即将生效", "现行基础目录", "现行使用中")):
            continue
        title = norm(doc.get("title", ""))
        version = norm(doc.get("version", ""))
        if not title or not version or not doc.get("officialUrl"):
            continue
        scope = "江苏" if version.upper().startswith("DB32") or "江苏" in title else "全国"
        item = {
            "id": ident,
            "name": f"{title} {version}",
            "aliases": [version, title],
            "level": level(version, title),
            "scope": scope,
            "status": "即将实施" if status.startswith("即将生效") else ("过渡期现行" if status.startswith("过渡期") else "现行有效"),
            "checked": date.today().isoformat(),
            "effectiveDate": "",
            "sourceUrl": doc["officialUrl"],
            "replaces": [],
            "replacedBy": [],
            "clauseRefs": [],
            "hazardCount": 0,
            "clauseCount": 0,
            "searchText": norm(f"{ident} {title} {version} {level(version, title)} {scope}").lower(),
            "privateFulltextOnly": True,
            "statusNote": status,
        }
        items.append(item)
        seen.add(ident)

OUT.write_text(json.dumps({
    "kind": "publication-metadata-proposal-v1",
    "asOf": date.today().isoformat(),
    "existingPublicationCount": len(existing),
    "proposalCount": len(items),
    "items": items,
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"existingPublicationCount": len(existing), "proposalCount": len(items), "output": str(OUT)}, ensure_ascii=False, indent=2))
