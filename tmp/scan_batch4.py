# -*- coding: utf-8 -*-
import json, glob, re, os
bad_regulator, bad_prefix, ok = [], [], 0
REG = re.compile(r"(监督部门|监督管理部门|消防救援机构|人民政府|主管部门|市场监管|公安部门|应急管理部门|监管部门|监察机构|有关部门)")
PREFIX = re.compile(r"^第[一二三四五六七八九十百千0-9]{1,4}条")
for f in glob.glob("knowledge/hazards/*.json"):
    d = json.load(open(f, encoding="utf-8"))
    hid = d["id"]
    if not (hid.startswith("H_") and d.get("note", "").startswith("依据 第")):
        continue
    t = d["title"]
    if REG.search(t):
        bad_regulator.append((hid, t[:56])); continue
    if PREFIX.match(t):
        bad_prefix.append((hid, t[:56])); continue
    ok += 1
print("合格", ok, "| 监管职责类", len(bad_regulator), "| 条号前缀", len(bad_prefix))
for h, t in bad_regulator[:8]: print("  [监管]", h[:24], t)
for h, t in bad_prefix[:8]: print("  [前缀]", h[:24], t)
json.dump({"regulator": [h for h, _ in bad_regulator],
           "prefix": {h: t for h, t in bad_prefix}},
          open("tmp/batch4_quality.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
