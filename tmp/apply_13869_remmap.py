# -*- coding: utf-8 -*-
"""GB/T 13869 12 条隐患换挂 2026 版条款（用户指令：已发布最新版立即引用，旧版即撤）。"""
import glob
import hashlib
import io
import json
import os
import sys

KNOW = "knowledge"
sys.path.insert(0, "tools/v4")
sys.path.insert(0, "tools/pipeline")
from canonical import content_hash  # noqa: E402

def jload(p):
    return json.load(io.open(p, encoding="utf-8"))

def wj(p, o):
    io.open(p, "w", encoding="utf-8", newline="\n").write(
        json.dumps(o, ensure_ascii=False, indent=2) + "\n")

NOW = "2026-09-13"
MODEL = "GLM-5.3-Flash (ZCode)"
LV_NEW = "LV_STD_GBT13869_2026"
clauses = {os.path.basename(p)[:-5]: jload(p) for p in glob.glob(f"{KNOW}/clauses/*.json")}

target_a = next(cid for cid, d in clauses.items()
                if d.get("lawVersionId") == LV_NEW and "安全通道和工作空间" in d.get("quote", ""))
target_b = next(cid for cid, d in clauses.items()
                if d.get("lawVersionId") == LV_NEW and "有效执行电气作业" in d.get("quote", ""))
print("target A:", target_a, "| target B:", target_b)

OLD_A = "C_111e6a4f843a9547ddddf11b"
OLD_B = "C_GBT13869_9"

affected = {}
links = {}
for p in glob.glob(f"{KNOW}/links/*.json"):
    l = jload(p)
    links[l["id"]] = l
    if l.get("lifecycle") == "active" and l.get("clauseId") in (OLD_A, OLD_B):
        affected.setdefault(l["hazardId"], []).append(l["id"])

print("affected hazards:", len(affected))
assert len(affected) == 13, f"应为 13，实际 {len(affected)}"

existing = {(l.get("hazardId"), l.get("clauseId")) for l in links.values() if l.get("lifecycle") == "active"}
hazards = {os.path.basename(p)[:-5]: jload(p) for p in glob.glob(f"{KNOW}/hazards/*.json")}

created = 0
REASON = "GB/T 13869 新旧版衔接（用户指令 2026-09-13：已发布最新版立即引用，旧版即撤）"
for hid, old_ids in sorted(affected.items()):
    old_roles = {links[i]["role"] for i in old_ids}
    new_cid = target_b if any(links[i]["clauseId"] == OLD_B for i in old_ids) else target_a
    role = "supporting" if "supporting" in old_roles and "direct" not in old_roles else "direct"
    if (hid, new_cid) in existing:
        print("skip dup:", hid)
        continue
    kid = "K_" + hashlib.md5(f"{hid}|{new_cid}".encode()).hexdigest()[:24].upper()
    link = {"id": kid, "hazardId": hid, "clauseId": new_cid, "role": role,
            "legacyRole": "", "applicability": hazards[hid]["title"][:44] + "的现场状态。",
            "jurisdictionCode": "CN", "lifecycle": "active",
            "priority": 10 if role == "direct" else 20, "requirementId": "",
            "reason": "新旧版衔接换挂（GLM 逐条映射审核，2026-09-13）"}
    wj(f"{KNOW}/links/{kid}.json", link)
    links[kid] = link
    lrev = {"checkedAt": NOW, "contextHashes": {"clause": content_hash(clauses[new_cid]),
                                                "hazard": content_hash(hazards[hid])},
            "decision": "verified", "entityId": kid, "entityType": "link",
            "evidenceRefs": [], "reason": REASON,
            "reviewType": "applicability", "reviewedContentHash": content_hash(link),
            "reviewer": MODEL}
    wj(f"{KNOW}/reviews/links/{kid}.json", lrev)
    existing.add((hid, new_cid))
    created += 1
print("new links created:", created)

removed = 0
for hid, old_ids in affected.items():
    for lid in old_ids:
        os.remove(f"{KNOW}/links/{lid}.json")
        rp = f"{KNOW}/reviews/links/{lid}.json"
        if os.path.exists(rp):
            os.remove(rp)
        links.pop(lid, None)
        removed += 1
print("old links removed:", removed)
