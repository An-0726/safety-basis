"""Deterministic checks for public hazard wording.

These checks intentionally target high-confidence structural damage. They do
not attempt to decide whether a hazard is legally correct; that remains part of
the evidence-backed review workflow.
"""
from __future__ import annotations

import re


_BROKEN_PHRASES = {
    "相,未": "疑似机器转译破坏了‘相应’",
    "相，未": "疑似机器转译破坏了‘相应’",
    "相未": "疑似机器转译破坏了‘相应’",
    "未急预案": "疑似机器转译破坏了‘应急预案’",
    "有,未": "疑似机器转译插入错误否定词",
    "有，未": "疑似机器转译插入错误否定词",
    "都,未": "疑似机器转译插入错误否定词",
    "都，未": "疑似机器转译插入错误否定词",
    "未无": "存在互相冲突的连续否定词",
    "不,未": "存在互相冲突的连续否定词",
    "不，未": "存在互相冲突的连续否定词",
}

_RISK_MARKERS = (
    "未", "无", "缺少", "缺失", "不足", "不到位", "不具备", "不符合", "不规范",
    "违规", "失效", "破损", "泄漏", "超限", "混放", "乱接",
    "仍继续", "滞后", "错误", "脱落", "失灵", "不合格",
)

_OBLIGATION_MARKERS = (
    "应当", "必须", "不得", "严禁", "不允许", "按照", "符合",
    "具备", "配备", "设置", "保持", "定期", "及时",
)


def normalized_title(value: str) -> str:
    return re.sub(r"\s+", "", value).strip("。；;，,")


def text_errors(title: str) -> list[str]:
    """Return high-confidence publication blockers for one hazard title."""
    value = title.strip()
    errors: list[str] = []
    if not value:
        return ["隐患标题为空"]
    if "\ufffd" in value:
        errors.append("隐患标题含损坏的 Unicode 替换字符")
    if re.match(r"^[、，,；;。.．]", value):
        errors.append("隐患标题以前导标点开头")
    if re.match(r"^[1-9](?=(?:低压|高压|电气|配电|照明|安全|消防|危险|压力|生产|作业))", value):
        errors.append("隐患标题残留孤立的列表序号")
    if re.search(r"[,，]{2,}|[。；;]{2,}", value):
        errors.append("隐患标题含重复标点")
    for phrase, reason in _BROKEN_PHRASES.items():
        if phrase in value:
            errors.append(reason + f"：{phrase}")
    if re.fullmatch(r"《[^》]+》\s*第?[0-9一二三四五六七八九十百千万.．]+条?", value):
        errors.append("隐患标题只有法规或条款引用，没有隐患描述")
    if len(value) > 180:
        errors.append("隐患标题超过 180 字，疑似直接复制法规原文或检查表整行")
    if (not any(marker in value for marker in _RISK_MARKERS)
            and any(marker in value for marker in _OBLIGATION_MARKERS)):
        errors.append("隐患标题呈现为正向义务或符合项，缺少不符合状态")
    return list(dict.fromkeys(errors))
