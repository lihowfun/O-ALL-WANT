"""Behavioral fixtures only: these numbers are not model measurements."""
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import eval_ledger as ledger
import eval_ledger_fixcheck as adapter
import eval_stats

STAGES = ('answer', 'proposal', 'probe', 'compose', 'selection', 'reflection', 'retry', 'grading')
STUDY = ('authoring', 'review', 'controller')
METRICS = ('logical_tokens', 'noncache_tokens', 'cost_usd', 'elapsed_seconds')
ROOT = Path(__file__).resolve().parents[1]


def h(data):
    return hashlib.sha256(data).hexdigest()


def canon(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def bind(bundle):
    value = h(canon(bundle['manifest']))
    bundle['manifest_sha256'] = value
    for item in bundle['records'] + bundle['outcomes']:
        item['manifest_sha256'] = value


def fixture(root):
    sources = {}
    def source(sid, data):
        path = root / (sid + '.txt')
        path.write_bytes(data)
        sources[sid] = {'path': path.name, 'sha256': h(data)}
        return h(data)
    source('meter', b'Synthetic independent meter fixture, not measured model work')
    judge = source('judge', b'Synthetic grader version 1')
    contract = {'metric_id': 'correct-fraction', 'metric_sha256': h(b'fixture scale 0..1'),
                'judge_sha256': judge, 'source_kind': 'mechanical'}
    manifest = {'schema_version': 1, 'study_id': 'synthetic', 'protocol_sha256': h(b'fixture protocol'),
                'analysis_unit': 'independent_task', 'grading_contract': contract, 'runs': []}
    records, outcomes = [], []
    for task in ('a', 'b'):
        for arm in ('base', 'candidate'):
            rid = task + '-' + arm
            manifest['runs'].append({'id': rid, 'task_id': task, 'arm': arm,
                'input_sha256': h(task.encode()), 'harness_sha256': h(arm.encode()), 'repeat': 1, 'split': 'test',
                'condition': {'id': 'c', 'model': 'fixture-model', 'effort': 'high', 'host': 'fixture-host',
                              'host_version': '1', 'environment_sha256': h(b'fixture environment')}})
            output = source(rid, ('fixture output ' + rid).encode())
            for stage in STAGES:
                active = stage in ('answer', 'grading')
                tokens = (100 if arm == 'base' else 50) if stage == 'answer' else 5 if stage == 'grading' else 0
                records.append({'id': rid + '-' + stage, 'run_id': rid, 'stage': stage, 'attempt': 1,
                    'status': 'completed' if active else 'not_applicable', 'reason': '' if active else 'Not part of fixture protocol',
                    'sources': ['meter', rid, 'judge'], 'meter': 'independent', 'complete': True, 'subagents_included': True,
                    'charge_ids': [rid + '-' + stage] if active else [],
                    'metrics': {'logical_tokens': tokens, 'noncache_tokens': tokens, 'cost_usd': tokens / 1000,
                                'elapsed_seconds': tokens / 10},
                    'produces': output if stage == 'answer' else None, 'selects': None,
                    'judges': output if stage == 'grading' else None})
            outcomes.append({'run_id': rid, 'status': 'scored', 'output_sha256': output,
                             'sources': [rid, 'judge'], 'score': 0.5 if arm == 'base' else 1.0,
                             'judge_sha256': judge, 'grading_contract': copy.deepcopy(contract)})
    for stage in STUDY:
        records.append({'id': 'study-' + stage, 'run_id': None, 'stage': stage, 'attempt': 1,
                        'status': 'not_applicable', 'reason': 'Synthetic fixture only', 'sources': ['meter'],
                        'meter': 'independent', 'complete': True, 'subagents_included': True,
                        'charge_ids': [], 'metrics': dict.fromkeys(METRICS, 0), 'produces': None, 'selects': None})
    bundle = {'manifest': manifest, 'sources': sources, 'records': records, 'outcomes': outcomes}
    bind(bundle)
    return bundle


def write_bundle(root, bundle):
    path = root / 'bundle.json'
    path.write_text(json.dumps(bundle), encoding='utf-8')
    return path


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='oaw-ledger-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = fixture(self.root)

    def compare(self, bundle=None, **kwargs):
        return ledger.compare(bundle or self.bundle, 'base', 'candidate', 'c', 0.1, floor_sd=0.05, **kwargs)

    def test_scored_not_applicable_grading_is_invalid_and_no_completed_grade_is_incomplete(self):
        for status in ('not_applicable', 'failed', 'unmeasured'):
            bundle = copy.deepcopy(self.bundle)
            for r in bundle['records']:
                if r['stage'] == 'grading':
                    r.update(status=status, reason='Synthetic contradiction', charge_ids=[], judges=None)
                    r['metrics'] = dict.fromkeys(METRICS, 0)
            path = write_bundle(self.root, bundle)
            process = subprocess.run([sys.executable, str(ROOT/'scripts/eval_ledger.py'), 'report', str(path)],
                                     text=True, capture_output=True)
            self.assertEqual(process.stderr, '')
            result = json.loads(process.stdout)
            if status == 'not_applicable':
                self.assertEqual(process.returncode, 1)
                self.assertEqual(result['status'], 'invalid')
                with self.assertRaisesRegex(ValueError, 'not-applicable grading'):
                    ledger.summarize(bundle)
            else:
                self.assertEqual(process.returncode, 2)
                self.assertEqual(result['status'], 'incomplete')
                self.assertTrue(all(not r['grading_evidence_complete'] for r in result['runs']))
                self.assertTrue(all('No complete grading evidence' in r['reasons'] for r in result['runs']))

    def test_huge_numbers_are_invalid_without_overflow(self):
        self.bundle['records'][0]['metrics']['logical_tokens'] = 10**400
        with self.assertRaisesRegex(ValueError, 'Non-finite'):
            ledger.summarize(self.bundle)

    def test_malformed_cli_input_has_no_traceback_or_path(self):
        path = self.root / 'bundle.json'
        for value in ([], {'sources': []}, {'sources': {'s': None}}):
            path.write_text(json.dumps(value))
            process = subprocess.run([sys.executable, str(ROOT/'scripts/eval_ledger.py'), 'report', str(path)],
                                     text=True, capture_output=True)
            self.assertEqual(process.returncode, 1)
            self.assertEqual(json.loads(process.stdout)['status'], 'invalid')
            self.assertEqual(process.stderr, '')
            self.assertNotIn(str(self.root), process.stdout)

    def test_complete_report_keeps_cost_scopes_and_delegates_exact_statistics(self):
        result = self.compare()
        self.assertEqual(result['coverage'], {'planned': 4, 'started': 4, 'completed': 4, 'scored': 4,
                          'missing_outcomes': 0, 'not_run_attempts': 0, 'interrupted_attempts': 0})
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['scopes']['execution']['logical_tokens']['total'], 300)
        self.assertEqual(result['scopes']['grading']['logical_tokens']['total'], 20)
        self.assertEqual(result['whole_study']['logical_tokens']['total'], 320)
        self.assertEqual(result['comparison']['quality'], eval_stats.compare({'a': [1.0], 'b': [1.0]},
                         {'a': [0.5], 'b': [0.5]}, 0.1, floor_sd=0.05))
        self.assertEqual(result['comparison']['cost'], eval_stats.cost({'a': [50], 'b': [50]}, {'a': [100], 'b': [100]}))
        self.assertIsNone(result['benefit_verdict'])
        self.assertIsNone(result['comparison']['cross_family_quality_verdict'])
        self.assertEqual(set(result['stages']), set(STAGES + STUDY))

    def test_missing_answer_stays_in_denominator_and_is_not_zero(self):
        self.bundle['records'] = [r for r in self.bundle['records'] if r['run_id'] != 'a-candidate']
        self.bundle['outcomes'] = [o for o in self.bundle['outcomes'] if o['run_id'] != 'a-candidate']
        result = ledger.summarize(self.bundle)
        self.assertEqual(result['coverage']['planned'], 4)
        self.assertEqual(result['coverage']['completed'], 3)
        self.assertIsNone(result['whole_study']['logical_tokens']['total'])
        self.assertEqual(next(r for r in result['runs'] if r['id'] == 'a-candidate')['score'], None)
        with self.assertRaisesRegex(ValueError, 'Missing/unscored'):
            self.compare()

    def test_unscored_and_scored_zero_are_distinct(self):
        self.bundle['outcomes'][0]['score'] = 0
        self.assertEqual(ledger.summarize(self.bundle)['coverage']['scored'], 4)
        self.bundle['outcomes'][0].update(status='completed', score=None, reason='Judge quota')
        self.assertEqual(ledger.summarize(self.bundle)['coverage']['scored'], 3)
        with self.assertRaisesRegex(ValueError, 'Missing/unscored'):
            self.compare()
        self.bundle['outcomes'][0]['score'] = 0
        with self.assertRaisesRegex(ValueError, 'Unscored is not zero'):
            ledger.summarize(self.bundle)

    def test_failed_attempt_spending_is_counted(self):
        extra = copy.deepcopy(self.bundle['records'][0])
        extra.update(id='failed-first', attempt=2, status='failed', reason='Tool failure', produces=None,
                     charge_ids=['failed-first'])
        extra['metrics']['logical_tokens'] = extra['metrics']['noncache_tokens'] = 70
        self.bundle['records'].append(extra)
        result = ledger.summarize(self.bundle)
        self.assertEqual(result['scopes']['execution']['logical_tokens']['total'], 370)
        self.assertEqual(result['coverage']['completed'], 4)

    def test_unknown_overhead_does_not_become_free_or_change_arm_costs(self):
        r = next(r for r in self.bundle['records'] if r['stage'] == 'controller')
        r.update(status='unmeasured', reason='Engineering usage not metered', complete=False)
        r['metrics'] = dict.fromkeys(METRICS)
        result = self.compare()
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['whole_study']['logical_tokens']['observed'], 320)
        self.assertIsNone(result['whole_study']['logical_tokens']['total'])
        self.assertEqual(result['comparison']['cost']['ratio'], 0.5)
        self.assertIn('excluding grading/shared', result['comparison']['scope'])

    def test_incomplete_or_self_reported_usage_refuses_comparison(self):
        for field, value in (('complete', False), ('subagents_included', False), ('meter', 'self_report')):
            b = copy.deepcopy(self.bundle)
            b['records'][0][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'Incomplete execution'):
                self.compare(b)
        self.bundle['records'][0]['metrics']['noncache_tokens'] = None
        r = ledger.summarize(self.bundle)
        self.assertEqual(r['whole_study']['logical_tokens']['total'], 320)
        self.assertIsNone(r['whole_study']['noncache_tokens']['total'])

    def test_duplicate_ids_attempts_and_parent_child_charges_are_rejected(self):
        for mutation in ('id', 'attempt', 'charge'):
            b = copy.deepcopy(self.bundle)
            extra = copy.deepcopy(b['records'][0])
            extra.update(id='new', attempt=2, charge_ids=['new'], produces=None)
            if mutation == 'id': extra['id'] = b['records'][0]['id']
            if mutation == 'attempt': extra['attempt'] = 1
            if mutation == 'charge': extra['charge_ids'] = b['records'][0]['charge_ids']
            b['records'].append(extra)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                ledger.summarize(b)
        b = copy.deepcopy(self.bundle)
        b['records'][0]['charge_ids'].append('child-session')
        b['records'][7]['charge_ids'].append('child-session')
        with self.assertRaisesRegex(ValueError, 'Overlapping billed'):
            ledger.summarize(b)

    def test_manifest_binding_and_conflicting_plan_are_rejected(self):
        self.bundle['manifest']['runs'][0]['harness_sha256'] = h(b'changed')
        with self.assertRaises(ValueError): ledger.summarize(self.bundle)
        b = fixture(self.root)
        b['manifest']['runs'][1]['input_sha256'] = h(b'wrong task')
        bind(b)
        with self.assertRaisesRegex(ValueError, 'Conflicting planned'):
            ledger.summarize(b)
        b = fixture(self.root)
        b['records'][0]['manifest_sha256'] = h(b'other manifest')
        with self.assertRaisesRegex(ValueError, 'Record manifest'):
            ledger.summarize(b)

    def test_source_tampering_and_snapshot_race_are_rejected(self):
        path = write_bundle(self.root, self.bundle)
        _, snapshot = ledger.load_bundle(path)
        (self.root / 'meter.txt').write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'Input changed'):
            snapshot.verify()
        with self.assertRaisesRegex(ValueError, 'source hash differs'):
            ledger.load_bundle(path)
        snap = ledger.Snapshot()
        absent = self.root / 'absent.json'
        self.assertIsNone(snap.read(absent, optional=True))
        absent.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Input appeared'):
            snap.verify()

    def test_evidence_path_confinement(self):
        for value in ('../outside', '/absolute', 'C:\\outside'):
            b = copy.deepcopy(self.bundle)
            b['sources']['meter']['path'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                ledger.load_bundle(write_bundle(self.root, b))
        if hasattr(os, 'symlink'):
            with tempfile.TemporaryDirectory() as other:
                outside = Path(other) / 'data'
                outside.write_bytes(b'x')
                try: (self.root / 'escape').symlink_to(outside)
                except OSError: return  # Windows host may not grant symlink creation.
                b = copy.deepcopy(self.bundle)
                b['sources']['meter'].update(path='escape', sha256=h(b'x'))
                with self.assertRaisesRegex(ValueError, 'symlink escapes'):
                    ledger.load_bundle(write_bundle(self.root, b))

    def test_selection_and_grade_must_bind_delivered_artifact(self):
        b = copy.deepcopy(self.bundle)
        select = next(r for r in b['records'] if r['id'] == 'a-base-selection')
        select.update(status='completed', reason='', selects=b['outcomes'][0]['output_sha256'])
        ledger.summarize(b)
        select['selects'] = b['outcomes'][1]['output_sha256']
        with self.assertRaisesRegex(ValueError, 'outside same run'):
            ledger.summarize(b)
        select['selects'] = None
        with self.assertRaisesRegex(ValueError, 'identify its choice'):
            ledger.summarize(b)
        b = copy.deepcopy(self.bundle)
        b['records'][7]['judges'] = b['outcomes'][1]['output_sha256']
        with self.assertRaisesRegex(ValueError, 'Grade refers to another'):
            ledger.summarize(b)

    def test_comparison_rejects_mixed_missing_and_self_grading_contracts(self):
        for field, value in (('judge_sha256', h(b'other judge')), ('metric_sha256', h(b'other scale')),
                             ('metric_id', 'other-score'), ('source_kind', 'self_report')):
            b = copy.deepcopy(self.bundle)
            b['outcomes'][0]['grading_contract'][field] = value
            if field == 'judge_sha256': b['outcomes'][0]['judge_sha256'] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'Mixed metric'):
                self.compare(b)
        for value in (None, {**self.bundle['manifest']['grading_contract'], 'source_kind': 'self_report'}):
            b = copy.deepcopy(self.bundle)
            b['manifest']['grading_contract'] = value
            bind(b)
            with self.assertRaises(ValueError): self.compare(b)

    def test_unmatched_repeats_pilot_stream_and_missing_floor_refused(self):
        b = copy.deepcopy(self.bundle)
        b['manifest']['runs'][1]['repeat'] = 2
        bind(b)
        with self.assertRaisesRegex(ValueError, 'Unmatched'):
            self.compare(b)
        for field, value in (('analysis_unit', 'stream'), ('analysis_unit', 'diagnostic')):
            b = copy.deepcopy(self.bundle)
            b['manifest'][field] = value
            bind(b)
            with self.assertRaisesRegex(ValueError, 'independent_task'):
                self.compare(b)
        b = copy.deepcopy(self.bundle)
        for run in b['manifest']['runs']: run['split'] = 'pilot'
        bind(b)
        with self.assertRaisesRegex(ValueError, 'planned test'):
            self.compare(b)
        with self.assertRaisesRegex(ValueError, 'floor_sd'):
            ledger.compare(self.bundle, 'base', 'candidate', 'c', 0.1)

    def test_invalid_numbers_boolean_tokens_and_zero_answer_rejected(self):
        for value in (-1, True, 1.5, float('nan'), float('inf'), 0):
            b = copy.deepcopy(self.bundle)
            b['records'][0]['metrics']['logical_tokens'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                ledger.summarize(b)
        self.bundle['records'][0]['metrics']['cost_usd'] = None
        self.assertIsNone(ledger.summarize(self.bundle)['whole_study']['cost_usd']['total'])

    def test_strict_json_rejects_duplicates_and_nonfinite(self):
        for raw in ('{"a":1,"a":2}', '{"x":NaN}', '{"x":Infinity}'):
            with self.assertRaises(ValueError): ledger.parse(raw)

    def test_cli_json_markdown_exit_codes_and_no_paths_or_source_contents(self):
        path = write_bundle(self.root, self.bundle)
        def run(*args):
            return subprocess.run([sys.executable, str(ROOT/'scripts/eval_ledger.py'), *args],
                                  text=True, capture_output=True, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        result = run('report', str(path))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['whole_study']['logical_tokens']['total'], 320)
        result = run('report', str(path), '--format', 'markdown')
        self.assertEqual(result.returncode, 0)
        self.assertIn('Planned 4;', result.stdout)
        self.assertNotIn(str(self.root), result.stdout)
        self.assertNotIn('Synthetic independent meter fixture', result.stdout)
        self.bundle['records'] = [r for r in self.bundle['records'] if r['stage'] != 'controller']
        write_bundle(self.root, self.bundle)
        result = run('report', str(path))
        self.assertEqual(result.returncode, 2)
        self.assertIsNone(json.loads(result.stdout)['whole_study']['logical_tokens']['total'])
        path.write_text('{"x":NaN}')
        self.assertEqual(run('report', str(path)).returncode, 1)

    def test_repeated_snapshot_reports_are_deterministic(self):
        path = write_bundle(self.root, self.bundle)
        one, _ = ledger.load_bundle(path)
        two, _ = ledger.load_bundle(path)
        self.assertEqual(canon(ledger.summarize(one)), canon(ledger.summarize(two)))


if __name__ == '__main__':
    unittest.main()
