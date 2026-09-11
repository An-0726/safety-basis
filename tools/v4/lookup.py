# -*- coding: utf-8 -*-
"""本地法规全文检索（优先于联网查证）。

数据源为项目既有的私有全文库 `source/library/fulltext.sqlite3`
（由 tools/pipeline/fulltext.py 导入，格式 safety-fulltext-v1），
里面是官方原件归档后的全文与 SHA-256。

用法：
    python tools/v4/lookup.py --list
        列出库内全部法规（标题、版本、段落数）。

    python tools/v4/lookup.py --law "XF 1131"
        列出某部法规的全部段落（可按 --limit 截断）。

    python tools/v4/lookup.py --law "XF 1131" --grep 消火栓
        在该法规内检索关键词，输出命中段落及其前后各 2 段上下文。

    python tools/v4/lookup.py --grep 消火栓 --limit 40
        全库检索关键词。

    python tools/v4/lookup.py --law "XF 1131" --article 10.1
        按条款号定位（等价于 --grep 但会优先匹配段首条款号）。

库路径解析顺序：--library 参数 > 环境变量 SAFETY_LIBRARY > 本仓库 source/library/。

注意：本工具只读，不写入全文库，也不修改 knowledge 树。
"""
import argparse
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_LIB = os.path.join(ROOT, "source", "library", "fulltext.sqlite3")


def resolve_library(arg):
    for cand in (arg, os.environ.get("SAFETY_LIBRARY"),
                 DEFAULT_LIB,
                 os.path.join(ROOT, "source", "library", "fulltext.sqlite3")):
        if not cand:
            continue
        p = cand if cand.endswith(".sqlite3") else os.path.join(cand, "fulltext.sqlite3")
        if os.path.exists(p):
            return p
    return None


def connect(path):
    return sqlite3.connect("file:%s?mode=ro" % path.replace("\\", "/"), uri=True)


def load_documents(conn):
    cur = conn.cursor()
    cur.execute("SELECT document_key, document_id, title, version, paragraph_count, "
                "current_status, review_status, text_sha256, official_url FROM documents")
    return [dict(zip(("key", "id", "title", "version", "paras", "current", "review",
                      "text_sha256", "url"), r)) for r in cur.fetchall()]


def load_paragraphs(conn, key_filter=None):
    """FTS5 表的非索引列不支持 LIKE，这里用游标全表扫描后过滤（万级行，毫秒级）。"""
    cur = conn.cursor()
    cur.execute("SELECT document_key, paragraph_no, title, version, content FROM fulltext_fts")
    out = []
    for dk, pno, title, version, content in cur.fetchall():
        if key_filter and key_filter not in dk:
            continue
        out.append({"key": dk, "no": pno, "title": title, "version": version,
                    "content": content or ""})
    return out


def law_number_index():
    """从 knowledge/law-versions 读 (lawId, versionKey) -> documentNumber。

    全文库的文档按 documentId=lawId、version=versionKey 命名以便与知识树对齐，
    因此文档自身不含标准号（如 "GB 15603-2022"）；这里把标准号补上，
    使用户可以直接按标准号检索。
    """
    out = {}
    d = os.path.join(ROOT, "knowledge", "law-versions")
    if not os.path.isdir(d):
        return out
    for fn in os.listdir(d):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(d, fn), encoding="utf-8") as f:
                v = json.load(f)
        except (OSError, ValueError) as exc:
            # 只吞"文件读不了/不是合法 JSON"；其它异常（如 NameError）必须暴露，
            # 否则真 bug 会被静默跳过、表现为索引为空。
            print("  [warn] 跳过无法解析的 lawVersion %s: %s" % (fn, exc), file=sys.stderr)
            continue
        num = (v.get("documentNumber") or "").strip()
        name = (v.get("officialName") or "").strip()
        if num or name:
            out[(v.get("lawId"), v.get("versionKey"))] = (num + " " + name).strip()
    return out


def match_docs(docs, needle, number_index=None):
    if not needle:
        return docs
    n = needle.lower().replace(" ", "").replace("-", "")
    hit = []
    for d in docs:
        extra = ""
        if number_index:
            extra = number_index.get((d["id"], d["version"]), "")
        hay = ((d["title"] or "") + (d["version"] or "") + (d["id"] or "") + extra).lower()
        hay = hay.replace(" ", "").replace("-", "")
        if n in hay:
            hit.append(d)
    return hit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--library", help="fulltext.sqlite3 路径或其所在目录")
    ap.add_argument("--list", action="store_true", help="列出库内全部法规")
    ap.add_argument("--law", help="法规名/标准号过滤（模糊匹配）")
    ap.add_argument("--grep", help="关键词检索")
    ap.add_argument("--article", help="条款号定位，例如 10.1 或 6.5.3")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--context", type=int, default=2, help="关键词命中的上下文段数")
    args = ap.parse_args()

    lib = resolve_library(args.library)
    if not lib:
        print("未找到 fulltext.sqlite3。请用 --library 指定私有全文库路径，"
              "或设置环境变量 SAFETY_LIBRARY。")
        return 1
    conn = connect(lib)
    docs = load_documents(conn)
    print("全文库: %s" % lib)
    print("收录法规: %d 份\n" % len(docs))

    if args.list or (not args.law and not args.grep and not args.article):
        for d in sorted(docs, key=lambda x: (x["title"] or "")):
            print("  %-44s | %-22s | %3s 段 | %s" %
                  ((d["title"] or "")[:44], (d["version"] or "")[:22], d["paras"], d["current"]))
        return 0

    sel = match_docs(docs, args.law, law_number_index())
    if args.law and not sel:
        print("库内没有匹配 %r 的法规。以下为全部标题，可据此确认是否缺件：" % args.law)
        for d in sorted(docs, key=lambda x: (x["title"] or "")):
            print("   ", d["title"], "|", d["version"])
        return 2
    if args.law:
        print("匹配法规: %s" % ", ".join("%s(%s)" % (d["title"], d["version"]) for d in sel))

    key_filters = {(d["key"].split("\x1f")[0] if d["key"] else "") for d in sel} if args.law else None
    paras = load_paragraphs(conn)
    if args.law:
        wanted = {d["id"] for d in sel} | {d["key"] for d in sel}
        paras = [p for p in paras if p["key"] in wanted
                 or (p["key"] or "").split("\x1f")[0] in {d["id"] for d in sel}
                 or any((d["version"] or "") and (d["version"] == p["version"]) for d in sel)]
    paras.sort(key=lambda p: (p["version"] or "", p["no"]))

    needle = args.grep or args.article
    if not needle:
        for p in paras[:args.limit]:
            print("\n[%s #%s] %s" % (p["version"], p["no"], p["content"][:600]))
        if len(paras) > args.limit:
            print("\n... 共 %d 段，已截断（用 --limit 调整）" % len(paras))
        return 0

    hits = [i for i, p in enumerate(paras) if needle in p["content"]]
    if not hits:
        print("未在%s检索到 %r。" % ("该法规内" if args.law else "全库", needle))
        return 2
    print("命中 %d 处（关键词 %r）\n" % (len(hits), needle))
    shown = set()
    for i in hits[:args.limit]:
        lo, hi = max(0, i - args.context), min(len(paras), i + args.context + 1)
        for j in range(lo, hi):
            if j in shown:
                continue
            shown.add(j)
            p = paras[j]
            mark = ">>" if j == i else "  "
            print("%s [%s #%s] %s" % (mark, p["version"], p["no"], p["content"][:700]))
        print("-" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
