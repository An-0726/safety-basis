#!/usr/bin/env python3
"""Reproducible knowledge inventory, candidate queue and dated release reconciliation.

Reads the existing Release Gate; never changes admission, reviews or knowledge.
The queue ranks evidence work, not the risk/severity of an unobserved site.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools" / "v4"))
from canonical import content_hash  # noqa: E402
from release_gate_core import evaluate_release_gate  # noqa: E402

ENTITY_DIRS = {"laws": "laws", "lawVersions": "law-versions", "clauses": "clauses",
               "hazards": "hazards", "links": "links", "evidence": "evidence",
               "successions": "successions", "requirements": "requirements"}
GAP_LABELS = {
    "no_exact_clause": "尚无精确条款关联",
    "rejected_or_misaligned_basis": "原依据或关联已拒绝，须重新对题核验",
    "version_transition_or_effectivity": "版本衔接或效力状态待核",
    "supporting_only": "只有辅助依据，缺独立支撑条款",
    "official_evidence_missing": "原文证据缺失或引用未解析",
    "hazard_review_pending": "内容审核未完成",
    "applicability_or_review_pending": "适用性或条款审核待补",
}
# Evidence-work priority, not a major-hazard determination or a site risk grade.
SCENE_WEIGHTS = [
    (r"爆炸|防爆|粉尘|镁|铝粉|除尘|喷涂|静电", 35, "爆炸及粉尘防护"),
    (r"有限空间|缺氧|窒息|硫化氢|氨|有毒|熔融|金属熔|高温液", 35, "中毒窒息及高温介质"),
    (r"燃气|液化|可燃|易燃|动火|氧气|乙炔|气瓶|危险化学", 30, "燃气及危化介质"),
    (r"触电|漏电|接地|带电|配电|电源|电缆|绝缘", 25, "用电保护"),
    (r"疏散|安全出口|消防|灭火|火灾|通道", 20, "消防及疏散"),
    (r"高处|坠落|起重|吊|压力|机械|防护罩|传动", 20, "作业及设备防护"),
]
STANDARD_RE = re.compile(
    r"\b(GBZ?|AQ|TSG|GBJ|GA|HJ|JGJ|DL|JB)\s*(?:[/／]\s*(T))?\s*[-—–]?\s*"
    r"(\d{2,6}(?:\.\d+)?)\s*[-—–]\s*((?:19|20)\d{2})", re.I)


def read_records(root: Path, dirname: str, review: bool = False) -> tuple[dict, dict]:
    records, paths = {}, {}
    for path in sorted((root / dirname).glob("*.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        key = (row.get("entityId") if review else row.get("id")) or path.stem
        if key in records:
            raise ValueError(f"duplicate stable ID in {dirname}: {key}")
        records[key] = row
        paths[key] = path.relative_to(root.parent).as_posix()
    return records, paths


def source_fingerprint(root: Path) -> str:
    dig = hashlib.sha256()
    for path in sorted(root.rglob("*.json")):
        dig.update(path.relative_to(root).as_posix().encode())
        dig.update(b"\0")
        dig.update(path.read_bytes())
        dig.update(b"\0")
    return dig.hexdigest()


def standard_refs(text: str) -> set[str]:
    return {f"{m[1].upper()}{'/T' if m[2] else ''}{m[3]}-{m[4]}"
            for m in STANDARD_RE.finditer(text)}


def project(gate, links: dict, clauses: dict) -> dict:
    # eligible_links alone includes content-rejected hazards. Match builder order.
    kids = sorted(k for k in gate.eligible_links
                  if links[k].get("hazardId") in gate.eligible_hazards)
    cids = sorted({links[k]["clauseId"] for k in kids})
    vids = sorted({clauses[c]["lawVersionId"] for c in cids})
    ids = {"hazards": sorted(gate.eligible_hazards), "links": kids,
           "clauses": cids, "lawVersions": vids}
    return {"counts": {k: len(v) for k, v in ids.items()}, "ids": ids}


def review_state(entity: dict, review: dict, evidence: dict) -> dict:
    refs = review.get("evidenceRefs") or []
    refs = refs if isinstance(refs, list) else []
    return {"decision": review.get("decision", "missing"),
            "hashCurrent": bool(review) and review.get("reviewedContentHash") == content_hash(entity),
            "checkedAt": review.get("checkedAt"),
            "reason": review.get("reason", ""),
            "evidenceRefs": refs,
            "unresolvedEvidenceRefs": [x for x in refs if x.startswith(("E_", "EH_")) and x not in evidence]}


def chain_record(kid: str, entities: dict, reviews: dict, gate) -> dict:
    link = entities["links"][kid]
    cid = link.get("clauseId")
    clause = entities["clauses"].get(cid, {})
    vid = clause.get("lawVersionId")
    version = entities["lawVersions"].get(vid, {})
    lid = version.get("lawId")
    law = entities["laws"].get(lid, {})
    state = lambda entity, kind, ident: review_state(entity, reviews[kind].get(ident, {}), entities["evidence"])
    return {"linkId": kid, "clauseId": cid, "lawVersionId": vid, "lawId": lid,
            "role": link.get("role"), "lifecycle": link.get("lifecycle"),
            "articlePath": clause.get("articlePath"), "officialName": version.get("officialName"),
            "documentNumber": version.get("documentNumber"), "sourceUrl": clause.get("sourceUrl") or version.get("sourceUrl"),
            "effectiveDate": version.get("effectiveDate"), "endDate": version.get("endDate"),
            "validityStatus": version.get("validityStatus"),
            "applicability": link.get("applicability", ""),
            "qualifiesCurrent": kid in gate.eligible_links and link.get("role") in {"direct", "fallback"},
            "gateReasons": {"link": gate.links.get(kid, {}).get("reasons", []),
                            "clause": gate.clauses.get(cid, {}).get("reasons", ["MISSING_CLAUSE"]),
                            "lawVersion": gate.law_versions.get(vid, {}).get("reasons", ["MISSING_VERSION"]),
                            "law": gate.laws.get(lid, {}).get("reasons", ["MISSING_LAW"])},
            "reviews": {"link": state(link, "links", kid), "clause": state(clause, "clauses", cid),
                        "lawVersion": state(version, "lawVersions", vid), "law": state(law, "laws", lid)}}


def classify_gap(chains: list[dict], hazard_review: dict) -> tuple[str, list[str]]:
    codes = []
    if not chains:
        codes.append("NO_STRUCTURED_BASIS_LINK")
    if chains and all(c["role"] == "supporting" for c in chains):
        codes.append("ONLY_SUPPORTING_LINKS")
    reasons = [reason for c in chains for rs in c["gateReasons"].values() for reason in rs]
    if any(c["reviews"][kind]["decision"] == "rejected" for c in chains for kind in ("link", "clause")):
        codes.append("REJECTED_BASIS_OR_APPLICABILITY")
    if any(r.startswith(("BLOCK_VERSION", "MISSING_VERSION")) for r in reasons):
        codes.append("VERSION_CURRENT_SUPPORT_UNAVAILABLE")
    if any(s["unresolvedEvidenceRefs"] for c in chains for s in c["reviews"].values()):
        codes.append("UNRESOLVED_EVIDENCE_REFERENCE")
    if any(not c["reviews"]["clause"]["evidenceRefs"] for c in chains):
        codes.append("CLAUSE_EVIDENCE_NOT_RECORDED")
    if hazard_review["decision"] != "verified" or not hazard_review["hashCurrent"]:
        codes.append("HAZARD_REVIEW_INCOMPLETE")
    if any(not c["qualifiesCurrent"] and c["role"] in {"direct", "fallback"} for c in chains):
        codes.append("QUALIFYING_LINK_NOT_ADMITTED")
    if not codes:
        codes.append("PROPOSED_REQUIRES_SUBSTANTIVE_ADMISSION_REVIEW")
    precedence = [("NO_STRUCTURED_BASIS_LINK", "no_exact_clause"),
                  ("REJECTED_BASIS_OR_APPLICABILITY", "rejected_or_misaligned_basis"),
                  ("VERSION_CURRENT_SUPPORT_UNAVAILABLE", "version_transition_or_effectivity"),
                  ("ONLY_SUPPORTING_LINKS", "supporting_only"),
                  ("UNRESOLVED_EVIDENCE_REFERENCE", "official_evidence_missing"),
                  ("CLAUSE_EVIDENCE_NOT_RECORDED", "official_evidence_missing")]
    for code, primary in precedence:
        if code in codes:
            return primary, codes
    if any(c["qualifiesCurrent"] for c in chains) and "HAZARD_REVIEW_INCOMPLETE" in codes:
        return "hazard_review_pending", codes
    return "applicability_or_review_pending", codes


def source_clues(hazard: dict) -> list[str]:
    """Original notes are leads, never verified clauses. Do not overwrite them."""
    note = str(hazard.get("note") or "")
    clues = re.findall(r"《[^》\n]{2,100}》[^\n]{0,200}", note)
    clues += re.findall(r"(?:GBZ?|AQ|TSG|GBJ|GA|HJ|JGJ)\s*(?:[/／]\s*T)?\s*\d{2,6}(?:\.\d+)?\s*[-—–]\s*\d{4}[^\n]{0,100}", note)
    return list(dict.fromkeys(clues))[:5]


def fact_checklist(hazard: dict) -> list[str]:
    text = " ".join(str(hazard.get(k, "")) for k in ("title", "description", "category"))
    facts = ["核实场所、设备/介质、作业状态及缺陷确实存在；照片或提问本身不等于隐患成立。"]
    if re.search(r"气瓶|燃气|液化|乙炔|氨|可燃|爆炸|粉尘|防爆", text):
        facts.append("确认介质/粉尘性质、实际工艺、危险区域或场所分类及设备设计用途；不得由相近关键词推定。")
    if re.search(r"电|接地|绝缘", text):
        facts.append("确认电压等级、固定或临时用电、是否建筑施工、接地系统和具体保护措施；需检测的缺陷补检测记录。")
    if re.search(r"出口|通道|疏散|建筑|消防|灭火", text):
        facts.append("确认建筑/仓储用途、建成年代、人员与火灾条件、通道功能、配置数量或尺寸及适用地方要求。")
    if re.search(r"有限空间|高处|检修|动火|吊|机械|压力", text):
        facts.append("确认具体作业边界、设备类型、暴露或能量状态及已有等效防护，保留现场确认记录。")
    if re.search(r"档案|记录|培训|制度|台账|检测|检查", text):
        facts.append("确认被要求的责任主体、项目范围和周期；区分未提供记录与确实未履行义务。")
    return facts


def actions(hazard: dict, chains: list[dict], primary: str, clues: list[str], successors: dict) -> list[str]:
    title = hazard["title"]
    out = []
    if primary == "no_exact_clause":
        target = "；".join(clues) if clues else f"“{title}”对应{hazard.get('category', '该专业')}具体义务"
        out.append(f"先检索发布机关/国家标准官方渠道的{target}，核对现行版本并取得完整条款原文及精确定位；原note仅是定位线索。")
    else:
        for c in chains:
            target = f"{c.get('officialName') or c.get('lawVersionId') or '缺失法规'} {c.get('documentNumber') or ''} {c.get('articlePath') or '条号待核'}".strip()
            if c["reviews"]["link"]["decision"] == "rejected" or c["reviews"]["clause"]["decision"] == "rejected":
                out.append(f"重新取得并对照{target}官方完整原文，查明原拒绝原因；不能以概括义务/相关术语替代“{title}”的直接支撑。")
            elif any(r.startswith("BLOCK_VERSION") for r in c["gateReasons"]["lawVersion"]):
                refs = successors.get(c.get("lawVersionId"), [])
                hint = "；已有接续线索：" + "、".join(refs) if refs else "；库内无可直接采用的接续关系，先核官方替代公告"
                out.append(f"核对{target}的施行/终止日期{hint}；逐条比对新旧义务后另建现行条款链，不能自动换号。")
            else:
                out.append(f"以{target}完整官方原文核对“{title}”的主体、场景和义务；补齐条款原件定位、证据引用和适用性理由。")
    if primary == "supporting_only":
        out.append("补取得可以独立支撑该缺陷的direct/fallback条款；辅助材料保持supporting。")
    if clues and chains:
        out.append("交叉核对原记录线索（未经确认）：" + "；".join(clues) + "；不得将原表引用直接视为已核依据。")
    out.append("逐项核实本记录conditions及factConfirmation；如果原描述混合不同义务，先收窄或拆分可观察事实，再做条款映射。")
    disposition = "保持proposed" if hazard.get("lifecycle") == "proposed" else "保留原稳定ID及生命周期、继续排除当前发布"
    out.append(f"取得原文且范围吻合后实质复核H/C/K及证据，绑定当前内容与上下文hash；未完成则{disposition}，不公开、不出确定违法结论。")
    return list(dict.fromkeys(out))


def priority(hazard: dict, chains: list[dict], clues: list[str]) -> tuple[int, list[str]]:
    text = " ".join(str(hazard.get(k, "")) for k in ("title", "description", "category"))
    matches = [(weight, name) for pattern, weight, name in SCENE_WEIGHTS if re.search(pattern, text)]
    score = max((v for v, _ in matches), default=10)
    why = sorted({name for _, name in matches}) or ["通用管理义务"]
    if chains:
        score += 8; why.append("已有结构化定位，可优先核对")
    elif clues:
        score += 5; why.append("原记录有条号/标准线索")
    if any(c["qualifiesCurrent"] for c in chains):
        score += 4; why.append("已有通过Gate的候选条款链，需内容及场景实审")
    if re.search(r"符合.*规定|符合.*要求|相关标准|按规定", hazard.get("title", "")):
        score -= 4; why.append("表述概括，先明确具体缺陷")
    return score, why


def succession_impacts(entities: dict, gate, projected: dict, as_of: date) -> tuple[list, list]:
    clauses_by_version = defaultdict(list); links_by_clause = defaultdict(list)
    for cid, c in entities["clauses"].items(): clauses_by_version[c.get("lawVersionId")].append(cid)
    for kid, link in entities["links"].items(): links_by_clause[link.get("clauseId")].append(kid)
    published_links = set(projected["ids"]["links"])
    result, warnings = [], []
    for sid, relation in sorted(entities["successions"].items()):
        old_id, new_id = relation.get("oldVersionId"), relation.get("newVersionId")
        old, new = entities["lawVersions"].get(old_id), entities["lawVersions"].get(new_id)
        if old is None or new is None:
            warnings.append({"code": "SUCCESSION_MISSING_VERSION", "successionId": sid, "oldVersionId": old_id, "newVersionId": new_id})
        cids = sorted(clauses_by_version[old_id]); kids = sorted({kid for cid in cids for kid in links_by_clause[cid]})
        active_hids = sorted({entities["links"][kid]["hazardId"] for kid in kids if entities["hazards"].get(entities["links"][kid].get("hazardId"), {}).get("lifecycle") == "active"})
        published_old = sorted({entities["links"][kid]["hazardId"] for kid in kids if kid in published_links})
        old_refs = standard_refs(" ".join(str((old or {}).get(x, "")) for x in ("officialName", "documentNumber", "versionKey")))
        text_hits = []
        if old_refs:
            for hid, h in sorted(entities["hazards"].items()):
                fields = [field for field in ("title", "description", "conditions", "note") if old_refs & standard_refs(str(h.get(field, "")))]
                if fields: text_hits.append({"hazardId": hid, "lifecycle": h.get("lifecycle"), "fields": fields})
        due = bool(relation.get("effectiveDate") and relation["effectiveDate"] <= as_of.isoformat())
        classification = "future_transition" if not due else ("partial_scope_only" if relation.get("relation") == "partially_replaces" else "effective_full_transition")
        if due and relation.get("relation") == "replaces" and published_old:
            warnings.append({"code": "PUBLISHED_OLD_VERSION_AFTER_FULL_SUCCESSION", "successionId": sid, "hazardIds": published_old})
        result.append({"successionId": sid, **relation, "classification": classification,
                       "oldName": (old or {}).get("officialName"), "newName": (new or {}).get("officialName"),
                       "oldCurrentSupport": gate.law_versions.get(old_id, {}).get("supports_current", False),
                       "newCurrentSupport": gate.law_versions.get(new_id, {}).get("supports_current", False),
                       "storedOldClauseIds": cids, "structuredActiveHazardIds": active_hids,
                       "currentPublishedOldHazardIds": published_old,
                       "textClues": text_hits,
                       "textClueMeaning": "字段含旧标准代号/年份的定位线索，包括历史note；不证明现行引用错误，不自动替代或晋级。"})
    for vid, v in sorted(entities["lawVersions"].items()):
        if v.get("validityStatus") == "upcoming" and v.get("effectiveDate") and v["effectiveDate"] <= as_of.isoformat():
            warnings.append({"code": "UPCOMING_PAST_EFFECTIVE_DATE", "lawVersionId": vid, "officialName": v.get("officialName"), "effectiveDate": v.get("effectiveDate"), "action": "复核官方当前版本和完整原文后再改变效力/审核；日期到达不自动转正。"})
    return result, warnings


def build_audit(knowledge: Path, as_of: date, baseline_as_of: date, priority_limit: int = 40) -> tuple[dict, list]:
    entities, paths, reviews = {}, {}, {}
    for kind, directory in ENTITY_DIRS.items(): entities[kind], paths[kind] = read_records(knowledge, directory)
    for kind in ("laws", "lawVersions", "clauses", "hazards", "links"):
        reviews[kind], _ = read_records(knowledge, "reviews/" + ENTITY_DIRS[kind], review=True)
    gate = evaluate_release_gate(knowledge, as_of=as_of)
    baseline_gate = evaluate_release_gate(knowledge, as_of=baseline_as_of)
    current = project(gate, entities["links"], entities["clauses"])
    baseline = project(baseline_gate, entities["links"], entities["clauses"])
    by_hazard, successors = defaultdict(list), defaultdict(list)
    for kid, link in entities["links"].items(): by_hazard[link.get("hazardId")].append(kid)
    for relation in entities["successions"].values(): successors[relation.get("oldVersionId")].append(relation.get("newVersionId"))
    candidates, excluded = [], []
    for hid, h in sorted(entities["hazards"].items()):
        if h.get("lifecycle") not in {"active", "proposed"}: continue
        if h.get("lifecycle") == "active" and hid in gate.eligible_hazards: continue
        chains = [chain_record(kid, entities, reviews, gate) for kid in sorted(by_hazard[hid])]
        review = review_state(h, reviews["hazards"].get(hid, {}), entities["evidence"])
        primary, codes = classify_gap(chains, review)
        clues = source_clues(h)
        row = {"hazardId": hid, "title": h["title"], "category": h.get("category"),
               "lifecycle": h.get("lifecycle"), "sourcePath": paths["hazards"][hid], "contentHash": content_hash(h),
               "primaryGap": primary, "primaryGapLabel": GAP_LABELS[primary], "gapCodes": codes,
               "hazardReview": review, "hazardGateReasons": gate.hazards[hid]["reasons"],
               "basisLinks": chains, "originalUnverifiedSourceClues": clues,
               "conditions": h.get("conditions", ""), "factConfirmation": fact_checklist(h),
               "minimumEvidenceActions": actions(h, chains, primary, clues, successors),
               "disposition": "retain_proposed" if h.get("lifecycle") == "proposed" else "exclude_from_current_release",
               "currentlyPublished": False}
        if h.get("lifecycle") == "proposed":
            score, why = priority(h, chains, clues)
            row.update(priorityScore=score, priorityReasons=why)
            candidates.append(row)
        else: excluded.append(row)
    ranked = sorted(candidates, key=lambda r: (-r["priorityScore"], r["hazardId"]))
    for rank, row in enumerate(ranked, start=1):
        row.update(priorityRank=rank, priorityBand="P1" if rank <= priority_limit else ("P2" if row["priorityScore"] >= 30 else "P3"))
    impacts, warnings = succession_impacts(entities, gate, current, as_of)
    life = Counter(h.get("lifecycle") for h in entities["hazards"].values())
    errors = []
    if len(candidates) != life["proposed"]: errors.append("candidate coverage mismatch")
    if len(excluded) + len(current["ids"]["hazards"]) != life["active"]: errors.append("active reconciliation mismatch")
    if set(current["ids"]["hazards"]) & {r["hazardId"] for r in candidates}: errors.append("proposed leaked into release")
    for c in candidates:
        if not c["minimumEvidenceActions"] or not c["factConfirmation"]: errors.append("incomplete candidate action: " + c["hazardId"])
    audit = {"schemaVersion": 1, "asOf": as_of.isoformat(), "baselineAsOf": baseline_as_of.isoformat(),
             "sourceFingerprint": source_fingerprint(knowledge),
             "method": "读取正式knowledge和现有release_gate_core；按Gate发布集合逐ID对账。优先级为补证工作排序，不是现场风险评级或重大隐患结论。",
             "inventory": {key: len(value) for key, value in entities.items()}, "lifecycle": dict(sorted(life.items())),
             "candidateCount": len(candidates), "candidateGapCounts": dict(sorted(Counter(r["primaryGap"] for r in candidates).items())),
             "priorityCount": min(priority_limit, len(candidates)), "priorityHazardIds": [r["hazardId"] for r in ranked[:priority_limit]],
             "baselineProjection": baseline, "currentProjection": current,
             "dateProjectionChanges": {key: {"addedIds": sorted(set(current["ids"][key]) - set(baseline["ids"][key])),
                                             "removedIds": sorted(set(baseline["ids"][key]) - set(current["ids"][key]))} for key in current["ids"]},
             "activeExcluded": excluded, "successions": impacts, "versionWarnings": warnings, "validationErrors": errors}
    return audit, candidates


def markdown_queue(audit: dict, candidates: list[dict]) -> str:
    by_id = {r["hazardId"]: r for r in candidates}
    lines = [f"# 候选优先补证队列（{audit['asOf']}）", "",
             f"全部 {audit['candidateCount']} 条详见同日 `CANDIDATE_INVENTORY_*.jsonl`；本页按确定性工作排序列出前 {audit['priorityCount']} 条。",
             "", "这些记录均保持 proposed，不表示已确认任何企业隐患。分数综合场景后果相关性、现有定位可操作性和描述具体程度，不用于重大隐患认定。相同分数按稳定ID排序。", "",
             "完整命令：`python tools/checks/knowledge_closeout.py --as-of " + audit["asOf"] + " --baseline-as-of " + audit["baselineAsOf"] + " --out docs`。", ""]
    for hid in audit["priorityHazardIds"]:
        r = by_id[hid]
        lines += [f"## {r['priorityRank']}. {r['title']}", "", f"- 稳定ID：`{hid}`；工作优先分 {r['priorityScore']}；缺口：{r['primaryGapLabel']}。",
                  f"- 原记录：[`{hid}`](../{r['sourcePath']})。",
                  "- 排序理由：" + "；".join(r["priorityReasons"]) + "。",
                  "- 原适用条件：" + str(r["conditions"]).replace("\n", " "), "", "最小补证动作：", ""]
        lines += [str(i) + ". " + text.replace("\n", " ") for i, text in enumerate(r["minimumEvidenceActions"], 1)]
        lines += ["", "事实确认：", ""] + ["- " + text for text in r["factConfirmation"]] + [""]
    return "\n".join(lines).rstrip() + "\n"


def markdown_summary(audit: dict) -> str:
    counts = audit["currentProjection"]["counts"]
    lines = [f"# 知识库可重建对账（{audit['asOf']}）", "", audit["method"], "",
             "本文件为机器产物；证据核验、实施前线上版本与本次修复解释见 [收口报告](KNOWLEDGE_CLOSEOUT.md)。", "",
             "## 源库与公开投影", "", "|对象|源库数量|当前发布投影|", "|---|---:|---:|"]
    for key, label in [("hazards", "隐患记录"), ("lawVersions", "法源版本"), ("clauses", "条款"), ("links", "关联")]:
        lines.append(f"|{label}|{audit['inventory'][key]}|{counts[key]}|")
    lines += ["", f"H lifecycle：active {audit['lifecycle'].get('active', 0)} / proposed {audit['lifecycle'].get('proposed', 0)} / superseded {audit['lifecycle'].get('superseded', 0)}。active中有 {len(audit['activeExcluded'])} 条没有通过完整发布链。", "",
              "## 266候选的当前缺口分类" if audit["candidateCount"] == 266 else "## 候选的当前缺口分类", "", "|主要缺口|数量|", "|---|---:|"]
    for gap, n in audit["candidateGapCounts"].items(): lines.append(f"|{GAP_LABELS[gap]}|{n}|")
    lines += ["", "主分类互斥用于计数；每条记录还保留全部 gapCodes、关联/条款/版本/法规Gate理由及证据状态，不能把单一主分类当成完整法律审查。", "",
              "## active而未发布的逐ID原因", "", "|稳定ID|标题|主要原因|", "|---|---|---|"]
    for r in audit["activeExcluded"]:
        reason = list(r["hazardGateReasons"])
        for c in r["basisLinks"]: reason.extend(c["gateReasons"]["link"] + c["gateReasons"]["clause"])
        lines.append(f"|`{r['hazardId']}`|{r['title'].replace('|', '｜')}|{'；'.join(dict.fromkeys(reason))}|")
    lines += ["", "每项最小补证动作与确切K/C/LV链在同日JSON的 `activeExcluded` 中；没有删除或改写这些稳定ID。", "",
              f"## {audit['baselineAsOf']}→{audit['asOf']}的逐ID版本投影变化", ""]
    for key, changes in audit["dateProjectionChanges"].items():
        lines += [f"### {key}", "", "- 新增：" + ("、".join('`'+x+'`' for x in changes["addedIds"]) or "无") + "。",
                  "- 移出：" + ("、".join('`'+x+'`' for x in changes["removedIds"]) or "无") + "。", ""]
    lines += ["## succession与效力待办", "", f"逐条检查 {len(audit['successions'])} 个succession，完整关系、旧条款、受关联active H、当前发布旧版H及旧代号文本线索在JSON中。部分替代不按整部废止处理，历史note命中不自动判错。", "",
              "|当前观察|版本/关系|最小动作|", "|---|---|---|"]
    for warning in audit["versionWarnings"]:
        lines.append(f"|{warning['code']}|`{warning.get('lawVersionId') or warning.get('successionId')}`|{warning.get('action', '核对完整替代范围及当前发布关联；禁止自动换号')}|")
    if not audit["versionWarnings"]: lines.append("|无新增结构/日期预警|—|保持按日复核|")
    lines += ["", "## 产物与复现", "", "- 全量候选JSONL：每个proposed恰好一行，含稳定ID、证据链、条件、优先分和具体补证动作。",
              "- 优先队列Markdown：前40项，便于人工领取。", "- 对账JSON：库存、公开集合、排除原因、逐ID日期差异与全部succession。",
              "- `--check`：比较生成文件与当前源库，产物过期或有覆盖/计数错误时非零退出；不会更新审核、修改知识或放宽发布。", "",
              f"知识源指纹：`{audit['sourceFingerprint']}`。验证错误数：{len(audit['validationErrors'])}。", ""]
    return "\n".join(lines)


def output_files(audit: dict, candidates: list[dict]) -> dict[str, str]:
    stamp = audit["asOf"].replace("-", "")
    return {f"CANDIDATE_INVENTORY_{stamp}.jsonl": "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in candidates),
            f"CANDIDATE_PRIORITY_{stamp}.md": markdown_queue(audit, candidates),
            f"KNOWLEDGE_CLOSEOUT_{stamp}.json": json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            f"KNOWLEDGE_CLOSEOUT_{stamp}.md": markdown_summary(audit)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--knowledge", type=Path, default=REPO / "knowledge")
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--baseline-as-of", type=date.fromisoformat, default=date(2026, 10, 16))
    parser.add_argument("--priority-limit", type=int, default=40)
    parser.add_argument("--out", type=Path, default=REPO / "docs")
    parser.add_argument("--check", action="store_true", help="Compare existing artifacts, do not write")
    args = parser.parse_args(argv)
    if args.priority_limit < 1: parser.error("--priority-limit must be positive")
    audit, candidates = build_audit(args.knowledge.resolve(), args.as_of, args.baseline_as_of, args.priority_limit)
    outputs = output_files(audit, candidates)
    errors = list(audit["validationErrors"])
    for name, text in outputs.items():
        path = args.out / name
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != text: errors.append("outdated or missing artifact: " + str(path))
        else:
            path.parent.mkdir(parents=True, exist_ok=True);path.write_text(text, encoding="utf-8")
    print(json.dumps({"asOf": audit["asOf"], "inventory": audit["inventory"], "lifecycle": audit["lifecycle"],
                      "projection": audit["currentProjection"]["counts"], "candidateGapCounts": audit["candidateGapCounts"],
                      "activeExcluded": len(audit["activeExcluded"]), "successions": len(audit["successions"]),
                      "versionWarnings": len(audit["versionWarnings"]), "errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
