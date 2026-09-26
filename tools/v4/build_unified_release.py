# -*- coding: utf-8 -*-
"""统一正式发布包构建器。

正式公开站只投影满足当前日期链式 Gate 的内容：

  knowledge/laws -> knowledge/law-versions -> knowledge/clauses
      -> knowledge/links -> knowledge/hazards

``source/publication`` 只提供公开全文、官方入口和同 ID 的来源元数据；它不再
单独创造正式法规卡。``lifecycle=proposed`` 的候选继续保存在 ``knowledge/``
供审核，但不进入正式发布包。

私有 PDF、SQLite、OCR、未核验条款和内部索引不会进入公开发布包。
所有生成文件由脚本确定性写出，禁止手工编辑。
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
from datetime import date, datetime, timezone

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from presentation import (  # noqa: E402
    SCENE_TAG_OPTIONS,
    display_level,
    presentation_review,
    project_hazard,
    raw_law_level,
    searchable,
)
from release_gate_core import evaluate_release_gate, load_dir  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")
PUBLICATION = os.path.join(ROOT, "source", "publication")
WEB = os.path.join(ROOT, "web")
DEFAULT_OUT = os.path.join(ROOT, "source", "releases", "current")
SHARD_SIZE = 200
AS_OF = "2026-09-14"
DATA_VERSION = "2026.09.14.current"
MODEL = "deterministic local build"

SITE_ASSETS = ("index.html", "library.html", "style.css", "library.css", "stage3.css", "app.js",
               "sw.js", "icon.svg", "manifest.webmanifest", "js/store.js", "js/search.js",
               "js/search-vocabulary.js",
               "js/library.js", "js/fulltext-search.js", "js/verified-files.js")

REGION = {"CN": "全国", "CN-32": "江苏", "CN-3201": "南京"}
STATUS_LABEL = {"active": "现行有效", "upcoming": "即将生效", "repealed": "已废止", "unknown": "待核验"}
def rd(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def wr(p, d, indent=None):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, ensure_ascii=False, indent=indent,
                  separators=None if indent else (",", ":"))


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def review_date(r):
    if not r:
        return "2026-09-19"
    d = (r.get("checkedAt") or
         (r.get("migratedFromV3Verification") or {}).get("reviewedAt", "") or
         r.get("reviewedAt", "") or
         r.get("createdAt", ""))
    return d or "2026-09-19"


def normalized_conditions(hazard_id, hazard):
    """Return source conditions without inventing or coercing applicability text."""
    value = hazard.get("conditions")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise SystemExit(
            "knowledge/hazards/%s.json 的 conditions 必须是字符串、null 或缺失，实际为 %s"
            % (hazard_id, type(value).__name__)
        )
    return value


def public_version_title(name, number):
    number = (number or "").strip()

    def norm(v):
        return (re.sub(r"\s+", "", unicodedata.normalize("NFKC", v))
                .translate(str.maketrans("—–－", "---")).casefold())

    return f"{name} {number}" if number and norm(number) not in norm(name) else name


def main():
    global AS_OF, DATA_VERSION
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--as-of", dest="as_of", default=AS_OF)
    ap.add_argument("--data-version", dest="data_version", default=DATA_VERSION)
    ap.add_argument("--overwrite", action="store_true", help="若输出目录已存在则清空覆盖")
    args = ap.parse_args()
    AS_OF = args.as_of
    DATA_VERSION = args.data_version
    try:
        as_of_date = date.fromisoformat(AS_OF)
    except ValueError as exc:
        raise SystemExit("--as-of 必须是 YYYY-MM-DD：" + AS_OF) from exc

    out = os.path.abspath(args.out)
    if os.path.exists(out):
        if args.overwrite:
            import stat
            def _handle_ro(func, path, exc):
                try:
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                except Exception:
                    pass
            try:
                shutil.rmtree(out, onexc=_handle_ro)
            except Exception:
                shutil.rmtree(out, ignore_errors=True)
        else:
            raise SystemExit("输出目录已存在，拒绝覆盖：" + out)
    data = os.path.join(out, "data")

    gate = evaluate_release_gate(KNOW, as_of_date)
    hazards = load_dir(KNOW, "hazards")
    hazard_conditions = {
        hid: normalized_conditions(hid, hazard)
        for hid, hazard in hazards.items()
    }
    links = load_dir(KNOW, "links")
    clauses = load_dir(KNOW, "clauses")
    lvs = load_dir(KNOW, "law-versions")
    laws = load_dir(KNOW, "laws")
    publication_by_id = {
        e["id"]: e for e in rd(os.path.join(PUBLICATION, "law-index.json"))
    }
    hazard_presentation = {
        hid: project_hazard(hazard, hazard_id=hid) for hid, hazard in hazards.items()
    }

    checked_at = {}
    for f in sorted(glob.glob(os.path.join(KNOW, "reviews", "hazards", "*.json"))):
        r = rd(f)
        if r.get("entityId"):
            checked_at[r["entityId"]] = review_date(r)
    clause_checked = {}
    for f in sorted(glob.glob(os.path.join(KNOW, "reviews", "clauses", "*.json"))):
        r = rd(f)
        if r.get("entityId"):
            clause_checked[r["entityId"]] = review_date(r)
    lv_checked = {}
    for f in sorted(glob.glob(os.path.join(KNOW, "reviews", "law-versions", "*.json"))):
        r = rd(f)
        if r.get("entityId"):
            lv_checked[r["entityId"]] = review_date(r)

    hazard_links = defaultdict(list)
    # Filesystem discovery order must not change published references or hashes.
    for kid in sorted(links):
        link = links[kid]
        hazard_links[link.get("hazardId")].append(kid)

    # ---- 正式隐患：只发布当前日期 Gate 通过的 active 实体 ----
    pub = sorted(gate.eligible_hazards)
    used_clauses, seen_clause = [], set()
    basis_of = {hid: [] for hid in pub}
    shipped_links = set()
    order = {"direct": 0, "fallback": 1, "supporting": 2}
    for hid in pub:
        refs = []
        for kid in hazard_links.get(hid, []):
            if kid not in gate.eligible_links:
                continue
            cid = links[kid].get("clauseId")
            if not cid or cid not in clauses:
                continue
            refs.append((cid, links[kid].get("role", "direct")))
            shipped_links.add(kid)
            if cid not in seen_clause:
                seen_clause.add(cid)
                used_clauses.append(cid)
        refs.sort(key=lambda x: (order.get(x[1], 9), x[0], x[1]))
        basis_of[hid] = refs

    # Canonical ID order also fixes clause shard boundaries across checkouts.
    used_clauses.sort()

    # ---- 隐患分片 ----
    hazard_shards, clause_shards = [], []
    h_shard_of, c_shard_of = {}, {}
    for i in range(0, len(pub), SHARD_SIZE):
        sid = "h%04d" % (i // SHARD_SIZE)
        recs = []
        for hid in pub[i:i + SHARD_SIZE]:
            h = hazards[hid]
            h_shard_of[hid] = sid
            note_projection = hazard_presentation[hid]
            recs.append({
                "id": hid,
                "title": h.get("title", ""),
                "description": h.get("description", ""),
                "measures": h.get("measures", ""),
                "conditions": hazard_conditions[hid],
                "note": h.get("note", ""),
                "noteSegments": note_projection["noteSegments"],
                "businessNote": note_projection["businessNote"],
                "maintenanceNote": note_projection["maintenanceNote"],
                "category": h.get("category", ""),
                "displayCategory": hazard_presentation[hid]["displayCategory"],
                "places": h.get("places") or [],
                "sceneTags": hazard_presentation[hid]["sceneTags"],
                "aliases": h.get("aliases") or [],
                "keywords": h.get("keywords") or [],
                "mode": h.get("mode", ""),
                "status": "已核验",
                "publishable": True,
                "lifecycle": h.get("lifecycle", "active"),
                "checked": checked_at.get(hid, ""),
                "basisRefs": [],
            })
        hazard_shards.append({"id": sid, "url": "data/hazards/%s.json" % sid})
        wr(os.path.join(data, "hazards", sid + ".json"),
           {"schemaVersion": 2, "records": recs})

    # ---- 正式条款分片 ----
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
                "lawId": c.get("lawVersionId", ""),
                "sourceUrl": c.get("sourceUrl") or lv.get("sourceUrl") or "",
                "checked": clause_checked.get(cid, ""),
                "status": STATUS_LABEL.get(validity, "待核验")
                          if (c.get("lifecycle") or "active") == "active" else "已废止",
                "region": REGION.get(c.get("jurisdictionCode") or "CN", "全国"),
            })
        clause_shards.append({"id": sid, "url": "data/clauses/%s.json" % sid})
        wr(os.path.join(data, "clauses", sid + ".json"),
           {"schemaVersion": 2, "records": recs})

    for i in range(0, len(pub), SHARD_SIZE):
        sid = "h%04d" % (i // SHARD_SIZE)
        p = os.path.join(data, "hazards", sid + ".json")
        payload = rd(p)
        for rec in payload["records"]:
            rec["basisRefs"] = [
                {"clauseId": cid, "clauseShard": c_shard_of.get(cid, ""), "role": role}
                for cid, role in basis_of[rec["id"]]
            ]
        wr(p, payload)

    # ---- 正式法规索引：knowledge 是身份/版本主源；publication 仅补来源元数据 ----
    base_index = rd(os.path.join(PUBLICATION, "law-index.json"))
    publication_by_id = {e["id"]: e for e in base_index}
    if len(publication_by_id) != len(base_index):
        raise SystemExit("source/publication/law-index.json 存在重复 id，拒绝发布")

    clause_haz = defaultdict(set)
    version_clause = defaultdict(set)
    for kid in shipped_links:
        link = links[kid]
        cid = link.get("clauseId")
        hid = link.get("hazardId")
        if cid in c_shard_of and hid in h_shard_of:
            clause_haz[cid].add(hid)
            vid = clauses[cid].get("lawVersionId")
            if not vid or vid not in lvs:
                raise SystemExit("正式条款缺少 knowledge 法规版本：" + str(cid))
            version_clause[vid].add(cid)

    # 同一个法规身份 + 同一个 versionKey 不允许出现两个正式版本 ID。
    canonical_keys = {}
    for vid in sorted(version_clause):
        lv = lvs[vid]
        key = (lv.get("lawId"), lv.get("versionKey") or lv.get("effectiveDate") or
               lv.get("documentNumber") or vid)
        old = canonical_keys.get(key)
        if old and old != vid:
            raise SystemExit("knowledge 存在重复正式法规版本：%s 与 %s" % (old, vid))
        canonical_keys[key] = vid

    def rebuilt_refs(clause_ids):
        refs = []
        for cid in sorted(clause_ids):
            refs.append({
                "clauseId": cid,
                "clauseShard": c_shard_of.get(cid, ""),
                "hazardIds": sorted(clause_haz.get(cid, [])),
            })
        return refs

    law_index = []
    for vid in sorted(version_clause):
        lv = lvs[vid]
        law = laws.get(lv.get("lawId"))
        if not law:
            raise SystemExit("法规版本缺少 knowledge 法规身份：" + vid)
        source = publication_by_id.get(vid) or {}
        canonical_name = (law.get("canonicalName") or law.get("officialName") or
                          lv.get("officialName") or vid)
        number = lv.get("documentNumber", "")
        name = public_version_title(canonical_name, number)
        aliases = list(dict.fromkeys((law.get("aliases") or []) + (source.get("aliases") or [])))
        validity = lv.get("validityStatus", "unknown")
        refs = rebuilt_refs(version_clause[vid])
        region_code = law.get("jurisdictionCode") or lv.get("scope") or "CN"
        raw_level = raw_law_level(law, lv, source)
        law_index.append({
            "id": vid,
            "name": name,
            "aliases": aliases,
            "documentNumber": number,
            "level": raw_level,
            "displayLevel": display_level(raw_level, vid),
            "scope": REGION.get(region_code, source.get("scope") or region_code),
            "status": STATUS_LABEL.get(validity, "待核验"),
            "checked": (lv_checked.get(vid, "") or source.get("checked", ""))[:10],
            "effectiveDate": lv.get("effectiveDate", ""),
            "sourceUrl": lv.get("sourceUrl") or source.get("sourceUrl", ""),
            "replaces": lv.get("replaces") or source.get("replaces") or [],
            "replacedBy": lv.get("replacedBy") or source.get("replacedBy") or [],
            "clauseRefs": refs,
            "hazardCount": len({h for r in refs for h in r["hazardIds"]}),
            "clauseCount": len(refs),
            "searchText": searchable([
                canonical_name, name, " ".join(aliases), law.get("issuer", ""), number,
                source.get("name", ""), raw_level, display_level(raw_level, vid),
            ]),
        })

    # ---- 搜索索引 / 分类 ----
    si = []
    cat_counter, place_counter = Counter(), Counter()
    mode_counter, level_counter = Counter(), Counter()
    display_category_counter = Counter()
    display_level_counter = Counter()
    level_records = {}
    for vid, lv in lvs.items():
        law = laws.get(lv.get("lawId")) or {}
        source = publication_by_id.get(vid) or {}
        raw = raw_law_level(law, lv, source)
        level_records[vid] = (raw, display_level(raw, vid))
    for hid in pub:
        h = hazards[hid]
        lns, stds, scopes, lvls, display_lvls = set(), set(), set(), set(), set()
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
            level = raw_law_level(law, lv, publication_by_id.get(c.get("lawVersionId")) or {})
            if level:
                lvls.add(level)
                display_lvls.add(display_level(level, c.get("lawVersionId", "")))
        si.append({
            "id": hid,
            "title": h.get("title", ""),
            "aliases": h.get("aliases") or [],
            "category": h.get("category", ""),
            "displayCategory": hazard_presentation[hid]["displayCategory"],
            "places": h.get("places") or [],
            "sceneTags": hazard_presentation[hid]["sceneTags"],
            "keywords": h.get("keywords") or [],
            "businessNote": hazard_presentation[hid]["businessNote"],
            "status": "已核验",
            "publishable": True,
            "mode": h.get("mode", ""),
            "checked": checked_at.get(hid, ""),
            "levels": sorted(lvls),
            "displayLevels": sorted(display_lvls),
            "scopes": sorted(scopes),
            "lawNames": sorted(lns),
            "stdNumbers": sorted(stds),
            "shard": h_shard_of[hid],
            "searchText": searchable([
                h.get("title", ""), " ".join(h.get("aliases") or []),
                " ".join(h.get("keywords") or []), h.get("description", ""),
                hazard_conditions[hid], hazard_presentation[hid]["businessNote"],
                " ".join(sorted(lns)), " ".join(sorted(stds)), h.get("category", ""),
                hazard_presentation[hid]["displayCategory"],
                " ".join(hazard_presentation[hid]["sceneTags"]),
                " ".join(sorted(display_lvls)),
            ]),
        })
        if h.get("category"):
            cat_counter[h["category"]] += 1
        if hazard_presentation[hid]["displayCategory"]:
            display_category_counter[hazard_presentation[hid]["displayCategory"]] += 1
        for pl in h.get("places") or []:
            place_counter[pl] += 1
        if h.get("mode"):
            mode_counter[h["mode"]] += 1
        for level in lvls:
            level_counter[level] += 1
        for level in display_lvls:
            display_level_counter[level] += 1

    taxonomy = {
        "categories": [c for c, _ in cat_counter.most_common()],
        "places": [p for p, _ in place_counter.most_common()],
        "lawLevels": sorted(level_counter),
        "hazardModes": sorted(mode_counter),
        "hazardStatuses": ["已核验"],
        "lawStatuses": sorted({x["status"] for x in law_index if x["status"]}),
        "displayCategories": sorted(display_category_counter),
        "sceneTagOptions": list(SCENE_TAG_OPTIONS),
        "displayLevels": sorted(display_level_counter),
    }

    proposed_count = sum(1 for h in hazards.values()
                         if (h.get("lifecycle") or "active") == "proposed")
    counts = {
        "hazards": len(si),
        "laws": len(law_index),
        "lawVersions": len(law_index),
        "clauses": len(used_clauses),
        "links": len(shipped_links),
    }
    manifest = {
        "schemaVersion": 2,
        "v4SchemaVersion": 3,
        "dataVersion": DATA_VERSION,
        "generatedAt": AS_OF,
        "publicScope": "国家法规标准优先，江苏／南京补充；正式站只发布当前日期已核验依据",
        "counts": counts,
        "sourceCounts": {
            "hazards": gate.counts["hazards"],
            "laws": gate.counts["laws"],
            "lawVersions": gate.counts["lawVersions"],
            "clauses": gate.counts["clauses"],
            "links": gate.counts["links"],
        },
        "health": {
            "verifiedHazards": len(pub),
            "pendingHazards": proposed_count,
            "activeLaws": sum(1 for x in law_index if x["status"] == "现行有效"),
            "pendingLaws": sum(1 for x in law_index if x["status"] not in ("现行有效", "")),
            "invalidReferences": 0,
            "stagedHazards": gate.counts["hazards"] - len(pub),
            "stagedLaws": gate.counts["lawVersions"] - len(law_index),
        },
        "files": {
            "searchIndex": "data/search-index.json",
            "lawIndex": "data/law-index.json",
            "taxonomy": "data/taxonomy.json",
        },
        "hazardShards": hazard_shards,
        "clauseShards": clause_shards,
        "releaseHash": "",
        "sourceRevision": "",
    }
    wr(os.path.join(data, "manifest.json"), manifest, indent=1)
    wr(os.path.join(data, "search-index.json"), si)
    wr(os.path.join(data, "law-index.json"), law_index, indent=2)
    wr(os.path.join(data, "taxonomy.json"), taxonomy)

    # ---- 前端资产与公开全文资料 ----
    for asset in SITE_ASSETS:
        src = os.path.join(WEB, asset)
        dst = os.path.join(out, asset)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
    shutil.copytree(os.path.join(PUBLICATION, "fulltext"), os.path.join(data, "fulltext"))

    catalog = rd(os.path.join(data, "fulltext", "catalog.json"))
    docs = catalog["documents"]
    full_text = [d for d in docs if d["textMode"] == "full_text"]
    link_only = [d for d in docs if d["textMode"] == "link_only"]
    d47236 = [d for d in docs if d.get("versionId") == "LV_STD_GBT47236_2026"]
    if len(d47236) != 1 or d47236[0]["textMode"] != "link_only":
        raise SystemExit("GB/T 47236-2026 题录缺失或不是 link_only，拒绝发布")

    # 全文资料库允许收录尚未成为正式依据的题录/未来版本，因此只要求它属于
    # publication 资料源或 knowledge 法规版本，不能再要求它出现在正式 law-index。
    source_version_ids = set(publication_by_id) | set(lvs)
    dangling = sorted({d["versionId"] for d in docs if d.get("versionId") not in source_version_ids})
    if dangling:
        raise SystemExit("全文资料目录存在未知版本：" + ", ".join(dangling))

    # ---- release.json / site-manifest.json / checksums.json ----
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

    cover_exclude = {"checksums.json", "release.json", "site-manifest.json", "data/manifest.json"}

    def compute_release_hash():
        payload = bundle_hashes(cover_exclude)
        return hashlib.sha256(
            json.dumps(sorted(payload.items()), ensure_ascii=False,
                       separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    manifest["releaseHash"] = compute_release_hash()
    manifest["sourceRevision"] = knowledge_manifest_sha
    manifest["buildToolVersion"] = "safety-unified-release-v2"
    wr(os.path.join(data, "manifest.json"), manifest, indent=1)
    release_hash = compute_release_hash()

    data_hashes = {rel: h for rel, h in sorted(bundle_hashes(set()).items())
                   if rel.startswith("data/")}
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
        "generator": {
            "tool": "tools/v4/build_unified_release.py",
            "model": MODEL,
            "executedAt": datetime.now(timezone.utc).isoformat(),
        },
        "knowledge": {
            "manifestSha256": knowledge_manifest_sha,
            "gate": {
                "asOf": gate.as_of,
                "eligibleHazards": len(pub),
                "eligibleLinks": len(shipped_links),
                "strictBlockers": 0,
                "publicProposalHazards": 0,
                "candidateHazardsInKnowledge": proposed_count,
            },
        },
        "provenance": {
            "hazardClauseLinkSource": "knowledge/ current chained-gate projection",
            "lawCatalogSource": "knowledge/law-versions referenced by eligible links; source/publication enriches source metadata only",
            "fulltextSource": "source/publication/fulltext/",
            "frontendSource": "web/",
        },
        "counts": counts,
        "fullText": {
            "count": len(full_text),
            "officialLinkCount": len(link_only),
            "gbt47236": "link_only",
        },
    }
    wr(os.path.join(out, "release.json"), release, indent=2)

    checksums = bundle_hashes({"checksums.json"})
    wr(os.path.join(out, "checksums.json"), checksums, indent=2)

    formal_ids = {e["id"] for e in law_index}
    public_hazards = {hid: hazards[hid] for hid in pub}
    public_roles = [role for refs in basis_of.values() for _cid, role in refs]
    presentation = presentation_review(
        public_hazards,
        level_records,
        modes=[h.get("mode", "") for h in public_hazards.values()],
        roles=public_roles,
    )
    presentation["scope"] = "public eligible hazards; source fields remain unchanged"
    presentation["sourcePlaceValues"] = len({
        place for hazard in hazards.values() for place in (hazard.get("places") or [])
        if isinstance(place, str)
    })
    presentation["sourceUnknownModes"] = sorted({
        h.get("mode", "") for h in hazards.values()
        if h.get("mode", "") not in ("direct", "conditional")
    })
    presentation["sourceUnknownRoles"] = sorted({
        link.get("role", "direct") for link in links.values()
        if link.get("role", "direct") not in ("direct", "supporting")
    })
    report = {
        "asOf": AS_OF,
        "releaseHash": release_hash,
        "model": MODEL,
        "output": out,
        "counts": counts,
        "gate": {
            "eligibleHazards": len(pub),
            "eligibleLinks": len(shipped_links),
            "candidateHazardsInKnowledge": proposed_count,
        },
        "lawCatalog": {
            "formalKnowledgeVersions": len(law_index),
            "publicationSourceRecords": len(base_index),
            "publicationOnlyOrUnused": len(set(publication_by_id) - formal_ids),
        },
        "fullText": {
            "fullTextCount": len(full_text),
            "officialLinkCount": len(link_only),
        },
        "presentation": presentation,
        "notes": [
            "正式站只发布当前日期 Gate 通过的 active 隐患；proposed 候选保留在 knowledge，不进入正式包",
            "正式法规索引只由已发布条款实际引用的 knowledge 法规版本生成",
            "source/publication 只补公开来源/全文资料，不再制造第二套正式法规身份",
            "upcoming 版本可保留在知识库和全文资料页，但实施日前不能支撑当前正式隐患",
        ],
    }
    wr(out + ".review.json", report, indent=2)

    print("统一正式发布包已生成:", out)
    print("  counts:", json.dumps(counts, ensure_ascii=False))
    print("  正式法规版本: %d；publication 来源记录: %d" % (len(law_index), len(base_index)))
    print("  knowledge 候选未公开: %d" % proposed_count)
    print("  全文资料: %d 部全文 / %d 官方入口" % (len(full_text), len(link_only)))
    print("  releaseHash:", release_hash)


if __name__ == "__main__":
    main()
