# 可替换检查记录模板

默认示范版为A4横向检查记录，列顺序为“序号 / 位置设备 / 隐患 / 隐患照片 / 整改建议 / 依据状态”，隐患照片紧随隐患。每条引用的完整原文、适用条件、稳定ID、知识快照日期放入附件。图片保留比例、旋转方向，经本机转码移除EXIF；不截掉现场证据。

尚未取得用户原版Word母版；本目录不是原版母版的复刻。

## 更换排版参数

将 `report-config.json` 复制到私有运行目录的 `templates/report-config.json`，按需要修改标题、字体、字号、A4/Letter、portrait/landscape、页边距和列宽比例。不要将真实企业模板、印章或签名提交到公开仓库。

## 更换Word母版

```sh
python -m workbench template --data-dir /private/inspection
```

这会在 `/private/inspection/templates/inspection.docx` 生成可编辑模板；若文件已存在不会覆盖。可将自己的母版放到同一位置，保留需要的段落、页眉、页脚和页面设置。支持占位符：

| 占位符 | 内容 |
| --- | --- |
| `{{title}}` | 报告标题（草稿会带待核标记） |
| `{{company}}` / `{{project}}` | 企业与项目 |
| `{{inspection_date}}` / `{{inspectors}}` | 日期与检查人员 |
| `{{report_mode}}` / `{{report_id}}` | 报告状态与编号 |
| `{{created_at}}` / `{{purpose}}` | 导出时间与用途 |
| `{{findings_table}}` | 检查表插入位置（独立段落） |

母版没有表格占位符时，检查表追加在文末；法规全文、适用条件、事实和审核附件统一追加，避免静默遗漏。导出的快照保存模板配置及母版哈希派生版本，后续换母版不会改变历史报告。

优先用 LibreOffice 将实际Word转换为PDF。未安装转换器时使用 ReportLab 从同一快照生成完整PDF，接口会明确返回 `reportlab (independent layout)`；内容一致，分页与Word可能不同。可设置 `WORKBENCH_SOFFICE` 指向转换器。
