#!/usr/bin/env python3
"""Independent H1 recomputation. Never imports/reads h1_judge.py.

Default: finalizes own results in recompute.json without opening judge.json.
--compare: preserves finalized calculations, then compares via a separate adapter.
All transcript files are read one line at a time. Claude messages are deduplicated
by API message ID, with final usage retained (blocks repeat the same message).
Codex usage is the last cumulative token_count in each distinct thread rollout;
input includes cached input, and output already includes reasoning output.
"""
import argparse
import collections
import hashlib
import importlib.util
import json
import math
import os
from fractions import Fraction
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
STATE = Path(os.environ['H1_STATE'])
RECORD = Path(__file__).resolve().parent.parent
STATS = Path(os.environ['H1_OAW']) / 'scripts' / 'eval_stats.py'
CELLS = ('claude', 'codex')
CLASSES = ('A', 'B', 'C')
LOGICAL = ('input_tokens', 'output_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens')
LIMIT = re.compile(r'hit your (?:\w+ )?limit|usage limit reached|you.ve reached your usage limit|limit \W* resets \d', re.I)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def events(path):
    with Path(path).open(encoding='utf-8', errors='replace') as f:
        for line_number, line in enumerate(f, 1):
            try:
                x = json.loads(line)
            except ValueError:
                continue
            if isinstance(x, dict):
                yield x


def load(path):
    return json.loads(Path(path).read_text())


def model_ok(model, cell):
    asked = 'claude-opus-5-5' if cell == 'claude' else 'gpt-6.1-sol'
    return bool(model) and re.fullmatch(re.escape(asked) + r'(?:-\d{8})?', str(model)) is not None


def usage_pair(u):
    total = sum(int(u.get(k) or 0) for k in LOGICAL)
    return [total, total - int(u.get('cache_read_input_tokens') or 0)]


def check_raw(row):
    root = STATE / row['root']
    streams = sorted((root / 'raw').glob('s[0-9]*.jsonl'))
    homes = [root / 'home', *root.glob('home-s*')]
    issues, details, errors = [], [], []
    if len(streams) != len(row['sessions']):
        issues.append('raw stream count differs from recorded session count')
    if row['cell'] == 'claude':
        by_session = collections.defaultdict(dict)
        paths = []
        for home in homes:
            for path in sorted(home.glob('.claude/projects/**/*.jsonl')):
                paths.append(str(path.relative_to(root)))
                for e in events(path):
                    m = e.get('message') or {}
                    if e.get('type') == 'assistant' and m.get('id') and isinstance(m.get('usage'), dict):
                        # A subagent's sessionId is its parent's sessionId.
                        by_session[e.get('sessionId')][m['id']] = m['usage']
        used_ids = set()
        for i, stream in enumerate(streams):
            session_id, root_messages, final, init = None, {}, None, None
            for e in events(stream):
                if e.get('session_id'):
                    session_id = e['session_id']
                if e.get('type') == 'system' and e.get('subtype') == 'init':
                    init = e
                if e.get('type') == 'rate_limit_event' and (e.get('rate_limit_info') or {}).get('status') == 'rejected':
                    issues.append(f'{stream.name}: rejected rate limit')
                if e.get('type') == 'assistant' and not e.get('parent_tool_use_id'):
                    m = e.get('message') or {}
                    if not model_ok(m.get('model'), 'claude'):
                        issues.append(f'{stream.name}: wrong/missing root model {m.get("model")}')
                    if e.get('error') == 'rate_limit' or m.get('error') == 'rate_limit':
                        issues.append(f'{stream.name}: root rate_limit error')
                    if m.get('id') and m.get('usage'):
                        root_messages[m['id']] = m['usage']
                if e.get('type') == 'result':
                    final = e
            if not init or init.get('apiKeySource') != 'none':
                issues.append(f'{stream.name}: missing/non-subscription billing init')
            if not root_messages:
                issues.append(f'{stream.name}: no root messages')
            if final is None:
                if row['sessions'][i].get('exit') not in ('timeout', 'token ceiling'):
                    issues.append(f'{stream.name}: missing CLI result')
            elif final.get('is_error'):
                issues.append(f'{stream.name}: result error {final.get("subtype")} status {final.get("api_error_status")}')
            messages = by_session.get(session_id, {})
            if not messages:
                issues.append(f'{stream.name}: no local per-message transcript for {session_id}')
                messages = root_messages
            used_ids.add(session_id)
            pair = [sum(usage_pair(u)[j] for u in messages.values()) for j in (0, 1)]
            if pair[0] == 0:
                issues.append(f'{stream.name}: zero tokens')
            result_pair = None
            if final:
                # Independent cross-check of aggregate event; not the primary count.
                aggregate = final.get('modelUsage') or {}
                result_pair = [sum(int(m.get(k) or 0) for m in aggregate.values() for k in
                                   ('inputTokens', 'outputTokens', 'cacheCreationInputTokens', 'cacheReadInputTokens')),
                               sum(int(m.get(k) or 0) for m in aggregate.values() for k in
                                   ('inputTokens', 'outputTokens', 'cacheCreationInputTokens'))]
            details.append({'stream': stream.name, 'session_id': session_id, 'message_count': len(messages),
                            'tokens_total': pair[0], 'tokens_noncache': pair[1], 'result_aggregate': result_pair,
                            'recorded': {k: row['sessions'][i].get(k) for k in ('tokens_total', 'tokens_noncache')},
                            'root_message_count': len(root_messages)})
        extra = set(by_session) - used_ids
        if extra:
            issues.append(f'unmapped transcript sessions: {sorted(str(x) for x in extra)}')
        source = {'files': paths, 'method': 'unique message IDs in root and subagent transcripts, final usage per message'}
    else:
        paths, seen_threads = [], set()
        archived = {p.name: p for p in (root / 'raw').glob('s*-rollouts/*.jsonl')}
        home_rollouts = {p.name: p for home in homes for p in home.glob('.codex/sessions/**/*.jsonl')}
        archive_differences = []
        for name, path in home_rollouts.items():
            if name not in archived or sha(path) != sha(archived[name]):
                archive_differences.append(name)
        if archive_differences:
            issues.append(f'home rollout missing/different in raw archive: {archive_differences}')
        for i, stream in enumerate(streams):
            root_id, parent_pair = None, [0, 0]
            for e in events(stream):
                if e.get('type') == 'thread.started':
                    root_id = e.get('thread_id')
                if e.get('type') == 'turn.completed':
                    u = e.get('usage') or {}
                    t = int(u.get('input_tokens') or 0) + int(u.get('output_tokens') or 0)
                    parent_pair[0] += t
                    parent_pair[1] += t - int(u.get('cached_input_tokens') or 0)
                if e.get('type') in ('error', 'turn.failed'):
                    errors.append({'stream': stream.name, 'event': e})
                    if LIMIT.search(json.dumps(e)) or e.get('type') == 'turn.failed':
                        issues.append(f'{stream.name}: structured CLI failure {e}')
            thread_details = []
            root_found = False
            for path in sorted(stream.with_name(stream.stem + '-rollouts').glob('*.jsonl')):
                last, thread_id, provider, models = None, None, None, []
                for e in events(path):
                    p = e.get('payload') or {}
                    if e.get('type') == 'session_meta':
                        thread_id = p.get('id') or p.get('session_id')
                        provider = p.get('model_provider')
                    if e.get('type') == 'turn_context':
                        models.append(p.get('model'))
                    if e.get('type') == 'event_msg' and p.get('type') == 'token_count':
                        u = (p.get('info') or {}).get('total_token_usage')
                        if u:
                            last = u
                    if e.get('type') == 'event_msg' and p.get('type') in ('error', 'turn_aborted'):
                        errors.append({'stream': stream.name, 'thread': thread_id, 'event': p})
                if thread_id in seen_threads:
                    issues.append(f'duplicate rollout thread {thread_id}')
                    continue
                seen_threads.add(thread_id)
                paths.append(str(path.relative_to(root)))
                if thread_id == root_id:
                    root_found = True
                    if provider != 'openai':
                        issues.append(f'{stream.name}: root provider {provider}')
                    if not models or any(not model_ok(m, 'codex') for m in models):
                        issues.append(f'{stream.name}: root model missing/wrong {models}')
                total = int((last or {}).get('input_tokens') or 0) + int((last or {}).get('output_tokens') or 0)
                pair = [total, total - int((last or {}).get('cached_input_tokens') or 0)]
                thread_details.append({'id': thread_id, 'root': thread_id == root_id, 'tokens_total': pair[0],
                                       'tokens_noncache': pair[1], 'models': sorted(set(str(m) for m in models)),
                                       'provider': provider})
            if not root_found:
                issues.append(f'{stream.name}: root rollout missing')
            pair = [sum(t[k] for t in thread_details) for k in ('tokens_total', 'tokens_noncache')]
            if not pair[0]:
                issues.append(f'{stream.name}: zero tokens')
            details.append({'stream': stream.name, 'tokens_total': pair[0], 'tokens_noncache': pair[1],
                            'threads': thread_details, 'parent_stream': parent_pair,
                            'recorded': {k: row['sessions'][i].get(k) for k in ('tokens_total', 'tokens_noncache')}})
        source = {'files': paths, 'method': 'last cumulative token usage in every distinct rollout thread',
                  'home_archive_check': {'home_files': len(home_rollouts), 'archived_files': len(archived),
                                         'differences': archive_differences}}
    for i, s in enumerate(row['sessions']):
        if s.get('api_key_source') != ('none' if row['cell'] == 'claude' else 'chatgpt'):
            issues.append(f's{i+1}: recorded non-subscription billing')
        if s.get('exit') not in (0, 'timeout', 'token ceiling'):
            issues.append(f's{i+1}: CLI exit {s.get("exit")}')
        if s.get('limit_seen'):
            issues.append(f's{i+1}: recorded usage limit')
    grade = row['grade']
    if grade.get('error') or grade.get('script_exit') not in (0, 124, 137):
        issues.append(f'grading infrastructure: {grade.get("error")} script exit {grade.get("script_exit")}')
    return {**source, 'sessions': details, 'tokens_total': sum(s['tokens_total'] for s in details),
            'tokens_noncache': sum(s['tokens_noncache'] for s in details), 'infrastructure_flags': issues,
            'structured_errors': errors}


def calculate():
    freeze = load(RECORD / 'FREEZE.json')
    freeze_sha = sha(RECORD / 'FREEZE.json')
    checks, problems = {}, []
    for name, path, expected in [('eval_stats', STATS, freeze['eval_stats_sha256']),
                                 ('prereg', RECORD/'PREREG.md', freeze['files']['PREREG.md']),
                                 ('runner', RECORD/'h1_run.py', freeze['files']['h1_run.py'])]:
        actual = sha(path)
        checks[name] = {'actual': actual, 'expected': expected, 'match': actual == expected}
        if actual != expected:
            problems.append(f'{name} digest mismatch')
    if not checks['eval_stats']['match']:
        raise RuntimeError('refusing to import unfrozen statistics')
    spec = importlib.util.spec_from_file_location('h1_frozen_eval_stats', STATS)
    stats = importlib.util.module_from_spec(spec)
    # Prevent writing bytecode outside the working directory.
    import sys
    sys.dont_write_bytecode = True
    spec.loader.exec_module(stats)
    units, unit_class, units_hash = {}, {}, {}
    class_units = {}
    for klass in CLASSES:
        path = STATE / f'units_{klass}.json'
        units_hash[klass] = sha(path)
        checks[f'units_{klass}'] = {'actual': units_hash[klass], 'expected': freeze['units'][klass],
                                    'match': units_hash[klass] == freeze['units'][klass]}
        if not checks[f'units_{klass}']['match']:
            problems.append(f'units {klass} digest mismatch')
        data = load(path)
        class_units[klass] = [u['id'] for u in data['units']]
        for u in data['units']:
            units[u['id']] = u
            unit_class[u['id']] = klass
    rows, attempts, starts = {}, {}, {}
    counts, coverage = {}, {}
    key = lambda r: (r['cell'], r['unit'], r['arm'], r['attempt'])
    for cell in CELLS:
        buckets = {}
        for kind in ('rows', 'attempts', 'starts'):
            records = list(events(STATE / f'{kind}-main-{cell}.jsonl'))
            buckets[kind] = records
            keys = [key(r) for r in records]
            if len(keys) != len(set(keys)):
                problems.append(f'duplicate {kind} in {cell}')
            for r in records:
                uid, klass = r['unit'], r['klass']
                if uid not in units or unit_class.get(uid) != klass or r['cell'] != cell:
                    problems.append(f'unknown unit/class/cell in {kind}: {key(r)}')
                    continue
                u = units[uid]
                expected = {'tag': 'main', 'freeze_sha256': freeze_sha, 'units_sha256': units_hash[klass],
                            'runner_sha256': freeze['files']['h1_run.py'],
                            'unit_sha256': hashlib.sha256(json.dumps(u, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
                            'candidate_sha256': u['candidate_sha256']}
                for field, value in expected.items():
                    if r.get(field) != value:
                        problems.append(f'{kind} {key(r)}: {field} mismatch')
                allowed = ('N1', 'N2', 'O', 'L') if cell == 'codex' and klass in ('B','C') else ('N1','N2','O')
                if r['arm'] not in allowed:
                    problems.append(f'{kind} unexpected arm: {key(r)}')
                if kind == 'starts' and r.get('event') != 'start':
                    problems.append(f'invalid start event {key(r)}')
            counts[cell] = {k: len(v) for k,v in buckets.items()}
        rows[cell], attempts[cell], starts[cell] = (buckets[k] for k in ('rows','attempts','starts'))
        rr = {key(r): r for r in rows[cell]}
        aa = {key(r): r for r in attempts[cell]}
        ss = {key(r): r for r in starts[cell]}
        for k, a in aa.items():
            if k not in ss:
                problems.append(f'attempt without start {k}')
            else:
                for field in ('root','tag','freeze_sha256','runner_sha256','units_sha256','unit_sha256','candidate_sha256'):
                    if a.get(field) != ss[k].get(field):
                        problems.append(f'attempt/start {field} mismatch {k}')
            if not a.get('not_run') and k not in rr:
                problems.append(f'counted attempt without row {k}')
        for k, r in rr.items():
            if k not in aa or aa[k].get('not_run'):
                problems.append(f'row without counted attempt {k}')
            elif aa[k] != r:
                problems.append(f'row/attempt payload mismatch {k}')
        wanted = {(uid,arm) for uid in units for arm in
                  (('N1','N2','O','L') if cell == 'codex' and unit_class[uid] in ('B','C') else ('N1','N2','O'))}
        got = [(r['unit'],r['arm']) for r in rows[cell]]
        coverage[cell] = {'expected':len(wanted), 'actual':len(got), 'missing': sorted(wanted-set(got)),
                          'unexpected':sorted(set(got)-wanted), 'duplicate_count':len(got)-len(set(got))}
        if set(got) != wanted or len(got) != len(set(got)):
            problems.append(f'{cell}: incomplete/duplicate unit arm coverage')
    token_rows, mismatches, session_mismatches, infra = [], [], [], []
    raw_map = {}
    for cell in CELLS:
        for row in rows[cell]:
            raw = check_raw(row)
            ident = {k: row[k] for k in ('cell','klass','unit','arm','attempt')}
            raw.update(ident)
            raw['recorded'] = {k: row[k] for k in ('tokens_total','tokens_noncache')}
            raw_map[key(row)] = raw
            for field in ('tokens_total','tokens_noncache'):
                if raw[field] != row[field]:
                    mismatches.append({**ident,'field':field,'raw':raw[field],'recorded':row[field],
                                       'relative_difference':abs(raw[field]-row[field])/row[field]})
            for s in raw['sessions']:
                for field in ('tokens_total','tokens_noncache'):
                    if s[field] != s['recorded'][field]:
                        session_mismatches.append({**ident,'session':s['stream'],'field':field,
                                                   'raw':s[field],'recorded':s['recorded'][field]})
            if raw['infrastructure_flags']:
                infra.append({**ident, 'flags':raw['infrastructure_flags']})
            token_rows.append(raw)
    score_map, fraction_map, score_checks = {}, {}, []
    recall_map = {}
    for cell in CELLS:
        for r in rows[cell]:
            g, u = r['grade'], units[r['unit']]
            regression = bool(g['suite_regression']) or g['suite_exit'] != 0 or g['suite_lost'] > 0
            f = Fraction(0) if regression else Fraction(g['passed'], g['n'])
            score_map[key(r)] = float(f)
            fraction_map[key(r)] = f
            if g['n'] != len(u['items']) or g['passed'] != sum(v is True for v in g['items'].values()):
                problems.append(f'pass count/frozen denominator inconsistent {key(r)}')
            recall_funcs = [n for n in u['functions'] if n.startswith('test_recall_')]
            recall = bool(recall_funcs) and all(g['functions'].get(n) is True for n in recall_funcs) and not regression
            recall_map[key(r)] = int(recall)
            if float(f) != r['score'] or float(f) != g['score']:
                score_checks.append({'key':list(key(r)),'recomputed':float(f),'recorded':r['score'],'grade':g['score']})
            if r['klass'] == 'B' and recall != g['recall']:
                problems.append(f'recall flag inconsistent {key(r)}')
    results = {}
    for cell in CELLS:
        ix = {(r['unit'],r['arm']): r for r in rows[cell]}
        ids = [uid for k in CLASSES for uid in class_units[k]]
        def values(metric, arms, ids=ids):
            return {uid:[metric[key(ix[uid,a])] for a in arms] for uid in ids}
        o, n = values(score_map,('O',)), values(score_map,('N1','N2'))
        noise = stats.pooled_within_sd(n)
        floor = max(noise,0.1318)
        overall = stats.compare(o,n,margin=0.10,floor_sd=floor)
        classes = {}
        for klass in CLASSES:
            subset = class_units[klass]
            comp = stats.compare({u:o[u] for u in subset},{u:n[u] for u in subset},margin=0.10,floor_sd=floor)
            exact_deltas = {uid:fraction_map[key(ix[uid,'O'])] -
                            (fraction_map[key(ix[uid,'N1'])]+fraction_map[key(ix[uid,'N2'])])/2 for uid in subset}
            wins = sum(d >= Fraction(1,10) for d in exact_deltas.values())
            losses = sum(d <= -Fraction(1,10) for d in exact_deltas.values())
            balance = wins-losses
            direction = ('方向：較好' if balance>=2 else '方向：較差' if balance<=-2 else
                         '差一題，不下結論' if abs(balance)==1 else '勝負抵銷，未證等價' if wins else '看不出差別，未證等價')
            classes[klass] = {'compare':comp, 'wins':wins, 'losses':losses, 'ties':4-wins-losses,
                              'direction':direction, 'exact_deltas':{u:str(d) for u,d in exact_deltas.items()},
                              'mean_O':sum(o[u][0] for u in subset)/4,
                              'mean_N':sum(sum(n[u])/2 for u in subset)/4}
        worse_classes = [k for k in CLASSES if classes[k]['compare']['class']=='worse']
        inconsistent = [k for k in CLASSES if sum(Fraction(x) for x in classes[k]['exact_deltas'].values())/4 <= -Fraction(1,10)]
        Q = ('worse' if worse_classes or overall['class']=='worse' else
             'undetermined' if inconsistent else overall['class'])
        q_reason = ('class worse: '+','.join(worse_classes) if worse_classes else 'overall worse' if overall['class']=='worse'
                    else '類別不一致: '+','.join(inconsistent) if inconsistent else 'overall class')
        b_ids=class_units['B']
        mo,mn = values(recall_map,('O',),b_ids), values(recall_map,('N1','N2'),b_ids)
        mem_noise=stats.pooled_within_sd(mn)
        mem=stats.compare(mo,mn,margin=0.10,floor_sd=max(mem_noise,0.1318))
        counts_mem={a:sum(recall_map[key(ix[u,a])] for u in b_ids) for a in ('O','N1','N2')}
        mem_word = ('記憶變好' if mem['class']=='better' else '記憶變差' if mem['class']=='worse' else
                    '都記得，這組題目分不出來（天花板，未證等價）' if all(v==4 for v in counts_mem.values()) else '未定')
        memory={'compare':mem,'word':mem_word,'counts':counts_mem,'N_mean_count':(counts_mem['N1']+counts_mem['N2'])/2,
                'native_noise_sd':mem_noise,'floor_sd':max(mem_noise,0.1318)}
        def totals(field, subset):
            s={a:sum(raw_map[key(ix[u,a])][field] for u in subset) for a in ('O','N1','N2')}
            s['N']=(s['N1']+s['N2'])/2
            T=s['O']/s['N'];B=max(s['N1']/s['N2'],s['N2']/s['N1'])
            sentence='token 變多' if T>max(1.10,B) else 'token 變少' if T<min(1/1.10,1/B) else '沒有確實變多'
            return {'totals':s,'T':T,'B':B,'word':sentence,'upper':max(1.10,B),'lower':min(1/1.10,1/B)}
        tokens={field:{'overall':totals(field,ids),'classes':{k:totals(field,class_units[k]) for k in CLASSES}}
                for field in ('tokens_total','tokens_noncache')}
        to = {u:[raw_map[key(ix[u,'O'])]['tokens_total']] for u in ids}
        tn = {u:[raw_map[key(ix[u,a])]['tokens_total'] for a in ('N1','N2')] for u in ids}
        cost=stats.cost(to,tn)
        token_word=tokens['tokens_total']['overall']['word']
        word = {'worse':'更慘','better':'有幫助','undetermined':'未定'}.get(Q)
        if Q=='equivalent':word='雞肋' if token_word=='token 變多' else '沒差'
        outcome=('提案移出預設' if Q=='worse' or (Q in ('equivalent','undetermined') and cost['class']=='over') else
                 '該改成選配' if (Q=='better' and cost['class']=='over') or (Q=='equivalent' and cost['class']!='cheaper') else
                 '留在預設站得住' if Q=='better' or (Q=='equivalent' and cost['class']=='cheaper') else
                 '能力未定：不能拿這次結果說預設站得住')
        failed={a:{'attempts':0,'tokens_total':0,'tokens_noncache':0,'unknown':0} for a in ('N1','N2','O','L')}
        ended={key(a) for a in attempts[cell]}
        for a in attempts[cell]:
            if a.get('not_run'):
                d=failed[a['arm']];d['attempts']+=1
                for field in ('tokens_total','tokens_noncache'):d[field]+=a.get(field) or 0
        for s in starts[cell]:
            if key(s) not in ended:
                d=failed[s['arm']];d['attempts']+=1;d['unknown']+=1
        ceiling=[u for u in class_units['C'] if n[u]==[1,1]]
        lcontrol={}
        if cell=='codex':
            subset=class_units['B']+class_units['C']
            l=values(score_map,('L',),subset)
            lcontrol={'O_vs_L':stats.compare({u:o[u] for u in subset},l,margin=0.10,floor_sd=floor),
                      'L_vs_N':stats.compare(l,{u:n[u] for u in subset},margin=0.10,floor_sd=floor)}
        results[cell]={'complete':True,'native_noise_sd':noise,'floor_sd':floor,'quality':overall,'classes':classes,
                       'Q':Q,'Q_reason':q_reason,'memory':memory,'tokens':tokens,'cost':cost,'word':word,'outcome':outcome,
                       'failed_attempts':failed,'C_ceiling':ceiling,'L':lcontrol,
                       'scores':{u:{a:score_map[key(ix[u,a])] for a in ('N1','N2','O')+ (('L',) if (u,'L') in ix else ())} for u in ids}}
    word_order=['更慘','未定','雞肋','沒差','有幫助']
    outcome_order=['提案移出預設','該改成選配','能力未定：不能拿這次結果說預設站得住','留在預設站得住']
    merged={'word':min((r['word'] for r in results.values()),key=word_order.index),
            'outcome':min((r['outcome'] for r in results.values()),key=outcome_order.index)}
    cross={u:{c:results[c]['quality']['per_question'][u] for c in CELLS} for u in units}
    budget=load(STATE/'budget.json')
    claude_spent=budget['spent_before']+sum(r['tokens_total'] for r in token_rows if r['cell']=='claude')
    if claude_spent>budget['cap']:infra.append({'cell':'claude','flags':['budget exceeded'],'spent':claude_spent,'cap':budget['cap']})
    return {'method':{'independent':True,'judge_read':False,'statistics_file':str(STATS),'freeze_sha256':freeze_sha,
                      'threshold_arithmetic':'exact fractions from pass counts for +/-0.10 direction and class guard'},
            'integrity':{'ok':not problems,'problems':problems,'digests':checks,'counts':counts,'coverage':coverage},
            'token_check':{'rows_checked':len(token_rows),'sessions_checked':sum(len(r['sessions']) for r in token_rows),
                           'max_relative_difference':max((m['relative_difference'] for m in mismatches),default=0),
                           'mismatches':mismatches,'session_mismatches':session_mismatches,'rows':token_rows},
            'score_mismatches':score_checks,'infrastructure_flags':infra,'cells':results,'merged':merged,
            'cross_cell_deltas':cross,'C_filled_at_ceiling':[u for u,n in load(STATE/'units_C.json')['notes'].items() if 'chosen: at ceiling' in n],
            'budget':{'spent_before':budget['spent_before'],'scored_raw_tokens':claude_spent-budget['spent_before'],
                      'total':claude_spent,'cap':budget['cap']}}


def compare_finalized():
    """Schema adapter only; does not alter any independently finalized number.

    The judge abbreviates the undetermined outcome; compare its short label
    against the same label derived from the full preregistered sentence.
    Explanatory prose is compared by the underlying reason, separately from
    exact numerical/categorical fields.
    """
    independent = HERE/'recompute-independent.json'
    expected_sha = (HERE/'recompute-independent.sha256').read_text().split()[0]
    if sha(independent) != expected_sha:
        raise RuntimeError('the finalized independent result changed')
    own = load(independent)
    judge_path = Path(os.environ['H1_JUDGE_JSON'])
    judge = load(judge_path)  # The first judge access in this program's workflow.
    stat_keys = ('class','point','ci95','ci90','se','mde','floor_applied','questions')
    def brief(s):
        return {k:s[k] for k in stat_keys}
    def short_outcome(s):
        return s.split('：',1)[0]
    def total_block(s):
        return {**{a:s['totals'][a] for a in ('O','N1','N2')}, 'ratio':s['T'],'band':s['B']}
    projection = {
        'rule':{'margin':0.10,'floor_min':0.1318,'step':0.10,'more':1.10,'per_class':4,
                'word_order':['更慘','未定','雞肋','沒差','有幫助'],
                'outcome_order':['提案移出預設','該改成選配','能力未定','留在預設站得住']},
        'inputs':{'freeze_sha256':own['method']['freeze_sha256'],
                  'units':{k:own['integrity']['digests'][f'units_{k}']['actual'] for k in CLASSES},
                  'eval_stats_sha256':own['integrity']['digests']['eval_stats']['actual']},
        'cells':{},
        'merged':{'word':own['merged']['word'],'outcome':short_outcome(own['merged']['outcome']),
                  'words':{c:own['cells'][c]['word'] for c in CELLS},
                  'outcomes':{c:short_outcome(own['cells'][c]['outcome']) for c in CELLS},
                  'cells_agree':len({own['cells'][c]['word'] for c in CELLS})==1}}
    semantic_reasons = []
    for cell,r in own['cells'].items():
        empty_attempts = {a:d for a,d in r['failed_attempts'].items() if d['attempts']}
        q = {'floor':r['floor_sd'],'own_spread':r['native_noise_sd'],
             'by_class':{k:brief(v['compare']) for k,v in r['classes'].items()},
             'Q':r['Q'],'composite':brief(r['quality'])}
        costs = {'by_class':{k:total_block(v) for k,v in r['tokens']['tokens_total']['classes'].items()},
                 'noncache_by_class':{k:total_block(v) for k,v in r['tokens']['tokens_noncache']['classes'].items()},
                 'attempts_not_counted':empty_attempts,
                 'batch':total_block(r['tokens']['tokens_total']['overall']),
                 'noncache_batch':total_block(r['tokens']['tokens_noncache']['overall']),
                 'sentence':r['tokens']['tokens_total']['overall']['word'],
                 'protocol':{k:r['cost'][k] for k in ('class','ratio','ci95','cap')}}
        directions = {}
        for klass,cl in r['classes'].items():
            ceilings=sorted(u for u,s in r['scores'].items()
                            if u in cl['exact_deltas'] and s['N1']==s['N2']==1)
            directions[klass] = {k:cl[k] for k in ('wins','losses','direction')}
            directions[klass].update(at_ceiling=ceilings,ceiling_note='頂到天花板，只看得出變差' if ceilings else '')
        mem = {**brief(r['memory']['compare']), 'word':r['memory']['word'],
               'remembered':r['memory']['counts'],'of':4,'floor':r['memory']['floor_sd']}
        p={'status':'complete' if r['complete'] else 'incomplete','why':[],
           'classes_done':list(CLASSES),'attempts_not_counted':empty_attempts,
           'quality':q,'cost':costs,'direction':directions,'memory':mem,
           'word':r['word'],'token_sentence':costs['sentence'],'outcome':short_outcome(r['outcome'])}
        if r['Q']=='undetermined':
            p['undetermined_detail']={k:r['quality'][k] for k in ('point','ci95','mde')}
        if r['L']:
            p['L_control']={'units':8,**{k:{f:v[f] for f in ('class','point','ci95')} for k,v in r['L'].items()}}
        projection['cells'][cell]=p
        raw_reason=judge['cells'][cell]['quality'].get('why','')
        # Compare the cause instead of requiring identical prose.
        reason_matches = ('B' in raw_reason and '類別不一致' in raw_reason
                          if r['Q_reason']=='類別不一致: B' else
                          'composite' in raw_reason if r['Q_reason']=='overall class' else
                          r['Q_reason'] == raw_reason)
        semantic_reasons.append({'path':f'cells.{cell}.quality.why','independent':r['Q_reason'],
                                 'judge':raw_reason,'agree':reason_matches})
    across = {}
    for uid in own['cross_cell_deltas']:
        across[uid] = {}
        for c in CELLS:
            klass=next(k for k,v in own['cells'][c]['classes'].items() if uid in v['exact_deltas'])
            delta=Fraction(own['cells'][c]['classes'][klass]['exact_deltas'][uid])
            across[uid][c]='+' if delta>=Fraction(1,10) else '-' if delta<=-Fraction(1,10) else '0'
    counts={'same_direction':0,'no_difference_in_both':0,'opposite':0,'difference_in_one_cell':0}
    for dirs in across.values():
        a,b=(dirs[c] for c in CELLS)
        category=('no_difference_in_both' if a==b=='0' else 'same_direction' if a==b else
                  'difference_in_one_cell' if '0' in (a,b) else 'opposite')
        counts[category]+=1
    projection['across_cells']={'units':across,**counts}
    comparisons=[]
    def walk(path,a,b):
        if isinstance(a,dict):
            if not isinstance(b,dict):
                comparisons.append({'path':path,'independent':a,'judge':b,'agree':False})
            else:
                for k,v in a.items():
                    if k not in b:
                        comparisons.append({'path':path+'.'+k,'independent':v,'judge':'<missing>','agree':False})
                    else:
                        walk(path+'.'+k if path else k,v,b[k])
        elif isinstance(a,list):
            if not isinstance(b,list) or len(a)!=len(b):
                comparisons.append({'path':path,'independent':a,'judge':b,'agree':False})
            else:
                if not a:
                    comparisons.append({'path':path,'independent':a,'judge':b,'agree':True})
                for i,(v,w) in enumerate(zip(a,b)):
                    walk(f'{path}[{i}]',v,w)
        else:
            comparisons.append({'path':path,'independent':a,'judge':b,'agree':a==b})
    walk('',projection,judge)
    disagreements=[v for v in comparisons+semantic_reasons if not v['agree']]
    own['judge_comparison']={
        'independent_finalized_sha256':expected_sha,'judge_sha256':sha(judge_path),
        'scalar_or_empty_list_fields_compared':len(comparisons),'exact_agreements':sum(v['agree'] for v in comparisons),
        'semantic_reason_comparisons':semantic_reasons,'disagreements':disagreements,
        'outcome_label_normalization':'judge uses 能力未定; own full sentence adds 不能拿這次結果說預設站得住',
        'fields':comparisons,
        'independent_only_fields':['raw per-row and per-session token counts (compared with scored rows)',
                                   'unit scores from exact pass counts (judge does not publish them)',
                                   'per-unit cost ratios and score differences (judge publishes summary statistics)',
                                   'per-class token words/thresholds and means',
                                   'token provenance and raw infrastructure checks',
                                   'C filled-at-ceiling selection and budget'],
        'judge_fields_not_recomputed':['cells.*.usage (descriptive tool-use summaries)',
                                       'cells.*.quality.sensitivity_own_spread_only (not a preregistered verdict step)']}
    (HERE/'recompute.json').write_text(json.dumps(own,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in own['judge_comparison'].items() if k!='fields'},ensure_ascii=False,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compare',action='store_true')
    args=parser.parse_args()
    if args.compare:
        compare_finalized()
        return
    result=calculate()
    (HERE/'recompute.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    # This seal excludes the later judge comparison and can verify the prereveal result.
    (HERE/'recompute-independent.sha256').write_text(sha(HERE/'recompute.json')+'  recompute-independent.json\n')
    (HERE/'recompute-independent.json').write_bytes((HERE/'recompute.json').read_bytes())
    print(json.dumps({k:result[k] for k in ('integrity','infrastructure_flags','merged','budget')},ensure_ascii=False,indent=2))
    for c,r in result['cells'].items():
        print(c,json.dumps({k:r[k] for k in ('Q','Q_reason','word','outcome','memory','cost','L')},ensure_ascii=False))
    print('TOKEN_CHECK',json.dumps({k:v for k,v in result['token_check'].items() if k!='rows'}))

if __name__=='__main__':
    main()
