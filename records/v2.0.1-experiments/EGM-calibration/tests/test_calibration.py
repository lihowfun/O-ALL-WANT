import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from contextlib import ExitStack

import build_packet
import cal_grade as G
import cal_run as R
import cal_launch
from cal_common import canonical, load, save, sha

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    packet = 'a' * 64
    key = {'schema_version': 1, 'packet_sha256': packet, 'items': [
        {'id': f'K{i:02d}', 'tier': 'primary', 'cluster': f'synthetic-{i}',
         'claim': 'Synthetic defect only', 'evidence': ['synthetic.txt:1'],
         'detected_if': 'synthetic mechanism', 'mention_only_if': 'synthetic uncertainty',
         'not_adjudicable_if': 'synthetic missing context'} for i in range(1, 4)]}
    kh = sha(canonical(key))
    index = {'schema_version': 1, 'seed': G.SEED, 'packet_sha256': packet,
             'key_sha256': kh, 'rubric_sha256': 'b' * 64, 'reports': []}
    mapping = {'schema_version': 1, 'reports': {}}
    for cell in R.CELLS:
        for arm in ('N1', 'N2'):
            ident = f'R{len(index["reports"]) + 1:03d}'
            digest = sha(ident.encode())
            index['reports'].append({'report_id': ident, 'report_sha256': digest})
            row = {'cell': cell, 'arm': arm, 'status': 'completed', 'dry_run': False,
                   'packet_sha256': packet, 'key_sha256': kh, 'metering_complete': True,
                   'isolation_complete': True, 'tokens_total': 100, 'tokens_noncache': 10, 'seconds': 2}
            mapping['reports'][ident] = {'row': row, 'anonymous_sha256': digest}
    mapping['blind_pack_sha256'] = sha(canonical(index))
    grades = []
    for family in ('family-a', 'family-b'):
        grade = {'schema_version': 1, 'grader_id': family, 'family': family,
                 'model': 'synthetic-grader', 'key_sha256': kh, 'packet_sha256': packet,
                 'rubric_sha256': index['rubric_sha256'], 'blind_pack_sha256': sha(canonical(index)),
                 'independent': True, 'blinded': True,
                 'reports': []}
        for r in index['reports']:
            grade['reports'].append({**r, 'valid_review': True, 'unsupported_claims': [], 'blinding_risks': [],
                'items': [{'id': k['id'], 'label': 'detected', 'reason': 'synthetic match',
                           'report_evidence': ['F001.claim'], 'source_evidence': ['synthetic.txt:1']} for k in key['items']]})
        grades.append(grade)
    return key, kh, grades, index, mapping


def label(grades, item, value, reports=None):
    for g in grades:
        for r in g['reports']:
            if reports is None or r['report_id'] in reports:
                next(i for i in r['items'] if i['id'] == item)['label'] = value


class DecisionTests(unittest.TestCase):
    def evaluate(self, f):
        return G.score(*f)['cells']

    def test_ceiling(self):
        self.assertTrue(all(c['outcome'] == 'ceiling' for c in self.evaluate(fixture()).values()))

    def test_room_both_native_absent(self):
        f = fixture()
        label(f[2], 'K01', 'absent')
        for result in self.evaluate(f).values():
            self.assertEqual(result['outcome'], 'room')
            self.assertEqual(result['room_items'], ['K01'])
            self.assertEqual(result['measured_native_unit_cost']['logical_tokens'], 100)

    def test_union_can_use_different_run_per_grader(self):
        f = fixture()
        label(f[2][:1], 'K01', 'absent', ['R001'])
        label(f[2][1:], 'K01', 'absent', ['R002'])
        self.assertEqual(self.evaluate(f)['claude']['outcome'], 'ceiling')

    def test_unresolved_deciding_disagreement(self):
        f = fixture()
        label(f[2], 'K01', 'absent')
        label(f[2][:1], 'K01', 'detected', ['R001', 'R004'])
        self.assertTrue(all(c['rule'].startswith('NC4') for c in self.evaluate(f).values()))

    def test_mention_is_not_absent(self):
        f = fixture()
        label(f[2], 'K01', 'mention-only')
        self.assertTrue(all(c['outcome'] == 'no conclusion' for c in self.evaluate(f).values()))

    def test_missing_required_native_is_no_conclusion(self):
        f = fixture()
        f[4]['reports']['R001']['row']['status'] = 'failed'
        self.assertTrue(self.evaluate(f)['claude']['rule'].startswith('NC1'))
        self.assertEqual(self.evaluate(f)['codex']['outcome'], 'ceiling')

    def test_isolation_or_metering_missing(self):
        for field in ('isolation_complete', 'metering_complete'):
            f = fixture()
            f[4]['reports']['R001']['row'][field] = False
            self.assertEqual(self.evaluate(f)['claude']['outcome'], 'no conclusion')

    def test_grader_cannot_redecide_eligibility(self):
        f = fixture()
        f[2][0]['eligibility'] = [{'id': 'K01', 'adjudicable': False}]
        with self.assertRaises(ValueError): self.evaluate(f)

    def test_na_in_one_native_does_not_erase_other_detection(self):
        f = fixture()
        label(f[2], 'K01', 'not adjudicable', ['R001', 'R004'])
        self.assertTrue(all(c['outcome'] == 'ceiling' for c in self.evaluate(f).values()))

    def test_na_in_both_does_not_mean_room(self):
        f = fixture()
        label(f[2], 'K01', 'not adjudicable')
        self.assertTrue(all(c['outcome'] == 'no conclusion' for c in self.evaluate(f).values()))

    def test_grade_binding_and_schema_refuse(self):
        for mutation in ('hash', 'duplicate', 'unknown', 'model', 'family', 'missing'):
            f = fixture()
            if mutation == 'hash': f[2][0]['key_sha256'] = '0' * 64
            if mutation == 'duplicate': f[2][0]['reports'][0]['items'][1]['id'] = 'K01'
            if mutation == 'unknown': f[2][0]['reports'][0]['items'][0]['label'] = 'maybe'
            if mutation == 'model': f[2][0]['model'] = 'gpt-6.1-sol'
            if mutation == 'family': f[2][1]['family'] = f[2][0]['family']
            if mutation == 'missing': f[2][0]['reports'].pop()
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): self.evaluate(f)

    def test_unsupported_severe_evidence_and_listing(self):
        f = fixture()
        claim = {'id': 'S1', 'claim': 'synthetic unsupported assertion', 'reason': 'contradicted',
                 'source_evidence': ['synthetic.txt:1'], 'report_evidence': ['F001'],
                 'severe': True, 'severe_effect': 'synthetic blocking effect'}
        f[2][0]['reports'][0]['unsupported_claims'] = [claim]
        result = self.evaluate(f)['claude']
        self.assertEqual(result['outcome'], 'ceiling')  # descriptive, no invented safety gate
        self.assertEqual(result['reports']['N1']['severe_false_alarms']['family-a'], [claim])
        del claim['source_evidence']
        with self.assertRaises(ValueError): self.evaluate(f)

    def test_blind_resolution_preserves_original(self):
        f = fixture()
        label(f[2], 'K01', 'absent')
        label(f[2][:1], 'K01', 'detected', ['R001'])
        resolution = {'schema_version': 1, 'input_grade_sha256': ['a', 'b'],
                      'blind_pack_sha256': sha(canonical(f[3])), 'unblinding_occurred': False,
                      'changes': [{'scope': 'item', 'report_id': 'R001', 'id': 'K01', 'label': 'absent',
                                   'reason': 'synthetic recheck', 'source_evidence': ['synthetic.txt:1'],
                                   'report_evidence': [], 'accepted_by': ['family-a', 'family-b']}]}
        result = G.score(*f, resolution=resolution, grade_hashes=['a', 'b'])
        self.assertEqual(result['cells']['claude']['outcome'], 'room')
        self.assertEqual(result['cells']['claude']['before_resolution']['outcome'], 'no conclusion')
        self.assertEqual(f[2][0]['reports'][0]['items'][0]['label'], 'detected')
        resolution['unblinding_occurred'] = True
        with self.assertRaises(ValueError): G.score(*f, resolution=resolution, grade_hashes=['a', 'b'])
        resolution['unblinding_occurred'] = False
        resolution['changes'][0]['id'] = 'K02'
        with self.assertRaises(ValueError): G.score(*f, resolution=resolution, grade_hashes=['a', 'b'])


    def test_final_accounting_gate_and_caps(self):
        binding = 'a' * 64
        ledger = {'providers': {p: {'observed_logical_tokens': 100,
                    'metering_complete_for_recorded_work': True} for p in ('claude', 'codex')}}
        audit = {'schema_version': 1, 'freeze_sha256': binding,
                 'all_shared_work_recorded': True, 'isolation_audit_complete': True,
                 'grading_metering_complete': True, 'curation_metering_complete': True,
                 'evidence_sha256': ['b' * 64], 'outside_stage_claude_logical': 0,
                 'outside_experiment_claude_logical': 0}
        self.assertTrue(G.final_accounting(audit, ledger, binding))
        self.assertFalse(G.final_accounting({}, ledger, binding))
        audit['outside_stage_claude_logical'] = 15_000_001
        audit['outside_experiment_claude_logical'] = 15_000_001
        self.assertTrue(G.final_accounting(audit, ledger, binding))  # late stage use still scoreable
        audit['outside_experiment_claude_logical'] = 30_000_000
        self.assertFalse(G.final_accounting(audit, ledger, binding))
        f = fixture()
        scored = G.score(*f, accounting_complete=False)
        self.assertTrue(all(c['rule'].startswith('NC1') for c in scored['cells'].values()))

    def test_synthetic_blind_pack_and_score_cli(self):
        # Every report, key item and grade in this test is invented. No real key is read.
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            state = Path(tmp)
            key = fixture()[0]
            key['packet_sha256'] = load(ROOT / 'packet_manifest.json')['tree_sha256']
            save(state / 'synthetic-key.json', key)
            kh = sha((state / 'synthetic-key.json').read_bytes())
            report = {'completed': True, 'findings': [{'location': 'synthetic.txt:1',
                'claim': 'Synthetic defect only', 'evidence': 'synthetic.txt:1',
                'rationale': 'Synthetic effect', 'severity': 'major'}], 'uncertainties': []}
            from cal_common import append
            for cell in R.CELLS:
                for arm in ('N1', 'N2'):
                    if (cell, arm) == ('claude', 'N2'):
                        continue
                    path = state / (cell + '-' + arm + '.json')
                    save(path, report)
                    row = {'attempt_id': cell + '-' + arm + '.a1', 'cell': cell, 'arm': arm,
                        'status': 'completed', 'dry_run': False, 'freeze_sha256': R.frozen(),
                        'key_sha256': kh, 'packet_sha256': key['packet_sha256'], 'metering_complete': True,
                        'isolation_complete': True, 'tokens_total': 100, 'tokens_noncache': 10, 'seconds': 2,
                        'report_path': path.name, 'report_sha256': sha(path.read_bytes())}
                    if arm == 'M':
                        mp = state / (cell + '-mapping.json')
                        save(mp, {'schema_version': 1, 'mapping': [
                            {'input_id': 'A:F001', 'action': 'kept', 'output_ids': ['F001'], 'reason': 'synthetic'},
                            {'input_id': 'B:F001', 'action': 'dropped', 'output_ids': ['F001'], 'reason': 'synthetic duplicate'}], 'contradictions': []})
                        row.update(mapping_path=mp.name, mapping_sha256=sha(mp.read_bytes()))
                    append(state / ('rows-' + cell + '.jsonl'), row)
            self.assertEqual(G.main(['pack', '--state', str(state), '--out', str(state / 'blind')]), 0)
            index = load(state / 'blind/index.json')
            for i, (model, family) in enumerate(G.GRADERS.values()):
                grade = fixture()[2][i]
                grade.update(grader_id=family, family=family, model=model, key_sha256=kh,
                             packet_sha256=key['packet_sha256'], rubric_sha256=index['rubric_sha256'],
                             blind_pack_sha256=sha(canonical(index)))
                grade['reports'] = grade['reports'][:len(index['reports'])]
                for r, actual in zip(grade['reports'], index['reports']):
                    r.update(actual)
                save(state / ('grade-' + str(i) + '.json'), grade)
            save(state / 'accounting.json', {'schema_version': 1, 'freeze_sha256': R.frozen(),
                 'all_shared_work_recorded': True, 'isolation_audit_complete': True,
                 'grading_metering_complete': True, 'curation_metering_complete': True,
                 'outside_stage_claude_logical': 0, 'outside_experiment_claude_logical': 0,
                 'evidence_sha256': [sha(b'synthetic-accounting-evidence')]})
            save(state / 'resolution.json', {'schema_version': 1, 'input_grade_sha256':
                [sha((state / ('grade-' + str(i) + '.json')).read_bytes()) for i in range(2)],
                'blind_pack_sha256': sha(canonical(index)), 'unblinding_occurred': False, 'rounds': 1, 'changes': []})
            self.assertEqual(G.main(['score', '--key', str(state / 'synthetic-key.json'),
                '--grade-a', str(state / 'grade-0.json'), '--grade-b', str(state / 'grade-1.json'),
                '--index', str(state / 'blind/index.json'), '--private-map', str(state / 'blind-PRIVATE-MAP.json'),
                '--state', str(state), '--resolution', str(state / 'resolution.json'), '--accounting', str(state / 'accounting.json'),
                '--out', str(state / 'decision.json')]), 0)
            result = load(state / 'decision.json')
            self.assertTrue(all(c['outcome'] == 'ceiling' for c in result['cells'].values()))
            self.assertNotIn('merge_mappings', result)


class PacketTests(unittest.TestCase):
    def test_manifest_closed_world(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            p = Path(tmp)
            (p / 'source.txt').write_text('source')
            manifest = build_packet.inventory(p)
            build_packet.verify(p, manifest)
            (p / 'extra').write_text('extra')
            with self.assertRaises(ValueError): build_packet.verify(p, manifest)
            (p / 'extra').unlink()
            (p / 'source.txt').write_text('changed')
            with self.assertRaises(ValueError): build_packet.verify(p, manifest)

    def test_forbidden_dirs_and_symlinks(self):
        for bad in ('.git', 'review_out', 'link'):
            with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
                p = Path(tmp)
                (p / 'a').write_text('a')
                if bad == 'link': (p / bad).symlink_to(p / 'a')
                else: (p / bad).mkdir()
                with self.subTest(bad=bad), self.assertRaises(ValueError): build_packet.inventory(p)


class MeterTests(unittest.TestCase):
    def stream(self, path, *events):
        path.write_bytes(b''.join(canonical(e) + b'\n' for e in events))

    def test_claude_dedup_and_all_model_usage(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            p = Path(tmp) / 'events.jsonl'
            msg = {'type': 'assistant', 'message': {'id': 'same', 'usage': {'input_tokens': 5, 'output_tokens': 1}}}
            self.stream(p, {'type': 'system', 'subtype': 'init', 'apiKeySource': 'none', 'model': 'claude-opus-5-5'},
                        msg, msg, {'type': 'result', 'modelUsage': {'parent': {'inputTokens': 5, 'outputTokens': 2, 'cacheReadInputTokens': 10, 'cacheCreationInputTokens': 0},
                                                                  'child': {'inputTokens': 3, 'outputTokens': 1, 'cacheCreationInputTokens': 4, 'cacheReadInputTokens': 0}}})
            u = R.claude_usage(p)
            self.assertEqual((u['tokens_total'], u['tokens_noncache'], u['streamed_lower_bound']), (25, 15, 6))
            self.assertTrue(u['metering_complete'])
            self.stream(p, msg)
            self.assertFalse(R.claude_usage(p)['metering_complete'])

    def test_codex_descendants_last_cumulative_stray_missing(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            p = Path(tmp)
            sessions = p / '.codex' / 'sessions'
            sessions.mkdir(parents=True)
            raw = p / 'events.jsonl'
            self.stream(raw, {'type': 'thread.started', 'thread_id': 'root'}, {'type': 'turn.completed', 'usage': {'input_tokens': 10, 'cached_input_tokens': 5, 'output_tokens': 2}})
            def thread(ident, parent, total):
                meta = {'id': ident, 'cwd': str(p), 'parent_thread_id': parent}
                e = {'type': 'session_meta', 'payload': meta}
                usage = {'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {'total_token_usage': {'input_tokens': total, 'cached_input_tokens': 5, 'output_tokens': 2}}}}
                self.stream(sessions / ('rollout-' + ident + '.jsonl'), e, usage, usage,
                            {'type': 'event_msg', 'payload': {'type': 'task_complete'}})
            thread('root', None, 10)
            thread('child', 'root', 20)
            thread('grandchild', 'child', 30)
            u = R.codex_usage(raw, p, p)
            self.assertEqual((u['tokens_total'], u['tokens_noncache'], u['agents']), (66, 51, 2))
            self.assertTrue(u['metering_complete'])
            thread('stray', None, 10)
            self.assertFalse(R.codex_usage(raw, p, p)['metering_complete'])
            (sessions / 'rollout-stray.jsonl').unlink()
            (sessions / 'rollout-child.jsonl').write_text(json.dumps({'type': 'session_meta', 'payload': {'id': 'child', 'cwd': str(p), 'parent_thread_id': 'root'}}) + '\n')
            self.assertFalse(R.codex_usage(raw, p, p)['metering_complete'])

    def test_api_key_refusal(self):
        for k in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'ANY_API_KEY', 'OPENAI_BASE_URL'):
            with self.subTest(key=k), self.assertRaises(ValueError): R.no_api_keys({k: 'not-a-real-secret'})

    def test_merge_mapping_coverage_and_no_promotion(self):
        report = {'completed': True, 'findings': [{'location': 'x:1', 'claim': 'synthetic', 'evidence': 'x:1', 'rationale': 'effect', 'severity': 'major'}], 'uncertainties': []}
        empty = {'completed': True, 'findings': [], 'uncertainties': []}
        mapping = {'schema_version': 1, 'mapping': [{'input_id': 'A:F001', 'action': 'kept', 'output_ids': ['F001'], 'reason': 'retain'}], 'contradictions': []}
        R.validate_mapping(mapping, [report, empty], report)
        mapping['mapping'] = []
        with self.assertRaises(ValueError): R.validate_mapping(mapping, [report, empty], report)


class OfflineRunnerTests(unittest.TestCase):
    def test_sequential_native_resume_no_cli_or_network(self):
        packet = os.environ.get('EGMCAL_TEST_PACKET', str(ROOT.parent / 'egmcal-src' / 'packet'))
        if not Path(packet).is_dir():
            self.skipTest('pristine packet unavailable; set EGMCAL_TEST_PACKET')
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp, patch.dict(os.environ, {}, clear=True), \
             patch.object(subprocess, 'Popen', side_effect=AssertionError('no subprocess in dry run')):
            for cell, arm in [('codex', 'N1'), ('codex', 'N2'), ('claude', 'N1'), ('claude', 'N2')]:
                base = ['--cell', cell, '--only', arm, '--packet', packet, '--out', tmp, '--dry-run']
                self.assertEqual(R.main(['native'] + base), 0)
                self.assertEqual(R.main(['native'] + base), 0)
            for cell in R.CELLS:
                self.assertEqual(len((Path(tmp) / ('rows-' + cell + '.jsonl')).read_text().splitlines()), 2)
                with self.assertRaises(ValueError):
                    R.main(['merge', '--cell', cell, '--packet', packet, '--out', tmp, '--dry-run'])
            with self.assertRaises(ValueError): G.pack(tmp, Path(tmp) / 'blind')

    def test_unsettled_attempt_blocks_resume(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            out = Path(tmp)
            p = out / 'attempts' / 'claude-N1' / 'claude-N1.a1'
            p.mkdir(parents=True)
            save(p / 'intent.json', {'attempt_id': 'claude-N1.a1', 'freeze_sha256': 'a' * 64})
            with self.assertRaises(ValueError): R.read_state(out, 'a' * 64)

    def test_prompt_diff_and_shared_context(self):
        import difflib
        original = (ROOT / 'prompts/x2-native.txt').read_text()
        native = (ROOT / 'prompts/native.txt').read_text()
        context = (ROOT / 'prompts/task_context.txt').read_text()
        self.assertTrue(native.startswith(context))
        self.assertEqual((ROOT / 'prompts/native-vs-x2.diff').read_text(), ''.join(
            difflib.unified_diff(original.splitlines(True), native.splitlines(True),
                                 fromfile='X2/TASK (empty treatment)', tofile='prompts/native.txt')))
        self.assertIn('at most 1500 words', native)

    def test_live_stop_with_synthetic_host(self):
        try:
            cal_launch.available()
        except ValueError as exc:
            self.skipTest(str(exc))
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            base = Path(tmp)
            work, home = base / 'work', base / 'home'
            (work / 'review_out').mkdir(parents=True)
            home.mkdir()
            cli = base / 'runtime' / 'fake-cli'
            cli.parent.mkdir()
            self.addCleanup(patch.stopall)
            patch.dict(os.environ, {'EGMCAL_RUNTIME_ROOTS': str(cli.parent)}).start()
            cli.write_text('#!/usr/bin/python3\nimport json,time\n'
                           'print(json.dumps({"type":"assistant","message":{"id":"synthetic",'
                           '"usage":{"input_tokens":900,"output_tokens":0}}}),flush=True)\n'
                           'time.sleep(5)\n')
            cli.chmod(0o700)
            result = R.execute('claude', str(cli), work, home, base, 'synthetic prompt',
                               timeout=10, token_allowance=1000, reserve=100)
            self.assertEqual(result['stop_reason'], 'token_stop')
            self.assertEqual(result['tokens_total'], 900)
            self.assertFalse(result['metering_complete'])

    def test_late_final_allowance_overrun_is_not_itself_a_failed_attempt(self):
        import io
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            base = Path(tmp)
            work, home = base / 'work', base / 'home'
            (work / 'review_out').mkdir(parents=True)
            home.mkdir()
            process = unittest.mock.Mock(pid=999999, returncode=0)
            process.stdin = io.BytesIO()
            process.poll.side_effect = [None, 0, 0]
            running = {'tokens_total': 100, 'api_key_source': 'none', 'result_seen': False}
            final = {'tokens_total': 5000, 'tokens_noncache': 500, 'metering_complete': True,
                     'result_seen': True, 'api_key_source': 'none'}
            with patch.object(subprocess, 'Popen', return_value=process), \
                 patch.object(R, 'get_usage', side_effect=[running, final]), \
                 patch.object(R.os, 'killpg'), patch.object(R.time, 'sleep'), \
                 patch.object(cal_launch, 'bubblewrap', side_effect=lambda command, *args: command):
                u = R.execute('claude', '/usr/bin/true', work, home, base, 'invented probe', 3600, 1000, 100)
            self.assertTrue(u['metering_complete'])
            self.assertIsNone(u['stop_reason'])
            self.assertTrue(u['late_reported_allowance_exceeded'])
            self.assertEqual(u['preflight_live_final_gap'], 5000)

    def test_budget_refuses_before_cli(self):
        packet = Path(os.environ.get('EGMCAL_TEST_PACKET', str(ROOT.parent / 'egmcal-src' / 'packet')))
        if not packet.is_dir(): self.skipTest('pristine packet unavailable')
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp, patch.dict(os.environ, {}, clear=True), \
             patch.object(subprocess, 'Popen', side_effect=AssertionError('no model call')):
            for cell in R.CELLS:
                with self.assertRaises(ValueError):
                    R.main(['native', '--cell', cell, '--packet', str(packet), '--out', tmp,
                            '--only', 'N1', '--dry-run', '--budget', '100000', '--spent', '100000', '--experiment-spent', '100000'])
            self.assertFalse((Path(tmp) / 'attempts').exists())



class PreflightTests(unittest.TestCase):
    def fake_execute(self, cell, cli, work, home, parent, prompt, timeout, token_allowance, reserve, model=None, probe=False):
        self.assertEqual(token_allowance, 500_000)
        self.assertEqual(reserve, 0)
        self.assertEqual((work / 'source.py').read_text(), R.PROBE_SOURCE)
        self.assertEqual(set(p.name for p in work.iterdir()), {'source.py', 'README.txt', 'small.json', 'review_out'})
        (home / cal_launch.MARKER).write_text('bwrap-v1')
        (work / 'source.py').write_text('changed')
        for name in R.SANDBOX_PLACEHOLDERS:
            (work / name).mkdir()
        event = {'type': 'assistant', 'message': {'content': [
            {'type': 'tool_use', 'id': 'list', 'name': 'Glob', 'input': {'pattern': '*'}},
            {'type': 'tool_use', 'id': 'read', 'name': 'Read', 'input': {'path': 'source.py'}},
            {'type': 'tool_use', 'id': 'write', 'name': 'Write', 'input': {'path': 'source.py'}},
            {'type': 'tool_use', 'id': 'outside', 'name': 'Read', 'input': {'path': str(self.outside)}},
            {'type': 'tool_use', 'id': 'web', 'name': 'WebFetch', 'input': {'url': 'https://example.com'}}]}}
        denied_web = {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': 'web', 'is_error': True}]}}
        (parent / 'events.jsonl').write_bytes(canonical(event) + b'\n' + canonical(denied_web) + b'\n')
        (parent / 'stderr.txt').write_bytes(b'')
        save(work / 'review_out' / 'report.json', {'source_overwritten': True, 'other_attempts_refused': True})
        return {'tokens_total': 1234, 'tokens_noncache': 234, 'seconds': 0.5, 'metering_complete': True,
                'api_key_source': 'none', 'model': R.CELLS[cell][0], 'models_seen': [R.CELLS[cell][0]],
                'cli_version': R.CELLS[cell][1], 'result_seen': True, 'exit': 0, 'stop_reason': None,
                'live_observed_totals': [0, 400], 'preflight_live_final_gap': 1234}

    def context(self, root):
        self.outside = root / 'outside.txt'
        self.outside.write_text('harmless synthetic outside canary 0123456789')
        self.cli = root / 'runtime' / 'fake-cli'
        self.cli.parent.mkdir()
        self.cli.write_text('synthetic executable bytes, never executed')
        out = root / 'state'
        out.mkdir()
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.dict(os.environ, {'EGMCAL_RUNTIME_ROOTS': str(self.cli.parent)}, clear=True))
        stack.enter_context(patch.object(R, 'check_out', side_effect=lambda p, dry: Path(p)))
        stack.enter_context(patch.object(R, 'frozen', return_value='a' * 64))
        stack.enter_context(patch.object(R, 'cli_identity', side_effect=lambda c, cli, home: R.CELLS[c][1]))
        stack.enter_context(patch.object(R, 'auth_home', side_effect=lambda c, a, h: 'subscription_oauth' if c == 'claude' else 'subscription_chatgpt'))
        stack.enter_context(patch.object(cal_launch, 'available', return_value=3))
        return stack, out

    def run_probe(self, out, cell, dry=False):
        args = ['preflight', '--cell', cell, '--out', str(out), '--cli', str(self.cli),
                '--auth-file', str(self.cli), '--outside-probe', str(self.outside)]
        return R.main(args + (['--dry-run'] if dry else []))

    def gate_args(self, out):
        return ['gate', '--out', str(out), '--gate', str(out / 'gate.json'), '--claude-cli', str(self.cli),
                '--codex-cli', str(self.cli), '--key-sha256', 'b' * 64, '--freeze-sha256', 'a' * 64,
                '--eligible-primary-count', '3']

    def test_preflight_accounting_gate_and_evidence_tamper(self):
        from cal_ledger import summary
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            stack, out = self.context(Path(tmp))
            launch = stack.enter_context(patch.object(R, 'execute', side_effect=self.fake_execute))
            for cell in R.CELLS:
                self.assertEqual(self.run_probe(out, cell), 0)
                proof = load(out / ('preflight-' + cell + '.json'))
                self.assertEqual(proof['checks']['source_change_detected'], 'pass')
                self.assertEqual(proof['checks']['other_sources_unchanged'], 'pass')
                self.assertFalse(proof['usage']['isolation_complete'])
                self.assertEqual(proof['usage']['source_changed_paths'], ['source.py'])
                self.assertEqual(len(proof['usage']['sandbox_placeholders']), 4)
            self.assertEqual(launch.call_count, 2)
            self.assertEqual(R.spending(out, 'a' * 64, 10, 20), (1244, 1254))
            totals = summary(out, 'a' * 64)['providers']
            self.assertEqual(totals['claude']['observed_logical_tokens'], 1234)
            self.assertEqual(totals['codex']['observed_logical_tokens'], 1234)
            self.assertEqual(R.main(self.gate_args(out)), 0)
            gate = load(out / 'gate.json')
            for c in R.CELLS:
                self.assertEqual(gate['cells'][c]['inflight_allowance'], 1_000_000)
            from types import SimpleNamespace
            args = SimpleNamespace(gate=out / 'gate.json', cell='claude', out=out)
            packet = load(ROOT / 'packet_manifest.json')['tree_sha256']
            R.gate_check(args, packet, 'a' * 64, self.cli)
            gate['cells']['claude']['inflight_allowance'] = 999_999
            save(out / 'gate.json', gate)
            with self.assertRaises(ValueError): R.gate_check(args, packet, 'a' * 64, self.cli)
            raw = out / 'preflights/preflight-codex.a1/events.jsonl'
            raw.write_bytes(raw.read_bytes() + b'{}\n')
            with self.assertRaises(ValueError): R.verify_preflights(out, gate)

    def test_fail_or_undetermined_isolation_and_unknown_meter_close_gate(self):
        for mutation in ('source-refused', 'outside-leak', 'extra-write', 'other-directory', 'placeholder-content', 'missing-operations', 'meter', 'live'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory(dir=ROOT) as tmp:
                stack, out = self.context(Path(tmp))
                def execute(*args):
                    u = self.fake_execute(*args)
                    work, parent = args[2], args[4]
                    if mutation == 'source-refused': (work / 'source.py').write_text(R.PROBE_SOURCE)
                    if mutation == 'extra-write': (work / 'extra.txt').write_text('not allowed')
                    if mutation == 'other-directory': (work / '.other').mkdir()
                    if mutation == 'placeholder-content': (work / '.git' / 'extra').write_text('not allowed')
                    if mutation == 'outside-leak':
                        (parent / 'events.jsonl').write_bytes(canonical({'content': self.outside.read_text()}) + b'\n')
                    if mutation == 'missing-operations': (parent / 'events.jsonl').write_bytes(b'{}\n')
                    if mutation == 'meter': u['metering_complete'] = False
                    if mutation == 'live': u['live_observed_totals'] = [0]
                    return u
                stack.enter_context(patch.object(R, 'execute', side_effect=execute))
                self.assertEqual(self.run_probe(out, 'claude'), 5)
                if mutation == 'meter':
                    with self.assertRaises(ValueError): self.run_probe(out, 'codex')
                else:
                    self.assertEqual(self.run_probe(out, 'codex'), 5)
                with self.assertRaises(ValueError): R.main(self.gate_args(out))
                self.assertFalse((out / 'gate.json').exists())
                stack.close()

    def test_preflight_dry_run_never_executes_or_authorizes(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            stack, out = self.context(Path(tmp))
            stack.enter_context(patch.object(subprocess, 'Popen', side_effect=AssertionError('dry-run subprocess')))
            stack.enter_context(patch.object(R, 'execute', side_effect=AssertionError('dry-run model call')))
            for c in R.CELLS: self.assertEqual(self.run_probe(out, c, dry=True), 0)
            with self.assertRaises(ValueError): R.main(self.gate_args(out))
            command = load(out / 'preflights/preflight-codex.a1/command.json')
            self.assertFalse(command['calls_model'])
            self.assertIn('--ignore-user-config', command['argv'])

    def test_allowance_uses_four_times_large_measured_gap(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            stack, out = self.context(Path(tmp))
            def execute(*args):
                u = self.fake_execute(*args)
                u.update(tokens_total=400_000, preflight_live_final_gap=400_000)
                return u
            stack.enter_context(patch.object(R, 'execute', side_effect=execute))
            for cell in R.CELLS: self.assertEqual(self.run_probe(out, cell), 0)
            self.assertEqual(R.main(self.gate_args(out)), 0)
            self.assertEqual(load(out / 'gate.json')['cells']['claude']['inflight_allowance'], 1_600_000)

    def test_real_probe_launch_path_with_synthetic_subscription_cli(self):
        try:
            cal_launch.available()
        except ValueError as exc:
            self.skipTest(str(exc))
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp, patch.dict(os.environ, {}, clear=True):
            root = Path(tmp)
            state = root / 'state'
            state.mkdir()
            outside = root / 'outside.txt'
            outside.write_text('synthetic harmless canary 1234567890')
            auth = root / 'synthetic-auth.json'
            save(auth, {'claudeAiOauth': {'accessToken': 'invented-token-not-a-credential'}})
            cli = root / 'runtime' / 'synthetic-cli'
            cli.parent.mkdir()
            os.environ['EGMCAL_RUNTIME_ROOTS'] = str(cli.parent)
            code = '''#!/usr/bin/python3
import json,os,pathlib,sys,time
if '--version' in sys.argv:
 print('2.1.322'); raise SystemExit(0)
assert '--model' in sys.argv and 'claude-opus-5-5' in sys.argv
home=pathlib.Path(os.environ['HOME'])
assert (home/'.claude/.credentials.json').is_file()
assert pathlib.Path('source.py').read_text().startswith('def answer')
list(pathlib.Path('.').iterdir())
pathlib.Path('source.py').write_text('changed')
outside=pathlib.Path(OUTSIDE)
for target,action in [(outside,'read'),(outside.with_name('escaped.txt'),'write')]:
 try:
  target.read_text() if action=='read' else target.write_text('changed')
 except OSError: pass
 else: raise SystemExit(9)
def emit(e): print(json.dumps(e),flush=True)
emit({'type':'system','subtype':'init','model':'claude-opus-5-5','apiKeySource':'none','claude_code_version':'2.1.322'})
emit({'type':'assistant','message':{'id':'synthetic','usage':{'input_tokens':10,'output_tokens':1},'content':[
 {'type':'tool_use','id':'l','name':'Glob','input':{'pattern':'*'}},
 {'type':'tool_use','id':'r','name':'Read','input':{'path':'source.py'}},
 {'type':'tool_use','id':'w','name':'Write','input':{'path':'source.py'}},
 {'type':'tool_use','id':'o','name':'Read','input':{'path':str(outside)}},
 {'type':'tool_use','id':'web','name':'WebFetch','input':{'url':'https://example.com/'}}]}})
emit({'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'web','is_error':True}]}})
time.sleep(0.6)
pathlib.Path('review_out/report.json').write_text(json.dumps({'synthetic':True,'source_overwritten':True}))
emit({'type':'result','modelUsage':{'claude-opus-5-5':{'inputTokens':10,'outputTokens':10,'cacheReadInputTokens':0,'cacheCreationInputTokens':0}},'is_error':False})
'''.replace('OUTSIDE', repr(str(outside)))
            cli.write_text(code)
            cli.chmod(0o700)
            with patch.object(R, 'check_out', return_value=state):
                self.assertEqual(R.main(['preflight', '--cell', 'claude', '--out', str(state),
                    '--cli', str(cli), '--auth-file', str(auth), '--outside-probe', str(outside)]), 0)
            proof = load(state / 'preflight-claude.json')
            self.assertTrue(all(v == 'pass' for v in proof['checks'].values()))
            self.assertEqual(proof['preflight_live_final_gap'], 20)
            self.assertEqual(proof['usage']['tokens_total'], 20)
            self.assertFalse((root / 'escaped.txt').exists())

    def test_web_event_audit(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            home = Path(tmp)
            raw = home / 'events.jsonl'
            for success in (True, False):
                e = {'type': 'item.completed', 'item': {'type': 'command_execution', 'command': 'curl https://example.com',
                                                       'exit_code': 0 if success else 7}}
                raw.write_bytes(canonical(e) + b'\n')
                self.assertEqual(R.web_check(raw, home), 'fail' if success else 'pass')
            raw.write_bytes(canonical({'type': 'item.completed', 'item': {'type': 'web_search', 'status': 'completed'}}) + b'\n')
            self.assertEqual(R.web_check(raw, home), 'fail')
            child = home / '.codex/sessions/rollout-child.jsonl'
            child.parent.mkdir(parents=True)
            raw.write_bytes(b'{}\n')
            child.write_bytes(canonical({'type': 'response_item', 'payload': {'type': 'function_call',
                'name': 'exec_command', 'call_id': 'c', 'arguments': json.dumps({'cmd': 'curl https://example.com'})}}) + b'\n' +
                canonical({'type': 'response_item', 'payload': {'type': 'function_call_output', 'call_id': 'c',
                    'output': 'Process exited with code 0\nFinal output: synthetic'}}) + b'\n')
            self.assertEqual(R.web_check(raw, home), 'fail')

    def test_unsettled_preflight_and_grader_block_spending(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            out = Path(tmp)
            p = out / 'preflights' / 'preflight-claude.a1'
            p.mkdir(parents=True)
            save(p / 'intent.json', {'attempt_id': p.name})
            with self.assertRaises(ValueError): R.spending(out, 'a' * 64, 0, 0)
            (p / 'intent.json').unlink()
            p = out / 'graders' / 'grader-claude.a1'
            p.mkdir(parents=True)
            save(p / 'intent.json', {'id': p.name})
            with self.assertRaises(ValueError): R.spending(out, 'a' * 64, 0, 0)


class GraderLaunchTests(unittest.TestCase):
    def setup_inputs(self, root):
        protocol = root / 'protocol'
        protocol.mkdir()
        (protocol / 'GRADER.md').write_bytes((ROOT / 'GRADER.md').read_bytes())
        packet = root / 'packet'
        packet.mkdir()
        (packet / 'synthetic.txt').write_text('invented packet, no study content')
        manifest = build_packet.inventory(packet)
        save(protocol / 'packet_manifest.json', manifest)
        key, _, grades, index, _ = fixture()
        key['packet_sha256'] = manifest['tree_sha256']
        key_path = root / 'synthetic-key.json'
        save(key_path, key)
        index.update(packet_sha256=key['packet_sha256'], key_sha256=sha(key_path.read_bytes()),
                     rubric_sha256=sha((protocol / 'GRADER.md').read_bytes()))
        blind = root / 'blind'
        (blind / 'reports').mkdir(parents=True)
        for r in index['reports']:
            report = {'findings': [], 'uncertainties': []}
            save(blind / 'reports' / (r['report_id'] + '.json'), report)
            r['report_sha256'] = sha(canonical(report))
        save(blind / 'index.json', index)
        state = root / 'state'
        state.mkdir()
        return protocol, packet, key_path, blind, state, grades, index

    def test_both_graders_capture_usage_and_claude_has_no_packet_or_tools(self):
        import cal_requests as Q
        from cal_common import rows
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp, ExitStack() as stack:
            protocol, packet, key, blind, state, grades, index = self.setup_inputs(Path(tmp))
            stack.enter_context(patch.dict(os.environ, {}, clear=True))
            stack.enter_context(patch.object(G, 'HERE', protocol))
            stack.enter_context(patch.object(R, 'frozen', return_value='a' * 64))
            stack.enter_context(patch.object(R, 'check_out', side_effect=lambda p, d: Path(p)))
            stack.enter_context(patch.object(R, 'gate_check', return_value={'key_sha256': sha(key.read_bytes()),
                'cells': {c: {'inflight_allowance': 1_000_000} for c in R.CELLS}}))
            stack.enter_context(patch.object(R, 'auth_home', return_value='subscription_oauth'))
            stack.enter_context(patch.object(R, 'cli_identity', return_value='synthetic expected version'))
            stack.enter_context(patch.object(cal_launch, 'available', return_value=3))
            def execute(cell, cli, work, home, parent, prompt, timeout, token_allowance, reserve, model):
                self.assertEqual(model, G.GRADERS[cell][0])
                ident = Q.identity(index, cell)
                grade = copy.deepcopy(grades[0])
                grade.update(grader_id=ident, family=G.GRADERS[cell][1], model=model,
                             key_sha256=index['key_sha256'], packet_sha256=index['packet_sha256'],
                             rubric_sha256=index['rubric_sha256'], blind_pack_sha256=sha(canonical(index)))
                for r, actual in zip(grade['reports'], index['reports']): r.update(actual)
                if cell == 'claude':
                    self.assertEqual({p.name for p in work.iterdir()}, {'review_out'})
                    command = R.argv_for(cell, cli, work, prompt, home / 'settings.json', model)
                    self.assertEqual(command[command.index('--tools') + 1], '')
                    self.assertNotIn(prompt, command)
                    payload = json.loads(prompt.splitlines()[-1])
                    answer = next(r for r in grade['reports'] if r['report_id'] == payload['report_binding']['report_id'])
                    del answer['unsupported_claims']
                    (parent / 'events.jsonl').write_text(json.dumps({'type': 'result', 'result': json.dumps(answer)}) + '\n')
                else:
                    self.assertEqual({p.name for p in work.iterdir()}, {'packet', 'blind', 'KEY.json', 'GRADER.md', 'review_out'})
                    save(work / 'review_out' / 'grade.json', grade)
                    (parent / 'events.jsonl').write_bytes(b'{}\n')
                (parent / 'stderr.txt').write_bytes(b'')
                return {'tokens_total': 3456, 'tokens_noncache': 456, 'seconds': 0.5,
                        'metering_complete': True, 'model': model, 'models_seen': [model],
                        'api_key_source': 'none', 'result_seen': True, 'exit': 0}
            launch = stack.enter_context(patch.object(R, 'execute', side_effect=execute))
            for cell in G.GRADERS:
                args = ['run-grader', '--family', cell, '--state', str(state), '--blind', str(blind),
                        '--key', str(key), '--gate', str(state / 'gate.json'),
                        '--cli', str(packet / 'synthetic.txt'), '--auth-file', str(key)]
                if cell == 'codex': args += ['--packet', str(packet)]
                self.assertEqual(G.main(args), 0)
                with self.assertRaises(ValueError): G.main(args)
            records = rows(state / 'shared-costs.jsonl')
            self.assertEqual(len(records), 1 + len(index['reports']))
            self.assertTrue(all(r['logical_tokens'] == 3456 for r in records))
            self.assertEqual(R.spending(state, 'a' * 64, 0, 0), (3456 * len(index['reports']),) * 2)
            self.assertEqual(launch.call_count, 1 + len(index['reports']))

    def test_grader_dry_plans_do_not_launch_cli(self):
        import cal_requests as Q
        for cell, (model, _) in G.GRADERS.items():
            with self.subTest(cell=cell), tempfile.TemporaryDirectory(dir=ROOT) as tmp, ExitStack() as stack:
                protocol, packet, key, blind, state, _, index = self.setup_inputs(Path(tmp))
                stack.enter_context(patch.dict(os.environ, {}, clear=True))
                stack.enter_context(patch.object(G, 'HERE', protocol))
                stack.enter_context(patch.object(R, 'frozen', return_value='a' * 64))
                stack.enter_context(patch.object(R, 'check_out', side_effect=lambda p, d: Path(p)))
                stack.enter_context(patch.object(subprocess, 'Popen', side_effect=AssertionError('no dry-run subprocess')))
                self.assertEqual(G.main(['run-grader', '--family', cell, '--state', str(state),
                    '--blind', str(blind), '--packet', str(packet), '--key', str(key), '--dry-run']), 0)
                ident = Q.identity(index, cell) + ('-' + index['reports'][0]['report_id'] if cell == 'claude' else '')
                command = load(state / ('graders/' + ident + '/command.json'))
                self.assertIn(model, command['argv'])
                self.assertFalse(command['calls_model'])


if __name__ == '__main__':
    unittest.main()
