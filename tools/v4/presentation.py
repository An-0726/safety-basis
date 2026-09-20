"""公开前台展示投影。

这些函数只负责把正式源字段投影成查询和界面使用的展示字段，不改变任何
knowledge 语义，也不对法规效力、强制属性或隐患分类作新的判断。
"""

import re
import unicodedata
from collections import defaultdict


CATEGORY_ALIASES = {
    "用电安全": "电气安全",
    "机械设备安全": "机械与设备安全",
    "安全教育": "安全教育培训",
    "安全生产管理": "安全管理",
    "专项安全与EHS": "综合安全",
}

# 仅用于公开前台的稳定编号展示投影。原始 ``category`` 字段、标题、场所、
# 条件、法规依据及关联关系均保持不变；未列入此表的编号不得因标题相似而
# 自动扩展覆盖范围。
STABLE_ID_CATEGORY_OVERRIDES = {
    "H_06280C62983C4FB2837C0CF2BC": "机械与设备安全",
    "H_612249886BDA48F69E025B509C": "机械与设备安全",
    "H_92653C5782964483B3D154937D": "机械与设备安全",
    "H_F8BD176AF46643EA9E3CC56A6F": "机械与设备安全",
    "H_GBT47236_4_2_2_6": "机械与设备安全",
    "H_07F925FDEFE56C60596FE131": "特种设备",
    "H_5D5ACB4A6D45FD9CEFC4654D": "特种设备",
    "H_5F45555A73771FE1F12AB88F": "特种设备",
    "H_D498594F88F040A2A583731E6F": "特种设备",
    "H_E37EF6102AE03060EDCB51D7": "特种设备",
    "H_F7BCC89D53AC460CB928258D91": "特种设备",
    "H_SZLD_148_3": "特种设备",
    "H_902B8261A176496C9DCA662834": "特种设备",
    "H_135CEF1FEDFF160F80424A5DCB_1": "消防安全",
    "H_32B64EF4F22A7AAC5B023DFCB5_1": "消防安全",
    "H_3BD1ECF362913A2E15E2314DED_1": "消防安全",
    "H_421CE6E205C8069977EB63572A_1": "消防安全",
    "H_68B4D4FA3376550BFD0C19FAC7_1": "消防安全",
    "H_99C14C8150B1AF834ADC8E5121_1": "消防安全",
    "H_99C14C8150B1AF834ADC8E5121_4": "消防安全",
    "H_9BCA80F06AB60F6A4FBF137A87_2": "消防安全",
    "H_B1F6637B204CE085C41B429B3D_1": "消防安全",
    "H_B883CCBBDC5DAECE911760C23D_3": "消防安全",
    "H_3B20B1FE3A9647A9A1AE26FC87": "危险废物与环境安全",
    "H_72C3801D44894633B32B67FD4E": "危险废物与环境安全",
    "H_9284B9BA196043B59022AF0FB7": "危险废物与环境安全",
    "H_D3EB901F4EC14131AEB880C102": "危险废物与环境安全",
    "H_F53C97BEFD7761225C2B413A": "危险废物与环境安全",
    "H_YJF_6_6_1": "危险废物与环境安全",
    "H_YJF_6_9_1": "危险废物与环境安全",
    "H_539E0915B38B64780FF185BE28_3": "职业卫生",
    "H_A915F52BFFC99371A8A67FC150_3": "职业卫生",
    "H_ZJWS_12_1": "职业卫生",
    "H_93650E0ABBD6D466BCB86E8073_2": "职业卫生",
    "H_GBZ188_16_7": "职业卫生",
    "H_462D38828DEBA46C8E23C177D2_3": "应急与事故管理",
    "H_86641EBB2649A7349D99D07AD9_3": "应急与事故管理",
    "H_D105E5E2683449C027B23E4B28_2": "应急与事故管理",
    "H_D105E5E2683449C027B23E4B28_3": "应急与事故管理",
    "H_YJYA_27_1": "应急与事故管理",
    "H078": "安全教育培训",
    "H_F022B667E1108FB90D68C36D19_1": "安全教育培训",
    "H_3227246FFEDB65997424055F": "安全教育培训",
    "H_9F790C9B0EA34E59207BCCC1AD_2": "安全教育培训",
    "H_9F790C9B0EA34E59207BCCC1AD_3": "安全教育培训",
    "H_AQPX_9_1": "安全教育培训",
    "H_D7F4B2B8F70D67B625BE3E5E95_2": "安全教育培训",
    "H_JS140_十七_1": "安全教育培训",
    "H_133DEA3AE07CE30E3CA5CBF4FF_1": "安全管理",
    "H_38586C4D52EB7979AC2D73A14A_1": "安全管理",
    "H_4306C3DA6C19836BDC0CC5A9E7_1": "安全管理",
    "H_5CD35729CF4B26FFA9F9489176_1": "安全管理",
    "H_71323E2862E5D3955E3DE6DE76_1": "安全管理",
    "H_71323E2862E5D3955E3DE6DE76_2": "安全管理",
    "H_96049FDA8623F7EF0CDA4B1F73_1": "安全管理",
    "H_97123DF324DB6A7FB1B4DAB9F1_2": "安全管理",
    "H_B1BBC7FA21B8DE36E1AB2CD21F_1": "安全管理",
    "H_D9B99E085E45534257B178AC2D_2": "安全管理",
    "H_JS140_七_1": "安全管理",
    "H_JS140_十二_2": "安全管理",
    "H_FCB_7_2": "粉尘防爆",
    "H_CF_MAJOR_06": "燃气安全",
    "H_GBT47236_4_2_11_1_1": "燃气安全",
    "H_GBT47236_4_2_5_2_1": "电气安全",
    "H_GBT47236_6_3_3_1": "安全标志",
}

DISPLAY_LEVEL_MAP = {
    "法律": "法律",
    "行政法规": "行政法规",
    "地方法规": "地方性法规",
    "部门规章": "部门规章",
    "部门规章（部令）": "部门规章",
    "地方政府规章": "地方政府规章",
    "国家标准": "国家标准",
    "强制性国家标准": "国家标准",
    "强制性国家职业卫生标准": "国家标准",
    "工程建设国家标准": "国家标准",
    "推荐性国家标准": "国家标准",
    "行业标准": "行业标准",
    "环境保护行业标准": "行业标准",
    "地方标准": "地方标准",
    "特种设备安全技术规范": "安全技术规范",
}

ENVIRONMENT_LEVEL_OVERRIDES = {
    "LV_YJFGZ": "行业标准",
}

SCENE_RULES = (
    ("消防与疏散", ("消防", "疏散")),
    ("电气与配电", ("电气", "用电", "配电", "电焊", "受电", "控制柜")),
    ("特种设备", ("特种设备", "电梯", "锅炉", "压力容器", "气瓶", "场车", "叉车", "起重", "行车", "吊车", "索道", "游乐设施", "储气罐", "电动葫芦")),
    ("机械加工", ("机械", "机加工", "冲压", "剪切", "砂轮", "五金", "模具", "机加清洗")),
    ("粉尘与除尘", ("粉尘", "除尘")),
    ("化学品管理", ("化学品", "危化品", "危险物品", "油料", "润滑加油")),
    ("危废与污染治理", ("危险废物", "废气", "污水处理")),
    ("燃气使用", ("燃气", "可燃气体燃烧")),
    ("有限空间", ("有限空间",)),
    ("动火与焊割", ("动火", "焊接", "气焊", "二保焊", "焊割", "切割", "热切割")),
    ("高处作业", ("高处", "坠落")),
    ("涂装作业", ("涂装", "喷漆", "喷粉", "调漆", "喷涂")),
    ("仓储与物流", ("仓储", "仓库", "库房", "库区", "原料库", "成品库", "物料仓", "物流", "装卸", "货台")),
    ("职业健康与防护", ("职业病", "个体防护")),
    ("应急管理", ("应急", "事故报告", "事故处置")),
    ("培训与资格", ("培训", "考核", "资格", "特种作业人员")),
    ("建筑与厂区", ("建筑", "总平面", "厂区", "厂房", "宿舍", "建设项目")),
    ("实验与化验", ("实验室", "化验室", "科研")),
    ("标志与警示", ("标志", "警示", "标识", "管线识别")),
    ("生产现场", ("车间", "工位", "流水线", "台位", "操作区域")),
)
SCENE_TAGS = tuple(tag for tag, _fragments in SCENE_RULES)
SCENE_TAG_OPTIONS = SCENE_TAGS + ("未细分场景",)

DISPLAY_MODE_MAP = {
    "direct": "直接适用",
    "conditional": "有条件适用",
}

DISPLAY_ROLE_MAP = {
    "direct": "直接依据",
    "supporting": "辅助依据",
}

NOTE_DATE_PREFIX = "2026-09-11 "
APPROVED_MAINTENANCE_SENTENCES = (
    "修订：原 description 与 title 完全相同，已补写为含情境的完整描述。",
    "修订：原 description 与 title 完全相同，已补写为完整描述。",
    "修订：原整改措施为现状描述或空话，已改写为可执行的整改动作。",
    "修订：原整改措施为现状描述或空话（“已设置…”“符合要求”等），已改写为可执行的整改动作。",
    "修订：原整改措施为空话或模板（“符合规定”“针对上述隐患制定整改措施并落实”等），已改写为针对本隐患的可执行措施。",
    "修订：原 measures 字段直接照抄隐患描述（V3 迁移遗留），已改写为针对该隐患的可执行整改措施；标题、描述与法律依据未改动。",
    "精简：原标题为法条式长句，已压缩为一句缺陷表述；法律依据与整改措施未改动。",
    "精简：原标题为法条式长句（含条款列举），已压缩为一句缺陷表述；法律依据与整改措施未改动。",
    "通用化：原表述含企业现场细节（具体编号/楼层/方位/数量词），已抽象为通用隐患表述，法律依据与整改措施未改动。",
    "修订：原标题为条款原文片段或存在文字损坏，语义不通且无法作为现场隐患表述；此处依其原描述与现有依据改写为可判定的现场事实，未改变依据本身。",
    "修订：原整改措施已改写为可执行动作。",
)
APPROVED_MAINTENANCE_TEXTS = tuple(
    sorted((NOTE_DATE_PREFIX + sentence for sentence in APPROVED_MAINTENANCE_SENTENCES),
           key=len, reverse=True)
)
_MAINTENANCE_RE = re.compile("|".join(re.escape(text) for text in APPROVED_MAINTENANCE_TEXTS))
_PUNCT = re.compile(r"[，。；：、（）()【】\[\]《》“”‘’'\"·•…—–_-]+")


def display_category(value, hazard_id=""):
    """Return a controlled UI alias while preserving unknown source values."""
    if hazard_id in STABLE_ID_CATEGORY_OVERRIDES:
        return STABLE_ID_CATEGORY_OVERRIDES[hazard_id]
    return CATEGORY_ALIASES.get(value or "", value or "")


def display_level(raw_level, version_id=""):
    """Map only the approved level dictionary and the approved stable-ID exception."""
    if version_id in ENVIRONMENT_LEVEL_OVERRIDES:
        return ENVIRONMENT_LEVEL_OVERRIDES[version_id]
    return DISPLAY_LEVEL_MAP.get(raw_level or "", raw_level or "")


def searchable(parts):
    """Return the deterministic normalized search text shared by build and verify."""
    value = " ".join(str(part) for part in parts if part)
    value = unicodedata.normalize("NFKC", value).lower()
    value = _PUNCT.sub(" ", value)
    return re.sub(r"\s+", " ", value).strip()


def project_note(note):
    """Split only the approved complete maintenance sentences, losslessly.

    The source note is never rewritten.  Offsets use Python string positions so
    every segment can be checked against the exact original text.
    """
    if note is None:
        return {"noteSegments": [], "businessNote": "", "maintenanceNote": ""}
    if not isinstance(note, str):
        raise TypeError("note 必须是字符串、null 或缺失")

    segments = []
    maintenance = []
    cursor = 0
    for match in _MAINTENANCE_RE.finditer(note):
        if match.start() > cursor:
            segments.append({"kind": "business", "text": note[cursor:match.start()],
                             "start": cursor, "end": match.start()})
        text = match.group(0)
        segments.append({"kind": "maintenance", "text": text,
                         "start": match.start(), "end": match.end()})
        maintenance.append(text)
        cursor = match.end()
    if cursor < len(note):
        segments.append({"kind": "business", "text": note[cursor:],
                         "start": cursor, "end": len(note)})

    return {
        "noteSegments": segments,
        "businessNote": "".join(segment["text"] for segment in segments
                                  if segment["kind"] == "business"),
        "maintenanceNote": "\n".join(maintenance),
    }


def raw_law_level(law, law_version, publication=None):
    """Match the builder's source precedence for the retained raw ``level`` field."""
    publication = publication or {}
    return (law.get("documentKind") or law_version.get("level") or
            publication.get("level", ""))


def scene_tags(places):
    """Project original places to the ordered union of explicitly approved tags."""
    texts = [place for place in (places or []) if isinstance(place, str)]
    return [tag for tag, fragments in SCENE_RULES
            if any(fragment in text for text in texts for fragment in fragments)]


def project_hazard(hazard, hazard_id=""):
    return {
        "displayCategory": display_category(hazard.get("category", ""), hazard_id),
        "sceneTags": scene_tags(hazard.get("places") or []),
        **project_note(hazard.get("note")),
    }


def project_law_level(raw_level, version_id=""):
    return {"displayLevel": display_level(raw_level, version_id)}


def presentation_review(hazards, level_records, modes=None, roles=None):
    """Build an external audit directory for the deterministic projection.

    ``level_records`` maps a stable law-version ID to ``(raw_level, display_level)``.
    The report is intentionally external to the public package so it does not become
    an additional runtime data source.
    """
    place_to_tags = {}
    for hazard in hazards.values():
        for place in hazard.get("places") or []:
            if isinstance(place, str):
                place_to_tags[place] = scene_tags([place])

    mapped = {place: tags for place, tags in place_to_tags.items() if tags}
    unmapped = sorted(place for place, tags in place_to_tags.items() if not tags)
    unknown_levels = defaultdict(list)
    for version_id, (raw, shown) in level_records.items():
        if raw not in DISPLAY_LEVEL_MAP and version_id not in ENVIRONMENT_LEVEL_OVERRIDES:
            unknown_levels[raw].append(version_id)

    mode_values = sorted(set(modes or []))
    role_values = sorted(set(roles or []))
    unknown_modes = [value for value in mode_values if value not in DISPLAY_MODE_MAP]
    unknown_roles = [value for value in role_values if value not in DISPLAY_ROLE_MAP]
    review_prompts = []
    if unknown_levels:
        review_prompts.append("以下依据类型未纳入批准映射，已保留原值，请架构师审查：" +
                              "、".join(sorted(unknown_levels)))
    if unknown_modes:
        review_prompts.append("以下适用方式枚举未纳入中文标签映射，已保留原值，请审查：" +
                              "、".join(unknown_modes))
    if unknown_roles:
        review_prompts.append("以下依据角色枚举未纳入中文标签映射，已保留原值，请审查：" +
                              "、".join(unknown_roles))

    return {
        "categoryAliases": dict(CATEGORY_ALIASES),
        "stableCategoryOverrides": dict(STABLE_ID_CATEGORY_OVERRIDES),
        "stableCategoryOverrideCount": len(STABLE_ID_CATEGORY_OVERRIDES),
        "displayLevelMap": dict(DISPLAY_LEVEL_MAP),
        "stableIdOverrides": dict(ENVIRONMENT_LEVEL_OVERRIDES),
        "sceneRules": [
            {"tag": tag, "contains": list(fragments)}
            for tag, fragments in SCENE_RULES
        ],
        "sceneCoverage": {
            "sourcePlaceValues": len(place_to_tags),
            "mappedPlaceValues": len(mapped),
            "unmappedPlaceValues": len(unmapped),
            "mapped": mapped,
            "unmapped": unmapped,
        },
        "unknownLawLevels": {
            raw: sorted(ids) for raw, ids in sorted(unknown_levels.items())
        },
        "unknownModes": unknown_modes,
        "unknownRoles": unknown_roles,
        "reviewPrompts": review_prompts,
    }
