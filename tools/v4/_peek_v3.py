# -*- coding: utf-8 -*-
"""读取 V3 SQLite 表结构与计数（只读）。"""
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")
con = sqlite3.connect("file:source/master/safety.sqlite3?mode=ro", uri=True)
cur = con.cursor()
tabs = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("tables:", tabs)
for t in tabs:
    n = cur.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0]
    print(" ", t, n)
con.close()
