"""Inspect assistant response metadata in a Codex rollout."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args()
for rp in a.folder.glob('*.jsonl'):
 es=[json.loads(l) for l in rp.read_text().splitlines()];m=es[0]['payload']
 if 'initial_zoom' not in m.get('agent_path',''):continue
 print(rp.name,m.get('agent_path'))
 for e in es:
  q=e.get('payload',{})
  if e['type']=='response_item' and q.get('role')=='assistant' and q.get('type')=='message':print({k:v for k,v in q.items() if k!='content'},str(q.get('content'))[:600])
