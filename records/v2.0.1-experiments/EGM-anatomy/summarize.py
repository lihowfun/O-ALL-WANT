"""Compute report tables from reconciled accounting and existing quality rows."""
import argparse,json,collections,statistics
from pathlib import Path
from anatomy import zero,add
p=argparse.ArgumentParser();p.add_argument('--records',required=True,type=Path);a=p.parse_args();d=json.loads(Path('anatomy.json').read_text());out={}
for cell,scope in [('claude','primary'),('codex','primary'),('claude','completed'),('codex','completed'),('claude','plan'),('claude','defects'),('codex','defects')]:
 rs=[r for r in d['runs'] if r['cell']==cell and (r['case']=='plan-review' if scope=='plan' else (r['primary'] and r['case'] not in ('registry','sessions','supplier','dashboard')) if scope=='defects' else r['primary'] if scope=='primary' else r['status']=='completed')];b=collections.defaultdict(zero);tot=zero();un=zero();parent=zero();readstats=collections.Counter();repeatstats=collections.Counter()
 for r in rs:
  add(tot,r['total']);add(un,r['unattributed'])
  for v in r['buckets']:
   role='parent' if v['agent']=='parent' else 'subagents';add(b[(v['stage'],role)],v)
   if role=='parent':add(parent,v)
  reads=[x for x in r['reads'] if x['kind']=='Read'];byfile=collections.Counter(x['file'] for x in reads)
  for f,n in byfile.items():readstats[f]+=n;repeatstats[f]+=max(0,n-1)
 stages=[dict(stage=s,role=role,**v) for (s,role),v in sorted(b.items())]
 tail=zero()
 for x in stages:
  if x['stage'] in ('S6','S7','S8','S9','final'):add(tail,x)
 # Bound tail conservatively by stage classification, excluding missing phase / outputs.
 known_s5prep=zero()
 for x in stages:
  if x['stage'] in ('S5','prep'):add(known_s5prep,x)
 trimmed=zero()
 for x in stages:
  if x['stage'] in ('S5','S6','S7','S8'):add(trimmed,x)
 out[f'{cell}:{scope}']=dict(runs=len(rs),total=tot,unattributed=un,stages=stages,parent=parent,tail_lower=tail,tail_upper=sum(tot.values())-sum(known_s5prep.values()),preset3_removable_work=trimmed,reads=dict(readstats),repeat_reads=dict(repeatstats))
 print(cell,scope,'TOTAL',tot,'PARENT',parent,'TAIL',sum(tail.values()),'UPPER',out[f'{cell}:{scope}']['tail_upper'],'PRESET3_REMOVE',sum(trimmed.values()),'UN',un)
 print('stage role cache other')
 for x in stages:print(x['stage'],x['role'],x['cache_read'],x['other'])
 print('reads',readstats.most_common(8))
quality={}
for cell in ('claude','codex'):
 rows=[json.loads(l) for l in (a.records/f'v2.0.1-experiments/X2/results/{cell}-rows.jsonl').read_text().splitlines()]
 for arm in ('N','E'):
  rs=[r for r in rows if r['arm']==arm and r['id'] not in ('events','clean')];quality[f'{cell}:{arm}']={'median':statistics.median(r['tokens_total'] for r in rs),'total':sum(r['tokens_total'] for r in rs)}
out['quality_cost']=quality
Path('summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
