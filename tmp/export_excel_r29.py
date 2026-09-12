# -*- coding: utf-8 -*-
"""把 V4 隐患知识导出为 Excel，供人工审查。

一张主表「隐患明细」+ 一张「说明」。每条隐患一行，列出标题、描述、依据（法规/条款/原文）、
整改措施、适用条件、分类场所、发布状态，便于逐条核对。
"""
import glob
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = r"D:\ESH\ESH_Codex\work\safety-basis"
KNOW = os.path.join(ROOT, "knowledge")
OUT = r"C:\Users\XGZ\Desktop\隐患库数据审查_20260913.xlsx"


def load(rel):
    o = {}
    for f in glob.glob(os.path.join(KNOW, rel, "*.json")):
        d = json.load(io.open(f, encoding="utf-8"))
        o[d.get("id")] = d
    return o


haz = load("hazards")
links = load("links")
clauses = load("clauses")
lvs = load("law-versions")
laws = load("laws")

# link review（取 decision 与 role）
rev = {}
for f in glob.glob(os.path.join(KNOW, "reviews", "links", "*.json")):
    d = json.load(io.open(f, encoding="utf-8"))
    rev[d.get("entityId")] = d

byh = {}
for k, l in links.items():
    byh.setdefault(l.get("hazardId"), []).append((k, l))

ORDER = {"direct": 0, "supporting": 1, "fallback": 2}
pub = set()
_m = json.load(io.open(os.path.join(ROOT, "source", "releases", "unified-v4-reviewed-20260913-r29", "data", "manifest.json"), encoding="utf-8"))
for shard in _m["hazardShards"]:
    for row in json.load(io.open(os.path.join(ROOT, "source", "releases", "unified-v4-reviewed-20260913-r29", shard["url"]), encoding="utf-8"))["records"]:
        pub.add(row["id"])
wants = sorted((h for h in haz.values() if h["id"] in pub and not h.get("mergedInto") and h.get("lifecycle") == "active"),
               key=lambda x: (x.get("category") or "", x.get("title") or ""))

wb = Workbook()
ws = wb.active
ws.title = "隐患明细"
HEAD = ["序号", "隐患ID", "主题", "场所", "隐患名称（标题）", "隐患专业描述",
        "直接依据", "依据原文", "补充/兜底依据", "整改措施", "适用条件", "备注", "可发布"]
ws.append(HEAD)

hfill = PatternFill("solid", fgColor="DDEBF7")
for c in range(1, len(HEAD) + 1):
    cell = ws.cell(row=1, column=c)
    cell.font = Font(bold=True)
    cell.fill = hfill
    cell.alignment = Alignment(vertical="center", horizontal="center", wrap_text=True)

n = 0
for h in wants:
    hid = h["id"]
    bases = sorted(byh.get(hid, []), key=lambda x: ORDER.get(x[1].get("role"), 9))
    direct_txt, quote_txt, other_txt = [], [], []
    publishable = False
    for k, l in bases:
        rv = rev.get(k) or {}
        dec = rv.get("decision")
        role = l.get("role")
        c = clauses.get(l.get("clauseId")) or {}
        v = lvs.get(c.get("lawVersionId")) or {}
        law = laws.get(v.get("lawId")) or {}
        name = law.get("canonicalName") or v.get("officialName") or ""
        doc = v.get("documentNumber") or ""
        path = c.get("articlePath") or ""
        label = "《%s》%s%s" % (name, doc and doc + " " or "", path)
        if dec == "verified":
            if role == "direct":
                direct_txt.append(label)
                quote_txt.append(c.get("quote") or "")
                publishable = True
            elif role == "fallback":
                direct_txt.append(label + "（兜底）")
                quote_txt.append(c.get("quote") or "")
                publishable = True
            else:
                other_txt.append(label + "（补充）")
    n += 1
    ws.append([
        n, hid, h.get("category") or "", "、".join(h.get("places") or []),
        h.get("title") or "", h.get("description") or "",
        "\n".join(direct_txt), "\n\n".join(quote_txt),
        "\n".join(other_txt), h.get("measures") or "",
        h.get("conditions") or "", h.get("note") or "",
        "是" if publishable else "否",
    ])

widths = [5, 26, 12, 14, 34, 46, 34, 60, 26, 50, 26, 40, 7]
for i, w in enumerate(widths, start=1):
    ws.column_dimensions[get_column_letter(i)].width = w
ws.freeze_panes = "E2"
for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
    for c in row:
        c.alignment = Alignment(vertical="top", wrap_text=True)

# 说明页
ws2 = wb.create_sheet("说明")
for line in [
    ["数据来源", "Safety Basis V4 knowledge/（r29，2026-09-13 发布版）"],
    ["导出时间", "2026-09-13"],
    ["隐患总数", n],
    ["", ""],
    ["列说明", ""],
    ["隐患名称（标题）", "现场缺陷的一句话表述，已去除条款序号、企业特定位置等"],
    ["隐患专业描述", "比标题更完整的表述，含情境"],
    ["直接依据", "经核验适用的法规/标准条款；标注（兜底）的为缺少专项条款时的上位法兜底"],
    ["依据原文", "该条款的官方原文"],
    ["补充/兜底依据", "补充性依据（supporting），不能单独支撑发布"],
    ["整改措施", "针对该隐患的可执行整改动作"],
    ["适用条件", "该隐患适用的场所/设备范围"],
    ["可发布", "“是”= 至少有 1 条通过门禁的直接或兜底依据"],
    ["", ""],
    ["未列入", "已合并（superseded）及未达发布标准的条目未导出；发布集 %d 条" % len(pub)],
]:
    ws2.append(line)
ws2.column_dimensions["A"].width = 18
ws2.column_dimensions["B"].width = 70
for row in ws2.iter_rows(min_row=1, max_row=ws2.max_row):
    row[0].font = Font(bold=True)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
wb.save(OUT)
print("已导出:", OUT)
print("隐患行数:", n)
