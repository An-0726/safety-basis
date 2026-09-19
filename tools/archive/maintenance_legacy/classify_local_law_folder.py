# -*- coding: utf-8 -*-
"""保守整理本地法规资料文件夹，不修改用户原件。

输出逐文件 CSV/JSON/Markdown；只有哈希、已登记题录或明确新旧版关系能自动
下结论。其余统一进入 needs_status_verification，避免仅凭文件名误判效力。
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = Path(r"D:\Desktop\模板\111常用法规标准")
DEFAULT_OUTPUT = ROOT / "source" / "library" / "inventory" / "111-common-laws-20260913"

# 仅列已经明确查到新版的旧版；不能把“强条废止”混入这里。
REPLACED = {
    "GB185972001": "GB 18597-2023",
    "GB201012006": "GB 20101-2025",
    "GB300772013": "GB 30077-2023",
    "GBT257112010": "GB/T 25711-2023",
    "GBT25502016": "GB/T 2550-2025",
    "GB156072008": "GB 15607-2023",
    "GB144442006": "GB 14444-2025",
    "GB144432007": "GB 14443-2025（2026-08-01实施）",
    "GB65142008": "GB 6514-2023（2024-10-01实施）",
    "GB76912003": "GB 7691-2025（2026-05-01实施）",
    "GB322762015": "GB 32276-2025（2026-05-01实施）",
    "GBT138692017": "GB/T 13869-2026（按实施日期衔接）",
}

TRANSITION_CURRENT = {
    "AQ42282012": "现行至2026-10-31；AQ 4228-2025自2026-11-01实施",
    "GB177502012": "现行至2026-09-30；GB 17750-2025自2026-10-01实施",
}

UPCOMING = {
    "AQ42282025": "已发布，2026-11-01实施；届时全部代替AQ 4228-2012",
}

DRAFT_WORDS = ("征求意见稿", "编制说明", "修订说明")
REFERENCE_WORDS = ("检查表", "指导手册", "指南（试行）", "指南(试行)", "行动计划", "专家检查")
MISNAMED_OR_EXCERPT = {
    "GB15562.2-2020环境保护图形标志-固体废物贮存(处置)场.pdf": "文件实际为旧式危险废物标志牌附件，不是GB 15562.2-2020全文；危险废物识别标志应结合HJ 1276-2022及GB 15562.2-1995修改单",
}
CONTENT_IDENTIFIED_DRAFTS = {
    "《酸碱罐区设计规范》.pdf": "实际内容为团体标准编制说明/起草材料，不是正式标准文本",
    "涂装作业安全规程 涂层烘干室安全技术规定 .pdf": "实际封面标注征求意见稿，不作现行直接依据",
    "《化学化工实验室安全管理规范》（T_CCSAS+005-2019）.pdf": "文件封面标注报批稿，不作为正式发布文本",
}
TITLE_ONLY_REPLACED = {
    "纺织工业粉尘防爆安全规程32276-2015-gb-cd-300.pdf": "GB 32276-2025（2026-05-01实施）",
    "企业职工伤亡事故分类标准.pdf": "GB 6441-2025",
    "国家危险废物名录-危险废物名录.pdf": "《国家危险废物名录（2025年版）》",
    "TSG ZF001-2006 安全阀安全技术监察规程.pdf": "TSG 92-2026（2026-07-01实施）",
}
TITLE_ONLY_REFERENCE = {
    "冶金企业高温熔融金属安全现场检查指南.doc": "现场检查工作资料，不自动等同法规或强制标准",
    "工贸行业重点可燃性粉尘目录（2015版）.doc": "工作目录资料，需结合现行粉尘防爆法规标准使用",
    "省安委办关于进一步加强铝镁机加工企业涉爆粉尘（废屑）处置安全工作的指导意见.doc": "江苏工作指导文件，保留参考，不自动作为全国直接依据",
    "《DB4403T-80-2020-危险化学品中间仓库安全管理规范-》.pdf": "深圳地方标准，江苏项目原则上不直接适用",
}
TITLE_ONLY_EXCERPT = {
    "南京市危险化学品禁止目录.docx": "已由南京市危险化学品禁止、限制和控制目录（2023版）完整版本覆盖",
    "江宁区限控危化品.docx": "区域节选，已由南京市2023版完整目录覆盖",
    "危险化学品名称及其临界量.doc": "GB 18218相关内容节选，不作为独立法规全文",
}
PUBLICATION_HINTS = {
    "各类监控化学品目录": "LV_META_ABE468D077A3918268DE18EF",
    "气瓶搬运、装卸、储存和使用安全规定": "LV_STD_6AFAD79D40F83A7BC16016D4",
    "特种设备安全监察条例": "LV_NPC_ff8080816f3cbb3c016f40d306b705f3",
    "吸附法工业有机废气治理工程技术规范": "L013",
    "工贸企业粉尘防爆安全规定": "L006",
    "粉尘爆炸危险场所用除尘系统安全技术规范": "LV_STD_7E0C7C218E837C8E2A8EE80A",
    "江苏省安全生产条例": "L020",
    "危险废物收集贮存运输技术规范": "L027",
    "建筑灭火器配置设计规范": "L008",
    "南京市危险化学品禁止、限制和控制目录": "LV_REG_91248A606189B3E07013325D",
}
TOKEN_RE = re.compile(
    r"(?:GB(?:/|_|\s)?T|GBT|GB|AQ|HJ|XF|JGJ|TSG|DL/T|DLT|DB\s*32(?:/T|T)?|T[/ +_-]?(?:CCSAS|CAQI|CASEI|CCGA))"
    r"\s*[-—_+ ]?\s*\d+(?:\.\d+)?(?:\s*[-—_ ]\s*\d{4})?",
    re.I,
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(value: str) -> str:
    value = value.upper().replace("—", "-").replace("–", "-").replace("－", "-")
    return re.sub(r"[^A-Z0-9]", "", value)


def tokens(value: str) -> list[str]:
    return sorted({norm(x) for x in TOKEN_RE.findall(value)})


def publication_tokens() -> tuple[dict[str, list[dict]], dict[str, dict]]:
    rows = json.loads((ROOT / "source" / "publication" / "law-index.json").read_text(encoding="utf-8"))
    out: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        for token in tokens(" ".join([row.get("name", ""), *row.get("aliases", [])])):
            out[token].append(row)
    return out, {row["id"]: row for row in rows}


def db_index() -> tuple[dict[str, list[dict]], dict[str, list[dict]], dict[str, list[dict]]]:
    db = ROOT / "source" / "library" / "fulltext.sqlite3"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        by_hash: dict[str, list[dict]] = defaultdict(list)
        by_id: dict[str, list[dict]] = defaultdict(list)
        by_token: dict[str, list[dict]] = defaultdict(list)
        for row in conn.execute("SELECT document_id,title,version,current_status,review_status,sha256 FROM documents"):
            item = dict(row)
            by_hash[row["sha256"]].append(item)
            by_id[row["document_id"]].append(item)
            by_id[row["version"]].append(item)
            for token in tokens(row["title"] + " " + row["version"]):
                by_token[token].append(item)
        return by_hash, by_id, by_token
    finally:
        conn.close()


def classify(path: Path, digest: str, duplicate_rank: int, db_hashes: dict, db_ids: dict,
             db_tokens: dict, pub: dict, pub_ids: dict) -> dict:
    rel = path.relative_to(args_source).as_posix()
    name = path.name
    found = tokens(name)
    registered = [row for token in found for row in pub.get(token, [])]
    for needle, ident in PUBLICATION_HINTS.items():
        if needle in rel and ident in pub_ids:
            registered.append(pub_ids[ident])
    registered = list({row["id"]: row for row in registered}.values())
    db_docs = list(db_hashes.get(digest, []))
    for row in registered:
        db_docs.extend(db_ids.get(row["id"], []))
    for token in found:
        db_docs.extend(db_tokens.get(token, []))
    db_docs = list({(x["document_id"], x["version"]): x for x in db_docs}.values())

    if duplicate_rank:
        category, reason = "duplicate", "与同文件夹另一文件SHA-256完全相同"
    elif name in CONTENT_IDENTIFIED_DRAFTS:
        category, reason = "draft_or_explanatory", CONTENT_IDENTIFIED_DRAFTS[name]
    elif name in TITLE_ONLY_REPLACED:
        category, reason = "historical_replaced", f"内容识别为旧版，已被{TITLE_ONLY_REPLACED[name]}替代"
    elif name in TITLE_ONLY_REFERENCE:
        category, reason = "reference_material", TITLE_ONLY_REFERENCE[name]
    elif name in TITLE_ONLY_EXCERPT:
        category, reason = "misnamed_or_excerpt", TITLE_ONLY_EXCERPT[name]
    elif name in MISNAMED_OR_EXCERPT:
        category, reason = "misnamed_or_excerpt", MISNAMED_OR_EXCERPT[name]
    elif any(word in name or word in rel for word in DRAFT_WORDS):
        category, reason = "draft_or_explanatory", "征求意见稿或编制/修订说明，不作现行直接依据"
    else:
        transition = next((TRANSITION_CURRENT[token] for token in found if token in TRANSITION_CURRENT), "")
        upcoming = next((UPCOMING[token] for token in found if token in UPCOMING), "")
        old = next((REPLACED[token] for token in found if token in REPLACED), "")
        if transition:
            category = "current_imported" if db_docs else "current_transition"
            reason = transition + ("；原件已入私有全文库" if db_docs else "")
        elif upcoming:
            category = "upcoming_imported" if db_docs else "upcoming_version"
            reason = upcoming + ("；原件已入私有全文库" if db_docs else "")
        elif old:
            category, reason = "historical_replaced", f"明确存在后续版本：{old}"
        elif db_docs:
            current = any(x["current_status"] in {"现行", "现行使用中", "current", "active"}
                          or x["current_status"].startswith(("现行有效", "过渡期现行")) for x in db_docs)
            category = "current_imported" if current else "imported_reference"
            exact = digest in db_hashes
            reason = ("原件SHA-256已存在私有全文库" if exact else "同一法规/版本身份已存在私有全文库（本文件为不同载体或扫描副本）") + "；效力沿用库内审阅状态"
        elif any(word in name or word in rel for word in REFERENCE_WORDS):
            category, reason = "reference_material", "指南、手册或检查表；可作工作资料，不能自动等同现行法规标准"
        elif registered:
            category, reason = "metadata_only", "已在173项公开目录登记，但本文件尚未通过全文导入与效力复核"
        else:
            category, reason = "needs_status_verification", "不能仅凭文件名确认现行性、适用范围或版本"

    return {
        "category": category,
        "relativePath": rel,
        "extension": path.suffix.lower(),
        "sizeBytes": path.stat().st_size,
        "sha256": digest,
        "duplicateOf": "",
        "identifiedTokens": "; ".join(found),
        "publicationIds": "; ".join(dict.fromkeys(row["id"] for row in registered)),
        "libraryDocuments": "; ".join(f'{x["document_id"]} {x["version"]}' for x in db_docs),
        "reason": reason,
    }


def main() -> int:
    global args_source
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    ns = ap.parse_args()
    args_source = ns.source.resolve()
    if not args_source.is_dir():
        raise SystemExit(f"资料文件夹不存在：{args_source}")

    files = sorted((p for p in args_source.rglob("*") if p.is_file()), key=lambda p: p.as_posix().casefold())
    digests = {p: sha256(p) for p in files}
    groups: dict[str, list[Path]] = defaultdict(list)
    for path, digest in digests.items():
        groups[digest].append(path)

    pub, pub_ids = publication_tokens()
    db_hashes, db_ids, db_tokens = db_index()
    rows = []
    for path in files:
        group = groups[digests[path]]
        row = classify(path, digests[path], group.index(path), db_hashes, db_ids, db_tokens, pub, pub_ids)
        if group.index(path):
            row["duplicateOf"] = group[0].relative_to(args_source).as_posix()
        rows.append(row)

    ns.output.parent.mkdir(parents=True, exist_ok=True)
    csv_path = ns.output.with_suffix(".csv")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    json_path = ns.output.with_suffix(".json")
    json_path.write_text(json.dumps({"source": str(args_source), "files": len(rows), "rows": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    counts = Counter(row["category"] for row in rows)
    lines = ["# 111常用法规标准逐文件整理", "", f"- 原文件：{len(rows)} 个（未移动、未删除）",
             f"- 唯一SHA-256：{len(groups)} 个", f"- 完全重复：{sum(len(v)-1 for v in groups.values())} 个", "", "## 分类统计", ""]
    labels = {
        "current_imported": "已入私有全文库且库内状态现行/过渡期现行",
        "current_transition": "过渡期仍现行、待导入",
        "upcoming_version": "已发布尚未实施",
        "upcoming_imported": "已发布尚未实施且全文已入库",
        "imported_reference": "已入全文库但不作为现行直接依据",
        "metadata_only": "已有目录题录、全文仍待处理",
        "historical_replaced": "明确被新版替代的历史版本",
        "draft_or_explanatory": "征求意见稿/编制说明",
        "reference_material": "指南、手册、检查表等工作资料",
        "misnamed_or_excerpt": "文件名/内容不一致或仅为节选",
        "duplicate": "完全重复文件",
        "needs_status_verification": "需官方效力/版本核验",
    }
    for key in labels:
        lines.append(f"- {labels[key]}：{counts[key]}")
    lines += ["", "## 使用原则", "", "`needs_status_verification` 不表示已失效，只表示自动程序没有足够证据下结论。GB 50016等部分强制性条文调整的标准，必须分整本状态和条款状态判断。", ""]
    ns.output.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(json.dumps({"files": len(rows), "uniqueHashes": len(groups), "counts": counts, "csv": str(csv_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
