# -*- coding: utf-8 -*-
"""构建 V4 candidate release（不切 production）。

输出：source/releases/v4-candidate-20260910/
- data/search-index.json      公开发布投影：只含共享 Gate 判定 publishable=true 的 hazard
- data/_internal/search-index-all.json  后台全量：所有 hazard，标注 publishable / excludedReason
- data/_internal/hazards/*.json         全量 hazard 详情（compact JSON，内部审计视图，不随公开站点发布）
- data/law-index.json         法规目录（law canonicalName + lawVersion validityStatus）
- data/taxonomy.json          分类/场所
- data/manifest.json          数据版本与健康摘要
- release.json                release 元信息（counts/state hash/gate 摘要）

公开目录下的 hazards/ 与 clauses/ 分片由 tools/v4/build_site_data.py 生成，
只包含通过链式 Gate 的隐患及其依据。

本脚本不再自行实现任何门禁规则：是否 publishable 完全由共享核心
release_gate_core.evaluate_release_gate 决定，避免与 strict_release_audit 漂移。
"""
import glob
import hashlib
import io
import json
import os
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from release_gate_core import evaluate_release_gate, load_dir  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")
REL = os.path.join(ROOT, "source", "releases", "v4-candidate-20260910")


def state_hash(paths):
    h = hashlib.sha256()
    for p in sorted(paths):
        with io.open(p, "rb") as fh:
            h.update(p.encode("utf-8"))
            h.update(fh.read())
    return h.hexdigest()


def law_display_name(law):
    """Law 名称优先 canonicalName，再 fallback 到其他名称字段。"""
    return law.get("canonicalName") or law.get("name") or law.get("title") or law.get("officialName") or law.get("id")


def main():
    hazards = load_dir(KNOW, "hazards")
    links = load_dir(KNOW, "links")
    clauses = load_dir(KNOW, "clauses")
    lvs = load_dir(KNOW, "law-versions")
    laws = load_dir(KNOW, "laws")

    # 共享链式 Gate：唯一的判定来源
    gate = evaluate_release_gate(KNOW)
    eligible_hazards = gate.eligible_hazards

    # clause -> lawVersion -> law 名称/文号
    lv_law = {vid: v.get("lawId") for vid, v in lvs.items()}
    law_name = {lid: law_display_name(l) for lid, l in laws.items()}

    hazard_links = defaultdict(list)
    for kid, l in links.items():
        hazard_links[l.get("hazardId")].append(kid)

    def excluded_reason(hid):
        """后台全量视图用：说明该 hazard 为何不公开发布。"""
        hv = gate.hazards.get(hid, {})
        if not hv.get("active", True):
            return "lifecycle_not_active"
        if hv.get("merged"):
            return "merged_into_another_hazard"
        if not hv.get("content_ok"):
            return "content_gate_failed:" + ";".join(hv.get("reasons", []))
        return "no_eligible_direct_or_fallback_link"

    def display_status(hid):
        """仅供展示的状态标签；publishable 判定以共享 Gate 为准。"""
        if hid in eligible_hazards:
            return "eligible"
        decs = [gate.links[k]["decision"] for k in hazard_links.get(hid, []) if k in gate.links]
        if not decs:
            return "no_link"
        if all(d == "rejected" for d in decs):
            return "rejected"
        if any(d == "pending" for d in decs):
            return "pending"
        return "not_eligible"

    si = []       # 公开发布投影
    si_all = []   # 后台全量
    hdata = {}
    cat_counter = Counter()
    place_counter = Counter()
    publish_stats = {"publishable": 0, "not_publishable": 0, "by_status": Counter()}
    warn_list = []

    for hid, h in hazards.items():
        lns, stds = set(), set()
        for kid in hazard_links.get(hid, []):
            l = links.get(kid, {})
            c = clauses.get(l.get("clauseId")) or {}
            v = lvs.get(c.get("lawVersionId")) or {}
            nm = law_name.get(v.get("lawId"))
            if nm:
                lns.add(nm)
            if v.get("documentNumber"):
                stds.add(v["documentNumber"])
        publishable = hid in eligible_hazards
        status = display_status(hid)
        publish_stats["by_status"][status] += 1
        if publishable:
            publish_stats["publishable"] += 1
        else:
            publish_stats["not_publishable"] += 1
            warn_list.append({"hazardId": hid, "title": h.get("title", ""),
                              "status": status, "excludedReason": excluded_reason(hid)})
        rec = {
            "id": hid,
            "title": h.get("title", ""),
            "aliases": h.get("aliases") or [],
            "category": h.get("category", ""),
            "places": h.get("places") or [],
            "keywords": h.get("keywords") or [],
            "status": status,
            "publishable": publishable,
            "excludedReason": None if publishable else excluded_reason(hid),
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

    # 全量 hazard 正文属内部审计视图，放到 _internal/，公开目录留给网站投影分片
    # （由 tools/v4/build_site_data.py 生成，只含通过链式 Gate 的隐患）。
    os.makedirs(os.path.join(REL, "data", "_internal", "hazards"), exist_ok=True)
    with io.open(os.path.join(REL, "data", "search-index.json"), "w", encoding="utf-8") as fh:
        json.dump(si, fh, ensure_ascii=False)
    with io.open(os.path.join(REL, "data", "_internal", "search-index-all.json"), "w", encoding="utf-8") as fh:
        json.dump(si_all, fh, ensure_ascii=False)
    # hazard 文件用 compact JSON（无缩进）
    for hid, h in hdata.items():
        with io.open(os.path.join(REL, "data", "_internal", "hazards", hid + ".json"), "w", encoding="utf-8") as fh:
            json.dump(h, fh, ensure_ascii=False, separators=(",", ":"))

    # law-index：名称优先 canonicalName；版本效力必须用 validityStatus
    law_index = []
    for lid, l in sorted(laws.items()):
        versions = []
        for vid, v in sorted(lvs.items()):
            if v.get("lawId") == lid:
                versions.append({
                    "id": vid,
                    "documentNumber": v.get("documentNumber", ""),
                    "effectiveDate": v.get("effectiveDate", ""),
                    "endDate": v.get("endDate", ""),
                    "validityStatus": v.get("validityStatus", "unknown"),
                })
        law_index.append({
            "id": lid,
            "name": law_display_name(l),
            "category": l.get("category", ""),
            "issuer": l.get("issuer", ""),
            "versions": versions,
        })
    with io.open(os.path.join(REL, "data", "law-index.json"), "w", encoding="utf-8") as fh:
        json.dump(law_index, fh, ensure_ascii=False, indent=2)
    with io.open(os.path.join(REL, "data", "taxonomy.json"), "w", encoding="utf-8") as fh:
        json.dump({"categories": [c for c, _ in cat_counter.most_common()],
                   "places": [p for p, _ in place_counter.most_common()]}, fh, ensure_ascii=False)

    dec = Counter(r["status"] for r in si_all)
    rev_dec = Counter(gate.links[k]["decision"] for k in gate.links)
    link_total = len(gate.links)
    mf = {
        "schemaVersion": 3,
        "dataVersion": "2026.09.10.v4-candidate",
        "generatedAt": "2026-09-10",
        "publicScope": "国家法规标准优先，江苏／南京补充",
        "counts": {"hazards": len(si), "laws": len(laws), "lawVersions": len(lvs),
                   "clauses": len(clauses), "links": len(links)},
        "sourceCounts": {"hazards": len(hazards), "laws": len(laws), "lawVersions": len(lvs),
                         "clauses": len(clauses), "links": len(links)},
        "health": {"eligibleHazards": dec.get("eligible", 0), "pendingHazards": dec.get("pending", 0),
                   "rejectedHazards": dec.get("rejected", 0), "noLinkHazards": dec.get("no_link", 0),
                   "notEligibleHazards": dec.get("not_eligible", 0)},
        "publishStats": {"publishable": publish_stats["publishable"],
                         "notPublishable": publish_stats["not_publishable"],
                         "byStatus": dict(publish_stats["by_status"])},
    }
    with io.open(os.path.join(REL, "data", "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(mf, fh, ensure_ascii=False, indent=1)

    src_files = glob.glob(os.path.join(KNOW, "**", "*.json"), recursive=True)
    rel_json = {
        "formatVersion": "safety-release-v1",
        "asOf": gate.as_of,
        "candidate": True,
        "production": False,
        "sourceStateHash": state_hash(src_files),
        "sourceCounts": {"laws": len(laws), "law_versions": len(lvs), "clauses": len(clauses),
                         "hazards": len(hazards), "links": len(links),
                         "requirements": len(load_dir(KNOW, "requirements"))},
        "reviewStats": {"level": "hazard-level (dedup by hazardId)",
                        "publishableHazards": publish_stats["publishable"],
                        "notPublishableHazards": publish_stats["not_publishable"]},
        "reviewStatsByLink": {"level": "review-level (%d links)" % link_total,
                              "verified": rev_dec.get("verified", 0),
                              "rejected": rev_dec.get("rejected", 0),
                              "pending": rev_dec.get("pending", 0)},
        "gate": "STRUCTURAL/CONTENT/APPLICABILITY/VERSION/EVIDENCE checked by shared release_gate_core",
        "strictGate": {"eligibleHazards": len(eligible_hazards),
                       "eligibleLinks": len(gate.eligible_links)},
        "notes": ("V4 candidate release. NOT switched to production. Chain-gated via shared "
                  "release_gate_core: search-index contains only publishable hazards "
                  "(>=1 eligible direct/fallback link through clause->lawVersion->law); "
                  "all hazards retained under data/_internal/ with excludedReason. "
                  "Public shards are written by tools/v4/build_site_data.py. "
                  "See docs/V4_GATE_REPORT.md."),
    }
    with io.open(os.path.join(REL, "release.json"), "w", encoding="utf-8") as fh:
        json.dump(rel_json, fh, ensure_ascii=False, indent=1)

    print("release built:", REL)
    print("publishable hazards:", len(si), "of", len(hazards),
          "| eligible links:", len(gate.eligible_links), "of", link_total)
    print("reviewStatsByLink:", rel_json["reviewStatsByLink"])
    print("sourceStateHash:", rel_json["sourceStateHash"][:16])


if __name__ == "__main__":
    main()
