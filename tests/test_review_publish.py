"""Synthetic legal text fixtures: exercise the gate, never validate real laws."""
from contextlib import closing
import copy
import datetime as dt
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools/pipeline"))
import exchange
import master
import publish
import review
import verification as v


class ReviewPublishTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "safety.sqlite3"
        self.counter = 0
        self.as_of = v.business_date(dt.datetime.now(dt.timezone.utc)).isoformat()
        self.url = "https://fixture.gov.cn/test-only-law.html"
        with closing(sqlite3.connect(self.db)) as conn:
            conn.executescript((REPO / "source/schemas/master.sql").read_text(encoding="utf-8"))
            def insert(table, **row):
                conn.execute(f"INSERT INTO {table} ({','.join(row)}) VALUES({','.join('?' for _ in row)})", tuple(row.values()))
            insert("laws", id="LF_TEST", canonical_name="测试法规夹具", issuer="测试机关", jurisdiction_code="CN",
                   document_kind="法律", identity_key="test-law", legacy_payload="{}", status="待核验")
            insert("law_versions", id="L_TEST", law_id="LF_TEST", version_key="2020", official_name="测试法规夹具（2020）",
                   level="法律", scope="全国", effective_date="2020-01-01", validity_status="现行有效", review_status="待核验",
                   source_url=self.url, legacy_payload="{}")
            insert("clauses", id="C_TEST", law_version_id="L_TEST", article_path="第一条", quote="测试要求：设施应保持完好。",
                   source_url=self.url, status="待核验", legacy_payload="{}")
            for number in (1, 2):
                ident = "H_TEST" + str(number)
                insert("hazards", id=ident, title="测试设施缺陷" + str(number), description="测试夹具描述", measures="测试整改措施",
                       category="测试分类", conditions="测试场景中实际存在该设施", mode="直接适用", status="待核验",
                       note="PRIVATE_INTERNAL_NOTE_DONT_PUBLISH", legacy_payload='{"secret":"PRIVATE_SOURCE"}')
                insert("hazard_tags", hazard_id=ident, kind="place", value="测试场所", ordinal=0)
                insert("hazard_tags", hazard_id=ident, kind="keyword", value="测试设施", ordinal=0)
                insert("hazard_tags", hazard_id=ident, kind="aliase", value="测试别名", ordinal=0)
                insert("links", id="K_TEST" + str(number), hazard_id=ident, clause_id="C_TEST", role="直接依据", priority=1,
                       applicability="测试夹具的设施义务适用于该测试场景", jurisdiction_code="CN", legacy_payload="{}")
            conn.commit()
        snapshot = self.root / "test-law.html"
        snapshot.write_text("<html><p>测试夹具，不是真实法规。</p><p>第一条 测试要求：设施应保持完好。</p></html>", encoding="utf-8")
        self.evidence = review.register_evidence(self.db, snapshot, self.url, "2020-01-01T01:00:00+00:00", archive=self.root / "archive")["evidenceId"]
        self.targets = ["law:LF_TEST", "law_version:L_TEST", "clause:C_TEST", "hazard:H_TEST1", "hazard:H_TEST2", "link:K_TEST1", "link:K_TEST2"]

    def tearDown(self):
        self.tmp.cleanup()

    def path(self):
        self.counter += 1
        return self.root / f"review-{self.counter}.json"

    def execute(self, sql, args=()):
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute(sql, args)
            conn.commit()

    def fetch(self, sql):
        with closing(sqlite3.connect(self.db)) as conn:
            return conn.execute(sql).fetchall()

    def draft(self, targets=None, result="passed", change=None):
        path = self.path()
        review.plan(self.db, targets or self.targets, path)
        data = json.loads(path.read_text(encoding="utf-8"))
        for item in data["items"]:
            item["decision"].update(result=result, evidenceId=self.evidence, locator="测试第一条", reason="仅用于测试核验流程", publicFieldsReviewed=True)
            if change:
                change(item)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def verified(self):
        proposal = self.path()
        review.propose(self.db, self.draft(), proposal, "test-reviewer", "synthetic-test")
        result = review.apply(self.db, proposal, "test-actor")
        return proposal, result

    def test_legacy_labels_and_manual_state_flags_do_not_publish(self):
        self.execute("UPDATE hazards SET status='已核验'")
        self.execute("UPDATE clauses SET status='已核验',identity_status='confirmed_locator'")
        self.execute("UPDATE law_versions SET review_status='已核验'")
        self.execute("UPDATE laws SET status='已核验',identity_status='confirmed'")
        self.execute("UPDATE links SET status='已核验'")
        release, report = publish.prepare(self.db, self.as_of)
        self.assertEqual(release["graph"]["hazards"], [])
        self.assertIn("没有最新通过记录", str(report))

    def test_version_number_is_searchable_without_changing_v1_rebuilds(self):
        self.execute("UPDATE law_versions SET document_number='GB/T 99999-2020'")
        self.verified()
        release, _ = publish.prepare(self.db, self.as_of)
        self.assertEqual(release['formatVersion'], 'safety-release-v2')
        self.assertIn('GB/T 99999-2020', publish.runtime_input(release)['laws'][0]['name'])
        legacy = copy.deepcopy(release)
        legacy['formatVersion'] = 'safety-release-v1'
        legacy['releaseHash'] = v.digest({k: val for k, val in legacy.items() if k != 'releaseHash'})
        publish.validate_release(legacy)
        self.assertEqual(publish.runtime_input(legacy)['laws'][0]['name'], '测试法规夹具（2020）')
        output = self.root / 'legacy-rebuild'
        publish.build(legacy, output, node=os.environ.get('SAFETY_NODE', 'node'))
        manifest = json.loads((output / 'data/manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['buildToolVersion'], 'safety-release-v1')

    def test_valid_shared_clause_release_is_private_free_and_reproducible(self):
        self.verified()
        release, report = publish.prepare(self.db, self.as_of)
        self.assertEqual(len(release["graph"]["hazards"]), 2)
        self.assertEqual(len(release["graph"]["clauses"]), 1)
        self.assertEqual(release["graph"]["hazards"][0]["aliases"], ["测试别名"])
        self.assertEqual(len(release["evidence"]), 1)
        self.assertNotIn("PRIVATE", json.dumps(release))
        self.assertNotIn("snapshot_ref", json.dumps(release))
        first, second = self.root / "build1", self.root / "build2"
        for out in (first, second):
            publish.build(release, out, node=os.environ.get("SAFETY_NODE", "node"))
        files = lambda root: {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*.json")}
        self.assertEqual(files(first), files(second))
        self.assertEqual(report["blockedHazards"], {})
        with self.assertRaisesRegex(ValueError, "拒绝覆盖"):
            publish.build(release, first)

    def test_clause_change_invalidates_every_dependent_hazard_even_without_revision_change(self):
        self.verified()
        self.execute("UPDATE clauses SET quote='被篡改的原文' WHERE id='C_TEST'")
        release, report = publish.prepare(self.db, self.as_of)
        self.assertEqual(release["graph"]["hazards"], [])
        self.assertEqual(len(report["blockedHazards"]), 2)
        self.assertIn("依赖版本不符", str(report))

    def test_law_expiry_future_effective_date_and_due_review_block_release(self):
        self.verified()
        for field, value in (("validity_status", "已废止"), ("effective_date", "2099-01-01"), ("end_date", self.as_of)):
            with self.subTest(field=field):
                original = self.fetch(f"SELECT {field} FROM law_versions")[0][0]
                self.execute(f"UPDATE law_versions SET {field}=?", (value,))
                self.assertFalse(publish.prepare(self.db, self.as_of)[0]["graph"]["hazards"])
                self.execute(f"UPDATE law_versions SET {field}=?", (original,))
        tomorrow = (v.date(self.as_of) + dt.timedelta(days=1)).isoformat()
        draft = self.draft(["clause:C_TEST"], change=lambda item: item["decision"].update(reviewDueAt=tomorrow))
        proposal = self.path()
        review.propose(self.db, draft, proposal, "test-reviewer")
        review.apply(self.db, proposal, "test-actor")
        self.assertTrue(publish.prepare(self.db, self.as_of)[0]["graph"]["hazards"])
        self.assertFalse(publish.prepare(self.db, tomorrow)[0]["graph"]["hazards"])

    def test_reviewed_upcoming_version_is_searchable_without_becoming_a_current_hazard_basis(self):
        self.execute("UPDATE law_versions SET validity_status='即将生效',effective_date='2099-01-01'")
        self.verified()
        release, report = publish.prepare(self.db, self.as_of)
        self.assertEqual([row['id'] for row in release['graph']['law_versions']], ['L_TEST'])
        self.assertEqual(release['graph']['hazards'], [])
        self.assertEqual(release['graph']['clauses'], [])
        self.assertEqual(report['blockedLawVersions'], {})
        self.assertEqual(len(report['blockedHazards']), 2)
        output = self.root / 'upcoming'
        publish.build(release, output, node=os.environ.get('SAFETY_NODE', 'node'))
        index = json.loads((output / 'data/law-index.json').read_text(encoding='utf-8'))
        self.assertEqual(index[0]['status'], '即将生效')
        self.assertEqual(index[0]['effectiveDate'], '2099-01-01')
        self.assertEqual(index[0]['hazardCount'], 0)

    def test_upcoming_still_requires_review_and_a_consistent_implementation_date(self):
        self.execute("UPDATE law_versions SET validity_status='即将生效',effective_date='2099-01-01'")
        self.assertEqual(publish.prepare(self.db, self.as_of)[0]['graph']['law_versions'], [])
        self.verified()
        self.assertEqual(len(publish.prepare(self.db, self.as_of)[0]['graph']['law_versions']), 1)
        # Crossing the announced date does not silently relabel an old snapshot.
        self.assertEqual(publish.prepare(self.db, '2099-01-01')[0]['graph']['law_versions'], [])
        proposal = self.path()
        review.propose(self.db, self.draft(['law_version:L_TEST'], result='pending'), proposal, 'test-reviewer')
        review.apply(self.db, proposal, 'test-actor')
        self.assertEqual(publish.prepare(self.db, self.as_of)[0]['graph']['law_versions'], [])

    def test_later_failed_review_supersedes_pass_and_history_is_immutable(self):
        self.verified()
        proposal = self.path()
        review.propose(self.db, self.draft(["clause:C_TEST"], result="failed"), proposal, "test-reviewer")
        review.apply(self.db, proposal, "test-actor")
        self.assertEqual(self.fetch("SELECT COUNT(*) FROM verification WHERE entity_type='clause'"), [(2,)])
        self.assertFalse(publish.prepare(self.db, self.as_of)[0]["graph"]["hazards"])
        for table in ("verification", "evidence", "review_actions", "verification_details"):
            with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
                self.execute(f"DELETE FROM {table}")

    def test_stale_proposal_and_repeated_submit(self):
        proposal, result = self.verified()
        before = self.db.read_bytes()
        again = review.apply(self.db, proposal, "test-actor")
        self.assertEqual(again["status"], "already_applied")
        self.assertEqual(again["reviews"], result["reviews"])
        self.assertEqual(before, self.db.read_bytes())
        stale = self.path()
        review.propose(self.db, self.draft(["clause:C_TEST"]), stale, "test-reviewer")
        self.execute("UPDATE hazards SET revision=revision+1 WHERE id='H_TEST1'")
        with self.assertRaisesRegex(ValueError, "过期"):
            review.apply(self.db, stale, "test-actor")

    def test_bad_quote_missing_evidence_and_unreviewed_public_fields_cannot_pass(self):
        self.execute("UPDATE clauses SET quote='原件不存在的要求'")
        with self.assertRaisesRegex(ValueError, "未在证据原件"):
            review.propose(self.db, self.draft(["clause:C_TEST"]), self.path(), "test-reviewer")
        for field, value in (("evidenceId", "E_MISSING"), ("publicFieldsReviewed", False)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                review.propose(self.db, self.draft(["hazard:H_TEST1"], change=lambda item: item["decision"].update({field: value})), self.path(), "test-reviewer")

    def test_resealed_proposal_does_not_bypass_business_rules_and_commit_rolls_back(self):
        path = self.path()
        review.propose(self.db, self.draft(), path, "test-reviewer")
        data = json.loads(path.read_text(encoding="utf-8"))
        data["items"][0]["decision"]["evidenceId"] = "E_MISSING"
        payload = {k: val for k, val in data.items() if k not in ("proposalHash", "proposalId")}
        data.update(proposalHash=v.digest(payload), proposalId="VR_" + v.digest(payload)[:26])
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(ValueError):
            review.apply(self.db, path, "test-actor")
        self.assertEqual(self.fetch("SELECT COUNT(*) FROM verification"), [(0,)])
        self.assertEqual(self.fetch("SELECT status FROM hazards"), [("待核验",), ("待核验",)])

    def test_corrupt_evidence_blocks_pass_and_existing_release_preparation(self):
        self.verified()
        ref = self.fetch("SELECT snapshot_ref FROM evidence")[0][0]
        (self.db.parent / ref).write_bytes(b"corrupted")
        self.assertFalse(publish.prepare(self.db, self.as_of)[0]["graph"]["hazards"])
        with self.assertRaisesRegex(ValueError, "官方证据原件"):
            review.propose(self.db, self.draft(["clause:C_TEST"]), self.path(), "test-reviewer")

    def test_rehashed_release_cannot_include_private_fields_or_drop_pending_links(self):
        self.verified()
        release, _ = publish.prepare(self.db, self.as_of)
        for mutate in (lambda data: data["graph"]["hazards"][0].update(raw_payload="secret"),
                       lambda data: data["graph"]["links"][0].update(status="待核验"),
                       lambda data: data["graph"]["clauses"][0].update(quote="替换条文")):
            corrupt = copy.deepcopy(release)
            mutate(corrupt)
            corrupt["releaseHash"] = v.digest({k: val for k, val in corrupt.items() if k != "releaseHash"})
            with self.assertRaises(ValueError):
                publish.validate_release(corrupt)

    def test_disabling_a_link_requires_hazard_recheck_and_withdrawals_are_reported(self):
        self.verified()
        self.execute("UPDATE links SET status='已失效',revision=revision+1 WHERE id='K_TEST1'")
        baseline = self.root / "baseline.json"
        baseline.write_text('[{"id":"H_TEST1"},{"id":"H_TEST2"}]', encoding="utf-8")
        release, report = publish.prepare(self.db, self.as_of, baseline=baseline)
        self.assertEqual([r["id"] for r in release["graph"]["hazards"]], ["H_TEST2"])
        self.assertEqual(report["removedHazardIds"], ["H_TEST1"])
        self.assertTrue(report["requiresPublicationReview"])

    def test_partial_sql_failure_rolls_back_all_reviews(self):
        path = self.path()
        review.propose(self.db, self.draft(), path, "test-reviewer")
        self.execute("CREATE TRIGGER fail_last BEFORE INSERT ON verification WHEN NEW.entity_type='link' BEGIN SELECT RAISE(ABORT,'test failure'); END")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "test failure"):
            review.apply(self.db, path, "test-actor")
        self.assertEqual(self.fetch("SELECT COUNT(*) FROM verification"), [(0,)])
        self.assertEqual(self.fetch("SELECT COUNT(*) FROM review_actions"), [(0,)])
        self.assertEqual(self.fetch("SELECT identity_status FROM laws"), [("provisional",)])

    def test_duplicate_provisional_laws_cannot_both_pass_in_one_batch(self):
        self.execute("""INSERT INTO laws(id,canonical_name,issuer,jurisdiction_code,document_kind,identity_key,status,legacy_payload)
                        SELECT 'LF_DUPLICATE',canonical_name,issuer,jurisdiction_code,document_kind,'duplicate-key',status,legacy_payload
                        FROM laws WHERE id='LF_TEST'""")
        targets = ["law:LF_TEST", "law:LF_DUPLICATE"]
        for ordered in (targets, list(reversed(targets))):
            with self.subTest(order=ordered), self.assertRaisesRegex(ValueError, "相同的已确认法规身份"):
                review.propose(self.db, self.draft(ordered), self.path(), "test-reviewer")
        draft = self.draft(targets, change=lambda item: item["decision"].update(
            result="pending" if item["entityId"] == "LF_DUPLICATE" else "passed"))
        proposal = self.path()
        review.propose(self.db, draft, proposal, "test-reviewer")
        data = json.loads(proposal.read_text(encoding="utf-8"))
        data["items"][1]["decision"]["result"] = "passed"
        payload = {k: val for k, val in data.items() if k not in ("proposalHash", "proposalId")}
        data.update(proposalHash=v.digest(payload), proposalId="VR_" + v.digest(payload)[:26])
        proposal.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "相同的已确认法规身份"):
            review.apply(self.db, proposal, "test-actor")
        self.assertEqual(self.fetch("SELECT COUNT(*) FROM verification"), [(0,)])
        self.assertEqual(self.fetch("SELECT identity_status FROM laws"), [("provisional",), ("provisional",)])

    def test_china_business_date_does_not_publish_tomorrows_review_yesterday(self):
        self.assertEqual(v.business_date("2026-09-08T16:01:00+00:00").isoformat(), "2026-09-09")
        self.verified()
        previous_day = (v.date(self.as_of) - dt.timedelta(days=1)).isoformat()
        self.assertFalse(publish.prepare(self.db, previous_day)[0]["graph"]["hazards"])


if __name__ == "__main__":
    unittest.main()
