# 法规目录受控提案（catalog-v1）

`tools/pipeline/catalog.py` 为现有 SQLite 母库提供最小的三段式接口：先构造请求，再生成 sealed proposal，最后在写锁内重建并提交。SQLite 仍是唯一母库；接口不写 `content/`、`data/`、网站构建产物或正式母库之外的来源原件。

## 请求形状

请求至少包含 `formatVersion`、`requestId`、`baseStateHash` 和 `operations`。`baseStateHash` 是当前 `exchange.state_hash()` 的 64 位十六进制值。每个操作使用 `op`、`entity`、可选 `ref`/`id`、`values` 和可选 `source`：

```json
{
  "formatVersion": "catalog-v1",
  "requestId": "REQ_BATCH003_001",
  "baseStateHash": "<当前母库 state_hash>",
  "actor": "batch-003",
  "operations": [
    {
      "op": "reuse",
      "entity": "law",
      "id": "LF_L001",
      "source": {"sourceId": "S_...", "sourceRowId": "R_..."}
    },
    {
      "op": "create",
      "entity": "law_version",
      "ref": "new:version",
      "values": {
        "law_id": "LF_L001",
        "version_key": "2026",
        "document_number": "文号",
        "official_name": "法规名称（2026）",
        "level": "法规",
        "scope": "适用范围",
        "effective_date": "2026-01-01",
        "validity_status": "现行有效",
        "source_url": "https://example.gov.cn/law"
      },
      "source": {"sourceId": "S_...", "sourceRowId": "R_...", "evidenceId": "E_..."}
    },
    {
      "op": "create",
      "entity": "clause",
      "ref": "new:clause",
      "values": {
        "law_version_id": "new:version",
        "article_path": "第一条",
        "quote": "完整条款原文",
        "source_url": "https://example.gov.cn/law"
      },
      "source": {"sourceId": "S_...", "sourceRowId": "R_..."}
    }
  ]
}
```

这段法规、版本、条款请求的完整样例位于本文“请求形状”一节；真实批次应将 `S_...`、`R_...`、`E_...` 替换为母库中已经存在的 ID。版本的 `validity_status` 只是效力判断，`review_status` 仍由接口固定为 `待整理`；不会从请求生成通过记录或核验人。

依据关联接在条款之后，使用临时引用：

```json
{
  "op": "create",
  "entity": "link",
  "values": {
    "hazard_id": "H001",
    "clause_id": "new:clause",
    "role": "直接依据",
    "priority": 1,
    "applicability": "适用于该隐患",
    "jurisdiction_code": "CN"
  },
  "source": {"sourceId": "S_...", "sourceRowId": "R_..."}
}
```

`hazard_tag` 用 `hazard_id/kind/value/ordinal`，`law_alias` 用 `law_id/alias/ordinal`。省略 `ordinal` 时由接口追加到该父实体和类别的末尾。相同语义内容会复用；相同语义键但内容不同必须显式 `reuse` 正确 ID，不能覆盖。标签或别名新增会递增父实体 `revision`、清空 `checked`，并将开放记录退回 `待核验`。

## 法规身份与版本合并

`identity.py` 把确认为同一法规/标准系列的不同版本归到一个身份下。旧身份保留为 `merged`；版本、条款与关联 ID 不变。版本键、标准号、实施日期冲突时拒绝合并，不能用身份合并代替条款对照。

```text
python tools/pipeline/identity.py --db PRIVATE_MASTER propose --source LF_OLD --target LF_KEEP --evidence E_OFFICIAL --reason "有证据的身份合并理由" --output merge.json
python tools/pipeline/identity.py --db PRIVATE_MASTER apply --proposal merge.json --actor REVIEWER
```

实际演练已将 `LF_L011` 归入 `LF_L010`，保留用电安全导则 `L010`（2017）和 `L011`（2026）。未来实施版本不提前替换当前版。完整请求与回执只写入操作日志一次，业务记录只存当前操作和请求 ID，避免成千上万条正文被反复复制。稳定 ID 使用字母起始、字母/数字/下划线/连字符，长度 2–80；旧 ID 保持不变。

## 三个函数和命令

```python
proposal = request_catalog(db_path, request)
report = propose_catalog(db_path, request, output_path)
receipt = apply_catalog(db_path, proposal_or_path, actor="reviewer-name")
```

命令行形式为：

```text
python tools/pipeline/catalog.py --db source/master/safety.sqlite3 propose --request request.json --output source/proposals/catalog-001.json
python tools/pipeline/catalog.py --db source/master/safety.sqlite3 apply --proposal source/proposals/catalog-001.json --actor reviewer-name
```

`apply` 在 `BEGIN IMMEDIATE` 中再次检查母库状态指纹、所有外键、条款定位、依据关联、字段白名单、来源/证据 ID 和提案内容；失败整体回滚。相同 `proposalId` 重复提交返回原回执。`catalog_actions` 和 `catalog_events` 保存完整请求、sealed proposal、来源/证据引用、前后值和临时引用映射。

`sources`、`source_rows`、`provenance`、`hazard_tags`、`law_aliases` 都已经属于 `exchange.STATE_TABLES`，因此这些业务或追溯记录的变化会改变 `state_hash`，导出的 Excel/旧提案不会绕过过期检查。`catalog_actions/events` 是审计记录，不参与业务状态指纹；实际业务行变化仍会改变指纹。

新法规身份固定为 `provisional/待整理`，新版本固定为 `review_status=待整理`，新条款固定为 `legacy_unreviewed/待整理`，新关联固定为 `待核验`。接口不联网核验官方 URL，也不新建来源或证据；传入的 `sourceId`、`sourceRowId`、`evidenceId` 必须已经存在且相互匹配。法规身份合并、法规替代关系、条款冲突解决和核验发布仍在本接口范围之外。
