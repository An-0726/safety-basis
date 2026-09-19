# -*- coding: utf-8 -*-
"""One-time audited GB/T 12801 version-transition maintenance script.

Kept for traceability. It is not part of the routine build and must not be
rerun without reviewing the hard-coded entity IDs and legal-status dates.
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

NOW = "2026-09-12"
MODEL = "GLM-5.3-Flash (ZCode)"


def wj(path, value):
    io.open(path, "w", encoding="utf-8", newline="\n").write(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def jload(path):
    return json.load(io.open(path, encoding="utf-8"))


for cid in ("C_12801_5", "C_12801_5_9_1"):
    for path in (f"{KNOW}/clauses/{cid}.json", f"{KNOW}/reviews/clauses/{cid}.json"):
        if os.path.exists(path):
            os.remove(path)

NEW_574 = "C_12801_5_7_4"
NEW_575 = "C_12801_5_7_5"
NEW_562 = "C_12801_5_6_2"
OLD_574 = "C_3B764981E731EA8D2F1B2B0C59"
OLD_546 = "C_GB12801_5_4_6"
OLD_562 = "C_GBT12801_5_7_1_C"
MAP_574 = ["H_1507C0C16EB84487BA", "H_3B764981E731EA8D2F", "H_608147EE09234EBC92", "H_8855020E458243468B", "H_2608B93F77A149399B", "H_2E28B7A14EFE498F90", "H_6F917217CE9748479D", "H_D52A0DF6DCCD445DBB"]
MAP_575 = ["H_42356AF341B9414E85", "H_4E1F7C3FFB724997B5", "H_85C9BDCE54474AEEBD", "H_B085FE55797E498897", "H_C3C0BC82FBF7414392", "H_CD20735BC6DB47CE9C", "H_GB12801_5_4_6_1", "H_GB12801_5_4_6_2", "H_GB12801_5_4_6_3", "H_GB12801_5_4_6_4"]
MAP_562 = ["H_96B64979BEB2440B93"]

hazards = {os.path.basename(p)[:-5]: jload(p) for p in glob.glob(f"{KNOW}/hazards/*.json")}


def full_id(prefix):
    hits = [hid for hid in hazards if hid.startswith(prefix)]
    if len(hits) != 1:
        sys.exit(f"prefix {prefix}: {len(hits)} matches")
    return hits[0]


MAP_574 = [full_id(value) for value in MAP_574]
MAP_575 = [full_id(value) for value in MAP_575]
MAP_562 = [full_id(value) for value in MAP_562]
clauses = {os.path.basename(p)[:-5]: jload(p) for p in glob.glob(f"{KNOW}/clauses/*.json")}
links = {os.path.basename(p)[:-5]: jload(p) for p in glob.glob(f"{KNOW}/links/*.json")}
existing = {(link.get("hazardId"), link.get("clauseId")) for link in links.values() if link.get("lifecycle") == "active"}
reason = "GB/T 12801 新旧版衔接（GLM，2026-09-12）：旧版 GB/T 12801-2008 条款 2026-09-30 到期，预建 GB 12801-2025 对应条款直接依据，新版 2026-10-01 起自动接管。"

for new_cid, old_cid, hids in ((NEW_574, OLD_574, MAP_574), (NEW_575, OLD_546, MAP_575), (NEW_562, OLD_562, MAP_562)):
    clause = clauses[new_cid]
    for hid in hids:
        if (hid, new_cid) in existing:
            continue
        kid = "K_" + hashlib.md5(f"{hid}|{new_cid}".encode()).hexdigest()[:24].upper()
        hazard = hazards[hid]
        link = {"id": kid, "hazardId": hid, "clauseId": new_cid, "role": "direct", "legacyRole": "", "applicability": hazard["title"][:44] + "的现场状态。", "jurisdictionCode": "CN", "lifecycle": "active", "priority": 10, "requirementId": "", "reason": "新版条款对应旧版" + clauses[old_cid].get("articlePath", "") + "（GLM 逐条映射审核，2026-09-12）"}
        wj(f"{KNOW}/links/{kid}.json", link)
        review = {"checkedAt": NOW, "contextHashes": {"clause": content_hash(clause), "hazard": content_hash(hazard)}, "decision": "verified", "entityId": kid, "entityType": "link", "evidenceRefs": [], "reason": reason, "reviewType": "applicability", "reviewedContentHash": content_hash(link), "reviewer": MODEL}
        wj(f"{KNOW}/reviews/links/{kid}.json", review)
        existing.add((hid, new_cid))

for lid, link in list(links.items()):
    if link.get("lifecycle") == "active" and link.get("clauseId") in (OLD_574, OLD_546, OLD_562):
        os.remove(f"{KNOW}/links/{lid}.json")
        review_path = f"{KNOW}/reviews/links/{lid}.json"
        if os.path.exists(review_path):
            os.remove(review_path)

succession = {"effectiveDate": "2026-10-01", "id": "LS_" + hashlib.md5("GBT12801-2008->2025".encode()).hexdigest()[:24].upper(), "legacyRelation": "replaced_by", "newVersionId": "LV_STD_GB12801", "oldVersionId": "LV_STD_GB12801_2008", "relation": "replaces", "scope": "GB 12801-2025《生产过程安全基本要求》替代 GB/T 12801-2008《生产过程安全卫生要求总则》（2026-10-01 实施；19 条隐患已预建新版条款链接，1 条倡导性要求新版无对应条款自然退出）。"}
path = f"{KNOW}/successions/{succession['id']}.json"
if not os.path.exists(path):
    wj(path, succession)
