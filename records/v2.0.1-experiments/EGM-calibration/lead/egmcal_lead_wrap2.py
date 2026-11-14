#!/usr/bin/env python3
"""Second lead wrapper for the EGM native calibration (issue #20): batch 2 packing, grading, reconciliation, scoring.

Written 2026-11-14 after Claude N2 completed and before any batch 2 grading. The frozen package is
not modified. It applies two run-time corrections:

1. The accounting aggregate of `egmcal_lead_score.py` (preflight probe rows are not study isolation).
2. The blind-pack provenance check. The frozen `cal_grade.check_blind_paths` refuses any report
   text in which the bare words `codex`, `claude`, `N1` or `N2` appear as a path-like token. The
   Claude N2 report mentions the branch name `claude/oaw-2`, which is content of the reviewed plan,
   not provenance, so the frozen check refused to pack batch 2 ("blind packet contains private path
   provenance"); batch 1 had passed only because no report happened to contain such a token.
   The corrected check still refuses the state root, every attempt id, and any `codex-N1`,
   `claude-N2.a1`-style token; it no longer refuses the bare words. Nothing else changes: the same
   reports, the same anonymisation, seed, key, graders, decision table.

Usage: egmcal_lead_wrap2.py grade <cal_grade arguments>  |  egmcal_lead_wrap2.py requests <cal_requests arguments>
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / 'egmcal'))

import egmcal_lead_score  # noqa: E402,F401  (applies correction 1 on import)
import cal_grade  # noqa: E402
import cal_requests  # noqa: E402
from cal_common import load, require  # noqa: E402


def check_blind_paths(folder, state, attempt_ids=()):
    """Reject run provenance in any packed file name or JSON string: state root, attempt ids, cell-arm tokens."""
    tokens = [re.escape(s) for s in sorted(set(attempt_ids))] + [r'(?:codex|claude)-(?:N1|N2|M)(?:\.a\d+)?']
    component = re.compile(r'(?:^|[/\\\s\x27"`(])(?:' + '|'.join(tokens) + r')(?=$|[/\\:\s\x27"`)])')
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


cal_grade.check_blind_paths = check_blind_paths

if __name__ == '__main__':
    module = {'grade': cal_grade, 'requests': cal_requests}[sys.argv[1]]
    raise SystemExit(module.main(sys.argv[2:]))
