# 隐患检查工作台 MVP

可运行的私有检查应用：创建企业项目、记录现场原话和专业描述、管理多张照片、复用正式知识库检索并选择精确条款、逐项核实适用条件、专业审核、导出 Word/PDF。一个 Python 服务、一个业务 SQLite、原生浏览器界面，检索直接调用现有 `DataStore` / `searchHazardsDetailed`，没有第二套法规库或词库。

## 1. 安装和启动

需要 Python 3.11+、Node.js 22+。在本仓库根目录执行：

```sh
python -m pip install -r tools/pipeline/requirements.txt -r workbench/requirements.txt
python -m workbench
```

打开 **http://127.0.0.1:8765/**。Windows 可将 `python` 替换为 `py -3`。第一次启动缺少发布包时，会按中国标准时间当天从 `knowledge/` 构建并验证；不会下载或读取本机其他项目材料。

默认业务数据保存到当前用户目录中的 `.safety-basis-workbench`，与仓库分开。也可指定私有目录：

```sh
python -m workbench --data-dir /private/inspection-data --port 8765
```

Windows PowerShell 示例：

```powershell
py -3 -m workbench --data-dir D:\EHS_Private\inspection-data
```

若要放在仓库内，只允许已忽略的 `workbench/runtime/`、`workbench/private/`、`workbench-data/` 或 `tmp/`；不允许写入 `web/`、`knowledge/` 或发布目录。

### 更新知识包

```sh
python -m workbench prepare
```

按指定历史日期复核可用 `--as-of YYYY-MM-DD`。更新后重启工作台，新检索使用新包；已经选定的法条和历史报告保持原来的文字、H/K/C/LV ID、快照日期、版本和哈希，不会静默改写。**快照日期不是实时法源核验承诺**，专业审核仍须核对实际适用版本。

审核与新正式报告会核对条款施行日期、检查日期和所选快照，并比较当前包的依据及适用条件。法规尚未施行、检查日期晚于知识包日期、引用被移除或内容变化时，须按检查日期准备合适的包并重新选择、核实。已导出的历史报告始终保持原样。修改企业、检查日期等项目条件会重置当前记录的事实与审核；同时编辑时，旧版本的事实或审核请求会被拒绝，须重新读取记录。

## 2. 完成一条检查记录

1. 创建项目，填写企业、项目名称、检查日期、检查人和用途。
2. 新建记录，填写位置、设备、现场原话、专业描述和整改建议；区分“现场隐患”与“资料核查”。记录可编辑、复制、排序；复制后重新录入现场事实与照片。
3. 上传 JPEG/PNG/WebP 照片，添加说明、调整顺序，必要时删除；每张照片对应具体记录。图像保留比例、校正旋转并移除EXIF，原图不会上传到第三方。可下载照片清单CSV。
4. 输入现场问法，查看条件提示，主动选择检索建议或正式条目。查看条款原文、各引用的适用条件和官方入口；同一隐患有多个场景时，只选本次适用的场景。可取消或重选依据。
5. 逐项记录条件和事实为“已确认 / 已否定 / 待核”，写明核实依据。不得由搜索结果、描述模板或示例图片自动推定现场结论。排除/误判边界按原文展示，明确核对其限制。
6. 提交审核。缺事实或法源时保存为“待补事实/证据”；齐备后进入“待审核”。审核人填写姓名和意见后确认或驳回。修改实质内容、照片、依据或事实会回到草稿，保留历史审核轨迹。
7. 导出“已审核报告”只含已确认记录；“草稿报告”明确标注待核，保留其他状态。下载Word、PDF和不可变的报告快照；历史报告在项目中持续可用。

专业审核记录是本机人工填写的审核轨迹，不是电子签章或机构资质认证。第一版不提供多人身份核验或权限矩阵。

## 3. 脱敏样例和导出示例

网页的“创建脱敏示例”会创建一条带合成图片和正式法条的草稿，所有事实均为待核，不自动通过审核。

用于验证导出程序的命令：

```sh
python -m workbench demo --export --data-dir /private/workbench-demo
```

`--export` 只对该命令新生成的合成示例模拟事实确认和审核，不用于真实企业记录。命令打印报告目录，其中有 `inspection.docx`、`inspection.pdf` 和 `snapshot.json`。合成图片明确写有 `SYNTHETIC DEMO - NOT SITE EVIDENCE`。

## 4. Word/PDF与模板

默认示范表格的“隐患照片”列紧随“隐患”列，外框1.5磅、内线0.5磅，照片保持比例；法规附件保留每条选定引用的完整原文、适用范围、官方来源和稳定ID。另附事实与审核记录。

支持替换私有 Word 母版、标题/字体/页边距/列宽配置；见 [模板说明](templates/README.md)。未提供原版母版，因此示范版不宣称完全复刻既有检查记录。

PDF优先使用已安装的 `soffice` / `libreoffice` 转换实际Word；可用环境变量 `WORKBENCH_SOFFICE` 指向可执行文件。无转换器时采用 ReportLab 生成完整PDF，页面会说明独立排版，接口标记所用引擎；内容共用同一快照，分页可能不同。

## 5. 备份与恢复

网页“备份”或以下命令会使用SQLite在线备份机制，将数据库、照片、报告、私有模板一起压缩：

```sh
python -m workbench backup --data-dir /private/inspection-data
python -m workbench restore /private/workbench-backup-xxx.zip --data-dir /private/restored-inspections
```

**备份含企业私有资料，妥善保存，不上传公开GitHub或Pages。** 恢复只接受空目录，校验路径、数据库及引用完整性；不会覆盖正在运行的数据。旧报告仍可引用已从当前记录移除的照片，避免历史报告失去证据。长期清理、加密备份和保留期限由部署方管理。

## 6. 部署边界

- GitHub Pages继续发布原有静态速查网站，不承载工作台API、企业照片或SQLite。
- 默认仅监听 `127.0.0.1`，适合本机试用；未开放公共注册、遥测或外部AI上传。
- 团队远程使用时，在受控主机设置 `WORKBENCH_ACCESS_TOKEN` 后再监听内网地址，并通过 HTTPS 反向代理提供访问。浏览器弹出基本认证，用户名任意、密码为该环境变量；不要把密码写入源码或命令提交。
- 该MVP的共享密码不是完整多人账号系统；尚未实现角色权限、SSO、加密磁盘或审计防篡改服务。真实团队生产使用须由部署方完成主机、HTTPS和私有备份配置。

## 7. 测试

```sh
python -m workbench prepare
python -m unittest discover -s workbench/tests -v
python -m playwright install chromium
python -m workbench.tests.browser_flow --output /private/workbench-ui-qa
```

浏览器测试另需安装 `playwright` Python 包与 Chromium。默认自动启动隔离的临时后端，可传 `--browser-executable /path/to/chromium` 使用系统浏览器，或 `--url` 指定已有的样例工作台。截图和报告输出目录必须在仓库外。测试内容包括项目/记录/照片/法源/事实/审核/导出、编辑撤销确认、原报告保持快照、损坏知识包拒绝、备份恢复和私有目录不暴露。

禁止启动 Chromium 的环境可显式使用 `--engine dom --dom-module /path/to/jsdom/lib/api.js` 运行 DOM 与真实后端联调；该模式明确记录 `visual_validation: false`，不代替浏览器及版式验收。交付应用本身不需要 jsdom。

## 8. API与代码位置

- `backend/app.py`：项目、记录、照片、事实、审核、导出API。
- `backend/knowledge_bridge.mjs`：原检索引擎和公开包完整性校验。
- `backend/storage.py`：业务数据库及审计轨迹。
- `backend/reporting.py`：Word与PDF，模板替换和完整法条附件。
- `backend/backup.py`：一致性备份和空目录恢复。
- `frontend/`：工作台界面，无外部CDN。
- `/api/docs`：本机API文档；公开部署需遵守上述访问边界。

回滚源码可切回上一个Git提交；不要删除或覆盖私有运行目录。恢复数据用已验证备份恢复到新目录后再切换启动参数。
