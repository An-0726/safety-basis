# -*- coding: utf-8 -*-
"""Finalize PHASE 7 publication metadata/fulltext source hygiene.

`knowledge/` is the only identity authority.  This tool rewrites the public
source layer so every published law/version relationship resolves to a current
knowledge ID, keeps proposed hazards out of public metadata, preserves only
explicitly permitted official full text, and deterministically rebuilds the
full-text search index.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KNOW = ROOT / "knowledge"
PUB = ROOT / "source" / "publication"
FT = PUB / "fulltext"
AS_OF = date(2026, 9, 16)
REGION = {"CN": "全国", "CN-32": "江苏", "CN-3201": "南京"}
STATUS = {"active": "现行有效", "upcoming": "即将生效", "repealed": "已废止", "unknown": "待核验"}
ALLOWED_PERMISSION = {"official_legal_text", "metadata_only"}
PRIVATE_MARKERS = ("source/library", "fulltext.sqlite", ".sqlite3", "private-user-provided", "file://")


def rd(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def wr(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def load_dir(name: str):
    out = {}
    for path in sorted((KNOW / name).glob("*.json")):
        row = rd(path)
        out[row["id"]] = row
    return out


def norm(value) -> str:
    value = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", value)


def search_text(parts) -> str:
    value = " ".join(str(p) for p in parts if p)
    value = unicodedata.normalize("NFKC", value).lower()
    value = re.sub(r"[，。；：、（）()【】\[\]《》“”‘’'\"·•…—–_-]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def title_for(law, lv) -> str:
    name = law.get("canonicalName") or lv.get("officialName") or lv["id"]
    number = (lv.get("documentNumber") or "").strip()
    if number and norm(number) not in norm(name):
        return f"{name} {number}"
    return name


def canonical_match(doc, laws, versions):
    """Resolve an old publication row without title-only guessing.

    Priority: direct canonical ID, exact official source URL, then unique
    official-name + effective-date identity.  The last rule uses two
    independent fields and is intentionally rejected if non-unique.
    """
    vid = str(doc.get("versionId") or doc.get("id") or "")
    if vid in versions:
        return vid, "direct_id"

    url = str(doc.get("officialUrl") or doc.get("sourceUrl") or "").strip()
    if url:
        hits = [k for k, lv in versions.items() if str(lv.get("sourceUrl") or "").strip() == url]
        if len(hits) == 1:
            return hits[0], "exact_official_url"

    blob = norm(" ".join([str(doc.get("title") or doc.get("name") or ""), str(doc.get("version") or "")]))
    effective = str(doc.get("effectiveDate") or "").strip()
    hits = []
    for k, lv in versions.items():
        law = laws.get(lv.get("lawId"), {})
        official = norm(law.get("canonicalName") or lv.get("officialName") or "")
        if not official or official not in blob:
            continue
        if effective and str(lv.get("effectiveDate") or "").strip() != effective:
            continue
        hits.append(k)
    if len(hits) == 1:
        return hits[0], "official_name_effective_date"
    return None, "unresolved"


def normalize_text(value) -> str:
    return re.sub(r"[\u0009-\u000d\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]+", "", unicodedata.normalize("NFKC", str(value or "")).lower())


def bigrams(value):
    chars = list(normalize_text(value))
    return {chars[i] + chars[i + 1] for i in range(len(chars) - 1)}


def build_publication_index(laws, versions, clauses, hazards, links, existing):
    existing_by_id = {row.get("id"): row for row in existing if row.get("id")}
    clause_hazards = defaultdict(set)
    version_clauses = defaultdict(set)
    proposed = {hid for hid, h in hazards.items() if (h.get("lifecycle") or "active") == "proposed"}

    for link in links.values():
        if (link.get("lifecycle") or "active") != "active":
            continue
        hid, cid = link.get("hazardId"), link.get("clauseId")
        h = hazards.get(hid, {})
        c = clauses.get(cid, {})
        if (h.get("lifecycle") or "active") != "active" or (c.get("lifecycle") or "active") != "active":
            continue
        vid = c.get("lawVersionId")
        if vid not in versions:
            continue
        clause_hazards[cid].add(hid)
        version_clauses[vid].add(cid)

    out = []
    for vid in sorted(versions):
        lv = versions[vid]
        law = laws.get(lv.get("lawId"))
        if not law:
            raise SystemExit(f"law version missing law identity: {vid}")
        source = existing_by_id.get(vid, {})
        refs = []
        for cid in sorted(version_clauses.get(vid, set())):
            hids = sorted(clause_hazards[cid])
            if any(h in proposed for h in hids):
                raise SystemExit(f"proposed hazard leaked into publication metadata: {vid}/{cid}")
            refs.append({"clauseId": cid, "clauseShard": "", "hazardIds": hids})
        aliases = []
        for value in (law.get("aliases") or []) + (source.get("aliases") or []):
            if value and value not in aliases:
                aliases.append(value)
        title = title_for(law, lv)
        jurisdiction = law.get("jurisdictionCode") or lv.get("scope") or "CN"
        row = {
            "id": vid,
            "name": title,
            "aliases": aliases,
            "documentNumber": lv.get("documentNumber") or "",
            "level": law.get("documentKind") or lv.get("level") or source.get("level") or "",
            "scope": REGION.get(jurisdiction, source.get("scope") or jurisdiction),
            "status": STATUS.get(lv.get("validityStatus") or "unknown", "待核验"),
            "checked": AS_OF.isoformat(),
            "effectiveDate": lv.get("effectiveDate") or "",
            "sourceUrl": lv.get("sourceUrl") or "",
            "replaces": source.get("replaces") or [],
            "replacedBy": source.get("replacedBy") or [],
            "clauseRefs": refs,
            "hazardCount": len({h for ref in refs for h in ref["hazardIds"]}),
            "clauseCount": len(refs),
            "searchText": search_text([vid, title, " ".join(aliases), law.get("issuer"), lv.get("documentNumber"), jurisdiction]),
        }
        out.append(row)
    return out


def choose_fulltext(rows):
    rank = {"full_text": 2, "link_only": 1}
    rows = sorted(rows, key=lambda d: (rank.get(d.get("textMode"), 0), bool(d.get("fullTextReviewed"))), reverse=True)
    full = [d for d in rows if d.get("textMode") == "full_text"]
    if len(full) > 1:
        hashes = {d.get("fullTextSha256") for d in full if d.get("fullTextSha256")}
        if len(hashes) > 1:
            raise SystemExit("conflicting official full texts for one canonical version: " + str([d.get("versionId") for d in rows]))
    return rows[0]


def canonicalize_fulltext(laws, versions, catalog):
    mapped = defaultdict(list)
    resolutions, dropped = [], []
    for doc in catalog.get("documents", []):
        vid, reason = canonical_match(doc, laws, versions)
        if not vid:
            dropped.append({"oldVersionId": doc.get("versionId"), "title": doc.get("title"), "reason": reason})
            continue
        copy = dict(doc)
        copy["_oldVersionId"] = doc.get("versionId")
        copy["_reason"] = reason
        mapped[vid].append(copy)

    docs = []
    referenced_texts = set()
    id_map = {}
    for vid in sorted(mapped):
        lv = versions[vid]
        law = laws[lv["lawId"]]
        chosen = choose_fulltext(mapped[vid])
        old_ids = sorted({str(d.get("_oldVersionId") or "") for d in mapped[vid] if d.get("_oldVersionId")})
        for old in old_ids:
            id_map[old] = vid
        mode = chosen.get("textMode")
        permission = chosen.get("publicationPermission")
        if mode not in {"full_text", "link_only"}:
            raise SystemExit(f"unsupported textMode: {vid} {mode}")
        if permission not in ALLOWED_PERMISSION:
            raise SystemExit(f"unsupported publication permission: {vid} {permission}")

        out = {k: v for k, v in chosen.items() if not k.startswith("_")}
        out["lawId"] = lv["lawId"]
        out["versionId"] = vid
        out["title"] = title_for(law, lv)
        out["version"] = lv.get("versionKey") or lv.get("documentNumber") or vid
        out["officialUrl"] = lv.get("sourceUrl") or out.get("officialUrl") or ""
        out["effectiveDate"] = lv.get("effectiveDate") or ""
        out["status"] = STATUS.get(lv.get("validityStatus") or "unknown", "待核验")

        if mode == "full_text":
            if permission != "official_legal_text" or not bool(out.get("fullTextReviewed")):
                raise SystemExit(f"full text lacks explicit official publication permission/review: {vid}")
            old_path = chosen.get("textPath")
            if not old_path or not str(old_path).startswith("texts/"):
                raise SystemExit(f"invalid full text path: {vid}")
            source = FT / old_path
            if not source.exists():
                raise SystemExit(f"full text file missing: {old_path}")
            payload = rd(source)
            payload["lawId"] = lv["lawId"]
            payload["versionId"] = vid
            payload["title"] = law.get("canonicalName") or lv.get("officialName") or out["title"]
            payload["version"] = out["version"]
            new_rel = f"texts/{vid}.json"
            wr(FT / new_rel, payload)
            out["textPath"] = new_rel
            referenced_texts.add(new_rel)
            if not re.fullmatch(r"[0-9a-fA-F]{64}", str(out.get("fullTextSha256") or "")):
                raise SystemExit(f"invalid fullTextSha256: {vid}")
        else:
            out["publicationPermission"] = "metadata_only"
            out["fullTextReviewed"] = False
            out["fullTextSha256"] = ""
            out["textPath"] = None

        docs.append(out)
        resolutions.append({"canonicalVersionId": vid, "oldVersionIds": old_ids, "resolution": chosen.get("_reason"), "textMode": mode})

    # Generated publication texts are replaceable derivatives.  Remove stale/orphan text files.
    text_dir = FT / "texts"
    if text_dir.exists():
        for path in text_dir.glob("*.json"):
            rel = f"texts/{path.name}"
            if rel not in referenced_texts:
                path.unlink()

    return docs, resolutions, dropped, id_map


def rebuild_search(docs):
    index_docs = []
    postings = defaultdict(set)
    for doc in docs:
        index_docs.append({
            "lawId": doc["lawId"], "versionId": doc["versionId"], "title": doc["title"],
            "version": doc.get("version") or "", "textMode": doc["textMode"], "textPath": doc.get("textPath"),
        })
        if doc["textMode"] != "full_text":
            continue
        payload = rd(FT / doc["textPath"])
        corpus = [doc["title"]] + [row.get("text", "") for row in payload.get("paragraphs", [])]
        grams = set()
        for part in corpus:
            grams.update(bigrams(part))
        for gram in grams:
            postings[gram].add(doc["versionId"])

    gram_dir = FT / "grams"
    if gram_dir.exists():
        shutil.rmtree(gram_dir)
    gram_dir.mkdir(parents=True, exist_ok=True)
    shards = defaultdict(dict)
    for gram, ids in sorted(postings.items()):
        prefix = hashlib.sha256(gram.encode("utf-8")).hexdigest()[:2]
        shards[prefix][gram] = sorted(ids)
    gram_shards = {}
    for prefix in sorted(shards):
        rel = f"grams/{prefix}.json"
        wr(FT / rel, {"schemaVersion": "safety-public-fulltext-grams-v1", "grams": shards[prefix]})
        gram_shards[prefix] = rel
    return {
        "schemaVersion": "safety-public-fulltext-search-v1",
        "asOf": AS_OF.isoformat(),
        "documents": index_docs,
        "gramShards": gram_shards,
    }


def audit(laws, versions, hazards, pub_index, catalog, search_index, resolutions, dropped, before):
    errors = []
    version_ids = set(versions)
    index_ids = [row.get("id") for row in pub_index]
    if len(index_ids) != len(set(index_ids)):
        errors.append("duplicate publication law-index IDs")
    if set(index_ids) != version_ids:
        errors.append("publication law-index is not a 1:1 projection of knowledge law versions")
    proposed = {hid for hid, h in hazards.items() if (h.get("lifecycle") or "active") == "proposed"}
    leaked = sorted({hid for row in pub_index for ref in row.get("clauseRefs", []) for hid in ref.get("hazardIds", []) if hid in proposed})
    if leaked:
        errors.append("proposed hazards leaked: " + ",".join(leaked[:10]))

    docs = catalog.get("documents", [])
    if len({d.get("versionId") for d in docs}) != len(docs):
        errors.append("duplicate canonical fulltext catalog versionId")
    for d in docs:
        vid = d.get("versionId")
        if vid not in versions or d.get("lawId") != versions[vid].get("lawId"):
            errors.append(f"noncanonical fulltext identity: {vid}")
        if not re.match(r"^https?://", str(d.get("officialUrl") or "")):
            errors.append(f"non-http official URL: {vid}")
        if d.get("textMode") == "full_text":
            if d.get("publicationPermission") != "official_legal_text" or not d.get("fullTextReviewed"):
                errors.append(f"unapproved full text: {vid}")
            if not d.get("textPath") or not (FT / d["textPath"]).exists():
                errors.append(f"missing full text: {vid}")
        elif d.get("textMode") == "link_only":
            if d.get("publicationPermission") != "metadata_only" or d.get("textPath") is not None:
                errors.append(f"metadata-only boundary violation: {vid}")
        else:
            errors.append(f"unknown text mode: {vid}")

    search_ids = [d.get("versionId") for d in search_index.get("documents", [])]
    if search_ids != [d.get("versionId") for d in docs]:
        errors.append("search-index/catalog order or identity mismatch")

    meta_blob = json.dumps([pub_index, catalog, search_index], ensure_ascii=False).lower()
    private_hits = [m for m in PRIVATE_MARKERS if m.lower() in meta_blob]
    if private_hits:
        errors.append("private boundary markers present: " + ",".join(private_hits))

    manifest = rd(KNOW / "manifest.json")
    lifecycle = defaultdict(int)
    for h in hazards.values():
        lifecycle[h.get("lifecycle") or "active"] += 1
    counts = manifest.get("counts") or {}
    report = {
        "phaseStatus": "DONE" if not errors else "FAILED",
        "asOf": AS_OF.isoformat(),
        "knowledge": {
            "laws": len(laws), "lawVersions": len(versions), "hazards": len(hazards),
            "manifestCounts": counts, "hazardLifecycle": dict(sorted(lifecycle.items())),
        },
        "publication": {
            "lawIndexBefore": before["lawIndex"], "lawIndexAfter": len(pub_index),
            "staleLawIndexIdsRemoved": before["staleLawIndexIds"],
            "fulltextCatalogBefore": before["fulltextCatalog"], "fulltextCatalogAfter": len(docs),
            "fullTextAfter": sum(d.get("textMode") == "full_text" for d in docs),
            "linkOnlyAfter": sum(d.get("textMode") == "link_only" for d in docs),
            "canonicalResolutions": resolutions,
            "droppedUngovernedFulltextRows": dropped,
            "proposedHazardLeakCount": len(leaked),
            "privateBoundaryMarkers": private_hits,
            "searchGramShardCount": len(search_index.get("gramShards") or {}),
        },
        "constraints": {
            "knowledgeModified": False, "privateSqliteModified": False, "stableIdsModified": False,
            "releaseOrPagesPerformed": False,
        },
        "errors": errors,
    }
    return report


def markdown(report):
    p = report["publication"]
    k = report["knowledge"]
    lines = [
        "# PHASE 7 Publication Source Hygiene — Final Audit", "",
        f"- Status: **{report['phaseStatus']}**", f"- As of: **{report['asOf']}**",
        f"- Knowledge authority: **{k['laws']} laws / {k['lawVersions']} law versions**", "",
        "## Result", "",
        f"- `source/publication/law-index.json`: {p['lawIndexBefore']} → **{p['lawIndexAfter']}** canonical version rows.",
        f"- Fulltext catalog: {p['fulltextCatalogBefore']} → **{p['fulltextCatalogAfter']}** canonical rows; **{p['fullTextAfter']}** approved official full texts and **{p['linkOnlyAfter']}** metadata-only official links.",
        f"- Proposed-hazard leakage: **{p['proposedHazardLeakCount']}**.",
        f"- Private-boundary marker leakage: **{len(p['privateBoundaryMarkers'])}**.",
        f"- Fulltext search gram shards rebuilt: **{p['searchGramShardCount']}**.", "",
        "## Canonicalization", "",
        "Publication identity is now a 1:1 projection of `knowledge/law-versions`; publication no longer creates independent law/version identities. Existing full text is retained only when its catalog row has explicit `official_legal_text` permission and `fullTextReviewed=true`; all other public entries are metadata-only official links.", "",
        f"- Stale law-index IDs removed: **{len(p['staleLawIndexIdsRemoved'])}**.",
        f"- Fulltext rows with no governed knowledge identity removed from the public catalog: **{len(p['droppedUngovernedFulltextRows'])}**.", "",
        "## Boundaries", "",
        "- `knowledge/` was not modified by the finalizer.",
        "- No private SQLite/PDF/OCR/archive material is introduced into `source/publication/`.",
        "- No stable knowledge IDs are renumbered.",
        "- No release bundle, PR merge, Pages deployment, or public deployment is performed by PHASE 7.", "",
    ]
    if report["errors"]:
        lines += ["## Errors", ""] + [f"- {e}" for e in report["errors"]] + [""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    laws = load_dir("laws")
    versions = load_dir("law-versions")
    clauses = load_dir("clauses")
    hazards = load_dir("hazards")
    links = load_dir("links")
    old_index = rd(PUB / "law-index.json")
    old_catalog = rd(FT / "catalog.json")
    before = {
        "lawIndex": len(old_index),
        "staleLawIndexIds": sorted(row.get("id") for row in old_index if row.get("id") not in versions),
        "fulltextCatalog": len(old_catalog.get("documents", [])),
    }

    if not args.apply:
        print(json.dumps(before, ensure_ascii=False, indent=2))
        return

    pub_index = build_publication_index(laws, versions, clauses, hazards, links, old_index)
    docs, resolutions, dropped, _id_map = canonicalize_fulltext(laws, versions, old_catalog)
    catalog = {"schemaVersion": "safety-public-fulltext-v1", "asOf": AS_OF.isoformat(), "documents": docs}
    search_index = rebuild_search(docs)
    report = audit(laws, versions, hazards, pub_index, catalog, search_index, resolutions, dropped, before)
    if report["errors"]:
        raise SystemExit(json.dumps(report, ensure_ascii=False, indent=2))

    wr(PUB / "law-index.json", pub_index)
    wr(FT / "catalog.json", catalog)
    wr(FT / "search-index.json", search_index)
    wr(ROOT / "docs" / "phase7-publication-audit.json", report)
    (ROOT / "docs" / "PHASE7_PUBLICATION_AUDIT.md").write_text(markdown(report), encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
