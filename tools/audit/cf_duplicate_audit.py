#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, re
from difflib import SequenceMatcher
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
H=ROOT/'knowledge'/'hazards'

def norm(s):
    s=str(s or '').lower()
    s=re.sub(r'[^0-9a-z\u4e00-\u9fff]+','',s)
    return s

def grams(s,n=2):
    s=norm(s)
    return {s[i:i+n] for i in range(max(0,len(s)-n+1))}

def sim(a,b):
    ta=norm(a.get('title')); tb=norm(b.get('title'))
    da=norm(a.get('description')); db=norm(b.get('description'))
    title=SequenceMatcher(None,ta,tb).ratio()
    desc=SequenceMatcher(None,da,db).ratio()
    ga,gb=grams((a.get('title') or '')+(a.get('description') or '')),grams((b.get('title') or '')+(b.get('description') or ''))
    jac=len(ga&gb)/len(ga|gb) if ga|gb else 0
    return 0.5*title+0.3*desc+0.2*jac

rows=[]
for p in H.glob('*.json'):
    o=json.loads(p.read_text(encoding='utf-8'))
    rows.append(o)
byid={x['id']:x for x in rows if x.get('id')}
targets=[x for x in rows if str(x.get('id','')).startswith('H_CF_')]
others=[x for x in rows if not str(x.get('id','')).startswith('H_CF_') and x.get('lifecycle')!='superseded']

print('CF_DUPLICATE_AUDIT_BEGIN')
for t in sorted(targets,key=lambda x:x['id']):
    scored=sorted(((sim(t,o),o) for o in others), key=lambda x:x[0], reverse=True)[:6]
    print(json.dumps({
      'id':t['id'],'title':t.get('title'),'lifecycle':t.get('lifecycle'),
      'top':[{'score':round(s,4),'id':o['id'],'title':o.get('title'),'lifecycle':o.get('lifecycle'),'category':o.get('category')} for s,o in scored]
    },ensure_ascii=False))
print('CF_DUPLICATE_AUDIT_END')
