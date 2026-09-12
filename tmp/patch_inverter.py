# -*- coding: utf-8 -*-
"""重写 auto_invert 为模态词感知版本。"""
import io
p = "tools/v4/generate_hazards_from_clauses.py"
s = io.open(p, encoding="utf-8").read()

old_start = s.index("def auto_invert(")
old_end = s.index("TITLE_OVERRIDES = {")
new_fn = '''COMPOUNDS = ("适应", "应急", "应该", "供应", "相应", "反应", "答应", "应允", "应聘",
             "应酬", "应运", "应声", "应名", "应分", "应敌", "应诊", "应约", "应景", "应诉")
LIST_PREFIX = re.compile(r"^(（?[一二三四五六七八九十]{1,3}）?|（?\d{1,3}）?|[a-h]\))\s*")
MODAL_RE = re.compile(r"应当|应|不得|不应|严禁|必须")

def is_modal_at(s, i):
    """判断 s[i] 的“应”是否为义务词（排除适应/应急等复合词）。"""
    if s[i:i+2] in COMPOUNDS or s[i-1:i+1] in COMPOUNDS:
        return False
    return True

def invert_sentence(s):
    """把一句义务句反转；返回 (title, measures) 或 None。"""
    if "应当" in s:
        title = s.replace("应当", "未", 1)
    elif "不应" in s:
        title = s.replace("不应", "", 1)
    elif "不得" in s:
        title = s.replace("不得", "", 1)
    elif "严禁" in s:
        title = "存在违反'" + s.replace("严禁", "", 1).strip("。 ") + "'的行为"
    elif "必须" in s:
        title = s.replace("必须", "未", 1)
    else:
        m = None
        for mm in MODAL_RE.finditer(s):
            if mm.group(0) == "应" and is_modal_at(s, mm.start()):
                m = mm; break
            if mm.group(0) != "应":
                m = mm; break
        if not m:
            return None
        title = s[:m.start()] + ("未" if m.group(0) == "应" else "未" + s[m.start()+len(m.group(0)):]) + s[m.end():]
        if m.group(0) != "应":
            title = s[:m.start()] + "未" + s[m.end():]
    title = clean_title(title)
    return (title, s) if title else None

def auto_invert(locator, quote):
    """把条款拆成原子义务句并反转。返回 [(sentence, title, measures)]。"""
    results = []
    sentences = [x.strip() for x in SPLIT_RE.split(quote) if x.strip()]
    merged = []
    for s in sentences:
        if merged and (s[0].isascii() and (s[0].islower() or s[0].isdigit() or s[0] in "ab)")):
            merged[-1] += s
        else:
            merged.append(s)
    for s in merged:
        if s.startswith("注") or "见 GB" in s[:8] or "见GB" in s[:8]:
            continue
        s2 = LIST_PREFIX.sub("", s).strip()
        if len(s2) < 8:
            continue
        r = invert_sentence(s2)
        if r:
            results.append((r[1], r[0], r[1]))
    return results

'''
s = s[:old_start] + new_fn + s[old_end:]
# clean_title 保留原实现（已含前缀剥离）；需把 PREFIX 引用与正则确认
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("inverter rewritten")
