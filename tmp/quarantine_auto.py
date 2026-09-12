# -*- coding: utf-8 -*-
"""下线全部自动反转隐患（保留批次1手工24条），恢复干净基线。"""
import json, glob, os, io, sys
sys.path.insert(0, "tools/v4")
import generate_hazards_from_clauses as g
batch1_clauses = {"C_GBT47236_" + s["clause"].replace(".", "_") for s in g.SPECS}
# 批次1的 hazard id
batch1_hids = {"H_GBT47236_" + s["clause"].replace(".", "_") for s in g.SPECS}
removed = 0
for f in glob.glob("knowledge/hazards/*.json"):
    d = json.load(open(f, encoding="utf-8"))
    if d["id"] in batch1_hids:
        continue
    if "反转生成" in d.get("note", ""):
        os.remove(f)
        rf = f.replace(os.sep + "hazards" + os.sep, os.sep + "reviews" + os.sep + "hazards" + os.sep)
        if os.path.exists(rf): os.remove(rf)
        removed += 1
rl = 0
for f in glob.glob("knowledge/links/*.json"):
    d = json.load(open(f, encoding="utf-8"))
    if d.get("hazardId", "").startswith("H_GBT47236_") and d["hazardId"] not in batch1_hids:
        os.remove(f)
        rf = f.replace(os.sep + "links" + os.sep, os.sep + "reviews" + os.sep + "links" + os.sep)
        if os.path.exists(rf): os.remove(rf)
        rl += 1
print("quarantined auto hazards:", removed, "| their links:", rl)
