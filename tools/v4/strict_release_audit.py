# -*- coding: utf-8 -*-
"""Strict V4 release audit（只读，不改动 knowledge / release 文件）。

本脚本只做“分类与汇报”，所有判定逻辑都来自共享核心 release_gate_core。
它把全量对象拆成三类（对齐 docs/GATE_V4.md §9/§13/§15）：

- releaseBlockers：真正影响“当前发布投影”的硬 blocker。
  例：已 verified 的 qualifying link 实际指向 repealed/upcoming/unknown 的
  LawVersion、review hash 漂移、context 漂移、管辖冲突、外键断裂、
  active hazard 内容硬门禁失败。
- inventoryWarnings：库存/数据质量软问题（backlog），不杀整个发布。
  例：active hazard 还没有任何合格 qualifying link（待补依据）、pending link、
  supporting-only link、可选 evidence 缺失。
- excludedEntities：历史/非发布实体，本就不该进当前发布投影。
  例：superseded / mergedInto hazard、superseded law、repealed/upcoming/unknown
  LawVersion、非 active clause、review=rejected 的 link。

strictVerdict 只由 releaseBlockers 是否非空决定：>0 -> BLOCK，否则 PASS。
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from release_gate_core import (  # noqa: E402
    evaluate_release_gate,
    QUALIFYING_ROLES,
)


def main():
    r = evaluate_release_gate()

    release_blockers = []
    inventory_warnings = []
    excluded_entities = []

    # ---- Law / LawVersion / Clause 结构失败：只有被合格 link 引用才算 blocker ----
    referenced_lvs = set()
    referenced_clauses = set()
    referenced_laws = set()
    for kid in r.eligible_links:
        cv = r.clauses.get(r.links[kid]["clauseId"])
        if cv:
            referenced_clauses.add(cv["lawVersionId"])
            # 反查 lawId
    for vid, v in r.law_versions.items():
        pass
    # lawId 反查
    lv_law = {}
    # 直接用原始 entity 关系：core 没暴露，这里从 law_versions 拿不到 lawId，
    # 但结构 blocker 我们用“该 lv 是否被任一 clause 引用且该 clause 被合格 link 引用”
    for kid in r.eligible_links:
        cid = r.links[kid]["clauseId"]
        vid = r.clauses.get(cid, {}).get("lawVersionId")
        referenced_lvs.add(vid)

    for lid, v in r.laws.items():
        if not v["ok"]:
            release_blockers.append({"entityType": "law", "id": lid, "reasons": v["reasons"]})
    for vid, v in r.law_versions.items():
        if not v["ok"]:
            if vid in referenced_lvs:
                release_blockers.append({"entityType": "lawVersion", "id": vid,
                                         "reasons": v["reasons"], "note": "referenced by eligible link"})
            else:
                excluded_entities.append({"entityType": "lawVersion", "id": vid,
                                          "reason": "structurally_invalid", "validityStatus": v["validityStatus"]})
        elif v["validityStatus"] != "active" or not v["supports_current"]:
            # 非 active 效力 = 历史/即将生效，进目录但不支撑当前 hazard
            excluded_entities.append({"entityType": "lawVersion", "id": vid,
                                      "reason": "not_active_support:" + v["validityStatus"],
                                      "validityStatus": v["validityStatus"]})
    for cid, v in r.clauses.items():
        if not v["ok"]:
            release_blockers.append({"entityType": "clause", "id": cid, "reasons": v["reasons"]})

    # ---- Link：已签署(verified)却没过 gate = 发布路径硬伤；其余按 review 状态分流 ----
    for kid, v in r.links.items():
        if v["decision"] == "verified" and not v["ok"]:
            release_blockers.append({"entityType": "link", "id": kid,
                                     "hazardId": v["hazardId"], "role": v["role"],
                                     "reasons": v["reasons"]})
        elif v["decision"] == "rejected":
            excluded_entities.append({"entityType": "link", "id": kid,
                                      "hazardId": v["hazardId"], "reason": "review_rejected"})
        elif v["decision"] == "pending":
            inventory_warnings.append({"type": "pending_link", "id": kid,
                                       "hazardId": v["hazardId"], "reason": "link review pending"})
        elif v["decision"] == "superseded":
            # 目标 hazard 已合并或非 active：关联保留用于历史追溯，不进入发布投影
            excluded_entities.append({"entityType": "link", "id": kid,
                                      "hazardId": v["hazardId"],
                                      "reason": "review_superseded:hazard_not_publishable"})
        elif v["ok"] and v["role"] == "supporting":
            inventory_warnings.append({"type": "supporting_link", "id": kid,
                                       "hazardId": v["hazardId"],
                                       "reason": "supporting link cannot alone qualify a hazard"})

    # ---- Hazard：内容硬失败且在发布路径(active 非 merged) = blocker；
    #      历史/合并 = excluded；active 但无合格依据 = inventory backlog ----
    for hid, v in r.hazards.items():
        if not v["active"] or v["merged"]:
            why = "superseded" if not v["active"] else "mergedInto"
            excluded_entities.append({"entityType": "hazard", "id": hid, "reason": why})
            continue
        if not v["content_ok"]:
            release_blockers.append({"entityType": "hazard", "id": hid,
                                     "reasons": v["reasons"]})
        elif hid not in r.eligible_hazards:
            inventory_warnings.append({
                "type": "active_hazard_without_qualifying_link", "id": hid,
                "reason": "active hazard has no eligible direct/fallback link yet (backlog, not published)",
            })

    eligible_hazard_ids = sorted(r.eligible_hazards)
    eligible_link_ids = sorted(r.eligible_links)

    summary = {
        "asOf": r.as_of,
        "entityCounts": r.counts,
        "releaseBlockers": release_blockers,
        "inventoryWarnings": inventory_warnings,
        "excludedEntities": excluded_entities,
        "eligibleHazards": len(eligible_hazard_ids),
        "eligibleHazardIds": eligible_hazard_ids,
        "eligibleLinks": len(eligible_link_ids),
        "eligibleLinkIds": eligible_link_ids,
        "strictVerdict": "BLOCK" if release_blockers else "PASS",
        "blockerCount": len(release_blockers),
        "warningCount": len(inventory_warnings),
        "excludedCount": len(excluded_entities),
    }

    print("=== STRICT_V4_RELEASE_AUDIT ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
