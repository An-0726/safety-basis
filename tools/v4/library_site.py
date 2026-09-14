# -*- coding: utf-8 -*-
"""把私有全文库导出成可直接双击浏览的本地法规查阅站点。

生成物（纯静态、无外部依赖、可离线打开）：
    index.html            法规/真实版本组清单
    groups/<key>.html     一个法规/真实版本下的多个全文载体
    laws/<key>.html       单个全文载体页面
    originals/*           对应私有原件/历史载体的本地链接副本

私有 source/library/document-aliases.json 可把历史 document identity
归到同一真实法规版本。归组只改变本地展示，不删除 SQLite document、
FTS 行或 archive 原件。没有 alias 文件时保持旧行为：一条 document 一条目录项。

说明：这是给用户自己查阅用的私有副本，不经过公开全文授权门禁，不得把
该站点当作对外发布网站。
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import sqlite3
import sys
from collections import defaultdict
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_LIB = os.path.join(ROOT, "source", "library", "fulltext.sqlite3")
ALIASES_FILE = "document-aliases.json"
ALIASES_SCHEMA = "safety-fulltext-document-aliases-v1"


def resolve_library(arg: str | None) -> str | None:
    for cand in (arg, os.environ.get("SAFETY_LIBRARY"), DEFAULT_LIB):
        if not cand:
            continue
        p = cand if cand.endswith(".sqlite3") else os.path.join(cand, "fulltext.sqlite3")
        if os.path.exists(p):
            return p
    return None


def safe_name(label: Any) -> str:
    """生成 Windows 也可用的本地静态文件名。"""
    s = re.sub(r'[\\/:*?"<>|]', "_", str(label or "")).strip()
    s = re.sub(r"\s+", " ", s)
    return s[:110] or "doc"


def load_law_versions() -> tuple[dict[tuple[str, str], str], dict[str, dict[str, Any]]]:
    """返回全文标签索引和 version-id -> knowledge metadata。"""
    number_index: dict[tuple[str, str], str] = {}
    by_id: dict[str, dict[str, Any]] = {}
    directory = os.path.join(ROOT, "knowledge", "law-versions")
    if not os.path.isdir(directory):
        return number_index, by_id

    for filename in os.listdir(directory):
        if not filename.endswith(".json"):
            continue
        try:
            with open(os.path.join(directory, filename), encoding="utf-8") as fh:
                version = json.load(fh)
        except (OSError, ValueError):
            continue

        vid = str(version.get("id") or "").strip()
        law_id = str(version.get("lawId") or "").strip()
        version_key = str(version.get("versionKey") or "").strip()
        number = str(version.get("documentNumber") or "").strip()
        if vid:
            by_id[vid] = version
        if number and version_key:
            if law_id:
                number_index[(law_id, version_key)] = number
            if vid:
                number_index[(vid, version_key)] = number
    return number_index, by_id


def load_alias_groups(library_root: str) -> dict[str, dict[str, Any]]:
    """读取私有 document alias 文件，返回 document_key -> group metadata。

    文件不存在时返回空映射。坏文件 fail closed：拒绝生成本地站点，避免把
    错误 alias 静默应用到全文库。
    """
    path = os.path.join(library_root, ALIASES_FILE)
    if not os.path.isfile(path):
        return {}

    try:
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
    except (OSError, ValueError) as exc:
        raise ValueError(f"{ALIASES_FILE} 无法读取") from exc

    if not isinstance(payload, dict) or payload.get("schemaVersion") != ALIASES_SCHEMA:
        raise ValueError(f"{ALIASES_FILE} schemaVersion 必须为 {ALIASES_SCHEMA}")
    groups = payload.get("groups")
    if not isinstance(groups, list):
        raise ValueError(f"{ALIASES_FILE} groups 必须为数组")

    by_document: dict[str, dict[str, Any]] = {}
    seen_group_ids: set[str] = set()
    for ordinal, group in enumerate(groups, 1):
        if not isinstance(group, dict):
            raise ValueError(f"{ALIASES_FILE} groups[{ordinal}] 必须为对象")
        group_id = str(group.get("groupId") or "").strip()
        title = str(group.get("title") or "").strip()
        members = group.get("memberDocumentKeys")
        classification = str(group.get("classification") or "").strip()
        canonical = str(group.get("canonicalVersionId") or "").strip()
        if not group_id or not title or not classification:
            raise ValueError(f"{ALIASES_FILE} groups[{ordinal}] 缺少 groupId/title/classification")
        if group_id in seen_group_ids:
            raise ValueError(f"{ALIASES_FILE} groupId 重复: {group_id}")
        seen_group_ids.add(group_id)
        if not isinstance(members, list) or len(members) < 2:
            raise ValueError(f"{ALIASES_FILE} groups[{ordinal}] 至少需要 2 个 memberDocumentKeys")

        normalized = {
            "groupId": group_id,
            "title": title,
            "classification": classification,
            "canonicalVersionId": canonical,
            "note": str(group.get("note") or "").strip(),
            "memberDocumentKeys": [str(value) for value in members],
        }
        for key in normalized["memberDocumentKeys"]:
            if not key:
                raise ValueError(f"{ALIASES_FILE} groups[{ordinal}] 存在空 document_key")
            if key in by_document:
                raise ValueError(f"{ALIASES_FILE} document_key 同时属于多个组: {key}")
            by_document[key] = normalized
    return by_document


def group_documents(
    docs: list[dict[str, Any]],
    alias_by_document: dict[str, dict[str, Any]],
    knowledge_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """把展示目录归成法规/真实版本组，但保留所有底层全文载体。"""
    doc_by_key = {doc["key"]: doc for doc in docs}
    grouped: dict[str, dict[str, Any]] = {}
    consumed: set[str] = set()

    # 仅当 alias 组的所有成员都实际存在于本次 SQLite 中时才归组。
    unique_groups: dict[str, dict[str, Any]] = {}
    for meta in alias_by_document.values():
        unique_groups.setdefault(meta["groupId"], meta)

    for group_id, meta in unique_groups.items():
        member_keys = meta["memberDocumentKeys"]
        missing = [key for key in member_keys if key not in doc_by_key]
        if missing:
            print(
                f"警告：{ALIASES_FILE} 组 {group_id} 缺少 {len(missing)} 个 SQLite document，"
                "本组不应用归组。",
                file=sys.stderr,
            )
            continue
        members = [doc_by_key[key] for key in member_keys]
        canonical_id = meta.get("canonicalVersionId") or ""
        knowledge = knowledge_by_id.get(canonical_id, {}) if canonical_id else {}
        number = str(knowledge.get("documentNumber") or "").strip()
        display_title = str(knowledge.get("officialName") or meta["title"]).strip()
        display_label = number or canonical_id or members[0]["label"]
        grouped[group_id] = {
            "group_id": group_id,
            "title": display_title,
            "label": display_label,
            "classification": meta["classification"],
            "canonical_version_id": canonical_id,
            "knowledge_mapped": bool(knowledge),
            "note": meta.get("note") or "",
            "members": members,
        }
        consumed.update(member_keys)

    # 未归组 document 作为单成员组，真实不同版本自然各自保留。
    for doc in docs:
        if doc["key"] in consumed:
            continue
        singleton_id = "DOC:" + doc["key"]
        grouped[singleton_id] = {
            "group_id": singleton_id,
            "title": doc["title"],
            "label": doc["label"],
            "classification": "singleton",
            "canonical_version_id": "",
            "knowledge_mapped": False,
            "note": "",
            "members": [doc],
        }

    return sorted(
        grouped.values(),
        key=lambda item: (
            str(item["title"]).casefold(),
            str(item["label"]).casefold(),
            str(item["group_id"]).casefold(),
        ),
    )


CSS = """
:root{--fg:#1f2328;--muted:#656d76;--line:#d0d7de;--bg:#fff;--accent:#0969da;--mark:#fff3bf}
*{box-sizing:border-box}
body{margin:0;font:15px/1.75 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif;color:var(--fg);background:var(--bg)}
header{position:sticky;top:0;background:#fff;border-bottom:1px solid var(--line);padding:14px 22px;z-index:5}
h1{margin:0 0 8px;font-size:18px}
.wrap{display:flex;gap:0;min-height:calc(100vh - 92px)}
aside{width:350px;border-right:1px solid var(--line);overflow:auto;max-height:calc(100vh - 92px);padding:12px}
main{flex:1;overflow:auto;max-height:calc(100vh - 92px);padding:18px 26px}
input[type=search]{width:100%;padding:9px 11px;border:1px solid var(--line);border-radius:7px;font-size:14px;margin-bottom:10px}
ul{list-style:none;margin:0;padding:0}
li a{display:block;padding:8px 10px;border-radius:7px;text-decoration:none;color:var(--fg);font-size:14px}
li a:hover{background:#f3f4f6}
.meta{color:var(--muted);font-size:12px}
.badge{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:0 7px;margin-left:6px;font-size:11px;color:var(--muted)}
.warn{color:#8a5a00}
p.para{margin:0 0 9px;padding:3px 6px;border-radius:4px}
p.para.hit{background:var(--mark)}
mark{background:#ffd8a8;padding:0 2px}
h2{font-size:17px;border-bottom:1px solid var(--line);padding-bottom:8px}
.notice{background:#fff8e1;border:1px solid #f0d58c;border-radius:7px;padding:9px 12px;font-size:13px;color:#7a5b00;margin-bottom:14px}
.card{border:1px solid var(--line);border-radius:8px;padding:12px 14px;margin:10px 0}
"""

JS_SEARCH = """function doSearch(q){
  const box=document.getElementById('results'); if(!q||q.length<1){box.innerHTML='';box.dataset.hit='';return;}
  const out=[]; const ql=q.toLowerCase(); const seen=new Set();
  for(const [key,ps] of Object.entries(SEARCH_DATA)){
    const doc=DOCS[key]||{};
    for(const [no,txt] of ps){
      if(txt.toLowerCase().includes(ql)){
        const sig=(doc.group||key)+'\\u001f'+txt;
        if(seen.has(sig)) continue;
        seen.add(sig);
        out.push([key,no,txt]); if(out.length>=300) break;
      }
    }
    if(out.length>=300) break;
  }
  box.dataset.hit=q;
  box.innerHTML = out.length? out.map(([k,no,t])=>{
    const d=DOCS[k]||{}; const i=t.toLowerCase().indexOf(ql);
    const s=Math.max(0,i-45), e=Math.min(t.length,i+ql.length+45);
    return '<p class="para hit"><a href="laws/'+k+'.html#'+no+'"><b>'+esc(d.title||'')+' '+esc(d.version||'')+'</b></a> #'+no+' …'+esc(t.slice(s,e))+'…</p>';
  }).join('') : '<p class="meta">未找到包含「'+esc(q)+'」的段落。</p>';
}
function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--library")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    lib = resolve_library(args.library)
    if not lib:
        print("未找到 fulltext.sqlite3（用 --library 或 SAFETY_LIBRARY 指定）", file=sys.stderr)
        return 1

    library_root = os.path.dirname(os.path.abspath(lib))
    number_index, knowledge_by_id = load_law_versions()
    try:
        alias_by_document = load_alias_groups(library_root)
    except ValueError as exc:
        print(f"全文 alias 配置错误：{exc}", file=sys.stderr)
        return 2

    conn = sqlite3.connect("file:%s?mode=ro" % lib.replace("\\", "/"), uri=True)
    try:
        docs: list[dict[str, Any]] = []
        used_files: set[str] = set()
        for row in conn.execute(
            "SELECT document_key, document_id, title, version, paragraph_count, "
            "current_status, review_status, official_url, archive_ref "
            "FROM documents ORDER BY title, version"
        ):
            key, did, title, version, paras, cur, rev, url, archive_ref = row
            label = number_index.get((did, version), "") or version or did
            base_file = safe_name("%s %s" % (label, title or ""))
            file_name = base_file
            if file_name.casefold() in used_files:
                file_name = safe_name("%s [%s]" % (base_file, key))
            suffix = 2
            while file_name.casefold() in used_files:
                file_name = safe_name("%s [%s-%d]" % (base_file, key, suffix))
                suffix += 1
            used_files.add(file_name.casefold())
            docs.append(
                {
                    "key": key,
                    "id": did,
                    "title": title or "",
                    "version": version or "",
                    "paras": int(paras or 0),
                    "current": cur or "",
                    "review": rev or "",
                    "url": url or "",
                    "archive_ref": archive_ref or "",
                    "label": label,
                    "file": file_name,
                }
            )

        display_groups = group_documents(docs, alias_by_document, knowledge_by_id)
        group_for_document: dict[str, str] = {}
        for group in display_groups:
            for member in group["members"]:
                group_for_document[member["key"]] = group["group_id"]

        out = os.path.abspath(args.output)
        laws_dir = os.path.join(out, "laws")
        groups_dir = os.path.join(out, "groups")
        originals_dir = os.path.join(out, "originals")
        for directory in (laws_dir, groups_dir, originals_dir):
            if os.path.isdir(directory):
                for filename in os.listdir(directory):
                    path = os.path.join(directory, filename)
                    if os.path.isfile(path):
                        os.remove(path)
            os.makedirs(directory, exist_ok=True)

        def original_extension(path: str) -> str:
            try:
                with open(path, "rb") as fh:
                    head = fh.read(16)
            except OSError:
                return ".bin"
            if head.startswith(b"%PDF"):
                return ".pdf"
            if head.startswith(b"PK"):
                return ".docx"
            if head.lstrip().startswith((b"<", b"<!")):
                return ".html"
            return ".txt"

        for doc in docs:
            source = os.path.join(library_root, doc["archive_ref"])
            if not os.path.isfile(source):
                continue
            original_name = doc["file"] + original_extension(source)
            destination = os.path.join(originals_dir, original_name)
            try:
                os.link(source, destination)
            except (OSError, AttributeError):
                shutil.copyfile(source, destination)
            doc["original_href"] = "../originals/" + original_name

        by_key: dict[str, list[tuple[int, str]]] = defaultdict(list)
        for document_key, paragraph_no, content in conn.execute(
            "SELECT document_key, paragraph_no, content FROM fulltext_fts"
        ):
            by_key[document_key].append((int(paragraph_no), content or ""))

        search_data: dict[str, list[list[Any]]] = {}
        docs_js: dict[str, dict[str, str]] = {}
        for doc in docs:
            paragraphs = sorted(by_key.get(doc["key"], []))
            body = "\n".join(
                '<p class="para" id="%d">%s</p>' % (no, html.escape(text))
                for no, text in paragraphs
            )
            page = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>%s %s</title><style>%s</style></head><body>
<header><h1>%s <span class="meta">%s</span></h1>
<div class="meta">%s ｜ %s ｜ %d 段 ｜ <a href="../index.html">返回目录</a>%s%s</div></header>
<main style="max-height:none">%s</main></body></html>""" % (
                html.escape(doc["title"]),
                html.escape(doc["version"]),
                CSS,
                html.escape(doc["title"]),
                html.escape(doc["version"]),
                html.escape(doc["current"] or "-"),
                html.escape(doc["review"] or "-"),
                len(paragraphs),
                (' ｜ <a href="%s" target="_blank">官方来源</a>' % html.escape(doc["url"]))
                if doc["url"] else "",
                (' ｜ <a href="%s" target="_blank">打开原始文件</a>' % html.escape(doc["original_href"]))
                if doc.get("original_href") else "",
                body,
            )
            with open(
                os.path.join(laws_dir, doc["file"] + ".html"),
                "w",
                encoding="utf-8",
                newline="\n",
            ) as fh:
                fh.write(page)
            search_data[doc["file"]] = [[no, text[:600]] for no, text in paragraphs]
            doc["href"] = "laws/%s.html" % doc["file"]
            docs_js[doc["file"]] = {
                "title": doc["title"],
                "version": doc["version"],
                "group": group_for_document.get(doc["key"], doc["key"]),
            }

        # 为多载体组生成一个聚合页；单成员组直接链接全文页。
        used_group_files: set[str] = set()
        for group in display_groups:
            members = group["members"]
            if len(members) == 1:
                group["href"] = members[0]["href"]
                continue

            base = safe_name("%s %s" % (group["label"], group["title"]))
            group_file = base
            suffix = 2
            while group_file.casefold() in used_group_files:
                group_file = safe_name("%s-%d" % (base, suffix))
                suffix += 1
            used_group_files.add(group_file.casefold())
            group["href"] = "groups/%s.html" % group_file

            cards = []
            for member in members:
                source_links = []
                if member.get("url"):
                    source_links.append(
                        '<a href="%s" target="_blank">官方来源</a>' % html.escape(member["url"])
                    )
                if member.get("original_href"):
                    source_links.append(
                        '<a href="../%s" target="_blank">打开原始文件</a>'
                        % html.escape(member["original_href"])
                    )
                links = " ｜ ".join(source_links)
                cards.append(
                    '<div class="card"><b><a href="../%s">%s</a></b>'
                    '<div class="meta">%s ｜ %s ｜ %d 段%s</div></div>'
                    % (
                        html.escape(member["href"]),
                        html.escape(member["version"] or member["label"]),
                        html.escape(member["current"] or "-"),
                        html.escape(member["review"] or "-"),
                        member["paras"],
                        (" ｜ " + links) if links else "",
                    )
                )

            unmapped = group["classification"] == "same_real_version_knowledge_unmapped"
            status_note = (
                '<div class="notice">该组已确认属于同一真实版本，但当前 knowledge 尚未建立正式 canonical version。'
                "这里只做私有全文展示归组，不把它当作正式法规依据。</div>"
                if unmapped
                else '<div class="notice">该组的多个 SQLite document 已归到同一真实法规版本。'
                "底层全文载体仍全部保留，未做物理删除。</div>"
            )
            page = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>%s</title><style>%s</style></head><body>
<header><h1>%s <span class="meta">%s</span></h1>
<div class="meta">%d 个全文载体 ｜ <a href="../index.html">返回目录</a></div></header>
<main style="max-height:none">%s%s</main></body></html>""" % (
                html.escape(group["title"]),
                CSS,
                html.escape(group["title"]),
                html.escape(group["label"]),
                len(members),
                status_note,
                "\n".join(cards),
            )
            with open(
                os.path.join(groups_dir, group_file + ".html"),
                "w",
                encoding="utf-8",
                newline="\n",
            ) as fh:
                fh.write(page)

        items = []
        for group in display_groups:
            members = group["members"]
            if len(members) == 1:
                member = members[0]
                meta = "%s ｜ %d 段" % (member["current"] or "-", member["paras"])
            else:
                suffix = (
                    " ｜ knowledge待映射"
                    if group["classification"] == "same_real_version_knowledge_unmapped"
                    else ""
                )
                meta = "%d 个全文载体%s" % (len(members), suffix)
            items.append(
                '<li><a href="%s"><b>%s</b> <span class="meta">%s</span>'
                '<br><span class="meta">%s</span></a></li>'
                % (
                    html.escape(group["href"]),
                    html.escape(group["title"]),
                    html.escape(group["label"]),
                    html.escape(meta),
                )
            )

        index = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>法规全文查阅</title><style>%s</style></head><body>
<header><h1>法规全文查阅（本地私有副本）</h1>
<input type="search" id="q" placeholder="搜索：法规名称，或全文关键词（如 消火栓、分离储存）" oninput="if(this.value.length>1&&this.value.length<40){filterList(this.value);}else{document.getElementById('results').innerHTML='';doSearch(this.value);}">
<div class="meta">共 %d 个法规/真实版本组；%d 个全文载体；数据来自私有全文库，仅供自查，未经过公开导出授权门禁。</div></header>
<div class="wrap"><aside><ul id="list">%s</ul></aside>
<main><div id="results"></div><div id="hint" class="notice">左侧目录按法规/真实版本归组；一个组可保留多个历史全文载体。上方输入框仍搜索全部 %d 个载体，不因归组丢失全文。</div></main></div>
<script>const DOCS=%s;const SEARCH_DATA=%s;%s
function filterList(q){const ql=q.toLowerCase();let n=0;
 document.querySelectorAll('#list li').forEach(li=>{const t=li.textContent.toLowerCase();const ok=t.includes(ql);li.style.display=ok?'':'none';if(ok)n++;});
 document.getElementById('results').innerHTML='<p class="meta">匹配法规/版本组 '+n+' 个。</p>';}</script>
</body></html>""" % (
            CSS,
            len(display_groups),
            len(docs),
            "\n".join(items),
            len(docs),
            json.dumps(docs_js, ensure_ascii=False),
            json.dumps(search_data, ensure_ascii=False),
            JS_SEARCH,
        )
        with open(os.path.join(out, "index.html"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(index)

        total = sum(doc["paras"] for doc in docs)
        multi_groups = sum(1 for group in display_groups if len(group["members"]) > 1)
        print("已生成: %s" % out)
        print(
            "  法规/版本组 %d 个 / 全文载体 %d 个 / 归组 %d 个 / 段落 %d"
            % (len(display_groups), len(docs), multi_groups, total)
        )
        if alias_by_document:
            print("  已应用私有 alias: %s" % os.path.join(library_root, ALIASES_FILE))
        else:
            print("  未发现私有 alias；目录保持一条 document 一项。")
        print("  打开: %s" % os.path.join(out, "index.html"))
        print("  提示：这是私有自查副本，不可当作对外发布网站。")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
