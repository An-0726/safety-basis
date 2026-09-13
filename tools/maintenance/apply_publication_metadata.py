# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / "source/proposals/excel-20260913/publication-metadata-proposal.json"
TARGET = ROOT / "source/publication/law-index.json"

proposal = json.loads(PROPOSAL.read_text(encoding="utf-8"))
catalog = json.loads(TARGET.read_text(encoding="utf-8"))
known = {row["id"] for row in catalog}
added = []
for item in proposal.get("items", []):
    if item["id"] in known:
        continue
    row = {key: value for key, value in item.items() if key not in {"privateFulltextOnly", "statusNote"}}
    catalog.append(row)
    known.add(row["id"])
    added.append(row["id"])
catalog.sort(key=lambda row: (str(row.get("name", "")), str(row.get("id", ""))))
TARGET.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
report = {"before": len(catalog) - len(added), "added": len(added), "after": len(catalog), "ids": added}
(ROOT / "source/proposals/excel-20260913/publication-metadata-apply-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
