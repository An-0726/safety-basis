"""Regression tests for the permanent publication integrity gate."""
from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools" / "v4"))
import validate_publication_integrity as gate


class PublicationIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.old_globals = (gate.ROOT, gate.KNOW, gate.PUB, gate.FT)
        gate.ROOT = self.root
        gate.KNOW = self.root / "knowledge"
        gate.PUB = self.root / "source" / "publication"
        gate.FT = gate.PUB / "fulltext"
        self.make_valid_fixture()

    def tearDown(self):
        gate.ROOT, gate.KNOW, gate.PUB, gate.FT = self.old_globals
        self.tmp.cleanup()

    @staticmethod
    def write_json(path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def read_json(path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    def make_valid_fixture(self) -> None:
        entities = {
            "laws/LF_TEST.json": {"id": "LF_TEST"},
            "law-versions/LV_TEST.json": {
                "id": "LV_TEST",
                "lawId": "LF_TEST",
                "documentNumber": "TEST-1",
                "effectiveDate": "2026-01-01",
                "sourceUrl": "https://example.test/law",
                "validityStatus": "active",
            },
            "clauses/C_TEST.json": {
                "id": "C_TEST",
                "lawVersionId": "LV_TEST",
            },
            "hazards/H_ACTIVE.json": {
                "id": "H_ACTIVE",
                "lifecycle": "active",
            },
            "hazards/H_PROPOSED.json": {
                "id": "H_PROPOSED",
                "lifecycle": "proposed",
            },
        }
        for rel, payload in entities.items():
            self.write_json(gate.KNOW / rel, payload)

        pub_row = {
            "id": "LV_TEST",
            "name": "测试法规 TEST-1",
            "aliases": [],
            "documentNumber": "TEST-1",
            "level": "测试",
            "scope": "国家",
            "status": "现行有效",
            "checked": "2026-09-17",
            "effectiveDate": "2026-01-01",
            "sourceUrl": "https://example.test/law",
            "replaces": [],
            "replacedBy": [],
            "clauseRefs": [
                {"clauseId": "C_TEST", "clauseShard": "", "hazardIds": ["H_ACTIVE"]}
            ],
            "hazardCount": 1,
            "clauseCount": 1,
            "searchText": "测试法规test1",
        }
        self.write_json(gate.PUB / "law-index.json", [pub_row])

        text_payload = {
            "schemaVersion": gate.TEXT_SCHEMA,
            "lawId": "LF_TEST",
            "versionId": "LV_TEST",
            "title": "测试法规",
            "version": "TEST-1",
            "paragraphs": [
                {"location": "paragraph:1", "text": "测试条文要求安全管理。"},
                {"location": "paragraph:2", "text": "第二段用于搜索索引。"},
            ],
        }
        self.write_json(gate.FT / "texts" / "LV_TEST.json", text_payload)

        doc = {
            "lawId": "LF_TEST",
            "versionId": "LV_TEST",
            "title": "测试法规 TEST-1",
            "version": "TEST-1",
            "officialUrl": "https://example.test/law",
            "effectiveDate": "2026-01-01",
            "status": "现行有效",
            "textMode": "full_text",
            "fullTextSha256": "0" * 64,
            "textPath": "texts/LV_TEST.json",
            "fullTextReviewed": True,
            "publicationPermission": "official_legal_text",
        }
        catalog = {
            "schemaVersion": gate.CATALOG_SCHEMA,
            "asOf": "2026-09-17",
            "documents": [doc],
        }
        self.write_json(gate.FT / "catalog.json", catalog)

        errors = []
        index_docs, shards, shard_map = gate.expected_search([doc], errors)
        self.assertEqual(errors, [])
        search_index = {
            "schemaVersion": gate.SEARCH_SCHEMA,
            "asOf": "2026-09-17",
            "documents": index_docs,
            "gramShards": shard_map,
        }
        self.write_json(gate.FT / "search-index.json", search_index)
        for prefix, grams in shards.items():
            self.write_json(
                gate.FT / "grams" / f"{prefix}.json",
                {"schemaVersion": gate.GRAM_SCHEMA, "grams": grams},
            )

    def run_gate(self):
        output = io.StringIO()
        with redirect_stdout(output):
            rc = gate.main()
        return rc, output.getvalue()

    def test_valid_fixture_passes(self):
        rc, output = self.run_gate()
        self.assertEqual(rc, 0, output)
        self.assertIn('"ok": true', output)

    def test_orphan_public_text_file_fails(self):
        self.write_json(
            gate.FT / "texts" / "ORPHAN.json",
            {
                "schemaVersion": gate.TEXT_SCHEMA,
                "lawId": "LF_TEST",
                "versionId": "ORPHAN",
                "paragraphs": [],
            },
        )
        rc, output = self.run_gate()
        self.assertEqual(rc, 1)
        self.assertIn("catalog/fulltext file set mismatch", output)
        self.assertIn("texts/ORPHAN.json", output)

    def test_stale_search_shard_fails(self):
        shard = next((gate.FT / "grams").glob("*.json"))
        payload = self.read_json(shard)
        payload["grams"]["伪造"] = ["LV_TEST"]
        self.write_json(shard, payload)
        rc, output = self.run_gate()
        self.assertEqual(rc, 1)
        self.assertIn("fulltext gram shard is stale", output)

    def test_proposed_hazard_leak_fails(self):
        index_path = gate.PUB / "law-index.json"
        rows = self.read_json(index_path)
        rows[0]["clauseRefs"][0]["hazardIds"] = ["H_PROPOSED"]
        self.write_json(index_path, rows)
        rc, output = self.run_gate()
        self.assertEqual(rc, 1)
        self.assertIn("proposed hazard leaked into publication metadata", output)

    def test_catalog_law_identity_mismatch_fails(self):
        path = gate.FT / "catalog.json"
        catalog = self.read_json(path)
        catalog["documents"][0]["lawId"] = "LF_WRONG"
        self.write_json(path, catalog)
        rc, output = self.run_gate()
        self.assertEqual(rc, 1)
        self.assertIn("fulltext catalog lawId mismatch", output)

    def test_fulltext_schema_mismatch_fails(self):
        path = gate.FT / "texts" / "LV_TEST.json"
        payload = self.read_json(path)
        payload["schemaVersion"] = "wrong-schema"
        self.write_json(path, payload)
        rc, output = self.run_gate()
        self.assertEqual(rc, 1)
        self.assertIn("full-text payload schema mismatch", output)

    def test_search_index_asof_must_match_catalog(self):
        path = gate.FT / "search-index.json"
        payload = self.read_json(path)
        payload["asOf"] = "2026-09-16"
        self.write_json(path, payload)
        rc, output = self.run_gate()
        self.assertEqual(rc, 1)
        self.assertIn("fulltext search-index/catalog asOf mismatch", output)


if __name__ == "__main__":
    unittest.main()
