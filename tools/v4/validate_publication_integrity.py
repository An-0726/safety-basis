# -*- coding: utf-8 -*-
"""Hard, read-only integrity gate for the public source/full-text layer.

PHASE 7 canonicalized ``source/publication`` against ``knowledge`` and rebuilt
its full-text search derivatives.  This validator keeps those invariants alive
in normal CI so a later maintenance edit cannot silently re-introduce stale
publication identities, orphan public text files, or stale search shards.

The command never mutates repository data.  Any error returns a non-zero exit
code and must block both validation and Pages deployment.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KNOW = ROOT / "knowledge"
PUB = ROOT / "source" / "publication"
FT = PUB / "fulltext"
CATALOG_SCHEMA = "safety-public-fulltext-v1"
SEARCH_SCHEMA = "safety-public-fulltext-search-v1"
TEXT_SCHEMA = "safety-public-fulltext-text-v1"
GRAM_SCHEMA = "safety-public-fulltext-grams-v1"
STATUS = {
    "active": "现行有效",
    "upcoming": "即将生效",
    "repealed": "已废止",
    "unknown": "待核验",
}
PRIVATE_MARKERS = (
    "source/library",
    "fulltext.sqlite",
    ".sqlite3",
    "private-user-provided",
    "file://",
)
HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
HTTP = re.compile(r"^https?://")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_entities(name: str) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for path in sorted((KNOW / name).glob("*.json")):
        row = read_json(path)
        entity_id = row.get("id")
        if not isinstance(entity_id, str) or not entity_id:
            raise ValueError(f"{path.relative_to(ROOT)} has no non-empty id")
        if entity_id in rows:
            raise ValueError(f"duplicate {name} id: {entity_id}")
        rows[entity_id] = row
    return rows


def normalize_text(value) -> str:
    return re.sub(
        r"[\u0009-\u000d\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]+",
        "",
        unicodedata.normalize("NFKC", str(value or "")).lower(),
    )


def bigrams(value) -> set[str]:
    chars = list(normalize_text(value))
    return {chars[i] + chars[i + 1] for i in range(len(chars) - 1)}


def expected_search(docs: list[dict], errors: list[str]):
    index_docs = []
    postings: dict[str, set[str]] = defaultdict(set)
    for doc in docs:
        vid = doc.get("versionId")
        index_docs.append({
            "lawId": doc.get("lawId"),
            "versionId": vid,
            "title": doc.get("title"),
            "version": doc.get("version") or "",
            "textMode": doc.get("textMode"),
            "textPath": doc.get("textPath"),
        })
        if doc.get("textMode") != "full_text":
            continue
        text_path = doc.get("textPath")
        if not isinstance(text_path, str) or not text_path:
            continue
        path = FT / text_path
        if not path.is_file():
            continue
        try:
            payload = read_json(path)
        except Exception as exc:  # pragma: no cover - surfaced in real data CI
            errors.append(f"invalid full-text JSON {text_path}: {exc}")
            continue
        if payload.get("schemaVersion") != TEXT_SCHEMA:
            errors.append(f"full-text payload schema mismatch: {vid}")
        if payload.get("versionId") != vid or payload.get("lawId") != doc.get("lawId"):
            errors.append(f"full-text payload identity mismatch: {vid}")
        paragraphs = payload.get("paragraphs")
        if not isinstance(paragraphs, list):
            errors.append(f"full-text paragraphs is not an array: {vid}")
            continue
        grams = set()
        for part in [doc.get("title") or ""] + [
            row.get("text", "") for row in paragraphs if isinstance(row, dict)
        ]:
            grams.update(bigrams(part))
        for gram in grams:
            postings[gram].add(str(vid))

    shards: dict[str, dict[str, list[str]]] = defaultdict(dict)
    for gram, ids in sorted(postings.items()):
        prefix = hashlib.sha256(gram.encode("utf-8")).hexdigest()[:2]
        shards[prefix][gram] = sorted(ids)
    gram_shards = {prefix: f"grams/{prefix}.json" for prefix in sorted(shards)}
    return index_docs, dict(shards), gram_shards


def main() -> int:
    errors: list[str] = []
    try:
        laws = load_entities("laws")
        versions = load_entities("law-versions")
        clauses = load_entities("clauses")
        hazards = load_entities("hazards")
        pub_index = read_json(PUB / "law-index.json")
        catalog = read_json(FT / "catalog.json")
        search_index = read_json(FT / "search-index.json")
    except Exception as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1

    if not isinstance(pub_index, list) or not all(isinstance(x, dict) for x in pub_index):
        errors.append("source/publication/law-index.json must be an array of objects")
        pub_index = []
    pub_ids = [row.get("id") for row in pub_index]
    if any(not isinstance(x, str) or not x for x in pub_ids):
        errors.append("publication law-index contains an empty/non-string id")
    if len(pub_ids) != len(set(pub_ids)):
        errors.append("duplicate publication law-index IDs")
    if set(x for x in pub_ids if isinstance(x, str)) != set(versions):
        missing = sorted(set(versions) - set(pub_ids))
        stale = sorted(set(pub_ids) - set(versions))
        errors.append(
            "publication law-index is not a 1:1 projection of knowledge law versions"
            f"; missing={missing[:10]}; stale={stale[:10]}"
        )

    proposed = {
        hid for hid, row in hazards.items()
        if (row.get("lifecycle") or "active") == "proposed"
    }
    for row in pub_index:
        vid = row.get("id")
        lv = versions.get(vid)
        if not lv:
            continue
        if row.get("documentNumber", "") != (lv.get("documentNumber") or ""):
            errors.append(f"publication documentNumber drift: {vid}")
        if row.get("effectiveDate", "") != (lv.get("effectiveDate") or ""):
            errors.append(f"publication effectiveDate drift: {vid}")
        if row.get("sourceUrl", "") != (lv.get("sourceUrl") or ""):
            errors.append(f"publication sourceUrl drift: {vid}")
        expected_status = STATUS.get(lv.get("validityStatus") or "unknown", "待核验")
        if row.get("status") != expected_status:
            errors.append(f"publication status drift: {vid}")
        refs = row.get("clauseRefs") or []
        if row.get("clauseCount") != len(refs):
            errors.append(f"publication clauseCount mismatch: {vid}")
        ref_hazards = set()
        for ref in refs:
            cid = ref.get("clauseId") if isinstance(ref, dict) else None
            clause = clauses.get(cid)
            if not clause or clause.get("lawVersionId") != vid:
                errors.append(f"publication clauseRef identity mismatch: {vid}/{cid}")
            for hid in (ref.get("hazardIds") or []) if isinstance(ref, dict) else []:
                ref_hazards.add(hid)
                if hid not in hazards:
                    errors.append(f"publication clauseRef unknown hazard: {vid}/{hid}")
                elif hid in proposed:
                    errors.append(f"proposed hazard leaked into publication metadata: {vid}/{hid}")
        if row.get("hazardCount") != len(ref_hazards):
            errors.append(f"publication hazardCount mismatch: {vid}")

    if not isinstance(catalog, dict):
        errors.append("fulltext catalog must be an object")
        catalog = {}
    if catalog.get("schemaVersion") != CATALOG_SCHEMA:
        errors.append("fulltext catalog schemaVersion mismatch")
    if not isinstance(catalog.get("documents"), list):
        errors.append("fulltext catalog must contain documents[]")
        docs = []
    else:
        docs = catalog["documents"]
    if not all(isinstance(x, dict) for x in docs):
        errors.append("fulltext catalog documents must be objects")
        docs = [x for x in docs if isinstance(x, dict)]

    doc_ids = [d.get("versionId") for d in docs]
    if any(not isinstance(x, str) or not x for x in doc_ids):
        errors.append("fulltext catalog contains an empty/non-string versionId")
    if len(doc_ids) != len(set(doc_ids)):
        errors.append("duplicate canonical fulltext catalog versionId")

    referenced_texts: set[str] = set()
    full_text_ids: set[str] = set()
    pub_id_set = set(x for x in pub_ids if isinstance(x, str))
    for doc in docs:
        vid = doc.get("versionId")
        lv = versions.get(vid)
        if not lv or vid not in pub_id_set:
            errors.append(f"fulltext catalog version is not canonical publication identity: {vid}")
            continue
        if doc.get("lawId") != lv.get("lawId") or doc.get("lawId") not in laws:
            errors.append(f"fulltext catalog lawId mismatch: {vid}")
        if not HTTP.match(str(doc.get("officialUrl") or "")):
            errors.append(f"fulltext catalog has non-http officialUrl: {vid}")
        if doc.get("effectiveDate", "") != (lv.get("effectiveDate") or ""):
            errors.append(f"fulltext catalog effectiveDate drift: {vid}")

        mode = doc.get("textMode")
        if mode == "full_text":
            full_text_ids.add(str(vid))
            if doc.get("publicationPermission") != "official_legal_text" or doc.get("fullTextReviewed") is not True:
                errors.append(f"unapproved full text: {vid}")
            if not HEX64.fullmatch(str(doc.get("fullTextSha256") or "")):
                errors.append(f"invalid fullTextSha256: {vid}")
            text_path = doc.get("textPath")
            if not isinstance(text_path, str) or not text_path.startswith("texts/") or Path(text_path).is_absolute() or ".." in Path(text_path).parts:
                errors.append(f"invalid full text path: {vid}")
            else:
                referenced_texts.add(text_path)
                if not (FT / text_path).is_file():
                    errors.append(f"missing full text file: {vid}/{text_path}")
        elif mode == "link_only":
            if doc.get("publicationPermission") != "metadata_only":
                errors.append(f"link-only publicationPermission mismatch: {vid}")
            if doc.get("fullTextReviewed") is not False:
                errors.append(f"link-only fullTextReviewed must be false: {vid}")
            if doc.get("textPath") is not None:
                errors.append(f"link-only entry unexpectedly has textPath: {vid}")
            if str(doc.get("fullTextSha256") or ""):
                errors.append(f"link-only entry unexpectedly has fullTextSha256: {vid}")
        else:
            errors.append(f"unknown fulltext textMode: {vid}={mode}")

    actual_texts = {
        f"texts/{path.name}" for path in (FT / "texts").glob("*.json")
    } if (FT / "texts").is_dir() else set()
    if actual_texts != referenced_texts:
        errors.append(
            "catalog/fulltext file set mismatch"
            f"; unreferenced={sorted(actual_texts - referenced_texts)[:10]}"
            f"; missing={sorted(referenced_texts - actual_texts)[:10]}"
        )

    expected_docs, expected_shards, expected_shard_map = expected_search(docs, errors)
    if not isinstance(search_index, dict):
        errors.append("fulltext search-index must be an object")
        search_index = {}
    if search_index.get("schemaVersion") != SEARCH_SCHEMA:
        errors.append("fulltext search-index schemaVersion mismatch")
    if search_index.get("asOf") != catalog.get("asOf"):
        errors.append("fulltext search-index/catalog asOf mismatch")
    if search_index.get("documents") != expected_docs:
        errors.append("fulltext search-index documents are stale or differ from catalog")
    if search_index.get("gramShards") != expected_shard_map:
        errors.append("fulltext search-index gramShards map is stale")

    gram_dir = FT / "grams"
    actual_gram_files = {
        f"grams/{path.name}" for path in gram_dir.glob("*.json")
    } if gram_dir.is_dir() else set()
    expected_gram_files = set(expected_shard_map.values())
    if actual_gram_files != expected_gram_files:
        errors.append(
            "fulltext gram file set mismatch"
            f"; unreferenced={sorted(actual_gram_files - expected_gram_files)[:10]}"
            f"; missing={sorted(expected_gram_files - actual_gram_files)[:10]}"
        )
    for prefix, grams in expected_shards.items():
        path = FT / f"grams/{prefix}.json"
        if not path.is_file():
            continue
        try:
            payload = read_json(path)
        except Exception as exc:
            errors.append(f"invalid gram shard {prefix}: {exc}")
            continue
        expected_payload = {
            "schemaVersion": GRAM_SCHEMA,
            "grams": grams,
        }
        if payload != expected_payload:
            errors.append(f"fulltext gram shard is stale: {prefix}")

    meta_blob = json.dumps([pub_index, catalog, search_index], ensure_ascii=False).lower()
    private_hits = [marker for marker in PRIVATE_MARKERS if marker.lower() in meta_blob]
    if private_hits:
        errors.append("private boundary markers present: " + ",".join(private_hits))

    summary = {
        "ok": not errors,
        "counts": {
            "knowledgeLaws": len(laws),
            "knowledgeLawVersions": len(versions),
            "publicationRows": len(pub_index),
            "catalogDocuments": len(docs),
            "catalogFullText": len(full_text_ids),
            "physicalTextFiles": len(actual_texts),
            "gramShards": len(actual_gram_files),
            "proposedHazards": len(proposed),
        },
        "errors": errors,
    }
    print("=== PUBLICATION_INTEGRITY_GATE ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
