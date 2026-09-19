# -*- coding: utf-8 -*-
"""分析新增隐患候选的直接依据是否能在现有知识源/全文库定位。"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / "source" / "proposals" / "excel-20260913" / "new-hazard-candidates.json"
OUT = ROOT / "source" / "proposals" / "excel-20260913" / "new-basis-coverage.json"

NUMBER_RE = re.compile(r"(?:GB/T|GBT|GB|AQ|HJ|XF|JGJ|TSG|DL/T|DLT|DB\s*\d{2,4}(?:/T|T)?|YJ/T|YJT|JB/T|JB)\s*[-—_+ ]?\s*\d+(?:\.\d+)?(?:\s*[-—_ ]\s*\d{4})?", re.I)


def norm(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper().replace("—", "-").replace("–", "-"))


payload = json.loads(PROPOSAL.read_text(encoding="utf-8"))
rows = payload["rows"]

law_index = json.loads((ROOT / "source" / "publication" / "law-index.json").read_text(encoding="utf-8"))
known_numbers = {}
for row in law_index:
    for value in [row.get("name", ""), *(row.get("aliases") or [])]:
        for token in NUMBER_RE.findall(value):
            known_numbers.setdefault(norm(token), []).append(row["id"])

clause_text = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "knowledge" / "clauses").glob("*.json"))
fulltext = sqlite3.connect(ROOT / "source" / "library" / "fulltext.sqlite3")
try:
    docs = fulltext.execute("SELECT title, version FROM documents").fetchall()
finally:
    fulltext.close()
fulltext_numbers = {norm(x) for title, version in docs for x in NUMBER_RE.findall(f"{title} {version}")}

records = []
for row in rows:
    basis = row.get("directBasis", "")
    numbers = sorted({norm(x) for x in NUMBER_RE.findall(basis)})
    known_catalog = sorted({ident for n in numbers for ident in known_numbers.get(n, [])})
    clause_hits = [n for n in numbers if n in clause_text.upper()]
    fulltext_hits = [n for n in numbers if n in fulltext_numbers]
    records.append({
        "hazardId": row["hazardId"],
        "sourceRow": row["sourceRow"],
        "numbers": numbers,
        "catalogIds": known_catalog,
        "clauseNumberHits": clause_hits,
        "fulltextDocumentHits": fulltext_hits,
        "basis": basis,
    })

summary = {
    "candidateCount": len(rows),
    "withNumberedBasis": sum(bool(r["numbers"]) for r in records),
    "catalogMatched": sum(bool(r["catalogIds"]) for r in records),
    "existingClauseTextMatched": sum(bool(r["clauseNumberHits"]) for r in records),
    "privateFulltextMatched": sum(bool(r["fulltextDocumentHits"]) for r in records),
    "noNumberedBasis": sum(not r["numbers"] for r in records),
    "topNumbers": Counter(n for r in records for n in r["numbers"]).most_common(30),
}
OUT.write_text(json.dumps({"summary": summary, "records": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
