"""Exact historical views for earlier tests only; never publication or Gate policy.

Only five frozen K judgments and the one quarantined C lifecycle are restored.
Unknown additions, losses and unexpected mutations remain observable or raise.
"""
import copy
import hashlib
import json
from pathlib import Path
F=json.loads((Path(__file__).parent/'fixtures/training_citation_repair_20261003.json').read_text())

def pre_training_gate(result):
 day=str(getattr(result,'as_of',''))
 if day not in F['gateSnapshots']:return copy.deepcopy(result)
 delta=F['gateSnapshots'][day]['changedLinks'];old=copy.deepcopy(result)
 # Independent miniature fixtures contain none of this real-source cohort.
 if not set(delta)&set(result.links):return old
 for kid,row in delta.items():
  if result.links.get(kid)!=row['after'] or kid not in result.eligible_links:
   raise AssertionError('unexpected training citation judgment or membership: '+kid)
  old.links[kid]=copy.deepcopy(row['before'])
 return old

def pre_training_inventory(kind,rows):
 out=[]
 for ident,state in rows:
  if kind=='clauses' and ident==F['badClauseId']:
   if state!='proposed':raise AssertionError('unexpected quarantined training clause lifecycle')
   state='active'
  out.append((ident,state))
 return sorted(out)

def pre_training_source_hashes(hashes):
 out=dict(hashes)
 for row in F['entities']:
  path=row['path']
  if path not in out:continue
  if out[path]!=row['fileSha256']:raise AssertionError('unexpected repaired training source: '+path)
  if hashlib.sha256(row['beforeFileText'].encode()).hexdigest()!=row['oldFileSha256']:
   raise AssertionError('corrupt historical training snapshot: '+path)
  out[path]=row['oldFileSha256']
 return out
