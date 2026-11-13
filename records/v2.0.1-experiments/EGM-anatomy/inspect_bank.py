"""Read-only inventory of historical versions, headings, and review metadata."""
import argparse,subprocess,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('records',type=Path);a=p.parse_args();repo=a.records.parent
paths=['v2.0.1-experiments/capability/PLAN.md','v2.0.1-experiments/H1/PREREG.md','v2.0.1-experiments/FIXCHECK/FIXCHECK.md']
out=[]
for path in paths:
 log=subprocess.check_output(['git','-C',str(repo),'log','--all','--format=%H %s','--','records/'+path],text=True)
 versions=[]
 for line in log.splitlines():
  commit,title=line.split(' ',1);data=subprocess.check_output(['git','-C',str(repo),'show',commit+':records/'+path]);versions.append(dict(commit=commit,title=title,lines=len(data.splitlines()),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
 out.append(dict(path='records/'+path,versions=versions))
for path in ['plan-review-2026-11-07/draft-as-reviewed.md','v2.0.1-experiments/H1/D45-review.md']:
 data=(a.records/path).read_bytes();out.append(dict(path='records/'+path,lines=len(data.splitlines()),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
Path('bank-inventory.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
for x in out:print(json.dumps(x,ensure_ascii=False))
spec=json.loads((a.records/'v2.0.1-experiments/X2/frozen/spec.json').read_text());print('SPEC',list(spec));print('RUBRIC',json.dumps(spec['rubric']['flags'],ensure_ascii=False))
