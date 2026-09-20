# -*- coding: utf-8 -*-
"""Generate a read-only, traceable audit of the public taxonomy.

The public release is the counting source.  Knowledge files are read only to
confirm that the public projection keeps the source labels and does not mix in
candidate inventory.  No classification, entity, or source file is written.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BUNDLE = ROOT / "source" / "releases" / "current"
FLAG_ORDER = ("可能近义", "维度混合", "疑似错分", "信息不足", "层级边界待审")

CATEGORY_NEAR_PAIRS = (
    ("电气安全", "用电安全"),
    ("机械与设备安全", "机械设备安全"),
    ("安全教育培训", "安全教育"),
)
GENERIC_CATEGORIES = ("设备设施", "专项安全与EHS")
COMPOSITE_CATEGORY_MARKERS = ("与", "及", "/", "、")
DEPARTMENT_LEVELS = ("部门规章", "部门规章（部令）")
NATIONAL_STANDARD_LEVELS = (
    "国家标准",
    "强制性国家标准",
    "强制性国家职业卫生标准",
    "推荐性国家标准",
    "工程建设国家标准",
)
PLACE_GENERIC_VALUES = {
    "通用场所",
    "生产经营单位",
    "生产车间",
    "仓库",
    "工贸企业",
    "工业企业",
    "作业场所",
    "特种设备",
}
REGION_RE = re.compile(r"全国|江苏|南京|省行政区域|市行政区域")
APPLICABILITY_RE = re.compile(
    r"依法|生产经营单位|相关|管理场景|作业活动|设备设施|行政区域|岗位|责任|设置场景"
)
MANAGEMENT_RE = re.compile(
    r"管理|制度|责任|培训|教育|检查|排查|台账|记录|维护|保养|检修|巡检|方案|预案|计划|许可|作业证"
)
SPECIFIC_DOMAIN_RE = re.compile(
    r"消防|电气|用电|燃气|机械|设备|粉尘|危险化学品|危化品|有限空间|高处|防坠落|职业卫生|危险废物|应急"
)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(value, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def bundle_path(bundle: Path, relative: str) -> Path:
    root = bundle.resolve()
    path = (bundle / relative).resolve()
    if root != path and root not in path.parents:
        raise ValueError(f"公开包路径越界：{relative}")
    return path


def load_shards(bundle: Path, manifest: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for shard in manifest.get(key, []):
        payload = read_json(bundle_path(bundle, shard["url"]))
        for record in payload.get("records", []):
            record_id = record.get("id")
            if not record_id:
                raise ValueError(f"{key} 存在无稳定编号记录：{shard.get('id')}")
            if record_id in records:
                raise ValueError(f"{key} 存在重复稳定编号：{record_id}")
            records[record_id] = record
    return records


def load_public_bundle(bundle: Path) -> dict[str, Any]:
    release = read_json(bundle_path(bundle, "release.json"))
    manifest = read_json(bundle_path(bundle, "data/manifest.json"))
    search_index = read_json(bundle_path(bundle, manifest["files"]["searchIndex"]))
    law_index = read_json(bundle_path(bundle, manifest["files"]["lawIndex"]))
    taxonomy = read_json(bundle_path(bundle, manifest["files"]["taxonomy"]))
    hazards = load_shards(bundle, manifest, "hazardShards")
    clauses = load_shards(bundle, manifest, "clauseShards")

    search_ids = {row["id"] for row in search_index}
    if search_ids != set(hazards):
        raise ValueError("search-index 与隐患分片的稳定编号集合不一致")
    if len(law_index) != len({row["id"] for row in law_index}):
        raise ValueError("法规索引存在重复稳定编号")

    return {
        "release": release,
        "manifest": manifest,
        "searchIndex": search_index,
        "lawIndex": law_index,
        "taxonomy": taxonomy,
        "hazards": hazards,
        "clauses": clauses,
    }


def load_knowledge_source(knowledge_root: Path) -> dict[str, Any]:
    hazards = {
        path.stem: read_json(path)
        for path in sorted((knowledge_root / "hazards").glob("*.json"))
    }
    law_versions = {
        path.stem: read_json(path)
        for path in sorted((knowledge_root / "law-versions").glob("*.json"))
    }
    return {
        "manifest": read_json(knowledge_root / "manifest.json"),
        "hazards": hazards,
        "lawVersions": law_versions,
    }


def git_value(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError:
        return "不可用"
    return result.stdout.strip() if result.returncode == 0 else "不可用"


def stable_ids(rows: Iterable[dict[str, Any]], limit: int | None = None) -> list[str]:
    values = sorted({str(row.get("id", "")) for row in rows if row.get("id")})
    return values if limit is None else values[:limit]


def ordered_flags(flags: Iterable[str]) -> list[str]:
    values = set(flags)
    return [flag for flag in FLAG_ORDER if flag in values]


def category_review(value: str) -> tuple[list[str], list[str]]:
    flags: list[str] = []
    notes: list[str] = []
    if any(value in pair for pair in CATEGORY_NEAR_PAIRS):
        flags.append("可能近义")
        notes.append("与同一审查组内的类别存在词面接近，需人工区分主题边界；不作自动合并。")
    if value in GENERIC_CATEGORIES:
        flags.extend(("维度混合", "信息不足"))
        notes.append("属于泛化类别，可能同时承载设备、作业、管理或专业主题，需逐条审定。")
    if any(marker in value for marker in COMPOSITE_CATEGORY_MARKERS):
        flags.append("维度混合")
        notes.append("类别名称组合了两个或多个主题/专业维度，需逐条检查，不作整体归并。")
    return ordered_flags(flags), notes


def place_review(value: str) -> tuple[list[str], list[str]]:
    flags: list[str] = []
    notes: list[str] = []
    if REGION_RE.search(value):
        flags.append("维度混合")
        notes.append("场所原值包含地域范围，应与地域筛选维度分开审定。")
    if len(value) > 20 or APPLICABILITY_RE.search(value):
        flags.append("维度混合")
        notes.append("场所原值包含适用对象、作业活动或管理条件，疑似把适用说明写入场所标签。")
    if value in PLACE_GENERIC_VALUES:
        flags.append("信息不足")
        notes.append("场所原值较泛，需结合逐条记录确定是否足以支持场所筛选。")
    return ordered_flags(flags), notes


def law_level_review(value: str) -> tuple[list[str], list[str]]:
    flags: list[str] = []
    notes: list[str] = []
    if value in DEPARTMENT_LEVELS:
        flags.extend(("可能近义", "层级边界待审"))
        notes.append("部门规章与部门规章（部令）并存，需统一粗细层级与部令标注口径；不作自动合并。")
    if value in NATIONAL_STANDARD_LEVELS:
        flags.append("层级边界待审")
        notes.append("国家标准及其强制性、推荐性、工程建设、职业卫生子类分散，需人工确定展示层级。")
    return ordered_flags(flags), notes


def row_brief(row: dict[str, Any], clue: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": row.get("id", ""),
        "title": row.get("title", ""),
        "category": row.get("category", ""),
        "places": list(dict.fromkeys(row.get("places") or [])),
    }
    if row.get("levels"):
        result["levels"] = list(dict.fromkeys(row["levels"]))
    if clue:
        result["reviewClue"] = clue
    return result


def law_brief(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id", ""),
        "name": row.get("name", ""),
        "level": row.get("level", ""),
        "scope": row.get("scope", ""),
        "status": row.get("status", ""),
        "effectiveDate": row.get("effectiveDate", ""),
        "clauseCount": row.get("clauseCount", 0),
        "hazardCount": row.get("hazardCount", 0),
    }


def records_for_value(rows: list[dict[str, Any]], field: str, value: str) -> list[dict[str, Any]]:
    def matches(row: dict[str, Any]) -> bool:
        raw = row.get(field)
        return value in raw if isinstance(raw, (list, tuple, set)) else raw == value

    return sorted(
        (row for row in rows if matches(row)),
        key=lambda row: str(row.get("id", "")),
    )


def category_entries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(row.get("category", "") for row in rows)
    entries = []
    for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        members = records_for_value(rows, "category", value)
        flags, notes = category_review(value)
        entry: dict[str, Any] = {
            "value": value,
            "publicRecordCount": count,
            "stableIdSamples": stable_ids(members, 5),
            "reviewFlags": flags,
            "reviewNotes": notes,
        }
        if flags:
            entry["stableIds"] = stable_ids(members)
        entries.append(entry)
    return entries


def place_entries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    members: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        for value in dict.fromkeys(row.get("places") or []):
            counts[value] += 1
            members.setdefault(value, []).append(row)

    entries = []
    for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        flags, notes = place_review(value)
        member_rows = members[value]
        entry: dict[str, Any] = {
            "value": value,
            "publicRecordCount": count,
            "stableIdSamples": stable_ids(member_rows, 5),
            "reviewFlags": flags,
            "reviewNotes": notes,
        }
        if flags:
            entry["stableIds"] = stable_ids(member_rows)
        entries.append(entry)
    return entries


def law_level_entries(law_rows: list[dict[str, Any]], references: list[dict[str, Any]]) -> list[dict[str, Any]]:
    law_members: dict[str, list[dict[str, Any]]] = {}
    ref_members: dict[str, list[dict[str, Any]]] = {}
    for law in law_rows:
        law_members.setdefault(law.get("level", ""), []).append(law)
    for ref in references:
        ref_members.setdefault(ref["level"], []).append(ref)

    entries = []
    for value, members in sorted(law_members.items(), key=lambda item: (-len(item[1]), item[0])):
        flags, notes = law_level_review(value)
        ref_rows = ref_members.get(value, [])
        entries.append({
            "value": value,
            "publicLawVersionCount": len(members),
            "publicHazardReferenceCount": len(ref_rows),
            "lawVersionIdSamples": stable_ids(members, 5),
            "hazardIdSamples": sorted({ref["hazardId"] for ref in ref_rows})[:5],
            "reviewFlags": flags,
            "reviewNotes": notes,
            "lawVersionIds": stable_ids(members) if flags else None,
        })
    for entry in entries:
        if entry["lawVersionIds"] is None:
            del entry["lawVersionIds"]
    return entries


def all_references(law_rows: list[dict[str, Any]], public_hazard_ids: set[str]) -> list[dict[str, Any]]:
    """Return the law-index projection, which intentionally uses sets in the builder."""
    references: list[dict[str, Any]] = []
    for law in law_rows:
        for clause_ref in law.get("clauseRefs") or []:
            for hazard_id in clause_ref.get("hazardIds") or []:
                if hazard_id not in public_hazard_ids:
                    raise ValueError(f"法规索引引用未公开隐患：{law.get('id')}/{hazard_id}")
                references.append({
                    "lawVersionId": law.get("id", ""),
                    "level": law.get("level", ""),
                    "clauseId": clause_ref.get("clauseId", ""),
                    "hazardId": hazard_id,
                })
    return references


def hazard_basis_references(
    hazards: dict[str, dict[str, Any]],
    clauses: dict[str, dict[str, Any]],
    law_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return the public association rows, preserving basisRefs role rows."""
    law_by_id = {law.get("id"): law for law in law_rows}
    references: list[dict[str, Any]] = []
    for hazard in hazards.values():
        for basis_ref in hazard.get("basisRefs") or []:
            clause_id = basis_ref.get("clauseId") or ""
            clause = clauses.get(clause_id)
            if not clause:
                raise ValueError(f"隐患依据引用不存在条款：{hazard.get('id')}/{clause_id}")
            law_id = clause.get("lawId") or ""
            law = law_by_id.get(law_id)
            if not law:
                raise ValueError(f"公开条款引用不存在法规版本：{clause_id}/{law_id}")
            references.append({
                "lawVersionId": law_id,
                "level": law.get("level", ""),
                "clauseId": clause_id,
                "hazardId": hazard.get("id", ""),
                "role": basis_ref.get("role", ""),
            })
    return references


def near_synonym_category_review(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for left, right in CATEGORY_NEAR_PAIRS:
        members = []
        for value in (left, right):
            value_rows = records_for_value(rows, "category", value)
            members.append({
                "value": value,
                "publicRecordCount": len(value_rows),
                "stableIds": stable_ids(value_rows),
                "records": [row_brief(row) for row in value_rows],
            })
        result.append({
            "values": [left, right],
            "reviewFlags": ["可能近义"],
            "reviewNote": "只列入人工审定候选组，不表示应合并或存在错误。",
            "members": members,
        })
    return result


def composite_category_review(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    values = sorted({
        row.get("category", "")
        for row in rows
        if any(marker in row.get("category", "") for marker in COMPOSITE_CATEGORY_MARKERS)
    })
    result = []
    for value in values:
        value_rows = records_for_value(rows, "category", value)
        result.append({
            "category": value,
            "publicRecordCount": len(value_rows),
            "reviewFlags": ["维度混合"],
            "reviewNote": "组合类别逐条待审定；本清单不执行整体归并。",
            "records": [row_brief(row) for row in value_rows],
        })
    return result


def generic_category_review(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for value in GENERIC_CATEGORIES:
        value_rows = records_for_value(rows, "category", value)
        result.append({
            "category": value,
            "publicRecordCount": len(value_rows),
            "reviewFlags": ["维度混合", "信息不足"],
            "reviewNote": "泛化类别逐条待审定；本清单不执行整体归并。",
            "records": [row_brief(row) for row in value_rows],
        })
    return result


def equipment_management_review(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for row in records_for_value(rows, "category", "设备设施"):
        searchable = " ".join([row.get("title", ""), *row.get("keywords", [])])
        match = MANAGEMENT_RE.search(searchable)
        if match:
            result.append(row_brief(
                row,
                f"标题或关键词包含管理类线索“{match.group(0)}”，需人工判断主题与管理事项边界。",
            ))
    return result


def place_scope_review(rows: list[dict[str, Any]], entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    row_by_id = {row.get("id"): row for row in rows}
    for entry in entries:
        if "维度混合" not in entry["reviewFlags"]:
            continue
        result.append({
            "value": entry["value"],
            "publicRecordCount": entry["publicRecordCount"],
            "reviewFlags": entry["reviewFlags"],
            "reviewNotes": entry["reviewNotes"],
            "stableIds": entry.get("stableIds", []),
            "sampleRecords": [row_brief(row_by_id[record_id]) for record_id in entry.get("stableIdSamples", [])],
        })
    return result


def suspected_wrong_classification(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        category = row.get("category", "")
        title = row.get("title", "")
        if category == "专项安全与EHS":
            match = SPECIFIC_DOMAIN_RE.search(title)
            if match:
                result.append(row_brief(
                    row,
                    f"泛化类别记录标题含具体专业线索“{match.group(0)}”，疑似需要复核分类维度；不推断目标类别。",
                ))
        elif category == "燃气与电气安全":
            has_gas = bool(re.search(r"燃气|天然气|液化气", title))
            has_electric = bool(re.search(r"电气|用电|配电|漏电|接地", title))
            if has_gas != has_electric:
                result.append(row_brief(
                    row,
                    "组合类别记录标题只呈现燃气或电气一侧线索，疑似需要复核是否为组合主题；不推断目标类别。",
                ))
    return result


def source_consistency(public_rows: list[dict[str, Any]], knowledge: dict[str, Any]) -> dict[str, Any]:
    source_rows = knowledge["hazards"]
    missing = sorted(row["id"] for row in public_rows if row["id"] not in source_rows)
    mismatches = []
    for row in public_rows:
        source = source_rows.get(row["id"])
        if not source:
            continue
        for field in ("title", "category", "places", "aliases", "keywords", "mode"):
            public_value = row.get(field) or [] if isinstance(row.get(field), list) else row.get(field, "")
            source_value = source.get(field) or [] if isinstance(source.get(field), list) else source.get(field, "")
            if public_value != source_value:
                mismatches.append({"id": row["id"], "field": field})
    return {
        "knowledgeHazardCount": len(source_rows),
        "publicIdsMissingFromKnowledge": missing,
        "publicLabelMismatches": mismatches,
        "publicIdsVerifiedAgainstKnowledge": len(public_rows) - len(missing),
    }


def build_audit(bundle: Path, knowledge_root: Path, argv: list[str]) -> dict[str, Any]:
    public = load_public_bundle(bundle)
    knowledge = load_knowledge_source(knowledge_root)
    rows = public["searchIndex"]
    laws = public["lawIndex"]
    law_index_references = all_references(laws, {row["id"] for row in rows})
    references = hazard_basis_references(public["hazards"], public["clauses"], laws)
    manifest_counts = public["manifest"].get("counts", {})
    recomputed_counts = {
        "hazards": len(rows),
        "laws": len(laws),
        "lawVersions": len(laws),
        "clauses": len(public["clauses"]),
        "links": len(references),
    }
    if manifest_counts != {key: manifest_counts.get(key) for key in recomputed_counts}:
        raise ValueError("公开 manifest 缺少必需计数字段")

    categories = category_entries(rows)
    places = place_entries(rows)
    law_levels = law_level_entries(laws, references)
    category_sum = sum(entry["publicRecordCount"] for entry in categories)
    place_tag_sum = sum(entry["publicRecordCount"] for entry in places)
    law_version_sum = sum(entry["publicLawVersionCount"] for entry in law_levels)
    law_reference_sum = sum(entry["publicHazardReferenceCount"] for entry in law_levels)

    composite = composite_category_review(rows)
    generic = generic_category_review(rows)
    near_synonyms = near_synonym_category_review(rows)
    equipment_management = equipment_management_review(rows)
    scope_mixing = place_scope_review(rows, places)
    suspected_wrong = suspected_wrong_classification(rows)
    law_by_level = {law.get("level", ""): [] for law in laws}
    for law in laws:
        law_by_level.setdefault(law.get("level", ""), []).append(law_brief(law))
    for value in law_by_level:
        law_by_level[value].sort(key=lambda row: row["id"])

    category_values = {entry["value"] for entry in categories}
    law_values = {entry["value"] for entry in law_levels}
    place_values = {entry["value"] for entry in places}
    taxonomy = public["taxonomy"]
    taxonomy_mismatch = {
        "categoriesOnlyInTaxonomy": sorted(set(taxonomy.get("categories", [])) - category_values),
        "categoriesOnlyInPublicRecords": sorted(category_values - set(taxonomy.get("categories", []))),
        "placesOnlyInTaxonomy": sorted(set(taxonomy.get("places", [])) - place_values),
        "placesOnlyInPublicRecords": sorted(place_values - set(taxonomy.get("places", []))),
        "lawLevelsOnlyInTaxonomy": sorted(set(taxonomy.get("lawLevels", [])) - law_values),
        "lawLevelsOnlyInPublicRecords": sorted(law_values - set(taxonomy.get("lawLevels", []))),
    }

    source_consistency_result = source_consistency(rows, knowledge)
    source_law_versions = knowledge["lawVersions"]
    public_law_missing = sorted(law["id"] for law in laws if law["id"] not in source_law_versions)
    public_law_level_mismatch = sorted(
        law["id"] for law in laws
        if law["id"] in source_law_versions
        and law.get("level", "") != source_law_versions[law["id"]].get("level", "")
    )

    release = public["release"]
    manifest = public["manifest"]
    output: dict[str, Any] = {
        "schemaVersion": "safety-basis-taxonomy-audit-v1",
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": {
            "reviewOnly": True,
            "noClassificationApplied": True,
            "reviewFlagsAreSuggestions": True,
            "publicPackageIsCountingSource": True,
            "publicRecordStatuses": ["已核验"],
            "candidateOrSupersededInventoryExcluded": True,
        },
        "source": {
            "worktree": str(ROOT),
            "branch": git_value("branch", "--show-current"),
            "baseOrHeadCommit": git_value("rev-parse", "HEAD"),
            "publicBundle": str(bundle.resolve()),
            "publicReleaseHash": release.get("releaseHash", ""),
            "asOf": release.get("asOf", ""),
            "dataVersion": manifest.get("dataVersion", ""),
            "generator": release.get("generator", {}),
            "knowledgeRoot": str(knowledge_root.resolve()),
            "knowledgeManifestCounts": knowledge["manifest"].get("counts", {}),
            "command": " ".join(argv),
        },
        "countingMethod": {
            "categories": "每条公开隐患记录的原始 category 计 1 次。",
            "places": "每条公开隐患记录的去重 places 标签各计 1 次；多标签会重复计入标签总和。",
            "lawLevels": "每个公开法规版本计 1 次；另列实际公开隐患引用次数，不将两者相加。",
            "hazardReferences": "遍历公开隐患分片 basisRefs，每个公开隐患—条款—角色关联行计 1 次；法规索引的集合投影另行交叉核对。",
        },
        "publicCounts": {
            "manifest": manifest_counts,
            "recomputed": recomputed_counts,
            "matchesManifest": manifest_counts == recomputed_counts,
            "categoryRecordCountSum": category_sum,
            "categoryRecordCountMatchesHazards": category_sum == len(rows),
            "placeTagOccurrenceCount": place_tag_sum,
            "lawVersionCountSum": law_version_sum,
            "lawVersionCountMatchesLawIndex": law_version_sum == len(laws),
            "lawReferenceCountSum": law_reference_sum,
            "lawReferenceCountMatchesLinks": law_reference_sum == len(references),
            "lawIndexUniqueReferenceCount": len(law_index_references),
            "lawIndexReferenceRowsCollapsed": len(references) - len(law_index_references),
            "clauseRefCountFromLawIndex": sum(len(law.get("clauseRefs") or []) for law in laws),
        },
        "taxonomyCoverage": {
            "taxonomyMismatch": taxonomy_mismatch,
            "allPublicCategoryValuesCovered": not taxonomy_mismatch["categoriesOnlyInPublicRecords"],
            "allPublicPlaceValuesCovered": not taxonomy_mismatch["placesOnlyInPublicRecords"],
            "allPublicLawLevelsCovered": not taxonomy_mismatch["lawLevelsOnlyInPublicRecords"],
        },
        "knowledgeCrossCheck": {
            **source_consistency_result,
            "knowledgeLawVersionCount": len(source_law_versions),
            "publicLawVersionsMissingFromKnowledge": public_law_missing,
            "publicLawLevelMismatches": public_law_level_mismatch,
            "publicLawVersionsVerifiedAgainstKnowledge": len(laws) - len(public_law_missing),
        },
        "dimensions": {
            "categories": {
                "distinct": len(categories),
                "values": categories,
            },
            "places": {
                "distinct": len(places),
                "values": places,
            },
            "lawLevels": {
                "distinct": len(law_levels),
                "values": law_levels,
            },
        },
        "targetedReviewQueues": {
            "nearSynonymCategoryPairs": near_synonyms,
            "equipmentFacilitiesManagementItems": {
                "category": "设备设施",
                "selectionRule": "category 等于设备设施，且标题/关键词命中管理、责任、培训、检查、记录、维护等线索；仅供人工复核。",
                "reviewFlags": ["维度混合", "疑似错分"],
                "records": equipment_management,
            },
            "compositeCategories": composite,
            "genericCategories": generic,
            "departmentRegulationBoundary": {
                "levels": list(DEPARTMENT_LEVELS),
                "reviewFlags": ["可能近义", "层级边界待审"],
                "recordsByLevel": {level: law_by_level.get(level, []) for level in DEPARTMENT_LEVELS},
            },
            "nationalStandardSubclasses": {
                "levels": [level for level in NATIONAL_STANDARD_LEVELS if level in law_by_level],
                "reviewFlags": ["层级边界待审"],
                "recordsByLevel": {level: law_by_level.get(level, []) for level in NATIONAL_STANDARD_LEVELS if level in law_by_level},
            },
            "placeScopeMixing": {
                "reviewFlags": ["维度混合"],
                "values": scope_mixing,
            },
            "suspectedWrongClassification": {
                "reviewFlags": ["疑似错分"],
                "records": suspected_wrong,
            },
        },
        "reviewBoundary": [
            "所有 reviewFlags、near-synonym、组合类别和疑似错分均为待审定线索，不是已确认分类结论。",
            "不合并、删除或改写任何实体、稳定编号、标签、法规类别或法规适用性。",
            "法规类型统计按公开法规版本计数；隐患引用计数单列，不能用引用次数替代版本数。",
        ],
    }
    return output


def markdown_report(audit: dict[str, Any]) -> str:
    source = audit["source"]
    counts = audit["publicCounts"]
    dimensions = audit["dimensions"]
    queues = audit["targetedReviewQueues"]
    categories = dimensions["categories"]["values"]
    laws = dimensions["lawLevels"]["values"]
    places = dimensions["places"]["values"]

    def flags(entry: dict[str, Any]) -> str:
        return "、".join(entry.get("reviewFlags") or []) or "—"

    lines = [
        "# 阶段 1 / T2 全量分类只读审定清单",
        "",
        "本文件只提供审定基础，不执行分类迁移、实体合并或法规适用性判断。完整原值、稳定编号和逐条待审定记录见同目录 JSON。",
        "",
        "## 来源与复现",
        "",
        f"- 公开包：`{source['publicBundle']}`",
        f"- `dataVersion`：`{source['dataVersion']}`；`releaseHash`：`{source['publicReleaseHash']}`；`asOf`：`{source['asOf']}`",
        f"- 工作区/分支/基线：`{source['worktree']}` / `{source['branch']}` / `{source['baseOrHeadCommit']}`",
        f"- 统计口径：{audit['countingMethod']['places']} {audit['countingMethod']['lawLevels']}",
        "- JSON 的 `knowledgeCrossCheck` 同时记录了公开投影与 `knowledge/` 原始标签的只读一致性核对；候选/库存不纳入公开统计。",
        "",
        "## 公开包计数复算",
        "",
        "| 指标 | manifest | 重算 | 结果 |",
        "|---|---:|---:|---|",
    ]
    for key in ("hazards", "laws", "lawVersions", "clauses", "links"):
        expected = audit["publicCounts"]["manifest"].get(key, "—")
        actual = audit["publicCounts"]["recomputed"].get(key, "—")
        lines.append(f"| {key} | {expected} | {actual} | {'一致' if expected == actual else '不一致'} |")
    lines.extend([
        f"| 主题记录计数总和 | — | {counts['categoryRecordCountSum']} | {'与隐患数一致' if counts['categoryRecordCountMatchesHazards'] else '需调查'} |",
        f"| 场所标签出现次数 | — | {counts['placeTagOccurrenceCount']} | 多标签重复计数 |",
        f"| 法规版本类型计数总和 | — | {counts['lawVersionCountSum']} | {'与法规索引一致' if counts['lawVersionCountMatchesLawIndex'] else '需调查'} |",
        f"| 隐患引用计数总和 | — | {counts['lawReferenceCountSum']} | {'与 links 一致' if counts['lawReferenceCountMatchesLinks'] else '需调查'} |",
        f"| 法规索引去重后的引用行 | — | {counts['lawIndexUniqueReferenceCount']} | 折叠 {counts['lawIndexReferenceRowsCollapsed']} 行，作为交叉值保留 |",
        "",
        "## 主题原值（全量）",
        "",
        "| 原值 | 公开隐患数 | 审查线索 | 稳定编号样例 |",
        "|---|---:|---|---|",
    ])
    for entry in categories:
        lines.append(f"| {entry['value']} | {entry['publicRecordCount']} | {flags(entry)} | {'、'.join(entry['stableIdSamples'])} |")
    lines.extend([
        "",
        "## 依据类型原值（全量）",
        "",
        "法规类型按法规版本计数；隐患引用次数单列，不能把引用次数当作法规版本数。",
        "",
        "| 原值 | 法规版本数 | 隐患引用数 | 审查线索 | 稳定编号样例 |",
        "|---|---:|---:|---|---|",
    ])
    for entry in laws:
        lines.append(f"| {entry['value']} | {entry['publicLawVersionCount']} | {entry['publicHazardReferenceCount']} | {flags(entry)} | {'、'.join(entry['lawVersionIdSamples'])} |")
    lines.extend([
        "",
        "## 场所原值",
        "",
        f"共 {len(places)} 个原值；每项稳定编号在 JSON 的 `dimensions.places.values`。长句、地域和适用说明混入的项目列入 `targetedReviewQueues.placeScopeMixing`。",
        "",
        "高频前 20 项：",
        "",
        "| 原值 | 公开记录数 | 审查线索 | 稳定编号样例 |",
        "|---|---:|---|---|",
    ])
    for entry in places[:20]:
        lines.append(f"| {entry['value']} | {entry['publicRecordCount']} | {flags(entry)} | {'、'.join(entry['stableIdSamples'])} |")
    lines.extend([
        "",
        "## 必查审定队列",
        "",
        f"- 可能近义类别组：电气安全/用电安全、机械与设备安全/机械设备安全、安全教育培训/安全教育；见 `nearSynonymCategoryPairs`，不表示自动合并。",
        f"- 设备设施中的管理事项：{len(queues['equipmentFacilitiesManagementItems']['records'])} 条，见 `equipmentFacilitiesManagementItems.records`。",
        f"- 组合类别：{len(queues['compositeCategories'])} 组；其中燃气与电气安全的 {next((x['publicRecordCount'] for x in queues['compositeCategories'] if x['category'] == '燃气与电气安全'), 0)} 条记录逐条列出。",
        f"- 泛化类别：设备设施（{next((x['publicRecordCount'] for x in queues['genericCategories'] if x['category'] == '设备设施'), 0)} 条）和专项安全与EHS（{next((x['publicRecordCount'] for x in queues['genericCategories'] if x['category'] == '专项安全与EHS'), 0)} 条）均逐条列出。",
        f"- 部门规章边界：部门规章 / 部门规章（部令），分别列出 {len(queues['departmentRegulationBoundary']['recordsByLevel'].get('部门规章', []))} / {len(queues['departmentRegulationBoundary']['recordsByLevel'].get('部门规章（部令）', []))} 个公开法规版本。",
        f"- 国家标准及子类：{', '.join(queues['nationalStandardSubclasses']['levels'])}；各版本逐条列于 `recordsByLevel`。",
        f"- 场所地域/适用说明混入线索：{len(queues['placeScopeMixing']['values'])} 个原值，均带稳定编号追溯。",
        f"- 疑似错分线索：{len(queues['suspectedWrongClassification']['records'])} 条，仅供人工复核，不提供目标分类。",
        "",
        "## 边界",
        "",
        "本阶段没有发布新分类体系，没有推断强制性或法规适用性，没有合并/删除实体，也没有写回业务记录。所有标记均为审查建议。",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="生成公开分类的只读全量审定清单")
    parser.add_argument("--bundle", required=True, help="本阶段从基线源码生成的公开包目录")
    parser.add_argument("--out-dir", required=True, help="JSON/Markdown/STATUS.md 的外部交付目录")
    parser.add_argument("--knowledge-root", default=str(ROOT / "knowledge"), help="只读 knowledge 根目录")
    parser.add_argument("--output-stem", default="taxonomy-audit-stage1", help="输出文件名主干")
    args = parser.parse_args()

    bundle = Path(args.bundle).resolve()
    knowledge_root = Path(args.knowledge_root).resolve()
    out_dir = Path(args.out_dir).resolve()
    if not (bundle / "release.json").is_file():
        raise SystemExit(f"公开包不存在或缺少 release.json：{bundle}")
    if not (knowledge_root / "manifest.json").is_file():
        raise SystemExit(f"knowledge 根目录不存在或缺少 manifest.json：{knowledge_root}")

    audit = build_audit(bundle, knowledge_root, [sys.executable, *sys.argv])
    json_path = out_dir / f"{args.output_stem}.json"
    markdown_path = out_dir / f"{args.output_stem}.md"
    write_json(json_path, audit)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown_report(audit), encoding="utf-8", newline="\n")

    print(f"只读分类审定 JSON：{json_path}")
    print(f"简短 Markdown：{markdown_path}")
    print(json.dumps(audit["publicCounts"]["recomputed"], ensure_ascii=False, sort_keys=True))
    print(f"主题 {audit['dimensions']['categories']['distinct']} 项；场所 {audit['dimensions']['places']['distinct']} 项；依据类型 {audit['dimensions']['lawLevels']['distinct']} 项")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
