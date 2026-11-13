"""Regression tests driven by trimmed real preflight tool records. No CLIs."""
import json
import unittest
from pathlib import Path
from host_probe import web_check, native_calls
from host_policy import CODEX_EXTERNAL_FEATURES

HERE=Path(__file__).resolve().parents[1]
FIX=HERE/'fixtures/host-preflight'

def fixture(name):
    return [json.loads(s) for s in (FIX/name).read_text().splitlines()]

class RemoteEvidenceTests(unittest.TestCase):
    def test_real_hosted_web_success_closes_gate(self):
        ev=fixture('egmcal-3-web.jsonl')
        self.assertEqual(web_check('codex',ev,True),'fail')
        self.assertEqual(web_check('codex',ev,False),'fail')
        self.assertTrue(any(c['name']=='mcp.codex_apps.search_service.web_run' for c in native_calls('codex',ev)))

    def test_real_dns_failure_is_observed_and_passes(self):
        ev=fixture('u2-codex-2-attempts.jsonl')
        self.assertEqual(web_check('codex',ev,True),'pass')

    def test_absent_pending_and_failed_mcp(self):
        self.assertEqual(web_check('codex',[],True),'could-not-determine')
        ev=fixture('egmcal-3-web.jsonl')
        self.assertEqual(web_check('codex',ev[:1],True),'could-not-determine')
        ev[-1]['item'].update(status='failed',result=None,error={'message':'tool not available'})
        self.assertEqual(web_check('codex',ev,True),'pass')

    def test_remote_content_overrides_command_failure(self):
        ev=[{'type':'item.completed','item':{'type':'command_execution','id':'c',
             'command':'curl https://example.com/; false','exit_code':1,
             'aggregated_output':'<!doctype html><html>remote</html>'}}]
        self.assertEqual(web_check('codex',ev,True),'fail')

    def test_claude_success_failure_missing_and_string_errors(self):
        call={'type':'assistant','message':{'content':[{'type':'tool_use','id':'x',
             'name':'mcp__anything__browse','input':{'url':'https://example.com/'}}]}}
        for error,wanted in ((True,'pass'),(False,'fail')):
            out={'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'x','is_error':error,'content':'result'}]}}
            self.assertEqual(web_check('claude',[{'type':'error','message':'error string'},call,out],True),wanted)
        self.assertEqual(web_check('claude',[call],True),'could-not-determine')

    def test_remote_error_page_and_partial_json_are_leaks(self):
        for output in ('HTTP status: 404\n', '{"remote":"body"}'):
            ev=[{'type':'item.completed','item':{'type':'command_execution','id':'c',
                 'command':'curl https://example.com/','exit_code':23,'aggregated_output':output}}]
            self.assertEqual(web_check('codex',ev,True),'fail')

    def test_other_remote_tool_return_is_a_leak(self):
        ev=[{'type':'response_item','payload':{'type':'function_call','name':'weather.lookup','call_id':'x','arguments':'{}'}},
            {'type':'response_item','payload':{'type':'function_call_output','call_id':'x','output':'{"temperature":20}'}}]
        self.assertEqual(web_check('codex',ev,True),'fail')

    def test_remote_function_structured_error_is_not_success(self):
        ev=[{'type':'response_item','payload':{'type':'function_call','name':'mcp.anything','call_id':'x','arguments':'{}'}},
            {'type':'response_item','payload':{'type':'function_call_output','call_id':'x','output':'{"is_error":true,"content":"unavailable"}'}}]
        self.assertEqual(web_check('codex',ev,True),'pass')

import os
import tempfile
import subprocess
from unittest.mock import patch
import cal_run as R
import cal_launch as L

class LaunchTests(unittest.TestCase):
    def test_all_launch_kinds_disable_external_features_and_keep_shell(self):
        for model in (None,'gpt-6-astra'):
            a=R.argv_for('codex','/cli',Path('/w'),'prompt',Path('/s'),model)
            for feature in CODEX_EXTERNAL_FEATURES: self.assertIn('features.'+feature+'=false',a)
            self.assertIn('mcp_servers={}',a); self.assertIn('web_search="disabled"',a)
            self.assertIn('sandbox_workspace_write.network_access=false',a)
            self.assertNotIn('features.shell_tool=false',a)
        for model,tools in ((None,'Read,Write,Glob,Grep,Agent,Skill'),('claude-fable-5-2','')):
            a=R.argv_for('claude','/cli',Path('/w'),'prompt',Path('/s'),model)
            self.assertEqual(a[a.index('--tools')+1],tools)
            self.assertEqual(a[a.index('--setting-sources')+1],'')
            self.assertIn('--strict-mcp-config',a); self.assertIn('{"mcpServers":{}}',a)

    def test_claude_probe_can_observe_curl_without_changing_native_tools(self):
        a=R.argv_for('claude','/cli',Path('/w'),'prompt',Path('/s'),probe=True)
        self.assertEqual(a[a.index('--tools')+1],'Read,Write,Glob,Grep,Bash,Agent,Skill')
        native=R.argv_for('claude','/cli',Path('/w'),'prompt',Path('/s'))
        self.assertNotIn('Bash',native[native.index('--tools')+1])

    def test_runtime_must_be_explicit_and_confined(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); runtime=root/'runtime'; runtime.mkdir(); cli=runtime/'cli';cli.touch()
            with patch.dict(os.environ,{'EGMCAL_RUNTIME_ROOTS':''}):
                with self.assertRaisesRegex(ValueError,'runtime_allowlist'): L.runtime_root(cli)
            with patch.dict(os.environ,{'EGMCAL_RUNTIME_ROOTS':str(runtime)}):
                self.assertEqual(L.runtime_root(cli),runtime)
                (runtime/'escape').symlink_to('/etc/passwd')
                with self.assertRaisesRegex(ValueError,'symlink'): L.runtime_root(cli)

    def test_bubblewrap_source_output_and_nested_sandbox_without_a_cli(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); runtime=root/'runtime'; runtime.mkdir(); cli=runtime/'fake'; cli.touch()
            work=root/'workspace'; (work/'review_out').mkdir(parents=True)
            (work/'source.py').write_text('original')
            before=R.snapshot(work)
            home=root/'home'; home.mkdir(); outside=root/'outside'; outside.write_text('canary')
            program='''from pathlib import Path
import subprocess
try: Path(OUTSIDE).read_bytes()
except OSError: pass
else: raise SystemExit("outside exposed")
args=["bwrap","--ro-bind","/","/","--bind","/home/dev/proj","/home/dev/proj"]
for name in (".git",".agents",".codex",".aws"):
 args += ["--tmpfs","/home/dev/proj/"+name,"--remount-ro","/home/dev/proj/"+name]
subprocess.run(args+["--","/usr/bin/python3","-c",'from pathlib import Path; Path("source.py").write_text("bad"); Path("review_out/report.json").write_text("{}")'],check=True)
'''.replace('OUTSIDE',repr(str(outside)))
            cli.write_text('#!/usr/bin/python3\n'+program); cli.chmod(0o700)
            with patch.dict(os.environ,{'EGMCAL_RUNTIME_ROOTS':str(runtime)}):
                a=L.bubblewrap([str(cli)],str(cli),work,home)
                env={'HOME':L.HOME,'PATH':'/usr/bin:/bin'}
                done=subprocess.run(a,capture_output=True,text=True,env=env)
            self.assertEqual(done.returncode,0,done.stderr)
            self.assertEqual((work/'source.py').read_text(),'bad')
            integrity=R.workspace_integrity(work,before,allow_placeholders=True)
            self.assertFalse(integrity['isolation_complete'])
            self.assertEqual(integrity['source_changed_paths'],['source.py'])
            self.assertEqual({p['path'] for p in integrity['sandbox_placeholders']},R.SANDBOX_PLACEHOLDERS)
            self.assertEqual((work/'review_out/report.json').read_text(),'{}')
            self.assertEqual((home/L.MARKER).read_text(),'bwrap-v1')

    def test_version_uses_namespace_without_real_cli(self):
        with tempfile.TemporaryDirectory() as td:
            runtime=Path(td)/'runtime'; runtime.mkdir(); cli=runtime/'fake'
            cli.write_text('#!/usr/bin/python3\nimport os,sys\nassert sys.argv[1:]==["--version"]\nassert os.environ["HOME"]=="/home/dev"\nprint("synthetic-version")\n')
            cli.chmod(0o700)
            with patch.dict(os.environ,{'EGMCAL_RUNTIME_ROOTS':str(runtime)}):
                done=L.version_output(cli)
            self.assertEqual(done.returncode,0,done.stderr)
            self.assertEqual(done.stdout.strip(),'synthetic-version')

    def test_calibration_wrapper_rejects_real_hosted_web_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            home=Path(td); raw=home/'events.jsonl'
            raw.write_bytes((FIX/'egmcal-3-web.jsonl').read_bytes())
            self.assertEqual(R.web_check(raw,home),'fail')
            self.assertTrue(any('search_service.web_run' in s for s in R.tool_records(fixture('egmcal-3-web.jsonl'))))

    def test_probe_prompt_names_concrete_actions_and_diagnostic_reasons(self):
        self.assertIn('cat {outside}',R.PROBE_PROMPT)
        self.assertIn('curl -sS -m 5 https://example.com/',R.PROBE_PROMPT)
        self.assertIn('remote content',R.check_reason('no_web_tool_succeeded','fail',{}))
