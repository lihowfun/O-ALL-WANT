"""Offline host probe evidence parser. Vendored identically in both runners."""
import json
import re
import shlex
from pathlib import Path

TRUNCATION = re.compile(r'output truncated|truncated output|\[truncated\]', re.I)

def output_text(value):
    if isinstance(value, str):
        try:
            obj = json.loads(value)
            if isinstance(obj, dict) and any(k in obj for k in ('output','content','text')):
                return output_text(obj)
        except ValueError:
            pass
        # Codex exec_command textual framing.
        if '\nOutput:\n' in value:
            return value.split('\nOutput:\n', 1)[1]
        return value
    if isinstance(value, list):
        return '\n'.join(output_text(x.get('text', x.get('content', ''))) for x in value if isinstance(x, dict))
    if isinstance(value, dict):
        return output_text(value.get('output', value.get('content', value.get('text', ''))))
    return ''


def native_calls(host, native):
    """Return ordered completed or pending calls. Missing joins are retained, never treated as reads."""
    calls, outputs, exits, seq, leaves = {}, {}, {}, 0, {}
    for e in native:
        if host == 'claude':
            message = e.get('message') if isinstance(e.get('message'), dict) else {}
            for b in message.get('content', []) if isinstance(message.get('content'), list) else []:
                if not isinstance(b,dict):
                    continue
                if b.get('type') == 'tool_use':
                    seq += 1
                    calls[b['id']] = {'seq': seq, 'name': b.get('name', ''), 'input': b.get('input') or {}, 'id': b['id']}
                elif b.get('type') == 'tool_result':
                    outputs[b['tool_use_id']] = (output_text(b.get('content')), not b.get('is_error', False))
        else:
            p = e.get('payload') or {}
            typ = p.get('type')
            if e.get('type') == 'response_item' and typ in ('function_call', 'custom_tool_call', 'local_shell_call'):
                seq += 1
                args = p.get('arguments', p.get('input', p.get('action', {})))
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except ValueError:
                        args = {'opaque': args}
                cid = p.get('call_id', p.get('id', str(seq)))
                calls[cid] = {'seq': seq, 'name': p.get('name', 'shell'), 'input': args, 'id': cid}
            elif e.get('type') == 'response_item' and typ in ('function_call_output', 'custom_tool_call_output', 'local_shell_call_output'):
                out = p.get('output', '')
                s = output_text(out)
                code = re.search(r'Process exited with code (\d+)', str(out))
                json_code = re.search(r'"exit_code"\s*:\s*(-?\d+)', str(out))
                ok = not p.get('is_error', False) and (not code or code[1] == '0') and (not json_code or json_code[1]=='0')
                try:
                    data=json.loads(out) if isinstance(out,str) else out
                except ValueError:
                    data={}
                if isinstance(data,dict) and (data.get('is_error') or data.get('isError') or data.get('error')):
                    ok=False
                if re.search(r'unknown tool|tool (?:is )?not available|tool unavailable|tool not found',s,re.I):
                    ok=False
                outputs[p.get('call_id')] = (s, ok)
                exits[p.get('call_id')]=int((code or json_code)[1]) if code or json_code else None
                # exec is an orchestration envelope. Its status/output describes
                # the JS batch, not the shell subprocesses inside it. Use actual
                # item events between call and output; never parse/evaluate JS.
                wrapper=calls.get(p.get('call_id'),{})
                if wrapper.get('name','').split('.')[-1]=='exec':
                    wrapper['children']=[x['id'] for x in leaves.values() if x['seq']>wrapper['seq']]
            item = e.get('item', {}) if e.get('type','').startswith('item.') else p.get('item', {}) if e.get('type')=='event_msg' else p if e.get('type')=='response_item' and p.get('type') in ('mcp_tool_call','web_search','web_search_call') else {}
            if item.get('type') in ('command_execution','CommandExecution'):
                cid=item.get('id')
                if cid not in leaves:
                    seq += 1
                completed=e.get('type')=='item.completed' or p.get('type')=='item_completed'
                code=item.get('exit_code')
                leaves[cid]={'seq':leaves.get(cid,{}).get('seq',seq), 'name':'exec_command',
                             'input':{'cmd':shell_command(item.get('command',''))},
                             'id':cid,'output':item.get('aggregated_output','') if completed else '',
                             'ok':code==0 if completed and type(code) is int else None,
                             'exit_code':code if completed else None,'evidence':'command_execution'}
            elif item.get('type') in ('mcp_tool_call','McpToolCall','web_search','web_search_call'):
                cid=item.get('id')
                if cid not in leaves: seq+=1
                status=item.get('status')
                result=item.get('result')
                failed=bool(item.get('error') or status=='failed' or
                            isinstance(result,dict) and (result.get('isError') or result.get('is_error') or result.get('error')))
                leaves[cid]={'seq':leaves.get(cid,{}).get('seq',seq),
                             'name':'mcp.'+item.get('server','')+'.'+item.get('tool',item['type']),
                             'input':item.get('arguments') or {},'id':cid,
                             'output':output_text(result) or output_text(item.get('output')),
                             'ok':False if failed else True if status=='completed' else None,
                             'evidence':item['type']}
            elif item.get('type') in ('file_change','FileChange'):
                cid=item.get('id')
                if cid not in leaves: seq+=1
                changes=item.get('changes') or {}
                paths=list(changes) if isinstance(changes,dict) else [x.get('path') for x in changes]
                leaves[cid]={'seq':leaves.get(cid,{}).get('seq',seq),'name':'file_change',
                             'input':{'paths':paths},'id':cid,'output':'',
                             'ok':True if item.get('status')=='completed' else False if item.get('status')=='failed' else None,
                             'evidence':'file_change'}
    result = []
    for cid, c in calls.items():
        if c.get('children'):
            continue
        out, ok = outputs.get(cid, ('', None))
        if host=='codex' and c['name'].split('.')[-1] in ('exec_command','shell') and exits.get(cid) is None and ok is True:
            ok=None
        result.append({**c, 'output': out, 'ok': ok,'exit_code':exits.get(cid)})
    # Direct function calls may also have item events. Keep one observation for
    # the same command; unlike exec batches they already have their own result.
    direct=list(result); matched=set()
    for leaf in leaves.values():
        if leaf['name']=='file_change' or leaf.get('evidence') in ('mcp_tool_call','McpToolCall','web_search','web_search_call'):
            result.append(leaf)
            continue
        duplicates=[c for c in direct if c['id'] not in matched and c['seq']<=leaf['seq'] and
                    c['name'].split('.')[-1] in ('exec_command','shell') and isinstance(c['input'],dict) and
                    shell_command(c['input'].get('cmd',c['input'].get('command','')))==leaf['input']['cmd']]
        if not duplicates:
            result.append(leaf)
        else:
            c=duplicates[0]; matched.add(c['id'])
            if leaf['ok'] is not None:
                c.update(output=leaf['output'],ok=leaf['ok'],exit_code=leaf['exit_code'])
    return sorted(result, key=lambda c: c['seq'])


def shell_command(command):
    """Unwrap one literal shell -c/-lc argv (CLI string or rollout argv array).

    Quoting belongs to the wrapper, so do not reject a quoted inner sed/python
    command for metacharacters until after unwrapping. No shell code is run.
    """
    try:
        words=shlex.split(command) if isinstance(command,str) else command
    except ValueError:
        return command
    if (isinstance(words,list) and len(words)==3 and isinstance(words[0],str) and
        Path(words[0]).name in ('bash','sh','zsh') and words[1] in ('-c','-lc')):
        return words[2]
    return shlex.join(words) if isinstance(command,list) else command


REFUSED_BEFORE_RUN = re.compile(r"requires approval|can't be checked before it runs|haven't granted it yet|"
                                r"permission to use .* has been denied|was blocked before execution", re.I)


def web_evidence(cell, events):
    """Actual network results, never the success of an orchestration envelope."""
    observations=[]
    for e in events:
        p=e.get('payload') or {}; item=e.get('item') or {}
        for x in (p,item):
            if x.get('type') in ('web_search_call','web_search'):
                content=x.get('results') or x.get('sources') or x.get('output')
                result='succeeded' if x.get('status')=='completed' else 'failed' if x.get('status')=='failed' else 'unknown'
                observations.append({'call_id':x.get('id'),'result':result,'basis':'native web result'})
    calls = native_calls(cell,events) if cell != 'both' else native_calls('codex',events) + native_calls('claude',events)
    for c in calls:
        name=c['name']; inp=c['input'] if isinstance(c['input'],dict) else {}
        command=shell_command(inp.get('cmd',inp.get('command','')))
        native_web=bool(re.search(r'web|search|browse|fetch|mcp|remote|http|finance|weather|sports|lookup|download|open_url',name,re.I))
        try: words=shlex.split(command)
        except ValueError: words=[]
        shell_web=bool(words and Path(words[0]).name in ('curl','wget'))
        python_web=bool(words and Path(words[0]).name.startswith('python') and
                        re.search(r'urllib|requests|socket|https?://',command))
        opaque=bool(re.search(r'curl|wget|https?://|urllib|requests|fetch\(',str(inp.get('opaque',''))))
        if not (native_web or shell_web or python_web or opaque): continue
        if shell_web:
            lexer=shlex.shlex(command,posix=True,punctuation_chars=';&|<>')
            lexer.whitespace_split=True
            # Exit status of a shell branch/pipeline is not curl's status.
            opaque=opaque or any(w and all(ch in ';&|<>' for ch in w) for w in lexer)
        output=c['output']
        statuses=[int(x) for x in re.findall(r'(?:HTTP status:\s*|HTTP/\S+\s+)(\d{3})\b',output,re.I)]
        result='unknown'; basis='missing or opaque network result'
        # The host's permission layer refused the call before anything ran (seen with the real
        # Claude CLI: "This command requires approval", "... can't be checked before it runs").
        # Nothing reached the network, whatever the shape of the command line.
        if c['ok'] is False and REFUSED_BEFORE_RUN.search(output):
            result='failed'; basis='refused by the host before execution'
        elif re.search(r'<(?:!doctype|html|body)\b|Crawled:|Content type: text/html',output,re.I) or (shell_web and c['ok'] is False and output.lstrip().startswith(('{','['))):
            result='succeeded'; basis='returned remote content'
        elif not opaque:
            if any(100<=s<600 for s in statuses):
                result='succeeded'; basis='remote HTTP response, including error pages'
            elif statuses and c['ok'] is not None:
                result='failed'; basis='HTTP status 000: no response'
            elif shell_web and re.search(r'could not resolve|failed to connect|couldn.t connect|connection refused|network is unreachable|curl: \(\d+\)',output,re.I):
                result='failed' if c['ok'] is False else 'unknown'; basis='network error diagnostic'
            elif shell_web and re.search(r'<(?:!doctype|html|body)\b',output,re.I):
                result='succeeded'; basis='returned remote content before command failure'
            elif native_web and c['ok'] is True:
                result='succeeded'; basis='successful remote tool call'
            elif c['ok'] is False:
                result='failed'; basis='tool/command failed'
            elif c['ok'] is True and (native_web or shell_web) and not TRUNCATION.search(output):
                result='succeeded'; basis='tool returned remote content'
        observations.append({'call_id':c['id'],'command':command or None,'result':result,'basis':basis,
                             'exit_code':c.get('exit_code'),'http_statuses':statuses})
    return observations


def web_check(cell, events, valid):
    observations=web_evidence(cell,events)
    # Positive remote evidence is a failure even if another attempt is opaque.
    if any(x['result']=='succeeded' for x in observations): return 'fail'
    if not valid or not observations or any(x['result']=='unknown' for x in observations): return 'could-not-determine'
    return 'pass'


