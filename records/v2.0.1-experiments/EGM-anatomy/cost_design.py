"""Explicit planning scenarios, not measured pilots or confidence intervals."""
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--product',required=True,type=Path);a=p.parse_args();s=json.loads(Path('summary.json').read_text());q=s['quality_cost'];plan_e=18480203;plan_n_codex=1085264
# Two within-cell scaling recipes form a sensitivity range, not a cross-provider conversion.
ratios={c:[q[f'{c}:E']['median']/q[f'{c}:N']['median'],q[f'{c}:E']['total']/q[f'{c}:N']['total']] for c in ('claude','codex')}
units={'claude':{'N':sorted(plan_e/x for x in ratios['claude']),'E':[plan_e,plan_e]},'codex':{'N':[plan_n_codex,plan_n_codex],'E':sorted(plan_n_codex*x for x in ratios['codex'])}}
factors={}
for c in ('claude','codex'):
 k=s[f'{c}:primary'];remove=sum(k['preset3_removable_work'].values())/sum(k['total'].values());factors[c]=[1-remove,1]
 # Plan observation gives a more relevant upper-size retained-work estimate for Claude.
 if c=='claude':factors[c]=sorted([1-remove,1-sum(s['claude:plan']['preset3_removable_work'].values())/plan_e])
 units[c]['T']=[units[c]['E'][0]*factors[c][0],units[c]['E'][1]*factors[c][1]]
# All candidate packets must be bounded by the plan-sized reference packet.
# No document-only linear scaling is implied; same envelope until packet pilot is available.
docs=['capability-v1','capability-v3','H1-v2-reference-only','execution-v1','D45-v1','FIXCHECK-preclosure-missing'];table=[]
for doc in docs:
 for c in ('claude','codex'):
  u=units[c];n=u['N'];e=u['E'];t=u['T'];merge=[0.1e6,0.2e6];grading=[0.5e6,1e6];prep=[0.1e6,0.2e6]
  arms={name:[round(v*1.3) for v in vals] for name,vals in {'N':n,'N2+merge':[2*n[i]+merge[i] for i in (0,1)],'E':e,'T':t}.items()}
  # N1 is shared between single and merged arms: exactly two native runs, not three.
  base=[2*n[i]+e[i]+merge[i]+grading[i]+prep[i] for i in (0,1)]
  four=[base[i]+t[i] for i in (0,1)]
  screen=[2*n[i]+merge[i]+grading[i]+prep[i] for i in (0,1)]
  process=[2*n[i]+t[i]+merge[i]+grading[i]+prep[i] for i in (0,1)]
  table.append(dict(document=doc,cell=c,arms_with_1_3=arms,three_arm_total=[round(x*1.3) for x in base],four_arm_total=[round(x*1.3) for x in four],native_screen=[round(x*1.3) for x in screen],trimmed_screen=[round(x*1.3) for x in process]))
data={'status':'planning_proxy_not_pilot','large_reference':{'E_claude':plan_e,'N_codex':plan_n_codex},'within_cell_ratios':ratios,'units':units,'trimmed_retained_fractions':factors,'stage_reserves':{'merge':[100000,200000],'grading_validation_adjudication':[500000,1000000],'preparation_selector_reporting':[100000,200000]},'per_document':table,'D45_size':{}}
data['H1_v2_double_generation_sensitivity']={c:[round((2*(2*units[c]['N'][i]+units[c]['E'][i])+[0.7e6,1.4e6][i])*1.3) for i in (0,1)] for c in units}
b=subprocess.check_output(['git','-C',str(a.product),'show','e2c3315:docs/plans/v2.0.1-release-path.md']);data['D45_size']={'commit':'e2c3315','lines':len(b.splitlines()),'bytes':len(b)}
Path('design-costs.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(data['units'],indent=2));print(data['D45_size'])
for x in table[:2]:print(x['cell'],json.dumps(x))
