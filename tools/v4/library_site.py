# -*- coding: utf-8 -*-
"""把私有全文库导出成可直接双击浏览的本地法规查阅站点。

生成物（纯静态、无外部依赖、可离线打开）：
    index.html            法规清单，支持按名称/标准号过滤
    laws/<key>.html       单部法规全文（可用浏览器 Ctrl+F 页内检索）
    search.js             全库段落索引（供 index.html 做跨法规关键词检索）

用法：
    python tools/v4/library_site.py --output ../法规全文查阅
    python tools/v4/library_site.py --library D:/.../fulltext.sqlite3 --output D:/法规全文查阅

说明：这是给你自己查阅用的私有副本，直接读取私有全文库；它不经过公开导出
门禁（public_fulltext），因此**不得**把它当作对外发布的网站。公开站点的全文
发布仍须走证据与授权门禁。
"""
import argparse
import html
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_LIB = os.path.join(ROOT, "source", "library", "fulltext.sqlite3")


def resolve_library(arg):
    for cand in (arg, os.environ.get("SAFETY_LIBRARY"), DEFAULT_LIB):
        if not cand:
            continue
        p = cand if cand.endswith(".sqlite3") else os.path.join(cand, "fulltext.sqlite3")
        if os.path.exists(p):
            return p
    return None


def safe_name(label):
    """用「标准号/版本 + 法规名称」做文件名，直观可读；仅去掉 Windows 非法字符。"""
    s = re.sub(r'[\/:*?"<>|]', "_", str(label or "")).strip()
    s = re.sub(r"\s+", " ", s)
    return (s[:110] or "doc")


CSS = """
:root{--fg:#1f2328;--muted:#656d76;--line:#d0d7de;--bg:#fff;--accent:#0969da;--mark:#fff3bf}
*{box-sizing:border-box}
body{margin:0;font:15px/1.75 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif;color:var(--fg);background:var(--bg)}
header{position:sticky;top:0;background:#fff;border-bottom:1px solid var(--line);padding:14px 22px;z-index:5}
h1{margin:0 0 8px;font-size:18px}
.wrap{display:flex;gap:0;min-height:calc(100vh - 92px)}
aside{width:330px;border-right:1px solid var(--line);overflow:auto;max-height:calc(100vh - 92px);padding:12px}
main{flex:1;overflow:auto;max-height:calc(100vh - 92px);padding:18px 26px}
input[type=search]{width:100%;padding:9px 11px;border:1px solid var(--line);border-radius:7px;font-size:14px;margin-bottom:10px}
ul{list-style:none;margin:0;padding:0}
li a{display:block;padding:8px 10px;border-radius:7px;text-decoration:none;color:var(--fg);font-size:14px}
li a:hover{background:#f3f4f6}
li a.on{background:#dbeafe;color:var(--accent);font-weight:600}
.meta{color:var(--muted);font-size:12px}
p.para{margin:0 0 9px;padding:3px 6px;border-radius:4px}
p.para.hit{background:var(--mark)}
mark{background:#ffd8a8;padding:0 2px}
h2{font-size:17px;border-bottom:1px solid var(--line);padding-bottom:8px}
.notice{background:#fff8e1;border:1px solid #f0d58c;border-radius:7px;padding:9px 12px;font-size:13px;color:#7a5b00;margin-bottom:14px}
"""

JS_SEARCH = """function doSearch(q){
  const box=document.getElementById('results'); if(!q||q.length<1){box.innerHTML='';box.dataset.hit='';return;}
  const out=[]; const ql=q.toLowerCase();
  for(const [key,ps] of Object.entries(SEARCH_DATA)){
    for(const [no,txt] of ps){
      if(txt.toLowerCase().includes(ql)){ out.push([key,no,txt]); if(out.length>=300) break; }
    }
    if(out.length>=300) break;
  }
  box.dataset.hit=q;
  box.innerHTML = out.length? out.map(([k,no,t])=>{
    const i=t.toLowerCase().indexOf(ql);
    const s=Math.max(0,i-45), e=Math.min(t.length,i+ql.length+45);
    return '<p class="para hit"><a href="laws/'+k+'.html#'+no+'"><b>'+DOCS[k].title+' '+(DOCS[k].version||'')+'</b></a> #'+no+' …'+esc(t.slice(s,e))+'…</p>';
  }).join('') : '<p class="meta">未找到包含「'+esc(q)+'」的段落。</p>';
}
function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--library")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    lib = resolve_library(args.library)
    if not lib:
        print("未找到 fulltext.sqlite3（用 --library 或 SAFETY_LIBRARY 指定）", file=sys.stderr)
        return 1
    conn = sqlite3.connect("file:%s?mode=ro" % lib.replace("\\", "/"), uri=True)

    docs = []
    for row in conn.execute("SELECT document_key, document_id, title, version, paragraph_count, "
                            "current_status, review_status, official_url FROM documents ORDER BY title, version"):
        key, did, title, version, paras, cur, rev, url = row
        docs.append({"key": key, "id": did, "title": title or "", "version": version or "",
                     "paras": paras, "current": cur or "", "review": rev or "", "url": url or "",
                     "file": safe_name("%s %s" % (version or did, title or ""))})
    out = os.path.abspath(args.output)
    os.makedirs(os.path.join(out, "laws"), exist_ok=True)

    # 段落
    by_key = {}
    for dk, pno, content in conn.execute("SELECT document_key, paragraph_no, content FROM fulltext_fts"):
        by_key.setdefault(dk, []).append((pno, content or ""))

    search_data = {}
    for d in docs:
        paras = sorted(by_key.get(d["key"], []))
        body = "\n".join('<p class="para" id="%d">%s</p>' % (no, html.escape(txt))
                         for no, txt in paras)
        page = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>%s %s</title><style>%s</style></head><body>
<header><h1>%s <span class="meta">%s</span></h1>
<div class="meta">%s ｜ %s ｜ %d 段 ｜ <a href="../index.html">返回目录</a>%s</div></header>
<main style="max-height:none">%s</main></body></html>""" % (
            html.escape(d["title"]), html.escape(d["version"]), CSS,
            html.escape(d["title"]), html.escape(d["version"]),
            html.escape(d["current"] or "-"), html.escape(d["review"] or "-"), len(paras),
            (' ｜ <a href="%s" target="_blank">官方来源</a>' % html.escape(d["url"])) if d["url"] else "",
            body)
        with open(os.path.join(out, "laws", d["file"] + ".html"), "w", encoding="utf-8", newline="\n") as f:
            f.write(page)
        # 搜索索引：只保留前 600 字，控制体积
        search_data[d["file"]] = [[no, (t or "")[:600]] for no, t in paras]
        d["href"] = "laws/%s.html" % d["file"]

    items = "\n".join(
        '<li><a href="%s"><b>%s</b> <span class="meta">%s</span><br><span class="meta">%s ｜ %d 段</span></a></li>'
        % (d["href"], html.escape(d["title"]), html.escape(d["version"]),
           html.escape(d["current"] or "-"), d["paras"]) for d in docs)

    index = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>法规全文查阅</title><style>%s</style></head><body>
<header><h1>法规全文查阅（本地私有副本）</h1>
<input type="search" id="q" placeholder="搜索：法规名称，或全文关键词（如 消火栓、分离储存）" oninput="if(this.value.length>1&&this.value.length<40){filterList(this.value);}else{box.innerHTML='';doSearch(this.value);}">
<div class="meta">共 %d 部法规；数据来自私有全文库，仅供自查，未经过公开导出授权门禁。</div></header>
<div class="wrap"><aside><ul id="list">%s</ul></aside>
<main><div id="results"></div><div id="hint" class="notice">左侧点选法规可读全文（Ctrl+F 页内检索）；上方输入框可直接做<b>跨法规关键词检索</b>（输入法规名则过滤左侧清单）。</div></main></div>
<script>const DOCS=%s;const SEARCH_DATA=%s;%s
function filterList(q){const ql=q.toLowerCase();let n=0;
 document.querySelectorAll('#list li').forEach(li=>{const t=li.textContent.toLowerCase();const ok=t.includes(ql);li.style.display=ok?'':'none';if(ok)n++;});
 document.getElementById('results').innerHTML='<p class="meta">匹配法规 '+n+' 部。</p>';}</script>
</body></html>""" % (CSS, len(docs), items,
                     json.dumps({d["file"]: {"title": d["title"], "version": d["version"]} for d in docs}, ensure_ascii=False),
                     json.dumps(search_data, ensure_ascii=False),
                     JS_SEARCH)
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(index)

    total = sum(d["paras"] for d in docs)
    print("已生成: %s" % out)
    print("  法规 %d 部 / 段落 %d / 页面 %d 个" % (len(docs), total, len(docs) + 1))
    print("  打开: %s" % os.path.join(out, "index.html"))
    print("  提示：这是私有自查副本，不可当作对外发布网站。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
