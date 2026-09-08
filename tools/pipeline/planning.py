"""Group private source citations before any model translation or legal review.

Names/numbers extracted here are search hints, never confirmed legal identities.
No writes to the staging database, master or website; source rows stay separate.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3

import intake
import review

FORMAT = "safety-work-plan-v1"
STANDARD = re.compile(
    r"(?<![A-Za-z])(?P<prefix>(?:GBZ?|AQ|HG|SH|SY|JB|DL|JT|JGJ|CJJ|HJ|WS|XF|GA|TSG|DB\d{2,6})"
    r"(?:\s*/\s*T)?)\s*(?P<number>\d{2,6}(?:\.\d{1,4})?)"
    r"(?:\s*[-—–－]\s*(?P<year>(?:19|20)\d{2}))?(?!\d)", re.I)
TITLE = re.compile(r"《([^《》\n]{2,120})》")
ARTICLE = re.compile(r"第[零〇一二三四五六七八九十百千万两\d]+条(?:之[一二三四五六七八九十\d]+)?"
                     r"(?:第[零〇一二三四五六七八九十百两\d]+款)?(?:第[（(]?[一二三四五六七八九十\d]+[）)]?项)?")
BARE_LAW = re.compile(r"(?:中华人民共和国|江苏省|南京市)[\u4e00-\u9fff]{1,35}?(?:条例|办法|规定|法)(?=[（(第，,。；;\s]|$)")


def extract_references(value):
    """Extract exact cited versions; never silently collapse GB and GB/T."""
    value = intake.norm(value)
    titles = list(TITLE.finditer(value))
    standards, assigned_titles = [], set()
    for match in STANDARD.finditer(value):
        prefix = re.sub(r"\s+", "", match["prefix"].upper())
        number, year = match["number"], match["year"] or ""
        family = prefix + " " + number
        before = [t for t in titles if t.end() <= match.start() and match.start() - t.end() < 30]
        after = [t for t in titles if t.start() >= match.end() and t.start() - match.end() < 8]
        # Only attach an adjacent name when no intervening standard exists.
        title = before[-1] if before else after[0] if after else None
        name = ""
        if title and not STANDARD.search(value[title.end():match.start()]):
            name = title[1].strip()
            assigned_titles.add(title.span())
        standards.append({"key": family + ("-" + year if year else ""),
                          "kind": "standard", "family": family, "citedVersion": year, "nameHint": name})
    laws = [{"key": "NAME:" + t[1].strip(), "kind": "named-document",
             "family": t[1].strip(), "citedVersion": "", "nameHint": t[1].strip()}
            for t in titles if t.span() not in assigned_titles]
    if not titles:
        laws.extend({"key": "NAME:" + m[0], "kind": "named-document", "family": m[0],
                     "citedVersion": "", "nameHint": m[0]} for m in BARE_LAW.finditer(value))
    unique = {}
    for row in standards + laws:
        unique.setdefault(row["key"], row)
    return {"documents": list(unique.values()), "articleHints": sorted(set(ARTICLE.findall(value))),
            "hasMultipleDocuments": len(unique) > 1, "unparsed": bool(value) and not unique}


def collect(db):
    db = Path(db).resolve()
    with closing(sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN")
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("staging integrity check failed")
        sources = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM sources")}
        locations = {}
        for row in conn.execute("SELECT * FROM source_locations ORDER BY original_path"):
            locations.setdefault(row["source_id"], []).append(row["original_path"])
        candidates = []
        for row in conn.execute("SELECT * FROM candidates ORDER BY id"):
            record = json.loads(row["normalized_json"])
            origins = [dict(r) for r in conn.execute(
                "SELECT DISTINCT r.id sourceRowId,r.source_id sourceId,r.sheet,r.row_number rowNumber "
                "FROM candidate_sources c JOIN source_rows r ON c.source_row_id=r.id "
                "JOIN import_runs i ON c.run_id=i.id WHERE c.candidate_id=? AND i.status='complete' "
                "ORDER BY r.source_id,r.sheet,r.row_number", (row["id"],))]
            candidates.append({"candidateId": row["id"], "record": record, "origins": origins})
        runs = [dict(r) for r in conn.execute("SELECT * FROM import_runs ORDER BY id")]
        raw_row_count = conn.execute("SELECT COUNT(*) FROM source_rows").fetchone()[0]
    return candidates, sources, locations, runs, raw_row_count


def prepare(db):
    candidates, sources, locations, runs, raw_rows = collect(db)
    requirements, groups, unparsed, empty_basis = {}, {}, [], []
    outcomes = Counter()
    for item in candidates:
        row, ident = item["record"], item["candidateId"]
        basis, quote = row.get("basis", ""), row.get("quote", "")
        outcomes[row.get("compliance", "") or "未提供"] += len(item["origins"])
        found = extract_references(basis)
        if not basis:
            empty_basis.append(ident)
        elif found["unparsed"]:
            unparsed.append({"candidateId": ident, "basis": basis, "origins": item["origins"]})
        for ref in found["documents"]:
            entry = requirements.setdefault(ref["key"], {**ref, "candidateIds": [], "sourceRowIds": set(),
                "nameHints": set(), "articleHints": set(), "coCitedDocuments": set(), "status": "待定位官方版本"})
            entry["candidateIds"].append(ident)
            entry["sourceRowIds"].update(o["sourceRowId"] for o in item["origins"])
            entry["articleHints"].update(found["articleHints"])
            entry["nameHints"].update([ref["nameHint"]] if ref["nameHint"] else [])
            entry["coCitedDocuments"].update(r["key"] for r in found["documents"] if r["key"] != ref["key"])
        # An identical normative requirement is a model-work group, not an
        # assertion that different site observations are the same event.
        group_id = "G_" + intake.digest(intake.dumps([basis, quote]))
        group = groups.setdefault(group_id, {"groupId": group_id, "basis": basis, "quote": quote,
            "referenceKeys": [r["key"] for r in found["documents"]], "candidateIds": [], "sourceRows": [],
            "status": "待整理", "emptyRequirement": not basis or not quote})
        group["candidateIds"].append(ident)
        group["sourceRows"].extend(item["origins"])
        item["requirementGroupId"] = group_id
        item["referenceKeys"] = [r["key"] for r in found["documents"]]
    for entry in requirements.values():
        for field in ("sourceRowIds", "nameHints", "articleHints", "coCitedDocuments"):
            entry[field] = sorted(entry[field])
        entry["sourceRowCount"] = len(entry["sourceRowIds"])
    queue = sorted(requirements.values(), key=lambda r: (-r["sourceRowCount"], r["key"]))
    return {"formatVersion": FORMAT,
        "summary": {"sources": len(sources), "rawRows": raw_rows, "candidates": len(candidates),
                    "requirementGroups": len(groups), "citedDocumentKeys": len(queue),
                    "standardFamilies": len({r["family"] for r in queue if r["kind"] == "standard"}),
                    "unparsedBasisCount": len(unparsed), "emptyBasisCount": len(empty_basis),
                    "sourceOutcomes": dict(outcomes)},
        "sources": [{**row, "locations": locations.get(ident, [])} for ident, row in sources.items()],
        "importRuns": runs, "lawQueue": queue,
        "requirementGroups": sorted(groups.values(), key=lambda r: (-len(r["sourceRows"]), r["groupId"])),
        "candidates": candidates, "unparsedBasis": unparsed, "emptyBasisCandidateIds": empty_basis}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = prepare(args.staging)
    review.write_json(args.output, data)
    print(json.dumps(data["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
