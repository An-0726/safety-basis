# -*- coding: utf-8 -*-
"""深度审查 6 条候选及其拟绑条款的每一个细节。"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
KNOW = ROOT / "knowledge"

candidates = [
    ("H_12158_4_2_2_3_1", "C_12158_4_2_2_3"),
    ("H_12158_6_3_1_1", "C_12158_6_3_1"),
    ("H_12158_7_1_1", "C_12158_7_1"),
    ("H_08C1576EE4824ED8BE0CDD56DF", "C_GB50140_5_1_3"),
    ("H_0A9DDC2534BC46FDA9AEE80A89", "C_EB1C00891F0F010C3E8DE36882"),
    ("H_1507C0C16EB84487BA78230E0D", "C_3B764981E731EA8D2F1B2B0C59")
]

for hid, cid in candidates:
    h = json.loads((KNOW / "hazards" / f"{hid}.json").read_text(encoding="utf-8"))
    c = json.loads((KNOW / "clauses" / f"{cid}.json").read_text(encoding="utf-8"))
    lvid = c["lawVersionId"]
    lv = json.loads((KNOW / "law-versions" / f"{lvid}.json").read_text(encoding="utf-8"))
    print("========================================")
    print("HAZARD ID:", hid)
    print("Title:", h.get("title"))
    print("Description:", h.get("description"))
    print("Conditions:", h.get("conditions"))
    print("Category:", h.get("category"))
    print("Note:", h.get("note"))
    print("---")
    print("CLAUSE ID:", cid)
    print("ArticlePath:", c.get("articlePath"))
    print("Quote:", c.get("quote"))
    print("LawVersion:", lv.get("documentNumber"), "|", lv.get("title"), "| validity:", lv.get("validityStatus"), "| eff:", lv.get("effectiveDate"))
