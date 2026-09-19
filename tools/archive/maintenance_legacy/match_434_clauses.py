# -*- coding: utf-8 -*-
"""使用 articlePath 精确匹配 434 条 proposed 与现行已核条款。"""
from __future__ import annotations
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
import openpyxl

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
KNOW = ROOT / "knowledge"
EXCEL_PATH = Path(r"D:\Desktop\隐患库_1929条_新版口径全部整改完成_20260914.xlsx")

def load_json_dir(rel: str) -> dict[str, dict]:
    out = {}
    for p in (KNOW / rel).glob("*.json"):
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f)
        key = d.get("id") or d.get("entityId") or p.stem
        out[key] = d
    return out

def norm_str(s: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]", "", str(s)).upper()

def main():
    hazards = load_json_dir("hazards")
    clauses = load_json_dir("clauses")
    links = load_json_dir("links")
    lvs = load_json_dir("law-versions")
    cr = load_json_dir("reviews/clauses")

    proposed = [h for h in hazards.values() if h.get("lifecycle") == "proposed"]
    active_hazards = {h["id"]: h for h in hazards.values() if h.get("lifecycle") == "active"}

    # 找出每个条款当前已被哪些 active hazard 引用
    active_hazards_by_clause = defaultdict(list)
    for l in links.values():
        if l.get("lifecycle") == "active":
            hid = l.get("hazardId")
            cid = l.get("clauseId")
            if hid in active_hazards:
                active_hazards_by_clause[cid].append(hid)

    # 索引 active + verified clauses
    verified_clauses = {}
    for cid, c in clauses.items():
        if c.get("lifecycle") != "active":
            continue
        lvid = c.get("lawVersionId")
        lv = lvs.get(lvid, {})
        if lv.get("validityStatus") != "active":
            continue
        r = cr.get(cid, {})
        if r.get("decision") != "verified":
            continue
        verified_clauses[cid] = c

    print(f"Verified active clauses: {len(verified_clauses)}")

    # 加载 Excel
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    sheet = wb["隐患明细_修订后"]
    headers = [cell.value for cell in sheet[1]]
    id_idx = headers.index("隐患ID")
    excel_rows = {}
    for r in range(2, sheet.max_row + 1):
        vals = [sheet.cell(r, c).value for c in range(1, len(headers) + 1)]
        hid = str(vals[id_idx]).strip() if vals[id_idx] else ""
        if hid:
            excel_rows[hid] = dict(zip(headers, vals))

    # 建立多维索引：
    # (norm(law_title_or_doc), norm(article_path)) -> clause
    clause_lookup = []
    for cid, c in verified_clauses.items():
        lvid = c.get("lawVersionId")
        lv = lvs.get(lvid, {})
        doc_num = lv.get("documentNumber") or ""
        law_title = lv.get("title") or ""
        art_path = c.get("articlePath") or ""

        clause_lookup.append({
            "cid": cid,
            "clause": c,
            "lawVersion": lv,
            "doc_num": doc_num,
            "law_title": law_title,
            "art_path": art_path,
            "norm_doc": norm_str(doc_num),
            "norm_title": norm_str(law_title),
            "norm_art": norm_str(art_path)
        })

    print(f"Built clause lookup with {len(clause_lookup)} entries.")

    matches = []
    for h in proposed:
        hid = h["id"]
        ex = excel_rows.get(hid, {})
        basis = str(ex.get("直接依据") or "")
        key_pts = str(ex.get("依据条款要点（修订，非原文摘录）") or "")
        rev_note = str(ex.get("修订说明") or "")
        h_note = str(h.get("note") or "")

        full_text = f"{basis} {key_pts} {rev_note} {h_note}"
        norm_full = norm_str(full_text)

        matched_c = []
        for item in clause_lookup:
            # 检查法规是否在文本中
            doc_matched = bool(item["norm_doc"] and item["norm_doc"] in norm_full)
            title_matched = bool(item["norm_title"] and item["norm_title"] in norm_full)
            if not (doc_matched or title_matched):
                continue

            # 检查条号是否在文本中
            # 例如 第三十三条，或者 5.1.1
            art = item["norm_art"]
            if art and len(art) >= 2 and art in norm_full:
                matched_c.append(item)

        if matched_c:
            matches.append((hid, h["title"], matched_c))

    print(f"\nProposed hazards matching verified active clauses: {len(matches)}")

    for hid, title, matched_items in matches[:25]:
        print(f"\n{hid}: {title}")
        for item in matched_items:
            cid = item["cid"]
            existing = active_hazards_by_clause.get(cid, [])
            doc = item["doc_num"] or item["law_title"]
            art = item["art_path"]
            quote = item["clause"].get("quote", "")[:40]
            print(f"  -> {cid} | {doc} | {art} | quote: {quote}")
            if existing:
                print(f"     [EXISTING ACTIVE HAZARD ON CLAUSE]: {existing}")

if __name__ == "__main__":
    main()
