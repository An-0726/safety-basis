import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hazard_quality


class HazardQualityTests(unittest.TestCase):
    def test_known_machine_translation_damage_is_blocked(self):
        cases = (
            "、暂存区域,未设置安全警示标志",
            "配备相,未品种和数量的消防器材",
            "企业编制有安全生产事故未急预案",
            "灭火器筒体,未无明显缺陷和机械损伤",
            "3低压断路器未安装在电源侧",
            "场内车辆有下列情形,,未判定为重大事故隐患",
        )
        for title in cases:
            with self.subTest(title=title):
                self.assertTrue(hazard_quality.text_errors(title))

    def test_positive_obligation_and_citation_only_are_blocked(self):
        self.assertTrue(hazard_quality.text_errors("按照国家标准配置消防设施、器材"))
        self.assertTrue(hazard_quality.text_errors("《科研建筑设计标准》第5.2.1条"))

    def test_normal_hazard_wording_passes(self):
        cases = (
            "安全设备维护保养检测或记录不到位",
            "危险废物未按要求设置贮存设施或贮存场所",
            "电源线路私拉乱接",
            "不具备法定安全生产条件仍从事生产经营活动",
            "火灾报警按钮被遮挡且无明显标志",
            "灭火器压力指针未在绿色范围内",
        )
        for title in cases:
            with self.subTest(title=title):
                self.assertEqual(hazard_quality.text_errors(title), [])


if __name__ == "__main__":
    unittest.main()
