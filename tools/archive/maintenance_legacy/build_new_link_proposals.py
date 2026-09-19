# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOC = ROOT / "source/proposals/excel-20260913/new-clause-location-results.json"
DISP = ROOT / "source/proposals/excel-20260913/new-hazard-disposition.json"
OUT = ROOT / "source/proposals/excel-20260913/new-link-proposals.json"


locations = json.loads(LOC.read_text(encoding="utf-8"))
dispositions = json.loads(DISP.read_text(encoding="utf-8"))
by_hazard = {row["hazardId"]: row for row in dispositions["records"]}
links = []
unresolved = []
for row in locations["rows"]:
    hazard = by_hazard.get(row["hazardId"], {})
    clause_ids = [cid for ref in row["refs"] for cid in ref["existingClauseIds"]]
    if not clause_ids:
        unresolved.append(row)
        continue
    for clause_id in dict.fromkeys(clause_ids):
        link_id = "K_XLSX_" + hashlib.sha1(f"{row['hazardId']}|{clause_id}".encode()).hexdigest()[:24]
        conditions = hazard.get("conditions", "")
        jurisdiction = "江苏" if "江苏" in conditions else "全国"
        links.append({
            "id": link_id,
            "hazardId": row["hazardId"],
            "clauseId": clause_id,
            "role": "direct",
            "applicability": "待核验",
            "jurisdiction": jurisdiction,
            "reason": f"来自Excel第{row['sourceRow']}行；依据条款已在knowledge中定位，需完成适用性与原文复核。",
            "status": "proposal_only",
        })

OUT.write_text(json.dumps({
    "kind": "excel-new-link-proposal-v1",
    "linkCount": len(links),
    "unresolvedCount": len(unresolved),
    "links": links,
    "unresolved": unresolved,
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"linkCount": len(links), "unresolvedCount": len(unresolved), "output": str(OUT)}, ensure_ascii=False, indent=2))
