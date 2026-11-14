#!/usr/bin/env python3
"""Lead continuation of the U2 pilot, by owner decision D49 (2026-11-14): run the planned 18 runs, do not stop.

The frozen runner ends the whole stage when one attempt is stopped at the observed token ceiling
("nonretryable attempt; stop stage"); the pilot stopped that way at attempt 7 of 18. The repository
owner then decided that the pilot continues to its planned 18 runs with the default settings.

This wrapper leaves every frozen file untouched (the freeze check still runs on every launch) and
changes two statements of `u2_run.run` in memory only:

1. A run whose last attempt was stopped at the observed token ceiling is final. It is kept, billed
   and never redrawn (as registered), listed in `lead-kept-ceiling-stops.jsonl`, and the stage moves
   on to the next planned run instead of stopping.
2. Such a run does not raise the end-of-run "attempt limit" stop.

Nothing else changes: the 600,000 ceiling, run order, prompts, arms, checker, freeze and preflight
verification, the budget guard, the stops for a broken checker or a severe violation (applied to a
kept ceiling stop exactly as to a completed run), and the single retry for infrastructure errors.

This is a deviation from the frozen pilot text (a metering error stops the stage), made on the
owner's instruction after seven attempts existed. Rows written under it carry the frozen runner's
source digest although this patch was active; `lead-continue.json` in the state records the patch.

Usage: u2_lead_continue.py <u2_run.py arguments>     (U2_RUNNER must point at the frozen runner folder)
"""
import hashlib
import json
import os
import sys
import time
import types
from pathlib import Path

RUNNER = Path(os.environ['U2_RUNNER']).resolve()
SOURCE = RUNNER / 'u2_run.py'
KEPT = 'lead-kept-ceiling-stops.jsonl'

A_OLD = """                if attempts and attempts[-1]['reason'] not in ('infrastructure','zero_or_unknown_usage'):
                    raise ValueError('nonretryable attempt; stop stage')
"""
A_NEW = """                if attempts and _lead_keep_ceiling_stop(state,args.cell,attempts[-1]):
                    break
                if attempts and attempts[-1]['reason'] not in ('infrastructure','zero_or_unknown_usage'):
                    raise ValueError('nonretryable attempt; stop stage')
"""
B_OLD = """            if attempts[-1]['status']!='completed':
                raise ValueError('attempt limit or infrastructure stop; both attempts retained and billed')
"""
B_NEW = """            if attempts[-1]['status']!='completed' and not _lead_is_ceiling_stop(attempts[-1]):
                raise ValueError('attempt limit or infrastructure stop; both attempts retained and billed')
"""


def is_ceiling_stop(row):
    return row.get('status') != 'completed' and row.get('exit') == 'token_ceiling' and row.get('truncated') is True


def keep_ceiling_stop(state, cell, row):
    """True for an attempt stopped at the observed ceiling; records it once and applies the safety stops."""
    if not is_ceiling_stop(row):
        return False
    state = Path(state)
    path = state / KEPT
    listed = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()] if path.exists() else []
    key = (row['run_id'], row['attempt'])
    if key not in {(r['run_id'], r['attempt']) for r in listed}:
        entry = {'run_id': row['run_id'], 'attempt': row['attempt'], 'cell': cell, 'exit': row['exit'], 'reason': row.get('reason'),
                 'logical_tokens_lower_bound': row['meter'].get('logical_tokens'), 'checker': row['checker']['status'],
                 'output_sha256': row.get('output_sha256'), 'decision': 'D49', 'recorded_at': time.strftime('%Y-%m-%dT%H:%M:%S%z')}
        with path.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(entry, sort_keys=True) + '\n')
        print(json.dumps({'run_id': row['run_id'], 'cell': cell, 'status': 'kept_ceiling_stop',
                          'logical_tokens_lower_bound': row['meter'].get('logical_tokens'), 'checker': row['checker']['status'],
                          'attachment_read': row['trigger']['attachment_read']}), flush=True)
    # Same safety stops as for a completed run.
    if row['checker']['status'] != 'completed':
        raise ValueError('checker broken; stop stage')
    result = json.loads((state / 'runs' / cell / row['run_id'] / ('attempt-' + str(row['attempt'])) / 'checker/result.json').read_text())
    if result['severe']:
        raise ValueError('severe violation; result retained, stage stopped')
    return True


def main():
    source = SOURCE.read_text(encoding='utf-8')
    if source.count(A_OLD) != 1 or source.count(B_OLD) != 1:
        raise SystemExit('frozen runner text differs from the two statements this wrapper replaces; refusing')
    patched = source.replace(A_OLD, A_NEW).replace(B_OLD, B_NEW)
    state = None
    if '--state' in sys.argv:
        state = Path(sys.argv[sys.argv.index('--state') + 1])
        record = state / 'lead-continue.json'
        if not record.exists():
            record.write_text(json.dumps({
                'decision': 'D49 (repository owner, 2026-11-14): run the planned 18 pilot runs, do not stop',
                'wrapper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'frozen_u2_run_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                'replaced_statements': [A_OLD, B_OLD], 'replacements': [A_NEW, B_NEW],
                'attempt_rows_before': sum(1 for line in (state / 'attempts-codex.jsonl').read_text().splitlines() if line.strip())
                                       if (state / 'attempts-codex.jsonl').exists() else 0,
                'written_at': time.strftime('%Y-%m-%dT%H:%M:%S%z')}, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    sys.path.insert(0, str(RUNNER))
    module = types.ModuleType('u2_run')
    module.__file__ = str(SOURCE)
    module.__dict__['_lead_keep_ceiling_stop'] = keep_ceiling_stop
    module.__dict__['_lead_is_ceiling_stop'] = is_ceiling_stop
    sys.modules['u2_run'] = module
    exec(compile(patched, str(SOURCE), 'exec'), module.__dict__)
    sys.argv = [str(SOURCE)] + sys.argv[1:]
    return module.main()


if __name__ == '__main__':
    raise SystemExit(main())
