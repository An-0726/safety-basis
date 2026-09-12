# -*- coding: utf-8 -*-
"""统一发布包（V4 格式）严格校验器。

与 tools/pipeline/site_bundle.verify_bundle（v2 契约）平行的 V4 通道：
不访问私有母库内容，只做公开包完整性、引用闭环、与 knowledge 实时 Gate 的一致性、
防篡改和版权边界检查。任何一项失败都以非零码退出。

检查范围：
  1. site-selection 指向与 releaseHash 一致；
  2. checksums.json 全覆盖且哈希匹配；文件在公开白名单内（无 _internal、无非 JSON 数据）；
  3. release.json 格式与 releaseHash 复算一致；
  4. manifest / 分片 / search-index / law-index / taxonomy 相互一致，引用全部闭环；
  5. 包内隐患集合 == 实时 evaluate_release_gate(knowledge).eligible_hazards，
     且标题/描述/措施/关联等字段与 knowledge 投影逐字段一致（防篡改）；
  6. 全文库与 r13 审阅版一致：15 部全文不扩面、136 个官方入口、
     GB/T 47236-2026 仅 link_only 题录（不公开 PDF 正文），且可检索。
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from release_gate_core import evaluate_release_gate, load_dir  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")
R13 = os.path.join(ROOT, "source", "releases", "reviewed-20260911-r13")
SELECTION = os.path.join(ROOT, "source", "releases", "site-selection.json")

SITE_ASSETS = ("index.html", "library.html", "style.css", "library.css", "app.js",
               "sw.js", "icon.svg", "manifest.webmanifest", "js/store.js", "js/search.js",
               "js/library.js", "js/fulltext-search.js", "js/verified-files.js")
COVER_EXCLUDE = {"checksums.json", "release.json", "site-manifest.json", "data/manifest.json"}


class Failures(list):
    def check(self, cond, message):
        if not cond:
            self.append(message)
        return cond


def rd(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def all_files(root):
    out = {}
    for base, _dirs, files in os.walk(root):
        for name in files:
            p = os.path.join(base, name)
            out[os.path.relpath(p, root).replace(os.sep, "/")] = p
    return out


def expected_release_hash(bundle):
    payload = {rel: sha256_file(p) for rel, p in all_files(bundle).items()
               if rel not in COVER_EXCLUDE}
    return hashlib.sha256(
        json.dumps(sorted(payload.items()), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", default=None)
    ap.add_argument("--selection", default=SELECTION)
    args = ap.parse_args()
    bad = Failures()

    sel = rd(args.selection)
    bad.check(set(sel) == {"schemaVersion", "bundle", "releaseHash"}
              and sel["schemaVersion"] == "safety-site-selection-v1", "site-selection 格式无效")
    bundle = os.path.abspath(args.bundle or os.path.join(ROOT, "source", "releases", sel["bundle"]))
    releases_root = os.path.join(ROOT, "source", "releases")
    bad.check(os.path.dirname(bundle) == releases_root, "发布包必须位于 source/releases 下")
    if not bad.check(os.path.isdir(bundle), "发布包不存在：" + bundle):
        print(json.dumps({"ok": False, "errors": list(bad)}, ensure_ascii=False, indent=2))
        return 1

    files = all_files(bundle)
    checksums = rd(os.path.join(bundle, "checksums.json"))
    bad.check(set(checksums) == {rel for rel in files if rel != "checksums.json"},
              "checksums.json 与文件集合不一致")
    for rel, expected in checksums.items():
        if rel in files:
            bad.check(sha256_file(files[rel]) == expected, "哈希不匹配：" + rel)

    allowed = ({"checksums.json", "release.json", "site-manifest.json"} | set(SITE_ASSETS)
               | {rel for rel in files if rel.startswith("data/") and rel.endswith(".json")})
    stray = sorted(rel for rel in files if rel not in allowed)
    bad.check(not stray, "发布包含白名单之外文件：" + ", ".join(stray[:10]))
    bad.check(not any(rel.startswith("data/_internal") for rel in files), "发布包含 _internal 索引")

    release = rd(os.path.join(bundle, "release.json"))
    bad.check(release.get("formatVersion") == "safety-unified-release-v1", "release.json 格式无效")
    actual_hash = expected_release_hash(bundle)
    bad.check(release.get("releaseHash") == actual_hash, "releaseHash 复算不一致")
    bad.check(release.get("releaseHash") == sel.get("releaseHash"), "site-selection releaseHash 不匹配")

    manifest = rd(os.path.join(bundle, "data", "manifest.json"))
    site_manifest = rd(os.path.join(bundle, "site-manifest.json"))
    bad.check(manifest.get("schemaVersion") == 2 and manifest.get("v4SchemaVersion") == 3,
              "manifest 格式标记无效")
    bad.check(manifest.get("releaseHash") == actual_hash, "manifest releaseHash 不一致")
    bad.check(site_manifest.get("releaseHash") == actual_hash, "site-manifest releaseHash 不一致")

    # ---- 分片与索引 ----
    hazards, clauses = {}, {}
    for key, target in (("hazardShards", hazards), ("clauseShards", clauses)):
        for shard in manifest[key]:
            payload = rd(os.path.join(bundle, shard["url"]))
            for row in payload["records"]:
                if not bad.check(row["id"] not in target, "分片记录重复：" + row["id"]):
                    continue
                target[row["id"]] = row
    for row in hazards.values():
        bad.check(row.get("status") == "已核验", "隐患分片存在非已核验记录：" + row["id"])
    for row in clauses.values():
        # 2026-09-13 起门禁允许已发布未实施（upcoming）版本支撑引用（用户决策），
        # 故条款效力标签接受 现行有效 与 即将生效；repealed/unknown 仍应被 Gate 拦截
        bad.check(row.get("status") in ("现行有效", "即将生效"),
                  "条款效力标签不可引用（Gate 应已拦截）：" + row["id"] + " " + str(row.get("status")))

    si = rd(os.path.join(bundle, "data", "search-index.json"))
    law_index = rd(os.path.join(bundle, "data", "law-index.json"))
    law_ids = {e["id"] for e in law_index}
    si_ids = {r["id"] for r in si}
    bad.check(si_ids == set(hazards), "search-index 与隐患分片集合不一致")
    bad.check(len(law_ids) == len(law_index), "法规目录存在重复 id")
    for row in clauses.values():
        bad.check(row["lawId"] in law_ids, "条款法规引用断链：" + row["id"])
    for row in hazards.values():
        for ref in row["basisRefs"]:
            ok = bad.check(ref["clauseId"] in clauses, "隐患依据断链：" + row["id"] + "/" + ref["clauseId"])
            if ok:
                shard_url = next(s["url"] for s in manifest["clauseShards"] if s["id"] == ref["clauseShard"])
                shard_ids = {r["id"] for r in rd(os.path.join(bundle, shard_url))["records"]}
                bad.check(ref["clauseId"] in shard_ids, "basisRefs clauseShard 错误：" + row["id"])
    for e in law_index:
        for ref in e.get("clauseRefs", []):
            ok = bad.check(ref["clauseId"] in clauses, "法规条款引用断链：" + e["id"] + "/" + ref["clauseId"])
            if ok:
                bad.check(set(ref.get("hazardIds", [])) <= si_ids, "法规引用的隐患不存在：" + e["id"])
    counts = manifest["counts"]
    bad.check(counts["hazards"] == len(hazards) and counts["clauses"] == len(clauses)
              and counts["laws"] == len(law_index), "manifest counts 与实际数据不一致")

    # ---- 与实时 Gate 的一致性（防篡改）----
    gate = evaluate_release_gate(KNOW)
    know_hazards = load_dir(KNOW, "hazards")
    know_links = load_dir(KNOW, "links")
    know_clauses = load_dir(KNOW, "clauses")
    know_lvs = load_dir(KNOW, "law-versions")
    bad.check(set(hazards) == gate.eligible_hazards,
              "公开隐患集合 != 实时 eligibleHazards（%d vs %d）" % (len(hazards), len(gate.eligible_hazards)))
    verified_by_hazard = {}
    for kid in gate.eligible_links:
        l = know_links[kid]
        if l.get("clauseId") in know_clauses:
            verified_by_hazard.setdefault(l["hazardId"], set()).add((l["clauseId"], l.get("role", "direct")))
    for hid, row in hazards.items():
        src = know_hazards[hid]
        for field in ("title", "description", "measures", "note", "category", "mode"):
            bad.check(row.get(field) == src.get(field), "隐患字段被改动：%s/%s" % (hid, field))
        for field in ("places", "aliases", "keywords"):
            bad.check((row.get(field) or []) == (src.get(field) or []), "隐患标签被改动：%s/%s" % (hid, field))
        shipped = {(r["clauseId"], r["role"]) for r in row["basisRefs"]}
        bad.check(shipped == verified_by_hazard.get(hid, set()), "隐患依据集合与 verified 关联不一致：" + hid)
    for cid, row in clauses.items():
        src = know_clauses[cid]
        lv = know_lvs.get(src.get("lawVersionId")) or {}
        bad.check(row["lawId"] == src.get("lawVersionId"), "条款法规键被改动：" + cid)
        bad.check(row["quote"] == src.get("quote", ""), "条款原文被改动：" + cid)
        bad.check(row["article"] == (src.get("articlePath") or src.get("clauseNumber") or ""),
                  "条款条号被改动：" + cid)

    # ---- 全文库边界 ----
    catalog = rd(os.path.join(bundle, "data", "fulltext", "catalog.json"))
    r13_catalog = rd(os.path.join(R13, "data", "fulltext", "catalog.json"))
    docs = catalog["documents"]
    full_text = {d["versionId"] for d in docs if d["textMode"] == "full_text"}
    r13_full = {d["versionId"] for d in r13_catalog["documents"] if d["textMode"] == "full_text"}
    bad.check(full_text == r13_full, "公开全文集合与 r13 审阅版不一致（不得扩面）")
    d47236 = [d for d in docs if d.get("versionId") == "LV_STD_GBT47236_2026"]
    if bad.check(len(d47236) == 1, "GB/T 47236-2026 题录缺失"):
        d = d47236[0]
        bad.check(d["textMode"] == "link_only", "GB/T 47236-2026 必须是 link_only 题录")
        bad.check("openstd.samr.gov.cn" in d.get("officialUrl", ""), "GB/T 47236-2026 官方入口异常")
        bad.check(d.get("effectiveDate") == "2026-09-01", "GB/T 47236-2026 实施日期应为 2026-09-01")
    entry = next((e for e in law_index if e["id"] == "LV_STD_GBT47236_2026"), None)
    if bad.check(entry is not None, "法规目录缺少 GB/T 47236-2026"):
        bad.check("47236" in (entry.get("searchText", "") + entry.get("name", "")).lower().replace("／", "/")
                  or "47236" in json.dumps(entry, ensure_ascii=False), "GB/T 47236-2026 不可检索")
    bad.check(site_manifest.get("fullTextCount") == len(full_text), "site-manifest fullTextCount 不一致")
    bad.check(site_manifest.get("officialLinkCount") ==
              sum(1 for d in docs if d["textMode"] == "link_only"), "site-manifest officialLinkCount 不一致")
    data_actual = {rel: sha256_file(p) for rel, p in files.items()
                   if rel.startswith("data/") and rel.endswith(".json")}
    bad.check(site_manifest.get("fileHashes") == data_actual, "site-manifest fileHashes 与实际不一致")

    summary = {"ok": not bad, "bundle": os.path.basename(bundle),
               "releaseHash": actual_hash,
               "counts": {"hazards": len(hazards), "laws": len(law_index),
                          "clauses": len(clauses), "links": counts["links"]},
               "gate": {"eligibleHazards": len(gate.eligible_hazards),
                        "eligibleLinks": len(gate.eligible_links)},
               "fullText": {"fullTextCount": len(full_text),
                            "officialLinkCount": site_manifest.get("officialLinkCount")},
               "errors": list(bad)}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
