import json
from pathlib import Path
import sqlite3
import unittest
import unicodedata

import test_admission as base
import admission


MAPPING = json.loads((base.REPO / "source/mappings/inspection-summary.json").read_text(encoding="utf-8"))


class InspectionAdmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base.AdmissionTests.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        base.AdmissionTests.tearDownClass.__func__(cls)

    setUp = base.AdmissionTests.setUp
    tearDown = base.AdmissionTests.tearDown
    path = base.AdmissionTests.path
    query = base.AdmissionTests.query
    modify = base.AdmissionTests.modify
    ingest = base.AdmissionTests.ingest
    review = base.AdmissionTests.review
    propose = base.AdmissionTests.propose
    apply = base.AdmissionTests.apply

    def source(self, external="A", result="符合", title=""):
        return {"序号": external, "隐患描述": title, "依据法规": "测试标准 第1条", "法规原文": "应留足安全活动空间，并保持通道畅通。",
                "现场实际情况": "现场留有活动空间，通道畅通。", "检查结果": result}

    @staticmethod
    def derive(item):
        return {"action": "derive", "target": "", "reason": "按两项独立义务拆成通用模板，不改变现场结论", "sourceReviewed": True,
                "basis": item["normalized"]["basis"], "quote": item["normalized"]["quote"],
                "hazards": [{"ref": "space", "title": "人员安全活动空间不足", "conditions": "有人员作业的区域", "measures": "留足安全活动空间",
                             "action": "create", "target": "", "reason": "独立空间义务"},
                            {"ref": "access", "title": "通道被占用或堵塞", "conditions": "通道用于人员通行", "measures": "清理占用物并恢复通行",
                             "action": "create", "target": "", "reason": "独立通行义务"}]}

    def test_blank_hazard_on_compliant_inspection_retains_all_original_fields(self):
        self.ingest([self.source()], mapping=MAPPING)
        _, draft = self.review()
        row = draft["items"][0]["normalized"]
        self.assertEqual(row["recordType"], "inspection")
        self.assertEqual(row["compliance"], "符合")
        self.assertEqual(row["sourceSituation"], unicodedata.normalize("NFKC", self.source()["现场实际情况"]))
        self.assertFalse(row.get("title"))
        self.assertFalse(row.get("reportedHazard"))
        self.assertEqual(row["basis"], self.source()["依据法规"])
        self.assertEqual(row["quote"], unicodedata.normalize("NFKC", self.source()["法规原文"]))

    def test_inspection_cannot_be_directly_created_or_attached(self):
        self.ingest([self.source(title="等待转译")], mapping=MAPPING)
        for action, target in (("create", ""), ("attach", "H001")):
            with self.subTest(action=action), self.assertRaisesRegex(ValueError, "不能直接"):
                self.propose(lambda item: {"action": action, "target": target, "reason": "尝试绕过转译"})

    def test_one_inspection_derives_multiple_draft_templates_without_changing_compliance(self):
        self.ingest([self.source()], mapping=MAPPING)
        count = self.query("SELECT COUNT(*) FROM verification")[0][0]
        result = self.apply(self.propose(self.derive))
        ids = result["decisions"][0]["hazardIds"]
        self.assertEqual(len(set(ids)), 2)
        for ident in ids:
            self.assertEqual(self.query("SELECT status,checked FROM hazards WHERE id=?", (ident,)), [("待整理", "")])
        self.assertEqual(self.query("SELECT kind,source_result FROM intake_derivations"), [("rule_template", "符合"), ("rule_template", "符合")])
        self.assertEqual(self.query("SELECT COUNT(*) FROM verification"), [(count,)])
        self.assertEqual(self.query("SELECT COUNT(*) FROM candidate_admissions"), [(2,)])
        raw = json.loads(self.query("SELECT r.raw_payload FROM source_rows r JOIN intake_provenance p ON r.id=p.source_row_id LIMIT 1")[0][0])
        self.assertEqual(raw["检查结果"], "符合")
        self.assertEqual(raw["隐患描述"], "")
        self.assertEqual(raw["现场实际情况"], self.source()["现场实际情况"])
        self.assertEqual(raw["法规原文"], self.source()["法规原文"])

    def test_repeated_candidate_from_new_source_reuses_every_template(self):
        self.ingest([self.source()], mapping=MAPPING)
        first = self.apply(self.propose(self.derive))
        ids = set(first["decisions"][0]["hazardIds"])
        self.ingest([self.source(external="B")], mapping=MAPPING)
        _, draft = self.review()
        self.assertEqual(draft["items"][0]["decision"]["action"], "reuse")
        second = self.apply(self.propose())
        self.assertEqual(set(second["decisions"][0]["hazardIds"]), ids)
        self.assertEqual(second["idMap"], {})
        self.assertEqual(self.query("SELECT COUNT(*) FROM intake_provenance"), [(4,)])
        self.assertEqual(self.query("SELECT COUNT(*) FROM intake_derivations"), [(2,)])
        self.assertFalse(self.review()[1]["items"])

    def test_source_column_review_and_atomic_template_text_are_required(self):
        self.ingest([self.source()], mapping=MAPPING)
        def choose(item):
            decision = self.derive(item)
            decision["sourceReviewed"] = False
            return decision
        with self.assertRaisesRegex(ValueError, "先确认"):
            self.propose(choose)
        def placeholder(item):
            decision = self.derive(item)
            decision["hazards"][0]["title"] = "符合"
            return decision
        with self.assertRaisesRegex(ValueError, "不能填写检查结果"):
            self.propose(placeholder)

    def test_noncompliant_observation_is_preserved_beside_generic_templates(self):
        source = self.source(result="不符合", title="东侧通道堆放纸箱")
        self.ingest([source], mapping=MAPPING)
        self.apply(self.propose(self.derive))
        row = json.loads(self.query("SELECT normalized_json FROM intake_candidates")[0][0])
        self.assertEqual(row["reportedHazard"], "东侧通道堆放纸箱")
        self.assertEqual(row["compliance"], "不符合")
        self.assertEqual(self.query("SELECT DISTINCT source_result FROM intake_derivations"), [("不符合",)])


if __name__ == "__main__":
    unittest.main()
