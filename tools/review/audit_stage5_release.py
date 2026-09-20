# -*- coding: utf-8 -*-
"""Audit the Stage 5 public projection and its delivery invariants.

The script is read-only with respect to knowledge/, source/ and publication/.
It compares the Stage 4 and Stage 5 public packages, verifies the exact
stable-ID display table, checks the two approved maintenance sentences, and
writes only external review material supplied through --out-dir.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "v4"))
sys.path.insert(0, str(ROOT / "tools" / "review"))
from presentation import (  # noqa: E402
    APPROVED_MAINTENANCE_TEXTS,
    CATEGORY_ALIASES,
    NOTE_DATE_PREFIX,
    STABLE_ID_CATEGORY_OVERRIDES,
    project_hazard,
    project_note,
    searchable,
)
import audit_public_taxonomy as taxonomy  # noqa: E402


EXPECTED_COUNTS = {"hazards": 1716, "laws": 58, "lawVersions": 58, "clauses": 1302, "links": 1824}
EXPECTED_NEW_SENTENCES = {
    NOTE_DATE_PREFIX + "修订：原标题为条款原文片段或存在文字损坏，语义不通且无法作为现场隐患表述；此处依其原描述与现有依据改写为可判定的现场事实，未改变依据本身。",
    NOTE_DATE_PREFIX + "修订：原整改措施已改写为可执行动作。",
}
PROJECTION_FIELDS = {"displayCategory", "sceneTags", "noteSegments", "businessNote", "maintenanceNote"}
RAW_FIELDS = (
    "title", "description", "measures", "conditions", "note", "category", "places",
    "aliases", "keywords", "mode", "lifecycle",
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def normalized_source_value(source: dict[str, Any], field: str) -> Any:
    value = source.get(field)
    if field == "conditions":
        return "" if value is None else value
    if field in {"places", "aliases", "keywords", "basisRefs"}:
        return value or []
    return value if value is not None else ""


def row_maps(public: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    return (
        public["hazards"],
        {row["id"]: row for row in public["searchIndex"]},
    )


def category_counts(search_rows: dict[str, dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(row.get("displayCategory", "") for row in search_rows.values()).items()))


def reason_for(target: str) -> str:
    return f"任务书 T5.1 指定稳定编号的导航展示主题为“{target}”；仅改变 displayCategory，保留原 category、事实字段与依据关联。"


def build_report(new_bundle: Path, old_bundle: Path, knowledge_root: Path, argv: list[str]) -> dict[str, Any]:
    new = taxonomy.load_public_bundle(new_bundle)
    old = taxonomy.load_public_bundle(old_bundle)
    source = taxonomy.load_knowledge_source(knowledge_root)
    new_hazards, new_search = row_maps(new)
    old_hazards, old_search = row_maps(old)
    source_hazards = source["hazards"]

    override_rows: list[dict[str, Any]] = []
    missing_override_ids: list[str] = []
    override_projection_errors: list[str] = []
    for hazard_id, target in sorted(STABLE_ID_CATEGORY_OVERRIDES.items()):
        src = source_hazards.get(hazard_id)
        row = new_hazards.get(hazard_id)
        index = new_search.get(hazard_id)
        if not src or not row or not index:
            missing_override_ids.append(hazard_id)
            continue
        expected = project_hazard(src, hazard_id=hazard_id)
        if row.get("displayCategory") != target or index.get("displayCategory") != target:
            override_projection_errors.append(hazard_id)
        override_rows.append({
            "id": hazard_id,
            "originalCategory": src.get("category", ""),
            "oldDisplayCategory": old_search.get(hazard_id, {}).get("displayCategory", ""),
            "displayCategory": target,
            "title": src.get("title", ""),
            "places": list(dict.fromkeys(src.get("places") or [])),
            "overrideReason": reason_for(target),
        })

    raw_mismatches: list[dict[str, str]] = []
    projection_mismatches: list[str] = []
    for hazard_id, row in sorted(new_hazards.items()):
        src = source_hazards.get(hazard_id)
        if not src:
            raw_mismatches.append({"id": hazard_id, "field": "missing knowledge source"})
            continue
        expected_projection = project_hazard(src, hazard_id=hazard_id)
        if any(row.get(field) != expected_projection[field] for field in PROJECTION_FIELDS):
            projection_mismatches.append(hazard_id)
        for field in RAW_FIELDS:
            if row.get(field) != normalized_source_value(src, field):
                raw_mismatches.append({"id": hazard_id, "field": field})

    display_changes: list[dict[str, str]] = []
    unexpected_display_changes: list[str] = []
    for hazard_id, new_row in sorted(new_search.items()):
        old_value = old_search.get(hazard_id, {}).get("displayCategory", "")
        new_value = new_row.get("displayCategory", "")
        if old_value == new_value:
            continue
        source_category = source_hazards.get(hazard_id, {}).get("category", "")
        expected_reason = "stable-ID override" if hazard_id in STABLE_ID_CATEGORY_OVERRIDES else "专项安全与EHS display alias"
        if hazard_id not in STABLE_ID_CATEGORY_OVERRIDES and source_category != "专项安全与EHS":
            unexpected_display_changes.append(hazard_id)
        display_changes.append({
            "id": hazard_id,
            "old": old_value,
            "new": new_value,
            "reason": expected_reason,
        })

    note_projection_errors: list[str] = []
    maintenance_leaks: list[dict[str, Any]] = []
    maintenance_near_match_hits: list[dict[str, Any]] = []
    for hazard_id, row in sorted(new_hazards.items()):
        src = source_hazards[hazard_id]
        expected = project_note(src.get("note"))
        if any(row.get(field) != expected[field] for field in ("noteSegments", "businessNote", "maintenanceNote")):
            note_projection_errors.append(hazard_id)
        search_text = new_search[hazard_id].get("searchText", "")
        for phrase in APPROVED_MAINTENANCE_TEXTS:
            if searchable([phrase]) not in search_text:
                continue
            if phrase in expected["businessNote"]:
                maintenance_leaks.append({"id": hazard_id, "query": phrase})
            else:
                maintenance_near_match_hits.append({"id": hazard_id, "query": phrase})

    business_query = "原 conditions 字段记录的引用依据"
    normalized_business_query = searchable([business_query])
    old_business_ids = sorted(hid for hid, row in old_search.items() if normalized_business_query in row.get("searchText", ""))
    new_business_ids = sorted(hid for hid, row in new_search.items() if normalized_business_query in row.get("searchText", ""))
    near_match = next(iter(EXPECTED_NEW_SENTENCES)).rstrip("。")
    near_match_projection = project_note(near_match)

    category_search_mismatches = sorted(
        hazard_id for hazard_id, row in new_search.items()
        if new_hazards.get(hazard_id, {}).get("displayCategory") != row.get("displayCategory")
    )
    taxonomy_categories = set(new["taxonomy"].get("displayCategories", new["taxonomy"].get("categories", [])))
    display_categories = {row.get("displayCategory", "") for row in new_search.values()}

    new_clause_map = {key: value for key, value in new["clauses"].items()}
    old_clause_map = {key: value for key, value in old["clauses"].items()}
    new_law_map = {row["id"]: row for row in new["lawIndex"]}
    old_law_map = {row["id"]: row for row in old["lawIndex"]}
    derived_fields = ("status", "publishable", "checked", "basisRefs")
    derived_mismatches = [
        {"id": hazard_id, "field": field}
        for hazard_id in new_hazards
        for field in derived_fields
        if new_hazards[hazard_id].get(field) != old_hazards.get(hazard_id, {}).get(field)
    ]

    counts = new["release"].get("counts", {})
    return {
        "schemaVersion": "safety-stage5-classification-maintenance-audit-v1",
        "scope": {
            "reviewOnly": True,
            "sourceKnowledgePublicationUnchanged": True,
            "stableOverridesAreExactTaskScope": True,
            "rawCategoryIsPreserved": True,
            "candidateAndUnlistedRecordsUntouched": True,
        },
        "source": {
            "newBundle": str(new_bundle.resolve()),
            "oldBundle": str(old_bundle.resolve()),
            "knowledgeRoot": str(knowledge_root.resolve()),
            "newReleaseHash": new["release"].get("releaseHash", ""),
            "oldReleaseHash": old["release"].get("releaseHash", ""),
            "newDataVersion": new["manifest"].get("dataVersion", ""),
            "command": " ".join(argv),
        },
        "counts": {
            "manifest": counts,
            "expected": EXPECTED_COUNTS,
            "matchesExpected": counts == EXPECTED_COUNTS,
            "oldDisplayCategoryCounts": category_counts(old_search),
            "newDisplayCategoryCounts": category_counts(new_search),
            "stableIdOverrideCount": len(STABLE_ID_CATEGORY_OVERRIDES),
            "stableIdRowsAudited": len(override_rows),
            "displayCategoryChangesFromStage4": len(display_changes),
            "aliasDisplayChanges": sum(item["reason"] == "专项安全与EHS display alias" for item in display_changes),
            "maintenanceRecords": sum(bool(row.get("maintenanceNote", "").strip()) for row in new_hazards.values()),
            "maintenanceSegments": sum(sum(segment.get("kind") == "maintenance" for segment in row.get("noteSegments", [])) for row in new_hazards.values()),
        },
        "stableIdAudit": {
            "missingIds": missing_override_ids,
            "projectionErrors": override_projection_errors,
            "unexpectedDisplayChanges": unexpected_display_changes,
            "rows": override_rows,
            "unlistedControl": {
                "id": "H_47B0A90180C24A42AFA38767B9",
                "rawCategory": source_hazards.get("H_47B0A90180C24A42AFA38767B9", {}).get("category", ""),
                "stage5DisplayCategory": new_search.get("H_47B0A90180C24A42AFA38767B9", {}).get("displayCategory", ""),
                "overridePresent": "H_47B0A90180C24A42AFA38767B9" in STABLE_ID_CATEGORY_OVERRIDES,
            },
            "alias": {"专项安全与EHS": CATEGORY_ALIASES.get("专项安全与EHS")},
        },
        "projectionIntegrity": {
            "rawMismatches": raw_mismatches,
            "derivedMismatchesStage4": derived_mismatches,
            "presentationMismatches": projection_mismatches,
            "noteProjectionMismatches": note_projection_errors,
            "searchIndexAndTaxonomyDisplayCategoryMismatches": category_search_mismatches,
            "taxonomyCategoriesEqualDisplayCategories": taxonomy_categories == display_categories,
            "taxonomyOnlyCategories": sorted(taxonomy_categories - display_categories),
            "displayOnlyCategories": sorted(display_categories - taxonomy_categories),
            "idSetEqualStage4": set(new_hazards) == set(old_hazards),
            "idSetEqualKnowledgePublic": set(new_hazards) <= set(source_hazards),
            "clauseMappingEqualStage4": new_clause_map == old_clause_map,
            "lawIndexEqualStage4": new_law_map == old_law_map,
            "basisRefsEqualStage4": all(new_hazards[key].get("basisRefs") == old_hazards[key].get("basisRefs") for key in new_hazards),
        },
        "maintenanceAudit": {
            "approvedSentences": list(APPROVED_MAINTENANCE_TEXTS),
            "newExactSentencesPresent": EXPECTED_NEW_SENTENCES <= set(APPROVED_MAINTENANCE_TEXTS),
            "nearMatchExample": near_match,
            "nearMatchMaintenanceNote": near_match_projection["maintenanceNote"],
            "nearMatchRetainedAsBusiness": near_match_projection["businessNote"] == near_match,
            "maintenanceSearchLeaks": maintenance_leaks,
            "maintenanceNearMatchSearchHits": maintenance_near_match_hits,
            "businessQuery": {
                "query": business_query,
                "stage4Count": len(old_business_ids),
                "stage5Count": len(new_business_ids),
                "changedIds": sorted(set(old_business_ids) ^ set(new_business_ids)),
            },
            "sourceNotesUnchanged": all(new_hazards[key].get("note") == old_hazards[key].get("note") for key in new_hazards),
        },
        "boundary": [
            "稳定编号清单以任务书为闭集；未列编号不因标题相似自动扩展。",
            "专项安全与EHS 仅增加综合安全展示别名；原 category 保留。",
            "候选、未批准维护线索、PHASE/版本治理等未批准内容不隐藏，仍按原边界保留并供审查。",
            "本审计不修改 knowledge、source/publication 或正式 current 发布目录；外部包仅用于本地预览交付。",
        ],
    }


def md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def markdown_report(report: dict[str, Any]) -> str:
    counts = report["counts"]
    integrity = report["projectionIntegrity"]
    maintenance = report["maintenanceAudit"]
    lines = [
        "# 阶段 5 最终分类展示与备注分流验收",
        "",
        "本报告是只读外部交付审计：稳定编号展示覆盖和两个批准维护句式均按任务书闭集执行，不写回 knowledge、source/publication 或正式 current 目录。候选与未批准线索仍保留，不作法规适用性或现场事实推断。",
        "",
        f"- 阶段 5 包：`{report['source']['newBundle']}`",
        f"- 阶段 4 包：`{report['source']['oldBundle']}`",
        f"- `dataVersion`：`{report['source']['newDataVersion']}`；`releaseHash`：`{report['source']['newReleaseHash']}`",
        f"- 计数：隐患 {counts['manifest'].get('hazards')} / 法规 {counts['manifest'].get('laws')} / 条款 {counts['manifest'].get('clauses')} / 关联 {counts['manifest'].get('links')}；期望一致：{'是' if counts['matchesExpected'] else '否'}",
        f"- 展示主题分布变化：阶段 4 {len(counts['oldDisplayCategoryCounts'])} 项 → 阶段 5 {len(counts['newDisplayCategoryCounts'])} 项；稳定编号改变 {counts['displayCategoryChangesFromStage4']} 条，其中别名变化 {counts['aliasDisplayChanges']} 条。",
        "",
        "## 稳定编号覆盖表",
        "",
        "覆盖原因统一为任务书指定的导航展示投影；原始 category、标题、场所、条件、措施、备注、条款和关联关系均保留。完整逐条表如下：",
        "",
        "| 稳定 ID | 原 category | 阶段 4 展示 | 阶段 5 展示 | 标题 | 覆盖原因 |",
        "|---|---|---|---|---|---|",
    ]
    for row in report["stableIdAudit"]["rows"]:
        lines.append("| " + " | ".join(md_escape(row[key]) for key in ("id", "originalCategory", "oldDisplayCategory", "displayCategory", "title", "overrideReason")) + " |")
    lines.extend([
        "",
        f"- 覆盖表数量：{counts['stableIdOverrideCount']}；审计到位：{counts['stableIdRowsAudited']}；缺失 ID：{len(report['stableIdAudit']['missingIds'])}；投影错误：{len(report['stableIdAudit']['projectionErrors'])}；额外展示变化：{len(report['stableIdAudit']['unexpectedDisplayChanges'])}。",
        f"- 别名：`专项安全与EHS` → `{report['stableIdAudit']['alias']['专项安全与EHS']}`；控制 ID `H_47B0A90180C24A42AFA38767B9` 的展示仍为 `{report['stableIdAudit']['unlistedControl']['stage5DisplayCategory']}`。",
        "",
        "## 原值、索引和依据不变性",
        "",
        f"- 隐患稳定 ID 集合与阶段 4 一致：{'是' if integrity['idSetEqualStage4'] else '否'}；公开 ID 均可追溯到 knowledge：{'是' if integrity['idSetEqualKnowledgePublic'] else '否'}。",
        f"- 原始字段不一致：{len(integrity['rawMismatches'])}；阶段 4/5 派生字段不一致：{len(integrity['derivedMismatchesStage4'])}；展示投影不一致：{len(integrity['presentationMismatches'])}；备注投影不一致：{len(integrity['noteProjectionMismatches'])}。",
        f"- 搜索索引与隐患分片展示主题一致：{'是' if not integrity['searchIndexAndTaxonomyDisplayCategoryMismatches'] else '否'}；taxonomy 与展示主题集合一致：{'是' if integrity['taxonomyCategoriesEqualDisplayCategories'] else '否'}。",
        f"- 条款映射与阶段 4 一致：{'是' if integrity['clauseMappingEqualStage4'] else '否'}；法规索引一致：{'是' if integrity['lawIndexEqualStage4'] else '否'}；basisRefs 一致：{'是' if integrity['basisRefsEqualStage4'] else '否'}。",
        "",
        "## 维护句式与搜索边界",
        "",
        f"- 新增两个完整句式均进入批准列表：{'是' if maintenance['newExactSentencesPresent'] else '否'}；维护搜索泄漏：{len(maintenance['maintenanceSearchLeaks'])}；近似句因搜索规范化保留为业务命中：{len(maintenance['maintenanceNearMatchSearchHits'])}。",
        f"- 近似句示例（去掉末句号）未分流 maintenance：{'是' if maintenance['nearMatchMaintenanceNote'] == '' and maintenance['nearMatchRetainedAsBusiness'] else '否'}。",
        f"- 业务查询“{maintenance['businessQuery']['query']}”：阶段 4 {maintenance['businessQuery']['stage4Count']} 条 → 阶段 5 {maintenance['businessQuery']['stage5Count']} 条；变化 ID：{len(maintenance['businessQuery']['changedIds'])}。",
        f"- 原始 note 保持不变：{'是' if maintenance['sourceNotesUnchanged'] else '否'}；维护记录数 {counts['maintenanceRecords']}，维护片段数 {counts['maintenanceSegments']}。",
        "",
        "## 边界与回滚",
        "",
        "- 本包是外部本地预览交付物；回滚方法为删除或改名 `luna-stage5/public-release/`，并改用阶段 4 的 `public-release/`，不触碰源库。",
        "- 未列稳定编号、候选 inventory、未批准维护/版本治理线索均不在本阶段改变；若需继续处理，应另立任务并逐条审定。",
        "- 完整机器可读结果见同目录 `classification-coverage-stage5.json`。",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--old-bundle", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--knowledge-root", default=str(ROOT / "knowledge"))
    args = parser.parse_args()
    report = build_report(Path(args.bundle).resolve(), Path(args.old_bundle).resolve(), Path(args.knowledge_root).resolve(), [sys.executable, *sys.argv])
    out_dir = Path(args.out_dir).resolve()
    write_json(out_dir / "classification-coverage-stage5.json", report)
    (out_dir / "classification-coverage-stage5.md").write_text(markdown_report(report), encoding="utf-8", newline="\n")
    print(json.dumps({
        "counts": report["counts"],
        "rawMismatches": len(report["projectionIntegrity"]["rawMismatches"]),
        "presentationMismatches": len(report["projectionIntegrity"]["presentationMismatches"]),
        "maintenanceLeaks": len(report["maintenanceAudit"]["maintenanceSearchLeaks"]),
        "maintenanceNearMatchHits": len(report["maintenanceAudit"]["maintenanceNearMatchSearchHits"]),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
