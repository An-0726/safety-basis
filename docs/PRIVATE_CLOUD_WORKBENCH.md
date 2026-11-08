# 私有云端隐患检查工作台

**状态：私有生产站点已于 2026-11-08 部署，15 项线上流程验收全部通过。** 使用站点所有者的 ChatGPT 账号登录即可操作。云端源码随本文交付；源码合并和 CI 状态以 [GitHub 工作流](https://github.com/An-0726/safety-basis/actions/workflows/site.yml) 及对应 PR 为准，不把运行部署等同于源码已合并。

| 交付项 | 当前记录 |
|---|---|
| 私有访问链接 | [打开隐患检查工作台](https://safety-basis-inspection.upezra8.chatgpt.site) |
| 部署与访问 | 2026-11-08 部署成功；owner-private，受 ChatGPT 登录保护 |
| 源码交付 | 云端实现见 `workbench/cloud/`；当前提交与 CI 见对应 [工作流](https://github.com/An-0726/safety-basis/actions/workflows/site.yml) |
| 首轮线上验收知识包 | `2026.11.08.3bb002368e57`，快照日期 `2026-11-08` |
| 公开知识规模 | 1764 条隐患、1949 条关联、1514 条条款、106 个法源版本 |
| 云端本地测试 | 38 / 38：26 项 API / SQL 业务回归，12 项报告回归 |
| 其他本地回归 | Node 880 项、Python 工作台与路径保护 19 项通过 |
| 线上验收与实际导出 | 15 / 15 通过；实际下载 Word 与 3 页 PDF 已核验 |

本次线上核对的知识包 `release_hash` 为 `e681ca40a794c5dce0aeb751a3e9b93dac9d976cc0266379e31a4ad8cc5c920d`。该值标识知识内容，不替代应用源码提交或未来发布记录；后续版本从登录后的 `/api/health` 与发布工作流核对。

该知识包版本是首轮线上验收凭据。后续源码合并并发布后，以工作台页脚和 `/api/knowledge/meta` 的实际版本、公开网站 `data/manifest.json` 及对应 main 工作流核对；同一版本的知识内容哈希须一致。

## 使用者如何进入

使用者**直接打开 [私有工作台](https://safety-basis-inspection.upezra8.chatgpt.site)，使用站点所有者的 ChatGPT 账号完成登录即可，无需安装 Python、Node.js 或运行命令**。站点内可创建项目、录入记录、上传照片、检索条款、核实事实、提交审核和下载 Word/PDF。匿名请求不能读取业务记录。

首次体验可点击“创建脱敏示例”。示例企业、观察描述和图片均为合成材料，记录保持草稿，事实保持待核；示例图片不构成现场证据。本次线上验收也只使用合成样例，模拟确认仅验证流程，不代表真实企业事实或专业结论。正式记录仍需实际观察、适用性核实和人工专业审核。

原 [GitHub Pages 速查网站](https://an-0726.github.io/safety-basis/) 继续提供公开法规检索；企业项目、照片、审核和报告通过私有工作台处理。本机安装方式保留在 [工作台运行说明](../workbench/README.md)。

## 实现与数据边界

云端使用同一份 [`workbench/frontend/`](../workbench/frontend/) 界面，通过 Worker 实现原有业务 API。检索继续调用 [`DataStore`](../web/js/store.js) 与 [`searchHazardsDetailed`](../web/js/search.js)，加载经过完整性校验的正式公开知识包；没有另建法规库，也没有把企业问法发送给外部搜索或模型服务。实现见 [知识包桥接](../workbench/cloud/knowledge.mjs)。

| 部分 | 职责与存储 |
|---|---|
| Sites 私有访问入口 | 在请求进入应用前执行 owner-private 登录或所有者服务访问校验 |
| Cloudflare Worker | 运行项目、记录、照片、依据、事实、审核、报告和备份 API |
| D1 | 保存项目、隐患记录、照片元数据、审核、报告快照和审计记录 |
| R2 | 保存处理后的私有照片及已生成的 Word/PDF 文件；下载须经应用 API |
| 静态资源 | 同一前端、公开知识包、报告样式配置和授权字体；不含企业业务数据 |

这是**单个所有者的共享工作区**。浏览器身份与所有者服务操作分别记录来源；所有者服务访问不冒充实名审核人。API 未收到可信身份上下文时拒绝访问，不从客户端自行提交的身份头建立身份。Worker 的入口信任 Sites 已完成的私有访问校验，因此部署必须保持 owner-private 边界，不能将同一入口直接开放为匿名公网服务。[入口实现](../workbench/cloud/worker.mjs) · [API 实现](../workbench/cloud/api.mjs)

照片在浏览器中转换为 JPEG、规范化尺寸并移除图像元数据，服务器再次校验 JPEG 结构与尺寸、移除 EXIF/IPTC/注释后保存。API 返回私有、不缓存响应；公开静态资源入口不读取 D1 或 R2 中的业务文件。

**企业照片、业务数据库、私有 PDF、备份、账号凭据和服务令牌不得进入公开 GitHub 仓库或 Pages。** 云端构建按指定目录复制应用源码及校验通过的公开法源资产，跳过运行目录、数据库和凭据；私有 Sites 配置在仓库外的独立工作区维护。[打包入口](../workbench/cloud/tools/prepare_site_checkout.py)

## 已实现的业务流程

| 功能 | 行为与约束 |
|---|---|
| 企业项目 | 填写企业、项目、检查日期、检查人和用途；项目条件改变会撤销当前记录的事实确认与审核 |
| 检查记录 | 录入位置、设备、现场原话、专业描述、整改建议、责任人和期限；可编辑、排序、复制和删除草稿 |
| 现场照片 | 多图上传、说明、排序和删除，支持照片清单 CSV；修改照片会重新进入待核状态 |
| 条款匹配 | 复用正式知识包的条款原文、官方入口、H/K/C/LV 稳定 ID 和场景配置；保留条件不足、法源缺证提示 |
| 适用条件与事实 | 逐项填写确认、否定或待核及核实说明；搜索结果、描述和照片不会自动成为确认结论 |
| 人工专业审核 | 事实与法源齐备后提交，填写审核人和意见后确认或驳回；不合格记录保留待补或草稿状态 |
| Word/PDF 报告 | 已审核报告只包含已确认记录；草稿明确标注待核；保存不可变报告快照及导出文件 |
| 备份与审计 | 下载结构化数据、照片、报告及审计记录的私有 ZIP；保留历史报告引用的照片 |

辅助条款不能单独替代直接或兜底依据；资料核查不能直接认定为现场缺陷。法规尚未施行、检查日期超过所选知识包日期、当前依据或适用条件已经变化时，阻止新的确认或正式导出，提示重新选取并核实。历史报告保持原样。

事实和审核请求必须携带当前修订号；SQL 条件更新防止并发覆盖。导出期间项目或记录变化时，不保存过期报告。已提交数据后发生读取故障时，异常处理保留可能已被数据库引用的 R2 文件，避免误删已保存的照片或报告。[存储实现](../workbench/cloud/storage.mjs)

## 云端报告与本机报告的区别

两种运行方式均保留完整法规原文、适用条件、来源与稳定 ID，并附现场事实和审核记录；报告基于保存的快照生成。

| 项目 | 云端 | 本机 |
|---|---|---|
| Word | `docx` 生成 OOXML 文档 | `python-docx` 生成文档，支持私有 Word 母版 |
| PDF | `pdf-lib` 与随构建发布的授权字体独立排版 | 优先 LibreOffice 转换 Word；无转换器时使用 ReportLab |
| 样式替换 | 使用 `report-config.json` 调整标题、字体配置、字号、页边距和六列表格列宽 | 样式配置及可替换的私有 Word 母版 |
| 分页 | 与 Word 使用相同内容快照，分页可能不同 | LibreOffice 路径来自实际 Word；ReportLab 路径独立分页 |

云端没有调用 LibreOffice，也没有实现任意 Word 母版的直接导入。未提供原版母版时采用可替换配置，不宣称完全复刻已有企业报告。云端版保留法规与事实附件，不提供关闭这些附件的配置。参见 [云端报告引擎](../workbench/cloud/reporting.mjs)、[共享报告配置](../workbench/templates/report-config.json) 和 [本机模板说明](../workbench/templates/README.md)。

PDF 嵌入字体问题已修复，12 项报告回归检查有效 TrueType 字体子集、字形轮廓、完整中文正文与实际渲染。线上已实际下载 `safety-basis-cloud-example.docx` 与 `safety-basis-cloud-example.pdf`；Word 含嵌入照片，PDF 为 3 页，中文法规正文可提取，均通过本次合成样例验收。字体结构与渲染检查见 [报告测试](../workbench/cloud/tests/reporting.test.mjs)。

## 维护与构建

以下命令供维护者使用，最终使用者无需执行。维护环境需要 Node.js 22.13 或以上；构建正式知识包与准备工作区还使用现有 Python 工具。

### 1. 在 GitHub 源码工作区验证

在仓库根目录执行：

```sh
python -m workbench prepare
npm ci --prefix workbench/cloud
npm test --prefix workbench/cloud
```

默认测试读取 `source/releases/current`；指定其他已验证包时：

```sh
WORKBENCH_BUNDLE=/private/verified-knowledge node --test workbench/cloud/tests/cloud_flow.test.mjs
```

`prepare` 的日期与知识包行为见 [本机运行说明](../workbench/README.md#更新知识包)。现有库的候选与未通过发布链的规则不会因为云端打包而自动进入正式包。

### 2. 准备独立私有 Sites 工作区

先通过托管工具建立 owner-private Worker 站点，并启用名为 `DB` 的 D1 与 `BUCKET` 的 R2 绑定。托管工具生成的 `.openai/hosting.json` 应位于仓库外的独立站点目录。下列命令要求该身份配置已经存在，不会新建公开站点，也不会复制企业资料：

```sh
python workbench/cloud/tools/prepare_site_checkout.py \
  --site /private/safety-basis-site \
  --bundle source/releases/current
```

进入该工作区后：

```sh
cd /private/safety-basis-site
npm ci
npm test
npm run build
```

构建输出为 `dist/client` 与 `dist/server`，另带托管配置与版本化 D1 迁移。构建逐文件核对公开知识包哈希。实际发布通过该私有 Sites 项目的托管流程完成；不要用公开 Pages 替代私有访问入口。[构建实现](../workbench/cloud/build.mjs) · [D1 schema](../workbench/cloud/db/schema.ts) · [版本化迁移](../workbench/cloud/migrations/)

需要修改 schema 时，在 `workbench/cloud` 目录使用已锁定依赖的 `drizzle-kit generate` 生成新迁移，审查迁移后再通过托管流程应用；不要修改已应用迁移来覆盖已有业务数据。应用更新前保留可核对的私有备份。

### 3. 合成样例预览

在上述独立站点工作区完成构建后：

```sh
npm run dev -- --port 5173
```

该预览只用于合成样例验收：D1 使用内存 SQLite 适配器，R2 使用内存对象存储，进程结束即丢失数据；它不是云端持久化服务，不能用来保存真实企业资料。生产站点使用实际托管 D1/R2。已有浏览器验收工具可通过 `--url` 指向预览，详见 [工作台测试说明](../workbench/README.md#7-测试)。

## 已取得的测试证据

2026-11-08 本地云端测试 **38 / 38 通过**，由 [`cloud_flow.test.mjs`](../workbench/cloud/tests/cloud_flow.test.mjs) 的 26 项 API / SQL 回归和 [`reporting.test.mjs`](../workbench/cloud/tests/reporting.test.mjs) 的 12 项报告回归组成。API 回归使用真实接口、正式公开知识包、实际 SQLite SQL 和事务、内存 R2；其中一项调用真实报告引擎，解析 Word/PDF 并检查照片、完整法条、引用 ID、快照日期和草稿标识。其余报告业务用例明确使用测试替身。报告专项另行检查字形完整性、中文正文和实际渲染。Node 全量 880 项与 Python 工作台及路径保护 19 项也已通过。

覆盖无身份与伪造身份头、跨站写入、事实未知、事实说明缺失、辅助条款、资料核查类型、法规日期、过期修订号、并发写入、修改撤销审核、历史报告不变、JPEG 元数据清理、级联删除、备份完整性、导出期间修改，以及 D1 已提交后读取故障不误删文件。

部署后的实际站点进一步执行了 **15 / 15 项线上验收**，使用真实 Worker、D1、R2 和受保护的下载接口。验收全部使用合成企业、描述、图片和人工填写的模拟审核，不采集真实企业资料。

| 序号 | 已通过的线上检查 |
|---|---|
| 1 | 匿名读取业务记录须先经过 Sites 私有访问校验 |
| 2 | 部署的 Worker 能访问实际 D1 和校验通过的知识包 |
| 3 | 真实检索保留 `needs_conditions` 条件不足提示 |
| 4 | 真实检索保留 `evidence_gap` 法源缺证提示 |
| 5 | 真实检索保留 `fact_unconfirmed` 事实未确认提示 |
| 6 | 合成项目、观察与 R2 照片保存为尚未确认的草稿 |
| 7 | 未知事实不能通过专业确认 |
| 8 | 云端实际导出带草稿标记、照片和完整法规正文的报告 |
| 9 | 明确填写合成事实并审核后生成不可变的已审核报告快照 |
| 10 | 认证后的 Word 下载返回真实文件字节及私有缓存策略 |
| 11 | 认证后的 PDF 下载返回真实文件字节及私有缓存策略 |
| 12 | 下载的 Word 内嵌照片，3 页 PDF 保留可提取的中文法规正文 |
| 13 | 私有备份归档包含 D1 记录、照片和报告文件 |
| 14 | 实质修改撤销当前确认，同时保留原历史报告 |
| 15 | 后续新请求仍可读取已保存的项目与私有对象 |

以上记录确认本次部署可用。最终云端源码 PR、对应提交和远端 CI 仍按 [当前工作流](https://github.com/An-0726/safety-basis/actions/workflows/site.yml) 核对，不预填未来提交哈希，也不沿用前序 PR 的 CI 结果作为本次云端源码检查结果。

## 真实限制与剩余事项

- **身份与审核：**单 owner 共享工作区，不是多租户产品；未提供企业 SSO、多人角色分权或专业资格认证。审核人姓名和意见是人工审核轨迹，不是电子签章、机构资质或独立复核证明。
- **在线完整备份：**当前接口上限为 32 MiB；超过限制时须由维护者从私有 D1/R2 导出，接口不会因此删除原数据。云端 ZIP 包含 `workspace.json` 与对象文件，格式不同于本机 SQLite 备份；当前没有网页一键恢复，不能直接交给本机 `restore` 命令。生产数据恢复演练、保留期限和长期备份由部署维护者落实。
- **法源：**266 条候选仍按证据缺口处理：136 条缺精确条款关联、111 条原依据或关联已被拒绝、17 条适用性或审核待补、2 条原文证据缺失或引用未解析。候选不直接用于正式确认，不能为了上线而转正。另有 11 条 active 记录未通过完整发布链。见 [知识库收口](KNOWLEDGE_CLOSEOUT.md) 与 [逐 ID 对账](KNOWLEDGE_CLOSEOUT_20261108.md)。
- **真实问法：**目前真实脱敏企业问法及独立专业人员标注均为 0；29 条新增合成样例和 120 条历史合成回放不能代表真实现场准确率。可导入工具已完成，后续实际样本须在私有位置保存与评估。见 [检索评估报告](SEARCH_EVALUATION_20261108.md) 与 [导入契约](SEARCH_EVALUATION.md)。
- **报告：**默认模板可替换配置；云端任意 Word 母版导入未实现。单次报告最多 150 条记录，单张照片最多 6 MiB、合计最多 6 MiB；超限时明确要求压缩照片或分批导出，原始记录继续保留。缺少字形的特殊字符会提示修正，不静默丢字。此次样例已验证实际 Word/PDF，未提供的企业原版母版仍不能宣称完全复刻。
- **源码交付：**私有生产站点已部署并通过上述验收；源码与 CI 通过对应工作流追溯，后续更新以实际部署版本与工作台知识包显示为准。
