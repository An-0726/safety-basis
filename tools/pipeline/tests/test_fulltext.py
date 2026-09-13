"""Synthetic private full-text library tests; no real legal source is used."""
from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[3]
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

    def doc(self, version="2025", snapshot=None, review_status="待核验", text_path=None):
        result = {
            "documentId": "FIXTURE-LAW",
            "title": "Synthetic safety rule",
            "version": version,
            "officialUrl": "https://fixture.gov.cn/law",
            "snapshotPath": str(snapshot or self.snapshot),
            "asOf": "2026-09-13",
            "currentStatus": "现行有效",
            "reviewStatus": review_status,
        }
        if text_path:
            result["textPath"] = str(text_path)
        return result

    def test_import_search_and_pending_is_not_current_basis(self):
        result = fulltext.import_manifest(self.library, self.manifest([self.doc()]))
        self.assertEqual(result["added"], 1)
        hit = fulltext.search(self.library, "Pressure")[0]
        self.assertEqual(hit["documentId"], "FIXTURE-LAW")
        self.assertFalse(hit["eligibleAsCurrentBasis"])
        self.assertEqual(len(fulltext.search(self.library, "消防")), 1)

    def test_duplicate_import_is_idempotent_and_conflict_is_blocked(self):
        manifest = self.manifest([self.doc()])
        self.assertEqual(fulltext.import_manifest(self.library, manifest)["added"], 1)
        self.assertEqual(fulltext.import_manifest(self.library, manifest)["alreadyImported"], 1)
        changed = self.root / "changed.txt"
        changed.write_text("different original", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "版本冲突"):
            fulltext.import_manifest(self.library, self.manifest([self.doc(snapshot=changed)]))

    def test_ocr_sidecar_indexes_text_but_archives_original(self):
        original = self.root / "scan.pdf"
        original.write_bytes(b"%PDF synthetic immutable original")
        sidecar = self.root / "scan.ocr.txt"
        sidecar.write_text("第三条 OCR searchable requirement", encoding="utf-8")
        result = fulltext.import_manifest(self.library, self.manifest([self.doc(snapshot=original, text_path=sidecar)]))
        self.assertEqual(result["added"], 1)
        hit = fulltext.search(self.library, "searchable")[0]
        archived = self.library / hit["archiveRef"]
        self.assertEqual(archived.read_bytes(), original.read_bytes())


if __name__ == "__main__":
    unittest.main()
