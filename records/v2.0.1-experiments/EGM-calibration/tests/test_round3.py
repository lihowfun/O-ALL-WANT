"""Round-3 branch, blindness, funding and request tests; invented keys only."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from cal_common import append, canonical, load, save, sha
import cal_grade as G
import cal_requests as Q
import cal_run as R
from tests.test_calibration import ROOT, fixture, label
from tests import test_calibration as T


class SequentialTests(unittest.TestCase):
    def prepare(self, root, cost=4_000_000, outcome='no conclusion'):
        attempts = [{'attempt_id': 'claude-N1.a1', 'cell': 'claude', 'arm': 'N1', 'status': 'completed',
                     'metering_complete': True, 'isolation_complete': True, 'tokens_total': cost}]
        hashes = {}
        for i in range(5):
            p = root / f'input{i}.json'
            save(p, {'synthetic': i})
            hashes[str(p)] = sha(p.read_bytes())
        d = {'freeze_sha256': 'a'*64, 'batch': 1, 'accounting_complete': True, 'reconciliation_complete': True,
             'input_attempts': attempts, 'input_sha256': hashes,
             'cells': {'claude': {'outcome': outcome, 'rule': 'C1_test' if outcome == 'ceiling' else 'NC4_test'}}}
        save(root / 'decision-batch1.json', d)
        args = SimpleNamespace(spent=0, experiment_spent=0, budget=15_000_000, reserve=1_000_000)
        return args, attempts

    def test_exact_funding_boundary_and_nc5(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            root = Path(tmp)
            a, attempts = self.prepare(root)
            with patch.object(R, 'spending', return_value=(9_050_000, 9_050_000)):
                self.assertTrue(R.sequential_n2(a, root, attempts, 'a'*64))
            with patch.object(R, 'spending', return_value=(9_050_001, 9_050_001)):
                self.assertFalse(R.sequential_n2(a, root, attempts, 'a'*64))
            status = load(root / 'claude-sequential.json')
            self.assertEqual(status['rule'], 'NC5_N2_not_funded')
            self.assertEqual(status['n2_projection'], 5_200_000)
            self.assertFalse((root / 'attempts').exists())
            with patch.object(R, 'spending', side_effect=AssertionError('terminal funding stop')):
                self.assertFalse(R.sequential_n2(a, root, attempts, 'a'*64))

    def test_n2_infrastructure_retry_keeps_batch1_baseline(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            root = Path(tmp)
            a, attempts = self.prepare(root)
            attempts = attempts + [{'attempt_id': 'claude-N2.a1', 'cell': 'claude', 'arm': 'N2',
                                    'status': 'failed', 'retryable': True, 'tokens_total': 100}]
            with patch.object(R, 'spending', return_value=(8_000_000, 8_000_000)):
                self.assertTrue(R.sequential_n2(a, root, attempts, 'a'*64))

    def test_ceiling_skips_and_stale_or_missing_score_refuses(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            root = Path(tmp)
            a, attempts = self.prepare(root, outcome='ceiling')
            with patch.object(R, 'spending', side_effect=AssertionError('no N2 funding needed')):
                self.assertFalse(R.sequential_n2(a, root, attempts, 'a'*64))
            (root / 'input0.json').write_text('changed')
            with self.assertRaises(ValueError): R.sequential_n2(a, root, attempts, 'a'*64)
            (root / 'decision-batch1.json').unlink()
            with self.assertRaises(OSError): R.sequential_n2(a, root, attempts, 'a'*64)

    def test_run_order_and_default_limits(self):
        packet = ROOT.parent / 'egmcal-src/packet'
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp, patch.dict(R.os.environ, {}, clear=True):
            args = ['--packet', str(packet), '--out', tmp, '--dry-run']
            with self.assertRaises(ValueError): R.main(['native', '--cell', 'claude', '--only', 'N1'] + args)
            with self.assertRaises(ValueError): R.main(['native', '--cell', 'claude'] + args)
        self.assertEqual((R.STAGE_CAP, R.N_CAP, R.EXPERIMENT_CAP), (15_000_000, 8_000_000, 30_000_000))

    def test_table_one_claude_report_and_failed_launched_n2(self):
        primary = ['K01','K02','K03']
        labs = [{'N1': dict.fromkeys(primary, 'detected')} for _ in range(2)]
        self.assertEqual(G.decision(primary, labs, True, 'claude', False)['outcome'], 'ceiling')
        for g in labs: g['N1']['K01'] = 'absent'
        self.assertTrue(G.decision(primary, labs, True, 'claude', False)['rule'].startswith('NC4'))
        self.assertTrue(G.decision(primary, labs, True, 'claude', False, False)['rule'].startswith('NC5'))
        self.assertTrue(G.decision(primary, labs, False, 'claude', True)['rule'].startswith('NC1'))
        self.assertTrue(G.decision(primary, labs, False, 'claude', True, False)['rule'].startswith('NC1'))


class BatchTests(unittest.TestCase):
    def setup_state(self, root):
        key, kh, _, _, _ = fixture()
        report = {'completed': True, 'findings': [], 'uncertainties': []}
        for cell, arm in [('codex','N1'), ('codex','N2'), ('claude','N1')]:
            self.add(root, key, kh, cell, arm, report)
        return key, kh

    def add(self, root, key, kh, cell, arm, report):
        path = root / f'{cell}-{arm}.json'
        save(path, report)
        row = {'attempt_id': cell+'-'+arm+'.a1', 'cell': cell, 'arm': arm, 'status':'completed',
               'dry_run':False, 'freeze_sha256':R.frozen(), 'packet_sha256':key['packet_sha256'],
               'key_sha256':kh, 'report_path':path.name, 'report_sha256':sha(path.read_bytes()),
               'metering_complete':True, 'isolation_complete':True, 'tokens_total':100,
               'tokens_noncache':10, 'seconds':2}
        append(root / ('rows-'+cell+'.jsonl'), row)

    def grades(self, key, index, value):
        gs = fixture()[2]
        for j,g in enumerate(gs):
            g.update(family=G.GRADERS[('codex','claude')[j]][1], model=G.GRADERS[('codex','claude')[j]][0],
                     rubric_sha256=index['rubric_sha256'], blind_pack_sha256=sha(canonical(index)))
            g['reports'] = [{**r, 'valid_review': True, 'unsupported_claims': [], 'blinding_risks': [],
                'items':[{'id':i['id'], 'label':value, 'reason':'Synthetic label.',
                          'report_evidence':['F001: synthetic passage'] if value!='absent' else [],
                          'source_evidence':['synthetic.txt:1']} for i in key['items']]} for r in index['reports']]
        return gs

    def test_two_batches_repeats_never_change_decisions(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            root=Path(tmp); key, kh = self.setup_state(root)
            ix1=G.pack(root,root/'blind1',1); mp1=load(root/'blind1-PRIVATE-MAP.json')
            self.assertEqual(len(ix1['reports']),3)
            self.assertNotIn('seed',ix1); self.assertNotIn('batch',ix1)
            gs1=self.grades(key,ix1,'absent')
            first=G.score(key,kh,gs1,ix1,mp1)
            first.update(accounting_complete=True,reconciliation_complete=True)
            self.assertEqual(first['cells']['codex']['outcome'],'room')
            self.assertEqual(first['cells']['claude']['outcome'],'no conclusion')
            self.add(root,key,kh,'claude','N2',{'completed':True,'findings':[],'uncertainties':[]})
            ix2=G.pack(root,root/'blind2',2); mp2=load(root/'blind2-PRIVATE-MAP.json')
            self.assertEqual(mp2['seed'],'egmcal-issue20-2026-11-14-v1-batch2')
            self.assertEqual(len(ix2['reports']),4)
            self.assertFalse({r['report_id'] for r in ix1['reports']} & {r['report_id'] for r in ix2['reports']})
            gs2=self.grades(key,ix2,'detected')
            result=G.score(key,kh,gs2,ix2,mp2,previous=first)
            self.assertEqual(result['cells']['codex']['outcome'],'room')
            self.assertEqual(result['cells']['claude']['outcome'],'ceiling')
            self.assertEqual(result['cells']['claude']['reports']['N1']['labels']['anthropic']['K01'],'absent')
            self.assertTrue(all(x['same_labels']==0 for x in result['test_retest_agreement']))
            self.assertEqual(len(result['test_retest_agreement']),12)
            self.assertEqual(result['cells']['claude']['measured_native_unit_cost']['native_to_historical_ratio'],100/18_480_203)
            with self.assertRaises(ValueError): G.pack(root,root/'blind2',2)

    def test_primary_area_denominators_and_no_report_based_exclusion(self):
        f=fixture()
        for item,new in zip(f[0]['items'],['K14','K15','K18']):
            old=item['id'];item['id']=new
            for grade in f[2]:
                for report in grade['reports']:
                    next(i for i in report['items'] if i['id']==old)['id']=new
        r=G.score(*f)
        area=r['cells']['codex']['recall_by_area']['catalog']['family-a']
        self.assertEqual(area['denominator'],3)
        self.assertEqual(area['native_union'],1)
        label(f[2],'K14','not adjudicable')
        r=G.score(*f)
        self.assertTrue(r['cells']['codex']['rule'].startswith('NC4'))
        self.assertEqual(r['cells']['codex']['recall_by_area']['catalog']['family-a']['denominator'],3)


class ReconciliationTests(unittest.TestCase):
    def test_one_round_consensus_only_and_anonymous_payload(self):
        helper=T.GraderLaunchTests()
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            root=Path(tmp)
            protocol,packet,key,blind,state,_,index=helper.setup_inputs(root)
            gs=[]
            for family in ('codex','claude'):
                g=Q.envelope(index,family)
                g['reports']=[{**r,'valid_review':True,'unsupported_claims':[],'blinding_risks':[],
                    'items':[{'id':f'K{i:02d}','label':'absent' if family=='codex' else 'detected',
                              'report_evidence':[] if family=='codex' else ['F001: passage'],
                              'source_evidence':['synthetic.txt:1'],'reason':'Synthetic reason.'} for i in range(1,4)]}
                              for r in index['reports']]
                gs.append(g)
                save(root/(family+'.json'),g)
            a=SimpleNamespace(blind=blind,key=key,state=state,packet=packet,grade_a=root/'codex.json',grade_b=root/'claude.json',
                out=root/'resolution.json',codex_cli=None,claude_cli=None,codex_auth_file=None,claude_auth_file=None,dry_run=False)
            prompts=[]
            def request(args,idx,ident,stage,prompt):
                prompts.append(prompt)
                payload=json.loads(prompt.splitlines()[-1]); self.assertNotIn('cell',payload)
                answers=[]
                for d in payload['disagreements']:
                    # K01 reaches consensus absent; K02 and K03 remain original disagreements.
                    v='absent' if d['id']=='K01' or args.family=='codex' else 'detected'
                    old=d['positions'][G.GRADERS[args.family][1]]['label']
                    answers.append({'report_id':d['report_id'],'id':d['id'],'label':v,
                        'action':'keep' if old==v else 'change','report_evidence':[] if v=='absent' else ['F001: passage'],
                        'reason':'Synthetic recheck.'})
                return {'answers':answers}
            with patch.object(G,'HERE',protocol),patch.object(Q,'request',side_effect=request) as launch:
                self.assertEqual(Q.reconcile(a),0)
                self.assertEqual(launch.call_count,2)
            resolution=load(a.out)
            self.assertEqual(len(resolution['changes']),len(index['reports']))
            resolved=G.apply_resolution(gs,resolution,[sha(a.grade_a.read_bytes()),sha(a.grade_b.read_bytes())],index,{'K01','K02','K03'})
            self.assertEqual(resolved[1]['reports'][0]['items'][0]['label'],'absent')
            self.assertEqual(resolved[1]['reports'][0]['items'][1]['label'],'detected')
            self.assertEqual(gs[1]['reports'][0]['items'][0]['label'],'detected')
            with self.assertRaises(ValueError): Q.reconcile(a)

    def test_missing_grader_is_nc1(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            root=Path(tmp);save(root/'key.json',fixture()[0])
            self.assertEqual(G.main(['score','--key',str(root/'key.json'),'--grade-a',str(root/'missingA'),
                '--grade-b',str(root/'missingB'),'--index',str(root/'none'),'--private-map',str(root/'none'),
                '--state',tmp,'--out',str(root/'result.json')]),0)
            self.assertTrue(all(c['rule'].startswith('NC1') for c in load(root/'result.json')['cells'].values()))


class RequestAccountingTests(unittest.TestCase):
    def test_actual_print_adapter_with_invented_cli_and_no_tools(self):
        """Execute a local fake host under Landlock; no provider/model/network access."""
        import os
        from contextlib import ExitStack
        import cal_sandbox
        from cal_common import rows
        try:
            cal_sandbox.abi()
        except ValueError as exc:
            self.skipTest(str(exc))
        for mode in ('success','tool','malformed'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(dir=ROOT) as tmp, ExitStack() as stack:
                root=Path(tmp)
                protocol,packet,key,blind,state,_,index=T.GraderLaunchTests().setup_inputs(root)
                r=index['reports'][0]
                answer={**r,'valid_review':True,'items':[{'id':f'K{i:02d}','label':'absent',
                    'report_evidence':[],'reason':'No such passage.'} for i in range(1,4)],'blinding_risks':[]}
                cli=root/'fake-cli'
                code='''#!/usr/bin/python3
import json,sys
from pathlib import Path
assert sys.argv[sys.argv.index('--tools')+1] == ''
assert '-p' in sys.argv
assert sys.stdin.read() == 'invented inline input'
assert not (Path.cwd()/'packet').exists()
print(json.dumps({'type':'system','subtype':'init','apiKeySource':'none','model':'claude-fable-5-2','claude_code_version':'2.1.322'}),flush=True)
'''
                if mode=='tool':
                    code+="print(json.dumps({'type':'assistant','message':{'id':'fake','content':[{'type':'tool_use','name':'Read'}]}}),flush=True)\n"
                final={'type':'result','result':json.dumps(answer) if mode!='malformed' else 'not JSON',
                    'modelUsage':{'claude-fable-5-2':{'inputTokens':100,'outputTokens':10,'cacheReadInputTokens':500,'cacheCreationInputTokens':5}}}
                code+='print('+repr(json.dumps(final))+',flush=True)\n'
                cli.write_text(code);cli.chmod(0o700)
                a=SimpleNamespace(state=state,family='claude',cli=cli,auth_file=key,gate=root/'gate.json',
                    spent=0,experiment_spent=0,reserve=0,estimate=500_000,budget=15_000_000,dry_run=False)
                stack.enter_context(patch.dict(os.environ,{},clear=True))
                stack.enter_context(patch.object(R,'frozen',return_value='a'*64))
                stack.enter_context(patch.object(R,'check_out',side_effect=lambda p,d:Path(p)))
                stack.enter_context(patch.object(R,'gate_check',return_value={'key_sha256':index['key_sha256'],
                    'cells':{'claude':{'inflight_allowance':1_000_000}}}))
                stack.enter_context(patch.object(R,'auth_home',return_value='subscription_oauth'))
                stack.enter_context(patch.object(R,'cli_identity',return_value='2.1.322'))
                if mode=='success':
                    self.assertEqual(Q.request(a,index,'invented-request','grading','invented inline input'),answer)
                else:
                    with self.assertRaises(ValueError):
                        Q.request(a,index,'invented-request','grading','invented inline input')
                charges=rows(state/'shared-costs.jsonl')
                self.assertEqual(len(charges),1)
                self.assertEqual((charges[0]['logical_tokens'],charges[0]['noncache_tokens']),(615,115))
                self.assertTrue(charges[0]['metering_complete'])
                self.assertEqual(charges[0]['isolation_complete'],mode!='tool')
                with self.assertRaises(ValueError): Q.request(a,index,'invented-request','grading','invented inline input')

    def test_lead_checker_import_complete_and_duplicate_refusal(self):
        import cal_ledger as L
        from cal_common import rows
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            root=Path(tmp);state=root/'state';state.mkdir()
            record={'schema_version':1,'id':'settled-checker','freeze_sha256':'a'*64,'provider':'claude','stage':'curation',
                'logical_tokens':3_398_755,'noncache_tokens':359_512,'seconds':12.5,'metering_complete':True,
                'subagents_included':True,'subagents':'none','metering_source':'session transcript',
                'charge_ids':['settled-checker-root'],'evidence_sha256':['b'*64]}
            save(root/'cost.json',record)
            args=['--state',str(state),'--add-shared',str(root/'cost.json'),'--eligibility-check']
            with patch.object(R,'frozen',return_value='a'*64),patch.object(R,'check_out',side_effect=lambda p,d:Path(p)):
                self.assertEqual(L.main(args),0)
                self.assertEqual(R.spending(state,'a'*64,0,0),(3_398_755,)*2)
                with self.assertRaises(ValueError): L.main(args)
                record['logical_tokens']=3_398_754;save(root/'cost.json',record)
                with self.assertRaises(ValueError): L.main(args)
            self.assertEqual(len(rows(state/'shared-costs.jsonl')),1)
