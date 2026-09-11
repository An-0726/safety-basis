# -*- coding: utf-8 -*-
"""Phase 20 修复: 将 V3 已核验但 V4 缺失的 hazard 补迁入 V4。

来源: V3 SQLite（只读）。幂等: V4 已存在同 id 则跳过。
不建 link: 迁移本体 + note 标注待补 link/evidence review。
"""
import glob
import io
import json
import os
import re
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")
DB = os.path.join(ROOT, "source", "master", "safety.sqlite3")


def norm(s):
    s = re.sub(r"[^\w\u4e00-\u9fff]", "", str(s))
    return s.lower()


def load_v4_titles():
    out = set()
    for f in glob.glob(os.path.join(KNOW, "hazards", "*.json")):
        with io.open(f, encoding="utf-8") as fh:
            out.add(norm(json.load(fh).get("title", "")))
    return out


def main():
    v4_titles = load_v4_titles()
    existing_ids = {os.path.splitext(os.path.basename(f))[0]
                    for f in glob.glob(os.path.join(KNOW, "hazards", "*.json"))}
    con = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
    cur = con.cursor()
    rows = cur.execute(
        "SELECT id,title,description,measures,category,conditions,note,mode,checked "
        "FROM hazards WHERE status=? AND merged_into IS NULL", ("已核验",)).fetchall()
    con.close()

    added = skipped_conflict = 0
    for hid, title, desc, measures, cat, cond, note, mode, checked in rows:
        t = norm(title or "")
        if t in v4_titles:
            continue  # V4 已有等价条目（title 命中）
        if hid in existing_ids:
            # id 冲突但 title 不同：跳过并报告（不应发生）
            print("ID CONFLICT (skip):", hid, title[:40])
            skipped_conflict += 1
            continue
        h = {
            "id": hid,
            "title": title or "",
            "description": desc or "",
            "category": cat or "",
            "conditions": cond or "",
            "measures": measures or "",
            "note": (note or "") + ("\n" if note else "") +
                    "【V3迁移】migrated from V3 verified hazard on 2026-09-10; link/evidence review pending.",
            "mode": mode or "",
            "aliases": [],
            "keywords": [],
            "places": [],
            "lifecycle": "active",
            "mergedInto": None,
            "checked": checked or "",
        }
        with io.open(os.path.join(KNOW, "hazards", hid + ".json"), "w", encoding="utf-8") as fh:
            json.dump(h, fh, ensure_ascii=False, indent=1)
        v4_titles.add(t)
        added += 1
        print("migrated", hid, "|", (title or "")[:44])

    # manifest batch
    mf_path = os.path.join(KNOW, "manifest.json")
    mf = json.load(io.open(mf_path, encoding="utf-8"))
    mf["batches"].append({
        "id": "v3-verified-backfill-20260910",
        "selection": "Backfilled %d V3 verified hazards missing from V4 (title-level); links/evidence review pending for each." % added,
    })
    with io.open(mf_path, "w", encoding="utf-8") as fh:
        json.dump(mf, fh, ensure_ascii=False, indent=1)
    print("added:", added, "id-conflicts:", skipped_conflict)


if __name__ == "__main__":
    main()
