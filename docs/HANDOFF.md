# 接手说明

先读根目录[AGENTS](../AGENTS.md)，再读[PROJECT_STATE](PROJECT_STATE.md)。后者是唯一当前状态与完整8步计划；本页只列真正需要继续做的工作。

## 下一步

已核生产为PR103合并提交`9cafe88cfac0d66f10321bc83f1cc5e7029b72f2`，build/deploy/online_verify均成功。商贸续轮在`review/commerce-remaining-gaps-20261002`完成云端验证：1680H/1825K/1367C/75LV、25场景，原1671H与25场景保留。源提交与全部验收范围见[本轮验收](COMMERCE_REMAINING_ACCEPTANCE_20261002.json)。

1. 核对本批次唯一PR的精确head、10项独立审核绑定、完整Validate与Build CI。云端执行者已获授权推送创建PR，合并部署由主执行者负责。
2. 合并后核对部署包asOf、releaseHash、1680H及25场景，使用真实桌面和390px浏览器复验线上交互，再更新PROJECT_STATE生产基线。云端本地包验收不能代替新增内容的上线证明。
3. 原44项26准入/7条件归并/1食品跨域排除/9泛化判据不准入/1叉车核验型分别计数，新增电源线原子H另计；保留remainingSourceClaims与个案取证。GB/T13869新版到期仍须另行实审，不自动激活。

## 每次接手先核对

- 源提交、tree、工作区现有修改和同一版本的`knowledge/manifest.json`
- 最近生产Actions、线上`release.json` / `data/manifest.json`与asOf；源码等价不证明已经发布
- 场景records、reviews、依赖指纹、正式投影和计数；源内容改变须重新实审
- GB 12158隔离、未知施行日阅读层、GB/AQ全文权利、候选和私有资料边界仍生效

历史台账、原件或试点材料未取得时，保留具体证据缺口与下一动作；不猜测审核结论，不把缺口消失写成完成。公开文档只留聚合、通用边界及公开证据，不添加企业事实或私有材料位置。
