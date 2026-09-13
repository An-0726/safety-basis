# -*- coding: utf-8 -*-
"""应用Excel交换稿中已存在实体的字段更新。

只处理 proposal 中已有 knowledge/hazards 的250条；新增候选永不在本脚本中写入。
Excel“场所”作为适用条件补充写入，保留原 places 检索标签。
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "source" / "proposals" / "excel-20260913" / "existing-hazard-updates.json"


def digest(obj: dict) -> str:
    body = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proposal", type=Path, default=DEFAULT)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    proposal = json.loads(args.proposal.read_text(encoding="utf-8"))
    rows = proposal.get("rows") or []
    if proposal.get("kind") != "excel-existing-hazard-update-proposal-v1":
        raise SystemExit("proposal kind 不匹配")

    changes = []
    missing = []
    for row in rows:
        path = ROOT / "knowledge" / "hazards" / f"{row['hazardId']}.json"
        if not path.is_file():
            missing.append(row["hazardId"])
            continue
        obj = json.loads(path.read_text(encoding="utf-8"))
        before = digest(obj)
        fields = row["changedFields"]
        for name in ("category", "title", "description", "measures", "note"):
            obj[name] = fields.get(name, obj.get(name, ""))
        incoming_scope = row.get("incomingPlaceScope", "").strip()
        incoming_conditions = fields.get("conditions", "").strip()
        if incoming_scope and incoming_scope not in incoming_conditions:
            incoming_conditions = f"{incoming_conditions}\n适用场所：{incoming_scope}" if incoming_conditions else f"适用场所：{incoming_scope}"
        obj["conditions"] = incoming_conditions
        after = digest(obj)
        if before != after:
            changes.append({"hazardId": row["hazardId"], "path": str(path), "before": before, "after": after})
            if args.apply:
                path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    report = {
        "proposal": str(args.proposal),
        "mode": "apply" if args.apply else "dry-run",
        "proposalRows": len(rows),
        "changed": len(changes),
        "missing": missing,
        "changes": changes,
    }
    out = ROOT / "source" / "proposals" / "excel-20260913" / ("apply-report.json" if args.apply else "dry-run-report.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("mode", "proposalRows", "changed", "missing")}, ensure_ascii=False, indent=2))
    return 0 if not missing else 2


if __name__ == "__main__":
    raise SystemExit(main())
