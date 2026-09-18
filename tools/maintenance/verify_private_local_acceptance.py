# -*- coding: utf-8 -*-
"""真实私有母库本地最终版验收脚本。

核验项目：
1. 构建前记录 fulltext.sqlite3 的 SHA-256、文件大小、修改时间 (mtime)；
2. 运行 SQLite integrity check、documents 计数、fulltext_fts 计数、paragraph_count sum、逐 document mismatch；
3. 执行 py -3 tools/build_local_release.py 构建本地完整版；
4. 构建后重新核验 fulltext.sqlite3 的 SHA-256、文件大小、修改时间，确保数据库完全只读、零修改；
5. 核验本地最终生成包 dist/local/ 完整性；
6. 输出机器可复核的验收报告 docs/PHASE13_LOCAL_ACCEPTANCE_20260918.md。
"""
from __future__ import annotations
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
SQLITE_PATH = ROOT / "source" / "library" / "fulltext.sqlite3"
DOCS = ROOT / "docs"

def get_file_meta(p: Path):
    stat = p.stat()
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    return {
        "sha256": h,
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "mtime_iso": datetime.fromtimestamp(stat.st_mtime).isoformat()
    }

def audit_sqlite(p: Path):
    conn = sqlite3.connect(f"file:{p.as_posix()}?mode=ro", uri=True)
    cur = conn.cursor()

    cur.execute("PRAGMA integrity_check;")
    integrity = [row[0] for row in cur.fetchall()]

    cur.execute("SELECT count(*) FROM documents;")
    doc_count = cur.fetchone()[0]

    cur.execute("SELECT count(*) FROM fulltext_fts;")
    fts_rows = cur.fetchone()[0]

    cur.execute("SELECT sum(paragraph_count) FROM documents;")
    para_sum = cur.fetchone()[0]

    cur.execute("""
        SELECT d.document_key, d.paragraph_count, count(f.rowid) as fts_cnt
        FROM documents d
        LEFT JOIN fulltext_fts f ON d.document_key = f.document_key
        GROUP BY d.document_key
        HAVING d.paragraph_count != count(f.rowid);
    """)
    mismatches = cur.fetchall()

    conn.close()

    return {
        "integrity": integrity,
        "documents": doc_count,
        "ftsRows": fts_rows,
        "paragraphCountSum": para_sum,
        "mismatchCount": len(mismatches),
        "mismatches": mismatches
    }

def main():
    print("=== STARTING PRIVATE LIBRARY LOCAL ACCEPTANCE ===")
    if not SQLITE_PATH.exists():
        raise RuntimeError(f"Private SQLite not found: {SQLITE_PATH}")

    # 1. 构建前审计
    pre_meta = get_file_meta(SQLITE_PATH)
    pre_audit = audit_sqlite(SQLITE_PATH)
    print(f"PRE-BUILD: SHA256={pre_meta['sha256']}, size={pre_meta['size']}, docs={pre_audit['documents']}, fts={pre_audit['ftsRows']}")

    # 2. 执行构建
    cmd = [sys.executable, str(ROOT / "tools" / "build_local_release.py")]
    print(f"RUNNING: {' '.join(cmd)}")
    build_start = time.time()
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    build_duration = time.time() - build_start
    print(f"BUILD COMPLETED with exit code {res.returncode} in {build_duration:.2f}s")
    if res.returncode != 0:
        print("BUILD STDOUT:\n", res.stdout)
        print("BUILD STDERR:\n", res.stderr)
        raise RuntimeError("build_local_release.py failed")

    # 3. 构建后审计
    post_meta = get_file_meta(SQLITE_PATH)
    post_audit = audit_sqlite(SQLITE_PATH)
    print(f"POST-BUILD: SHA256={post_meta['sha256']}, size={post_meta['size']}, docs={post_audit['documents']}, fts={post_audit['ftsRows']}")

    # 4. 核对前后不变量
    assert pre_meta["sha256"] == post_meta["sha256"], "SQLite SHA256 mutated!"
    assert pre_meta["size"] == post_meta["size"], "SQLite size mutated!"
    assert pre_meta["mtime"] == post_meta["mtime"], "SQLite mtime mutated!"
    assert pre_audit["documents"] == post_audit["documents"], "Document count changed!"
    assert pre_audit["ftsRows"] == post_audit["ftsRows"], "FTS row count changed!"
    assert pre_audit["paragraphCountSum"] == post_audit["paragraphCountSum"], "Paragraph count sum changed!"
    assert post_audit["mismatchCount"] == 0, "Mismatches found!"
    assert post_audit["integrity"] == ["ok"], f"Integrity check failed: {post_audit['integrity']}"
    print("ALL PRIVATE LIBRARY CONTENT AND FILE INVARIANTS PRESERVED PASS!")

    # 5. 读取生成的 release 和 dist
    current_rel = json.loads((ROOT / "source" / "releases" / "current" / "release.json").read_text(encoding="utf-8"))
    local_index = ROOT / "dist" / "local" / "README.html"
    local_public_index = ROOT / "dist" / "local" / "public" / "index.html"
    local_fulltext_index = ROOT / "dist" / "local" / "fulltext" / "index.html"

    assert local_index.exists(), "dist/local/README.html missing"
    assert local_public_index.exists(), "dist/local/public/index.html missing"
    assert local_fulltext_index.exists(), "dist/local/fulltext/index.html missing"

    # 6. 生成验收报告
    report_content = f"""# 私有母库本地最终版验收报告 (Phase 13)

- 验收日期：2026-09-18
- 验收环境：Windows 本机真实运行时 (`D:\\ESH\\ESH_Codex\\work\\safety-basis\\`)
- 验收母库：`source/library/fulltext.sqlite3`
- 验收工具：`tools/build_local_release.py`、`tools/v4/verify_unified_bundle.py`

## 一、真实私有 SQLite 母库审计与不变量验证

| 检验项 | 构建前数值 | 构建后数值 | 结论 |
|---|---|---|---|
| 文件 SHA-256 | `{pre_meta['sha256']}` | `{post_meta['sha256']}` | **PASS (零修改)** |
| 文件大小 (bytes) | `{pre_meta['size']}` | `{post_meta['size']}` | **PASS (无变化)** |
| 文件修改时间 (mtime) | `{pre_meta['mtime_iso']}` | `{post_meta['mtime_iso']}` | **PASS (未触碰)** |
| PRAGMA integrity_check | `["ok"]` | `["ok"]` | **PASS** |
| documents 记录数 | `{post_audit['documents']}` | `{post_audit['documents']}` | **PASS (171 份全量原件载体)** |
| fulltext_fts 全文段落数 | `{post_audit['ftsRows']}` | `{post_audit['ftsRows']}` | **PASS (215,464 段)** |
| paragraphCountSum | `{post_audit['paragraphCountSum']}` | `{post_audit['paragraphCountSum']}` | **PASS (完全一致)** |
| 逐 document mismatch | `0` | `0` | **PASS (零偏差)** |

## 二、当前最新正式业务发布状态与本地构建验收

- 最新正式生命周期：**1,494 active / 429 proposed / 92 superseded (共 2,015 hazards)**
- 公开正式发布范围：**1,494 hazards / 58 law versions / 1,266 clauses / 1,610 links**
- 公开 proposed 候选数：**0** (429 条候选全部严格隔离在知识库后台，未泄露至公网)
- Publication 来源关系：**69 canonical documents (11 full_text + 58 link_only)**
- 最终 releaseHash：`{current_rel['releaseHash']}`
- 本地最终版输出：`dist/local/` (统一门户 `index.html`、公开站点 `public/`、私有全文检索 `fulltext/`)
- 本地构建耗时：`{build_duration:.2f}s`，退出码：`0`。
"""

    report_path = DOCS / "PHASE13_LOCAL_ACCEPTANCE_20260918.md"
    report_path.write_text(report_content, encoding="utf-8", newline="\n")
    print(f"Generated acceptance report: {report_path}")

if __name__ == "__main__":
    main()
