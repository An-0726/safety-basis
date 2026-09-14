# -*- coding: utf-8 -*-
"""Apply the bounded PHASE 5 lifecycle corrections found by reconciliation."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "v4"))
from canonical import content_hash  # noqa: E402


AS_OF = "2026-09-14"
REVIEWER = "Codex PHASE 5 reconciliation 20260914"

MERGED_TARGET_IDS = {
    "H_128CF6B2AEFB46EA98D63BE037",
    "H_15577_4_7_1",
    "H_15577_6_3_2_1",
    "H_3B764981E731EA8D2F1B2B0C59_1",
    "H_6F52BBD3B8764A2EB1BD84D811",
    "H_998C5607F7EAB6589B9DD35598_2",
    "H_A6FFD804B89A850BBF832DC4_1",
    "H_GB12801_5_4_6_1",
}

NON_TARGET_PROPOSED_IDS = {
    "H_02FEFD347E114E1E979C9589AF",
    "H_0647B65088564B789D64080EF1",
    "H_1F19FA1B951D46C1971E9B59B4",
    "H_23D109AF79FF0519BCD1837EC6_1",
    "H_3A5DEC6C74244A949CE3BC9A42",
    "H_5B89D7164D2C4B6E983663B009",
    "H_6E7E9CD077AD4918962EBA6EAE",
}


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def append_once(text: str, note: str) -> str:
    text = str(text or "").strip()
    return text if note in text else "\n\n".join(part for part in (text, note) if part)


def update_review(hazard_id: str, hazard: dict, decision: str | None, reason: str, apply: bool) -> None:
    path = ROOT / "knowledge" / "reviews" / "hazards" / f"{hazard_id}.json"
    if path.exists():
        review = read(path)
        if decision:
            review["decision"] = decision
        review["reason"] = append_once(review.get("reason", ""), reason)
    else:
        if decision != "superseded":
            raise ValueError(f"missing hazard review for non-superseded correction: {hazard_id}")
        review = {
            "checkedAt": AS_OF,
            "decision": "superseded",
            "entityId": hazard_id,
            "entityType": "hazard",
            "evidenceRefs": [],
            "reason": reason,
            "reviewType": "content",
            "reviewer": REVIEWER,
        }
    review["checkedAt"] = AS_OF
    review["reviewedContentHash"] = content_hash(hazard)
    review["phase5ReconciledAt"] = AS_OF
    review["phase5ReconciledBy"] = REVIEWER
    if apply:
        write(path, review)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    changed: list[dict] = []
    updated_hazards: dict[str, dict] = {}

    for hazard_id in sorted(MERGED_TARGET_IDS):
        path = ROOT / "knowledge" / "hazards" / f"{hazard_id}.json"
        hazard = read(path)
        if hazard.get("id") != hazard_id or not hazard.get("mergedInto") or hazard.get("lifecycle") not in {"active", "superseded"}:
            raise ValueError(f"expected merged target entity: {hazard_id}")
        before = content_hash(hazard)
        hazard["lifecycle"] = "superseded"
        note = (
            f"【PHASE 5 对账 {AS_OF}】该工作簿目标 ID 已合并至 {hazard['mergedInto']}；"
            "保留稳定 ID 供追溯，不再作为独立当前实体。"
        )
        hazard["note"] = append_once(hazard.get("note", ""), note)
        reason = f"PHASE 5 全量对账确认该实体已通过 mergedInto 指向 {hazard['mergedInto']}，生命周期同步为 superseded。"
        update_review(hazard_id, hazard, "superseded", reason, args.apply)
        if args.apply:
            write(path, hazard)
        updated_hazards[hazard_id] = hazard
        changed.append({"hazardId": hazard_id, "from": before, "to": content_hash(hazard), "lifecycle": "superseded"})

    for hazard_id in sorted(NON_TARGET_PROPOSED_IDS):
        path = ROOT / "knowledge" / "hazards" / f"{hazard_id}.json"
        hazard = read(path)
        if hazard.get("id") != hazard_id or hazard.get("mergedInto") or hazard.get("lifecycle") not in {"active", "proposed"}:
            raise ValueError(f"expected active non-target entity: {hazard_id}")
        before = content_hash(hazard)
        hazard["lifecycle"] = "proposed"
        hazard["mode"] = "candidate"
        hazard["proposalStatus"] = "knowledge_extra_non_target_pending_scope_review"
        note = (
            f"【PHASE 5 对账 {AS_OF}】该实体不在 1,929 目标工作簿内，且当前缺少完整有效的正式 Gate；"
            "降为 proposed 保留，待范围、表述或依据链复核，不删除稳定 ID 和既有证据。"
        )
        hazard["note"] = append_once(hazard.get("note", ""), note)
        reason = "PHASE 5 全量对账：目标外实体缺少完整当前 Gate，保留原审阅结论并将 lifecycle 调整为 proposed。"
        update_review(hazard_id, hazard, None, reason, args.apply)
        if args.apply:
            write(path, hazard)
        updated_hazards[hazard_id] = hazard
        changed.append({"hazardId": hazard_id, "from": before, "to": content_hash(hazard), "lifecycle": "proposed"})

    link_reviews_by_entity: dict[str, tuple[Path, dict]] = {}
    for review_path in (ROOT / "knowledge" / "reviews" / "links").glob("*.json"):
        review = read(review_path)
        link_reviews_by_entity[str(review.get("entityId") or review_path.stem)] = (review_path, review)
    link_review_changes: list[dict] = []
    for link_path in sorted((ROOT / "knowledge" / "links").glob("*.json")):
        link = read(link_path)
        hazard_id = link.get("hazardId")
        if hazard_id not in NON_TARGET_PROPOSED_IDS:
            continue
        if link.get("id") not in link_reviews_by_entity:
            raise ValueError(f"missing link review: {link.get('id')}")
        review_path, review = link_reviews_by_entity[link["id"]]
        before_decision = review.get("decision")
        review["decision"] = "rejected"
        review["reason"] = append_once(
            review.get("reason", ""),
            "PHASE 5 全量对账：关联所属 hazard 已降为 proposed；保留关联与证据，但关联审阅退回，待范围、表述和完整依据链复核。",
        )
        review.setdefault("contextHashes", {})["hazard"] = content_hash(updated_hazards[hazard_id])
        review["reviewedContentHash"] = content_hash(link)
        review["checkedAt"] = AS_OF
        review["phase5ReconciledAt"] = AS_OF
        review["phase5ReconciledBy"] = REVIEWER
        if args.apply:
            write(review_path, review)
        link_review_changes.append(
            {"linkId": link["id"], "hazardId": hazard_id, "from": before_decision, "to": "rejected"}
        )

    print(
        json.dumps(
            {
                "mode": "apply" if args.apply else "dry-run",
                "changed": changed,
                "linkReviewChanges": link_review_changes,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
