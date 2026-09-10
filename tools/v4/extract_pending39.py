# -*- coding: utf-8 -*-
"""提取当前所有 pending link 的完整上下文，输出供逐条研判。"""
import glob
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = "knowledge"


def load_dir(sub):
    out = {}
    for f in glob.glob(os.path.join(BASE, sub, "*.json")):
        d = json.load(io.open(f, encoding="utf-8"))
        eid = d.get("id") or d.get("entityId")
        out[eid] = d
    return out


links = load_dir("links")
hazards = load_dir("hazards")
clauses = load_dir("clauses")
lvs = load_dir("law-versions")
laws = load_dir("laws")
evidence = load_dir("evidence")
reviews = load_dir("reviews/links")

pending = [r for r in reviews.values() if r.get("decision") == "pending"]
print(f"pending reviews: {len(pending)}\n")

rows = []
for r in sorted(pending, key=lambda x: x.get("entityId", "")):
    lid = r.get("entityId")
    link = links.get(lid, {})
    hid = link.get("hazardId") or (link.get("hazard") or {}).get("id")
    cid = link.get("clauseId") or (link.get("clause") or {}).get("id")
    haz = hazards.get(hid, {})
    cl = clauses.get(cid, {})
    lv = lvs.get(cl.get("lawVersionId", ""), {})
    law = laws.get(lv.get("lawId", ""), {})
    evrefs = r.get("evidenceRefs", [])
    evs = [evidence.get(e, {}).get("url", "?") for e in evrefs if e in evidence]
    rows.append({
        "link": lid, "hazard": hid, "clause": cid,
        "h_title": haz.get("title", ""), "h_desc": (haz.get("description") or "")[:120],
        "h_cond": (haz.get("conditions") or "")[:150],
        "law": law.get("name", ""), "lv": lv.get("versionLabel", "") or lv.get("effectiveDate", ""),
        "clause_text": (cl.get("text") or cl.get("content") or "")[:180],
        "codes": r.get("reasonCodes", []),
        "reason": (r.get("reason") or "")[:250],
        "evidence": evs,
    })

for i, x in enumerate(rows, 1):
    print(f"### {i}. {x['link']}  hazard={x['hazard']}  clause={x['clause']}")
    print(f"  HAZ: {x['h_title']} | {x['h_desc']}")
    print(f"  COND: {x['h_cond']}")
    print(f"  LAW: {x['law']} {x['lv']}")
    print(f"  CLAUSE: {x['clause_text']}")
    print(f"  CODES: {x['codes']}")
    print(f"  REASON: {x['reason']}")
    print(f"  EVIDENCE: {x['evidence']}")
    print()

with io.open("tools/workbooks/pending_39_workbook.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)
print("workbook saved: tools/workbooks/pending_39_workbook.json")
