import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "tools" / "pipeline"
sys.path.insert(0, str(PIPELINE))

import catalog  # noqa: E402
import exchange  # noqa: E402


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "master.sqlite3"
        conn = sqlite3.connect(self.db)
        conn.executescript((ROOT / "source/schemas/master.sql").read_text(encoding="utf-8"))
        conn.execute("INSERT INTO sources VALUES(?,?,?,?,?,?,?,?,?)", ("S_SRC", "a" * 64, "law.txt", "text/plain", 3, "private", "archive/a", "", "2026-01-01T00:00:00+00:00"))
        conn.execute("INSERT INTO source_rows VALUES(?,?,?,?,?,?)", ("R_SRC", "S_SRC", "Sheet", 1, "/rows/0", "{}"))
        conn.execute("INSERT INTO evidence VALUES(?,?,?,?,?,?,?)", ("E_SRC", "https://example.gov.cn/law", "2026-01-01T00:00:00+00:00", "", "b" * 64, "", "p1"))
        conn.execute("INSERT INTO hazards VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", ("H001", "测试隐患", "描述", "措施", "分类", "条件", "", "直接适用", "待核验", "", 1, None, "{}"))
        conn.commit()
        conn.close()

    def tearDown(self):
        self.temp.cleanup()

    def base(self):
        conn = sqlite3.connect(self.db)
        result = exchange.state_hash(conn)
        conn.close()
        return result

    def request(self, operations, request_id="REQ_TEST_001"):
        return {"formatVersion": catalog.VERSION, "requestId": request_id, "baseStateHash": self.base(),
                "actor": "tester", "source": {"sourceId": "S_SRC", "sourceRowId": "R_SRC", "jsonPointer": "/rows/0", "evidenceId": "E_SRC"},
                "operations": operations}

    def test_create_reuse_and_tags_are_atomic(self):
        request = self.request([
            {"op": "create", "entity": "law", "ref": "tmp:law", "values": {"canonical_name": "测试法规", "issuer": "机关", "jurisdiction_code": "CN", "document_kind": "条例"}},
            {"op": "create", "entity": "law_version", "ref": "tmp:version", "values": {"law_id": "tmp:law", "version_key": "2026", "official_name": "测试法规（2026）", "source_url": "https://example.gov.cn/law"}},
            {"op": "create", "entity": "clause", "ref": "tmp:clause", "values": {"law_version_id": "tmp:version", "article_path": "第一条", "quote": "完整原文", "source_url": "https://example.gov.cn/law"}},
            {"op": "create", "entity": "link", "values": {"hazard_id": "H001", "clause_id": "tmp:clause", "role": "直接依据", "priority": 1, "applicability": "适用", "jurisdiction_code": "CN"}},
            {"op": "create", "entity": "hazard_tag", "values": {"hazard_id": "H001", "kind": "place", "value": "车间"}},
            {"op": "create", "entity": "law_alias", "values": {"law_id": "tmp:law", "alias": "测试条例"}},
        ])
        proposal = catalog.request_catalog(self.db, request)
        applied = catalog.apply_catalog(self.db, proposal)
        self.assertEqual(applied["status"], "applied")
        self.assertEqual(applied["actor"], "tester")
        conn = sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT count(*) FROM laws").fetchone()[0], 1)
        law_id = conn.execute("SELECT id FROM laws").fetchone()[0]
        self.assertEqual(conn.execute("SELECT status,revision FROM hazards WHERE id='H001'").fetchone(), ("待核验", 2))
        self.assertEqual(conn.execute("SELECT count(*) FROM hazard_tags WHERE hazard_id='H001'").fetchone()[0], 1)
        self.assertEqual(conn.execute("SELECT count(*) FROM law_aliases WHERE law_id=?", (law_id,)).fetchone()[0], 1)
        self.assertEqual(conn.execute("SELECT review_status,validity_status,checked FROM law_versions").fetchone(), ("待整理", "", ""))
        self.assertEqual(conn.execute("SELECT count(*) FROM catalog_events WHERE action_id=?", (proposal["proposalId"],)).fetchone()[0], 6)
        conn.close()
        repeat = catalog.apply_catalog(self.db, proposal)
        self.assertEqual(repeat["status"], "already_applied")

    def test_batch_request_is_not_copied_into_each_business_row(self):
        request = self.request([
            {"op": "create", "entity": "law", "ref": "tmp:law",
             "values": {"canonical_name": "共享审计法规"}},
            {"op": "create", "entity": "law_version", "ref": "tmp:version",
             "values": {"law_id": "tmp:law", "version_key": "2026", "official_name": "共享审计法规"}},
            {"op": "create", "entity": "clause", "values": {
                "law_version_id": "tmp:version", "article_path": "第一条", "quote": "第一条独有正文"}},
            {"op": "create", "entity": "clause", "values": {
                "law_version_id": "tmp:version", "article_path": "第二条", "quote": "第二条独有正文"}},
        ])
        catalog.apply_catalog(self.db, catalog.request_catalog(self.db, request))
        with closing(sqlite3.connect(self.db)) as conn:
            payload = conn.execute("SELECT legacy_payload FROM clauses WHERE article_path='第一条'").fetchone()[0]
            self.assertNotIn("第二条独有正文", payload)
            self.assertEqual(json.loads(payload)["catalogRequestId"], request["requestId"])
            audit = conn.execute("SELECT request_json FROM catalog_actions").fetchone()[0]
            self.assertIn("第一条独有正文", audit)
            self.assertIn("第二条独有正文", audit)

    def test_corrupt_decoded_text_cannot_enter_catalog(self):
        request = self.request([{"op":"create", "entity":"law", "values":{"canonical_name":"安全\ufffd生产法"}}])
        with self.assertRaisesRegex(ValueError, "编码损坏"):
            catalog.request_catalog(self.db, request)

    def test_multiple_tags_and_aliases_reserve_distinct_positions_in_one_batch(self):
        request=self.request([
            {"op":"create","entity":"law","ref":"tmp:law","values":{"canonical_name":"多别名法规"}},
            {"op":"create","entity":"hazard_tag","values":{"hazard_id":"H001","kind":"keyword","value":"培训"}},
            {"op":"create","entity":"hazard_tag","values":{"hazard_id":"H001","kind":"keyword","value":"记录"}},
            {"op":"create","entity":"law_alias","values":{"law_id":"tmp:law","alias":"简称一"}},
            {"op":"create","entity":"law_alias","values":{"law_id":"tmp:law","alias":"简称二"}},
        ])
        catalog.apply_catalog(self.db,catalog.request_catalog(self.db,request))
        with closing(sqlite3.connect(self.db)) as conn:
            self.assertEqual(conn.execute("SELECT ordinal,value FROM hazard_tags WHERE kind='keyword' ORDER BY ordinal").fetchall(),[(0,'培训'),(1,'记录')])
            self.assertEqual(conn.execute('SELECT ordinal,alias FROM law_aliases ORDER BY ordinal').fetchall(),[(0,'简称一'),(1,'简称二')])

    def test_duplicate_semantic_content_conflict_and_explicit_reuse(self):
        first = self.request([
            {"op": "create", "entity": "law", "id": "L001", "values": {"canonical_name": "同名", "issuer": "机关", "jurisdiction_code": "CN", "document_kind": "条例"}},
            {"op": "create", "entity": "law_version", "id": "V001", "values": {"law_id": "L001", "version_key": "2026", "official_name": "同名（2026）"}},
        ])
        proposal = catalog.request_catalog(self.db, first)
        catalog.apply_catalog(self.db, proposal)
        conflict = self.request([{ "op": "create", "entity": "law_version", "values": {"law_id": "L001", "version_key": "2026", "official_name": "不同名称"}}], "REQ_CONFLICT")
        with self.assertRaises(ValueError):
            catalog.request_catalog(self.db, conflict)
        reuse = self.request([{ "op": "reuse", "entity": "law", "id": "L001", "values": {"canonical_name": "同名", "issuer": "机关", "jurisdiction_code": "CN", "document_kind": "条例"}}], "REQ_REUSE")
        ready = catalog.request_catalog(self.db, reuse)
        result = catalog.apply_catalog(self.db, ready)
        self.assertEqual(result["status"], "applied")
        conn = sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT count(*) FROM laws").fetchone()[0], 1)
        conn.close()

    def test_stale_and_fake_source_are_rejected(self):
        stale = self.request([{ "op": "create", "entity": "law", "values": {"canonical_name": "过期", "issuer": "机关", "jurisdiction_code": "CN", "document_kind": "条例"}}])
        proposal = catalog.request_catalog(self.db, stale)
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE hazards SET note='changed', revision=2 WHERE id='H001'")
        conn.commit()
        conn.close()
        with self.assertRaises(ValueError):
            catalog.apply_catalog(self.db, proposal)
        fake = self.request([{ "op": "create", "entity": "law", "values": {"canonical_name": "假来源", "issuer": "机关", "jurisdiction_code": "CN", "document_kind": "条例"}, "sourceId": "S_MISSING"}])
        with self.assertRaises(ValueError):
            catalog.request_catalog(self.db, fake)

    def test_existing_update_uses_exchange_demotion_and_revision(self):
        request = self.request([{"op": "update", "entity": "hazard", "id": "H001", "values": {"description": "更新描述"}}], "REQ_UPDATE")
        proposal = catalog.request_catalog(self.db, request)
        result = catalog.apply_catalog(self.db, proposal)
        self.assertEqual(result["status"], "applied")
        conn = sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT description,status,checked,revision FROM hazards WHERE id='H001'").fetchone(), ("更新描述", "待核验", "", 2))
        conn.close()

    def test_tags_and_aliases_change_master_state_hash(self):
        before = self.base()
        conn = sqlite3.connect(self.db)
        conn.execute("INSERT INTO laws VALUES(?,?,?,?,?,?,?,?,?,?,?)", ("L_HASH", "哈希法规", "机关", "CN", "条例", "hash-key", "provisional", "待整理", "", 1, "{}"))
        conn.commit()
        conn.close()
        after_law = self.base()
        self.assertNotEqual(before, after_law)

        conn = sqlite3.connect(self.db)
        conn.execute("INSERT INTO hazard_tags VALUES(?,?,?,?)", ("H001", "place", "哈希场所", 0))
        conn.commit()
        conn.close()
        after_tag = self.base()
        self.assertNotEqual(after_law, after_tag)

        conn = sqlite3.connect(self.db)
        conn.execute("INSERT INTO law_aliases VALUES(?,?,?)", ("L_HASH", "哈希别名", 0))
        conn.commit()
        conn.close()
        self.assertNotEqual(after_tag, self.base())


if __name__ == "__main__":
    unittest.main()
