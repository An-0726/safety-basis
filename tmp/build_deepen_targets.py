# -*- coding: utf-8 -*-
"""Phase B：筛"直接依据全部来自母法"的隐患 + 每条候选专项条款清单。

泛化母法 = 安全生产法 / 消防法 / 职业病防治法（交接书口径：安法 35/36 条等）。
候选专项条款 = 库内已核验条款中，与隐患标题/描述/关键词字符二元组重叠度最高的 8 条
（排除母法条款与已挂接条款）。
"""
import io
import json
import os
import glob
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOW = os.path.join(ROOT, "knowledge")

def load(sub):
    out = {}
    for p in glob.glob(os.path.join(KNOW, sub, "*.json")):
        out[os.path.basename(p)[:-5]] = json.load(io.open(p, encoding="utf-8"))
    return out

hazards, links, clauses = load("hazards"), load("links"), load("clauses")
lawvers = load("law-versions")
# clause -> 法规版本/法规名
clause_law = {}
for c in clauses.values():
    lv = lawvers.get(c.get("lawVersionId", ""), {})
    clause_law[c["id"]] = (lv.get("officialName", c.get("lawVersionId", "?")),
                           c.get("articlePath", ""), c.get("quote", ""))

MOTHER = ("安全生产法", "消防法", "职业病防治法")
def is_mother(cid):
    name = clause_law.get(cid, ("?",))[0]
    return any(m in name for m in MOTHER)

def bigrams(s):
    s = "".join(ch for ch in s if ch.strip())
    return {s[i:i+2] for i in range(len(s)-1)}

# 条款 bigram 索引
cbi = {cid: bigrams(q) for cid, (_, _, q) in clause_law.items() if q}

targets = []
for h in hazards.values():
    if h.get("lifecycle") != "active":
        continue
    ls = [l for l in links.values() if l.get("hazardId") == h["id"] and l.get("lifecycle") == "active"]
    directs = [l for l in ls if l.get("role") == "direct"]
    if not directs:
        continue
    if not all(is_mother(l["clauseId"]) for l in directs):
        continue
    cur = []
    for l in sorted(ls, key=lambda x: x["id"]):
        name, art, q = clause_law.get(l["clauseId"], ("?", "", ""))
        cur.append({"clauseId": l["clauseId"], "role": l["role"], "law": name,
                    "article": art, "quote": q[:110]})
    text = h["title"] + " " + h.get("description", "") + " " + " ".join(h.get("keywords", []))
    hb = bigrams(text)
    scored = []
    for cid, cb in cbi.items():
        if is_mother(cid) or any(l["clauseId"] == cid for l in ls):
            continue
        ov = len(hb & cb)
        if ov >= 6:
            scored.append((ov, cid))
    scored.sort(reverse=True)
    cands = []
    for ov, cid in scored[:8]:
        name, art, q = clause_law[cid]
        cands.append({"clauseId": cid, "law": name, "article": art, "quote": q[:160], "ov": ov})
    if cands:
        targets.append({"hazardId": h["id"], "title": h["title"], "category": h.get("category", ""),
                        "description": h.get("description", "")[:150],
                        "currentLinks": cur, "candidates": cands})

with io.open(os.path.join(ROOT, "tmp", "deepen_targets.json"), "w", encoding="utf-8", newline="\n") as f:
    json.dump(targets, f, ensure_ascii=False, indent=1)
print("targets:", len(targets))
no_cand = sum(1 for h in hazards.values() if h.get("lifecycle") == "active"
              and (lambda ls: ls and all(is_mother(l["clauseId"]) for l in ls if l.get("role") == "direct")
                   and any(l.get("role") == "direct" for l in ls))
              ([l for l in links.values() if l.get("hazardId") == h["id"] and l.get("lifecycle") == "active"]))
print("mother-only hazards (incl. no-candidate):", no_cand)
