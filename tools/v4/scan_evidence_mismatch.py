# -*- coding: utf-8 -*-
"""扫描全部 link review 的 evidenceRefs 与 clause/lawVersion 匹配度。

规则（启发式，输出候选）：
- evidence.url 含 flk.npc.gov.cn / npc.gov.cn / gov.cn / mem.gov.cn / mee.gov.cn / samr.gov.cn 等官方域
- 按 URL 关键词与 clause 的 lawVersion officialName 比对，不一致则标记候选错配
"""
import glob
import io
import json
import os
import re
import sys

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


def main():
    reviews = load_dir(os.path.join("reviews", "links"))
    links = load_dir("links")
    clauses = load_dir("clauses")
    lvs = load_dir("law-versions")
    evidence = load_dir("evidence")

    candidates = []
    for kid, r in sorted(reviews.items()):
        refs = r.get("evidenceRefs") or []
        if not refs:
            continue
        link = links.get(kid) or {}
        cid = link.get("clauseId")
        c = clauses.get(cid) or {}
        lv = lvs.get(c.get("lawVersionId")) or {}
        law_name = lv.get("officialName", "")
        law_doc = lv.get("documentNumber", "")
        for e in refs:
            ev = evidence.get(e)
            if not ev:
                candidates.append((kid, "MISSING_EVIDENCE", e[:16], law_name[:40], ""))
                continue
            url = str(ev.get("url", ""))
            cand = None
            # 规则：law 是标准（GB/AQ/TSG）时 url 应是标准发布/正文来源
            if re.match(r"(GB|AQ|TSG|GBZ)", law_doc or law_name or ""):
                if "mee.gov.cn" in url or "gov.cn" in url or "samr.gov.cn" in url or "std.samr" in url or "openstd" in url:
                    cand = None
                else:
                    cand = "STD_EVIDENCE_URL_UNUSUAL"
            else:
                # 法规类：flk.npc / npc.gov.cn / gov.cn / mem.gov.cn 均可
                if re.search(r"(flk\.npc\.gov\.cn|npc\.gov\.cn|gov\.cn|mem\.gov\.cn|mee\.gov\.cn|samr\.gov\.cn)", url):
                    cand = None
                else:
                    cand = "LAW_EVIDENCE_URL_UNUSUAL"
            if cand:
                candidates.append((kid, cand, e[:16], law_name[:50], url[:90]))
    print("candidate mismatches:", len(candidates))
    for x in candidates:
        print(" -", x[0], "|", x[1], "| ev:", x[2], "| law:", x[3], "| url:", x[4])
    # 另列出易制毒/危废等专项 law 的 url 与 law 名，供人工核对
    print()
    print("== all evidence urls by clause law (unique) ==")
    seen = set()
    for kid, r in sorted(reviews.items()):
        for e in (r.get("evidenceRefs") or []):
            ev = evidence.get(e)
            if not ev:
                continue
            link = links.get(kid) or {}
            c = clauses.get(link.get("clauseId")) or {}
            lv = lvs.get(c.get("lawVersionId")) or {}
            key = (lv.get("officialName", "?"), str(ev.get("url", ""))[:80])
            if key in seen:
                continue
            seen.add(key)
            print(" law:", key[0][:45], "| url:", key[1])


if __name__ == "__main__":
    main()
