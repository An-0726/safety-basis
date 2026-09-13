# -*- coding: utf-8 -*-
"""生成唯一的本地使用版：公开隐患库 + 私有法规全文库。

输出目录默认是 ``dist/local``，属于可重复生成的本地成品，不提交 Git。
生成后直接打开 ``dist/local/README.html`` 即可选择使用入口。
"""
from __future__ import annotations

import argparse
import html
import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "dist" / "local"
PUBLIC_RELEASE = ROOT / "source" / "releases" / "current"
PRIVATE_LIBRARY = ROOT / "source" / "library" / "fulltext.sqlite3"
LIBRARY_SITE = ROOT / "tools" / "v4" / "library_site.py"


def _safe_output(path: Path) -> Path:
    resolved = path.resolve()
    dist_root = (ROOT / "dist").resolve()
    if resolved == dist_root or dist_root not in resolved.parents:
        raise ValueError("输出目录必须位于仓库 dist/ 之下")
    return resolved


def _counts() -> tuple[dict, int, int]:
    release = json.loads((PUBLIC_RELEASE / "release.json").read_text(encoding="utf-8"))
    with sqlite3.connect(f"file:{PRIVATE_LIBRARY.as_posix()}?mode=ro", uri=True) as conn:
        private_docs = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        private_paragraphs = conn.execute("SELECT COUNT(*) FROM fulltext_fts").fetchone()[0]
    return release, private_docs, private_paragraphs


def _write_landing(output: Path, release: dict, private_docs: int, private_paragraphs: int) -> None:
    counts = release.get("counts", {})
    release_hash = html.escape(str(release.get("releaseHash", "-")))
    page = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>安全依据库・本地最终版</title>
<style>
body{{max-width:920px;margin:52px auto;padding:0 24px;font:16px/1.75 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif;color:#1f2328;background:#f6f8fa}}
h1{{font-size:30px;margin-bottom:6px}}.sub{{color:#656d76;margin-bottom:28px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:18px}}
.card{{display:block;padding:24px;border:1px solid #d0d7de;border-radius:12px;background:#fff;color:inherit;text-decoration:none;box-shadow:0 2px 8px #1f232810}}
.card:hover{{border-color:#0969da;box-shadow:0 5px 18px #0969da20}}.card h2{{margin:0 0 8px;font-size:21px;color:#0969da}}
.num{{font-size:28px;font-weight:700}}.meta{{font-size:13px;color:#656d76}}
.notice{{margin-top:24px;padding:15px 18px;background:#fff8e1;border:1px solid #e5c66b;border-radius:9px}}
code{{font-size:12px;word-break:break-all}}
</style></head><body>
<h1>安全依据库・本地最终版</h1>
<div class="sub">以后日常使用双击“打开本地最终版.cmd”。两个库职责不同，但从本页统一进入。</div>
<div class="cards">
  <a class="card" href="public/index.html"><h2>查隐患、条款和依据关系</h2>
    <div><span class="num">{counts.get('hazards', 0)}</span> 条已发布隐患</div>
    <p>{counts.get('laws', 0)} 项法规/版本，{counts.get('clauses', 0)} 条已发布条款，{counts.get('links', 0)} 个关联。</p>
    <div class="meta">这是可对外分享的公开精简版。</div></a>
  <a class="card" href="fulltext/index.html"><h2>查法规全文</h2>
    <div><span class="num">{private_docs}</span> 份本地全文</div>
    <p>{private_paragraphs:,} 个可搜索段落，可跨法规检索，也可打开单部法规阅读。</p>
    <div class="meta">这是本地私有完整版，不得整体对外发布。</div></a>
</div>
<div class="notice"><b>效力提示：</b>“部分强制性条文废止”不等于整本标准废止。引用时仍应结合整本状态、具体条款状态、强制性和新旧规范冲突关系判断。OCR文字只用于检索定位，正式引用须回看原PDF。</div>
<p class="meta">发布哈希：<code>{release_hash}</code></p>
</body></html>"""
    (output / "README.html").write_text(page, encoding="utf-8", newline="\n")


def _write_launcher(output: Path) -> None:
    server = '''# -*- coding: utf-8 -*-
import http.server
import os
import socketserver
import threading
import webbrowser

os.chdir(os.path.dirname(os.path.abspath(__file__)))
with socketserver.TCPServer(("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler) as httpd:
    port = httpd.server_address[1]
    url = f"http://127.0.0.1:{port}/README.html"
    print("本地最终版已启动：" + url)
    print("关闭本窗口即可停止；私有全文不会上传到网络。")
    threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
'''
    cmd = '''@echo off\r
chcp 65001 >nul\r
cd /d "%~dp0"\r
py -3 serve_local.py\r
if errorlevel 1 (\r
  echo.\r
  echo 未能启动，请确认已安装 Python，或在此目录运行：py -3 serve_local.py\r
  pause\r
)\r
'''
    (output / "serve_local.py").write_text(server, encoding="utf-8", newline="\n")
    (output / "打开本地最终版.cmd").write_text(cmd, encoding="utf-8", newline="")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    output = _safe_output(Path(args.output))

    for required in (PUBLIC_RELEASE / "release.json", PRIVATE_LIBRARY, LIBRARY_SITE):
        if not required.exists():
            print(f"缺少必要文件：{required}", file=sys.stderr)
            return 1

    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    shutil.copytree(PUBLIC_RELEASE, output / "public")

    result = subprocess.run(
        [sys.executable, str(LIBRARY_SITE), "--library", str(PRIVATE_LIBRARY), "--output", str(output / "fulltext")],
        cwd=ROOT,
        check=False,
    )
    if result.returncode:
        return result.returncode

    release, private_docs, private_paragraphs = _counts()
    _write_landing(output, release, private_docs, private_paragraphs)
    _write_launcher(output)
    print(f"本地最终版已生成：{output}")
    print(f"统一入口：{output / '打开本地最终版.cmd'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
