"""Summarize only existing X2 grades, preserving graders' recorded allegations."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--records',required=True,type=Path);a=p.parse_args();out={}
for fam in ('opus','codex'):
 gs=[json.loads(l) for l in (a.records/f'v2.0.1-experiments/X2/results/main-grades-{fam}.jsonl').read_text().splitlines()]
 for cell in ('claude','codex'):
  for arm in ('N','E'):
   sel=[g for g in gs if g['cell']==cell and g['arm']==arm and g['id'] not in ('events','clean')]
   out[f'{fam}:{cell}:{arm}']={'detected':sum(len(g['detected']) for g in sel),'unsupported':sum(g['unsupported'] for g in sel),'clean':{g['id']:g for g in sel if g['id'] in ('registry','sessions','supplier','dashboard')}}
Path('quality.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
for k,v in out.items():
 print(k,'detected',v['detected'],'unsupported',v['unsupported'])
 if k.endswith(':E'):
  for c,g in v['clean'].items():
   if g['unsupported'] or g.get('hard_negatives_violated'):print(c,json.dumps(g,ensure_ascii=False)[:3000])
