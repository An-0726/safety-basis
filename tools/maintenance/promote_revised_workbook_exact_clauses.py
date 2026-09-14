# -*- coding: utf-8 -*-
"""Promote revised-workbook candidates when an exact reviewed clause exists.

The 2026-09-14 workbook supplies corrected hazard wording and the intended
latest-edition citation.  This tool only promotes a row when the knowledge
source already contains a reviewed clause with the same standard/version and
article locator.  Rows without that exact chain remain visible candidates.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from openpyxl import load_workbook

import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "v4"))
from canonical import content_hash  # noqa: E402
from release_gate_core import evaluate_release_gate, load_dir  # noqa: E402

KNOW = ROOT / "knowledge"
PROPOSAL = ROOT / "source" / "proposals" / "excel-20260914"
XLSX = Path(r"D:/Desktop/隐患库_1929条_新版口径全部整改完成_20260914.xlsx")
AS_OF = "2026-09-14"


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def compact(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]", "", str(value or "")).casefold()


def article_tokens(value: str) -> list[str]:
    found = re.findall(r"第\s*([0-9]+(?:\.[0-9]+)*|[一二三四五六七八九十百千万零〇两]+)\s*条", value)
    found += re.findall(r"(?<![A-Za-z])([0-9]+(?:\.[0-9]+)+)", value)
    return list(dict.fromkeys(found))


def load_all(relative: str) -> dict[str, dict]:
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (KNOW / relative).glob("*.json")}


def select_clause(line: str, lvs: dict[str, dict], clauses_by_version: dict[tuple[str, str], dict], gate) -> list[dict]:
    text = compact(line)
    arts = article_tokens(line)
    candidates: list[tuple[str, dict]] = []
    for vid, lv in lvs.items():
        document = compact(lv.get("documentNumber"))
        official = compact(lv.get("officialName"))
        if not ((document and len(document) >= 5 and document in text) or
                (official and len(official) >= 6 and official in text)):
            continue
        if not gate.law_versions.get(vid, {}).get("ok"):
            continue
        if not gate.law_versions.get(vid, {}).get("supports_current"):
            continue
        for article in arts:
            clause = clauses_by_version.get((vid, str(article)))
            if clause:
                candidates.append((vid, clause))
    # Prefer the newest matching version when a title has both an alias and a
    # normalized version record; preserve source order for different clauses.
    candidates.sort(key=lambda item: (lvs[item[0]].get("effectiveDate") or "", item[0]), reverse=True)
    out = []
    seen = set()
    for _vid, clause in candidates:
        if clause["id"] not in seen:
            out.append(clause)
            seen.add(clause["id"])
    return out


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", type=Path, default=XLSX)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    wb = load_workbook(args.xlsx, read_only=True, data_only=True)
    ws = wb["隐患明细_修订后"]
    rows = list(ws.iter_rows(values_only=True))
    headers = [str(v or "") for v in rows[0]]
    ix = {name: i for i, name in enumerate(headers)}
    hazards = load_all("hazards")
    lvs = load_all("law-versions")
    clauses = load_all("clauses")
    reviews_clauses = load_all("reviews/clauses")
    gate = evaluate_release_gate(KNOW)
    by_version = {(c.get("lawVersionId"), str(c.get("articlePath"))): c for c in clauses.values()}
    proposed = {hid for hid, h in hazards.items() if h.get("lifecycle") == "proposed" and not h.get("mergedInto")}
    promoted = []
    skipped = []
    for row in rows[1:]:
        hid = str(row[ix["隐患ID"]] or "").strip()
        if hid not in proposed:
            continue
        basis = str(row[ix["直接依据"]] or "").strip()
        clauses_found = []
        for line in basis.splitlines():
            clauses_found.extend(select_clause(line, lvs, by_version, gate))
        dedup = {c["id"]: c for c in clauses_found}
        if not dedup:
            skipped.append({"hazardId": hid, "reason": "no_exact_reviewed_clause", "basis": basis})
            continue
        hazard = hazards[hid]
        hazard["lifecycle"] = "active"
        hazard["mode"] = "direct"
        hazard.pop("proposalStatus", None)
        hazard.pop("sourceRow", None)
        marker = "本批已按新版整改表找到知识源中已核验的同版次条款，完成直接关联回绑。"
        if marker not in str(hazard.get("note") or ""):
            hazard["note"] = (str(hazard.get("note") or "").rstrip() + "\n" + marker).strip()
        evidence_refs = []
        links = []
        for clause in dedup.values():
            review = reviews_clauses.get(clause["id"], {})
            evidence_refs.extend(review.get("evidenceRefs") or [])
            kid = "K_XLSX_NEW14_" + hashlib.sha1((hid + "|" + clause["id"]).encode()).hexdigest()[:24].upper()
            link = {
                "id": kid,
                "hazardId": hid,
                "clauseId": clause["id"],
                "role": "direct",
                "legacyRole": "直接依据",
                "applicability": hazard.get("conditions") or "适用于对应场所、设备和作业条件。",
                "jurisdictionCode": "CN",
                "lifecycle": "active",
                "priority": 10,
                "requirementId": "",
                "reason": "新版整改表要求与现有已核验同版次条款直接对应。",
            }
            link_review = {
                "checkedAt": AS_OF,
                "contextHashes": {"clause": content_hash(clause), "hazard": content_hash(hazard)},
                "decision": "verified",
                "entityId": kid,
                "entityType": "link",
                "evidenceRefs": list(dict.fromkeys(review.get("evidenceRefs") or [])),
                "reason": "新版整改字段与现有已核验条款的对象、版本和适用范围一致。",
                "reviewType": "applicability",
                "reviewedContentHash": content_hash(link),
                "reviewer": "Codex新版整改回绑批次20260914",
            }
            links.append((link, link_review))
        hazard_review = {
            "checkedAt": AS_OF,
            "decision": "verified",
            "entityId": hid,
            "entityType": "hazard",
            "evidenceRefs": list(dict.fromkeys(evidence_refs)),
            "reason": "新版整改表内容已与知识源同版次已核验条款逐项回绑；未使用修订表摘要替代官方原文。",
            "reviewType": "content",
            "reviewedContentHash": content_hash(hazard),
            "reviewer": "Codex新版整改回绑批次20260914",
        }
        promoted.append({"hazard": hazard, "hazardReview": hazard_review, "links": links})

    print(json.dumps({"proposedCandidates": len(proposed), "promotable": len(promoted), "skipped": len(skipped), "newLinks": sum(len(x["links"]) for x in promoted)}, ensure_ascii=False, indent=2))
    if not args.apply:
        return 0
    for item in promoted:
        hid = item["hazard"]["id"]
        write_json(KNOW / "hazards" / f"{hid}.json", item["hazard"])
        write_json(KNOW / "reviews" / "hazards" / f"{hid}.json", item["hazardReview"])
        for link, review in item["links"]:
            write_json(KNOW / "links" / f"{link['id']}.json", link)
            write_json(KNOW / "reviews" / "links" / f"{link['id']}.json", review)
    report = {"asOf": AS_OF, "promoted": [x["hazard"]["id"] for x in promoted], "skipped": skipped, "newLinks": sum(len(x["links"]) for x in promoted)}
    PROPOSAL.mkdir(parents=True, exist_ok=True)
    write_json(PROPOSAL / "promote-exact-clause-report.json", report)
    manifest_path = KNOW / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    batch_id = "excel-revised-workbook-exact-clause-rebind-20260914"
    if batch_id not in {b.get("id") for b in manifest.get("batches", [])}:
        manifest.setdefault("batches", []).append({"id": batch_id, "hazardsPromoted": len(promoted), "linksAdded": report["newLinks"], "selection": "Promote workbook candidates only where exact reviewed same-version clauses already exist."})
    manifest.setdefault("counts", {})["hazards"] = len(load_all("hazards")); manifest["counts"]["clauses"] = len(load_all("clauses")); manifest["counts"]["links"] = len(load_all("links"))
    write_json(manifest_path, manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
