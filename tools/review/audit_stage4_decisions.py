# -*- coding: utf-8 -*-
"""Generate Stage 4 classification and residual-note decision material.

This is a read-only candidate finder.  It never writes knowledge, publication,
taxonomy, or public records and never infers legal applicability.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "review"))
sys.path.insert(0, str(ROOT / "tools" / "v4"))
import audit_public_taxonomy as taxonomy  # noqa: E402
from presentation import scene_tags  # noqa: E402

GENERIC_CATEGORIES = ("设备设施", "安全管理", "专项安全与EHS")
COMPOSITE_MARKERS = ("与", "及", "/", "、")
DOMAIN_RE = re.compile(r"消防|电气|用电|燃气|机械|粉尘|危险化学品|危化品|有限空间|高处|防坠落|职业卫生|危险废物|应急|特种设备|场车|叉车")
MANAGEMENT_RE = re.compile(r"管理|制度|责任|培训|教育|检查|排查|台账|记录|维护|保养|检修|巡检|方案|预案|计划|许可|作业证")
GAS_RE = re.compile(r"燃气|天然气|液化气")
ELECTRIC_RE = re.compile(r"电气|用电|配电|漏电|接地")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def detail_record(row: dict[str, Any], public: dict[str, Any], reason: str = "") -> dict[str, Any]:
    clauses = public["clauses"]
    laws = {law["id"]: law for law in public["lawIndex"]}
    basis = []
    for ref in row.get("basisRefs") or []:
        clause = clauses.get(ref.get("clauseId"), {})
        law = laws.get(clause.get("lawId"), {})
        quote = clause.get("quote", "")
        basis.append({
            "role": ref.get("role", ""),
            "clauseId": ref.get("clauseId", ""),
            "lawVersionId": clause.get("lawId", ""),
            "lawName": law.get("name", ""),
            "article": clause.get("article", ""),
            "quoteSummary": quote[:240],
        })
    title = row.get("title", "")
    places = list(dict.fromkeys(row.get("places") or []))
    clues = scene_tags([title, *places])
    return {
        "id": row.get("id", ""),
        "originalCategory": row.get("category", ""),
        "displayCategory": row.get("displayCategory", ""),
        "title": title,
        "places": places,
        "conditions": row.get("conditions", ""),
        "basisSummary": basis,
        "suggestedDisplayTheme": row.get("displayCategory") or None,
        "suggestedSceneCluesFromApprovedFragments": clues,
        "suggestedScene": clues[0] if clues else "未细分场景",
        "evidence": {
            "source": f"knowledge/hazards/{row.get('id', '')}.json",
            "publicProjection": "public-release/data/hazards/<shard>.json + search-index.json",
            "basis": "当前公开包 basisRefs / clauses / law-index 的摘要，仅作追溯，不作法律判断。",
        },
        "uncertainty": [
            "展示主题/场景仅为候选线索，未写回分类或 taxonomy。",
            "conditions 与 basisSummary 仅用于审定上下文，不证明现场事实或法规适用性。",
            reason or "需架构师逐条审定。",
        ],
    }


def candidate_reason(row: dict[str, Any]) -> list[str]:
    category = row.get("category", "")
    text = " ".join([row.get("title", ""), *(row.get("keywords") or [])])
    reasons = []
    if category in GENERIC_CATEGORIES:
        reasons.append("泛化类别全量待审")
        if DOMAIN_RE.search(text):
            reasons.append("标题/关键词含具体专业线索")
        if category == "设备设施" and MANAGEMENT_RE.search(text):
            reasons.append("设备设施类别含管理事项线索")
    if any(marker in category for marker in COMPOSITE_MARKERS):
        reasons.append("组合类别需逐条审定")
        has_gas = bool(GAS_RE.search(row.get("title", "")))
        has_electric = bool(ELECTRIC_RE.search(row.get("title", "")))
        if category == "燃气与电气安全" and has_gas != has_electric:
            reasons.append("组合类别标题只呈现一侧专业线索")
    return reasons


def build_report(bundle: Path, knowledge_root: Path) -> dict[str, Any]:
    public = taxonomy.load_public_bundle(bundle)
    knowledge = taxonomy.load_knowledge_source(knowledge_root)
    rows = public["searchIndex"]
    shard_rows = public["hazards"]
    source_rows = knowledge["hazards"]

    unmapped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    generic_review: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    suspected: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    composite_review: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)

    for index_row in rows:
        row = shard_rows[index_row["id"]]
        source_row = source_rows.get(index_row["id"], {})
        merged = {**index_row, **row}
        # Keep source fields explicit for the decision record; the public row is
        # only the auditable projection used for counting and basis tracing.
        merged["keywords"] = source_row.get("keywords") or index_row.get("keywords") or []
        merged["category"] = source_row.get("category", index_row.get("category", ""))
        merged["places"] = source_row.get("places") or index_row.get("places") or []
        detail = detail_record(merged, public)
        for place in dict.fromkeys(merged["places"]):
            if not scene_tags([place]):
                unmapped[place].append(detail)

        reasons = candidate_reason(merged)
        if merged["category"] in GENERIC_CATEGORIES:
            generic_review[merged["category"]].append({**detail, "reviewReasons": reasons})
        if any(marker in merged["category"] for marker in COMPOSITE_MARKERS):
            composite_review[merged["category"]].append({**detail, "reviewReasons": reasons})
        for reason in reasons:
            if "一侧专业线索" in reason or "具体专业线索" in reason or "管理事项线索" in reason:
                suspected[reason].append({**detail, "reviewReasons": reasons})

    explicit_id = "H_133DEA3AE07CE30E3CA5CBF4FF_1"
    explicit = None
    if explicit_id in shard_rows:
        explicit = detail_record({**public["searchIndex"][[row["id"] for row in rows].index(explicit_id)], **shard_rows[explicit_id]}, public,
                                 "任务书明确点名，需单独审定设备设施/管理主题边界；不提供目标分类。")

    return {
        "schemaVersion": "safety-stage4-decision-material-v1",
        "scope": {
            "readOnly": True,
            "noClassificationApplied": True,
            "noLegalJudgment": True,
            "publicPackageIsCountingSource": True,
            "candidateRulesAreDiscoveryOnly": True,
        },
        "source": {
            "bundle": str(bundle.resolve()),
            "knowledgeRoot": str(knowledge_root.resolve()),
            "releaseHash": public["release"].get("releaseHash", ""),
            "asOf": public["release"].get("asOf", ""),
            "dataVersion": public["manifest"].get("dataVersion", ""),
        },
        "counts": {
            "publicHazards": len(rows),
            "unmappedPlaceValues": len(unmapped),
            "genericCategoryCandidates": sum(len(items) for items in generic_review.values()),
            "compositeCategoryCandidates": sum(len(items) for items in composite_review.values()),
            "suspectedWrongClassificationCandidates": sum(len(items) for items in suspected.values()),
        },
        "unmappedPlaceValues": [
            {"value": value, "publicRecordCount": len(items), "records": items}
            for value, items in sorted(unmapped.items(), key=lambda item: (-len(item[1]), item[0]))
        ],
        "genericCategoryReview": {
            value: {"publicRecordCount": len(items), "records": items}
            for value, items in sorted(generic_review.items())
        },
        "compositeCategoryReview": {
            value: {"publicRecordCount": len(items), "records": items}
            for value, items in sorted(composite_review.items())
        },
        "suspectedWrongClassification": {
            reason: {"candidateCount": len(items), "records": items}
            for reason, items in sorted(suspected.items())
        },
        "representativeExamples": {
            reason: items[:5] for reason, items in sorted(suspected.items())
        },
        "explicitReviewTarget": explicit,
        "decisionBoundary": [
            "未映射场所值逐项保留原文和完整候选记录；建议场景只来自已批准展示片段的线索，不自动应用。",
            "泛化/组合类别输出完整候选清单与代表例，不合并、不改主题、不把未细分场景视为错误。",
            "conditions、basisSummary 和证据路径仅用于追溯；不据此推断法规效力、适用性、现场事实或合规结论。",
        ],
    }


def markdown_report(report: dict[str, Any]) -> str:
    counts = report["counts"]
    lines = [
        "# 阶段 4 分类与剩余备注决策清单",
        "",
        "本清单是只读候选材料：不执行重分类、合并、删除或法规适用性判断。完整 ID、标题、places、conditions、依据摘要、建议线索和不确定性见 JSON。",
        "",
        f"- 公开包：`{report['source']['bundle']}`",
        f"- `asOf`：`{report['source']['asOf']}`；`releaseHash`：`{report['source']['releaseHash']}`",
        f"- 公开隐患：{counts['publicHazards']}；未映射场所值：{counts['unmappedPlaceValues']}；泛化类别候选：{counts['genericCategoryCandidates']}；组合类别记录：{counts['compositeCategoryCandidates']}；疑似错分线索：{counts['suspectedWrongClassificationCandidates']}",
        "",
        "## 未映射原始场所值（全量）",
        "",
        "每个值及其完整候选记录均在 JSON 的 `unmappedPlaceValues`；此处列出数量和代表 ID。",
        "",
        "| 原始场所值 | 公开记录数 | 代表 ID |",
        "|---|---:|---|",
    ]
    for entry in report["unmappedPlaceValues"]:
        ids = "、".join(record["id"] for record in entry["records"][:5])
        lines.append(f"| {entry['value']} | {entry['publicRecordCount']} | {ids} |")
    lines.extend(["", "## 泛化/交叉类别决策材料", ""])
    for name, group in report["genericCategoryReview"].items():
        lines.append(f"- `{name}`：{group['publicRecordCount']} 条，全量候选见 JSON；不提供目标分类。")
    for name, group in report["compositeCategoryReview"].items():
        lines.append(f"- 组合类别 `{name}`：{group['publicRecordCount']} 条，全量候选见 JSON；只做逐条审定入口。")
    lines.extend(["", "## 疑似错分线索与代表例", ""])
    for reason, group in report["suspectedWrongClassification"].items():
        examples = "、".join(record["id"] for record in group["records"][:5])
        lines.append(f"- {reason}：{group['candidateCount']} 条；代表 ID：{examples}。")
    lines.extend(["", "## 明确点名记录", ""])
    target = report.get("explicitReviewTarget")
    if target:
        lines.append(f"- `{target['id']}`：原主题 `{target['originalCategory']}`，标题“{target['title']}”，原场所 `{ '、'.join(target['places']) }`；任务书要求单独审定，未给出目标分类。")
    else:
        lines.append("- 目标 ID 未出现在当前公开包，需保留该缺口，不作推断。")
    lines.extend(["", "## 决策边界", "", *[f"- {item}" for item in report["decisionBoundary"]], ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--knowledge-root", default=str(ROOT / "knowledge"))
    args = parser.parse_args()
    report = build_report(Path(args.bundle).resolve(), Path(args.knowledge_root).resolve())
    out_dir = Path(args.out_dir).resolve()
    write_json(out_dir / "classification-decision-stage4.json", report)
    (out_dir / "classification-decision-stage4.md").write_text(markdown_report(report), encoding="utf-8", newline="\n")
    print(json.dumps(report["counts"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
