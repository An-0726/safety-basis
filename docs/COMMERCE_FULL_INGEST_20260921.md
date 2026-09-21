# 商贸集团检查全量补库（2026-09-21）

- 来源：当前商贸集团检查文件夹 16 份 Word 检查记录。
- 去企业化：未把企业名称、联系人、照片或个人信息写入知识库。
- 来源事项：134 条；覆盖矩阵：134/134。
- 处理原则：已有 canonical 隐患直接复用；复合句拆分；真正缺口新增通用候选。
- 新增隐患：48 条，其中 active 1 条、proposed 47 条。
- 新增正式 direct：H_COM_DUST_AIR_BLOW → GB 15577-2018 第9.5条。
- proposed 不进入公网，后续逐条补齐官方直接条款和适用条件后再转正。
- 详细逐条映射：docs/commerce-ingest-map-20260921.jsonl。

## 正式部署结果

- PR #76 已合并 `main`，merge commit `fdd973190e76d53b02a1cfaddea1c2b6af9dcdca`。
- main Validate run `35553278277`：PASS。
- main Build / Pages Deploy / Online Chromium Verify run `35553278312`：PASS。
- 正式公开包：1,681 hazards / 59 laws / 59 law versions / 1,304 clauses / 1,791 links；public proposed 0。
- 正式 `releaseHash=c69264f35bb6e046692b60f1833d1d808c7c764bc56b6f626c17e771770902e3`。
