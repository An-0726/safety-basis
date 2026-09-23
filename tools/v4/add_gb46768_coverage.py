#!/usr/bin/env python3
"""Curated, repeatable GB 46768-2025 hazard coverage batch.

Every clause below already has a verified text review and an authoritative
evidence card. This batch deliberately uses complete, actionable clauses.
"""
from __future__ import annotations

import json
from pathlib import Path

from canonical import content_hash

ROOT = Path(__file__).resolve().parents[2]
KNOW = ROOT / "knowledge"
EVIDENCE = "E_46768_GB46768"
DATE = "2026-09-23"
REVIEWER = "Codex Local Agent"
BASE_CONDITION = (
    "仅适用于现场符合有限空间定义且实际开展进入作业的生产经营单位；"
    "应结合空间、作业内容和危险因素核对，不适用于普通封闭场所。"
)

# (clause suffix, title, inspection description, corrective measure, extra condition)
NEW = [
    ("4_2_2", "多个有限空间集中布置场所未设置作业安全风险告知牌",
     "多个有限空间集中布置的场所，显著位置缺少有限空间作业安全风险告知牌。",
     "在该场所显著位置设置有限空间作业安全风险告知牌，并保持内容清晰、适用。",
     "仅在多个有限空间集中布置时适用。"),
    ("4_5_1", "有限空间作业安全防护和应急救援设备设施未配备或未建台账",
     "作业单位未按有限空间作业需要配备安全防护、应急救援设备设施，或未建立相应管理台账。",
     "按作业风险配备安全防护和应急救援设备设施，建立并维护设备设施管理台账。", ""),
    ("4_5_3", "有限空间作业安全防护和救援设备设施缺少维护校准等管理",
     "作业单位未安排人员负责有关设备设施的维护、检验、检定、校准、报废或更换，设备设施有效性缺少保障。",
     "明确设备设施管理人员，依设备要求实施维护、检验、检定、校准、报废和更换，核查完好有效状态。", ""),
    ("5_1_1", "有限空间作业前未分析危险因素或未制定防范措施",
     "作业前未针对有限空间环境和作业过程分析可能存在的危险因素，缺少对应防范措施。",
     "作业前识别环境及作业过程危险因素，制定与识别结果相对应的防范措施。", ""),
    ("5_2_1", "有限空间作业未填写审批单或未按要求留存",
     "有限空间作业未填写作业审批单，或审批单未归档保存。",
     "作业前填写并履行有限空间作业审批单，作业完成后归档保存。", ""),
    ("5_3", "有限空间作业前未进行安全交底并留存确认记录",
     "作业负责人或安全管理人员未向作业人交底作业内容、分工、危险因素、安全要求和应急措施，或未留存签字确认记录。",
     "作业前开展针对性安全交底，由交底人与被交底人签字确认并保存记录。", ""),
    ("5_5", "有限空间作业前未检查安全防护和救援设备设施",
     "作业前未检查安全防护、应急救援设备设施的齐备性、安全性及适用性，或发现问题后未处置。",
     "作业前逐项检查设备设施，发现问题及时维护、更换或增配，确认适用后再作业。", ""),
    ("5_6_1", "有限空间作业前未隔离危险物料能量或设备设施",
     "存在可能危及作业安全的物料、能量或设备设施时，未实施隔断、封堵、关闭、移除等隔离措施，或未上锁挂牌、安排专人看管。",
     "识别与空间相连的物料、能量及设备设施，实施有效隔离，并上锁挂牌或安排专人看管。",
     "仅在存在可能危及作业安全的物料、能量或设备设施时适用。"),
    ("5_8_2", "有限空间作业前气体检测未覆盖必要项目",
     "作业前未根据可能存在的危害气体针对性检测，或未至少检测氧气、可燃气、硫化氢和一氧化碳。",
     "依据危险因素选定检测项目，至少检测氧气、可燃气、硫化氢和一氧化碳，并记录结果。", ""),
    ("5_8_5", "有限空间气体检测人员未在空间外上风侧实施检测",
     "检测人员未在有限空间外上风侧使用泵吸式气体检测报警仪检测。",
     "由检测人员在空间外上风侧使用泵吸式气体检测报警仪实施检测，并核对仪器状态。", ""),
    ("5_8_7", "有限空间作业气体检测结果未如实记录签字并归档",
     "气体检测记录缺少位置、时间、气体种类、浓度等信息，或未经检测人员签字确认并归档。",
     "如实记录检测位置、时间、气体种类及浓度，由检测人员签字确认并归档。", ""),
    ("5_9_1", "有限空间初始气体检测结果不符合准入条件仍实施作业",
     "初始检测的氧含量、可燃性气体或有毒有害气体浓度未满足标准规定的全部条件，仍实施有限空间作业。",
     "按标准规定核对全部初始检测指标；未达到准入条件时停止进入，采取通风等措施后重新检测判断。", ""),
    ("5_10_1", "有限空间通风使用纯氧富氧空气或未送入清洁空气",
     "向有限空间送入的空气不清洁，或使用纯氧、富氧空气进行通风。",
     "向有限空间输送清洁空气，停止使用纯氧或富氧空气通风。", ""),
    ("5_12_2", "可能突发缺氧或有毒气体升高的有限空间作业防护不足",
     "初始气体检测合格，但作业过程中可能突发缺氧或有毒有害气体升高时，作业人员未按要求穿戴全身式安全带、系安全绳并配用适用呼吸防护用品。",
     "按风险配置全身式安全带、安全绳及标准列明的适用呼吸防护用品，确认穿戴和救援配套条件。",
     "仅在初始检测合格且作业中仍可能缺氧或有毒有害气体突然升高时适用。"),
    ("6_2_3", "有限空间作业中未实时监测气体或每15分钟记录瞬时值",
     "作业过程中未对作业人员活动区域实施实时气体监测，或未每15分钟记录一个瞬时值。",
     "对作业人员活动区域实时监测气体，每15分钟记录一个瞬时值并保存。", ""),
    ("7_1_1", "有限空间作业完成后未清点人员工具并确认关闭出入口",
     "作业完成后，作业负责人未确认人员全部安全出离、设备工具全部带离、出入口关闭及作业前隔离措施解除等事项。",
     "由作业负责人逐项验收确认人员、设备工具、出入口和隔离措施状态。", ""),
]

# Only exact existing hazard/standard clause matches; no broad clause stuffing.
EXISTING = [
    ("4_1_1", "H_48B66BAC_6_1"),
    ("4_2_1", "H_48B66BAC_11_1"),
    ("4_4_3", "H_48B66BAC_9_1"),
    ("4_4_3", "H_48B66BAC_9_2"),
    ("4_7_2", "H_48B66BAC_8_1"),
    ("6_3_1", "H_48B66BAC_15_1"),
    ("6_3_2", "H_48B66BAC_15_1"),
    ("6_2_8", "H_48B66BAC_15_3"),
]


def read(rel: str) -> dict:
    with (KNOW / rel).open(encoding="utf-8") as f:
        return json.load(f)


def write_new(rel: str, obj: dict) -> None:
    path = KNOW / rel
    if path.exists():
        if read(rel) != obj:
            raise RuntimeError(f"Refusing to overwrite {path}")
        return
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def add_link(clause_suffix: str, hazard: dict, *, existing: bool) -> None:
    clause_id = "C_46768_" + clause_suffix
    clause = read(f"clauses/{clause_id}.json")
    clause_review = read(f"reviews/clauses/{clause_id}.json")
    if clause_review.get("decision") != "verified" or clause_review.get("reviewedContentHash") != content_hash(clause):
        raise RuntimeError(f"Clause not currently verified: {clause_id}")
    link_id = f"K_46768_{clause_suffix}_{hazard['id']}"
    link = {
        "id": link_id, "hazardId": hazard["id"], "clauseId": clause_id,
        "role": "direct", "applicability": hazard["conditions"],
        "jurisdictionCode": "CN", "lifecycle": "active", "priority": 10,
        "reason": (
            "已核对既有正式隐患与该条具体义务一致；补充技术标准直接依据。"
            if existing else "依据已核验的标准条款逐项核对隐患对象、缺陷及适用前提。"
        ),
    }
    review = {
        "entityId": link_id, "entityType": "link", "reviewType": "applicability",
        "decision": "verified", "reviewedContentHash": content_hash(link),
        "checkedAt": DATE, "reviewer": REVIEWER,
        "evidenceRefs": [EVIDENCE],
        "contextHashes": {"clause": content_hash(clause), "hazard": content_hash(hazard)},
        "reason": link["reason"],
    }
    write_new(f"links/{link_id}.json", link)
    write_new(f"reviews/links/{link_id}.json", review)


def main() -> None:
    for suffix, title, description, measures, extra in NEW:
        hid = "H_46768_" + suffix
        conditions = BASE_CONDITION + (" " + extra if extra else "")
        hazard = {
            "id": hid, "title": title, "description": description,
            "category": "有限空间作业", "conditions": conditions,
            "measures": measures, "note": f"依据 GB 46768-2025 第{suffix.replace('_', '.')}条；是否构成现场隐患须核实实际状态。",
            "mode": "direct", "aliases": [], "keywords": ["有限空间", title],
            "places": ["有限空间作业现场"], "lifecycle": "active", "mergedInto": None,
        }
        review = {
            "entityId": hid, "entityType": "hazard", "reviewType": "definition",
            "decision": "verified", "reviewedContentHash": content_hash(hazard),
            "checkedAt": DATE, "reviewer": REVIEWER, "evidenceRefs": [EVIDENCE],
            "reason": f"核对 GB 46768-2025 第{suffix.replace('_', '.')}条的具体义务、适用前提和既有有限空间隐患；本项是可独立检查的缺口。",
        }
        write_new(f"hazards/{hid}.json", hazard)
        write_new(f"reviews/hazards/{hid}.json", review)
        add_link(suffix, hazard, existing=False)
    for suffix, hid in EXISTING:
        hazard = read(f"hazards/{hid}.json")
        if hazard["lifecycle"] != "active":
            raise RuntimeError(f"Existing hazard is not active: {hid}")
        add_link(suffix, hazard, existing=True)
    print(f"curated: {len(NEW)} new hazards; {len(NEW) + len(EXISTING)} new links")


if __name__ == "__main__":
    main()
