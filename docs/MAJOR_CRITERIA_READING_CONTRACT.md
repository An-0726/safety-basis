# 独立官方原文查阅契约

本层提供官方行政文件原文查阅，不能取得本站现行判定依据资格，不创建canonical C、H、K，不放松普通日期、法源或语义Gate。未知施行日仍为null。现有规范目录、direct专题、AQ短主题和题录投影保持各自原契约。

## 来源与审核

`knowledge/major-criteria-reading/v1` 是独立命名空间。records保存完整印发通知、官方分节标题、各一级项及其全部嵌套原文，明确原文件与补充文件关系，保存私有官方证据元数据及必要的原创解释整理。文件的发布日期、明确施行日或未核准状态与已有受控目录逐字段一致；使用记录只描述主管机关在某日引用两文件，不能倒推出最早施行日。

每份文件有独立text-review，精确绑定整个notice/sections正文及逐项内容hash和审核决定。组级scope-review另外绑定完整record、两份text-review、完整题录及canonical LF/LV metadata/review/证据链、公开权利依据、当前使用记录、必要说明。helper只读提供hash，不生成review或批准决定。

范围review只允许 `referenceTextPublicationReady:true` 且 `currentDeterminationBasis:false`。metadata-only审核不能自动批准全文，普通C/H依据Gate不读取此命名空间。原文查阅仅限经过独立公开范围审查的政府行政文件；GB/AQ技术标准身份不能继承行政文件的公开依据。

任一主补充成员、审核、证据或说明依赖缺失、变化、未来审核、错配或身份/日期不一致时，全组退出查阅投影。原有题录可继续保留。文本和摘要核对不是现场重大隐患结论，也不是源文件当前外部规则全部有效的保证。

## 公开文件与常量

`manifest.files.majorCriteriaReading` 指向 `data/major-criteria-reading.json`。该文件由独立source projection重算并纳入manifest、site-manifest、checksums及releaseHash。verifier逐对象比较投影，重新计算封装hash也不能绕过内容或资格限制。稳定源快照显式包含新命名空间的record与review。

根schema为 `safety-major-criteria-reading-v1`。referenceOnly固定true；currentDeterminationBasis、standaloneDeterminationAllowed、allIndustryCoverage固定false；reviewedCurrentClauseCount和directHazardCount固定0。计数只使用readingGroupCount、sourceDocumentCount、firstLevelItemCount，不使用当前条款数或H数。

readingGroups每组必须与已审目录的primary及全部companion集合一致。每份sourceIdentity逐字段对照目录，包括版本、文号、法性质、官方链接、范围、分组与配套关系，以及effectiveDate的null值。字段不允许偷偷加入active状态、basisRef、clauseId或H/K关联。

公开文本包含完整noticeText及有序sections/items；每项quote照录官方行政正文。necessary officialClarifications仅允许完整原创整理或待核官方链接两种模式：`reviewed_summary`、`official_link_pending`。显示为“依据官方说明整理，非规范原文”或明确待核说明，不伪装为标准quote。相关时期、来源日期、页位和URL随说明保留。首批不复制官方解读全文或被转引GB文字。

## 首批非煤范围

主文矿安〔2022〕88号含地下32、露天13、尾矿库19，共64个一级项及79个数字子项；补充矿安〔2024〕41号含4+2+2，共8个一级项。64+8仅为一级项原文数量，不能称逻辑叶子数、已审现行C数量或现场隐患数。

主文明确2022-09-01施行；补充通知未单列明确施行日，保持null。广西局2026-02-13报道同时对照两文件执法，只是有日期的使用证据。2026征求意见稿及意见截止日期不替换本组。

16组原创整理保留必要范围与例外，另1组联合试运转期限只提供待核链接，不显示未核当前数值。尾矿库说明必须同时保留威胁尾矿库安全、暴雨/洪水等红色或橙色预警、停止相应作业，以及大雨/暴雨期间现场实时巡查和应急抢救人员例外。正常生产波动不能被改成统一百分比豁免；历史解读人员数值不能自动成为当前要求。

## 页面和检索

仍保留三个页签，在现有官方查阅入口的对应目录组内用一次展开显示主文与补充；不新增第四入口或阅读路由。未知日期及只读边界在折叠时也可见，不能复用现行条文/H卡的资格、状态和计数文案。

目录组/文件总数不相加，显示“其中若干组若干份可展开原文，不计入现行条文”；一级项原文数量在展开区域说明。独立阅读selector可补充检索，但始终返回完整主补配套组。精确文号只匹配文件自身身份；不能将跨两文件的词拼成AND命中。切回现行条文或关联隐患时不索引或显示reading内容，AQ仍禁止quote。

缺少可选manifest键时兼容旧包；声明该键但路径、payload或跨文件身份校验错误时按现有专题fail-closed策略处理，不在失败后的popstate恢复残留内容。

## 验收

验证所有审核/内容/日期/权利/伴随文件的负向门禁、来源快照和原子退出；同时核72项全部原文重建、说明例外、无资格升级、无C/H/K、新旧数据差异、manifest完整性和重封装篡改。全量Node/Python、validators、双日期strict/build/verify、schema/隐私及真实包模型回放完成后才冻结。真实GUI未验时必须明示，模型和模拟DOM不代替实际视觉验收。
