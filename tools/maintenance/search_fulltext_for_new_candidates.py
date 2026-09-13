# -*- coding: utf-8 -*-
"""用私有全文库为全部新增候选寻找原文段落，不写入正式知识源。"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DISP = ROOT / "source/proposals/excel-20260913/new-hazard-disposition.json"
OUT = ROOT / "source/proposals/excel-20260913/new-fulltext-clause-candidates.json"


def norm(value: str) -> str:
    return re.sub(r"[^A-Z0-9\u4e00-\u9fff]", "", str(value or "").upper())


def phrases(value: str) -> list[str]:
    text = re.sub(r"\s+", "", str(value or ""))
    text = re.sub(r"[，。；：、,.;:（）()【】\[\]《》<>“”‘’\"'\-—_]+", "", text)
    out = []
    if len(text) >= 16:
        out.append(text[:20])
        out.append(text[:14])
    elif len(text) >= 8:
        out.append(text[:12])
    if len(text) > 20:
        out.append(text[-16:])
    return list(dict.fromkeys(x for x in out if len(x) >= 6))


payload = json.loads(DISP.read_text(encoding="utf-8"))
conn = sqlite3.connect(ROOT / "source/library/fulltext.sqlite3")
conn.row_factory = sqlite3.Row
try:
    docs = [dict(row) for row in conn.execute("SELECT document_key,document_id,title,version FROM documents")]
    rows = []
    for cand in payload["records"]:
        basis = cand.get("directBasis", "")
        # Search quote first; Excel disposition report does not duplicate quote, so use title/description too.
        source_text = " ".join([basis, cand.get("title", ""), cand.get("description", "")])
        ps = phrases(source_text)
        doc_candidates = []
        numbers = set(norm(x) for x in re.findall(r"(?:GB/T|GBT|GB|AQ|HJ|XF|JGJ|TSG|DL/T|DLT|DB\s*\d{2,4}(?:/T|T)?|YJ/T|YJT|JB/T|JB)\s*[-—_+ ]?\s*\d+(?:\.\d+)?(?:\s*[-—_ ]\s*\d{4})?", basis, re.I))
        for doc in docs:
            hay = norm(doc["title"] + " " + doc["version"])
            if any(token in hay for token in numbers):
                doc_candidates.append(doc)
        if not doc_candidates:
            doc_candidates = docs

        hits = []
        for phrase in ps:
            sql = "SELECT document_key,paragraph_no,content FROM fulltext_fts WHERE content LIKE ? LIMIT 8"
            params = (f"%{phrase}%",)
            if len(doc_candidates) < len(docs):
                keys = [doc["document_key"] for doc in doc_candidates]
                marks = ",".join("?" for _ in keys)
                sql = f"SELECT document_key,paragraph_no,content FROM fulltext_fts WHERE document_key IN ({marks}) AND content LIKE ? LIMIT 8"
                params = tuple(keys) + (f"%{phrase}%",)
            for hit in conn.execute(sql, params):
                hits.append({"documentKey": hit[0], "paragraphNo": hit[1], "snippet": (hit[2] or "")[:800], "phrase": phrase})
            if hits:
                break
        rows.append({
            "hazardId": cand["hazardId"],
            "sourceRow": cand["sourceRow"],
            "disposition": cand.get("disposition", ""),
            "basis": basis,
            "title": cand.get("title", ""),
            "status": "fulltext_hit" if hits else "no_fulltext_hit",
            "hits": hits[:8],
        })
finally:
    conn.close()

summary = {"candidateCount": len(rows), "fulltextHit": sum(r["status"] == "fulltext_hit" for r in rows), "noFulltextHit": sum(r["status"] == "no_fulltext_hit" for r in rows), "byDisposition": Counter(r["disposition"] for r in rows)}
OUT.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
