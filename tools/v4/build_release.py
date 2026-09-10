# -*- coding: utf-8 -*-
"""Phase 18/19: 构建 V4 candidate release（不切 production）。

输出：source/releases/v4-candidate-20260910/
- data/search-index.json   搜索记录（hazard + lawNames + scope）
- data/hazards/*.json      hazard 详情
- data/law-index.json      法规目录（law + lawVersion 状态）
- data/taxonomy.json       分类/场所
- data/manifest.json       数据版本与健康摘要
- release.json             release 元信息（counts/state hash/gate 摘要）
- index.html / library.html / js / css   静态站（本地可打开）
"""
import glob
import hashlib
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")
REL = os.path.join(ROOT, "source", "releases", "v4-candidate-20260910")


def load_dir(rel):
    out = {}
    for f in glob.glob(os.path.join(KNOW, rel, "*.json")):
        with io.open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        key = d.get("id") or d.get("entityId") or os.path.splitext(os.path.basename(f))[0]
        out[key] = d
    return out


def state_hash(paths):
    h = hashlib.sha256()
    for p in sorted(paths):
        with io.open(p, "rb") as fh:
            h.update(p.encode("utf-8"))
            h.update(fh.read())
    return h.hexdigest()


def main():
    hazards = load_dir("hazards")
    links = load_dir("links")
    clauses = load_dir("clauses")
    lvs = load_dir("law-versions")
    laws = load_dir("laws")
    reviews = load_dir(os.path.join("reviews", "links"))

    # clause -> lawVersion -> law
    lv_law = {}
    for vid, v in lvs.items():
        lv_law[vid] = v.get("lawId")
    law_name = {lid: (l.get("name") or l.get("title")) for lid, l in laws.items()}

    # hazard -> lawNames + reviewStatus
    hazard_links = defaultdict(list)
    hazard_decision = {}
    for kid, l in links.items():
        hazard_links[l.get("hazardId")].append(l)
        hazard_decision[l.get("hazardId")] = (reviews.get(kid) or {}).get("decision") or "pending"

    si = []
    hdata = {}
    cat_counter = Counter()
    place_counter = Counter()
    for hid, h in hazards.items():
        lns = set()
        stds = set()
        for l in hazard_links.get(hid, []):
            c = clauses.get(l.get("clauseId")) or {}
            v = lvs.get(c.get("lawVersionId")) or {}
            nm = law_name.get(v.get("lawId"))
            if nm:
                lns.add(nm)
            if v.get("documentNumber"):
                stds.add(v["documentNumber"])
        rec = {
            "id": hid,
            "title": h.get("title", ""),
            "aliases": h.get("aliases") or [],
            "category": h.get("category", ""),
            "places": h.get("places") or [],
            "keywords": h.get("keywords") or [],
            "status": "已核验" if hazard_decision.get(hid) == "verified" else
                      ("待定" if hazard_decision.get(hid) == "pending" else
                       ("不适用" if hazard_decision.get(hid) == "rejected" else "未审")),
            "mode": h.get("mode", ""),
            "checked": h.get("checked", ""),
            "levels": [],
            "scopes": ["全国"],
            "lawNames": sorted(lns),
            "stdNumbers": sorted(stds),
        }
        si.append(rec)
        hdata[hid] = h
        if h.get("category"):
            cat_counter[h["category"]] += 1
        for p in (h.get("places") or []):
            place_counter[p] += 1

    os.makedirs(os.path.join(REL, "data", "hazards"), exist_ok=True)
    with io.open(os.path.join(REL, "data", "search-index.json"), "w", encoding="utf-8") as fh:
        json.dump(si, fh, ensure_ascii=False)
    for hid, h in hdata.items():
        with io.open(os.path.join(REL, "data", "hazards", hid + ".json"), "w", encoding="utf-8") as fh:
            json.dump(h, fh, ensure_ascii=False)

    # law-index
    law_index = []
    for lid, l in sorted(laws.items()):
        versions = []
        for vid, v in lvs.items():
            if v.get("lawId") == lid:
                versions.append({
                    "id": vid,
                    "documentNumber": v.get("documentNumber", ""),
                    "effectiveDate": v.get("effectiveDate", ""),
                    "lifecycle": v.get("lifecycle", "active"),
                    "status": v.get("status", ""),
                })
        law_index.append({"id": lid, "name": l.get("name") or l.get("title"),
                          "category": l.get("category", ""), "versions": versions})

    with io.open(os.path.join(REL, "data", "law-index.json"), "w", encoding="utf-8") as fh:
        json.dump(law_index, fh, ensure_ascii=False)
    with io.open(os.path.join(REL, "data", "taxonomy.json"), "w", encoding="utf-8") as fh:
        json.dump({"categories": [c for c, _ in cat_counter.most_common()],
                   "places": [p for p, _ in place_counter.most_common()]}, fh, ensure_ascii=False)

    dec = Counter(hazard_decision.values())
    rev_dec = Counter((reviews.get(kid) or {}).get("decision") or "" for kid in links)
    mf = {
        "schemaVersion": 3,
        "dataVersion": "2026.09.10.v4-candidate",
        "generatedAt": "2026-09-10",
        "publicScope": "国家法规标准优先，江苏／南京补充",
        "counts": {"hazards": len(si), "laws": len(laws), "lawVersions": len(lvs),
                   "clauses": len(clauses), "links": len(links)},
        "sourceCounts": {"hazards": len(hazards), "laws": len(laws), "lawVersions": len(lvs),
                         "clauses": len(clauses), "links": len(links)},
        "health": {"verifiedHazards": dec.get("verified", 0), "pendingHazards": dec.get("pending", 0),
                   "rejectedHazards": dec.get("rejected", 0), "unreviewedHazards": dec.get("", 0)},
    }
    with io.open(os.path.join(REL, "data", "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(mf, fh, ensure_ascii=False, indent=1)

    # release.json
    src_files = glob.glob(os.path.join(KNOW, "**", "*.json"), recursive=True)
    rel_json = {
        "formatVersion": "safety-release-v1",
        "asOf": "2026-09-10",
        "candidate": True,
        "production": False,
        "sourceStateHash": state_hash(src_files),
        "sourceCounts": {"laws": len(laws), "law_versions": len(lvs), "clauses": len(clauses),
                         "hazards": len(hazards), "links": len(links), "requirements": len(load_dir("requirements"))},
        "reviewStats": {"level": "hazard-level (dedup by hazardId)", "verified": dec.get("verified", 0),
                        "rejected": dec.get("rejected", 0), "pending": dec.get("pending", 0)},
        "reviewStatsByLink": {"level": "review-level (181 links)", "verified": rev_dec.get("verified", 0),
                              "rejected": rev_dec.get("rejected", 0), "pending": rev_dec.get("pending", 0)},
        "gate": "STRUCTURAL/CONTENT/APPLICABILITY/VERSION/EVIDENCE PASS; RELEASE pending final acceptance",
        "notes": "V4 candidate release. NOT switched to production. See docs/V4_GATE_REPORT.md and docs/CHAT_HANDOFF.md.",
    }
    with io.open(os.path.join(REL, "release.json"), "w", encoding="utf-8") as fh:
        json.dump(rel_json, fh, ensure_ascii=False, indent=1)

    print("release built:", REL)
    print("hazards:", len(si), "laws:", len(laws), "lawVersions:", len(lvs),
          "clauses:", len(clauses), "links:", len(links))
    print("reviewStats:", dict(dec))
    print("sourceStateHash:", rel_json["sourceStateHash"][:16])


if __name__ == "__main__":
    main()
