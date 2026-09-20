#!/usr/bin/env python3
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
K=ROOT/'knowledge'
TARGETS={'H_AD27C51EB8E840D5BA2F0365E0','H_F3E7D18DBD77459B983AB5CD06'}
def rd(p): return json.loads(p.read_text(encoding='utf-8'))
clauses={rd(p)['id']:rd(p) for p in (K/'clauses').glob('*.json')}
lvs={rd(p)['id']:rd(p) for p in (K/'law-versions').glob('*.json')}
laws={rd(p)['id']:rd(p) for p in (K/'laws').glob('*.json')}
link_reviews={}
for p in (K/'reviews'/'links').glob('*.json'):
    r=rd(p); link_reviews[r.get('entityId') or p.stem]=r
for p in sorted((K/'links').glob('*.json')):
    l=rd(p)
    if l.get('hazardId') not in TARGETS: continue
    c=clauses.get(l.get('clauseId'),{})
    lv=lvs.get(c.get('lawVersionId'),{})
    law=laws.get(lv.get('lawId'),{})
    r=link_reviews.get(l.get('id'),{})
    print(json.dumps({
      'hazardId':l.get('hazardId'),'linkId':l.get('id'),'linkLifecycle':l.get('lifecycle'),
      'role':l.get('role'),'clauseId':l.get('clauseId'),'clauseArticle':c.get('articlePath'),
      'quote':c.get('quote'),'lawVersionId':lv.get('id'),'lawName':law.get('canonicalName'),
      'documentNumber':lv.get('documentNumber'),'validityStatus':lv.get('validityStatus'),
      'effectiveDate':lv.get('effectiveDate'),'endDate':lv.get('endDate'),
      'reviewDecision':r.get('decision'),'reviewReason':r.get('reason')
    },ensure_ascii=False))