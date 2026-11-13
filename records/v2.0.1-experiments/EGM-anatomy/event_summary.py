"""Compute read repetition and scoped example recurrence from recorded tool events."""
import json,collections,argparse,re
from pathlib import Path
from anatomy import read_jsonl,stage_for
p=argparse.ArgumentParser();p.add_argument('--scratch',required=True,type=Path);a=p.parse_args();d=json.loads(Path('anatomy.json').read_text());out={}
for key in ('claude:primary','codex:primary','claude:plan'):
 cell,scope=key.split(':');rs=[r for r in d['runs'] if r['cell']==cell and (r['primary'] if scope=='primary' else r['case']=='plan-review')];total=sum(sum(r['total'].values()) for r in rs);parent=sum(sum(b[k] for k in ('cache_read','other')) for r in rs for b in r['buckets'] if b['agent']=='parent');st=collections.Counter();agents=collections.Counter()
 for r in rs:
  for b in r['buckets']:st[b['stage']]+=b['cache_read']+b['other'];agents[b['agent']]+=b['cache_read']+b['other']
 out[key]=dict(total=total,cache_percent=100*sum(r['total']['cache_read'] for r in rs)/total,parent_percent=100*parent/total,stage_percent={s:100*v/total for s,v in st.items()},top_agents=agents.most_common())
flags=next(r for r in d['runs'] if r['cell']=='claude' and r['case']=='flags');rds=collections.Counter((r['file'],r['agent']) for r in flags['reads'] if r['kind']=='Read');out['claude_flags_reads']=[dict(file=f,agent=ag,count=n) for (f,ag),n in sorted(rds.items()) if f in ('README.md','docs/design.md','src/flags.py')]
# Manual-example matching is an audit aid; no new quality score is computed.
es=read_jsonl(a.scratch/flags['trace']);matches=[]
for n,e in es:
 if e.get('subtype')=='task_notification':
  t=e.get('summary','');patt=r'get_global[^\n]{0,180}|KeyError[^\n]{0,180}|1,200[^\n]{0,180}|cross.tenant[^\n]{0,180}';m=re.search(patt,t,re.I)
  if m:matches.append({'line':n,'excerpt':m.group(0),'task_id':e.get('task_id')})
out['flags_repeat_evidence']=matches
Path('events.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
for k,v in out.items():print(k,json.dumps(v,ensure_ascii=False)[:4000])
