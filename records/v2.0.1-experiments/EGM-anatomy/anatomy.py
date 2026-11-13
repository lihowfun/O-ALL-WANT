"""Offline token anatomy. No model calls or writes outside the output directory.
Run with PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 anatomy.py --help.
"""
import argparse,collections,hashlib,json,re,statistics,platform,sys
from pathlib import Path
STAGES=('prep','S5','S6','S7','S8','S9','final','unknown')
FIELDS=('cache_read','other')
def read_jsonl(path):
    result=[]
    for n,line in enumerate(path.read_text(errors='replace').splitlines(),1):
        try: result.append((n,json.loads(line)))
        except ValueError: raise ValueError(f'Invalid JSON line {n} in {path.name}')
    return result
def short(path,root): return str(path.relative_to(root))
def tokens(u,camel=False):
    if camel:
        return dict(cache_read=u.get('cacheReadInputTokens',0),other=sum(u.get(k,0) for k in ('inputTokens','outputTokens','cacheCreationInputTokens')))
    return dict(cache_read=u.get('cache_read_input_tokens',0),other=sum(u.get(k,0) for k in ('input_tokens','output_tokens','cache_creation_input_tokens')))
def add(a,b):
    for k in FIELDS:a[k]+=b[k]
def zero():return dict.fromkeys(FIELDS,0)
def stage_for(name,zoom=0,style=0):
    n=name.lower().replace('-','_')
    if any(s in n for s in ('intermediate','second_zoom','zoom2','zoom_2','mid_zoom')):return 'S8'
    if 'zoom' in n:return 'S8' if zoom else 'S5'
    if 'comprehension' in n:return 'S6'
    if any(s in n for s in ('readiness','implementation','codebase','code_details','code_detail','impl_','ready','stage9','stage_9')):return 'S9'
    if 'style' in n:return 'S9' if style else 'S7'
    if any(s in n for s in ('critic','design','structur','stage7','stage_7')):return 'S7'
    return 'unknown'
def normalize_file(s):
    s=str(s).replace('\\','/')
    for marker in ('/ws/','/evidence/','/review_out/','/.oaw/','/.agents/','/.claude/'):
        if marker in s:
            tail=s.split(marker,1)[1]
            return tail.split('/',1)[1] if marker=='/ws/' and '/' in tail else marker.strip('/')+'/'+tail
    return s if not s.startswith('/') else Path(s).name
REPORT_STAGE={'zoom_out_report.md':'S5','comprehension_report.md':'S6','critic_report.md':'S7','intermediate_zoom_out_report.md':'S8','implementation_readiness_report.md':'S9','consolidated_review_report.md':'final','report.json':'final'}
def claude(path,root,expected=None):
    events=read_jsonl(path); agents={}; zoom=style=0; phase='prep'; msgs={}; reads=[]; writes=[]; launches=[]; last_usage={}; tools={}
    for n,e in events:
        if e.get('type')=='assistant':
            m=e.get('message',{});parent=e.get('parent_tool_use_id');oldphase=phase
            for b in m.get('content',[]):
                if b.get('type')!='tool_use':continue
                name=b.get('name');inp=b.get('input',{});tid=b.get('id')
                tools[tid]=(name,inp)
                if name in ('Agent','Task'):
                    desc=inp.get('subagent_type','')+' '+inp.get('description','')
                    s=stage_for(desc,zoom,style)
                    if 'zoom' in desc:zoom+=1
                    if 'style' in desc:style+=1
                    agents[tid]={'stage':s,'agent':inp.get('subagent_type') or inp.get('description','unknown'),'launch_line':n}
                    launches.append({'line':n,'stage':s,'agent':agents[tid]['agent']})
                    if not parent:phase=s
                if name in ('Read','Grep','Glob'):
                    f=inp.get('file_path') or inp.get('path') or inp.get('pattern','')
                    reads.append({'line':n,'stage':agents.get(parent,{}).get('stage',phase),'agent':agents.get(parent,{}).get('agent','parent'),'kind':name,'file':normalize_file(f),'offset':inp.get('offset'),'limit':inp.get('limit')})
                if name=='Write':
                    f=Path(inp.get('file_path','')).name;s=REPORT_STAGE.get(f)
                    writes.append({'line':n,'stage':s or phase,'file':f})
                    if f=='implementation_readiness_report.md':phase='final'
            if m.get('id') and m.get('usage'):
                # Last block of the same message carries the completed output usage.
                msgs[m['id']]={'line':n,'stage':agents.get(parent,{}).get('stage',oldphase),'agent':agents.get(parent,{}).get('agent','parent' if not parent else 'unmapped_child'),'usage':tokens(m['usage'])}
        if e.get('type')=='result' and e.get('modelUsage'):
            last_usage=zero()
            for u in e['modelUsage'].values():add(last_usage,tokens(u,True))
    buckets=collections.defaultdict(zero)
    for m in msgs.values():add(buckets[(m['stage'],m['agent'])],m['usage'])
    observed=zero()
    for b in buckets.values():add(observed,b)
    target=expected or last_usage or observed
    residual={k:target[k]-observed[k] for k in FIELDS}
    return {'trace':short(path,root),'total':target,'observed':observed,'unattributed':residual,'buckets':[dict(stage=s,agent=a,**v) for (s,a),v in sorted(buckets.items())],'launches':launches,'reads':reads,'writes':writes,'usage_events':list(msgs.values())}
def codex(path,root,expected):
    rollouts=path.with_name(path.stem+'-rollouts');buckets=[];reads=[];launches=[];writes=[];usage_events=[];unknown=[]
    tree=[]
    for p in sorted(rollouts.glob('*.jsonl')):
        evs=read_jsonl(p);meta=next(e['payload'] for n,e in evs if e['type']=='session_meta');ap=meta.get('agent_path') or '/root'
        tree.append((p,evs,meta,ap))
    # Classify from actual agent paths; temporal order resolves repeated personas.
    for p,evs,meta,ap in sorted(tree,key=lambda x:x[2].get('timestamp','')):
        isroot=not meta.get('parent_thread_id');s='prep' if isroot else stage_for(ap)
        if not isroot and s=='unknown':unknown.append(ap)
        if not isroot:launches.append({'agent':ap,'stage':s,'trace':short(p,root)})
        prev=zero();last=None
        for n,e in evs:
            pl=e.get('payload',{});typ=pl.get('type')
            if e['type']=='event_msg' and typ=='token_count' and pl.get('info'):
                u=pl['info'].get('total_token_usage')
                if not u:continue
                v={'cache_read':u.get('cached_input_tokens',0),'other':u.get('input_tokens',0)+u.get('output_tokens',0)-u.get('cached_input_tokens',0)}
                delta={k:v[k]-prev[k] for k in FIELDS}
                if any(delta.values()):usage_events.append({'line':n,'trace':short(p,root),'stage':s,'agent':'parent' if isroot else ap,'usage':delta,'timestamp':e.get('timestamp')})
                prev=v;last=v
            if e['type']=='response_item' and typ in ('function_call','custom_tool_call'):
                raw=pl.get('arguments') or pl.get('input') or ''
                # Commands stay private; only matching review artifact names retained.
                name=pl.get('name','')
                for filename,rs in REPORT_STAGE.items():
                    if filename in str(raw) and any(w in str(raw) for w in ('apply_patch','*** Add','*** Update','cat >','write_text')):
                        writes.append({'line':n,'trace':short(p,root),'stage':rs,'file':filename})
                if isroot:
                    if 'spawn_agent' in str(raw) or 'spawn_agent' in name:
                        found=stage_for(str(raw)[:700])
                        if found!='unknown':s=found
                    if 'consolidated_review_report.md' in str(raw) and 'apply_patch' in str(raw):s='final'
                # Count commands mentioning specific input paths; not exact shell parsing.
                for f in sorted(set(re.findall(r'(?:docs/[\w./-]+\.md|src/[\w./-]+\.py|README\.md)',str(raw)))):
                    reads.append({'line':n,'trace':short(p,root),'stage':s,'agent':'parent' if isroot else ap,'kind':'command_reference','file':f})
        buckets.append({'stage':'parent_mixed' if isroot else s,'agent':'parent' if isroot else ap,**(last or zero()),'trace':short(p,root),'missing_usage':last is None})
    # Parent is apportioned by token_count delta and active stage, while child totals are exact.
    parent=collections.defaultdict(zero)
    for m in usage_events:
        if m['agent']=='parent':add(parent[m['stage']],m['usage'])
    buckets=[b for b in buckets if b['agent']!='parent']+[dict(stage=s,agent='parent',**v) for s,v in parent.items()]
    obs=zero()
    for b in buckets:add(obs,b)
    return {'trace':short(path,root),'total':expected,'observed':obs,'unattributed':{k:expected[k]-obs[k] for k in FIELDS},'buckets':buckets,'reads':reads,'writes':writes,'launches':launches,'unknown_paths':unknown,'usage_events':usage_events}
def main():
    p=argparse.ArgumentParser();p.add_argument('--scratch',required=True,type=Path,help='Scratchpad containing x2 and plan-review');p.add_argument('--records',required=True,type=Path);p.add_argument('--out',type=Path,default=Path(__file__).resolve().parent);a=p.parse_args()
    root=a.scratch;records=a.records;runs=[];sources=[]
    spec=json.loads((records/'v2.0.1-experiments/X2/frozen/spec.json').read_text())
    for cell in ('claude','codex'):
        rows=[json.loads(l) for l in (records/f'v2.0.1-experiments/X2/results/{cell}-rows.jsonl').read_text().splitlines()]
        for row in rows:
            if row['arm']!='E':continue
            tag=f"E-{row['id']}.a{row['attempt']}";paths=list((root/'x2/runs').glob(f'{cell}-*/raw/{tag}.jsonl'))
            if len(paths)!=1:raise ValueError((tag,paths))
            target={'cache_read':row['tokens_total']-row['tokens_noncache'],'other':row['tokens_noncache']}
            x=claude(paths[0],root,target) if cell=='claude' else codex(paths[0],root,target)
            x.update(cell=cell,case=row['id'],primary=row['id'] in spec['planned_primary'],attempt=row['attempt'],status='completed');runs.append(x)
    for path in sorted((root/'x2/runs').glob('claude-*/deviations.jsonl')):
        for _,row in read_jsonl(path):
            if row['arm']=='E':
                rp=path.parent/'raw'/f"E-{row['id']}.a{row['attempt']}.jsonl";x=claude(rp,root,{'cache_read':row['tokens_total']-row['tokens_noncache'],'other':row['tokens_noncache']});x.update(cell='claude',case=row['id'],primary=False,attempt=row['attempt'],status='usage_limit');runs.append(x)
    for cell in ('claude','codex'):
        pilot=root/'x2'/f'pilot-{cell}'
        for _,row in read_jsonl(pilot/'rows.jsonl'):
            if row['arm']!='E':continue
            rp=pilot/'raw'/f"E-{row['id']}.jsonl"
            target={'cache_read':row['tokens_total']-row['tokens_noncache'],'other':row['tokens_noncache']}
            x=claude(rp,root,target) if cell=='claude' else codex(rp,root,target)
            x.update(cell=cell,case=row['id'],primary=False,status='pilot',attempt=1);runs.append(x)
    u=json.loads((records/'plan-review-2026-11-07/usage.json').read_text())['egm'];pl=claude(root/'plan-review/out/egm.jsonl',root,{'cache_read':u['modelUsage']['cacheReadInputTokens'],'other':u['tokens_without_cache_reads']});pl.update(cell='claude',case='plan-review',primary=False,status='historical');runs.append(pl)
    summaries={}
    for cell in ('claude','codex'):
        for scope in ('primary','completed'):
            subset=[r for r in runs if r['cell']==cell and (r['primary'] if scope=='primary' else r['status']=='completed')]
            b=collections.defaultdict(zero);t=zero();un=zero();ag=collections.defaultdict(zero)
            for r in subset:
                add(t,r['total']);add(un,r['unattributed'])
                for v in r['buckets']:
                    add(b[(v['stage'],'parent' if v['agent']=='parent' else 'subagents')],v)
                    add(ag[v['agent']],v)
            summaries[f'{cell}:{scope}']={'runs':len(subset),'total':t,'unattributed':un,'stages':[dict(stage=s,role=role,**v) for (s,role),v in sorted(b.items())],'agents':dict(ag),'median_logical':statistics.median(sum(r['total'].values()) for r in subset)}
    # Retain only relative locators and numerical metadata, never transcript content.
    for r in runs:
        rp=root/r['trace'];sources.append({'locator':r['trace'],'sha256':hashlib.sha256(rp.read_bytes()).hexdigest()})
        if r['cell']=='codex':
            for child in sorted(rp.with_name(rp.stem+'-rollouts').glob('*.jsonl')):
                sources.append({'locator':short(child,root),'sha256':hashlib.sha256(child.read_bytes()).hexdigest()})
    output={'schema':1,'platform':platform.platform(),'python':sys.version.split()[0],'protocol':'Claude last usage per message id; final modelUsage reconciliation. Codex final cumulative usage per rollout, token_count deltas for parent phases. Residuals never imputed.','summaries':summaries,'runs':runs,'sources':sources}
    (a.out/'anatomy.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summaries,ensure_ascii=False,indent=2))
    print('plan',pl['total'],pl['observed'],pl['unattributed'])
if __name__=='__main__':main()
