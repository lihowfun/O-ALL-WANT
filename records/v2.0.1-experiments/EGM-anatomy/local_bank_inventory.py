"""Measure recovered H1 v2 snapshots without copying their contents."""
import argparse,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--h1-review',required=True,type=Path);a=p.parse_args();out=[]
for name in ['PREREG.v2.md','AUTHOR_BRIEF_B.v2.md','AUTHOR_BRIEF_C.v2.md','h1_run.v2.py','h1_judge.v2.py']:
 b=(a.h1_review/name).read_bytes();out.append(dict(locator='h1-review/'+name,lines=len(b.splitlines()),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
Path('local-bank-inventory.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
