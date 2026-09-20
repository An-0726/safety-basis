# -*- coding: utf-8 -*-
"""Audit Stage 4 note routing without changing source or public data."""
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
sys.path.insert(0, str(ROOT / "tools" / "v4"))
from presentation import (  # noqa: E402
    APPROVED_MAINTENANCE_TEXTS,
    NOTE_DATE_PREFIX,
    project_note,
    searchable,
)

SUSPECT_MARKERS = (NOTE_DATE_PREFIX, "PHASE", "质检", "版本治理", "对账", "已复核", "修订", "精简", "通用化")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def load_hazards(bundle: Path) -> dict[str, dict[str, Any]]:
    manifest = read_json(bundle / "data" / "manifest.json")
    result: dict[str, dict[str, Any]] = {}
    for shard in manifest["hazardShards"]:
        payload = read_json(bundle / shard["url"])
        for row in payload["records"]:
            result[row["id"]] = row
    return result


def load_search_index(bundle: Path) -> dict[str, dict[str, Any]]:
    manifest = read_json(bundle / "data" / "manifest.json")
    return {row["id"]: row for row in read_json(bundle / manifest["files"]["searchIndex"])}


def old_search_text(source: dict[str, Any], index: dict[str, Any], note: str) -> str:
    return searchable([
        source.get("title", ""), " ".join(source.get("aliases") or []),
        " ".join(source.get("keywords") or []), source.get("description", ""),
        source.get("conditions") or "", note,
        " ".join(sorted(index.get("lawNames") or [])),
        " ".join(sorted(index.get("stdNumbers") or [])), source.get("category", ""),
        index.get("displayCategory", ""), " ".join(index.get("sceneTags") or []),
        " ".join(sorted(index.get("displayLevels") or [])),
    ])


def first_business_query(note: str) -> str:
    text = " ".join(part.strip() for part in note.splitlines() if part.strip())
    if not text:
        return ""
    return text[:12]


def build_report(bundle: Path, old_bundle: Path, knowledge_root: Path) -> dict[str, Any]:
    new_hazards = load_hazards(bundle)
    new_search = load_search_index(bundle)
    old_search = load_search_index(old_bundle) if old_bundle and old_bundle.is_dir() else {}
    source_hazards = {
        path.stem: read_json(path)
        for path in sorted((knowledge_root / "hazards").glob("*.json"))
    }

    records = []
    maintenance_groups: Counter[str] = Counter()
    suspected_groups: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    source_note_mismatches = []
    projection_mismatches = []
    search_mismatches = []
    maintenance_leaks = []
    old_search_by_id: dict[str, str] = {}
    new_search_by_id: dict[str, str] = {}

    for hazard_id in sorted(new_hazards):
        row = new_hazards[hazard_id]
        source = source_hazards.get(hazard_id, {})
        raw_note = source.get("note")
        raw_text = "" if raw_note is None else raw_note
        projection = project_note(raw_note)
        search_row = new_search.get(hazard_id, {})
        old_row = old_search.get(hazard_id, {})
        expected_old = old_search_text(source, search_row or old_row, raw_text)
        expected_new = old_search_text(source, search_row, projection["businessNote"])
        old_search_by_id[hazard_id] = old_row.get("searchText", expected_old)
        new_search_by_id[hazard_id] = search_row.get("searchText", "")

        if row.get("note") != source.get("note", ""):
            source_note_mismatches.append(hazard_id)
        if any(row.get(field) != projection[field]
               for field in ("noteSegments", "businessNote", "maintenanceNote")):
            projection_mismatches.append(hazard_id)
        if search_row.get("searchText") != expected_new:
            search_mismatches.append(hazard_id)

        if projection["maintenanceNote"]:
            for segment in projection["noteSegments"]:
                if segment["kind"] == "maintenance":
                    maintenance_groups[segment["text"]] += 1
        if any(marker in projection["businessNote"] for marker in SUSPECT_MARKERS):
            suspected_groups[projection["businessNote"]].append({
                "id": hazard_id,
                "title": source.get("title", ""),
                "note": raw_note,
                "businessNote": projection["businessNote"],
                "reason": "备注仍含未命中批准句式的维护/审查线索；仅列入审查，不隐藏。",
            })
        if projection["maintenanceNote"]:
            maintenance_texts = [segment["text"] for segment in projection["noteSegments"]
                                 if segment["kind"] == "maintenance"]
            if any(searchable([text]) in new_search_by_id[hazard_id] for text in maintenance_texts):
                maintenance_leaks.append(hazard_id)

        records.append({
            "id": hazard_id,
            "title": source.get("title", ""),
            "note": raw_note,
            "noteSegments": projection["noteSegments"],
            "businessNote": projection["businessNote"],
            "maintenanceNote": projection["maintenanceNote"],
            "sourceNotePreserved": row.get("note") == source.get("note", ""),
            "projectionVerified": not any(row.get(field) != projection[field]
                                           for field in ("noteSegments", "businessNote", "maintenanceNote")),
            "searchTextUsesBusinessNote": search_row.get("searchText") == expected_new,
            "oldSearchTextRecomputedWithRawNote": expected_old,
            "newSearchTextRecomputedWithBusinessNote": expected_new,
        })

    maintenance_queries = []
    for phrase in APPROVED_MAINTENANCE_TEXTS:
        query = searchable([phrase])
        old_ids = sorted(hid for hid, text in old_search_by_id.items() if query in text)
        new_ids = sorted(hid for hid, text in new_search_by_id.items() if query in text)
        maintenance_queries.append({
            "query": phrase,
            "oldRawNoteSearchCount": len(old_ids),
            "newBusinessNoteSearchCount": len(new_ids),
            "removedMaintenanceOnlyIds": sorted(set(old_ids) - set(new_ids)),
            "retainedIds": sorted(set(old_ids) & set(new_ids)),
        })

    business_queries = []
    fixed_query = "原 conditions 字段记录的引用依据"
    sample_queries = [fixed_query]
    for record in records:
        query = first_business_query(record["businessNote"])
        if query and query not in sample_queries:
            sample_queries.append(query)
        if len(sample_queries) >= 4:
            break
    for query in sample_queries:
        normalized_query = searchable([query])
        old_ids = sorted(hid for hid, text in old_search_by_id.items() if normalized_query in text)
        new_ids = sorted(hid for hid, text in new_search_by_id.items() if normalized_query in text)
        business_queries.append({
            "query": query,
            "oldRawNoteSearchCount": len(old_ids),
            "newBusinessNoteSearchCount": len(new_ids),
            "retainedBusinessIds": sorted(set(old_ids) & set(new_ids)),
            "changedIds": sorted(set(old_ids) ^ set(new_ids)),
        })

    return {
        "schemaVersion": "safety-stage4-note-routing-v1",
        "scope": {
            "reviewOnly": True,
            "sourceNotesUnchanged": True,
            "approvedSentencesOnly": True,
            "unmatchedSuspectedMaintenanceIsReviewOnly": True,
        },
        "source": {
            "knowledgeRoot": str(knowledge_root.resolve()),
            "newBundle": str(bundle.resolve()),
            "oldBundle": str(old_bundle.resolve()) if old_bundle else "未提供",
            "newReleaseHash": read_json(bundle / "release.json").get("releaseHash", ""),
        },
        "counts": {
            "publicHazards": len(records),
            "recordsWithMaintenance": sum(bool(record["maintenanceNote"]) for record in records),
            "maintenanceSegments": sum(len([s for s in record["noteSegments"] if s["kind"] == "maintenance"])
                                        for record in records),
            "recordsWithBusinessNote": sum(bool(record["businessNote"].strip()) for record in records),
            "sourceNoteMismatches": len(source_note_mismatches),
            "projectionMismatches": len(projection_mismatches),
            "searchMismatches": len(search_mismatches),
            "maintenanceSearchLeaks": len(maintenance_leaks),
            "unmatchedSuspectedMaintenanceRecords": sum(len(rows) for rows in suspected_groups.values()),
        },
        "maintenanceTextGroups": [
            {"text": text, "publicRecordCount": count}
            for text, count in sorted(maintenance_groups.items(), key=lambda item: (-item[1], item[0]))
        ],
        "searchDiff": {
            "approvedMaintenanceQueries": maintenance_queries,
            "businessQueries": business_queries,
            "interpretation": "旧口径按原 note 重算，新口径按 businessNote 重算；维护句式被清理的命中列为 maintenance-only，正常业务命中保留在 retainedBusinessIds。",
        },
        "integrity": {
            "sourceNoteMismatches": source_note_mismatches,
            "projectionMismatches": projection_mismatches,
            "searchMismatches": search_mismatches,
            "maintenanceSearchLeaks": maintenance_leaks,
        },
        "unmatchedSuspectedMaintenance": [
            {"businessNote": business_note, "records": rows}
            for business_note, rows in sorted(suspected_groups.items())
        ],
        "records": records,
        "boundary": [
            "只对批准的完整句式做 maintenance 分流；近似、其他日期、PHASE/质检/版本治理等未批准内容保留在 businessNote 并列入审查清单。",
            "不改变 source/knowledge/publication，不判断法规效力、适用性、分类正确性或隐患结论。",
        ],
    }


def markdown_report(report: dict[str, Any]) -> str:
    counts = report["counts"]
    lines = [
        "# 阶段 4 备注无损分流与搜索差异报告",
        "",
        "本报告只审计公开投影，不改写源 note；只有任务书批准的完整句式进入 maintenance，其余字符保留 business 并进入审查清单。",
        "",
        f"- 新包：`{report['source']['newBundle']}`",
        f"- releaseHash：`{report['source']['newReleaseHash']}`",
        f"- 公开隐患：{counts['publicHazards']}；含维护片段：{counts['recordsWithMaintenance']}；维护片段：{counts['maintenanceSegments']}；含业务说明：{counts['recordsWithBusinessNote']}",
        f"- 无损/投影/搜索不一致：{counts['sourceNoteMismatches']} / {counts['projectionMismatches']} / {counts['searchMismatches']}；维护语料搜索泄漏：{counts['maintenanceSearchLeaks']}",
        f"- 未命中批准句式但含审查线索的记录：{counts['unmatchedSuspectedMaintenanceRecords']}（保留 business，不隐藏）",
        "",
        "## 维护句式分组",
        "",
        "| 批准维护原文 | 公开覆盖数 |",
        "|---|---:|",
    ]
    for entry in report["maintenanceTextGroups"]:
        lines.append(f"| {entry['text']} | {entry['publicRecordCount']} |")
    lines.extend(["", "## 搜索差异", "", "### 已清理维护命中", ""])
    for entry in report["searchDiff"]["approvedMaintenanceQueries"]:
        lines.append(f"- `{entry['query']}`：旧口径 {entry['oldRawNoteSearchCount']}，新口径 {entry['newBusinessNoteSearchCount']}，清理维护命中 {len(entry['removedMaintenanceOnlyIds'])} 条。")
    lines.extend(["", "### 正常业务命中", ""])
    for entry in report["searchDiff"]["businessQueries"]:
        lines.append(f"- `{entry['query']}`：旧口径 {entry['oldRawNoteSearchCount']}，新口径 {entry['newBusinessNoteSearchCount']}，保留业务命中 {len(entry['retainedBusinessIds'])} 条。")
    lines.extend(["", "## 未批准疑似维护内容", "", "完整原文、ID、标题和 business 残留见 JSON 的 `unmatchedSuspectedMaintenance`；本节只提示审查边界，不做隐藏。", ""])
    for group in report["unmatchedSuspectedMaintenance"][:20]:
        lines.append(f"- 记录组（{len(group['records'])} 条）：`{group['businessNote'][:160]}`")
    lines.extend(["", "## 边界", "", *[f"- {item}" for item in report["boundary"]], ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--old-bundle", default="")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--knowledge-root", default=str(ROOT / "knowledge"))
    args = parser.parse_args()
    bundle = Path(args.bundle).resolve()
    old_bundle = Path(args.old_bundle).resolve() if args.old_bundle else None
    report = build_report(bundle, old_bundle, Path(args.knowledge_root).resolve())
    out_dir = Path(args.out_dir).resolve()
    write_json(out_dir / "note-routing-stage4.json", report)
    (out_dir / "note-routing-stage4.md").write_text(markdown_report(report), encoding="utf-8", newline="\n")
    print(json.dumps(report["counts"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
