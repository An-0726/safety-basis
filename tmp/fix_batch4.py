# -*- coding: utf-8 -*-
"""批次 3/4 自动反转隐患质量修正：监管职责类删除、条号前缀清洗。"""
import json, glob, re, os, sys
sys.path.insert(0, "tools/v4"); sys.path.insert(0, "tools/pipeline")
from canonical import content_hash
import hazard_quality

REG = re.compile(r"(监督部门|监督管理部门|消防救援机构|人民政府|主管部门|市场监管|公安部门|应急管理部门|监管部门|监察机构|负有.{0,6}职责的|有关地方人民政府|行政部门)")
PREFIX = re.compile(r"^第[一二三四五六七八九十百千0-9]{1,4}条\s*")

hazards = {}
for f in glob.glob("knowledge/hazards/*.json"):
    d = json.load(open(f, encoding="utf-8"))
    if "反转生成" in d.get("note", ""):
        hazards[d["id"]] = (f, d)
links = {}
for f in glob.glob("knowledge/links/*.json"):
    d = json.load(open(f, encoding="utf-8"))
    if d.get("hazardId") in hazards:
        links[d["hazardId"]] = (f, d)

norm_titles = {}
for f in glob.glob("knowledge/hazards/*.json"):
    d = json.load(open(f, encoding="utf-8"))
    if d["id"] not in hazards:
        norm_titles.setdefault(hazard_quality.normalized_title(d["title"]), set()).add(d["id"])

to_delete, to_fix, errs = [], [], []
for hid, (f, d) in hazards.items():
    t = d["title"]
    if REG.search(t):
        to_delete.append(hid); continue
    if PREFIX.match(t):
        newt = PREFIX.sub("", t).strip()
        nt = hazard_quality.normalized_title(newt)
        dup = nt in norm_titles and hid not in norm_titles.get(nt, set())
        if len(newt) < 8 or dup or hazard_quality.text_errors(newt):
            to_delete.append(hid); continue
        to_fix.append((hid, f, newt))
        continue
    if hazard_quality.text_errors(t):
        errs.append(hid)

print("待删除(监管职责/清洗后无效):", len(to_delete), "| 待清洗前缀:", len(to_fix), "| 其他问题:", len(errs))

# 删除：hazard + link + 双 review
import shutil
dels = set(to_delete)
for hid in list(dels):
    f, _ = hazards[hid]
    os.remove(f)
    rf = f.replace(os.sep + "hazards" + os.sep, os.sep + "reviews" + os.sep + "hazards" + os.sep)
    if os.path.exists(rf): os.remove(rf)
    if hid in links:
        lf, ld = links[hid]
        os.remove(lf)
        lrf = lf.replace(os.sep + "links" + os.sep, os.sep + "reviews" + os.sep + "links" + os.sep)
        if os.path.exists(lrf): os.remove(lrf)

# 清洗前缀
fixed = 0
for hid, f, newt in to_fix:
    if hid in dels: continue
    d = json.load(open(f, encoding="utf-8"))
    d["title"] = newt
    if PREFIX.match(d.get("description", "")):
        d["description"] = PREFIX.sub("", d["description"]).strip()
    json.dump(d, open(f, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2)
    rp = f.replace(os.sep + "hazards" + os.sep, os.sep + "reviews" + os.sep + "hazards" + os.sep)
    r = json.load(open(rp, encoding="utf-8"))
    r["reviewedContentHash"] = content_hash(d)
    r["reason"] = (r.get("reason") or "") + "\n2026-09-12 GLM 修订：清洗标题中的条号前缀，通用化写法。"
    json.dump(r, open(rp, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2)
    fixed += 1
print("前缀清洗完成:", fixed)
