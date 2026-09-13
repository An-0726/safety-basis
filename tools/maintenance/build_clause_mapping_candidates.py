# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
disp = json.loads((ROOT / "source/proposals/excel-20260913/new-hazard-disposition.json").read_text(encoding="utf-8"))
coverage = json.loads((ROOT / "source/proposals/excel-20260913/new-basis-coverage.json").read_text(encoding="utf-8"))
cov = {row["hazardId"]: row for row in coverage["records"]}
rows = []
for row in disp["records"]:
    if row["disposition"] != "basis_found_private_text":
        continue
    c = cov.get(row["hazardId"], {})
    rows.append({
        "hazardId": row["hazardId"],
        "sourceRow": row["sourceRow"],
        "title": row["title"],
        "description": row["description"],
        "conditions": row["conditions"],
        "measures": row["measures"],
        "directBasis": row["directBasis"],
        "catalogIds": c.get("catalogIds", []),
        "privateDocumentHits": c.get("privateDocumentHits", []),
        "clauseQuote": "",
        "proposedClauseStatus": "needs_clause_locator",
        "proposedLinkStatus": "needs_applicability_review",
    })
out = ROOT / "source/proposals/excel-20260913/new-clause-mapping-candidates.json"
out.write_text(json.dumps({
    "kind": "excel-new-clause-mapping-candidates-v1",
    "count": len(rows),
    "rows": rows,
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"count": len(rows), "output": str(out)}, ensure_ascii=False, indent=2))
