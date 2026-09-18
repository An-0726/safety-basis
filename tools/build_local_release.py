# -*- coding: utf-8 -*-
"""生成唯一的本地使用版：当前正式公开库 + 私有法规全文库。

``source/releases/current`` 是生成物，不再提交 Git。本脚本每次运行都会先按当天日期
校验 knowledge、重建当前正式公开包，再组合本地私有全文入口。私有 PDF/SQLite 只读，
不会被公开构建器修改。
"""
from __future__ import annotations

import argparse
from datetime import date
import html
import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "dist" / "local"
RELEASES = ROOT / "source" / "releases"
PUBLIC_RELEASE = RELEASES / "current"
SELECTION = RELEASES / "site-selection.json"
PRIVATE_LIBRARY = ROOT / "source" / "library" / "fulltext.sqlite3"
LIBRARY_SITE = ROOT / "tools" / "v4" / "library_site.py"
VALIDATE = ROOT / "tools" / "v4" / "validate_all.py"
STRICT_AUDIT = ROOT / "tools" / "v4" / "strict_release_audit.py"
BUILD_PUBLIC = ROOT / "tools" / "v4" / "build_unified_release.py"
VERIFY_PUBLIC = ROOT / "tools" / "v4" / "verify_unified_bundle.py"


def _safe_output(path: Path) -> Path:
    resolved = path.resolve()
    dist_root = (ROOT / "dist").resolve()
    if resolved == dist_root or dist_root not in resolved.parents:
        raise ValueError("输出目录必须位于仓库 dist/ 之下")
    return resolved


def _run(*args: str) -> bool:
    result = subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, check=False)
    return result.returncode == 0


def _rebuild_public() -> bool:
    """从当前源码重建公开正式包，不读取旧发布快照。"""
    if not _run(VALIDATE):
        return False
    if not _run(STRICT_AUDIT):
        return False
    if PUBLIC_RELEASE.exists():
        for _ in range(3):
            try:
                shutil.rmtree(PUBLIC_RELEASE)
                break
            except Exception:
                import time
                time.sleep(0.3)
        if PUBLIC_RELEASE.exists():
            subprocess.run(["powershell", "-NoProfile", "-Command", f"Remove-Item -Recurse -Force '{PUBLIC_RELEASE}'"], check=False)
    if SELECTION.exists():
        SELECTION.unlink()

    as_of = date.today().isoformat()
    data_version = date.today().strftime("%Y.%m.%d") + ".local"
    if not _run(BUILD_PUBLIC, "--out", PUBLIC_RELEASE, "--as-of", as_of,
                "--data-version", data_version):
        return False

    release = json.loads((PUBLIC_RELEASE / "release.json").read_text(encoding="utf-8"))
    RELEASES.mkdir(parents=True, exist_ok=True)
    SELECTION.write_text(json.dumps({
        "schemaVersion": "safety-site-selection-v1",
        "bundle": "current",
        "releaseHash": release["releaseHash"],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return _run(VERIFY_PUBLIC, "--bundle", PUBLIC_RELEASE)


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
<div class="sub">日常使用双击“打开本地最终版.cmd”。公开正式库与私有全文库职责不同，但从本页统一进入。</div>
<div class="cards">
  <a class="card" href="public/index.html"><h2>查隐患、条款和依据关系</h2>
    <div><span class="num">{counts.get('hazards', 0)}</span> 条当前已核验隐患</div>
    <p>{counts.get('laws', 0)} 个实际引用法规版本，{counts.get('clauses', 0)} 条正式条款，{counts.get('links', 0)} 个正式关联。</p>
    <div class="meta">只包含当天 Gate 通过的正式公开投影；候选留在 knowledge 后台。</div></a>
  <a class="card" href="fulltext/index.html"><h2>查法规全文</h2>
    <div><span class="num">{private_docs}</span> 份本地全文</div>
    <p>{private_paragraphs:,} 个可搜索段落，可跨法规检索，也可打开单部法规阅读。</p>
    <div class="meta">这是本地私有完整版，不得整体对外发布。</div></a>
</div>
<div class="notice"><b>效力提示：</b>“最新发布”不等于“当前适用”。尚未实施的 upcoming 版本不能支撑当前正式隐患；OCR 只用于定位，正式引用须回看官方原文或原 PDF。</div>
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

    for required in (PRIVATE_LIBRARY, LIBRARY_SITE, VALIDATE, STRICT_AUDIT, BUILD_PUBLIC, VERIFY_PUBLIC):
        if not required.exists():
            print(f"缺少必要文件：{required}", file=sys.stderr)
            return 1

    if not _rebuild_public():
        print("当前正式公开包重建/验证失败，已停止生成本地最终版。", file=sys.stderr)
        return 1

    if output.exists():
        for _ in range(3):
            try:
                shutil.rmtree(output)
                break
            except Exception:
                import time
                time.sleep(0.3)
        if output.exists():
            subprocess.run(["powershell", "-NoProfile", "-Command", f"Remove-Item -Recurse -Force '{output}'"], check=False)
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
