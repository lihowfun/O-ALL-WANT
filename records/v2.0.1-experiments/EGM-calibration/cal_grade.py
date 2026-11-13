#!/usr/bin/env python3
"""Prepare blind reports and mechanically apply the preregistered native screen.

Only run-grader calls a model; pack and score are offline. Private unblinding
maps must never reach graders. Tests use synthetic keys exclusively.
"""
import argparse
import copy
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from types import SimpleNamespace
from cal_common import append, canonical, hexsha, load, require, rows, save, sha
from cal_run import CELLS, usable, validate_report

HERE = Path(__file__).resolve().parent
SEED = 'egmcal-issue20-2026-11-14-v1'
LABELS = {'detected', 'mention-only', 'absent', 'not adjudicable'}
TEST_MODELS = {c[0] for c in CELLS.values()}
KEY_FIELDS = {'id', 'tier', 'cluster', 'claim', 'evidence', 'detected_if', 'mention_only_if', 'not_adjudicable_if'}
GRADERS = {'codex': ('gpt-6-astra', 'openai'), 'claude': ('claude-fable-5-2', 'anthropic')}


def text(value):
    return isinstance(value, str) and bool(value.strip())


def evidence(value, allow_empty=False):
    return (isinstance(value, list) and (allow_empty or bool(value)) and
            all(text(v) for v in value))


def validate_key(key):
    require(key.get('schema_version') == 1 and hexsha(key.get('packet_sha256')) and
            isinstance(key.get('items'), list), 'invalid key schema/binding')
    seen = set()
    for k in key['items']:
        require(isinstance(k, dict) and set(k) == KEY_FIELDS, 'key item fields differ')
        require(text(k['id']) and k['id'] not in seen and k['tier'] in ('primary', 'secondary'), 'bad key id/tier')
        require(evidence(k['evidence']), 'key source evidence missing')
        require(all(text(k[f]) for f in KEY_FIELDS - {'evidence', 'tier'}), 'empty key definition')
        seen.add(k['id'])
    return seen


def anonymous_report(state, row, report):
    """Rewrite known private roots once, longest prefix first; never edit raw state."""
    state = Path(state).resolve()
    parent = state / 'attempts' / (row['cell'] + '-' + row['arm']) / row['attempt_id']
    prefixes = {str(parent / 'workspace'), str(parent / 'home'), str(state)}
    # Also support an audited report in a nonstandard attempt location.
    path = state / row['report_path']
    if path.parent.name == 'review_out':
        prefixes.update((str(path.parent.parent), str(path.parent.parent.parent / 'home')))
    pattern = re.compile('(?:' + '|'.join(re.escape(p) for p in sorted(prefixes, key=lambda p: (-len(p), p))) + r')(?=/|$|[\s:<>"\x27`])')
    count = 0
    def rewrite(value):
        nonlocal count
        if isinstance(value, str):
            result, n = pattern.subn('packet', value)
            count += n
            return result
        if isinstance(value, list):
            return [rewrite(v) for v in value]
        if isinstance(value, dict):
            return {rewrite(k): rewrite(v) for k, v in value.items()}
        return value
    return rewrite({k: report[k] for k in ('findings', 'uncertainties')}), count


def check_blind_paths(folder, state, attempt_ids=()):
    """Reject provenance in any packed file name or JSON string path component."""
    forbidden = {'codex', 'claude', 'N1', 'N2'} | set(attempt_ids)
    component = re.compile(r'(?:^|[/\\\s\x27"`(])(?:' + '|'.join(re.escape(s) for s in sorted(forbidden))
                           + r'|(?:codex|claude)-(?:N1|N2|M)(?:\.a\d+)?)(?=$|[/\\:\s\x27"`)])')
    root = str(Path(state).resolve())
    def check(value):
        if isinstance(value, str):
            require(root not in value and not component.search(value), 'blind packet contains private path provenance')
        elif isinstance(value, list):
            for v in value:
                check(v)
        elif isinstance(value, dict):
            for k, v in value.items():
                check(k)
                check(v)
    for path in Path(folder).rglob('*'):
        check(path.relative_to(folder).as_posix())
        if path.is_file():
            check(load(path))


def pack(state, destination, batch=1):
    state, destination = Path(state), Path(destination)
    require(not destination.exists(), 'blind pack already exists; no reshuffle')
    require(batch in (1, 2), 'invalid batch')
    seed = SEED if batch == 1 else SEED + '-batch2'
    expected = [('codex', 'N1'), ('codex', 'N2'), ('claude', 'N1')]
    if batch == 2:
        expected.append(('claude', 'N2'))
    reports = []
    attempts = [r for cell in CELLS for r in rows(state / ('rows-' + cell + '.jsonl'))]
    for cell, arm in expected:
        found = [r for r in attempts if r['cell'] == cell and r['arm'] == arm and usable(r)]
        require(len(found) == 1, 'batch requires every specified completed report')
        r = found[0]
        require(not r.get('dry_run'), 'synthetic dry-run reports cannot be graded')
        path = state / r['report_path']
        require(path.resolve().is_relative_to(state.resolve()), 'report escapes state root')
        require(sha(path.read_bytes()) == r['report_sha256'], 'report changed')
        report = validate_report(load(path))
        report, rewrite_count = anonymous_report(state, r, report)
        reports.append((r, report, rewrite_count))
    if batch == 2:
        previous = load(state / 'blind1-PRIVATE-MAP.json')
        require({(m['row']['cell'], m['row']['arm']): m['row'] for m in previous['reports'].values()} ==
                {(r['cell'], r['arm']): r for r, _, _ in reports if (r['cell'], r['arm']) != ('claude', 'N2')},
                'batch-1 repeats differ')
    require(reports, 'no completed reports')
    reports.sort(key=lambda pair: sha((seed + '|' + pair[0]['cell'] + '|' + pair[0]['arm']).encode()))
    destination.mkdir(mode=0o700)
    (destination / 'reports').mkdir()
    index, mapping = [], {}
    for i, (row, report, rewrite_count) in enumerate(reports, 1):
        ident = f'R{(100 if batch == 2 else 0) + i:03d}'
        save(destination / 'reports' / (ident + '.json'), report)
        digest = sha(canonical(report))
        index.append({'report_id': ident, 'report_sha256': digest})
        mapping[ident] = {'row': row, 'original_report_sha256': row['report_sha256'], 'anonymous_sha256': digest,
                          'path_rewrite_count': rewrite_count}
    packet_hashes = {r['packet_sha256'] for r, _, _ in reports}
    key_hashes = {r.get('key_sha256') for r, _, _ in reports}
    require(len(packet_hashes) == 1 and len(key_hashes) == 1 and hexsha(next(iter(key_hashes))), 'mixed/missing packet/key binding')
    public = {'schema_version': 1, 'reports': index,
              'packet_sha256': next(iter(packet_hashes)), 'key_sha256': next(iter(key_hashes)),
              'rubric_sha256': sha((HERE / 'GRADER.md').read_bytes())}
    save(destination / 'index.json', public)
    check_blind_paths(destination, state, [r['attempt_id'] for r, _, _ in reports])
    # Deliberately outside the directory that is sent to graders.
    save(destination.with_name(destination.name + '-PRIVATE-MAP.json'),
         {'schema_version': 1, 'blind_pack_sha256': sha(canonical(public)), 'reports': mapping,
          'batch': batch, 'seed': seed, 'planned_runs': [f'{c}-{a}' for c, a in expected]})
    return public


def validate_grade(grade, key, key_sha, index):
    ids = validate_key(key)
    require(grade.get('schema_version') == 1 and text(grade.get('grader_id')) and text(grade.get('family'))
            and text(grade.get('model')) and grade['model'].casefold() not in TEST_MODELS, 'bad/prohibited grader identity')
    require(grade.get('key_sha256') == key_sha == index['key_sha256'] and
            grade.get('packet_sha256') == key['packet_sha256'] == index['packet_sha256'] and
            grade.get('rubric_sha256') == index['rubric_sha256'] and
            grade.get('blind_pack_sha256') == sha(canonical(index)), 'grade binding differs')
    require(grade.get('independent') is True and grade.get('blinded') is True, 'grading not independent/blind')
    require('eligibility' not in grade, 'eligibility is settled; graders must not re-decide it')
    expected = {r['report_id']: r['report_sha256'] for r in index['reports']}
    require(len(expected) == len(index['reports']), 'duplicate blind report id')
    reports = grade.get('reports')
    require(isinstance(reports, list) and len(reports) == len(expected), 'grades missing reports')
    seen = set()
    for r in reports:
        rid = r.get('report_id')
        require(rid in expected and rid not in seen and r.get('report_sha256') == expected[rid], 'bad/duplicate graded report')
        require(type(r.get('valid_review')) is bool and isinstance(r.get('items'), list), 'bad review grade')
        require(len(r['items']) == len(ids), 'missing item labels')
        items = set()
        for item in r['items']:
            require(item.get('id') in ids and item['id'] not in items and item.get('label') in LABELS
                    and text(item.get('reason')) and
                    (grade['family'] == 'anthropic' or evidence(item.get('source_evidence'))), 'invalid item grade')
            require(evidence(item.get('report_evidence'), allow_empty=item['label'] in ('absent', 'not adjudicable')), 'report anchors missing')
            items.add(item['id'])
        claims = r.get('unsupported_claims')
        require(isinstance(claims, list), 'unsupported claims missing')
        require(grade['family'] != 'anthropic' or not claims, 'Claude does not assess unsupported claims')
        claim_ids = set()
        for c in claims:
            require(text(c.get('id')) and c['id'] not in claim_ids and text(c.get('claim'))
                    and text(c.get('reason')) and evidence(c.get('report_evidence')) and
                    evidence(c.get('source_evidence')) and type(c.get('severe')) is bool, 'unsupported claim lacks evidence')
            require(not c['severe'] or text(c.get('severe_effect')), 'severe false alarm lacks effect')
            claim_ids.add(c['id'])
        require(isinstance(r.get('blinding_risks'), list), 'blinding assessment missing')
        seen.add(rid)
    return grade


def apply_resolution(grades, resolution, input_hashes, index, primary=None):
    result = copy.deepcopy(grades)
    if resolution is None:
        return result
    require(resolution.get('schema_version') == 1 and resolution.get('input_grade_sha256') == input_hashes
            and resolution.get('blind_pack_sha256') == sha(canonical(index))
            and resolution.get('unblinding_occurred') is False, 'resolution binding/blinding differs')
    require(isinstance(resolution.get('changes'), list), 'bad resolution changes')
    grader_ids = sorted(g['grader_id'] for g in grades)
    seen = set()
    for c in resolution['changes']:
        require(c.get('scope') == 'item' and (primary is None or c.get('id') in primary)
                and text(c.get('reason')) and sorted(c.get('accepted_by', [])) == grader_ids,
                'only consensus primary-label corrections are allowed')
        ident = (c.get('report_id'), c.get('id'))
        require(ident not in seen and c.get('label') in LABELS, 'duplicate/invalid correction')
        seen.add(ident)
        old = [i['label'] for g in grades for r in g['reports'] if r['report_id'] == ident[0]
               for i in r['items'] if i['id'] == ident[1]]
        require(len(old) == 2 and len(set(old)) == 2, 'correction requires original disagreement')
        require(evidence(c.get('report_evidence'), allow_empty=c['label'] in ('absent', 'not adjudicable')),
                'correction lacks passage')
        for g in result:
            item = next(i for r in g['reports'] if r['report_id'] == ident[0] for i in r['items'] if i['id'] == ident[1])
            item.update(label=c['label'], reason=c['reason'], report_evidence=c['report_evidence'])
    return result


def decision(primary, labels, complete, cell='codex', n2_launched=True, n2_funded=True):
    """Frozen key gate precedes data; never exclude a primary based on report labels."""
    if not complete or len(primary) < 3:
        return {'outcome': 'no conclusion', 'rule': 'NC1_incomplete_runs_grading_isolation_metering_or_key_gate'}
    arms = ('N1', 'N2') if n2_launched else ('N1',)
    covered = [{i for i in primary if any(g[n].get(i) == 'detected' for n in arms)} for g in labels]
    if all(s == set(primary) for s in covered):
        return {'outcome': 'ceiling', 'rule': 'C1_both_graders_native_union_detects_every_primary'}
    if cell == 'claude' and not n2_launched and not n2_funded:
        return {'outcome': 'no conclusion', 'rule': 'NC5_N2_not_funded'}
    if n2_launched:
        missing = [i for i in primary if all(g[n].get(i) == 'absent' for g in labels for n in arms)]
        if missing:
            return {'outcome': 'room', 'rule': 'R1_both_graders_both_native_absent', 'room_items': missing}
    return {'outcome': 'no conclusion', 'rule': 'NC4_unresolved_deciding_labels_or_mention_only',
            'not_covered_by_both': sorted(set(primary) - set.intersection(*covered))}


def score(key, key_sha, grades, index, mapping, resolution=None, grade_hashes=None,
          accounting_complete=True, previous=None, n2_launched=False, n2_funded=True):
    for g in grades:
        validate_grade(g, key, key_sha, index)
    require(len(grades) == 2 and grades[0]['family'].casefold() != grades[1]['family'].casefold()
            and grades[0]['grader_id'] != grades[1]['grader_id'], 'two different-family graders required')
    require(mapping.get('schema_version') == 1 and mapping.get('blind_pack_sha256') == sha(canonical(index)), 'map binding differs')
    require(set(mapping['reports']) == {r['report_id'] for r in index['reports']}, 'map report set differs')
    for rid, m in mapping['reports'].items():
        require(m['anonymous_sha256'] == next(r['report_sha256'] for r in index['reports'] if r['report_id'] == rid), 'anonymous map differs')
    primary = [i['id'] for i in key['items'] if i['tier'] == 'primary']
    resolved = apply_resolution(grades, resolution, grade_hashes, index, primary)
    for g in resolved:
        validate_grade(g, key, key_sha, index)
    if previous:
        require(previous['key_sha256'] == key_sha and previous['reconciliation_complete'] and
                previous['accounting_complete'], 'batch-1 score incomplete')
    by_grade = [{r['report_id']: r for r in g['reports']} for g in resolved]
    original = [{r['report_id']: r for r in g['reports']} for g in grades]
    results = {}
    retest = []
    batch = mapping.get('batch', 1)
    n2_launched = n2_launched or any(m['row']['cell'] == 'claude' and m['row']['arm'] == 'N2' for m in mapping['reports'].values())
    for cell in CELLS:
        reports, originals = {}, {}
        arms = ('N1', 'N2') if cell == 'codex' or n2_launched or batch == 2 else ('N1',)
        complete = accounting_complete
        for arm in arms:
            matches = [(rid, m['row']) for rid, m in mapping['reports'].items()
                       if m['row']['cell'] == cell and m['row']['arm'] == arm]
            if len(matches) != 1:
                complete = False
                continue
            rid, row = matches[0]
            complete = complete and usable(row) and not row.get('dry_run') and row['packet_sha256'] == key['packet_sha256'] and row.get('key_sha256') == key_sha
            if not previous or (cell, arm) == ('claude', 'N2'):
                complete = complete and all(bg[rid]['valid_review'] for bg in by_grade)
            current = {'blind_id': rid, 'logical_tokens': row['tokens_total'], 'noncache_tokens': row['tokens_noncache'],
                'seconds': row.get('seconds'), 'row': row,
                'valid_review': {g['family']: by_grade[j][rid]['valid_review'] for j, g in enumerate(resolved)},
                'labels': {g['family']: {i['id']: i['label'] for i in by_grade[j][rid]['items']} for j, g in enumerate(resolved)},
                'item_details': {g['family']: by_grade[j][rid]['items'] for j, g in enumerate(resolved)},
                'unsupported_claims': {g['family']: by_grade[j][rid]['unsupported_claims'] for j, g in enumerate(resolved) if g['family'] != 'anthropic'},
                'unsupported_claims_attribution': 'one grader (Codex family)',
                'severe_false_alarms': {g['family']: [c for c in by_grade[j][rid]['unsupported_claims'] if c['severe']] for j, g in enumerate(resolved) if g['family'] != 'anthropic'}}
            orig = {g['family']: {i['id']: i['label'] for i in original[j][rid]['items']} for j, g in enumerate(grades)}
            if previous and (cell, arm) != ('claude', 'N2'):
                old = previous['cells'][cell]['reports'][arm]
                require(old['row'] == row, 'repeated report changed')
                complete = complete and all(old['valid_review'].values())
                for family in current['labels']:
                    # Original independent labels give the test-retest figure, before reconciliation.
                    before = previous['independent_labels'][cell][arm][family]
                    now = orig[family]
                    for tier, ids in [('primary', primary), ('all', [i['id'] for i in key['items']])]:
                        retest.append({'cell': cell, 'arm': arm, 'family': family, 'tier': tier,
                            'same_labels': sum(before[i] == now[i] for i in ids), 'items': len(ids),
                            'agreement': sum(before[i] == now[i] for i in ids) / len(ids) if ids else None})
                reports[arm] = old  # repeated batch-2 labels NEVER enter the decision
                originals[arm] = previous['independent_labels'][cell][arm]
            else:
                reports[arm], originals[arm] = current, orig
        labs = [{arm: reports[arm]['labels'][g['family']] if arm in reports else {} for arm in arms} for g in resolved]
        orig_labs = [{arm: originals[arm][g['family']] if arm in originals else {} for arm in arms} for g in grades]
        has_n2 = 'N2' in arms
        verdict = decision(primary, labs, complete, cell, has_n2, n2_funded)
        verdict['before_resolution'] = decision(primary, orig_labs, complete, cell, has_n2, n2_funded)
        verdict['complete'] = bool(complete)
        verdict['reports'] = reports
        verdict['N1_N2_agreement'] = []
        if complete and has_n2:
            for j, g in enumerate(resolved):
                sets = [{i for i in primary if labs[j][n][i] == 'detected'} for n in arms]
                union = sets[0] | sets[1]
                verdict['N1_N2_agreement'].append({'family': g['family'], 'primary_items': len(primary),
                    'identical_labels': sum(labs[j]['N1'][i] == labs[j]['N2'][i] for i in primary),
                    'detected_intersection': sorted(sets[0] & sets[1]), 'detected_union': sorted(union),
                    'detection_jaccard': len(sets[0] & sets[1]) / len(union) if union else None})
        verdict['recall_by_area'] = {}
        for area, ids in [('catalog', [i for i in primary if i in ('K14', 'K15', 'K18')]),
                          ('other', [i for i in primary if i not in ('K14', 'K15', 'K18')])]:
            verdict['recall_by_area'][area] = {g['family']: {'primary_ids': ids, 'denominator': len(ids),
                'per_report': {arm: sum(labs[j][arm].get(i) == 'detected' for i in ids) / len(ids) if ids else None for arm in reports},
                'native_union': sum(any(labs[j][arm].get(i) == 'detected' for arm in reports) for i in ids) / len(ids) if ids else None}
                for j, g in enumerate(resolved)}
        retained = [r['row'] for r in reports.values() if usable(r['row'])]
        unit = sum(r['tokens_total'] for r in retained) / len(retained) if retained else None
        verdict['measured_native_unit_cost'] = {'logical_tokens': unit,
            'noncache_tokens': sum(r['tokens_noncache'] for r in retained) / len(retained) if retained else None,
            'retained_runs': len(retained), 'historical_full_egm_logical_tokens': 18_480_203,
            'native_to_historical_ratio': unit / 18_480_203 if unit is not None else None,
            'historical_date': '2026-11-07',
            'statement': 'One historical full-EGM run on this same document; not a comparison of quality. Provider token units are recorded separately.'}
        if previous and cell == 'codex':
            # Batch 1 is final for Codex. Only later accounting can invalidate it.
            verdict = copy.deepcopy(previous['cells'][cell])
            if not complete or not accounting_complete:
                verdict.update(decision(primary, labs, False, cell, has_n2, n2_funded), complete=False)
                verdict['before_resolution'] = decision(primary, orig_labs, False, cell, has_n2, n2_funded)
        results[cell] = verdict
        # Keep original labels for batch-2 test-retest without reusing batch-2 repeats in decisions.
        verdict['_independent'] = originals
    independent = {c: v.pop('_independent') for c, v in results.items()}
    return {'schema_version': 1, 'cells': results, 'benefit_verdict': None, 'batch': batch,
            'key_sha256': key_sha, 'blind_pack_sha256': sha(canonical(index)),
            'resolution_applied': resolution is not None, 'independent_labels': independent,
            'test_retest_agreement': retest, 'secondary_items': 'descriptive only; see per-report item_details'}


def final_accounting(audit, ledger, binding):
    if ledger.get('unsettled_intents'):
        return False
    if audit.get('schema_version') != 1 or audit.get('freeze_sha256') != binding:
        return False
    if not all(audit.get(k) is True for k in ('all_shared_work_recorded', 'isolation_audit_complete',
                                             'grading_metering_complete', 'curation_metering_complete')):
        return False
    if not evidence(audit.get('evidence_sha256')) or not all(hexsha(h) for h in audit['evidence_sha256']):
        return False
    stage = audit.get('outside_stage_claude_logical')
    experiment = audit.get('outside_experiment_claude_logical')
    if type(stage) is not int or type(experiment) is not int or not 0 <= stage <= experiment:
        return False
    recorded = ledger['providers']['claude']['observed_logical_tokens']
    return (all(p['metering_complete_for_recorded_work'] and p.get('isolation_complete_for_recorded_work', True)
                for p in ledger['providers'].values())
            and recorded + experiment <= 30_000_000)


def run_grader(a):
    if a.family == 'claude':
        from cal_requests import run_claude_grades
        return run_claude_grades(a)
    import build_packet
    import cal_run as R
    import cal_sandbox
    R.no_api_keys(os.environ)
    binding = R.frozen()
    out = R.check_out(a.state, a.dry_run)
    manifest = load(HERE / 'packet_manifest.json')
    require(a.packet, 'Codex grader requires packet')
    packet_sha = build_packet.verify(a.packet, manifest)
    key = load(a.key)
    validate_key(key)
    key_sha = sha(a.key.read_bytes())
    index = load(a.blind / 'index.json')
    check_blind_paths(a.blind, out)
    require(index['packet_sha256'] == packet_sha == key['packet_sha256'] and
            index['key_sha256'] == key_sha and index['rubric_sha256'] == sha((HERE / 'GRADER.md').read_bytes()),
            'grader inputs differ from official packet/key/rubric')
    require({p.relative_to(a.blind).as_posix() for p in a.blind.rglob('*') if p.is_file()} ==
            {'index.json'} | {'reports/' + r['report_id'] + '.json' for r in index['reports']},
            'blind folder contains unexpected files')
    require(not any(p.is_symlink() for p in a.blind.rglob('*')), 'blind symlink')
    for r in index['reports']:
        require(re.fullmatch(r'R\d{3}', r['report_id']) and
                sha(canonical(load(a.blind / 'reports' / (r['report_id'] + '.json')))) == r['report_sha256'],
                'blind report hash differs')
    model, family = GRADERS[a.family]
    ident = 'grader-' + a.family + '-' + sha(canonical(index))[:12] + '.a1'
    cli = str(a.cli.resolve()) if a.cli else a.family
    with (out / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        require(not (out / 'graders' / ident).exists(), 'grader already started; preserve original, no redraw')
        stage, experiment = R.spending(out, binding, a.spent, a.experiment_spent)
        allowance = R.DEFAULT_INFLIGHT
        if not a.dry_run:
            require(a.cli and a.auth_file and a.gate, 'grader requires gate, CLI and subscription auth')
            gate = R.gate_check(SimpleNamespace(gate=a.gate, cell=a.family, out=out), packet_sha, binding, cli)
            require(gate['key_sha256'] == key_sha, 'grader key differs from lead freeze')
            allowance = gate['cells'][a.family]['inflight_allowance']
        a.reserve = R.grading_reserve(out, index=index, current_id=ident, family=a.family)
        require(a.estimate > 0, 'invalid grader estimate')
        remaining = min(a.budget - stage - a.reserve, R.EXPERIMENT_CAP - experiment - a.reserve)
        require(stage < a.budget and experiment < R.EXPERIMENT_CAP and
                (a.family != 'claude' or remaining >= a.estimate + allowance), 'grader stage/experiment launch guard')
        parent = out / 'graders' / ident
        work, home = parent / 'workspace', parent / 'home'
        work.mkdir(parents=True, mode=0o700)
        home.mkdir(mode=0o700)
        build_packet.copy_packet(a.packet, work / 'packet', manifest)
        shutil.copytree(a.blind, work / 'blind')
        shutil.copyfile(HERE / 'GRADER.md', work / 'GRADER.md')
        shutil.copyfile(a.key, work / 'KEY.json')
        (work / 'review_out').mkdir()
        before = R.snapshot(work)
        prompt = (f'Read GRADER.md and follow it. You are {ident}, family {family}, model {model}. '
                  'Only use KEY.json, packet/ and blind/. Eligibility is settled. Grade every key item in every report. '
                  f'Binding hashes: key_sha256={key_sha}, packet_sha256={packet_sha}, '
                  f'rubric_sha256={index["rubric_sha256"]}, blind_pack_sha256={sha(canonical(index))}. '
                  'Write the complete grade JSON to review_out/grade.json. No web, code execution, '
                  'delegation or other model calls. Inputs are read-only. Do not infer arm or cell.')
        usage = {'tokens_total': 0, 'tokens_noncache': 0, 'seconds': 0, 'metering_complete': False}
        status = 'dry-run'
        if a.dry_run:
            save(parent / 'command.json', {'argv': R.argv_for(a.family, cli, work, prompt, home / 'settings.json', model),
                                         'calls_model': False})
            (parent / 'events.jsonl').write_bytes(b'')
            (parent / 'stderr.txt').write_bytes(b'')
        else:
            cal_sandbox.abi()
            billing = R.auth_home(a.family, a.auth_file, home)
            version = R.cli_identity(a.family, cli, home)
            save(parent / 'intent.json', {'id': ident, 'freeze_sha256': binding, 'model': model,
                                          'provider': a.family, 'stage': 'grading'})
            try:
                usage.update(R.execute(a.family, cli, work, home, parent, prompt, 3600,
                                       remaining if a.family == 'claude' else 2**63 - 1, allowance, model))
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                usage.update(R.get_usage(a.family, parent / 'events.jsonl', home, work))
                usage.update(metering_complete=False, error_type=type(exc).__name__)
            usage.update(billing_source=billing, version_output=version)
            status = 'failed'
        isolated = R.workspace_unchanged(work, before)
        # Even malformed grades and interrupted calls are charged exactly once.
        record = {'schema_version': 1, 'id': ident, 'freeze_sha256': binding,
                  'provider': a.family, 'model': model, 'stage': 'grading', 'dry_run': a.dry_run,
                  'logical_tokens': usage['tokens_total'], 'noncache_tokens': usage['tokens_noncache'],
                  'seconds': usage.get('seconds') or 0, 'metering_complete': usage['metering_complete'],
                  'subagents_included': usage['metering_complete'], 'charge_ids': [ident],
                  'evidence_sha256': [R.evidence_digest(parent)], 'isolation_complete': isolated}
        if a.family == 'claude' and stage + usage['tokens_total'] > R.STAGE_CAP:
            record['deviations'] = ['late_reported_stage_threshold_exceeded; stop further launches']
        append(out / 'shared-costs.jsonl', record)
        try:
            grade = load(work / 'review_out' / 'grade.json')
            validate_grade(grade, key, key_sha, index)
            require(grade['model'] == model and grade['family'] == family and grade['grader_id'] == ident,
                    'assigned grader identity differs')
            require(isolated and usage['metering_complete'] and usage.get('exit') == 0 and
                    usage.get('result_seen') and not usage.get('stop_reason') and not usage.get('is_error'),
                    'incomplete grader execution')
            require((usage.get('model') == model and usage.get('api_key_source') == 'none') if a.family == 'claude'
                    else usage.get('models_seen') == [model], 'grader model or subscription mismatch')
            require(experiment + (usage['tokens_total'] if a.family == 'claude' else 0) <= R.EXPERIMENT_CAP,
                    'experiment cap exceeded')
            status = 'completed'
        except (ValueError, OSError, KeyError, TypeError):
            pass
        save(parent / 'usage.json', {'usage': usage, 'cost_record': record, 'status': status})
        if status == 'completed':
            save(out / ('grade-' + sha(canonical(index))[:12] + '-codex.json'), grade)
        print(ident + ': ' + status + '; logical=' + str(usage['tokens_total']))
        return 0 if status == 'completed' or a.dry_run else 5


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    b = sub.add_parser('pack')
    b.add_argument('--state', type=Path, required=True)
    b.add_argument('--out', type=Path, required=True)
    b.add_argument('--batch', type=int, choices=(1, 2), default=1)
    g = sub.add_parser('run-grader')
    g.add_argument('--family', choices=tuple(GRADERS), required=True)
    g.add_argument('--state', type=Path, required=True)
    g.add_argument('--blind', type=Path, required=True)
    g.add_argument('--packet', type=Path, help='required only for Codex; Claude never receives the packet')
    g.add_argument('--key', type=Path, required=True)
    g.add_argument('--cli', type=Path)
    g.add_argument('--auth-file', type=Path)
    g.add_argument('--gate', type=Path)
    g.add_argument('--spent', type=int, default=0)
    g.add_argument('--experiment-spent', type=int, default=0)
    g.add_argument('--budget', type=int, default=15_000_000)
    g.add_argument('--estimate', type=int, default=500_000)
    g.add_argument('--dry-run', action='store_true')
    s = sub.add_parser('score')
    s.add_argument('--key', type=Path, required=True)
    s.add_argument('--grade-a', type=Path, required=True)
    s.add_argument('--grade-b', type=Path, required=True)
    s.add_argument('--index', type=Path, required=True)
    s.add_argument('--private-map', type=Path, required=True)
    s.add_argument('--state', type=Path, required=True)
    s.add_argument('--resolution', type=Path)
    s.add_argument('--accounting', type=Path, help='final private coverage/cost audit; omitted means no conclusion')
    s.add_argument('--out', type=Path, required=True)
    s.add_argument('--previous', type=Path, help='audited batch-1 score for batch 2')
    a = p.parse_args(argv)
    if a.command == 'run-grader':
        require(0 < a.budget <= 15_000_000, 'invalid grading budget')
        return run_grader(a)
    if a.command == 'pack':
        pack(a.state, a.out, a.batch)
        print('Blind pack created. Withhold the separate PRIVATE-MAP file.')
    else:
        key = load(a.key)
        if not a.grade_a.is_file() or not a.grade_b.is_file():
            save(a.out, {'schema_version': 1, 'cells': {c: {'outcome': 'no conclusion', 'rule': 'NC1_missing_grader_file'} for c in CELLS},
                         'accounting_complete': False, 'reconciliation_complete': False})
            return 0
        grades = [load(a.grade_a), load(a.grade_b)]
        require({(g.get('model'), g.get('family')) for g in grades} == set(GRADERS.values()),
                'lead-assigned grader models/families required')
        mapping = load(a.private_map)
        # Audit delivered bytes again at scoring; do not trust an editable map alone.
        actual = [r for c in CELLS for r in rows(a.state / ('rows-' + c + '.jsonl'))]
        for rid, m in mapping['reports'].items():
            row = m['row']
            require(row['arm'] in ('N1', 'N2') and sum(r == row for r in actual) == 1, 'row/map differs')
            path = a.state / row['report_path']
            require(path.resolve().is_relative_to(a.state.resolve()) and sha(path.read_bytes()) == row['report_sha256'], 'report changed')
            report, rewrite_count = anonymous_report(a.state, row, load(path))
            require(sha(canonical(report)) == m['anonymous_sha256'] and rewrite_count == m['path_rewrite_count'], 'anonymous report changed')
        from cal_ledger import summary
        from cal_run import frozen
        ledger = summary(a.state, frozen())
        audit = load(a.accounting) if a.accounting else {}
        account_ok = final_accounting(audit, ledger, frozen())
        previous = load(a.previous) if a.previous else None
        require((mapping.get('batch', 1) == 2) == bool(previous), 'batch 2 requires batch-1 score')
        pending = ledger['unsettled_intents']
        n2_launched = any(r['cell'] == 'claude' and r['arm'] == 'N2' for r in actual + pending)
        sequential = load(a.state / 'claude-sequential.json') if (a.state / 'claude-sequential.json').exists() else {}
        if sequential:
            require(sequential.get('freeze_sha256') == frozen() and sequential.get('decision_sha256') ==
                    sha((a.state / 'decision-batch1.json').read_bytes()), 'sequential funding evidence changed')
        if previous:
            require(a.previous.resolve() == (a.state / 'decision-batch1.json').resolve() and
                    previous.get('freeze_sha256') == frozen() and sequential.get('funded') is True,
                    'batch 2 requires runner-authorized N2 and original batch-1 score')
            require(all(Path(p).is_file() and sha(Path(p).read_bytes()) == h for p,h in previous['input_sha256'].items()),
                    'batch-1 scoring inputs changed')
        result = score(key, sha(a.key.read_bytes()), grades, load(a.index), mapping,
                       load(a.resolution) if a.resolution else None,
                       [sha(a.grade_a.read_bytes()), sha(a.grade_b.read_bytes())], accounting_complete=account_ok, previous=previous,
                       n2_launched=n2_launched, n2_funded=sequential.get('funded', True))
        result['accounting_complete'] = account_ok
        result['freeze_sha256'] = frozen()
        result['input_attempts'] = [r for r in actual if r['arm'] in ('N1', 'N2')]
        result['claude_sequential'] = sequential
        result['reconciliation_complete'] = bool(a.resolution) and load(a.resolution).get('rounds') == 1
        result['input_sha256'] = {str(p): sha(p.read_bytes()) for p in (a.grade_a, a.grade_b, a.index, a.private_map) + ((a.resolution,) if a.resolution else ())}
        if not result['reconciliation_complete']:
            for v in result['cells'].values():
                v.update(outcome='no conclusion', rule='NC1_missing_blind_reconciliation_record')
        outside_stage = audit.get('outside_stage_claude_logical')
        result['deviations'] = (['late_reported_stage_threshold_exceeded; scoring remains allowed']
            if type(outside_stage) is int and
            ledger['providers']['claude']['observed_logical_tokens'] + outside_stage > 15_000_000 else [])
        result['observed_ledger'] = ledger
        for cell, verdict in result['cells'].items():
            native_attempts = [r for r in actual + pending if r['cell'] == cell and r['arm'] in ('N1', 'N2')]
            completed_count = sum(1 for r in native_attempts if usable(r))
            verdict['native_unit_cost_including_all_attempts'] = {
                'logical_tokens': sum(r['tokens_total'] for r in native_attempts) / completed_count if completed_count else None,
                'noncache_tokens': sum(r['tokens_noncache'] for r in native_attempts) / completed_count if completed_count else None,
                'complete': bool(native_attempts) and all(r.get('metering_complete') for r in native_attempts) and all(
                    any(r['arm'] == arm and usable(r) for r in native_attempts) for arm in
                    (('N1', 'N2') if cell == 'codex' or n2_launched else ('N1',))),
                'definition': 'all native attempts divided by retained completed N reports; missing work remains unknown'}
        result['all_attempt_costs'] = [{k: r.get(k) for k in ('attempt_id', 'cell', 'arm', 'status', 'tokens_total', 'tokens_noncache', 'seconds', 'metering_complete')} for r in actual + pending]
        if a.out.resolve() == (a.state / 'decision-batch1.json').resolve():
            require(not a.out.exists(), 'batch-1 score is immutable; use decision-final.json for branch/failure reporting')
        save(a.out, result)
        for cell, value in result['cells'].items():
            print(cell + ': ' + value['outcome'] + ' [' + value['rule'] + ']')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, TypeError, OSError):
        print('Refused: incomplete/malformed grades or mismatched frozen evidence.')
        raise SystemExit(2)
