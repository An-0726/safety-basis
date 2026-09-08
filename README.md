# 隐患依据速查

国家法规标准优先，江苏／南京补充的安全隐患与法规依据速查工具。

在线访问：https://an-0726.github.io/safety-basis/

## 当前架构

第一阶段扩展设计见 [数据架构 V3](docs/DATA_ARCHITECTURE_V3.md)，多来源导入原型见 [source/README.md](source/README.md)。当前生产构建仍使用下述 V2 输入，尚未迁移正式母库。

网站保持纯静态部署，不依赖服务器或数据库服务：

- `content/`：人工 / AI 维护的规范化源数据
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
- 数据状态页可查看规模和完整性统计，并导出维护源 JSON 包
- GitHub Commit 留存数据版本，可比较和回滚

## 数据维护

不要直接编辑 `data/`。修改 `content/` 后运行：

```bash
node tools/build-data.mjs
```

然后提交 `content/` 与重新生成的 `data/`。GitHub Actions 会再次构建并检查 `data/` 是否与维护源一致。

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
