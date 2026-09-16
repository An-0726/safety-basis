#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a deterministic PHASE 6 proposed-hazard evidence backlog.

This is an inventory/reporting tool.  It never mutates ``knowledge/``, the
private library, SQLite, or release output.  A candidate remains ``proposed``
until the normal evidence-chain gate is completed by a separate, reviewed
batch.

The report deliberately distinguishes mechanical linkage facts from legal
conclusions.  A verified sidecar or an existing URL is not treated as proof
that a candidate is ready for publication; it is only recorded as an input
to the next official-source review.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE = ROOT / "knowledge"
DEFAULT_AS_OF = "2026-09-16"
EXPECTED_PROPOSED = 519
QUALIFYING_ROLES = {"direct", "fallback"}
SUPPORTED_ROLES = {"direct", "fallback", "supporting"}

sys.path.insert(0, str(ROOT / "tools" / "v4"))
from canonical import content_hash  # noqa: E402  (repository canonical hash)


def load_dir(relative: str | Path) -> dict[str, dict[str, Any]]:
    """Load JSON entities keyed by their stable id/entityId."""

    result: dict[str, dict[str, Any]] = {}
    for path in sorted((KNOWLEDGE / relative).glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        key = data.get("id") or data.get("entityId") or path.stem
        result[str(key)] = data
    return result


def load_scope() -> dict[str, str]:
    """Read PHASE 5 target classification without treating it as new evidence."""

    result: dict[str, str] = {}
    path = ROOT / "docs" / "hazard-reconciliation.jsonl"
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("recordType") == "target":
            result[str(record["hazardId"])] = str(record.get("classification") or "unknown")
    return result


def parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def evidence_refs(value: Any) -> tuple[list[str], list[Any]]:
    """Split string evidence IDs from malformed/non-ID values."""

    ids: list[str] = []
    malformed: list[Any] = []
    for item in value or []:
        if isinstance(item, str):
            ids.append(item)
        else:
            malformed.append(item)
    return ids, malformed


def evidence_summary(refs: Iterable[Any], evidence: dict[str, dict[str, Any]]) -> dict[str, Any]:
    ids, malformed = evidence_refs(list(refs))
    unique_ids = sorted(set(ids))
    existing = [item for item in unique_ids if item in evidence]
    authoritative = [
        item
        for item in existing
        if (evidence.get(item) or {}).get("tier") == "authoritative-public"
    ]
    return {
        "refCount": len(list(refs)) if not isinstance(refs, list) else len(refs),
        "uniqueIdCount": len(unique_ids),
        "ids": unique_ids,
        "existingIds": existing,
        "authoritativePublicIds": authoritative,
        "malformedCount": len(malformed),
    }


def review_snapshot(
    entity: dict[str, Any] | None,
    review: dict[str, Any] | None,
    *,
    evidence: dict[str, dict[str, Any]],
    require_evidence: bool,
) -> tuple[dict[str, Any], list[str]]:
    """Return a stable review summary and mechanical blocker codes."""

    reasons: list[str] = []
    if not review:
        reasons.append("REVIEW_MISSING")
        return {
            "present": False,
            "decision": "missing",
            "evidence": evidence_summary([], evidence),
        }, reasons

    decision = review.get("decision") or "missing"
    if decision != "verified":
        reasons.append(f"REVIEW_NOT_VERIFIED:{decision}")
    if entity is not None and review.get("reviewedContentHash"):
        if review.get("reviewedContentHash") != content_hash(entity):
            reasons.append("REVIEW_STALE")
    refs, malformed = evidence_refs(review.get("evidenceRefs") or [])
    evidence_state = evidence_summary(refs + malformed, evidence)
    # Keep malformed items visible without copying arbitrary nested objects to
    # the report.  They are structural defects, not evidence.
    if malformed:
        reasons.append("EVIDENCE_REF_MALFORMED")
    if require_evidence and not refs:
        reasons.append("EVIDENCE_REF_MISSING")
    if require_evidence and refs and not any(item in evidence for item in refs):
        reasons.append("EVIDENCE_REF_UNKNOWN")
    return {
        "present": True,
        "decision": decision,
        "reviewType": review.get("reviewType"),
        "checkedAt": review.get("checkedAt") or review.get("reviewedAt"),
        "reviewer": review.get("reviewer"),
        "reasonCodes": sorted(set(review.get("reasonCodes") or [])),
        "evidence": evidence_state,
        "hashCurrent": "REVIEW_STALE" not in reasons,
    }, reasons


def law_version_snapshot(
    clause: dict[str, Any] | None,
    clauses: dict[str, dict[str, Any]],
    law_versions: dict[str, dict[str, Any]],
    laws: dict[str, dict[str, Any]],
    law_version_reviews: dict[str, dict[str, Any]],
    law_reviews: dict[str, dict[str, Any]],
    evidence: dict[str, dict[str, Any]],
    as_of: date,
) -> tuple[dict[str, Any], list[str]]:
    """Summarize the clause -> version -> law side of the chain."""

    reasons: list[str] = []
    if not clause:
        return {"present": False}, ["CLAUSE_MISSING"]

    clause_id = str(clause.get("id"))
    version_id = clause.get("lawVersionId")
    version = law_versions.get(version_id) if version_id else None
    if not version:
        reasons.append("LAW_VERSION_MISSING")
    law = laws.get(version.get("lawId")) if version else None
    if version and not law:
        reasons.append("LAW_MISSING")

    version_status = version.get("validityStatus") if version else None
    effective = parse_date(version.get("effectiveDate")) if version else None
    end = parse_date(version.get("endDate")) if version else None
    supports_current = bool(
        version
        and version_status == "active"
        and effective
        and effective <= as_of
        and (not end or as_of < end)
    )
    if version and not supports_current:
        reasons.append("LAW_VERSION_NOT_CURRENT")

    version_review, version_review_reasons = review_snapshot(
        version,
        law_version_reviews.get(version_id) if version_id else None,
        evidence=evidence,
        require_evidence=True,
    )
    law_review, law_review_reasons = review_snapshot(
        law,
        law_reviews.get(version.get("lawId")) if version and version.get("lawId") else None,
        evidence=evidence,
        require_evidence=True,
    )
    reasons.extend(f"LAW_VERSION_REVIEW:{code}" for code in version_review_reasons)
    reasons.extend(f"LAW_REVIEW:{code}" for code in law_review_reasons)

    return {
        "present": True,
        "clauseId": clause_id,
        "lawVersionId": version_id,
        "lawId": version.get("lawId") if version else None,
        "lawName": law.get("canonicalName") if law else None,
        "lawVersionName": version.get("officialName") if version else None,
        "validityStatus": version_status,
        "effectiveDate": version.get("effectiveDate") if version else None,
        "endDate": version.get("endDate") if version else None,
        "supportsCurrent": supports_current,
        "lawReview": law_review,
        "lawVersionReview": version_review,
    }, reasons


def clause_snapshot(
    clause_id: Any,
    clauses: dict[str, dict[str, Any]],
    clause_reviews: dict[str, dict[str, Any]],
    law_versions: dict[str, dict[str, Any]],
    laws: dict[str, dict[str, Any]],
    law_version_reviews: dict[str, dict[str, Any]],
    law_reviews: dict[str, dict[str, Any]],
    evidence: dict[str, dict[str, Any]],
    as_of: date,
) -> tuple[dict[str, Any], list[str]]:
    reasons: list[str] = []
    clause = clauses.get(clause_id) if clause_id else None
    if not clause:
        return {"present": False, "clauseId": clause_id}, ["CLAUSE_MISSING"]

    if (clause.get("lifecycle") or "active") != "active":
        reasons.append("CLAUSE_NOT_ACTIVE")
    if not clause.get("articlePath"):
        reasons.append("CLAUSE_LOCATOR_MISSING")
    if not clause.get("quote"):
        reasons.append("CLAUSE_QUOTE_MISSING")

    review, review_reasons = review_snapshot(
        clause,
        clause_reviews.get(clause_id),
        evidence=evidence,
        require_evidence=True,
    )
    reasons.extend(f"CLAUSE_REVIEW:{code}" for code in review_reasons)
    chain, chain_reasons = law_version_snapshot(
        clause,
        clauses,
        law_versions,
        laws,
        law_version_reviews,
        law_reviews,
        evidence,
        as_of,
    )
    reasons.extend(chain_reasons)
    return {
        "present": True,
        "clauseId": clause.get("id"),
        "articlePath": clause.get("articlePath"),
        "quotePresent": bool(clause.get("quote")),
        "sourceUrl": clause.get("sourceUrl"),
        "lifecycle": clause.get("lifecycle") or "active",
        "review": review,
        "chain": chain,
    }, reasons


def link_snapshot(
    link: dict[str, Any],
    hazard: dict[str, Any],
    links_reviews: dict[str, dict[str, Any]],
    clauses: dict[str, dict[str, Any]],
    clause_reviews: dict[str, dict[str, Any]],
    law_versions: dict[str, dict[str, Any]],
    laws: dict[str, dict[str, Any]],
    law_version_reviews: dict[str, dict[str, Any]],
    law_reviews: dict[str, dict[str, Any]],
    evidence: dict[str, dict[str, Any]],
    as_of: date,
) -> tuple[dict[str, Any], list[str]]:
    reasons: list[str] = []
    link_id = str(link.get("id"))
    role = link.get("role")
    if role not in SUPPORTED_ROLES:
        reasons.append("LINK_ROLE_INVALID")
    if role not in QUALIFYING_ROLES:
        reasons.append("LINK_NOT_QUALIFYING_ROLE")
    if (link.get("lifecycle") or "active") != "active":
        reasons.append("LINK_NOT_ACTIVE")
    if not link.get("applicability"):
        reasons.append("LINK_APPLICABILITY_MISSING")

    review = links_reviews.get(link_id)
    review_summary, review_reasons = review_snapshot(
        link,
        review,
        evidence=evidence,
        require_evidence=False,
    )
    reasons.extend(f"LINK_REVIEW:{code}" for code in review_reasons)
    if review and review.get("decision") == "verified":
        if not review.get("reason"):
            reasons.append("LINK_REVIEW_REASON_MISSING")
        contexts = review.get("contextHashes") or {}
        if contexts.get("hazard") != content_hash(hazard):
            reasons.append("LINK_CONTEXT_HAZARD_STALE")

    clause_summary, clause_reasons = clause_snapshot(
        link.get("clauseId"),
        clauses,
        clause_reviews,
        law_versions,
        laws,
        law_version_reviews,
        law_reviews,
        evidence,
        as_of,
    )
    reasons.extend(clause_reasons)
    if review and review.get("decision") == "verified":
        clause = clauses.get(link.get("clauseId"))
        contexts = review.get("contextHashes") or {}
        if clause and contexts.get("clause") != content_hash(clause):
            reasons.append("LINK_CONTEXT_CLAUSE_STALE")

    return {
        "linkId": link_id,
        "role": role,
        "qualifyingRole": role in QUALIFYING_ROLES,
        "lifecycle": link.get("lifecycle") or "active",
        "clauseId": link.get("clauseId"),
        "review": review_summary,
        "clause": clause_summary,
        "reasonCodes": sorted(set(reasons)),
    }, sorted(set(reasons))


def proposal_stage(status: str | None) -> str:
    return {
        "workbook_revised_pending_clause_rebind": "workbook_revised",
        "basis_catalog_only": "catalog_only",
        "knowledge_extra_non_target_pending_scope_review": "non_target_scope_review",
    }.get(status or "", "unspecified")


def backlog_group(status: str | None, links: list[dict[str, Any]], target_scope: str) -> str:
    if not links:
        if status == "workbook_revised_pending_clause_rebind":
            return "workbook_revised_no_qualifying_link"
        if status == "basis_catalog_only":
            return "catalog_only_no_qualifying_link"
        if target_scope == "knowledge-extra-proposed-non-target":
            return "non_target_scope_review_no_qualifying_link"
        return "no_qualifying_link"

    decisions = [item["review"]["decision"] for item in links]
    if decisions and all(decision == "rejected" for decision in decisions):
        return "rejected_links_need_rebind"
    if any(decision in {"missing", "pending"} for decision in decisions):
        return "link_review_pending"
    if any(item["reasonCodes"] for item in links):
        return "link_chain_incomplete"
    return "link_chain_needs_manual_gate"


def next_action(group: str, hazard_review_decision: str, target_scope: str) -> str:
    if group == "workbook_revised_no_qualifying_link":
        return "按修订后隐患对象核验现行法规/版本和精确条款，建立 direct/fallback 关联；保持 proposed。"
    if group == "catalog_only_no_qualifying_link":
        return "先确认法规身份、版本效力和官方原文，再建立条款及 direct/fallback 关联；保持 proposed。"
    if group == "non_target_scope_review_no_qualifying_link":
        return "先完成目标外范围与隐患对象复核，再决定是否保留并绑定条款；保持 proposed。"
    if group == "rejected_links_need_rebind":
        return "按 rejected reasonCodes 修订隐患/条款对应关系，必要时拆分对象，再建立新的 direct/fallback 关联；保留旧拒绝记录。"
    if group == "link_review_pending":
        return "完成关联适用性审核、上下文哈希和理由记录；证据链完整前保持 proposed。"
    return "逐项复核法规身份、版本、条款原文、原始证据和适用性后再评估转正。"


def build_records(as_of_text: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    as_of = date.fromisoformat(as_of_text)
    hazards = load_dir("hazards")
    links = load_dir("links")
    clauses = load_dir("clauses")
    laws = load_dir("laws")
    law_versions = load_dir("law-versions")
    evidence = load_dir("evidence")
    hazard_reviews = load_dir("reviews/hazards")
    link_reviews = load_dir("reviews/links")
    clause_reviews = load_dir("reviews/clauses")
    law_reviews = load_dir("reviews/laws")
    law_version_reviews = load_dir("reviews/law-versions")
    scope = load_scope()

    proposed = {hid: hazard for hid, hazard in hazards.items() if hazard.get("lifecycle") == "proposed"}
    records: list[dict[str, Any]] = []
    for hazard_id in sorted(proposed):
        hazard = proposed[hazard_id]
        target_scope = scope.get(hazard_id)
        if not target_scope and hazard.get("proposalStatus") == "knowledge_extra_non_target_pending_scope_review":
            target_scope = "knowledge-extra-proposed-non-target"
        target_scope = target_scope or "unmapped"

        hazard_review, hazard_review_reasons = review_snapshot(
            hazard,
            hazard_reviews.get(hazard_id),
            evidence=evidence,
            require_evidence=False,
        )
        hazard_links = [link for link in links.values() if link.get("hazardId") == hazard_id]
        link_records: list[dict[str, Any]] = []
        link_reasons: list[str] = []
        for link in sorted(hazard_links, key=lambda item: str(item.get("id"))):
            summary, reasons = link_snapshot(
                link,
                hazard,
                link_reviews,
                clauses,
                clause_reviews,
                law_versions,
                laws,
                law_version_reviews,
                law_reviews,
                evidence,
                as_of,
            )
            link_records.append(summary)
            link_reasons.extend(reasons)

        group = backlog_group(hazard.get("proposalStatus"), link_records, target_scope)
        reasons = sorted(set(hazard_review_reasons + link_reasons))
        hazard_review_decision = hazard_review.get("decision", "missing")
        if hazard_review_decision == "missing":
            evidence_stage = "hazard_review_missing"
        elif hazard_review_decision == "rejected":
            evidence_stage = "hazard_review_rejected"
        elif "REVIEW_STALE" in hazard_review_reasons:
            evidence_stage = "hazard_review_stale"
        else:
            evidence_stage = "hazard_review_verified"

        records.append(
            {
                "recordType": "candidate",
                "hazardId": hazard_id,
                "title": hazard.get("title"),
                "category": hazard.get("category"),
                "lifecycle": hazard.get("lifecycle"),
                "proposalStatus": hazard.get("proposalStatus"),
                "proposalStage": proposal_stage(hazard.get("proposalStatus")),
                "revisionState": hazard.get("revisionState"),
                "sourceRow": hazard.get("sourceRow"),
                "targetScope": target_scope,
                "backlogGroup": group,
                "evidenceStage": evidence_stage,
                "hazardReview": hazard_review,
                "links": link_records,
                "linkCount": len(link_records),
                "qualifyingLinkCount": sum(1 for item in link_records if item["qualifyingRole"]),
                "reasonCodes": reasons,
                "safeToPromoteNow": False,
                "nextAction": next_action(group, hazard_review_decision, target_scope),
            }
        )

    def count(field: str) -> dict[str, int]:
        return dict(sorted(Counter(str(item.get(field)) for item in records).items()))

    cross = Counter((item["backlogGroup"], item["evidenceStage"]) for item in records)
    summary = {
        "candidateCount": len(records),
        "expectedCandidateCount": EXPECTED_PROPOSED,
        "candidateCountMatchesExpected": len(records) == EXPECTED_PROPOSED,
        "targetScopeCounts": count("targetScope"),
        "proposalStatusCounts": count("proposalStatus"),
        "backlogGroupCounts": count("backlogGroup"),
        "evidenceStageCounts": count("evidenceStage"),
        "backlogGroupByEvidenceStage": {
            f"{group}|{stage}": value
            for (group, stage), value in sorted(cross.items())
        },
        "hazardsWithNoLinks": sum(item["linkCount"] == 0 for item in records),
        "hazardsWithRejectedOnlyLinks": sum(item["backlogGroup"] == "rejected_links_need_rebind" for item in records),
        "linksAcrossCandidates": sum(item["linkCount"] for item in records),
        "rejectedLinksAcrossCandidates": sum(
            1
            for item in records
            for link in item["links"]
            if link["review"]["decision"] == "rejected"
        ),
        "safeToPromoteNow": 0,
    }
    metadata = {
        "recordType": "metadata",
        "schemaVersion": 1,
        "asOf": as_of_text,
        "purpose": "PHASE 6 deterministic proposed-hazard evidence backlog; inventory only",
        "source": {
            "knowledgeRoot": "knowledge/",
            "reconciliationMap": "docs/hazard-reconciliation.jsonl",
            "candidateLifecycle": "proposed",
            "evidenceRule": "string evidence IDs are resolved against knowledge/evidence; malformed or unknown refs remain blockers",
        },
        "knowledgeCounts": {
            "laws": len(laws),
            "lawVersions": len(law_versions),
            "clauses": len(clauses),
            "hazards": len(hazards),
            "links": len(links),
            "evidence": len(evidence),
        },
        "summary": summary,
        "integrity": {
            "allRecordsAreProposed": all(item["lifecycle"] == "proposed" for item in records),
            "uniqueHazardIds": len({item["hazardId"] for item in records}) == len(records),
            "allCandidatesHaveExplicitGroup": all(bool(item["backlogGroup"]) for item in records),
            "noPromotionPerformed": all(item["safeToPromoteNow"] is False for item in records),
        },
    }
    return metadata, records


def write_jsonl(path: Path, metadata: dict[str, Any], records: list[dict[str, Any]]) -> None:
    lines = [metadata] + records
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for item in lines),
        encoding="utf-8",
    )


def markdown_table(rows: list[list[str]], headers: list[str]) -> str:
    result = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    result.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(result)


def write_markdown(path: Path, metadata: dict[str, Any], records: list[dict[str, Any]], as_of: str) -> None:
    summary = metadata["summary"]
    lines = [
        "# PHASE 6 候选证据回绑 backlog",
        "",
        f"> 核验基准日：{as_of}。本报告是 `knowledge/` 的机械状态盘点，不是法规现行性结论，也不执行候选转正。",
        "> 所有记录继续保持 `lifecycle=proposed`；正式转正必须另行完成法规身份、适用版本、具体条款、逐字原文、原始证据和适用性审核。",
        "",
        "## 盘点结论",
        "",
        f"- 候选总数：**{summary['candidateCount']}**（目标集内 512，目标集外 7）。",
        f"- **{summary['hazardsWithNoLinks']}** 条没有任何现有关联；**{summary['hazardsWithRejectedOnlyLinks']}** 条只有已拒绝关联（共 {summary['rejectedLinksAcrossCandidates']} 条）。",
        f"- hazard review：缺失 **{summary['evidenceStageCounts'].get('hazard_review_missing', 0)}**，已核验 **{summary['evidenceStageCounts'].get('hazard_review_verified', 0)}**，已拒绝 **{summary['evidenceStageCounts'].get('hazard_review_rejected', 0)}**。",
        "- 本批没有任何记录被标记为可直接转正；本工具没有修改 `knowledge/`、SQLite、私有母库或发布包。",
        "",
        "## 按 backlog 阶段",
        "",
    ]
    rows = [[group, str(value)] for group, value in summary["backlogGroupCounts"].items()]
    lines.append(markdown_table(rows, ["机械分组", "数量"]))
    lines.extend(
        [
            "",
            "分组含义：",
            "",
            "- `workbook_revised_no_qualifying_link`：工作簿修订候选，尚未建立 direct/fallback 关联。",
            "- `catalog_only_no_qualifying_link`：只有法规题录/入口线索，尚未完成身份、版本、条款和关联链。",
            "- `non_target_scope_review_no_qualifying_link`：目标外候选，尚无关联，先做范围复核。",
            "- `rejected_links_need_rebind`：现有关联已被拒绝，须按拒绝原因重绑或拆分对象。",
            "",
            "## 按 proposalStatus",
            "",
        ]
    )
    rows = [[status, str(value)] for status, value in summary["proposalStatusCounts"].items()]
    lines.append(markdown_table(rows, ["proposalStatus", "数量"]))
    lines.extend(["", "## 按 hazard review 状态", ""])
    rows = [[stage, str(value)] for stage, value in summary["evidenceStageCounts"].items()]
    lines.append(markdown_table(rows, ["状态", "数量"]))

    extras = [item for item in records if item["targetScope"] == "knowledge-extra-proposed-non-target"]
    lines.extend(["", "## 目标外 7 条候选", ""])
    lines.append(
        markdown_table(
            [
                [
                    item["hazardId"],
                    (item.get("title") or "").replace("|", "\\|"),
                    item["backlogGroup"],
                    item["evidenceStage"],
                    str(item["linkCount"]),
                ]
                for item in extras
            ],
            ["ID", "标题", "分组", "hazard review", "关联数"],
        )
    )
    lines.extend(
        [
            "",
            "## 下一批执行边界",
            "",
            "1. 优先从 `workbook_revised_no_qualifying_link` 中按法规/设备/作业主题分批，逐项回到官方原文或合法保存的原始证据。",
            "2. 对 `rejected_links_need_rebind` 先读取 `reasonCodes` 和上下文，必要时修订隐患对象或拆分对象；旧 rejected 记录不删除。",
            "3. 每个候选必须同时满足 hazard review、law/lawVersion、clause、evidence、link applicability 的门禁后，才可另开转正批次。",
            "4. 任何条款号、版本效力、替代关系或官方原文无法核准时，保持 `proposed` 并标记 `待核`。",
            "",
            "机器明细见 [`docs/phase6-candidate-backlog.jsonl`](phase6-candidate-backlog.jsonl)。",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", default=DEFAULT_AS_OF)
    parser.add_argument("--jsonl", type=Path, default=ROOT / "docs" / "phase6-candidate-backlog.jsonl")
    parser.add_argument("--markdown", type=Path, default=ROOT / "docs" / "PHASE6_CANDIDATE_BACKLOG.md")
    args = parser.parse_args()
    metadata, records = build_records(args.as_of)
    write_jsonl(args.jsonl, metadata, records)
    write_markdown(args.markdown, metadata, records, args.as_of)
    print(json.dumps(metadata["summary"], ensure_ascii=False, sort_keys=True))
    return 0 if metadata["integrity"]["allRecordsAreProposed"] and metadata["summary"]["candidateCountMatchesExpected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
