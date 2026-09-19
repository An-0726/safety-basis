# -*- coding: utf-8 -*-
"""Stage the 2026-09-14 revised workbook into the knowledge source.

The workbook is an editorial correction source, not an official standard-text
source.  Revised rows are therefore staged as lifecycle=proposed until their
direct clause, evidence snapshot, and applicability review are rebound.  Rows
that already had a formal active entity are preserved in the archive and are
not silently treated as formally re-reviewed by this import.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_XLSX = Path(r"D:/Desktop/隐患库_1929条_新版口径全部整改完成_20260914.xlsx")
KNOW = ROOT / "knowledge"
OUT_DIR = ROOT / "source" / "proposals" / "excel-20260914"
AS_OF = "2026-09-14"


def digest(value: dict) -> str:
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def load_dir(relative: str) -> dict[str, dict]:
    directory = KNOW / relative
    return {
        p.stem: json.loads(p.read_text(encoding="utf-8"))
        for p in directory.glob("*.json")
    }


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def split_places(value: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"[、,，;；/]+", str(value or "")) if p.strip()]
    return list(dict.fromkeys(parts))


def append_note(old: str, basis: str, explanation: str, status: str) -> str:
    marker = "【2026-09-14新版整改表】"
    text = str(old or "").strip()
    text = "\n\n".join(p for p in (text, f"{marker} 修订状态：{status}。直接依据：{basis or '未填写'}。修订说明：{explanation or '见新版整改表。'}") if p)
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not args.xlsx.is_file():
        raise SystemExit(f"Excel 不存在: {args.xlsx}")

    workbook = load_workbook(args.xlsx, read_only=True, data_only=True)
    if "隐患明细_修订后" not in workbook.sheetnames:
        raise SystemExit("缺少隐患明细_修订后工作表")
    ws = workbook["隐患明细_修订后"]
    rows = list(ws.iter_rows(values_only=True))
    headers = [str(v or "") for v in rows[0]]
    ix = {name: i for i, name in enumerate(headers)}
    required = {"序号", "隐患ID", "主题", "场所", "隐患名称（标题）", "隐患专业描述",
                "直接依据", "整改措施", "适用条件", "备注", "可发布", "修订状态", "修订说明"}
    missing_headers = required - set(ix)
    if missing_headers:
        raise SystemExit(f"工作表缺少字段: {sorted(missing_headers)}")

    hazards = load_dir("hazards")
    changed: list[dict] = []
    added: list[dict] = []
    preserved: list[str] = []
    merged: list[str] = []
    for row in rows[1:]:
        hid = str(row[ix["隐患ID"]] or "").strip()
        if not hid:
            continue
        status = str(row[ix["修订状态"]] or "").strip()
        revised = status == "已修订"
        basis = str(row[ix["直接依据"]] or "").strip()
        explanation = str(row[ix["修订说明"]] or "").strip()
        title = str(row[ix["隐患名称（标题）"]] or "").strip()
        description = str(row[ix["隐患专业描述"]] or "").strip()
        measures = str(row[ix["整改措施"]] or "").strip()
        conditions = str(row[ix["适用条件"]] or "").strip()
        topic = str(row[ix["主题"]] or "").strip()
        places = split_places(row[ix["场所"]])
        if hid in hazards:
            if not revised:
                preserved.append(hid)
                continue
            obj = dict(hazards[hid])
            before = digest(obj)
            obj["title"] = title or obj.get("title", "")
            obj["description"] = description or obj.get("description", "")
            obj["measures"] = measures or obj.get("measures", "")
            obj["conditions"] = conditions or obj.get("conditions", "")
            if topic:
                obj["category"] = topic
            old_places = list(obj.get("places") or [])
            obj["places"] = list(dict.fromkeys(old_places + places)) or old_places
            obj["note"] = append_note(obj.get("note", ""), basis, explanation, status)
            obj["revisionSource"] = "隐患库_1929条_新版口径全部整改完成_20260914.xlsx"
            obj["revisionDate"] = AS_OF
            obj["revisionState"] = "workbook-revised-pending-clause-rebind"
            if obj.get("mergedInto"):
                merged.append(hid)
            else:
                obj["lifecycle"] = "proposed"
                obj["mode"] = "candidate"
                obj["proposalStatus"] = "workbook_revised_pending_clause_rebind"
                obj["sourceRow"] = int(row[ix["序号"]]) if str(row[ix["序号"]] or "").isdigit() else row[ix["序号"]]
            after = digest(obj)
            if before != after:
                changed.append({"hazardId": hid, "before": before, "after": after, "status": status})
                if args.apply:
                    write_json(KNOW / "hazards" / f"{hid}.json", obj)
        else:
            # The workbook contains 1929 IDs while the current V4 knowledge
            # source contains fewer.  Admit missing rows as visible candidates
            # so the coverage gap is explicit, without inventing clause proof.
            obj = {
                "id": hid,
                "title": title,
                "description": description,
                "measures": measures,
                "conditions": conditions,
                "category": topic or "未分类",
                "places": places,
                "aliases": [],
                "keywords": [title] if title else [],
                "lifecycle": "proposed",
                "mode": "candidate",
                "proposalStatus": "workbook_revised_pending_clause_rebind",
                "sourceRow": int(row[ix["序号"]]) if str(row[ix["序号"]] or "").isdigit() else row[ix["序号"]],
                "revisionSource": "隐患库_1929条_新版口径全部整改完成_20260914.xlsx",
                "revisionDate": AS_OF,
                "revisionState": "workbook-revised-pending-clause-rebind",
                "note": append_note(str(row[ix["备注"]] or ""), basis, explanation, status),
            }
            added.append({"hazardId": hid, "status": status})
            if args.apply:
                write_json(KNOW / "hazards" / f"{hid}.json", obj)

    report = {
        "asOf": AS_OF,
        "source": str(args.xlsx),
        "mode": "apply" if args.apply else "dry-run",
        "workbookRows": len(rows) - 1,
        "changedExisting": len(changed),
        "addedMissing": len(added),
        "preservedPassing": len(preserved),
        "mergedRevised": len(merged),
        "changed": changed,
        "added": added,
        "note": "修订表摘要不是官方条文原文；所有修订项需完成条款、证据和适用性回绑后才能进入正式依据门禁。",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / ("apply-report.json" if args.apply else "dry-run-report.json")).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    if args.apply:
        manifest_path = KNOW / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        batch_id = "excel-revised-workbook-stage-20260914"
        if batch_id not in {b.get("id") for b in manifest.get("batches", [])}:
            manifest.setdefault("batches", []).append({
                "id": batch_id,
                "hazardsAdded": len(added),
                "hazardsUpdated": len(changed),
                "hazardsStaged": len(changed) + len(added),
                "selection": "Stage the 2026-09-14 revised workbook; revised and missing rows remain proposed until exact clause/evidence/applicability rebinding.",
            })
        manifest.setdefault("counts", {})["hazards"] = len(load_dir("hazards"))
        manifest["counts"]["clauses"] = len(load_dir("clauses"))
        manifest["counts"]["links"] = len(load_dir("links"))
        write_json(manifest_path, manifest)
    print(json.dumps({k: report[k] for k in ("mode", "workbookRows", "changedExisting", "addedMissing", "preservedPassing", "mergedRevised")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
