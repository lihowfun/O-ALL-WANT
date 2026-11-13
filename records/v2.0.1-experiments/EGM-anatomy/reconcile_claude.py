"""Recover Claude completion usage omitted or partial in stream message blocks.
Cache inputs are per deduplicated message; completion counters repair output totals.
Parent result usage is exact per root turn, but output cannot be split within a turn.
"""
import argparse,json,collections
from pathlib import Path
from anatomy import read_jsonl,tokens,zero,add,stage_for
p=argparse.ArgumentParser();p.add_argument('--scratch',required=True,type=Path);a=p.parse_args();data=json.loads(Path('anatomy.json').read_text())
for r in data['runs']:
 if r['cell']!='claude':continue
 es=read_jsonl(a.scratch/r['trace']);parent=zero();details=[];tools={};z=st=0;last_msg={};sync_finals={}
 for n,e in es:
  if e.get('type')=='assistant':
   par=e.get('parent_tool_use_id');m=e.get('message',{})
   if par and m.get('usage'):last_msg[par]=dict(usage=tokens(m['usage']),line=n)
   for b in m.get('content',[]):
    if b.get('type')=='tool_use' and b.get('name') in ('Agent','Task'):
     inp=b.get('input',{});desc=inp.get('subagent_type','')+' '+inp.get('description','');s=stage_for(desc,z,st)
     if 'zoom' in desc:z+=1
     if 'style' in desc:st+=1
     tools[b['id']]={'stage':s,'agent':inp.get('subagent_type') or inp.get('description','unknown')}
  if e.get('type')=='result' and e.get('usage'):add(parent,tokens(e['usage']))
  if e.get('type')=='user' and isinstance(e.get('tool_use_result'),dict) and e['tool_use_result'].get('usage') and 'totalTokens' in e['tool_use_result']:
   tids=[b.get('tool_use_id') for b in e.get('message',{}).get('content',[]) if b.get('type')=='tool_result']
   if tids:sync_finals[tids[0]]=dict(usage=tokens(e['tool_use_result']['usage']),line=n)
 for n,e in es:
  if e.get('subtype')!='task_notification':continue
  tid=e['tool_use_id'];agent=tools.get(tid,dict(stage='unknown',agent='unknown'));last=last_msg.get(tid);count=e.get('usage',{}).get('total_tokens',0)
  if tid in sync_finals:
   correction=sync_finals[tid]['usage'];method='sync final request absent from assistant stream'
  elif last:
   correction={'cache_read':0,'other':count-sum(last['usage'].values())};method='async final output correction from completion counter'
  else:correction={'cache_read':0,'other':0};method='missing last message'
  details.append(dict(line=n,stage=agent['stage'],agent=agent['agent'],last_request_logical=count,correction=correction,method=method))
  r['buckets'].append(dict(stage=agent['stage'],agent=agent['agent'],**correction,source='completion'))
 old_parent=zero()
 for b in r['buckets']:
  if b['agent']=='parent':add(old_parent,b)
 correction={k:parent[k]-old_parent[k] for k in parent}
 r['buckets'].append(dict(stage='parent_output_unallocated',agent='parent',**correction,source='root turn usage'))
 obs=zero()
 for b in r['buckets']:add(obs,b)
 r['observed']=obs;r['unattributed']={k:r['total'][k]-obs[k] for k in obs}
 r['claude_reconciliation']={'parent_result_usage':parent,'parent_stream_correction':correction,'completion_counters':details,'reconciliation_error':sum(r['unattributed'].values())}
 print(r['case'],r['status'],'parent',sum(parent.values()),'unattributed',r['unattributed'])
data.pop('summaries',None)
data['reconciled']=True
data['summary_file']='summary.json'
Path('anatomy.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
