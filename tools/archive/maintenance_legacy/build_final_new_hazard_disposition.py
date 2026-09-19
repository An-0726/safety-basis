# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = json.loads((ROOT / "source/proposals/excel-20260913/new-hazard-disposition.json").read_text(encoding="utf-8"))
TEXT = json.loads((ROOT / "source/proposals/excel-20260913/new-fulltext-clause-candidates.json").read_text(encoding="utf-8"))
hits = {row["hazardId"]: row for row in TEXT["rows"]}
rows = []
for row in BASE["records"]:
    hit = hits.get(row["hazardId"], {})
    disposition = row["disposition"]
    if disposition in {"basis_catalog_only", "basis_name_unresolved", "basis_number_unresolved"} and hit.get("status") == "fulltext_hit":
        disposition = "fulltext_clause_candidate"
        reason = "已从私有全文库检出段落候选，需核对条款号、原文和适用性"
    else:
        reason = row["reason"]
    rows.append({**row, "finalDisposition": disposition, "finalReason": reason, "fulltextHits": hit.get("hits", [])})
summary = {"count": len(rows), "finalDispositions": Counter(row["finalDisposition"] for row in rows), "notAdmitted": len(rows)}
out = ROOT / "source/proposals/excel-20260913/final-new-hazard-disposition.json"
out.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
