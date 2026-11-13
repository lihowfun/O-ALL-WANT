#!/usr/bin/env python3
"""Read-only, evidence-bound evaluation accounting. Never runs or grades a task."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

import eval_stats

RUN_STAGES = ('answer', 'proposal', 'probe', 'compose', 'selection', 'reflection', 'retry', 'grading')
STUDY_STAGES = ('authoring', 'review', 'controller')
METRICS = ('logical_tokens', 'noncache_tokens', 'cost_usd', 'elapsed_seconds')
STATUSES = ('completed', 'failed', 'interrupted', 'not_run', 'unmeasured', 'not_applicable')
METERS = ('host', 'independent', 'runner', 'self_report')
GRADERS = ('mechanical', 'independent_model', 'self_report', 'unknown')
IDENT = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z')
HEX = re.compile(r'[0-9a-f]{64}\Z')
LIMITATION = ('Verified bytes and declared coverage do not authenticate meter/grader independence or prove '
              'that no work was omitted. Observed subtotals are not complete study costs. '
              'Summed elapsed_seconds are stage durations, not experiment wall-clock time.')


class LedgerError(ValueError):
    """Invalid or incompatible evaluation evidence."""


def require(ok, message):
    if not ok:
        raise LedgerError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def object_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key')
        result[key] = value
    return result


def parse(data):
    def invalid_constant(value):
        raise LedgerError('Non-finite JSON number: ' + value)
    return json.loads(data, object_pairs_hook=object_pairs, parse_constant=invalid_constant)


def ident(value, label):
    require(isinstance(value, str) and IDENT.fullmatch(value), 'Invalid ' + label)
    return value


def sha(value, label):
    require(isinstance(value, str) and HEX.fullmatch(value), 'Invalid SHA-256: ' + label)
    return value


def text(value, label):
    require(isinstance(value, str) and value.strip() and len(value) <= 2000
            and not any(ord(c) < 32 for c in value), 'Invalid ' + label)
    return value


def finite(value):
    try:
        return math.isfinite(value)
    except (OverflowError, TypeError):
        return False


def number(value, label, *, integer=False, nullable=False):
    if value is None and nullable:
        return None
    require(type(value) is int if integer else type(value) in (int, float), 'Invalid number: ' + label)
    require(finite(value) and value >= 0, 'Non-finite/negative number: ' + label)
    return value


class Snapshot:
    """Hold bytes once; refuse inputs changing before report completion."""
    def __init__(self):
        self.files = {}

    def read(self, path, *, optional=False):
        path = Path(path).resolve()
        if path in self.files:
            return self.files[path]
        if optional and not path.exists():
            self.files[path] = None
            return None
        require(path.is_file(), 'Missing input file')
        data = path.read_bytes()
        self.files[path] = data
        return data

    def verify(self):
        for path, data in self.files.items():
            if data is None:
                require(not path.exists(), 'Input appeared during snapshot')
            else:
                require(path.is_file() and path.read_bytes() == data, 'Input changed during snapshot')


def confined(root, value):
    require(isinstance(value, str) and value and '\\' not in value and ':' not in value,
            'Evidence path must be portable and relative')
    path = Path(value)
    require(not path.is_absolute() and '..' not in path.parts, 'Evidence path escapes root')
    resolved = (root / path).resolve()
    require(resolved.is_relative_to(root.resolve()), 'Evidence symlink escapes root')
    return resolved


def grading_contract(value):
    require(isinstance(value, dict), 'Missing grading contract')
    require(set(value) == {'metric_id', 'metric_sha256', 'judge_sha256', 'source_kind'}, 'Invalid grading contract fields')
    ident(value['metric_id'], 'metric id')
    sha(value['metric_sha256'], 'metric contract')
    sha(value['judge_sha256'], 'judge contract')
    require(value['source_kind'] in GRADERS, 'Unknown grading source')
    return value


def manifest_index(manifest):
    require(isinstance(manifest, dict), 'Manifest must be an object')
    require(type(manifest.get('schema_version')) is int and manifest['schema_version'] == 1, 'Unknown manifest schema')
    ident(manifest.get('study_id'), 'study id')
    sha(manifest.get('protocol_sha256'), 'protocol')
    require(manifest.get('analysis_unit') in ('independent_task', 'stream', 'diagnostic'), 'Declare analysis_unit')
    if manifest.get('grading_contract') is not None:
        grading_contract(manifest['grading_contract'])
    runs = manifest.get('runs')
    require(isinstance(runs, list) and runs, 'Plan must contain runs')
    index, keys, tasks, arms, conditions = {}, set(), {}, {}, {}
    for run in runs:
        require(isinstance(run, dict), 'Invalid planned run')
        rid = ident(run.get('id'), 'run id')
        require(rid not in index, 'Duplicate planned run')
        for field in ('task_id', 'arm'):
            ident(run.get(field), field)
        for field in ('input_sha256', 'harness_sha256'):
            sha(run.get(field), field)
        number(run.get('repeat'), 'repeat', integer=True)
        require(run['repeat'] > 0, 'Repeat must be positive')
        require(run.get('split') in ('development', 'pilot', 'test'), 'Invalid task split')
        condition = run.get('condition')
        require(isinstance(condition, dict), 'Missing condition')
        require(set(condition) == {'id', 'model', 'effort', 'host', 'host_version', 'environment_sha256'}, 'Invalid condition fields')
        cid = ident(condition['id'], 'condition id')
        for field in ('model', 'effort', 'host', 'host_version'):
            text(condition[field], field)
        sha(condition['environment_sha256'], 'environment')
        for registry, key, value in ((tasks, run['task_id'], (run['input_sha256'], run['split'])),
                                      (arms, run['arm'], run['harness_sha256']), (conditions, cid, condition)):
            require(key not in registry or registry[key] == value, 'Conflicting planned identity')
            registry[key] = value
        key = (cid, run['task_id'], run['arm'], run['repeat'])
        require(key not in keys, 'Duplicate planned case/repeat')
        keys.add(key)
        index[rid] = run
    return index


def source_refs(refs, sources):
    require(isinstance(refs, list) and refs and all(isinstance(r, str) for r in refs), 'Evidence source IDs required')
    require(len(set(refs)) == len(refs) and all(r in sources for r in refs), 'Unknown/duplicate evidence source')


def validate(bundle):
    """Validate normalized content. File byte verification belongs to load_bundle."""
    require(isinstance(bundle, dict), 'Bundle must be an object')
    manifest = bundle['manifest']
    index = manifest_index(manifest)
    bound = digest(canonical(manifest))
    require(bundle.get('manifest_sha256') == bound, 'Manifest binding differs')
    sources = bundle['sources']
    require(isinstance(sources, dict), 'Invalid sources')
    for sid, source in sources.items():
        ident(sid, 'source id')
        require(isinstance(source, dict), 'Source must be an object')
        sha(source.get('sha256'), 'source')
    records, outcomes = bundle['records'], bundle['outcomes']
    require(isinstance(records, list) and isinstance(outcomes, list), 'Records/outcomes must be arrays')
    ids, keys, charged, slots, products, selections = set(), set(), set(), {}, {}, {}
    for record in records:
        require(isinstance(record, dict), 'Record must be an object')
        ident(record.get('id'), 'record id')
        require(record['id'] not in ids, 'Duplicate record id')
        ids.add(record['id'])
        require(record.get('manifest_sha256') == bound, 'Record manifest differs')
        rid, stage = record.get('run_id'), record.get('stage')
        require(rid is None or rid in index, 'Unknown run')
        require(stage in (STUDY_STAGES if rid is None else RUN_STAGES), 'Stage has wrong scope')
        number(record.get('attempt'), 'attempt', integer=True)
        require(record['attempt'] > 0, 'Attempt must be positive')
        key = (rid, stage, record['attempt'])
        require(key not in keys, 'Duplicate stage attempt')
        keys.add(key)
        status = record.get('status')
        require(status in STATUSES, 'Unknown record status')
        if status != 'completed':
            text(record.get('reason'), 'record reason')
        require(record.get('meter') in METERS, 'Unknown meter')
        require(type(record.get('complete')) is bool and type(record.get('subagents_included')) is bool,
                'Coverage flags must be booleans')
        source_refs(record.get('sources'), sources)
        metrics = record.get('metrics')
        require(isinstance(metrics, dict) and set(metrics) == set(METRICS), 'All metrics required; unknown is null')
        for metric in METRICS:
            number(metrics[metric], metric, integer=metric.endswith('tokens'), nullable=True)
        if metrics['logical_tokens'] is not None and metrics['noncache_tokens'] is not None:
            require(metrics['noncache_tokens'] <= metrics['logical_tokens'], 'Noncache exceeds logical tokens')
        if status == 'completed' and stage == 'answer':
            require(metrics['logical_tokens'] is not None and metrics['logical_tokens'] > 0, 'Zero-token answer did not run')
        charges = record.get('charge_ids')
        require(isinstance(charges, list), 'Charge IDs required')
        for cid in charges:
            ident(cid, 'charge id')
            require(cid not in charged, 'Overlapping billed scopes, including parent/child: ' + cid)
            charged.add(cid)
        if any(v is not None and v > 0 for v in metrics.values()):
            require(charges, 'Measured spending needs billed scope IDs')
        slot = slots.setdefault((rid, stage), [])
        slot.append(record)
        if status == 'not_applicable':
            require(all(v == 0 for v in metrics.values()) and not charges, 'Not-applicable must be explicit zero work')
        produces = record.get('produces')
        if produces is not None:
            sha(produces, 'output')
            require(rid is not None and status == 'completed' and stage in ('answer', 'probe', 'compose'),
                    'Only completed execution produces a delivery candidate')
            require(produces in {sources[s]['sha256'] for s in record['sources']}, 'Output bytes need bound source')
            products.setdefault(rid, set()).add(produces)
        selected = record.get('selects')
        if stage == 'selection' and status == 'completed':
            require(selected is not None, 'Completed selection must identify its choice')
        judged = record.get('judges')
        if stage == 'grading' and status == 'completed':
            sha(judged, 'graded output')
        elif judged is not None:
            require(False, 'Only completed grading may name a judged output')
        if selected is not None:
            sha(selected, 'selected output')
            require(rid is not None and stage == 'selection' and status == 'completed' and rid not in selections,
                    'Selection must have one completed result per run')
            selections[rid] = selected
    for slot in slots.values():
        require(not any(r['status'] == 'not_applicable' for r in slot) or len(slot) == 1, 'N/A conflicts with work')
    for rid, selected in selections.items():
        require(selected in products.get(rid, set()), 'Selection points outside same run outputs')
    seen = set()
    for outcome in outcomes:
        require(isinstance(outcome, dict), 'Outcome must be an object')
        rid = outcome.get('run_id')
        require(rid in index and rid not in seen, 'Unknown/duplicate outcome')
        seen.add(rid)
        require(outcome.get('manifest_sha256') == bound, 'Outcome manifest differs')
        require(outcome.get('status') in ('completed', 'scored'), 'Invalid outcome status')
        source_refs(outcome.get('sources'), sources)
        output = outcome.get('output_sha256')
        if output is None:
            text(outcome.get('identity_note'), 'missing artifact identity reason')
        else:
            sha(output, 'delivered output')
            require(output in products.get(rid, set()), 'Delivered output was not produced by this run')
            if rid in selections:
                require(output == selections[rid], 'Delivered output differs from selection')
            grades = [r for r in slots.get((rid, 'grading'), []) if r['status'] == 'completed']
            require(not grades or any(r['judges'] == output for r in grades), 'Grade refers to another output')
        require(any(r['status'] == 'completed' for r in slots.get((rid, 'answer'), [])), 'Outcome has no completed answer')
        if outcome['status'] == 'scored':
            require(not any(r['status'] == 'not_applicable' for r in slots.get((rid, 'grading'), [])),
                    'Scored outcome conflicts with not-applicable grading')
            score = outcome.get('score')
            require(type(score) in (float, int) and finite(score), 'Scored outcome requires finite score')
            sha(outcome.get('judge_sha256'), 'judge')
            contract = outcome.get('grading_contract')
            if contract is not None:
                grading_contract(contract)
                require(contract['judge_sha256'] == outcome['judge_sha256'], 'Outcome judge contradicts contract')
        else:
            require(outcome.get('score') is None, 'Unscored is not zero')
            text(outcome.get('reason'), 'unscored reason')
    return index, slots


def measured(record, metric):
    return (record['metrics'][metric] is not None and record['complete'] and record['subagents_included']
            and record['meter'] != 'self_report'
            and record['status'] not in ('interrupted', 'unmeasured'))


def totals(records, missing=0):
    result = {}
    for metric in METRICS:
        values = [r['metrics'][metric] for r in records if r['metrics'][metric] is not None]
        observed = sum(values)
        require(finite(observed), 'Aggregate overflow: ' + metric)
        unknown = missing + sum(not measured(r, metric) for r in records)
        result[metric] = {'observed': observed, 'complete': unknown == 0,
                          'unknown_entries': unknown, 'total': observed if unknown == 0 else None}
    return result


def summarize(bundle):
    index, slots = validate(bundle)
    required = [(rid, stage) for rid in index for stage in RUN_STAGES] + [(None, s) for s in STUDY_STAGES]
    absent = [key for key in required if key not in slots]
    outcomes = {o['run_id']: o for o in bundle['outcomes']}
    records = bundle['records']
    rows = []
    for rid, run in sorted(index.items()):
        own = [r for r in records if r['run_id'] == rid]
        outcome = outcomes.get(rid)
        missing = [s for r, s in absent if r == rid]
        identity = bool(outcome and outcome.get('output_sha256') and outcome.get('grading_contract'))
        graded = bool(outcome and outcome.get('output_sha256') and any(
            r['status'] == 'completed' and r.get('judges') == outcome['output_sha256']
            and r['complete'] and r['subagents_included'] and r['meter'] != 'self_report'
            for r in own if r['stage'] == 'grading'))
        rows.append({'id': rid, 'task_id': run['task_id'], 'arm': run['arm'], 'condition': run['condition']['id'],
                     'repeat': run['repeat'], 'split': run['split'],
                     'started': any(r['status'] not in ('not_applicable', 'unmeasured') for r in own),
                     'completed': outcome is not None, 'scored': bool(outcome and outcome['status'] == 'scored'),
                     'artifact_identity_complete': identity, 'grading_evidence_complete': graded, 'score': outcome.get('score') if outcome else None,
                     'not_run_attempts': sum(r['status'] == 'not_run' for r in own),
                     'interrupted_attempts': sum(r['status'] == 'interrupted' for r in own),
                     'missing_stages': missing,
                     'reasons': sorted(set(r.get('reason', '') for r in own if r.get('reason'))
                                       | ({outcome['reason']} if outcome and outcome.get('reason') else set())
                                       | ({'No completed outcome'} if not outcome else set())
                                       | ({'No complete grading evidence'} if outcome and outcome['status'] == 'scored' and not graded else set())),
                     'cost': totals(own, len(missing))})
    scopes = {}
    for name, pred in (
        ('execution', lambda scope, stage: scope is not None and stage != 'grading'),
        ('grading', lambda scope, stage: stage == 'grading'),
        ('study_overhead', lambda scope, stage: scope is None)):
        scopes[name] = totals([r for r in records if pred(r['run_id'], r['stage'])],
                              sum(pred(*key) for key in absent))
    stages = {stage: totals([r for r in records if r['stage'] == stage], sum(s == stage for _, s in absent))
              for stage in RUN_STAGES + STUDY_STAGES}
    groups = []
    for condition, arm in sorted({(r['condition'], r['arm']) for r in rows}):
        ids = {r['id'] for r in rows if r['condition'] == condition and r['arm'] == arm}
        groups.append({'condition': condition, 'arm': arm,
                       'execution': totals([r for r in records if r['run_id'] in ids and r['stage'] != 'grading'],
                                           sum(rid in ids and stage != 'grading' for rid, stage in absent))})
    whole = totals(records, len(absent))
    complete = all(v['complete'] for v in whole.values()) and all(r['artifact_identity_complete'] and r['grading_evidence_complete'] and r['scored'] for r in rows)
    return {'schema_version': 1, 'study_id': bundle['manifest']['study_id'], 'manifest_sha256': bundle['manifest_sha256'],
            'status': 'complete' if complete else 'incomplete', 'benefit_verdict': None,
            'coverage': {'planned': len(rows), 'started': sum(r['started'] for r in rows),
                         'completed': sum(r['completed'] for r in rows), 'scored': sum(r['scored'] for r in rows),
                         'missing_outcomes': sum(not r['completed'] for r in rows),
                         'not_run_attempts': sum(r['not_run_attempts'] for r in rows),
                         'interrupted_attempts': sum(r['interrupted_attempts'] for r in rows)},
            'scopes': scopes, 'whole_study': whole, 'stages': stages, 'groups': groups, 'runs': rows,
            'sources': {sid: {'sha256': value['sha256']} for sid, value in sorted(bundle['sources'].items())},
            'record_sha256': {r['id']: digest(canonical(r)) for r in records}, 'limitation': LIMITATION}


def load_bundle(path, evidence_root=None):
    snapshot = Snapshot()
    bundle = parse(snapshot.read(path))
    root = Path(evidence_root) if evidence_root else Path(path).resolve().parent
    require(isinstance(bundle, dict), 'Bundle must be an object')
    require(isinstance(bundle.get('sources'), dict), 'Invalid sources')
    for source in bundle['sources'].values():
        require(isinstance(source, dict), 'Source must be an object')
        data = snapshot.read(confined(root, source['path']))
        require(digest(data) == source['sha256'], 'Evidence source hash differs')
    validate(bundle)
    snapshot.verify()
    return bundle, snapshot


def compare(bundle, baseline, candidate, condition, margin, *, floor_sd=None, lower_is_better=False):
    report = summarize(bundle)
    manifest = bundle['manifest']
    require(manifest['analysis_unit'] == 'independent_task', 'Comparator requires independent_task; no stream/diagnostic inference')
    require(baseline != candidate, 'Comparison arms must differ')
    contract = grading_contract(manifest.get('grading_contract'))
    require(contract['source_kind'] in ('mechanical', 'independent_model'), 'Independent grading contract required')
    runs = [r for r in manifest['runs'] if r['arm'] in (baseline, candidate) and r['condition']['id'] == condition]
    require(runs and all(r['split'] == 'test' for r in runs), 'Comparison requires only planned test runs, no pilot/development')
    by_arm = {arm: {(r['task_id'], r['repeat']): r for r in runs if r['arm'] == arm} for arm in (baseline, candidate)}
    require(by_arm[baseline] and set(by_arm[baseline]) == set(by_arm[candidate]), 'Unmatched task/repeat plan')
    outcomes = {o['run_id']: o for o in bundle['outcomes']}
    products, costs = {baseline: {}, candidate: {}}, {baseline: {}, candidate: {}}
    for arm, mapped in by_arm.items():
        for (task, repeat), run in sorted(mapped.items()):
            outcome = outcomes.get(run['id'])
            require(outcome and outcome['status'] == 'scored' and outcome.get('output_sha256'), 'Missing/unscored/artifact-incomplete outcome')
            require(outcome.get('grading_contract') == contract, 'Mixed metric/judge/grading-source contract')
            grade_records = [r for r in bundle['records'] if r['run_id'] == run['id'] and r['stage'] == 'grading']
            require(any(r['status'] == 'completed' and r['judges'] == outcome['output_sha256']
                        and r['complete'] and r['meter'] != 'self_report' for r in grade_records),
                    'Independent completed grading evidence required')
            own = [r for r in bundle['records'] if r['run_id'] == run['id'] and r['stage'] != 'grading']
            absent = sum(not any(r['stage'] == stage for r in own) for stage in RUN_STAGES if stage != 'grading')
            usage = totals(own, absent)['logical_tokens']
            require(usage['complete'] and usage['total'] > 0, 'Incomplete execution token coverage')
            products[arm].setdefault(task, []).append(outcome['score'])
            costs[arm].setdefault(task, []).append(usage['total'])
    if any(len(v) == 1 for v in products[baseline].values()):
        require(floor_sd is not None, 'Single-repeat comparison requires predeclared floor_sd')
    return {**report, 'comparison': {'scope': 'single metric/judge; execution tokens excluding grading/shared study overhead',
             'condition': condition, 'baseline': baseline, 'candidate': candidate, 'grading_contract': contract,
             'task_repeats': [[task, repeat] for task, repeat in sorted(by_arm[baseline])],
             'quality': eval_stats.compare(products[candidate], products[baseline], margin,
                                           floor_sd=floor_sd, lower_is_better=lower_is_better),
             'cost': eval_stats.cost(costs[candidate], costs[baseline]),
             'adoption_verdict': None, 'cross_family_quality_verdict': None}}


def markdown(report):
    c = report['coverage']
    lines = ['# Evaluation accounting: ' + report['study_id'], '',
             'Status: **' + report['status'] + '**. No benefit/adoption verdict.', '',
             f"Planned {c['planned']}; started {c['started']}; completed {c['completed']}; scored {c['scored']}; missing outcomes {c['missing_outcomes']}.",
             '', '| Scope | Observed logical tokens | Complete total |', '|---|---:|---:|']
    for name, values in list(report['scopes'].items()) + [('whole_study', report['whole_study'])]:
        t = values['logical_tokens']
        lines.append(f"| {name} | {t['observed']} | {t['total'] if t['complete'] else 'unknown'} |")
    lines += ['', '| Stage | Observed logical tokens | Complete total |', '|---|---:|---:|']
    for name, values in report['stages'].items():
        t = values['logical_tokens']
        lines.append(f"| {name} | {t['observed']} | {t['total'] if t['complete'] else 'unknown'} |")
    lines += ['', '| Run | Completed | Scored | Missing stages |', '|---|---|---|---|']
    for r in report['runs']:
        lines.append(f"| {r['id']} | {r['completed']} | {r['scored']} | {', '.join(r['missing_stages']) or 'none'} |")
    if report.get('comparison'):
        comp = report['comparison']
        lines += ['', 'Comparison scope: ' + comp['scope'],
                  f"Quality: {comp['quality']['class']}; execution cost: {comp['cost']['class']}. No adoption verdict."]
    if report.get('adapter'):
        lines += ['', 'Import: ' + report['adapter']['limitation'],
                  'Outstanding reserve (not spent): ' + str(report['adapter']['claude_outstanding_reserve'])]
    lines += ['', report['limitation'], '', 'Source hashes:', '']
    lines += ['- ' + sid + ': `' + source['sha256'] + '`' for sid, source in report['sources'].items()]
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('report', 'compare'):
        p = sub.add_parser(name)
        p.add_argument('bundle', type=Path)
        p.add_argument('--evidence-root', type=Path)
        p.add_argument('--format', choices=('json', 'markdown'), default='json')
        if name == 'compare':
            p.add_argument('--baseline', required=True)
            p.add_argument('--candidate', required=True)
            p.add_argument('--condition', required=True)
            p.add_argument('--margin', type=float, required=True)
            p.add_argument('--floor-sd', type=float)
            p.add_argument('--lower-is-better', action='store_true')
    p = sub.add_parser('fixcheck')
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--state', type=Path, required=True)
    p.add_argument('--format', choices=('json', 'markdown'), default='json')
    args = parser.parse_args(argv)
    try:
        if args.command == 'fixcheck':
            from eval_ledger_fixcheck import report_fixcheck
            result = report_fixcheck(args.manifest, args.state)
        else:
            bundle, snapshot = load_bundle(args.bundle, args.evidence_root)
            result = (compare(bundle, args.baseline, args.candidate, args.condition, args.margin,
                              floor_sd=args.floor_sd, lower_is_better=args.lower_is_better)
                      if args.command == 'compare' else summarize(bundle))
            snapshot.verify()
        print(markdown(result) if args.format == 'markdown' else json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False),
              end='' if args.format == 'markdown' else '\n')
        return 0 if result['status'] == 'complete' else 2
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, OSError) as exc:
        # No input contents/absolute paths in an automatically publishable report.
        message = str(exc) if isinstance(exc, LedgerError) else 'Invalid or unreadable evaluation input'
        print(json.dumps({'status': 'invalid', 'error': message}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
