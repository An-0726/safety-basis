# -*- coding: utf-8 -*-
"""V2 老工程 → V4 新工程 条款筛选迁移（交接书 18.14）。

筛选标准（三条全过才迁入）：
  1. V2 法规版本能映射到 V4 现行法规版本（official_name+document_number 归一匹配）；
  2. 条款引文去空白后与归档官方全文逐字一致；
  3. V4 中尚无同 (lawVersionId, articlePath) 条款。

每条迁入都带 verified review（reason 记录 V2 来源 + 逐字比对结论）与法规级证据。
V2 的 1092 条隐患不批量迁移（质量门禁），改由条款反转管线覆盖。

用法：py tools/v4/migrate_v2_clauses.py [--apply]
"""
import argparse
import glob
import hashlib
import io
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools", "pipeline"))
from canonical import content_hash  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")
MASTER = os.path.join(ROOT, "source", "master", "safety.sqlite3")
FULLTEXT = os.path.join(ROOT, "source", "library", "fulltext.sqlite3")
NOW_DATE = "2026-09-12"
MODEL = "GLM-5.3-Flash (ZCode)"


def clean(s):
    out = []
    s = (s or "").replace("\u3000", " ")
    for i, ch in enumerate(s):
        if ch == " ":
            prev = s[i - 1] if i > 0 else " "
            nxt = s[i + 1] if i + 1 < len(s) else " "
            if prev.isascii() and nxt.isascii():
                out.append(ch)
            continue
        out.append(ch)
    return re.sub(r"\s+", " ", "".join(out)).strip()


def nospace(s):
    return re.sub(r"\s+", "", s)


def wr(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(f"file:{MASTER}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    v2_versions = {r["id"]: dict(r) for r in con.execute(
        "SELECT id, law_id, document_number, official_name, validity_status, source_url FROM law_versions")}
    v2_clauses = [dict(r) for r in con.execute(
        "SELECT id, law_version_id, article_path, quote, source_url, status FROM clauses")]

    # V4 版本映射表
    v4_versions = {}
    for f in glob.glob(os.path.join(KNOW, "law-versions", "*.json")):
        d = json.load(io.open(f, encoding="utf-8"))
        key = nospace(d.get("officialName") or "") + "|" + nospace(d.get("documentNumber") or "")
        v4_versions[key] = d
    mappings = {}
    for vid, rec in v2_versions.items():
        key = nospace(rec["official_name"] or "") + "|" + nospace(rec["document_number"] or "")
        if key in v4_versions:
            mappings[vid] = v4_versions[key]

    # 归档全文语料（nospace）
    con2 = sqlite3.connect(f"file:{FULLTEXT}?mode=ro", uri=True)
    corpora = {}
    for did, ver in con2.execute("SELECT document_id, version FROM documents"):
        paras = [clean(r[0]) for r in con2.execute(
            "SELECT content FROM fulltext_fts WHERE document_key=? ORDER BY CAST(paragraph_no AS INTEGER)",
            (did + "\x1f" + ver,))]
        ns = nospace("".join(paras))
        if ns:
            corpora[did] = ns
    ft_by_title = {}
    for did, t in con2.execute("SELECT document_id, title FROM documents"):
        ft_by_title[nospace(clean(t))] = did

    def find_docid(official_name):
        """按标题双向子串匹配归档文档（兼容“（2018修正）”等后缀差异）。"""
        key = nospace(clean(official_name))
        if key in ft_by_title:
            return ft_by_title[key]
        for t, did in ft_by_title.items():
            if len(key) >= 8 and (key in t or t in key):
                return did
        return None

    existing = set()
    for f in glob.glob(os.path.join(KNOW, "clauses", "*.json")):
        d = json.load(io.open(f, encoding="utf-8"))
        existing.add((d.get("lawVersionId"), d.get("articlePath")))
    existing_ids = {d["id"] for d in
                    (json.load(io.open(f, encoding="utf-8")) for f in glob.glob(os.path.join(KNOW, "clauses", "*.json")))}

    created, skip_exists, skip_nocorpus, skip_verify = [], 0, 0, []
    per_v4law = {}
    for c in v2_clauses:
        v4ver = mappings.get(c["law_version_id"])
        if not v4ver:
            continue
        v4vid = v4ver["id"]
        if (v4vid, c["article_path"]) in existing or c["id"] in existing_ids:
            skip_exists += 1
            continue
        quote = clean(c["quote"])
        if len(quote) < 12:
            continue
        # 语料：按 V4 版本 official_name 找归档文档
        docid = find_docid(v4ver["officialName"])
        if not docid or docid not in corpora:
            skip_nocorpus += 1
            continue
        if nospace(quote) not in corpora[docid]:
            skip_verify.append((c["id"], c["article_path"]))
            continue
        cid = c["id"] if c["id"] not in existing_ids else "C_M" + hashlib.md5(c["id"].encode()).hexdigest()[:16]
        eid = "E_" + v4vid.replace("LV_", "")
        clause = {"articlePath": c["article_path"], "id": cid, "jurisdictionCode": "CN",
                  "lawVersionId": v4vid, "lifecycle": "active", "quote": quote,
                  "sourceUrl": c["source_url"] or v4ver.get("sourceUrl", "")}
        created.append((clause, eid, v4ver))
        per_v4law[v4vid] = per_v4law.get(v4vid, 0) + 1

    print(f"筛选结果：可迁移 {len(created)} | 已存在 {skip_exists} | 无法规全文语料 {skip_nocorpus} | 逐字比对不符 {len(skip_verify)}")
    for vid, n in sorted(per_v4law.items(), key=lambda x: -x[1]):
        print(f"   + {vid[:34]:36} {n} 条")
    if not args.apply:
        print("（dry-run，--apply 迁移）")
        return 0

    evidence_cache = {}
    NOW_ISO = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
    for clause, eid, v4ver in created:
        vid = clause["lawVersionId"]
        if eid not in evidence_cache:
            raw = "".join(re.sub(r"\s+", "", x) for x in [v4ver["officialName"]])
            ev = {"id": eid, "locator": f"{v4ver['officialName']}（{v4ver.get('documentNumber','')}）官方全文归档文本。",
                  "page": "全文", "retrievedAt": NOW_ISO, "snapshotSha256": "",
                  "tier": "authoritative-public", "url": v4ver.get("sourceUrl", "")}
            wr(os.path.join(KNOW, "evidence", eid + ".json"), ev)
            evidence_cache[eid] = ev
        wr(os.path.join(KNOW, "clauses", clause["id"] + ".json"), clause)
        v2src = next((c for c in v2_clauses if c["id"] == clause["id"]), None)
        rev = {"checkedAt": NOW_DATE, "decision": "verified", "entityId": clause["id"],
               "entityType": "clause", "evidenceRefs": [eid],
               "reason": "V2 迁移核验（GLM）：老工程条款经筛选迁移，引文去空白后与归档官方全文逐字比对一致；lawVersion 已映射为 V4 现行版本。",
               "reviewType": "text", "reviewedContentHash": content_hash(clause), "reviewer": MODEL}
        wr(os.path.join(KNOW, "reviews", "clauses", clause["id"] + ".json"), rev)
    print(f"applied: {len(created)} clauses migrated")


if __name__ == "__main__":
    raise SystemExit(main())
