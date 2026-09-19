# -*- coding: utf-8 -*-
"""分析Excel产生的新增隐患候选与现有知识的重复关系。只读知识源。"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / "source" / "proposals" / "excel-20260913" / "new-hazard-candidates.json"
OUT = ROOT / "source" / "proposals" / "excel-20260913" / "new-candidate-dedup.json"
BOOK = Path(r"D:\Desktop\隐患库最终修订交付版_20260913.xlsx")


def norm(value: str) -> str:
    text = str(value or "").lower()
    return re.sub(r"[^\w\u4e00-\u9fff]", "", text)


def key(row: dict) -> str:
    fields = row.get("changedFields") or {}
    return norm(fields.get("title", "")) + "|" + norm(fields.get("description", ""))


hazards = {}
for path in (ROOT / "knowledge" / "hazards").glob("*.json"):
    row = json.loads(path.read_text(encoding="utf-8"))
    hazards[row["id"]] = row

existing_by_key = defaultdict(list)
existing_by_title = defaultdict(list)
for row in hazards.values():
    k = norm(row.get("title", "")) + "|" + norm(row.get("description", ""))
    existing_by_key[k].append(row["id"])
    existing_by_title[norm(row.get("title", ""))].append(row["id"])

payload = json.loads(PROPOSAL.read_text(encoding="utf-8"))
candidates = payload["rows"]
candidate_by_key = defaultdict(list)
for row in candidates:
    candidate_by_key[key(row)].append(row["hazardId"])

records = []
for row in candidates:
    fields = row.get("changedFields") or {}
    k = key(row)
    title = norm(fields.get("title", ""))
    records.append({
        "hazardId": row["hazardId"],
        "sourceRow": row["sourceRow"],
        "sameTitleExistingIds": existing_by_title.get(title, []),
        "exactSemanticExistingIds": existing_by_key.get(k, []),
        "sameCandidateSemanticIds": [x for x in candidate_by_key.get(k, []) if x != row["hazardId"]],
        "finalDecision": row.get("finalDecision", ""),
        "basisReview": row.get("basisReview", ""),
    })

summary = {
    "candidateCount": len(candidates),
    "sameTitleExisting": sum(bool(r["sameTitleExistingIds"]) for r in records),
    "exactSemanticExisting": sum(bool(r["exactSemanticExistingIds"]) for r in records),
    "duplicateWithinCandidates": sum(bool(r["sameCandidateSemanticIds"]) for r in records),
    "candidateSemanticGroups": sum(1 for ids in candidate_by_key.values() if len(ids) > 1),
    "recordCount": len(records),
}
OUT.write_text(json.dumps({"summary": summary, "records": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
