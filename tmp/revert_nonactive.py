# -*- coding: utf-8 -*-
"""Phase B 撤销：删除指向非现行版本条款的新 direct 链接；受影响隐患恢复母法 direct。"""
import glob
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOW = os.path.join(ROOT, "knowledge")
sys.path.insert(0, os.path.join(ROOT, "tools", "v4"))
sys.path.insert(0, os.path.join(ROOT, "tools", "pipeline"))
from canonical import content_hash  # noqa: E402

def load(sub):
    out = {}
    for p in glob.glob(os.path.join(KNOW, sub, "*.json")):
        out[os.path.basename(p)[:-5]] = json.load(io.open(p, encoding="utf-8"))
    return out

def wj(p, o):
    io.open(p, "w", encoding="utf-8", newline="\n").write(
        json.dumps(o, ensure_ascii=False, indent=2) + "\n")

def jload(p):
    return json.load(io.open(p, encoding="utf-8"))

hazards, links, clauses = load("hazards"), load("links"), load("clauses")
lawvers = load("law-versions")
clause_lv = {c["id"]: c.get("lawVersionId", "") for c in clauses.values()}
lv_status = {k: v.get("validityStatus", "?") for k, v in lawvers.items()}

# 我本轮新增的链接：review reason 以"专项技术依据审核"开头
new_links = {}
for p in glob.glob(os.path.join(KNOW, "reviews", "links", "*.json")):
    r = jload(p)
    if str(r.get("reason", "")).startswith("专项技术依据审核"):
        new_links[r["entityId"]] = p
print("new links:", len(new_links))

removed, by_hazard = 0, {}
for kid, rp in new_links.items():
    lp = os.path.join(KNOW, "links", kid + ".json")
    link = jload(lp)
    st = lv_status.get(clause_lv.get(link["clauseId"], ""), "?")
    if st == "active":
        continue
    os.remove(lp); os.remove(rp)
    links.pop(kid, None)
    removed += 1
    by_hazard.setdefault(link["hazardId"], []).append((kid, st))
print("removed non-active-version links:", removed, "| statuses:", {s: sum(1 for v in by_hazard.values() for _, s2 in v for s in [s2]) for s in []} or {})

# 每个受影响隐患：若已无任何 direct 链接 → 恢复其被我降级的母法链接
restored = 0
for hid in by_hazard:
    directs = [l for l in links.values() if l.get("hazardId") == hid
               and l.get("role") == "direct" and l.get("lifecycle") == "active"]
    if directs:
        continue
    for lid, l in list(links.items()):
        if (l.get("hazardId") == hid and l.get("role") == "supporting"
                and "母法通用义务改作上位法补充" in str(l.get("reason", ""))):
            l2 = dict(l, role="direct", priority=10,
                      reason="恢复 direct：本次新增的专项条款属非现行版本，撤销改判（GLM，2026-09-12）。")
            wj(os.path.join(KNOW, "links", lid + ".json"), l2)
            links[lid] = l2
            rp = os.path.join(KNOW, "reviews", "links", lid + ".json")
            if os.path.exists(rp):
                r = jload(rp)
                r["reviewedContentHash"] = content_hash(l2)
                r["reason"] = str(r.get("reason", "")).replace(
                    "（链接降级 supporting 后哈希同步更新，2026-09-12）", "")
                wj(rp, r)
            restored += 1
print("restored mother directs:", restored)
