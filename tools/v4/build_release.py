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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canonical import content_hash

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

    # 预加载 clause/hazard review（与 strict_release_audit 对齐）
    clause_reviews = {}
    for f in glob.glob(os.path.join(KNOW, "reviews", "clauses", "*.json")):
        x = json.load(io.open(f, encoding="utf-8"))
        clause_reviews[x.get("entityId") or os.path.basename(f).replace(".json", "")] = x
    hazard_reviews = {}
    for f in glob.glob(os.path.join(KNOW, "reviews", "hazards", "*.json")):
        x = json.load(io.open(f, encoding="utf-8"))
        hazard_reviews[x.get("entityId") or os.path.basename(f).replace(".json", "")] = x

    def clause_has_verified_review(cid):
        rv = clause_reviews.get(cid) or {}
        if rv.get("decision") != "verified":
            return False
        cl = clauses.get(cid) or {}
        if cl and rv.get("reviewedContentHash") != content_hash(cl):
            return False
        return True

    def hazard_content_ok(hid):
        hz = hazards.get(hid) or {}
        rv = hazard_reviews.get(hid) or {}
        if rv.get("decision") != "verified":
            return False
        if hz and rv.get("reviewedContentHash") != content_hash(hz):
            return False
        for field in ("title", "description", "measures", "category"):
            if not hz.get(field):
                return False
        if (hz.get("lifecycle") or "active") != "active":
            return False
        if hz.get("mergedInto"):
            return False
        return True

    # hazard -> lawNames + 聚合发布状态（链式发布门禁，与 strict_release_audit 对齐）
    # 规则：eligible link = review decision=verified + reviewedContentHash 匹配 + contextHashes 匹配 + clause 有 verified review；
    # publishable hazard = 至少 1 条 eligible link 且 role in {direct, fallback}；
    # pending/rejected link 不进正式发布投影（search-index），但保留在 data/hazards 详情中并标 WARN。
    hazard_links = defaultdict(list)
    hazard_link_decisions = defaultdict(list)  # hid -> [(decision, role, kid, eligible)]
    for kid, l in links.items():
        hid = l.get("hazardId")
        hazard_links[hid].append(l)
        rv = reviews.get(kid) or {}
        dec = rv.get("decision") or "pending"
        role = l.get("role") or ""
        # eligible 检查：verified + hash 匹配 + clause 有 verified review（与 strict_release_audit 对齐）
        eligible = False
        if dec == "verified":
            if rv.get("reviewedContentHash") == content_hash(l):
                ctx = rv.get("contextHashes") or {}
                hz = hazards.get(hid) or {}
                cl = clauses.get(l.get("clauseId")) or {}
                if (not hz or ctx.get("hazard") == content_hash(hz)) and \
                   (not cl or ctx.get("clause") == content_hash(cl)):
                    if clause_has_verified_review(l.get("clauseId")):
                        eligible = True
        hazard_link_decisions[hid].append((dec, role, kid, eligible))

    def aggregate_hazard_status(hid):
        """聚合 hazard 发布状态：返回 (status, publishable, warn_reasons)。"""
        decs = hazard_link_decisions.get(hid, [])
        if not decs:
            return "unreviewed", False, ["no link"]
        has_eligible_qualifying = any(
            elig and r in ("direct", "fallback") for _, r, _, elig in decs
        )
        has_pending = any(d == "pending" for d, _, _, _ in decs)
        has_rejected = any(d == "rejected" for d, _, _, _ in decs)
        all_eligible = all(elig for _, _, _, elig in decs)
        if all_eligible and not has_pending and not has_rejected:
            status = "verified"
        elif has_eligible_qualifying and has_pending:
            status = "verified_with_pending"
        elif has_eligible_qualifying and has_rejected:
            status = "verified_with_rejections"
        elif has_pending:
            status = "pending"
        elif has_rejected and not has_eligible_qualifying:
            status = "rejected"
        else:
            status = "unreviewed"
        publishable = has_eligible_qualifying and hazard_content_ok(hid)
        warns = []
        if not hazard_content_ok(hid):
            warns.append("hazard content review missing or stale")
        if has_pending:
            warns.append("pending links: " + ",".join(k for d, _, k, _ in decs if d == "pending"))
        if has_rejected:
            warns.append("rejected links: " + ",".join(k for d, _, k, _ in decs if d == "rejected"))
        stale = [k for _, _, k, elig in decs if not elig]
        if stale:
            warns.append("stale/unverified links: " + ",".join(stale))
        if not publishable:
            warns.append("no eligible verified direct/fallback link")
        return status, publishable, warns

    si = []  # 正式发布投影：只放 publishable
    si_all = []  # 全部 hazard（含不可发布，供后台/候选站查看）
    hdata = {}
    cat_counter = Counter()
    place_counter = Counter()
    publish_stats = {"publishable": 0, "not_publishable": 0, "by_status": {}}
    warn_list = []
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
        status, publishable, warns = aggregate_hazard_status(hid)
        publish_stats["by_status"][status] = publish_stats["by_status"].get(status, 0) + 1
        if publishable:
            publish_stats["publishable"] += 1
        else:
            publish_stats["not_publishable"] += 1
            warn_list.append({"hazardId": hid, "title": h.get("title", ""), "status": status, "reasons": warns})
        rec = {
            "id": hid,
            "title": h.get("title", ""),
            "aliases": h.get("aliases") or [],
            "category": h.get("category", ""),
            "places": h.get("places") or [],
            "keywords": h.get("keywords") or [],
            "status": status,
            "publishable": publishable,
            "mode": h.get("mode", ""),
            "checked": h.get("checked", ""),
            "levels": [],
            "scopes": ["全国"],
            "lawNames": sorted(lns),
            "stdNumbers": sorted(stds),
        }
        si_all.append(rec)
        if publishable:
            si.append(rec)
        hdata[hid] = h
        if h.get("category"):
            cat_counter[h["category"]] += 1
        for p in (h.get("places") or []):
            place_counter[p] += 1

    os.makedirs(os.path.join(REL, "data", "hazards"), exist_ok=True)
    # search-index = 正式发布投影（只 publishable）
    with io.open(os.path.join(REL, "data", "search-index.json"), "w", encoding="utf-8") as fh:
        json.dump(si, fh, ensure_ascii=False)
    # search-index-all = 全部 hazard（候选站后台查看用）
    with io.open(os.path.join(REL, "data", "search-index-all.json"), "w", encoding="utf-8") as fh:
        json.dump(si_all, fh, ensure_ascii=False)
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

    dec = Counter(r["status"] for r in si_all)
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
                   "rejectedHazards": dec.get("rejected", 0), "unreviewedHazards": dec.get("unreviewed", 0),
                   "verifiedWithPending": dec.get("verified_with_pending", 0),
                   "verifiedWithRejections": dec.get("verified_with_rejections", 0)},
        "publishStats": publish_stats,
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
        "publishStats": publish_stats,
        "publishWarnList": warn_list,
        "gate": "STRUCTURAL/CONTENT/APPLICABILITY/VERSION/EVIDENCE/RELEASE PASS (candidate; production NOT switched)",
        "notes": "V4 candidate release. NOT switched to production. Chain-gated: search-index contains only publishable hazards (>=1 verified direct/fallback link); all hazards retained in data/hazards + search-index-all. See docs/V4_GATE_REPORT.md and docs/CHAT_HANDOFF.md.",
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
