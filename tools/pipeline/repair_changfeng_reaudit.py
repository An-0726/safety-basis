#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Re-audit the Changfeng ingestion against verified, evidence-backed clauses.

The original ingestion published every generated hazard/link as active + verified,
even when the review contained no evidenceRefs.  This migration keeps only the
entities that can be directly supported by an existing verified clause and moves
the remaining general hazards back to the non-public candidate lifecycle.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
KNOW = ROOT / "knowledge"
HAZARDS = KNOW / "hazards"
LINKS = KNOW / "links"
HAZARD_REVIEWS = KNOW / "reviews" / "hazards"
LINK_REVIEWS = KNOW / "reviews" / "links"
CLAUSE_REVIEWS = KNOW / "reviews" / "clauses"
CLAUSES = KNOW / "clauses"

sys.path.insert(0, str(ROOT / "tools" / "v4"))
from canonical import content_hash  # noqa: E402


CHECKED_AT = "2026-09-19T17:00:00+08:00"
REVIEWER = "Codex / Changfeng Re-audit 2026-09-19"


GENERAL_FIXES = {
    "H_CF_GEN_04": {
        "clauseId": "C035",
        "title": "厂内特种设备未经定期检验或超过检验有效期继续使用",
        "description": "叉车、桥式起重机、电梯等依法纳入特种设备范围的设备，未经定期检验或者超过检验有效期仍继续使用。",
        "measures": "立即停止使用未经定期检验或检验超期的设备；按规定申报定期检验，检验合格后方可恢复使用，并建立检验到期提醒台账。",
        "places": ["企业厂区内依法纳入特种设备范围的叉车、起重机械、电梯等设备使用场所"],
        "keywords": ["特种设备", "定期检验", "超期使用", "叉车", "起重机械"],
        "applicability": "依法纳入特种设备范围的在用设备定期检验状态核查。",
    },
    "H_CF_GEN_26": {
        "clauseId": "C_SAFE_LAW_81_1",
        "title": "未定期组织生产安全事故应急预案演练",
        "description": "生产经营单位未按规定定期组织生产安全事故应急救援预案演练。",
        "measures": "制定应急演练计划并定期组织实施，留存演练方案、签到、过程记录和总结等资料。",
        "places": ["生产经营单位及其生产作业场所"],
        "keywords": ["应急预案", "应急演练", "定期演练", "演练记录"],
        "applicability": "生产经营单位是否定期组织生产安全事故应急救援预案演练。",
    },
    "H_CF_GEN_27": {
        "clauseId": "C_SAFE_LAW_41_2",
        "title": "事故隐患排查治理情况未如实记录",
        "description": "生产经营单位开展事故隐患排查治理后，未如实记录隐患排查治理情况，造成治理过程和结果无法核查。",
        "measures": "如实记录隐患排查治理情况，明确隐患、治理措施和完成情况，并按规定向从业人员通报。",
        "places": ["生产经营单位及各生产作业区域"],
        "keywords": ["隐患排查治理", "如实记录", "治理记录", "从业人员通报"],
        "applicability": "生产安全事故隐患排查治理情况是否如实记录并按规定向从业人员通报。",
    },
    "H_CF_GEN_28": {
        "clauseId": "C039",
        "title": "特种作业人员未取得相应资格上岗作业",
        "description": "属于国家规定特种作业范围的电工作业、焊接与热切割作业、高处作业等岗位人员，未经专门安全作业培训并取得相应资格即上岗作业。",
        "measures": "立即停止无相应资格人员的特种作业；组织参加专门安全作业培训并取得相应资格后再上岗，建立持证人员台账并核验证件有效状态。",
        "places": ["电工作业、焊接与热切割作业、高处作业等特种作业岗位"],
        "keywords": ["特种作业", "专门安全作业培训", "相应资格", "持证上岗", "无证作业"],
        "applicability": "属于国家规定特种作业范围的人员是否经专门安全作业培训并取得相应资格后上岗。",
    },
}


MAJOR_05_FIX = {
    "title": "有限空间未辨识建账且未设置明显安全警示标志",
    "description": "存在有限空间的工贸企业，未对有限空间进行辨识、建立安全管理台账，并且未设置明显的安全警示标志，构成重大事故隐患。",
    "measures": "立即辨识有限空间并建立安全管理台账，在有限空间醒目位置设置明显的安全警示标志；完成整改并复查确认。",
    "places": ["存在有限空间的工贸企业相关场所"],
    "keywords": ["有限空间", "辨识", "安全管理台账", "安全警示标志", "重大事故隐患"],
}


CANDIDATE_NOTE = (
    "2026-09-19 复核：现有关联条款不足以直接支撑该具体隐患的违法构成或具体整改要求，"
    "降为 proposed 候选；待补充现行、直接、经核验的法规标准依据后再发布。"
)


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def clause_evidence(clause_id: str) -> list[str]:
    review_path = CLAUSE_REVIEWS / f"{clause_id}.json"
    if not review_path.exists():
        raise RuntimeError(f"missing clause review: {clause_id}")
    review = load_json(review_path)
    refs = list(review.get("evidenceRefs") or [])
    if review.get("decision") != "verified" or not refs:
        raise RuntimeError(f"clause lacks verified evidence: {clause_id}")
    if not (CLAUSES / f"{clause_id}.json").exists():
        raise RuntimeError(f"missing clause entity: {clause_id}")
    return refs


def make_hazard_review(hazard: dict, decision: str, evidence_refs: list[str], reason: str) -> dict:
    return {
        "entityType": "hazard",
        "entityId": hazard["id"],
        "reviewType": "definition",
        "decision": decision,
        "reviewedContentHash": content_hash(hazard),
        "checkedAt": CHECKED_AT,
        "reviewer": REVIEWER,
        "reason": reason,
        "evidenceRefs": evidence_refs,
    }


def make_link_review(link: dict, hazard: dict, decision: str, evidence_refs: list[str], reason: str) -> dict:
    clause = load_json(CLAUSES / f"{link['clauseId']}.json")
    return {
        "entityType": "link",
        "entityId": link["id"],
        "reviewType": "applicability",
        "decision": decision,
        "reviewedContentHash": content_hash(link),
        "contextHashes": {
            "hazard": content_hash(hazard),
            "clause": content_hash(clause),
        },
        "checkedAt": CHECKED_AT,
        "reviewer": REVIEWER,
        "reason": reason,
        "evidenceRefs": evidence_refs,
    }


def all_links() -> dict[str, dict]:
    result = {}
    for path in LINKS.glob("*.json"):
        obj = load_json(path)
        result[obj["id"]] = obj
    return result


def links_for_hazard(links: dict[str, dict], hazard_id: str) -> list[dict]:
    return [link for link in links.values() if link.get("hazardId") == hazard_id]


def set_link_candidate(link: dict, hazard: dict, reason: str) -> None:
    link["lifecycle"] = "proposed"
    write_json(LINKS / f"{link['id']}.json", link)
    review = make_link_review(link, hazard, "pending", [], reason)
    write_json(LINK_REVIEWS / f"{link['id']}.json", review)


def active_link_for(hazard: dict, clause_id: str, applicability: str) -> dict:
    link_id = f"K_CF_{hazard['id'].replace('H_CF_', '')}_{clause_id}"
    return {
        "applicability": applicability,
        "clauseId": clause_id,
        "hazardId": hazard["id"],
        "id": link_id,
        "jurisdictionCode": "CN",
        "legacyRole": "直接依据",
        "lifecycle": "active",
        "priority": 10,
        "role": "direct",
    }


def repair_general(links: dict[str, dict]) -> tuple[int, int]:
    general_paths = sorted(HAZARDS.glob("H_CF_GEN_*.json"))
    if len(general_paths) != 28:
        raise RuntimeError(f"expected 28 Changfeng general hazards, found {len(general_paths)}")

    retained = 0
    candidate = 0
    for path in general_paths:
        hazard = load_json(path)
        hid = hazard["id"]
        current_links = links_for_hazard(links, hid)

        if hid not in GENERAL_FIXES:
            hazard["lifecycle"] = "proposed"
            hazard["mode"] = "candidate"
            hazard["note"] = CANDIDATE_NOTE
            write_json(path, hazard)
            reason = "当前缺少能够直接支撑该具体隐患表述的现行、经核验法规标准依据，暂不进入公开发布。"
            write_json(HAZARD_REVIEWS / f"{hid}.json", make_hazard_review(hazard, "pending", [], reason))
            for link in current_links:
                set_link_candidate(link, hazard, "现有关联条款不足以作为该具体隐患的直接依据，待补充直接依据后复核。")
            candidate += 1
            continue

        fix = GENERAL_FIXES[hid]
        target_clause = fix["clauseId"]
        evidence_refs = clause_evidence(target_clause)
        for field in ("title", "description", "measures", "places", "keywords"):
            hazard[field] = fix[field]
        hazard["lifecycle"] = "active"
        hazard["mode"] = "direct"
        hazard["note"] = ""
        write_json(path, hazard)

        for link in current_links:
            if link.get("clauseId") != target_clause:
                set_link_candidate(link, hazard, "原关联条款不能直接支撑复核后的隐患表述，已退出正式发布链。")

        link = active_link_for(hazard, target_clause, fix["applicability"])
        write_json(LINKS / f"{link['id']}.json", link)
        links[link["id"]] = link

        hazard_reason = f"隐患表述已收窄至条款 {target_clause} 直接规定的法定义务，并由该条款官方证据支撑。"
        write_json(
            HAZARD_REVIEWS / f"{hid}.json",
            make_hazard_review(hazard, "verified", evidence_refs, hazard_reason),
        )
        link_reason = f"该隐患事实与条款 {target_clause} 的法定义务直接对应，可作为直接依据。"
        write_json(
            LINK_REVIEWS / f"{link['id']}.json",
            make_link_review(link, hazard, "verified", evidence_refs, link_reason),
        )
        retained += 1

    return retained, candidate


def repair_major(links: dict[str, dict]) -> int:
    major_paths = sorted(HAZARDS.glob("H_CF_MAJOR_*.json"))
    if len(major_paths) != 8:
        raise RuntimeError(f"expected 8 Changfeng major hazards, found {len(major_paths)}")

    repaired = 0
    for path in major_paths:
        hazard = load_json(path)
        hid = hazard["id"]
        if hid == "H_CF_MAJOR_05":
            hazard.update(MAJOR_05_FIX)
        hazard["lifecycle"] = "active"
        hazard["mode"] = "direct"
        hazard["note"] = ""
        write_json(path, hazard)

        current_links = links_for_hazard(links, hid)
        active = [link for link in current_links if (link.get("lifecycle") or "active") == "active"]
        if not active:
            raise RuntimeError(f"major hazard has no active link: {hid}")

        hazard_evidence = []
        for link in active:
            refs = clause_evidence(link["clauseId"])
            for ref in refs:
                if ref not in hazard_evidence:
                    hazard_evidence.append(ref)
            link_reason = f"该重大事故隐患判定条件与条款 {link['clauseId']} 直接对应。"
            write_json(
                LINK_REVIEWS / f"{link['id']}.json",
                make_link_review(link, hazard, "verified", refs, link_reason),
            )

        hazard_reason = "隐患表述已与现行《工贸企业重大事故隐患判定标准》的对应判定条件核对一致。"
        write_json(
            HAZARD_REVIEWS / f"{hid}.json",
            make_hazard_review(hazard, "verified", hazard_evidence, hazard_reason),
        )
        repaired += 1
    return repaired


def main() -> int:
    links = all_links()
    retained, candidate = repair_general(links)
    major = repair_major(links)
    print(f"Changfeng re-audit complete: active major={major}, active general={retained}, candidate general={candidate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
