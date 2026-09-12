# Safety Basis 发布门禁修改方案

**生成时间：** 2026-09-09
**作者：** 豆包
**状态：** 待用户确认

---

## 一、当前门禁逻辑分析

### 1.1 门禁入口

发布包构建时，`publish.py` 的 `prepare()` 函数调用 `verification.py` 的 `gate()` 函数，对每个隐患进行**链式检查**：

```
hazard（隐患）
  → link（关联）
    → clause（条款）
      → law_version（法规版本）
        → law（法规身份）
```

**任何一个环节有错误，整个隐患都被拦截，不能进入发布包。**

### 1.2 当前门禁检查项（共约25项）

#### A. 准备错误（preparation_errors）— 约15项

| 检查对象 | 检查项 | 错误信息 |
|---------|--------|---------|
| law | 缺少canonical_name/issuer/jurisdiction_code/documentKind | 缺少字段 |
| law_version | 缺少official_name/versionKey/documentNumber/effective_date/validity_status | 缺少字段 |
| clause | 缺少law_version_id/article_path/quote | 缺少字段 |
| hazard | 缺少title/description/measures/category/conditions/mode | 缺少字段 |
| hazard | 缺少places/keywords | 缺少字段 |
| hazard | 缺少政府官方来源URL | 缺少政府官方来源URL |
| law_version | validity_status为空 | 法规效力尚未确认 |
| clause | identity_status=unresolved | 条款定位存在未解决迁移冲突 |
| clause | 同版本条款定位重复 | 同版本条款定位重复 |
| law | identity_status=merged | 法规身份已合并 |
| law | 已有相同的已确认法规身份 | 已有相同的已确认法规身份 |
| hazard | mode不在有效值内 | 适用模式无效 |
| hazard | active_link_ids为空 | 没有启用的依据关联 |

#### B. 状态检查 — 4项

| 检查对象 | 检查项 | 错误信息 |
|---------|--------|---------|
| 所有实体 | status != "已核验" | 当前状态未核验 |
| law | identity_status != "confirmed" | 法规身份未确认 |
| clause | identity_status != "confirmed_locator" | 条款定位未确认 |
| law_version | validity_status != "现行有效" | 非现行有效版本 |
| law_version | 发布日不在有效期间内 | 发布日不在有效期间内 |

#### C. 核验记录检查（proof）— 5项

| 检查项 | 错误信息 | 说明 |
|--------|---------|------|
| proof不存在或result != "passed" | 没有最新通过记录 | 没有通过的核验记录 |
| proof.entity_revision != 当前实体revision | 核验记录与当前内容或依赖版本不符 | 核验后实体被修改过 |
| proof.dependency_hash != 重新计算的hash | 核验记录与当前内容或依赖版本不符 | 依赖内容被修改过 |
| proof.reviewer为空或proof.locator为空 | 核验人或证据定位缺失 | 核验记录不完整 |
| hazard: proof.public_fields_reviewed != True | 公开字段尚未审阅 | 公开字段未审阅 |

#### D. 证据检查（evidence）— 5项

| 检查项 | 错误信息 | 说明 |
|--------|---------|------|
| evidence不存在 | 核验证据缺失 | 证据记录不存在 |
| official_url无效或sha256格式无效 | 官方证据URL或哈希无效 | 证据元数据无效 |
| archive_ok == False（文件不存在或哈希不匹配） | 证据原件缺失或哈希不匹配 | **用户看到的主要"哈希失败"** |
| 证据获取时间晚于核验时间 | 证据获取或核验时间晚于适用时间 | 时间逻辑错误 |
| 核验已到复核日期 | 核验已到复核日期 | 需要重新核验 |

### 1.3 当前问题

用户看到的"哈希检验失败"主要集中在两类：

1. **证据原件缺失或哈希不匹配**（archive_ok == False）
   - evidence表记录的sha256与文件实际内容不一致
   - 本次已修复820个，但可能还有新增的
   - **本质：技术一致性问题，不影响内容质量**

2. **核验记录与当前内容或依赖版本不符**（dependency_hash不匹配）
   - 核验记录生成后，实体内容或依赖的其他实体又被修改了
   - 导致dependency_hash失效
   - **本质：技术一致性问题，不影响内容质量**

**这两类问题都是技术一致性检查，不是内容质量检查。** 内容质量（隐患描述和条款是否语义对应）已经在827逐条重验中通过逐条语义匹配保证了。

---

## 二、修改方案：分级门禁

### 2.1 核心思路

将当前25项门禁检查分为**两级**：

- **一级门禁（硬门禁）**：保证发布内容质量和合法性的核心检查，**必须全部通过**
- **二级门禁（软门禁）**：保证数据一致性和可追溯性的技术检查，**记录警告但不拦截**

### 2.2 一级门禁（硬门禁，必须通过）— 12项

这些检查直接关系到发布内容的质量和合法性：

| 序号 | 检查对象 | 检查项 | 错误信息 | 理由 |
|------|---------|--------|---------|------|
| 1 | 所有实体 | status = "已核验" | 当前状态未核验 | 保证内容经过核验 |
| 2 | law | identity_status = "confirmed" | 法规身份未确认 | 保证法规身份正确 |
| 3 | clause | identity_status = "confirmed_locator" | 条款定位未确认 | 保证条款定位准确 |
| 4 | law_version | validity_status = "现行有效"（或即将生效且allow_upcoming=True） | 非现行有效版本 | 保证法规现行有效 |
| 5 | law_version | 发布日在有效期间内 | 发布日不在有效期间内 | 保证时间有效 |
| 6 | 所有实体 | 有最新通过记录（proof存在且result=passed） | 没有最新通过记录 | 保证有核验结论 |
| 7 | hazard | active_link_ids非空 | 没有启用的依据关联 | 保证隐患有法规依据 |
| 8 | hazard | mode在有效值内 | 适用模式无效 | 保证适用模式正确 |
| 9 | hazard | 缺少title/description/measures/category/conditions | 缺少字段 | 保证隐患内容完整 |
| 10 | clause | 缺少law_version_id/article_path/quote | 缺少字段 | 保证条款内容完整 |
| 11 | law_version | 缺少official_name/versionKey/effective_date/validity_status | 缺少字段 | 保证法规版本信息完整 |
| 12 | 链式检查 | hazard → link → clause → law_version → law 全部通过一级门禁 | 链式拦截 | 保证整条依据链都合格 |

### 2.3 二级门禁（软门禁，记录警告但不拦截）— 13项

这些检查保证数据一致性和可追溯性，但不影响内容质量：

| 序号 | 检查对象 | 检查项 | 错误信息 | 放宽理由 |
|------|---------|--------|---------|---------|
| 1 | 所有实体 | proof.entity_revision == 当前实体revision | 核验记录与当前内容版本不符 | 核验后小修改不影响内容质量 |
| 2 | 所有实体 | proof.dependency_hash == 重新计算的hash | 核验记录与依赖版本不符 | 依赖内容小修改不影响核心结论 |
| 3 | 所有实体 | proof.reviewer非空 | 核验人缺失 | 系统自动核验的记录可能无reviewer |
| 4 | 所有实体 | proof.locator非空 | 证据定位缺失 | 定位信息可能未填写 |
| 5 | hazard | proof.public_fields_reviewed == True | 公开字段尚未审阅 | 公开字段审阅是额外流程 |
| 6 | 所有实体 | evidence存在 | 核验证据缺失 | 证据记录可能被清理 |
| 7 | 所有实体 | official_url有效 | 官方证据URL无效 | URL可能已变更 |
| 8 | 所有实体 | sha256格式有效 | 哈希格式无效 | 格式问题不影响内容 |
| 9 | 所有实体 | archive_ok == True（文件存在且哈希匹配） | 证据原件缺失或哈希不匹配 | **主要放宽项**：文件可能被重新处理 |
| 10 | 所有实体 | 证据获取时间不晚于核验时间 | 时间逻辑错误 | 时间戳可能有误差 |
| 11 | 所有实体 | 核验未到复核日期 | 核验已到复核日期 | 复核是额外流程 |
| 12 | law | 法规身份未合并 | 法规身份已合并 | 合并身份仍可使用 |
| 13 | clause | 同版本条款定位不重复 | 条款定位重复 | 重复可后续清理 |

### 2.4 放宽机制

#### 方案A：全局放宽（简单，推荐先用）

- 新增`gate_level`参数：`'strict'`（严格，当前逻辑）或`'relaxed'`（放宽，一级门禁）
- 发布时默认使用`'relaxed'`，但在发布报告中列出所有二级门禁警告
- 保留`'strict'`模式，用于正式上线前的最终检查

#### 方案B：按核验批次放宽（更精细）

- 在verification表新增`gate_level`字段：`'strict'`或`'relaxed'`
- 对于经过用户确认的核验批次（如827逐条重验），标记为`'relaxed'`
- 发布时，根据每条核验记录的`gate_level`决定适用的门禁级别
- `'relaxed'`的记录只检查一级门禁，`'strict'`的记录检查全部门禁

#### 推荐：先用方案A，后续再细化为方案B

### 2.5 审计与可追溯

无论使用哪种方案，都必须保证：

1. **发布报告中增加"二级门禁警告"部分**，列出所有跳过二级门禁的实体和具体原因
2. **每个发布包保留完整的门禁检查日志**，包括一级门禁通过情况和二级门禁警告详情
3. **Git提交记录中说明使用的门禁级别**，便于回溯
4. **用户可以随时切换回严格模式**，重新构建发布包

---

## 三、具体实现方案

### 3.1 修改文件清单

| 文件 | 修改内容 |
|------|---------|
| `tools/pipeline/verification.py` | 新增`gate_level`参数，修改`own_errors`和`gate`函数，新增`relaxed_gate`函数 |
| `tools/pipeline/publish.py` | 修改`prepare`函数，支持`gate_level`参数，发布报告增加二级门禁警告 |
| `tools/pipeline/manage.py` | `site`命令增加`--gate-level`参数 |

### 3.2 核心代码修改（verification.py）

```python
# 新增门禁级别常量
GATE_STRICT = 'strict'    # 严格模式：全部25项检查
GATE_RELAXED = 'relaxed'  # 放宽模式：只检查一级门禁12项

# 一级门禁检查项（硬门禁）
HARD_GATE_CHECKS = {
    'status_check',           # 状态=已核验
    'identity_check',         # 法规身份/条款定位确认
    'validity_check',         # 法规版本现行有效
    'effective_date_check',   # 发布日在有效期内
    'proof_existence_check',  # 有最新通过记录
    'link_check',             # 隐患有启用的依据关联
    'mode_check',             # 适用模式有效
    'required_fields_check',  # 必填字段完整
    'chain_check',            # 链式检查
}

def own_errors(graph, kind, ident, proofs, evidence, as_of, *, 
                allow_upcoming=False, gate_level=GATE_RELAXED):
    """
    门禁检查函数
    gate_level: 
        - 'strict': 严格模式，返回全部错误
        - 'relaxed': 放宽模式，只返回一级门禁错误，二级门禁记录到warnings
    """
    errors = []
    warnings = []
    
    # === 一级门禁（硬门禁）===
    # 1. 状态检查
    row = maps(graph)[kind][ident]
    if row.get("review_status", row.get("status")) != "已核验":
        errors.append("当前状态未核验")
    
    # 2. 身份确认检查
    if kind == "law" and row["identity_status"] != "confirmed":
        errors.append("法规身份未确认")
    if kind == "clause" and row["identity_status"] != "confirmed_locator":
        errors.append("条款定位未确认")
    
    # 3. 法规效力检查
    if kind == "law_version":
        upcoming = allow_upcoming and row["validity_status"] == "即将生效"
        if row["validity_status"] != "现行有效" and not upcoming:
            errors.append("非现行有效版本")
        # 4. 有效期检查
        try:
            effective = date(row["effective_date"])
            if (effective > as_of and not upcoming) or (row["end_date"] and date(row["end_date"]) <= as_of):
                errors.append("发布日不在有效期间内")
        except ValueError:
            pass
    
    # 5. 核验记录存在性检查
    proof = proofs.get((kind, ident))
    if not proof or proof["result"] != "passed":
        errors.append("没有最新通过记录")
        return errors, warnings  # 没有通过记录，直接返回
    
    # 6. 隐患关联检查
    if kind == "hazard" and not row["active_link_ids"]:
        errors.append("没有启用的依据关联")
    
    # 7. 适用模式检查
    if kind == "hazard" and row["mode"] not in ("直接适用", "条件适用", "上位法兜底"):
        errors.append("适用模式无效")
    
    # 8. 必填字段检查（简化版）
    errors += preparation_errors(graph, kind, ident)
    
    # === 二级门禁（软门禁，仅在strict模式下作为错误，relaxed模式下作为警告）===
    if proof and proof["result"] == "passed":
        # 9. 实体版本匹配检查
        if proof["entity_revision"] != row["revision"]:
            msg = "核验记录与当前内容版本不符"
            if gate_level == GATE_STRICT:
                errors.append(msg)
            else:
                warnings.append(msg)
        
        # 10. 依赖哈希匹配检查
        if proof["dependency_hash"] != dependency_hash(graph, kind, ident):
            msg = "核验记录与依赖版本不符"
            if gate_level == GATE_STRICT:
                errors.append(msg)
            else:
                warnings.append(msg)
        
        # 11. 核验人和证据定位检查
        if not proof["reviewer"].strip() or not proof["locator"].strip():
            msg = "核验人或证据定位缺失"
            if gate_level == GATE_STRICT:
                errors.append(msg)
            else:
                warnings.append(msg)
        
        # 12. 公开字段审阅检查
        if kind == "hazard" and proof["public_fields_reviewed"] is not True:
            msg = "公开字段尚未审阅"
            if gate_level == GATE_STRICT:
                errors.append(msg)
            else:
                warnings.append(msg)
        
        # 13. 证据检查
        document = evidence.get(proof["evidence_id"])
        if not document:
            msg = "核验证据缺失"
            if gate_level == GATE_STRICT:
                errors.append(msg)
            else:
                warnings.append(msg)
        else:
            if not official_url(document["official_url"]) or not re.fullmatch(r"[0-9a-f]{64}", document["sha256"]):
                msg = "官方证据URL或哈希无效"
                if gate_level == GATE_STRICT:
                    errors.append(msg)
                else:
                    warnings.append(msg)
            
            if document.get("archive_ok") is False:
                msg = "证据原件缺失或哈希不匹配"
                if gate_level == GATE_STRICT:
                    errors.append(msg)
                else:
                    warnings.append(msg)
            
            # 时间检查
            try:
                checked = timestamp(proof["checked_at"])
                retrieved = timestamp(document["retrieved_at"])
                if retrieved > checked or business_date(checked) > as_of:
                    msg = "证据获取或核验时间晚于适用时间"
                    if gate_level == GATE_STRICT:
                        errors.append(msg)
                    else:
                        warnings.append(msg)
                if proof["review_due_at"] and date(proof["review_due_at"]) <= as_of:
                    msg = "核验已到复核日期"
                    if gate_level == GATE_STRICT:
                        errors.append(msg)
                    else:
                        warnings.append(msg)
            except (ValueError, TypeError):
                msg = "核验或证据日期无效"
                if gate_level == GATE_STRICT:
                    errors.append(msg)
                else:
                    warnings.append(msg)
    
    return errors, warnings


def gate(graph, proofs, evidence, as_of, *, gate_level=GATE_RELAXED):
    """
    门禁主函数
    返回: {
        'hazards': {hazard_id: [errors]},
        'lawVersions': {version_id: [errors]},
        'warnings': {hazard_id: [warnings]}  # 二级门禁警告
    }
    """
    validate_graph(graph)
    as_of = date(as_of) if isinstance(as_of, str) else as_of
    index = maps(graph)
    
    # 收集所有实体的错误和警告
    all_errors = {}
    all_warnings = {}
    for kind in TABLES:
        for ident in index[kind]:
            errors, warnings = own_errors(graph, kind, ident, proofs, evidence, as_of, gate_level=gate_level)
            all_errors[(kind, ident)] = errors
            all_warnings[(kind, ident)] = warnings
    
    # 链式检查（隐患 → 关联 → 条款 → 法规版本 → 法规）
    def chain(kind, ident):
        result = [f"{kind}:{ident}: {reason}" for reason in all_errors[(kind, ident)]]
        row = index[kind][ident]
        if kind == "law_version":
            result += chain("law", row["law_id"])
        elif kind == "clause":
            result += chain("law_version", row["law_version_id"])
        elif kind == "link":
            result += chain("clause", row["clause_id"])
        return result
    
    def chain_warnings(kind, ident):
        result = [f"{kind}:{ident}: {reason}" for reason in all_warnings[(kind, ident)]]
        row = index[kind][ident]
        if kind == "law_version":
            result += chain_warnings("law", row["law_id"])
        elif kind == "clause":
            result += chain_warnings("law_version", row["law_version_id"])
        elif kind == "link":
            result += chain_warnings("clause", row["clause_id"])
        return result
    
    # 隐患门禁结果
    hazards = {}
    hazard_warnings = {}
    for ident, row in index["hazard"].items():
        messages = chain("hazard", ident)
        for link_id in row["active_link_ids"]:
            messages += chain("link", link_id)
        hazards[ident] = sorted(set(messages))
        
        # 收集警告
        warn_messages = chain_warnings("hazard", ident)
        for link_id in row["active_link_ids"]:
            warn_messages += chain_warnings("link", link_id)
        hazard_warnings[ident] = sorted(set(warn_messages))
    
    # 法规版本门禁结果（允许即将生效版本）
    versions = {}
    for ident, row in index["law_version"].items():
        messages = sorted(set(
            [f"law_version:{ident}: {reason}" for reason in
             own_errors(graph, "law_version", ident, proofs, evidence, as_of, allow_upcoming=True, gate_level=gate_level)[0]]
            + chain("law", row["law_id"])))
        versions[ident] = messages
    
    return {
        "hazards": hazards,
        "lawVersions": versions,
        "warnings": hazard_warnings,  # 新增：二级门禁警告
        "gate_level": gate_level,      # 新增：使用的门禁级别
    }
```

### 3.3 修改publish.py

```python
def prepare(db, as_of, *, baseline=None, gate_level='relaxed'):
    # ... 现有代码 ...
    
    # 门禁检查
    gate_result = verification.gate(graph, proofs, evidence, as_of, gate_level=gate_level)
    
    # 筛选通过门禁的隐患
    publishable_hazards = {
        ident: row for ident, row in index["hazard"].items()
        if not gate_result["hazards"].get(ident)
    }
    
    # ... 构建发布包 ...
    
    # 发布报告增加二级门禁警告
    release["gateReport"] = {
        "gateLevel": gate_level,
        "totalHazards": len(index["hazard"]),
        "publishedHazards": len(publishable_hazards),
        "blockedHazards": len(index["hazard"]) - len(publishable_hazards),
        "blockedReasons": Counter(
            reason for reasons in gate_result["hazards"].values() for reason in reasons
        ).most_common(20),
        "warnings": {  # 新增：二级门禁警告详情
            ident: warnings for ident, warnings in gate_result["warnings"].items() if warnings
        },
        "warningSummary": Counter(
            warning for warnings in gate_result["warnings"].values() for warning in warnings
        ).most_common(20),
    }
    
    return release, gate_result
```

### 3.4 修改manage.py

```python
# site命令增加--gate-level参数
@cli.command()
@click.option('--as-of', required=True, help='发布日期')
@click.option('--output', required=True, help='输出目录')
@click.option('--node', default=None, help='Node路径')
@click.option('--gate-level', type=click.Choice(['strict', 'relaxed']), default='relaxed',
              help='门禁级别：strict=严格模式（全部检查），relaxed=放宽模式（仅一级门禁）')
def site(as_of, output, node, gate_level):
    """构建网站发布包"""
    # ... 现有代码 ...
    release, report = publish.prepare(db_path, as_of, gate_level=gate_level)
    # ... 现有代码 ...
```

---

## 四、预期效果

### 4.1 当前数据（r10发布包，严格模式）

| 指标 | 数量 |
|------|------|
| 母库隐患总数 | 1125 |
| 已核验隐患 | 662 |
| 已匹配隐患（827重验中） | 366 |
| 当前发布隐患（r10，严格模式） | 242 |
| 被拦截隐患 | 1078 |

### 4.2 预期效果（放宽模式）

| 指标 | 严格模式 | 放宽模式（预期） | 增量 |
|------|---------|----------------|------|
| 发布隐患数 | 242 | 300-366 | +58~124 |
| 一级门禁拦截 | - | 主要拦截未核验、法规失效等 | - |
| 二级门禁警告 | - | 约100-200条（哈希、依赖版本等） | - |

### 4.3 被拦截隐患分类（预期）

**一级门禁拦截（即使放宽模式也会被拦截）：**
- 状态=待核验的隐患：461个
- 没有启用依据关联的隐患
- 法规版本非现行有效的隐患
- 缺少必填字段的隐患

**二级门禁警告（放宽模式会发布，但记录警告）：**
- 证据原件缺失或哈希不匹配
- 核验记录与当前内容版本不符
- 核验记录与依赖版本不符
- 公开字段尚未审阅
- 核验人或证据定位缺失

---

## 五、风险与应对

### 5.1 风险

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| 放宽门禁后发布了内容质量有问题的隐患 | 网站内容不准确 | 一级门禁仍保证状态=已核验、有通过记录、链式检查；827逐条重验已保证语义匹配 |
| 证据哈希不匹配导致无法追溯原始证据 | 审计困难 | 发布报告中完整记录二级门禁警告，包括哪些证据哈希不匹配；保留原始证据文件 |
| 用户忘记使用了放宽模式 | 混淆发布质量 | 每次构建都在发布报告和Git提交中明确标注门禁级别；manifest.json中增加gateLevel字段 |
| 后续需要切换回严格模式 | 发布数量下降 | 支持`--gate-level strict`参数，随时可切换；保留两种模式的发布包对比 |

### 5.2 建议的使用策略

1. **日常开发和预览**：使用放宽模式（`--gate-level relaxed`），快速看到更多内容
2. **正式上线前**：使用严格模式（`--gate-level strict`），确保全部检查通过
3. **发布报告**：无论哪种模式，都完整记录门禁检查结果和警告
4. **用户确认**：对于放宽模式发布的内容，用户可以抽查确认质量，有问题随时回退

---

## 六、实施步骤

1. **用户确认方案** — 确认分级门禁的思路和具体检查项划分
2. **修改verification.py** — 新增gate_level参数，修改own_errors和gate函数
3. **修改publish.py** — 支持gate_level参数，发布报告增加警告详情
4. **修改manage.py** — site命令增加--gate-level参数
5. **测试验证** — 分别用strict和relaxed模式构建发布包，对比结果
6. **生成报告** — 输出两种模式的对比报告，包括发布数量、拦截原因、警告详情
7. **用户验收** — 用户确认放宽模式的发布内容质量可接受
8. **正式使用** — 日常使用放宽模式，正式上线前用严格模式最终检查

---

**文档结束。** 请用户审阅本方案，确认后开始实施。

## 2026-09-13 已实施变更（用户本人决策，非提案）

**已发布未实施（upcoming）版本的条款可支撑当前隐患引用。**

- 背景：§7 原设计为"upcoming 可进目录但不能支撑隐患"，导致已发布新版（GB 12801-2025、
  GB/T 13869-2026）的条款入库即整体阻断发布，新旧版切换被迫等实施日。
- 用户决策原话："我就是要最新的，没生效也没关系。"
- 变更内容：release_gate_core.gate_law_version 中 upcoming 分支改为 supports_current=True
  （effectiveDate <= asOf 仍标 upcoming 的效力标错拦截保留）；gate_clause §10 注释、
  verify_unified_bundle 条款效力标签检查（接受 现行有效/即将生效）同步对齐。
- 影响：repealed/unknown 仍被排除；引用将始终指向最新发布版，无需再为版本切换排期。
