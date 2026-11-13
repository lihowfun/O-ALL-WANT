"""Read saved stage reports for provenance tracing; no grading is performed."""
import argparse,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--records',required=True,type=Path);p.add_argument('--scratch',required=True,type=Path);p.add_argument('--cell',required=True);p.add_argument('--cases',default='');p.add_argument('--full',action='store_true');p.add_argument('--stage',default='zoom_out_report.md');a=p.parse_args()
s=json.loads((a.records/'v2.0.1-experiments/X2/frozen/spec.json').read_text())
rows=[json.loads(l) for l in (a.records/f'v2.0.1-experiments/X2/results/{a.cell}-rows.jsonl').read_text().splitlines()]
for row in rows:
 case=row['id']
 if row['arm']!='E' or case not in s['planned_primary'] or (a.cases and case not in a.cases.split(',')):continue
 r=s['rubric'][case]
 if not r['critical'] and not r['major']:continue
 print('\nCASE',a.cell,case, '|'.join(f'{k[0].upper()}{i+1}:{x}' for k in ('critical','major') for i,x in enumerate(r[k])))
 paths=list((a.scratch/'x2/runs').glob(f"{a.cell}-*/raw/E-{case}.a{row['attempt']}-review_out/{a.stage}"))
 for path in paths:
  t=path.read_text();print('TRACE',str(path.relative_to(a.scratch)))
  if a.full: print(t)
  else:
   for i,line in enumerate(t.splitlines(),1):
    if re.search(r'^#{1,6} |^\*\*|^\d+[.)] |^\|',line):print(i,line[:600])
