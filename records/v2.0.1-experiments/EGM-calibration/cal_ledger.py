#!/usr/bin/env python3
"""Validate/summarize private plain accounting; no execution or inferred usage."""
import argparse
import json
import math
from pathlib import Path
from cal_common import append, canonical, hexsha, load, require, rows, sha


def shared_costs(path, binding, run_charge_ids=()):
    records = rows(path)
    ids, charges = set(), set(run_charge_ids)
    for r in records:
        require(r.get('schema_version') == 1 and r.get('freeze_sha256') == binding, 'shared ledger freeze differs')
        require(isinstance(r.get('id'), str) and r['id'] not in ids and r.get('provider') in
                ('claude', 'codex', 'other', 'human'), 'invalid shared ledger identity/provider')
        require(r.get('stage') in ('curation', 'grading', 'reconciliation', 'preparation', 'reporting'), 'invalid shared stage')
        require(type(r.get('metering_complete')) is bool and type(r.get('subagents_included')) is bool, 'shared coverage flags missing')
        require(type(r.get('logical_tokens')) is int and type(r.get('noncache_tokens')) is int and
                0 <= r['noncache_tokens'] <= r['logical_tokens'], 'shared token counts invalid')
        require(type(r.get('seconds')) in (int, float) and math.isfinite(r['seconds']) and r['seconds'] >= 0, 'shared wall time invalid')
        require(isinstance(r.get('evidence_sha256'), list) and r['evidence_sha256'] and
                all(hexsha(h) for h in r['evidence_sha256']), 'shared usage evidence not bound')
        require(isinstance(r.get('charge_ids'), list) and r['charge_ids'], 'shared charge scopes missing')
        for c in r['charge_ids']:
            require(isinstance(c, str) and c and c not in charges, 'duplicate/overlapping charge scope')
            charges.add(c)
        ids.add(r['id'])
    return records


def summary(state, binding):
    from cal_run import preflight_rows, read_state, unsettled_intents
    state = Path(state)
    attempts = read_state(state, binding, strict=False)
    attempts += preflight_rows(state, strict=False)
    shared = shared_costs(state / 'shared-costs.jsonl', binding, [r['attempt_id'] for r in attempts])
    pending = unsettled_intents(state, attempts + shared, binding)
    attempts += pending
    result = {'schema_version': 1, 'format': 'egmcal-plain-ledger-summary', 'providers': {},
              'unsettled_intents': pending}
    for provider in ('claude', 'codex', 'other', 'human'):
        own = [r for r in attempts if r['cell'] == provider] + [r for r in shared if r['provider'] == provider]
        complete = all(r['metering_complete'] and r.get('subagents_included', True) for r in own)
        result['providers'][provider] = {'observed_logical_tokens': sum(r['tokens_total'] if 'tokens_total' in r else r['logical_tokens'] for r in own),
            'observed_noncache_tokens': sum(r['tokens_noncache'] if 'tokens_noncache' in r else r['noncache_tokens'] for r in own),
            'observed_seconds': sum(r.get('seconds') or 0 for r in own), 'record_count': len(own),
            'metering_complete_for_recorded_work': complete,
            'isolation_complete_for_recorded_work': all(r.get('isolation_complete', True) for r in own),
            'planned_work_complete': False}
    result['note'] = 'Recorded work plus observed lower bounds for unsettled intents (unknown final cost). Add outside-root spent amounts; outstanding reserve is not spending. Missing planned work is never zero.'
    return result


def main(argv=None):
    from cal_run import frozen
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state', type=Path, required=True)
    p.add_argument('--add-shared', type=Path, help='lead-supplied shared cost JSON; never a public private path')
    p.add_argument('--eligibility-check', action='store_true', help='validate the settled already-spent checker charge')
    a = p.parse_args(argv)
    if a.add_shared:
        import fcntl
        from cal_run import check_out
        state = check_out(a.state, False)
        with (state / '.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            record = load(a.add_shared)
            if a.eligibility_check:
                require(record.get('provider') == 'claude' and record.get('stage') == 'curation' and
                        record.get('logical_tokens') == 3_398_755 and record.get('noncache_tokens') == 359_512 and
                        record.get('metering_complete') is True and record.get('subagents') == 'none' and
                        record.get('metering_source') == 'session transcript', 'settled checker charge differs')
            import tempfile
            previous = rows(state / 'shared-costs.jsonl')
            with tempfile.TemporaryDirectory(dir=state) as temp:
                candidate = Path(temp) / 'candidate.jsonl'
                for r in previous + [record]:
                    append(candidate, r)
                attempts = [r for c in ('claude', 'codex') for r in rows(state / ('rows-' + c + '.jsonl'))]
                from cal_run import preflight_rows
                attempts += preflight_rows(state)
                shared_costs(candidate, frozen(), [r['attempt_id'] for r in attempts])
            append(state / 'shared-costs.jsonl', record)
    print(json.dumps(summary(a.state, frozen()), ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, TypeError):
        raise SystemExit('ledger incomplete or invalid')
