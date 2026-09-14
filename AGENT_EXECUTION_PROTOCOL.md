# AGENT_EXECUTION_PROTOCOL.md — 总控与本地执行器协作协议

> 本文件定义本项目中“总控 AI”与“本地 Luna/agent 执行器”的职责边界。新窗口接手时应与根目录 `AGENTS.md` 一并阅读。

## 1. 核心模式

本项目采用：**总控负责判断与验收，本地 agent 只负责总控无法直接完成的本机执行。**

总控必须始终掌握项目方向、数据口径、法律证据标准、阶段状态和最终上线目标。不得因为本机环境难操作，就把判断权交给本地执行器。

工作循环固定为：

`总控判断与拆解 → 必要时生成严格执行提示词 → 本地 agent 执行 → 回传结构化结果 → 总控复核 → 更新 AGENTS.md → 推进 MASTER ROADMAP`

## 2. 必须由总控完成的工作

以下工作不得因为本地 agent 可访问文件就转交其自行判断：

- 法规真实性、效力状态、发布/实施/废止日期核验；
- 官方原文、具体条/款/项和证据链核验；
- 隐患描述修订、风险含义判断、法规适用性判断；
- Excel 隐患库的正式口径与证据回绑；
- `knowledge/` 的法规身份、版本、条款、隐患和关联设计；
- 同法规同版本去重、真实历史版本区分、canonical/alias 策略；
- candidate 是否可转正；
- publication 与正式知识源边界；
- 网站数据口径、Gate 规则、测试规则、Release Candidate 判定；
- GitHub PR 是否可合并、Pages 是否可正式上线；
- 对本地 agent 回传结果的复核以及下一步决策；
- `AGENTS.md` 的阶段状态、NEXT ACTION 和 MASTER ROADMAP 推进。

法律引用继续遵守硬规则：AI/搜索/OCR/Excel 摘要只能用于定位，正式依据必须回到官方原文/原始证据和准确条款；找不到时写“待核实/证据不足”，不得编造。

## 3. 本地 Luna/agent 只允许承担的工作

只有当任务依赖总控当前无法直接访问或控制的本机环境时，才交给本地执行器，例如：

- Windows PowerShell / CMD 命令执行；
- 检查本机进程、文件锁、端口、占用状态；
- 本机 Git/worktree/文件系统状态检查；
- 运行仓库已有脚本、测试、构建；
- 在明确提示词约束下写本机 `source/library/fulltext.sqlite3`；
- 创建本机 SQLite 一致性备份；
- 本机文件复制、哈希、路径/权限检查；
- 只有本机才能完成的同步客户端状态核查。

本地执行器不得自行决定：

- 删除/合并 document；
- 删除/移动 archive 原件；
- 修改稳定 `LF/LV/C/H` ID；
- 合并同名法规版本；
- 判断法规是否现行/失效/适用；
- 改隐患描述或正式法规依据；
- 为了“清零”候选而生成证据；
- 改项目架构、发布口径或 MASTER ROADMAP；
- 未经总控定义验收标准就继续高风险操作。

## 4. 什么时候必须切换到本地执行器

总控遇到以下情况应停止继续猜本机状态，直接给用户一段可复制的执行提示词：

- 本机文件锁/权限/进程状态无法由当前工具确认；
- Windows 本地 Git/worktree 状态复杂，远程信息不足以安全判断；
- 必须对本机私有 SQLite 做写操作；
- 必须运行仅本机存在的软件/脚本/服务；
- 云端连接器无法完成文件原位替换，但本机可安全完成；
- 继续远程试错可能损坏私有母库或本地 Git 环境。

执行提示词必须包含：目标、允许动作、禁止动作、已知基线、停止条件、验收标准和最终报告格式。Luna 只执行，不扩大任务范围。

## 5. 本地执行器回传后的处理

本地 agent 的“PASS”不是最终结论。总控必须重新检查其报告是否满足预先定义的验收条件；必要时通过 Google Drive/GitHub/上传文件再次独立核验。

只有总控验收后，才允许：

1. 更新 `AGENTS.md`；
2. 将当前 NEXT ACTION 标为完成；
3. 进入下一个 MASTER ROADMAP 动作；
4. 对正式数据或部署状态作最终结论。

## 6. 当前本机执行上下文（2026-09-14）

当前 PHASE 3 第一批任务是工作 `fulltext.sqlite3` 的 FTS5 修复。

总控已经完成：

- 私有库只读审计；
- 隔离副本 FTS rebuild 验证；
- 云盘修复前备份；
- 维护脚本与测试进入 GitHub main；
- repaired candidate 验证为 `integrity_check=ok`，170 documents / 215,326 rows / 全文内容不变。

本机环境已知：

- 工作目录：`D:\ESH\ESH_Codex\work\safety-basis`；
- 当前本地分支：`data-verify-batch-003`；
- 本地没有 `main` 分支，但存在 `remotes/origin/main`；
- `origin/main` 已 fetch；
- `.tmp.drivedownload/`、`.tmp.driveupload/` 为未跟踪临时目录，不得随意删除；
- 旧 `.git/worktrees/wt-agent*` 在 pull 自动清理时出现 Permission denied；
- 不应为了本轮 FTS 修复继续手工清理 `.git/worktrees/*`；
- 用户已确认可能占用 SQLite 的程序已关闭；
- 已给本地 agent 一份严格提示词：从 GitHub main 临时取得 `private_library_maintenance.py`，完成 audit → SQLite Backup API → 仅 FTS rebuild → post-audit → 搜索抽检，并回传结构化报告。

在本地报告回来以前，不得把工作母库 FTS 修复写成“已完成”。

## 7. 新窗口接手规则

新窗口第一步读取：

1. 根目录 `AGENTS.md`；
2. 根目录 `AGENT_EXECUTION_PROTOCOL.md`。

然后按 `AGENTS.md` 的 `CURRENT PHASE / NEXT ACTION / MASTER ROADMAP` 继续。

如果下一动作属于法规核验、隐患描述、证据链、knowledge/候选/发布决策，**总控自己做**。

只有下一动作必须操作用户本机，而当前工具做不到时，才生成严格提示词让本地 Luna 执行；Luna 回传后由总控验收。
