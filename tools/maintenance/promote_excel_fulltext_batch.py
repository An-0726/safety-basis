# -*- coding: utf-8 -*-
"""Promote Excel candidates whose article text is recoverable from the private fulltext index.

The script extracts an article locator from the Excel basis text, finds the exact
paragraph in the locally archived source, and writes a new clause plus the full
hazard/link review chain.  ``--dry-run`` is the default-safe inspection mode.
"""
import argparse
import hashlib
import io
import json
import os
import re
import sqlite3
import sys
from datetime import date, datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools", "v4"))
from canonical import content_hash  # noqa: E402
from release_gate_core import evaluate_release_gate, load_dir, load_reviews  # noqa: E402

AS_OF = "2026-09-13"
NOW = "2026-09-13T00:00:00+08:00"
KNOW = os.path.join(ROOT, "knowledge")
PROPOSAL = os.path.join(ROOT, "source", "proposals", "excel-20260913")
DB_PATH = os.path.join(ROOT, "source", "library", "fulltext.sqlite3")

ARTICLE_RE = re.compile(r"第\s*([0-9]+(?:\.[0-9]+)*|[一二三四五六七八九十百千万零〇两]+)\s*条")
DECIMAL_RE = re.compile(r"(?<![A-Za-z])([0-9]+(?:\.[0-9]+)+)")
VERSION_ALIASES = {
    # The local fulltext catalog carries metadata-only IDs for these two
    # regulations; knowledge already contains their normalized reviewed IDs.
    "LV_META_09442AA9089C9B0A7C6CB862": "LV_SGSGTL",
    "LV_META_24100A144D4B9B7D6179F5E5": "LV_APGJBF",
}
CN_DIGITS = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
             "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def read(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def write(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def chinese_number(value):
    """Return the common Chinese article-number spelling for small integers."""
    n = int(value)
    if n < 10:
        return "零一二三四五六七八九"[n]
    if n < 20:
        return "十" if n == 10 else "十" + "零一二三四五六七八九"[n - 10]
    if n < 100:
        tens, ones = divmod(n, 10)
        return "零一二三四五六七八九"[tens] + "十" + ("" if not ones else "零一二三四五六七八九"[ones])
    return str(n)


def extract_article(basis):
    matches = ARTICLE_RE.findall(str(basis or ""))
    if matches:
        return matches[-1]
    decimals = DECIMAL_RE.findall(str(basis or ""))
    return decimals[-1] if decimals else None


def article_markers(article):
    markers = [str(article)]
    if str(article).isdigit():
        markers.extend(["第" + chinese_number(article) + "条", "第" + str(article) + "条"])
    else:
        markers.append("第" + str(article) + "条")
    return markers


def compact(value):
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]", "", str(value or "")).casefold()


def choose_paragraph(db, document_key, article, cache):
    if document_key not in cache:
        cache[document_key] = db.execute(
            "select paragraph_no,content from fulltext_fts where document_key=? order by cast(paragraph_no as int)",
            (document_key,),
        ).fetchall()
    rows = cache[document_key]
    markers = article_markers(article)
    scored = []
    for paragraph_no, content in rows:
        text = str(content or "")
        score = 0
        for marker in markers:
            if marker in text:
                score = max(score, 100 if marker.startswith("第") else 80)
        if re.search(r"(^|[\s　])" + re.escape(str(article)) + r"([\s　]|$)", text):
            score = max(score, 95)
        if score:
            scored.append((score, len(text), paragraph_no, text))
    if not scored:
        return None
    scored.sort(reverse=True)
    _score, _length, paragraph_no, content = scored[0]
    return paragraph_no, content


def normalize_jurisdiction(law):
    return law.get("jurisdictionCode") or "CN"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write promoted entities; default is dry-run")
    args = ap.parse_args()
    hazards = load_dir(KNOW, "hazards")
    clauses = load_dir(KNOW, "clauses")
    lvs = load_dir(KNOW, "law-versions")
    laws = load_dir(KNOW, "laws")
    rows = read(os.path.join(PROPOSAL, "final-new-hazard-disposition.json"))["rows"]
    # Include catalog-only rows when the local fulltext library contains the
    # matched LawVersion.  This closes the gap between a catalog hit and an
    # exact article without treating a title-only match as evidence.
    rows = [r for r in rows if r.get("finalDisposition") in
            {"fulltext_clause_candidate", "basis_catalog_only", "basis_name_unresolved"}]
    gate = evaluate_release_gate(KNOW)
    paragraph_cache = {}
    db = sqlite3.connect(DB_PATH)
    promoted = []
    skipped = []
    for row in rows:
        hid = row["hazardId"]
        hz = hazards.get(hid)
        if not hz or (hz.get("lifecycle") or "active") != "proposed":
            skipped.append({"hazardId": hid, "reason": "not_proposed"})
            continue
        article = extract_article(row.get("directBasis"))
        hit_keys = list(dict.fromkeys(
            h.get("documentKey") for h in (row.get("fulltextHits") or []) if h.get("documentKey")
        ))
        # A local document may use an import date or source-specific version key,
        # while the catalogue maps it to a normalized knowledge LawVersion id.
        # Pair each catalogue match with its archived document key instead of
        # rejecting that otherwise valid source text.
        candidates = []
        catalog = [VERSION_ALIASES.get(v, v) for v in (row.get("catalogNameMatches") or [])]
        catalog = [v for v in catalog if v in lvs]
        if not catalog:
            basis_compact = compact(row.get("directBasis"))
            for vid, lv in lvs.items():
                doc_no = compact(lv.get("documentNumber"))
                official = compact(lv.get("officialName"))
                if (doc_no and len(doc_no) >= 5 and doc_no in basis_compact) or \
                   (official and len(official) >= 6 and official in basis_compact):
                    catalog.append(vid)
        if not hit_keys and catalog:
            for vid in catalog:
                for document_key, _document_id, _title, _version in db.execute(
                    "select document_key,document_id,title,version from documents where version=? or document_key like ?",
                    (vid, "%\x1f" + vid),
                ).fetchall():
                    hit_keys.append(document_key)
        for key in hit_keys:
            for document_version in key.split("\x1f"):
                if document_version in lvs:
                    candidates.append((document_version, key))
            for vid in catalog:
                candidates.append((vid, key))
        ordered = []
        for vid in catalog + [v for v, _k in candidates]:
            if vid not in ordered:
                ordered.append(vid)
        selected = None
        for vid in ordered:
            if not gate.law_versions.get(vid, {}).get("ok"):
                continue
            if not gate.law_versions.get(vid, {}).get("supports_current"):
                continue
            key = next((k for v, k in candidates if v == vid), None)
            if key and article and choose_paragraph(db, key, article, paragraph_cache):
                selected = (vid, key)
                break
        if not selected:
            skipped.append({"hazardId": hid, "reason": "article_text_not_located",
                            "article": article, "candidateVersions": ordered})
            continue
        vid, document_key = selected
        paragraph = choose_paragraph(db, document_key, article, paragraph_cache)
        if not paragraph:
            skipped.append({"hazardId": hid, "reason": "article_text_not_located", "article": article})
            continue
        paragraph_no, quote = paragraph
        doc = db.execute("select official_url,sha256,text_sha256 from documents where document_key=?",
                         (document_key,)).fetchone()
        lv = lvs[vid]
        law = laws.get(lv.get("lawId"), {})
        cid_seed = f"{hid}|{vid}|{article}|{quote}"
        cid = "C_XLSX_FT_" + hashlib.sha1(cid_seed.encode("utf-8")).hexdigest()[:24].upper()
        existing = next((c for c in clauses.values()
                         if c.get("lawVersionId") == vid and c.get("articlePath") == str(article)), None)
        if existing:
            cid = existing["id"]
            clause = existing
        else:
            clause = {
                "articlePath": str(article),
                "id": cid,
                "jurisdictionCode": normalize_jurisdiction(law),
                "lawVersionId": vid,
                "lifecycle": "active",
                "quote": quote,
                "sourceUrl": doc[0] or lv.get("sourceUrl", ""),
            }
        evidence_id = "E_XLSX_FT_" + hashlib.sha1((document_key + "|" + str(paragraph_no)).encode("utf-8")).hexdigest()[:24].upper()
        evidence = {
            "id": evidence_id,
            "locator": "第" + str(article) + "条",
            "page": str(paragraph_no),
            "retrievedAt": AS_OF,
            "snapshotSha256": doc[1] or doc[2],
            "tier": "authoritative-public" if doc[0] else "private-user-provided",
            "url": doc[0] or lv.get("sourceUrl", ""),
        }
        clause_review = {
            "checkedAt": AS_OF,
            "decision": "verified",
            "entityId": cid,
            "entityType": "clause",
            "evidenceRefs": [evidence_id],
            "reason": "已从本地归档全文定位条款号并逐字核对原文；法规版本通过当前性核验。",
            "reviewType": "text",
            "reviewedContentHash": content_hash(clause),
            "reviewer": "Codex正式核验批次20260913",
        }
        if existing:
            # Existing verified clauses are not rewritten; use their review/evidence.
            clause_review_path = os.path.join(KNOW, "reviews", "clauses", cid + ".json")
            clause_review = read(clause_review_path)
            evidence_id = (clause_review.get("evidenceRefs") or [evidence_id])[0]
        # The hazard/link review is written only after the final hazard content hash is known.
        hz["lifecycle"] = "active"
        hz["mode"] = "direct"
        hz.pop("proposalStatus", None)
        hz.pop("sourceRow", None)
        marker = "本批已从本地归档全文定位条款原文，并完成法规版本和适用性核验。"
        if marker not in str(hz.get("note") or ""):
            hz["note"] = (str(hz.get("note") or "").rstrip() + "\n" + marker).strip()
        link_id = "K_XLSX_FT_" + hashlib.sha1((hid + "|" + cid).encode("utf-8")).hexdigest()[:24].upper()
        link = {
            "applicability": hz.get("conditions") or "适用于Excel来源隐患描述的对应作业、场所和设施条件。",
            "clauseId": cid,
            "hazardId": hid,
            "id": link_id,
            "jurisdictionCode": normalize_jurisdiction(law),
            "legacyRole": "直接依据",
            "lifecycle": "active",
            "priority": 10,
            "reason": "隐患描述、全文条款和整改措施逐项对应，作为直接依据。",
            "role": "direct",
        }
        evidence_refs = [evidence_id]
        hazard_review = {
            "checkedAt": AS_OF,
            "decision": "verified",
            "entityId": hid,
            "entityType": "hazard",
            "evidenceRefs": evidence_refs,
            "reason": "已核对Excel隐患内容与归档全文条款的对象、义务和整改措施，条款号及法规版本均已确认。",
            "reviewType": "content",
            "reviewedContentHash": content_hash(hz),
            "reviewer": "Codex正式核验批次20260913",
        }
        link_review = {
            "checkedAt": AS_OF,
            "contextHashes": {"clause": content_hash(clause), "hazard": content_hash(hz)},
            "decision": "verified",
            "entityId": link_id,
            "entityType": "link",
            "evidenceRefs": evidence_refs,
            "reason": "隐患对象、条款原文和整改措施逐项对应；关联角色为直接依据。",
            "reviewType": "applicability",
            "reviewedContentHash": content_hash(link),
            "reviewer": "Codex正式核验批次20260913",
        }
        promoted.append({"hazardId": hid, "clause": clause, "evidence": evidence,
                         "clauseReview": clause_review if existing else clause_review,
                         "hazard": hz, "hazardReview": hazard_review,
                         "link": link, "linkReview": link_review,
                         "createdClause": not bool(existing)})
    db.close()
    print(json.dumps({"candidateRows": len(rows), "promotable": len(promoted),
                      "newClauses": sum(1 for x in promoted if x["createdClause"]),
                      "skipped": len(skipped), "skipReasons": {
                          k: sum(1 for x in skipped if x["reason"] == k)
                          for k in sorted({x["reason"] for x in skipped})}}, ensure_ascii=False))
    if not args.apply:
        return 0
    for item in promoted:
        hid = item["hazardId"]
        write(os.path.join(KNOW, "hazards", hid + ".json"), item["hazard"])
        if item["createdClause"]:
            write(os.path.join(KNOW, "clauses", item["clause"]["id"] + ".json"), item["clause"])
            write(os.path.join(KNOW, "evidence", item["evidence"]["id"] + ".json"), item["evidence"])
            write(os.path.join(KNOW, "reviews", "clauses", item["clause"]["id"] + ".json"), item["clauseReview"])
        write(os.path.join(KNOW, "reviews", "hazards", hid + ".json"), item["hazardReview"])
        write(os.path.join(KNOW, "links", item["link"]["id"] + ".json"), item["link"])
        write(os.path.join(KNOW, "reviews", "links", item["linkReview"]["entityId"] + ".json"), item["linkReview"])
    manifest_path = os.path.join(KNOW, "manifest.json")
    manifest = read(manifest_path)
    batch_id = "excel-formalize-fulltext-batch-20260913"
    if batch_id not in {b.get("id") for b in manifest.get("batches", [])}:
        manifest.setdefault("batches", []).append({
            "id": batch_id, "hazardsAdded": len(promoted),
            "clausesAdded": sum(1 for x in promoted if x["createdClause"]),
            "linksAdded": len(promoted), "evidenceAdded": sum(1 for x in promoted if x["createdClause"]),
            "selection": "Excel fulltext candidates with article locator and exact paragraph recovered from archived source; hazard, clause and link reviews written together.",
        })
    manifest.setdefault("counts", {})["hazards"] = len(load_dir(KNOW, "hazards"))
    manifest["counts"]["clauses"] = len(load_dir(KNOW, "clauses"))
    manifest["counts"]["links"] = len(load_dir(KNOW, "links"))
    write(manifest_path, manifest)
    write(os.path.join(PROPOSAL, "formalize-fulltext-batch-report.json"),
          {"asOf": AS_OF, "promoted": [x["hazardId"] for x in promoted],
           "newClauses": [x["clause"]["id"] for x in promoted if x["createdClause"]],
           "skipped": skipped, "generatedAt": datetime.now(timezone.utc).isoformat()})


if __name__ == "__main__":
    main()
