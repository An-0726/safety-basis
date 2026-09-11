# -*- coding: utf-8 -*-
"""Phase 8: 历史 Hazard / Link 结构质量系统扫描（候选生成）。

扫描项：
1. 重复/近似重复 Hazard（title/description 规范化相似度）
2. dangling refs（links -> hazard/clause；mergedInto -> hazard；clause -> lawVersion）
3. conditions 残留旧标准号（被 succession 替代的旧版）
4. note / measures 残留旧标准号
5. 空 category / places / keywords / aliases
6. FACT_NOT_HAZARD 句式（义务复述）候选
7. merged 实体仍被活跃引用
"""
import glob
import io
import json
import os
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")


def load_dir(rel):
    out = {}
    for f in glob.glob(os.path.join(KNOW, rel, "*.json")):
        with io.open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        key = d.get("id") or d.get("entityId") or os.path.splitext(os.path.basename(f))[0]
        out[key] = d
    return out


def norm(s):
    s = re.sub(r"[^\w\u4e00-\u9fff]", "", str(s))
    return s.lower()


def main():
    hazards = load_dir("hazards")
    links = load_dir("links")
    clauses = load_dir("clauses")
    lvs = load_dir("law-versions")
    succs = load_dir("successions")

    # 1. 近似重复（只统计双方都未被合并的“活跃重复”；已合并的条目 history 由 mergedInto 表达）
    seen = {}
    dups = []
    for hid, h in sorted(hazards.items()):
        if h.get("mergedInto"):
            continue
        key = norm(h.get("title", ""))[:60]
        if key in seen and len(key) >= 8:
            dups.append((seen[key], hid, h.get("title", "")[:50]))
        else:
            seen[key] = hid
    print("== active near-duplicate titles: %d ==" % len(dups))
    for a, b, t in dups[:30]:
        print("  %s == %s | %s" % (a, b, t))

    # 2. dangling refs
    dangling = []
    for kid, l in links.items():
        if l.get("hazardId") not in hazards:
            dangling.append(("link->hazard", kid, l.get("hazardId")))
        if l.get("clauseId") not in clauses:
            dangling.append(("link->clause", kid, l.get("clauseId")))
    for cid, c in clauses.items():
        if c.get("lawVersionId") not in lvs:
            dangling.append(("clause->lawVersion", cid, c.get("lawVersionId")))
    for hid, h in hazards.items():
        mi = h.get("mergedInto")
        if mi and mi not in hazards:
            dangling.append(("hazard->mergedInto", hid, mi))
    print("== dangling refs: %d ==" % len(dangling))
    for d in dangling[:20]:
        print("  ", d)

    # 3. conditions / note / measures 残留旧标准号
    replaced = {}
    for sid, s in succs.items():
        if s.get("relation") != "replaces":
            continue
        old = lvs.get(s.get("oldVersionId")) or {}
        old_doc = old.get("documentNumber", "")
        m = re.search(r"(GBZ?T?|AQ|TSG|GBJ|GA)\s?[-—–]?\s?(\d{3,5})(?:[-—–](\d{4}))?", old_doc or "")
        if m:
            replaced[m.group(1).upper() + " " + m.group(2) + "-" + (m.group(3) or "")] = s.get("newVersionId")
    stale = []
    for hid, h in hazards.items():
        for field in ("conditions", "note", "measures"):
            txt = str(h.get(field) or "")
            for old_std in replaced:
                if old_std not in txt:
                    continue
                # 说明版本沿革（“原依据 XX 已由 YY 替代”）属于正常记录，不算残留引用
                ctx = txt[max(0, txt.find(old_std) - 25): txt.find(old_std) + 45]
                if re.search(r"替代|作废|废止|旧版|原依据|已由|已被", ctx):
                    continue
                stale.append((hid, field, old_std, h.get("title", "")[:40]))
    print("== stale old-standard refs in hazard fields: %d ==" % len(stale))
    for s in stale[:40]:
        print("  ", s)

    # 4. 空字段
    empties = []
    for hid, h in hazards.items():
        for f in ("category", "places", "keywords", "aliases"):
            v = h.get(f)
            if v is None or v == "" or v == []:
                empties.append((hid, f))
    print("== empty fields: %d ==" % len(empties))
    for e in empties[:20]:
        print("  ", e)

    # 5. FACT_NOT_HAZARD 句式候选
    fact_cands = []
    for hid, h in hazards.items():
        t = h.get("title", "")
        if re.search(r"(必须|应当).{0,20}(未|不得|禁止)", t) or t.startswith("中的") or "必须配置" in t:
            fact_cands.append((hid, t[:60]))
    print("== obligation-restatement candidates: %d ==" % len(fact_cands))
    for c in fact_cands[:30]:
        print("  ", c)

    # 6. merged hazard 仍被活跃引用
    merged_refs = []
    for kid, l in links.items():
        h = hazards.get(l.get("hazardId")) or {}
        if h.get("mergedInto"):
            merged_refs.append((kid, l.get("hazardId"), h.get("mergedInto")))
    print("== links to merged hazards: %d ==" % len(merged_refs))
    for m in merged_refs[:10]:
        print("  ", m)

    # 7. 统计
    print()
    print("total hazards:", len(hazards), "links:", len(links), "clauses:", len(clauses))


if __name__ == "__main__":
    main()
