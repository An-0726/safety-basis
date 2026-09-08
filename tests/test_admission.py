"""End-to-end private admission/merge tests; fixtures never change production data."""
from contextlib import closing
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools/pipeline"))
import admission
import exchange
import intake
import master

MAPPING = {"version": 1, "fields": {field: [field] for field in
           ("title", "description", "category", "place", "basis", "measures", "conditions", "externalId")}, "required": ["title"]}


class AdmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = tempfile.TemporaryDirectory()
        cls.fixture = Path(cls.fixtures.name)
        master.migrate(REPO, cls.fixture / "source/master/safety.sqlite3", cls.fixture / "source/archive")

    @classmethod
    def tearDownClass(cls):
        cls.fixtures.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        shutil.copytree(self.fixture / "source", self.root / "source")
        self.db = self.root / "source/master/safety.sqlite3"
        self.staging = self.root / "staging.sqlite3"
        self.archive = self.root / "source/archive"
        self.counter = 0

    def tearDown(self):
        self.tmp.cleanup()

    def path(self, suffix="json"):
        self.counter += 1
        return self.root / f"artifact-{self.counter}.{suffix}"

    def query(self, sql, args=(), db=None):
        with closing(sqlite3.connect(db or self.db)) as conn:
            return conn.execute(sql, args).fetchall()

    def modify(self, sql, args=(), db=None):
        with closing(sqlite3.connect(db or self.db)) as conn:
            with conn:
                conn.execute(sql, args)

    def ingest(self, data, file=None, mapping=MAPPING):
        file = file or self.path()
        file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        with closing(intake.connect(self.staging)) as conn:
            report = intake.ingest(conn, file, mapping, self.root / "intake-archive")
        self.assertEqual(report["status"], "complete", report)
        return file

    def review(self, choose=None):
        path = self.path()
        admission.plan(self.db, self.staging, path)
        document = json.loads(path.read_text(encoding="utf-8"))
        if choose:
            for item in document["items"]:
                item["decision"] = choose(item)
            path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        return path, document

    def propose(self, choose=None):
        path, _ = self.review(choose)
        output = self.path()
        admission.propose(self.db, self.staging, path, output)
        return output

    def apply(self, proposal):
        return admission.apply(self.db, proposal, "test-reviewer", staging_db=self.staging, archive=self.archive)

    @staticmethod
    def create(item):
        return {"action": "create", "target": "", "reason": "隔离测试：独立隐患概念"}

    def test_new_hazard_defaults_to_draft_and_source_law_is_not_verified(self):
        original = self.ingest([{"title": "测试夹具：新隐患", "place": "车间", "basis": "源文件自称已核验的法规", "externalId": "Z0001"}])
        counts = [self.query(f"SELECT COUNT(*) FROM {table}")[0][0] for table in ("laws", "clauses", "links", "verification")]
        proposal = self.propose(self.create)
        result = self.apply(proposal)
        ident = next(iter(result["idMap"].values()))
        self.assertRegex(ident, r"^H_[0-9A-F]{26}$")
        self.assertEqual(self.query("SELECT status,checked,revision FROM hazards WHERE id=?", (ident,)), [("待整理", "", 1)])
        self.assertEqual(counts, [self.query(f"SELECT COUNT(*) FROM {table}")[0][0] for table in ("laws", "clauses", "links", "verification")])
        self.assertIn("Z0001", self.query("SELECT raw_payload FROM source_rows WHERE id LIKE 'R_%'")[0][0])
        normalized = json.loads(self.query("SELECT normalized_json FROM intake_candidates")[0][0])
        self.assertEqual(normalized["basis"], "源文件自称已核验的法规")
        source = self.query("SELECT storage_ref,visibility FROM sources WHERE id=?", ("S_" + intake.digest(original.read_bytes()),))[0]
        self.assertEqual((self.db.parent / source[0]).read_bytes(), original.read_bytes())
        self.assertEqual(source[1], "private")
        self.assertEqual(self.query("SELECT COUNT(*) FROM intake_provenance"), [(1,)])

    def test_repeated_submit_and_repeated_or_renamed_import_are_idempotent(self):
        file = self.ingest([{"title": "测试重复", "externalId": "row-1"}])
        proposal = self.propose(self.create)
        first = self.apply(proposal)
        before = self.db.read_bytes()
        again = self.apply(proposal)
        self.assertEqual(again["status"], "already_applied")
        self.assertEqual(again["idMap"], first["idMap"])
        self.assertEqual(before, self.db.read_bytes())
        with closing(intake.connect(self.staging)) as conn:
            self.assertTrue(intake.ingest(conn, file, MAPPING, self.root / "intake-archive")["repeated"])
        _, review = self.review()
        self.assertEqual(review["items"], [])
        renamed = self.root / "renamed.json"
        shutil.copyfile(file, renamed)
        with closing(intake.connect(self.staging)) as conn:
            self.assertTrue(intake.ingest(conn, renamed, MAPPING, self.root / "intake-archive")["repeated"])
        alias_proposal = self.propose()
        alias_result = self.apply(alias_proposal)
        self.assertEqual(alias_result["decisions"][0]["action"], "attach")
        self.assertEqual(self.query("SELECT COUNT(*) FROM candidate_admissions"), [(1,)])
        self.assertEqual(self.query("SELECT COUNT(*) FROM intake_source_locations"), [(2,)])

    def test_distinct_sources_for_same_candidate_reuse_master_id(self):
        self.ingest([{"title": "测试相同候选", "externalId": "A"}])
        first = self.apply(self.propose(self.create))
        ident = next(iter(first["idMap"].values()))
        self.ingest([{"title": "测试相同候选", "externalId": "B"}])
        second = self.apply(self.propose())
        self.assertEqual(second["decisions"][0]["hazardId"], ident)
        self.assertEqual(second["idMap"], {})
        self.assertEqual(self.query("SELECT COUNT(*) FROM intake_provenance"), [(2,)])
        self.assertEqual(self.query("SELECT revision FROM hazards WHERE id=?", (ident,)), [(1,)])

    def test_similar_titles_need_decisions_and_conditions_are_preserved(self):
        self.ingest([{"title": "压力不足", "conditions": "低于0.1MPa"}, {"title": "压力不足", "conditions": "低于0.2MPa"}])
        review_file, review = self.review()
        self.assertEqual(len(review["items"]), 2)
        for item in review["items"]:
            self.assertEqual(item["decision"]["action"], "review")
            self.assertTrue(any(m["target"].startswith("new:") for m in item["suggestedMatches"]))
        with self.assertRaisesRegex(ValueError, "选择"):
            admission.propose(self.db, self.staging, review_file, self.path())

    def test_cross_candidate_temporary_reference_joins_two_different_rows(self):
        self.ingest([{"title": "统一概念", "basis": "来源A"}, {"title": "统一概念", "basis": "来源B"}])
        review_file, review = self.review()
        first, second = review["items"]
        first["decision"] = self.create(first)
        second["decision"] = {"action": "attach", "target": "new:" + first["candidateId"], "reason": "测试确认两个来源同一概念"}
        review_file.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")
        proposal = self.path()
        admission.propose(self.db, self.staging, review_file, proposal)
        result = self.apply(proposal)
        self.assertEqual(len(result["idMap"]), 1)
        self.assertEqual(self.query("SELECT COUNT(*),COUNT(DISTINCT hazard_id) FROM candidate_admissions"), [(2, 1)])
        self.assertEqual(self.query("SELECT COUNT(*) FROM source_rows WHERE id LIKE 'R_%'"), [(2,)])

    def test_attach_to_existing_record_preserves_existing_content_and_verification(self):
        self.ingest([{"title": "来源对灭火器的描述", "basis": "未核验依据"}])
        before = self.query("SELECT * FROM hazards WHERE id='H001'")
        records = self.query("SELECT * FROM verification")
        self.apply(self.propose(lambda _: {"action": "attach", "target": "H001", "reason": "测试确认同一知识概念，仅保留新来源"}))
        self.assertEqual(self.query("SELECT * FROM hazards WHERE id='H001'"), before)
        self.assertEqual(self.query("SELECT * FROM verification"), records)

    def test_stale_master_and_staging_both_block_commit(self):
        self.ingest([{"title": "过期测试"}])
        proposal = self.propose(self.create)
        self.ingest([{"title": "后来导入的内容"}])
        before = self.db.read_bytes()
        with self.assertRaisesRegex(ValueError, "staging"):
            self.apply(proposal)
        self.assertEqual(before, self.db.read_bytes())
        fresh = self.propose(self.create)
        self.modify("UPDATE hazards SET revision=revision+1 WHERE id='H001'")
        with self.assertRaisesRegex(ValueError, "母库已变化"):
            self.apply(fresh)

    def test_corrupt_archive_aborts_without_partial_master_or_schema(self):
        self.ingest([{"title": "原件损坏"}])
        proposal = self.propose(self.create)
        archive = self.query("SELECT archive_path FROM sources", db=self.staging)[0][0]
        Path(archive).write_bytes(b"damaged")
        before = self.db.read_bytes()
        with self.assertRaisesRegex(ValueError, "归档校验失败"):
            self.apply(proposal)
        self.assertEqual(self.db.read_bytes(), before)
        self.assertEqual(self.query("SELECT name FROM sqlite_master WHERE name='master_actions'"), [])

    def test_late_failure_rolls_back_hazards_provenance_and_receipt(self):
        self.ingest([{"title": "晚期回滚测试"}])
        proposal = self.propose(self.create)
        before = self.db.read_bytes()
        with patch.object(admission, "add_provenance", side_effect=RuntimeError("forced")):
            with self.assertRaises(RuntimeError): self.apply(proposal)
        self.assertEqual(self.db.read_bytes(), before)

    def test_proposal_rehash_cannot_create_verified_records_or_forged_origins(self):
        self.ingest([{"title": "提案保护"}])
        proposal = self.propose(self.create)
        original = json.loads(proposal.read_text(encoding="utf-8"))
        for mutation in ("status", "raw", "normal", "action"):
            with self.subTest(mutation=mutation):
                payload = admission.unseal(json.loads(json.dumps(original)))
                if mutation == "status": payload["items"][0]["status"] = "已核验"
                if mutation == "raw": payload["items"][0]["bundle"]["origins"][0]["parsedRaw"] = "{}"
                if mutation == "normal": payload["items"][0]["bundle"]["normalized"]["title"] = "伪造"
                if mutation == "action": payload["decisions"][0]["action"] = "publish"
                proposal.write_text(json.dumps(admission.seal(payload)), encoding="utf-8")
                before = self.db.read_bytes()
                with self.assertRaises(ValueError): self.apply(proposal)
                self.assertEqual(before, self.db.read_bytes())

    def test_bad_targets_and_cycle_of_temporary_refs_rejected(self):
        self.ingest([{"title": "目标测试A"}, {"title": "目标测试B"}])
        for target in ("H999", "new:missing"):
            with self.subTest(target=target):
                with self.assertRaises(ValueError):
                    self.propose(lambda _: {"action": "attach", "target": target, "reason": "测试"})
        review_file, review = self.review()
        a, b = review["items"]
        a["decision"] = {"action": "attach", "target": "new:" + b["candidateId"], "reason": "test"}
        b["decision"] = {"action": "attach", "target": "new:" + a["candidateId"], "reason": "test"}
        review_file.write_text(json.dumps(review), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "临时引用"):
            admission.propose(self.db, self.staging, review_file, self.path())

    def test_closed_target_cannot_be_reactivated(self):
        self.ingest([{"title": "失效测试"}])
        self.modify("UPDATE hazards SET status='已失效' WHERE id='H001'")
        with self.assertRaisesRegex(ValueError, "关闭"):
            self.propose(lambda _: {"action": "attach", "target": "H001", "reason": "test"})
        with self.assertRaisesRegex(ValueError, "关闭"):
            admission.propose_merge(self.db, "H002", "H001", "test", self.path())

    def test_hazard_merge_preserves_source_links_and_invalidates_target_links(self):
        before_links = self.query("SELECT * FROM links WHERE hazard_id='H001'")
        before_verification = self.query("SELECT * FROM verification")
        proposal = self.path()
        admission.propose_merge(self.db, "H001", "H002", "隔离测试合并，不作为真实知识判断", proposal)
        result = self.apply(proposal)
        self.assertEqual(result["targetId"], "H002")
        self.assertEqual(self.query("SELECT status,merged_into,revision FROM hazards WHERE id='H001'"), [("merged", "H002", 2)])
        self.assertEqual(self.query("SELECT status,revision FROM hazards WHERE id='H002'"), [("待核验", 2)])
        self.assertEqual(before_links, self.query("SELECT * FROM links WHERE hazard_id='H001'"))
        self.assertEqual(before_verification, self.query("SELECT * FROM verification"))
        self.assertEqual(self.query("SELECT DISTINCT status FROM links WHERE hazard_id='H002'"), [("待核验",)])
        self.assertEqual(self.query("SELECT COUNT(*) FROM merge_decisions"), [(1,)])
        self.assertEqual(self.apply(proposal)["status"], "already_applied")
        with self.assertRaises(ValueError):
            admission.propose_merge(self.db, "H002", "H001", "不能循环", self.path())

    def test_merge_duplicate_clause_keeps_both_interpretations_for_review(self):
        self.modify("INSERT INTO links SELECT 'K_TEST_CONFLICT','H002',clause_id,'冲突角色',999,'另一适用范围','江苏','已核验',1,'{}' FROM links WHERE hazard_id='H001' LIMIT 1")
        proposal = self.path()
        admission.propose_merge(self.db, "H001", "H002", "隔离测试冲突", proposal)
        payload = json.loads(proposal.read_text(encoding="utf-8"))
        self.assertTrue(payload["linkConflicts"])
        self.apply(proposal)
        self.assertEqual(self.query("SELECT role,priority,applicability,status,revision FROM links WHERE id='K_TEST_CONFLICT'"),
                         [("冲突角色", 999, "另一适用范围", "待核验", 2)])

    def test_admitted_candidate_resolves_to_survivor_after_merge(self):
        self.ingest([{"title": "入库后合并", "externalId": "A"}])
        created = self.apply(self.propose(self.create))
        ident = next(iter(created["idMap"].values()))
        proposal = self.path()
        admission.propose_merge(self.db, ident, "H001", "隔离测试归并", proposal)
        self.apply(proposal)
        self.ingest([{"title": "入库后合并", "externalId": "B"}])
        result = self.apply(self.propose())
        self.assertEqual(result["decisions"][0]["hazardId"], "H001")
        self.assertEqual(self.query("SELECT COUNT(*) FROM intake_provenance WHERE entity_id='H001'"), [(2,)])

    def test_existing_excel_snapshot_expires_on_admission_and_new_export_roundtrips(self):
        oldbook = self.path("xlsx")
        exchange.export_workbook(self.db, oldbook)
        self.ingest([{"title": "入库后Excel"}])
        self.apply(self.propose(self.create))
        with self.assertRaisesRegex(ValueError, "母库已变化"):
            exchange.create_proposal(self.db, oldbook, self.path())
        newbook = self.path("xlsx")
        exchange.export_workbook(self.db, newbook)
        self.assertEqual(exchange.create_proposal(self.db, newbook, self.path())["changeCount"], 0)

    def test_defer_leaves_candidate_pending_and_does_not_change_knowledge(self):
        self.ingest([{"title": "待后续整理"}])
        before = self.query("SELECT COUNT(*) FROM hazards")
        self.apply(self.propose(lambda _: {"action": "defer", "target": "", "reason": "需要更多现场条件"}))
        self.assertEqual(before, self.query("SELECT COUNT(*) FROM hazards"))
        self.assertEqual(self.query("SELECT COUNT(*) FROM candidate_admissions"), [(0,)])
        _, review = self.review()
        self.assertEqual(len(review["items"]), 1)

    def test_raw_archives_restore_after_portable_backup(self):
        file = self.ingest([{"title": "可搬迁原件"}])
        self.apply(self.propose(self.create))
        backup = self.root / "backup"
        shutil.copytree(self.root / "source", backup / "source")
        result = master.restore(backup / "source/master/safety.sqlite3", backup / "restored")
        self.assertGreater(result["count"], 19)
        restored = backup / "restored/source/imports" / intake.digest(file.read_bytes()) / file.name
        self.assertEqual(restored.read_bytes(), file.read_bytes())

    def test_no_overwrite_and_audit_records_are_append_only(self):
        self.ingest([{"title": "审计不可覆盖"}])
        proposal = self.propose(self.create)
        with self.assertRaises(ValueError): admission.plan(self.db, self.staging, self.db)
        self.apply(proposal)
        with self.assertRaises(sqlite3.IntegrityError): self.modify("DELETE FROM master_actions")
        with self.assertRaises(sqlite3.IntegrityError): self.modify("UPDATE master_actions SET actor='changed'")


if __name__ == "__main__":
    unittest.main()
