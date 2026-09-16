#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audit the publication/source layer against canonical V4 law identities.

This command is intentionally conservative:
- knowledge/laws and knowledge/law-versions are canonical;
- source/publication is a source/publication layer, never a second identity source;
- only exact canonical IDs and exact official/source URLs are used for mapping diagnostics;
- title/alias similarity is never used to infer identity.

The command is read-only and exits zero unless the input structure itself is invalid.
Use the JSON output when a machine-readable Phase 7 remediation backlog is needed.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LAWS_DIR = ROOT / "knowledge" / "laws"
VERSIONS_DIR = ROOT / "knowledge" / "law-versions"
PUBLICATION_INDEX = ROOT / "source" / "publication" / "law-index.json"
FULLTEXT_ROOT = ROOT / "source" / "publication" / "fulltext"
FULLTEXT_CATALOG = FULLTEXT_ROOT / "catalog.json"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_entities(directory: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        obj = load_json(path)
        if not isinstance(obj, dict):
            raise ValueError(f"{path.relative_to(ROOT)} must contain a JSON object")
        if not isinstance(obj.get("id"), str) or not obj["id"].strip():
            raise ValueError(f"{path.relative_to(ROOT)} has no non-empty id")
        row = dict(obj)
        row["__path"] = str(path.relative_to(ROOT))
        rows.append(row)
    return rows


def require_unique_ids(rows: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    dupes: list[str] = []
    for row in rows:
        rid = row["id"]
        if rid in by_id:
            dupes.append(rid)
        else:
            by_id[rid] = row
    if dupes:
        raise ValueError(f"duplicate {label} ids: {sorted(set(dupes))}")
    return by_id


def exact_url(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def index_versions_by_url(versions: list[dict[str, Any]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    for row in versions:
        url = exact_url(row.get("sourceUrl"))
        if url:
            out[url].append(row["id"])
    return dict(out)


def publication_audit(
    laws: list[dict[str, Any]],
    versions: list[dict[str, Any]],
    publication: list[dict[str, Any]],
    fulltext_docs: list[dict[str, Any]],
) -> dict[str, Any]:
    law_by_id = require_unique_ids(laws, "law")
    version_by_id = require_unique_ids(versions, "law-version")

    publication_ids = [row.get("id") for row in publication]
    if any(not isinstance(v, str) or not v.strip() for v in publication_ids):
        raise ValueError("source/publication/law-index.json contains a row without a non-empty id")
    publication_id_counts = Counter(publication_ids)
    publication_duplicate_ids = sorted(k for k, n in publication_id_counts.items() if n > 1)

    version_urls = index_versions_by_url(versions)
    canonical_version_ids = set(version_by_id)

    publication_exact_id: list[dict[str, str]] = []
    publication_url_fallback: list[dict[str, Any]] = []
    publication_unmapped: list[dict[str, Any]] = []
    pub_by_canonical_version: dict[str, list[str]] = defaultdict(list)

    for row in publication:
        rid = row["id"]
        url = exact_url(row.get("sourceUrl"))
        if rid in version_by_id:
            publication_exact_id.append({"publicationId": rid, "versionId": rid})
            pub_by_canonical_version[rid].append(rid)
            continue
        url_matches = version_urls.get(url, []) if url else []
        if len(url_matches) == 1:
            vid = url_matches[0]
            publication_url_fallback.append(
                {"publicationId": rid, "versionId": vid, "sourceUrl": url}
            )
            pub_by_canonical_version[vid].append(rid)
        else:
            publication_unmapped.append(
                {
                    "publicationId": rid,
                    "name": row.get("name", ""),
                    "sourceUrl": url,
                    "urlMatchCount": len(url_matches),
                    "urlMatches": sorted(url_matches),
                }
            )

    publication_multi_source_versions = [
        {"versionId": vid, "publicationIds": sorted(ids)}
        for vid, ids in sorted(pub_by_canonical_version.items())
        if len(ids) > 1
    ]
    canonical_versions_without_publication_mapping = sorted(
        canonical_version_ids - set(pub_by_canonical_version)
    )

    fulltext_exact: list[dict[str, Any]] = []
    fulltext_url_fallback: list[dict[str, Any]] = []
    fulltext_unmapped: list[dict[str, Any]] = []
    fulltext_law_mismatch: list[dict[str, Any]] = []
    fulltext_missing_text_files: list[dict[str, Any]] = []
    fulltext_paths: list[str] = []

    for i, row in enumerate(fulltext_docs):
        version_id = row.get("versionId")
        law_id = row.get("lawId")
        official_url = exact_url(row.get("officialUrl") or row.get("sourceUrl"))
        resolved_version_id: str | None = None
        resolution = ""

        if isinstance(version_id, str) and version_id in version_by_id:
            resolved_version_id = version_id
            resolution = "exact_version_id"
        else:
            url_matches = version_urls.get(official_url, []) if official_url else []
            if len(url_matches) == 1:
                resolved_version_id = url_matches[0]
                resolution = "exact_source_url"
            else:
                fulltext_unmapped.append(
                    {
                        "row": i,
                        "versionId": version_id,
                        "lawId": law_id,
                        "title": row.get("title", ""),
                        "officialUrl": official_url,
                        "urlMatchCount": len(url_matches),
                        "urlMatches": sorted(url_matches),
                    }
                )

        if resolved_version_id:
            canonical = version_by_id[resolved_version_id]
            item = {
                "row": i,
                "versionId": version_id,
                "resolvedVersionId": resolved_version_id,
                "lawId": law_id,
                "resolution": resolution,
            }
            if resolution == "exact_version_id":
                fulltext_exact.append(item)
            else:
                fulltext_url_fallback.append(item)
            expected_law_id = canonical.get("lawId")
            if law_id != expected_law_id:
                fulltext_law_mismatch.append(
                    {
                        **item,
                        "expectedLawId": expected_law_id,
                        "lawIdExists": law_id in law_by_id if isinstance(law_id, str) else False,
                    }
                )

        text_path = row.get("textPath")
        text_mode = row.get("textMode")
        if isinstance(text_path, str) and text_path.strip():
            fulltext_paths.append(text_path)
            candidate = FULLTEXT_ROOT / text_path
            if not candidate.is_file():
                fulltext_missing_text_files.append(
                    {"row": i, "versionId": version_id, "textPath": text_path}
                )
        elif text_mode == "full_text":
            fulltext_missing_text_files.append(
                {"row": i, "versionId": version_id, "textPath": text_path}
            )

    fulltext_duplicate_paths = sorted(
        path for path, n in Counter(fulltext_paths).items() if n > 1
    )

    orphan_versions = sorted(
        row["id"] for row in versions if row.get("lawId") not in law_by_id
    )

    text_modes = Counter(str(row.get("textMode", "")) for row in fulltext_docs)
    permissions = Counter(str(row.get("publicationPermission", "")) for row in fulltext_docs)

    return {
        "schemaVersion": "safety-publication-audit-v1",
        "counts": {
            "canonicalLaws": len(laws),
            "canonicalVersions": len(versions),
            "publicationRows": len(publication),
            "publicationExactIdMappings": len(publication_exact_id),
            "publicationUniqueUrlMappings": len(publication_url_fallback),
            "publicationUnmappedRows": len(publication_unmapped),
            "canonicalVersionsWithoutPublicationMapping": len(canonical_versions_without_publication_mapping),
            "fulltextCatalogRows": len(fulltext_docs),
            "fulltextExactVersionIdMappings": len(fulltext_exact),
            "fulltextUniqueUrlMappings": len(fulltext_url_fallback),
            "fulltextUnmappedRows": len(fulltext_unmapped),
            "fulltextLawMismatches": len(fulltext_law_mismatch),
            "fulltextMissingTextFiles": len(fulltext_missing_text_files),
        },
        "textModes": dict(sorted(text_modes.items())),
        "publicationPermissions": dict(sorted(permissions.items())),
        "publicationDuplicateIds": publication_duplicate_ids,
        "publicationExactIdMappings": publication_exact_id,
        "publicationUniqueUrlMappings": publication_url_fallback,
        "publicationUnmapped": publication_unmapped,
        "publicationMultiSourceVersions": publication_multi_source_versions,
        "canonicalVersionsWithoutPublicationMapping": canonical_versions_without_publication_mapping,
        "fulltextExactVersionIdMappings": fulltext_exact,
        "fulltextUniqueUrlMappings": fulltext_url_fallback,
        "fulltextUnmapped": fulltext_unmapped,
        "fulltextLawMismatches": fulltext_law_mismatch,
        "fulltextMissingTextFiles": fulltext_missing_text_files,
        "fulltextDuplicateTextPaths": fulltext_duplicate_paths,
        "canonicalVersionsWithMissingLawId": orphan_versions,
    }


def print_summary(report: dict[str, Any]) -> None:
    c = report["counts"]
    print("Publication audit (exact IDs / exact URLs only)")
    print(f"canonical laws: {c['canonicalLaws']}")
    print(f"canonical versions: {c['canonicalVersions']}")
    print(
        "publication rows: "
        f"{c['publicationRows']} = {c['publicationExactIdMappings']} exact-id + "
        f"{c['publicationUniqueUrlMappings']} unique-url + {c['publicationUnmappedRows']} unmapped"
    )
    print(
        "canonical versions without publication mapping: "
        f"{c['canonicalVersionsWithoutPublicationMapping']}"
    )
    print(
        "fulltext catalog rows: "
        f"{c['fulltextCatalogRows']} = {c['fulltextExactVersionIdMappings']} exact-id + "
        f"{c['fulltextUniqueUrlMappings']} unique-url + {c['fulltextUnmappedRows']} unmapped"
    )
    print(f"fulltext text modes: {json.dumps(report['textModes'], ensure_ascii=False, sort_keys=True)}")
    print(
        "publication permissions: "
        f"{json.dumps(report['publicationPermissions'], ensure_ascii=False, sort_keys=True)}"
    )
    print(f"fulltext law mismatches: {c['fulltextLawMismatches']}")
    print(f"fulltext missing text files: {c['fulltextMissingTextFiles']}")
    print(f"publication duplicate ids: {len(report['publicationDuplicateIds'])}")
    print(f"publication multi-source canonical versions: {len(report['publicationMultiSourceVersions'])}")
    print(f"canonical versions with missing lawId target: {len(report['canonicalVersionsWithMissingLawId'])}")

    for label, key in (
        ("publication unique-url remap candidates", "publicationUniqueUrlMappings"),
        ("publication unmapped rows", "publicationUnmapped"),
        ("fulltext unique-url remap candidates", "fulltextUniqueUrlMappings"),
        ("fulltext unmapped rows", "fulltextUnmapped"),
        ("fulltext law mismatches", "fulltextLawMismatches"),
    ):
        rows = report[key]
        if rows:
            print(f"\n{label} ({len(rows)}):")
            for row in rows:
                print(json.dumps(row, ensure_ascii=False, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, help="optional path for the complete audit JSON")
    args = parser.parse_args()

    laws = load_entities(LAWS_DIR)
    versions = load_entities(VERSIONS_DIR)
    publication = load_json(PUBLICATION_INDEX)
    if not isinstance(publication, list) or not all(isinstance(x, dict) for x in publication):
        raise ValueError("source/publication/law-index.json must be an array of objects")
    catalog = load_json(FULLTEXT_CATALOG)
    if not isinstance(catalog, dict) or not isinstance(catalog.get("documents"), list):
        raise ValueError("source/publication/fulltext/catalog.json must contain documents[]")
    fulltext_docs = catalog["documents"]
    if not all(isinstance(x, dict) for x in fulltext_docs):
        raise ValueError("source/publication/fulltext/catalog.json documents must be objects")

    report = publication_audit(laws, versions, publication, fulltext_docs)
    print_summary(report)
    if args.json_out:
        out = args.json_out
        if not out.is_absolute():
            out = ROOT / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote: {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
