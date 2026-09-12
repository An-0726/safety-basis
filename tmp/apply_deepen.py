# -*- coding: utf-8 -*-
"""Phase B 应用：新增专项 direct 链接 + 母法 direct 降级 supporting。

链接/审阅结构完全对齐 generate_hazards_from_clauses 的 lrev 惯例；
新链接 id = K_ + md5(hazardId|clauseId) 前 24 位十六进制（确定性，可重跑）。
"""
import glob
import hashlib
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOW = os.path.join(ROOT, "knowledge")
sys.path.insert(0, os.path.join(ROOT, "tools", "v4"))
sys.path.insert(0, os.path.join(ROOT, "tools", "pipeline"))
from canonical import content_hash  # noqa: E402

NOW = "2026-09-12"
MODEL = "GLM-5.3-Flash (ZCode)"
MOTHER = ("安全生产法", "消防法", "职业病防治法")


def load(sub):
    out = {}
    for p in glob.glob(os.path.join(KNOW, sub, "*.json")):
        out[os.path.basename(p)[:-5]] = json.load(io.open(p, encoding="utf-8"))
    return out


def wj(p, o):
    io.open(p, "w", encoding="utf-8", newline="\n").write(
        json.dumps(o, ensure_ascii=False, indent=2) + "\n")


def wjson(p, o):
    io.open(p, "w", encoding="utf-8", newline="\n").write(
        json.dumps(o, ensure_ascii=False, indent=1) + "\n")


def jload(p):
    return json.load(io.open(p, encoding="utf-8"))


hazards, links, clauses = load("hazards"), load("links"), load("clauses")
lawvers = load("law-versions")
clause_lv = {c["id"]: c.get("lawVersionId", "") for c in clauses.values()}

def law_name(cid):
    return lawvers.get(clause_lv.get(cid, ""), {}).get("officialName", "?")

def is_mother(cid):
    return any(m in law_name(cid) for m in MOTHER)

# 汇总 6 份裁决
verdicts = []
bad = 0
for c in range(1, 7):
    inp = {d["hazardId"]: d for d in jload(os.path.join(ROOT, "tmp", f"deepen_in_{c}.json"))}
    out = jload(os.path.join(ROOT, "tmp", f"deepen_out_{c}.json"))
    if len(out) != len(inp):
        sys.exit(f"chunk {c}: out {len(out)} != in {len(inp)}")
    for d in out:
        h = inp.get(d["hazardId"])
        if h is None:
            sys.exit(f"chunk {c}: 未知 hazardId {d['hazardId']}")
        cand_ids = {x["clauseId"] for x in h["candidates"]}
        picks = d.get("direct", [])
        if not picks and not d.get("skipReason"):
            bad += 1
        for pk in picks:
            if pk["clauseId"] not in cand_ids:
                bad += 1
                print(f"  ! {d['hazardId']}: 非法候选 {pk['clauseId']}")
        verdicts.append((d, h))
if bad:
    sys.exit(f"校验失败 {bad} 处")

existing_pairs = {(l["hazardId"], l["clauseId"]) for l in links.values() if l.get("lifecycle") == "active"}
added, demoted, skipped_dup = 0, 0, 0
for d, h in verdicts:
    hid = d["hazardId"]
    picks = d.get("direct", [])
    if not picks:
        continue
    for pk in picks:
        cid = pk["clauseId"]
        if (hid, cid) in existing_pairs:
            skipped_dup += 1
            continue
        kid = "K_" + hashlib.md5(f"{hid}|{cid}".encode()).hexdigest()[:24].upper()
        if kid in links:
            skipped_dup += 1
            continue
        link = {"id": kid, "hazardId": hid, "clauseId": cid, "role": "direct",
                "legacyRole": "", "applicability": h["title"][:44] + "的现场状态。",
                "jurisdictionCode": "CN", "lifecycle": "active", "priority": 10,
                "requirementId": "", "reason": pk["reason"] + "（GLM 专项依据审核，2026-09-12）"}
        wj(os.path.join(KNOW, "links", kid + ".json"), link)
        haz = hazards[hid]
        clause = clauses[cid]
        lrev = {"checkedAt": NOW, "contextHashes": {"clause": content_hash(clause),
                                                    "hazard": content_hash(haz)},
                "decision": "verified", "entityId": kid, "entityType": "link",
                "evidenceRefs": [],
                "reason": "专项技术依据审核（GLM）：条款原文具体规定本隐患所违反的要求，"
                          "原母法通用条款降级为 supporting。",
                "reviewType": "applicability", "reviewedContentHash": content_hash(link),
                "reviewer": MODEL}
        wj(os.path.join(KNOW, "reviews", "links", kid + ".json"), lrev)
        links[kid] = link
        existing_pairs.add((hid, cid))
        added += 1
    # 母法 direct 降级 supporting
    for lid, l in list(links.items()):
        if l.get("hazardId") == hid and l.get("role") == "direct" and is_mother(l["clauseId"]):
            l2 = dict(l, role="supporting", priority=20,
                      reason="该隐患已具备专项技术条款直接依据，母法通用义务改作上位法补充"
                             "（GLM，2026-09-12）。")
            wj(os.path.join(KNOW, "links", lid + ".json"), l2)
            links[lid] = l2
            rp = os.path.join(KNOW, "reviews", "links", lid + ".json")
            if os.path.exists(rp):
                r = jload(rp)
                r["reviewedContentHash"] = content_hash(l2)
                r["reason"] = r.get("reason", "") + "（链接降级 supporting 后哈希同步更新，2026-09-12）"
                wj(rp, r)
            demoted += 1

summary = {"added_direct_links": added, "demoted_to_supporting": demoted,
           "duplicates_skipped": skipped_dup,
           "hazards_with_direct": sum(1 for d, _ in verdicts if d.get("direct")),
           "hazards_skipped": sum(1 for d, _ in verdicts if not d.get("direct"))}
wjson(os.path.join(ROOT, "tmp", "deepen_summary.json"), summary)
print(json.dumps(summary, ensure_ascii=False))
