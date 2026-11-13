"""Offline consistency and privacy checks against independent recorded run totals."""
import argparse,json,hashlib,platform,sys,re,collections
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--scratch',required=True,type=Path);p.add_argument('--records',required=True,type=Path);a=p.parse_args();checks=[]
def check(name,condition):
 if not condition:raise AssertionError(name)
 checks.append(name)
d=json.loads(Path('anatomy.json').read_text());f=json.loads(Path('finding-provenance.json').read_text());s=json.loads(Path('summary.json').read_text());cost=json.loads(Path('design-costs.json').read_text())
check('49 E traces retained including pilots and interruptions',len(d['runs'])==49)
check('44 completed X2 E traces',sum(r['status']=='completed' for r in d['runs'])==44)
for r in d['runs']:
 total={k:sum(b[k] for b in r['buckets'])+r['unattributed'][k] for k in ('cache_read','other')}
 check('Reconcile '+r['trace'],total==r['total'])
 check('Nonnegative accounting '+r['trace'],all(b[k]>=0 for b in r['buckets'] for k in ('cache_read','other')) and all(v>=0 for v in r['unattributed'].values()))
for src in d['sources']:check('Source SHA '+src['locator'],hashlib.sha256((a.scratch/src['locator']).read_bytes()).hexdigest()==src['sha256'])
for cell in ('claude','codex'):
 rows=[json.loads(l) for l in (a.records/f'v2.0.1-experiments/X2/results/{cell}-rows.jsonl').read_text().splitlines()]
 wanted={(x['id'],x['attempt']):x for x in rows if x['arm']=='E'}
 for r in [r for r in d['runs'] if r['cell']==cell and r['status']=='completed']:
  old=wanted[(r['case'],r['attempt'])];check('Original totals '+cell+':'+r['case'],sum(r['total'].values())==old['tokens_total'] and r['total']['other']==old['tokens_noncache'])
 check('All completed source files unchanged '+cell,all(not x['sources_changed'] for x in rows if x['arm']=='E'))
check('96 distinct provenance entries',len(f)==96 and len({(x['cell'],x['case'],x['defect']) for x in f})==96)
check('Every first-return anchor located',all(x['excerpt'] and x['first_observable_review_stage']=='S5' for x in f))
for cell,n in [('claude',48),('codex',47)]:
 for grader in ('opus','codex'):check('Existing final grade '+cell+':'+grader,sum(x['final_existing_grades'][grader]=='detected' for x in f if x['cell']==cell)==n)
check('Codex complete stage totals reconcile',all(sum(x['unattributed'].values())==0 for x in d['runs'] if x['cell']=='codex' and x['status']=='completed'))
check('Claude primary source total',sum(s['claude:primary']['total'].values())==33413778)
check('Codex primary source total',sum(s['codex:primary']['total'].values())==58994320)
check('Plan source total',sum(s['claude:plan']['total'].values())==18480203)
check('Three-arm conditional Claude budget under 30M',all(x['three_arm_total'][1]<30000000 for x in cost['per_document'] if x['cell']=='claude'))
check('Four-arm conditional Claude budget over 30M',all(x['four_arm_total'][0]>30000000 for x in cost['per_document'] if x['cell']=='claude'))
check('Generated numerical appendix matches report',Path('ANATOMY.md').read_text().split('## 數字附錄（由 `render_tables.py` 生成）\n',1)[1].strip()==Path('TABLES.generated.md').read_text().strip())
for path in list(Path('.').glob('*.json'))+list(Path('.').glob('*.md')):
 text=path.read_text();check('No local account/project paths '+path.name,not re.search(r'/(?:mnt|home|tmp)/|akuo|creator_account_id|creator_user_id',text))
for path in Path('.').glob('*.py'):compile(path.read_text(),str(path),'exec')
check('All retained scripts compile without bytecode',True)
result={'platform':platform.platform(),'python':sys.version.split()[0],'checks':len(checks),'result':'PASS','source_hashes_checked':len(d['sources']),'e_traces':len(d['runs']),'provenance_items':len(f),'limitations':'Checks establish accounting and source consistency, not model quality, host discovery, or efficacy of any proposed change.'}
Path('validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
