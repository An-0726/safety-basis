import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[3]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


builder = load_module("build_unified_release_conditions", ROOT / "tools" / "v4" / "build_unified_release.py")
verifier = load_module("verify_unified_bundle_conditions", ROOT / "tools" / "v4" / "verify_unified_bundle.py")
presentation = sys.modules["presentation"]


class UnifiedReleaseConditionsTests(unittest.TestCase):
    def test_builder_preserves_text_and_normalizes_missing_or_null(self):
        source_text = "仅在 <特定> 场景 & 设备\n第二行条件"
        self.assertEqual(builder.normalized_conditions("H_TEXT", {"conditions": source_text}), source_text)
        self.assertEqual(builder.normalized_conditions("H_MISSING", {}), "")
        self.assertEqual(builder.normalized_conditions("H_NULL", {"conditions": None}), "")

    def test_builder_rejects_non_string_source_conditions(self):
        with self.assertRaisesRegex(SystemExit, "conditions 必须是字符串"):
            builder.normalized_conditions("H_BAD", {"conditions": ["不能擅自 stringify"]})

    def test_bundle_verifier_rejects_source_condition_difference(self):
        failures = verifier.Failures()
        verifier.check_hazard_conditions(
            failures,
            "H_TEXT",
            {"conditions": "bundle text"},
            {"conditions": "source text"},
        )
        self.assertTrue(any("conditions 与源字段不一致" in message for message in failures))

    def test_bundle_verifier_normalizes_null_source_to_empty_string(self):
        failures = verifier.Failures()
        verifier.check_hazard_conditions(
            failures,
            "H_NULL",
            {"conditions": ""},
            {"conditions": None},
        )
        self.assertEqual(failures, [])

    def test_bundle_verifier_requires_string_in_generated_record(self):
        failures = verifier.Failures()
        verifier.check_hazard_conditions(
            failures,
            "H_BAD",
            {"conditions": None},
            {"conditions": "source text"},
        )
        self.assertTrue(any("公开隐患 conditions 必须是字符串" in message for message in failures))

    def test_controlled_category_and_level_projection(self):
        self.assertEqual(presentation.display_category("用电安全"), "电气安全")
        self.assertEqual(presentation.display_category("专项安全与EHS"), "综合安全")
        self.assertEqual(presentation.display_category("未批准的新主题"), "未批准的新主题")
        self.assertEqual(presentation.display_level("部门规章（部令）"), "部门规章")
        self.assertEqual(presentation.display_level("环境保护标准", "LV_YJFGZ"), "行业标准")
        self.assertEqual(presentation.display_level("未知依据类型", "LV_UNKNOWN"), "未知依据类型")

    def test_stable_id_category_projection_is_exact_and_raw_category_is_preserved(self):
        self.assertEqual(len(presentation.STABLE_ID_CATEGORY_OVERRIDES), 65)
        source_dir = ROOT / "knowledge" / "hazards"
        for hazard_id, target in presentation.STABLE_ID_CATEGORY_OVERRIDES.items():
            source = json.loads((source_dir / (hazard_id + ".json")).read_text(encoding="utf-8"))
            projected = presentation.project_hazard(source, hazard_id=hazard_id)
            self.assertEqual(projected["displayCategory"], target, hazard_id)
            self.assertIn("category", source)
            self.assertEqual(
                presentation.project_hazard(source, hazard_id="H_NOT_IN_OVERRIDE")["displayCategory"],
                presentation.display_category(source.get("category", "")),
                hazard_id,
            )
        self.assertNotIn("H_47B0A90180C24A42AFA38767B9", presentation.STABLE_ID_CATEGORY_OVERRIDES)
        self.assertEqual(
            presentation.display_category("设备设施", "H_47B0A90180C24A42AFA38767B9"),
            "设备设施",
        )
        self.assertEqual(
            presentation.display_category("机械设备安全", "H_NOT_IN_OVERRIDE"),
            "机械与设备安全",
        )

    def test_scene_projection_is_union_and_empty_is_unclassified(self):
        tags = presentation.scene_tags([
            "车间电气控制柜旁的消防疏散通道",
            "机械加工工位及仓库装卸货台",
        ])
        self.assertEqual(tags, [
            "消防与疏散", "电气与配电", "机械加工", "仓储与物流", "生产现场",
        ])
        self.assertEqual(presentation.scene_tags(["通用场所"]), [])

    def test_presentation_review_reports_unmapped_and_unknown_values(self):
        review = presentation.presentation_review(
            {"H1": {"places": ["通用场所", "配电室"]}},
            {"LV1": ("未知依据类型", "未知依据类型")},
            modes=["direct", "new-mode"],
            roles=["direct", "new-role"],
        )
        self.assertEqual(review["sceneCoverage"]["unmapped"], ["通用场所"])
        self.assertEqual(review["unknownLawLevels"], {"未知依据类型": ["LV1"]})
        self.assertEqual(review["unknownModes"], ["new-mode"])
        self.assertEqual(review["unknownRoles"], ["new-role"])
        self.assertEqual(review["stableCategoryOverrideCount"], 65)

    def test_bundle_verifier_recomputes_and_rejects_presentation_tamper(self):
        failures = verifier.Failures()
        source = {"category": "用电安全", "places": ["配电室"]}
        expected = presentation.project_hazard(source)
        verifier.check_hazard_presentation(
            failures,
            "H_TAMPER",
            {**expected, "displayCategory": "篡改主题"},
            expected,
            source,
        )
        self.assertTrue(any("展示投影被改动" in message for message in failures))

    def test_bundle_verifier_recomputes_stable_id_category_override(self):
        failures = verifier.Failures()
        source = {"category": "设备设施", "places": ["机械加工区"]}
        expected = presentation.project_hazard(source, hazard_id="H_06280C62983C4FB2837C0CF2BC")
        verifier.check_hazard_presentation(
            failures,
            "H_06280C62983C4FB2837C0CF2BC",
            {**expected, "displayCategory": "设备设施"},
            expected,
            source,
        )
        self.assertTrue(any("展示投影被改动" in message for message in failures))

    def test_note_projection_preserves_exact_segments_and_separates_approved_maintenance(self):
        first = presentation.NOTE_DATE_PREFIX + presentation.APPROVED_MAINTENANCE_SENTENCES[0]
        second = presentation.NOTE_DATE_PREFIX + presentation.APPROVED_MAINTENANCE_SENTENCES[5]
        source_note = "业务 <说明> & 保留" + first + second + "尾部业务"
        projected = presentation.project_note(source_note)

        self.assertEqual("".join(segment["text"] for segment in projected["noteSegments"]), source_note)
        self.assertEqual([segment["kind"] for segment in projected["noteSegments"]],
                         ["business", "maintenance", "maintenance", "business"])
        self.assertEqual(projected["businessNote"], "业务 <说明> & 保留尾部业务")
        self.assertEqual(projected["maintenanceNote"], first + "\n" + second)

    def test_note_projection_covers_empty_missing_near_match_and_html_business_text(self):
        self.assertEqual(presentation.project_note(None), {
            "noteSegments": [], "businessNote": "", "maintenanceNote": "",
        })
        self.assertEqual(presentation.project_note(""), {
            "noteSegments": [], "businessNote": "", "maintenanceNote": "",
        })
        business = "普通说明 <b>& 内容"
        self.assertEqual(presentation.project_note(business)["businessNote"], business)
        near = presentation.NOTE_DATE_PREFIX + presentation.APPROVED_MAINTENANCE_SENTENCES[0].rstrip("。")
        near_projection = presentation.project_note(near)
        self.assertEqual(near_projection["maintenanceNote"], "")
        self.assertEqual(near_projection["businessNote"], near)

    def test_new_maintenance_sentences_match_exactly_and_reject_near_match(self):
        exact_one = presentation.NOTE_DATE_PREFIX + presentation.APPROVED_MAINTENANCE_SENTENCES[-2]
        exact_two = presentation.NOTE_DATE_PREFIX + presentation.APPROVED_MAINTENANCE_SENTENCES[-1]
        projected = presentation.project_note("业务前" + exact_one + exact_two + "业务后")
        self.assertEqual(projected["maintenanceNote"], exact_one + "\n" + exact_two)
        self.assertEqual(projected["businessNote"], "业务前业务后")

        near = exact_one[:-1]
        near_projected = presentation.project_note(near)
        self.assertEqual(near_projected["maintenanceNote"], "")
        self.assertEqual(near_projected["businessNote"], near)

    def test_bundle_verifier_rejects_note_segment_tamper(self):
        source = {
            "category": "设备设施",
            "places": ["通用场所"],
            "note": presentation.NOTE_DATE_PREFIX + presentation.APPROVED_MAINTENANCE_SENTENCES[0],
        }
        expected = presentation.project_hazard(source)
        row = {**expected, "noteSegments": [{"kind": "business", "text": "篡改", "start": 0, "end": 2}]}
        search_row = {
            "displayCategory": expected["displayCategory"],
            "sceneTags": expected["sceneTags"],
            "businessNote": expected["businessNote"],
        }
        failures = verifier.Failures()
        verifier.check_hazard_presentation(failures, "H_NOTE_TAMPER", row, search_row, source)
        self.assertTrue(any("备注投影被改动" in message for message in failures))


if __name__ == "__main__":
    unittest.main()
