"""Locate already-graded defects in first reviewer returns, without regrading.
Regex anchors are manually chosen provenance aids; they do not assign quality labels.
"""
import argparse,json,re,collections
from pathlib import Path
from anatomy import read_jsonl,stage_for
p=argparse.ArgumentParser();p.add_argument('--scratch',required=True,type=Path);p.add_argument('--records',required=True,type=Path);a=p.parse_args();data=json.loads(Path('anatomy.json').read_text());anchors=json.loads(Path('finding_anchors.json').read_text());out=[]
grades={}
for fam in ('opus','codex'):
 for _,g in read_jsonl(a.records/f'v2.0.1-experiments/X2/results/main-grades-{fam}.jsonl'):grades[(fam,g['cell'],g['arm'],g['id'])]=g
for run in data['runs']:
 if run['status']!='completed' or run['case'] not in anchors:continue
 path=a.scratch/run['trace'];returns=[]
 if run['cell']=='claude':
  es=read_jsonl(path);stage_map={};z=st=0
  for n,e in es:
   if e.get('type')=='assistant':
    for b in e.get('message',{}).get('content',[]):
     if b.get('type')=='tool_use' and b.get('name') in ('Agent','Task'):
      inp=b.get('input',{});desc=inp.get('subagent_type','')+' '+inp.get('description','');s=stage_for(desc,z,st)
      if 'zoom' in desc:z+=1
      if 'style' in desc:st+=1
      stage_map[b['id']]=s
   if e.get('subtype')=='task_notification' and stage_map.get(e.get('tool_use_id'))=='S5':returns.append((n,e.get('summary',''),run['trace']))
 else:
  for rp in path.with_name(path.stem+'-rollouts').glob('*.jsonl'):
   es=read_jsonl(rp);m=es[0][1]['payload']
   if stage_for(m.get('agent_path',''))!='S5' or not m.get('parent_thread_id'):continue
   for n,e in es:
    pl=e.get('payload',{})
    if e.get('type')=='response_item' and pl.get('type')=='message' and pl.get('role')=='assistant' and pl.get('phase')=='final_answer':
     txt='\n'.join(b.get('text','') for b in pl.get('content',[]));returns.append((n,txt,str(rp.relative_to(a.scratch))))
 if not returns:raise ValueError(('Missing S5 return',run['cell'],run['case']))
 n,txt,loc=returns[-1]
 for rid,pattern in anchors[run['case']].items():
  m=re.search(pattern,txt,re.I)
  quote=txt[max(0,m.start()-90):min(len(txt),m.end()+200)].replace('\n',' ') if m else None
  out.append(dict(cell=run['cell'],case=run['case'],defect=rid,first_observable_review_stage='S5' if m else None,locator=loc,line=n,anchor=pattern,excerpt=quote,final_existing_grades={f:('detected' if rid in grades[(f,run['cell'],'E',run['case'])]['detected'] else 'mentioned_only' if rid in grades[(f,run['cell'],'E',run['case'])]['mentioned_only'] else 'absent') for f in ('opus','codex')}))
  if not m:print('UNMATCHED',run['cell'],run['case'],rid,txt[:12000])
Path('finding-provenance.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print('entries',len(out),'located',sum(x['excerpt'] is not None for x in out))
