# -*- coding: utf-8 -*-
"""One-time audited GB/T 13869 clause-remapping maintenance script.

Kept for traceability. It is not part of the routine build and must not be
rerun without reviewing the hard-coded entity IDs and legal-status policy.
"""
import glob
import hashlib
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")
sys.path.insert(0, os.path.join(ROOT, "tools", "v4"))
sys.path.insert(0, os.path.join(ROOT, "tools", "pipeline"))
from canonical import content_hash  # noqa: E402


def jload(path):
    return json.load(io.open(path, encoding="utf-8"))


def wj(path, value):
    io.open(path, "w", encoding="utf-8", newline="\n").write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


now = "2026-09-13"
model = "GLM-5.3-Flash (ZCode)"
new_version = "LV_STD_GBT13869_2026"
clauses = {os.path.basename(p)[:-5]: jload(p) for p in glob.glob(f"{KNOW}/clauses/*.json")}
target_a = next(cid for cid, data in clauses.items() if data.get("lawVersionId") == new_version and "安全通道和工作空间" in data.get("quote", ""))
target_b = next(cid for cid, data in clauses.items() if data.get("lawVersionId") == new_version and "有效执行电气作业" in data.get("quote", ""))
old_a = "C_111e6a4f843a9547ddddf11b"
old_b = "C_GBT13869_9"
affected = {}
links = {}
for path in glob.glob(f"{KNOW}/links/*.json"):
    link = jload(path)
    links[link["id"]] = link
    if link.get("lifecycle") == "active" and link.get("clauseId") in (old_a, old_b):
        affected.setdefault(link["hazardId"], []).append(link["id"])
assert len(affected) == 13, f"应为 13，实际 {len(affected)}"

existing = {(link.get("hazardId"), link.get("clauseId")) for link in links.values() if link.get("lifecycle") == "active"}
hazards = {os.path.basename(p)[:-5]: jload(p) for p in glob.glob(f"{KNOW}/hazards/*.json")}
reason = "GB/T 13869 新旧版衔接（用户指令 2026-09-13：已发布最新版立即引用，旧版即撤）"
for hid, old_ids in sorted(affected.items()):
    roles = {links[lid]["role"] for lid in old_ids}
    new_cid = target_b if any(links[lid]["clauseId"] == old_b for lid in old_ids) else target_a
    role = "supporting" if "supporting" in roles and "direct" not in roles else "direct"
    if (hid, new_cid) in existing:
        continue
    kid = "K_" + hashlib.md5(f"{hid}|{new_cid}".encode()).hexdigest()[:24].upper()
    link = {"id": kid, "hazardId": hid, "clauseId": new_cid, "role": role, "legacyRole": "", "applicability": hazards[hid]["title"][:44] + "的现场状态。", "jurisdictionCode": "CN", "lifecycle": "active", "priority": 10 if role == "direct" else 20, "requirementId": "", "reason": "新旧版衔接换挂（GLM 逐条映射审核，2026-09-13）"}
    wj(f"{KNOW}/links/{kid}.json", link)
    review = {"checkedAt": now, "contextHashes": {"clause": content_hash(clauses[new_cid]), "hazard": content_hash(hazards[hid])}, "decision": "verified", "entityId": kid, "entityType": "link", "evidenceRefs": [], "reason": reason, "reviewType": "applicability", "reviewedContentHash": content_hash(link), "reviewer": model}
    wj(f"{KNOW}/reviews/links/{kid}.json", review)
    existing.add((hid, new_cid))

for old_ids in affected.values():
    for lid in old_ids:
        os.remove(f"{KNOW}/links/{lid}.json")
        review_path = f"{KNOW}/reviews/links/{lid}.json"
        if os.path.exists(review_path):
            os.remove(review_path)
