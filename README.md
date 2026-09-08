# 隐患依据速查

国家法规标准优先，江苏／南京补充的安全隐患与法规依据速查工具。

在线访问：https://an-0726.github.io/safety-basis/

## 当前架构

采用 SQLite 规范化母库、多 Sheet Excel 编辑交换、证据核验记录和自动网站构建，设计见 [数据架构 V3](docs/DATA_ARCHITECTURE_V3.md)。可执行入口与实施边界见 [数据流水线](source/README.md)。
已实现 [旧数据无损迁移](docs/MASTER_MIGRATION.md)、[Excel 编辑往返](docs/EXCEL_EXCHANGE.md)、[多来源入库与隐患合并](docs/ADMISSION.md)、[核验及严格发布包生成](docs/VERIFICATION_PUBLISH.md)。当前生产构建仍使用下述 V2 输入，新发布器只生成隔离包。

网站保持纯静态部署，不依赖服务器或数据库服务：

- `content/`：过渡期保留的旧规范化输入和全部 batch 历史
  - `hazards.json`：隐患主表
  - `laws.json`：法规 / 标准主表
  - `clauses.json`：法规条款原文
  - `links.json`：隐患与条款之间的关联关系
  - `settings.json`：数据版本与分片参数
- `tools/build-data.mjs`：完整性校验、关联检查、搜索索引构建和运行数据分片
- `data/`：网站运行时使用的派生数据，不作为人工编辑入口
- `app.js`、`js/`：搜索、按需加载、法规反查与页面逻辑

网站启动时只加载轻量搜索索引；点击具体隐患或法规后，再读取对应数据分片。法规原文只保存一次，通过关联关系复用，避免在大量隐患中重复复制。

## 功能

- 隐患关键词、主题、场所、法规类别、地区、匹配方式和核验状态筛选
- 法规 / 标准独立检索，并可从法规条款反查关联隐患
- 展示隐患专业描述、法规原文、整改措施、适用说明和核验状态
- 数据版本、核验日期、法规效力状态可见
- URL 可保存当前隐患 / 法规详情，便于分享和复查
- 支持离线缓存；在线时法规数据采用网络优先策略，避免长期停留旧版本
- 数据状态页可查看规模和完整性统计；旧页面 JSON 导出不能作为完整母库备份
- GitHub Commit 留存数据版本，可比较和回滚

## 数据维护

新增资料放入私有 `source/imports/`，由 AI 和导入工具整理、去重、核验，通过提案更新母库。已有内容通过 Excel 编辑往返维护。原始检查项的“符合/不符合”与通用隐患模板分开保存；待核数据保留在母库并被发布门禁阻断。

核验后生成新网站数据包：

```text
python tools/pipeline/manage.py publish --as-of YYYY-MM-DD --output source/exchange/release-preview-001
```

输出包含 release、索引、分片、manifest 和校验和。用户无需编辑网站 JSON。正式切换前审阅增减差异；当前 4 条真实样板仅供验证流程，未替换站点。

以下命令继续用于过渡期生产数据的重建检查：

```bash
node tools/build-data.mjs
```

GitHub Actions 检查旧 `data/` 与遗留输入一致，同时从公开样板快照独立重建两次、比较输出。`content/README.md` 保留旧维护流程的历史说明，当前操作以本页和流水线文档为准。

详细字段见 [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md)，报告入库流程见 [`docs/WORKFLOW.md`](docs/WORKFLOW.md)。

## 隐私边界

本仓库和 GitHub Pages 为公开内容。企业完整报告、现场照片、未脱敏附件、内部台账等资料不要直接上传本仓库。它们应保留在私有资料源（例如 Google Drive），只将经过筛选、去敏和核验后的知识条目写入本库。

## 本地运行

```bash
python -m http.server 8080
```

访问 `http://localhost:8080/`。

## 许可证

代码使用 [MIT License](LICENSE)。法规原文及其权利归相应发布机关或权利人所有。
