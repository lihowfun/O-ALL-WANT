"""Inspect completion accounting keys, omitting content and paths."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('path',type=Path);a=p.parse_args()
for n,l in enumerate(a.path.read_text().splitlines(),1):
 e=json.loads(l)
 if e.get('subtype')=='task_notification':print(n,'notification',list(e),{k:v for k,v in e.items() if k in ('usage','total_tokens','tool_use_id','task_id')})
 if e.get('type')=='user' and isinstance(e.get('tool_use_result'),dict) and 'totalTokens' in e['tool_use_result']:print(n,'toolresult',e['tool_use_result']['totalTokens'],e['tool_use_result'].get('usage'))
 if e.get('type')=='result':print(n,'result',e.get('parent_tool_use_id'),e.get('session_id'),e.get('usage'))
