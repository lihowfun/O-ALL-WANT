"""Read-only adapter for OAW's frozen H1 FIXCHECK. No runner imports or grading."""
from __future__ import annotations

import json
from pathlib import Path

from eval_ledger import (Snapshot, canonical, confined, digest, ident, number,
                         parse, require, summarize)


def report_fixcheck(manifest_path, state):
    state = Path(state).resolve()
    snapshot, sources = Snapshot(), {}

    def read(path, sid, *, optional=False, jsonl=False):
        data = snapshot.read(path, optional=optional)
        if data is None:
            return [] if jsonl else None
        sources[sid] = {'sha256': digest(data)}
        if jsonl:
            return [parse(line) for line in data.splitlines() if line.strip()]
        return parse(data)

    original = read(manifest_path, 'fixcheck-manifest')
    original_sha = sources['fixcheck-manifest']['sha256']
    binding = read(state / 'BINDING.json', 'state-binding')
    require(binding.get('manifest_sha256') == original_sha, 'FIXCHECK manifest/state binding differs')
    require(type(original.get('schema')) is int and original['schema'] == 1 and original['method']['tag'] == 'fixcheck'
            and original['method']['arms'] == ['O'] and original['method']['cells'] == ['codex', 'claude'],
            'Unsupported FIXCHECK manifest')
    rt = original['runtime']
    require(rt['oaw_commit'] == original['candidate_commit'], 'FIXCHECK candidate contradicts runtime')
    budget = read(state / 'budget.json', 'budget')
    require(budget == rt['budget'] == {'cap': 17000000, 'decision': 'D45', 'spent_before': 0},
            'FIXCHECK budget differs')
    raises = read(state / 'budget-raise.jsonl', 'budget-raises', optional=True, jsonl=True)
    require(not raises, 'FIXCHECK budget was raised')
    for name, expected in original['files'].items():
        raw = snapshot.read(confined(Path(manifest_path).resolve().parent, name))
        require(digest(raw) == expected, 'Frozen FIXCHECK source differs')
        sources['frozen-' + ident(name, 'frozen filename')] = {'sha256': expected}
    raw = snapshot.read(Path(manifest_path).resolve().parent / 'BASELINES.json')
    require(digest(raw) == original['baseline_sha256'], 'Frozen baseline differs')
    sources['frozen-baselines'] = {'sha256': digest(raw)}
    units = {}
    for unit in original['units']:
        ident(unit['id'], 'unit id')
        require(unit['id'] not in units and unit['klass'] in ('A', 'B', 'C'), 'Duplicate/invalid frozen unit')
        units[unit['id']] = unit
    candidates = {}
    for klass in 'ABC':
        data = read(state / ('units_' + klass + '.json'), 'units-' + klass)
        require(sources['units-' + klass]['sha256'] == rt['units'][klass], 'Frozen unit bank differs')
        for unit in data['units']:
            require(unit['id'] in units and units[unit['id']]['klass'] == klass and unit['id'] not in candidates,
                    'Unit bank identity differs')
            # Match frozen H1 unit_digest: unlike normalized bundles it includes JSON spaces.
            unit_sha = digest(json.dumps(unit, sort_keys=True, ensure_ascii=False, allow_nan=False).encode())
            require(unit_sha == units[unit['id']]['sha256'], 'Frozen per-unit hash differs from bank entry')
            candidates[unit['id']] = unit.get('candidate_sha256')
    require(set(candidates) == set(units), 'Unit bank is incomplete')
    environment = digest(canonical({k: rt[k] for k in ('base_commit', 'tools', 'system_tools', 'launch')}))
    manifest = {'schema_version': 1, 'study_id': ident(original['experiment'], 'study id'),
                'protocol_sha256': original_sha, 'analysis_unit': 'diagnostic', 'grading_contract': None, 'runs': []}
    for cell in ('codex', 'claude'):
        cfg = rt['launch']['cells'][cell]
        argv = cfg['argv']
        require(isinstance(argv, list) and all(isinstance(arg, str) for arg in argv), 'Invalid launch arguments')
        if cell == 'claude':
            require(argv.count('--effort') == 1 and argv.index('--effort') + 1 < len(argv)
                    and argv[argv.index('--effort') + 1] == 'high', 'Unsupported Claude effort')
        else:
            efforts = [arg for arg in argv if arg.startswith('model_reasoning_effort=')]
            require(efforts == ['model_reasoning_effort="high"'], 'Unsupported Codex effort')
        for unit in units.values():
            manifest['runs'].append({'id': cell + ':' + unit['id'], 'task_id': unit['id'], 'arm': 'O',
                 'input_sha256': unit['sha256'], 'harness_sha256': rt['arms']['O']['content_sha256'],
                 'repeat': 1, 'split': 'development',
                 'condition': {'id': cell, 'model': cfg['model'], 'effort': 'high', 'host': cell,
                               'host_version': cfg['cli_version'], 'environment_sha256': environment}})
    bound = digest(canonical(manifest))
    bundle = {'manifest': manifest, 'manifest_sha256': bound, 'sources': sources, 'records': [], 'outcomes': []}
    input_rows, recovered, starts_all = {}, [], {}
    attempts_all = {}

    def key(row, cell):
        require(isinstance(row, dict) and row.get('cell') == cell and row.get('unit') in units, 'Unknown row identity')
        unit = units[row['unit']]
        number(row.get('attempt'), 'attempt', integer=True)
        require(row['attempt'] > 0, 'Attempt must be positive')
        expected = {'tag': 'fixcheck', 'arm': 'O', 'klass': unit['klass'], 'freeze_sha256': '',
                    'runner_sha256': rt['files']['h1_run.py'], 'units_sha256': rt['units'][unit['klass']],
                    'unit_sha256': unit['sha256'], 'candidate_sha256': candidates[unit['id']]}
        require(all(row.get(k) == v for k, v in expected.items()), 'FIXCHECK row/source identity differs')
        root = f"runs/fixcheck/{cell}/{row['unit']}/O/a{row['attempt']}"
        require(row.get('root') == root, 'Unexpected FIXCHECK attempt root')
        return root

    def grade(row, unit):
        g = row['grade']
        require(not g.get('error') and type(g.get('suite_regression')) is bool, 'Invalid mechanical grade')
        functions = g['functions']
        require(set(functions) == set(unit['functions']) and all(type(v) is bool for v in functions.values()),
                'Grade functions differ from frozen mapping')
        items = {name: bool(members) and all(functions[f] for f in members) for name, members in unit['items'].items()}
        require(g['items'] == items and all(type(v) is bool for v in g['items'].values()), 'Grade items contradict functions')
        require(type(g['n']) is int and type(g['passed']) is int and g['n'] == len(items) > 0
                and g['passed'] == sum(items.values()), 'Grade denominator differs')
        expected = 0 if g['suite_regression'] else g['passed'] / g['n']
        number(row['score'], 'score')
        require(abs(row['score'] - expected) <= 1e-12, 'Recorded score contradicts grade')
        recalls = [f for f in functions if f.startswith('test_recall_')]
        recall = (all(functions[f] for f in recalls) and not g['suite_regression']) if recalls else None
        require(g.get('recall') is recall, 'Recall contradicts grade')

    for cell in ('codex', 'claude'):
        starts = read(state / f'starts-fixcheck-{cell}.jsonl', 'starts-' + cell, optional=True, jsonl=True)
        attempts = read(state / f'attempts-fixcheck-{cell}.jsonl', 'attempts-' + cell, optional=True, jsonl=True)
        rows = read(state / f'rows-fixcheck-{cell}.jsonl', 'rows-' + cell, optional=True, jsonl=True)
        for start in starts:
            root = key(start, cell)
            require(start.get('event') == 'start' and root not in starts_all, 'Duplicate/invalid start')
            starts_all[root] = start
        valid = {}
        for attempt in attempts:
            root = key(attempt, cell)
            require(root in starts_all and root not in attempts_all, 'Attempt without start or duplicate attempt')
            require(attempt['model_asked'] == rt['launch']['cells'][cell]['model']
                    and attempt['arm_commit'] == rt['arms']['O']['commit'], 'Attempt model/candidate differs')
            if cell == 'claude':
                require(attempt['cap'] == 17000000 and attempt['cap_decision'] == 'D45', 'Wrong Claude budget identity')
            for metric in ('tokens_total', 'tokens_noncache'):
                number(attempt.get(metric), metric, integer=True)
            require(attempt['tokens_noncache'] <= attempt['tokens_total'], 'Noncache exceeds total')
            sessions = attempt['sessions']
            require(isinstance(sessions, list) and 0 < len(sessions) <= units[attempt['unit']]['sessions'], 'Session count differs')
            for session in sessions:
                for metric in ('tokens_total', 'tokens_noncache'):
                    number(session.get(metric), metric, integer=True)
                require(session['tokens_noncache'] <= session['tokens_total'], 'Session noncache exceeds total')
            require(sum(s['tokens_total'] for s in sessions) == attempt['tokens_total']
                    and sum(s['tokens_noncache'] for s in sessions) == attempt['tokens_noncache'], 'Session/attempt usage mismatch')
            number(attempt.get('seconds'), 'attempt seconds', nullable=True)
            if not attempt.get('not_run'):
                require(len(sessions) == units[attempt['unit']]['sessions'] and attempt['tokens_total'] > 0,
                        'Valid answer has missing sessions or zero tokens')
                require(all(s['tokens_total'] > 0 for s in sessions), 'Valid answer has zero session tokens')
                grade(attempt, units[attempt['unit']])
                require(attempt['unit'] not in valid, 'Multiple valid answers for one unit')
                valid[attempt['unit']] = attempt
            attempts_all[root] = attempt
        counted = {}
        for row in rows:
            root = key(row, cell)
            require(row['unit'] not in counted and root in attempts_all and not row.get('not_run'), 'Duplicate/orphan counted row')
            require(canonical(row) == canonical(attempts_all[root]), 'Counted row differs from its attempt')
            counted[row['unit']] = row
        require(set(counted) == set(valid), 'Valid attempts and counted rows are not reconciled')
        input_rows[cell] = len(rows)

    # Budget reservations are not spending. Reconcile each observed Claude session.
    ledger = read(state / 'ledger-claude.jsonl', 'claude-meter', optional=True, jsonl=True)
    meter_starts, meter_ends, meter_roots = {}, {}, {}
    for entry in ledger:
        sid = entry['key']
        require(isinstance(sid, str), 'Invalid meter key')
        matched = [root for root, start in starts_all.items() if start['cell'] == 'claude'
                   and sid.startswith(root + '/raw/s') and sid.endswith('.jsonl')]
        require(len(matched) == 1, 'Meter key has no unique declared attempt')
        root = matched[0]
        suffix = sid[len(root + '/raw/s'):-len('.jsonl')]
        require(suffix.isdigit() and str(int(suffix)) == suffix and 1 <= int(suffix) <= units[starts_all[root]['unit']]['sessions'],
                'Invalid meter session index')
        meter_roots[sid] = root
        if entry['event'] == 'start':
            require(sid not in meter_starts and entry['raw'] == sid, 'Duplicate/mismatched meter start')
            number(entry['reserve'], 'reservation', integer=True)
            meter_starts[sid] = entry
        elif entry['event'] == 'end':
            require(sid in meter_starts and sid not in meter_ends, 'Duplicate/orphan meter end')
            number(entry['tokens'], 'meter tokens', integer=True)
            meter_ends[sid] = entry
        else:
            require(False, 'Unknown meter event')
    outstanding = sum(e['reserve'] for sid, e in meter_starts.items() if sid not in meter_ends)
    for root, start in sorted(starts_all.items()):
        cell, unit = start['cell'], start['unit']
        rid = cell + ':' + unit
        attempt = attempts_all.get(root)
        if attempt is not None:
            tokens, noncache, elapsed = attempt['tokens_total'], attempt['tokens_noncache'], attempt.get('seconds')
            if cell == 'claude':
                expected_keys = {root + f'/raw/s{i}.jsonl' for i in range(1, len(attempt['sessions']) + 1)}
                require({sid for sid, value in meter_roots.items() if value == root} == expected_keys,
                        'Claude session/meter coverage differs')
                for i, session in enumerate(attempt['sessions'], 1):
                    end = meter_ends.get(root + f'/raw/s{i}.jsonl')
                    require(end and end['tokens'] == session['tokens_total'], 'Claude meter/attempt tokens differ')
            status = 'not_run' if attempt.get('not_run') else 'completed'
            reason = 'Frozen runner reports an uncounted attempt' if status == 'not_run' else ''
            refs = ['attempts-' + cell, 'starts-' + cell]
            if cell == 'claude':
                refs.append('claude-meter')
        else:
            known = [entry['tokens'] for sid, entry in meter_ends.items() if meter_roots[sid] == root]
            tokens = sum(known) if known else None
            noncache = elapsed = None
            status = 'interrupted'
            reason = 'Started attempt has no serialized completion; it may still be running'
            refs = ['starts-' + cell] + (['claude-meter'] if known else [])
        record = {'id': rid + ':a' + str(start['attempt']), 'manifest_sha256': bound, 'run_id': rid,
                  'stage': 'answer', 'attempt': start['attempt'], 'status': status, 'reason': reason,
                  'sources': refs, 'meter': 'runner', 'complete': False, 'subagents_included': False,
                  'charge_ids': [rid + ':a' + str(start['attempt'])],
                  'metrics': {'logical_tokens': tokens, 'noncache_tokens': noncache, 'cost_usd': None, 'elapsed_seconds': elapsed},
                  'produces': None, 'selects': None}
        bundle['records'].append(record)
        if attempt is not None and status == 'completed':
            bundle['outcomes'].append({'run_id': rid, 'manifest_sha256': bound, 'status': 'scored',
                    'output_sha256': None, 'identity_note': 'Legacy rows do not bind the delivered artifact; no statistical export',
                    'sources': ['rows-' + cell], 'score': attempt['score'],
                    'judge_sha256': rt['files']['h1_judge.py'], 'grading_contract': None})
            if attempt.get('recovery'):
                recovered.append({'run_id': rid, 'attempt': start['attempt'], 'logical_tokens': tokens,
                                  'row_sha256': digest(canonical(attempt)), 'elapsed_seconds': elapsed,
                                  'note': 'Preserved recovered attempt total; no new answer or regrading. Missing metadata remains unknown.'})
    report = summarize(bundle)
    report['adapter'] = {'format': 'h1-fixcheck', 'source_manifest_sha256': original_sha,
            'candidate_commit': original['candidate_commit'], 'counted_rows': input_rows,
            'claude_meter_observed_tokens': sum(e['tokens'] for e in meter_ends.values()),
            'claude_outstanding_reserve': outstanding, 'recovered_attempts': recovered,
            'limitation': 'Runner-reported observations, not independent native-trace replay. All cost completeness remains unverified. '
                          'Study/reviewer/grading overhead is unknown; no FIXCHECK threshold or effectiveness judgment was run.'}
    snapshot.verify()
    return report
