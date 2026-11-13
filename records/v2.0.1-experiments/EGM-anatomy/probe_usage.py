"""Compare Claude message identifiers, request identifiers, and final accounting."""
import argparse,json,collections
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('path',type=Path);a=p.parse_args();es=[json.loads(l) for l in a.path.read_text().splitlines()];d=collections.defaultdict(list)
for n,e in enumerate(es,1):
 if e.get('type')=='assistant':
  m=e['message'];d[(e.get('parent_tool_use_id'),m.get('id'))].append((n,e.get('request_id'),m.get('usage'),[(b.get('type'),b.get('name')) for b in m.get('content',[])]))
for (parent,mid),v in list(d.items())[:12]:
 print(parent,mid,'blocks',len(v),'requests',len(set(x[1] for x in v)))
 for x in v:print(x[0],x[1],{k:y for k,y in (x[2] or {}).items() if k.endswith('tokens')},x[3])
