# -*- coding: utf-8 -*-
"""为311条新隐患候选定位现有知识条款，不写入正式知识源。"""
from __future__ import annotations

import json
import re
from collections import defaultdict, Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
IN = ROOT / "source/proposals/excel-20260913/new-clause-mapping-candidates.json"
OUT = ROOT / "source/proposals/excel-20260913/new-clause-location-results.json"

NUM = re.compile(r"(?:GB/T|GBT|GB|AQ|HJ|XF|JGJ|TSG|DL/T|DLT|DB\s*\d{2,4}(?:/T|T)?|YJ/T|YJT|JB/T|JB)\s*[-—_+ ]?\s*\d+(?:\.\d+)?(?:\s*[-—_ ]\s*\d{4})?", re.I)
CLAUSE = re.compile(r"(?:第\s*)?(\d+(?:\.\d+){0,5})\s*条")
PLAIN_CLAUSE = re.compile(r"(?<!\d)(\d+(?:\.\d+){1,5})")
CN_CLAUSE = re.compile(r"第\s*([一二三四五六七八九十百千万零〇]+)\s*条")


def chinese_number(value: str) -> str:
    digits = {"零": 0, "〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    if value.isdigit():
        return value
    if "十" not in value and "百" not in value and "千" not in value and "万" not in value:
        return str(digits.get(value, value))
    total = 0
    section = 0
    number = 0
    units = {"十": 10, "百": 100, "千": 1000, "万": 10000}
    for char in value:
        if char in digits:
            number = digits[char]
        elif char in units:
            unit = units[char]
            if unit == 10000:
                section = (section + number) * unit
                total += section
                section = 0
            else:
                section += (number or 1) * unit
            number = 0
    return str(total + section + number)


def norm(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper().replace("—", "-").replace("–", "-"))


law_versions = []
for path in (ROOT / "knowledge/law-versions").glob("*.json"):
    row = json.loads(path.read_text(encoding="utf-8"))
    law_versions.append(row)
by_number = defaultdict(list)
for row in law_versions:
    by_number[norm(row.get("documentNumber", ""))].append(row)
by_name = [(re.sub(r"[（）()]", "", row.get("officialName", "")), row) for row in law_versions]

clauses = []
for path in (ROOT / "knowledge/clauses").glob("*.json"):
    row = json.loads(path.read_text(encoding="utf-8"))
    clauses.append(row)
clause_by_law_path = defaultdict(list)
for row in clauses:
    path_key = re.sub(r"[^0-9.]", "", row.get("articlePath", ""))
    clause_by_law_path[(row.get("lawVersionId"), path_key)].append(row)

payload = json.loads(IN.read_text(encoding="utf-8"))
results = []
for candidate in payload["rows"]:
    basis = candidate.get("directBasis", "")
    refs = []
    tokens = {norm(x) for x in NUM.findall(basis)}
    for name, law in by_name:
        if name and name in basis:
            tokens.add(norm(law.get("documentNumber", "")))
    clause_numbers = [x for x in CLAUSE.findall(basis)]
    clause_numbers += [chinese_number(x) for x in CN_CLAUSE.findall(basis)]
    if not clause_numbers:
        clause_numbers = PLAIN_CLAUSE.findall(basis)
    for token in sorted(tokens):
        laws = by_number.get(token, [])
        matches = []
        for law in laws:
            for number in clause_numbers:
                matches.extend(clause_by_law_path.get((law["id"], number), []))
        refs.append({
            "standardToken": token,
            "lawVersionIds": [law["id"] for law in laws],
            "articleNumbers": clause_numbers,
            "existingClauseIds": [row["id"] for row in matches],
        })
    if any(ref["existingClauseIds"] for ref in refs):
        status = "clause_found"
    elif any(ref["lawVersionIds"] for ref in refs):
        status = "law_version_found_clause_missing"
    else:
        status = "law_version_unresolved"
    results.append({"hazardId": candidate["hazardId"], "sourceRow": candidate["sourceRow"], "status": status, "refs": refs, "directBasis": basis, "clauseQuote": candidate.get("clauseQuote", "")})

summary = {"candidateCount": len(results), "statuses": Counter(row["status"] for row in results), "existingClauseMatches": sum(row["status"] == "clause_found" for row in results)}
OUT.write_text(json.dumps({"summary": summary, "rows": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
