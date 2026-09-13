# -*- coding: utf-8 -*-
"""把全部Excel新增候选登记为knowledge中的提案实体，不进入发布门禁。"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / "source/proposals/excel-20260913/new-hazard-candidates.json"
DISP = ROOT / "source/proposals/excel-20260913/final-new-hazard-disposition.json"
OUT = ROOT / "source/proposals/excel-20260913/proposed-hazard-admission-report.json"


def words(value: str) -> list[str]:
    text = str(value or "")
    pieces = [x.strip() for x in re.split(r"[，。；、,;：:\s/（）()]+", text) if x.strip()]
    return list(dict.fromkeys(pieces[:24])) or ["待核验候选"]


proposal = json.loads(PROPOSAL.read_text(encoding="utf-8"))
disp = json.loads(DISP.read_text(encoding="utf-8"))
dispositions = {row["hazardId"]: row for row in disp["rows"]}
hazard_dir = ROOT / "knowledge" / "hazards"
added = []
skipped = []
for row in proposal["rows"]:
    hid = row["hazardId"]
    path = hazard_dir / f"{hid}.json"
    if path.exists():
        skipped.append(hid)
        continue
    fields = row["changedFields"]
    disposition = dispositions.get(hid, {})
    scope = row.get("incomingPlaceScope", "")
    obj = {
        "aliases": [],
        "category": fields.get("category", "待分类"),
        "conditions": fields.get("conditions", "") + (f"\n适用场所：{scope}" if scope else ""),
        "description": fields.get("description", ""),
        "id": hid,
        "keywords": words(fields.get("title", "")),
        "lifecycle": "proposed",
        "measures": fields.get("measures", ""),
        "mergedInto": None,
        "mode": "candidate",
        "note": f"Excel 2026-09-13 提案；来源行{row['sourceRow']}；处置={disposition.get('finalDisposition', 'candidate')}；{disposition.get('finalReason', '')}；依据：{row.get('directBasis', '')}",
        "places": [scope] if scope else ["待核验场所"],
        "title": fields.get("title", ""),
        "proposalStatus": disposition.get("finalDisposition", "candidate"),
        "sourceRow": row["sourceRow"],
    }
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    added.append(hid)

report = {"proposalRows": len(proposal["rows"]), "added": len(added), "skippedExisting": skipped, "lifecycle": "proposed", "published": False}
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
