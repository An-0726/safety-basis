#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
KNOW=ROOT/'knowledge'
sys.path.insert(0,str(ROOT/'tools'/'v4'))
from canonical import content_hash

STAMP='2026-09-21T00:55:00+08:00'
MERGES={
 'H_CF_GEN_04':'H036',
 'H_CF_GEN_06':'H_F63729C889F642C8BBA2F263F0',
 'H_CF_GEN_28':'H040',
 'H_CF_MAJOR_02':'H_FCB_16_1',
 'H_CF_MAJOR_03':'H_FCB_18_1',
 'H_CF_MAJOR_05':'H_48B66BAC_11_1',
 'H_CF_MAJOR_07':'H_CC076DB8C16B4C058C3009E25A',
}
ALL=[f'H_CF_GEN_{i:02d}' for i in range(1,29)]+[f'H_CF_MAJOR_{i:02d}' for i in range(1,9)]

def rd(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def wr(p,o): Path(p).write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

for hid in ALL:
    hp=KNOW/'hazards'/f'{hid}.json'
    h=rd(hp)
    hrp=KNOW/'reviews'/'hazards'/f'{hid}.json'
    hr=rd(hrp)
    pattern='K_CF_'+hid.replace('H_CF_','')+'_*.json'
    links=sorted((KNOW/'links').glob(pattern))
    if len(links)!=1:
        raise SystemExit(f'{hid}: expected exactly one PR70 link, got {len(links)}')
    lp=links[0]; l=rd(lp)
    lrp=KNOW/'reviews'/'links'/f"{l['id']}.json"; lr=rd(lrp)

    if hid in MERGES:
        target=MERGES[hid]
        if not (KNOW/'hazards'/f'{target}.json').is_file():
            raise SystemExit(f'missing merge target {target}')
        h['lifecycle']='superseded'
        h['mergedInto']=target
        prefix=((h.get('note') or '').strip()+'\n\n') if (h.get('note') or '').strip() else ''
        h['note']=prefix+f'2026-09-21工程审计：与现有隐患 {target} 重复或实质重叠，保留Stable ID并归并。'
        hr['decision']='verified'
        hr['reason']=f'工程审计确认本条与 {target} 重复/实质重叠；采用superseded+mergedInto保留历史，不再独立发布。'
        l['lifecycle']='superseded'
        lr['decision']='superseded'
        lr['reason']=f'源隐患 {hid} 已归并至 {target}，原PR #70关联仅保留历史，不参与发布。'
    else:
        h['lifecycle']='proposed'
        h['mode']='candidate'
        h['mergedInto']=None
        prefix=((h.get('note') or '').strip()+'\n\n') if (h.get('note') or '').strip() else ''
        h['note']=prefix+'2026-09-21工程审计：PR #70批量导入的direct/verified依据不足或描述含复合条件，暂降为proposed；待逐条取得直接技术条款和完整适用条件后再转正。'
        hr['decision']='pending'
        hr['reason']='工程审计未确认当前PR #70关联可以直接支持本隐患全部构成要件；保留候选用于检索，不进入正式发布。'
        lr['decision']='rejected'
        lr['reason']='PR #70批量关联未证明该条款可直接支持本隐患全部构成要件；关联拒绝，后续如有合格直接依据应新建/重新审核。'

    wr(hp,h); wr(lp,l)
    hr['reviewedContentHash']=content_hash(h); hr['checkedAt']=STAMP; hr['reviewer']='ChatGPT / Engineering Audit'
    wr(hrp,hr)
    lr['reviewedContentHash']=content_hash(l)
    ctx=lr.get('contextHashes') or {}
    lr['contextHashes']={'hazard':content_hash(h),'clause':ctx.get('clause'),'link':content_hash(l)}
    lr['checkedAt']=STAMP; lr['reviewer']='ChatGPT / Engineering Audit'
    wr(lrp,lr)

m=rd(KNOW/'manifest.json')
lc=Counter(rd(p).get('lifecycle') for p in (KNOW/'hazards').glob('*.json'))
m['activeHazards']=lc['active'];m['proposedHazards']=lc['proposed'];m['supersededHazards']=lc['superseded']
m['lifecycle']={k:lc[k] for k in ('active','proposed','superseded')}
m['asOf']='2026-09-21'
if not any(x.get('id')=='pr70-disposition-20260921' for x in m.setdefault('batches',[])):
    m['batches'].append({'id':'pr70-disposition-20260921','candidatesReviewed':36,'hazardsMerged':len(MERGES),'proposedRetained':36-len(MERGES),'selection':'Engineering audit of PR #70 Changfeng generated hazards: clear duplicates merged via Stable ID preservation; all remaining records retained as proposed until direct technical basis and applicability are independently verified.'})
wr(KNOW/'manifest.json',m)
print(json.dumps({'merged':MERGES,'lifecycle':m['lifecycle']},ensure_ascii=False,indent=2))
