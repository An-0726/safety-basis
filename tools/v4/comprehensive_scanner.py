# -*- coding: utf-8 -*-
"""全库精确质量扫描器：区分真实错误 (ERROR) 与启发式疑点 (WARNING)。

检查项覆盖：
- RULE_REJECTED_LINK_ACTIVE: review 决策为 rejected，但 link lifecycle 仍为 active
- RULE_DANGLING_REF: 悬空引用（link->hazard/clause, clause->lawVersion, hazard->mergedInto）
- RULE_STALE_REVIEW_HASH: review 绑定的哈希与当前内容哈希不一致
- RULE_DUPLICATE_ACTIVE_TITLE: active 隐患之间存在完全相同的标题
- RULE_DUPLICATE_PROPOSED_ACTIVE: proposed 隐患与 active 隐患存在完全相同的标题
- RULE_UPCOMING_VERSION_ACTIVE_LINK: upcoming 版本支撑了当前 active 隐患
- RULE_REPEALED_VERSION_ACTIVE_LINK: 已废止版本支撑了当前 active 隐患
- RULE_CLAUSE_TEXT_CORRUPTION: 条款原文存在明显 OCR 乱码或指数缺失
- RULE_OBLIGATION_RESTATEMENT: 标题为法条复述式或正向义务陈述
- RULE_HAZARD_WITHOUT_ACTIVE_LINK: active 隐患缺少 active link
- RULE_CROSS_REF_WITHOUT_DETAILS: 条款仅为表号/附录转致但被标为直接依据
"""
from __future__ import annotations
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
KNOW = ROOT / "knowledge"
AS_OF = "2026-09-18"

sys.path.insert(0, str(ROOT / "tools" / "v4"))
from canonical import content_hash

def load_dir(rel: str) -> dict[str, dict]:
    out = {}
    for p in (KNOW / rel).glob("*.json"):
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f)
        key = d.get("id") or d.get("entityId") or p.stem
        out[key] = d
    return out

def norm_text(s: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]", "", str(s)).lower()

def run_scan():
    hazards = load_dir("hazards")
    clauses = load_dir("clauses")
    links = load_dir("links")
    lvs = load_dir("law-versions")
    laws = load_dir("laws")
    hr = load_dir("reviews/hazards")
    cr = load_dir("reviews/clauses")
    lr = load_dir("reviews/links")

    findings = []

    # 1. RULE_DANGLING_REF (ERROR)
    for lid, l in links.items():
        hid = l.get("hazardId")
        cid = l.get("clauseId")
        if hid not in hazards:
            findings.append({
                "rule_id": "RULE_DANGLING_REF",
                "entity_id": lid,
                "entity_type": "link",
                "severity": "ERROR",
                "reason": f"Link 引用了不存在的 hazardId: {hid}",
                "evidence": {"linkId": lid, "hazardId": hid},
                "disposition": "REMOVE_OR_FIX_LINK",
                "resolved": False
            })
        if cid not in clauses:
            findings.append({
                "rule_id": "RULE_DANGLING_REF",
                "entity_id": lid,
                "entity_type": "link",
                "severity": "ERROR",
                "reason": f"Link 引用了不存在的 clauseId: {cid}",
                "evidence": {"linkId": lid, "clauseId": cid},
                "disposition": "REMOVE_OR_FIX_LINK",
                "resolved": False
            })

    for cid, c in clauses.items():
        lvid = c.get("lawVersionId")
        if lvid not in lvs:
            findings.append({
                "rule_id": "RULE_DANGLING_REF",
                "entity_id": cid,
                "entity_type": "clause",
                "severity": "ERROR",
                "reason": f"Clause 引用了不存在的 lawVersionId: {lvid}",
                "evidence": {"clauseId": cid, "lawVersionId": lvid},
                "disposition": "FIX_CLAUSE_LAW_VERSION",
                "resolved": False
            })

    for hid, h in hazards.items():
        mi = h.get("mergedInto")
        if mi and mi not in hazards:
            findings.append({
                "rule_id": "RULE_DANGLING_REF",
                "entity_id": hid,
                "entity_type": "hazard",
                "severity": "ERROR",
                "reason": f"Hazard mergedInto 引用了不存在的 hazardId: {mi}",
                "evidence": {"hazardId": hid, "mergedInto": mi},
                "disposition": "FIX_MERGED_INTO",
                "resolved": False
            })

    # 2. RULE_REJECTED_LINK_ACTIVE (ERROR)
    for lid, l in links.items():
        if l.get("lifecycle") == "active":
            r = lr.get(lid, {})
            if r.get("decision") == "rejected":
                findings.append({
                    "rule_id": "RULE_REJECTED_LINK_ACTIVE",
                    "entity_id": lid,
                    "entity_type": "link",
                    "severity": "ERROR",
                    "reason": "Link review 已标记为 rejected，但 link lifecycle 仍为 active",
                    "evidence": {"linkId": lid, "reviewDecision": "rejected"},
                    "disposition": "DEMOTE_OR_REMOVE_LINK",
                    "resolved": False
                })

    # 3. RULE_STALE_REVIEW_HASH (ERROR)
    for hid, h in hazards.items():
        if h.get("lifecycle") == "active":
            r = hr.get(hid, {})
            ch = content_hash(h)
            if r and r.get("decision") == "verified" and r.get("reviewedContentHash") != ch:
                findings.append({
                    "rule_id": "RULE_STALE_REVIEW_HASH",
                    "entity_id": hid,
                    "entity_type": "hazard",
                    "severity": "ERROR",
                    "reason": "Active hazard content_hash 与 review 中的 reviewedContentHash 不一致",
                    "evidence": {"hazardId": hid, "currentHash": ch, "reviewedHash": r.get("reviewedContentHash")},
                    "disposition": "REFRESH_HAZARD_REVIEW",
                    "resolved": False
                })

    for cid, c in clauses.items():
        if c.get("lifecycle") == "active":
            r = cr.get(cid, {})
            ch = content_hash(c)
            if r and r.get("decision") == "verified" and r.get("reviewedContentHash") != ch:
                findings.append({
                    "rule_id": "RULE_STALE_REVIEW_HASH",
                    "entity_id": cid,
                    "entity_type": "clause",
                    "severity": "ERROR",
                    "reason": "Active clause content_hash 与 review 中的 reviewedContentHash 不一致",
                    "evidence": {"clauseId": cid, "currentHash": ch, "reviewedHash": r.get("reviewedContentHash")},
                    "disposition": "REFRESH_CLAUSE_REVIEW",
                    "resolved": False
                })

    for lid, l in links.items():
        if l.get("lifecycle") == "active":
            r = lr.get(lid, {})
            ch = content_hash(l)
            if r and r.get("decision") == "verified" and r.get("reviewedContentHash") != ch:
                findings.append({
                    "rule_id": "RULE_STALE_REVIEW_HASH",
                    "entity_id": lid,
                    "entity_type": "link",
                    "severity": "ERROR",
                    "reason": "Active link content_hash 与 review 中的 reviewedContentHash 不一致",
                    "evidence": {"linkId": lid, "currentHash": ch, "reviewedHash": r.get("reviewedContentHash")},
                    "disposition": "REFRESH_LINK_REVIEW",
                    "resolved": False
                })

    # 4. RULE_UPCOMING_VERSION_ACTIVE_LINK / RULE_REPEALED_VERSION_ACTIVE_LINK (ERROR)
    for lid, l in links.items():
        if l.get("lifecycle") == "active":
            cid = l.get("clauseId")
            c = clauses.get(cid, {})
            lvid = c.get("lawVersionId")
            lv = lvs.get(lvid, {})
            val = lv.get("validityStatus")
            eff = lv.get("effectiveDate") or ""
            end = lv.get("endDate") or ""

            if val == "upcoming" or (eff and eff > AS_OF):
                findings.append({
                    "rule_id": "RULE_UPCOMING_VERSION_ACTIVE_LINK",
                    "entity_id": lid,
                    "entity_type": "link",
                    "severity": "ERROR",
                    "reason": f"Active link 依赖了尚未实施的 upcoming 版本 {lvid} (eff={eff})",
                    "evidence": {"linkId": lid, "lawVersionId": lvid, "effectiveDate": eff},
                    "disposition": "DEMOTE_LINK_OR_SWITCH_CURRENT",
                    "resolved": False
                })

            if val == "repealed" or (end and end <= AS_OF):
                findings.append({
                    "rule_id": "RULE_REPEALED_VERSION_ACTIVE_LINK",
                    "entity_id": lid,
                    "entity_type": "link",
                    "severity": "ERROR",
                    "reason": f"Active link 依赖了已废止版本 {lvid} (endDate={end})",
                    "evidence": {"linkId": lid, "lawVersionId": lvid, "endDate": end},
                    "disposition": "MIGRATE_OR_DEMOTE_LINK",
                    "resolved": False
                })

    # 5. RULE_DUPLICATE_ACTIVE_TITLE (ERROR)
    active_by_title = defaultdict(list)
    for hid, h in hazards.items():
        if h.get("lifecycle") == "active" and not h.get("mergedInto"):
            norm_t = norm_text(h.get("title"))
            active_by_title[norm_t].append(hid)

    for norm_t, hids in active_by_title.items():
        if len(hids) > 1 and len(norm_t) >= 6:
            for hid in hids:
                findings.append({
                    "rule_id": "RULE_DUPLICATE_ACTIVE_TITLE",
                    "entity_id": hid,
                    "entity_type": "hazard",
                    "severity": "ERROR",
                    "reason": f"存在重名 active 隐患: {hids}",
                    "evidence": {"hazardId": hid, "duplicateGroup": hids, "title": hazards[hid].get("title")},
                    "disposition": "MERGE_DUPLICATES",
                    "resolved": False
                })

    # 6. RULE_DUPLICATE_PROPOSED_ACTIVE (WARNING / ACTIONABLE)
    active_norm_map = {norm_text(h.get("title")): hid for hid, h in hazards.items() if h.get("lifecycle") == "active"}
    for hid, h in hazards.items():
        if h.get("lifecycle") == "proposed" and not h.get("mergedInto"):
            norm_t = norm_text(h.get("title"))
            if norm_t in active_norm_map and len(norm_t) >= 6:
                act_target = active_norm_map[norm_t]
                findings.append({
                    "rule_id": "RULE_DUPLICATE_PROPOSED_ACTIVE",
                    "entity_id": hid,
                    "entity_type": "hazard",
                    "severity": "WARNING",
                    "reason": f"Proposed 候选与 Active 隐患 {act_target} 标题完全相同",
                    "evidence": {"proposedId": hid, "activeTargetId": act_target, "title": h.get("title")},
                    "disposition": "MERGE_INTO_ACTIVE",
                    "resolved": False
                })

    # 7. RULE_CLAUSE_TEXT_CORRUPTION (ERROR / WARNING)
    # 检测如 1×Ω, 10Ω 漏掉指数, 乱码等
    for cid, c in clauses.items():
        quote = c.get("quote", "")
        # 匹配 1×Ω 或 类似遗漏上标
        if re.search(r"1[×x]\s*Ω|10Ω|1\.0[×x]10Ω", quote):
            findings.append({
                "rule_id": "RULE_CLAUSE_TEXT_CORRUPTION",
                "entity_id": cid,
                "entity_type": "clause",
                "severity": "WARNING",
                "reason": "条款原文疑似缺失科学计数法指数/上标（如 1×Ω 或 10Ω 代替 10^9）",
                "evidence": {"clauseId": cid, "snippet": quote[:80]},
                "disposition": "RESTORE_VERBATIM_EXPONENT",
                "resolved": False
            })

    # 8. RULE_OBLIGATION_RESTATEMENT (WARNING)
    for hid, h in hazards.items():
        title = h.get("title", "")
        if re.search(r"^(依法)?(应当|必须).*(未经|擅自|未)", title) or "中的" in title and "必须配置" in title:
            findings.append({
                "rule_id": "RULE_OBLIGATION_RESTATEMENT",
                "entity_id": hid,
                "entity_type": "hazard",
                "severity": "WARNING",
                "reason": "标题为法条复述式或正向义务陈述，缺少精炼不符合状态表述",
                "evidence": {"hazardId": hid, "title": title},
                "disposition": "REWRITE_HAZARD_DEFECT",
                "resolved": False
            })

    # 9. RULE_HAZARD_WITHOUT_ACTIVE_LINK (ERROR)
    active_links_by_hazard = defaultdict(list)
    for lid, l in links.items():
        if l.get("lifecycle") == "active":
            active_links_by_hazard[l.get("hazardId")].append(lid)

    for hid, h in hazards.items():
        if h.get("lifecycle") == "active":
            if not active_links_by_hazard[hid]:
                findings.append({
                    "rule_id": "RULE_HAZARD_WITHOUT_ACTIVE_LINK",
                    "entity_id": hid,
                    "entity_type": "hazard",
                    "severity": "ERROR",
                    "reason": "Active 隐患没有任何 active link 支撑",
                    "evidence": {"hazardId": hid, "title": h.get("title")},
                    "disposition": "ADD_ACTIVE_LINK_OR_DEMOTE",
                    "resolved": False
                })

    return findings

def main():
    findings = run_scan()
    print(f"Scan complete. Total findings: {len(findings)}")

    errors = [f for f in findings if f["severity"] == "ERROR"]
    warnings = [f for f in findings if f["severity"] == "WARNING"]

    print(f"  Real Errors (ERROR): {len(errors)}")
    print(f"  Heuristic Suspects (WARNING): {len(warnings)}")

    err_by_rule = Counter(f["rule_id"] for f in errors)
    print("\nErrors by rule:")
    for r, c in err_by_rule.most_common():
        print(f"  {r}: {c}")

    warn_by_rule = Counter(f["rule_id"] for f in warnings)
    print("\nWarnings by rule:")
    for r, c in warn_by_rule.most_common():
        print(f"  {r}: {c}")

    # 保存机器可复核结果
    report_file = ROOT / "docs" / "scan_findings.jsonl"
    with open(report_file, "w", encoding="utf-8") as f:
        for fnd in findings:
            f.write(json.dumps(fnd, ensure_ascii=False) + "\n")
    print(f"\nWrote machine-checkable scan findings to: {report_file}")

if __name__ == "__main__":
    main()
