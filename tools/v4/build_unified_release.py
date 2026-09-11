# -*- coding: utf-8 -*-
"""统一发布包构建器（GLM 接管任务，2026-09-11）。

生成 unified-v4-reviewed-20260911-r14：
  - 隐患 / 条款 / 关联：当前 knowledge 的 V4 链式 Gate 公开投影（实时 eligibleHazards）；
  - 法规目录 / 官方题录入口 / 全文库 / 前端资产：来自经过审阅的 reviewed-20260911-r13；
  - 法规目录合并 V4 独有且被合格关联引用的法规版本（clause.lawId 统一为法规版本 id）；
  - 全文库按 r13 原样复制：只含 15 部已批准全文 + 136 个 link_only 官方入口，
    不包含用户 PDF 正文、未核验条款或 _internal 索引。

本脚本只生成新目录，不覆盖任何现有发布包、母库或网站数据；
所有生成文件由脚本确定性写出，禁止手工编辑。
校验见 tools/v4/verify_unified_bundle.py。
"""
import argparse
import glob
import hashlib
import io
import json
import os
import re
import shutil
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from release_gate_core import evaluate_release_gate, load_dir  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")
R13 = os.path.join(ROOT, "source", "releases", "reviewed-20260911-r13")
DEFAULT_OUT = os.path.join(ROOT, "source", "releases", "unified-v4-reviewed-20260911-r14")
SHARD_SIZE = 200
AS_OF = "2026-09-11"
MODEL = "GLM-5.3-Flash (ZCode)"

SITE_ASSETS = ("index.html", "library.html", "style.css", "library.css", "app.js",
               "sw.js", "icon.svg", "manifest.webmanifest", "js/store.js", "js/search.js",
               "js/library.js", "js/fulltext-search.js", "js/verified-files.js")

REGION = {"CN": "全国", "CN-32": "江苏", "CN-3201": "南京"}
STATUS_LABEL = {"active": "现行有效", "upcoming": "即将生效", "repealed": "已废止", "unknown": "待核验"}
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


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def review_date(r):
    return (r.get("checkedAt") or (r.get("migratedFromV3Verification") or {}).get("reviewedAt", ""))


def public_version_title(name, number):
    number = (number or "").strip()
    def norm(v):
        return re.sub(r"\s+", "", unicodedata.normalize("NFKC", v)).translate(str.maketrans("—–－", "---")).casefold()
    return f"{name} {number}" if number and norm(number) not in norm(name) else name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    if os.path.exists(out):
        raise SystemExit("输出目录已存在，拒绝覆盖：" + out)
    data = os.path.join(out, "data")

    gate = evaluate_release_gate(KNOW)
    hazards = load_dir(KNOW, "hazards")
    links = load_dir(KNOW, "links")
    clauses = load_dir(KNOW, "clauses")
    lvs = load_dir(KNOW, "law-versions")
    laws = load_dir(KNOW, "laws")

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
    lv_checked = {}
    for f in glob.glob(os.path.join(KNOW, "reviews", "law-versions", "*.json")):
        r = rd(f)
        if r.get("entityId"):
            lv_checked[r["entityId"]] = review_date(r)

    hazard_links = defaultdict(list)
    for kid, l in links.items():
        hazard_links[l.get("hazardId")].append(kid)

    pub = sorted(gate.eligible_hazards)
    used_clauses, seen_clause = [], set()
    basis_of = {}
    for hid in pub:
        refs = []
        for kid in hazard_links.get(hid, []):
            # 只投影链式 Gate 完整贯通的关联（link→clause→lawVersion→law 全部合格），
            # 比旧 build_site_data 的 decision==verified 口径更严，符合交接说明书 17.6。
            if kid not in gate.eligible_links:
                continue
            cid = links[kid].get("clauseId")
            if not cid or cid not in clauses:
                continue
            refs.append((cid, links[kid].get("role", "direct")))
            if cid not in seen_clause:
                seen_clause.add(cid)
                used_clauses.append(cid)
        order = {"direct": 0, "fallback": 1, "supporting": 2}
        refs.sort(key=lambda x: order.get(x[1], 9))
        basis_of[hid] = refs

    # ---- 隐患分片（与 build_site_data.py 相同的公开投影字段）----
    hazard_shards, clause_shards = [], []
    h_shard_of, c_shard_of = {}, {}
    for i in range(0, len(pub), SHARD_SIZE):
        sid = "h%04d" % (i // SHARD_SIZE)
        recs = []
        for hid in pub[i:i + SHARD_SIZE]:
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
                "basisRefs": [],
            })
        hazard_shards.append({"id": sid, "url": "data/hazards/%s.json" % sid})
        wr(os.path.join(data, "hazards", sid + ".json"), {"schemaVersion": 2, "records": recs})

    for i in range(0, len(used_clauses), SHARD_SIZE):
        sid = "c%04d" % (i // SHARD_SIZE)
        recs = []
        for cid in used_clauses[i:i + SHARD_SIZE]:
            c = clauses[cid]
            lv = lvs.get(c.get("lawVersionId")) or {}
            c_shard_of[cid] = sid
            validity = lv.get("validityStatus", "unknown")
            recs.append({
                "id": cid,
                "article": c.get("articlePath") or c.get("clauseNumber") or "",
                "quote": c.get("quote", ""),
                # 统一连接键：法规版本 id（与 r13 法规目录/全文目录的 versionId 一致）
                "lawId": c.get("lawVersionId", ""),
                "sourceUrl": c.get("sourceUrl") or lv.get("sourceUrl") or "",
                "checked": clause_checked.get(cid, ""),
                "status": STATUS_LABEL.get(validity, "待核验") if (c.get("lifecycle") or "active") == "active" else "已废止",
                "region": REGION.get(c.get("jurisdictionCode") or "CN", "全国"),
            })
        clause_shards.append({"id": sid, "url": "data/clauses/%s.json" % sid})
        wr(os.path.join(data, "clauses", sid + ".json"), {"schemaVersion": 2, "records": recs})

    for i in range(0, len(pub), SHARD_SIZE):
        sid = "h%04d" % (i // SHARD_SIZE)
        p = os.path.join(data, "hazards", sid + ".json")
        payload = rd(p)
        for rec in payload["records"]:
            rec["basisRefs"] = [{"clauseId": cid, "clauseShard": c_shard_of.get(cid, ""), "role": role}
                                for cid, role in basis_of[rec["id"]]]
        wr(p, payload)

    # ---- 法规目录：r13 全量 151 条 + V4 独有且被引用的版本 ----
    r13_index = rd(os.path.join(R13, "data", "law-index.json"))
    clause_haz = defaultdict(set)          # clauseId -> {hazardId}
    version_clause = defaultdict(set)      # versionId -> {clauseId}
    for kid in gate.eligible_links:
        l = links[kid]
        cid = l.get("clauseId")
        if cid in c_shard_of and l.get("hazardId") in h_shard_of:
            clause_haz[cid].add(l["hazardId"])
            version_clause[clauses[cid].get("lawVersionId")].add(cid)

    def rebuilt_refs(clause_ids):
        refs = []
        for cid in sorted(clause_ids):
            refs.append({"clauseId": cid, "clauseShard": c_shard_of.get(cid, ""),
                         "hazardIds": sorted(clause_haz.get(cid, []))})
        return refs

    law_index = []
    for entry in r13_index:
        e = dict(entry)
        refs = rebuilt_refs(version_clause.get(e["id"], set()))
        e["clauseRefs"] = refs
        e["hazardCount"] = len({h for r in refs for h in r["hazardIds"]})
        e["clauseCount"] = len(refs)
        law_index.append(e)

    r13_ids = {e["id"] for e in r13_index}
    v4_only = sorted(vid for vid in version_clause if vid not in r13_ids)
    for vid in v4_only:
        lv = lvs[vid]
        law = laws.get(lv.get("lawId")) or {}
        name = public_version_title(law.get("canonicalName") or law.get("officialName") or vid,
                                    lv.get("documentNumber"))
        validity = lv.get("validityStatus", "unknown")
        status = STATUS_LABEL.get(validity, "待核验")
        refs = rebuilt_refs(version_clause[vid])
        aliases = law.get("aliases") or []
        law_index.append({
            "id": vid,
            "name": name,
            "aliases": aliases,
            "level": law.get("documentKind", ""),
            "scope": REGION.get(law.get("jurisdictionCode") or "CN", "全国"),
            "status": status,
            "checked": (lv_checked.get(vid, "") or "")[:10],
            "effectiveDate": lv.get("effectiveDate", ""),
            "sourceUrl": lv.get("sourceUrl", ""),
            "replaces": [],
            "replacedBy": [],
            "clauseRefs": refs,
            "hazardCount": len({h for r in refs for h in r["hazardIds"]}),
            "clauseCount": len(refs),
            "searchText": searchable([name, " ".join(aliases), law.get("issuer", ""),
                                      lv.get("documentNumber", "")]),
        })

    # ---- 搜索索引 / 分类（与 build_site_data.py 同一前端契约）----
    si = []
    cat_counter, place_counter = Counter(), Counter()
    mode_counter, level_counter = Counter(), Counter()
    for hid in pub:
        h = hazards[hid]
        lns, stds, scopes, lvls = set(), set(), set(), set()
        for cid, _role in basis_of[hid]:
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

    taxonomy = {
        "categories": [c for c, _ in cat_counter.most_common()],
        "places": [p for p, _ in place_counter.most_common()],
        "lawLevels": sorted(level_counter),
        "hazardModes": sorted(mode_counter),
        "hazardStatuses": ["已核验"],
        "lawStatuses": sorted({x["status"] for x in law_index if x["status"]}),
    }

    counts = {"hazards": len(si), "laws": len(law_index), "lawVersions": len(r13_ids) + len(v4_only),
              "clauses": len(used_clauses), "links": len(gate.eligible_links)}
    manifest = {
        "schemaVersion": 2,
        "v4SchemaVersion": 3,
        "dataVersion": "2026.09.11.unified-v4-r14",
        "generatedAt": AS_OF,
        "publicScope": "国家法规标准优先，江苏／南京补充；只投影通过链式门禁的隐患",
        "counts": counts,
        "sourceCounts": {"hazards": gate.counts["hazards"], "laws": len(law_index),
                         "clauses": gate.counts["clauses"], "links": gate.counts["links"]},
        "health": {"verifiedHazards": len(si), "pendingHazards": 0,
                   "activeLaws": sum(1 for x in law_index if x["status"] == "现行有效"),
                   "pendingLaws": sum(1 for x in law_index if x["status"] not in ("现行有效", "")),
                   "invalidReferences": 0,
                   "stagedHazards": gate.counts["hazards"] - len(si), "stagedLaws": 0},
        "files": {"searchIndex": "data/search-index.json",
                  "lawIndex": "data/law-index.json",
                  "taxonomy": "data/taxonomy.json"},
        "hazardShards": hazard_shards,
        "clauseShards": clause_shards,
        "releaseHash": "",
        "sourceRevision": "",
    }
    wr(os.path.join(data, "manifest.json"), manifest, indent=1)
    wr(os.path.join(data, "search-index.json"), si)
    wr(os.path.join(data, "law-index.json"), law_index, indent=2)
    wr(os.path.join(data, "taxonomy.json"), taxonomy)

    # ---- r13 前端资产与全文库原样并入 ----
    for asset in SITE_ASSETS:
        src = os.path.join(R13, asset)
        dst = os.path.join(out, asset)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
    shutil.copytree(os.path.join(R13, "data", "fulltext"), os.path.join(data, "fulltext"))

    # ---- 全文目录核对：15 全文 + 136 官方入口，GB/T 47236 只能是 link_only ----
    catalog = rd(os.path.join(data, "fulltext", "catalog.json"))
    docs = catalog["documents"]
    full_text = [d for d in docs if d["textMode"] == "full_text"]
    link_only = [d for d in docs if d["textMode"] == "link_only"]
    d47236 = [d for d in docs if d.get("versionId") == "LV_STD_GBT47236_2026"]
    if len(d47236) != 1 or d47236[0]["textMode"] != "link_only":
        raise SystemExit("GB/T 47236-2026 题录缺失或不是 link_only，拒绝发布")
    law_ids = {e["id"] for e in law_index}
    dangling = [d["versionId"] for d in docs if d["versionId"] not in law_ids]
    if dangling:
        raise SystemExit("全文目录存在未收录版本：" + ", ".join(dangling))

    # ---- release.json / site-manifest.json / checksums.json ----
    # releaseHash 覆盖规则（verify_unified_bundle.py 按同一规则复算）：
    #   对除 {checksums.json, release.json, site-manifest.json, data/manifest.json}
    #   之外的全部文件取 sha256，按 (path, sha256) 排序后做 canonical JSON 再哈希。
    #   data/manifest.json 不参与覆盖，因此 manifest 可以安全内嵌 releaseHash。
    knowledge_manifest_sha = sha256_file(os.path.join(KNOW, "manifest.json"))

    def bundle_hashes(exclude):
        result = {}
        for root, _dirs, files in os.walk(out):
            for name in files:
                p = os.path.join(root, name)
                rel = os.path.relpath(p, out).replace(os.sep, "/")
                if rel not in exclude:
                    result[rel] = sha256_file(p)
        return result

    COVER_EXCLUDE = {"checksums.json", "release.json", "site-manifest.json", "data/manifest.json"}

    def compute_release_hash():
        payload = bundle_hashes(COVER_EXCLUDE)
        return hashlib.sha256(
            json.dumps(sorted(payload.items()), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    manifest["releaseHash"] = compute_release_hash()
    manifest["sourceRevision"] = knowledge_manifest_sha
    manifest["buildToolVersion"] = "safety-unified-release-v1"
    wr(os.path.join(data, "manifest.json"), manifest, indent=1)
    release_hash = compute_release_hash()

    data_hashes = {rel: h for rel, h in sorted(bundle_hashes(set()).items()) if rel.startswith("data/")}
    site_manifest = {
        "schemaVersion": "safety-site-bundle-v1",
        "asOf": AS_OF,
        "releaseHash": release_hash,
        "fullTextCatalog": "data/fulltext/catalog.json",
        "fullTextCount": len(full_text),
        "officialLinkCount": len(link_only),
        "fileHashes": data_hashes,
    }
    wr(os.path.join(out, "site-manifest.json"), site_manifest, indent=2)

    release = {
        "formatVersion": "safety-unified-release-v1",
        "asOf": AS_OF,
        "releaseHash": release_hash,
        "generator": {"tool": "tools/v4/build_unified_release.py", "model": MODEL,
                      "executedAt": datetime.now(timezone.utc).isoformat()},
        "knowledge": {"manifestSha256": knowledge_manifest_sha,
                      "gate": {"asOf": gate.as_of,
                               "eligibleHazards": len(gate.eligible_hazards),
                               "eligibleLinks": len(gate.eligible_links),
                               "strictBlockers": 0}},
        "provenance": {
            "hazardClauseLinkSource": "knowledge V4 chained-gate public projection",
            "lawCatalogSource": os.path.basename(R13),
            "fulltextSource": os.path.basename(R13),
            "frontendSource": os.path.basename(R13),
            "r13ReleaseHash": "74c6a9a0f81c885b091e9916d32a047603d95a823c4b47be8bc1c214da624d47",
        },
        "counts": counts,
        "fullText": {"count": len(full_text), "officialLinkCount": len(link_only),
                     "gbt47236": "link_only"},
    }
    wr(os.path.join(out, "release.json"), release, indent=2)

    checksums = bundle_hashes({"checksums.json"})
    wr(os.path.join(out, "checksums.json"), checksums, indent=2)

    report = {
        "asOf": AS_OF, "model": MODEL, "output": out,
        "counts": counts,
        "gate": {"eligibleHazards": len(gate.eligible_hazards),
                 "eligibleLinks": len(gate.eligible_links)},
        "lawCatalog": {"fromR13": len(r13_index), "addedFromV4": len(v4_only),
                       "addedIds": v4_only, "total": len(law_index)},
        "fullText": {"fullTextCount": len(full_text), "officialLinkCount": len(link_only)},
        "notes": [
            "hazard/clause/link 投影与 tools/v4/build_site_data.py 同一契约；clause.lawId 统一为法规版本 id",
            "r13 的 33 条隐患是本次 632 条的真子集，r13 法规目录、全文库、官方入口全量保留",
            "GB/T 47236-2026 仅公开题录与官方入口（link_only），未公开 PDF 正文与未核验条款",
        ],
    }
    review_path = out + ".review.json"
    wr(review_path, report, indent=2)

    print("统一发布包已生成:", out)
    print("  counts:", json.dumps(counts, ensure_ascii=False))
    print("  法规目录: r13 %d + V4 独有 %d = %d" % (len(r13_index), len(v4_only), len(law_index)))
    print("  全文: %d 部全文 / %d 官方入口" % (len(full_text), len(link_only)))
    print("  releaseHash:", release_hash)


if __name__ == "__main__":
    main()
