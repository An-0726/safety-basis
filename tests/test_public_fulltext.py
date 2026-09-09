"""Synthetic evidence-gated public full-text export tests."""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools/pipeline"))
import fulltext
import master
import public_fulltext
import verification


class PublicFullTextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "master.sqlite3"
        self.library = self.root / "fulltext"
        self.snapshot = self.root / "law.txt"
        self.snapshot.write_text("第一条 Pressure equipment must be guarded.", encoding="utf-8")
        self.metadata = self.root / "metadata.json"
        self.metadata.write_text('{"title":"Synthetic safety rule","status":"current"}', encoding="utf-8")
        with closing(sqlite3.connect(self.db)) as conn:
            conn.executescript((REPO / "source/schemas/master.sql").read_text(encoding="utf-8"))
            conn.executescript((REPO / "source/schemas/review.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO laws VALUES(?,?,?,?,?,?,?,?,?,?,?)", (
                "LF_TEST", "Synthetic safety rule", "测试机关", "CN", "法律", "synthetic", "confirmed", "已核验", "", 1, "{}"))
            conn.execute("INSERT INTO law_versions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                "LV_TEST", "LF_TEST", "2025", "", "Synthetic safety rule (2025)", "法律", "全国", "2020-01-01", "", "现行有效", "已核验", "https://fixture.gov.cn/law", "", 1, "{}"))
            blob = self.snapshot.read_bytes()
            sha = hashlib.sha256(blob).hexdigest()
            archive = self.root / "evidence" / "original"
            archive.parent.mkdir()
            archive.write_bytes(blob)
            conn.execute("INSERT INTO evidence VALUES(?,?,?,?,?,?,?)", (
                "E_TEST", "https://fixture.gov.cn/law", "2026-09-08T01:00:00+00:00",
                "evidence/original", sha, "", "全文"))
            metadata_blob = self.metadata.read_bytes()
            metadata_archive = self.root / "evidence" / "metadata"
            metadata_archive.write_bytes(metadata_blob)
            conn.execute("INSERT INTO evidence VALUES(?,?,?,?,?,?,?)", (
                "E_META", "https://fixture.gov.cn/law", "2026-09-08T01:00:00+00:00",
                "evidence/metadata", hashlib.sha256(metadata_blob).hexdigest(), "", "效力元数据"))
            conn.commit()
            graph = verification.graph_from_db(conn)
            law_hash = verification.dependency_hash(graph, "law", "LF_TEST")
            version_hash = verification.dependency_hash(graph, "law_version", "LV_TEST")
            for ident, rev, dep, check in (("LF_TEST", 1, law_hash, "identity"), ("LV_TEST", 1, version_hash, "version")):
                kind = "law" if ident == "LF_TEST" else "law_version"
                conn.execute("INSERT INTO verification VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                    "V_" + ident, kind, ident, rev, dep, check, "passed", "reviewer", "model",
                    "2026-09-08T02:00:00+00:00", "", "E_META", "synthetic proof", None))
            conn.execute("INSERT INTO review_actions VALUES(?,?,?,?,?,?,?,?)", ("A_TEST", "hash", "base", "result", "actor", "2026-09-08T02:00:00+00:00", "{}", "{}"))
            conn.execute("INSERT INTO verification_details VALUES(?,?,?,?)", ("V_LF_TEST", "第一条", 1, "A_TEST"))
            conn.execute("INSERT INTO verification_details VALUES(?,?,?,?)", ("V_LV_TEST", "第一条", 1, "A_TEST"))
            conn.commit()
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(json.dumps({"schemaVersion": fulltext.MANIFEST_SCHEMA, "documents": [{
            "documentId": "LF_TEST", "title": "Synthetic safety rule", "version": "2025",
            "officialUrl": "https://fixture.gov.cn/law", "snapshotPath": str(self.snapshot),
            "asOf": "2026-09-08", "currentStatus": "现行有效", "reviewStatus": "待核验"}]}, ensure_ascii=False), encoding="utf-8")
        fulltext.import_manifest(self.library, self.manifest)
        self.sha = hashlib.sha256(self.snapshot.read_bytes()).hexdigest()

    def tearDown(self):
        self.tmp.cleanup()

    def checklist(self, full_sha=None, evidence_id="E_TEST"):
        path = self.root / "checklist.json"
        path.write_text(json.dumps({"schemaVersion": public_fulltext.CHECKLIST_SCHEMA, "documents": [{
            "lawId": "LF_TEST", "versionId": "LV_TEST", "fullTextSha256": full_sha if full_sha is not None else self.sha,
            "evidenceId": evidence_id, "publicationPermission": "official_legal_text",
            "permissionReason": "官方公开法规正文", "permissionSource": "https://fixture.gov.cn/law",
            "fullTextReviewed": True, "reviewer": "reviewer", "reviewedAt": "2026-09-08T03:00:00+00:00"}]}, ensure_ascii=False), encoding="utf-8")
        return path

    def test_metadata_and_fulltext_evidence_may_be_separate(self):
        output = self.root / "public"
        result = public_fulltext.export_public(self.db, self.library, self.checklist(), "2026-09-09", output)
        self.assertEqual(result["publicCount"], 1)
        catalog = json.loads((output / "catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(catalog["documents"][0]["textMode"], "full_text")
        self.assertNotIn("evidenceId", catalog["documents"][0])
        shard = json.loads((output / "texts/LV_TEST.json").read_text(encoding="utf-8"))
        self.assertEqual(shard["paragraphs"][0]["location"], "paragraph:1")
        self.assertFalse((output / "catalog.json").read_text(encoding="utf-8").find(str(self.snapshot)) >= 0)
        search_index = json.loads((output / "search-index.json").read_text(encoding="utf-8"))
        gram = "pr"
        prefix = hashlib.sha256(gram.encode("utf-8")).hexdigest()[:2]
        self.assertEqual(search_index["gramShards"][prefix], f"grams/{prefix}.json")
        gram_shard = json.loads((output / search_index["gramShards"][prefix]).read_text(encoding="utf-8"))
        self.assertEqual(gram_shard["schemaVersion"], public_fulltext.GRAM_SCHEMA)
        self.assertEqual(gram_shard["grams"][gram], ["LV_TEST"])

    def test_failed_version_proof_is_blocked_and_not_exported(self):
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute("INSERT INTO verification VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                "V_PENDING", "law_version", "LV_TEST", 1,
                verification.dependency_hash(verification.graph_from_db(conn), "law_version", "LV_TEST"),
                "version", "pending", "reviewer", "model", "2026-09-08T04:00:00+00:00", "", "E_TEST", "pending", None))
            conn.commit()
        output = self.root / "blocked"
        result = public_fulltext.export_public(self.db, self.library, self.checklist(), "2026-09-09", output)
        self.assertEqual(result["publicCount"], 0)
        self.assertEqual(result["blockedCount"], 1)
        self.assertFalse((output / "texts/LV_TEST.json").exists())
        report = json.loads((self.root / "blocked.blockers.json").read_text(encoding="utf-8"))
        self.assertTrue(any("通过" in reason or "核验" in reason for reason in report["blockers"][0]["reasons"]))

    def test_reviewed_partial_repeal_note_reaches_public_catalog(self):
        checklist = self.checklist('')
        payload = json.loads(checklist.read_text(encoding='utf-8'))
        note = '本测试标准第三条已废止；其他条款仍需分别核对。'
        payload['documents'][0]['validityNote'] = note
        checklist.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
        output = self.root / 'partial-repeal'
        public_fulltext.export_public(self.db, self.library, checklist, '2026-09-09', output)
        catalog = json.loads((output / 'catalog.json').read_text(encoding='utf-8'))
        self.assertEqual(catalog['documents'][0]['validityNote'], note)
        self.assertNotIn('permissionReason', catalog['documents'][0])

    def test_fulltext_sha_mismatch_is_blocked(self):
        output = self.root / "sha-blocked"
        result = public_fulltext.export_public(self.db, self.library, self.checklist("0" * 64), "2026-09-09", output)
        self.assertEqual(result["publicCount"], 0)
        self.assertFalse((output / "texts/LV_TEST.json").exists())

    def test_link_only_exports_metadata_without_text_shard(self):
        output = self.root / "link-only"
        result = public_fulltext.export_public(self.db, self.library, self.checklist(""), "2026-09-09", output)
        self.assertEqual(result["publicCount"], 1)
        catalog = json.loads((output / "catalog.json").read_text(encoding="utf-8"))
        document = catalog["documents"][0]
        self.assertEqual(document["textMode"], "link_only")
        self.assertIsNone(document["textPath"])
        self.assertEqual(document["fullTextSha256"], "")
        self.assertFalse((output / "texts/LV_TEST.json").exists())

    def test_reviewed_upcoming_fulltext_and_official_link_are_both_publishable(self):
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute("UPDATE law_versions SET validity_status='即将生效',effective_date='2027-02-01'")
            graph = verification.graph_from_db(conn)
            conn.execute("INSERT INTO verification VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                'V_UPCOMING', 'law_version', 'LV_TEST', 1,
                verification.dependency_hash(graph, 'law_version', 'LV_TEST'), 'version',
                'passed', 'reviewer', 'synthetic-test', '2026-09-08T04:00:00+00:00', '',
                'E_META', 'Verified announced future edition in synthetic fixture', 'V_LV_TEST'))
            conn.execute("INSERT INTO verification_details VALUES(?,?,?,?)", ('V_UPCOMING', '实施日期', 1, 'A_TEST'))
            conn.commit()
        for sha, mode in ((self.sha, 'full_text'), ('', 'link_only')):
            with self.subTest(mode=mode):
                output = self.root / ('upcoming-' + mode)
                result = public_fulltext.export_public(self.db, self.library, self.checklist(sha), '2026-09-09', output)
                self.assertEqual(result['publicCount'], 1)
                document = json.loads((output / 'catalog.json').read_text(encoding='utf-8'))['documents'][0]
                self.assertEqual(document['status'], '即将生效')
                self.assertEqual(document['effectiveDate'], '2027-02-01')
                self.assertEqual(document['textMode'], mode)

    def test_unsupported_article_directory_is_blocked_from_public_output(self):
        unsupported = self.root / "standard.txt"
        unsupported.write_text("3.1 Requirement; 3.2 Another requirement.", encoding="utf-8")
        blob = unsupported.read_bytes()
        sha = hashlib.sha256(blob).hexdigest()
        archive = self.root / "evidence" / "unsupported"
        archive.write_bytes(blob)
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute("INSERT INTO evidence VALUES(?,?,?,?,?,?,?)", (
                "E_STD", "https://fixture.gov.cn/law", "2026-09-08T01:00:00+00:00",
                "evidence/unsupported", sha, "", "正文"))
            conn.commit()
        manifest = self.root / "standard-manifest.json"
        manifest.write_text(json.dumps({"schemaVersion": fulltext.MANIFEST_SCHEMA, "documents": [{
            "documentId": "LF_TEST", "title": "Synthetic safety rule", "version": "2025",
            "officialUrl": "https://fixture.gov.cn/law", "snapshotPath": str(unsupported),
            "asOf": "2026-09-08", "currentStatus": "现行有效", "reviewStatus": "待核验"}]}, ensure_ascii=False), encoding="utf-8")
        standard_library = self.root / "standard-fulltext"
        fulltext.import_manifest(standard_library, manifest)
        output = self.root / "unsupported-public"
        result = public_fulltext.export_public(self.db, standard_library, self.checklist(sha, "E_STD"), "2026-09-09", output)
        self.assertEqual(result["publicCount"], 0)
        self.assertEqual(result["blockedCount"], 1)
        report = json.loads((self.root / "unsupported-public.blockers.json").read_text(encoding="utf-8"))
        self.assertTrue(any("No Chinese statutory article headings" in reason
                            for reason in report["blockers"][0]["reasons"]))

    def test_metadata_link_does_not_claim_text_review_or_permission(self):
        checklist=self.checklist("")
        data=json.loads(checklist.read_text(encoding='utf-8'))
        data['documents'][0].update(publicationPermission='metadata_only',fullTextReviewed=False)
        checklist.write_text(json.dumps(data),encoding='utf-8')
        output=self.root/'metadata-only'
        result=public_fulltext.export_public(self.db,self.library,checklist,'2026-09-09',output)
        self.assertEqual(result['publicCount'],1)
        record=json.loads((output/'catalog.json').read_text(encoding='utf-8'))['documents'][0]
        self.assertFalse(record['fullTextReviewed'])
        self.assertEqual(record['textMode'],'link_only')
        data['documents'][0].update(fullTextSha256=self.sha,fullTextReviewed=True)
        checklist.write_text(json.dumps(data),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'metadata_only'):
            public_fulltext.export_public(self.db,self.library,checklist,'2026-09-09',self.root/'must-fail')


if __name__ == "__main__":
    unittest.main()
