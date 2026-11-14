#!/usr/bin/env python3
"""First real example of the fast decision (D50): the minimal-change card, on existing U2 answers.

Follows EXAMPLE_PLAN.md. Usage:
    run_example.py prepare          build checklists, answers and the screen skeleton (no model call)
    run_example.py judge ARM        ARM = native (arm A) or food (arm B): judge, check labels
    run_example.py verdict          run fast_screen.py verdict on the current screen

State (judge calls with a fresh HOME) stays on the local disk; the example folder holds only
checklists, answers, replies, checked labels and the screen file.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import jev_calibrate as J  # noqa: E402  (reuses the tool-free judge call)

TOOL = Path(os.environ.get('FAST_SCREEN', 'scripts/fast_screen.py'))
TRUTH = {'P1': '<u2-tasks>/pilot/P1/hidden/truth.json',
         'P2': '<u2-tasks>/pilot/P2/hidden/truth.json',
         'D2': '<u2-tasks>/dev/D2/hidden/truth.json'}
COUNTED = {'P1': 'abcdefgh', 'P2': 'abcdefgh', 'D2': 'abcdi'}
READER = {'P1': 'lmno', 'P2': 'lmno', 'D2': 'jkl'}
RUNS = {('P1', 'native'): ('state5', 'pilot-P1-A-r1'), ('P1', 'food'): ('state5', 'pilot-P1-B-r1'),
        ('P2', 'native'): ('state5', 'pilot-P2-A-r1'), ('P2', 'food'): ('state5', 'pilot-P2-B-r1'),
        ('D2', 'native'): ('state4', 'development-D2-A-r1'), ('D2', 'food'): ('state4', 'development-D2-B-r1')}
U2 = Path.home() / 'oaw-u2'
STATE = Path.home() / 'oaw-jev' / 'example1'
JUDGE = ('claude-haiku-5-5', 'low')


def tool(*args):
    done = subprocess.run(['/usr/bin/python3', str(TOOL), *map(str, args)], capture_output=True, text=True)
    return done.returncode, done.stdout, done.stderr


def prepare():
    screen = {'food': 'minimal-change card (OAW 2.0.1 improve skill with the card)',
              'static': {'status': 'clear', 'reason': 'Markdown reference text only; no code, dependency or licence question'},
              'tasks': []}
    for task in ('P1', 'P2', 'D2'):
        items = {i['id'].split('.')[-1]: i for i in json.loads(Path(TRUTH[task]).read_text())['items']}
        for kind, letters in (('counted', COUNTED[task]), ('reader', READER[task])):
            checklist = {'task_id': task, 'items': [{'id': task + '.' + x, 'text': items[x]['text']} for x in letters]}
            (HERE / f'{task}-{kind}-checklist.json').write_text(json.dumps(checklist, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
        entry = {'id': task}
        for arm in ('native', 'food'):
            state, run_id = RUNS[(task, arm)]
            base = U2 / state / 'runs/codex' / run_id / 'attempt-1'
            work = base / 'run/workspace/review_out'
            patch = work / 'proposed.patch'
            answer = ('## review_out/decision.md\n\n' + (work / 'decision.md').read_text(encoding='utf-8').rstrip('\n')
                      + '\n\n## review_out/proposed.patch\n\n' + (patch.read_text(encoding='utf-8') if patch.exists() else '(no file)\n'))
            (HERE / f'{task}-{arm}-answer.txt').write_text(answer, encoding='utf-8')
            row = json.loads((base / 'row.json').read_text())
            entry[arm + '_recorded'] = {'run_id': run_id, 'labels': f'{task}-{arm}-counted-labels.json',
                                        'logical_tokens': row['meter']['logical_tokens'],
                                        'seconds': round(row['meter']['elapsed_seconds'], 1), 'family': 'codex'}
        screen['tasks'].append(entry)
    (HERE / 'runs.json').write_text(json.dumps(screen, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    write_screen(with_food=False)
    print('prepared', sorted(p.name for p in HERE.glob('*-checklist.json')))


def write_screen(with_food):
    runs = json.loads((HERE / 'runs.json').read_text())
    screen = {'food': runs['food'], 'static': runs['static'], 'tasks': []}
    for t in runs['tasks']:
        def run(arm):
            r = t[arm + '_recorded']
            return {k: r[k] for k in ('labels', 'logical_tokens', 'seconds', 'family')}
        screen['tasks'].append({'id': t['id'], 'native': run('native'), 'food': run('food') if with_food else None})
    (HERE / 'screen.json').write_text(json.dumps(screen, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')


def judge(arm):
    STATE.mkdir(parents=True, exist_ok=True)
    os.chmod(STATE, 0o700)
    summary = []
    for task in ('P1', 'P2', 'D2'):
        answer = HERE / f'{task}-{arm}-answer.txt'
        for kind in ('counted', 'reader'):
            checklist = HERE / f'{task}-{kind}-checklist.json'
            code, prompt, err = tool('prompt', '--checklist', checklist, '--answer', answer)
            if code != 0:
                raise SystemExit('prompt failed: ' + err + prompt)
            ident = f'{task}-{arm}-{kind}'
            text, usage = J.call(STATE, ident, prompt.rstrip('\n') + '\n', *JUDGE)
            reply = HERE / f'{ident}-reply.json'
            reply.write_text(text, encoding='utf-8')
            labels = HERE / f'{ident}-labels.json'
            code, out, err = tool('labels', '--checklist', checklist, '--answer', answer, '--reply', reply, '--out', labels,
                                  '--judge', 'claude-haiku-5-5 low', '--judge-tokens', usage['logical_tokens'] or 0, '--format', 'json')
            checked = json.loads(labels.read_text()) if labels.exists() else {}
            summary.append({'call': ident, 'exit': usage['exit'], 'error': usage['is_error'], 'seconds': usage['seconds'],
                            'judge_tokens': usage['logical_tokens'], 'labels_exit': code, 'counts': checked.get('counts'),
                            'reasons': sorted({i['reason'] for i in checked.get('items', []) if i['reason']})})
            print(json.dumps(summary[-1], ensure_ascii=False), flush=True)
    (HERE / f'judge-{arm}-summary.json').write_text(json.dumps(summary, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')


def verdict():
    code, out, err = tool('verdict', '--screen', HERE / 'screen.json', '--format', 'json')
    (HERE / 'verdict.json').write_text(out, encoding='utf-8')
    print('exit', code)
    print(out or err)


if __name__ == '__main__':
    command = sys.argv[1]
    if command == 'prepare':
        prepare()
    elif command == 'judge':
        judge(sys.argv[2])
    elif command == 'screen':
        write_screen(with_food=sys.argv[2] == 'with-food')
    elif command == 'verdict':
        verdict()
    else:
        raise SystemExit(__doc__)
