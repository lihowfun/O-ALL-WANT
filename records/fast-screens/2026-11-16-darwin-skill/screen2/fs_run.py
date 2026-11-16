#!/usr/bin/python3
"""Fast screen of one food on real answers: sandboxed fresh-context runs, the JEV judge, the verdict.

    fs_run.py preflight ARM          probe run through the exact launch path (not a study run)
    fs_run.py answer TASK ARM        one fresh run; ARM = native | food
    fs_run.py judge TASK ARM         JEV judge (tool-free) + checked labels
    fs_run.py verdict                write screen.json from what exists and run the verdict

Raw event streams and the fresh HOME stay in STATE on the local disk. This folder keeps prompts,
answers, judge replies, checked labels, per-run rows and the screen file.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE = Path(os.environ.get('FS_STATE', str(Path.home() / 'oaw-fs' / 'darwin-1')))
CLI = Path(os.environ.get('FS_CLI', str(Path.home() / 'oaw-runtime/claude/claude')))
CREDENTIAL = Path(os.environ.get('FS_CREDENTIAL', str(Path.home() / '.claude/.credentials.json')))
FOOD_SRC = Path(os.environ['FS_FOOD_SRC']) if 'FS_FOOD_SRC' in os.environ else None
FOOD_NAME = 'darwin-skill'
TOOL = Path(os.environ.get('FAST_SCREEN', 'scripts/fast_screen.py'))
JEV_DIR = os.environ.get('JEV_DIR')
MODEL, EFFORT, FAMILY = 'claude-opus-5-5', 'high', 'claude'
TOOLS = 'Read,Glob,Grep,Skill'
JUDGE = ('claude-haiku-5-5', 'low')
IN_HOME, IN_WORK, IN_RT = '/home/dev', '/home/dev/proj', '/opt/rt'
PROBE = '請列出你現在可以使用的 skill 名稱，每行一個；沒有就回答「沒有」。不要做別的事。'


def bubblewrap(home, work, inner):
    runtime = CLI.resolve().parent
    argv = ['bwrap', '--tmpfs', '/', '--ro-bind', '/usr', '/usr', '--ro-bind', '/bin', '/bin',
            '--ro-bind', '/lib', '/lib', '--ro-bind', '/lib64', '/lib64', '--dir', '/etc']
    for p in ('/etc/ssl', '/etc/resolv.conf', '/etc/hosts', '/etc/nsswitch.conf'):
        if Path(p).exists():
            argv += ['--ro-bind', str(Path(p).resolve()), p]
    argv += ['--dev', '/dev', '--proc', '/proc', '--tmpfs', '/tmp', '--dir', '/home',
             '--bind', str(home), IN_HOME, '--bind', str(work), IN_WORK,
             '--dir', '/opt', '--ro-bind', str(runtime), IN_RT,
             '--chdir', IN_WORK, '--die-with-parent', '--unshare-ipc', '--unshare-pid']
    return argv + [IN_RT + '/' + CLI.name] + inner


def run(ident, arm, prompt, timeout=900):
    folder = STATE / 'runs' / ident
    if folder.exists():
        raise SystemExit(f'{ident}: already issued; no redraw')
    home, work = folder / 'home', folder / 'work'
    (home / '.claude').mkdir(parents=True, mode=0o700)
    work.mkdir(mode=0o700)
    (work / 'README.md').write_text('# demo project\n\nA small project used for one question.\n', encoding='utf-8')
    if arm == 'food':
        shutil.copytree(FOOD_SRC, work / '.claude' / 'skills' / FOOD_NAME)
    (home / 'settings.json').write_text(json.dumps({
        'permissions': {'deny': ['WebSearch', 'WebFetch', 'Bash', 'Write', 'Edit', 'NotebookEdit',
                                 f'Read({IN_HOME}/.claude/**)', f'Read({IN_HOME}/settings.json)'],
                        'allow': [f'Read({IN_WORK}/**)']},
        'disableAllHooks': True, 'enabledPlugins': {}}), encoding='utf-8')
    copy = home / '.claude/.credentials.json'
    shutil.copyfile(CREDENTIAL, copy)
    os.chmod(copy, 0o600)
    inner = ['-p', prompt, '--output-format', 'stream-json', '--verbose', '--model', MODEL, '--effort', EFFORT,
             '--tools', TOOLS, '--permission-mode', 'acceptEdits', '--setting-sources', 'project',
             '--settings', IN_HOME + '/settings.json', '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
             '--no-session-persistence']
    env = {'HOME': IN_HOME, 'PATH': IN_RT + ':/usr/bin:/bin', 'DISABLE_AUTOUPDATER': '1', 'LANG': 'C.UTF-8'}
    started = time.time()
    try:
        done = subprocess.run(bubblewrap(home, work, inner), capture_output=True, text=True, env=env,
                              timeout=timeout, cwd=str(work))
        out, err, code = done.stdout, done.stderr, done.returncode
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or '')
        err, code = 'timeout', -1
    finally:
        copy.write_bytes(b'')
    seconds = round(time.time() - started, 1)
    (folder / 'events.jsonl').write_text(out, encoding='utf-8')
    (folder / 'stderr.txt').write_text(err, encoding='utf-8')
    row = {'id': ident, 'arm': arm, 'model': MODEL, 'effort': EFFORT, 'tools_allowed': TOOLS, 'exit': code,
           'seconds': seconds, 'logical_tokens': None, 'noncache_tokens': None, 'models_used': [],
           'listed_skills': None, 'tool_calls': {}, 'skill_calls': [], 'skill_file_reads': 0, 'is_error': None}
    answer = ''
    for line in out.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get('type') == 'system' and event.get('subtype') == 'init':
            row['listed_skills'] = sorted(str(s) for s in event.get('skills') or [])
        elif event.get('type') == 'assistant':
            for block in (event.get('message') or {}).get('content') or []:
                if block.get('type') == 'tool_use':
                    name = block.get('name')
                    row['tool_calls'][name] = row['tool_calls'].get(name, 0) + 1
                    payload = block.get('input') or {}
                    if name == 'Skill':
                        row['skill_calls'].append(str(payload.get('skill', '')))
                    if name == 'Read' and f'skills/{FOOD_NAME}/' in str(payload.get('file_path', '')):
                        row['skill_file_reads'] += 1
        elif event.get('type') == 'result':
            usage = event.get('modelUsage') or {}
            logical = noncache = 0
            for u in usage.values():
                parts = [u.get(k, 0) or 0 for k in ('inputTokens', 'outputTokens', 'cacheReadInputTokens',
                                                    'cacheCreationInputTokens')]
                logical += sum(parts)
                noncache += sum(parts) - parts[2]
            row.update(logical_tokens=logical, noncache_tokens=noncache, models_used=sorted(usage),
                       is_error=bool(event.get('is_error')))
            answer = event.get('result') or ''
    (folder / 'row.json').write_text(json.dumps(row, ensure_ascii=False, indent=1), encoding='utf-8')
    return answer, row


def tool(*args):
    done = subprocess.run(['/usr/bin/python3', str(TOOL), *map(str, args)], capture_output=True, text=True)
    return done.returncode, done.stdout, done.stderr


def cmd_preflight(arm):
    answer, row = run(f'preflight-{arm}-{int(time.time())}', arm, PROBE, timeout=300)
    print(json.dumps(row, ensure_ascii=False))
    print('ANSWER:', answer[:400])


def cmd_answer(task, arm):
    prompt = json.loads((HERE / 'tasks.json').read_text(encoding='utf-8'))[task]['prompt']
    if arm == 'food':
        prompt = os.environ.get('FS_FOOD_PREFIX', '') + prompt
    answer, row = run(f'{task}-{arm}', arm, prompt)
    if row['exit'] != 0 or row['is_error'] or not answer.strip():
        print(json.dumps(row, ensure_ascii=False))
        raise SystemExit(f'{task}-{arm}: run did not produce an answer')
    (HERE / f'{task}-{arm}-answer.txt').write_text(answer, encoding='utf-8')
    (HERE / f'{task}-{arm}-row.json').write_text(json.dumps(row, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k: row[k] for k in ('id', 'seconds', 'logical_tokens', 'listed_skills', 'tool_calls',
                                           'skill_calls', 'skill_file_reads')}, ensure_ascii=False))


def cmd_judge(task, arm):
    sys.path.insert(0, JEV_DIR)
    import jev_calibrate as J
    checklist, answer = HERE / f'{task}-checklist.json', HERE / f'{task}-{arm}-answer.txt'
    code, prompt, err = tool('prompt', '--checklist', checklist, '--answer', answer)
    if code != 0:
        raise SystemExit('prompt failed: ' + err)
    ident = f'{task}-{arm}'
    text, usage = J.call(STATE / 'judge', ident, prompt.rstrip('\n') + '\n', *JUDGE)
    reply, labels = HERE / f'{ident}-reply.json', HERE / f'{ident}-labels.json'
    reply.write_text(text, encoding='utf-8')
    code, out, err = tool('labels', '--checklist', checklist, '--answer', answer, '--reply', reply, '--out', labels,
                          '--judge', ' '.join(JUDGE), '--judge-tokens', usage['logical_tokens'] or 0, '--format', 'json')
    checked = json.loads(labels.read_text()) if labels.exists() else {}
    record = {'call': ident, 'exit': usage['exit'], 'error': usage['is_error'], 'seconds': usage['seconds'],
              'judge_tokens': usage['logical_tokens'], 'labels_exit': code, 'counts': checked.get('counts'),
              'items': {i['id']: i['label'] for i in checked.get('items', [])},
              'reasons': sorted({i['reason'] for i in checked.get('items', []) if i.get('reason')})}
    (HERE / f'{ident}-judge.json').write_text(json.dumps(record, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(record, ensure_ascii=False))


def cmd_verdict():
    static = json.loads((HERE / 'static.json').read_text(encoding='utf-8'))
    tasks = []
    for task in sorted(json.loads((HERE / 'tasks.json').read_text(encoding='utf-8'))):
        entry = {'id': task}
        for arm in ('native', 'food'):
            row, labels = HERE / f'{task}-{arm}-row.json', HERE / f'{task}-{arm}-labels.json'
            if row.exists() and labels.exists():
                r = json.loads(row.read_text())
                entry[arm] = {'labels': labels.name, 'logical_tokens': r['logical_tokens'], 'seconds': r['seconds'],
                              'family': FAMILY}
            else:
                entry[arm] = None
        tasks.append(entry)
    screen = {'food': static['food'], 'static': {'status': static['status'], 'reason': static['reason']}, 'tasks': tasks}
    (HERE / 'screen.json').write_text(json.dumps(screen, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    code, out, err = tool('verdict', '--screen', HERE / 'screen.json', '--format', 'json')
    (HERE / 'verdict.json').write_text(out, encoding='utf-8')
    print('exit', code)
    print(out if out else err)


if __name__ == '__main__':
    STATE.mkdir(parents=True, exist_ok=True)
    os.chmod(STATE, 0o700)
    command, args = sys.argv[1], sys.argv[2:]
    {'preflight': cmd_preflight, 'answer': cmd_answer, 'judge': cmd_judge, 'verdict': cmd_verdict}[command](*args)
