# -*- coding: utf-8 -*-
"""Promote the first reviewed GB/T 47236-2026 candidate batch.

Only candidates whose hazard wording directly mirrors a current, reviewed
clause are promoted.  The partially overlapping motion-part candidate remains
proposed until its warning-sign subject can be split or merged without losing
meaning.  This tool does not touch the private SQLite/library or release files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
KNOW = ROOT / "knowledge"
DOCS = ROOT / "docs"
sys.path.insert(0, str(ROOT / "tools" / "v4"))
from canonical import content_hash  # noqa: E402
from release_gate_core import evaluate_release_gate  # noqa: E402


AS_OF = "2026-09-18"
REVIEWER = "Codex PHASE11 GB/T 47236 review 20260918"
STANDARD_SCOPE = (
    "仅适用于GB/T 47236-2026范围内的低压铸造机、差压铸造机及其他金属型铸造设备；"
    "其他机械应按相应通用或专用标准判断。"
)
OFFICIAL_URL = "https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=0A7C3D2DABA433E1DAA4A495EFF1A047"
EVIDENCE_SHA256 = "204eeb5579a83d51a9b48d0c07cad0d6393501b006f321ed27c480f1faf076a1"


PROMOTE: dict[str, tuple[str, str]] = {
    "H_GBT47236_4_1_3": (
        "C_GBT47236_4_1_3",
        "第4.1.3条直接要求机器设计时进行风险评估并采取减小风险措施，与候选对象和缺陷完整对应。",
    ),
    "H_GBT47236_4_1_6": (
        "C_GBT47236_4_1_6",
        "第4.1.6条直接要求对设计不能避免的危险采取安全防护及补充保护措施。",
    ),
    "H_GBT47236_4_1_7": (
        "C_GBT47236_4_1_7",
        "第4.1.7条直接要求以使用信息通知或警告操作者无法消除的剩余风险。",
    ),
    "H_GBT47236_4_2_1_1": (
        "C_GBT47236_4_2_1_1",
        "第4.2.1.1条直接规定机器及零部件强度和刚度应满足储运、安装和使用要求。",
    ),
    "H_GBT47236_4_2_1_2": (
        "C_GBT47236_4_2_1_2",
        "第4.2.1.2条逐项覆盖尖角锐边、薄板件棱边处理和管端开口包覆。",
    ),
    "H_GBT47236_4_2_1_3": (
        "C_GBT47236_4_2_1_3",
        "第4.2.1.3条直接要求螺栓、螺钉、螺母等紧固件采取防松措施。",
    ),
    "H_GBT47236_4_2_1_4": (
        "C_GBT47236_4_2_1_4",
        "第4.2.1.4条直接要求机器保持稳定，避免翻倒、掉落或自行移动。",
    ),
    "H_GBT47236_4_2_1_7": (
        "C_GBT47236_4_2_1_7",
        "第4.2.1.7条直接要求正确设计起吊装置位置，防止偏重失稳。",
    ),
    "H_GBT47236_4_2_1_8": (
        "C_GBT47236_4_2_1_8",
        "第4.2.1.8条直接要求设置可承受预期冲击负荷的防护隔离，防止材料或碎块飞出。",
    ),
    "H_GBT47236_4_2_2_4": (
        "C_GBT47236_4_2_2_4",
        "第4.2.2.4条直接规定活动罩盖的警告标志或罩盖联锁装置。",
    ),
    "H_GBT47236_4_2_2_6": (
        "C_GBT47236_4_2_2_6",
        "第4.2.2.6条直接规定运动部件减速、防冲击碰撞和机械极限限位装置。",
    ),
    "H_GBT47236_4_2_3_3_2": (
        "C_GBT47236_4_2_3_3_2",
        "第4.2.3.3.2条直接要求电敏保护设备覆盖人员进出区域。",
    ),
    "H_GBT47236_4_2_3_4_2": (
        "C_GBT47236_4_2_3_4_2",
        "第4.2.3.4.2条直接要求急停装置位于易接近且无操作危险的位置。",
    ),
    "H_GBT47236_4_2_5_4": (
        "C_GBT47236_4_2_5_4",
        "第4.2.5.4条直接规定不同工作模式采用钥匙锁定选择开关或可卸手柄转换开关。",
    ),
    "H_GBT47236_4_2_5_7": (
        "C_GBT47236_4_2_5_7",
        "第4.2.5.7条直接要求防止动力供应失效危险和控制回路切断后的意外重启。",
    ),
    "H_GBT47236_4_2_6_4_1": (
        "C_GBT47236_4_2_6_4",
        "第4.2.6.4条直接要求高压气动系统、液压系统安装自动泄压装置。",
    ),
}

DEFERRED = "H_GBT47236_4_2_2_3"
CANONICAL_OVERLAP = "H_F8BD176AF46643EA9E3CC56A6F"
CANONICAL_CLAUSE = "C_GBT47236_4_2_2_3"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def load_dir(relative: str) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for path in (KNOW / relative).glob("*.json"):
        value = read_json(path)
        result[value.get("id") or value.get("entityId") or path.stem] = value
    return result


def make_hazard_review(hazard: dict, reason: str) -> dict:
    return {
        "checkedAt": AS_OF,
        "decision": "verified",
        "entityId": hazard["id"],
        "entityType": "hazard",
        "evidenceRefs": ["E_GBT47236_2026"],
        "reason": (
            "已按GB/T 47236-2026官方归档全文复核隐患对象、反向表述和标准适用范围；"
            f"{reason}"
        ),
        "reviewType": "content",
        "reviewedContentHash": content_hash(hazard),
        "reviewer": REVIEWER,
    }


def make_link(hazard: dict, clause: dict, reason: str) -> tuple[dict, dict]:
    link_id = "K_PHASE11_GBT47236_" + hashlib.sha1(
        (hazard["id"] + "|" + clause["id"]).encode("utf-8")
    ).hexdigest()[:20].upper()
    link = {
        "id": link_id,
        "hazardId": hazard["id"],
        "clauseId": clause["id"],
        "role": "direct",
        "legacyRole": "直接依据",
        "applicability": STANDARD_SCOPE,
        "jurisdictionCode": "CN",
        "lifecycle": "active",
        "priority": 10,
        "requirementId": "",
        "reason": reason,
    }
    review = {
        "checkedAt": AS_OF,
        "contextHashes": {
            "clause": content_hash(clause),
            "hazard": content_hash(hazard),
        },
        "decision": "verified",
        "entityId": link_id,
        "entityType": "link",
        "evidenceRefs": ["E_GBT47236_2026"],
        "reason": reason + "适用范围已限定为该标准覆盖的铸造设备。",
        "reviewType": "applicability",
        "reviewedContentHash": content_hash(link),
        "reviewer": REVIEWER,
    }
    return link, review


def validate_baseline(
    hazards: dict[str, dict],
    clauses: dict[str, dict],
    links: dict[str, dict],
    reviews: dict[str, dict],
) -> None:
    lifecycle = Counter(h.get("lifecycle") for h in hazards.values())
    if lifecycle != Counter({"active": 1442, "proposed": 487, "superseded": 86}):
        raise RuntimeError(f"lifecycle baseline drift: {dict(lifecycle)}")
    if any(hazards[hid].get("lifecycle") != "proposed" for hid in PROMOTE):
        raise RuntimeError("promotion allow-list contains a non-proposed hazard")
    if hazards[DEFERRED].get("lifecycle") != "proposed":
        raise RuntimeError(f"deferred overlap is no longer proposed: {DEFERRED}")

    version = read_json(KNOW / "law-versions" / "LV_STD_GBT47236_2026.json")
    evidence = read_json(KNOW / "evidence" / "E_GBT47236_2026.json")
    if version.get("validityStatus") != "active" or version.get("effectiveDate") != "2026-09-01":
        raise RuntimeError("GB/T 47236-2026 version is not current for this batch")
    if version.get("sourceUrl") != OFFICIAL_URL or evidence.get("url") != OFFICIAL_URL:
        raise RuntimeError("GB/T 47236-2026 official source URL drift")
    if evidence.get("snapshotSha256") != EVIDENCE_SHA256 or evidence.get("tier") != "authoritative-public":
        raise RuntimeError("GB/T 47236-2026 authoritative evidence drift")

    active_by_clause: dict[str, list[str]] = {}
    for link in links.values():
        linked_hazard = hazards.get(link.get("hazardId"), {})
        if link.get("lifecycle") == "active" and linked_hazard.get("lifecycle") == "active" and not linked_hazard.get("mergedInto"):
            active_by_clause.setdefault(link.get("clauseId"), []).append(link.get("hazardId"))

    for hazard_id, (clause_id, _reason) in PROMOTE.items():
        clause = clauses.get(clause_id)
        review = reviews.get(clause_id, {})
        if not clause or clause.get("lifecycle") != "active":
            raise RuntimeError(f"missing active clause: {clause_id}")
        if review.get("decision") != "verified" or review.get("reviewedContentHash") != content_hash(clause):
            raise RuntimeError(f"clause review is not current: {clause_id}")
        if review.get("evidenceRefs") != ["E_GBT47236_2026"]:
            raise RuntimeError(f"unexpected clause evidence: {clause_id}")
        if active_by_clause.get(clause_id):
            raise RuntimeError(f"clause already supports active hazard(s): {clause_id} {active_by_clause[clause_id]}")

    if CANONICAL_OVERLAP not in active_by_clause.get(CANONICAL_CLAUSE, []):
        raise RuntimeError("expected partial-overlap canonical link is missing")


def update_current_reviews() -> None:
    for entity_type, relative, entity_id in (
        ("law", "laws", "LF_STD_GBT47236"),
        ("law-version", "law-versions", "LV_STD_GBT47236_2026"),
    ):
        entity = read_json(KNOW / relative / f"{entity_id}.json")
        review_path = KNOW / "reviews" / relative / f"{entity_id}.json"
        review = read_json(review_path)
        review["checkedAt"] = AS_OF
        review["reviewedContentHash"] = content_hash(entity)
        review["reviewer"] = REVIEWER
        if entity_type == "law-version":
            review["reason"] = (
                "国家标准全文公开系统官方页面于2026-09-18复核：GB/T 47236-2026于2026-02-27发布、"
                "2026-09-01实施，当前状态为现行。"
            )
        else:
            review["reason"] = (
                "国家标准全文公开系统官方页面于2026-09-18复核标准名称、编号、发布机关和标准性质。"
            )
        write_json(review_path, review)


def update_manifest() -> None:
    path = KNOW / "manifest.json"
    manifest = read_json(path)
    batch_id = "phase11-promote-gbt47236-direct-batch-20260918"
    batches = [item for item in manifest.get("batches", []) if item.get("id") != batch_id]
    batches.append(
        {
            "id": batch_id,
            "hazardsPromoted": len(PROMOTE),
            "linksAdded": len(PROMOTE),
            "candidatesReviewed": len(PROMOTE) + 1,
            "candidatesDeferred": 1,
            "selection": (
                "Promote only GB/T 47236-2026 candidates whose wording directly mirrors a current reviewed clause; "
                "defer the partially overlapping motion-part candidate for split/merge review."
            ),
        }
    )
    manifest["batches"] = batches
    counts = manifest.setdefault("counts", {})
    for key, relative in (
        ("laws", "laws"),
        ("lawVersions", "law-versions"),
        ("clauses", "clauses"),
        ("hazards", "hazards"),
        ("links", "links"),
        ("evidence", "evidence"),
    ):
        counts[key] = len(list((KNOW / relative).glob("*.json")))
    manifest["asOf"] = AS_OF
    write_json(path, manifest)


def write_reports(promoted: list[dict], deferred_title: str) -> None:
    rows = [
        {
            "recordType": "metadata",
            "schemaVersion": 1,
            "asOf": AS_OF,
            "baselineProposed": 487,
            "reviewed": len(PROMOTE) + 1,
            "promoted": len(PROMOTE),
            "retainedProposed": 1,
            "proposedAfter": 471,
            "privateSqliteModified": False,
        }
    ]
    rows.extend(
        {
            "hazardId": item["hazardId"],
            "title": item["title"],
            "outcome": "promoted_active",
            "lifecycleAfter": "active",
            "clauseId": item["clauseId"],
            "linkId": item["linkId"],
            "reasonCode": "verified_direct_scope_bounded",
            "reason": item["reason"],
        }
        for item in promoted
    )
    rows.append(
        {
            "hazardId": DEFERRED,
            "title": deferred_title,
            "outcome": "retained_proposed",
            "lifecycleAfter": "proposed",
            "clauseId": CANONICAL_CLAUSE,
            "reasonCode": "partial_overlap_split_or_merge_required",
            "reason": (
                f"候选同时包含运动部件防护和警告标志两个缺陷；现有active隐患{CANONICAL_OVERLAP}只覆盖防护装置。"
                "两者并非完整语义重复，需先拆分警告标志对象或扩充canonical后再决定合并，不能直接转正或归并。"
            ),
            "nextRequiredEvidence": "形成无重复的稳定对象处置方案，并重新审核canonical内容哈希及关联上下文。",
        }
    )
    write_jsonl(DOCS / "phase11-gbt47236-disposition.jsonl", rows)

    lines = [
        "# PHASE 11 GB/T 47236 候选核验批次",
        "",
        f"> 基准日：{AS_OF}。本批仅处理逐字条款、对象和适用范围均已闭环的候选。",
        "",
        "## 结论",
        "",
        "- 复核 17 条候选：16 条转为 `active`，1 条继续 `proposed`。",
        "- 转正项全部限定于 GB/T 47236-2026 覆盖的低压铸造机、差压铸造机及其他金属型铸造设备。",
        "- 标准官方状态已于 2026-09-18 复核：2026-02-27 发布、2026-09-01 实施、当前现行。",
        "- 未修改私有 SQLite、archive、稳定 ID 或既有官方原文快照。",
        "- 本批后 knowledge lifecycle 为 1,458 active / 471 proposed / 86 superseded。",
        "",
        "## 转正清单",
        "",
        "| hazardId | clauseId | 核验结论 |",
        "| --- | --- | --- |",
    ]
    for item in promoted:
        lines.append(f"| `{item['hazardId']}` | `{item['clauseId']}` | {item['reason']} |")
    lines += [
        "",
        "## 保留候选",
        "",
        f"- `{DEFERRED}`：同时描述防护装置和警告标志缺失，与 `{CANONICAL_OVERLAP}` 仅部分重叠；"
        "需先拆分或扩充 canonical 后再合并，当前不强行转正。",
        "",
        "机器明细见 `docs/phase11-gbt47236-disposition.jsonl`。",
        "",
    ]
    (DOCS / "PHASE11_GBT47236_BATCH.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    hazards = load_dir("hazards")
    clauses = load_dir("clauses")
    links = load_dir("links")
    clause_reviews = load_dir("reviews/clauses")
    validate_baseline(hazards, clauses, links, clause_reviews)

    summary = {
        "mode": "apply" if args.apply else "dry-run",
        "baselineProposed": 487,
        "reviewed": len(PROMOTE) + 1,
        "promotable": len(PROMOTE),
        "deferred": [DEFERRED],
        "proposedAfter": 487 - len(PROMOTE),
    }
    if not args.apply:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    promoted: list[dict] = []
    for hazard_id, (clause_id, reason) in sorted(PROMOTE.items()):
        hazard = dict(hazards[hazard_id])
        clause = clauses[clause_id]
        hazard["conditions"] = STANDARD_SCOPE
        hazard["lifecycle"] = "active"
        hazard["mode"] = "direct"
        hazard.pop("proposalStatus", None)
        hazard.pop("sourceRow", None)
        hazard.pop("revisionState", None)
        marker = (
            "【PHASE 11 2026-09-18】已复核GB/T 47236-2026现行状态、官方逐字条款、"
            "隐患对象和设备适用范围，建立当前direct关联。"
        )
        note = str(hazard.get("note") or "").rstrip()
        if marker not in note:
            hazard["note"] = (note + "\n" + marker).strip()
        write_json(KNOW / "hazards" / f"{hazard_id}.json", hazard)
        write_json(KNOW / "reviews" / "hazards" / f"{hazard_id}.json", make_hazard_review(hazard, reason))
        link, link_review = make_link(hazard, clause, reason)
        write_json(KNOW / "links" / f"{link['id']}.json", link)
        write_json(KNOW / "reviews" / "links" / f"{link['id']}.json", link_review)
        promoted.append(
            {
                "hazardId": hazard_id,
                "title": hazard.get("title"),
                "clauseId": clause_id,
                "linkId": link["id"],
                "reason": reason,
            }
        )

    update_current_reviews()
    update_manifest()
    write_reports(promoted, hazards[DEFERRED].get("title", ""))

    gate = evaluate_release_gate(KNOW)
    missing = sorted(set(PROMOTE) - set(gate.eligible_hazards))
    if missing:
        raise RuntimeError(f"promoted hazards failed release Gate: {missing}")
    final_hazards = load_dir("hazards")
    final_counts = Counter(h.get("lifecycle") for h in final_hazards.values())
    expected = Counter({"active": 1458, "proposed": 471, "superseded": 86})
    if final_counts != expected:
        raise RuntimeError(f"unexpected final lifecycle counts: {dict(final_counts)}")
    summary["allPromotedGateEligible"] = True
    summary["finalLifecycle"] = dict(final_counts)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
