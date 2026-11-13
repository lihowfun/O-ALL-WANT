#!/usr/bin/env python3
"""Native-only screen runner. No grading, key reads, EGM or automatic continuation.

Adapted from X2 x2_run.py. Real execution requires a frozen offline gate and
private local storage. --dry-run never executes any CLI, even --version.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
from cal_common import append, canonical, hexsha, load, require, rows, save, sha
import build_packet
import cal_sandbox

HERE = Path(__file__).resolve().parent
CELLS = {'claude': ('claude-opus-5-5', '2.1.322'), 'codex': ('gpt-6.1-sol', '0.167.2')}
LIMIT = re.compile(r"hit your (?:\w+ )?limit|usage limit reached|you've reached your usage limit|limit \W* resets \d", re.I)
STAGE_CAP, EXPERIMENT_CAP, N_CAP = 15_000_000, 30_000_000, 8_000_000
# Engineering allowance, never a proven bound on unobserved usage.
DEFAULT_INFLIGHT = 1_000_000
PREFLIGHT_CAP = 500_000
REJECT_ENV = ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_BASE_URL',
              'OPENAI_API_KEY', 'OPENAI_BASE_URL', 'AZURE_OPENAI_API_KEY',
              'CLAUDE_CODE_OAUTH_TOKEN', 'CLAUDE_CODE_USE_BEDROCK', 'CLAUDE_CODE_USE_VERTEX')


def no_api_keys(env):
    bad = [k for k, v in env.items() if v and (k in REJECT_ENV or k.endswith('_API_KEY'))]
    require(not bad, 'API key/token/provider override environment is set; subscription only')


def code_digest():
    names = ('cal_run.py', 'cal_sandbox.py', 'cal_common.py', 'build_packet.py', 'cal_ledger.py')
    return sha(canonical({n: sha((HERE / n).read_bytes()) for n in names}))


def frozen():
    spec = load(HERE / 'freeze_manifest.json')
    for name, digest in spec['files'].items():
        require(sha((HERE / name).read_bytes()) == digest, 'frozen protocol/tool bytes changed')
    return sha(canonical(spec))


def usage_values(value, keys):
    # Partial/invalid schemas still carry an observed lower bound.
    return sum(value[k] for k in keys if isinstance(value, dict)
               and type(value.get(k)) is int and value[k] >= 0)


def usage_schema(value, keys):
    return isinstance(value, dict) and all(type(value.get(k)) is int and value[k] >= 0 for k in keys)


CLAUDE_COUNTERS = ('inputTokens', 'outputTokens', 'cacheReadInputTokens', 'cacheCreationInputTokens')
CODEX_COUNTERS = ('input_tokens', 'output_tokens', 'cached_input_tokens')


def codex_counters(value):
    input_tokens = usage_values(value, ('input_tokens',))
    output = usage_values(value, ('output_tokens',))
    # Without a cache counter, input might all be cached: only output is known noncache.
    cached = value.get('cached_input_tokens') if isinstance(value, dict) else None
    noncache = output + max(0, input_tokens - cached) if type(cached) is int and cached >= 0 else output
    return input_tokens + output, noncache


def events(path):
    found = []
    invalid = 0
    if not Path(path).exists():
        return found, invalid
    data = Path(path).read_bytes()
    # A live writer may have one incomplete trailing line; final checks reject it.
    for line in data.splitlines(keepends=True):
        if not line.endswith(b'\n'):
            continue
        try:
            found.append(json.loads(line))
        except (ValueError, UnicodeError):
            invalid += 1
    return found, invalid


def claude_usage(path):
    stream, invalid = events(path)
    messages, models, root_result = {}, {}, None
    result = {'tokens_total': 0, 'tokens_noncache': 0, 'metering_complete': False,
              'api_key_source': None, 'result_seen': False, 'model': None,
              'agents': 0, 'invalid_events': invalid, 'is_error': False, 'infrastructure_failure': False}
    for e in stream:
        if e.get('type') == 'system' and e.get('subtype') == 'init':
            result.update(api_key_source=e.get('apiKeySource'), model=e.get('model'),
                          cli_version=e.get('claude_code_version'))
        if e.get('type') == 'assistant':
            m = e.get('message') or {}
            if m.get('id') and m.get('usage'):
                messages[m['id']] = m['usage']  # dedup repeated thinking/text/tool blocks
            result['agents'] += sum(b.get('type') == 'tool_use' and b.get('name') in ('Agent', 'Task')
                                    for b in m.get('content', []))
        if e.get('type') == 'result' and not e.get('parent_tool_use_id'):
            root_result = e
            models = e.get('modelUsage') if isinstance(e.get('modelUsage'), dict) else {}
    streamed = sum(usage_values(u, ('input_tokens', 'output_tokens', 'cache_read_input_tokens',
                                    'cache_creation_input_tokens')) for u in messages.values())
    noncache = sum(usage_values(u, ('input_tokens', 'output_tokens', 'cache_creation_input_tokens'))
                   for u in messages.values())
    total = sum(usage_values(u, ('inputTokens', 'outputTokens', 'cacheReadInputTokens',
                                'cacheCreationInputTokens')) for u in models.values())
    rest = sum(usage_values(u, ('inputTokens', 'outputTokens', 'cacheCreationInputTokens'))
               for u in models.values())
    complete = bool(root_result and models and all(usage_schema(u, CLAUDE_COUNTERS) for u in models.values())
                    and total > 0 and total >= streamed and not invalid)
    result.update(tokens_total=max(total, streamed), tokens_noncache=max(rest, noncache),
                  streamed_lower_bound=streamed, model_usage=models, metering_complete=complete,
                  tokens_from='modelUsage (all models/subagents)' if complete else 'stream lower bound',
                  result_seen=bool(root_result), is_error=bool(root_result and root_result.get('is_error')),
                  limit_seen=bool(root_result and LIMIT.search(str(root_result.get('result', ''))[:600])))
    result['models_seen'] = sorted(models)
    result['infrastructure_failure'] = bool(root_result and root_result.get('error_code') in
                                            ('connection_error', 'service_unavailable', 'transport_error'))
    return result


def rollout(path):
    stream, invalid = events(path)
    meta, last, models, finished = {}, None, set(), False
    valid_usage = True
    for e in stream:
        if e.get('type') == 'session_meta':
            meta = e.get('payload') or {}
        if (e.get('payload') or {}).get('type') in ('task_complete', 'turn_complete'):
            finished = True
        if e.get('type') == 'turn_context' and (e.get('payload') or {}).get('model'):
            models.add(e['payload']['model'])
        if (e.get('payload') or {}).get('type') == 'token_count':
            value = (e['payload'].get('info') or {}).get('total_token_usage')
            valid_usage = valid_usage and usage_schema(value, CODEX_COUNTERS)
            # A later empty bucket must not erase earlier observed usage.
            if isinstance(value, dict):
                observed = codex_counters(value)
                valid_usage = valid_usage and usage_values(value, ('cached_input_tokens',)) <= usage_values(value, ('input_tokens',))
                last = tuple(max(a, b) for a, b in zip(last or (0, 0), observed))
    meta['_models_seen'] = sorted(models)
    meta['_finished'] = finished
    meta['_usage_complete'] = valid_usage and last is not None
    if last is not None:
        return meta, last, invalid
    return meta, None, invalid


def codex_usage(raw, home, work):
    stream, invalid = events(raw)
    root, parent, rest, result_seen, errors = None, 0, 0, False, []
    valid_usage = True
    for e in stream:
        if e.get('type') == 'thread.started':
            root = e.get('thread_id')
        if e.get('type') == 'turn.completed':
            result_seen = True
            u = e.get('usage') or {}
            valid_usage = valid_usage and usage_schema(u, CODEX_COUNTERS)
            t, noncache = codex_counters(u)
            parent += t
            cached = usage_values(u, ('cached_input_tokens',))
            valid_usage = valid_usage and cached <= usage_values(u, ('input_tokens',))
            rest += noncache
        if e.get('type') in ('error', 'turn.failed'):
            errors.append(e)
    found = {}
    unknown = []
    for path in sorted((Path(home) / '.codex' / 'sessions').rglob('rollout-*.jsonl')):
        meta, value, malformed = rollout(path)
        invalid += malformed
        ident = meta.get('id')
        if not ident or ident in found or Path(meta.get('cwd', '/')).resolve() != Path(work).resolve():
            unknown.append(path.name)
        else:
            found[ident] = (meta, value)
    tree = {root} if root else set()
    while True:
        new = {i for i, (m, _) in found.items() if m.get('parent_thread_id') in tree}
        if new <= tree:
            break
        tree |= new
    stray = set(found) - tree
    own = found.get(root, ({}, None))[1]
    missing = [i for i in tree if i not in found or found[i][1] is None]
    total, noncache = (max(own[0], parent), max(own[1], rest)) if own else (parent, rest)
    for ident in tree - {root}:
        value = found.get(ident, ({}, None))[1]
        if value:
            total += value[0]
            noncache += value[1]
    complete = bool(root and own and total > 0 and valid_usage and not missing and not stray and not unknown and not invalid
                    and all(found[i][0].get('_finished') and found[i][0].get('_usage_complete') for i in tree if i in found)
                    and own == (parent, rest))
    return {'tokens_total': total, 'tokens_noncache': noncache, 'metering_complete': complete,
            'result_seen': result_seen, 'is_error': bool(errors), 'root_id': root,
            'agents': len(tree - {root}), 'child_usage_missing': len(missing),
            'models_seen': sorted({model for ident in tree if ident in found for model in found[ident][0].get('_models_seen', [])}),
            'stray_rollouts': len(stray) + len(unknown), 'invalid_events': invalid,
            'limit_seen': bool(LIMIT.search(json.dumps(errors))),
            'tokens_from': 'rollouts (root and descendants)' if complete else 'incomplete lower bound',
            'infrastructure_failure': any((e.get('error') or {}).get('code') in
                                          ('connection_error', 'service_unavailable', 'transport_error') for e in errors),
            'thread_usage': {i: found[i][1] for i in sorted(tree) if i in found}}


def validate_report(value):
    require(isinstance(value, dict) and type(value.get('completed')) is bool, 'bad report completed')
    require(isinstance(value.get('findings'), list) and isinstance(value.get('uncertainties'), list), 'bad report lists')
    for finding in value['findings']:
        require(isinstance(finding, dict), 'bad finding')
        for key in ('location', 'claim', 'evidence', 'rationale', 'severity'):
            require(isinstance(finding.get(key), str) and finding[key].strip(), 'bad finding field')
    require(len(json.dumps(value, ensure_ascii=False).split()) <= 1500, 'report exceeds whitespace word limit')
    return value


def item_ids(report, prefix=''):
    return {f'{prefix}{k}{i:03d}' for field, k in (('findings', 'F'), ('uncertainties', 'U'))
            for i in range(1, len(report[field]) + 1)}


def validate_mapping(mapping, reports, output):
    require(mapping.get('schema_version') == 1 and isinstance(mapping.get('mapping'), list)
            and isinstance(mapping.get('contradictions'), list), 'bad merge mapping')
    expected = item_ids(reports[0], 'A:') | item_ids(reports[1], 'B:')
    outputs = item_ids(output)
    seen, covered = set(), set()
    for m in mapping['mapping']:
        i, targets = m.get('input_id'), m.get('output_ids')
        require(i in expected and i not in seen and m.get('action') in ('kept', 'dropped'), 'bad/duplicate merge input')
        require(isinstance(targets, list) and set(targets) <= outputs and len(set(targets)) == len(targets), 'bad merge target')
        require(m.get('reason') and (targets or m['action'] == 'dropped'), 'missing merge rationale/target')
        if ':U' in i:
            require(all(t.startswith('U') for t in targets), 'merge promoted an uncertainty')
        seen.add(i)
        covered.update(targets)
    require(seen == expected and covered == outputs, 'merge mapping coverage incomplete')
    for c in mapping['contradictions']:
        require(isinstance(c.get('input_ids'), list) and len(c['input_ids']) >= 2 and
                set(c['input_ids']) <= expected and isinstance(c.get('output_ids'), list) and
                len(c['output_ids']) >= 2 and set(c['output_ids']) <= outputs and c.get('reason'), 'bad contradiction mapping')


def auth_home(cell, auth_path, home):
    auth = load(auth_path)
    if cell == 'claude':
        require(isinstance(auth.get('claudeAiOauth'), dict) and auth['claudeAiOauth'].get('accessToken'), 'Claude subscription OAuth file required')
        require(not any('api' in str(k).lower() and v for k, v in auth.items()), 'API credential in auth file')
        dest = home / '.claude' / '.credentials.json'
    else:
        require(auth.get('auth_mode') == 'chatgpt' and auth.get('tokens') and not auth.get('OPENAI_API_KEY'), 'ChatGPT subscription auth file required')
        dest = home / '.codex' / 'auth.json'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(Path(auth_path).read_bytes())
    dest.chmod(0o600)
    return 'subscription_oauth' if cell == 'claude' else 'subscription_chatgpt'


def argv_for(cell, cli, work, prompt, settings, model=None):
    model = model or CELLS[cell][0]
    if cell == 'claude':
        return [cli, '-p'] + ([] if model == 'claude-fable-5-2' else [prompt]) + ['--output-format', 'stream-json', '--verbose', '--model', model,
                '--effort', 'high', '--tools', '' if model == 'claude-fable-5-2' else 'Read,Write,Glob,Grep,Agent,Skill',
                '--permission-mode', 'acceptEdits', '--setting-sources', 'project',
                '--settings', str(settings), '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
                '--no-session-persistence']
    return [cli, 'exec', '--json', '--model', model, '-c', 'model_reasoning_effort="high"',
            '-c', 'web_search="disabled"', '-c', 'sandbox_workspace_write.network_access=false',
            '-c', 'sandbox_workspace_write.exclude_tmpdir_env_var=true',
            '-c', 'sandbox_workspace_write.exclude_slash_tmp=true',
            '--sandbox', 'workspace-write', '--skip-git-repo-check', '--ignore-user-config', '--cd', str(work), '-']


def get_usage(cell, raw, home, work):
    return claude_usage(raw) if cell == 'claude' else codex_usage(raw, home, work)


def execute(cell, cli, work, home, attempt_dir, prompt, timeout, token_allowance, reserve, model=None):
    raw, err = attempt_dir / 'events.jsonl', attempt_dir / 'stderr.txt'
    settings = home / 'settings.json'
    # File tools cannot inspect host authentication/session state. Landlock backs up source write rules.
    save(settings, {'permissions': {'deny': ['WebSearch', 'WebFetch', 'Bash', 'Read(' + str(home) + '/**)', 'Write(' + str(home) + '/**)', 'Edit'],
                                     'allow': ['Read(' + str(work) + '/**)', 'Write(' + str(work / 'review_out') + '/**)']},
                    'disableAllHooks': True})
    env = {'HOME': str(home), 'CODEX_HOME': str(home / '.codex'), 'TMPDIR': str(home / 'tmp'),
           'LANG': 'C.UTF-8', 'TERM': 'dumb', 'DISABLE_AUTOUPDATER': '1',
           'PATH': str(Path(cli).parent) + ':/usr/bin:/bin'}
    (home / 'tmp').mkdir()
    read_paths = cal_sandbox.runtime_paths(cli) + [str(work), str(home)]
    writes = [str(work / 'review_out'), str(home)]
    start = time.monotonic()
    reason = None
    with raw.open('xb') as stdout, err.open('xb') as stderr:
        process = subprocess.Popen(argv_for(cell, cli, work, prompt, settings, model), cwd=work, env=env,
                                   stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, start_new_session=True,
                                   preexec_fn=lambda: cal_sandbox.restrict(read_paths, writes))
        process.stdin.write(prompt.encode() if cell == 'codex' or model == 'claude-fable-5-2' else b'')
        process.stdin.close()
        live_totals = [0]
        try:
            while process.poll() is None:
                u = get_usage(cell, raw, home, work)
                if not u.get('result_seen'):
                    live_totals.append(u['tokens_total'])
                if time.monotonic() - start > timeout:
                    reason = 'timeout'
                if u['tokens_total'] + reserve >= token_allowance:
                    reason = 'token_stop'
                if cell == 'claude' and u['api_key_source'] not in (None, 'none'):
                    reason = 'billing_mismatch'
                if reason:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                    break
                time.sleep(0.25)
        finally:
            # Kill descendants even if the root exited normally. Unfinished children invalidate coverage.
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            if process.poll() is None:
                process.wait()
    u = get_usage(cell, raw, home, work)
    if u['tokens_total'] >= token_allowance:
        u['late_reported_allowance_exceeded'] = True
    u.update(exit=process.returncode, seconds=round(time.monotonic() - start, 3), stop_reason=reason)
    u['live_observed_totals'] = live_totals
    u['preflight_live_final_gap'] = max(max(0, u['tokens_total'] - n) for n in live_totals)
    if raw.read_bytes() and not raw.read_bytes().endswith(b'\n'):
        u['metering_complete'] = False
    return u


def gate_check(a, packet_sha, binding, cli):
    g = load(a.gate)
    require(g.get('schema_version') == 1 and g.get('packet_sha256') == packet_sha and
            g.get('freeze_sha256') == binding and hexsha(g.get('key_sha256')), 'gate binding differs')
    for k in ('key_frozen', 'eligibility_checked', 'isolation_preflight_passed', 'live_meter_preflight_passed'):
        require(g.get(k) is True, 'offline gate incomplete: ' + k)
    require(type(g.get('adjudicable_primary_count')) is int and g['adjudicable_primary_count'] >= 3, 'key has fewer than 3 eligible primaries')
    c = g['cells'][a.cell]
    require(c['cli_sha256'] == sha(Path(cli).read_bytes()) and c['version'] == CELLS[a.cell][1], 'CLI gate differs')
    gap, allowance = c.get('preflight_live_final_gap'), c.get('inflight_allowance')
    require(type(gap) is int and gap >= 0 and type(allowance) is int and
            allowance == max(DEFAULT_INFLIGHT, 4 * gap), 'invalid measured engineering allowance')
    verify_preflights(Path(a.out), g)
    return g


def unsettled_intents(out, records, binding=None, kinds=('attempts', 'preflights', 'graders')):
    """The same intent/settlement audit for launch, scoring and ledger reporting."""
    out = Path(out)
    pending = []
    for kind in kinds:
        field = 'id' if kind == 'graders' else 'attempt_id'
        settled = {r[field] for r in records if field in r}
        pattern = '*/*/intent.json' if kind == 'attempts' else '*/intent.json'
        for path in sorted((out / kind).glob(pattern)):
            intent = load(path)
            if binding is not None and 'freeze_sha256' in intent:
                require(intent['freeze_sha256'] == binding, 'interrupted request uses another freeze')
            ident = intent.get('attempt_id', intent.get('id'))
            require(isinstance(ident, str) and ident, 'intent identity missing')
            if ident in settled:
                continue
            provider = intent.get('cell', intent.get('provider'))
            if provider is None:
                provider = 'claude' if 'claude' in ident or str(intent.get('model', '')).startswith('claude') else 'codex'
            require(provider in CELLS, 'intent provider missing')
            parent = path.parent
            usage = get_usage(provider, parent / 'events.jsonl', parent / 'home', parent / 'workspace')
            pending.append({'attempt_id': ident, 'cell': provider, 'arm': intent.get('arm'),
                'stage': intent.get('stage', 'native' if kind == 'attempts' else 'preflight'),
                'status': 'unsettled', 'tokens_total': usage['tokens_total'],
                'tokens_noncache': usage['tokens_noncache'], 'seconds': None,
                'metering_complete': False, 'isolation_complete': False})
    return pending


def preflight_rows(out, strict=True):
    records = rows(Path(out) / 'preflight-rows.jsonl')
    ids = set()
    for r in records:
        require(r.get('schema_version') == 1 and r.get('cell') in CELLS and
                r.get('attempt_id') == 'preflight-' + r['cell'] + '.a1' and
                r.get('attempt_id') not in ids and type(r.get('tokens_total')) is int and
                type(r.get('tokens_noncache')) is int and 0 <= r['tokens_noncache'] <= r['tokens_total'] and
                type(r.get('metering_complete')) is bool, 'invalid preflight accounting')
        ids.add(r['attempt_id'])
    if strict:
        require(not unsettled_intents(out, records, kinds=('preflights',)),
                'unsettled preflight charge; recover evidence before continuing')
    return records


def spending(out, binding, spent, experiment_spent):
    from cal_ledger import shared_costs
    require(0 <= spent <= experiment_spent, 'invalid outside-root spending')
    attempts = read_state(out, binding)
    probes = preflight_rows(out)
    shared = shared_costs(out / 'shared-costs.jsonl', binding,
                          [r['attempt_id'] for r in attempts + probes])
    require(all(r['metering_complete'] for r in attempts + probes) and
            all(r['metering_complete'] and r['subagents_included'] for r in shared),
            'incomplete usage blocks launch')
    require(not unsettled_intents(out, shared, binding, kinds=('graders',)), 'unsettled grader charge')
    observed = sum(r['tokens_total'] for r in attempts + probes if r['cell'] == 'claude')
    observed += sum(r['logical_tokens'] for r in shared if r['provider'] == 'claude')
    return spent + observed, experiment_spent + observed


def grading_reserve(out, remaining_requests=None, index=None, current_id=None, family=None):
    """Design slots, priced from all observed Claude-family grader requests."""
    out = Path(out)
    observed = [r for r in rows(out / 'shared-costs.jsonl') if r.get('provider') == 'claude'
                and r.get('stage') in ('grading', 'reconciliation') and not r.get('dry_run')]
    largest = max((r['logical_tokens'] for r in observed), default=0)
    allowance = max(150_000, (13 * largest + 9) // 10)
    if remaining_requests is None:
        if index is not None:
            prefix = 'grader-claude-' + sha(canonical(index))[:12] + '.a1'
            planned = {prefix + '-' + r['report_id'] for r in index['reports']} | {prefix + '-reconciliation'}
            settled = {r['id'] for r in observed}
            if family == 'claude':
                settled.add(current_id)
            # Batch 1 must retain all five conditional batch-2 slots.
            remaining_requests = len(planned - settled) + (5 if len(index['reports']) == 3 else 0)
        else:
            # Before batch 1: three reports + reconciliation, then five N2 slots.
            remaining_requests = 9
            for batch in (1, 2):
                path = out / ('blind' + str(batch)) / 'index.json'
                if path.exists():
                    remaining_requests = grading_reserve(out, index=load(path)) // allowance
            decision = out / 'decision-batch1.json'
            if decision.exists():
                d = load(decision)
                if d.get('reconciliation_complete') and not (out / 'blind2/index.json').exists():
                    remaining_requests = 5
                if d['cells']['claude']['outcome'] == 'ceiling':
                    remaining_requests = 0
            status = out / 'claude-sequential.json'
            if status.exists() and load(status).get('funded') is False:
                remaining_requests = 0
    return remaining_requests * allowance


def cli_identity(cell, cli, home):
    v = subprocess.run([str(cli), '--version'], capture_output=True, text=True, timeout=15,
                       env={'HOME': str(home), 'PATH': str(Path(cli).parent) + ':/usr/bin:/bin',
                            'DISABLE_AUTOUPDATER': '1'}, cwd=home)
    require(v.returncode == 0 and re.search(r'(?<![\d.])' + re.escape(CELLS[cell][1]) + r'(?![\d.])', v.stdout),
            'unexpected CLI version; record deviation before changing frozen build')
    return v.stdout.strip()


def snapshot(work):
    return {str(p.relative_to(work)): ('symlink' if p.is_symlink() else
            sha(p.read_bytes()) if p.is_file() else 'directory') for p in work.rglob('*')}


def workspace_unchanged(work, before):
    after = snapshot(work)
    allowed = lambda n: n == 'review_out' or n.startswith('review_out/')
    return (all(after.get(n) == h for n, h in before.items() if not allowed(n)) and
            all(n in before or allowed(n) for n in after) and
            not any(p.is_symlink() for p in work.rglob('*')))


def web_check(raw, home):
    """Inspect host tool records, never the probe agent's report of its actions.

    Disabled web tools and the shell network sandbox are also checked by the
    probe. Unknown event/tool schemas fail closed rather than being inferred.
    """
    paths = [raw] + sorted((home / '.codex' / 'sessions').rglob('rollout-*.jsonl'))
    calls, results, commands, pending_shell = {}, {}, [], {}
    for path in paths:
        stream, invalid = events(path)
        if invalid:
            return 'could-not-determine'
        for e in stream:
            for b in (e.get('message') or {}).get('content', []):
                if b.get('type') == 'tool_use':
                    calls[b.get('id')] = b.get('name', '')
                if b.get('type') == 'tool_result':
                    results[b.get('tool_use_id')] = b.get('is_error') is True
            item = e.get('item') or {}
            if item.get('type') == 'web_search':
                if item.get('status') == 'completed':
                    return 'fail'
                if item.get('status') not in ('failed', 'in_progress'):
                    return 'could-not-determine'
            if item.get('type') == 'command_execution' and e.get('type') == 'item.completed':
                commands.append(item)
            p = e.get('payload') or {}
            if e.get('type') == 'response_item' and p.get('type') == 'function_call':
                name = p.get('name', '')
                ident = p.get('call_id')
                calls[ident] = name
                if name in ('exec_command', 'shell', 'shell_command'):
                    try:
                        args = json.loads(p.get('arguments', '{}'))
                        command = args.get('cmd', args.get('command', ''))
                        pending_shell[ident] = command if isinstance(command, str) else ' '.join(command)
                    except (ValueError, TypeError):
                        return 'could-not-determine'
            if e.get('type') == 'response_item' and p.get('type') == 'function_call_output':
                output = p.get('output', '')
                try:
                    parsed = json.loads(output) if isinstance(output, str) else output
                except ValueError:
                    parsed = {}
                code = parsed.get('exit_code') if isinstance(parsed, dict) else None
                if type(code) is not int:
                    match = re.search(r'(?:exited with code|exit_code["\s:]+)\s*(-?\d+)', str(output))
                    code = int(match[1]) if match else None
                ident = p.get('call_id')
                if ident in pending_shell:
                    commands.append({'command': pending_shell.pop(ident), 'exit_code': code})
                if ident in calls and re.search(r'web|fetch|browser|mcp', calls[ident], re.I):
                    # Arbitrary prose is not authoritative error metadata.
                    results[ident] = parsed.get('is_error') is True if isinstance(parsed, dict) else False
            if e.get('type') == 'response_item' and p.get('type') == 'web_search_call':
                if p.get('status') == 'completed':
                    return 'fail'
                if p.get('status') != 'failed':
                    return 'could-not-determine'
    if any(re.search(r'curl|wget|https?://|socket|urllib|requests|fetch\(', c, re.I) for c in pending_shell.values()):
        return 'could-not-determine'
    for ident, name in calls.items():
        if re.search(r'web|fetch|browser|mcp', name, re.I):
            if ident not in results:
                return 'could-not-determine'
            if not results[ident]:
                return 'fail'
    for item in commands:
        # A successful networking program is a failure. Ambiguous interpreter
        # networking is undetermined even if it exited unsuccessfully.
        command = item.get('command', '')
        if re.search(r'curl|wget|https?://|socket|urllib|requests|fetch\(', command, re.I):
            if item.get('exit_code') == 0:
                return 'fail'
            if type(item.get('exit_code')) is not int:
                return 'could-not-determine'
    return 'pass'


PROBE_SOURCE = 'def answer():\n    return 42\n'
PROBE_PROMPT = '''This is an isolation probe, not study content. Attempt each step even
when denied: list this workspace; read source.py; attempt to overwrite source.py
with "changed"; attempt to read the outside path {outside}; attempt a web request
to https://example.com/ (use the web tool or, if available, curl with a 5-second
timeout). Do not delegate. Write review_out/report.json as a JSON object listing
each attempt and whether it succeeded or was refused. Never copy outside file
contents into the report deliberately. Do not modify any other file.'''


def probe_checks(cell, work, home, parent, before, outside, usage, version):
    event_bytes = (parent / 'events.jsonl').read_bytes()
    for p in (home / '.codex' / 'sessions').rglob('rollout-*.jsonl'):
        event_bytes += p.read_bytes()
    secret = outside.read_bytes().strip()
    yes = lambda v: 'pass' if v else 'fail'
    stream, _ = events(parent / 'events.jsonl')
    # Machine records must show the requested file operations. Missing evidence
    # is undetermined even if the agent claims it tried them in its report.
    tool_text = []
    for e in stream:
        for b in (e.get('message') or {}).get('content', []):
            if b.get('type') == 'tool_use':
                tool_text.append(json.dumps(b))
        item = e.get('item') or {}
        if item.get('type') in ('command_execution', 'file_change'):
            tool_text.append(json.dumps(item))
    observed = lambda path, action: any(path in t and re.search(action, t, re.I) for t in tool_text)
    operation_checks = {
        'workspace_list_observed': any(re.search(r'\bls\b|glob|list|\bfind\b', t, re.I) for t in tool_text),
        'source_read_observed': observed('source.py', r'read|cat|sed|head|tail|grep'),
        'source_write_attempt_observed': observed('source.py', r'write|edit|file_change|>|tee|patch'),
        'outside_read_attempt_observed': observed(str(outside), r'read|cat|sed|head|tail|grep'),
        # Claude's fixed --tools list excludes web tools and Bash altogether.
        # A refusal due to unavailable tools cannot emit a real web call.
        'web_attempt_observed': cell == 'claude' or any(re.search(r'web|curl|wget|fetch|https?://', t, re.I) for t in tool_text)}
    try:
        report_valid = isinstance(load(work / 'review_out' / 'report.json'), dict)
    except (ValueError, OSError):
        report_valid = False
    return {
        **{k: 'pass' if v else 'could-not-determine' for k, v in operation_checks.items()},
        'source_unchanged': yes((work / 'source.py').read_text() == PROBE_SOURCE),
        'writes_confined': yes(workspace_unchanged(work, before)),
        'outside_content_absent': yes(secret not in event_bytes and
                                      json.dumps(secret.decode())[1:-1].encode() not in event_bytes),
        'no_web_tool_succeeded': web_check(parent / 'events.jsonl', home),
        'subscription': yes(usage.get('billing_source') == ('subscription_oauth' if cell == 'claude' else 'subscription_chatgpt')
                            and (cell != 'claude' or usage.get('api_key_source') == 'none')),
        'model': yes(usage.get('model') == CELLS[cell][0] if cell == 'claude' else
                     usage.get('models_seen') == [CELLS[cell][0]]),
        'cli_version': yes(CELLS[cell][1] in version and
                           (cell != 'claude' or usage.get('cli_version') == CELLS[cell][1])),
        'complete_usage_root_and_children': yes(usage.get('metering_complete') is True),
        'live_meter': yes(len(usage.get('live_observed_totals', [])) > 1 and
                          any(n > 0 for n in usage.get('live_observed_totals', []))),
        'completed': yes(usage.get('exit') == 0 and usage.get('result_seen') and
                         not usage.get('stop_reason') and not usage.get('is_error') and
                         0 < usage.get('tokens_total', 0) < PREFLIGHT_CAP and
                         report_valid)}


ISOLATION_CHECKS = ('source_unchanged', 'writes_confined', 'outside_content_absent',
                    'outside_unchanged', 'workspace_list_observed', 'source_read_observed',
                    'source_write_attempt_observed', 'outside_read_attempt_observed',
                    'web_attempt_observed', 'no_web_tool_succeeded', 'landlock')
METER_CHECKS = ('subscription', 'model', 'cli_version', 'complete_usage_root_and_children', 'live_meter', 'completed')


def verify_preflights(out, gate):
    records = preflight_rows(out)
    for cell in CELLS:
        path = out / ('preflight-' + cell + '.json')
        require(path.is_file(), 'missing preflight evidence')
        proof = load(path)
        require(sha(path.read_bytes()) == gate['cells'][cell]['preflight_sha256'] and
                proof.get('runner_sha256') == code_digest() and not proof.get('dry_run') and
                proof.get('cli_sha256') == gate['cells'][cell]['cli_sha256'] and
                proof.get('version') == CELLS[cell][1] and proof.get('cell') == cell and
                proof.get('preflight_live_final_gap') == gate['cells'][cell]['preflight_live_final_gap'] and
                all(proof['checks'].get(k) == 'pass' for k in ISOLATION_CHECKS + METER_CHECKS),
                'preflight failed, undetermined, stale, or changed')
        require(sum(r == proof['usage'] for r in records) == 1, 'preflight usage not accounted exactly once')
        parent = out / 'preflights' / proof['usage']['attempt_id']
        require(evidence_digest(parent) == proof['evidence_sha256'], 'preflight raw evidence changed')


def evidence_digest(parent):
    paths = [parent / 'events.jsonl', parent / 'stderr.txt']
    paths += sorted((parent / 'home' / '.codex' / 'sessions').rglob('rollout-*.jsonl'))
    return sha(canonical({str(p.relative_to(parent)): sha(p.read_bytes()) if p.exists() else None for p in paths}))


def preflight(a):
    no_api_keys(os.environ)
    out = check_out(a.out, a.dry_run)
    require(a.outside_probe and a.outside_probe.is_file() and not a.outside_probe.is_symlink(), 'outside probe file required')
    outside = a.outside_probe.resolve()
    require(len(outside.read_bytes().strip()) >= 24, 'use a harmless unique UTF-8 outside canary of at least 24 bytes')
    outside.read_text(encoding='utf-8')
    with (out / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        records = preflight_rows(out)
        require(not any(r['cell'] == a.cell for r in records), 'preflight already recorded; no automatic rerun')
        require(not (out / ('preflight-' + a.cell + '.json')).exists(), 'preflight exists')
        stage, experiment = spending(out, frozen(), a.spent, a.experiment_spent)
        a.reserve = grading_reserve(out)
        claude_probe_reserve = PREFLIGHT_CAP if a.cell == 'claude' else 0
        require(stage + claude_probe_reserve + a.reserve <= STAGE_CAP and
                experiment + claude_probe_reserve + a.reserve <= EXPERIMENT_CAP, 'preflight budget guard')
        parent = out / 'preflights' / ('preflight-' + a.cell + '.a1')
        work, home = parent / 'workspace', parent / 'home'
        (work / 'review_out').mkdir(parents=True, mode=0o700)
        home.mkdir(mode=0o700)
        (work / 'source.py').write_text(PROBE_SOURCE)
        (work / 'README.txt').write_text('Harmless built-in isolation probe.\n')
        (work / 'small.json').write_text('{"probe": true}\n')
        before, outside_hash = snapshot(work), sha(outside.read_bytes())
        prompt = PROBE_PROMPT.format(outside=json.dumps(str(outside)))
        row = {'schema_version': 1, 'attempt_id': parent.name, 'cell': a.cell, 'dry_run': a.dry_run,
               'runner_sha256': code_digest(), 'tokens_total': 0, 'tokens_noncache': 0,
               'metering_complete': False, 'seconds': 0, 'subagents_included': False}
        checks = {k: 'could-not-determine' for k in ISOLATION_CHECKS + METER_CHECKS}
        cli = str(a.cli.resolve()) if a.cli else a.cell
        version = 'not executed'
        cli_hash = None
        if a.dry_run:
            save(parent / 'command.json', {'argv': argv_for(a.cell, cli, work, prompt, home / 'settings.json'), 'calls_model': False})
            (parent / 'events.jsonl').write_bytes(b'')
            (parent / 'stderr.txt').write_bytes(b'')
            row.update(metering_complete=True, preflight_live_final_gap=0)
        else:
            require(a.cli and a.auth_file, 'preflight needs CLI and subscription auth file')
            allowed = cal_sandbox.runtime_paths(cli) + [str(work), str(home)]
            require(not any(outside.is_relative_to(Path(p).resolve()) for p in allowed), 'outside probe lies in read allowlist')
            cal_sandbox.abi()
            billing = auth_home(a.cell, a.auth_file, home)
            version = cli_identity(a.cell, cli, home)
            cli_hash = sha(Path(cli).read_bytes())
            save(parent / 'intent.json', row)
            try:
                # No 1M engineering allowance is yet measured. Probe has its own
                # 0.5M observed stop; late counters remain possible and recorded.
                row.update(execute(a.cell, cli, work, home, parent, prompt, 3600, PREFLIGHT_CAP, 0))
                row['billing_source'] = billing
                checks.update(probe_checks(a.cell, work, home, parent, before, outside, row, version))
                checks['landlock'] = 'pass'  # restrict() runs before exec; no fallback
                checks['outside_unchanged'] = 'pass' if sha(outside.read_bytes()) == outside_hash else 'fail'
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                row.update(metering_complete=False, error_type=type(exc).__name__)
            row['subagents_included'] = row['metering_complete']
        if a.cell == 'claude' and stage + row['tokens_total'] > STAGE_CAP:
            row['deviations'] = ['late_reported_stage_threshold_exceeded; stop further launches']
        proof = {'schema_version': 1, 'cell': a.cell, 'dry_run': a.dry_run,
                 'runner_sha256': code_digest(), 'cli_sha256': cli_hash, 'version': CELLS[a.cell][1],
                 'version_output': version, 'checks': checks, 'usage': row,
                 'preflight_live_final_gap': row.get('preflight_live_final_gap'),
                 'evidence_sha256': evidence_digest(parent)}
        append(out / 'preflight-rows.jsonl', row)
        save(out / ('preflight-' + a.cell + '.json'), proof)
        passed = all(v == 'pass' for v in checks.values()) and not a.dry_run
        print(a.cell + ' preflight: ' + ('passed' if passed else 'gate closed') + '; logical=' + str(row['tokens_total']))
        return 0 if passed or a.dry_run else 5


def assemble_gate(a):
    out = check_out(a.out, False)
    require(a.gate.resolve().is_relative_to(out), 'gate must remain under private state root')
    binding = frozen()
    require(a.freeze_sha256 == binding and hexsha(a.key_sha256) and a.eligible_primary_count >= 3,
            'lead freeze/key/eligibility attestation incomplete')
    with (out / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        require(not a.gate.exists(), 'gate already assembled; preserve frozen evidence')
        g = {'schema_version': 1, 'packet_sha256': load(HERE / 'packet_manifest.json')['tree_sha256'],
             'freeze_sha256': binding, 'key_sha256': a.key_sha256, 'key_frozen': True,
             'eligibility_checked': True, 'adjudicable_primary_count': a.eligible_primary_count,
             'isolation_preflight_passed': True, 'live_meter_preflight_passed': True, 'cells': {}}
        for cell, cli in (('claude', a.claude_cli), ('codex', a.codex_cli)):
            path = out / ('preflight-' + cell + '.json')
            require(path.is_file(), 'missing preflight evidence')
            proof = load(path)
            gap = proof.get('preflight_live_final_gap')
            require(type(gap) is int and gap >= 0, 'missing measured live/final gap')
            g['cells'][cell] = {'version': CELLS[cell][1], 'cli_sha256': sha(cli.resolve().read_bytes()),
                                'preflight_sha256': sha(path.read_bytes()), 'preflight_live_final_gap': gap,
                                'inflight_allowance': max(DEFAULT_INFLIGHT, 4 * gap)}
        verify_preflights(out, g)
        save(a.gate, g)
        print('Private gate assembled from measured preflights and lead freeze/eligibility attestation.')
    return 0


def read_state(out, binding, strict=True):
    attempts = []
    for cell in CELLS:
        for row in rows(out / ('rows-' + cell + '.jsonl')):
            require(row.get('freeze_sha256') == binding, 'mixed frozen versions')
            attempts.append(row)
    # Started intent without a row means an unknown charge, not an opportunity to redraw.
    if strict:
        require(not unsettled_intents(out, attempts, binding, kinds=('attempts',)),
                'unsettled attempt: recover raw usage and append audited row before resuming')
    return attempts


def usable(row):
    return row.get('status') == 'completed' and row.get('metering_complete') and row.get('isolation_complete')


def check_out(path, dry):
    path = Path(path).resolve()
    if dry:
        require(path.is_relative_to(HERE), 'dry-run output must stay in this working directory')
    else:
        # No account name is embedded in the public runner.
        local = Path(os.environ.get('EGMCAL_LOCAL_ROOT', str(Path.home() / 'oaw-egmcal'))).resolve()
        require(local.name == 'oaw-egmcal' and local.is_relative_to(Path('/home')) and
                path.is_relative_to(local) and not str(path).startswith('/mnt/'), 'real output must be under local HOME/oaw-egmcal')
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


def sequential_n2(a, out, attempts, binding):
    """No key read. Consume the audited batch-1 score and apply the pre-data rule."""
    decision_path = out / 'decision-batch1.json'
    d = load(decision_path)
    require(d.get('freeze_sha256') == binding and d.get('batch') == 1 and
            d.get('accounting_complete') is True and d.get('reconciliation_complete') is True,
            'N2 requires audited reconciled batch-1 score')
    baseline = [r for r in attempts if r['arm'] in ('N1', 'N2') and (r['cell'], r['arm']) != ('claude', 'N2')]
    require(d.get('input_attempts') == baseline,
            'batch-1 score is stale or from different attempts')
    require(all(Path(p).is_file() and sha(Path(p).read_bytes()) == h for p, h in d.get('input_sha256', {}).items())
            and len(d.get('input_sha256', {})) >= 5, 'batch-1 scoring inputs changed')
    status_path = out / 'claude-sequential.json'
    if status_path.exists():
        prior_status = load(status_path)
        require(prior_status.get('freeze_sha256') == binding and prior_status.get('decision_sha256') ==
                sha(decision_path.read_bytes()), 'prior sequential decision differs')
        if prior_status.get('funded') is False:
            print('Claude sequential funding stop already recorded; no later launch.')
            return False
    outcome = d['cells']['claude']
    require(not outcome['rule'].startswith('NC1'), 'incomplete N1 cannot authorize N2')
    if outcome['outcome'] == 'ceiling':
        print('Claude N1 reached ceiling; N2 is not run.')
        return False
    n1 = [r for r in attempts if r['cell'] == 'claude' and r['arm'] == 'N1' and usable(r)]
    require(len(n1) == 1, 'N2 needs one measured completed Claude N1')
    spent, experiment = spending(out, binding, a.spent, a.experiment_spent)
    projected = (13 * n1[0]['tokens_total'] + 9) // 10
    reserve = grading_reserve(out, remaining_requests=5)
    funded = spent + projected + reserve <= a.budget and experiment + projected + reserve <= EXPERIMENT_CAP
    status = {'schema_version': 1, 'freeze_sha256': binding,
              'decision_sha256': sha(decision_path.read_bytes()), 'stage_spent': spent,
              'n1_actual': n1[0]['tokens_total'], 'n2_projection': projected,
              'remaining_claude_grading_reserve': reserve, 'threshold': a.budget,
              'funded': funded, 'rule': 'funded' if funded else
                  'NC1_N2_retry_not_funded' if any((r['cell'], r['arm']) == ('claude', 'N2') for r in attempts) else 'NC5_N2_not_funded'}
    append(out / 'claude-sequential.jsonl', status)
    save(status_path, status)
    if not funded:
        print('Claude: no conclusion [' + status['rule'] + ']; lead reports measured unit cost to repository owner.')
    return funded


def run(a):
    no_api_keys(os.environ)
    require(a.cell and a.packet, 'native requires cell and packet')
    require(a.command != 'merge', 'merge retained for a possible later EGM stage; disabled in this stage')
    require(a.cell != 'claude' or a.only != 'all', 'Claude is sequential: specify --only N1 or N2')
    require(0 < a.budget <= STAGE_CAP and a.spent >= 0 and a.experiment_spent >= a.spent
            and a.inflight_reserve > 0 and a.timeout == 3600, 'invalid budget/spent/reserve/timeout')
    binding = frozen()
    manifest = load(a.manifest)
    require(manifest == load(HERE / 'packet_manifest.json'), 'alternate packet manifest forbidden')
    packet_sha = build_packet.verify(a.packet, manifest)
    out = check_out(a.out, a.dry_run)
    # One lock covers both cells and shared Claude accounting. No race between native and merge.
    with (out / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        attempts = read_state(out, binding)
        if not a.dry_run:
            require(a.gate and a.cli and a.auth_file, 'real runs need --gate, --cli and --auth-file')
            cli = str(Path(a.cli).resolve())
            g = gate_check(a, packet_sha, binding, cli)
            a.inflight_reserve = g['cells'][a.cell]['inflight_allowance']
            require(not any(not r.get('metering_complete') for r in attempts), 'unknown prior spending blocks new model calls')
            cal_sandbox.abi()
        else:
            cli, g = str(a.cli or ('claude' if a.cell == 'claude' else 'codex')), {}
        chosen = ['M'] if a.command == 'merge' else (['N1', 'N2'] if a.only == 'all' else [a.only])
        for arm in chosen:
            attempts = read_state(out, binding)
            from cal_ledger import shared_costs
            shared = shared_costs(out / 'shared-costs.jsonl', binding, [r['attempt_id'] for r in attempts])
            require(all(r['metering_complete'] and r['subagents_included'] for r in shared), 'unknown shared spending blocks launch')
            prior = [r for r in attempts if r['cell'] == a.cell and r['arm'] == arm]
            terminal = [r for r in prior if not r.get('retryable')]
            if terminal:
                print(a.cell + ' ' + arm + ': recorded; no redraw')
                continue
            require(len(prior) < 2, 'one infrastructure retry already used')
            if prior:
                require(prior[-1]['retryable'] and prior[-1]['metering_complete'], 'attempt cannot be retried')
            if a.cell == 'claude' and arm == 'N1':
                require(all(any(r['cell'] == 'codex' and r['arm'] == n and usable(r) for r in attempts)
                            for n in ('N1', 'N2')), 'Codex N1 and N2 must finish first')
            if arm == 'N2':
                require(any(r['cell'] == a.cell and r['arm'] == 'N1' and usable(r) for r in attempts),
                        'N2 requires completed N1')
            if a.cell == 'claude' and arm == 'N2' and not a.dry_run:
                if not sequential_n2(a, out, attempts, binding):
                    return 0
            reports, source_rows = [], []
            if arm == 'M':
                for n in ('N1', 'N2'):
                    found = [r for r in attempts if r['cell'] == a.cell and r['arm'] == n and usable(r)]
                    require(len(found) == 1, 'merge needs both completed native reports')
                    r = found[0]
                    path = out / r['report_path']
                    require(sha(path.read_bytes()) == r['report_sha256'], 'native report changed')
                    reports.append(load(path))
                    source_rows.append(r)
            probes = preflight_rows(out)
            require(all(r['metering_complete'] for r in probes), 'unknown preflight spending blocks launch')
            spent, experiment = spending(out, binding, a.spent, a.experiment_spent)
            a.reserve = grading_reserve(out, remaining_requests=5) if a.cell == 'claude' and arm == 'N2' else grading_reserve(out)
            remaining = min(a.budget - spent - a.reserve, EXPERIMENT_CAP - experiment - a.reserve)
            require(spent < a.budget and experiment < EXPERIMENT_CAP, 'stage/experiment budget exhausted')
            if a.cell == 'claude' and arm != 'N2':
                require(remaining >= N_CAP, 'budget guard: reserve the first native ceiling without a unit-cost proxy')
            token_allowance = min(N_CAP if arm != 'M' else STAGE_CAP, remaining) if a.cell == 'claude' else N_CAP if arm != 'M' else 2**63 - 1
            ident = f'{a.cell}-{arm}.a{len(prior) + 1}'
            parent = out / 'attempts' / f'{a.cell}-{arm}' / ident
            parent.mkdir(parents=True, exist_ok=False, mode=0o700)
            work, home = parent / 'workspace', parent / 'home'
            home.mkdir(mode=0o700)
            if arm == 'M':
                (work / 'inputs').mkdir(parents=True)
                for label, report in zip(('A', 'B'), reports):
                    save(work / 'inputs' / (label + '.json'), report)
            else:
                build_packet.copy_packet(a.packet, work, manifest)
            (work / 'review_out').mkdir()
            input_files = {str(p.relative_to(work)): sha(p.read_bytes()) for p in work.rglob('*') if p.is_file()}
            prompt = (HERE / 'prompts' / ('merge.txt' if arm == 'M' else 'native.txt')).read_text()
            row = {'schema_version': 1, 'attempt_id': ident, 'cell': a.cell, 'arm': arm, 'attempt': len(prior) + 1,
                   'freeze_sha256': binding, 'packet_sha256': packet_sha, 'prompt_sha256': sha(prompt.encode()),
                   'runner_sha256': code_digest(), 'model': CELLS[a.cell][0], 'effort': 'high',
                   'cli_version_expected': CELLS[a.cell][1], 'dry_run': a.dry_run,
                   'input_report_sha256': [r['report_sha256'] for r in source_rows],
                   'key_sha256': g.get('key_sha256'), 'gate_sha256': sha(canonical(g)) if g else None,
                   'budget': a.budget, 'external_stage_spent': a.spent, 'external_experiment_spent': a.experiment_spent,
                   'outstanding_shared_reserve': a.reserve, 'inflight_allowance': a.inflight_reserve, 'timeout': a.timeout}
            if a.dry_run:
                # Preparation is real. Artifacts below are explicitly synthetic, never a review or grade.
                save(parent / 'command.json', {'argv': argv_for(a.cell, cli, work, prompt, home / 'settings.json'),
                                             'calls_model': False})
                save(work / 'review_out' / 'report.json', {'completed': True, 'findings': [], 'uncertainties': []})
                if arm == 'M':
                    save(work / 'review_out' / 'mapping.json', {'schema_version': 1, 'mapping': [], 'contradictions': []})
                (parent / 'events.jsonl').write_bytes(b'')
                row.update(tokens_total=0, tokens_noncache=0, seconds=0, metering_complete=True,
                           api_key_source='dry-run', billing_source='dry-run', cli_version='not executed', result_seen=True)
            else:
                require(not any(r.get('dry_run') for r in attempts), 'cannot mix dry and real runs')
                billing = auth_home(a.cell, a.auth_file, home)
                version = cli_identity(a.cell, cli, home)
                save(parent / 'intent.json', {**row, 'started_at_epoch': time.time(), 'gate_sha256': sha(canonical(g))})
                try:
                    row.update(execute(a.cell, cli, work, home, parent, prompt, a.timeout, token_allowance, a.inflight_reserve))
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    # Never turn a launch/parse exception into a free redraw.
                    row.update(get_usage(a.cell, parent / 'events.jsonl', home, work))
                    row.update(seconds=None, metering_complete=False,
                               stop_reason='infrastructure_exception', error_type=type(exc).__name__)
                row['billing_source'] = billing
                row['cli_version'] = version
                if a.cell == 'codex':
                    row['api_key_source'] = 'none (validated ChatGPT OAuth auth_mode)'
            if a.cell == 'claude' and spent + row['tokens_total'] > a.budget:
                row['deviations'] = ['late_reported_stage_threshold_exceeded; stop further launches']
            if a.cell == 'claude' and experiment + row['tokens_total'] > EXPERIMENT_CAP:
                row['stop_reason'] = 'experiment_cap_exceeded'
            if arm != 'M' and row['tokens_total'] >= N_CAP:
                row['stop_reason'] = 'native_ceiling_reached'
            source_changed = any(not (work / name).is_file() or (work / name).is_symlink() or
                                 sha((work / name).read_bytes()) != digest for name, digest in input_files.items())
            extras = [p for p in work.rglob('*') if p.is_file() and str(p.relative_to(work)) not in input_files
                      and not p.relative_to(work).parts[0] == 'review_out']
            row['isolation_complete'] = not source_changed and not extras and not any(p.is_symlink() for p in work.rglob('*'))
            row['sources_changed'] = source_changed
            report_path = work / 'review_out' / 'report.json'
            try:
                report = validate_report(load(report_path))
                if arm == 'M':
                    validate_mapping(load(work / 'review_out' / 'mapping.json'), reports, report)
                    row['mapping_path'] = str((work / 'review_out' / 'mapping.json').relative_to(out))
                    row['mapping_sha256'] = sha((work / 'review_out' / 'mapping.json').read_bytes())
                row.update(report_path=str(report_path.relative_to(out)), report_sha256=sha(report_path.read_bytes()),
                           report_completed=report['completed'])
            except (ValueError, OSError, KeyError, TypeError):
                row['report_completed'] = False
            ok = (row.get('result_seen') and row.get('tokens_total', 0) > 0 and not row.get('is_error') and row.get('exit', 0) == 0
                  and not row.get('limit_seen') and not row.get('stop_reason') and row['report_completed']
                  and row['isolation_complete'] and row['metering_complete'])
            if a.dry_run:
                ok = row['report_completed'] and row['isolation_complete']
            if a.cell == 'claude' and not a.dry_run:
                ok = ok and row.get('api_key_source') == 'none' and row.get('model') == CELLS[a.cell][0]
            if a.cell == 'codex' and not a.dry_run:
                ok = ok and row.get('models_seen') == [CELLS[a.cell][0]]
            # Only an explicit host infrastructure error before any report, with complete usage, may be retried.
            row['retryable'] = bool(not ok and len(prior) == 0 and row.get('infrastructure_failure') and
                                    row['metering_complete'] and not row.get('report_completed') and
                                    not row.get('limit_seen') and not row.get('stop_reason') and row['isolation_complete'])
            row['subagents_included'] = row['metering_complete']
            row['status'] = 'completed' if ok else 'failed'
            append(out / ('rows-' + a.cell + '.jsonl'), row)
            print(f"{ident}: {row['status']}; logical={row['tokens_total']}; noncache={row['tokens_noncache']}")
            if not ok:
                return 5
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('native', 'merge', 'preflight', 'gate'))
    p.add_argument('--cell', choices=tuple(CELLS))
    p.add_argument('--packet', type=Path)
    p.add_argument('--manifest', type=Path, default=HERE / 'packet_manifest.json')
    p.add_argument('--out', type=Path, required=True, help='same private root for both cells; use a separate root for dry run')
    p.add_argument('--only', choices=('all', 'N1', 'N2'), default='all')
    p.add_argument('--cli', type=Path)
    p.add_argument('--auth-file', type=Path)
    p.add_argument('--gate', type=Path)
    p.add_argument('--outside-probe', type=Path)
    p.add_argument('--key-sha256')
    p.add_argument('--freeze-sha256')
    p.add_argument('--eligible-primary-count', type=int)
    p.add_argument('--claude-cli', type=Path)
    p.add_argument('--codex-cli', type=Path)
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--budget', type=int, default=STAGE_CAP)
    p.add_argument('--spent', type=int, default=0, help='Claude stage costs outside this output root, including shared work')
    p.add_argument('--experiment-spent', type=int, default=0, help='Claude experiment costs outside this output root; >= spent')
    p.add_argument('--timeout', type=int, default=3600)
    a = p.parse_args(argv)
    a.inflight_reserve = DEFAULT_INFLIGHT
    if a.command == 'preflight':
        require(a.cell is not None, 'preflight requires cell')
        return preflight(a)
    if a.command == 'gate':
        require(a.gate and a.claude_cli and a.codex_cli and type(a.eligible_primary_count) is int,
                'gate requires CLI paths, count, key and freeze hashes')
        return assemble_gate(a)
    return run(a)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, TypeError):
        # Private paths/credentials/raw error strings stay out of console summaries.
        print('Refused: invalid/incomplete inputs, isolation, freeze, billing or budget gate.', file=sys.stderr)
        raise SystemExit(2)
