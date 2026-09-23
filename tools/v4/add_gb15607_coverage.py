#!/usr/bin/env python3
"""Promote two existing powder-coating candidates and add one verified gap."""
from __future__ import annotations

import json
from pathlib import Path

from canonical import content_hash

KNOW = Path(__file__).resolve().parents[2] / "knowledge"
EVIDENCE = "E_15607_2023"
DATE = "2026-09-23"
CONDITION = "仅适用于采用粉末静电喷涂工艺的喷粉区；应核实喷粉室、设备和实际作业状态。"
SPEC = [
    (
        "H_15607_4_3_6_1", "4_3_6",
        "粉末静电喷涂人员操作区未按每6米配置紧急停止按钮",
        "粉末静电喷涂人员操作区每个操作面间隔6 m处未配置紧急停止按钮。",
        "按每个操作面间隔6 m配置紧急停止按钮，检查可触及性和停止功能。",
    ),
    (
        "H_15607_5_1_3_1", "5_1_3",
        "存在粉尘爆炸危险的喷粉设施仅用隔爆装置作为控爆措施",
        "存在粉尘爆炸危险的刚性粉末回收、净化、供粉装置或基本封闭喷粉室仅单独使用隔爆装置，未配置符合要求的控爆措施。",
        "按粉尘爆炸风险配置符合要求的控爆措施，不单独以隔爆装置作为唯一措施。",
    ),
    (
        "H_15607_7_1", "7_1",
        "喷粉区粉末涂料存量超过当班需要或包装破损外逸",
        "喷粉区存放的粉末涂料超过当班所需耗量，或包装破损、粉末外逸。",
        "控制喷粉区粉末涂料存量不超过当班所需耗量，保持包装完整并防止粉末外逸。",
    ),
]
OLD_CANDIDATE_LINKS = {
    "H_15607_4_3_6_1": "K_XLSX_WEB_6F4BBC0EED7998446198121C",
    "H_15607_5_1_3_1": "K_XLSX_WEB_F2A3485B33CA36587CDC9728",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    for hid, suffix, title, description, measures in SPEC:
        clause_id = "C_15607_" + suffix
        clause = load(KNOW / "clauses" / (clause_id + ".json"))
        crev = load(KNOW / "reviews" / "clauses" / (clause_id + ".json"))
        if crev.get("decision") != "verified" or crev.get("reviewedContentHash") != content_hash(clause):
            raise RuntimeError(f"Clause not verified: {clause_id}")

        hpath = KNOW / "hazards" / (hid + ".json")
        is_existing = hpath.exists()
        h = load(hpath) if is_existing else {
            "id": hid, "mode": "direct", "aliases": [], "mergedInto": None,
        }
        if is_existing and h["lifecycle"] not in ("proposed", "active"):
            raise RuntimeError(f"Unexpected hazard lifecycle: {hid}")
        h.update({
            "title": title, "description": description, "category": "涂装安全",
            "conditions": CONDITION + (
                " 仅在相关设施存在粉尘爆炸危险时适用。" if suffix == "5_1_3" else ""
            ),
            "measures": measures,
            "note": f"依据 GB 15607-2023 第{suffix.replace('_', '.')}条；现场判定仍需核实实际状态。",
            "keywords": ["粉末静电喷涂", title], "places": ["粉末静电喷涂喷粉区"],
            "lifecycle": "active",
        })
        save(hpath, h)
        hrev = {
            "entityId": hid, "entityType": "hazard", "reviewType": "definition",
            "decision": "verified", "reviewedContentHash": content_hash(h),
            "checkedAt": DATE, "reviewer": "Codex Local Agent",
            "evidenceRefs": [EVIDENCE],
            "reason": "核对现行 GB 15607-2023 的完整具体条款；已有候选保留稳定编号并收紧适用范围，新增项目已对照现有隐患去重。",
        }
        save(KNOW / "reviews" / "hazards" / (hid + ".json"), hrev)

        if hid in OLD_CANDIDATE_LINKS:
            old_id = OLD_CANDIDATE_LINKS[hid]
            old_review_path = KNOW / "reviews" / "links" / (old_id + ".json")
            old_review = load(old_review_path)
            old_review["contextHashes"]["hazard"] = content_hash(h)
            save(old_review_path, old_review)

        kid = f"K_15607_{suffix}_{hid}"
        link = {
            "id": kid, "hazardId": hid, "clauseId": clause_id, "role": "direct",
            "applicability": h["conditions"], "jurisdictionCode": "CN",
            "lifecycle": "active", "priority": 10,
            "reason": "该标准条款的工艺对象、具体义务和适用前提与隐患逐项对应。",
        }
        lpath = KNOW / "links" / (kid + ".json")
        if lpath.exists() and load(lpath) != link:
            raise RuntimeError(f"Refusing to overwrite changed link: {kid}")
        save(lpath, link)
        lrev = {
            "entityId": kid, "entityType": "link", "reviewType": "applicability",
            "decision": "verified", "reviewedContentHash": content_hash(link),
            "checkedAt": DATE, "reviewer": "Codex Local Agent",
            "evidenceRefs": [EVIDENCE],
            "contextHashes": {"clause": content_hash(clause), "hazard": content_hash(h)},
            "reason": link["reason"],
        }
        save(KNOW / "reviews" / "links" / (kid + ".json"), lrev)
    print("curated: 2 proposed hazards promoted, 1 new active hazard, 3 direct links")


if __name__ == "__main__":
    main()
