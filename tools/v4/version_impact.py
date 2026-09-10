# -*- coding: utf-8 -*-
"""
Phase 13: 新旧法规版本影响分析工具。

输入：knowledge/successions/*.json + knowledge/hazards/*.json + knowledge/clauses/*.json
输出：影响报告（stdout）：
  1) 每条 succession 的 old -> new
  2) 引用旧标准号/旧法规的 Hazard 清单（文本命中）
  3) 引用旧版本 lawVersion 的 Clause 清单
  4) 结论：哪些 Hazard / Clause 需要版本迁移修复，哪些 Link 需重审

原则：文本命中仅产生"候选"，语义判断由人工/后续 Phase 8 修复完成。
"""
import glob
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_dir(rel):
    out = []
    for f in glob.glob(os.path.join(ROOT, rel, "*.json")):
        with io.open(f, encoding="utf-8") as fh:
            out.append(json.load(fh))
    return out


STD_RE = re.compile(r"(GBZ?T?|AQ|TSG|GBJ|GA)\s?[-—–]?\s?(\d{3,5})(?:[-—–](\d{4}))?")


def norm(m):
    prefix = m.group(1).replace(" ", "").upper()
    num = m.group(2)
    year = m.group(3) or ""
    return "%s %s-%s" % (prefix, num, year) if year else "%s %s" % (prefix, num)


def main():
    succs = load_dir("knowledge/successions")
    hazards = load_dir("knowledge/hazards")
    clauses = load_dir("knowledge/clauses")
    lvs = {d["id"]: d for d in load_dir("knowledge/law-versions")}

    print("== successions (%d) ==" % len(succs))
    for s in succs:
        old = lvs.get(s["oldVersionId"], {})
        new = lvs.get(s["newVersionId"], {})
        old_std = old.get("documentNumber", s["oldVersionId"])
        new_std = new.get("documentNumber", s["newVersionId"])
        print("  %s -> %s [%s] eff=%s" % (old_std, new_std, s["relation"], s.get("effectiveDate", "")))
        print("     scope: %s" % s.get("scope", "")[:120])

    print()
    print("== version impact: hazard text hits ==")
    total = 0
    total_partial = 0
    for s in succs:
        old = lvs.get(s["oldVersionId"], {})
        old_doc = old.get("documentNumber", "")
        # 提取旧标准号的核心标识，如 "GB 9448-1999" -> ("GB 9448", "1999")
        m = STD_RE.search(old_doc or "")
        if not m:
            continue
        old_num = "%s %s" % (m.group(1).upper(), m.group(2))
        old_year = m.group(3)
        is_partial = s.get("relation") == "partially_replaces"
        hits = []
        for h in hazards:
            # 只扫 conditions/description/title（权威引用）；note 是追溯注释，不计入
            txt = " ".join(str(h.get(k, "")) for k in ("title", "description", "conditions"))
            # 1) 明确旧年份命中
            if old_year and re.search(re.escape(old_num) + r"[-—–]?" + re.escape(old_year), txt):
                hits.append((h["id"], "explicit-year", h.get("title", "")))
            # 2) 无年份但现行号也未被引用（说明可能沿用旧版含义）——仅提示，不做判定
        if hits:
            tag = "PARTIAL(superseded-still-current)" if is_partial else "FULL-REPLACED(migrate)"
            total += 0 if is_partial else len(hits)
            total_partial += len(hits) if is_partial else 0
            print("  [%s] %s referenced by %d hazard(s) [%s]:" % (old_num + "-" + (old_year or "?"), old_doc, len(hits), tag))
            for hid, kind, title in hits[:12]:
                print("      %s [%s] %s" % (hid, kind, title[:70]))

    # 无年份标准号命中（现行/旧版不明），只统计
    print()
    print("== clauses referencing superseded lawVersions (relation=replaces only) ==")
    cl_hits = 0
    replaced_olds = {s["oldVersionId"] for s in succs if s.get("relation") == "replaces"}
    for c in clauses:
        if c["lawVersionId"] in replaced_olds:
            print("  clause %s -> superseded %s | %s" % (c["id"], c["lawVersionId"], c.get("articlePath")))
            cl_hits += 1
    print("  clause hits:", cl_hits)

    print()
    print("TOTAL hazard hits requiring migration (full-replaced):", total)
    print("TOTAL hazard hits on partially-replaced (still current, no migration):", total_partial)
    print("NOTE: hits are candidates only; semantic adjudication required.")


if __name__ == "__main__":
    main()
