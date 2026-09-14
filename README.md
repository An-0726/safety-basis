# 隐患依据速查库

面向工贸企业安全检查与评价报告的法规、标准、条款和隐患关联库。国家层面为主，江苏、南京地方依据为补充。

在线站点：<https://an-0726.github.io/safety-basis/>

## 现在只认这四层

| 层级 | 位置 | 用途 | 是否公开 |
|---|---|---|---|
| 正式知识源 | `knowledge/` | 法规版本、条款、隐患、适用关系及核验记录 | 是 |
| 公开出版源 | `source/publication/` | 经审阅可公开的216项法规目录和15份全文 | 是 |
| 私有全文库 | `source/library/` | 本地原件、全文数据库、OCR和待处理资料 | 否，Git忽略 |
| 当前发布包 | `source/releases/current/` | GitHub Pages与离线公开精简版 | 是 |

旧 `data/`、`content/` 和旧发布编号不再是维护入口。架构说明见 [ARCHITECTURE](docs/ARCHITECTURE.md)，日常操作见 [MAINTENANCE](docs/MAINTENANCE.md)。

## 当前基线（2026-09-14）

- `knowledge/`：96个法规身份、97个版本、2,843条条款、2,014项隐患（1,419项active、517项待审核、78项历史）、1,393个当前关联。
- `source/publication/`：216项公开目录；15份获准公开全文；140项官方入口。
- `source/releases/current/`：1,926项公开隐患（1,409项已核验 + 517项待审核候选）、223项法规版本、1,193条正式发布条款、1,530个正式关联；候选记录可查但不能直接作为正式依据。
- `source/library/fulltext.sqlite3`：当前170份私有全文、215,326个检索段落；新增PDF只有成功解析或OCR并建立正文索引后才计数。
- `dist/local/打开本地最终版.cmd`：本地日常使用的唯一总入口；运行 `py -3 tools/build_local_release.py` 可随时重新生成。
- 新版1929条整改表已完成目标字段回灌；621条已修订，1308条保留。517条仍需精确条款/证据回绑，见 `docs/NEW_EDITION_RECONCILIATION_20260914.md`。

这些数字统计的是不同层次，不能互相替代。尤其“216项法规目录”不等于“216份全文”。

## 验证与构建

```text
python tools/v4/validate_all.py
python tools/v4/strict_release_audit.py
python tools/v4/build_unified_release.py --out source/releases/current
python tools/v4/verify_unified_bundle.py --bundle source/releases/current
```

CI只验证并发布 `source/releases/site-selection.json` 指向的包。任何法规效力、条款内容或隐患适用关系变更，都必须经过人工核验，不能仅凭文件名、网页可访问性或模型判断直接生效。

## 隐私边界

本仓库与GitHub Pages是公开空间。企业报告、照片、未脱敏附件、内部台账、受版权限制的标准全文只进入私有目录。法规原文及标准文本的权利归相应发布机关或权利人所有。

## 许可证

代码采用 [MIT License](LICENSE)。
