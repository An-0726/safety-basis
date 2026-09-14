# -*- coding: utf-8 -*-
"""Strict V4 release audit（只读，不改动 knowledge / release 文件）。

所有判定逻辑来自 release_gate_core。审计将对象分为：

- releaseBlockers：会污染当前正式发布路径的硬错误；
- inventoryWarnings：需要继续整改、回绑或补证据，但当前正式投影会自动排除；
- excludedEntities：历史、未来版本、已合并等本来就不应进入当前正式投影的实体。

strictVerdict 由 releaseBlockers 决定；存在 blocker 时脚本返回非零退出码，CI 必须失败。
"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from release_gate_core import evaluate_release_gate  # noqa: E402


def has_non_current_reason(reasons):
    return any(str(x).startswith((
        "BLOCK_VERSION_NOT_EFFECTIVE:",
        "BLOCK_VERSION_EXPIRED:",
        "EXCLUDED_CLAUSE_NOT_CURRENT:",
    )) for x in (reasons or []))


def main():
    r = evaluate_release_gate()

    release_blockers = []
    inventory_warnings = []
    excluded_entities = []

    eligible_clause_ids = {r.links[kid]["clauseId"] for kid in r.eligible_links}
    referenced_lvs = {r.clauses[cid]["lawVersionId"] for cid in eligible_clause_ids
                      if cid in r.clauses}

    # ---- Law / LawVersion ----
    # Law 身份结构错误只有真正进入当前正式链时才应阻断。当前 core 不暴露
    # lawVersion->lawId 的投影关系，因此未被当前版本链使用的 law 结构问题作为库存告警。
    for lid, value in r.laws.items():
        if not value["ok"]:
            inventory_warnings.append({
                "type": "law_identity_not_publishable",
                "id": lid,
                "reasons": value["reasons"],
            })

    for vid, value in r.law_versions.items():
        if vid in referenced_lvs and not value["ok"]:
            release_blockers.append({
                "entityType": "lawVersion", "id": vid,
                "reasons": value["reasons"], "note": "referenced by current eligible link",
            })
        elif value["validityStatus"] != "active" or not value["supports_current"]:
            excluded_entities.append({
                "entityType": "lawVersion", "id": vid,
                "reason": "not_current_support:" + value["validityStatus"],
                "validityStatus": value["validityStatus"],
            })
        elif not value["ok"]:
            inventory_warnings.append({
                "type": "law_version_not_publishable",
                "id": vid,
                "reasons": value["reasons"],
            })

    # ---- Clause ----
    for cid, value in r.clauses.items():
        if value["ok"]:
            continue
        if cid in eligible_clause_ids:
            release_blockers.append({
                "entityType": "clause", "id": cid, "reasons": value["reasons"],
            })
        elif has_non_current_reason(value["reasons"]):
            excluded_entities.append({
                "entityType": "clause", "id": cid,
                "reason": "clause_not_current",
                "reasons": value["reasons"],
            })
        else:
            inventory_warnings.append({
                "type": "clause_not_publishable",
                "id": cid,
                "reasons": value["reasons"],
            })

    # ---- Link ----
    # 已 verified 但指向未来/历史版本的关联不能进入正式站，但不应阻断其它
    # 完整链发布；它作为明确的待回绑事项进入 inventoryWarnings。
    for kid, value in r.links.items():
        if value["decision"] == "verified" and not value["ok"]:
            clause_reasons = r.clauses.get(value["clauseId"], {}).get("reasons", [])
            if has_non_current_reason(clause_reasons):
                inventory_warnings.append({
                    "type": "verified_link_non_current_basis",
                    "id": kid,
                    "hazardId": value["hazardId"],
                    "role": value["role"],
                    "reason": "verified link points to a version not effective for current asOf",
                    "clauseReasons": clause_reasons,
                })
            else:
                release_blockers.append({
                    "entityType": "link", "id": kid,
                    "hazardId": value["hazardId"], "role": value["role"],
                    "reasons": value["reasons"],
                })
        elif value["decision"] == "rejected":
            excluded_entities.append({
                "entityType": "link", "id": kid,
                "hazardId": value["hazardId"], "reason": "review_rejected",
            })
        elif value["decision"] == "pending":
            inventory_warnings.append({
                "type": "pending_link", "id": kid,
                "hazardId": value["hazardId"], "reason": "link review pending",
            })
        elif value["decision"] == "superseded":
            excluded_entities.append({
                "entityType": "link", "id": kid,
                "hazardId": value["hazardId"],
                "reason": "review_superseded:hazard_not_publishable",
            })
        elif value["ok"] and value["role"] == "supporting":
            inventory_warnings.append({
                "type": "supporting_link", "id": kid,
                "hazardId": value["hazardId"],
                "reason": "supporting link cannot alone qualify a hazard",
            })

    # ---- Hazard ----
    review_state_only = re.compile(r"^BLOCK_REVIEW_NOT_VERIFIED:(rejected|pending)$")
    for hid, value in r.hazards.items():
        if not value["active"] or value["merged"]:
            why = "superseded" if not value["active"] else "mergedInto"
            excluded_entities.append({"entityType": "hazard", "id": hid, "reason": why})
            continue
        if not value["content_ok"]:
            if value["reasons"] and all(review_state_only.match(str(x)) for x in value["reasons"]):
                excluded_entities.append({
                    "entityType": "hazard", "id": hid,
                    "reason": "hazard_review_not_verified:" + value["reasons"][0],
                })
            else:
                release_blockers.append({
                    "entityType": "hazard", "id": hid, "reasons": value["reasons"],
                })
        elif hid not in r.eligible_hazards:
            inventory_warnings.append({
                "type": "active_hazard_without_current_qualifying_link",
                "id": hid,
                "reason": "active hazard has no current effective direct/fallback basis yet",
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
    return 1 if release_blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
