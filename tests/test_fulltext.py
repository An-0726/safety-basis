"""Synthetic private full-text library tests; no real legal source is used."""
from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile
import unittest
from zipfile import ZipFile, ZIP_DEFLATED

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools/pipeline"))
import fulltext


class FullTextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.library = self.root / "private-fulltext"
        self.snapshot = self.root / "law.txt"
        self.snapshot.write_text("第一条 Pressure equipment must be guarded.\n消防车道保持畅通。", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def manifest(self, docs):
        path = self.root / "manifest.json"
        path.write_text(json.dumps({"schemaVersion": fulltext.MANIFEST_SCHEMA, "documents": docs}, ensure_ascii=False), encoding="utf-8")
        return path

    def doc(self, version="2025", snapshot=None, review_status="待核验"):
        return {
            "documentId": "FIXTURE-LAW",
            "title": "Synthetic safety rule",
            "version": version,
            "officialUrl": "https://fixture.gov.cn/law",
            "snapshotPath": str(snapshot or self.snapshot),
            "asOf": "2026-09-09",
            "currentStatus": "现行有效",
            "reviewStatus": review_status,
        }

    def test_import_search_and_pending_is_not_current_basis(self):
        result = fulltext.import_manifest(self.library, self.manifest([self.doc()]))
        self.assertEqual(result["added"], 1)
        hits = fulltext.search(self.library, "Pressure")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["documentId"], "FIXTURE-LAW")
        self.assertEqual(hits[0]["location"], "paragraph:1")
        self.assertFalse(hits[0]["eligibleAsCurrentBasis"])
        self.assertEqual(hits[0]["reviewStatus"], "待核验")
        self.assertIn("[Pressure]", hits[0]["snippet"])
        short_hits = fulltext.search(self.library, "消防")
        self.assertEqual(len(short_hits), 1)
        self.assertIn("[消防]", short_hits[0]["snippet"])
        self.assertEqual(fulltext.search(self.library, "Pressure OR absent"), [])

    def test_versions_coexist_and_duplicate_import_is_idempotent(self):
        newer = self.root / "new.txt"
        newer.write_text("Pressure rule version 2026.", encoding="utf-8")
        manifest = self.manifest([self.doc("2025"), self.doc("2026", newer)])
        first = fulltext.import_manifest(self.library, manifest)
        second = fulltext.import_manifest(self.library, manifest)
        self.assertEqual(first["added"], 2)
        self.assertEqual(second["added"], 0)
        self.assertEqual(second["alreadyImported"], 2)
        hits = fulltext.search(self.library, "Pressure")
        self.assertEqual({hit["version"] for hit in hits}, {"2025", "2026"})

    def test_same_id_and_version_different_bytes_is_a_conflict(self):
        self.assertEqual(fulltext.import_manifest(self.library, self.manifest([self.doc()]))["added"], 1)
        changed = self.root / "changed.txt"
        changed.write_text("A different official snapshot.", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "版本冲突"):
            fulltext.import_manifest(self.library, self.manifest([self.doc(snapshot=changed)]))

    def test_corrupt_archive_is_detected_on_idempotent_import(self):
        fulltext.import_manifest(self.library, self.manifest([self.doc()]))
        archive = next((self.library / "archive").glob("*/original"))
        archive.write_bytes(b"corrupted")
        with self.assertRaisesRegex(ValueError, "归档缺失或损坏"):
            fulltext.import_manifest(self.library, self.manifest([self.doc()]))

    def test_docx_extraction_and_unsafe_or_wrong_schema_library_are_rejected(self):
        docx = self.root / "fixture.docx"
        xml = ("<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>"
               "<w:body><w:p><w:r><w:t>Article pressure</w:t></w:r></w:p></w:body></w:document>")
        with ZipFile(docx, "w", ZIP_DEFLATED) as archive:
            archive.writestr("word/document.xml", xml)
        fulltext.import_manifest(self.library, self.manifest([self.doc("docx", docx)]))
        self.assertEqual(fulltext.search(self.library, "pressure")[0]["version"], "docx")

        with self.assertRaisesRegex(ValueError, "master/staging"):
            fulltext.import_manifest(REPO / "source/master/fulltext", self.manifest([self.doc("bad")]))
        wrong = self.root / "wrong"
        wrong.mkdir()
        (wrong / "fulltext.sqlite3").write_bytes(b"not sqlite")
        with self.assertRaises(Exception):
            fulltext.search(wrong, "pressure")

    def test_html_paragraph_locations_are_preserved(self):
        html = self.root / "fixture.html"
        html.write_text("<html><body><p>alpha requirement</p><p>beta requirement</p></body></html>", encoding="utf-8")
        fulltext.import_manifest(self.library, self.manifest([self.doc("html", html)]))
        hits = fulltext.search(self.library, "beta")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["location"], "paragraph:2")


if __name__ == "__main__":
    unittest.main()
