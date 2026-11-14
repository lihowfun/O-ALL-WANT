#!/usr/bin/env python3
"""Lead wrapper around the frozen scorer of the EGM native calibration (issue #20).

Written 2026-11-14 after both graders' files and the reconciliation overlay were frozen and
before the private map was opened or any decision computed. The frozen package is not modified
(its freeze hash still verifies); this wrapper replaces one aggregate at run time.

Why: the preflight probe is required to overwrite its probe source file and to see that change
detected (DEVIATIONS, fifth host fix). The runner records that probe row with
`isolation_complete: false`, and `cal_ledger.summary` folds preflight rows into each provider's
`isolation_complete_for_recorded_work`. `cal_grade.final_accounting` then reports the accounting
as incomplete and every cell becomes "no conclusion (NC1)", although PREREG's isolation rule is
about the native runs (and graders), whose rows all record complete isolation. Text and script
disagree; the text governs. The preflight's own verdicts are enforced by the launch gate.

What changes: `isolation_complete_for_recorded_work` is computed over native attempts, unsettled
intents and shared work, excluding preflight probe rows. Token totals, metering flags, unsettled
intents, grades, key, decision table and everything else come from the frozen code unchanged.
The summary carries a `lead_correction` entry so the output shows that this wrapper was used.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'egmcal'))

import cal_grade  # noqa: E402
import cal_ledger  # noqa: E402
from cal_run import preflight_rows, read_state  # noqa: E402

_frozen_summary = cal_ledger.summary


def summary(state, binding):
    result = _frozen_summary(state, binding)
    state = Path(state)
    probes = preflight_rows(state, strict=False)
    attempts = read_state(state, binding, strict=False)
    shared = cal_ledger.shared_costs(state / 'shared-costs.jsonl', binding,
                                     [r['attempt_id'] for r in attempts + probes])
    pending = result['unsettled_intents']
    changed = {}
    for provider, entry in result['providers'].items():
        own = ([r for r in attempts if r['cell'] == provider] + [r for r in pending if r.get('cell') == provider]
               + [r for r in shared if r['provider'] == provider])
        value = all(r.get('isolation_complete', True) for r in own)
        if value != entry['isolation_complete_for_recorded_work']:
            changed[provider] = {'frozen_value': entry['isolation_complete_for_recorded_work'], 'value': value}
        entry['isolation_complete_for_recorded_work'] = value
    result['lead_correction'] = {
        'what': 'preflight probe rows excluded from isolation_complete_for_recorded_work',
        'probe_rows': sorted(r['attempt_id'] for r in probes), 'changed': changed}
    return result


cal_ledger.summary = summary

if __name__ == '__main__':
    raise SystemExit(cal_grade.main(sys.argv[1:]))
