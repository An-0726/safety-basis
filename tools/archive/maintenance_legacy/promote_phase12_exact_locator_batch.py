# -*- coding: utf-8 -*-
"""Promote the Phase 12 exact-locator candidates with self-contained duties."""
from __future__ import annotations
import argparse, hashlib, json, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KNOW, DOCS = ROOT / "knowledge", ROOT / "docs"
sys.path.insert(0, str(ROOT / "tools" / "v4"))
from canonical import content_hash
from release_gate_core import evaluate_release_gate

AS_OF = "2026-09-18"
REVIEWER = "Codex PHASE12 exact-locator review 20260918"
PROMOTE = {
    "H_0472DC58091F4C30A2007DCB2B": ("C_FA780CB453964F88B50E9BFE82", "安全生产法第二十九条直接要求从业人员了解、掌握安全技术特性并接受专门培训。"),
    "H_317326A8B80648F4A57D50755D": ("C_JS140_十六", "江苏省生产经营单位安全风险管理条例第十六条直接要求公示较大以上安全风险信息。"),
    "H_68B4D4FA3376550BFD0C19FAC7_1": ("C_0361BBA9D7060472D4D7557C7E", "消防法相关条款直接要求公共消防设施保持完好有效。"),
    "H_6DC0BB9AF6BB4D2A9EA6F293CA": ("C_JS140_十六", "江苏省生产经营单位安全风险管理条例第十六条直接要求公示信息真实、准确。"),
    "H_70CF6BE6FCDB433192C9456223": ("C_GB50187_5_1_4", "GB 50187-2012第5.1.4条直接规定厂区通道宽度应满足运输、消防和安全要求。"),
    "H_71323E2862E5D3955E3DE6DE76_1": ("C_71323E2862E5D3955E3DE6DE76", "安全生产法相关条款直接规定建立健全全员安全生产责任制和规章制度。"),
    "H_71323E2862E5D3955E3DE6DE76_2": ("C_71323E2862E5D3955E3DE6DE76", "安全生产法相关条款直接规定新兴行业领域单位落实全员安全生产责任制。"),
    "H_A49CD5CCAE8D45A3A4015F1AD1": ("C_GB50187_3_0_9", "GB 50187-2012第3.0.9条直接规定厂址选择和发展余地要求。"),
    "H_BB5D261648AF4AFE8664310C13": ("C_GB50187_5_1_1", "GB 50187-2012第5.1.1条直接规定总平面布置应结合场地条件经技术经济比较确定。"),
    "H_D9B99E085E45534257B178AC2D_1": ("C_D9B99E085E45534257B178AC2D", "安全生产法相关条款直接规定安全评价、认证、检测、检验机构资质条件。"),
    "H_E37EF6102AE03060EDCB51D7": ("C_GB45067_4_1", "GB 45067-2024第4.1条直接规定特种设备事故后检查消除隐患及许可、参数和适用范围要求。"),
}

def load(rel):
    out={}
    for p in (KNOW/rel).glob('*.json'):
        x=json.loads(p.read_text(encoding='utf-8')); out[x.get('id') or x.get('entityId') or p.stem]=x
    return out
def dump(path,x):
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--apply',action='store_true'); a=ap.parse_args()
    hz,cl,lk,cr=load('hazards'),load('clauses'),load('links'),load('reviews/clauses')
    counts=Counter(x.get('lifecycle') for x in hz.values())
    if counts != Counter({'active':1484,'proposed':445,'superseded':86}): raise RuntimeError(f'baseline drift {counts}')
    active_by_clause={}
    for l in lk.values():
        if l.get('lifecycle')=='active' and hz.get(l.get('hazardId'),{}).get('lifecycle')=='active': active_by_clause.setdefault(l.get('clauseId'),[]).append(l.get('hazardId'))
    for hid,(cid,_) in PROMOTE.items():
        if hz.get(hid,{}).get('lifecycle')!='proposed': raise RuntimeError(f'not proposed {hid}')
        c=cl.get(cid); r=cr.get(cid,{})
        if not c or c.get('lifecycle')!='active' or r.get('decision')!='verified' or r.get('reviewedContentHash')!=content_hash(c): raise RuntimeError(f'clause review {cid}')
        if cid in active_by_clause and hid not in active_by_clause[cid]: raise RuntimeError(f'existing active duplicate {cid}: {active_by_clause[cid]}')
    if not a.apply:
        print(json.dumps({'mode':'dry-run','reviewed':len(PROMOTE),'promotable':len(PROMOTE),'proposedAfter':445-len(PROMOTE)},ensure_ascii=False,indent=2)); return
    out=[]
    for hid,(cid,reason) in PROMOTE.items():
        h=dict(hz[hid]); h['lifecycle']='active'; h['mode']='direct'; h.pop('proposalStatus',None); h.pop('sourceRow',None); h.pop('revisionState',None)
        marker='【PHASE 12 2026-09-18】已复核现行条款原文、隐患对象和适用范围，建立当前direct关联。'; note=str(h.get('note') or '').rstrip(); h['note']=(note+'\n'+marker).strip()
        dump(KNOW/'hazards'/f'{hid}.json',h)
        dump(KNOW/'reviews'/'hazards'/f'{hid}.json',{'checkedAt':AS_OF,'decision':'verified','entityId':hid,'entityType':'hazard','evidenceRefs':['E_PHASE12_EXACT_LOCATOR'],'reason':reason,'reviewType':'content','reviewedContentHash':content_hash(h),'reviewer':REVIEWER})
        lid='K_PHASE12_EXACT_'+hashlib.sha1((hid+'|'+cid).encode()).hexdigest()[:20].upper(); link={'id':lid,'hazardId':hid,'clauseId':cid,'role':'direct','legacyRole':'直接依据','applicability':'按所引现行法规/标准条款及其适用范围判断。','jurisdictionCode':'CN','lifecycle':'active','priority':10,'requirementId':'','reason':reason}; dump(KNOW/'links'/f'{lid}.json',link); dump(KNOW/'reviews'/'links'/f'{lid}.json',{'checkedAt':AS_OF,'contextHashes':{'clause':content_hash(cl[cid]),'hazard':content_hash(h)},'decision':'verified','entityId':lid,'entityType':'link','evidenceRefs':['E_PHASE12_EXACT_LOCATOR'],'reason':reason,'reviewType':'applicability','reviewedContentHash':content_hash(link),'reviewer':REVIEWER}); out.append({'hazardId':hid,'clauseId':cid,'linkId':lid,'title':h.get('title'),'reason':reason})
    m=json.loads((KNOW/'manifest.json').read_text(encoding='utf-8')); m.setdefault('batches',[]).append({'id':'phase12-exact-locator-batch-20260918','hazardsPromoted':len(PROMOTE),'linksAdded':len(PROMOTE),'candidatesReviewed':len(PROMOTE),'selection':'self-contained exact-locator duties; generic, conditional, duplicate and cross-standard cases retained proposed'}); m['asOf']=AS_OF; m['counts']['links']=len(list((KNOW/'links').glob('*.json'))); dump(KNOW/'manifest.json',m)
    rows=[{'recordType':'metadata','schemaVersion':1,'asOf':AS_OF,'baselineProposed':445,'reviewed':len(PROMOTE),'promoted':len(PROMOTE),'proposedAfter':445-len(PROMOTE),'privateSqliteModified':False}]+[{**x,'outcome':'promoted_active','lifecycleAfter':'active','reasonCode':'verified_direct_exact_locator'} for x in out]; (DOCS/'phase12-exact-locator-disposition.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in rows),encoding='utf-8',newline='\n')
    gate=evaluate_release_gate(KNOW); missing=sorted(set(PROMOTE)-set(gate.eligible_hazards));
    if missing: raise RuntimeError(f'Gate failed {missing}')
    print(json.dumps({'mode':'apply','promoted':len(PROMOTE),'proposedAfter':445-len(PROMOTE),'gateEligible':True},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
