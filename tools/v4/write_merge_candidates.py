# -*- coding: utf-8 -*-
"""Phase 8: 生成 merge 候选清单文档 + 标记新增义务复述候选。"""
import glob
import io
import json
import os
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")
DOCS = os.path.join(ROOT, "docs")


def norm(s):
    s = re.sub(r"[^\w\u4e00-\u9fff]", "", str(s))
    return s.lower()


def main():
    hazards = {}
    for f in glob.glob(os.path.join(KNOW, "hazards", "*.json")):
        with io.open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        hazards[d["id"]] = d

    # 1. merge 候选：title 规范化相同分组
    groups = {}
    for hid, h in sorted(hazards.items()):
        key = norm(h.get("title", ""))
        if len(key) < 8:
            continue
        groups.setdefault(key, []).append(hid)
    dup_groups = [v for v in groups.values() if len(v) > 1]
    dup_groups.sort(key=lambda v: (-len(v), v[0]))

    lines = [
        "# V4 Merge Candidates（Phase 8 扫描输出，语义判断待最终验收）",
        "",
        "生成时间：2026-09-10",
        "来源：`tools/v4/scan_quality_v4.py` 与 `tools/v4/write_merge_candidates.py`",
        "",
        "说明：以下分组仅基于 title 规范化后的字符串相同；是否真正重复（同一隐患事实）需",
        "结合 description / conditions / places / link 覆盖做语义判断。本清单不自动执行 merge。",
        "",
        "## 分组（共 %d 组，涉及 %d 条）" % (len(dup_groups), sum(len(v) for v in dup_groups)),
        "",
    ]
    for g in dup_groups:
        h = hazards[g[0]]
        lines.append("### 组 %s（%d 条）" % (norm(h.get("title", ""))[:40], len(g)))
        lines.append("")
        for hid in g:
            hh = hazards[hid]
            lines.append("- `%s` %s | places=%s | category=%s" % (
                hid, (hh.get("title") or "")[:80], hh.get("places"), hh.get("category")))
        lines.append("")

    with io.open(os.path.join(DOCS, "V4_MERGE_CANDIDATES.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print("merge candidate groups:", len(dup_groups), "hazards:", sum(len(v) for v in dup_groups))

    # 2. 为新增义务复述候选追加 note
    OBLIG = ["H_3468C2ACFD8C44CB917C9FD791", "H_8A64C27145D64B229F53234268",
             "H_B6EF072262744FF68DE47B0341", "H_D0E34E3CC9C64F458BCCDA4674",
             "H_DE7BC85739664C5EB603237A62", "H_E07A5C9FCD4C4DE29EAAC18D6C"]
    OBLIG_TEXT = "【Phase8】义务条款复述型描述（'必须…未…'句式），非现场缺陷事实本身，FACT_NOT_HAZARD 候选；建议后续改写为隐患事实表述。"
    for hid in OBLIG:
        h = hazards[hid]
        note = h.get("note") or ""
        if "FACT_NOT_HAZARD" not in note:
            note = (note + "\n" if note else "") + OBLIG_TEXT
            h["note"] = note
            with io.open(os.path.join(KNOW, "hazards", hid + ".json"), "w", encoding="utf-8") as fh:
                json.dump(h, fh, ensure_ascii=False, indent=1)
            print("marked", hid)
    print("done")


if __name__ == "__main__":
    main()
