# -*- coding: utf-8 -*-
"""Phase 11 adapter：把 V4 knowledge 投影成网站前端（js/store.js）所需的数据结构。

前端契约（js/store.js + app.js）：
  data/manifest.json   schemaVersion=2 + hazardShards/clauseShards/files
  data/hazards/*.json  {records:[{id,...,basisRefs:[{clauseId,clauseShard,role}]}]}
  data/clauses/*.json  {records:[{id,article,quote,lawId,sourceUrl,checked,status}]}
  data/search-index.json / data/law-index.json / data/taxonomy.json

公开投影只包含通过共享链式 Gate 的 hazard 与其依据，未通过的实体不写入。

用法：py tools/v4/build_site_data.py [--out DIR]
默认输出到 candidate release 包（不触碰生产网站数据目录）。
"""
import argparse
import glob
import io
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from release_gate_core import evaluate_release_gate, load_dir  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")
DEFAULT_OUT = os.path.join(ROOT, "source", "releases", "v4-candidate-20260910")
SHARD_SIZE = 200

REGION = {"CN": "全国", "CN-32": "江苏", "CN-3201": "南京"}

_PUNCT = re.compile(r"[，。；：、（）()【】\[\]《》“”‘’'\"·•…—–_-]+")


def searchable(parts):
    """复现前端 js/search.js 的 normalize，保证 searchText 与查询词同形。"""
    s = " ".join(str(p) for p in parts if p)
    s = unicodedata.normalize("NFKC", s).lower()
    s = _PUNCT.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def rd(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def wr(p, d, indent=None):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, ensure_ascii=False, indent=indent, separators=None if indent else (",", ":"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    data = os.path.join(out, "data")

    hazards = load_dir(KNOW, "hazards")
    links = load_dir(KNOW, "links")
    clauses = load_dir(KNOW, "clauses")
    lvs = load_dir(KNOW, "law-versions")
    laws = load_dir(KNOW, "laws")

    gate = evaluate_release_gate(KNOW)
    eligible = gate.eligible_hazards
    link_decision = {k: v.get("decision") for k, v in gate.links.items()}

    # 展示用核验日期：部分记录由 V3 迁移而来，日期存在 migratedFromV3Verification.reviewedAt
    def review_date(r):
        return (r.get("checkedAt")
                or (r.get("migratedFromV3Verification") or {}).get("reviewedAt", ""))

    checked_at = {}
    for f in glob.glob(os.path.join(KNOW, "reviews", "hazards", "*.json")):
        r = rd(f)
        if r.get("entityId"):
            checked_at[r["entityId"]] = review_date(r)
    clause_checked = {}
    for f in glob.glob(os.path.join(KNOW, "reviews", "clauses", "*.json")):
        r = rd(f)
        if r.get("entityId"):
            clause_checked[r["entityId"]] = review_date(r)

    hazard_links = defaultdict(list)
    for kid, l in links.items():
        hazard_links[l.get("hazardId")].append(kid)

    # ---- 收集需要投影的 hazard 与其 basis ----
    pub = sorted(eligible)
    used_clauses = []          # 有序去重
    seen_clause = set()
    basis_of = {}              # hid -> [clauseId...]
    for hid in pub:
        refs = []
        for kid in hazard_links.get(hid, []):
            if link_decision.get(kid) != "verified":
                continue
            cid = links[kid].get("clauseId")
            if not cid or cid not in clauses:
                continue
            refs.append((cid, links[kid].get("role", "direct")))
            if cid not in seen_clause:
                seen_clause.add(cid)
                used_clauses.append(cid)
        # direct/fallback 优先展示
        order = {"direct": 0, "fallback": 1, "supporting": 2}
        refs.sort(key=lambda x: order.get(x[1], 9))
        basis_of[hid] = refs

    # ---- 分片（公开目录只保留投影，避免全量/未发布内容混入）----
    # Windows 下目录可能被浏览器/静态服务器短暂占用，删除失败不应中断构建；
    # 分片文件名固定，被覆盖写即可。
    import shutil
    for sub in ("hazards", "clauses"):
        p = os.path.join(data, sub)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
    hazard_shards, clause_shards = [], []
    h_shard_of = {}
    c_shard_of = {}
    for i in range(0, len(pub), SHARD_SIZE):
        sid = "h%04d" % (i // SHARD_SIZE)
        ids = pub[i:i + SHARD_SIZE]
        recs = []
        for hid in ids:
            h = hazards[hid]
            h_shard_of[hid] = sid
            recs.append({
                "id": hid,
                "title": h.get("title", ""),
                "description": h.get("description", ""),
                "measures": h.get("measures", ""),
                "note": h.get("note", ""),
                "category": h.get("category", ""),
                "places": h.get("places") or [],
                "aliases": h.get("aliases") or [],
                "keywords": h.get("keywords") or [],
                "mode": h.get("mode", ""),
                "status": "已核验",
                "checked": checked_at.get(hid, ""),
                "basisRefs": [{"clauseId": cid, "clauseShard": c_shard_of.get(cid, ""), "role": role}
                              for cid, role in basis_of[hid]],
            })
        hazard_shards.append({"id": sid, "url": "data/hazards/%s.json" % sid})
        wr(os.path.join(data, "hazards", sid + ".json"), {"schemaVersion": 2, "records": recs})

    for i in range(0, len(used_clauses), SHARD_SIZE):
        sid = "c%04d" % (i // SHARD_SIZE)
        ids = used_clauses[i:i + SHARD_SIZE]
        recs = []
        for cid in ids:
            c = clauses[cid]
            lv = lvs.get(c.get("lawVersionId")) or {}
            c_shard_of[cid] = sid
            recs.append({
                "id": cid,
                "article": c.get("articlePath") or c.get("clauseNumber") or "",
                "quote": c.get("quote", ""),
                "lawId": lv.get("lawId", ""),
                "sourceUrl": c.get("sourceUrl") or lv.get("sourceUrl") or "",
                "checked": clause_checked.get(cid, ""),
                "status": "现行有效" if (c.get("lifecycle") or "active") == "active" else "已废止",
                "region": REGION.get(c.get("jurisdictionCode") or "CN", "全国"),
            })
        clause_shards.append({"id": sid, "url": "data/clauses/%s.json" % sid})
        wr(os.path.join(data, "clauses", sid + ".json"), {"schemaVersion": 2, "records": recs})

    # basisRefs 里的 clauseShard 需回填（clause 分片在第一轮之后才确定）
    for i in range(0, len(pub), SHARD_SIZE):
        sid = "h%04d" % (i // SHARD_SIZE)
        p = os.path.join(data, "hazards", sid + ".json")
        payload = rd(p)
        for rec in payload["records"]:
            for b in rec["basisRefs"]:
                b["clauseShard"] = c_shard_of.get(b["clauseId"], "")
        wr(p, payload)

    # ---- search-index / law-index / taxonomy ----
    si = []
    cat_counter, place_counter = Counter(), Counter()
    mode_counter, level_counter = Counter(), Counter()
    law_clause_haz = defaultdict(lambda: defaultdict(set))   # lawId -> clauseId -> {hazardId}
    for hid in pub:
        h = hazards[hid]
        lns, stds, scopes, lvls = set(), set(), set(), set()
        for cid, role in basis_of[hid]:
            c = clauses[cid]
            lv = lvs.get(c.get("lawVersionId")) or {}
            law = laws.get(lv.get("lawId")) or {}
            nm = law.get("canonicalName") or law.get("officialName") or lv.get("officialName")
            if nm:
                lns.add(nm)
            if lv.get("documentNumber"):
                stds.add(lv["documentNumber"])
            scopes.add(REGION.get(c.get("jurisdictionCode") or "CN", "全国"))
            if law.get("documentKind"):
                lvls.add(law["documentKind"])
            law_clause_haz[lv.get("lawId")][cid].add(hid)
        si.append({
            "id": hid, "title": h.get("title", ""), "aliases": h.get("aliases") or [],
            "category": h.get("category", ""), "places": h.get("places") or [],
            "keywords": h.get("keywords") or [], "status": "已核验", "publishable": True,
            "excludedReason": None, "mode": h.get("mode", ""), "checked": checked_at.get(hid, ""),
            "levels": sorted(lvls), "scopes": sorted(scopes), "lawNames": sorted(lns),
            "stdNumbers": sorted(stds), "shard": h_shard_of[hid],
            "searchText": searchable([
                h.get("title", ""), " ".join(h.get("aliases") or []),
                " ".join(h.get("keywords") or []), h.get("description", ""),
                " ".join(sorted(lns)), " ".join(sorted(stds)), h.get("category", ""),
            ]),
        })
        if h.get("category"):
            cat_counter[h["category"]] += 1
        for pl in (h.get("places") or []):
            place_counter[pl] += 1
        if h.get("mode"):
            mode_counter[h["mode"]] += 1
        for x in lvls:
            level_counter[x] += 1

    law_index = []
    for lid in sorted(laws):
        law = laws[lid]
        # 法规库只列现行有效的法规身份；已被替代的历史身份由 succession 表达，
        # 不作为独立条目出现在公开投影里。
        if law.get("lifecycle") != "active":
            continue
        refs = []
        for cid, hids in sorted(law_clause_haz.get(lid, {}).items()):
            refs.append({"clauseId": cid, "clauseShard": c_shard_of.get(cid, ""),
                         "hazardIds": sorted(hids)})
        versions = []
        for vid, v in sorted(lvs.items()):
            if v.get("lawId") == lid:
                versions.append({"id": vid, "documentNumber": v.get("documentNumber", ""),
                                 "effectiveDate": v.get("effectiveDate", ""),
                                 "endDate": v.get("endDate", ""),
                                 "validityStatus": v.get("validityStatus", "unknown"),
                                 "sourceUrl": v.get("sourceUrl", "")})
        if not versions:
            continue
        active_ver = next((x for x in versions if x["validityStatus"] == "active"), versions[0])
        all_hids = sorted({hid for ref in refs for hid in ref["hazardIds"]})
        law_index.append({
            "id": lid,
            "name": law.get("canonicalName") or law.get("officialName") or lid,
            "aliases": law.get("aliases") or [],
            "level": law.get("documentKind", ""),
            "scope": REGION.get(law.get("jurisdictionCode") or "CN", "全国"),
            "status": "现行有效",
            "sourceUrl": active_ver.get("sourceUrl") or "",
            "issuer": law.get("issuer", ""),
            "effectiveDate": active_ver.get("effectiveDate", ""),
            "checked": "",
            "clauseCount": len(refs),
            "hazardCount": len(all_hids),
            "versions": versions,
            "clauseRefs": refs,
            "searchText": searchable([
                law.get("canonicalName") or law.get("officialName") or "",
                " ".join(law.get("aliases") or []), law.get("issuer", ""),
                " ".join(v.get("documentNumber", "") for v in versions),
            ]),
        })

    mf = {
        "schemaVersion": 2,
        "v4SchemaVersion": 3,
        "dataVersion": "2026.09.10.v4-candidate",
        "generatedAt": "2026-09-10",
        "publicScope": "国家法规标准优先，江苏／南京补充；只投影通过链式门禁的隐患",
        "counts": {"hazards": len(si), "laws": len(law_index), "lawVersions": len(lvs),
                   "clauses": len(used_clauses), "links": len(gate.eligible_links)},
        "sourceCounts": {"hazards": len(hazards), "laws": len(laws), "lawVersions": len(lvs),
                         "clauses": len(clauses), "links": len(links)},
        "health": {"verifiedHazards": len(si), "pendingHazards": 0,
                   "activeLaws": sum(1 for x in law_index if x["status"] == "现行有效"),
                   "pendingLaws": 0, "invalidReferences": 0,
                   "stagedHazards": len(hazards) - len(si), "stagedLaws": 0},
        "files": {"searchIndex": "data/search-index.json",
                  "lawIndex": "data/law-index.json",
                  "taxonomy": "data/taxonomy.json"},
        "hazardShards": hazard_shards,
        "clauseShards": clause_shards,
    }
    wr(os.path.join(data, "manifest.json"), mf, indent=1)
    wr(os.path.join(data, "search-index.json"), si)
    wr(os.path.join(data, "law-index.json"), law_index, indent=2)
    wr(os.path.join(data, "taxonomy.json"),
       {"categories": [c for c, _ in cat_counter.most_common()],
        "places": [p for p, _ in place_counter.most_common()],
        "lawLevels": sorted(level_counter),
        "hazardModes": sorted(mode_counter),
        "hazardStatuses": ["已核验"],
        "lawStatuses": sorted({x["status"] for x in law_index if x["status"]})})

    # 非发布视图单独存放，避免与公开投影混在一起
    internal = os.path.join(data, "_internal")
    wr(os.path.join(internal, "search-index-all.json"), [
        {"id": hid, "title": h.get("title", ""), "publishable": hid in set(pub)} for hid, h in sorted(hazards.items())
    ])

    print("网站数据已生成:", data)
    print("  hazards=%d laws=%d clauses=%d" % (len(si), len(law_index), len(used_clauses)))
    print("  分片: hazard %d / clause %d" % (len(hazard_shards), len(clause_shards)))


if __name__ == "__main__":
    main()
