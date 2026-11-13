"""Print selected trace metadata or review snippets without executing trace actions."""
import argparse,json,collections
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('path',type=Path);p.add_argument('--mode',choices=['meta','reports','rubric'],default='meta');a=p.parse_args()
if a.mode=='meta':
 es=[json.loads(l) for l in a.path.read_text().splitlines()];print(collections.Counter((e.get('type'),e.get('subtype')) for e in es))
 for i,e in enumerate(es):
  if e.get('type')=='system' and e.get('subtype') not in ('init','local_command'):print(i+1,str(e)[:1200])
  if e.get('type')=='user' and 'tool_use_result' in e and isinstance(e['tool_use_result'],dict) and e['tool_use_result'].get('isAsync'):print('async',i+1,{k:v for k,v in e['tool_use_result'].items() if k in ('agentId','outputFile')})
elif a.mode=='rubric':
 s=json.loads(a.path.read_text())
 for case in s['planned_primary']:
  r=s['rubric'][case]
  print(case, ' | '.join(f'{k[0].upper()}{i+1}: {x}' for k in ('critical','major') for i,x in enumerate(r[k])))
else:
 for path in sorted(a.path.glob('*report.md')):
  print(path.name);print(path.read_text()[:24000])
