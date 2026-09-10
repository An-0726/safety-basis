# V3/V4 差异验收报告

> 生成时间：2026-09-10
> 基线：V3 SQLite（source/master/safety.sqlite3，SHA-256 7086d945...）vs V4 chat-v4
> V3 全程只读，未修改

## 1. 实体数量对比

| 实体 | V3 | V4 | 分类 |
|---|---|---|---|
| hazards 总数 | 1125 | 712 | expected structural change |
| hazards active 未合并 | 0* | 646 | V3 status 列全为 NULL |
| hazards superseded/merged | 0 | 66 | V4 引入 lifecycle |
| hazards publishable | N/A | 543 (84.1%) | V4 新增链式门禁 |
| laws | 160 | 75 | expected structural change |
| lawVersions | 161 | 75 | V4 只保留实际使用版本 |
| clauses | 2603 | 88 | V3 大量原始导入未筛选 |
| links 总数 | 2298 | 596 | expected improvement |
| links eligible | N/A | 523 | V4 全部专业 review |

*V3 hazards 表 status/merged_into 列全为 NULL，无法区分 active/merged

## 2. V3 已知错误是否被继承

| 问题 | V3 | V4 | 结论 |
|---|---|---|---|
| 非法 role | 2298 (全部) | 0 | V4 已修复，全部 role∈{direct,supporting,fallback} |
| dangling link | 0 | 0 | 均无 dangling |
| 疑似 FACT_NOT_HAZARD 未 reject | 约 169 | 已专业 review 分类 | V4 已区分 verified/rejected/pending |
| 无 review 的 link | 2298 (全部) | 0 | V4 全部 link 有 review+hash 绑定 |

## 3. 常见隐患搜索覆盖（V4 publishable）

| 关键词 | V4 总数 | publishable | 覆盖率 |
|---|---|---|---|
| 消火栓 | 8 | 8 | 100% |
| 疏散 | 26 | 22 | 84.6% |
| 灭火器 | 28 | 25 | 89.3% |
| 特种设备 | 7 | 7 | 100% |
| 特种作业 | 4 | 4 | 100% |
| 培训 | 25 | 24 | 96.0% |
| 应急 | 31 | 30 | 96.8% |
| 粉尘 | 20 | 18 | 90.0% |
| 危险化学品 | 38 | 32 | 84.2% |
| 电气 | 25 | 17 | 68.0% |
| 燃气 | 17 | 15 | 88.2% |
| 有限空间 | 2 | 2 | 100% |
| 防雷 | 7 | 6 | 85.7% |
| 涂装 | 1 | 1 | 100% |

电气类覆盖率最低（68%），需后续优先处理。

## 4. V4 publishable hazard category 分布

| category | 数量 |
|---|---|
| 安全管理 | 117 |
| 消防安全 | 84 |
| 危险化学品与危险物质 | 44 |
| 电气安全 | 43 |
| 应急与事故管理 | 42 |
| 安全标志 | 36 |
| 设备设施 | 32 |
| 总图与建筑 | 32 |
| 粉尘防爆 | 30 |
| 涂装安全 | 23 |
| 作业安全与个体防护 | 21 |
| 专项安全与EHS | 19 |
| 燃气安全 | 10 |
| 安全教育 | 8 |

## 5. 差异分类总结

- **expected improvement**: V4 link 全部专业 review + hash 绑定，质量大幅提升；V3 的 2298 条 link 全部 role 非法且无 review
- **expected structural change**: V4 经过 merge/拆分/质量筛选，实体数减少但更精准；引入 Requirement 层、lifecycle、succession 等 V3 没有的架构
- **regression**: 未发现（strict audit PASS，releaseBlockers=0，搜索回归 20/20）
- **needs expert review**: 剩余约 175 个 active hazard 仍无合格 link，电气类覆盖率最低（68%），需后续优先处理

## 6. V3 冻结状态确认

- V3 SQLite SHA-256: `7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`（与预期一致，未修改）
- V3 全程以 mode=ro 只读访问
