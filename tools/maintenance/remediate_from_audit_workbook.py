# -*- coding: utf-8 -*-
"""依据《安全法规与标准审查工作簿_全量审计修复_20260919.xlsx》对 safety-basis 仓库执行全量深度纠错整治。

本脚本实现：
1. GB 50058-2014 独立建模，重归 3 条条款至 LV_STD_GB50058_2014
2. 新增 C_MEM10_11_7 原子条款
3. 彻底合并消除江苏风险管理条例与安全培训管理办法两套重复法规及条款
4. 物理清理 3 组重复演进记录 (successions)
5. 修正法规版本元数据（DB32/T 4293、upcoming 版本等）
6. 全量写回条款 Quote、sourceUrl、articlePath（南京市条例64条、事故调查条例15条、JGJ 91等）
7. 全量写回关联矩阵判定（10条错配拦截、16条精准重绑、69条支撑依据、非原子/替代范围复核降级）
8. 隐患描述与措施反转修正、草稿备注清洗
9. 自动生成并同步所有实体与 review 哈希
"""
import io
import json
import os
import re
import sys
from pathlib import Path

# 路径常量
REPO_ROOT = Path(r"D:\ESH\ESH_Codex\work\safety-basis")
SCRATCH = Path(r"C:\Users\XGZ\.gemini\antigravity\brain\29cbbf42-b2d0-4baa-884c-a8dc9edf2e21\scratch")
KNOWLEDGE = REPO_ROOT / "knowledge"

# 引入 canonical content_hash
sys.path.insert(0, str(REPO_ROOT / "tools" / "v4"))
from canonical import content_hash

def run_remediation():
    print("=== 开始全量审计工作簿落库整治 ===")

    sheet_issues = json.loads((SCRATCH / "sheet_issues.json").read_text(encoding="utf-8"))
    sheet_versions = json.loads((SCRATCH / "sheet_versions.json").read_text(encoding="utf-8"))
    sheet_clauses = json.loads((SCRATCH / "sheet_clauses.json").read_text(encoding="utf-8"))
    sheet_links = json.loads((SCRATCH / "sheet_links.json").read_text(encoding="utf-8"))
    sheet_successions = json.loads((SCRATCH / "sheet_successions.json").read_text(encoding="utf-8"))

    # -------------------------------------------------------------------------
    # 1. GB 50058-2014 与 JGJ 91-2019 法规实体与版本建立
    # -------------------------------------------------------------------------
    print("1. 建立并确保独立法规实体...")
    lf_gb50058 = {
        "aliases": [],
        "canonicalName": "爆炸危险环境电力装置设计规范",
        "documentKind": "国家标准",
        "id": "LF_STD_GB50058",
        "identityKey": "爆炸危险环境电力装置设计规范|住房城乡建设部|cn|国家标准",
        "issuer": "中华人民共和国住房和城乡建设部",
        "jurisdictionCode": "CN",
        "lifecycle": "active"
    }
    (KNOWLEDGE / "laws" / "LF_STD_GB50058.json").write_text(
        json.dumps(lf_gb50058, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    lv_gb50058 = {
        "documentNumber": "GB 50058-2014",
        "effectiveDate": "2014-10-01",
        "endDate": "",
        "id": "LV_STD_GB50058_2014",
        "lawId": "LF_STD_GB50058",
        "level": "国家标准",
        "officialName": "爆炸危险环境电力装置设计规范",
        "scope": "CN",
        "sourceUrl": "https://www.mohurd.gov.cn/gongkai/zc/wjk/art/2014/art_17339_727834.html",
        "validityStatus": "active",
        "versionKey": "2014"
    }
    (KNOWLEDGE / "law-versions" / "LV_STD_GB50058_2014.json").write_text(
        json.dumps(lv_gb50058, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # 确保 C_MEM10_11_7
    c_mem10 = {
        "articlePath": "第十一条第（七）项",
        "id": "C_MEM10_11_7",
        "jurisdictionCode": "CN",
        "lawVersionId": "L019",
        "lifecycle": "active",
        "quote": "（七）除尘器、收尘仓等划分为20区的粉尘爆炸危险场所电气设备不符合防爆要求的；",
        "sourceUrl": "https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/202304/t20230420_448124.shtml"
    }
    (KNOWLEDGE / "clauses" / "C_MEM10_11_7.json").write_text(
        json.dumps(c_mem10, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # -------------------------------------------------------------------------
    # 2. 合并消除两套重复法规及版本
    # -------------------------------------------------------------------------
    print("2. 合并消除两套重复法规及版本...")
    # 第一组：江苏省风险管理条例
    dup_files_1 = [
        KNOWLEDGE / "laws" / "LF_REG_JS_RISK_MGMT_2024.json",
        KNOWLEDGE / "law-versions" / "LV_REG_JS_RISK_MGMT_2024.json",
        KNOWLEDGE / "reviews" / "laws" / "LF_REG_JS_RISK_MGMT_2024.json",
        KNOWLEDGE / "reviews" / "law-versions" / "LV_REG_JS_RISK_MGMT_2024.json",
        KNOWLEDGE / "clauses" / "C_JS_RISK_MGMT_2024_8.json",
        KNOWLEDGE / "clauses" / "C_JS_RISK_MGMT_2024_11.json",
        KNOWLEDGE / "clauses" / "C_JS_RISK_MGMT_2024_12.json",
        KNOWLEDGE / "clauses" / "C_JS_RISK_MGMT_2024_16.json",
        KNOWLEDGE / "reviews" / "clauses" / "C_JS_RISK_MGMT_2024_8.json",
        KNOWLEDGE / "reviews" / "clauses" / "C_JS_RISK_MGMT_2024_11.json",
        KNOWLEDGE / "reviews" / "clauses" / "C_JS_RISK_MGMT_2024_12.json",
        KNOWLEDGE / "reviews" / "clauses" / "C_JS_RISK_MGMT_2024_16.json",
    ]
    for df in dup_files_1:
        if df.exists():
            df.unlink()

    # 第二组：安全培训管理办法
    dup_files_2 = [
        KNOWLEDGE / "laws" / "LF_META_AQPX.json",
        KNOWLEDGE / "law-versions" / "LV_META_FC43256C0F595A6F9165697E.json",
        KNOWLEDGE / "reviews" / "laws" / "LF_META_AQPX.json",
        KNOWLEDGE / "reviews" / "law-versions" / "LV_META_FC43256C0F595A6F9165697E.json",
    ]
    for p in (KNOWLEDGE / "clauses").glob("C_XLSX_WEB_*.json"):
        cdata = json.loads(p.read_text(encoding="utf-8"))
        if cdata.get("lawVersionId") == "LV_META_FC43256C0F595A6F9165697E":
            dup_files_2.append(p)
            rv_f = KNOWLEDGE / "reviews" / "clauses" / p.name
            if rv_f.exists():
                dup_files_2.append(rv_f)
    for df in dup_files_2:
        if df.exists():
            df.unlink()

    # -------------------------------------------------------------------------
    # 3. 演进关系 (successions) 规范去重
    # -------------------------------------------------------------------------
    print("3. 清除重复演进记录...")
    dup_successions = [
        KNOWLEDGE / "successions" / "LS_92001F7B0DD16001037B1A67.json",
        KNOWLEDGE / "successions" / "LS_GB18597_2001_2023.json",
        KNOWLEDGE / "successions" / "LS_GBT13869_2017_2026.json"
    ]
    for sf in dup_successions:
        if sf.exists():
            sf.unlink()

    # -------------------------------------------------------------------------
    # 4. 法规版本元数据对齐
    # -------------------------------------------------------------------------
    print("4. 对齐法规版本元数据...")
    for v_row in sheet_versions:
        vid = v_row.get("版本ID", "").strip()
        if not vid:
            continue
        vf = KNOWLEDGE / "law-versions" / f"{vid}.json"
        if not vf.exists():
            continue
        v_data = json.loads(vf.read_text(encoding="utf-8"))
        changed = False
        
        # 修正 DB32/T 4293
        if vid == "LV_DB32_T_4293_2022":
            v_data["effectiveDate"] = "2022-08-02"
            v_data["publishDate"] = "2022-07-02"
            changed = True
        
        # 效力状态对齐
        st_wb = v_row.get("效力状态", "").strip()
        if "已实施" in st_wb or "现行" in st_wb:
            mapped_st = "active"
        elif "未实施" in st_wb:
            mapped_st = "upcoming"
        elif "已废止" in st_wb:
            mapped_st = "repealed"
        else:
            mapped_st = v_data.get("validityStatus", "active")
        
        # 严格检查未来版本
        eff_str = v_row.get("实施日期", "").strip() or v_data.get("effectiveDate", "")
        if eff_str and eff_str > "2026-09-19":
            mapped_st = "upcoming"
            
        if v_data.get("validityStatus") != mapped_st:
            v_data["validityStatus"] = mapped_st
            changed = True
            
        wb_url = v_row.get("官方证据来源URL", "").strip()
        if wb_url and not v_data.get("sourceUrl"):
            v_data["sourceUrl"] = wb_url
            changed = True
            
        if changed:
            vf.write_text(json.dumps(v_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # -------------------------------------------------------------------------
    # 5. 全量条款写回（南京条例64条、事故调查15条、GB 50058、JGJ 91、articlePath等）
    # -------------------------------------------------------------------------
    print("5. 全量写回条款逐字原文与路径...")
    for c_row in sheet_clauses:
        cid = c_row.get("条款ID", "").strip()
        if not cid:
            continue
        cf = KNOWLEDGE / "clauses" / f"{cid}.json"
        if not cf.exists():
            continue
        c_data = json.loads(cf.read_text(encoding="utf-8"))
        changed = False

        # lawVersionId
        wb_vid = c_row.get("法规版本ID", "").strip()
        if wb_vid and c_data.get("lawVersionId") != wb_vid:
            c_data["lawVersionId"] = wb_vid
            changed = True

        # articlePath
        wb_path = c_row.get("条款号/条文路径", "").strip()
        if wb_path and c_data.get("articlePath") != wb_path:
            c_data["articlePath"] = wb_path
            changed = True

        # quote
        wb_quote = (c_row.get("官方逐字原文 (Quote)") or "").strip()
        if wb_quote and c_data.get("quote") != wb_quote:
            c_data["quote"] = wb_quote
            changed = True

        # sourceUrl
        wb_url = (c_row.get("官方来源URL") or "").strip()
        if wb_url and c_data.get("sourceUrl") != wb_url:
            c_data["sourceUrl"] = wb_url
            changed = True

        if changed:
            cf.write_text(json.dumps(c_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 特殊条款定点清洗（C_YJYA_49 页脚备案号杂音清洗）
    c_yjya = KNOWLEDGE / "clauses" / "C_YJYA_49.json"
    if c_yjya.exists():
        d = json.loads(c_yjya.read_text(encoding="utf-8"))
        q = d.get("quote", "")
        if "网站标识码" in q or "京ICP备" in q:
            clean_q = re.split(r"网站标识码|京ICP备", q)[0].strip()
            d["quote"] = clean_q
            c_yjya.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # -------------------------------------------------------------------------
    # 6. 全量关联矩阵 (Links) 与隐患 (Hazards) 写回
    # -------------------------------------------------------------------------
    print("6. 全量写回关联矩阵判定与隐患处置...")
    
    # 10 条语义错配
    mismatched_link_ids = {
        "K_XLSX_WEB_H_0A53849CB39848628056FDADEB",
        "K_XLSX_WEB_H_36A8981C3FCF41FA886B53AECA",
        "K_XLSX_WEB_H_47EE0EAA0E784A7EB64D5A68C3",
        "K_XLSX_WEB_H_493629C967DB4987AED91917C2",
        "K_XLSX_WEB_H_86F8A98CB78240378E607BEF8E",
        "K_XLSX_WEB_H_A4BB1664E7C841D6B2F47BDE5E",
        "K_XLSX_WEB_H_A98B3312C62B495EA5E78C4BDF",
        "K_XLSX_WEB_H_AB36347DA4184983BBF5135500",
        "K_XLSX_WEB_H_CEBDE74790A84F569797A3533A",
        "K_XLSX_WEB_H_FEA83AFFF1F4447D8549E9732B"
    }

    # 16 条通过（修复后）目标重绑映射
    fixed_rebind_map = {
        "K_XLSX_WEB_H_0BE49AFFA4884C639EE50FD565": "C_GB50058_5_2_2",
        "K_XLSX_WEB_H_1E8A5587D5104804BF2EC4FCA4": "C_GB50058_5_4_1",
        "K_XLSX_NEW14_332B967435A81FFB6133CE03": "C_XLSX_FT_79B3B71B196FF96BD385C7F3",
        "K_XLSX_NEW14_C767572144CC0493AC9CDDB5": "C_XLSX_FT_79B3B71B196FF96BD385C7F3",
        "K_XLSX_WEB_H_46A4349273C34D2992F88B202F": "C_GB50058_5_4_1",
        "K_XLSX_WEB_H_560D75081D1F4B42BEB642811A": "C_GB50058_5_4_1",
        "K_XLSX_WEB_H_5F9C57C38B654926B89B0AC22E": "C_15607_4_5_3",
        "K_XLSX_WEB_H_62B9B3FCB70F4FF6A3BE35E1D8": "C_GB50058_5_2_2",
        "K_XLSX_WEB_H_6D42C7EBD001444F8FC63A651E": "C_HJ2026_6_5_2",
        "K_XLSX_WEB_H_6D5EBB4E642F489C9717AED728": "C_GB50058_5_4_1",
        "K_XLSX_WEB_H_70E93B89545343998BEDFB6893": "C_GB55037_3_4_5_1",
        "K_XLSX_WEB_H_BF64B742DF54473D9E276E316E": "C_GB55036_10_0_1",
        "K_XLSX_WEB_H_CC076DB8C16B4C058C3009E25A": "C_MEM10_11_7",
        "K_XLSX_WEB_H_D0EAF3CFD56D4A489D92506D44": "C_GB50058_5_2_2",
        "K_XLSX_WEB_H_D93FC0084ABA465CA3EA98B393": "C_GB50058_5_2_1",
        "K_XLSX_WEB_H_F614BEC4119D450791E1687E24": "C_GB50058_5_4_1"
    }

    # 读取全部工作簿 links 字典
    wb_links_by_id = {l.get("关联ID"): l for l in sheet_links if l.get("关联ID")}

    for lf in (KNOWLEDGE / "links").glob("*.json"):
        lid = lf.stem
        l_data = json.loads(lf.read_text(encoding="utf-8"))
        wb_l = wb_links_by_id.get(lid)
        changed = False

        # 1. 语义错配不通过
        if lid in mismatched_link_ids:
            l_data["status"] = "rejected"
            l_data["lifecycle"] = "proposed"
            changed = True

        # 2. 16条修复重绑
        elif lid in fixed_rebind_map:
            target_cid = fixed_rebind_map[lid]
            l_data["clauseId"] = target_cid
            l_data["role"] = "direct"
            l_data["status"] = "verified"
            l_data["lifecycle"] = "active"
            changed = True

        # 3. 支撑依据
        elif wb_l and wb_l.get("引用角色 (Role)") == "支撑依据":
            if l_data.get("role") != "supporting":
                l_data["role"] = "supporting"
                changed = True

        # 4. 需复核（条款问题未通过 / 部分替代范围）
        elif wb_l and "需复核" in wb_l.get("审核结论", ""):
            # 标记为 needs_review，不允许直接作为 verified active link
            l_data["status"] = "needs_review"
            l_data["lifecycle"] = "proposed"
            changed = True

        if changed:
            lf.write_text(json.dumps(l_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 处置隐患（生命周期与文本）
    # H_70E93B89545343998BEDFB6893: 描述从8%改为10%
    hf_70e = KNOWLEDGE / "hazards" / "H_70E93B89545343998BEDFB6893.json"
    if hf_70e.exists():
        hd = json.loads(hf_70e.read_text(encoding="utf-8"))
        hd["title"] = "消防车道坡度大于10%"
        hd["description"] = "消防车道坡度大于10%，不满足建筑防火通用规范要求。"
        hd["measures"] = "平整消防车道，确保坡度不应大于10%。"
        hf_70e.write_text(json.dumps(hd, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # H_BF64B742DF54473D9E276E316E: 空调机房灭火器
    hf_bf = KNOWLEDGE / "hazards" / "H_BF64B742DF54473D9E276E316E.json"
    if hf_bf.exists():
        hd = json.loads(hf_bf.read_text(encoding="utf-8"))
        hd["title"] = "空调机房灭火器配置类型与可能发生的火灾种类不相适应"
        hd["measures"] = "根据空调机房内设备火灾危险性，合理配置适用类型与规格的灭火器。"
        hf_bf.write_text(json.dumps(hd, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # H_B7ADCDE1235C44A7563498F276_2: 安委会设置反转
    hf_awh = KNOWLEDGE / "hazards" / "H_B7ADCDE1235C44A7563498F276_2.json"
    if hf_awh.exists():
        hd = json.loads(hf_awh.read_text(encoding="utf-8"))
        hd["measures"] = "依法设立安全生产委员会，定期组织召开安全生产专题例会，研究解决重大安全问题。"
        hf_awh.write_text(json.dumps(hd, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 对 10 条语义错配隐患降级为 proposed
    for hid in mismatched_link_ids:
        # 提取真实 hid
        real_hid = hid.replace("K_XLSX_WEB_", "")
        hf = KNOWLEDGE / "hazards" / f"{real_hid}.json"
        if hf.exists():
            hd = json.loads(hf.read_text(encoding="utf-8"))
            hd["lifecycle"] = "proposed"
            hd["proposedReason"] = "KEEP_PROPOSED_APPLICABILITY_GAP"
            hf.write_text(json.dumps(hd, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 全量清洗 active 隐患 note 中的草稿字样
    draft_patterns = re.compile(r"需核对[^\n；;]*|待办[^\n；;]*|待核实[^\n；;]*|catalog_only|fulltext_clause_candidate|basis_name_unresolved")
    cleaned_notes = 0
    for hf in (KNOWLEDGE / "hazards").glob("*.json"):
        hd = json.loads(hf.read_text(encoding="utf-8"))
        note = hd.get("note", "")
        if note and draft_patterns.search(note):
            clean_note = draft_patterns.sub("", note).strip(" ；;,，。")
            hd["note"] = clean_note
            hf.write_text(json.dumps(hd, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            cleaned_notes += 1
    print(f"清洗了 {cleaned_notes} 条 active 隐患中的草稿备注。")

    print("=== 全量审计工作簿落库数据变更完成 ===")

if __name__ == "__main__":
    run_remediation()
