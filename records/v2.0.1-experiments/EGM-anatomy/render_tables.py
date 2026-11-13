"""Render numerical appendices from JSON. Does not modify prose reports."""
import json,collections
from pathlib import Path
s=json.loads(Path('summary.json').read_text());d=json.loads(Path('anatomy.json').read_text());fp=json.loads(Path('finding-provenance.json').read_text());out=[]
for key,label in [('claude:primary','X2 Claude，20 主分析 E'),('codex:primary','X2 Codex，20 主分析 E'),('claude:plan','plan-review Claude E，1 次')]:
 x=s[key];out += ['### '+label,'','單位：logical tokens。各列是已歸因值；末列差額仍計入總額。','', '| Stage | parent cache reads | parent rest | subagents cache reads | subagents rest |','|---|---:|---:|---:|---:|']
 b={(v['stage'],v['role']):v for v in x['stages']}
 for stage in ('prep','S5','S6','S7','S8','S9','final','parent_output_unallocated','unknown'):
  if not any((stage,r) in b for r in ('parent','subagents')):continue
  vals=[b.get((stage,role),{}).get(k,0) for role in ('parent','subagents') for k in ('cache_read','other')];out.append('| '+stage+' | '+' | '.join(f'{v:,}' for v in vals)+' |')
 out += [f"| 未歸因（actor 不明） | — | {x['unattributed']['other']:,} | — | — |",'',f"總計：cache reads **{x['total']['cache_read']:,}**；rest **{x['total']['other']:,}**；logical **{sum(x['total'].values()):,}**。",'']
out += ['### 每次完成作答的總額','', '原始 locator：`x2/runs/{cell}-{part}/raw/E-{case}.a{attempt}.jsonl`；`anatomy.json` 保存完整短 locator、逐 agent／stage 與 source hash。','', '| Case | Claude cache | Claude rest | Codex cache | Codex rest |','|---|---:|---:|---:|---:|']
cs=sorted({r['case'] for r in d['runs'] if r['status']=='completed'})
for c in cs:
 vals=[]
 for cell in ('claude','codex'):
  r=next(r for r in d['runs'] if r['case']==c and r['cell']==cell and r['status']=='completed');vals += [r['total']['cache_read'],r['total']['other']]
 out.append('| '+c+' | '+' | '.join(f'{v:,}' for v in vals)+' |')
out+=['','### Pilot 與未計入品質的中斷','', '| Cell / case / status | logical | cache | rest | 未歸因 rest |','|---|---:|---:|---:|---:|']
for r in d['runs']:
 if r['status'] in ('pilot','usage_limit'):out.append(f"| {r['cell']} / {r['case']} / {r['status']} | {sum(r['total'].values()):,} | {r['total']['cache_read']:,} | {r['total']['other']:,} | {r['unattributed']['other']:,} |")
out+=['','### 各 planted defect 的最早可見 reviewer 回報','', '每個 ID 在兩格都是 **S5** 的初次回報；不是對中間報告另做評分。逐 ID 的原文摘錄、raw line、final 既有兩家 grade 見 `finding-provenance.json`。','', '| Case | IDs（Claude / Codex 都在 S5） | Claude S5 raw line | Codex S5 rollout raw line |','|---|---|---:|---:|']
for c in sorted({x['case'] for x in fp}):
 xs=[x for x in fp if x['case']==c];a=next(x for x in xs if x['cell']=='claude');b=next(x for x in xs if x['cell']=='codex');ids=', '.join(x['defect'] for x in xs if x['cell']=='claude');out.append(f"| {c} | {ids} | {a['line']} | {b['line']} |")
Path('TABLES.generated.md').write_text('\n'.join(out)+'\n')
