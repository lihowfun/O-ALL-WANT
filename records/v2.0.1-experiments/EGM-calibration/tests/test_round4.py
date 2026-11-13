"""Five blind-review regressions; invented reports, usage and hosts only."""
from contextlib import ExitStack, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import cal_grade as G
import cal_ledger as L
import cal_requests as Q
import cal_run as R
import cal_launch
from cal_common import append, canonical, load, rows, save, sha
from tests.test_calibration import ROOT, fixture
from tests import test_calibration as T
from tests import test_round3 as T3


class BlindReviewTests(unittest.TestCase):
    def test_p02_reserve_option_removed_from_all_launch_commands(self):
        for module, command in ((R, ['native']), (R, ['preflight']), (G, ['run-grader']), (Q, [])):
            output = io.StringIO()
            with self.subTest(module=module.__name__, command=command), redirect_stdout(output), self.assertRaises(SystemExit) as stopped:
                module.main(command + ['--help'])
            self.assertEqual(stopped.exception.code, 0)
            self.assertNotIn('--reserve', output.getvalue())

    def test_p01_batch1_invalidity_cannot_be_upgraded(self):
        helper = T3.BatchTests()
        for invalid_cell in ('codex', 'claude'):
            with self.subTest(cell=invalid_cell), tempfile.TemporaryDirectory(dir=ROOT) as tmp:
                root = Path(tmp)
                key, kh = helper.setup_state(root)
                ix1 = G.pack(root, root / 'blind1')
                mp1 = load(root / 'blind1-PRIVATE-MAP.json')
                gs1 = helper.grades(key, ix1, 'detected')
                rid = next(rid for rid, m in mp1['reports'].items()
                           if (m['row']['cell'], m['row']['arm']) == (invalid_cell, 'N1'))
                next(r for r in gs1[0]['reports'] if r['report_id'] == rid)['valid_review'] = False
                first = G.score(key, kh, gs1, ix1, mp1)
                first.update(accounting_complete=True, reconciliation_complete=True)
                self.assertTrue(first['cells'][invalid_cell]['rule'].startswith('NC1'))
                helper.add(root, key, kh, 'claude', 'N2', {'completed': True, 'findings': [], 'uncertainties': []})
                ix2 = G.pack(root, root / 'blind2', 2)
                mp2 = load(root / 'blind2-PRIVATE-MAP.json')
                gs2 = helper.grades(key, ix2, 'detected')
                result = G.score(key, kh, gs2, ix2, mp2, previous=first)
                self.assertTrue(result['cells'][invalid_cell]['rule'].startswith('NC1'))
                self.assertEqual(result['cells'][invalid_cell]['reports']['N1'], first['cells'][invalid_cell]['reports']['N1'])
                if invalid_cell == 'codex':
                    self.assertEqual(result['cells']['codex'], first['cells']['codex'])
                failed = G.score(key, kh, gs2, ix2, mp2, previous=first, accounting_complete=False)
                self.assertTrue(all(c['rule'].startswith('NC1') for c in failed['cells'].values()))

    def test_p02_n2_reserve_is_computed_not_chosen(self):
        for chosen in (0, 2_000_000):
            with self.subTest(chosen=chosen), tempfile.TemporaryDirectory(dir=ROOT) as tmp:
                root = Path(tmp)
                a, attempts = T3.SequentialTests().prepare(root)
                a.reserve = chosen  # Legacy callers cannot influence the decision.
                with patch.object(R, 'spending', return_value=(9_050_000, 9_050_000)):
                    self.assertTrue(R.sequential_n2(a, root, attempts, 'a' * 64))
                self.assertEqual(load(root / 'claude-sequential.json')['remaining_claude_grading_reserve'], 750_000)

    def test_p02_observed_request_raises_reserve_and_guards_all_paths(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            root = Path(tmp)
            a, attempts = T3.SequentialTests().prepare(root)
            append(root / 'shared-costs.jsonl', {'provider': 'claude', 'stage': 'grading', 'id': 'observed',
                                                'logical_tokens': 300_001, 'dry_run': False})
            with patch.object(R, 'spending', return_value=(8_000_000, 8_000_000)):
                self.assertFalse(R.sequential_n2(a, root, attempts, 'a' * 64))
            self.assertEqual(load(root / 'claude-sequential.json')['remaining_claude_grading_reserve'], 5 * 390_002)
            index = fixture()[3]
            prefix = Q.identity(index, 'claude')
            # Current Claude request is excluded; Codex reserves every pending Claude slot.
            self.assertEqual(R.grading_reserve(root, index=index, family='claude', current_id=prefix + '-R001'), 4 * 390_002)
            self.assertEqual(R.grading_reserve(root, index=index, family='codex'), 5 * 390_002)
            append(root / 'shared-costs.jsonl', {'provider': 'claude', 'stage': 'reconciliation',
                'id': prefix + '-R001', 'logical_tokens': 100, 'dry_run': False})
            self.assertEqual(R.grading_reserve(root, index=index, family='codex'), 4 * 390_002)

    def test_p03_pack_rewrites_all_strings_and_keeps_private_original(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            root = Path(tmp)
            key, kh, *_ = fixture()
            originals = {}
            for cell, arm in [('codex', 'N1'), ('codex', 'N2'), ('claude', 'N1')]:
                ident = f'{cell}-{arm}.a1'
                parent = root / 'attempts' / f'{cell}-{arm}' / ident
                work = parent / 'workspace'
                report = {'completed': True, 'findings': [{'location': str(work / 'source.txt') + ':1',
                    'claim': 'Synthetic', 'evidence': str(parent / 'home' / 'source.txt'),
                    'rationale': str(root / 'source.txt'), 'severity': 'major',
                    'nested': [str(work / 'other.txt')]}], 'uncertainties': [str(work / 'source.txt')]}
                T3.BatchTests().add(root, key, kh, cell, arm, report)
                originals[root / f'{cell}-{arm}.json'] = (root / f'{cell}-{arm}.json').read_bytes()
            G.pack(root, root / 'blind1')
            for path, data in originals.items():
                self.assertEqual(path.read_bytes(), data)
            mapping = load(root / 'blind1-PRIVATE-MAP.json')
            for rid, m in mapping['reports'].items():
                report = load(root / 'blind1/reports' / (rid + '.json'))
                self.assertEqual(report['findings'][0]['location'], 'packet/source.txt:1')
                self.assertEqual(report['findings'][0]['nested'], ['packet/other.txt'])
                self.assertEqual(report['uncertainties'], ['packet/source.txt'])
                self.assertEqual(m['path_rewrite_count'], 5)
            G.check_blind_paths(root / 'blind1', root, [m['row']['attempt_id'] for m in mapping['reports'].values()])

    def test_p03_blind_path_check_refuses_provenance_components(self):
        for component in ('codex', 'claude', 'N1', 'N2', 'codex-N1', 'claude-N2', 'codex-N1.a1'):
            with self.subTest(component=component), tempfile.TemporaryDirectory(dir=ROOT) as tmp:
                root = Path(tmp)
                key, kh = T3.BatchTests().setup_state(root)
                path = root / 'codex-N1.json'
                report = load(path)
                report['uncertainties'] = ['unrecognized/' + component + '/source.txt:1']
                save(path, report)
                records = rows(root / 'rows-codex.jsonl')
                records[0]['report_sha256'] = sha(path.read_bytes())
                (root / 'rows-codex.jsonl').unlink()
                for row in records:
                    append(root / 'rows-codex.jsonl', row)
                with self.assertRaises(ValueError): G.pack(root, root / 'blind1')

    def test_p04_claude_missing_invalid_and_empty_final_buckets(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            path = Path(tmp) / 'events.jsonl'
            good = {'inputTokens': 50, 'outputTokens': 5, 'cacheReadInputTokens': 20, 'cacheCreationInputTokens': 2}
            for bucket in ({}, {**good, 'outputTokens': None}, {**good, 'inputTokens': True},
                           {k: v for k, v in good.items() if k != 'cacheCreationInputTokens'},
                           dict.fromkeys(good, 0)):
                for streamed in (False, True):
                    events = [{'type': 'assistant', 'message': {'id': 'm', 'usage': {'input_tokens': 10, 'output_tokens': 1}}}] if streamed else []
                    T.MeterTests().stream(path, *events, {'type': 'result', 'result': 'output', 'modelUsage': {'synthetic': bucket}})
                    usage = R.claude_usage(path)
                    self.assertFalse(usage['metering_complete'], bucket)
                    self.assertGreaterEqual(usage['tokens_total'], 11 if streamed else 0)
            T.MeterTests().stream(path, {'type': 'result', 'result': 'output', 'modelUsage': {'good': good, 'missing': {}}})
            usage = R.claude_usage(path)
            self.assertFalse(usage['metering_complete'])
            self.assertEqual((usage['tokens_total'], usage['tokens_noncache']), (77, 57))

    def test_p04_codex_missing_final_counter_keeps_lower_bound(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            root = Path(tmp)
            sessions = root / '.codex/sessions'
            sessions.mkdir(parents=True)
            good = {'input_tokens': 10, 'cached_input_tokens': 5, 'output_tokens': 2}
            for bad in ({}, {'input_tokens': 10, 'output_tokens': 2}, {**good, 'output_tokens': None}, dict.fromkeys(good, 0)):
                raw = root / 'events.jsonl'
                T.MeterTests().stream(raw, {'type': 'thread.started', 'thread_id': 'root'}, {'type': 'turn.completed', 'usage': bad})
                T.MeterTests().stream(sessions / 'rollout-root.jsonl',
                    {'type': 'session_meta', 'payload': {'id': 'root', 'cwd': str(root)}},
                    {'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {'total_token_usage': bad}}},
                    {'type': 'event_msg', 'payload': {'type': 'task_complete'}})
                self.assertFalse(R.codex_usage(raw, root, root)['metering_complete'], bad)
            T.MeterTests().stream(raw, {'type': 'thread.started', 'thread_id': 'root'}, {'type': 'turn.completed', 'usage': good})
            self.assertGreaterEqual(R.codex_usage(raw, root, root)['tokens_total'], 12)

    def test_p04_actual_grader_and_reconciliation_requests_reject_empty_usage(self):
        try:
            cal_launch.available()
        except ValueError as exc:
            self.skipTest(str(exc))
        for stage in ('grading', 'reconciliation'):
            for streamed in (False, True):
                with self.subTest(stage=stage, streamed=streamed), tempfile.TemporaryDirectory(dir=ROOT) as tmp, ExitStack() as stack:
                    root = Path(tmp)
                    _, _, key, _, state, _, index = T.GraderLaunchTests().setup_inputs(root)
                    cli = root / 'runtime/fake-cli'
                    cli.parent.mkdir()
                    events = [{'type': 'system', 'subtype': 'init', 'apiKeySource': 'none', 'model': 'claude-fable-5-2'}]
                    if streamed:
                        events.append({'type': 'assistant', 'message': {'id': 'm', 'usage': {'input_tokens': 500_000, 'output_tokens': 50}}})
                    events.append({'type': 'result', 'result': '{}', 'modelUsage': {'claude-fable-5-2': {}}})
                    cli.write_text('#!/usr/bin/python3\nimport sys\nsys.stdin.read()\n' + ''.join('print(' + repr(json.dumps(e)) + ', flush=True)\n' for e in events))
                    cli.chmod(0o700)
                    a = SimpleNamespace(state=state, family='claude', cli=cli, auth_file=key, gate=root / 'gate.json',
                        spent=0, experiment_spent=0, estimate=500_000, budget=15_000_000, dry_run=False)
                    stack.enter_context(patch.dict(R.os.environ, {'EGMCAL_RUNTIME_ROOTS':str(cli.parent)}, clear=True))
                    stack.enter_context(patch.object(R, 'frozen', return_value='a' * 64))
                    stack.enter_context(patch.object(R, 'check_out', side_effect=lambda p, d: Path(p)))
                    stack.enter_context(patch.object(R, 'gate_check', return_value={'key_sha256': index['key_sha256'], 'cells': {'claude': {'inflight_allowance': 1_000_000}}}))
                    stack.enter_context(patch.object(R, 'auth_home', return_value='subscription_oauth'))
                    stack.enter_context(patch.object(R, 'cli_identity', return_value='2.1.322'))
                    with self.assertRaises(ValueError): Q.request(a, index, 'invented-' + stage, stage, 'invented input')
                    record = rows(state / 'shared-costs.jsonl')[0]
                    self.assertFalse(record['metering_complete'])
                    self.assertEqual(record['logical_tokens'], 500_050 if streamed else 0)
                    self.assertEqual(load(state / 'graders' / ('invented-' + stage) / 'usage.json')['status'], 'failed')

    def test_p05_unsettled_intents_invalidate_scoring_and_ledger(self):
        for kind in ('native', 'grading', 'reconciliation'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory(dir=ROOT) as tmp, patch.object(R, 'frozen', return_value='a' * 64):
                root = Path(tmp)
                key = fixture()[0]
                save(root / 'key.json', key)
                kh = sha((root / 'key.json').read_bytes())
                for cell, arm in [('codex', 'N1'), ('codex', 'N2'), ('claude', 'N1')]:
                    T3.BatchTests().add(root, key, kh, cell, arm, {'completed': True, 'findings': [], 'uncertainties': []})
                index = G.pack(root, root / 'blind1')
                grades = T3.BatchTests().grades(key, index, 'absent')
                for i, grade in enumerate(grades):
                    grade['key_sha256'] = kh
                    save(root / f'grade{i}.json', grade)
                save(root / 'resolution.json', {'schema_version': 1, 'input_grade_sha256': [sha((root / f'grade{i}.json').read_bytes()) for i in range(2)],
                    'blind_pack_sha256': sha(canonical(index)), 'unblinding_occurred': False, 'rounds': 1, 'changes': []})
                save(root / 'audit.json', {'schema_version': 1, 'freeze_sha256': 'a' * 64, 'all_shared_work_recorded': True,
                    'isolation_audit_complete': True, 'grading_metering_complete': True, 'curation_metering_complete': True,
                    'evidence_sha256': ['b' * 64], 'outside_stage_claude_logical': 0, 'outside_experiment_claude_logical': 0})
                ident = 'claude-N2.a1' if kind == 'native' else 'grader-claude-' + kind
                parent = root / ('attempts/claude-N2' if kind == 'native' else 'graders') / ident
                parent.mkdir(parents=True)
                intent = {'freeze_sha256': 'a' * 64, 'cell': 'claude', 'arm': 'N2', 'attempt_id': ident} if kind == 'native' else {'freeze_sha256': 'a' * 64, 'provider': 'claude', 'id': ident, 'stage': kind}
                save(parent / 'intent.json', intent)
                T.MeterTests().stream(parent / 'events.jsonl', {'type': 'assistant', 'message': {'id': 'm', 'usage': {'input_tokens': 500_000, 'output_tokens': 50}}})
                ledger = L.summary(root, 'a' * 64)
                self.assertFalse(ledger['providers']['claude']['metering_complete_for_recorded_work'])
                self.assertEqual(ledger['providers']['claude']['observed_logical_tokens'], 500_150)
                self.assertEqual(len(ledger['unsettled_intents']), 1)
                self.assertFalse(G.final_accounting(load(root / 'audit.json'), ledger, 'a' * 64))
                args = ['score', '--key', str(root / 'key.json'), '--grade-a', str(root / 'grade0.json'), '--grade-b', str(root / 'grade1.json'),
                    '--index', str(root / 'blind1/index.json'), '--private-map', str(root / 'blind1-PRIVATE-MAP.json'), '--state', str(root),
                    '--resolution', str(root / 'resolution.json'), '--accounting', str(root / 'audit.json'), '--out', str(root / 'final.json')]
                self.assertEqual(G.main(args), 0)
                result = load(root / 'final.json')
                self.assertTrue(result['cells']['claude']['rule'].startswith('NC1'))
                self.assertFalse(result['cells']['claude']['native_unit_cost_including_all_attempts']['complete'] if kind == 'native' else result['accounting_complete'])
                with self.assertRaises(ValueError): R.spending(root, 'a' * 64, 0, 0)
                # Recovery settles the same intent exactly once; raw usage is no longer added twice.
                if kind == 'native':
                    append(root / 'rows-claude.jsonl', {**intent, 'status': 'failed', 'tokens_total': 500_050,
                        'tokens_noncache': 500_050, 'metering_complete': True, 'isolation_complete': True})
                else:
                    append(root / 'shared-costs.jsonl', {'schema_version': 1, 'id': ident, 'freeze_sha256': 'a' * 64,
                        'provider': 'claude', 'stage': kind, 'logical_tokens': 500_050, 'noncache_tokens': 500_050,
                        'seconds': 1, 'metering_complete': True, 'subagents_included': True,
                        'charge_ids': [ident], 'evidence_sha256': [sha((parent / 'events.jsonl').read_bytes())]})
                recovered = L.summary(root, 'a' * 64)
                self.assertEqual(recovered['unsettled_intents'], [])
                self.assertEqual(recovered['providers']['claude']['observed_logical_tokens'], 500_150)
                self.assertTrue(recovered['providers']['claude']['metering_complete_for_recorded_work'])
                self.assertEqual(G.main(args), 0)
                self.assertEqual(load(root / 'final.json')['cells']['claude']['rule'].startswith('NC1'), kind == 'native')
