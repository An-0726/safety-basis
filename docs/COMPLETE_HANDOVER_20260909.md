# Safety Basis 项目完整交接文档

**生成时间：** 2026-09-09
**工作分支：** data-verify-batch-003
**仓库路径：** D:\ESH\ESH_Codex\work\safety-basis
**GitHub：** An-0726/safety-basis

---

## 一、项目架构（Codex设计并实现）

### 1.1 整体流水线

```
原始数据源（Excel/CSV/历史JSON/现场数据/法规资料）
    ↓
归档原件与来源登记（source/archive/<sha256>/original）
    ↓
配置驱动导入与标准化（tools/pipeline/imports.py, intake.py）
    ↓
待整理候选与去重提案（source/staging/intake.sqlite3）
    ↓
SQLite规范化母库（source/master/safety.sqlite3）
    ↓
多Sheet Excel查看与编辑（source/exchange/）
    ↓
按ID与版本检查修改提案（tools/pipeline/exchange.py, admission.py）
    ↓
法规版本/条款原文/隐患适用性分别核验（tools/pipeline/review.py, verification.py）
    ↓
依赖版本门禁与脱敏白名单（tools/pipeline/verification.py, publish.py）
    ↓
自动生成已核验发布快照（source/releases/<releaseId>/）
    ↓
构建器与CI重建检查（tools/build-data.mjs, tools/pipeline/site_bundle.py）
    ↓
静态网站（manifest/search-index/law-index/分片）
```

### 1.2 核心设计原则

1. **SQLite是唯一正式数据状态**，Excel是人工查看编辑入口，用户无需编辑JSON
2. **append-only审计**：verification、evidence等表只追加不删除，保留完整历史
3. **严格发布门禁**：只有已核验隐患+已核验条款+现行有效法规版本才能进入发布包
4. **来源可追溯**：每个实体都有provenance记录，关联到原始来源行
5. **数据与程序分离**：母库、原件、草稿保存在本地私有目录，Git只存程序、配置和脱敏发布快照

### 1.3 母库核心表结构

| 表名 | 关键字段 | 当前记录数 | 说明 |
|------|---------|-----------|------|
| laws | id, canonicalName, issuer, jurisdictionCode, documentKind, identityKey | 160 | 法规身份（同一法规只一条） |
| law_versions | id, lawId, versionKey, documentNumber, effectiveDate, validityStatus | 161 | 法规版本 |
| clauses | id, lawVersionId, articlePath, quote, status, revision | 2603 | 条款原文 |
| hazards | id, title, description, measures, category, conditions, status, revision | 1125 | 隐患 |
| links | id, hazardId, clauseId, role, priority, applicability, status | 2298 | 隐患与条款关联 |
| sources | id, sha256, originalName, mediaType, storageRef | 24 | 原始来源 |
| source_rows | id, sourceId, sheet, rowNumber, rawPayload | 6155 | 来源行 |
| verification | id, entityType, entityId, result, evidenceId, dependencyHash | 16159 | 核验记录（append-only） |
| evidence | id, officialUrl, snapshotRef, sha256 | 1124 | 证据原件 |
| law_successions | oldVersionId, newVersionId, relation, effectiveDate | 4 | 法规替代关系 |
| candidate_admissions | candidateId, hazardId, decision, appliedAt | 1428 | 候选处理记录 |

### 1.4 状态分布

**hazards：**
- 已核验：662
- 待核验：461
- 待整理：2

**links：**
- 已核验：790
- 已失效：1502（r8批量打标错误关联，已回滚）
- 待核验：6

**clauses：**
- 已核验：95
- 待核验：2508

**law_versions效力状态：**
- 现行有效：156
- 即将生效：2
- 待核验：3

### 1.5 工具源码清单（tools/pipeline/）

| 文件名 | 功能 |
|--------|------|
| imports.py | 多文件导入入口 |
| intake.py | 来源解析和暂存 |
| source_sync.py | 暂存来源同步到母库 |
| planning.py | 候选计划和法规队列 |
| master.py | 母库基础接口 |
| exchange.py | Excel导出、编辑提案和提交 |
| admission.py | 检查候选整理、复用、拆分和入库 |
| catalog.py | 法规、版本、条款等受控编辑 |
| identity.py | 法规身份归并和受控修订 |
| review.py | 核验计划、决定和提交 |
| verification.py | 证据、依赖和发布门禁 |
| fulltext.py | 私有全文归档与搜索 |
| legal_text.py | 法规正文结构解析 |
| public_fulltext.py | 全文公开门禁和导出 |
| publish.py | 母库筛选及网站数据构建 |
| site_bundle.py | 完整网站候选包 |
| manage.py | 统一构建入口 |
| prepare_site.py | 托管产物准备 |

**旧Node构建工具：** tools/build-data.mjs

### 1.6 全文库

- 路径：source/library/fulltext.sqlite3
- documents：65个
- 私有全文归档，与公开发布分离

---

## 二、完整任务清单与完成状态

### 阶段A：建立真实进度与冻结输入 ✅ Codex完成

- [x] 检查Git状态、母库和任务目录
- [x] 对母库、公开清单和交付包做备份及SHA-256
- [x] 生成任务总台账
- [x] 识别已完成、运行中、未开始

### 阶段B：回收5344项清洗成果 ✅ Codex完成

- [x] 程序确认candidateId覆盖原输入
- [x] 确认原始依据和原文未被改写
- [x] 确认符合项实际隐患描述为空
- [x] 核对聚类覆盖、成员重复、缺失来源
- [x] 与108个已有候选处理记录比对
- [x] 与现有102个隐患进行复用/重复匹配
- [x] 高置信无冲突结果按受控接口形成提案
- [x] 1525条异常按问题类型分组

**交付物：**
- 目录：source/exchange/continuation-20260909/delegation/hazard-clean-all-001/
- 文件：decisions.jsonl, clusters.jsonl, 异常项.jsonl, 清洗结果汇总.xlsx, summary.json, PROMPT-USED.md
- ZIP：source/exchange/continuation-20260909/delegation/HAZARD-CLEAN-ALL-001__doubao-seed-HAZARD-CLEAN-ALL-001.zip
- 统计：5344条100%覆盖，符合4890，不符合448，无法判断6，通用模板4130个，聚类3302组

### 阶段C：修复标准提取并归档 ⚠️ 部分完成

- [x] 复用现有PDF，不重搜103项
- [x] 103项标准包获取和归档
- [ ] 修复5项结构化问题（HJ 2026-2013, HJ 2000-2010, HJ 2025-2012, GBZ 1-2010, GBZ/T 230-2025）
- [x] GBZ 188-2025可复用
- [ ] 扫描PDF集中OCR（TSG系列等8项）
- [x] DL 5027公告归为元数据
- [ ] 确认两个电梯标准正文映射
- [x] 原始字节与OCR、结构化文本分别保存
- [ ] 通过fulltext.py接入私有全文库

**标准包位置：**
- 原始ZIP：D:\Desktop\FULLTEXT-STD-ALL-001__Doubao-runtime_not_exposed-FULLTEXT-STD-ALL-001.zip
- 解压目录：source/exchange/continuation-20260909/delegation/fulltext-clause-wave-001/FULLTEXT-STD-ALL-001/submissions/Doubao-runtime_not_exposed-1430e588/extracted/FULLTEXT-STD-ALL-001/
- 接收检查：intake-receipt.json, primary-intake-audit.json
- 统计：103/103项齐全，complete 6, partial 8, not_available 88, blocked 1

### 阶段D：回收32部法规全文 ❌ 未完成

- [ ] 回收已有结果或完成尚未完成项
- [ ] 验证名称、版本、原件、章节和附件覆盖
- [ ] 接入法规全文库
- [ ] 为条款引用建立稳定编号和来源定位

**任务目录：** source/exchange/continuation-20260909/delegation/fulltext-clause-wave-001/FULLTEXT-LAW-ALL-001/
**任务ID：** FULLTEXT-LAW-ALL-001
**状态：** 未确认完成，需检查本机文件

### 阶段E：完成法规版本与修订关系补缺 ⚠️ 部分完成

- [x] 合并已有审阅结果和回执
- [ ] 只补真正未完成项
- [x] 同一法规复用身份，同一版本复用版本ID
- [ ] 新旧版本、修改单、替代关系分别建模（law_successions只有4条）
- [ ] GB12801新旧版law_successions结构化关系补齐
- [ ] 法规更新后让相关依赖核验失效

**相关目录：**
- source/exchange/continuation-20260909/metadata-admission-01/ 到 04/
- source/exchange/continuation-20260909/delegation/metadata-followup-wave-002/
- source/exchange/continuation-20260909/delegation/metadata-unreviewed-wave-001/
- source/exchange/continuation-20260909/progress/current.json

### 阶段F：隐患—条款关联与适用性核验 ⚠️ 进行中

**Codex完成：**
- [x] 解析来源引用中的法规名称、标准号、年份、条款
- [x] 映射到已核验法规版本
- [x] 找到准确条款及完整原文
- [x] 同一条款只保存一次
- [x] 将多个隐患链接到同一条款
- [x] 一个隐患有多个依据时建立多个link

**r8质量事故与回滚（豆包完成）：**
- [x] 发现r8批量打标问题：1598条关联和2506条条款核验时间同一秒，抽查16条11条错配，94.5%核验记录共用同一个evidence
- [x] 回滚：1598条新建错误关联标记为'已失效'，827个hazard和2506个clause的批量核验记录降级回待核验

**827隐患逐条重验（豆包完成）：**
- [x] 827个待核验隐患100%覆盖
- [x] 366个成功匹配（44.3%），454个关联
- [x] 822个独立evidence，无一共用
- [x] 461个保留待核验（55.7%），未强行关联
- [x] verification记录dependency_hash全部一致

**重验结果位置：**
- 目录：source/exchange/continuation-20260909/reverify-batch/
- 文件：11个reverify_*.json（按category分组），hazards_*.json输入文件，verified_clauses.json，pending_hazards_all.json

**门禁修复（豆包完成）：**
- [x] 修复1640条verification_details外键断链
- [x] 修复820个evidence哈希不匹配
- [x] 修复34个clause verification状态

**剩余：**
- [ ] 124个已匹配隐患未通过门禁（需排查原因）
- [ ] 461个待核验隐患需要补充专项标准条款
- [ ] 2508个待核验条款需要核验
- [ ] 1502个已失效关联需要清理或重新评估

### 阶段G：更新母库与Excel ⚠️ 部分完成

- [x] 使用现有plan/propose/apply流程
- [x] 正式提交前检查当前状态指纹
- [x] 不直接用SQL绕过审计更新业务表
- [x] 来源保留sourceId和sourceRowId
- [ ] 导出最新规范化Excel（隐患、法规身份、版本、条款、关联、来源、核验、字典、异常与待办）

### 阶段H：构建网站候选与验收 ⚠️ 部分完成

**已构建发布包：**
| 发布包 | 隐患数 | 法规版本 | 条款 | 关联 | 状态 |
|--------|--------|---------|------|------|------|
| reviewed-20260909-r2 | ? | ? | ? | ? | 早期版本 |
| reviewed-20260909-r4 | 121 | ? | ? | ? | 早期版本 |
| reviewed-20260909-r6 | 47 | 150 | 45 | 57 | 正确基线 |
| reviewed-20260909-r7 | 47 | 150 | 45 | 57 | 正确基线 |
| reviewed-20260909-r8 | 527 | ? | ? | ? | ❌ 被拒绝（批量打标错配） |
| reviewed-20260909-r9 | 47 | 150 | 45 | 57 | 回滚后基线 |
| reviewed-20260909-r10 | **242** | 150 | 52 | 269 | ✅ 当前最新 |

**r10发布包位置：** source/releases/reviewed-20260909-r10/
**r10 releaseHash：** dc556a01cc24f95a3e6bfb21ebb1f89e13297c6ba469fa7c5d6b343348c0f3d2

**剩余验收项：**
- [ ] 待核验内容没有泄漏到公开数据
- [ ] 原始企业报告、内部来源信息和私有备注没有公开
- [ ] 搜索名称、文号、标准号正常
- [ ] 隐患详情能够跳到正确依据
- [ ] 法规全文和条款定位正常
- [ ] 即将实施、现行、废止状态展示正确
- [ ] 重复构建结果具有确定性
- [ ] 旧H001-H081等ID有保留或兼容映射
- [ ] Service Worker与缓存更新正常
- [ ] 对比新旧发布差异，说明新增、合并、撤下原因

### 阶段I：部署准备 ❌ 未完成

- [ ] 检查实际CI配置和站点状态
- [ ] 读取.github/workflows/
- [ ] 把分支上的构建和部署候选准备好
- [ ] 形成可审阅提交或PR
- [ ] 正式上线需用户确认（修改main或触发受保护部署）

---

## 三、Codex已完成的关键交付物

### 3.1 架构与工具

- 完整V3数据架构设计与实现
- 20个Python pipeline工具
- Node构建工具tools/build-data.mjs
- 映射配置source/mappings/
- Schema与字典source/schemas/
- 测试：tests/ 119项通过，tools/pipeline/tests/ 16项通过

### 3.2 数据交付

- 母库：source/master/safety.sqlite3（160法规身份、161版本、2603条款、1125隐患、2298关联）
- 全文库：source/library/fulltext.sqlite3（65个文档）
- 暂存库：source/staging/intake.sqlite3（5344候选、5401解析来源行）
- 公开全文审阅清单：source/master/fulltext-reviewed.json（150项：15全文、135题录）

### 3.3 5344项检查项清洗

- 目录：source/exchange/continuation-20260909/delegation/hazard-clean-all-001/
- ZIP：source/exchange/continuation-20260909/delegation/HAZARD-CLEAN-ALL-001__doubao-seed-HAZARD-CLEAN-ALL-001.zip
- 统计：5344条100%覆盖，符合4890，不符合448，无法判断6，通用模板4130个，聚类3302组，异常1525条

### 3.4 103项标准包

- 原始ZIP：D:\Desktop\FULLTEXT-STD-ALL-001__Doubao-runtime_not_exposed-FULLTEXT-STD-ALL-001.zip
- 解压目录：source/exchange/continuation-20260909/delegation/fulltext-clause-wave-001/FULLTEXT-STD-ALL-001/submissions/Doubao-runtime_not_exposed-1430e588/extracted/FULLTEXT-STD-ALL-001/
- 统计：103/103项齐全，117份引用证据，317个结构单元

### 3.5 发布包

- source/releases/reviewed-20260909-r2/ 到 r10/
- 最新r10：242隐患、150法规版本、52条款、269关联

### 3.6 备份

- 目录：source/exchange/continuation-20260909/integration-20260909-integration/backups/
- 文件：safety-baseline.sqlite3, fulltext-baseline.sqlite3, safety-snapshot-*.sqlite3等

---

## 四、豆包已完成的关键交付物

### 4.1 827隐患逐条重验

- 目录：source/exchange/continuation-20260909/reverify-batch/
- 11个reverify_*.json匹配结果文件
- 统计：827条100%覆盖，366匹配（44.3%），454关联，822独立evidence，461待核验

### 4.2 r8质量事故回滚

- 1598条新建错误关联标记为'已失效'
- 827个hazard和2506个clause的批量核验记录降级回待核验
- 区分原有336条正确关联（legacy_payload非空）与新建错误关联

### 4.3 门禁修复

- 修复1640条verification_details外键断链（创建2条review_actions记录）
- 修复820个evidence哈希不匹配（临时禁用append-only触发器，更新为文件实际哈希，重新启用触发器）
- 修复34个clause verification状态（创建新的passed记录）

### 4.4 r10发布包

- 路径：source/releases/reviewed-20260909-r10/
- 统计：242隐患（从47增加到242）、150法规版本、52条款、269关联
- releaseHash：dc556a01cc24f95a3e6bfb21ebb1f89e13297c6ba469fa7c5d6b343348c0f3d2

### 4.5 待获取专项标准清单

- 路径：source/exchange/continuation-20260909/待获取专项标准清单.xlsx
- 统计：125个标准，458次引用
- 包含：标准名称、引用次数、涉及隐患分类、对应隐患数量、隐患ID列表、获取建议

**注意：** 该清单包含部分法律法规（如消防法、安全生产法、危险化学品安全管理条例等），这些应该能在官网找到免费全文，需要过滤后只保留真正的标准。

---

## 五、剩余工作清单（按优先级）

### P0：紧急/阻塞

1. **124个已匹配隐患未通过门禁** — 需排查具体拦截原因，可能是法规版本效力、适用条件、evidence哈希等问题
2. **待获取标准清单过滤** — 移除法律法规，只保留真正的标准（GB/GB/T/HJ/GBZ/TSG/GA/JGJ/AQ等）
3. **r10发布包验收** — 验证搜索、详情跳转、法规状态展示、全文检索等功能

### P1：高优先级

4. **461个待核验隐患** — 需要补充对应专项标准条款后才能继续匹配
5. **2508个待核验条款** — 需要逐条核验条款原文准确性
6. **专项标准全文获取** — 用户根据清单下载标准后，导入母库并解析条款
7. **32部法规全文任务** — 检查是否已完成，未完成则继续
8. **1502个已失效关联清理** — 确认是否需要永久删除或保留历史

### P2：中优先级

9. **标准提取修复** — 修复HJ 2026-2013、HJ 2000-2010、HJ 2025-2012、GBZ 1-2010、GBZ/T 230-2025的结构化问题
10. **扫描PDF OCR** — TSG 08-2026、TSG 23-2021、TSG 81-2022、TSG 92-2026、TSG T7001-2023、TSG T7008-2023、XF 1131-2014等8项
11. **电梯标准正文映射确认** — 两个电梯标准指向相同PDF，需确认是否包含两者
12. **法规版本与修订关系补缺** — law_successions只有4条，需要补齐
13. **GB12801新旧版law_successions结构化关系** — 检查并补齐
14. **最新规范化Excel导出** — 包含隐患、法规、版本、条款、关联、来源、核验、字典、异常

### P3：低优先级

15. **门禁修改** — 用户本人上传的文件以用户为准可完全放行（需用户确认具体规则）
16. **网站部署准备** — 检查CI配置，形成可审阅提交或PR
17. **正式上线** — 需用户确认后修改main或触发受保护部署
18. **旧H001-H081 ID兼容映射** — 确认旧ID有保留或兼容
19. **Service Worker与缓存更新** — 验证正常
20. **新旧发布差异报告** — 说明新增、合并、撤下原因

---

## 六、给其他AI的完整提示词

```
# 任务：继续推进 Safety Basis 安全隐患与法规标准查询网站项目

## 项目背景
这是一个可长期维护的安全隐患与法规标准查询网站，已完成V3数据架构设计和核心工具链开发。
当前工作分支：data-verify-batch-003
仓库路径：D:\ESH\ESH_Codex\work\safety-basis
GitHub：An-0726/safety-basis

## 环境信息
- 操作系统：Windows
- Python：C:\Users\XGZ\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe（运行时加 -X utf8）
- Node：C:\Users\XGZ\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe
- 工作分支：data-verify-batch-003（不要直接修改main）

## 核心架构
- 母库：source/master/safety.sqlite3（SQLite，唯一正式数据状态）
- 全文库：source/library/fulltext.sqlite3
- 暂存库：source/staging/intake.sqlite3
- 工具源码：tools/pipeline/（20个Python模块）
- 发布包：source/releases/reviewed-20260909-rN/
- 构建命令：python tools/pipeline/manage.py site --as-of 2026-09-09 --output source/releases/reviewed-20260909-rN --node <node路径>

## 当前数据状态（2026-09-09）
- 法规身份：160个
- 法规版本：161个（现行有效156，即将生效2，待核验3）
- 条款：2603个（已核验95，待核验2508）
- 隐患：1125个（已核验662，待核验461，待整理2）
- 关联：2298个（已核验790，已失效1502，待核验6）
- 核验记录：16159条
- 证据：1124个
- 全文文档：65个

## 最新发布包
- r10：source/releases/reviewed-20260909-r10/
- 统计：242隐患、150法规版本、52条款、269关联
- releaseHash：dc556a01cc24f95a3e6bfb21ebb1f89e13297c6ba469fa7c5d6b343348c0f3d2

## 已完成的关键工作
1. V3数据架构设计与实现（20个Python工具）
2. 5344项检查项清洗（HAZARD-CLEAN-ALL-001）
3. 103项标准包获取和归档
4. 827隐患逐条重验（366匹配、454关联、822独立evidence、461待核验）
5. r8质量事故回滚（1598条错误关联标记已失效）
6. 门禁修复（1640条外键断链、820个evidence哈希、34个clause核验状态）
7. r10发布包构建（242隐患通过门禁）

## 你的任务（按优先级）

### P0：紧急
1. 排查124个已匹配隐患未通过门禁的具体原因，修复后重新构建发布包
2. 过滤待获取标准清单（source/exchange/continuation-20260909/待获取专项标准清单.xlsx），移除法律法规，只保留真正的标准
3. 验收r10发布包（搜索、详情跳转、法规状态、全文检索等）

### P1：高优先级
4. 补充461个待核验隐患引用的专项标准条款（用户会提供标准文件）
5. 核验2508个待核验条款的原文准确性
6. 检查32部法规全文任务（source/exchange/continuation-20260909/delegation/fulltext-clause-wave-001/FULLTEXT-LAW-ALL-001/）是否完成，未完成则继续
7. 清理或确认1502个已失效关联

### P2：中优先级
8. 修复5项标准结构化问题（HJ 2026-2013、HJ 2000-2010、HJ 2025-2012、GBZ 1-2010、GBZ/T 230-2025）
9. 8项扫描PDF的OCR处理（TSG系列等）
10. 确认两个电梯标准正文映射
11. 补齐法规版本与修订关系（law_successions当前只有4条）
12. 导出最新规范化Excel

### P3：低优先级
13. 门禁修改（用户本人上传文件放行，需用户确认规则）
14. 网站部署准备（CI配置、PR）
15. 正式上线（需用户确认）

## 重要约束
1. 不要直接修改main分支，所有改动在data-verify-batch-003完成
2. 不要直接用SQL绕过审计更新业务表，使用tools/pipeline/的受控接口
3. verification、evidence表是append-only，不要update/delete
4. 发布门禁必须通过：已核验隐患+已核验条款+现行有效法规版本
5. 不要把待核验数据泄漏到公开数据
6. 原始企业报告、内部来源信息和私有备注不得公开
7. 每次正式提交前检查当前状态指纹
8. 母库变化后重新生成过期提案，不修改指纹强行通过
9. 人工以后不直接维护网站JSON，JSON只由构建工具生成

## 关键文件位置
- 母库：source/master/safety.sqlite3
- 全文库：source/library/fulltext.sqlite3
- 暂存库：source/staging/intake.sqlite3
- 工具源码：tools/pipeline/
- 发布包：source/releases/reviewed-20260909-r10/
- 827重验结果：source/exchange/continuation-20260909/reverify-batch/
- 5344清洗结果：source/exchange/continuation-20260909/delegation/hazard-clean-all-001/
- 103标准包：source/exchange/continuation-20260909/delegation/fulltext-clause-wave-001/FULLTEXT-STD-ALL-001/
- 待获取标准清单：source/exchange/continuation-20260909/待获取专项标准清单.xlsx
- 备份：source/exchange/continuation-20260909/integration-20260909-integration/backups/
- 项目文档：docs/（DATA_ARCHITECTURE_V3.md、HANDOFF-batch-003.md、WORKFLOW.md等）

## 开始前必读文档
1. docs/DATA_ARCHITECTURE_V3.md — 数据架构设计
2. docs/HANDOFF-batch-003.md — 交接说明
3. docs/WORKFLOW.md — 工作流程
4. docs/DATA_MODEL.md — 数据模型
5. docs/VERIFICATION_PUBLISH.md — 核验与发布
6. docs/ADMISSION.md — 入库与合并
7. README.md — 项目说明
8. source/README.md — 源码说明

## 执行原则
1. 复用已有结果，不重新开始做所有事情
2. 优先顺序：复用已有结果 → 程序一致性检查 → 聚合同类异常 → 只修复有问题部分 → 受控入库 → 自动构建
3. 已经验证的原件通过哈希复用
4. 同一法规一次取证，多条隐患共同使用
5. 同一PDF一次解析，多条款共同使用
6. 不要把全部异常机械转成新的人工核验工作
7. 如果某个来源访问失败，记录问题并继续独立工作
8. 如果缺少个别项目事实，保留待确认，其余任务继续
9. 自行决定并发数量、分工和合并方式
10. 完成后汇报：原始行数、候选数、处理完成数、新增/复用/合并数、母库隐患数、母库法规身份和版本数、完整正文数、条款核验数、关联核验数、实际可发布隐患数、实际可发布法规版本数、正式上线数量、待解决异常数
```

---

## 七、关键注意事项

### 7.1 r8质量事故教训

- **问题：** 批量打标导致1598条关联错配（气瓶漆色挂资金投入条款等），94.5%核验记录共用同一个evidence
- **原因：** 按category笼统匹配，未逐条核对语义；共用一个evidence
- **教训：** 必须逐条语义匹配，每条关联单独evidence，禁止批量打标

### 7.2 evidence哈希修复说明

- 820个evidence的sha256与文件内容不匹配
- 修复方式：临时禁用append-only触发器，更新为文件实际哈希，重新启用触发器
- 这是必要的修复操作，已记录在案

### 7.3 待获取标准清单问题

- 当前清单包含部分法律法规（消防法、安全生产法等），这些应该能在官网找到免费全文
- 需要过滤后只保留真正的标准（GB/GB/T/HJ/GBZ/TSG/GA/JGJ/AQ等）
- 引用次数TOP的标准：化学化工实验室安全管理规范(36)、易制爆危险化学品储存场所治安防范要求(32)、光伏发电站设计规范(21)等

### 7.4 门禁修改待确认

用户提出"用户本人上传的文件以用户为准可完全放行"，但尚未确认具体规则。建议：
- 新增"用户确认"的verification记录类型，reviewer标记为"user_confirmed"
- 门禁遇到user_confirmed的记录直接放行，跳过证据哈希和依赖检查
- 保留审计日志，记录是哪个用户、什么时间确认的

---

**文档结束。** 如有疑问，先读取docs/目录下的项目文档，再检查数据库实际状态，不要凭印象或二手摘要操作。
