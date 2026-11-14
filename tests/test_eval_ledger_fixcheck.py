"""Synthetic legacy-ledger acceptance fixtures, never real task answers."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import eval_ledger_fixcheck as adapter


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()


def write(path, value):
    path.write_text(json.dumps(value), encoding='utf-8')


def rows(path, values):
    path.write_text(''.join(json.dumps(v) + '\n' for v in values), encoding='utf-8')


def fixture(root):
    state, frozen = root/'state', root/'frozen'
    state.mkdir(); frozen.mkdir()
    budget = {'cap': 17000000, 'decision': 'D45', 'spent_before': 0}
    write(state/'budget.json', budget)
    unitlist, banks = [], {}
    for klass in 'ABC':
        uid = 'task-' + klass
        fn = 'test_recall_value' if klass == 'B' else 'test_correct'
        original = {'id': uid, 'candidate_sha256': digest((uid+'candidate').encode())}
        write(state/f'units_{klass}.json', {'units': [original]})
        banks[klass] = digest((state/f'units_{klass}.json').read_bytes())
        unitlist.append({'id': uid, 'klass': klass, 'sha256': digest(json.dumps(original, sort_keys=True, ensure_ascii=False).encode()),
                         'sessions': 2 if klass == 'B' else 1, 'functions': [fn], 'items': {'ok': [fn]}})
    source_files = {}
    for name in ('FIXCHECK.md', 'fixcheck.py', 'thresholds.py', 'test_fixcheck.py'):
        (frozen/name).write_text('Frozen synthetic fixture, not executed\n')
        source_files[name] = digest((frozen/name).read_bytes())
    write(frozen/'BASELINES.json', {'fixture': True})
    rt = {'arms': {'O': {'commit': '1'*40, 'content_sha256': '2'*64}}, 'oaw_commit': '3'*40,
          'budget': budget, 'files': {'h1_run.py': '4'*64, 'h1_judge.py': '5'*64}, 'units': banks,
          'base_commit': '6'*40, 'tools': [], 'system_tools': {},
          'launch': {'cells': {c: {'model': 'fixture-'+c, 'cli_version': 'fixture-1',
              'argv': ['--effort', 'high'] if c == 'claude' else ['-c', 'model_reasoning_effort="high"']} for c in ('codex','claude')}}}
    manifest = {'schema': 1, 'experiment': 'synthetic-fixcheck', 'candidate_commit': '3'*40,
                'method': {'tag': 'fixcheck', 'arms': ['O'], 'cells': ['codex','claude']},
                'runtime': rt, 'units': unitlist, 'files': source_files,
                'baseline_sha256': digest((frozen/'BASELINES.json').read_bytes())}
    mp = frozen/'MANIFEST.json'
    write(mp, manifest)
    write(state/'BINDING.json', {'manifest_sha256': digest(mp.read_bytes())})

    def start(cell, klass, attempt=1):
        unit = next(u for u in unitlist if u['klass'] == klass)
        return {'event': 'start', 'cell': cell, 'unit': unit['id'], 'attempt': attempt,
                'tag': 'fixcheck', 'arm': 'O', 'klass': klass, 'freeze_sha256': '',
                'root': f"runs/fixcheck/{cell}/{unit['id']}/O/a{attempt}",
                'runner_sha256': rt['files']['h1_run.py'], 'units_sha256': banks[klass],
                'unit_sha256': unit['sha256'], 'candidate_sha256': digest((unit['id']+'candidate').encode())}

    def answer(cell, klass, values, not_run=None):
        record = start(cell, klass)
        del record['event']
        unit = next(u for u in unitlist if u['klass'] == klass)
        record.update(model_asked=rt['launch']['cells'][cell]['model'], arm_commit='1'*40,
                      cap=17000000 if cell=='claude' else None, cap_decision='D45' if cell=='claude' else None,
                      sessions=[{'tokens_total': v, 'tokens_noncache': 0, 'seconds': None} for v in values],
                      tokens_total=sum(values), tokens_noncache=0, seconds=None)
        if not_run: record['not_run'] = not_run
        else:
            record['grade'] = {'error': '', 'suite_regression': False, 'functions': dict.fromkeys(unit['functions'], True),
                               'items': {'ok': True}, 'n': 1, 'passed': 1, 'recall': True if klass=='B' else None}
            record['score'] = 1.0
        return record

    codex = [answer('codex','A',[1000]), answer('codex','B',[165952,262326])]
    codex[1]['recovery'] = {'method': 'same preserved answer', 'input_index_sha256': '7'*64}
    claude = [answer('claude','A',[0], 's1: usage limit')]
    rows(state/'starts-fixcheck-codex.jsonl', [start('codex','A'),start('codex','B')])
    rows(state/'attempts-fixcheck-codex.jsonl', codex)
    rows(state/'rows-fixcheck-codex.jsonl', codex)
    rows(state/'starts-fixcheck-claude.jsonl', [start('claude','A')])
    rows(state/'attempts-fixcheck-claude.jsonl', claude)
    key = claude[0]['root']+'/raw/s1.jsonl'
    meter = [{'event': 'start', 'key': key, 'raw': key, 'reserve': 450000}, {'event':'end','key':key,'tokens':0}]
    rows(state/'ledger-claude.jsonl', meter)
    return mp, state, start


class FixcheckAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='oaw-ledger-import-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest, self.state, self.start = fixture(self.root)

    def report(self):
        return adapter.report_fixcheck(self.manifest, self.state)

    def values(self, name):
        return [json.loads(s) for s in (self.state/name).read_text().splitlines()]

    def test_read_only_preserves_recovered_usage_and_missing_denominator(self):
        before = {str(p.relative_to(self.root)): digest(p.read_bytes()) for p in self.root.rglob('*') if p.is_file()}
        result = self.report()
        after = {str(p.relative_to(self.root)): digest(p.read_bytes()) for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(result['coverage']['planned'], 6)
        self.assertEqual(result['coverage']['scored'], 2)
        self.assertEqual(result['coverage']['not_run_attempts'], 1)
        self.assertEqual(result['whole_study']['logical_tokens']['observed'], 429278)
        self.assertIsNone(result['whole_study']['logical_tokens']['total'])
        recovery = result['adapter']['recovered_attempts'][0]
        self.assertEqual(recovery['logical_tokens'], 428278)
        self.assertNotEqual(recovery['logical_tokens'], 397636)
        self.assertIsNone(recovery['elapsed_seconds'])
        self.assertEqual(result['adapter']['claude_meter_observed_tokens'], 0)
        self.assertNotIn(str(self.root), json.dumps(result))
        self.assertNotIn('runs/fixcheck', json.dumps(result))
        self.assertEqual(result, self.report())

    def test_unfinished_meter_reserve_is_not_spending(self):
        starts = self.values('starts-fixcheck-claude.jsonl')
        pending = self.start('claude','B');starts.append(pending)
        rows(self.state/'starts-fixcheck-claude.jsonl', starts)
        meter = self.values('ledger-claude.jsonl')
        key = pending['root']+'/raw/s1.jsonl'
        meter.append({'event':'start','key':key,'raw':key,'reserve':450000})
        rows(self.state/'ledger-claude.jsonl', meter)
        result = self.report()
        self.assertEqual(result['adapter']['claude_outstanding_reserve'], 450000)
        self.assertEqual(result['whole_study']['logical_tokens']['observed'], 429278)
        self.assertEqual(result['coverage']['interrupted_attempts'], 1)
        meter.append({'event':'end','key':key,'tokens':1234})
        rows(self.state/'ledger-claude.jsonl', meter)
        result = self.report()
        self.assertEqual(result['adapter']['claude_outstanding_reserve'], 0)
        self.assertEqual(result['whole_study']['logical_tokens']['observed'], 430512)
        self.assertEqual(result['coverage']['scored'], 2)

    def test_duplicate_counted_or_attempt_rows_are_refused(self):
        for name in ('rows-fixcheck-codex.jsonl','attempts-fixcheck-codex.jsonl'):
            original = (self.state/name).read_bytes()
            data = self.values(name)
            rows(self.state/name, data+[data[0]])
            with self.subTest(name=name), self.assertRaises(ValueError): self.report()
            (self.state/name).write_bytes(original)

    def test_missing_counted_row_requires_recovery_not_silent_skip(self):
        rows(self.state/'rows-fixcheck-codex.jsonl', self.values('rows-fixcheck-codex.jsonl')[:1])
        with self.assertRaisesRegex(ValueError, 'not reconciled'): self.report()

    def test_meter_mismatch_and_duplicate_end_refused(self):
        meter = self.values('ledger-claude.jsonl')
        rows(self.state/'ledger-claude.jsonl', meter+[meter[-1]])
        with self.assertRaisesRegex(ValueError, 'Duplicate/orphan'): self.report()
        meter[-1]['tokens'] = 10
        rows(self.state/'ledger-claude.jsonl', meter)
        with self.assertRaisesRegex(ValueError, 'tokens differ'): self.report()

    def test_source_manifest_binding_and_budget_tampering_refused(self):
        for path, mutate in ((self.state/'BINDING.json', lambda d:d.update(manifest_sha256='f'*64)),
                             (self.state/'budget.json',lambda d:d.update(cap=17000001))):
            saved=path.read_bytes();data=json.loads(saved);mutate(data);write(path,data)
            with self.subTest(path=path.name), self.assertRaises(ValueError): self.report()
            path.write_bytes(saved)
        (self.manifest.parent/'thresholds.py').write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'Frozen FIXCHECK source'): self.report()

    def test_manifest_and_rows_cannot_contradict_actual_unit_bank(self):
        manifest = json.loads(self.manifest.read_text())
        manifest['units'][0]['sha256'] = 'f'*64
        write(self.manifest, manifest)
        write(self.state/'BINDING.json', {'manifest_sha256': digest(self.manifest.read_bytes())})
        for cell in ('codex', 'claude'):
            for kind in ('starts', 'attempts', 'rows'):
                name = f'{kind}-fixcheck-{cell}.jsonl'
                if not (self.state/name).exists():
                    continue
                values = self.values(name)
                for row in values:
                    if row['unit'] == 'task-A':
                        row['unit_sha256'] = 'f'*64
                rows(self.state/name, values)
        with self.assertRaisesRegex(ValueError, 'per-unit hash'):
            self.report()

    def test_session_totals_and_hidden_item_mapping_refused(self):
        for mutation in ('sessions','grade','identity','zero'):
            attempts = self.values('attempts-fixcheck-codex.jsonl')
            saved = copy.deepcopy(attempts)
            if mutation == 'sessions': attempts[0]['sessions'][0]['tokens_total'] = 999
            elif mutation == 'grade': attempts[0]['grade']['functions']['test_correct'] = False
            elif mutation == 'identity': attempts[0]['unit_sha256'] = 'f'*64
            else:
                attempts[0]['tokens_total']=0;attempts[0]['sessions'][0]['tokens_total']=0
            rows(self.state/'attempts-fixcheck-codex.jsonl', attempts)
            rows(self.state/'rows-fixcheck-codex.jsonl', attempts)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): self.report()
            rows(self.state/'attempts-fixcheck-codex.jsonl', saved)
            rows(self.state/'rows-fixcheck-codex.jsonl', saved)

    def test_truncated_json_is_invalid_not_a_cheaper_run(self):
        path=self.state/'attempts-fixcheck-codex.jsonl'
        path.write_bytes(path.read_bytes()+b'{"tokens_total": 1')
        with self.assertRaises(ValueError): self.report()


if __name__ == '__main__':
    unittest.main()
