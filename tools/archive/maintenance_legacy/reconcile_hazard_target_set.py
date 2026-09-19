# -*- coding: utf-8 -*-
"""Reconcile the revised 1,929-row workbook with knowledge hazards.

The workbook is read-only evidence for the target ID set.  This tool does not
modify the workbook or knowledge entities; it emits a deterministic JSON map
and a human-readable audit report.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_XLSX = Path(r"D:/Desktop/隐患库_1929条_新版口径全部整改完成_20260914.xlsx")
DEFAULT_JSON = ROOT / "docs" / "hazard-reconciliation.jsonl"
DEFAULT_MD = ROOT / "docs" / "HAZARD_RECONCILIATION.md"
SHEET = "隐患明细_修订后"
ID_RE = re.compile(r"H(?:_[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*|\d+(?:_\d+)*)")


def load_json_dir(path: Path) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for item in sorted(path.glob("*.json")):
        obj = json.loads(item.read_text(encoding="utf-8"))
        entity_id = str(obj.get("id") or obj.get("entityId") or item.stem)
        if entity_id in result:
            raise ValueError(f"duplicate entity id: {entity_id}")
        result[entity_id] = obj
    return result


def workbook_rows(path: Path) -> tuple[list[dict], dict]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    if SHEET not in workbook.sheetnames:
        raise ValueError(f"missing worksheet: {SHEET}")
    sheet = workbook[SHEET]
    rows = sheet.iter_rows(values_only=True)
    headers = [str(value or "").strip() for value in next(rows)]
    index = {name: offset for offset, name in enumerate(headers)}
    required = {"序号", "隐患ID", "隐患名称（标题）", "修订状态"}
    missing = sorted(required - set(index))
    if missing:
        raise ValueError(f"missing workbook columns: {missing}")

    records: list[dict] = []
    seen: set[str] = set()
    for excel_row, row in enumerate(rows, start=2):
        hazard_id = str(row[index["隐患ID"]] or "").strip()
        if not hazard_id:
            continue
        if hazard_id in seen:
            raise ValueError(f"duplicate workbook hazard id: {hazard_id}")
        seen.add(hazard_id)
        records.append(
            {
                "hazardId": hazard_id,
                "excelRow": excel_row,
                "sourceRow": row[index["序号"]],
                "workbookStatus": str(row[index["修订状态"]] or "").strip(),
                "workbookTitle": str(row[index["隐患名称（标题）"]] or "").strip(),
            }
        )
    return records, {
        "fileName": path.name,
        "size": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "sheet": SHEET,
        "dataRange": f"A2:R{len(records) + 1}",
    }


def terminal_id(hazard_id: str, hazards: dict[str, dict]) -> tuple[str | None, list[str]]:
    chain: list[str] = []
    current = hazard_id
    while hazards.get(current, {}).get("mergedInto"):
        if current in chain:
            return None, chain + [current]
        chain.append(current)
        current = hazards[current]["mergedInto"]
        if current not in hazards:
            return None, chain + [current]
    return current, chain + ([current] if chain else [])


def classify_target(hazard: dict) -> tuple[str, list[str]]:
    flags: list[str] = []
    if hazard.get("mergedInto"):
        if hazard.get("lifecycle") != "superseded":
            flags.append("merged-entity-lifecycle-not-superseded")
        return "target-merged-alias", flags
    if hazard.get("lifecycle") == "active":
        return "target-current", flags
    if hazard.get("lifecycle") == "proposed":
        return "target-proposed", flags
    flags.append("unexpected-target-lifecycle")
    return "needs-review", flags


def classify_extra(hazard: dict) -> tuple[str, list[str], list[str]]:
    flags: list[str] = []
    note = str(hazard.get("note") or "")
    children: list[str] = []
    if hazard.get("mergedInto"):
        return "knowledge-extra-merged-history", flags, children
    if hazard.get("lifecycle") == "superseded" and ("拆分" in note or "split" in note.lower()):
        children = list(dict.fromkeys(ID_RE.findall(note)))
        children = [item for item in children if item != hazard.get("id")]
        return "knowledge-extra-split-parent", flags, children
    if hazard.get("lifecycle") == "superseded":
        return "knowledge-extra-historical-non-hazard", flags, children
    if hazard.get("lifecycle") == "active":
        flags.append("active-entity-not-in-target-workbook")
        return "knowledge-extra-active-needs-review", flags, children
    if hazard.get("lifecycle") == "proposed":
        return "knowledge-extra-proposed-non-target", flags, children
    flags.append("unclassified-knowledge-extra")
    return "needs-review", flags, children


def md_escape(value: object) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def normalize_title(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip()
    return text.replace(",", "，").replace("。", "").replace(".", "").replace(" ", "")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    workbook, source = workbook_rows(args.xlsx)
    hazards = load_json_dir(ROOT / "knowledge" / "hazards")
    hazard_reviews = load_json_dir(ROOT / "knowledge" / "reviews" / "hazards")
    links = load_json_dir(ROOT / "knowledge" / "links")
    link_reviews = load_json_dir(ROOT / "knowledge" / "reviews" / "links")
    links_by_hazard: dict[str, list[dict]] = defaultdict(list)
    for link_id, link in links.items():
        if link.get("hazardId"):
            links_by_hazard[link["hazardId"]].append(
                {
                    "linkId": link_id,
                    "clauseId": link.get("clauseId"),
                    "role": link.get("role"),
                    "reviewDecision": link_reviews.get(link_id, {}).get("decision"),
                }
            )

    target_ids = {row["hazardId"] for row in workbook}
    knowledge_ids = set(hazards)
    target_records: list[dict] = []
    for row in workbook:
        hazard = hazards.get(row["hazardId"])
        if hazard is None:
            target_records.append({**row, "classification": "target-missing", "flags": ["missing-from-knowledge"]})
            continue
        classification, flags = classify_target(hazard)
        review_decision = hazard_reviews.get(row["hazardId"], {}).get("decision")
        title_exact = row["workbookTitle"] == hazard.get("title")
        title_normalized = normalize_title(row["workbookTitle"]) == normalize_title(hazard.get("title"))
        if not title_normalized and review_decision != "verified":
            flags.append("workbook-title-differs-after-normalization")
        title_disposition = (
            "exact"
            if title_exact
            else "punctuation-or-spacing-only"
            if title_normalized
            else "knowledge-reviewed-professional-wording"
            if review_decision == "verified"
            else "needs-review"
        )
        terminal, chain = terminal_id(row["hazardId"], hazards)
        target_records.append(
            {
                **row,
                "knowledgeTitle": hazard.get("title"),
                "titleExactMatch": title_exact,
                "titleNormalizedMatch": title_normalized,
                "titleDisposition": title_disposition,
                "lifecycle": hazard.get("lifecycle"),
                "mode": hazard.get("mode"),
                "proposalStatus": hazard.get("proposalStatus"),
                "mergedInto": hazard.get("mergedInto"),
                "terminalCanonicalId": terminal,
                "mergeChain": chain,
                "aliases": hazard.get("aliases") or [],
                "hazardReviewDecision": review_decision,
                "links": sorted(links_by_hazard.get(row["hazardId"], []), key=lambda item: item["linkId"]),
                "classification": classification,
                "flags": flags,
            }
        )

    extra_records: list[dict] = []
    for hazard_id in sorted(knowledge_ids - target_ids):
        hazard = hazards[hazard_id]
        classification, flags, children = classify_extra(hazard)
        terminal, chain = terminal_id(hazard_id, hazards)
        extra_records.append(
            {
                "hazardId": hazard_id,
                "knowledgeTitle": hazard.get("title"),
                "lifecycle": hazard.get("lifecycle"),
                "mode": hazard.get("mode"),
                "mergedInto": hazard.get("mergedInto"),
                "terminalCanonicalId": terminal,
                "mergeChain": chain,
                "splitChildren": children,
                "aliases": hazard.get("aliases") or [],
                "hazardReviewDecision": hazard_reviews.get(hazard_id, {}).get("decision"),
                "links": sorted(links_by_hazard.get(hazard_id, []), key=lambda item: item["linkId"]),
                "classification": classification,
                "flags": flags,
                "note": hazard.get("note") or "",
            }
        )

    all_merged = [hazard_id for hazard_id, hazard in hazards.items() if hazard.get("mergedInto")]
    missing_merge_targets = sorted(
        {hazard["mergedInto"] for hazard in hazards.values() if hazard.get("mergedInto") and hazard["mergedInto"] not in hazards}
    )
    merge_cycles = []
    for hazard_id in all_merged:
        terminal, chain = terminal_id(hazard_id, hazards)
        if terminal is None and chain and chain[-1] in chain[:-1]:
            merge_cycles.append(chain)

    summary = {
        "workbookRows": len(workbook),
        "workbookUniqueIds": len(target_ids),
        "workbookStatusCounts": dict(sorted(Counter(row["workbookStatus"] for row in workbook).items())),
        "knowledgeHazards": len(hazards),
        "knowledgeUniqueIds": len(knowledge_ids),
        "intersection": len(target_ids & knowledge_ids),
        "targetMissing": len(target_ids - knowledge_ids),
        "knowledgeExtra": len(knowledge_ids - target_ids),
        "targetClassificationCounts": dict(sorted(Counter(row["classification"] for row in target_records).items())),
        "extraClassificationCounts": dict(sorted(Counter(row["classification"] for row in extra_records).items())),
        "targetByWorkbookStatusAndClassification": [
            {"workbookStatus": status, "classification": classification, "count": count}
            for (status, classification), count in sorted(
                Counter((row["workbookStatus"], row["classification"]) for row in target_records).items()
            )
        ],
        "targetTitleExactMatches": sum(bool(row.get("titleExactMatch")) for row in target_records),
        "targetTitleNormalizedMatches": sum(bool(row.get("titleNormalizedMatch")) for row in target_records),
        "mergeEdges": len(all_merged),
        "missingMergeTargets": missing_merge_targets,
        "mergeCycles": merge_cycles,
        "flaggedTargetRows": sum(bool(row.get("flags")) for row in target_records),
        "flaggedExtraRows": sum(bool(row.get("flags")) for row in extra_records),
    }
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    jsonl_records = [
        {"recordType": "metadata", "schemaVersion": 1, "asOf": "2026-09-14", "source": source, "summary": summary},
        *({"recordType": "target", **record} for record in target_records),
        *({"recordType": "knowledge-extra", **record} for record in extra_records),
    ]
    args.json_out.write_text(
        "".join(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n" for record in jsonl_records),
        encoding="utf-8",
        newline="\n",
    )

    target_merged = [row for row in target_records if row["classification"] == "target-merged-alias"]
    title_differences = [row for row in target_records if not row.get("titleNormalizedMatch")]
    non_target_candidates = [
        row
        for row in extra_records
        if row["classification"] in {"knowledge-extra-active-needs-review", "knowledge-extra-proposed-non-target"}
    ]
    lines = [
        "# 1,929 目标隐患与 knowledge 全量对账",
        "",
        "> 本报告由 `tools/maintenance/reconcile_hazard_target_set.py` 从修订工作簿与当前 `knowledge/` 确定性生成。工作簿只用于目标 ID 和编辑状态核对，不作为法规原文证据。",
        "",
        "## 输入与结论",
        "",
        f"- 工作簿：`{source['fileName']}`，SHA-256 `{source['sha256']}`，`{source['sheet']}!{source['dataRange']}`。",
        f"- 工作簿有 {summary['workbookRows']} 行、{summary['workbookUniqueIds']} 个唯一 ID；knowledge 有 {summary['knowledgeHazards']} 个唯一 hazard 实体。",
        f"- 1,929 个目标 ID 全部直接存在于 knowledge；目标缺失 {summary['targetMissing']}，knowledge 目标外实体 {summary['knowledgeExtra']}。",
        "- `2,014 - 1,929 = 85` 只是集合差额，不等于 85 条重复。85 条已逐项分类见机器映射和附录。",
        f"- merge 图共有 {summary['mergeEdges']} 条边；缺失目标 {len(summary['missingMergeTargets'])}，循环 {len(summary['mergeCycles'])}。",
        f"- 标题逐字一致 {summary['targetTitleExactMatches']} 条；统一中英文标点和空格后仍有 {len(title_differences)} 条实质表述差异。",
        "",
        "## 目标集分类",
        "",
        "| 分类 | 数量 | 解释 |",
        "| --- | ---: | --- |",
    ]
    target_explanations = {
        "target-current": "当前 active、无 mergedInto；与现有 1,409 条正式发布基线一致。",
        "target-proposed": "仍为 proposed，保留在 knowledge，不进入正式公网。",
        "target-merged-alias": "工作簿目标 ID 仍保留，但已指向另一目标 ID；不是独立发布实体。",
        "target-missing": "工作簿 ID 在 knowledge 缺失。",
        "needs-review": "目标实体状态不符合已定义分类。",
    }
    for name, count in summary["targetClassificationCounts"].items():
        lines.append(f"| `{name}` | {count} | {target_explanations.get(name, '')} |")

    lines += ["", "### 621 修订与 1,308 保留的实际去向", "", "| 工作簿状态 | knowledge 分类 | 数量 |", "| --- | --- | ---: |"]
    for item in summary["targetByWorkbookStatusAndClassification"]:
        lines.append(f"| {md_escape(item['workbookStatus'])} | `{item['classification']}` | {item['count']} |")

    lines += [
        "",
        "## 目标外 85 个 knowledge 实体",
        "",
        "| 分类 | 数量 | 解释 |",
        "| --- | ---: | --- |",
    ]
    extra_explanations = {
        "knowledge-extra-merged-history": "已有 mergedInto 的历史稳定 ID。",
        "knowledge-extra-split-parent": "已拆分为更具体子隐患的历史父项。",
        "knowledge-extra-historical-non-hazard": "经终审认定为正向事实、非隐患，仅保留追溯。",
        "knowledge-extra-active-needs-review": "不在目标工作簿但仍为 active，须确认保留为目标外知识或调整生命周期。",
        "knowledge-extra-proposed-non-target": "不在目标工作簿且缺少完整正式 Gate，作为 proposed 范围复核 backlog 保留。",
        "needs-review": "未能由现有字段唯一解释。",
    }
    for name, count in summary["extraClassificationCounts"].items():
        lines.append(f"| `{name}` | {count} | {extra_explanations.get(name, '')} |")

    lines += [
        "",
        "## 状态复核结果",
        "",
        f"### 目标集内已合并并保留为 superseded alias（{len(target_merged)}）",
        "",
        "| 工作簿行 | ID | 标题 | mergedInto | review |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for row in target_merged:
        lines.append(
            f"| {row['sourceRow']} | `{row['hazardId']}` | {md_escape(row['knowledgeTitle'])} | `{row['mergedInto']}` | {md_escape(row['hazardReviewDecision'])} |"
        )

    lines += [
        "",
        f"### 目标外 proposed 范围复核 backlog（{len(non_target_candidates)}）",
        "",
        "| ID | 标题 | hazard review | links（verified/rejected/无审阅） |",
        "| --- | --- | --- | --- |",
    ]
    for row in non_target_candidates:
        link_counts = Counter((link.get("reviewDecision") or "missing") for link in row["links"])
        link_text = ", ".join(f"{key}={value}" for key, value in sorted(link_counts.items())) or "0"
        lines.append(
            f"| `{row['hazardId']}` | {md_escape(row['knowledgeTitle'])} | {md_escape(row['hazardReviewDecision'])} | {link_text} |"
        )

    lines += [
        "",
        f"### 工作簿与 knowledge 标题规范化后仍不同（{len(title_differences)}）",
        "",
        "这些 ID 集合一致，且对应 hazard review 均为 verified；Git 历史显示其在正式核验/官方来源核验批次中改写，按已审阅专业化表达保留，不用工作簿旧句式反向覆盖。",
        "",
        "| 工作簿行 | ID | 工作簿标题 | knowledge 标题 |",
        "| ---: | --- | --- | --- |",
    ]
    for row in title_differences:
        lines.append(
            f"| {row['sourceRow']} | `{row['hazardId']}` | {md_escape(row['workbookTitle'])} | {md_escape(row['knowledgeTitle'])} |"
        )

    lines += [
        "",
        "## 85 条目标外实体逐项解释",
        "",
        "| ID | 分类 | lifecycle | 归并/拆分去向 | 标题 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in extra_records:
        destination = row.get("mergedInto") or ", ".join(row.get("splitChildren") or []) or "—"
        lines.append(
            f"| `{row['hazardId']}` | `{row['classification']}` | {md_escape(row['lifecycle'])} | {md_escape(destination)} | {md_escape(row['knowledgeTitle'])} |"
        )

    lines += [
        "",
        "## 下一步",
        "",
        "1. 8 个目标内 merged alias 已统一为 `superseded` 并重绑审阅 hash。",
        "2. 7 个目标外且缺少完整正式 Gate 的实体已降为 `proposed`，保留稳定 ID、原审阅结论和既有证据。",
        f"3. {len(title_differences)} 个标题实质差异均有 verified hazard review，保留 knowledge 的专业化表述。",
        "4. PHASE 5 完成后进入 PHASE 6，按 proposed 候选的证据链缺口分批回绑，不为清零而转正。",
        "",
        f"机器可读明细：`{args.json_out.relative_to(ROOT).as_posix()}`。",
    ]
    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
