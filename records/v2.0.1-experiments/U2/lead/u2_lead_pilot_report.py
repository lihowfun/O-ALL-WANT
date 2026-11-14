#!/usr/bin/env python3
"""Lead report of the continued U2 pilot (D49): every planned run's final attempt, completed or kept at the ceiling.

The frozen `u2_report.py pilot` needs 18 completed rows with complete metering and so cannot report a pilot
that contains a kept ceiling stop. This reads the same retained files (attempt rows, checker results, trigger
files, raw host records) and prints measured numbers only. Usage: u2_lead_pilot_report.py STATE [--json OUT]
"""
import hashlib
import json
import statistics
import sys
from pathlib import Path


def strings(path):
    texts = []

    def walk(x):
        if isinstance(x, str):
            texts.append(x)
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    for line in Path(path).read_text(errors='replace').splitlines():
        try:
            walk(json.loads(line))
        except ValueError:
            pass
    return '\n'.join(texts)


def main():
    state = Path(sys.argv[1])
    attempts = [json.loads(line) for line in (state / 'attempts-codex.jsonl').read_text().splitlines() if line.strip()]
    final = {}
    for order, a in enumerate(attempts, 1):
        final[a['run_id']] = (order, a)   # the last attempt of a run is its final one
    rows = []
    for run_id, (order, a) in sorted(final.items(), key=lambda kv: kv[1][0]):
        base = state / 'runs/codex' / run_id / ('attempt-' + str(a['attempt']))
        result = json.loads((base / 'checker/result.json').read_text())
        mech = [i for i in result['items'] if i['by'] == 'check']
        work = base / 'run/workspace'
        extra = sorted(str(p.relative_to(work)) for d in ('review_out', '.oaw/improvements') if (work / d).exists()
                       for p in (work / d).rglob('*') if p.is_file()
                       and str(p.relative_to(work)) not in ('review_out/decision.md', 'review_out/proposed.patch'))
        patch = work / 'review_out/proposed.patch'
        card = base / 'run/baseline/.agents/skills/oaw-improve/references/minimal-change-card.md'
        card_lines = None
        if card.exists():
            lines = [l.strip() for l in card.read_text().splitlines() if l.strip()]
            joined = strings(base / 'all-native.jsonl')
            card_lines = [sum(1 for l in lines if l in joined), len(lines)]
        rows.append({
            'order': order, 'run_id': run_id, 'task': a['task_id'], 'arm': a['arm'], 'repeat': a['repeat'],
            'status': a['status'], 'exit': a.get('exit'), 'truncated': bool(a.get('truncated')),
            'kept_ceiling_stop': a['status'] != 'completed' and a.get('exit') == 'token_ceiling' and bool(a.get('truncated')),
            'above_ceiling': (a['meter'].get('logical_tokens') or 0) > 600000,
            'logical_tokens': a['meter'].get('logical_tokens'), 'noncache_tokens': a['meter'].get('noncache_tokens'),
            'meter_complete': a['meter'].get('complete'), 'seconds': round(a['meter'].get('elapsed_seconds') or 0),
            'mechanical_met': sum(i['met'] is True for i in mech), 'mechanical_total': len(mech),
            'unmet': [i['id'] for i in mech if i['met'] is not True], 'severe': result['severe'], 'burden': result['burden'],
            'extra_files': len(extra), 'patch_sha256': hashlib.sha256(patch.read_bytes()).hexdigest()[:10] if patch.exists() else None,
            'instrument_read': a['trigger'].get('attachment_read'), 'card_lines_in_tool_output': card_lines})
    cells = {}
    for r in rows:
        cells.setdefault((r['task'], r['arm']), []).append(r)
    summary = []
    for (task, arm), rs in sorted(cells.items()):
        rs.sort(key=lambda r: r['repeat'])
        tokens = [r['logical_tokens'] for r in rs]
        summary.append({'task': task, 'arm': arm, 'runs': len(rs), 'kept_ceiling_stops': sum(r['kept_ceiling_stop'] for r in rs),
                        'tokens_by_repeat': tokens, 'mean_tokens_lower_bound' if any(r['meter_complete'] is not True for r in rs) else 'mean_tokens':
                        round(statistics.fmean(tokens), 2),
                        'mechanical_by_repeat': [f"{r['mechanical_met']}/{r['mechanical_total']}" for r in rs],
                        'unmet_ids': sorted({u for r in rs for u in r['unmet']}),
                        'patches': sorted({r['patch_sha256'] for r in rs if r['patch_sha256']}),
                        'card_full_reads_by_lines': sum(1 for r in rs if r['card_lines_in_tool_output']
                                                        and r['card_lines_in_tool_output'][0] == r['card_lines_in_tool_output'][1]) if arm == 'B' else None,
                        'instrument_reads': [r['instrument_read'] for r in rs] if arm == 'B' else None})
    arm_means = {arm: statistics.fmean(r['logical_tokens'] for r in rows if r['arm'] == arm) for arm in 'ABN'}
    highest = max(arm_means.values())
    out = {'planned': 18, 'final_attempts': len(rows), 'completed': sum(r['status'] == 'completed' for r in rows),
           'kept_ceiling_stops': [r['run_id'] for r in rows if r['kept_ceiling_stop']],
           'completed_above_ceiling': [r['run_id'] for r in rows if r['status'] == 'completed' and r['above_ceiling']],
           'arm_means_are_lower_bounds': sorted({r['arm'] for r in rows if r['meter_complete'] is not True}),
           'attempt_rows': len(attempts), 'total_logical_tokens_all_attempts': sum(a['meter'].get('logical_tokens') or 0 for a in attempts),
           'arm_means': {k: round(v, 2) for k, v in arm_means.items()},
           'projection_highest_observed_arm_mean_x108_x1_3_lower_bound': round(highest * 108 * 1.3, 2),
           'cells_all_items_met_in_all_repeats': sum(all(r['mechanical_met'] == r['mechanical_total'] for r in rs) and len(rs) == 3
                                                     for rs in cells.values()),
           'runs_all_items_met': sum(r['mechanical_met'] == r['mechanical_total'] for r in rows),
           'any_severe': any(r['severe'] for r in rows), 'cells': summary, 'runs': rows}
    if '--json' in sys.argv:
        Path(sys.argv[sys.argv.index('--json') + 1]).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: v for k, v in out.items() if k != 'runs'}, indent=1, ensure_ascii=False))
    print('| # | run | status | tokens | noncache | s | mech | unmet | extra files | patch | instrument | card lines |')
    for r in rows:
        print('|', ' | '.join(str(x) for x in (r['order'], r['run_id'], r['status'] + ('/kept ceiling stop' if r['kept_ceiling_stop'] else '/above ceiling' if r['above_ceiling'] else ''), r['logical_tokens'],
                                               r['noncache_tokens'], r['seconds'], f"{r['mechanical_met']}/{r['mechanical_total']}",
                                               ','.join(r['unmet']) or '-', r['extra_files'], r['patch_sha256'], r['instrument_read'],
                                               r['card_lines_in_tool_output'])), '|')


if __name__ == '__main__':
    main()
