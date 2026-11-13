"""Read-only structural inspection; arguments are local inputs, never persisted."""
import argparse,json,collections
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args()
for path in sorted(a.root.glob('*a/raw/E-flags.a1.jsonl')):
 print(path.parent.parent.name,path.name)
 es=[json.loads(l) for l in path.read_text().splitlines()]
 if 'claude' in str(path):
  for i,e in enumerate(es):
   if e.get('type')=='assistant':
    for b in e.get('message',{}).get('content',[]):
     if b.get('type')=='tool_use' and b.get('name') in ('Agent','Task'):
      print(i+1,b['id'],b['input'].get('subagent_type'),b['input'].get('description'))
   if e.get('type')=='result': print('result',i+1,{k:v for k,v in e.items() if k in ('modelUsage','parent_tool_use_id','usage','total_cost_usd')})
   if e.get('type')=='user' and isinstance(e.get('tool_use_result'),dict) and 'totalTokens' in e['tool_use_result']:
    t=e['tool_use_result'];print('toolresult',i+1,str(t)[:350] if not isinstance(t,dict) else {k:v for k,v in t.items() if k in ('totalTokens','usage','totalToolUseCount')})
 else:
  for rp in sorted(path.with_name(path.stem+'-rollouts').glob('*.jsonl')):
   events=[json.loads(l) for l in rp.read_text().splitlines()];m=events[0]['payload'];ts=[e['payload']['info']['total_token_usage'] for e in events if e.get('type')=='event_msg' and e.get('payload',{}).get('type')=='token_count' and e['payload'].get('info')];print(rp.name,m.get('agent_path'),ts[-1] if ts else None)
