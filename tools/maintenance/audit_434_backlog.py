# -*- coding: utf-8 -*-
"""深度审计当前 434 条 proposed 候选的状态、依据线索、重名及分类情况。"""
from __future__ import annotations
import io
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

def norm_text(s: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]", "", str(s)).lower()

def main():
    hazards = load_dir("hazards")
    clauses = load_dir("clauses")
    links = load_dir("links")
    lvs = load_dir("law-versions")

    proposed = [h for h in hazards.values() if h.get("lifecycle") == "proposed"]
    active = [h for h in hazards.values() if h.get("lifecycle") == "active"]

    print(f"Total proposed: {len(proposed)}, active: {len(active)}")

    # 1. 检查 proposed 与 active 的重名
    active_by_norm = defaultdict(list)
    for h in active:
        active_by_norm[norm_text(h.get("title"))].append(h)

    dup_with_active = []
    for h in proposed:
        k = norm_text(h.get("title"))
        if k in active_by_norm:
            dup_with_active.append((h, active_by_norm[k]))

    print(f"\n[1] Proposed with exact normalized title duplicate in Active: {len(dup_with_active)}")
    for p, act_list in dup_with_active:
        for a in act_list:
            print(f"  Proposed: {p['id']} | {p['title']}")
            print(f"    -> Active: {a['id']} | {a['title']}")

    # 2. 检查 proposed 内部的重名
    prop_by_norm = defaultdict(list)
    for h in proposed:
        prop_by_norm[norm_text(h.get("title"))].append(h)

    internal_dups = {k: v for k, v in prop_by_norm.items() if len(v) > 1}
    print(f"\n[2] Proposed internal title duplicate groups: {len(internal_dups)}")
    for k, v in internal_dups.items():
        ids = [h["id"] for h in v]
        print(f"  Title: {v[0]['title']} -> IDs: {ids}")

    # 3. proposalStatus 分布
    p_status = Counter(h.get("proposalStatus") for h in proposed)
    print(f"\n[3] Proposal Status distribution: {p_status}")

    # 4. 特殊候选检查
    extra_non_target = [h for h in proposed if h.get("proposalStatus") == "knowledge_extra_non_target_pending_scope_review"]
    print(f"\n[4] Extra non-target count: {len(extra_non_target)}")
    for h in extra_non_target:
        print(f"  {h['id']}: {h['title']} (sourceRow={h.get('sourceRow')}, note={h.get('note', '')[:60]})")

    catalog_only = [h for h in proposed if h.get("proposalStatus") == "basis_catalog_only"]
    print(f"\n[5] Catalog only count: {len(catalog_only)}")
    for h in catalog_only:
        print(f"  {h['id']}: {h['title']} (note={h.get('note', '')[:60]})")

    # 5. 分析法规/标准引用来源与提取
    law_pattern = re.compile(
        r"(GB\s?5\d{4}|GB\s?[1-4]\d{4}|GB/T\s?\d{3,5}|AQ\s?\d{3,5}|TSG\s?[A-Z0-9\-]+|"
        r"JGJ\s?\d+|DL/T\s?\d+|GA\s?\d+|HJ\s?\d+|HG/T\s?\d+|SZDB/Z\s?\d+|DB\d+/\w+|"
        r"中华人民共和国[\u4e00-\u9fa5]+法|江苏省[\u4e00-\u9fa5]+条例|南京市[\u4e00-\u9fa5]+条例|"
        r"危险化学品[\u4e00-\u9fa5]+条例|工贸企业[\u4e00-\u9fa5]+规定|消防法|安全生产法|特种设备安全法|"
        r"职业病防治法|环境保护法)"
    )

    law_to_hazards = defaultdict(list)
    unmatched_hazards = []
    for h in proposed:
        note = h.get("note", "")
        desc = h.get("description", "")
        title = h.get("title", "")
        combined = f"{title} {desc} {note}"
        matches = set(law_pattern.findall(combined))
        if matches:
            for m in matches:
                clean_m = re.sub(r"\s+", " ", m).strip()
                law_to_hazards[clean_m].append(h["id"])
        else:
            unmatched_hazards.append(h)

    print(f"\n[6] Referenced laws/standards in proposed: {len(law_to_hazards)} unique patterns")
    for l, hz_ids in sorted(law_to_hazards.items(), key=lambda x: len(x[1]), reverse=True)[:25]:
        print(f"  {l}: {len(hz_ids)} hazards")

    print(f"\n[7] Unmatched hazards (no standard pattern found in text): {len(unmatched_hazards)}")
    for h in unmatched_hazards[:10]:
        print(f"  {h['id']}: {h['title']} | note: {h.get('note', '')[:60]}")

if __name__ == "__main__":
    main()
