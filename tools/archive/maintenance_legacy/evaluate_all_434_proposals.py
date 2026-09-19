# -*- coding: utf-8 -*-
"""深度遍历 434 条 proposed 候选，解析依据线索并匹配知识库现行条款。"""
from __future__ import annotations
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
KNOW = ROOT / "knowledge"

def load_dir(rel: str) -> dict[str, dict]:
    out = {}
    for p in (KNOW / rel).glob("*.json"):
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f)
        key = d.get("id") or d.get("entityId") or p.stem
        out[key] = d
    return out

def main():
    hazards = load_dir("hazards")
    clauses = load_dir("clauses")
    links = load_dir("links")
    lvs = load_dir("law-versions")
    laws = load_dir("laws")

    proposed = [h for h in hazards.values() if h.get("lifecycle") == "proposed"]
    print(f"Total proposed hazards: {len(proposed)}")

    # 建立现行条款索引：(norm(standard_num), clause_locator) -> clause
    # 建立版本库索引
    active_lvs = {k: v for k, v in lvs.items() if v.get("validityStatus") == "active"}
    print(f"Active law versions: {len(active_lvs)}")

    # 提取每个 proposed 的 note 中的修订直接依据
    # 典型格式：【2026-09-14新版明细】 修订状态：已修订；修订直接依据：GB 55036-2022《消防设施通用规范》；修订说明：...
    results = []
    
    basis_pattern = re.compile(r"修订直接依据[：:](.*?)(?:[；;]|修订说明[：:]|\n|$)")
    desc_clause_pattern = re.compile(r"(第[一二三四五六七八九十百0-9\.\s]+条(?:第[一二三四五六七八九十0-9]+款)?(?:第[一二三四五六七八九十0-9]+项)?)")

    for h in proposed:
        hid = h["id"]
        note = h.get("note", "")
        m = basis_pattern.search(note)
        revised_basis = m.group(1).strip() if m else ""
        
        results.append({
            "id": hid,
            "title": h.get("title", ""),
            "revised_basis": revised_basis,
            "proposalStatus": h.get("proposalStatus", ""),
            "sourceRow": h.get("sourceRow"),
            "category": h.get("category", ""),
            "note": note
        })

    with_basis = [r for r in results if r["revised_basis"]]
    print(f"Proposed with parsed revised_basis: {len(with_basis)} / {len(proposed)}")

    # 统计出现最频繁的 revised_basis
    basis_counts = Counter(r["revised_basis"] for r in with_basis)
    print("\nTop 25 revised_basis expressions:")
    for b, c in basis_counts.most_common(25):
        print(f"  {b}: {c}")

if __name__ == "__main__":
    main()
