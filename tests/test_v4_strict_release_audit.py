# -*- coding: utf-8 -*-
"""Tests for the V4 release gate refactor.

Covers:
1. strict_release_audit.py runs end-to-end (subprocess smoke).
2. Shared core invariants on real knowledge (eligibility closure).
3. Pure logic of release_gate_core: asOf validity, jurisdiction normalization,
   review binding, law-version current-support rules.
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools" / "v4"
sys.path.insert(0, str(TOOLS))

from canonical import content_hash  # noqa: E402
import release_gate_core as core  # noqa: E402


class StrictAuditSmokeTest(unittest.TestCase):
    def test_strict_audit_runs_and_classifies(self):
        p = subprocess.run(
            [sys.executable, str(TOOLS / "strict_release_audit.py")],
            cwd=str(ROOT), text=True, capture_output=True,
            encoding="utf-8", errors="replace",
        )
        self.assertEqual(p.returncode, 0, msg=p.stderr or p.stdout)
        self.assertIn("STRICT_V4_RELEASE_AUDIT", p.stdout)
        # 抓取 JSON 部分
        payload = p.stdout.split("=== STRICT_V4_RELEASE_AUDIT ===", 1)[1]
        data = json.loads(payload)
        for field in ("releaseBlockers", "inventoryWarnings", "excludedEntities",
                      "eligibleHazards", "eligibleLinks", "strictVerdict",
                      "blockerCount", "warningCount"):
            self.assertIn(field, data)
        self.assertEqual(data["blockerCount"], len(data["releaseBlockers"]))
        self.assertEqual(data["strictVerdict"],
                         "BLOCK" if data["blockerCount"] > 0 else "PASS")
        # 合格 hazard/link 数必须为正
        self.assertGreater(data["eligibleHazards"], 0)
        self.assertGreater(data["eligibleLinks"], 0)


class RealKnowledgeInvariantsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = core.evaluate_release_gate()

    def test_eligible_hazards_are_active_and_content_ok(self):
        for hid in self.gate.eligible_hazards:
            v = self.gate.hazards[hid]
            self.assertTrue(v["active"])
            self.assertFalse(v["merged"])
            self.assertTrue(v["content_ok"])

    def test_every_eligible_hazard_has_qualifying_eligible_link(self):
        for hid in self.gate.eligible_hazards:
            qs = self.gate.qualifying_links_by_hazard.get(hid, [])
            self.assertTrue(qs)
            for kid in qs:
                self.assertIn(kid, self.gate.eligible_links)
                self.assertIn(self.gate.links[kid]["role"], core.QUALIFYING_ROLES)

    def test_eligible_links_point_at_active_supporting_versions(self):
        # 任一合格 link 的 clause -> lawVersion 必须 supports_current
        clauses = self.gate.clauses
        lvs = self.gate.law_versions
        for kid in self.gate.eligible_links:
            cid = self.gate.links[kid]["clauseId"]
            vid = clauses[cid]["lawVersionId"]
            self.assertTrue(lvs[vid]["supports_current"])
            self.assertEqual(lvs[vid]["validityStatus"], "active")

    def test_no_verified_link_silently_broken(self):
        # 已签署 verified 的 link 要么合格，要么必须在 releaseBlockers 里被点名
        for kid, v in self.gate.links.items():
            if v["decision"] == "verified" and not v["ok"]:
                self.fail("verified link %s not eligible: %s" % (kid, v["reasons"]))


class AsOfValidityTest(unittest.TestCase):
    AS_OF = core.date(2026, 9, 10)

    def _review(self, ent):
        return {"decision": "verified",
                "reviewedContentHash": content_hash(ent),
                "evidenceRefs": ["EV_X"]}

    def test_active_in_window_supports_current(self):
        lv = {"id": "L1", "lawId": "LF", "versionKey": "L1", "officialName": "x",
              "effectiveDate": "2020-01-01", "endDate": "", "validityStatus": "active"}
        ok, supports, reasons = core.gate_law_version(lv, self._review(lv), True, self.AS_OF)
        self.assertTrue(ok)
        self.assertTrue(supports)

    def test_active_after_enddate_does_not_support(self):
        lv = {"id": "L1", "lawId": "LF", "versionKey": "L1", "officialName": "x",
              "effectiveDate": "2020-01-01", "endDate": "2026-01-01", "validityStatus": "active"}
        ok, supports, reasons = core.gate_law_version(lv, self._review(lv), True, self.AS_OF)
        self.assertFalse(supports)
        self.assertTrue(any("EXPIRED" in r for r in reasons))

    def test_upcoming_does_not_support_current(self):
        lv = {"id": "L1", "lawId": "LF", "versionKey": "L1", "officialName": "x",
              "effectiveDate": "2026-10-01", "endDate": "", "validityStatus": "upcoming"}
        ok, supports, reasons = core.gate_law_version(lv, self._review(lv), True, self.AS_OF)
        self.assertFalse(supports)
        self.assertTrue(ok)  # upcoming 自身结构合格，只是不能支撑当前

    def test_upcoming_in_past_is_flagged(self):
        lv = {"id": "L1", "lawId": "LF", "versionKey": "L1", "officialName": "x",
              "effectiveDate": "2020-01-01", "endDate": "", "validityStatus": "upcoming"}
        ok, supports, reasons = core.gate_law_version(lv, self._review(lv), True, self.AS_OF)
        self.assertFalse(supports)
        self.assertFalse(ok)  # 效力标错，需复核

    def test_repealed_never_supports(self):
        lv = {"id": "L1", "lawId": "LF", "versionKey": "L1", "officialName": "x",
              "effectiveDate": "2000-01-01", "endDate": "2020-01-01", "validityStatus": "repealed"}
        ok, supports, reasons = core.gate_law_version(lv, self._review(lv), True, self.AS_OF)
        self.assertFalse(supports)

    def test_unknown_never_supports(self):
        lv = {"id": "L1", "lawId": "LF", "versionKey": "L1", "officialName": "x",
              "effectiveDate": "2020-01-01", "endDate": "", "validityStatus": "unknown"}
        ok, supports, reasons = core.gate_law_version(lv, self._review(lv), True, self.AS_OF)
        self.assertFalse(supports)


class JurisdictionAndBindingTest(unittest.TestCase):
    def test_national_normalized(self):
        self.assertEqual(core._region("全国"), "CN")
        self.assertEqual(core._region("CN"), "CN")

    def test_national_vs_region_no_conflict(self):
        self.assertFalse(core.jurisdiction_conflicts("全国", "CN-32"))
        self.assertFalse(core.jurisdiction_conflicts("CN", "CN-3201"))

    def test_region_conflict_detected(self):
        self.assertTrue(core.jurisdiction_conflicts("CN-32", "CN-3201"))

    def test_stale_review_not_bound(self):
        ent = {"id": "X", "a": 1}
        good = {"decision": "verified", "reviewedContentHash": content_hash(ent),
                "evidenceRefs": ["E"]}
        bad = {"decision": "verified", "reviewedContentHash": "0" * 64,
               "evidenceRefs": ["E"]}
        self.assertTrue(core._review_binding(ent, good, True)[0])
        ok, reasons = core._review_binding(ent, bad, True)
        self.assertFalse(ok)
        self.assertTrue(any("STALE" in r for r in reasons))

    def test_missing_evidence_blocked_for_law(self):
        law = {"id": "LF", "canonicalName": "x", "issuer": "y", "jurisdictionCode": "CN"}
        rev = {"decision": "verified", "reviewedContentHash": content_hash(law),
               "evidenceRefs": []}
        ok, reasons = core.gate_law(law, rev)
        self.assertFalse(ok)
        self.assertTrue(any("EVIDENCE" in r for r in reasons))


if __name__ == "__main__":
    unittest.main()
