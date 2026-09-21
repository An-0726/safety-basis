#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];K=ROOT/"knowledge"
def rd(p): return json.loads(p.read_text(encoding="utf-8"))
haz=[rd(p) for p in (K/"hazards").glob("*.json")]
queries={
 "combustible_clutter":[r"可燃.*(杂物|纸箱|包装|堆积|堆放)",r"(纸箱|包装物|衣物|塑料袋).*(堆积|堆放)"],
 "dust_air_blow":[r"压缩空气.*(粉尘|积尘|清扫|吹扫)",r"(粉尘|积尘).*(压缩空气|吹扫)"],
 "insulating_ppe_test":[r"绝缘(鞋|靴|手套).*(检测|试验|检验|合格)",r"(检测|试验).*(绝缘鞋|绝缘靴|绝缘手套)"],
 "cylinder_fall":[r"气瓶.*(防倾倒|固定|倾倒)",r"(防倾倒|固定).*气瓶"],
 "press_light_curtain":[r"(冲压|压力机|剪板).*光电",r"光幕.*(失效|联锁|防护)"],
 "sling_marking":[r"(吊索|吊装带|吊具).*(载荷|吨位|标识|标志)",r"(额定|工作载荷).*(吊索|吊具|吊装带)"],
 "smoke_window":[r"(排烟窗|自然排烟).*(手动|开启|遮挡)",r"手动开启装置.*排烟"],
 "fire_door_wrong":[r"(普通木门|防火门).*(防火分隔|耐火|产品标识)",r"应设置防火门"],
 "flame_failure":[r"(熄火保护|熄火安全).*(装置|失效|有效)",r"燃具.*熄火"],
 "splash_socket":[r"(防溅|防水).*(插座|开关)",r"(潮湿|厨房|水).*(插座).*(防溅|防水)"],
 "socket_loose":[r"(插座|开关).*(未固定|松动|面板缺失|面板缺少)",r"(未固定|面板缺失).*插座"],
 "kitchen_grease":[r"(油烟|烟道|排油烟).*(清洗|油污)",r"(清洗).*(油烟|烟道)"],
 "slippery_floor":[r"(地面).*(湿滑|防滑|摔倒)",r"(湿滑).*(地面|通道)"],
 "gas_detector_location":[r"(可燃气体|燃气).*(探测器|报警器).*(位置|距离|高|低)",r"(探测器|报警器).*(释放源|0\.3m|安装位置)"],
 "emergency_light_power":[r"(应急照明|疏散照明).*(供电|电源|断电|插头)",r"(电源|供电).*(应急照明|疏散照明)"],
 "breaker_barrier":[r"(隔弧板|相间隔板|绝缘隔板).*(缺失|脱落|未安装)",r"断路器.*隔板"],
 "exit_locked_sign":[r"(安全出口).*(上锁|锁闭).*(标志|指示)",r"(安全出口).*(标志|指示).*(上锁|锁闭)"],
 "unattended_patrol":[r"(无人值守|无人看护).*(巡查|巡检|看护)",r"(仓储|仓库).*(巡查|值守)"],
 "outdoor_ad":[r"(广告|招牌|外立面).*(破损|松脱|固定)",r"(户外广告|招牌).*(安全|松动)"],
}
out={}
for name,pats in queries.items():
    rs=[]
    for h in haz:
        text=" ".join([h.get("title",""),h.get("description","")," ".join(h.get("keywords") or [])," ".join(h.get("aliases") or [])])
        if any(re.search(p,text,re.I) for p in pats):
            rs.append({"id":h["id"],"title":h.get("title"),"lifecycle":h.get("lifecycle"),"category":h.get("category"),"description":h.get("description")})
    out[name]=rs
print(json.dumps({k:len(v) for k,v in out.items()},ensure_ascii=False,indent=2))
Path("/tmp/commerce-gap-search.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
