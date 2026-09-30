"""Source-grounded UI clue tests; never change applicability or knowledge."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('scene_clue_presentation', ROOT / 'tools/v4/presentation.py')
presentation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(presentation)


class SceneClueTests(unittest.TestCase):
    def test_reviewed_singleton_category_aliases_keep_exact_source_and_basis(self):
        cases = {
            'H_FORKLIFT_UNATTENDED_KEY': ('特种设备安全', '特种设备', 'C_GBT36507_2023_4_8_1'),
            'H_WORKPLACE_CHEM_SDS_MISSING': ('危险化学品安全', '危险化学品与危险物质', 'C_HAZCHEM_LAW_51'),
            'H_CF_GEN_18': ('设备设施安全', '设备设施', 'C_GBT34525_2017_7_1_6'),
        }
        links = [json.loads(path.read_text()) for path in (ROOT / 'knowledge/links').glob('*.json')]
        for record_id, (raw, display, clause_id) in cases.items():
            with self.subTest(record_id=record_id):
                source = json.loads((ROOT / 'knowledge/hazards' / f'{record_id}.json').read_text())
                before = copy.deepcopy(source)
                self.assertEqual(source['category'], raw)
                self.assertEqual(presentation.project_hazard(source, record_id)['displayCategory'], display)
                self.assertEqual(source, before)
                self.assertTrue(any(link['hazardId'] == record_id and link['clauseId'] == clause_id
                                    and link['lifecycle'] == 'active' for link in links))

    def test_mixed_or_distinct_professional_categories_are_not_collapsed(self):
        cases = {
            'H_PDDB_14_1': '重大事故隐患判定',
            'H_12158_8_8_5_3': '安全防护',
            'H_CF_GEN_15': '危险化学品与危险废物',
        }
        for record_id, expected in cases.items():
            source = json.loads((ROOT / 'knowledge/hazards' / f'{record_id}.json').read_text())
            self.assertEqual(source['category'], expected)
            self.assertEqual(presentation.project_hazard(source, record_id)['displayCategory'], expected)
        # The new name aliases must not displace an already reviewed stable-ID override.
        source = json.loads((ROOT / 'knowledge/hazards/H_06280C62983C4FB2837C0CF2BC.json').read_text())
        self.assertEqual(presentation.project_hazard(source, source['id'])['displayCategory'], '机械与设备安全')

    def test_actual_equipment_and_place_records(self):
        cases = {
            'H_ELECTRICAL_ROOM_SMALL_ANIMAL_PROTECTION': ['配电室与配电装置'],
            'H_FORKLIFT_UNATTENDED_KEY': ['叉车与场车', '仓储与物流'],
            'H065': ['气瓶', '危化品储存场所', '仓储与物流'],
            'H066': ['通道与出口'],
            'H078': ['危废贮存场所'],
            'H_EXIT_SIGN_LAMP_FAULT': ['通道与出口'],
        }
        for record_id, expected in cases.items():
            with self.subTest(record_id=record_id):
                source = json.loads((ROOT / 'knowledge/hazards' / f'{record_id}.json').read_text())
                before = copy.deepcopy(source)
                self.assertEqual(presentation.project_hazard(source, record_id)['sceneTags'], expected)
                self.assertEqual(source, before)

    def test_generic_professional_obligation_is_not_a_place(self):
        values = [
            '依法承担消防安全责任的建筑、场所或单位',
            '电气设备安装、运行、检维修及用电相关场所',
            '生产经营单位从业人员培训、考核和资格管理活动',
            '存在职业病危害因素的用人单位及相关作业场所',
            '生产经营单位及应急准备、事故报告和应急处置相关活动',
            '存在安全标志、警示标识或管线识别要求的场所和设备',
            '特种设备使用、运行、维护检修或相关管理场景',
        ]
        self.assertEqual(presentation.scene_tags(values), [])

    def test_no_title_keyword_or_condition_inference(self):
        source = {'title': '电梯高处作业培训', 'category': '特种设备',
                  'keywords': ['配电房', '灭火器'], 'conditions': '仓库、焊接、气瓶',
                  'description': '消防控制室', 'places': ['通用场所']}
        self.assertEqual(presentation.project_hazard(source)['sceneTags'], [])

    def test_bicycle_is_not_crane_and_cold_cutting_is_not_hot_work(self):
        self.assertEqual(presentation.scene_tags(['电动自行车停放充电场所']), ['电动自行车充电'])
        self.assertEqual(presentation.scene_tags(['切割作业区']), [])
        self.assertEqual(presentation.scene_tags(['行车作业工位']), ['起重设备', '生产现场'])
        self.assertEqual(presentation.scene_tags(['焊接切割作业点']), ['动火与焊割'])

    def test_existing_reviewed_category_stays_separate_from_scene(self):
        source = json.loads((ROOT / 'knowledge/hazards/H078.json').read_text())
        projected = presentation.project_hazard(source, 'H078')
        self.assertEqual(projected['displayCategory'], '安全教育培训')
        self.assertEqual(projected['sceneTags'], ['危废贮存场所'])
        self.assertNotIn('安全教育培训', presentation.SCENE_TAGS)

    def test_tags_are_unique_and_serialized_unclassified_sentinel_is_retained(self):
        self.assertEqual(len(presentation.SCENE_TAGS), len(set(presentation.SCENE_TAGS)))
        self.assertEqual(presentation.SCENE_TAG_OPTIONS[-1], '未细分场景')
        self.assertEqual(presentation.scene_tags([None, '通用场所', '']), [])
