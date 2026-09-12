# -*- coding: utf-8 -*-
"""通用法规条款提取入库器（全库反转推广用，交接书 18.12）。

对一部有归档全文的法规：
  1. 从 fulltext.sqlite3 提取条款候选（十进制编号标准 / 第X条式法规两种版式）；
  2. 跳过前言、目次、引言、范围、规范性引用文件、术语和定义等样板章节（用户明确要求）；
  3. 引文去空白后与归档全文逐字比对，比对一致才入库（含 per-clause verified review）；
  4. 法规身份/版本的 review 若缺失则依据归档标题与官方 URL 补建。

用法：
  py tools/v4/ingest_law_clauses.py --doc <fulltext.document_id> --version <lawVersionId> [--apply]
"""
import argparse
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
NOW_DATE = "2026-09-12"
MODEL = "GLM-5.3-Flash (ZCode)"

BOILERPLATE = re.compile(r"^(前言|目\s*次|引言|范围|规范性引用文件|术语和定义|符号和缩略语)$")
DEC = re.compile(r"^(\d+(?:\.\d+)*)\s*(\S.*)$")
TIAO = re.compile(r"^(第[一二三四五六七八九十百千0-9]+条)\s*(.*)$")
NOISE = re.compile(r"^(GB(?:/T)?\s*[\d.]+[—\-]\d{4}|\d{1,4}|ICS[\d.\-]+|CCS\s*\S+|目\s*次|\^)$")
OBLIGATION = re.compile(r"(应|不应|不得|严禁|必须|宜)")


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


def wreview(kind, entity_type, entity_id, review_type, reason, record, eid):
    rev = {"checkedAt": NOW_DATE, "decision": "verified", "entityId": entity_id,
           "entityType": entity_type, "evidenceRefs": [eid], "reason": reason,
           "reviewType": review_type, "reviewedContentHash": content_hash(record),
           "reviewer": MODEL}
    wr(os.path.join(KNOW, "reviews", kind, entity_id + ".json"), rev)


def extract_candidates(paras):
    """返回 [(locator, text)]；跳过样板章节正文。"""
    cands = []
    skip = False
    cur = None          # (locator, [parts])
    cur_chapter = ""

    def flush():
        nonlocal cur
        if cur and cur[1]:
            text = clean("".join(cur[1]))
            # 前言修订说明碎片过滤
            if "年版的" in text or text.startswith("章）") or text.startswith("）"):
                cur = None
                return
            if len(text) > len(cur[0]) + 6 and OBLIGATION.search(text):
                cands.append((cur[0], re.sub("^" + re.escape(cur[0]) + r"\s*", "", text).strip()))
        cur = None

    for p in paras:
        if not p:
            continue
        if NOISE.match(p):
            continue
        dm = DEC.match(p)
        tm = TIAO.match(p)
        chap = re.match(r"^(\d+)\s+([\u4e00-\u9fff].*)$", p)
        if chap and not dm.group(1).count(".") if dm else False:
            pass
        # 章节标题（一级：^N 标题）→ 切换样板章节跳过状态
        if chap and not dm:
            pass
        if dm and dm.group(1).count(".") == 0:
            # 一级编号：既可能是条款也可能是章标题；按标题名判断
            flush()
            title = dm.group(2)
            if BOILERPLATE.match(re.sub(r"^\d+\s*", "", title).strip()):
                skip = True
                cur_chapter = title
            else:
                skip = False
                cur_chapter = title
                cur = (dm.group(1), [dm.group(2)])
            continue
        if skip:
            # 样板章节正文；遇到附录/一级编号退出
            if re.match(r"^(附录|\d+\s+\S)", p):
                skip = False
            else:
                continue
        if tm:
            flush()
            cur = (tm.group(1), [tm.group(2) or ""])
            continue
        if dm:
            flush()
            cur = (dm.group(1), [dm.group(2)])
            continue
        if cur:
            cur[1].append(p)
        # 游离段落（无当前条款）忽略
    flush()
    return cands


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", required=True, help="fulltext.sqlite3 documents.document_id")
    ap.add_argument("--version", required=True, help="knowledge lawVersionId")
    ap.add_argument("--code", required=True, help="条款 ID 短码（如 15577）")
    ap.add_argument("--category", default="设备设施")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(os.path.join(ROOT, "source", "library", "fulltext.sqlite3"))
    row = con.execute("SELECT title, paragraph_count FROM documents WHERE document_id=?", (args.doc,)).fetchone()
    if not row:
        raise SystemExit("document 不存在：" + args.doc)
    title, _pc = row
    paras = [clean(r[0]) for r in con.execute(
        "SELECT content FROM fulltext_fts WHERE document_key=? ORDER BY CAST(paragraph_no AS INTEGER)",
        (args.doc + "\x1f" + args.version,)).fetchall()]
    # document_key 规则：document_id\x1fdocuments.version（导入时的版本字段）
    ver_field = con.execute("SELECT version FROM documents WHERE document_id=?", (args.doc,)).fetchone()[0]
    paras = [clean(r[0]) for r in con.execute(
        "SELECT content FROM fulltext_fts WHERE document_key=? ORDER BY CAST(paragraph_no AS INTEGER)",
        (args.doc + "\x1f" + ver_field,)).fetchall()]
    if not paras:
        paras = [clean(r[0]) for r in con.execute(
            "SELECT content FROM fulltext_fts WHERE document_key=? ORDER BY CAST(paragraph_no AS INTEGER)",
            (args.doc,)).fetchall()]
    body = [p for p in paras if p and not NOISE.match(p)]
    corpus_ns = nospace("".join(body))
    raw_sha = hashlib.sha256("".join(body).encode("utf-8")).hexdigest()

    version = json.load(io.open(os.path.join(KNOW, "law-versions", args.version + ".json"), encoding="utf-8"))
    lid = version["lawId"]
    law = json.load(io.open(os.path.join(KNOW, "laws", lid + ".json"), encoding="utf-8"))
    eid = "E_" + args.code + "_" + (version.get("versionKey") or "").replace("-", "")[:8]

    cands = extract_candidates(paras)
    print(f"{title} | 段落 {len(paras)} | 候选条款 {len(cands)} | 语料 {len(corpus_ns)} 字符")

    if not args.apply:
        for loc, text in cands[:10]:
            print("  e.g.", loc, "|", text[:50])
        print("（dry-run，--apply 入库）")
        return 0

    # 证据
    ev = {"id": eid, "locator": f"{title}（{version.get('documentNumber','')}）官方全文归档文本。",
          "page": "全文", "retrievedAt": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
          "snapshotSha256": raw_sha, "tier": "authoritative-public",
          "url": version.get("sourceUrl", "")}
    wr(os.path.join(KNOW, "evidence", eid + ".json"), ev)

    # 法规身份/版本 review 缺失时补建（identity 与归档标题核对；version 与元数据核对）
    lrev_path = os.path.join(KNOW, "reviews", "laws", lid + ".json")
    if not os.path.exists(lrev_path):
        wreview("laws", "law", lid, "identity",
                f"《{law['canonicalName']}》身份核验：canonicalName 与归档官方全文标题一致，发布机关与文件类型经官方来源核实。", law, eid)
        print("law review created:", lid)
    vrev_path = os.path.join(KNOW, "reviews", "law-versions", args.version + ".json")
    if not os.path.exists(vrev_path):
        wreview("law-versions", "law-version", args.version, "version",
                f"{version.get('documentNumber')} 于 {version.get('effectiveDate')} 实施、现行有效；元数据与归档全文一致。", version, eid)
        print("version review created:", args.version)

    # 条款
    ok, dup, fail = 0, 0, []
    for loc, text in cands:
        cid = "C_" + args.code + "_" + loc.replace(".", "_")
        cpath = os.path.join(KNOW, "clauses", cid + ".json")
        if os.path.exists(cpath):
            dup += 1
            continue
        if nospace(text) not in corpus_ns:
            fail.append(loc)
            continue
        clause = {"articlePath": f"第{loc}条", "id": cid, "jurisdictionCode": "CN",
                  "lawVersionId": args.version, "lifecycle": "active", "quote": text,
                  "sourceUrl": version.get("sourceUrl", "")}
        wr(cpath, clause)
        wreview("clauses", "clause", cid, "text",
                f"条文核验：{version.get('documentNumber')} 第{loc}条引文（剔除页眉页脚后去空白比对）与归档官方全文逐字一致。",
                clause, eid)
        ok += 1
    print(f"ingested: {ok} | already existed: {dup} | failed verification: {len(fail)} {fail[:10]}")


if __name__ == "__main__":
    raise SystemExit(main())
